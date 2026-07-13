"""Local-only facade for bounded B1 review and experimental C# fact workspaces."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from experimental_csharp_workspace import (
    ExperimentalWorkspaceError,
    initialize_workspace as initialize_experimental_csharp_workspace,
    validate_command as validate_experimental_csharp_workspace,
)
from emit_experimental_csharp_fact_workbench import (
    FactWorkbenchError,
    emit_workbench as emit_experimental_csharp_fact_workbench,
    validate_emitted_workbench as validate_experimental_csharp_fact_workbench,
)
from experimental_csharp_project import (
    ProjectWorkspaceError,
    add_change_proposal as add_experimental_csharp_change_proposal,
    draft_change_proposal_from_mapping as draft_experimental_csharp_change_proposal,
    draft_review_receipt_from_proposal as draft_experimental_csharp_review_receipt,
    add_mapping_candidate as add_experimental_csharp_mapping_candidate,
    add_review_receipt as add_experimental_csharp_review_receipt,
    add_verifier_result as add_experimental_csharp_verifier_result,
    add_work_request as add_experimental_csharp_work_request,
    emit_project_workbench as emit_experimental_csharp_project_workbench,
    initialize_project as initialize_experimental_csharp_project,
    record_semantic_foundation as record_experimental_csharp_semantic_foundation,
    record_semantic_relation_overlay as record_experimental_csharp_semantic_relation_overlay,
    validate_emitted_project_workbench as validate_experimental_csharp_project_workbench,
)
from serve_experimental_csharp_project_workbench import LocalWorkbenchServerError, serve as serve_experimental_csharp_project_workbench

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_FILE = "intentgraph.workspace.json"
PROFILE = "b1-typescript-rest-api-sample"
WORKSPACE_ROLE = "intentgraph-local-review-workspace"
SCHEMA_VERSION = "0.2.0"
LOGICAL_SOURCE_ROOT_ID = "intentgraph://profiles/b1-typescript-rest-api-sample/source"

SAMPLE_SOURCE = ROOT / "docs" / "examples" / "b1-typescript-rest-api" / "source"
SAMPLE_OVERLAY = ROOT / "docs" / "examples" / "b1-typescript-rest-api" / "intentgraph.overlay.json"
SAMPLE_WORKSPACE_PROPOSAL = (
    ROOT
    / "docs"
    / "examples"
    / "b1-typescript-rest-api"
    / "proposals"
    / "p9.2-local-review-workspace.proposal.json"
)

REQUIRED_OUTPUTS = {
    "codeFacts": "artifacts/code-facts.json",
    "codeFactsValidation": "artifacts/code-facts-validation.json",
    "mapping": "artifacts/intent-mapping.json",
    "proposalValidation": "artifacts/proposal-validation.json",
    "consistency": "artifacts/proposal-consistency.json",
    "workbenchProjection": "artifacts/workbench-projection.json",
    "workbenchHtml": "artifacts/workbench.html",
    "workbenchValidation": "artifacts/workbench-validation.json",
    "reviewReport": "artifacts/review-report.json",
}

REQUIRED_AUTHORITY = {
    "targetRepositoryMutation": False,
    "automaticCodeApplication": False,
    "networkRequired": False,
    "providerApiAllowed": False,
    "credentialAccessAllowed": False,
    "hookInstallationAllowed": False,
    "releasePublishingAllowed": False,
}


class WorkspaceError(ValueError):
    """Raised when a workspace violates the local review contract."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def digest_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def digest_json(value: Any) -> str:
    return digest_bytes(canonical_json(value).encode("utf-8"))


def digest_tree(root: Path) -> str:
    return digest_records(source_tree_records(root))


def digest_records(records: list[dict[str, str]]) -> str:
    if not records:
        raise WorkspaceError("source root must contain at least one file")
    return digest_json(records)


