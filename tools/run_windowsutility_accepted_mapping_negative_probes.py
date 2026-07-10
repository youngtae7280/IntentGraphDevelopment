import argparse
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GOOD_MAPPING = REPO_ROOT / "generated/windowsutility/p8.9-shell-workspace-accepted-mapping.json"
TARGET_ROOT = Path(r"C:\Users\ytkim\Desktop\kyt_work\WindowsUtility")
VERIFY = REPO_ROOT / "tools/verify_windowsutility_accepted_mapping.py"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_verify(mapping: Path, out: Path):
    return subprocess.run(
        [
            sys.executable,
            str(VERIFY),
            "--mapping",
            str(mapping),
            "--target-root",
            str(TARGET_ROOT),
            "--out",
            str(out),
        ],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
    )


def mutate_stale_digest(mapping):
    mapping["acceptedMapping"]["codeSurfaceRefs"][0]["digest"] = "sha256:" + "0" * 64


def mutate_missing_ref(mapping):
    mapping["acceptedMapping"]["codeSurfaceRefs"][0]["path"] = "src/WindowsUtility.App/Missing.csproj"


def mutate_human_acceptance_missing(mapping):
    mapping["humanAcceptance"]["recorded"] = False


def mutate_human_acceptance_rejected(mapping):
    mapping["humanAcceptance"]["accepted"] = False
    mapping["humanAcceptance"]["responseText"] = "reject"


def mutate_mapping_not_accepted(mapping):
    mapping["acceptedMapping"]["accepted"] = False


def mutate_target_write(mapping):
    mapping["target"]["targetWritesAuthorized"] = True
    mapping["authorizations"]["targetWritesAuthorized"] = True


def mutate_productization(mapping):
    mapping["authorizations"]["productizationAuthorized"] = True


PROBES = [
    ("stale-digest", mutate_stale_digest, "digest mismatch for source ref"),
    ("missing-source-ref", mutate_missing_ref, "source ref missing"),
    ("human-acceptance-missing", mutate_human_acceptance_missing, "human acceptance must be recorded and accepted"),
    ("human-acceptance-rejected", mutate_human_acceptance_rejected, "human acceptance must be recorded and accepted"),
    ("mapping-not-accepted", mutate_mapping_not_accepted, "accepted mapping must be accepted true"),
    ("target-write-true", mutate_target_write, "target writes must remain unauthorized"),
    ("productization-true", mutate_productization, "productizationAuthorized must remain false"),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    good = load_json(GOOD_MAPPING)
    probe_results = []

    with tempfile.TemporaryDirectory(prefix="windowsutility-accepted-mapping-probes-") as temp_dir:
        temp = Path(temp_dir)
        positive_out = temp / "positive-report.json"
        positive = run_verify(GOOD_MAPPING, positive_out)
        positive_report = load_json(positive_out) if positive_out.exists() else {}
        positive_passed = positive.returncode == 0 and positive_report.get("result") == "pass"

        for probe_id, mutate, expected_error in PROBES:
            bad = copy.deepcopy(good)
            mutate(bad)
            bad_path = temp / f"{probe_id}.json"
            report_path = temp / f"{probe_id}-report.json"
            write_json(bad_path, bad)
            completed = run_verify(bad_path, report_path)
            report = load_json(report_path) if report_path.exists() else {}
            errors = report.get("errors", [])
            observed = completed.returncode != 0 and any(expected_error in err for err in errors)
            probe_results.append(
                {
                    "id": probe_id,
                    "expectedError": expected_error,
                    "expectedFailureObserved": observed,
                    "actualReturnCode": completed.returncode,
                    "actualErrors": errors,
                }
            )

    result = "pass" if positive_passed and all(p["expectedFailureObserved"] for p in probe_results) else "fail"
    report = {
        "artifactRole": "intentgraph-windowsutility-accepted-mapping-negative-probes-report",
        "status": "intentgraph-windowsutility-accepted-mapping-negative-probes-passed" if result == "pass" else "intentgraph-windowsutility-accepted-mapping-negative-probes-failed",
        "scope": "p8.10-shell-workspace-accepted-mapping-negative-probes-report-only",
        "workItem": "P8.10 Shell Workspace Accepted Mapping Negative Probes",
        "result": result,
        "positiveBaseline": {
            "mapping": str(GOOD_MAPPING.relative_to(REPO_ROOT)).replace("\\", "/"),
            "rerunResult": "pass" if positive_passed else "fail",
        },
        "probeCount": len(probe_results),
        "probes": probe_results,
        "authorizations": {
            "acceptedMappingCreated": True,
            "targetWritesAuthorized": False,
            "proposalApplicationAuthorized": False,
            "aiAuthorityPromoted": False,
            "productizationAuthorized": False,
        },
    }
    write_json(Path(args.out), report)
    return 0 if result == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
