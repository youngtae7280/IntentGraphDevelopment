"""Run the bounded P9.6 WindowsUtility C# syntax-only feasibility probe.

The target source tree is read-only. Roslyn is compiled from a disposable copy
of the local probe source and every output is written outside the target.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROBE_SOURCE = ROOT / "tools" / "csharp_syntax_probe"
PROBE_PROJECT_NAME = "IntentGraph.CSharpSyntaxProbe.csproj"
EXPECTED_SCOPE = "windowsutility-csharp-syntax-only-readonly"
EXPECTED_PROFILE = "windowsutility-csharp-syntax-probe"
EXPECTED_FACT_KINDS = {
    "file",
    "namespace",
    "type",
    "method",
    "constructor",
    "property",
    "field",
    "using",
    "invocation",
}
EXPECTED_RELATION_KINDS = {"contains", "imports", "invokes-syntax"}


class ProbeError(RuntimeError):
    """Raised when the P9.6 read-only probe cannot be trusted."""


def canonical_json(data: Any) -> bytes:
    return (json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def run_command(args: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)


def require_success(completed: subprocess.CompletedProcess[str], label: str) -> None:
    if completed.returncode != 0:
        raise ProbeError(f"{label} failed: {completed.stderr.strip() or completed.stdout.strip()}")


def is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def is_reparse_point(path: Path) -> bool:
    details = path.lstat()
    attributes = getattr(details, "st_file_attributes", 0)
    reparse_attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(details.st_mode) or bool(attributes & reparse_attribute)


def resolved_source_path(path: Path, root: Path, relative: Path) -> Path:
    try:
        if is_reparse_point(path):
            raise ProbeError(f"target source tree must not contain reparse points: {relative.as_posix()}")
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
    except ProbeError:
        raise
    except (OSError, ValueError) as error:
        raise ProbeError(f"target source path must resolve under the source root: {relative.as_posix()}") from error
    return resolved


def csharp_files(source_root: Path) -> list[Path]:
    try:
        invalid_root = not source_root.is_dir() or is_reparse_point(source_root)
    except OSError:
        invalid_root = True
    if invalid_root:
        raise ProbeError("target source root must be an existing non-symlink directory")
    source_root = source_root.resolve(strict=True)
    files: list[Path] = []
    pending = [source_root]
    while pending:
        directory = pending.pop()
        try:
            entries = sorted(os.scandir(directory), key=lambda entry: entry.name)
        except OSError as error:
            raise ProbeError(f"cannot enumerate target source directory: {directory}") from error
        for entry in entries:
            path = Path(entry.path)
            relative = path.relative_to(source_root)
            resolved = resolved_source_path(path, source_root, relative)
            try:
                if entry.is_dir(follow_symlinks=False):
                    if not any(part.lower() in {"bin", "obj"} for part in relative.parts):
                        pending.append(resolved)
                elif entry.is_file(follow_symlinks=False) and path.suffix.lower() == ".cs":
                    files.append(resolved)
            except OSError as error:
                raise ProbeError(f"cannot inspect target source path: {relative.as_posix()}") from error
    files.sort(key=lambda item: item.relative_to(source_root).as_posix())
    if not files:
        raise ProbeError("target source root has no C# files")
    return files


def source_snapshot(source_root: Path) -> dict[str, str]:
    source_root = source_root.resolve(strict=True)
    return {
        path.relative_to(source_root).as_posix(): sha256_bytes(path.read_bytes())
        for path in csharp_files(source_root)
    }


def source_snapshot_digest(snapshot: dict[str, str]) -> str:
    return sha256_bytes(canonical_json(snapshot))


def logical_source_root_is_valid(value: str) -> bool:
    return value.startswith("intentgraph://") and ".." not in value and "\\" not in value


def target_git_state(target_source_root: Path) -> dict[str, str]:
    repository = target_source_root.parent
    head = run_command(["git", "rev-parse", "HEAD"], cwd=repository)
    upstream = run_command(["git", "rev-parse", "origin/main"], cwd=repository)
    status = run_command(["git", "status", "--porcelain"], cwd=repository)
    require_success(head, "target git HEAD read")
    require_success(upstream, "target git origin/main read")
    require_success(status, "target git status read")
    return {
        "head": head.stdout.strip(),
        "originMain": upstream.stdout.strip(),
        "status": status.stdout.strip(),
    }


def build_probe(temp_root: Path) -> Path:
    copied_probe = temp_root / "probe"
    shutil.copytree(PROBE_SOURCE, copied_probe)
    project = copied_probe / PROBE_PROJECT_NAME
    nuget_packages = temp_root / "nuget-packages"
    nuget_http_cache = temp_root / "nuget-http-cache"
    env = os.environ.copy()
    env.update(
        {
            "DOTNET_CLI_HOME": str(temp_root / "dotnet-home"),
            "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
            "NUGET_PACKAGES": str(nuget_packages),
            "NUGET_HTTP_CACHE_PATH": str(nuget_http_cache),
        }
    )
    restore = run_command(
        ["dotnet", "restore", str(project), "--configfile", str(copied_probe / "NuGet.Config"), "--disable-parallel"],
        cwd=copied_probe,
        env=env,
    )
    require_success(restore, "isolated Roslyn probe restore")
    build = run_command(
        ["dotnet", "build", str(project), "--configuration", "Release", "--no-restore"],
        cwd=copied_probe,
        env=env,
    )
    require_success(build, "isolated Roslyn probe build")
    assembly = copied_probe / "bin" / "Release" / "net8.0" / "IntentGraph.CSharpSyntaxProbe.dll"
    if not assembly.is_file():
        raise ProbeError("isolated Roslyn probe assembly was not produced")
    return assembly


def invoke_probe(
    assembly: Path,
    source_root: Path,
    logical_source_root: str,
    output: Path,
    *,
    artifact_scope: str | None = None,
    profile_id: str | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [
        "dotnet",
        str(assembly),
        "--source-root",
        str(source_root),
        "--source-root-id",
        logical_source_root,
        "--out",
        str(output),
    ]
    if artifact_scope is not None:
        command.extend(["--artifact-scope", artifact_scope])
    if profile_id is not None:
        command.extend(["--profile-id", profile_id])
    return run_command(
        command,
        cwd=assembly.parent,
        env={
            **os.environ,
            "DOTNET_CLI_HOME": str(assembly.parent / ".dotnet-home"),
            "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
        },
    )


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ProbeError("code facts must be a JSON object")
    return data


def validate_facts(
    data: dict[str, Any],
    snapshot: dict[str, str],
    logical_source_root: str,
    *,
    expected_scope: str = EXPECTED_SCOPE,
    expected_profile_id: str = EXPECTED_PROFILE,
) -> dict[str, Any]:
    if data.get("artifactRole") != "intentgraph-code-facts":
        raise ProbeError("wrong code-facts artifactRole")
    if data.get("status") != "intentgraph-code-facts-extracted":
        raise ProbeError("wrong code-facts status")
    if data.get("scope") != expected_scope or data.get("profileId") != expected_profile_id:
        raise ProbeError("wrong C# syntax-probe profile or scope")
    if data.get("sourceRoot") != logical_source_root or data.get("sourceRootKind") != "logical-id":
        raise ProbeError("code facts must use the supplied logical source root")
    extractor = data.get("extractor")
    if not isinstance(extractor, dict):
        raise ProbeError("code facts missing extractor metadata")
    for key, expected in {
        "mode": "roslyn-syntax-only",
        "deterministic": True,
        "semanticResolution": False,
        "sourceBuildAllowed": False,
        "broadExtractor": False,
    }.items():
        if extractor.get(key) != expected:
            raise ProbeError(f"extractor.{key} must be {expected!r}")
    if data.get("sourceDigests") != snapshot:
        raise ProbeError("source digest set does not match the read-only target snapshot")

    facts = data.get("facts")
    relations = data.get("relations")
    if not isinstance(facts, list) or not facts or not isinstance(relations, list):
        raise ProbeError("code facts must contain a non-empty facts array and a relations array")
    fact_ids: set[str] = set()
    observed_kinds: set[str] = set()
    file_fact_counts = {source_file: 0 for source_file in snapshot}
    for fact in facts:
        if not isinstance(fact, dict):
            raise ProbeError("every fact must be an object")
        fact_id = fact.get("id")
        if not isinstance(fact_id, str) or not fact_id or fact_id in fact_ids:
            raise ProbeError("fact ids must be non-empty and unique")
        fact_ids.add(fact_id)
        kind = fact.get("kind")
        if kind not in EXPECTED_FACT_KINDS:
            raise ProbeError(f"unsupported syntax fact kind: {kind}")
        observed_kinds.add(kind)
        source_file = fact.get("sourceFile")
        if not isinstance(source_file, str) or source_file not in snapshot or source_file.startswith(("/", "\\")) or ":" in source_file:
            raise ProbeError(f"fact {fact_id} has an unsafe or unknown sourceFile")
        if fact.get("sourceDigest") != snapshot[source_file]:
            raise ProbeError(f"fact {fact_id} has a stale source digest")
        if fact.get("extractor") != "tools/csharp_syntax_probe/Program.cs" or not isinstance(fact.get("extractorVersion"), str):
            raise ProbeError(f"fact {fact_id} has invalid extractor provenance")
        if fact.get("confidence") not in {"extracted", "ambiguous"}:
            raise ProbeError(f"fact {fact_id} has invalid confidence")
        if kind == "invocation":
            if fact.get("confidence") != "ambiguous" or not isinstance(fact.get("invocationShape"), str):
                raise ProbeError(f"invocation fact {fact_id} must remain syntax-only and ambiguous")
        elif fact.get("confidence") != "extracted":
            raise ProbeError(f"non-invocation fact {fact_id} must be extracted")
        if "sourceText" in fact or "targetSyntax" in fact:
            raise ProbeError(f"fact {fact_id} must not persist source text")
        location = fact.get("sourceLocation")
        if kind == "file":
            if fact.get("sourceLocationStatus") != "file-level":
                raise ProbeError(f"file fact {fact_id} must be file-level")
            file_fact_counts[source_file] += 1
        elif not isinstance(location, dict) or not {"lineStart", "lineEnd", "columnStart", "columnEnd"}.issubset(location):
            raise ProbeError(f"fact {fact_id} is missing source location provenance")
    invalid_file_fact_counts = {path: count for path, count in file_fact_counts.items() if count != 1}
    if invalid_file_fact_counts:
        raise ProbeError(
            "C# facts must contain exactly one file fact per source digest entry; "
            f"invalid counts={invalid_file_fact_counts}"
        )
    if [fact["id"] for fact in facts] != sorted(fact_ids):
        raise ProbeError("facts must be sorted by id")

    relation_ids: set[str] = set()
    observed_relation_kinds: set[str] = set()
    for relation in relations:
        if not isinstance(relation, dict):
            raise ProbeError("every relation must be an object")
        relation_id = relation.get("id")
        if not isinstance(relation_id, str) or not relation_id or relation_id in relation_ids:
            raise ProbeError("relation ids must be non-empty and unique")
        relation_ids.add(relation_id)
        kind = relation.get("kind")
        if kind not in EXPECTED_RELATION_KINDS:
            raise ProbeError(f"unsupported relation kind: {kind}")
        observed_relation_kinds.add(kind)
        if relation.get("from") not in fact_ids or relation.get("to") not in fact_ids:
            raise ProbeError(f"relation {relation_id} has an unresolved endpoint")
    if [relation["id"] for relation in relations] != sorted(relation_ids):
        raise ProbeError("relations must be sorted by id")
    return {
        "sourceFileCount": len(snapshot),
        "factCount": len(facts),
        "relationCount": len(relations),
        "factKindCounts": {kind: sum(1 for fact in facts if fact["kind"] == kind) for kind in sorted(observed_kinds)},
        "relationKindCounts": {kind: sum(1 for relation in relations if relation["kind"] == kind) for kind in sorted(observed_relation_kinds)},
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-source-root", type=Path, required=True)
    parser.add_argument("--logical-source-root", required=True)
    parser.add_argument("--out-facts", type=Path, required=True)
    parser.add_argument("--out-report", type=Path, required=True)
    parser.add_argument("--expected-target-revision", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target_source_root = args.target_source_root.resolve()
    out_facts = args.out_facts.resolve()
    out_report = args.out_report.resolve()
    if not logical_source_root_is_valid(args.logical_source_root):
        raise SystemExit("error: logical source root must be an intentgraph:// identifier without traversal or backslashes")
    if out_facts == out_report or is_under(out_facts, target_source_root) or is_under(out_report, target_source_root):
        raise SystemExit("error: facts and report outputs must be distinct and outside the target source root")

    try:
        before_git = target_git_state(target_source_root)
        if before_git["status"] or before_git["head"] != before_git["originMain"]:
            raise ProbeError("target repository must be clean and aligned with origin/main")
        if before_git["head"] != args.expected_target_revision:
            raise ProbeError("target revision does not match the P9.6 declared revision")
        before_snapshot = source_snapshot(target_source_root)
        with tempfile.TemporaryDirectory(prefix="p9.6-csharp-syntax-") as temporary:
            temp_root = Path(temporary)
            assembly = build_probe(temp_root)
            first = temp_root / "first-facts.json"
            repeat = temp_root / "repeat-facts.json"
            require_success(invoke_probe(assembly, target_source_root, args.logical_source_root, first), "first syntax extraction")
            require_success(invoke_probe(assembly, target_source_root, args.logical_source_root, repeat), "repeat syntax extraction")
            if first.read_bytes() != repeat.read_bytes():
                raise ProbeError("repeat syntax extraction was not byte-identical")
            facts = read_json(first)
        summary = validate_facts(facts, before_snapshot, args.logical_source_root)
        after_snapshot = source_snapshot(target_source_root)
        after_git = target_git_state(target_source_root)
        if before_snapshot != after_snapshot or before_git != after_git:
            raise ProbeError("target source state changed during the syntax-only probe")
        write_json(out_facts, facts)
        report = {
            "artifactRole": "intentgraph-csharp-syntax-feasibility-probe-report",
            "status": "intentgraph-csharp-syntax-feasibility-probe-passed",
            "scope": "p9.6-windowsutility-csharp-syntax-only-readonly",
            "result": "pass",
            "target": {"id": "WindowsUtility", "revision": before_git["head"], "cleanAligned": True},
            "source": {
                "logicalRoot": args.logical_source_root,
                "fileCount": len(before_snapshot),
                "beforeDigest": source_snapshot_digest(before_snapshot),
                "afterDigest": source_snapshot_digest(after_snapshot),
                "unchanged": True,
            },
            "extraction": {
                "adapter": "roslyn-syntax-only",
                "deterministic": True,
                "repeatOutputByteIdentical": True,
                "semanticResolution": False,
                "sourceBuildAllowed": False,
                "summary": summary,
            },
            "authority": {
                "targetRepositoryMutation": False,
                "targetBuildExecuted": False,
                "targetRestoreExecuted": False,
                "targetLaunchExecuted": False,
                "hardwareAccess": False,
                "networkRequired": False,
                "providerApiAllowed": False,
                "credentialAccessAllowed": False,
                "automaticCodeApplication": False,
                "igdProductizationClaimed": False,
            },
        }
        write_json(out_report, report)
        print(json.dumps(report, ensure_ascii=True, indent=2))
        return 0
    except ProbeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
