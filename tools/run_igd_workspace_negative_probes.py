"""Repeatable P9.1 negative probes for the local-review workspace contract."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
FACADE = ROOT / "tools" / "intentgraph.py"


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def mutate_manifest(workspace: Path, mutate: Callable[[dict[str, Any]], None]) -> None:
    path = workspace / "intentgraph.workspace.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    mutate(value)
    write_json(path, value)


def run(workspace: Path, command: str = "validate") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(FACADE), command, "--workspace", str(workspace)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def stale_profile_proposal_baseline(workspace: Path) -> None:
    path = workspace / "proposals" / "p4.0-complete-todo-route.proposal.json"
    proposal = json.loads(path.read_text(encoding="utf-8"))
    proposal["baseline"]["codeFactsDigest"] = "sha256:stale"
    write_json(path, proposal)


def wrong_profile_proposal(workspace: Path) -> None:
    path = workspace / "proposals" / "p4.0-complete-todo-route.proposal.json"
    proposal = json.loads(path.read_text(encoding="utf-8"))
    proposal["workspaceProfile"]["logicalSourceRoot"] = "intentgraph://wrong/profile"
    write_json(path, proposal)


def enable_authority(workspace: Path, key: str) -> None:
    mutate_manifest(workspace, lambda value: value["authority"].__setitem__(key, True))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run P9.1 workspace negative probes.")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    probes: list[tuple[str, Callable[[Path], None], str, str]] = [
        (
            "wrong-workspace-role",
            lambda workspace: mutate_manifest(workspace, lambda value: value.__setitem__("artifactRole", "wrong-role")),
            "workspace artifactRole must equal intentgraph-local-review-workspace",
            "validate",
        ),
        (
            "target-mutation-enabled",
            lambda workspace: enable_authority(workspace, "targetRepositoryMutation"),
            "workspace authority must equal the local review-only authority boundary",
            "validate",
        ),
        (
            "automatic-code-application-enabled",
            lambda workspace: enable_authority(workspace, "automaticCodeApplication"),
            "workspace authority must equal the local review-only authority boundary",
            "validate",
        ),
        (
            "network-enabled",
            lambda workspace: enable_authority(workspace, "networkRequired"),
            "workspace authority must equal the local review-only authority boundary",
            "validate",
        ),
        (
            "provider-api-enabled",
            lambda workspace: enable_authority(workspace, "providerApiAllowed"),
            "workspace authority must equal the local review-only authority boundary",
            "validate",
        ),
        (
            "credential-access-enabled",
            lambda workspace: enable_authority(workspace, "credentialAccessAllowed"),
            "workspace authority must equal the local review-only authority boundary",
            "validate",
        ),
        (
            "hook-installation-enabled",
            lambda workspace: enable_authority(workspace, "hookInstallationAllowed"),
            "workspace authority must equal the local review-only authority boundary",
            "validate",
        ),
        (
            "release-publishing-enabled",
            lambda workspace: enable_authority(workspace, "releasePublishingAllowed"),
            "workspace authority must equal the local review-only authority boundary",
            "validate",
        ),
        (
            "unsupported-profile",
            lambda workspace: mutate_manifest(workspace, lambda value: value.__setitem__("profile", "unsupported")),
            "workspace profile must equal b1-typescript-rest-api-sample",
            "validate",
        ),
        (
            "wrong-logical-source-root",
            lambda workspace: mutate_manifest(
                workspace,
                lambda value: value["source"].__setitem__("logicalId", "intentgraph://wrong/profile"),
            ),
            "workspace source logicalId must equal intentgraph://profiles/b1-typescript-rest-api-sample/source",
            "validate",
        ),
        (
            "wrong-profile-proposal-logical-source-root",
            wrong_profile_proposal,
            "workspace proposal must declare the bounded logical source profile",
            "validate",
        ),
        (
            "source-path-traversal",
            lambda workspace: mutate_manifest(
                workspace,
                lambda value: value["source"].__setitem__("root", "../outside"),
            ),
            "workspace path must be relative and contained",
            "validate",
        ),
        (
            "output-outside-artifacts",
            lambda workspace: mutate_manifest(
                workspace,
                lambda value: value["outputs"].__setitem__("codeFacts", "outside/code-facts.json"),
            ),
            "workspace output codeFacts must equal artifacts/code-facts.json",
            "validate",
        ),
        (
            "stale-source-provenance",
            lambda workspace: (workspace / "source" / "src" / "model" / "todo.ts").write_text(
                (workspace / "source" / "src" / "model" / "todo.ts").read_text(encoding="utf-8") + "\nexport const staleProbe = true;\n",
                encoding="utf-8",
            ),
            "workspace source digest does not match declared provenance",
            "validate",
        ),
        (
            "missing-proposal",
            lambda workspace: (workspace / "proposals" / "p4.0-complete-todo-route.proposal.json").unlink(),
            "workspace input proposal is missing",
            "validate",
        ),
        (
            "stale-profile-proposal-baseline",
            stale_profile_proposal_baseline,
            "review step failed: validate-proposal",
            "review",
        ),
    ]
    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="intentgraph-p9.1-") as temp:
        root = Path(temp)
        baseline = root / "baseline"
        init = subprocess.run(
            [sys.executable, str(FACADE), "init-sample", "--workspace", str(baseline)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if init.returncode != 0:
            raise SystemExit(f"baseline init failed: {init.stderr}")
        baseline_validation = run(baseline)
        if baseline_validation.returncode != 0:
            raise SystemExit(f"baseline validation failed: {baseline_validation.stderr}")
        baseline_review = run(baseline, "review")
        if baseline_review.returncode != 0:
            raise SystemExit(f"baseline review failed: {baseline_review.stderr}")
        for identifier, mutate, expected_error, command in probes:
            workspace = root / identifier
            shutil.copytree(baseline, workspace)
            mutate(workspace)
            completed = run(workspace, command)
            observed = completed.returncode != 0 and expected_error in completed.stderr
            results.append(
                {
                    "id": identifier,
                    "expectedError": expected_error,
                    "command": command,
                    "exitCode": completed.returncode,
                    "stderr": completed.stderr.strip(),
                    "expectedFailureObserved": observed,
                }
            )
    report = {
        "artifactRole": "intentgraph-local-review-workspace-negative-probes-report",
        "status": "intentgraph-local-review-workspace-negative-probes-passed"
        if all(item["expectedFailureObserved"] for item in results)
        else "intentgraph-local-review-workspace-negative-probes-failed",
        "result": "pass" if all(item["expectedFailureObserved"] for item in results) else "fail",
        "profile": "b1-typescript-rest-api-sample",
        "baselineValidationPassed": True,
        "baselineReviewPassed": True,
        "probeCount": len(results),
        "probes": results,
        "authority": {
            "targetRepositoryMutation": False,
            "automaticCodeApplication": False,
            "networkRequired": False,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.out, report)
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
