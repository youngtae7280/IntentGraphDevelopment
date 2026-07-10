"""Shared CF0 negative-probe mechanics.

This module is deliberately CF0-local. It centralizes the small mechanics that
the committed CF0 harnesses repeat, without becoming a general probe framework.
"""

from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable


REPORT_VERSION = "0.1.0"
ROOT = Path(__file__).resolve().parents[1]

Mutation = Callable[[dict[str, Any], dict[str, Any], dict[str, Any], Path], dict[str, Path]]


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def run_delta_verifier(
    verifier: Path,
    paths: dict[str, Path],
    source_root: Path,
    out: Path,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(verifier),
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
        str(source_root),
        "--out",
        str(out),
    ]
    return subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)


def run_positive_baseline(
    verifier: Path,
    paths: dict[str, Path],
    source_root: Path,
    report_path: Path,
) -> dict[str, Any]:
    completed = run_delta_verifier(verifier, paths, source_root, report_path)
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
        "deltaRecordsVerification": verifier_report.get("deltaRecordsVerification", {}).get("result"),
        "errors": verifier_report.get("errors", []),
    }


def run_negative_probe(
    probe: dict[str, Any],
    good_delta: dict[str, Any],
    good_after_facts: dict[str, Any],
    good_overlay: dict[str, Any],
    base_paths: dict[str, Path],
    source_root: Path,
    verifier: Path,
    tmp: Path,
) -> dict[str, Any]:
    probe_dir = tmp / probe["id"]
    probe_dir.mkdir(parents=True)
    delta = deepcopy(good_delta)
    after_facts = deepcopy(good_after_facts)
    overlay = deepcopy(good_overlay)
    mutate: Mutation = probe["mutate"]
    overrides = mutate(delta, after_facts, overlay, probe_dir)
    delta_path = probe_dir / "delta.json"
    report_path = probe_dir / "verifier-report.json"
    write_json(delta_path, delta)

    paths = dict(base_paths)
    paths["delta"] = delta_path
    paths.update(overrides)
    completed = run_delta_verifier(verifier, paths, source_root, report_path)
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


def build_negative_probe_report(
    *,
    artifact_role: str,
    scope: str,
    baseline_scope: str,
    good_delta_path: Path,
    before_facts_path: Path,
    before_overlay_path: Path,
    after_facts_path: Path,
    after_overlay_path: Path,
    source_root: Path,
    verifier: Path,
    probes: list[dict[str, Any]],
    tmp: Path,
    temp_prefix: str,
    boundary_overrides: dict[str, Any] | None = None,
    top_level_overrides: dict[str, Any] | None = None,
    historical_inputs: bool = False,
) -> dict[str, Any]:
    good_delta = read_json(good_delta_path)
    good_after_facts = read_json(after_facts_path)
    good_overlay = read_json(after_overlay_path)
    base_paths = {
        "delta": good_delta_path,
        "before_facts": before_facts_path,
        "before_overlay": before_overlay_path,
        "after_facts": after_facts_path,
        "after_overlay": after_overlay_path,
    }
    probe_tmp = tmp / temp_prefix
    probe_tmp.mkdir(parents=True, exist_ok=True)
    baseline = run_positive_baseline(verifier, base_paths, source_root, probe_tmp / "positive-baseline-report.json")
    probe_reports = [
        run_negative_probe(probe, good_delta, good_after_facts, good_overlay, base_paths, source_root, verifier, probe_tmp)
        for probe in probes
    ]

    baseline_passed = baseline.get("rerunResult") == "pass" and baseline.get("exitCode") == 0
    all_passed = baseline_passed and all(probe["expectedFailureObserved"] is True for probe in probe_reports)
    source_digest = good_after_facts.get("source", {}).get("sha256")
    before_source_digest = read_json(before_facts_path).get("source", {}).get("sha256")
    boundaries = {
        "sourceBytesUnchanged": source_digest == before_source_digest,
        "sourceTextEqualityRequired": False,
        "hiddenGeneratedCodeSnapshotUsed": False,
        "aiAuthorityPromoted": False,
        "productBehaviorAdded": False,
        "generalNegativeProbeFrameworkClaimed": False,
    }
    if boundary_overrides:
        boundaries.update(boundary_overrides)

    report: dict[str, Any] = {
        "artifactRole": artifact_role,
        "reportVersion": REPORT_VERSION,
        "status": "pass" if all_passed else "fail",
        "result": "pass" if all_passed else "fail",
        "scope": scope,
        "baselineScope": baseline_scope,
        "baselineDelta": good_delta_path.relative_to(ROOT).as_posix(),
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
        "probeCount": len(probe_reports),
        "probes": probe_reports,
        "boundaries": boundaries,
    }
    if top_level_overrides:
        report.update(top_level_overrides)
    if historical_inputs:
        report["historicalInputs"] = {
            "delta": good_delta_path.relative_to(ROOT).as_posix(),
            "beforeCodeFacts": before_facts_path.relative_to(ROOT).as_posix(),
            "beforeOverlay": before_overlay_path.relative_to(ROOT).as_posix(),
            "afterCodeFacts": after_facts_path.relative_to(ROOT).as_posix(),
            "afterOverlay": after_overlay_path.relative_to(ROOT).as_posix(),
            "sourceRoot": source_root.relative_to(ROOT).as_posix(),
        }
    return report
