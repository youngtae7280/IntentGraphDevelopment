"""Run repeatable negative probes for B1 mapping candidate verification."""

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
GOOD_CANDIDATES = ROOT / "docs" / "examples" / "b1-typescript-rest-api" / "mapping-candidates" / "p3.2-ambiguous-mutate-todo.candidates.json"
CODE_FACTS = ROOT / "generated" / "b1-typescript-rest-api" / "code-facts.json"
VERIFIER = ROOT / "tools" / "verify_b1_mapping_candidates.py"


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def first_candidate(data: dict[str, Any]) -> dict[str, Any]:
    return data["candidates"][0]


def mutate_accepted_true(data: dict[str, Any]) -> None:
    first_candidate(data)["accepted"] = True


def mutate_accepted_by_authority(data: dict[str, Any]) -> None:
    first_candidate(data)["status"] = "accepted-by-authority"


def mutate_missing_ambiguity(data: dict[str, Any]) -> None:
    first_candidate(data).pop("ambiguity", None)


def mutate_missing_candidate_fact(data: dict[str, Any]) -> None:
    first_candidate(data)["candidateFactIds"] = ["fact.function.missing"]


def mutate_ai_generated(data: dict[str, Any]) -> None:
    first_candidate(data)["claimScope"]["aiGenerated"] = True


def mutate_authority_granted(data: dict[str, Any]) -> None:
    first_candidate(data)["claimScope"]["authorityGranted"] = True


def mutate_accepted_into_overlay(data: dict[str, Any]) -> None:
    first_candidate(data)["claimScope"]["acceptedIntoOverlay"] = True


PROBES: list[tuple[str, Callable[[dict[str, Any]], None], str]] = [
    ("accepted-true", mutate_accepted_true, "candidate.accepted must be false"),
    ("accepted-by-authority", mutate_accepted_by_authority, "accepted-by-authority is forbidden in P3.2"),
    ("missing-ambiguity", mutate_missing_ambiguity, "candidate must declare ambiguity"),
    ("missing-candidate-fact", mutate_missing_candidate_fact, "candidate fact does not exist"),
    ("ai-generated", mutate_ai_generated, "claimScope.aiGenerated must be false"),
    ("authority-granted", mutate_authority_granted, "claimScope.authorityGranted must be false"),
    ("accepted-into-overlay", mutate_accepted_into_overlay, "claimScope.acceptedIntoOverlay must be false"),
]


def run_verifier(candidates: Path, out: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(VERIFIER),
            "--candidates",
            str(candidates),
            "--code-facts",
            str(CODE_FACTS),
            "--out",
            str(out),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def run_probe(temp_dir: Path, good: dict[str, Any], probe: tuple[str, Callable[[dict[str, Any]], None], str]) -> dict[str, Any]:
    probe_id, mutate, expected = probe
    mutated = copy.deepcopy(good)
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
    good = read_json(GOOD_CANDIDATES)
    with tempfile.TemporaryDirectory(prefix="b1-candidate-probes-") as temp:
        temp_dir = Path(temp)
        baseline_report = temp_dir / "positive-baseline.report.json"
        baseline = run_verifier(GOOD_CANDIDATES, baseline_report)
        baseline_data = read_json(baseline_report) if baseline_report.exists() else {}
        probes = [run_probe(temp_dir, good, probe) for probe in PROBES]
    all_passed = baseline.returncode == 0 and all(probe["expectedFailureObserved"] for probe in probes)
    return {
        "artifactRole": "intentgraph-b1-mapping-candidate-negative-probes-report",
        "status": "intentgraph-b1-mapping-candidate-negative-probes-passed" if all_passed else "intentgraph-b1-mapping-candidate-negative-probes-failed",
        "scope": "b1-typescript-rest-api-mapping-candidate-negative-probes",
        "benchmarkId": "B1-typescript-rest-api",
        "result": "pass" if all_passed else "fail",
        "positiveBaseline": {
            "returnCode": baseline.returncode,
            "result": baseline_data.get("result"),
        },
        "probeCount": len(probes),
        "probes": probes,
        "claimScope": {
            "ambiguousCandidatesVisible": True,
            "acceptedIntoOverlay": False,
            "aiAuthorityClaimed": False,
            "automaticResolutionClaimed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run B1 mapping candidate negative probes.")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    report = run()
    write_json(args.out, report)
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
