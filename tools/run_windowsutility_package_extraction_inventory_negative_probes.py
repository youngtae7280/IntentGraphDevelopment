"""Run negative probes for the package extraction inventory verifier."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Callable

from run_windowsutility_package_extraction_inventory_tool_readiness import (
    AUTHORIZATION_TOKEN,
    VERIFY_TOOL,
    create_sources,
    create_synthetic_package,
)


WORK_ITEM = "P8.70 Packaged Artifact Extraction Inventory Negative Probes"
SCOPE = "p8.70-packaged-artifact-extraction-inventory-negative-probes"
DATE = "2026-07-10"
DEFAULT_OUT = Path("generated/windowsutility/package-artifact/p8.70/negative-probes-report.json")


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def mutate_json(path: Path, mutate: Callable[[dict[str, Any]], None]) -> None:
    data = read_json(path)
    mutate(data)
    write_json(path, data)


def remove_zip_entry(source: Path, removed_entry: str) -> None:
    target = source.with_suffix(".missing.zip")
    with zipfile.ZipFile(source, "r") as src, zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            if info.filename == removed_entry:
                continue
            dst.writestr(info, src.read(info.filename))
    shutil.move(str(target), source)


def add_zip_slip_entry(package: Path) -> None:
    with zipfile.ZipFile(package, "a", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("../escape.txt", b"must not escape sandbox\n")


def list_zip_entries(package: Path) -> list[str]:
    with zipfile.ZipFile(package, "r") as archive:
        return sorted(name for name in archive.namelist() if not name.endswith("/"))


def create_probe_inputs(root: Path) -> tuple[Path, Path, Path, Path, Path]:
    package = root / "synthetic-package.zip"
    manifest = root / "package-manifest.json"
    metadata_replay = root / "metadata-replay-report.json"
    extract_root = root / "extract-root"
    out = root / "report.json"
    names = create_synthetic_package(package)
    create_sources(package, manifest, metadata_replay, names)
    return package, manifest, metadata_replay, extract_root, out


def run_probe(
    probe_id: str,
    expected_error: str,
    mutate: Callable[[Path, Path, Path, Path], str],
    tmp_root: Path,
) -> dict[str, Any]:
    probe_root = tmp_root / probe_id
    probe_root.mkdir(parents=True, exist_ok=True)
    package, manifest, metadata_replay, extract_root, out = create_probe_inputs(probe_root)
    authorization_token = mutate(package, manifest, metadata_replay, extract_root)
    command = [
        sys.executable,
        str(VERIFY_TOOL),
        "--package",
        str(package),
        "--manifest",
        str(manifest),
        "--metadata-replay",
        str(metadata_replay),
        "--extract-root",
        str(extract_root),
        "--out",
        str(out),
        "--authorization-token",
        authorization_token,
        "--scope",
        SCOPE,
        "--verification-mode",
        "synthetic-negative-probe-only",
    ]
    completed = subprocess.run(command, check=False, text=True, capture_output=True)
    report_errors: list[str] = []
    package_extracted = False
    if out.exists():
        report = read_json(out)
        report_errors = [str(error) for error in report.get("errors", [])]
        package_extracted = report.get("boundary", {}).get("packageExtractionPerformed") is True
    observed = completed.returncode != 0 and any(expected_error in error for error in report_errors)
    return {
        "id": probe_id,
        "expectedError": expected_error,
        "exitCode": completed.returncode,
        "expectedFailureObserved": observed,
        "errors": report_errors,
        "packageExtractionPerformed": package_extracted,
    }


def build_report() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="intentgraph-p8.70-") as tmp:
        tmp_root = Path(tmp)
        probes = [
            run_probe(
                "missing-authorization-token",
                "missing accepted sandboxed extraction inventory authorization token",
                lambda _package, _manifest, _metadata, _extract_root: "",
                tmp_root,
            ),
            run_probe(
                "wrong-authorization-token",
                "missing accepted sandboxed extraction inventory authorization token",
                lambda _package, _manifest, _metadata, _extract_root: "accept",
                tmp_root,
            ),
            run_probe(
                "manifest-sha-mismatch",
                "manifest sha256 does not match package artifact",
                lambda _package, manifest, _metadata, _extract_root: (
                    mutate_json(manifest, lambda data: data["artifact"].__setitem__("sha256", "sha256:0000")),
                    AUTHORIZATION_TOKEN,
                )[1],
                tmp_root,
            ),
            run_probe(
                "metadata-replay-count-mismatch",
                "metadata replay fileCount does not match zip inventory",
                lambda _package, _manifest, metadata, _extract_root: (
                    mutate_json(metadata, lambda data: data["packageArtifactReplay"].__setitem__("fileCount", 1)),
                    AUTHORIZATION_TOKEN,
                )[1],
                tmp_root,
            ),
            run_probe(
                "package-not-zip",
                "package artifact is not a readable zip",
                lambda package, _manifest, _metadata, _extract_root: (
                    package.write_bytes(b"not a zip"),
                    AUTHORIZATION_TOKEN,
                )[1],
                tmp_root,
            ),
            run_probe(
                "missing-required-entry",
                "required package entry missing from zip inventory: SmartComm2.dll",
                lambda package, _manifest, _metadata, _extract_root: (
                    remove_zip_entry(package, "SmartComm2.dll"),
                    AUTHORIZATION_TOKEN,
                )[1],
                tmp_root,
            ),
            run_probe(
                "unsafe-zip-slip-entry",
                "unsafe zip entry path: ../escape.txt",
                lambda package, manifest, metadata, _extract_root: (
                    add_zip_slip_entry(package),
                    create_sources(package, manifest, metadata, list_zip_entries(package)),
                    AUTHORIZATION_TOKEN,
                )[2],
                tmp_root,
            ),
            run_probe(
                "non-empty-extract-root",
                "extract root must be empty before package extraction",
                lambda _package, _manifest, _metadata, extract_root: (
                    extract_root.mkdir(parents=True, exist_ok=True),
                    (extract_root / "existing.txt").write_text("existing", encoding="utf-8"),
                    AUTHORIZATION_TOKEN,
                )[2],
                tmp_root,
            ),
        ]

    result = "pass" if all(probe["expectedFailureObserved"] for probe in probes) else "fail"
    return {
        "artifactRole": "intentgraph-packaged-artifact-extraction-inventory-negative-probes-report",
        "status": "intentgraph-packaged-artifact-extraction-inventory-negative-probes-passed"
        if result == "pass"
        else "intentgraph-packaged-artifact-extraction-inventory-negative-probes-failed",
        "scope": SCOPE,
        "workItem": WORK_ITEM,
        "date": DATE,
        "result": result,
        "probeCount": len(probes),
        "probes": probes,
        "boundary": {
            "existingPackageExtractionPerformed": False,
            "syntheticPackageExtractionPerformedInPositivePath": False,
            "packagedExecutableLaunched": False,
            "packagedUiLaunched": False,
            "packagedUiScreenshotCaptured": False,
            "installerCreated": False,
            "artifactSigned": False,
            "credentialAccessed": False,
            "providerApiCalled": False,
            "releasePublished": False,
            "productizationClaimed": False,
        },
        "recommendedNextSlice": "P8.71 Packaged Artifact Verification Authorization Result Gate",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run P8.70 extraction inventory negative probes.")
    parser.add_argument("--out", default=DEFAULT_OUT, type=Path)
    args = parser.parse_args()
    report = build_report()
    write_json(args.out, report)
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
