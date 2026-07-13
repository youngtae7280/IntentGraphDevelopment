"""Local-only P9.1 facade for the bounded B1 IntentGraph review workflow."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


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
    if not root.is_dir():
        raise WorkspaceError(f"source root is not a directory: {root}")
    records: list[dict[str, str]] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        records.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": digest_bytes(path.read_bytes()),
            }
        )
    if not records:
        raise WorkspaceError("source root must contain at least one file")
    return digest_json(records)


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
        raise WorkspaceError(f"unsupported command: {args.command}")
    except WorkspaceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
