"""Create and render a local semantic-overlay project workspace over a C# fact snapshot.

The workspace owns IntentGraph records only.  Its nested snapshot is an immutable copy
of a validated P9.10 C# fact workspace; it never points at or edits the source project.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
import re
import shutil
import tempfile
import time
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
VERIFIER_RESULT_ROLE = "intentgraph-experimental-csharp-verifier-result"
VERIFIER_RESULT_SCOPE = "experimental-csharp-semantic-overlay-verifier-result"
VERIFIER_RESULT_STATUS = "verifier-result-imported"
VERIFIER_RESULT_RESULTS = {"pass", "fail", "blocked"}
VERIFIER_RESULT_KINDS = {"build", "test", "runtime-smoke", "static-analysis"}
VERIFIER_EVIDENCE_CONTENT_TYPE = "application/vnd.intentgraph.verifier-evidence+json"
VERIFIER_ARTIFACT_KINDS = {
    "build-report", "runtime-observation", "static-analysis-report",
    "stderr-log", "stdout-log", "test-report",
}
VERIFIER_ARTIFACT_MEDIA_TYPES = {"application/json", "application/xml", "text/plain"}
VERIFIER_ARTIFACT_AVAILABILITY = "external-digest-only"
EVIDENCE_DECISION_ROLE = "intentgraph-experimental-csharp-evidence-decision"
EVIDENCE_DECISION_SCOPE = "experimental-csharp-semantic-overlay-evidence-decision"
EVIDENCE_DECISION_STATUS = "evidence-decision-recorded"
EVIDENCE_DECISIONS = {"accepted", "rejected"}
EVIDENCE_REVIEWER_ROLES = {"maintainer", "quality-reviewer", "security-reviewer"}
EVIDENCE_DECISION_PERMISSIONS = {
    "accepted": "evidence.accept",
    "rejected": "evidence.reject",
}
PROPOSAL_VERIFICATION_KINDS = {
    "build-required", "local-review", "runtime-smoke-required",
    "static-analysis-required", "test-required",
}
PROPOSAL_EVIDENCE_KINDS = {
    "build-evidence", "review-note", "runtime-evidence",
    "static-analysis-evidence", "test-evidence",
}
VERIFICATION_KIND_TO_VERIFIER_KINDS = {
    "build-required": ["build"],
    "runtime-smoke-required": ["runtime-smoke"],
    "static-analysis-required": ["static-analysis"],
    "test-required": ["test"],
}
EVIDENCE_KIND_TO_REQUIRED_ARTIFACT_KINDS = {
    "build-evidence": ["build-report"],
    "runtime-evidence": ["runtime-observation"],
    "static-analysis-evidence": ["static-analysis-report"],
    "test-evidence": ["test-report"],
}
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
VERIFIER_RESULT_AUTHORITY = {
    "resultImported": True,
    "verificationExecutedByIntentGraph": False,
    "evidenceCollectedByIntentGraph": False,
    "targetRepositoryMutation": False,
    "automaticCodeApplication": False,
    "selfAuthorized": False,
    "approvalRecorded": False,
    "networkRequired": False,
    "credentialAccessAllowed": False,
}
EVIDENCE_DECISION_AUTHORITY = {
    "decisionRecorded": True,
    "reviewerAuthoritySource": "explicit-local-human-declaration",
    "reviewerAuthenticatedByIntentGraph": False,
    "localWorkspaceReadinessMayChange": True,
    "proposalApprovalRecorded": False,
    "graphMutationApplied": False,
    "targetRepositoryMutation": False,
    "automaticCodeApplication": False,
    "selfAuthorized": False,
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

WORK_STATUSES = {"intake", "mapping-candidate", "mapped", "proposal-ready", "verification-observed", "verified", "blocked", "complete"}
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


def write_bytes_atomic(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        temporary.replace(path)
        if os.name != "nt":
            directory_descriptor = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
    finally:
        temporary.unlink(missing_ok=True)


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    document = (json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode("utf-8")
    write_bytes_atomic(path, document)


@contextmanager
def project_workspace_write_lock(project_workspace: Path, timeout_seconds: float = 10.0):
    """Serialize local writers without making the lock file part of project state."""

    lock_path = project_workspace.parent / f".{project_workspace.name}.intentgraph-project.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = lock_path.open("a+b")
    if handle.seek(0, os.SEEK_END) == 0:
        handle.write(b"0")
        handle.flush()
    deadline = time.monotonic() + timeout_seconds
    acquired = False
    try:
        while not acquired:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
            except OSError as error:
                if time.monotonic() >= deadline:
                    raise ProjectWorkspaceError("project workspace is busy with another writer") from error
                time.sleep(0.05)
        yield
    finally:
        if acquired:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def commit_project_state_atomic(
    project_workspace: Path,
    state: dict[str, Any],
    project_file_before: bytes,
    *,
    operation: str,
) -> None:
    """Commit one locked state-only mutation with compare-and-swap and rollback."""

    project_file = project_workspace / PROJECT_FILE
    if project_file.read_bytes() != project_file_before:
        raise ProjectWorkspaceError(f"project workspace changed during {operation}")
    try:
        write_json_atomic(project_file, state)
        validate_project_workspace(project_workspace)
    except Exception:
        write_bytes_atomic(project_file, project_file_before)
        raise


def digest_json(value: Any) -> str:
    return digest_bytes(canonical_json(value))


WORK_STAGE_REVISION_AUTHORITY = {
    "targetRepositoryMutation": False,
    "automaticCodeApplication": False,
    "verificationExecution": False,
    "runtimeEvidenceCollection": False,
    "approvalAutomation": False,
}


def project_core_digest(state: dict[str, Any]) -> str:
    """Digest the append-only work lifecycle independently of extractor refreshes."""
    history_kinds = {
        "work-request-recorded",
        "mapping-candidate-recorded",
        "mapping-candidate-expanded",
        "non-applied-change-proposal-recorded",
        "review-receipt-recorded",
        "verifier-result-imported",
        "evidence-decision-recorded",
    }
    requirement_kinds = {
        "proposal-verification-requirements",
        "proposal-evidence-requirements",
        "review-receipt",
        "tool-verifier-result",
        "deterministic-verifier-evidence",
        "evidence-acceptance-decision",
        "accepted-verifier-evidence",
        "rejected-verifier-evidence",
    }
    lifecycle = {
        "project": state.get("project"),
        "workItems": state.get("workItems", []),
        "mappings": state.get("mappings", []),
        "changeProposals": state.get("changeProposals", []),
        "reviewReceipts": state.get("reviewReceipts", []),
        "verification": [item for item in state.get("verification", []) if item.get("kind") in requirement_kinds],
        "evidence": [item for item in state.get("evidence", []) if item.get("kind") in requirement_kinds],
        "history": [item for item in state.get("history", []) if item.get("kind") in history_kinds],
    }
    # Empty verifier-result storage is a backward-compatible schema extension. It
    # must not invalidate durable revision digests recorded before P9.29.
    if state.get("verifierResults"):
        lifecycle["verifierResults"] = state["verifierResults"]
    if state.get("evidenceDecisions"):
        lifecycle["evidenceDecisions"] = state["evidenceDecisions"]
    return digest_json(lifecycle)


def evidence_decision_state_records(decision: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Derive the immutable state records represented by one evidence decision."""

    identifier = decision["id"]
    result_id = decision["verifierResultId"]
    outcome = decision["decision"]
    reviewer_id = decision["reviewer"]["id"]
    evidence_digest = decision["subject"]["evidenceDigest"]
    return {
        "verification": {
            "id": f"verification.evidence-decision.{identifier}",
            "kind": "evidence-acceptance-decision",
            "result": outcome,
            "summary": f"Recorded {outcome} for verifier result {result_id}.",
        },
        "evidence": {
            "id": f"evidence.evidence-decision.{identifier}",
            "kind": (
                "accepted-verifier-evidence"
                if outcome == "accepted"
                else "rejected-verifier-evidence"
            ),
            "result": outcome,
            "verifierResultId": result_id,
            "evidenceDigest": evidence_digest,
            "authorityRef": f"authority.evidence-decision.{identifier}",
            "summary": f"Reviewer {reviewer_id} decided evidence {evidence_digest}.",
        },
        "history": {
            "id": f"history.evidence-decision.{identifier}",
            "kind": "evidence-decision-recorded",
            "summary": f"Recorded local evidence decision {identifier} without approving or applying the proposal.",
        },
    }


def append_work_stage_revision(
    state: dict[str, Any],
    *,
    work_item_id: str,
    stage_kind: str,
    before_digest: str,
    record_ids: list[str],
    added_node_ids: list[str],
    changed_node_ids: list[str],
    added_edge_ids: list[str],
    changed_edge_ids: list[str] | None = None,
    code_diff_ids: list[str] | None = None,
) -> dict[str, Any]:
    revisions = state.setdefault("workStageRevisions", [])
    work_revisions = [item for item in revisions if item["workItemId"] == work_item_id]
    sequence = len(work_revisions) + 1
    after_digest = project_core_digest(state)
    identifier = f"revision.{work_item_id[:52]}.{sequence}.{after_digest.removeprefix('sha256:')[:12]}"
    safe_id(identifier, "work stage revision id")
    revision = {
        "id": identifier,
        "workItemId": work_item_id,
        "sequence": sequence,
        "stageKind": stage_kind,
        "predecessorRevisionId": work_revisions[-1]["id"] if work_revisions else None,
        "beforeProjectStateDigest": before_digest,
        "afterProjectStateDigest": after_digest,
        "recordIds": sorted(set(record_ids)),
        "graphDelta": {
            "addedNodeIds": sorted(set(added_node_ids)),
            "changedNodeIds": sorted(set(changed_node_ids)),
            "addedEdgeIds": sorted(set(added_edge_ids)),
            "changedEdgeIds": sorted(set(changed_edge_ids or [])),
        },
        "codeDiffIds": sorted(set(code_diff_ids or [])),
        "authority": WORK_STAGE_REVISION_AUTHORITY,
    }
    revisions.append(revision)
    return revision


def validate_work_stage_revisions(
    state: dict[str, Any],
    *,
    work_ids: set[str],
    proposals: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    revisions = state["workStageRevisions"]
    revision_ids = validate_record_ids(revisions, "work stage revision")
    known_record_ids = {
        record["id"]
        for key in ("verification", "evidence", "history")
        for record in state[key]
    }
    known_diff_ids = {
        diff["id"]
        for proposal in proposals
        for diff in proposal["codeDiffs"]
    }
    expected_fields = {
        "id", "workItemId", "sequence", "stageKind", "predecessorRevisionId",
        "beforeProjectStateDigest", "afterProjectStateDigest", "recordIds",
        "graphDelta", "codeDiffIds", "authority",
    }
    allowed_stage_kinds = {
        "request-recorded",
        "mapping-candidate-recorded",
        "mapping-candidate-expanded",
        "proposal-and-requirements-recorded",
        "review-receipt-recorded",
        "verifier-result-imported",
        "evidence-decision-recorded",
    }
    by_work: dict[str, list[dict[str, Any]]] = {}
    for revision in revisions:
        if set(revision) != expected_fields or revision["id"] not in revision_ids:
            raise ProjectWorkspaceError("work stage revision fields are invalid")
        if revision["workItemId"] not in work_ids or revision["stageKind"] not in allowed_stage_kinds:
            raise ProjectWorkspaceError("work stage revision lifecycle reference is invalid")
        if not isinstance(revision["sequence"], int) or revision["sequence"] < 1:
            raise ProjectWorkspaceError("work stage revision sequence is invalid")
        if not sha256_value(revision["beforeProjectStateDigest"]) or not sha256_value(revision["afterProjectStateDigest"]):
            raise ProjectWorkspaceError("work stage revision state digests are invalid")
        record_ids = revision["recordIds"]
        if not isinstance(record_ids, list) or not record_ids or record_ids != sorted(set(record_ids)) or any(item not in known_record_ids for item in record_ids):
            raise ProjectWorkspaceError("work stage revision record references are invalid")
        graph_delta = revision["graphDelta"]
        if not isinstance(graph_delta, dict) or set(graph_delta) != {"addedNodeIds", "changedNodeIds", "addedEdgeIds", "changedEdgeIds"}:
            raise ProjectWorkspaceError("work stage revision graph delta is invalid")
        for values in graph_delta.values():
            if not isinstance(values, list) or values != sorted(set(values)) or any(not isinstance(item, str) or not item for item in values):
                raise ProjectWorkspaceError("work stage revision graph delta identifiers are invalid")
        diff_ids = revision["codeDiffIds"]
        if not isinstance(diff_ids, list) or diff_ids != sorted(set(diff_ids)) or any(item not in known_diff_ids for item in diff_ids):
            raise ProjectWorkspaceError("work stage revision code diff references are invalid")
        if revision["authority"] != WORK_STAGE_REVISION_AUTHORITY:
            raise ProjectWorkspaceError("work stage revision authority is invalid")
        by_work.setdefault(revision["workItemId"], []).append(revision)
    for records in by_work.values():
        ordered = sorted(records, key=lambda item: item["sequence"])
        if [item["sequence"] for item in ordered] != list(range(1, len(ordered) + 1)):
            raise ProjectWorkspaceError("work stage revision sequence must be contiguous")
        for index, revision in enumerate(ordered):
            expected_predecessor = ordered[index - 1]["id"] if index else None
            if revision["predecessorRevisionId"] != expected_predecessor:
                raise ProjectWorkspaceError("work stage revision predecessor chain is invalid")
    for index, revision in enumerate(revisions):
        if index and revision["beforeProjectStateDigest"] != revisions[index - 1]["afterProjectStateDigest"]:
            raise ProjectWorkspaceError("work stage revision global before/after chain is invalid")
    if revisions and revisions[-1]["afterProjectStateDigest"] != project_core_digest(state):
        raise ProjectWorkspaceError("latest work stage revision does not match current work lifecycle state")
    return revisions


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
        "verifierResults": [],
        "evidenceDecisions": [],
        "workStageRevisions": [],
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


def required_safe_id(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ProjectWorkspaceError(f"{label} must be a string")
    safe_id(value, label)
    return value


def proposal_verifier_bindings(proposal: dict[str, Any]) -> list[dict[str, Any]]:
    """Return explicit verifier bindings, or a safe singleton legacy binding."""

    explicit = proposal.get("verifierBindings")
    if explicit is not None:
        return explicit
    verification = proposal["verificationRequirements"]
    evidence = proposal["evidenceRequirements"]
    if len(verification) != 1 or len(evidence) != 1:
        return []
    allowed_kinds = VERIFICATION_KIND_TO_VERIFIER_KINDS.get(verification[0]["kind"], [])
    artifact_kinds = EVIDENCE_KIND_TO_REQUIRED_ARTIFACT_KINDS.get(evidence[0]["kind"], [])
    if not allowed_kinds or not artifact_kinds:
        return []
    return [
        {
            "verificationRequirementId": verification[0]["id"],
            "evidenceRequirementId": evidence[0]["id"],
            "allowedVerifierKinds": allowed_kinds,
            "requiredArtifactKinds": artifact_kinds,
        }
    ]


def proposal_verifier_pairs(proposal: dict[str, Any]) -> set[tuple[str, str, str]]:
    return {
        (proposal["id"], binding["verificationRequirementId"], binding["evidenceRequirementId"])
        for binding in proposal_verifier_bindings(proposal)
    }


def validate_guided_unified_diff(
    unified_diff: str,
    *,
    source_path: Path,
    source_location: dict[str, Any],
) -> None:
    """Validate a hunk-only unified diff against the immutable snapshot source."""

    if not isinstance(unified_diff, str) or not unified_diff.startswith("@@") or len(unified_diff.encode("utf-8")) > 32768 or "\\" in unified_diff or "\x00" in unified_diff:
        raise ProjectWorkspaceError("guided proposal unified diff is invalid")
    if not source_path.is_file() or source_path.is_symlink():
        raise ProjectWorkspaceError("guided proposal source artifact is unavailable")
    try:
        source_lines = source_path.read_text(encoding="utf-8-sig").splitlines()
    except UnicodeDecodeError as error:
        raise ProjectWorkspaceError("guided proposal source artifact must be UTF-8 text") from error
    diff_lines = unified_diff.splitlines()
    header_pattern = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?: .*)?$")
    line_start = source_location.get("lineStart")
    line_end = source_location.get("lineEnd")
    if not isinstance(line_start, int) or not isinstance(line_end, int) or line_start < 1 or line_end < line_start:
        raise ProjectWorkspaceError("guided proposal code fact source location is invalid")

    hunk_count = 0
    previous_old_end = 0
    overlaps_fact = False
    source_changed = False
    index = 0
    while index < len(diff_lines):
        match = header_pattern.fullmatch(diff_lines[index])
        if match is None:
            raise ProjectWorkspaceError("guided proposal unified diff hunk header is invalid")
        old_start = int(match.group(1))
        old_count = int(match.group(2) or "1")
        new_count = int(match.group(4) or "1")
        if old_start < 1 or old_count < 0 or new_count < 0 or old_start - 1 + old_count > len(source_lines):
            raise ProjectWorkspaceError("guided proposal unified diff hunk range is invalid")
        if old_start < previous_old_end:
            raise ProjectWorkspaceError("guided proposal unified diff hunks must be ordered and non-overlapping")
        hunk_count += 1
        index += 1
        old_cursor = old_start - 1
        seen_old = 0
        seen_new = 0
        removed: list[str] = []
        added: list[str] = []
        while index < len(diff_lines) and not diff_lines[index].startswith("@@"):
            line = diff_lines[index]
            if not line or line[0] not in {" ", "+", "-"}:
                raise ProjectWorkspaceError("guided proposal unified diff line prefix is invalid")
            marker, content = line[0], line[1:]
            if marker in {" ", "-"}:
                if old_cursor >= len(source_lines) or source_lines[old_cursor] != content:
                    raise ProjectWorkspaceError("guided proposal unified diff does not match snapshot source")
                old_cursor += 1
                seen_old += 1
            if marker in {" ", "+"}:
                seen_new += 1
            if marker == "-":
                removed.append(content)
            elif marker == "+":
                added.append(content)
            index += 1
        if seen_old != old_count or seen_new != new_count:
            raise ProjectWorkspaceError("guided proposal unified diff hunk counts are invalid")
        if removed != added:
            source_changed = source_changed or bool(removed or added)
        old_end = old_start + max(old_count, 1) - 1
        overlaps_fact = overlaps_fact or (old_start <= line_end and old_end >= line_start)
        previous_old_end = old_start + old_count

    if hunk_count == 0 or not source_changed:
        raise ProjectWorkspaceError("guided proposal unified diff must describe a real source change")
    if not overlaps_fact:
        raise ProjectWorkspaceError("guided proposal unified diff must overlap its mapped code fact")


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
    if frozenset(proposal) not in {frozenset(expected), frozenset({*expected, "verifierBindings"})}:
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
        if (
            len(record_ids) != len(records)
            or any(set(record) != {"id", "kind", "summary"} for record in records)
            or any(
                not isinstance(record.get("kind"), str)
                or SAFE_ID.fullmatch(record["kind"]) is None
                or not isinstance(record.get("summary"), str)
                or not record["summary"].strip()
                for record in records
            )
        ):
            raise ProjectWorkspaceError(f"change proposal {key} records are invalid")
    verification_by_id = {record["id"]: record for record in proposal["verificationRequirements"]}
    evidence_by_id = {record["id"]: record for record in proposal["evidenceRequirements"]}
    bindings = proposal.get("verifierBindings")
    if bindings is not None:
        if not isinstance(bindings, list):
            raise ProjectWorkspaceError("change proposal verifier bindings must be a list")
        pair_ids: list[tuple[str, str]] = []
        for binding in bindings:
            if not isinstance(binding, dict) or set(binding) != {
                "verificationRequirementId", "evidenceRequirementId",
                "allowedVerifierKinds", "requiredArtifactKinds",
            }:
                raise ProjectWorkspaceError("change proposal verifier binding fields are invalid")
            verification_id = required_safe_id(binding["verificationRequirementId"], "verifier binding verification requirement id")
            evidence_id = required_safe_id(binding["evidenceRequirementId"], "verifier binding evidence requirement id")
            if verification_id not in verification_by_id or evidence_id not in evidence_by_id:
                raise ProjectWorkspaceError("change proposal verifier binding references are invalid")
            allowed_kinds = binding["allowedVerifierKinds"]
            artifact_kinds = binding["requiredArtifactKinds"]
            if (
                not isinstance(allowed_kinds, list)
                or not allowed_kinds
                or allowed_kinds != sorted(set(allowed_kinds))
                or any(not isinstance(kind, str) or kind not in VERIFIER_RESULT_KINDS for kind in allowed_kinds)
                or not isinstance(artifact_kinds, list)
                or not artifact_kinds
                or artifact_kinds != sorted(set(artifact_kinds))
                or any(not isinstance(kind, str) or kind not in VERIFIER_ARTIFACT_KINDS for kind in artifact_kinds)
            ):
                raise ProjectWorkspaceError("change proposal verifier binding kinds are invalid")
            expected_verifier_kinds = VERIFICATION_KIND_TO_VERIFIER_KINDS.get(verification_by_id[verification_id]["kind"], [])
            expected_artifact_kinds = EVIDENCE_KIND_TO_REQUIRED_ARTIFACT_KINDS.get(evidence_by_id[evidence_id]["kind"], [])
            if allowed_kinds != expected_verifier_kinds or artifact_kinds != expected_artifact_kinds:
                raise ProjectWorkspaceError("change proposal verifier binding is incompatible with its requirements")
            pair_ids.append((verification_id, evidence_id))
        if pair_ids != sorted(set(pair_ids)):
            raise ProjectWorkspaceError("change proposal verifier bindings must be uniquely sorted")
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
    required_safe_id(receipt["id"], "review receipt id")
    proposal_id = required_safe_id(receipt["proposalId"], "review receipt proposal id")
    verification_requirement_id = required_safe_id(
        receipt["verificationRequirementId"], "review receipt verification requirement id"
    )
    evidence_requirement_id = required_safe_id(
        receipt["evidenceRequirementId"], "review receipt evidence requirement id"
    )
    proposal = proposal_by_id.get(proposal_id)
    if proposal is None:
        raise ProjectWorkspaceError("review receipt must reference a known change proposal")
    verification_ids = {record["id"] for record in proposal["verificationRequirements"]}
    evidence_ids = {record["id"] for record in proposal["evidenceRequirements"]}
    if verification_requirement_id not in verification_ids or evidence_requirement_id not in evidence_ids:
        raise ProjectWorkspaceError("review receipt requirement references are invalid")
    if not isinstance(receipt["result"], str) or receipt["result"] not in REVIEW_RECEIPT_RESULTS:
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


def verifier_result_pair(result: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(result["proposalId"]),
        str(result["verificationRequirementId"]),
        str(result["evidenceRequirementId"]),
    )


def verifier_result_id_prefix(pair: tuple[str, str, str]) -> str:
    fingerprint = digest_json(
        {
            "proposalId": pair[0],
            "verificationRequirementId": pair[1],
            "evidenceRequirementId": pair[2],
        }
    ).removeprefix("sha256:")[:16]
    prefix = f"result.{pair[0][:52]}.{fingerprint}"
    safe_id(prefix, "verifier result id prefix")
    return prefix


def validate_verifier_result_document(
    result: dict[str, Any],
    *,
    proposal_by_id: dict[str, dict[str, Any]],
    snapshot_logical_source_root: str,
    snapshot_source_digest: str,
    latest_result_by_pair: dict[tuple[str, str, str], dict[str, Any]],
) -> dict[str, Any]:
    assert_no_unsafe_state(result)
    expected = {
        "artifactRole",
        "schemaVersion",
        "scope",
        "id",
        "proposalId",
        "verificationRequirementId",
        "evidenceRequirementId",
        "attempt",
        "result",
        "verifier",
        "invocation",
        "subject",
        "evidence",
        "observationStatus",
        "acceptanceStatus",
        "supersedesResultId",
        "authority",
    }
    if set(result) != expected:
        raise ProjectWorkspaceError("verifier result fields are invalid")
    if (
        result["artifactRole"] != VERIFIER_RESULT_ROLE
        or result["schemaVersion"] != PROJECT_SCHEMA_VERSION
        or result["scope"] != VERIFIER_RESULT_SCOPE
    ):
        raise ProjectWorkspaceError("verifier result role, schema version, or scope is invalid")
    required_safe_id(result["id"], "verifier result id")
    proposal_id = required_safe_id(result["proposalId"], "verifier result proposal id")
    verification_requirement_id = required_safe_id(
        result["verificationRequirementId"], "verifier result verification requirement id"
    )
    evidence_requirement_id = required_safe_id(
        result["evidenceRequirementId"], "verifier result evidence requirement id"
    )
    proposal = proposal_by_id.get(proposal_id)
    if proposal is None:
        raise ProjectWorkspaceError("verifier result must reference a known change proposal")
    binding = next(
        (
            item
            for item in proposal_verifier_bindings(proposal)
            if item["verificationRequirementId"] == verification_requirement_id
            and item["evidenceRequirementId"] == evidence_requirement_id
        ),
        None,
    )
    if binding is None:
        raise ProjectWorkspaceError("verifier result requirement pair is not declared as verifier-compatible")
    if not isinstance(result["result"], str) or result["result"] not in VERIFIER_RESULT_RESULTS:
        raise ProjectWorkspaceError("verifier result status is invalid")

    verifier = result["verifier"]
    if not isinstance(verifier, dict) or set(verifier) != {"id", "kind", "version", "deterministic"}:
        raise ProjectWorkspaceError("verifier identity is invalid")
    required_safe_id(verifier["id"], "verifier id")
    if (
        not isinstance(verifier["kind"], str)
        or verifier["kind"] not in VERIFIER_RESULT_KINDS
        or verifier["kind"] not in binding["allowedVerifierKinds"]
        or not isinstance(verifier["version"], str)
        or not verifier["version"].strip()
        or len(verifier["version"].encode("utf-8")) > 128
        or verifier["deterministic"] is not True
    ):
        raise ProjectWorkspaceError("verifier identity must declare deterministic and typed metadata")

    invocation = result["invocation"]
    if not isinstance(invocation, dict) or set(invocation) != {"id", "digest"}:
        raise ProjectWorkspaceError("verifier invocation identity is invalid")
    required_safe_id(invocation["id"], "verifier invocation id")
    if not sha256_value(invocation["digest"]):
        raise ProjectWorkspaceError("verifier invocation digest is invalid")

    subject = result["subject"]
    if not isinstance(subject, dict) or set(subject) != {"logicalSourceRoot", "snapshotSourceDigest", "proposalDigest"}:
        raise ProjectWorkspaceError("verifier result subject is invalid")
    if (
        subject["logicalSourceRoot"] != snapshot_logical_source_root
        or subject["snapshotSourceDigest"] != snapshot_source_digest
        or subject["proposalDigest"] != digest_json(proposal)
    ):
        raise ProjectWorkspaceError("verifier result subject digest is stale or mismatched")

    evidence = result["evidence"]
    if not isinstance(evidence, dict) or set(evidence) != {"contentType", "byteLength", "digest", "payload"}:
        raise ProjectWorkspaceError("verifier evidence envelope is invalid")
    payload = evidence["payload"]
    if not isinstance(payload, dict) or set(payload) != {"summary", "exitCode", "checks", "metrics", "artifactRefs"}:
        raise ProjectWorkspaceError("verifier evidence payload is invalid")
    if (
        not isinstance(payload["summary"], str)
        or not payload["summary"].strip()
        or len(payload["summary"].encode("utf-8")) > 12000
    ):
        raise ProjectWorkspaceError("verifier evidence summary is invalid")
    checks = payload["checks"]
    if not isinstance(checks, list) or not 1 <= len(checks) <= 256:
        raise ProjectWorkspaceError("verifier evidence checks are invalid")
    check_ids: list[str] = []
    check_results: list[str] = []
    for check in checks:
        if not isinstance(check, dict) or set(check) != {"id", "result", "summary"}:
            raise ProjectWorkspaceError("verifier evidence check fields are invalid")
        required_safe_id(check["id"], "verifier evidence check id")
        if not isinstance(check["result"], str) or check["result"] not in VERIFIER_RESULT_RESULTS:
            raise ProjectWorkspaceError("verifier evidence check result is invalid")
        if (
            not isinstance(check["summary"], str)
            or not check["summary"].strip()
            or len(check["summary"].encode("utf-8")) > 4000
        ):
            raise ProjectWorkspaceError("verifier evidence check summary is invalid")
        check_ids.append(check["id"])
        check_results.append(check["result"])
    if check_ids != sorted(set(check_ids)):
        raise ProjectWorkspaceError("verifier evidence checks must be uniquely sorted by id")

    metrics = payload["metrics"]
    metric_fields = {
        "build": {"errorCount", "warningCount"},
        "static-analysis": {"errorCount", "warningCount"},
        "test": {"total", "passed", "failed", "skipped"},
        "runtime-smoke": {"started", "observed", "responsive", "observationSeconds"},
    }[verifier["kind"]]
    if not isinstance(metrics, dict) or set(metrics) != metric_fields:
        raise ProjectWorkspaceError("verifier evidence metrics do not match the verifier kind")
    if verifier["kind"] in {"build", "static-analysis"}:
        if any(not isinstance(metrics[key], int) or isinstance(metrics[key], bool) or metrics[key] < 0 for key in metric_fields):
            raise ProjectWorkspaceError("build or static-analysis metrics are invalid")
    elif verifier["kind"] == "test":
        if any(not isinstance(metrics[key], int) or isinstance(metrics[key], bool) or metrics[key] < 0 for key in metric_fields):
            raise ProjectWorkspaceError("test metrics are invalid")
        if metrics["total"] != metrics["passed"] + metrics["failed"] + metrics["skipped"]:
            raise ProjectWorkspaceError("test metrics total is inconsistent")
    else:
        if any(not isinstance(metrics[key], bool) for key in ("started", "observed", "responsive")):
            raise ProjectWorkspaceError("runtime-smoke boolean metrics are invalid")
        seconds = metrics["observationSeconds"]
        if not isinstance(seconds, (int, float)) or isinstance(seconds, bool) or not 0 <= seconds <= 86400:
            raise ProjectWorkspaceError("runtime-smoke observation duration is invalid")

    artifact_refs = payload["artifactRefs"]
    if not isinstance(artifact_refs, list) or not 1 <= len(artifact_refs) <= 32:
        raise ProjectWorkspaceError("verifier evidence artifact references are invalid")
    artifact_ids: list[str] = []
    for artifact in artifact_refs:
        if not isinstance(artifact, dict) or set(artifact) != {"id", "kind", "logicalName", "mediaType", "byteLength", "digest", "availability"}:
            raise ProjectWorkspaceError("verifier evidence artifact reference fields are invalid")
        required_safe_id(artifact["id"], "verifier evidence artifact id")
        logical_name = artifact["logicalName"]
        if (
            not isinstance(artifact["kind"], str)
            or artifact["kind"] not in VERIFIER_ARTIFACT_KINDS
            or not isinstance(artifact["mediaType"], str)
            or artifact["mediaType"] not in VERIFIER_ARTIFACT_MEDIA_TYPES
            or artifact["availability"] != VERIFIER_ARTIFACT_AVAILABILITY
            or not isinstance(logical_name, str)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,255}", logical_name)
            or ".." in Path(logical_name).parts
            or not isinstance(artifact["byteLength"], int)
            or isinstance(artifact["byteLength"], bool)
            or not 0 < artifact["byteLength"] <= 2_147_483_647
            or not sha256_value(artifact["digest"])
        ):
            raise ProjectWorkspaceError("verifier evidence artifact reference is invalid")
        artifact_ids.append(artifact["id"])
    if artifact_ids != sorted(set(artifact_ids)):
        raise ProjectWorkspaceError("verifier evidence artifact references must be uniquely sorted by id")
    artifact_kinds = {artifact["kind"] for artifact in artifact_refs}
    if not set(binding["requiredArtifactKinds"]).issubset(artifact_kinds):
        raise ProjectWorkspaceError("verifier evidence is missing an artifact kind required by the proposal binding")

    exit_code = payload["exitCode"]
    if exit_code is not None and (not isinstance(exit_code, int) or isinstance(exit_code, bool) or not 0 <= exit_code <= 255):
        raise ProjectWorkspaceError("verifier evidence exit code is invalid")
    if result["result"] == "pass" and (exit_code != 0 or any(value != "pass" for value in check_results)):
        raise ProjectWorkspaceError("passing verifier result is inconsistent with its evidence")
    if result["result"] == "fail" and (
        exit_code is None
        or any(value == "blocked" for value in check_results)
        or (exit_code == 0 and all(value != "fail" for value in check_results))
    ):
        raise ProjectWorkspaceError("failing verifier result is inconsistent with its evidence")
    if result["result"] == "blocked" and (exit_code is not None or "blocked" not in check_results):
        raise ProjectWorkspaceError("blocked verifier result is inconsistent with its evidence")
    typed_pass = (
        metrics.get("errorCount", 0) == 0
        and metrics.get("failed", 0) == 0
        and (verifier["kind"] != "test" or metrics["passed"] > 0)
        and (
            verifier["kind"] != "runtime-smoke"
            or all(metrics[key] is True for key in ("started", "observed", "responsive"))
        )
    )
    if result["result"] == "pass" and not typed_pass:
        raise ProjectWorkspaceError("passing verifier result is inconsistent with its typed metrics")
    payload_bytes = canonical_json(payload)
    if (
        evidence["contentType"] != VERIFIER_EVIDENCE_CONTENT_TYPE
        or evidence["byteLength"] != len(payload_bytes)
        or evidence["digest"] != digest_bytes(payload_bytes)
    ):
        raise ProjectWorkspaceError("verifier evidence digest or byte length is invalid")

    pair = verifier_result_pair(result)
    latest = latest_result_by_pair.get(pair)
    expected_supersedes = latest["id"] if latest else None
    expected_attempt = latest["attempt"] + 1 if latest else 1
    if (
        not isinstance(result["attempt"], int)
        or isinstance(result["attempt"], bool)
        or result["attempt"] != expected_attempt
        or result["supersedesResultId"] != expected_supersedes
    ):
        raise ProjectWorkspaceError("verifier result supersedes chain is invalid")
    if result["observationStatus"] != "observed" or result["acceptanceStatus"] != "pending":
        raise ProjectWorkspaceError("verifier result must remain observed and pending acceptance")
    if result["authority"] != VERIFIER_RESULT_AUTHORITY:
        raise ProjectWorkspaceError("verifier result authority must remain import-only and non-approving")
    return result


