"""Run repeatable negative probes for the CF0 P1.9 overlay-only delta."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable


REPORT_VERSION = "0.1.0"

ROOT = Path(__file__).resolve().parents[1]
GOOD_DELTA = ROOT / "docs/examples/cf0-python-cli-calculator/deltas/p1.9-overlay-unsupported-operation.delta.json"
BEFORE_FACTS = ROOT / "generated/cf0-python-cli-calculator/p1.9-before-code-facts.json"
BEFORE_OVERLAY = ROOT / "generated/cf0-python-cli-calculator/p1.9-before-overlay.json"
AFTER_FACTS = ROOT / "generated/cf0-python-cli-calculator/p1.9-after-code-facts.json"
AFTER_OVERLAY = ROOT / "generated/cf0-python-cli-calculator/p1.9-after-overlay.json"
SOURCE_ROOT = ROOT / "generated/cf0-python-cli-calculator/p1.9-after-source"
VERIFIER = ROOT / "tools/verify_code_first_delta.py"

Mutation = Callable[[dict[str, Any], dict[str, Any], dict[str, Any], Path], dict[str, Path]]


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def run_verifier(paths: dict[str, Path], out: Path) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(VERIFIER),
        "--delta",
        str(paths["delta"]),
        "--before-code-facts",
        str(paths["before_facts"]),
        "--before-overlay",
        str(paths["before_overlay"]),
        "--after-code-facts",
        str(paths["after_facts"]),
        "--overlay",
        str(paths["after_overlay"]),
        "--source-root",
        str(SOURCE_ROOT),
        "--out",
        str(out),
    ]
    return subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)


def set_source_changed_true(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    delta["expectedAfter"]["sourceChanged"] = True
    return {}


def set_overlay_changed_false(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    delta["expectedAfter"]["overlayChanged"] = False
    return {}


def set_contract_coverage_false(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    delta["expectedAfter"]["contractCoverageIncreased"] = False
    return {}


def remove_added_unit_expectation(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    delta["expectedAfter"]["addedBehaviorUnits"] = ["unit.behavior.unsupported-operation.missing"]
    return {}


def remove_unsupported_fact(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    after_facts["facts"] = [
        fact
        for fact in after_facts.get("facts", [])
        if fact.get("id") != "fact.function.main.stderr.unsupported_operation"
    ]
    after_facts_path = tmp / "after-facts.json"
    write_json(after_facts_path, after_facts)
    return {"after_facts": after_facts_path}


def remove_unsupported_verification(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    overlay["verification"] = [
        item for item in overlay.get("verification", []) if item.get("id") != "test.case.unsupported-operation"
    ]
    overlay_path = tmp / "overlay.json"
    write_json(overlay_path, overlay)
    return {"after_overlay": overlay_path}


def remove_expected_stderr(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    for item in overlay.get("verification", []):
        if item.get("id") == "test.case.unsupported-operation":
            item.pop("expectedStderr", None)
    overlay_path = tmp / "overlay.json"
    write_json(overlay_path, overlay)
    return {"after_overlay": overlay_path}


def set_wrong_expected_stderr(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    for item in overlay.get("verification", []):
        if item.get("id") == "test.case.unsupported-operation":
            item["expectedStderr"] = "wrong stderr\n"
    overlay_path = tmp / "overlay.json"
    write_json(overlay_path, overlay)
    return {"after_overlay": overlay_path}


def set_missing_evidence_id(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    delta["evidenceIds"] = ["evidence.p1.9-missing"]
    return {}


def set_missing_authority_id(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    delta["authorityIds"] = ["authority.record.p1.9-missing"]
    return {}


def set_missing_history_id(delta: dict[str, Any], after_facts: dict[str, Any], overlay: dict[str, Any], tmp: Path) -> dict[str, Path]:
    delta["historyIds"] = ["history.delta.p1.9-missing"]
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
        "id": "missing-unsupported-added-unit",
        "mutation": "Replace expected added behavior unit with a missing unit id.",
        "expectedErrorSubstring": "missing added behavior units",
        "mutate": remove_added_unit_expectation,
    },
    {
        "id": "missing-unsupported-code-fact",
        "mutation": "Remove fact.function.main.stderr.unsupported_operation from after facts.",
        "expectedErrorSubstring": "missing expected added facts",
        "mutate": remove_unsupported_fact,
    },
    {
        "id": "missing-unsupported-verification",
        "mutation": "Remove test.case.unsupported-operation from after overlay verification records.",
        "expectedErrorSubstring": "missing expected behavior checks",
        "mutate": remove_unsupported_verification,
    },
    {
        "id": "missing-expected-stderr",
        "mutation": "Remove expectedStderr from unsupported-operation verification.",
        "expectedErrorSubstring": "stderr contract missing",
        "mutate": remove_expected_stderr,
    },
    {
        "id": "wrong-expected-stderr",
        "mutation": "Set unsupported-operation expectedStderr to the wrong value.",
        "expectedErrorSubstring": "stderr mismatch",
        "mutate": set_wrong_expected_stderr,
    },
    {
        "id": "missing-p1.9-evidence-id",
        "mutation": "Replace P1.9 evidence ids with a missing id.",
        "expectedErrorSubstring": "missing delta evidence records",
        "mutate": set_missing_evidence_id,
    },
    {
        "id": "missing-p1.9-authority-id",
        "mutation": "Replace P1.9 authority ids with a missing id.",
        "expectedErrorSubstring": "missing delta authority records",
        "mutate": set_missing_authority_id,
    },
    {
        "id": "missing-p1.9-history-id",
        "mutation": "Replace P1.9 history ids with a missing id.",
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


def run_positive_baseline(tmp: Path) -> dict[str, Any]:
    report_path = tmp / "positive-baseline-report.json"
    paths = {
        "delta": GOOD_DELTA,
        "before_facts": BEFORE_FACTS,
        "before_overlay": BEFORE_OVERLAY,
        "after_facts": AFTER_FACTS,
        "after_overlay": AFTER_OVERLAY,
    }
    completed = run_verifier(paths, report_path)
    verifier_report = read_json(report_path) if report_path.exists() else {}
    return {
        "rerunResult": verifier_report.get("result"),
        "exitCode": completed.returncode,
        "deltaReport": report_path.as_posix(),
        "sourceChanged": verifier_report.get("delta", {}).get("sourceChanged"),
        "overlayChanged": verifier_report.get("delta", {}).get("overlayChanged"),
        "contractCoverageIncreased": verifier_report.get("delta", {}).get("contractCoverageIncreased"),
        "sourceTextEqualityRequired": verifier_report.get("sourceTextEqualityRequired"),
        "hiddenGeneratedCodeSnapshotUsed": verifier_report.get("hiddenGeneratedCodeSnapshotUsed"),
        "errors": verifier_report.get("errors", []),
    }


def run_probe(probe: dict[str, Any], good_delta: dict[str, Any], good_after_facts: dict[str, Any], good_overlay: dict[str, Any], tmp: Path) -> dict[str, Any]:
    probe_dir = tmp / probe["id"]
    probe_dir.mkdir(parents=True)
    delta = deepcopy(good_delta)
    after_facts = deepcopy(good_after_facts)
    overlay = deepcopy(good_overlay)
    overrides = probe["mutate"](delta, after_facts, overlay, probe_dir)
    delta_path = probe_dir / "delta.json"
    report_path = probe_dir / "verifier-report.json"
    write_json(delta_path, delta)

    paths = {
        "delta": delta_path,
        "before_facts": BEFORE_FACTS,
        "before_overlay": BEFORE_OVERLAY,
        "after_facts": AFTER_FACTS,
        "after_overlay": AFTER_OVERLAY,
    }
    paths.update(overrides)
    completed = run_verifier(paths, report_path)
    verifier_report = read_json(report_path) if report_path.exists() else {}
    errors = verifier_report.get("errors", [])
    if not isinstance(errors, list):
        errors = []
    joined_errors = "\n".join(str(error) for error in errors)
    expected = probe["expectedErrorSubstring"]
    expected_failure_observed = (
        completed.returncode != 0
        and verifier_report.get("result") == "fail"
        and expected in joined_errors
    )
    return {
        "id": probe["id"],
        "mutation": probe["mutation"],
        "expectedErrorSubstring": expected,
        "actualExitCode": completed.returncode,
        "actualVerifierResult": verifier_report.get("result"),
        "actualErrors": errors,
        "actualMessage": (completed.stdout + completed.stderr).strip(),
        "expectedFailureObserved": expected_failure_observed,
    }


def build_report() -> dict[str, Any]:
    good_delta = read_json(GOOD_DELTA)
    good_after_facts = read_json(AFTER_FACTS)
    good_overlay = read_json(AFTER_OVERLAY)
    with tempfile.TemporaryDirectory(prefix="cf0-overlay-contract-negative-probes-") as tmp_name:
        tmp = Path(tmp_name)
        baseline = run_positive_baseline(tmp)
        probes = [run_probe(probe, good_delta, good_after_facts, good_overlay, tmp) for probe in PROBES]

    baseline_passed = baseline.get("rerunResult") == "pass" and baseline.get("exitCode") == 0
    all_passed = baseline_passed and all(probe["expectedFailureObserved"] is True for probe in probes)
    source_digest = good_after_facts.get("source", {}).get("sha256")
    before_source_digest = read_json(BEFORE_FACTS).get("source", {}).get("sha256")
    return {
        "artifactRole": "intentgraph-cf0-overlay-contract-negative-probes-report",
        "reportVersion": REPORT_VERSION,
        "status": "pass" if all_passed else "fail",
        "result": "pass" if all_passed else "fail",
        "scope": "cf0-p1.9-overlay-contract-negative-probes",
        "baselineScope": "historical-p1.9-overlay-only-contract-delta",
        "currentCodeFactsUsed": False,
        "currentOverlayUsed": False,
        "historicalSourceUsed": True,
        "baselineDelta": GOOD_DELTA.relative_to(ROOT).as_posix(),
        "positiveBaseline": {
            "rerunResult": baseline.get("rerunResult"),
            "exitCode": baseline.get("exitCode"),
            "sourceChanged": baseline.get("sourceChanged"),
            "overlayChanged": baseline.get("overlayChanged"),
            "contractCoverageIncreased": baseline.get("contractCoverageIncreased"),
            "sourceTextEqualityRequired": baseline.get("sourceTextEqualityRequired"),
            "hiddenGeneratedCodeSnapshotUsed": baseline.get("hiddenGeneratedCodeSnapshotUsed"),
            "errors": baseline.get("errors", []),
        },
        "probeCount": len(probes),
        "probes": probes,
        "boundaries": {
            "sourceBytesUnchanged": source_digest == before_source_digest,
            "sourceTextEqualityRequired": False,
            "hiddenGeneratedCodeSnapshotUsed": False,
            "aiAuthorityPromoted": False,
            "productBehaviorAdded": False,
            "generalNegativeProbeFrameworkClaimed": False,
            "currentP1_11ArtifactsUsed": False,
        },
        "historicalInputs": {
            "delta": GOOD_DELTA.relative_to(ROOT).as_posix(),
            "beforeCodeFacts": BEFORE_FACTS.relative_to(ROOT).as_posix(),
            "beforeOverlay": BEFORE_OVERLAY.relative_to(ROOT).as_posix(),
            "afterCodeFacts": AFTER_FACTS.relative_to(ROOT).as_posix(),
            "afterOverlay": AFTER_OVERLAY.relative_to(ROOT).as_posix(),
            "sourceRoot": SOURCE_ROOT.relative_to(ROOT).as_posix(),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run CF0 P1.9 overlay contract negative probes.")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    report = build_report()
    write_json(args.out, report)
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
