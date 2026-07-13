"""Repeatable fail-closed probes for the daily-use `igd` C# launcher."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "igd.py"
FIXTURE = ROOT / "docs" / "examples" / "product-smoke-csharp"

sys.dont_write_bytecode = True
from experimental_csharp_workspace import FACT_PROFILE_ID, FACT_SCOPE  # noqa: E402
import igd_daily  # noqa: E402
from run_windowsutility_csharp_syntax_probe import ProbeError, validate_facts  # noqa: E402


def digest_tree(root: Path) -> str:
    records: list[dict[str, str]] = []
    if root.exists():
        for path in sorted(root.rglob("*")):
            if path.is_file() and not path.is_symlink():
                records.append(
                    {
                        "path": path.relative_to(root).as_posix(),
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    }
                )
    return hashlib.sha256(json.dumps(records, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        timeout=90,
        check=False,
    )


def project_root(home: Path) -> Path:
    projects = [path for path in (home / "p").iterdir() if path.is_dir()]
    if len(projects) != 1:
        raise RuntimeError("expected one prepared project")
    return projects[0]


def first_create_lock_probe(temp: Path, source: Path) -> dict[str, object]:
    home = temp / "first-create-lock-home"
    entered = threading.Event()
    release = threading.Event()
    call_guard = threading.Lock()
    call_count = 0
    result: dict[str, object] = {}
    failures: list[BaseException] = []
    original = igd_daily.initialize_workspace

    def delayed_initialize(*args: object, **kwargs: object) -> object:
        nonlocal call_count
        with call_guard:
            call_count += 1
            current_call = call_count
        if current_call == 1:
            entered.set()
            if not release.wait(timeout=30):
                raise RuntimeError("first-create lock probe timed out")
        return original(*args, **kwargs)

    def create() -> None:
        try:
            result.update(igd_daily.prepare_project(source, home, "First create lock probe"))
        except BaseException as error:
            failures.append(error)

    igd_daily.initialize_workspace = delayed_initialize
    thread = threading.Thread(target=create, daemon=True)
    try:
        thread.start()
        if not entered.wait(timeout=20):
            raise RuntimeError("first prepare did not enter workspace preparation")
        try:
            igd_daily.prepare_project(source, home, "Concurrent duplicate")
        except igd_daily.DailyLaunchError as error:
            second_error = str(error)
        else:
            second_error = ""
    finally:
        release.set()
        thread.join(timeout=120)
        igd_daily.initialize_workspace = original
    if thread.is_alive() or failures:
        raise RuntimeError(f"first-create lock owner failed: {failures!r}")
    roots = [path for path in (home / "p").iterdir() if path.is_dir()]
    if "already open" not in second_error or result.get("action") != "created" or len(roots) != 1 or call_count != 1:
        raise RuntimeError(
            f"first-create lock probe failed: second={second_error!r}, action={result.get('action')!r}, "
            f"roots={len(roots)}, initializeCalls={call_count}"
        )
    return {
        "id": "concurrent-first-create-lock",
        "expectedFailureObserved": True,
        "secondPrepareBlockedBeforePreparation": True,
        "singleAtomicProjectCreated": True,
    }


def file_fact_cardinality_probes(home: Path) -> list[dict[str, object]]:
    facts_path = project_root(home) / "workspace" / "snapshot" / "artifacts" / "code-facts.json"
    baseline = json.loads(facts_path.read_text(encoding="utf-8"))
    snapshot = baseline["sourceDigests"]
    file_fact = next(fact for fact in baseline["facts"] if fact["kind"] == "file")
    probes: list[dict[str, object]] = []

    missing = json.loads(json.dumps(baseline))
    missing["facts"] = [fact for fact in missing["facts"] if fact["id"] != file_fact["id"]]
    duplicate = json.loads(json.dumps(baseline))
    duplicate_fact = dict(file_fact)
    duplicate_fact["id"] = file_fact["id"] + ".duplicate"
    duplicate["facts"].append(duplicate_fact)
    duplicate["facts"].sort(key=lambda fact: fact["id"])

    for identifier, candidate in (("missing-file-fact", missing), ("duplicate-file-fact", duplicate)):
        try:
            validate_facts(
                candidate,
                snapshot,
                baseline["sourceRoot"],
                expected_scope=FACT_SCOPE,
                expected_profile_id=FACT_PROFILE_ID,
            )
        except ProbeError as error:
            observed = "exactly one file fact per source digest entry" in str(error)
        else:
            observed = False
        if not observed:
            raise RuntimeError(f"syntax file-fact cardinality probe failed: {identifier}")
        probes.append({"id": identifier, "expectedFailureObserved": True, "sourceDigestCardinalityEnforced": True})
    return probes


def write_report(path: Path, probes: list[dict[str, object]]) -> None:
    report = {
        "artifactRole": "intentgraph-daily-launch-negative-probes-report",
        "status": "intentgraph-daily-launch-negative-probes-passed",
        "scope": "p9.34-local-csharp-daily-launch",
        "result": "pass",
        "probeCount": len(probes),
        "probes": probes,
        "authority": {
            "targetRepositoryMutation": False,
            "browserLaunched": False,
            "serverLeftRunning": False,
            "networkRequired": False,
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    out_index = sys.argv.index("--out") + 1 if "--out" in sys.argv else -1
    if out_index <= 0 or out_index >= len(sys.argv):
        raise SystemExit("usage: run_igd_daily_negative_probes.py --out <report.json>")
    out = Path(sys.argv[out_index]).resolve()
    if out == CLI.resolve() or out.is_relative_to(FIXTURE.resolve()):
        raise SystemExit("error: output must not overwrite launcher inputs")

    probes: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="igd-daily-probes-") as temporary:
        temp = Path(temporary)
        source = temp / "source"
        baseline_home = temp / "baseline-home"
        shutil.copytree(FIXTURE, source)
        prepared = run("prepare", str(source), "--home", str(baseline_home), "--title", "Negative probe")
        if prepared.returncode != 0:
            raise RuntimeError(f"positive baseline failed: {prepared.stderr}")
        baseline_source = digest_tree(source)
        probes.append(first_create_lock_probe(temp, source))
        probes.extend(file_fact_cardinality_probes(baseline_home))

        def probe(
            identifier: str,
            expected: str,
            mutate: Callable[[Path, Path], None],
            command: Callable[[Path, Path], subprocess.CompletedProcess[str]] | None = None,
            *,
            source_may_change: bool = False,
        ) -> None:
            home = temp / f"home-{identifier}"
            shutil.copytree(baseline_home, home)
            mutate(source, home)
            before_home = digest_tree(home)
            before_source = digest_tree(source)
            result = (command or (lambda current_source, current_home: run("prepare", str(current_source), "--home", str(current_home))))(source, home)
            observed = result.returncode == 2 and expected in result.stderr
            home_unchanged = digest_tree(home) == before_home
            source_unchanged = digest_tree(source) == before_source
            if source_may_change:
                shutil.rmtree(source)
                shutil.copytree(FIXTURE, source)
            if not observed or not home_unchanged or not source_unchanged:
                raise RuntimeError(
                    f"probe failed: {identifier}; rc={result.returncode}; stderr={result.stderr!r}; "
                    f"homeUnchanged={home_unchanged}; sourceUnchanged={source_unchanged}"
                )
            probes.append(
                {
                    "id": identifier,
                    "expectedFailureObserved": True,
                    "expectedError": expected,
                    "workspaceTreeUnchanged": home_unchanged,
                    "sourceTreeUnchanged": source_unchanged,
                }
            )

        probe(
            "source-content-stale",
            "source changed since the recorded snapshot",
            lambda current_source, _home: (current_source / "Program.cs").write_text(
                (current_source / "Program.cs").read_text(encoding="utf-8") + "\n// changed\n", encoding="utf-8"
            ),
            source_may_change=True,
        )
        probe(
            "missing-launch-record",
            "workspace and launch record must both exist",
            lambda _source, home: (project_root(home) / "intentgraph.launch.json").unlink(),
        )
        probe(
            "tampered-launch-identity",
            "launch record does not match",
            lambda _source, home: _mutate_json(project_root(home) / "intentgraph.launch.json", "sourceIdentityDigest", "sha256:" + "0" * 64),
        )
        probe(
            "tampered-project-state",
            "project state does not match nested snapshot provenance",
            lambda _source, home: _mutate_nested_json(
                project_root(home) / "workspace" / "intentgraph.project.json", ("project", "sourceDigest"), "sha256:" + "0" * 64
            ),
        )

        overlap_home = source / ".intentgraph-data"
        overlap = run("prepare", str(source), "--home", str(overlap_home))
        if overlap.returncode != 2 or "must not overlap" not in overlap.stderr or overlap_home.exists() or digest_tree(source) != baseline_source:
            raise RuntimeError("overlapping-home probe failed")
        probes.append({"id": "source-home-overlap", "expectedFailureObserved": True, "workspaceAbsent": True, "sourceTreeUnchanged": True})

        empty_source = temp / "empty-source"
        empty_home = temp / "empty-home"
        empty_source.mkdir()
        empty = run("prepare", str(empty_source), "--home", str(empty_home))
        empty_projects = [path for path in (empty_home / "p").iterdir() if path.is_dir()] if (empty_home / "p").is_dir() else []
        if empty.returncode != 2 or "at least one C# file" not in empty.stderr or empty_projects:
            raise RuntimeError("empty-source probe failed")
        probes.append(
            {
                "id": "empty-csharp-source",
                "expectedFailureObserved": True,
                "workspaceAbsent": True,
                "onlyStableLockMetadataAllowed": True,
            }
        )

        reparse_source = temp / "reparse-source"
        reparse_home = temp / "reparse-home"
        reparse_target = temp / "reparse-target"
        shutil.copytree(FIXTURE, reparse_source)
        reparse_target.mkdir()
        (reparse_target / "Escaped.cs").write_text("class Escaped {}\n", encoding="utf-8")
        reparse_directory = reparse_source / "linked-source"
        if os.name == "nt":
            created = subprocess.run(
                ["cmd.exe", "/d", "/c", "mklink", "/J", str(reparse_directory), str(reparse_target)],
                text=True,
                capture_output=True,
                encoding="utf-8",
                check=False,
            )
            if created.returncode != 0:
                raise RuntimeError(f"could not create C# intake junction probe: {created.stderr or created.stdout}")
        else:
            reparse_directory.symlink_to(reparse_target, target_is_directory=True)
        reparse = run("prepare", str(reparse_source), "--home", str(reparse_home))
        reparse_observed = reparse.returncode == 2 and "must not contain reparse points" in reparse.stderr
        reparse_directory.rmdir()
        if not reparse_observed or not (reparse_target / "Escaped.cs").is_file():
            raise RuntimeError(f"C# intake reparse probe failed: {reparse.stderr}")
        probes.append(
            {
                "id": "csharp-directory-reparse-point",
                "expectedFailureObserved": True,
                "resolvedSourceContainmentEnforced": True,
                "reparseTargetUnchanged": True,
            }
        )

        home_junction_target = temp / "home-junction-target"
        home_junction = temp / "home-junction"
        home_junction_target.mkdir()
        home_sentinel = home_junction_target / "preserved.txt"
        home_sentinel.write_text("preserve\n", encoding="utf-8")
        if os.name == "nt":
            created = subprocess.run(
                ["cmd.exe", "/d", "/c", "mklink", "/J", str(home_junction), str(home_junction_target)],
                text=True,
                capture_output=True,
                encoding="utf-8",
                check=False,
            )
            if created.returncode != 0:
                raise RuntimeError(f"could not create IntentGraph home junction probe: {created.stderr or created.stdout}")
        else:
            home_junction.symlink_to(home_junction_target, target_is_directory=True)
        home_reparse = run("prepare", str(source), "--home", str(home_junction))
        home_reparse_observed = (
            home_reparse.returncode == 2
            and "IntentGraph home must not contain reparse points" in home_reparse.stderr
            and not (home_junction_target / "p").exists()
            and home_sentinel.is_file()
        )
        home_junction.rmdir()
        if not home_reparse_observed:
            raise RuntimeError(f"IntentGraph home reparse probe failed: {home_reparse.stderr}")
        probes.append(
            {
                "id": "intentgraph-home-reparse-point",
                "expectedFailureObserved": True,
                "workspaceAbsent": True,
                "reparseTargetUnchanged": True,
            }
        )

        invalid_home = temp / "invalid-port-home"
        invalid = run("open", str(source), "--home", str(invalid_home), "--port", "65536", "--no-browser")
        if invalid.returncode != 2 or "port must be between" not in invalid.stderr or invalid_home.exists():
            raise RuntimeError("invalid-port probe failed")
        probes.append({"id": "invalid-port", "expectedFailureObserved": True, "workspaceAbsent": True, "browserLaunched": False})

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as occupied_socket:
            occupied_socket.bind(("127.0.0.1", 0))
            occupied_socket.listen(1)
            occupied_port = occupied_socket.getsockname()[1]
            occupied_home = temp / "occupied-port-home"
            occupied = run("open", str(source), "--home", str(occupied_home), "--port", str(occupied_port), "--no-browser")
        if occupied.returncode != 2 or "loopback port is unavailable" not in occupied.stderr or occupied_home.exists():
            raise RuntimeError("occupied-port probe failed")
        probes.append({"id": "occupied-explicit-port", "expectedFailureObserved": True, "workspaceAbsent": True, "browserLaunched": False})

        mtime_home = temp / "mtime-home"
        shutil.copytree(baseline_home, mtime_home)
        os.utime(source / "Program.cs", None)
        mtime = run("prepare", str(source), "--home", str(mtime_home))
        if mtime.returncode != 0 or json.loads(mtime.stdout)["action"] != "resumed":
            raise RuntimeError("mtime-only resume probe failed")
        probes.append({"id": "mtime-only-resume", "expectedPassObserved": True, "sourceTextEqualityNotRequired": True})

        ignored_home = temp / "ignored-home"
        shutil.copytree(baseline_home, ignored_home)
        (source / "bin").mkdir()
        (source / "bin" / "Generated.cs").write_text("class Ignored {}\n", encoding="utf-8")
        ignored = run("prepare", str(source), "--home", str(ignored_home))
        shutil.rmtree(source / "bin")
        if ignored.returncode != 0 or json.loads(ignored.stdout)["action"] != "resumed":
            raise RuntimeError("bin-ignore resume probe failed")
        probes.append({"id": "bin-obj-ignored-resume", "expectedPassObserved": True})

        launch_text = (project_root(baseline_home) / "intentgraph.launch.json").read_text(encoding="utf-8")
        if str(source.resolve()) in launch_text:
            raise RuntimeError("launch record persisted the absolute source path")
        probes.append({"id": "absolute-source-path-not-persisted", "expectedPassObserved": True})

    write_report(out, probes)
    print(json.dumps({"result": "pass", "probeCount": len(probes), "out": out.as_posix()}, sort_keys=True))
    return 0


def _mutate_json(path: Path, key: str, value: object) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    data[key] = value
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _mutate_nested_json(path: Path, keys: tuple[str, ...], value: object) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    current = data
    for key in keys[:-1]:
        current = current[key]
    current[keys[-1]] = value
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
