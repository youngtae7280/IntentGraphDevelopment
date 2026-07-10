"""Emit a static graph-delta approval workbench HTML prototype."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


WORK_ITEM = "P8.60 Static Graph Delta Approval Workbench Prototype"
SCOPE = "p8.60-static-graph-delta-approval-workbench-prototype"
REPORT_VERSION = "0.1.0"
DATE = "2026-07-10"
CYTOSCAPE_VERSION = "3.34.0"
DEFAULT_OUTPUT_DIR = Path("generated/product-surfaces/graph-delta-approval-workbench/p8.60")
DEFAULT_PROJECTION = Path("generated/windowsutility/graph-delta-approval-workbench/p8.59/projection.json")
DEFAULT_CYTOSCAPE_JS = DEFAULT_OUTPUT_DIR / "assets" / "cytoscape.min.js"
DEFAULT_CYTOSCAPE_LICENSE = DEFAULT_OUTPUT_DIR / "assets" / "cytoscape-license.txt"


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def digest_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def digest_json(data: Any) -> str:
    return digest_bytes(json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def file_summary(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    summary: dict[str, Any] = {
        "path": path.as_posix(),
        "byteLength": len(raw),
        "sha256": digest_bytes(raw),
    }
    if path.suffix.lower() == ".json":
        data = read_json(path)
        for key in ["artifactRole", "status", "scope", "workItem", "result", "decision"]:
            if key in data:
                summary[key] = data[key]
    return summary


def relative_file_summary(root: Path, rel_path: str) -> dict[str, Any]:
    summary = file_summary(root / rel_path)
    summary["path"] = rel_path
    return summary


def copy_asset(source: Path, target: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(f"required asset source missing: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() == target.resolve():
        return
    shutil.copyfile(source, target)


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def assert_false_tree(value: Any, path: str, errors: list[str]) -> None:
    unsafe_true_keys = {
        "approvalAutomation",
        "approvalAutomationAuthorized",
        "graphMutationFromUi",
        "graphMutationFromUiAuthorized",
        "packageExtractionPerformed",
        "packageExtractionAuthorized",
        "packagedExecutableLaunchPerformed",
        "packagedExecutableLaunchAuthorized",
        "productizationClaimed",
        "productizationAuthorized",
        "releasePublished",
        "releasePublishingAuthorized",
        "sourceEditsAuthorized",
        "targetWritesAuthorized",
        "windowsUtilitySourceMutated",
    }
    if isinstance(value, dict):
        for key, child in value.items():
            next_path = f"{path}.{key}" if path else str(key)
            if key in unsafe_true_keys and child is True:
                errors.append(f"{next_path} must remain false")
            assert_false_tree(child, next_path, errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            assert_false_tree(child, f"{path}[{index}]", errors)


def build_workbench_projection(source_projection: dict[str, Any], source_projection_path: Path) -> dict[str, Any]:
    projection = copy.deepcopy(source_projection)
    projection["artifactRole"] = "intentgraph-static-graph-delta-approval-workbench-projection"
    projection["status"] = "intentgraph-static-graph-delta-approval-workbench-projection-emitted"
    projection["scope"] = SCOPE
    projection["workItem"] = WORK_ITEM
    projection["reportVersion"] = REPORT_VERSION
    projection["date"] = DATE
    projection["sourceProjection"] = file_summary(source_projection_path)
    projection.setdefault("claimScope", {})
    projection["claimScope"].update(
        {
            "projectionOnly": False,
            "staticHtmlImplemented": True,
            "graphUiImplemented": True,
            "graphDeltaVisualizationImplemented": True,
            "nodeInspectorImplemented": True,
            "edgeInspectorImplemented": True,
            "codeDiffInspectorImplemented": True,
            "graphElementDiffInspectorImplemented": True,
            "evidenceAuthorityInspectorImplemented": True,
            "graphMutationFromUi": False,
            "approvalAutomation": False,
            "windowsUtilitySourceMutated": False,
            "packageExtractionPerformed": False,
            "packagedExecutableLaunchPerformed": False,
            "releasePublished": False,
            "productizationClaimed": False,
        }
    )
    projection["uiContract"] = {
        "mode": "static-local-approval-workbench",
        "graphLibrary": "cytoscape",
        "graphLibraryVersion": CYTOSCAPE_VERSION,
        "networkRequired": False,
        "externalRuntimeUrlsAllowed": False,
        "graphInteractionQuality": {
            "userPanningEnabled": True,
            "wheelZoomEnabled": True,
            "toolbarZoomControls": True,
            "fitControl": True,
            "semanticZoomKeepsNodesAndEdgesReadable": True,
            "graphifyGradeInspectabilityTarget": True,
        },
        "selectionBehaviors": [
            "node-click-shows-node-inspector",
            "edge-click-shows-edge-inspector",
            "delta-step-click-highlights-affected-elements",
            "code-node-click-shows-code-diff",
            "changed-node-click-shows-graph-node-before-after-diff",
            "changed-edge-click-shows-graph-edge-before-after-diff",
        ],
        "mutationControlsPresent": False,
        "approvalControlsPresent": False,
    }
    return projection


def render_html(projection: dict[str, Any]) -> str:
    data = json.dumps(projection, sort_keys=True, ensure_ascii=False).replace("</", "<\\/")
    return HTML_TEMPLATE.replace("__WORKBENCH_DATA__", data)


def validate_projection_contract(projection: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    graph = projection.get("graph", {})
    delta = projection.get("delta", {})
    nodes = as_list(graph.get("nodes"))
    edges = as_list(graph.get("edges"))
    node_ids = {node.get("id") for node in nodes if isinstance(node, dict)}
    edge_ids = {edge.get("id") for edge in edges if isinstance(edge, dict)}
    code_diff_ids = {diff.get("id") for diff in as_list(delta.get("codeDiffs")) if isinstance(diff, dict)}
    graph_node_diff_ids = {diff.get("id") for diff in as_list(delta.get("graphNodeDiffs")) if isinstance(diff, dict)}
    graph_edge_diff_ids = {diff.get("id") for diff in as_list(delta.get("graphEdgeDiffs")) if isinstance(diff, dict)}

    if not nodes:
        errors.append("projection graph nodes missing")
    if not edges:
        errors.append("projection graph edges missing")
    if not code_diff_ids:
        errors.append("projection must include at least one code diff")
    if not graph_node_diff_ids:
        errors.append("projection must include at least one graph node diff")
    if not graph_edge_diff_ids:
        errors.append("projection must include at least one graph edge diff")

    for edge in edges:
        if not isinstance(edge, dict):
            continue
        if edge.get("source") not in node_ids:
            errors.append(f"edge {edge.get('id')} source endpoint missing")
        if edge.get("target") not in node_ids:
            errors.append(f"edge {edge.get('id')} target endpoint missing")
        if edge.get("status") == "changed" and edge.get("graphDiffRef") not in graph_edge_diff_ids:
            errors.append(f"changed edge {edge.get('id')} must reference graph edge diff")

    for node in nodes:
        if not isinstance(node, dict):
            continue
        if node.get("status") == "changed" and node.get("graphDiffRef") not in graph_node_diff_ids:
            errors.append(f"changed node {node.get('id')} must reference graph node diff")
        if str(node.get("kind", "")).startswith("code") and node.get("status") in {"added", "changed"}:
            refs = set(as_list(node.get("codeDiffRefs")))
            missing = sorted(ref for ref in refs if ref not in code_diff_ids)
            if not refs:
                errors.append(f"code node {node.get('id')} must expose code diff refs")
            for ref in missing:
                errors.append(f"code node {node.get('id')} references missing code diff {ref}")

    for diff in as_list(delta.get("codeDiffs")):
        if not isinstance(diff, dict):
            continue
        for node_id in as_list(diff.get("affectedNodeIds")):
            if node_id not in node_ids:
                errors.append(f"code diff {diff.get('id')} affected node missing: {node_id}")
        for edge_id in as_list(diff.get("affectedEdgeIds")):
            if edge_id not in edge_ids:
                errors.append(f"code diff {diff.get('id')} affected edge missing: {edge_id}")

    for diff in as_list(delta.get("graphNodeDiffs")):
        if not isinstance(diff, dict):
            continue
        if diff.get("elementId") not in node_ids:
            errors.append(f"graph node diff {diff.get('id')} element node missing")
        if not diff.get("beforePayload") or not diff.get("afterPayload"):
            errors.append(f"graph node diff {diff.get('id')} must include beforePayload and afterPayload")
        if not diff.get("changedFields"):
            errors.append(f"graph node diff {diff.get('id')} must list changedFields")

    for diff in as_list(delta.get("graphEdgeDiffs")):
        if not isinstance(diff, dict):
            continue
        if diff.get("elementId") not in edge_ids:
            errors.append(f"graph edge diff {diff.get('id')} element edge missing")
        if not diff.get("beforePayload") or not diff.get("afterPayload"):
            errors.append(f"graph edge diff {diff.get('id')} must include beforePayload and afterPayload")
        if not diff.get("changedFields"):
            errors.append(f"graph edge diff {diff.get('id')} must list changedFields")

    assert_false_tree(projection.get("authorizations", {}), "authorizations", errors)
    assert_false_tree(projection.get("claimScope", {}), "claimScope", errors)
    return errors


def validate_output(output_dir: Path, projection: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    index = output_dir / "index.html"
    projection_path = output_dir / "projection.json"
    manifest_path = output_dir / "manifest.json"
    cytoscape_js = output_dir / "assets" / "cytoscape.min.js"
    license_path = output_dir / "assets" / "cytoscape-license.txt"

    for path in [index, projection_path, manifest_path, cytoscape_js, license_path]:
        if not path.exists():
            errors.append(f"missing required file: {path.as_posix()}")

    errors.extend(validate_projection_contract(projection))

    if index.exists():
        html = index.read_text(encoding="utf-8")
        forbidden = ["https://", "http://", "import(", "fetch("]
        for token in forbidden:
            if token in html:
                errors.append(f"index must not require network or dynamic imports: {token}")
        required_markers = [
            "id=\"graphCanvas\"",
            "id=\"inspectorPanel\"",
            "id=\"deltaSteps\"",
            "id=\"codeDiffPanel\"",
            "id=\"graphDiffPanel\"",
            "id=\"zoomIn\"",
            "id=\"zoomOut\"",
            "id=\"fitGraph\"",
            "wheelSensitivity",
            "userPanningEnabled",
            "applySemanticZoom",
            "renderCodeDiffs",
            "renderGraphElementDiff",
            "changedFields",
            "cytoscape.min.js",
            "selectGraphElement",
            "selectDeltaStep",
        ]
        for marker in required_markers:
            if marker not in html:
                errors.append(f"index missing required marker: {marker}")

    if manifest_path.exists():
        manifest = read_json(manifest_path)
        if manifest.get("artifactRole") != "intentgraph-static-graph-delta-approval-workbench-manifest":
            errors.append("manifest artifactRole mismatch")
        for entry in as_list(manifest.get("files")):
            rel = entry.get("path") if isinstance(entry, dict) else None
            expected_digest = entry.get("sha256") if isinstance(entry, dict) else None
            if not rel or not expected_digest:
                errors.append("manifest file entry missing path or sha256")
                continue
            target = output_dir / rel
            if not target.exists():
                errors.append(f"manifest file missing: {rel}")
                continue
            actual = digest_bytes(target.read_bytes())
            if actual != expected_digest:
                errors.append(f"manifest digest mismatch: {rel}")

    result = "pass" if not errors else "fail"
    return {
        "artifactRole": "intentgraph-static-graph-delta-approval-workbench-validation-report",
        "status": "intentgraph-static-graph-delta-approval-workbench-validation-passed"
        if result == "pass"
        else "intentgraph-static-graph-delta-approval-workbench-validation-failed",
        "scope": SCOPE,
        "workItem": WORK_ITEM,
        "result": result,
        "errors": errors,
        "counts": {
            "nodes": len(as_list(projection.get("graph", {}).get("nodes"))),
            "edges": len(as_list(projection.get("graph", {}).get("edges"))),
            "deltaSteps": len(as_list(projection.get("delta", {}).get("steps"))),
            "codeDiffs": len(as_list(projection.get("delta", {}).get("codeDiffs"))),
            "graphNodeDiffs": len(as_list(projection.get("delta", {}).get("graphNodeDiffs"))),
            "graphEdgeDiffs": len(as_list(projection.get("delta", {}).get("graphEdgeDiffs"))),
        },
        "uiChecks": {
            "graphCanvas": result == "pass",
            "nodeInspector": result == "pass",
            "edgeInspector": result == "pass",
            "deltaStepHighlighting": result == "pass",
            "codeDiffPanel": result == "pass",
            "changedNodeDiffPanel": result == "pass",
            "changedEdgeDiffPanel": result == "pass",
            "panZoomInteraction": result == "pass",
            "semanticZoom": result == "pass",
            "graphifyGradeInspectabilityTarget": result == "pass",
            "localCytoscapeAsset": cytoscape_js.exists(),
            "networkDependency": False,
            "mutationControlsPresent": False,
            "approvalAutomationPresent": False,
        },
    }


def build_manifest(output_dir: Path, projection_path: Path, source_projection_path: Path) -> dict[str, Any]:
    files = [
        relative_file_summary(output_dir, "index.html"),
        relative_file_summary(output_dir, "projection.json"),
        relative_file_summary(output_dir, "assets/cytoscape.min.js"),
        relative_file_summary(output_dir, "assets/cytoscape-license.txt"),
    ]
    return {
        "artifactRole": "intentgraph-static-graph-delta-approval-workbench-manifest",
        "status": "intentgraph-static-graph-delta-approval-workbench-manifest-emitted",
        "scope": SCOPE,
        "workItem": WORK_ITEM,
        "date": DATE,
        "sourceProjection": file_summary(source_projection_path),
        "projection": file_summary(projection_path),
        "runtime": {
            "graphLibrary": "cytoscape",
            "graphLibraryVersion": CYTOSCAPE_VERSION,
            "assetPath": "assets/cytoscape.min.js",
            "networkRequired": False,
            "cdnRequired": False,
            "panZoomRequired": True,
            "semanticZoomRequired": True,
        },
        "files": files,
        "claimScope": {
            "staticHtmlImplemented": True,
            "graphUiImplemented": True,
            "graphMutationFromUi": False,
            "approvalAutomation": False,
            "windowsUtilitySourceMutated": False,
            "packageExtractionPerformed": False,
            "packagedExecutableLaunchPerformed": False,
            "releasePublished": False,
            "productizationClaimed": False,
        },
    }


def build_roadmap_report(output_dir: Path, validation: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifactRole": "intentgraph-roadmap-phase-report",
        "status": "intentgraph-roadmap-phase-completed" if validation.get("result") == "pass" else "intentgraph-roadmap-phase-failed",
        "scope": SCOPE,
        "workItem": WORK_ITEM,
        "date": DATE,
        "result": validation.get("result"),
        "outputDir": output_dir.as_posix(),
        "producedArtifacts": [
            "tools/emit_graph_delta_approval_workbench_static_html.py",
            (output_dir / "index.html").as_posix(),
            (output_dir / "projection.json").as_posix(),
            (output_dir / "manifest.json").as_posix(),
            (output_dir / "validation-report.json").as_posix(),
            (output_dir / "assets" / "cytoscape.min.js").as_posix(),
            (output_dir / "assets" / "cytoscape-license.txt").as_posix(),
        ],
        "validation": validation,
        "manifestDigest": digest_json(manifest),
        "implementedSelectionBehaviors": [
            "node selection inspector",
            "edge selection inspector",
            "delta step highlighting",
            "code node code diff panel",
            "changed node before/after graph diff panel",
            "changed edge before/after graph diff panel",
            "evidence and authority panel",
        ],
        "nonGoals": {
            "approvalAutomation": False,
            "graphMutationFromUi": False,
            "windowsUtilitySourceMutation": False,
            "packageExtraction": False,
            "packagedExecutableLaunch": False,
            "releasePublishing": False,
            "productizationClaimed": False,
        },
        "recommendedNextSlice": "P8.61 Static Graph Delta Approval Workbench Visual/Interaction Dry Run",
    }


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>IntentGraph Graph Delta Approval Workbench</title>
  <script src="assets/cytoscape.min.js"></script>
  <style>
    :root {
      --ink: #17202f;
      --muted: #687385;
      --paper: #fbfcfe;
      --surface: #f3f5f8;
      --surface-strong: #e9edf3;
      --line: #d7dde7;
      --line-strong: #b7c0ce;
      --accent: #2f63d6;
      --accent-soft: #e8efff;
      --add: #16825d;
      --add-soft: #e8f7f1;
      --changed: #9a6500;
      --changed-soft: #fff4db;
      --removed: #b83b30;
      --removed-soft: #fff0ed;
      --code: #145c72;
      --shadow: rgba(20, 31, 48, 0.08);
      --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
      --sans: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      background: var(--surface);
      font-family: var(--sans);
      letter-spacing: 0;
    }
    button, input, select { font: inherit; }
    .shell {
      height: 100vh;
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
    }
    .topbar {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 18px;
      align-items: center;
      padding: 14px 18px;
      background: var(--paper);
      border-bottom: 1px solid var(--line);
    }
    .eyebrow {
      font-size: 11px;
      text-transform: uppercase;
      color: var(--muted);
      letter-spacing: .08em;
      margin-bottom: 4px;
    }
    h1 {
      margin: 0;
      font-size: 19px;
      line-height: 1.2;
      letter-spacing: 0;
    }
    .summary {
      margin-top: 5px;
      color: var(--muted);
      font-size: 13px;
    }
    .badges {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }
    .badge {
      display: inline-flex;
      min-height: 25px;
      align-items: center;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--muted);
      border-radius: 999px;
      padding: 3px 9px;
      font-size: 12px;
      white-space: nowrap;
    }
    .badge.ok { color: var(--add); border-color: #a9d9c6; background: var(--add-soft); }
    .badge.warn { color: var(--changed); border-color: #e4c98f; background: var(--changed-soft); }
    .workbench {
      min-height: 0;
      display: grid;
      grid-template-columns: 260px minmax(480px, 1fr) 390px;
      grid-template-rows: minmax(0, 1fr) 250px;
    }
    .rail, .inspector, .diffDock {
      background: var(--paper);
      border-color: var(--line);
    }
    .rail {
      grid-row: 1 / 3;
      border-right: 1px solid var(--line);
      overflow: auto;
      padding: 14px;
    }
    .graphPane {
      min-width: 0;
      min-height: 0;
      display: grid;
      grid-template-rows: auto minmax(0, 1fr);
      background: #eef2f7;
    }
    .graphToolbar {
      min-height: 52px;
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 10px;
      align-items: center;
      padding: 10px 12px;
      border-bottom: 1px solid var(--line);
      background: rgba(251, 252, 254, .92);
    }
    .searchRow {
      display: grid;
      grid-template-columns: minmax(150px, 1fr) 130px;
      gap: 8px;
    }
    input, select {
      width: 100%;
      min-height: 32px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      color: var(--ink);
      padding: 6px 9px;
    }
    .toolButtons { display: flex; gap: 6px; align-items: center; }
    .iconButton {
      min-width: 32px;
      height: 32px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      color: var(--ink);
      cursor: pointer;
    }
    .iconButton:hover, .item:hover, .stepButton:hover {
      border-color: var(--line-strong);
      background: #f8fafc;
    }
    #graphCanvas {
      width: 100%;
      height: 100%;
      min-height: 360px;
      background:
        linear-gradient(rgba(23, 32, 47, .045) 1px, transparent 1px),
        linear-gradient(90deg, rgba(23, 32, 47, .045) 1px, transparent 1px),
        #eef2f7;
      background-size: 28px 28px;
    }
    .inspector {
      grid-column: 3;
      grid-row: 1 / 3;
      border-left: 1px solid var(--line);
      min-height: 0;
      overflow: auto;
      padding: 14px;
    }
    .diffDock {
      grid-column: 2;
      grid-row: 2;
      border-top: 1px solid var(--line);
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      min-width: 0;
      min-height: 0;
    }
    .diffPane {
      min-width: 0;
      min-height: 0;
      overflow: auto;
      padding: 12px;
      border-right: 1px solid var(--line);
    }
    .diffPane:last-child { border-right: 0; }
    h2 {
      margin: 18px 0 8px;
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: .08em;
    }
    h2:first-child { margin-top: 0; }
    h3 {
      margin: 0 0 8px;
      font-size: 15px;
      line-height: 1.25;
    }
    .small { color: var(--muted); font-size: 12px; line-height: 1.42; }
    .metricGrid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 7px;
      padding: 9px;
      background: #fff;
    }
    .metric strong {
      display: block;
      font-size: 18px;
      line-height: 1;
      margin-bottom: 4px;
    }
    .item, .stepButton {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: #fff;
      color: var(--ink);
      text-align: left;
      padding: 9px;
      margin-bottom: 7px;
      cursor: pointer;
    }
    .item.active, .stepButton.active {
      border-color: var(--accent);
      background: var(--accent-soft);
      box-shadow: inset 0 0 0 1px var(--accent);
    }
    .item.changed, .stepButton.changed { border-color: #dfbf79; background: var(--changed-soft); }
    .item.added, .stepButton.added { border-color: #9ad1bd; background: var(--add-soft); }
    .itemTitle {
      font-size: 12px;
      font-weight: 650;
      overflow-wrap: anywhere;
    }
    .itemMeta {
      color: var(--muted);
      font-size: 11px;
      margin-top: 3px;
      overflow-wrap: anywhere;
    }
    .pillRow { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 8px; }
    .pill {
      display: inline-flex;
      align-items: center;
      min-height: 20px;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 2px 7px;
      font-size: 11px;
      color: var(--muted);
      background: #fff;
    }
    .pill.added { color: var(--add); border-color: #a9d9c6; background: var(--add-soft); }
    .pill.changed { color: var(--changed); border-color: #e4c98f; background: var(--changed-soft); }
    .pill.removed { color: var(--removed); border-color: #dfaaa4; background: var(--removed-soft); }
    .kv {
      display: grid;
      grid-template-columns: 118px minmax(0, 1fr);
      gap: 6px 9px;
      font-size: 12px;
      line-height: 1.35;
    }
    .kv .key { color: var(--muted); }
    .kv .value { overflow-wrap: anywhere; }
    pre, code {
      font-family: var(--mono);
      font-size: 12px;
      letter-spacing: 0;
    }
    pre {
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      border: 1px solid var(--line);
      background: #f6f8fb;
      border-radius: 7px;
      padding: 10px;
    }
    .diffBlock {
      border: 1px solid var(--line);
      border-radius: 7px;
      overflow: hidden;
      background: #fff;
      margin-bottom: 10px;
    }
    .diffHead {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      border-bottom: 1px solid var(--line);
      background: #f8fafc;
      padding: 8px 10px;
      font-size: 12px;
      font-weight: 650;
    }
    .diffHunk {
      margin: 0;
      border: 0;
      border-radius: 0;
      background: #0f1724;
      color: #d7e1ef;
      max-height: 390px;
      overflow: auto;
    }
    .jsonPair {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 8px;
    }
    .jsonPair pre { max-height: 260px; overflow: auto; }
    .empty {
      border: 1px dashed var(--line-strong);
      color: var(--muted);
      border-radius: 7px;
      padding: 14px;
      background: #fff;
      font-size: 13px;
      line-height: 1.4;
    }
    .legend {
      display: grid;
      gap: 6px;
      font-size: 12px;
      color: var(--muted);
    }
    .legend span::before {
      content: "";
      display: inline-block;
      width: 10px;
      height: 10px;
      border-radius: 50%;
      margin-right: 7px;
      vertical-align: -1px;
      background: #adc0d5;
    }
    .legend .added::before { background: var(--add); }
    .legend .changed::before { background: var(--changed); }
    .legend .code::before { background: var(--code); }
    .legend .selected::before { background: var(--accent); }
    @media (max-width: 1120px) {
      .workbench {
        grid-template-columns: 230px minmax(0, 1fr);
        grid-template-rows: minmax(420px, 1fr) 360px auto;
      }
      .inspector {
        grid-column: 1 / 3;
        grid-row: 3;
        border-left: 0;
        border-top: 1px solid var(--line);
      }
      .diffDock {
        grid-column: 2;
        grid-row: 2;
      }
    }
  </style>
</head>
<body>
  <script>window.__WORKBENCH_PROJECTION__ = __WORKBENCH_DATA__;</script>
  <div class="shell">
    <header class="topbar">
      <div>
        <div class="eyebrow">IntentGraph Approval Workbench</div>
        <h1>Graph Delta Review: WindowsUtility Shell Workspace</h1>
        <div class="summary">Inspect graph nodes, graph edges, code diffs, changed element diffs, evidence, and authority before any approval gate.</div>
      </div>
      <div class="badges">
        <span class="badge ok">Local static</span>
        <span class="badge warn">No approval automation</span>
        <span class="badge">Cytoscape.js bundled</span>
      </div>
    </header>

    <section class="workbench">
      <nav class="rail">
        <h2>Delta Steps</h2>
        <div id="deltaSteps"></div>
        <h2>Graph Counts</h2>
        <div class="metricGrid">
          <div class="metric"><strong id="nodeCount">0</strong><span class="small">nodes</span></div>
          <div class="metric"><strong id="edgeCount">0</strong><span class="small">edges</span></div>
          <div class="metric"><strong id="codeDiffCount">0</strong><span class="small">code diffs</span></div>
          <div class="metric"><strong id="graphDiffCount">0</strong><span class="small">graph diffs</span></div>
        </div>
        <h2>Changed Elements</h2>
        <div id="changedElements"></div>
        <h2>Legend</h2>
        <div class="legend">
          <span class="added">Added node/edge</span>
          <span class="changed">Changed existing node/edge</span>
          <span class="code">Code element</span>
          <span class="selected">Current selection</span>
        </div>
      </nav>

      <main class="graphPane">
        <div class="graphToolbar">
          <div class="searchRow">
            <input id="searchBox" type="search" placeholder="Search nodes or edges">
            <select id="statusFilter" aria-label="Status filter">
              <option value="all">All statuses</option>
              <option value="added">Added</option>
              <option value="changed">Changed</option>
              <option value="unchanged">Unchanged</option>
            </select>
          </div>
          <div class="toolButtons">
            <button class="iconButton" id="zoomOut" title="Zoom out">-</button>
            <button class="iconButton" id="zoomIn" title="Zoom in">+</button>
            <button class="iconButton" id="fitGraph" title="Fit graph">Fit</button>
            <button class="iconButton" id="resetFocus" title="Clear selection">Clear</button>
          </div>
        </div>
        <div id="graphCanvas" aria-label="Graph delta canvas"></div>
      </main>

      <aside class="inspector">
        <div id="inspectorPanel"></div>
        <h2>Evidence / Authority</h2>
        <div id="evidenceAuthorityPanel"></div>
      </aside>

      <section class="diffDock">
        <div class="diffPane">
          <h2>Code Diff</h2>
          <div id="codeDiffPanel"></div>
        </div>
        <div class="diffPane">
          <h2>Graph Element Diff</h2>
          <div id="graphDiffPanel"></div>
        </div>
      </section>
    </section>
  </div>

  <script>
    const projection = window.__WORKBENCH_PROJECTION__;
    const graph = projection.graph || { nodes: [], edges: [] };
    const delta = projection.delta || {};
    const indexes = projection.indexes || {};
    const nodeById = new Map((graph.nodes || []).map((node) => [node.id, node]));
    const edgeById = new Map((graph.edges || []).map((edge) => [edge.id, edge]));
    const codeDiffById = new Map((delta.codeDiffs || []).map((diff) => [diff.id, diff]));
    const graphNodeDiffById = new Map((delta.graphNodeDiffs || []).map((diff) => [diff.id, diff]));
    const graphEdgeDiffById = new Map((delta.graphEdgeDiffs || []).map((diff) => [diff.id, diff]));
    const stepById = new Map((delta.steps || []).map((step) => [step.id, step]));
    let selected = null;
    let selectedStepId = null;

    const safe = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "\"": "&quot;",
      "'": "&#39;"
    })[char]);
    const json = (value) => safe(JSON.stringify(value ?? null, null, 2));
    const unique = (values) => Array.from(new Set((values || []).filter(Boolean)));
    const list = (value) => Array.isArray(value) ? value : [];
    const isCodeKind = (kind) => String(kind || "").startsWith("code");
    const diffForElement = (data, group) => group === "nodes"
      ? graphNodeDiffById.get(data.graphDiffRef)
      : graphEdgeDiffById.get(data.graphDiffRef);
    const codeDiffsFor = (data, group) => {
      const refs = new Set(list(data.codeDiffRefs));
      const graphDiff = diffForElement(data, group);
      list(graphDiff && graphDiff.affectedCodeDiffRefs).forEach((ref) => refs.add(ref));
      list(graphDiff && graphDiff.changedRefs).forEach((ref) => {
        if (codeDiffById.has(ref)) refs.add(ref);
      });
      return Array.from(refs).map((ref) => codeDiffById.get(ref)).filter(Boolean);
    };

    function statusClass(status) {
      return ["added", "changed", "removed"].includes(status) ? status : "";
    }

    function renderPills(values, className = "") {
      if (!values || values.length === 0) return "<span class=\"pill\">none</span>";
      return values.map((value) => `<span class="pill ${className}">${safe(value)}</span>`).join("");
    }

    function renderKv(rows) {
      return `<div class="kv">${rows.map(([key, value]) => `
        <div class="key">${safe(key)}</div>
        <div class="value">${Array.isArray(value) ? renderPills(value) : safe(value)}</div>
      `).join("")}</div>`;
    }

    function renderInspector(title, type, data) {
      const graphDiff = diffForElement(data, type === "node" ? "nodes" : "edges");
      const rows = [
        ["id", data.id],
        ["kind", data.kind],
        ["status", data.status],
        ["label", data.label || data.kind],
      ];
      if (type === "edge") {
        rows.push(["source", data.source], ["target", data.target], ["confidence", data.confidence || ""]);
      }
      const diffLine = graphDiff ? `<div class="pillRow"><span class="pill changed">graph diff: ${safe(graphDiff.id)}</span></div>` : "";
      document.getElementById("inspectorPanel").innerHTML = `
        <h2>${safe(type)} inspector</h2>
        <h3>${safe(title)}</h3>
        ${renderKv(rows)}
        ${diffLine}
        <h2>Source refs</h2>
        <div class="pillRow">${renderPills(list(data.sourceRefs))}</div>
        <h2>Delta refs</h2>
        <div class="pillRow">${renderPills(list(data.deltaRefs), statusClass(data.status))}</div>
        <h2>Attributes</h2>
        <pre>${json(data.attributes || {})}</pre>
      `;
      renderEvidenceAuthority(data, graphDiff);
      renderCodeDiffs(codeDiffsFor(data, type === "node" ? "nodes" : "edges"));
      renderGraphElementDiff(graphDiff, type);
    }

    function renderStepInspector(step) {
      document.getElementById("inspectorPanel").innerHTML = `
        <h2>delta step inspector</h2>
        <h3>${safe(step.label)}</h3>
        ${renderKv([
          ["id", step.id],
          ["status", step.status],
          ["affected nodes", list(step.affectedNodeIds)],
          ["affected edges", list(step.affectedEdgeIds)]
        ])}
        <h2>Graph diff refs</h2>
        <div class="pillRow">${renderPills([...list(step.graphNodeDiffRefs), ...list(step.graphEdgeDiffRefs)], "changed")}</div>
      `;
      renderEvidenceAuthority(step, null);
      renderCodeDiffs(list(step.codeDiffRefs).map((ref) => codeDiffById.get(ref)).filter(Boolean));
      const graphDiffs = [
        ...list(step.graphNodeDiffRefs).map((ref) => graphNodeDiffById.get(ref)).filter(Boolean),
        ...list(step.graphEdgeDiffRefs).map((ref) => graphEdgeDiffById.get(ref)).filter(Boolean)
      ];
      renderGraphDiffList(graphDiffs);
    }

    function renderEvidenceAuthority(data, diff) {
      const evidence = unique([...list(data.evidenceRefs), ...list(diff && diff.evidenceRefs)]);
      const authority = unique([...list(data.authorityRefs), ...list(diff && diff.authorityRefs)]);
      const history = unique([...list(data.historyRefs), ...list(diff && diff.historyRefs)]);
      document.getElementById("evidenceAuthorityPanel").innerHTML = `
        <div class="small">Evidence</div>
        <div class="pillRow">${renderPills(evidence)}</div>
        <div class="small" style="margin-top:12px">Authority</div>
        <div class="pillRow">${renderPills(authority)}</div>
        <div class="small" style="margin-top:12px">History</div>
        <div class="pillRow">${renderPills(history)}</div>
      `;
    }

    function renderCodeDiffs(diffs) {
      const panel = document.getElementById("codeDiffPanel");
      if (!diffs || diffs.length === 0) {
        panel.innerHTML = `<div class="empty">No code diff is linked to the current selection.</div>`;
        return;
      }
      panel.innerHTML = diffs.map((diff) => `
        <article class="diffBlock">
          <div class="diffHead">
            <span>${safe(diff.id)}</span>
            <span>${safe(diff.changeKind)}</span>
          </div>
          <div class="pillRow" style="padding:8px 10px">
            ${renderPills(list(diff.affectedNodeIds), "added")}
            ${renderPills(list(diff.affectedEdgeIds), "changed")}
          </div>
          ${(diff.diffHunks || []).map((hunk) => `<pre class="diffHunk">${safe(hunk)}</pre>`).join("")}
        </article>
      `).join("");
    }

    function renderGraphElementDiff(diff, type) {
      if (!diff) {
        document.getElementById("graphDiffPanel").innerHTML = `<div class="empty">No before/after graph diff is linked to the current selection.</div>`;
        return;
      }
      document.getElementById("graphDiffPanel").innerHTML = `
        <article class="diffBlock">
          <div class="diffHead">
            <span>${safe(diff.id)}</span>
            <span>${safe(type)} ${safe(diff.changeKind)}</span>
          </div>
          <div style="padding:10px">
            <div class="small">Changed fields</div>
            <div class="pillRow">${renderPills(list(diff.changedFields), "changed")}</div>
            <div class="jsonPair" style="margin-top:10px">
              <div>
                <div class="small">Before</div>
                <pre>${json(diff.beforePayload)}</pre>
              </div>
              <div>
                <div class="small">After</div>
                <pre>${json(diff.afterPayload)}</pre>
              </div>
            </div>
          </div>
        </article>
      `;
    }

    function renderGraphDiffList(diffs) {
      const panel = document.getElementById("graphDiffPanel");
      if (!diffs || diffs.length === 0) {
        panel.innerHTML = `<div class="empty">No changed node or edge diff is linked to this delta step.</div>`;
        return;
      }
      panel.innerHTML = diffs.map((diff) => `
        <article class="diffBlock">
          <div class="diffHead"><span>${safe(diff.id)}</span><span>${safe(diff.elementKind)} ${safe(diff.changeKind)}</span></div>
          <div style="padding:10px">
            <div class="small">Changed fields</div>
            <div class="pillRow">${renderPills(list(diff.changedFields), "changed")}</div>
            <div class="jsonPair" style="margin-top:10px">
              <div><div class="small">Before</div><pre>${json(diff.beforePayload)}</pre></div>
              <div><div class="small">After</div><pre>${json(diff.afterPayload)}</pre></div>
            </div>
          </div>
        </article>
      `).join("");
    }

    function graphElements() {
      const nodes = (graph.nodes || []).map((node) => ({
        data: {
          ...node,
          label: node.label || node.id,
          baseSize: isCodeKind(node.kind) ? 54 : 46,
          baseFont: 10
        },
        classes: `${node.status || "unchanged"} ${isCodeKind(node.kind) ? "code-node" : ""}`
      }));
      const edges = (graph.edges || []).map((edge) => ({
        data: {
          ...edge,
          label: edge.label || edge.kind,
          baseWidth: edge.status === "changed" ? 3 : 2
        },
        classes: `${edge.status || "unchanged"}`
      }));
      return [...nodes, ...edges];
    }

    const cy = cytoscape({
      container: document.getElementById("graphCanvas"),
      elements: graphElements(),
      userPanningEnabled: true,
      userZoomingEnabled: true,
      boxSelectionEnabled: false,
      wheelSensitivity: 0.18,
      minZoom: 0.35,
      maxZoom: 2.8,
      style: [
        {
          selector: "node",
          style: {
            "shape": "round-rectangle",
            "background-color": "#ffffff",
            "border-color": "#8795a8",
            "border-width": 2,
            "label": "data(label)",
            "font-family": "ui-sans-serif, system-ui",
            "font-size": 10,
            "color": "#17202f",
            "text-wrap": "wrap",
            "text-max-width": 110,
            "text-valign": "center",
            "text-halign": "center",
            "width": 48,
            "height": 38,
            "overlay-opacity": 0
          }
        },
        { selector: "node[kind = 'intent']", style: { "shape": "hexagon", "background-color": "#f7fbff", "border-color": "#2f63d6" } },
        { selector: "node[kind = 'evidence']", style: { "shape": "diamond", "background-color": "#f4fbf8", "border-color": "#16825d" } },
        { selector: "node[kind = 'package-artifact']", style: { "shape": "tag", "background-color": "#fbf7ff", "border-color": "#7c58a8" } },
        { selector: "node.code-node", style: { "shape": "round-rectangle", "background-color": "#ecf8fb", "border-color": "#145c72" } },
        { selector: "node.added", style: { "background-color": "#e8f7f1", "border-color": "#16825d", "border-width": 3 } },
        { selector: "node.changed", style: { "background-color": "#fff4db", "border-color": "#9a6500", "border-width": 3 } },
        {
          selector: "edge",
          style: {
            "curve-style": "bezier",
            "target-arrow-shape": "triangle",
            "target-arrow-color": "#7b8798",
            "line-color": "#aeb8c6",
            "width": 2,
            "label": "data(label)",
            "font-size": 9,
            "text-background-color": "#eef2f7",
            "text-background-opacity": 0.86,
            "text-background-padding": 2,
            "color": "#556174",
            "overlay-opacity": 0
          }
        },
        { selector: "edge.added", style: { "line-color": "#16825d", "target-arrow-color": "#16825d", "width": 3 } },
        { selector: "edge.changed", style: { "line-color": "#9a6500", "target-arrow-color": "#9a6500", "line-style": "dashed", "width": 3 } },
        { selector: ".faded", style: { "opacity": 0.18, "text-opacity": 0.06 } },
        { selector: ".step-focus", style: { "opacity": 1, "z-index": 40 } },
        { selector: ".selected", style: { "border-color": "#2f63d6", "line-color": "#2f63d6", "target-arrow-color": "#2f63d6", "border-width": 5, "width": 4, "z-index": 90 } },
        { selector: "edge.selected", style: { "width": 5 } },
        { selector: ".search-hit", style: { "border-color": "#111827", "line-color": "#111827", "target-arrow-color": "#111827", "z-index": 70 } }
      ],
      layout: {
        name: "cose",
        animate: false,
        fit: true,
        padding: 48,
        nodeRepulsion: 6800,
        idealEdgeLength: 115,
        edgeElasticity: 90,
        gravity: 0.26,
        numIter: 1400
      }
    });

    function applySemanticZoom() {
      const z = cy.zoom();
      const inv = 1 / Math.max(0.55, Math.min(1.9, z));
      cy.batch(() => {
        cy.nodes().forEach((node) => {
          const base = node.data("baseSize") || 46;
          node.style({
            width: Math.round(base * inv),
            height: Math.round((base * 0.78) * inv),
            "font-size": Math.max(7, Math.min(12, 10 * inv))
          });
        });
        cy.edges().forEach((edge) => {
          const base = edge.data("baseWidth") || 2;
          edge.style({
            width: Math.max(1.2, base * inv),
            "font-size": Math.max(7, Math.min(11, 9 * inv))
          });
        });
      });
    }

    function focusElements(nodeIds, edgeIds) {
      cy.elements().removeClass("faded step-focus selected");
      if ((!nodeIds || nodeIds.length === 0) && (!edgeIds || edgeIds.length === 0)) return;
      cy.elements().addClass("faded");
      let targets = cy.collection();
      (nodeIds || []).forEach((id) => { targets = targets.union(cy.getElementById(id)); });
      (edgeIds || []).forEach((id) => { targets = targets.union(cy.getElementById(id)); });
      targets.removeClass("faded").addClass("step-focus");
      targets.connectedEdges().removeClass("faded").addClass("step-focus");
      targets.connectedNodes().removeClass("faded").addClass("step-focus");
    }

    function selectGraphElement(group, id) {
      selected = { group, id };
      selectedStepId = null;
      document.querySelectorAll(".item, .stepButton").forEach((el) => el.classList.remove("active"));
      const ele = cy.getElementById(id);
      cy.elements().removeClass("selected");
      if (ele && ele.length) {
        ele.addClass("selected");
        if (group === "nodes") focusElements([id], []);
        if (group === "edges") focusElements([], [id]);
      }
      if (group === "nodes") {
        const data = nodeById.get(id);
        if (data) renderInspector(data.label || id, "node", data);
      } else {
        const data = edgeById.get(id);
        if (data) renderInspector(data.label || id, "edge", data);
      }
      const item = document.querySelector(`[data-element-id="${CSS.escape(id)}"]`);
      if (item) item.classList.add("active");
    }

    function selectDeltaStep(id) {
      const step = stepById.get(id);
      if (!step) return;
      selectedStepId = id;
      selected = null;
      document.querySelectorAll(".item, .stepButton").forEach((el) => el.classList.remove("active"));
      const button = document.querySelector(`[data-step-id="${CSS.escape(id)}"]`);
      if (button) button.classList.add("active");
      focusElements(list(step.affectedNodeIds), list(step.affectedEdgeIds));
      renderStepInspector(step);
    }

    function renderDeltaSteps() {
      const holder = document.getElementById("deltaSteps");
      holder.innerHTML = (delta.steps || []).map((step) => `
        <button class="stepButton ${statusClass(step.status)}" data-step-id="${safe(step.id)}">
          <div class="itemTitle">${safe(step.label)}</div>
          <div class="itemMeta">${safe(step.status)} | ${list(step.affectedNodeIds).length} nodes | ${list(step.affectedEdgeIds).length} edges</div>
        </button>
      `).join("");
      holder.querySelectorAll("[data-step-id]").forEach((button) => {
        button.addEventListener("click", () => selectDeltaStep(button.getAttribute("data-step-id")));
      });
    }

    function renderChangedElements() {
      const changedNodes = (graph.nodes || []).filter((node) => node.status === "changed" || node.status === "added");
      const changedEdges = (graph.edges || []).filter((edge) => edge.status === "changed" || edge.status === "added");
      const entries = [
        ...changedNodes.map((node) => ({ group: "nodes", id: node.id, label: node.label, status: node.status, kind: node.kind })),
        ...changedEdges.map((edge) => ({ group: "edges", id: edge.id, label: `${edge.source} -> ${edge.target}`, status: edge.status, kind: edge.kind }))
      ];
      document.getElementById("changedElements").innerHTML = entries.map((entry) => `
        <button class="item ${statusClass(entry.status)}" data-element-group="${entry.group}" data-element-id="${safe(entry.id)}">
          <div class="itemTitle">${safe(entry.label || entry.id)}</div>
          <div class="itemMeta">${safe(entry.status)} | ${safe(entry.kind)}</div>
        </button>
      `).join("");
      document.querySelectorAll("[data-element-id]").forEach((button) => {
        button.addEventListener("click", () => selectGraphElement(button.getAttribute("data-element-group"), button.getAttribute("data-element-id")));
      });
    }

    function applySearchAndFilter() {
      const query = document.getElementById("searchBox").value.trim().toLowerCase();
      const status = document.getElementById("statusFilter").value;
      cy.elements().removeClass("search-hit");
      cy.elements().forEach((ele) => {
        const data = ele.data();
        const haystack = `${data.id} ${data.label || ""} ${data.kind || ""} ${data.source || ""} ${data.target || ""}`.toLowerCase();
        const statusOk = status === "all" || data.status === status;
        const queryOk = !query || haystack.includes(query);
        ele.style("display", statusOk && queryOk ? "element" : "none");
        if (query && queryOk) ele.addClass("search-hit");
      });
    }

    function resetFocus() {
      selected = null;
      selectedStepId = null;
      cy.elements().removeClass("faded step-focus selected search-hit");
      document.querySelectorAll(".item, .stepButton").forEach((el) => el.classList.remove("active"));
      renderInitialInspector();
    }

    function renderInitialInspector() {
      document.getElementById("inspectorPanel").innerHTML = `
        <h2>selection</h2>
        <h3>Choose a graph node, graph edge, or delta step.</h3>
        <div class="empty">Changed existing graph nodes and edges show before/after graph diffs. Code nodes and code-affecting steps show source code diffs.</div>
      `;
      document.getElementById("evidenceAuthorityPanel").innerHTML = `<div class="empty">Evidence, authority, and history refs appear here for the selected item.</div>`;
      document.getElementById("codeDiffPanel").innerHTML = `<div class="empty">Select a code node or code-affecting delta step to inspect code changes.</div>`;
      document.getElementById("graphDiffPanel").innerHTML = `<div class="empty">Select a changed node or changed edge to inspect graph before/after payloads.</div>`;
    }

    cy.on("tap", "node", (event) => selectGraphElement("nodes", event.target.id()));
    cy.on("tap", "edge", (event) => selectGraphElement("edges", event.target.id()));
    cy.on("tap", (event) => { if (event.target === cy) resetFocus(); });
    cy.on("zoom", applySemanticZoom);
    document.getElementById("zoomIn").addEventListener("click", () => cy.zoom({ level: cy.zoom() * 1.18, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } }));
    document.getElementById("zoomOut").addEventListener("click", () => cy.zoom({ level: cy.zoom() / 1.18, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } }));
    document.getElementById("fitGraph").addEventListener("click", () => cy.fit(undefined, 42));
    document.getElementById("resetFocus").addEventListener("click", resetFocus);
    document.getElementById("searchBox").addEventListener("input", applySearchAndFilter);
    document.getElementById("statusFilter").addEventListener("change", applySearchAndFilter);

    document.getElementById("nodeCount").textContent = String((graph.nodes || []).length);
    document.getElementById("edgeCount").textContent = String((graph.edges || []).length);
    document.getElementById("codeDiffCount").textContent = String((delta.codeDiffs || []).length);
    document.getElementById("graphDiffCount").textContent = String((delta.graphNodeDiffs || []).length + (delta.graphEdgeDiffs || []).length);
    renderDeltaSteps();
    renderChangedElements();
    renderInitialInspector();
    applySemanticZoom();
    setTimeout(() => cy.fit(undefined, 44), 0);
  </script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit a static graph-delta approval workbench HTML prototype.")
    parser.add_argument("--projection", default=DEFAULT_PROJECTION, type=Path)
    parser.add_argument("--out-dir", default=DEFAULT_OUTPUT_DIR, type=Path)
    parser.add_argument("--cytoscape-js", default=DEFAULT_CYTOSCAPE_JS, type=Path)
    parser.add_argument("--cytoscape-license", default=DEFAULT_CYTOSCAPE_LICENSE, type=Path)
    parser.add_argument("--roadmap-report", default=Path("generated/roadmap/p8.60-static-graph-delta-approval-workbench-prototype-report.json"), type=Path)
    args = parser.parse_args()

    source_projection = read_json(args.projection)
    workbench_projection = build_workbench_projection(source_projection, args.projection)
    output_dir = args.out_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    projection_path = output_dir / "projection.json"
    index_path = output_dir / "index.html"
    cytoscape_target = output_dir / "assets" / "cytoscape.min.js"
    license_target = output_dir / "assets" / "cytoscape-license.txt"
    manifest_path = output_dir / "manifest.json"
    validation_path = output_dir / "validation-report.json"

    write_json(projection_path, workbench_projection)
    index_path.write_text(render_html(workbench_projection), encoding="utf-8")
    copy_asset(args.cytoscape_js, cytoscape_target)
    copy_asset(args.cytoscape_license, license_target)

    manifest = build_manifest(output_dir, projection_path, args.projection)
    write_json(manifest_path, manifest)
    validation = validate_output(output_dir, workbench_projection)
    write_json(validation_path, validation)
    roadmap_report = build_roadmap_report(output_dir, validation, manifest)
    write_json(args.roadmap_report, roadmap_report)
    return 0 if validation.get("result") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
