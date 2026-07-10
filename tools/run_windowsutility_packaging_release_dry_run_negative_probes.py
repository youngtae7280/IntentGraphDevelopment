"""Run negative probes for the WindowsUtility packaging/release dry run."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
GOOD_DRY_RUN_DIR = REPO_ROOT / "generated/windowsutility/packaging-release-dry-run/p8.49"
TARGET_ROOT = Path(r"C:\Users\ytkim\Desktop\kyt_work\WindowsUtility")

sys.path.insert(0, str(REPO_ROOT / "tools"))
from emit_windowsutility_packaging_release_dry_run import (  # noqa: E402
    AUTHORITY_REPORT_FILE,
    BUILD_TEST_PLAN_FILE,
    PACKAGE_MANIFEST_FILE,
    PUBLISH_DESTINATION_FILE,
    RELEASE_NOTES_FILE,
    REQUEST_FILE,
    ROLLBACK_PLAN_FILE,
    canonical_pretty,
    validate_dry_run_dir,
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(canonical_pretty(data), encoding="utf-8")


def mutate_json(directory: Path, filename: str, mutate: Callable[[dict[str, Any]], None]) -> None:
    path = directory / filename
    data = load_json(path)
    mutate(data)
    write_json(path, data)


def mutate_package_artifact_created(directory: Path) -> None:
    def mutate_request(data: dict[str, Any]) -> None:
        data["claimScope"]["packageArtifactCreated"] = True

    def mutate_manifest(data: dict[str, Any]) -> None:
        data["packageArtifactCreationExpected"] = True

    mutate_json(directory, REQUEST_FILE, mutate_request)
    mutate_json(directory, PACKAGE_MANIFEST_FILE, mutate_manifest)


def mutate_installer_created(directory: Path) -> None:
    def mutate_request(data: dict[str, Any]) -> None:
        data["claimScope"]["installerCreated"] = True

    def mutate_manifest(data: dict[str, Any]) -> None:
        data["installerCreationExpected"] = True

    mutate_json(directory, REQUEST_FILE, mutate_request)
    mutate_json(directory, PACKAGE_MANIFEST_FILE, mutate_manifest)


def mutate_artifact_signed(directory: Path) -> None:
    def mutate_request(data: dict[str, Any]) -> None:
        data["claimScope"]["artifactSigned"] = True

    def mutate_authority(data: dict[str, Any]) -> None:
        data["dryRunAuthority"]["artifactSigningAuthorized"] = True
        data["authorizations"]["artifactSigningAuthorized"] = True

    mutate_json(directory, REQUEST_FILE, mutate_request)
    mutate_json(directory, AUTHORITY_REPORT_FILE, mutate_authority)


def mutate_credential_access(directory: Path) -> None:
    def mutate_request(data: dict[str, Any]) -> None:
        data["claimScope"]["credentialAccessed"] = True

    def mutate_publish(data: dict[str, Any]) -> None:
        data["credentialAccess"] = True

    mutate_json(directory, REQUEST_FILE, mutate_request)
    mutate_json(directory, PUBLISH_DESTINATION_FILE, mutate_publish)


def mutate_provider_api_call(directory: Path) -> None:
    def mutate_request(data: dict[str, Any]) -> None:
        data["claimScope"]["providerApiCalled"] = True

    def mutate_publish(data: dict[str, Any]) -> None:
        data["providerApiCalls"] = True

    mutate_json(directory, REQUEST_FILE, mutate_request)
    mutate_json(directory, PUBLISH_DESTINATION_FILE, mutate_publish)


def mutate_release_tag_created(directory: Path) -> None:
    def mutate_request(data: dict[str, Any]) -> None:
        data["claimScope"]["releaseTagCreated"] = True

    def mutate_publish(data: dict[str, Any]) -> None:
        data["releaseTagCreation"] = True

    mutate_json(directory, REQUEST_FILE, mutate_request)
    mutate_json(directory, PUBLISH_DESTINATION_FILE, mutate_publish)


def mutate_release_published(directory: Path) -> None:
    def mutate_request(data: dict[str, Any]) -> None:
        data["claimScope"]["releasePublished"] = True

    def mutate_release_notes(data: dict[str, Any]) -> None:
        data["releasePublished"] = True

    def mutate_publish(data: dict[str, Any]) -> None:
        data["releasePublishing"] = True

    mutate_json(directory, REQUEST_FILE, mutate_request)
    mutate_json(directory, RELEASE_NOTES_FILE, mutate_release_notes)
    mutate_json(directory, PUBLISH_DESTINATION_FILE, mutate_publish)


def mutate_missing_package_scope(directory: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["packageScope"] = {}

    mutate_json(directory, PACKAGE_MANIFEST_FILE, mutate)


def mutate_missing_artifact_version(directory: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["artifactIdentity"]["version"] = ""

    mutate_json(directory, PACKAGE_MANIFEST_FILE, mutate)


def mutate_build_command_executed(directory: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["buildCommands"][0]["executeInDryRun"] = True

    mutate_json(directory, BUILD_TEST_PLAN_FILE, mutate)


def mutate_missing_test_plan(directory: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["testEvidencePlan"] = []

    mutate_json(directory, BUILD_TEST_PLAN_FILE, mutate)


def mutate_missing_rollback_plan(directory: Path) -> None:
    (directory / ROLLBACK_PLAN_FILE).unlink()


def mutate_ai_authority(directory: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["dryRunAuthority"]["aiSelfAuthorizationAllowed"] = True
        data["authorizations"]["aiAuthorityPromoted"] = True

    mutate_json(directory, AUTHORITY_REPORT_FILE, mutate)


def mutate_productization_claim(directory: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["claimScope"]["productizationClaimed"] = True

    mutate_json(directory, REQUEST_FILE, mutate)


Probe = tuple[str, Callable[[Path], None], str]


PROBES: list[Probe] = [
    ("package-artifact-created", mutate_package_artifact_created, "request.claimScope.packageArtifactCreated must be false"),
    ("installer-created", mutate_installer_created, "request.claimScope.installerCreated must be false"),
    ("artifact-signed", mutate_artifact_signed, "request.claimScope.artifactSigned must be false"),
    ("credential-access", mutate_credential_access, "request.claimScope.credentialAccessed must be false"),
    ("provider-api-call", mutate_provider_api_call, "request.claimScope.providerApiCalled must be false"),
    ("release-tag-created", mutate_release_tag_created, "request.claimScope.releaseTagCreated must be false"),
    ("release-published", mutate_release_published, "request.claimScope.releasePublished must be false"),
    ("missing-package-scope", mutate_missing_package_scope, "package-manifest.packageScope must declare product and surface"),
    ("missing-artifact-version", mutate_missing_artifact_version, "package-manifest.artifactIdentity must declare id and version"),
    ("build-command-executed", mutate_build_command_executed, "build-test.buildCommands executeInDryRun must be false"),
    ("missing-test-plan", mutate_missing_test_plan, "build-test.testEvidencePlan must be non-empty"),
    ("missing-rollback-plan", mutate_missing_rollback_plan, "missing artifact rollback-plan.json"),
    ("ai-authority", mutate_ai_authority, "authority-requirement-report.json.authorizations.aiAuthorityPromoted must be false"),
    ("productization-claim", mutate_productization_claim, "request.claimScope.productizationClaimed must be false"),
]


def copy_good_to(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for filename in [
        REQUEST_FILE,
        PACKAGE_MANIFEST_FILE,
        BUILD_TEST_PLAN_FILE,
        RELEASE_NOTES_FILE,
        PUBLISH_DESTINATION_FILE,
        ROLLBACK_PLAN_FILE,
        AUTHORITY_REPORT_FILE,
    ]:
        shutil.copy2(GOOD_DRY_RUN_DIR / filename, destination / filename)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run WindowsUtility packaging/release dry-run negative probes.")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    positive_report = validate_dry_run_dir(GOOD_DRY_RUN_DIR, target_root=TARGET_ROOT)
    positive_passed = positive_report.get("result") == "pass"
    probe_results = []

    with tempfile.TemporaryDirectory(prefix="windowsutility-packaging-release-dry-run-probes-") as temp_dir:
        temp = Path(temp_dir)
        for probe_id, mutate, expected_error in PROBES:
            probe_dir = temp / probe_id
            copy_good_to(probe_dir)
            mutate(probe_dir)
            report = validate_dry_run_dir(probe_dir, target_root=TARGET_ROOT)
            errors = report.get("errors", [])
            observed = report.get("result") == "fail" and any(expected_error in err for err in errors)
            probe_results.append(
                {
                    "id": probe_id,
                    "expectedError": expected_error,
                    "expectedFailureObserved": observed,
                    "actualErrors": errors,
                }
            )

    result = "pass" if positive_passed and all(item["expectedFailureObserved"] for item in probe_results) else "fail"
    report = {
        "artifactRole": "intentgraph-windowsutility-packaging-release-dry-run-negative-probes-report",
        "status": "intentgraph-windowsutility-packaging-release-dry-run-negative-probes-passed"
        if result == "pass"
        else "intentgraph-windowsutility-packaging-release-dry-run-negative-probes-failed",
        "scope": "p8.49-non-mutating-packaging-release-dry-run-negative-probes-report-only",
        "workItem": "P8.49 Non-Mutating Packaging/Release Dry-Run Prototype",
        "result": result,
        "positiveBaseline": {
            "dryRunDir": str(GOOD_DRY_RUN_DIR.relative_to(REPO_ROOT)).replace("\\", "/"),
            "rerunResult": "pass" if positive_passed else "fail",
        },
        "probeCount": len(probe_results),
        "probes": probe_results,
        "authorizations": {
            "sourceEditsAuthorized": False,
            "targetWritesAuthorized": False,
            "windowsUtilityBuildArtifactCreationAuthorized": False,
            "packageArtifactCreationAuthorized": False,
            "installerCreationAuthorized": False,
            "artifactSigningAuthorized": False,
            "credentialAccessAuthorized": False,
            "providerApiCallsAuthorized": False,
            "releaseTagCreationAuthorized": False,
            "releasePublishingAuthorized": False,
            "aiAuthorityPromoted": False,
            "productizationAuthorized": False,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.out, report)
    return 0 if result == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
