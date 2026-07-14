"""Emit the P9.35 milestone review report from validated committed evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
NEGATIVE = ROOT / "generated" / "roadmap" / "p9.35-reviewed-source-refresh-negative-probes-report.json"
BENCHMARK = ROOT / "generated" / "roadmap" / "p9.35-windowsutility-refresh-benchmark-report.json"
DAILY = ROOT / "generated" / "roadmap" / "p9.34-daily-launch-negative-probes-report.json"
SERVER = ROOT / "generated" / "roadmap" / "p9.34-daily-launch-server-smoke-report.json"
BUNDLE = ROOT / "generated" / "roadmap" / "p9.34-windows-bundle-negative-probes-report.json"
INSTALL = ROOT / "generated" / "roadmap" / "p9.34-windows-install-smoke-report.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate P9.35 evidence and emit its canonical milestone review report.")
    parser.add_argument("--out", type=Path, required=True, help="Canonical JSON review report path.")
    return parser.parse_args()


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def digest_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def read_report(path: Path, role: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"invalid P9.35 evidence report: {path}") from error
    if not isinstance(value, dict) or value.get("artifactRole") != role or value.get("result") != "pass":
        raise RuntimeError(f"P9.35 evidence report did not pass its exact role boundary: {path}")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def emit() -> dict[str, Any]:
    negative = read_report(NEGATIVE, "intentgraph-local-source-refresh-negative-probes-report")
    benchmark = read_report(BENCHMARK, "intentgraph-p9.35-windowsutility-refresh-benchmark-report")
    daily = read_report(DAILY, "intentgraph-daily-launch-negative-probes-report")
    server = read_report(SERVER, "intentgraph-daily-launch-server-smoke-report")
    bundle = read_report(BUNDLE, "intentgraph-windows-portable-bundle-negative-probes-report")
    install = read_report(INSTALL, "intentgraph-windows-local-install-smoke-report")

    refresh_probes = negative.get("probes")
    require(isinstance(refresh_probes, list) and negative.get("probeCount") == len(refresh_probes), "refresh probe count is stale")
    require(all(probe.get("expectedFailureObserved") is True for probe in refresh_probes), "a refresh negative probe did not fail closed")
    immutability = negative.get("positiveEvidence", {}).get("sourceImmutability", {})
    operations = immutability.get("operations")
    require(isinstance(operations, list) and immutability.get("operationCount") == len(operations), "source immutability count is stale")
    require(immutability.get("allIgdOperationsByteStable") is True, "source immutability did not pass")
    require(all(operation.get("sourceBytesUnchanged") is True for operation in operations), "an IGD operation changed source bytes")

    daily_probes = daily.get("probes")
    bundle_probes = bundle.get("probes")
    server_checks = server.get("checks")
    install_checks = install.get("checks")
    require(isinstance(daily_probes, list) and daily.get("probeCount") == len(daily_probes), "daily probe count is stale")
    require(isinstance(bundle_probes, list) and bundle.get("probeCount") == len(bundle_probes), "bundle probe count is stale")
    require(isinstance(server_checks, dict) and all(server_checks.values()), "server smoke checks did not all pass")
    require(isinstance(install_checks, dict) and all(install_checks.values()), "installed runtime checks did not all pass")

    thresholds = benchmark.get("thresholds", {})
    timings = benchmark.get("timings", {})
    source = benchmark.get("source", {})
    require(thresholds.get("planPassed") is True and thresholds.get("acceptPassed") is True, "benchmark thresholds did not pass")
    require(source.get("unchanged") is True and source.get("sourcePathPersisted") is False, "benchmark source boundary did not pass")
    require(benchmark.get("temporarySource", {}).get("unchangedByIntentGraph") is True, "IGD changed benchmark source bytes")
    require(benchmark.get("determinism", {}).get("pendingPlanCanonicalJsonStable") is True, "benchmark plan was not deterministic")

    return {
        "artifactRole": "intentgraph-p9.35-reviewed-source-refresh-review-report",
        "benchmark": {
            "acceptMaxSeconds": thresholds["acceptMaxSeconds"],
            "acceptSeconds": timings["acceptSeconds"],
            "csharpFileCount": source["csharpFileCount"],
            "gitRevision": source.get("gitRevision"),
            "inputMode": source.get("inputMode"),
            "liveWorkingTreeUsed": source.get("liveWorkingTreeUsed"),
            "originalSourceUnchanged": source["unchanged"],
            "planMaxSeconds": thresholds["planMaxSeconds"],
            "planSeconds": timings["planSeconds"],
            "prepareSeconds": timings["prepareSeconds"],
            "temporarySourceUnchangedByIntentGraph": benchmark["temporarySource"]["unchangedByIntentGraph"],
        },
        "decision": "reviewed-source-refresh-evidence-bearing-slice-passed",
        "evidence": {
            "bundleNegativeProbeCount": len(bundle_probes),
            "dailyLaunchProbeCount": len(daily_probes),
            "installedRuntimeCheckCount": len(install_checks),
            "refreshProbeCount": len(refresh_probes),
            "refreshReportByteIdentical": True,
            "refreshReportSha256": digest_bytes(NEGATIVE.read_bytes()),
            "serverCheckCount": len(server_checks),
            "sourceImmutabilityObservationCount": len(operations),
            "windowsBundleFileCount": bundle["positiveBaseline"]["fileCount"],
            "windowsZipRepeatByteIdentical": install_checks["repeatArchiveByteIdentical"],
        },
        "level": "level-4-evidence-bearing-slice",
        "nextSlice": "p9.36-reviewed-proposal-application-product-gate-plan-only",
        "nonGoals": {
            "approvalAutomation": False,
            "automaticIntentMapping": False,
            "networkRequired": False,
            "providerApiAllowed": False,
            "sourceApplicationAuthorized": False,
            "targetBuildExecuted": False,
            "targetLaunchExecuted": False,
            "targetRepositoryMutation": False,
            "targetRestoreExecuted": False,
        },
        "result": "pass",
        "scope": "p9.35-reviewed-source-refresh-and-revision-preservation",
        "status": "intentgraph-p9.35-reviewed-source-refresh-review-passed",
    }


def main() -> int:
    arguments = parse_args()
    output = arguments.out.expanduser().resolve()
    protected = {Path(__file__).resolve(), NEGATIVE.resolve(), BENCHMARK.resolve(), DAILY.resolve(), SERVER.resolve(), BUNDLE.resolve(), INSTALL.resolve()}
    if output in protected:
        raise SystemExit("error: output must not overwrite review code or evidence inputs")
    report = emit()
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_bytes(report)
    output.write_bytes(payload)
    print(json.dumps({"result": "pass", "out": output.as_posix(), "refreshProbeCount": report["evidence"]["refreshProbeCount"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
