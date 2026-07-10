"""Verify a bounded B1 incremental code fact change."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPORT_VERSION = "0.1.0"
BENCHMARK_ID = "B1-typescript-rest-api"


class IncrementalVerifyError(Exception):
    """Raised when incremental verification inputs are malformed."""


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise IncrementalVerifyError(f"{path} must contain a JSON object")
    return data


def index_by_id(items: list[Any], label: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            raise IncrementalVerifyError(f"{label} contains item without string id")
        if item["id"] in result:
            raise IncrementalVerifyError(f"{label} contains duplicate id {item['id']}")
        result[item["id"]] = item
    return result


def sorted_delta(before: set[str], after: set[str]) -> tuple[list[str], list[str]]:
    return sorted(after - before), sorted(before - after)


def changed_ids(before: dict[str, dict[str, Any]], after: dict[str, dict[str, Any]]) -> list[str]:
    return sorted(key for key in before.keys() & after.keys() if before[key] != after[key])


def facts_for_file(facts: dict[str, dict[str, Any]], source_file: str) -> dict[str, dict[str, Any]]:
    return {fact_id: fact for fact_id, fact in facts.items() if fact.get("sourceFile") == source_file}


def compare_expected(label: str, actual: list[str], expected: list[str], errors: list[str]) -> None:
    if actual != expected:
        errors.append(f"{label} mismatch: actual={actual} expected={expected}")


def verify(delta: dict[str, Any], before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if delta.get("artifactRole") != "intentgraph-code-fact-incremental-delta":
        errors.append(f"wrong delta artifactRole: {delta.get('artifactRole')}")
    if delta.get("status") != "intentgraph-code-fact-incremental-delta-declared":
        errors.append(f"wrong delta status: {delta.get('status')}")
    if delta.get("benchmarkId") != BENCHMARK_ID:
        errors.append(f"wrong delta benchmarkId: {delta.get('benchmarkId')}")
    if before.get("benchmarkId") != BENCHMARK_ID or after.get("benchmarkId") != BENCHMARK_ID:
        errors.append("before and after code facts must be B1 reports")

    before_facts = index_by_id(before.get("facts", []), "before facts")
    after_facts = index_by_id(after.get("facts", []), "after facts")
    before_relations = index_by_id(before.get("relations", []), "before relations")
    after_relations = index_by_id(after.get("relations", []), "after relations")

    before_digests = before.get("sourceDigests", {})
    after_digests = after.get("sourceDigests", {})
    if not isinstance(before_digests, dict) or not isinstance(after_digests, dict):
        errors.append("before/after sourceDigests must be objects")
        before_digests = {}
        after_digests = {}

    policy = delta.get("sourceChangePolicy", {})
    changed_files = sorted(policy.get("changedSourceFiles", []))
    unchanged_files = sorted(policy.get("unchangedSourceFiles", []))
    if policy.get("exactlyOneSourceFileChanged") is not True:
        errors.append("delta must require exactlyOneSourceFileChanged true")
    actual_changed_files = sorted(
        path for path in set(before_digests) | set(after_digests) if before_digests.get(path) != after_digests.get(path)
    )
    compare_expected("changed source files", actual_changed_files, changed_files, errors)
    if len(actual_changed_files) != 1:
        errors.append(f"expected exactly one changed source file, got {len(actual_changed_files)}")
    for path in unchanged_files:
        if before_digests.get(path) != after_digests.get(path):
            errors.append(f"unchanged file digest changed: {path}")
        if facts_for_file(before_facts, path) != facts_for_file(after_facts, path):
            errors.append(f"unchanged file facts changed: {path}")

    added_facts, removed_facts = sorted_delta(set(before_facts), set(after_facts))
    changed_facts = changed_ids(before_facts, after_facts)
    expected_fact_delta = delta.get("expectedFactDelta", {})
    compare_expected("added facts", added_facts, sorted(expected_fact_delta.get("addedFactIds", [])), errors)
    compare_expected("removed facts", removed_facts, sorted(expected_fact_delta.get("removedFactIds", [])), errors)
    compare_expected("changed facts", changed_facts, sorted(expected_fact_delta.get("changedFactIds", [])), errors)

    added_relations, removed_relations = sorted_delta(set(before_relations), set(after_relations))
    changed_relations = changed_ids(before_relations, after_relations)
    expected_relation_delta = delta.get("expectedRelationDelta", {})
    compare_expected("added relations", added_relations, sorted(expected_relation_delta.get("addedRelationIds", [])), errors)
    compare_expected("removed relations", removed_relations, sorted(expected_relation_delta.get("removedRelationIds", [])), errors)
    compare_expected("changed relations", changed_relations, sorted(expected_relation_delta.get("changedRelationIds", [])), errors)

    claim_scope = delta.get("claimScope", {})
    for forbidden in ["broadExtractorClaimed", "intentMappingClaimed", "workbenchClaimed", "aiAuthorityClaimed"]:
        if claim_scope.get(forbidden) is not False:
            errors.append(f"claimScope.{forbidden} must be false")

    return {
        "artifactRole": "intentgraph-code-fact-incremental-verification-report",
        "status": "intentgraph-code-fact-incremental-verification-passed" if not errors else "intentgraph-code-fact-incremental-verification-failed",
        "scope": "b1-typescript-rest-api-incremental-change-verification",
        "reportVersion": REPORT_VERSION,
        "benchmarkId": BENCHMARK_ID,
        "changeId": delta.get("changeId"),
        "result": "pass" if not errors else "fail",
        "summary": {
            "changedSourceFiles": actual_changed_files,
            "addedFactCount": len(added_facts),
            "removedFactCount": len(removed_facts),
            "changedFactCount": len(changed_facts),
            "addedRelationCount": len(added_relations),
            "removedRelationCount": len(removed_relations),
            "changedRelationCount": len(changed_relations),
            "errorCount": len(errors),
        },
        "factDelta": {
            "added": added_facts,
            "removed": removed_facts,
            "changed": changed_facts,
        },
        "relationDelta": {
            "added": added_relations,
            "removed": removed_relations,
            "changed": changed_relations,
        },
        "claimScope": {
            "b1FixtureBounded": True,
            "incrementalBehaviorMeasured": True,
            "broadExtractorClaimed": False,
            "intentMappingClaimed": False,
            "workbenchClaimed": False,
            "aiAuthorityClaimed": False,
        },
        "errors": errors,
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify B1 incremental code fact change.")
    parser.add_argument("--delta", required=True, type=Path)
    parser.add_argument("--before-code-facts", required=True, type=Path)
    parser.add_argument("--after-code-facts", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = verify(read_json(args.delta), read_json(args.before_code_facts), read_json(args.after_code_facts))
        write_json(args.out, report)
    except (OSError, json.JSONDecodeError, IncrementalVerifyError) as error:
        print(f"verify B1 incremental change failed: {error}")
        return 1
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
