"""Reviewed source refresh workflow for the local IntentGraph C# Workbench."""

from __future__ import annotations

from copy import deepcopy
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from experimental_csharp_project import (
    PROJECT_FILE,
    initialize_project,
    validate_project_workspace,
)
from experimental_csharp_workspace import (
    PROFILE_PATH,
    csharp_source_records,
    initialize_workspace,
    records_digest,
)
from igd_daily import (
    ACCEPTED_REFRESH_PLAN_FILE,
    DailyLaunchError,
    digest_bytes,
    first_reparse_component,
    project_paths,
    project_session_lock,
    read_json,
    revision_launch_record,
    source_identity,
    validate_launch_record,
    validate_project_path_boundary,
    validate_refresh_plan_record,
    validate_roots,
    workspace_tree_digest,
)
from igd_refresh_model import candidate_state, file_delta, recompute_plan_fields


REFRESH_DIRECTORY = "refresh"
PENDING_DIRECTORY = "pending"
PLAN_FILE = "refresh-plan.json"
REVISIONS_DIRECTORY = "revisions"
REFRESH_PLAN_ROLE = "intentgraph-local-source-refresh-plan"
REFRESH_PLAN_STATUS = "intentgraph-local-source-refresh-review-required"
REFRESH_PLAN_SCOPE = "p9.35-reviewed-csharp-source-refresh"
REFRESH_RECEIPT_ROLE = "intentgraph-local-source-refresh-receipt"
REFRESH_AUTHORITY = {
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
    **REFRESH_AUTHORITY,
    "activeRevisionMutation": True,
    "explicitPlanAcceptanceRequired": True,
}


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_name, path)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def tree_digest(root: Path) -> str:
    return workspace_tree_digest(root)


def _revision_id(sequence: int) -> str:
    return f"revision.r{sequence:04d}"


def _revision_summary(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": record["id"],
        "sequence": record["sequence"],
        "sourceDigest": record["sourceDigest"],
    }


def _pending_root(root: Path) -> Path:
    pending = root / REFRESH_DIRECTORY / PENDING_DIRECTORY
    if first_reparse_component(pending) is not None:
        raise DailyLaunchError("local refresh paths must not contain reparse points")
    return pending


def _read_pending_plan(pending: Path) -> dict[str, Any]:
    plan_path = pending / PLAN_FILE
    if first_reparse_component(plan_path) is not None:
        raise DailyLaunchError("local refresh plan path must not contain reparse points")
    if not plan_path.is_file():
        raise DailyLaunchError("no pending source refresh exists")
    if {path.name for path in pending.iterdir()} != {PLAN_FILE, "workspace"}:
        raise DailyLaunchError("pending refresh directory contains unexpected entries")
    return _validate_plan(read_json(plan_path))


def _revision_root(root: Path, revision_id: str) -> Path:
    revision = root / REVISIONS_DIRECTORY / revision_id
    if first_reparse_component(revision) is not None:
        raise DailyLaunchError("local revision paths must not contain reparse points")
    return revision


def _validate_plan(plan: dict[str, Any]) -> dict[str, Any]:
    return validate_refresh_plan_record(plan)


def _acceptance_receipt(plan: dict[str, Any], prior_workspace: str, active_workspace: str) -> dict[str, Any]:
    return {
        "artifactRole": REFRESH_RECEIPT_ROLE,
        "schemaVersion": "0.1.0",
        "scope": REFRESH_PLAN_SCOPE,
        "status": "intentgraph-local-source-refresh-accepted",
        "result": "pass",
        "planId": plan["id"],
        "planDigest": digest_bytes(canonical_bytes(plan)),
        "fromRevision": plan["fromRevision"],
        "toRevision": plan["toRevision"],
        "priorWorkspace": prior_workspace,
        "activeWorkspace": active_workspace,
        "sourcePathPersisted": False,
        "authority": REFRESH_ACCEPT_AUTHORITY,
    }


