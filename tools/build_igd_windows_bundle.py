"""Build and validate the deterministic Windows-local IntentGraph bundle."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_NAME = "igd-bundle-manifest.json"
BUNDLE_ROLE = "intentgraph-windows-portable-bundle-manifest"
BUNDLE_STATUS = "intentgraph-windows-portable-bundle-built"
BUNDLE_SCOPE = "p9.34-windows-local-portable-distribution"
BUNDLE_VERSION = "0.1.0-preview"
ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)

ENTRYPOINTS = ("tools/igd.py", "tools/igd_daily.py")
CORE_RUNTIME_MODULES = (
    "tools/intentgraph.py",
    "tools/experimental_csharp_workspace.py",
    "tools/experimental_csharp_project.py",
    "tools/emit_experimental_csharp_fact_workbench.py",
    "tools/serve_experimental_csharp_project_workbench.py",
    "tools/preflight_csharp_host_sdk_profile.py",
    "tools/run_windowsutility_csharp_syntax_probe.py",
)
STATIC_RUNTIME_FILES = (
    "tools/csharp_syntax_probe/IntentGraph.CSharpSyntaxProbe.csproj",
    "tools/csharp_syntax_probe/NuGet.Config",
    "tools/csharp_syntax_probe/Program.cs",
    "tools/csharp_semantic_overlay_probe/IntentGraph.CSharpSemanticOverlayProbe.csproj",
    "tools/csharp_semantic_overlay_probe/Program.cs",
    "docs/examples/profiles/experimental-host-sdk-csharp-syntax.profile.json",
    "generated/product-surfaces/graph-delta-approval-workbench/p8.60/assets/cytoscape.min.js",
    "generated/product-surfaces/graph-delta-approval-workbench/p8.60/assets/cytoscape-license.txt",
)
TEMPLATE_FILES = {
    "packaging/windows/igd.cmd": "igd.cmd",
    "packaging/windows/install.ps1": "install.ps1",
    "packaging/windows/uninstall.ps1": "uninstall.ps1",
    "packaging/windows/README.txt": "README.txt",
}
ROOT_FILES = frozenset((*TEMPLATE_FILES.values(), MANIFEST_NAME))
FALSE_AUTHORITY = {
    "networkAccessed": False,
    "downloadPerformed": False,
    "credentialAccessed": False,
    "artifactSigned": False,
    "releasePublished": False,
    "providerApiCalled": False,
    "targetRepositoryMutated": False,
}
FORBIDDEN_INSTALLER_TOKENS = (
    "invoke-webrequest",
    "start-bitstransfer",
    "bitsadmin",
    "curl.exe",
    "wget.exe",
    "certutil -urlcache",
    "signtool",
    "gh release",
    "publish-module",
    "nuget install",
)
WINDOWS_RESERVED_NAMES = frozenset(
    {"con", "prn", "aux", "nul", "clock$"}
    | {f"com{index}" for index in range(1, 10)}
    | {f"lpt{index}" for index in range(1, 10)}
)
MANIFEST_KEYS = {
    "artifactRole",
    "status",
    "scope",
    "bundleVersion",
    "platform",
    "entrypoints",
    "requirements",
    "runtime",
    "authority",
    "files",
    "fileCount",
}


class BundleError(ValueError):
    """Raised when the portable bundle contract is violated."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def pretty_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"


