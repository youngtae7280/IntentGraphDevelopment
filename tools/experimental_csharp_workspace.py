"""Create and validate the bounded P9.10 experimental C# fact workspace."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Any

from preflight_csharp_host_sdk_profile import PreflightError, preflight_profile, validate_profile
from run_windowsutility_csharp_syntax_probe import (
    ProbeError,
    build_probe,
    invoke_probe,
    read_json,
    validate_facts,
)


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_FILE = "intentgraph.workspace.json"
WORKSPACE_ROLE = "intentgraph-experimental-csharp-fact-workspace"
WORKSPACE_SCHEMA_VERSION = "0.1.0"
PROFILE_PATH = ROOT / "docs" / "examples" / "profiles" / "experimental-host-sdk-csharp-syntax.profile.json"
PROFILE_COPY = "profiles/experimental-host-sdk-csharp-syntax.profile.json"
PROFILE_ID = "experimental-csharp-host-sdk-syntax-only"
LOGICAL_SOURCE_ROOT = "intentgraph://profiles/experimental-csharp-host-sdk-syntax-only/source"
FACT_SCOPE = "experimental-csharp-host-sdk-fact-workspace"
FACT_PROFILE_ID = "experimental-csharp-host-sdk-syntax-only"
OUTPUTS = {
    "preflight": "artifacts/host-sdk-preflight.json",
    "intakeReceipt": "artifacts/external-source-intake-receipt.json",
    "codeFacts": "artifacts/code-facts.json",
    "extractionReport": "artifacts/csharp-extraction-report.json",
    "workspaceValidation": "artifacts/fact-workspace-validation.json",
}
AUTHORITY = {
    "externalSourceReadForSnapshot": True,
    "targetRepositoryMutation": False,
    "targetBuildExecuted": False,
    "targetRestoreExecuted": False,
    "targetLaunchExecuted": False,
    "packageDependencyAdded": False,
    "packageInstallExecuted": False,
    "externalPackageRestoreExecuted": False,
    "localAdapterProjectRestoreExecuted": True,
    "localAdapterRestorePackageSources": "empty",
    "networkRequired": False,
    "providerApiAllowed": False,
    "credentialAccessAllowed": False,
    "hookInstallationAllowed": False,
    "automaticCodeApplication": False,
    "releasePublishingAllowed": False,
    "igdProductizationClaimed": False,
}
PREFLIGHT_AUTHORITY = {
    "targetRepositoryRead": False,
    "targetRepositoryMutation": False,
    "targetBuildExecuted": False,
    "targetRestoreExecuted": False,
    "targetLaunchExecuted": False,
    "packageDependencyAdded": False,
    "packageRestoreExecuted": False,
    "packageInstallExecuted": False,
    "networkRequired": False,
    "providerApiAllowed": False,
    "credentialAccessAllowed": False,
    "automaticCodeApplication": False,
    "igdProductizationClaimed": False,
}


class ExperimentalWorkspaceError(ValueError):
    """Raised when the experimental C# fact workspace contract is violated."""


def digest_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def digest_json(value: Any) -> str:
    return digest_bytes(canonical_json(value))


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        return read_json(path)
    except (OSError, json.JSONDecodeError, ProbeError) as error:
        raise ExperimentalWorkspaceError(f"invalid JSON artifact: {path.name}") from error


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def is_reparse_point(path: Path) -> bool:
    details = path.lstat()
    attributes = getattr(details, "st_file_attributes", 0)
    reparse_attribute = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(details.st_mode) or bool(attributes & reparse_attribute)


def resolved_source_path(path: Path, root: Path, relative: Path) -> Path:
    try:
        if is_reparse_point(path):
            raise ExperimentalWorkspaceError(f"C# source tree must not contain reparse points: {relative.as_posix()}")
        resolved = path.resolve(strict=True)
        resolved.relative_to(root)
    except ExperimentalWorkspaceError:
        raise
    except (OSError, ValueError) as error:
        raise ExperimentalWorkspaceError(f"C# source path must resolve under the source root: {relative.as_posix()}") from error
    return resolved


def contained_path(workspace: Path, value: str, *, artifact: bool = False) -> Path:
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ExperimentalWorkspaceError(f"workspace path must be relative and contained: {value}")
    if artifact and (not relative.parts or relative.parts[0] != "artifacts"):
        raise ExperimentalWorkspaceError(f"workspace output must remain under artifacts/: {value}")
    candidate = (workspace / relative).resolve()
    if not is_within(candidate, workspace):
        raise ExperimentalWorkspaceError(f"workspace path escapes workspace: {value}")
    return candidate


