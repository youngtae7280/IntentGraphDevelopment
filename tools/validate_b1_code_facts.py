"""Validate B1 TypeScript REST code fact reports."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPORT_VERSION = "0.1.0"
BENCHMARK_ID = "B1-typescript-rest-api"
EXPECTED_ROLE = "intentgraph-code-facts"
EXPECTED_STATUS = "intentgraph-code-facts-extracted"
EXPECTED_SCOPE = "b1-typescript-rest-api-code-facts"

ALLOWED_FACT_KINDS = {"file", "module", "function", "type", "route", "test", "import", "call"}
ENDPOINT_FACT_KINDS = {"file", "module", "function", "type", "route", "test"}
ALLOWED_RELATION_KINDS = {"contains", "imports", "references", "calls", "handles_route", "tests", "depends_on"}
ALLOWED_CONFIDENCE = {"extracted", "inferred", "ambiguous"}
REQUIRED_FACT_FIELDS = {"id", "kind", "sourceFile", "sourceDigest", "extractor", "extractorVersion", "confidence"}


class ValidationError(Exception):
    """Raised when a validation input cannot be read."""


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValidationError(f"{path} must contain a JSON object")
    return data


def source_digest(source_root: Path, relative_path: str) -> str | None:
    path = source_root / relative_path
    if not path.exists() or not path.is_file():
        return None
    return sha256_bytes(path.read_bytes())


def has_location_or_status(fact: dict[str, Any]) -> bool:
    location = fact.get("sourceLocation")
    if isinstance(location, dict):
        required = {"lineStart", "lineEnd", "columnStart", "columnEnd"}
        return required.issubset(location)
    return isinstance(fact.get("sourceLocationStatus"), str)


def validate(data: dict[str, Any], source_root: Path | None = None) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if data.get("artifactRole") != EXPECTED_ROLE:
        errors.append(f"wrong artifactRole: {data.get('artifactRole')}")
    if data.get("status") != EXPECTED_STATUS:
        errors.append(f"wrong status: {data.get('status')}")
    if data.get("scope") != EXPECTED_SCOPE:
        errors.append(f"wrong scope: {data.get('scope')}")
    if data.get("benchmarkId") != BENCHMARK_ID:
        errors.append(f"wrong benchmarkId: {data.get('benchmarkId')}")

    extractor = data.get("extractor")
    if not isinstance(extractor, dict):
        errors.append("missing extractor object")
    else:
        if extractor.get("deterministic") is not True:
            errors.append("extractor.deterministic must be true")
        if extractor.get("broadExtractor") is not False:
            errors.append("extractor.broadExtractor must be false")
        if not isinstance(extractor.get("id"), str) or not extractor.get("id"):
            errors.append("extractor.id must be present")
        if not isinstance(extractor.get("version"), str) or not extractor.get("version"):
            errors.append("extractor.version must be present")

    facts = data.get("facts")
    relations = data.get("relations")
    if not isinstance(facts, list) or not facts:
        errors.append("facts must be a non-empty array")
        facts = []
    if not isinstance(relations, list):
        errors.append("relations must be an array")
        relations = []

    fact_ids: set[str] = set()
    endpoint_ids: set[str] = set()
    source_files: set[str] = set()

    for fact in facts:
        if not isinstance(fact, dict):
            errors.append("every fact must be an object")
            continue
        fact_id = fact.get("id")
        if not isinstance(fact_id, str) or not fact_id:
            errors.append("fact missing string id")
            continue
        if fact_id in fact_ids:
            errors.append(f"duplicate fact id: {fact_id}")
        fact_ids.add(fact_id)
        missing = sorted(field for field in REQUIRED_FACT_FIELDS if field not in fact)
        if missing:
            errors.append(f"{fact_id} missing required fields: {', '.join(missing)}")
        kind = fact.get("kind")
        if kind not in ALLOWED_FACT_KINDS:
            errors.append(f"{fact_id} unknown fact kind: {kind}")
        if kind in ENDPOINT_FACT_KINDS:
            endpoint_ids.add(fact_id)
        if fact.get("confidence") not in ALLOWED_CONFIDENCE:
            errors.append(f"{fact_id} invalid confidence: {fact.get('confidence')}")
        if not has_location_or_status(fact):
            errors.append(f"{fact_id} missing sourceLocation or sourceLocationStatus")
        source_file = fact.get("sourceFile")
        if isinstance(source_file, str) and source_file:
            source_files.add(source_file)
            if source_root is not None:
                digest = source_digest(source_root, source_file)
                if digest is None:
                    errors.append(f"{fact_id} source file missing: {source_file}")
                elif fact.get("sourceDigest") != digest:
                    errors.append(f"{fact_id} stale sourceDigest for {source_file}")
        else:
            errors.append(f"{fact_id} missing sourceFile")
        if isinstance(fact.get("sourceText"), str):
            errors.append(f"{fact_id} must not contain sourceText")

    relation_ids: set[str] = set()
    for relation in relations:
        if not isinstance(relation, dict):
            errors.append("every relation must be an object")
            continue
        relation_id = relation.get("id")
        if not isinstance(relation_id, str) or not relation_id:
            errors.append("relation missing string id")
            continue
        if relation_id in relation_ids:
            errors.append(f"duplicate relation id: {relation_id}")
        relation_ids.add(relation_id)
        if relation.get("kind") not in ALLOWED_RELATION_KINDS:
            errors.append(f"{relation_id} unknown relation kind: {relation.get('kind')}")
        source = relation.get("from")
        target = relation.get("to")
        if source not in endpoint_ids:
            errors.append(f"{relation_id} missing source endpoint: {source}")
        if target not in endpoint_ids:
            errors.append(f"{relation_id} missing target endpoint: {target}")

    required_kinds = {"file", "module", "function", "type", "route", "test", "import", "call"}
    observed_kinds = {fact.get("kind") for fact in facts if isinstance(fact, dict)}
    for required in sorted(required_kinds - observed_kinds):
        errors.append(f"missing required fact kind: {required}")

    required_relations = {"contains", "imports", "references", "calls", "handles_route", "tests"}
    observed_relations = {relation.get("kind") for relation in relations if isinstance(relation, dict)}
    for required in sorted(required_relations - observed_relations):
        errors.append(f"missing required relation kind: {required}")

    source_digest_count = len(data.get("sourceDigests", {})) if isinstance(data.get("sourceDigests"), dict) else 0
    if source_digest_count != len(source_files):
        warnings.append("sourceDigests count does not match distinct sourceFile count")

    return {
        "artifactRole": "intentgraph-code-facts-validation-report",
        "status": "intentgraph-code-facts-validation-passed" if not errors else "intentgraph-code-facts-validation-failed",
        "scope": "b1-typescript-rest-api-code-facts-validation",
        "reportVersion": REPORT_VERSION,
        "benchmarkId": BENCHMARK_ID,
        "result": "pass" if not errors else "fail",
        "summary": {
            "factCount": len(facts),
            "relationCount": len(relations),
            "sourceFileCount": len(source_files),
            "endpointFactCount": len(endpoint_ids),
            "errorCount": len(errors),
            "warningCount": len(warnings),
        },
        "factKindCounts": count_by_key(facts, "kind"),
        "relationKindCounts": count_by_key(relations, "kind"),
        "errors": errors,
        "warnings": warnings,
        "claimScope": {
            "b1FixtureBounded": True,
            "broadExtractorClaimed": False,
            "sourceTextAuthorityClaimed": False,
            "aiAuthorityClaimed": False,
            "workbenchClaimed": False,
        },
    }


def count_by_key(items: list[Any], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        if isinstance(item, dict) and isinstance(item.get(key), str):
            counts[item[key]] = counts.get(item[key], 0) + 1
    return dict(sorted(counts.items()))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate B1 code facts.")
    parser.add_argument("--code-facts", required=True, type=Path)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = validate(read_json(args.code_facts), args.source_root)
        write_json(args.out, report)
    except (OSError, ValidationError, json.JSONDecodeError) as error:
        print(f"validate B1 code facts failed: {error}")
        return 1
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
