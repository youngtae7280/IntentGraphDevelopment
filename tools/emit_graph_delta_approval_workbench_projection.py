"""Emit a graph/delta approval workbench projection for WindowsUtility."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPORT_VERSION = "0.1.0"
WORK_ITEM = "P8.59 Graph Delta Approval Workbench Projection Schema"
SCOPE = "p8.59-graph-delta-approval-workbench-projection-schema"
DATE = "2026-07-10"


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


def artifact_summary(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    summary: dict[str, Any] = {
        "path": path.as_posix(),
        "sha256": digest_bytes(raw),
        "byteLength": len(raw),
    }
    if path.suffix.lower() == ".json":
        data = read_json(path)
        for key in ["artifactRole", "status", "scope", "workItem", "decision", "result"]:
            if key in data:
                summary[key] = data[key]
    return summary


def make_edge(edge_id: str, kind: str, source: str, target: str, **extra: Any) -> dict[str, Any]:
    edge: dict[str, Any] = {
        "id": edge_id,
        "kind": kind,
        "source": source,
        "target": target,
        "label": kind,
        "status": extra.pop("status", "unchanged"),
        "confidence": extra.pop("confidence", "extracted"),
        "provenance": extra.pop("provenance", "generated-from-p8.59-projection-schema"),
        "attributes": extra.pop("attributes", {}),
        "evidenceRefs": extra.pop("evidenceRefs", []),
        "authorityRefs": extra.pop("authorityRefs", []),
        "historyRefs": extra.pop("historyRefs", []),
        "deltaRefs": extra.pop("deltaRefs", []),
        "graphDiffRef": extra.pop("graphDiffRef", None),
    }
    edge.update(extra)
    return edge


def make_node(node_id: str, kind: str, label: str, **extra: Any) -> dict[str, Any]:
    node: dict[str, Any] = {
        "id": node_id,
        "kind": kind,
        "label": label,
        "status": extra.pop("status", "unchanged"),
        "attributes": extra.pop("attributes", {}),
        "sourceRefs": extra.pop("sourceRefs", []),
        "codeDiffRefs": extra.pop("codeDiffRefs", []),
        "evidenceRefs": extra.pop("evidenceRefs", []),
        "authorityRefs": extra.pop("authorityRefs", []),
        "historyRefs": extra.pop("historyRefs", []),
        "deltaRefs": extra.pop("deltaRefs", []),
        "graphDiffRef": extra.pop("graphDiffRef", None),
    }
    node.update(extra)
    return node


def plus_hunk_from_file(path: Path) -> str:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    header = f"@@ -0,0 +1,{len(lines)} @@"
    return "\n".join([header, *[f"+{line}" for line in lines]])


def build_projection(args: argparse.Namespace) -> dict[str, Any]:
    requirement = read_json(args.requirement)
    boundary = read_json(args.boundary)
    proposal = read_json(args.proposal)
    application = read_json(args.application)
    package_summary = read_json(args.package_summary)
    applied_file = args.applied_file
    code_diff_hunk = plus_hunk_from_file(applied_file)

    source_artifacts = [
        artifact_summary(args.requirement),
        artifact_summary(args.boundary),
        artifact_summary(args.proposal),
        artifact_summary(args.application),
        artifact_summary(args.package_summary),
        artifact_summary(applied_file),
    ]

    nodes = [
        make_node(
            "intent.shell-workspace",
            "intent",
            "WindowsUtility shell/workspace review intent",
            sourceRefs=[args.proposal.as_posix(), args.application.as_posix()],
            evidenceRefs=["evidence.p8.44-build", "evidence.p8.44-final-preflight"],
            authorityRefs=["authority.p8.44-user-source-edit"],
            historyRefs=["history.p8.44-source-application"],
        ),
        make_node(
            "code.surface.windowsutility-shell",
            "code-surface",
            "WindowsUtility shell/workspace code surface",
            sourceRefs=[
                "src/WindowsUtility.App/WindowsUtility.App.csproj",
                "src/WindowsUtility.Shell/WindowsUtility.Shell.csproj",
            ],
            evidenceRefs=["evidence.p8.44-build"],
        ),
        make_node(
            "proposal.p8.43-preflight",
            "proposal",
            "Minimal source edit proposal",
            status="changed",
            sourceRefs=[args.proposal.as_posix()],
            evidenceRefs=["evidence.p8.43-validation"],
            authorityRefs=["authority.p8.43-preview-only"],
            historyRefs=["history.p8.43-proposal-preview", "history.p8.44-source-application"],
            deltaRefs=["delta.p8.44-apply-preflight"],
            graphDiffRef="graphNodeDiff.proposal.p8.43-preflight",
            attributes={
                "beforeStatus": proposal.get("status"),
                "afterStatus": application.get("status"),
                "previewExactContentApplied": application.get("previewDeviation", {}).get("previewExactContentApplied"),
            },
        ),
        make_node(
            "code.file.intentgraph-preflight",
            "code-file",
            "Invoke-IntentGraphShellWorkspacePreflight.ps1",
            status="added",
            sourceRefs=[
                "tests/RegressionSmoke/Invoke-IntentGraphShellWorkspacePreflight.ps1",
                args.applied_file.as_posix(),
            ],
            codeDiffRefs=["codeDiff.add-intentgraph-preflight"],
            evidenceRefs=["evidence.p8.44-final-preflight"],
            authorityRefs=["authority.p8.44-user-source-edit"],
            historyRefs=["history.p8.44-source-application"],
            deltaRefs=["delta.p8.44-apply-preflight"],
        ),
        make_node(
            "test.preflight.intentgraph-shell",
            "test",
            "IntentGraph shell/workspace preflight",
            status="added",
            sourceRefs=["tests/RegressionSmoke/Invoke-IntentGraphShellWorkspacePreflight.ps1"],
            codeDiffRefs=["codeDiff.add-intentgraph-preflight"],
            evidenceRefs=["evidence.p8.44-final-preflight"],
            authorityRefs=["authority.p8.44-user-source-edit"],
            historyRefs=["history.p8.44-source-application"],
            deltaRefs=["delta.p8.44-apply-preflight"],
        ),
        make_node(
            "evidence.p8.44-final-preflight",
            "evidence",
            "Final preflight passed",
            sourceRefs=[args.application.as_posix()],
            attributes={"result": "pass"},
        ),
        make_node(
            "evidence.p8.44-build",
            "evidence",
            "WindowsUtility build passed",
            sourceRefs=[args.application.as_posix()],
            attributes={"result": "pass"},
        ),
        make_node(
            "package.p8.55-sandbox-artifact",
            "package-artifact",
            "Sandboxed WindowsUtility package artifact",
            status="added",
            sourceRefs=[args.package_summary.as_posix()],
            evidenceRefs=["evidence.p8.55-package-validation"],
            authorityRefs=["authority.p8.54-package-artifact"],
            historyRefs=["history.p8.55-package-artifact"],
            deltaRefs=["delta.p8.55-package-artifact"],
            attributes={
                "sha256": package_summary.get("packageArtifact", {}).get("sha256"),
                "byteLength": package_summary.get("packageArtifact", {}).get("byteLength"),
                "fileCount": package_summary.get("packageArtifact", {}).get("fileCount"),
            },
        ),
        make_node(
            "requirement.p8.57-graph-delta-workbench",
            "requirement",
            "Approval workbench graph/delta/diff requirement",
            status="added",
            sourceRefs=[args.requirement.as_posix()],
            evidenceRefs=[],
            authorityRefs=["authority.coordinator.p8.57"],
            historyRefs=["history.p8.57-requirement-record"],
            deltaRefs=["delta.p8.57-approval-workbench-requirement"],
        ),
        make_node(
            "boundary.p8.58-graph-delta-workbench",
            "boundary",
            "Graph delta approval workbench boundary",
            status="added",
            sourceRefs=[args.boundary.as_posix()],
            evidenceRefs=[],
            authorityRefs=["authority.roadmap.p8.58"],
            historyRefs=["history.p8.58-boundary-plan"],
            deltaRefs=["delta.p8.58-boundary-plan"],
        ),
    ]

    edges = [
        make_edge(
            "edge.intent-to-surface",
            "targets",
            "intent.shell-workspace",
            "code.surface.windowsutility-shell",
            evidenceRefs=["evidence.p8.44-build"],
        ),
        make_edge(
            "edge.proposal-to-code-file",
            "proposes",
            "proposal.p8.43-preflight",
            "code.file.intentgraph-preflight",
            status="changed",
            evidenceRefs=["evidence.p8.44-final-preflight"],
            authorityRefs=["authority.p8.44-user-source-edit"],
            historyRefs=["history.p8.44-source-application"],
            deltaRefs=["delta.p8.44-apply-preflight"],
            graphDiffRef="graphEdgeDiff.edge.proposal-to-code-file",
            attributes={"beforeRelation": "planned-add", "afterRelation": "applied-add"},
        ),
        make_edge(
            "edge.code-file-to-test",
            "contains",
            "code.file.intentgraph-preflight",
            "test.preflight.intentgraph-shell",
            status="added",
            evidenceRefs=["evidence.p8.44-final-preflight"],
            deltaRefs=["delta.p8.44-apply-preflight"],
        ),
        make_edge(
            "edge.test-verifies-surface",
            "verifies",
            "test.preflight.intentgraph-shell",
            "code.surface.windowsutility-shell",
            status="added",
            evidenceRefs=["evidence.p8.44-final-preflight"],
            deltaRefs=["delta.p8.44-apply-preflight"],
        ),
        make_edge(
            "edge.package-derived-from-surface",
            "packages",
            "package.p8.55-sandbox-artifact",
            "code.surface.windowsutility-shell",
            status="added",
            evidenceRefs=["evidence.p8.55-package-validation"],
            authorityRefs=["authority.p8.54-package-artifact"],
            deltaRefs=["delta.p8.55-package-artifact"],
        ),
        make_edge(
            "edge.requirement-drives-boundary",
            "drives",
            "requirement.p8.57-graph-delta-workbench",
            "boundary.p8.58-graph-delta-workbench",
            status="added",
            authorityRefs=["authority.coordinator.p8.57"],
            deltaRefs=["delta.p8.58-boundary-plan"],
        ),
        make_edge(
            "edge.boundary-requires-code-diff",
            "requires",
            "boundary.p8.58-graph-delta-workbench",
            "code.file.intentgraph-preflight",
            status="added",
            deltaRefs=["delta.p8.58-boundary-plan"],
        ),
    ]

    code_diffs = [
        {
            "id": "codeDiff.add-intentgraph-preflight",
            "filePath": "tests/RegressionSmoke/Invoke-IntentGraphShellWorkspacePreflight.ps1",
            "beforeRange": None,
            "afterRange": {"startLine": 1, "endLine": len(applied_file.read_text(encoding="utf-8-sig").splitlines())},
            "changeKind": "add-file",
            "diffHunks": [code_diff_hunk],
            "affectedNodeIds": ["code.file.intentgraph-preflight", "test.preflight.intentgraph-shell"],
            "affectedEdgeIds": ["edge.proposal-to-code-file", "edge.code-file-to-test", "edge.test-verifies-surface"],
            "deltaStepId": "deltaStep.p8.44-apply-preflight.add-file",
            "evidenceRefs": ["evidence.p8.44-final-preflight", "evidence.p8.44-build"],
            "authorityRefs": ["authority.p8.44-user-source-edit"],
            "blockerIfMissing": None,
        }
    ]

    graph_node_diffs = [
        {
            "id": "graphNodeDiff.proposal.p8.43-preflight",
            "elementId": "proposal.p8.43-preflight",
            "elementKind": "proposal",
            "changeKind": "status-and-application-result",
            "beforePayload": {
                "status": proposal.get("status"),
                "applicationStatus": "not-applied",
                "patchApplied": proposal.get("patchPreview", {}).get("patchApplied"),
            },
            "afterPayload": {
                "status": application.get("status"),
                "applicationStatus": "applied",
                "previewExactContentApplied": application.get("previewDeviation", {}).get("previewExactContentApplied"),
                "targetCommit": application.get("targetRepository", {}).get("afterHead"),
            },
            "changedFields": ["status", "applicationStatus", "previewExactContentApplied", "targetCommit"],
            "addedRefs": ["evidence.p8.44-final-preflight", "evidence.p8.44-build", "history.p8.44-source-application"],
            "removedRefs": [],
            "changedRefs": ["codeDiff.add-intentgraph-preflight"],
            "affectedCodeDiffRefs": ["codeDiff.add-intentgraph-preflight"],
            "deltaStepId": "deltaStep.p8.44-apply-preflight.apply",
            "evidenceRefs": ["evidence.p8.44-final-preflight", "evidence.p8.44-build"],
            "authorityRefs": ["authority.p8.44-user-source-edit"],
            "blockerIfMissing": None,
        }
    ]

    graph_edge_diffs = [
        {
            "id": "graphEdgeDiff.edge.proposal-to-code-file",
            "elementId": "edge.proposal-to-code-file",
            "elementKind": "edge",
            "changeKind": "planned-to-applied",
            "beforePayload": {
                "kind": "proposes",
                "source": "proposal.p8.43-preflight",
                "target": "code.file.intentgraph-preflight",
                "status": "planned",
                "attributes": {"relationState": "planned-add"},
            },
            "afterPayload": {
                "kind": "proposes",
                "source": "proposal.p8.43-preflight",
                "target": "code.file.intentgraph-preflight",
                "status": "changed",
                "attributes": {"relationState": "applied-add"},
            },
            "changedFields": ["status", "attributes.relationState"],
            "addedRefs": ["evidence.p8.44-final-preflight", "authority.p8.44-user-source-edit"],
            "removedRefs": [],
            "changedRefs": ["codeDiff.add-intentgraph-preflight"],
            "affectedCodeDiffRefs": ["codeDiff.add-intentgraph-preflight"],
            "deltaStepId": "deltaStep.p8.44-apply-preflight.apply",
            "evidenceRefs": ["evidence.p8.44-final-preflight"],
            "authorityRefs": ["authority.p8.44-user-source-edit"],
            "blockerIfMissing": None,
        }
    ]

    delta_steps = [
        {
            "id": "deltaStep.p8.44-apply-preflight.apply",
            "label": "Apply shell/workspace preflight source edit",
            "deltaId": "delta.p8.44-apply-preflight",
            "status": "applied",
            "affectedNodeIds": ["proposal.p8.43-preflight", "code.file.intentgraph-preflight", "test.preflight.intentgraph-shell"],
            "affectedEdgeIds": ["edge.proposal-to-code-file", "edge.code-file-to-test", "edge.test-verifies-surface"],
            "codeDiffRefs": ["codeDiff.add-intentgraph-preflight"],
            "graphNodeDiffRefs": ["graphNodeDiff.proposal.p8.43-preflight"],
            "graphEdgeDiffRefs": ["graphEdgeDiff.edge.proposal-to-code-file"],
            "evidenceRefs": ["evidence.p8.44-final-preflight", "evidence.p8.44-build"],
            "authorityRefs": ["authority.p8.44-user-source-edit"],
        },
        {
            "id": "deltaStep.p8.55-package-artifact.create",
            "label": "Create sandboxed package artifact",
            "deltaId": "delta.p8.55-package-artifact",
            "status": "recorded",
            "affectedNodeIds": ["package.p8.55-sandbox-artifact", "code.surface.windowsutility-shell"],
            "affectedEdgeIds": ["edge.package-derived-from-surface"],
            "codeDiffRefs": [],
            "graphNodeDiffRefs": [],
            "graphEdgeDiffRefs": [],
            "evidenceRefs": ["evidence.p8.55-package-validation"],
            "authorityRefs": ["authority.p8.54-package-artifact"],
        },
        {
            "id": "deltaStep.p8.58-boundary-plan.record",
            "label": "Record graph delta approval workbench boundary",
            "deltaId": "delta.p8.58-boundary-plan",
            "status": "recorded",
            "affectedNodeIds": ["requirement.p8.57-graph-delta-workbench", "boundary.p8.58-graph-delta-workbench"],
            "affectedEdgeIds": ["edge.requirement-drives-boundary", "edge.boundary-requires-code-diff"],
            "codeDiffRefs": [],
            "graphNodeDiffRefs": [],
            "graphEdgeDiffRefs": [],
            "evidenceRefs": [],
            "authorityRefs": ["authority.coordinator.p8.57", "authority.roadmap.p8.58"],
        },
    ]

    graph = {
        "nodes": nodes,
        "edges": edges,
    }
    indexes = build_indexes(nodes, edges, delta_steps, code_diffs, graph_node_diffs, graph_edge_diffs)
    delta = {
        "beforeGraphRef": "generated/windowsutility/workbench/p8.51-packaging-release-workbench-projection.json",
        "afterGraphRef": "generated/windowsutility/graph-delta-approval-workbench/p8.59/projection.json",
        "nodeStates": summarize_states(nodes),
        "edgeStates": summarize_states(edges),
        "addedNodes": [node["id"] for node in nodes if node["status"] == "added"],
        "removedNodes": [],
        "changedNodes": [node["id"] for node in nodes if node["status"] == "changed"],
        "impactedNodes": ["code.surface.windowsutility-shell"],
        "addedEdges": [edge["id"] for edge in edges if edge["status"] == "added"],
        "removedEdges": [],
        "changedEdges": [edge["id"] for edge in edges if edge["status"] == "changed"],
        "impactedEdges": ["edge.intent-to-surface"],
        "codeDiffs": code_diffs,
        "graphNodeDiffs": graph_node_diffs,
        "graphEdgeDiffs": graph_edge_diffs,
        "steps": delta_steps,
    }

    return {
        "artifactRole": "intentgraph-graph-delta-approval-workbench-projection",
        "status": "intentgraph-graph-delta-approval-workbench-projection-emitted",
        "scope": SCOPE,
        "workItem": WORK_ITEM,
        "date": DATE,
        "reportVersion": REPORT_VERSION,
        "sourceArtifacts": source_artifacts,
        "sourceRequirement": {
            "artifactRole": requirement.get("artifactRole"),
            "status": requirement.get("status"),
            "decision": requirement.get("decision"),
        },
        "sourceBoundary": {
            "artifactRole": boundary.get("artifactRole"),
            "status": boundary.get("status"),
            "decision": boundary.get("decision"),
        },
        "graph": graph,
        "delta": delta,
        "indexes": indexes,
        "selectionModel": {
            "nodeInspectorRequired": True,
            "edgeInspectorRequired": True,
            "codeDiffPanelRequired": True,
            "graphElementDiffPanelRequired": True,
            "evidenceAuthorityPanelRequired": True,
        },
        "claimScope": {
            "projectionOnly": True,
            "staticHtmlImplemented": False,
            "graphUiImplemented": False,
            "graphMutationFromUi": False,
            "approvalAutomation": False,
            "windowsUtilitySourceMutated": False,
            "packageExtractionPerformed": False,
            "packagedExecutableLaunchPerformed": False,
            "releasePublished": False,
            "productizationClaimed": False,
        },
        "authorizations": {
            "sourceEditsAuthorized": False,
            "targetWritesAuthorized": False,
            "graphMutationFromUiAuthorized": False,
            "approvalAutomationAuthorized": False,
            "packageExtractionAuthorized": False,
            "packagedExecutableLaunchAuthorized": False,
            "releasePublishingAuthorized": False,
            "productizationAuthorized": False,
        },
        "recommendedNextSlice": "P8.60 Static Graph Delta Approval Workbench Prototype",
    }


def summarize_states(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {"added": 0, "removed": 0, "changed": 0, "impacted": 0, "unchanged": 0}
    for item in items:
        status = str(item.get("status", "unchanged"))
        if status in counts:
            counts[status] += 1
        else:
            counts["unchanged"] += 1
    return counts


def build_indexes(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    delta_steps: list[dict[str, Any]],
    code_diffs: list[dict[str, Any]],
    graph_node_diffs: list[dict[str, Any]],
    graph_edge_diffs: list[dict[str, Any]],
) -> dict[str, Any]:
    nodes_by_id = {node["id"]: node for node in nodes}
    edges_by_id = {edge["id"]: edge for edge in edges}
    incoming: dict[str, list[str]] = {node["id"]: [] for node in nodes}
    outgoing: dict[str, list[str]] = {node["id"]: [] for node in nodes}
    nodes_by_kind: dict[str, list[str]] = {}
    edges_by_kind: dict[str, list[str]] = {}
    for node in nodes:
        nodes_by_kind.setdefault(node["kind"], []).append(node["id"])
    for edge in edges:
        outgoing.setdefault(edge["source"], []).append(edge["id"])
        incoming.setdefault(edge["target"], []).append(edge["id"])
        edges_by_kind.setdefault(edge["kind"], []).append(edge["id"])
    return {
        "nodesById": nodes_by_id,
        "edgesById": edges_by_id,
        "incomingEdgesByNode": incoming,
        "outgoingEdgesByNode": outgoing,
        "nodesByKind": {key: sorted(value) for key, value in sorted(nodes_by_kind.items())},
        "edgesByKind": {key: sorted(value) for key, value in sorted(edges_by_kind.items())},
        "deltaStepsById": {step["id"]: step for step in delta_steps},
        "codeDiffsById": {diff["id"]: diff for diff in code_diffs},
        "graphNodeDiffsById": {diff["id"]: diff for diff in graph_node_diffs},
        "graphEdgeDiffsById": {diff["id"]: diff for diff in graph_edge_diffs},
    }


def validate_projection(projection: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if projection.get("artifactRole") != "intentgraph-graph-delta-approval-workbench-projection":
        errors.append("projection artifactRole is not accepted")
    if projection.get("scope") != SCOPE:
        errors.append("projection scope is not accepted")
    nodes = projection.get("graph", {}).get("nodes", [])
    edges = projection.get("graph", {}).get("edges", [])
    if not nodes:
        errors.append("graph.nodes must be non-empty")
    if not edges:
        errors.append("graph.edges must be non-empty")
    node_ids = {node.get("id") for node in nodes if isinstance(node, dict)}
    edge_ids = {edge.get("id") for edge in edges if isinstance(edge, dict)}
    if len(node_ids) != len(nodes):
        errors.append("graph node ids must be unique")
    if len(edge_ids) != len(edges):
        errors.append("graph edge ids must be unique")
    for edge in edges:
        if edge.get("source") not in node_ids:
            errors.append(f"edge {edge.get('id')} source endpoint missing")
        if edge.get("target") not in node_ids:
            errors.append(f"edge {edge.get('id')} target endpoint missing")
    indexes = projection.get("indexes", {})
    for key in [
        "nodesById",
        "edgesById",
        "incomingEdgesByNode",
        "outgoingEdgesByNode",
        "nodesByKind",
        "edgesByKind",
        "deltaStepsById",
        "codeDiffsById",
        "graphNodeDiffsById",
        "graphEdgeDiffsById",
    ]:
        if key not in indexes:
            errors.append(f"indexes.{key} missing")

    code_diffs = indexes.get("codeDiffsById", {})
    graph_node_diffs = indexes.get("graphNodeDiffsById", {})
    graph_edge_diffs = indexes.get("graphEdgeDiffsById", {})
    for node in nodes:
        if "id" not in node or "kind" not in node or "label" not in node:
            errors.append("each node must have id/kind/label")
        if node.get("status") == "changed" and not node.get("graphDiffRef"):
            errors.append(f"changed node {node.get('id')} missing graphDiffRef")
        if node.get("graphDiffRef") and node.get("graphDiffRef") not in graph_node_diffs:
            errors.append(f"node {node.get('id')} graphDiffRef not found")
        if node.get("kind", "").startswith("code") or node.get("codeDiffRefs"):
            for diff_id in node.get("codeDiffRefs", []):
                if diff_id not in code_diffs:
                    errors.append(f"node {node.get('id')} codeDiffRef not found: {diff_id}")
    for edge in edges:
        if "id" not in edge or "kind" not in edge or "source" not in edge or "target" not in edge:
            errors.append("each edge must have id/kind/source/target")
        if edge.get("status") == "changed" and not edge.get("graphDiffRef"):
            errors.append(f"changed edge {edge.get('id')} missing graphDiffRef")
        if edge.get("graphDiffRef") and edge.get("graphDiffRef") not in graph_edge_diffs:
            errors.append(f"edge {edge.get('id')} graphDiffRef not found")
    for diff_id, diff in code_diffs.items():
        if not diff.get("diffHunks"):
            errors.append(f"code diff {diff_id} missing diffHunks")
        for node_id in diff.get("affectedNodeIds", []):
            if node_id not in node_ids:
                errors.append(f"code diff {diff_id} affected node missing: {node_id}")
        for edge_id in diff.get("affectedEdgeIds", []):
            if edge_id not in edge_ids:
                errors.append(f"code diff {diff_id} affected edge missing: {edge_id}")
    for diff_id, diff in graph_node_diffs.items():
        if not diff.get("beforePayload") or not diff.get("afterPayload") or not diff.get("changedFields"):
            errors.append(f"graph node diff {diff_id} missing before/after/changedFields")
    for diff_id, diff in graph_edge_diffs.items():
        if not diff.get("beforePayload") or not diff.get("afterPayload") or not diff.get("changedFields"):
            errors.append(f"graph edge diff {diff_id} missing before/after/changedFields")
    for step_id, step in indexes.get("deltaStepsById", {}).items():
        for node_id in step.get("affectedNodeIds", []):
            if node_id not in node_ids:
                errors.append(f"delta step {step_id} affected node missing: {node_id}")
        for edge_id in step.get("affectedEdgeIds", []):
            if edge_id not in edge_ids:
                errors.append(f"delta step {step_id} affected edge missing: {edge_id}")
        for diff_id in step.get("codeDiffRefs", []):
            if diff_id not in code_diffs:
                errors.append(f"delta step {step_id} code diff missing: {diff_id}")
        for diff_id in step.get("graphNodeDiffRefs", []):
            if diff_id not in graph_node_diffs:
                errors.append(f"delta step {step_id} graph node diff missing: {diff_id}")
        for diff_id in step.get("graphEdgeDiffRefs", []):
            if diff_id not in graph_edge_diffs:
                errors.append(f"delta step {step_id} graph edge diff missing: {diff_id}")
    claim_scope = projection.get("claimScope", {})
    for key in [
        "graphMutationFromUi",
        "approvalAutomation",
        "windowsUtilitySourceMutated",
        "packageExtractionPerformed",
        "packagedExecutableLaunchPerformed",
        "releasePublished",
        "productizationClaimed",
    ]:
        if claim_scope.get(key) is not False:
            errors.append(f"claimScope.{key} must be false")
    return {
        "artifactRole": "intentgraph-graph-delta-approval-workbench-projection-validation-report",
        "status": "intentgraph-graph-delta-approval-workbench-projection-validation-passed"
        if not errors
        else "intentgraph-graph-delta-approval-workbench-projection-validation-failed",
        "scope": SCOPE,
        "workItem": WORK_ITEM,
        "date": DATE,
        "reportVersion": REPORT_VERSION,
        "result": "pass" if not errors else "fail",
        "summary": {
            "nodeCount": len(nodes) if isinstance(nodes, list) else 0,
            "edgeCount": len(edges) if isinstance(edges, list) else 0,
            "deltaStepCount": len(indexes.get("deltaStepsById", {})) if isinstance(indexes, dict) else 0,
            "codeDiffCount": len(indexes.get("codeDiffsById", {})) if isinstance(indexes, dict) else 0,
            "graphNodeDiffCount": len(indexes.get("graphNodeDiffsById", {})) if isinstance(indexes, dict) else 0,
            "graphEdgeDiffCount": len(indexes.get("graphEdgeDiffsById", {})) if isinstance(indexes, dict) else 0,
            "errorCount": len(errors),
        },
        "projectionDigest": digest_json(projection),
        "errors": errors,
    }


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Emit graph delta approval workbench projection.")
    parser.add_argument("--requirement", default=repo_root / "generated/roadmap/p8.57-approval-workbench-graph-delta-visualization-requirement-report.json", type=Path)
    parser.add_argument("--boundary", default=repo_root / "generated/roadmap/p8.58-graph-delta-approval-workbench-boundary-plan-report.json", type=Path)
    parser.add_argument("--proposal", default=repo_root / "generated/windowsutility/source-application-proposals/p8.43/minimal-source-edit-proposal.json", type=Path)
    parser.add_argument("--application", default=repo_root / "generated/windowsutility/source-application-applications/p8.44/application-report.json", type=Path)
    parser.add_argument("--applied-file", default=repo_root / "generated/windowsutility/source-application-applications/p8.44/applied-Invoke-IntentGraphShellWorkspacePreflight.ps1", type=Path)
    parser.add_argument("--package-summary", default=repo_root / "generated/roadmap/p8.55-sandboxed-package-artifact-creation-probe-report.json", type=Path)
    parser.add_argument("--out", default=repo_root / "generated/windowsutility/graph-delta-approval-workbench/p8.59/projection.json", type=Path)
    parser.add_argument("--validation-out", default=repo_root / "generated/windowsutility/graph-delta-approval-workbench/p8.59/validation-report.json", type=Path)
    args = parser.parse_args()

    try:
        projection = build_projection(args)
        validation = validate_projection(projection)
        write_json(args.out, projection)
        write_json(args.validation_out, validation)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"emit graph delta approval workbench projection failed: {error}")
        return 1
    return 0 if validation["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
