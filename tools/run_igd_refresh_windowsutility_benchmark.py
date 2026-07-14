"""Benchmark the reviewed IGD source-refresh flow on a safe WindowsUtility copy."""

from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path, PurePosixPath
from typing import Any

from experimental_csharp_project import validate_project_workspace
from experimental_csharp_workspace import csharp_source_records, records_digest
from igd_daily import project_paths, read_json, validate_launch_record
from igd_refresh import tree_digest


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path(r"C:\Users\ytkim\Desktop\kyt_work\WindowsUtility")
PLAN_MAX_SECONDS = 60.0
ACCEPT_MAX_SECONDS = 10.0
BENCHMARK_COMMENT = b"\n// IGD P9.35 deterministic refresh benchmark probe\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark a reviewed IGD refresh on an isolated copy of the C# files "
            "accepted from WindowsUtility. The source repository is never mutated."
        )
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help=f"C# source root (default: {DEFAULT_SOURCE}).",
    )
    parser.add_argument(
        "--git-revision",
        help="Benchmark an immutable local Git commit export instead of the mutable working tree.",
    )
    parser.add_argument("--out", type=Path, required=True, help="Canonical JSON report path.")
    return parser.parse_args()


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def copy_accepted_sources(source: Path, destination: Path, records: list[dict[str, str]]) -> None:
    destination.mkdir(parents=True)
    for record in records:
        relative = PurePosixPath(record["path"])
        target = destination.joinpath(*relative.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.joinpath(*relative.parts).read_bytes())


def parse_cli_json(
    process: subprocess.CompletedProcess[str],
    label: str,
    accepted_returncodes: tuple[int, ...],
) -> dict[str, Any]:
    if process.returncode not in accepted_returncodes:
        detail = (process.stderr or process.stdout).strip()
        raise RuntimeError(f"{label} failed with exit code {process.returncode}: {detail}")
    try:
        value = json.loads(process.stdout.strip().splitlines()[-1])
    except (IndexError, json.JSONDecodeError) as error:
        raise RuntimeError(f"{label} did not emit a JSON object") from error
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} did not emit a JSON object")
    return value


def run_igd(
    arguments: list[str],
    label: str,
    *,
    timeout: int = 300,
    accepted_returncodes: tuple[int, ...] = (0,),
) -> tuple[dict[str, Any], float]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONHASHSEED"] = "0"
    started = time.monotonic()
    process = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "igd.py"), *arguments],
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    elapsed = time.monotonic() - started
    return parse_cli_json(process, label, accepted_returncodes), elapsed


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def authority_is_non_mutating(value: dict[str, Any]) -> bool:
    if value.get("targetRepositoryMutation") is not False:
        return False
    authority = value.get("authority")
    return not isinstance(authority, dict) or authority.get("targetRepositoryMutation") is False


def relative_workspace(project_root: Path, value: str) -> Path:
    parsed = PurePosixPath(value)
    require(not parsed.is_absolute() and bool(parsed.parts), "revision workspace path is invalid")
    require(all(part not in {"", ".", ".."} for part in parsed.parts), "revision workspace path is unsafe")
    candidate = project_root.joinpath(*parsed.parts).resolve()
    try:
        candidate.relative_to(project_root.resolve())
    except ValueError as error:
        raise RuntimeError("revision workspace escaped the project root") from error
    return candidate


def git_commit(source: Path, revision: str) -> str:
    process = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "--verify", f"{revision}^{{commit}}"],
        text=True,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if process.returncode != 0:
        raise RuntimeError(f"Git revision is not a local commit: {revision}")
    return process.stdout.strip()


