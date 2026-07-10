"""Replay WindowsUtility package artifact metadata without extraction or execution."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any


WORK_ITEM = "P8.66 Packaged Artifact Metadata Replay Verification"
SCOPE = "p8.66-packaged-artifact-metadata-replay-verification"
DATE = "2026-07-10"
DEFAULT_PACKAGE = Path(
    "generated/windowsutility/package-artifact/p8.55/windowsutility-shell-workspace-p8.55-sandbox-package.zip"
)
DEFAULT_MANIFEST = Path("generated/windowsutility/package-artifact/p8.55/package-manifest.json")
DEFAULT_BOUNDARY = Path("generated/roadmap/p8.56-packaged-artifact-verification-boundary-report.json")
DEFAULT_OUT = Path("generated/windowsutility/package-artifact/p8.66/metadata-replay-report.json")
REQUIRED_ENTRIES = [
    "WindowsUtility.App.exe",
    "WindowsUtility.App.dll",
    "SmartComm2.dll",
]


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def digest_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def file_summary(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "path": path.as_posix(),
        "byteLength": len(raw),
        "sha256": digest_bytes(raw),
    }


def replay_package(package_path: Path) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    raw = package_path.read_bytes()
    artifact = {
        "path": package_path.as_posix(),
        "byteLength": len(raw),
        "sha256": digest_bytes(raw),
        "zipReadable": False,
        "fileCount": 0,
        "requiredEntries": {},
        "sampleEntries": [],
    }
    try:
        with zipfile.ZipFile(package_path, "r") as archive:
            bad_file = archive.testzip()
            names = sorted(name for name in archive.namelist() if not name.endswith("/"))
            artifact["zipReadable"] = bad_file is None
            artifact["zipTestFailure"] = bad_file
            artifact["fileCount"] = len(names)
            artifact["sampleEntries"] = names[:80]
            artifact["requiredEntries"] = {entry: entry in names for entry in REQUIRED_ENTRIES}
            if bad_file is not None:
                errors.append(f"zip test failed for entry: {bad_file}")
    except zipfile.BadZipFile as exc:
        artifact["zipTestFailure"] = str(exc)
        errors.append("package artifact is not a readable zip")

    for entry, present in artifact["requiredEntries"].items():
        if not present:
            errors.append(f"required package entry missing: {entry}")
    return artifact, errors


def validate_against_sources(
    artifact: dict[str, Any],
    manifest: dict[str, Any],
    boundary: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    manifest_artifact = manifest.get("artifact", {})
    boundary_artifact = boundary.get("packageArtifact", {})
    for label, source in [("manifest", manifest_artifact), ("boundary", boundary_artifact)]:
        if source.get("sha256") != artifact["sha256"]:
            errors.append(f"{label} sha256 does not match replayed package artifact")
        if source.get("byteLength") != artifact["byteLength"]:
            errors.append(f"{label} byteLength does not match replayed package artifact")
        if source.get("fileCount") != artifact["fileCount"]:
            errors.append(f"{label} fileCount does not match replayed package artifact")
        if source.get("zipReadable") is not True:
            errors.append(f"{label} must record zipReadable true")
    if manifest_artifact.get("containsWindowsUtilityAppExe") is not True:
        errors.append("manifest must record containsWindowsUtilityAppExe true")
    if manifest_artifact.get("containsSmartComm2Dll") is not True:
        errors.append("manifest must record containsSmartComm2Dll true")
    if boundary.get("verificationBoundary", {}).get("mayExtractPackageForVerification") is not False:
        errors.append("boundary must keep extraction unauthorized")
    if boundary.get("verificationBoundary", {}).get("mayRunPackagedExecutable") is not False:
        errors.append("boundary must keep packaged executable launch unauthorized")
    return errors


def build_report(package_path: Path, manifest_path: Path, boundary_path: Path) -> dict[str, Any]:
    manifest = read_json(manifest_path)
    boundary = read_json(boundary_path)
    artifact, replay_errors = replay_package(package_path)
    errors = replay_errors + validate_against_sources(artifact, manifest, boundary)
    result = "pass" if not errors else "fail"
    return {
        "artifactRole": "intentgraph-packaged-artifact-metadata-replay-report",
        "status": "intentgraph-packaged-artifact-metadata-replay-passed"
        if result == "pass"
        else "intentgraph-packaged-artifact-metadata-replay-failed",
        "scope": SCOPE,
        "workItem": WORK_ITEM,
        "date": DATE,
        "result": result,
        "errors": errors,
        "sourceReports": {
            "packageManifest": file_summary(manifest_path),
            "verificationBoundary": file_summary(boundary_path),
        },
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
        "authorizations": {
            "mayReadPackageArtifact": True,
            "mayVerifyChecksumFromExistingArtifact": True,
            "mayInspectZipInventory": True,
            "mayExtractPackageForVerification": False,
            "mayRunPackagedExecutable": False,
            "mayLaunchPackagedUi": False,
            "mayCapturePackagedUiScreenshot": False,
            "mayCreateInstaller": False,
            "maySignArtifact": False,
            "mayReadCredentials": False,
            "mayCallProviderApis": False,
            "mayCreateReleaseTags": False,
            "mayPublishRelease": False,
            "mayClaimProductizationReady": False,
        },
        "recommendedNextSlice": "P8.67 Packaged Artifact Metadata Replay Negative Probes",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay WindowsUtility package metadata without extraction.")
    parser.add_argument("--package", default=DEFAULT_PACKAGE, type=Path)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST, type=Path)
    parser.add_argument("--boundary", default=DEFAULT_BOUNDARY, type=Path)
    parser.add_argument("--out", default=DEFAULT_OUT, type=Path)
    args = parser.parse_args()

    report = build_report(args.package, args.manifest, args.boundary)
    write_json(args.out, report)
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
