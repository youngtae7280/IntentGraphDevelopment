"""Run a loopback-only smoke test for the interactive C# project workbench server."""

from __future__ import annotations

import argparse
import json
import tempfile
import threading
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from experimental_csharp_project import (
    PROJECT_SCHEMA_VERSION,
    PROPOSAL_AUTHORITY,
    PROPOSAL_ROLE,
    PROPOSAL_SCOPE,
    PROPOSAL_STATUS,
    REVIEW_RECEIPT_AUTHORITY,
    REVIEW_RECEIPT_ROLE,
    REVIEW_RECEIPT_SCOPE,
    initialize_project,
    record_semantic_relation_overlay,
    validate_project_workspace,
)
from serve_experimental_csharp_project_workbench import LocalWorkbenchServerError, make_server


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def request(url: str, *, method: str = "GET", body: dict[str, Any] | None = None) -> tuple[int, bytes, dict[str, str]]:
    data = None if body is None else json.dumps(body, ensure_ascii=True).encode("utf-8")
    headers = {} if data is None else {"Content-Type": "application/json"}
    response = urlopen(Request(url, data=data, headers=headers, method=method), timeout=15)
    with response:
        return response.status, response.read(), dict(response.headers.items())


def server_proposal(code_fact_id: str) -> dict[str, Any]:
    return {
        "artifactRole": PROPOSAL_ROLE,
        "schemaVersion": PROJECT_SCHEMA_VERSION,
        "scope": PROPOSAL_SCOPE,
        "id": "server-proposal",
        "workItemId": "server-request",
        "mappingId": "mapping.server-request.candidate",
        "title": "Server-recorded review proposal",
        "summary": "Exercise the local review-only proposal intake without editing source code.",
        "applicationStatus": PROPOSAL_STATUS,
        "graphDelta": {
            "addedNodes": [
                {
                    "id": "verification.server-proposal",
                    "category": "verification",
                    "label": "Server proposal verification requirement",
                    "details": {"kind": "server-smoke", "result": "required-not-run", "summary": "A local review-only verification requirement."},
                }
            ],
            "changedNodeIds": [code_fact_id],
            "addedEdges": [
                {
                    "id": "edge.server-proposal.verifies",
                    "kind": "verifies",
                    "source": "intent.server-request",
                    "target": "verification.server-proposal",
                    "details": {"status": "required-not-run"},
                }
            ],
        },
        "codeDiffs": [],
        "verificationRequirements": [{"id": "verification.requirement.server-proposal", "kind": "server-smoke", "summary": "Review the proposal before any source action."}],
        "evidenceRequirements": [{"id": "evidence.requirement.server-proposal", "kind": "server-smoke", "summary": "Collect evidence only through a later authorized boundary."}],
        "authority": PROPOSAL_AUTHORITY,
    }


def server_guided_proposal(code_fact_id: str, unified_diff: str) -> dict[str, Any]:
    return {
        "proposalId": "server-proposal",
        "workId": "server-request",
        "title": "Server-recorded review proposal",
        "summary": "Exercise the local guided proposal intake without editing source code.",
        "verificationKind": "server-review",
        "verificationSummary": "Review the declared mapping before any source action.",
        "evidenceKind": "server-evidence",
        "evidenceSummary": "Collect evidence only through a later authorized boundary.",
        "codeDiffs": [{"codeFactId": code_fact_id, "unifiedDiff": unified_diff}],
    }


def server_receipt() -> dict[str, Any]:
    return {
        "artifactRole": REVIEW_RECEIPT_ROLE,
        "schemaVersion": PROJECT_SCHEMA_VERSION,
        "scope": REVIEW_RECEIPT_SCOPE,
        "id": "server-review-receipt",
        "proposalId": "server-proposal",
        "verificationRequirementId": "verification.requirement.server-proposal",
        "evidenceRequirementId": "evidence.requirement.server-proposal",
        "result": "reviewed-pass",
        "reviewScope": ["evidence-requirement", "proposal", "verification-requirement"],
        "summary": "Reviewed the non-applied server proposal requirements without running evidence collection.",
        "authority": REVIEW_RECEIPT_AUTHORITY,
    }


