"""Run negative probes for the static WindowsUtility workbench export."""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable

from emit_windowsutility_static_workbench_export import canonical_pretty, validate_export


GOOD_EXPORT = Path("generated/product-surfaces/windowsutility-shell-workspace-static-workbench/p8.31")
TARGET_ROOT = Path("C:/Users/ytkim/Desktop/kyt_work/WindowsUtility")
DEFAULT_SCOPE = "p8.31-static-local-workbench-export-negative-probes"
DEFAULT_VALIDATION_SCOPE = "p8.31-static-local-workbench-export-validation"
DEFAULT_WORK_ITEM = "P8.31 Static Local Workbench Export Prototype"


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(canonical_pretty(data), encoding="utf-8")


def copy_export(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst)


def remove_manifest(root: Path) -> None:
    (root / "manifest.json").unlink()


def stale_source_digest(root: Path) -> None:
    manifest = read_json(root / "manifest.json")
    manifest["sourceArtifacts"][0]["sha256"] = "sha256:0000"
    write_json(root / "manifest.json", manifest)


def remove_screenshot(root: Path) -> None:
    (root / "assets" / "screenshot.png").unlink()


def productization_true(root: Path) -> None:
    projection = read_json(root / "projection.json")
    projection["claimScope"]["productizationClaimed"] = True
    write_json(root / "projection.json", projection)


def target_write_true(root: Path) -> None:
    projection = read_json(root / "projection.json")
    projection["authorityBoundary"]["targetWritesAuthorized"] = True
    write_json(root / "projection.json", projection)


def proposal_applied(root: Path) -> None:
    projection = read_json(root / "projection.json")
    projection["proposal"]["applicationStatus"] = "applied"
    write_json(root / "projection.json", projection)


def ai_authority_true(root: Path) -> None:
    projection = read_json(root / "projection.json")
    projection["claimScope"]["aiAuthorityGranted"] = True
    write_json(root / "projection.json", projection)


def require_network(root: Path) -> None:
    index = root / "index.html"
    index.write_text(index.read_text(encoding="utf-8") + "\n<script src=\"https://example.invalid/tool.js\"></script>\n", encoding="utf-8")


def target_dirty(root: Path) -> None:
    projection = read_json(root / "projection.json")
    projection["target"]["current"]["status"] = "## main...origin/main\n M src/WindowsUtility.App/WindowsUtility.App.csproj"
    write_json(root / "projection.json", projection)


def remove_selection_records(root: Path) -> None:
    projection = read_json(root / "projection.json")
    projection["selectionRecords"] = []
    write_json(root / "projection.json", projection)


PROBES: list[tuple[str, Callable[[Path], None], str]] = [
    ("missing-manifest", remove_manifest, "missing required file: manifest.json"),
    ("stale-source-digest", stale_source_digest, "manifest source digest mismatch"),
    ("missing-screenshot-asset", remove_screenshot, "missing required file: assets/screenshot.png"),
    ("productization-authority-true", productization_true, "projection claimScope.productizationClaimed must be false"),
    ("target-write-authority-true", target_write_true, "projection authorityBoundary.targetWritesAuthorized must be false"),
    ("proposal-applied-true", proposal_applied, "projection proposal must remain not-applied"),
    ("ai-authority-true", ai_authority_true, "projection claimScope.aiAuthorityGranted must be false"),
    ("network-dependency-required", require_network, "index must not require network or dynamic imports"),
    ("target-dirty", target_dirty, "projection target current status must be clean/aligned"),
    ("selection-records-missing", remove_selection_records, "projection selection records missing"),
]


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run static WindowsUtility workbench export negative probes.")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--export-dir", default=GOOD_EXPORT, type=Path)
    parser.add_argument("--target-root", default=TARGET_ROOT, type=Path)
    parser.add_argument("--scope", default=DEFAULT_SCOPE)
    parser.add_argument("--validation-scope", default=DEFAULT_VALIDATION_SCOPE)
    parser.add_argument("--work-item", default=DEFAULT_WORK_ITEM)
    parser.add_argument("--require-orientation-markers", action="store_true")
    args = parser.parse_args()

    positive = validate_export(
        args.export_dir,
        args.target_root,
        args.validation_scope,
        args.work_item,
        args.require_orientation_markers,
    )
    probes: list[dict[str, Any]] = []

    with TemporaryDirectory(prefix="intentgraph-static-workbench-export-probes-") as tmp:
        tmp_root = Path(tmp)
        for probe_id, mutate, expected in PROBES:
            candidate = tmp_root / probe_id
            copy_export(args.export_dir, candidate)
            mutate(candidate)
            report = validate_export(
                candidate,
                args.target_root,
                args.validation_scope,
                args.work_item,
                args.require_orientation_markers,
            )
            errors = report.get("errors", [])
            expected_observed = report.get("result") == "fail" and any(expected in error for error in errors)
            probes.append(
                {
                    "id": probe_id,
                    "result": report.get("result"),
                    "expectedFailureObserved": expected_observed,
                    "expectedErrorSubstring": expected,
                    "actualErrors": errors,
                }
            )

    all_passed = positive.get("result") == "pass" and all(probe["expectedFailureObserved"] for probe in probes)
    report = {
        "artifactRole": "intentgraph-static-local-workbench-export-negative-probes-report",
        "status": "intentgraph-static-local-workbench-export-negative-probes-passed" if all_passed else "intentgraph-static-local-workbench-export-negative-probes-failed",
        "scope": args.scope,
        "workItem": args.work_item,
        "result": "pass" if all_passed else "fail",
        "positiveBaseline": {
            "exportDir": args.export_dir.as_posix(),
            "rerunResult": positive.get("result"),
            "errors": positive.get("errors", []),
        },
        "probeCount": len(probes),
        "probes": probes,
        "authorizations": {
            "sourceEditsAuthorized": False,
            "proposalApplicationAuthorized": False,
            "targetWritesAuthorized": False,
            "aiAuthorityPromoted": False,
            "hardwareActionsAuthorized": False,
            "packagingAuthorized": False,
            "releaseAuthorized": False,
            "productizationAuthorized": False,
            "badFixturesCommitted": False,
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(canonical_pretty(report), encoding="utf-8")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
