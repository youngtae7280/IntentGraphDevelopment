"""Serve the local interactive C# IntentGraph project workbench on loopback only."""

from __future__ import annotations

import argparse
import json
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from emit_experimental_csharp_fact_workbench import CYTOSCAPE_LICENSE_SOURCE, CYTOSCAPE_SOURCE
from experimental_csharp_project import (
    ProjectWorkspaceError,
    add_work_request,
    build_projection,
    canonical_json,
    render_server_html,
    validate_project_workspace,
)


LOOPBACK_HOSTS = {"127.0.0.1", "::1"}
MAX_REQUEST_BYTES = 32768
CONTENT_SECURITY_POLICY = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; frame-ancestors 'none'"


class LocalWorkbenchServerError(ValueError):
    """Raised when the interactive local workbench server boundary is invalid."""


def json_bytes(value: dict[str, Any]) -> bytes:
    return canonical_json(value)


def make_server(workspace: Path, host: str, port: int) -> ThreadingHTTPServer:
    workspace = workspace.resolve()
    if host not in LOOPBACK_HOSTS:
        raise LocalWorkbenchServerError("interactive workbench host must be an explicit loopback address")
    if not 0 <= port <= 65535:
        raise LocalWorkbenchServerError("interactive workbench port must be between 0 and 65535")
    validate_project_workspace(workspace)
    lock = threading.RLock()

    class Handler(BaseHTTPRequestHandler):
        server_version = "IntentGraphLocalWorkbench/0.1"

        def log_message(self, _format: str, *_args: object) -> None:
            return

        def respond(self, status: HTTPStatus, payload: bytes, content_type: str) -> None:
            self.send_response(status.value)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", CONTENT_SECURITY_POLICY)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(payload)

        def error_json(self, status: HTTPStatus, message: str) -> None:
            self.respond(status, json_bytes({"result": "fail", "error": message}), "application/json; charset=utf-8")

        def projection(self) -> dict[str, Any]:
            projection, _ = build_projection(workspace)
            return projection

        def do_GET(self) -> None:  # noqa: N802 - HTTP handler contract
            path = urlparse(self.path).path
            try:
                with lock:
                    if path in {"/", "/index.html"}:
                        self.respond(HTTPStatus.OK, render_server_html(self.projection()).encode("utf-8"), "text/html; charset=utf-8")
                        return
                    if path == "/api/projection":
                        self.respond(HTTPStatus.OK, json_bytes(self.projection()), "application/json; charset=utf-8")
                        return
                    if path == "/assets/cytoscape.min.js":
                        self.respond(HTTPStatus.OK, CYTOSCAPE_SOURCE.read_bytes(), "application/javascript; charset=utf-8")
                        return
                    if path == "/assets/cytoscape-license.txt":
                        self.respond(HTTPStatus.OK, CYTOSCAPE_LICENSE_SOURCE.read_bytes(), "text/plain; charset=utf-8")
                        return
                self.error_json(HTTPStatus.NOT_FOUND, "local workbench route does not exist")
            except (ProjectWorkspaceError, OSError) as error:
                self.error_json(HTTPStatus.INTERNAL_SERVER_ERROR, f"local workbench projection failed: {error}")

        def do_POST(self) -> None:  # noqa: N802 - HTTP handler contract
            path = urlparse(self.path).path
            if path != "/api/work-requests":
                self.error_json(HTTPStatus.NOT_FOUND, "local workbench route does not exist")
                return
            content_length = self.headers.get("Content-Length")
            if content_length is None:
                self.error_json(HTTPStatus.LENGTH_REQUIRED, "content length is required")
                return
            try:
                length = int(content_length)
            except ValueError:
                self.error_json(HTTPStatus.BAD_REQUEST, "content length is invalid")
                return
            if not 0 < length <= MAX_REQUEST_BYTES:
                self.error_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "request payload size is invalid")
                return
            if self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
                self.error_json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "content type must be application/json")
                return
            try:
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self.error_json(HTTPStatus.BAD_REQUEST, "request body must be a UTF-8 JSON object")
                return
            if not isinstance(payload, dict) or set(payload) != {"workId", "title", "request"} or any(not isinstance(payload.get(key), str) for key in payload):
                self.error_json(HTTPStatus.BAD_REQUEST, "work request must contain only workId, title, and request strings")
                return
            try:
                with lock:
                    result = add_work_request(workspace, payload["workId"], payload["title"], payload["request"])
                    self.respond(HTTPStatus.CREATED, json_bytes(result), "application/json; charset=utf-8")
            except ProjectWorkspaceError as error:
                self.error_json(HTTPStatus.BAD_REQUEST, str(error))

    return ThreadingHTTPServer((host, port), Handler)


def serve(workspace: Path, host: str, port: int) -> int:
    server = make_server(workspace, host, port)
    address, assigned_port = server.server_address[:2]
    print(json.dumps({"result": "serving", "url": f"http://{address}:{assigned_port}/", "host": address, "port": assigned_port, "targetRepositoryMutation": False, "networkRequired": False}, ensure_ascii=True))
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        return serve(args.workspace, args.host, args.port)
    except LocalWorkbenchServerError as error:
        print(f"error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
