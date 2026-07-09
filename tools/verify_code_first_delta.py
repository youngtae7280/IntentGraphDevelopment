"""Verify a tiny CF0 code-first maintenance delta."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from verify_code_first_overlay import verify as verify_overlay


REPORT_VERSION = "0.1.0"
ALLOWED_MODES = {
    "code-first-maintenance-delta",
    "code-first-refactor-delta",
    "code-first-overlay-only-contract-delta",
}


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


def source_digest(code_facts: dict[str, Any]) -> str | None:
    digest = code_facts.get("source", {}).get("sha256")
    if not isinstance(digest, str):
        return None
    return digest if digest.startswith("sha256:") else f"sha256:{digest}"


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


def unit_code_fact_ids(overlay: dict[str, Any], unit_id: str) -> set[str]:
    for unit in overlay.get("intentUnits", []):
        if isinstance(unit, dict) and unit.get("id") == unit_id:
            return {
                ref["factId"]
                for ref in unit.get("codeFactRefs", [])
                if isinstance(ref, dict) and isinstance(ref.get("factId"), str)
            }
    return set()


def record_ids(overlay: dict[str, Any], field: str) -> set[str]:
    return {
        record["id"]
        for record in overlay.get(field, [])
        if isinstance(record, dict) and isinstance(record.get("id"), str)
    }


def verify_delta(
    delta_path: Path,
    before_code_facts_path: Path,
    before_overlay_path: Path,
    after_code_facts_path: Path,
    overlay_path: Path,
    source_root: Path,
) -> dict[str, Any]:
    delta = read_json(delta_path)
    before_facts = read_json(before_code_facts_path)
    before_overlay = read_json(before_overlay_path)
    after_facts = read_json(after_code_facts_path)
    overlay = read_json(overlay_path)
    overlay_report = verify_overlay(overlay_path, after_code_facts_path, source_root)

    before_ids = fact_ids(before_facts)
    after_ids = fact_ids(after_facts)
    added_fact_ids = sorted(after_ids - before_ids)
    removed_fact_ids = sorted(before_ids - after_ids)
    expected_added = set(delta.get("expectedAfter", {}).get("addedCodeFactIds", []))
    expected_removed = set(delta.get("expectedAfter", {}).get("removedCodeFactIds", []))
    added_behaviors = set(delta.get("expectedAfter", {}).get("addedBehaviorUnits", []))
    preserved_behaviors = set(delta.get("expectedAfter", {}).get("preservedBehaviorUnits", []))
    remapped_units = [
        remap
        for remap in delta.get("expectedAfter", {}).get("remappedUnits", [])
        if isinstance(remap, dict)
    ]
    expected_authority_ids = set(delta.get("authorityIds", []))
    expected_evidence_ids = set(delta.get("evidenceIds", []))
    expected_history_ids = set(delta.get("historyIds", []))
    units = overlay_unit_ids(overlay)
    authority_ids = record_ids(overlay, "authority")
    evidence_ids = record_ids(overlay, "evidence")
    history_ids = record_ids(overlay, "history")

    checks: list[str] = []
    errors: list[str] = []
    if delta.get("mode") not in ALLOWED_MODES:
        errors.append(f"delta mode must be one of {sorted(ALLOWED_MODES)}")
    if delta.get("sourceTextEqualityRequired") is not False:
        errors.append("delta must not require source text equality")
    if delta.get("hiddenGeneratedCodeSnapshotUsed") is not False:
        errors.append("delta must not use hidden generated-code snapshots")
    source_changed = source_digest(before_facts) != source_digest(after_facts)
    overlay_changed = digest_json(before_overlay) != digest_json(overlay)
    expected_after = delta.get("expectedAfter", {})
    if "sourceChanged" in expected_after and expected_after.get("sourceChanged") is not source_changed:
        errors.append("sourceChanged expectation does not match before/after source digests")
    if "overlayChanged" in expected_after and expected_after.get("overlayChanged") is not overlay_changed:
        errors.append("overlayChanged expectation does not match before/after overlay digests")
    if delta.get("mode") == "code-first-overlay-only-contract-delta":
        if source_changed:
            errors.append("overlay-only contract delta must not change source bytes")
        if not overlay_changed:
            errors.append("overlay-only contract delta must change the overlay")
        if expected_after.get("contractCoverageIncreased") is not True:
            errors.append("overlay-only contract delta must declare increased contract coverage")
    if delta.get("before", {}).get("sourceDigest") != source_digest(before_facts):
        errors.append("before source digest does not match before code facts")
    if delta.get("before", {}).get("codeFactsDigest") != digest_json(before_facts):
        errors.append("before code facts digest does not match delta")
    if delta.get("before", {}).get("codeFactCount") != len(before_ids):
        errors.append("before code fact count does not match delta")
    if delta.get("before", {}).get("overlayDigest") != digest_json(before_overlay):
        errors.append("before overlay digest does not match before overlay artifact")
    if delta.get("before", {}).get("mappingObligationCount") != count_mapping_obligations(before_overlay):
        errors.append("before mapping obligation count does not match before overlay artifact")
    if not expected_added.issubset(set(added_fact_ids)):
        errors.append(f"missing expected added facts: {sorted(expected_added - set(added_fact_ids))}")
    if not expected_removed.issubset(set(removed_fact_ids)):
        errors.append(f"missing expected removed facts: {sorted(expected_removed - set(removed_fact_ids))}")
    if not added_behaviors.issubset(units):
        errors.append(f"missing added behavior units: {sorted(added_behaviors - units)}")
    if not preserved_behaviors.issubset(units):
        errors.append(f"missing preserved behavior units: {sorted(preserved_behaviors - units)}")
    for remap in remapped_units:
        unit_id = remap.get("unitId")
        from_facts = set(remap.get("fromCodeFactIds", []))
        to_facts = set(remap.get("toCodeFactIds", []))
        current_unit_facts = unit_code_fact_ids(overlay, unit_id) if isinstance(unit_id, str) else set()
        if unit_id not in units:
            errors.append(f"missing remapped unit: {unit_id}")
            continue
        if not from_facts.issubset(before_ids):
            errors.append(f"remapped unit {unit_id} missing before facts: {sorted(from_facts - before_ids)}")
        if from_facts.intersection(after_ids):
            errors.append(f"remapped unit {unit_id} old facts still present after refactor: {sorted(from_facts.intersection(after_ids))}")
        if not to_facts.issubset(after_ids):
            errors.append(f"remapped unit {unit_id} missing after facts: {sorted(to_facts - after_ids)}")
        if not to_facts.intersection(current_unit_facts):
            errors.append(f"remapped unit {unit_id} does not reference any new code facts")
        if from_facts.intersection(current_unit_facts):
            errors.append(f"remapped unit {unit_id} still references old code facts: {sorted(from_facts.intersection(current_unit_facts))}")
    if overlay_report["result"] != "pass":
        errors.append("after overlay verification failed")
    if not expected_evidence_ids.issubset(evidence_ids):
        errors.append(f"missing delta evidence records: {sorted(expected_evidence_ids - evidence_ids)}")
    if not expected_authority_ids.issubset(authority_ids):
        errors.append(f"missing delta authority records: {sorted(expected_authority_ids - authority_ids)}")
    if not expected_history_ids.issubset(history_ids):
        errors.append(f"missing delta history records: {sorted(expected_history_ids - history_ids)}")

    checks.append("before code facts captured independently")
    checks.append("before source digest verified against before code facts")
    checks.append("before overlay digest verified against before overlay artifact")
    checks.append("before mapping obligation count verified against before overlay artifact")
    checks.append("after overlay verification executed")
    checks.append("expected added and removed code facts verified")
    checks.append("remapped units verified when declared")
    checks.append("delta evidence, authority, and history ids verified")
    checks.append("source text equality not required")
    checks.append("hidden generated-code snapshot not used")

    return {
        "reportVersion": REPORT_VERSION,
        "mode": delta.get("mode", "code-first-maintenance-delta"),
        "result": "pass" if not errors else "fail",
        "sourceRole": after_facts.get("source", {}).get("role"),
        "sourceTextEqualityRequired": False,
        "hiddenGeneratedCodeSnapshotUsed": False,
        "inputs": {
            "delta": delta_path.as_posix(),
            "beforeCodeFacts": before_code_facts_path.as_posix(),
            "beforeOverlay": before_overlay_path.as_posix(),
            "afterCodeFacts": after_code_facts_path.as_posix(),
            "overlay": overlay_path.as_posix(),
            "sourceRoot": source_root.as_posix(),
        },
        "before": {
            "sourceDigest": source_digest(before_facts),
            "codeFactsDigest": digest_json(before_facts),
            "codeFactCount": len(before_ids),
            "overlayDigest": digest_json(before_overlay),
            "mappingObligationCount": count_mapping_obligations(before_overlay),
        },
        "after": {
            "sourceDigest": source_digest(after_facts),
            "codeFactsDigest": digest_json(after_facts),
            "codeFactCount": len(after_ids),
            "overlayDigest": digest_json(overlay),
            "mappingObligationCount": count_mapping_obligations(overlay),
        },
        "delta": {
            "deltaId": delta.get("deltaId"),
            "sourceChanged": source_changed,
            "overlayChanged": overlay_changed,
            "contractCoverageIncreased": expected_after.get("contractCoverageIncreased"),
            "addedBehaviorUnits": sorted(added_behaviors),
            "addedBehaviorCount": len(added_behaviors),
            "preservedBehaviorUnits": sorted(preserved_behaviors),
            "addedCodeFactIds": added_fact_ids,
            "removedCodeFactIds": removed_fact_ids,
            "expectedAddedCodeFactIds": sorted(expected_added),
            "expectedRemovedCodeFactIds": sorted(expected_removed),
            "remappedUnits": [
                {
                    "unitId": remap.get("unitId"),
                    "fromCodeFactIds": sorted(remap.get("fromCodeFactIds", [])),
                    "toCodeFactIds": sorted(remap.get("toCodeFactIds", [])),
                    "currentUnitCodeFactIds": sorted(unit_code_fact_ids(overlay, remap.get("unitId", ""))),
                }
                for remap in remapped_units
            ],
        },
        "deltaRecordsVerification": {
            "authorityIds": sorted(expected_authority_ids),
            "evidenceIds": sorted(expected_evidence_ids),
            "historyIds": sorted(expected_history_ids),
            "result": (
                "pass"
                if expected_authority_ids.issubset(authority_ids)
                and expected_evidence_ids.issubset(evidence_ids)
                and expected_history_ids.issubset(history_ids)
                else "fail"
            ),
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
    parser.add_argument("--before-overlay", required=True, type=Path)
    parser.add_argument("--after-code-facts", required=True, type=Path)
    parser.add_argument("--overlay", required=True, type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = verify_delta(
            args.delta,
            args.before_code_facts,
            args.before_overlay,
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
