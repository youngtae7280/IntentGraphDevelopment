"""Run negative probes for the WindowsUtility source application dry-run."""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
GOOD_DRY_RUN_DIR = REPO_ROOT / "generated/windowsutility/source-application-dry-run/p8.41"
TARGET_ROOT = Path(r"C:\Users\ytkim\Desktop\kyt_work\WindowsUtility")

sys.path.insert(0, str(REPO_ROOT / "tools"))
from emit_windowsutility_source_application_dry_run import (  # noqa: E402
    AUTHORITY_REPORT_FILE,
    CHANGE_SET_FILE,
    EVIDENCE_PLAN_FILE,
    REQUEST_FILE,
    ROLLBACK_PLAN_FILE,
    TOUCHED_FILE_FILE,
    VALIDATION_REPORT_FILE,
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


def mutate_source_write_claim(directory: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["authorizations"]["sourceEditsAuthorized"] = True

    mutate_json(directory, REQUEST_FILE, mutate)


def mutate_proposal_applied(directory: Path) -> None:
    def mutate_request(data: dict[str, Any]) -> None:
        data["claimScope"]["proposalApplied"] = True

    def mutate_change_set(data: dict[str, Any]) -> None:
        data["applicationStatus"] = "applied"

    mutate_json(directory, REQUEST_FILE, mutate_request)
    mutate_json(directory, CHANGE_SET_FILE, mutate_change_set)


def mutate_dirty_target_baseline(directory: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["targetBaseline"]["cleanAligned"] = False
        data["targetBaseline"]["gitStatus"] = "## main...origin/main\n M src/WindowsUtility.App/WindowsUtility.App.csproj"

    mutate_json(directory, REQUEST_FILE, mutate)


def mutate_missing_touched_file_scope(directory: Path) -> None:
    def mutate_change_set(data: dict[str, Any]) -> None:
        data["intendedTouchedFiles"] = []

    def mutate_touched(data: dict[str, Any]) -> None:
        data["fileCount"] = 0
        data["results"] = []

    mutate_json(directory, CHANGE_SET_FILE, mutate_change_set)
    mutate_json(directory, TOUCHED_FILE_FILE, mutate_touched)


def mutate_missing_evidence_plan(directory: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["requiredEvidence"] = []
        data["preApplicationEvidence"] = []

    mutate_json(directory, EVIDENCE_PLAN_FILE, mutate)


def mutate_missing_rollback_plan(directory: Path) -> None:
    (directory / ROLLBACK_PLAN_FILE).unlink()


def mutate_ai_authority(directory: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["dryRunAuthority"]["aiSelfAuthorizationAllowed"] = True
        data["authorizations"]["aiAuthorityPromoted"] = True

    mutate_json(directory, AUTHORITY_REPORT_FILE, mutate)


def mutate_hardware_authority(directory: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["dryRunAuthority"]["hardwareActionsAuthorized"] = True
        data["authorizations"]["hardwareActionsAuthorized"] = True

    mutate_json(directory, AUTHORITY_REPORT_FILE, mutate)


def mutate_packaging_release_authority(directory: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["dryRunAuthority"]["packagingAuthorized"] = True
        data["dryRunAuthority"]["releaseAuthorized"] = True
        data["authorizations"]["packagingAuthorized"] = True
        data["authorizations"]["releaseAuthorized"] = True

    mutate_json(directory, AUTHORITY_REPORT_FILE, mutate)


def mutate_patch_operation(directory: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["operationCount"] = 1
        data["operations"] = [
            {
                "id": "operation.forbidden-source-patch",
                "targetFile": "src/WindowsUtility.Shell/WindowsUtility.Shell.csproj",
                "writeExpected": True,
            }
        ]

    mutate_json(directory, CHANGE_SET_FILE, mutate)


def mutate_source_patch_expected(directory: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["sourcePatchExpected"] = True

    mutate_json(directory, CHANGE_SET_FILE, mutate)


def mutate_windowsutility_generated_write(directory: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["authorizations"]["windowsUtilityGeneratedWritesAuthorized"] = True

    mutate_json(directory, REQUEST_FILE, mutate)


Probe = tuple[str, Callable[[Path], None], str]


PROBES: list[Probe] = [
    ("source-write-claimed", mutate_source_write_claim, "dry-run-request.json.authorizations.sourceEditsAuthorized must be false"),
    ("proposal-applied-claimed", mutate_proposal_applied, "request.claimScope.proposalApplied must be false"),
    ("dirty-target-baseline", mutate_dirty_target_baseline, "request.targetBaseline.cleanAligned must be true"),
    ("missing-touched-file-scope", mutate_missing_touched_file_scope, "change-set.intendedTouchedFiles must be non-empty"),
    ("missing-evidence-plan", mutate_missing_evidence_plan, "evidence-plan.requiredEvidence must include at least four items"),
    ("missing-rollback-plan", mutate_missing_rollback_plan, "missing artifact rollback-plan.json"),
    ("ai-authority-true", mutate_ai_authority, "authority-requirement-report.json.authorizations.aiAuthorityPromoted must be false"),
    ("hardware-authority-true", mutate_hardware_authority, "authority-requirement-report.json.authorizations.hardwareActionsAuthorized must be false"),
    ("packaging-release-authority-true", mutate_packaging_release_authority, "authority-requirement-report.json.authorizations.packagingAuthorized must be false"),
    ("patch-operation-present", mutate_patch_operation, "change-set.operationCount must be 0"),
    ("source-patch-expected-true", mutate_source_patch_expected, "change-set.sourcePatchExpected must be false"),
    ("windowsutility-generated-write-authority", mutate_windowsutility_generated_write, "dry-run-request.json.authorizations.windowsUtilityGeneratedWritesAuthorized must be false"),
]


def copy_good_to(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for filename in [
        REQUEST_FILE,
        CHANGE_SET_FILE,
        TOUCHED_FILE_FILE,
        EVIDENCE_PLAN_FILE,
        ROLLBACK_PLAN_FILE,
        AUTHORITY_REPORT_FILE,
    ]:
        shutil.copy2(GOOD_DRY_RUN_DIR / filename, destination / filename)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run WindowsUtility source application dry-run negative probes.")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    positive_report = validate_dry_run_dir(GOOD_DRY_RUN_DIR, target_root=TARGET_ROOT)
    positive_passed = positive_report.get("result") == "pass"
    probe_results = []

    with tempfile.TemporaryDirectory(prefix="windowsutility-source-application-dry-run-probes-") as temp_dir:
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
        "artifactRole": "intentgraph-windowsutility-source-application-dry-run-negative-probes-report",
        "status": "intentgraph-windowsutility-source-application-dry-run-negative-probes-passed"
        if result == "pass"
        else "intentgraph-windowsutility-source-application-dry-run-negative-probes-failed",
        "scope": "p8.41-non-mutating-source-application-dry-run-negative-probes-report-only",
        "workItem": "P8.41 Non-Mutating Source Application Dry-Run Prototype",
        "result": result,
        "positiveBaseline": {
            "dryRunDir": str(GOOD_DRY_RUN_DIR.relative_to(REPO_ROOT)).replace("\\", "/"),
            "rerunResult": "pass" if positive_passed else "fail",
        },
        "probeCount": len(probe_results),
        "probes": probe_results,
        "authorizations": {
            "sourceEditsAuthorized": False,
            "proposalApplicationAuthorized": False,
            "targetWritesAuthorized": False,
            "windowsUtilityGeneratedWritesAuthorized": False,
            "gitIndexMutationAuthorized": False,
            "windowsUtilityCommitAuthorized": False,
            "windowsUtilityPushAuthorized": False,
            "aiAuthorityPromoted": False,
            "hardwareActionsAuthorized": False,
            "packagingAuthorized": False,
            "releaseAuthorized": False,
            "productizationAuthorized": False,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.out, report)
    return 0 if result == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
