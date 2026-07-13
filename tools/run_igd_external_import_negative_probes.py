"""Repeatable P9.4 negative probes for B1-equivalent external source intake."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
FACADE = ROOT / "tools" / "intentgraph.py"
SOURCE = ROOT / "docs" / "examples" / "b1-typescript-rest-api" / "source"


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def tree_digest(root: Path) -> str:
    records = [
        {
            "path": item.relative_to(root).as_posix(),
            "sha256": "sha256:" + hashlib.sha256(item.read_bytes()).hexdigest(),
        }
        for item in sorted(root.rglob("*.ts"))
    ]
    canonical = json.dumps(records, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def run_import(workspace: Path, source_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(FACADE),
            "import-b1-equivalent",
            "--workspace",
            str(workspace),
            "--source-root",
            str(source_root),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def validate(workspace: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(FACADE), "validate", "--workspace", str(workspace)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def mutate_source_file(root: Path) -> None:
    path = root / "src" / "model" / "todo.ts"
    path.write_text(path.read_text(encoding="utf-8") + "\nexport const intakeProbe = true;\n", encoding="utf-8")


def add_unsupported_file(root: Path) -> None:
    (root / "README.md").write_text("unsupported for B1 source profile\n", encoding="utf-8")


def tamper_receipt(workspace: Path) -> None:
    path = workspace / "artifacts" / "external-source-intake-receipt.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value["sourcePathPersisted"] = True
    write_json(path, value)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run P9.4 external import negative probes.")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    probe_results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="intentgraph-p9.4-") as temp:
        root = Path(temp)
        baseline_source = root / "baseline-source"
        shutil.copytree(SOURCE, baseline_source)
        before_digest = tree_digest(baseline_source)
        baseline_workspace = root / "baseline-workspace"
        baseline_import = run_import(baseline_workspace, baseline_source)
        if baseline_import.returncode != 0:
            raise SystemExit(f"baseline import failed: {baseline_import.stderr}")
        baseline_review = subprocess.run(
            [sys.executable, str(FACADE), "review", "--workspace", str(baseline_workspace)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if baseline_review.returncode != 0:
            raise SystemExit(f"baseline review failed: {baseline_review.stderr}")
        if tree_digest(baseline_source) != before_digest:
            raise SystemExit("baseline external source changed during import/review")

        import_probes: list[tuple[str, Callable[[Path], None], str, bool]] = [
            ("missing-source-root", lambda source: shutil.rmtree(source), "external source root must be a non-symlink directory", True),
            ("source-root-is-file", lambda source: None, "external source root must be a non-symlink directory", True),
            ("unsupported-source-extension", add_unsupported_file, "unsupported source extension for B1 profile", True),
            ("source-not-b1-equivalent", mutate_source_file, "external source is not B1-equivalent to the bounded profile", True),
            ("workspace-overlaps-source", lambda source: None, "external source root and workspace must not overlap", True),
            ("workspace-already-exists", lambda source: None, "workspace must not exist for external import", True),
        ]
        for identifier, mutate, expected_error, should_absent in import_probes:
            source = root / f"{identifier}-source"
            shutil.copytree(SOURCE, source)
            mutate(source)
            if identifier == "source-root-is-file":
                source_root = source / "src" / "model" / "todo.ts"
                workspace = root / f"{identifier}-workspace"
            elif identifier == "workspace-overlaps-source":
                source_root = source
                workspace = source / "new-workspace"
            else:
                source_root = source
                workspace = root / f"{identifier}-workspace"
            if identifier == "workspace-already-exists":
                workspace.mkdir(parents=True)
                should_absent = False
            completed = run_import(workspace, source_root)
            observed = completed.returncode != 0 and expected_error in completed.stderr
            probe_results.append(
                {
                    "id": identifier,
                    "kind": "import",
                    "expectedError": expected_error,
                    "exitCode": completed.returncode,
                    "stderr": completed.stderr.strip(),
                    "workspaceAbsentAfterFailure": not workspace.exists(),
                    "workspaceAbsenceRequired": should_absent,
                    "expectedFailureObserved": observed and (not should_absent or not workspace.exists()),
                }
            )

        receipt_workspace = root / "tampered-receipt-workspace"
        receipt_source = root / "tampered-receipt-source"
        shutil.copytree(SOURCE, receipt_source)
        receipt_import = run_import(receipt_workspace, receipt_source)
        if receipt_import.returncode != 0:
            raise SystemExit(f"receipt probe setup failed: {receipt_import.stderr}")
        tamper_receipt(receipt_workspace)
        receipt_validation = validate(receipt_workspace)
        expected_error = "external source intake receipt does not match copied source evidence"
        probe_results.append(
            {
                "id": "tampered-intake-receipt",
                "kind": "workspace-validation",
                "expectedError": expected_error,
                "exitCode": receipt_validation.returncode,
                "stderr": receipt_validation.stderr.strip(),
                "workspaceAbsentAfterFailure": False,
                "workspaceAbsenceRequired": False,
                "expectedFailureObserved": receipt_validation.returncode != 0 and expected_error in receipt_validation.stderr,
            }
        )
    report = {
        "artifactRole": "intentgraph-external-source-intake-negative-probes-report",
        "status": "intentgraph-external-source-intake-negative-probes-passed"
        if all(item["expectedFailureObserved"] for item in probe_results)
        else "intentgraph-external-source-intake-negative-probes-failed",
        "result": "pass" if all(item["expectedFailureObserved"] for item in probe_results) else "fail",
        "profile": "b1-typescript-rest-api-sample",
        "baselineImportPassed": True,
        "baselineReviewPassed": True,
        "externalSourceDigestStable": True,
        "sourcePathPersisted": False,
        "probeCount": len(probe_results),
        "probes": probe_results,
        "authority": {
            "externalSourceMutation": False,
            "targetRepositoryMutation": False,
            "automaticCodeApplication": False,
            "networkRequired": False,
        },
    }
    write_json(args.out, report)
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
