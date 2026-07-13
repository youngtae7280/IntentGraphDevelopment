"""Run repeatable negative probes for guided local C# review receipts."""

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
    draft_review_receipt_from_proposal,
    initialize_project,
    validate_project_workspace,
)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def receipt_values(**changes: str) -> dict[str, str]:
    values = {
        "receipt_id": "guided-receipt",
        "proposal_id": "guided-proposal",
        "verification_requirement_id": "verification.requirement.guided-proposal",
        "evidence_requirement_id": "evidence.requirement.guided-proposal",
        "result": "reviewed-pass",
        "summary": "Reviewed the declared requirement pair without running verification or collecting execution evidence.",
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
    with tempfile.TemporaryDirectory(prefix="p9.22-guided-receipt-negative-") as temporary:
        workspace = Path(temporary) / "project"
        initialize_project(snapshot, workspace, "guided-receipt-probe-project", "Guided receipt negative probes")
        before_state, before_manifest, _, before_data = validate_project_workspace(workspace)
        code_fact_id = next(
            fact["id"]
            for fact in before_data["facts"]["facts"]
            if isinstance(fact, dict) and fact.get("kind") == "method"
        )
        add_work_request(workspace, "guided-work", "Guided work", "Record a local mapped review proposal.")
        add_mapping_candidate(workspace, "guided-work", [code_fact_id], "Selected for guided review receipt validation.")
        draft_change_proposal_from_mapping(
            workspace,
            proposal_id="guided-proposal",
            work_id="guided-work",
            title="Guided review proposal",
            summary="Record one bounded review proposal before a guided receipt.",
            verification_kind="local-review",
            verification_summary="Review the mapped code facts before any source action.",
            evidence_kind="review-note",
            evidence_summary="Record a later review note without claiming execution evidence.",
        )

        probes = [
            probe(
                "rejects-invalid-guided-receipt-id",
                "guided review receipt id must be a stable lowercase identifier",
                lambda: draft_review_receipt_from_proposal(workspace, **receipt_values(receipt_id="Bad")),
            ),
            probe(
                "rejects-unknown-guided-receipt-proposal",
                "must reference a known change proposal",
                lambda: draft_review_receipt_from_proposal(workspace, **receipt_values(receipt_id="unknown-proposal-receipt", proposal_id="missing-proposal")),
            ),
            probe(
                "rejects-invalid-guided-receipt-requirement",
                "requirement references are invalid",
                lambda: draft_review_receipt_from_proposal(workspace, **receipt_values(receipt_id="missing-requirement-receipt", verification_requirement_id="verification.requirement.missing")),
            ),
            probe(
                "rejects-blank-guided-receipt-summary",
                "guided review receipt fields must be non-blank strings",
                lambda: draft_review_receipt_from_proposal(workspace, **receipt_values(receipt_id="blank-receipt", summary="   ")),
            ),
            probe(
                "rejects-unsafe-guided-receipt-path",
                "must not persist a physical path",
                lambda: draft_review_receipt_from_proposal(workspace, **receipt_values(receipt_id="unsafe-receipt", summary="C:\\unsafe")),
            ),
            probe(
                "rejects-invalid-guided-receipt-result",
                "guided review receipt result is invalid",
                lambda: draft_review_receipt_from_proposal(workspace, **receipt_values(receipt_id="invalid-result-receipt", result="reviewed")),
            ),
        ]
        positive = draft_review_receipt_from_proposal(workspace, **receipt_values())
        probes.append(
            probe(
                "rejects-duplicate-guided-receipt-pair",
                "already exists for the proposal requirement pair",
                lambda: draft_review_receipt_from_proposal(workspace, **receipt_values(receipt_id="second-guided-receipt")),
            )
        )
        after_state, after_manifest, _, _ = validate_project_workspace(workspace)
        passed = all(item["expectedFailureObserved"] for item in probes)
        report = {
            "artifactRole": "intentgraph-experimental-csharp-guided-receipt-negative-probes-report",
            "status": "intentgraph-experimental-csharp-guided-receipt-negative-probes-" + ("pass" if passed else "fail"),
            "scope": "p9.22-guided-review-receipt-boundary",
            "result": "pass" if passed else "fail",
            "probeCount": len(probes),
            "probes": probes,
            "positiveBaseline": {
                "result": positive["result"],
                "receiptId": positive["receiptId"],
                "guidedReviewReceipt": positive["guidedReviewReceipt"],
                "resultStatus": positive["resultStatus"],
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
