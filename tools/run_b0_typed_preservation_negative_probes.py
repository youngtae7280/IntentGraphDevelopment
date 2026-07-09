"""Run repeatable negative probes for B0 typed preservation metadata."""

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
GOOD_METADATA = ROOT / "generated/b0-python-cli-calculator/calc.intentgraph.json"
SOURCE = ROOT / "generated/b0-python-cli-calculator/calc.py"
RETROFIT = ROOT / "tools/retrofit_reconstruct.py"

Mutation = Callable[[dict[str, Any], Path], None]


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def remove_typed_preservation(metadata: dict[str, Any], tmp: Path) -> None:
    metadata.pop("typedPreservation", None)


def set_snapshot_still_present_false(metadata: dict[str, Any], tmp: Path) -> None:
    metadata["typedPreservation"]["snapshotStillPresent"] = False


def remove_evidence_domain(metadata: dict[str, Any], tmp: Path) -> None:
    metadata["typedPreservation"]["domains"].pop("evidence", None)


def corrupt_evidence_digest(metadata: dict[str, Any], tmp: Path) -> None:
    metadata["typedPreservation"]["domains"]["evidence"]["digest"] = "sha256:0000"


def remove_evidence_record(metadata: dict[str, Any], tmp: Path) -> None:
    metadata["typedPreservation"]["domains"]["evidence"]["records"].pop()


def corrupt_evidence_count(metadata: dict[str, Any], tmp: Path) -> None:
    metadata["typedPreservation"]["domains"]["evidence"]["count"] = 999


def unsort_evidence_records(metadata: dict[str, Any], tmp: Path) -> None:
    metadata["typedPreservation"]["domains"]["evidence"]["records"].reverse()


def remove_authority_record(metadata: dict[str, Any], tmp: Path) -> None:
    metadata["typedPreservation"]["domains"]["authority"]["records"].pop()


def remove_history_record(metadata: dict[str, Any], tmp: Path) -> None:
    metadata["typedPreservation"]["domains"]["history"]["records"].pop()


def remove_intent_unit_record(metadata: dict[str, Any], tmp: Path) -> None:
    metadata["typedPreservation"]["domains"]["intentUnits"]["records"].pop()


def remove_unit_edge_record(metadata: dict[str, Any], tmp: Path) -> None:
    metadata["typedPreservation"]["domains"]["unitEdges"]["records"].pop()


PROBES: list[dict[str, Any]] = [
    {
        "id": "missing-typed-preservation",
        "mutation": "Remove top-level typedPreservation.",
        "expectedErrorSubstring": "Metadata missing required field: typedPreservation",
        "mutate": remove_typed_preservation,
    },
    {
        "id": "snapshot-still-present-false",
        "mutation": "Set typedPreservation.snapshotStillPresent to false.",
        "expectedErrorSubstring": "P1.5 typedPreservation must acknowledge snapshotStillPresent true",
        "mutate": set_snapshot_still_present_false,
    },
    {
        "id": "missing-domain-evidence",
        "mutation": "Remove typedPreservation.domains.evidence.",
        "expectedErrorSubstring": "typedPreservation missing domain: evidence",
        "mutate": remove_evidence_domain,
    },
    {
        "id": "stale-evidence-digest",
        "mutation": "Set typedPreservation.domains.evidence.digest to sha256:0000.",
        "expectedErrorSubstring": "typedPreservation evidence digest does not match records",
        "mutate": corrupt_evidence_digest,
    },
    {
        "id": "missing-evidence-record",
        "mutation": "Remove one typed evidence record without updating digest or count.",
        "expectedErrorSubstring": "typedPreservation evidence digest does not match records",
        "mutate": remove_evidence_record,
    },
    {
        "id": "wrong-evidence-count",
        "mutation": "Set typedPreservation.domains.evidence.count to 999.",
        "expectedErrorSubstring": "typedPreservation evidence count mismatch",
        "mutate": corrupt_evidence_count,
    },
    {
        "id": "unsorted-evidence-records",
        "mutation": "Reverse typed evidence record order.",
        "expectedErrorSubstring": "typedPreservation evidence records must be sorted by id",
        "mutate": unsort_evidence_records,
    },
    {
        "id": "missing-authority-record",
        "mutation": "Remove one typed authority record without updating digest or count.",
        "expectedErrorSubstring": "typedPreservation authority digest does not match records",
        "mutate": remove_authority_record,
    },
    {
        "id": "missing-history-record",
        "mutation": "Remove one typed history record without updating digest or count.",
        "expectedErrorSubstring": "typedPreservation history digest does not match records",
        "mutate": remove_history_record,
    },
    {
        "id": "missing-intent-unit-record",
        "mutation": "Remove one typed Intent Unit record without updating digest or count.",
        "expectedErrorSubstring": "typedPreservation intentUnits digest does not match records",
        "mutate": remove_intent_unit_record,
    },
    {
        "id": "missing-unit-edge-record",
        "mutation": "Remove one typed unit edge record without updating digest or count.",
        "expectedErrorSubstring": "typedPreservation unitEdges digest does not match records",
        "mutate": remove_unit_edge_record,
    },
]


def run_retrofit(metadata_path: Path, out: Path) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(RETROFIT),
        "--source",
        str(SOURCE),
        "--metadata",
        str(metadata_path),
        "--out",
        str(out),
    ]
    return subprocess.run(command, cwd=ROOT, text=True, capture_output=True)


def run_probe(probe: dict[str, Any], good_metadata: dict[str, Any], tmp: Path) -> dict[str, Any]:
    probe_dir = tmp / probe["id"]
    probe_dir.mkdir(parents=True)
    metadata = deepcopy(good_metadata)
    probe["mutate"](metadata, probe_dir)
    metadata_path = probe_dir / "calc.intentgraph.json"
    out_dir = probe_dir / "out"
    write_json(metadata_path, metadata)

    completed = run_retrofit(metadata_path, out_dir)
    expected = probe["expectedErrorSubstring"]
    combined = (completed.stdout + completed.stderr).strip()
    expected_failure_observed = completed.returncode != 0 and expected in combined
    return {
        "id": probe["id"],
        "mutation": probe["mutation"],
        "expectedErrorSubstring": expected,
        "actualExitCode": completed.returncode,
        "actualMessage": combined,
        "expectedFailureObserved": expected_failure_observed,
    }


def build_report() -> dict[str, Any]:
    good_metadata = read_json(GOOD_METADATA)
    with tempfile.TemporaryDirectory(prefix="b0-typed-preservation-negative-probes-") as tmp_name:
        tmp = Path(tmp_name)
        probes = [run_probe(probe, good_metadata, tmp) for probe in PROBES]

    all_passed = all(probe["expectedFailureObserved"] is True for probe in probes)
    typed = good_metadata.get("typedPreservation", {})
    return {
        "reportVersion": REPORT_VERSION,
        "mode": "b0-typed-preservation-negative-probes",
        "result": "pass" if all_passed else "fail",
        "probeCount": len(probes),
        "probes": probes,
        "positiveBaseline": {
            "metadata": "generated/b0-python-cli-calculator/calc.intentgraph.json",
            "typedPreservationVersion": typed.get("version"),
            "snapshotStillPresent": typed.get("snapshotStillPresent"),
            "domains": sorted(typed.get("domains", {})),
        },
        "boundaries": {
            "hiddenStateSourceGraphSnapshotRemoved": False,
            "codeOnlyReconstructionClaimed": False,
            "typedDomainsExpanded": False,
            "dependencyAdded": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run B0 typed preservation negative probes.")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    report = build_report()
    write_json(args.out, report)
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
