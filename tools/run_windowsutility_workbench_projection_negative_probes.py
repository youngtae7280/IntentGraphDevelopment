"""Run repeatable negative probes for the WindowsUtility workbench projection."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable

from emit_windowsutility_workbench_projection import canonical_pretty, validate_projection


GOOD_PROJECTION = Path("generated/windowsutility/workbench/p8.21-shell-workspace-evidence-workbench-projection.json")
GOOD_HTML = Path("generated/windowsutility/workbench/p8.21-shell-workspace-evidence-workbench.html")
GOOD_SCREENSHOT = Path("generated/windowsutility/p8.19-shell-workspace-sandboxed-window.png")


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def run_validation(projection: dict[str, Any], html_path: Path, screenshot_path: Path) -> dict[str, Any]:
    return validate_projection(projection, html_path, screenshot_path)


def set_first_authority_true(data: dict[str, Any]) -> None:
    data["authorityBoundary"]["targetWritesAuthorized"] = True


def set_productization_claim(data: dict[str, Any]) -> None:
    data["claimScope"]["productizationClaimed"] = True


def set_source_mutated_claim(data: dict[str, Any]) -> None:
    data["claimScope"]["sourceMutated"] = True


def set_proposal_applied(data: dict[str, Any]) -> None:
    data["proposal"]["applicationStatus"] = "applied"


def set_evidence_failed(data: dict[str, Any]) -> None:
    data["evidence"][0]["result"] = "fail"


def set_summary_evidence_false(data: dict[str, Any]) -> None:
    data["summary"]["allEvidencePassed"] = False


def remove_screenshot_path(data: dict[str, Any]) -> None:
    for card in data["evidence"]:
        if card.get("kind") == "sandboxed-screenshot":
            card["screenshotPath"] = ""


def invalidate_screenshot_png_flag(data: dict[str, Any]) -> None:
    for card in data["evidence"]:
        if card.get("kind") == "sandboxed-screenshot":
            card["validPng"] = False


def set_target_dirty(data: dict[str, Any]) -> None:
    data["target"]["current"]["status"] = "## main...origin/main\n M src/WindowsUtility.App/WindowsUtility.App.csproj"


def set_target_head_mismatch(data: dict[str, Any]) -> None:
    data["target"]["current"]["originMain"] = "0000000000000000000000000000000000000000"


def remove_selection_records(data: dict[str, Any]) -> None:
    data["selectionRecords"] = []


def mark_source_artifact_missing(data: dict[str, Any]) -> None:
    data["sourceArtifacts"][0]["exists"] = False


def remove_source_artifact_digest(data: dict[str, Any]) -> None:
    data["sourceArtifacts"][0]["sha256"] = ""


PROBES: list[tuple[str, Callable[[dict[str, Any]], None], str]] = [
    ("target-write-authority-true", set_first_authority_true, "authorityBoundary.targetWritesAuthorized must be false"),
    ("productization-claim-true", set_productization_claim, "claimScope.productizationClaimed must be false"),
    ("source-mutated-claim-true", set_source_mutated_claim, "claimScope.sourceMutated must be false"),
    ("proposal-applied", set_proposal_applied, "proposal must remain not-applied"),
    ("evidence-card-failed", set_evidence_failed, "all evidence cards must pass"),
    ("summary-evidence-false", set_summary_evidence_false, "all linked evidence cards must pass"),
    ("missing-screenshot-path", remove_screenshot_path, "screenshot evidence must include screenshotPath"),
    ("invalid-screenshot-png-flag", invalidate_screenshot_png_flag, "screenshot evidence must validate PNG"),
    ("target-dirty", set_target_dirty, "current WindowsUtility target must be clean/aligned"),
    ("target-head-mismatch", set_target_head_mismatch, "current WindowsUtility HEAD must match origin/main"),
    ("missing-selection-records", remove_selection_records, "projection must expose at least five selection records"),
    ("missing-source-artifact", mark_source_artifact_missing, "source artifact missing"),
    ("missing-source-artifact-digest", remove_source_artifact_digest, "source artifact digest missing"),
]


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run WindowsUtility workbench projection negative probes.")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    good_projection = read_json(GOOD_PROJECTION)
    positive = run_validation(good_projection, GOOD_HTML, GOOD_SCREENSHOT)
    probes: list[dict[str, Any]] = []

    with TemporaryDirectory(prefix="intentgraph-windowsutility-workbench-probes-") as tmp:
        tmp_root = Path(tmp)
        missing_html = tmp_root / "missing-marker.html"
        missing_html.write_text(GOOD_HTML.read_text(encoding="utf-8").replace("Authority and safety boundary", ""), encoding="utf-8")

        missing_screenshot = tmp_root / "missing.png"

        for probe_id, mutate, expected in PROBES:
            candidate = copy.deepcopy(good_projection)
            mutate(candidate)
            report = run_validation(candidate, GOOD_HTML, GOOD_SCREENSHOT)
            errors = report.get("errors", [])
            expected_observed = report.get("result") == "fail" and any(expected in error for error in errors)
            probes.append(
                {
                    "id": probe_id,
                    "result": report.get("result"),
                    "expectedFailureObserved": expected_observed,
                    "expectedErrorSubstring": expected,
                    "actualErrors": errors,
                }
            )

        html_report = run_validation(good_projection, missing_html, GOOD_SCREENSHOT)
        probes.append(
            {
                "id": "html-missing-authority-marker",
                "result": html_report.get("result"),
                "expectedFailureObserved": html_report.get("result") == "fail"
                and any("html preview missing marker Authority and safety boundary" in error for error in html_report.get("errors", [])),
                "expectedErrorSubstring": "html preview missing marker Authority and safety boundary",
                "actualErrors": html_report.get("errors", []),
            }
        )

        screenshot_report = run_validation(good_projection, GOOD_HTML, missing_screenshot)
        probes.append(
            {
                "id": "screenshot-file-missing",
                "result": screenshot_report.get("result"),
                "expectedFailureObserved": screenshot_report.get("result") == "fail"
                and any("screenshot PNG missing" in error for error in screenshot_report.get("errors", [])),
                "expectedErrorSubstring": "screenshot PNG missing",
                "actualErrors": screenshot_report.get("errors", []),
            }
        )

    all_passed = positive.get("result") == "pass" and all(probe["expectedFailureObserved"] for probe in probes)
    report = {
        "artifactRole": "intentgraph-windowsutility-workbench-negative-probes-report",
        "status": "intentgraph-windowsutility-workbench-negative-probes-passed" if all_passed else "intentgraph-windowsutility-workbench-negative-probes-failed",
        "scope": "p8.22-shell-workspace-workbench-projection-negative-probes",
        "workItem": "P8.22 Shell Workspace Workbench Projection Negative Probes",
        "result": "pass" if all_passed else "fail",
        "positiveBaseline": {
            "projection": GOOD_PROJECTION.as_posix(),
            "html": GOOD_HTML.as_posix(),
            "screenshot": GOOD_SCREENSHOT.as_posix(),
            "rerunResult": positive.get("result"),
            "errors": positive.get("errors", []),
        },
        "probeCount": len(probes),
        "probes": probes,
        "claimScope": {
            "targetMutated": False,
            "sourceMutated": False,
            "proposalApplied": False,
            "aiAuthorityGranted": False,
            "hardwareActionClaimed": False,
            "productizationClaimed": False,
            "badFixturesCommitted": False,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(canonical_pretty(report), encoding="utf-8")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
