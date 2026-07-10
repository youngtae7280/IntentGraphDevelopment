"""Run repeatable negative probes for B1 change proposal validation."""

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
GOOD_PROPOSAL = ROOT / "docs" / "examples" / "b1-typescript-rest-api" / "proposals" / "p4.0-complete-todo-route.proposal.json"
CODE_FACTS = ROOT / "generated" / "b1-typescript-rest-api" / "code-facts.json"
OVERLAY = ROOT / "docs" / "examples" / "b1-typescript-rest-api" / "intentgraph.overlay.json"
VALIDATOR = ROOT / "tools" / "validate_b1_change_proposal.py"


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def mutate_stale_code_facts_digest(data: dict[str, Any]) -> None:
    data["baseline"]["codeFactsDigest"] = "sha256:0000"


def mutate_stale_source_digest(data: dict[str, Any]) -> None:
    data["baseline"]["sourceDigests"]["src/routes/todos.ts"] = "sha256:0000"


def mutate_overbroad_scope(data: dict[str, Any]) -> None:
    data["deltaC"]["plannedSourceChanges"][0]["targetFile"] = "src/model/todo.ts"


def mutate_missing_mapping_update(data: dict[str, Any]) -> None:
    data["deltaM"]["mappingUpdates"] = []


def mutate_missing_tests(data: dict[str, Any]) -> None:
    data["requiredTests"] = []


def mutate_missing_evidence(data: dict[str, Any]) -> None:
    data["requiredEvidence"] = []


def mutate_missing_authority(data: dict[str, Any]) -> None:
    data["requiredAuthority"] = []


def mutate_self_authorized(data: dict[str, Any]) -> None:
    data["requiredAuthority"][0]["selfAuthorized"] = True


def mutate_ai_authority(data: dict[str, Any]) -> None:
    data["claimScope"]["aiAuthorityGranted"] = True


def mutate_source_mutated(data: dict[str, Any]) -> None:
    data["claimScope"]["sourceMutated"] = True


def mutate_patch_applied(data: dict[str, Any]) -> None:
    data["claimScope"]["patchApplied"] = True


def mutate_source_text(data: dict[str, Any]) -> None:
    data["deltaC"]["plannedSourceChanges"][0]["sourceText"] = "import { completeTodo } from '../service/todoService';"


PROBES: list[tuple[str, Callable[[dict[str, Any]], None], str]] = [
    ("stale-code-facts-digest", mutate_stale_code_facts_digest, "baseline codeFactsDigest does not match supplied code facts"),
    ("stale-source-digest", mutate_stale_source_digest, "baseline sourceDigests do not match supplied code facts"),
    ("overbroad-scope", mutate_overbroad_scope, "targets file outside impact scope"),
    ("missing-mapping-update", mutate_missing_mapping_update, "deltaM.mappingUpdates must be non-empty"),
    ("missing-tests", mutate_missing_tests, "requiredTests must be non-empty"),
    ("missing-evidence", mutate_missing_evidence, "requiredEvidence must be non-empty"),
    ("missing-authority", mutate_missing_authority, "requiredAuthority must be non-empty"),
    ("self-authorized", mutate_self_authorized, "must not be self-authorized"),
    ("ai-authority", mutate_ai_authority, "claimScope.aiAuthorityGranted must be false"),
    ("source-mutated", mutate_source_mutated, "claimScope.sourceMutated must be false"),
    ("patch-applied", mutate_patch_applied, "claimScope.patchApplied must be false"),
    ("source-text-contained", mutate_source_text, "must not contain sourceText"),
]


def run_validator(proposal: Path, out: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--proposal",
            str(proposal),
            "--code-facts",
            str(CODE_FACTS),
            "--overlay",
            str(OVERLAY),
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
    input_path = temp_dir / f"{probe_id}.proposal.json"
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


def run() -> dict[str, Any]:
    good = read_json(GOOD_PROPOSAL)
    with tempfile.TemporaryDirectory(prefix="b1-change-proposal-probes-") as temp:
        temp_dir = Path(temp)
        baseline_report = temp_dir / "positive-baseline.report.json"
        baseline = run_validator(GOOD_PROPOSAL, baseline_report)
        baseline_data = read_json(baseline_report) if baseline_report.exists() else {}
        probes = [run_probe(temp_dir, good, probe) for probe in PROBES]
    all_passed = baseline.returncode == 0 and all(probe["expectedFailureObserved"] for probe in probes)
    return {
        "artifactRole": "intentgraph-b1-change-proposal-negative-probes-report",
        "status": "intentgraph-b1-change-proposal-negative-probes-passed" if all_passed else "intentgraph-b1-change-proposal-negative-probes-failed",
        "scope": "b1-typescript-rest-api-change-proposal-negative-probes",
        "benchmarkId": "B1-typescript-rest-api",
        "result": "pass" if all_passed else "fail",
        "positiveBaseline": {
            "returnCode": baseline.returncode,
            "result": baseline_data.get("result"),
        },
        "probeCount": len(probes),
        "probes": probes,
        "claimScope": {
            "proposalOnly": True,
            "sourceMutated": False,
            "patchApplied": False,
            "aiAuthorityGranted": False,
            "selfAuthorized": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run B1 change proposal negative probes.")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    report = run()
    write_json(args.out, report)
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
