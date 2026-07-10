"""Validate B1 non-applied change proposal artifacts."""

from __future__ import annotations

import argparse
import json
import hashlib
from pathlib import Path
from typing import Any


BENCHMARK_ID = "B1-typescript-rest-api"
REPORT_VERSION = "0.1.0"


class ProposalValidationError(Exception):
    """Raised when proposal validation input cannot be read."""


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def digest_json(data: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ProposalValidationError(f"{path} must contain a JSON object")
    return data


def index_by_id(items: Any, label: str, errors: list[str]) -> dict[str, dict[str, Any]]:
    if not isinstance(items, list):
        errors.append(f"{label} must be a list")
        return {}
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            errors.append(f"{label} item missing string id")
            continue
        if item["id"] in result:
            errors.append(f"{label} duplicate id {item['id']}")
        result[item["id"]] = item
    return result


def validate(proposal: dict[str, Any], code_facts: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if proposal.get("artifactRole") != "intentgraph-b1-change-proposal":
        errors.append(f"wrong proposal artifactRole: {proposal.get('artifactRole')}")
    if proposal.get("status") != "intentgraph-b1-change-proposal-proposed":
        errors.append(f"wrong proposal status: {proposal.get('status')}")
    if proposal.get("scope") != "b1-typescript-rest-api-change-proposal-non-applied":
        errors.append(f"wrong proposal scope: {proposal.get('scope')}")
    if proposal.get("benchmarkId") != BENCHMARK_ID or code_facts.get("benchmarkId") != BENCHMARK_ID or overlay.get("benchmarkId") != BENCHMARK_ID:
        errors.append("proposal, code facts, and overlay must target B1")
    if proposal.get("proposalMode") != "non-applied-plan":
        errors.append("proposalMode must be non-applied-plan")
    if proposal.get("applicationStatus") != "not-applied":
        errors.append("applicationStatus must be not-applied")

    if code_facts.get("artifactRole") != "intentgraph-code-facts" or code_facts.get("status") != "intentgraph-code-facts-extracted":
        errors.append("code facts source must be extracted code facts")
    if overlay.get("artifactRole") != "intentgraph-b1-overlay" or overlay.get("status") != "intentgraph-b1-overlay-declared":
        errors.append("overlay source must be declared B1 overlay")

    baseline = proposal.get("baseline", {})
    actual_code_digest = digest_json(code_facts)
    if baseline.get("codeFactsDigest") != actual_code_digest:
        errors.append("baseline codeFactsDigest does not match supplied code facts")
    if baseline.get("sourceDigests") != code_facts.get("sourceDigests"):
        errors.append("baseline sourceDigests do not match supplied code facts")
    if not baseline.get("codeFactsPath") or not baseline.get("overlayPath"):
        errors.append("baseline must declare codeFactsPath and overlayPath")

    facts = index_by_id(code_facts.get("facts", []), "code facts", errors)
    units = index_by_id(overlay.get("intentUnits", []), "overlay intentUnits", errors)

    impact = proposal.get("impactScope", {})
    allowed_files = impact.get("allowedSourceFiles")
    if not isinstance(allowed_files, list) or not allowed_files:
        errors.append("impactScope.allowedSourceFiles must be non-empty")
        allowed_files = []
    source_digest_map = code_facts.get("sourceDigests", {})
    for source_file in allowed_files:
        if source_file not in source_digest_map:
            errors.append(f"impactScope references unknown source file {source_file}")
    for unit_id in impact.get("existingIntentUnitIds", []):
        if unit_id not in units:
            errors.append(f"impactScope references unknown existing Intent Unit {unit_id}")

    delta_c = proposal.get("deltaC", {})
    changes = delta_c.get("plannedSourceChanges")
    if not isinstance(changes, list) or not changes:
        errors.append("deltaC.plannedSourceChanges must be non-empty")
        changes = []
    if delta_c.get("sourceTextIncluded") is not False:
        errors.append("deltaC.sourceTextIncluded must be false")
    if delta_c.get("patchIncluded") is not False:
        errors.append("deltaC.patchIncluded must be false")
    for change in changes:
        change_id = change.get("id", "<missing>")
        if change.get("applied") is not False:
            errors.append(f"{change_id} must be non-applied")
        target_file = change.get("targetFile")
        if target_file not in allowed_files:
            errors.append(f"{change_id} targets file outside impact scope: {target_file}")
        for forbidden in ["sourceText", "patch", "diff", "replacementText"]:
            if forbidden in change:
                errors.append(f"{change_id} must not contain {forbidden}")

    delta_i = proposal.get("deltaI", {})
    proposed_units = delta_i.get("proposedIntentUnits")
    if not isinstance(proposed_units, list) or not proposed_units:
        errors.append("deltaI.proposedIntentUnits must be non-empty")
        proposed_units = []
    for unit in proposed_units:
        if unit.get("mappingStatus") != "planned":
            errors.append(f"{unit.get('id', '<missing>')} mappingStatus must be planned")
        if unit.get("accepted") is not False:
            errors.append(f"{unit.get('id', '<missing>')} accepted must be false")

    delta_m = proposal.get("deltaM", {})
    mapping_updates = delta_m.get("mappingUpdates")
    if not isinstance(mapping_updates, list) or not mapping_updates:
        errors.append("deltaM.mappingUpdates must be non-empty")
        mapping_updates = []
    for update in mapping_updates:
        update_id = update.get("id", "<missing>")
        if update.get("accepted") is not False:
            errors.append(f"{update_id} accepted must be false")
        if update.get("mappingObligationRequired") is not True:
            errors.append(f"{update_id} must require mapping obligation")
        for fact_id in update.get("existingCodeFactIds", []):
            if fact_id not in facts:
                errors.append(f"{update_id} references missing existing code fact {fact_id}")
        future_facts = update.get("futureCodeFacts")
        if not isinstance(future_facts, list) or not future_facts:
            errors.append(f"{update_id} must declare future code facts")
            future_facts = []
        for future_fact in future_facts:
            if future_fact.get("sourceLocationStatus") != "future-not-applied":
                errors.append(f"{update_id} future fact {future_fact.get('id')} must be future-not-applied")
            if future_fact.get("sourceFile") not in allowed_files:
                errors.append(f"{update_id} future fact {future_fact.get('id')} is outside impact scope")

    required_tests = proposal.get("requiredTests")
    required_evidence = proposal.get("requiredEvidence")
    required_authority = proposal.get("requiredAuthority")
    if not isinstance(required_tests, list) or not required_tests:
        errors.append("requiredTests must be non-empty")
        required_tests = []
    if not isinstance(required_evidence, list) or not required_evidence:
        errors.append("requiredEvidence must be non-empty")
        required_evidence = []
    if not isinstance(required_authority, list) or not required_authority:
        errors.append("requiredAuthority must be non-empty")
        required_authority = []
    for item in required_tests:
        if item.get("requiredBeforeAcceptance") is not True:
            errors.append(f"test {item.get('id')} must be required before acceptance")
    for item in required_evidence:
        if item.get("requiredBeforeAcceptance") is not True:
            errors.append(f"evidence {item.get('id')} must be required before acceptance")
    for item in required_authority:
        if item.get("requiredBeforeAcceptance") is not True:
            errors.append(f"authority {item.get('id')} must be required before acceptance")
        if item.get("aiAuthority") is not False:
            errors.append(f"authority {item.get('id')} must not grant AI authority")
        if item.get("selfAuthorized") is not False:
            errors.append(f"authority {item.get('id')} must not be self-authorized")

    ambiguity = proposal.get("ambiguityBoundary", {})
    if ambiguity.get("ambiguousCandidateResolved") is not False:
        errors.append("ambiguityBoundary.ambiguousCandidateResolved must be false")
    if ambiguity.get("automaticAmbiguityResolutionClaimed") is not False:
        errors.append("automatic ambiguity resolution is forbidden")

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
        "artifactRole": "intentgraph-b1-change-proposal-validation-report",
        "status": "intentgraph-b1-change-proposal-validation-passed" if not errors else "intentgraph-b1-change-proposal-validation-failed",
        "scope": "b1-typescript-rest-api-change-proposal-validation",
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
            "allowedSourceFiles": allowed_files,
        },
        "claimScope": {
            "proposalOnly": True,
            "sourceMutated": False,
            "patchApplied": False,
            "aiAuthorityGranted": False,
            "selfAuthorized": False,
            "automaticAcceptanceClaimed": False,
        },
        "errors": errors,
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a B1 non-applied change proposal.")
    parser.add_argument("--proposal", required=True, type=Path)
    parser.add_argument("--code-facts", required=True, type=Path)
    parser.add_argument("--overlay", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = validate(read_json(args.proposal), read_json(args.code_facts), read_json(args.overlay))
        write_json(args.out, report)
    except (OSError, json.JSONDecodeError, ProposalValidationError) as error:
        print(f"validate B1 change proposal failed: {error}")
        return 1
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
