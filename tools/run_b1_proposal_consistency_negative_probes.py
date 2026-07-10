"""Run repeatable negative probes for B1 proposal consistency verification."""

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
GOOD_VALIDATION = ROOT / "generated" / "b1-typescript-rest-api" / "p4.0-change-proposal-validation-report.json"
CODE_FACTS = ROOT / "generated" / "b1-typescript-rest-api" / "code-facts.json"
OVERLAY = ROOT / "docs" / "examples" / "b1-typescript-rest-api" / "intentgraph.overlay.json"
VERIFIER = ROOT / "tools" / "verify_b1_proposal_consistency.py"


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def mutate_validation_failed(proposal: dict[str, Any], validation: dict[str, Any]) -> None:
    validation["result"] = "fail"


def mutate_validation_proposal_mismatch(proposal: dict[str, Any], validation: dict[str, Any]) -> None:
    validation["proposalId"] = "proposal.mismatch"


def mutate_stale_code_digest(proposal: dict[str, Any], validation: dict[str, Any]) -> None:
    proposal["baseline"]["codeFactsDigest"] = "sha256:0000"


def mutate_missing_existing_unit(proposal: dict[str, Any], validation: dict[str, Any]) -> None:
    proposal["impactScope"]["existingIntentUnitIds"] = ["unit.behavior.missing"]


def mutate_missing_mapping_update(proposal: dict[str, Any], validation: dict[str, Any]) -> None:
    proposal["deltaM"]["mappingUpdates"] = []


def mutate_missing_test(proposal: dict[str, Any], validation: dict[str, Any]) -> None:
    proposal["requiredTests"] = []


def mutate_missing_evidence(proposal: dict[str, Any], validation: dict[str, Any]) -> None:
    proposal["requiredEvidence"] = []


def mutate_missing_authority(proposal: dict[str, Any], validation: dict[str, Any]) -> None:
    proposal["requiredAuthority"] = []


def mutate_source_mutated(proposal: dict[str, Any], validation: dict[str, Any]) -> None:
    proposal["claimScope"]["sourceMutated"] = True


def mutate_patch_applied(proposal: dict[str, Any], validation: dict[str, Any]) -> None:
    proposal["claimScope"]["patchApplied"] = True


def mutate_ai_judgment(proposal: dict[str, Any], validation: dict[str, Any]) -> None:
    proposal["claimScope"]["aiAuthorityGranted"] = True


PROBES: list[tuple[str, Callable[[dict[str, Any], dict[str, Any]], None], str]] = [
    ("validation-failed", mutate_validation_failed, "proposal validation report must pass"),
    ("validation-proposal-mismatch", mutate_validation_proposal_mismatch, "proposal validation report proposalId must match proposal"),
    ("stale-code-digest", mutate_stale_code_digest, "proposal baseline codeFactsDigest is stale"),
    ("missing-existing-unit", mutate_missing_existing_unit, "impact scope references missing Intent Unit"),
    ("missing-mapping-update", mutate_missing_mapping_update, "proposal must declare mapping updates"),
    ("missing-test", mutate_missing_test, "proposal consistency requires tests"),
    ("missing-evidence", mutate_missing_evidence, "proposal consistency requires evidence"),
    ("missing-authority", mutate_missing_authority, "proposal consistency requires authority"),
    ("source-mutated", mutate_source_mutated, "claimScope.sourceMutated must be false"),
    ("patch-applied", mutate_patch_applied, "claimScope.patchApplied must be false"),
    ("ai-authority", mutate_ai_judgment, "claimScope.aiAuthorityGranted must be false"),
]


def run_verifier(proposal: Path, validation: Path, out: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(VERIFIER),
            "--proposal",
            str(proposal),
            "--proposal-validation",
            str(validation),
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


def run_probe(
    temp_dir: Path,
    good_proposal: dict[str, Any],
    good_validation: dict[str, Any],
    probe: tuple[str, Callable[[dict[str, Any], dict[str, Any]], None], str],
) -> dict[str, Any]:
    probe_id, mutate, expected = probe
    proposal = copy.deepcopy(good_proposal)
    validation = copy.deepcopy(good_validation)
    mutate(proposal, validation)
    proposal_path = temp_dir / f"{probe_id}.proposal.json"
    validation_path = temp_dir / f"{probe_id}.validation.json"
    report_path = temp_dir / f"{probe_id}.report.json"
    write_json(proposal_path, proposal)
    write_json(validation_path, validation)
    result = run_verifier(proposal_path, validation_path, report_path)
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
    good_proposal = read_json(GOOD_PROPOSAL)
    good_validation = read_json(GOOD_VALIDATION)
    with tempfile.TemporaryDirectory(prefix="b1-proposal-consistency-probes-") as temp:
        temp_dir = Path(temp)
        baseline_report = temp_dir / "positive-baseline.report.json"
        baseline = run_verifier(GOOD_PROPOSAL, GOOD_VALIDATION, baseline_report)
        baseline_data = read_json(baseline_report) if baseline_report.exists() else {}
        probes = [run_probe(temp_dir, good_proposal, good_validation, probe) for probe in PROBES]
    all_passed = baseline.returncode == 0 and all(probe["expectedFailureObserved"] for probe in probes)
    return {
        "artifactRole": "intentgraph-b1-proposal-consistency-negative-probes-report",
        "status": "intentgraph-b1-proposal-consistency-negative-probes-passed" if all_passed else "intentgraph-b1-proposal-consistency-negative-probes-failed",
        "scope": "b1-typescript-rest-api-proposal-consistency-negative-probes",
        "benchmarkId": "B1-typescript-rest-api",
        "result": "pass" if all_passed else "fail",
        "positiveBaseline": {
            "returnCode": baseline.returncode,
            "result": baseline_data.get("result"),
        },
        "probeCount": len(probes),
        "probes": probes,
        "claimScope": {
            "deterministicVerifier": True,
            "proposalOnly": True,
            "sourceMutated": False,
            "patchApplied": False,
            "aiJudgmentUsed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run B1 proposal consistency negative probes.")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    report = run()
    write_json(args.out, report)
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