def digest_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def digest_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return "sha256:" + hasher.hexdigest()


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def safe_relative(value: str) -> str:
    if not value or "\\" in value:
        raise BundleError(f"unsafe bundle path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts or any(not part for part in path.parts):
        raise BundleError(f"unsafe bundle path: {value!r}")
    normalized = path.as_posix()
    if normalized != value:
        raise BundleError(f"bundle path is not normalized: {value!r}")
    for part in path.parts:
        if ":" in part or part.endswith((".", " ")) or part.split(".", 1)[0].lower() in WINDOWS_RESERVED_NAMES:
            raise BundleError(f"unsafe Windows bundle path: {value!r}")
    return normalized


def assert_safe_output(path: Path, *, label: str, source_root: Path = REPO_ROOT) -> Path:
    resolved = path.expanduser().resolve()
    protected = [
        source_root.resolve(),
        (source_root / ".git").resolve(),
        (source_root / "tools").resolve(),
        (source_root / "docs").resolve(),
        (source_root / "packaging").resolve(),
    ]
    if resolved in protected:
        raise BundleError(f"{label} must not overwrite a protected repository path: {resolved}")
    for source in protected[1:]:
        if is_within(resolved, source):
            raise BundleError(f"{label} must not be inside a protected repository path: {resolved}")
    if resolved.exists():
        raise BundleError(f"{label} already exists: {resolved}")
    return resolved


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise BundleError(f"invalid JSON file: {path}") from error
    if not isinstance(value, dict):
        raise BundleError(f"JSON root must be an object: {path}")
    return value


def local_module_index(source_root: Path) -> dict[str, Path]:
    index: dict[str, Path] = {}
    tools_root = source_root / "tools"
    for path in sorted(tools_root.glob("*.py")):
        if path.is_symlink():
            raise BundleError(f"runtime module must not be a symlink: {path}")
        index[path.stem] = path
    return index


def imported_local_modules(path: Path, index: dict[str, Path]) -> set[Path]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    except (OSError, SyntaxError, UnicodeError) as error:
        raise BundleError(f"cannot parse runtime module: {path}") from error
    imported: set[Path] = set()
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names.extend(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.append(node.module.split(".", 1)[0])
        for name in names:
            candidate = index.get(name)
            if candidate is not None:
                imported.add(candidate)
    return imported


def runtime_python_files(source_root: Path) -> list[Path]:
    seed_relatives = (*ENTRYPOINTS, *CORE_RUNTIME_MODULES)
    seeds: list[Path] = []
    for relative in seed_relatives:
        path = source_root / relative
        if not path.is_file():
            raise BundleError(f"missing required runtime module: {relative}")
        if path.is_symlink():
            raise BundleError(f"runtime module must not be a symlink: {relative}")
        seeds.append(path)

    index = local_module_index(source_root)
    pending = list(seeds)
    included: set[Path] = set()
    while pending:
        path = pending.pop()
        resolved = path.resolve()
        if resolved in included:
            continue
        included.add(resolved)
        pending.extend(imported_local_modules(path, index))
    return sorted(included, key=lambda item: item.relative_to(source_root).as_posix())


def source_to_bundle_files(source_root: Path) -> dict[str, Path]:
    mapping: dict[str, Path] = {}
    for source, destination in TEMPLATE_FILES.items():
        mapping[destination] = source_root / source
    for path in runtime_python_files(source_root):
        mapping[path.relative_to(source_root).as_posix()] = path
    for relative in STATIC_RUNTIME_FILES:
        mapping[relative] = source_root / relative

    for destination, source in mapping.items():
        safe_relative(destination)
        if not source.is_file():
            raise BundleError(f"missing required bundle source: {source.relative_to(source_root).as_posix()}")
        if source.is_symlink():
            raise BundleError(f"bundle source must not be a symlink: {source.relative_to(source_root).as_posix()}")
    return dict(sorted(mapping.items()))


def file_record(path: Path, relative: str) -> dict[str, Any]:
    return {
        "path": relative,
        "sha256": digest_file(path),
        "byteLength": path.stat().st_size,
    }


def create_manifest(bundle_root: Path, python_files: Iterable[str]) -> dict[str, Any]:
    records = [
        file_record(bundle_root / relative, relative)
        for relative in sorted(
            path.relative_to(bundle_root).as_posix()
            for path in bundle_root.rglob("*")
            if path.is_file() and path.relative_to(bundle_root).as_posix() != MANIFEST_NAME
        )
    ]
    return {
        "artifactRole": BUNDLE_ROLE,
        "status": BUNDLE_STATUS,
        "scope": BUNDLE_SCOPE,
        "bundleVersion": BUNDLE_VERSION,
        "platform": "windows-local-portable",
        "entrypoints": {
            "command": "igd.cmd",
            "cli": "tools/igd.py",
            "dailyWorkflow": "tools/igd_daily.py",
        },
        "requirements": {
            "python": "Python 3.11 or newer available as py -3 or python",
            "csharpWorkflow": "Supported locally installed .NET SDK",
        },
        "runtime": {
            "pythonModules": sorted(python_files),
            "csharpProbeProjects": [
                "tools/csharp_syntax_probe/IntentGraph.CSharpSyntaxProbe.csproj",
                "tools/csharp_semantic_overlay_probe/IntentGraph.CSharpSemanticOverlayProbe.csproj",
            ],
            "browserGraphLibrary": "generated/product-surfaces/graph-delta-approval-workbench/p8.60/assets/cytoscape.min.js",
        },
        "authority": FALSE_AUTHORITY,
        "files": records,
        "fileCount": len(records),
    }


def allowed_payload_path(relative: str) -> bool:
    path = PurePosixPath(relative)
    if len(path.parts) == 1:
        return relative in (ROOT_FILES - {MANIFEST_NAME})
    if path.parts[0] == "tools":
        return path.suffix.lower() in {".py", ".cs", ".csproj"} or path.name == "NuGet.Config"
    if relative == "docs/examples/profiles/experimental-host-sdk-csharp-syntax.profile.json":
        return True
    return relative in {
        "generated/product-surfaces/graph-delta-approval-workbench/p8.60/assets/cytoscape.min.js",
        "generated/product-surfaces/graph-delta-approval-workbench/p8.60/assets/cytoscape-license.txt",
    }


def validate_script_safety(bundle_root: Path) -> None:
    for relative in ("igd.cmd", "install.ps1", "uninstall.ps1"):
        text = (bundle_root / relative).read_text(encoding="utf-8-sig").lower()
        for token in FORBIDDEN_INSTALLER_TOKENS:
            if token in text:
                raise BundleError(f"unsafe installer instruction in {relative}: {token}")
    launcher = (bundle_root / "igd.cmd").read_text(encoding="utf-8-sig").lower()
    if "%igd_root%tools\\igd.py" not in launcher:
        raise BundleError("igd.cmd must launch the bundled tools\\igd.py")


def validate_directory(bundle_root: Path) -> dict[str, Any]:
    root = bundle_root.resolve()
    if not root.is_dir() or root.is_symlink():
        raise BundleError(f"bundle must be a non-symlink directory: {bundle_root}")
    manifest_path = root / MANIFEST_NAME
    manifest = read_json(manifest_path)
    if set(manifest) != MANIFEST_KEYS:
        raise BundleError("unexpected bundle manifest fields")
    if manifest.get("artifactRole") != BUNDLE_ROLE:
        raise BundleError("unexpected bundle manifest role")
    if manifest.get("status") != BUNDLE_STATUS:
        raise BundleError("unexpected bundle manifest status")
    if manifest.get("scope") != BUNDLE_SCOPE or manifest.get("bundleVersion") != BUNDLE_VERSION:
        raise BundleError("unexpected bundle scope or version")
    if manifest.get("authority") != FALSE_AUTHORITY:
        raise BundleError("unsafe bundle authority boundary")
    expected_entrypoints = {"command": "igd.cmd", "cli": "tools/igd.py", "dailyWorkflow": "tools/igd_daily.py"}
    if manifest.get("entrypoints") != expected_entrypoints:
        raise BundleError("unexpected bundle entrypoints")

    records = manifest.get("files")
    if not isinstance(records, list) or not records:
        raise BundleError("bundle manifest files must be a non-empty array")
    if manifest.get("fileCount") != len(records):
        raise BundleError("bundle manifest fileCount mismatch")

    seen: set[str] = set()
    manifest_paths: list[str] = []
    for record in records:
        if not isinstance(record, dict) or set(record) != {"path", "sha256", "byteLength"}:
            raise BundleError("invalid bundle file record")
        relative = safe_relative(str(record.get("path", "")))
        if relative in seen:
            raise BundleError(f"duplicate bundle file record: {relative}")
        seen.add(relative)
        manifest_paths.append(relative)
        if not allowed_payload_path(relative):
            raise BundleError(f"unsafe or unsupported bundle payload path: {relative}")
        path = root / Path(*PurePosixPath(relative).parts)
        if not path.is_file() or path.is_symlink():
            raise BundleError(f"missing bundle file: {relative}")
        if record["sha256"] != digest_file(path):
            raise BundleError(f"stale bundle digest: {relative}")
        if record["byteLength"] != path.stat().st_size:
            raise BundleError(f"stale bundle byte length: {relative}")

    if manifest_paths != sorted(manifest_paths):
        raise BundleError("bundle file records must be sorted by path")

    actual_paths: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise BundleError(f"bundle must not contain symlinks: {path.relative_to(root).as_posix()}")
        if path.is_file() and path.relative_to(root).as_posix() != MANIFEST_NAME:
            actual_paths.append(path.relative_to(root).as_posix())
    missing = sorted(set(manifest_paths) - set(actual_paths))
    extra = sorted(set(actual_paths) - set(manifest_paths))
    if missing:
        raise BundleError(f"bundle is missing manifest files: {', '.join(missing)}")
    if extra:
        raise BundleError(f"bundle contains extra files: {', '.join(extra)}")

    required = set(ENTRYPOINTS) | set(STATIC_RUNTIME_FILES) | set(TEMPLATE_FILES.values())
    absent_required = sorted(required - set(actual_paths))
    if absent_required:
        raise BundleError(f"bundle is missing required runtime files: {', '.join(absent_required)}")

    runtime = manifest.get("runtime")
    if not isinstance(runtime, dict) or runtime.get("pythonModules") != sorted(
        path for path in manifest_paths if path.startswith("tools/") and path.endswith(".py")
    ):
        raise BundleError("runtime python module inventory mismatch")
    validate_script_safety(root)
    return {
        "artifactRole": "intentgraph-windows-portable-bundle-validation-report",
        "status": "intentgraph-windows-portable-bundle-validation-passed",
        "scope": BUNDLE_SCOPE,
        "result": "pass",
        "bundle": str(root),
        "fileCount": len(records),
        "manifestSha256": digest_file(manifest_path),
        "authority": FALSE_AUTHORITY,
    }


def validate_archive(archive_path: Path) -> dict[str, Any]:
    archive = archive_path.resolve()
    if not archive.is_file() or archive.is_symlink():
        raise BundleError(f"bundle archive must be a non-symlink file: {archive_path}")
    try:
        with zipfile.ZipFile(archive, "r") as handle:
            infos = handle.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                raise BundleError("bundle archive contains duplicate entries")
            for info in infos:
                safe_relative(info.filename)
                if info.is_dir():
                    raise BundleError(f"bundle archive contains an unexpected directory entry: {info.filename}")
                unix_mode = (info.external_attr >> 16) & 0xFFFF
                if stat.S_ISLNK(unix_mode):
                    raise BundleError(f"bundle archive contains a symlink: {info.filename}")
            if MANIFEST_NAME not in names:
                raise BundleError("bundle archive is missing the manifest")
            with tempfile.TemporaryDirectory(prefix="igd-windows-bundle-validate-") as temporary:
                root = Path(temporary) / "bundle"
                root.mkdir()
                for info in infos:
                    target = root / Path(*PurePosixPath(info.filename).parts)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(handle.read(info))
                report = validate_directory(root)
    except zipfile.BadZipFile as error:
        raise BundleError(f"invalid bundle archive: {archive}") from error
    report["bundle"] = str(archive)
    report["archiveSha256"] = digest_file(archive)
    return report


def validate_bundle(path: Path) -> dict[str, Any]:
    return validate_directory(path) if path.is_dir() else validate_archive(path)


def write_deterministic_zip(bundle_root: Path, archive_path: Path) -> None:
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as handle:
        for path in sorted(item for item in bundle_root.rglob("*") if item.is_file()):
            relative = path.relative_to(bundle_root).as_posix()
            info = zipfile.ZipInfo(relative, ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            handle.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def build_bundle(output: Path, archive: Path | None = None, *, source_root: Path = REPO_ROOT) -> dict[str, Any]:
    source = source_root.resolve()
    destination = assert_safe_output(output, label="bundle output", source_root=source)
    archive_destination = None
    if archive is not None:
        archive_destination = assert_safe_output(archive, label="bundle archive", source_root=source)
        if archive_destination == destination or is_within(archive_destination, destination):
            raise BundleError("bundle archive must not collide with or be inside the bundle output")

    mapping = source_to_bundle_files(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
    try:
        for relative, source_path in mapping.items():
            target = staging / Path(*PurePosixPath(relative).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_path, target)
        python_files = sorted(relative for relative in mapping if relative.startswith("tools/") and relative.endswith(".py"))
        manifest = create_manifest(staging, python_files)
        (staging / MANIFEST_NAME).write_text(pretty_json(manifest), encoding="utf-8", newline="\n")
        validate_directory(staging)
        staging.replace(destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    directory_report = validate_directory(destination)
    result: dict[str, Any] = {
        "artifactRole": "intentgraph-windows-portable-bundle-build-report",
        "status": "intentgraph-windows-portable-bundle-build-passed",
        "scope": BUNDLE_SCOPE,
        "result": "pass",
        "bundleDirectory": str(destination),
        "fileCount": directory_report["fileCount"],
        "manifestSha256": directory_report["manifestSha256"],
        "authority": FALSE_AUTHORITY,
    }
    if archive_destination is not None:
        try:
            archive_destination.parent.mkdir(parents=True, exist_ok=True)
            write_deterministic_zip(destination, archive_destination)
            archive_report = validate_archive(archive_destination)
        except Exception:
            archive_destination.unlink(missing_ok=True)
            raise
        result["archive"] = str(archive_destination)
        result["archiveSha256"] = archive_report["archiveSha256"]
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build", help="Build a deterministic directory bundle and optional ZIP archive.")
    build.add_argument("--output", required=True, type=Path)
    build.add_argument("--archive", type=Path)
    validate = subparsers.add_parser("validate", help="Validate a bundle directory or ZIP archive.")
    validate.add_argument("--bundle", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        report = build_bundle(args.output, args.archive) if args.command == "build" else validate_bundle(args.bundle)
    except (BundleError, OSError, zipfile.BadZipFile) as error:
        print(pretty_json({"result": "fail", "error": str(error)}), file=sys.stderr, end="")
        return 1
    print(pretty_json(report), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
