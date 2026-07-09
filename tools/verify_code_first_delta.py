"""Verify a tiny CF0 code-first maintenance delta."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from verify_code_first_overlay import verify as verify_overlay


REPORT_VERSION = "0.1.0"


class DeltaVerifyError(Exception):
    """Raised when the CF0 maintenance delta cannot be verified."""


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise DeltaVerifyError(f"{path} must contain a JSON object")
    return data


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest_json(data: Any) -> str:
    return f"sha256:{hashlib.sha256(canonical_json(data).encode('utf-8')).hexdigest()}"


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def fact_ids(code_facts: dict[str, Any]) -> set[str]:
    return {
        fact["id"]
        for fact in code_facts.get("facts", [])
        if isinstance(fact, dict) and isinstance(fact.get("id"), str)
    }


def count_mapping_obligations(overlay: dict[str, Any]) -> int:
    return sum(
        len(unit.get("mappingObligations", []))
        for unit in overlay.get("intentUnits", [])
        if isinstance(unit, dict)
    )


def overlay_unit_ids(overlay: dict[str, Any]) -> set[str]:
    return {
        unit["id"]
        for unit in overlay.get("intentUnits", [])
        if isinstance(unit, dict) and isinstance(unit.get("id"), str)
    }


def verify_delta(
    delta_path: Path,
    before_code_facts_path: Path,
    after_code_facts_path: Path,
    overlay_path: Path,
    source_root: Path,
) -> dict[str, Any]:
    delta = read_json(delta_path)
    before_facts = read_json(before_code_facts_path)
    after_facts = read_json(after_code_facts_path)
    overlay = read_json(overlay_path)
    overlay_report = verify_overlay(overlay_path, after_code_facts_path, source_root)

    before_ids = fact_ids(before_facts)
    after_ids = fact_ids(after_facts)
    added_fact_ids = sorted(after_ids - before_ids)
    removed_fact_ids = sorted(before_ids - after_ids)
    expected_added = set(delta.get("expectedAfter", {}).get("addedCodeFactIds", []))
    added_behaviors = set(delta.get("expectedAfter", {}).get("addedBehaviorUnits", []))
    preserved_behaviors = set(delta.get("expectedAfter", {}).get("preservedBehaviorUnits", []))
    units = overlay_unit_ids(overlay)

    checks: list[str] = []
    errors: list[str] = []
    if delta.get("mode") != "code-first-maintenance-delta":
        errors.append("delta mode must be code-first-maintenance-delta")
    if delta.get("sourceTextEqualityRequired") is not False:
        errors.append("delta must not require source text equality")
    if delta.get("hiddenGeneratedCodeSnapshotUsed") is not False:
        errors.append("delta must not use hidden generated-code snapshots")
    if delta.get("before", {}).get("codeFactsDigest") != digest_json(before_facts):
        errors.append("before code facts digest does not match delta")
    if delta.get("before", {}).get("codeFactCount") != len(before_ids):
        errors.append("before code fact count does not match delta")
    if not expected_added.issubset(set(added_fact_ids)):
        errors.append(f"missing expected added facts: {sorted(expected_added - set(added_fact_ids))}")
    if not added_behaviors.issubset(units):
        errors.append(f"missing added behavior units: {sorted(added_behaviors - units)}")
    if not preserved_behaviors.issubset(units):
        errors.append(f"missing preserved behavior units: {sorted(preserved_behaviors - units)}")
    if overlay_report["result"] != "pass":
        errors.append("after overlay verification failed")
    if not overlay.get("evidence") or not overlay.get("authority") or not overlay.get("history"):
        errors.append("overlay must contain evidence, authority, and history records")

    checks.append("before code facts captured independently")
    checks.append("after overlay verification executed")
    checks.append("source text equality not required")
    checks.append("hidden generated-code snapshot not used")

    return {
        "reportVersion": REPORT_VERSION,
        "mode": "code-first-maintenance-delta",
        "result": "pass" if not errors else "fail",
        "sourceRole": after_facts.get("source", {}).get("role"),
        "sourceTextEqualityRequired": False,
        "hiddenGeneratedCodeSnapshotUsed": False,
        "inputs": {
            "delta": delta_path.as_posix(),
            "beforeCodeFacts": before_code_facts_path.as_posix(),
            "afterCodeFacts": after_code_facts_path.as_posix(),
            "overlay": overlay_path.as_posix(),
            "sourceRoot": source_root.as_posix(),
        },
        "before": {
            "sourceDigest": before_facts.get("source", {}).get("sha256"),
            "codeFactsDigest": digest_json(before_facts),
            "codeFactCount": len(before_ids),
            "overlayDigest": delta.get("before", {}).get("overlayDigest"),
            "mappingObligationCount": delta.get("before", {}).get("mappingObligationCount"),
        },
        "after": {
            "sourceDigest": after_facts.get("source", {}).get("sha256"),
            "codeFactsDigest": digest_json(after_facts),
            "codeFactCount": len(after_ids),
            "overlayDigest": digest_json(overlay),
            "mappingObligationCount": count_mapping_obligations(overlay),
        },
        "delta": {
            "deltaId": delta.get("deltaId"),
            "addedBehaviorUnits": sorted(added_behaviors),
            "addedBehaviorCount": len(added_behaviors),
            "preservedBehaviorUnits": sorted(preserved_behaviors),
            "addedCodeFactIds": added_fact_ids,
            "removedCodeFactIds": removed_fact_ids,
            "expectedAddedCodeFactIds": sorted(expected_added),
        },
        "mappingVerification": overlay_report["mappingVerification"],
        "behaviorVerification": overlay_report["behaviorVerification"],
        "semanticBoundaries": overlay_report["semanticBoundaries"],
        "checks": checks,
        "errors": errors,
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the CF0 P1.3 maintenance delta.")
    parser.add_argument("--delta", required=True, type=Path)
    parser.add_argument("--before-code-facts", required=True, type=Path)
    parser.add_argument("--after-code-facts", required=True, type=Path)
    parser.add_argument("--overlay", required=True, type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = verify_delta(
            args.delta,
            args.before_code_facts,
            args.after_code_facts,
            args.overlay,
            args.source_root,
        )
        write_json(args.out, report)
    except (OSError, json.JSONDecodeError, DeltaVerifyError) as error:
        print(f"verify code-first delta failed: {error}")
        return 1
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
