"""Launch the installed-style `igd open` flow and verify the loopback Workbench."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "igd.py"
SOURCE = ROOT / "docs" / "examples" / "product-smoke-csharp"

sys.dont_write_bytecode = True
from igd_daily import open_browser_when_ready  # noqa: E402


class FakeResponse:
    status = 200

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def observe_browser_launch_paths() -> tuple[dict[str, object], dict[str, bool]]:
    url = "http://127.0.0.1:43210/"
    events: list[str] = []
    readiness_calls = 0

    def readiness_then_success(request_url: str, *, timeout: float) -> FakeResponse:
        nonlocal readiness_calls
        readiness_calls += 1
        events.append(f"readiness:{request_url}:{timeout}")
        if readiness_calls == 1:
            raise OSError("not ready")
        return FakeResponse()

    def fake_browser_open(browser_url: str) -> bool:
        events.append(f"browser:{browser_url}")
        return True

    positive = open_browser_when_ready(
        url,
        attempts=3,
        readiness_timeout=0.01,
        retry_delay=0,
        urlopen=readiness_then_success,
        browser_open=fake_browser_open,
        sleep=lambda _delay: None,
    )

    failure_browser_called = False

    def never_ready(_request_url: str, *, timeout: float) -> FakeResponse:
        del timeout
        raise OSError("still not ready")

    def forbidden_browser(_browser_url: str) -> bool:
        nonlocal failure_browser_called
        failure_browser_called = True
        return True

    readiness_failure = open_browser_when_ready(
        url,
        attempts=3,
        readiness_timeout=0.01,
        retry_delay=0,
        urlopen=never_ready,
        browser_open=forbidden_browser,
        sleep=lambda _delay: None,
    )
    browser_failure = open_browser_when_ready(
        url,
        attempts=1,
        readiness_timeout=0.01,
        retry_delay=0,
        urlopen=lambda _request_url, timeout: FakeResponse(),
        browser_open=lambda _browser_url: False,
        sleep=lambda _delay: None,
    )
    checks = {
        "browserLaunchReadinessGated": events[-1] == f"browser:{url}" and readiness_calls == 2,
        "browserLaunchAttemptBounded": positive["attempts"] == 2 and readiness_failure["attempts"] == 3,
        "browserNotCalledWhenReadinessFails": not failure_browser_called and readiness_failure["ready"] is False,
        "browserOpenFailureObserved": browser_failure["ready"] is True and browser_failure["browserOpened"] is False,
    }
    evidence: dict[str, object] = {
        "positive": positive,
        "readinessFailure": readiness_failure,
        "browserOpenFailure": browser_failure,
        "realBrowserOpened": False,
    }
    return evidence, checks


def digest_tree(root: Path) -> str:
    records = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            records.append((path.relative_to(root).as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()))
    return hashlib.sha256(json.dumps(records, separators=(",", ":")).encode()).hexdigest()


def main() -> int:
    out_index = sys.argv.index("--out") + 1 if "--out" in sys.argv else -1
    if out_index <= 0 or out_index >= len(sys.argv):
        raise SystemExit("usage: run_igd_daily_server_smoke.py --out <report.json>")
    out = Path(sys.argv[out_index]).resolve()
    source_before = digest_tree(SOURCE)
    browser_evidence, browser_checks = observe_browser_launch_paths()
    with tempfile.TemporaryDirectory(prefix="igd-open-smoke-") as temporary:
        home = Path(temporary) / "home"
        process = subprocess.Popen(
            [sys.executable, str(CLI), "open", str(SOURCE), "--home", str(home), "--port", "0", "--no-browser"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        try:
            if process.stdout is None:
                raise RuntimeError("open smoke stdout unavailable")
            line = process.stdout.readline().strip()
            launch = json.loads(line)
            url = launch["url"]
            deadline = time.monotonic() + 15
            html = b""
            projection = b""
            while time.monotonic() < deadline:
                try:
                    with urllib.request.urlopen(url, timeout=2) as response:
                        html = response.read()
                    with urllib.request.urlopen(url + "api/projection", timeout=2) as response:
                        projection = response.read()
                    break
                except OSError:
                    time.sleep(0.1)
            if not html or not projection:
                raise RuntimeError("loopback Workbench did not become ready")
            concurrent = subprocess.run(
                [sys.executable, str(CLI), "open", str(SOURCE), "--home", str(home), "--port", "0", "--no-browser"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                encoding="utf-8",
                timeout=20,
                check=False,
            )
            model = json.loads(projection)
            if launch.get("result") != "serving" or launch.get("port") == 0 or launch.get("browserRequested") is not False:
                raise RuntimeError("open launch record is invalid")
            if b"IntentGraph" not in html or model.get("graph", {}).get("nodes") is None:
                raise RuntimeError("Workbench response is incomplete")
            workspace = Path(launch["workspace"])
            state = workspace / "intentgraph.project.json"
            state_before = hashlib.sha256(state.read_bytes()).hexdigest()
            with urllib.request.urlopen(url + "api/revision-head", timeout=2) as response:
                revision_head = json.loads(response.read())
            state_after = hashlib.sha256(state.read_bytes()).hexdigest()
            report = {
                "artifactRole": "intentgraph-daily-launch-server-smoke-report",
                "status": "intentgraph-daily-launch-server-smoke-passed",
                "scope": "p9.34-local-csharp-daily-launch",
                "result": "pass",
                "launch": {
                    "action": launch["action"],
                    "productVersion": launch["productVersion"],
                    "sourceDigest": launch["sourceDigest"],
                    "sourceFileCount": launch["sourceFileCount"],
                    "host": launch["host"],
                    "automaticPortAssigned": launch["port"] > 0,
                    "browserRequested": launch["browserRequested"],
                    "sourcePathPersisted": launch["sourcePathPersisted"],
                    "targetRepositoryMutation": launch["targetRepositoryMutation"],
                },
                "browserLaunchObservation": browser_evidence,
                "checks": {
                    "automaticPortAssigned": True,
                    "loopbackOnly": launch["host"] == "127.0.0.1",
                    "browserSuppressed": True,
                    "htmlNonblank": len(html) > 1024,
                    "projectionLoaded": bool(model["graph"]["nodes"]),
                    "revisionHeadLoaded": revision_head["artifactRole"].endswith("revision-head"),
                    "projectStateUnchangedByReads": state_before == state_after,
                    "sourceTreeUnchanged": source_before == digest_tree(SOURCE),
                    "concurrentSessionBlocked": concurrent.returncode == 2 and "already open" in concurrent.stderr,
                    **browser_checks,
                },
                "authority": {"targetRepositoryMutation": False, "realBrowserLaunched": False, "networkRequired": False},
            }
            if not all(report["checks"].values()):
                raise RuntimeError("one or more daily launch smoke checks failed")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    print(json.dumps({"result": "pass", "out": out.as_posix()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
