"""Run repeatable negative probes for the B1 code fact validator."""

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
GOOD_FACTS = ROOT / "generated" / "b1-typescript-rest-api" / "code-facts.json"
SOURCE_ROOT = ROOT / "docs" / "examples" / "b1-typescript-rest-api" / "source"
VALIDATOR = ROOT / "tools" / "validate_b1_code_facts.py"


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def first_fact(data: dict[str, Any], kind: str) -> dict[str, Any]:
    for fact in data["facts"]:
        if fact.get("kind") == kind:
            return fact
    raise AssertionError(f"missing fact kind {kind}")


def first_relation(data: dict[str, Any], kind: str) -> dict[str, Any]:
    for relation in data["relations"]:
        if relation.get("kind") == kind:
            return relation
    raise AssertionError(f"missing relation kind {kind}")


def mutate_wrong_role(data: dict[str, Any]) -> None:
    data["artifactRole"] = "wrong-role"


def mutate_unknown_fact_kind(data: dict[str, Any]) -> None:
    first_fact(data, "function")["kind"] = "mystery"


def mutate_unknown_relation_kind(data: dict[str, Any]) -> None:
    first_relation(data, "calls")["kind"] = "teleports"


def mutate_missing_endpoint(data: dict[str, Any]) -> None:
    first_relation(data, "calls")["to"] = "fact.function.missing"


def mutate_missing_source_digest(data: dict[str, Any]) -> None:
    first_fact(data, "function").pop("sourceDigest", None)


def mutate_stale_source_digest(data: dict[str, Any]) -> None:
    first_fact(data, "function")["sourceDigest"] = "sha256:0000"


def mutate_source_text(data: dict[str, Any]) -> None:
    first_fact(data, "function")["sourceText"] = "export function leaked() {}"


def mutate_broad_extractor(data: dict[str, Any]) -> None:
    data["extractor"]["broadExtractor"] = True


def mutate_missing_location(data: dict[str, Any]) -> None:
    fact = first_fact(data, "function")
    fact.pop("sourceLocation", None)
    fact.pop("sourceLocationStatus", None)


def mutate_nondeterministic(data: dict[str, Any]) -> None:
    data["extractor"]["deterministic"] = False


PROBES: list[tuple[str, Callable[[dict[str, Any]], None], str]] = [
    ("wrong-role", mutate_wrong_role, "wrong artifactRole"),
    ("unknown-fact-kind", mutate_unknown_fact_kind, "unknown fact kind"),
    ("unknown-relation-kind", mutate_unknown_relation_kind, "unknown relation kind"),
    ("missing-endpoint", mutate_missing_endpoint, "missing target endpoint"),
    ("missing-source-digest", mutate_missing_source_digest, "missing required fields: sourceDigest"),
    ("stale-source-digest", mutate_stale_source_digest, "stale sourceDigest"),
    ("source-text-leak", mutate_source_text, "must not contain sourceText"),
    ("broad-extractor-true", mutate_broad_extractor, "extractor.broadExtractor must be false"),
    ("missing-location", mutate_missing_location, "missing sourceLocation or sourceLocationStatus"),
    ("nondeterministic-extractor", mutate_nondeterministic, "extractor.deterministic must be true"),
]


def run_validator(code_facts: Path, out: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--code-facts",
            str(code_facts),
            "--source-root",
            str(SOURCE_ROOT),
            "--out",
            str(out),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def run_probe(temp_dir: Path, good_data: dict[str, Any], probe: tuple[str, Callable[[dict[str, Any]], None], str]) -> dict[str, Any]:
    probe_id, mutate, expected = probe
    mutated = copy.deepcopy(good_data)
    mutate(mutated)
    input_path = temp_dir / f"{probe_id}.json"
    report_path = temp_dir / f"{probe_id}.report.json"
    write_json(input_path, mutated)
    result = run_validator(input_path, report_path)
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


def run(out: Path) -> dict[str, Any]:
    good_data = read_json(GOOD_FACTS)
    with tempfile.TemporaryDirectory(prefix="b1-code-fact-probes-") as temp:
        temp_dir = Path(temp)
        baseline_report = temp_dir / "positive-baseline.report.json"
        baseline = run_validator(GOOD_FACTS, baseline_report)
        baseline_data = read_json(baseline_report) if baseline_report.exists() else {}
        probes = [run_probe(temp_dir, good_data, probe) for probe in PROBES]
    all_passed = baseline.returncode == 0 and all(probe["expectedFailureObserved"] for probe in probes)
    return {
        "artifactRole": "intentgraph-code-fact-negative-probes-report",
        "status": "intentgraph-code-fact-negative-probes-passed" if all_passed else "intentgraph-code-fact-negative-probes-failed",
        "scope": "b1-typescript-rest-api-code-fact-negative-probes",
        "benchmarkId": "B1-typescript-rest-api",
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
            "workbenchClaimed": False,
            "aiAuthorityClaimed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run B1 code fact negative probes.")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    report = run(args.out)
    write_json(args.out, report)
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