def server_guided_receipt() -> dict[str, str]:
    return {
        "receiptId": "server-review-receipt",
        "proposalId": "server-proposal",
        "verificationRequirementId": "verification.requirement.server-proposal",
        "evidenceRequirementId": "evidence.requirement.server-proposal",
        "result": "reviewed-pass",
        "summary": "Reviewed the non-applied server proposal requirements without running evidence collection.",
    }


def run(snapshot: Path, output: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="p9.15-server-smoke-") as temporary:
        root = Path(temporary)
        workspace = root / "project"
        initialize_project(snapshot, workspace, "server-smoke-project", "Server smoke project")
        before_state, before_manifest, _, before_data = validate_project_workspace(workspace)
        facts = before_data["facts"]
        local_facts = [fact for fact in facts["facts"] if isinstance(fact, dict) and fact.get("kind") in {"method", "constructor"}]
        semantic_overlay = {
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
            "relations": [{"id": "resolved.calls.server-smoke", "kind": "calls", "from": local_facts[0]["id"], "to": local_facts[1]["id"], "confidence": "resolved-local-symbol"}],
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
        overlay_path = root / "semantic-relation-overlay.json"
        write_json(overlay_path, semantic_overlay)
        recorded_overlay = record_semantic_relation_overlay(workspace, overlay_path)
        if recorded_overlay["result"] != "pass":
            raise RuntimeError("server smoke could not record its synthetic semantic relation overlay")
        code_fact = next(
            fact
            for fact in before_data["facts"]["facts"]
            if isinstance(fact, dict) and fact.get("kind") == "method"
        )
        code_fact_id = code_fact["id"]
        source_line_number = code_fact["sourceLocation"]["lineStart"]
        source_line = (workspace / "snapshot" / "source" / Path(code_fact["sourceFile"])).read_text(encoding="utf-8-sig").splitlines()[source_line_number - 1]
        guided_unified_diff = f"@@ -{source_line_number},1 +{source_line_number},2 @@\n+// IGD review-only proposed change.\n {source_line}"
        server = make_server(workspace, "127.0.0.1", 0)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        host, port = server.server_address[:2]
        base_url = f"http://{host}:{port}"
        probes: list[dict[str, Any]] = []
        try:
            status, html, headers = request(base_url + "/")
            probes.append({"id": "serves-deferred-interactive-html", "passed": status == 200 and len(html) < 120000 and b"newWorkTrigger" in html and b"mapCodeTrigger" in html and b"draftProposalTrigger" in html and b"draftCodeDiffList" in html and b"proposalCodeFacts" in html and b"Import proposal JSON" in html and b"draftReceiptTrigger" in html and b"importReceiptTrigger" in html and b"modeBadge" in html and b"previousWork" in html and b"nextWork" in html and b"previousStage" in html and b"nextStage" in html and b"workPosition" in html and b"stagePosition" in html and b"workSearch" in html and b"workStatusFilter" in html and b"workWindowSummary" in html and b"workListRenderLimit=60" in html and b"maxZoom:100" in html and b"deepZoomFloors" in html and b"precision-" in html and b"makeSpectralObsidianNodeMaterialTexture" in html and b"edge:selected" in html and b"zoomReadout" in html and b"highlightedEdgeIds" in html and b"focusStage" in html and b"workStageTimeline" in html and b"__intentGraphLoadProjection" in html and b"/api/revision-head" in html and b"checkForProjectUpdate" in html and b"/api/work-requests" in html and b"/api/mapping-candidates" in html and b"/api/change-proposals" in html and b"/api/draft-change-proposals" in html and b"/api/review-receipts" in html and b"/api/draft-review-receipts" in html and b"spiralPoint" in html and b"local-symbol links" in html and b"completeGraph" in html and b"semanticEdgeIds" in html and b"importantCodeLabelIds" in html and b"show-on-demand-label" in html and b"updateViewportScale" in html and b"zoomStyleBand" in html and b"codeNodes.addClass('show-code-label')" not in html and b"edge.low-detail',style:{'display':'none'}" not in html and b"search-match" in html and b"selection-neighbor" in html and b"visibilityUpdates" in html and b"state.cy.destroy" not in html and b"name:'cose'" not in html and headers.get("Content-Security-Policy") is not None})
            status, projection_bytes, _ = request(base_url + "/api/projection")
            initial_projection = json.loads(projection_bytes)
            head_status, head_bytes, _ = request(base_url + "/api/revision-head")
            initial_head = json.loads(head_bytes)
            probes.append({"id": "serves-project-projection", "passed": status == 200 and head_status == 200 and initial_head["revisionCount"] == 0 and initial_head["workItemCount"] == 0 and initial_head["latestRevisionId"] is None and initial_head["projectStateVersion"].startswith("sha256:") and initial_projection["workflow"]["workItems"] == [] and initial_projection["workflow"]["workStageTimeline"] == [] and initial_projection["workflow"]["workStageRevisions"] == [] and initial_projection["workflow"]["timelineContract"]["durableRevisionCount"] == 0 and initial_projection["uiContract"]["allRecordedWorkItemsNavigable"] is True and initial_projection["uiContract"]["workHistorySearch"] is True and initial_projection["uiContract"]["workHistoryStatusFilter"] is True and initial_projection["uiContract"]["boundedWorkHistoryRendering"] is True and initial_projection["uiContract"]["previousNextWorkNavigation"] is True and initial_projection["uiContract"]["previousNextStageNavigation"] is True and initial_projection["uiContract"]["liveProjectionRefreshAfterMutation"] is True and initial_projection["snapshot"]["semanticRelationOverlay"]["resolvedRelationCount"] == 1 and initial_projection["graph"]["relationCounts"].get("calls") == 1 and initial_projection["graph"]["defaultView"]["id"] == "all" and set(initial_projection["graph"]["views"]["all"]["nodeIds"]) == {node["id"] for node in initial_projection["graph"]["nodes"]}})
            status, created_bytes, _ = request(base_url + "/api/work-requests", method="POST", body={"workId": "server-request", "title": "Server-recorded request", "request": "Record a local work request without editing the source project."})
            created = json.loads(created_bytes)
            probes.append({"id": "records-work-request-only-in-project-workspace", "passed": status == 201 and created["result"] == "pass" and created["workItemId"] == "server-request" and created["revisionId"].startswith("revision.server-request.1.")})
            status, updated_bytes, _ = request(base_url + "/api/projection")
            updated = json.loads(updated_bytes)
            head_status, head_bytes, _ = request(base_url + "/api/revision-head")
            updated_head = json.loads(head_bytes)
            request_stage = updated["workflow"]["workStageTimeline"][0]
            probes.append({"id": "reloads-updated-projection", "passed": status == 200 and head_status == 200 and updated_head["projectStateVersion"] != initial_head["projectStateVersion"] and updated_head["revisionCount"] == 1 and updated_head["latestRevisionId"] == created["revisionId"] and len(updated["workflow"]["workItems"]) == 1 and updated["workflow"]["workItems"][0]["id"] == "server-request" and [stage["kind"] for stage in updated["workflow"]["workStageTimeline"]] == ["request-recorded"] and len(updated["workflow"]["workStageRevisions"]) == 1 and request_stage["durableRevision"] is True and request_stage["revisionIds"] == [created["revisionId"]] and request_stage["beforeProjectStateDigest"].startswith("sha256:") and request_stage["afterProjectStateDigest"].startswith("sha256:")})
            status, second_created_bytes, _ = request(base_url + "/api/work-requests", method="POST", body={"workId": "server-request-two", "title": "Second server request", "request": "Prove that one HTML can retain and navigate more than one work history."})
            second_created = json.loads(second_created_bytes)
            status, two_work_projection_bytes, _ = request(base_url + "/api/projection")
            two_work_projection = json.loads(two_work_projection_bytes)
            probes.append({"id": "retains-multiple-independent-work-histories", "passed": status == 200 and second_created["revisionId"].startswith("revision.server-request-two.1.") and [item["id"] for item in two_work_projection["workflow"]["workItems"]] == ["server-request", "server-request-two"] and len(two_work_projection["workflow"]["workStageRevisions"]) == 2 and {stage["workItemId"] for stage in two_work_projection["workflow"]["workStageTimeline"]} == {"server-request", "server-request-two"}})
            status, mapped_bytes, _ = request(base_url + "/api/mapping-candidates", method="POST", body={"workId": "server-request", "codeFactId": code_fact_id, "rationale": "Selected from the local code graph for smoke coverage."})
            mapped = json.loads(mapped_bytes)
            probes.append({"id": "records-code-mapping-only-in-project-workspace", "passed": status == 201 and mapped["result"] == "pass" and mapped["codeFactCount"] == 1 and mapped["revisionId"].startswith("revision.server-request.2.")})
            status, mapped_projection_bytes, _ = request(base_url + "/api/projection")
            mapped_projection = json.loads(mapped_projection_bytes)
            mapping_stage = mapped_projection["workflow"]["workStageTimeline"][1]
            probes.append({"id": "reloads-mapped-projection", "passed": status == 200 and len(mapped_projection["workflow"]["mappings"]) == 1 and mapped_projection["workflow"]["mappings"][0]["codeFactIds"] == [code_fact_id] and [stage["kind"] for stage in mapped_projection["workflow"]["workStageTimeline"] if stage["workItemId"] == "server-request"] == ["request-recorded", "mapping-candidate-recorded"] and len(mapped_projection["workflow"]["workStageRevisions"]) == 3 and mapping_stage["durableRevision"] is True and mapping_stage["revisionIds"] == [mapped["revisionId"]]})
            status, proposal_bytes, _ = request(base_url + "/api/draft-change-proposals", method="POST", body=server_guided_proposal(code_fact_id, guided_unified_diff))
            proposal_result = json.loads(proposal_bytes)
            probes.append({"id": "records-diff-backed-guided-proposal-in-project-workspace", "passed": status == 201 and proposal_result["result"] == "pass" and proposal_result["proposalId"] == "server-proposal" and proposal_result["mappingId"] == "mapping.server-request.candidate" and proposal_result["revisionId"].startswith("revision.server-request.3.") and proposal_result["codeDiffCount"] == 1 and proposal_result["diffBackedGuidedProposal"] is True and proposal_result["guidedReviewProposal"] is True and proposal_result["targetRepositoryMutation"] is False})
            status, proposal_projection_bytes, _ = request(base_url + "/api/projection")
            proposal_projection = json.loads(proposal_projection_bytes)
            proposal_stages = [stage for stage in proposal_projection["workflow"]["workStageTimeline"] if stage["workItemId"] == "server-request"][2:4]
            probes.append({"id": "reloads-diff-backed-proposal-delta", "passed": status == 200 and len(proposal_projection["workflow"]["changeProposals"]) == 1 and len(proposal_projection["workflow"]["changeProposals"][0]["codeDiffs"]) == 1 and proposal_stages[0]["codeDiffs"][0]["codeFactId"] == code_fact_id and [stage["kind"] for stage in proposal_projection["workflow"]["workStageTimeline"] if stage["workItemId"] == "server-request"] == ["request-recorded", "mapping-candidate-recorded", "change-proposal-recorded", "verification-and-evidence-requirements-recorded"] and len(proposal_projection["workflow"]["workStageRevisions"]) == 4 and all(stage["durableRevision"] is True and stage["revisionIds"] == [proposal_result["revisionId"]] for stage in proposal_stages) and proposal_stages[0]["beforeProjectStateDigest"] == proposal_stages[1]["beforeProjectStateDigest"] and proposal_stages[0]["afterProjectStateDigest"] == proposal_stages[1]["afterProjectStateDigest"] and proposal_projection["changeReview"]["status"] == "review-required" and proposal_projection["snapshot"]["proposedCodeDiffFragmentsShown"] is True and proposal_projection["authority"]["targetRepositoryMutation"] is False})
            status, receipt_bytes, _ = request(base_url + "/api/draft-review-receipts", method="POST", body=server_guided_receipt())
            receipt_result = json.loads(receipt_bytes)
            probes.append({"id": "records-guided-non-executing-review-receipt", "passed": status == 201 and receipt_result["result"] == "pass" and receipt_result["receiptId"] == "server-review-receipt" and receipt_result["revisionId"].startswith("revision.server-request.4.") and receipt_result["guidedReviewReceipt"] is True and receipt_result["targetRepositoryMutation"] is False})
            status, receipt_projection_bytes, _ = request(base_url + "/api/projection")
            receipt_projection = json.loads(receipt_projection_bytes)
            receipt_stage = next(stage for stage in receipt_projection["workflow"]["workStageTimeline"] if stage["kind"] == "review-receipt-recorded")
            revisions = receipt_projection["workflow"]["workStageRevisions"]
            probes.append({"id": "reloads-review-receipt-state", "passed": status == 200 and len(receipt_projection["workflow"]["reviewReceipts"]) == 1 and [stage["kind"] for stage in receipt_projection["workflow"]["workStageTimeline"] if stage["workItemId"] == "server-request"] == ["request-recorded", "mapping-candidate-recorded", "change-proposal-recorded", "verification-and-evidence-requirements-recorded", "review-receipt-recorded"] and len(revisions) == 5 and [revision["sequence"] for revision in revisions if revision["workItemId"] == "server-request"] == [1, 2, 3, 4] and all(revision["beforeProjectStateDigest"] == revisions[index - 1]["afterProjectStateDigest"] for index, revision in enumerate(revisions) if index) and receipt_stage["durableRevision"] is True and receipt_stage["revisionIds"] == [receipt_result["revisionId"]] and any(node["id"] == "review-receipt.server-review-receipt" for node in receipt_projection["graph"]["nodes"]) and receipt_projection["workflow"]["workItems"][0]["verificationStatus"] == "review-receipt-recorded" and receipt_projection["authority"]["targetRepositoryMutation"] is False})
            try:
                request(base_url + "/api/work-requests", method="POST", body={"workId": "server-request", "title": "Duplicate", "request": "Duplicate identifier."})
            except HTTPError as error:
                duplicate = json.loads(error.read())
                probes.append({"id": "rejects-duplicate-work-id", "passed": error.code == 400 and "already exists" in duplicate.get("error", "")})
            else:
                probes.append({"id": "rejects-duplicate-work-id", "passed": False})
            try:
                request(base_url + "/api/mapping-candidates", method="POST", body={"workId": "server-request", "codeFactId": code_fact_id, "rationale": "Duplicate fact."})
            except HTTPError as error:
                duplicate_mapping = json.loads(error.read())
                probes.append({"id": "rejects-duplicate-code-mapping", "passed": error.code == 400 and "already contains" in duplicate_mapping.get("error", "")})
            else:
                probes.append({"id": "rejects-duplicate-code-mapping", "passed": False})
            invalid_proposal = server_proposal(code_fact_id)
            invalid_proposal["applicationStatus"] = "applied"
            try:
                request(base_url + "/api/change-proposals", method="POST", body={"proposal": invalid_proposal})
            except HTTPError as error:
                invalid = json.loads(error.read())
                probes.append({"id": "rejects-applied-proposal-claim", "passed": error.code == 400 and "must remain non-applied" in invalid.get("error", "")})
            else:
                probes.append({"id": "rejects-applied-proposal-claim", "passed": False})
            try:
                request(base_url + "/api/change-proposals", method="POST", body={"proposal": []})
            except HTTPError as error:
                malformed = json.loads(error.read())
                probes.append({"id": "rejects-non-object-proposal-payload", "passed": error.code == 400 and "proposal object" in malformed.get("error", "")})
            else:
                probes.append({"id": "rejects-non-object-proposal-payload", "passed": False})
            invalid_draft = {**server_guided_proposal(code_fact_id, guided_unified_diff), "workId": "unknown-work"}
            try:
                request(base_url + "/api/draft-change-proposals", method="POST", body=invalid_draft)
            except HTTPError as error:
                invalid = json.loads(error.read())
                probes.append({"id": "rejects-guided-proposal-with-unknown-work", "passed": error.code == 400 and "work item does not exist" in invalid.get("error", "")})
            else:
                probes.append({"id": "rejects-guided-proposal-with-unknown-work", "passed": False})
            invalid_guided_receipt = {**server_guided_receipt(), "proposalId": "unknown-proposal"}
            try:
                request(base_url + "/api/draft-review-receipts", method="POST", body=invalid_guided_receipt)
            except HTTPError as error:
                invalid = json.loads(error.read())
                probes.append({"id": "rejects-guided-receipt-with-unknown-proposal", "passed": error.code == 400 and "known change proposal" in invalid.get("error", "")})
            else:
                probes.append({"id": "rejects-guided-receipt-with-unknown-proposal", "passed": False})
            invalid_receipt = server_receipt()
            invalid_receipt["authority"] = {**REVIEW_RECEIPT_AUTHORITY, "verificationExecution": True}
            try:
                request(base_url + "/api/review-receipts", method="POST", body={"receipt": invalid_receipt})
            except HTTPError as error:
                invalid = json.loads(error.read())
                probes.append({"id": "rejects-executing-review-receipt-claim", "passed": error.code == 400 and "authority must remain non-executing" in invalid.get("error", "")})
            else:
                probes.append({"id": "rejects-executing-review-receipt-claim", "passed": False})
            status, asset, _ = request(base_url + "/assets/cytoscape.min.js")
            probes.append({"id": "serves-local-graph-asset", "passed": status == 200 and len(asset) > 100000})
        finally:
            server.shutdown()
            thread.join(timeout=10)
            server.server_close()
        after_state, after_manifest, _, _ = validate_project_workspace(workspace)
        probes.append({"id": "snapshot-provenance-unchanged", "passed": before_manifest["source"] == after_manifest["source"] and before_state["project"] == after_state["project"] and len(after_state["workItems"]) == 2 and len(after_state["mappings"]) == 1 and len(after_state["changeProposals"]) == 1 and len(after_state["reviewReceipts"]) == 1 and len(after_state["workStageRevisions"]) == 5})
        try:
            make_server(workspace, "0.0.0.0", 0)
        except LocalWorkbenchServerError as error:
            probes.append({"id": "rejects-non-loopback-host", "passed": "loopback" in str(error)})
        else:
            probes.append({"id": "rejects-non-loopback-host", "passed": False})
    result = "pass" if all(probe["passed"] for probe in probes) else "fail"
    report = {
        "artifactRole": "intentgraph-experimental-csharp-project-server-smoke-report",
        "status": "intentgraph-experimental-csharp-project-server-smoke-" + result,
        "scope": "p9.25-durable-work-stage-revisions-and-navigation",
        "result": result,
        "probeCount": len(probes),
        "probes": probes,
        "loopbackOnly": True,
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
