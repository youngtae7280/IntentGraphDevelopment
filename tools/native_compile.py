"""Tiny M2 Native compiler for the B0 IntentGraph calculator fixture."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Any


COMPILER_CONTRACT = "native-python-b0-v0"
METADATA_VERSION = "0.1.0"
DETERMINISTIC_GENERATED_AT = "deterministic:m2-native-python-b0-v0"


class CompileError(Exception):
    """Raised when the B0 graph cannot be compiled."""


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise CompileError("Graph source must be a JSON object.")
    return data


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def node_index(graph: dict[str, Any]) -> dict[str, dict[str, Any]]:
    nodes = graph.get("nodes")
    if not isinstance(nodes, list):
        raise CompileError("Graph must contain a nodes array.")
    index: dict[str, dict[str, Any]] = {}
    for node in nodes:
        if not isinstance(node, dict):
            raise CompileError("Every node must be an object.")
        node_id = node.get("id")
        if not isinstance(node_id, str):
            raise CompileError("Every node must have a string id.")
        if node_id in index:
            raise CompileError(f"Duplicate node id: {node_id}")
        index[node_id] = node
    return index


def edge_index(graph: dict[str, Any], nodes: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    edges = graph.get("edges")
    if not isinstance(edges, list):
        raise CompileError("Graph must contain an edges array.")
    index: dict[str, dict[str, Any]] = {}
    for edge in edges:
        if not isinstance(edge, dict):
            raise CompileError("Every edge must be an object.")
        edge_id = edge.get("id")
        if not isinstance(edge_id, str):
            raise CompileError("Every edge must have a string id.")
        if edge_id in index:
            raise CompileError(f"Duplicate edge id: {edge_id}")
        if edge_id in nodes:
            raise CompileError(f"Node and edge id collision: {edge_id}")
        for endpoint in ("from", "to"):
            endpoint_id = edge.get(endpoint)
            if endpoint_id not in nodes:
                raise CompileError(f"Edge {edge_id} has missing {endpoint} endpoint: {endpoint_id}")
        index[edge_id] = edge
    return index


def attrs(node: dict[str, Any]) -> dict[str, Any]:
    attributes = node.get("attributes")
    if not isinstance(attributes, dict):
        raise CompileError(f"Node {node.get('id')} must have attributes.")
    return attributes


def require_nodes(nodes: dict[str, dict[str, Any]], required_ids: list[str]) -> None:
    for node_id in required_ids:
        if node_id not in nodes:
            raise CompileError(f"Required B0 node is missing: {node_id}")


def require_attrs(node: dict[str, Any], required_keys: list[str]) -> dict[str, Any]:
    attributes = attrs(node)
    for key in required_keys:
        if key not in attributes:
            raise CompileError(f"{node['id']} missing required attribute {key}.")
    return attributes


def validate_b0_graph(graph: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    if graph.get("graphirVersion") != "0.1.0":
        raise CompileError("M2 compiler supports only graphirVersion 0.1.0.")
    if graph.get("benchmarkId") != "B0-python-cli-calculator":
        raise CompileError("M2 compiler supports only B0-python-cli-calculator.")

    nodes = node_index(graph)
    edges = edge_index(graph, nodes)

    require_nodes(
        nodes,
        [
            "code.cli.command",
            "code.function.add",
            "code.function.main",
            "code.function.sub",
            "code.module.calc",
            "metadata.source-map.add",
            "metadata.source-map.cli",
            "metadata.source-map.main",
            "metadata.source-map.module",
            "metadata.source-map.sub",
            "projection.target.python-source",
            "test.case.add",
            "test.case.sub",
        ],
    )

    if not any(node.get("kind") == "authority.record" for node in nodes.values()):
        raise CompileError("At least one authority.record node is required.")
    if not any(node.get("kind") == "evidence.record" for node in nodes.values()):
        raise CompileError("At least one evidence.record node is required.")
    if not any(node.get("kind") == "history.delta" for node in nodes.values()):
        raise CompileError("At least one history.delta node is required.")

    projection = graph.get("projections", {}).get("native", {})
    if projection.get("language") != "python":
        raise CompileError("B0 native projection language must be python.")
    if projection.get("targetFiles") != ["calc.py"]:
        raise CompileError("B0 native targetFiles must be exactly ['calc.py'].")
    if projection.get("metadataFile") != "calc.intentgraph.json":
        raise CompileError("B0 metadataFile must be calc.intentgraph.json.")

    require_attrs(
        nodes["code.cli.command"],
        ["commandName", "argumentSchema", "stdout", "exitCodes"],
    )
    require_attrs(
        nodes["code.function.add"],
        ["functionName", "parameters", "returns", "operationKind"],
    )
    require_attrs(
        nodes["code.function.main"],
        [
            "functionName",
            "parameters",
            "returns",
            "dispatches",
            "argumentSource",
            "outputTarget",
            "successExitCode",
            "invalidInputExitCode",
        ],
    )
    require_attrs(
        nodes["code.function.sub"],
        ["functionName", "parameters", "returns", "operationKind"],
    )
    require_attrs(nodes["test.case.add"], ["command", "expectedStdout", "expectedExitCode", "status"])
    require_attrs(nodes["test.case.sub"], ["command", "expectedStdout", "expectedExitCode", "status"])

    cli_attrs = attrs(nodes["code.cli.command"])
    main_attrs = attrs(nodes["code.function.main"])
    exit_codes = cli_attrs["exitCodes"]
    if int(exit_codes["success"]) != int(main_attrs["successExitCode"]):
        raise CompileError("CLI success exit code must match main successExitCode.")
    if int(exit_codes["invalidOperation"]) != int(main_attrs["invalidInputExitCode"]):
        raise CompileError("CLI invalidOperation exit code must match main invalidInputExitCode.")
    if int(exit_codes["invalidInteger"]) != int(main_attrs["invalidInputExitCode"]):
        raise CompileError("CLI invalidInteger exit code must match main invalidInputExitCode.")

    expected_tests = {
        "test.case.add": ("python calc.py add 2 3", "5\n", int(exit_codes["success"])),
        "test.case.sub": ("python calc.py sub 5 2", "3\n", int(exit_codes["success"])),
    }
    for node_id, (command, stdout, exit_code) in expected_tests.items():
        test_attrs = attrs(nodes[node_id])
        if test_attrs["command"] != command:
            raise CompileError(f"{node_id} command must be {command!r}.")
        if test_attrs["expectedStdout"] != stdout:
            raise CompileError(f"{node_id} expectedStdout must be {stdout!r}.")
        if int(test_attrs["expectedExitCode"]) != exit_code:
            raise CompileError(f"{node_id} expectedExitCode must be {exit_code}.")

    for node_id in [
        "metadata.source-map.add",
        "metadata.source-map.cli",
        "metadata.source-map.main",
        "metadata.source-map.module",
        "metadata.source-map.sub",
    ]:
        metadata_attrs = attrs(nodes[node_id])
        for key in [
            "targetFile",
            "targetName",
            "targetKind",
            "compilerContract",
            "graphNodeIds",
            "requiredForRoundTrip",
        ]:
            if key not in metadata_attrs:
                raise CompileError(f"{node_id} missing metadata attribute {key}.")
        for graph_node_id in metadata_attrs["graphNodeIds"]:
            if graph_node_id not in nodes:
                raise CompileError(f"{node_id} references missing graph node {graph_node_id}.")

    return nodes, edges


def operation_expression(operation_kind: str) -> str:
    if operation_kind == "integer-add":
        return "left + right"
    if operation_kind == "integer-subtract":
        return "left - right"
    raise CompileError(f"Unsupported B0 operationKind: {operation_kind}")


def generate_calc_source(graph: dict[str, Any], nodes: dict[str, dict[str, Any]]) -> str:
    graph_digest = sha256_text(canonical_json(graph))
    cli_attrs = attrs(nodes["code.cli.command"])
    add_attrs = attrs(nodes["code.function.add"])
    sub_attrs = attrs(nodes["code.function.sub"])
    main_attrs = attrs(nodes["code.function.main"])

    allowed_operations = cli_attrs["argumentSchema"][0]["allowedValues"]
    if allowed_operations != ["add", "sub"]:
        raise CompileError("B0 compiler currently requires allowed operations ['add', 'sub'].")
    if cli_attrs["stdout"].get("format") != "plain-integer":
        raise CompileError("B0 compiler supports only plain-integer stdout.")
    if not cli_attrs["stdout"].get("trailingNewline"):
        raise CompileError("B0 compiler requires trailingNewline stdout.")

    add_name = add_attrs["functionName"]
    sub_name = sub_attrs["functionName"]
    main_name = main_attrs["functionName"]
    success_exit = int(main_attrs["successExitCode"])
    invalid_exit = int(main_attrs["invalidInputExitCode"])
    add_expression = operation_expression(add_attrs["operationKind"])
    sub_expression = operation_expression(sub_attrs["operationKind"])
    allowed_literal = "{" + ", ".join(f'"{operation}"' for operation in allowed_operations) + "}"
    usage_operations = "|".join(allowed_operations)

    return f'''# Generated by IntentGraph compiler contract: {COMPILER_CONTRACT}
# Source graph: {graph["graphId"]}
# Graph digest: sha256:{graph_digest}
"""Generated CLI calculator for the IntentGraph B0 benchmark."""

from __future__ import annotations

import sys


def {add_name}(left: int, right: int) -> int:
    return {add_expression}


def {sub_name}(left: int, right: int) -> int:
    return {sub_expression}


def {main_name}(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) != 3:
        print("usage: {cli_attrs["commandName"]} {{{usage_operations}}} LEFT RIGHT", file=sys.stderr)
        return {invalid_exit}
    operation, left_raw, right_raw = argv
    if operation not in {allowed_literal}:
        print(f"unsupported operation: {{operation}}", file=sys.stderr)
        return {invalid_exit}
    try:
        left = int(left_raw)
        right = int(right_raw)
    except ValueError:
        print("LEFT and RIGHT must be integers", file=sys.stderr)
        return {invalid_exit}
    if operation == "add":
        result = {add_name}(left, right)
    else:
        result = {sub_name}(left, right)
    print(result)
    return {success_exit}


if __name__ == "__main__":
    raise SystemExit({main_name}())
'''


def function_ranges(source: str) -> dict[str, tuple[int, int]]:
    tree = ast.parse(source)
    ranges: dict[str, tuple[int, int]] = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            ranges[node.name] = (node.lineno, node.end_lineno or node.lineno)
    return ranges


def target_range_for(metadata_attrs: dict[str, Any], source: str) -> tuple[int, int]:
    target_kind = metadata_attrs["targetKind"]
    target_name = metadata_attrs["targetName"]
    if target_kind == "module":
        return (1, len(source.splitlines()))
    if target_kind == "cli":
        return function_ranges(source)["main"]
    if target_kind == "function":
        return function_ranges(source)[target_name]
    raise CompileError(f"Unsupported targetKind in source map: {target_kind}")


def build_node_map(nodes: dict[str, dict[str, Any]], source: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for metadata_node in sorted(
        (node for node in nodes.values() if node.get("kind") == "metadata.sourceMap"),
        key=lambda node: node["id"],
    ):
        metadata_attrs = attrs(metadata_node)
        line_start, line_end = target_range_for(metadata_attrs, source)
        for graph_node_id in metadata_attrs["graphNodeIds"]:
            graph_node = nodes[graph_node_id]
            entries.append(
                {
                    "metadataNodeId": metadata_node["id"],
                    "graphNodeId": graph_node_id,
                    "nodeKind": graph_node["kind"],
                    "targetFile": metadata_attrs["targetFile"],
                    "targetName": metadata_attrs["targetName"],
                    "targetKind": metadata_attrs["targetKind"],
                    "lineStart": line_start,
                    "lineEnd": line_end,
                    "requiredForRoundTrip": bool(metadata_attrs["requiredForRoundTrip"]),
                }
            )
    return entries


def edge_preservation(edge_kind: str) -> str:
    if edge_kind in {"calls", "handled_by", "contains"}:
        return "source"
    if edge_kind == "projects_to":
        return "projection"
    return "metadata"


def build_edge_map(edges: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for edge in sorted(edges.values(), key=lambda item: item["id"]):
        entries.append(
            {
                "graphEdgeId": edge["id"],
                "edgeKind": edge["kind"],
                "from": edge["from"],
                "to": edge["to"],
                "preservation": edge_preservation(edge["kind"]),
            }
        )
    return entries


def build_projection_rules(graph: dict[str, Any]) -> dict[str, Any]:
    emitted_kinds = {"code.module", "code.function", "code.cli", "projection.target"}
    metadata_only_kinds = {"metadata.sourceMap", "evidence.record", "authority.record", "history.delta"}
    projection_only_kinds = {"intent.requirement", "domain.concept", "test.case"}
    classified: set[str] = set()
    emitted_to_source = [
        node["id"]
        for node in graph["nodes"]
        if node.get("kind") in emitted_kinds
    ]
    metadata_only = [
        node["id"]
        for node in graph["nodes"]
        if node.get("kind") in metadata_only_kinds
    ]
    projection_only = [
        node["id"]
        for node in graph["nodes"]
        if node.get("kind") in projection_only_kinds
    ]
    for node_id in emitted_to_source + metadata_only + projection_only:
        classified.add(node_id)
    unclassified = [
        node["id"]
        for node in graph["nodes"]
        if node["id"] not in classified
    ]
    return {
        "emittedToSource": emitted_to_source,
        "metadataOnly": metadata_only,
        "projectionOnly": projection_only,
        "unclassified": unclassified,
        "codeOnlyLossModel": graph["projections"]["codeOnlyLossModel"],
    }


def build_metadata(
    graph: dict[str, Any],
    nodes: dict[str, dict[str, Any]],
    edges: dict[str, dict[str, Any]],
    source: str,
    graph_path: Path,
) -> dict[str, Any]:
    source_hash = sha256_text(source)
    graph_digest = sha256_text(canonical_json(graph))
    return {
        "metadataVersion": METADATA_VERSION,
        "benchmarkId": graph["benchmarkId"],
        "graphId": graph["graphId"],
        "graphDigest": f"sha256:{graph_digest}",
        "compilerContract": COMPILER_CONTRACT,
        "generatedAt": DETERMINISTIC_GENERATED_AT,
        "sourceGraph": {
            "canonicalPath": "docs/examples/b0-python-cli-calculator.graph.json",
            "inputPath": graph_path.as_posix(),
            "digest": f"sha256:{graph_digest}",
            "graphirVersion": graph["graphirVersion"],
        },
        "generatedArtifacts": [
            {
                "path": "calc.py",
                "kind": "python-source",
                "sha256": source_hash,
            }
        ],
        "nodeMap": build_node_map(nodes, source),
        "edgeMap": build_edge_map(edges),
        "projectionRules": build_projection_rules(graph),
        "hiddenState": {
            "reason": "B0 exact round-trip needs non-code graph data for intent, evidence, authority, history, and stable graph identity.",
            "sourceGraphSnapshot": graph,
        },
        "diagnostics": {
            "status": "pass",
            "warnings": [
                "M2 metadata carries a full graph snapshot; M3 must treat it as preservation metadata, not code-derived reconstruction."
            ],
        },
    }


def build_diagnostics(
    graph: dict[str, Any],
    metadata: dict[str, Any],
    source: str,
) -> dict[str, Any]:
    metadata_text = canonical_pretty(metadata)
    return {
        "diagnosticsVersion": "0.1.0",
        "compilerContract": COMPILER_CONTRACT,
        "status": "pass",
        "benchmarkId": graph["benchmarkId"],
        "graphDigest": metadata["graphDigest"],
        "generatedAt": DETERMINISTIC_GENERATED_AT,
        "generatedArtifacts": [
            {
                "path": "calc.py",
                "sha256": sha256_text(source),
            },
            {
                "path": "calc.intentgraph.json",
                "sha256": sha256_text(metadata_text),
            },
        ],
        "warnings": metadata["diagnostics"]["warnings"],
        "errors": [],
    }


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def compile_graph(graph_path: Path, out_dir: Path) -> None:
    graph = read_json(graph_path)
    nodes, edges = validate_b0_graph(graph)
    source = generate_calc_source(graph, nodes)
    metadata = build_metadata(graph, nodes, edges, source, graph_path)
    diagnostics = build_diagnostics(graph, metadata, source)

    write_text(out_dir / "calc.py", source)
    write_text(out_dir / "calc.intentgraph.json", canonical_pretty(metadata))
    write_text(out_dir / "native-diagnostics.json", canonical_pretty(diagnostics))


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile the B0 IntentGraph fixture to Python.")
    parser.add_argument("--graph", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    try:
        compile_graph(args.graph, args.out)
    except CompileError as error:
        print(f"native compile failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
