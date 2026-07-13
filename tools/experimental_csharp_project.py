"""Create and render a local semantic-overlay project workspace over a C# fact snapshot.

The workspace owns IntentGraph records only.  Its nested snapshot is an immutable copy
of a validated P9.10 C# fact workspace; it never points at or edits the source project.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from emit_experimental_csharp_fact_workbench import (
    ALLOWED_FACT_KINDS,
    ALLOWED_RELATION_KINDS,
    CYTOSCAPE_LICENSE_SOURCE,
    CYTOSCAPE_SOURCE,
    fact_interpretation,
    relation_interpretation,
    safe_relative_source,
)
from experimental_csharp_workspace import (
    ExperimentalWorkspaceError,
    LOGICAL_SOURCE_ROOT,
    PROFILE_ID,
    canonical_json,
    digest_bytes,
    validate_workspace as validate_snapshot_workspace,
)


PROJECT_FILE = "intentgraph.project.json"
SNAPSHOT_DIRECTORY = "snapshot"
PROJECT_ROLE = "intentgraph-experimental-csharp-project-workspace"
PROJECT_STATE_ROLE = "intentgraph-experimental-csharp-project-state"
PROJECT_SCHEMA_VERSION = "0.1.0"
PROJECT_SCOPE = "experimental-csharp-semantic-overlay-review"
WORKBENCH_ROLE = "intentgraph-experimental-csharp-project-workbench"
WORKBENCH_SCOPE = "p9.13-experimental-csharp-project-overlay-workbench"
WORKBENCH_VERSION = "0.1.0"
PROPOSAL_ROLE = "intentgraph-experimental-csharp-change-proposal"
PROPOSAL_SCOPE = "experimental-csharp-semantic-overlay-change-proposal"
PROPOSAL_STATUS = "not-applied-review-required"
REVIEW_RECEIPT_ROLE = "intentgraph-experimental-csharp-review-receipt"
REVIEW_RECEIPT_SCOPE = "experimental-csharp-semantic-overlay-review-receipt"
REVIEW_RECEIPT_STATUS = "review-only-receipt-recorded"
REVIEW_RECEIPT_RESULTS = {"reviewed-pass", "reviewed-fail", "review-blocked"}
REVIEW_RECEIPT_SCOPES = {"proposal", "code-diff", "graph-delta", "verification-requirement", "evidence-requirement"}
FOUNDATION_ROLE = "intentgraph-semantic-foundation"
FOUNDATION_STATUS = "intentgraph-semantic-foundation-declared"
FOUNDATION_SCOPE = "experimental-csharp-semantic-foundation-declared-only"
FOUNDATION_RECORD_ROLE = "intentgraph-semantic-foundation-record"
FOUNDATION_RECORD_SCOPE = "experimental-csharp-semantic-foundation-project-state"
SEMANTIC_RELATION_OVERLAY_ROLE = "intentgraph-experimental-csharp-semantic-relation-overlay"
SEMANTIC_RELATION_OVERLAY_STATUS = "intentgraph-experimental-csharp-semantic-relation-overlay-extracted"
SEMANTIC_RELATION_OVERLAY_SCOPE = "experimental-csharp-semantic-relation-overlay-readonly"
SEMANTIC_RELATION_RECORD_ROLE = "intentgraph-experimental-csharp-semantic-relation-overlay-record"
SEMANTIC_RELATION_RECORD_SCOPE = "experimental-csharp-semantic-relation-overlay-project-state"
SEMANTIC_RELATION_KINDS = {"calls", "references", "constructs", "inherits", "implements"}
FOUNDATION_AUTHORITY = {
    "targetRepositoryMutation": False,
    "automaticIntentCreation": False,
    "automaticMapping": False,
    "automaticCodeApplication": False,
    "networkRequired": False,
    "credentialAccessAllowed": False,
}
PROPOSAL_AUTHORITY = {
    "targetRepositoryMutation": False,
    "automaticCodeApplication": False,
    "selfAuthorized": False,
    "networkRequired": False,
    "credentialAccessAllowed": False,
    "graphMutationApplied": False,
    "approvalRecorded": False,
}
REVIEW_RECEIPT_AUTHORITY = {
    "targetRepositoryMutation": False,
    "automaticCodeApplication": False,
    "verificationExecution": False,
    "evidenceExecution": False,
    "selfAuthorized": False,
    "approvalRecorded": False,
    "networkRequired": False,
    "credentialAccessAllowed": False,
}
SEMANTIC_DELTA_CATEGORIES = {"verification", "evidence"}

PROJECT_AUTHORITY = {
    "projectWorkspaceMutation": True,
    "snapshotWorkspaceMutation": False,
    "targetRepositoryMutation": False,
    "targetBuildExecuted": False,
    "targetRestoreExecuted": False,
    "targetLaunchExecuted": False,
    "networkRequired": False,
    "providerApiAllowed": False,
    "credentialAccessAllowed": False,
    "automaticIntentMapping": False,
    "automaticCodeApplication": False,
    "approvalAutomation": False,
    "graphMutationFromUi": False,
    "igdProductizationClaimed": False,
}

WORK_STATUSES = {"intake", "mapping-candidate", "mapped", "proposal-ready", "verified", "blocked", "complete"}
MAPPING_STATUSES = {"unmapped", "candidate", "accepted"}
SAFE_ID = re.compile(r"^[a-z][a-z0-9.-]{2,100}$")


class ProjectWorkspaceError(ValueError):
    """Raised when the project overlay workspace boundary is violated."""


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ProjectWorkspaceError(f"invalid JSON artifact: {path.name}") from error
    if not isinstance(value, dict):
        raise ProjectWorkspaceError(f"JSON root must be an object: {path.name}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def digest_json(value: Any) -> str:
    return digest_bytes(canonical_json(value))


def file_digest(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def safe_id(value: str, label: str) -> None:
    if not SAFE_ID.fullmatch(value):
        raise ProjectWorkspaceError(f"{label} must be a stable lowercase identifier")


def assert_no_unsafe_state(value: Any, path: str = "") -> None:
    forbidden_keys = {"externalSourcePath", "physicalSourceRoot", "targetSyntax", "sourceText", "patch", "replacementText"}
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if key in forbidden_keys:
                raise ProjectWorkspaceError(f"{child_path} is not permitted in project overlay state")
            assert_no_unsafe_state(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            assert_no_unsafe_state(child, f"{path}[{index}]")
    elif isinstance(value, str) and (re.search(r"^[A-Za-z]:[\\/]", value) or value.startswith("/")):
        raise ProjectWorkspaceError(f"{path or 'state'} must not persist a physical path")


def snapshot_paths(project_workspace: Path) -> tuple[Path, Path]:
    workspace = project_workspace.resolve()
    project_file = workspace / PROJECT_FILE
    snapshot = workspace / SNAPSHOT_DIRECTORY
    if not project_file.is_file():
        raise ProjectWorkspaceError(f"project workspace is missing {PROJECT_FILE}")
    if not snapshot.is_dir():
        raise ProjectWorkspaceError("project workspace is missing its nested snapshot")
    return project_file, snapshot


def contained_project_path(project_workspace: Path, value: str, *, required_directory: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts or relative.parts[0] != required_directory:
        raise ProjectWorkspaceError(f"project artifact path must remain beneath {required_directory}/")
    candidate = (project_workspace / relative).resolve()
    if not is_within(candidate, project_workspace):
        raise ProjectWorkspaceError("project artifact path escapes the project workspace")
    return candidate


def snapshot_summary(snapshot: Path) -> tuple[dict[str, Any], dict[str, Path], dict[str, Any], dict[str, Any]]:
    try:
        manifest, paths, summary = validate_snapshot_workspace(snapshot)
    except ExperimentalWorkspaceError as error:
        raise ProjectWorkspaceError(f"validated experimental C# snapshot required: {error}") from error
    facts = read_json(paths["codeFacts"])
    if facts.get("profileId") != PROFILE_ID or facts.get("sourceRoot") != LOGICAL_SOURCE_ROOT:
        raise ProjectWorkspaceError("nested C# snapshot source identity is invalid")
    extractor = facts.get("extractor")
    if not isinstance(extractor, dict) or extractor.get("semanticResolution") is not False:
        raise ProjectWorkspaceError("nested C# snapshot must remain syntax-only")
    return manifest, paths, summary, facts


def empty_semantic_foundation() -> dict[str, Any]:
    return {
        "artifactRole": FOUNDATION_RECORD_ROLE,
        "status": "not-recorded",
        "scope": FOUNDATION_RECORD_SCOPE,
        "sourceArtifactDigest": None,
        "sourceDocuments": [],
        "goals": [],
        "capabilities": [],
        "constraints": [],
        "verificationRequirements": [],
    }


def empty_semantic_relation_overlay() -> dict[str, Any]:
    return {
        "artifactRole": SEMANTIC_RELATION_RECORD_ROLE,
        "status": "not-recorded",
        "scope": SEMANTIC_RELATION_RECORD_SCOPE,
        "sourceArtifactDigest": None,
        "extractor": None,
        "diagnostics": None,
        "relations": [],
    }


def resolved_relation_interpretation(kind: str) -> str:
    meanings = {
        "calls": "Resolved local call target from the read-only C# semantic overlay.",
        "references": "Resolved local symbol reference from the read-only C# semantic overlay.",
        "constructs": "Resolved local constructor target from the read-only C# semantic overlay.",
        "inherits": "Resolved local base-type relationship from the read-only C# semantic overlay.",
        "implements": "Resolved local interface implementation from the read-only C# semantic overlay.",
    }
    return meanings[kind]


def validate_semantic_relation_overlay(
    overlay: dict[str, Any],
    *,
    facts: dict[str, Any],
    source_artifact: bool,
) -> dict[str, Any]:
    """Validate a local-symbol relation sidecar without treating it as a project build."""
    assert_no_unsafe_state(overlay)
    raw_facts = facts.get("facts")
    source_digests = facts.get("sourceDigests")
    if not isinstance(raw_facts, list) or not isinstance(source_digests, dict):
        raise ProjectWorkspaceError("nested C# snapshot facts are incomplete for semantic relation validation")
    fact_ids = {item.get("id") for item in raw_facts if isinstance(item, dict) and isinstance(item.get("id"), str)}
    if not fact_ids or len(fact_ids) != len(raw_facts):
        raise ProjectWorkspaceError("nested C# snapshot fact identifiers are invalid for semantic relation validation")
    if source_artifact:
        expected = {
            "artifactRole", "status", "scope", "profileId", "sourceRoot", "sourceRootKind",
            "extractor", "sourceDigests", "diagnostics", "relations", "authority",
        }
        if set(overlay) != expected:
            raise ProjectWorkspaceError("semantic relation overlay artifact fields are invalid")
        if (
            overlay["artifactRole"] != SEMANTIC_RELATION_OVERLAY_ROLE
            or overlay["status"] != SEMANTIC_RELATION_OVERLAY_STATUS
            or overlay["scope"] != SEMANTIC_RELATION_OVERLAY_SCOPE
            or overlay["profileId"] != PROFILE_ID
            or overlay["sourceRoot"] != LOGICAL_SOURCE_ROOT
            or overlay["sourceRootKind"] != "logical-id"
            or overlay["sourceDigests"] != source_digests
        ):
            raise ProjectWorkspaceError("semantic relation overlay source identity is invalid")
        authority = {
            "sourceReadFromSnapshotOnly": True,
            "targetRepositoryMutation": False,
            "targetBuildExecuted": False,
            "targetRestoreExecuted": False,
            "networkRequired": False,
            "credentialAccessAllowed": False,
            "graphMutationApplied": False,
        }
        if overlay["authority"] != authority:
            raise ProjectWorkspaceError("semantic relation overlay authority boundary is invalid")
        record = {
            "artifactRole": SEMANTIC_RELATION_RECORD_ROLE,
            "status": "recorded",
            "scope": SEMANTIC_RELATION_RECORD_SCOPE,
            "sourceArtifactDigest": None,
            "extractor": overlay["extractor"],
            "diagnostics": overlay["diagnostics"],
            "relations": overlay["relations"],
        }
    else:
        expected = {"artifactRole", "status", "scope", "sourceArtifactDigest", "extractor", "diagnostics", "relations"}
        if set(overlay) != expected or overlay["artifactRole"] != SEMANTIC_RELATION_RECORD_ROLE or overlay["scope"] != SEMANTIC_RELATION_RECORD_SCOPE:
            raise ProjectWorkspaceError("semantic relation overlay project state is invalid")
        if overlay["status"] == "not-recorded":
            if any(overlay[key] is not None for key in ("sourceArtifactDigest", "extractor", "diagnostics")) or overlay["relations"]:
                raise ProjectWorkspaceError("empty semantic relation overlay must not contain relation data")
            return overlay
        if overlay["status"] != "recorded" or not sha256_value(overlay["sourceArtifactDigest"]):
            raise ProjectWorkspaceError("recorded semantic relation overlay provenance is invalid")
        record = overlay

    extractor = record["extractor"]
    expected_extractor = {
        "id", "version", "mode", "deterministic", "semanticResolution", "sourceBuildAllowed", "broadExtractor",
    }
    if not isinstance(extractor, dict) or set(extractor) != expected_extractor or extractor["id"] != "tools/csharp_semantic_overlay_probe/Program.cs" or not isinstance(extractor["version"], str) or not extractor["version"].strip() or extractor["mode"] != "roslyn-semantic-overlay-local-symbols" or extractor["deterministic"] is not True or extractor["semanticResolution"] is not True or extractor["sourceBuildAllowed"] is not False or extractor["broadExtractor"] is not False:
        raise ProjectWorkspaceError("semantic relation overlay extractor boundary is invalid")
    diagnostics = record["diagnostics"]
    expected_diagnostics = {"compilationErrorCount", "compilationWarningCount", "localDeclarationCount"}
    if not isinstance(diagnostics, dict) or set(diagnostics) != expected_diagnostics or any(not isinstance(value, int) or value < 0 for value in diagnostics.values()):
        raise ProjectWorkspaceError("semantic relation overlay diagnostics are invalid")
    relations = record["relations"]
    if not isinstance(relations, list) or not relations:
        raise ProjectWorkspaceError("semantic relation overlay must contain resolved local relations")
    relation_ids: set[str] = set()
    for relation in relations:
        if not isinstance(relation, dict) or set(relation) != {"id", "kind", "from", "to", "confidence"}:
            raise ProjectWorkspaceError("semantic relation overlay relation fields are invalid")
        safe_id(str(relation.get("id", "")), "semantic relation id")
        if relation["id"] in relation_ids or relation["kind"] not in SEMANTIC_RELATION_KINDS or relation["from"] not in fact_ids or relation["to"] not in fact_ids or relation["from"] == relation["to"] or relation["confidence"] != "resolved-local-symbol":
            raise ProjectWorkspaceError("semantic relation overlay relation is invalid")
        relation_ids.add(relation["id"])
    if [relation["id"] for relation in relations] != sorted(relation_ids):
        raise ProjectWorkspaceError("semantic relation overlay relations must be sorted by id")
    return record


def safe_logical_document_path(value: Any) -> bool:
    return (
        isinstance(value, str)
        and bool(value)
        and not value.startswith("/")
        and "\\" not in value
        and ".." not in value.split("/")
        and all(part not in {"", "."} for part in value.split("/"))
    )


def sha256_value(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"sha256:[0-9a-f]{64}", value) is not None


def validate_semantic_foundation(
    foundation: dict[str, Any],
    *,
    module_labels: set[str],
    source_artifact: bool,
) -> dict[str, Any]:
    assert_no_unsafe_state(foundation)
    if source_artifact:
        expected = {
            "artifactRole",
            "status",
            "scope",
            "sourceDocuments",
            "goals",
            "capabilities",
            "constraints",
            "verificationRequirements",
            "authority",
        }
        if set(foundation) != expected:
            raise ProjectWorkspaceError("semantic foundation artifact fields are invalid")
        if foundation["artifactRole"] != FOUNDATION_ROLE or foundation["status"] != FOUNDATION_STATUS or foundation["scope"] != FOUNDATION_SCOPE:
            raise ProjectWorkspaceError("semantic foundation artifact role, status, or scope is invalid")
        if foundation["authority"] != FOUNDATION_AUTHORITY:
            raise ProjectWorkspaceError("semantic foundation authority must remain declarative and non-applying")
        record = {
            "artifactRole": FOUNDATION_RECORD_ROLE,
            "status": "recorded",
            "scope": FOUNDATION_RECORD_SCOPE,
            "sourceArtifactDigest": None,
            **{key: foundation[key] for key in ("sourceDocuments", "goals", "capabilities", "constraints", "verificationRequirements")},
        }
    else:
        expected = {
            "artifactRole",
            "status",
            "scope",
            "sourceArtifactDigest",
            "sourceDocuments",
            "goals",
            "capabilities",
            "constraints",
            "verificationRequirements",
        }
        if set(foundation) != expected or foundation["artifactRole"] != FOUNDATION_RECORD_ROLE or foundation["scope"] != FOUNDATION_RECORD_SCOPE:
            raise ProjectWorkspaceError("semantic foundation project state is invalid")
        if foundation["status"] == "not-recorded":
            if foundation["sourceArtifactDigest"] is not None or any(foundation[key] for key in ("sourceDocuments", "goals", "capabilities", "constraints", "verificationRequirements")):
                raise ProjectWorkspaceError("empty semantic foundation must not contain declared records")
            return foundation
        if foundation["status"] != "recorded" or not sha256_value(foundation["sourceArtifactDigest"]):
            raise ProjectWorkspaceError("recorded semantic foundation provenance is invalid")
        record = foundation

    documents = record["sourceDocuments"]
    if not isinstance(documents, list) or not documents:
        raise ProjectWorkspaceError("semantic foundation must declare source documents")
    document_ids: set[str] = set()
    for document in documents:
        if not isinstance(document, dict) or set(document) != {"id", "title", "logicalPath", "contentDigest", "role"}:
            raise ProjectWorkspaceError("semantic foundation source document fields are invalid")
        safe_id(str(document.get("id", "")), "semantic foundation source document id")
        if document["id"] in document_ids or not isinstance(document["title"], str) or not document["title"].strip() or not safe_logical_document_path(document["logicalPath"]) or not sha256_value(document["contentDigest"]) or not isinstance(document["role"], str) or not document["role"].strip():
            raise ProjectWorkspaceError("semantic foundation source document is invalid")
        document_ids.add(document["id"])
    if [document["id"] for document in documents] != sorted(document_ids):
        raise ProjectWorkspaceError("semantic foundation source documents must be sorted by id")

    def validate_records(
        key: str,
        required_fields: set[str],
        *,
        capability_refs: bool = False,
        module_refs: bool = False,
    ) -> set[str]:
        records = record[key]
        if not isinstance(records, list) or not records:
            raise ProjectWorkspaceError(f"semantic foundation {key} must be non-empty")
        ids: set[str] = set()
        for item in records:
            if not isinstance(item, dict) or set(item) != required_fields:
                raise ProjectWorkspaceError(f"semantic foundation {key} fields are invalid")
            safe_id(str(item.get("id", "")), f"semantic foundation {key} id")
            if item["id"] in ids or not isinstance(item["title"], str) or not item["title"].strip() or not isinstance(item["summary"], str) or not item["summary"].strip():
                raise ProjectWorkspaceError(f"semantic foundation {key} record is invalid")
            source_ids = item.get("sourceDocumentIds")
            if not isinstance(source_ids, list) or not source_ids or source_ids != sorted(set(source_ids)) or any(identifier not in document_ids for identifier in source_ids):
                raise ProjectWorkspaceError(f"semantic foundation {key} source document references are invalid")
            if capability_refs:
                refs = item.get("capabilityIds")
                if not isinstance(refs, list) or not refs or refs != sorted(set(refs)):
                    raise ProjectWorkspaceError("semantic foundation goal capability references are invalid")
            if module_refs:
                labels = item.get("codeCapsuleLabels")
                if not isinstance(labels, list) or not labels or labels != sorted(set(labels)) or any(label not in module_labels for label in labels):
                    raise ProjectWorkspaceError(f"semantic foundation {key} code capsule references are invalid")
            ids.add(item["id"])
        return ids

    capability_ids = validate_records(
        "capabilities",
        {"id", "title", "summary", "sourceDocumentIds", "codeCapsuleLabels"},
        module_refs=True,
    )
    goal_ids = validate_records(
        "goals",
        {"id", "title", "summary", "sourceDocumentIds", "capabilityIds"},
        capability_refs=True,
    )
    if any(
        identifier not in capability_ids
        for goal in record["goals"]
        for identifier in goal["capabilityIds"]
    ):
        raise ProjectWorkspaceError("semantic foundation goal references an unknown capability")
    validate_records(
        "constraints",
        {"id", "title", "summary", "sourceDocumentIds"},
    )
    validate_records(
        "verificationRequirements",
        {"id", "title", "summary", "sourceDocumentIds", "codeCapsuleLabels"},
        module_refs=True,
    )
    if not goal_ids:
        raise ProjectWorkspaceError("semantic foundation must declare goals")
    return record


def state_for(project_id: str, title: str, snapshot_manifest: dict[str, Any], summary: dict[str, Any]) -> dict[str, Any]:
    safe_id(project_id, "project id")
    if not title.strip():
        raise ProjectWorkspaceError("project title must not be blank")
    source = snapshot_manifest["source"]
    return {
        "artifactRole": PROJECT_STATE_ROLE,
        "schemaVersion": PROJECT_SCHEMA_VERSION,
        "scope": PROJECT_SCOPE,
        "project": {
            "id": project_id,
            "title": title.strip(),
            "logicalSourceRoot": source["logicalId"],
            "sourceDigest": source["digest"],
            "sourceRole": source["sourceRole"],
        },
        "semanticFoundation": empty_semantic_foundation(),
        "semanticRelationOverlay": empty_semantic_relation_overlay(),
        "workItems": [],
        "mappings": [],
        "changeProposals": [],
        "reviewReceipts": [],
        "verification": [
            {
                "id": "verification.snapshot-integrity",
                "kind": "snapshot-integrity",
                "result": "pass",
                "summary": "The local C# source snapshot and syntax facts validated without modifying the source project.",
                "factCount": summary["factCount"],
                "relationCount": summary["relationCount"],
            }
        ],
        "evidence": [
            {
                "id": "evidence.snapshot-intake",
                "kind": "source-snapshot-receipt",
                "result": "pass",
                "summary": "Snapshot receipt, extraction report, and workspace validation are present.",
            }
        ],
        "authority": PROJECT_AUTHORITY,
        "history": [
            {
                "id": "history.project-initialized",
                "kind": "project-initialized",
                "summary": "Initialized a local semantic-overlay workspace from a validated read-only C# fact snapshot.",
            }
        ],
    }


def initialize_project(snapshot_workspace: Path, project_workspace: Path, project_id: str, title: str) -> dict[str, Any]:
    snapshot_workspace = snapshot_workspace.resolve()
    project_workspace = project_workspace.resolve()
    if project_workspace.exists():
        raise ProjectWorkspaceError("project workspace directory must not exist")
    if is_within(project_workspace, snapshot_workspace) or is_within(snapshot_workspace, project_workspace):
        raise ProjectWorkspaceError("project workspace must not overlap the source snapshot workspace")
    manifest, _, summary, _ = snapshot_summary(snapshot_workspace)
    project_workspace.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="intentgraph-csharp-project-", dir=project_workspace.parent) as temporary:
        staged = Path(temporary) / "project"
        shutil.copytree(snapshot_workspace, staged / SNAPSHOT_DIRECTORY)
        write_json(staged / PROJECT_FILE, state_for(project_id, title, manifest, summary))
        validate_project_workspace(staged)
        shutil.move(str(staged), str(project_workspace))
    return {
        "result": "pass",
        "command": "init-experimental-csharp-project",
        "projectWorkspace": project_workspace.as_posix(),
        "projectId": project_id,
        "snapshotWorkspaceMutation": False,
        "targetRepositoryMutation": False,
        "authority": PROJECT_AUTHORITY,
    }


def validate_record_ids(records: list[dict[str, Any]], label: str) -> set[str]:
    ids: set[str] = set()
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("id"), str):
            raise ProjectWorkspaceError(f"{label} records must have stable identifiers")
        identifier = str(record["id"])
        if identifier in ids:
            raise ProjectWorkspaceError(f"{label} record identifiers must be unique")
        ids.add(identifier)
    return ids


def validate_proposal_document(
    proposal: dict[str, Any],
    *,
    work_ids: set[str],
    mapping_ids: set[str],
    fact_by_id: dict[str, dict[str, Any]],
    known_node_ids: set[str],
) -> dict[str, Any]:
    assert_no_unsafe_state(proposal)
    expected = {
        "artifactRole",
        "schemaVersion",
        "scope",
        "id",
        "workItemId",
        "mappingId",
        "title",
        "summary",
        "applicationStatus",
        "graphDelta",
        "codeDiffs",
        "verificationRequirements",
        "evidenceRequirements",
        "authority",
    }
    if set(proposal) != expected:
        raise ProjectWorkspaceError("change proposal fields are invalid")
    if proposal["artifactRole"] != PROPOSAL_ROLE or proposal["schemaVersion"] != PROJECT_SCHEMA_VERSION or proposal["scope"] != PROPOSAL_SCOPE:
        raise ProjectWorkspaceError("change proposal role, schema version, or scope is invalid")
    safe_id(str(proposal["id"]), "change proposal id")
    if proposal["workItemId"] not in work_ids or proposal["mappingId"] not in mapping_ids:
        raise ProjectWorkspaceError("change proposal must reference a known work item and mapping candidate")
    if proposal["applicationStatus"] != PROPOSAL_STATUS:
        raise ProjectWorkspaceError("change proposal must remain non-applied and review-required")
    if not isinstance(proposal["title"], str) or not proposal["title"].strip() or not isinstance(proposal["summary"], str) or not proposal["summary"].strip():
        raise ProjectWorkspaceError("change proposal title and summary are required")
    if proposal["authority"] != PROPOSAL_AUTHORITY:
        raise ProjectWorkspaceError("change proposal authority must remain non-applying and non-self-authorizing")
    graph_delta = proposal["graphDelta"]
    if not isinstance(graph_delta, dict) or set(graph_delta) != {"addedNodes", "changedNodeIds", "addedEdges"}:
        raise ProjectWorkspaceError("change proposal graph delta is invalid")
    added_nodes = graph_delta["addedNodes"]
    changed_node_ids = graph_delta["changedNodeIds"]
    added_edges = graph_delta["addedEdges"]
    if not isinstance(added_nodes, list) or not isinstance(changed_node_ids, list) or not isinstance(added_edges, list):
        raise ProjectWorkspaceError("change proposal graph delta records must be lists")
    added_ids: set[str] = set()
    for node in added_nodes:
        if not isinstance(node, dict) or set(node) != {"id", "category", "label", "details"}:
            raise ProjectWorkspaceError("change proposal added node is invalid")
        safe_id(str(node["id"]), "change proposal added node id")
        if node["id"] in known_node_ids or node["id"] in added_ids or node["category"] not in SEMANTIC_DELTA_CATEGORIES:
            raise ProjectWorkspaceError("change proposal added node identifier or category is invalid")
        if not isinstance(node["label"], str) or not node["label"].strip() or not isinstance(node["details"], dict):
            raise ProjectWorkspaceError("change proposal added node content is invalid")
        added_ids.add(node["id"])
    if not changed_node_ids or any(not isinstance(identifier, str) or identifier not in known_node_ids for identifier in changed_node_ids) or len(set(changed_node_ids)) != len(changed_node_ids):
        raise ProjectWorkspaceError("change proposal changed node references are invalid")
    complete_node_ids = known_node_ids | added_ids
    edge_ids: set[str] = set()
    for edge in added_edges:
        if not isinstance(edge, dict) or set(edge) != {"id", "kind", "source", "target", "details"}:
            raise ProjectWorkspaceError("change proposal added edge is invalid")
        safe_id(str(edge["id"]), "change proposal added edge id")
        if edge["id"] in edge_ids or edge["source"] not in complete_node_ids or edge["target"] not in complete_node_ids or edge["kind"] not in {"requires", "verifies", "evidences"} or not isinstance(edge["details"], dict):
            raise ProjectWorkspaceError("change proposal added edge endpoints or kind are invalid")
        edge_ids.add(edge["id"])
    code_diffs = proposal["codeDiffs"]
    if not isinstance(code_diffs, list):
        raise ProjectWorkspaceError("change proposal code diffs must be a list")
    diff_ids: set[str] = set()
    diff_fact_ids: set[str] = set()
    for diff in code_diffs:
        if not isinstance(diff, dict) or set(diff) != {"id", "codeFactId", "sourceFile", "beforeSourceDigest", "unifiedDiff"}:
            raise ProjectWorkspaceError("change proposal code diff fields are invalid")
        safe_id(str(diff["id"]), "change proposal code diff id")
        fact = fact_by_id.get(diff["codeFactId"])
        if fact is None or diff["codeFactId"] not in changed_node_ids or diff["id"] in diff_ids or diff["codeFactId"] in diff_fact_ids:
            raise ProjectWorkspaceError("change proposal code diff must uniquely target a changed code fact")
        if diff["sourceFile"] != fact["sourceFile"] or diff["beforeSourceDigest"] != fact["sourceDigest"] or not safe_relative_source(diff["sourceFile"]):
            raise ProjectWorkspaceError("change proposal code diff provenance does not match its code fact")
        unified = diff["unifiedDiff"]
        if not isinstance(unified, str) or not unified.startswith("@@") or len(unified.encode("utf-8")) > 32768 or "\\" in unified or "\x00" in unified:
            raise ProjectWorkspaceError("change proposal unified diff is invalid")
        diff_ids.add(diff["id"])
        diff_fact_ids.add(diff["codeFactId"])
    for key in ("verificationRequirements", "evidenceRequirements"):
        records = proposal[key]
        if not isinstance(records, list) or not records:
            raise ProjectWorkspaceError(f"change proposal {key} must contain at least one requirement")
        record_ids = validate_record_ids(records, f"change proposal {key}")
        if len(record_ids) != len(records) or any(not isinstance(record.get("summary"), str) or not record["summary"].strip() for record in records):
            raise ProjectWorkspaceError(f"change proposal {key} records are invalid")
    return proposal


def proposal_artifacts(
    project_workspace: Path,
    state: dict[str, Any],
    *,
    work_ids: set[str],
    mapping_ids: set[str],
    fact_by_id: dict[str, dict[str, Any]],
    known_node_ids: set[str],
) -> list[dict[str, Any]]:
    records = state["changeProposals"]
    proposal_ids = validate_record_ids(records, "change proposal")
    proposals: list[dict[str, Any]] = []
    seen_work_items: set[str] = set()
    for record in records:
        expected = {"id", "artifact", "workItemId", "mappingId", "status"}
        if set(record) != expected:
            raise ProjectWorkspaceError("change proposal index record fields are invalid")
        if record["id"] not in proposal_ids or record["workItemId"] not in work_ids or record["mappingId"] not in mapping_ids or record["status"] != PROPOSAL_STATUS:
            raise ProjectWorkspaceError("change proposal index record is invalid")
        if record["workItemId"] in seen_work_items:
            raise ProjectWorkspaceError("P9.14 allows one active change proposal per work item")
        seen_work_items.add(record["workItemId"])
        artifact = contained_project_path(project_workspace, str(record["artifact"]), required_directory="proposals")
        if not artifact.is_file():
            raise ProjectWorkspaceError("change proposal artifact is missing")
        proposal = validate_proposal_document(read_json(artifact), work_ids=work_ids, mapping_ids=mapping_ids, fact_by_id=fact_by_id, known_node_ids=known_node_ids)
        if proposal["id"] != record["id"] or proposal["workItemId"] != record["workItemId"] or proposal["mappingId"] != record["mappingId"]:
            raise ProjectWorkspaceError("change proposal index record does not match its artifact")
        proposals.append(proposal)
    return proposals


def validate_review_receipt_document(
    receipt: dict[str, Any],
    *,
    proposal_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    assert_no_unsafe_state(receipt)
    expected = {
        "artifactRole",
        "schemaVersion",
        "scope",
        "id",
        "proposalId",
        "verificationRequirementId",
        "evidenceRequirementId",
        "result",
        "reviewScope",
        "summary",
        "authority",
    }
    if set(receipt) != expected:
        raise ProjectWorkspaceError("review receipt fields are invalid")
    if receipt["artifactRole"] != REVIEW_RECEIPT_ROLE or receipt["schemaVersion"] != PROJECT_SCHEMA_VERSION or receipt["scope"] != REVIEW_RECEIPT_SCOPE:
        raise ProjectWorkspaceError("review receipt role, schema version, or scope is invalid")
    safe_id(str(receipt["id"]), "review receipt id")
    proposal = proposal_by_id.get(receipt["proposalId"])
    if proposal is None:
        raise ProjectWorkspaceError("review receipt must reference a known change proposal")
    verification_ids = {record["id"] for record in proposal["verificationRequirements"]}
    evidence_ids = {record["id"] for record in proposal["evidenceRequirements"]}
    if receipt["verificationRequirementId"] not in verification_ids or receipt["evidenceRequirementId"] not in evidence_ids:
        raise ProjectWorkspaceError("review receipt requirement references are invalid")
    if receipt["result"] not in REVIEW_RECEIPT_RESULTS:
        raise ProjectWorkspaceError("review receipt result is invalid")
    review_scope = receipt["reviewScope"]
    if not isinstance(review_scope, list) or not review_scope or review_scope != sorted(set(review_scope)) or "proposal" not in review_scope or any(item not in REVIEW_RECEIPT_SCOPES for item in review_scope):
        raise ProjectWorkspaceError("review receipt scope is invalid")
    if not isinstance(receipt["summary"], str) or not receipt["summary"].strip():
        raise ProjectWorkspaceError("review receipt summary is required")
    if receipt["authority"] != REVIEW_RECEIPT_AUTHORITY:
        raise ProjectWorkspaceError("review receipt authority must remain non-executing and non-approving")
    return receipt


def review_receipt_artifacts(
    project_workspace: Path,
    state: dict[str, Any],
    *,
    proposals: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    records = state.get("reviewReceipts", [])
    if not isinstance(records, list):
        raise ProjectWorkspaceError("project state reviewReceipts must be a list")
    receipt_ids = validate_record_ids(records, "review receipt")
    proposal_by_id = {proposal["id"]: proposal for proposal in proposals}
    receipts: list[dict[str, Any]] = []
    seen_requirement_pairs: set[tuple[str, str, str]] = set()
    for record in records:
        expected = {"id", "artifact", "proposalId", "verificationRequirementId", "evidenceRequirementId", "status"}
        if set(record) != expected:
            raise ProjectWorkspaceError("review receipt index record fields are invalid")
        if record["id"] not in receipt_ids or record["proposalId"] not in proposal_by_id or record["status"] != REVIEW_RECEIPT_STATUS:
            raise ProjectWorkspaceError("review receipt index record is invalid")
        artifact = contained_project_path(project_workspace, str(record["artifact"]), required_directory="receipts")
        if not artifact.is_file():
            raise ProjectWorkspaceError("review receipt artifact is missing")
        receipt = validate_review_receipt_document(read_json(artifact), proposal_by_id=proposal_by_id)
        if any(receipt[key] != record[key] for key in ("id", "proposalId", "verificationRequirementId", "evidenceRequirementId")):
            raise ProjectWorkspaceError("review receipt index record does not match its artifact")
        requirement_pair = (receipt["proposalId"], receipt["verificationRequirementId"], receipt["evidenceRequirementId"])
        if requirement_pair in seen_requirement_pairs:
            raise ProjectWorkspaceError("review receipt already exists for the proposal requirement pair")
        seen_requirement_pairs.add(requirement_pair)
        receipts.append(receipt)
    return receipts


def validate_project_workspace(project_workspace: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Path], dict[str, Any]]:
    project_workspace = project_workspace.resolve()
    project_file, snapshot = snapshot_paths(project_workspace)
    snapshot_manifest, snapshot_artifacts, summary, facts = snapshot_summary(snapshot)
    state = read_json(project_file)
    assert_no_unsafe_state(state)
    if state.get("artifactRole") != PROJECT_STATE_ROLE or state.get("schemaVersion") != PROJECT_SCHEMA_VERSION or state.get("scope") != PROJECT_SCOPE:
        raise ProjectWorkspaceError("project state role, schema version, or scope is invalid")
    project = state.get("project")
    if not isinstance(project, dict):
        raise ProjectWorkspaceError("project state project must be an object")
    if set(project) != {"id", "title", "logicalSourceRoot", "sourceDigest", "sourceRole"}:
        raise ProjectWorkspaceError("project identity fields are invalid")
    safe_id(str(project.get("id", "")), "project id")
    if not isinstance(project.get("title"), str) or not project["title"].strip():
        raise ProjectWorkspaceError("project title is invalid")
    source = snapshot_manifest["source"]
    expected_project_source = {
        "logicalSourceRoot": source["logicalId"],
        "sourceDigest": source["digest"],
        "sourceRole": source["sourceRole"],
    }
    if {key: project[key] for key in expected_project_source} != expected_project_source:
        raise ProjectWorkspaceError("project state does not match nested snapshot provenance")
    if state.get("authority") != PROJECT_AUTHORITY:
        raise ProjectWorkspaceError("project authority boundary is invalid")
    if "reviewReceipts" not in state:
        state["reviewReceipts"] = []
    if "semanticRelationOverlay" not in state:
        state["semanticRelationOverlay"] = empty_semantic_relation_overlay()
    for key in ("workItems", "mappings", "changeProposals", "reviewReceipts", "verification", "evidence", "history"):
        if not isinstance(state.get(key), list):
            raise ProjectWorkspaceError(f"project state {key} must be a list")
    work_ids = validate_record_ids(state["workItems"], "work item")
    intent_ids: set[str] = set()
    for item in state["workItems"]:
        expected = {"id", "intentUnitId", "title", "request", "status", "mappingStatus", "changeStatus", "verificationStatus"}
        if set(item) != expected:
            raise ProjectWorkspaceError(f"work item {item.get('id')} fields are invalid")
        safe_id(str(item["id"]), "work item id")
        safe_id(str(item["intentUnitId"]), "intent unit id")
        if item["intentUnitId"] in intent_ids:
            raise ProjectWorkspaceError("intent unit identifiers must be unique")
        intent_ids.add(item["intentUnitId"])
        if not isinstance(item["title"], str) or not item["title"].strip() or not isinstance(item["request"], str) or not item["request"].strip():
            raise ProjectWorkspaceError(f"work item {item['id']} title and request are required")
        if item["status"] not in WORK_STATUSES or item["mappingStatus"] not in MAPPING_STATUSES:
            raise ProjectWorkspaceError(f"work item {item['id']} lifecycle state is invalid")
        if item["changeStatus"] not in {"not-proposed", "proposal-review-required"} or item["verificationStatus"] not in {"not-required", "snapshot-only", "requirements-recorded", "review-receipt-recorded"}:
            raise ProjectWorkspaceError(f"work item {item['id']} claims an unsupported change or verification state")
    fact_by_id = {fact.get("id"): fact for fact in facts.get("facts", []) if isinstance(fact, dict) and isinstance(fact.get("id"), str)}
    fact_ids = set(fact_by_id)
    module_labels = {
        str(fact["sourceFile"]).split("/", 1)[0]
        for fact in fact_by_id.values()
        if isinstance(fact.get("sourceFile"), str) and safe_relative_source(fact["sourceFile"])
    }
    foundation = validate_semantic_foundation(
        state.get("semanticFoundation", empty_semantic_foundation()),
        module_labels=module_labels,
        source_artifact=False,
    )
    semantic_relation_overlay = validate_semantic_relation_overlay(
        state["semanticRelationOverlay"],
        facts=facts,
        source_artifact=False,
    )
    mapping_ids = validate_record_ids(state["mappings"], "mapping")
    linked_work_ids: set[str] = set()
    for mapping in state["mappings"]:
        expected = {"id", "workItemId", "intentUnitId", "codeFactIds", "rationale", "status", "confidence"}
        if set(mapping) != expected:
            raise ProjectWorkspaceError(f"mapping {mapping.get('id')} fields are invalid")
        if mapping["workItemId"] not in work_ids or mapping["intentUnitId"] not in intent_ids:
            raise ProjectWorkspaceError("mapping must reference a known work item and intent unit")
        if mapping["workItemId"] in linked_work_ids:
            raise ProjectWorkspaceError("P9.13 allows one mapping candidate per work item")
        linked_work_ids.add(mapping["workItemId"])
        fact_refs = mapping["codeFactIds"]
        if not isinstance(fact_refs, list) or not fact_refs or any(not isinstance(item, str) or item not in fact_ids for item in fact_refs):
            raise ProjectWorkspaceError("mapping code fact references must resolve in the nested snapshot")
        if len(set(fact_refs)) != len(fact_refs):
            raise ProjectWorkspaceError("mapping code fact references must be unique")
        if mapping["status"] != "candidate" or mapping["confidence"] != "declared":
            raise ProjectWorkspaceError("P9.13 mappings must remain declared, unaccepted candidates")
        if not isinstance(mapping["rationale"], str) or not mapping["rationale"].strip():
            raise ProjectWorkspaceError("mapping rationale is required")
    for item in state["workItems"]:
        is_mapped = item["id"] in linked_work_ids
        expected_status = "candidate" if is_mapped else "unmapped"
        if item["mappingStatus"] != expected_status:
            raise ProjectWorkspaceError("work item mapping status must agree with mapping records")
    semantic_ids = {f"project.{project['id']}"}
    semantic_ids.update(f"work.{item['id']}" for item in state["workItems"])
    semantic_ids.update(item["intentUnitId"] for item in state["workItems"])
    semantic_ids.update(f"mapping.{mapping['id']}" for mapping in state["mappings"])
    semantic_ids.update(fact_ids)
    semantic_ids.add("authority.project-boundary")
    semantic_ids.update(f"verification.{record['id']}" for record in state["verification"])
    semantic_ids.update(f"evidence.{record['id']}" for record in state["evidence"])
    semantic_ids.update(f"history.{record['id']}" for record in state["history"])
    proposals = proposal_artifacts(project_workspace, state, work_ids=work_ids, mapping_ids=mapping_ids, fact_by_id=fact_by_id, known_node_ids=semantic_ids)
    review_receipts = review_receipt_artifacts(project_workspace, state, proposals=proposals)
    reviewed_proposal_ids = {receipt["proposalId"] for receipt in review_receipts}
    proposed_work_ids = {proposal["workItemId"] for proposal in proposals}
    for item in state["workItems"]:
        if item["id"] in proposed_work_ids:
            proposal = next(proposal for proposal in proposals if proposal["workItemId"] == item["id"])
            expected_verification_status = "review-receipt-recorded" if proposal["id"] in reviewed_proposal_ids else "requirements-recorded"
            if item["changeStatus"] != "proposal-review-required" or item["verificationStatus"] != expected_verification_status:
                raise ProjectWorkspaceError("work item proposal status must agree with its change proposal")
        elif item["changeStatus"] != "not-proposed":
            raise ProjectWorkspaceError("work item without a proposal must remain not-proposed")
    for key in ("verification", "evidence", "history"):
        validate_record_ids(state[key], key)
    if not state["verification"] or not state["evidence"] or not state["history"]:
        raise ProjectWorkspaceError("project state must retain snapshot verification, evidence, and history")
    return state, snapshot_manifest, snapshot_artifacts, {
        "summary": summary,
        "facts": facts,
        "mappingIds": mapping_ids,
        "proposals": proposals,
        "reviewReceipts": review_receipts,
        "semanticFoundation": foundation,
        "semanticRelationOverlay": semantic_relation_overlay,
    }


def add_work_request(project_workspace: Path, work_id: str, title: str, request: str) -> dict[str, Any]:
    project_workspace = project_workspace.resolve()
    state, _, _, _ = validate_project_workspace(project_workspace)
    safe_id(work_id, "work item id")
    intent_id = f"intent.{work_id}"
    safe_id(intent_id, "intent unit id")
    if any(item["id"] == work_id or item["intentUnitId"] == intent_id for item in state["workItems"]):
        raise ProjectWorkspaceError("work item identifier already exists")
    if not title.strip() or not request.strip():
        raise ProjectWorkspaceError("work item title and request must not be blank")
    state["workItems"].append(
        {
            "id": work_id,
            "intentUnitId": intent_id,
            "title": title.strip(),
            "request": request.strip(),
            "status": "intake",
            "mappingStatus": "unmapped",
            "changeStatus": "not-proposed",
            "verificationStatus": "snapshot-only",
        }
    )
    state["history"].append(
        {
            "id": f"history.request.{work_id}",
            "kind": "work-request-recorded",
            "summary": f"Recorded work request {work_id} without automatic mapping or source mutation.",
        }
    )
    write_json(project_workspace / PROJECT_FILE, state)
    validate_project_workspace(project_workspace)
    return {"result": "pass", "command": "add-experimental-csharp-work-request", "workItemId": work_id, "authority": PROJECT_AUTHORITY}


def add_mapping_candidate(project_workspace: Path, work_id: str, fact_ids: list[str], rationale: str) -> dict[str, Any]:
    project_workspace = project_workspace.resolve()
    state, _, _, data = validate_project_workspace(project_workspace)
    work = next((item for item in state["workItems"] if item["id"] == work_id), None)
    if work is None:
        raise ProjectWorkspaceError("mapping candidate work item does not exist")
    if not fact_ids or len(set(fact_ids)) != len(fact_ids):
        raise ProjectWorkspaceError("mapping candidate must reference one or more unique fact identifiers")
    known_facts = {fact.get("id") for fact in data["facts"].get("facts", []) if isinstance(fact, dict)}
    if any(fact_id not in known_facts for fact_id in fact_ids):
        raise ProjectWorkspaceError("mapping candidate contains an unknown code fact identifier")
    if not rationale.strip():
        raise ProjectWorkspaceError("mapping candidate rationale must not be blank")
    mapping_id = f"mapping.{work_id}.candidate"
    existing = next((item for item in state["mappings"] if item["workItemId"] == work_id), None)
    if existing is None:
        state["mappings"].append(
            {
                "id": mapping_id,
                "workItemId": work_id,
                "intentUnitId": work["intentUnitId"],
                "codeFactIds": sorted(fact_ids),
                "rationale": rationale.strip(),
                "status": "candidate",
                "confidence": "declared",
            }
        )
        history_kind = "mapping-candidate-recorded"
        history_summary = f"Recorded declared mapping candidate {mapping_id}; acceptance is not automatic."
    else:
        added = sorted(set(fact_ids) - set(existing["codeFactIds"]))
        if not added:
            raise ProjectWorkspaceError("mapping candidate already contains the selected code fact")
        existing["codeFactIds"] = sorted(set(existing["codeFactIds"]) | set(fact_ids))
        existing["rationale"] = existing["rationale"] + "\n" + rationale.strip()
        history_kind = "mapping-candidate-expanded"
        history_summary = f"Expanded declared mapping candidate {mapping_id} by {len(added)} code fact(s); acceptance is not automatic."
    work["mappingStatus"] = "candidate"
    work["status"] = "mapping-candidate"
    state["history"].append(
        {
            "id": f"history.mapping.{work_id}.{len(state['history'])}",
            "kind": history_kind,
            "summary": history_summary,
        }
    )
    write_json(project_workspace / PROJECT_FILE, state)
    validate_project_workspace(project_workspace)
    active_mapping = next(item for item in state["mappings"] if item["id"] == mapping_id)
    return {"result": "pass", "command": "add-experimental-csharp-mapping-candidate", "mappingId": mapping_id, "codeFactCount": len(active_mapping["codeFactIds"]), "authority": PROJECT_AUTHORITY}


def record_semantic_foundation(project_workspace: Path, foundation_path: Path) -> dict[str, Any]:
    project_workspace = project_workspace.resolve()
    foundation_path = foundation_path.resolve()
    if not foundation_path.is_file() or foundation_path.is_symlink():
        raise ProjectWorkspaceError("semantic foundation artifact must be a regular JSON file")
    state, _, _, data = validate_project_workspace(project_workspace)
    if data["semanticFoundation"]["status"] != "not-recorded":
        raise ProjectWorkspaceError("semantic foundation is already recorded; a future reviewed replacement boundary is required")
    module_labels = {
        str(fact["sourceFile"]).split("/", 1)[0]
        for fact in data["facts"].get("facts", [])
        if isinstance(fact, dict) and isinstance(fact.get("sourceFile"), str) and safe_relative_source(fact["sourceFile"])
    }


def record_semantic_relation_overlay(project_workspace: Path, overlay_path: Path) -> dict[str, Any]:
    """Record already-extracted local symbol relations without reading or altering the target repository."""
    project_workspace = project_workspace.resolve()
    overlay_path = overlay_path.resolve()
    if not overlay_path.is_file() or overlay_path.is_symlink():
        raise ProjectWorkspaceError("semantic relation overlay artifact must be a regular JSON file")
    if is_within(overlay_path, project_workspace):
        raise ProjectWorkspaceError("semantic relation overlay artifact must remain outside the project workspace")
    state, _, _, data = validate_project_workspace(project_workspace)
    if data["semanticRelationOverlay"]["status"] != "not-recorded":
        raise ProjectWorkspaceError("semantic relation overlay is already recorded; a future reviewed replacement boundary is required")
    overlay = validate_semantic_relation_overlay(read_json(overlay_path), facts=data["facts"], source_artifact=True)
    state["semanticRelationOverlay"] = {
        **overlay,
        "sourceArtifactDigest": file_digest(overlay_path),
    }
    state["history"].append(
        {
            "id": f"history.semantic-relation-overlay.{len(state['history'])}",
            "kind": "semantic-relation-overlay-recorded",
            "summary": "Recorded deterministic local-symbol relations from the immutable C# snapshot without building, restoring, launching, or changing the target project.",
        }
    )
    write_json(project_workspace / PROJECT_FILE, state)
    validate_project_workspace(project_workspace)
    diagnostics = state["semanticRelationOverlay"]["diagnostics"]
    return {
        "result": "pass",
        "command": "record-experimental-csharp-semantic-relation-overlay",
        "sourceArtifactDigest": state["semanticRelationOverlay"]["sourceArtifactDigest"],
        "resolvedRelationCount": len(state["semanticRelationOverlay"]["relations"]),
        "compilationErrorCount": diagnostics["compilationErrorCount"],
        "targetRepositoryMutation": False,
        "targetBuildExecuted": False,
        "targetRestoreExecuted": False,
        "authority": PROJECT_AUTHORITY,
    }
    foundation = validate_semantic_foundation(
        read_json(foundation_path),
        module_labels=module_labels,
        source_artifact=True,
    )
    state["semanticFoundation"] = {
        "artifactRole": FOUNDATION_RECORD_ROLE,
        "status": "recorded",
        "scope": FOUNDATION_RECORD_SCOPE,
        "sourceArtifactDigest": file_digest(foundation_path),
        **{key: foundation[key] for key in ("sourceDocuments", "goals", "capabilities", "constraints", "verificationRequirements")},
    }
    state["history"].append(
        {
            "id": f"history.semantic-foundation.{len(state['history'])}",
            "kind": "semantic-foundation-recorded",
            "summary": "Recorded declared project goals, capabilities, constraints, and verification requirements without creating automatic Intent Units or changing source code.",
        }
    )
    write_json(project_workspace / PROJECT_FILE, state)
    validate_project_workspace(project_workspace)
    return {
        "result": "pass",
        "command": "record-experimental-csharp-semantic-foundation",
        "sourceArtifactDigest": state["semanticFoundation"]["sourceArtifactDigest"],
        "goalCount": len(state["semanticFoundation"]["goals"]),
        "capabilityCount": len(state["semanticFoundation"]["capabilities"]),
        "constraintCount": len(state["semanticFoundation"]["constraints"]),
        "verificationRequirementCount": len(state["semanticFoundation"]["verificationRequirements"]),
        "authority": PROJECT_AUTHORITY,
    }


def add_change_proposal_document(project_workspace: Path, proposal: dict[str, Any]) -> dict[str, Any]:
    project_workspace = project_workspace.resolve()
    if not isinstance(proposal, dict):
        raise ProjectWorkspaceError("change proposal document must be a JSON object")
    state, _, _, data = validate_project_workspace(project_workspace)
    work_ids = {item["id"] for item in state["workItems"]}
    mapping_ids = {item["id"] for item in state["mappings"]}
    fact_by_id = {fact.get("id"): fact for fact in data["facts"].get("facts", []) if isinstance(fact, dict) and isinstance(fact.get("id"), str)}
    semantic_ids = {f"project.{state['project']['id']}"}
    semantic_ids.update(f"work.{item['id']}" for item in state["workItems"])
    semantic_ids.update(item["intentUnitId"] for item in state["workItems"])
    semantic_ids.update(f"mapping.{mapping['id']}" for mapping in state["mappings"])
    semantic_ids.update(fact_by_id)
    semantic_ids.add("authority.project-boundary")
    semantic_ids.update(f"verification.{record['id']}" for record in state["verification"])
    semantic_ids.update(f"evidence.{record['id']}" for record in state["evidence"])
    semantic_ids.update(f"history.{record['id']}" for record in state["history"])
    proposal = validate_proposal_document(proposal, work_ids=work_ids, mapping_ids=mapping_ids, fact_by_id=fact_by_id, known_node_ids=semantic_ids)
    if any(item["id"] == proposal["id"] or item["workItemId"] == proposal["workItemId"] for item in state["changeProposals"]):
        raise ProjectWorkspaceError("work item already has an active change proposal")
    destination_relative = f"proposals/{proposal['id']}.json"
    destination = contained_project_path(project_workspace, destination_relative, required_directory="proposals")
    if destination.exists():
        raise ProjectWorkspaceError("change proposal artifact path already exists")
    write_json(destination, proposal)
    state["changeProposals"].append(
        {
            "id": proposal["id"],
            "artifact": destination_relative,
            "workItemId": proposal["workItemId"],
            "mappingId": proposal["mappingId"],
            "status": PROPOSAL_STATUS,
        }
    )
    work = next(item for item in state["workItems"] if item["id"] == proposal["workItemId"])
    work["status"] = "proposal-ready"
    work["changeStatus"] = "proposal-review-required"
    work["verificationStatus"] = "requirements-recorded"
    state["verification"].append(
        {
            "id": f"verification.requirements.{proposal['id']}",
            "kind": "proposal-verification-requirements",
            "result": "required-not-run",
            "summary": f"Recorded {len(proposal['verificationRequirements'])} verification requirements for non-applied proposal {proposal['id']}.",
        }
    )
    state["evidence"].append(
        {
            "id": f"evidence.requirements.{proposal['id']}",
            "kind": "proposal-evidence-requirements",
            "result": "required-not-collected",
            "summary": f"Recorded {len(proposal['evidenceRequirements'])} evidence requirements for non-applied proposal {proposal['id']}.",
        }
    )
    state["history"].append(
        {
            "id": f"history.proposal.{proposal['id']}",
            "kind": "non-applied-change-proposal-recorded",
            "summary": f"Recorded non-applied proposal {proposal['id']} with graph delta and {len(proposal['codeDiffs'])} code diff record(s); no source change was applied.",
        }
    )
    write_json(project_workspace / PROJECT_FILE, state)
    validate_project_workspace(project_workspace)
    return {
        "result": "pass",
        "command": "add-experimental-csharp-change-proposal",
        "proposalId": proposal["id"],
        "applicationStatus": PROPOSAL_STATUS,
        "targetRepositoryMutation": False,
        "authority": PROJECT_AUTHORITY,
    }


def draft_change_proposal_from_mapping(
    project_workspace: Path,
    *,
    proposal_id: str,
    work_id: str,
    title: str,
    summary: str,
    verification_kind: str,
    verification_summary: str,
    evidence_kind: str,
    evidence_summary: str,
) -> dict[str, Any]:
    """Build one bounded, non-applied review proposal from a declared mapping.

    The caller supplies the review intent and requirements.  The workspace derives only
    stable references already recorded in the local project state; it never synthesizes
    a code patch, applies a graph delta, or changes the inspected source project.
    """

    draft = {
        "proposalId": proposal_id,
        "workId": work_id,
        "title": title,
        "summary": summary,
        "verificationKind": verification_kind,
        "verificationSummary": verification_summary,
        "evidenceKind": evidence_kind,
        "evidenceSummary": evidence_summary,
    }
    assert_no_unsafe_state(draft)
    if any(not isinstance(value, str) or not value.strip() for value in draft.values()):
        raise ProjectWorkspaceError("guided review proposal fields must be non-blank strings")
    if any(len(value.encode("utf-8")) > 12000 for value in draft.values()):
        raise ProjectWorkspaceError("guided review proposal fields exceed the local workspace size limit")
    safe_id(proposal_id, "guided review proposal id")
    safe_id(work_id, "guided review proposal work item id")
    safe_id(verification_kind, "guided review proposal verification kind")
    safe_id(evidence_kind, "guided review proposal evidence kind")

    project_workspace = project_workspace.resolve()
    state, _, _, _ = validate_project_workspace(project_workspace)
    work = next((item for item in state["workItems"] if item["id"] == work_id), None)
    if work is None:
        raise ProjectWorkspaceError("guided review proposal work item does not exist")
    mapping = next((item for item in state["mappings"] if item["workItemId"] == work_id), None)
    if mapping is None or mapping["status"] != "candidate" or mapping["confidence"] != "declared":
        raise ProjectWorkspaceError("guided review proposal requires a declared mapping candidate")
    if work["changeStatus"] != "not-proposed":
        raise ProjectWorkspaceError("guided review proposal work item already has an active change proposal")

    proposal = {
        "artifactRole": PROPOSAL_ROLE,
        "schemaVersion": PROJECT_SCHEMA_VERSION,
        "scope": PROPOSAL_SCOPE,
        "id": proposal_id,
        "workItemId": work_id,
        "mappingId": mapping["id"],
        "title": title.strip(),
        "summary": summary.strip(),
        "applicationStatus": PROPOSAL_STATUS,
        "graphDelta": {
            "addedNodes": [
                {
                    "id": f"verification.{proposal_id}",
                    "category": "verification",
                    "label": f"{title.strip()} review requirement",
                    "details": {
                        "kind": verification_kind,
                        "result": "required-not-run",
                        "summary": verification_summary.strip(),
                        "source": "guided-review-proposal-form",
                    },
                }
            ],
            "changedNodeIds": sorted(mapping["codeFactIds"]),
            "addedEdges": [
                {
                    "id": f"edge.{proposal_id}.verifies",
                    "kind": "verifies",
                    "source": work["intentUnitId"],
                    "target": f"verification.{proposal_id}",
                    "details": {"status": "required-not-run", "source": "guided-review-proposal-form"},
                }
            ],
        },
        "codeDiffs": [],
        "verificationRequirements": [
            {
                "id": f"verification.requirement.{proposal_id}",
                "kind": verification_kind,
                "summary": verification_summary.strip(),
            }
        ],
        "evidenceRequirements": [
            {
                "id": f"evidence.requirement.{proposal_id}",
                "kind": evidence_kind,
                "summary": evidence_summary.strip(),
            }
        ],
        "authority": PROPOSAL_AUTHORITY,
    }
    result = add_change_proposal_document(project_workspace, proposal)
    return {
        **result,
        "command": "draft-experimental-csharp-change-proposal",
        "mappingId": mapping["id"],
        "codeDiffCount": 0,
        "guidedReviewProposal": True,
    }


def add_change_proposal(project_workspace: Path, proposal_path: Path) -> dict[str, Any]:
    proposal_path = proposal_path.resolve()
    return add_change_proposal_document(project_workspace, read_json(proposal_path))


def add_review_receipt_document(project_workspace: Path, receipt: dict[str, Any]) -> dict[str, Any]:
    project_workspace = project_workspace.resolve()
    if not isinstance(receipt, dict):
        raise ProjectWorkspaceError("review receipt document must be a JSON object")
    state, _, _, data = validate_project_workspace(project_workspace)
    proposals = data["proposals"]
    proposal_by_id = {proposal["id"]: proposal for proposal in proposals}
    receipt = validate_review_receipt_document(receipt, proposal_by_id=proposal_by_id)
    if any(record["id"] == receipt["id"] for record in state["reviewReceipts"]):
        raise ProjectWorkspaceError("review receipt identifier already exists")
    if any(
        record["proposalId"] == receipt["proposalId"]
        and record["verificationRequirementId"] == receipt["verificationRequirementId"]
        and record["evidenceRequirementId"] == receipt["evidenceRequirementId"]
        for record in state["reviewReceipts"]
    ):
        raise ProjectWorkspaceError("review receipt already exists for the proposal requirement pair")
    destination_relative = f"receipts/{receipt['id']}.json"
    destination = contained_project_path(project_workspace, destination_relative, required_directory="receipts")
    if destination.exists():
        raise ProjectWorkspaceError("review receipt artifact path already exists")
    write_json(destination, receipt)
    state["reviewReceipts"].append(
        {
            "id": receipt["id"],
            "artifact": destination_relative,
            "proposalId": receipt["proposalId"],
            "verificationRequirementId": receipt["verificationRequirementId"],
            "evidenceRequirementId": receipt["evidenceRequirementId"],
            "status": REVIEW_RECEIPT_STATUS,
        }
    )
    proposal = proposal_by_id[receipt["proposalId"]]
    work = next(item for item in state["workItems"] if item["id"] == proposal["workItemId"])
    work["verificationStatus"] = "review-receipt-recorded"
    state["verification"].append(
        {
            "id": f"verification.review-receipt.{receipt['id']}",
            "kind": "review-receipt",
            "result": receipt["result"],
            "summary": f"Recorded a non-executing review receipt for {receipt['verificationRequirementId']}.",
        }
    )
    state["evidence"].append(
        {
            "id": f"evidence.review-receipt.{receipt['id']}",
            "kind": "review-receipt",
            "result": receipt["result"],
            "summary": f"Recorded a non-executing review receipt for {receipt['evidenceRequirementId']}.",
        }
    )
    state["history"].append(
        {
            "id": f"history.review-receipt.{receipt['id']}",
            "kind": "review-receipt-recorded",
            "summary": f"Recorded review receipt {receipt['id']} without executing verification, collecting runtime evidence, applying a graph delta, or changing source code.",
        }
    )
    write_json(project_workspace / PROJECT_FILE, state)
    validate_project_workspace(project_workspace)
    return {
        "result": "pass",
        "command": "add-experimental-csharp-review-receipt",
        "receiptId": receipt["id"],
        "proposalId": receipt["proposalId"],
        "resultStatus": receipt["result"],
        "targetRepositoryMutation": False,
        "authority": PROJECT_AUTHORITY,
    }


def draft_review_receipt_from_proposal(
    project_workspace: Path,
    *,
    receipt_id: str,
    proposal_id: str,
    verification_requirement_id: str,
    evidence_requirement_id: str,
    result: str,
    summary: str,
) -> dict[str, Any]:
    """Record one user-authored, non-executing review receipt from proposal requirements.

    The local workspace supplies only the immutable receipt envelope and the bounded
    review scope. It does not run the stated verification, collect evidence, approve
    the proposal, apply the proposal delta, or edit the inspected source project.
    """

    draft = {
        "receiptId": receipt_id,
        "proposalId": proposal_id,
        "verificationRequirementId": verification_requirement_id,
        "evidenceRequirementId": evidence_requirement_id,
        "result": result,
        "summary": summary,
    }
    assert_no_unsafe_state(draft)
    if any(not isinstance(value, str) or not value.strip() for value in draft.values()):
        raise ProjectWorkspaceError("guided review receipt fields must be non-blank strings")
    if any(len(value.encode("utf-8")) > 12000 for value in draft.values()):
        raise ProjectWorkspaceError("guided review receipt fields exceed the local workspace size limit")
    safe_id(receipt_id, "guided review receipt id")
    safe_id(proposal_id, "guided review receipt proposal id")
    safe_id(verification_requirement_id, "guided review receipt verification requirement id")
    safe_id(evidence_requirement_id, "guided review receipt evidence requirement id")
    if result not in REVIEW_RECEIPT_RESULTS:
        raise ProjectWorkspaceError("guided review receipt result is invalid")

    receipt = {
        "artifactRole": REVIEW_RECEIPT_ROLE,
        "schemaVersion": PROJECT_SCHEMA_VERSION,
        "scope": REVIEW_RECEIPT_SCOPE,
        "id": receipt_id.strip(),
        "proposalId": proposal_id.strip(),
        "verificationRequirementId": verification_requirement_id.strip(),
        "evidenceRequirementId": evidence_requirement_id.strip(),
        "result": result.strip(),
        "reviewScope": ["evidence-requirement", "proposal", "verification-requirement"],
        "summary": summary.strip(),
        "authority": REVIEW_RECEIPT_AUTHORITY,
    }
    recorded = add_review_receipt_document(project_workspace, receipt)
    return {
        **recorded,
        "command": "draft-experimental-csharp-review-receipt",
        "guidedReviewReceipt": True,
        "reviewScope": receipt["reviewScope"],
    }


def add_review_receipt(project_workspace: Path, receipt_path: Path) -> dict[str, Any]:
    receipt_path = receipt_path.resolve()
    return add_review_receipt_document(project_workspace, read_json(receipt_path))


def code_node(fact: dict[str, Any]) -> dict[str, Any]:
    kind = str(fact["kind"])
    location = fact.get("sourceLocation") if isinstance(fact.get("sourceLocation"), dict) else {"status": "file-level"}
    name = str(fact.get("name") or fact["sourceFile"].split("/")[-1])
    return {
        "id": fact["id"],
        "category": "code",
        "kind": kind,
        "label": name,
        "source": {"file": fact["sourceFile"], "digest": fact["sourceDigest"], "location": location},
        "provenance": {"extractor": fact["extractor"], "version": fact["extractorVersion"], "confidence": fact["confidence"]},
        "details": {"declarationKind": fact.get("declarationKind"), "invocationShape": fact.get("invocationShape"), "interpretation": fact_interpretation(kind)},
        "deltaState": "unchanged",
        "codeDiffs": [],
    }


def semantic_node(identifier: str, category: str, label: str, details: dict[str, Any]) -> dict[str, Any]:
    return {"id": identifier, "category": category, "kind": category, "label": label, "details": details}


def counts(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for record in records:
        value = str(record[key])
        result[value] = result.get(value, 0) + 1
    return dict(sorted(result.items()))


def build_work_stage_timeline(
    state: dict[str, Any],
    *,
    proposals: list[dict[str, Any]],
    review_receipts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Derive one inspectable lifecycle trace per recorded work item.

    The workspace already stores immutable request, mapping, proposal, and receipt
    records.  This projection deliberately groups those records without changing
    their authority or treating a review receipt as applied work.
    """
    mappings_by_work = {mapping["workItemId"]: mapping for mapping in state["mappings"]}
    proposals_by_work = {proposal["workItemId"]: proposal for proposal in proposals}
    receipts_by_proposal: dict[str, list[dict[str, Any]]] = {}
    for receipt in review_receipts:
        receipts_by_proposal.setdefault(receipt["proposalId"], []).append(receipt)

    stages: list[dict[str, Any]] = []
    for work in sorted(state["workItems"], key=lambda item: item["id"]):
        work_id = work["id"]
        intent_id = work["intentUnitId"]
        work_node = f"work.{work_id}"
        request_history = f"history.request.{work_id}"
        stages.append(
            {
                "id": f"stage.{work_id}.request",
                "workItemId": work_id,
                "sequence": 1,
                "kind": "request-recorded",
                "title": "Request recorded",
                "summary": "A requested semantic change was recorded without automatic mapping, source mutation, or approval.",
                "status": work["status"],
                "recordIds": [request_history],
                "nodeIds": [work_node, intent_id],
                "addedNodeIds": [work_node, intent_id],
                "changedNodeIds": [],
                "contextNodeIds": [],
                "edgeIds": [f"edge.project.{state['project']['id']}.tracks.{work_id}", f"edge.{work_id}.expresses.{intent_id}"],
                "addedEdgeIds": [f"edge.project.{state['project']['id']}.tracks.{work_id}", f"edge.{work_id}.expresses.{intent_id}"],
                "changedEdgeIds": [],
                "codeDiffs": [],
                "verificationRecordIds": [],
                "evidenceRecordIds": [],
                "revisionKind": "record-derived-no-application",
            }
        )
        mapping = mappings_by_work.get(work_id)
        if mapping is None:
            continue
        mapping_node = f"mapping.{mapping['id']}"
        mapping_edges = [f"edge.{mapping_node}.for.{intent_id}", *[f"edge.{mapping_node}.to.{fact_id}" for fact_id in mapping["codeFactIds"]]]
        stages.append(
            {
                "id": f"stage.{work_id}.mapping",
                "workItemId": work_id,
                "sequence": 2,
                "kind": "mapping-candidate-recorded",
                "title": "Code mapping recorded",
                "summary": "Candidate code facts were linked to the request. The mapping remains declared and is not an approval.",
                "status": mapping["status"],
                "recordIds": [f"history.mapping.{work_id}"],
                "nodeIds": [work_node, intent_id, mapping_node, *mapping["codeFactIds"]],
                "addedNodeIds": [mapping_node],
                "changedNodeIds": [],
                "contextNodeIds": list(mapping["codeFactIds"]),
                "edgeIds": mapping_edges,
                "addedEdgeIds": mapping_edges,
                "changedEdgeIds": [],
                "codeDiffs": [],
                "verificationRecordIds": [],
                "evidenceRecordIds": [],
                "revisionKind": "record-derived-no-application",
            }
        )
        proposal = proposals_by_work.get(work_id)
        if proposal is None:
            continue
        proposal_node = f"proposal.{proposal['id']}"
        added_node_ids = [item["id"] for item in proposal["graphDelta"]["addedNodes"]]
        changed_node_ids = list(proposal["graphDelta"]["changedNodeIds"])
        diff_node_ids = [item["codeFactId"] for item in proposal["codeDiffs"]]
        proposal_edges = [
            f"edge.work.{work_id}.proposes.{proposal['id']}",
            *[f"edge.{proposal_node}.changes.{item}" for item in changed_node_ids],
            *[f"edge.{proposal_node}.adds.{item}" for item in added_node_ids],
            *[item["id"] for item in proposal["graphDelta"]["addedEdges"]],
        ]
        stages.append(
            {
                "id": f"stage.{work_id}.proposal",
                "workItemId": work_id,
                "sequence": 3,
                "kind": "change-proposal-recorded",
                "title": "Graph and code delta proposed",
                "summary": "A review-required proposal records candidate graph changes and code diff fragments. It has not been applied.",
                "status": proposal["applicationStatus"],
                "recordIds": [f"history.proposal.{work_id}"],
                "nodeIds": [work_node, intent_id, mapping_node, proposal_node, *added_node_ids, *changed_node_ids, *diff_node_ids],
                "addedNodeIds": [proposal_node, *added_node_ids],
                "changedNodeIds": changed_node_ids,
                "contextNodeIds": list(mapping["codeFactIds"]),
                "edgeIds": proposal_edges,
                "addedEdgeIds": proposal_edges,
                "changedEdgeIds": [],
                "codeDiffs": list(proposal["codeDiffs"]),
                "verificationRecordIds": [],
                "evidenceRecordIds": [],
                "revisionKind": "proposal-only-not-applied",
            }
        )
        requirement_verification = f"verification.verification.requirements.{proposal['id']}"
        requirement_evidence = f"evidence.evidence.requirements.{proposal['id']}"
        stages.append(
            {
                "id": f"stage.{work_id}.requirements",
                "workItemId": work_id,
                "sequence": 4,
                "kind": "verification-and-evidence-requirements-recorded",
                "title": "Verification and evidence requirements",
                "summary": "Required verification and evidence are visible before any code or graph delta can be considered accepted.",
                "status": "requirements-recorded",
                "recordIds": [f"verification.requirements.{proposal['id']}", f"evidence.requirements.{proposal['id']}"],
                "nodeIds": [proposal_node, requirement_verification, requirement_evidence],
                "addedNodeIds": [requirement_verification, requirement_evidence],
                "changedNodeIds": [],
                "contextNodeIds": [work_node, *diff_node_ids],
                "edgeIds": [f"edge.project.{state['project']['id']}.verified-by.verification.requirements.{proposal['id']}", f"edge.project.{state['project']['id']}.evidenced-by.evidence.requirements.{proposal['id']}"],
                "addedEdgeIds": [f"edge.project.{state['project']['id']}.verified-by.verification.requirements.{proposal['id']}", f"edge.project.{state['project']['id']}.evidenced-by.evidence.requirements.{proposal['id']}"],
                "changedEdgeIds": [],
                "codeDiffs": list(proposal["codeDiffs"]),
                "verificationRecordIds": [requirement_verification],
                "evidenceRecordIds": [requirement_evidence],
                "revisionKind": "requirement-recorded-not-executed",
            }
        )
        for receipt_index, receipt in enumerate(sorted(receipts_by_proposal.get(proposal["id"], []), key=lambda item: item["id"]), start=5):
            receipt_node = f"review-receipt.{receipt['id']}"
            verification_node = f"verification.verification.review-receipt.{receipt['id']}"
            evidence_node = f"evidence.evidence.review-receipt.{receipt['id']}"
            stages.append(
                {
                    "id": f"stage.{work_id}.review-receipt.{receipt['id']}",
                    "workItemId": work_id,
                    "sequence": receipt_index,
                    "kind": "review-receipt-recorded",
                    "title": "Review receipt recorded",
                    "summary": "A human review outcome was recorded. It is not runtime evidence, an approval, or application of the proposal.",
                    "status": receipt["result"],
                    "recordIds": [f"history.review-receipt.{receipt['id']}"],
                    "nodeIds": [proposal_node, receipt_node, verification_node, evidence_node],
                    "addedNodeIds": [receipt_node, verification_node, evidence_node],
                    "changedNodeIds": [],
                    "contextNodeIds": [work_node, *diff_node_ids],
                    "edgeIds": [f"edge.{proposal_node}.reviewed-by.{receipt['id']}", f"edge.{receipt_node}.records-verification.{receipt['id']}", f"edge.{receipt_node}.records-evidence.{receipt['id']}"],
                    "addedEdgeIds": [f"edge.{proposal_node}.reviewed-by.{receipt['id']}", f"edge.{receipt_node}.records-verification.{receipt['id']}", f"edge.{receipt_node}.records-evidence.{receipt['id']}"],
                    "changedEdgeIds": [],
                    "codeDiffs": list(proposal["codeDiffs"]),
                    "verificationRecordIds": [verification_node],
                    "evidenceRecordIds": [evidence_node],
                    "revisionKind": "human-review-record-not-approval",
                }
            )
    return stages


