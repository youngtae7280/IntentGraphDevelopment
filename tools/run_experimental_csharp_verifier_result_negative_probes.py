"""Run positive and negative probes for typed external verifier-result intake."""

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
    PROJECT_AUTHORITY,
    PROJECT_FILE,
    PROJECT_SCHEMA_VERSION,
    PROPOSAL_AUTHORITY,
    PROPOSAL_ROLE,
    PROPOSAL_SCOPE,
    PROPOSAL_STATUS,
    VERIFIER_EVIDENCE_CONTENT_TYPE,
    VERIFIER_RESULT_AUTHORITY,
    VERIFIER_RESULT_ROLE,
    VERIFIER_RESULT_SCOPE,
    ProjectWorkspaceError,
    add_change_proposal_document,
    add_mapping_candidate,
    add_verifier_result_document,
    add_work_request,
    build_projection,
    digest_bytes,
    draft_change_proposal_from_mapping,
    draft_review_receipt_from_proposal,
    initialize_project,
    project_workspace_write_lock,
    validate_project_workspace,
    validate_projection,
    write_json,
)
from experimental_csharp_workspace import canonical_json


SPECS = {
    "build": ("build-required", "build-evidence", "build-report"),
    "runtime-smoke": ("runtime-smoke-required", "runtime-evidence", "runtime-observation"),
    "static-analysis": ("static-analysis-required", "static-analysis-evidence", "static-analysis-report"),
    "test": ("test-required", "test-evidence", "test-report"),
}


def write_report(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def project_inventory(workspace: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": path.relative_to(workspace).as_posix(),
            "byteLength": path.stat().st_size,
            "digest": digest_bytes(path.read_bytes()),
        }
        for path in sorted(workspace.rglob("*"))
        if path.is_file() and not path.is_symlink()
    ]


def prepare(snapshot: Path, root: Path, project_id: str) -> Path:
    workspace = root / project_id
    initialize_project(snapshot, workspace, project_id, "Typed verifier result probes")
    _, _, _, data = validate_project_workspace(workspace)
    fact_id = next(
        fact["id"]
        for fact in data["facts"]["facts"]
        if isinstance(fact, dict) and fact.get("kind") == "method"
    )
    for verifier_kind, (verification_kind, evidence_kind, _) in sorted(SPECS.items()):
        suffix = verifier_kind.replace("-", ".")
        work_id = f"verify.{suffix}"
        proposal_id = f"proposal.verify.{suffix}"
        add_work_request(workspace, work_id, f"Verify {verifier_kind}", f"Observe one external {verifier_kind} result without accepting it.")
        add_mapping_candidate(workspace, work_id, [fact_id], f"Map one immutable code fact for {verifier_kind} verification.")
        draft_change_proposal_from_mapping(
            workspace,
            proposal_id=proposal_id,
            work_id=work_id,
            title=f"Observe {verifier_kind}",
            summary=f"Declare one typed {verifier_kind} verification and evidence binding.",
            verification_kind=verification_kind,
            verification_summary=f"Run the external {verifier_kind} verifier later.",
            evidence_kind=evidence_kind,
            evidence_summary=f"Bind one typed {evidence_kind} artifact digest later.",
        )
    return workspace