def source_tree_records(root: Path, *, require_typescript_only: bool = False) -> list[dict[str, str]]:
    if not root.is_dir():
        raise WorkspaceError(f"source root is not a directory: {root}")
    if root.is_symlink():
        raise WorkspaceError("source root must not be a symlink")
    records: list[dict[str, str]] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise WorkspaceError(f"source tree must not contain symlinks: {path.name}")
        if not path.is_file():
            continue
        if require_typescript_only and path.suffix != ".ts":
            raise WorkspaceError(f"unsupported source extension for B1 profile: {path.suffix or '<none>'}")
        records.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": digest_bytes(path.read_bytes()),
            }
        )
    if not records:
        raise WorkspaceError("source root must contain at least one file")
    return records


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise WorkspaceError(f"missing required file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise WorkspaceError(f"invalid JSON: {path}: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise WorkspaceError(f"JSON root must be an object: {path}")
    return value


def workspace_path(value: str) -> Path:
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise WorkspaceError(f"workspace path must be relative and contained: {value}")
    return candidate


def contained_path(workspace: Path, value: str, *, artifact: bool = False) -> Path:
    relative = workspace_path(value)
    if artifact and (not relative.parts or relative.parts[0] != "artifacts"):
        raise WorkspaceError(f"workspace output must remain under artifacts/: {value}")
    resolved_workspace = workspace.resolve()
    candidate = (workspace / relative).resolve()
    try:
        candidate.relative_to(resolved_workspace)
    except ValueError as exc:
        raise WorkspaceError(f"workspace path escapes workspace: {value}") from exc
    return candidate


def sample_manifest() -> dict[str, Any]:
    return {
        "artifactRole": WORKSPACE_ROLE,
        "schemaVersion": SCHEMA_VERSION,
        "profile": PROFILE,
        "mode": "local-review-only",
        "source": {
            "root": "source",
            "digest": digest_tree(SAMPLE_SOURCE),
            "logicalId": LOGICAL_SOURCE_ROOT_ID,
            "mutationAllowed": False,
        },
        "inputs": {
            "overlay": "overlay/intentgraph.overlay.json",
            "proposal": "proposals/p4.0-complete-todo-route.proposal.json",
        },
        "outputs": REQUIRED_OUTPUTS,
        "authority": REQUIRED_AUTHORITY,
    }


def profile_source_records() -> list[dict[str, str]]:
    return source_tree_records(SAMPLE_SOURCE, require_typescript_only=True)


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def external_source_receipt(records: list[dict[str, str]]) -> dict[str, Any]:
    source_digest = digest_records(records)
    return {
        "artifactRole": "intentgraph-external-source-intake-receipt",
        "status": "intentgraph-external-source-intake-recorded",
        "profileId": PROFILE,
        "logicalSourceRoot": LOGICAL_SOURCE_ROOT_ID,
        "sourceTreeDigestBefore": source_digest,
        "sourceTreeDigestAfter": source_digest,
        "copiedSourceTreeDigest": source_digest,
        "sourceFileCount": len(records),
        "sourceFileDigests": records,
        "externalSourceMutated": False,
        "sourcePathPersisted": False,
        "networkRequired": False,
        "automaticCodeApplication": False,
        "targetRepositoryMutation": False,
    }


def validate_workspace(workspace: Path) -> tuple[dict[str, Any], dict[str, Path]]:
    workspace = workspace.resolve()
    manifest_path = workspace / WORKSPACE_FILE
    manifest = read_json(manifest_path)
    expected_scalars = {
        "artifactRole": WORKSPACE_ROLE,
        "schemaVersion": SCHEMA_VERSION,
        "profile": PROFILE,
        "mode": "local-review-only",
    }
    for key, expected in expected_scalars.items():
        if manifest.get(key) != expected:
            raise WorkspaceError(f"workspace {key} must equal {expected}")

    source = manifest.get("source")
    if not isinstance(source, dict):
        raise WorkspaceError("workspace source must be an object")
    if source.get("mutationAllowed") is not False:
        raise WorkspaceError("workspace source mutation must remain false")
    if source.get("logicalId") != LOGICAL_SOURCE_ROOT_ID:
        raise WorkspaceError(f"workspace source logicalId must equal {LOGICAL_SOURCE_ROOT_ID}")
    source_root = contained_path(workspace, str(source.get("root", "")))
    expected_digest = source.get("digest")
    if not isinstance(expected_digest, str) or not expected_digest.startswith("sha256:"):
        raise WorkspaceError("workspace source digest must be a sha256 value")
    actual_digest = digest_tree(source_root)
    if actual_digest != expected_digest:
        raise WorkspaceError("workspace source digest does not match declared provenance")

    inputs = manifest.get("inputs")
    if not isinstance(inputs, dict):
        raise WorkspaceError("workspace inputs must be an object")
    input_paths: dict[str, Path] = {"sourceRoot": source_root}
    for key in ("overlay", "proposal"):
        value = inputs.get(key)
        if not isinstance(value, str):
            raise WorkspaceError(f"workspace input {key} must be a relative path")
        path = contained_path(workspace, value)
        if not path.is_file():
            raise WorkspaceError(f"workspace input {key} is missing: {value}")
        input_paths[key] = path

    proposal_profile = read_json(input_paths["proposal"]).get("workspaceProfile")
    expected_profile = {
        "id": PROFILE,
        "logicalSourceRoot": LOGICAL_SOURCE_ROOT_ID,
        "pathSpecificBaselineMaterialization": False,
        "sourceTextIncluded": False,
        "patchIncluded": False,
        "applied": False,
    }
    if proposal_profile != expected_profile:
        raise WorkspaceError("workspace proposal must declare the bounded logical source profile")

    outputs = manifest.get("outputs")
    if not isinstance(outputs, dict):
        raise WorkspaceError("workspace outputs must be an object")
    for key, expected in REQUIRED_OUTPUTS.items():
        if outputs.get(key) != expected:
            raise WorkspaceError(f"workspace output {key} must equal {expected}")
        input_paths[key] = contained_path(workspace, expected, artifact=True)

    authority = manifest.get("authority")
    if authority != REQUIRED_AUTHORITY:
        raise WorkspaceError("workspace authority must equal the local review-only authority boundary")

    intake = manifest.get("externalSourceIntake")
    if intake is not None:
        if intake != {
            "mode": "read-only-snapshot-copy",
            "receipt": "artifacts/external-source-intake-receipt.json",
            "sourcePathPersisted": False,
        }:
            raise WorkspaceError("workspace external source intake boundary is invalid")
        receipt_path = contained_path(workspace, str(intake["receipt"]), artifact=True)
        receipt = read_json(receipt_path)
        records = source_tree_records(source_root, require_typescript_only=True)
        source_digest = digest_records(records)
        expected_receipt = external_source_receipt(records)
        if receipt != expected_receipt or receipt["copiedSourceTreeDigest"] != source_digest:
            raise WorkspaceError("external source intake receipt does not match copied source evidence")
        input_paths["externalSourceIntakeReceipt"] = receipt_path

    return manifest, input_paths


def emit_status(value: dict[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=True, indent=2))


def initialize_sample(workspace: Path) -> int:
    workspace = workspace.resolve()
    if workspace.exists() and any(workspace.iterdir()):
        raise WorkspaceError("workspace must be absent or empty for init-sample")
    workspace.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SAMPLE_SOURCE, workspace / "source", dirs_exist_ok=True)
    (workspace / "overlay").mkdir(parents=True, exist_ok=True)
    (workspace / "proposals").mkdir(parents=True, exist_ok=True)
    shutil.copy2(SAMPLE_OVERLAY, workspace / "overlay" / "intentgraph.overlay.json")
    proposal_path = workspace / "proposals" / "p4.0-complete-todo-route.proposal.json"
    shutil.copy2(SAMPLE_WORKSPACE_PROPOSAL, proposal_path)
    manifest = sample_manifest()
    write_json(workspace / WORKSPACE_FILE, manifest)
    _, paths = validate_workspace(workspace)
    emit_status(
        {
            "result": "pass",
            "command": "init-sample",
            "workspaceRole": WORKSPACE_ROLE,
            "profile": PROFILE,
            "workspace": workspace.as_posix(),
            "sourceDigest": manifest["source"]["digest"],
            "overlay": paths["overlay"].relative_to(workspace).as_posix(),
            "proposal": paths["proposal"].relative_to(workspace).as_posix(),
            "logicalSourceRoot": LOGICAL_SOURCE_ROOT_ID,
            "proposalProfileTemplate": True,
            "authority": REQUIRED_AUTHORITY,
        }
    )
    return 0


