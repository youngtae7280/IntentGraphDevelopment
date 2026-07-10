"""Emit a read-only WindowsUtility adoption inventory outside the target repo."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


REPORT_VERSION = "0.1.0"
TARGET_ID = "WindowsUtility"
SELECTED_EXTENSIONS = {".sln", ".csproj", ".cs", ".xaml", ".md", ".props", ".targets"}
EXCLUDED_PARTS = {".git", ".vs", ".devview", "bin", "obj"}


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


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


def git_rev(target: Path, ref: str) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", ref],
        cwd=target,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def is_excluded(path: Path, target: Path) -> bool:
    rel_parts = path.relative_to(target).parts
    return any(part in EXCLUDED_PARTS for part in rel_parts)


def collect_files(target: Path) -> list[Path]:
    files: list[Path] = []
    for path in target.rglob("*"):
        if not path.is_file() or is_excluded(path, target):
            continue
        if path.suffix.lower() in SELECTED_EXTENSIONS:
            files.append(path)
    return sorted(files, key=lambda item: item.relative_to(target).as_posix().lower())


def summarize_inventory(target: Path) -> dict[str, Any]:
    selected = collect_files(target)
    records: list[dict[str, Any]] = []
    for path in selected:
        rel = path.relative_to(target).as_posix()
        records.append(
            {
                "path": rel,
                "extension": path.suffix.lower(),
                "byteLength": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    project_files = [record for record in records if record["extension"] in {".sln", ".csproj"}]
    source_files = [record for record in records if record["extension"] in {".cs", ".xaml"}]
    docs = [record for record in records if record["extension"] == ".md"]
    top_dirs = sorted({Path(record["path"]).parts[0] for record in records if len(Path(record["path"]).parts) > 1})
    return {
        "selectedFileCount": len(records),
        "projectFileCount": len(project_files),
        "sourceFileCount": len(source_files),
        "docFileCount": len(docs),
        "topLevelDirectories": top_dirs,
        "projectFiles": project_files,
        "sampleSourceFiles": source_files[:40],
        "sourceDigests": {record["path"]: record["sha256"] for record in records},
    }


def build_inventory(target: Path, status_before: str, status_after: str, before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    unchanged = before["sourceDigests"] == after["sourceDigests"] and status_before == status_after
    return {
        "artifactRole": "intentgraph-windowsutility-readonly-inventory",
        "status": "intentgraph-windowsutility-readonly-inventory-passed" if unchanged else "intentgraph-windowsutility-readonly-inventory-failed",
        "scope": "p7.1-windowsutility-readonly-retrofit-inventory",
        "reportVersion": REPORT_VERSION,
        "target": {
            "id": TARGET_ID,
            "path": str(target),
            "head": git_rev(target, "HEAD"),
            "originMain": git_rev(target, "origin/main"),
            "writeAuthorized": False,
        },
        "gitStatus": {
            "before": status_before,
            "after": status_after,
            "unchanged": status_before == status_after,
        },
        "inventory": after,
        "candidateAdoptionScope": {
            "taskClass": "read-only retrofit inventory for a bounded WPF/MVVM utility slice",
            "candidateSurfaces": [
                "solution and project structure",
                "app entry and WPF window/view boundaries",
                "view-model and service boundaries",
                "test and smoke harnesses",
                "native interop boundaries",
                "documentation and existing DevView artifacts"
            ],
            "nextSlice": "P7.2 WindowsUtility Read-Only Intent Mapping Hypothesis"
        },
        "claimScope": {
            "readOnlyTarget": True,
            "artifactsWrittenInsideTarget": False,
            "targetSourceMutated": False,
            "unboundedRetrofitClaimed": False,
            "aiCodeApplied": False,
            "productReadinessClaimed": False,
        },
        "result": "pass" if unchanged else "fail",
        "errors": [] if unchanged else ["target git status or selected file digests changed during inventory"],
    }


def render_markdown(inventory: dict[str, Any]) -> str:
    target = inventory["target"]
    inv = inventory["inventory"]
    lines = [
        "# P7.1 WindowsUtility Read-Only Inventory",
        "",
        f"Target: `{target['path']}`",
        f"Result: `{inventory['result']}`",
        "",
        "## Target Boundary",
        "",
        f"- write authorized: `{target['writeAuthorized']}`",
        f"- git status unchanged: `{inventory['gitStatus']['unchanged']}`",
        f"- artifacts written inside target: `{inventory['claimScope']['artifactsWrittenInsideTarget']}`",
        "",
        "## Inventory Summary",
        "",
        f"- selected files: {inv['selectedFileCount']}",
        f"- project files: {inv['projectFileCount']}",
        f"- source files: {inv['sourceFileCount']}",
        f"- docs: {inv['docFileCount']}",
        "",
        "## Project Files",
        "",
    ]
    for record in inv["projectFiles"]:
        lines.append(f"- `{record['path']}`")
    lines.extend(["", "## Next Slice", "", "- P7.2 WindowsUtility Read-Only Intent Mapping Hypothesis", ""])
    return "\n".join(lines)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit read-only WindowsUtility inventory outside target repo.")
    parser.add_argument("--target", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--markdown", required=True, type=Path)
    args = parser.parse_args()
    target = args.target.resolve()
    status_before = git_status(target)
    before = summarize_inventory(target)
    after = summarize_inventory(target)
    status_after = git_status(target)
    inventory = build_inventory(target, status_before, status_after, before, after)
    write_json(args.out, inventory)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.write_text(render_markdown(inventory), encoding="utf-8")
    return 0 if inventory["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
