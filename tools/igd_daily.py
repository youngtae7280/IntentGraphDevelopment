"""Daily-use local launcher for the IntentGraph C# review Workbench.

The launcher snapshots source into an IntentGraph-owned workspace. It never writes to
the target repository and it refuses to resume when that target no longer matches the
recorded snapshot.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import socket
import sys
import tempfile
import threading
import time
import urllib.request
import webbrowser
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from typing import Any

from emit_experimental_csharp_fact_workbench import CYTOSCAPE_LICENSE_SOURCE, CYTOSCAPE_SOURCE
from experimental_csharp_project import PROJECT_FILE, initialize_project, validate_project_workspace
from experimental_csharp_workspace import (
    PROFILE_PATH,
    csharp_source_records,
    initialize_workspace,
    is_reparse_point,
    records_digest,
)
from preflight_csharp_host_sdk_profile import preflight_profile
from serve_experimental_csharp_project_workbench import make_server
from igd_refresh_model import recompute_plan_fields


PRODUCT_VERSION = "0.1.0-preview"
LAUNCH_FILE = "intentgraph.launch.json"
LAUNCH_ROLE = "intentgraph-local-project-launch-record"
LAUNCH_SCOPE = "local-csharp-review-workbench-daily-launch"
REVISION_LAUNCH_SCHEMA = "0.2.0"
SAFE_FRAGMENT = re.compile(r"[^a-z0-9]+")
LAUNCH_AUTHORITY = {
    "externalSourceReadForSnapshot": True,
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
}
REFRESH_PLAN_AUTHORITY = {
    "externalSourceReadForSnapshot": True,
    "localCandidateWorkspaceCreated": True,
    "activeRevisionMutation": False,
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
}
REFRESH_ACCEPT_AUTHORITY = {
    **REFRESH_PLAN_AUTHORITY,
    "activeRevisionMutation": True,
    "explicitPlanAcceptanceRequired": True,
}
REFRESH_PLAN_ROLE = "intentgraph-local-source-refresh-plan"
REFRESH_PLAN_STATUS = "intentgraph-local-source-refresh-review-required"
REFRESH_PLAN_SCOPE = "p9.35-reviewed-csharp-source-refresh"
REFRESH_PLAN_SCHEMA = "0.1.0"
REFRESH_RECEIPT_ROLE = "intentgraph-local-source-refresh-receipt"
REFRESH_RECEIPT_STATUS = "intentgraph-local-source-refresh-accepted"
ACCEPTED_REFRESH_PLAN_FILE = "accepted-refresh-plan.json"


class DailyLaunchError(ValueError):
    """Raised when a daily-use launch would violate provenance or containment."""


def digest_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True).encode("utf-8") + b"\n")


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DailyLaunchError(f"invalid local launch record: {path}") from error
    if not isinstance(value, dict):
        raise DailyLaunchError("local launch record must be a JSON object")
    return value


def validate_refresh_plan_record(plan: dict[str, Any]) -> dict[str, Any]:
    expected = {
        "artifactRole", "schemaVersion", "scope", "status", "result", "id",
        "projectKey", "projectTitle", "fromRevision", "toRevision", "sourceDelta",
        "codeFactDelta", "relationDelta", "invalidation", "preservation",
        "activeWorkspaceDigest", "candidateWorkspace", "candidateWorkspaceDigest",
        "sourcePathPersisted", "authority",
    }
    if (
        not isinstance(plan, dict)
        or set(plan) != expected
        or plan["artifactRole"] != REFRESH_PLAN_ROLE
        or plan["schemaVersion"] != REFRESH_PLAN_SCHEMA
        or plan["scope"] != REFRESH_PLAN_SCOPE
        or plan["status"] != REFRESH_PLAN_STATUS
        or plan["result"] != "review-required"
    ):
        raise DailyLaunchError("pending refresh plan role, schema, scope, or status is invalid")
    if plan["authority"] != REFRESH_PLAN_AUTHORITY or plan["sourcePathPersisted"] is not False:
        raise DailyLaunchError("pending refresh plan authority is invalid")
    for key in ("fromRevision", "toRevision"):
        revision = plan[key]
        if (
            not isinstance(revision, dict)
            or set(revision) != {"id", "sequence", "sourceDigest"}
            or not isinstance(revision["sequence"], int)
            or revision["sequence"] < 1
            or revision["id"] != f"revision.r{revision['sequence']:04d}"
            or not isinstance(revision["sourceDigest"], str)
            or re.fullmatch(r"sha256:[0-9a-f]{64}", revision["sourceDigest"]) is None
        ):
            raise DailyLaunchError("pending refresh plan revision record is invalid")
    if plan["toRevision"]["sequence"] != plan["fromRevision"]["sequence"] + 1:
        raise DailyLaunchError("pending refresh plan revision transition is invalid")
    expected_id = (
        f"refresh.{plan['fromRevision']['sequence']:04d}."
        f"{plan['toRevision']['sourceDigest'].removeprefix('sha256:')[:12]}"
    )
    if plan["id"] != expected_id:
        raise DailyLaunchError("pending refresh plan id is invalid")
    if plan["candidateWorkspace"] != "refresh/pending/workspace":
        raise DailyLaunchError("pending refresh candidate path is invalid")
    for key in ("activeWorkspaceDigest", "candidateWorkspaceDigest"):
        if not isinstance(plan[key], str) or re.fullmatch(r"sha256:[0-9a-f]{64}", plan[key]) is None:
            raise DailyLaunchError("pending refresh workspace digest is invalid")
    if not isinstance(plan["projectKey"], str) or not plan["projectKey"]:
        raise DailyLaunchError("pending refresh project identity is invalid")
    if not isinstance(plan["projectTitle"], str) or not plan["projectTitle"].strip():
        raise DailyLaunchError("pending refresh project identity is invalid")
    return plan


def workspace_tree_digest(root: Path) -> str:
    if not root.is_dir() or is_reparse_point(root):
        raise DailyLaunchError("local workspace tree root must be an existing non-reparse directory")
    records: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        if is_reparse_point(path):
            raise DailyLaunchError("local workspace trees must not contain reparse points")
        if path.is_file():
            records.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "byteLength": path.stat().st_size,
                    "sha256": digest_bytes(path.read_bytes()),
                }
            )
    return digest_bytes(canonical_json(records))


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def lexical_absolute(path: Path) -> Path:
    return Path(os.path.abspath(os.fspath(path.expanduser())))


def first_reparse_component(path: Path) -> Path | None:
    for candidate in (path, *path.parents):
        try:
            if candidate.exists() and is_reparse_point(candidate):
                return candidate
        except OSError:
            return candidate
    return None


def default_home() -> Path:
    override = os.environ.get("INTENTGRAPH_HOME")
    if override:
        return Path(override).expanduser()
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "IntentGraph"
    return Path.home() / ".intentgraph"


def source_identity(source_root: Path) -> tuple[str, str]:
    resolved = source_root.resolve()
    normalized = os.path.normcase(str(resolved)).replace("\\", "/")
    digest = digest_bytes(normalized.encode("utf-8"))
    base = SAFE_FRAGMENT.sub("-", resolved.name.casefold()).strip("-") or "project"
    return digest, f"{base[:36]}-{digest.removeprefix('sha256:')[:12]}"


def project_paths(source_root: Path, home: Path | None = None) -> dict[str, Path]:
    home = lexical_absolute(home or default_home())
    source_digest, key = source_identity(source_root)
    root = home / "p" / source_digest.removeprefix("sha256:")[:12]
    return {
        "home": home,
        "root": root,
        "workspace": root / "workspace",
        "launch": root / LAUNCH_FILE,
    }


def safe_project_id(key: str) -> str:
    fragment = SAFE_FRAGMENT.sub(".", key.casefold()).strip(".")
    return f"project.{fragment}"[:100].rstrip(".")


def validate_roots(source_root: Path, home: Path) -> Path:
    source_root = source_root.expanduser()
    try:
        invalid_source_root = not source_root.is_dir() or is_reparse_point(source_root)
    except OSError:
        invalid_source_root = True
    if invalid_source_root:
        raise DailyLaunchError("source root must be an existing non-symlink directory")
    source_root = source_root.resolve(strict=True)
    home_reparse = first_reparse_component(home)
    if home_reparse is not None:
        raise DailyLaunchError("IntentGraph home must not contain reparse points")
    if home.exists() and not home.is_dir():
        raise DailyLaunchError("IntentGraph home must be a directory")
    if is_within(home, source_root) or is_within(source_root, home):
        raise DailyLaunchError("IntentGraph home and source root must not overlap")
    return source_root


def validate_project_path_boundary(paths: dict[str, Path]) -> None:
    home = lexical_absolute(paths["home"])
    for name in ("root", "workspace", "launch"):
        path = lexical_absolute(paths[name])
        try:
            path.relative_to(home)
        except ValueError as error:
            raise DailyLaunchError("local project paths must remain inside IntentGraph home") from error
        reparse = first_reparse_component(path)
        if reparse is not None:
            raise DailyLaunchError("IntentGraph project paths must not contain reparse points")


def launch_record(source_root: Path, workspace: Path, title: str, source_digest: str) -> dict[str, Any]:
    identity_digest, key = source_identity(source_root)
    return {
        "artifactRole": LAUNCH_ROLE,
        "schemaVersion": "0.1.0",
        "scope": LAUNCH_SCOPE,
        "productVersion": PRODUCT_VERSION,
        "projectKey": key,
        "projectTitle": title,
        "sourceIdentityDigest": identity_digest,
        "sourceDigest": source_digest,
        "workspace": workspace.relative_to(workspace.parent.parent).as_posix(),
        "sourcePathPersisted": False,
        "authority": LAUNCH_AUTHORITY,
    }


def revision_launch_record(
    source_root: Path,
    title: str,
    active_revision: dict[str, Any],
    archived_revisions: list[dict[str, Any]],
) -> dict[str, Any]:
    identity_digest, key = source_identity(source_root)
    return {
        "artifactRole": LAUNCH_ROLE,
        "schemaVersion": REVISION_LAUNCH_SCHEMA,
        "scope": LAUNCH_SCOPE,
        "productVersion": PRODUCT_VERSION,
        "projectKey": key,
        "projectTitle": title,
        "sourceIdentityDigest": identity_digest,
        "sourceDigest": active_revision["sourceDigest"],
        "activeRevision": active_revision,
        "archivedRevisions": archived_revisions,
        "sourcePathPersisted": False,
        "authority": LAUNCH_AUTHORITY,
    }


def _revision_workspace(project_root: Path, relative: str) -> Path:
    parsed = PurePosixPath(relative)
    if parsed.is_absolute() or not parsed.parts or any(part in {"", ".", ".."} for part in parsed.parts):
        raise DailyLaunchError("local revision workspace path is invalid")
    workspace = lexical_absolute(project_root.joinpath(*parsed.parts))
    try:
        workspace.relative_to(lexical_absolute(project_root))
    except ValueError as error:
        raise DailyLaunchError("local revision workspace must remain inside the project root") from error
    if first_reparse_component(workspace) is not None:
        raise DailyLaunchError("local revision workspace must not contain reparse points")
    if not workspace.is_dir():
        raise DailyLaunchError("local active revision workspace is missing")
    return workspace


def _revision_summary(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": record["id"],
        "sequence": record["sequence"],
        "sourceDigest": record["sourceDigest"],
    }


def _validate_revision_record(
    record: Any,
    sequence: int,
    project_root: Path,
    previous_revision: dict[str, Any] | None,
    project_key: str,
    project_title: str,
) -> tuple[dict[str, Any], Path]:
    expected = {
        "id", "sequence", "sourceDigest", "workspace", "workspaceDigest",
        "activatedByPlanId", "activatedByPlanDigest",
    }
    if not isinstance(record, dict) or set(record) != expected:
        raise DailyLaunchError("local revision record is invalid")
    if record["sequence"] != sequence or record["id"] != f"revision.r{sequence:04d}":
        raise DailyLaunchError("local revision sequence is invalid")
    for key in ("sourceDigest", "workspaceDigest"):
        if not isinstance(record[key], str) or re.fullmatch(r"sha256:[0-9a-f]{64}", record[key]) is None:
            raise DailyLaunchError("local revision digest is invalid")
    for key in ("activatedByPlanId", "activatedByPlanDigest"):
        value = record[key]
        if value is not None and (not isinstance(value, str) or not value):
            raise DailyLaunchError("local revision activation provenance is invalid")
    if (record["activatedByPlanId"] is None) != (record["activatedByPlanDigest"] is None):
        raise DailyLaunchError("local revision activation provenance is incomplete")
    if sequence == 1 and record["activatedByPlanId"] is not None:
        raise DailyLaunchError("initial local revision must not claim refresh activation provenance")
    if sequence > 1 and record["activatedByPlanId"] is None:
        raise DailyLaunchError("refreshed local revision is missing activation provenance")
    if record["activatedByPlanDigest"] is not None and re.fullmatch(r"sha256:[0-9a-f]{64}", record["activatedByPlanDigest"]) is None:
        raise DailyLaunchError("local revision activation plan digest is invalid")
    if not isinstance(record["workspace"], str):
        raise DailyLaunchError("local revision workspace path is invalid")
    workspace = _revision_workspace(project_root, record["workspace"])
    if workspace_tree_digest(workspace) != record["workspaceDigest"]:
        raise DailyLaunchError("local revision workspace digest does not match launch provenance")
    state, _, _, _ = validate_project_workspace(workspace)
    if state["project"]["sourceDigest"] != record["sourceDigest"]:
        raise DailyLaunchError("local revision source digest does not match workspace provenance")
    if record["activatedByPlanId"] is not None:
        receipt_path = workspace.parent / "refresh-receipt.json"
        accepted_plan_path = workspace.parent / ACCEPTED_REFRESH_PLAN_FILE
        if first_reparse_component(receipt_path) is not None or first_reparse_component(accepted_plan_path) is not None:
            raise DailyLaunchError("local revision activation provenance must not contain reparse points")
        if not receipt_path.is_file() or not accepted_plan_path.is_file():
            raise DailyLaunchError("local revision activation receipt is missing")
        receipt = read_json(receipt_path)
        accepted_plan = validate_refresh_plan_record(read_json(accepted_plan_path))
        plan_digest = digest_bytes(canonical_json(accepted_plan))
        expected_receipt_keys = {
            "artifactRole", "schemaVersion", "scope", "status", "result", "planId",
            "planDigest", "fromRevision", "toRevision", "priorWorkspace",
            "activeWorkspace", "sourcePathPersisted", "authority",
        }
        if previous_revision is None:
            raise DailyLaunchError("local revision activation predecessor is missing")
        expected_receipt = {
            "artifactRole": REFRESH_RECEIPT_ROLE,
            "schemaVersion": REFRESH_PLAN_SCHEMA,
            "scope": REFRESH_PLAN_SCOPE,
            "status": REFRESH_RECEIPT_STATUS,
            "result": "pass",
            "planId": accepted_plan["id"],
            "planDigest": plan_digest,
            "fromRevision": _revision_summary(previous_revision),
            "toRevision": _revision_summary(record),
            "priorWorkspace": previous_revision["workspace"],
            "activeWorkspace": record["workspace"],
            "sourcePathPersisted": False,
            "authority": REFRESH_ACCEPT_AUTHORITY,
        }
        if set(receipt) != expected_receipt_keys or receipt != expected_receipt:
            raise DailyLaunchError("local revision activation receipt does not match launch provenance")
        if (
            accepted_plan["projectKey"] != project_key
            or accepted_plan["projectTitle"] != project_title
            or accepted_plan["fromRevision"] != _revision_summary(previous_revision)
            or accepted_plan["toRevision"] != _revision_summary(record)
            or accepted_plan["activeWorkspaceDigest"] != previous_revision["workspaceDigest"]
            or accepted_plan["candidateWorkspaceDigest"] != record["workspaceDigest"]
            or record["activatedByPlanId"] != accepted_plan["id"]
            or record["activatedByPlanDigest"] != plan_digest
        ):
            raise DailyLaunchError("local revision accepted plan does not match launch provenance")
        prior_workspace = _revision_workspace(project_root, previous_revision["workspace"])
        recomputed = recompute_plan_fields(
            prior_workspace,
            workspace,
            accepted_plan["toRevision"],
            accepted_plan["fromRevision"]["sourceDigest"],
        )
        if (
            state != recomputed["candidateState"]
            or accepted_plan["sourceDelta"] != recomputed["sourceDelta"]
            or accepted_plan["codeFactDelta"] != recomputed["codeFactDelta"]
            or accepted_plan["relationDelta"] != recomputed["relationDelta"]
            or accepted_plan["invalidation"] != recomputed["invalidation"]
            or accepted_plan["preservation"] != recomputed["preservation"]
        ):
            raise DailyLaunchError("local revision accepted plan semantics do not match preserved workspaces")
    return record, workspace


def validate_launch_record(record: dict[str, Any], source_root: Path, project_root: Path) -> dict[str, Any]:
    identity_digest, key = source_identity(source_root)
    common_valid = (
        record.get("artifactRole") == LAUNCH_ROLE
        and record.get("scope") == LAUNCH_SCOPE
        and record.get("productVersion") == PRODUCT_VERSION
        and record.get("projectKey") == key
        and record.get("sourceIdentityDigest") == identity_digest
        and record.get("sourcePathPersisted") is False
        and record.get("authority") == LAUNCH_AUTHORITY
        and isinstance(record.get("projectTitle"), str)
        and bool(record["projectTitle"].strip())
        and isinstance(record.get("sourceDigest"), str)
        and record["sourceDigest"].startswith("sha256:")
    )
    if not common_valid:
        raise DailyLaunchError("local launch record does not match the source and product boundary")
    if record.get("schemaVersion") == "0.1.0":
        legacy_workspace = project_root / "workspace"
        expected = launch_record(source_root, legacy_workspace, record["projectTitle"], record["sourceDigest"])
        if record != expected:
            raise DailyLaunchError("local launch record does not match the source and product boundary")
        if first_reparse_component(legacy_workspace) is not None or not legacy_workspace.is_dir():
            raise DailyLaunchError("local active revision workspace is missing or unsafe")
        return {
            "schemaVersion": "0.1.0",
            "activeWorkspace": legacy_workspace,
            "activeRevision": {
                "id": "revision.r0001",
                "sequence": 1,
                "sourceDigest": record["sourceDigest"],
                "workspace": "workspace",
                "workspaceDigest": None,
                "activatedByPlanId": None,
                "activatedByPlanDigest": None,
            },
            "archivedRevisions": [],
        }
    expected_keys = {
        "artifactRole", "schemaVersion", "scope", "productVersion", "projectKey",
        "projectTitle", "sourceIdentityDigest", "sourceDigest", "activeRevision",
        "archivedRevisions", "sourcePathPersisted", "authority",
    }
    if record.get("schemaVersion") != REVISION_LAUNCH_SCHEMA or set(record) != expected_keys:
        raise DailyLaunchError("local launch record schema is invalid")
    archives = record["archivedRevisions"]
    if not isinstance(archives, list):
        raise DailyLaunchError("local archived revisions must be a list")
    validated_archives: list[dict[str, Any]] = []
    workspace_paths: set[str] = set()
    previous_revision: dict[str, Any] | None = None
    for sequence, archive in enumerate(archives, start=1):
        validated, path = _validate_revision_record(
            archive,
            sequence,
            project_root,
            previous_revision,
            record["projectKey"],
            record["projectTitle"],
        )
        normalized_path = os.path.normcase(str(path.resolve()))
        if normalized_path in workspace_paths:
            raise DailyLaunchError("local revision workspace paths must be unique")
        workspace_paths.add(normalized_path)
        validated_archives.append(validated)
        previous_revision = validated
    active, active_workspace = _validate_revision_record(
        record["activeRevision"],
        len(archives) + 1,
        project_root,
        previous_revision,
        record["projectKey"],
        record["projectTitle"],
    )
    if active["sourceDigest"] != record["sourceDigest"]:
        raise DailyLaunchError("local active revision does not match launch provenance")
    normalized_active = os.path.normcase(str(active_workspace.resolve()))
    if normalized_active in workspace_paths:
        raise DailyLaunchError("local active revision workspace must be unique")
    return {
        "schemaVersion": REVISION_LAUNCH_SCHEMA,
        "activeWorkspace": active_workspace,
        "activeRevision": active,
        "archivedRevisions": validated_archives,
    }


def _prepare_project_locked(source_root: Path, paths: dict[str, Path], title: str | None) -> dict[str, Any]:
    records = csharp_source_records(source_root)
    source_digest = records_digest(records)
    workspace = paths["workspace"]
    launch_path = paths["launch"]
    identity_digest, key = source_identity(source_root)

    if paths["root"].exists():
        if not paths["root"].is_dir() or is_reparse_point(paths["root"]) or not launch_path.is_file():
            raise DailyLaunchError("local project is incomplete; workspace and launch record must both exist")
        record = read_json(launch_path)
        launch_view = validate_launch_record(record, source_root, paths["root"])
        workspace = launch_view["activeWorkspace"]
        state, _, _, _ = validate_project_workspace(workspace)
        if record["sourceDigest"] != source_digest:
            raise DailyLaunchError("source changed since the recorded snapshot; refresh is required before reopening")
        if state["project"]["sourceDigest"] != record["sourceDigest"]:
            raise DailyLaunchError("project state does not match the recorded launch provenance")
        if records_digest(csharp_source_records(source_root)) != source_digest:
            raise DailyLaunchError("source changed while the local project was being resumed")
        action = "resumed"
        project_title = record["projectTitle"]
    else:
        project_title = (title or source_root.name).strip()
        if not project_title:
            raise DailyLaunchError("project title must not be empty")
        with tempfile.TemporaryDirectory(prefix=f".{paths['root'].name}.stage-", dir=paths["root"].parent) as temporary:
            temporary_root = Path(temporary)
            snapshot = temporary_root / "snapshot"
            staged_project = temporary_root / "project"
            staged_root = temporary_root / "complete"
            initialize_workspace(snapshot, source_root, PROFILE_PATH)
            initialize_project(snapshot, staged_project, safe_project_id(key), project_title)
            if records_digest(csharp_source_records(source_root)) != source_digest:
                raise DailyLaunchError("source changed while the local project was being prepared")
            staged_root.mkdir()
            shutil.move(str(staged_project), str(staged_root / "workspace"))
            write_json(staged_root / LAUNCH_FILE, launch_record(source_root, workspace, project_title, source_digest))
            staged_root.replace(paths["root"])
        validate_launch_record(read_json(launch_path), source_root, paths["root"])
        validate_project_workspace(workspace)
        action = "created"

    return {
        "result": "pass",
        "command": "prepare",
        "action": action,
        "productVersion": PRODUCT_VERSION,
        "projectKey": key,
        "projectTitle": project_title,
        "workspace": workspace.as_posix(),
        "sourceIdentityDigest": identity_digest,
        "sourceDigest": source_digest,
        "sourceFileCount": len(records),
        "sourcePathPersisted": False,
        "targetRepositoryMutation": False,
        "authority": LAUNCH_AUTHORITY,
    }


def prepare_project(source_root: Path, home: Path | None = None, title: str | None = None) -> dict[str, Any]:
    paths = project_paths(source_root, home)
    source_root = validate_roots(source_root, paths["home"])
    validate_project_path_boundary(paths)
    with project_session_lock(paths["root"]):
        return _prepare_project_locked(source_root, paths, title)


def pending_refresh_plan_id(
    project_root: Path,
    current_source_digest: str,
    launch_record_value: dict[str, Any],
    launch_view: dict[str, Any],
) -> str | None:
    pending = project_root / "refresh" / "pending"
    if first_reparse_component(pending) is not None:
        raise DailyLaunchError("local refresh paths must not contain reparse points")
    plan_path = pending / "refresh-plan.json"
    if not plan_path.is_file():
        return None
    if {path.name for path in pending.iterdir()} != {"refresh-plan.json", "workspace"}:
        raise DailyLaunchError("pending refresh directory contains unexpected entries")
    if first_reparse_component(plan_path) is not None:
        raise DailyLaunchError("local refresh plan path must not contain reparse points")
    plan = validate_refresh_plan_record(read_json(plan_path))
    to_revision = plan["toRevision"]
    active_revision = launch_view["activeRevision"]
    active_workspace = launch_view["activeWorkspace"]
    if (
        to_revision["sourceDigest"] != current_source_digest
        or plan["fromRevision"] != _revision_summary(active_revision)
        or plan["activeWorkspaceDigest"] != workspace_tree_digest(active_workspace)
        or plan["projectKey"] != launch_record_value["projectKey"]
        or plan["projectTitle"] != launch_record_value["projectTitle"]
    ):
        raise DailyLaunchError("pending refresh plan does not match the current source review boundary")
    candidate = pending / "workspace"
    if not candidate.is_dir() or first_reparse_component(candidate) is not None:
        raise DailyLaunchError("pending refresh candidate is missing or unsafe")
    if workspace_tree_digest(candidate) != plan["candidateWorkspaceDigest"]:
        raise DailyLaunchError("pending refresh candidate digest does not match the plan")
    candidate_state, _, _, _ = validate_project_workspace(candidate)
    if candidate_state["project"]["sourceDigest"] != current_source_digest:
        raise DailyLaunchError("pending refresh candidate source provenance is stale")
    return plan["id"]


def project_status(source_root: Path, home: Path | None = None) -> dict[str, Any]:
    paths = project_paths(source_root, home)
    source_root = validate_roots(source_root, paths["home"])
    validate_project_path_boundary(paths)
    with project_session_lock(paths["root"]):
        if not paths["root"].exists():
            return {
                "result": "not-initialized",
                "command": "status",
                "projectKey": source_identity(source_root)[1],
                "targetRepositoryMutation": False,
            }
        if not paths["launch"].is_file():
            raise DailyLaunchError("local project is incomplete; workspace and launch record must both exist")
        record = read_json(paths["launch"])
        launch_view = validate_launch_record(record, source_root, paths["root"])
        active_workspace = launch_view["activeWorkspace"]
        state, _, _, _ = validate_project_workspace(active_workspace)
        current_records = csharp_source_records(source_root)
        current_source_digest = records_digest(current_records)
        if record["sourceDigest"] != current_source_digest:
            pending_plan_id = pending_refresh_plan_id(
                paths["root"],
                current_source_digest,
                record,
                launch_view,
            )
            return {
                "result": "refresh-review-required" if pending_plan_id else "refresh-required",
                "command": "status",
                "projectKey": record["projectKey"],
                "projectTitle": record["projectTitle"],
                "workspace": active_workspace.as_posix(),
                "activeRevision": launch_view["activeRevision"]["id"],
                "archivedRevisionCount": len(launch_view["archivedRevisions"]),
                "activeSourceDigest": record["sourceDigest"],
                "currentSourceDigest": current_source_digest,
                "currentSourceFileCount": len(current_records),
                "pendingRefreshPlanId": pending_plan_id,
                "projectStateMatchesActiveSnapshot": state["project"]["sourceDigest"] == record["sourceDigest"],
                "sourcePathPersisted": False,
                "targetRepositoryMutation": False,
            }
        return {**_prepare_project_locked(source_root, paths, None), "command": "status"}


def doctor() -> dict[str, Any]:
    if sys.version_info < (3, 11):
        raise DailyLaunchError("IntentGraph requires Python 3.11 or newer")
    profile = preflight_profile(PROFILE_PATH)
    missing_assets = [path.as_posix() for path in (CYTOSCAPE_SOURCE, CYTOSCAPE_LICENSE_SOURCE) if not path.is_file()]
    if missing_assets:
        raise DailyLaunchError("required local Workbench assets are missing: " + ", ".join(missing_assets))
    return {
        "result": "pass",
        "command": "doctor",
        "productVersion": PRODUCT_VERSION,
        "python": {"executable": os.path.basename(os.sys.executable), "version": os.sys.version.split()[0]},
        "csharpProfile": {
            "id": profile["profile"]["id"],
            "selectedSdkVersion": profile["selectedSdk"]["version"],
            "available": True,
        },
        "workbenchAssets": {"cytoscape": True, "license": True},
        "networkRequired": False,
        "targetRepositoryMutation": False,
    }


@contextmanager
def project_session_lock(project_root: Path):
    lock_path = project_root.parent / f".{project_root.name}.igd-session.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if lock_path.exists() and is_reparse_point(lock_path):
        raise DailyLaunchError("IntentGraph project lock must not be a reparse point")
    handle = lock_path.open("a+b")
    handle.seek(0, os.SEEK_END)
    if handle.tell() == 0:
        handle.write(b"0")
        handle.flush()
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as error:
        handle.close()
        raise DailyLaunchError("this IntentGraph project is already open in another process") from error
    try:
        yield
    finally:
        try:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


def open_browser_when_ready(
    url: str,
    *,
    attempts: int = 50,
    readiness_timeout: float = 1.0,
    retry_delay: float = 0.1,
    urlopen: Any | None = None,
    browser_open: Any | None = None,
    sleep: Any | None = None,
) -> dict[str, Any]:
    if attempts < 1:
        raise DailyLaunchError("browser readiness attempts must be positive")
    request = urlopen or urllib.request.urlopen
    launch = browser_open or webbrowser.open
    wait = sleep or time.sleep
    for attempt in range(1, attempts + 1):
        try:
            with request(url + "api/revision-head", timeout=readiness_timeout) as response:
                if response.status == 200:
                    break
        except OSError:
            if attempt < attempts:
                wait(retry_delay)
    else:
        result = {
            "result": "warning",
            "warning": "Workbench did not become ready for browser launch",
            "url": url,
            "ready": False,
            "browserOpened": False,
            "attempts": attempts,
        }
        print(json.dumps(result), file=sys.stderr)
        return result
    opened = bool(launch(url))
    result = {
        "result": "opened" if opened else "warning",
        "url": url,
        "ready": True,
        "browserOpened": opened,
        "attempts": attempt,
    }
    if not opened:
        result["warning"] = "Default browser could not be opened"
        print(json.dumps(result), file=sys.stderr)
    return result


def open_project(
    source_root: Path,
    home: Path | None = None,
    title: str | None = None,
    *,
    port: int = 0,
    open_browser: bool = True,
) -> int:
    if not 0 <= port <= 65535:
        raise DailyLaunchError("port must be between 0 and 65535")
    if port:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError as error:
                raise DailyLaunchError(f"requested loopback port is unavailable: {port}") from error
    paths = project_paths(source_root, home)
    source_root = validate_roots(source_root, paths["home"])
    validate_project_path_boundary(paths)
    with project_session_lock(paths["root"]):
        prepared = _prepare_project_locked(source_root, paths, title)
        workspace = Path(prepared["workspace"])
        server = make_server(workspace, "127.0.0.1", port)
        address, assigned_port = server.server_address[:2]
        url = f"http://{address}:{assigned_port}/"
        print(
            json.dumps(
                {
                    **prepared,
                    "result": "serving",
                    "command": "open",
                    "url": url,
                    "host": address,
                    "port": assigned_port,
                    "browserRequested": open_browser,
                },
                ensure_ascii=True,
            ),
            flush=True,
        )
        if open_browser:
            thread = threading.Thread(target=open_browser_when_ready, args=(url,), daemon=True)
            thread.start()
        try:
            server.serve_forever(poll_interval=0.25)
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
    return 0
