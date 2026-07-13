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

from experimental_csharp_project import (
    PROJECT_SCHEMA_VERSION,
    PROPOSAL_AUTHORITY,
    PROPOSAL_ROLE,
    PROPOSAL_SCOPE,
    PROPOSAL_STATUS,
    initialize_project,
    validate_project_workspace,
)
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


def server_proposal(code_fact_id: str) -> dict[str, Any]:
    return {
        "artifactRole": PROPOSAL_ROLE,
        "schemaVersion": PROJECT_SCHEMA_VERSION,
        "scope": PROPOSAL_SCOPE,
        "id": "server-proposal",
        "workItemId": "server-request",
        "mappingId": "mapping.server-request.candidate",
        "title": "Server-recorded review proposal",
        "summary": "Exercise the local review-only proposal intake without editing source code.",
        "applicationStatus": PROPOSAL_STATUS,
        "graphDelta": {
            "addedNodes": [
                {
                    "id": "verification.server-proposal",
                    "category": "verification",
                    "label": "Server proposal verification requirement",
                    "details": {"kind": "server-smoke", "result": "required-not-run", "summary": "A local review-only verification requirement."},
                }
            ],
            "changedNodeIds": [code_fact_id],
            "addedEdges": [
                {
                    "id": "edge.server-proposal.verifies",
                    "kind": "verifies",
                    "source": "intent.server-request",
                    "target": "verification.server-proposal",
                    "details": {"status": "required-not-run"},
                }
            ],
        },
        "codeDiffs": [],
        "verificationRequirements": [{"id": "verification.requirement.server-proposal", "kind": "server-smoke", "summary": "Review the proposal before any source action."}],
        "evidenceRequirements": [{"id": "evidence.requirement.server-proposal", "kind": "server-smoke", "summary": "Collect evidence only through a later authorized boundary."}],
        "authority": PROPOSAL_AUTHORITY,
    }


