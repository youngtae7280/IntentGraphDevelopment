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
from pathlib import Path
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


PRODUCT_VERSION = "0.1.0-preview"
LAUNCH_FILE = "intentgraph.launch.json"
LAUNCH_ROLE = "intentgraph-local-project-launch-record"
LAUNCH_SCOPE = "local-csharp-review-workbench-daily-launch"
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


def validate_launch_record(record: dict[str, Any], source_root: Path, workspace: Path) -> None:
    identity_digest, key = source_identity(source_root)
    expected = {
        "artifactRole": LAUNCH_ROLE,
        "schemaVersion": "0.1.0",
        "scope": LAUNCH_SCOPE,
        "productVersion": PRODUCT_VERSION,
        "projectKey": key,
        "projectTitle": record.get("projectTitle"),
        "sourceIdentityDigest": identity_digest,
        "sourceDigest": record.get("sourceDigest"),
        "workspace": workspace.relative_to(workspace.parent.parent).as_posix(),
        "sourcePathPersisted": False,
        "authority": LAUNCH_AUTHORITY,
    }
    if (
        record != expected
        or not isinstance(record.get("projectTitle"), str)
        or not record["projectTitle"].strip()
        or not isinstance(record.get("sourceDigest"), str)
        or not record["sourceDigest"].startswith("sha256:")
    ):
        raise DailyLaunchError("local launch record does not match the source and product boundary")


def _prepare_project_locked(source_root: Path, paths: dict[str, Path], title: str | None) -> dict[str, Any]:
    records = csharp_source_records(source_root)
    source_digest = records_digest(records)
    workspace = paths["workspace"]
    launch_path = paths["launch"]
    identity_digest, key = source_identity(source_root)

    if paths["root"].exists():
        if not paths["root"].is_dir() or is_reparse_point(paths["root"]) or not workspace.is_dir() or not launch_path.is_file():
            raise DailyLaunchError("local project is incomplete; workspace and launch record must both exist")
        record = read_json(launch_path)
        validate_launch_record(record, source_root, workspace)
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
        validate_launch_record(read_json(launch_path), source_root, workspace)
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
