"""Command-line entry points (IF-02)."""

from __future__ import annotations

import argparse
import os
import sys
import traceback
from typing import TYPE_CHECKING

from nanopnp.cli.common import _configure_logging
from nanopnp.cli.parser import build_parser
from nanopnp.cli.workbench import _env
from nanopnp.core.errors import EXIT_OK, EXIT_UNEXPECTED, classify

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Sequence

__all__ = ["build_parser", "main"]


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ``nanopnp`` command-line interface and return its process exit status."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        if getattr(args, "env_flag", False):
            return _env(argparse.Namespace(json=getattr(args, "json", False)))
        parser.print_help()
        return EXIT_OK

    # Separate destinations before and after the subcommand: a shared one would collapse
    # `-vv run -v` to one level.
    _configure_logging(args.verbose + getattr(args, "subcommand_verbose", 0), args.log_file)
    if args.command == "reproduce" and args.tolerance is None:
        from nanopnp.api.reproduce import DEFAULT_TOLERANCE

        args.tolerance = DEFAULT_TOLERANCE

    threads = getattr(args, "threads", None)
    if threads is not None:
        from nanopnp.sweep.run import THREAD_VARIABLES

        for var in THREAD_VARIABLES:
            os.environ[var] = str(threads)

    handler = args.handler
    try:
        code: int = handler(args)
    except SystemExit:
        raise
    except BaseException as error:
        code = classify(error)
        if args.traceback:
            traceback.print_exc(file=sys.stderr)
        else:
            print(f"nanopnp {args.command}: {error}", file=sys.stderr)
            if code == EXIT_UNEXPECTED:
                print(
                    f"nanopnp {args.command}: unexpected {type(error).__name__}; "
                    "re-run with --traceback",
                    file=sys.stderr,
                )
        return code
    return code


if __name__ == "__main__":  # pragma: no cover - run as a script, never imported by a test
    sys.exit(main())
