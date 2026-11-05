"""The argument parser, assembled from the command modules."""

from __future__ import annotations

import argparse
from pathlib import Path

from nanopnp.cli import building, running, sweeping, validating, workbench
from nanopnp.core.public import __version__

_DESCRIPTION = "Command-line entry points (IF-02)."


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser, importing nothing a subcommand does not need."""
    parser = argparse.ArgumentParser(prog="nanopnp", description=_DESCRIPTION)
    parser.add_argument("--version", action="version", version=f"nanopnp {__version__}")
    parser.add_argument(
        "--env",
        action="store_true",
        dest="env_flag",
        help="alias for 'nanopnp env': report the resolved environment and data locations",
    )
    parser.add_argument(
        "--json", action="store_true", default=False, help="write the result to stdout as JSON"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        dest="verbose",
        help="log at INFO; twice for DEBUG. Log records go to stderr",
    )
    parser.add_argument(
        "--log-file", type=Path, default=None, help="also write log records to this file"
    )
    parser.add_argument(
        "--traceback",
        action="store_true",
        default=False,
        help="print the traceback of a failure; suppressed by default, because a gate abort's "
        "diagnostic is the message (QR-12)",
    )
    subparsers = parser.add_subparsers(dest="command")

    running.register(subparsers)
    building.register(subparsers)
    sweeping.register(subparsers)
    validating.register(subparsers)
    workbench.register(subparsers)

    return parser