def csharp_source_records(root: Path) -> list[dict[str, str]]:
    try:
        invalid_root = not root.is_dir() or is_reparse_point(root)
    except OSError:
        invalid_root = True
    if invalid_root:
        raise ExperimentalWorkspaceError("external C# source root must be an existing non-symlink directory")
    root = root.resolve(strict=True)
    records: list[dict[str, str]] = []
    pending = [root]
    while pending:
        directory = pending.pop()
        try:
            entries = sorted(os.scandir(directory), key=lambda entry: entry.name)
        except OSError as error:
            raise ExperimentalWorkspaceError(f"cannot enumerate C# source directory: {directory}") from error
        for entry in entries:
            path = Path(entry.path)
            relative = path.relative_to(root)
            resolved = resolved_source_path(path, root, relative)
            try:
                if entry.is_dir(follow_symlinks=False):
                    if not any(part.lower() in {"bin", "obj"} for part in relative.parts):
                        pending.append(resolved)
                elif entry.is_file(follow_symlinks=False) and path.suffix.lower() == ".cs":
                    records.append({"path": relative.as_posix(), "sha256": digest_bytes(resolved.read_bytes())})
            except OSError as error:
                raise ExperimentalWorkspaceError(f"cannot inspect C# source path: {relative.as_posix()}") from error
    records.sort(key=lambda record: record["path"])
    if not records:
        raise ExperimentalWorkspaceError("external C# source root must contain at least one C# file")
    return records


def records_digest(records: list[dict[str, str]]) -> str:
    if not records:
        raise ExperimentalWorkspaceError("C# source records must be non-empty")
    return digest_json(records)


def declared_profile(profile_path: Path, *, require_canonical_path: bool) -> tuple[dict[str, Any], str]:
    if require_canonical_path and profile_path.resolve() != PROFILE_PATH.resolve():
        raise ExperimentalWorkspaceError("experimental C# workspace must use the declared host-SDK profile path")
    profile = read_json_object(PROFILE_PATH)
    try:
        validate_profile(profile)
    except PreflightError as error:
        raise ExperimentalWorkspaceError(f"declared C# profile is unsafe: {error}") from error
    expected_digest = digest_bytes(PROFILE_PATH.read_bytes())
    if not require_canonical_path and profile_path.read_bytes() != PROFILE_PATH.read_bytes():
        raise ExperimentalWorkspaceError("workspace profile copy must match the declared host-SDK profile")
    return profile, expected_digest


def intake_receipt(records: list[dict[str, str]], profile_digest: str) -> dict[str, Any]:
    digest = records_digest(records)
    return {
        "artifactRole": "intentgraph-experimental-csharp-source-intake-receipt",
        "status": "intentgraph-experimental-csharp-source-intake-recorded",
        "profileId": PROFILE_ID,
        "profileDigest": profile_digest,
        "logicalSourceRoot": LOGICAL_SOURCE_ROOT,
        "sourceTreeDigestBefore": digest,
        "sourceTreeDigestAfter": digest,
        "copiedSourceTreeDigest": digest,
        "sourceFileCount": len(records),
        "sourceFileDigests": records,
        "externalSourceMutated": False,
        "externalSourcePathPersisted": False,
        "sourceRole": "snapshot-copy-not-target",
        "networkRequired": False,
        "automaticCodeApplication": False,
        "targetRepositoryMutation": False,
    }


def manifest_for(records: list[dict[str, str]], profile_digest: str) -> dict[str, Any]:
    return {
        "artifactRole": WORKSPACE_ROLE,
        "schemaVersion": WORKSPACE_SCHEMA_VERSION,
        "profile": {
            "id": PROFILE_ID,
            "path": PROFILE_COPY,
            "digest": profile_digest,
            "experimental": True,
            "hostSdkSpecific": True,
            "portable": False,
            "productReady": False,
        },
        "mode": "experimental-csharp-fact-only",
        "source": {
            "root": "source",
            "digest": records_digest(records),
            "logicalId": LOGICAL_SOURCE_ROOT,
            "sourceRole": "snapshot-copy-not-target",
            "mutationAllowed": False,
            "externalSourcePathPersisted": False,
        },
        "inputs": {"preflight": OUTPUTS["preflight"], "intakeReceipt": OUTPUTS["intakeReceipt"]},
        "outputs": OUTPUTS,
        "mapping": {"status": "fact-only-no-intent-mapping", "intentUnitMappingCreated": False},
        "authority": AUTHORITY,
    }