def run(snapshot: Path, output: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="p9.15-server-smoke-") as temporary:
        root = Path(temporary)
        workspace = root / "project"
        initialize_project(snapshot, workspace, "server-smoke-project", "Server smoke project")
        before_state, before_manifest, _, before_data = validate_project_workspace(workspace)
        code_fact_id = next(
            fact["id"]
            for fact in before_data["facts"]["facts"]
            if isinstance(fact, dict) and fact.get("kind") == "method"
        )
        server = make_server(workspace, "127.0.0.1", 0)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        host, port = server.server_address[:2]
        base_url = f"http://{host}:{port}"
        probes: list[dict[str, Any]] = []
        try:
            status, html, headers = request(base_url + "/")
            probes.append({"id": "serves-deferred-interactive-html", "passed": status == 200 and len(html) < 100000 and b"newWorkTrigger" in html and b"mapCodeTrigger" in html and b"importProposalTrigger" in html and b"__intentGraphLoadProjection" in html and b"/api/work-requests" in html and b"/api/mapping-candidates" in html and b"/api/change-proposals" in html and b"spiralPoint" in html and b"completeGraph" in html and b"semanticEdgeIds" in html and b"edge.low-detail" in html and b"'display':'none'" in html and b"search-match" in html and b"selection-neighbor" in html and b"visibilityUpdates" in html and b"state.cy.destroy" not in html and b"name:'cose'" not in html and headers.get("Content-Security-Policy") is not None})
            status, projection_bytes, _ = request(base_url + "/api/projection")
            initial_projection = json.loads(projection_bytes)
            probes.append({"id": "serves-project-projection", "passed": status == 200 and initial_projection["workflow"]["workItems"] == [] and initial_projection["graph"]["defaultView"]["id"] == "all" and set(initial_projection["graph"]["views"]["all"]["nodeIds"]) == {node["id"] for node in initial_projection["graph"]["nodes"]}})
            status, created_bytes, _ = request(base_url + "/api/work-requests", method="POST", body={"workId": "server-request", "title": "Server-recorded request", "request": "Record a local work request without editing the source project."})
            created = json.loads(created_bytes)
            probes.append({"id": "records-work-request-only-in-project-workspace", "passed": status == 201 and created["result"] == "pass" and created["workItemId"] == "server-request"})
            status, updated_bytes, _ = request(base_url + "/api/projection")
            updated = json.loads(updated_bytes)
            probes.append({"id": "reloads-updated-projection", "passed": status == 200 and len(updated["workflow"]["workItems"]) == 1 and updated["workflow"]["workItems"][0]["id"] == "server-request"})
            status, mapped_bytes, _ = request(base_url + "/api/mapping-candidates", method="POST", body={"workId": "server-request", "codeFactId": code_fact_id, "rationale": "Selected from the local code graph for smoke coverage."})
            mapped = json.loads(mapped_bytes)
            probes.append({"id": "records-code-mapping-only-in-project-workspace", "passed": status == 201 and mapped["result"] == "pass" and mapped["codeFactCount"] == 1})
            status, mapped_projection_bytes, _ = request(base_url + "/api/projection")
            mapped_projection = json.loads(mapped_projection_bytes)
            probes.append({"id": "reloads-mapped-projection", "passed": status == 200 and len(mapped_projection["workflow"]["mappings"]) == 1 and mapped_projection["workflow"]["mappings"][0]["codeFactIds"] == [code_fact_id]})
            status, proposal_bytes, _ = request(base_url + "/api/change-proposals", method="POST", body={"proposal": server_proposal(code_fact_id)})
            proposal_result = json.loads(proposal_bytes)
            probes.append({"id": "records-review-only-change-proposal-in-project-workspace", "passed": status == 201 and proposal_result["result"] == "pass" and proposal_result["proposalId"] == "server-proposal" and proposal_result["targetRepositoryMutation"] is False})
            status, proposal_projection_bytes, _ = request(base_url + "/api/projection")
            proposal_projection = json.loads(proposal_projection_bytes)
            probes.append({"id": "reloads-review-only-proposal-delta", "passed": status == 200 and len(proposal_projection["workflow"]["changeProposals"]) == 1 and proposal_projection["changeReview"]["status"] == "review-required" and proposal_projection["authority"]["targetRepositoryMutation"] is False})
            try:
                request(base_url + "/api/work-requests", method="POST", body={"workId": "server-request", "title": "Duplicate", "request": "Duplicate identifier."})
            except HTTPError as error:
                duplicate = json.loads(error.read())
                probes.append({"id": "rejects-duplicate-work-id", "passed": error.code == 400 and "already exists" in duplicate.get("error", "")})
            else:
                probes.append({"id": "rejects-duplicate-work-id", "passed": False})
            try:
                request(base_url + "/api/mapping-candidates", method="POST", body={"workId": "server-request", "codeFactId": code_fact_id, "rationale": "Duplicate fact."})
            except HTTPError as error:
                duplicate_mapping = json.loads(error.read())
                probes.append({"id": "rejects-duplicate-code-mapping", "passed": error.code == 400 and "already contains" in duplicate_mapping.get("error", "")})
            else:
                probes.append({"id": "rejects-duplicate-code-mapping", "passed": False})
            invalid_proposal = server_proposal(code_fact_id)
            invalid_proposal["applicationStatus"] = "applied"
            try:
                request(base_url + "/api/change-proposals", method="POST", body={"proposal": invalid_proposal})
            except HTTPError as error:
                invalid = json.loads(error.read())
                probes.append({"id": "rejects-applied-proposal-claim", "passed": error.code == 400 and "must remain non-applied" in invalid.get("error", "")})
            else:
                probes.append({"id": "rejects-applied-proposal-claim", "passed": False})
            try:
                request(base_url + "/api/change-proposals", method="POST", body={"proposal": []})
            except HTTPError as error:
                malformed = json.loads(error.read())
                probes.append({"id": "rejects-non-object-proposal-payload", "passed": error.code == 400 and "proposal object" in malformed.get("error", "")})
            else:
                probes.append({"id": "rejects-non-object-proposal-payload", "passed": False})
            status, asset, _ = request(base_url + "/assets/cytoscape.min.js")
            probes.append({"id": "serves-local-graph-asset", "passed": status == 200 and len(asset) > 100000})
        finally:
            server.shutdown()
            thread.join(timeout=10)
            server.server_close()
        after_state, after_manifest, _, _ = validate_project_workspace(workspace)
        probes.append({"id": "snapshot-provenance-unchanged", "passed": before_manifest["source"] == after_manifest["source"] and before_state["project"] == after_state["project"] and len(after_state["workItems"]) == 1 and len(after_state["mappings"]) == 1 and len(after_state["changeProposals"]) == 1})
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
        "scope": "p9.19-interactive-loopback-proposal-intake",
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
