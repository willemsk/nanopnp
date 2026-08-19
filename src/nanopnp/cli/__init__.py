"""Command-line entry points (IF-02).

The CLI drives the same stage objects as the Python API and the desktop shell
(SPECIFICATION.md section 5.1); it holds no logic of its own.
"""

from __future__ import annotations

import argparse
import platform
import sys
from collections.abc import Sequence

from nanopnp import __version__
from nanopnp.core.paths import CORRECTIONS_DIR


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ``nanopnp`` command-line interface.

    Parameters
    ----------
    argv
        Argument vector, defaulting to ``sys.argv[1:]``.

    Returns
    -------
    int
        Process exit status.
    """
    parser = argparse.ArgumentParser(prog="nanopnp", description=__doc__.splitlines()[0])
    parser.add_argument("--version", action="version", version=f"nanopnp {__version__}")
    parser.add_argument(
        "--env",
        action="store_true",
        help="report the resolved environment and data locations, then exit",
    )
    args = parser.parse_args(argv)

    if args.env:
        print(f"nanopnp {__version__}")
        print(f"python  {platform.python_version()} on {platform.platform()}")
        print(f"data    {CORRECTIONS_DIR}")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
