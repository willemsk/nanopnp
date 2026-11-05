"""The gui and env commands."""

from __future__ import annotations

import argparse
import importlib.util
import os
import platform
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.cli.common import _common, _emit, _refuse
from nanopnp.core.errors import EXIT_OK
from nanopnp.core.paths import (
    CORRECTIONS_DIR,
    DATA_DIR,
    GEOMETRY_DIR,
    REFERENCE_DATA_VARIABLE,
    STORE_ROOT_VARIABLE,
    reference_data_root,
    store_root,
)
from nanopnp.core.public import __version__

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.cli.common import Subparsers
    from nanopnp.core.hashing import Canonicalisable


def _environment() -> dict[str, Canonicalisable]:
    reference = reference_data_root()
    return {
        "version": __version__,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "data": str(DATA_DIR),
        "corrections": str(CORRECTIONS_DIR),
        "geometry": str(GEOMETRY_DIR),
        "store": str(Path(store_root()).resolve()),
        STORE_ROOT_VARIABLE: os.environ.get(STORE_ROOT_VARIABLE),
        "reference_data": str(reference) if reference is not None else None,
        REFERENCE_DATA_VARIABLE: os.environ.get(REFERENCE_DATA_VARIABLE),
    }


def _env(args: argparse.Namespace) -> int:
    found = _environment()
    lines = [
        f"nanopnp   {found['version']}",
        f"python    {found['python']} on {found['platform']}",
        f"data      {found['data']}",
        f"store     {found['store']} "
        f"({STORE_ROOT_VARIABLE}={found[STORE_ROOT_VARIABLE] or 'unset'})",
        f"reference {found['reference_data'] or 'none'} "
        f"({REFERENCE_DATA_VARIABLE}={found[REFERENCE_DATA_VARIABLE] or 'unset'})",
    ]
    _emit(found, lines, as_json=bool(getattr(args, "json", False)))
    return EXIT_OK


def _gui(args: argparse.Namespace) -> int:
    from nanopnp.core.stages import MissingExtraError

    for package in ("fastapi", "uvicorn", "nicegui"):
        if importlib.util.find_spec(package) is None:
            raise MissingExtraError(
                f"nanopnp gui needs the 'gui' extra: {package!r} is not installed. Install the "
                "extras with `uv sync --all-extras`",
                name=package,
            )
    # Named by string: gui sits above cli in the layer order, so an import would point upward.
    server = importlib.import_module("nanopnp.gui.web.server")
    if args.state is not None and args.state not in server.STATES:
        _refuse(args, f"--state {args.state!r}: the states are {', '.join(server.STATES)}")
    if args.case is not None and args.state is not None:
        _refuse(args, "give a case file or --state, not both")
    code: int = server.serve(
        case=args.case,
        state=args.state,
        port=args.port,
        no_browser=args.no_browser,
        dev=args.dev,
        as_json=bool(getattr(args, "json", False)),
    )
    return code


def register(subparsers: Subparsers) -> None:
    """Add the gui and env subcommands."""
    gui = _common(
        subparsers.add_parser(
            "gui",
            help="serve the browser workbench on 127.0.0.1 (the 'gui' extra)",
            description="Serve the workbench on 127.0.0.1. The server prints one line, "
            "'nanopnp-gui ready <url>' (with --json, {\"ready\": <url>}), and stops when its "
            "standard input closes or on SIGINT or SIGTERM.",
        )
    )
    gui.add_argument("case", nargs="?", type=Path, default=None, help="a case file to show")
    gui.add_argument("--state", default=None, help="a fixture state in place of a case")
    gui.add_argument("--port", type=int, default=0, help="the port; 0 picks a free one")
    gui.add_argument("--no-browser", action="store_true", help="print the address, open nothing")
    gui.add_argument("--dev", action="store_true", help="reload on a change to the screens' source")
    gui.set_defaults(handler=_gui)

    env = _common(subparsers.add_parser("env", help="report the environment and data locations"))
    env.set_defaults(handler=_env)
