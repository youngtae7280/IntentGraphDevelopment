"""Repeatable P9.2 probes for B1 logical source-root identity input."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR = ROOT / "tools" / "extract_b1_code_facts.py"
VALIDATOR = ROOT / "tools" / "validate_b1_code_facts.py"
SOURCE = ROOT / "docs" / "examples" / "b1-typescript-rest-api" / "source"
LOGICAL_ID = "intentgraph://profiles/b1-typescript-rest-api-sample/source"
EXPECTED_ERROR = "source root id must be an intentgraph:// logical identifier"


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def extract(logical_id: str, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(EXTRACTOR),
            "--source-root",
            str(SOURCE),
            "--source-root-id",
            logical_id,
            "--out",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def validate(code_facts: Path, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--code-facts",
            str(code_facts),
            "--source-root",
            str(SOURCE),
            "--out",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run P9.2 logical source identity negative probes.")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    probes = [
        ("physical-path-logical-id", r"C:\outside", EXPECTED_ERROR),
        ("path-traversal-logical-id", "intentgraph://profiles/../outside", EXPECTED_ERROR),
        ("backslash-logical-id", r"intentgraph://profiles\b1", EXPECTED_ERROR),
    ]
    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="intentgraph-p9.2-") as temp:
        root = Path(temp)
        positive = extract(LOGICAL_ID, root / "positive.json")
        if positive.returncode != 0:
            raise SystemExit(f"positive logical extraction failed: {positive.stdout}{positive.stderr}")
        facts = json.loads((root / "positive.json").read_text(encoding="utf-8"))
        if facts.get("sourceRoot") != LOGICAL_ID or facts.get("sourceRootKind") != "logical-id":
            raise SystemExit("positive logical extraction did not retain the declared logical source identity")
        positive_validation = validate(root / "positive.json", root / "positive-validation.json")
        if positive_validation.returncode != 0:
            raise SystemExit("positive logical validation failed")
        for identifier, logical_id, expected_error in probes:
            completed = extract(logical_id, root / f"{identifier}.json")
            observed = completed.returncode != 0 and expected_error in completed.stdout
            results.append(
                {
                    "id": identifier,
                    "kind": "extractor-input",
                    "logicalId": logical_id,
                    "expectedError": expected_error,
                    "exitCode": completed.returncode,
                    "stdout": completed.stdout.strip(),
                    "expectedFailureObserved": observed,
                }
            )
        validation_probes = [
            (
                "wrong-logical-source-root-kind",
                lambda value: value.__setitem__("sourceRootKind", "physical-path"),
                "sourceRootKind must be logical-id when declared",
            ),
            (
                "traversal-logical-source-root",
                lambda value: value.__setitem__("sourceRoot", "intentgraph://profiles/../outside"),
                "logical sourceRoot must be an intentgraph:// identifier without traversal",
            ),
        ]
        for identifier, mutate, expected_error in validation_probes:
            mutated = dict(facts)
            mutate(mutated)
            code_facts_path = root / f"{identifier}.json"
            report_path = root / f"{identifier}-report.json"
            write_json(code_facts_path, mutated)
            completed = validate(code_facts_path, report_path)
            validation_report = json.loads(report_path.read_text(encoding="utf-8"))
            observed = completed.returncode != 0 and expected_error in validation_report.get("errors", [])
            results.append(
                {
                    "id": identifier,
                    "kind": "validator-input",
                    "expectedError": expected_error,
                    "exitCode": completed.returncode,
                    "errors": validation_report.get("errors", []),
                    "expectedFailureObserved": observed,
                }
            )
    report = {
        "artifactRole": "intentgraph-b1-logical-source-identity-negative-probes-report",
        "status": "intentgraph-b1-logical-source-identity-negative-probes-passed"
        if all(item["expectedFailureObserved"] for item in results)
        else "intentgraph-b1-logical-source-identity-negative-probes-failed",
        "result": "pass" if all(item["expectedFailureObserved"] for item in results) else "fail",
        "logicalSourceRoot": LOGICAL_ID,
        "positiveLogicalExtractionPassed": True,
        "positiveLogicalValidationPassed": True,
        "probeCount": len(results),
        "probes": results,
        "authority": {
            "sourceMutation": False,
            "networkRequired": False,
            "automaticCodeApplication": False,
        },
    }
    write_json(args.out, report)
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
