"""Run repeatable negative probes for the bounded P9.6 C# syntax parser."""

from __future__ import annotations

import copy
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from run_windowsutility_csharp_syntax_probe import (
    ROOT,
    ProbeError,
    build_probe,
    invoke_probe,
    read_json,
    run_command,
    sha256_bytes,
    source_snapshot,
    validate_facts,
    write_json,
)


LOGICAL_ROOT = "intentgraph://probes/csharp-syntax/source"
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


def write_sample(root: Path, text: str = SAMPLE_SOURCE) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "Sample.cs").write_text(text, encoding="utf-8", newline="\n")
    return root


def probe_process(assembly: Path, source: Path, logical_root: str, output: Path) -> tuple[int, str]:
    completed = invoke_probe(assembly, source, logical_root, output)
    return completed.returncode, completed.stderr.strip()


def expect_process(probes: list[dict[str, Any]], identifier: str, expected_error: str, result: tuple[int, str]) -> None:
    exit_code, stderr = result
    probes.append(
        {
            "id": identifier,
            "expectedError": expected_error,
            "exitCode": exit_code,
            "expectedFailureObserved": exit_code != 0 and expected_error in stderr,
        }
    )


def expect_validation(probes: list[dict[str, Any]], identifier: str, expected_error: str, facts: dict[str, Any], snapshot: dict[str, str]) -> None:
    observed_error = ""
    try:
        validate_facts(facts, snapshot, LOGICAL_ROOT)
    except ProbeError as error:
        observed_error = str(error)
    probes.append(
        {
            "id": identifier,
            "expectedError": expected_error,
            "expectedFailureObserved": expected_error in observed_error,
        }
    )


def missing_roslyn_probe(temp_root: Path) -> tuple[int, str]:
    source = ROOT / "tools" / "csharp_syntax_probe"
    broken = temp_root / "broken-roslyn-probe"
    shutil.copytree(source, broken)
    project = broken / "IntentGraph.CSharpSyntaxProbe.csproj"
    project.write_text(
        project.read_text(encoding="utf-8").replace("Microsoft.CodeAnalysis.CSharp.dll", "Missing.CodeAnalysis.CSharp.dll"),
        encoding="utf-8",
        newline="\n",
    )
    environment = os.environ.copy()
    environment.update(
        {
            "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
            "NUGET_PACKAGES": str(temp_root / "missing-roslyn-nuget-packages"),
            "NUGET_HTTP_CACHE_PATH": str(temp_root / "missing-roslyn-nuget-http-cache"),
        }
    )
    restore = run_command(
        ["dotnet", "restore", str(project), "--configfile", str(broken / "NuGet.Config"), "--disable-parallel"],
        cwd=broken,
        env=environment,
    )
    if restore.returncode != 0:
        return restore.returncode, (restore.stderr + "\n" + restore.stdout).strip()
    completed = run_command(
        ["dotnet", "build", str(project), "--configuration", "Release", "--no-restore"],
        cwd=broken,
        env=environment,
    )
    detail = (completed.stderr + "\n" + completed.stdout).strip()
    return completed.returncode, detail


