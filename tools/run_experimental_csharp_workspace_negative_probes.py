"""Run repeatable P9.10 experimental C# fact-workspace positive and negative probes."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable
from unittest.mock import patch

import experimental_csharp_workspace as workspace_module


ROOT = Path(__file__).resolve().parents[1]
FACADE = ROOT / "tools" / "intentgraph.py"
PROFILE = ROOT / "docs" / "examples" / "profiles" / "experimental-host-sdk-csharp-syntax.profile.json"
SAMPLE_SOURCE = """using System;

namespace Probe;

public sealed class Sample
{
    private readonly int _value = 1;

    public int Value => _value;

    public Sample()
    {
    }

    public void Print()
    {
        Console.WriteLine(Value);
    }
}
"""


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_source(root: Path, content: str = SAMPLE_SOURCE) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "Sample.cs").write_text(content, encoding="utf-8", newline="\n")
    return root


def run_init(workspace: Path, source_root: Path, profile: Path = PROFILE) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(FACADE),
            "init-experimental-csharp",
            "--workspace",
            str(workspace),
            "--source-root",
            str(source_root),
            "--profile",
            str(profile),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def run_validate(workspace: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(FACADE), "validate-experimental-csharp", "--workspace", str(workspace)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def artifact_hashes(workspace: Path) -> dict[str, str]:
    paths = [
        "intentgraph.workspace.json",
        "source/Sample.cs",
        "profiles/experimental-host-sdk-csharp-syntax.profile.json",
        "artifacts/host-sdk-preflight.json",
        "artifacts/external-source-intake-receipt.json",
        "artifacts/code-facts.json",
        "artifacts/csharp-extraction-report.json",
        "artifacts/fact-workspace-validation.json",
    ]
    return {value: workspace_module.digest_bytes((workspace / value).read_bytes()) for value in paths}


def append_process_probe(
    probes: list[dict[str, Any]],
    identifier: str,
    expected_error: str,
    completed: subprocess.CompletedProcess[str],
    workspace: Path | None = None,
) -> None:
    probes.append(
        {
            "id": identifier,
            "expectedError": expected_error,
            "exitCode": completed.returncode,
            "workspaceAbsentAfterFailure": None if workspace is None else not workspace.exists(),
            "expectedFailureObserved": completed.returncode != 0 and expected_error in completed.stderr,
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    temp_parent = ROOT / ".tmp"
    temp_parent.mkdir(exist_ok=True)
    probes: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="p9.10-csharp-workspace-negative-", dir=temp_parent) as temporary:
        root = Path(temporary)
        source = write_source(root / "source")
        first_workspace = root / "first-workspace"
        second_workspace = root / "second-workspace"
        first = run_init(first_workspace, source)
        second = run_init(second_workspace, source)
        first_validation = run_validate(first_workspace)
        second_validation = run_validate(second_workspace)
        if (
            first.returncode != 0
            or second.returncode != 0
            or first_validation.returncode != 0
            or second_validation.returncode != 0
            or artifact_hashes(first_workspace) != artifact_hashes(second_workspace)
        ):
            raise SystemExit("P9.10 positive C# workspace baseline did not pass deterministically")
        if str(source.resolve()).lower() in (first_workspace / "intentgraph.workspace.json").read_text(encoding="utf-8").lower():
            raise SystemExit("P9.10 workspace persisted an external source path")

        source_file = root / "source-file.cs"
        source_file.write_text(SAMPLE_SOURCE, encoding="utf-8", newline="\n")
        append_process_probe(
            probes,
            "external-source-root-is-file",
            "external C# source root must be an existing non-symlink directory",
            run_init(root / "file-workspace", source_file),
            root / "file-workspace",
        )
        empty = root / "empty-source"
        empty.mkdir()
        (empty / "readme.txt").write_text("not C#\n", encoding="utf-8", newline="\n")
        append_process_probe(
            probes,
            "external-source-root-has-no-csharp",
            "external C# source root must contain at least one C# file",
            run_init(root / "empty-workspace", empty),
            root / "empty-workspace",
        )
        existing = root / "existing-workspace"
        existing.mkdir()
        append_process_probe(
            probes,
            "workspace-already-exists",
            "experimental C# workspace must not exist before initialization",
            run_init(existing, source),
            existing,
        )
        append_process_probe(
            probes,
            "workspace-overlaps-source",
            "external C# source root and workspace must not overlap",
            run_init(source / "nested-workspace", source),
            source / "nested-workspace",
        )
        copied_profile = root / "copied-profile.json"
        copied_profile.write_bytes(PROFILE.read_bytes())
        append_process_probe(
            probes,
            "undeclared-profile-path",
            "experimental C# workspace must use the declared host-SDK profile path",
            run_init(root / "wrong-profile-workspace", source, copied_profile),
            root / "wrong-profile-workspace",
        )

        tampered_receipt = root / "tampered-receipt-workspace"
        if run_init(tampered_receipt, source).returncode != 0:
            raise SystemExit("tampered receipt setup failed")
        receipt_path = tampered_receipt / "artifacts" / "external-source-intake-receipt.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["externalSourcePathPersisted"] = True
        write_json(receipt_path, receipt)
        append_process_probe(
            probes,
            "external-source-path-persisted",
            "workspace intake receipt does not match snapshot source evidence",
            run_validate(tampered_receipt),
        )

        source_text_workspace = root / "source-text-workspace"
        if run_init(source_text_workspace, source).returncode != 0:
            raise SystemExit("source text setup failed")
        facts_path = source_text_workspace / "artifacts" / "code-facts.json"
        facts = json.loads(facts_path.read_text(encoding="utf-8"))
        facts["facts"][0]["sourceText"] = "must-not-persist"
        write_json(facts_path, facts)
        append_process_probe(
            probes,
            "persisted-source-text",
            "must not persist source text",
            run_validate(source_text_workspace),
        )

        semantic_workspace = root / "semantic-resolution-workspace"
        if run_init(semantic_workspace, source).returncode != 0:
            raise SystemExit("semantic resolution setup failed")
        semantic_facts_path = semantic_workspace / "artifacts" / "code-facts.json"
        semantic_facts = json.loads(semantic_facts_path.read_text(encoding="utf-8"))
        semantic_facts["extractor"]["semanticResolution"] = True
        write_json(semantic_facts_path, semantic_facts)
        append_process_probe(
            probes,
            "semantic-resolution-claimed",
            "extractor.semanticResolution must be False",
            run_validate(semantic_workspace),
        )

        escape_workspace = root / "escape-workspace"
        if run_init(escape_workspace, source).returncode != 0:
            raise SystemExit("path escape setup failed")
        manifest_path = escape_workspace / "intentgraph.workspace.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["outputs"]["codeFacts"] = "../escape.json"
        write_json(manifest_path, manifest)
        append_process_probe(
            probes,
            "workspace-output-path-escape",
            "workspace inputs or outputs are invalid",
            run_validate(escape_workspace),
        )

        mutation_source = write_source(root / "mutation-source")
        mutation_workspace = root / "mutation-workspace"
        original_copy = workspace_module.copy_snapshot

        def copy_then_mutate(source_root: Path, workspace_source: Path, records: list[dict[str, str]]) -> None:
            original_copy(source_root, workspace_source, records)
            (source_root / "Sample.cs").write_text(SAMPLE_SOURCE + "\n// changed after copy\n", encoding="utf-8", newline="\n")

        mutation_error = ""
        with patch.object(workspace_module, "copy_snapshot", side_effect=copy_then_mutate):
            try:
                workspace_module.initialize_workspace(mutation_workspace, mutation_source, PROFILE)
            except workspace_module.ExperimentalWorkspaceError as error:
                mutation_error = str(error)
        probes.append(
            {
                "id": "external-source-changed-during-snapshot",
                "expectedError": "external C# source changed during snapshot intake",
                "workspaceAbsentAfterFailure": not mutation_workspace.exists(),
                "expectedFailureObserved": "external C# source changed during snapshot intake" in mutation_error and not mutation_workspace.exists(),
            }
        )

    passed = all(item["expectedFailureObserved"] for item in probes)
    report = {
        "artifactRole": "intentgraph-experimental-csharp-fact-workspace-negative-probes-report",
        "status": "intentgraph-experimental-csharp-fact-workspace-negative-probes-passed" if passed else "intentgraph-experimental-csharp-fact-workspace-negative-probes-failed",
        "scope": "p9.10-experimental-csharp-snapshot-workspace-negative-probes",
        "result": "pass" if passed else "fail",
        "positiveBaselinePassed": True,
        "repeatWorkspaceArtifactsByteIdentical": True,
        "externalSourcePathPersisted": False,
        "probeCount": len(probes),
        "probes": probes,
        "authority": {
            "externalSourceMutation": False,
            "targetRepositoryMutation": False,
            "targetBuildExecuted": False,
            "packageDependencyAdded": False,
            "externalPackageRestoreExecuted": False,
            "localAdapterProjectRestoreExecuted": True,
            "localAdapterRestorePackageSources": "empty",
            "networkRequired": False,
            "automaticCodeApplication": False,
            "intentUnitMappingCreated": False,
        },
    }
    write_json(args.out, report)
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
