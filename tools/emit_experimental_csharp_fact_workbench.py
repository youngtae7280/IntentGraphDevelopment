"""Emit a local, read-only HTML inspector for an experimental C# fact workspace."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from experimental_csharp_workspace import (
    AUTHORITY as WORKSPACE_AUTHORITY,
    ExperimentalWorkspaceError,
    LOGICAL_SOURCE_ROOT,
    PROFILE_ID,
    WORKSPACE_ROLE,
    canonical_json,
    digest_bytes,
    validate_workspace,
)


ROOT = Path(__file__).resolve().parents[1]
WORKBENCH_ROLE = "intentgraph-experimental-csharp-fact-workbench"
WORKBENCH_SCOPE = "p9.12-experimental-csharp-fact-only-workbench"
WORKBENCH_VERSION = "0.1.0"
ASSET_SOURCE = ROOT / "generated" / "product-surfaces" / "graph-delta-approval-workbench" / "p8.60" / "assets"
CYTOSCAPE_SOURCE = ASSET_SOURCE / "cytoscape.min.js"
CYTOSCAPE_LICENSE_SOURCE = ASSET_SOURCE / "cytoscape-license.txt"
ALLOWED_FACT_KINDS = {"file", "namespace", "type", "method", "constructor", "property", "field", "using", "invocation"}
ALLOWED_RELATION_KINDS = {"contains", "imports", "invokes-syntax"}
STRUCTURAL_KINDS = ["file", "namespace", "type"]
UNAVAILABLE_STATES = {
    "intentMapping": "not-recorded-in-fact-only-workspace",
    "changeProposal": "not-recorded-in-fact-only-workspace",
    "graphDelta": "not-recorded-in-fact-only-workspace",
    "codeDiff": "not-recorded-in-fact-only-workspace",
    "verification": "not-recorded-in-fact-only-workspace",
    "evidence": "not-recorded-in-fact-only-workspace",
    "acceptanceAuthority": "not-recorded-in-fact-only-workspace",
    "semanticHistory": "not-recorded-in-fact-only-workspace",
    "resolvedCallGraph": "not-available-syntax-only-extraction",
    "projectSystemEvaluation": "not-recorded-in-fact-only-workspace",
    "buildTestLaunch": "not-executed-in-fact-only-workspace",
}
WORKBENCH_AUTHORITY = {
    "workspaceSnapshotRead": True,
    "workspaceMutation": False,
    "targetRepositoryMutation": False,
    "targetBuildExecuted": False,
    "targetRestoreExecuted": False,
    "targetLaunchExecuted": False,
    "externalPackageRestoreExecuted": False,
    "packageDependencyAdded": False,
    "networkRequired": False,
    "providerApiAllowed": False,
    "credentialAccessAllowed": False,
    "automaticCodeApplication": False,
    "approvalAutomation": False,
    "graphMutationFromUi": False,
    "igdProductizationClaimed": False,
}


class FactWorkbenchError(ValueError):
    """Raised when a fact-only workbench contract is violated."""


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise FactWorkbenchError(f"invalid JSON artifact: {path.name}") from error
    if not isinstance(value, dict):
        raise FactWorkbenchError(f"JSON artifact must be an object: {path.name}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def canonical_digest(value: Any) -> str:
    return digest_bytes(canonical_json(value))


def file_digest(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def relative_file_records(root: Path) -> list[dict[str, str]]:
    if not root.is_dir():
        raise FactWorkbenchError("workspace must be an existing directory")
    records: list[dict[str, str]] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise FactWorkbenchError("workspace must not contain symlinks")
        if path.is_file():
            records.append({"path": path.relative_to(root).as_posix(), "sha256": file_digest(path)})
    if not records:
        raise FactWorkbenchError("workspace must contain files")
    return records


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def safe_relative_source(value: Any) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts


def assert_safe_tree(value: Any, path: str = "") -> None:
    forbidden_keys = {"sourceText", "targetSyntax", "externalSourcePath", "workspacePath", "physicalSourceRoot"}
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if key in forbidden_keys:
                raise FactWorkbenchError(f"{child_path} must not persist source text or physical paths")
            assert_safe_tree(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            assert_safe_tree(child, f"{path}[{index}]")


def label_for(fact: dict[str, Any]) -> str:
    kind = str(fact["kind"])
    if kind == "file":
        return str(fact["sourceFile"]).split("/")[-1]
    return str(fact.get("name") or kind)


def fact_interpretation(kind: str) -> str:
    if kind == "invocation":
        return "Ambiguous syntax observation. This is not a resolved call target."
    if kind == "using":
        return "Syntax-level using/import declaration."
    return "Extracted syntax fact with source-range provenance."


def relation_interpretation(kind: str) -> str:
    if kind == "invokes-syntax":
        return "Ambiguous syntax relation. It does not prove a resolved runtime or semantic call."
    if kind == "imports":
        return "Syntax-level import relation."
    return "Syntax containment relation."


def fact_node(fact: dict[str, Any]) -> dict[str, Any]:
    kind = str(fact["kind"])
    source_location = fact.get("sourceLocation")
    if not isinstance(source_location, dict):
        source_location = {"status": "file-level"}
    return {
        "id": fact["id"],
        "kind": kind,
        "label": label_for(fact),
        "source": {
            "file": fact["sourceFile"],
            "digest": fact["sourceDigest"],
            "location": source_location,
        },
        "provenance": {
            "extractor": fact["extractor"],
            "extractorVersion": fact["extractorVersion"],
            "confidence": fact["confidence"],
        },
        "declarationKind": fact.get("declarationKind"),
        "invocationShape": fact.get("invocationShape"),
        "interpretation": fact_interpretation(kind),
        "codeDiffState": "not-recorded-in-fact-only-workspace",
    }


def relation_edge(relation: dict[str, Any]) -> dict[str, Any]:
    kind = str(relation["kind"])
    return {
        "id": relation["id"],
        "kind": kind,
        "source": relation["from"],
        "target": relation["to"],
        "interpretation": relation_interpretation(kind),
        "confidence": "ambiguous" if kind == "invokes-syntax" else "extracted",
    }


def kind_counts(records: list[dict[str, Any]], key: str = "kind") -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        value = str(record[key])
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def source_file_counts(nodes: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for node in nodes:
        file_name = str(node["source"]["file"])
        counts[file_name] = counts.get(file_name, 0) + 1
    return dict(sorted(counts.items()))


def workspace_input_summary(paths: dict[str, Path], manifest: dict[str, Any]) -> dict[str, Any]:
    input_names = ["preflight", "intakeReceipt", "codeFacts", "extractionReport", "workspaceValidation"]
    return {
        "workspaceRole": manifest["artifactRole"],
        "workspaceSchemaVersion": manifest["schemaVersion"],
        "profileId": manifest["profile"]["id"],
        "profileDigest": manifest["profile"]["digest"],
        "logicalSourceRoot": manifest["source"]["logicalId"],
        "sourceDigest": manifest["source"]["digest"],
        "artifacts": {
            name: {"path": paths[name].relative_to(paths["sourceRoot"].parent).as_posix(), "sha256": file_digest(paths[name])}
            for name in input_names
        },
    }


def build_projection(workspace: Path) -> tuple[dict[str, Any], dict[str, Path], list[dict[str, str]]]:
    try:
        manifest, paths, summary = validate_workspace(workspace)
    except ExperimentalWorkspaceError as error:
        raise FactWorkbenchError(f"validated experimental C# workspace required: {error}") from error
    facts_document = read_json(paths["codeFacts"])
    assert_safe_tree(facts_document)
    if facts_document.get("artifactRole") != "intentgraph-code-facts":
        raise FactWorkbenchError("code facts artifact role is invalid")
    if facts_document.get("scope") != "experimental-csharp-host-sdk-fact-workspace":
        raise FactWorkbenchError("code facts scope is invalid")
    if facts_document.get("profileId") != PROFILE_ID or facts_document.get("sourceRoot") != LOGICAL_SOURCE_ROOT:
        raise FactWorkbenchError("code facts profile or logical source identity is invalid")
    extractor = facts_document.get("extractor")
    if not isinstance(extractor, dict) or extractor.get("semanticResolution") is not False or extractor.get("mode") != "roslyn-syntax-only":
        raise FactWorkbenchError("code facts must remain syntax-only without semantic resolution")
    raw_facts = facts_document.get("facts")
    raw_relations = facts_document.get("relations")
    if not isinstance(raw_facts, list) or not isinstance(raw_relations, list):
        raise FactWorkbenchError("code facts must contain facts and relations")
    nodes = [fact_node(fact) for fact in raw_facts if isinstance(fact, dict)]
    if len(nodes) != len(raw_facts) or not nodes:
        raise FactWorkbenchError("code facts must contain only object facts")
    if any(node["kind"] not in ALLOWED_FACT_KINDS for node in nodes):
        raise FactWorkbenchError("code facts contain an unknown fact kind")
    if any(not safe_relative_source(node["source"]["file"]) for node in nodes):
        raise FactWorkbenchError("code facts contain unsafe source references")
    node_ids = {node["id"] for node in nodes}
    if len(node_ids) != len(nodes):
        raise FactWorkbenchError("code facts contain duplicate node identifiers")
    edges = [relation_edge(relation) for relation in raw_relations if isinstance(relation, dict)]
    if len(edges) != len(raw_relations):
        raise FactWorkbenchError("code facts must contain only object relations")
    if any(edge["kind"] not in ALLOWED_RELATION_KINDS for edge in edges):
        raise FactWorkbenchError("code facts contain an unknown relation kind")
    if any(edge["source"] not in node_ids or edge["target"] not in node_ids for edge in edges):
        raise FactWorkbenchError("code facts contain a relation endpoint that does not resolve")
    if len({edge["id"] for edge in edges}) != len(edges):
        raise FactWorkbenchError("code facts contain duplicate relation identifiers")
    records_before = relative_file_records(workspace)
    projection = {
        "artifactRole": "intentgraph-experimental-csharp-fact-workbench-projection",
        "status": "intentgraph-experimental-csharp-fact-workbench-projection-emitted",
        "scope": WORKBENCH_SCOPE,
        "version": WORKBENCH_VERSION,
        "mode": "experimental-csharp-fact-only-workbench",
        "input": workspace_input_summary(paths, manifest),
        "snapshot": {
            "sourceRole": manifest["source"]["sourceRole"],
            "sourceFileCount": summary["sourceFileCount"],
            "sourceDigest": manifest["source"]["digest"],
            "externalSourcePathPersisted": False,
            "codeContentIncluded": False,
            "sourceSnapshotCoherent": True,
        },
        "extractor": {
            "id": extractor["id"],
            "version": extractor["version"],
            "mode": extractor["mode"],
            "deterministic": extractor["deterministic"],
            "semanticResolution": False,
            "resolvedCallGraph": False,
        },
        "graph": {
            "nodes": sorted(nodes, key=lambda item: item["id"]),
            "edges": sorted(edges, key=lambda item: item["id"]),
            "defaultView": {"nodeKinds": STRUCTURAL_KINDS, "edgeKinds": ["contains", "imports"]},
            "factKindCounts": kind_counts(nodes),
            "relationKindCounts": kind_counts(edges),
            "sourceFileCounts": source_file_counts(nodes),
        },
        "unavailable": UNAVAILABLE_STATES,
        "authority": WORKBENCH_AUTHORITY,
        "uiContract": {
            "staticLocalHtml": True,
            "graphLibrary": "cytoscape",
            "graphLibraryVersion": "3.34.0",
            "networkRequired": False,
            "externalRuntimeUrlsAllowed": False,
            "graphMutationFromUi": False,
            "approvalControlsPresent": False,
            "codeContentShown": False,
            "codeDiffShown": False,
        },
    }
    return projection, paths, records_before


def escape_html_data(projection: dict[str, Any]) -> str:
    return json.dumps(projection, ensure_ascii=True, sort_keys=True, separators=(",", ":")).replace("</", "<\\/")


def render_html(projection: dict[str, Any]) -> str:
    return HTML_TEMPLATE.replace("__WORKBENCH_DATA__", escape_html_data(projection))


def output_paths(output: Path) -> dict[str, Path]:
    return {
        "index": output / "index.html",
        "projection": output / "projection.json",
        "manifest": output / "manifest.json",
        "validation": output / "validation-report.json",
        "cytoscape": output / "assets" / "cytoscape.min.js",
        "license": output / "assets" / "cytoscape-license.txt",
    }


def validate_projection(projection: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if projection.get("artifactRole") != "intentgraph-experimental-csharp-fact-workbench-projection":
        errors.append("wrong projection artifact role")
    if projection.get("mode") != "experimental-csharp-fact-only-workbench":
        errors.append("wrong projection mode")
    if projection.get("unavailable") != UNAVAILABLE_STATES:
        errors.append("unavailable semantic/change state is incomplete")
    if projection.get("authority") != WORKBENCH_AUTHORITY:
        errors.append("workbench authority must remain fact-only and read-only")
    if projection.get("input", {}).get("workspaceRole") != WORKSPACE_ROLE:
        errors.append("projection workspace role is invalid")
    if projection.get("input", {}).get("profileId") != PROFILE_ID:
        errors.append("projection profile is invalid")
    if projection.get("input", {}).get("logicalSourceRoot") != LOGICAL_SOURCE_ROOT:
        errors.append("projection logical source identity is invalid")
    graph = projection.get("graph")
    if not isinstance(graph, dict):
        return errors + ["projection graph is missing"]
    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list) or not nodes:
        return errors + ["projection graph records are missing"]
    node_ids = {node.get("id") for node in nodes if isinstance(node, dict)}
    if len(node_ids) != len(nodes):
        errors.append("projection graph node identifiers are invalid")
    for node in nodes:
        if not isinstance(node, dict) or node.get("kind") not in ALLOWED_FACT_KINDS:
            errors.append("projection has an unknown node kind")
            continue
        source = node.get("source")
        if not isinstance(source, dict) or not safe_relative_source(source.get("file")) or not str(source.get("digest", "")).startswith("sha256:"):
            errors.append(f"node {node.get('id')} has invalid source provenance")
        if not node.get("interpretation") or node.get("codeDiffState") != UNAVAILABLE_STATES["codeDiff"]:
            errors.append(f"node {node.get('id')} inspector payload is incomplete")
    for edge in edges:
        if not isinstance(edge, dict) or edge.get("kind") not in ALLOWED_RELATION_KINDS:
            errors.append("projection has an unknown edge kind")
            continue
        if edge.get("source") not in node_ids or edge.get("target") not in node_ids:
            errors.append(f"edge {edge.get('id')} endpoint does not resolve")
        if not edge.get("interpretation"):
            errors.append(f"edge {edge.get('id')} inspector payload is incomplete")
    try:
        assert_safe_tree(projection)
    except FactWorkbenchError as error:
        errors.append(str(error))
    return errors


def validate_output(output: Path, workspace: Path, expected_projection: dict[str, Any], workspace_before: list[dict[str, str]]) -> dict[str, Any]:
    paths = output_paths(output)
    errors: list[str] = []
    for key, path in paths.items():
        if key == "validation":
            continue
        if not path.is_file():
            errors.append(f"missing output file: {key}")
    if errors:
        return {"result": "fail", "errors": errors}
    projection = read_json(paths["projection"])
    if projection != expected_projection:
        errors.append("projection does not match deterministic input projection")
    errors.extend(validate_projection(projection))
    html = paths["index"].read_text(encoding="utf-8")
    for marker in [
        "id=\"factGraph\"",
        "id=\"search\"",
        "id=\"kindFilter\"",
        "id=\"relationFilter\"",
        "id=\"sourceFilter\"",
        "id=\"nodeInspector\"",
        "id=\"edgeInspector\"",
        "id=\"unavailablePanel\"",
        "id=\"zoomIn\"",
        "id=\"zoomOut\"",
        "id=\"fitGraph\"",
        "assets/cytoscape.min.js",
    ]:
        if marker not in html:
            errors.append(f"HTML marker missing: {marker}")
    for forbidden in ["http://", "https://", "fetch(", "import(", "sourceText", "targetSyntax", "applyProposal", "approveProposal"]:
        if forbidden in html:
            errors.append(f"HTML contains forbidden token: {forbidden}")
    if file_digest(paths["cytoscape"]) != file_digest(CYTOSCAPE_SOURCE):
        errors.append("bundled Cytoscape asset digest does not match the declared local asset")
    if file_digest(paths["license"]) != file_digest(CYTOSCAPE_LICENSE_SOURCE):
        errors.append("bundled Cytoscape license digest does not match the declared local asset")
    manifest = read_json(paths["manifest"])
    expected_manifest = {
        "artifactRole": WORKBENCH_ROLE,
        "status": "intentgraph-experimental-csharp-fact-workbench-emitted",
        "scope": WORKBENCH_SCOPE,
        "version": WORKBENCH_VERSION,
        "input": expected_projection["input"],
        "workspaceMutation": False,
        "authority": WORKBENCH_AUTHORITY,
        "assets": {
            "cytoscape": {"path": "assets/cytoscape.min.js", "sha256": file_digest(paths["cytoscape"]), "version": "3.34.0"},
            "license": {"path": "assets/cytoscape-license.txt", "sha256": file_digest(paths["license"])},
        },
        "outputs": {
            "projection": {"path": "projection.json", "sha256": file_digest(paths["projection"])},
            "html": {"path": "index.html", "sha256": file_digest(paths["index"])},
        },
    }
    if manifest != expected_manifest:
        errors.append("workbench manifest is invalid")
    try:
        _, _, current_summary = validate_workspace(workspace)
        if relative_file_records(workspace) != workspace_before:
            errors.append("workbench export changed the input workspace")
        if current_summary != expected_projection["snapshot"].get("summary", current_summary):
            pass
    except ExperimentalWorkspaceError as error:
        errors.append(f"input workspace is no longer valid: {error}")
    result = "pass" if not errors else "fail"
    return {
        "artifactRole": "intentgraph-experimental-csharp-fact-workbench-validation-report",
        "status": f"intentgraph-experimental-csharp-fact-workbench-validation-{result}",
        "scope": WORKBENCH_SCOPE,
        "result": result,
        "errors": errors,
        "workspaceMutation": False,
        "sourceTextPersisted": False,
        "externalSourcePathPersisted": False,
        "networkRequired": False,
        "graphNavigationContract": result == "pass",
        "unavailableStateExplicit": result == "pass",
        "authority": WORKBENCH_AUTHORITY,
    }


def emit_workbench(workspace: Path, output: Path) -> dict[str, Any]:
    workspace = workspace.resolve()
    output = output.resolve()
    if output.exists():
        raise FactWorkbenchError("workbench output directory must not exist")
    if is_within(output, workspace) or is_within(workspace, output):
        raise FactWorkbenchError("workbench output directory must not overlap the input workspace")
    if not CYTOSCAPE_SOURCE.is_file() or not CYTOSCAPE_LICENSE_SOURCE.is_file():
        raise FactWorkbenchError("declared local Cytoscape asset is missing")
    projection, _, workspace_before = build_projection(workspace)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="p9.12-fact-workbench-", dir=output.parent) as temporary:
        staged = Path(temporary) / "output"
        paths = output_paths(staged)
        write_json(paths["projection"], projection)
        paths["index"].parent.mkdir(parents=True, exist_ok=True)
        paths["index"].write_text(render_html(projection), encoding="utf-8", newline="\n")
        paths["cytoscape"].parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(CYTOSCAPE_SOURCE, paths["cytoscape"])
        shutil.copyfile(CYTOSCAPE_LICENSE_SOURCE, paths["license"])
        manifest = {
            "artifactRole": WORKBENCH_ROLE,
            "status": "intentgraph-experimental-csharp-fact-workbench-emitted",
            "scope": WORKBENCH_SCOPE,
            "version": WORKBENCH_VERSION,
            "input": projection["input"],
            "workspaceMutation": False,
            "authority": WORKBENCH_AUTHORITY,
            "assets": {
                "cytoscape": {"path": "assets/cytoscape.min.js", "sha256": file_digest(paths["cytoscape"]), "version": "3.34.0"},
                "license": {"path": "assets/cytoscape-license.txt", "sha256": file_digest(paths["license"])},
            },
            "outputs": {
                "projection": {"path": "projection.json", "sha256": file_digest(paths["projection"])},
                "html": {"path": "index.html", "sha256": file_digest(paths["index"])},
            },
        }
        write_json(paths["manifest"], manifest)
        validation = validate_output(staged, workspace, projection, workspace_before)
        write_json(paths["validation"], validation)
        if validation["result"] != "pass":
            raise FactWorkbenchError("fact workbench validation failed: " + "; ".join(validation["errors"]))
        shutil.move(str(staged), str(output))
    return {
        "result": "pass",
        "command": "emit-experimental-csharp-fact-workbench",
        "outputRole": WORKBENCH_ROLE,
        "output": output.as_posix(),
        "mode": projection["mode"],
        "logicalSourceRoot": projection["input"]["logicalSourceRoot"],
        "sourceDigest": projection["snapshot"]["sourceDigest"],
        "factCount": len(projection["graph"]["nodes"]),
        "relationCount": len(projection["graph"]["edges"]),
        "workspaceMutation": False,
        "unavailable": projection["unavailable"],
        "authority": WORKBENCH_AUTHORITY,
    }


def validate_emitted_workbench(workspace: Path, output: Path) -> dict[str, Any]:
    workspace = workspace.resolve()
    output = output.resolve()
    if not output.is_dir():
        raise FactWorkbenchError("workbench output directory must exist")
    if is_within(output, workspace) or is_within(workspace, output):
        raise FactWorkbenchError("workbench output directory must not overlap the input workspace")
    projection, _, workspace_before = build_projection(workspace)
    validation = validate_output(output, workspace, projection, workspace_before)
    paths = output_paths(output)
    stored_validation = read_json(paths["validation"])
    if stored_validation != validation:
        raise FactWorkbenchError("stored workbench validation report is stale or invalid")
    if validation["result"] != "pass":
        raise FactWorkbenchError("fact workbench validation failed: " + "; ".join(validation["errors"]))
    return {
        "result": "pass",
        "command": "validate-experimental-csharp-fact-workbench",
        "outputRole": WORKBENCH_ROLE,
        "mode": projection["mode"],
        "factCount": len(projection["graph"]["nodes"]),
        "relationCount": len(projection["graph"]["edges"]),
        "workspaceMutation": False,
        "authority": WORKBENCH_AUTHORITY,
    }


HTML_TEMPLATE = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>IntentGraph C# Fact Explorer</title>
  <script src="assets/cytoscape.min.js"></script>
  <style>
    :root { --ink:#dbe2ea; --muted:#7f8b99; --quiet:#536171; --canvas:#090c10; --rail:#0d1218; --panel:#121922; --line:#263240; --line-hi:#344455; --accent:#44bdb2; --warning:#d5aa5d; --danger:#d56b69; --file:#a8b1bd; --namespace:#86a9bf; --type:#c9ae76; --method:#8bb999; --syntax:#a995c7; --left:270px; --right:358px; }
    * { box-sizing:border-box; }
    html, body { height:100%; margin:0; background:var(--canvas); color:var(--ink); font-family:Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; font-size:13px; }
    button, select, input { font:inherit; }
    .app { height:100%; display:grid; grid-template-rows:56px minmax(0,1fr); }
    .topbar { display:flex; align-items:center; gap:18px; padding:0 16px; border-bottom:1px solid var(--line); background:#0b1015; min-width:0; }
    .brand { display:flex; align-items:baseline; gap:9px; white-space:nowrap; }
    .brand strong { letter-spacing:0; font-size:15px; }
    .brand span { color:var(--muted); font:11px ui-monospace, SFMono-Regular, Consolas, monospace; }
    .topmeta { display:flex; gap:7px; min-width:0; overflow:hidden; }
    .badge { border:1px solid var(--line); color:var(--muted); padding:3px 7px; border-radius:3px; white-space:nowrap; font:11px ui-monospace, SFMono-Regular, Consolas, monospace; }
    .badge.accent { color:#a9e4dd; border-color:#28736c; background:#0d2425; }
    .workspace { display:grid; grid-template-columns:var(--left) 6px minmax(0,1fr) 6px var(--right); min-height:0; }
    .rail, .inspector { overflow:auto; background:var(--rail); min-width:0; }
    .rail { border-right:1px solid var(--line); padding:16px 14px 18px; }
    .inspector { border-left:1px solid var(--line); padding:16px 14px 24px; }
    .resizer { background:transparent; position:relative; cursor:col-resize; z-index:5; }
    .resizer::after { content:""; position:absolute; inset:0 2px; background:transparent; }
    .resizer:hover::after, .resizer.active::after { background:var(--accent); opacity:.7; }
    .canvas { min-width:0; min-height:0; display:grid; grid-template-rows:auto minmax(0,1fr); background:#0a0f14; }
    .canvasbar { display:flex; align-items:center; justify-content:space-between; gap:10px; padding:10px 14px; border-bottom:1px solid var(--line); background:#0d141b; }
    .canvasbar h1 { margin:0; font-size:14px; font-weight:600; }
    .canvasbar p { margin:3px 0 0; color:var(--muted); font-size:12px; }
    .tools { display:flex; gap:6px; flex-shrink:0; }
    .icon { min-width:28px; height:28px; border:1px solid var(--line-hi); background:#121b24; color:var(--ink); border-radius:3px; cursor:pointer; }
    .icon:hover { border-color:var(--accent); color:#b5ece6; }
    #factGraph { min-height:0; width:100%; height:100%; }
    .section { margin:0 0 18px; }
    .section h2 { margin:0 0 9px; color:#b9c5d2; font-size:11px; letter-spacing:.08em; text-transform:uppercase; }
    .filter { display:grid; gap:6px; margin:0 0 10px; }
    .filter label { color:var(--muted); font-size:11px; }
    input, select { width:100%; min-width:0; color:var(--ink); background:#101820; border:1px solid var(--line); border-radius:3px; padding:8px; outline:none; }
    input:focus, select:focus { border-color:var(--accent); box-shadow:0 0 0 2px rgba(68,189,178,.12); }
    .viewmodes { display:grid; grid-template-columns:1fr 1fr; gap:5px; }
    .mode { padding:7px 6px; border:1px solid var(--line); border-radius:3px; background:#101820; color:var(--muted); cursor:pointer; text-align:left; }
    .mode.active { color:#d8f3ee; border-color:#28736c; background:#0d2525; }
    .metrics { display:grid; grid-template-columns:1fr 1fr; gap:7px; }
    .metric { border-left:2px solid var(--line-hi); padding:7px 8px; background:#10161d; }
    .metric strong { display:block; color:var(--ink); font:600 16px ui-monospace, SFMono-Regular, Consolas, monospace; }
    .metric span { display:block; color:var(--muted); margin-top:2px; font-size:10px; }
    .legend { display:grid; gap:6px; color:var(--muted); font-size:11px; }
    .legend i { display:inline-block; width:8px; height:8px; margin-right:7px; border-radius:2px; vertical-align:middle; }
    .callout { border:1px solid #54452d; background:#1b1711; padding:10px; color:#d3bd95; line-height:1.45; border-radius:3px; }
    .callout strong { color:#ead7ae; }
    .detail { border:1px solid var(--line); background:#10161d; padding:10px; border-radius:3px; }
    .detail h3 { margin:0 0 6px; font-size:14px; overflow-wrap:anywhere; }
    .detail p { margin:0 0 9px; color:var(--muted); line-height:1.45; }
    .kv { display:grid; grid-template-columns:94px minmax(0,1fr); gap:6px 9px; margin:0; }
    .kv dt { color:var(--muted); font-size:11px; }
    .kv dd { margin:0; color:#c9d2dc; font:11px ui-monospace, SFMono-Regular, Consolas, monospace; overflow-wrap:anywhere; }
    .empty { color:var(--muted); border:1px dashed var(--line); padding:10px; border-radius:3px; line-height:1.45; }
    .statusList { display:grid; gap:5px; }
    .statusRow { display:flex; justify-content:space-between; gap:8px; border-bottom:1px solid #1c2630; padding:6px 0; }
    .statusRow span:first-child { color:#b8c3cf; }
    .statusRow span:last-child { color:var(--warning); text-align:right; font-size:10px; overflow-wrap:anywhere; }
    @media (max-width:900px) { :root { --left:230px; --right:300px; } .topmeta { display:none; } }
    @media (max-width:700px) { .workspace { grid-template-columns:1fr; overflow:auto; } .resizer { display:none; } .rail, .inspector { border:0; border-bottom:1px solid var(--line); } .canvas { min-height:500px; } }
  </style>
</head>
<body>
  <div class="app">
    <header class="topbar">
      <div class="brand"><strong>IntentGraph</strong><span>C# fact explorer</span></div>
      <div class="topmeta"><span class="badge accent">snapshot read-only</span><span class="badge" id="profileBadge"></span><span class="badge" id="sourceBadge"></span></div>
    </header>
    <div class="workspace">
      <aside class="rail">
        <section class="section">
          <h2>Graph lens</h2>
          <div class="viewmodes"><button class="mode active" data-mode="structure">Structure</button><button class="mode" data-mode="all">All matching</button><button class="mode" data-mode="focus">Focus selection</button><button class="mode" id="clearSelection">Clear focus</button></div>
        </section>
        <section class="section">
          <h2>Filter</h2>
          <div class="filter"><label for="search">Find fact</label><input id="search" type="search" placeholder="Name, file, or identifier"></div>
          <div class="filter"><label for="kindFilter">Fact kind</label><select id="kindFilter"></select></div>
          <div class="filter"><label for="relationFilter">Relation kind</label><select id="relationFilter"></select></div>
          <div class="filter"><label for="sourceFilter">Source file</label><select id="sourceFilter"></select></div>
        </section>
        <section class="section"><h2>Snapshot</h2><div class="metrics" id="metrics"></div></section>
        <section class="section"><h2>Legend</h2><div class="legend"><div><i style="background:var(--file)"></i>File</div><div><i style="background:var(--namespace)"></i>Namespace</div><div><i style="background:var(--type)"></i>Type</div><div><i style="background:var(--method)"></i>Method / member</div><div><i style="background:var(--syntax)"></i>Syntax invocation</div></div></section>
      </aside>
      <div class="resizer" data-side="left" role="separator" aria-label="Resize filters"></div>
      <main class="canvas">
        <div class="canvasbar"><div><h1 id="graphTitle">Structural overview</h1><p id="graphSummary"></p></div><div class="tools"><button class="icon" id="zoomOut" title="Zoom out">-</button><button class="icon" id="zoomIn" title="Zoom in">+</button><button class="icon" id="fitGraph" title="Fit graph">Fit</button></div></div>
        <div id="factGraph" aria-label="C sharp fact graph"></div>
      </main>
      <div class="resizer" data-side="right" role="separator" aria-label="Resize inspector"></div>
      <aside class="inspector">
        <section class="section"><h2>Selection</h2><div id="nodeInspector" class="empty">Select a graph node to inspect its source pointer and extraction provenance.</div><div id="edgeInspector" style="margin-top:8px"></div></section>
        <section class="section"><h2>Not recorded here</h2><div id="unavailablePanel" class="statusList"></div></section>
        <section class="section"><h2>Extraction boundary</h2><div id="boundaryPanel" class="callout"></div></section>
      </aside>
    </div>
  </div>
  <script id="workbench-data" type="application/json">__WORKBENCH_DATA__</script>
  <script>
    const model = JSON.parse(document.getElementById('workbench-data').textContent);
    const allNodes = model.graph.nodes;
    const allEdges = model.graph.edges;
    const nodesById = new Map(allNodes.map(item => [item.id, item]));
    const state = { mode: 'structure', selected: null, cy: null };
    const kindColor = { file:'#a8b1bd', namespace:'#86a9bf', type:'#c9ae76', method:'#8bb999', constructor:'#8bb999', property:'#8bb999', field:'#8bb999', using:'#86a9bf', invocation:'#a995c7' };
    const safe = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
    const shortDigest = value => String(value || '').replace('sha256:', '').slice(0, 12);
    function populate(select, values, label) { select.innerHTML = `<option value="">All ${label}</option>` + values.map(value => `<option value="${safe(value)}">${safe(value)}</option>`).join(''); }
    function initControls() {
      populate(document.getElementById('kindFilter'), Object.keys(model.graph.factKindCounts), 'fact kinds');
      populate(document.getElementById('relationFilter'), Object.keys(model.graph.relationKindCounts), 'relation kinds');
      populate(document.getElementById('sourceFilter'), Object.keys(model.graph.sourceFileCounts), 'source files');
      ['search','kindFilter','relationFilter','sourceFilter'].forEach(id => { const control = document.getElementById(id); control.addEventListener('input', renderGraph); control.addEventListener('change', renderGraph); });
      document.querySelectorAll('[data-mode]').forEach(button => button.addEventListener('click', () => { state.mode = button.dataset.mode; document.querySelectorAll('[data-mode]').forEach(item => item.classList.toggle('active', item === button)); renderGraph(); }));
      document.getElementById('clearSelection').addEventListener('click', () => { state.selected = null; renderGraph(); renderSelection(); });
    }
    function filters() { return { search:document.getElementById('search').value.trim().toLowerCase(), kind:document.getElementById('kindFilter').value, relation:document.getElementById('relationFilter').value, source:document.getElementById('sourceFilter').value }; }
    function selectNodes() {
      const filter = filters();
      let nodes = allNodes.filter(node => (!filter.kind || node.kind === filter.kind) && (!filter.source || node.source.file === filter.source) && (!filter.search || `${node.label} ${node.source.file} ${node.id}`.toLowerCase().includes(filter.search)));
      const detailRequested = Boolean(filter.search || filter.relation || (filter.kind && !model.graph.defaultView.nodeKinds.includes(filter.kind)));
      if (state.mode === 'structure' && !detailRequested) nodes = nodes.filter(node => model.graph.defaultView.nodeKinds.includes(node.kind));
      if (state.mode === 'focus' && state.selected) {
        const neighborIds = new Set();
        if (state.selected.type === 'node') neighborIds.add(state.selected.id);
        allEdges.forEach(edge => { if (edge.id === state.selected.id || edge.source === state.selected.id) { neighborIds.add(edge.source); neighborIds.add(edge.target); } if (edge.target === state.selected.id) { neighborIds.add(edge.source); neighborIds.add(edge.target); } });
        nodes = nodes.filter(node => neighborIds.has(node.id));
      }
      return nodes;
    }
    function selectEdges(nodeIds) {
      const filter = filters();
      const detailRequested = Boolean(filter.search || filter.relation || (filter.kind && !model.graph.defaultView.nodeKinds.includes(filter.kind)));
      return allEdges.filter(edge => nodeIds.has(edge.source) && nodeIds.has(edge.target) && (!filter.relation || edge.kind === filter.relation) && (state.mode !== 'structure' || detailRequested || model.graph.defaultView.edgeKinds.includes(edge.kind)));
    }
    function graphElements() {
      const nodes = selectNodes(); const nodeIds = new Set(nodes.map(node => node.id)); const edges = selectEdges(nodeIds);
      return { nodes, edges, elements:[...nodes.map(node => ({data:{id:node.id,label:node.label,kind:node.kind}})), ...edges.map(edge => ({data:{id:edge.id,source:edge.source,target:edge.target,kind:edge.kind}}))] };
    }
    function renderGraph() {
      const graph = graphElements();
      document.getElementById('graphTitle').textContent = state.mode === 'structure' ? 'Structural overview' : state.mode === 'focus' ? 'Focused neighborhood' : 'All matching facts';
      document.getElementById('graphSummary').textContent = `${graph.nodes.length.toLocaleString()} facts / ${graph.edges.length.toLocaleString()} syntax relations visible`;
      if (state.cy) state.cy.destroy();
      state.cy = cytoscape({ container:document.getElementById('factGraph'), elements:graph.elements, style:[
        {selector:'node',style:{'background-color':element => kindColor[element.data('kind')] || '#a8b1bd','label':element => element.data('label'),'color':'#c8d2dd','font-size':10,'text-wrap':'ellipsis','text-max-width':100,'text-valign':'bottom','text-margin-y':6,'width':element => element.data('kind') === 'file' ? 20 : 14,'height':element => element.data('kind') === 'file' ? 20 : 14,'border-width':1,'border-color':'#19232d'}},
        {selector:'edge',style:{'width':1,'line-color':'#384957','target-arrow-color':'#384957','target-arrow-shape':'triangle','curve-style':'bezier','opacity':.72}},
        {selector:'edge[kind = "invokes-syntax"]',style:{'line-style':'dashed','line-color':'#776798','target-arrow-color':'#776798'}},
        {selector:':selected',style:{'border-width':3,'border-color':'#44bdb2','line-color':'#44bdb2','target-arrow-color':'#44bdb2','z-index':99}},
        {selector:'.dim',style:{'opacity':.16}},
      ], layout:{name:'cose',animate:false,randomize:false,fit:true,padding:42,nodeRepulsion:9000,idealEdgeLength:72,gravity:.6}, minZoom:.22,maxZoom:2.5,wheelSensitivity:.16 });
      state.cy.on('tap','node', event => { state.selected = {type:'node',id:event.target.id()}; renderSelection(); highlightSelection(); });
      state.cy.on('tap','edge', event => { state.selected = {type:'edge',id:event.target.id()}; renderSelection(); highlightSelection(); });
      state.cy.on('tap', event => { if (event.target === state.cy) { state.selected = null; renderSelection(); } });
      state.cy.on('zoom', semanticZoom);
      semanticZoom();
      highlightSelection();
    }
    function semanticZoom() { const showLabels = state.cy.zoom() > .62; state.cy.style().selector('node').style('font-size', showLabels ? 10 : 0).update(); }
    function highlightSelection() { if (!state.cy || !state.selected) return; const element = state.cy.$id(state.selected.id); if (!element.length) return; state.cy.elements().addClass('dim'); element.removeClass('dim').select(); if (state.selected.type === 'node') element.connectedEdges().removeClass('dim'); if (state.selected.type === 'edge') element.connectedNodes().removeClass('dim'); }
    function rows(entries) { return `<dl class="kv">${entries.map(([key,value]) => `<dt>${safe(key)}</dt><dd>${safe(value)}</dd>`).join('')}</dl>`; }
    function renderSelection() {
      const nodePanel = document.getElementById('nodeInspector'); const edgePanel = document.getElementById('edgeInspector'); edgePanel.innerHTML = '';
      if (!state.selected) { nodePanel.className='empty'; nodePanel.textContent='Select a graph node or edge to inspect its fact provenance.'; return; }
      if (state.selected.type === 'node') {
        const node = nodesById.get(state.selected.id); if (!node) return;
        nodePanel.className='detail'; nodePanel.innerHTML = `<h3>${safe(node.label)}</h3><p>${safe(node.interpretation)}</p>${rows([['kind',node.kind],['source file',node.source.file],['range',`${node.source.location.lineStart || 'file'}:${node.source.location.columnStart || ''} - ${node.source.location.lineEnd || ''}:${node.source.location.columnEnd || ''}`],['source digest',shortDigest(node.source.digest)],['confidence',node.provenance.confidence],['declaration',node.declarationKind || 'n/a'],['shape',node.invocationShape || 'n/a'],['code diff', 'Not recorded in this fact-only workspace']])}`;
      } else {
        const edge = allEdges.find(item => item.id === state.selected.id); if (!edge) return;
        nodePanel.className='empty'; nodePanel.textContent='Edge selected.'; edgePanel.innerHTML = `<div class="detail"><h3>${safe(edge.kind)}</h3><p>${safe(edge.interpretation)}</p>${rows([['source',edge.source],['target',edge.target],['confidence',edge.confidence]])}</div>`;
      }
    }
    function renderStaticPanels() {
      document.getElementById('profileBadge').textContent = model.input.profileId;
      document.getElementById('sourceBadge').textContent = `snapshot ${shortDigest(model.snapshot.sourceDigest)}`;
      const metrics = [['files',model.snapshot.sourceFileCount],['facts',allNodes.length],['relations',allEdges.length],['resolved calls','0']];
      document.getElementById('metrics').innerHTML = metrics.map(([label,value]) => `<div class="metric"><strong>${Number(value).toLocaleString()}</strong><span>${safe(label)}</span></div>`).join('');
      document.getElementById('unavailablePanel').innerHTML = Object.entries(model.unavailable).map(([name,status]) => `<div class="statusRow"><span>${safe(name)}</span><span>${safe(status)}</span></div>`).join('');
      document.getElementById('boundaryPanel').innerHTML = `<strong>Syntax-only snapshot.</strong><br>Invocation nodes and dashed edges are ambiguous syntax observations, not resolved calls. This export contains no source text, code diff, proposal, approval, build, test, or launch result.`;
    }
    function installResize() { document.querySelectorAll('.resizer').forEach(handle => handle.addEventListener('pointerdown', event => { event.preventDefault(); handle.classList.add('active'); const side=handle.dataset.side; const start=event.clientX; const initial=parseInt(getComputedStyle(document.documentElement).getPropertyValue(side === 'left' ? '--left' : '--right')); const move=moveEvent => { const delta=moveEvent.clientX-start; const value=side === 'left' ? initial+delta : initial-delta; document.documentElement.style.setProperty(side === 'left' ? '--left' : '--right', `${Math.max(210,Math.min(520,value))}px`); state.cy && state.cy.resize(); }; const up=()=>{handle.classList.remove('active'); window.removeEventListener('pointermove',move);window.removeEventListener('pointerup',up);state.cy&&state.cy.fit(undefined,42);}; window.addEventListener('pointermove',move);window.addEventListener('pointerup',up); })); }
    document.getElementById('zoomIn').addEventListener('click',()=>state.cy.zoom({level:state.cy.zoom()*1.18,renderedPosition:{x:state.cy.width()/2,y:state.cy.height()/2}}));
    document.getElementById('zoomOut').addEventListener('click',()=>state.cy.zoom({level:state.cy.zoom()/1.18,renderedPosition:{x:state.cy.width()/2,y:state.cy.height()/2}}));
    document.getElementById('fitGraph').addEventListener('click',()=>state.cy.fit(undefined,42));
    initControls(); renderStaticPanels(); renderGraph(); renderSelection(); installResize();
  </script>
</body>
</html>'''


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        print(json.dumps(emit_workbench(args.workspace, args.out), ensure_ascii=True, indent=2))
        return 0
    except FactWorkbenchError as error:
        print(f"error: {error}", file=__import__("sys").stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
