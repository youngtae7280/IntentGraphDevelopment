"""Create and validate a sandboxed WindowsUtility package artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Any


REPORT_VERSION = "0.1.0"
WORK_ITEM = "P8.55 Sandboxed Package Artifact Creation Probe"
SCOPE = "p8.55-sandboxed-package-artifact-creation-probe"
DATE = "2026-07-10"

AUTHORIZATION_ROLE = "intentgraph-package-artifact-creation-authorization-result"
AUTHORIZATION_STATUS = "intentgraph-package-artifact-creation-authorization-result-recorded"

TRUE_AUTHORIZATION_KEYS = [
    "packageArtifactCreationAuthorized",
    "sandboxedPackageArtifactCreationAuthorized",
    "sandboxedBuildOrPublishAuthorized",
    "packageManifestAuthorized",
    "artifactReadabilityVerificationAuthorized",
]

FALSE_AUTHORIZATION_KEYS = [
    "installerCreationAuthorized",
    "artifactSigningAuthorized",
    "credentialAccessAuthorized",
    "providerApiCallsAuthorized",
    "releaseTagCreationAuthorized",
    "releasePublishingAuthorized",
    "sourceEditsAuthorized",
    "targetWritesAuthorized",
    "windowsUtilityCommitAuthorized",
    "windowsUtilityPushAuthorized",
    "aiAuthorityPromoted",
    "productizationAuthorized",
]

FORBIDDEN_CLAIM_KEYS = [
    "sourceMutated",
    "targetMutated",
    "installerCreated",
    "artifactSigned",
    "credentialAccessed",
    "providerApiCalled",
    "releaseTagCreated",
    "releasePublished",
    "productizationClaimed",
]

ZIP_TIMESTAMP = (2026, 7, 10, 0, 0, 0)


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def digest_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def digest_json(data: Any) -> str:
    return digest_bytes(canonical_json(data).encode("utf-8"))


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def run_capture(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def run_git(target_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(target_root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def collect_target_state(target_root: Path) -> dict[str, Any]:
    head = run_git(target_root, "rev-parse", "HEAD")
    origin = run_git(target_root, "rev-parse", "origin/main")
    status = run_git(target_root, "status", "--short", "--branch")
    return {
        "path": str(target_root),
        "head": head,
        "originMain": origin,
        "gitStatus": status,
        "cleanAligned": head == origin and status == "## main...origin/main",
    }


def sandbox_root(repo_root: Path) -> Path:
    return repo_root / ".tmp" / "windowsutility-package-artifact" / "p8.55"


def reset_sandbox(repo_root: Path) -> Path:
    root = sandbox_root(repo_root).resolve()
    allowed_parent = (repo_root / ".tmp" / "windowsutility-package-artifact").resolve()
    if allowed_parent not in [root, *root.parents]:
        raise ValueError(f"refusing to reset sandbox outside allowed parent: {root}")
    if root.exists():
        shutil.rmtree(root, ignore_errors=True)
    if root.exists():
        raise OSError(f"failed to reset sandbox directory: {root}")
    root.mkdir(parents=True, exist_ok=True)
    return root


def create_sandbox_copy(repo_root: Path, target_root: Path, smartcomm_dll: Path) -> dict[str, Any]:
    root = reset_sandbox(repo_root)
    archive_path = root / "windowsutility-source.zip"
    source_parent = root / "source"
    sandbox_target = source_parent / "WindowsUtility"
    sandbox_target.mkdir(parents=True, exist_ok=True)

    archive_result = subprocess.run(
        ["git", "-C", str(target_root), "archive", "--format=zip", "HEAD", "-o", str(archive_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    shutil.unpack_archive(str(archive_path), str(sandbox_target), "zip")

    dependency_target = source_parent / "Utility_Windows" / "Release_x64" / "SmartComm2.dll"
    dependency_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(smartcomm_dll, dependency_target)

    return {
        "sandboxRoot": root,
        "sandboxTargetRoot": sandbox_target,
        "sourceArchive": archive_path,
        "sourceArchiveDigest": digest_file(archive_path),
        "sourceArchiveByteLength": archive_path.stat().st_size,
        "dependencyCopies": [
            {
                "sourcePath": str(smartcomm_dll),
                "sandboxPath": str(dependency_target),
                "sha256": digest_file(dependency_target),
                "byteLength": dependency_target.stat().st_size,
            }
        ],
        "archiveStdout": archive_result.stdout,
        "archiveStderr": archive_result.stderr,
    }


def write_log(path: Path, text: str) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return {
        "path": str(path),
        "sha256": digest_file(path),
        "byteLength": path.stat().st_size,
    }


def publish_sandbox(sandbox_target: Path, publish_dir: Path, out_dir: Path) -> dict[str, Any]:
    command = [
        "dotnet",
        "publish",
        "src/WindowsUtility.App/WindowsUtility.App.csproj",
        "-c",
        "Release",
        "-o",
        str(publish_dir),
        "--no-self-contained",
    ]
    result = run_capture(command, cwd=sandbox_target)
    stdout_log = write_log(out_dir / "publish-stdout.txt", result.stdout)
    stderr_log = write_log(out_dir / "publish-stderr.txt", result.stderr)
    files = [path for path in publish_dir.rglob("*") if path.is_file()] if publish_dir.exists() else []
    relative_files = sorted(str(path.relative_to(publish_dir)).replace("\\", "/") for path in files)
    return {
        "command": " ".join(command),
        "cwd": str(sandbox_target),
        "exitCode": result.returncode,
        "stdoutLog": stdout_log,
        "stderrLog": stderr_log,
        "publishDir": str(publish_dir),
        "fileCount": len(relative_files),
        "requiredFiles": {
            "WindowsUtility.App.exe": "WindowsUtility.App.exe" in relative_files,
            "WindowsUtility.App.dll": "WindowsUtility.App.dll" in relative_files,
            "SmartComm2.dll": "SmartComm2.dll" in relative_files,
        },
        "sampleFiles": relative_files[:40],
    }


def create_zip_from_directory(source_dir: Path, zip_path: Path) -> dict[str, Any]:
    if zip_path.exists():
        zip_path.unlink()
    files = sorted([path for path in source_dir.rglob("*") if path.is_file()], key=lambda p: str(p.relative_to(source_dir)).lower())
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            arcname = str(path.relative_to(source_dir)).replace("\\", "/")
            info = zipfile.ZipInfo(arcname, date_time=ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())

    with zipfile.ZipFile(zip_path, "r") as archive:
        bad_file = archive.testzip()
        names = archive.namelist()

    return {
        "path": str(zip_path),
        "sha256": digest_file(zip_path),
        "byteLength": zip_path.stat().st_size,
        "fileCount": len(names),
        "zipReadable": bad_file is None,
        "zipTestFailure": bad_file,
        "containsWindowsUtilityAppExe": "WindowsUtility.App.exe" in names,
        "containsSmartComm2Dll": "SmartComm2.dll" in names,
        "sampleEntries": names[:40],
    }


def base_authorizations() -> dict[str, bool]:
    result = {key: True for key in TRUE_AUTHORIZATION_KEYS}
    result.update({key: False for key in FALSE_AUTHORIZATION_KEYS})
    return result


def validate_authorization(auth: dict[str, Any], errors: list[str]) -> None:
    if auth.get("artifactRole") != AUTHORIZATION_ROLE:
        errors.append("authorization artifactRole is not accepted")
    if auth.get("status") != AUTHORIZATION_STATUS:
        errors.append("authorization status is not accepted")
    authorizations = auth.get("authorizations", {})
    if not isinstance(authorizations, dict):
        errors.append("authorization.authorizations must be an object")
        return
    for key in TRUE_AUTHORIZATION_KEYS:
        if authorizations.get(key) is not True:
            errors.append(f"authorization.authorizations.{key} must be true")
    for key in FALSE_AUTHORIZATION_KEYS:
        if authorizations.get(key) is not False:
            errors.append(f"authorization.authorizations.{key} must be false")


def validate_probe_report(report_path: Path, repo_root: Path, target_root: Path) -> dict[str, Any]:
    errors: list[str] = []
    report = read_json(report_path)

    if report.get("artifactRole") != "intentgraph-windowsutility-sandboxed-package-artifact-probe-report":
        errors.append("report artifactRole is not accepted")
    if report.get("scope") != SCOPE:
        errors.append("report scope is not accepted")
    if report.get("packageArtifactProbe", {}).get("mode") != "sandboxed-local-package-artifact-validation-only":
        errors.append("packageArtifactProbe.mode must be sandboxed-local-package-artifact-validation-only")

    authorizations = report.get("authorizations", {})
    if not isinstance(authorizations, dict):
        errors.append("report.authorizations must be an object")
    else:
        for key in TRUE_AUTHORIZATION_KEYS:
            if authorizations.get(key) is not True:
                errors.append(f"report.authorizations.{key} must be true")
        for key in FALSE_AUTHORIZATION_KEYS:
            if authorizations.get(key) is not False:
                errors.append(f"report.authorizations.{key} must be false")

    claim_scope = report.get("claimScope", {})
    if claim_scope.get("sandboxedPackageArtifactCreated") is not True:
        errors.append("claimScope.sandboxedPackageArtifactCreated must be true")
    if claim_scope.get("sandboxedBuildOrPublishPerformed") is not True:
        errors.append("claimScope.sandboxedBuildOrPublishPerformed must be true")
    for key in FORBIDDEN_CLAIM_KEYS:
        if claim_scope.get(key) is not False:
            errors.append(f"claimScope.{key} must be false")

    publish = report.get("publish", {})
    if publish.get("exitCode") != 0:
        errors.append("publish.exitCode must be 0")
    required_files = publish.get("requiredFiles", {})
    for required in ["WindowsUtility.App.exe", "WindowsUtility.App.dll", "SmartComm2.dll"]:
        if required_files.get(required) is not True:
            errors.append(f"publish.requiredFiles.{required} must be true")

    artifact = report.get("packageArtifact", {})
    artifact_path_text = artifact.get("path")
    artifact_path = Path(artifact_path_text) if isinstance(artifact_path_text, str) else None
    if artifact_path is None or not artifact_path.exists():
        errors.append("packageArtifact.path must exist")
    else:
        if artifact.get("sha256") != digest_file(artifact_path):
            errors.append("packageArtifact.sha256 does not match artifact bytes")
        if artifact.get("byteLength") != artifact_path.stat().st_size:
            errors.append("packageArtifact.byteLength does not match artifact bytes")
        try:
            with zipfile.ZipFile(artifact_path, "r") as archive:
                bad_file = archive.testzip()
                names = archive.namelist()
            if bad_file is not None:
                errors.append("packageArtifact zip readability check failed")
            for required in ["WindowsUtility.App.exe", "WindowsUtility.App.dll", "SmartComm2.dll"]:
                if required not in names:
                    errors.append(f"packageArtifact missing {required}")
        except zipfile.BadZipFile:
            errors.append("packageArtifact must be a readable zip file")
    if artifact.get("zipReadable") is not True:
        errors.append("packageArtifact.zipReadable must be true")
    if artifact.get("fileCount", 0) <= 0:
        errors.append("packageArtifact.fileCount must be positive")

    baseline = report.get("targetBaseline", {})
    final_state = report.get("targetFinalState", {})
    if baseline.get("cleanAligned") is not True:
        errors.append("targetBaseline.cleanAligned must be true")
    if final_state.get("cleanAligned") is not True:
        errors.append("targetFinalState.cleanAligned must be true")
    if baseline.get("head") != final_state.get("head"):
        errors.append("target HEAD changed during package artifact probe")
    if baseline.get("originMain") != final_state.get("originMain"):
        errors.append("target origin/main changed during package artifact probe")

    try:
        actual = collect_target_state(target_root)
        if actual["head"] != baseline.get("head"):
            errors.append("current target HEAD does not match recorded baseline")
        if actual["originMain"] != baseline.get("originMain"):
            errors.append("current target origin/main does not match recorded baseline")
        if actual["gitStatus"] != "## main...origin/main":
            errors.append("current target status must stay clean/aligned")
    except (OSError, subprocess.CalledProcessError) as error:
        errors.append(f"failed to inspect current target state: {error}")

    return {
        "artifactRole": "intentgraph-windowsutility-sandboxed-package-artifact-validation-report",
        "status": "intentgraph-windowsutility-sandboxed-package-artifact-validation-passed"
        if not errors
        else "intentgraph-windowsutility-sandboxed-package-artifact-validation-failed",
        "scope": SCOPE,
        "workItem": WORK_ITEM,
        "date": DATE,
        "reportVersion": REPORT_VERSION,
        "result": "pass" if not errors else "fail",
        "validatedReport": rel(report_path, repo_root),
        "errorCount": len(errors),
        "errors": errors,
    }


def emit(
    repo_root: Path,
    target_root: Path,
    utility_windows_root: Path,
    authorization_path: Path,
    out_dir: Path,
) -> dict[str, Any]:
    auth = read_json(authorization_path)
    auth_errors: list[str] = []
    validate_authorization(auth, auth_errors)
    if auth_errors:
        raise ValueError("; ".join(auth_errors))

    out_dir.mkdir(parents=True, exist_ok=True)
    package_path = out_dir / "windowsutility-shell-workspace-p8.55-sandbox-package.zip"
    manifest_path = out_dir / "package-manifest.json"
    report_path = out_dir / "package-artifact-probe-report.json"
    validation_path = out_dir / "validation-report.json"

    smartcomm_dll = utility_windows_root / "Release_x64" / "SmartComm2.dll"
    if not smartcomm_dll.exists():
        raise FileNotFoundError(f"required dependency missing: {smartcomm_dll}")

    baseline = collect_target_state(target_root)
    sandbox = create_sandbox_copy(repo_root, target_root, smartcomm_dll)
    publish_dir = sandbox["sandboxRoot"] / "publish"
    publish = publish_sandbox(sandbox["sandboxTargetRoot"], publish_dir, out_dir)
    if publish["exitCode"] != 0:
        report = {
            "artifactRole": "intentgraph-windowsutility-sandboxed-package-artifact-probe-report",
            "status": "intentgraph-windowsutility-sandboxed-package-artifact-probe-failed",
            "scope": SCOPE,
            "workItem": WORK_ITEM,
            "date": DATE,
            "reportVersion": REPORT_VERSION,
            "sourceAuthorization": {
                "path": rel(authorization_path, repo_root),
                "digest": digest_json(auth),
                "artifactRole": auth.get("artifactRole"),
                "status": auth.get("status"),
            },
            "targetBaseline": baseline,
            "targetFinalState": collect_target_state(target_root),
            "packageArtifactProbe": {
                "mode": "sandboxed-local-package-artifact-validation-only",
                "result": "fail",
            },
            "sandbox": {
                "root": str(sandbox["sandboxRoot"]),
                "targetRoot": str(sandbox["sandboxTargetRoot"]),
                "sourceArchiveDigest": sandbox["sourceArchiveDigest"],
                "sourceArchiveByteLength": sandbox["sourceArchiveByteLength"],
                "dependencyCopies": sandbox["dependencyCopies"],
            },
            "publish": publish,
            "packageArtifact": {
                "path": str(package_path),
                "created": False,
            },
            "claimScope": {
                "sandboxedPackageArtifactCreated": False,
                "sandboxedBuildOrPublishPerformed": True,
                "sourceMutated": False,
                "targetMutated": False,
                "installerCreated": False,
                "artifactSigned": False,
                "credentialAccessed": False,
                "providerApiCalled": False,
                "releaseTagCreated": False,
                "releasePublished": False,
                "productizationClaimed": False,
            },
            "authorizations": base_authorizations(),
        }
        write_json(report_path, report)
        validation = validate_probe_report(report_path, repo_root, target_root)
        write_json(validation_path, validation)
        return validation

    package_artifact = create_zip_from_directory(publish_dir, package_path)
    manifest = {
        "artifactRole": "intentgraph-windowsutility-sandboxed-package-artifact-manifest",
        "status": "intentgraph-windowsutility-sandboxed-package-artifact-manifest-recorded",
        "scope": SCOPE,
        "workItem": WORK_ITEM,
        "date": DATE,
        "packageApplicationMode": "sandboxed-local-validation-only",
        "product": "WindowsUtility",
        "surface": "shell-workspace",
        "artifact": package_artifact,
        "sourceAuthorization": rel(authorization_path, repo_root),
        "targetHead": baseline["head"],
        "releasePublished": False,
        "artifactSigned": False,
        "productizationClaimed": False,
    }
    write_json(manifest_path, manifest)

    final_state = collect_target_state(target_root)
    report = {
        "artifactRole": "intentgraph-windowsutility-sandboxed-package-artifact-probe-report",
        "status": "intentgraph-windowsutility-sandboxed-package-artifact-probe-passed",
        "scope": SCOPE,
        "workItem": WORK_ITEM,
        "date": DATE,
        "reportVersion": REPORT_VERSION,
        "sourceAuthorization": {
            "path": rel(authorization_path, repo_root),
            "digest": digest_json(auth),
            "artifactRole": auth.get("artifactRole"),
            "status": auth.get("status"),
            "decision": auth.get("decision"),
        },
        "targetBaseline": baseline,
        "targetFinalState": final_state,
        "packageArtifactProbe": {
            "mode": "sandboxed-local-package-artifact-validation-only",
            "result": "pass",
            "packageArtifactCreated": True,
            "packageArtifactReadable": package_artifact["zipReadable"],
        },
        "sandbox": {
            "root": str(sandbox["sandboxRoot"]),
            "targetRoot": str(sandbox["sandboxTargetRoot"]),
            "sourceArchiveDigest": sandbox["sourceArchiveDigest"],
            "sourceArchiveByteLength": sandbox["sourceArchiveByteLength"],
            "dependencyCopies": sandbox["dependencyCopies"],
        },
        "publish": publish,
        "packageArtifact": package_artifact,
        "packageManifest": {
            "path": rel(manifest_path, repo_root),
            "digest": digest_json(manifest),
            "byteLength": manifest_path.stat().st_size,
        },
        "claimScope": {
            "sandboxedPackageArtifactCreated": True,
            "sandboxedBuildOrPublishPerformed": True,
            "sourceMutated": False,
            "targetMutated": False,
            "installerCreated": False,
            "artifactSigned": False,
            "credentialAccessed": False,
            "providerApiCalled": False,
            "releaseTagCreated": False,
            "releasePublished": False,
            "productizationClaimed": False,
        },
        "authorizations": base_authorizations(),
        "remainingGates": [
            "packaged artifact verification beyond zip readability",
            "installer/signing authority",
            "release authority",
            "user acceptance of package candidate",
            "productization authority",
        ],
    }
    write_json(report_path, report)
    validation = validate_probe_report(report_path, repo_root, target_root)
    write_json(validation_path, validation)
    return validation


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a sandboxed WindowsUtility package artifact probe.")
    parser.add_argument("--target-root", required=True, type=Path)
    parser.add_argument("--utility-windows-root", required=True, type=Path)
    parser.add_argument("--authorization", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    try:
        validation = emit(
            repo_root=repo_root,
            target_root=args.target_root,
            utility_windows_root=args.utility_windows_root,
            authorization_path=args.authorization,
            out_dir=args.out_dir,
        )
    except (OSError, json.JSONDecodeError, ValueError, subprocess.CalledProcessError) as error:
        print(f"emit WindowsUtility sandboxed package artifact probe failed: {error}")
        return 1
    return 0 if validation.get("result") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
