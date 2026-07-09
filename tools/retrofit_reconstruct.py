"""Tiny M3 Retrofit reconstructor for the B0 IntentGraph calculator."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from json import JSONDecodeError
from pathlib import Path
from typing import Any


RECONSTRUCTOR_CONTRACT = "retrofit-python-b0-v0"
DETERMINISTIC_RECONSTRUCTED_AT = "deterministic:m3-retrofit-python-b0-v0"


class RetrofitError(Exception):
    """Raised when metadata-backed reconstruction cannot proceed."""


def read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except JSONDecodeError as error:
        raise RetrofitError(f"{path} is not valid JSON: {error}") from error
    if not isinstance(data, dict):
        raise RetrofitError(f"{path} must contain a JSON object.")
    return data


def read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8") as handle:
        return handle.read()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def prefixed_sha256(text: str) -> str:
    return f"sha256:{sha256_text(text)}"


def require_metadata(metadata: dict[str, Any]) -> None:
    required = [
        "metadataVersion",
        "benchmarkId",
        "graphId",
        "graphDigest",
        "compilerContract",
        "generatedArtifacts",
        "nodeMap",
        "edgeMap",
        "projectionRules",
        "hiddenState",
    ]
    for key in required:
        if key not in metadata:
            raise RetrofitError(f"Metadata missing required field: {key}")
    hidden_state = metadata["hiddenState"]
    if not isinstance(hidden_state, dict) or "sourceGraphSnapshot" not in hidden_state:
        raise RetrofitError("Metadata missing hiddenState.sourceGraphSnapshot.")
    projection_rules = metadata["projectionRules"]
    if projection_rules.get("unclassified") != []:
        raise RetrofitError("Metadata projectionRules.unclassified must be empty.")
    if not isinstance(metadata["nodeMap"], list) or not metadata["nodeMap"]:
        raise RetrofitError("Metadata nodeMap must be a non-empty array.")
    if not isinstance(metadata["edgeMap"], list) or not metadata["edgeMap"]:
        raise RetrofitError("Metadata edgeMap must be a non-empty array.")


def validate_source_hash(source: str, metadata: dict[str, Any]) -> None:
    artifacts = metadata.get("generatedArtifacts")
    if not isinstance(artifacts, list):
        raise RetrofitError("Metadata generatedArtifacts must be an array.")
    calc_artifact = next((item for item in artifacts if item.get("path") == "calc.py"), None)
    if not calc_artifact:
        raise RetrofitError("Metadata does not include calc.py artifact hash.")
    actual_hash = sha256_text(source)
    if calc_artifact.get("sha256") != actual_hash:
        raise RetrofitError("Generated source hash does not match metadata.")


def validate_graph_digest(metadata: dict[str, Any]) -> dict[str, Any]:
    graph = metadata["hiddenState"]["sourceGraphSnapshot"]
    if not isinstance(graph, dict):
        raise RetrofitError("hiddenState.sourceGraphSnapshot must be an object.")
    actual_digest = prefixed_sha256(canonical_json(graph))
    if metadata["graphDigest"] != actual_digest:
        raise RetrofitError("hiddenState.sourceGraphSnapshot digest does not match metadata graphDigest.")
    return graph


def graph_indexes(graph: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    node_index: dict[str, dict[str, Any]] = {}
    edge_index: dict[str, dict[str, Any]] = {}
    for node in graph.get("nodes", []):
        node_id = node.get("id")
        if not isinstance(node_id, str):
            raise RetrofitError("Snapshot node missing string id.")
        node_index[node_id] = node
    for edge in graph.get("edges", []):
        edge_id = edge.get("id")
        if not isinstance(edge_id, str):
            raise RetrofitError("Snapshot edge missing string id.")
        edge_index[edge_id] = edge
    return node_index, edge_index


def validate_node_map(metadata: dict[str, Any], graph: dict[str, Any], source: str) -> None:
    nodes, _ = graph_indexes(graph)
    source_line_count = len(source.splitlines())
    required_fields = {
        "metadataNodeId",
        "graphNodeId",
        "nodeKind",
        "targetFile",
        "targetName",
        "targetKind",
        "lineStart",
        "lineEnd",
        "requiredForRoundTrip",
    }
    round_trip_ids: set[str] = set()
    for entry in metadata["nodeMap"]:
        if not isinstance(entry, dict):
            raise RetrofitError("Every nodeMap entry must be an object.")
        missing = required_fields - set(entry)
        if missing:
            raise RetrofitError(f"nodeMap entry missing fields: {sorted(missing)}")
        graph_node_id = entry["graphNodeId"]
        if graph_node_id not in nodes:
            raise RetrofitError(f"nodeMap references missing graph node: {graph_node_id}")
        if nodes[graph_node_id]["kind"] != entry["nodeKind"]:
            raise RetrofitError(f"nodeMap nodeKind mismatch for {graph_node_id}.")
        metadata_node_id = entry["metadataNodeId"]
        if metadata_node_id not in nodes:
            raise RetrofitError(f"nodeMap references missing metadata node: {metadata_node_id}")
        if nodes[metadata_node_id]["kind"] != "metadata.sourceMap":
            raise RetrofitError(f"nodeMap metadataNodeId is not metadata.sourceMap: {metadata_node_id}")
        line_start = int(entry["lineStart"])
        line_end = int(entry["lineEnd"])
        if line_start < 1 or line_end < line_start or line_end > source_line_count:
            raise RetrofitError(f"nodeMap line range is invalid for {graph_node_id}.")
        if entry["requiredForRoundTrip"]:
            round_trip_ids.add(graph_node_id)

    required_graph_ids: set[str] = set()
    for node in nodes.values():
        if node.get("kind") == "metadata.sourceMap":
            attrs = node.get("attributes", {})
            if attrs.get("requiredForRoundTrip"):
                required_graph_ids.update(attrs.get("graphNodeIds", []))
    missing_coverage = sorted(required_graph_ids - round_trip_ids)
    if missing_coverage:
        raise RetrofitError(f"nodeMap missing round-trip coverage for: {missing_coverage}")


def validate_edge_map(metadata: dict[str, Any], graph: dict[str, Any]) -> None:
    nodes, edges = graph_indexes(graph)
    required_fields = {"graphEdgeId", "edgeKind", "from", "to", "preservation"}
    seen_edges: set[str] = set()
    for entry in metadata["edgeMap"]:
        if not isinstance(entry, dict):
            raise RetrofitError("Every edgeMap entry must be an object.")
        missing = required_fields - set(entry)
        if missing:
            raise RetrofitError(f"edgeMap entry missing fields: {sorted(missing)}")
        edge_id = entry["graphEdgeId"]
        if edge_id not in edges:
            raise RetrofitError(f"edgeMap references missing graph edge: {edge_id}")
        edge = edges[edge_id]
        if edge["kind"] != entry["edgeKind"]:
            raise RetrofitError(f"edgeMap edgeKind mismatch for {edge_id}.")
        if edge["from"] != entry["from"] or edge["to"] != entry["to"]:
            raise RetrofitError(f"edgeMap endpoint mismatch for {edge_id}.")
        if entry["from"] not in nodes or entry["to"] not in nodes:
            raise RetrofitError(f"edgeMap references missing endpoint for {edge_id}.")
        if entry["preservation"] not in {"source", "metadata", "projection"}:
            raise RetrofitError(f"edgeMap preservation value is invalid for {edge_id}.")
        seen_edges.add(edge_id)
    missing_edges = sorted(set(edges) - seen_edges)
    if missing_edges:
        raise RetrofitError(f"edgeMap missing graph edges: {missing_edges}")


def reconstruct_graph(metadata: dict[str, Any]) -> dict[str, Any]:
    graph = json.loads(json.dumps(metadata["hiddenState"]["sourceGraphSnapshot"]))
    graph["status"] = "m3-reconstructed"
    return graph


def call_names(node: ast.AST) -> list[str]:
    names: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
            names.append(child.func.id)
    return sorted(set(names))


def return_expressions(node: ast.FunctionDef) -> list[str]:
    expressions: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Return) and child.value is not None:
            expressions.append(ast.unparse(child.value))
    return expressions


def string_constants(tree: ast.AST) -> list[str]:
    values: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            values.add(node.value)
    return sorted(values)


def integer_constants(tree: ast.AST) -> list[int]:
    values: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            values.add(node.value)
    return sorted(values)


def code_only_projection(source_path: Path, source: str) -> dict[str, Any]:
    tree = ast.parse(source)
    functions: list[dict[str, Any]] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            functions.append(
                {
                    "name": node.name,
                    "arguments": [arg.arg for arg in node.args.args],
                    "lineStart": node.lineno,
                    "lineEnd": node.end_lineno or node.lineno,
                    "returnExpressions": return_expressions(node),
                    "calls": call_names(node),
                }
            )
    constants = string_constants(tree)
    return {
        "projectionVersion": "0.1.0",
        "reconstructorContract": RECONSTRUCTOR_CONTRACT,
        "sourcePath": source_path.as_posix(),
        "sourceSha256": sha256_text(source),
        "recoverableFacts": {
            "modulePath": source_path.name,
            "functions": functions,
            "stringConstants": constants,
            "integerConstants": integer_constants(tree),
            "cliOperationHints": [
                value
                for value in constants
                if value in {"add", "sub"}
            ],
        },
        "lossModel": [
            "full product intent wording",
            "requirement priorities",
            "domain concept descriptions",
            "evidence records",
            "authority records",
            "semantic graph history",
            "stable source graph IDs",
            "metadata source-map node IDs",
            "accepted change state",
            "verifier equality mode",
        ],
        "claim": "lossy-code-only-projection",
    }


def build_diagnostics(metadata: dict[str, Any], reconstructed: dict[str, Any]) -> dict[str, Any]:
    return {
        "diagnosticsVersion": "0.1.0",
        "reconstructorContract": RECONSTRUCTOR_CONTRACT,
        "status": "pass",
        "benchmarkId": metadata["benchmarkId"],
        "graphDigest": metadata["graphDigest"],
        "reconstructedGraphDigest": prefixed_sha256(canonical_json(reconstructed)),
        "reconstructedAt": DETERMINISTIC_RECONSTRUCTED_AT,
        "roundTripVerification": "not-run-in-m3",
        "warnings": [
            "M3 reconstructed from preservation metadata; M4 must perform equality verification.",
            "Code-only projection is lossy and must not be treated as the full intent graph.",
        ],
        "errors": [],
    }


def reconstruct(source_path: Path, metadata_path: Path, out_dir: Path) -> None:
    source = read_text(source_path)
    metadata = read_json(metadata_path)
    require_metadata(metadata)
    validate_source_hash(source, metadata)
    graph = validate_graph_digest(metadata)
    validate_node_map(metadata, graph, source)
    validate_edge_map(metadata, graph)

    reconstructed = reconstruct_graph(metadata)
    projection = code_only_projection(source_path, source)
    diagnostics = build_diagnostics(metadata, reconstructed)

    write_text(out_dir / "reconstructed.graph.json", canonical_pretty(reconstructed))
    write_text(out_dir / "code-only-projection.json", canonical_pretty(projection))
    write_text(out_dir / "retrofit-diagnostics.json", canonical_pretty(diagnostics))


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconstruct B0 GraphIR from generated source and metadata.")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    try:
        reconstruct(args.source, args.metadata, args.out)
    except (RetrofitError, OSError, SyntaxError) as error:
        print(f"retrofit failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
