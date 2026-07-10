"""Emit and validate a non-mutating WindowsUtility source application dry run."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


REPORT_VERSION = "0.1.0"
WORK_ITEM = "P8.41 Non-Mutating Source Application Dry-Run Prototype"
SCOPE = "p8.41-non-mutating-source-application-dry-run-prototype"
DATE = "2026-07-10"

REQUEST_FILE = "dry-run-request.json"
CHANGE_SET_FILE = "change-set-preview.json"
TOUCHED_FILE_FILE = "touched-file-expectation-report.json"
EVIDENCE_PLAN_FILE = "evidence-plan.json"
ROLLBACK_PLAN_FILE = "rollback-plan.json"
AUTHORITY_REPORT_FILE = "authority-requirement-report.json"
VALIDATION_REPORT_FILE = "validation-report.json"

FALSE_AUTHORIZATION_KEYS = [
    "sourceEditsAuthorized",
    "proposalApplicationAuthorized",
    "targetWritesAuthorized",
    "windowsUtilityGeneratedWritesAuthorized",
    "gitIndexMutationAuthorized",
    "windowsUtilityCommitAuthorized",
    "windowsUtilityPushAuthorized",
    "aiAuthorityPromoted",
    "hardwareActionsAuthorized",
    "packagingAuthorized",
    "releaseAuthorized",
    "productizationAuthorized",
]


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


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def run_git(target_root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(target_root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def empty_authorizations() -> dict[str, bool]:
    return {key: False for key in FALSE_AUTHORIZATION_KEYS}


def require_false_map(data: dict[str, Any], prefix: str, errors: list[str]) -> None:
    for key in FALSE_AUTHORIZATION_KEYS:
        if data.get(key) is not False:
            errors.append(f"{prefix}.{key} must be false")


def collect_target_state(target_root: Path) -> dict[str, Any]:
    head = run_git(target_root, "rev-parse", "HEAD")
    origin = run_git(target_root, "rev-parse", "origin/main")
    status = run_git(target_root, "status", "--short", "--branch")
    return {
        "path": str(target_root),
        "head": head,
        "originMain": origin,
        "gitStatus": status,
        "cleanAligned": head == origin and status == "## main...origin/main",
        "sourceModificationPermissionObserved": False,
    }


def source_inputs(
    repo_root: Path,
    boundary_report_path: Path,
    accepted_mapping_path: Path,
    proposal_path: Path,
    target_root: Path,
    boundary: dict[str, Any],
    mapping: dict[str, Any],
    proposal: dict[str, Any],
) -> dict[str, Any]:
    return {
        "boundaryReport": {
            "path": rel(boundary_report_path, repo_root),
            "digest": digest_json(boundary),
            "artifactRole": boundary.get("artifactRole"),
            "status": boundary.get("status"),
        },
        "acceptedMapping": {
            "path": rel(accepted_mapping_path, repo_root),
            "digest": digest_json(mapping),
            "artifactRole": mapping.get("artifactRole"),
            "status": mapping.get("status"),
            "mappingId": mapping.get("acceptedMapping", {}).get("id"),
        },
        "nonAppliedProposal": {
            "path": rel(proposal_path, repo_root),
            "digest": digest_json(proposal),
            "artifactRole": proposal.get("artifactRole"),
            "status": proposal.get("status"),
            "proposalId": proposal.get("proposalId"),
            "applicationStatus": proposal.get("applicationStatus"),
        },
        "targetRoot": str(target_root),
    }


def build_touched_file_results(proposal: dict[str, Any], target_root: Path) -> list[dict[str, Any]]:
    refs = proposal.get("impactScope", {}).get("codeSurfaceRefs", [])
    results = []
    for ref in refs if isinstance(refs, list) else []:
        if not isinstance(ref, dict):
            continue
        path_value = ref.get("path")
        if not isinstance(path_value, str) or Path(path_value).is_absolute():
            results.append(
                {
                    "path": path_value,
                    "result": "invalid-ref",
                    "exists": False,
                    "digestMatched": False,
                    "byteLengthMatched": False,
                }
            )
            continue
        source_path = target_root / path_value
        exists = source_path.exists()
        actual_digest = sha256_file(source_path) if exists else None
        actual_length = source_path.stat().st_size if exists else None
        results.append(
            {
                "path": path_value,
                "expectedDigest": ref.get("digest"),
                "actualDigest": actual_digest,
                "expectedByteLength": ref.get("byteLength"),
                "actualByteLength": actual_length,
                "exists": exists,
                "digestMatched": exists and actual_digest == ref.get("digest"),
                "byteLengthMatched": exists and actual_length == ref.get("byteLength"),
                "writeExpected": False,
                "readOnlyDigestRecheck": True,
            }
        )
    return results


def build_artifacts(
    repo_root: Path,
    target_root: Path,
    boundary_report_path: Path,
    accepted_mapping_path: Path,
    proposal_path: Path,
    source_modification_permission_observed: bool,
) -> dict[str, dict[str, Any]]:
    boundary = read_json(boundary_report_path)
    mapping = read_json(accepted_mapping_path)
    proposal = read_json(proposal_path)
    target_state = collect_target_state(target_root)
    target_state["sourceModificationPermissionObserved"] = source_modification_permission_observed
    inputs = source_inputs(
        repo_root,
        boundary_report_path,
        accepted_mapping_path,
        proposal_path,
        target_root,
        boundary,
        mapping,
        proposal,
    )
    proposal_delta = proposal.get("proposedCodeDelta", {})
    touched_results = build_touched_file_results(proposal, target_root)
    touched_refs = [
        {
            "path": item.get("path"),
            "expectedDigest": item.get("expectedDigest"),
            "expectedByteLength": item.get("expectedByteLength"),
            "writeExpected": False,
            "readOnlyDigestRecheck": True,
        }
        for item in touched_results
    ]

    request = {
        "artifactRole": "intentgraph-windowsutility-source-application-dry-run-request",
        "status": "intentgraph-windowsutility-source-application-dry-run-request-recorded",
        "scope": SCOPE,
        "workItem": WORK_ITEM,
        "date": DATE,
        "reportVersion": REPORT_VERSION,
        "mode": "non-mutating-source-application-dry-run",
        "dryRunPurpose": "Create a deterministic source-application rehearsal record before any WindowsUtility source write is performed.",
        "sourceInputs": inputs,
        "targetBaseline": target_state,
        "permissionContext": {
            "sourceModificationPermissionObserved": source_modification_permission_observed,
            "permissionExercisedInThisSlice": False,
            "reason": "P8.41 remains a non-mutating dry-run prototype even when a later source-application slice may be authorized.",
        },
        "authorizations": empty_authorizations(),
        "claimScope": {
            "dryRunOnly": True,
            "sourceMutated": False,
            "targetMutated": False,
            "proposalApplied": False,
            "sourcePatchGenerated": False,
            "sourcePatchApplied": False,
            "windowsUtilityCommitCreated": False,
            "windowsUtilityPushPerformed": False,
            "hardwareActionClaimed": False,
            "packagingClaimed": False,
            "releaseClaimed": False,
            "productizationClaimed": False,
        },
    }

    change_set = {
        "artifactRole": "intentgraph-windowsutility-source-change-set-preview",
        "status": "intentgraph-windowsutility-source-change-set-preview-recorded",
        "scope": SCOPE,
        "workItem": WORK_ITEM,
        "date": DATE,
        "patchApplicationMode": "non-mutating-preview-only",
        "proposalId": proposal.get("proposalId"),
        "applicationStatus": "not-applied",
        "sourcePatchExpected": proposal_delta.get("sourcePatchExpected", False),
        "sourcePatchGenerated": False,
        "sourcePatchApplied": False,
        "operationCount": 0,
        "operations": [],
        "plannedSourceChanges": proposal_delta.get("plannedSourceChanges", []),
        "intendedTouchedFiles": touched_refs,
        "reason": "The bound proposal requests smoke evidence and does not include a source patch.",
        "authorizations": empty_authorizations(),
    }

    touched = {
        "artifactRole": "intentgraph-windowsutility-touched-file-expectation-report",
        "status": "intentgraph-windowsutility-touched-file-expectation-passed"
        if touched_results and all(item["digestMatched"] and item["byteLengthMatched"] for item in touched_results)
        else "intentgraph-windowsutility-touched-file-expectation-failed",
        "scope": SCOPE,
        "workItem": WORK_ITEM,
        "date": DATE,
        "targetRoot": str(target_root),
        "fileCount": len(touched_results),
        "writeExpectedFileCount": 0,
        "digestMatchedCount": sum(1 for item in touched_results if item["digestMatched"]),
        "byteLengthMatchedCount": sum(1 for item in touched_results if item["byteLengthMatched"]),
        "results": touched_results,
        "authorizations": empty_authorizations(),
    }

    required_evidence = proposal.get("requiredEvidence", [])
    evidence = {
        "artifactRole": "intentgraph-windowsutility-source-application-evidence-plan",
        "status": "intentgraph-windowsutility-source-application-evidence-plan-recorded",
        "scope": SCOPE,
        "workItem": WORK_ITEM,
        "date": DATE,
        "proposalId": proposal.get("proposalId"),
        "requiredEvidence": required_evidence if isinstance(required_evidence, list) else [],
        "preApplicationEvidence": [
            item
            for item in required_evidence
            if isinstance(item, dict) and item.get("requiredBeforeAcceptance") is True
        ]
        if isinstance(required_evidence, list)
        else [],
        "postApplicationEvidence": [],
        "dryRunCollectedEvidence": [
            {
                "id": "evidence.p8.41-source-digest-recheck",
                "kind": "source-ref-digest-recheck",
                "status": "collected-in-dry-run",
                "report": TOUCHED_FILE_FILE,
                "targetWrites": False,
            }
        ],
        "hardwareRequired": False,
        "authorizations": empty_authorizations(),
    }

    rollback = {
        "artifactRole": "intentgraph-windowsutility-source-application-rollback-plan",
        "status": "intentgraph-windowsutility-source-application-rollback-plan-recorded",
        "scope": SCOPE,
        "workItem": WORK_ITEM,
        "date": DATE,
        "sourceMutationPerformed": False,
        "rollbackActionRequiredForThisDryRun": False,
        "futureRollbackRequirements": [
            {
                "id": "rollback.future.clean-target-baseline",
                "requirement": "Capture clean HEAD/origin/main/status before any future source write.",
            },
            {
                "id": "rollback.future.patch-preview",
                "requirement": "Record exact touched files and patch preview before applying any future source write.",
            },
            {
                "id": "rollback.future-stop-on-dirty-target",
                "requirement": "Stop instead of applying if the WindowsUtility target is dirty or stale.",
            },
        ],
        "stopConditions": proposal.get("rollbackStopConditions", []),
        "authorizations": empty_authorizations(),
    }

    authority = {
        "artifactRole": "intentgraph-windowsutility-source-application-authority-requirement-report",
        "status": "intentgraph-windowsutility-source-application-authority-requirements-recorded",
        "scope": SCOPE,
        "workItem": WORK_ITEM,
        "date": DATE,
        "permissionContext": request["permissionContext"],
        "requiredAuthority": proposal.get("requiredAuthority", []),
        "dryRunAuthority": {
            "nonMutatingDryRunRecorded": True,
            "sourceApplicationAuthorized": False,
            "proposalApplicationAuthorized": False,
            "targetWritesAuthorized": False,
            "aiSelfAuthorizationAllowed": False,
            "hardwareActionsAuthorized": False,
            "packagingAuthorized": False,
            "releaseAuthorized": False,
        },
        "nextGate": {
            "id": "gate.p8.42-source-application-authorization-review",
            "requiredBeforeSourceWrite": True,
            "reason": "A source-modifying slice must use this dry-run plus explicit coordinator/user authority before editing WindowsUtility.",
        },
        "authorizations": empty_authorizations(),
    }

    return {
        REQUEST_FILE: request,
        CHANGE_SET_FILE: change_set,
        TOUCHED_FILE_FILE: touched,
        EVIDENCE_PLAN_FILE: evidence,
        ROLLBACK_PLAN_FILE: rollback,
        AUTHORITY_REPORT_FILE: authority,
    }


def load_dry_run_artifacts(out_dir: Path) -> tuple[dict[str, dict[str, Any]], list[str]]:
    errors: list[str] = []
    artifacts: dict[str, dict[str, Any]] = {}
    for filename in [
        REQUEST_FILE,
        CHANGE_SET_FILE,
        TOUCHED_FILE_FILE,
        EVIDENCE_PLAN_FILE,
        ROLLBACK_PLAN_FILE,
        AUTHORITY_REPORT_FILE,
    ]:
        path = out_dir / filename
        if not path.exists():
            errors.append(f"missing artifact {filename}")
            continue
        try:
            artifacts[filename] = read_json(path)
        except (OSError, json.JSONDecodeError, ValueError) as error:
            errors.append(f"failed to read {filename}: {error}")
    return artifacts, errors


def validate_dry_run_dir(out_dir: Path, target_root: Path | None = None) -> dict[str, Any]:
    artifacts, errors = load_dry_run_artifacts(out_dir)
    request = artifacts.get(REQUEST_FILE, {})
    change_set = artifacts.get(CHANGE_SET_FILE, {})
    touched = artifacts.get(TOUCHED_FILE_FILE, {})
    evidence = artifacts.get(EVIDENCE_PLAN_FILE, {})
    rollback = artifacts.get(ROLLBACK_PLAN_FILE, {})
    authority = artifacts.get(AUTHORITY_REPORT_FILE, {})

    expected_roles = {
        REQUEST_FILE: "intentgraph-windowsutility-source-application-dry-run-request",
        CHANGE_SET_FILE: "intentgraph-windowsutility-source-change-set-preview",
        TOUCHED_FILE_FILE: "intentgraph-windowsutility-touched-file-expectation-report",
        EVIDENCE_PLAN_FILE: "intentgraph-windowsutility-source-application-evidence-plan",
        ROLLBACK_PLAN_FILE: "intentgraph-windowsutility-source-application-rollback-plan",
        AUTHORITY_REPORT_FILE: "intentgraph-windowsutility-source-application-authority-requirement-report",
    }
    for filename, role in expected_roles.items():
        artifact = artifacts.get(filename)
        if not artifact:
            continue
        if artifact.get("artifactRole") != role:
            errors.append(f"{filename} has wrong artifactRole")
        if artifact.get("scope") != SCOPE:
            errors.append(f"{filename} has wrong scope")
        require_false_map(artifact.get("authorizations", {}) if isinstance(artifact.get("authorizations"), dict) else {}, f"{filename}.authorizations", errors)

    baseline = request.get("targetBaseline", {}) if isinstance(request, dict) else {}
    if baseline.get("cleanAligned") is not True:
        errors.append("request.targetBaseline.cleanAligned must be true")
    if baseline.get("gitStatus") != "## main...origin/main":
        errors.append("request.targetBaseline.gitStatus must be clean/aligned")
    if request.get("claimScope", {}).get("dryRunOnly") is not True:
        errors.append("request.claimScope.dryRunOnly must be true")
    for key in [
        "sourceMutated",
        "targetMutated",
        "proposalApplied",
        "sourcePatchGenerated",
        "sourcePatchApplied",
        "windowsUtilityCommitCreated",
        "windowsUtilityPushPerformed",
        "hardwareActionClaimed",
        "packagingClaimed",
        "releaseClaimed",
        "productizationClaimed",
    ]:
        if request.get("claimScope", {}).get(key) is not False:
            errors.append(f"request.claimScope.{key} must be false")

    if target_root is not None and target_root.exists():
        try:
            actual = collect_target_state(target_root)
            if actual["head"] != baseline.get("head"):
                errors.append("target HEAD does not match dry-run baseline")
            if actual["originMain"] != baseline.get("originMain"):
                errors.append("target origin/main does not match dry-run baseline")
            if actual["gitStatus"] != "## main...origin/main":
                errors.append("target status must stay clean/aligned")
        except (OSError, subprocess.CalledProcessError) as error:
            errors.append(f"failed to inspect target git state: {error}")

    if change_set.get("patchApplicationMode") != "non-mutating-preview-only":
        errors.append("change-set.patchApplicationMode must be non-mutating-preview-only")
    if change_set.get("applicationStatus") != "not-applied":
        errors.append("change-set.applicationStatus must be not-applied")
    if change_set.get("sourcePatchExpected") is not False:
        errors.append("change-set.sourcePatchExpected must be false")
    if change_set.get("sourcePatchGenerated") is not False:
        errors.append("change-set.sourcePatchGenerated must be false")
    if change_set.get("sourcePatchApplied") is not False:
        errors.append("change-set.sourcePatchApplied must be false")
    if change_set.get("plannedSourceChanges") != []:
        errors.append("change-set.plannedSourceChanges must be empty")
    if change_set.get("operationCount") != 0:
        errors.append("change-set.operationCount must be 0")
    if change_set.get("operations") != []:
        errors.append("change-set.operations must be empty")
    intended = change_set.get("intendedTouchedFiles", [])
    if not isinstance(intended, list) or not intended:
        errors.append("change-set.intendedTouchedFiles must be non-empty")
    elif any(item.get("writeExpected") is not False for item in intended if isinstance(item, dict)):
        errors.append("change-set.intendedTouchedFiles writeExpected must stay false")

    touched_results = touched.get("results", [])
    if touched.get("fileCount") != len(touched_results) or not touched_results:
        errors.append("touched-file report must include non-empty results")
    if touched.get("writeExpectedFileCount") != 0:
        errors.append("touched-file writeExpectedFileCount must be 0")
    for item in touched_results if isinstance(touched_results, list) else []:
        if item.get("writeExpected") is not False:
            errors.append(f"touched-file {item.get('path')} writeExpected must be false")
        if item.get("digestMatched") is not True:
            errors.append(f"touched-file {item.get('path')} digest must match")
        if item.get("byteLengthMatched") is not True:
            errors.append(f"touched-file {item.get('path')} byte length must match")

    required_evidence = evidence.get("requiredEvidence", [])
    if not isinstance(required_evidence, list) or len(required_evidence) < 4:
        errors.append("evidence-plan.requiredEvidence must include at least four items")
    if evidence.get("hardwareRequired") is not False:
        errors.append("evidence-plan.hardwareRequired must be false")

    if rollback.get("sourceMutationPerformed") is not False:
        errors.append("rollback-plan.sourceMutationPerformed must be false")
    if rollback.get("rollbackActionRequiredForThisDryRun") is not False:
        errors.append("rollback-plan.rollbackActionRequiredForThisDryRun must be false")
    if not rollback.get("stopConditions"):
        errors.append("rollback-plan.stopConditions must be non-empty")

    dry_run_authority = authority.get("dryRunAuthority", {})
    if dry_run_authority.get("nonMutatingDryRunRecorded") is not True:
        errors.append("authority.dryRunAuthority.nonMutatingDryRunRecorded must be true")
    for key in [
        "sourceApplicationAuthorized",
        "proposalApplicationAuthorized",
        "targetWritesAuthorized",
        "aiSelfAuthorizationAllowed",
        "hardwareActionsAuthorized",
        "packagingAuthorized",
        "releaseAuthorized",
    ]:
        if dry_run_authority.get(key) is not False:
            errors.append(f"authority.dryRunAuthority.{key} must be false")

    output_files = [str((out_dir / name).resolve()) for name in artifacts]
    return {
        "artifactRole": "intentgraph-windowsutility-source-application-dry-run-validation-report",
        "status": "intentgraph-windowsutility-source-application-dry-run-validation-passed"
        if not errors
        else "intentgraph-windowsutility-source-application-dry-run-validation-failed",
        "scope": SCOPE,
        "workItem": WORK_ITEM,
        "date": DATE,
        "reportVersion": REPORT_VERSION,
        "result": "pass" if not errors else "fail",
        "summary": {
            "artifactCount": len(artifacts),
            "touchedFileCount": len(touched_results) if isinstance(touched_results, list) else 0,
            "requiredEvidenceCount": len(required_evidence) if isinstance(required_evidence, list) else 0,
            "changeOperationCount": change_set.get("operationCount"),
            "errorCount": len(errors),
        },
        "outputFiles": output_files,
        "authorizations": empty_authorizations(),
        "errors": errors,
    }


def emit(
    repo_root: Path,
    target_root: Path,
    boundary_report: Path,
    accepted_mapping: Path,
    proposal: Path,
    out_dir: Path,
    source_modification_permission_observed: bool,
) -> dict[str, Any]:
    artifacts = build_artifacts(
        repo_root,
        target_root,
        boundary_report,
        accepted_mapping,
        proposal,
        source_modification_permission_observed,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    for filename, data in artifacts.items():
        write_json(out_dir / filename, data)
    validation = validate_dry_run_dir(out_dir, target_root=target_root)
    write_json(out_dir / VALIDATION_REPORT_FILE, validation)
    return validation


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit a non-mutating WindowsUtility source application dry-run.")
    parser.add_argument("--boundary-report", required=True, type=Path)
    parser.add_argument("--accepted-mapping", required=True, type=Path)
    parser.add_argument("--non-applied-proposal", required=True, type=Path)
    parser.add_argument("--target-root", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--source-modification-permission-observed", action="store_true")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    try:
        report = emit(
            repo_root=repo_root,
            target_root=args.target_root,
            boundary_report=args.boundary_report,
            accepted_mapping=args.accepted_mapping,
            proposal=args.non_applied_proposal,
            out_dir=args.out_dir,
            source_modification_permission_observed=args.source_modification_permission_observed,
        )
    except (OSError, json.JSONDecodeError, ValueError, subprocess.CalledProcessError) as error:
        print(f"emit WindowsUtility source application dry-run failed: {error}")
        return 1
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
