"""Run repeatable zero-write negative probes for the C# local-symbol relation overlay."""

from __future__ import annotations

import argparse
import json
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

from experimental_csharp_project import (
    ProjectWorkspaceError,
    initialize_project,
    record_semantic_relation_overlay,
    validate_project_workspace,
)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def valid_overlay(facts: dict[str, Any]) -> dict[str, Any]:
    local_facts = [fact for fact in facts["facts"] if isinstance(fact, dict) and fact.get("kind") in {"method", "constructor"}]
    return {
        "artifactRole": "intentgraph-experimental-csharp-semantic-relation-overlay",
        "status": "intentgraph-experimental-csharp-semantic-relation-overlay-extracted",
        "scope": "experimental-csharp-semantic-relation-overlay-readonly",
        "profileId": facts["profileId"],
        "sourceRoot": facts["sourceRoot"],
        "sourceRootKind": facts["sourceRootKind"],
        "extractor": {
            "id": "tools/csharp_semantic_overlay_probe/Program.cs",
            "version": "test-0.1.0",
            "mode": "roslyn-semantic-overlay-local-symbols",
            "deterministic": True,
            "semanticResolution": True,
            "sourceBuildAllowed": False,
            "broadExtractor": False,
        },
        "sourceDigests": facts["sourceDigests"],
        "diagnostics": {"compilationErrorCount": 0, "compilationWarningCount": 0, "localDeclarationCount": len(facts["facts"])},
        "relations": [{"id": "resolved.calls.negative-probe", "kind": "calls", "from": local_facts[0]["id"], "to": local_facts[1]["id"], "confidence": "resolved-local-symbol"}],
        "authority": {
            "sourceReadFromSnapshotOnly": True,
            "targetRepositoryMutation": False,
            "targetBuildExecuted": False,
            "targetRestoreExecuted": False,
            "networkRequired": False,
            "credentialAccessAllowed": False,
            "graphMutationApplied": False,
        },
    }


def run(snapshot_workspace: Path, output: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="p9.23-semantic-relations-") as temporary:
        root = Path(temporary)
        workspace = root / "project"
        initialize_project(snapshot_workspace, workspace, "semantic-relation-probe", "Semantic relation probe")
        _, _, _, data = validate_project_workspace(workspace)
        baseline = valid_overlay(data["facts"])
        project_file = workspace / "intentgraph.project.json"
        probes: list[tuple[str, dict[str, Any], str]] = []
        unsafe_authority = deepcopy(baseline)
        unsafe_authority["authority"]["targetBuildExecuted"] = True
        probes.append(("rejects-target-build-claim", unsafe_authority, "authority boundary"))
        missing_endpoint = deepcopy(baseline)
        missing_endpoint["relations"][0]["to"] = "csharp.method.not-present"
        probes.append(("rejects-unknown-code-fact-endpoint", missing_endpoint, "relation is invalid"))
        unsafe_text = deepcopy(baseline)
        unsafe_text["sourceText"] = "class Unsafe {}"
        probes.append(("rejects-persisted-source-text", unsafe_text, "not permitted"))
        wrong_extractor = deepcopy(baseline)
        wrong_extractor["extractor"]["sourceBuildAllowed"] = True
        probes.append(("rejects-source-build-capability", wrong_extractor, "extractor boundary"))
        source_digest_mismatch = deepcopy(baseline)
        source_digest_mismatch["sourceDigests"] = {**source_digest_mismatch["sourceDigests"], next(iter(source_digest_mismatch["sourceDigests"])): "sha256:" + "0" * 64}
        probes.append(("rejects-source-digest-mismatch", source_digest_mismatch, "source identity"))
        results: list[dict[str, Any]] = []
        for identifier, invalid, expected in probes:
            path = root / f"{identifier}.json"
            write_json(path, invalid)
            before = project_file.read_bytes()
            try:
                record_semantic_relation_overlay(workspace, path)
            except ProjectWorkspaceError as error:
                observed = str(error)
                passed = expected in observed and project_file.read_bytes() == before
            else:
                observed = "accepted invalid semantic relation overlay"
                passed = False
            results.append({"id": identifier, "expectedError": expected, "observedError": observed, "zeroWrite": project_file.read_bytes() == before, "passed": passed})
    report = {
        "artifactRole": "intentgraph-experimental-csharp-semantic-relation-overlay-negative-probes-report",
        "status": "intentgraph-experimental-csharp-semantic-relation-overlay-negative-probes-" + ("pass" if all(item["passed"] for item in results) else "fail"),
        "scope": "p9.23-readonly-semantic-relation-overlay-negative-probes",
        "result": "pass" if all(item["passed"] for item in results) else "fail",
        "probeCount": len(results),
        "probes": results,
        "targetRepositoryMutation": False,
        "targetBuildExecuted": False,
        "networkRequired": False,
    }
    write_json(output, report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-workspace", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args.snapshot_workspace.resolve(), args.out.resolve())
    print(json.dumps({"result": report["result"], "probeCount": report["probeCount"]}, ensure_ascii=True))
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
