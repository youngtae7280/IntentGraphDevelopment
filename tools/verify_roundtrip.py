"""Tiny M4 round-trip verifier for the B0 IntentGraph slice."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


VERIFIER_CONTRACT = "roundtrip-b0-v0"


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


def build_report(
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
    for key in ["evidencePreserved", "authorityPreserved", "historyPreserved"]:
        if not reconstructed_domain[key]:
            mismatches.append(f"{key} is false")
    for domain, domain_report in domain_preservation_report.items():
        if not domain_report["matched"]:
            mismatches.append(f"{domain} domain subgraph digest differs")

    result = "pass" if graph_equal and not mismatches else "fail"
    if result == "pass":
        diagnostics.append("normalized metadata-backed graph equality passed")
    else:
        diagnostics.extend(mismatches)

    return {
        "reportVersion": "0.1.0",
        "verifierContract": VERIFIER_CONTRACT,
        "benchmarkId": original.get("benchmarkId"),
        "result": result,
        "graphEqual": graph_equal,
        "equalityMode": "GraphEqualAfterNormalization",
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
        "codeOnlyProjection": {
            "claim": code_only.get("claim"),
            "usedForExactEquality": False,
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
