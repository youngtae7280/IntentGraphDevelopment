import argparse
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GOOD_DRAFT = REPO_ROOT / "generated/windowsutility/p8.4-shell-workspace-accepted-mapping-draft.json"
TARGET_ROOT = Path(r"C:\Users\ytkim\Desktop\kyt_work\WindowsUtility")
VERIFY = REPO_ROOT / "tools/verify_windowsutility_mapping_draft.py"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_verify(draft: Path, out: Path):
    return subprocess.run(
        [
            sys.executable,
            str(VERIFY),
            "--draft",
            str(draft),
            "--target-root",
            str(TARGET_ROOT),
            "--out",
            str(out),
        ],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
    )


def mutate_stale_digest(draft):
    draft["draftMapping"]["codeSurfaceRefs"][0]["digest"] = "sha256:" + "0" * 64


def mutate_missing_ref(draft):
    draft["draftMapping"]["codeSurfaceRefs"][0]["path"] = "src/WindowsUtility.App/Missing.csproj"


def mutate_accepted(draft):
    draft["draftMapping"]["accepted"] = True


def mutate_target_write(draft):
    draft["target"]["targetWritesAuthorized"] = True
    draft["authorizations"]["targetWritesAuthorized"] = True


def mutate_baseline_accepted(draft):
    draft["target"]["baselineAccepted"] = True


PROBES = [
    ("stale-digest", mutate_stale_digest, "digest mismatch for source ref"),
    ("missing-source-ref", mutate_missing_ref, "source ref missing"),
    ("accepted-true", mutate_accepted, "mapping draft must remain unaccepted"),
    ("target-write-true", mutate_target_write, "target writes must remain unauthorized"),
    ("baseline-accepted-true", mutate_baseline_accepted, "target baseline must remain unaccepted"),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    good = load_json(GOOD_DRAFT)
    probe_results = []

    with tempfile.TemporaryDirectory(prefix="windowsutility-mapping-draft-probes-") as temp_dir:
        temp = Path(temp_dir)
        positive_out = temp / "positive-report.json"
        positive = run_verify(GOOD_DRAFT, positive_out)
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
        "artifactRole": "intentgraph-windowsutility-mapping-draft-negative-probes-report",
        "status": "intentgraph-windowsutility-mapping-draft-negative-probes-passed" if result == "pass" else "intentgraph-windowsutility-mapping-draft-negative-probes-failed",
        "scope": "p8.5-shell-workspace-mapping-draft-negative-probes-report-only",
        "workItem": "P8.5 Shell Workspace Mapping Draft Negative Probes",
        "result": result,
        "positiveBaseline": {
            "draft": str(GOOD_DRAFT.relative_to(REPO_ROOT)).replace("\\", "/"),
            "rerunResult": "pass" if positive_passed else "fail",
        },
        "probeCount": len(probe_results),
        "probes": probe_results,
        "authorizations": {
            "acceptedMappingCreated": False,
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
