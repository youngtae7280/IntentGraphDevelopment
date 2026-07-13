"""Run repeatable negative probes for P9.14 non-applied C# change proposals."""

from __future__ import annotations

import argparse
import copy
import json
import tempfile
from pathlib import Path
from typing import Any, Callable

from experimental_csharp_project import (
    PROJECT_AUTHORITY,
    PROPOSAL_AUTHORITY,
    ProjectWorkspaceError,
    add_change_proposal,
    add_mapping_candidate,
    add_work_request,
    initialize_project,
    read_json,
    write_json,
)


def write_report(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def prepare(snapshot: Path, proposal: dict[str, Any], root: Path) -> Path:
    workspace = root / "project"
    initialize_project(snapshot, workspace, "proposal-negative-project", "Proposal negative project")
    add_work_request(workspace, proposal["workItemId"], proposal["title"], proposal["summary"])
    add_mapping_candidate(workspace, proposal["workItemId"], proposal["graphDelta"]["changedNodeIds"], "Declared fixture mapping candidate for proposal validation.")
    return workspace


def run_probe(snapshot: Path, original: dict[str, Any], probe_id: str, mutate: Callable[[dict[str, Any]], None], expected: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="p9.14-negative-") as temporary:
        root = Path(temporary)
        workspace = prepare(snapshot, original, root)
        proposal = copy.deepcopy(original)
        mutate(proposal)
        proposal_path = root / "proposal.json"
        write_json(proposal_path, proposal)
        try:
            add_change_proposal(workspace, proposal_path)
        except ProjectWorkspaceError as error:
            message = str(error)
            return {"id": probe_id, "expectedError": expected, "actualError": message, "expectedFailureObserved": expected in message}
        return {"id": probe_id, "expectedError": expected, "actualError": "proposal unexpectedly accepted", "expectedFailureObserved": False}


def run(snapshot: Path, proposal_path: Path, output: Path) -> dict[str, Any]:
    original = read_json(proposal_path)
    probes = [
        run_probe(snapshot, original, "wrong-proposal-role", lambda value: value.__setitem__("artifactRole", "wrong-role"), "role, schema version, or scope is invalid"),
        run_probe(snapshot, original, "applied-status-claim", lambda value: value.__setitem__("applicationStatus", "applied"), "must remain non-applied and review-required"),
        run_probe(snapshot, original, "unknown-changed-code-fact", lambda value: value["graphDelta"].__setitem__("changedNodeIds", ["csharp.method.missing"]), "changed node references are invalid"),
        run_probe(snapshot, original, "stale-code-diff-digest", lambda value: value["codeDiffs"][0].__setitem__("beforeSourceDigest", "sha256:0000"), "provenance does not match"),
        run_probe(snapshot, original, "unsafe-proposal-authority", lambda value: value.__setitem__("authority", {**PROPOSAL_AUTHORITY, "targetRepositoryMutation": True}), "authority must remain non-applying"),
        run_probe(snapshot, original, "invalid-unified-diff", lambda value: value["codeDiffs"][0].__setitem__("unifiedDiff", "not a diff"), "unified diff is invalid"),
        run_probe(snapshot, original, "unresolved-added-edge", lambda value: value["graphDelta"]["addedEdges"][0].__setitem__("target", "missing.node"), "added edge endpoints or kind are invalid"),
        run_probe(snapshot, original, "missing-verification-requirements", lambda value: value.__setitem__("verificationRequirements", []), "verificationRequirements must contain at least one requirement"),
    ]
    result = "pass" if all(item["expectedFailureObserved"] for item in probes) else "fail"
    report = {
        "artifactRole": "intentgraph-experimental-csharp-change-proposal-negative-probes-report",
        "status": "intentgraph-experimental-csharp-change-proposal-negative-probes-" + result,
        "scope": "p9.14-experimental-csharp-change-proposal",
        "result": result,
        "probeCount": len(probes),
        "probes": probes,
        "targetRepositoryMutation": False,
        "automaticCodeApplication": False,
        "networkRequired": False,
        "projectAuthority": PROJECT_AUTHORITY,
        "proposalAuthority": PROPOSAL_AUTHORITY,
    }
    write_report(output, report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-workspace", required=True, type=Path)
    parser.add_argument("--proposal", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = run(args.snapshot_workspace.resolve(), args.proposal.resolve(), args.out.resolve())
    except ProjectWorkspaceError as error:
        print(f"error: {error}")
        return 2
    print(json.dumps({"result": report["result"], "probeCount": report["probeCount"]}, ensure_ascii=True))
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
