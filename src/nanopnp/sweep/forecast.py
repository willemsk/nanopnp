"""What a sweep rebuilds, forecast from the plan before any member runs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from nanopnp.core.stages import describe, walk_order
from nanopnp.pipeline.run import Identity, keyed_walk

if TYPE_CHECKING:
    from nanopnp.io.store import Store
    from nanopnp.pipeline.extension import FunctionStage
    from nanopnp.sweep.plan import SweepPlan

__all__ = ["Forecast", "forecast"]


@dataclass(frozen=True)
class Forecast:
    """The stages a sweep builds and reuses, and the axes that move them.

    Parameters
    ----------
    builds
        The number of points that build each stage.
    reused
        The number of points that find each stage already built.
    points
        Each point's built stages, in plan order.
    axes
        The stages each axis moves, by axis name.
    """

    builds: Mapping[str, int]
    reused: Mapping[str, int]
    points: tuple[tuple[str, ...], ...]
    axes: Mapping[str, tuple[str, ...]]

    def summary(self) -> dict[str, object]:
        """Return the forecast as plain data, for the CLI's JSON."""
        return {
            "builds": dict(self.builds),
            "reused": dict(self.reused),
            "points": [list(stages) for stages in self.points],
            "axes": {name: list(stages) for name, stages in self.axes.items()},
        }

    def warnings(self) -> tuple[str, ...]:
        """Return a line for each axis that moves a stage before the solve."""
        order = walk_order()
        before = order[: order.index("solve")] if "solve" in order else ()
        costly = {name for name in before if not describe(name).key_is_artefact}
        lines: list[str] = []
        for axis, moved in self.axes.items():
            early = [name for name in moved if name in costly]
            if not early:
                continue
            counts = " and ".join(f"{self.builds.get(name, 0)} {name}" for name in early)
            lines.append(
                f"axis {axis!r} moves {', '.join(moved)}; {counts} builds come before the solves"
            )
        return tuple(lines)


def forecast(
    plan: SweepPlan,
    *,
    store: Store,
    stages: Mapping[str, FunctionStage] | None = None,
) -> Forecast:
    """Key every point of ``plan`` against ``store`` and report what a run would build.

    No stage runs and the store gains nothing.
    """
    planned: set[str] = set()
    walked: list[dict[str, Identity]] = [
        keyed_walk(resolved, store=store, stages=stages, planned=planned)
        for resolved in plan.resolved_members
    ]
    order = _order(walked, stages)
    builds = {
        name: sum(1 for point in walked if name in point and point[name].built) for name in order
    }
    reused = {
        name: sum(1 for point in walked if name in point and not point[name].built)
        for name in order
    }
    points = tuple(
        tuple(name for name in order if name in point and point[name].built) for point in walked
    )
    return Forecast(builds=builds, reused=reused, points=points, axes=_moved(plan, walked, order))


def _order(
    walked: list[dict[str, Identity]], stages: Mapping[str, FunctionStage] | None
) -> list[str]:
    seen = {name for point in walked for name in point}
    return [name for name in (*walk_order(), *(stages or {})) if name in seen]


def _moved(
    plan: SweepPlan, walked: list[dict[str, Identity]], order: list[str]
) -> dict[str, tuple[str, ...]]:
    names = [str(axis["name"]) for axis in plan.document["axes"]]
    found: dict[str, tuple[str, ...]] = {}
    for position, axis in enumerate(names):
        lines: dict[tuple[int, ...], list[dict[str, Identity]]] = {}
        for point, identities in zip(plan.points, walked, strict=True):
            rest = point.coordinates[:position] + point.coordinates[position + 1 :]
            lines.setdefault(rest, []).append(identities)
        moved = {
            name
            for members in lines.values()
            for name in order
            if len({member[name].hash if name in member else None for member in members}) > 1
        }
        found[axis] = tuple(name for name in order if name in moved)
    return found
