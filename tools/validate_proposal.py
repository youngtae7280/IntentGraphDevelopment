"""Tiny M6 deterministic validator for AI proposal fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from verify_roundtrip import validate_semantics


REPORT_VERSION = "0.1.0"
VALIDATOR_CONTRACT = "m6-proposal-validator-v0"
ALLOWED_ACTOR_TYPES = {"human", "ai", "tool", "system"}
REQUIRED_ACCEPTED_CHECKS = {
    "ProposalWellFormed",
    "BaseGraphDigestMatches",
    "CanApplyDelta",
    "AuthorityGranted",
}
SUPPORTED_OPS = {"addNode", "addEdge", "updateNodeAttributes"}
ALLOWED_PROPOSED_NODE_KINDS = {"test.case"}
ALLOWED_PROPOSED_EDGE_KINDS = {"tested_by"}
KNOWN_NODE_KINDS = {
    "intent.requirement",
    "domain.concept",
    "code.module",
    "code.function",
    "code.cli",
    "test.case",
    "projection.target",
    "metadata.sourceMap",
    "evidence.record",
    "authority.record",
    "history.delta",
}
KNOWN_EDGE_KINDS = {
    "decomposes_to",
    "uses_concept",
    "projects_to",
    "contains",
    "calls",
    "handled_by",
    "tested_by",
    "evidenced_by",
    "authorizes",
    "changes",
    "maps_from",
    "maps_to",
}
EDGE_ENDPOINT_RULES = {
    "decomposes_to": ({"intent.requirement"}, {"intent.requirement"}),
    "uses_concept": (
        {"intent.requirement", "code.module", "code.function", "code.cli"},
        {"domain.concept"},
    ),
    "projects_to": (
        {"intent.requirement", "domain.concept", "code.module", "code.function", "code.cli"},
        {"code.module", "code.function", "code.cli", "projection.target"},
    ),
    "contains": ({"code.module"}, {"code.function", "code.cli"}),
    "calls": ({"code.function"}, {"code.function"}),
    "handled_by": ({"code.cli"}, {"code.function"}),
    "tested_by": (
        {"intent.requirement", "code.module", "code.function", "code.cli"},
        {"test.case"},
    ),
    "evidenced_by": (KNOWN_NODE_KINDS - {"evidence.record"}, {"evidence.record"}),
    "authorizes": ({"authority.record"}, {"history.delta", "projection.target", "evidence.record"}),
    "changes": ({"history.delta"}, KNOWN_NODE_KINDS),
    "maps_from": ({"metadata.sourceMap"}, KNOWN_NODE_KINDS - {"metadata.sourceMap"}),
    "maps_to": ({"metadata.sourceMap"}, {"code.module", "code.function", "code.cli", "projection.target"}),
}
REQUIRED_NODE_ATTRS = {
    "evidence.record": {"evidenceType", "status", "summary", "recordedBy"},
    "authority.record": {
        "proposer",
        "proposerType",
        "requiredAuthority",
        "validator",
        "decidedBy",
        "decidedByType",
        "decision",
        "decisionStatus",
    },
    "history.delta": {"sequence", "changeType", "summary", "status", "gitCommit"},
}


class ProposalError(Exception):
    """Raised when a proposal input cannot be loaded."""


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ProposalError(f"{path} must contain a JSON object.")
    return data


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def prefixed_sha256(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


def digest_json(data: Any) -> str:
    return prefixed_sha256(canonical_json(data))


def graph_digest(graph: dict[str, Any]) -> str:
    return prefixed_sha256(canonical_json(graph))


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def graph_indexes(graph: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    nodes = {
        node["id"]: node
        for node in graph.get("nodes", [])
        if isinstance(node, dict) and isinstance(node.get("id"), str)
    }
    edges = {
        edge["id"]: edge
        for edge in graph.get("edges", [])
        if isinstance(edge, dict) and isinstance(edge.get("id"), str)
    }
    return nodes, edges


def attrs(node: dict[str, Any]) -> dict[str, Any]:
    attributes = node.get("attributes")
    return attributes if isinstance(attributes, dict) else {}


def normalized_actor_type(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.strip().casefold()


def evidence_accepted(nodes: dict[str, dict[str, Any]], evidence_id: str) -> bool:
    node = nodes.get(evidence_id)
    if not node or node.get("kind") != "evidence.record":
        return False
    return attrs(node).get("acceptanceStatus") == "accepted"


def authority_valid_for_proposal(
    nodes: dict[str, dict[str, Any]],
    authority_id: Any,
    required_authority: Any,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not isinstance(authority_id, str):
        return False, ["decision.authorityRecordId must be a string"]
    authority = nodes.get(authority_id)
    if not authority:
        return False, [f"decision authorityRecordId is missing: {authority_id}"]
    if authority.get("kind") != "authority.record":
        return False, [f"decision authorityRecordId is not authority.record: {authority_id}"]
    authority_attrs = attrs(authority)
    decided_by_type = normalized_actor_type(authority_attrs.get("decidedByType"))
    if authority_attrs.get("decisionStatus") != "accepted":
        errors.append(f"decision authorityRecordId is not accepted: {authority_id}")
    if decided_by_type == "ai":
        errors.append(f"decision authorityRecordId has AI final authority: {authority_id}")
    if required_authority and authority_attrs.get("requiredAuthority") != required_authority:
        errors.append(
            f"decision authorityRecordId requiredAuthority mismatch: {authority_attrs.get('requiredAuthority')}"
        )
    return not errors, errors


def validate_graphir_subset(graph: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    nodes_list = graph.get("nodes")
    edges_list = graph.get("edges")
    if not isinstance(nodes_list, list):
        return ["graph nodes must be an array"]
    if not isinstance(edges_list, list):
        return ["graph edges must be an array"]

    nodes, edges = graph_indexes(graph)
    node_ids = [node.get("id") for node in nodes_list if isinstance(node, dict)]
    edge_ids = [edge.get("id") for edge in edges_list if isinstance(edge, dict)]
    if len(node_ids) != len(set(node_ids)):
        errors.append("graph has duplicate node IDs")
    if len(edge_ids) != len(set(edge_ids)):
        errors.append("graph has duplicate edge IDs")
    collisions = sorted(set(node_ids) & set(edge_ids))
    if collisions:
        errors.append(f"graph has node/edge ID collisions: {collisions}")

    for node in nodes_list:
        if not isinstance(node, dict):
            errors.append("graph node must be an object")
            continue
        node_id = node.get("id")
        node_kind = node.get("kind")
        if node_kind not in KNOWN_NODE_KINDS:
            errors.append(f"{node_id} has unknown node kind: {node_kind}")
        node_attrs = node.get("attributes")
        if not isinstance(node_attrs, dict):
            errors.append(f"{node_id} attributes must be an object")
            node_attrs = {}
        required = REQUIRED_NODE_ATTRS.get(node_kind, set())
        missing = sorted(required - set(node_attrs))
        if missing:
            errors.append(f"{node_id} missing required attributes: {missing}")

    for edge in edges_list:
        if not isinstance(edge, dict):
            errors.append("graph edge must be an object")
            continue
        edge_id = edge.get("id")
        edge_kind = edge.get("kind")
        if edge_kind not in KNOWN_EDGE_KINDS:
            errors.append(f"{edge_id} has unknown edge kind: {edge_kind}")
            continue
        from_id = edge.get("from")
        to_id = edge.get("to")
        if from_id not in nodes:
            errors.append(f"{edge_id} missing from endpoint: {from_id}")
            continue
        if to_id not in nodes:
            errors.append(f"{edge_id} missing to endpoint: {to_id}")
            continue
        allowed_from, allowed_to = EDGE_ENDPOINT_RULES[edge_kind]
        from_kind = nodes[from_id].get("kind")
        to_kind = nodes[to_id].get("kind")
        if from_kind not in allowed_from or to_kind not in allowed_to:
            errors.append(
                f"{edge_id} endpoint kinds not allowed for {edge_kind}: {from_kind} -> {to_kind}"
            )
    return errors


def require_fields(container: dict[str, Any], required: set[str], label: str, errors: list[str]) -> None:
    missing = sorted(required - set(container))
    if missing:
        errors.append(f"{label} missing fields: {missing}")


def validate_node_shape(node: Any, errors: list[str], label: str) -> str | None:
    if not isinstance(node, dict):
        errors.append(f"{label} node must be an object")
        return None
    require_fields(node, {"id", "kind", "label", "attributes"}, f"{label} node", errors)
    node_id = node.get("id")
    if not isinstance(node_id, str):
        errors.append(f"{label} node id must be a string")
        return None
    if not isinstance(node.get("attributes"), dict):
        errors.append(f"{label} node attributes must be an object")
    return node_id


def validate_edge_shape(edge: Any, errors: list[str], label: str) -> str | None:
    if not isinstance(edge, dict):
        errors.append(f"{label} edge must be an object")
        return None
    require_fields(edge, {"id", "kind", "from", "to", "attributes"}, f"{label} edge", errors)
    edge_id = edge.get("id")
    if not isinstance(edge_id, str):
        errors.append(f"{label} edge id must be a string")
        return None
    if not isinstance(edge.get("attributes"), dict):
        errors.append(f"{label} edge attributes must be an object")
    return edge_id


def validate_delta(
    proposal: dict[str, Any],
    graph: dict[str, Any],
    nodes: dict[str, dict[str, Any]],
    edges: dict[str, dict[str, Any]],
    errors: list[str],
) -> dict[str, Any]:
    delta = proposal.get("delta")
    if not isinstance(delta, list) or not delta:
        errors.append("proposal delta must be a non-empty array")
        return {"addedNodes": [], "addedEdges": [], "updatedNodes": [], "appliedGraph": graph}

    applied_graph = json.loads(json.dumps(graph))
    simulated_nodes, simulated_edges = graph_indexes(applied_graph)
    added_nodes: list[str] = []
    added_edges: list[str] = []
    updated_nodes: list[str] = []

    for index, operation in enumerate(delta):
        label = f"delta[{index}]"
        if not isinstance(operation, dict):
            errors.append(f"{label} must be an object")
            continue
        op = operation.get("op")
        if op not in SUPPORTED_OPS:
            errors.append(f"{label} unsupported op: {op}")
            continue

        if op == "addNode":
            node = operation.get("node")
            node_id = validate_node_shape(node, errors, label)
            if node_id is None or not isinstance(node, dict):
                continue
            if node_id in simulated_nodes:
                errors.append(f"{label} addNode id already exists: {node_id}")
                continue
            if node.get("kind") not in ALLOWED_PROPOSED_NODE_KINDS:
                errors.append(f"{label} addNode unsupported node kind for M6: {node.get('kind')}")
                continue
            simulated_nodes[node_id] = node
            applied_graph.setdefault("nodes", []).append(node)
            added_nodes.append(node_id)

        if op == "addEdge":
            edge = operation.get("edge")
            edge_id = validate_edge_shape(edge, errors, label)
            if edge_id is None or not isinstance(edge, dict):
                continue
            if edge_id in simulated_edges:
                errors.append(f"{label} addEdge id already exists: {edge_id}")
                continue
            if edge.get("kind") not in ALLOWED_PROPOSED_EDGE_KINDS:
                errors.append(f"{label} addEdge unsupported edge kind for M6: {edge.get('kind')}")
                continue
            for endpoint in ("from", "to"):
                endpoint_id = edge.get(endpoint)
                if endpoint_id not in simulated_nodes:
                    errors.append(f"{label} addEdge missing {endpoint} endpoint: {endpoint_id}")
            simulated_edges[edge_id] = edge
            applied_graph.setdefault("edges", []).append(edge)
            added_edges.append(edge_id)

        if op == "updateNodeAttributes":
            node_id = operation.get("nodeId")
            patch = operation.get("attributes")
            if node_id not in simulated_nodes:
                errors.append(f"{label} updateNodeAttributes missing node: {node_id}")
                continue
            if simulated_nodes[node_id].get("kind") not in ALLOWED_PROPOSED_NODE_KINDS:
                errors.append(
                    f"{label} updateNodeAttributes unsupported node kind for M6: "
                    f"{simulated_nodes[node_id].get('kind')}"
                )
                continue
            if not isinstance(patch, dict):
                errors.append(f"{label} updateNodeAttributes attributes must be an object")
                continue
            updated = json.loads(json.dumps(simulated_nodes[node_id]))
            updated.setdefault("attributes", {}).update(patch)
            simulated_nodes[node_id] = updated
            for index, existing_node in enumerate(applied_graph.get("nodes", [])):
                if existing_node.get("id") == node_id:
                    applied_graph["nodes"][index] = updated
                    break
            updated_nodes.append(node_id)

    return {
        "addedNodes": added_nodes,
        "addedEdges": added_edges,
        "updatedNodes": updated_nodes,
        "appliedGraph": applied_graph,
    }


def validate_proposal(graph: dict[str, Any], proposal: dict[str, Any], path: Path) -> dict[str, Any]:
    nodes, edges = graph_indexes(graph)
    digest = graph_digest(graph)
    proposal_digest = digest_json(proposal)
    errors: list[str] = []
    diagnostics: list[str] = []

    require_fields(
        proposal,
        {
            "proposalVersion",
            "proposalId",
            "benchmarkId",
            "source",
            "target",
            "intent",
            "delta",
            "requiredAcceptedEvidence",
            "deterministicChecks",
            "decision",
            "expectedValidation",
        },
        "proposal",
        errors,
    )

    if proposal.get("proposalVersion") != "0.1.0":
        errors.append("proposalVersion must be 0.1.0")
    if proposal.get("benchmarkId") != graph.get("benchmarkId"):
        errors.append("proposal benchmarkId must match graph benchmarkId")

    source = proposal.get("source", {})
    if not isinstance(source, dict):
        errors.append("source must be an object")
        source = {}
    source_kind = normalized_actor_type(source.get("kind"))
    if source_kind not in ALLOWED_ACTOR_TYPES:
        errors.append(f"source.kind is invalid: {source.get('kind')}")
    if source_kind != "ai":
        errors.append("M6 fixture proposals must have source.kind ai")

    target = proposal.get("target", {})
    if not isinstance(target, dict):
        errors.append("target must be an object")
        target = {}
    if target.get("graphId") != graph.get("graphId"):
        errors.append("target.graphId must match graph graphId")
    if target.get("baseGraphDigest") != digest:
        errors.append("target.baseGraphDigest must match current graph digest")
    else:
        diagnostics.append("base graph digest matched")

    decision = proposal.get("decision", {})
    if not isinstance(decision, dict):
        errors.append("decision must be an object")
        decision = {}
    require_fields(
        decision,
        {
            "decisionStatus",
            "authorityRecordId",
            "requiredAuthority",
            "validator",
            "decidedBy",
            "decidedByType",
        },
        "decision",
        errors,
    )
    decision_status = decision.get("decisionStatus")
    decided_by_type = normalized_actor_type(decision.get("decidedByType"))
    if decided_by_type not in ALLOWED_ACTOR_TYPES:
        errors.append(f"decision.decidedByType is invalid: {decision.get('decidedByType')}")
    if decision_status == "accepted" and decided_by_type == "ai":
        errors.append("AI cannot be final authority for an accepted proposal")
    if decision_status == "accepted" and not decision.get("requiredAuthority"):
        errors.append("accepted proposal requires requiredAuthority")
    if decision_status == "accepted" and decision.get("validator") != "m6-proposal-validator":
        errors.append("accepted proposal validator must be m6-proposal-validator")
    authority_granted, authority_errors = authority_valid_for_proposal(
        nodes,
        decision.get("authorityRecordId"),
        decision.get("requiredAuthority"),
    )
    if decision_status == "accepted" and not authority_granted:
        errors.extend(authority_errors)

    checks = proposal.get("deterministicChecks")
    if not isinstance(checks, list) or not all(isinstance(item, str) for item in checks):
        errors.append("deterministicChecks must be an array of strings")
        checks = []
    if decision_status == "accepted":
        missing_checks = sorted(REQUIRED_ACCEPTED_CHECKS - set(checks))
        if missing_checks:
            errors.append(f"accepted proposal missing deterministic checks: {missing_checks}")

    evidence_refs = proposal.get("requiredAcceptedEvidence")
    if not isinstance(evidence_refs, list) or not all(isinstance(item, str) for item in evidence_refs):
        errors.append("requiredAcceptedEvidence must be an array of strings")
        evidence_refs = []
    if decision_status == "accepted" and not evidence_refs:
        errors.append("accepted proposal requires at least one accepted evidence reference")
    for evidence_id in evidence_refs:
        if not evidence_accepted(nodes, evidence_id):
            errors.append(f"required evidence is not accepted: {evidence_id}")

    delta_result = validate_delta(proposal, graph, nodes, edges, errors)
    applied_graph = delta_result.pop("appliedGraph")
    graphir_errors = validate_graphir_subset(applied_graph)
    semantic_result = validate_semantics(
        applied_graph,
        Path("generated/b0-python-cli-calculator/roundtrip-report.json"),
    )
    if graphir_errors:
        errors.extend(f"post-delta graph invalid: {error}" for error in graphir_errors)
    if semantic_result["result"] != "pass":
        errors.extend(
            f"post-delta semantic validation failed: {error}"
            for error in semantic_result.get("errors", [])
        )
    validation = "accepted" if decision_status == "accepted" and not errors else "rejected"
    expected = proposal.get("expectedValidation")
    expected_matched = validation == expected

    return {
        "proposalPath": path.as_posix(),
        "proposalId": proposal.get("proposalId"),
        "proposalDigest": proposal_digest,
        "sourceKind": source_kind,
        "decisionStatus": decision_status,
        "authorityRecordId": decision.get("authorityRecordId"),
        "authorityGranted": authority_granted,
        "decidedByType": decided_by_type,
        "requiredAcceptedEvidenceRole": "base-graph-prerequisite",
        "expectedValidation": expected,
        "validation": validation,
        "expectedMatched": expected_matched,
        "acceptedForApplication": validation == "accepted",
        "deltaSummary": delta_result,
        "postDelta": {
            "graphDigest": graph_digest(applied_graph),
            "graphirValid": not graphir_errors,
            "semanticValidation": semantic_result["result"],
        },
        "errors": errors,
        "diagnostics": diagnostics,
    }


def build_report(graph_path: Path, proposal_paths: list[Path]) -> dict[str, Any]:
    graph = read_json(graph_path)
    results = [validate_proposal(graph, read_json(path), path) for path in proposal_paths]
    accepted = [result for result in results if result["validation"] == "accepted"]
    rejected = [result for result in results if result["validation"] == "rejected"]
    ai_authority_leak = any(result["validation"] == "accepted" and result["decidedByType"] == "ai" for result in results)
    automatic_application = False
    expected_mismatches = [
        result["proposalId"]
        for result in results
        if not result["expectedMatched"]
    ]
    report_pass = not expected_mismatches and bool(accepted) and bool(rejected) and not ai_authority_leak
    return {
        "reportVersion": REPORT_VERSION,
        "validatorContract": VALIDATOR_CONTRACT,
        "result": "pass" if report_pass else "fail",
        "graph": {
            "path": graph_path.as_posix(),
            "graphId": graph.get("graphId"),
            "benchmarkId": graph.get("benchmarkId"),
            "graphDigest": graph_digest(graph),
        },
        "summary": {
            "proposalCount": len(results),
            "acceptedForApplication": len(accepted),
            "rejected": len(rejected),
            "expectedMismatches": expected_mismatches,
            "aiOutputTreatedAsAuthority": ai_authority_leak,
            "automaticApplication": automatic_application,
        },
        "proposalResults": results,
    }


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(canonical_pretty(report))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate M6 AI proposal fixtures.")
    parser.add_argument("--graph", required=True, type=Path)
    parser.add_argument("--proposal", required=True, action="append", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    try:
        report = build_report(args.graph, args.proposal)
        write_report(args.out, report)
    except (OSError, json.JSONDecodeError, ProposalError) as error:
        print(f"proposal validation failed: {error}")
        return 1
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
