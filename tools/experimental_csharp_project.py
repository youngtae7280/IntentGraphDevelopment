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
PROPOSAL_AUTHORITY = {
    "targetRepositoryMutation": False,
    "automaticCodeApplication": False,
    "selfAuthorized": False,
    "networkRequired": False,
    "credentialAccessAllowed": False,
    "graphMutationApplied": False,
    "approvalRecorded": False,
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
        "workItems": [],
        "mappings": [],
        "changeProposals": [],
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
    for key in ("workItems", "mappings", "changeProposals", "verification", "evidence", "history"):
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
        if item["changeStatus"] not in {"not-proposed", "proposal-review-required"} or item["verificationStatus"] not in {"not-required", "snapshot-only", "requirements-recorded"}:
            raise ProjectWorkspaceError(f"work item {item['id']} claims an unsupported change or verification state")
    fact_by_id = {fact.get("id"): fact for fact in facts.get("facts", []) if isinstance(fact, dict) and isinstance(fact.get("id"), str)}
    fact_ids = set(fact_by_id)
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
    proposed_work_ids = {proposal["workItemId"] for proposal in proposals}
    for item in state["workItems"]:
        if item["id"] in proposed_work_ids:
            if item["changeStatus"] != "proposal-review-required" or item["verificationStatus"] != "requirements-recorded":
                raise ProjectWorkspaceError("work item proposal status must agree with its change proposal")
        elif item["changeStatus"] != "not-proposed":
            raise ProjectWorkspaceError("work item without a proposal must remain not-proposed")
    for key in ("verification", "evidence", "history"):
        validate_record_ids(state[key], key)
    if not state["verification"] or not state["evidence"] or not state["history"]:
        raise ProjectWorkspaceError("project state must retain snapshot verification, evidence, and history")
    return state, snapshot_manifest, snapshot_artifacts, {"summary": summary, "facts": facts, "mappingIds": mapping_ids, "proposals": proposals}


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
    if any(item["workItemId"] == work_id for item in state["mappings"]):
        raise ProjectWorkspaceError("work item already has a mapping candidate")
    if not fact_ids or len(set(fact_ids)) != len(fact_ids):
        raise ProjectWorkspaceError("mapping candidate must reference one or more unique fact identifiers")
    known_facts = {fact.get("id") for fact in data["facts"].get("facts", []) if isinstance(fact, dict)}
    if any(fact_id not in known_facts for fact_id in fact_ids):
        raise ProjectWorkspaceError("mapping candidate contains an unknown code fact identifier")
    if not rationale.strip():
        raise ProjectWorkspaceError("mapping candidate rationale must not be blank")
    mapping_id = f"mapping.{work_id}.candidate"
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
    work["mappingStatus"] = "candidate"
    work["status"] = "mapping-candidate"
    state["history"].append(
        {
            "id": f"history.mapping.{work_id}",
            "kind": "mapping-candidate-recorded",
            "summary": f"Recorded declared mapping candidate {mapping_id}; acceptance is not automatic.",
        }
    )
    write_json(project_workspace / PROJECT_FILE, state)
    validate_project_workspace(project_workspace)
    return {"result": "pass", "command": "add-experimental-csharp-mapping-candidate", "mappingId": mapping_id, "authority": PROJECT_AUTHORITY}


def add_change_proposal(project_workspace: Path, proposal_path: Path) -> dict[str, Any]:
    project_workspace = project_workspace.resolve()
    state, _, _, data = validate_project_workspace(project_workspace)
    proposal = read_json(proposal_path.resolve())
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
            "summary": f"Recorded non-applied proposal {proposal['id']} with graph delta and code diff evidence; no source change was applied.",
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
    project = state["project"]
    project_node = f"project.{project['id']}"
    nodes.append(semantic_node(project_node, "project", project["title"], {"logicalSourceRoot": project["logicalSourceRoot"], "sourceDigest": project["sourceDigest"], "sourceRole": project["sourceRole"]}))
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
    all_ids = {node["id"] for node in nodes}
    if len(all_ids) != len(nodes) or len({edge["id"] for edge in edges}) != len(edges) or any(edge["source"] not in all_ids or edge["target"] not in all_ids for edge in edges):
        raise ProjectWorkspaceError("project projection graph integrity is invalid")
    summary = data["summary"]
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
            "externalSourcePathPersisted": False,
            "codeContentShown": False,
            "proposedCodeDiffFragmentsShown": any(proposal["codeDiffs"] for proposal in proposals),
        },
        "workflow": {**{key: state[key] for key in ("workItems", "mappings", "verification", "evidence", "history")}, "changeProposals": proposals, "proposalDeltas": sorted(proposal_deltas, key=lambda item: item["id"])},
        "authority": state["authority"],
        "graph": {
            "nodes": sorted(nodes, key=lambda item: item["id"]),
            "edges": sorted(edges, key=lambda item: item["id"]),
            "categoryCounts": counts(nodes, "category"),
            "relationCounts": counts(edges, "kind"),
            "defaultView": {"codeKinds": ["file", "namespace", "type"], "semanticCategories": ["project", "work", "intent", "mapping", "proposal", "verification", "evidence", "authority", "history", "code-capsule"]},
            "views": {
                "overview": {"title": "Project overview", "nodeIds": sorted(base_semantic_node_ids | set(capsule_ids.values())), "summary": "Intent, work, proposal, evidence, authority, history, and aggregated code capsules."},
                "impact": {"title": "Active work impact", "nodeIds": sorted(base_semantic_node_ids | impacted_code_ids | impacted_capsule_ids), "summary": "Active semantic work records plus mapped and proposed code facts with direct syntax neighbors."},
                "code": {"title": "Code topology", "nodeIds": sorted(structural_code_ids | set(capsule_ids.values()) | {project_node}), "summary": "Aggregated code capsules and structural file, namespace, and type facts."},
                "all": {"title": "All matching records", "nodeIds": sorted(all_ids), "summary": "Every projected semantic and code fact record."},
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
        "uiContract": {"staticLocalHtml": True, "graphLibrary": "cytoscape", "networkRequired": False, "externalRuntimeUrlsAllowed": False, "graphMutationFromUi": False, "approvalControlsPresent": False},
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
    :root { --left: 286px; --right: 356px; --bg:#0a1016; --panel:#111923; --panel2:#0e151d; --line:#263544; --text:#e1e9f1; --muted:#8d9cac; --accent:#4ec6ba; --warn:#deb96f; --danger:#e47f76; --code:#8fa9c3; --intent:#da9f66; --work:#72b790; --evidence:#b68ee0; --history:#8f9bb2; --proposal:#e47f76; }
    * { box-sizing:border-box; } body { margin:0; background:var(--bg); color:var(--text); font:13px/1.45 Inter,Segoe UI,Arial,sans-serif; letter-spacing:0; overflow:hidden; }
    button,input,select { font:inherit; } button { color:var(--text); background:#172331; border:1px solid #314556; border-radius:4px; padding:6px 9px; cursor:pointer; } button:hover,button.active { border-color:var(--accent); background:#19343a; } input,select { width:100%; color:var(--text); background:#0b1219; border:1px solid #314556; border-radius:4px; padding:7px 8px; }
    .app { height:100vh; display:grid; grid-template-rows:54px 1fr; } .topbar { display:flex; align-items:center; justify-content:space-between; padding:0 16px; border-bottom:1px solid var(--line); background:#0d151e; } .brand { display:flex; align-items:baseline; gap:9px; } .brand strong { font-size:15px; letter-spacing:.2px; } .brand span { color:var(--muted); } .badges { display:flex; gap:6px; } .badge { color:#aebccb; border:1px solid #314556; padding:3px 7px; border-radius:99px; font-size:11px; } .badge.accent { color:#9ee8df; border-color:#266a63; }
    .workspace { min-height:0; display:grid; grid-template-columns:var(--left) 7px minmax(440px,1fr) 7px var(--right); } .rail,.inspector { overflow:auto; background:var(--panel2); } .rail { border-right:1px solid var(--line); } .inspector { border-left:1px solid var(--line); } .resizer { background:#101a24; cursor:col-resize; position:relative; } .resizer:hover,.resizer.active { background:var(--accent); } .section { padding:14px; border-bottom:1px solid var(--line); } h2 { margin:0 0 9px; font-size:11px; text-transform:uppercase; color:#97aabb; letter-spacing:.7px; } h3 { margin:0 0 7px; font-size:15px; } p { margin:5px 0; color:#b8c5d0; } label { display:block; margin:8px 0 4px; color:var(--muted); font-size:11px; } .modes { display:grid; grid-template-columns:1fr 1fr; gap:5px; } .modes button:last-child { grid-column:span 2; }
    .work-list { display:grid; gap:7px; } .work-card { text-align:left; padding:9px; background:#111c25; } .work-card small { display:block; color:var(--muted); margin-top:3px; } .work-card .state { color:#9ee8df; text-transform:uppercase; font-size:10px; letter-spacing:.5px; } .work-card.unmapped .state { color:var(--warn); } .empty { color:var(--muted); font-style:italic; padding:7px 0; } .metrics { display:grid; grid-template-columns:1fr 1fr; gap:7px; } .metric { padding:8px; border:1px solid var(--line); background:#0c141c; } .metric strong { display:block; font-size:16px; } .metric span { color:var(--muted); font-size:11px; }
    .canvas { min-width:0; min-height:0; display:grid; grid-template-rows:68px minmax(0,1fr) 174px; background:#0b1219; } .canvasbar { display:flex; align-items:center; justify-content:space-between; padding:12px 16px; border-bottom:1px solid var(--line); } h1 { margin:0; font-size:16px; } .canvasbar p { font-size:11px; margin:2px 0 0; color:var(--muted); } .tools { display:flex; gap:5px; } .icon { min-width:32px; } #projectGraph { min-height:0; } .review-tray { border-top:1px solid var(--line); display:grid; grid-template-columns:1.2fr 1fr 1fr; overflow:auto; } .tray-section { padding:12px; border-right:1px solid var(--line); } .tray-section:last-child { border-right:0; } .tray-title { color:#9aacbb; text-transform:uppercase; font-size:10px; letter-spacing:.65px; margin-bottom:6px; } .state-line { color:#b6c4d1; } .state-line strong { color:var(--warn); } .detail { padding:8px; background:#0d151e; border:1px solid #2a3a49; border-radius:4px; } .detail + .detail { margin-top:8px; } .kv { display:grid; grid-template-columns:112px 1fr; gap:4px 8px; margin:8px 0 0; } .kv dt { color:var(--muted); } .kv dd { margin:0; overflow-wrap:anywhere; } .status-list { display:grid; gap:6px; } .status-row { display:flex; justify-content:space-between; gap:10px; padding:6px 0; border-bottom:1px solid #1e2a35; } .status-row:last-child { border-bottom:0; } .status-row span:last-child { color:var(--warn); text-align:right; } .boundary { color:#b7c7d5; } .boundary strong { color:#9ee8df; } .legend { display:grid; grid-template-columns:1fr 1fr; gap:6px; color:#c4d0db; } .legend i { width:10px; height:10px; display:inline-block; border-radius:50%; margin-right:5px; } .delta-list { display:grid; gap:4px; margin-top:8px; } .delta-step { width:100%; text-align:left; font-size:11px; padding:5px 7px; } .diff { margin:9px 0 0; padding:9px; overflow:auto; white-space:pre; background:#071018; border:1px solid #2a3d4e; color:#c9d8e5; font:11px/1.45 Consolas,monospace; }
    @media (max-width: 980px) { :root { --left:240px; --right:300px; } .review-tray { grid-template-columns:1fr; } .canvas { grid-template-rows:68px minmax(0,1fr) 220px; } } @media (max-width: 760px) { body { overflow:auto; } .app { height:auto; min-height:100vh; } .workspace { grid-template-columns:1fr; } .resizer { display:none; } .rail,.inspector { border:0; } .canvas { min-height:560px; } }
  </style>
</head>
<body>
  <div class="app">
    <header class="topbar"><div class="brand"><strong>IntentGraph</strong><span>Project workbench</span></div><div class="badges"><span class="badge accent">local semantic overlay</span><span class="badge" id="projectBadge"></span><span class="badge" id="snapshotBadge"></span></div></header>
    <div class="workspace">
      <aside class="rail">
        <section class="section"><h2>Graph lens</h2><div class="modes"><button class="mode active" data-mode="overview">Project</button><button class="mode" data-mode="impact">Active work</button><button class="mode" data-mode="code">Code topology</button><button class="mode" data-mode="all">All matching</button><button class="mode" data-mode="focus">Focus selection</button><button id="clearSelection">Clear focus</button></div></section>
        <section class="section"><h2>Find</h2><label for="search">Node, relation, or source file</label><input id="search" type="search" placeholder="Find project or code fact"><label for="categoryFilter">Node category</label><select id="categoryFilter"></select><label for="relationFilter">Relation kind</label><select id="relationFilter"></select></section>
        <section class="section"><h2>Active work</h2><div id="workList" class="work-list"></div></section>
        <section class="section"><h2>Project snapshot</h2><div id="metrics" class="metrics"></div></section>
        <section class="section"><h2>Legend</h2><div class="legend"><div><i style="background:var(--code)"></i>Code fact</div><div><i style="background:var(--intent)"></i>Intent</div><div><i style="background:var(--work)"></i>Work item</div><div><i style="background:var(--evidence)"></i>Evidence / verify</div><div><i style="background:var(--history)"></i>History / authority</div></div></section>
      </aside>
      <div class="resizer" data-side="left" role="separator" aria-label="Resize navigation"></div>
      <main class="canvas">
        <div class="canvasbar"><div><h1 id="graphTitle">Project overview</h1><p id="graphSummary"></p></div><div class="tools"><button class="icon" id="zoomOut" title="Zoom out">-</button><button class="icon" id="zoomIn" title="Zoom in">+</button><button class="icon" id="fitGraph" title="Fit graph">Fit</button></div></div>
        <div id="projectGraph" aria-label="IntentGraph project graph"></div>
        <section class="review-tray"><div class="tray-section"><div class="tray-title">Change review</div><div id="changePanel"></div><div id="deltaList" class="delta-list"></div></div><div class="tray-section"><div class="tray-title">Verification and evidence</div><div id="evidencePanel"></div></div><div class="tray-section"><div class="tray-title">Authority and history</div><div id="authorityPanel"></div></div></section>
      </main>
      <div class="resizer" data-side="right" role="separator" aria-label="Resize inspector"></div>
      <aside class="inspector"><section class="section"><h2>Selection</h2><div id="selectionInspector" class="empty">Select a node or relation to inspect its semantic and source provenance.</div></section><section class="section"><h2>What this view does not claim</h2><div id="boundaryPanel" class="boundary"></div></section></aside>
    </div>
  </div>
  <script id="workbench-data" type="application/json">__WORKBENCH_DATA__</script>
  <script>
    const model = JSON.parse(document.getElementById('workbench-data').textContent);
    const allNodes = model.graph.nodes, allEdges = model.graph.edges;
    const nodeById = new Map(allNodes.map(node => [node.id,node]));
    const state = { mode:'overview', selected:null, cy:null };
    const colors = { code:'#8fa9c3', project:'#4ec6ba', work:'#72b790', intent:'#da9f66', mapping:'#efc66d', proposal:'#e47f76', verification:'#b68ee0', evidence:'#b68ee0', authority:'#8f9bb2', history:'#8f9bb2' };
    const safe = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
    const short = value => String(value || '').replace('sha256:','').slice(0,12);
    const rows = entries => `<dl class="kv">${entries.map(([key,value])=>`<dt>${safe(key)}</dt><dd>${safe(value)}</dd>`).join('')}</dl>`;
    function populate(id, values, label) { document.getElementById(id).innerHTML=`<option value="">All ${safe(label)}</option>`+values.map(value=>`<option value="${safe(value)}">${safe(value)}</option>`).join(''); }
    function init() { populate('categoryFilter',Object.keys(model.graph.categoryCounts),'categories'); populate('relationFilter',Object.keys(model.graph.relationCounts),'relations'); ['search','categoryFilter','relationFilter'].forEach(id=>{const c=document.getElementById(id);c.addEventListener('input',renderGraph);c.addEventListener('change',renderGraph);}); document.querySelectorAll('[data-mode]').forEach(button=>button.addEventListener('click',()=>{state.mode=button.dataset.mode;document.querySelectorAll('[data-mode]').forEach(item=>item.classList.toggle('active',item===button));renderGraph();}));document.getElementById('clearSelection').addEventListener('click',()=>{state.selected=null;renderGraph();renderSelection();}); }
    function filters() { return { search:document.getElementById('search').value.trim().toLowerCase(), category:document.getElementById('categoryFilter').value, relation:document.getElementById('relationFilter').value }; }
    function selectedNodes() { const f=filters(); const detailRequested=Boolean(f.search||f.category||f.relation); let view=model.graph.views[state.mode]||model.graph.views.overview; let allowed=new Set(view.nodeIds); if(state.mode==='overview'&&detailRequested) allowed=new Set(model.graph.views.all.nodeIds); let nodes=allNodes.filter(node=>allowed.has(node.id)&&(!f.category||node.category===f.category)&&(!f.search||`${node.label} ${node.id} ${node.kind} ${node.source?.file||''}`.toLowerCase().includes(f.search))); if(state.mode==='focus'&&state.selected) { const near=new Set([state.selected.id]); allEdges.forEach(edge=>{if(edge.id===state.selected.id||edge.source===state.selected.id||edge.target===state.selected.id){near.add(edge.source);near.add(edge.target);}});nodes=nodes.filter(node=>near.has(node.id)); } return nodes; }
    function graphData() { const nodes=selectedNodes(), ids=new Set(nodes.map(node=>node.id)), f=filters(); const edges=allEdges.filter(edge=>ids.has(edge.source)&&ids.has(edge.target)&&(!f.relation||edge.kind===f.relation)); return {nodes,edges,elements:[...nodes.map(node=>({data:{id:node.id,label:node.label,category:node.category,kind:node.kind,deltaState:node.deltaState||'unchanged'}})),...edges.map(edge=>({data:{id:edge.id,source:edge.source,target:edge.target,kind:edge.kind,category:edge.category}}))]}; }
    function renderGraph() { const graph=graphData(); const view=model.graph.views[state.mode]||model.graph.views.overview; document.getElementById('graphTitle').textContent=view.title;document.getElementById('graphSummary').textContent=`${view.summary} ${graph.nodes.length.toLocaleString()} nodes / ${graph.edges.length.toLocaleString()} relations visible`; if(state.cy)state.cy.destroy(); state.cy=cytoscape({container:document.getElementById('projectGraph'),elements:graph.elements,style:[{selector:'node',style:{'background-color':el=>colors[el.data('category')]||'#8fa9c3','label':el=>el.data('label'),'color':'#d8e2eb','font-size':10,'text-wrap':'ellipsis','text-max-width':118,'text-valign':'bottom','text-margin-y':6,'width':el=>el.data('category')==='project'?25:el.data('category')==='code'?(el.data('kind')==='file'?20:el.data('kind')==='type'?16:14):el.data('category')==='code-capsule'?44:19,'height':el=>el.data('category')==='project'?25:el.data('category')==='code'?(el.data('kind')==='file'?20:el.data('kind')==='type'?16:14):el.data('category')==='code-capsule'?28:19,'border-width':1,'border-color':'#172531'}},{selector:'node[category = "code-capsule"]',style:{'background-color':'#31566e','shape':'round-rectangle','border-width':2,'border-color':'#6f9ab5','font-size':11,'text-max-width':145}},{selector:'node[deltaState = "proposed-change"]',style:{'border-width':3,'border-color':'#e47f76'}},{selector:'edge',style:{'width':1,'line-color':'#405262','target-arrow-color':'#405262','target-arrow-shape':'triangle','curve-style':'bezier','opacity':.68}},{selector:'edge[category = "capsule-relation"]',style:{'line-color':'#54788f','target-arrow-color':'#54788f','width':2}},{selector:'edge[category = "mapping-relation"]',style:{'line-color':'#efc66d','target-arrow-color':'#efc66d','line-style':'dashed','width':2}},{selector:'edge[category = "delta-relation"]',style:{'line-color':'#e47f76','target-arrow-color':'#e47f76','line-style':'dashed','width':2}},{selector:'edge[kind = "invokes-syntax"]',style:{'line-color':'#8573a3','target-arrow-color':'#8573a3','line-style':'dashed'}},{selector:':selected',style:{'border-width':3,'border-color':'#4ec6ba','line-color':'#4ec6ba','target-arrow-color':'#4ec6ba','z-index':99}},{selector:'.dim',style:{'opacity':.15}}],layout:{name:'cose',animate:false,randomize:false,fit:true,padding:44,nodeRepulsion:9300,idealEdgeLength:75,gravity:.6},minZoom:.22,maxZoom:2.6,wheelSensitivity:.16}); state.cy.on('tap','node',event=>{state.selected={type:'node',id:event.target.id()};renderSelection();highlight();}); state.cy.on('tap','edge',event=>{state.selected={type:'edge',id:event.target.id()};renderSelection();highlight();});state.cy.on('tap',event=>{if(event.target===state.cy){state.selected=null;renderSelection();}}); state.cy.on('zoom',semanticZoom);semanticZoom();highlight(); }
    function semanticZoom(){const visible=state.cy.zoom()>.62;state.cy.style().selector('node').style('font-size',visible?10:0).update();}
    function highlight(){if(!state.cy||!state.selected)return;const item=state.cy.$id(state.selected.id);if(!item.length)return;state.cy.elements().addClass('dim');item.removeClass('dim').select();if(state.selected.type==='node')item.connectedEdges().removeClass('dim');if(state.selected.type==='edge')item.connectedNodes().removeClass('dim');}
    function renderSelection(){const panel=document.getElementById('selectionInspector');if(!state.selected){panel.className='empty';panel.textContent='Select a graph node or relation to inspect its semantic and source provenance.';return;}if(state.selected.type==='node'){const node=nodeById.get(state.selected.id);if(!node)return;const base=[['category',node.category],['kind',node.kind],['identifier',node.id]];let diffHtml='';if(node.category==='code'){const diffs=node.codeDiffs||[];base.push(['source file',node.source.file],['range',`${node.source.location?.lineStart||'file'}:${node.source.location?.columnStart||''} - ${node.source.location?.lineEnd||''}:${node.source.location?.columnEnd||''}`],['source digest',short(node.source.digest)],['confidence',node.provenance.confidence],['delta state',node.deltaState||'unchanged'],['interpretation',node.details.interpretation],['code diff',diffs.length?`${diffs.length} proposed diff(s) below`:'No change proposal recorded']);diffHtml=diffs.map(diff=>`<h3 style="margin-top:12px">${safe(diff.proposalTitle)}</h3><p>${safe(diff.sourceFile)}</p><pre class="diff">${safe(diff.unifiedDiff)}</pre>`).join('');}else base.push(...Object.entries(node.details).map(([key,value])=>[key,typeof value==='object'?JSON.stringify(value):value]));panel.className='detail';panel.innerHTML=`<h3>${safe(node.label)}</h3>${rows(base)}${diffHtml}`; }else{const edge=allEdges.find(item=>item.id===state.selected.id);if(!edge)return;panel.className='detail';panel.innerHTML=`<h3>${safe(edge.kind)}</h3>${rows([['category',edge.category],['source',edge.source],['target',edge.target],...Object.entries(edge.details||{}).map(([key,value])=>[key,typeof value==='object'?JSON.stringify(value):value])])}`;}}
    function focusWork(workId){state.selected={type:'node',id:`work.${workId}`};state.mode='impact';document.querySelectorAll('[data-mode]').forEach(item=>item.classList.toggle('active',item.dataset.mode==='impact'));renderGraph();renderSelection();}
    function focusDelta(nodeId){state.selected={type:'node',id:nodeId};state.mode='impact';document.querySelectorAll('[data-mode]').forEach(item=>item.classList.toggle('active',item.dataset.mode==='impact'));renderGraph();renderSelection();}
    function staticPanels(){document.getElementById('projectBadge').textContent=model.project.id;document.getElementById('snapshotBadge').textContent=`snapshot ${short(model.snapshot.sourceDigest)}`;const metrics=[['files',model.snapshot.sourceFileCount],['facts',model.snapshot.factCount],['relations',model.snapshot.relationCount],['work items',model.workflow.workItems.length]];document.getElementById('metrics').innerHTML=metrics.map(([label,value])=>`<div class="metric"><strong>${Number(value).toLocaleString()}</strong><span>${safe(label)}</span></div>`).join('');const works=model.workflow.workItems;document.getElementById('workList').innerHTML=works.length?works.map(work=>`<button class="work-card ${work.mappingStatus==='unmapped'?'unmapped':''}" data-work="${safe(work.id)}"><span class="state">${safe(work.status)} / ${safe(work.mappingStatus)}</span><strong>${safe(work.title)}</strong><small>${safe(work.request)}</small></button>`).join(''):'<div class="empty">No work request has been recorded. Use the project workspace command to add one.</div>';document.querySelectorAll('[data-work]').forEach(button=>button.addEventListener('click',()=>focusWork(button.dataset.work)));const c=model.changeReview;document.getElementById('changePanel').innerHTML=`<div class="state-line"><strong>${safe(c.status)}</strong><br>${safe(c.summary)}<br><small>${safe(c.reason)}</small></div>`;const deltas=model.workflow.proposalDeltas||[];document.getElementById('deltaList').innerHTML=deltas.length?deltas.map(delta=>`<button class="delta-step" data-delta="${safe(delta.targetNodeId)}">${safe(delta.kind)}: ${safe(delta.label)}</button>`).join(''):'<div class="empty">No graph delta is recorded.</div>';document.querySelectorAll('[data-delta]').forEach(button=>button.addEventListener('click',()=>focusDelta(button.dataset.delta)));document.getElementById('evidencePanel').innerHTML=`<div class="state-line">${model.workflow.verification.map(item=>`<strong>${safe(item.result)}</strong> ${safe(item.kind)}`).join('<br>')}<br>${model.workflow.evidence.map(item=>`<strong>${safe(item.result)}</strong> ${safe(item.kind)}`).join('<br>')}</div>`;document.getElementById('authorityPanel').innerHTML=`<div class="state-line"><strong>read-only boundary</strong><br>Target edits: ${safe(model.authority.targetRepositoryMutation)}<br>Automatic application: ${safe(model.authority.automaticCodeApplication)}<br>History records: ${model.workflow.history.length}</div>`;document.getElementById('boundaryPanel').innerHTML='<strong>This page is a project-state projection.</strong><br>It can show recorded requests, candidate mappings, review-required proposals, graph delta, code diff, verification, evidence, authority, and history alongside C# syntax facts. It does not resolve calls, apply changes, or approve work.';}
    function resize(){document.querySelectorAll('.resizer').forEach(handle=>handle.addEventListener('pointerdown',event=>{event.preventDefault();handle.classList.add('active');const side=handle.dataset.side,start=event.clientX,variable=side==='left'?'--left':'--right',initial=parseInt(getComputedStyle(document.documentElement).getPropertyValue(variable));const move=e=>{const delta=e.clientX-start;const next=side==='left'?initial+delta:initial-delta;document.documentElement.style.setProperty(variable,`${Math.max(230,Math.min(560,next))}px`);state.cy?.resize();};const up=()=>{handle.classList.remove('active');window.removeEventListener('pointermove',move);window.removeEventListener('pointerup',up);state.cy?.fit(undefined,44);};window.addEventListener('pointermove',move);window.addEventListener('pointerup',up);}));}
    document.getElementById('zoomIn').addEventListener('click',()=>state.cy.zoom({level:state.cy.zoom()*1.18,renderedPosition:{x:state.cy.width()/2,y:state.cy.height()/2}}));document.getElementById('zoomOut').addEventListener('click',()=>state.cy.zoom({level:state.cy.zoom()/1.18,renderedPosition:{x:state.cy.width()/2,y:state.cy.height()/2}}));document.getElementById('fitGraph').addEventListener('click',()=>state.cy.fit(undefined,44));init();staticPanels();renderGraph();renderSelection();resize();
  </script>
</body>
</html>'''


def render_html(projection: dict[str, Any]) -> str:
    return HTML_TEMPLATE.replace("__WORKBENCH_DATA__", html_data(projection))


SERVER_UI_EXTENSION = r'''<style>
  .new-work-trigger { position:fixed; right:18px; bottom:18px; z-index:30; background:#16413f; border-color:#3b9c94; color:#d9fffa; box-shadow:0 10px 30px rgba(0,0,0,.35); }
  .new-work-dialog { width:min(520px,calc(100vw - 32px)); color:#e1e9f1; background:#111923; border:1px solid #355061; border-radius:6px; padding:0; box-shadow:0 20px 60px rgba(0,0,0,.55); }
  .new-work-dialog::backdrop { background:rgba(0,0,0,.66); } .new-work-form { padding:18px; display:grid; gap:10px; } .new-work-form h2 { margin:0; color:#c8d7e5; font-size:15px; letter-spacing:0; text-transform:none; } .new-work-form label { margin:0; font-size:12px; } .new-work-form textarea { min-height:110px; resize:vertical; color:#e1e9f1; background:#0b1219; border:1px solid #314556; border-radius:4px; padding:8px; font:inherit; } .new-work-actions { display:flex; justify-content:flex-end; gap:7px; } .new-work-message { min-height:18px; color:#deb96f; font-size:12px; }
</style>
<button id="newWorkTrigger" class="new-work-trigger" type="button">New work request</button>
<dialog id="newWorkDialog" class="new-work-dialog"><form id="newWorkForm" class="new-work-form" method="dialog"><h2>Record a work request</h2><p>This records a request in the local IntentGraph project workspace. It does not edit the source project.</p><label for="newWorkId">Stable work id</label><input id="newWorkId" name="workId" required pattern="[a-z][a-z0-9.-]{2,100}" placeholder="example-work-item"><label for="newWorkTitle">Title</label><input id="newWorkTitle" name="title" required maxlength="180" placeholder="Short work title"><label for="newWorkRequest">Request</label><textarea id="newWorkRequest" name="request" required maxlength="12000" placeholder="Describe the desired behavior or change."></textarea><div id="newWorkMessage" class="new-work-message"></div><div class="new-work-actions"><button id="cancelNewWork" type="button">Cancel</button><button type="submit">Record request</button></div></form></dialog>
<script>
  (() => { const dialog=document.getElementById('newWorkDialog'), trigger=document.getElementById('newWorkTrigger'), form=document.getElementById('newWorkForm'), message=document.getElementById('newWorkMessage'); trigger.addEventListener('click',()=>dialog.showModal()); document.getElementById('cancelNewWork').addEventListener('click',()=>dialog.close()); form.addEventListener('submit',async event=>{event.preventDefault();message.textContent='Recording request...';const body={workId:form.workId.value.trim(),title:form.title.value.trim(),request:form.request.value.trim()};try{const response=await fetch('/api/work-requests',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const result=await response.json();if(!response.ok){throw new Error(result.error||'Request could not be recorded.');}message.textContent='Recorded. Reloading workbench...';window.setTimeout(()=>window.location.reload(),250);}catch(error){message.textContent=error.message||'Request could not be recorded.';}}); })();
</script>'''


def render_server_html(projection: dict[str, Any]) -> str:
    """Render the local-server variant. The static export intentionally does not include its API client."""
    return render_html(projection).replace("</body>", SERVER_UI_EXTENSION + "\n</body>")


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
        if not isinstance(node, dict) or node.get("category") not in {"code", "code-capsule", "project", "work", "intent", "mapping", "proposal", "verification", "evidence", "authority", "history"}:
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
    for marker in ["id=\"projectGraph\"", "id=\"workList\"", "id=\"selectionInspector\"", "id=\"changePanel\"", "id=\"deltaList\"", "id=\"evidencePanel\"", "id=\"authorityPanel\"", "id=\"zoomIn\"", "id=\"zoomOut\"", "assets/cytoscape.min.js"]:
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
    proposal = sub.add_parser("add-change-proposal")
    proposal.add_argument("--workspace", required=True, type=Path)
    proposal.add_argument("--proposal", required=True, type=Path)
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
        elif args.command == "add-change-proposal":
            result = add_change_proposal(args.workspace, args.proposal)
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
