"""Run repeatable P9.12 fact-workbench positive and negative probes."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable

from experimental_csharp_workspace import PROFILE_PATH, initialize_workspace
from emit_experimental_csharp_fact_workbench import (
    FactWorkbenchError,
    build_projection,
    emit_workbench,
    output_paths,
    relative_file_records,
    validate_output,
    validate_projection,
)


ROOT = Path(__file__).resolve().parents[1]
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
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_source(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "Sample.cs").write_text(SAMPLE_SOURCE, encoding="utf-8", newline="\n")


def mutate_json(path: Path, mutate: Callable[[dict[str, Any]], None]) -> None:
    value = read_json(path)
    mutate(value)
    write_json(path, value)


def clone_workspace(source: Path, target: Path) -> None:
    shutil.copytree(source, target)


def append_probe(probes: list[dict[str, Any]], identifier: str, expected: str, action: Callable[[], None], output: Path | None = None) -> None:
    actual = ""
    try:
        action()
    except FactWorkbenchError as error:
        actual = str(error)
    probes.append(
        {
            "id": identifier,
            "expectedError": expected,
            "actualError": actual,
            "outputAbsentAfterFailure": None if output is None else not output.exists(),
            "expectedFailureObserved": expected in actual,
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    temp_parent = ROOT / ".tmp"
    temp_parent.mkdir(exist_ok=True)
    probes: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="p9.12-fact-workbench-negative-", dir=temp_parent) as temporary:
        root = Path(temporary)
        source = root / "source"
        write_source(source)
        base_workspace = root / "workspace"
        initialize_workspace(base_workspace, source, PROFILE_PATH)
        first_output = root / "first-output"
        second_output = root / "second-output"
        emit_workbench(base_workspace, first_output)
        emit_workbench(base_workspace, second_output)
        if relative_file_records(first_output) != relative_file_records(second_output):
            raise SystemExit("P9.12 fixed-input outputs are not byte-identical")
        before_workspace = relative_file_records(base_workspace)
        if before_workspace != relative_file_records(base_workspace):
            raise SystemExit("P9.12 baseline changed the input workspace")

        wrong_profile = root / "wrong-profile-workspace"
        clone_workspace(base_workspace, wrong_profile)
        mutate_json(wrong_profile / "intentgraph.workspace.json", lambda value: value["profile"].update({"id": "wrong-profile"}))
        append_probe(probes, "wrong-workspace-profile", "validated experimental C# workspace required", lambda: emit_workbench(wrong_profile, root / "wrong-profile-output"), root / "wrong-profile-output")

        source_text = root / "source-text-workspace"
        clone_workspace(base_workspace, source_text)
        mutate_json(source_text / "artifacts" / "code-facts.json", lambda value: value["facts"][0].update({"sourceText": "forbidden"}))
        append_probe(probes, "persisted-source-text", "validated experimental C# workspace required", lambda: emit_workbench(source_text, root / "source-text-output"), root / "source-text-output")

        semantic = root / "semantic-workspace"
        clone_workspace(base_workspace, semantic)
        mutate_json(semantic / "artifacts" / "code-facts.json", lambda value: value["extractor"].update({"semanticResolution": True}))
        append_probe(probes, "semantic-resolution-promoted", "validated experimental C# workspace required", lambda: emit_workbench(semantic, root / "semantic-output"), root / "semantic-output")

        unknown_kind = root / "unknown-kind-workspace"
        clone_workspace(base_workspace, unknown_kind)
        mutate_json(unknown_kind / "artifacts" / "code-facts.json", lambda value: value["facts"][0].update({"kind": "unknown"}))
        append_probe(probes, "unknown-fact-kind", "validated experimental C# workspace required", lambda: emit_workbench(unknown_kind, root / "unknown-kind-output"), root / "unknown-kind-output")

        unresolved_edge = root / "unresolved-edge-workspace"
        clone_workspace(base_workspace, unresolved_edge)
        mutate_json(unresolved_edge / "artifacts" / "code-facts.json", lambda value: value["relations"][0].update({"to": "fact.missing"}))
        append_probe(probes, "unresolved-edge-endpoint", "validated experimental C# workspace required", lambda: emit_workbench(unresolved_edge, root / "unresolved-edge-output"), root / "unresolved-edge-output")

        physical_path = root / "physical-path-workspace"
        clone_workspace(base_workspace, physical_path)
        mutate_json(physical_path / "artifacts" / "code-facts.json", lambda value: value["facts"][0].update({"sourceFile": "C:/outside/Sample.cs"}))
        append_probe(probes, "physical-source-path", "validated experimental C# workspace required", lambda: emit_workbench(physical_path, root / "physical-path-output"), root / "physical-path-output")

        append_probe(probes, "output-already-exists", "workbench output directory must not exist", lambda: emit_workbench(base_workspace, first_output), first_output)
        append_probe(probes, "output-overlaps-workspace", "workbench output directory must not overlap the input workspace", lambda: emit_workbench(base_workspace, base_workspace / "output"), base_workspace / "output")

        projection, _, workspace_before = build_projection(base_workspace)
        tampered_output = root / "tampered-html-output"
        emit_workbench(base_workspace, tampered_output)
        html_path = output_paths(tampered_output)["index"]
        html_path.write_text(html_path.read_text(encoding="utf-8") + "\n<script src=\"https://example.invalid/x.js\"></script>\n", encoding="utf-8", newline="\n")
        validation = validate_output(tampered_output, base_workspace, projection, workspace_before)
        probes.append(
            {
                "id": "external-runtime-url",
                "expectedError": "HTML contains forbidden token: https://",
                "actualError": "; ".join(validation["errors"]),
                "outputAbsentAfterFailure": None,
                "expectedFailureObserved": "HTML contains forbidden token: https://" in validation["errors"],
            }
        )

        unavailable_projection = json.loads(json.dumps(projection))
        unavailable_projection["unavailable"].pop("codeDiff")
        unavailable_errors = validate_projection(unavailable_projection)
        probes.append(
            {
                "id": "missing-unavailable-state",
                "expectedError": "unavailable semantic/change state is incomplete",
                "actualError": "; ".join(unavailable_errors),
                "outputAbsentAfterFailure": None,
                "expectedFailureObserved": "unavailable semantic/change state is incomplete" in unavailable_errors,
            }
        )

        mutation_projection = json.loads(json.dumps(projection))
        mutation_projection["authority"]["graphMutationFromUi"] = True
        mutation_errors = validate_projection(mutation_projection)
        probes.append(
            {
                "id": "graph-mutation-authority-promoted",
                "expectedError": "workbench authority must remain fact-only and read-only",
                "actualError": "; ".join(mutation_errors),
                "outputAbsentAfterFailure": None,
                "expectedFailureObserved": "workbench authority must remain fact-only and read-only" in mutation_errors,
            }
        )

    passed = all(item["expectedFailureObserved"] for item in probes)
    report = {
        "artifactRole": "intentgraph-experimental-csharp-fact-workbench-negative-probes-report",
        "status": "intentgraph-experimental-csharp-fact-workbench-negative-probes-passed" if passed else "intentgraph-experimental-csharp-fact-workbench-negative-probes-failed",
        "scope": "p9.12-experimental-csharp-fact-only-workbench-negative-probes",
        "result": "pass" if passed else "fail",
        "positiveBaselinePassed": True,
        "repeatOutputsByteIdentical": True,
        "inputWorkspaceMutated": False,
        "probeCount": len(probes),
        "probes": probes,
    }
    write_json(args.out, report)
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
