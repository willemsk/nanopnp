"""The convergence plot's view-model: what the ladder did, and what may be claimed of it."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal, TypeAlias

__all__ = [
    "RESIDUAL",
    "UPDATE",
    "Band",
    "ConvergenceModel",
    "ConvergenceState",
    "Series",
    "Step",
]

Series: TypeAlias = Literal["residual", "update"]

RESIDUAL: Series = "residual"

UPDATE: Series = "update"

# ``served`` is a state of its own: a solve answered from the store reports no rung, and an empty
# plot would read as one that converged instantly.
ConvergenceState: TypeAlias = Literal["idle", "running", "complete", "served", "stopped"]

# NUM-16's cap is 50 iterations, so no band reaches it; a raised cap must cost the plot nothing.
MAX_POINTS_PER_BAND = 256


@dataclass(frozen=True)
class Step:
    """One accepted Newton step, as it crossed the process boundary."""

    iteration: int
    residual: float
    update: float
    damping: float
    trials: int
    forced: bool

    def value(self, series: Series) -> float:
        """Return the sample this step contributes to one series."""
        return self.residual if series == RESIDUAL else self.update


@dataclass
class Band:
    """One rung of the continuation ladder, and the steps reported inside it."""

    name: str
    stage: int
    index: int
    reporting: bool
    tolerance: float
    steps: list[Step] = field(default_factory=list)
    closed: bool = False

    @property
    def width(self) -> float:
        """The band's extent on the x-axis, in steps; ``1`` for an empty band."""
        return float(max(len(self.steps), 1))

    @property
    def minimum_damping(self) -> float:
        """The smallest damping factor any accepted step of this rung was taken with."""
        return min((step.damping for step in self.steps), default=1.0)

    @property
    def forced_steps(self) -> int:
        """Number of steps accepted at minimum damping without reduction."""
        return sum(1 for step in self.steps if step.forced)

    def closed_on(self) -> str:
        """Return which convergence test can be proved to have ended this rung.

        Returns
        -------
        str
            ``"residual"``, ``"update"``, or ``""``: a band that did not close or reported no step.
        """
        if not self.closed or not self.steps:
            return ""
        last = self.steps[-1]
        if last.forced or last.update > self.tolerance:
            return "residual"
        return "update"

    def note(self) -> str:
        """Return the sentence the panel prints under this band."""
        if not self.reporting:
            return "no Newton steps: this rung's model takes no Newton callback"
        if not self.steps:
            if not self.closed:
                return "no Newton step reported yet"
            return "converged on entry: the residual was already below target before the first step"
        parts = [f"{len(self.steps)} step{'s' if len(self.steps) != 1 else ''}"]
        closed = self.closed_on()
        if closed == "residual":
            parts.append("closed on the residual test")
        elif closed == "update":
            # The measured update, not the threshold it passed: the tolerance is a number the solve
            # never produced.
            parts.append(
                f"the relative update fell to {self.steps[-1].update:.2e} at the last step, "
                f"below the {self.tolerance:.0e} tolerance"
            )
        if self.minimum_damping < 1.0:
            parts.append(f"damping down to {self.minimum_damping:.3g}")
        if self.forced_steps:
            parts.append(f"{self.forced_steps} forced (NUM-16)")
        return ", ".join(parts)


def _decimate(steps: list[Step], limit: int) -> list[Step]:
    if len(steps) <= limit:
        return list(steps)
    stride = (len(steps) - 1) / (limit - 1)
    kept = [steps[min(len(steps) - 1, round(index * stride))] for index in range(limit)]
    if kept[-1] is not steps[-1]:
        kept[-1] = steps[-1]
    return kept


