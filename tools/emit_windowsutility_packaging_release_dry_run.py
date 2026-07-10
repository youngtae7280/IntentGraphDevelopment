"""Emit and validate a non-mutating WindowsUtility packaging/release dry run."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


REPORT_VERSION = "0.1.0"
WORK_ITEM = "P8.49 Non-Mutating Packaging/Release Dry-Run Prototype"
SCOPE = "p8.49-non-mutating-packaging-release-dry-run-prototype"
DATE = "2026-07-10"

REQUEST_FILE = "dry-run-request.json"
PACKAGE_MANIFEST_FILE = "package-manifest-preview.json"
BUILD_TEST_PLAN_FILE = "build-test-evidence-plan.json"
RELEASE_NOTES_FILE = "release-notes-preview.json"
PUBLISH_DESTINATION_FILE = "publish-destination-plan.json"
ROLLBACK_PLAN_FILE = "rollback-plan.json"
AUTHORITY_REPORT_FILE = "authority-requirement-report.json"
VALIDATION_REPORT_FILE = "validation-report.json"

FALSE_AUTHORIZATION_KEYS = [
    "sourceEditsAuthorized",
    "targetWritesAuthorized",
    "windowsUtilityBuildArtifactCreationAuthorized",
    "packageArtifactCreationAuthorized",
    "installerCreationAuthorized",
    "artifactSigningAuthorized",
    "credentialAccessAuthorized",
    "providerApiCallsAuthorized",
    "releaseTagCreationAuthorized",
    "releasePublishingAuthorized",
    "aiAuthorityPromoted",
    "productizationAuthorized",
]


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def digest_json(data: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


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
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def run_git(target_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(target_root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def empty_authorizations() -> dict[str, bool]:
    return {key: False for key in FALSE_AUTHORIZATION_KEYS}


def require_false_map(data: dict[str, Any], prefix: str, errors: list[str]) -> None:
    for key in FALSE_AUTHORIZATION_KEYS:
        if data.get(key) is not False:
            errors.append(f"{prefix}.{key} must be false")


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


def source_inputs(
    repo_root: Path,
    boundary_report_path: Path,
    workbench_report_path: Path,
    target_root: Path,
    boundary: dict[str, Any],
    workbench: dict[str, Any],
) -> dict[str, Any]:
    return {
        "boundaryReport": {
            "path": rel(boundary_report_path, repo_root),
            "digest": digest_json(boundary),
            "artifactRole": boundary.get("artifactRole"),
            "status": boundary.get("status"),
        },
        "sourceApplicationWorkbenchReport": {
            "path": rel(workbench_report_path, repo_root),
            "digest": digest_json(workbench),
            "artifactRole": workbench.get("artifactRole"),
            "status": workbench.get("status"),
            "decision": workbench.get("decision"),
        },
        "targetRoot": str(target_root),
    }


def required_files(target_root: Path) -> list[dict[str, Any]]:
    paths = [
        "WindowsUtility.sln",
        "src/WindowsUtility.App/WindowsUtility.App.csproj",
        "src/WindowsUtility.Shell/WindowsUtility.Shell.csproj",
        "tests/RegressionSmoke/Invoke-IntentGraphShellWorkspacePreflight.ps1",
    ]
    results = []
    for path in paths:
        full_path = target_root / path
        results.append({"path": path, "exists": full_path.exists(), "readOnlyCheck": True})
    return results


def build_artifacts(
    repo_root: Path,
    target_root: Path,
    boundary_report_path: Path,
    workbench_report_path: Path,
) -> dict[str, dict[str, Any]]:
    boundary = read_json(boundary_report_path)
    workbench = read_json(workbench_report_path)
    target_state = collect_target_state(target_root)
    inputs = source_inputs(repo_root, boundary_report_path, workbench_report_path, target_root, boundary, workbench)
    files = required_files(target_root)

    request = {
        "artifactRole": "intentgraph-windowsutility-packaging-release-dry-run-request",
        "status": "intentgraph-windowsutility-packaging-release-dry-run-request-recorded",
        "scope": SCOPE,
        "workItem": WORK_ITEM,
        "date": DATE,
        "reportVersion": REPORT_VERSION,
        "mode": "non-mutating-packaging-release-dry-run",
        "dryRunPurpose": "Create a deterministic packaging/release rehearsal record before any package artifact or release is created.",
        "sourceInputs": inputs,
        "targetBaseline": target_state,
        "readOnlyTargetFileChecks": files,
        "authorizations": empty_authorizations(),
        "claimScope": {
            "dryRunOnly": True,
            "sourceMutated": False,
            "targetMutated": False,
            "windowsUtilityBuildArtifactCreated": False,
            "packageArtifactCreated": False,
            "installerCreated": False,
            "artifactSigned": False,
            "credentialAccessed": False,
            "providerApiCalled": False,
            "releaseTagCreated": False,
            "releasePublished": False,
            "productizationClaimed": False,
        },
    }

    manifest = {
        "artifactRole": "intentgraph-windowsutility-package-manifest-preview",
        "status": "intentgraph-windowsutility-package-manifest-preview-recorded",
        "scope": SCOPE,
        "workItem": WORK_ITEM,
        "date": DATE,
        "packageApplicationMode": "non-mutating-preview-only",
        "packageScope": {
            "product": "WindowsUtility",
            "surface": "shell-workspace",
            "target": "local-windows-desktop-preview",
        },
        "artifactIdentity": {
            "id": "windowsutility-shell-workspace-preview",
            "version": "0.0.0-p8.49-dry-run",
            "format": "zip-or-installer-preview-only",
        },
        "expectedOutputs": [],
        "packageArtifactCreationExpected": False,
        "installerCreationExpected": False,
        "artifactSigningExpected": False,
        "authorizations": empty_authorizations(),
    }

    build_test = {
        "artifactRole": "intentgraph-windowsutility-packaging-build-test-evidence-plan",
        "status": "intentgraph-windowsutility-packaging-build-test-evidence-plan-recorded",
        "scope": SCOPE,
        "workItem": WORK_ITEM,
        "date": DATE,
        "buildCommands": [
            {
                "id": "build.windowsutility.solution",
                "command": "dotnet build .\\WindowsUtility.sln",
                "executeInDryRun": False,
                "requiresPackageOutput": False,
            }
        ],
        "testEvidencePlan": [
            {
                "id": "test.intentgraph.shell-workspace-preflight",
                "command": "powershell -NoProfile -ExecutionPolicy Bypass -File .\\tests\\RegressionSmoke\\Invoke-IntentGraphShellWorkspacePreflight.ps1",
                "executeInDryRun": False,
            },
            {
                "id": "test.windowsutility.regression-smoke",
                "command": "powershell -NoProfile -ExecutionPolicy Bypass -File .\\tests\\RegressionSmoke\\Invoke-WindowsUtilityRegressionSmoke.ps1",
                "executeInDryRun": False,
            },
        ],
        "priorEvidence": [
            "generated/roadmap/p8.44-minimal-windowsutility-source-edit-application-report.json",
            "generated/roadmap/p8.46-windowsutility-source-application-workbench-refresh-report.json",
        ],
        "authorizations": empty_authorizations(),
    }

    release_notes = {
        "artifactRole": "intentgraph-windowsutility-release-notes-preview",
        "status": "intentgraph-windowsutility-release-notes-preview-recorded",
        "scope": SCOPE,
        "workItem": WORK_ITEM,
        "date": DATE,
        "releaseNotesPreviewOnly": True,
        "releasePublished": False,
        "summary": "Preview only: WindowsUtility shell/workspace IntentGraph preflight evidence became available.",
        "changeItems": [
            "Added IntentGraph shell/workspace source-application preflight script in WindowsUtility.",
            "Refreshed static IntentGraph workbench evidence for the applied source edit.",
        ],
        "authorizations": empty_authorizations(),
    }

    publish_destination = {
        "artifactRole": "intentgraph-windowsutility-publish-destination-plan",
        "status": "intentgraph-windowsutility-publish-destination-plan-recorded",
        "scope": SCOPE,
        "workItem": WORK_ITEM,
        "date": DATE,
        "publishDestination": {
            "kind": "future-release-destination-placeholder",
            "provider": "not-selected",
            "repository": "not-authorized",
        },
        "credentialAccess": False,
        "providerApiCalls": False,
        "releaseTagCreation": False,
        "releasePublishing": False,
        "authorizations": empty_authorizations(),
    }

    rollback = {
        "artifactRole": "intentgraph-windowsutility-packaging-release-rollback-plan",
        "status": "intentgraph-windowsutility-packaging-release-rollback-plan-recorded",
        "scope": SCOPE,
        "workItem": WORK_ITEM,
        "date": DATE,
        "packageArtifactCreated": False,
        "releasePublished": False,
        "rollbackActionRequiredForThisDryRun": False,
        "futureRollbackRequirements": [
            "Capture clean target baseline before package artifact creation.",
            "Record exact package artifact identity and checksums before release.",
            "Stop if credentials, signing, provider APIs, or release publishing are not explicitly approved.",
        ],
        "authorizations": empty_authorizations(),
    }

    authority = {
        "artifactRole": "intentgraph-windowsutility-packaging-release-authority-requirement-report",
        "status": "intentgraph-windowsutility-packaging-release-authority-requirements-recorded",
        "scope": SCOPE,
        "workItem": WORK_ITEM,
        "date": DATE,
        "dryRunAuthority": {
            "nonMutatingPackagingReleaseDryRunRecorded": True,
            "packageArtifactCreationAuthorized": False,
            "installerCreationAuthorized": False,
            "artifactSigningAuthorized": False,
            "credentialAccessAuthorized": False,
            "providerApiCallsAuthorized": False,
            "releaseTagCreationAuthorized": False,
            "releasePublishingAuthorized": False,
            "aiSelfAuthorizationAllowed": False,
            "productizationAuthorized": False,
        },
        "nextGate": {
            "id": "gate.future-packaging-release-authorization",
            "requiredBeforePackageOrRelease": True,
            "reason": "A packaging/release slice must use this dry-run plus explicit coordinator/user authority before creating artifacts or publishing.",
        },
        "authorizations": empty_authorizations(),
    }

    return {
        REQUEST_FILE: request,
        PACKAGE_MANIFEST_FILE: manifest,
        BUILD_TEST_PLAN_FILE: build_test,
        RELEASE_NOTES_FILE: release_notes,
        PUBLISH_DESTINATION_FILE: publish_destination,
        ROLLBACK_PLAN_FILE: rollback,
        AUTHORITY_REPORT_FILE: authority,
    }


def load_dry_run_artifacts(out_dir: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    errors: list[str] = []
    artifacts: dict[str, dict[str, Any]] = {}
    for filename in [
        REQUEST_FILE,
        PACKAGE_MANIFEST_FILE,
        BUILD_TEST_PLAN_FILE,
        RELEASE_NOTES_FILE,
        PUBLISH_DESTINATION_FILE,
        ROLLBACK_PLAN_FILE,
        AUTHORITY_REPORT_FILE,
    ]:
        path = out_dir / filename
        if not path.exists():
            errors.append(f"missing artifact {filename}")
            continue
        try:
            artifacts[filename] = read_json(path)
        except (OSError, json.JSONDecodeError, ValueError) as error:
            errors.append(f"failed to read {filename}: {error}")
    return artifacts, errors


def validate_dry_run_dir(out_dir: Path, target_root: Path | None = None) -> dict[str, Any]:
    artifacts, errors = load_dry_run_artifacts(out_dir)
    request = artifacts.get(REQUEST_FILE, {})
    manifest = artifacts.get(PACKAGE_MANIFEST_FILE, {})
    build_test = artifacts.get(BUILD_TEST_PLAN_FILE, {})
    release_notes = artifacts.get(RELEASE_NOTES_FILE, {})
    publish = artifacts.get(PUBLISH_DESTINATION_FILE, {})
    rollback = artifacts.get(ROLLBACK_PLAN_FILE, {})
    authority = artifacts.get(AUTHORITY_REPORT_FILE, {})

    expected_roles = {
        REQUEST_FILE: "intentgraph-windowsutility-packaging-release-dry-run-request",
        PACKAGE_MANIFEST_FILE: "intentgraph-windowsutility-package-manifest-preview",
        BUILD_TEST_PLAN_FILE: "intentgraph-windowsutility-packaging-build-test-evidence-plan",
        RELEASE_NOTES_FILE: "intentgraph-windowsutility-release-notes-preview",
        PUBLISH_DESTINATION_FILE: "intentgraph-windowsutility-publish-destination-plan",
        ROLLBACK_PLAN_FILE: "intentgraph-windowsutility-packaging-release-rollback-plan",
        AUTHORITY_REPORT_FILE: "intentgraph-windowsutility-packaging-release-authority-requirement-report",
    }
    for filename, role in expected_roles.items():
        artifact = artifacts.get(filename)
        if not artifact:
            continue
        if artifact.get("artifactRole") != role:
            errors.append(f"{filename} has wrong artifactRole")
        if artifact.get("scope") != SCOPE:
            errors.append(f"{filename} has wrong scope")
        authorizations = artifact.get("authorizations", {})
        if not isinstance(authorizations, dict):
            errors.append(f"{filename}.authorizations must be an object")
        else:
            require_false_map(authorizations, f"{filename}.authorizations", errors)

    baseline = request.get("targetBaseline", {}) if isinstance(request, dict) else {}
    if baseline.get("cleanAligned") is not True:
        errors.append("request.targetBaseline.cleanAligned must be true")
    if baseline.get("gitStatus") != "## main...origin/main":
        errors.append("request.targetBaseline.gitStatus must be clean/aligned")
    if request.get("claimScope", {}).get("dryRunOnly") is not True:
        errors.append("request.claimScope.dryRunOnly must be true")
    for key in [
        "sourceMutated",
        "targetMutated",
        "windowsUtilityBuildArtifactCreated",
        "packageArtifactCreated",
        "installerCreated",
        "artifactSigned",
        "credentialAccessed",
        "providerApiCalled",
        "releaseTagCreated",
        "releasePublished",
        "productizationClaimed",
    ]:
        if request.get("claimScope", {}).get(key) is not False:
            errors.append(f"request.claimScope.{key} must be false")
    file_checks = request.get("readOnlyTargetFileChecks", [])
    if not isinstance(file_checks, list) or not file_checks:
        errors.append("request.readOnlyTargetFileChecks must be non-empty")
    elif any(item.get("exists") is not True for item in file_checks if isinstance(item, dict)):
        errors.append("request.readOnlyTargetFileChecks must all exist")

    if target_root is not None and target_root.exists():
        try:
            actual = collect_target_state(target_root)
            if actual["head"] != baseline.get("head"):
                errors.append("target HEAD does not match dry-run baseline")
            if actual["originMain"] != baseline.get("originMain"):
                errors.append("target origin/main does not match dry-run baseline")
            if actual["gitStatus"] != "## main...origin/main":
                errors.append("target status must stay clean/aligned")
        except (OSError, subprocess.CalledProcessError) as error:
            errors.append(f"failed to inspect target git state: {error}")

    if manifest.get("packageApplicationMode") != "non-mutating-preview-only":
        errors.append("package-manifest.packageApplicationMode must be non-mutating-preview-only")
    package_scope = manifest.get("packageScope", {})
    if not isinstance(package_scope, dict) or not package_scope.get("product") or not package_scope.get("surface"):
        errors.append("package-manifest.packageScope must declare product and surface")
    artifact_identity = manifest.get("artifactIdentity", {})
    if not isinstance(artifact_identity, dict) or not artifact_identity.get("id") or not artifact_identity.get("version"):
        errors.append("package-manifest.artifactIdentity must declare id and version")
    if manifest.get("expectedOutputs") != []:
        errors.append("package-manifest.expectedOutputs must be empty")
    for key in ["packageArtifactCreationExpected", "installerCreationExpected", "artifactSigningExpected"]:
        if manifest.get(key) is not False:
            errors.append(f"package-manifest.{key} must be false")

    build_commands = build_test.get("buildCommands", [])
    if not isinstance(build_commands, list) or not build_commands:
        errors.append("build-test.buildCommands must be non-empty")
    elif any(item.get("executeInDryRun") is not False for item in build_commands if isinstance(item, dict)):
        errors.append("build-test.buildCommands executeInDryRun must be false")
    test_plan = build_test.get("testEvidencePlan", [])
    if not isinstance(test_plan, list) or not test_plan:
        errors.append("build-test.testEvidencePlan must be non-empty")
    elif any(item.get("executeInDryRun") is not False for item in test_plan if isinstance(item, dict)):
        errors.append("build-test.testEvidencePlan executeInDryRun must be false")

    if release_notes.get("releaseNotesPreviewOnly") is not True:
        errors.append("release-notes.releaseNotesPreviewOnly must be true")
    if release_notes.get("releasePublished") is not False:
        errors.append("release-notes.releasePublished must be false")

    for key in ["credentialAccess", "providerApiCalls", "releaseTagCreation", "releasePublishing"]:
        if publish.get(key) is not False:
            errors.append(f"publish-destination.{key} must be false")

    if rollback.get("packageArtifactCreated") is not False:
        errors.append("rollback.packageArtifactCreated must be false")
    if rollback.get("releasePublished") is not False:
        errors.append("rollback.releasePublished must be false")
    if rollback.get("rollbackActionRequiredForThisDryRun") is not False:
        errors.append("rollback.rollbackActionRequiredForThisDryRun must be false")
    if not rollback.get("futureRollbackRequirements"):
        errors.append("rollback.futureRollbackRequirements must be non-empty")

    dry_run_authority = authority.get("dryRunAuthority", {})
    if dry_run_authority.get("nonMutatingPackagingReleaseDryRunRecorded") is not True:
        errors.append("authority.dryRunAuthority.nonMutatingPackagingReleaseDryRunRecorded must be true")
    for key in [
        "packageArtifactCreationAuthorized",
        "installerCreationAuthorized",
        "artifactSigningAuthorized",
        "credentialAccessAuthorized",
        "providerApiCallsAuthorized",
        "releaseTagCreationAuthorized",
        "releasePublishingAuthorized",
        "aiSelfAuthorizationAllowed",
        "productizationAuthorized",
    ]:
        if dry_run_authority.get(key) is not False:
            errors.append(f"authority.dryRunAuthority.{key} must be false")

    output_files = [str((out_dir / name).resolve()) for name in artifacts]
    return {
        "artifactRole": "intentgraph-windowsutility-packaging-release-dry-run-validation-report",
        "status": "intentgraph-windowsutility-packaging-release-dry-run-validation-passed"
        if not errors
        else "intentgraph-windowsutility-packaging-release-dry-run-validation-failed",
        "scope": SCOPE,
        "workItem": WORK_ITEM,
        "date": DATE,
        "reportVersion": REPORT_VERSION,
        "result": "pass" if not errors else "fail",
        "summary": {
            "artifactCount": len(artifacts),
            "readOnlyTargetFileCheckCount": len(file_checks) if isinstance(file_checks, list) else 0,
            "buildCommandCount": len(build_commands) if isinstance(build_commands, list) else 0,
            "testEvidencePlanCount": len(test_plan) if isinstance(test_plan, list) else 0,
            "errorCount": len(errors),
        },
        "outputFiles": output_files,
        "authorizations": empty_authorizations(),
        "errors": errors,
    }


def emit(
    repo_root: Path,
    target_root: Path,
    boundary_report: Path,
    workbench_report: Path,
    out_dir: Path,
) -> dict[str, Any]:
    artifacts = build_artifacts(repo_root, target_root, boundary_report, workbench_report)
    out_dir.mkdir(parents=True, exist_ok=True)
    for filename, data in artifacts.items():
        write_json(out_dir / filename, data)
    validation = validate_dry_run_dir(out_dir, target_root=target_root)
    write_json(out_dir / VALIDATION_REPORT_FILE, validation)
    return validation


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit a non-mutating WindowsUtility packaging/release dry run.")
    parser.add_argument("--boundary-report", required=True, type=Path)
    parser.add_argument("--workbench-report", required=True, type=Path)
    parser.add_argument("--target-root", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    try:
        report = emit(
            repo_root=repo_root,
            target_root=args.target_root,
            boundary_report=args.boundary_report,
            workbench_report=args.workbench_report,
            out_dir=args.out_dir,
        )
    except (OSError, json.JSONDecodeError, ValueError, subprocess.CalledProcessError) as error:
        print(f"emit WindowsUtility packaging/release dry-run failed: {error}")
        return 1
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
