"""Run a loopback-only smoke test for the interactive C# project workbench server."""

from __future__ import annotations

import argparse
import copy
import json
import tempfile
import threading
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from experimental_csharp_project import (
    EVIDENCE_DECISION_AUTHORITY,
    EVIDENCE_DECISION_PERMISSIONS,
    EVIDENCE_DECISION_ROLE,
    EVIDENCE_DECISION_SCOPE,
    EVIDENCE_DECISION_STATUS,
    PROJECT_SCHEMA_VERSION,
    PROPOSAL_AUTHORITY,
    PROPOSAL_ROLE,
    PROPOSAL_SCOPE,
    PROPOSAL_STATUS,
    REVIEW_RECEIPT_AUTHORITY,
    REVIEW_RECEIPT_ROLE,
    REVIEW_RECEIPT_SCOPE,
    VERIFIER_EVIDENCE_CONTENT_TYPE,
    VERIFIER_RESULT_AUTHORITY,
    VERIFIER_RESULT_ROLE,
    VERIFIER_RESULT_SCOPE,
    canonical_json,
    digest_bytes,
    initialize_project,
    record_semantic_relation_overlay,
    validate_project_workspace,
)
from serve_experimental_csharp_project_workbench import LocalWorkbenchServerError, make_server


DEFERRED_INTERACTIVE_HTML_BYTE_LIMIT = 160_000


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
        "verificationKind": "test-required",
        "verificationSummary": "Review the declared mapping before any source action.",
        "evidenceKind": "test-evidence",
        "evidenceSummary": "Collect evidence only through a later authorized boundary.",
        "codeDiffs": [{"codeFactId": code_fact_id, "unifiedDiff": unified_diff}],
    }