def verifier_result_artifacts(
    project_workspace: Path,
    state: dict[str, Any],
    *,
    proposals: list[dict[str, Any]],
    snapshot_logical_source_root: str,
    snapshot_source_digest: str,
) -> list[dict[str, Any]]:
    records = state.get("verifierResults", [])
    if not isinstance(records, list):
        raise ProjectWorkspaceError("project state verifierResults must be a list")
    result_ids = validate_record_ids(records, "verifier result")
    proposal_by_id = {proposal["id"]: proposal for proposal in proposals}
    results: list[dict[str, Any]] = []
    latest_result_by_pair: dict[tuple[str, str, str], dict[str, Any]] = {}
    for record in records:
        expected = {
            "id",
            "artifact",
            "artifactDigest",
            "proposalId",
            "verificationRequirementId",
            "evidenceRequirementId",
            "attempt",
            "status",
            "result",
            "observationStatus",
            "acceptanceStatus",
            "supersedesResultId",
        }
        if set(record) != expected:
            raise ProjectWorkspaceError("verifier result index record fields are invalid")
        for key, label in (
            ("id", "verifier result index id"),
            ("proposalId", "verifier result index proposal id"),
            ("verificationRequirementId", "verifier result index verification requirement id"),
            ("evidenceRequirementId", "verifier result index evidence requirement id"),
        ):
            required_safe_id(record[key], label)
        if (
            record["id"] not in result_ids
            or record["proposalId"] not in proposal_by_id
            or record["status"] != VERIFIER_RESULT_STATUS
            or not isinstance(record["result"], str)
            or record["result"] not in VERIFIER_RESULT_RESULTS
            or not sha256_value(record["artifactDigest"])
        ):
            raise ProjectWorkspaceError("verifier result index record is invalid")
        artifact = contained_project_path(project_workspace, str(record["artifact"]), required_directory="verifier-results")
        if not artifact.is_file():
            raise ProjectWorkspaceError("verifier result artifact is missing")
        document = read_json(artifact)
        result = validate_verifier_result_document(
            document,
            proposal_by_id=proposal_by_id,
            snapshot_logical_source_root=snapshot_logical_source_root,
            snapshot_source_digest=snapshot_source_digest,
            latest_result_by_pair=latest_result_by_pair,
        )
        if (
            record["artifactDigest"] != digest_json(result)
            or any(
                result[key] != record[key]
                for key in (
                    "id",
                    "proposalId",
                    "verificationRequirementId",
                    "evidenceRequirementId",
                    "attempt",
                    "result",
                    "observationStatus",
                    "acceptanceStatus",
                    "supersedesResultId",
                )
            )
        ):
            raise ProjectWorkspaceError("verifier result index record does not match its artifact")
        latest_result_by_pair[verifier_result_pair(result)] = result
        results.append(result)
    return results


def evidence_decision_id_prefix(verifier_result_id: str) -> str:
    fingerprint = digest_json({"verifierResultId": verifier_result_id}).removeprefix("sha256:")[:16]
    prefix = f"decision.{verifier_result_id[:48]}.{fingerprint}"
    safe_id(prefix, "evidence decision id prefix")
    return prefix