def initialize_b1_equivalent_import(workspace: Path, external_source_root: Path) -> int:
    workspace = workspace.resolve()
    if external_source_root.is_symlink():
        raise WorkspaceError("external source root must be a non-symlink directory")
    external_source_root = external_source_root.resolve()
    if workspace.exists():
        raise WorkspaceError("workspace must not exist for external import")
    if not external_source_root.is_dir():
        raise WorkspaceError("external source root must be a non-symlink directory")
    if is_within(workspace, external_source_root) or is_within(external_source_root, workspace):
        raise WorkspaceError("external source root and workspace must not overlap")

    before_records = source_tree_records(external_source_root, require_typescript_only=True)
    if before_records != profile_source_records():
        raise WorkspaceError("external source is not B1-equivalent to the bounded profile")

    try:
        workspace.mkdir(parents=True, exist_ok=False)
        shutil.copytree(external_source_root, workspace / "source", dirs_exist_ok=False)
        after_records = source_tree_records(external_source_root, require_typescript_only=True)
        copied_records = source_tree_records(workspace / "source", require_typescript_only=True)
        if after_records != before_records:
            raise WorkspaceError("external source digest changed during intake")
        if copied_records != before_records:
            raise WorkspaceError("copied source evidence does not match external source")

        (workspace / "overlay").mkdir(parents=True, exist_ok=True)
        (workspace / "proposals").mkdir(parents=True, exist_ok=True)
        shutil.copy2(SAMPLE_OVERLAY, workspace / "overlay" / "intentgraph.overlay.json")
        shutil.copy2(SAMPLE_WORKSPACE_PROPOSAL, workspace / "proposals" / "p4.0-complete-todo-route.proposal.json")
        manifest = sample_manifest()
        manifest["externalSourceIntake"] = {
            "mode": "read-only-snapshot-copy",
            "receipt": "artifacts/external-source-intake-receipt.json",
            "sourcePathPersisted": False,
        }
        write_json(workspace / WORKSPACE_FILE, manifest)
        write_json(workspace / "artifacts" / "external-source-intake-receipt.json", external_source_receipt(before_records))
        _, paths = validate_workspace(workspace)
    except Exception:
        if workspace.exists():
            shutil.rmtree(workspace)
        raise

    emit_status(
        {
            "result": "pass",
            "command": "import-b1-equivalent",
            "workspaceRole": WORKSPACE_ROLE,
            "profile": PROFILE,
            "logicalSourceRoot": LOGICAL_SOURCE_ROOT_ID,
            "sourceDigest": manifest["source"]["digest"],
            "sourceFileCount": len(before_records),
            "externalSourceMutated": False,
            "sourcePathPersisted": False,
            "receipt": paths["externalSourceIntakeReceipt"].relative_to(workspace).as_posix(),
            "authority": REQUIRED_AUTHORITY,
        }
    )
    return 0