def build_projection(project_workspace: Path) -> tuple[dict[str, Any], list[dict[str, str]]]:
    state, snapshot_manifest, snapshot_artifacts, data = validate_project_workspace(project_workspace)
    facts_document = data["facts"]
    proposals = data["proposals"]
    raw_facts = facts_document.get("facts")
    raw_relations = facts_document.get("relations")
    if not isinstance(raw_facts, list) or not isinstance(raw_relations, list):
        raise ProjectWorkspaceError("nested snapshot facts are incomplete")
    nodes = [code_node(fact) for fact in raw_facts if isinstance(fact, dict)]
    if len(nodes) != len(raw_facts) or not nodes or any(node["kind"] not in ALLOWED_FACT_KINDS for node in nodes):
        raise ProjectWorkspaceError("nested snapshot fact kinds are invalid")
    if any(not safe_relative_source(node["source"]["file"]) for node in nodes):
        raise ProjectWorkspaceError("nested snapshot contains unsafe source references")
    node_ids = {node["id"] for node in nodes}
    code_diffs_by_fact: dict[str, list[dict[str, Any]]] = {}
    changed_node_ids: set[str] = set()
    for proposal in proposals:
        changed_node_ids.update(proposal["graphDelta"]["changedNodeIds"])
        for diff in proposal["codeDiffs"]:
            code_diffs_by_fact.setdefault(diff["codeFactId"], []).append({**diff, "proposalId": proposal["id"], "proposalTitle": proposal["title"]})
    for node in nodes:
        if node["id"] in changed_node_ids:
            node["deltaState"] = "proposed-change"
        node["codeDiffs"] = sorted(code_diffs_by_fact.get(node["id"], []), key=lambda item: item["id"])
    edges: list[dict[str, Any]] = []
    for relation in raw_relations:
        if not isinstance(relation, dict) or relation.get("kind") not in ALLOWED_RELATION_KINDS:
            raise ProjectWorkspaceError("nested snapshot relation kinds are invalid")
        if relation.get("from") not in node_ids or relation.get("to") not in node_ids:
            raise ProjectWorkspaceError("nested snapshot relation endpoint does not resolve")
        edges.append(
            {
                "id": relation["id"],
                "category": "code-relation",
                "kind": relation["kind"],
                "source": relation["from"],
                "target": relation["to"],
                "details": {"interpretation": relation_interpretation(str(relation["kind"])), "confidence": "ambiguous" if relation["kind"] == "invokes-syntax" else "extracted"},
            }
        )
    semantic_relation_overlay = data["semanticRelationOverlay"]
    if semantic_relation_overlay["status"] == "recorded":
        for relation in semantic_relation_overlay["relations"]:
            edges.append(
                {
                    "id": relation["id"],
                    "category": "code-relation",
                    "kind": relation["kind"],
                    "source": relation["from"],
                    "target": relation["to"],
                    "details": {
                        "interpretation": resolved_relation_interpretation(relation["kind"]),
                        "confidence": relation["confidence"],
                        "resolution": "local-symbol-only",
                        "sourceArtifactDigest": semantic_relation_overlay["sourceArtifactDigest"],
                    },
                }
            )
    project = state["project"]
    project_node = f"project.{project['id']}"
    nodes.append(semantic_node(project_node, "project", project["title"], {"logicalSourceRoot": project["logicalSourceRoot"], "sourceDigest": project["sourceDigest"], "sourceRole": project["sourceRole"]}))
    semantic_foundation = data["semanticFoundation"]
    if semantic_foundation["status"] == "recorded":
        document_nodes: dict[str, str] = {}
        for document in semantic_foundation["sourceDocuments"]:
            node_id = f"source-document.{document['id']}"
            document_nodes[document["id"]] = node_id
            nodes.append(semantic_node(node_id, "source-document", document["title"], {**document, "declarationStatus": "declared"}))
            edges.append({"id": f"edge.{project_node}.documents.{document['id']}", "category": "semantic-relation", "kind": "documents", "source": project_node, "target": node_id, "details": {"role": document["role"], "declarationStatus": "declared"}})
        for goal in semantic_foundation["goals"]:
            node_id = f"goal.{goal['id']}"
            nodes.append(semantic_node(node_id, "goal", goal["title"], {**goal, "declarationStatus": "declared"}))
            edges.append({"id": f"edge.{project_node}.pursues.{goal['id']}", "category": "semantic-relation", "kind": "pursues", "source": project_node, "target": node_id, "details": {"declarationStatus": "declared"}})
            for source_id in goal["sourceDocumentIds"]:
                edges.append({"id": f"edge.{document_nodes[source_id]}.declares.{goal['id']}", "category": "semantic-relation", "kind": "declares", "source": document_nodes[source_id], "target": node_id, "details": {"declarationStatus": "declared"}})
            for capability_id in goal["capabilityIds"]:
                edges.append({"id": f"edge.{node_id}.includes.{capability_id}", "category": "semantic-relation", "kind": "includes", "source": node_id, "target": f"capability.{capability_id}", "details": {"declarationStatus": "declared"}})
        for capability in semantic_foundation["capabilities"]:
            node_id = f"capability.{capability['id']}"
            nodes.append(semantic_node(node_id, "capability", capability["title"], {**capability, "declarationStatus": "declared"}))
            for source_id in capability["sourceDocumentIds"]:
                edges.append({"id": f"edge.{document_nodes[source_id]}.declares.{capability['id']}", "category": "semantic-relation", "kind": "declares", "source": document_nodes[source_id], "target": node_id, "details": {"declarationStatus": "declared"}})
        for constraint in semantic_foundation["constraints"]:
            node_id = f"constraint.{constraint['id']}"
            nodes.append(semantic_node(node_id, "constraint", constraint["title"], {**constraint, "declarationStatus": "declared"}))
            edges.append({"id": f"edge.{project_node}.constrained-by.{constraint['id']}", "category": "semantic-relation", "kind": "constrained-by", "source": project_node, "target": node_id, "details": {"declarationStatus": "declared"}})
            for source_id in constraint["sourceDocumentIds"]:
                edges.append({"id": f"edge.{document_nodes[source_id]}.declares.{constraint['id']}", "category": "semantic-relation", "kind": "declares", "source": document_nodes[source_id], "target": node_id, "details": {"declarationStatus": "declared"}})
        for requirement in semantic_foundation["verificationRequirements"]:
            node_id = f"verification-requirement.{requirement['id']}"
            nodes.append(semantic_node(node_id, "verification-requirement", requirement["title"], {**requirement, "declarationStatus": "declared"}))
            edges.append({"id": f"edge.{project_node}.requires.{requirement['id']}", "category": "semantic-relation", "kind": "requires", "source": project_node, "target": node_id, "details": {"declarationStatus": "declared"}})
            for source_id in requirement["sourceDocumentIds"]:
                edges.append({"id": f"edge.{document_nodes[source_id]}.declares.{requirement['id']}", "category": "semantic-relation", "kind": "declares", "source": document_nodes[source_id], "target": node_id, "details": {"declarationStatus": "declared"}})
    for item in state["workItems"]:
        work_node = f"work.{item['id']}"
        nodes.append(semantic_node(work_node, "work", item["title"], item))
        nodes.append(semantic_node(item["intentUnitId"], "intent", item["title"], {"request": item["request"], "mappingStatus": item["mappingStatus"], "changeStatus": item["changeStatus"], "verificationStatus": item["verificationStatus"]}))
        edges.append({"id": f"edge.{project_node}.tracks.{item['id']}", "category": "semantic-relation", "kind": "tracks", "source": project_node, "target": work_node, "details": {"state": item["status"]}})
        edges.append({"id": f"edge.{item['id']}.expresses.{item['intentUnitId']}", "category": "semantic-relation", "kind": "expresses", "source": work_node, "target": item["intentUnitId"], "details": {"state": item["mappingStatus"]}})
    for mapping in state["mappings"]:
        mapping_node = f"mapping.{mapping['id']}"
        nodes.append(semantic_node(mapping_node, "mapping", mapping["id"], mapping))
        edges.append({"id": f"edge.{mapping_node}.for.{mapping['intentUnitId']}", "category": "semantic-relation", "kind": "maps", "source": mapping_node, "target": mapping["intentUnitId"], "details": {"status": mapping["status"], "confidence": mapping["confidence"]}})
        for fact_id in mapping["codeFactIds"]:
            edges.append({"id": f"edge.{mapping_node}.to.{fact_id}", "category": "mapping-relation", "kind": "maps-to", "source": mapping_node, "target": fact_id, "details": {"status": "candidate", "confidence": "declared"}})
    proposal_deltas: list[dict[str, Any]] = []
    for proposal in proposals:
        proposal_node = f"proposal.{proposal['id']}"
        nodes.append(
            semantic_node(
                proposal_node,
                "proposal",
                proposal["title"],
                {
                    "summary": proposal["summary"],
                    "applicationStatus": proposal["applicationStatus"],
                    "workItemId": proposal["workItemId"],
                    "mappingId": proposal["mappingId"],
                    "verificationRequirementCount": len(proposal["verificationRequirements"]),
                    "evidenceRequirementCount": len(proposal["evidenceRequirements"]),
                },
            )
        )
        edges.append({"id": f"edge.work.{proposal['workItemId']}.proposes.{proposal['id']}", "category": "semantic-relation", "kind": "proposes", "source": f"work.{proposal['workItemId']}", "target": proposal_node, "details": {"status": proposal["applicationStatus"]}})
        for changed_id in proposal["graphDelta"]["changedNodeIds"]:
            edges.append({"id": f"edge.{proposal_node}.changes.{changed_id}", "category": "delta-relation", "kind": "changes", "source": proposal_node, "target": changed_id, "details": {"proposalId": proposal["id"], "deltaState": "proposed-change"}})
            proposal_deltas.append({"id": f"delta.{proposal['id']}.change.{changed_id}", "proposalId": proposal["id"], "kind": "change-existing-node", "label": f"Change {changed_id}", "targetNodeId": changed_id, "details": {"deltaState": "proposed-change"}})
        for added in proposal["graphDelta"]["addedNodes"]:
            nodes.append(semantic_node(added["id"], added["category"], added["label"], {**added["details"], "deltaState": "proposed-addition", "proposalId": proposal["id"]}))
            edges.append({"id": f"edge.{proposal_node}.adds.{added['id']}", "category": "delta-relation", "kind": "adds", "source": proposal_node, "target": added["id"], "details": {"proposalId": proposal["id"], "deltaState": "proposed-addition"}})
            proposal_deltas.append({"id": f"delta.{proposal['id']}.add.{added['id']}", "proposalId": proposal["id"], "kind": "add-node", "label": f"Add {added['label']}", "targetNodeId": added["id"], "details": {"deltaState": "proposed-addition"}})
        for added_edge in proposal["graphDelta"]["addedEdges"]:
            edges.append({**added_edge, "category": "delta-relation"})
        for diff in proposal["codeDiffs"]:
            proposal_deltas.append({"id": f"delta.{proposal['id']}.diff.{diff['id']}", "proposalId": proposal["id"], "kind": "code-diff", "label": f"Review code diff for {diff['sourceFile']}", "targetNodeId": diff["codeFactId"], "details": {"codeDiffId": diff["id"], "sourceFile": diff["sourceFile"]}})
    for record in state["verification"]:
        node_id = f"verification.{record['id']}"
        nodes.append(semantic_node(node_id, "verification", record["kind"], record))
        edges.append({"id": f"edge.{project_node}.verified-by.{record['id']}", "category": "semantic-relation", "kind": "verified-by", "source": project_node, "target": node_id, "details": {"result": record["result"]}})
    for record in state["evidence"]:
        node_id = f"evidence.{record['id']}"
        nodes.append(semantic_node(node_id, "evidence", record["kind"], record))
        edges.append({"id": f"edge.{project_node}.evidenced-by.{record['id']}", "category": "semantic-relation", "kind": "evidenced-by", "source": project_node, "target": node_id, "details": {"result": record["result"]}})
    for receipt in data["reviewReceipts"]:
        receipt_node = f"review-receipt.{receipt['id']}"
        verification_node = f"verification.verification.review-receipt.{receipt['id']}"
        evidence_node = f"evidence.evidence.review-receipt.{receipt['id']}"
        if verification_node not in {node["id"] for node in nodes} or evidence_node not in {node["id"] for node in nodes}:
            raise ProjectWorkspaceError("review receipt projection records are incomplete")
        proposal_node = f"proposal.{receipt['proposalId']}"
        nodes.append(semantic_node(receipt_node, "review-receipt", receipt["id"], receipt))
        edges.append({"id": f"edge.{proposal_node}.reviewed-by.{receipt['id']}", "category": "semantic-relation", "kind": "reviewed-by", "source": proposal_node, "target": receipt_node, "details": {"result": receipt["result"], "authority": "non-executing-non-approving"}})
        edges.append({"id": f"edge.{receipt_node}.records-verification.{receipt['id']}", "category": "semantic-relation", "kind": "records-verification", "source": receipt_node, "target": verification_node, "details": {"requirementId": receipt["verificationRequirementId"]}})
        edges.append({"id": f"edge.{receipt_node}.records-evidence.{receipt['id']}", "category": "semantic-relation", "kind": "records-evidence", "source": receipt_node, "target": evidence_node, "details": {"requirementId": receipt["evidenceRequirementId"]}})
    authority_node = "authority.project-boundary"
    nodes.append(semantic_node(authority_node, "authority", "Read-only authority boundary", state["authority"]))
    edges.append({"id": f"edge.{project_node}.governed-by.authority", "category": "semantic-relation", "kind": "governed-by", "source": project_node, "target": authority_node, "details": {"targetRepositoryMutation": False, "automaticCodeApplication": False}})
    for record in state["history"]:
        node_id = f"history.{record['id']}"
        nodes.append(semantic_node(node_id, "history", record["kind"], record))
        edges.append({"id": f"edge.{project_node}.recorded-by.{record['id']}", "category": "semantic-relation", "kind": "recorded-by", "source": project_node, "target": node_id, "details": {}})
    code_nodes = [node for node in nodes if node["category"] == "code"]
    code_by_id = {node["id"]: node for node in code_nodes}
    capsule_members: dict[str, set[str]] = {}
    for node in code_nodes:
        capsule_label = str(node["source"]["file"]).split("/", 1)[0]
        capsule_members.setdefault(capsule_label, set()).add(node["id"])
    capsule_ids: dict[str, str] = {}
    for capsule_label, members in sorted(capsule_members.items()):
        capsule_id = "capsule." + capsule_label.lower().replace(".", "-")
        capsule_ids[capsule_label] = capsule_id
        source_files = {code_by_id[member]["source"]["file"] for member in members}
        nodes.append(
            semantic_node(
                capsule_id,
                "code-capsule",
                capsule_label,
                {
                    "representation": "derived-code-capsule",
                    "factCount": len(members),
                    "sourceFileCount": len(source_files),
                    "summary": "Aggregated code-fact capsule used only for project and active-work overview navigation.",
                },
            )
        )
        edges.append({"id": f"edge.{project_node}.contains-code.{capsule_id}", "category": "capsule-relation", "kind": "contains-code", "source": project_node, "target": capsule_id, "details": {"factCount": len(members), "sourceFileCount": len(source_files)}})
    for mapping in state["mappings"]:
        mapping_node = f"mapping.{mapping['id']}"
        mapped_capsules = {
            capsule_ids[str(code_by_id[fact_id]["source"]["file"]).split("/", 1)[0]]
            for fact_id in mapping["codeFactIds"]
        }
        for capsule_id in sorted(mapped_capsules):
            edges.append({"id": f"edge.{mapping_node}.to-capsule.{capsule_id}", "category": "mapping-relation", "kind": "maps-to-capsule", "source": mapping_node, "target": capsule_id, "details": {"status": "candidate", "representation": "aggregated-code-scope"}})
    if semantic_foundation["status"] == "recorded":
        for capability in semantic_foundation["capabilities"]:
            source = f"capability.{capability['id']}"
            for label in capability["codeCapsuleLabels"]:
                edges.append({"id": f"edge.{source}.scopes.{label}", "category": "semantic-relation", "kind": "scopes", "source": source, "target": capsule_ids[label], "details": {"declarationStatus": "declared"}})
        for requirement in semantic_foundation["verificationRequirements"]:
            source = f"verification-requirement.{requirement['id']}"
            for label in requirement["codeCapsuleLabels"]:
                edges.append({"id": f"edge.{source}.covers.{label}", "category": "semantic-relation", "kind": "covers", "source": source, "target": capsule_ids[label], "details": {"declarationStatus": "declared"}})
    all_ids = {node["id"] for node in nodes}
    if len(all_ids) != len(nodes) or len({edge["id"] for edge in edges}) != len(edges) or any(edge["source"] not in all_ids or edge["target"] not in all_ids for edge in edges):
        raise ProjectWorkspaceError("project projection graph integrity is invalid")
    edge_ids = {edge["id"] for edge in edges}
    work_stage_timeline = build_work_stage_timeline(state, proposals=proposals, review_receipts=data["reviewReceipts"])
    for stage in work_stage_timeline:
        if (
            not stage["nodeIds"]
            or any(node_id not in all_ids for node_id in stage["nodeIds"])
            or any(edge_id not in edge_ids for edge_id in stage["edgeIds"])
            or any(node_id not in all_ids for node_id in stage["addedNodeIds"] + stage["changedNodeIds"] + stage["contextNodeIds"])
            or any(edge_id not in edge_ids for edge_id in stage["addedEdgeIds"] + stage["changedEdgeIds"])
        ):
            raise ProjectWorkspaceError("work stage timeline does not resolve projected graph records")
    summary = data["summary"]
    resolved_relation_count = len(semantic_relation_overlay["relations"])
    resolved_cross_module_relation_count = sum(
        1
        for relation in semantic_relation_overlay["relations"]
        if relation["from"] in code_by_id
        and relation["to"] in code_by_id
        and str(code_by_id[relation["from"]]["source"]["file"]).split("/", 1)[0]
        != str(code_by_id[relation["to"]]["source"]["file"]).split("/", 1)[0]
    )
    base_semantic_node_ids = {node["id"] for node in nodes if node["category"] not in {"code", "code-capsule"}}
    mapped_code_ids = {fact_id for mapping in state["mappings"] for fact_id in mapping["codeFactIds"]}
    impacted_code_ids = set(mapped_code_ids) | changed_node_ids
    # Active-work navigation walks only upward through containment. Following invocation
    # children would turn a three-method proposal back into a raw-code hairball.
    for _ in range(4):
        parents = {
            edge["source"]
            for edge in edges
            if edge["category"] == "code-relation" and edge["kind"] == "contains" and edge["target"] in impacted_code_ids
        }
        before_count = len(impacted_code_ids)
        impacted_code_ids.update(parents)
        if len(impacted_code_ids) == before_count:
            break
    impacted_capsule_ids = {
        capsule_ids[str(code_by_id[node_id]["source"]["file"]).split("/", 1)[0]]
        for node_id in impacted_code_ids
        if node_id in code_by_id
    }
    structural_code_ids = {node["id"] for node in code_nodes if node["kind"] in {"file", "namespace", "type"}}
    projection = {
        "artifactRole": "intentgraph-experimental-csharp-project-workbench-projection",
        "status": "intentgraph-experimental-csharp-project-workbench-projection-emitted",
        "scope": WORKBENCH_SCOPE,
        "version": WORKBENCH_VERSION,
        "mode": "experimental-csharp-semantic-overlay-project-workbench",
        "project": project,
        "snapshot": {
            "workspaceRole": snapshot_manifest["artifactRole"],
            "profileId": snapshot_manifest["profile"]["id"],
            "logicalSourceRoot": snapshot_manifest["source"]["logicalId"],
            "sourceDigest": snapshot_manifest["source"]["digest"],
            "sourceFileCount": summary["sourceFileCount"],
            "factCount": summary["factCount"],
            "relationCount": summary["relationCount"],
            "semanticResolution": False,
            "semanticRelationOverlay": {
                "status": semantic_relation_overlay["status"],
                "resolvedRelationCount": resolved_relation_count,
                "resolvedCrossModuleRelationCount": resolved_cross_module_relation_count,
                "compilationErrorCount": semantic_relation_overlay["diagnostics"]["compilationErrorCount"] if semantic_relation_overlay["diagnostics"] else 0,
                "compilationWarningCount": semantic_relation_overlay["diagnostics"]["compilationWarningCount"] if semantic_relation_overlay["diagnostics"] else 0,
                "resolutionScope": "local-symbol-only" if semantic_relation_overlay["status"] == "recorded" else "not-recorded",
            },
            "externalSourcePathPersisted": False,
            "codeContentShown": False,
            "proposedCodeDiffFragmentsShown": any(proposal["codeDiffs"] for proposal in proposals),
        },
        "workflow": {
            **{key: state[key] for key in ("workItems", "mappings", "verification", "evidence", "history")},
            "reviewReceipts": data["reviewReceipts"],
            "semanticFoundation": semantic_foundation,
            "changeProposals": proposals,
            "proposalDeltas": sorted(proposal_deltas, key=lambda item: item["id"]),
            "workStageTimeline": work_stage_timeline,
            "timelineContract": {
                "kind": "record-derived-work-stage-timeline",
                "immutableRecordsRequired": True,
                "automaticApplication": False,
                "targetRepositoryMutation": False,
            },
        },
        "authority": state["authority"],
        "graph": {
            "nodes": sorted(nodes, key=lambda item: item["id"]),
            "edges": sorted(edges, key=lambda item: item["id"]),
            "categoryCounts": counts(nodes, "category"),
            "relationCounts": counts(edges, "kind"),
            "defaultView": {
                "id": "all",
                "codeKinds": ["file", "namespace", "type"],
                "semanticCategories": ["project", "source-document", "goal", "capability", "constraint", "verification-requirement", "work", "intent", "mapping", "proposal", "verification", "evidence", "review-receipt", "authority", "history", "code-capsule"],
                "rendering": "full-graph-progressive-detail",
                "layout": "deterministic-relation-aware-community-preset",
                "physicsLayoutOnLoad": False,
            },
            "views": {
                "overview": {"title": "Project overview", "nodeIds": sorted(base_semantic_node_ids | set(capsule_ids.values())), "summary": "Declared project goals, capabilities, constraints, verification requirements, work, Intent, evidence, authority, history, and aggregated code capsules."},
                "impact": {"title": "Active work impact", "nodeIds": sorted(base_semantic_node_ids | impacted_code_ids | impacted_capsule_ids), "summary": "Active semantic work records plus mapped and proposed code facts with direct syntax neighbors."},
                "code": {"title": "Code topology", "nodeIds": sorted(structural_code_ids | set(capsule_ids.values()) | {project_node}), "summary": "Aggregated code capsules and structural facts, laid out from the recorded local-symbol relation overlay when available."},
                "all": {"title": "Full project graph", "nodeIds": sorted(all_ids), "summary": "Every projected semantic and code fact is loaded. Primary semantic nodes stay labeled; supporting and code-fact labels appear on demand while syntax facts and recorded local-symbol relations reveal progressively as you zoom."},
            },
        },
        "changeReview": (
            {
                "status": "review-required",
                "summary": f"{len(proposals)} non-applied change proposal(s) record {len(proposal_deltas)} graph delta step(s) and {sum(len(item['codeDiffs']) for item in proposals)} code diff(s).",
                "graphDeltaShown": True,
                "codeDiffShown": any(proposal["codeDiffs"] for proposal in proposals),
                "reason": "These are review artifacts only. No graph or source change has been applied.",
            }
            if proposals
            else {
                "status": "not-recorded",
                "summary": "No change proposal, graph delta, or code diff has been recorded for this project workspace.",
                "graphDeltaShown": False,
                "codeDiffShown": False,
                "reason": "A work request may be mapped to code facts, but a separate deterministic proposal is required before changes or diffs exist.",
            }
        ),
        "uiContract": {
            "staticLocalHtml": True,
            "graphLibrary": "cytoscape",
            "networkRequired": False,
            "externalRuntimeUrlsAllowed": False,
            "staticGraphMutationFromUi": False,
            "loopbackProjectStateMutationFromUi": True,
            "loopbackReviewProposalIntakeFromUi": True,
            "loopbackGuidedReviewProposalFromUi": True,
            "loopbackReviewReceiptIntakeFromUi": True,
            "loopbackGuidedReviewReceiptFromUi": True,
            "targetRepositoryMutationFromUi": False,
            "approvalControlsPresent": False,
            "fullGraphDefault": True,
            "allNodesLoaded": True,
            "allEdgesLoaded": True,
            "progressiveDetail": True,
            "viewportScaleCompensation": True,
            "relationAwareCommunityLayout": True,
            "zoomStyleBuckets": True,
            "supportingNodeLabelsOnDemand": True,
            "workStageTimeline": True,
            "physicsLayoutOnLoad": False,
        },
    }
    snapshot_records = [{"path": path.relative_to(project_workspace).as_posix(), "sha256": file_digest(path)} for path in sorted(project_workspace.rglob("*")) if path.is_file() and not path.is_symlink()]
    return projection, snapshot_records


