"""Run repeatable negative probes for B1 incremental change verification."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
GOOD_DELTA = ROOT / "docs" / "examples" / "b1-typescript-rest-api" / "deltas" / "p2.1-add-complete-todo.delta.json"
BEFORE_FACTS = ROOT / "generated" / "b1-typescript-rest-api" / "p2.1-before-code-facts.json"
AFTER_FACTS = ROOT / "generated" / "b1-typescript-rest-api" / "p2.1-after-code-facts.json"
VERIFIER = ROOT / "tools" / "verify_b1_incremental_change.py"


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def mutate_wrong_changed_file(data: dict[str, Any]) -> None:
    data["sourceChangePolicy"]["changedSourceFiles"] = ["src/model/todo.ts"]


def mutate_missing_added_fact(data: dict[str, Any]) -> None:
    data["expectedFactDelta"]["addedFactIds"] = []


def mutate_missing_changed_fact(data: dict[str, Any]) -> None:
    data["expectedFactDelta"]["changedFactIds"] = data["expectedFactDelta"]["changedFactIds"][1:]


def mutate_unexpected_removed_fact(data: dict[str, Any]) -> None:
    data["expectedFactDelta"]["removedFactIds"] = ["fact.function.addtodo"]


def mutate_missing_added_relation(data: dict[str, Any]) -> None:
    data["expectedRelationDelta"]["addedRelationIds"] = []


def mutate_intent_mapping_claim(data: dict[str, Any]) -> None:
    data["claimScope"]["intentMappingClaimed"] = True


def mutate_workbench_claim(data: dict[str, Any]) -> None:
    data["claimScope"]["workbenchClaimed"] = True


PROBES: list[tuple[str, Callable[[dict[str, Any]], None], str]] = [
    ("wrong-changed-file", mutate_wrong_changed_file, "changed source files mismatch"),
    ("missing-added-fact", mutate_missing_added_fact, "added facts mismatch"),
    ("missing-changed-fact", mutate_missing_changed_fact, "changed facts mismatch"),
    ("unexpected-removed-fact", mutate_unexpected_removed_fact, "removed facts mismatch"),
    ("missing-added-relation", mutate_missing_added_relation, "added relations mismatch"),
    ("intent-mapping-claim", mutate_intent_mapping_claim, "claimScope.intentMappingClaimed must be false"),
    ("workbench-claim", mutate_workbench_claim, "claimScope.workbenchClaimed must be false"),
]


def run_verifier(delta_path: Path, out_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(VERIFIER),
            "--delta",
            str(delta_path),
            "--before-code-facts",
            str(BEFORE_FACTS),
            "--after-code-facts",
            str(AFTER_FACTS),
            "--out",
            str(out_path),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def run_probe(temp_dir: Path, good_delta: dict[str, Any], probe: tuple[str, Callable[[dict[str, Any]], None], str]) -> dict[str, Any]:
    probe_id, mutate, expected = probe
    mutated = copy.deepcopy(good_delta)
    mutate(mutated)
    input_path = temp_dir / f"{probe_id}.json"
    report_path = temp_dir / f"{probe_id}.report.json"
    write_json(input_path, mutated)
    result = run_verifier(input_path, report_path)
    report = read_json(report_path) if report_path.exists() else {}
    errors = report.get("errors", [])
    combined = "\n".join(str(error) for error in errors) + "\n" + result.stdout + "\n" + result.stderr
    observed = result.returncode != 0 and expected in combined
    return {
        "id": probe_id,
        "expectedFailureSubstring": expected,
        "returnCode": result.returncode,
        "expectedFailureObserved": observed,
        "errors": errors,
    }


def run() -> dict[str, Any]:
    good_delta = read_json(GOOD_DELTA)
    with tempfile.TemporaryDirectory(prefix="b1-incremental-probes-") as temp:
        temp_dir = Path(temp)
        baseline_report = temp_dir / "positive-baseline.report.json"
        baseline = run_verifier(GOOD_DELTA, baseline_report)
        baseline_data = read_json(baseline_report) if baseline_report.exists() else {}
        probes = [run_probe(temp_dir, good_delta, probe) for probe in PROBES]
    all_passed = baseline.returncode == 0 and all(probe["expectedFailureObserved"] for probe in probes)
    return {
        "artifactRole": "intentgraph-code-fact-incremental-negative-probes-report",
        "status": "intentgraph-code-fact-incremental-negative-probes-passed" if all_passed else "intentgraph-code-fact-incremental-negative-probes-failed",
        "scope": "b1-typescript-rest-api-incremental-negative-probes",
        "benchmarkId": "B1-typescript-rest-api",
        "changeId": "p2.1-add-complete-todo",
        "result": "pass" if all_passed else "fail",
        "positiveBaseline": {
            "returnCode": baseline.returncode,
            "result": baseline_data.get("result"),
        },
        "probeCount": len(probes),
        "probes": probes,
        "claimScope": {
            "b1FixtureBounded": True,
            "broadExtractorClaimed": False,
            "intentMappingClaimed": False,
            "workbenchClaimed": False,
            "aiAuthorityClaimed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run B1 incremental negative probes.")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    report = run()
    write_json(args.out, report)
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
