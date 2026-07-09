"""Emit the tiny M7 workbench projection for the B0 IntentGraph slice."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


PROJECTION_VERSION = "0.1.0"
AUTHORITY_DISCLAIMER = "This projection is a report. It is not accepted graph authority."


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest_json(data: Any) -> str:
    return f"sha256:{hashlib.sha256(canonical_json(data).encode('utf-8')).hexdigest()}"


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def count_by_kind(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        kind = item.get("kind", "<missing>")
        counts[kind] = counts.get(kind, 0) + 1
    return dict(sorted(counts.items()))


def graph_indexes(graph: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    nodes = {node["id"]: node for node in graph.get("nodes", []) if isinstance(node.get("id"), str)}
    edges = {edge["id"]: edge for edge in graph.get("edges", []) if isinstance(edge.get("id"), str)}
    return nodes, edges


def group_edges(edges: dict[str, dict[str, Any]], endpoint: str) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for edge in edges.values():
        grouped.setdefault(edge[endpoint], []).append(edge["id"])
    return {node_id: sorted(edge_ids) for node_id, edge_ids in sorted(grouped.items())}


def group_edges_by_kind(edges: dict[str, dict[str, Any]], kind: str, endpoint: str) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for edge in edges.values():
        if edge.get("kind") == kind:
            grouped.setdefault(edge[endpoint], []).append(edge["id"])
    return {node_id: sorted(edge_ids) for node_id, edge_ids in sorted(grouped.items())}


def nodes_by_kind(nodes: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for node in nodes.values():
        grouped.setdefault(node.get("kind", "<missing>"), []).append(node["id"])
    return {kind: sorted(node_ids) for kind, node_ids in sorted(grouped.items())}


def edges_by_kind(edges: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for edge in edges.values():
        grouped.setdefault(edge.get("kind", "<missing>"), []).append(edge["id"])
    return {kind: sorted(edge_ids) for kind, edge_ids in sorted(grouped.items())}


def intent_units_by_kind(graph: dict[str, Any]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for unit in graph.get("intentUnits", []):
        if isinstance(unit, dict) and isinstance(unit.get("id"), str):
            grouped.setdefault(unit.get("kind", "<missing>"), []).append(unit["id"])
    return {kind: sorted(unit_ids) for kind, unit_ids in sorted(grouped.items())}


def unit_edges_by_kind(graph: dict[str, Any]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for edge in graph.get("unitEdges", []):
        if isinstance(edge, dict) and isinstance(edge.get("id"), str):
            grouped.setdefault(edge.get("kind", "<missing>"), []).append(edge["id"])
    return {kind: sorted(edge_ids) for kind, edge_ids in sorted(grouped.items())}


def unit_membership(graph: dict[str, Any]) -> dict[str, dict[str, list[str]]]:
    membership: dict[str, dict[str, list[str]]] = {}
    for unit in graph.get("intentUnits", []):
        if not isinstance(unit, dict) or not isinstance(unit.get("id"), str):
            continue
        internal_graph = unit.get("internalGraph", {})
        membership[unit["id"]] = {
            "nodeIds": sorted(internal_graph.get("nodeIds", [])),
            "edgeIds": sorted(internal_graph.get("edgeIds", [])),
        }
    return dict(sorted(membership.items()))


def proposal_results_by_id(proposal_report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for result in proposal_report.get("proposalResults", []):
        proposal_id = result.get("proposalId")
        if isinstance(proposal_id, str):
            results[proposal_id] = {
                "validation": result.get("validation"),
                "acceptedForApplication": result.get("acceptedForApplication"),
                "authorityRecordId": result.get("authorityRecordId"),
                "proposalDigest": result.get("proposalDigest"),
                "deltaSummary": result.get("deltaSummary"),
                "postDelta": result.get("postDelta"),
                "errors": result.get("errors", []),
            }
    return dict(sorted(results.items()))


def input_consistency(graph: dict[str, Any], roundtrip: dict[str, Any], proposal_report: dict[str, Any]) -> dict[str, Any]:
    graph_digest = digest_json(graph)
    graph_benchmark = graph.get("benchmarkId")
    roundtrip_original_digest = roundtrip.get("digests", {}).get("originalGraph")
    proposal_graph_digest = proposal_report.get("graph", {}).get("graphDigest")
    proposal_benchmark = proposal_report.get("graph", {}).get("benchmarkId")
    checks = {
        "graphDigest": graph_digest,
        "roundtripOriginalGraphDigest": roundtrip_original_digest,
        "proposalGraphDigest": proposal_graph_digest,
        "graphBenchmarkId": graph_benchmark,
        "proposalBenchmarkId": proposal_benchmark,
        "roundtripDigestMatchesGraph": roundtrip_original_digest == graph_digest,
        "proposalDigestMatchesGraph": proposal_graph_digest == graph_digest,
        "proposalBenchmarkMatchesGraph": proposal_benchmark == graph_benchmark,
    }
    checks["result"] = "pass" if all(
        [
            checks["roundtripDigestMatchesGraph"],
            checks["proposalDigestMatchesGraph"],
            checks["proposalBenchmarkMatchesGraph"],
        ]
    ) else "fail"
    return checks


def mermaid_overview(roundtrip: dict[str, Any], proposal_report: dict[str, Any], consistency: dict[str, Any]) -> str:
    roundtrip_result = roundtrip.get("result", "unknown")
    semantic_result = roundtrip.get("semanticValidation", {}).get("result", "unknown")
    proposal_result = proposal_report.get("result", "unknown")
    consistency_result = consistency.get("result", "unknown")
    return "\n".join(
        [
            "graph TD",
            '  G["B0 IntentGraph"] --> C["generated calc.py"]',
            '  C --> M["calc.intentgraph.json"]',
            '  M --> R["reconstructed graph"]',
            f'  R --> V["round-trip verifier: {roundtrip_result}"]',
            f'  V --> E["evidence / authority / history: {semantic_result}"]',
            f'  E --> P["AI proposal validation: {proposal_result}"]',
            f'  P --> I["input consistency: {consistency_result}"]',
        ]
    )


def build_projection(
    graph_path: Path,
    roundtrip_path: Path,
    proposal_path: Path,
) -> dict[str, Any]:
    graph = read_json(graph_path)
    roundtrip = read_json(roundtrip_path)
    proposal_report = read_json(proposal_path)
    consistency = input_consistency(graph, roundtrip, proposal_report)
    if consistency["result"] != "pass":
        raise ValueError(f"workbench projection input consistency failed: {consistency}")
    nodes, edges = graph_indexes(graph)
    semantic = roundtrip.get("semanticValidation", {}).get("reconstructed", {})
    domain_subgraphs = roundtrip.get("preservation", {}).get("domainSubgraphs", {})
    return {
        "projectionVersion": PROJECTION_VERSION,
        "projectionKind": "workbench-report",
        "authorityDisclaimer": AUTHORITY_DISCLAIMER,
        "inputs": {
            "graph": graph_path.as_posix(),
            "roundtripReport": roundtrip_path.as_posix(),
            "proposalReport": proposal_path.as_posix(),
        },
        "inputConsistency": consistency,
        "graph": {
            "graphId": graph.get("graphId"),
            "benchmarkId": graph.get("benchmarkId"),
            "graphDigest": digest_json(graph),
            "nodeCount": len(nodes),
            "edgeCount": len(edges),
            "intentUnitCount": len(graph.get("intentUnits", [])),
            "unitEdgeCount": len(graph.get("unitEdges", [])),
            "nodesByKind": nodes_by_kind(nodes),
            "edgesByKind": edges_by_kind(edges),
            "intentUnitsByKind": intent_units_by_kind(graph),
            "unitEdgesByKind": unit_edges_by_kind(graph),
            "nodeCountsByKind": count_by_kind(list(nodes.values())),
            "edgeCountsByKind": count_by_kind(list(edges.values())),
        },
        "roundTrip": {
            "result": roundtrip.get("result"),
            "graphEqual": roundtrip.get("graphEqual"),
            "equalityMode": roundtrip.get("equalityMode"),
            "semanticValidation": roundtrip.get("semanticValidation", {}).get("result"),
            "m5ClaimScope": roundtrip.get("m5ClaimScope"),
            "metadataGraphDigest": roundtrip.get("digests", {}).get("metadataGraphDigest"),
            "codeOnlyUsedForExactEquality": roundtrip.get("codeOnlyProjection", {}).get("usedForExactEquality"),
            "codeOnlyUsedForEvidenceAuthorityHistory": roundtrip.get("codeOnlyProjection", {}).get("usedForEvidenceAuthorityHistory"),
            "codeOnlyLossModel": roundtrip.get("codeOnlyProjection", {}).get("lossModel", []),
            "domainSubgraphMatches": {
                domain: value.get("matched")
                for domain, value in domain_subgraphs.items()
            },
            "intentUnitPreservation": roundtrip.get("preservation", {}).get("intentUnits"),
        },
        "evidenceAuthorityHistory": {
            "evidenceAccepted": semantic.get("evidence", {}).get("acceptedCount"),
            "authorityAccepted": semantic.get("authority", {}).get("acceptedCount"),
            "aiFinalAuthorityCount": semantic.get("authority", {}).get("aiFinalAuthorityCount"),
            "historyAccepted": semantic.get("history", {}).get("acceptedCount"),
            "gitVerifiedCount": semantic.get("history", {}).get("gitVerifiedCount"),
            "pendingCurrentMilestoneCount": semantic.get("history", {}).get("pendingCurrentMilestoneCount"),
        },
        "proposalValidation": {
            "result": proposal_report.get("result"),
            "proposalCount": proposal_report.get("summary", {}).get("proposalCount"),
            "acceptedForApplication": proposal_report.get("summary", {}).get("acceptedForApplication"),
            "rejected": proposal_report.get("summary", {}).get("rejected"),
            "aiOutputTreatedAsAuthority": proposal_report.get("summary", {}).get("aiOutputTreatedAsAuthority"),
            "automaticApplication": proposal_report.get("summary", {}).get("automaticApplication"),
        },
        "navigation": {
            "incomingEdgesByNode": group_edges(edges, "to"),
            "outgoingEdgesByNode": group_edges(edges, "from"),
            "evidenceByTarget": group_edges_by_kind(edges, "evidenced_by", "from"),
            "authorityByTarget": group_edges_by_kind(edges, "authorizes", "to"),
            "historyChangesByDelta": group_edges_by_kind(edges, "changes", "from"),
            "unitMembership": unit_membership(graph),
            "proposalResultsById": proposal_results_by_id(proposal_report),
        },
        "diagram": {
            "format": "mermaid",
            "authority": "orientation-only",
            "source": mermaid_overview(roundtrip, proposal_report, consistency),
        },
    }


def write_projection(path: Path, projection: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(canonical_pretty(projection))


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit the B0 workbench projection report.")
    parser.add_argument("--graph", required=True, type=Path)
    parser.add_argument("--roundtrip", required=True, type=Path)
    parser.add_argument("--proposals", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        projection = build_projection(args.graph, args.roundtrip, args.proposals)
        write_projection(args.out, projection)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"workbench projection failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