def _validate_unreferenced_staged_revision(
    plan: dict[str, Any],
    revision_root: Path,
    prior_workspace: str,
) -> None:
    workspace = revision_root / "workspace"
    receipt_path = revision_root / "refresh-receipt.json"
    accepted_plan_path = revision_root / ACCEPTED_REFRESH_PLAN_FILE
    for path in (revision_root, workspace, receipt_path, accepted_plan_path):
        if first_reparse_component(path) is not None:
            raise DailyLaunchError("staged revision cannot contain reparse points")
    if not workspace.is_dir() or not receipt_path.is_file() or not accepted_plan_path.is_file():
        raise DailyLaunchError("staged revision cannot be attributed to the pending plan")
    if {path.name for path in revision_root.iterdir()} != {
        "workspace", "refresh-receipt.json", ACCEPTED_REFRESH_PLAN_FILE
    }:
        raise DailyLaunchError("staged revision contains unexpected entries")
    accepted_plan = _validate_plan(read_json(accepted_plan_path))
    active_workspace = f"revisions/{plan['toRevision']['id']}/workspace"
    if accepted_plan != plan or read_json(receipt_path) != _acceptance_receipt(plan, prior_workspace, active_workspace):
        raise DailyLaunchError("staged revision cannot be attributed to the pending plan")
    if tree_digest(workspace) != plan["candidateWorkspaceDigest"]:
        raise DailyLaunchError("staged revision workspace does not match the pending plan")
    state, _, _, _ = validate_project_workspace(workspace)
    if state["project"]["sourceDigest"] != plan["toRevision"]["sourceDigest"]:
        raise DailyLaunchError("staged revision source provenance does not match the pending plan")


