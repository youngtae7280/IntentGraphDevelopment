"""Build, install, launch, and uninstall the Windows-local IntentGraph preview."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any

from build_igd_windows_bundle import build_bundle, digest_file


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "docs" / "examples" / "product-smoke-csharp"


def run(
    arguments: list[str],
    *,
    timeout: int = 120,
    cwd: Path = ROOT,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        arguments,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        encoding="utf-8",
        timeout=timeout,
        check=False,
    )


def powershell(
    script: Path,
    install_root: Path,
    *,
    no_path_update: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    arguments = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script),
            "-InstallRoot",
            str(install_root),
        ]
    if no_path_update:
        arguments.append("-NoPathUpdate")
    return run(arguments, env=env)


def tree_digest(root: Path) -> str:
    records: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            records.append((path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()))
    return "sha256:" + hashlib.sha256(json.dumps(records, separators=(",", ":")).encode()).hexdigest()


def parsed_json(result: subprocess.CompletedProcess[str], label: str) -> dict[str, Any]:
    if result.returncode != 0:
        raise RuntimeError(f"{label} failed: {result.stderr or result.stdout}")
    try:
        value = json.loads(result.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError) as error:
        raise RuntimeError(f"{label} did not emit JSON") from error
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} JSON must be an object")
    return value


def read_process_json_line(
    process: subprocess.Popen[str], label: str, timeout_seconds: float = 15.0
) -> dict[str, Any]:
    if process.stdout is None:
        raise RuntimeError(f"{label} stdout unavailable")
    lines: queue.Queue[str | BaseException] = queue.Queue(maxsize=1)

    def read_line() -> None:
        try:
            lines.put(process.stdout.readline())
        except BaseException as error:  # Preserve cleanup even on stream failures.
            lines.put(error)

    threading.Thread(target=read_line, daemon=True).start()
    try:
        value = lines.get(timeout=timeout_seconds)
    except queue.Empty as error:
        raise RuntimeError(f"{label} did not emit startup JSON within {timeout_seconds:g} seconds") from error
    if isinstance(value, BaseException):
        raise RuntimeError(f"{label} startup stream failed") from value
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"{label} did not emit valid startup JSON") from error
    if not isinstance(parsed, dict):
        raise RuntimeError(f"{label} startup JSON must be an object")
    return parsed


def matching_windows_processes(unique_root: Path) -> list[dict[str, Any]]:
    """Return only processes whose command line names this smoke run's temp root."""
    env = os.environ.copy()
    env["IGD_INSTALL_SMOKE_PROCESS_ROOT"] = str(unique_root.resolve())
    script = """
$needle = $env:IGD_INSTALL_SMOKE_PROCESS_ROOT
$rows = @(Get-CimInstance Win32_Process |
    Where-Object { $_.CommandLine -and $_.CommandLine.Contains($needle) } |
    ForEach-Object {
        [pscustomobject]@{
            processId = [int]$_.ProcessId
            parentProcessId = [int]$_.ParentProcessId
            name = [string]$_.Name
            commandLine = [string]$_.CommandLine
        }
    })
ConvertTo-Json -InputObject @($rows) -Compress
"""
    result = run(
        ["powershell", "-NoProfile", "-Command", script],
        timeout=30,
        env=env,
    )
    if result.returncode != 0:
        raise RuntimeError(f"could not inventory installed launch processes: {result.stderr or result.stdout}")
    try:
        value = json.loads(result.stdout.strip() or "[]")
    except json.JSONDecodeError as error:
        raise RuntimeError("installed launch process inventory did not emit JSON") from error
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise RuntimeError("installed launch process inventory must be a JSON array")
    return value


