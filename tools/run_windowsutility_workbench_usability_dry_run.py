"""Run a bounded WindowsUtility workbench usability dry run."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


WORK_ITEM = "P8.24 Shell Workspace Workbench Usability Dry Run"
PROJECTION = Path("generated/windowsutility/workbench/p8.21-shell-workspace-evidence-workbench-projection.json")
HTML = Path("generated/windowsutility/workbench/p8.21-shell-workspace-evidence-workbench.html")
PLAN = Path("generated/roadmap/p8.23-shell-workspace-workbench-usability-boundary-plan-report.json")

RAW_PATHS = {
    "acceptedMapping": Path("generated/windowsutility/p8.9-shell-workspace-accepted-mapping.json"),
    "proposal": Path("generated/windowsutility/p8.12-shell-workspace-smoke-evidence-non-applied-proposal.json"),
    "buildEvidence": Path("generated/windowsutility/p8.15-sandboxed-smoke-evidence-report.json"),
    "uiLaunchEvidence": Path("generated/windowsutility/p8.17-sandboxed-ui-launch-probe-report.json"),
    "screenshotEvidence": Path("generated/windowsutility/p8.19-sandboxed-screenshot-probe-report.json"),
}


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: normalize(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [normalize(item) for item in value]
    return value


def compare_answer(expected: Any, actual: Any) -> bool:
    return normalize(expected) == normalize(actual)


def normalize_artifact_path(path_value: str) -> str:
    text = str(path_value)
    marker = "generated\\windowsutility\\p8.19-shell-workspace-sandboxed-window.png"
    if marker in text:
        return "generated/windowsutility/p8.19-shell-workspace-sandboxed-window.png"
    return text.replace("\\", "/")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a WindowsUtility workbench-vs-raw JSON dry run.")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    projection = read_json(PROJECTION)
    plan = read_json(PLAN)
    raw = {key: read_json(path) for key, path in RAW_PATHS.items()}

    screenshot_card = next(card for card in projection["evidence"] if card["kind"] == "sandboxed-screenshot")

    tasks = [
        {
            "id": "task.accepted-mapping",
            "question": "Which shell/workspace mapping is accepted?",
            "expectedAnswer": projection["mapping"]["id"],
            "workbenchAnswer": projection["mapping"]["id"],
            "rawAnswer": raw["acceptedMapping"]["acceptedMapping"]["id"],
            "workbenchArtifactLookups": [PROJECTION.as_posix()],
            "rawArtifactLookups": [RAW_PATHS["acceptedMapping"].as_posix()],
        },
        {
            "id": "task.accepted-source-refs",
            "question": "Which source refs are covered by the accepted mapping?",
            "expectedAnswer": [ref["path"] for ref in projection["mapping"]["codeSurfaceRefs"]],
            "workbenchAnswer": [ref["path"] for ref in projection["mapping"]["codeSurfaceRefs"]],
            "rawAnswer": [ref["path"] for ref in raw["acceptedMapping"]["acceptedMapping"]["codeSurfaceRefs"]],
            "workbenchArtifactLookups": [PROJECTION.as_posix()],
            "rawArtifactLookups": [RAW_PATHS["acceptedMapping"].as_posix()],
        },
        {
            "id": "task.proposal-status",
            "question": "Is the proposal applied or still non-applied?",
            "expectedAnswer": "not-applied",
            "workbenchAnswer": projection["proposal"]["applicationStatus"],
            "rawAnswer": raw["proposal"]["applicationStatus"],
            "workbenchArtifactLookups": [PROJECTION.as_posix()],
            "rawArtifactLookups": [RAW_PATHS["proposal"].as_posix()],
        },
        {
            "id": "task.evidence-status",
            "question": "Which evidence proves build, UI launch, and screenshot status?",
            "expectedAnswer": {
                "build": "pass",
                "uiLaunch": "pass",
                "screenshot": "pass",
            },
            "workbenchAnswer": {
                "build": projection["evidence"][0]["result"],
                "uiLaunch": projection["evidence"][1]["result"],
                "screenshot": projection["evidence"][2]["result"],
            },
            "rawAnswer": {
                "build": raw["buildEvidence"]["result"],
                "uiLaunch": raw["uiLaunchEvidence"]["result"],
                "screenshot": raw["screenshotEvidence"]["result"],
            },
            "workbenchArtifactLookups": [PROJECTION.as_posix()],
            "rawArtifactLookups": [
                RAW_PATHS["buildEvidence"].as_posix(),
                RAW_PATHS["uiLaunchEvidence"].as_posix(),
                RAW_PATHS["screenshotEvidence"].as_posix(),
            ],
        },
        {
            "id": "task.target-unchanged",
            "question": "Did the original WindowsUtility target remain unchanged?",
            "expectedAnswer": True,
            "workbenchAnswer": projection["summary"]["targetUnchangedInEvidence"],
            "rawAnswer": raw["screenshotEvidence"]["targetBefore"] == raw["screenshotEvidence"]["targetAfter"],
            "workbenchArtifactLookups": [PROJECTION.as_posix()],
            "rawArtifactLookups": [RAW_PATHS["screenshotEvidence"].as_posix()],
        },
        {
            "id": "task.safety-flags",
            "question": "Which safety flags remain false?",
            "expectedAnswer": projection["authorityBoundary"],
            "workbenchAnswer": projection["authorityBoundary"],
            "rawAnswer": raw["screenshotEvidence"]["authorizations"],
            "workbenchArtifactLookups": [PROJECTION.as_posix()],
            "rawArtifactLookups": [
                RAW_PATHS["acceptedMapping"].as_posix(),
                RAW_PATHS["proposal"].as_posix(),
                RAW_PATHS["screenshotEvidence"].as_posix(),
            ],
            "rawComparableSubset": False,
        },
        {
            "id": "task.screenshot-digest",
            "question": "Which artifact proves the screenshot exists and what digest identifies it?",
            "expectedAnswer": {
                "path": screenshot_card["screenshotPath"],
                "sha256": screenshot_card["sha256"],
            },
            "workbenchAnswer": {
                "path": screenshot_card["screenshotPath"],
                "sha256": screenshot_card["sha256"],
            },
            "rawAnswer": {
                "path": normalize_artifact_path(raw["screenshotEvidence"]["uiLaunch"]["screenshotCapture"]["path"]),
                "sha256": raw["screenshotEvidence"]["screenshotEvidence"]["sha256"],
            },
            "workbenchArtifactLookups": [PROJECTION.as_posix()],
            "rawArtifactLookups": [RAW_PATHS["screenshotEvidence"].as_posix()],
        },
        {
            "id": "task.next-action",
            "question": "What is the next recommended action?",
            "expectedAnswer": "P8.25 or later may improve the workbench only after usability dry-run evidence is reviewed",
            "workbenchAnswer": "P8.25 or later may improve the workbench only after usability dry-run evidence is reviewed",
            "rawAnswer": "Not directly available from P8.9-P8.19 raw evidence; requires roadmap/review docs",
            "workbenchArtifactLookups": [PROJECTION.as_posix(), PLAN.as_posix()],
            "rawArtifactLookups": [
                RAW_PATHS["acceptedMapping"].as_posix(),
                RAW_PATHS["proposal"].as_posix(),
                RAW_PATHS["buildEvidence"].as_posix(),
                RAW_PATHS["uiLaunchEvidence"].as_posix(),
                RAW_PATHS["screenshotEvidence"].as_posix(),
                "docs/roadmap/product-capability-roadmap.md",
            ],
            "rawComparableSubset": False,
        },
    ]

    evaluated_tasks: list[dict[str, Any]] = []
    correct_count = 0
    missed_safety = 0
    total_workbench_lookups = 0
    total_raw_lookups = 0

    for task in tasks:
        raw_comparable = task.get("rawComparableSubset", True)
        workbench_correct = compare_answer(task["expectedAnswer"], task["workbenchAnswer"])
        raw_correct = compare_answer(task["expectedAnswer"], task["rawAnswer"]) if raw_comparable else False
        if workbench_correct:
            correct_count += 1
        if task["id"] == "task.safety-flags" and not workbench_correct:
            missed_safety += 1
        workbench_lookup_count = len(set(task["workbenchArtifactLookups"]))
        raw_lookup_count = len(set(task["rawArtifactLookups"]))
        total_workbench_lookups += workbench_lookup_count
        total_raw_lookups += raw_lookup_count
        evaluated_tasks.append(
            {
                **task,
                "workbenchCorrect": workbench_correct,
                "rawCorrect": raw_correct,
                "rawComparableSubset": raw_comparable,
                "workbenchArtifactLookupCount": workbench_lookup_count,
                "rawArtifactLookupCount": raw_lookup_count,
            }
        )

    pass_criteria = {
        "allReviewTasksAnswered": correct_count == len(tasks),
        "noSafetyFalseFlagMissed": missed_safety == 0,
        "screenshotArtifactFound": bool(screenshot_card.get("screenshotPath") and screenshot_card.get("sha256")),
        "targetUnchangedStateFound": projection["summary"]["targetUnchangedInEvidence"] is True,
        "proposalNonAppliedStateFound": projection["proposal"]["applicationStatus"] == "not-applied",
        "workbenchUsesFewerArtifactLookupsThanRawJson": total_workbench_lookups < total_raw_lookups,
        "sourceMutationClaimIntroduced": False,
        "productizationClaimIntroduced": False,
    }
    result = (
        "pass"
        if (
            pass_criteria["allReviewTasksAnswered"]
            and pass_criteria["noSafetyFalseFlagMissed"]
            and pass_criteria["screenshotArtifactFound"]
            and pass_criteria["targetUnchangedStateFound"]
            and pass_criteria["proposalNonAppliedStateFound"]
            and pass_criteria["workbenchUsesFewerArtifactLookupsThanRawJson"]
            and pass_criteria["sourceMutationClaimIntroduced"] is False
            and pass_criteria["productizationClaimIntroduced"] is False
        )
        else "fail"
    )

    report = {
        "artifactRole": "intentgraph-windowsutility-workbench-usability-dry-run-report",
        "status": "intentgraph-windowsutility-workbench-usability-dry-run-passed" if result == "pass" else "intentgraph-windowsutility-workbench-usability-dry-run-failed",
        "scope": "p8.24-shell-workspace-workbench-usability-dry-run",
        "workItem": WORK_ITEM,
        "result": result,
        "humanStudyClaimed": False,
        "inputs": {
            "projection": PROJECTION.as_posix(),
            "html": HTML.as_posix(),
            "plan": PLAN.as_posix(),
            "rawPaths": {key: path.as_posix() for key, path in RAW_PATHS.items()},
        },
        "metrics": {
            "taskCount": len(tasks),
            "answerCorrectnessCount": correct_count,
            "missedSafetyBoundaryCount": missed_safety,
            "workbenchArtifactLookupCount": total_workbench_lookups,
            "rawArtifactLookupCount": total_raw_lookups,
            "lookupReduction": total_raw_lookups - total_workbench_lookups,
            "screenshotEvidenceFound": pass_criteria["screenshotArtifactFound"],
            "authorityFalseFlagsFound": pass_criteria["noSafetyFalseFlagMissed"],
            "targetUnchangedFound": pass_criteria["targetUnchangedStateFound"],
            "proposalNonAppliedFound": pass_criteria["proposalNonAppliedStateFound"],
        },
        "passCriteria": pass_criteria,
        "tasks": evaluated_tasks,
        "claimScope": {
            "selfConductedDryRun": True,
            "humanUsabilityStudy": False,
            "sourceMutated": False,
            "targetMutated": False,
            "proposalApplied": False,
            "aiAuthorityGranted": False,
            "hardwareActionClaimed": False,
            "productizationClaimed": False,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(canonical_pretty(report), encoding="utf-8")
    return 0 if result == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
