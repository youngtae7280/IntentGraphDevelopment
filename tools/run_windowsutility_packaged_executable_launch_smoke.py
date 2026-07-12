"""Run a bounded packaged WindowsUtility executable launch smoke."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
TARGET_ROOT = Path(r"C:\Users\ytkim\Desktop\kyt_work\WindowsUtility")
EXTRACTION_REPORT = REPO_ROOT / "generated/windowsutility/package-artifact/p8.107/extraction-inventory-report.json"
AUTHORIZATION_RECORD = (
    REPO_ROOT / "generated/roadmap/p8.113-packaged-executable-launch-smoke-authorization-response-record.json"
)
LAUNCH_SANDBOX = REPO_ROOT / ".tmp/p8.114-windowsutility-packaged-launch-smoke"
P8_114_OUTPUT_DIR = REPO_ROOT / "generated/windowsutility/package-artifact/p8.114"
AUTHORIZATION_TOKEN = "accept-sandboxed-packaged-executable-launch-smoke"
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
    result = subprocess.run(
        ["git", "-C", str(target_root), *args],
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


def prepare_launch_sandbox(verified_extraction_root: Path) -> None:
    sandbox = ensure_under_repo_tmp(LAUNCH_SANDBOX)
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
        "mainWindowTitle = $p.MainWindowTitle; responding = $p.Responding } | ConvertTo-Json -Compress }"
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
    parser = argparse.ArgumentParser(description="Run packaged WindowsUtility executable launch smoke.")
    parser.add_argument("--authorization-token", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--keep-sandbox", action="store_true")
    args = parser.parse_args()

    errors: list[str] = []
    extraction_report = read_json(EXTRACTION_REPORT)
    authorization_record = read_json(AUTHORIZATION_RECORD)

    if args.authorization_token != AUTHORIZATION_TOKEN:
        errors.append("authorization token does not match packaged executable launch smoke contract")
    if authorization_record.get("acceptedResponse") != "accept sandboxed packaged executable launch smoke":
        errors.append("exact launch smoke accepted response is not recorded")
    if (
        authorization_record.get("authorizationState", {}).get("packagedExecutableLaunchAllowedForNextVerifierRun")
        is not True
    ):
        errors.append("launch smoke authorization record does not allow next verifier run")
    if extraction_report.get("result") != "pass":
        errors.append("source extraction inventory report did not pass")

    before_status = run_git(TARGET_ROOT, "status", "--short", "--branch")
    before_head = run_git(TARGET_ROOT, "rev-parse", "HEAD")
    before_origin = run_git(TARGET_ROOT, "rev-parse", "origin/main")
    if before_status != "## main...origin/main":
        errors.append("target is not clean/aligned before packaged launch smoke")

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
        "termination": {},
        "stdoutLog": None,
        "stderrLog": None,
    }

    if not errors:
        source_file_results = verify_extracted_files(extraction_report, source_extract_root)
        if any(item.get("result") != "pass" for item in source_file_results):
            errors.append("verified extraction root files do not match P8.107 extraction report")

    if not errors:
        prepare_launch_sandbox(source_extract_root)
        sandbox_file_results = verify_extracted_files(extraction_report, LAUNCH_SANDBOX)
        if any(item.get("result") != "pass" for item in sandbox_file_results):
            errors.append("launch sandbox files do not match P8.107 extraction report")

    app_exe = LAUNCH_SANDBOX / "WindowsUtility.App.exe"
    stdout_log = P8_114_OUTPUT_DIR / "launch-stdout.log"
    stderr_log = P8_114_OUTPUT_DIR / "launch-stderr.log"
    if not errors:
        if not app_exe.exists():
            errors.append("packaged executable missing from launch sandbox")
        else:
            launch["attempted"] = True
            stdout_log.parent.mkdir(parents=True, exist_ok=True)
            launch["stdoutLog"] = str(stdout_log.relative_to(REPO_ROOT)).replace("\\", "/")
            launch["stderrLog"] = str(stderr_log.relative_to(REPO_ROOT)).replace("\\", "/")
            with stdout_log.open("wb") as stdout_handle, stderr_log.open("wb") as stderr_handle:
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
                launch["termination"] = close_process(process.pid)
            launch["stdoutLogByteLength"] = stdout_log.stat().st_size if stdout_log.exists() else None
            launch["stderrLogByteLength"] = stderr_log.stat().st_size if stderr_log.exists() else None
            launch["stdoutLogSha256"] = sha256_file(stdout_log) if stdout_log.exists() else None
            launch["stderrLogSha256"] = sha256_file(stderr_log) if stderr_log.exists() else None
            if launch["initialExitCode"] is not None:
                errors.append("packaged executable exited before observation window completed")
            if launch["processObservation"].get("found") is not True and launch["initialExitCode"] is None:
                errors.append("packaged executable process could not be observed")
            if launch["termination"].get("exited") is not True:
                errors.append("packaged executable process did not terminate")

    after_status = run_git(TARGET_ROOT, "status", "--short", "--branch")
    after_head = run_git(TARGET_ROOT, "rev-parse", "HEAD")
    after_origin = run_git(TARGET_ROOT, "rev-parse", "origin/main")
    if after_status != before_status:
        errors.append("target git status changed after packaged launch smoke")
    if after_head != before_head or after_origin != before_origin:
        errors.append("target git refs changed after packaged launch smoke")

    sandbox_removed = False
    if not args.keep_sandbox and LAUNCH_SANDBOX.exists():
        shutil.rmtree(ensure_under_repo_tmp(LAUNCH_SANDBOX), ignore_errors=True)
        sandbox_removed = not LAUNCH_SANDBOX.exists()

    result = "pass" if not errors else "fail"
    report = {
        "artifactRole": "intentgraph-packaged-executable-launch-smoke-report",
        "status": "intentgraph-packaged-executable-launch-smoke-passed"
        if result == "pass"
        else "intentgraph-packaged-executable-launch-smoke-failed",
        "scope": "p8.114-packaged-executable-launch-smoke-verification",
        "workItem": "P8.114 Packaged Executable Launch Smoke Verification",
        "date": "2026-07-13",
        "result": result,
        "sourceReports": {
            "authorization": str(AUTHORIZATION_RECORD.relative_to(REPO_ROOT)).replace("\\", "/"),
            "extractionInventory": str(EXTRACTION_REPORT.relative_to(REPO_ROOT)).replace("\\", "/"),
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
            "sourceExtractionRoot": str(source_extract_root.relative_to(REPO_ROOT)).replace("\\", "/"),
            "launchSandboxRoot": str(LAUNCH_SANDBOX.relative_to(REPO_ROOT)).replace("\\", "/"),
            "copiedVerifiedExtractionToLaunchSandbox": bool(sandbox_file_results),
            "packageExtractionPerformedByThisRun": False,
            "writesConfinedToSandbox": True,
            "retained": args.keep_sandbox,
            "removedAfterRun": sandbox_removed,
        },
        "sourceExtractionFileResults": source_file_results,
        "launchSandboxFileResults": sandbox_file_results,
        "launchSmoke": launch,
        "boundary": {
            "artifactSigned": False,
            "credentialAccessed": False,
            "installerCreated": False,
            "packagedExecutableLaunched": launch["started"],
            "packagedUiWindowObserved": bool(launch["processObservation"].get("mainWindowTitle")),
            "packagedUiScreenshotCaptured": False,
            "productCandidateAccepted": False,
            "productizationClaimed": False,
            "providerApiCalled": False,
            "releasePublished": False,
        },
        "errors": errors,
    }
    write_json(args.out, report)
    return 0 if result == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
