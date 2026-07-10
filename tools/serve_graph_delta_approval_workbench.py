"""Serve the static graph-delta approval workbench for user review."""

from __future__ import annotations

import argparse
import functools
import http.server
import socketserver
import webbrowser
from pathlib import Path


DEFAULT_ROOT = Path("generated/product-surfaces/graph-delta-approval-workbench/p8.60")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8762


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve the P8.60 graph-delta approval workbench locally.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-open", action="store_true", help="Do not open the browser automatically.")
    args = parser.parse_args()

    root = args.root.resolve()
    index = root / "index.html"
    if not index.exists():
        raise SystemExit(f"Workbench index not found: {index}")

    handler = functools.partial(QuietHandler, directory=str(root))
    with socketserver.TCPServer((args.host, args.port), handler) as httpd:
        url = f"http://{args.host}:{args.port}/index.html"
        print("IntentGraph graph-delta approval workbench review server")
        print(f"Serving: {root}")
        print(f"Open:    {url}")
        print("Review response contract: accept | revise | blocked")
        print("Press Ctrl+C to stop.")
        if not args.no_open:
            webbrowser.open(url)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
