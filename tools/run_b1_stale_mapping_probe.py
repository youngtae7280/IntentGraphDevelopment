"""Run a focused stale mapping probe for B1 Intent mapping."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GOOD_FACTS = ROOT / "generated" / "b1-typescript-rest-api" / "code-facts.json"
OVERLAY = ROOT / "docs" / "examples" / "b1-typescript-rest-api" / "intentgraph.overlay.json"
VERIFIER = ROOT / "tools" / "verify_b1_intent_mapping.py"


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def remove_fact(data: dict[str, Any], fact_id: str) -> dict[str, Any]:
    mutated = json.loads(json.dumps(data))
    mutated["status"] = "intentgraph-code-facts-stale-probe"
    mutated["scope"] = "b1-typescript-rest-api-stale-mapping-probe"
    mutated["staleProbe"] = {
        "removedFactId": fact_id,
        "purpose": "prove Intent mapping fails when a mapped fact disappears",
    }
    mutated["facts"] = [fact for fact in mutated["facts"] if fact.get("id") != fact_id]
    return mutated


def run_verifier(code_facts: Path, out: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(VERIFIER),
            "--overlay",
            str(OVERLAY),
            "--code-facts",
            str(code_facts),
            "--out",
            str(out),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def run(stale_facts_path: Path, verifier_report_path: Path) -> dict[str, Any]:
    removed_fact_id = "fact.function.addtodo"
    good_facts = read_json(GOOD_FACTS)
    stale_facts = remove_fact(good_facts, removed_fact_id)
    write_json(stale_facts_path, stale_facts)
    result = run_verifier(stale_facts_path, verifier_report_path)
    verifier_report = read_json(verifier_report_path) if verifier_report_path.exists() else {}
    errors = verifier_report.get("errors", [])
    expected_substrings = [
        "codeRef.create-todo.addTodo references missing fact fact.function.addtodo",
        "codeFactRef.create-todo.addTodo references missing fact fact.function.addtodo",
        "codeRef.route.post-todos.handler references missing fact fact.function.addtodo",
        "codeFactRef.route.post-todos.handler references missing fact fact.function.addtodo",
    ]
    combined = "\n".join(str(error) for error in errors)
    expected_failures = [
        {
            "expectedFailureSubstring": expected,
            "observed": expected in combined,
        }
        for expected in expected_substrings
    ]
    passed = result.returncode != 0 and all(item["observed"] for item in expected_failures)
    return {
        "artifactRole": "intentgraph-b1-stale-mapping-probe-report",
        "status": "intentgraph-b1-stale-mapping-probe-passed" if passed else "intentgraph-b1-stale-mapping-probe-failed",
        "scope": "b1-typescript-rest-api-stale-mapping-probe",
        "benchmarkId": "B1-typescript-rest-api",
        "result": "pass" if passed else "fail",
        "removedFactId": removed_fact_id,
        "verifierReturnCode": result.returncode,
        "staleFactsPath": stale_facts_path.as_posix(),
        "verifierReportPath": verifier_report_path.as_posix(),
        "expectedFailures": expected_failures,
        "claimScope": {
            "sourceEdited": False,
            "staleFactsOnly": True,
            "automaticRepairClaimed": False,
            "aiMappingClaimed": False,
            "workbenchClaimed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run B1 stale mapping probe.")
    parser.add_argument("--stale-code-facts", required=True, type=Path)
    parser.add_argument("--stale-verifier-report", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    report = run(args.stale_code_facts, args.stale_verifier_report)
    write_json(args.out, report)
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
