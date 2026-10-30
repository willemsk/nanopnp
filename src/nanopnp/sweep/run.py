"""A sweep member's record: its dataset row and its file in the sweep directory."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from nanopnp.core.errors import EXIT_OK
from nanopnp.core.hashing import Canonicalisable, canonical
from nanopnp.io.store import atomic_write_bytes

__all__ = [
    "MEMBERS_DIRNAME",
    "THREAD_VARIABLES",
    "MemberResult",
    "member_from_row",
    "pin_threads",
]

MEMBERS_DIRNAME = "members"

THREAD_VARIABLES: tuple[str, ...] = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
)


def pin_threads() -> dict[str, str]:
    """Pin the linear-algebra thread counts to one; return what was set."""
    for variable in THREAD_VARIABLES:
        os.environ[variable] = "1"
    return {variable: os.environ[variable] for variable in THREAD_VARIABLES}


@dataclass(frozen=True)
class MemberResult:
    """What one member did, as its dataset row and as its own file on disk.

    Parameters
    ----------
    status
        ok, failed or cancelled.
    error
        The diagnostic, verbatim, or None.
    """

    index: int
    point_id: str
    assignments: Mapping[str, Canonicalisable]
    wave: int
    status: str
    exit_class: int = EXIT_OK
    error: str | None = None
    quantities: Mapping[str, Canonicalisable] | None = None
    directory: str | None = None
    manifest: str | None = None
    solution: str | None = None
    seconds: float = 0.0
    iterations: int | None = None
    cached: bool = False
    warm_start: Mapping[str, Canonicalisable] | None = None
    wall_distance: Mapping[str, Canonicalisable] | None = None
    route_agreement: float | None = None

    def row(self) -> dict[str, Canonicalisable]:
        """Return this member's dataset row."""
        return {
            "index": self.index,
            "id": self.point_id,
            "assignments": dict(self.assignments),
            "wave": self.wave,
            "status": self.status,
            "exit_class": self.exit_class,
            "error": self.error,
            "quantities": None if self.quantities is None else dict(self.quantities),
            "directory": self.directory,
            "manifest": self.manifest,
            "solution": self.solution,
            "seconds": self.seconds,
            "iterations": self.iterations,
            "cached": self.cached,
            "warm_start": None if self.warm_start is None else dict(self.warm_start),
            "wall_distance": None if self.wall_distance is None else dict(self.wall_distance),
            "route_agreement": self.route_agreement,
        }

    def write(self, directory: Path) -> Path:
        """Write this member's record into the sweep's members/ directory, atomically."""
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{self.index:06d}.json"
        atomic_write_bytes(path, canonical(self.row()) + b"\n")
        return path


def member_from_row(row: Mapping[str, Canonicalisable]) -> MemberResult:
    """Rebuild a member's record from a row, such as a worker's return value or a file."""
    return MemberResult(
        index=int(row["index"]),
        point_id=str(row["id"]),
        assignments=dict(row["assignments"]),
        wave=int(row["wave"]),
        status=str(row["status"]),
        exit_class=EXIT_OK if row["exit_class"] is None else int(row["exit_class"]),
        error=None if row["error"] is None else str(row["error"]),
        quantities=None if row["quantities"] is None else dict(row["quantities"]),
        directory=None if row["directory"] is None else str(row["directory"]),
        manifest=None if row["manifest"] is None else str(row["manifest"]),
        solution=None if row["solution"] is None else str(row["solution"]),
        seconds=float(row["seconds"]),
        iterations=None if row.get("iterations") is None else int(row["iterations"]),
        cached=bool(row["cached"]),
        warm_start=None if row["warm_start"] is None else dict(row["warm_start"]),
        wall_distance=None if row["wall_distance"] is None else dict(row["wall_distance"]),
        route_agreement=(None if row["route_agreement"] is None else float(row["route_agreement"])),
    )