@dataclass
class ConvergenceModel:
    """The live plot's state, driven by the rung and step events and nothing else."""

    state: ConvergenceState = "idle"
    bands: list[Band] = field(default_factory=list)
    omitted_samples: int = 0

    def reset(self) -> None:
        """Return to the state of a run that has not reported anything."""
        self.state = "idle"
        self.bands = []
        self.omitted_samples = 0

    def rung(
        self, name: str, stage: int, index: int, total: int, reporting: bool, tolerance: float
    ) -> None:
        """Open a band for a rung the solve has announced; ``total`` is accepted and ignored."""
        del total
        if self.bands:
            # The ladder moved past the previous rung, so that rung converged.
            self.bands[-1].closed = True
        self.state = "running"
        self.bands.append(
            Band(
                name=str(name),
                stage=int(stage),
                index=int(index),
                reporting=bool(reporting),
                tolerance=float(tolerance),
            )
        )

    def step(
        self,
        iteration: int,
        residual: float,
        update: float,
        damping: float,
        trials: int,
        forced: bool,
    ) -> None:
        """Record one accepted Newton step in the band most recently opened.

        Raises
        ------
        ValueError
            If no rung has been announced.
        """
        if not self.bands:
            raise ValueError(
                f"Newton step {iteration} arrived before any rung was announced; the solve hook "
                "reports a rung before the steps it scopes, and a step with no rung cannot be "
                "banded"
            )
        self.bands[-1].steps.append(
            Step(
                iteration=int(iteration),
                residual=float(residual),
                update=float(update),
                damping=float(damping),
                trials=int(trials),
                forced=bool(forced),
            )
        )

    def settle(self, *, finished: bool) -> None:
        """Close the plot when the run reaches a terminal state.

        Parameters
        ----------
        finished
            Whether the run finished, rather than failed or was cancelled.
        """
        if not finished:
            self.state = "stopped"
            return
        for band in self.bands:
            band.closed = True
        self.state = "served" if not self.bands else "complete"

    @property
    def summary(self) -> str:
        """Return the line the panel shows above the plot."""
        if self.state == "idle":
            return "no solve has been watched yet"
        if self.state == "served":
            return (
                "this solve was served from the artefact store: it climbed no ladder and took no "
                "Newton step, so there is no convergence history to draw"
            )
        rungs = f"{len(self.bands)} rung{'s' if len(self.bands) != 1 else ''}"
        steps = sum(len(band.steps) for band in self.bands)
        tail = {
            "running": "solving",
            "complete": "complete",
            "stopped": "stopped before the ladder finished",
        }[self.state]
        text = f"{rungs}, {steps} Newton step{'s' if steps != 1 else ''}: {tail}"
        if self.omitted_samples:
            text += f" ({self.omitted_samples} sample(s) omitted: not positive)"
        return text

    @property
    def x_range(self) -> tuple[float, float]:
        """The horizontal extent of the whole ladder, in band widths."""
        return 0.0, sum(band.width for band in self.bands) or 1.0

    def extent(self, band: Band) -> tuple[float, float]:
        """Return one band's ``(start, end)`` on the x-axis, found by identity.

        Raises
        ------
        ValueError
            If ``band`` is not one of this model's.
        """
        start = 0.0
        for earlier in self.bands:
            if earlier is band:
                return start, start + band.width
            start += earlier.width
        raise ValueError(f"band {band.name!r} is not one this model opened")

    def points(self, band: Band, series: Series) -> tuple[tuple[float, float], ...]:
        """Return one band's ``(x, log₁₀ y)`` polyline for one series, skipping non-positives."""
        start, _ = self.extent(band)
        drawn: list[tuple[float, float]] = []
        for step in _decimate(band.steps, MAX_POINTS_PER_BAND):
            value = step.value(series)
            if value <= 0.0:
                continue
            drawn.append((start + step.iteration - 0.5, math.log10(value)))
        return tuple(drawn)

    @property
    def y_range(self) -> tuple[float, float]:
        """Whole decades enclosing every drawn sample; ``(-1, 1)`` when nothing is drawn."""
        values = [
            math.log10(value)
            for band in self.bands
            for step in band.steps
            for value in (step.residual, step.update)
            if value > 0.0
        ]
        if not values:
            return -1.0, 1.0
        low, high = math.floor(min(values)), math.ceil(max(values))
        return (low, high) if high > low else (low - 1.0, high + 1.0)

    def ticks(self, *, limit: int = 8) -> tuple[float, ...]:
        """Return the decade ticks of :attr:`y_range`, thinned to at most ``limit``."""
        low, high = self.y_range
        decades = [float(value) for value in range(int(low), int(high) + 1)]
        if len(decades) <= limit:
            return tuple(decades)
        stride = math.ceil(len(decades) / limit)
        thinned = decades[::stride]
        if thinned[-1] != decades[-1]:
            thinned.append(decades[-1])
        return tuple(thinned)

    def count_omitted(self) -> int:
        """Count and record the non-positive samples the axis cannot place."""
        self.omitted_samples = sum(
            1
            for band in self.bands
            for step in band.steps
            for value in (step.residual, step.update)
            if value <= 0.0
        )
        return self.omitted_samples