def run_tool(script: str, args: list[str | Path]) -> dict[str, Any]:
    command = [sys.executable, str(ROOT / "tools" / script)] + [str(path) for path in args]
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    return {
        "script": f"tools/{script}",
        "exitCode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def review_workspace(workspace: Path) -> int:
    workspace = workspace.resolve()
    manifest, paths = validate_workspace(workspace)
    source_digest_before = digest_tree(paths["sourceRoot"])

    calls = [
        (
            "extract-code-facts",
            "extract_b1_code_facts.py",
            [
                Path("--source-root"),
                paths["sourceRoot"],
                Path("--source-root-id"),
                LOGICAL_SOURCE_ROOT_ID,
                Path("--out"),
                paths["codeFacts"],
            ],
        ),
        (
            "validate-code-facts",
            "validate_b1_code_facts.py",
            [
                Path("--code-facts"),
                paths["codeFacts"],
                Path("--source-root"),
                paths["sourceRoot"],
                Path("--out"),
                paths["codeFactsValidation"],
            ],
        ),
        (
            "verify-intent-mapping",
            "verify_b1_intent_mapping.py",
            [
                Path("--overlay"),
                paths["overlay"],
                Path("--code-facts"),
                paths["codeFacts"],
                Path("--out"),
                paths["mapping"],
            ],
        ),
        (
            "validate-proposal",
            "validate_b1_change_proposal.py",
            [
                Path("--proposal"),
                paths["proposal"],
                Path("--code-facts"),
                paths["codeFacts"],
                Path("--overlay"),
                paths["overlay"],
                Path("--out"),
                paths["proposalValidation"],
            ],
        ),
        (
            "verify-proposal-consistency",
            "verify_b1_proposal_consistency.py",
            [
                Path("--proposal"),
                paths["proposal"],
                Path("--proposal-validation"),
                paths["proposalValidation"],
                Path("--code-facts"),
                paths["codeFacts"],
                Path("--overlay"),
                paths["overlay"],
                Path("--out"),
                paths["consistency"],
            ],
        ),
        (
            "emit-workbench",
            "emit_b1_workbench_projection.py",
            [
                Path("--proposal"),
                paths["proposal"],
                Path("--proposal-validation"),
                paths["proposalValidation"],
                Path("--consistency"),
                paths["consistency"],
                Path("--code-facts"),
                paths["codeFacts"],
                Path("--overlay"),
                paths["overlay"],
                Path("--projection-out"),
                paths["workbenchProjection"],
                Path("--html-out"),
                paths["workbenchHtml"],
                Path("--validation-out"),
                paths["workbenchValidation"],
            ],
        ),
    ]

    results: list[dict[str, Any]] = []
    for label, script, arguments in calls:
        result = run_tool(script, arguments)
        result["step"] = label
        results.append(result)
        if result["exitCode"] != 0:
            write_json(
                paths["reviewReport"],
                {
                    "artifactRole": "intentgraph-local-review-report",
                    "status": "intentgraph-local-review-failed",
                    "profile": PROFILE,
                    "result": "fail",
                    "failedStep": label,
                    "steps": results,
                    "sourceDigestBefore": source_digest_before,
                    "sourceDigestAfter": digest_tree(paths["sourceRoot"]),
                    "sourceTextEqualityRequired": False,
                    "targetRepositoryMutation": False,
                    "automaticCodeApplication": False,
                },
            )
            raise WorkspaceError(f"review step failed: {label}")

    source_digest_after = digest_tree(paths["sourceRoot"])
    if source_digest_after != source_digest_before:
        raise WorkspaceError("workspace review changed source contents")

    output_digests = {
        key: digest_bytes(path.read_bytes())
        for key, path in paths.items()
        if key in REQUIRED_OUTPUTS and key != "reviewReport" and path.is_file()
    }
    report = {
        "artifactRole": "intentgraph-local-review-report",
        "status": "intentgraph-local-review-passed",
        "profile": PROFILE,
        "mode": "local-review-only",
        "result": "pass",
        "workspaceManifestDigest": digest_json(manifest),
        "sourceDigestBefore": source_digest_before,
        "sourceDigestAfter": source_digest_after,
        "logicalSourceRoot": manifest["source"]["logicalId"],
        "sourceTextEqualityRequired": False,
        "targetRepositoryMutation": False,
        "automaticCodeApplication": False,
        "networkRequired": False,
        "steps": [
            {"step": entry["step"], "script": entry["script"], "exitCode": entry["exitCode"]}
            for entry in results
        ],
        "outputs": {
            key: {
                "path": path.relative_to(workspace).as_posix(),
                "digest": output_digests.get(key),
                "digestStatus": "self-not-hashed" if key == "reviewReport" else "file-bytes",
            }
            for key, path in paths.items()
            if key in REQUIRED_OUTPUTS
        },
    }
    write_json(paths["reviewReport"], report)
    emit_status(report)
    return 0


def validate_command(workspace: Path) -> int:
    manifest, paths = validate_workspace(workspace.resolve())
    emit_status(
        {
            "result": "pass",
            "command": "validate",
            "workspaceRole": manifest["artifactRole"],
            "profile": manifest["profile"],
            "sourceDigest": manifest["source"]["digest"],
            "paths": {key: value.relative_to(workspace.resolve()).as_posix() for key, value in paths.items()},
            "authority": manifest["authority"],
        }
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the bounded local IntentGraph B1 review workflow.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("init-sample", "Create a fresh B1 local-review workspace."),
        ("validate", "Validate a local-review workspace without running the workflow."),
        ("review", "Run the deterministic B1 review workflow inside a workspace."),
    ):
        command = subparsers.add_parser(name, help=help_text)
        command.add_argument("--workspace", required=True, type=Path)
    external_import = subparsers.add_parser(
        "import-b1-equivalent",
        help="Snapshot a B1-equivalent external TypeScript source tree into a new local-review workspace.",
    )
    external_import.add_argument("--workspace", required=True, type=Path)
    external_import.add_argument("--source-root", required=True, type=Path)
    csharp_init = subparsers.add_parser(
        "init-experimental-csharp",
        help="Create a fact-only C# snapshot workspace from the declared experimental host-SDK profile.",
    )
    csharp_init.add_argument("--workspace", required=True, type=Path)
    csharp_init.add_argument("--source-root", required=True, type=Path)
    csharp_init.add_argument("--profile", required=True, type=Path)
    csharp_validate = subparsers.add_parser(
        "validate-experimental-csharp",
        help="Validate an existing fact-only experimental C# snapshot workspace.",
    )
    csharp_validate.add_argument("--workspace", required=True, type=Path)
    csharp_workbench = subparsers.add_parser(
        "emit-experimental-csharp-fact-workbench",
        help="Emit a separate local HTML inspector from a validated fact-only experimental C# workspace.",
    )
    csharp_workbench.add_argument("--workspace", required=True, type=Path)
    csharp_workbench.add_argument("--out", required=True, type=Path)
    csharp_workbench_validate = subparsers.add_parser(
        "validate-experimental-csharp-fact-workbench",
        help="Validate a separate local HTML inspector emitted from a fact-only experimental C# workspace.",
    )
    csharp_workbench_validate.add_argument("--workspace", required=True, type=Path)
    csharp_workbench_validate.add_argument("--out", required=True, type=Path)
    csharp_project_init = subparsers.add_parser(
        "init-experimental-csharp-project",
        help="Create a separate semantic-overlay project workspace from a validated C# fact snapshot.",
    )
    csharp_project_init.add_argument("--snapshot-workspace", required=True, type=Path)
    csharp_project_init.add_argument("--workspace", required=True, type=Path)
    csharp_project_init.add_argument("--project-id", required=True)
    csharp_project_init.add_argument("--title", required=True)
    csharp_project_request = subparsers.add_parser(
        "add-experimental-csharp-work-request",
        help="Record a user work request in a local C# semantic-overlay project workspace.",
    )
    csharp_project_request.add_argument("--workspace", required=True, type=Path)
    csharp_project_request.add_argument("--work-id", required=True)
    csharp_project_request.add_argument("--title", required=True)
    csharp_project_request.add_argument("--request", required=True)
    csharp_project_mapping = subparsers.add_parser(
        "add-experimental-csharp-mapping-candidate",
        help="Record a declared, unaccepted work-to-code-fact mapping candidate.",
    )
    csharp_project_mapping.add_argument("--workspace", required=True, type=Path)
    csharp_project_mapping.add_argument("--work-id", required=True)
    csharp_project_mapping.add_argument("--code-fact", required=True, action="append")
    csharp_project_mapping.add_argument("--rationale", required=True)
    csharp_project_foundation = subparsers.add_parser(
        "record-experimental-csharp-semantic-foundation",
        help="Record a declared project semantic foundation without creating Intent Units or changing source code.",
    )
    csharp_project_foundation.add_argument("--workspace", required=True, type=Path)
    csharp_project_foundation.add_argument("--foundation", required=True, type=Path)
    csharp_project_semantic_relations = subparsers.add_parser(
        "record-experimental-csharp-semantic-relation-overlay",
        help="Record read-only local C# symbol relations for relation-aware graph layout without building or changing source.",
    )
    csharp_project_semantic_relations.add_argument("--workspace", required=True, type=Path)
    csharp_project_semantic_relations.add_argument("--overlay", required=True, type=Path)
    csharp_project_proposal = subparsers.add_parser(
        "add-experimental-csharp-change-proposal",
        help="Record a non-applied C# change proposal with graph delta and code diff review data.",
    )
    csharp_project_proposal.add_argument("--workspace", required=True, type=Path)
    csharp_project_proposal.add_argument("--proposal", required=True, type=Path)
    csharp_project_guided_proposal = subparsers.add_parser(
        "draft-experimental-csharp-change-proposal",
        help="Record a bounded non-applied review proposal from an existing declared mapping, without a code patch.",
    )
    csharp_project_guided_proposal.add_argument("--workspace", required=True, type=Path)
    csharp_project_guided_proposal.add_argument("--proposal-id", required=True)
    csharp_project_guided_proposal.add_argument("--work-id", required=True)
    csharp_project_guided_proposal.add_argument("--title", required=True)
    csharp_project_guided_proposal.add_argument("--summary", required=True)
    csharp_project_guided_proposal.add_argument("--verification-kind", required=True)
    csharp_project_guided_proposal.add_argument("--verification-summary", required=True)
    csharp_project_guided_proposal.add_argument("--evidence-kind", required=True)
    csharp_project_guided_proposal.add_argument("--evidence-summary", required=True)
    csharp_project_receipt = subparsers.add_parser(
        "add-experimental-csharp-review-receipt",
        help="Record a non-executing review receipt for one proposal verification/evidence requirement pair.",
    )
    csharp_project_receipt.add_argument("--workspace", required=True, type=Path)
    csharp_project_receipt.add_argument("--receipt", required=True, type=Path)
    csharp_project_verifier_result = subparsers.add_parser(
        "add-experimental-csharp-verifier-result",
        help="Import a deterministic verifier result and bind its evidence to proposal requirements.",
    )
    csharp_project_verifier_result.add_argument("--workspace", required=True, type=Path)
    csharp_project_verifier_result.add_argument("--result", required=True, type=Path)
    csharp_project_guided_receipt = subparsers.add_parser(
        "draft-experimental-csharp-review-receipt",
        help="Record a user-authored, non-executing review receipt from existing proposal requirements.",
    )
    csharp_project_guided_receipt.add_argument("--workspace", required=True, type=Path)
    csharp_project_guided_receipt.add_argument("--receipt-id", required=True)
    csharp_project_guided_receipt.add_argument("--proposal-id", required=True)
    csharp_project_guided_receipt.add_argument("--verification-requirement-id", required=True)
    csharp_project_guided_receipt.add_argument("--evidence-requirement-id", required=True)
    csharp_project_guided_receipt.add_argument("--result", required=True, choices=["reviewed-pass", "reviewed-fail", "review-blocked"])
    csharp_project_guided_receipt.add_argument("--summary", required=True)
    csharp_project_workbench = subparsers.add_parser(
        "emit-experimental-csharp-project-workbench",
        help="Emit a unified project workbench from a local C# semantic-overlay project workspace.",
    )
    csharp_project_workbench.add_argument("--workspace", required=True, type=Path)
    csharp_project_workbench.add_argument("--out", required=True, type=Path)
    csharp_project_workbench_validate = subparsers.add_parser(
        "validate-experimental-csharp-project-workbench",
        help="Validate a unified project workbench emitted from a local C# semantic-overlay project workspace.",
    )
    csharp_project_workbench_validate.add_argument("--workspace", required=True, type=Path)
    csharp_project_workbench_validate.add_argument("--out", required=True, type=Path)
    csharp_project_serve = subparsers.add_parser(
        "serve-experimental-csharp-project-workbench",
        help="Serve an interactive local C# project workbench on loopback only.",
    )
    csharp_project_serve.add_argument("--workspace", required=True, type=Path)
    csharp_project_serve.add_argument("--host", default="127.0.0.1")
    csharp_project_serve.add_argument("--port", default=8765, type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "init-sample":
            return initialize_sample(args.workspace)
        if args.command == "validate":
            return validate_command(args.workspace)
        if args.command == "review":
            return review_workspace(args.workspace)
        if args.command == "import-b1-equivalent":
            return initialize_b1_equivalent_import(args.workspace, args.source_root)
        if args.command == "init-experimental-csharp":
            emit_status(initialize_experimental_csharp_workspace(args.workspace, args.source_root, args.profile))
            return 0
        if args.command == "validate-experimental-csharp":
            emit_status(validate_experimental_csharp_workspace(args.workspace))
            return 0
        if args.command == "emit-experimental-csharp-fact-workbench":
            emit_status(emit_experimental_csharp_fact_workbench(args.workspace, args.out))
            return 0
        if args.command == "validate-experimental-csharp-fact-workbench":
            emit_status(validate_experimental_csharp_fact_workbench(args.workspace, args.out))
            return 0
        if args.command == "init-experimental-csharp-project":
            emit_status(initialize_experimental_csharp_project(args.snapshot_workspace, args.workspace, args.project_id, args.title))
            return 0
        if args.command == "add-experimental-csharp-work-request":
            emit_status(add_experimental_csharp_work_request(args.workspace, args.work_id, args.title, args.request))
            return 0
        if args.command == "add-experimental-csharp-mapping-candidate":
            emit_status(add_experimental_csharp_mapping_candidate(args.workspace, args.work_id, args.code_fact, args.rationale))
            return 0
        if args.command == "record-experimental-csharp-semantic-foundation":
            emit_status(record_experimental_csharp_semantic_foundation(args.workspace, args.foundation))
            return 0
        if args.command == "record-experimental-csharp-semantic-relation-overlay":
            emit_status(record_experimental_csharp_semantic_relation_overlay(args.workspace, args.overlay))
            return 0
        if args.command == "add-experimental-csharp-change-proposal":
            emit_status(add_experimental_csharp_change_proposal(args.workspace, args.proposal))
            return 0
        if args.command == "draft-experimental-csharp-change-proposal":
            emit_status(
                draft_experimental_csharp_change_proposal(
                    args.workspace,
                    proposal_id=args.proposal_id,
                    work_id=args.work_id,
                    title=args.title,
                    summary=args.summary,
                    verification_kind=args.verification_kind,
                    verification_summary=args.verification_summary,
                    evidence_kind=args.evidence_kind,
                    evidence_summary=args.evidence_summary,
                )
            )
            return 0
        if args.command == "add-experimental-csharp-review-receipt":
            emit_status(add_experimental_csharp_review_receipt(args.workspace, args.receipt))
            return 0
        if args.command == "add-experimental-csharp-verifier-result":
            emit_status(add_experimental_csharp_verifier_result(args.workspace, args.result))
            return 0
        if args.command == "draft-experimental-csharp-review-receipt":
            emit_status(
                draft_experimental_csharp_review_receipt(
                    args.workspace,
                    receipt_id=args.receipt_id,
                    proposal_id=args.proposal_id,
                    verification_requirement_id=args.verification_requirement_id,
                    evidence_requirement_id=args.evidence_requirement_id,
                    result=args.result,
                    summary=args.summary,
                )
            )
            return 0
        if args.command == "emit-experimental-csharp-project-workbench":
            emit_status(emit_experimental_csharp_project_workbench(args.workspace, args.out))
            return 0
        if args.command == "validate-experimental-csharp-project-workbench":
            emit_status(validate_experimental_csharp_project_workbench(args.workspace, args.out))
            return 0
        if args.command == "serve-experimental-csharp-project-workbench":
            return serve_experimental_csharp_project_workbench(args.workspace, args.host, args.port)
        raise WorkspaceError(f"unsupported command: {args.command}")
    except (WorkspaceError, ExperimentalWorkspaceError, FactWorkbenchError, ProjectWorkspaceError, LocalWorkbenchServerError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
