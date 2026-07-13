"""Run repeatable negative probes for declared C# project semantic foundations."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any, Callable

from experimental_csharp_project import (
    PROJECT_FILE,
    ProjectWorkspaceError,
    initialize_project,
    read_json,
    record_semantic_foundation,
)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def run_probe(
    snapshot: Path,
    foundation: Path,
    probe_id: str,
    mutate: Callable[[dict[str, Any]], None],
    expected: str,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="p9.17-foundation-negative-") as temporary:
        root = Path(temporary)
        workspace = root / "project"
        foundation_copy = root / "foundation.json"
        initialize_project(snapshot, workspace, "foundation-probe", "Foundation probe")
        candidate = read_json(foundation)
        mutate(candidate)
        write_json(foundation_copy, candidate)
        before = (workspace / PROJECT_FILE).read_bytes()
        try:
            record_semantic_foundation(workspace, foundation_copy)
        except ProjectWorkspaceError as error:
            message = str(error)
            return {
                "id": probe_id,
                "expectedError": expected,
                "actualError": message,
                "expectedFailureObserved": expected in message,
                "projectStateUnchanged": before == (workspace / PROJECT_FILE).read_bytes(),
            }
        return {
            "id": probe_id,
            "expectedError": expected,
            "actualError": "semantic foundation unexpectedly recorded",
            "expectedFailureObserved": False,
            "projectStateUnchanged": before == (workspace / PROJECT_FILE).read_bytes(),
        }


def repeated_foundation_probe(snapshot: Path, foundation: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="p9.17-foundation-repeat-") as temporary:
        root = Path(temporary)
        workspace = root / "project"
        initialize_project(snapshot, workspace, "foundation-repeat", "Foundation repeat")
        record_semantic_foundation(workspace, foundation)
        before = (workspace / PROJECT_FILE).read_bytes()
        try:
            record_semantic_foundation(workspace, foundation)
        except ProjectWorkspaceError as error:
            message = str(error)
            return {
                "id": "repeated-foundation-record",
                "expectedError": "already recorded",
                "actualError": message,
                "expectedFailureObserved": "already recorded" in message,
                "projectStateUnchanged": before == (workspace / PROJECT_FILE).read_bytes(),
            }
        return {
            "id": "repeated-foundation-record",
            "expectedError": "already recorded",
            "actualError": "semantic foundation was replaced unexpectedly",
            "expectedFailureObserved": False,
            "projectStateUnchanged": before == (workspace / PROJECT_FILE).read_bytes(),
        }


def run(snapshot: Path, foundation: Path, output: Path) -> dict[str, Any]:
    snapshot = snapshot.resolve()
    foundation = foundation.resolve()
    probes = [
        run_probe(snapshot, foundation, "wrong-foundation-role", lambda value: value.__setitem__("artifactRole", "wrong-role"), "role, status, or scope is invalid"),
        run_probe(snapshot, foundation, "automatic-intent-creation", lambda value: value["authority"].__setitem__("automaticIntentCreation", True), "authority must remain declarative"),
        run_probe(snapshot, foundation, "unknown-code-capsule", lambda value: value["capabilities"][0].__setitem__("codeCapsuleLabels", ["WindowsUtility.Unknown"]), "code capsule references are invalid"),
        run_probe(snapshot, foundation, "physical-document-path", lambda value: value["sourceDocuments"][0].__setitem__("logicalPath", "C:\\unsafe\\document.md"), "must not persist a physical path"),
        run_probe(snapshot, foundation, "unknown-source-document", lambda value: value["goals"][0].__setitem__("sourceDocumentIds", ["document.missing"]), "source document references are invalid"),
        repeated_foundation_probe(snapshot, foundation),
    ]
    result = "pass" if all(probe["expectedFailureObserved"] and probe["projectStateUnchanged"] for probe in probes) else "fail"
    report = {
        "artifactRole": "intentgraph-experimental-csharp-semantic-foundation-negative-probes-report",
        "status": "intentgraph-experimental-csharp-semantic-foundation-negative-probes-" + result,
        "scope": "p9.17-declared-semantic-foundation",
        "result": result,
        "probeCount": len(probes),
        "probes": probes,
        "snapshotWorkspaceMutation": False,
        "targetRepositoryMutation": False,
        "automaticIntentCreation": False,
        "automaticMapping": False,
        "automaticCodeApplication": False,
        "networkRequired": False,
    }
    write_json(output, report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-workspace", required=True, type=Path)
    parser.add_argument("--foundation", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = run(args.snapshot_workspace, args.foundation, args.out)
    except ProjectWorkspaceError as error:
        print(f"error: {error}")
        return 2
    print(json.dumps({"result": report["result"], "probeCount": report["probeCount"]}, ensure_ascii=True))
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
