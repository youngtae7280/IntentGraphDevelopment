"""IntentGraph Local Review Kit command line entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from experimental_csharp_project import ProjectWorkspaceError
from experimental_csharp_workspace import ExperimentalWorkspaceError
from igd_daily import DailyLaunchError, PRODUCT_VERSION, default_home, doctor, open_project, prepare_project, project_status
from igd_refresh import accept_refresh, discard_refresh, plan_refresh
from preflight_csharp_host_sdk_profile import PreflightError
from run_windowsutility_csharp_syntax_probe import ProbeError
from serve_experimental_csharp_project_workbench import LocalWorkbenchServerError


def emit(value: dict[str, object]) -> None:
    print(json.dumps(value, ensure_ascii=True, sort_keys=True))


def add_project_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("source_root", type=Path, help="C# repository or source directory to review.")
    parser.add_argument("--home", type=Path, default=None, help="IntentGraph local data root (defaults to LOCALAPPDATA).")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="igd",
        description="Open a local IntentGraph semantic-overlay Workbench over a C# project.",
    )
    parser.add_argument("--version", action="version", version=f"IntentGraph {PRODUCT_VERSION}")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Check local Python, .NET SDK, profile, and Workbench assets.")
    prepare = commands.add_parser("prepare", help="Create or validate the local review workspace without starting a server.")
    add_project_arguments(prepare)
    prepare.add_argument("--title", default=None, help="Project title used only on first creation.")
    status = commands.add_parser("status", help="Validate and summarize an existing local review workspace.")
    add_project_arguments(status)
    refresh = commands.add_parser("refresh", help="Plan or explicitly accept a reviewed source snapshot refresh.")
    add_project_arguments(refresh)
    refresh_action = refresh.add_mutually_exclusive_group()
    refresh_action.add_argument("--accept-plan", metavar="PLAN_ID", help="Accept the exact pending refresh plan and activate its candidate revision.")
    refresh_action.add_argument("--discard-plan", metavar="PLAN_ID", help="Discard the exact pending refresh plan without changing the active revision.")
    open_command = commands.add_parser("open", help="Create or resume the workspace, serve it locally, and open the browser.")
    add_project_arguments(open_command)
    open_command.add_argument("--title", default=None, help="Project title used only on first creation.")
    open_command.add_argument("--port", type=int, default=0, help="Loopback port; 0 chooses an available port.")
    open_command.add_argument("--no-browser", action="store_true", help="Serve without opening the default browser.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "doctor":
            emit(doctor())
            return 0
        home = args.home or default_home()
        if args.command == "prepare":
            emit(prepare_project(args.source_root, home, args.title))
            return 0
        if args.command == "status":
            result = project_status(args.source_root, home)
            emit(result)
            return 0 if result["result"] == "pass" else 1
        if args.command == "refresh":
            if args.accept_plan:
                emit(accept_refresh(args.source_root, args.accept_plan, home))
            elif args.discard_plan:
                emit(discard_refresh(args.source_root, args.discard_plan, home))
            else:
                emit(plan_refresh(args.source_root, home))
            return 0
        if args.command == "open":
            return open_project(args.source_root, home, args.title, port=args.port, open_browser=not args.no_browser)
        raise DailyLaunchError(f"unsupported command: {args.command}")
    except (
        DailyLaunchError,
        ExperimentalWorkspaceError,
        ProjectWorkspaceError,
        PreflightError,
        ProbeError,
        LocalWorkbenchServerError,
        OSError,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
