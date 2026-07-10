"""Run a sandboxed WindowsUtility UI launch feasibility probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
TARGET_ROOT = Path(r"C:\Users\ytkim\Desktop\kyt_work\WindowsUtility")
SANDBOX_ROOT = Path(r"C:\Users\ytkim\Desktop\kyt_work\WindowsUtility-p8.17-ui")
PROPOSAL = REPO_ROOT / "generated/windowsutility/p8.12-shell-workspace-smoke-evidence-non-applied-proposal.json"
BUILD_LOG = REPO_ROOT / "generated/windowsutility/p8.17-sandboxed-ui-launch-build.log"


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def run_git(target_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(target_root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def ignore_for_sandbox(dir_path: str, names: list[str]) -> set[str]:
    ignored = set()
    for name in names:
        if name in {".git", ".vs", "bin", "obj"}:
            ignored.add(name)
    return ignored


def copy_sandbox() -> None:
    if SANDBOX_ROOT.exists():
        shutil.rmtree(SANDBOX_ROOT)
    SANDBOX_ROOT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(TARGET_ROOT, SANDBOX_ROOT, ignore=ignore_for_sandbox)


def run_build() -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["DOTNET_CLI_UI_LANGUAGE"] = "en"
    return subprocess.run(
        ["dotnet", "build", "WindowsUtility.sln", "--nologo"],
        cwd=str(SANDBOX_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=240,
    )


def source_ref_results(proposal: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    results = []
    for ref in proposal.get("impactScope", {}).get("codeSurfaceRefs", []):
        rel = ref.get("path")
        path = root / rel
        if not path.exists():
            results.append({"path": rel, "result": "missing"})
            continue
        digest = sha256_file(path)
        byte_length = path.stat().st_size
        results.append(
            {
                "path": rel,
                "result": "pass" if digest == ref.get("digest") and byte_length == ref.get("byteLength") else "fail",
                "actualDigest": digest,
                "expectedDigest": ref.get("digest"),
                "actualByteLength": byte_length,
                "expectedByteLength": ref.get("byteLength"),
            }
        )
    return results


def query_process(pid: int) -> dict[str, Any]:
    script = (
        f"$p = Get-Process -Id {pid} -ErrorAction SilentlyContinue; "
        "if ($null -eq $p) { @{ found = $false } | ConvertTo-Json -Compress } "
        "else { @{ found = $true; id = $p.Id; processName = $p.ProcessName; "
        "mainWindowTitle = $p.MainWindowTitle; responding = $p.Responding } | ConvertTo-Json -Compress }"
    )
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        return {"found": False, "queryError": completed.stderr.strip()}
    data = json.loads(completed.stdout)
    return data if isinstance(data, dict) else {"found": False, "queryError": "unexpected powershell output"}


def close_process(pid: int) -> dict[str, Any]:
    script = (
        f"$p = Get-Process -Id {pid} -ErrorAction SilentlyContinue; "
        "if ($null -eq $p) { @{ found = $false; exited = $true; method = 'already-exited' } | ConvertTo-Json -Compress; exit 0 }; "
        "$closed = $p.CloseMainWindow(); Start-Sleep -Seconds 2; $p.Refresh(); "
        "if (-not $p.HasExited) { $p.Kill(); $p.WaitForExit(5000); $p.Refresh(); $method = 'kill-after-close-window-timeout' } "
        "else { $method = 'close-main-window' }; "
        "@{ found = $true; closeMainWindowReturned = $closed; exited = $p.HasExited; method = $method } | ConvertTo-Json -Compress"
    )
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=15,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        return {"found": False, "exited": False, "method": "close-query-failed", "error": completed.stderr.strip()}
    data = json.loads(completed.stdout)
    return data if isinstance(data, dict) else {"found": False, "exited": False, "method": "unexpected-output"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run sandboxed WindowsUtility UI launch probe.")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--keep-sandbox", action="store_true")
    args = parser.parse_args()

    proposal = read_json(PROPOSAL)
    errors: list[str] = []

    before_status = run_git(TARGET_ROOT, "status", "--short", "--branch")
    before_head = run_git(TARGET_ROOT, "rev-parse", "HEAD")
    before_origin = run_git(TARGET_ROOT, "rev-parse", "origin/main")
    if before_status != "## main...origin/main":
        errors.append("target is not clean/aligned before UI launch probe")

    copy_sandbox()
    sandbox_ref_results = source_ref_results(proposal, SANDBOX_ROOT)
    if any(item.get("result") != "pass" for item in sandbox_ref_results):
        errors.append("sandbox source refs do not match proposal baseline")

    build = run_build()
    stdout = build.stdout or ""
    stderr = build.stderr or ""
    BUILD_LOG.parent.mkdir(parents=True, exist_ok=True)
    BUILD_LOG.write_text(
        (
            "COMMAND: dotnet build WindowsUtility.sln --nologo\n"
            f"EXIT CODE: {build.returncode}\n\n"
            "STDOUT:\n"
            f"{stdout}\n\n"
            "STDERR:\n"
            f"{stderr}"
        ).rstrip()
        + "\n",
        encoding="utf-8",
    )
    if build.returncode != 0:
        errors.append("sandbox dotnet build failed")

    app_exe = SANDBOX_ROOT / "src/WindowsUtility.App/bin/Debug/net9.0-windows/WindowsUtility.App.exe"
    launch: dict[str, Any] = {
        "path": str(app_exe),
        "attempted": False,
        "started": False,
        "pid": None,
        "initialExitCode": None,
        "processObservation": {},
        "termination": {},
    }
    if not app_exe.exists():
        errors.append("sandbox app executable missing after build")
    elif build.returncode == 0:
        launch["attempted"] = True
        process = subprocess.Popen(
            [str(app_exe)],
            cwd=str(app_exe.parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        launch["started"] = True
        launch["pid"] = process.pid
        time.sleep(5)
        launch["initialExitCode"] = process.poll()
        launch["processObservation"] = query_process(process.pid)
        launch["termination"] = close_process(process.pid)
        if launch["initialExitCode"] is not None:
            errors.append("sandbox app exited before observation window completed")
        if launch["processObservation"].get("found") is not True and launch["initialExitCode"] is None:
            errors.append("sandbox app process could not be observed")
        if launch["termination"].get("exited") is not True:
            errors.append("sandbox app process did not terminate")

    after_status = run_git(TARGET_ROOT, "status", "--short", "--branch")
    after_head = run_git(TARGET_ROOT, "rev-parse", "HEAD")
    after_origin = run_git(TARGET_ROOT, "rev-parse", "origin/main")
    if after_status != before_status:
        errors.append("target git status changed after UI launch probe")
    if after_head != before_head or after_origin != before_origin:
        errors.append("target git refs changed after UI launch probe")

    sandbox_removed = False
    if not args.keep_sandbox:
        shutil.rmtree(SANDBOX_ROOT, ignore_errors=True)
        sandbox_removed = not SANDBOX_ROOT.exists()

    result = "pass" if not errors else "fail"
    report = {
        "artifactRole": "intentgraph-windowsutility-sandboxed-ui-launch-probe-report",
        "status": "intentgraph-windowsutility-sandboxed-ui-launch-probe-passed" if result == "pass" else "intentgraph-windowsutility-sandboxed-ui-launch-probe-failed",
        "scope": "p8.17-shell-workspace-sandboxed-ui-launch-feasibility-probe",
        "workItem": "P8.17 Shell Workspace Sandboxed UI Launch Feasibility Probe",
        "result": result,
        "proposal": str(PROPOSAL.relative_to(REPO_ROOT)).replace("\\", "/"),
        "sandbox": {
            "path": str(SANDBOX_ROOT),
            "writesConfinedToSandbox": True,
            "retained": args.keep_sandbox,
            "removedAfterRun": sandbox_removed,
        },
        "targetBefore": {
            "status": before_status,
            "head": before_head,
            "originMain": before_origin,
        },
        "targetAfter": {
            "status": after_status,
            "head": after_head,
            "originMain": after_origin,
        },
        "sourceRefResults": sandbox_ref_results,
        "build": {
            "command": "dotnet build WindowsUtility.sln --nologo",
            "exitCode": build.returncode,
            "log": str(BUILD_LOG.relative_to(REPO_ROOT)).replace("\\", "/"),
            "stdoutLineCount": len(stdout.splitlines()),
            "stderrLineCount": len(stderr.splitlines()),
        },
        "uiLaunch": launch,
        "screenshotEvidence": {
            "attempted": False,
            "captured": False,
            "reason": "P8.17 verifies launch feasibility only; screenshot capture remains a later bounded evidence slice.",
        },
        "authorizations": {
            "sourceEditsAuthorized": False,
            "proposalApplicationAuthorized": False,
            "targetWritesAuthorized": False,
            "sandboxWritesAuthorizedForThisProbe": True,
            "uiLaunchAuthorizedForThisProbe": True,
            "aiAuthorityPromoted": False,
            "hardwareActionsAuthorized": False,
            "productizationAuthorized": False,
        },
        "errors": errors,
    }
    write_json(args.out, report)
    return 0 if result == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
