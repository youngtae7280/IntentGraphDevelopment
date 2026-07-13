"""Run repeatable negative probes for durable C# project work-stage revisions."""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable

from experimental_csharp_project import (
    PROJECT_FILE,
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


def mutate_probe(
    root: Path,
    baseline_workspace: Path,
    baseline_state: dict[str, Any],
    identifier: str,
    expected: str,
    mutation: Callable[[dict[str, Any]], None],
) -> dict[str, Any]:
    workspace = root / identifier
    shutil.copytree(baseline_workspace, workspace)
    state = copy.deepcopy(baseline_state)
    mutation(state)
    write_json(workspace / PROJECT_FILE, state)
    try:
        validate_project_workspace(workspace)
    except ProjectWorkspaceError as error:
        return {"id": identifier, "expectedFailureObserved": expected in str(error), "error": str(error)}
    return {"id": identifier, "expectedFailureObserved": False, "error": "mutated revision unexpectedly validated"}


def run(snapshot: Path, output: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="p9.25-work-stage-revision-negative-") as temporary:
        root = Path(temporary)
        workspace = root / "baseline"
        initialize_project(snapshot, workspace, "revision-probe-project", "Work stage revision probes")
        _, before_manifest, _, before_data = validate_project_workspace(workspace)
        code_fact_id = next(
            fact["id"]
            for fact in before_data["facts"]["facts"]
            if isinstance(fact, dict) and fact.get("kind") == "method"
        )
        add_work_request(workspace, "revision-work", "Revision work", "Record a durable staged work history.")
        add_work_request(workspace, "interleaved-work", "Interleaved work", "Prove global revision ordering across work items.")
        add_mapping_candidate(workspace, "revision-work", [code_fact_id], "Map one local method fact for revision validation.")
        proposal = draft_change_proposal_from_mapping(
            workspace,
            proposal_id="revision-proposal",
            work_id="revision-work",
            title="Revision proposal",
            summary="Record a non-applied proposal for revision integrity probes.",
            verification_kind="local-review",
            verification_summary="Review the mapping before any source action.",
            evidence_kind="review-note",
            evidence_summary="Record review evidence only through a later boundary.",
        )
        draft_review_receipt_from_proposal(
            workspace,
            receipt_id="revision-receipt",
            proposal_id="revision-proposal",
            verification_requirement_id="verification.requirement.revision-proposal",
            evidence_requirement_id="evidence.requirement.revision-proposal",
            result="reviewed-pass",
            summary="Reviewed the non-applied proposal without executing verification.",
        )
        baseline_state, after_manifest, _, baseline_data = validate_project_workspace(workspace)
        revisions = baseline_state["workStageRevisions"]
        if len(revisions) != 5 or proposal["revisionId"] != revisions[3]["id"]:
            raise RuntimeError("positive work-stage revision baseline is incomplete")

        probes = [
            mutate_probe(
                root,
                workspace,
                baseline_state,
                "rejects-missing-revision-field",
                "work stage revision fields are invalid",
                lambda state: state["workStageRevisions"][0].pop("authority"),
            ),
            mutate_probe(
                root,
                workspace,
                baseline_state,
                "rejects-unknown-stage-kind",
                "work stage revision lifecycle reference is invalid",
                lambda state: state["workStageRevisions"][0].update(stageKind="source-applied"),
            ),
            mutate_probe(
                root,
                workspace,
                baseline_state,
                "rejects-noncontiguous-work-sequence",
                "work stage revision sequence must be contiguous",
                lambda state: state["workStageRevisions"][2].update(sequence=8),
            ),
            mutate_probe(
                root,
                workspace,
                baseline_state,
                "rejects-broken-work-predecessor",
                "work stage revision predecessor chain is invalid",
                lambda state: state["workStageRevisions"][2].update(predecessorRevisionId=None),
            ),
            mutate_probe(
                root,
                workspace,
                baseline_state,
                "rejects-broken-global-digest-chain",
                "work stage revision global before/after chain is invalid",
                lambda state: state["workStageRevisions"][2].update(beforeProjectStateDigest="sha256:" + "0" * 64),
            ),
            mutate_probe(
                root,
                workspace,
                baseline_state,
                "rejects-latest-state-digest-mismatch",
                "latest work stage revision does not match current work lifecycle state",
                lambda state: state["workStageRevisions"][-1].update(afterProjectStateDigest="sha256:" + "1" * 64),
            ),
            mutate_probe(
                root,
                workspace,
                baseline_state,
                "rejects-unknown-record-reference",
                "work stage revision record references are invalid",
                lambda state: state["workStageRevisions"][0].update(recordIds=["history.missing"]),
            ),
            mutate_probe(
                root,
                workspace,
                baseline_state,
                "rejects-unknown-code-diff-reference",
                "work stage revision code diff references are invalid",
                lambda state: state["workStageRevisions"][3].update(codeDiffIds=["diff.missing"]),
            ),
            mutate_probe(
                root,
                workspace,
                baseline_state,
                "rejects-duplicate-graph-delta-identifiers",
                "work stage revision graph delta identifiers are invalid",
                lambda state: state["workStageRevisions"][0]["graphDelta"].update(addedNodeIds=["intent.revision-work", "intent.revision-work"]),
            ),
            mutate_probe(
                root,
                workspace,
                baseline_state,
                "rejects-authority-promotion",
                "work stage revision authority is invalid",
                lambda state: state["workStageRevisions"][0]["authority"].update(automaticCodeApplication=True),
            ),
        ]
        passed = all(item["expectedFailureObserved"] for item in probes)
        report = {
            "artifactRole": "intentgraph-experimental-csharp-work-stage-revision-negative-probes-report",
            "status": "intentgraph-experimental-csharp-work-stage-revision-negative-probes-" + ("pass" if passed else "fail"),
            "scope": "p9.25-durable-work-stage-revision-boundary",
            "result": "pass" if passed else "fail",
            "probeCount": len(probes),
            "probes": probes,
            "positiveBaseline": {
                "workItemCount": len(baseline_state["workItems"]),
                "revisionCount": len(revisions),
                "interleavedWorkItems": True,
                "globalDigestChain": all(
                    revision["beforeProjectStateDigest"] == revisions[index - 1]["afterProjectStateDigest"]
                    for index, revision in enumerate(revisions)
                    if index
                ),
                "projectedDurableRevisionCount": len(baseline_data["workStageRevisions"]),
            },
            "snapshotProvenanceUnchanged": before_manifest["source"] == after_manifest["source"],
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
