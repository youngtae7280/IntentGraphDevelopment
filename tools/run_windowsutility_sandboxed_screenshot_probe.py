"""Capture a screenshot of the sandboxed WindowsUtility app window."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import time
from pathlib import Path
from typing import Any

import run_windowsutility_sandboxed_ui_launch_probe as ui_probe


REPO_ROOT = Path(__file__).resolve().parents[1]
SANDBOX_ROOT = Path(r"C:\Users\ytkim\Desktop\kyt_work\WindowsUtility-p8.19-screenshot")
BUILD_LOG = REPO_ROOT / "generated/windowsutility/p8.19-sandboxed-screenshot-build.log"
SCREENSHOT = REPO_ROOT / "generated/windowsutility/p8.19-shell-workspace-sandboxed-window.png"


ui_probe.SANDBOX_ROOT = SANDBOX_ROOT
ui_probe.BUILD_LOG = BUILD_LOG


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def ps_quote(path: Path) -> str:
    return "'" + str(path).replace("'", "''") + "'"


def capture_window(pid: int, screenshot_path: Path) -> dict[str, Any]:
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    script = f"""
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32Capture {{
  [StructLayout(LayoutKind.Sequential)]
  public struct RECT {{
    public int Left;
    public int Top;
    public int Right;
    public int Bottom;
  }}
  [DllImport("user32.dll")]
  public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
}}
"@
$p = Get-Process -Id {pid} -ErrorAction SilentlyContinue
if ($null -eq $p) {{ @{{ captured = $false; error = "process-not-found" }} | ConvertTo-Json -Compress; exit 0 }}
$handle = $p.MainWindowHandle
if ($handle -eq 0) {{ @{{ captured = $false; error = "main-window-handle-missing" }} | ConvertTo-Json -Compress; exit 0 }}
$rect = New-Object Win32Capture+RECT
$ok = [Win32Capture]::GetWindowRect($handle, [ref]$rect)
if (-not $ok) {{ @{{ captured = $false; error = "get-window-rect-failed" }} | ConvertTo-Json -Compress; exit 0 }}
$width = $rect.Right - $rect.Left
$height = $rect.Bottom - $rect.Top
if ($width -le 0 -or $height -le 0) {{ @{{ captured = $false; error = "invalid-window-rect"; width = $width; height = $height }} | ConvertTo-Json -Compress; exit 0 }}
$bitmap = New-Object System.Drawing.Bitmap($width, $height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$graphics.CopyFromScreen($rect.Left, $rect.Top, 0, 0, $bitmap.Size)
$bitmap.Save({ps_quote(screenshot_path)}, [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bitmap.Dispose()
@{{ captured = $true; left = $rect.Left; top = $rect.Top; width = $width; height = $height; path = {ps_quote(screenshot_path)} }} | ConvertTo-Json -Compress
"""
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        return {"captured": False, "error": completed.stderr.strip() or "capture-command-failed"}
    data = json.loads(completed.stdout)
    return data if isinstance(data, dict) else {"captured": False, "error": "unexpected capture output"}


def png_info(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False, "validPng": False}
    data = path.read_bytes()
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return {"exists": True, "validPng": False, "byteLength": len(data)}
    width, height = struct.unpack(">II", data[16:24])
    return {
        "exists": True,
        "validPng": True,
        "byteLength": len(data),
        "width": width,
        "height": height,
        "sha256": sha256_file(path),
    }


def write_build_log(build: subprocess.CompletedProcess[str]) -> None:
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Run sandboxed WindowsUtility screenshot probe.")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--keep-sandbox", action="store_true")
    args = parser.parse_args()

    proposal = ui_probe.read_json(ui_probe.PROPOSAL)
    errors: list[str] = []

    before_status = ui_probe.run_git(ui_probe.TARGET_ROOT, "status", "--short", "--branch")
    before_head = ui_probe.run_git(ui_probe.TARGET_ROOT, "rev-parse", "HEAD")
    before_origin = ui_probe.run_git(ui_probe.TARGET_ROOT, "rev-parse", "origin/main")
    if before_status != "## main...origin/main":
        errors.append("target is not clean/aligned before screenshot probe")

    ui_probe.copy_sandbox()
    sandbox_ref_results = ui_probe.source_ref_results(proposal, SANDBOX_ROOT)
    if any(item.get("result") != "pass" for item in sandbox_ref_results):
        errors.append("sandbox source refs do not match proposal baseline")

    build = ui_probe.run_build()
    write_build_log(build)
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
        "screenshotCapture": {},
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
        launch["processObservation"] = ui_probe.query_process(process.pid)
        if launch["initialExitCode"] is None and launch["processObservation"].get("found") is True:
            launch["screenshotCapture"] = capture_window(process.pid, SCREENSHOT)
        launch["termination"] = ui_probe.close_process(process.pid)
        if launch["initialExitCode"] is not None:
            errors.append("sandbox app exited before screenshot capture")
        if launch["processObservation"].get("found") is not True:
            errors.append("sandbox app process could not be observed")
        if launch["screenshotCapture"].get("captured") is not True:
            errors.append("sandbox app screenshot capture failed")
        if launch["termination"].get("exited") is not True:
            errors.append("sandbox app process did not terminate")

    screenshot = png_info(SCREENSHOT)
    if screenshot.get("validPng") is not True:
        errors.append("screenshot artifact is not a valid PNG")
    if screenshot.get("byteLength", 0) <= 10000:
        errors.append("screenshot artifact is unexpectedly small")
    if screenshot.get("width", 0) <= 100 or screenshot.get("height", 0) <= 100:
        errors.append("screenshot dimensions are unexpectedly small")

    after_status = ui_probe.run_git(ui_probe.TARGET_ROOT, "status", "--short", "--branch")
    after_head = ui_probe.run_git(ui_probe.TARGET_ROOT, "rev-parse", "HEAD")
    after_origin = ui_probe.run_git(ui_probe.TARGET_ROOT, "rev-parse", "origin/main")
    if after_status != before_status:
        errors.append("target git status changed after screenshot probe")
    if after_head != before_head or after_origin != before_origin:
        errors.append("target git refs changed after screenshot probe")

    sandbox_removed = False
    if not args.keep_sandbox:
        shutil.rmtree(SANDBOX_ROOT, ignore_errors=True)
        sandbox_removed = not SANDBOX_ROOT.exists()

    result = "pass" if not errors else "fail"
    report = {
        "artifactRole": "intentgraph-windowsutility-sandboxed-screenshot-probe-report",
        "status": "intentgraph-windowsutility-sandboxed-screenshot-probe-passed" if result == "pass" else "intentgraph-windowsutility-sandboxed-screenshot-probe-failed",
        "scope": "p8.19-shell-workspace-sandboxed-screenshot-evidence-probe",
        "workItem": "P8.19 Shell Workspace Sandboxed Screenshot Evidence Probe",
        "result": result,
        "proposal": str(ui_probe.PROPOSAL.relative_to(REPO_ROOT)).replace("\\", "/"),
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
            "stdoutLineCount": len((build.stdout or "").splitlines()),
            "stderrLineCount": len((build.stderr or "").splitlines()),
        },
        "uiLaunch": launch,
        "screenshotEvidence": screenshot,
        "authorizations": {
            "sourceEditsAuthorized": False,
            "proposalApplicationAuthorized": False,
            "targetWritesAuthorized": False,
            "sandboxWritesAuthorizedForThisProbe": True,
            "uiLaunchAuthorizedForThisProbe": True,
            "screenshotCaptureAuthorizedForThisProbe": True,
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
