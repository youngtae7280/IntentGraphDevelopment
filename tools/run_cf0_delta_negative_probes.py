"""Run repeatable negative probes for the CF0 P1.3 delta verifier."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path
from typing import Any

from cf0_probe_support import (
    REPORT_VERSION,
    ROOT,
    read_json,
    run_negative_probe,
    run_positive_baseline,
    write_json,
)

GOOD_DELTA = ROOT / "docs/examples/cf0-python-cli-calculator/deltas/p1.3-add-mul.delta.json"
BEFORE_FACTS = ROOT / "generated/cf0-python-cli-calculator/p1.3-before-code-facts.json"
BEFORE_OVERLAY = ROOT / "generated/cf0-python-cli-calculator/p1.3-before-overlay.json"
AFTER_FACTS = ROOT / "generated/cf0-python-cli-calculator/p1.3-after-code-facts.json"
AFTER_OVERLAY = ROOT / "generated/cf0-python-cli-calculator/p1.3-after-overlay.json"
SOURCE_ROOT = ROOT / "generated/cf0-python-cli-calculator/p1.3-after-source"
VERIFIER = ROOT / "tools/verify_code_first_delta.py"


def set_wrong_before_source_digest(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    delta["before"]["sourceDigest"] = "sha256:0000"
    return {}


def set_wrong_before_overlay_digest(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    delta["before"]["overlayDigest"] = "sha256:0000"
    return {}


def set_wrong_before_mapping_count(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    delta["before"]["mappingObligationCount"] = 999
    return {}


def add_missing_expected_fact(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    delta["expectedAfter"]["addedCodeFactIds"].append("fact.function.missing")
    return {}


def add_missing_evidence_id(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    delta["evidenceIds"] = ["evidence.missing"]
    return {}


def add_missing_authority_id(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    delta["authorityIds"] = ["authority.missing"]
    return {}


def add_missing_history_id(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    delta["historyIds"] = ["history.missing"]
    return {}


def require_source_text_equality(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    delta["sourceTextEqualityRequired"] = True
    return {}


def use_hidden_generated_snapshot(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    delta["hiddenGeneratedCodeSnapshotUsed"] = True
    return {}


PROBES: list[dict[str, Any]] = [
    {
        "id": "wrong-before-source-digest",
        "mutation": "Set delta.before.sourceDigest to sha256:0000.",
        "expectedErrorSubstring": "before source digest does not match before code facts",
        "mutate": set_wrong_before_source_digest,
    },
    {
        "id": "wrong-before-overlay-digest",
        "mutation": "Set delta.before.overlayDigest to sha256:0000.",
        "expectedErrorSubstring": "before overlay digest does not match before overlay artifact",
        "mutate": set_wrong_before_overlay_digest,
    },
    {
        "id": "wrong-before-mapping-obligation-count",
        "mutation": "Set delta.before.mappingObligationCount to 999.",
        "expectedErrorSubstring": "before mapping obligation count does not match before overlay artifact",
        "mutate": set_wrong_before_mapping_count,
    },
    {
        "id": "missing-added-code-fact",
        "mutation": "Add fact.function.missing to expected added code facts.",
        "expectedErrorSubstring": "missing expected added facts",
        "mutate": add_missing_expected_fact,
    },
    {
        "id": "missing-evidence-id",
        "mutation": "Replace delta evidence ids with evidence.missing.",
        "expectedErrorSubstring": "missing delta evidence records",
        "mutate": add_missing_evidence_id,
    },
    {
        "id": "missing-authority-id",
        "mutation": "Replace delta authority ids with authority.missing.",
        "expectedErrorSubstring": "missing delta authority records",
        "mutate": add_missing_authority_id,
    },
    {
        "id": "missing-history-id",
        "mutation": "Replace delta history ids with history.missing.",
        "expectedErrorSubstring": "missing delta history records",
        "mutate": add_missing_history_id,
    },
    {
        "id": "source-text-equality-true",
        "mutation": "Set sourceTextEqualityRequired to true.",
        "expectedErrorSubstring": "delta must not require source text equality",
        "mutate": require_source_text_equality,
    },
    {
        "id": "hidden-generated-code-snapshot-true",
        "mutation": "Set hiddenGeneratedCodeSnapshotUsed to true.",
        "expectedErrorSubstring": "delta must not use hidden generated-code snapshots",
        "mutate": use_hidden_generated_snapshot,
    },
]


def build_report() -> dict[str, Any]:
    good_delta = read_json(GOOD_DELTA)
    good_after_facts = read_json(AFTER_FACTS)
    good_overlay = read_json(AFTER_OVERLAY)
    base_paths = {
        "delta": GOOD_DELTA,
        "before_facts": BEFORE_FACTS,
        "before_overlay": BEFORE_OVERLAY,
        "after_facts": AFTER_FACTS,
        "after_overlay": AFTER_OVERLAY,
    }
    with tempfile.TemporaryDirectory(prefix="cf0-delta-negative-probes-") as tmp_name:
        tmp = Path(tmp_name)
        baseline = run_positive_baseline(VERIFIER, base_paths, SOURCE_ROOT, tmp / "positive-baseline-report.json")
        probes = [
            run_negative_probe(probe, good_delta, good_after_facts, good_overlay, base_paths, SOURCE_ROOT, VERIFIER, tmp)
            for probe in PROBES
        ]

    baseline_passed = baseline.get("rerunResult") == "pass" and baseline.get("exitCode") == 0
    all_passed = baseline_passed and all(probe["expectedFailureObserved"] is True for probe in probes)
    return {
        "reportVersion": REPORT_VERSION,
        "mode": "cf0-code-first-delta-negative-probes",
        "baselineScope": "historical-p1.3-additive-after-state",
        "currentCodeFactsUsed": False,
        "currentOverlayUsed": False,
        "historicalSourceUsed": True,
        "result": "pass" if all_passed else "fail",
        "probeCount": len(probes),
        "probes": probes,
        "positiveBaseline": {
            "scope": "historical-p1.3-additive-after-state",
            "rerunResult": baseline.get("rerunResult"),
            "exitCode": baseline.get("exitCode"),
            "sourceTextEqualityRequired": baseline.get("sourceTextEqualityRequired"),
            "hiddenGeneratedCodeSnapshotUsed": baseline.get("hiddenGeneratedCodeSnapshotUsed"),
            "deltaRecordsVerification": baseline.get("deltaRecordsVerification"),
            "errors": baseline.get("errors", []),
        },
        "historicalInputs": {
            "delta": GOOD_DELTA.relative_to(ROOT).as_posix(),
            "beforeCodeFacts": BEFORE_FACTS.relative_to(ROOT).as_posix(),
            "beforeOverlay": BEFORE_OVERLAY.relative_to(ROOT).as_posix(),
            "afterCodeFacts": AFTER_FACTS.relative_to(ROOT).as_posix(),
            "afterOverlay": AFTER_OVERLAY.relative_to(ROOT).as_posix(),
            "sourceRoot": SOURCE_ROOT.relative_to(ROOT).as_posix(),
        },
        "boundaries": {
            "sourceTextEqualityRequired": False,
            "hiddenGeneratedCodeSnapshotUsed": False,
            "aiAuthorityPromoted": False,
            "broadExtractorClaimed": False,
            "generalPlannerClaimed": False,
            "historicalAdditiveBaseline": True,
            "currentRefactorStateUsed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CF0 P1.3 delta verifier negative probes.")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    report = build_report()
    write_json(args.out, report)
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