def prepare_multi_binding_proposal(snapshot: Path, root: Path) -> Path:
    workspace = root / "verifier-multi-binding"
    initialize_project(snapshot, workspace, "verifier-multi-binding", "Multi-binding verifier result probe")
    _, _, _, data = validate_project_workspace(workspace)
    fact_id = next(
        fact["id"]
        for fact in data["facts"]["facts"]
        if isinstance(fact, dict) and fact.get("kind") == "method"
    )
    work_id = "verify.multi"
    proposal_id = "proposal.verify.multi"
    add_work_request(workspace, work_id, "Verify multiple requirements", "Observe build and test results independently.")
    add_mapping_candidate(workspace, work_id, [fact_id], "Map one immutable code fact for both declared verifier pairs.")
    proposal = {
        "artifactRole": PROPOSAL_ROLE,
        "schemaVersion": PROJECT_SCHEMA_VERSION,
        "scope": PROPOSAL_SCOPE,
        "id": proposal_id,
        "workItemId": work_id,
        "mappingId": "mapping.verify.multi.candidate",
        "title": "Observe build and test",
        "summary": "Declare two independently addressable verifier requirement pairs.",
        "applicationStatus": PROPOSAL_STATUS,
        "graphDelta": {
            "addedNodes": [
                {
                    "id": f"verification.{proposal_id}.build",
                    "category": "verification",
                    "label": "Build review requirement",
                    "details": {"kind": "build-required", "result": "required-not-run", "summary": "Observe build.", "source": "p9.29-probe"},
                },
                {
                    "id": f"verification.{proposal_id}.test",
                    "category": "verification",
                    "label": "Test review requirement",
                    "details": {"kind": "test-required", "result": "required-not-run", "summary": "Observe tests.", "source": "p9.29-probe"},
                },
            ],
            "changedNodeIds": [fact_id],
            "addedEdges": [
                {
                    "id": f"edge.{proposal_id}.build.verifies",
                    "kind": "verifies",
                    "source": f"intent.{work_id}",
                    "target": f"verification.{proposal_id}.build",
                    "details": {"status": "required-not-run", "source": "p9.29-probe"},
                },
                {
                    "id": f"edge.{proposal_id}.test.verifies",
                    "kind": "verifies",
                    "source": f"intent.{work_id}",
                    "target": f"verification.{proposal_id}.test",
                    "details": {"status": "required-not-run", "source": "p9.29-probe"},
                },
            ],
        },
        "codeDiffs": [],
        "verificationRequirements": [
            {"id": f"verification.requirement.{proposal_id}.build", "kind": "build-required", "summary": "Run external build later."},
            {"id": f"verification.requirement.{proposal_id}.test", "kind": "test-required", "summary": "Run external tests later."},
        ],
        "evidenceRequirements": [
            {"id": f"evidence.requirement.{proposal_id}.build", "kind": "build-evidence", "summary": "Bind build report later."},
            {"id": f"evidence.requirement.{proposal_id}.test", "kind": "test-evidence", "summary": "Bind test report later."},
        ],
        "verifierBindings": [
            {
                "verificationRequirementId": f"verification.requirement.{proposal_id}.build",
                "evidenceRequirementId": f"evidence.requirement.{proposal_id}.build",
                "allowedVerifierKinds": ["build"],
                "requiredArtifactKinds": ["build-report"],
            },
            {
                "verificationRequirementId": f"verification.requirement.{proposal_id}.test",
                "evidenceRequirementId": f"evidence.requirement.{proposal_id}.test",
                "allowedVerifierKinds": ["test"],
                "requiredArtifactKinds": ["test-report"],
            },
        ],
        "authority": PROPOSAL_AUTHORITY,
    }
    add_change_proposal_document(workspace, proposal)
    return workspace


def metrics_for(kind: str) -> dict[str, Any]:
    if kind == "test":
        return {"total": 2, "passed": 2, "failed": 0, "skipped": 0}
    if kind == "runtime-smoke":
        return {"started": True, "observed": True, "responsive": True, "observationSeconds": 2}
    return {"errorCount": 0, "warningCount": 0}


def refresh_evidence(result: dict[str, Any]) -> None:
    payload_bytes = canonical_json(result["evidence"]["payload"])
    result["evidence"]["byteLength"] = len(payload_bytes)
    result["evidence"]["digest"] = digest_bytes(payload_bytes)


