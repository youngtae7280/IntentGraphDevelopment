"""Run negative probes for the WindowsUtility non-applied proposal validator."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
GOOD_PROPOSAL = REPO_ROOT / "generated/windowsutility/p8.12-shell-workspace-smoke-evidence-non-applied-proposal.json"
ACCEPTED_MAPPING = REPO_ROOT / "generated/windowsutility/p8.9-shell-workspace-accepted-mapping.json"
ACCEPTED_MAPPING_VERIFICATION = REPO_ROOT / "generated/windowsutility/p8.9-shell-workspace-accepted-mapping-verification-report.json"
TARGET_ROOT = Path(r"C:\Users\ytkim\Desktop\kyt_work\WindowsUtility")
VALIDATOR = REPO_ROOT / "tools/validate_windowsutility_non_applied_proposal.py"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_validate(proposal: Path, out: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--proposal",
            str(proposal),
            "--accepted-mapping",
            str(ACCEPTED_MAPPING),
            "--accepted-mapping-verification",
            str(ACCEPTED_MAPPING_VERIFICATION),
            "--target-root",
            str(TARGET_ROOT),
            "--out",
            str(out),
        ],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
    )


def mutate_stale_mapping_digest(proposal: dict[str, Any]) -> None:
    proposal["acceptedMappingBinding"]["digest"] = "sha256:" + "0" * 64


def mutate_stale_verification_digest(proposal: dict[str, Any]) -> None:
    proposal["acceptedMappingBinding"]["verificationReportDigest"] = "sha256:" + "0" * 64


def mutate_wrong_mapping_id(proposal: dict[str, Any]) -> None:
    proposal["acceptedMappingBinding"]["mappingId"] = "mapping.windowsutility.shell-workspace.other"
    proposal["impactScope"]["mappingIds"] = ["mapping.windowsutility.shell-workspace.other"]


def mutate_stale_target_head(proposal: dict[str, Any]) -> None:
    proposal["targetBaseline"]["head"] = "0" * 40


def mutate_non_empty_source_delta(proposal: dict[str, Any]) -> None:
    proposal["proposedCodeDelta"]["plannedSourceChanges"] = [
        {
            "id": "change.p8.13-forbidden-source-edit",
            "targetFile": "src/WindowsUtility.Shell/WindowsUtility.Shell.csproj",
            "applied": False,
        }
    ]


def mutate_source_patch_expected(proposal: dict[str, Any]) -> None:
    proposal["proposedCodeDelta"]["sourcePatchExpected"] = True


def mutate_source_text_included(proposal: dict[str, Any]) -> None:
    proposal["proposedCodeDelta"]["sourceTextIncluded"] = True


def mutate_missing_evidence(proposal: dict[str, Any]) -> None:
    proposal["requiredEvidence"] = [
        item
        for item in proposal["requiredEvidence"]
        if item.get("id") != "evidence.requirement.p8.12-shell-workspace-screenshot"
    ]


def mutate_missing_authority(proposal: dict[str, Any]) -> None:
    proposal["requiredAuthority"] = []


def mutate_verification_mutates_target(proposal: dict[str, Any]) -> None:
    proposal["deterministicVerificationPlan"][0]["mutatesTarget"] = True


def mutate_target_write_authority(proposal: dict[str, Any]) -> None:
    proposal["authorizations"]["targetWritesAuthorized"] = True


def mutate_ai_authority(proposal: dict[str, Any]) -> None:
    proposal["claimScope"]["aiAuthorityGranted"] = True
    proposal["requiredAuthority"][0]["aiAuthority"] = True


def mutate_hardware_authority(proposal: dict[str, Any]) -> None:
    proposal["authorizations"]["hardwareActionsAuthorized"] = True
    proposal["claimScope"]["hardwareActionClaimed"] = True


def mutate_productization(proposal: dict[str, Any]) -> None:
    proposal["authorizations"]["productizationAuthorized"] = True
    proposal["claimScope"]["productizationClaimed"] = True


def mutate_self_authorized(proposal: dict[str, Any]) -> None:
    proposal["claimScope"]["selfAuthorized"] = True
    proposal["requiredAuthority"][0]["selfAuthorized"] = True


Probe = tuple[str, Callable[[dict[str, Any]], None], str]


PROBES: list[Probe] = [
    ("stale-accepted-mapping-digest", mutate_stale_mapping_digest, "accepted mapping digest mismatch"),
    ("stale-verification-digest", mutate_stale_verification_digest, "accepted mapping verification digest mismatch"),
    ("wrong-mapping-id", mutate_wrong_mapping_id, "accepted mapping id mismatch"),
    ("stale-target-head", mutate_stale_target_head, "target baseline must match accepted mapping target"),
    ("non-empty-source-delta", mutate_non_empty_source_delta, "proposedCodeDelta.plannedSourceChanges must be empty"),
    ("source-patch-expected-true", mutate_source_patch_expected, "proposedCodeDelta.sourcePatchExpected must be false"),
    ("source-text-included-true", mutate_source_text_included, "proposedCodeDelta.sourceTextIncluded must be false"),
    ("missing-screenshot-evidence", mutate_missing_evidence, "missing required evidence evidence.requirement.p8.12-shell-workspace-screenshot"),
    ("missing-authority", mutate_missing_authority, "requiredAuthority must include at least two authority requirements"),
    ("verification-mutates-target", mutate_verification_mutates_target, "verification step verify.p8.12-accepted-mapping must not mutate target"),
    ("target-write-authority-true", mutate_target_write_authority, "authorizations.targetWritesAuthorized must be false"),
    ("ai-authority-true", mutate_ai_authority, "claimScope.aiAuthorityGranted must be false"),
    ("hardware-authority-true", mutate_hardware_authority, "authorizations.hardwareActionsAuthorized must be false"),
    ("productization-true", mutate_productization, "authorizations.productizationAuthorized must be false"),
    ("self-authorized-true", mutate_self_authorized, "claimScope.selfAuthorized must be false"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run WindowsUtility non-applied proposal negative probes.")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    good = load_json(GOOD_PROPOSAL)
    probe_results = []

    with tempfile.TemporaryDirectory(prefix="windowsutility-non-applied-proposal-probes-") as temp_dir:
        temp = Path(temp_dir)
        positive_out = temp / "positive-report.json"
        positive = run_validate(GOOD_PROPOSAL, positive_out)
        positive_report = load_json(positive_out) if positive_out.exists() else {}
        positive_passed = positive.returncode == 0 and positive_report.get("result") == "pass"

        for probe_id, mutate, expected_error in PROBES:
            bad = copy.deepcopy(good)
            mutate(bad)
            bad_path = temp / f"{probe_id}.json"
            report_path = temp / f"{probe_id}-report.json"
            write_json(bad_path, bad)
            completed = run_validate(bad_path, report_path)
            report = load_json(report_path) if report_path.exists() else {}
            errors = report.get("errors", [])
            observed = completed.returncode != 0 and any(expected_error in err for err in errors)
            probe_results.append(
                {
                    "id": probe_id,
                    "expectedError": expected_error,
                    "expectedFailureObserved": observed,
                    "actualReturnCode": completed.returncode,
                    "actualErrors": errors,
                }
            )

    result = "pass" if positive_passed and all(p["expectedFailureObserved"] for p in probe_results) else "fail"
    report = {
        "artifactRole": "intentgraph-windowsutility-non-applied-proposal-negative-probes-report",
        "status": "intentgraph-windowsutility-non-applied-proposal-negative-probes-passed" if result == "pass" else "intentgraph-windowsutility-non-applied-proposal-negative-probes-failed",
        "scope": "p8.13-shell-workspace-non-applied-proposal-negative-probes-report-only",
        "workItem": "P8.13 Shell Workspace Non-Applied Proposal Negative Probes",
        "result": result,
        "positiveBaseline": {
            "proposal": str(GOOD_PROPOSAL.relative_to(REPO_ROOT)).replace("\\", "/"),
            "rerunResult": "pass" if positive_passed else "fail",
        },
        "probeCount": len(probe_results),
        "probes": probe_results,
        "authorizations": {
            "sourceEditsAuthorized": False,
            "proposalApplicationAuthorized": False,
            "targetWritesAuthorized": False,
            "aiAuthorityPromoted": False,
            "hardwareActionsAuthorized": False,
            "productizationAuthorized": False,
        },
    }
    write_json(Path(args.out), report)
    return 0 if result == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