def output_paths(output: Path) -> dict[str, Path]:
    return {
        "index": output / "index.html",
        "projection": output / "projection.json",
        "manifest": output / "manifest.json",
        "validation": output / "validation-report.json",
        "cytoscape": output / "assets" / "cytoscape.min.js",
        "license": output / "assets" / "cytoscape-license.txt",
    }


def html_data(projection: dict[str, Any]) -> str:
    return json.dumps(projection, ensure_ascii=True, sort_keys=True, separators=(",", ":")).replace("</", "<\\/")


HTML_TEMPLATE = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>IntentGraph Project Workbench</title>
  <script src="assets/cytoscape.min.js"></script>
  <style>
    :root { --left:286px; --right:356px; --void:#070914; --panel:#101322; --panel2:#121526; --line:#2a3145; --text:#edf1f8; --muted:#9ba7bc; --accent:#65c4d6; --pink:#e985ad; --violet:#9d8cdc; --warn:#e5bc62; --danger:#df7873; --code:#5f7f99; --intent:#d99855; --work:#62ae91; --evidence:#a18ad0; --history:#8295b4; --proposal:#df7873; }
    * { box-sizing:border-box; } body { margin:0; background:var(--void); color:var(--text); font:13px/1.45 Inter,Segoe UI,Arial,sans-serif; letter-spacing:0; overflow:hidden; }
    button,input,select { font:inherit; } button { color:var(--text); background:#161b2a; border:1px solid #323b52; border-radius:4px; padding:6px 9px; cursor:pointer; transition:border-color 120ms ease,background 120ms ease,box-shadow 120ms ease; } button:hover,button.active { border-color:var(--accent); background:#1a2634; box-shadow:0 0 0 1px rgba(101,196,214,.12); } input,select { width:100%; color:var(--text); background:#0b0f1a; border:1px solid #323b52; border-radius:4px; padding:7px 8px; }
    .app { height:100vh; display:grid; grid-template-rows:54px 1fr; } .topbar { display:flex; align-items:center; justify-content:space-between; padding:0 16px; border-bottom:1px solid var(--line); background:#0c0f1a; box-shadow:0 1px 10px rgba(0,0,0,.18); } .brand { display:flex; align-items:baseline; gap:9px; } .brand strong { color:#fbfcff; font-size:15px; letter-spacing:.4px; } .brand span { color:var(--muted); } .badges { display:flex; gap:6px; } .badge { color:#bbc6d6; border:1px solid #3a455b; padding:3px 7px; border-radius:99px; font-size:11px; } .badge.accent { color:#9bdfeb; border-color:#397884; }
    .workspace { min-height:0; display:grid; grid-template-columns:var(--left) 7px minmax(440px,1fr) 7px var(--right); } .rail,.inspector { overflow:auto; background:var(--panel2); } .rail { border-right:1px solid var(--line); } .inspector { border-left:1px solid var(--line); } .resizer { background:#161b2a; cursor:col-resize; position:relative; } .resizer:hover,.resizer.active { background:var(--accent); box-shadow:0 0 10px rgba(101,196,214,.2); } .section { padding:14px; border-bottom:1px solid var(--line); } h2 { margin:0 0 9px; font-size:11px; text-transform:uppercase; color:#b6c4d9; letter-spacing:.8px; } h3 { margin:0 0 7px; font-size:15px; } p { margin:5px 0; color:#c7d0dd; } label { display:block; margin:8px 0 4px; color:var(--muted); font-size:11px; } .modes { display:grid; grid-template-columns:1fr 1fr; gap:5px; } .modes button:last-child { grid-column:span 2; }
    .work-list,.stage-list { display:grid; gap:7px; } .work-card { text-align:left; padding:9px; background:#151320; } .work-card small { display:block; color:var(--muted); margin-top:3px; } .work-card .state { display:block; color:#92fff0; text-transform:uppercase; font-size:10px; letter-spacing:.5px; } .work-card.unmapped .state { color:var(--warn); } .stage-card { text-align:left; padding:8px 9px; background:#101725; border-left:2px solid #466b8a; } .stage-card:hover,.stage-card.active { border-left-color:#92fff0; } .stage-card .stage-meta { display:flex; justify-content:space-between; gap:8px; color:#a7b9c9; font-size:10px; text-transform:uppercase; letter-spacing:.4px; } .stage-card strong,.stage-card small { display:block; } .stage-card strong { margin-top:2px; color:#e5edf6; } .stage-card small { margin-top:2px; color:var(--muted); } .stage-card .stage-delta { color:#9ce0e8; } .empty { color:var(--muted); font-style:italic; padding:7px 0; } .metrics { display:grid; grid-template-columns:1fr 1fr; gap:7px; } .metric { padding:8px; border:1px solid var(--line); background:#0a0910; } .metric strong { color:#fff; display:block; font-size:16px; } .metric span { color:var(--muted); font-size:11px; }
    .canvas { min-width:0; min-height:0; display:grid; grid-template-rows:68px minmax(0,1fr) 174px; background:#080b14; } .canvasbar { display:flex; align-items:center; justify-content:space-between; padding:12px 16px; border-bottom:1px solid var(--line); background:#0d111d; } h1 { margin:0; font-size:16px; } .canvasbar p { font-size:11px; margin:2px 0 0; color:var(--muted); } .tools { display:flex; gap:5px; } .icon { min-width:32px; } #projectGraph { min-height:0; background:radial-gradient(ellipse at 48% 47%,rgba(38,69,97,.2),transparent 48%),radial-gradient(ellipse at 22% 76%,rgba(45,42,80,.12),transparent 42%),#080b14; } .review-tray { border-top:1px solid var(--line); display:grid; grid-template-columns:1.2fr 1fr 1fr; overflow:auto; background:#0d111d; } .tray-section { padding:12px; border-right:1px solid var(--line); } .tray-section:last-child { border-right:0; } .tray-title { color:#b7c8dd; text-transform:uppercase; font-size:10px; letter-spacing:.65px; margin-bottom:6px; } .state-line { color:#c9d2df; } .state-line strong { color:var(--warn); } .detail { padding:8px; background:#141a28; border:1px solid #35405a; border-radius:4px; } .detail + .detail { margin-top:8px; } .kv { display:grid; grid-template-columns:112px 1fr; gap:4px 8px; margin:8px 0 0; } .kv dt { color:var(--muted); } .kv dd { margin:0; overflow-wrap:anywhere; } .status-list { display:grid; gap:6px; } .status-row { display:flex; justify-content:space-between; gap:10px; padding:6px 0; border-bottom:1px solid #293248; } .status-row:last-child { border-bottom:0; } .status-row span:last-child { color:var(--warn); text-align:right; } .boundary { color:#c8d2df; } .boundary strong { color:#9bdfeb; } .legend { display:grid; grid-template-columns:1fr 1fr; gap:6px; color:#ced7e5; } .legend i { width:10px; height:10px; display:inline-block; border-radius:50%; margin-right:5px; } .delta-list { display:grid; gap:4px; margin-top:8px; } .delta-step { width:100%; text-align:left; font-size:11px; padding:5px 7px; } .diff { margin:9px 0 0; padding:9px; overflow:auto; white-space:pre; background:#080b14; border:1px solid #35405a; color:#d8f3ef; font:11px/1.45 Consolas,monospace; }
    @media (max-width: 980px) { :root { --left:240px; --right:300px; } .review-tray { grid-template-columns:1fr; } .canvas { grid-template-rows:68px minmax(0,1fr) 220px; } } @media (max-width: 760px) { body { overflow:auto; } .app { height:auto; min-height:100vh; } .workspace { grid-template-columns:1fr; } .resizer { display:none; } .rail,.inspector { border:0; } .canvas { min-height:560px; } }
  </style>
</head>
<body>
  <div class="app">
    <header class="topbar"><div class="brand"><strong>IntentGraph</strong><span>Project workbench</span></div><div class="badges"><span class="badge accent">local semantic overlay</span><span class="badge" id="projectBadge"></span><span class="badge" id="snapshotBadge"></span></div></header>
    <div class="workspace">
      <aside class="rail">
        <section class="section"><h2>Graph lens</h2><div class="modes"><button class="mode active" data-mode="all">Full graph</button><button class="mode" data-mode="overview">Semantic overview</button><button class="mode" data-mode="impact">Active work</button><button class="mode" data-mode="code">Code topology</button><button class="mode" data-mode="focus">Focus selection</button><button id="clearSelection">Clear focus</button></div></section>
        <section class="section"><h2>Find</h2><label for="search">Node, relation, or source file</label><input id="search" type="search" placeholder="Find project or code fact"><label for="categoryFilter">Node category</label><select id="categoryFilter"></select><label for="relationFilter">Relation kind</label><select id="relationFilter"></select></section>
        <section class="section"><h2>Active work</h2><div id="workList" class="work-list"></div></section>
        <section class="section"><h2>Work stages</h2><div id="stageList" class="stage-list"></div></section>
        <section class="section"><h2>Project snapshot</h2><div id="metrics" class="metrics"></div></section>
        <section class="section"><h2>Legend</h2><div class="legend"><div><i style="background:var(--code)"></i>Code fact</div><div><i style="background:#d6a762"></i>Goal / Intent</div><div><i style="background:#5fb8a5"></i>Capability / work</div><div><i style="background:#7993a8"></i>Source document</div><div><i style="background:var(--evidence)"></i>Evidence / verify</div><div><i style="background:var(--history)"></i>History / authority</div></div></section>
      </aside>
      <div class="resizer" data-side="left" role="separator" aria-label="Resize navigation"></div>
      <main class="canvas">
        <div class="canvasbar"><div><h1 id="graphTitle">Full project graph</h1><p id="graphSummary"></p></div><div class="tools"><button class="icon" id="zoomOut" title="Zoom out">-</button><button class="icon" id="zoomIn" title="Zoom in">+</button><button class="icon" id="fitGraph" title="Fit graph">Fit</button></div></div>
        <div id="projectGraph" aria-label="IntentGraph project graph"></div>
        <section class="review-tray"><div class="tray-section"><div class="tray-title">Change review</div><div id="changePanel"></div><div id="deltaList" class="delta-list"></div></div><div class="tray-section"><div class="tray-title">Verification and evidence</div><div id="evidencePanel"></div></div><div class="tray-section"><div class="tray-title">Authority and history</div><div id="authorityPanel"></div></div></section>
      </main>
      <div class="resizer" data-side="right" role="separator" aria-label="Resize inspector"></div>
      <aside class="inspector"><section class="section"><h2>Selection</h2><div id="selectionInspector" class="empty">Select a node or relation to inspect its semantic and source provenance.</div></section><section class="section"><h2>What this view does not claim</h2><div id="boundaryPanel" class="boundary"></div></section></aside>
    </div>
  </div>
  <script id="workbench-data" type="application/json">__WORKBENCH_DATA__</script>
  <script>
    function boot(model) {
    const allNodes = model.graph.nodes, allEdges = model.graph.edges;
    const nodeById = new Map(allNodes.map(node => [node.id,node]));
    const alwaysLabeledCategories = new Set(['project']);
    const allNodeIds = new Set(allNodes.map(node=>node.id));
    const allEdgeIds = new Set(allEdges.map(edge=>edge.id));
    const completeGraph = {nodes:allNodes,edges:allEdges,nodeIds:allNodeIds,edgeIds:allEdgeIds};
    const semanticNodeIds = new Set(model.graph.views.overview.nodeIds);
    const semanticEdgeIds = new Set(allEdges.filter(edge=>semanticNodeIds.has(edge.source)&&semanticNodeIds.has(edge.target)).map(edge=>edge.id));
    const importantCodeLabelIds = new Set(allNodes.filter(node=>node.category==='code'&&(node.codeDiffs||[]).length>0).map(node=>node.id));
    const emptyIds = new Set();
    const state = { mode:model.graph.defaultView?.id || 'all', selected:null, stageFocus:null, cy:null, renderTimer:null, detailLevel:null, viewportScale:null, positions:null, visibleNodeIds:null, visibleEdgeIds:null, highlighted:null, emphasizedNodeIds:new Set(), emphasizedEdgeIds:new Set(), stageAddedNodeIds:new Set(), stageChangedNodeIds:new Set(), stageEdgeIds:new Set(), searchMatchNodeIds:new Set(), onDemandLabelIds:new Set(), resizeQueued:false, graphInstanceCount:0, visibilityUpdates:0 };
    const colors = { code:'#5f7f99', project:'#75c9d8', 'source-document':'#8197ad', goal:'#dfad62', capability:'#72b798', constraint:'#d8936a', 'verification-requirement':'#a892d0', work:'#72b798', intent:'#dc91ad', mapping:'#d7b56c', proposal:'#de817a', verification:'#a892d0', evidence:'#a892d0', 'review-receipt':'#bc8ce5', authority:'#8297b6', history:'#8297b6' };
    const communityPalette = ['#5c8ec4','#db913d','#dc5e68','#70b5aa','#5da45b','#d7bc4b','#a77ba2','#d882a1','#a77f68','#9a9da8'];
    const safe = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
    const short = value => String(value || '').replace('sha256:','').slice(0,12);
    const rows = entries => `<dl class="kv">${entries.map(([key,value])=>`<dt>${safe(key)}</dt><dd>${safe(value)}</dd>`).join('')}</dl>`;
    function populate(id, values, label) { document.getElementById(id).innerHTML=`<option value="">All ${safe(label)}</option>`+values.map(value=>`<option value="${safe(value)}">${safe(value)}</option>`).join(''); }
    function filters() { return { search:document.getElementById('search').value.trim().toLowerCase(), category:document.getElementById('categoryFilter').value, relation:document.getElementById('relationFilter').value }; }
    function sourceModule(node) { return node.category==='code-capsule' ? node.label : String(node.source?.file||'Unmapped').split('/')[0]; }
    function stableHash(value) { let hash=2166136261; for(let index=0;index<value.length;index+=1){hash^=value.charCodeAt(index);hash=Math.imul(hash,16777619);} return hash>>>0; }
    function nodeColor(node) { return node.category==='code'||node.category==='code-capsule' ? communityPalette[stableHash(sourceModule(node))%communityPalette.length] : (colors[node.category]||'#8fa1b9'); }
    function spiralPoint(index,scale,rotation=0) { const golden=Math.PI*(3-Math.sqrt(5)),radius=scale*Math.sqrt(index+.75),angle=rotation+index*golden; return {x:Math.cos(angle)*radius,y:Math.sin(angle)*radius}; }
    function buildPresetPositions() {
      const positions=new Map(),groups=new Map(),capsules=new Map();
      allNodes.filter(node=>node.category==='code-capsule').forEach(node=>capsules.set(node.label,node));
      allNodes.filter(node=>node.category==='code').forEach(node=>{const group=sourceModule(node);if(!groups.has(group))groups.set(group,[]);groups.get(group).push(node);});
      const orderedGroups=[...groups.entries()].sort((left,right)=>right[1].length-left[1].length||left[0].localeCompare(right[0]));
      const centers=new Map(),groupIndex=new Map(),totalCode=allNodes.filter(node=>node.category==='code').length;
      orderedGroups.forEach(([group],index)=>{groupIndex.set(group,index);const angle=index*Math.PI*2/Math.max(1,orderedGroups.length)+stableHash(group)%97/250;const radius=600+Math.min(240,Math.sqrt(totalCode)*2.1)+(stableHash(group)%71);centers.set(group,{x:Math.cos(angle)*radius,y:Math.sin(angle)*radius});});
      const links=new Map(),linkKey=(left,right)=>left<right?left+'\u001f'+right:right+'\u001f'+left;
      allEdges.forEach(edge=>{if(edge.category!=='code-relation'||!['calls','references','constructs','inherits','implements'].includes(edge.kind))return;const source=nodeById.get(edge.source),target=nodeById.get(edge.target);if(!source||!target||source.category!=='code'||target.category!=='code')return;const left=sourceModule(source),right=sourceModule(target);if(left===right||!groupIndex.has(left)||!groupIndex.has(right))return;const key=linkKey(left,right);links.set(key,(links.get(key)||0)+1);});
      // A small deterministic force pass on module centers uses real local-symbol links.
      // It runs once while building the preset, never during pan or wheel interactions.
      for(let iteration=0;iteration<96;iteration+=1){
        const forces=new Map(orderedGroups.map(([group])=>[group,{x:0,y:0}]));
        for(let leftIndex=0;leftIndex<orderedGroups.length;leftIndex+=1){for(let rightIndex=leftIndex+1;rightIndex<orderedGroups.length;rightIndex+=1){
          const left=orderedGroups[leftIndex][0],right=orderedGroups[rightIndex][0],a=centers.get(left),b=centers.get(right);let dx=b.x-a.x,dy=b.y-a.y,distance=Math.max(1,Math.hypot(dx,dy));dx/=distance;dy/=distance;
          const repulsion=150000/(distance*distance);forces.get(left).x-=dx*repulsion;forces.get(left).y-=dy*repulsion;forces.get(right).x+=dx*repulsion;forces.get(right).y+=dy*repulsion;
          const weight=links.get(linkKey(left,right))||0;if(weight){const targetDistance=430-Math.min(130,Math.log1p(weight)*34),spring=(distance-targetDistance)*(.003+Math.min(.012,weight*.000025));forces.get(left).x+=dx*spring;forces.get(left).y+=dy*spring;forces.get(right).x-=dx*spring;forces.get(right).y-=dy*spring;}
        }}
        orderedGroups.forEach(([group])=>{const point=centers.get(group),force=forces.get(group),distance=Math.max(1,Math.hypot(point.x,point.y));force.x-=point.x/distance*.12;force.y-=point.y/distance*.12;const step=Math.min(11,Math.hypot(force.x,force.y));if(step){point.x+=force.x/Math.hypot(force.x,force.y)*step;point.y+=force.y/Math.hypot(force.x,force.y)*step;}});
      }
      orderedGroups.forEach(([group,nodes])=>{
        const center=centers.get(group),files=new Map();
        nodes.forEach(node=>{const file=String(node.source?.file||'Unmapped');if(!files.has(file))files.set(file,[]);files.get(file).push(node);});
        const fileScale=31+Math.min(30,Math.sqrt(nodes.length)*.82);
        [...files.entries()].sort((left,right)=>left[0].localeCompare(right[0])).forEach(([file,fileNodes],fileIndex)=>{
          const filePoint=spiralPoint(fileIndex,fileScale,stableHash(file)%628/100),fileCenter={x:center.x+filePoint.x,y:center.y+filePoint.y};
          fileNodes.slice().sort((left,right)=>(left.kind+'|'+left.id).localeCompare(right.kind+'|'+right.id)).forEach((node,nodeIndex)=>{
            if(node.kind==='file'){positions.set(node.id,fileCenter);return;}
            const local=spiralPoint(nodeIndex,4.1,stableHash(node.id)%628/100);
            positions.set(node.id,{x:fileCenter.x+local.x,y:fileCenter.y+local.y});
          });
        });
        const capsule=capsules.get(group);if(capsule)positions.set(capsule.id,center);
      });
      const semanticGroups=new Map();
      allNodes.filter(node=>node.category!=='code'&&node.category!=='code-capsule'&&node.category!=='project').forEach(node=>{if(!semanticGroups.has(node.category))semanticGroups.set(node.category,[]);semanticGroups.get(node.category).push(node);});
      [...semanticGroups.entries()].sort((left,right)=>left[0].localeCompare(right[0])).forEach(([category,nodes],categoryIndex)=>{
        const angle=categoryIndex*Math.PI*2/semanticGroups.size+stableHash(category)%61/100;
        const center={x:Math.cos(angle)*(145+(categoryIndex%2)*38),y:Math.sin(angle)*(145+(categoryIndex%2)*38)};
        nodes.slice().sort((left,right)=>left.id.localeCompare(right.id)).forEach((node,nodeIndex)=>{
          const local=spiralPoint(nodeIndex,18,stableHash(node.id)%628/100);
          positions.set(node.id,{x:center.x+local.x,y:center.y+local.y});
        });
      });
      const project=allNodes.find(node=>node.category==='project');if(project)positions.set(project.id,{x:0,y:0});
      return positions;
    }
    function scheduleRender(){window.clearTimeout(state.renderTimer);state.renderTimer=window.setTimeout(()=>renderGraph({fit:false}),100);}
    function init() {
      populate('categoryFilter',Object.keys(model.graph.categoryCounts),'categories');
      populate('relationFilter',Object.keys(model.graph.relationCounts),'relations');
      document.getElementById('search').addEventListener('input',scheduleRender);
      ['categoryFilter','relationFilter'].forEach(id=>document.getElementById(id).addEventListener('change',()=>renderGraph({fit:false})));
      document.querySelectorAll('[data-mode]').forEach(button=>button.addEventListener('click',()=>{
        state.mode=button.dataset.mode;
        state.stageFocus=null;
        document.querySelectorAll('[data-mode]').forEach(item=>item.classList.toggle('active',item===button));
        renderGraph({fit:false});
      }));
      document.getElementById('clearSelection').addEventListener('click',()=>{state.selected=null;state.stageFocus=null;renderGraph({fit:false});renderSelection();});
    }
    function selectedNodes() {
      const f=filters();
      const view=model.graph.views[state.mode]||model.graph.views[model.graph.defaultView.id];
      let allowed=new Set(view.nodeIds);
      if(state.mode==='overview')allowed=new Set(model.graph.views.all.nodeIds);
      let nodes=allNodes.filter(node=>allowed.has(node.id)&&(!f.category||node.category===f.category));
      if(state.mode==='focus'&&(state.selected||state.stageFocus)) {
        const near=new Set(state.stageFocus ? state.stageFocus.nodeIds : [state.selected.id]);
        if(state.stageFocus) state.stageFocus.contextNodeIds.forEach(id=>near.add(id));
        allEdges.forEach(edge=>{if((state.selected&&(edge.id===state.selected.id||edge.source===state.selected.id||edge.target===state.selected.id))||(state.stageFocus&&state.stageFocus.edgeIds.includes(edge.id))){near.add(edge.source);near.add(edge.target);}});
        nodes=nodes.filter(node=>near.has(node.id));
      }
      return nodes;
    }
    function graphElements(nodes,edges) {
      const positions=state.positions||(state.positions=buildPresetPositions());
      return [
        ...nodes.map(node=>({data:{id:node.id,label:node.label,labelMode:alwaysLabeledCategories.has(node.category)?'always':'on-demand',category:node.category,kind:node.kind,deltaState:node.deltaState||'unchanged',color:nodeColor(node),community:node.category==='code'||node.category==='code-capsule'?sourceModule(node):node.category},position:positions.get(node.id)||{x:0,y:0}})),
        ...edges.map(edge=>{const source=nodeById.get(edge.source);return {data:{id:edge.id,source:edge.source,target:edge.target,kind:edge.kind,category:edge.category,color:edge.category==='code-relation'&&source?nodeColor(source):'#718096'}};})
      ];
    }
    function allGraphData(){return {nodes:allNodes,edges:allEdges,elements:graphElements(allNodes,allEdges)};}
    function visibleGraphData() {
      const f=filters();
      if(!f.category&&!f.relation&&(state.mode==='all'||state.mode==='overview'))return completeGraph;
      const nodes=selectedNodes(),ids=new Set(nodes.map(node=>node.id));
      const edges=allEdges.filter(edge=>ids.has(edge.source)&&ids.has(edge.target)&&(!f.relation||edge.kind===f.relation));
      return {nodes,edges,nodeIds:ids,edgeIds:new Set(edges.map(edge=>edge.id))};
    }
    function graphStyle(){return [
      {selector:'node',style:{'shape':'ellipse','background-color':'data(color)','background-opacity':.9,'label':'data(label)','color':'#dce6f2','font-family':'Inter,Segoe UI,Arial,sans-serif','font-weight':500,'font-size':9.5,'text-wrap':'ellipsis','text-max-width':126,'text-valign':'bottom','text-margin-y':5,'width':15,'height':15,'border-width':1,'border-color':'#b9c9d9','border-opacity':.36,'text-outline-width':0}},
      {selector:'node[category = "code"]',style:{'label':'','background-color':'data(color)','background-opacity':.84,'width':2.6,'height':2.6,'opacity':.94,'border-width':0}},
      {selector:'node[category = "code"][kind = "file"]',style:{'width':6.5,'height':6.5,'background-opacity':.95}},
      {selector:'node[category = "code"][kind = "namespace"]',style:{'width':4.3,'height':4.3}},
      {selector:'node[category = "code"][kind = "type"]',style:{'width':5.2,'height':5.2}},
      {selector:'node[category = "code-capsule"]',style:{'background-color':'data(color)','background-opacity':.08,'shape':'ellipse','border-width':1.2,'border-color':'data(color)','border-opacity':.8,'font-size':9,'font-weight':600,'text-max-width':135,'width':23,'height':23,'color':'#c8d8e8'}},
      {selector:'node[labelMode = "on-demand"]',style:{'label':''}},
      {selector:'node.show-on-demand-label',style:{'label':'data(label)','font-size':8.5,'text-max-width':118,'color':'#cfd9e5','text-outline-width':0}},
      {selector:'node.low-detail',style:{'opacity':.46}},
      {selector:'node[deltaState = "proposed-change"]',style:{'border-width':2,'border-color':'#e37c74','border-opacity':1}},
      {selector:'edge',style:{'width':.52,'line-color':'data(color)','curve-style':'straight','opacity':.28}},
      {selector:'edge[category = "code-relation"]',style:{'width':.28,'line-color':'data(color)','opacity':.15}},
      {selector:'edge.low-detail',style:{'opacity':.055}},
      {selector:'edge.detail-edge',style:{'width':.48,'opacity':.28}},
      {selector:'edge[category = "capsule-relation"]',style:{'width':.9,'opacity':.52}},
      {selector:'edge[category = "mapping-relation"]',style:{'line-color':'#d7b56c','line-style':'dashed','width':1.1,'opacity':.75}},
      {selector:'edge[category = "delta-relation"]',style:{'line-color':'#de817a','line-style':'dashed','width':1.1,'opacity':.8}},
      {selector:'edge[kind = "invokes-syntax"]',style:{'line-color':'#8d78c1','line-style':'dashed'}},
      {selector:'.filtered-out',style:{'display':'none'}},
      {selector:'node.semantic-emphasis',style:{'border-width':2,'border-color':'#f0cd75','border-opacity':1,'z-index':97}},
      {selector:'edge.semantic-emphasis',style:{'line-color':'#d7b56c','width':1.1,'opacity':.82,'z-index':96}},
      {selector:'node.stage-added',style:{'border-width':2.3,'border-color':'#70e5d2','border-opacity':1,'z-index':98}},
      {selector:'node.stage-changed',style:{'border-width':2.5,'border-color':'#f0a36d','border-opacity':1,'z-index':98}},
      {selector:'edge.stage-delta',style:{'line-color':'#7de2e9','width':1.35,'opacity':.96,'z-index':97}},
      {selector:'node.search-match',style:{'border-width':2,'border-color':'#8de0e8','border-opacity':1,'z-index':98}},
      {selector:':selected',style:{'border-width':2.4,'border-color':'#aeeaf0','border-opacity':1,'line-color':'#aeeaf0','z-index':99}},
      {selector:'edge.selection-neighbor',style:{'line-color':'#8de0e8','width':1.1,'opacity':.85,'z-index':98}}
    ];}
    function setDifference(left,right){const values=[];left.forEach(value=>{if(!right.has(value))values.push(value);});return values;}
    function updateSemanticEmphasis() {
      const active=state.mode==='overview'&&!filters().search&&!filters().category&&!filters().relation;
      const nextNodes=active?semanticNodeIds:emptyIds;
      const nextEdges=active?semanticEdgeIds:emptyIds;
      const removeNodes=setDifference(state.emphasizedNodeIds,nextNodes),addNodes=setDifference(nextNodes,state.emphasizedNodeIds),removeEdges=setDifference(state.emphasizedEdgeIds,nextEdges),addEdges=setDifference(nextEdges,state.emphasizedEdgeIds);
      state.cy.batch(()=>{removeNodes.forEach(id=>state.cy.$id(id).removeClass('semantic-emphasis'));addNodes.forEach(id=>state.cy.$id(id).addClass('semantic-emphasis'));removeEdges.forEach(id=>state.cy.$id(id).removeClass('semantic-emphasis'));addEdges.forEach(id=>state.cy.$id(id).addClass('semantic-emphasis'));});
      state.emphasizedNodeIds=nextNodes;state.emphasizedEdgeIds=nextEdges;
    }
    function updateStageHighlight() {
      const stage=state.stageFocus,added=stage?new Set(stage.addedNodeIds):emptyIds,changed=stage?new Set(stage.changedNodeIds):emptyIds,edges=stage?new Set(stage.edgeIds):emptyIds;
      const removeAdded=setDifference(state.stageAddedNodeIds,added),addAdded=setDifference(added,state.stageAddedNodeIds),removeChanged=setDifference(state.stageChangedNodeIds,changed),addChanged=setDifference(changed,state.stageChangedNodeIds),removeEdges=setDifference(state.stageEdgeIds,edges),addEdges=setDifference(edges,state.stageEdgeIds);
      state.cy.batch(()=>{removeAdded.forEach(id=>state.cy.$id(id).removeClass('stage-added'));addAdded.forEach(id=>state.cy.$id(id).addClass('stage-added'));removeChanged.forEach(id=>state.cy.$id(id).removeClass('stage-changed'));addChanged.forEach(id=>state.cy.$id(id).addClass('stage-changed'));removeEdges.forEach(id=>state.cy.$id(id).removeClass('stage-delta'));addEdges.forEach(id=>state.cy.$id(id).addClass('stage-delta'));});
      state.stageAddedNodeIds=added;state.stageChangedNodeIds=changed;state.stageEdgeIds=edges;
    }
    function searchMatchIds() { const search=filters().search;if(!search)return new Set();return new Set(allNodes.filter(node=>String(node.label+' '+node.id+' '+node.kind+' '+(node.source?.file||'')).toLowerCase().includes(search)).map(node=>node.id)); }
    function updateSearchHighlights(nextNodes) {
      const removeNodes=setDifference(state.searchMatchNodeIds,nextNodes),addNodes=setDifference(nextNodes,state.searchMatchNodeIds);
      state.cy.batch(()=>{removeNodes.forEach(id=>state.cy.$id(id).removeClass('search-match'));addNodes.forEach(id=>state.cy.$id(id).addClass('search-match'));});
      state.searchMatchNodeIds=nextNodes;
      updateOnDemandLabels();
    }
    function updateOnDemandLabels() {
      if(!state.cy)return;
      const labels=new Set(importantCodeLabelIds);
      if(state.mode==='impact'||state.mode==='focus'){
        allNodes.filter(node=>state.visibleNodeIds?.has(node.id)&&['work','intent','proposal','verification','evidence'].includes(node.category)).forEach(node=>labels.add(node.id));
      }
      state.searchMatchNodeIds.forEach(id=>{const node=nodeById.get(id);if(node&& !alwaysLabeledCategories.has(node.category))labels.add(id);});
      if(state.selected?.type==='node'){const node=nodeById.get(state.selected.id);if(node&& !alwaysLabeledCategories.has(node.category))labels.add(node.id);}
      if(state.mode==='code')allNodes.filter(node=>node.category==='code-capsule').forEach(node=>labels.add(node.id));
      const remove=setDifference(state.onDemandLabelIds||emptyIds,labels),add=setDifference(labels,state.onDemandLabelIds||emptyIds);
      if(remove.length||add.length)state.cy.batch(()=>{remove.forEach(id=>state.cy.$id(id).removeClass('show-on-demand-label'));add.forEach(id=>state.cy.$id(id).addClass('show-on-demand-label'));});
      state.onDemandLabelIds=labels;
    }
    function fitNodes(nodes) {
      if(!nodes.length)return;
      const positions=state.positions||(state.positions=buildPresetPositions());
      let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
      nodes.forEach(node=>{const point=positions.get(node.id)||{x:0,y:0};minX=Math.min(minX,point.x);minY=Math.min(minY,point.y);maxX=Math.max(maxX,point.x);maxY=Math.max(maxY,point.y);});
      const padding=54,width=Math.max(1,state.cy.width()-padding*2),height=Math.max(1,state.cy.height()-padding*2),spanX=Math.max(160,maxX-minX),spanY=Math.max(160,maxY-minY),zoom=Math.max(state.cy.minZoom(),Math.min(state.cy.maxZoom(),Math.min(width/spanX,height/spanY))),centerX=(minX+maxX)/2,centerY=(minY+maxY)/2;
      state.cy.viewport({zoom,pan:{x:state.cy.width()/2-centerX*zoom,y:state.cy.height()/2-centerY*zoom}});
    }
    function applyGraphVisibility(graph,fitRequested,searchMatches) {
      const nodeIds=graph.nodeIds||new Set(graph.nodes.map(node=>node.id)),edgeIds=graph.edgeIds||new Set(graph.edges.map(edge=>edge.id));
      const previousNodes=state.visibleNodeIds,previousEdges=state.visibleEdgeIds;
      if(!previousNodes||!previousEdges){
        state.visibleNodeIds=nodeIds;state.visibleEdgeIds=edgeIds;
      }else if(previousNodes===nodeIds&&previousEdges===edgeIds){
        state.visibleNodeIds=nodeIds;state.visibleEdgeIds=edgeIds;
      }else{
        const nodeChanges=[],edgeChanges=[];
        previousNodes.forEach(id=>{if(!nodeIds.has(id))nodeChanges.push([id,true]);});
        nodeIds.forEach(id=>{if(!previousNodes.has(id))nodeChanges.push([id,false]);});
        previousEdges.forEach(id=>{if(!edgeIds.has(id))edgeChanges.push([id,true]);});
        edgeIds.forEach(id=>{if(!previousEdges.has(id))edgeChanges.push([id,false]);});
        state.cy.batch(()=>{nodeChanges.forEach(([id,hidden])=>state.cy.$id(id).toggleClass('filtered-out',hidden));edgeChanges.forEach(([id,hidden])=>state.cy.$id(id).toggleClass('filtered-out',hidden));});
        state.visibleNodeIds=nodeIds;state.visibleEdgeIds=edgeIds;state.visibilityUpdates+=nodeChanges.length+edgeChanges.length;
      }
      updateSemanticEmphasis();
      updateStageHighlight();
      updateSearchHighlights(searchMatches);
      if(fitRequested){const semanticFocus=state.mode==='overview'&&!filters().search&&!filters().category&&!filters().relation?model.graph.views.overview.nodeIds.map(id=>nodeById.get(id)).filter(Boolean):graph.nodes;fitNodes(semanticFocus);}
      semanticZoom();highlight();
    }
    function renderGraph(options={}) {
      const graph=visibleGraphData(),view=model.graph.views[state.mode]||model.graph.views[model.graph.defaultView.id];
      const searchMatches=searchMatchIds();
      const stage=state.stageFocus;
      document.getElementById('graphTitle').textContent=stage?stage.title:view.title;
      const semanticOverview=state.mode==='overview'&&!filters().search&&!filters().category&&!filters().relation;
      const emphasis=semanticOverview?model.graph.views.overview.nodeIds.length.toLocaleString()+' semantic nodes emphasized / ':'';
      const searchSummary=searchMatches.size?searchMatches.size.toLocaleString()+' matches highlighted / ':'';
      const stageSummary=stage?`${stage.summary} +${stage.addedNodeIds.length} nodes / ${stage.changedNodeIds.length} changed / ${stage.codeDiffs.length} code diffs. `:'';
      document.getElementById('graphSummary').textContent=stageSummary+view.summary+' '+emphasis+searchSummary+graph.nodes.length.toLocaleString()+' nodes / '+graph.edges.length.toLocaleString()+' relations loaded';
      if(!state.cy){
        state.detailLevel=null;
        state.cy=cytoscape({
          container:document.getElementById('projectGraph'),elements:allGraphData().elements,style:graphStyle(),
          layout:{name:'preset',fit:true,padding:52},
          minZoom:.10,maxZoom:3.2,pixelRatio:1,textureOnViewport:true,motionBlur:true,hideEdgesOnViewport:true,boxSelectionEnabled:false,autoungrabify:true
        });
        state.graphInstanceCount+=1;
        state.cy.on('tap','node',event=>{state.selected={type:'node',id:event.target.id()};renderSelection();highlight();});
        state.cy.on('tap','edge',event=>{state.selected={type:'edge',id:event.target.id()};renderSelection();highlight();});
        state.cy.on('tap',event=>{if(event.target===state.cy){state.selected=null;renderSelection();highlight();}});
        state.cy.on('zoom',()=>{if(state.zoomQueued)return;state.zoomQueued=true;window.requestAnimationFrame(()=>{state.zoomQueued=false;semanticZoom();});});
      }
      applyGraphVisibility(graph,Boolean(options.fit),searchMatches);
    }
    function semanticZoom() {
      if(!state.cy)return;
      const zoom=state.cy.zoom(),level=zoom>=1.05?'detail':zoom>=.43?'structure':'overview';
      if(state.detailLevel!==level){
        state.detailLevel=level;
        const codeNodes=state.cy.nodes('[category = "code"]'),codeEdges=state.cy.edges('[category = "code-relation"]');
        state.cy.batch(()=>{
          codeNodes.removeClass('low-detail');
          codeEdges.removeClass('low-detail detail-edge');
          if(level==='overview'){codeNodes.addClass('low-detail');codeEdges.addClass('low-detail');}
          if(level==='detail'){codeEdges.addClass('detail-edge');}
        });
      }
      updateViewportScale();
      updateOnDemandLabels();
    }
    function updateViewportScale() {
      if(!state.cy)return;
      const zoom=state.cy.zoom(),band=zoom<.25?'far':zoom<.52?'overview':zoom<1.05?'structure':zoom<1.8?'detail':'close';
      if(state.viewportScale===band)return;
      state.viewportScale=band;
      const profiles={far:{scale:4.4,node:14,code:2.1,file:5,namespace:3.4,type:4.1,capsule:18,edge:.38,codeEdge:.2,semanticEdge:.82},overview:{scale:2.35,node:14.5,code:2.25,file:5.3,namespace:3.5,type:4.3,capsule:18,edge:.42,codeEdge:.22,semanticEdge:.9},structure:{scale:1.18,node:15.5,code:2.8,file:6.2,namespace:4.1,type:5,capsule:21,edge:.5,codeEdge:.28,semanticEdge:1},detail:{scale:.62,node:16,code:3.1,file:6.8,namespace:4.5,type:5.4,capsule:23,edge:.54,codeEdge:.32,semanticEdge:1.04},close:{scale:.34,node:17,code:3.45,file:7.3,namespace:4.9,type:5.9,capsule:25,edge:.6,codeEdge:.36,semanticEdge:1.1}};
      const profile=profiles[band],size=value=>Math.max(.12,Math.round(value*profile.scale*100)/100),apply=(selector,style)=>state.cy.$(selector).style(style);
      // Full collections are restyled only when crossing one of five zoom bands, not for every wheel tick.
      state.cy.batch(()=>{
        apply('node',{'width':size(profile.node),'height':size(profile.node)});apply('node[category = "code"]',{'width':size(profile.code),'height':size(profile.code)});apply('node[category = "code"][kind = "file"]',{'width':size(profile.file),'height':size(profile.file)});apply('node[category = "code"][kind = "namespace"]',{'width':size(profile.namespace),'height':size(profile.namespace)});apply('node[category = "code"][kind = "type"]',{'width':size(profile.type),'height':size(profile.type)});apply('node[category = "code-capsule"]',{'width':size(profile.capsule),'height':size(profile.capsule)});apply('edge',{'width':size(profile.edge)});apply('edge[category = "code-relation"]',{'width':size(profile.codeEdge)});apply('edge.detail-edge',{'width':size(profile.codeEdge*1.3)});apply('edge[category = "capsule-relation"]',{'width':size(profile.semanticEdge*.82)});apply('edge[category = "mapping-relation"]',{'width':size(profile.semanticEdge)});apply('edge[category = "delta-relation"]',{'width':size(profile.semanticEdge)});apply('edge.selection-neighbor',{'width':size(profile.semanticEdge)});apply('edge.semantic-emphasis',{'width':size(profile.semanticEdge)});
      });
    }
    function highlight(){
      if(!state.cy)return;
      if(state.highlighted){const previous=state.cy.$id(state.highlighted);previous.unselect();previous.connectedEdges().removeClass('selection-neighbor');}
      state.highlighted=null;
      if(!state.selected){updateOnDemandLabels();return;}
      const item=state.cy.$id(state.selected.id);if(!item.length)return;
      item.select();item.connectedEdges().addClass('selection-neighbor');state.highlighted=state.selected.id;updateOnDemandLabels();
    }
    function renderStageSelection(stage){const panel=document.getElementById('selectionInspector'),diffs=stage.codeDiffs||[],diffHtml=diffs.map(diff=>`<h3 style="margin-top:12px">${safe(diff.sourceFile)}</h3><pre class="diff">${safe(diff.unifiedDiff)}</pre>`).join('');panel.className='detail';panel.innerHTML=`<h3>${safe(stage.title)}</h3>${rows([['work item',stage.workItemId],['stage',`${stage.sequence}. ${stage.kind}`],['status',stage.status],['revision boundary',stage.revisionKind],['graph additions',stage.addedNodeIds.length+' node(s), '+stage.addedEdgeIds.length+' edge(s)'],['graph changes',stage.changedNodeIds.length+' node(s), '+stage.changedEdgeIds.length+' edge(s)'],['code diffs',diffs.length],['verification records',stage.verificationRecordIds.length],['evidence records',stage.evidenceRecordIds.length],['history records',stage.recordIds.join(', ')||'none']])}<p>${safe(stage.summary)}</p>${diffHtml}`;}
    function renderSelection(){const panel=document.getElementById('selectionInspector');if(!state.selected){if(state.stageFocus){renderStageSelection(state.stageFocus);return;}panel.className='empty';panel.textContent='Select a graph node or relation to inspect its semantic and source provenance.';return;}if(state.selected.type==='node'){const node=nodeById.get(state.selected.id);if(!node)return;const base=[['category',node.category],['kind',node.kind],['identifier',node.id]];let diffHtml='';if(node.category==='code'){const diffs=node.codeDiffs||[];base.push(['source file',node.source.file],['range',`${node.source.location?.lineStart||'file'}:${node.source.location?.columnStart||''} - ${node.source.location?.lineEnd||''}:${node.source.location?.columnEnd||''}`],['source digest',short(node.source.digest)],['confidence',node.provenance.confidence],['delta state',node.deltaState||'unchanged'],['interpretation',node.details.interpretation],['code diff',diffs.length?`${diffs.length} proposed diff(s) below`:'No change proposal recorded']);diffHtml=diffs.map(diff=>`<h3 style="margin-top:12px">${safe(diff.proposalTitle)}</h3><p>${safe(diff.sourceFile)}</p><pre class="diff">${safe(diff.unifiedDiff)}</pre>`).join('');}else base.push(...Object.entries(node.details).map(([key,value])=>[key,typeof value==='object'?JSON.stringify(value):value]));panel.className='detail';panel.innerHTML=`<h3>${safe(node.label)}</h3>${rows(base)}${diffHtml}`; }else{const edge=allEdges.find(item=>item.id===state.selected.id);if(!edge)return;panel.className='detail';panel.innerHTML=`<h3>${safe(edge.kind)}</h3>${rows([['category',edge.category],['source',edge.source],['target',edge.target],...Object.entries(edge.details||{}).map(([key,value])=>[key,typeof value==='object'?JSON.stringify(value):value])])}`;}}
    function focusWork(workId){state.stageFocus=null;state.selected={type:'node',id:`work.${workId}`};state.mode='impact';document.querySelectorAll('[data-mode]').forEach(item=>item.classList.toggle('active',item.dataset.mode==='impact'));renderGraph({fit:true});renderSelection();}
    function focusDelta(nodeId){state.stageFocus=null;state.selected={type:'node',id:nodeId};state.mode='impact';document.querySelectorAll('[data-mode]').forEach(item=>item.classList.toggle('active',item.dataset.mode==='impact'));renderGraph({fit:true});renderSelection();}
    function focusStage(stageId){const stage=(model.workflow.workStageTimeline||[]).find(item=>item.id===stageId);if(!stage)return;state.selected=null;state.stageFocus=stage;state.mode='focus';document.querySelectorAll('[data-mode]').forEach(item=>item.classList.toggle('active',item.dataset.mode==='focus'));document.querySelectorAll('[data-stage]').forEach(item=>item.classList.toggle('active',item.dataset.stage===stageId));renderGraph({fit:true});renderStageSelection(stage);}
    function staticPanels(){
      document.getElementById('projectBadge').textContent=model.project.id;
      document.getElementById('snapshotBadge').textContent=`snapshot ${short(model.snapshot.sourceDigest)}`;
      const overlay=model.snapshot.semanticRelationOverlay||{},metrics=[['files',model.snapshot.sourceFileCount],['facts',model.snapshot.factCount],['syntax relations',model.snapshot.relationCount],['resolved relations',overlay.resolvedRelationCount||0],['cross-module',overlay.resolvedCrossModuleRelationCount||0],['work items',model.workflow.workItems.length]];
      document.getElementById('metrics').innerHTML=metrics.map(([label,value])=>`<div class="metric"><strong>${Number(value).toLocaleString()}</strong><span>${safe(label)}</span></div>`).join('');
      const works=model.workflow.workItems;document.getElementById('workList').innerHTML=works.length?works.map(work=>`<button class="work-card ${work.mappingStatus==='unmapped'?'unmapped':''}" data-work="${safe(work.id)}"><span class="state">${safe(work.status)} / ${safe(work.mappingStatus)}</span><strong>${safe(work.title)}</strong><small>${safe(work.request)}</small></button>`).join(''):'<div class="empty">No work request has been recorded. Use the project workspace command to add one.</div>';document.querySelectorAll('[data-work]').forEach(button=>button.addEventListener('click',()=>focusWork(button.dataset.work)));
      const stages=model.workflow.workStageTimeline||[];document.getElementById('stageList').innerHTML=stages.length?stages.map(stage=>{const delta=`+${stage.addedNodeIds.length} nodes / ${stage.changedNodeIds.length} changed / ${stage.codeDiffs.length} diffs`;return `<button class="stage-card" data-stage="${safe(stage.id)}"><span class="stage-meta"><span>${safe(stage.workItemId)}</span><span>${safe(stage.sequence)} / ${safe(stage.status)}</span></span><strong>${safe(stage.title)}</strong><small class="stage-delta">${safe(delta)}</small></button>`;}).join(''):'<div class="empty">No recorded work stages are available.</div>';document.querySelectorAll('[data-stage]').forEach(button=>button.addEventListener('click',()=>focusStage(button.dataset.stage)));
      const c=model.changeReview;document.getElementById('changePanel').innerHTML=`<div class="state-line"><strong>${safe(c.status)}</strong><br>${safe(c.summary)}<br><small>${safe(c.reason)}</small></div>`;const deltas=model.workflow.proposalDeltas||[];document.getElementById('deltaList').innerHTML=deltas.length?deltas.map(delta=>`<button class="delta-step" data-delta="${safe(delta.targetNodeId)}">${safe(delta.kind)}: ${safe(delta.label)}</button>`).join(''):'<div class="empty">No graph delta is recorded.</div>';document.querySelectorAll('[data-delta]').forEach(button=>button.addEventListener('click',()=>focusDelta(button.dataset.delta)));
      const receipts=model.workflow.reviewReceipts||[];document.getElementById('evidencePanel').innerHTML=`<div class="state-line">${model.workflow.verification.map(item=>`<strong>${safe(item.result)}</strong> ${safe(item.kind)}`).join('<br>')}<br>${model.workflow.evidence.map(item=>`<strong>${safe(item.result)}</strong> ${safe(item.kind)}`).join('<br>')}<br><strong>Review receipts:</strong> ${receipts.length?receipts.map(item=>safe(item.status)).join(', '):'none recorded'}</div>`;document.getElementById('authorityPanel').innerHTML=`<div class="state-line"><strong>read-only boundary</strong><br>Target edits: ${safe(model.authority.targetRepositoryMutation)}<br>Automatic application: ${safe(model.authority.automaticCodeApplication)}<br>History records: ${model.workflow.history.length}</div>`;
      document.getElementById('boundaryPanel').innerHTML='<strong>This page is a project-state projection.</strong><br>It can show recorded requests, candidate mappings, review-required proposals, graph delta, code diff, non-executing review receipts, verification, evidence, authority, history, syntax facts, and bounded local-symbol relations. It does not build, restore, launch, apply changes, execute verification, collect runtime evidence, or approve work.';
    }
    function resize(){document.querySelectorAll('.resizer').forEach(handle=>handle.addEventListener('pointerdown',event=>{event.preventDefault();handle.classList.add('active');const side=handle.dataset.side,start=event.clientX,variable=side==='left'?'--left':'--right',initial=parseInt(getComputedStyle(document.documentElement).getPropertyValue(variable));const move=e=>{const delta=e.clientX-start;const next=side==='left'?initial+delta:initial-delta;document.documentElement.style.setProperty(variable,`${Math.max(230,Math.min(560,next))}px`);if(!state.resizeQueued){state.resizeQueued=true;window.requestAnimationFrame(()=>{state.resizeQueued=false;state.cy?.resize();});}};const up=()=>{handle.classList.remove('active');window.removeEventListener('pointermove',move);window.removeEventListener('pointerup',up);state.cy?.resize();};window.addEventListener('pointermove',move);window.addEventListener('pointerup',up);}));}
    window.intentGraphWorkbench={selectedCodeNode:()=>{if(!state.selected||state.selected.type!=='node')return null;const node=nodeById.get(state.selected.id);return node&&node.category==='code'?node:null;},workItems:()=>model.workflow.workItems.slice(),reviewReceiptPairs:()=>{const recorded=new Set((model.workflow.reviewReceipts||[]).map(receipt=>receipt.proposalId+'|'+receipt.verificationRequirementId+'|'+receipt.evidenceRequirementId));return (model.workflow.changeProposals||[]).flatMap(proposal=>(proposal.verificationRequirements||[]).flatMap(verification=>(proposal.evidenceRequirements||[]).map(evidence=>({key:proposal.id+'|'+verification.id+'|'+evidence.id,proposalId:proposal.id,proposalTitle:proposal.title,verificationRequirementId:verification.id,evidenceRequirementId:evidence.id,verificationKind:verification.kind,evidenceKind:evidence.kind})))).filter(pair=>!recorded.has(pair.key));},metrics:()=>({graphInstanceCount:state.graphInstanceCount,visibilityUpdates:state.visibilityUpdates,visibleNodeCount:state.visibleNodeIds?.size||0,visibleEdgeCount:state.visibleEdgeIds?.size||0,totalNodeCount:allNodes.length,totalEdgeCount:allEdges.length,zoom:state.cy?.zoom()||null,zoomStyleBand:state.viewportScale||null})};
    document.getElementById('zoomIn').addEventListener('click',()=>state.cy.zoom({level:state.cy.zoom()*1.18,renderedPosition:{x:state.cy.width()/2,y:state.cy.height()/2}}));document.getElementById('zoomOut').addEventListener('click',()=>state.cy.zoom({level:state.cy.zoom()/1.18,renderedPosition:{x:state.cy.width()/2,y:state.cy.height()/2}}));document.getElementById('fitGraph').addEventListener('click',()=>{const graph=visibleGraphData(),semanticFocus=state.mode==='overview'&&!filters().search&&!filters().category&&!filters().relation?model.graph.views.overview.nodeIds.map(id=>nodeById.get(id)).filter(Boolean):graph.nodes;fitNodes(semanticFocus);});init();staticPanels();renderGraph({fit:true});renderSelection();resize();window.dispatchEvent(new Event('intentgraph-ready'));
    }
    const embeddedProjection=JSON.parse(document.getElementById('workbench-data').textContent);
    if(embeddedProjection&&embeddedProjection.deferred===true&&typeof window.__intentGraphLoadProjection==='function'){
      document.getElementById('graphSummary').textContent='Loading the full local project graph...';
      window.__intentGraphLoadProjection().then(boot).catch(error=>{document.getElementById('graphSummary').textContent='The local project graph could not be loaded: '+(error.message||'unknown error');});
    }else{boot(embeddedProjection);}
  </script>
</body>
</html>'''


def render_html(projection: dict[str, Any]) -> str:
    return HTML_TEMPLATE.replace("__WORKBENCH_DATA__", html_data(projection))


SERVER_UI_EXTENSION = r'''<style>
  .new-work-trigger { position:fixed; right:18px; bottom:18px; z-index:30; background:#133f3e; border-color:#45f2dc; color:#d9fffa; box-shadow:0 0 18px rgba(69,242,220,.16); }
  .new-work-dialog { width:min(520px,calc(100vw - 32px)); color:#f2efff; background:#100e1a; border:1px solid #50466d; border-radius:6px; padding:0; box-shadow:0 20px 60px rgba(0,0,0,.6); }
  .new-work-dialog::backdrop { background:rgba(2,1,8,.78); } .new-work-form { padding:18px; display:grid; gap:10px; } .new-work-form h2 { margin:0; color:#e8e1ff; font-size:15px; letter-spacing:0; text-transform:none; } .new-work-form label { margin:0; font-size:12px; } .new-work-form input,.new-work-form select,.new-work-form textarea { color:#f2efff; background:#07060d; border:1px solid #443d60; border-radius:4px; padding:8px; font:inherit; } .new-work-form textarea { min-height:110px; resize:vertical; } .new-work-actions { display:flex; justify-content:flex-end; gap:7px; } .new-work-message { min-height:18px; color:#ffd166; font-size:12px; } .map-code-trigger { position:fixed; right:18px; bottom:62px; z-index:30; background:#221e3a; border-color:#ad91ff; color:#efe8ff; box-shadow:0 0 18px rgba(173,145,255,.13); } .selected-code-fact { padding:8px; overflow-wrap:anywhere; color:#d4cceb; background:#07060d; border:1px solid #443d60; border-radius:4px; font:11px/1.4 Consolas,monospace; }
  .draft-proposal-trigger { position:fixed; right:18px; bottom:106px; z-index:30; background:#173a34; border-color:#63efc3; color:#dcfff3; box-shadow:0 0 18px rgba(99,239,195,.14); } .proposal-trigger { position:fixed; right:18px; bottom:150px; z-index:30; background:#422718; border-color:#ffd166; color:#fff2cc; box-shadow:0 0 18px rgba(255,209,102,.12); } .proposal-dialog { width:min(760px,calc(100vw - 32px)); } .proposal-input { min-height:300px !important; font:12px/1.45 Consolas,monospace !important; tab-size:2; }
  .draft-receipt-trigger { position:fixed; right:18px; bottom:194px; z-index:30; background:#2f2449; border-color:#c0a0ff; color:#f0e7ff; box-shadow:0 0 18px rgba(192,160,255,.12); } .receipt-trigger { position:fixed; right:18px; bottom:238px; z-index:30; background:#35244e; border-color:#c0a0ff; color:#f0e7ff; box-shadow:0 0 18px rgba(192,160,255,.12); }
</style>
<button id="newWorkTrigger" class="new-work-trigger" type="button">New work request</button>
<button id="mapCodeTrigger" class="map-code-trigger" type="button">Map selected code</button>
<button id="draftProposalTrigger" class="draft-proposal-trigger" type="button" disabled>Draft review proposal</button>
<button id="importProposalTrigger" class="proposal-trigger" type="button" disabled>Import proposal JSON</button>
<button id="draftReceiptTrigger" class="draft-receipt-trigger" type="button" disabled>Record review receipt</button>
<button id="importReceiptTrigger" class="receipt-trigger" type="button" disabled>Import receipt JSON</button>
<dialog id="newWorkDialog" class="new-work-dialog"><form id="newWorkForm" class="new-work-form" method="dialog"><h2>Record a work request</h2><p>This records a request in the local IntentGraph project workspace. It does not edit the source project.</p><label for="newWorkId">Stable work id</label><input id="newWorkId" name="workId" required pattern="[a-z][a-z0-9.-]{2,100}" placeholder="example-work-item"><label for="newWorkTitle">Title</label><input id="newWorkTitle" name="title" required maxlength="180" placeholder="Short work title"><label for="newWorkRequest">Request</label><textarea id="newWorkRequest" name="request" required maxlength="12000" placeholder="Describe the desired behavior or change."></textarea><div id="newWorkMessage" class="new-work-message"></div><div class="new-work-actions"><button id="cancelNewWork" type="button">Cancel</button><button type="submit">Record request</button></div></form></dialog>
<dialog id="mapCodeDialog" class="new-work-dialog"><form id="mapCodeForm" class="new-work-form" method="dialog"><h2>Record a code mapping candidate</h2><p>This connects the selected code fact to a local work request as a declared candidate. It does not approve the mapping or edit the source project.</p><label>Selected code fact</label><div id="selectedCodeFact" class="selected-code-fact"></div><label for="mapWorkId">Work request</label><select id="mapWorkId" name="workId" required></select><label for="mapRationale">Why this code is relevant</label><textarea id="mapRationale" name="rationale" required maxlength="12000" placeholder="Describe the relationship between this request and the selected code."></textarea><div id="mapCodeMessage" class="new-work-message"></div><div class="new-work-actions"><button id="cancelMapCode" type="button">Cancel</button><button id="submitMapCode" type="submit">Record mapping candidate</button></div></form></dialog>
<dialog id="draftProposalDialog" class="new-work-dialog"><form id="draftProposalForm" class="new-work-form" method="dialog"><h2>Draft a review proposal</h2><p>Creates a non-applied review proposal from an existing declared mapping. It records no code patch and does not edit the source project.</p><label for="draftProposalWorkId">Mapped work request</label><select id="draftProposalWorkId" name="workId" required></select><label for="draftProposalId">Stable proposal id</label><input id="draftProposalId" name="proposalId" required pattern="[a-z][a-z0-9.-]{2,100}" maxlength="101"><label for="draftProposalTitle">Proposal title</label><input id="draftProposalTitle" name="title" required maxlength="180" placeholder="Short review proposal title"><label for="draftProposalSummary">Review summary</label><textarea id="draftProposalSummary" name="summary" required maxlength="12000" placeholder="Describe the bounded review change."></textarea><label for="draftVerificationKind">Verification kind</label><select id="draftVerificationKind" name="verificationKind" required><option value="local-review">Local review</option><option value="build-required">Build required</option><option value="test-required">Test required</option></select><label for="draftVerificationSummary">Verification requirement</label><textarea id="draftVerificationSummary" name="verificationSummary" required maxlength="12000" placeholder="State what must be verified later."></textarea><label for="draftEvidenceKind">Evidence kind</label><select id="draftEvidenceKind" name="evidenceKind" required><option value="review-note">Review note</option><option value="test-evidence">Test evidence</option><option value="build-evidence">Build evidence</option></select><label for="draftEvidenceSummary">Evidence requirement</label><textarea id="draftEvidenceSummary" name="evidenceSummary" required maxlength="12000" placeholder="State what evidence must be collected later."></textarea><div id="draftProposalMessage" class="new-work-message"></div><div class="new-work-actions"><button id="cancelDraftProposal" type="button">Cancel</button><button id="submitDraftProposal" type="submit">Record review proposal</button></div></form></dialog>
<dialog id="draftReceiptDialog" class="new-work-dialog"><form id="draftReceiptForm" class="new-work-form" method="dialog"><h2>Record a review receipt</h2><p>Records a human review result for one existing proposal requirement pair. It does not execute the requirement, collect runtime evidence, apply the proposal, approve the proposal, or edit the source project.</p><label for="draftReceiptPair">Proposal requirement pair</label><select id="draftReceiptPair" name="pair" required></select><label for="draftReceiptId">Stable receipt id</label><input id="draftReceiptId" name="receiptId" required pattern="[a-z][a-z0-9.-]{2,100}" maxlength="101"><label for="draftReceiptResult">Review result</label><select id="draftReceiptResult" name="result" required><option value="reviewed-pass">Reviewed pass</option><option value="reviewed-fail">Reviewed fail</option><option value="review-blocked">Review blocked</option></select><label for="draftReceiptSummary">Review summary</label><textarea id="draftReceiptSummary" name="summary" required maxlength="12000" placeholder="State what was reviewed. This is not execution evidence."></textarea><div id="draftReceiptMessage" class="new-work-message"></div><div class="new-work-actions"><button id="cancelDraftReceipt" type="button">Cancel</button><button id="submitDraftReceipt" type="submit">Record receipt</button></div></form></dialog>
<dialog id="importProposalDialog" class="new-work-dialog proposal-dialog"><form id="importProposalForm" class="new-work-form" method="dialog"><h2>Import a review-only change proposal</h2><p>Paste a deterministic proposal document for an existing work request and mapping candidate. The local server validates it before recording any project-state artifact. It does not edit the C# source project, apply a graph delta, or approve the proposal.</p><label for="proposalDocument">Proposal JSON</label><textarea id="proposalDocument" class="proposal-input" name="proposalDocument" required maxlength="100000" spellcheck="false" placeholder="Paste an intentgraph-experimental-csharp-change-proposal document."></textarea><div id="importProposalMessage" class="new-work-message"></div><div class="new-work-actions"><button id="cancelImportProposal" type="button">Cancel</button><button type="submit">Validate and record proposal</button></div></form></dialog>
<dialog id="importReceiptDialog" class="new-work-dialog proposal-dialog"><form id="importReceiptForm" class="new-work-form" method="dialog"><h2>Import a non-executing review receipt</h2><p>Paste one deterministic receipt for a proposal verification/evidence requirement pair. It records what was reviewed as pass, fail, or blocked. It does not run verification, collect runtime evidence, apply a graph delta, approve the proposal, or edit C# source.</p><label for="receiptDocument">Review receipt JSON</label><textarea id="receiptDocument" class="proposal-input" name="receiptDocument" required maxlength="100000" spellcheck="false" placeholder="Paste an intentgraph-experimental-csharp-review-receipt document."></textarea><div id="importReceiptMessage" class="new-work-message"></div><div class="new-work-actions"><button id="cancelImportReceipt" type="button">Cancel</button><button type="submit">Validate and record receipt</button></div></form></dialog>
<script>
  (() => { const dialog=document.getElementById('newWorkDialog'), trigger=document.getElementById('newWorkTrigger'), form=document.getElementById('newWorkForm'), workId=document.getElementById('newWorkId'), title=document.getElementById('newWorkTitle'), request=document.getElementById('newWorkRequest'), message=document.getElementById('newWorkMessage'); trigger.addEventListener('click',()=>dialog.showModal()); document.getElementById('cancelNewWork').addEventListener('click',()=>dialog.close()); form.addEventListener('submit',async event=>{event.preventDefault();message.textContent='Recording request...';const body={workId:workId.value.trim(),title:title.value.trim(),request:request.value.trim()};try{const response=await fetch('/api/work-requests',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const result=await response.json();if(!response.ok){throw new Error(result.error||'Request could not be recorded.');}message.textContent='Recorded. Reloading workbench...';window.setTimeout(()=>window.location.reload(),250);}catch(error){message.textContent=error.message||'Request could not be recorded.';}}); })();
</script>
<script>
  (() => {
    const dialog=document.getElementById('mapCodeDialog'),trigger=document.getElementById('mapCodeTrigger'),form=document.getElementById('mapCodeForm'),selected=document.getElementById('selectedCodeFact'),workSelect=document.getElementById('mapWorkId'),rationale=document.getElementById('mapRationale'),message=document.getElementById('mapCodeMessage'),submit=document.getElementById('submitMapCode');
    let selectedFactId='';
    function openMappingDialog(){
      const workbench=window.intentGraphWorkbench;
      const node=workbench&&workbench.selectedCodeNode?workbench.selectedCodeNode():null;
      const works=workbench&&workbench.workItems?workbench.workItems():[];
      workSelect.replaceChildren();
      works.forEach(work=>workSelect.add(new Option(work.title+' ('+work.id+')',work.id)));
      selectedFactId=node?node.id:'';
      selected.textContent=node?node.id+'\n'+node.source.file:'Select a code node in the graph before recording a mapping candidate.';
      message.textContent=node&&works.length?'':'A code selection and at least one recorded work request are required.';
      submit.disabled=!node||!works.length;
      dialog.showModal();
    }
    trigger.disabled=true;
    window.addEventListener('intentgraph-ready',()=>{trigger.disabled=false;});
    trigger.addEventListener('click',openMappingDialog);
    document.getElementById('cancelMapCode').addEventListener('click',()=>dialog.close());
    form.addEventListener('submit',async event=>{
      event.preventDefault();
      if(!selectedFactId)return;
      message.textContent='Recording mapping candidate...';
      const body={workId:workSelect.value,codeFactId:selectedFactId,rationale:rationale.value.trim()};
      try{
        const response=await fetch('/api/mapping-candidates',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
        const result=await response.json();
        if(!response.ok)throw new Error(result.error||'Mapping candidate could not be recorded.');
        message.textContent='Recorded. Reloading workbench...';
        window.setTimeout(()=>window.location.reload(),250);
      }catch(error){message.textContent=error.message||'Mapping candidate could not be recorded.';}
    });
  })();
</script>
<script>
  (() => {
    const dialog=document.getElementById('draftProposalDialog'),trigger=document.getElementById('draftProposalTrigger'),form=document.getElementById('draftProposalForm'),workSelect=document.getElementById('draftProposalWorkId'),proposalId=document.getElementById('draftProposalId'),title=document.getElementById('draftProposalTitle'),summary=document.getElementById('draftProposalSummary'),verificationKind=document.getElementById('draftVerificationKind'),verificationSummary=document.getElementById('draftVerificationSummary'),evidenceKind=document.getElementById('draftEvidenceKind'),evidenceSummary=document.getElementById('draftEvidenceSummary'),message=document.getElementById('draftProposalMessage'),submit=document.getElementById('submitDraftProposal');
    function eligibleWorks(){const workbench=window.intentGraphWorkbench;const works=workbench&&workbench.workItems?workbench.workItems():[];return works.filter(work=>work.mappingStatus==='candidate'&&work.changeStatus==='not-proposed');}
    function updateProposalId(){const workId=workSelect.value;proposalId.value=workId?'proposal-'+workId:'';}
    function openDialog(){const works=eligibleWorks();workSelect.replaceChildren();works.forEach(work=>workSelect.add(new Option(work.title+' ('+work.id+')',work.id)));updateProposalId();const ready=works.length>0;message.textContent=ready?'':'Record a declared code mapping before drafting a review proposal.';submit.disabled=!ready;dialog.showModal();}
    trigger.disabled=true;
    window.addEventListener('intentgraph-ready',()=>{trigger.disabled=false;});
    trigger.addEventListener('click',openDialog);
    workSelect.addEventListener('change',updateProposalId);
    document.getElementById('cancelDraftProposal').addEventListener('click',()=>dialog.close());
    form.addEventListener('submit',async event=>{
      event.preventDefault();
      message.textContent='Recording review proposal...';
      const body={proposalId:proposalId.value.trim(),workId:workSelect.value,title:title.value.trim(),summary:summary.value.trim(),verificationKind:verificationKind.value,verificationSummary:verificationSummary.value.trim(),evidenceKind:evidenceKind.value,evidenceSummary:evidenceSummary.value.trim()};
      try{
        const response=await fetch('/api/draft-change-proposals',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
        const result=await response.json();
        if(!response.ok)throw new Error(result.error||'Review proposal could not be recorded.');
        message.textContent='Recorded for review. Reloading workbench...';
        window.setTimeout(()=>window.location.reload(),250);
      }catch(error){message.textContent=error.message||'Review proposal could not be recorded.';}
    });
  })();
</script>
<script>
  (() => {
    const dialog=document.getElementById('draftReceiptDialog'),trigger=document.getElementById('draftReceiptTrigger'),form=document.getElementById('draftReceiptForm'),pairSelect=document.getElementById('draftReceiptPair'),receiptId=document.getElementById('draftReceiptId'),result=document.getElementById('draftReceiptResult'),summary=document.getElementById('draftReceiptSummary'),message=document.getElementById('draftReceiptMessage'),submit=document.getElementById('submitDraftReceipt');
    let pairsByKey=new Map();
    function updateReceiptId(){const pair=pairsByKey.get(pairSelect.value);receiptId.value=pair?'receipt-'+pair.proposalId.slice(0,90):'';}
    function openDialog(){const workbench=window.intentGraphWorkbench;const pairs=workbench&&workbench.reviewReceiptPairs?workbench.reviewReceiptPairs():[];pairsByKey=new Map(pairs.map(pair=>[pair.key,pair]));pairSelect.replaceChildren();pairs.forEach(pair=>pairSelect.add(new Option(pair.proposalTitle+' - '+pair.verificationKind+' / '+pair.evidenceKind,pair.key)));updateReceiptId();const ready=pairs.length>0;message.textContent=ready?'':'Record a review proposal with an unreviewed requirement pair before recording a receipt.';submit.disabled=!ready;dialog.showModal();}
    trigger.disabled=true;
    window.addEventListener('intentgraph-ready',()=>{trigger.disabled=false;});
    trigger.addEventListener('click',openDialog);
    pairSelect.addEventListener('change',updateReceiptId);
    document.getElementById('cancelDraftReceipt').addEventListener('click',()=>dialog.close());
    form.addEventListener('submit',async event=>{
      event.preventDefault();
      const pair=pairsByKey.get(pairSelect.value);if(!pair)return;
      message.textContent='Recording review receipt...';
      const body={receiptId:receiptId.value.trim(),proposalId:pair.proposalId,verificationRequirementId:pair.verificationRequirementId,evidenceRequirementId:pair.evidenceRequirementId,result:result.value,summary:summary.value.trim()};
      try{
        const response=await fetch('/api/draft-review-receipts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
        const recorded=await response.json();
        if(!response.ok)throw new Error(recorded.error||'Review receipt could not be recorded.');
        message.textContent='Receipt recorded. Reloading workbench...';
        window.setTimeout(()=>window.location.reload(),250);
      }catch(error){message.textContent=error.message||'Review receipt could not be recorded.';}
    });
  })();
</script>
<script>
  (() => {
    const dialog=document.getElementById('importProposalDialog'),trigger=document.getElementById('importProposalTrigger'),form=document.getElementById('importProposalForm'),documentField=document.getElementById('proposalDocument'),message=document.getElementById('importProposalMessage');
    trigger.disabled=true;
    window.addEventListener('intentgraph-ready',()=>{trigger.disabled=false;});
    trigger.addEventListener('click',()=>dialog.showModal());
    document.getElementById('cancelImportProposal').addEventListener('click',()=>dialog.close());
    form.addEventListener('submit',async event=>{
      event.preventDefault();
      let proposal;
      try { proposal=JSON.parse(documentField.value); } catch (_error) { message.textContent='Proposal JSON is not valid.'; return; }
      if(!proposal || Array.isArray(proposal) || typeof proposal!=='object'){ message.textContent='Proposal JSON must be an object.'; return; }
      message.textContent='Validating review-only proposal...';
      try {
        const response=await fetch('/api/change-proposals',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({proposal})});
        const result=await response.json();
        if(!response.ok)throw new Error(result.error||'Proposal could not be recorded.');
        message.textContent='Recorded for review. Reloading workbench...';
        window.setTimeout(()=>window.location.reload(),250);
      }catch(error){message.textContent=error.message||'Proposal could not be recorded.';}
    });
  })();
</script>
<script>
  (() => {
    const dialog=document.getElementById('importReceiptDialog'),trigger=document.getElementById('importReceiptTrigger'),form=document.getElementById('importReceiptForm'),documentField=document.getElementById('receiptDocument'),message=document.getElementById('importReceiptMessage');
    trigger.disabled=true;
    window.addEventListener('intentgraph-ready',()=>{trigger.disabled=false;});
    trigger.addEventListener('click',()=>dialog.showModal());
    document.getElementById('cancelImportReceipt').addEventListener('click',()=>dialog.close());
    form.addEventListener('submit',async event=>{
      event.preventDefault();
      let receipt;
      try { receipt=JSON.parse(documentField.value); } catch (_error) { message.textContent='Review receipt JSON is not valid.'; return; }
      if(!receipt || Array.isArray(receipt) || typeof receipt!=='object'){ message.textContent='Review receipt JSON must be an object.'; return; }
      message.textContent='Validating non-executing review receipt...';
      try {
        const response=await fetch('/api/review-receipts',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({receipt})});
        const result=await response.json();
        if(!response.ok)throw new Error(result.error||'Review receipt could not be recorded.');
        message.textContent='Receipt recorded. Reloading workbench...';
        window.setTimeout(()=>window.location.reload(),250);
      }catch(error){message.textContent=error.message||'Review receipt could not be recorded.';}
    });
  })();
</script>'''


def render_server_html(projection: dict[str, Any]) -> str:
    """Render the local-server variant. The static export intentionally does not include its API client."""
    del projection
    loader = "<script>window.__intentGraphLoadProjection=()=>fetch('/api/projection').then(response=>{if(!response.ok)throw new Error('projection request failed');return response.json();});</script>\n"
    html = render_html({"deferred": True})
    html = html.replace('<script id="workbench-data"', loader + '<script id="workbench-data"', 1)
    return html.replace("</body>", SERVER_UI_EXTENSION + "\n</body>")


def validate_projection(projection: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if projection.get("artifactRole") != "intentgraph-experimental-csharp-project-workbench-projection" or projection.get("scope") != WORKBENCH_SCOPE:
        errors.append("wrong project workbench projection role or scope")
    if projection.get("authority") != PROJECT_AUTHORITY:
        errors.append("project workbench authority is invalid")
    change_review = projection.get("changeReview", {})
    if change_review.get("status") not in {"not-recorded", "review-required"}:
        errors.append("project workbench change review state is invalid")
    if change_review.get("status") == "not-recorded" and (change_review.get("graphDeltaShown") is not False or change_review.get("codeDiffShown") is not False):
        errors.append("project workbench no-proposal boundary is invalid")
    if change_review.get("status") == "review-required" and change_review.get("graphDeltaShown") is not True:
        errors.append("project workbench proposal graph delta is not visible")
    workflow = projection.get("workflow")
    if not isinstance(workflow, dict) or not isinstance(workflow.get("reviewReceipts"), list) or not isinstance(workflow.get("workStageTimeline"), list):
        errors.append("project workbench review receipt state is invalid")
    else:
        required_stage_fields = {"id", "workItemId", "sequence", "kind", "title", "summary", "status", "recordIds", "nodeIds", "addedNodeIds", "changedNodeIds", "contextNodeIds", "edgeIds", "addedEdgeIds", "changedEdgeIds", "codeDiffs", "verificationRecordIds", "evidenceRecordIds", "revisionKind"}
        work_ids = {item["id"] for item in workflow.get("workItems", []) if isinstance(item, dict) and isinstance(item.get("id"), str)}
        stage_ids = set()
        for stage in workflow["workStageTimeline"]:
            if not isinstance(stage, dict) or set(stage) != required_stage_fields or stage["id"] in stage_ids or stage["workItemId"] not in work_ids or not isinstance(stage["sequence"], int) or stage["sequence"] < 1:
                errors.append("project workbench work stage timeline is invalid")
                break
            stage_ids.add(stage["id"])
    graph = projection.get("graph")
    if not isinstance(graph, dict) or not isinstance(graph.get("nodes"), list) or not isinstance(graph.get("edges"), list):
        return errors + ["project workbench graph is missing"]
    nodes = graph["nodes"]
    edges = graph["edges"]
    node_ids = {node.get("id") for node in nodes if isinstance(node, dict)}
    if len(node_ids) != len(nodes):
        errors.append("project workbench graph node identifiers are invalid")
    if not any(node.get("category") == "project" for node in nodes if isinstance(node, dict)):
        errors.append("project workbench graph needs a project node")
    for node in nodes:
        if not isinstance(node, dict) or node.get("category") not in {"code", "code-capsule", "project", "source-document", "goal", "capability", "constraint", "verification-requirement", "work", "intent", "mapping", "proposal", "verification", "evidence", "review-receipt", "authority", "history"}:
            errors.append("project workbench graph contains an unknown node category")
            continue
        if node["category"] == "code":
            source = node.get("source")
            if node.get("kind") not in ALLOWED_FACT_KINDS or not isinstance(source, dict) or not safe_relative_source(source.get("file")):
                errors.append(f"code node {node.get('id')} provenance is invalid")
    for edge in edges:
        if not isinstance(edge, dict) or edge.get("source") not in node_ids or edge.get("target") not in node_ids:
            errors.append("project workbench graph edge endpoint does not resolve")
    views = graph.get("views")
    if not isinstance(views, dict) or set(views) != {"overview", "impact", "code", "all"}:
        errors.append("project workbench graph views are invalid")
    elif any(not isinstance(view, dict) or not isinstance(view.get("nodeIds"), list) or any(identifier not in node_ids for identifier in view["nodeIds"]) for view in views.values()):
        errors.append("project workbench graph view nodes do not resolve")
    elif set(views["all"]["nodeIds"]) != node_ids:
        errors.append("project workbench full graph view must include every node")
    default_view = graph.get("defaultView")
    if not isinstance(default_view, dict) or default_view.get("id") != "all" or default_view.get("rendering") != "full-graph-progressive-detail" or default_view.get("layout") != "deterministic-relation-aware-community-preset" or default_view.get("physicsLayoutOnLoad") is not False:
        errors.append("project workbench full graph rendering contract is invalid")
    ui_contract = projection.get("uiContract")
    if not isinstance(ui_contract, dict) or any(ui_contract.get(key) is not True for key in ("fullGraphDefault", "allNodesLoaded", "allEdgesLoaded", "progressiveDetail", "viewportScaleCompensation", "relationAwareCommunityLayout", "zoomStyleBuckets", "supportingNodeLabelsOnDemand", "workStageTimeline", "loopbackProjectStateMutationFromUi", "loopbackReviewProposalIntakeFromUi", "loopbackGuidedReviewProposalFromUi", "loopbackReviewReceiptIntakeFromUi", "loopbackGuidedReviewReceiptFromUi")) or any(ui_contract.get(key) is not False for key in ("staticGraphMutationFromUi", "targetRepositoryMutationFromUi", "physicsLayoutOnLoad")):
        errors.append("project workbench progressive full graph UI contract is invalid")
    try:
        assert_no_unsafe_state(projection)
    except ProjectWorkspaceError as error:
        errors.append(str(error))
    return errors


def validate_output(output: Path, project_workspace: Path, expected_projection: dict[str, Any], project_before: list[dict[str, str]]) -> dict[str, Any]:
    paths = output_paths(output)
    errors: list[str] = []
    for key, path in paths.items():
        if key != "validation" and not path.is_file():
            errors.append(f"missing output: {key}")
    if errors:
        return {"result": "fail", "errors": errors}
    projection = read_json(paths["projection"])
    if projection != expected_projection:
        errors.append("projection does not match deterministic project workspace input")
    errors.extend(validate_projection(projection))
    html = paths["index"].read_text(encoding="utf-8")
    for marker in ["id=\"projectGraph\"", "id=\"workList\"", "id=\"stageList\"", "id=\"selectionInspector\"", "id=\"changePanel\"", "id=\"deltaList\"", "id=\"evidencePanel\"", "id=\"authorityPanel\"", "id=\"zoomIn\"", "id=\"zoomOut\"", "assets/cytoscape.min.js"]:
        if marker not in html:
            errors.append(f"HTML marker missing: {marker}")
    for forbidden in ["http://", "https://", "fetch(", "sourceText", "targetSyntax", "applyProposal", "approveProposal"]:
        if forbidden in html:
            errors.append(f"HTML contains forbidden token: {forbidden}")
    if file_digest(paths["cytoscape"]) != file_digest(CYTOSCAPE_SOURCE) or file_digest(paths["license"]) != file_digest(CYTOSCAPE_LICENSE_SOURCE):
        errors.append("local graph runtime assets are invalid")
    expected_manifest = {
        "artifactRole": WORKBENCH_ROLE,
        "status": "intentgraph-experimental-csharp-project-workbench-emitted",
        "scope": WORKBENCH_SCOPE,
        "version": WORKBENCH_VERSION,
        "project": expected_projection["project"],
        "projectWorkspaceMutation": False,
        "authority": PROJECT_AUTHORITY,
        "assets": {"cytoscape": {"path": "assets/cytoscape.min.js", "sha256": file_digest(paths["cytoscape"]), "version": "3.34.0"}, "license": {"path": "assets/cytoscape-license.txt", "sha256": file_digest(paths["license"])}},
        "outputs": {"projection": {"path": "projection.json", "sha256": file_digest(paths["projection"])}, "html": {"path": "index.html", "sha256": file_digest(paths["index"])}},
    }
    if read_json(paths["manifest"]) != expected_manifest:
        errors.append("project workbench manifest is invalid")
    try:
        validate_project_workspace(project_workspace)
        after = [{"path": path.relative_to(project_workspace).as_posix(), "sha256": file_digest(path)} for path in sorted(project_workspace.rglob("*")) if path.is_file() and not path.is_symlink()]
        if after != project_before:
            errors.append("workbench emitter mutated the project workspace")
    except ProjectWorkspaceError as error:
        errors.append(f"project workspace is no longer valid: {error}")
    return {
        "artifactRole": "intentgraph-experimental-csharp-project-workbench-validation-report",
        "status": "intentgraph-experimental-csharp-project-workbench-validation-" + ("pass" if not errors else "fail"),
        "scope": WORKBENCH_SCOPE,
        "result": "pass" if not errors else "fail",
        "errors": errors,
        "projectWorkspaceMutation": False,
        "targetRepositoryMutation": False,
        "fullSourceContentPersisted": False,
        "proposedCodeDiffFragmentsShown": expected_projection["snapshot"]["proposedCodeDiffFragmentsShown"],
        "externalSourcePathPersisted": False,
        "networkRequired": False,
        "semanticOverlayVisible": not errors,
        "changeBoundaryVisible": not errors,
        "authority": PROJECT_AUTHORITY,
    }


def emit_project_workbench(project_workspace: Path, output: Path) -> dict[str, Any]:
    project_workspace = project_workspace.resolve()
    output = output.resolve()
    if output.exists():
        raise ProjectWorkspaceError("project workbench output directory must not exist")
    if is_within(output, project_workspace) or is_within(project_workspace, output):
        raise ProjectWorkspaceError("project workbench output must not overlap the project workspace")
    if not CYTOSCAPE_SOURCE.is_file() or not CYTOSCAPE_LICENSE_SOURCE.is_file():
        raise ProjectWorkspaceError("declared local Cytoscape asset is missing")
    projection, project_before = build_projection(project_workspace)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="intentgraph-csharp-project-workbench-", dir=output.parent) as temporary:
        staged = Path(temporary) / "output"
        paths = output_paths(staged)
        write_json(paths["projection"], projection)
        paths["index"].parent.mkdir(parents=True, exist_ok=True)
        paths["index"].write_text(render_html(projection), encoding="utf-8", newline="\n")
        paths["cytoscape"].parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(CYTOSCAPE_SOURCE, paths["cytoscape"])
        shutil.copyfile(CYTOSCAPE_LICENSE_SOURCE, paths["license"])
        write_json(
            paths["manifest"],
            {
                "artifactRole": WORKBENCH_ROLE,
                "status": "intentgraph-experimental-csharp-project-workbench-emitted",
                "scope": WORKBENCH_SCOPE,
                "version": WORKBENCH_VERSION,
                "project": projection["project"],
                "projectWorkspaceMutation": False,
                "authority": PROJECT_AUTHORITY,
                "assets": {"cytoscape": {"path": "assets/cytoscape.min.js", "sha256": file_digest(paths["cytoscape"]), "version": "3.34.0"}, "license": {"path": "assets/cytoscape-license.txt", "sha256": file_digest(paths["license"])}},
                "outputs": {"projection": {"path": "projection.json", "sha256": file_digest(paths["projection"])}, "html": {"path": "index.html", "sha256": file_digest(paths["index"])}},
            },
        )
        validation = validate_output(staged, project_workspace, projection, project_before)
        write_json(paths["validation"], validation)
        if validation["result"] != "pass":
            raise ProjectWorkspaceError("project workbench validation failed: " + "; ".join(validation["errors"]))
        shutil.move(str(staged), str(output))
    return {"result": "pass", "command": "emit-experimental-csharp-project-workbench", "output": output.as_posix(), "project": projection["project"], "workItemCount": len(projection["workflow"]["workItems"]), "mappingCount": len(projection["workflow"]["mappings"]), "authority": PROJECT_AUTHORITY}


def validate_emitted_project_workbench(project_workspace: Path, output: Path) -> dict[str, Any]:
    project_workspace = project_workspace.resolve()
    output = output.resolve()
    if not output.is_dir():
        raise ProjectWorkspaceError("project workbench output directory must exist")
    if is_within(output, project_workspace) or is_within(project_workspace, output):
        raise ProjectWorkspaceError("project workbench output must not overlap the project workspace")
    projection, before = build_projection(project_workspace)
    validation = validate_output(output, project_workspace, projection, before)
    if validation["result"] != "pass":
        raise ProjectWorkspaceError("project workbench validation failed: " + "; ".join(validation["errors"]))
    return {"result": "pass", "command": "validate-experimental-csharp-project-workbench", "output": output.as_posix(), "projectWorkspaceMutation": False, "authority": PROJECT_AUTHORITY}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--snapshot-workspace", required=True, type=Path)
    init.add_argument("--workspace", required=True, type=Path)
    init.add_argument("--project-id", required=True)
    init.add_argument("--title", required=True)
    request = sub.add_parser("add-work-request")
    request.add_argument("--workspace", required=True, type=Path)
    request.add_argument("--work-id", required=True)
    request.add_argument("--title", required=True)
    request.add_argument("--request", required=True)
    mapping = sub.add_parser("add-mapping-candidate")
    mapping.add_argument("--workspace", required=True, type=Path)
    mapping.add_argument("--work-id", required=True)
    mapping.add_argument("--code-fact", required=True, action="append")
    mapping.add_argument("--rationale", required=True)
    foundation = sub.add_parser("record-semantic-foundation")
    foundation.add_argument("--workspace", required=True, type=Path)
    foundation.add_argument("--foundation", required=True, type=Path)
    semantic_relations = sub.add_parser("record-semantic-relation-overlay")
    semantic_relations.add_argument("--workspace", required=True, type=Path)
    semantic_relations.add_argument("--overlay", required=True, type=Path)
    proposal = sub.add_parser("add-change-proposal")
    proposal.add_argument("--workspace", required=True, type=Path)
    proposal.add_argument("--proposal", required=True, type=Path)
    draft_proposal = sub.add_parser("draft-change-proposal")
    draft_proposal.add_argument("--workspace", required=True, type=Path)
    draft_proposal.add_argument("--proposal-id", required=True)
    draft_proposal.add_argument("--work-id", required=True)
    draft_proposal.add_argument("--title", required=True)
    draft_proposal.add_argument("--summary", required=True)
    draft_proposal.add_argument("--verification-kind", required=True)
    draft_proposal.add_argument("--verification-summary", required=True)
    draft_proposal.add_argument("--evidence-kind", required=True)
    draft_proposal.add_argument("--evidence-summary", required=True)
    receipt = sub.add_parser("add-review-receipt")
    receipt.add_argument("--workspace", required=True, type=Path)
    receipt.add_argument("--receipt", required=True, type=Path)
    draft_receipt = sub.add_parser("draft-review-receipt")
    draft_receipt.add_argument("--workspace", required=True, type=Path)
    draft_receipt.add_argument("--receipt-id", required=True)
    draft_receipt.add_argument("--proposal-id", required=True)
    draft_receipt.add_argument("--verification-requirement-id", required=True)
    draft_receipt.add_argument("--evidence-requirement-id", required=True)
    draft_receipt.add_argument("--result", required=True, choices=sorted(REVIEW_RECEIPT_RESULTS))
    draft_receipt.add_argument("--summary", required=True)
    emit = sub.add_parser("emit-workbench")
    emit.add_argument("--workspace", required=True, type=Path)
    emit.add_argument("--out", required=True, type=Path)
    validate = sub.add_parser("validate-workbench")
    validate.add_argument("--workspace", required=True, type=Path)
    validate.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "init":
            result = initialize_project(args.snapshot_workspace, args.workspace, args.project_id, args.title)
        elif args.command == "add-work-request":
            result = add_work_request(args.workspace, args.work_id, args.title, args.request)
        elif args.command == "add-mapping-candidate":
            result = add_mapping_candidate(args.workspace, args.work_id, args.code_fact, args.rationale)
        elif args.command == "record-semantic-foundation":
            result = record_semantic_foundation(args.workspace, args.foundation)
        elif args.command == "record-semantic-relation-overlay":
            result = record_semantic_relation_overlay(args.workspace, args.overlay)
        elif args.command == "add-change-proposal":
            result = add_change_proposal(args.workspace, args.proposal)
        elif args.command == "draft-change-proposal":
            result = draft_change_proposal_from_mapping(
                args.workspace,
                proposal_id=args.proposal_id,
                work_id=args.work_id,
                title=args.title,
                summary=args.summary,
                verification_kind=args.verification_kind,
                verification_summary=args.verification_summary,
                evidence_kind=args.evidence_kind,
                evidence_summary=args.evidence_summary,
            )
        elif args.command == "add-review-receipt":
            result = add_review_receipt(args.workspace, args.receipt)
        elif args.command == "draft-review-receipt":
            result = draft_review_receipt_from_proposal(
                args.workspace,
                receipt_id=args.receipt_id,
                proposal_id=args.proposal_id,
                verification_requirement_id=args.verification_requirement_id,
                evidence_requirement_id=args.evidence_requirement_id,
                result=args.result,
                summary=args.summary,
            )
        elif args.command == "emit-workbench":
            result = emit_project_workbench(args.workspace, args.out)
        else:
            result = validate_emitted_project_workbench(args.workspace, args.out)
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    except ProjectWorkspaceError as error:
        print(f"error: {error}", file=__import__("sys").stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
