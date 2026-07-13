"""Preflight the local experimental host-SDK C# profile without reading a target."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


EXPECTED_ROLE = "intentgraph-experimental-csharp-host-sdk-profile"
EXPECTED_STATUS = "intentgraph-experimental-csharp-host-sdk-profile-declared"
EXPECTED_SCOPE = "experimental-host-sdk-csharp-availability-preflight"
EXPECTED_PROFILE_ID = "experimental-csharp-host-sdk-syntax-only"
EXPECTED_AUTHORITY = {
    "targetRepositoryRead": False,
    "targetRepositoryMutation": False,
    "targetBuildExecuted": False,
    "targetRestoreExecuted": False,
    "targetLaunchExecuted": False,
    "packageDependencyAdded": False,
    "packageRestoreExecuted": False,
    "packageInstallExecuted": False,
    "networkRequired": False,
    "providerApiAllowed": False,
    "credentialAccessAllowed": False,
    "automaticCodeApplication": False,
    "igdProductizationClaimed": False,
}
FORBIDDEN_PROFILE_KEYS = {
    "targetSourceRoot",
    "sourceRoot",
    "sourceExtractionAllowed",
    "targetRepositoryPath",
    "targetProjectPath",
}
SDK_LINE = re.compile(r"^(?P<version>\d+\.\d+\.\d+)\s+\[(?P<root>.+)\]$")


class PreflightError(RuntimeError):
    """Raised when the experimental profile is unavailable or unsafe."""


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def read_profile(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as error:
        raise PreflightError(f"profile cannot be read: {error}") from error
    if not isinstance(data, dict):
        raise PreflightError("profile must be a JSON object")
    return data


def validate_profile(profile: dict[str, Any]) -> tuple[list[int], list[str]]:
    if profile.get("artifactRole") != EXPECTED_ROLE:
        raise PreflightError("wrong profile artifactRole")
    if profile.get("status") != EXPECTED_STATUS or profile.get("scope") != EXPECTED_SCOPE:
        raise PreflightError("wrong experimental host-SDK profile status or scope")
    if profile.get("profileId") != EXPECTED_PROFILE_ID or profile.get("language") != "csharp":
        raise PreflightError("wrong experimental host-SDK profile identity")
    if any(key in profile for key in FORBIDDEN_PROFILE_KEYS):
        raise PreflightError("experimental host-SDK preflight profile must not declare target source or extraction")
    availability = profile.get("availability")
    if availability != {"experimental": True, "hostSdkSpecific": True, "portable": False, "productReady": False}:
        raise PreflightError("profile availability boundary must remain experimental host-SDK-only and not portable")
    adapter = profile.get("adapter")
    expected_adapter = {
        "id": "roslyn-syntax-only-host-sdk",
        "semanticResolution": False,
        "sourceBuildAllowed": False,
        "sourceExtractionAllowed": False,
        "packageRestoreAllowed": False,
        "packageInstallAllowed": False,
        "networkRequired": False,
    }
    if adapter != expected_adapter:
        raise PreflightError("profile adapter must remain syntax-only with all execution authority false")
    if profile.get("authority") != EXPECTED_AUTHORITY:
        raise PreflightError("profile authority must remain the host-SDK preflight boundary")
    host_sdk = profile.get("hostSdk")
    if not isinstance(host_sdk, dict) or host_sdk.get("selection") != "latest-supported-installed":
        raise PreflightError("profile hostSdk selection must be latest-supported-installed")
    majors = host_sdk.get("supportedMajorVersions")
    assemblies = host_sdk.get("requiredAssemblies")
    if not isinstance(majors, list) or not majors or any(not isinstance(item, int) or item < 1 for item in majors):
        raise PreflightError("profile must declare supported SDK major versions")
    if assemblies != ["Microsoft.CodeAnalysis.dll", "Microsoft.CodeAnalysis.CSharp.dll"]:
        raise PreflightError("profile must declare the exact required Roslyn assemblies")
    return sorted(set(majors)), assemblies


def installed_sdks(dotnet: str) -> list[tuple[tuple[int, int, int], str, Path]]:
    try:
        completed = subprocess.run([dotnet, "--list-sdks"], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    except OSError as error:
        raise PreflightError(f"dotnet host is unavailable: {error}") from error
    if completed.returncode != 0:
        raise PreflightError(f"dotnet SDK discovery failed: {completed.stderr.strip() or completed.stdout.strip()}")
    discovered: list[tuple[tuple[int, int, int], str, Path]] = []
    for line in completed.stdout.splitlines():
        match = SDK_LINE.match(line.strip())
        if not match:
            continue
        version = match.group("version")
        parsed = tuple(int(part) for part in version.split("."))
        discovered.append((parsed, version, Path(match.group("root")) / version))
    if not discovered:
        raise PreflightError("dotnet host reported no installed SDKs")
    return discovered


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def preflight_profile(profile_path: Path, dotnet: str = "dotnet") -> dict[str, Any]:
    profile = read_profile(profile_path)
    supported_majors, assemblies = validate_profile(profile)
    candidates = [entry for entry in installed_sdks(dotnet) if entry[0][0] in supported_majors]
    if not candidates:
        raise PreflightError("no supported installed .NET SDK is available for the experimental profile")
    version_key, version, sdk_root = max(candidates, key=lambda entry: entry[0])
    roslyn_root = sdk_root / "Roslyn" / "bincore"
    assembly_records: list[dict[str, Any]] = []
    for assembly in assemblies:
        path = roslyn_root / assembly
        if not path.is_file():
            raise PreflightError(f"required Roslyn assembly is missing: {assembly}")
        assembly_records.append(
            {
                "name": assembly,
                "byteLength": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return {
        "artifactRole": "intentgraph-experimental-csharp-host-sdk-preflight-report",
        "status": "intentgraph-experimental-csharp-host-sdk-preflight-passed",
        "scope": EXPECTED_SCOPE,
        "result": "pass",
        "profile": {
            "id": profile["profileId"],
            "version": profile["profileVersion"],
            "experimental": True,
            "hostSdkSpecific": True,
            "portable": False,
            "productReady": False,
        },
        "selectedSdk": {
            "version": version,
            "major": version_key[0],
            "pathPersisted": False,
            "requiredAssemblies": assembly_records,
        },
        "adapter": {
            "id": profile["adapter"]["id"],
            "semanticResolution": False,
            "sourceBuildAllowed": False,
            "sourceExtractionAllowed": False,
        },
        "authority": EXPECTED_AUTHORITY,
    }


def main() -> int:
    args = parse_args()
    profile_path = args.profile.resolve()
    output_path = args.out.resolve()
    if profile_path == output_path:
        print("error: output must not overwrite the profile", file=sys.stderr)
        return 2
    try:
        report = preflight_profile(profile_path)
        write_json(output_path, report)
        print(json.dumps(report, ensure_ascii=True, indent=2))
        return 0
    except PreflightError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
