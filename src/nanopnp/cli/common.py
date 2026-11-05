"""Helpers shared by the command modules of the command line."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn, TextIO

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Sequence

    from nanopnp.core.hashing import Canonicalisable
    from nanopnp.io.store import Store

    Subparsers = argparse._SubParsersAction[argparse.ArgumentParser]


_LEVELS = (logging.WARNING, logging.INFO, logging.DEBUG)


def _common(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument(
        "--json",
        action="store_true",
        default=argparse.SUPPRESS,
        help="write the result to stdout as JSON",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=argparse.SUPPRESS,
        dest="subcommand_verbose",
        help="log at INFO; twice for DEBUG. Log records go to stderr",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=argparse.SUPPRESS,
        help="also write log records to this file",
    )
    parser.add_argument(
        "--traceback",
        action="store_true",
        default=argparse.SUPPRESS,
        help="print the traceback of a failure; suppressed by default, because a gate abort's "
        "diagnostic is the message (QR-12)",
    )
    return parser


def _configure_logging(verbose: int, log_file: Path | None) -> None:
    level = _LEVELS[min(verbose, len(_LEVELS) - 1)]
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    if log_file is not None:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=level,
        handlers=handlers,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        force=True,
    )


def _emit(payload: dict[str, Canonicalisable], lines: Sequence[str], *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))
        return
    for line in lines:
        print(line)


class _Progress:
    def __init__(self, stream: TextIO) -> None:
        self._stream = stream
        self._reporting = False
        self._steps = 0

    def _print(self, line: str) -> None:
        print(line, file=self._stream, flush=True)

    def __call__(self, name: str, index: int, total: int) -> None:
        from nanopnp.core.stages import describe

        self._print(f"stage {describe(name).number:>2} {name}")

    def rung(
        self, name: str, stage: int, index: int, total: int, reporting: bool, tolerance: float
    ) -> None:
        self._print(f"  rung {index + 1}/{total} {name}")
        self._reporting = reporting
        self._steps = 0

    def step(
        self,
        iteration: int,
        residual: float,
        update: float,
        damping: float,
        trials: int,
        forced: bool,
    ) -> None:
        self._steps += 1

    def rung_solved(self, name: str, seconds: float, iterations: int) -> None:
        steps = f"{self._steps} Newton steps, " if self._reporting else ""
        self._print(f"    {steps}{seconds:.3f} s")

    def close(self) -> None:
        return None


def _progress(args: argparse.Namespace) -> _Progress | None:
    shown = sys.stderr.isatty() if args.progress is None else args.progress
    return _Progress(sys.stderr) if shown else None


def _refuse(args: argparse.Namespace, message: str) -> NoReturn:
    args.parser.error(message)
    raise AssertionError("ArgumentParser.error returns no value")  # pragma: no cover


def _destination(args: argparse.Namespace, suffix: str) -> Path:
    # Refused before anything is built: left to the write, a bad destination would exit 3 or 1
    # instead of 2.
    out = Path(args.out)
    if not out.name or out.is_dir():
        args.parser.error(f"--out {out} is a directory; name the {suffix} file to write")
    if not out.parent.is_dir():
        args.parser.error(f"--out {out}: the directory {out.parent} does not exist")
    return out


def _positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not a valid integer") from None
    if value < 1:
        raise argparse.ArgumentTypeError(f"must be at least 1, found {value}")
    return value


def _positive_nm(text: str) -> float:
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not a valid number") from None
    if not 0.0 < value < float("inf"):
        raise argparse.ArgumentTypeError(f"{text!r} is not a positive length in nm")
    return value


def _store(args: argparse.Namespace) -> Store:
    from nanopnp.io.store import Store

    return Store(args.store)


def _progress_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--progress",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="print each stage and solver rung to stderr as it starts; "
        "by default when stderr is a terminal",
    )
