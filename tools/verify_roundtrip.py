"""Tiny M5 round-trip and evidence/authority/history verifier for B0."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any


VERIFIER_CONTRACT = "roundtrip-b0-m5-eah-v0"
COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")
ALLOWED_EVIDENCE_STATUS = {"planned", "pass", "fail", "blocked", "superseded"}
ALLOWED_OBSERVATION_STATUS = {"planned", "observed", "missing"}
ALLOWED_ACCEPTANCE_STATUS = {"accepted", "rejected", "pending", "superseded"}
ALLOWED_DECISION_STATUS = {"accepted", "rejected", "pending", "superseded"}
ALLOWED_HISTORY_STATUS = {"accepted", "rejected", "pending", "superseded"}
ALLOWED_ACTOR_TYPES = {"human", "ai", "tool", "system"}
ALLOWED_AUTHORITY_TARGET_KINDS = {"evidence.record", "history.delta", "projection.target"}


class VerifyError(Exception):
    """Raised when the verifier cannot produce a valid report."""


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise VerifyError(f"{path} must contain a JSON object.")
    return data


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def prefixed_sha256(text: str) -> str:
    return f"sha256:{sha256_text(text)}"


def normalize_graph(graph: dict[str, Any]) -> dict[str, Any]:
    normalized = json.loads(json.dumps(graph))
    normalized.pop("status", None)
    if isinstance(normalized.get("nodes"), list):
        normalized["nodes"] = sorted(normalized["nodes"], key=lambda node: node["id"])
    if isinstance(normalized.get("edges"), list):
        normalized["edges"] = sorted(normalized["edges"], key=lambda edge: edge["id"])
    return normalized


def digest_graph(graph: dict[str, Any]) -> str:
    return prefixed_sha256(canonical_json(graph))


def count_by_kind(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        kind = item.get("kind", "<missing>")
        counts[kind] = counts.get(kind, 0) + 1
    return dict(sorted(counts.items()))


def graph_indexes(graph: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[str, dict[str, Any]] = {}
    for node in graph.get("nodes", []):
        if isinstance(node, dict) and isinstance(node.get("id"), str):
            nodes[node["id"]] = node
    for edge in graph.get("edges", []):
        if isinstance(edge, dict) and isinstance(edge.get("id"), str):
            edges[edge["id"]] = edge
    return nodes, edges


def attrs(node: dict[str, Any]) -> dict[str, Any]:
    attributes = node.get("attributes")
    return attributes if isinstance(attributes, dict) else {}


def authorizes_edges_by_target(edges: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    by_target: dict[str, list[str]] = {}
    for edge in edges.values():
        if edge.get("kind") == "authorizes":
            by_target.setdefault(edge["to"], []).append(edge["from"])
    return {target: sorted(authorities) for target, authorities in by_target.items()}


def authorizes_edges_by_authority(edges: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    by_authority: dict[str, list[str]] = {}
    for edge in edges.values():
        if edge.get("kind") == "authorizes":
            by_authority.setdefault(edge["from"], []).append(edge["to"])
    return {authority: sorted(targets) for authority, targets in by_authority.items()}


def changed_targets_by_delta(edges: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    by_delta: dict[str, list[str]] = {}
    for edge in edges.values():
        if edge.get("kind") == "changes":
            by_delta.setdefault(edge["from"], []).append(edge["to"])
    return {delta: sorted(targets) for delta, targets in by_delta.items()}


def evidence_links_by_target(edges: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    by_evidence: dict[str, list[str]] = {}
    for edge in edges.values():
        if edge.get("kind") == "evidenced_by":
            by_evidence.setdefault(edge["to"], []).append(edge["from"])
    return {evidence: sorted(sources) for evidence, sources in by_evidence.items()}


def authority_accepted(node: dict[str, Any] | None) -> bool:
    if not node or node.get("kind") != "authority.record":
        return False
    return attrs(node).get("decisionStatus") == "accepted"


def missing_attrs(attributes: dict[str, Any], required: set[str]) -> list[str]:
    return sorted(required - set(attributes))


def normalized_actor_type(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip().casefold()


def git_commit_exists(commit: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
            cwd=Path.cwd(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        return False
    return result.returncode == 0


def artifact_ref_checks(artifact_refs: Any, current_report_path: Path | None) -> list[dict[str, Any]]:
    if not isinstance(artifact_refs, list):
        return []
    current_report = current_report_path.as_posix() if current_report_path else None
    checks: list[dict[str, Any]] = []
    for ref in artifact_refs:
        if not isinstance(ref, str):
            continue
        if ref == current_report:
            checks.append(
                {
                    "ref": ref,
                    "exists": True,
                    "jsonResult": "current-run",
                    "jsonResultPass": None,
                    "resolution": "current-report-output",
                }
            )
        else:
            path = Path(ref)
            json_result: str | None = None
            json_result_pass: bool | None = None
            if path.exists() and path.suffix == ".json":
                try:
                    loaded = json.loads(path.read_text(encoding="utf-8-sig"))
                    if isinstance(loaded, dict):
                        result = loaded.get("result")
                        if isinstance(result, str):
                            json_result = result
                            json_result_pass = result == "pass"
                except (OSError, json.JSONDecodeError):
                    json_result_pass = False
            checks.append(
                {
                    "ref": ref,
                    "exists": path.exists(),
                    "jsonResult": json_result,
                    "jsonResultPass": json_result_pass,
                    "resolution": "local-path",
                }
            )
    return checks


def require_preconditions(
    original: dict[str, Any],
    reconstructed: dict[str, Any],
    metadata: dict[str, Any],
    code_only: dict[str, Any],
) -> list[str]:
    diagnostics: list[str] = []
    original_digest = digest_graph(original)
    if metadata.get("graphDigest") != original_digest:
        raise VerifyError("Metadata graphDigest does not match original graph digest.")
    if original.get("status") != "m1-fixture":
        raise VerifyError("Original graph must have status m1-fixture.")
    if reconstructed.get("status") != "m3-reconstructed":
        raise VerifyError("Reconstructed graph must have status m3-reconstructed.")
    if code_only.get("claim") != "lossy-code-only-projection":
        raise VerifyError("Code-only projection must declare lossy-code-only-projection.")
    if metadata.get("projectionRules", {}).get("unclassified") != []:
        raise VerifyError("Metadata projectionRules.unclassified must be empty.")
    diagnostics.append("preconditions passed")
    return diagnostics


def domain_status(graph: dict[str, Any]) -> dict[str, Any]:
    node_counts = count_by_kind(graph.get("nodes", []))
    return {
        "evidenceRecords": node_counts.get("evidence.record", 0),
        "authorityRecords": node_counts.get("authority.record", 0),
        "historyDeltas": node_counts.get("history.delta", 0),
        "evidencePreserved": node_counts.get("evidence.record", 0) > 0,
        "authorityPreserved": node_counts.get("authority.record", 0) > 0,
        "historyPreserved": node_counts.get("history.delta", 0) > 0,
    }


def domain_subgraph(graph: dict[str, Any], node_kinds: set[str], edge_kinds: set[str]) -> dict[str, Any]:
    node_ids = {
        node["id"]
        for node in graph.get("nodes", [])
        if node.get("kind") in node_kinds
    }
    edges = [
        edge
        for edge in graph.get("edges", [])
        if edge.get("kind") in edge_kinds or edge.get("from") in node_ids or edge.get("to") in node_ids
    ]
    connected_node_ids = set(node_ids)
    for edge in edges:
        connected_node_ids.add(edge["from"])
        connected_node_ids.add(edge["to"])
    nodes = [
        node
        for node in graph.get("nodes", [])
        if node.get("id") in connected_node_ids
    ]
    return {
        "nodes": sorted(nodes, key=lambda node: node["id"]),
        "edges": sorted(edges, key=lambda edge: edge["id"]),
    }


def domain_preservation(original: dict[str, Any], reconstructed: dict[str, Any]) -> dict[str, Any]:
    domains = {
        "evidence": ({"evidence.record"}, {"evidenced_by"}),
        "authority": ({"authority.record"}, {"authorizes"}),
        "history": ({"history.delta"}, {"changes"}),
    }
    result: dict[str, Any] = {}
    for domain, (node_kinds, edge_kinds) in domains.items():
        original_subgraph = domain_subgraph(original, node_kinds, edge_kinds)
        reconstructed_subgraph = domain_subgraph(reconstructed, node_kinds, edge_kinds)
        original_digest = digest_graph(original_subgraph)
        reconstructed_digest = digest_graph(reconstructed_subgraph)
        original_node_ids = [node["id"] for node in original_subgraph["nodes"] if node.get("kind") in node_kinds]
        reconstructed_node_ids = [
            node["id"]
            for node in reconstructed_subgraph["nodes"]
            if node.get("kind") in node_kinds
        ]
        result[domain] = {
            "originalDigest": original_digest,
            "reconstructedDigest": reconstructed_digest,
            "matched": original_digest == reconstructed_digest,
            "domainNodeIds": original_node_ids,
            "reconstructedDomainNodeIds": reconstructed_node_ids,
        }
    return result


def validate_evidence_semantics(graph: dict[str, Any], current_report_path: Path | None) -> dict[str, Any]:
    nodes, edges = graph_indexes(graph)
    by_target = authorizes_edges_by_target(edges)
    evidence_links = evidence_links_by_target(edges)
    errors: list[str] = []
    records: list[dict[str, Any]] = []
    required = {
        "evidenceType",
        "status",
        "summary",
        "recordedBy",
        "observationStatus",
        "acceptanceStatus",
        "artifactRefs",
    }

    evidence_nodes = sorted(
        (node for node in nodes.values() if node.get("kind") == "evidence.record"),
        key=lambda node: node["id"],
    )
    for node in evidence_nodes:
        node_id = node["id"]
        attributes = attrs(node)
        missing = missing_attrs(attributes, required)
        if missing:
            errors.append(f"{node_id} missing evidence attributes: {missing}")

        status = attributes.get("status")
        observation_status = attributes.get("observationStatus")
        acceptance_status = attributes.get("acceptanceStatus")
        accepted_by = attributes.get("acceptedByAuthority")
        artifact_refs = attributes.get("artifactRefs")
        artifact_checks = artifact_ref_checks(artifact_refs, current_report_path)
        authorized_by = by_target.get(node_id, [])
        linked_from = evidence_links.get(node_id, [])

        if status not in ALLOWED_EVIDENCE_STATUS:
            errors.append(f"{node_id} has invalid evidence status: {status}")
        if observation_status not in ALLOWED_OBSERVATION_STATUS:
            errors.append(f"{node_id} has invalid observationStatus: {observation_status}")
        if acceptance_status not in ALLOWED_ACCEPTANCE_STATUS:
            errors.append(f"{node_id} has invalid acceptanceStatus: {acceptance_status}")
        if not isinstance(artifact_refs, list) or not all(isinstance(item, str) for item in artifact_refs):
            errors.append(f"{node_id} artifactRefs must be an array of strings")
        if isinstance(artifact_refs, list):
            for check in artifact_checks:
                if not check["exists"]:
                    errors.append(f"{node_id} artifactRef does not exist: {check['ref']}")
        if not linked_from and attributes.get("scope") != "milestone":
            errors.append(f"{node_id} must be linked by evidenced_by or declare milestone scope")

        if acceptance_status == "accepted":
            if not isinstance(accepted_by, str):
                errors.append(f"{node_id} accepted evidence must name acceptedByAuthority")
            elif accepted_by not in nodes:
                errors.append(f"{node_id} acceptedByAuthority references missing node: {accepted_by}")
            elif not authority_accepted(nodes[accepted_by]):
                errors.append(f"{node_id} acceptedByAuthority is not accepted authority: {accepted_by}")
            if isinstance(accepted_by, str) and accepted_by not in authorized_by:
                errors.append(f"{node_id} must be authorized by {accepted_by}")
            if observation_status != "observed":
                errors.append(f"{node_id} accepted evidence must be observed first")
            if status in {"fail", "blocked", "superseded"}:
                errors.append(f"{node_id} accepted evidence cannot have status {status}")
            if status == "planned":
                if attributes.get("claimScope") != "plan-only" or attributes.get("runtimeProof") is not False:
                    errors.append(f"{node_id} planned evidence can only be accepted with plan-only scope")
            if attributes.get("evidenceType") == "verifier-report":
                if status != "pass":
                    errors.append(f"{node_id} verifier-report evidence must have status pass")
                if not any(
                    check["resolution"] == "current-report-output"
                    or check.get("jsonResultPass") is True
                    for check in artifact_checks
                ):
                    errors.append(f"{node_id} verifier-report evidence must reference a passing report")

        records.append(
            {
                "id": node_id,
                "evidenceType": attributes.get("evidenceType"),
                "status": status,
                "claimScope": attributes.get("claimScope"),
                "runtimeProof": attributes.get("runtimeProof"),
                "observationStatus": observation_status,
                "acceptanceStatus": acceptance_status,
                "acceptedByAuthority": accepted_by,
                "authorizedBy": authorized_by,
                "linkedFrom": linked_from,
                "artifactRefs": artifact_refs if isinstance(artifact_refs, list) else [],
                "artifactChecks": artifact_checks,
            }
        )

    return {
        "result": "pass" if not errors else "fail",
        "recordCount": len(records),
        "observedCount": sum(1 for record in records if record["observationStatus"] == "observed"),
        "acceptedCount": sum(1 for record in records if record["acceptanceStatus"] == "accepted"),
        "observedDoesNotImplyAccepted": True,
        "records": records,
        "errors": errors,
    }


def validate_authority_semantics(graph: dict[str, Any]) -> dict[str, Any]:
    nodes, edges = graph_indexes(graph)
    by_authority = authorizes_edges_by_authority(edges)
    errors: list[str] = []
    records: list[dict[str, Any]] = []
    required = {
        "proposer",
        "proposerType",
        "requiredAuthority",
        "validator",
        "decidedBy",
        "decidedByType",
        "decision",
        "decisionStatus",
    }

    authority_nodes = sorted(
        (node for node in nodes.values() if node.get("kind") == "authority.record"),
        key=lambda node: node["id"],
    )
    for node in authority_nodes:
        node_id = node["id"]
        attributes = attrs(node)
        missing = missing_attrs(attributes, required)
        if missing:
            errors.append(f"{node_id} missing authority attributes: {missing}")

        decision_status = attributes.get("decisionStatus")
        proposer_type = normalized_actor_type(attributes.get("proposerType"))
        decided_by_type = normalized_actor_type(attributes.get("decidedByType"))
        authorized_targets = by_authority.get(node_id, [])
        target_kinds: dict[str, str | None] = {}
        allowed_targets: list[str] = []
        for target in authorized_targets:
            target_node = nodes.get(target)
            target_kind = target_node.get("kind") if target_node else None
            target_kinds[target] = target_kind
            if target_kind in ALLOWED_AUTHORITY_TARGET_KINDS:
                allowed_targets.append(target)
            elif target_node is None:
                errors.append(f"{node_id} authorizes missing target: {target}")
            else:
                errors.append(f"{node_id} authorizes unsupported target kind {target_kind}: {target}")

        if decision_status not in ALLOWED_DECISION_STATUS:
            errors.append(f"{node_id} has invalid decisionStatus: {decision_status}")
        if proposer_type not in ALLOWED_ACTOR_TYPES:
            errors.append(f"{node_id} has invalid proposerType: {attributes.get('proposerType')}")
        if decided_by_type not in ALLOWED_ACTOR_TYPES:
            errors.append(f"{node_id} has invalid decidedByType: {attributes.get('decidedByType')}")
        if decision_status == "accepted":
            if decided_by_type == "ai":
                errors.append(f"{node_id} accepted authority must not have ai as decidedByType")
            if not allowed_targets:
                errors.append(f"{node_id} accepted authority must authorize at least one allowed target")

        records.append(
            {
                "id": node_id,
                "proposerType": proposer_type,
                "requiredAuthority": attributes.get("requiredAuthority"),
                "validator": attributes.get("validator"),
                "decidedByType": decided_by_type,
                "decision": attributes.get("decision"),
                "decisionStatus": decision_status,
                "authorizedTargets": authorized_targets,
                "authorizedTargetKinds": target_kinds,
                "allowedAuthorizedTargets": sorted(allowed_targets),
            }
        )

    return {
        "result": "pass" if not errors else "fail",
        "recordCount": len(records),
        "acceptedCount": sum(1 for record in records if record["decisionStatus"] == "accepted"),
        "aiFinalAuthorityCount": sum(
            1
            for record in records
            if record["decisionStatus"] == "accepted" and record["decidedByType"] == "ai"
        ),
        "records": records,
        "errors": errors,
    }


def validate_history_semantics(graph: dict[str, Any]) -> dict[str, Any]:
    nodes, edges = graph_indexes(graph)
    by_target = authorizes_edges_by_target(edges)
    by_delta = changed_targets_by_delta(edges)
    errors: list[str] = []
    records: list[dict[str, Any]] = []
    sequences: set[int] = set()
    accepted_sequences: list[int] = []
    required = {"sequence", "changeType", "summary", "status", "gitCommit"}

    history_nodes = sorted(
        (node for node in nodes.values() if node.get("kind") == "history.delta"),
        key=lambda node: node["id"],
    )
    for node in history_nodes:
        node_id = node["id"]
        attributes = attrs(node)
        missing = missing_attrs(attributes, required)
        if missing:
            errors.append(f"{node_id} missing history attributes: {missing}")

        sequence = attributes.get("sequence")
        status = attributes.get("status")
        git_commit = attributes.get("gitCommit")
        git_commit_verified = False
        changed_targets = by_delta.get(node_id, [])
        authorizers = by_target.get(node_id, [])
        accepted_authorizers = [
            authority_id
            for authority_id in authorizers
            if authority_accepted(nodes.get(authority_id))
        ]

        if not isinstance(sequence, int) or sequence <= 0:
            errors.append(f"{node_id} sequence must be a positive integer")
        elif sequence in sequences:
            errors.append(f"{node_id} duplicates history sequence {sequence}")
        else:
            sequences.add(sequence)

        if status not in ALLOWED_HISTORY_STATUS:
            errors.append(f"{node_id} has invalid history status: {status}")
        if status == "accepted":
            if not changed_targets:
                errors.append(f"{node_id} accepted history delta must change at least one node")
            if not accepted_authorizers:
                errors.append(f"{node_id} accepted history delta must have accepted authority")
            if isinstance(sequence, int) and sequence > 0:
                accepted_sequences.append(sequence)

        if git_commit is None:
            if attributes.get("gitCommitBoundary") != "pending-current-milestone":
                errors.append(f"{node_id} null gitCommit requires pending-current-milestone boundary")
            if not attributes.get("gitCommitReason"):
                errors.append(f"{node_id} null gitCommit requires gitCommitReason")
        elif not isinstance(git_commit, str) or not COMMIT_RE.match(git_commit):
            errors.append(f"{node_id} gitCommit must be a Git commit hex string or null with boundary")
        elif not git_commit_exists(git_commit):
            errors.append(f"{node_id} gitCommit does not resolve to a local commit: {git_commit}")
        else:
            git_commit_verified = True

        records.append(
            {
                "id": node_id,
                "sequence": sequence,
                "changeType": attributes.get("changeType"),
                "status": status,
                "gitCommit": git_commit,
                "gitCommitVerified": git_commit_verified,
                "gitCommitBoundary": attributes.get("gitCommitBoundary"),
                "authorizedBy": authorizers,
                "acceptedAuthorizers": accepted_authorizers,
                "changedTargets": changed_targets,
            }
        )

    expected_sequences = list(range(1, len(accepted_sequences) + 1))
    if sorted(accepted_sequences) != expected_sequences:
        errors.append(
            f"accepted history sequences must be contiguous from 1: got {sorted(accepted_sequences)}"
        )

    return {
        "result": "pass" if not errors else "fail",
        "recordCount": len(records),
        "acceptedCount": sum(1 for record in records if record["status"] == "accepted"),
        "gitLinkedCount": sum(1 for record in records if isinstance(record["gitCommit"], str)),
        "gitVerifiedCount": sum(1 for record in records if record["gitCommitVerified"]),
        "acceptedSequenceContiguous": sorted(accepted_sequences) == expected_sequences,
        "pendingCurrentMilestoneCount": sum(
            1
            for record in records
            if record["gitCommit"] is None
            and record["gitCommitBoundary"] == "pending-current-milestone"
        ),
        "records": records,
        "errors": errors,
    }


def validate_semantics(graph: dict[str, Any], current_report_path: Path | None) -> dict[str, Any]:
    evidence = validate_evidence_semantics(graph, current_report_path)
    authority = validate_authority_semantics(graph)
    history = validate_history_semantics(graph)
    errors = evidence["errors"] + authority["errors"] + history["errors"]
    return {
        "result": "pass" if not errors else "fail",
        "evidence": evidence,
        "authority": authority,
        "history": history,
        "errors": errors,
    }


def build_report(
    report_path: Path,
    original_path: Path,
    reconstructed_path: Path,
    metadata_path: Path,
    code_only_path: Path,
    original: dict[str, Any],
    reconstructed: dict[str, Any],
    metadata: dict[str, Any],
    code_only: dict[str, Any],
) -> dict[str, Any]:
    diagnostics = require_preconditions(original, reconstructed, metadata, code_only)
    normalized_original = normalize_graph(original)
    normalized_reconstructed = normalize_graph(reconstructed)
    normalized_original_digest = digest_graph(normalized_original)
    normalized_reconstructed_digest = digest_graph(normalized_reconstructed)
    graph_equal = normalized_original_digest == normalized_reconstructed_digest

    original_node_counts = count_by_kind(original.get("nodes", []))
    reconstructed_node_counts = count_by_kind(reconstructed.get("nodes", []))
    original_edge_counts = count_by_kind(original.get("edges", []))
    reconstructed_edge_counts = count_by_kind(reconstructed.get("edges", []))

    mismatches: list[str] = []
    if not graph_equal:
        mismatches.append("normalized graph digests differ")
    if original_node_counts != reconstructed_node_counts:
        mismatches.append("node kind counts differ")
    if original_edge_counts != reconstructed_edge_counts:
        mismatches.append("edge kind counts differ")

    reconstructed_domain = domain_status(reconstructed)
    domain_preservation_report = domain_preservation(original, reconstructed)
    original_semantics = validate_semantics(original, report_path)
    reconstructed_semantics = validate_semantics(reconstructed, report_path)
    for key in ["evidencePreserved", "authorityPreserved", "historyPreserved"]:
        if not reconstructed_domain[key]:
            mismatches.append(f"{key} is false")
    for domain, domain_report in domain_preservation_report.items():
        if not domain_report["matched"]:
            mismatches.append(f"{domain} domain subgraph digest differs")
    if original_semantics["result"] != "pass":
        mismatches.append("original evidence/authority/history semantics failed")
    if reconstructed_semantics["result"] != "pass":
        mismatches.append("reconstructed evidence/authority/history semantics failed")

    result = "pass" if graph_equal and not mismatches else "fail"
    if result == "pass":
        diagnostics.append("normalized metadata-backed graph equality passed")
    else:
        diagnostics.extend(mismatches)

    return {
        "reportVersion": "0.2.0",
        "verifierContract": VERIFIER_CONTRACT,
        "benchmarkId": original.get("benchmarkId"),
        "result": result,
        "graphEqual": graph_equal,
        "equalityMode": "GraphEqualAfterNormalization",
        "m5ClaimScope": {
            "level4Claim": "metadata-backed preservation with semantic validation",
            "codeDerivedRecovery": False,
            "hiddenStateSnapshotUsed": bool(metadata.get("hiddenState", {}).get("sourceGraphSnapshot")),
        },
        "normalizationRules": [
            "remove top-level lifecycle field: status",
            "sort nodes by id",
            "sort edges by id",
            "sort object keys for canonical JSON",
        ],
        "inputs": {
            "originalGraph": original_path.as_posix(),
            "reconstructedGraph": reconstructed_path.as_posix(),
            "metadata": metadata_path.as_posix(),
            "codeOnlyProjection": code_only_path.as_posix(),
        },
        "rawStatuses": {
            "original": original.get("status"),
            "reconstructed": reconstructed.get("status"),
            "allowedPair": ["m1-fixture", "m3-reconstructed"],
        },
        "digests": {
            "originalGraph": digest_graph(original),
            "reconstructedGraph": digest_graph(reconstructed),
            "metadataGraphDigest": metadata.get("graphDigest"),
            "normalizedOriginalGraph": normalized_original_digest,
            "normalizedReconstructedGraph": normalized_reconstructed_digest,
        },
        "counts": {
            "originalNodesByKind": original_node_counts,
            "reconstructedNodesByKind": reconstructed_node_counts,
            "originalEdgesByKind": original_edge_counts,
            "reconstructedEdgesByKind": reconstructed_edge_counts,
        },
        "preservation": {
            "original": domain_status(original),
            "reconstructed": reconstructed_domain,
            "domainSubgraphs": domain_preservation_report,
        },
        "semanticValidation": {
            "result": "pass"
            if original_semantics["result"] == "pass"
            and reconstructed_semantics["result"] == "pass"
            else "fail",
            "rules": [
                "observed evidence is not accepted without accepted authority",
                "accepted evidence status must be compatible with the evidence type",
                "accepted authority cannot use ai as final decision authority",
                "accepted authority targets must use allowed target kinds",
                "accepted history deltas require changed targets and accepted authority",
                "accepted history sequence values must be contiguous from 1..n",
                "non-null gitCommit values must resolve to local commits",
                "null gitCommit requires pending-current-milestone boundary",
            ],
            "original": original_semantics,
            "reconstructed": reconstructed_semantics,
        },
        "codeOnlyProjection": {
            "claim": code_only.get("claim"),
            "usedForExactEquality": False,
            "usedForEvidenceAuthorityHistory": False,
            "lossModel": code_only.get("lossModel", []),
        },
        "mismatches": mismatches,
        "diagnostics": diagnostics,
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(canonical_pretty(report))


def verify(args: argparse.Namespace) -> int:
    original = read_json(args.original)
    reconstructed = read_json(args.reconstructed)
    metadata = read_json(args.metadata)
    code_only = read_json(args.code_only)
    report = build_report(
        args.out,
        args.original,
        args.reconstructed,
        args.metadata,
        args.code_only,
        original,
        reconstructed,
        metadata,
        code_only,
    )
    write_report(args.out, report)
    return 0 if report["result"] == "pass" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the B0 IntentGraph round trip.")
    parser.add_argument("--original", required=True, type=Path)
    parser.add_argument("--reconstructed", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--code-only", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    try:
        return verify(args)
    except (OSError, json.JSONDecodeError, VerifyError) as error:
        print(f"verify failed: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
