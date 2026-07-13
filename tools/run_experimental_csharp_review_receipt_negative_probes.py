"""Run repeatable negative probes for P9.20 non-executing C# review receipts."""

from __future__ import annotations

import argparse
import copy
import json
import tempfile
from pathlib import Path
from typing import Any, Callable

from experimental_csharp_project import (
    PROJECT_AUTHORITY,
    PROJECT_SCHEMA_VERSION,
    REVIEW_RECEIPT_AUTHORITY,
    REVIEW_RECEIPT_ROLE,
    REVIEW_RECEIPT_SCOPE,
    ProjectWorkspaceError,
    add_change_proposal,
    add_mapping_candidate,
    add_review_receipt_document,
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
    initialize_project(snapshot, workspace, "receipt-negative-project", "Review receipt negative project")
    add_work_request(workspace, proposal["workItemId"], proposal["title"], proposal["summary"])
    add_mapping_candidate(workspace, proposal["workItemId"], proposal["graphDelta"]["changedNodeIds"], "Declared fixture mapping candidate for review receipt validation.")
    proposal_path = root / "proposal.json"
    write_json(proposal_path, proposal)
    add_change_proposal(workspace, proposal_path)
    return workspace


def base_receipt(proposal: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifactRole": REVIEW_RECEIPT_ROLE,
        "schemaVersion": PROJECT_SCHEMA_VERSION,
        "scope": REVIEW_RECEIPT_SCOPE,
        "id": "receipt-negative-check",
        "proposalId": proposal["id"],
        "verificationRequirementId": proposal["verificationRequirements"][0]["id"],
        "evidenceRequirementId": proposal["evidenceRequirements"][0]["id"],
        "result": "reviewed-pass",
        "reviewScope": ["evidence-requirement", "proposal", "verification-requirement"],
        "summary": "Review only the declared proposal requirement pair without execution or approval.",
        "authority": REVIEW_RECEIPT_AUTHORITY,
    }


def run_probe(snapshot: Path, proposal: dict[str, Any], probe_id: str, mutate: Callable[[dict[str, Any]], None], expected: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="p9.20-negative-") as temporary:
        workspace = prepare(snapshot, proposal, Path(temporary))
        receipt = base_receipt(proposal)
        mutate(receipt)
        try:
            add_review_receipt_document(workspace, receipt)
        except ProjectWorkspaceError as error:
            message = str(error)
            return {"id": probe_id, "expectedError": expected, "actualError": message, "expectedFailureObserved": expected in message}
        return {"id": probe_id, "expectedError": expected, "actualError": "review receipt unexpectedly accepted", "expectedFailureObserved": False}


def duplicate_probe(snapshot: Path, proposal: dict[str, Any]) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="p9.20-duplicate-") as temporary:
        workspace = prepare(snapshot, proposal, Path(temporary))
        receipt = base_receipt(proposal)
        add_review_receipt_document(workspace, receipt)
        duplicate = copy.deepcopy(receipt)
        duplicate["id"] = "receipt-negative-duplicate"
        try:
            add_review_receipt_document(workspace, duplicate)
        except ProjectWorkspaceError as error:
            message = str(error)
            return {"id": "duplicate-requirement-pair", "expectedError": "already exists for the proposal requirement pair", "actualError": message, "expectedFailureObserved": "already exists for the proposal requirement pair" in message}
        return {"id": "duplicate-requirement-pair", "expectedError": "already exists for the proposal requirement pair", "actualError": "duplicate review receipt unexpectedly accepted", "expectedFailureObserved": False}


def run(snapshot: Path, proposal_path: Path, output: Path) -> dict[str, Any]:
    proposal = read_json(proposal_path)
    probes = [
        run_probe(snapshot, proposal, "wrong-receipt-role", lambda value: value.__setitem__("artifactRole", "wrong-role"), "role, schema version, or scope is invalid"),
        run_probe(snapshot, proposal, "unknown-proposal", lambda value: value.__setitem__("proposalId", "missing-proposal"), "must reference a known change proposal"),
        run_probe(snapshot, proposal, "unknown-verification-requirement", lambda value: value.__setitem__("verificationRequirementId", "verification.requirement.missing"), "requirement references are invalid"),
        run_probe(snapshot, proposal, "invalid-result", lambda value: value.__setitem__("result", "pass"), "review receipt result is invalid"),
        run_probe(snapshot, proposal, "missing-proposal-review-scope", lambda value: value.__setitem__("reviewScope", ["evidence-requirement"]), "review receipt scope is invalid"),
        run_probe(snapshot, proposal, "executing-receipt-authority", lambda value: value.__setitem__("authority", {**REVIEW_RECEIPT_AUTHORITY, "verificationExecution": True}), "authority must remain non-executing and non-approving"),
        run_probe(snapshot, proposal, "source-text-in-receipt", lambda value: value.__setitem__("sourceText", "forbidden"), "sourceText is not permitted"),
        duplicate_probe(snapshot, proposal),
    ]
    result = "pass" if all(item["expectedFailureObserved"] for item in probes) else "fail"
    report = {
        "artifactRole": "intentgraph-experimental-csharp-review-receipt-negative-probes-report",
        "status": "intentgraph-experimental-csharp-review-receipt-negative-probes-" + result,
        "scope": "p9.20-experimental-csharp-review-receipt",
        "result": result,
        "probeCount": len(probes),
        "probes": probes,
        "targetRepositoryMutation": False,
        "verificationExecution": False,
        "evidenceExecution": False,
        "automaticCodeApplication": False,
        "projectAuthority": PROJECT_AUTHORITY,
        "reviewReceiptAuthority": REVIEW_RECEIPT_AUTHORITY,
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
