"""Emit read-only WindowsUtility Intent mapping hypotheses from inventory."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


REPORT_VERSION = "0.1.0"
TARGET_ID = "WindowsUtility"


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def git_status(target: Path) -> str:
    result = subprocess.run(
        ["git", "status", "--short", "--branch"],
        cwd=target,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return result.stdout.strip()


def project_paths(inventory: dict[str, Any]) -> list[str]:
    return [record["path"] for record in inventory["inventory"].get("projectFiles", [])]


def paths_containing(paths: list[str], *needles: str) -> list[str]:
    lowered = [(path, path.lower()) for path in paths]
    return [path for path, lower in lowered if any(needle.lower() in lower for needle in needles)]


def build_hypothesis(inventory: dict[str, Any], target: Path, before_status: str, after_status: str) -> dict[str, Any]:
    projects = project_paths(inventory)
    source_count = inventory["inventory"].get("sourceFileCount", 0)
    units = [
        {
            "id": "unit.windowsutility.shell-workspace",
            "kind": "application-shell",
            "title": "WindowsUtility WPF shell and workspace",
            "mappingStatus": "hypothesis",
            "confidence": "inferred-from-project-structure",
            "codeSurfaceRefs": paths_containing(projects, "WindowsUtility.App", "WindowsUtility.Shell"),
            "evidenceGaps": ["screenshot evidence", "shell navigation smoke test"],
            "authorityGaps": ["user acceptance for shell/workspace mapping"]
        },
        {
            "id": "unit.windowsutility.core-services",
            "kind": "core-service-boundary",
            "title": "Core abstractions, services, and native boundary",
            "mappingStatus": "hypothesis",
            "confidence": "inferred-from-project-structure",
            "codeSurfaceRefs": paths_containing(projects, "Core.Abstractions", "Core.Services", "Core.Native"),
            "evidenceGaps": ["service contract tests", "native boundary smoke evidence"],
            "authorityGaps": ["maintainer review for native boundary risk"]
        },
        {
            "id": "unit.windowsutility.utility-modules",
            "kind": "feature-module-family",
            "title": "Feature modules for printer, diagnostics, dump, firmware, network, serial, and config utilities",
            "mappingStatus": "hypothesis",
            "confidence": "inferred-from-project-structure",
            "codeSurfaceRefs": paths_containing(projects, "WindowsUtility.Modules."),
            "evidenceGaps": ["module-level smoke tests", "legacy parity evidence"],
            "authorityGaps": ["module owner review", "hardware-aware test approval"]
        },
        {
            "id": "unit.windowsutility.tests-and-smoke",
            "kind": "verification-surface",
            "title": "Tests, diagnostics, and hardware smoke surfaces",
            "mappingStatus": "hypothesis",
            "confidence": "inferred-from-project-structure",
            "codeSurfaceRefs": paths_containing(projects, "Test", "Diagnostics", "HardwareSmoke"),
            "evidenceGaps": ["repeatable build/test log", "hardware unavailable fallback evidence"],
            "authorityGaps": ["test maintainer acceptance"]
        }
    ]
    ambiguity = [
        {
            "id": "ambiguity.windowsutility.module-boundaries",
            "summary": "Project names reveal module families but do not prove runtime ownership or user-facing feature boundaries.",
            "resolutionRequiredBeforeMutation": True
        },
        {
            "id": "ambiguity.windowsutility.hardware-coupling",
            "summary": "Hardware-aware modules may require real devices, mocks, or explicit unavailable-hardware evidence.",
            "resolutionRequiredBeforeMutation": True
        }
    ]
    unchanged = before_status == after_status and inventory.get("result") == "pass"
    return {
        "artifactRole": "intentgraph-windowsutility-mapping-hypothesis",
        "status": "intentgraph-windowsutility-mapping-hypothesis-passed" if unchanged else "intentgraph-windowsutility-mapping-hypothesis-failed",
        "scope": "p7.2-windowsutility-readonly-intent-mapping-hypothesis",
        "reportVersion": REPORT_VERSION,
        "target": {
            "id": TARGET_ID,
            "path": str(target),
            "writeAuthorized": False,
            "gitStatusBefore": before_status,
            "gitStatusAfter": after_status,
            "gitStatusUnchanged": before_status == after_status
        },
        "sourceInventory": {
            "selectedFileCount": inventory["inventory"].get("selectedFileCount"),
            "projectFileCount": inventory["inventory"].get("projectFileCount"),
            "sourceFileCount": source_count,
            "docFileCount": inventory["inventory"].get("docFileCount")
        },
        "intentUnitHypotheses": units,
        "ambiguityRecords": ambiguity,
        "evidenceGapSummary": {
            "gapCount": sum(len(unit["evidenceGaps"]) for unit in units),
            "requiresBuildTestEvidence": True,
            "requiresUiOrScreenshotEvidence": True,
            "requiresHardwareAwareEvidence": True
        },
        "authorityGapSummary": {
            "gapCount": sum(len(unit["authorityGaps"]) for unit in units),
            "requiresHumanReview": True,
            "requiresHardwareAwareApproval": True
        },
        "recommendedBoundedAdoptionSlice": {
            "id": "P7.3",
            "name": "WindowsUtility Read-Only Adoption Boundary Review and Productization Gate",
            "reason": "target remains read-only until repo state is reconciled; productization should stay blocked"
        },
        "claimScope": {
            "readOnlyTarget": True,
            "artifactsWrittenInsideTarget": False,
            "targetSourceMutated": False,
            "intentMappingsAccepted": False,
            "aiAuthorityGranted": False,
            "productReadinessClaimed": False
        },
        "result": "pass" if unchanged else "fail",
        "errors": [] if unchanged else ["target status changed or inventory did not pass"]
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# P7.2 WindowsUtility Read-Only Intent Mapping Hypothesis",
        "",
        f"Result: `{report['result']}`",
        f"Target: `{report['target']['path']}`",
        "",
        "## Hypotheses",
        "",
    ]
    for unit in report["intentUnitHypotheses"]:
        lines.append(f"### {unit['id']}")
        lines.append("")
        lines.append(f"- title: {unit['title']}")
        lines.append(f"- kind: `{unit['kind']}`")
        lines.append(f"- mapping status: `{unit['mappingStatus']}`")
        lines.append(f"- code surfaces: {len(unit['codeSurfaceRefs'])}")
        lines.append("")
    lines.extend(["## Ambiguity", ""])
    for item in report["ambiguityRecords"]:
        lines.append(f"- `{item['id']}`: {item['summary']}")
    lines.extend(["", "## Boundary", "", "- read-only target: true", "- mappings accepted: false", "- source mutated: false", ""])
    return "\n".join(lines)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit WindowsUtility mapping hypotheses from read-only inventory.")
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--markdown", required=True, type=Path)
    args = parser.parse_args()
    target = args.target.resolve()
    before_status = git_status(target)
    inventory = read_json(args.inventory)
    after_status = git_status(target)
    report = build_hypothesis(inventory, target, before_status, after_status)
    write_json(args.out, report)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(render_markdown(report), encoding="utf-8")
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