def export_git_csharp_revision(source: Path, commit: str, destination: Path) -> None:
    process = subprocess.run(
        ["git", "-C", str(source), "archive", "--format=tar", commit],
        capture_output=True,
        check=False,
    )
    if process.returncode != 0:
        raise RuntimeError("could not export the local Git revision")
    destination.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(process.stdout), mode="r:") as archive:
        for member in archive.getmembers():
            relative = PurePosixPath(member.name)
            if (
                not member.isfile()
                or relative.suffix.lower() != ".cs"
                or relative.is_absolute()
                or not relative.parts
                or any(part in {"", ".", ".."} for part in relative.parts)
            ):
                continue
            stream = archive.extractfile(member)
            if stream is None:
                raise RuntimeError(f"could not read archived C# file: {member.name}")
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(stream.read())


def benchmark(source: Path, source_provenance: dict[str, Any] | None = None) -> dict[str, Any]:
    source = source.expanduser().resolve(strict=True)
    original_before = csharp_source_records(source)
    original_digest_before = records_digest(original_before)

    with tempfile.TemporaryDirectory(prefix="igd-p9.35-windowsutility-") as temporary:
        temporary_root = Path(temporary)
        copied_source = temporary_root / "source"
        home = temporary_root / "home"
        copy_accepted_sources(source, copied_source, original_before)
        copied_before = csharp_source_records(copied_source)
        require(copied_before == original_before, "temporary C# copy does not match the accepted real-source records")

        prepare, prepare_seconds = run_igd(
            ["prepare", str(copied_source), "--home", str(home), "--title", "WindowsUtility P9.35 benchmark"],
            "prepare",
        )
        require(prepare.get("result") == "pass" and prepare.get("action") == "created", "prepare did not create the benchmark project")
        require(authority_is_non_mutating(prepare), "prepare claimed target repository mutation authority")

        changed_record = original_before[0]
        changed_relative = PurePosixPath(changed_record["path"])
        changed_file = copied_source.joinpath(*changed_relative.parts)
        changed_file.write_bytes(changed_file.read_bytes() + BENCHMARK_COMMENT)
        intentional_records = csharp_source_records(copied_source)
        intentional_digest = records_digest(intentional_records)
        require(intentional_digest != original_digest_before, "benchmark comment did not change the temporary source digest")
        require(len(intentional_records) == len(original_before), "benchmark comment changed the C# file count")

        first_plan, first_plan_seconds = run_igd(
            ["refresh", str(copied_source), "--home", str(home)],
            "first refresh plan",
        )
        require(first_plan.get("result") == "review-required" and first_plan.get("action") == "planned", "first refresh did not require review")
        require(first_plan.get("activeRevisionChanged") is False, "refresh planning changed the active revision")
        require(authority_is_non_mutating(first_plan), "refresh planning claimed target repository mutation authority")

        paths = project_paths(copied_source, home)
        pending_plan_path = paths["root"] / "refresh" / "pending" / "refresh-plan.json"
        first_pending = read_json(pending_plan_path)
        first_pending_bytes = canonical_bytes(first_pending)
        first_status, first_status_seconds = run_igd(
            ["status", str(copied_source), "--home", str(home)],
            "status after first plan",
            accepted_returncodes=(1,),
        )
        require(first_status.get("result") == "refresh-review-required", "status did not expose the pending refresh review")
        require(first_status.get("pendingRefreshPlanId") == first_plan.get("planId"), "status reported a different pending plan id")

        discard, discard_seconds = run_igd(
            ["refresh", str(copied_source), "--home", str(home), "--discard-plan", str(first_plan["planId"])],
            "discard first refresh plan",
        )
        require(discard.get("result") == "pass" and discard.get("action") == "discarded", "first refresh plan was not discarded")
        require(discard.get("activeRevisionChanged") is False, "discard changed the active revision")
        require(authority_is_non_mutating(discard), "discard claimed target repository mutation authority")

        discarded_status, discarded_status_seconds = run_igd(
            ["status", str(copied_source), "--home", str(home)],
            "status after discard",
            accepted_returncodes=(1,),
        )
        require(discarded_status.get("result") == "refresh-required", "discard did not restore refresh-required status")

        second_plan, second_plan_seconds = run_igd(
            ["refresh", str(copied_source), "--home", str(home)],
            "second refresh plan",
        )
        require(second_plan.get("result") == "review-required" and second_plan.get("action") == "planned", "second refresh did not require review")
        second_pending = read_json(pending_plan_path)
        second_pending_bytes = canonical_bytes(second_pending)
        require(canonical_bytes(first_plan) == canonical_bytes(second_plan), "refresh plan summaries were not deterministic")
        require(first_pending_bytes == second_pending_bytes, "pending refresh plans were not byte-deterministic")
        require(first_plan.get("planId") == second_plan.get("planId"), "refresh plan ids were not deterministic")
        require(first_pending.get("candidateWorkspaceDigest") == second_pending.get("candidateWorkspaceDigest"), "candidate workspace digests were not deterministic")

        accept, accept_seconds = run_igd(
            ["refresh", str(copied_source), "--home", str(home), "--accept-plan", str(second_plan["planId"])],
            "accept second refresh plan",
        )
        require(accept.get("result") == "pass" and accept.get("action") == "accepted", "accepted refresh did not pass")
        require(accept.get("activeRevisionChanged") is True, "accepted refresh did not change the active revision")
        require(authority_is_non_mutating(accept), "accepted refresh claimed target repository mutation authority")

        final_status, final_status_seconds = run_igd(
            ["status", str(copied_source), "--home", str(home)],
            "final status",
        )
        require(final_status.get("result") == "pass", "status did not pass after refresh acceptance")
        require(authority_is_non_mutating(final_status), "final status claimed target repository mutation authority")

        launch = read_json(paths["launch"])
        launch_view = validate_launch_record(launch, copied_source, paths["root"])
        active_revision = launch_view["activeRevision"]
        archived_revisions = launch_view["archivedRevisions"]
        require(active_revision["id"] == "revision.r0002" and active_revision["sequence"] == 2, "accepted revision is not revision.r0002")
        require(len(archived_revisions) == 1, "accepted refresh did not archive exactly one revision")
        require(archived_revisions[0]["id"] == "revision.r0001", "archived revision is not revision.r0001")

        active_workspace = launch_view["activeWorkspace"]
        prior_workspace = relative_workspace(paths["root"], archived_revisions[0]["workspace"])
        validate_project_workspace(active_workspace)
        validate_project_workspace(prior_workspace)
        require(tree_digest(active_workspace) == active_revision["workspaceDigest"], "active revision workspace digest is stale")
        require(tree_digest(prior_workspace) == archived_revisions[0]["workspaceDigest"], "archived revision workspace digest is stale")

        temporary_after = csharp_source_records(copied_source)
        temporary_digest_after = records_digest(temporary_after)
        original_after = csharp_source_records(source)
        original_digest_after = records_digest(original_after)
        require(temporary_after == intentional_records, "IGD changed the temporary source after the intentional benchmark edit")
        require(original_after == original_before, "the real source repository changed during the benchmark")
        require(first_plan_seconds <= PLAN_MAX_SECONDS and second_plan_seconds <= PLAN_MAX_SECONDS, "refresh planning exceeded 60 seconds")
        require(accept_seconds <= ACCEPT_MAX_SECONDS, "refresh acceptance exceeded 10 seconds")

        plan_seconds = max(first_plan_seconds, second_plan_seconds)
        return {
            "artifactRole": "intentgraph-p9.35-windowsutility-refresh-benchmark-report",
            "schemaVersion": "0.1.0",
            "scope": "p9.35-reviewed-source-refresh-windowsutility-benchmark",
            "result": "pass",
            "source": {
                "name": (source_provenance or {}).get("name", source.name),
                "inputMode": (source_provenance or {}).get("inputMode", "working-tree"),
                "gitRevision": (source_provenance or {}).get("gitRevision"),
                "liveWorkingTreeUsed": (source_provenance or {}).get("inputMode", "working-tree") == "working-tree",
                "sourcePathPersisted": False,
                "csharpFileCount": len(original_before),
                "digestBefore": original_digest_before,
                "digestAfter": original_digest_after,
                "unchanged": original_before == original_after,
            },
            "temporarySource": {
                "acceptedCopyMatchesRealSource": copied_before == original_before,
                "intentionalChangePath": changed_record["path"],
                "intentionalChangeKind": "comment-only-append",
                "digestAfterIntentionalChange": intentional_digest,
                "digestAfterIntentGraph": temporary_digest_after,
                "unchangedByIntentGraph": temporary_after == intentional_records,
            },
            "timings": {
                "prepareSeconds": round(prepare_seconds, 6),
                "firstPlanSeconds": round(first_plan_seconds, 6),
                "discardSeconds": round(discard_seconds, 6),
                "secondPlanSeconds": round(second_plan_seconds, 6),
                "planSeconds": round(plan_seconds, 6),
                "firstStatusSeconds": round(first_status_seconds, 6),
                "discardedStatusSeconds": round(discarded_status_seconds, 6),
                "acceptSeconds": round(accept_seconds, 6),
                "finalStatusSeconds": round(final_status_seconds, 6),
            },
            "thresholds": {
                "planMaxSeconds": PLAN_MAX_SECONDS,
                "planPassed": plan_seconds <= PLAN_MAX_SECONDS,
                "acceptMaxSeconds": ACCEPT_MAX_SECONDS,
                "acceptPassed": accept_seconds <= ACCEPT_MAX_SECONDS,
            },
            "determinism": {
                "discardAndReplanPerformed": True,
                "planIdStable": first_plan["planId"] == second_plan["planId"],
                "planSummaryCanonicalJsonStable": canonical_bytes(first_plan) == canonical_bytes(second_plan),
                "pendingPlanCanonicalJsonStable": first_pending_bytes == second_pending_bytes,
                "candidateWorkspaceDigestStable": first_pending["candidateWorkspaceDigest"] == second_pending["candidateWorkspaceDigest"],
            },
            "refresh": {
                "planResult": second_plan["result"],
                "planId": second_plan["planId"],
                "fromRevision": second_plan["fromRevision"]["id"],
                "toRevision": second_plan["toRevision"]["id"],
                "acceptResult": accept["result"],
                "statusResult": final_status["result"],
                "activeRevision": active_revision["id"],
                "archivedRevisionCount": len(archived_revisions),
            },
            "workspaceValidation": {
                "activeRevisionValidated": True,
                "activeWorkspaceDigestMatched": True,
                "priorRevisionValidated": True,
                "priorWorkspaceDigestMatched": True,
            },
            "authority": {
                "explicitPlanAcceptanceUsed": True,
                "targetRepositoryMutation": False,
                "activeRevisionMutation": True,
                "networkRequired": False,
                "providerApiAllowed": False,
                "credentialAccessAllowed": False,
                "automaticIntentMapping": False,
                "automaticCodeApplication": False,
                "approvalAutomation": False,
            },
            "nonGoals": {
                "realSourceChanged": False,
                "targetBuildExecuted": False,
                "targetRestoreExecuted": False,
                "targetLaunchExecuted": False,
                "sourcePatchApplied": False,
            },
        }


def main() -> int:
    arguments = parse_args()
    source = arguments.source.expanduser().resolve(strict=True)
    output = arguments.out.expanduser().resolve()
    if output == Path(__file__).resolve() or output.is_relative_to(source):
        raise SystemExit("error: output must not overwrite benchmark code or source inputs")
    if arguments.git_revision:
        commit = git_commit(source, arguments.git_revision)
        with tempfile.TemporaryDirectory(prefix="igd-p9.35-git-export-") as temporary:
            exported_source = Path(temporary) / source.name
            export_git_csharp_revision(source, commit, exported_source)
            report = benchmark(
                exported_source,
                {
                    "name": source.name,
                    "inputMode": "git-committed-export",
                    "gitRevision": commit,
                },
            )
    else:
        report = benchmark(source)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_bytes(report)
    output.write_bytes(payload)
    sys.stdout.buffer.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