def main() -> int:
    output_parser = __import__("argparse").ArgumentParser(description=__doc__)
    output_parser.add_argument("--out", type=Path, required=True)
    args = output_parser.parse_args()
    probes: list[dict[str, Any]] = []
    temp_parent = ROOT / ".tmp"
    temp_parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="p9.6-csharp-negative-", dir=temp_parent) as temporary:
        temp_root = Path(temporary)
        assembly = build_probe(temp_root)
        sample = write_sample(temp_root / "sample")
        baseline_output = temp_root / "baseline.json"
        baseline_process = invoke_probe(assembly, sample, LOGICAL_ROOT, baseline_output)
        if baseline_process.returncode != 0:
            raise SystemExit(f"baseline C# syntax probe failed: {baseline_process.stderr.strip()}")
        baseline_facts = read_json(baseline_output)
        baseline_snapshot = source_snapshot(sample)
        validate_facts(baseline_facts, baseline_snapshot, LOGICAL_ROOT)

        expect_process(
            probes,
            "invalid-logical-source-root",
            "source root id must be an intentgraph:// logical identifier",
            probe_process(assembly, sample, "file://unsafe", temp_root / "invalid-logical.json"),
        )
        expect_process(
            probes,
            "output-inside-source-root",
            "output must not be written inside source root",
            probe_process(assembly, sample, LOGICAL_ROOT, sample / "facts.json"),
        )
        malformed = write_sample(temp_root / "malformed", "public sealed class Broken { public void M( { }\n")
        expect_process(
            probes,
            "malformed-csharp",
            "C# syntax errors in Sample.cs",
            probe_process(assembly, malformed, LOGICAL_ROOT, temp_root / "malformed.json"),
        )
        empty = temp_root / "empty"
        empty.mkdir()
        expect_process(
            probes,
            "empty-csharp-source-root",
            "no C# source files found under source root",
            probe_process(assembly, empty, LOGICAL_ROOT, temp_root / "empty.json"),
        )
        expect_process(
            probes,
            "missing-csharp-source-root",
            "source root must be an existing directory",
            probe_process(assembly, temp_root / "missing", LOGICAL_ROOT, temp_root / "missing.json"),
        )
        extra = run_command(
            [
                "dotnet",
                str(assembly),
                "--source-root",
                str(sample),
                "--source-root-id",
                LOGICAL_ROOT,
                "--out",
                str(temp_root / "extra.json"),
                "--unexpected",
                "value",
            ],
            cwd=assembly.parent,
        )
        expect_process(probes, "unexpected-parser-argument", "only --source-root, --source-root-id, --out, --artifact-scope, and --profile-id are allowed", (extra.returncode, extra.stderr.strip()))

        with_source_text = copy.deepcopy(baseline_facts)
        with_source_text["facts"][0]["sourceText"] = "must-not-persist"
        expect_validation(probes, "persisted-source-text", "must not persist source text", with_source_text, baseline_snapshot)
        with_target_syntax = copy.deepcopy(baseline_facts)
        with_target_syntax["facts"][0]["targetSyntax"] = "must-not-persist"
        expect_validation(probes, "persisted-target-syntax", "must not persist source text", with_target_syntax, baseline_snapshot)

        missing_roslyn_exit, missing_roslyn_detail = missing_roslyn_probe(temp_root)
        probes.append(
            {
                "id": "missing-roslyn-assembly",
                "expectedError": "isolated Roslyn build must fail when the CSharp assembly reference is missing",
                "exitCode": missing_roslyn_exit,
                "expectedFailureObserved": missing_roslyn_exit != 0 and "error" in missing_roslyn_detail.lower(),
            }
        )

    passed = all(item["expectedFailureObserved"] for item in probes)
    report = {
        "artifactRole": "intentgraph-csharp-syntax-negative-probes-report",
        "status": "intentgraph-csharp-syntax-negative-probes-passed" if passed else "intentgraph-csharp-syntax-negative-probes-failed",
        "scope": "p9.6-windowsutility-csharp-syntax-only-negative-probes",
        "result": "pass" if passed else "fail",
        "baseline": {
            "result": "pass",
            "sourceDigest": sha256_bytes(SAMPLE_SOURCE.encode("utf-8")),
            "factCount": len(baseline_facts["facts"]),
            "relationCount": len(baseline_facts["relations"]),
        },
        "probeCount": len(probes),
        "probes": probes,
        "authority": {
            "windowsUtilityRead": False,
            "targetRepositoryMutation": False,
            "targetBuildExecuted": False,
            "networkRequired": False,
            "automaticCodeApplication": False,
        },
    }
    write_json(args.out, report)
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