def result_for_intake_pair(
    pair: dict[str, Any],
    verifier_kind: str,
    *,
    identifier: str | None = None,
) -> dict[str, Any]:
    result_id = identifier or f"{pair['resultIdPrefix']}.{pair['nextAttempt']}"
    artifact_kind = pair["requiredArtifactKinds"][0]
    artifact_bytes = f"{verifier_kind} evidence for {result_id}\n".encode("utf-8")
    payload = {
        "summary": f"External deterministic {verifier_kind} observation.",
        "exitCode": 0,
        "checks": [{"id": "check.primary", "result": "pass", "summary": "The declared external check reported pass."}],
        "metrics": metrics_for(verifier_kind),
        "artifactRefs": [
            {
                "id": "artifact.primary",
                "kind": artifact_kind,
                "logicalName": f"{verifier_kind}.txt",
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
        "id": result_id,
        "proposalId": pair["proposalId"],
        "verificationRequirementId": pair["verificationRequirement"]["id"],
        "evidenceRequirementId": pair["evidenceRequirement"]["id"],
        "attempt": pair["nextAttempt"],
        "result": "pass",
        "verifier": {"id": f"probe.{verifier_kind}", "kind": verifier_kind, "version": "1.0.0", "deterministic": True},
        "invocation": {"id": f"invocation.{result_id}"[:101], "digest": digest_bytes(canonical_json({"kind": verifier_kind, "attempt": pair["nextAttempt"]}))},
        "subject": {"logicalSourceRoot": pair["logicalSourceRoot"], "snapshotSourceDigest": pair["snapshotSourceDigest"], "proposalDigest": pair["proposalDigest"]},
        "evidence": {"contentType": VERIFIER_EVIDENCE_CONTENT_TYPE, "byteLength": len(payload_bytes), "digest": digest_bytes(payload_bytes), "payload": payload},
        "observationStatus": "observed",
        "acceptanceStatus": "pending",
        "supersedesResultId": pair["supersedesResultId"],
        "authority": VERIFIER_RESULT_AUTHORITY,
    }


def result_for(workspace: Path, verifier_kind: str, *, identifier: str | None = None) -> dict[str, Any]:
    projection, _ = build_projection(workspace)
    proposal_id = f"proposal.verify.{verifier_kind.replace('-', '.')}"
    pair = next(item for item in projection["workflow"]["verifierResultIntake"]["pairs"] if item["proposalId"] == proposal_id)
    return result_for_intake_pair(pair, verifier_kind, identifier=identifier)


def set_outcome(result: dict[str, Any], outcome: str) -> None:
    result["result"] = outcome
    result["evidence"]["payload"]["checks"][0]["result"] = outcome
    result["evidence"]["payload"]["exitCode"] = 0 if outcome == "pass" else (1 if outcome == "fail" else None)
    refresh_evidence(result)


def run_invalid_probe(
    workspace: Path,
    verifier_kind: str,
    identifier: str,
    mutation: Callable[[dict[str, Any]], None],
    expected: str,
    *,
    refresh: bool = False,
) -> dict[str, Any]:
    before = project_inventory(workspace)
    result = result_for(workspace, verifier_kind, identifier=f"result.invalid.{identifier}"[:101])
    mutation(result)
    if refresh:
        refresh_evidence(result)
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
    except Exception as error:  # The validator must be total over arbitrary JSON values.
        return {"id": identifier, "expectedError": expected, "actualError": f"{type(error).__name__}: {error}", "expectedFailureObserved": False, "zeroWrite": before == project_inventory(workspace)}
    return {"id": identifier, "expectedError": expected, "actualError": "invalid result unexpectedly accepted", "expectedFailureObserved": False, "zeroWrite": before == project_inventory(workspace)}


def run(snapshot: Path, output: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="p9.29-verifier-result-") as temporary:
        root = Path(temporary)
        positive = prepare(snapshot, root, "verifier-positive")
        _, before_manifest, _, _ = validate_project_workspace(positive)

        build_result = result_for(positive, "build")
        add_verifier_result_document(positive, build_result)
        draft_review_receipt_from_proposal(
            positive,
            receipt_id="receipt.after.build.result",
            proposal_id=build_result["proposalId"],
            verification_requirement_id=build_result["verificationRequirementId"],
            evidence_requirement_id=build_result["evidenceRequirementId"],
            result="reviewed-pass",
            summary="Review receipt recorded after an observed build result without accepting it.",
        )

        static_before = result_for(positive, "static-analysis")
        draft_review_receipt_from_proposal(
            positive,
            receipt_id="receipt.before.static.result",
            proposal_id=static_before["proposalId"],
            verification_requirement_id=static_before["verificationRequirementId"],
            evidence_requirement_id=static_before["evidenceRequirementId"],
            result="reviewed-pass",
            summary="Review receipt recorded before an observed static-analysis result.",
        )
        for kind in ("runtime-smoke", "static-analysis", "test"):
            add_verifier_result_document(positive, result_for(positive, kind))

        test_fail = result_for(positive, "test")
        set_outcome(test_fail, "fail")
        fail_response = add_verifier_result_document(positive, test_fail)
        test_blocked = result_for(positive, "test")
        set_outcome(test_blocked, "blocked")
        blocked_response = add_verifier_result_document(positive, test_blocked)
        test_pass = result_for(positive, "test")
        pass_response = add_verifier_result_document(positive, test_pass)

        positive_state, after_manifest, _, positive_data = validate_project_workspace(positive)
        positive_projection, _ = build_projection(positive)
        projection_errors = validate_projection(positive_projection)
        current_result_ids = {
            pair["currentResult"]["id"]
            for pair in positive_projection["workflow"]["verifierResultIntake"]["pairs"]
            if pair["currentResult"] is not None
        }
        result_nodes = [node for node in positive_projection["graph"]["nodes"] if node["category"] == "verifier-result"]
        result_stages = [stage for stage in positive_projection["workflow"]["workStageTimeline"] if stage["kind"] == "verifier-result-imported"]
        positive_checks = {
            "fourTypedKindsImported": {item["verifier"]["kind"] for item in positive_data["verifierResults"]} == set(SPECS),
            "allResultsObservedPending": all(item["observationStatus"] == "observed" and item["acceptanceStatus"] == "pending" for item in positive_data["verifierResults"]),
            "pendingOutcomesNeverBlockWork": fail_response["verificationStatus"] == "verifier-result-fail" and blocked_response["verificationStatus"] == "verifier-result-blocked" and all(item["status"] != "blocked" for item in positive_state["workItems"]),
            "supersessionReturnsToPassingObservation": pass_response["verificationStatus"] == "verifier-result-pass" and test_pass["attempt"] == 4 and test_pass["supersedesResultId"] == test_blocked["id"],
            "receiptOrderingPreserved": next(item for item in positive_state["workItems"] if item["id"] == "verify.build")["verificationStatus"] == "verifier-result-pass" and next(item for item in positive_state["workItems"] if item["id"] == "verify.static.analysis")["verificationStatus"] == "verifier-result-pass",
            "projectionContractPasses": not projection_errors,
            "currentAndSupersededVisible": len(current_result_ids) == 4 and sum(bool(node["details"]["current"]) for node in result_nodes) == 4 and len(result_nodes) == 7,
            "oneDurableRevisionPerResultStage": len(result_stages) == 7 and all(stage["durableRevision"] and len(stage["revisionIds"]) == 1 for stage in result_stages),
            "allCoveragePassingPending": all(item["allPairsObservedPassing"] and item["acceptanceStatus"] == "pending" for item in positive_projection["workflow"]["verifierResultCoverage"]),
            "snapshotProvenanceUnchanged": before_manifest["source"] == after_manifest["source"],
        }

        multi_binding = prepare_multi_binding_proposal(snapshot, root)
        multi_projection, _ = build_projection(multi_binding)
        multi_pairs = [
            item
            for item in multi_projection["workflow"]["verifierResultIntake"]["pairs"]
            if item["proposalId"] == "proposal.verify.multi"
        ]
        multi_default_ids = [f"{item['resultIdPrefix']}.{item['nextAttempt']}" for item in multi_pairs]
        for pair in multi_pairs:
            add_verifier_result_document(
                multi_binding,
                result_for_intake_pair(pair, pair["allowedVerifierKinds"][0]),
            )
        _, _, _, multi_data = validate_project_workspace(multi_binding)
        multi_projection_after, _ = build_projection(multi_binding)
        multi_binding_passed = (
            len(multi_pairs) == 2
            and len(set(multi_default_ids)) == 2
            and all(len(identifier) <= 101 for identifier in multi_default_ids)
            and len(multi_data["verifierResults"]) == 2
            and not validate_projection(multi_projection_after)
        )

        negative = prepare(snapshot, root, "verifier-negative")
        probes = [
            run_invalid_probe(negative, "test", "wrong-role", lambda value: value.__setitem__("artifactRole", "wrong-role"), "role, schema version, or scope is invalid"),
            run_invalid_probe(negative, "test", "non-string-proposal-id", lambda value: value.__setitem__("proposalId", []), "proposal id must be a string"),
            run_invalid_probe(negative, "test", "unknown-requirement", lambda value: value.__setitem__("verificationRequirementId", "verification.requirement.missing"), "requirement pair is not declared"),
            run_invalid_probe(negative, "test", "stale-source-digest", lambda value: value["subject"].__setitem__("snapshotSourceDigest", "sha256:" + "0" * 64), "subject digest is stale or mismatched"),
            run_invalid_probe(negative, "test", "wrong-verifier-kind", lambda value: value["verifier"].__setitem__("kind", "build"), "deterministic and typed"),
            run_invalid_probe(negative, "test", "all-tests-skipped", lambda value: value["evidence"]["payload"].__setitem__("metrics", {"total": 1, "passed": 0, "failed": 0, "skipped": 1}), "typed metrics", refresh=True),
            run_invalid_probe(negative, "test", "inconsistent-test-total", lambda value: value["evidence"]["payload"]["metrics"].__setitem__("total", 99), "test metrics total is inconsistent", refresh=True),
            run_invalid_probe(negative, "runtime-smoke", "runtime-responsive-not-boolean", lambda value: value["evidence"]["payload"]["metrics"].__setitem__("responsive", "yes"), "runtime-smoke boolean metrics are invalid", refresh=True),
            run_invalid_probe(negative, "test", "missing-required-artifact-kind", lambda value: value["evidence"]["payload"]["artifactRefs"][0].__setitem__("kind", "stdout-log"), "missing an artifact kind required", refresh=True),
            run_invalid_probe(negative, "test", "unsafe-artifact-name", lambda value: value["evidence"]["payload"]["artifactRefs"][0].__setitem__("logicalName", "../secret.txt"), "artifact reference is invalid", refresh=True),
            run_invalid_probe(negative, "test", "unsorted-checks", lambda value: value["evidence"]["payload"]["checks"].append({"id": "check.alpha", "result": "pass", "summary": "Out of order."}), "checks must be uniquely sorted", refresh=True),
            run_invalid_probe(negative, "test", "bad-evidence-digest", lambda value: value["evidence"].__setitem__("digest", "sha256:" + "0" * 64), "evidence digest or byte length is invalid"),
            run_invalid_probe(negative, "test", "wrong-attempt", lambda value: value.__setitem__("attempt", 2), "supersedes chain is invalid"),
            run_invalid_probe(negative, "test", "acceptance-promoted", lambda value: value.__setitem__("acceptanceStatus", "accepted"), "observed and pending acceptance"),
            run_invalid_probe(negative, "test", "authority-promoted", lambda value: value.__setitem__("authority", {**VERIFIER_RESULT_AUTHORITY, "approvalRecorded": True}), "authority must remain import-only"),
        ]

        projection_mutations = []
        for identifier, mutate, expected in (
            ("missing-verifier-results", lambda value: value["workflow"].pop("verifierResults"), "review receipt state is invalid"),
            ("missing-verifier-intake", lambda value: value["workflow"].pop("verifierResultIntake"), "review receipt state is invalid"),
            ("wrong-current-result-node", lambda value: next(node for node in value["graph"]["nodes"] if node["category"] == "verifier-result" and not node["details"]["current"])["details"].__setitem__("current", True), "verifier result graph nodes are invalid"),
        ):
            mutated = copy.deepcopy(positive_projection)
            mutate(mutated)
            errors = validate_projection(mutated)
            projection_mutations.append({"id": identifier, "expectedFailureObserved": any(expected in error for error in errors), "errors": errors})

        concurrent = prepare(snapshot, root, "verifier-concurrent")
        first = result_for(concurrent, "test", identifier="result.concurrent.a")
        second = result_for(concurrent, "test", identifier="result.concurrent.b")
        first_path = root / "concurrent-a.json"
        second_path = root / "concurrent-b.json"
        write_json(first_path, first)
        write_json(second_path, second)
        command_prefix = [sys.executable, str(Path(__file__).with_name("intentgraph.py")), "add-experimental-csharp-verifier-result", "--workspace", str(concurrent), "--result"]
        processes = [
            subprocess.Popen([*command_prefix, str(first_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True),
            subprocess.Popen([*command_prefix, str(second_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True),
        ]
        process_results = [{"returnCode": process.wait(), "stdout": process.stdout.read(), "stderr": process.stderr.read()} for process in processes]
        concurrent_state, _, _, concurrent_data = validate_project_workspace(concurrent)
        concurrency_passed = sorted(item["returnCode"] for item in process_results) == [0, 2] and len(concurrent_data["verifierResults"]) == 1 and len(concurrent_state["verifierResults"]) == 1

        cross_operation = prepare(snapshot, root, "verifier-cross-operation")
        cross_result = result_for(cross_operation, "test", identifier="result.concurrent.cross.operation")
        cross_result_path = root / "cross-operation-result.json"
        write_json(cross_result_path, cross_result)
        cross_commands = [
            [
                sys.executable,
                str(Path(__file__).with_name("intentgraph.py")),
                "add-experimental-csharp-verifier-result",
                "--workspace",
                str(cross_operation),
                "--result",
                str(cross_result_path),
            ],
            [
                sys.executable,
                str(Path(__file__).with_name("intentgraph.py")),
                "add-experimental-csharp-work-request",
                "--workspace",
                str(cross_operation),
                "--work-id",
                "verify.concurrent.work",
                "--title",
                "Concurrent work request",
                "--request",
                "Record one work request concurrently with a verifier result.",
            ],
        ]
        # Hold the same writer lock used by production mutations while both
        # subprocesses start. Releasing this gate makes the two different
        # operations contend for the workspace lock instead of merely hoping
        # their critical sections happen to overlap.
        with project_workspace_write_lock(cross_operation):
            cross_processes = [
                subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                for command in cross_commands
            ]
            time.sleep(0.25)
            cross_processes_waiting_at_gate = all(process.poll() is None for process in cross_processes)
        cross_process_results = [
            {"returnCode": process.wait(), "stdout": process.stdout.read(), "stderr": process.stderr.read()}
            for process in cross_processes
        ]
        cross_state, _, _, cross_data = validate_project_workspace(cross_operation)
        cross_operation_passed = (
            cross_processes_waiting_at_gate
            and all(item["returnCode"] == 0 for item in cross_process_results)
            and any(item["id"] == "verify.concurrent.work" for item in cross_state["workItems"])
            and len(cross_data["verifierResults"]) == 1
            and len({revision["id"] for revision in cross_state["workStageRevisions"]})
            == len(cross_state["workStageRevisions"])
        )

        passed = (
            all(positive_checks.values())
            and multi_binding_passed
            and all(item["expectedFailureObserved"] and item["zeroWrite"] for item in probes)
            and all(item["expectedFailureObserved"] for item in projection_mutations)
            and concurrency_passed
            and cross_operation_passed
        )
        report = {
            "artifactRole": "intentgraph-experimental-csharp-verifier-result-probes-report",
            "status": "intentgraph-experimental-csharp-verifier-result-probes-" + ("pass" if passed else "fail"),
            "scope": "p9.29-typed-verifier-result-intake",
            "result": "pass" if passed else "fail",
            "positiveChecks": positive_checks,
            "multiBinding": {
                "passed": multi_binding_passed,
                "pairCount": len(multi_pairs),
                "defaultResultIds": multi_default_ids,
                "acceptedResultCount": len(multi_data["verifierResults"]),
            },
            "negativeProbeCount": len(probes),
            "negativeProbes": probes,
            "projectionProbeCount": len(projection_mutations),
            "projectionProbes": projection_mutations,
            "concurrency": {"passed": concurrency_passed, "processes": process_results, "acceptedResultCount": len(concurrent_data["verifierResults"])},
            "crossOperationConcurrency": {
                "passed": cross_operation_passed,
                "synchronizationGateHeld": True,
                "bothProcessesWaitingWhileGateHeld": cross_processes_waiting_at_gate,
                "processes": cross_process_results,
                "workRequestPresent": any(item["id"] == "verify.concurrent.work" for item in cross_state["workItems"]),
                "acceptedResultCount": len(cross_data["verifierResults"]),
            },
            "targetRepositoryMutation": False,
            "verificationExecutedByHarness": False,
            "acceptanceRecorded": False,
            "projectAuthority": PROJECT_AUTHORITY,
            "verifierResultAuthority": VERIFIER_RESULT_AUTHORITY,
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
    print(json.dumps({"result": report["result"], "negativeProbeCount": report["negativeProbeCount"], "projectionProbeCount": report["projectionProbeCount"]}, ensure_ascii=True))
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
