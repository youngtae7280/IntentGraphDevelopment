"""Verify B1 Intent Unit overlay mappings against B1 code facts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_VERSION = "0.1.0"
BENCHMARK_ID = "B1-typescript-rest-api"
ALLOWED_MAPPING_STATUS = {"resolved", "ambiguous", "unmapped-explicit"}
ALLOWED_UNIT_KINDS = {"behavior", "contract", "route", "verification"}


class MappingVerifyError(Exception):
    """Raised when mapping verification inputs are malformed."""


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise MappingVerifyError(f"{path} must contain a JSON object")
    return data


def index_by_id(items: list[Any], label: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise MappingVerifyError(f"{label} contains item without string id")
        if item["id"] in result:
            raise MappingVerifyError(f"{label} contains duplicate id {item['id']}")
        result[item["id"]] = item
    return result


def verify(overlay: dict[str, Any], code_facts: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if overlay.get("artifactRole") != "intentgraph-b1-overlay":
        errors.append(f"wrong overlay artifactRole: {overlay.get('artifactRole')}")
    if overlay.get("status") != "intentgraph-b1-overlay-declared":
        errors.append(f"wrong overlay status: {overlay.get('status')}")
    if overlay.get("scope") != "b1-typescript-rest-api-intent-mapping":
        errors.append(f"wrong overlay scope: {overlay.get('scope')}")
    if overlay.get("benchmarkId") != BENCHMARK_ID or code_facts.get("benchmarkId") != BENCHMARK_ID:
        errors.append("overlay and code facts must target B1")

    facts = index_by_id(code_facts.get("facts", []), "code facts")
    evidence = index_by_id(overlay.get("evidence", []), "evidence")
    authority = index_by_id(overlay.get("authority", []), "authority")
    verification = index_by_id(overlay.get("verification", []), "verification")
    history = index_by_id(overlay.get("history", []), "history")
    units = overlay.get("intentUnits")
    if not isinstance(units, list) or not units:
        errors.append("overlay requires non-empty intentUnits")
        units = []

    unit_reports: list[dict[str, Any]] = []
    for unit in units:
        if not isinstance(unit, dict):
            errors.append("intent unit must be object")
            continue
        unit_id = str(unit.get("id", "<missing>"))
        unit_errors: list[str] = []
        if unit.get("kind") not in ALLOWED_UNIT_KINDS:
            unit_errors.append(f"unknown unit kind: {unit.get('kind')}")
        mapping_status = unit.get("mappingStatus")
        if mapping_status not in ALLOWED_MAPPING_STATUS:
            unit_errors.append(f"invalid mappingStatus: {mapping_status}")
        if unit.get("codeTextContained") is not False:
            unit_errors.append("codeTextContained must be false")
        if "codeText" in unit:
            unit_errors.append("unit must not contain codeText")
        if mapping_status == "resolved" and unit.get("ambiguity"):
            unit_errors.append("resolved unit must not declare ambiguity")

        code_refs = unit.get("codeRefs")
        code_fact_refs = unit.get("codeFactRefs")
        obligations = unit.get("mappingObligations")
        if not isinstance(code_refs, list) or not code_refs:
            unit_errors.append("missing non-empty codeRefs")
            code_refs = []
        if not isinstance(code_fact_refs, list) or not code_fact_refs:
            unit_errors.append("missing non-empty codeFactRefs")
            code_fact_refs = []
        if not isinstance(obligations, list) or not obligations:
            unit_errors.append("missing non-empty mappingObligations")
            obligations = []

        code_ref_index = index_local(code_refs, "codeRef", unit_errors)
        code_fact_ref_index = index_local(code_fact_refs, "codeFactRef", unit_errors)

        for code_ref in code_refs:
            ref_id = str(code_ref.get("id", "<missing>"))
            fact_id = code_ref.get("factId")
            if code_ref.get("ownership") != "reference-only":
                unit_errors.append(f"{ref_id} ownership must be reference-only")
            if fact_id not in facts:
                unit_errors.append(f"{ref_id} references missing fact {fact_id}")
        for code_fact_ref in code_fact_refs:
            ref_id = str(code_fact_ref.get("id", "<missing>"))
            fact_id = code_fact_ref.get("factId")
            expected_kind = code_fact_ref.get("expectedFactKind")
            fact = facts.get(fact_id)
            if not fact:
                unit_errors.append(f"{ref_id} references missing fact {fact_id}")
            elif fact.get("kind") != expected_kind:
                unit_errors.append(f"{ref_id} expected {expected_kind} got {fact.get('kind')}")
        for obligation in obligations:
            obligation_id = str(obligation.get("id", "<missing>"))
            if obligation.get("sourceTextEqualityRequired") is not False:
                unit_errors.append(f"{obligation_id} must not require source text equality")
            for ref_id in obligation.get("codeRefIds", []):
                if ref_id not in code_ref_index:
                    unit_errors.append(f"{obligation_id} missing codeRef {ref_id}")
            for ref_id in obligation.get("codeFactRefIds", []):
                if ref_id not in code_fact_ref_index:
                    unit_errors.append(f"{obligation_id} missing codeFactRef {ref_id}")
            for verification_id in obligation.get("verificationIds", []):
                if verification_id not in verification:
                    unit_errors.append(f"{obligation_id} missing verification {verification_id}")
            for evidence_id in obligation.get("evidenceIds", []):
                if evidence_id not in evidence:
                    unit_errors.append(f"{obligation_id} missing evidence {evidence_id}")
            for authority_id in obligation.get("authorityIds", []):
                if authority_id not in authority:
                    unit_errors.append(f"{obligation_id} missing authority {authority_id}")
        errors.extend(f"{unit_id}: {error}" for error in unit_errors)
        unit_reports.append(
            {
                "unitId": unit_id,
                "kind": unit.get("kind"),
                "mappingStatus": mapping_status,
                "codeRefCount": len(code_refs),
                "codeFactRefCount": len(code_fact_refs),
                "mappingObligationCount": len(obligations),
                "errorCount": len(unit_errors),
            }
        )

    claim_scope = overlay.get("claimScope", {})
    for forbidden in ["sourceTextContained", "sourceTextEqualityRequired", "aiAuthorityClaimed", "automaticMappingClaimed", "codeEdited", "workbenchClaimed"]:
        if claim_scope.get(forbidden) is not False:
            errors.append(f"claimScope.{forbidden} must be false")
    for authority_record in authority.values():
        if authority_record.get("aiAuthority") is not False:
            errors.append(f"authority {authority_record.get('id')} must not grant AI authority")

    return {
        "artifactRole": "intentgraph-b1-intent-mapping-verification-report",
        "status": "intentgraph-b1-intent-mapping-verification-passed" if not errors else "intentgraph-b1-intent-mapping-verification-failed",
        "scope": "b1-typescript-rest-api-intent-mapping-verification",
        "reportVersion": REPORT_VERSION,
        "benchmarkId": BENCHMARK_ID,
        "result": "pass" if not errors else "fail",
        "summary": {
            "unitCount": len(units),
            "evidenceCount": len(evidence),
            "authorityCount": len(authority),
            "verificationCount": len(verification),
            "historyCount": len(history),
            "errorCount": len(errors),
        },
        "unitReports": unit_reports,
        "claimScope": {
            "staticB1OverlayOnly": True,
            "codeEdited": False,
            "automaticMappingClaimed": False,
            "aiAuthorityClaimed": False,
            "workbenchClaimed": False,
        },
        "errors": errors,
    }


def index_local(items: list[Any], label: str, errors: list[str]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            errors.append(f"{label} missing string id")
            continue
        result[item["id"]] = item
    return result


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify B1 intent mapping overlay.")
    parser.add_argument("--overlay", required=True, type=Path)
    parser.add_argument("--code-facts", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = verify(read_json(args.overlay), read_json(args.code_facts))
        write_json(args.out, report)
    except (OSError, json.JSONDecodeError, MappingVerifyError) as error:
        print(f"verify B1 intent mapping failed: {error}")
        return 1
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