def terminate_matching_windows_processes(unique_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Terminate the launcher chain without touching unrelated Python processes."""
    observed: dict[int, dict[str, Any]] = {}
    for _ in range(4):
        matches = matching_windows_processes(unique_root)
        if not matches:
            return list(observed.values()), []
        for item in matches:
            pid = int(item["processId"])
            observed[pid] = item
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                text=True,
                capture_output=True,
                timeout=15,
                check=False,
            )
        time.sleep(0.25)
    return list(observed.values()), matching_windows_processes(unique_root)


def windows_listener_pids(port: int) -> list[int]:
    script = """
$port = [int]$args[0]
$pids = @(Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue |
    ForEach-Object { [int]$_.OwningProcess } | Select-Object -Unique)
ConvertTo-Json -InputObject @($pids) -Compress
"""
    try:
        result = run(
            ["powershell", "-NoProfile", "-Command", script, str(port)], timeout=30
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0:
        return []
    try:
        value = json.loads(result.stdout.strip() or "[]")
    except json.JSONDecodeError:
        return []
    if isinstance(value, int):
        value = [value]
    return [int(item) for item in value] if isinstance(value, list) else []


def taskkill_windows_processes(process_ids: set[int]) -> None:
    for pid in sorted(process_ids):
        if pid <= 0:
            continue
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                text=True,
                capture_output=True,
                timeout=15,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue


def wait_for_port_close(url: str, timeout_seconds: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=0.5):
                time.sleep(0.1)
        except OSError:
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    source_before = tree_digest(FIXTURE)

    with tempfile.TemporaryDirectory(prefix="igd-windows-install-smoke-") as temporary:
        temp = Path(temporary)
        bundle_a = temp / "bundle-a"
        archive_a = temp / "bundle-a.zip"
        bundle_b = temp / "bundle-b"
        archive_b = temp / "bundle-b.zip"
        first_build = build_bundle(bundle_a, archive_a)
        second_build = build_bundle(bundle_b, archive_b)
        repeat_archive_identical = digest_file(archive_a) == digest_file(archive_b)
        install_root = temp / "installed"
        user_data = temp / "user-data"
        user_data.mkdir()
        sentinel = user_data / "preserve-after-uninstall.txt"
        sentinel.write_text("preserve\n", encoding="utf-8")
        user_path_before = os.environ.get("PATH", "")

        shadow = temp / "shadow"
        shadow.mkdir()
        (shadow / "igd.exe").write_bytes(b"not an executable; PATH detection must still fail closed\n")
        shadow_env = os.environ.copy()
        shadow_env["PATH"] = str(shadow) + os.pathsep + shadow_env.get("PATH", "")
        shadowed_root = temp / "shadowed-install"
        shadowed = powershell(
            bundle_a / "install.ps1",
            shadowed_root,
            no_path_update=False,
            env=shadow_env,
        )
        path_shadowing_rejected = (
            shadowed.returncode != 0
            and "PATH already resolves igd outside InstallRoot" in (shadowed.stderr + shadowed.stdout)
            and not shadowed_root.exists()
        )
        if not path_shadowing_rejected:
            raise RuntimeError(f"PATH-shadowing installer probe failed: {shadowed.stderr or shadowed.stdout}")

        installed = powershell(bundle_a / "install.ps1", install_root)
        if installed.returncode != 0:
            raise RuntimeError(f"installer failed: {installed.stderr or installed.stdout}")
        launcher = install_root / "igd.cmd"
        runtime_digest_after_install = tree_digest(install_root)
        launch_env = os.environ.copy()
        launch_env["PATH"] = str(install_root) + os.pathsep + launch_env.get("PATH", "")
        where_igd = run(["where.exe", "igd"], cwd=temp, env=launch_env)
        resolved_igd = Path(where_igd.stdout.splitlines()[0]).resolve() if where_igd.returncode == 0 and where_igd.stdout.splitlines() else None
        default_path_resolution = resolved_igd == launcher.resolve()
        doctor = parsed_json(
            run(["cmd.exe", "/d", "/s", "/c", "igd doctor"], cwd=temp, env=launch_env),
            "PATH-resolved installed doctor",
        )
        prepared = parsed_json(
            run([str(launcher), "prepare", str(FIXTURE), "--home", str(user_data), "--title", "Installed smoke"]),
            "installed prepare",
        )

        process = subprocess.Popen(
            [str(launcher), "open", str(FIXTURE), "--home", str(user_data), "--port", "0", "--no-browser"],
            cwd=ROOT,
            env=launch_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        observed_launch_processes: list[dict[str, Any]] = []
        remaining_launch_processes: list[dict[str, Any]] = []
        cleanup_inventory_error: str | None = None
        launch: dict[str, Any] = {}
        try:
            launch = read_process_json_line(process, "installed open")
            deadline = time.monotonic() + 15
            projection: dict[str, Any] | None = None
            while time.monotonic() < deadline:
                try:
                    with urllib.request.urlopen(launch["url"] + "api/projection", timeout=2) as response:
                        projection = json.loads(response.read())
                    break
                except OSError:
                    time.sleep(0.1)
            if projection is None:
                raise RuntimeError("installed Workbench did not become ready")
            observed_launch_processes = matching_windows_processes(temp)
        finally:
            if os.name == "nt":
                known_pids = {process.pid}
                known_pids.update(int(item["processId"]) for item in observed_launch_processes)
                if isinstance(launch.get("port"), int):
                    known_pids.update(windows_listener_pids(launch["port"]))
                taskkill_windows_processes(known_pids)
                try:
                    cleanup_observed, remaining_launch_processes = terminate_matching_windows_processes(temp)
                except Exception as error:
                    cleanup_inventory_error = str(error)
                    cleanup_observed = []
                    try:
                        remaining_launch_processes = matching_windows_processes(temp)
                    except Exception as verification_error:
                        remaining_launch_processes = [
                            {"cleanupVerificationError": str(verification_error)}
                        ]
                observed_by_pid = {int(item["processId"]): item for item in observed_launch_processes}
                observed_by_pid.update({int(item["processId"]): item for item in cleanup_observed})
                observed_launch_processes = list(observed_by_pid.values())
            else:
                process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

        installed_server_process_observed = any(
            "igd.py" in str(item.get("commandLine", "")).lower()
            and " open " in str(item.get("commandLine", "")).lower()
            for item in observed_launch_processes
        )
        installed_process_cleanup_verified = not remaining_launch_processes
        installed_process_inventory_succeeded = cleanup_inventory_error is None
        installed_port_closed = wait_for_port_close(launch["url"] + "api/projection")
        resumed = parsed_json(
            run([str(launcher), "prepare", str(FIXTURE), "--home", str(user_data)]),
            "installed prepare after server cleanup",
        )
        session_lock_released = resumed.get("result") == "pass" and resumed.get("action") == "resumed"

        unknown_file = install_root / "unrecorded.txt"
        unknown_file.write_text("not in manifest\n", encoding="utf-8")
        unknown_file_result = powershell(install_root / "uninstall.ps1", install_root)
        unknown_file_rejected = (
            unknown_file_result.returncode != 0
            and "unknown file: unrecorded.txt" in (unknown_file_result.stderr + unknown_file_result.stdout)
            and install_root.is_dir()
        )
        unknown_file.unlink()

        unknown_directory = install_root / "unrecorded-directory"
        unknown_directory.mkdir()
        unknown_directory_result = powershell(install_root / "uninstall.ps1", install_root)
        unknown_directory_rejected = (
            unknown_directory_result.returncode != 0
            and "unknown directory: unrecorded-directory" in (unknown_directory_result.stderr + unknown_directory_result.stdout)
            and install_root.is_dir()
        )
        unknown_directory.rmdir()

        tampered_runtime = install_root / "tools" / "igd.py"
        original_runtime = tampered_runtime.read_bytes()
        tampered_runtime.write_bytes(original_runtime + b"\n# uninstall tamper probe\n")
        tampered_result = powershell(install_root / "uninstall.ps1", install_root)
        digest_mismatch_rejected = (
            tampered_result.returncode != 0
            and "digest mismatch: tools/igd.py" in (tampered_result.stderr + tampered_result.stdout)
            and install_root.is_dir()
        )
        tampered_runtime.write_bytes(original_runtime)

        reparse_target = temp / "reparse-target"
        reparse_target.mkdir()
        reparse_sentinel = reparse_target / "preserved.txt"
        reparse_sentinel.write_text("preserve\n", encoding="utf-8")
        install_junction = install_root / "reparse-probe"
        junction = run(["cmd.exe", "/d", "/c", "mklink", "/J", str(install_junction), str(reparse_target)], cwd=temp)
        if junction.returncode != 0:
            raise RuntimeError(f"could not create uninstall reparse probe: {junction.stderr or junction.stdout}")
        reparse_result = powershell(install_root / "uninstall.ps1", install_root)
        reparse_rejected = (
            reparse_result.returncode != 0
            and "reparse point: reparse-probe" in (reparse_result.stderr + reparse_result.stdout)
            and reparse_sentinel.is_file()
            and install_root.is_dir()
        )
        install_junction.rmdir()

        runtime_immutable = runtime_digest_after_install == tree_digest(install_root)
        bytecode_absent = not any(path.name == "__pycache__" or path.suffix.lower() in {".pyc", ".pyo"} for path in install_root.rglob("*"))

        uninstalled = powershell(install_root / "uninstall.ps1", install_root)
        if uninstalled.returncode != 0:
            raise RuntimeError(f"uninstaller failed: {uninstalled.stderr or uninstalled.stdout}")
        checks = {
            "firstBundleBuilt": first_build["result"] == "pass",
            "secondBundleBuilt": second_build["result"] == "pass",
            "repeatArchiveByteIdentical": repeat_archive_identical,
            "pathShadowingRejected": path_shadowing_rejected,
            "defaultPathResolutionPassed": default_path_resolution,
            "installedDoctorPassed": doctor.get("result") == "pass",
            "installedProjectCreated": prepared.get("action") == "created",
            "installedWorkbenchServed": launch.get("result") == "serving" and bool(projection["graph"]["nodes"]),
            "automaticPortAssigned": isinstance(launch.get("port"), int) and launch["port"] > 0,
            "browserSuppressed": launch.get("browserRequested") is False,
            "installedServerProcessObserved": installed_server_process_observed,
            "installedProcessCleanupVerified": installed_process_cleanup_verified,
            "installedProcessInventorySucceeded": installed_process_inventory_succeeded,
            "installedPortClosed": installed_port_closed,
            "installedSessionLockReleased": session_lock_released,
            "runtimeTreeImmutableDuringExecution": runtime_immutable,
            "runtimeBytecodeAbsent": bytecode_absent,
            "unknownInstallFileRejected": unknown_file_rejected,
            "unknownInstallDirectoryRejected": unknown_directory_rejected,
            "tamperedManifestFileRejected": digest_mismatch_rejected,
            "installReparsePointRejected": reparse_rejected,
            "reparseTargetPreserved": reparse_sentinel.is_file(),
            "runtimeRemoved": not install_root.exists(),
            "userDataPreserved": sentinel.is_file(),
            "sourceTreeUnchanged": source_before == tree_digest(FIXTURE),
            "processPathUnchanged": user_path_before == os.environ.get("PATH", ""),
        }
        if not all(checks.values()):
            raise RuntimeError("one or more install smoke checks failed")
        report = {
            "artifactRole": "intentgraph-windows-local-install-smoke-report",
            "status": "intentgraph-windows-local-install-smoke-passed",
            "scope": "p9.34-windows-local-portable-distribution",
            "result": "pass",
            "bundle": {
                "fileCount": first_build["fileCount"],
                "archiveSha256": first_build["archiveSha256"],
                "repeatArchiveByteIdentical": repeat_archive_identical,
            },
            "launch": {
                "productVersion": doctor["productVersion"],
                "projectAction": prepared["action"],
                "sourceFileCount": prepared["sourceFileCount"],
                "loopbackHost": launch["host"],
                "portAssigned": True,
                "graphNodeCount": len(projection["graph"]["nodes"]),
                "graphEdgeCount": len(projection["graph"]["edges"]),
                "observedProcessCount": len(observed_launch_processes),
                "cleanupVerified": installed_process_cleanup_verified,
            },
            "checks": checks,
            "authority": {
                "targetRepositoryMutation": False,
                "networkRequired": False,
                "downloadPerformed": False,
                "pathUpdated": False,
                "artifactSigned": False,
                "releasePublished": False,
            },
        }

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"result": "pass", "out": out.as_posix(), "checks": len(checks)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
