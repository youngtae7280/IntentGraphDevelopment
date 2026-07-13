"""Run repeatable negative probes for diff-backed guided C# proposals."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any, Callable

from experimental_csharp_project import (
    ProjectWorkspaceError,
    add_mapping_candidate,
    add_work_request,
    draft_change_proposal_from_mapping,
    initialize_project,
    validate_project_workspace,
)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def source_line(workspace: Path, fact: dict[str, Any], line_number: int) -> str:
    source = workspace / "snapshot" / "source" / Path(fact["sourceFile"])
    return source.read_text(encoding="utf-8-sig").splitlines()[line_number - 1]


def insertion_hunk(workspace: Path, fact: dict[str, Any], *, line_number: int | None = None) -> str:
    target_line = line_number or fact["sourceLocation"]["lineStart"]
    existing = source_line(workspace, fact, target_line)
    return f"@@ -{target_line},1 +{target_line},2 @@\n+// IGD review-only proposed change.\n {existing}"


def draft_values(code_diffs: list[dict[str, str]], **changes: str) -> dict[str, Any]:
    values: dict[str, Any] = {
        "proposal_id": "diff-guided-proposal",
        "work_id": "diff-guided-work",
        "title": "Diff-backed guided proposal",
        "summary": "Record a snapshot-checked code change for graph and code review.",
        "verification_kind": "local-review",
        "verification_summary": "Review the proposed code fragment before any source action.",
        "evidence_kind": "review-note",
        "evidence_summary": "Record review evidence without claiming execution.",
        "code_diffs": code_diffs,
    }
    values.update(changes)
    return values


def probe(identifier: str, expected: str, operation: Callable[[], Any]) -> dict[str, Any]:
    try:
        operation()
    except ProjectWorkspaceError as error:
        return {"id": identifier, "expectedFailureObserved": expected in str(error), "error": str(error)}
    return {"id": identifier, "expectedFailureObserved": False, "error": "operation unexpectedly succeeded"}


def run(snapshot: Path, output: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="p9.27-diff-guided-negative-") as temporary:
        workspace = Path(temporary) / "project"
        initialize_project(snapshot, workspace, "diff-guided-probe", "Diff-guided proposal probes")
        before_state, before_manifest, _, before_data = validate_project_workspace(workspace)
        method_facts = [
            fact
            for fact in before_data["facts"]["facts"]
            if isinstance(fact, dict) and fact.get("kind") == "method"
        ]
        mapped_fact, context_fact, other_fact = method_facts[:3]
        add_work_request(workspace, "diff-guided-work", "Diff-guided work", "Prepare one review-only code change.")
        add_mapping_candidate(workspace, "diff-guided-work", [mapped_fact["id"], context_fact["id"]], "Selected one changed fact plus one mapped context fact for diff-backed proposal validation.")
        valid_diff = {"codeFactId": mapped_fact["id"], "unifiedDiff": insertion_hunk(workspace, mapped_fact)}
        other_diff = {"codeFactId": other_fact["id"], "unifiedDiff": insertion_hunk(workspace, other_fact)}
        mapped_line = mapped_fact["sourceLocation"]["lineStart"]
        mapped_source = source_line(workspace, mapped_fact, mapped_line)
        first_source = source_line(workspace, mapped_fact, 1)

        probes = [
            probe(
                "rejects-empty-code-diff-list",
                "between one and 32 mapped fact hunks",
                lambda: draft_change_proposal_from_mapping(workspace, **draft_values([])),
            ),
            probe(
                "rejects-unmapped-code-fact",
                "must target a mapped code fact",
                lambda: draft_change_proposal_from_mapping(workspace, **draft_values([other_diff])),
            ),
            probe(
                "rejects-duplicate-code-fact-diffs",
                "must target unique mapped code facts",
                lambda: draft_change_proposal_from_mapping(workspace, **draft_values([valid_diff, valid_diff])),
            ),
            probe(
                "rejects-malformed-hunk-header",
                "unified diff is invalid",
                lambda: draft_change_proposal_from_mapping(
                    workspace,
                    **draft_values([{"codeFactId": mapped_fact["id"], "unifiedDiff": "not-a-hunk"}]),
                ),
            ),
            probe(
                "rejects-stale-source-context",
                "does not match snapshot source",
                lambda: draft_change_proposal_from_mapping(
                    workspace,
                    **draft_values([{"codeFactId": mapped_fact["id"], "unifiedDiff": f"@@ -{mapped_line},1 +{mapped_line},2 @@\n+// proposed\n stale source line"}]),
                ),
            ),
            probe(
                "rejects-hunk-outside-code-fact-range",
                "must overlap its mapped code fact",
                lambda: draft_change_proposal_from_mapping(
                    workspace,
                    **draft_values([{"codeFactId": mapped_fact["id"], "unifiedDiff": f"@@ -1,1 +1,2 @@\n+// proposed\n {first_source}"}]),
                ),
            ),
            probe(
                "rejects-no-op-diff",
                "must describe a real source change",
                lambda: draft_change_proposal_from_mapping(
                    workspace,
                    **draft_values([{"codeFactId": mapped_fact["id"], "unifiedDiff": f"@@ -{mapped_line},1 +{mapped_line},1 @@\n-{mapped_source}\n+{mapped_source}"}]),
                ),
            ),
            probe(
                "rejects-inconsistent-hunk-count",
                "hunk counts are invalid",
                lambda: draft_change_proposal_from_mapping(
                    workspace,
                    **draft_values([{"codeFactId": mapped_fact["id"], "unifiedDiff": f"@@ -{mapped_line},2 +{mapped_line},2 @@\n-{mapped_source}\n+changed"}]),
                ),
            ),
        ]
        positive = draft_change_proposal_from_mapping(workspace, **draft_values([valid_diff]))
        after_state, after_manifest, _, after_data = validate_project_workspace(workspace)
        recorded = after_data["proposals"][0]
        positive_valid = (
            positive["codeDiffCount"] == 1
            and positive["diffBackedGuidedProposal"] is True
            and recorded["graphDelta"]["changedNodeIds"] == [mapped_fact["id"]]
        )
        passed = all(item["expectedFailureObserved"] for item in probes) and positive_valid
        report = {
            "artifactRole": "intentgraph-experimental-csharp-diff-guided-proposal-negative-probes-report",
            "status": "intentgraph-experimental-csharp-diff-guided-proposal-negative-probes-" + ("pass" if passed else "fail"),
            "scope": "p9.27-diff-backed-guided-proposal-boundary",
            "result": "pass" if passed else "fail",
            "probeCount": len(probes),
            "probes": probes,
            "positiveBaseline": {
                "result": positive["result"],
                "proposalId": positive["proposalId"],
                "codeDiffCount": positive["codeDiffCount"],
                "diffBackedGuidedProposal": positive["diffBackedGuidedProposal"],
                "recordedCodeFactId": recorded["codeDiffs"][0]["codeFactId"],
                "changedNodeIds": recorded["graphDelta"]["changedNodeIds"],
                "mappedContextExcludedFromChanges": context_fact["id"] not in recorded["graphDelta"]["changedNodeIds"],
                "beforeSourceDigest": recorded["codeDiffs"][0]["beforeSourceDigest"],
            },
            "snapshotProvenanceUnchanged": before_manifest["source"] == after_manifest["source"] and before_state["project"] == after_state["project"],
            "targetRepositoryMutation": False,
            "automaticCodeApplication": False,
            "graphMutationApplied": False,
            "networkRequired": False,
        }
    write_json(output, report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-workspace", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args.snapshot_workspace.resolve(), args.out.resolve())
    print(json.dumps({"result": report["result"], "probeCount": report["probeCount"]}, ensure_ascii=True))
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
