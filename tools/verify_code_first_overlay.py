"""Verify the CF0 code-first IntentGraph overlay against extracted code facts."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REPORT_VERSION = "0.1.0"


class OverlayVerifyError(Exception):
    """Raised when the CF0 overlay inputs are malformed."""


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise OverlayVerifyError(f"{path} must contain a JSON object")
    return data


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def fact_index(code_facts: dict[str, Any]) -> dict[str, dict[str, Any]]:
    facts = code_facts.get("facts")
    if not isinstance(facts, list):
        raise OverlayVerifyError("code facts must contain a facts array")
    index: dict[str, dict[str, Any]] = {}
    for fact in facts:
        if not isinstance(fact, dict) or not isinstance(fact.get("id"), str):
            raise OverlayVerifyError("every code fact must be an object with string id")
        if fact["id"] in index:
            raise OverlayVerifyError(f"duplicate code fact id: {fact['id']}")
        index[fact["id"]] = fact
    return index


def id_index(items: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for item in items:
        item_id = item.get("id")
        if not isinstance(item_id, str):
            raise OverlayVerifyError(f"{label} item missing string id")
        index[item_id] = item
    return index


def verify_units(overlay: dict[str, Any], facts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    errors: list[str] = []
    units = overlay.get("intentUnits")
    if not isinstance(units, list) or not units:
        raise OverlayVerifyError("overlay requires non-empty intentUnits")
    evidence_ids = set(id_index(overlay.get("evidence", []), "evidence"))
    authority_ids = set(id_index(overlay.get("authority", []), "authority"))
    verification_ids = set(id_index(overlay.get("verification", []), "verification"))
    unit_reports: list[dict[str, Any]] = []
    for unit in units:
        unit_id = unit.get("id", "<missing>")
        unit_errors: list[str] = []
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
        code_ref_ids = {ref.get("id") for ref in code_refs if isinstance(ref, dict)}
        code_fact_ref_ids = {ref.get("id") for ref in code_fact_refs if isinstance(ref, dict)}
        for ref in code_refs:
            fact_id = ref.get("factId")
            if ref.get("ownership") != "reference-only":
                unit_errors.append(f"codeRef {ref.get('id')} is not reference-only")
            if fact_id not in facts:
                unit_errors.append(f"codeRef {ref.get('id')} references missing fact {fact_id}")
        for ref in code_fact_refs:
            fact_id = ref.get("factId")
            expected_kind = ref.get("expectedFactKind")
            fact = facts.get(fact_id)
            if not fact:
                unit_errors.append(f"codeFactRef {ref.get('id')} references missing fact {fact_id}")
            elif expected_kind and fact.get("kind") != expected_kind:
                unit_errors.append(f"codeFactRef {ref.get('id')} expected {expected_kind} got {fact.get('kind')}")
        for obligation in obligations:
            obligation_id = obligation.get("id", "<missing>")
            if obligation.get("sourceTextEqualityRequired") is not False:
                unit_errors.append(f"{obligation_id} must not require source text equality")
            for ref_id in obligation.get("codeRefIds", []):
                if ref_id not in code_ref_ids:
                    unit_errors.append(f"{obligation_id} missing codeRef {ref_id}")
            for ref_id in obligation.get("codeFactRefIds", []):
                if ref_id not in code_fact_ref_ids:
                    unit_errors.append(f"{obligation_id} missing codeFactRef {ref_id}")
            for evidence_id in obligation.get("evidenceIds", []):
                if evidence_id not in evidence_ids:
                    unit_errors.append(f"{obligation_id} missing evidence {evidence_id}")
            for authority_id in obligation.get("authorityIds", []):
                if authority_id not in authority_ids:
                    unit_errors.append(f"{obligation_id} missing authority {authority_id}")
            for verification_id in obligation.get("verificationIds", []):
                if verification_id not in verification_ids:
                    unit_errors.append(f"{obligation_id} missing verification {verification_id}")
        admission = unit.get("admission", {})
        if admission.get("codeTextContained") is not False:
            unit_errors.append("unit must declare codeTextContained false")
        errors.extend(f"{unit_id}: {error}" for error in unit_errors)
        unit_reports.append(
            {
                "unitId": unit_id,
                "result": "pass" if not unit_errors else "fail",
                "codeRefCount": len(code_refs),
                "codeFactRefCount": len(code_fact_refs),
                "mappingObligationCount": len(obligations),
                "errors": unit_errors,
            }
        )
    return {
        "result": "pass" if not errors else "fail",
        "unitCount": len(units),
        "mappingObligationCount": sum(item["mappingObligationCount"] for item in unit_reports),
        "units": unit_reports,
        "errors": errors,
    }


def run_behavior_smokes(overlay: dict[str, Any], source_root: Path) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for check in overlay.get("verification", []):
        if check.get("kind") != "behavior-smoke":
            continue
        command = check.get("command")
        if not isinstance(command, list) or not all(isinstance(part, str) for part in command):
            results.append({"id": check.get("id"), "result": "fail", "error": "invalid command"})
            continue
        run_command = [sys.executable if part == "python" else part for part in command]
        completed = subprocess.run(run_command, cwd=source_root, text=True, capture_output=True, check=False)
        passed = (
            completed.returncode == int(check.get("expectedExitCode"))
            and completed.stdout == check.get("expectedStdout")
        )
        results.append(
            {
                "id": check.get("id"),
                "result": "pass" if passed else "fail",
                "command": command,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "exitCode": completed.returncode,
                "expectedStdout": check.get("expectedStdout"),
                "expectedExitCode": check.get("expectedExitCode"),
            }
        )
    return {
        "result": "pass" if results and all(item["result"] == "pass" for item in results) else "fail",
        "checks": results,
    }


def verify(overlay_path: Path, code_facts_path: Path, source_root: Path) -> dict[str, Any]:
    overlay = read_json(overlay_path)
    code_facts = read_json(code_facts_path)
    facts = fact_index(code_facts)
    if overlay.get("developmentStateModel", {}).get("hiddenGeneratedCodeSnapshotUsed") is not False:
        raise OverlayVerifyError("CF0 must not use hidden generated-code snapshots")
    mapping = verify_units(overlay, facts)
    behavior = run_behavior_smokes(overlay, source_root)
    evidence_present = len(overlay.get("evidence", [])) > 0
    authority_present = len(overlay.get("authority", [])) > 0
    history_present = len(overlay.get("history", [])) > 0
    result = (
        mapping["result"] == "pass"
        and behavior["result"] == "pass"
        and evidence_present
        and authority_present
        and history_present
    )
    return {
        "reportVersion": REPORT_VERSION,
        "benchmarkId": overlay.get("benchmarkId"),
        "mode": "code-first-maintenance-overlay",
        "result": "pass" if result else "fail",
        "sourceTextEqualityRequired": False,
        "hiddenGeneratedCodeSnapshotUsed": False,
        "inputs": {
            "overlay": overlay_path.as_posix(),
            "codeFacts": code_facts_path.as_posix(),
            "sourceRoot": source_root.as_posix(),
        },
        "codeFacts": {
            "sourceRole": code_facts.get("source", {}).get("role"),
            "sourceDigest": code_facts.get("source", {}).get("sha256"),
            "factCount": len(facts),
            "deterministic": code_facts.get("extractor", {}).get("deterministic"),
            "externalExtractor": code_facts.get("extractor", {}).get("externalExtractor"),
        },
        "mappingVerification": mapping,
        "behaviorVerification": behavior,
        "semanticBoundaries": {
            "evidencePresent": evidence_present,
            "authorityPresent": authority_present,
            "historyPresent": history_present,
            "aiAuthority": False,
        },
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify the CF0 code-first overlay.")
    parser.add_argument("--overlay", required=True, type=Path)
    parser.add_argument("--code-facts", required=True, type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = verify(args.overlay, args.code_facts, args.source_root)
        write_json(args.out, report)
    except (OSError, json.JSONDecodeError, OverlayVerifyError) as error:
        print(f"verify code-first overlay failed: {error}")
        return 1
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
