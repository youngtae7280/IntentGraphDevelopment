"""Validate WindowsUtility non-applied proposal artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


REPORT_VERSION = "0.1.0"


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def digest_json(data: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def run_git(target_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(target_root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def require_false(data: dict[str, Any], keys: list[str], errors: list[str], prefix: str) -> None:
    for key in keys:
        if data.get(key) is not False:
            errors.append(f"{prefix}.{key} must be false")


def validate(
    proposal: dict[str, Any],
    mapping: dict[str, Any],
    mapping_verification: dict[str, Any],
    target_root: Path,
) -> dict[str, Any]:
    errors: list[str] = []

    if proposal.get("artifactRole") != "intentgraph-windowsutility-non-applied-proposal":
        errors.append("wrong proposal artifactRole")
    if proposal.get("status") != "intentgraph-windowsutility-non-applied-proposal-proposed":
        errors.append("wrong proposal status")
    if proposal.get("scope") != "p8.12-shell-workspace-smoke-evidence-non-applied-proposal":
        errors.append("wrong proposal scope")
    if proposal.get("proposalMode") != "non-applied-evidence-plan":
        errors.append("proposalMode must be non-applied-evidence-plan")
    if proposal.get("applicationStatus") != "not-applied":
        errors.append("applicationStatus must be not-applied")

    if mapping.get("artifactRole") != "intentgraph-windowsutility-accepted-mapping":
        errors.append("wrong accepted mapping artifactRole")
    if mapping.get("status") != "intentgraph-windowsutility-accepted-mapping-recorded":
        errors.append("wrong accepted mapping status")
    if mapping_verification.get("artifactRole") != "intentgraph-windowsutility-accepted-mapping-verification-report":
        errors.append("wrong accepted mapping verification artifactRole")
    if mapping_verification.get("result") != "pass":
        errors.append("accepted mapping verification must pass")

    binding = proposal.get("acceptedMappingBinding", {})
    accepted = mapping.get("acceptedMapping", {})
    target = mapping.get("target", {})

    if binding.get("digest") != digest_json(mapping):
        errors.append("accepted mapping digest mismatch")
    if binding.get("verificationReportDigest") != digest_json(mapping_verification):
        errors.append("accepted mapping verification digest mismatch")
    if binding.get("mappingId") != accepted.get("id"):
        errors.append("accepted mapping id mismatch")
    if binding.get("intentUnitId") != accepted.get("intentUnitId"):
        errors.append("accepted mapping intent unit mismatch")
    if binding.get("accepted") is not True or accepted.get("accepted") is not True:
        errors.append("accepted mapping must be accepted")

    baseline = proposal.get("targetBaseline", {})
    if baseline.get("head") != target.get("head") or baseline.get("originMain") != target.get("originMain"):
        errors.append("target baseline must match accepted mapping target")
    if baseline.get("head") != baseline.get("originMain"):
        errors.append("target baseline head must equal originMain")
    if baseline.get("status") != "clean-aligned":
        errors.append("target baseline status must be clean-aligned")
    if baseline.get("targetWritesAuthorized") is not False:
        errors.append("target baseline must not authorize writes")

    try:
        actual_head = run_git(target_root, "rev-parse", "HEAD")
        actual_origin = run_git(target_root, "rev-parse", "origin/main")
        actual_status = run_git(target_root, "status", "--short", "--branch")
    except (OSError, subprocess.CalledProcessError) as error:
        errors.append(f"failed to inspect target git state: {error}")
        actual_head = ""
        actual_origin = ""
        actual_status = ""

    if actual_head and actual_head != baseline.get("head"):
        errors.append("target HEAD does not match proposal baseline")
    if actual_origin and actual_origin != baseline.get("originMain"):
        errors.append("target origin/main does not match proposal baseline")
    if actual_status and actual_status != "## main...origin/main":
        errors.append("target status must stay clean/aligned")

    impact = proposal.get("impactScope", {})
    if impact.get("mappingIds") != [accepted.get("id")]:
        errors.append("impactScope.mappingIds must contain the accepted mapping id")
    if impact.get("intentUnitIds") != [accepted.get("intentUnitId")]:
        errors.append("impactScope.intentUnitIds must contain the accepted intent unit id")

    ref_errors = []
    proposal_refs = impact.get("codeSurfaceRefs", [])
    mapping_refs = accepted.get("codeSurfaceRefs", [])
    if proposal_refs != [
        {"path": ref.get("path"), "digest": ref.get("digest"), "byteLength": ref.get("byteLength")}
        for ref in mapping_refs
    ]:
        errors.append("impactScope.codeSurfaceRefs must match accepted mapping refs")
    for ref in proposal_refs:
        rel = ref.get("path")
        if not isinstance(rel, str) or Path(rel).is_absolute():
            ref_errors.append(f"invalid source ref {rel!r}")
            continue
        path = target_root / rel
        if not path.exists():
            ref_errors.append(f"source ref missing: {rel}")
            continue
        if sha256_file(path) != ref.get("digest"):
            ref_errors.append(f"source ref digest mismatch: {rel}")
        if path.stat().st_size != ref.get("byteLength"):
            ref_errors.append(f"source ref byte length mismatch: {rel}")
    errors.extend(ref_errors)

    code_delta = proposal.get("proposedCodeDelta", {})
    if code_delta.get("sourcePatchExpected") is not False:
        errors.append("proposedCodeDelta.sourcePatchExpected must be false")
    if code_delta.get("plannedSourceChanges") != []:
        errors.append("proposedCodeDelta.plannedSourceChanges must be empty")
    require_false(
        code_delta,
        ["sourceTextIncluded", "patchIncluded", "diffIncluded", "replacementTextIncluded", "sourceMutated"],
        errors,
        "proposedCodeDelta",
    )

    evidence = proposal.get("requiredEvidence", [])
    authority = proposal.get("requiredAuthority", [])
    stops = proposal.get("rollbackStopConditions", [])
    plan = proposal.get("deterministicVerificationPlan", [])
    if not isinstance(evidence, list):
        errors.append("requiredEvidence must be a list")
        evidence = []
    elif len(evidence) < 4:
        errors.append("requiredEvidence must include at least four evidence requirements")
    if not isinstance(authority, list) or len(authority) < 2:
        errors.append("requiredAuthority must include at least two authority requirements")
        authority = []
    if not isinstance(stops, list) or not stops:
        errors.append("rollbackStopConditions must be non-empty")
        stops = []
    if not isinstance(plan, list) or len(plan) < 2:
        errors.append("deterministicVerificationPlan must include at least two steps")
        plan = []

    evidence_ids = {item.get("id") for item in evidence if isinstance(item, dict)}
    for required_id in [
        "evidence.requirement.p8.12-accepted-mapping-verification",
        "evidence.requirement.p8.12-source-digest-recheck",
        "evidence.requirement.p8.12-shell-navigation-smoke",
        "evidence.requirement.p8.12-shell-workspace-screenshot",
    ]:
        if required_id not in evidence_ids:
            errors.append(f"missing required evidence {required_id}")
    for item in evidence:
        if not isinstance(item, dict):
            errors.append("requiredEvidence items must be objects")
            continue
        if item.get("requiredBeforeAcceptance") is not True:
            errors.append(f"evidence {item.get('id')} must be required before acceptance")

    for item in authority:
        if not isinstance(item, dict):
            errors.append("requiredAuthority items must be objects")
            continue
        if item.get("requiredBeforeAcceptance") is not True:
            errors.append(f"authority {item.get('id')} must be required before acceptance")
        if item.get("aiAuthority") is not False:
            errors.append(f"authority {item.get('id')} must not grant AI authority")
        if item.get("selfAuthorized") is not False:
            errors.append(f"authority {item.get('id')} must not be self-authorized")
        if item.get("targetWritesAuthorized") is not False:
            errors.append(f"authority {item.get('id')} must not authorize target writes")

    for step in plan:
        if not isinstance(step, dict):
            errors.append("deterministicVerificationPlan items must be objects")
            continue
        if step.get("mutatesTarget") is not False:
            errors.append(f"verification step {step.get('id')} must not mutate target")

    authorizations = proposal.get("authorizations", {})
    require_false(
        authorizations,
        [
            "sourceEditsAuthorized",
            "proposalApplicationAuthorized",
            "targetWritesAuthorized",
            "aiAuthorityPromoted",
            "productizationAuthorized",
            "hardwareActionsAuthorized",
        ],
        errors,
        "authorizations",
    )

    claim_scope = proposal.get("claimScope", {})
    if claim_scope.get("proposalOnly") is not True:
        errors.append("claimScope.proposalOnly must be true")
    require_false(
        claim_scope,
        [
            "sourceMutated",
            "patchApplied",
            "automaticAcceptanceClaimed",
            "aiAuthorityGranted",
            "selfAuthorized",
            "productizationClaimed",
            "hardwareActionClaimed",
        ],
        errors,
        "claimScope",
    )

    return {
        "artifactRole": "intentgraph-windowsutility-non-applied-proposal-validation-report",
        "status": "intentgraph-windowsutility-non-applied-proposal-validation-passed" if not errors else "intentgraph-windowsutility-non-applied-proposal-validation-failed",
        "scope": "p8.12-shell-workspace-smoke-evidence-non-applied-proposal-validation-report",
        "reportVersion": REPORT_VERSION,
        "proposalId": proposal.get("proposalId"),
        "result": "pass" if not errors else "fail",
        "summary": {
            "requiredEvidenceCount": len(evidence),
            "requiredAuthorityCount": len(authority),
            "rollbackStopConditionCount": len(stops),
            "verificationStepCount": len(plan),
            "codeSurfaceRefCount": len(proposal_refs),
            "plannedSourceChangeCount": len(code_delta.get("plannedSourceChanges", [])) if isinstance(code_delta, dict) else 0,
            "errorCount": len(errors),
        },
        "baseline": {
            "acceptedMappingDigestMatched": binding.get("digest") == digest_json(mapping),
            "acceptedMappingVerificationDigestMatched": binding.get("verificationReportDigest") == digest_json(mapping_verification),
            "targetHeadMatched": actual_head == baseline.get("head") if actual_head else False,
            "targetOriginMainMatched": actual_origin == baseline.get("originMain") if actual_origin else False,
            "targetStatus": actual_status,
        },
        "claimScope": {
            "proposalOnly": True,
            "sourceMutated": False,
            "patchApplied": False,
            "targetWritesAuthorized": False,
            "aiAuthorityGranted": False,
            "selfAuthorized": False,
            "productizationClaimed": False,
            "hardwareActionClaimed": False,
        },
        "errors": errors,
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a WindowsUtility non-applied proposal.")
    parser.add_argument("--proposal", required=True, type=Path)
    parser.add_argument("--accepted-mapping", required=True, type=Path)
    parser.add_argument("--accepted-mapping-verification", required=True, type=Path)
    parser.add_argument("--target-root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    try:
        report = validate(
            read_json(args.proposal),
            read_json(args.accepted_mapping),
            read_json(args.accepted_mapping_verification),
            args.target_root,
        )
        write_json(args.out, report)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"validate WindowsUtility non-applied proposal failed: {error}")
        return 1
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