def server_verifier_result(pair: dict[str, Any]) -> dict[str, Any]:
    artifact_bytes = b"server smoke external test evidence\n"
    payload = {
        "summary": "Observed one external server-smoke test result with declared deterministic metadata.",
        "exitCode": 0,
        "checks": [{"id": "check.server", "result": "pass", "summary": "The external test command reported pass."}],
        "metrics": {"total": 1, "passed": 1, "failed": 0, "skipped": 0},
        "artifactRefs": [
            {
                "id": "artifact.server",
                "kind": pair["requiredArtifactKinds"][0],
                "logicalName": "server-test-report.txt",
                "mediaType": "text/plain",
                "byteLength": len(artifact_bytes),
                "digest": digest_bytes(artifact_bytes),
                "availability": "external-digest-only",
            }
        ],
    }
    payload_bytes = canonical_json(payload)
    return {
        "artifactRole": VERIFIER_RESULT_ROLE,
        "schemaVersion": PROJECT_SCHEMA_VERSION,
        "scope": VERIFIER_RESULT_SCOPE,
        "id": f"{pair['resultIdPrefix']}.{pair['nextAttempt']}",
        "proposalId": pair["proposalId"],
        "verificationRequirementId": pair["verificationRequirement"]["id"],
        "evidenceRequirementId": pair["evidenceRequirement"]["id"],
        "attempt": pair["nextAttempt"],
        "result": "pass",
        "verifier": {"id": "server.test.verifier", "kind": "test", "version": "1.0.0", "deterministic": True},
        "invocation": {"id": "invocation.server.test", "digest": digest_bytes(canonical_json({"description": "server smoke test"}))},
        "subject": {"logicalSourceRoot": pair["logicalSourceRoot"], "snapshotSourceDigest": pair["snapshotSourceDigest"], "proposalDigest": pair["proposalDigest"]},
        "evidence": {"contentType": VERIFIER_EVIDENCE_CONTENT_TYPE, "byteLength": len(payload_bytes), "digest": digest_bytes(payload_bytes), "payload": payload},
        "observationStatus": "observed",
        "acceptanceStatus": "pending",
        "supersedesResultId": pair["supersedesResultId"],
        "authority": VERIFIER_RESULT_AUTHORITY,
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


def server_guided_evidence_decision(verifier_result_id: str) -> dict[str, str]:
    return {
        "decisionId": "server-evidence-decision",
        "verifierResultId": verifier_result_id,
        "decision": "accepted",
        "reviewerId": "server.quality-reviewer",
        "reviewerRole": "quality-reviewer",
        "summary": "Accept the current passing external evidence for local workspace readiness only.",
    }


def server_evidence_decision(verifier_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifactRole": EVIDENCE_DECISION_ROLE,
        "schemaVersion": PROJECT_SCHEMA_VERSION,
        "scope": EVIDENCE_DECISION_SCOPE,
        "id": "server-evidence-decision-raw",
        "verifierResultId": verifier_result["id"],
        "proposalId": verifier_result["proposalId"],
        "verificationRequirementId": verifier_result["verificationRequirementId"],
        "evidenceRequirementId": verifier_result["evidenceRequirementId"],
        "decision": "accepted",
        "reviewer": {
            "id": "server.quality-reviewer",
            "actorType": "human",
            "role": "quality-reviewer",
            "permission": EVIDENCE_DECISION_PERMISSIONS["accepted"],
            "authorityScope": "local-project-workspace",
            "authenticationStatus": "local-session-not-cryptographically-verified",
        },
        "subject": {
            "verifierResultDigest": digest_bytes(canonical_json(verifier_result)),
            "evidenceDigest": verifier_result["evidence"]["digest"],
            "proposalDigest": verifier_result["subject"]["proposalDigest"],
            "snapshotSourceDigest": verifier_result["subject"]["snapshotSourceDigest"],
        },
        "summary": "Accept the current passing external evidence for local workspace readiness only.",
        "status": EVIDENCE_DECISION_STATUS,
        "authority": EVIDENCE_DECISION_AUTHORITY,
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
            probes.append({"id": "serves-deferred-interactive-html", "passed": status == 200 and len(html) < DEFERRED_INTERACTIVE_HTML_BYTE_LIMIT and b"newWorkTrigger" in html and b"mapCodeTrigger" in html and b"draftProposalTrigger" in html and b"draftCodeDiffList" in html and b"proposalCodeFacts" in html and b"Import proposal JSON" in html and b"draftReceiptTrigger" in html and b"importReceiptTrigger" in html and b"importVerifierResultTrigger" in html and b"importVerifierResultDialog" in html and b"evidenceDecisionTrigger" in html and b"evidenceDecisionDialog" in html and b"Review observed evidence" in html and b"/api/draft-evidence-decisions" in html and b"client-side" not in html and b"hashed in this browser" in html and b"/api/verifier-results" in html and b"pair.resultIdPrefix" in html and b"crypto.subtle.digest" in html and b"modeBadge" in html and b"previousWork" in html and b"nextWork" in html and b"previousStage" in html and b"nextStage" in html and b"workPosition" in html and b"stagePosition" in html and b"workSearch" in html and b"workStatusFilter" in html and b"workWindowSummary" in html and b"workListRenderLimit=60" in html and b"maxZoom:rendererMaximumZoom" in html and b"logicalZoomFromActual" in html and b"deepZoomFloors" in html and b"precision-" in html and b"spectralObsidianOpticalMaterial" in html and b"edge:selected" in html and b"zoomReadout" in html and b"highlightedEdgeIds" in html and b"focusStage" in html and b"workStageTimeline" in html and b"__intentGraphLoadProjection" in html and b"/api/revision-head" in html and b"checkForProjectUpdate" in html and b"/api/work-requests" in html and b"/api/mapping-candidates" in html and b"/api/change-proposals" in html and b"/api/draft-change-proposals" in html and b"/api/review-receipts" in html and b"/api/draft-review-receipts" in html and b"spiralPoint" in html and b"local-symbol links" in html and b"completeGraph" in html and b"semanticEdgeIds" in html and b"importantCodeLabelIds" in html and b"show-on-demand-label" in html and b"updateViewportScale" in html and b"zoomStyleBand" in html and b"codeNodes.addClass('show-code-label')" not in html and b"edge.low-detail',style:{'display':'none'}" not in html and b"search-match" in html and b"selection-neighbor" in html and b"visibilityUpdates" in html and b"state.cy.destroy" not in html and b"name:'cose'" not in html and headers.get("Content-Security-Policy") is not None})
            probes.append({"id": "serves-512x-and-cached-black-metal-material", "passed": all(marker in html for marker in (b"rendererMaximumZoom=512", b"effectiveGeometryZoom", b"virtualGeometryScale", b"selectedEdgeRenderedOpacity", b"culledOrdinaryCode", b"node-material-layer", b"materialSprite", b"materialCandidates", b"materialNodePixelEvidence", b"cached-nebula-black-metal-v7", b"zoomAnchorModelPosition", b"intentGraphRuntimeProbe", b"intentgraph-runtime-probe-report", b"graphPixelEvidence", b"scheduleMaterialLayer"))})
            status, projection_bytes, _ = request(base_url + "/api/projection")
            initial_projection = json.loads(projection_bytes)
            head_status, head_bytes, _ = request(base_url + "/api/revision-head")
            initial_head = json.loads(head_bytes)
            probes.append({"id": "projects-512x-rendering-contract", "passed": initial_projection["uiContract"]["rendererMaximumZoom"] == 512 and initial_projection["uiContract"]["actualCameraMaximumZoom"] is True and initial_projection["uiContract"]["effectiveGeometryMaximumZoom"] == 512 and initial_projection["uiContract"]["virtualGeometryScaleAtMaximumZoom"] == 1.0 and initial_projection["uiContract"]["selectedEdgeRenderedWidthPixelsAtMaximumZoom"] == 0.08 and initial_projection["uiContract"]["selectedEdgeRenderedOpacityAtMaximumZoom"] == 0.12 and initial_projection["uiContract"]["selectedEdgeEndpointMaterialScaleAtMaximumZoom"] == 0.72 and initial_projection["uiContract"]["selectedEdgeEndpointOpaqueBoundsMaximumPixels"] == 22 and initial_projection["uiContract"]["nebulaBlackMetalNodeMaterial"] is True and initial_projection["uiContract"]["stellarVitreousNodeMaterial"] is False and initial_projection["uiContract"]["celestialCeramicNodeMaterial"] is False and initial_projection["uiContract"]["astralForgedGlassNodeMaterial"] is False and initial_projection["uiContract"]["spectralTitaniumNodeMaterial"] is False and initial_projection["uiContract"]["virtualPrecisionZoom"] is False and initial_projection["uiContract"]["browserRuntimeProbe"] is True and initial_projection["uiContract"]["headlessBrowserRegression"] is True and initial_projection["uiContract"]["canvasPixelEvidence"] is True and initial_projection["uiContract"]["cachedCanvasNodeMaterial"] is True and initial_projection["uiContract"]["boundedMaterialSpriteCache"] is True and initial_projection["uiContract"]["viewportLocalMaterialRendering"] is True and initial_projection["uiContract"]["viewportSpatialMaterialIndex"] is True and initial_projection["uiContract"]["farZoomMaterialCulling"] is True and initial_projection["uiContract"]["selectedMaterialPixelEvidence"] is True})
            probes.append({"id": "serves-project-projection", "passed": status == 200 and head_status == 200 and initial_head["revisionCount"] == 0 and initial_head["workItemCount"] == 0 and initial_head["latestRevisionId"] is None and initial_head["projectStateVersion"].startswith("sha256:") and initial_projection["workflow"]["workItems"] == [] and initial_projection["workflow"]["workStageTimeline"] == [] and initial_projection["workflow"]["workStageRevisions"] == [] and initial_projection["workflow"]["timelineContract"]["durableRevisionCount"] == 0 and initial_projection["workflow"]["verifierResults"] == [] and initial_projection["workflow"]["evidenceDecisions"] == [] and initial_projection["workflow"]["verifierResultIntake"]["pairs"] == [] and initial_projection["workflow"]["evidenceDecisionIntake"]["results"] == [] and initial_projection["uiContract"]["allRecordedWorkItemsNavigable"] is True and initial_projection["uiContract"]["workHistorySearch"] is True and initial_projection["uiContract"]["workHistoryStatusFilter"] is True and initial_projection["uiContract"]["boundedWorkHistoryRendering"] is True and initial_projection["uiContract"]["previousNextWorkNavigation"] is True and initial_projection["uiContract"]["previousNextStageNavigation"] is True and initial_projection["uiContract"]["liveProjectionRefreshAfterMutation"] is True and initial_projection["uiContract"]["loopbackVerifierResultIntakeFromUi"] is True and initial_projection["uiContract"]["loopbackEvidenceDecisionFromUi"] is True and initial_projection["uiContract"]["clientSideEvidenceArtifactHashing"] is True and initial_projection["uiContract"]["externalVerifierExecutionByWorkbench"] is False and initial_projection["uiContract"]["externalEvidenceAcceptanceByWorkbench"] is True and initial_projection["uiContract"]["reviewerAuthenticationByWorkbench"] is False and initial_projection["snapshot"]["semanticRelationOverlay"]["resolvedRelationCount"] == 1 and initial_projection["graph"]["relationCounts"].get("calls") == 1 and initial_projection["graph"]["defaultView"]["id"] == "all" and set(initial_projection["graph"]["views"]["all"]["nodeIds"]) == {node["id"] for node in initial_projection["graph"]["nodes"]}})
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
            verifier_pair = receipt_projection["workflow"]["verifierResultIntake"]["pairs"][0]
            verifier_result = server_verifier_result(verifier_pair)
            probes.append({"id": "projects-pair-scoped-default-verifier-result-id", "passed": verifier_result["id"] == f"{verifier_pair['resultIdPrefix']}.{verifier_pair['nextAttempt']}" and len(verifier_result["id"]) <= 101})
            invalid_verifier = copy.deepcopy(verifier_result)
            invalid_verifier["authority"] = {**VERIFIER_RESULT_AUTHORITY, "approvalRecorded": True}
            before_invalid_state = (workspace / "intentgraph.project.json").read_bytes()
            try:
                request(base_url + "/api/verifier-results", method="POST", body={"verifierResult": invalid_verifier})
            except HTTPError as error:
                invalid = json.loads(error.read())
                probes.append({"id": "rejects-authority-promoted-verifier-result-zero-write", "passed": error.code == 400 and "authority must remain import-only" in invalid.get("error", "") and (workspace / "intentgraph.project.json").read_bytes() == before_invalid_state})
            else:
                probes.append({"id": "rejects-authority-promoted-verifier-result-zero-write", "passed": False})
            status, verifier_bytes, _ = request(base_url + "/api/verifier-results", method="POST", body={"verifierResult": verifier_result})
            verifier_response = json.loads(verifier_bytes)
            probes.append({"id": "imports-observed-verifier-result-without-acceptance", "passed": status == 201 and verifier_response["result"] == "pass" and verifier_response["resultStatus"] == "pass" and verifier_response["verificationStatus"] == "verifier-result-pass" and verifier_response["revisionId"].startswith("revision.server-request.5.") and verifier_response["approvalRecorded"] is False and verifier_response["targetRepositoryMutation"] is False})
            status, verifier_projection_bytes, _ = request(base_url + "/api/projection")
            verifier_projection = json.loads(verifier_projection_bytes)
            verifier_stage = next(stage for stage in verifier_projection["workflow"]["workStageTimeline"] if stage["kind"] == "verifier-result-imported")
            verifier_coverage = verifier_projection["workflow"]["verifierResultCoverage"][0]
            verifier_node = next(node for node in verifier_projection["graph"]["nodes"] if node["category"] == "verifier-result")
            probes.append({"id": "projects-current-observed-result-evidence-and-pending-authority", "passed": status == 200 and len(verifier_projection["workflow"]["verifierResults"]) == 1 and verifier_coverage["requiredPairCount"] == 1 and verifier_coverage["observedPairCount"] == 1 and verifier_coverage["passPairCount"] == 1 and verifier_coverage["allPairsObservedPassing"] is True and verifier_coverage["acceptanceStatus"] == "pending" and verifier_node["details"]["current"] is True and verifier_node["details"]["artifactRefs"][0]["digest"].startswith("sha256:") and verifier_stage["durableRevision"] is True and verifier_stage["revisionIds"] == [verifier_response["revisionId"]] and verifier_projection["workflow"]["workItems"][0]["status"] == "verification-observed" and verifier_projection["workflow"]["workItems"][0]["verificationStatus"] == "verifier-result-pass" and len(verifier_projection["workflow"]["reviewReceipts"]) == 1 and verifier_projection["authority"]["approvalAutomation"] is False})
            invalid_decision = server_evidence_decision(verifier_result)
            invalid_decision["decision"] = []
            before_invalid_decision_state = (workspace / "intentgraph.project.json").read_bytes()
            try:
                request(
                    base_url + "/api/evidence-decisions",
                    method="POST",
                    body={"evidenceDecision": invalid_decision},
                )
            except HTTPError as error:
                invalid = json.loads(error.read())
                probes.append(
                    {
                        "id": "rejects-nested-array-evidence-decision-as-json-400-zero-write",
                        "passed": (
                            error.code == 400
                            and "evidence decision result is invalid" in invalid.get("error", "")
                            and (workspace / "intentgraph.project.json").read_bytes()
                            == before_invalid_decision_state
                        ),
                    }
                )
            else:
                probes.append(
                    {
                        "id": "rejects-nested-array-evidence-decision-as-json-400-zero-write",
                        "passed": False,
                    }
                )
            decision_payload = server_guided_evidence_decision(verifier_result["id"])
            status, decision_bytes, _ = request(base_url + "/api/draft-evidence-decisions", method="POST", body=decision_payload)
            decision_response = json.loads(decision_bytes)
            probes.append({"id": "records-human-evidence-acceptance-without-proposal-approval", "passed": status == 201 and decision_response["result"] == "pass" and decision_response["evidenceDecisionId"] == "server-evidence-decision" and decision_response["decision"] == "accepted" and decision_response["workStatus"] == "verified" and decision_response["proposalApprovalRecorded"] is False and decision_response["targetRepositoryMutation"] is False})
            status, decision_projection_bytes, _ = request(base_url + "/api/projection")
            decision_projection = json.loads(decision_projection_bytes)
            decision_stage = next(stage for stage in decision_projection["workflow"]["workStageTimeline"] if stage["kind"] == "evidence-decision-recorded")
            decision_coverage = decision_projection["workflow"]["verifierResultCoverage"][0]
            decision_node = next(node for node in decision_projection["graph"]["nodes"] if node["id"] == "evidence-decision.server-evidence-decision")
            decision_authority = next(node for node in decision_projection["graph"]["nodes"] if node["id"] == "authority.evidence-decision.server-evidence-decision")
            authority_edge = next(edge for edge in decision_projection["graph"]["edges"] if edge["source"] == decision_authority["id"] and edge["kind"] == "authorizes")
            probes.append({"id": "projects-accepted-evidence-decision-authority-and-verified-work", "passed": status == 200 and len(decision_projection["workflow"]["evidenceDecisions"]) == 1 and decision_projection["workflow"]["evidenceDecisionIntake"]["results"][0]["decisionRecorded"] is True and decision_coverage["acceptanceStatus"] == "accepted" and decision_coverage["allPairsAcceptedPassing"] is True and decision_projection["workflow"]["workItems"][0]["status"] == "verified" and decision_projection["workflow"]["workItems"][0]["verificationStatus"] == "evidence-accepted-pass" and decision_node["details"]["decision"] == "accepted" and decision_authority["details"]["decidedByType"] == "human" and decision_authority["details"]["proposalApprovalRecorded"] is False and authority_edge["target"] == "evidence.evidence.evidence-decision.server-evidence-decision" and decision_stage["durableRevision"] is True and decision_stage["revisionIds"] == [decision_response["revisionId"]]})
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
        probes.append({"id": "snapshot-provenance-unchanged", "passed": before_manifest["source"] == after_manifest["source"] and before_state["project"] == after_state["project"] and len(after_state["workItems"]) == 2 and len(after_state["mappings"]) == 1 and len(after_state["changeProposals"]) == 1 and len(after_state["reviewReceipts"]) == 1 and len(after_state["verifierResults"]) == 1 and len(after_state["evidenceDecisions"]) == 1 and len(after_state["workStageRevisions"]) == 7})
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
        "scope": "p9.30-local-evidence-decision-authority",
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