def copy_snapshot(source_root: Path, workspace_source: Path, records: list[dict[str, str]]) -> None:
    source_root = source_root.resolve(strict=True)
    for record in records:
        relative = Path(record["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ExperimentalWorkspaceError(f"unsafe C# source record path: {record['path']}")
        source = resolved_source_path(source_root / relative, source_root, relative)
        if not source.is_file():
            raise ExperimentalWorkspaceError(f"C# source record must resolve to a file: {record['path']}")
        destination = workspace_source / record["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def validate_workspace(workspace: Path) -> tuple[dict[str, Any], dict[str, Path], dict[str, Any]]:
    workspace = workspace.resolve()
    manifest = read_json_object(workspace / WORKSPACE_FILE)
    if manifest.get("artifactRole") != WORKSPACE_ROLE or manifest.get("schemaVersion") != WORKSPACE_SCHEMA_VERSION:
        raise ExperimentalWorkspaceError("wrong experimental C# workspace role or schema version")
    if manifest.get("mode") != "experimental-csharp-fact-only":
        raise ExperimentalWorkspaceError("workspace mode must remain experimental-csharp-fact-only")
    if manifest.get("authority") != AUTHORITY:
        raise ExperimentalWorkspaceError("workspace authority must remain the experimental fact-only boundary")
    if manifest.get("mapping") != {"status": "fact-only-no-intent-mapping", "intentUnitMappingCreated": False}:
        raise ExperimentalWorkspaceError("workspace must remain fact-only without Intent Unit mapping")

    profile = manifest.get("profile")
    if not isinstance(profile, dict):
        raise ExperimentalWorkspaceError("workspace profile must be an object")
    profile_path = contained_path(workspace, str(profile.get("path", "")))
    if profile.get("id") != PROFILE_ID or profile.get("digest") != digest_bytes(profile_path.read_bytes()):
        raise ExperimentalWorkspaceError("workspace profile identity or digest is invalid")
    _, expected_profile_digest = declared_profile(profile_path, require_canonical_path=False)
    if profile["digest"] != expected_profile_digest:
        raise ExperimentalWorkspaceError("workspace profile digest must match the declared host-SDK profile")
    if profile != {
        "id": PROFILE_ID,
        "path": PROFILE_COPY,
        "digest": profile["digest"],
        "experimental": True,
        "hostSdkSpecific": True,
        "portable": False,
        "productReady": False,
    }:
        raise ExperimentalWorkspaceError("workspace profile boundary is invalid")

    source = manifest.get("source")
    if not isinstance(source, dict):
        raise ExperimentalWorkspaceError("workspace source must be an object")
    source_root = contained_path(workspace, str(source.get("root", "")))
    records = csharp_source_records(source_root)
    if source != {
        "root": "source",
        "digest": records_digest(records),
        "logicalId": LOGICAL_SOURCE_ROOT,
        "sourceRole": "snapshot-copy-not-target",
        "mutationAllowed": False,
        "externalSourcePathPersisted": False,
    }:
        raise ExperimentalWorkspaceError("workspace C# source provenance is invalid")

    outputs = manifest.get("outputs")
    if outputs != OUTPUTS or manifest.get("inputs") != {"preflight": OUTPUTS["preflight"], "intakeReceipt": OUTPUTS["intakeReceipt"]}:
        raise ExperimentalWorkspaceError("workspace inputs or outputs are invalid")
    paths = {"sourceRoot": source_root, "profile": profile_path}
    for key, value in OUTPUTS.items():
        paths[key] = contained_path(workspace, value, artifact=True)

    preflight = read_json_object(paths["preflight"])
    if (
        preflight.get("artifactRole") != "intentgraph-experimental-csharp-host-sdk-preflight-report"
        or preflight.get("result") != "pass"
        or preflight.get("profile", {}).get("id") != PROFILE_ID
        or preflight.get("profile", {}).get("portable") is not False
        or preflight.get("authority") != PREFLIGHT_AUTHORITY
    ):
        raise ExperimentalWorkspaceError("workspace preflight evidence is invalid")

    receipt = read_json_object(paths["intakeReceipt"])
    expected_receipt = intake_receipt(records, str(profile["digest"]))
    if receipt != expected_receipt:
        raise ExperimentalWorkspaceError("workspace intake receipt does not match snapshot source evidence")

    facts = read_json_object(paths["codeFacts"])
    try:
        fact_summary = validate_facts(
            facts,
            {record["path"]: record["sha256"] for record in records},
            LOGICAL_SOURCE_ROOT,
            expected_scope=FACT_SCOPE,
            expected_profile_id=FACT_PROFILE_ID,
        )
    except ProbeError as error:
        raise ExperimentalWorkspaceError(f"workspace code facts are invalid: {error}") from error
    extraction = read_json_object(paths["extractionReport"])
    if extraction != {
        "artifactRole": "intentgraph-experimental-csharp-fact-extraction-report",
        "status": "intentgraph-experimental-csharp-fact-extraction-passed",
        "scope": "p9.10-experimental-csharp-snapshot-workspace",
        "result": "pass",
        "profileId": PROFILE_ID,
        "logicalSourceRoot": LOGICAL_SOURCE_ROOT,
        "sourceDigestBefore": records_digest(records),
        "sourceDigestAfter": records_digest(records),
        "repeatFactsByteIdentical": True,
        "factDigest": digest_bytes(paths["codeFacts"].read_bytes()),
        "summary": fact_summary,
        "authority": {
            "externalSourceMutation": False,
            "targetRepositoryMutation": False,
            "targetBuildExecuted": False,
            "targetRestoreExecuted": False,
            "targetLaunchExecuted": False,
            "packageDependencyAdded": False,
            "externalPackageRestoreExecuted": False,
            "localAdapterProjectRestoreExecuted": True,
            "localAdapterRestorePackageSources": "empty",
            "networkRequired": False,
            "automaticCodeApplication": False,
            "intentUnitMappingCreated": False,
            "igdProductizationClaimed": False,
        },
    }:
        raise ExperimentalWorkspaceError("workspace C# extraction evidence is invalid")
    return manifest, paths, fact_summary


def initialize_workspace(workspace: Path, external_source_root: Path, profile_path: Path) -> dict[str, Any]:
    workspace = workspace.resolve()
    if workspace.exists():
        raise ExperimentalWorkspaceError("experimental C# workspace must not exist before initialization")
    try:
        invalid_source_root = not external_source_root.is_dir() or is_reparse_point(external_source_root)
    except OSError:
        invalid_source_root = True
    if invalid_source_root:
        raise ExperimentalWorkspaceError("external C# source root must be an existing non-symlink directory")
    external_source_root = external_source_root.resolve(strict=True)
    if is_within(workspace, external_source_root) or is_within(external_source_root, workspace):
        raise ExperimentalWorkspaceError("external C# source root and workspace must not overlap")
    profile, profile_digest = declared_profile(profile_path, require_canonical_path=True)
    try:
        preflight = preflight_profile(PROFILE_PATH)
    except PreflightError as error:
        raise ExperimentalWorkspaceError(f"experimental C# host-SDK preflight failed: {error}") from error
    before_records = csharp_source_records(external_source_root)
    try:
        workspace.mkdir(parents=True, exist_ok=False)
        workspace_source = workspace / "source"
        copy_snapshot(external_source_root, workspace_source, before_records)
        after_records = csharp_source_records(external_source_root)
        copied_records = csharp_source_records(workspace_source)
        if after_records != before_records:
            raise ExperimentalWorkspaceError("external C# source changed during snapshot intake")
        if copied_records != before_records:
            raise ExperimentalWorkspaceError("workspace C# snapshot does not match external source evidence")
        profile_copy = workspace / PROFILE_COPY
        profile_copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROFILE_PATH, profile_copy)
        if digest_bytes(profile_copy.read_bytes()) != profile_digest:
            raise ExperimentalWorkspaceError("workspace profile copy digest does not match declared profile")
        write_json(workspace / OUTPUTS["preflight"], preflight)
        write_json(workspace / OUTPUTS["intakeReceipt"], intake_receipt(before_records, profile_digest))
        manifest = manifest_for(before_records, profile_digest)
        write_json(workspace / WORKSPACE_FILE, manifest)

        with tempfile.TemporaryDirectory(prefix="p9.10-csharp-workspace-") as temporary:
            temporary_root = Path(temporary)
            assembly = build_probe(temporary_root)
            first_facts = temporary_root / "first-facts.json"
            repeat_facts = temporary_root / "repeat-facts.json"
            first = invoke_probe(
                assembly,
                workspace_source,
                LOGICAL_SOURCE_ROOT,
                first_facts,
                artifact_scope=FACT_SCOPE,
                profile_id=FACT_PROFILE_ID,
            )
            second = invoke_probe(
                assembly,
                workspace_source,
                LOGICAL_SOURCE_ROOT,
                repeat_facts,
                artifact_scope=FACT_SCOPE,
                profile_id=FACT_PROFILE_ID,
            )
            if first.returncode != 0 or second.returncode != 0:
                raise ExperimentalWorkspaceError("experimental C# snapshot extraction failed")
            if first_facts.read_bytes() != repeat_facts.read_bytes():
                raise ExperimentalWorkspaceError("experimental C# snapshot extraction was not byte-identical")
            shutil.copy2(first_facts, workspace / OUTPUTS["codeFacts"])
        facts = read_json_object(workspace / OUTPUTS["codeFacts"])
        fact_summary = validate_facts(
            facts,
            {record["path"]: record["sha256"] for record in before_records},
            LOGICAL_SOURCE_ROOT,
            expected_scope=FACT_SCOPE,
            expected_profile_id=FACT_PROFILE_ID,
        )
        extraction = {
            "artifactRole": "intentgraph-experimental-csharp-fact-extraction-report",
            "status": "intentgraph-experimental-csharp-fact-extraction-passed",
            "scope": "p9.10-experimental-csharp-snapshot-workspace",
            "result": "pass",
            "profileId": PROFILE_ID,
            "logicalSourceRoot": LOGICAL_SOURCE_ROOT,
            "sourceDigestBefore": records_digest(before_records),
            "sourceDigestAfter": records_digest(csharp_source_records(workspace_source)),
            "repeatFactsByteIdentical": True,
            "factDigest": digest_bytes((workspace / OUTPUTS["codeFacts"]).read_bytes()),
            "summary": fact_summary,
            "authority": {
                "externalSourceMutation": False,
                "targetRepositoryMutation": False,
                "targetBuildExecuted": False,
                "targetRestoreExecuted": False,
                "targetLaunchExecuted": False,
                "packageDependencyAdded": False,
                "externalPackageRestoreExecuted": False,
                "localAdapterProjectRestoreExecuted": True,
                "localAdapterRestorePackageSources": "empty",
                "networkRequired": False,
                "automaticCodeApplication": False,
                "intentUnitMappingCreated": False,
                "igdProductizationClaimed": False,
            },
        }
        write_json(workspace / OUTPUTS["extractionReport"], extraction)
        _, paths, validated_summary = validate_workspace(workspace)
        validation = {
            "artifactRole": "intentgraph-experimental-csharp-fact-workspace-validation-report",
            "status": "intentgraph-experimental-csharp-fact-workspace-validation-passed",
            "scope": "p9.10-experimental-csharp-snapshot-workspace",
            "result": "pass",
            "profileId": PROFILE_ID,
            "logicalSourceRoot": LOGICAL_SOURCE_ROOT,
            "sourceDigest": manifest["source"]["digest"],
            "summary": validated_summary,
            "sourcePathPersisted": False,
            "factOnly": True,
            "authority": AUTHORITY,
        }
        write_json(paths["workspaceValidation"], validation)
        return {
            "result": "pass",
            "command": "init-experimental-csharp",
            "workspaceRole": WORKSPACE_ROLE,
            "profile": PROFILE_ID,
            "logicalSourceRoot": LOGICAL_SOURCE_ROOT,
            "sourceDigest": manifest["source"]["digest"],
            "sourceFileCount": len(before_records),
            "externalSourceMutated": False,
            "externalSourcePathPersisted": False,
            "factOnly": True,
            "outputs": {key: path.relative_to(workspace).as_posix() for key, path in paths.items() if key in OUTPUTS},
            "authority": AUTHORITY,
        }
    except Exception:
        if workspace.exists():
            shutil.rmtree(workspace)
        raise


def validate_command(workspace: Path) -> dict[str, Any]:
    manifest, paths, summary = validate_workspace(workspace.resolve())
    return {
        "result": "pass",
        "command": "validate-experimental-csharp",
        "workspaceRole": manifest["artifactRole"],
        "profile": manifest["profile"]["id"],
        "logicalSourceRoot": manifest["source"]["logicalId"],
        "sourceDigest": manifest["source"]["digest"],
        "factOnly": True,
        "summary": summary,
        "outputs": {key: path.relative_to(workspace.resolve()).as_posix() for key, path in paths.items() if key in OUTPUTS},
        "authority": manifest["authority"],
    }
