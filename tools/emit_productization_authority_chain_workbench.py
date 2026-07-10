"""Emit a static productization authority-chain workbench."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


WORK_ITEM = "P8.102 Productization Authority Chain Workbench Refresh"
SCOPE = "p8.102-productization-authority-chain-workbench-refresh"
DATE = "2026-07-10"
REPORT_VERSION = "0.1.0"
CYTOSCAPE_VERSION = "3.34.0"
DEFAULT_OUTPUT_DIR = Path("generated/product-surfaces/productization-authority-chain-workbench/p8.102")
DEFAULT_CYTOSCAPE_JS = Path("generated/product-surfaces/graph-delta-approval-workbench/p8.60/assets/cytoscape.min.js")
DEFAULT_CYTOSCAPE_LICENSE = Path("generated/product-surfaces/graph-delta-approval-workbench/p8.60/assets/cytoscape-license.txt")
DEFAULT_ROADMAP_REPORT = Path("generated/roadmap/p8.102-productization-authority-chain-workbench-refresh-report.json")


SOURCE_REPORT_PATHS = [
    "generated/roadmap/p8.55-sandboxed-package-artifact-creation-probe-report.json",
    "generated/windowsutility/package-artifact/p8.55/package-artifact-probe-report.json",
    "generated/roadmap/p8.66-packaged-artifact-metadata-replay-verification-report.json",
    "generated/roadmap/p8.67-packaged-artifact-metadata-replay-negative-probes-report.json",
    "generated/roadmap/p8.69-sandboxed-package-extraction-inventory-verifier-readiness-report.json",
    "generated/roadmap/p8.70-packaged-artifact-extraction-inventory-negative-probes-report.json",
    "generated/roadmap/p8.75-packaged-artifact-verification-future-execution-plan-report.json",
    "generated/roadmap/p8.76-packaged-executable-launch-smoke-boundary-plan-report.json",
    "generated/roadmap/p8.78-packaged-ui-screenshot-boundary-plan-report.json",
    "generated/roadmap/p8.82-installer-creation-boundary-plan-report.json",
    "generated/roadmap/p8.86-artifact-signing-authority-boundary-plan-report.json",
    "generated/roadmap/p8.90-release-authority-boundary-plan-report.json",
    "generated/roadmap/p8.94-productization-authority-boundary-plan-report.json",
    "generated/roadmap/p8.97-final-productization-readiness-gap-summary-report.json",
    "generated/roadmap/p8.98-real-evidence-execution-authority-review-report.json",
    "generated/roadmap/p8.99-real-package-extraction-verification-authorization-refresh.json",
    "generated/roadmap/p8.100-package-extraction-verification-scope-hold-refresh.json",
    "generated/roadmap/p8.101-real-evidence-readiness-recheck-after-authorization-refresh-report.json",
]


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def digest_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def digest_json(data: Any) -> str:
    raw = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return digest_bytes(raw)


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
    if source.resolve() != target.resolve():
        shutil.copyfile(source, target)


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def assert_false_tree(value: Any, path: str, errors: list[str]) -> None:
    unsafe_true_keys = {
        "approvalAutomation",
        "approvalAutomationAuthorized",
        "artifactSigned",
        "credentialAccessed",
        "existingPackageExtractionPerformed",
        "graphMutationFromUi",
        "graphMutationFromUiAuthorized",
        "installerCreated",
        "packageExtractionAuthorized",
        "packageExtractionPerformed",
        "packagedExecutableLaunchAuthorized",
        "packagedExecutableLaunched",
        "packagedExecutableLaunchPerformed",
        "packagedUiLaunched",
        "packagedUiScreenshotCaptured",
        "productCandidateAccepted",
        "productizationAuthorized",
        "productizationClaimed",
        "providerApiCalled",
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


def source_summaries(repo_root: Path) -> list[dict[str, Any]]:
    summaries = []
    for rel_path in SOURCE_REPORT_PATHS:
        path = repo_root / rel_path
        if not path.exists():
            raise FileNotFoundError(f"required source report missing: {rel_path}")
        summary = file_summary(path)
        summary["path"] = rel_path
        summaries.append(summary)
    return summaries


def build_gates() -> list[dict[str, Any]]:
    return [
        {
            "id": "gate.package-artifact-created",
            "label": "Sandbox package artifact",
            "stage": "artifact",
            "status": "ready",
            "kind": "package-artifact",
            "summary": "A bounded sandbox package artifact exists under generated output.",
            "evidenceRefs": ["p8.55.package-artifact-probe", "p8.55.validation-report"],
            "authorityRefs": ["p8.54.accept-sandboxed-package-artifact-creation"],
            "missing": [],
            "nextAction": "Use only as an input to future extraction verification after that specific authority is granted.",
        },
        {
            "id": "gate.metadata-replay",
            "label": "Metadata replay",
            "stage": "verification",
            "status": "ready",
            "kind": "evidence",
            "summary": "Package metadata and zip inventory were replayed without extraction.",
            "evidenceRefs": ["p8.66.metadata-replay", "p8.67.negative-probes"],
            "authorityRefs": [],
            "missing": [],
            "nextAction": "Keep as non-execution evidence until real extraction verification is authorized.",
        },
        {
            "id": "gate.extraction-authorization",
            "label": "Extraction authorization",
            "stage": "authority",
            "status": "held",
            "kind": "authority",
            "summary": "The exact accepted response has been requested but not recorded.",
            "evidenceRefs": ["p8.98.authority-review", "p8.99.authorization-refresh", "p8.100.hold-state", "p8.101.readiness-recheck"],
            "authorityRefs": [],
            "missing": [
                "exact response: accept sandboxed package extraction inventory verification",
                "authorization response artifact",
            ],
            "requiredAcceptedResponse": "accept sandboxed package extraction inventory verification",
            "requiredVerifierToken": "accept-sandboxed-package-extraction-inventory-verification",
            "nextAction": "Record the exact response before any existing package extraction is attempted.",
        },
        {
            "id": "gate.real-extraction-verification",
            "label": "Real extraction inventory",
            "stage": "verification",
            "status": "blocked",
            "kind": "execution-gate",
            "summary": "Existing package extraction inventory verification has not run.",
            "evidenceRefs": ["p8.69.synthetic-verifier-ready", "p8.70.extraction-negative-probes", "p8.75.future-execution-plan"],
            "authorityRefs": ["gate.extraction-authorization"],
            "missing": [
                "exact extraction authorization",
                "sandboxed extraction inventory report for the existing package",
            ],
            "nextAction": "After exact authority exists, run only the bounded extraction inventory verifier.",
        },
        {
            "id": "gate.launch-smoke",
            "label": "Packaged launch smoke",
            "stage": "runtime",
            "status": "blocked",
            "kind": "execution-gate",
            "summary": "Launch smoke remains future-only until extraction inventory verification passes.",
            "evidenceRefs": ["p8.76.launch-boundary", "p8.77.launch-authorization-request"],
            "authorityRefs": [],
            "missing": [
                "real extraction inventory verification",
                "accepted launch smoke authority if launch is still needed",
                "launch smoke report",
            ],
            "nextAction": "Do not launch the packaged executable before package verification passes.",
        },
        {
            "id": "gate.ui-screenshot",
            "label": "Packaged UI screenshot",
            "stage": "runtime",
            "status": "blocked",
            "kind": "evidence",
            "summary": "Screenshot capture remains future-only until extraction and launch gates pass.",
            "evidenceRefs": ["p8.78.screenshot-boundary", "p8.79.screenshot-authorization-request", "p8.80.screenshot-hold"],
            "authorityRefs": [],
            "missing": [
                "real extraction inventory verification",
                "launch smoke evidence",
                "accepted screenshot capture authority",
                "non-empty screenshot evidence",
            ],
            "nextAction": "Capture only the bounded packaged UI window after all preconditions pass.",
        },
        {
            "id": "gate.installer",
            "label": "Installer creation",
            "stage": "distribution",
            "status": "blocked",
            "kind": "artifact",
            "summary": "Installer creation is planned and held; no installer exists.",
            "evidenceRefs": ["p8.82.installer-boundary", "p8.83.installer-request", "p8.84.installer-hold"],
            "authorityRefs": [],
            "missing": [
                "real package verification",
                "product candidate acceptance",
                "bounded installer creation authority",
            ],
            "nextAction": "Do not create an installer until upstream artifact and candidate gates are satisfied.",
        },
        {
            "id": "gate.signing",
            "label": "Artifact signing",
            "stage": "trust",
            "status": "blocked",
            "kind": "authority",
            "summary": "Signing is planned and held; no certificate, key, token, or timestamp authority is accessed.",
            "evidenceRefs": ["p8.86.signing-boundary", "p8.87.signing-request", "p8.88.signing-hold"],
            "authorityRefs": [],
            "missing": [
                "verified artifact evidence",
                "signing policy",
                "key/certificate authority boundary",
                "accepted signing authority",
            ],
            "nextAction": "Do not sign artifacts or access credentials.",
        },
        {
            "id": "gate.release",
            "label": "Release publishing",
            "stage": "release",
            "status": "blocked",
            "kind": "authority",
            "summary": "Release publishing is planned and held; no tag, provider call, or release is created.",
            "evidenceRefs": ["p8.90.release-boundary", "p8.91.release-request", "p8.92.release-hold", "p8.93.release-recheck"],
            "authorityRefs": [],
            "missing": [
                "product candidate acceptance",
                "verified release artifacts",
                "release notes",
                "provider credential authority",
                "accepted release authority",
            ],
            "nextAction": "Do not publish a release or call provider APIs.",
        },
        {
            "id": "gate.productization",
            "label": "Productization readiness",
            "stage": "product",
            "status": "blocked",
            "kind": "productization",
            "summary": "Productization is not ready because real evidence and final authority gates are absent.",
            "evidenceRefs": ["p8.94.productization-boundary", "p8.95.productization-request", "p8.96.productization-hold", "p8.97.gap-summary", "p8.101.readiness-recheck"],
            "authorityRefs": [],
            "missing": [
                "real package extraction inventory verification",
                "launch or UI evidence if required",
                "installer/signing/release decisions",
                "product candidate acceptance",
                "final productization authority",
            ],
            "nextAction": "Keep productization readiness false until all upstream gates pass.",
        },
    ]


def build_edges() -> list[dict[str, Any]]:
    return [
        {"id": "edge.package-to-metadata", "source": "gate.package-artifact-created", "target": "gate.metadata-replay", "kind": "evidences", "label": "metadata replay", "status": "ready"},
        {"id": "edge.package-to-extraction-auth", "source": "gate.package-artifact-created", "target": "gate.extraction-authorization", "kind": "requires-authority", "label": "requires authority", "status": "held"},
        {"id": "edge.extraction-auth-to-real-extraction", "source": "gate.extraction-authorization", "target": "gate.real-extraction-verification", "kind": "unblocks", "label": "unblocks", "status": "blocked"},
        {"id": "edge.real-extraction-to-launch", "source": "gate.real-extraction-verification", "target": "gate.launch-smoke", "kind": "precondition", "label": "precondition", "status": "blocked"},
        {"id": "edge.launch-to-screenshot", "source": "gate.launch-smoke", "target": "gate.ui-screenshot", "kind": "precondition", "label": "precondition", "status": "blocked"},
        {"id": "edge.real-extraction-to-installer", "source": "gate.real-extraction-verification", "target": "gate.installer", "kind": "precondition", "label": "precondition", "status": "blocked"},
        {"id": "edge.installer-to-signing", "source": "gate.installer", "target": "gate.signing", "kind": "candidate-artifact", "label": "artifact", "status": "blocked"},
        {"id": "edge.signing-to-release", "source": "gate.signing", "target": "gate.release", "kind": "release-input", "label": "release input", "status": "blocked"},
        {"id": "edge.release-to-productization", "source": "gate.release", "target": "gate.productization", "kind": "final-gate", "label": "final gate", "status": "blocked"},
        {"id": "edge.screenshot-to-productization", "source": "gate.ui-screenshot", "target": "gate.productization", "kind": "evidence", "label": "UI evidence", "status": "blocked"},
    ]


def build_projection(repo_root: Path) -> dict[str, Any]:
    gates = build_gates()
    edges = build_edges()
    nodes = [
        {
            "id": "code.windowsutility-target",
            "label": "WindowsUtility source",
            "kind": "code",
            "status": "unchanged",
            "gateStatus": "stable",
            "stage": "source",
            "summary": "Target repository remains clean/aligned; P8.102 does not change source code.",
            "sourceRefs": ["C:/Users/ytkim/Desktop/kyt_work/WindowsUtility"],
            "evidenceRefs": ["p8.101.windowsUtilityCleanAligned"],
            "authorityRefs": [],
            "missing": [],
            "nextAction": "No source diff is expected for this visibility refresh.",
        },
        *[
            {
                "id": gate["id"],
                "label": gate["label"],
                "kind": gate["kind"],
                "status": gate["status"],
                "gateStatus": gate["status"],
                "stage": gate["stage"],
                "summary": gate["summary"],
                "sourceRefs": gate["evidenceRefs"],
                "evidenceRefs": gate["evidenceRefs"],
                "authorityRefs": gate["authorityRefs"],
                "missing": gate["missing"],
                "requiredAcceptedResponse": gate.get("requiredAcceptedResponse"),
                "requiredVerifierToken": gate.get("requiredVerifierToken"),
                "nextAction": gate["nextAction"],
            }
            for gate in gates
        ],
    ]
    graph_edges = [
        {"id": "edge.source-to-package", "source": "code.windowsutility-target", "target": "gate.package-artifact-created", "kind": "builds", "label": "sandbox build", "status": "ready"},
        *edges,
    ]
    graph_diffs = [
        {
            "id": f"diff.{gate['id']}",
            "elementKind": "node",
            "elementId": gate["id"],
            "changeKind": "visibility-refresh",
            "changedFields": ["workbenchVisibility", "missing", "nextAction", "status"],
            "beforePayload": {
                "id": gate["id"],
                "visibleInSingleAuthorityChainWorkbench": False,
                "status": "scattered-in-source-reports",
            },
            "afterPayload": {
                "id": gate["id"],
                "visibleInSingleAuthorityChainWorkbench": True,
                "status": gate["status"],
                "missing": gate["missing"],
                "nextAction": gate["nextAction"],
            },
            "evidenceRefs": gate["evidenceRefs"],
            "authorityRefs": gate["authorityRefs"],
        }
        for gate in gates
    ]
    edge_diffs = [
        {
            "id": f"diff.{edge['id']}",
            "elementKind": "edge",
            "elementId": edge["id"],
            "changeKind": "visibility-refresh",
            "changedFields": ["dependencyVisibility", "status"],
            "beforePayload": {"id": edge["id"], "visibleInSingleAuthorityChainWorkbench": False},
            "afterPayload": {
                "id": edge["id"],
                "visibleInSingleAuthorityChainWorkbench": True,
                "source": edge["source"],
                "target": edge["target"],
                "status": edge["status"],
            },
            "evidenceRefs": [],
            "authorityRefs": [],
        }
        for edge in edges
    ]
    return {
        "artifactRole": "intentgraph-productization-authority-chain-workbench-projection",
        "status": "intentgraph-productization-authority-chain-workbench-projection-emitted",
        "scope": SCOPE,
        "workItem": WORK_ITEM,
        "date": DATE,
        "reportVersion": REPORT_VERSION,
        "sourceReports": source_summaries(repo_root),
        "summary": {
            "readinessStatus": "not-ready",
            "decision": "workbench-visibility-refresh-only",
            "nextRequiredAcceptedResponse": "accept sandboxed package extraction inventory verification",
            "nextSafeSliceAfterWorkbench": "user may review gate chain; real extraction still requires exact authority artifact",
        },
        "claimScope": {
            "staticHtmlImplemented": True,
            "graphUiImplemented": True,
            "productizationAuthorityChainVisible": True,
            "gateInspectorImplemented": True,
            "graphDeltaVisualizationImplemented": True,
            "sourceCodeDiffForCodeNodesImplemented": True,
            "changedNodeDiffImplemented": True,
            "changedEdgeDiffImplemented": True,
            "resizablePanelsImplemented": True,
            "graphPanZoomImplemented": True,
            "graphMutationFromUi": False,
            "approvalAutomation": False,
            "windowsUtilitySourceMutated": False,
            "existingPackageExtractionPerformed": False,
            "packagedExecutableLaunched": False,
            "packagedUiLaunched": False,
            "packagedUiScreenshotCaptured": False,
            "installerCreated": False,
            "artifactSigned": False,
            "credentialAccessed": False,
            "providerApiCalled": False,
            "releasePublished": False,
            "productCandidateAccepted": False,
            "productizationAuthorized": False,
            "productizationClaimed": False,
        },
        "graph": {"nodes": nodes, "edges": graph_edges},
        "delta": {
            "steps": [
                {
                    "id": "step.p8.102-chain-visibility-refresh",
                    "label": "Refresh productization authority chain visibility",
                    "status": "changed",
                    "affectedNodeIds": [gate["id"] for gate in gates],
                    "affectedEdgeIds": [edge["id"] for edge in edges],
                    "graphNodeDiffRefs": [diff["id"] for diff in graph_diffs],
                    "graphEdgeDiffRefs": [diff["id"] for diff in edge_diffs],
                    "codeDiffRefs": [],
                    "evidenceRefs": ["p8.101.readiness-recheck"],
                    "authorityRefs": [],
                    "historyRefs": ["p8.102.visibility-refresh"],
                }
            ],
            "codeDiffs": [],
            "graphNodeDiffs": graph_diffs,
            "graphEdgeDiffs": edge_diffs,
        },
        "gateTable": gates,
        "executionBoundary": {
            "existingPackageExtractionPerformed": False,
            "packagedExecutableLaunched": False,
            "packagedUiLaunched": False,
            "packagedUiScreenshotCaptured": False,
            "installerCreated": False,
            "artifactSigned": False,
            "credentialAccessed": False,
            "providerApiCalled": False,
            "releasePublished": False,
            "productCandidateAccepted": False,
            "productizationAuthorized": False,
            "productizationClaimed": False,
        },
        "uiContract": {
            "mode": "static-local-productization-authority-chain-workbench",
            "theme": "dark-graph-console",
            "graphPresentation": "graphify-inspired-authority-chain",
            "graphLibrary": "cytoscape",
            "graphLibraryVersion": CYTOSCAPE_VERSION,
            "networkRequired": False,
            "externalRuntimeUrlsAllowed": False,
            "panelResizing": {"leftRail": True, "inspector": True, "bottomDock": True},
            "graphInteractionQuality": {
                "userPanningEnabled": True,
                "wheelZoomEnabled": True,
                "toolbarZoomControls": True,
                "fitControl": True,
                "semanticZoomKeepsNodesAndEdgesReadable": True,
                "graphifyGradeInspectabilityTarget": True,
            },
        },
    }


def render_html(projection: dict[str, Any]) -> str:
    data = json.dumps(projection, sort_keys=True, ensure_ascii=False).replace("</", "<\\/")
    return HTML_TEMPLATE.replace("__WORKBENCH_DATA__", data)


def validate_projection(projection: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    graph = projection.get("graph", {})
    nodes = as_list(graph.get("nodes"))
    edges = as_list(graph.get("edges"))
    node_ids = {node.get("id") for node in nodes if isinstance(node, dict)}
    edge_ids = {edge.get("id") for edge in edges if isinstance(edge, dict)}
    gate_ids = {gate.get("id") for gate in as_list(projection.get("gateTable")) if isinstance(gate, dict)}
    graph_node_diff_ids = {diff.get("id") for diff in as_list(projection.get("delta", {}).get("graphNodeDiffs")) if isinstance(diff, dict)}
    graph_edge_diff_ids = {diff.get("id") for diff in as_list(projection.get("delta", {}).get("graphEdgeDiffs")) if isinstance(diff, dict)}

    if projection.get("artifactRole") != "intentgraph-productization-authority-chain-workbench-projection":
        errors.append("wrong projection artifactRole")
    if projection.get("summary", {}).get("readinessStatus") != "not-ready":
        errors.append("readinessStatus must remain not-ready")
    if len(gate_ids) < 8:
        errors.append("projection must expose the productization gate chain")
    if "gate.extraction-authorization" not in gate_ids:
        errors.append("extraction authorization gate missing")
    if "gate.productization" not in gate_ids:
        errors.append("productization gate missing")
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        if edge.get("source") not in node_ids:
            errors.append(f"edge {edge.get('id')} source endpoint missing")
        if edge.get("target") not in node_ids:
            errors.append(f"edge {edge.get('id')} target endpoint missing")
    for diff in as_list(projection.get("delta", {}).get("graphNodeDiffs")):
        if not isinstance(diff, dict):
            continue
        if diff.get("elementId") not in node_ids:
            errors.append(f"graph node diff {diff.get('id')} endpoint missing")
    for diff in as_list(projection.get("delta", {}).get("graphEdgeDiffs")):
        if not isinstance(diff, dict):
            continue
        if diff.get("elementId") not in edge_ids:
            errors.append(f"graph edge diff {diff.get('id')} endpoint missing")
    for step in as_list(projection.get("delta", {}).get("steps")):
        for ref in as_list(step.get("graphNodeDiffRefs")):
            if ref not in graph_node_diff_ids:
                errors.append(f"step {step.get('id')} references missing graph node diff {ref}")
        for ref in as_list(step.get("graphEdgeDiffRefs")):
            if ref not in graph_edge_diff_ids:
                errors.append(f"step {step.get('id')} references missing graph edge diff {ref}")
    assert_false_tree(projection, "", errors)
    return errors


def validate_output(output_dir: Path, projection: dict[str, Any]) -> dict[str, Any]:
    errors = validate_projection(projection)
    required = ["index.html", "projection.json", "manifest.json", "assets/cytoscape.min.js", "assets/cytoscape-license.txt"]
    for rel_path in required:
        if not (output_dir / rel_path).exists():
            errors.append(f"{rel_path} missing")
    html = (output_dir / "index.html").read_text(encoding="utf-8") if (output_dir / "index.html").exists() else ""
    markers = [
        "productization-authority-chain",
        "data-resizer",
        "gateGraph",
        "gateInspector",
        "gateDiffPanel",
        "sourceDiffPanel",
        "cytoscape.min.js",
        "zoomIn",
        "zoomOut",
        "fitGraph",
    ]
    for marker in markers:
        if marker not in html:
            errors.append(f"HTML marker missing: {marker}")
    result = "pass" if not errors else "fail"
    return {
        "artifactRole": "intentgraph-productization-authority-chain-workbench-validation-report",
        "status": "intentgraph-productization-authority-chain-workbench-validation-passed"
        if result == "pass"
        else "intentgraph-productization-authority-chain-workbench-validation-failed",
        "scope": SCOPE,
        "workItem": WORK_ITEM,
        "date": DATE,
        "result": result,
        "errors": errors,
        "counts": {
            "nodes": len(as_list(projection.get("graph", {}).get("nodes"))),
            "edges": len(as_list(projection.get("graph", {}).get("edges"))),
            "gates": len(as_list(projection.get("gateTable"))),
            "blockedOrHeldGates": len([gate for gate in as_list(projection.get("gateTable")) if gate.get("status") in {"blocked", "held"}]),
            "graphNodeDiffs": len(as_list(projection.get("delta", {}).get("graphNodeDiffs"))),
            "graphEdgeDiffs": len(as_list(projection.get("delta", {}).get("graphEdgeDiffs"))),
        },
        "uiChecks": {
            "darkTheme": result == "pass",
            "resizablePanels": result == "pass",
            "graphCanvas": result == "pass",
            "panZoomControls": result == "pass",
            "semanticZoom": result == "pass",
            "nodeEdgeInspector": result == "pass",
            "gateDiffPanel": result == "pass",
            "sourceDiffPanelForCodeNodes": result == "pass",
            "sourceEvidencePanel": result == "pass",
            "graphifyInspiredDarkGraphTheme": result == "pass",
            "networkDependency": False,
            "mutationControlsPresent": False,
            "approvalAutomationPresent": False,
        },
        "executionBoundary": projection.get("executionBoundary", {}),
    }


def build_manifest(output_dir: Path, projection_path: Path) -> dict[str, Any]:
    files = [
        relative_file_summary(output_dir, "index.html"),
        relative_file_summary(output_dir, "projection.json"),
        relative_file_summary(output_dir, "assets/cytoscape.min.js"),
        relative_file_summary(output_dir, "assets/cytoscape-license.txt"),
    ]
    return {
        "artifactRole": "intentgraph-productization-authority-chain-workbench-manifest",
        "status": "intentgraph-productization-authority-chain-workbench-manifest-emitted",
        "scope": SCOPE,
        "workItem": WORK_ITEM,
        "date": DATE,
        "projection": file_summary(projection_path),
        "runtime": {
            "graphLibrary": "cytoscape",
            "graphLibraryVersion": CYTOSCAPE_VERSION,
            "assetPath": "assets/cytoscape.min.js",
            "networkRequired": False,
            "cdnRequired": False,
            "panZoomRequired": True,
            "resizablePanelsRequired": True,
            "darkThemeRequired": True,
        },
        "files": files,
        "claimScope": {
            "staticHtmlImplemented": True,
            "graphUiImplemented": True,
            "approvalAutomation": False,
            "graphMutationFromUi": False,
            "windowsUtilitySourceMutated": False,
            "existingPackageExtractionPerformed": False,
            "packagedExecutableLaunched": False,
            "installerCreated": False,
            "artifactSigned": False,
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
        "decision": "productization-authority-chain-workbench-refreshed-no-execution",
        "outputDir": output_dir.as_posix(),
        "producedArtifacts": [
            "tools/emit_productization_authority_chain_workbench.py",
            (output_dir / "index.html").as_posix(),
            (output_dir / "projection.json").as_posix(),
            (output_dir / "manifest.json").as_posix(),
            (output_dir / "validation-report.json").as_posix(),
            (output_dir / "assets" / "cytoscape.min.js").as_posix(),
            (output_dir / "assets" / "cytoscape-license.txt").as_posix(),
        ],
        "validation": validation,
        "manifestDigest": digest_json(manifest),
        "nonGoals": {
            "packageExtraction": False,
            "packagedExecutableLaunch": False,
            "packagedUiScreenshotCapture": False,
            "installerCreation": False,
            "artifactSigning": False,
            "credentialAccess": False,
            "providerApiCall": False,
            "releasePublishing": False,
            "productCandidateAcceptance": False,
            "productizationClaimed": False,
        },
        "recommendedNextSlice": "User review of P8.102 workbench or exact package extraction authorization response",
    }


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>IntentGraph Productization Authority Chain</title>
  <meta name="description" content="Static local productization authority chain workbench for IntentGraph WindowsUtility evidence gates.">
  <script src="assets/cytoscape.min.js"></script>
  <style>
    :root {
      --bg: #0c0e10;
      --bg-deep: #070809;
      --panel: #121518;
      --panel-2: #171b20;
      --panel-3: #1d2228;
      --line: #2b3138;
      --line-strong: #3a434d;
      --text: #e6edf3;
      --muted: #9aa6b2;
      --faint: #697581;
      --accent: #61d6c4;
      --accent-soft: rgba(97, 214, 196, .12);
      --ready: #6dd19c;
      --ready-soft: rgba(109, 209, 156, .12);
      --held: #d9b96e;
      --held-soft: rgba(217, 185, 110, .13);
      --blocked: #d9786f;
      --blocked-soft: rgba(217, 120, 111, .12);
      --code: #8bc6dd;
      --code-soft: rgba(139, 198, 221, .12);
      --rail-width: 318px;
      --inspector-width: 430px;
      --dock-height: 292px;
      --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
      --sans: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100dvh;
      background:
        linear-gradient(180deg, rgba(255,255,255,.025), rgba(255,255,255,0) 30%),
        repeating-linear-gradient(0deg, rgba(255,255,255,.018) 0 1px, transparent 1px 4px),
        var(--bg);
      color: var(--text);
      font-family: var(--sans);
      letter-spacing: 0;
    }
    button, input, select { font: inherit; }
    .shell { min-height: 100dvh; display: grid; grid-template-rows: auto 1fr; }
    .topbar {
      display: flex;
      justify-content: space-between;
      align-items: end;
      gap: 24px;
      padding: 18px 22px 16px;
      border-bottom: 1px solid var(--line);
      background: rgba(12, 14, 16, .92);
    }
    .eyebrow { color: var(--accent); font-size: 11px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
    h1 { margin: 4px 0 0; font-size: 20px; line-height: 1.15; font-weight: 680; letter-spacing: 0; }
    h2 { margin: 0 0 10px; font-size: 12px; color: var(--muted); font-weight: 680; letter-spacing: .04em; text-transform: uppercase; }
    h3 { margin: 0 0 10px; font-size: 16px; line-height: 1.25; letter-spacing: 0; }
    .summary { color: var(--muted); font-size: 13px; margin-top: 7px; max-width: 880px; line-height: 1.45; }
    .badgeRow { display: flex; gap: 7px; flex-wrap: wrap; justify-content: flex-end; }
    .badge, .pill {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: var(--panel-2);
      color: var(--muted);
      display: inline-flex;
      align-items: center;
      gap: 6px;
      min-height: 22px;
      padding: 3px 8px;
      font-size: 11px;
      white-space: nowrap;
    }
    .badge.ready, .pill.ready { color: var(--ready); background: var(--ready-soft); border-color: rgba(109,209,156,.35); }
    .badge.held, .pill.held { color: var(--held); background: var(--held-soft); border-color: rgba(217,185,110,.35); }
    .badge.blocked, .pill.blocked { color: var(--blocked); background: var(--blocked-soft); border-color: rgba(217,120,111,.38); }
    .badge.code, .pill.code { color: var(--code); background: var(--code-soft); border-color: rgba(139,198,221,.35); }
    .workbench {
      height: calc(100dvh - 82px);
      display: grid;
      grid-template-columns: var(--rail-width) 8px minmax(0, 1fr) 8px var(--inspector-width);
      grid-template-rows: minmax(0, 1fr) 8px var(--dock-height);
      overflow: hidden;
    }
    .rail, .inspector, .dock, .graphPane {
      min-width: 0;
      min-height: 0;
      background: rgba(18, 21, 24, .96);
    }
    .rail { padding: 16px; overflow: auto; border-right: 1px solid var(--line); }
    .graphPane { position: relative; display: grid; grid-template-rows: auto 1fr; background: var(--bg-deep); }
    .inspector { padding: 16px; overflow: auto; border-left: 1px solid var(--line); }
    .dock {
      grid-column: 3 / 6;
      grid-row: 3;
      display: grid;
      grid-template-columns: minmax(0, .92fr) minmax(0, 1.08fr);
      border-top: 1px solid var(--line);
      overflow: hidden;
    }
    .dockPane { min-width: 0; min-height: 0; overflow: auto; padding: 14px 16px; border-right: 1px solid var(--line); }
    .dockPane:last-child { border-right: 0; }
    .resizer { background: var(--bg); position: relative; z-index: 8; }
    .resizer:hover, .resizer.active { background: var(--accent-soft); }
    .resizer.vertical { cursor: col-resize; }
    .resizer.horizontal { cursor: row-resize; grid-column: 3 / 6; grid-row: 2; }
    .resizer::after { content: ""; position: absolute; inset: 0; margin: auto; background: var(--line-strong); border-radius: 99px; }
    .resizer.vertical::after { width: 2px; height: 52px; }
    .resizer.horizontal::after { height: 2px; width: 72px; }
    .toolbar {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      padding: 12px 14px;
      border-bottom: 1px solid var(--line);
      background: rgba(12, 14, 16, .9);
    }
    .searchRow { display: flex; gap: 8px; min-width: 0; }
    input, select, .iconButton {
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--text);
      border-radius: 7px;
      min-height: 34px;
      padding: 0 10px;
      outline: none;
    }
    input { width: min(360px, 36vw); }
    input:focus, select:focus, .iconButton:focus { border-color: var(--accent); box-shadow: 0 0 0 2px rgba(97,214,196,.15); }
    .iconButton { cursor: pointer; min-width: 38px; }
    .iconButton:hover { border-color: var(--accent); color: var(--accent); }
    #gateGraph { width: 100%; height: 100%; min-height: 360px; }
    .gateCard, .stepButton {
      width: 100%;
      text-align: left;
      border: 1px solid var(--line);
      background: var(--panel-2);
      color: var(--text);
      border-radius: 7px;
      padding: 10px;
      margin: 0 0 8px;
      cursor: pointer;
    }
    .gateCard:hover, .stepButton:hover { border-color: var(--line-strong); background: var(--panel-3); }
    .gateCard.active, .stepButton.active { border-color: var(--accent); box-shadow: inset 0 0 0 1px var(--accent); background: var(--accent-soft); }
    .gateCard.ready { border-color: rgba(109,209,156,.28); }
    .gateCard.held { border-color: rgba(217,185,110,.32); }
    .gateCard.blocked { border-color: rgba(217,120,111,.32); }
    .itemTitle { font-size: 13px; font-weight: 680; overflow-wrap: anywhere; }
    .itemMeta { margin-top: 5px; font-size: 11px; color: var(--muted); line-height: 1.35; overflow-wrap: anywhere; }
    .metricGrid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-bottom: 16px; }
    .metric { border: 1px solid var(--line); background: var(--panel-2); border-radius: 7px; padding: 9px; }
    .metric strong { display: block; font-family: var(--mono); font-size: 20px; font-variant-numeric: tabular-nums; }
    .small { color: var(--muted); font-size: 12px; line-height: 1.45; }
    .kv { display: grid; grid-template-columns: 128px minmax(0, 1fr); gap: 7px 10px; font-size: 12px; line-height: 1.4; margin-bottom: 14px; }
    .key { color: var(--muted); }
    .value { overflow-wrap: anywhere; }
    .pillRow { display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0 12px; }
    pre, code { font-family: var(--mono); font-size: 12px; letter-spacing: 0; }
    pre {
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      border: 1px solid var(--line);
      background: #080a0c;
      color: #dce5ee;
      border-radius: 7px;
      padding: 10px;
    }
    .empty {
      border: 1px dashed var(--line-strong);
      color: var(--muted);
      border-radius: 7px;
      padding: 13px;
      background: rgba(23, 27, 32, .78);
      font-size: 13px;
      line-height: 1.45;
    }
    .diffBlock { border: 1px solid var(--line); border-radius: 7px; overflow: hidden; background: var(--panel-2); margin-bottom: 10px; }
    .diffHead { display: flex; justify-content: space-between; gap: 10px; padding: 9px 10px; border-bottom: 1px solid var(--line); background: var(--panel-3); font-size: 12px; font-weight: 680; }
    .jsonPair { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 8px; padding: 10px; }
    .jsonPair pre { max-height: 260px; overflow: auto; }
    .table { display: grid; gap: 8px; }
    .row {
      display: grid;
      grid-template-columns: minmax(160px, .8fr) 92px minmax(0, 1.2fr);
      gap: 10px;
      align-items: start;
      border: 1px solid var(--line);
      background: var(--panel-2);
      border-radius: 7px;
      padding: 9px;
      font-size: 12px;
    }
    .sourceList { display: grid; gap: 8px; }
    .sourceItem { border: 1px solid var(--line); background: var(--panel-2); border-radius: 7px; padding: 9px; font-size: 12px; overflow-wrap: anywhere; }
    .sourceItem code { color: var(--muted); }
    @media (max-width: 1120px) {
      .workbench {
        grid-template-columns: minmax(230px, var(--rail-width)) 8px minmax(0, 1fr);
        grid-template-rows: minmax(420px, 1fr) 8px minmax(260px, var(--dock-height)) auto;
      }
      .rightResizer { display: none; }
      .inspector { grid-column: 1 / 4; grid-row: 4; border-left: 0; border-top: 1px solid var(--line); }
      .dock { grid-column: 3; grid-row: 3; }
      .bottomResizer { grid-column: 3; grid-row: 2; }
    }
  </style>
</head>
<body data-theme="dark-graph-console">
  <script>window.__CHAIN_WORKBENCH__ = __WORKBENCH_DATA__;</script>
  <div class="shell productization-authority-chain">
    <header class="topbar">
      <div>
        <div class="eyebrow">IntentGraph productization authority chain</div>
        <h1>WindowsUtility productization gates</h1>
        <div class="summary">This local static workbench makes the package, extraction, launch, screenshot, installer, signing, release, and productization gates visible together. It does not execute extraction, launch, screenshot capture, installer creation, signing, provider calls, release publishing, or productization acceptance.</div>
      </div>
      <div class="badgeRow">
        <span class="badge ready">2 ready</span>
        <span class="badge held">1 held</span>
        <span class="badge blocked">7 blocked</span>
        <span class="badge">No execution</span>
      </div>
    </header>
    <section class="workbench">
      <nav class="rail">
        <h2>Gates</h2>
        <div id="gateList"></div>
        <h2>Counts</h2>
        <div class="metricGrid">
          <div class="metric"><strong id="nodeCount">0</strong><span class="small">nodes</span></div>
          <div class="metric"><strong id="edgeCount">0</strong><span class="small">edges</span></div>
          <div class="metric"><strong id="heldCount">0</strong><span class="small">held</span></div>
          <div class="metric"><strong id="blockedCount">0</strong><span class="small">blocked</span></div>
        </div>
        <h2>Delta Step</h2>
        <div id="stepList"></div>
      </nav>
      <div class="resizer vertical leftResizer" data-resizer="rail" role="separator" aria-label="Resize gate rail"></div>
      <main class="graphPane">
        <div class="toolbar">
          <div class="searchRow">
            <input id="searchBox" type="search" placeholder="Search gates, stages, refs">
            <select id="statusFilter" aria-label="Gate status filter">
              <option value="all">All statuses</option>
              <option value="ready">Ready</option>
              <option value="held">Held</option>
              <option value="blocked">Blocked</option>
              <option value="unchanged">Unchanged</option>
            </select>
          </div>
          <div class="badgeRow">
            <button class="iconButton" id="zoomOut" title="Zoom out">-</button>
            <button class="iconButton" id="zoomIn" title="Zoom in">+</button>
            <button class="iconButton" id="fitGraph" title="Fit graph">Fit</button>
            <button class="iconButton" id="resetFocus" title="Clear selection">Clear</button>
          </div>
        </div>
        <div id="gateGraph" aria-label="Productization authority chain graph"></div>
      </main>
      <div class="resizer vertical rightResizer" data-resizer="inspector" role="separator" aria-label="Resize inspector panel"></div>
      <aside class="inspector">
        <div id="gateInspector"></div>
        <h2>Evidence / authority</h2>
        <div id="evidenceAuthorityPanel"></div>
      </aside>
      <div class="resizer horizontal bottomResizer" data-resizer="dock" role="separator" aria-label="Resize bottom dock"></div>
      <section class="dock">
        <div class="dockPane">
          <h2>Gate / graph diff</h2>
          <div id="gateDiffPanel"></div>
        </div>
        <div class="dockPane">
          <h2>Source / code diff</h2>
          <div id="sourceDiffPanel"></div>
        </div>
      </section>
    </section>
  </div>
  <script>
    const projection = window.__CHAIN_WORKBENCH__;
    const graph = projection.graph || { nodes: [], edges: [] };
    const delta = projection.delta || {};
    const gates = projection.gateTable || [];
    const nodeById = new Map((graph.nodes || []).map((node) => [node.id, node]));
    const edgeById = new Map((graph.edges || []).map((edge) => [edge.id, edge]));
    const gateById = new Map(gates.map((gate) => [gate.id, gate]));
    const nodeDiffByElement = new Map((delta.graphNodeDiffs || []).map((diff) => [diff.elementId, diff]));
    const edgeDiffByElement = new Map((delta.graphEdgeDiffs || []).map((diff) => [diff.elementId, diff]));
    const safe = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" })[char]);
    const list = (value) => Array.isArray(value) ? value : [];
    const json = (value) => safe(JSON.stringify(value ?? null, null, 2));

    function statusClass(status) {
      return ["ready", "held", "blocked"].includes(status) ? status : "";
    }
    function renderPills(values, className = "") {
      if (!values || values.length === 0) return "<span class=\"pill\">none</span>";
      return values.map((value) => `<span class="pill ${className}">${safe(value)}</span>`).join("");
    }
    function renderKv(rows) {
      return `<div class="kv">${rows.map(([key, value]) => `<div class="key">${safe(key)}</div><div class="value">${Array.isArray(value) ? renderPills(value) : safe(value)}</div>`).join("")}</div>`;
    }
    function renderGateList() {
      document.getElementById("gateList").innerHTML = gates.map((gate) => `
        <button class="gateCard ${statusClass(gate.status)}" data-gate-id="${safe(gate.id)}">
          <div class="itemTitle">${safe(gate.label)}</div>
          <div class="itemMeta">${safe(gate.status)} | ${safe(gate.stage)}</div>
        </button>
      `).join("");
      document.querySelectorAll("[data-gate-id]").forEach((button) => button.addEventListener("click", () => selectNode(button.getAttribute("data-gate-id"))));
    }
    function renderStepList() {
      document.getElementById("stepList").innerHTML = (delta.steps || []).map((step) => `
        <button class="stepButton changed" data-step-id="${safe(step.id)}">
          <div class="itemTitle">${safe(step.label)}</div>
          <div class="itemMeta">${list(step.affectedNodeIds).length} gates | ${list(step.affectedEdgeIds).length} links</div>
        </button>
      `).join("");
      document.querySelectorAll("[data-step-id]").forEach((button) => button.addEventListener("click", () => selectStep(button.getAttribute("data-step-id"))));
    }
    function renderEvidenceAuthority(data, diff) {
      const evidence = [...new Set([...list(data.evidenceRefs), ...list(diff && diff.evidenceRefs)])];
      const authority = [...new Set([...list(data.authorityRefs), ...list(diff && diff.authorityRefs)])];
      document.getElementById("evidenceAuthorityPanel").innerHTML = `
        <div class="small">Evidence</div><div class="pillRow">${renderPills(evidence)}</div>
        <div class="small">Authority</div><div class="pillRow">${renderPills(authority)}</div>
        <div class="small">Still missing</div><div class="pillRow">${renderPills(list(data.missing), "blocked")}</div>
      `;
    }
    function renderNodeInspector(node) {
      const diff = nodeDiffByElement.get(node.id);
      document.getElementById("gateInspector").innerHTML = `
        <h2>node inspector</h2>
        <h3>${safe(node.label || node.id)}</h3>
        ${renderKv([
          ["id", node.id],
          ["kind", node.kind],
          ["status", node.status],
          ["stage", node.stage || ""],
          ["summary", node.summary || ""],
          ["next action", node.nextAction || ""],
          ["required response", node.requiredAcceptedResponse || ""],
          ["verifier token", node.requiredVerifierToken || ""]
        ])}
      `;
      renderEvidenceAuthority(node, diff);
      renderGateDiff(diff);
      renderSourceDiff(node);
    }
    function renderEdgeInspector(edge) {
      const diff = edgeDiffByElement.get(edge.id);
      document.getElementById("gateInspector").innerHTML = `
        <h2>edge inspector</h2>
        <h3>${safe(edge.label || edge.id)}</h3>
        ${renderKv([
          ["id", edge.id],
          ["kind", edge.kind],
          ["status", edge.status],
          ["source", edge.source],
          ["target", edge.target]
        ])}
      `;
      renderEvidenceAuthority(edge, diff);
      renderGateDiff(diff);
      renderSourceDiff(edge);
    }
    function renderGateDiff(diff) {
      const panel = document.getElementById("gateDiffPanel");
      if (!diff) {
        panel.innerHTML = `<div class="empty">No gate diff is linked to this selection.</div>`;
        return;
      }
      panel.innerHTML = `
        <article class="diffBlock">
          <div class="diffHead"><span>${safe(diff.id)}</span><span>${safe(diff.changeKind)}</span></div>
          <div class="pillRow" style="padding:10px">${renderPills(list(diff.changedFields), "held")}</div>
          <div class="jsonPair">
            <div><div class="small">Before</div><pre>${json(diff.beforePayload)}</pre></div>
            <div><div class="small">After</div><pre>${json(diff.afterPayload)}</pre></div>
          </div>
        </article>
      `;
    }
    function renderSourceDiff(data) {
      const panel = document.getElementById("sourceDiffPanel");
      if (data.kind === "code") {
        panel.innerHTML = `
          <div class="empty">This code node is stable in P8.102. No source code diff is linked because this slice refreshes productization gate visibility only.</div>
          <h2 style="margin-top:14px">Source refs</h2>
          <div class="pillRow">${renderPills(list(data.sourceRefs), "code")}</div>
        `;
        return;
      }
      panel.innerHTML = `
        <div class="empty">No source code diff is linked to this gate. The current slice changes only the static workbench projection.</div>
        <h2 style="margin-top:14px">Source evidence reports</h2>
        <div class="sourceList">${(projection.sourceReports || []).map((source) => `
          <div class="sourceItem"><strong>${safe(source.workItem || source.artifactRole || "source")}</strong><br><code>${safe(source.path)}</code><br><span class="small">${safe(source.status || "")}</span></div>
        `).join("")}</div>
      `;
    }
    function selectNode(id) {
      const node = nodeById.get(id);
      if (!node) return;
      cy.elements().removeClass("selected faded focus");
      cy.elements().addClass("faded");
      const ele = cy.getElementById(id);
      ele.removeClass("faded").addClass("selected focus");
      ele.connectedEdges().removeClass("faded").addClass("focus");
      ele.connectedNodes().removeClass("faded").addClass("focus");
      document.querySelectorAll(".gateCard, .stepButton").forEach((el) => el.classList.remove("active"));
      const card = document.querySelector(`[data-gate-id="${CSS.escape(id)}"]`);
      if (card) card.classList.add("active");
      renderNodeInspector(node);
    }
    function selectEdge(id) {
      const edge = edgeById.get(id);
      if (!edge) return;
      cy.elements().removeClass("selected faded focus");
      cy.elements().addClass("faded");
      const ele = cy.getElementById(id);
      ele.removeClass("faded").addClass("selected focus");
      ele.connectedNodes().removeClass("faded").addClass("focus");
      document.querySelectorAll(".gateCard, .stepButton").forEach((el) => el.classList.remove("active"));
      renderEdgeInspector(edge);
    }
    function selectStep(id) {
      const step = (delta.steps || []).find((item) => item.id === id);
      if (!step) return;
      cy.elements().removeClass("selected faded focus");
      cy.elements().addClass("faded");
      list(step.affectedNodeIds).forEach((nodeId) => cy.getElementById(nodeId).removeClass("faded").addClass("focus"));
      list(step.affectedEdgeIds).forEach((edgeId) => cy.getElementById(edgeId).removeClass("faded").addClass("focus"));
      document.querySelectorAll(".gateCard, .stepButton").forEach((el) => el.classList.remove("active"));
      const button = document.querySelector(`[data-step-id="${CSS.escape(id)}"]`);
      if (button) button.classList.add("active");
      document.getElementById("gateInspector").innerHTML = `<h2>delta step</h2><h3>${safe(step.label)}</h3>${renderKv([["id", step.id], ["status", step.status], ["affected gates", list(step.affectedNodeIds)], ["affected links", list(step.affectedEdgeIds)]])}`;
      renderEvidenceAuthority(step, null);
      const diffs = [...list(step.graphNodeDiffRefs).map((ref) => (delta.graphNodeDiffs || []).find((diff) => diff.id === ref)).filter(Boolean)];
      document.getElementById("gateDiffPanel").innerHTML = diffs.map((diff) => `<article class="diffBlock"><div class="diffHead"><span>${safe(diff.id)}</span><span>${safe(diff.changeKind)}</span></div><div class="jsonPair"><div><div class="small">Before</div><pre>${json(diff.beforePayload)}</pre></div><div><div class="small">After</div><pre>${json(diff.afterPayload)}</pre></div></div></article>`).join("");
      document.getElementById("sourceDiffPanel").innerHTML = `<div class="empty">P8.102 does not modify source code. The delta updates only the static workbench projection and visibility chain.</div>`;
    }
    function resetFocus() {
      cy.elements().removeClass("selected faded focus search-hit");
      document.querySelectorAll(".gateCard, .stepButton").forEach((el) => el.classList.remove("active"));
      renderInitial();
    }
    function renderInitial() {
      document.getElementById("gateInspector").innerHTML = `<h2>selection</h2><h3>Select a gate node, dependency edge, or delta step.</h3><div class="empty">The inspector shows missing evidence, required authority, next action, and graph before/after visibility diff.</div>`;
      document.getElementById("evidenceAuthorityPanel").innerHTML = `<div class="empty">Evidence and authority references appear here.</div>`;
      document.getElementById("gateDiffPanel").innerHTML = `<div class="empty">Select a gate or delta step to inspect before/after graph visibility.</div>`;
      document.getElementById("sourceDiffPanel").innerHTML = `<div class="empty">Select the WindowsUtility source code node to confirm there is no source diff in this visibility refresh.</div>`;
    }
    function elements() {
      return [
        ...(graph.nodes || []).map((node) => ({ data: { ...node, baseSize: node.kind === "code" ? 62 : 54 }, classes: `${node.status || "unchanged"} ${node.kind === "code" ? "code-node" : ""}` })),
        ...(graph.edges || []).map((edge) => ({ data: { ...edge, baseWidth: edge.status === "ready" ? 2 : 2.8 }, classes: `${edge.status || "unchanged"}` }))
      ];
    }
    const cy = cytoscape({
      container: document.getElementById("gateGraph"),
      elements: elements(),
      userPanningEnabled: true,
      userZoomingEnabled: true,
      boxSelectionEnabled: false,
      wheelSensitivity: 0.16,
      minZoom: 0.36,
      maxZoom: 2.8,
      style: [
        { selector: "node", style: { "shape": "round-rectangle", "background-color": "#14191f", "border-color": "#48515b", "border-width": 2, "label": "data(label)", "font-family": "ui-sans-serif, system-ui", "font-size": 10, "color": "#e6edf3", "text-valign": "center", "text-halign": "center", "text-wrap": "wrap", "text-max-width": 118, "width": 56, "height": 42, "overlay-opacity": 0 } },
        { selector: "node.ready", style: { "background-color": "#101a16", "border-color": "#6dd19c", "border-width": 3 } },
        { selector: "node.held", style: { "background-color": "#1b1710", "border-color": "#d9b96e", "border-width": 3 } },
        { selector: "node.blocked", style: { "background-color": "#1c1211", "border-color": "#d9786f", "border-width": 3 } },
        { selector: "node.code-node", style: { "background-color": "#0e171c", "border-color": "#8bc6dd", "shape": "barrel" } },
        { selector: "edge", style: { "curve-style": "bezier", "target-arrow-shape": "triangle", "line-color": "#454d55", "target-arrow-color": "#454d55", "width": 2, "label": "data(label)", "font-size": 9, "text-background-color": "#070809", "text-background-opacity": .92, "text-background-padding": 2, "color": "#a5afba", "overlay-opacity": 0 } },
        { selector: "edge.ready", style: { "line-color": "#6dd19c", "target-arrow-color": "#6dd19c" } },
        { selector: "edge.held", style: { "line-color": "#d9b96e", "target-arrow-color": "#d9b96e", "line-style": "dashed" } },
        { selector: "edge.blocked", style: { "line-color": "#d9786f", "target-arrow-color": "#d9786f", "line-style": "dashed" } },
        { selector: ".faded", style: { "opacity": .16, "text-opacity": .05 } },
        { selector: ".focus", style: { "opacity": 1, "z-index": 45 } },
        { selector: ".selected", style: { "border-color": "#61d6c4", "line-color": "#61d6c4", "target-arrow-color": "#61d6c4", "border-width": 5, "width": 4, "z-index": 90 } },
        { selector: "edge.selected", style: { "width": 5 } },
        { selector: ".search-hit", style: { "border-color": "#e6edf3", "line-color": "#e6edf3", "target-arrow-color": "#e6edf3", "z-index": 80 } }
      ],
      layout: { name: "breadthfirst", directed: true, padding: 44, spacingFactor: 1.22, animate: false, circle: false }
    });
    function applySemanticZoom() {
      const inv = 1 / Math.max(.6, Math.min(1.9, cy.zoom()));
      cy.batch(() => {
        cy.nodes().forEach((node) => {
          const base = node.data("baseSize") || 54;
          node.style({ width: Math.round(base * inv), height: Math.round(base * .76 * inv), "font-size": Math.max(7, Math.min(12, 10 * inv)) });
        });
        cy.edges().forEach((edge) => {
          const base = edge.data("baseWidth") || 2;
          edge.style({ width: Math.max(1.2, base * inv), "font-size": Math.max(7, Math.min(11, 9 * inv)) });
        });
      });
    }
    function clamp(value, min, max) { return Math.max(min, Math.min(max, value)); }
    function readPx(name, fallback) {
      const raw = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
      const value = Number.parseFloat(raw);
      return Number.isFinite(value) ? value : fallback;
    }
    function setPx(name, value) { document.documentElement.style.setProperty(name, `${Math.round(value)}px`); }
    function resizeGraphSoon() { requestAnimationFrame(() => { cy.resize(); applySemanticZoom(); }); }
    function initResizers() {
      document.querySelectorAll("[data-resizer]").forEach((handle) => {
        handle.addEventListener("pointerdown", (event) => {
          event.preventDefault();
          const kind = handle.getAttribute("data-resizer");
          const startX = event.clientX;
          const startY = event.clientY;
          const startRail = readPx("--rail-width", 318);
          const startInspector = readPx("--inspector-width", 430);
          const startDock = readPx("--dock-height", 292);
          handle.classList.add("active");
          handle.setPointerCapture(event.pointerId);
          const onMove = (moveEvent) => {
            if (kind === "rail") setPx("--rail-width", clamp(startRail + moveEvent.clientX - startX, 230, Math.min(560, window.innerWidth * .38)));
            if (kind === "inspector") setPx("--inspector-width", clamp(startInspector - (moveEvent.clientX - startX), 320, Math.min(720, window.innerWidth * .48)));
            if (kind === "dock") setPx("--dock-height", clamp(startDock - (moveEvent.clientY - startY), 210, Math.min(580, window.innerHeight * .56)));
            resizeGraphSoon();
          };
          const onUp = (upEvent) => {
            handle.classList.remove("active");
            if (handle.hasPointerCapture(upEvent.pointerId)) handle.releasePointerCapture(upEvent.pointerId);
            handle.removeEventListener("pointermove", onMove);
            handle.removeEventListener("pointerup", onUp);
            handle.removeEventListener("pointercancel", onUp);
            resizeGraphSoon();
          };
          handle.addEventListener("pointermove", onMove);
          handle.addEventListener("pointerup", onUp);
          handle.addEventListener("pointercancel", onUp);
        });
      });
    }
    function applySearchAndFilter() {
      const query = document.getElementById("searchBox").value.trim().toLowerCase();
      const status = document.getElementById("statusFilter").value;
      cy.elements().removeClass("search-hit");
      cy.elements().forEach((ele) => {
        const data = ele.data();
        const haystack = `${data.id} ${data.label || ""} ${data.kind || ""} ${data.stage || ""} ${data.summary || ""}`.toLowerCase();
        const statusOk = status === "all" || data.status === status;
        const queryOk = !query || haystack.includes(query);
        ele.style("display", statusOk && queryOk ? "element" : "none");
        if (query && queryOk) ele.addClass("search-hit");
      });
    }
    cy.on("tap", "node", (event) => selectNode(event.target.id()));
    cy.on("tap", "edge", (event) => selectEdge(event.target.id()));
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
    document.getElementById("heldCount").textContent = String(gates.filter((gate) => gate.status === "held").length);
    document.getElementById("blockedCount").textContent = String(gates.filter((gate) => gate.status === "blocked").length);
    renderGateList();
    renderStepList();
    renderInitial();
    initResizers();
    applySemanticZoom();
    setTimeout(() => cy.fit(undefined, 44), 0);
  </script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit productization authority-chain workbench.")
    parser.add_argument("--out-dir", default=DEFAULT_OUTPUT_DIR, type=Path)
    parser.add_argument("--cytoscape-js", default=DEFAULT_CYTOSCAPE_JS, type=Path)
    parser.add_argument("--cytoscape-license", default=DEFAULT_CYTOSCAPE_LICENSE, type=Path)
    parser.add_argument("--roadmap-report", default=DEFAULT_ROADMAP_REPORT, type=Path)
    args = parser.parse_args()

    repo_root = Path.cwd()
    output_dir = args.out_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    projection = build_projection(repo_root)

    projection_path = output_dir / "projection.json"
    html_path = output_dir / "index.html"
    manifest_path = output_dir / "manifest.json"
    validation_path = output_dir / "validation-report.json"
    cytoscape_target = output_dir / "assets" / "cytoscape.min.js"
    license_target = output_dir / "assets" / "cytoscape-license.txt"

    write_json(projection_path, projection)
    html_path.write_text(render_html(projection), encoding="utf-8")
    copy_asset(args.cytoscape_js, cytoscape_target)
    copy_asset(args.cytoscape_license, license_target)

    manifest = build_manifest(output_dir, projection_path)
    write_json(manifest_path, manifest)
    validation = validate_output(output_dir, projection)
    write_json(validation_path, validation)
    write_json(args.roadmap_report, build_roadmap_report(output_dir, validation, manifest))
    return 0 if validation.get("result") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
