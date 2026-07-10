"""Run a synthetic readiness check for the package extraction inventory verifier."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any


WORK_ITEM = "P8.69 Sandboxed Package Extraction Inventory Verifier Readiness"
SCOPE = "p8.69-sandboxed-package-extraction-inventory-verifier-readiness"
DATE = "2026-07-10"
DEFAULT_OUT = Path("generated/windowsutility/package-artifact/p8.69/synthetic-tool-readiness-report.json")
VERIFY_TOOL = Path("tools/verify_windowsutility_package_extraction_inventory.py")
AUTHORIZATION_TOKEN = "accept-sandboxed-package-extraction-inventory-verification"
REQUIRED_ENTRIES = [
    "WindowsUtility.App.exe",
    "WindowsUtility.App.dll",
    "SmartComm2.dll",
]


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def digest_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def digest_file(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def create_synthetic_package(path: Path) -> list[str]:
    entries = {
        "WindowsUtility.App.exe": b"synthetic executable marker only\n",
        "WindowsUtility.App.dll": b"synthetic app dll marker only\n",
        "SmartComm2.dll": b"synthetic smartcomm marker only\n",
        "WindowsUtility.Shell.dll": b"synthetic shell marker only\n",
    }
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(entries.items()):
            info = zipfile.ZipInfo(name)
            info.date_time = (2026, 7, 10, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, content)
    return sorted(entries)


def create_sources(package: Path, manifest: Path, metadata_replay: Path, names: list[str]) -> None:
    artifact = {
        "path": "synthetic-package.zip",
        "sha256": digest_file(package),
        "byteLength": package.stat().st_size,
        "fileCount": len(names),
        "zipReadable": True,
        "containsWindowsUtilityAppExe": True,
        "containsSmartComm2Dll": True,
        "sampleEntries": names,
    }
    write_json(
        manifest,
        {
            "artifactRole": "intentgraph-windowsutility-synthetic-package-artifact-manifest",
            "status": "intentgraph-windowsutility-synthetic-package-artifact-manifest-recorded",
            "scope": SCOPE,
        "date": DATE,
        "artifact": artifact,
            "productizationClaimed": False,
            "artifactSigned": False,
            "releasePublished": False,
        },
    )
    write_json(
        metadata_replay,
        {
            "artifactRole": "intentgraph-packaged-artifact-metadata-replay-report",
            "status": "intentgraph-packaged-artifact-metadata-replay-passed",
            "scope": SCOPE,
            "date": DATE,
            "result": "pass",
            "packageArtifactReplay": artifact,
            "boundary": {
                "packageExtractionPerformed": False,
                "packagedExecutableLaunched": False,
                "packagedUiLaunched": False,
                "installerCreated": False,
                "artifactSigned": False,
                "credentialAccessed": False,
                "providerApiCalled": False,
                "releasePublished": False,
                "productizationClaimed": False,
            },
        },
    )


def run_synthetic_verifier(tmp_root: Path) -> tuple[int, dict[str, Any]]:
    package = tmp_root / "synthetic-package.zip"
    manifest = tmp_root / "package-manifest.json"
    metadata_replay = tmp_root / "metadata-replay-report.json"
    extract_root = tmp_root / "extract-root"
    out = tmp_root / "extraction-inventory-report.json"
    names = create_synthetic_package(package)
    create_sources(package, manifest, metadata_replay, names)
    command = [
        sys.executable,
        str(VERIFY_TOOL),
        "--package",
        str(package),
        "--manifest",
        str(manifest),
        "--metadata-replay",
        str(metadata_replay),
        "--extract-root",
        str(extract_root),
        "--out",
        str(out),
        "--authorization-token",
        AUTHORIZATION_TOKEN,
        "--scope",
        SCOPE,
        "--verification-mode",
        "synthetic-tool-readiness-only",
    ]
    completed = subprocess.run(command, check=False, text=True, capture_output=True)
    report = read_json(out) if out.exists() else {}
    report = scrub_temp_paths(report, tmp_root)
    report["verifierExitCode"] = completed.returncode
    report["verifierStdout"] = completed.stdout
    report["verifierStderr"] = completed.stderr
    return completed.returncode, report


def scrub_temp_paths(value: Any, tmp_root: Path) -> Any:
    if isinstance(value, dict):
        return {key: scrub_temp_paths(item, tmp_root) for key, item in value.items()}
    if isinstance(value, list):
        return [scrub_temp_paths(item, tmp_root) for item in value]
    if isinstance(value, str):
        normalized = value.replace("\\", "/")
        tmp_normalized = tmp_root.as_posix()
        return normalized.replace(tmp_normalized, "<synthetic-temp>")
    return value


def build_report() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="intentgraph-p8.69-synthetic-") as tmp:
        exit_code, verifier_report = run_synthetic_verifier(Path(tmp))

    result = "pass" if exit_code == 0 and verifier_report.get("result") == "pass" else "fail"
    return {
        "artifactRole": "intentgraph-packaged-artifact-extraction-inventory-tool-readiness-report",
        "status": "intentgraph-packaged-artifact-extraction-inventory-tool-readiness-passed"
        if result == "pass"
        else "intentgraph-packaged-artifact-extraction-inventory-tool-readiness-failed",
        "scope": SCOPE,
        "workItem": WORK_ITEM,
        "date": DATE,
        "result": result,
        "verifierReport": verifier_report,
        "readinessAssertions": {
            "syntheticPackageOnly": True,
            "existingWindowsUtilityPackageExtracted": False,
            "authorizationTokenRequired": True,
            "sandboxExtractionSupported": verifier_report.get("boundary", {}).get("packageExtractionPerformed") is True,
            "extractedInventoryComparedToZipInventory": verifier_report.get("zipInventory", {}).get("fileCount")
            == verifier_report.get("extractionInventory", {}).get("fileCount"),
        },
        "boundary": {
            "existingPackageExtractionPerformed": False,
            "syntheticPackageExtractionPerformed": verifier_report.get("boundary", {}).get("packageExtractionPerformed") is True,
            "packagedExecutableLaunched": False,
            "packagedUiLaunched": False,
            "packagedUiScreenshotCaptured": False,
            "installerCreated": False,
            "artifactSigned": False,
            "credentialAccessed": False,
            "providerApiCalled": False,
            "releasePublished": False,
            "productizationClaimed": False,
        },
        "recommendedNextSlice": "P8.70 Packaged Artifact Extraction Inventory Negative Probes",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run P8.69 synthetic package extraction verifier readiness.")
    parser.add_argument("--out", default=DEFAULT_OUT, type=Path)
    args = parser.parse_args()
    report = build_report()
    write_json(args.out, report)
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
