"""Run repeatable negative probes for the CF0 P1.11 input validation delta."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path
from typing import Any

from cf0_probe_support import (
    REPORT_VERSION,
    ROOT,
    build_negative_probe_report,
    write_json,
)

GOOD_DELTA = ROOT / "docs/examples/cf0-python-cli-calculator/deltas/p1.11-overlay-invalid-integer.delta.json"
BEFORE_FACTS = ROOT / "generated/cf0-python-cli-calculator/p1.11-before-code-facts.json"
BEFORE_OVERLAY = ROOT / "generated/cf0-python-cli-calculator/p1.11-before-overlay.json"
AFTER_FACTS = ROOT / "generated/cf0-python-cli-calculator/p1.11-after-code-facts.json"
AFTER_OVERLAY = ROOT / "generated/cf0-python-cli-calculator/p1.11-after-overlay.json"
SOURCE_ROOT = ROOT / "generated/cf0-python-cli-calculator/p1.11-after-source"
VERIFIER = ROOT / "tools/verify_code_first_delta.py"


def set_source_changed_true(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    delta["expectedAfter"]["sourceChanged"] = True
    return {}


def set_overlay_changed_false(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    delta["expectedAfter"]["overlayChanged"] = False
    return {}


def set_contract_coverage_false(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    delta["expectedAfter"]["contractCoverageIncreased"] = False
    return {}


def replace_added_unit(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    delta["expectedAfter"]["addedBehaviorUnits"] = ["unit.behavior.invalid-integer-input.missing"]
    return {}


def remove_invalid_integer_fact(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    after_facts["facts"] = [
        fact
        for fact in after_facts.get("facts", [])
        if fact.get("id") != "fact.function.main.stderr.left_and_right_must_be_integers"
    ]
    after_facts_path = tmp / "after-facts.json"
    write_json(after_facts_path, after_facts)
    return {"after_facts": after_facts_path}


def remove_invalid_integer_verification(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    overlay["verification"] = [
        item for item in overlay.get("verification", []) if item.get("id") != "test.case.invalid-integer"
    ]
    overlay_path = tmp / "overlay.json"
    write_json(overlay_path, overlay)
    return {"after_overlay": overlay_path}


def remove_expected_stderr(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    for item in overlay.get("verification", []):
        if item.get("id") == "test.case.invalid-integer":
            item.pop("expectedStderr", None)
    overlay_path = tmp / "overlay.json"
    write_json(overlay_path, overlay)
    return {"after_overlay": overlay_path}


def set_wrong_expected_stderr(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    for item in overlay.get("verification", []):
        if item.get("id") == "test.case.invalid-integer":
            item["expectedStderr"] = "wrong stderr\n"
    overlay_path = tmp / "overlay.json"
    write_json(overlay_path, overlay)
    return {"after_overlay": overlay_path}


def set_wrong_expected_exit_code(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    for item in overlay.get("verification", []):
        if item.get("id") == "test.case.invalid-integer":
            item["expectedExitCode"] = 0
    overlay_path = tmp / "overlay.json"
    write_json(overlay_path, overlay)
    return {"after_overlay": overlay_path}


def set_missing_evidence_id(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    delta["evidenceIds"] = ["evidence.p1.11-missing"]
    return {}


def set_missing_authority_id(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    delta["authorityIds"] = ["authority.record.p1.11-missing"]
    return {}


def set_missing_history_id(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    delta["historyIds"] = ["history.delta.p1.11-missing"]
    return {}


def require_source_text_equality(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    delta["sourceTextEqualityRequired"] = True
    return {}


def use_hidden_generated_snapshot(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    delta["hiddenGeneratedCodeSnapshotUsed"] = True
    return {}


PROBES: list[dict[str, Any]] = [
    {
        "id": "source-changed-true-for-unchanged-source",
        "mutation": "Set expectedAfter.sourceChanged to true while source digests are unchanged.",
        "expectedErrorSubstring": "sourceChanged expectation does not match before/after source digests",
        "mutate": set_source_changed_true,
    },
    {
        "id": "overlay-changed-false-for-overlay-change",
        "mutation": "Set expectedAfter.overlayChanged to false while overlay digest changes.",
        "expectedErrorSubstring": "overlayChanged expectation does not match before/after overlay digests",
        "mutate": set_overlay_changed_false,
    },
    {
        "id": "contract-coverage-not-increased",
        "mutation": "Set expectedAfter.contractCoverageIncreased to false.",
        "expectedErrorSubstring": "overlay-only contract delta must declare increased contract coverage",
        "mutate": set_contract_coverage_false,
    },
    {
        "id": "missing-invalid-integer-added-unit",
        "mutation": "Replace expected added behavior unit with a missing invalid-integer unit id.",
        "expectedErrorSubstring": "missing added behavior units",
        "mutate": replace_added_unit,
    },
    {
        "id": "missing-invalid-integer-code-fact",
        "mutation": "Remove fact.function.main.stderr.left_and_right_must_be_integers from after facts.",
        "expectedErrorSubstring": "references missing fact fact.function.main.stderr.left_and_right_must_be_integers",
        "mutate": remove_invalid_integer_fact,
    },
    {
        "id": "missing-invalid-integer-verification",
        "mutation": "Remove test.case.invalid-integer from after overlay verification records.",
        "expectedErrorSubstring": "missing expected behavior checks",
        "mutate": remove_invalid_integer_verification,
    },
    {
        "id": "missing-expected-stderr",
        "mutation": "Remove expectedStderr from invalid-integer verification.",
        "expectedErrorSubstring": "stderr contract missing",
        "mutate": remove_expected_stderr,
    },
    {
        "id": "wrong-expected-stderr",
        "mutation": "Set invalid-integer expectedStderr to the wrong value.",
        "expectedErrorSubstring": "stderr mismatch",
        "mutate": set_wrong_expected_stderr,
    },
    {
        "id": "wrong-expected-exit-code",
        "mutation": "Set invalid-integer expectedExitCode to 0.",
        "expectedErrorSubstring": "exit code mismatch",
        "mutate": set_wrong_expected_exit_code,
    },
    {
        "id": "missing-p1.11-evidence-id",
        "mutation": "Replace P1.11 evidence ids with a missing id.",
        "expectedErrorSubstring": "missing delta evidence records",
        "mutate": set_missing_evidence_id,
    },
    {
        "id": "missing-p1.11-authority-id",
        "mutation": "Replace P1.11 authority ids with a missing id.",
        "expectedErrorSubstring": "missing delta authority records",
        "mutate": set_missing_authority_id,
    },
    {
        "id": "missing-p1.11-history-id",
        "mutation": "Replace P1.11 history ids with a missing id.",
        "expectedErrorSubstring": "missing delta history records",
        "mutate": set_missing_history_id,
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
    with tempfile.TemporaryDirectory(prefix="cf0-input-validation-negative-probes-") as tmp_name:
        return build_negative_probe_report(
            artifact_role="intentgraph-cf0-input-validation-negative-probes-report",
            scope="cf0-p1.11-input-validation-negative-probes",
            baseline_scope="historical-p1.11-overlay-only-input-validation-delta",
            good_delta_path=GOOD_DELTA,
            before_facts_path=BEFORE_FACTS,
            before_overlay_path=BEFORE_OVERLAY,
            after_facts_path=AFTER_FACTS,
            after_overlay_path=AFTER_OVERLAY,
            source_root=SOURCE_ROOT,
            verifier=VERIFIER,
            probes=PROBES,
            tmp=Path(tmp_name),
            temp_prefix="p1.12",
            boundary_overrides={
                "historicalInputValidationBaseline": True,
                "currentP1_14ArtifactsUsed": False,
            },
            top_level_overrides={
                "currentCodeFactsUsed": False,
                "currentOverlayUsed": False,
                "historicalSourceUsed": True,
            },
            historical_inputs=True,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CF0 P1.11 input validation negative probes.")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    report = build_report()
    write_json(args.out, report)
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
