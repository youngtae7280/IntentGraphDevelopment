"""Emit a deterministic CF0 overlay coverage/completeness report."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPORT_VERSION = "0.1.0"
ROOT = Path(__file__).resolve().parents[1]
REQUIRED_BEHAVIOR_UNITS = {
    "unit.behavior.add": "test.case.add",
    "unit.behavior.sub": "test.case.sub",
    "unit.behavior.mul": "test.case.mul",
    "unit.behavior.unsupported-operation": "test.case.unsupported-operation",
    "unit.behavior.invalid-integer-input": "test.case.invalid-integer",
    "unit.behavior.usage-arity": "test.case.usage-arity",
}


class CoverageReportError(Exception):
    """Raised when the CF0 coverage report cannot be emitted safely."""


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise CoverageReportError(f"{path} must contain a JSON object")
    return data


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def digest_bytes(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def id_index(items: Any, label: str) -> dict[str, dict[str, Any]]:
    if not isinstance(items, list):
        raise CoverageReportError(f"{label} must be a list")
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise CoverageReportError(f"{label} item missing string id")
        if item["id"] in result:
            raise CoverageReportError(f"duplicate {label} id: {item['id']}")
        result[item["id"]] = item
    return result


def fact_index(code_facts: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return id_index(code_facts.get("facts", []), "code fact")


def classify_uncovered_fact(fact: dict[str, Any]) -> dict[str, Any]:
    fact_id = fact["id"]
    fact_kind = fact.get("kind")
    if fact_kind == "call" and fact_id.endswith((".calls.int", ".calls.len", ".calls.print")):
        classification = "structural-low-level"
        reason = "Built-in parsing/printing call fact is useful context but not a standalone Intent Unit in CF0."
    elif fact_id == "fact.function.main.return.0":
        classification = "structural-low-level"
        reason = "Successful main return fact is covered through behavior smoke checks rather than a standalone Intent Unit."
    else:
        classification = "unclassified"
        reason = "Uncovered fact is not classified as intentionally structural."
    return {
        "id": fact_id,
        "kind": fact_kind,
        "classification": classification,
        "intentUnitRequired": classification == "unclassified",
        "reason": reason,
    }


def unit_ref_report(
    unit: dict[str, Any],
    facts: dict[str, dict[str, Any]],
    evidence_ids: set[str],
    authority_ids: set[str],
    history_ids: set[str],
    verification_ids: set[str],
) -> dict[str, Any]:
    unit_id = unit.get("id", "<missing>")
    code_refs = unit.get("codeRefs", [])
    code_fact_refs = unit.get("codeFactRefs", [])
    obligations = unit.get("mappingObligations", [])
    errors: list[str] = []
    covered_fact_ids: set[str] = set()

    if not isinstance(code_refs, list) or not code_refs:
        errors.append("missing non-empty codeRefs")
        code_refs = []
    if not isinstance(code_fact_refs, list) or not code_fact_refs:
        errors.append("missing non-empty codeFactRefs")
        code_fact_refs = []
    if not isinstance(obligations, list) or not obligations:
        errors.append("missing non-empty mappingObligations")
        obligations = []

    code_ref_ids = {ref.get("id") for ref in code_refs if isinstance(ref, dict)}
    code_fact_ref_ids = {ref.get("id") for ref in code_fact_refs if isinstance(ref, dict)}
    unresolved_code_refs: list[dict[str, Any]] = []
    unresolved_code_fact_refs: list[dict[str, Any]] = []
    unresolved_obligations: list[dict[str, Any]] = []

    for ref in code_refs:
        if not isinstance(ref, dict):
            errors.append("codeRef must be an object")
            continue
        fact_id = ref.get("factId")
        if ref.get("ownership") != "reference-only":
            errors.append(f"codeRef {ref.get('id')} is not reference-only")
        if fact_id in facts:
            covered_fact_ids.add(fact_id)
        else:
            unresolved_code_refs.append({"id": ref.get("id"), "factId": fact_id})
            errors.append(f"codeRef {ref.get('id')} references missing fact {fact_id}")

    for ref in code_fact_refs:
        if not isinstance(ref, dict):
            errors.append("codeFactRef must be an object")
            continue
        fact_id = ref.get("factId")
        expected_kind = ref.get("expectedFactKind")
        fact = facts.get(fact_id)
        if not fact:
            unresolved_code_fact_refs.append({"id": ref.get("id"), "factId": fact_id})
            errors.append(f"codeFactRef {ref.get('id')} references missing fact {fact_id}")
            continue
        covered_fact_ids.add(fact_id)
        if expected_kind and fact.get("kind") != expected_kind:
            errors.append(f"codeFactRef {ref.get('id')} expected {expected_kind} got {fact.get('kind')}")

    for obligation in obligations:
        if not isinstance(obligation, dict):
            errors.append("mappingObligation must be an object")
            continue
        obligation_id = obligation.get("id", "<missing>")
        obligation_errors: list[str] = []
        if obligation.get("sourceTextEqualityRequired") is not False:
            obligation_errors.append("sourceTextEqualityRequired must be false")
        for ref_id in obligation.get("codeRefIds", []):
            if ref_id not in code_ref_ids:
                obligation_errors.append(f"missing codeRef {ref_id}")
        for ref_id in obligation.get("codeFactRefIds", []):
            if ref_id not in code_fact_ref_ids:
                obligation_errors.append(f"missing codeFactRef {ref_id}")
        for evidence_id in obligation.get("evidenceIds", []):
            if evidence_id not in evidence_ids:
                obligation_errors.append(f"missing evidence {evidence_id}")
        for authority_id in obligation.get("authorityIds", []):
            if authority_id not in authority_ids:
                obligation_errors.append(f"missing authority {authority_id}")
        for verification_id in obligation.get("verificationIds", []):
            if verification_id not in verification_ids:
                obligation_errors.append(f"missing verification {verification_id}")
        if obligation_errors:
            unresolved_obligations.append({"id": obligation_id, "errors": obligation_errors})
            errors.extend(f"{obligation_id}: {error}" for error in obligation_errors)

    evidence_refs = unit.get("evidence", [])
    authority_refs = unit.get("authority", [])
    history_refs = unit.get("history", [])
    missing_evidence = [item for item in evidence_refs if item not in evidence_ids]
    missing_authority = [item for item in authority_refs if item not in authority_ids]
    missing_history = [item for item in history_refs if item not in history_ids]
    if not evidence_refs:
        errors.append("unit missing evidence refs")
    if not authority_refs:
        errors.append("unit missing authority refs")
    if not history_refs:
        errors.append("unit missing history refs")
    errors.extend(f"unit missing evidence {item}" for item in missing_evidence)
    errors.extend(f"unit missing authority {item}" for item in missing_authority)
    errors.extend(f"unit missing history {item}" for item in missing_history)

    return {
        "unitId": unit_id,
        "kind": unit.get("kind"),
        "result": "pass" if not errors else "fail",
        "codeRefCount": len(code_refs),
        "codeFactRefCount": len(code_fact_refs),
        "mappingObligationCount": len(obligations),
        "coveredFactIds": sorted(covered_fact_ids),
        "unresolvedCodeRefs": unresolved_code_refs,
        "unresolvedCodeFactRefs": unresolved_code_fact_refs,
        "unresolvedMappingObligations": unresolved_obligations,
        "evidenceCount": len(evidence_refs),
        "authorityCount": len(authority_refs),
        "historyCount": len(history_refs),
        "missingEvidence": missing_evidence,
        "missingAuthority": missing_authority,
        "missingHistory": missing_history,
        "errors": errors,
    }


def build_report(overlay_path: Path, code_facts_path: Path, source_root: Path) -> dict[str, Any]:
    overlay = read_json(overlay_path)
    code_facts = read_json(code_facts_path)
    facts = fact_index(code_facts)
    units = id_index(overlay.get("intentUnits", []), "intent unit")
    evidence_ids = set(id_index(overlay.get("evidence", []), "evidence"))
    authority_ids = set(id_index(overlay.get("authority", []), "authority"))
    history_ids = set(id_index(overlay.get("history", []), "history"))
    verification = id_index(overlay.get("verification", []), "verification")
    verification_ids = set(verification)

    source_rel = code_facts.get("source", {}).get("path")
    source_path = ROOT / source_rel if isinstance(source_rel, str) else source_root / "calc.py"
    source_digest = code_facts.get("source", {}).get("sha256")
    source_bytes_unchanged = source_path.exists() and source_digest == digest_bytes(source_path)

    unit_reports = [
        unit_ref_report(unit, facts, evidence_ids, authority_ids, history_ids, verification_ids)
        for unit in units.values()
    ]
    covered_fact_ids = sorted({fact_id for unit in unit_reports for fact_id in unit["coveredFactIds"]})
    uncovered = [
        classify_uncovered_fact(fact)
        for fact_id, fact in sorted(facts.items())
        if fact_id not in set(covered_fact_ids)
    ]
    unclassified_uncovered = [item for item in uncovered if item["classification"] == "unclassified"]

    required_units: list[dict[str, Any]] = []
    for unit_id, verification_id in sorted(REQUIRED_BEHAVIOR_UNITS.items()):
        unit = units.get(unit_id)
        unit_report = next((item for item in unit_reports if item["unitId"] == unit_id), None)
        required_units.append(
            {
                "unitId": unit_id,
                "present": unit is not None,
                "verificationId": verification_id,
                "verificationPresent": verification_id in verification_ids,
                "evidencePresent": bool(unit and unit.get("evidence")),
                "authorityPresent": bool(unit and unit.get("authority")),
                "historyPresent": bool(unit and unit.get("history")),
                "mappingPass": bool(unit_report and unit_report["result"] == "pass"),
            }
        )

    unresolved_ref_count = sum(
        len(unit["unresolvedCodeRefs"]) + len(unit["unresolvedCodeFactRefs"]) for unit in unit_reports
    )
    unresolved_obligation_count = sum(len(unit["unresolvedMappingObligations"]) for unit in unit_reports)
    required_units_pass = all(
        unit["present"]
        and unit["verificationPresent"]
        and unit["evidencePresent"]
        and unit["authorityPresent"]
        and unit["historyPresent"]
        and unit["mappingPass"]
        for unit in required_units
    )
    mapping_pass = unresolved_ref_count == 0 and unresolved_obligation_count == 0 and all(
        unit["result"] == "pass" for unit in unit_reports
    )
    behavior_verification_pass = all(item["verificationPresent"] for item in required_units)
    semantic_coverage_pass = required_units_pass and not unclassified_uncovered
    boundaries = {
        "sourceBytesUnchanged": source_bytes_unchanged,
        "sourceTextEqualityRequired": False,
        "hiddenGeneratedCodeSnapshotUsed": False,
        "aiAuthorityPromoted": False,
        "productBehaviorChanged": False,
        "broadExtractorClaimed": False,
        "genericCoverageFrameworkClaimed": False,
    }
    result = (
        mapping_pass
        and behavior_verification_pass
        and semantic_coverage_pass
        and boundaries["sourceBytesUnchanged"]
        and boundaries["sourceTextEqualityRequired"] is False
        and boundaries["hiddenGeneratedCodeSnapshotUsed"] is False
        and boundaries["aiAuthorityPromoted"] is False
        and boundaries["productBehaviorChanged"] is False
    )

    return {
        "artifactRole": "intentgraph-cf0-overlay-coverage-report",
        "reportVersion": REPORT_VERSION,
        "status": "pass" if result else "fail",
        "result": "pass" if result else "fail",
        "scope": "cf0-code-first-overlay-coverage-current-state",
        "inputs": {
            "overlay": overlay_path.as_posix(),
            "codeFacts": code_facts_path.as_posix(),
            "sourceRoot": source_root.as_posix(),
        },
        "source": {
            "path": source_rel,
            "role": code_facts.get("source", {}).get("role"),
            "sha256": source_digest,
        },
        "codeFacts": {
            "factCount": len(facts),
            "coveredFactCount": len(covered_fact_ids),
            "uncoveredFactCount": len(uncovered),
            "unclassifiedUncoveredFactCount": len(unclassified_uncovered),
            "extractor": code_facts.get("extractor"),
        },
        "overlay": {
            "unitCount": len(units),
            "behaviorUnitCount": sum(1 for unit in units.values() if unit.get("kind") == "behavior"),
            "productUnitCount": sum(1 for unit in units.values() if unit.get("kind") == "product"),
            "verificationCount": len(verification_ids),
            "evidenceCount": len(evidence_ids),
            "authorityCount": len(authority_ids),
            "historyCount": len(history_ids),
        },
        "requiredBehaviorUnits": required_units,
        "unitCoverage": unit_reports,
        "factCoverage": {
            "coveredFactIds": covered_fact_ids,
            "uncoveredFacts": uncovered,
        },
        "mappingCoverage": {
            "result": "pass" if mapping_pass else "fail",
            "mappingObligationCount": sum(unit["mappingObligationCount"] for unit in unit_reports),
            "unresolvedOverlayRefCount": unresolved_ref_count,
            "unresolvedMappingObligationCount": unresolved_obligation_count,
        },
        "semanticCoverage": {
            "result": "pass" if semantic_coverage_pass else "fail",
            "requiredBehaviorUnitsPass": required_units_pass,
            "behaviorVerificationCoveragePass": behavior_verification_pass,
            "evidenceAuthorityHistoryCoveragePass": all(
                unit["evidencePresent"] and unit["authorityPresent"] and unit["historyPresent"]
                for unit in required_units
            ),
            "structuralFactsDoNotRequireIntentUnits": True,
        },
        "boundaries": boundaries,
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit CF0 overlay coverage/completeness report.")
    parser.add_argument("--overlay", required=True, type=Path)
    parser.add_argument("--code-facts", required=True, type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = build_report(args.overlay, args.code_facts, args.source_root)
        write_json(args.out, report)
    except (OSError, json.JSONDecodeError, CoverageReportError) as error:
        print(f"emit CF0 overlay coverage report failed: {error}")
        return 1
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
