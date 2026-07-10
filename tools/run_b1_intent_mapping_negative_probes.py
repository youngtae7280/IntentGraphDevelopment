"""Run repeatable negative probes for B1 Intent mapping verification."""

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
GOOD_OVERLAY = ROOT / "docs" / "examples" / "b1-typescript-rest-api" / "intentgraph.overlay.json"
CODE_FACTS = ROOT / "generated" / "b1-typescript-rest-api" / "code-facts.json"
VERIFIER = ROOT / "tools" / "verify_b1_intent_mapping.py"


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def first_unit(data: dict[str, Any]) -> dict[str, Any]:
    return data["intentUnits"][0]


def first_obligation(data: dict[str, Any]) -> dict[str, Any]:
    return first_unit(data)["mappingObligations"][0]


def mutate_missing_code_fact(data: dict[str, Any]) -> None:
    first_unit(data)["codeFactRefs"][0]["factId"] = "fact.function.missing"


def mutate_wrong_expected_kind(data: dict[str, Any]) -> None:
    first_unit(data)["codeFactRefs"][0]["expectedFactKind"] = "route"


def mutate_missing_obligation_ref(data: dict[str, Any]) -> None:
    first_obligation(data)["codeFactRefIds"].append("codeFactRef.missing")


def mutate_missing_evidence(data: dict[str, Any]) -> None:
    first_obligation(data)["evidenceIds"] = ["evidence.missing"]


def mutate_missing_authority(data: dict[str, Any]) -> None:
    first_obligation(data)["authorityIds"] = ["authority.missing"]


def mutate_source_text_equality(data: dict[str, Any]) -> None:
    first_obligation(data)["sourceTextEqualityRequired"] = True


def mutate_code_text_contained(data: dict[str, Any]) -> None:
    first_unit(data)["codeTextContained"] = True
    first_unit(data)["codeText"] = "export function leaked() {}"


def mutate_ambiguous_resolved(data: dict[str, Any]) -> None:
    first_unit(data)["ambiguity"] = {"reason": "two candidate handlers"}


def mutate_ai_authority(data: dict[str, Any]) -> None:
    data["authority"][0]["aiAuthority"] = True


def mutate_automatic_mapping_claim(data: dict[str, Any]) -> None:
    data["claimScope"]["automaticMappingClaimed"] = True


PROBES: list[tuple[str, Callable[[dict[str, Any]], None], str]] = [
    ("missing-code-fact", mutate_missing_code_fact, "references missing fact"),
    ("wrong-expected-kind", mutate_wrong_expected_kind, "expected route got function"),
    ("missing-obligation-ref", mutate_missing_obligation_ref, "missing codeFactRef"),
    ("missing-evidence", mutate_missing_evidence, "missing evidence"),
    ("missing-authority", mutate_missing_authority, "missing authority"),
    ("source-text-equality", mutate_source_text_equality, "must not require source text equality"),
    ("code-text-contained", mutate_code_text_contained, "codeTextContained must be false"),
    ("ambiguous-resolved", mutate_ambiguous_resolved, "resolved unit must not declare ambiguity"),
    ("ai-authority", mutate_ai_authority, "must not grant AI authority"),
    ("automatic-mapping-claim", mutate_automatic_mapping_claim, "claimScope.automaticMappingClaimed must be false"),
]


def run_verifier(overlay: Path, out: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(VERIFIER),
            "--overlay",
            str(overlay),
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


def run_probe(temp_dir: Path, good_overlay: dict[str, Any], probe: tuple[str, Callable[[dict[str, Any]], None], str]) -> dict[str, Any]:
    probe_id, mutate, expected = probe
    mutated = copy.deepcopy(good_overlay)
    mutate(mutated)
    overlay_path = temp_dir / f"{probe_id}.overlay.json"
    report_path = temp_dir / f"{probe_id}.report.json"
    write_json(overlay_path, mutated)
    result = run_verifier(overlay_path, report_path)
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
    good_overlay = read_json(GOOD_OVERLAY)
    with tempfile.TemporaryDirectory(prefix="b1-mapping-probes-") as temp:
        temp_dir = Path(temp)
        baseline_report = temp_dir / "positive-baseline.report.json"
        baseline = run_verifier(GOOD_OVERLAY, baseline_report)
        baseline_data = read_json(baseline_report) if baseline_report.exists() else {}
        probes = [run_probe(temp_dir, good_overlay, probe) for probe in PROBES]
    all_passed = baseline.returncode == 0 and all(probe["expectedFailureObserved"] for probe in probes)
    return {
        "artifactRole": "intentgraph-b1-intent-mapping-negative-probes-report",
        "status": "intentgraph-b1-intent-mapping-negative-probes-passed" if all_passed else "intentgraph-b1-intent-mapping-negative-probes-failed",
        "scope": "b1-typescript-rest-api-intent-mapping-negative-probes",
        "benchmarkId": "B1-typescript-rest-api",
        "result": "pass" if all_passed else "fail",
        "positiveBaseline": {
            "returnCode": baseline.returncode,
            "result": baseline_data.get("result"),
        },
        "probeCount": len(probes),
        "probes": probes,
        "claimScope": {
            "staticB1OverlayOnly": True,
            "codeEdited": False,
            "automaticMappingClaimed": False,
            "aiAuthorityClaimed": False,
            "workbenchClaimed": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run B1 intent mapping negative probes.")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    report = run()
    write_json(args.out, report)
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
