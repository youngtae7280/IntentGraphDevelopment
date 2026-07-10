"""Run WindowsUtility shell/workspace smoke evidence in a disposable sandbox."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
TARGET_ROOT = Path(r"C:\Users\ytkim\Desktop\kyt_work\WindowsUtility")
SANDBOX_ROOT = Path(r"C:\Users\ytkim\Desktop\kyt_work\WindowsUtility-p8.15-smoke")
PROPOSAL = REPO_ROOT / "generated/windowsutility/p8.12-shell-workspace-smoke-evidence-non-applied-proposal.json"
BUILD_LOG = REPO_ROOT / "generated/windowsutility/p8.15-sandboxed-smoke-evidence-build.log"


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Run sandboxed WindowsUtility smoke evidence.")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--keep-sandbox", action="store_true")
    args = parser.parse_args()

    proposal = read_json(PROPOSAL)
    errors: list[str] = []

    before_status = run_git(TARGET_ROOT, "status", "--short", "--branch")
    before_head = run_git(TARGET_ROOT, "rev-parse", "HEAD")
    before_origin = run_git(TARGET_ROOT, "rev-parse", "origin/main")

    if before_status != "## main...origin/main":
        errors.append("target is not clean/aligned before sandbox run")
    if before_head != proposal.get("targetBaseline", {}).get("head"):
        errors.append("target HEAD does not match proposal baseline before sandbox run")

    copy_sandbox()
    sandbox_ref_results = source_ref_results(proposal, SANDBOX_ROOT)
    if any(item.get("result") != "pass" for item in sandbox_ref_results):
        errors.append("sandbox source refs do not match proposal baseline")

    build = run_build()
    BUILD_LOG.parent.mkdir(parents=True, exist_ok=True)
    stdout = build.stdout or ""
    stderr = build.stderr or ""
    build_log_text = (
        "COMMAND: dotnet build WindowsUtility.sln --nologo\n"
        f"EXIT CODE: {build.returncode}\n\n"
        "STDOUT:\n"
        f"{stdout}\n\n"
        "STDERR:\n"
        f"{stderr}"
    ).rstrip() + "\n"
    BUILD_LOG.write_text(build_log_text, encoding="utf-8")
    if build.returncode != 0:
        errors.append("sandbox dotnet build failed")

    after_status = run_git(TARGET_ROOT, "status", "--short", "--branch")
    after_head = run_git(TARGET_ROOT, "rev-parse", "HEAD")
    after_origin = run_git(TARGET_ROOT, "rev-parse", "origin/main")
    if after_status != before_status:
        errors.append("target git status changed after sandbox run")
    if after_head != before_head or after_origin != before_origin:
        errors.append("target git refs changed after sandbox run")

    sandbox_removed = False
    if not args.keep_sandbox:
        shutil.rmtree(SANDBOX_ROOT, ignore_errors=True)
        sandbox_removed = not SANDBOX_ROOT.exists()

    result = "pass" if not errors else "fail"
    report = {
        "artifactRole": "intentgraph-windowsutility-sandboxed-smoke-evidence-report",
        "status": "intentgraph-windowsutility-sandboxed-smoke-evidence-passed" if result == "pass" else "intentgraph-windowsutility-sandboxed-smoke-evidence-failed",
        "scope": "p8.15-shell-workspace-sandboxed-smoke-evidence-dry-run",
        "workItem": "P8.15 Shell Workspace Sandboxed Smoke Evidence Dry Run",
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
        "uiEvidence": {
            "launchAttempted": False,
            "screenshotCaptured": False,
            "reason": "P8.15 performs build-only smoke evidence first; UI launch and screenshots remain a later bounded slice.",
        },
        "authorizations": {
            "sourceEditsAuthorized": False,
            "proposalApplicationAuthorized": False,
            "targetWritesAuthorized": False,
            "sandboxWritesAuthorizedForThisDryRun": True,
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
