"""Verify package extraction inventory inside an explicit sandbox boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
from typing import Any


WORK_ITEM = "Packaged Artifact Extraction Inventory Verification"
DATE = "2026-07-10"
AUTHORIZATION_TOKEN = "accept-sandboxed-package-extraction-inventory-verification"
DEFAULT_PACKAGE = Path(
    "generated/windowsutility/package-artifact/p8.55/windowsutility-shell-workspace-p8.55-sandbox-package.zip"
)
DEFAULT_MANIFEST = Path("generated/windowsutility/package-artifact/p8.55/package-manifest.json")
DEFAULT_METADATA_REPLAY = Path("generated/windowsutility/package-artifact/p8.66/metadata-replay-report.json")
DEFAULT_OUT = Path("generated/windowsutility/package-artifact/p8.69/extraction-inventory-report.json")
DEFAULT_EXTRACT_ROOT = Path("generated/windowsutility/package-artifact/p8.69/extracted")
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


def file_summary(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    return {
        "path": path.as_posix(),
        "byteLength": len(raw),
        "sha256": digest_bytes(raw),
    }


def ensure_empty_extract_root(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise ValueError("extract root must be empty before package extraction")
    path.mkdir(parents=True, exist_ok=True)


def safe_member_target(root: Path, member_name: str) -> Path:
    normalized = member_name.replace("\\", "/")
    candidate = Path(normalized)
    if candidate.is_absolute() or ".." in candidate.parts or not normalized.strip():
        raise ValueError(f"unsafe zip entry path: {member_name}")
    target = (root / candidate).resolve()
    root_resolved = root.resolve()
    if target != root_resolved and root_resolved not in target.parents:
        raise ValueError(f"zip entry escapes extraction root: {member_name}")
    return target


def read_zip_inventory(package_path: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    try:
        with zipfile.ZipFile(package_path, "r") as archive:
            bad_file = archive.testzip()
            if bad_file is not None:
                errors.append(f"zip test failed for entry: {bad_file}")
            names = sorted(name for name in archive.namelist() if not name.endswith("/"))
            return names, errors
    except zipfile.BadZipFile:
        return [], ["package artifact is not a readable zip"]


def extract_safely(package_path: Path, extract_root: Path) -> list[dict[str, Any]]:
    ensure_empty_extract_root(extract_root)
    extracted: list[dict[str, Any]] = []
    with zipfile.ZipFile(package_path, "r") as archive:
        for info in sorted(archive.infolist(), key=lambda item: item.filename):
            if info.filename.endswith("/"):
                continue
            target = safe_member_target(extract_root, info.filename)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info, "r") as source, target.open("wb") as dest:
                shutil.copyfileobj(source, dest)
            relative = target.relative_to(extract_root).as_posix()
            extracted.append(
                {
                    "path": relative,
                    "byteLength": target.stat().st_size,
                    "sha256": digest_file(target),
                }
            )
    return extracted


def source_artifact(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key, {})
    if not isinstance(value, dict):
        return {}
    return value


def validate_sources(
    package_path: Path,
    names: list[str],
    manifest: dict[str, Any],
    metadata_replay: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    package_sha = digest_file(package_path)
    package_size = package_path.stat().st_size
    manifest_artifact = source_artifact(manifest, "artifact")
    replay_artifact = source_artifact(metadata_replay, "packageArtifactReplay")
    for label, artifact in [("manifest", manifest_artifact), ("metadata replay", replay_artifact)]:
        if artifact.get("sha256") != package_sha:
            errors.append(f"{label} sha256 does not match package artifact")
        if artifact.get("byteLength") != package_size:
            errors.append(f"{label} byteLength does not match package artifact")
        if artifact.get("fileCount") != len(names):
            errors.append(f"{label} fileCount does not match zip inventory")
        if artifact.get("zipReadable") is not True:
            errors.append(f"{label} must record zipReadable true")
    for entry in REQUIRED_ENTRIES:
        if entry not in names:
            errors.append(f"required package entry missing from zip inventory: {entry}")
    return errors


def validate_extracted_inventory(names: list[str], extracted: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    extracted_names = sorted(str(item["path"]) for item in extracted)
    if extracted_names != names:
        errors.append("extracted file inventory does not match zip inventory")
    for entry in REQUIRED_ENTRIES:
        if entry not in extracted_names:
            errors.append(f"required package entry missing after extraction: {entry}")
    return errors


def build_report(
    package_path: Path,
    manifest_path: Path,
    metadata_replay_path: Path,
    extract_root: Path,
    authorization_token: str,
    scope: str,
    verification_mode: str,
) -> dict[str, Any]:
    authorization_ok = authorization_token == AUTHORIZATION_TOKEN
    boundary = {
        "authorizationTokenAccepted": authorization_ok,
        "packageExtractionPerformed": False,
        "packagedExecutableLaunched": False,
        "packagedUiLaunched": False,
        "packagedUiScreenshotCaptured": False,
        "installerCreated": False,
        "artifactSigned": False,
        "credentialAccessed": False,
        "providerApiCalled": False,
        "releasePublished": False,
        "productizationClaimed": False,
    }
    errors: list[str] = []
    if not authorization_ok:
        errors.append("missing accepted sandboxed extraction inventory authorization token")
        return {
            "artifactRole": "intentgraph-packaged-artifact-extraction-inventory-report",
            "status": "intentgraph-packaged-artifact-extraction-inventory-failed",
            "scope": scope,
            "workItem": WORK_ITEM,
            "date": DATE,
            "result": "fail",
            "errors": errors,
            "verificationMode": verification_mode,
            "boundary": boundary,
        }

    manifest = read_json(manifest_path)
    metadata_replay = read_json(metadata_replay_path)
    names, zip_errors = read_zip_inventory(package_path)
    errors.extend(zip_errors)
    errors.extend(validate_sources(package_path, names, manifest, metadata_replay))

    extracted: list[dict[str, Any]] = []
    if not errors:
        try:
            extracted = extract_safely(package_path, extract_root)
            boundary["packageExtractionPerformed"] = True
            errors.extend(validate_extracted_inventory(names, extracted))
        except ValueError as exc:
            errors.append(str(exc))

    result = "pass" if not errors else "fail"
    return {
        "artifactRole": "intentgraph-packaged-artifact-extraction-inventory-report",
        "status": "intentgraph-packaged-artifact-extraction-inventory-passed"
        if result == "pass"
        else "intentgraph-packaged-artifact-extraction-inventory-failed",
        "scope": scope,
        "workItem": WORK_ITEM,
        "date": DATE,
        "result": result,
        "errors": errors,
        "verificationMode": verification_mode,
        "sourceReports": {
            "packageArtifact": file_summary(package_path),
            "packageManifest": file_summary(manifest_path),
            "metadataReplay": file_summary(metadata_replay_path),
        },
        "zipInventory": {
            "fileCount": len(names),
            "requiredEntries": {entry: entry in names for entry in REQUIRED_ENTRIES},
            "sampleEntries": names[:80],
        },
        "extractionInventory": {
            "extractRoot": extract_root.as_posix(),
            "fileCount": len(extracted),
            "requiredEntries": {entry: any(item["path"] == entry for item in extracted) for entry in REQUIRED_ENTRIES},
            "sampleEntries": extracted[:80],
        },
        "boundary": boundary,
        "authorizations": {
            "mayUseTemporarySandboxDirectory": True,
            "mayCopyExistingPackageArtifactToSandbox": True,
            "mayExtractSandboxPackageCopy": authorization_ok,
            "mayListExtractedFiles": authorization_ok,
            "mayHashExtractedFiles": authorization_ok,
            "mayCompareExtractedInventoryToManifest": authorization_ok,
            "mayRunPackagedExecutable": False,
            "mayLaunchPackagedUi": False,
            "mayCapturePackagedUiScreenshot": False,
            "mayCreateInstaller": False,
            "maySignArtifacts": False,
            "mayReadCredentials": False,
            "mayCallProviderApis": False,
            "mayCreateReleaseTags": False,
            "mayPublishReleases": False,
            "mayClaimProductizationReady": False,
        },
        "recommendedNextSlice": "P8.70 Packaged Artifact Extraction Inventory Negative Probes"
        if result == "pass"
        else "P8.69 Package Verification Scope Revision",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify package extraction inventory in a sandbox.")
    parser.add_argument("--package", default=DEFAULT_PACKAGE, type=Path)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST, type=Path)
    parser.add_argument("--metadata-replay", default=DEFAULT_METADATA_REPLAY, type=Path)
    parser.add_argument("--extract-root", default=DEFAULT_EXTRACT_ROOT, type=Path)
    parser.add_argument("--out", default=DEFAULT_OUT, type=Path)
    parser.add_argument("--authorization-token", default="")
    parser.add_argument("--scope", default="packaged-artifact-extraction-inventory-verification")
    parser.add_argument("--verification-mode", default="sandboxed-local-package-extraction-inventory-verification")
    args = parser.parse_args()

    report = build_report(
        args.package,
        args.manifest,
        args.metadata_replay,
        args.extract_root,
        args.authorization_token,
        args.scope,
        args.verification_mode,
    )
    write_json(args.out, report)
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
