"""Run a loopback-only smoke test for the interactive C# project workbench server."""

from __future__ import annotations

import argparse
import json
import tempfile
import threading
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from experimental_csharp_project import initialize_project, validate_project_workspace
from serve_experimental_csharp_project_workbench import LocalWorkbenchServerError, make_server


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def request(url: str, *, method: str = "GET", body: dict[str, Any] | None = None) -> tuple[int, bytes, dict[str, str]]:
    data = None if body is None else json.dumps(body, ensure_ascii=True).encode("utf-8")
    headers = {} if data is None else {"Content-Type": "application/json"}
    response = urlopen(Request(url, data=data, headers=headers, method=method), timeout=15)
    with response:
        return response.status, response.read(), dict(response.headers.items())


def run(snapshot: Path, output: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="p9.15-server-smoke-") as temporary:
        root = Path(temporary)
        workspace = root / "project"
        initialize_project(snapshot, workspace, "server-smoke-project", "Server smoke project")
        before_state, before_manifest, _, _ = validate_project_workspace(workspace)
        server = make_server(workspace, "127.0.0.1", 0)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        host, port = server.server_address[:2]
        base_url = f"http://{host}:{port}"
        probes: list[dict[str, Any]] = []
        try:
            status, html, headers = request(base_url + "/")
            probes.append({"id": "serves-interactive-html", "passed": status == 200 and b"newWorkTrigger" in html and b"/api/work-requests" in html and headers.get("Content-Security-Policy") is not None})
            status, projection_bytes, _ = request(base_url + "/api/projection")
            initial_projection = json.loads(projection_bytes)
            probes.append({"id": "serves-project-projection", "passed": status == 200 and initial_projection["workflow"]["workItems"] == []})
            status, created_bytes, _ = request(base_url + "/api/work-requests", method="POST", body={"workId": "server-request", "title": "Server-recorded request", "request": "Record a local work request without editing the source project."})
            created = json.loads(created_bytes)
            probes.append({"id": "records-work-request-only-in-project-workspace", "passed": status == 201 and created["result"] == "pass" and created["workItemId"] == "server-request"})
            status, updated_bytes, _ = request(base_url + "/api/projection")
            updated = json.loads(updated_bytes)
            probes.append({"id": "reloads-updated-projection", "passed": status == 200 and len(updated["workflow"]["workItems"]) == 1 and updated["workflow"]["workItems"][0]["id"] == "server-request"})
            try:
                request(base_url + "/api/work-requests", method="POST", body={"workId": "server-request", "title": "Duplicate", "request": "Duplicate identifier."})
            except HTTPError as error:
                duplicate = json.loads(error.read())
                probes.append({"id": "rejects-duplicate-work-id", "passed": error.code == 400 and "already exists" in duplicate.get("error", "")})
            else:
                probes.append({"id": "rejects-duplicate-work-id", "passed": False})
            status, asset, _ = request(base_url + "/assets/cytoscape.min.js")
            probes.append({"id": "serves-local-graph-asset", "passed": status == 200 and len(asset) > 100000})
        finally:
            server.shutdown()
            thread.join(timeout=10)
            server.server_close()
        after_state, after_manifest, _, _ = validate_project_workspace(workspace)
        probes.append({"id": "snapshot-provenance-unchanged", "passed": before_manifest["source"] == after_manifest["source"] and before_state["project"] == after_state["project"] and len(after_state["workItems"]) == 1})
        try:
            make_server(workspace, "0.0.0.0", 0)
        except LocalWorkbenchServerError as error:
            probes.append({"id": "rejects-non-loopback-host", "passed": "loopback" in str(error)})
        else:
            probes.append({"id": "rejects-non-loopback-host", "passed": False})
    result = "pass" if all(probe["passed"] for probe in probes) else "fail"
    report = {
        "artifactRole": "intentgraph-experimental-csharp-project-server-smoke-report",
        "status": "intentgraph-experimental-csharp-project-server-smoke-" + result,
        "scope": "p9.15-interactive-loopback-project-workbench",
        "result": result,
        "probeCount": len(probes),
        "probes": probes,
        "loopbackOnly": True,
        "targetRepositoryMutation": False,
        "automaticCodeApplication": False,
        "networkRequired": False,
    }
    write_json(output, report)
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-workspace", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = run(args.snapshot_workspace.resolve(), args.out.resolve())
    print(json.dumps({"result": report["result"], "probeCount": report["probeCount"]}, ensure_ascii=True))
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