def _prepare_candidate(
    source_root: Path,
    root: Path,
    workspace: Path,
    old_state: dict[str, Any],
    old_data: dict[str, Any],
    current_revision: dict[str, Any],
    source_records: list[dict[str, str]],
) -> dict[str, Any]:
    pending = _pending_root(root)
    if pending.exists():
        existing = _read_pending_plan(pending)
        existing_candidate = pending / "workspace"
        if existing["toRevision"]["sourceDigest"] == records_digest(source_records):
            if (
                existing["fromRevision"] != current_revision
                or existing["activeWorkspaceDigest"] != tree_digest(workspace)
                or not existing_candidate.is_dir()
                or existing["candidateWorkspaceDigest"] != tree_digest(existing_candidate)
                or existing["projectKey"] != source_identity(source_root)[1]
                or existing["projectTitle"] != old_state["project"]["title"]
            ):
                raise DailyLaunchError("pending source refresh no longer matches its active or candidate workspace")
            validate_project_workspace(existing_candidate)
            return existing
        raise DailyLaunchError("a different source refresh is already pending; accept or discard it first")
    pending.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".r-", dir=root) as temporary:
        temporary_root = Path(temporary)
        snapshot = temporary_root / "s"
        candidate = temporary_root / "w"
        initialize_workspace(snapshot, source_root, PROFILE_PATH)
        initialize_project(snapshot, candidate, old_state["project"]["id"], old_state["project"]["title"])
        fresh_state, _, _, fresh_data = validate_project_workspace(candidate)
        to_revision = {
            "id": _revision_id(current_revision["sequence"] + 1),
            "sequence": current_revision["sequence"] + 1,
            "sourceDigest": fresh_state["project"]["sourceDigest"],
        }
        next_candidate_state, delta = candidate_state(
            old_state,
            fresh_state,
            old_data["facts"],
            fresh_data["facts"],
            to_revision,
            current_revision["sourceDigest"],
        )
        (candidate / PROJECT_FILE).write_text(
            json.dumps(next_candidate_state, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        validate_project_workspace(candidate)
        old_snapshot_records = csharp_source_records(workspace / "snapshot" / "source")
        plan = {
            "artifactRole": REFRESH_PLAN_ROLE,
            "schemaVersion": "0.1.0",
            "scope": REFRESH_PLAN_SCOPE,
            "status": REFRESH_PLAN_STATUS,
            "result": "review-required",
            "id": f"refresh.{current_revision['sequence']:04d}.{to_revision['sourceDigest'].removeprefix('sha256:')[:12]}",
            "projectKey": source_identity(source_root)[1],
            "projectTitle": old_state["project"]["title"],
            "fromRevision": current_revision,
            "toRevision": to_revision,
            "sourceDelta": file_delta(old_snapshot_records, source_records),
            "codeFactDelta": delta["facts"],
            "relationDelta": delta["relations"],
            "invalidation": delta["invalidation"],
            "preservation": {
                "priorWorkspaceSealedOnAcceptance": True,
                "priorHistoryRecordCount": len(old_state["history"]),
                "priorEvidenceRecordCount": len(old_state["evidence"]),
                "priorAuthorityDigest": digest_bytes(canonical_bytes(old_state["authority"])),
                "workItemCount": len(old_state["workItems"]),
                "targetRepositoryMutation": False,
            },
            "activeWorkspaceDigest": tree_digest(workspace),
            "candidateWorkspace": "refresh/pending/workspace",
            "candidateWorkspaceDigest": tree_digest(candidate),
            "sourcePathPersisted": False,
            "authority": REFRESH_AUTHORITY,
        }
        _validate_plan(plan)
        complete = temporary_root / "p"
        complete.mkdir()
        candidate.replace(complete / "workspace")
        write_json_atomic(complete / PLAN_FILE, plan)
        complete.replace(pending)
    return plan


def plan_refresh(source_root: Path, home: Path | None = None) -> dict[str, Any]:
    paths = project_paths(source_root, home)
    source_root = validate_roots(source_root, paths["home"])
    validate_project_path_boundary(paths)
    with project_session_lock(paths["root"]):
        if not paths["root"].is_dir() or not paths["launch"].is_file():
            raise DailyLaunchError("local project must be prepared before refresh")
        launch = read_json(paths["launch"])
        launch_view = validate_launch_record(launch, source_root, paths["root"])
        workspace = launch_view["activeWorkspace"]
        recorded_workspace_digest = launch_view["activeRevision"]["workspaceDigest"]
        if recorded_workspace_digest is not None and tree_digest(workspace) != recorded_workspace_digest:
            raise DailyLaunchError("active revision workspace digest does not match launch provenance")
        old_state, _, _, old_data = validate_project_workspace(workspace)
        source_records = csharp_source_records(source_root)
        source_digest = records_digest(source_records)
        if source_digest == launch["sourceDigest"]:
            pending = _pending_root(paths["root"])
            if pending.exists():
                pending_plan = _read_pending_plan(pending)
                active_revision = launch_view["activeRevision"]
                if (
                    _revision_summary(active_revision) == pending_plan["toRevision"]
                    and active_revision.get("activatedByPlanId") == pending_plan["id"]
                    and active_revision.get("activatedByPlanDigest") == digest_bytes(canonical_bytes(pending_plan))
                ):
                    shutil.rmtree(pending)
            return {
                "result": "pass",
                "command": "refresh",
                "action": "not-required",
                "sourceDigest": source_digest,
                "targetRepositoryMutation": False,
            }
        current_revision = _revision_summary(launch_view["activeRevision"])
        plan = _prepare_candidate(
            source_root,
            paths["root"],
            workspace,
            old_state,
            old_data,
            current_revision,
            source_records,
        )
        if records_digest(csharp_source_records(source_root)) != plan["toRevision"]["sourceDigest"]:
            raise DailyLaunchError("source changed while the refresh candidate was being prepared")
        return {
            "result": "review-required",
            "command": "refresh",
            "action": "planned",
            "planId": plan["id"],
            "fromRevision": plan["fromRevision"],
            "toRevision": plan["toRevision"],
            "sourceDelta": plan["sourceDelta"],
            "codeFactDelta": plan["codeFactDelta"],
            "relationDelta": plan["relationDelta"],
            "invalidation": plan["invalidation"],
            "activeRevisionChanged": False,
            "targetRepositoryMutation": False,
            "acceptCommand": f"igd refresh <source-root> --accept-plan {plan['id']}",
        }


def accept_refresh(source_root: Path, plan_id: str, home: Path | None = None) -> dict[str, Any]:
    paths = project_paths(source_root, home)
    source_root = validate_roots(source_root, paths["home"])
    validate_project_path_boundary(paths)
    with project_session_lock(paths["root"]):
        pending = _pending_root(paths["root"])
        plan_path = pending / PLAN_FILE
        candidate = pending / "workspace"
        if not candidate.is_dir():
            raise DailyLaunchError("no pending source refresh exists")
        plan = _read_pending_plan(pending)
        if plan_id != plan["id"]:
            raise DailyLaunchError("accepted refresh plan id does not match the pending plan")
        launch_bytes_before = paths["launch"].read_bytes()
        launch = read_json(paths["launch"])
        launch_view = validate_launch_record(launch, source_root, paths["root"])
        active_workspace = launch_view["activeWorkspace"]
        if launch["sourceDigest"] != plan["fromRevision"]["sourceDigest"]:
            raise DailyLaunchError("active launch provenance changed after refresh planning")
        if records_digest(csharp_source_records(source_root)) != plan["toRevision"]["sourceDigest"]:
            raise DailyLaunchError("source changed after refresh planning; discard and plan again")
        if tree_digest(active_workspace) != plan["activeWorkspaceDigest"]:
            raise DailyLaunchError("active project changed after refresh planning; discard and plan again")
        if tree_digest(candidate) != plan["candidateWorkspaceDigest"]:
            raise DailyLaunchError("refresh candidate changed after planning")
        old_state, _, _, _ = validate_project_workspace(active_workspace)
        candidate_state, _, _, _ = validate_project_workspace(candidate)
        if candidate_state["project"]["sourceDigest"] != plan["toRevision"]["sourceDigest"]:
            raise DailyLaunchError("refresh candidate source provenance is stale")
        recomputed = recompute_plan_fields(
            active_workspace,
            candidate,
            plan["toRevision"],
            plan["fromRevision"]["sourceDigest"],
        )
        if (
            candidate_state != recomputed["candidateState"]
            or plan["sourceDelta"] != recomputed["sourceDelta"]
            or plan["codeFactDelta"] != recomputed["codeFactDelta"]
            or plan["relationDelta"] != recomputed["relationDelta"]
            or plan["invalidation"] != recomputed["invalidation"]
            or plan["preservation"] != recomputed["preservation"]
            or plan["projectKey"] != source_identity(source_root)[1]
            or plan["projectTitle"] != old_state["project"]["title"]
        ):
            raise DailyLaunchError("refresh plan or candidate does not match deterministic recomputation")
        active_revision = launch_view["activeRevision"]
        if _revision_summary(active_revision) != plan["fromRevision"]:
            raise DailyLaunchError("active revision changed after refresh planning")
        plan_digest = digest_bytes(canonical_bytes(plan))
        prior_revision = deepcopy(active_revision)
        prior_revision["workspaceDigest"] = plan["activeWorkspaceDigest"]
        if prior_revision["workspace"] == active_workspace.as_posix():
            prior_revision["workspace"] = active_workspace.relative_to(paths["root"]).as_posix()
        if active_workspace == paths["workspace"]:
            prior_revision["workspace"] = "workspace"
        prior_revision.setdefault("activatedByPlanId", None)
        prior_revision.setdefault("activatedByPlanDigest", None)
        next_revision = {
            **plan["toRevision"],
            "workspace": f"revisions/{plan['toRevision']['id']}/workspace",
            "workspaceDigest": plan["candidateWorkspaceDigest"],
            "activatedByPlanId": plan["id"],
            "activatedByPlanDigest": plan_digest,
        }
        archived_revisions = [deepcopy(record) for record in launch_view["archivedRevisions"]] + [prior_revision]
        receipt = _acceptance_receipt(plan, prior_revision["workspace"], next_revision["workspace"])
        revision_root = _revision_root(paths["root"], plan["toRevision"]["id"])
        revision_workspace = revision_root / "workspace"
        receipt_path = revision_root / "refresh-receipt.json"
        accepted_plan_path = revision_root / ACCEPTED_REFRESH_PLAN_FILE
        if revision_root.exists():
            if (
                not revision_workspace.is_dir()
                or tree_digest(revision_workspace) != plan["candidateWorkspaceDigest"]
                or not receipt_path.is_file()
                or not accepted_plan_path.is_file()
                or read_json(receipt_path) != receipt
                or read_json(accepted_plan_path) != plan
            ):
                raise DailyLaunchError("staged accepted revision conflicts with the pending candidate")
        else:
            revision_root.parent.mkdir(parents=True, exist_ok=True)
            staging = Path(tempfile.mkdtemp(prefix=f".{plan['toRevision']['id']}.", dir=revision_root.parent))
            try:
                shutil.copytree(candidate, staging / "workspace")
                if tree_digest(staging / "workspace") != plan["candidateWorkspaceDigest"]:
                    raise DailyLaunchError("staged accepted revision digest does not match the candidate")
                write_json_atomic(staging / "refresh-receipt.json", receipt)
                write_json_atomic(staging / ACCEPTED_REFRESH_PLAN_FILE, plan)
                staging.replace(revision_root)
            except Exception:
                shutil.rmtree(staging, ignore_errors=True)
                raise
        next_launch = revision_launch_record(
            source_root,
            launch["projectTitle"],
            next_revision,
            archived_revisions,
        )
        validate_launch_record(next_launch, source_root, paths["root"])
        validate_project_workspace(revision_workspace)
        if paths["launch"].read_bytes() != launch_bytes_before:
            raise DailyLaunchError("active launch record changed during refresh acceptance")
        if records_digest(csharp_source_records(source_root)) != plan["toRevision"]["sourceDigest"]:
            raise DailyLaunchError("source changed during refresh acceptance; plan again")
        write_json_atomic(paths["launch"], next_launch)
        try:
            committed_launch = read_json(paths["launch"])
            committed_view = validate_launch_record(committed_launch, source_root, paths["root"])
            if committed_view["activeRevision"] != next_revision:
                raise DailyLaunchError("accepted revision did not become the exact active revision")
            if records_digest(csharp_source_records(source_root)) != plan["toRevision"]["sourceDigest"]:
                raise DailyLaunchError("source changed during refresh activation")
        except Exception as error:
            write_bytes_atomic(paths["launch"], launch_bytes_before)
            if paths["launch"].read_bytes() != launch_bytes_before:
                raise DailyLaunchError("accepted revision failed validation and prior launch recovery failed") from error
            raise DailyLaunchError("accepted revision failed post-commit validation; prior launch restored") from error
        shutil.rmtree(pending, ignore_errors=True)
        return {
            "result": "pass",
            "command": "refresh",
            "action": "accepted",
            "planId": plan["id"],
            "fromRevision": plan["fromRevision"],
            "toRevision": plan["toRevision"],
            "priorWorkspace": prior_revision["workspace"],
            "activeWorkspace": next_revision["workspace"],
            "activeRevisionChanged": True,
            "targetRepositoryMutation": False,
            "authority": REFRESH_ACCEPT_AUTHORITY,
        }


def discard_refresh(source_root: Path, plan_id: str, home: Path | None = None) -> dict[str, Any]:
    paths = project_paths(source_root, home)
    source_root = validate_roots(source_root, paths["home"])
    validate_project_path_boundary(paths)
    with project_session_lock(paths["root"]):
        pending = _pending_root(paths["root"])
        plan_path = pending / PLAN_FILE
        plan = _read_pending_plan(pending)
        if plan_id != plan["id"]:
            raise DailyLaunchError("discarded refresh plan id does not match the pending plan")
        launch = read_json(paths["launch"])
        launch_view = validate_launch_record(launch, source_root, paths["root"])
        active_revision = launch_view["activeRevision"]
        launch_revisions = [*launch_view["archivedRevisions"], active_revision]
        accepted_revision = next(
            (
                revision
                for revision in launch_revisions
                if _revision_summary(revision) == plan["toRevision"]
                and revision.get("activatedByPlanId") == plan["id"]
                and revision.get("activatedByPlanDigest") == digest_bytes(canonical_bytes(plan))
            ),
            None,
        )
        if any(revision["id"] == plan["toRevision"]["id"] for revision in launch_revisions) and accepted_revision is None:
            raise DailyLaunchError("pending plan revision conflicts with launch history")
        staged_revision = _revision_root(paths["root"], plan["toRevision"]["id"])
        if accepted_revision is not None:
            shutil.rmtree(pending)
            return {
                "result": "pass",
                "command": "refresh",
                "action": "accepted-plan-cleanup",
                "planId": plan["id"],
                "activeRevision": active_revision["id"],
                "acceptedRevision": accepted_revision["id"],
                "activeRevisionChanged": False,
                "targetRepositoryMutation": False,
            }
        if staged_revision.exists():
            _validate_unreferenced_staged_revision(
                plan,
                staged_revision,
                active_revision["workspace"],
            )
            shutil.rmtree(staged_revision)
        shutil.rmtree(pending)
        return {
            "result": "pass",
            "command": "refresh",
            "action": "discarded",
            "planId": plan["id"],
            "activeRevisionChanged": False,
            "targetRepositoryMutation": False,
        }
