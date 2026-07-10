"""Run negative probes for the WindowsUtility sandboxed package artifact report."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
GOOD_DIR = REPO_ROOT / "generated/windowsutility/package-artifact/p8.55"
GOOD_REPORT = GOOD_DIR / "package-artifact-probe-report.json"
TARGET_ROOT = Path(r"C:\Users\ytkim\Desktop\kyt_work\WindowsUtility")

sys.path.insert(0, str(REPO_ROOT / "tools"))
from emit_windowsutility_sandboxed_package_artifact_probe import (  # noqa: E402
    canonical_pretty,
    validate_probe_report,
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(canonical_pretty(data), encoding="utf-8")


def mutate_report(report_path: Path, mutate: Callable[[dict[str, Any]], None]) -> None:
    data = load_json(report_path)
    mutate(data)
    write_json(report_path, data)


def mutate_source_mutated(report_path: Path) -> None:
    mutate_report(report_path, lambda data: data["claimScope"].__setitem__("sourceMutated", True))


def mutate_target_mutated(report_path: Path) -> None:
    mutate_report(report_path, lambda data: data["claimScope"].__setitem__("targetMutated", True))


def mutate_artifact_signed(report_path: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["claimScope"]["artifactSigned"] = True
        data["authorizations"]["artifactSigningAuthorized"] = True

    mutate_report(report_path, mutate)


def mutate_credential_access(report_path: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["claimScope"]["credentialAccessed"] = True
        data["authorizations"]["credentialAccessAuthorized"] = True

    mutate_report(report_path, mutate)


def mutate_provider_api(report_path: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["claimScope"]["providerApiCalled"] = True
        data["authorizations"]["providerApiCallsAuthorized"] = True

    mutate_report(report_path, mutate)


def mutate_release_published(report_path: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["claimScope"]["releasePublished"] = True
        data["authorizations"]["releasePublishingAuthorized"] = True

    mutate_report(report_path, mutate)


def mutate_productization_claim(report_path: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["claimScope"]["productizationClaimed"] = True
        data["authorizations"]["productizationAuthorized"] = True

    mutate_report(report_path, mutate)


def mutate_stale_checksum(report_path: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["packageArtifact"]["sha256"] = "sha256:0000"

    mutate_report(report_path, mutate)


def mutate_missing_package_path(report_path: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["packageArtifact"]["path"] = str(report_path.parent / "missing.zip")

    mutate_report(report_path, mutate)


def mutate_unreadable_zip(report_path: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["packageArtifact"]["zipReadable"] = False

    mutate_report(report_path, mutate)


def mutate_publish_failed(report_path: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["publish"]["exitCode"] = 1

    mutate_report(report_path, mutate)


def mutate_target_final_dirty(report_path: Path) -> None:
    def mutate(data: dict[str, Any]) -> None:
        data["targetFinalState"]["cleanAligned"] = False
        data["targetFinalState"]["gitStatus"] = "## main...origin/main\n M src/WindowsUtility.App/WindowsUtility.App.csproj"

    mutate_report(report_path, mutate)


Probe = tuple[str, Callable[[Path], None], str]


PROBES: list[Probe] = [
    ("source-mutated", mutate_source_mutated, "claimScope.sourceMutated must be false"),
    ("target-mutated", mutate_target_mutated, "claimScope.targetMutated must be false"),
    ("artifact-signed", mutate_artifact_signed, "report.authorizations.artifactSigningAuthorized must be false"),
    ("credential-access", mutate_credential_access, "report.authorizations.credentialAccessAuthorized must be false"),
    ("provider-api-call", mutate_provider_api, "report.authorizations.providerApiCallsAuthorized must be false"),
    ("release-published", mutate_release_published, "report.authorizations.releasePublishingAuthorized must be false"),
    ("productization-claim", mutate_productization_claim, "report.authorizations.productizationAuthorized must be false"),
    ("stale-checksum", mutate_stale_checksum, "packageArtifact.sha256 does not match artifact bytes"),
    ("missing-package-path", mutate_missing_package_path, "packageArtifact.path must exist"),
    ("unreadable-zip-claim", mutate_unreadable_zip, "packageArtifact.zipReadable must be true"),
    ("publish-failed", mutate_publish_failed, "publish.exitCode must be 0"),
    ("target-final-dirty", mutate_target_final_dirty, "targetFinalState.cleanAligned must be true"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run WindowsUtility sandboxed package artifact negative probes.")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    positive_report = validate_probe_report(GOOD_REPORT, REPO_ROOT, TARGET_ROOT)
    positive_passed = positive_report.get("result") == "pass"
    probe_results = []

    with tempfile.TemporaryDirectory(prefix="windowsutility-package-artifact-probes-") as temp_dir:
        temp = Path(temp_dir)
        for probe_id, mutate, expected_error in PROBES:
            probe_dir = temp / probe_id
            shutil.copytree(GOOD_DIR, probe_dir)
            probe_report = probe_dir / "package-artifact-probe-report.json"
            mutate(probe_report)
            report = validate_probe_report(probe_report, REPO_ROOT, TARGET_ROOT)
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
        "artifactRole": "intentgraph-windowsutility-sandboxed-package-artifact-negative-probes-report",
        "status": "intentgraph-windowsutility-sandboxed-package-artifact-negative-probes-passed"
        if result == "pass"
        else "intentgraph-windowsutility-sandboxed-package-artifact-negative-probes-failed",
        "scope": "p8.55-sandboxed-package-artifact-negative-probes-report-only",
        "workItem": "P8.55 Sandboxed Package Artifact Creation Probe",
        "result": result,
        "positiveBaseline": {
            "report": str(GOOD_REPORT.relative_to(REPO_ROOT)).replace("\\", "/"),
            "rerunResult": positive_report.get("result"),
        },
        "probeCount": len(probe_results),
        "probes": probe_results,
        "boundary": {
            "sourceMutationsAllowed": False,
            "targetWritesAllowed": False,
            "artifactSigningAllowed": False,
            "credentialAccessAllowed": False,
            "providerApiCallsAllowed": False,
            "releasePublishingAllowed": False,
            "productizationClaimAllowed": False,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.out, report)
    return 0 if result == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
