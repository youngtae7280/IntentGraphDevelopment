"""Verify consistency of a B1 non-applied proposal with facts and overlay."""

from __future__ import annotations

import argparse
import json
import hashlib
from pathlib import Path
from typing import Any


BENCHMARK_ID = "B1-typescript-rest-api"
REPORT_VERSION = "0.1.0"


class ConsistencyError(Exception):
    """Raised when consistency inputs cannot be loaded."""


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def digest_json(data: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ConsistencyError(f"{path} must contain a JSON object")
    return data


def index_by_id(items: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(items, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            result[item["id"]] = item
    return result


def verify(
    proposal: dict[str, Any],
    proposal_validation: dict[str, Any],
    code_facts: dict[str, Any],
    overlay: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []

    if proposal.get("artifactRole") != "intentgraph-b1-change-proposal":
        errors.append("proposal source must be B1 change proposal")
    if proposal_validation.get("artifactRole") != "intentgraph-b1-change-proposal-validation-report":
        errors.append("proposal validation source must be proposal validation report")
    if proposal_validation.get("result") != "pass":
        errors.append("proposal validation report must pass")
    if proposal_validation.get("proposalId") != proposal.get("proposalId"):
        errors.append("proposal validation report proposalId must match proposal")
    if code_facts.get("artifactRole") != "intentgraph-code-facts" or code_facts.get("status") != "intentgraph-code-facts-extracted":
        errors.append("code facts must be extracted B1 code facts")
    if overlay.get("artifactRole") != "intentgraph-b1-overlay" or overlay.get("status") != "intentgraph-b1-overlay-declared":
        errors.append("overlay must be declared B1 overlay")
    if proposal.get("benchmarkId") != BENCHMARK_ID or code_facts.get("benchmarkId") != BENCHMARK_ID or overlay.get("benchmarkId") != BENCHMARK_ID:
        errors.append("all inputs must target B1")

    baseline = proposal.get("baseline", {})
    actual_code_digest = digest_json(code_facts)
    if baseline.get("codeFactsDigest") != actual_code_digest:
        errors.append("proposal baseline codeFactsDigest is stale")
    if baseline.get("sourceDigests") != code_facts.get("sourceDigests"):
        errors.append("proposal baseline sourceDigests are stale")
    validation_baseline = proposal_validation.get("baseline", {})
    if validation_baseline.get("codeFactsDigestMatched") is not True:
        errors.append("proposal validation did not confirm code facts digest")
    if validation_baseline.get("sourceDigestsMatched") is not True:
        errors.append("proposal validation did not confirm source digests")

    facts = index_by_id(code_facts.get("facts", []))
    units = index_by_id(overlay.get("intentUnits", []))

    impact = proposal.get("impactScope", {})
    allowed_files = impact.get("allowedSourceFiles")
    if not isinstance(allowed_files, list) or not allowed_files:
        errors.append("impact scope must declare allowed source files")
        allowed_files = []
    for unit_id in impact.get("existingIntentUnitIds", []):
        unit = units.get(unit_id)
        if not unit:
            errors.append(f"impact scope references missing Intent Unit {unit_id}")
        elif unit.get("mappingStatus") != "resolved":
            errors.append(f"impact scope Intent Unit {unit_id} must be resolved")

    changes = proposal.get("deltaC", {}).get("plannedSourceChanges", [])
    if not changes:
        errors.append("proposal must declare planned source changes")
    for change in changes:
        if change.get("applied") is not False:
            errors.append(f"{change.get('id', '<missing>')} must remain non-applied")
        if change.get("targetFile") not in allowed_files:
            errors.append(f"{change.get('id', '<missing>')} target file outside impact scope")

    proposed_units = proposal.get("deltaI", {}).get("proposedIntentUnits", [])
    if not proposed_units:
        errors.append("proposal must declare proposed Intent Units")
    for unit in proposed_units:
        if unit.get("accepted") is not False:
            errors.append(f"{unit.get('id', '<missing>')} must not be accepted")

    mapping_updates = proposal.get("deltaM", {}).get("mappingUpdates", [])
    if not mapping_updates:
        errors.append("proposal must declare mapping updates")
    for update in mapping_updates:
        if update.get("accepted") is not False:
            errors.append(f"{update.get('id', '<missing>')} mapping update must not be accepted")
        if update.get("mappingObligationRequired") is not True:
            errors.append(f"{update.get('id', '<missing>')} must require mapping obligation")
        for fact_id in update.get("existingCodeFactIds", []):
            if fact_id not in facts:
                errors.append(f"{update.get('id', '<missing>')} references missing existing code fact {fact_id}")
        for future_fact in update.get("futureCodeFacts", []):
            if future_fact.get("sourceLocationStatus") != "future-not-applied":
                errors.append(f"{update.get('id', '<missing>')} future fact {future_fact.get('id')} must be future-not-applied")
            if future_fact.get("sourceFile") not in allowed_files:
                errors.append(f"{update.get('id', '<missing>')} future fact {future_fact.get('id')} outside impact scope")

    required_tests = proposal.get("requiredTests", [])
    required_evidence = proposal.get("requiredEvidence", [])
    required_authority = proposal.get("requiredAuthority", [])
    if not required_tests:
        errors.append("proposal consistency requires tests")
    if not required_evidence:
        errors.append("proposal consistency requires evidence")
    if not required_authority:
        errors.append("proposal consistency requires authority")
    for authority in required_authority:
        if authority.get("aiAuthority") is not False:
            errors.append(f"authority {authority.get('id')} must not grant AI authority")
        if authority.get("selfAuthorized") is not False:
            errors.append(f"authority {authority.get('id')} must not be self-authorized")

    claim_scope = proposal.get("claimScope", {})
    for forbidden in [
        "sourceMutated",
        "patchApplied",
        "automaticAcceptanceClaimed",
        "aiAuthorityGranted",
        "selfAuthorized",
        "broadPlannerClaimed",
        "workbenchClaimed",
        "productizationClaimed",
    ]:
        if claim_scope.get(forbidden) is not False:
            errors.append(f"claimScope.{forbidden} must be false")

    return {
        "artifactRole": "intentgraph-b1-proposal-consistency-report",
        "status": "intentgraph-b1-proposal-consistency-passed" if not errors else "intentgraph-b1-proposal-consistency-failed",
        "scope": "b1-typescript-rest-api-proposal-consistency-verification",
        "reportVersion": REPORT_VERSION,
        "benchmarkId": BENCHMARK_ID,
        "proposalId": proposal.get("proposalId"),
        "result": "pass" if not errors else "fail",
        "summary": {
            "plannedSourceChangeCount": len(changes),
            "proposedIntentUnitCount": len(proposed_units),
            "mappingUpdateCount": len(mapping_updates),
            "requiredTestCount": len(required_tests),
            "requiredEvidenceCount": len(required_evidence),
            "requiredAuthorityCount": len(required_authority),
            "errorCount": len(errors),
        },
        "baseline": {
            "codeFactsDigestMatched": baseline.get("codeFactsDigest") == actual_code_digest,
            "sourceDigestsMatched": baseline.get("sourceDigests") == code_facts.get("sourceDigests"),
            "proposalValidationPassed": proposal_validation.get("result") == "pass",
        },
        "claimScope": {
            "deterministicVerifier": True,
            "proposalOnly": True,
            "sourceMutated": False,
            "patchApplied": False,
            "aiJudgmentUsed": False,
            "fullSemanticEquivalenceClaimed": False,
        },
        "errors": errors,
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify B1 proposal consistency.")
    parser.add_argument("--proposal", required=True, type=Path)
    parser.add_argument("--proposal-validation", required=True, type=Path)
    parser.add_argument("--code-facts", required=True, type=Path)
    parser.add_argument("--overlay", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = verify(read_json(args.proposal), read_json(args.proposal_validation), read_json(args.code_facts), read_json(args.overlay))
        write_json(args.out, report)
    except (OSError, json.JSONDecodeError, ConsistencyError) as error:
        print(f"verify B1 proposal consistency failed: {error}")
        return 1
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
