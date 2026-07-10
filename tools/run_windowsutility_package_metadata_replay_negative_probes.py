"""Run negative probes for WindowsUtility package metadata replay verification."""

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


WORK_ITEM = "P8.67 Packaged Artifact Metadata Replay Negative Probes"
SCOPE = "p8.67-packaged-artifact-metadata-replay-negative-probes"
DATE = "2026-07-10"
DEFAULT_OUT = Path("generated/windowsutility/package-artifact/p8.67/negative-probes-report.json")
BASE_PACKAGE = Path(
    "generated/windowsutility/package-artifact/p8.55/windowsutility-shell-workspace-p8.55-sandbox-package.zip"
)
BASE_MANIFEST = Path("generated/windowsutility/package-artifact/p8.55/package-manifest.json")
BASE_BOUNDARY = Path("generated/roadmap/p8.56-packaged-artifact-verification-boundary-report.json")
VERIFY_TOOL = Path("tools/verify_windowsutility_package_metadata_replay.py")


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


def remove_zip_entry(source: Path, target: Path, removed_entry: str) -> None:
    with zipfile.ZipFile(source, "r") as src, zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            if info.filename == removed_entry:
                continue
            dst.writestr(info, src.read(info.filename))


def run_probe(
    probe_id: str,
    expected_error: str,
    mutate: Callable[[Path, Path, Path], None],
    tmp_root: Path,
) -> dict[str, Any]:
    package = tmp_root / probe_id / "package.zip"
    manifest = tmp_root / probe_id / "package-manifest.json"
    boundary = tmp_root / probe_id / "boundary.json"
    out = tmp_root / probe_id / "report.json"
    package.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(BASE_PACKAGE, package)
    shutil.copyfile(BASE_MANIFEST, manifest)
    shutil.copyfile(BASE_BOUNDARY, boundary)
    mutate(package, manifest, boundary)

    cmd = [
        sys.executable,
        str(VERIFY_TOOL),
        "--package",
        str(package),
        "--manifest",
        str(manifest),
        "--boundary",
        str(boundary),
        "--out",
        str(out),
    ]
    completed = subprocess.run(cmd, check=False, text=True, capture_output=True)
    report_errors: list[str] = []
    if out.exists():
        report = read_json(out)
        report_errors = [str(error) for error in report.get("errors", [])]
    observed = completed.returncode != 0 and any(expected_error in error for error in report_errors)
    return {
        "id": probe_id,
        "expectedError": expected_error,
        "exitCode": completed.returncode,
        "expectedFailureObserved": observed,
        "errors": report_errors,
    }


def build_report() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="intentgraph-p8.67-") as tmp:
        tmp_root = Path(tmp)
        probes = [
            run_probe(
                "manifest-sha-mismatch",
                "manifest sha256 does not match replayed package artifact",
                lambda _package, manifest, _boundary: mutate_json(
                    manifest, lambda data: data["artifact"].__setitem__("sha256", "sha256:0000")
                ),
                tmp_root,
            ),
            run_probe(
                "manifest-byte-length-mismatch",
                "manifest byteLength does not match replayed package artifact",
                lambda _package, manifest, _boundary: mutate_json(
                    manifest, lambda data: data["artifact"].__setitem__("byteLength", 1)
                ),
                tmp_root,
            ),
            run_probe(
                "manifest-file-count-mismatch",
                "manifest fileCount does not match replayed package artifact",
                lambda _package, manifest, _boundary: mutate_json(
                    manifest, lambda data: data["artifact"].__setitem__("fileCount", 1)
                ),
                tmp_root,
            ),
            run_probe(
                "boundary-extraction-authorized",
                "boundary must keep extraction unauthorized",
                lambda _package, _manifest, boundary: mutate_json(
                    boundary,
                    lambda data: data["verificationBoundary"].__setitem__("mayExtractPackageForVerification", True),
                ),
                tmp_root,
            ),
            run_probe(
                "boundary-execution-authorized",
                "boundary must keep packaged executable launch unauthorized",
                lambda _package, _manifest, boundary: mutate_json(
                    boundary,
                    lambda data: data["verificationBoundary"].__setitem__("mayRunPackagedExecutable", True),
                ),
                tmp_root,
            ),
            run_probe(
                "package-byte-appended",
                "manifest sha256 does not match replayed package artifact",
                lambda package, _manifest, _boundary: package.write_bytes(package.read_bytes() + b"intentgraph-negative"),
                tmp_root,
            ),
            run_probe(
                "package-not-zip",
                "package artifact is not a readable zip",
                lambda package, _manifest, _boundary: package.write_bytes(b"not a zip"),
                tmp_root,
            ),
            run_probe(
                "package-missing-smartcomm",
                "required package entry missing: SmartComm2.dll",
                lambda package, _manifest, _boundary: (
                    remove_zip_entry(package, package.with_suffix(".missing.zip"), "SmartComm2.dll"),
                    shutil.move(str(package.with_suffix(".missing.zip")), package),
                ),
                tmp_root,
            ),
        ]

    result = "pass" if all(probe["expectedFailureObserved"] for probe in probes) else "fail"
    return {
        "artifactRole": "intentgraph-packaged-artifact-metadata-replay-negative-probes-report",
        "status": "intentgraph-packaged-artifact-metadata-replay-negative-probes-passed"
        if result == "pass"
        else "intentgraph-packaged-artifact-metadata-replay-negative-probes-failed",
        "scope": SCOPE,
        "workItem": WORK_ITEM,
        "date": DATE,
        "result": result,
        "probeCount": len(probes),
        "probes": probes,
        "boundary": {
            "packageExtractionPerformed": False,
            "packagedExecutableLaunched": False,
            "packagedUiLaunched": False,
            "installerCreated": False,
            "artifactSigned": False,
            "credentialAccessed": False,
            "providerApiCalled": False,
            "releasePublished": False,
            "productizationClaimed": False,
        },
        "recommendedNextSlice": "P8.68 Packaged Artifact Verification Authorization Request",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run P8.67 package metadata replay negative probes.")
    parser.add_argument("--out", default=DEFAULT_OUT, type=Path)
    args = parser.parse_args()
    report = build_report()
    write_json(args.out, report)
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
