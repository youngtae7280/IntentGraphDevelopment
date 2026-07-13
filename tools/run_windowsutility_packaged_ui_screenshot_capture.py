"""Capture a bounded screenshot of the packaged WindowsUtility app window."""

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


REPO_ROOT = Path(__file__).resolve().parents[1]
TARGET_ROOT = Path(r"C:\Users\ytkim\Desktop\kyt_work\WindowsUtility")
EXTRACTION_REPORT = REPO_ROOT / "generated/windowsutility/package-artifact/p8.107/extraction-inventory-report.json"
LAUNCH_SMOKE_REPORT = REPO_ROOT / "generated/windowsutility/package-artifact/p8.114/launch-smoke-report.json"
AUTHORIZATION_RECORD = REPO_ROOT / "generated/roadmap/p8.119-packaged-ui-screenshot-authorization-response-record.json"
CAPTURE_SANDBOX = REPO_ROOT / ".tmp/p8.120-windowsutility-packaged-ui-screenshot"
P8_120_OUTPUT_DIR = REPO_ROOT / "generated/windowsutility/package-artifact/p8.120"
SCREENSHOT = P8_120_OUTPUT_DIR / "packaged-ui-screenshot.png"
STDOUT_LOG = P8_120_OUTPUT_DIR / "screenshot-stdout.log"
STDERR_LOG = P8_120_OUTPUT_DIR / "screenshot-stderr.log"
AUTHORIZATION_TOKEN = "accept-sandboxed-packaged-ui-screenshot-capture"
OBSERVATION_SECONDS = 5


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
    safe_dir = str(target_root).replace("\\", "/")
    result = subprocess.run(
        ["git", "-c", f"safe.directory={safe_dir}", "-C", str(target_root), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return result.stdout.strip()


def ensure_under_repo_tmp(path: Path) -> Path:
    resolved = path.resolve()
    tmp_root = (REPO_ROOT / ".tmp").resolve()
    if resolved != tmp_root and tmp_root not in resolved.parents:
        raise ValueError(f"{path} must resolve under {tmp_root}")
    return resolved


def prepare_capture_sandbox(verified_extraction_root: Path) -> None:
    sandbox = ensure_under_repo_tmp(CAPTURE_SANDBOX)
    if sandbox.exists():
        shutil.rmtree(sandbox)
    sandbox.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(verified_extraction_root, sandbox)


def verify_extracted_files(extraction_report: dict[str, Any], extraction_root: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for entry in extraction_report.get("extractionInventory", {}).get("sampleEntries", []):
        rel = entry.get("path")
        if not isinstance(rel, str):
            continue
        path = extraction_root / rel
        if not path.exists():
            results.append({"path": rel, "result": "missing"})
            continue
        actual_digest = sha256_file(path)
        actual_length = path.stat().st_size
        expected_digest = entry.get("sha256")
        expected_length = entry.get("byteLength")
        results.append(
            {
                "path": rel,
                "result": "pass" if actual_digest == expected_digest and actual_length == expected_length else "fail",
                "actualByteLength": actual_length,
                "actualSha256": actual_digest,
                "expectedByteLength": expected_length,
                "expectedSha256": expected_digest,
            }
        )
    return results


def query_process(pid: int) -> dict[str, Any]:
    script = (
        f"$p = Get-Process -Id {pid} -ErrorAction SilentlyContinue; "
        "if ($null -eq $p) { @{ found = $false } | ConvertTo-Json -Compress } "
        "else { @{ found = $true; id = $p.Id; processName = $p.ProcessName; "
        "mainWindowTitle = $p.MainWindowTitle; responding = $p.Responding; "
        "mainWindowHandle = $p.MainWindowHandle } | ConvertTo-Json -Compress }"
    )
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=10,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        return {"found": False, "queryError": completed.stderr.strip()}
    data = json.loads(completed.stdout)
    return data if isinstance(data, dict) else {"found": False, "queryError": "unexpected powershell output"}


def ps_quote(path: Path) -> str:
    return "'" + str(path).replace("'", "''") + "'"


def capture_window(pid: int, screenshot_path: Path) -> dict[str, Any]:
    screenshot_path.parent.mkdir(parents=True, exist_ok=True)
    if screenshot_path.exists():
        screenshot_path.unlink()
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
  [DllImport("user32.dll")]
  public static extern bool SetForegroundWindow(IntPtr hWnd);
  [DllImport("user32.dll")]
  public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
  [DllImport("user32.dll")]
  public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdcBlt, int nFlags);
}}
"@
$p = Get-Process -Id {pid} -ErrorAction SilentlyContinue
if ($null -eq $p) {{ @{{ captured = $false; error = "process-not-found" }} | ConvertTo-Json -Compress; exit 0 }}
$handle = $p.MainWindowHandle
if ($handle -eq 0) {{ @{{ captured = $false; error = "main-window-handle-missing" }} | ConvertTo-Json -Compress; exit 0 }}
[Win32Capture]::ShowWindow($handle, 5) | Out-Null
[Win32Capture]::SetForegroundWindow($handle) | Out-Null
Start-Sleep -Milliseconds 750
$rect = New-Object Win32Capture+RECT
$ok = [Win32Capture]::GetWindowRect($handle, [ref]$rect)
if (-not $ok) {{ @{{ captured = $false; error = "get-window-rect-failed" }} | ConvertTo-Json -Compress; exit 0 }}
$width = $rect.Right - $rect.Left
$height = $rect.Bottom - $rect.Top
if ($width -le 0 -or $height -le 0) {{ @{{ captured = $false; error = "invalid-window-rect"; width = $width; height = $height }} | ConvertTo-Json -Compress; exit 0 }}
$bitmap = New-Object System.Drawing.Bitmap($width, $height)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$hdc = $graphics.GetHdc()
$printed = [Win32Capture]::PrintWindow($handle, $hdc, 2)
$graphics.ReleaseHdc($hdc)
$captureMethod = "print-window"
if (-not $printed) {{
  $graphics.CopyFromScreen($rect.Left, $rect.Top, 0, 0, $bitmap.Size)
  $captureMethod = "copy-from-screen-fallback"
}}
$bitmap.Save({ps_quote(screenshot_path)}, [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$bitmap.Dispose()
@{{ captured = $true; left = $rect.Left; top = $rect.Top; width = $width; height = $height; path = {ps_quote(screenshot_path)}; captureMethod = $captureMethod; printWindowSucceeded = $printed }} | ConvertTo-Json -Compress
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
    parser = argparse.ArgumentParser(description="Capture a screenshot of the packaged WindowsUtility app window.")
    parser.add_argument("--authorization-token", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--keep-sandbox", action="store_true")
    args = parser.parse_args()

    errors: list[str] = []
    extraction_report = read_json(EXTRACTION_REPORT)
    launch_smoke_report = read_json(LAUNCH_SMOKE_REPORT)
    authorization_record = read_json(AUTHORIZATION_RECORD)

    if args.authorization_token != AUTHORIZATION_TOKEN:
        errors.append("authorization token does not match packaged UI screenshot capture contract")
    if authorization_record.get("acceptedResponse") != "accept sandboxed packaged UI screenshot capture":
        errors.append("exact packaged UI screenshot accepted response is not recorded")
    if authorization_record.get("authorizationState", {}).get("packagedUiScreenshotCaptureAllowedForNextVerifierRun") is not True:
        errors.append("screenshot authorization record does not allow next verifier run")
    if extraction_report.get("result") != "pass":
        errors.append("source extraction inventory report did not pass")
    if launch_smoke_report.get("result") != "pass":
        errors.append("source packaged executable launch smoke report did not pass")

    before_status = run_git(TARGET_ROOT, "status", "--short", "--branch")
    before_head = run_git(TARGET_ROOT, "rev-parse", "HEAD")
    before_origin = run_git(TARGET_ROOT, "rev-parse", "origin/main")
    if before_status != "## main...origin/main":
        errors.append("target is not clean/aligned before packaged UI screenshot capture")

    source_extract_root = REPO_ROOT / extraction_report.get("extractionInventory", {}).get("extractRoot", "")
    source_extract_root = source_extract_root.resolve()
    if not source_extract_root.exists():
        errors.append("verified extraction root is missing")

    source_file_results: list[dict[str, Any]] = []
    sandbox_file_results: list[dict[str, Any]] = []
    launch: dict[str, Any] = {
        "attempted": False,
        "started": False,
        "pid": None,
        "initialExitCode": None,
        "observationSeconds": OBSERVATION_SECONDS,
        "processObservation": {},
        "screenshotCapture": {},
        "termination": {},
        "stdoutLog": None,
        "stderrLog": None,
    }

    if not errors:
        source_file_results = verify_extracted_files(extraction_report, source_extract_root)
        if any(item.get("result") != "pass" for item in source_file_results):
            errors.append("verified extraction root files do not match P8.107 extraction report")

    if not errors:
        prepare_capture_sandbox(source_extract_root)
        sandbox_file_results = verify_extracted_files(extraction_report, CAPTURE_SANDBOX)
        if any(item.get("result") != "pass" for item in sandbox_file_results):
            errors.append("capture sandbox files do not match P8.107 extraction report")

    app_exe = CAPTURE_SANDBOX / "WindowsUtility.App.exe"
    if not errors:
        if not app_exe.exists():
            errors.append("packaged executable missing from capture sandbox")
        else:
            P8_120_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            launch["attempted"] = True
            launch["stdoutLog"] = str(STDOUT_LOG.relative_to(REPO_ROOT)).replace("\\", "/")
            launch["stderrLog"] = str(STDERR_LOG.relative_to(REPO_ROOT)).replace("\\", "/")
            with STDOUT_LOG.open("wb") as stdout_handle, STDERR_LOG.open("wb") as stderr_handle:
                process = subprocess.Popen(
                    [str(app_exe)],
                    cwd=str(app_exe.parent),
                    stdout=stdout_handle,
                    stderr=stderr_handle,
                )
                launch["started"] = True
                launch["pid"] = process.pid
                time.sleep(OBSERVATION_SECONDS)
                launch["initialExitCode"] = process.poll()
                launch["processObservation"] = query_process(process.pid)
                if launch["initialExitCode"] is None and launch["processObservation"].get("found") is True:
                    launch["screenshotCapture"] = capture_window(process.pid, SCREENSHOT)
                launch["termination"] = close_process(process.pid)
            launch["stdoutLogByteLength"] = STDOUT_LOG.stat().st_size if STDOUT_LOG.exists() else None
            launch["stderrLogByteLength"] = STDERR_LOG.stat().st_size if STDERR_LOG.exists() else None
            launch["stdoutLogSha256"] = sha256_file(STDOUT_LOG) if STDOUT_LOG.exists() else None
            launch["stderrLogSha256"] = sha256_file(STDERR_LOG) if STDERR_LOG.exists() else None
            if launch["initialExitCode"] is not None:
                errors.append("packaged executable exited before screenshot capture")
            if launch["processObservation"].get("found") is not True:
                errors.append("packaged executable process could not be observed")
            if launch["screenshotCapture"].get("captured") is not True:
                errors.append("packaged UI screenshot capture failed")
            if launch["termination"].get("exited") is not True:
                errors.append("packaged executable process did not terminate")

    screenshot = png_info(SCREENSHOT)
    if screenshot.get("validPng") is not True:
        errors.append("screenshot artifact is not a valid PNG")
    if screenshot.get("byteLength", 0) <= 10000:
        errors.append("screenshot artifact is unexpectedly small")
    if screenshot.get("width", 0) <= 100 or screenshot.get("height", 0) <= 100:
        errors.append("screenshot dimensions are unexpectedly small")

    after_status = run_git(TARGET_ROOT, "status", "--short", "--branch")
    after_head = run_git(TARGET_ROOT, "rev-parse", "HEAD")
    after_origin = run_git(TARGET_ROOT, "rev-parse", "origin/main")
    if after_status != before_status:
        errors.append("target git status changed after packaged UI screenshot capture")
    if after_head != before_head or after_origin != before_origin:
        errors.append("target git refs changed after packaged UI screenshot capture")

    sandbox_removed = False
    if not args.keep_sandbox and CAPTURE_SANDBOX.exists():
        shutil.rmtree(ensure_under_repo_tmp(CAPTURE_SANDBOX), ignore_errors=True)
        sandbox_removed = not CAPTURE_SANDBOX.exists()

    result = "pass" if not errors else "fail"
    report = {
        "artifactRole": "intentgraph-packaged-ui-screenshot-capture-report",
        "status": "intentgraph-packaged-ui-screenshot-capture-passed" if result == "pass" else "intentgraph-packaged-ui-screenshot-capture-failed",
        "scope": "p8.120-packaged-ui-screenshot-capture-verification",
        "workItem": "P8.120 Packaged UI Screenshot Capture Verification",
        "date": "2026-07-13",
        "result": result,
        "sourceReports": {
            "authorization": str(AUTHORIZATION_RECORD.relative_to(REPO_ROOT)).replace("\\", "/"),
            "extractionInventory": str(EXTRACTION_REPORT.relative_to(REPO_ROOT)).replace("\\", "/"),
            "launchSmoke": str(LAUNCH_SMOKE_REPORT.relative_to(REPO_ROOT)).replace("\\", "/"),
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
        "sandbox": {
            "sourceExtractionRoot": str(source_extract_root.relative_to(REPO_ROOT)).replace("\\", "/") if source_extract_root.exists() else str(source_extract_root),
            "captureSandboxRoot": str(CAPTURE_SANDBOX.relative_to(REPO_ROOT)).replace("\\", "/"),
            "copiedVerifiedExtractionToCaptureSandbox": bool(sandbox_file_results),
            "packageExtractionPerformedByThisRun": False,
            "writesConfinedToSandbox": True,
            "retained": args.keep_sandbox,
            "removedAfterRun": sandbox_removed,
        },
        "sourceExtractionFileResults": source_file_results,
        "captureSandboxFileResults": sandbox_file_results,
        "launchAndCapture": launch,
        "screenshotEvidence": screenshot | {
            "path": str(SCREENSHOT.relative_to(REPO_ROOT)).replace("\\", "/"),
        },
        "boundary": {
            "artifactSigned": False,
            "credentialAccessed": False,
            "installerCreated": False,
            "packagedExecutableLaunched": launch["started"],
            "packagedUiWindowObserved": bool(launch["processObservation"].get("mainWindowTitle")),
            "packagedUiScreenshotCaptured": bool(screenshot.get("validPng")),
            "productCandidateAccepted": False,
            "productizationClaimed": False,
            "providerApiCalled": False,
            "releasePublished": False,
        },
        "authorizationBoundary": {
            "authorizationTokenAccepted": args.authorization_token == AUTHORIZATION_TOKEN,
            "sourceEditsAuthorized": False,
            "targetWritesAuthorized": False,
            "sandboxWritesAuthorizedForThisProbe": True,
            "packagedExecutableLaunchAuthorizedForThisProbe": True,
            "screenshotCaptureAuthorizedForThisProbe": True,
            "installerCreationAuthorized": False,
            "artifactSigningAuthorized": False,
            "releaseAuthorized": False,
            "productizationAuthorized": False,
        },
        "errors": errors,
    }
    write_json(args.out, report)
    return 0 if result == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
