"""Run repeatable negative probes for guided local C# review proposals."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any, Callable

from experimental_csharp_project import (
    ProjectWorkspaceError,
    add_mapping_candidate,
    add_work_request,
    draft_change_proposal_from_mapping,
    initialize_project,
    validate_project_workspace,
)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def draft_values(**changes: str) -> dict[str, str]:
    values = {
        "proposal_id": "guided-proposal",
        "work_id": "guided-work",
        "title": "Guided review proposal",
        "summary": "Record a bounded review proposal from the declared local mapping.",
        "verification_kind": "local-review",
        "verification_summary": "Review the mapped code facts before any source action.",
        "evidence_kind": "review-note",
        "evidence_summary": "Record a later review note without claiming execution evidence.",
    }
    values.update(changes)
    return values


def probe(identifier: str, expected: str, operation: Callable[[], Any]) -> dict[str, Any]:
    try:
        operation()
    except ProjectWorkspaceError as error:
        return {"id": identifier, "expectedFailureObserved": expected in str(error), "error": str(error)}
    return {"id": identifier, "expectedFailureObserved": False, "error": "operation unexpectedly succeeded"}


def run(snapshot: Path, output: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="p9.21-guided-proposal-negative-") as temporary:
        workspace = Path(temporary) / "project"
        initialize_project(snapshot, workspace, "guided-probe-project", "Guided proposal negative probes")
        before_state, before_manifest, _, before_data = validate_project_workspace(workspace)
        code_fact_id = next(
            fact["id"]
            for fact in before_data["facts"]["facts"]
            if isinstance(fact, dict) and fact.get("kind") == "method"
        )
        add_work_request(workspace, "guided-work", "Guided work", "Record a local mapped review proposal.")
        add_mapping_candidate(workspace, "guided-work", [code_fact_id], "Selected for guided review proposal validation.")
        add_work_request(workspace, "unmapped-work", "Unmapped work", "Exercise missing mapping rejection.")

        probes = [
            probe(
                "rejects-invalid-guided-proposal-id",
                "guided review proposal id must be a stable lowercase identifier",
                lambda: draft_change_proposal_from_mapping(workspace, **draft_values(proposal_id="Bad")),
            ),
            probe(
                "rejects-unknown-guided-work",
                "guided review proposal work item does not exist",
                lambda: draft_change_proposal_from_mapping(workspace, **draft_values(proposal_id="unknown-work-proposal", work_id="missing-work")),
            ),
            probe(
                "rejects-unmapped-guided-work",
                "guided review proposal requires a declared mapping candidate",
                lambda: draft_change_proposal_from_mapping(workspace, **draft_values(proposal_id="unmapped-work-proposal", work_id="unmapped-work")),
            ),
            probe(
                "rejects-blank-guided-summary",
                "guided review proposal fields must be non-blank strings",
                lambda: draft_change_proposal_from_mapping(workspace, **draft_values(proposal_id="blank-summary-proposal", summary="   ")),
            ),
            probe(
                "rejects-unsafe-guided-path",
                "must not persist a physical path",
                lambda: draft_change_proposal_from_mapping(workspace, **draft_values(proposal_id="unsafe-title-proposal", title="C:\\unsafe")),
            ),
            probe(
                "rejects-invalid-guided-verification-kind",
                "guided review proposal verification kind must be a stable lowercase identifier",
                lambda: draft_change_proposal_from_mapping(workspace, **draft_values(proposal_id="invalid-kind-proposal", verification_kind="LocalReview")),
            ),
        ]
        positive = draft_change_proposal_from_mapping(workspace, **draft_values())
        probes.append(
            probe(
                "rejects-duplicate-guided-proposal-work",
                "already has an active change proposal",
                lambda: draft_change_proposal_from_mapping(workspace, **draft_values(proposal_id="second-guided-proposal")),
            )
        )
        after_state, after_manifest, _, _ = validate_project_workspace(workspace)
        report = {
            "artifactRole": "intentgraph-experimental-csharp-guided-proposal-negative-probes-report",
            "status": "intentgraph-experimental-csharp-guided-proposal-negative-probes-" + ("pass" if all(item["expectedFailureObserved"] for item in probes) else "fail"),
            "scope": "p9.21-guided-review-proposal-boundary",
            "result": "pass" if all(item["expectedFailureObserved"] for item in probes) else "fail",
            "probeCount": len(probes),
            "probes": probes,
            "positiveBaseline": {
                "result": positive["result"],
                "proposalId": positive["proposalId"],
                "guidedReviewProposal": positive["guidedReviewProposal"],
                "codeDiffCount": positive["codeDiffCount"],
            },
            "snapshotProvenanceUnchanged": before_manifest["source"] == after_manifest["source"] and before_state["project"] == after_state["project"],
            "targetRepositoryMutation": False,
            "automaticCodeApplication": False,
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
