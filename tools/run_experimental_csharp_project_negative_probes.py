"""Run repeatable negative probes for the P9.13 C# semantic-overlay project workspace."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any, Callable

from experimental_csharp_project import (
    PROJECT_AUTHORITY,
    PROJECT_FILE,
    ProjectWorkspaceError,
    add_mapping_candidate,
    add_work_request,
    emit_project_workbench,
    initialize_project,
    read_json,
    validate_project_workspace,
    write_json,
)


def write_report(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def first_type_fact(snapshot: Path) -> str:
    facts = read_json(snapshot / "artifacts" / "code-facts.json").get("facts", [])
    for fact in facts:
        if isinstance(fact, dict) and fact.get("kind") == "type" and isinstance(fact.get("id"), str):
            return fact["id"]
    raise ProjectWorkspaceError("negative probe fixture needs one type fact")


def prepare(snapshot: Path, root: Path) -> Path:
    workspace = root / "project"
    initialize_project(snapshot, workspace, "negative-probe-project", "Negative probe project")
    add_work_request(workspace, "startup-inspection", "Inspect startup", "Inspect a C# startup fact without proposing a source change.")
    add_mapping_candidate(workspace, "startup-inspection", [first_type_fact(snapshot)], "Declared fixture mapping candidate.")
    return workspace


def mutate_state(workspace: Path, mutate: Callable[[dict[str, Any]], None]) -> None:
    state = read_json(workspace / PROJECT_FILE)
    mutate(state)
    write_json(workspace / PROJECT_FILE, state)


def run_probe(snapshot: Path, probe_id: str, mutate: Callable[[dict[str, Any]], None], expected: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="p9.13-negative-") as temporary:
        workspace = prepare(snapshot, Path(temporary))
        mutate_state(workspace, mutate)
        try:
            validate_project_workspace(workspace)
        except ProjectWorkspaceError as error:
            message = str(error)
            return {"id": probe_id, "expectedError": expected, "actualError": message, "expectedFailureObserved": expected in message}
        return {"id": probe_id, "expectedError": expected, "actualError": "validation unexpectedly passed", "expectedFailureObserved": False}


def output_collision_probe(snapshot: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="p9.13-output-collision-") as temporary:
        root = Path(temporary)
        workspace = prepare(snapshot, root)
        output = root / "output"
        emit_project_workbench(workspace, output)
        try:
            emit_project_workbench(workspace, output)
        except ProjectWorkspaceError as error:
            message = str(error)
            return {"id": "existing-output-collision", "expectedError": "output directory must not exist", "actualError": message, "expectedFailureObserved": "output directory must not exist" in message}
        return {"id": "existing-output-collision", "expectedError": "output directory must not exist", "actualError": "emitter unexpectedly overwrote output", "expectedFailureObserved": False}


def run(snapshot: Path, output: Path) -> dict[str, Any]:
    snapshot = snapshot.resolve()
    probes = [
        run_probe(snapshot, "wrong-project-state-role", lambda state: state.__setitem__("artifactRole", "wrong-role"), "role, schema version, or scope is invalid"),
        run_probe(snapshot, "physical-path-leak", lambda state: state["project"].__setitem__("title", "C:\\unsafe\\project"), "must not persist a physical path"),
        run_probe(snapshot, "unknown-code-fact", lambda state: state["mappings"][0].__setitem__("codeFactIds", ["csharp.type.missing"]), "code fact references must resolve"),
        run_probe(snapshot, "mapping-status-mismatch", lambda state: state["workItems"][0].__setitem__("mappingStatus", "unmapped"), "mapping status must agree"),
        run_probe(snapshot, "target-write-authority", lambda state: state.__setitem__("authority", {**PROJECT_AUTHORITY, "targetRepositoryMutation": True}), "authority boundary is invalid"),
        run_probe(snapshot, "automatic-code-application", lambda state: state.__setitem__("authority", {**PROJECT_AUTHORITY, "automaticCodeApplication": True}), "authority boundary is invalid"),
        run_probe(snapshot, "malformed-proposal-index", lambda state: state["changeProposals"].append({"id": "proposal.unsafe"}), "change proposal index record fields are invalid"),
        output_collision_probe(snapshot),
    ]
    result = "pass" if all(item["expectedFailureObserved"] for item in probes) else "fail"
    report = {
        "artifactRole": "intentgraph-experimental-csharp-project-negative-probes-report",
        "status": "intentgraph-experimental-csharp-project-negative-probes-" + result,
        "scope": "p9.13-experimental-csharp-project-overlay-workbench",
        "result": result,
        "probeCount": len(probes),
        "probes": probes,
        "snapshotWorkspaceMutation": False,
        "targetRepositoryMutation": False,
        "networkRequired": False,
        "authority": PROJECT_AUTHORITY,
    }
    write_report(output, report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-workspace", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = run(args.snapshot_workspace, args.out)
    except ProjectWorkspaceError as error:
        print(f"error: {error}")
        return 2
    print(json.dumps({"result": report["result"], "probeCount": report["probeCount"]}, ensure_ascii=True))
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