def validate_evidence_decision_document(
    decision: dict[str, Any],
    *,
    result_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    assert_no_unsafe_state(decision)
    expected = {
        "artifactRole",
        "schemaVersion",
        "scope",
        "id",
        "verifierResultId",
        "proposalId",
        "verificationRequirementId",
        "evidenceRequirementId",
        "decision",
        "reviewer",
        "subject",
        "summary",
        "status",
        "authority",
    }
    if set(decision) != expected:
        raise ProjectWorkspaceError("evidence decision fields are invalid")
    if (
        decision["artifactRole"] != EVIDENCE_DECISION_ROLE
        or decision["schemaVersion"] != PROJECT_SCHEMA_VERSION
        or decision["scope"] != EVIDENCE_DECISION_SCOPE
        or decision["status"] != EVIDENCE_DECISION_STATUS
    ):
        raise ProjectWorkspaceError("evidence decision role, schema version, scope, or status is invalid")
    required_safe_id(decision["id"], "evidence decision id")
    result_id = required_safe_id(decision["verifierResultId"], "evidence decision verifier result id")
    result = result_by_id.get(result_id)
    if result is None:
        raise ProjectWorkspaceError("evidence decision must reference a known verifier result")
    for key, label in (
        ("proposalId", "evidence decision proposal id"),
        ("verificationRequirementId", "evidence decision verification requirement id"),
        ("evidenceRequirementId", "evidence decision evidence requirement id"),
    ):
        required_safe_id(decision[key], label)
        if decision[key] != result[key]:
            raise ProjectWorkspaceError("evidence decision requirement binding does not match its verifier result")
    if not isinstance(decision["decision"], str) or decision["decision"] not in EVIDENCE_DECISIONS:
        raise ProjectWorkspaceError("evidence decision result is invalid")
    if decision["decision"] == "accepted" and result["result"] != "pass":
        raise ProjectWorkspaceError("only a current passing verifier result may be accepted as evidence")
    reviewer = decision["reviewer"]
    if not isinstance(reviewer, dict) or set(reviewer) != {
        "id", "actorType", "role", "permission", "authorityScope", "authenticationStatus",
    }:
        raise ProjectWorkspaceError("evidence decision reviewer fields are invalid")
    required_safe_id(reviewer["id"], "evidence decision reviewer id")
    if (
        reviewer["actorType"] != "human"
        or not isinstance(reviewer["role"], str)
        or reviewer["role"] not in EVIDENCE_REVIEWER_ROLES
        or reviewer["permission"] != EVIDENCE_DECISION_PERMISSIONS[decision["decision"]]
        or reviewer["authorityScope"] != "local-project-workspace"
        or reviewer["authenticationStatus"] != "local-session-not-cryptographically-verified"
    ):
        raise ProjectWorkspaceError("evidence decision reviewer authority is invalid")
    subject = decision["subject"]
    if not isinstance(subject, dict) or set(subject) != {
        "verifierResultDigest", "evidenceDigest", "proposalDigest", "snapshotSourceDigest",
    }:
        raise ProjectWorkspaceError("evidence decision subject fields are invalid")
    expected_subject = {
        "verifierResultDigest": digest_json(result),
        "evidenceDigest": result["evidence"]["digest"],
        "proposalDigest": result["subject"]["proposalDigest"],
        "snapshotSourceDigest": result["subject"]["snapshotSourceDigest"],
    }
    if subject != expected_subject:
        raise ProjectWorkspaceError("evidence decision subject does not match its verifier result")
    if not isinstance(decision["summary"], str) or not decision["summary"].strip():
        raise ProjectWorkspaceError("evidence decision summary is required")
    if len(decision["summary"].encode("utf-8")) > 12000:
        raise ProjectWorkspaceError("evidence decision summary exceeds the local workspace size limit")
    if decision["authority"] != EVIDENCE_DECISION_AUTHORITY:
        raise ProjectWorkspaceError("evidence decision authority exceeds the local human-decision boundary")
    return decision


def evidence_decision_artifacts(
    project_workspace: Path,
    state: dict[str, Any],
    *,
    verifier_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    records = state.get("evidenceDecisions", [])
    if not isinstance(records, list):
        raise ProjectWorkspaceError("project state evidenceDecisions must be a list")
    decision_ids = validate_record_ids(records, "evidence decision")
    result_by_id = {result["id"]: result for result in verifier_results}
    decisions: list[dict[str, Any]] = []
    seen_result_ids: set[str] = set()
    expected_index_fields = {
        "id", "artifact", "artifactDigest", "verifierResultId", "proposalId",
        "verificationRequirementId", "evidenceRequirementId", "decision", "status",
        "reviewerId", "reviewerRole",
    }
    for record in records:
        if set(record) != expected_index_fields:
            raise ProjectWorkspaceError("evidence decision index record fields are invalid")
        for key, label in (
            ("id", "evidence decision index id"),
            ("verifierResultId", "evidence decision index verifier result id"),
            ("proposalId", "evidence decision index proposal id"),
            ("verificationRequirementId", "evidence decision index verification requirement id"),
            ("evidenceRequirementId", "evidence decision index evidence requirement id"),
            ("reviewerId", "evidence decision index reviewer id"),
        ):
            required_safe_id(record[key], label)
        if (
            record["id"] not in decision_ids
            or record["verifierResultId"] not in result_by_id
            or record["decision"] not in EVIDENCE_DECISIONS
            or record["status"] != EVIDENCE_DECISION_STATUS
            or record["reviewerRole"] not in EVIDENCE_REVIEWER_ROLES
            or not sha256_value(record["artifactDigest"])
        ):
            raise ProjectWorkspaceError("evidence decision index record is invalid")
        if record["verifierResultId"] in seen_result_ids:
            raise ProjectWorkspaceError("evidence decision already exists for the verifier result")
        artifact = contained_project_path(
            project_workspace,
            str(record["artifact"]),
            required_directory="evidence-decisions",
        )
        if not artifact.is_file():
            raise ProjectWorkspaceError("evidence decision artifact is missing")
        decision = validate_evidence_decision_document(read_json(artifact), result_by_id=result_by_id)
        if (
            record["artifactDigest"] != digest_json(decision)
            or any(
                decision[key] != record[key]
                for key in (
                    "id", "verifierResultId", "proposalId", "verificationRequirementId",
                    "evidenceRequirementId", "decision", "status",
                )
            )
            or decision["reviewer"]["id"] != record["reviewerId"]
            or decision["reviewer"]["role"] != record["reviewerRole"]
        ):
            raise ProjectWorkspaceError("evidence decision index record does not match its artifact")
        seen_result_ids.add(decision["verifierResultId"])
        decisions.append(decision)
    return decisions


def proposal_verifier_status(
    proposal: dict[str, Any],
    verifier_results: list[dict[str, Any]],
    evidence_decisions: list[dict[str, Any]] | None = None,
) -> tuple[str | None, str]:
    expected_pairs = proposal_verifier_pairs(proposal)
    latest: dict[tuple[str, str, str], dict[str, Any]] = {}
    for result in verifier_results:
        if result["proposalId"] == proposal["id"]:
            latest[verifier_result_pair(result)] = result
    if not latest:
        return None, "proposal-ready"
    decision_by_result = {
        decision["verifierResultId"]: decision
        for decision in (evidence_decisions or [])
    }
    current_decisions = [decision_by_result.get(result["id"]) for result in latest.values()]
    decided = [decision for decision in current_decisions if decision is not None]
    if any(decision["decision"] == "rejected" for decision in decided):
        return "evidence-rejected", "blocked"
    if set(latest) == expected_pairs and len(decided) == len(expected_pairs):
        statuses = {result["result"] for result in latest.values()}
        if statuses == {"pass"}:
            return "evidence-accepted-pass", "verified"
    if decided:
        return "evidence-decision-partial", "verification-observed"
    statuses = {result["result"] for result in latest.values()}
    if "fail" in statuses:
        return "verifier-result-fail", "verification-observed"
    if "blocked" in statuses:
        return "verifier-result-blocked", "verification-observed"
    if set(latest) == expected_pairs and statuses == {"pass"}:
        # The Workbench verifies structure and binding, not producer identity or
        # human acceptance. A complete imported pass is therefore observed, not
        # an approval or completed-work claim.
        return "verifier-result-pass", "verification-observed"
    return "verifier-result-partial", "verification-observed"


def verifier_result_coverage_for(
    proposals: list[dict[str, Any]],
    verifier_results: list[dict[str, Any]],
    evidence_decisions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Derive proposal coverage only from proposal bindings and current results."""

    latest_by_pair: dict[tuple[str, str, str], dict[str, Any]] = {}
    for result in verifier_results:
        latest_by_pair[verifier_result_pair(result)] = result
    decision_by_result = {
        decision["verifierResultId"]: decision for decision in evidence_decisions
    }
    coverage: list[dict[str, Any]] = []
    for proposal in proposals:
        pairs = sorted(proposal_verifier_pairs(proposal))
        latest = [latest_by_pair[pair] for pair in pairs if pair in latest_by_pair]
        results = [item["result"] for item in latest]
        decisions = [decision_by_result.get(item["id"]) for item in latest]
        accepted = sum(1 for item in decisions if item and item["decision"] == "accepted")
        rejected = sum(1 for item in decisions if item and item["decision"] == "rejected")
        pending = len(pairs) - accepted - rejected
        acceptance_status = (
            "accepted"
            if accepted == len(pairs) and len(latest) == len(pairs)
            else "rejected"
            if rejected
            else "partial"
            if accepted
            else "pending"
        )
        coverage.append(
            {
                "proposalId": proposal["id"],
                "workItemId": proposal["workItemId"],
                "requiredPairCount": len(pairs),
                "observedPairCount": len(latest),
                "missingPairCount": len(pairs) - len(latest),
                "passPairCount": results.count("pass"),
                "failPairCount": results.count("fail"),
                "blockedPairCount": results.count("blocked"),
                "allPairsObservedPassing": len(latest) == len(pairs) and set(results) == {"pass"},
                "acceptedPairCount": accepted,
                "rejectedPairCount": rejected,
                "pendingPairCount": pending,
                "allPairsAcceptedPassing": (
                    accepted == len(pairs)
                    and len(latest) == len(pairs)
                    and set(results) == {"pass"}
                ),
                "acceptanceStatus": acceptance_status,
            }
        )
    return sorted(coverage, key=lambda item: item["proposalId"])


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
    if "verifierResults" not in state:
        state["verifierResults"] = []
    if "evidenceDecisions" not in state:
        state["evidenceDecisions"] = []
    if "semanticRelationOverlay" not in state:
        state["semanticRelationOverlay"] = empty_semantic_relation_overlay()
    if "workStageRevisions" not in state:
        state["workStageRevisions"] = []
    for key in ("workItems", "mappings", "changeProposals", "reviewReceipts", "verifierResults", "evidenceDecisions", "workStageRevisions", "verification", "evidence", "history"):
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
        if item["changeStatus"] not in {"not-proposed", "proposal-review-required"} or item["verificationStatus"] not in {
            "not-required",
            "snapshot-only",
            "requirements-recorded",
            "review-receipt-recorded",
            "verifier-result-partial",
            "verifier-result-pass",
            "verifier-result-fail",
            "verifier-result-blocked",
            "evidence-decision-partial",
            "evidence-rejected",
            "evidence-accepted-pass",
        }:
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
    verifier_results = verifier_result_artifacts(
        project_workspace,
        state,
        proposals=proposals,
        snapshot_logical_source_root=project["logicalSourceRoot"],
        snapshot_source_digest=project["sourceDigest"],
    )
    evidence_decisions = evidence_decision_artifacts(
        project_workspace,
        state,
        verifier_results=verifier_results,
    )
    record_by_domain: dict[str, dict[str, dict[str, Any]]] = {}
    for domain in ("verification", "evidence", "history"):
        validate_record_ids(state[domain], domain)
        record_by_domain[domain] = {record["id"]: record for record in state[domain]}
    expected_decision_record_ids = {domain: set() for domain in record_by_domain}
    for decision in evidence_decisions:
        for domain, expected_record in evidence_decision_state_records(decision).items():
            expected_decision_record_ids[domain].add(expected_record["id"])
            if record_by_domain[domain].get(expected_record["id"]) != expected_record:
                raise ProjectWorkspaceError(
                    f"evidence decision {domain} record does not match its decision artifact"
                )
    decision_record_prefixes = {
        "verification": "verification.evidence-decision.",
        "evidence": "evidence.evidence-decision.",
        "history": "history.evidence-decision.",
    }
    for domain, prefix in decision_record_prefixes.items():
        actual_ids = {
            identifier for identifier in record_by_domain[domain] if identifier.startswith(prefix)
        }
        if actual_ids != expected_decision_record_ids[domain]:
            raise ProjectWorkspaceError(f"evidence decision {domain} records are incomplete")
    work_stage_revisions = validate_work_stage_revisions(state, work_ids=work_ids, proposals=proposals)
    reviewed_proposal_ids = {receipt["proposalId"] for receipt in review_receipts}
    proposed_work_ids = {proposal["workItemId"] for proposal in proposals}
    for item in state["workItems"]:
        if item["id"] in proposed_work_ids:
            proposal = next(proposal for proposal in proposals if proposal["workItemId"] == item["id"])
            verifier_status, expected_work_status = proposal_verifier_status(
                proposal,
                verifier_results,
                evidence_decisions,
            )
            expected_verification_status = verifier_status or (
                "review-receipt-recorded" if proposal["id"] in reviewed_proposal_ids else "requirements-recorded"
            )
            if (
                item["changeStatus"] != "proposal-review-required"
                or item["verificationStatus"] != expected_verification_status
                or item["status"] != expected_work_status
            ):
                raise ProjectWorkspaceError("work item proposal status must agree with its change proposal")
        elif item["changeStatus"] != "not-proposed":
            raise ProjectWorkspaceError("work item without a proposal must remain not-proposed")
    if not state["verification"] or not state["evidence"] or not state["history"]:
        raise ProjectWorkspaceError("project state must retain snapshot verification, evidence, and history")
    return state, snapshot_manifest, snapshot_artifacts, {
        "summary": summary,
        "facts": facts,
        "mappingIds": mapping_ids,
        "proposals": proposals,
        "reviewReceipts": review_receipts,
        "verifierResults": verifier_results,
        "evidenceDecisions": evidence_decisions,
        "workStageRevisions": work_stage_revisions,
        "semanticFoundation": foundation,
        "semanticRelationOverlay": semantic_relation_overlay,
    }


def add_work_request(project_workspace: Path, work_id: str, title: str, request: str) -> dict[str, Any]:
    project_workspace = project_workspace.resolve()
    with project_workspace_write_lock(project_workspace):
        return _add_work_request_locked(project_workspace, work_id, title, request)


def _add_work_request_locked(project_workspace: Path, work_id: str, title: str, request: str) -> dict[str, Any]:
    project_workspace = project_workspace.resolve()
    project_file_before = (project_workspace / PROJECT_FILE).read_bytes()
    state, _, _, _ = validate_project_workspace(project_workspace)
    before_digest = project_core_digest(state)
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
    revision = append_work_stage_revision(
        state,
        work_item_id=work_id,
        stage_kind="request-recorded",
        before_digest=before_digest,
        record_ids=[f"history.request.{work_id}"],
        added_node_ids=[f"work.{work_id}", intent_id],
        changed_node_ids=[],
        added_edge_ids=[f"edge.project.{state['project']['id']}.tracks.{work_id}", f"edge.{work_id}.expresses.{intent_id}"],
    )
    commit_project_state_atomic(
        project_workspace,
        state,
        project_file_before,
        operation="work request recording",
    )
    return {"result": "pass", "command": "add-experimental-csharp-work-request", "workItemId": work_id, "revisionId": revision["id"], "authority": PROJECT_AUTHORITY}


def add_mapping_candidate(project_workspace: Path, work_id: str, fact_ids: list[str], rationale: str) -> dict[str, Any]:
    project_workspace = project_workspace.resolve()
    with project_workspace_write_lock(project_workspace):
        return _add_mapping_candidate_locked(project_workspace, work_id, fact_ids, rationale)


def _add_mapping_candidate_locked(project_workspace: Path, work_id: str, fact_ids: list[str], rationale: str) -> dict[str, Any]:
    project_workspace = project_workspace.resolve()
    project_file_before = (project_workspace / PROJECT_FILE).read_bytes()
    state, _, _, data = validate_project_workspace(project_workspace)
    before_digest = project_core_digest(state)
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
        added_fact_ids = sorted(fact_ids)
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
        added_fact_ids = added
        existing["rationale"] = existing["rationale"] + "\n" + rationale.strip()
        history_kind = "mapping-candidate-expanded"
        history_summary = f"Expanded declared mapping candidate {mapping_id} by {len(added)} code fact(s); acceptance is not automatic."
    work["mappingStatus"] = "candidate"
    work["status"] = "mapping-candidate"
    history_id = f"history.mapping.{work_id}.{len(state['history'])}"
    state["history"].append(
        {
            "id": history_id,
            "kind": history_kind,
            "summary": history_summary,
        }
    )
    revision = append_work_stage_revision(
        state,
        work_item_id=work_id,
        stage_kind=history_kind,
        before_digest=before_digest,
        record_ids=[history_id],
        added_node_ids=[f"mapping.{mapping_id}"] if existing is None else [],
        changed_node_ids=[] if existing is None else [f"mapping.{mapping_id}"],
        added_edge_ids=(
            [f"edge.mapping.{mapping_id}.for.{work['intentUnitId']}"]
            if existing is None
            else []
        ) + [f"edge.mapping.{mapping_id}.to.{fact_id}" for fact_id in added_fact_ids],
    )
    commit_project_state_atomic(
        project_workspace,
        state,
        project_file_before,
        operation="mapping candidate recording",
    )
    active_mapping = next(item for item in state["mappings"] if item["id"] == mapping_id)
    return {"result": "pass", "command": "add-experimental-csharp-mapping-candidate", "mappingId": mapping_id, "codeFactCount": len(active_mapping["codeFactIds"]), "revisionId": revision["id"], "authority": PROJECT_AUTHORITY}


def record_semantic_foundation(project_workspace: Path, foundation_path: Path) -> dict[str, Any]:
    project_workspace = project_workspace.resolve()
    foundation_path = foundation_path.resolve()
    if not foundation_path.is_file() or foundation_path.is_symlink():
        raise ProjectWorkspaceError("semantic foundation artifact must be a regular JSON file")
    with project_workspace_write_lock(project_workspace):
        return _record_semantic_foundation_locked(project_workspace, foundation_path)


def _record_semantic_foundation_locked(project_workspace: Path, foundation_path: Path) -> dict[str, Any]:
    project_file_before = (project_workspace / PROJECT_FILE).read_bytes()
    state, _, _, data = validate_project_workspace(project_workspace)
    if data["semanticFoundation"]["status"] != "not-recorded":
        raise ProjectWorkspaceError("semantic foundation is already recorded; a future reviewed replacement boundary is required")
    module_labels = {
        str(fact["sourceFile"]).split("/", 1)[0]
        for fact in data["facts"].get("facts", [])
        if isinstance(fact, dict) and isinstance(fact.get("sourceFile"), str) and safe_relative_source(fact["sourceFile"])
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
    commit_project_state_atomic(
        project_workspace,
        state,
        project_file_before,
        operation="semantic foundation recording",
    )
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


def record_semantic_relation_overlay(project_workspace: Path, overlay_path: Path) -> dict[str, Any]:
    """Record already-extracted local symbol relations without reading or altering the target repository."""
    project_workspace = project_workspace.resolve()
    overlay_path = overlay_path.resolve()
    if not overlay_path.is_file() or overlay_path.is_symlink():
        raise ProjectWorkspaceError("semantic relation overlay artifact must be a regular JSON file")
    if is_within(overlay_path, project_workspace):
        raise ProjectWorkspaceError("semantic relation overlay artifact must remain outside the project workspace")
    with project_workspace_write_lock(project_workspace):
        return _record_semantic_relation_overlay_locked(project_workspace, overlay_path)


def _record_semantic_relation_overlay_locked(project_workspace: Path, overlay_path: Path) -> dict[str, Any]:
    project_file_before = (project_workspace / PROJECT_FILE).read_bytes()
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
    commit_project_state_atomic(
        project_workspace,
        state,
        project_file_before,
        operation="semantic relation overlay recording",
    )
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


def add_change_proposal_document(project_workspace: Path, proposal: dict[str, Any]) -> dict[str, Any]:
    project_workspace = project_workspace.resolve()
    with project_workspace_write_lock(project_workspace):
        return _add_change_proposal_document_locked(project_workspace, proposal)


def _add_change_proposal_document_locked(project_workspace: Path, proposal: dict[str, Any]) -> dict[str, Any]:
    project_workspace = project_workspace.resolve()
    if not isinstance(proposal, dict):
        raise ProjectWorkspaceError("change proposal document must be a JSON object")
    project_file = project_workspace / PROJECT_FILE
    project_file_before = project_file.read_bytes()
    state, _, _, data = validate_project_workspace(project_workspace)
    before_digest = project_core_digest(state)
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
    destination_preexisting = destination.exists()
    if destination_preexisting and digest_json(read_json(destination)) != digest_json(proposal):
        raise ProjectWorkspaceError("change proposal artifact path already exists with different content")
    destination_created = False
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
    proposal_node = f"proposal.{proposal['id']}"
    added_node_ids = [item["id"] for item in proposal["graphDelta"]["addedNodes"]]
    verification_record_id = f"verification.requirements.{proposal['id']}"
    evidence_record_id = f"evidence.requirements.{proposal['id']}"
    history_record_id = f"history.proposal.{proposal['id']}"
    revision = append_work_stage_revision(
        state,
        work_item_id=proposal["workItemId"],
        stage_kind="proposal-and-requirements-recorded",
        before_digest=before_digest,
        record_ids=[verification_record_id, evidence_record_id, history_record_id],
        added_node_ids=[
            proposal_node,
            *added_node_ids,
            f"verification.{verification_record_id}",
            f"evidence.{evidence_record_id}",
        ],
        changed_node_ids=list(proposal["graphDelta"]["changedNodeIds"]),
        added_edge_ids=[
            f"edge.work.{proposal['workItemId']}.proposes.{proposal['id']}",
            *[f"edge.{proposal_node}.changes.{item}" for item in proposal["graphDelta"]["changedNodeIds"]],
            *[f"edge.{proposal_node}.adds.{item}" for item in added_node_ids],
            *[item["id"] for item in proposal["graphDelta"]["addedEdges"]],
            f"edge.project.{state['project']['id']}.verified-by.{verification_record_id}",
            f"edge.project.{state['project']['id']}.evidenced-by.{evidence_record_id}",
        ],
        code_diff_ids=[item["id"] for item in proposal["codeDiffs"]],
    )
    if project_file.read_bytes() != project_file_before:
        raise ProjectWorkspaceError("project workspace changed during change proposal recording")
    try:
        if not destination_preexisting:
            write_json_atomic(destination, proposal)
            destination_created = True
        write_json_atomic(project_file, state)
        validate_project_workspace(project_workspace)
    except Exception:
        write_bytes_atomic(project_file, project_file_before)
        if destination_created:
            destination.unlink(missing_ok=True)
        raise
    return {
        "result": "pass",
        "command": "add-experimental-csharp-change-proposal",
        "proposalId": proposal["id"],
        "revisionId": revision["id"],
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
    code_diffs: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Build one bounded, non-applied review proposal from a declared mapping.

    The caller supplies the review intent and requirements.  The workspace derives only
    stable references already recorded in the local project state.  Optional diff hunks
    are supplied by the caller and checked against the immutable source snapshot; this
    function never synthesizes or applies a patch or changes the inspected source project.
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
    if verification_kind not in PROPOSAL_VERIFICATION_KINDS or evidence_kind not in PROPOSAL_EVIDENCE_KINDS:
        raise ProjectWorkspaceError("guided review proposal requirement kind is unsupported")
    allowed_verifier_kinds = VERIFICATION_KIND_TO_VERIFIER_KINDS.get(verification_kind, [])
    required_artifact_kinds = EVIDENCE_KIND_TO_REQUIRED_ARTIFACT_KINDS.get(evidence_kind, [])
    if bool(allowed_verifier_kinds) != bool(required_artifact_kinds):
        raise ProjectWorkspaceError("guided review proposal verification and evidence kinds are incompatible")

    project_workspace = project_workspace.resolve()
    state, _, snapshot_artifacts, data = validate_project_workspace(project_workspace)
    work = next((item for item in state["workItems"] if item["id"] == work_id), None)
    if work is None:
        raise ProjectWorkspaceError("guided review proposal work item does not exist")
    mapping = next((item for item in state["mappings"] if item["workItemId"] == work_id), None)
    if mapping is None or mapping["status"] != "candidate" or mapping["confidence"] != "declared":
        raise ProjectWorkspaceError("guided review proposal requires a declared mapping candidate")
    if work["changeStatus"] != "not-proposed":
        raise ProjectWorkspaceError("guided review proposal work item already has an active change proposal")

    normalized_code_diffs: list[dict[str, str]] = []
    if code_diffs is not None:
        if not isinstance(code_diffs, list) or not code_diffs or len(code_diffs) > 32:
            raise ProjectWorkspaceError("guided proposal code diffs must contain between one and 32 mapped fact hunks")
        assert_no_unsafe_state(code_diffs, "codeDiffs")
        fact_by_id = {
            fact.get("id"): fact
            for fact in data["facts"].get("facts", [])
            if isinstance(fact, dict) and isinstance(fact.get("id"), str)
        }
        seen_fact_ids: set[str] = set()
        source_root = snapshot_artifacts["sourceRoot"].resolve()
        for item in code_diffs:
            if not isinstance(item, dict) or set(item) != {"codeFactId", "unifiedDiff"} or any(not isinstance(value, str) for value in item.values()):
                raise ProjectWorkspaceError("guided proposal code diff fields are invalid")
            fact_id = item["codeFactId"]
            if fact_id in seen_fact_ids:
                raise ProjectWorkspaceError("guided proposal code diffs must target unique mapped code facts")
            if fact_id not in mapping["codeFactIds"]:
                raise ProjectWorkspaceError("guided proposal code diff must target a mapped code fact")
            fact = fact_by_id.get(fact_id)
            if fact is None or not isinstance(fact.get("sourceLocation"), dict) or not safe_relative_source(str(fact.get("sourceFile", ""))):
                raise ProjectWorkspaceError("guided proposal code diff fact provenance is invalid")
            source_path = (source_root / Path(str(fact["sourceFile"]))).resolve()
            if not is_within(source_path, source_root):
                raise ProjectWorkspaceError("guided proposal code diff source escapes the immutable snapshot")
            if digest_bytes(source_path.read_bytes()) != fact.get("sourceDigest"):
                raise ProjectWorkspaceError("guided proposal source digest does not match its code fact")
            validate_guided_unified_diff(
                item["unifiedDiff"],
                source_path=source_path,
                source_location=fact["sourceLocation"],
            )
            diff_fingerprint = digest_bytes(
                canonical_json({"proposalId": proposal_id, "codeFactId": fact_id})
            ).split(":", 1)[1][:16]
            normalized_code_diffs.append(
                {
                    "id": f"diff.{proposal_id[:75]}.{diff_fingerprint}",
                    "codeFactId": fact_id,
                    "sourceFile": fact["sourceFile"],
                    "beforeSourceDigest": fact["sourceDigest"],
                    "unifiedDiff": item["unifiedDiff"],
                }
            )
            seen_fact_ids.add(fact_id)

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
            "changedNodeIds": sorted(
                item["codeFactId"] for item in normalized_code_diffs
            ) if normalized_code_diffs else sorted(mapping["codeFactIds"]),
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
        "codeDiffs": normalized_code_diffs,
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
        "verifierBindings": (
            [
                {
                    "verificationRequirementId": f"verification.requirement.{proposal_id}",
                    "evidenceRequirementId": f"evidence.requirement.{proposal_id}",
                    "allowedVerifierKinds": allowed_verifier_kinds,
                    "requiredArtifactKinds": required_artifact_kinds,
                }
            ]
            if allowed_verifier_kinds
            else []
        ),
        "authority": PROPOSAL_AUTHORITY,
    }
    result = add_change_proposal_document(project_workspace, proposal)
    return {
        **result,
        "command": "draft-experimental-csharp-change-proposal",
        "mappingId": mapping["id"],
        "codeDiffCount": len(normalized_code_diffs),
        "diffBackedGuidedProposal": bool(normalized_code_diffs),
        "guidedReviewProposal": True,
    }


def add_change_proposal(project_workspace: Path, proposal_path: Path) -> dict[str, Any]:
    proposal_path = proposal_path.resolve()
    return add_change_proposal_document(project_workspace, read_json(proposal_path))


def add_review_receipt_document(project_workspace: Path, receipt: dict[str, Any]) -> dict[str, Any]:
    project_workspace = project_workspace.resolve()
    with project_workspace_write_lock(project_workspace):
        return _add_review_receipt_document_locked(project_workspace, receipt)


def _add_review_receipt_document_locked(project_workspace: Path, receipt: dict[str, Any]) -> dict[str, Any]:
    project_workspace = project_workspace.resolve()
    if not isinstance(receipt, dict):
        raise ProjectWorkspaceError("review receipt document must be a JSON object")
    project_file = project_workspace / PROJECT_FILE
    project_file_before = project_file.read_bytes()
    state, _, _, data = validate_project_workspace(project_workspace)
    before_digest = project_core_digest(state)
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
    destination_preexisting = destination.exists()
    destination_created = False
    if destination_preexisting and digest_json(read_json(destination)) != digest_json(receipt):
        raise ProjectWorkspaceError("review receipt artifact path already exists with different content")
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
    verifier_status, work_status = proposal_verifier_status(
        proposal,
        data["verifierResults"],
        data["evidenceDecisions"],
    )
    work["verificationStatus"] = verifier_status or "review-receipt-recorded"
    work["status"] = work_status
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
    verification_record_id = f"verification.review-receipt.{receipt['id']}"
    evidence_record_id = f"evidence.review-receipt.{receipt['id']}"
    history_record_id = f"history.review-receipt.{receipt['id']}"
    receipt_node = f"review-receipt.{receipt['id']}"
    proposal_node = f"proposal.{receipt['proposalId']}"
    revision = append_work_stage_revision(
        state,
        work_item_id=proposal["workItemId"],
        stage_kind="review-receipt-recorded",
        before_digest=before_digest,
        record_ids=[verification_record_id, evidence_record_id, history_record_id],
        added_node_ids=[receipt_node, f"verification.{verification_record_id}", f"evidence.{evidence_record_id}"],
        changed_node_ids=[],
        added_edge_ids=[
            f"edge.{proposal_node}.reviewed-by.{receipt['id']}",
            f"edge.{receipt_node}.records-verification.{receipt['id']}",
            f"edge.{receipt_node}.records-evidence.{receipt['id']}",
            f"edge.project.{state['project']['id']}.verified-by.{verification_record_id}",
            f"edge.project.{state['project']['id']}.evidenced-by.{evidence_record_id}",
        ],
        code_diff_ids=[item["id"] for item in proposal["codeDiffs"]],
    )
    if project_file.read_bytes() != project_file_before:
        raise ProjectWorkspaceError("project workspace changed during review receipt recording")
    try:
        if not destination_preexisting:
            write_json_atomic(destination, receipt)
            destination_created = True
        write_json_atomic(project_file, state)
        validate_project_workspace(project_workspace)
    except Exception:
        write_bytes_atomic(project_file, project_file_before)
        if destination_created:
            destination.unlink(missing_ok=True)
        raise
    return {
        "result": "pass",
        "command": "add-experimental-csharp-review-receipt",
        "receiptId": receipt["id"],
        "revisionId": revision["id"],
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


def add_verifier_result_document(project_workspace: Path, result: dict[str, Any]) -> dict[str, Any]:
    project_workspace = project_workspace.resolve()
    with project_workspace_write_lock(project_workspace):
        return _add_verifier_result_document_locked(project_workspace, result)


def _add_verifier_result_document_locked(project_workspace: Path, result: dict[str, Any]) -> dict[str, Any]:
    project_workspace = project_workspace.resolve()
    if not isinstance(result, dict):
        raise ProjectWorkspaceError("verifier result document must be a JSON object")
    project_file = project_workspace / PROJECT_FILE
    project_file_before = project_file.read_bytes()
    state, _, _, data = validate_project_workspace(project_workspace)
    before_digest = project_core_digest(state)
    proposals = data["proposals"]
    proposal_by_id = {proposal["id"]: proposal for proposal in proposals}
    latest_by_pair: dict[tuple[str, str, str], dict[str, Any]] = {}
    for existing in data["verifierResults"]:
        latest_by_pair[verifier_result_pair(existing)] = existing
    result = validate_verifier_result_document(
        result,
        proposal_by_id=proposal_by_id,
        snapshot_logical_source_root=state["project"]["logicalSourceRoot"],
        snapshot_source_digest=state["project"]["sourceDigest"],
        latest_result_by_pair=latest_by_pair,
    )
    if any(record["id"] == result["id"] for record in state["verifierResults"]):
        raise ProjectWorkspaceError("verifier result identifier already exists")
    destination_relative = f"verifier-results/{result['id']}.json"
    destination = contained_project_path(project_workspace, destination_relative, required_directory="verifier-results")
    destination_preexisting = destination.exists()
    destination_created = False
    if destination_preexisting and digest_json(read_json(destination)) != digest_json(result):
        raise ProjectWorkspaceError("verifier result artifact path already exists with different content")
    state["verifierResults"].append(
        {
            "id": result["id"],
            "artifact": destination_relative,
            "artifactDigest": digest_json(result),
            "proposalId": result["proposalId"],
            "verificationRequirementId": result["verificationRequirementId"],
            "evidenceRequirementId": result["evidenceRequirementId"],
            "attempt": result["attempt"],
            "status": VERIFIER_RESULT_STATUS,
            "result": result["result"],
            "observationStatus": result["observationStatus"],
            "acceptanceStatus": result["acceptanceStatus"],
            "supersedesResultId": result["supersedesResultId"],
        }
    )
    proposal = proposal_by_id[result["proposalId"]]
    work = next(item for item in state["workItems"] if item["id"] == proposal["workItemId"])
    verification_status, work_status = proposal_verifier_status(
        proposal,
        [*data["verifierResults"], result],
        data["evidenceDecisions"],
    )
    if verification_status is None:
        raise ProjectWorkspaceError("verifier result did not produce a proposal verification state")
    work["verificationStatus"] = verification_status
    work["status"] = work_status
    verification_record_id = f"verification.verifier-result.{result['id']}"
    evidence_record_id = f"evidence.verifier-result.{result['id']}"
    history_record_id = f"history.verifier-result.{result['id']}"
    state["verification"].append(
        {
            "id": verification_record_id,
            "kind": "tool-verifier-result",
            "result": result["result"],
            "summary": f"Imported declared-deterministic {result['verifier']['kind']} result for {result['verificationRequirementId']}.",
        }
    )
    state["evidence"].append(
        {
            "id": evidence_record_id,
            "kind": "deterministic-verifier-evidence",
            "result": result["result"],
            "summary": f"Bound {result['evidence']['digest']} to {result['evidenceRequirementId']}.",
        }
    )
    state["history"].append(
        {
            "id": history_record_id,
            "kind": "verifier-result-imported",
            "summary": f"Imported verifier result {result['id']} without executing verification, applying the proposal, approving work, or changing source code.",
        }
    )
    result_node = f"verifier-result.{result['id']}"
    proposal_node = f"proposal.{result['proposalId']}"
    added_edge_ids = [
        f"edge.{proposal_node}.verified-by-result.{result['id']}",
        f"edge.{result_node}.records-verification.{result['id']}",
        f"edge.{result_node}.records-evidence.{result['id']}",
        f"edge.project.{state['project']['id']}.verified-by.{verification_record_id}",
        f"edge.project.{state['project']['id']}.evidenced-by.{evidence_record_id}",
    ]
    if result["supersedesResultId"] is not None:
        added_edge_ids.append(f"edge.{result_node}.supersedes.{result['supersedesResultId']}")
    revision = append_work_stage_revision(
        state,
        work_item_id=proposal["workItemId"],
        stage_kind="verifier-result-imported",
        before_digest=before_digest,
        record_ids=[verification_record_id, evidence_record_id, history_record_id],
        added_node_ids=[
            result_node,
            f"verification.{verification_record_id}",
            f"evidence.{evidence_record_id}",
        ],
        changed_node_ids=[f"work.{proposal['workItemId']}", proposal_node],
        added_edge_ids=added_edge_ids,
        code_diff_ids=[item["id"] for item in proposal["codeDiffs"]],
    )
    if project_file.read_bytes() != project_file_before:
        raise ProjectWorkspaceError("project workspace changed during verifier result recording")
    try:
        if not destination_preexisting:
            write_json_atomic(destination, result)
            destination_created = True
        write_json_atomic(project_file, state)
        validate_project_workspace(project_workspace)
    except Exception:
        write_bytes_atomic(project_file, project_file_before)
        if destination_created:
            destination.unlink(missing_ok=True)
        raise
    return {
        "result": "pass",
        "command": "add-experimental-csharp-verifier-result",
        "verifierResultId": result["id"],
        "revisionId": revision["id"],
        "proposalId": result["proposalId"],
        "resultStatus": result["result"],
        "verificationStatus": verification_status,
        "evidenceDigest": result["evidence"]["digest"],
        "targetRepositoryMutation": False,
        "automaticCodeApplication": False,
        "approvalRecorded": False,
        "authority": PROJECT_AUTHORITY,
    }


def add_verifier_result(project_workspace: Path, result_path: Path) -> dict[str, Any]:
    return add_verifier_result_document(project_workspace, read_json(result_path.resolve()))


def add_evidence_decision_document(project_workspace: Path, decision: dict[str, Any]) -> dict[str, Any]:
    project_workspace = project_workspace.resolve()
    with project_workspace_write_lock(project_workspace):
        return _add_evidence_decision_document_locked(project_workspace, decision)


def _add_evidence_decision_document_locked(project_workspace: Path, decision: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(decision, dict):
        raise ProjectWorkspaceError("evidence decision document must be a JSON object")
    project_file = project_workspace / PROJECT_FILE
    project_file_before = project_file.read_bytes()
    state, _, _, data = validate_project_workspace(project_workspace)
    before_digest = project_core_digest(state)
    result_by_id = {result["id"]: result for result in data["verifierResults"]}
    decision = validate_evidence_decision_document(decision, result_by_id=result_by_id)
    if any(record["id"] == decision["id"] for record in state["evidenceDecisions"]):
        raise ProjectWorkspaceError("evidence decision identifier already exists")
    if any(record["verifierResultId"] == decision["verifierResultId"] for record in state["evidenceDecisions"]):
        raise ProjectWorkspaceError("evidence decision already exists for the verifier result")
    result = result_by_id[decision["verifierResultId"]]
    pair = verifier_result_pair(result)
    latest_by_pair: dict[tuple[str, str, str], dict[str, Any]] = {}
    for existing in data["verifierResults"]:
        latest_by_pair[verifier_result_pair(existing)] = existing
    if latest_by_pair[pair]["id"] != result["id"]:
        raise ProjectWorkspaceError("evidence decision must reference the current verifier result for its requirement pair")

    destination_relative = f"evidence-decisions/{decision['id']}.json"
    destination = contained_project_path(
        project_workspace,
        destination_relative,
        required_directory="evidence-decisions",
    )
    destination_preexisting = destination.exists()
    destination_created = False
    if destination_preexisting and digest_json(read_json(destination)) != digest_json(decision):
        raise ProjectWorkspaceError("evidence decision artifact path already exists with different content")
    state["evidenceDecisions"].append(
        {
            "id": decision["id"],
            "artifact": destination_relative,
            "artifactDigest": digest_json(decision),
            "verifierResultId": decision["verifierResultId"],
            "proposalId": decision["proposalId"],
            "verificationRequirementId": decision["verificationRequirementId"],
            "evidenceRequirementId": decision["evidenceRequirementId"],
            "decision": decision["decision"],
            "status": decision["status"],
            "reviewerId": decision["reviewer"]["id"],
            "reviewerRole": decision["reviewer"]["role"],
        }
    )
    proposal = next(item for item in data["proposals"] if item["id"] == decision["proposalId"])
    work = next(item for item in state["workItems"] if item["id"] == proposal["workItemId"])
    verification_status, work_status = proposal_verifier_status(
        proposal,
        data["verifierResults"],
        [*data["evidenceDecisions"], decision],
    )
    if verification_status is None:
        raise ProjectWorkspaceError("evidence decision did not produce a proposal verification state")
    work["verificationStatus"] = verification_status
    work["status"] = work_status

    decision_records = evidence_decision_state_records(decision)
    verification_record_id = decision_records["verification"]["id"]
    evidence_record_id = decision_records["evidence"]["id"]
    history_record_id = decision_records["history"]["id"]
    for domain, record in decision_records.items():
        state[domain].append(record)
    decision_node = f"evidence-decision.{decision['id']}"
    decision_authority_node = f"authority.evidence-decision.{decision['id']}"
    result_node = f"verifier-result.{decision['verifierResultId']}"
    proposal_node = f"proposal.{decision['proposalId']}"
    revision = append_work_stage_revision(
        state,
        work_item_id=proposal["workItemId"],
        stage_kind="evidence-decision-recorded",
        before_digest=before_digest,
        record_ids=[verification_record_id, evidence_record_id, history_record_id],
        added_node_ids=[
            decision_node,
            decision_authority_node,
            f"verification.{verification_record_id}",
            f"evidence.{evidence_record_id}",
        ],
        changed_node_ids=[f"work.{proposal['workItemId']}", proposal_node, result_node],
        added_edge_ids=[
            f"edge.{result_node}.decided-by.{decision['id']}",
            f"edge.{decision_node}.records-verification.{decision['id']}",
            f"edge.{decision_node}.records-evidence.{decision['id']}",
            f"edge.{decision_node}.records-authority.{decision['id']}",
            f"edge.{decision_authority_node}.{'authorizes' if decision['decision'] == 'accepted' else 'rejects'}.{evidence_record_id}",
            f"edge.{decision_node}.governed-by.authority",
            f"edge.project.{state['project']['id']}.verified-by.{verification_record_id}",
            f"edge.project.{state['project']['id']}.evidenced-by.{evidence_record_id}",
        ],
        code_diff_ids=[item["id"] for item in proposal["codeDiffs"]],
    )
    if project_file.read_bytes() != project_file_before:
        raise ProjectWorkspaceError("project workspace changed during evidence decision recording")
    try:
        if not destination_preexisting:
            write_json_atomic(destination, decision)
            destination_created = True
        write_json_atomic(project_file, state)
        validate_project_workspace(project_workspace)
    except Exception:
        write_bytes_atomic(project_file, project_file_before)
        if destination_created:
            destination.unlink(missing_ok=True)
        raise
    return {
        "result": "pass",
        "command": "add-experimental-csharp-evidence-decision",
        "evidenceDecisionId": decision["id"],
        "revisionId": revision["id"],
        "verifierResultId": decision["verifierResultId"],
        "proposalId": decision["proposalId"],
        "decision": decision["decision"],
        "verificationStatus": verification_status,
        "workStatus": work_status,
        "proposalApprovalRecorded": False,
        "targetRepositoryMutation": False,
        "automaticCodeApplication": False,
        "authority": PROJECT_AUTHORITY,
    }


def draft_evidence_decision_from_result(
    project_workspace: Path,
    *,
    decision_id: str,
    verifier_result_id: str,
    decision: str,
    reviewer_id: str,
    reviewer_role: str,
    summary: str,
) -> dict[str, Any]:
    draft = {
        "decisionId": decision_id,
        "verifierResultId": verifier_result_id,
        "decision": decision,
        "reviewerId": reviewer_id,
        "reviewerRole": reviewer_role,
        "summary": summary,
    }
    assert_no_unsafe_state(draft)
    if any(not isinstance(value, str) or not value.strip() for value in draft.values()):
        raise ProjectWorkspaceError("guided evidence decision fields must be non-blank strings")
    safe_id(decision_id, "guided evidence decision id")
    safe_id(verifier_result_id, "guided evidence decision verifier result id")
    safe_id(reviewer_id, "guided evidence decision reviewer id")
    if decision not in EVIDENCE_DECISIONS:
        raise ProjectWorkspaceError("guided evidence decision result is invalid")
    if reviewer_role not in EVIDENCE_REVIEWER_ROLES:
        raise ProjectWorkspaceError("guided evidence decision reviewer role is invalid")
    _, _, _, data = validate_project_workspace(project_workspace.resolve())
    result_by_id = {item["id"]: item for item in data["verifierResults"]}
    result = result_by_id.get(verifier_result_id)
    if result is None:
        raise ProjectWorkspaceError("guided evidence decision must reference a known verifier result")
    document = {
        "artifactRole": EVIDENCE_DECISION_ROLE,
        "schemaVersion": PROJECT_SCHEMA_VERSION,
        "scope": EVIDENCE_DECISION_SCOPE,
        "id": decision_id.strip(),
        "verifierResultId": verifier_result_id.strip(),
        "proposalId": result["proposalId"],
        "verificationRequirementId": result["verificationRequirementId"],
        "evidenceRequirementId": result["evidenceRequirementId"],
        "decision": decision.strip(),
        "reviewer": {
            "id": reviewer_id.strip(),
            "actorType": "human",
            "role": reviewer_role.strip(),
            "permission": EVIDENCE_DECISION_PERMISSIONS[decision],
            "authorityScope": "local-project-workspace",
            "authenticationStatus": "local-session-not-cryptographically-verified",
        },
        "subject": {
            "verifierResultDigest": digest_json(result),
            "evidenceDigest": result["evidence"]["digest"],
            "proposalDigest": result["subject"]["proposalDigest"],
            "snapshotSourceDigest": result["subject"]["snapshotSourceDigest"],
        },
        "summary": summary.strip(),
        "status": EVIDENCE_DECISION_STATUS,
        "authority": EVIDENCE_DECISION_AUTHORITY,
    }
    recorded = add_evidence_decision_document(project_workspace, document)
    return {
        **recorded,
        "command": "draft-experimental-csharp-evidence-decision",
        "guidedEvidenceDecision": True,
        "reviewerAuthority": document["reviewer"],
    }


def add_evidence_decision(project_workspace: Path, decision_path: Path) -> dict[str, Any]:
    return add_evidence_decision_document(project_workspace, read_json(decision_path.resolve()))


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
    verifier_results: list[dict[str, Any]],
    evidence_decisions: list[dict[str, Any]],
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
    results_by_proposal: dict[str, list[dict[str, Any]]] = {}
    for result in verifier_results:
        results_by_proposal.setdefault(result["proposalId"], []).append(result)
    decisions_by_proposal: dict[str, list[dict[str, Any]]] = {}
    for decision in evidence_decisions:
        decisions_by_proposal.setdefault(decision["proposalId"], []).append(decision)
    revision_sequence_by_record = {
        record_id: revision["sequence"]
        for revision in state.get("workStageRevisions", [])
        for record_id in revision["recordIds"]
    }

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
        lifecycle_events = [
            (
                revision_sequence_by_record.get(f"history.review-receipt.{receipt['id']}", 1_000_000),
                "review-receipt",
                receipt,
            )
            for receipt in receipts_by_proposal.get(proposal["id"], [])
        ]
        lifecycle_events.extend(
            (
                revision_sequence_by_record.get(f"history.verifier-result.{result['id']}", 1_000_000),
                "verifier-result",
                result,
            )
            for result in results_by_proposal.get(proposal["id"], [])
        )
        lifecycle_events.extend(
            (
                revision_sequence_by_record.get(f"history.evidence-decision.{decision['id']}", 1_000_000),
                "evidence-decision",
                decision,
            )
            for decision in decisions_by_proposal.get(proposal["id"], [])
        )
        lifecycle_events.sort(key=lambda item: (item[0], item[1], item[2]["id"]))
        for event_index, (_, event_kind, event) in enumerate(lifecycle_events, start=5):
            if event_kind == "review-receipt":
                receipt = event
                receipt_node = f"review-receipt.{receipt['id']}"
                verification_node = f"verification.verification.review-receipt.{receipt['id']}"
                evidence_node = f"evidence.evidence.review-receipt.{receipt['id']}"
                edge_ids = [
                    f"edge.{proposal_node}.reviewed-by.{receipt['id']}",
                    f"edge.{receipt_node}.records-verification.{receipt['id']}",
                    f"edge.{receipt_node}.records-evidence.{receipt['id']}",
                ]
                stages.append(
                    {
                        "id": f"stage.{work_id}.review-receipt.{receipt['id']}",
                        "workItemId": work_id,
                        "sequence": event_index,
                        "kind": "review-receipt-recorded",
                        "title": "Review receipt recorded",
                        "summary": "A human review outcome was recorded. It is not runtime evidence, an approval, or application of the proposal.",
                        "status": receipt["result"],
                        "recordIds": [f"history.review-receipt.{receipt['id']}"],
                        "nodeIds": [proposal_node, receipt_node, verification_node, evidence_node],
                        "addedNodeIds": [receipt_node, verification_node, evidence_node],
                        "changedNodeIds": [],
                        "contextNodeIds": [work_node, *diff_node_ids],
                        "edgeIds": edge_ids,
                        "addedEdgeIds": edge_ids,
                        "changedEdgeIds": [],
                        "codeDiffs": list(proposal["codeDiffs"]),
                        "verificationRecordIds": [verification_node],
                        "evidenceRecordIds": [evidence_node],
                        "revisionKind": "human-review-record-not-approval",
                    }
                )
                continue
            if event_kind == "evidence-decision":
                decision = event
                decision_node = f"evidence-decision.{decision['id']}"
                result_node = f"verifier-result.{decision['verifierResultId']}"
                verification_node = f"verification.verification.evidence-decision.{decision['id']}"
                evidence_node = f"evidence.evidence.evidence-decision.{decision['id']}"
                authority_node = f"authority.evidence-decision.{decision['id']}"
                authority_relation = "authorizes" if decision["decision"] == "accepted" else "rejects"
                edge_ids = [
                    f"edge.{result_node}.decided-by.{decision['id']}",
                    f"edge.{decision_node}.records-verification.{decision['id']}",
                    f"edge.{decision_node}.records-evidence.{decision['id']}",
                    f"edge.{decision_node}.records-authority.{decision['id']}",
                    f"edge.{authority_node}.{authority_relation}.evidence.evidence-decision.{decision['id']}",
                    f"edge.{decision_node}.governed-by.authority",
                ]
                stages.append(
                    {
                        "id": f"stage.{work_id}.evidence-decision.{decision['id']}",
                        "workItemId": work_id,
                        "sequence": event_index,
                        "kind": "evidence-decision-recorded",
                        "title": "Evidence decision recorded",
                        "summary": "A local human reviewer accepted or rejected one current verifier result for workspace readiness only. The proposal remains unapproved and unapplied.",
                        "status": decision["decision"],
                        "recordIds": [f"history.evidence-decision.{decision['id']}"],
                        "nodeIds": [proposal_node, result_node, decision_node, verification_node, evidence_node, authority_node],
                        "addedNodeIds": [decision_node, verification_node, evidence_node, authority_node],
                        "changedNodeIds": [work_node, proposal_node, result_node],
                        "contextNodeIds": [work_node, *diff_node_ids],
                        "edgeIds": edge_ids,
                        "addedEdgeIds": edge_ids,
                        "changedEdgeIds": [],
                        "codeDiffs": list(proposal["codeDiffs"]),
                        "verificationRecordIds": [verification_node],
                        "evidenceRecordIds": [evidence_node],
                        "revisionKind": "local-human-evidence-decision-not-proposal-approval",
                    }
                )
                continue
            result = event
            result_node = f"verifier-result.{result['id']}"
            verification_node = f"verification.verification.verifier-result.{result['id']}"
            evidence_node = f"evidence.evidence.verifier-result.{result['id']}"
            edge_ids = [
                f"edge.{proposal_node}.verified-by-result.{result['id']}",
                f"edge.{result_node}.records-verification.{result['id']}",
                f"edge.{result_node}.records-evidence.{result['id']}",
            ]
            if result["supersedesResultId"] is not None:
                edge_ids.append(f"edge.{result_node}.supersedes.{result['supersedesResultId']}")
            stages.append(
                {
                    "id": f"stage.{work_id}.verifier-result.{result['id']}",
                    "workItemId": work_id,
                    "sequence": event_index,
                    "kind": "verifier-result-imported",
                    "title": "Verifier result imported",
                    "summary": "A declared-deterministic external verifier result and its evidence digest were bound to the proposal requirements. No source or graph delta was applied.",
                    "status": result["result"],
                    "recordIds": [f"history.verifier-result.{result['id']}"],
                    "nodeIds": [proposal_node, result_node, verification_node, evidence_node],
                    "addedNodeIds": [result_node, verification_node, evidence_node],
                    "changedNodeIds": [work_node, proposal_node],
                    "contextNodeIds": [work_node, *diff_node_ids],
                    "edgeIds": edge_ids,
                    "addedEdgeIds": edge_ids,
                    "changedEdgeIds": [],
                    "codeDiffs": list(proposal["codeDiffs"]),
                    "verificationRecordIds": [verification_node],
                    "evidenceRecordIds": [evidence_node],
                    "revisionKind": "tool-result-imported-not-approval",
                }
            )
    revision_kinds_by_stage = {
        "request-recorded": {"request-recorded"},
        "mapping-candidate-recorded": {"mapping-candidate-recorded", "mapping-candidate-expanded"},
        "change-proposal-recorded": {"proposal-and-requirements-recorded"},
        "verification-and-evidence-requirements-recorded": {"proposal-and-requirements-recorded"},
        "review-receipt-recorded": {"review-receipt-recorded"},
        "verifier-result-imported": {"verifier-result-imported"},
        "evidence-decision-recorded": {"evidence-decision-recorded"},
    }
    for stage in stages:
        candidates = [
            revision
            for revision in state.get("workStageRevisions", [])
            if revision["workItemId"] == stage["workItemId"]
            and revision["stageKind"] in revision_kinds_by_stage[stage["kind"]]
            and (
                stage["kind"] not in {"review-receipt-recorded", "verifier-result-imported", "evidence-decision-recorded"}
                or bool(set(stage["recordIds"]) & set(revision["recordIds"]))
            )
        ]
        candidates.sort(key=lambda item: item["sequence"])
        stage["revisionIds"] = [item["id"] for item in candidates]
        stage["durableRevision"] = bool(candidates)
        stage["beforeProjectStateDigest"] = candidates[0]["beforeProjectStateDigest"] if candidates else None
        stage["afterProjectStateDigest"] = candidates[-1]["afterProjectStateDigest"] if candidates else None
    return stages


def evidence_decision_projection_edges(decision: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the complete authority topology represented by one decision."""

    identifier = decision["id"]
    result_node = f"verifier-result.{decision['verifierResultId']}"
    decision_node = f"evidence-decision.{identifier}"
    verification_node = f"verification.verification.evidence-decision.{identifier}"
    evidence_node = f"evidence.evidence.evidence-decision.{identifier}"
    authority_node = f"authority.evidence-decision.{identifier}"
    authority_relation = "authorizes" if decision["decision"] == "accepted" else "rejects"
    return [
        {
            "id": f"edge.{result_node}.decided-by.{identifier}",
            "category": "authority-relation",
            "kind": "decided-by",
            "source": result_node,
            "target": decision_node,
            "details": {
                "decision": decision["decision"],
                "reviewerRole": decision["reviewer"]["role"],
            },
        },
        {
            "id": f"edge.{decision_node}.records-verification.{identifier}",
            "category": "semantic-relation",
            "kind": "records-verification",
            "source": decision_node,
            "target": verification_node,
            "details": {"verifierResultId": decision["verifierResultId"]},
        },
        {
            "id": f"edge.{decision_node}.records-evidence.{identifier}",
            "category": "semantic-relation",
            "kind": "records-evidence",
            "source": decision_node,
            "target": evidence_node,
            "details": {"evidenceDigest": decision["subject"]["evidenceDigest"]},
        },
        {
            "id": f"edge.{decision_node}.records-authority.{identifier}",
            "category": "authority-relation",
            "kind": "records-authority",
            "source": decision_node,
            "target": authority_node,
            "details": {
                "reviewerRole": decision["reviewer"]["role"],
                "authenticationStatus": decision["reviewer"]["authenticationStatus"],
            },
        },
        {
            "id": f"edge.{authority_node}.{authority_relation}.evidence.evidence-decision.{identifier}",
            "category": "authority-relation",
            "kind": authority_relation,
            "source": authority_node,
            "target": evidence_node,
            "details": {
                "verifierResultId": decision["verifierResultId"],
                "evidenceDigest": decision["subject"]["evidenceDigest"],
                "proposalApprovalRecorded": False,
            },
        },
        {
            "id": f"edge.{decision_node}.governed-by.authority",
            "category": "authority-relation",
            "kind": "governed-by",
            "source": decision_node,
            "target": "authority.project-boundary",
            "details": {
                "authorityScope": decision["reviewer"]["authorityScope"],
                "proposalApprovalRecorded": False,
            },
        },
    ]


def build_projection(project_workspace: Path) -> tuple[dict[str, Any], list[dict[str, str]]]:
    state, snapshot_manifest, snapshot_artifacts, data = validate_project_workspace(project_workspace)
    facts_document = data["facts"]
    proposals = data["proposals"]
    verifier_results = data["verifierResults"]
    evidence_decisions = data["evidenceDecisions"]
    decision_by_result_id = {
        decision["verifierResultId"]: decision
        for decision in evidence_decisions
    }
    latest_verifier_result_by_pair: dict[tuple[str, str, str], dict[str, Any]] = {}
    for verifier_result in verifier_results:
        latest_verifier_result_by_pair[verifier_result_pair(verifier_result)] = verifier_result
    current_verifier_result_ids = {result["id"] for result in latest_verifier_result_by_pair.values()}
    verifier_result_intake_pairs: list[dict[str, Any]] = []
    evidence_decision_intake_results: list[dict[str, Any]] = []
    verifier_result_coverage: list[dict[str, Any]] = []
    for proposal in proposals:
        proposal_pairs: list[tuple[str, str, str]] = []
        verification_by_id = {item["id"]: item for item in proposal["verificationRequirements"]}
        evidence_by_id = {item["id"]: item for item in proposal["evidenceRequirements"]}
        for binding in proposal_verifier_bindings(proposal):
            verification = verification_by_id[binding["verificationRequirementId"]]
            evidence_requirement = evidence_by_id[binding["evidenceRequirementId"]]
            pair = (proposal["id"], verification["id"], evidence_requirement["id"])
            proposal_pairs.append(pair)
            latest = latest_verifier_result_by_pair.get(pair)
            latest_decision = decision_by_result_id.get(latest["id"]) if latest else None
            verifier_result_intake_pairs.append(
                {
                    "key": "|".join(pair),
                    "resultIdPrefix": verifier_result_id_prefix(pair),
                    "proposalId": proposal["id"],
                    "proposalTitle": proposal["title"],
                    "workItemId": proposal["workItemId"],
                    "verificationRequirement": verification,
                    "evidenceRequirement": evidence_requirement,
                    "allowedVerifierKinds": binding["allowedVerifierKinds"],
                    "requiredArtifactKinds": binding["requiredArtifactKinds"],
                    "logicalSourceRoot": state["project"]["logicalSourceRoot"],
                    "snapshotSourceDigest": state["project"]["sourceDigest"],
                    "proposalDigest": digest_json(proposal),
                    "nextAttempt": latest["attempt"] + 1 if latest else 1,
                    "supersedesResultId": latest["id"] if latest else None,
                    "currentResult": (
                        {
                            "id": latest["id"],
                            "result": latest["result"],
                            "observationStatus": latest["observationStatus"],
                            "acceptanceStatus": latest_decision["decision"] if latest_decision else "pending",
                            "decisionId": latest_decision["id"] if latest_decision else None,
                        }
                        if latest
                        else None
                    ),
                }
            )
            if latest:
                evidence_decision_intake_results.append(
                    {
                        "key": latest["id"],
                        "decisionIdPrefix": evidence_decision_id_prefix(latest["id"]),
                        "proposalId": proposal["id"],
                        "proposalTitle": proposal["title"],
                        "workItemId": proposal["workItemId"],
                        "verifierResultId": latest["id"],
                        "verifierResult": latest["result"],
                        "verifierKind": latest["verifier"]["kind"],
                        "evidenceDigest": latest["evidence"]["digest"],
                        "verificationRequirementId": latest["verificationRequirementId"],
                        "evidenceRequirementId": latest["evidenceRequirementId"],
                        "decisionRecorded": latest_decision is not None,
                        "currentDecision": latest_decision,
                    }
                )
    verifier_result_coverage = verifier_result_coverage_for(
        proposals,
        verifier_results,
        evidence_decisions,
    )
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
    for result in verifier_results:
        effective_decision = decision_by_result_id.get(result["id"])
        nodes.append(
            semantic_node(
                f"verifier-result.{result['id']}",
                "verifier-result",
                f"{result['verifier']['kind']} {result['result']}",
                {
                    "id": result["id"],
                    "proposalId": result["proposalId"],
                    "verificationRequirementId": result["verificationRequirementId"],
                    "evidenceRequirementId": result["evidenceRequirementId"],
                    "attempt": result["attempt"],
                    "result": result["result"],
                    "verifier": result["verifier"],
                    "invocation": result["invocation"],
                    "metrics": result["evidence"]["payload"]["metrics"],
                    "artifactRefs": result["evidence"]["payload"]["artifactRefs"],
                    "summary": result["evidence"]["payload"]["summary"],
                    "exitCode": result["evidence"]["payload"]["exitCode"],
                    "checks": result["evidence"]["payload"]["checks"],
                    "evidenceDigest": result["evidence"]["digest"],
                    "evidenceByteLength": result["evidence"]["byteLength"],
                    "observationStatus": result["observationStatus"],
                    "observationAcceptanceStatus": result["acceptanceStatus"],
                    "acceptanceStatus": effective_decision["decision"] if effective_decision else "pending",
                    "evidenceDecisionId": effective_decision["id"] if effective_decision else None,
                    "current": result["id"] in current_verifier_result_ids,
                    "supersedesResultId": result["supersedesResultId"],
                    "authority": "import-only-non-approving",
                },
            )
        )
    for decision in evidence_decisions:
        nodes.append(
            semantic_node(
                f"evidence-decision.{decision['id']}",
                "evidence-decision",
                f"Evidence {decision['decision']}",
                {
                    "id": decision["id"],
                    "verifierResultId": decision["verifierResultId"],
                    "proposalId": decision["proposalId"],
                    "verificationRequirementId": decision["verificationRequirementId"],
                    "evidenceRequirementId": decision["evidenceRequirementId"],
                    "decision": decision["decision"],
                    "reviewer": decision["reviewer"],
                    "subject": decision["subject"],
                    "summary": decision["summary"],
                    "authority": decision["authority"],
                },
            )
        )
        authority_record = {
            "id": f"authority.evidence-decision.{decision['id']}",
            "kind": "evidence-decision-authority",
            "proposer": decision["reviewer"]["id"],
            "proposerType": "human",
            "requiredAuthority": decision["reviewer"]["role"],
            "validator": "p9.30-evidence-decision-validator",
            "decidedBy": decision["reviewer"]["id"],
            "decidedByType": "human",
            "decision": decision["decision"],
            "decisionStatus": decision["decision"],
            "permission": decision["reviewer"]["permission"],
            "authorityScope": decision["reviewer"]["authorityScope"],
            "authenticationStatus": decision["reviewer"]["authenticationStatus"],
            "verifierResultId": decision["verifierResultId"],
            "proposalApprovalRecorded": False,
            "graphMutationApplied": False,
            "targetRepositoryMutation": False,
        }
        nodes.append(
            semantic_node(
                authority_record["id"],
                "authority",
                f"Evidence {decision['decision']} authority",
                authority_record,
            )
        )
    projected_node_ids = {node["id"] for node in nodes}
    for result in verifier_results:
        result_node = f"verifier-result.{result['id']}"
        proposal_node = f"proposal.{result['proposalId']}"
        verification_node = f"verification.verification.verifier-result.{result['id']}"
        evidence_node = f"evidence.evidence.verifier-result.{result['id']}"
        if any(identifier not in projected_node_ids for identifier in (proposal_node, verification_node, evidence_node)):
            raise ProjectWorkspaceError("verifier result projection records are incomplete")
        edges.append({"id": f"edge.{proposal_node}.verified-by-result.{result['id']}", "category": "semantic-relation", "kind": "verified-by-result", "source": proposal_node, "target": result_node, "details": {"result": result["result"], "proposalDigest": result["subject"]["proposalDigest"]}})
        edges.append({"id": f"edge.{result_node}.records-verification.{result['id']}", "category": "semantic-relation", "kind": "records-verification", "source": result_node, "target": verification_node, "details": {"requirementId": result["verificationRequirementId"]}})
        edges.append({"id": f"edge.{result_node}.records-evidence.{result['id']}", "category": "semantic-relation", "kind": "records-evidence", "source": result_node, "target": evidence_node, "details": {"requirementId": result["evidenceRequirementId"], "evidenceDigest": result["evidence"]["digest"]}})
        if result["supersedesResultId"] is not None:
            previous_node = f"verifier-result.{result['supersedesResultId']}"
            if previous_node not in projected_node_ids:
                raise ProjectWorkspaceError("verifier result supersedes node is missing")
            edges.append({"id": f"edge.{result_node}.supersedes.{result['supersedesResultId']}", "category": "semantic-relation", "kind": "supersedes", "source": result_node, "target": previous_node, "details": {"appendOnly": True}})
    for decision in evidence_decisions:
        decision_node = f"evidence-decision.{decision['id']}"
        result_node = f"verifier-result.{decision['verifierResultId']}"
        verification_node = f"verification.verification.evidence-decision.{decision['id']}"
        evidence_node = f"evidence.evidence.evidence-decision.{decision['id']}"
        authority_node = f"authority.evidence-decision.{decision['id']}"
        if any(identifier not in projected_node_ids for identifier in (decision_node, result_node, verification_node, evidence_node, authority_node)):
            raise ProjectWorkspaceError("evidence decision projection records are incomplete")
        edges.extend(evidence_decision_projection_edges(decision))
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
    work_stage_timeline = build_work_stage_timeline(
        state,
        proposals=proposals,
        review_receipts=data["reviewReceipts"],
        verifier_results=data["verifierResults"],
        evidence_decisions=data["evidenceDecisions"],
    )
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
            "verifierResults": verifier_results,
            "evidenceDecisions": evidence_decisions,
            "verifierResultCoverage": sorted(verifier_result_coverage, key=lambda item: item["proposalId"]),
            "verifierResultIntake": {
                "artifactRole": VERIFIER_RESULT_ROLE,
                "schemaVersion": PROJECT_SCHEMA_VERSION,
                "scope": VERIFIER_RESULT_SCOPE,
                "evidenceContentType": VERIFIER_EVIDENCE_CONTENT_TYPE,
                "allowedVerifierKinds": sorted(VERIFIER_RESULT_KINDS),
                "allowedArtifactKinds": sorted(VERIFIER_ARTIFACT_KINDS),
                "allowedArtifactMediaTypes": sorted(VERIFIER_ARTIFACT_MEDIA_TYPES),
                "artifactAvailability": VERIFIER_ARTIFACT_AVAILABILITY,
                "pairs": sorted(verifier_result_intake_pairs, key=lambda item: item["key"]),
                "authority": VERIFIER_RESULT_AUTHORITY,
            },
            "evidenceDecisionIntake": {
                "artifactRole": EVIDENCE_DECISION_ROLE,
                "schemaVersion": PROJECT_SCHEMA_VERSION,
                "scope": EVIDENCE_DECISION_SCOPE,
                "allowedDecisions": sorted(EVIDENCE_DECISIONS),
                "allowedReviewerRoles": sorted(EVIDENCE_REVIEWER_ROLES),
                "decisionPermissions": EVIDENCE_DECISION_PERMISSIONS,
                "results": sorted(evidence_decision_intake_results, key=lambda item: item["key"]),
                "authority": EVIDENCE_DECISION_AUTHORITY,
            },
            "semanticFoundation": semantic_foundation,
            "changeProposals": proposals,
            "proposalDeltas": sorted(proposal_deltas, key=lambda item: item["id"]),
            "workStageTimeline": work_stage_timeline,
            "workStageRevisions": data["workStageRevisions"],
            "timelineContract": {
                "kind": "record-derived-work-stage-timeline",
                "immutableRecordsRequired": True,
                "durableRevisionCount": len(data["workStageRevisions"]),
                "legacyDerivedStageCount": sum(1 for stage in work_stage_timeline if not stage["durableRevision"]),
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
                "semanticCategories": ["project", "source-document", "goal", "capability", "constraint", "verification-requirement", "work", "intent", "mapping", "proposal", "verification", "evidence", "review-receipt", "verifier-result", "evidence-decision", "authority", "history", "code-capsule"],
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
            "loopbackVerifierResultIntakeFromUi": True,
            "loopbackEvidenceDecisionFromUi": True,
            "clientSideEvidenceArtifactHashing": True,
            "externalVerifierExecutionByWorkbench": False,
            "externalEvidenceAcceptanceByWorkbench": True,
            "evidenceAcceptanceAuthorityScope": "local-project-workspace",
            "reviewerAuthenticationByWorkbench": False,
            "targetRepositoryMutationFromUi": False,
            "approvalControlsPresent": False,
            "fullGraphDefault": True,
            "allNodesLoaded": True,
            "allEdgesLoaded": True,
            "progressiveDetail": True,
            "viewportScaleCompensation": True,
            "relationAwareCommunityLayout": True,
            "zoomStyleBuckets": True,
            "maximumZoom": 100,
            "rendererMaximumZoom": 24,
            "virtualPrecisionZoom": True,
            "effectiveGeometryMaximumZoom": 100,
            "virtualGeometryScaleAtMaximumZoom": 4.1667,
            "selectedEdgeRenderedWidthPixelsAtMaximumZoom": 0.065,
            "selectedEdgeRenderedOpacityAtMaximumZoom": 0.34,
            "selectedEdgeScreenSpaceTaper": True,
            "spectralObsidianNodeMaterial": True,
            "iridescentVoidNodeMaterial": True,
            "spectralTitaniumNodeMaterial": True,
            "browserRuntimeProbe": True,
            "headlessBrowserRegression": True,
            "canvasPixelEvidence": True,
            "rendererSafeOpticalMaterial": True,
            "cachedCanvasNodeMaterial": True,
            "viewportLocalMaterialRendering": True,
            "farZoomMaterialCulling": True,
            "precisionDeepZoomBands": True,
            "supportingNodeLabelsOnDemand": True,
            "workStageTimeline": True,
            "durableWorkStageRevisions": True,
            "allRecordedWorkItemsNavigable": True,
            "workHistorySearch": True,
            "workHistoryStatusFilter": True,
            "boundedWorkHistoryRendering": True,
            "previousNextWorkNavigation": True,
            "previousNextStageNavigation": True,
            "liveProjectionRefreshAfterMutation": True,
            "staticRevisionSnapshotImmutable": True,
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
    :root { --left:286px; --right:356px; --void:#050710; --panel:#0c101c; --panel2:#0e1320; --line:#273149; --text:#edf4ff; --muted:#91a0b7; --accent:#54b6bd; --pink:#c078a0; --violet:#8f72ae; --warn:#c9a96d; --danger:#c96d79; --code:#46a8c6; --intent:#c078a0; --work:#65a98f; --evidence:#8f72ae; --history:#687ea8; --proposal:#c96d79; }
    * { box-sizing:border-box; } body { margin:0; background:var(--void); color:var(--text); font:13px/1.45 Inter,Segoe UI,Arial,sans-serif; letter-spacing:0; overflow:hidden; }
    button,input,select { font:inherit; } button { color:var(--text); background:#161b2a; border:1px solid #323b52; border-radius:4px; padding:6px 9px; cursor:pointer; transition:border-color 120ms ease,background 120ms ease,box-shadow 120ms ease; } button:hover,button.active { border-color:var(--accent); background:#1a2634; box-shadow:0 0 0 1px rgba(101,196,214,.12); } button:disabled { opacity:.36; cursor:not-allowed; border-color:#293248; box-shadow:none; filter:saturate(.38); } input,select { width:100%; color:var(--text); background:#0b0f1a; border:1px solid #323b52; border-radius:4px; padding:7px 8px; }
    .app { height:100vh; display:grid; grid-template-rows:54px 1fr; } .topbar { display:flex; align-items:center; justify-content:space-between; padding:0 16px; border-bottom:1px solid var(--line); background:#0c0f1a; box-shadow:0 1px 10px rgba(0,0,0,.18); } .brand { display:flex; align-items:baseline; gap:9px; } .brand strong { color:#fbfcff; font-size:15px; letter-spacing:.4px; } .brand span { color:var(--muted); } .badges { display:flex; gap:6px; } .badge { color:#bbc6d6; border:1px solid #3a455b; padding:3px 7px; border-radius:99px; font-size:11px; } .badge.accent { color:#9bdfeb; border-color:#397884; }
    .workspace { min-height:0; display:grid; grid-template-columns:var(--left) 7px minmax(440px,1fr) 7px var(--right); } .rail,.inspector { overflow:auto; background:var(--panel2); } .rail { border-right:1px solid var(--line); } .inspector { border-left:1px solid var(--line); } .resizer { background:#161b2a; cursor:col-resize; position:relative; } .resizer:hover,.resizer.active { background:var(--accent); box-shadow:0 0 10px rgba(101,196,214,.2); } .section { padding:14px; border-bottom:1px solid var(--line); } h2 { margin:0 0 9px; font-size:11px; text-transform:uppercase; color:#b6c4d9; letter-spacing:.8px; } h3 { margin:0 0 7px; font-size:15px; } p { margin:5px 0; color:#c7d0dd; } label { display:block; margin:8px 0 4px; color:var(--muted); font-size:11px; } .modes { display:grid; grid-template-columns:1fr 1fr; gap:5px; } .modes button:last-child { grid-column:span 2; }
    .work-list,.stage-list { display:grid; gap:7px; } .work-controls { display:grid; grid-template-columns:minmax(0,1fr) 104px; gap:5px; margin-bottom:7px; } .work-controls input,.work-controls select { min-width:0; } .record-nav { display:grid; grid-template-columns:30px minmax(0,1fr) 30px; gap:5px; align-items:stretch; margin-bottom:8px; } .record-nav button { padding:4px; font-size:18px; line-height:1; } .record-nav button:disabled { opacity:.35; cursor:default; border-color:#293248; background:#101522; box-shadow:none; } .record-position { min-width:0; display:flex; flex-direction:column; justify-content:center; padding:4px 7px; border:1px solid #303a50; background:#0d121e; } .record-position strong,.record-position small { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; } .record-position strong { color:#dce8f4; font-size:11px; } .record-position small { color:var(--muted); font-size:10px; } .work-window-summary { margin:7px 0 0; color:var(--muted); font-size:10px; text-align:right; } .work-card { text-align:left; padding:9px; background:#151320; } .work-card.active { border-color:#65c4d6; background:#172333; box-shadow:inset 2px 0 #65c4d6; } .work-card small { display:block; color:var(--muted); margin-top:3px; } .work-card .state { display:block; color:#92fff0; text-transform:uppercase; font-size:10px; letter-spacing:.5px; } .work-card.unmapped .state { color:var(--warn); } .stage-card { text-align:left; padding:8px 9px; background:#101725; border-left:2px solid #466b8a; } .stage-card:hover,.stage-card.active { border-left-color:#92fff0; } .stage-card .stage-meta { display:flex; justify-content:space-between; gap:8px; color:#a7b9c9; font-size:10px; text-transform:uppercase; letter-spacing:.4px; } .stage-card strong,.stage-card small { display:block; } .stage-card strong { margin-top:2px; color:#e5edf6; } .stage-card small { margin-top:2px; color:var(--muted); } .stage-card .stage-delta { color:#9ce0e8; } .stage-card .stage-revision { color:#a999c9; } .stage-card .stage-revision.durable { color:#79d9c8; } .empty { color:var(--muted); font-style:italic; padding:7px 0; } .metrics { display:grid; grid-template-columns:1fr 1fr; gap:7px; } .metric { padding:8px; border:1px solid var(--line); background:#0a0910; } .metric strong { color:#fff; display:block; font-size:16px; } .metric span { color:var(--muted); font-size:11px; }
    .canvas { min-width:0; min-height:0; display:grid; grid-template-rows:68px minmax(0,1fr) 174px; background:#050812; } .canvasbar { display:flex; align-items:center; justify-content:space-between; padding:12px 16px; border-bottom:1px solid var(--line); background:#0a0f1a; } h1 { margin:0; font-size:16px; } .canvasbar p { font-size:11px; margin:2px 0 0; color:var(--muted); } .tools { display:flex; gap:5px; align-items:center; } .icon { min-width:32px; } .zoom-readout { width:64px; color:#bdebf2; font:600 11px/1.2 Consolas,monospace; text-align:center; font-variant-numeric:tabular-nums; } #projectGraph { min-height:0; position:relative; overflow:hidden; isolation:isolate; background-color:#03060d; background-image:linear-gradient(rgba(86,125,153,.022) 1px,transparent 1px),linear-gradient(90deg,rgba(86,125,153,.022) 1px,transparent 1px),radial-gradient(circle at 34% 28%,rgba(31,88,105,.055),transparent 31%),radial-gradient(circle at 72% 64%,rgba(99,46,89,.035),transparent 36%); background-size:40px 40px,40px 40px,100% 100%,100% 100%; } .node-material-layer { position:absolute; inset:0; width:100%; height:100%; z-index:7; pointer-events:none; } .review-tray { border-top:1px solid var(--line); display:grid; grid-template-columns:1.2fr 1fr 1fr; overflow:auto; background:#0a0f1a; } .tray-section { padding:12px; border-right:1px solid var(--line); } .tray-section:last-child { border-right:0; } .tray-title { color:#b7c8dd; text-transform:uppercase; font-size:10px; letter-spacing:.65px; margin-bottom:6px; } .state-line { color:#c9d2df; } .state-line strong { color:var(--warn); } .evidence-result { margin-top:6px; padding:7px; border:1px solid #30475a; background:#09111b; color:#c9d8e2; } .evidence-result strong { color:#7ee6d3; } .evidence-result small { color:#8fa6b6; overflow-wrap:anywhere; } .evidence-result.superseded { opacity:.52; border-style:dashed; } .evidence-result.current { box-shadow:inset 2px 0 #5fc8b4; } .detail { padding:8px; background:#111827; border:1px solid #35405a; border-radius:4px; } .detail + .detail { margin-top:8px; } .kv { display:grid; grid-template-columns:112px 1fr; gap:4px 8px; margin:8px 0 0; } .kv dt { color:var(--muted); } .kv dd { margin:0; overflow-wrap:anywhere; } .status-list { display:grid; gap:6px; } .status-row { display:flex; justify-content:space-between; gap:10px; padding:6px 0; border-bottom:1px solid #293248; } .status-row:last-child { border-bottom:0; } .status-row span:last-child { color:var(--warn); text-align:right; } .boundary { color:#c8d2df; } .boundary strong { color:#8cecf4; } .legend { display:grid; grid-template-columns:1fr 1fr; gap:6px; color:#ced7e5; } .legend i { width:10px; height:10px; display:inline-block; border-radius:50%; margin-right:5px; } .delta-list { display:grid; gap:4px; margin-top:8px; } .delta-step { width:100%; text-align:left; font-size:11px; padding:5px 7px; } .diff { margin:9px 0 0; padding:9px; overflow:auto; white-space:pre; background:#050812; border:1px solid #35405a; color:#d8f3ef; font:11px/1.45 Consolas,monospace; }
    @media (max-width: 980px) { :root { --left:240px; --right:300px; } .review-tray { grid-template-columns:1fr; } .canvas { grid-template-rows:68px minmax(0,1fr) 220px; } } @media (max-width: 760px) { body { overflow:auto; } .app { height:auto; min-height:100vh; } .workspace { grid-template-columns:1fr; } .resizer { display:none; } .rail,.inspector { border:0; } .canvas { min-height:560px; } }
  </style>
</head>
<body>
  <div class="app">
    <header class="topbar"><div class="brand"><strong>IntentGraph</strong><span>Project workbench</span></div><div class="badges"><span class="badge accent">local semantic overlay</span><span class="badge" id="modeBadge"></span><span class="badge" id="projectBadge"></span><span class="badge" id="snapshotBadge"></span></div></header>
    <div class="workspace">
      <aside class="rail">
        <section class="section"><h2>Graph lens</h2><div class="modes"><button class="mode active" data-mode="all">Full graph</button><button class="mode" data-mode="overview">Semantic overview</button><button class="mode" data-mode="impact">Active work</button><button class="mode" data-mode="code">Code topology</button><button class="mode" data-mode="focus">Focus selection</button><button id="clearSelection">Clear focus</button></div></section>
        <section class="section"><h2>Find</h2><label for="search">Node, relation, or source file</label><input id="search" type="search" placeholder="Find project or code fact"><label for="categoryFilter">Node category</label><select id="categoryFilter"></select><label for="relationFilter">Relation kind</label><select id="relationFilter"></select></section>
        <section class="section"><h2>Work history</h2><div class="work-controls"><input id="workSearch" type="search" aria-label="Find recorded work" placeholder="Work id, title, request"><select id="workStatusFilter" aria-label="Work state"><option value="">All states</option><option value="unmapped">Unmapped</option><option value="mapped">Mapped</option><option value="proposal-ready">Proposal ready</option><option value="verification-observed">Verification observed</option><option value="blocked">Blocked</option><option value="reviewed">Review receipt</option></select></div><div class="record-nav"><button id="previousWork" type="button" title="Previous work" aria-label="Previous work">&lsaquo;</button><div id="workPosition" class="record-position"></div><button id="nextWork" type="button" title="Next work" aria-label="Next work">&rsaquo;</button></div><div id="workList" class="work-list"></div><div id="workWindowSummary" class="work-window-summary"></div></section>
        <section class="section"><h2>Work stages</h2><div class="record-nav"><button id="previousStage" type="button" title="Previous stage" aria-label="Previous stage">&lsaquo;</button><div id="stagePosition" class="record-position"></div><button id="nextStage" type="button" title="Next stage" aria-label="Next stage">&rsaquo;</button></div><div id="stageList" class="stage-list"></div></section>
        <section class="section"><h2>Project snapshot</h2><div id="metrics" class="metrics"></div></section>
        <section class="section"><h2>Legend</h2><div class="legend"><div><i style="background:var(--code)"></i>Code fact</div><div><i style="background:#d6a762"></i>Goal / Intent</div><div><i style="background:#5fb8a5"></i>Capability / work</div><div><i style="background:#7993a8"></i>Source document</div><div><i style="background:var(--evidence)"></i>Evidence / verify</div><div><i style="background:#5fc8b4"></i>Observed verifier result</div><div><i style="background:#d5b15b"></i>Evidence decision</div><div><i style="background:var(--history)"></i>History / authority</div></div></section>
      </aside>
      <div class="resizer" data-side="left" role="separator" aria-label="Resize navigation"></div>
      <main class="canvas">
        <div class="canvasbar"><div><h1 id="graphTitle">Full project graph</h1><p id="graphSummary"></p></div><div class="tools"><button class="icon" id="zoomOut" title="Zoom out">-</button><output id="zoomReadout" class="zoom-readout" title="Current graph zoom; maximum 100x">x1.0</output><button class="icon" id="zoomIn" title="Zoom in">+</button><button class="icon" id="zoom100" title="Jump to 100x around the current selection">100x</button><button class="icon" id="fitGraph" title="Fit graph">Fit</button></div></div>
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
    const liveMode=typeof window.__intentGraphLoadProjection==='function';
    const runtimeProbeRequested=new URLSearchParams(window.location.search).get('intentGraphRuntimeProbe')==='1';
    const runtimeProbeErrors=[];
    if(runtimeProbeRequested){window.addEventListener('error',event=>runtimeProbeErrors.push(String(event.error?.message||event.message||'window error')));window.addEventListener('unhandledrejection',event=>runtimeProbeErrors.push(String(event.reason?.message||event.reason||'unhandled rejection')));}
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
    const workItems=model.workflow.workItems||[],workStages=model.workflow.workStageTimeline||[],workListRenderLimit=60;
    const state = { mode:model.graph.defaultView?.id || 'all', selected:null, selectedWorkId:workItems.length?workItems[workItems.length-1].id:null, stageFocus:null, cy:null, renderTimer:null, workFilterTimer:null, zoomSettleTimer:null, precisionZoomOverride:null, precisionActualZoomOverride:null, detailLevel:null, viewportScale:null, positions:null, visibleNodeIds:null, visibleEdgeIds:null, highlighted:null, highlightedEdgeIds:new Set(), emphasizedNodeIds:new Set(), emphasizedEdgeIds:new Set(), stageAddedNodeIds:new Set(), stageChangedNodeIds:new Set(), stageEdgeIds:new Set(), searchMatchNodeIds:new Set(), onDemandLabelIds:new Set(), resizeQueued:false, graphInstanceCount:0, visibilityUpdates:0, renderedWorkCardCount:0, virtualGeometryScale:1, virtualGeometryAnchorId:null, virtualGeometryFrame:null, desiredLogicalZoom:1, desiredActualZoom:1, materialLayer:null, materialContext:null, materialFrame:null, materialSpriteCache:new Map(), materialProfile:null, materialDrawCount:0, materialCulledOrdinaryCodeCount:0 };
    const precisionZoomPivot=18,rendererMaximumZoom=24,logicalMaximumZoom=100;
    function logicalZoomFromActual(actual){if(actual<=precisionZoomPivot)return actual;return precisionZoomPivot+(actual-precisionZoomPivot)*(logicalMaximumZoom-precisionZoomPivot)/(rendererMaximumZoom-precisionZoomPivot);}
    function actualZoomFromLogical(logical){if(logical<=precisionZoomPivot)return logical;return precisionZoomPivot+(logical-precisionZoomPivot)*(rendererMaximumZoom-precisionZoomPivot)/(logicalMaximumZoom-precisionZoomPivot);}
    const colors = { code:'#58a8bd', project:'#77c4c5', 'source-document':'#738ba2', goal:'#b99b67', capability:'#689b84', constraint:'#ae765e', 'verification-requirement':'#8976a0', work:'#68a083', intent:'#a96f8d', mapping:'#ad9660', proposal:'#b9616d', verification:'#756b98', evidence:'#806c9b', 'review-receipt':'#8f6ca5', 'verifier-result':'#6cc5b3', 'evidence-decision':'#c2a25a', authority:'#6382a8', history:'#667894' };
    const communityPalette = ['#477f94','#8a7957','#8c5963','#4f817c','#627e68','#837653','#715f83','#815d71','#846451','#667788'];
    const safe = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
    const short = value => String(value || '').replace('sha256:','').slice(0,12);
    const rows = entries => `<dl class="kv">${entries.map(([key,value])=>`<dt>${safe(key)}</dt><dd>${safe(value)}</dd>`).join('')}</dl>`;
    function populate(id, values, label) { document.getElementById(id).innerHTML=`<option value="">All ${safe(label)}</option>`+values.map(value=>`<option value="${safe(value)}">${safe(value)}</option>`).join(''); }
    function filters() { return { search:document.getElementById('search').value.trim().toLowerCase(), category:document.getElementById('categoryFilter').value, relation:document.getElementById('relationFilter').value }; }
    function sourceModule(node) { return node.category==='code-capsule' ? node.label : String(node.source?.file||'Unmapped').split('/')[0]; }
    function stableHash(value) { let hash=2166136261; for(let index=0;index<value.length;index+=1){hash^=value.charCodeAt(index);hash=Math.imul(hash,16777619);} return hash>>>0; }
    function nodeColor(node) { return node.category==='code'||node.category==='code-capsule' ? communityPalette[stableHash(sourceModule(node))%communityPalette.length] : (colors[node.category]||'#8fa1b9'); }
    function rgba(hex,alpha){const value=String(hex||'#8fa1b9').replace('#',''),full=value.length===3?value.split('').map(char=>char+char).join(''):value,number=parseInt(full,16);return `rgba(${number>>16&255},${number>>8&255},${number&255},${alpha})`;}
    function materialShape(node){if(['file','source-document','work'].includes(node.kind)||['source-document','work'].includes(node.category))return 'squircle';if(['type','project','code-capsule','proposal'].includes(node.kind)||['project','code-capsule','proposal'].includes(node.category))return 'hex';if(['verification','evidence','verifier-result','evidence-decision','authority','history','verification-requirement'].includes(node.category))return 'diamond';return 'orb';}
    function traceMaterialShape(context,shape,cx,cy,radius){context.beginPath();if(shape==='squircle'){const left=cx-radius,right=cx+radius,top=cy-radius,bottom=cy+radius,corner=radius*.36;context.moveTo(left+corner,top);context.lineTo(right-corner,top);context.quadraticCurveTo(right,top,right,top+corner);context.lineTo(right,bottom-corner);context.quadraticCurveTo(right,bottom,right-corner,bottom);context.lineTo(left+corner,bottom);context.quadraticCurveTo(left,bottom,left,bottom-corner);context.lineTo(left,top+corner);context.quadraticCurveTo(left,top,left+corner,top);}else if(shape==='hex'){for(let index=0;index<6;index+=1){const angle=Math.PI/3*index-Math.PI/2,point={x:cx+Math.cos(angle)*radius,y:cy+Math.sin(angle)*radius};if(index===0)context.moveTo(point.x,point.y);else context.lineTo(point.x,point.y);}}else if(shape==='diamond'){context.moveTo(cx,cy-radius);context.lineTo(cx+radius*.82,cy);context.lineTo(cx,cy+radius);context.lineTo(cx-radius*.82,cy);}else context.arc(cx,cy,radius,0,Math.PI*2);context.closePath();}
    function materialSprite(node,selected,accent){const color=nodeColor(node),shape=materialShape(node),key=['spectral-titanium-v2',color,shape,selected?'selected':'normal',accent||''].join('|');if(state.materialSpriteCache.has(key))return state.materialSpriteCache.get(key);const canvas=document.createElement('canvas');canvas.width=canvas.height=128;const context=canvas.getContext('2d'),cx=64,cy=64,radius=29;
      // Cached sprites keep the live graph cheap while preserving a legible, asymmetric metal finish at 12-24px.
      const halo=context.createRadialGradient(cx,cy,radius*.9,cx,cy,46);halo.addColorStop(0,rgba(color,selected?.12:.045));halo.addColorStop(.58,rgba(color,selected?.035:.012));halo.addColorStop(1,rgba(color,0));context.fillStyle=halo;context.fillRect(0,0,128,128);
      context.save();traceMaterialShape(context,shape,cx,cy,radius);context.clip();context.fillStyle='#01040a';context.fillRect(31,31,66,66);
      const titanium=context.createLinearGradient(37,91,91,35);titanium.addColorStop(0,'rgba(1,4,9,1)');titanium.addColorStop(.24,'rgba(8,14,22,1)');titanium.addColorStop(.46,rgba(color,.18));titanium.addColorStop(.505,'rgba(190,229,232,.22)');titanium.addColorStop(.55,rgba(color,.1));titanium.addColorStop(.75,'rgba(5,9,16,1)');titanium.addColorStop(1,'rgba(0,2,6,1)');context.fillStyle=titanium;context.fillRect(31,31,66,66);
      const shadow=context.createLinearGradient(35,38,92,88);shadow.addColorStop(0,'rgba(213,240,241,.08)');shadow.addColorStop(.2,'rgba(0,0,0,0)');shadow.addColorStop(.63,'rgba(0,0,0,.32)');shadow.addColorStop(1,'rgba(0,0,0,.72)');context.fillStyle=shadow;context.fillRect(31,31,66,66);
      context.globalCompositeOperation='screen';const spectral=context.createLinearGradient(39,86,88,40);spectral.addColorStop(.31,'rgba(0,0,0,0)');spectral.addColorStop(.435,'rgba(80,214,224,.03)');spectral.addColorStop(.49,'rgba(154,241,239,.23)');spectral.addColorStop(.515,'rgba(190,104,164,.2)');spectral.addColorStop(.545,'rgba(222,176,101,.13)');spectral.addColorStop(.63,'rgba(0,0,0,0)');context.fillStyle=spectral;context.fillRect(31,31,66,66);context.globalCompositeOperation='source-over';
      let grainSeed=stableHash(key);for(let grainIndex=0;grainIndex<34;grainIndex+=1){grainSeed=Math.imul(grainSeed^grainIndex,1664525)+1013904223>>>0;const gy=38+(grainSeed%5200)/100,gx=39+((grainSeed>>>11)%5000)/100;context.fillStyle=grainIndex%7===0?'rgba(210,239,239,.105)':rgba(color,.052);context.fillRect(gx,gy,grainIndex%5===0?1.25:.55,.45);}context.restore();
      context.save();context.shadowColor=rgba(color,selected?.52:.22);context.shadowBlur=selected?7:3;traceMaterialShape(context,shape,cx,cy,radius+.5);context.strokeStyle='rgba(0,0,0,.98)';context.lineWidth=5;context.stroke();context.restore();
      traceMaterialShape(context,shape,cx,cy,radius+.15);context.strokeStyle='rgba(219,239,241,.26)';context.lineWidth=.82;context.stroke();traceMaterialShape(context,shape,cx,cy,radius-1.05);context.strokeStyle=rgba(color,.34);context.lineWidth=.66;context.stroke();traceMaterialShape(context,shape,cx,cy,radius-3.2);context.strokeStyle='rgba(187,224,227,.11)';context.lineWidth=.48;context.stroke();
      context.save();traceMaterialShape(context,shape,cx,cy,radius-4.2);context.clip();context.beginPath();context.moveTo(39,80);context.lineTo(88,41);context.strokeStyle='rgba(186,238,240,.2)';context.lineWidth=.62;context.stroke();context.beginPath();context.moveTo(42,85);context.lineTo(83,45);context.strokeStyle=rgba(color,.16);context.lineWidth=.44;context.stroke();context.setLineDash([1.1,2.4]);context.beginPath();context.arc(cx,cy,11,0,Math.PI*2);context.strokeStyle='rgba(196,230,232,.14)';context.lineWidth=.52;context.stroke();context.setLineDash([]);context.beginPath();context.moveTo(cx-6,cy);context.lineTo(cx+6,cy);context.moveTo(cx,cy-6);context.lineTo(cx,cy+6);context.strokeStyle=rgba(color,.2);context.lineWidth=.5;context.stroke();context.restore();
      context.beginPath();context.arc(cx,cy,radius+.35,-2.72,-1.32);context.strokeStyle='rgba(115,226,234,.72)';context.lineWidth=.8;context.stroke();context.beginPath();context.arc(cx,cy,radius+.25,-.18,.62);context.strokeStyle='rgba(213,97,163,.45)';context.lineWidth=.64;context.stroke();context.beginPath();context.arc(cx,cy,radius+.2,.72,1.16);context.strokeStyle='rgba(232,185,101,.3)';context.lineWidth=.52;context.stroke();
      if(accent){context.beginPath();context.arc(cx,cy,radius+2.8,-2.72,-1.82);context.strokeStyle=accent;context.globalAlpha=.7;context.lineWidth=.82;context.stroke();context.beginPath();context.arc(cx,cy,radius+2.6,.34,.78);context.globalAlpha=.32;context.lineWidth=.58;context.stroke();context.globalAlpha=1;}if(selected){traceMaterialShape(context,shape,cx,cy,radius+3.8);context.strokeStyle='rgba(177,242,243,.88)';context.lineWidth=.82;context.stroke();}
      state.materialSpriteCache.set(key,canvas);return canvas;}
    function ensureMaterialLayer(){if(state.materialLayer)return;const host=document.getElementById('projectGraph'),layer=document.createElement('canvas');layer.className='node-material-layer';layer.setAttribute('aria-hidden','true');host.appendChild(layer);state.materialLayer=layer;state.materialContext=layer.getContext('2d',{alpha:true});}
    function materialNodeSize(node){const profileState=state.materialProfile;if(!profileState)return node.category==='code'?3:16;const {profile,scale,actualZoom}=profileState;let value=profile.node;if(node.category==='code-capsule')value=profile.capsule;else if(node.category==='code'){value=profile.code;if(node.kind==='file')value=profile.file;else if(node.kind==='namespace')value=profile.namespace;else if(node.kind==='type')value=profile.type;}return Math.max(node.category==='code'?2.2:8,Math.min(42,value*scale*actualZoom));}
    function drawMaterialLayer(){
      state.materialFrame=null;if(!state.cy)return;ensureMaterialLayer();
      const layer=state.materialLayer,context=state.materialContext,width=Math.max(1,Math.round(state.cy.width())),height=Math.max(1,Math.round(state.cy.height())),ratio=Math.min(2,window.devicePixelRatio||1);
      if(layer.width!==Math.round(width*ratio)||layer.height!==Math.round(height*ratio)){layer.width=Math.round(width*ratio);layer.height=Math.round(height*ratio);layer.style.width=width+'px';layer.style.height=height+'px';}
      context.setTransform(ratio,0,0,ratio,0,0);context.clearRect(0,0,width,height);
      const zoom=state.cy.zoom(),pan=state.cy.pan(),positions=state.positions||(state.positions=buildPresetPositions()),factor=state.virtualGeometryScale||1,anchor=positions.get(state.virtualGeometryAnchorId)||{x:0,y:0},farMaterial=state.detailLevel==='overview';let drawn=0,culledOrdinaryCode=0;
      allNodes.forEach(node=>{
        if(state.visibleNodeIds&&!state.visibleNodeIds.has(node.id))return;const base=positions.get(node.id);if(!base)return;
        const selected=state.selected?.type==='node'&&state.selected.id===node.id;
        const accent=state.stageAddedNodeIds.has(node.id)?'#71ead8':state.stageChangedNodeIds.has(node.id)?'#f0a36d':state.searchMatchNodeIds.has(node.id)?'#8de0e8':state.emphasizedNodeIds.has(node.id)?'#d7b56c':'';
        const materialLandmark=node.category!=='code'||['file','namespace','type'].includes(node.kind)||importantCodeLabelIds.has(node.id)||selected||Boolean(accent);
        if(farMaterial&&!materialLandmark){culledOrdinaryCode+=1;return;}
        const modelX=anchor.x+(base.x-anchor.x)*factor,modelY=anchor.y+(base.y-anchor.y)*factor,x=modelX*zoom+pan.x,y=modelY*zoom+pan.y,size=materialNodeSize(node),outer=size*1.44;
        if(x+outer<0||x-outer>width||y+outer<0||y-outer>height)return;
        context.globalAlpha=node.category==='code'&&state.detailLevel==='overview'?.58:1;context.drawImage(materialSprite(node,selected,accent),x-outer/2,y-outer/2,outer,outer);drawn+=1;
      });
      context.globalAlpha=1;state.materialDrawCount=drawn;state.materialCulledOrdinaryCodeCount=culledOrdinaryCode;layer.dataset.drawCount=String(drawn);layer.dataset.culledOrdinaryCode=String(culledOrdinaryCode);layer.dataset.spriteCount=String(state.materialSpriteCache.size);layer.dataset.material='cached-spectral-titanium-v2';
    }
    function scheduleMaterialLayer(){if(state.materialFrame!==null)return;state.materialFrame=window.requestAnimationFrame(drawMaterialLayer);}
    function spiralPoint(index,scale,rotation=0) { const golden=Math.PI*(3-Math.sqrt(5)),radius=scale*Math.sqrt(index+.75),angle=rotation+index*golden; return {x:Math.cos(angle)*radius,y:Math.sin(angle)*radius}; }
    function buildPresetPositions() {
      const positions=new Map(),groups=new Map(),capsules=new Map();
      allNodes.filter(node=>node.category==='code-capsule').forEach(node=>capsules.set(node.label,node));
      allNodes.filter(node=>node.category==='code').forEach(node=>{const group=sourceModule(node);if(!groups.has(group))groups.set(group,[]);groups.get(group).push(node);});
      const orderedGroups=[...groups.entries()].sort((left,right)=>right[1].length-left[1].length||left[0].localeCompare(right[0]));
      const centers=new Map(),groupIndex=new Map(),totalCode=allNodes.filter(node=>node.category==='code').length;
      orderedGroups.forEach(([group],index)=>{groupIndex.set(group,index);const angle=index*Math.PI*2/Math.max(1,orderedGroups.length)+stableHash(group)%97/250;const radius=360+Math.min(150,Math.sqrt(totalCode)*1.35)+(stableHash(group)%47);centers.set(group,{x:Math.cos(angle)*radius,y:Math.sin(angle)*radius});});
      const links=new Map(),linkKey=(left,right)=>left<right?left+'\u001f'+right:right+'\u001f'+left;
      allEdges.forEach(edge=>{if(edge.category!=='code-relation'||!['calls','references','constructs','inherits','implements'].includes(edge.kind))return;const source=nodeById.get(edge.source),target=nodeById.get(edge.target);if(!source||!target||source.category!=='code'||target.category!=='code')return;const left=sourceModule(source),right=sourceModule(target);if(left===right||!groupIndex.has(left)||!groupIndex.has(right))return;const key=linkKey(left,right);links.set(key,(links.get(key)||0)+1);});
      // A small deterministic force pass on module centers uses real local-symbol links.
      // It runs once while building the preset, never during pan or wheel interactions.
      for(let iteration=0;iteration<96;iteration+=1){
        const forces=new Map(orderedGroups.map(([group])=>[group,{x:0,y:0}]));
        for(let leftIndex=0;leftIndex<orderedGroups.length;leftIndex+=1){for(let rightIndex=leftIndex+1;rightIndex<orderedGroups.length;rightIndex+=1){
          const left=orderedGroups[leftIndex][0],right=orderedGroups[rightIndex][0],a=centers.get(left),b=centers.get(right);let dx=b.x-a.x,dy=b.y-a.y,distance=Math.max(1,Math.hypot(dx,dy));dx/=distance;dy/=distance;
          const repulsion=92000/(distance*distance);forces.get(left).x-=dx*repulsion;forces.get(left).y-=dy*repulsion;forces.get(right).x+=dx*repulsion;forces.get(right).y+=dy*repulsion;
          const weight=links.get(linkKey(left,right))||0;if(weight){const targetDistance=330-Math.min(105,Math.log1p(weight)*27),spring=(distance-targetDistance)*(.0035+Math.min(.013,weight*.000028));forces.get(left).x+=dx*spring;forces.get(left).y+=dy*spring;forces.get(right).x-=dx*spring;forces.get(right).y-=dy*spring;}
        }}
        orderedGroups.forEach(([group])=>{const point=centers.get(group),force=forces.get(group),distance=Math.max(1,Math.hypot(point.x,point.y));force.x-=point.x/distance*.12;force.y-=point.y/distance*.12;const step=Math.min(11,Math.hypot(force.x,force.y));if(step){point.x+=force.x/Math.hypot(force.x,force.y)*step;point.y+=force.y/Math.hypot(force.x,force.y)*step;}});
      }
      orderedGroups.forEach(([group,nodes])=>{
        const center=centers.get(group),files=new Map();
        nodes.forEach(node=>{const file=String(node.source?.file||'Unmapped');if(!files.has(file))files.set(file,[]);files.get(file).push(node);});
        const fileScale=24+Math.min(23,Math.sqrt(nodes.length)*.62);
        [...files.entries()].sort((left,right)=>left[0].localeCompare(right[0])).forEach(([file,fileNodes],fileIndex)=>{
          const filePoint=spiralPoint(fileIndex,fileScale,stableHash(file)%628/100),fileCenter={x:center.x+filePoint.x,y:center.y+filePoint.y};
          fileNodes.slice().sort((left,right)=>(left.kind+'|'+left.id).localeCompare(right.kind+'|'+right.id)).forEach((node,nodeIndex)=>{
            if(node.kind==='file'){positions.set(node.id,fileCenter);return;}
            const local=spiralPoint(nodeIndex,3.7,stableHash(node.id)%628/100);
            positions.set(node.id,{x:fileCenter.x+local.x,y:fileCenter.y+local.y});
          });
        });
        const capsule=capsules.get(group);if(capsule)positions.set(capsule.id,center);
      });
      const semanticGroups=new Map();
      allNodes.filter(node=>node.category!=='code'&&node.category!=='code-capsule'&&node.category!=='project').forEach(node=>{if(!semanticGroups.has(node.category))semanticGroups.set(node.category,[]);semanticGroups.get(node.category).push(node);});
      [...semanticGroups.entries()].sort((left,right)=>left[0].localeCompare(right[0])).forEach(([category,nodes],categoryIndex)=>{
        const angle=categoryIndex*Math.PI*2/semanticGroups.size+stableHash(category)%61/100;
        const center={x:Math.cos(angle)*(108+(categoryIndex%2)*26),y:Math.sin(angle)*(108+(categoryIndex%2)*26)};
        nodes.slice().sort((left,right)=>left.id.localeCompare(right.id)).forEach((node,nodeIndex)=>{
          const local=spiralPoint(nodeIndex,15,stableHash(node.id)%628/100);
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
      document.getElementById('workSearch').addEventListener('input',scheduleWorkHistoryRender);
      document.getElementById('workStatusFilter').addEventListener('change',renderWorkHistory);
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
    const spectralObsidianOpticalMaterial={'background-fill':'solid','background-color':'#070a11','background-blacken':0,'background-opacity':.08,'border-color':'data(color)','border-opacity':.08,'outline-color':'data(color)','outline-opacity':0,'outline-style':'solid','padding':0,'overlay-opacity':0,'overlay-padding':0};
    function graphStyle(){return [
      {selector:'node',style:{...spectralObsidianOpticalMaterial,'shape':'ellipse','label':'data(label)','color':'#edf7fb','font-family':'Inter,Segoe UI,Arial,sans-serif','font-weight':600,'font-size':9.5,'text-wrap':'ellipsis','text-max-width':126,'text-valign':'bottom','text-margin-y':5,'width':15,'height':15,'border-width':.52,'underlay-opacity':0,'underlay-padding':0,'underlay-shape':'ellipse','text-outline-width':1.35,'text-outline-color':'#030710','text-outline-opacity':.96}},
      {selector:'node[category = "code"]',style:{'label':'','background-fill':'solid','background-color':'data(color)','background-opacity':.08,'background-blacken':.65,'width':2.2,'height':2.2,'opacity':1,'border-width':0,'border-opacity':0,'outline-width':0,'outline-opacity':0,'underlay-opacity':0,'underlay-padding':0}},
      {selector:'node[category = "code"][kind = "file"]',style:{...spectralObsidianOpticalMaterial,'shape':'round-rectangle','width':6.5,'height':6.5,'background-opacity':.08,'border-width':.42,'border-color':'#d8fbff','border-opacity':.08,'underlay-opacity':0,'underlay-padding':0}},
      {selector:'node[category = "code"][kind = "namespace"]',style:{...spectralObsidianOpticalMaterial,'shape':'diamond','width':4.3,'height':4.3,'border-opacity':.76}},
      {selector:'node[category = "code"][kind = "type"]',style:{...spectralObsidianOpticalMaterial,'shape':'round-hexagon','width':5.2,'height':5.2,'border-opacity':.82}},
      {selector:'node[category = "code"][kind = "constructor"]',style:{'shape':'round-diamond'}},
      {selector:'node[category = "code"][kind = "property"]',style:{'shape':'round-rectangle'}},
      {selector:'node[category = "code"][kind = "field"]',style:{'shape':'round-rectangle'}},
      {selector:'node[category = "code-capsule"]',style:{...spectralObsidianOpticalMaterial,'background-opacity':.06,'shape':'round-hexagon','border-width':.46,'border-opacity':.06,'underlay-opacity':0,'underlay-padding':0,'font-size':9,'font-weight':600,'text-max-width':135,'width':19,'height':19,'color':'#dcebf3'}},
      {selector:'node[category = "project"]',style:{'shape':'round-hexagon'}},
      {selector:'node[category = "source-document"]',style:{'shape':'round-rectangle'}},
      {selector:'node[category = "goal"]',style:{'shape':'ellipse'}},
      {selector:'node[category = "intent"]',style:{'shape':'ellipse'}},
      {selector:'node[category = "work"]',style:{'shape':'round-rectangle'}},
      {selector:'node[category = "proposal"]',style:{'shape':'round-diamond'}},
      {selector:'node[category = "verification"]',style:{'shape':'diamond'}},
      {selector:'node[category = "evidence"]',style:{'shape':'diamond'}},
      {selector:'node[labelMode = "on-demand"]',style:{'label':''}},
      {selector:'node.show-on-demand-label',style:{'label':'data(label)','font-size':8.5,'text-max-width':118,'color':'#cfd9e5','text-outline-width':0}},
      {selector:'node.low-detail',style:{'opacity':.46}},
      {selector:'node[deltaState = "proposed-change"]',style:{'border-width':2,'border-color':'#e37c74','border-opacity':1}},
      {selector:'edge',style:{'width':.52,'line-color':'data(color)','curve-style':'straight','opacity':.38}},
      {selector:'edge[category = "code-relation"]',style:{'width':.28,'line-color':'data(color)','opacity':.22}},
      {selector:'edge.low-detail',style:{'opacity':.055}},
      {selector:'edge.detail-edge',style:{'width':.48,'opacity':.28}},
      {selector:'edge[category = "capsule-relation"]',style:{'width':.9,'opacity':.52}},
      {selector:'edge[category = "mapping-relation"]',style:{'line-color':'#d7b56c','line-style':'dashed','width':1.1,'opacity':.75}},
      {selector:'edge[category = "delta-relation"]',style:{'line-color':'#de817a','line-style':'dashed','width':1.1,'opacity':.8}},
      {selector:'edge[kind = "invokes-syntax"]',style:{'line-color':'#8d78c1','line-style':'dashed'}},
      {selector:'.filtered-out',style:{'display':'none'}},
      {selector:'node.semantic-emphasis',style:{'border-width':.72,'border-color':'#988767','border-opacity':.42,'underlay-color':'#8d7a58','underlay-opacity':.055,'z-index':97}},
      {selector:'edge.semantic-emphasis',style:{'line-color':'#8f8268','width':.72,'opacity':.54,'z-index':96}},
      {selector:'node.stage-added',style:{'border-width':2.3,'border-color':'#70e5d2','border-opacity':1,'underlay-color':'#70e5d2','underlay-opacity':.25,'z-index':98}},
      {selector:'node.stage-changed',style:{'border-width':2.5,'border-color':'#f0a36d','border-opacity':1,'underlay-color':'#f0a36d','underlay-opacity':.25,'z-index':98}},
      {selector:'edge.stage-delta',style:{'line-color':'#7de2e9','width':1.35,'opacity':.96,'z-index':97}},
      {selector:'node.search-match',style:{'border-width':2,'border-color':'#8de0e8','border-opacity':1,'underlay-color':'#8de0e8','underlay-opacity':.24,'z-index':98}},
      {selector:'node:selected',style:{'border-opacity':0,'underlay-opacity':0,'overlay-opacity':0,'z-index':99}},
      {selector:'edge:selected',style:{'line-color':'#aee8eb','opacity':.58,'overlay-opacity':0,'underlay-opacity':0,'z-index':99}},
      {selector:'edge.selection-neighbor',style:{'line-color':'#6d9ca3','width':.38,'opacity':.34,'overlay-opacity':0,'underlay-opacity':0,'z-index':98}}
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
      if(state.mode==='code'&&state.cy?.zoom()>=.36)allNodes.filter(node=>node.category==='code-capsule').forEach(node=>labels.add(node.id));
      const remove=setDifference(state.onDemandLabelIds||emptyIds,labels),add=setDifference(labels,state.onDemandLabelIds||emptyIds);
      if(remove.length||add.length)state.cy.batch(()=>{remove.forEach(id=>state.cy.$id(id).removeClass('show-on-demand-label'));add.forEach(id=>state.cy.$id(id).addClass('show-on-demand-label'));});
      state.onDemandLabelIds=labels;
      scheduleMaterialLayer();
    }
    function precisionAnchorId(){if(state.selected?.type==='node')return state.selected.id;if(state.selected?.type==='edge'){const edge=allEdges.find(candidate=>candidate.id===state.selected.id);if(edge)return edge.source;}return allNodes.find(node=>node.category==='project')?.id||allNodes[0]?.id||null;}
    function applyVirtualGeometry(force=false){
      state.virtualGeometryFrame=null;if(!state.cy)return;
      const logical=state.desiredLogicalZoom||logicalZoomFromActual(state.cy.zoom()),actual=Math.max(.1,state.desiredActualZoom||state.cy.zoom()),factor=logical>precisionZoomPivot?logical/actual:1,readout=document.getElementById('zoomReadout');
      readout.dataset.virtualGeometryScale=factor.toFixed(4);readout.dataset.effectiveGeometryZoom=(actual*factor).toFixed(3);
      if(!force&&Math.abs(factor-state.virtualGeometryScale)<.002){scheduleMaterialLayer();return;}
      const positions=state.positions||(state.positions=buildPresetPositions());if(factor>1&&!state.virtualGeometryAnchorId)state.virtualGeometryAnchorId=precisionAnchorId();const anchor=positions.get(state.virtualGeometryAnchorId)||{x:0,y:0};
      state.cy.batch(()=>state.cy.nodes().positions(item=>{const base=positions.get(item.id())||{x:0,y:0};return {x:anchor.x+(base.x-anchor.x)*factor,y:anchor.y+(base.y-anchor.y)*factor};}));
      state.virtualGeometryScale=factor;if(factor===1)state.virtualGeometryAnchorId=null;scheduleMaterialLayer();
    }
    function scheduleVirtualGeometry(){if(!state.cy)return;state.desiredActualZoom=state.cy.zoom();state.desiredLogicalZoom=logicalZoomFromActual(state.desiredActualZoom);if(state.virtualGeometryFrame!==null)return;state.virtualGeometryFrame=window.requestAnimationFrame(()=>applyVirtualGeometry());}
    function fitNodes(nodes) {
      if(!nodes.length)return;
      state.desiredLogicalZoom=1;state.desiredActualZoom=1;applyVirtualGeometry(true);
      const positions=state.positions||(state.positions=buildPresetPositions());
      let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
      nodes.forEach(node=>{const point=positions.get(node.id)||{x:0,y:0};minX=Math.min(minX,point.x);minY=Math.min(minY,point.y);maxX=Math.max(maxX,point.x);maxY=Math.max(maxY,point.y);});
      const padding=26,width=Math.max(1,state.cy.width()-padding*2),height=Math.max(1,state.cy.height()-padding*2),spanX=Math.max(110,maxX-minX),spanY=Math.max(110,maxY-minY),zoom=Math.max(state.cy.minZoom(),Math.min(state.cy.maxZoom(),Math.min(width/spanX,height/spanY))),centerX=(minX+maxX)/2,centerY=(minY+maxY)/2;
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
          layout:{name:'preset',fit:true,padding:26},
          minZoom:.10,maxZoom:rendererMaximumZoom,pixelRatio:1,textureOnViewport:false,motionBlur:false,hideEdgesOnViewport:true,boxSelectionEnabled:false,autoungrabify:true
        });
        state.graphInstanceCount+=1;
        ensureMaterialLayer();
        state.cy.on('tap','node',event=>{state.selected={type:'node',id:event.target.id()};renderSelection();highlight();});
        state.cy.on('tap','edge',event=>{state.selected={type:'edge',id:event.target.id()};renderSelection();highlight();});
        state.cy.on('tap',event=>{if(event.target===state.cy){state.selected=null;renderSelection();highlight();}});
        state.cy.on('zoom',()=>{updateZoomReadout();scheduleVirtualGeometry();updateViewportScale();scheduleSettledSemanticZoom();scheduleMaterialLayer();});
        state.cy.on('pan render',scheduleMaterialLayer);
      }
      applyGraphVisibility(graph,Boolean(options.fit),searchMatches);
    }
    function scheduleSettledSemanticZoom(){window.clearTimeout(state.zoomSettleTimer);state.zoomSettleTimer=window.setTimeout(semanticZoom,350);}
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
    function updateZoomReadout(){if(!state.cy)return;const actualZoom=state.cy.zoom(),zoom=logicalZoomFromActual(actualZoom),display=zoom<1?zoom.toFixed(2):zoom<10?zoom.toFixed(1):Math.round(zoom),readout=document.getElementById('zoomReadout');readout.textContent='x'+display;readout.dataset.rendererZoom=actualZoom.toFixed(3);if(zoom>=60){const project=allNodes.find(node=>node.category==='project'),item=project?state.cy.$id(project.id):null;if(item?.length){const bounds=item.renderedBoundingBox({includeLabels:false,includeOverlays:false,includeUnderlays:false}),modelBounds=item.boundingBox({includeLabels:false,includeOverlays:false,includeUnderlays:false}),position=item.renderedPosition();readout.dataset.maximumZoomProjectModelWidth=item.style('width');readout.dataset.maximumZoomProjectOuterWidth=String(item.outerWidth());readout.dataset.maximumZoomProjectRenderedWidth=item.renderedStyle('width');readout.dataset.maximumZoomProjectPadding=item.style('padding');readout.dataset.maximumZoomProjectBorderWidth=item.style('border-width');readout.dataset.maximumZoomProjectOutlineWidth=item.style('outline-width');readout.dataset.maximumZoomProjectOutlineOffset=item.style('outline-offset');readout.dataset.maximumZoomProjectBoundsExpansion=item.style('bounds-expansion');readout.dataset.maximumZoomProjectOverlayOpacity=item.style('overlay-opacity');readout.dataset.maximumZoomProjectOverlayPadding=item.style('overlay-padding');readout.dataset.maximumZoomProjectUnderlayOpacity=item.style('underlay-opacity');readout.dataset.maximumZoomProjectUnderlayPadding=item.style('underlay-padding');readout.dataset.maximumZoomProjectIsParent=String(item.isParent());readout.dataset.maximumZoomProjectModelBounds=`${modelBounds.w.toFixed(3)}x${modelBounds.h.toFixed(3)}`;readout.dataset.maximumZoomProjectBounds=`${bounds.w.toFixed(3)}x${bounds.h.toFixed(3)}`;readout.dataset.maximumZoomProjectPosition=`${position.x.toFixed(3)},${position.y.toFixed(3)}`;}}}
    function zoomAnchorPosition(){
      const center={x:state.cy.width()/2,y:state.cy.height()/2};let item=null;
      if(state.selected?.type==='node')item=state.cy.$id(state.selected.id);
      else if(state.selected?.type==='edge'){const edge=allEdges.find(candidate=>candidate.id===state.selected.id);if(edge)item=state.cy.$id(edge.source);}
      if(!item?.length){const project=allNodes.find(node=>node.category==='project');if(project)item=state.cy.$id(project.id);}
      if(!item?.length)return center;const position=item.renderedPosition();return Number.isFinite(position.x)&&Number.isFinite(position.y)?position:center;
    }
    function highlightedEdgeScreenWidth(zoom,selected){if(zoom>=80)return selected ? .065 : .032;if(zoom>=45)return selected ? .09 : .046;if(zoom>=18)return selected ? .14 : .075;return selected ? .28 : .15;}
    function highlightedEdgeOpacity(zoom,selected){if(zoom>=80)return selected ? .34 : .1;if(zoom>=45)return selected ? .39 : .13;if(zoom>=18)return selected ? .44 : .16;return selected ? .5 : .2;}
    function refreshHighlightedEdgeScale(){if(!state.cy||!state.highlightedEdgeIds.size)return;const actualZoom=Math.max(.1,state.cy.zoom()),logicalZoom=logicalZoomFromActual(actualZoom),readout=document.getElementById('zoomReadout');state.highlightedEdgeIds.forEach(id=>{const selected=state.selected?.type==='edge'&&state.selected.id===id;state.cy.$id(id).style({'width':highlightedEdgeScreenWidth(logicalZoom,selected)/actualZoom,'opacity':highlightedEdgeOpacity(logicalZoom,selected)});});if(state.selected?.type==='edge'){const edge=allEdges.find(candidate=>candidate.id===state.selected.id),item=state.cy.$id(state.selected.id);readout.dataset.selectedEdgeRenderedWidth=parseFloat(item.renderedStyle('width')).toFixed(3);readout.dataset.selectedEdgeRenderedOpacity=parseFloat(item.style('opacity')).toFixed(3);if(edge){const source=state.cy.$id(edge.source),target=state.cy.$id(edge.target),sourceBounds=source.renderedBoundingBox({includeLabels:false,includeOverlays:false,includeUnderlays:false}),targetBounds=target.renderedBoundingBox({includeLabels:false,includeOverlays:false,includeUnderlays:false});readout.dataset.selectedSourceRenderedWidth=parseFloat(source.renderedStyle('width')).toFixed(3);readout.dataset.selectedTargetRenderedWidth=parseFloat(target.renderedStyle('width')).toFixed(3);readout.dataset.selectedSourceRenderedBorder=parseFloat(source.renderedStyle('border-width')).toFixed(3);readout.dataset.selectedTargetRenderedBorder=parseFloat(target.renderedStyle('border-width')).toFixed(3);readout.dataset.selectedSourceRenderedUnderlay=parseFloat(source.renderedStyle('underlay-padding')).toFixed(3);readout.dataset.selectedTargetRenderedUnderlay=parseFloat(target.renderedStyle('underlay-padding')).toFixed(3);readout.dataset.selectedSourceRenderedBounds=`${sourceBounds.w.toFixed(3)}x${sourceBounds.h.toFixed(3)}`;readout.dataset.selectedTargetRenderedBounds=`${targetBounds.w.toFixed(3)}x${targetBounds.h.toFixed(3)}`;}}}
    function updateViewportScale() {
      if(!state.cy)return;
      const actualZoom=state.precisionActualZoomOverride||state.cy.zoom(),zoom=state.precisionZoomOverride||logicalZoomFromActual(actualZoom),deepZoomFloors=[18,24,32,45,60,80,100],deepFloor=zoom>=18?deepZoomFloors.reduce((floor,candidate)=>zoom>=candidate?candidate:floor,18):null,band=zoom<.25?'far':zoom<.52?'overview':zoom<1.05?'structure':zoom<1.8?'detail':zoom<3.5?'close':zoom<7?'deep':zoom<18?'inspect':`precision-${deepFloor}`;
      if(state.viewportScale===band){if(state.materialProfile)state.materialProfile.actualZoom=actualZoom;refreshHighlightedEdgeScale();scheduleMaterialLayer();return;}
      state.viewportScale=band;
      const profiles={far:{scale:7,node:16,code:1.55,file:4.7,namespace:3.1,type:3.8,capsule:11.5,label:8.4,onDemandLabel:8.1,labelWidth:88,border:.52,codeBorder:.2,glow:1.45,edge:.3,codeEdge:.16,semanticEdge:.7},overview:{scale:3,node:17,code:2,file:5.2,namespace:3.5,type:4.3,capsule:14,label:8.8,onDemandLabel:8.2,labelWidth:96,border:.52,codeBorder:.2,glow:1.45,edge:.36,codeEdge:.2,semanticEdge:.78},structure:{scale:1.4,node:18,code:2.8,file:6.2,namespace:4.2,type:5.1,capsule:17,label:9,onDemandLabel:8.4,labelWidth:108,border:.52,codeBorder:.2,glow:1.45,edge:.44,codeEdge:.26,semanticEdge:.88},detail:{scale:.75,node:19,code:4.4,file:7.6,namespace:5.4,type:6.5,capsule:20,label:9.2,onDemandLabel:8.7,labelWidth:118,border:.52,codeBorder:.2,glow:1.45,edge:.5,codeEdge:.32,semanticEdge:.98},close:{scale:.38,node:20,code:7,file:9.4,namespace:7.7,type:8.6,capsule:22,label:9.4,onDemandLabel:9,labelWidth:130,border:.52,codeBorder:.2,glow:1.45,edge:.58,codeEdge:.44,semanticEdge:1.06},deep:{scale:.19,node:21,code:11,file:13.4,namespace:11.8,type:12.6,capsule:24,label:9.6,onDemandLabel:9.3,labelWidth:142,border:.52,codeBorder:.2,glow:1.45,edge:.66,codeEdge:.58,semanticEdge:1.14},inspect:{scale:.085,node:22,code:16,file:19,namespace:17,type:18,capsule:26,label:9.8,onDemandLabel:9.5,labelWidth:154,border:.52,codeBorder:.2,glow:1.45,edge:.72,codeEdge:.7,semanticEdge:1.22}};
      const precisionProfile={scale:deepFloor?18.5/(23*actualZoom):1,node:25,code:23,file:26,namespace:24,type:25,capsule:31,label:13,onDemandLabel:12,labelWidth:162,border:.52,codeBorder:.5,glow:1.45,edge:.88,codeEdge:.88,semanticEdge:1.28};
      const precision=band.startsWith('precision-'),profile=precision?precisionProfile:profiles[band],size=value=>Math.max(.001,Math.round(value*profile.scale*1000)/1000),dynamicStyles=[
        {selector:'node',style:{'width':size(profile.node),'height':size(profile.node),'font-size':size(profile.label),'text-max-width':size(profile.labelWidth),'border-width':size(profile.border),'outline-width':size(profile.border*.48),'outline-offset':size(profile.border*.65),'underlay-padding':size(profile.glow),'text-margin-y':size(5),'text-outline-width':size(1.35)}},
        {selector:'node.show-on-demand-label',style:{'font-size':size(profile.onDemandLabel),'text-max-width':size(profile.labelWidth)}},
        {selector:'node[category = "code"]',style:{'width':size(profile.code),'height':size(profile.code),'border-width':size(profile.codeBorder),'outline-width':0,'outline-opacity':0,'underlay-padding':size(.45)}},
        {selector:'node[category = "code"][kind = "file"]',style:{'width':size(profile.file),'height':size(profile.file),'border-width':size(profile.codeBorder*1.6),'outline-width':size(profile.border*.42),'outline-opacity':.18,'outline-offset':size(profile.border*.55),'underlay-padding':size(1.05)}},
        {selector:'node[category = "code"][kind = "namespace"]',style:{'width':size(profile.namespace),'height':size(profile.namespace)}},
        {selector:'node[category = "code"][kind = "type"]',style:{'width':size(profile.type),'height':size(profile.type)}},
        {selector:'node[category = "code-capsule"]',style:{'width':size(profile.capsule),'height':size(profile.capsule),'border-width':size(profile.border),'underlay-padding':size(1.15)}},
        {selector:'edge',style:{'width':size(profile.edge)}},
        {selector:'edge[category = "code-relation"]',style:{'width':size(profile.codeEdge)}},
        {selector:'edge.detail-edge',style:{'width':size(profile.codeEdge*1.3)}},
        {selector:'edge[category = "capsule-relation"]',style:{'width':size(profile.semanticEdge*.82)}},
        {selector:'edge[category = "mapping-relation"]',style:{'width':size(profile.semanticEdge)}},
        {selector:'edge[category = "delta-relation"]',style:{'width':size(profile.semanticEdge)}},
        {selector:'edge.selection-neighbor',style:{'width':size(profile.semanticEdge)}},
        {selector:'edge.semantic-emphasis',style:{'width':size(profile.semanticEdge)}},
        {selector:'edge.stage-delta',style:{'width':size(profile.semanticEdge*1.12)}},
        {selector:'node[deltaState = "proposed-change"]',style:{'border-width':size(profile.border*1.45),'underlay-padding':size(profile.glow*1.1)}},
        {selector:'node.semantic-emphasis',style:{'border-width':size(profile.border*1.4),'underlay-padding':size(profile.glow*1.15)}},
        {selector:'node.stage-added',style:{'border-width':size(profile.border*1.55),'underlay-padding':size(profile.glow*1.2)}},
        {selector:'node.stage-changed',style:{'border-width':size(profile.border*1.65),'underlay-padding':size(profile.glow*1.2)}},
        {selector:'node.search-match',style:{'border-width':size(profile.border*1.45),'underlay-padding':size(profile.glow*1.15)}},
        {selector:'node:selected',style:{'border-width':size(profile.border*1.25),'underlay-padding':size(profile.glow*1.1)}}
      ];
      state.materialProfile={profile,scale:profile.scale,actualZoom};
      if(precision)dynamicStyles.push({selector:'node',style:{'shape':'ellipse','padding':0,'underlay-opacity':0,'overlay-opacity':0,'overlay-padding':0,'background-fill':'solid','background-color':'#070a11','background-blacken':0,'background-opacity':.02,'border-opacity':0,'outline-width':0,'outline-opacity':0}},{selector:'node[category = "code"]',style:{'shape':'ellipse','background-color':'data(color)','background-blacken':.7,'background-opacity':.04,'border-opacity':0,'outline-width':0,'outline-opacity':0}});
      state.cy.style().fromJson(graphStyle().concat(dynamicStyles)).update();
      if(precision){const readout=document.getElementById('zoomReadout');readout.dataset.precisionNodeCount=String(allNodes.length);readout.dataset.precisionEdgeCount=String(allEdges.length);}
      refreshHighlightedEdgeScale();
      scheduleMaterialLayer();
    }
    function primePrecisionZoom(targetZoom){
      if(!state.cy||targetZoom<18)return;
      const targetActualZoom=actualZoomFromLogical(targetZoom);state.precisionZoomOverride=targetZoom;state.precisionActualZoomOverride=targetActualZoom;state.viewportScale=null;updateViewportScale();state.precisionZoomOverride=null;state.precisionActualZoomOverride=null;
    }
    function zoomGraphTo(level){const target=Math.max(state.cy.minZoom(),Math.min(logicalMaximumZoom,level)),actualTarget=actualZoomFromLogical(target);if(target>=18){state.virtualGeometryAnchorId=precisionAnchorId();primePrecisionZoom(target);}state.desiredLogicalZoom=target;state.desiredActualZoom=actualTarget;state.cy.zoom({level:actualTarget,renderedPosition:zoomAnchorPosition()});applyVirtualGeometry(true);}
    function highlight(){
      if(!state.cy)return;
      const hadHighlightedEdges=state.highlightedEdgeIds.size>0;
      if(state.highlighted){state.cy.$id(state.highlighted).unselect();state.highlightedEdgeIds.forEach(id=>{const edge=state.cy.$id(id);edge.removeClass('selection-neighbor');edge.removeStyle('width opacity');});}
      state.highlightedEdgeIds=new Set();
      state.highlighted=null;
      if(hadHighlightedEdges){state.viewportScale=null;updateViewportScale();}
      if(!state.selected){updateOnDemandLabels();return;}
      const item=state.cy.$id(state.selected.id);if(!item.length)return;
      item.select();const highlightedEdges=state.selected.type==='edge'?item:item.connectedEdges();highlightedEdges.addClass('selection-neighbor');state.highlightedEdgeIds=new Set(highlightedEdges.map(edge=>edge.id()));refreshHighlightedEdgeScale();state.highlighted=state.selected.id;updateOnDemandLabels();
    }
    function renderStageSelection(stage){const panel=document.getElementById('selectionInspector'),diffs=stage.codeDiffs||[];let detailHtml=diffs.map(diff=>`<h3 style="margin-top:12px">${safe(diff.sourceFile)}</h3><pre class="diff">${safe(diff.unifiedDiff)}</pre>`).join('');if(stage.kind==='verifier-result-imported'){const resultId=(stage.nodeIds||[]).find(id=>id.startsWith('verifier-result.'))?.slice('verifier-result.'.length),result=(model.workflow.verifierResults||[]).find(item=>item.id===resultId),pair=(model.workflow.verifierResultIntake?.pairs||[]).find(item=>item.currentResult?.id===resultId),checks=result?.evidence?.payload?.checks||[],artifacts=result?.evidence?.payload?.artifactRefs||[];if(result)detailHtml=`<h3 style="margin-top:12px">Observed external result</h3>${rows([['result',result.result],['attempt',result.attempt],['current',pair?'yes':'superseded'],['observation',result.observationStatus],['acceptance',result.acceptanceStatus],['verifier',result.verifier.kind+' / '+result.verifier.id],['evidence digest',result.evidence.digest],['checks',checks.length],['artifacts',artifacts.length]])}<p>${safe(result.evidence.payload.summary)}</p>`;}panel.className='detail';panel.innerHTML=`<h3>${safe(stage.title)}</h3>${rows([['work item',stage.workItemId],['stage',`${stage.sequence}. ${stage.kind}`],['status',stage.status],['revision persistence',stage.durableRevision?'durable':'legacy derived'],['revision ids',stage.revisionIds.join(', ')||'not available'],['before state',short(stage.beforeProjectStateDigest)||'not available'],['after state',short(stage.afterProjectStateDigest)||'not available'],['revision boundary',stage.revisionKind],['graph additions',stage.addedNodeIds.length+' node(s), '+stage.addedEdgeIds.length+' edge(s)'],['graph changes',stage.changedNodeIds.length+' node(s), '+stage.changedEdgeIds.length+' edge(s)'],['code diffs',diffs.length],['verification records',stage.verificationRecordIds.length],['evidence records',stage.evidenceRecordIds.length],['history records',stage.recordIds.join(', ')||'none']])}<p>${safe(stage.summary)}</p>${detailHtml}`;}
    function renderSelection(){const panel=document.getElementById('selectionInspector');if(!state.selected){if(state.stageFocus){renderStageSelection(state.stageFocus);return;}panel.className='empty';panel.textContent='Select a graph node or relation to inspect its semantic and source provenance.';return;}if(state.selected.type==='node'){const node=nodeById.get(state.selected.id);if(!node)return;const base=[['category',node.category],['kind',node.kind],['identifier',node.id]];let diffHtml='';if(node.category==='code'){const diffs=node.codeDiffs||[];base.push(['source file',node.source.file],['range',`${node.source.location?.lineStart||'file'}:${node.source.location?.columnStart||''} - ${node.source.location?.lineEnd||''}:${node.source.location?.columnEnd||''}`],['source digest',short(node.source.digest)],['confidence',node.provenance.confidence],['delta state',node.deltaState||'unchanged'],['interpretation',node.details.interpretation],['code diff',diffs.length?`${diffs.length} proposed diff(s) below`:'No change proposal recorded']);diffHtml=diffs.map(diff=>`<h3 style="margin-top:12px">${safe(diff.proposalTitle)}</h3><p>${safe(diff.sourceFile)}</p><pre class="diff">${safe(diff.unifiedDiff)}</pre>`).join('');}else if(node.category==='verifier-result'){const checks=node.details.checks||[],artifacts=node.details.artifactRefs||[];base.push(['result',node.details.result],['currency',node.details.current?'current':'superseded'],['attempt',node.details.attempt],['observation',node.details.observationStatus],['acceptance',node.details.acceptanceStatus],['verifier',`${node.details.verifier?.kind||''} / ${node.details.verifier?.id||''} ${node.details.verifier?.version||''}`],['invocation digest',node.details.invocation?.digest||''],['exit code',node.details.exitCode===null?'not executed':node.details.exitCode],['evidence digest',node.details.evidenceDigest],['metrics',JSON.stringify(node.details.metrics||{})]);diffHtml=`<h3 style="margin-top:12px">Evidence summary</h3><p>${safe(node.details.summary||'')}</p><h3 style="margin-top:12px">Checks</h3>${checks.map(check=>`<div class="evidence-result"><strong>${safe(check.result)}</strong> ${safe(check.id)}<br><small>${safe(check.summary)}</small></div>`).join('')||'<div class="empty">No checks recorded.</div>'}<h3 style="margin-top:12px">Artifact identities</h3>${artifacts.map(artifact=>`<div class="evidence-result"><strong>${safe(artifact.kind)}</strong> ${safe(artifact.logicalName)}<br><small>${safe(artifact.digest+' / '+artifact.byteLength+' bytes / '+artifact.availability)}</small></div>`).join('')||'<div class="empty">No artifacts recorded.</div>'}`;}else base.push(...Object.entries(node.details).map(([key,value])=>[key,typeof value==='object'?JSON.stringify(value):value]));panel.className='detail';panel.innerHTML=`<h3>${safe(node.label)}</h3>${rows(base)}${diffHtml}`; }else{const edge=allEdges.find(item=>item.id===state.selected.id);if(!edge)return;panel.className='detail';panel.innerHTML=`<h3>${safe(edge.kind)}</h3>${rows([['category',edge.category],['source',edge.source],['target',edge.target],...Object.entries(edge.details||{}).map(([key,value])=>[key,typeof value==='object'?JSON.stringify(value):value])])}`;}}
    function stagesForWork(workId){return workStages.filter(stage=>stage.workItemId===workId).sort((left,right)=>left.sequence-right.sequence||left.id.localeCompare(right.id));}
    function workMatchesStatus(work,status){if(!status)return true;if(status==='unmapped')return work.mappingStatus==='unmapped';if(status==='mapped')return Boolean(work.mappingStatus&&work.mappingStatus!=='unmapped');if(status==='proposal-ready')return work.status==='proposal-ready';if(status==='verification-observed')return work.status==='verification-observed';if(status==='blocked')return work.status==='blocked';if(status==='reviewed')return /reviewed|accepted|rejected|receipt/.test(String(work.status+' '+work.changeStatus+' '+work.verificationStatus).toLowerCase());return true;}
    function filteredWorkItems(){const query=document.getElementById('workSearch').value.trim().toLowerCase(),status=document.getElementById('workStatusFilter').value;return workItems.filter(work=>workMatchesStatus(work,status)&&(!query||String(work.id+' '+work.title+' '+work.request).toLowerCase().includes(query)));}
    function scheduleWorkHistoryRender(){window.clearTimeout(state.workFilterTimer);state.workFilterTimer=window.setTimeout(renderWorkHistory,100);}
    function renderWorkHistory() {
      const filtered=filteredWorkItems(),workIndex=workItems.findIndex(work=>work.id===state.selectedWorkId),filteredIndex=filtered.findIndex(work=>work.id===state.selectedWorkId),work=workIndex>=0?workItems[workIndex]:null,windowCenter=filteredIndex>=0?filteredIndex:Math.max(0,filtered.length-1),windowStart=Math.max(0,Math.min(Math.max(0,filtered.length-workListRenderLimit),windowCenter-Math.floor(workListRenderLimit/2))),windowed=filtered.slice(windowStart,windowStart+workListRenderLimit);
      state.renderedWorkCardCount=windowed.length;
      document.getElementById('previousWork').disabled=!filtered.length||(filteredIndex===0);
      document.getElementById('nextWork').disabled=!filtered.length||(filteredIndex===filtered.length-1);
      document.getElementById('workPosition').innerHTML=work?`<strong>${workIndex+1} / ${workItems.length} - ${safe(work.title)}</strong><small>${safe(work.id)}${filtered.length!==workItems.length?' / '+filtered.length+' filtered':''}</small>`:'<strong>No recorded work</strong><small>0 / 0</small>';
      document.getElementById('workList').innerHTML=windowed.length?windowed.map(item=>`<button class="work-card ${item.mappingStatus==='unmapped'?'unmapped':''} ${item.id===state.selectedWorkId?'active':''}" data-work="${safe(item.id)}"><span class="state">${safe(item.status)} / ${safe(item.mappingStatus)}</span><strong>${safe(item.title)}</strong><small>${safe(item.request)}</small></button>`).join(''):`<div class="empty">${workItems.length?'No recorded work matches these filters.':'No work request has been recorded. Use the project workspace command to add one.'}</div>`;
      document.getElementById('workWindowSummary').textContent=filtered.length?`Showing ${windowStart+1}-${windowStart+windowed.length} of ${filtered.length}${filtered.length!==workItems.length?' filtered':' recorded'} work items`:(workItems.length?'0 matching work items':'0 recorded work items');
      document.querySelectorAll('[data-work]').forEach(button=>button.addEventListener('click',()=>focusWork(button.dataset.work)));
      renderWorkStages();
    }
    function renderWorkStages() {
      const stages=stagesForWork(state.selectedWorkId),stageIndex=state.stageFocus?stages.findIndex(stage=>stage.id===state.stageFocus.id):-1;
      document.getElementById('previousStage').disabled=!stages.length||(stageIndex===0);
      document.getElementById('nextStage').disabled=!stages.length||(stageIndex===stages.length-1);
      document.getElementById('stagePosition').innerHTML=stages.length?`<strong>${stageIndex>=0?stageIndex+1:'-'} / ${stages.length} - ${safe(stageIndex>=0?stages[stageIndex].title:'Select a stage')}</strong><small>${safe(state.selectedWorkId||'')}</small>`:`<strong>No recorded stages</strong><small>${safe(state.selectedWorkId||'0 / 0')}</small>`;
      document.getElementById('stageList').innerHTML=stages.length?stages.map(stage=>{const delta=`+${stage.addedNodeIds.length} nodes / ${stage.changedNodeIds.length} changed / ${stage.codeDiffs.length} diffs`,revision=stage.durableRevision?`${stage.revisionIds.length} durable revision(s)`:'legacy record-derived';return `<button class="stage-card ${state.stageFocus?.id===stage.id?'active':''}" data-stage="${safe(stage.id)}"><span class="stage-meta"><span>${safe(stage.workItemId)}</span><span>${safe(stage.sequence)} / ${safe(stage.status)}</span></span><strong>${safe(stage.title)}</strong><small class="stage-delta">${safe(delta)}</small><small class="stage-revision ${stage.durableRevision?'durable':''}">${safe(revision)}</small></button>`;}).join(''):'<div class="empty">No recorded work stages are available for this work item.</div>';
      document.querySelectorAll('[data-stage]').forEach(button=>button.addEventListener('click',()=>focusStage(button.dataset.stage)));
    }
    function focusWork(workId){if(!workItems.some(work=>work.id===workId))return;state.selectedWorkId=workId;state.stageFocus=null;state.selected={type:'node',id:`work.${workId}`};state.mode='impact';document.querySelectorAll('[data-mode]').forEach(item=>item.classList.toggle('active',item.dataset.mode==='impact'));renderWorkHistory();renderGraph({fit:true});renderSelection();}
    function focusDelta(nodeId){state.stageFocus=null;state.selected={type:'node',id:nodeId};state.mode='impact';document.querySelectorAll('[data-mode]').forEach(item=>item.classList.toggle('active',item.dataset.mode==='impact'));renderGraph({fit:true});renderSelection();}
    function focusStage(stageId){const stage=workStages.find(item=>item.id===stageId);if(!stage)return;state.selectedWorkId=stage.workItemId;state.selected=null;state.stageFocus=stage;state.mode='focus';document.querySelectorAll('[data-mode]').forEach(item=>item.classList.toggle('active',item.dataset.mode==='focus'));renderWorkHistory();renderGraph({fit:true});renderStageSelection(stage);}
    function moveWork(offset){const filtered=filteredWorkItems();if(!filtered.length)return;const index=filtered.findIndex(work=>work.id===state.selectedWorkId),next=index<0?(offset<0?filtered.length-1:0):Math.max(0,Math.min(filtered.length-1,index+offset));if(filtered[next])focusWork(filtered[next].id);}
    function moveStage(offset){const stages=stagesForWork(state.selectedWorkId);if(!stages.length)return;const index=state.stageFocus?stages.findIndex(stage=>stage.id===state.stageFocus.id):-1;const next=index<0?(offset<0?stages.length-1:0):Math.max(0,Math.min(stages.length-1,index+offset));focusStage(stages[next].id);}
    function staticPanels(){
      document.getElementById('projectBadge').textContent=model.project.id;
      document.getElementById('modeBadge').textContent=liveMode?'live current':'revision snapshot';
      document.getElementById('snapshotBadge').textContent=`snapshot ${short(model.snapshot.sourceDigest)}`;
      const overlay=model.snapshot.semanticRelationOverlay||{},metrics=[['files',model.snapshot.sourceFileCount],['facts',model.snapshot.factCount],['syntax relations',model.snapshot.relationCount],['resolved relations',overlay.resolvedRelationCount||0],['cross-module',overlay.resolvedCrossModuleRelationCount||0],['work items',model.workflow.workItems.length]];
      document.getElementById('metrics').innerHTML=metrics.map(([label,value])=>`<div class="metric"><strong>${Number(value).toLocaleString()}</strong><span>${safe(label)}</span></div>`).join('');
      renderWorkHistory();
      const c=model.changeReview;document.getElementById('changePanel').innerHTML=`<div class="state-line"><strong>${safe(c.status)}</strong><br>${safe(c.summary)}<br><small>${safe(c.reason)}</small></div>`;const deltas=model.workflow.proposalDeltas||[];document.getElementById('deltaList').innerHTML=deltas.length?deltas.map(delta=>`<button class="delta-step" data-delta="${safe(delta.targetNodeId)}">${safe(delta.kind)}: ${safe(delta.label)}</button>`).join(''):'<div class="empty">No graph delta is recorded.</div>';document.querySelectorAll('[data-delta]').forEach(button=>button.addEventListener('click',()=>focusDelta(button.dataset.delta)));
      const receipts=model.workflow.reviewReceipts||[],verifierResults=model.workflow.verifierResults||[],decisions=model.workflow.evidenceDecisions||[],decisionByResult=new Map(decisions.map(item=>[item.verifierResultId,item])),coverage=model.workflow.verifierResultCoverage||[],intake=model.workflow.verifierResultIntake||{pairs:[]},currentResultIds=new Set((intake.pairs||[]).map(pair=>pair.currentResult?.id).filter(Boolean));
      const coverageHtml=coverage.length?coverage.map(item=>`<div class="evidence-result"><strong>${safe(item.observedPairCount+'/'+item.requiredPairCount+' observed')}</strong> ${safe(item.proposalId)}<br><small>${safe(item.passPairCount+' pass / '+item.failPairCount+' fail / '+item.blockedPairCount+' blocked / '+item.missingPairCount+' missing / '+item.acceptedPairCount+' accepted / '+item.rejectedPairCount+' rejected / '+item.pendingPairCount+' pending')}</small></div>`).join(''):'<div class="empty">No proposal verification coverage exists.</div>';
      const resultHtml=verifierResults.length?verifierResults.map(item=>{const current=currentResultIds.has(item.id),decision=decisionByResult.get(item.id),payload=item.evidence?.payload||{},artifactCount=(payload.artifactRefs||[]).length;return `<div class="evidence-result ${current?'current':'superseded'}"><strong>${safe(item.verifier?.kind||'verifier')} ${safe(item.result)}</strong> ${safe(current?'current observed result':'superseded result')}<br><small>${safe(item.id+' / attempt '+item.attempt+' / '+item.observationStatus+' / acceptance '+(decision?.decision||'pending')+' / '+(payload.checks||[]).length+' checks / '+artifactCount+' artifacts')}</small></div>`;}).join(''):'<div class="empty">No external verifier result has been imported.</div>';
      const decisionHtml=decisions.length?decisions.map(item=>`<div class="evidence-result ${item.decision==='accepted'?'current':'superseded'}"><strong>${safe(item.decision)}</strong> ${safe(item.verifierResultId)}<br><small>${safe(item.reviewer.id+' / '+item.reviewer.role+' / '+item.reviewer.permission+' / local workspace only')}</small></div>`).join(''):'<div class="empty">No evidence acceptance decision has been recorded.</div>';
      document.getElementById('evidencePanel').innerHTML=`<div class="state-line">${model.workflow.verification.map(item=>`<strong>${safe(item.result)}</strong> ${safe(item.kind)}`).join('<br>')}<br>${model.workflow.evidence.map(item=>`<strong>${safe(item.result)}</strong> ${safe(item.kind)}`).join('<br>')}<br><strong>Review receipts:</strong> ${receipts.length?receipts.map(item=>safe(item.status)).join(', '):'none recorded'}</div><h3 style="margin-top:12px">Requirement coverage</h3>${coverageHtml}<h3 style="margin-top:12px">External verifier results</h3>${resultHtml}<h3 style="margin-top:12px">Evidence decisions</h3>${decisionHtml}`;
      document.getElementById('authorityPanel').innerHTML=`<div class="state-line"><strong>local human evidence authority</strong><br>Target edits: ${safe(model.authority.targetRepositoryMutation)}<br>Automatic application: ${safe(model.authority.automaticCodeApplication)}<br>Verifier execution by IGD: false<br>Evidence decisions: ${decisions.length}<br>Reviewer authentication by IGD: false<br>Proposal approval: false<br>History records: ${model.workflow.history.length}</div>`;
      document.getElementById('boundaryPanel').innerHTML='<strong>This page is a project-state projection.</strong><br>It can show requests, mappings, review-required proposals, graph/code deltas, external verifier observations, and explicit local human evidence decisions. A decision changes only local workspace readiness for the exact current evidence. It does not authenticate the reviewer or producer, execute verification, approve the proposal, apply graph/code changes, or edit the target repository.';
    }
    function resize(){document.querySelectorAll('.resizer').forEach(handle=>handle.addEventListener('pointerdown',event=>{event.preventDefault();handle.classList.add('active');const side=handle.dataset.side,start=event.clientX,variable=side==='left'?'--left':'--right',initial=parseInt(getComputedStyle(document.documentElement).getPropertyValue(variable));const move=e=>{const delta=e.clientX-start;const next=side==='left'?initial+delta:initial-delta;document.documentElement.style.setProperty(variable,`${Math.max(230,Math.min(560,next))}px`);if(!state.resizeQueued){state.resizeQueued=true;window.requestAnimationFrame(()=>{state.resizeQueued=false;state.cy?.resize();});}};const up=()=>{handle.classList.remove('active');window.removeEventListener('pointermove',move);window.removeEventListener('pointerup',up);state.cy?.resize();};window.addEventListener('pointermove',move);window.addEventListener('pointerup',up);}));}
    function sampledCanvasPixels(canvas){const width=canvas.width||0,height=canvas.height||0;if(!width||!height)return {width,height,sampleCount:0,opaqueSampleCount:0,chromaticSampleCount:0};try{const context=canvas.getContext('2d',{willReadFrequently:true}),pixels=context.getImageData(0,0,width,height).data,step=Math.max(1,Math.floor(Math.sqrt(width*height/14000)));let sampleCount=0,opaqueSampleCount=0,chromaticSampleCount=0;for(let y=0;y<height;y+=step){for(let x=0;x<width;x+=step){const offset=(y*width+x)*4,r=pixels[offset],g=pixels[offset+1],b=pixels[offset+2],a=pixels[offset+3];sampleCount+=1;if(a>8)opaqueSampleCount+=1;if(a>8&&Math.max(r,g,b)-Math.min(r,g,b)>12)chromaticSampleCount+=1;}}return {width,height,sampleCount,opaqueSampleCount,chromaticSampleCount};}catch(error){runtimeProbeErrors.push('canvas sample: '+String(error.message||error));return {width,height,sampleCount:0,opaqueSampleCount:0,chromaticSampleCount:0};}}
    function graphPixelEvidence(){const canvases=[...document.querySelectorAll('#projectGraph canvas')],layers=canvases.map(canvas=>({className:canvas.className||'',...sampledCanvasPixels(canvas)})),material=layers.find(layer=>String(layer.className).includes('node-material-layer'))||null;return {canvasCount:layers.length,totalOpaqueSampleCount:layers.reduce((total,layer)=>total+layer.opaqueSampleCount,0),totalChromaticSampleCount:layers.reduce((total,layer)=>total+layer.chromaticSampleCount,0),materialOpaqueSampleCount:material?.opaqueSampleCount||0,layers};}
    function runtimeProbeState(){const readout=document.getElementById('zoomReadout'),material=document.querySelector('.node-material-layer');return {logicalZoom:Number(readout.textContent.replace('x','')),rendererZoom:Number(readout.dataset.rendererZoom||0),virtualGeometryScale:Number(readout.dataset.virtualGeometryScale||0),effectiveGeometryZoom:Number(readout.dataset.effectiveGeometryZoom||0),selectedEdgeRenderedWidth:Number(readout.dataset.selectedEdgeRenderedWidth||0),selectedEdgeRenderedOpacity:Number(readout.dataset.selectedEdgeRenderedOpacity||0),materialProfile:material?.dataset.material||'',materialDrawCount:Number(material?.dataset.drawCount||0),materialCulledOrdinaryCodeCount:Number(material?.dataset.culledOrdinaryCode||0),materialSpriteCount:Number(material?.dataset.spriteCount||0)};}
    function publishRuntimeProbe(report){let output=document.getElementById('intentgraph-runtime-probe-report');if(!output){output=document.createElement('script');output.id='intentgraph-runtime-probe-report';output.type='application/json';document.body.appendChild(output);}output.textContent=JSON.stringify(report).replace(/</g,'\\u003c');document.documentElement.dataset.intentGraphRuntimeProbeStatus=report.result;document.title='IntentGraph runtime probe '+report.result;}
    async function runRuntimeProbe(){const pause=milliseconds=>new Promise(resolve=>window.setTimeout(resolve,milliseconds)),endpointDistance=edge=>{const source=state.cy.$id(edge.source),target=state.cy.$id(edge.target);if(!source.length||!target.length)return 0;const a=source.position(),b=target.position();return Math.hypot(a.x-b.x,a.y-b.y);};await pause(450);drawMaterialLayer();await pause(80);const selectedEdge=allEdges.find(edge=>edge.category==='semantic-relation')||allEdges[0];if(!selectedEdge)throw new Error('runtime probe requires at least one relation');const overview={state:runtimeProbeState(),pixels:graphPixelEvidence(),selectedEdgeEndpointDistance:endpointDistance(selectedEdge)};state.selected={type:'edge',id:selectedEdge.id};renderSelection();highlight();zoomGraphTo(100);await pause(420);updateViewportScale();updateZoomReadout();refreshHighlightedEdgeScale();drawMaterialLayer();await pause(80);const maximum={state:runtimeProbeState(),pixels:graphPixelEvidence(),selectedEdgeId:selectedEdge.id,selectedEdgeEndpointDistance:endpointDistance(selectedEdge),selectionText:document.getElementById('selectionInspector').innerText};maximum.endpointGeometryScale=overview.selectedEdgeEndpointDistance>0?maximum.selectedEdgeEndpointDistance/overview.selectedEdgeEndpointDistance:0;const checks=[
      {id:'full-node-count-loaded',passed:allNodes.length>0&&state.cy.nodes().length===allNodes.length,actual:state.cy.nodes().length,expected:allNodes.length},
      {id:'full-edge-count-loaded',passed:allEdges.length>0&&state.cy.edges().length===allEdges.length,actual:state.cy.edges().length,expected:allEdges.length},
      {id:'single-graph-instance',passed:state.graphInstanceCount===1,actual:state.graphInstanceCount,expected:1},
      {id:'overview-canvas-nonblank',passed:overview.pixels.canvasCount>0&&overview.pixels.totalOpaqueSampleCount>0,actual:overview.pixels.totalOpaqueSampleCount,expected:'>0'},
      {id:'overview-material-nonblank',passed:overview.pixels.materialOpaqueSampleCount>0,actual:overview.pixels.materialOpaqueSampleCount,expected:'>0'},
      {id:'spectral-titanium-material-active',passed:maximum.state.materialProfile==='cached-spectral-titanium-v2',actual:maximum.state.materialProfile,expected:'cached-spectral-titanium-v2'},
      {id:'material-sprite-cache-bounded',passed:maximum.state.materialSpriteCount>0&&maximum.state.materialSpriteCount<=128,actual:maximum.state.materialSpriteCount,expected:'1..128'},
      {id:'logical-zoom-100',passed:Math.abs(maximum.state.logicalZoom-100)<.001,actual:maximum.state.logicalZoom,expected:100},
      {id:'renderer-zoom-24',passed:Math.abs(maximum.state.rendererZoom-24)<.001,actual:maximum.state.rendererZoom,expected:24},
      {id:'effective-geometry-zoom-100',passed:Math.abs(maximum.state.effectiveGeometryZoom-100)<.001,actual:maximum.state.effectiveGeometryZoom,expected:100},
      {id:'virtual-geometry-scale',passed:Math.abs(maximum.state.virtualGeometryScale-4.1667)<.001,actual:maximum.state.virtualGeometryScale,expected:4.1667},
      {id:'maximum-canvas-nonblank',passed:maximum.pixels.totalOpaqueSampleCount>0,actual:maximum.pixels.totalOpaqueSampleCount,expected:'>0'},
      {id:'maximum-material-nonblank',passed:maximum.pixels.materialOpaqueSampleCount>0,actual:maximum.pixels.materialOpaqueSampleCount,expected:'>0'},
      {id:'actual-endpoint-geometry-scale',passed:overview.selectedEdgeEndpointDistance>0&&Math.abs(maximum.endpointGeometryScale-4.1667)<.01,actual:maximum.endpointGeometryScale,expected:4.1667},
      {id:'selected-edge-screen-width',passed:Math.abs(maximum.state.selectedEdgeRenderedWidth-.065)<.002,actual:maximum.state.selectedEdgeRenderedWidth,expected:.065},
      {id:'selected-edge-opacity',passed:Math.abs(maximum.state.selectedEdgeRenderedOpacity-.34)<.002,actual:maximum.state.selectedEdgeRenderedOpacity,expected:.34},
      {id:'selection-inspector-populated',passed:maximum.selectionText.includes('source')&&maximum.selectionText.includes('target')&&maximum.selectionText.includes(selectedEdge.source)&&maximum.selectionText.includes(selectedEdge.target),actual:maximum.selectionText,expected:'source and target details'},
      {id:'runtime-errors-empty',passed:runtimeProbeErrors.length===0,actual:runtimeProbeErrors.slice(),expected:[]}
    ];publishRuntimeProbe({artifactRole:'intentgraph-workbench-browser-runtime-observation',status:checks.every(check=>check.passed)?'intentgraph-workbench-browser-runtime-pass':'intentgraph-workbench-browser-runtime-fail',scope:'browser-runtime-probe-read-only',result:checks.every(check=>check.passed)?'pass':'fail',graph:{nodeCount:allNodes.length,edgeCount:allEdges.length},overview,maximum,checks,errors:runtimeProbeErrors.slice(),boundary:{queryActivated:true,graphMutation:false,sourceMutation:false,networkRequired:false}});}
    window.intentGraphWorkbench={selectedCodeNode:()=>{if(!state.selected||state.selected.type!=='node')return null;const node=nodeById.get(state.selected.id);return node&&node.category==='code'?node:null;},selectGraphElement:identifier=>{const item=state.cy?.$id(identifier);if(!item?.length)return false;state.selected={type:item.isNode()?'node':'edge',id:identifier};renderSelection();highlight();return true;},workItems:()=>workItems.slice(),filteredWorkItems:()=>filteredWorkItems().slice(),workStages:()=>workStages.slice(),proposalCodeFacts:workId=>{const mapping=(model.workflow.mappings||[]).find(item=>item.workItemId===workId);return mapping?(mapping.codeFactIds||[]).map(identifier=>nodeById.get(identifier)).filter(Boolean).map(node=>({id:node.id,label:node.label,kind:node.kind,source:node.source})):[];},selectedWork:()=>state.selectedWorkId,selectedStage:()=>state.stageFocus?.id||null,selectWork:focusWork,selectStage:focusStage,previousWork:()=>moveWork(-1),nextWork:()=>moveWork(1),previousStage:()=>moveStage(-1),nextStage:()=>moveStage(1),reviewReceiptPairs:()=>{const recorded=new Set((model.workflow.reviewReceipts||[]).map(receipt=>receipt.proposalId+'|'+receipt.verificationRequirementId+'|'+receipt.evidenceRequirementId));return (model.workflow.changeProposals||[]).flatMap(proposal=>(proposal.verificationRequirements||[]).flatMap(verification=>(proposal.evidenceRequirements||[]).map(evidence=>({key:proposal.id+'|'+verification.id+'|'+evidence.id,proposalId:proposal.id,proposalTitle:proposal.title,verificationRequirementId:verification.id,evidenceRequirementId:evidence.id,verificationKind:verification.kind,evidenceKind:evidence.kind})))).filter(pair=>!recorded.has(pair.key));},verifierResultIntake:()=>model.workflow.verifierResultIntake,evidenceDecisionIntake:()=>model.workflow.evidenceDecisionIntake,elementMetrics:identifier=>{const item=state.cy?.$id(identifier);if(!item?.length)return null;return {type:item.isNode()?'node':'edge',width:parseFloat(item.renderedStyle('width')),height:item.isNode()?parseFloat(item.renderedStyle('height')):null,shape:item.isNode()?item.style('shape'):null,backgroundImage:item.isNode()?item.style('background-image'):null,backgroundOpacity:item.isNode()?parseFloat(item.style('background-opacity')):null,underlayOpacity:parseFloat(item.style('underlay-opacity'))};},metrics:()=>({graphInstanceCount:state.graphInstanceCount,visibilityUpdates:state.visibilityUpdates,visibleNodeCount:state.visibleNodeIds?.size||0,visibleEdgeCount:state.visibleEdgeIds?.size||0,totalNodeCount:allNodes.length,totalEdgeCount:allEdges.length,highlightedEdgeCount:state.highlightedEdgeIds.size,selectedEdgeRenderedWidth:state.selected?.type==='edge'?state.cy.$id(state.selected.id).renderedStyle('width'):null,renderedWorkCardCount:state.renderedWorkCardCount,workListRenderLimit,zoom:logicalZoomFromActual(state.cy?.zoom()||0),rendererZoom:state.cy?.zoom()||null,maxZoom:logicalMaximumZoom,rendererMaxZoom:state.cy?.maxZoom()||null,zoomStyleBand:state.viewportScale||null})};
    window.intentGraphRendererMetrics=()=>({logicalZoom:logicalZoomFromActual(state.cy?.zoom()||0),rendererZoom:state.cy?.zoom()||null,virtualGeometryScale:state.virtualGeometryScale,effectiveGeometryZoom:(state.cy?.zoom()||0)*state.virtualGeometryScale,selectedEdgeRenderedWidth:state.selected?.type==='edge'?parseFloat(state.cy.$id(state.selected.id).renderedStyle('width')):null,materialNodesDrawn:state.materialDrawCount,cachedMaterialSprites:state.materialSpriteCache.size,rendererMaximumZoom,logicalMaximumZoom});
    document.getElementById('previousWork').addEventListener('click',()=>moveWork(-1));document.getElementById('nextWork').addEventListener('click',()=>moveWork(1));document.getElementById('previousStage').addEventListener('click',()=>moveStage(-1));document.getElementById('nextStage').addEventListener('click',()=>moveStage(1));document.getElementById('zoomIn').addEventListener('click',()=>zoomGraphTo(logicalZoomFromActual(state.cy.zoom())*1.8));document.getElementById('zoomOut').addEventListener('click',()=>zoomGraphTo(logicalZoomFromActual(state.cy.zoom())/1.8));document.getElementById('zoom100').addEventListener('click',()=>zoomGraphTo(100));document.getElementById('fitGraph').addEventListener('click',()=>{const graph=visibleGraphData(),semanticFocus=state.mode==='overview'&&!filters().search&&!filters().category&&!filters().relation?model.graph.views.overview.nodeIds.map(id=>nodeById.get(id)).filter(Boolean):graph.nodes;fitNodes(semanticFocus);updateZoomReadout();});init();staticPanels();renderGraph({fit:true});updateZoomReadout();renderSelection();resize();window.dispatchEvent(new Event('intentgraph-ready'));if(runtimeProbeRequested)window.setTimeout(()=>runRuntimeProbe().catch(error=>publishRuntimeProbe({artifactRole:'intentgraph-workbench-browser-runtime-observation',status:'intentgraph-workbench-browser-runtime-fail',scope:'browser-runtime-probe-read-only',result:'fail',graph:{nodeCount:allNodes.length,edgeCount:allEdges.length},checks:[],errors:[String(error.message||error),...runtimeProbeErrors],boundary:{queryActivated:true,graphMutation:false,sourceMutation:false,networkRequired:false}})),120);
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
  .draft-proposal-dialog { width:min(940px,calc(100vw - 32px)); } .diff-authoring { display:grid; gap:8px; max-height:34vh; overflow:auto; padding:2px 4px 2px 0; } .diff-entry { border:1px solid #273d4d; background:rgba(6,13,22,.72); padding:10px; display:grid; gap:8px; } .diff-entry.enabled { border-color:#38c7b0; box-shadow:inset 2px 0 #38c7b0; } .diff-entry-head { display:grid; grid-template-columns:auto minmax(0,1fr); gap:9px; align-items:start; color:#d8eaf4; } .diff-entry-head input { margin-top:3px; accent-color:#63efc3; } .diff-entry-meta { display:grid; gap:2px; min-width:0; } .diff-entry-meta strong,.diff-entry-meta small { overflow-wrap:anywhere; } .diff-entry-meta small { color:#8298a9; } .diff-entry textarea { min-height:112px !important; resize:vertical; font:12px/1.45 Consolas,monospace !important; tab-size:2; } .diff-entry textarea:disabled { opacity:.42; cursor:not-allowed; }
  .draft-receipt-trigger { position:fixed; right:18px; bottom:194px; z-index:30; background:#2f2449; border-color:#c0a0ff; color:#f0e7ff; box-shadow:0 0 18px rgba(192,160,255,.12); } .receipt-trigger { position:fixed; right:18px; bottom:238px; z-index:30; background:#35244e; border-color:#c0a0ff; color:#f0e7ff; box-shadow:0 0 18px rgba(192,160,255,.12); } .verifier-trigger { position:fixed; right:18px; bottom:282px; z-index:30; background:#123b3a; border-color:#5fc8b4; color:#dffcf6; box-shadow:0 0 18px rgba(95,200,180,.15); } .evidence-decision-trigger { position:fixed; right:18px; bottom:326px; z-index:30; background:#443414; border-color:#d5b15b; color:#fff2c8; box-shadow:0 0 18px rgba(213,177,91,.15); }
  .verifier-dialog { width:min(900px,calc(100vw - 32px)); } .verifier-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px 14px; } .verifier-grid>div { min-width:0; } .verifier-grid .wide { grid-column:1/-1; } .verifier-grid input,.verifier-grid select,.verifier-grid textarea { box-sizing:border-box; width:100%; } .verifier-grid textarea { min-height:84px; } .verifier-boundary { padding:9px 11px; border:1px solid #315a58; background:#091817; color:#bfe9e1; font-size:11px; line-height:1.5; } .verifier-file-state { min-height:18px; color:#8fdaca; font-size:11px; overflow-wrap:anywhere; }
</style>
<button id="newWorkTrigger" class="new-work-trigger" type="button">New work request</button>
<button id="mapCodeTrigger" class="map-code-trigger" type="button">Map selected code</button>
<button id="draftProposalTrigger" class="draft-proposal-trigger" type="button" disabled>Draft code change</button>
<button id="importProposalTrigger" class="proposal-trigger" type="button" disabled>Import proposal JSON</button>
<button id="draftReceiptTrigger" class="draft-receipt-trigger" type="button" disabled>Record review receipt</button>
<button id="importReceiptTrigger" class="receipt-trigger" type="button" disabled>Import receipt JSON</button>
<button id="importVerifierResultTrigger" class="verifier-trigger" type="button" disabled>Import verification result</button>
<button id="evidenceDecisionTrigger" class="evidence-decision-trigger" type="button" disabled>Review observed evidence</button>
<dialog id="newWorkDialog" class="new-work-dialog"><form id="newWorkForm" class="new-work-form" method="dialog"><h2>Record a work request</h2><p>This records a request in the local IntentGraph project workspace. It does not edit the source project.</p><label for="newWorkId">Stable work id</label><input id="newWorkId" name="workId" required pattern="[a-z][a-z0-9.-]{2,100}" placeholder="example-work-item"><label for="newWorkTitle">Title</label><input id="newWorkTitle" name="title" required maxlength="180" placeholder="Short work title"><label for="newWorkRequest">Request</label><textarea id="newWorkRequest" name="request" required maxlength="12000" placeholder="Describe the desired behavior or change."></textarea><div id="newWorkMessage" class="new-work-message"></div><div class="new-work-actions"><button id="cancelNewWork" type="button">Cancel</button><button type="submit">Record request</button></div></form></dialog>
<dialog id="mapCodeDialog" class="new-work-dialog"><form id="mapCodeForm" class="new-work-form" method="dialog"><h2>Record a code mapping candidate</h2><p>This connects the selected code fact to a local work request as a declared candidate. It does not approve the mapping or edit the source project.</p><label>Selected code fact</label><div id="selectedCodeFact" class="selected-code-fact"></div><label for="mapWorkId">Work request</label><select id="mapWorkId" name="workId" required></select><label for="mapRationale">Why this code is relevant</label><textarea id="mapRationale" name="rationale" required maxlength="12000" placeholder="Describe the relationship between this request and the selected code."></textarea><div id="mapCodeMessage" class="new-work-message"></div><div class="new-work-actions"><button id="cancelMapCode" type="button">Cancel</button><button id="submitMapCode" type="submit">Record mapping candidate</button></div></form></dialog>
<dialog id="draftProposalDialog" class="new-work-dialog draft-proposal-dialog"><form id="draftProposalForm" class="new-work-form" method="dialog"><h2>Draft a code change</h2><p>Attach hunk-only unified diffs to mapped code facts. IGD checks every hunk against the immutable source snapshot, then records a non-applied proposal for graph and code review. Source files are never modified here.</p><label for="draftProposalWorkId">Mapped work request</label><select id="draftProposalWorkId" name="workId" required></select><label for="draftProposalId">Stable proposal id</label><input id="draftProposalId" name="proposalId" required pattern="[a-z][a-z0-9.-]{2,100}" maxlength="101"><label for="draftProposalTitle">Proposal title</label><input id="draftProposalTitle" name="title" required maxlength="180" placeholder="Short code change title"><label for="draftProposalSummary">Change summary</label><textarea id="draftProposalSummary" name="summary" required maxlength="12000" placeholder="Describe the intended behavior and bounded code change."></textarea><label>Mapped code change fragments</label><div id="draftCodeDiffList" class="diff-authoring"></div><label for="draftVerificationKind">Verification kind</label><select id="draftVerificationKind" name="verificationKind" required><option value="local-review">Local review</option><option value="build-required">Build required</option><option value="test-required">Test required</option></select><label for="draftVerificationSummary">Verification requirement</label><textarea id="draftVerificationSummary" name="verificationSummary" required maxlength="12000" placeholder="State what must be verified later."></textarea><label for="draftEvidenceKind">Evidence kind</label><select id="draftEvidenceKind" name="evidenceKind" required><option value="review-note">Review note</option><option value="test-evidence">Test evidence</option><option value="build-evidence">Build evidence</option></select><label for="draftEvidenceSummary">Evidence requirement</label><textarea id="draftEvidenceSummary" name="evidenceSummary" required maxlength="12000" placeholder="State what evidence must be collected later."></textarea><div id="draftProposalMessage" class="new-work-message"></div><div class="new-work-actions"><button id="cancelDraftProposal" type="button">Cancel</button><button id="submitDraftProposal" type="submit">Record code change</button></div></form></dialog>
<dialog id="draftReceiptDialog" class="new-work-dialog"><form id="draftReceiptForm" class="new-work-form" method="dialog"><h2>Record a review receipt</h2><p>Records a human review result for one existing proposal requirement pair. It does not execute the requirement, collect runtime evidence, apply the proposal, approve the proposal, or edit the source project.</p><label for="draftReceiptPair">Proposal requirement pair</label><select id="draftReceiptPair" name="pair" required></select><label for="draftReceiptId">Stable receipt id</label><input id="draftReceiptId" name="receiptId" required pattern="[a-z][a-z0-9.-]{2,100}" maxlength="101"><label for="draftReceiptResult">Review result</label><select id="draftReceiptResult" name="result" required><option value="reviewed-pass">Reviewed pass</option><option value="reviewed-fail">Reviewed fail</option><option value="review-blocked">Review blocked</option></select><label for="draftReceiptSummary">Review summary</label><textarea id="draftReceiptSummary" name="summary" required maxlength="12000" placeholder="State what was reviewed. This is not execution evidence."></textarea><div id="draftReceiptMessage" class="new-work-message"></div><div class="new-work-actions"><button id="cancelDraftReceipt" type="button">Cancel</button><button id="submitDraftReceipt" type="submit">Record receipt</button></div></form></dialog>
<dialog id="importProposalDialog" class="new-work-dialog proposal-dialog"><form id="importProposalForm" class="new-work-form" method="dialog"><h2>Import a review-only change proposal</h2><p>Paste a deterministic proposal document for an existing work request and mapping candidate. The local server validates it before recording any project-state artifact. It does not edit the C# source project, apply a graph delta, or approve the proposal.</p><label for="proposalDocument">Proposal JSON</label><textarea id="proposalDocument" class="proposal-input" name="proposalDocument" required maxlength="100000" spellcheck="false" placeholder="Paste an intentgraph-experimental-csharp-change-proposal document."></textarea><div id="importProposalMessage" class="new-work-message"></div><div class="new-work-actions"><button id="cancelImportProposal" type="button">Cancel</button><button type="submit">Validate and record proposal</button></div></form></dialog>
<dialog id="importReceiptDialog" class="new-work-dialog proposal-dialog"><form id="importReceiptForm" class="new-work-form" method="dialog"><h2>Import a non-executing review receipt</h2><p>Paste one deterministic receipt for a proposal verification/evidence requirement pair. It records what was reviewed as pass, fail, or blocked. It does not run verification, collect runtime evidence, apply a graph delta, approve the proposal, or edit C# source.</p><label for="receiptDocument">Review receipt JSON</label><textarea id="receiptDocument" class="proposal-input" name="receiptDocument" required maxlength="100000" spellcheck="false" placeholder="Paste an intentgraph-experimental-csharp-review-receipt document."></textarea><div id="importReceiptMessage" class="new-work-message"></div><div class="new-work-actions"><button id="cancelImportReceipt" type="button">Cancel</button><button type="submit">Validate and record receipt</button></div></form></dialog>
<dialog id="importVerifierResultDialog" class="new-work-dialog verifier-dialog"><form id="importVerifierResultForm" class="new-work-form" method="dialog"><h2>Import an observed verification result</h2><div class="verifier-boundary">This records what an external tool declared to be a deterministic result for one requirement pair. The selected local file is hashed in this browser and is not uploaded. IntentGraph does not independently prove determinism, run the verifier, authenticate its producer, accept the evidence, apply the proposal, or edit source.</div><div class="verifier-grid"><div class="wide"><label for="verifierPair">Proposal requirement pair</label><select id="verifierPair" required></select></div><div><label for="verifierResultId">Stable result id</label><input id="verifierResultId" required pattern="[a-z][a-z0-9.-]{2,100}" maxlength="101"></div><div><label for="verifierOutcome">Observed outcome</label><select id="verifierOutcome" required><option value="pass">Pass</option><option value="fail">Fail</option><option value="blocked">Blocked</option></select></div><div><label for="verifierKind">Verifier kind</label><select id="verifierKind" required></select></div><div><label for="verifierIdentity">Verifier identity</label><input id="verifierIdentity" required pattern="[a-z][a-z0-9.-]{2,100}" maxlength="101" value="local.verifier"></div><div><label for="verifierVersion">Verifier version</label><input id="verifierVersion" required maxlength="128" value="1.0.0"></div><div><label for="verifierInvocation">Invocation description (hashed, not stored)</label><input id="verifierInvocation" required maxlength="4000" placeholder="dotnet test --no-restore"></div><div class="wide"><label for="verifierSummary">Observed result summary</label><textarea id="verifierSummary" required maxlength="12000" placeholder="State exactly what this external run observed."></textarea></div><div><label for="verifierCheckId">Check id</label><input id="verifierCheckId" required pattern="[a-z][a-z0-9.-]{2,100}" maxlength="101" value="check.primary"></div><div><label for="verifierExitCode">Exit code (blank when blocked)</label><input id="verifierExitCode" type="number" min="0" max="255" value="0"></div><div class="wide"><label for="verifierCheckSummary">Check summary</label><input id="verifierCheckSummary" required maxlength="4000" placeholder="One declared deterministic check represented by this result"></div><div class="wide"><label for="verifierMetrics">Typed metrics JSON</label><textarea id="verifierMetrics" required spellcheck="false"></textarea></div><div><label for="verifierArtifactKind">Evidence artifact kind</label><select id="verifierArtifactKind" required></select></div><div><label for="verifierArtifactMediaType">Artifact media type</label><select id="verifierArtifactMediaType" required><option value="text/plain">text/plain</option><option value="application/json">application/json</option><option value="application/xml">application/xml</option></select></div><div class="wide"><label for="verifierArtifactFile">Local evidence artifact (hashed only)</label><input id="verifierArtifactFile" type="file" required><div id="verifierArtifactState" class="verifier-file-state">No file selected.</div></div></div><div id="importVerifierResultMessage" class="new-work-message"></div><div class="new-work-actions"><button id="cancelImportVerifierResult" type="button">Cancel</button><button id="submitImportVerifierResult" type="submit">Hash and import observation</button></div></form></dialog>
<dialog id="evidenceDecisionDialog" class="new-work-dialog verifier-dialog"><form id="evidenceDecisionForm" class="new-work-form" method="dialog"><h2>Review observed evidence</h2><div class="verifier-boundary">Accept or reject one current observed result for this local workspace. Only a passing result can be accepted. Your reviewer identity and role are explicit local declarations and are not cryptographically authenticated by IntentGraph. This does not approve or apply the proposal.</div><div class="verifier-grid"><div class="wide"><label for="evidenceDecisionResult">Current verifier result</label><select id="evidenceDecisionResult" required></select></div><div><label for="evidenceDecisionId">Stable decision id</label><input id="evidenceDecisionId" required pattern="[a-z][a-z0-9.-]{2,100}" maxlength="101"></div><div><label for="evidenceDecisionOutcome">Decision</label><select id="evidenceDecisionOutcome" required></select></div><div><label for="evidenceReviewerId">Reviewer identity</label><input id="evidenceReviewerId" required pattern="[a-z][a-z0-9.-]{2,100}" maxlength="101" value="local.reviewer"></div><div><label for="evidenceReviewerRole">Reviewer role</label><select id="evidenceReviewerRole" required><option value="maintainer">Maintainer</option><option value="quality-reviewer">Quality reviewer</option><option value="security-reviewer">Security reviewer</option></select></div><div class="wide"><label for="evidenceDecisionSummary">Decision rationale</label><textarea id="evidenceDecisionSummary" required maxlength="12000" placeholder="Explain why this exact evidence is accepted or rejected for local workspace readiness."></textarea></div></div><div id="evidenceDecisionMessage" class="new-work-message"></div><div class="new-work-actions"><button id="cancelEvidenceDecision" type="button">Cancel</button><button id="submitEvidenceDecision" type="submit">Record evidence decision</button></div></form></dialog>
<script>
  (() => { const dialog=document.getElementById('newWorkDialog'), trigger=document.getElementById('newWorkTrigger'), form=document.getElementById('newWorkForm'), workId=document.getElementById('newWorkId'), title=document.getElementById('newWorkTitle'), request=document.getElementById('newWorkRequest'), message=document.getElementById('newWorkMessage'); trigger.addEventListener('click',()=>dialog.showModal()); document.getElementById('cancelNewWork').addEventListener('click',()=>dialog.close()); form.addEventListener('submit',async event=>{event.preventDefault();message.textContent='Recording request...';const body={workId:workId.value.trim(),title:title.value.trim(),request:request.value.trim()};try{const response=await fetch('/api/work-requests',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const result=await response.json();if(!response.ok){throw new Error(result.error||'Request could not be recorded.');}message.textContent='Recorded. Reloading workbench...';window.setTimeout(()=>window.location.reload(),250);}catch(error){message.textContent=error.message||'Request could not be recorded.';}}); })();
</script>
<script>
  (() => {
    let projectStateVersion=null;
    async function loadRevisionHead(){
      const response=await fetch('/api/revision-head',{cache:'no-store'});
      if(!response.ok)throw new Error('revision head request failed');
      return response.json();
    }
    async function checkForProjectUpdate(){
      if(document.visibilityState==='hidden')return;
      try {
        const head=await loadRevisionHead();
        if(projectStateVersion===null){projectStateVersion=head.projectStateVersion;return;}
        if(head.projectStateVersion!==projectStateVersion)window.location.reload();
      } catch (_error) {
        // The next interval retries; a transient local read must not disturb review.
      }
    }
    window.addEventListener('intentgraph-ready',()=>{checkForProjectUpdate();window.setInterval(checkForProjectUpdate,2000);});
  })();
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
    const dialog=document.getElementById('draftProposalDialog'),trigger=document.getElementById('draftProposalTrigger'),form=document.getElementById('draftProposalForm'),workSelect=document.getElementById('draftProposalWorkId'),proposalId=document.getElementById('draftProposalId'),title=document.getElementById('draftProposalTitle'),summary=document.getElementById('draftProposalSummary'),diffList=document.getElementById('draftCodeDiffList'),verificationKind=document.getElementById('draftVerificationKind'),verificationSummary=document.getElementById('draftVerificationSummary'),evidenceKind=document.getElementById('draftEvidenceKind'),evidenceSummary=document.getElementById('draftEvidenceSummary'),message=document.getElementById('draftProposalMessage'),submit=document.getElementById('submitDraftProposal');
    function eligibleWorks(){const workbench=window.intentGraphWorkbench;const works=workbench&&workbench.workItems?workbench.workItems():[];return works.filter(work=>work.mappingStatus==='candidate'&&work.changeStatus==='not-proposed');}
    function updateProposalId(){const workId=workSelect.value;proposalId.value=workId?'proposal-'+workId:'';}
    function renderCodeDiffs(){
      const workbench=window.intentGraphWorkbench,facts=workbench&&workbench.proposalCodeFacts?workbench.proposalCodeFacts(workSelect.value):[];
      diffList.replaceChildren();
      facts.forEach(fact=>{
        const entry=document.createElement('section'),head=document.createElement('label'),toggle=document.createElement('input'),meta=document.createElement('span'),name=document.createElement('strong'),source=document.createElement('small'),textarea=document.createElement('textarea'),location=fact.source?.location||{};
        entry.className='diff-entry';head.className='diff-entry-head';meta.className='diff-entry-meta';toggle.type='checkbox';toggle.dataset.codeFactId=fact.id;name.textContent=fact.label||fact.id;source.textContent=`${fact.source?.file||'unknown source'}:${location.lineStart||'?'}-${location.lineEnd||'?'} / ${fact.kind||'code fact'}`;textarea.disabled=true;textarea.dataset.codeFactId=fact.id;textarea.maxLength=32768;textarea.spellcheck=false;textarea.placeholder=`@@ -${location.lineStart||1},1 +${location.lineStart||1},1 @@\n-existing source line\n+proposed source line`;
        meta.append(name,source);head.append(toggle,meta);entry.append(head,textarea);diffList.append(entry);
        toggle.addEventListener('change',()=>{textarea.disabled=!toggle.checked;entry.classList.toggle('enabled',toggle.checked);if(toggle.checked)textarea.focus();});
      });
      if(!facts.length){const empty=document.createElement('div');empty.className='empty';empty.textContent='This work item has no mapped code facts.';diffList.append(empty);}
      return facts.length;
    }
    function openDialog(){const works=eligibleWorks();workSelect.replaceChildren();works.forEach(work=>workSelect.add(new Option(work.title+' ('+work.id+')',work.id)));updateProposalId();const factCount=renderCodeDiffs(),ready=works.length>0&&factCount>0;message.textContent=ready?'Select at least one mapped fact and provide a snapshot-matching unified diff.':'Record a declared code mapping before drafting a code change.';submit.disabled=!ready;dialog.showModal();}
    trigger.disabled=true;
    window.addEventListener('intentgraph-ready',()=>{trigger.disabled=false;});
    trigger.addEventListener('click',openDialog);
    workSelect.addEventListener('change',()=>{updateProposalId();renderCodeDiffs();});
    verificationKind.addEventListener('change',()=>{const compatible={'local-review':'review-note','build-required':'build-evidence','test-required':'test-evidence'};evidenceKind.value=compatible[verificationKind.value]||evidenceKind.value;});
    document.getElementById('cancelDraftProposal').addEventListener('click',()=>dialog.close());
    form.addEventListener('submit',async event=>{
      event.preventDefault();
      const codeDiffs=[...diffList.querySelectorAll('.diff-entry')].filter(entry=>entry.querySelector('input')?.checked).map(entry=>({codeFactId:entry.querySelector('input').dataset.codeFactId,unifiedDiff:entry.querySelector('textarea').value.trimEnd()}));
      if(!codeDiffs.length){message.textContent='Select at least one mapped code fact and provide its unified diff.';return;}
      if(codeDiffs.some(item=>!item.unifiedDiff.trim())){message.textContent='Every selected code fact needs a unified diff.';return;}
      message.textContent='Checking code diffs against the immutable snapshot...';
      const body={proposalId:proposalId.value.trim(),workId:workSelect.value,title:title.value.trim(),summary:summary.value.trim(),codeDiffs,verificationKind:verificationKind.value,verificationSummary:verificationSummary.value.trim(),evidenceKind:evidenceKind.value,evidenceSummary:evidenceSummary.value.trim()};
      try{
        const response=await fetch('/api/draft-change-proposals',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
        const result=await response.json();
        if(!response.ok)throw new Error(result.error||'Code change could not be recorded.');
        message.textContent=`Recorded ${result.codeDiffCount} checked code diff(s). Reloading workbench...`;
        window.setTimeout(()=>window.location.reload(),250);
      }catch(error){message.textContent=error.message||'Code change could not be recorded.';}
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
</script>
<script>
  (() => {
    const dialog=document.getElementById('importVerifierResultDialog'),trigger=document.getElementById('importVerifierResultTrigger'),form=document.getElementById('importVerifierResultForm'),pairSelect=document.getElementById('verifierPair'),resultId=document.getElementById('verifierResultId'),outcome=document.getElementById('verifierOutcome'),kind=document.getElementById('verifierKind'),identity=document.getElementById('verifierIdentity'),version=document.getElementById('verifierVersion'),invocation=document.getElementById('verifierInvocation'),summary=document.getElementById('verifierSummary'),checkId=document.getElementById('verifierCheckId'),checkSummary=document.getElementById('verifierCheckSummary'),exitCode=document.getElementById('verifierExitCode'),metrics=document.getElementById('verifierMetrics'),artifactKind=document.getElementById('verifierArtifactKind'),mediaType=document.getElementById('verifierArtifactMediaType'),artifactFile=document.getElementById('verifierArtifactFile'),artifactState=document.getElementById('verifierArtifactState'),message=document.getElementById('importVerifierResultMessage'),submit=document.getElementById('submitImportVerifierResult');
    let pairsByKey=new Map();
    const authority={resultImported:true,verificationExecutedByIntentGraph:false,evidenceCollectedByIntentGraph:false,targetRepositoryMutation:false,automaticCodeApplication:false,selfAuthorized:false,approvalRecorded:false,networkRequired:false,credentialAccessAllowed:false};
    function ordered(value){if(Array.isArray(value))return value.map(ordered);if(value&&typeof value==='object'){return Object.fromEntries(Object.keys(value).sort().map(key=>[key,ordered(value[key])]));}return value;}
    function canonicalBytes(value){const ascii=JSON.stringify(ordered(value)).replace(/[^\x00-\x7f]/g,char=>'\\u'+char.charCodeAt(0).toString(16).padStart(4,'0'));return new TextEncoder().encode(ascii+'\n');}
    async function sha256(bytes){const digest=await crypto.subtle.digest('SHA-256',bytes);return 'sha256:'+Array.from(new Uint8Array(digest),byte=>byte.toString(16).padStart(2,'0')).join('');}
    function safeFragment(value,max=74){return String(value).toLowerCase().replace(/[^a-z0-9.-]+/g,'-').replace(/^-+|-+$/g,'').slice(0,max)||'result';}
    function currentPair(){return pairsByKey.get(pairSelect.value);}
    function defaultMetrics(verifierKind){if(verifierKind==='test')return {total:1,passed:1,failed:0,skipped:0};if(verifierKind==='runtime-smoke')return {started:true,observed:true,responsive:true,observationSeconds:1};return {errorCount:0,warningCount:0};}
    function updatePair(){const pair=currentPair();kind.replaceChildren();artifactKind.replaceChildren();if(!pair)return;(pair.allowedVerifierKinds||[]).forEach(value=>kind.add(new Option(value,value)));(pair.requiredArtifactKinds||[]).forEach(value=>artifactKind.add(new Option(value,value)));resultId.value=`${pair.resultIdPrefix}.${pair.nextAttempt}`;metrics.value=JSON.stringify(defaultMetrics(kind.value),null,2);}
    function updateOutcome(){if(outcome.value==='blocked'){exitCode.value='';exitCode.disabled=true;}else{exitCode.disabled=false;exitCode.value=outcome.value==='pass'?'0':'1';}}
    function inferMediaType(file){const name=file.name.toLowerCase();return name.endsWith('.json')?'application/json':name.endsWith('.xml')?'application/xml':'text/plain';}
    async function updateFileState(){const file=artifactFile.files[0];if(!file){artifactState.textContent='No file selected.';return;}mediaType.value=inferMediaType(file);const digest=await sha256(await file.arrayBuffer());artifactState.textContent=`${file.name} / ${file.size} bytes / ${digest} / contents remain local`;}
    function openDialog(){const intake=window.intentGraphWorkbench?.verifierResultIntake?.()||{pairs:[]};pairsByKey=new Map((intake.pairs||[]).map(pair=>[pair.key,pair]));pairSelect.replaceChildren();for(const pair of intake.pairs||[]){pairSelect.add(new Option(`${pair.proposalTitle} - ${pair.verificationRequirement.kind} / ${pair.evidenceRequirement.kind} / attempt ${pair.nextAttempt}`,pair.key));}updatePair();updateOutcome();const ready=pairsByKey.size>0;message.textContent=ready?'Select the external evidence artifact whose bytes produced this observation.':'No proposal has a declared verifier-compatible requirement pair.';submit.disabled=!ready;dialog.showModal();}
    trigger.disabled=true;
    window.addEventListener('intentgraph-ready',()=>{trigger.disabled=false;});
    trigger.addEventListener('click',openDialog);
    pairSelect.addEventListener('change',updatePair);
    kind.addEventListener('change',()=>{metrics.value=JSON.stringify(defaultMetrics(kind.value),null,2);});
    outcome.addEventListener('change',updateOutcome);
    artifactFile.addEventListener('change',()=>{updateFileState().catch(error=>{artifactState.textContent=error.message||'File hashing failed.';});});
    document.getElementById('cancelImportVerifierResult').addEventListener('click',()=>dialog.close());
    form.addEventListener('submit',async event=>{
      event.preventDefault();const pair=currentPair(),file=artifactFile.files[0];if(!pair||!file)return;
      message.textContent='Hashing local evidence and validating observation...';submit.disabled=true;
      try{
        if(file.size<1)throw new Error('Evidence artifact must not be empty.');
        let typedMetrics;try{typedMetrics=JSON.parse(metrics.value);}catch(_error){throw new Error('Typed metrics JSON is not valid.');}
        const observedOutcome=outcome.value,parsedExit=exitCode.value===''?null:Number(exitCode.value),resultIdentifier=resultId.value.trim(),artifactName=(file.name.replace(/[^A-Za-z0-9._-]/g,'_').slice(0,256)||'evidence.txt');
        const artifactDigest=await sha256(await file.arrayBuffer()),invocationDigest=await sha256(canonicalBytes({description:invocation.value.trim()}));
        const payload={summary:summary.value.trim(),exitCode:parsedExit,checks:[{id:checkId.value.trim(),result:observedOutcome,summary:checkSummary.value.trim()}],metrics:typedMetrics,artifactRefs:[{id:`artifact.${safeFragment(resultIdentifier,90)}`,kind:artifactKind.value,logicalName:artifactName,mediaType:mediaType.value,byteLength:file.size,digest:artifactDigest,availability:'external-digest-only'}]};
        const payloadBytes=canonicalBytes(payload),verifierResult={artifactRole:'intentgraph-experimental-csharp-verifier-result',schemaVersion:'0.1.0',scope:'experimental-csharp-semantic-overlay-verifier-result',id:resultIdentifier,proposalId:pair.proposalId,verificationRequirementId:pair.verificationRequirement.id,evidenceRequirementId:pair.evidenceRequirement.id,attempt:pair.nextAttempt,result:observedOutcome,verifier:{id:identity.value.trim(),kind:kind.value,version:version.value.trim(),deterministic:true},invocation:{id:`invocation.${safeFragment(resultIdentifier,88)}`,digest:invocationDigest},subject:{logicalSourceRoot:pair.logicalSourceRoot,snapshotSourceDigest:pair.snapshotSourceDigest,proposalDigest:pair.proposalDigest},evidence:{contentType:'application/vnd.intentgraph.verifier-evidence+json',byteLength:payloadBytes.byteLength,digest:await sha256(payloadBytes),payload},observationStatus:'observed',acceptanceStatus:'pending',supersedesResultId:pair.supersedesResultId,authority};
        const response=await fetch('/api/verifier-results',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({verifierResult})}),recorded=await response.json();if(!response.ok)throw new Error(recorded.error||'Verification result could not be imported.');message.textContent='Observation imported with acceptance still pending. Reloading workbench...';window.setTimeout(()=>window.location.reload(),250);
      }catch(error){message.textContent=error.message||'Verification result could not be imported.';submit.disabled=false;}
    });
  })();
</script>
<script>
  (() => {
    const dialog=document.getElementById('evidenceDecisionDialog'),trigger=document.getElementById('evidenceDecisionTrigger'),form=document.getElementById('evidenceDecisionForm'),resultSelect=document.getElementById('evidenceDecisionResult'),decisionId=document.getElementById('evidenceDecisionId'),outcome=document.getElementById('evidenceDecisionOutcome'),reviewerId=document.getElementById('evidenceReviewerId'),reviewerRole=document.getElementById('evidenceReviewerRole'),summary=document.getElementById('evidenceDecisionSummary'),message=document.getElementById('evidenceDecisionMessage'),submit=document.getElementById('submitEvidenceDecision');
    let resultsById=new Map();
    function currentResult(){return resultsById.get(resultSelect.value);}
    function updateResult(){const item=currentResult();outcome.replaceChildren();if(!item)return;if(item.verifierResult==='pass')outcome.add(new Option('Accept passing evidence','accepted'));outcome.add(new Option('Reject evidence','rejected'));decisionId.value=item.decisionIdPrefix;message.textContent=item.verifierResult==='pass'?'Acceptance can mark this requirement evidence as accepted for local readiness.':'A non-passing result cannot be accepted; reject it and record a later verifier attempt.';}
    function openDialog(){const intake=window.intentGraphWorkbench?.evidenceDecisionIntake?.()||{results:[]};const pending=(intake.results||[]).filter(item=>!item.decisionRecorded);resultsById=new Map(pending.map(item=>[item.verifierResultId,item]));resultSelect.replaceChildren();for(const item of pending){resultSelect.add(new Option(`${item.proposalTitle} - ${item.verifierKind} ${item.verifierResult} - ${item.verifierResultId}`,item.verifierResultId));}updateResult();const ready=pending.length>0;if(!ready)message.textContent='No current observed verifier result is waiting for an evidence decision.';submit.disabled=!ready;dialog.showModal();}
    trigger.disabled=true;
    window.addEventListener('intentgraph-ready',()=>{const intake=window.intentGraphWorkbench?.evidenceDecisionIntake?.()||{results:[]};trigger.disabled=!(intake.results||[]).some(item=>!item.decisionRecorded);});
    trigger.addEventListener('click',openDialog);
    resultSelect.addEventListener('change',updateResult);
    document.getElementById('cancelEvidenceDecision').addEventListener('click',()=>dialog.close());
    form.addEventListener('submit',async event=>{
      event.preventDefault();const item=currentResult();if(!item)return;
      message.textContent='Validating reviewer authority and exact evidence binding...';submit.disabled=true;
      try{
        const body={decisionId:decisionId.value.trim(),verifierResultId:item.verifierResultId,decision:outcome.value,reviewerId:reviewerId.value.trim(),reviewerRole:reviewerRole.value,summary:summary.value.trim()};
        const response=await fetch('/api/draft-evidence-decisions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}),recorded=await response.json();if(!response.ok)throw new Error(recorded.error||'Evidence decision could not be recorded.');message.textContent='Evidence decision recorded for local workspace readiness. Proposal remains unapproved. Reloading...';window.setTimeout(()=>window.location.reload(),250);
      }catch(error){message.textContent=error.message||'Evidence decision could not be recorded.';submit.disabled=false;}
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
    if (
        not isinstance(workflow, dict)
        or not isinstance(workflow.get("reviewReceipts"), list)
        or not isinstance(workflow.get("workStageTimeline"), list)
        or not isinstance(workflow.get("verifierResults"), list)
        or not isinstance(workflow.get("evidenceDecisions"), list)
        or not isinstance(workflow.get("verifierResultCoverage"), list)
        or not isinstance(workflow.get("verifierResultIntake"), dict)
        or not isinstance(workflow.get("evidenceDecisionIntake"), dict)
        or not isinstance(workflow.get("changeProposals"), list)
        or not isinstance(workflow.get("workItems"), list)
    ):
        errors.append("project workbench review receipt state is invalid")
    else:
        required_stage_fields = {"id", "workItemId", "sequence", "kind", "title", "summary", "status", "recordIds", "nodeIds", "addedNodeIds", "changedNodeIds", "contextNodeIds", "edgeIds", "addedEdgeIds", "changedEdgeIds", "codeDiffs", "verificationRecordIds", "evidenceRecordIds", "revisionKind", "revisionIds", "durableRevision", "beforeProjectStateDigest", "afterProjectStateDigest"}
        work_ids = {item["id"] for item in workflow.get("workItems", []) if isinstance(item, dict) and isinstance(item.get("id"), str)}
        stage_ids = set()
        for stage in workflow["workStageTimeline"]:
            if not isinstance(stage, dict) or set(stage) != required_stage_fields or stage["id"] in stage_ids or stage["workItemId"] not in work_ids or not isinstance(stage["sequence"], int) or stage["sequence"] < 1:
                errors.append("project workbench work stage timeline is invalid")
                break
            if stage["durableRevision"] != bool(stage["revisionIds"]) or (stage["durableRevision"] and (not sha256_value(stage["beforeProjectStateDigest"]) or not sha256_value(stage["afterProjectStateDigest"]))):
                errors.append("project workbench durable work stage revision is invalid")
                break
            if stage["kind"] == "verifier-result-imported" and (
                not stage["durableRevision"] or len(stage["revisionIds"]) != 1
            ):
                errors.append("project workbench verifier result stage revision is invalid")
                break
            if stage["kind"] == "evidence-decision-recorded" and (
                not stage["durableRevision"] or len(stage["revisionIds"]) != 1
            ):
                errors.append("project workbench evidence decision stage revision is invalid")
                break
            stage_ids.add(stage["id"])
        try:
            verifier_results = workflow["verifierResults"]
            result_ids = [required_safe_id(item["id"], "projection verifier result id") for item in verifier_results]
            if len(result_ids) != len(set(result_ids)):
                raise ProjectWorkspaceError("projection verifier results must be unique")
            latest_by_pair: dict[tuple[str, str, str], dict[str, Any]] = {}
            for item in verifier_results:
                if not isinstance(item, dict):
                    raise ProjectWorkspaceError("projection verifier result is invalid")
                pair = verifier_result_pair(item)
                latest_by_pair[pair] = item
                if item.get("observationStatus") != "observed" or item.get("acceptanceStatus") != "pending":
                    raise ProjectWorkspaceError("projection verifier result authority state is invalid")
            result_by_id = {item["id"]: item for item in verifier_results}
            evidence_decisions = workflow["evidenceDecisions"]
            decision_ids: set[str] = set()
            decided_result_ids: set[str] = set()
            for decision in evidence_decisions:
                if not isinstance(decision, dict):
                    raise ProjectWorkspaceError("projection evidence decision is invalid")
                validate_evidence_decision_document(decision, result_by_id=result_by_id)
                if decision["id"] in decision_ids or decision["verifierResultId"] in decided_result_ids:
                    raise ProjectWorkspaceError("projection evidence decisions must be unique by id and verifier result")
                decision_ids.add(decision["id"])
                decided_result_ids.add(decision["verifierResultId"])
            decision_by_result = {decision["verifierResultId"]: decision for decision in evidence_decisions}
            intake = workflow["verifierResultIntake"]
            required_intake_fields = {
                "artifactRole", "schemaVersion", "scope", "evidenceContentType",
                "allowedVerifierKinds", "allowedArtifactKinds", "allowedArtifactMediaTypes",
                "artifactAvailability", "pairs", "authority",
            }
            if (
                set(intake) != required_intake_fields
                or intake["artifactRole"] != VERIFIER_RESULT_ROLE
                or intake["schemaVersion"] != PROJECT_SCHEMA_VERSION
                or intake["scope"] != VERIFIER_RESULT_SCOPE
                or intake["evidenceContentType"] != VERIFIER_EVIDENCE_CONTENT_TYPE
                or intake["allowedVerifierKinds"] != sorted(VERIFIER_RESULT_KINDS)
                or intake["allowedArtifactKinds"] != sorted(VERIFIER_ARTIFACT_KINDS)
                or intake["allowedArtifactMediaTypes"] != sorted(VERIFIER_ARTIFACT_MEDIA_TYPES)
                or intake["artifactAvailability"] != VERIFIER_ARTIFACT_AVAILABILITY
                or intake["authority"] != VERIFIER_RESULT_AUTHORITY
                or not isinstance(intake["pairs"], list)
            ):
                raise ProjectWorkspaceError("projection verifier result intake contract is invalid")
            pair_keys: list[str] = []
            for pair in intake["pairs"]:
                required_pair_fields = {
                    "key", "resultIdPrefix", "proposalId", "proposalTitle", "workItemId",
                    "verificationRequirement", "evidenceRequirement",
                    "allowedVerifierKinds", "requiredArtifactKinds", "logicalSourceRoot",
                    "snapshotSourceDigest", "proposalDigest", "nextAttempt",
                    "supersedesResultId", "currentResult",
                }
                if not isinstance(pair, dict) or set(pair) != required_pair_fields:
                    raise ProjectWorkspaceError("projection verifier result intake pair is invalid")
                key = pair["key"]
                tuple_key = (pair["proposalId"], pair["verificationRequirement"]["id"], pair["evidenceRequirement"]["id"])
                latest = latest_by_pair.get(tuple_key)
                if (
                    not isinstance(key, str)
                    or key != "|".join(tuple_key)
                    or pair["resultIdPrefix"] != verifier_result_id_prefix(tuple_key)
                    or pair["allowedVerifierKinds"] != sorted(set(pair["allowedVerifierKinds"]))
                    or not pair["allowedVerifierKinds"]
                    or pair["requiredArtifactKinds"] != sorted(set(pair["requiredArtifactKinds"]))
                    or not pair["requiredArtifactKinds"]
                    or not sha256_value(pair["snapshotSourceDigest"])
                    or not sha256_value(pair["proposalDigest"])
                    or pair["nextAttempt"] != (latest["attempt"] + 1 if latest else 1)
                    or pair["supersedesResultId"] != (latest["id"] if latest else None)
                    or (pair["currentResult"] or {}).get("id") != (latest["id"] if latest else None)
                ):
                    raise ProjectWorkspaceError("projection verifier result intake pair does not match current state")
                pair_keys.append(key)
            if pair_keys != sorted(set(pair_keys)):
                raise ProjectWorkspaceError("projection verifier result intake pairs must be uniquely sorted")
            decision_intake = workflow["evidenceDecisionIntake"]
            required_decision_intake_fields = {
                "artifactRole", "schemaVersion", "scope", "allowedDecisions",
                "allowedReviewerRoles", "decisionPermissions", "results", "authority",
            }
            if (
                set(decision_intake) != required_decision_intake_fields
                or decision_intake["artifactRole"] != EVIDENCE_DECISION_ROLE
                or decision_intake["schemaVersion"] != PROJECT_SCHEMA_VERSION
                or decision_intake["scope"] != EVIDENCE_DECISION_SCOPE
                or decision_intake["allowedDecisions"] != sorted(EVIDENCE_DECISIONS)
                or decision_intake["allowedReviewerRoles"] != sorted(EVIDENCE_REVIEWER_ROLES)
                or decision_intake["decisionPermissions"] != EVIDENCE_DECISION_PERMISSIONS
                or decision_intake["authority"] != EVIDENCE_DECISION_AUTHORITY
                or not isinstance(decision_intake["results"], list)
            ):
                raise ProjectWorkspaceError("projection evidence decision intake contract is invalid")
            expected_current_results = {item["id"]: item for item in latest_by_pair.values()}
            proposal_by_id = {
                item["id"]: item
                for item in workflow.get("changeProposals", [])
                if isinstance(item, dict) and isinstance(item.get("id"), str)
            }
            decision_result_keys: list[str] = []
            for item in decision_intake["results"]:
                required_decision_result_fields = {
                    "key", "decisionIdPrefix", "proposalId", "proposalTitle", "workItemId",
                    "verifierResultId", "verifierResult", "verifierKind", "evidenceDigest",
                    "verificationRequirementId", "evidenceRequirementId", "decisionRecorded",
                    "currentDecision",
                }
                if not isinstance(item, dict) or set(item) != required_decision_result_fields:
                    raise ProjectWorkspaceError("projection evidence decision intake result is invalid")
                result = expected_current_results.get(item["verifierResultId"])
                current_decision = decision_by_result.get(item["verifierResultId"])
                proposal = proposal_by_id.get(item["proposalId"])
                if (
                    result is None
                    or proposal is None
                    or item["key"] != result["id"]
                    or item["decisionIdPrefix"] != evidence_decision_id_prefix(result["id"])
                    or item["proposalId"] != result["proposalId"]
                    or item["proposalTitle"] != proposal.get("title")
                    or item["workItemId"] != proposal.get("workItemId")
                    or item["verifierResult"] != result["result"]
                    or item["verifierKind"] != result["verifier"]["kind"]
                    or item["evidenceDigest"] != result["evidence"]["digest"]
                    or item["verificationRequirementId"] != result["verificationRequirementId"]
                    or item["evidenceRequirementId"] != result["evidenceRequirementId"]
                    or item["decisionRecorded"] != (current_decision is not None)
                    or item["currentDecision"] != current_decision
                ):
                    raise ProjectWorkspaceError("projection evidence decision intake does not match current state")
                decision_result_keys.append(item["key"])
            if decision_result_keys != sorted(expected_current_results) or len(decision_result_keys) != len(set(decision_result_keys)):
                raise ProjectWorkspaceError("projection evidence decision intake results must be complete and uniquely sorted")
            coverage = workflow["verifierResultCoverage"]
            if any(
                not isinstance(item, dict)
                or set(item) != {
                    "proposalId", "workItemId", "requiredPairCount", "observedPairCount",
                    "missingPairCount", "passPairCount", "failPairCount", "blockedPairCount",
                    "allPairsObservedPassing", "acceptedPairCount", "rejectedPairCount",
                    "pendingPairCount", "allPairsAcceptedPassing", "acceptanceStatus",
                }
                or item["acceptanceStatus"] not in {"pending", "partial", "accepted", "rejected"}
                or item["requiredPairCount"] != item["observedPairCount"] + item["missingPairCount"]
                or item["observedPairCount"] != item["passPairCount"] + item["failPairCount"] + item["blockedPairCount"]
                or item["requiredPairCount"] != item["acceptedPairCount"] + item["rejectedPairCount"] + item["pendingPairCount"]
                or item["allPairsAcceptedPassing"] is not (
                    item["allPairsObservedPassing"]
                    and item["acceptedPairCount"] == item["requiredPairCount"]
                )
                or item["acceptanceStatus"] != (
                    "accepted"
                    if item["acceptedPairCount"] == item["requiredPairCount"] and item["requiredPairCount"] > 0
                    else "rejected"
                    if item["rejectedPairCount"] > 0
                    else "partial"
                    if item["acceptedPairCount"] > 0
                    else "pending"
                )
                for item in coverage
            ):
                raise ProjectWorkspaceError("projection verifier result coverage is invalid")
            expected_coverage = verifier_result_coverage_for(
                workflow["changeProposals"],
                verifier_results,
                evidence_decisions,
            )
            if coverage != expected_coverage:
                raise ProjectWorkspaceError(
                    "projection verifier result coverage does not match current results and decisions"
                )
            work_by_id = {
                item["id"]: item
                for item in workflow["workItems"]
                if isinstance(item, dict) and isinstance(item.get("id"), str)
            }
            if len(work_by_id) != len(workflow["workItems"]):
                raise ProjectWorkspaceError("projection work item identifiers are invalid")
            reviewed_proposal_ids = {
                receipt["proposalId"]
                for receipt in workflow["reviewReceipts"]
                if isinstance(receipt, dict) and isinstance(receipt.get("proposalId"), str)
            }
            for proposal in workflow["changeProposals"]:
                if not isinstance(proposal, dict) or proposal.get("workItemId") not in work_by_id:
                    raise ProjectWorkspaceError("projection change proposal work binding is invalid")
                verifier_status, expected_work_status = proposal_verifier_status(
                    proposal,
                    verifier_results,
                    evidence_decisions,
                )
                expected_verification_status = verifier_status or (
                    "review-receipt-recorded"
                    if proposal["id"] in reviewed_proposal_ids
                    else "requirements-recorded"
                )
                work = work_by_id[proposal["workItemId"]]
                if (
                    work.get("changeStatus") != "proposal-review-required"
                    or work.get("verificationStatus") != expected_verification_status
                    or work.get("status") != expected_work_status
                ):
                    raise ProjectWorkspaceError(
                        "projection work readiness does not match current results and decisions"
                    )
        except (KeyError, TypeError, ProjectWorkspaceError):
            errors.append("project workbench verifier result projection contract is invalid")
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
        if not isinstance(node, dict) or node.get("category") not in {"code", "code-capsule", "project", "source-document", "goal", "capability", "constraint", "verification-requirement", "work", "intent", "mapping", "proposal", "verification", "evidence", "review-receipt", "verifier-result", "evidence-decision", "authority", "history"}:
            errors.append("project workbench graph contains an unknown node category")
            continue
        if node["category"] == "code":
            source = node.get("source")
            if node.get("kind") not in ALLOWED_FACT_KINDS or not isinstance(source, dict) or not safe_relative_source(source.get("file")):
                errors.append(f"code node {node.get('id')} provenance is invalid")
    if isinstance(workflow, dict) and isinstance(workflow.get("verifierResults"), list):
        current_result_ids = {
            pair.get("currentResult", {}).get("id")
            for pair in workflow.get("verifierResultIntake", {}).get("pairs", [])
            if isinstance(pair, dict) and isinstance(pair.get("currentResult"), dict)
        }
        result_nodes = {
            str(node.get("id", "")).removeprefix("verifier-result."): node
            for node in nodes
            if isinstance(node, dict) and node.get("category") == "verifier-result"
        }
        expected_result_ids = {item.get("id") for item in workflow["verifierResults"] if isinstance(item, dict)}
        if set(result_nodes) != expected_result_ids or any(
            bool(node.get("details", {}).get("current")) != (identifier in current_result_ids)
            or node.get("details", {}).get("observationAcceptanceStatus") != "pending"
            or node.get("details", {}).get("acceptanceStatus") != (
                next((item["decision"] for item in workflow.get("evidenceDecisions", []) if item.get("verifierResultId") == identifier), "pending")
            )
            for identifier, node in result_nodes.items()
        ):
            errors.append("project workbench verifier result graph nodes are invalid")
    if isinstance(workflow, dict) and isinstance(workflow.get("evidenceDecisions"), list):
        decision_nodes = {
            str(node.get("id", "")).removeprefix("evidence-decision."): node
            for node in nodes
            if isinstance(node, dict) and node.get("category") == "evidence-decision"
        }
        expected_decision_ids = {item.get("id") for item in workflow["evidenceDecisions"] if isinstance(item, dict)}
        authority_nodes = {
            str(node.get("id", "")).removeprefix("authority.evidence-decision."): node
            for node in nodes
            if isinstance(node, dict) and str(node.get("id", "")).startswith("authority.evidence-decision.")
        }
        edge_by_id = {edge.get("id"): edge for edge in edges if isinstance(edge, dict)}
        if set(decision_nodes) != expected_decision_ids or set(authority_nodes) != expected_decision_ids:
            errors.append("project workbench evidence decision graph nodes are invalid")
        else:
            for decision in workflow["evidenceDecisions"]:
                identifier = decision["id"]
                authority_node = authority_nodes[identifier]
                authority_details = authority_node.get("details", {})
                expected_edges = evidence_decision_projection_edges(decision)
                if (
                    decision_nodes[identifier].get("details", {}).get("decision") != decision["decision"]
                    or authority_details.get("proposerType") != "human"
                    or authority_details.get("decidedByType") != "human"
                    or authority_details.get("decisionStatus") != decision["decision"]
                    or authority_details.get("proposalApprovalRecorded") is not False
                    or authority_details.get("graphMutationApplied") is not False
                    or any(edge_by_id.get(edge["id"]) != edge for edge in expected_edges)
                ):
                    errors.append("project workbench evidence decision authority graph is invalid")
                    break
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
    if not isinstance(ui_contract, dict) or any(ui_contract.get(key) is not True for key in ("fullGraphDefault", "allNodesLoaded", "allEdgesLoaded", "progressiveDetail", "viewportScaleCompensation", "relationAwareCommunityLayout", "zoomStyleBuckets", "spectralObsidianNodeMaterial", "iridescentVoidNodeMaterial", "spectralTitaniumNodeMaterial", "browserRuntimeProbe", "headlessBrowserRegression", "canvasPixelEvidence", "rendererSafeOpticalMaterial", "cachedCanvasNodeMaterial", "viewportLocalMaterialRendering", "farZoomMaterialCulling", "virtualPrecisionZoom", "selectedEdgeScreenSpaceTaper", "precisionDeepZoomBands", "supportingNodeLabelsOnDemand", "workStageTimeline", "durableWorkStageRevisions", "allRecordedWorkItemsNavigable", "workHistorySearch", "workHistoryStatusFilter", "boundedWorkHistoryRendering", "previousNextWorkNavigation", "previousNextStageNavigation", "liveProjectionRefreshAfterMutation", "staticRevisionSnapshotImmutable", "loopbackProjectStateMutationFromUi", "loopbackReviewProposalIntakeFromUi", "loopbackGuidedReviewProposalFromUi", "loopbackReviewReceiptIntakeFromUi", "loopbackGuidedReviewReceiptFromUi", "loopbackVerifierResultIntakeFromUi", "loopbackEvidenceDecisionFromUi", "clientSideEvidenceArtifactHashing", "externalEvidenceAcceptanceByWorkbench")) or ui_contract.get("maximumZoom") != 100 or ui_contract.get("rendererMaximumZoom") != 24 or ui_contract.get("effectiveGeometryMaximumZoom") != 100 or ui_contract.get("virtualGeometryScaleAtMaximumZoom") != 4.1667 or ui_contract.get("selectedEdgeRenderedWidthPixelsAtMaximumZoom") != 0.065 or ui_contract.get("selectedEdgeRenderedOpacityAtMaximumZoom") != 0.34 or ui_contract.get("evidenceAcceptanceAuthorityScope") != "local-project-workspace" or any(ui_contract.get(key) is not False for key in ("staticGraphMutationFromUi", "targetRepositoryMutationFromUi", "physicsLayoutOnLoad", "externalVerifierExecutionByWorkbench", "reviewerAuthenticationByWorkbench")):
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
    for marker in ["id=\"projectGraph\"", "id=\"modeBadge\"", "id=\"workList\"", "id=\"previousWork\"", "id=\"nextWork\"", "id=\"workPosition\"", "id=\"stageList\"", "id=\"previousStage\"", "id=\"nextStage\"", "id=\"stagePosition\"", "id=\"selectionInspector\"", "id=\"changePanel\"", "id=\"deltaList\"", "id=\"evidencePanel\"", "id=\"authorityPanel\"", "id=\"zoomIn\"", "id=\"zoomOut\"", "id=\"zoom100\"", "id=\"zoomReadout\"", "maxZoom:rendererMaximumZoom", "logicalZoomFromActual", "applyVirtualGeometry", "effectiveGeometryZoom", "selectedEdgeRenderedOpacity", "culledOrdinaryCode", "node-material-layer", "materialSprite", "cached-spectral-titanium-v2", "intentGraphRuntimeProbe", "intentgraph-runtime-probe-report", "graphPixelEvidence", "deepZoomFloors", "precision-", "spectralObsidianOpticalMaterial", "edge:selected", "assets/cytoscape.min.js"]:
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
    verifier_result = sub.add_parser("add-verifier-result")
    verifier_result.add_argument("--workspace", required=True, type=Path)
    verifier_result.add_argument("--result", required=True, type=Path)
    evidence_decision = sub.add_parser("add-evidence-decision")
    evidence_decision.add_argument("--workspace", required=True, type=Path)
    evidence_decision.add_argument("--decision", required=True, type=Path)
    draft_evidence_decision = sub.add_parser("draft-evidence-decision")
    draft_evidence_decision.add_argument("--workspace", required=True, type=Path)
    draft_evidence_decision.add_argument("--decision-id", required=True)
    draft_evidence_decision.add_argument("--verifier-result-id", required=True)
    draft_evidence_decision.add_argument("--decision", required=True, choices=sorted(EVIDENCE_DECISIONS))
    draft_evidence_decision.add_argument("--reviewer-id", required=True)
    draft_evidence_decision.add_argument("--reviewer-role", required=True, choices=sorted(EVIDENCE_REVIEWER_ROLES))
    draft_evidence_decision.add_argument("--summary", required=True)
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
        elif args.command == "add-verifier-result":
            result = add_verifier_result(args.workspace, args.result)
        elif args.command == "add-evidence-decision":
            result = add_evidence_decision(args.workspace, args.decision)
        elif args.command == "draft-evidence-decision":
            result = draft_evidence_decision_from_result(
                args.workspace,
                decision_id=args.decision_id,
                verifier_result_id=args.verifier_result_id,
                decision=args.decision,
                reviewer_id=args.reviewer_id,
                reviewer_role=args.reviewer_role,
                summary=args.summary,
            )
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
