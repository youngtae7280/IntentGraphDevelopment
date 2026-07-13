"""Run positive and negative probes for P9.30 evidence decisions."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from experimental_csharp_project import (
    EVIDENCE_DECISION_AUTHORITY,
    EVIDENCE_DECISION_PERMISSIONS,
    EVIDENCE_DECISION_ROLE,
    EVIDENCE_DECISION_SCOPE,
    EVIDENCE_DECISION_STATUS,
    PROJECT_AUTHORITY,
    PROJECT_FILE,
    PROJECT_SCHEMA_VERSION,
    ProjectWorkspaceError,
    add_evidence_decision_document,
    add_verifier_result_document,
    build_projection,
    digest_json,
    draft_review_receipt_from_proposal,
    project_workspace_write_lock,
    validate_project_workspace,
    validate_projection,
    write_json,
)
from run_experimental_csharp_verifier_result_negative_probes import (
    prepare,
    prepare_multi_binding_proposal,
    project_inventory,
    result_for,
    result_for_intake_pair,
    set_outcome,
)


def write_report(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def evidence_decision_for(
    result: dict[str, Any],
    *,
    identifier: str,
    decision: str,
    reviewer_id: str = "reviewer.local.human",
    reviewer_role: str = "quality-reviewer",
) -> dict[str, Any]:
    return {
        "artifactRole": EVIDENCE_DECISION_ROLE,
        "schemaVersion": PROJECT_SCHEMA_VERSION,
        "scope": EVIDENCE_DECISION_SCOPE,
        "id": identifier,
        "verifierResultId": result["id"],
        "proposalId": result["proposalId"],
        "verificationRequirementId": result["verificationRequirementId"],
        "evidenceRequirementId": result["evidenceRequirementId"],
        "decision": decision,
        "reviewer": {
            "id": reviewer_id,
            "actorType": "human",
            "role": reviewer_role,
            "permission": EVIDENCE_DECISION_PERMISSIONS[decision],
            "authorityScope": "local-project-workspace",
            "authenticationStatus": "local-session-not-cryptographically-verified",
        },
        "subject": {
            "verifierResultDigest": digest_json(result),
            "evidenceDigest": result["evidence"]["digest"],
            "proposalDigest": result["subject"]["proposalDigest"],
            "snapshotSourceDigest": result["subject"]["snapshotSourceDigest"],
        },
        "summary": f"Record a local human {decision} decision for {result['id']}.",
        "status": EVIDENCE_DECISION_STATUS,
        "authority": EVIDENCE_DECISION_AUTHORITY,
    }


def work_state(workspace: Path, work_id: str) -> dict[str, Any]:
    state, _, _, _ = validate_project_workspace(workspace)
    return next(item for item in state["workItems"] if item["id"] == work_id)


def run_invalid_decision_probe(
    workspace: Path,
    identifier: str,
    decision: dict[str, Any],
    expected: str,
) -> dict[str, Any]:
    before = project_inventory(workspace)
    try:
        add_evidence_decision_document(workspace, decision)
    except ProjectWorkspaceError as error:
        message = str(error)
        return {
            "id": identifier,
            "expectedError": expected,
            "actualError": message,
            "expectedFailureObserved": expected in message,
            "zeroWrite": before == project_inventory(workspace),
        }
    except Exception as error:  # The validator must be total over arbitrary JSON values.
        return {
            "id": identifier,
            "expectedError": expected,
            "actualError": f"{type(error).__name__}: {error}",
            "expectedFailureObserved": False,
            "zeroWrite": before == project_inventory(workspace),
        }
    return {
        "id": identifier,
        "expectedError": expected,
        "actualError": "invalid evidence decision unexpectedly accepted",
        "expectedFailureObserved": False,
        "zeroWrite": before == project_inventory(workspace),
    }


def run_invalid_result_probe(
    workspace: Path,
    identifier: str,
    result: dict[str, Any],
    expected: str,
) -> dict[str, Any]:
    before = project_inventory(workspace)
    try:
        add_verifier_result_document(workspace, result)
    except ProjectWorkspaceError as error:
        message = str(error)
        return {
            "id": identifier,
            "expectedError": expected,
            "actualError": message,
            "expectedFailureObserved": expected in message,
            "zeroWrite": before == project_inventory(workspace),
        }
    except Exception as error:
        return {
            "id": identifier,
            "expectedError": expected,
            "actualError": f"{type(error).__name__}: {error}",
            "expectedFailureObserved": False,
            "zeroWrite": before == project_inventory(workspace),
        }
    return {
        "id": identifier,
        "expectedError": expected,
        "actualError": "stale verifier result unexpectedly accepted",
        "expectedFailureObserved": False,
        "zeroWrite": before == project_inventory(workspace),
    }


def mutate_decision(
    base: dict[str, Any],
    mutation: Callable[[dict[str, Any]], None],
) -> dict[str, Any]:
    value = copy.deepcopy(base)
    mutation(value)
    return value


def record_receipt(workspace: Path, result: dict[str, Any], identifier: str) -> None:
    draft_review_receipt_from_proposal(
        workspace,
        receipt_id=identifier,
        proposal_id=result["proposalId"],
        verification_requirement_id=result["verificationRequirementId"],
        evidence_requirement_id=result["evidenceRequirementId"],
        result="reviewed-pass",
        summary="Record a non-executing review receipt for ordering coverage.",
    )


def run_ordering_probe(
    snapshot: Path,
    root: Path,
    identifier: str,
    ordering: tuple[str, ...],
) -> dict[str, Any]:
    workspace = prepare(snapshot, root, f"ordering-{identifier}")
    snapshot_before = project_inventory(workspace / "snapshot")
    result = result_for(workspace, "build", identifier=f"result.ordering.{identifier}")
    decision = evidence_decision_for(
        result,
        identifier=f"decision.ordering.{identifier}",
        decision="accepted",
    )
    for operation in ordering:
        if operation == "receipt":
            record_receipt(workspace, result, f"receipt.ordering.{identifier}")
        elif operation == "result":
            add_verifier_result_document(workspace, result)
        elif operation == "decision":
            add_evidence_decision_document(workspace, decision)
        else:  # pragma: no cover - the fixed probe table owns the operation set.
            raise AssertionError(f"unknown ordering probe operation: {operation}")
    state, _, _, data = validate_project_workspace(workspace)
    projection, _ = build_projection(workspace)
    work = next(item for item in state["workItems"] if item["id"] == "verify.build")
    passed = (
        work["status"] == "verified"
        and work["verificationStatus"] == "evidence-accepted-pass"
        and len(data["reviewReceipts"]) == 1
        and len(data["verifierResults"]) == 1
        and len(data["evidenceDecisions"]) == 1
        and not validate_projection(projection)
        and snapshot_before == project_inventory(workspace / "snapshot")
    )
    return {
        "id": identifier,
        "ordering": list(ordering),
        "passed": passed,
        "workStatus": work["status"],
        "verificationStatus": work["verificationStatus"],
        "snapshotUnchanged": snapshot_before == project_inventory(workspace / "snapshot"),
    }


def projection_probe(
    baseline: dict[str, Any],
    identifier: str,
    mutation: Callable[[dict[str, Any]], None],
    expected: str,
) -> dict[str, Any]:
    mutated = copy.deepcopy(baseline)
    mutation(mutated)
    errors = validate_projection(mutated)
    return {
        "id": identifier,
        "expectedError": expected,
        "errors": errors,
        "expectedFailureObserved": any(expected in error for error in errors),
    }


def workspace_tamper_probe(
    workspace: Path,
    identifier: str,
    mutation: Callable[[dict[str, Any]], None],
    expected: str,
) -> dict[str, Any]:
    project_file = workspace / PROJECT_FILE
    original = project_file.read_bytes()
    state = json.loads(original.decode("utf-8"))
    mutation(state)
    write_json(project_file, state)
    try:
        validate_project_workspace(workspace)
    except ProjectWorkspaceError as error:
        message = str(error)
        return {
            "id": identifier,
            "expectedError": expected,
            "actualError": message,
            "expectedFailureObserved": expected in message,
        }
    except Exception as error:
        return {
            "id": identifier,
            "expectedError": expected,
            "actualError": f"{type(error).__name__}: {error}",
            "expectedFailureObserved": False,
        }
    finally:
        project_file.write_bytes(original)
    return {
        "id": identifier,
        "expectedError": expected,
        "actualError": "tampered workspace unexpectedly validated",
        "expectedFailureObserved": False,
    }


def remove_graph_element(projection: dict[str, Any], key: str, identifier: str) -> None:
    projection["graph"][key] = [
        item for item in projection["graph"][key] if item["id"] != identifier
    ]


def run(snapshot: Path, output: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="p9.30-evidence-decision-") as temporary:
        root = Path(temporary)

        accepted = prepare(snapshot, root, "evidence-decision-accepted")
        accepted_snapshot_before = project_inventory(accepted / "snapshot")
        _, accepted_manifest_before, _, _ = validate_project_workspace(accepted)
        accepted_result = result_for(
            accepted,
            "build",
            identifier="result.evidence.accepted.pass",
        )
        add_verifier_result_document(accepted, accepted_result)
        accepted_decision = evidence_decision_for(
            accepted_result,
            identifier="decision.evidence.accepted.pass",
            decision="accepted",
        )
        accepted_response = add_evidence_decision_document(accepted, accepted_decision)
        accepted_state, accepted_manifest_after, _, accepted_data = validate_project_workspace(accepted)
        accepted_projection, _ = build_projection(accepted)
        accepted_projection_errors = validate_projection(accepted_projection)
        accepted_work = next(
            item for item in accepted_state["workItems"] if item["id"] == "verify.build"
        )
        accepted_stages = [
            item
            for item in accepted_projection["workflow"]["workStageTimeline"]
            if item["kind"] == "evidence-decision-recorded"
        ]
        accepted_decision_id = accepted_decision["id"]
        accepted_authority_edge_id = (
            f"edge.authority.evidence-decision.{accepted_decision_id}.authorizes."
            f"evidence.evidence-decision.{accepted_decision_id}"
        )
        accepted_checks = {
            "acceptPassingCurrentResultVerifiesWork": (
                accepted_response["verificationStatus"] == "evidence-accepted-pass"
                and accepted_response["workStatus"] == "verified"
                and accepted_work["verificationStatus"] == "evidence-accepted-pass"
                and accepted_work["status"] == "verified"
            ),
            "decisionArtifactAndIndexRecorded": (
                len(accepted_data["evidenceDecisions"]) == 1
                and len(accepted_state["evidenceDecisions"]) == 1
            ),
            "projectionContractPasses": not accepted_projection_errors,
            "oneDurableRevisionPerDecision": (
                len(accepted_stages) == 1
                and accepted_stages[0]["durableRevision"] is True
                and len(accepted_stages[0]["revisionIds"]) == 1
            ),
            "explicitHumanAuthorityProjected": (
                any(
                    node["id"] == f"authority.evidence-decision.{accepted_decision_id}"
                    and node["details"]["proposerType"] == "human"
                    and node["details"]["decidedByType"] == "human"
                    for node in accepted_projection["graph"]["nodes"]
                )
                and any(
                    edge["id"] == accepted_authority_edge_id
                    and edge["kind"] == "authorizes"
                    for edge in accepted_projection["graph"]["edges"]
                )
            ),
            "snapshotAndSourceProvenanceUnchanged": (
                accepted_snapshot_before == project_inventory(accepted / "snapshot")
                and accepted_manifest_before["source"] == accepted_manifest_after["source"]
            ),
            "proposalAuthorityNotPromoted": (
                accepted_response["proposalApprovalRecorded"] is False
                and accepted_response["targetRepositoryMutation"] is False
                and accepted_response["automaticCodeApplication"] is False
            ),
        }
        state_integrity_probes = [
            workspace_tamper_probe(
                accepted,
                "tampered-decision-evidence-record",
                lambda value: next(
                    item
                    for item in value["evidence"]
                    if item["id"]
                    == f"evidence.evidence-decision.{accepted_decision_id}"
                ).update(
                    {
                        "result": "rejected",
                        "evidenceDigest": "sha256:" + "0" * 64,
                    }
                ),
                "evidence decision evidence record does not match its decision artifact",
            )
        ]

        rejected = prepare(snapshot, root, "evidence-decision-rejected")
        rejected_snapshot_before = project_inventory(rejected / "snapshot")
        rejected_result = result_for(
            rejected,
            "build",
            identifier="result.evidence.rejected.pass",
        )
        add_verifier_result_document(rejected, rejected_result)
        rejected_response = add_evidence_decision_document(
            rejected,
            evidence_decision_for(
                rejected_result,
                identifier="decision.evidence.rejected.pass",
                decision="rejected",
            ),
        )
        rejected_projection, _ = build_projection(rejected)
        rejected_work = work_state(rejected, "verify.build")
        rejected_checks = {
            "rejectBlocksWork": (
                rejected_response["verificationStatus"] == "evidence-rejected"
                and rejected_response["workStatus"] == "blocked"
                and rejected_work["verificationStatus"] == "evidence-rejected"
                and rejected_work["status"] == "blocked"
            ),
            "rejectionProjectionPasses": not validate_projection(rejected_projection),
            "rejectionAuthorityEdgeProjected": any(
                edge["kind"] == "rejects"
                and edge["source"].startswith("authority.evidence-decision.")
                for edge in rejected_projection["graph"]["edges"]
            ),
            "rejectionSnapshotUnchanged": (
                rejected_snapshot_before == project_inventory(rejected / "snapshot")
            ),
        }

        multi = prepare_multi_binding_proposal(snapshot, root)
        multi_snapshot_before = project_inventory(multi / "snapshot")
        multi_projection_before, _ = build_projection(multi)
        multi_pairs = [
            item
            for item in multi_projection_before["workflow"]["verifierResultIntake"]["pairs"]
            if item["proposalId"] == "proposal.verify.multi"
        ]
        multi_results = [
            result_for_intake_pair(pair, pair["allowedVerifierKinds"][0])
            for pair in multi_pairs
        ]
        for result in multi_results:
            add_verifier_result_document(multi, result)
        partial_response = add_evidence_decision_document(
            multi,
            evidence_decision_for(
                multi_results[0],
                identifier="decision.evidence.multi.first",
                decision="accepted",
            ),
        )
        partial_work = work_state(multi, "verify.multi")
        complete_response = add_evidence_decision_document(
            multi,
            evidence_decision_for(
                multi_results[1],
                identifier="decision.evidence.multi.second",
                decision="accepted",
            ),
        )
        complete_work = work_state(multi, "verify.multi")
        multi_projection_after, _ = build_projection(multi)
        multi_coverage = next(
            item
            for item in multi_projection_after["workflow"]["verifierResultCoverage"]
            if item["proposalId"] == "proposal.verify.multi"
        )
        multi_checks = {
            "partialDecisionRemainsObserved": (
                partial_response["verificationStatus"] == "evidence-decision-partial"
                and partial_response["workStatus"] == "verification-observed"
                and partial_work["verificationStatus"] == "evidence-decision-partial"
                and partial_work["status"] == "verification-observed"
            ),
            "allAcceptedPassingVerifies": (
                complete_response["verificationStatus"] == "evidence-accepted-pass"
                and complete_response["workStatus"] == "verified"
                and complete_work["verificationStatus"] == "evidence-accepted-pass"
                and complete_work["status"] == "verified"
            ),
            "coverageCountsDecisions": (
                multi_coverage["acceptedPairCount"] == 2
                and multi_coverage["pendingPairCount"] == 0
                and multi_coverage["rejectedPairCount"] == 0
                and multi_coverage["allPairsAcceptedPassing"] is True
                and multi_coverage["acceptanceStatus"] == "accepted"
            ),
            "multiProjectionPasses": not validate_projection(multi_projection_after),
            "multiSnapshotUnchanged": (
                multi_snapshot_before == project_inventory(multi / "snapshot")
            ),
        }

        outcome = prepare(snapshot, root, "evidence-decision-outcomes")
        outcome_probes: list[dict[str, Any]] = []
        fail_result = result_for(
            outcome,
            "test",
            identifier="result.evidence.fail.current",
        )
        set_outcome(fail_result, "fail")
        add_verifier_result_document(outcome, fail_result)
        outcome_probes.append(
            run_invalid_decision_probe(
                outcome,
                "accept-fail",
                evidence_decision_for(
                    fail_result,
                    identifier="decision.evidence.accept.fail",
                    decision="accepted",
                ),
                "only a current passing verifier result may be accepted as evidence",
            )
        )
        blocked_result = result_for(
            outcome,
            "test",
            identifier="result.evidence.blocked.current",
        )
        set_outcome(blocked_result, "blocked")
        add_verifier_result_document(outcome, blocked_result)
        outcome_probes.append(
            run_invalid_decision_probe(
                outcome,
                "accept-blocked",
                evidence_decision_for(
                    blocked_result,
                    identifier="decision.evidence.accept.blocked",
                    decision="accepted",
                ),
                "only a current passing verifier result may be accepted as evidence",
            )
        )

        superseded = prepare(snapshot, root, "evidence-decision-superseded")
        stale_result = result_for(
            superseded,
            "test",
            identifier="result.evidence.stale.after.later",
        )
        first_result = result_for(
            superseded,
            "test",
            identifier="result.evidence.superseded.first",
        )
        add_verifier_result_document(superseded, first_result)
        later_result = result_for(
            superseded,
            "test",
            identifier="result.evidence.superseded.later",
        )
        add_verifier_result_document(superseded, later_result)
        supersession_probes = [
            run_invalid_decision_probe(
                superseded,
                "decision-on-superseded-result",
                evidence_decision_for(
                    first_result,
                    identifier="decision.evidence.superseded",
                    decision="accepted",
                ),
                "must reference the current verifier result",
            ),
            run_invalid_result_probe(
                superseded,
                "stale-result-after-later-result",
                stale_result,
                "supersedes chain is invalid",
            ),
        ]

        duplicates = prepare(snapshot, root, "evidence-decision-duplicates")
        duplicate_build = result_for(
            duplicates,
            "build",
            identifier="result.evidence.duplicate.build",
        )
        duplicate_test = result_for(
            duplicates,
            "test",
            identifier="result.evidence.duplicate.test",
        )
        add_verifier_result_document(duplicates, duplicate_build)
        add_verifier_result_document(duplicates, duplicate_test)
        original_duplicate_decision = evidence_decision_for(
            duplicate_build,
            identifier="decision.evidence.duplicate",
            decision="accepted",
        )
        add_evidence_decision_document(duplicates, original_duplicate_decision)
        duplicate_probes = [
            run_invalid_decision_probe(
                duplicates,
                "duplicate-result",
                evidence_decision_for(
                    duplicate_build,
                    identifier="decision.evidence.duplicate.result",
                    decision="accepted",
                ),
                "already exists for the verifier result",
            ),
            run_invalid_decision_probe(
                duplicates,
                "duplicate-identifier",
                evidence_decision_for(
                    duplicate_test,
                    identifier="decision.evidence.duplicate",
                    decision="accepted",
                ),
                "identifier already exists",
            ),
        ]

        malformed = prepare(snapshot, root, "evidence-decision-malformed")
        malformed_result = result_for(
            malformed,
            "build",
            identifier="result.evidence.malformed.base",
        )
        add_verifier_result_document(malformed, malformed_result)
        base_decision = evidence_decision_for(
            malformed_result,
            identifier="decision.evidence.malformed.base",
            decision="accepted",
        )
        malformed_specs: list[
            tuple[str, Callable[[dict[str, Any]], None], str]
        ] = [
            (
                "wrong-role",
                lambda value: value.__setitem__("artifactRole", "wrong-role"),
                "role, schema version, scope, or status is invalid",
            ),
            (
                "wrong-status",
                lambda value: value.__setitem__("status", "wrong-status"),
                "role, schema version, scope, or status is invalid",
            ),
            (
                "wrong-scope",
                lambda value: value.__setitem__("scope", "wrong-scope"),
                "role, schema version, scope, or status is invalid",
            ),
            (
                "decision-array-type",
                lambda value: value.__setitem__("decision", []),
                "evidence decision result is invalid",
            ),
            (
                "wrong-binding",
                lambda value: value.__setitem__("proposalId", "proposal.missing"),
                "requirement binding does not match",
            ),
            (
                "wrong-verifier-result-digest",
                lambda value: value["subject"].__setitem__(
                    "verifierResultDigest", "sha256:" + "0" * 64
                ),
                "subject does not match",
            ),
            (
                "wrong-evidence-digest",
                lambda value: value["subject"].__setitem__(
                    "evidenceDigest", "sha256:" + "0" * 64
                ),
                "subject does not match",
            ),
            (
                "wrong-proposal-digest",
                lambda value: value["subject"].__setitem__(
                    "proposalDigest", "sha256:" + "0" * 64
                ),
                "subject does not match",
            ),
            (
                "wrong-snapshot-digest",
                lambda value: value["subject"].__setitem__(
                    "snapshotSourceDigest", "sha256:" + "0" * 64
                ),
                "subject does not match",
            ),
            (
                "reviewer-actor-not-human",
                lambda value: value["reviewer"].__setitem__("actorType", "ai"),
                "reviewer authority is invalid",
            ),
            (
                "reviewer-role-invalid",
                lambda value: value["reviewer"].__setitem__("role", "automation"),
                "reviewer authority is invalid",
            ),
            (
                "reviewer-role-object-type",
                lambda value: value["reviewer"].__setitem__("role", {}),
                "reviewer authority is invalid",
            ),
            (
                "reviewer-permission-invalid",
                lambda value: value["reviewer"].__setitem__(
                    "permission", "evidence.reject"
                ),
                "reviewer authority is invalid",
            ),
            (
                "reviewer-scope-invalid",
                lambda value: value["reviewer"].__setitem__(
                    "authorityScope", "enterprise"
                ),
                "reviewer authority is invalid",
            ),
            (
                "reviewer-authentication-invalid",
                lambda value: value["reviewer"].__setitem__(
                    "authenticationStatus", "cryptographically-verified"
                ),
                "reviewer authority is invalid",
            ),
            (
                "authority-proposal-approval",
                lambda value: value["authority"].__setitem__(
                    "proposalApprovalRecorded", True
                ),
                "authority exceeds the local human-decision boundary",
            ),
            (
                "authority-graph-mutation",
                lambda value: value["authority"].__setitem__(
                    "graphMutationApplied", True
                ),
                "authority exceeds the local human-decision boundary",
            ),
            (
                "authority-target-mutation",
                lambda value: value["authority"].__setitem__(
                    "targetRepositoryMutation", True
                ),
                "authority exceeds the local human-decision boundary",
            ),
            (
                "unknown-result",
                lambda value: value.__setitem__(
                    "verifierResultId", "result.evidence.missing"
                ),
                "must reference a known verifier result",
            ),
        ]
        malformed_probes = [
            run_invalid_decision_probe(
                malformed,
                identifier,
                mutate_decision(base_decision, mutation),
                expected,
            )
            for identifier, mutation, expected in malformed_specs
        ]

        ordering_probes = [
            run_ordering_probe(
                snapshot,
                root,
                "result-decision-receipt",
                ("result", "decision", "receipt"),
            ),
            run_ordering_probe(
                snapshot,
                root,
                "result-receipt-decision",
                ("result", "receipt", "decision"),
            ),
            run_ordering_probe(
                snapshot,
                root,
                "receipt-result-decision",
                ("receipt", "result", "decision"),
            ),
        ]

        projection_probes = [
            projection_probe(
                accepted_projection,
                "missing-decisions",
                lambda value: value["workflow"].pop("evidenceDecisions"),
                "project workbench review receipt state is invalid",
            ),
            projection_probe(
                accepted_projection,
                "missing-decision-intake",
                lambda value: value["workflow"].pop("evidenceDecisionIntake"),
                "project workbench review receipt state is invalid",
            ),
            projection_probe(
                accepted_projection,
                "missing-decision-node",
                lambda value: remove_graph_element(
                    value,
                    "nodes",
                    f"evidence-decision.{accepted_decision_id}",
                ),
                "project workbench evidence decision graph nodes are invalid",
            ),
            projection_probe(
                accepted_projection,
                "missing-authority-node",
                lambda value: remove_graph_element(
                    value,
                    "nodes",
                    f"authority.evidence-decision.{accepted_decision_id}",
                ),
                "project workbench evidence decision graph nodes are invalid",
            ),
            projection_probe(
                accepted_projection,
                "missing-authority-edge",
                lambda value: remove_graph_element(
                    value,
                    "edges",
                    accepted_authority_edge_id,
                ),
                "project workbench evidence decision authority graph is invalid",
            ),
            projection_probe(
                accepted_projection,
                "missing-decision-records-verification-edge",
                lambda value: remove_graph_element(
                    value,
                    "edges",
                    f"edge.evidence-decision.{accepted_decision_id}.records-verification.{accepted_decision_id}",
                ),
                "project workbench evidence decision authority graph is invalid",
            ),
            projection_probe(
                accepted_projection,
                "wrong-result-acceptance",
                lambda value: next(
                    node
                    for node in value["graph"]["nodes"]
                    if node["id"] == f"verifier-result.{accepted_result['id']}"
                )["details"].__setitem__("acceptanceStatus", "pending"),
                "project workbench verifier result graph nodes are invalid",
            ),
            projection_probe(
                accepted_projection,
                "wrong-coverage-acceptance",
                lambda value: next(
                    item
                    for item in value["workflow"]["verifierResultCoverage"]
                    if item["proposalId"] == accepted_result["proposalId"]
                ).__setitem__("acceptanceStatus", "pending"),
                "project workbench verifier result projection contract is invalid",
            ),
            projection_probe(
                accepted_projection,
                "missing-intake-current-decision",
                lambda value: next(
                    item
                    for item in value["workflow"]["evidenceDecisionIntake"]["results"]
                    if item["verifierResultId"] == accepted_result["id"]
                ).__setitem__("currentDecision", None),
                "project workbench verifier result projection contract is invalid",
            ),
            projection_probe(
                accepted_projection,
                "decision-stage-not-durable",
                lambda value: next(
                    stage
                    for stage in value["workflow"]["workStageTimeline"]
                    if stage["kind"] == "evidence-decision-recorded"
                ).update({"durableRevision": False, "revisionIds": []}),
                "project workbench evidence decision stage revision is invalid",
            ),
            projection_probe(
                accepted_projection,
                "decision-stage-two-revisions",
                lambda value: next(
                    stage
                    for stage in value["workflow"]["workStageTimeline"]
                    if stage["kind"] == "evidence-decision-recorded"
                )["revisionIds"].append("revision.unexpected.second"),
                "project workbench evidence decision stage revision is invalid",
            ),
            projection_probe(
                multi_projection_before,
                "fabricated-verified-work-readiness",
                lambda value: next(
                    item
                    for item in value["workflow"]["workItems"]
                    if item["id"] == "verify.multi"
                ).update(
                    {
                        "status": "verified",
                        "verificationStatus": "evidence-accepted-pass",
                    }
                ),
                "project workbench verifier result projection contract is invalid",
            ),
            projection_probe(
                multi_projection_before,
                "fabricated-internally-consistent-accepted-coverage",
                lambda value: next(
                    item
                    for item in value["workflow"]["verifierResultCoverage"]
                    if item["proposalId"] == "proposal.verify.multi"
                ).update(
                    {
                        "acceptedPairCount": 2,
                        "rejectedPairCount": 0,
                        "pendingPairCount": 0,
                        "allPairsAcceptedPassing": False,
                        "acceptanceStatus": "accepted",
                    }
                ),
                "project workbench verifier result projection contract is invalid",
            ),
        ]

        concurrent = prepare(snapshot, root, "evidence-decision-concurrent")
        concurrent_snapshot_before = project_inventory(concurrent / "snapshot")
        concurrent_result = result_for(
            concurrent,
            "test",
            identifier="result.evidence.concurrent.current",
        )
        add_verifier_result_document(concurrent, concurrent_result)
        concurrent_documents = [
            evidence_decision_for(
                concurrent_result,
                identifier=f"decision.evidence.concurrent.{suffix}",
                decision="accepted",
            )
            for suffix in ("a", "b")
        ]
        concurrent_paths = [root / f"concurrent-{index}.json" for index in range(2)]
        for path, document in zip(concurrent_paths, concurrent_documents, strict=True):
            write_json(path, document)
        decision_command = [
            sys.executable,
            str(Path(__file__).with_name("intentgraph.py")),
            "add-experimental-csharp-evidence-decision",
            "--workspace",
            str(concurrent),
            "--decision",
        ]
        concurrent_processes = [
            subprocess.Popen(
                [*decision_command, str(path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            for path in concurrent_paths
        ]
        concurrent_results = [
            {
                "returnCode": process.wait(),
                "stdout": process.stdout.read(),
                "stderr": process.stderr.read(),
            }
            for process in concurrent_processes
        ]
        concurrent_state, _, _, concurrent_data = validate_project_workspace(concurrent)
        concurrent_projection, _ = build_projection(concurrent)
        concurrent_decision_stages = [
            stage
            for stage in concurrent_projection["workflow"]["workStageTimeline"]
            if stage["kind"] == "evidence-decision-recorded"
        ]
        concurrency_passed = (
            sorted(item["returnCode"] for item in concurrent_results) == [0, 2]
            and len(concurrent_data["evidenceDecisions"]) == 1
            and len(concurrent_state["evidenceDecisions"]) == 1
            and len(concurrent_decision_stages) == 1
            and len(concurrent_decision_stages[0]["revisionIds"]) == 1
            and work_state(concurrent, "verify.test")["status"] == "verified"
            and not validate_projection(concurrent_projection)
            and concurrent_snapshot_before == project_inventory(concurrent / "snapshot")
        )

        cross_operation = prepare(snapshot, root, "evidence-decision-cross-operation")
        cross_result = result_for(
            cross_operation,
            "test",
            identifier="result.evidence.concurrent.cross",
        )
        add_verifier_result_document(cross_operation, cross_result)
        cross_document = evidence_decision_for(
            cross_result,
            identifier="decision.evidence.concurrent.cross",
            decision="accepted",
        )
        cross_path = root / "cross-operation-decision.json"
        write_json(cross_path, cross_document)
        cross_commands = [
            [*decision_command[:-2], str(cross_operation), "--decision", str(cross_path)],
            [
                sys.executable,
                str(Path(__file__).with_name("intentgraph.py")),
                "add-experimental-csharp-work-request",
                "--workspace",
                str(cross_operation),
                "--work-id",
                "evidence.concurrent.work",
                "--title",
                "Concurrent evidence work",
                "--request",
                "Record a work request concurrently with an evidence decision.",
            ],
        ]
        with project_workspace_write_lock(cross_operation):
            cross_processes = [
                subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                for command in cross_commands
            ]
            time.sleep(0.25)
            cross_waiting = all(process.poll() is None for process in cross_processes)
        cross_process_results = [
            {
                "returnCode": process.wait(),
                "stdout": process.stdout.read(),
                "stderr": process.stderr.read(),
            }
            for process in cross_processes
        ]
        cross_state, _, _, cross_data = validate_project_workspace(cross_operation)
        cross_projection, _ = build_projection(cross_operation)
        cross_operation_passed = (
            cross_waiting
            and all(item["returnCode"] == 0 for item in cross_process_results)
            and len(cross_data["evidenceDecisions"]) == 1
            and any(
                item["id"] == "evidence.concurrent.work"
                for item in cross_state["workItems"]
            )
            and len({item["id"] for item in cross_state["workStageRevisions"]})
            == len(cross_state["workStageRevisions"])
            and not validate_projection(cross_projection)
        )

        negative_probes = [
            *outcome_probes,
            *supersession_probes,
            *duplicate_probes,
            *malformed_probes,
        ]
        positive_checks = {
            **accepted_checks,
            **rejected_checks,
            **multi_checks,
            "allReceiptResultDecisionOrderingsPass": all(
                item["passed"] for item in ordering_probes
            ),
            "concurrentDuplicateHasOneWinner": concurrency_passed,
            "crossOperationHasNoLostUpdate": cross_operation_passed,
        }
        passed = (
            all(positive_checks.values())
            and all(item["expectedFailureObserved"] for item in state_integrity_probes)
            and all(
                item["expectedFailureObserved"] and item["zeroWrite"]
                for item in negative_probes
            )
            and all(item["expectedFailureObserved"] for item in projection_probes)
        )
        report = {
            "artifactRole": "intentgraph-experimental-csharp-evidence-decision-probes-report",
            "status": "intentgraph-experimental-csharp-evidence-decision-probes-"
            + ("pass" if passed else "fail"),
            "scope": "p9.30-evidence-decision-authority",
            "result": "pass" if passed else "fail",
            "positiveCheckCount": len(positive_checks),
            "positiveChecks": positive_checks,
            "orderingProbeCount": len(ordering_probes),
            "orderingProbes": ordering_probes,
            "negativeProbeCount": len(negative_probes),
            "negativeProbes": negative_probes,
            "projectionProbeCount": len(projection_probes),
            "projectionProbes": projection_probes,
            "stateIntegrityProbeCount": len(state_integrity_probes),
            "stateIntegrityProbes": state_integrity_probes,
            "concurrency": {
                "passed": concurrency_passed,
                "returnCodes": sorted(
                    item["returnCode"] for item in concurrent_results
                ),
                "acceptedDecisionCount": len(concurrent_data["evidenceDecisions"]),
                "durableDecisionStageCount": len(concurrent_decision_stages),
            },
            "crossOperationConcurrency": {
                "passed": cross_operation_passed,
                "synchronizationGateHeld": True,
                "bothProcessesWaitingWhileGateHeld": cross_waiting,
                "returnCodes": sorted(
                    item["returnCode"] for item in cross_process_results
                ),
                "acceptedDecisionCount": len(cross_data["evidenceDecisions"]),
                "workRequestPresent": any(
                    item["id"] == "evidence.concurrent.work"
                    for item in cross_state["workItems"]
                ),
            },
            "snapshotAndSourceImmutable": all(
                [
                    accepted_checks["snapshotAndSourceProvenanceUnchanged"],
                    rejected_checks["rejectionSnapshotUnchanged"],
                    multi_checks["multiSnapshotUnchanged"],
                    *(item["snapshotUnchanged"] for item in ordering_probes),
                    concurrent_snapshot_before
                    == project_inventory(concurrent / "snapshot"),
                ]
            ),
            "verificationExecutedByHarness": False,
            "temporaryWorkspaceAcceptanceRecorded": True,
            "proposalApprovalRecorded": False,
            "targetRepositoryMutation": False,
            "automaticCodeApplication": False,
            "projectAuthority": PROJECT_AUTHORITY,
            "evidenceDecisionAuthority": EVIDENCE_DECISION_AUTHORITY,
        }
    write_report(output, report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-workspace", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args.snapshot_workspace.resolve(), args.out.resolve())
    print(
        json.dumps(
            {
                "result": report["result"],
                "positiveCheckCount": report["positiveCheckCount"],
                "negativeProbeCount": report["negativeProbeCount"],
                "projectionProbeCount": report["projectionProbeCount"],
            },
            ensure_ascii=True,
        )
    )
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
