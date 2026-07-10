"""Verify B1 mapping candidate artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_VERSION = "0.1.0"
BENCHMARK_ID = "B1-typescript-rest-api"
ALLOWED_STATUS = {"ambiguous-unresolved", "rejected", "accepted-by-authority"}


class CandidateVerifyError(Exception):
    """Raised when mapping candidate inputs are malformed."""


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise CandidateVerifyError(f"{path} must contain a JSON object")
    return data


def verify(candidates: dict[str, Any], code_facts: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if candidates.get("artifactRole") != "intentgraph-b1-mapping-candidates":
        errors.append(f"wrong artifactRole: {candidates.get('artifactRole')}")
    if candidates.get("status") != "intentgraph-b1-mapping-candidates-declared":
        errors.append(f"wrong status: {candidates.get('status')}")
    if candidates.get("scope") != "b1-typescript-rest-api-ambiguous-mapping-candidates":
        errors.append(f"wrong scope: {candidates.get('scope')}")
    if candidates.get("benchmarkId") != BENCHMARK_ID or code_facts.get("benchmarkId") != BENCHMARK_ID:
        errors.append("candidate artifact and code facts must target B1")
    fact_ids = {fact.get("id") for fact in code_facts.get("facts", []) if isinstance(fact, dict)}
    candidate_items = candidates.get("candidates")
    if not isinstance(candidate_items, list) or not candidate_items:
        errors.append("candidates must be a non-empty array")
        candidate_items = []

    reports: list[dict[str, Any]] = []
    for candidate in candidate_items:
        if not isinstance(candidate, dict):
            errors.append("candidate must be object")
            continue
        candidate_id = str(candidate.get("id", "<missing>"))
        candidate_errors: list[str] = []
        if candidate.get("status") not in ALLOWED_STATUS:
            candidate_errors.append(f"invalid candidate status: {candidate.get('status')}")
        if candidate.get("status") == "accepted-by-authority":
            candidate_errors.append("accepted-by-authority is forbidden in P3.2")
        if candidate.get("accepted") is not False:
            candidate_errors.append("candidate.accepted must be false")
        if not isinstance(candidate.get("ambiguity"), dict):
            candidate_errors.append("candidate must declare ambiguity")
        fact_refs = candidate.get("candidateFactIds")
        if not isinstance(fact_refs, list) or not fact_refs:
            candidate_errors.append("candidateFactIds must be non-empty")
            fact_refs = []
        for fact_id in fact_refs:
            if fact_id not in fact_ids:
                candidate_errors.append(f"candidate fact does not exist: {fact_id}")
        claim_scope = candidate.get("claimScope", {})
        for forbidden in ["aiGenerated", "authorityGranted", "acceptedIntoOverlay"]:
            if claim_scope.get(forbidden) is not False:
                candidate_errors.append(f"claimScope.{forbidden} must be false")
        errors.extend(f"{candidate_id}: {error}" for error in candidate_errors)
        reports.append(
            {
                "candidateId": candidate_id,
                "status": candidate.get("status"),
                "accepted": candidate.get("accepted"),
                "candidateFactCount": len(fact_refs),
                "errorCount": len(candidate_errors),
            }
        )

    return {
        "artifactRole": "intentgraph-b1-mapping-candidates-verification-report",
        "status": "intentgraph-b1-mapping-candidates-verification-passed" if not errors else "intentgraph-b1-mapping-candidates-verification-failed",
        "scope": "b1-typescript-rest-api-mapping-candidates-verification",
        "reportVersion": REPORT_VERSION,
        "benchmarkId": BENCHMARK_ID,
        "result": "pass" if not errors else "fail",
        "summary": {
            "candidateCount": len(candidate_items),
            "errorCount": len(errors),
        },
        "candidateReports": reports,
        "claimScope": {
            "ambiguousCandidatesVisible": True,
            "acceptedIntoOverlay": False,
            "aiAuthorityClaimed": False,
            "automaticResolutionClaimed": False,
        },
        "errors": errors,
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify B1 mapping candidates.")
    parser.add_argument("--candidates", required=True, type=Path)
    parser.add_argument("--code-facts", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = verify(read_json(args.candidates), read_json(args.code_facts))
        write_json(args.out, report)
    except (OSError, json.JSONDecodeError, CandidateVerifyError) as error:
        print(f"verify B1 mapping candidates failed: {error}")
        return 1
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
