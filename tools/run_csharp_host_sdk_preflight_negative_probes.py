"""Run repeatable negative probes for the P9.8 host-SDK availability preflight."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

from preflight_csharp_host_sdk_profile import PreflightError, preflight_profile


ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "tools" / "preflight_csharp_host_sdk_profile.py"
PROFILE = ROOT / "docs" / "examples" / "profiles" / "experimental-host-sdk-csharp-syntax.profile.json"


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def run(profile: Path, output: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(PREFLIGHT), "--profile", str(profile), "--out", str(output)], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    original = json.loads(PROFILE.read_text(encoding="utf-8"))
    temp_parent = ROOT / ".tmp"
    temp_parent.mkdir(exist_ok=True)
    probes: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="p9.8-host-sdk-negative-", dir=temp_parent) as temporary:
        root = Path(temporary)
        baseline_profile = root / "baseline-profile.json"
        write_json(baseline_profile, original)
        first = run(baseline_profile, root / "first.json")
        second = run(baseline_profile, root / "second.json")
        if first.returncode != 0 or second.returncode != 0 or (root / "first.json").read_bytes() != (root / "second.json").read_bytes():
            raise SystemExit("experimental host-SDK positive baseline did not pass deterministically")

        cases: list[tuple[str, str, Callable[[dict[str, Any]], None]]] = [
            ("wrong-profile-role", "wrong profile artifactRole", lambda data: data.__setitem__("artifactRole", "wrong-role")),
            ("target-read-enabled", "profile authority must remain the host-SDK preflight boundary", lambda data: data["authority"].__setitem__("targetRepositoryRead", True)),
            ("network-enabled", "profile adapter must remain syntax-only with all execution authority false", lambda data: data["adapter"].__setitem__("networkRequired", True)),
            ("source-extraction-enabled", "experimental host-SDK preflight profile must not declare target source or extraction", lambda data: data.__setitem__("sourceExtractionAllowed", True)),
            ("unsupported-sdk-major", "no supported installed .NET SDK is available", lambda data: data["hostSdk"].__setitem__("supportedMajorVersions", [999])),
            ("missing-roslyn-assembly", "profile must declare the exact required Roslyn assemblies", lambda data: data["hostSdk"].__setitem__("requiredAssemblies", ["Missing.dll"])),
            ("portable-profile-claim", "profile availability boundary must remain experimental host-SDK-only and not portable", lambda data: data["availability"].__setitem__("portable", True)),
        ]
        for identifier, expected_error, mutate in cases:
            profile = copy.deepcopy(original)
            mutate(profile)
            profile_path = root / f"{identifier}.json"
            write_json(profile_path, profile)
            completed = run(profile_path, root / f"{identifier}-report.json")
            probes.append(
                {
                    "id": identifier,
                    "expectedError": expected_error,
                    "exitCode": completed.returncode,
                    "expectedFailureObserved": completed.returncode != 0 and expected_error in completed.stderr,
                }
            )

        fake_sdk_root = root / "fake-sdk-root"
        (fake_sdk_root / "9.0.100" / "Roslyn" / "bincore").mkdir(parents=True)
        fake_dotnet = root / "fake-dotnet.cmd"
        fake_dotnet.write_text(
            "@echo off\n"
            f"echo 9.0.100 [{fake_sdk_root}]\n",
            encoding="utf-8",
            newline="\n",
        )
        missing_binary_error = ""
        try:
            preflight_profile(baseline_profile, str(fake_dotnet))
        except PreflightError as error:
            missing_binary_error = str(error)
        probes.append(
            {
                "id": "required-host-roslyn-binary-missing",
                "expectedError": "required Roslyn assembly is missing: Microsoft.CodeAnalysis.dll",
                "expectedFailureObserved": "required Roslyn assembly is missing: Microsoft.CodeAnalysis.dll" in missing_binary_error,
            }
        )

        overwrite = subprocess.run(
            [sys.executable, str(PREFLIGHT), "--profile", str(baseline_profile), "--out", str(baseline_profile)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        probes.append(
            {
                "id": "output-overwrites-profile",
                "expectedError": "output must not overwrite the profile",
                "exitCode": overwrite.returncode,
                "expectedFailureObserved": overwrite.returncode != 0 and "output must not overwrite the profile" in overwrite.stderr,
            }
        )
    passed = all(item["expectedFailureObserved"] for item in probes)
    report = {
        "artifactRole": "intentgraph-experimental-csharp-host-sdk-preflight-negative-probes-report",
        "status": "intentgraph-experimental-csharp-host-sdk-preflight-negative-probes-passed" if passed else "intentgraph-experimental-csharp-host-sdk-preflight-negative-probes-failed",
        "scope": "p9.8-experimental-host-sdk-csharp-preflight-negative-probes",
        "result": "pass" if passed else "fail",
        "positiveBaselinePassed": True,
        "repeatOutputByteIdentical": True,
        "probeCount": len(probes),
        "probes": probes,
        "authority": {
            "targetRepositoryRead": False,
            "targetRepositoryMutation": False,
            "targetBuildExecuted": False,
            "packageDependencyAdded": False,
            "packageRestoreExecuted": False,
            "packageInstallExecuted": False,
            "networkRequired": False,
            "automaticCodeApplication": False,
        },
    }
    write_json(args.out, report)
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
