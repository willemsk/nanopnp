"""The convergence plot's view-model: what the ladder did, and what may be claimed of it.

Everything the live plot decides lives here, and nothing here imports PySide6 or
NGSolve — the same split :mod:`nanopnp.gui.run_model` is built on, and for the
same reason: ``PySide6.QtWidgets`` does not import on the Linux push gate
(`.knowledge/07-software-stack.md` §5), so a rule implemented in the widget would
be a rule asserted on two of the seven matrix jobs.

**The x-axis is the ladder, not a running iteration count.** NUM-18's
electrostatic rungs are not coupled models, so the solve stage injects no Newton
callback into them and they report no step at all. A continuous axis would show
them as a gap and could offer no reason for it. One band per rung shows them as
what they are: rungs that ran and kept no Newton record. Band widths are
proportional to the steps inside them, so the ladder's cost is legible and a
silent rung still occupies a band wide enough to label.

**A band is empty for two unrelated reasons and the model never guesses which.**
A rung whose model takes no Newton callback reports no step by construction; a
coupled rung reports none when the damped-Newton solve found the transferred
state already below its target and returned before its first step — the NUM-16
warm-start case, and what most of a warm ladder does. The hook says which
(:class:`~nanopnp.core.stages.SolveHook`), and :meth:`Band.note` says it back.

**No convergence threshold is drawn.** NUM-16's criterion is per rung and
disjunctive: the residual relative to its value on entry, *or* the relative
update on the undamped direction, and never on a forced step. One horizontal rule
would have to be drawn at one of the two, on an axis whose zero is per rung, and
a reader would take it for the thing the solver tested. What the band says
instead is what can be proved from the numbers it holds — see :meth:`Band.closed_on`.

**Two series, not one.** The residual is the number a progress caption carries;
the relative update is the one that moves on a warm start, where the entry
residual is already at its floor and six further orders are not available. A plot
of the residual alone shows such a rung converging while its curve is flat.
"""

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
"""Which of the two quantities a caller is asking for."""

RESIDUAL: Series = "residual"
"""Series name: the residual norm after each accepted step."""

UPDATE: Series = "update"
"""Series name: the relative update on the *undamped* Newton direction."""

ConvergenceState: TypeAlias = Literal["idle", "running", "complete", "served", "stopped"]
"""Where the plot is.

``served`` is its own state and not a flavour of ``complete``: a solve answered
from the artefact store never enters the ladder, so it reports no rung and no
step, and an empty plot would read as a solve that converged instantly.
``stopped`` is a run that failed or was cancelled, whose last band therefore
cannot be said to have closed."""

MAX_POINTS_PER_BAND = 256
"""Most samples any one band contributes to a drawn polyline.

A band with more is decimated to this many, keeping the first and the last. At
the NUM-16 reference cap of 50 iterations no band reaches it; the limit exists
because a cap raised for a hard corner of the FR-17 envelope must cost the plot
nothing, and because the decimation is a display decision that belongs on this
side of the Qt boundary where it can be asserted."""


@dataclass(frozen=True)
class Step:
    """One accepted Newton step, as it crossed the process boundary.

    The fields of :class:`~nanopnp.solve.newton.NewtonStep`, as numbers. They are
    the solver's own: the hook forwards them structurally, never recovered from
    the ``:.3e`` of a progress caption (VER-44).
    """

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
    """One rung of the continuation ladder, and the steps reported inside it.

    Parameters
    ----------
    name, stage, index
        The rung as the ladder names it, its NUM-18 stage number and its position.
    reporting
        Whether this rung's solve was given a Newton callback at all.
    tolerance
        The relative tolerance the rung was solved to, carried from the solver
        rather than assumed, so that :meth:`closed_on` measures against the
        number actually used.
    steps
        The accepted steps, in order.
    closed
        Whether this rung is known to have converged: every rung the ladder
        moved past has, and the last one has once the run finished. A band that
        is not closed makes no claim about which NUM-16 test ended it, because
        none did.
    """

    name: str
    stage: int
    index: int
    reporting: bool
    tolerance: float
    steps: list[Step] = field(default_factory=list)
    closed: bool = False

    @property
    def width(self) -> float:
        """The band's extent on the x-axis, in steps.

        ``1`` for an empty band, which is what keeps a silent rung a labelled
        region rather than a zero-width line between its neighbours.
        """
        return float(max(len(self.steps), 1))

    @property
    def minimum_damping(self) -> float:
        """The smallest damping factor any accepted step of this rung was taken with."""
        return min((step.damping for step in self.steps), default=1.0)

    @property
    def forced_steps(self) -> int:
        """How many steps NUM-16 accepted at minimum damping without reduction."""
        return sum(1 for step in self.steps if step.forced)

    def closed_on(self) -> str:
        """Return which NUM-16 test can be *proved* to have ended this rung.

        Not which one the solver happened to evaluate first. NUM-16 accepts
        either test and they are not exclusive, so the honest reading is the one
        the recorded numbers support:

        - a last step that was **forced** cannot have met the update test, which
          NUM-16 excludes on a forced step, so the residual test ended the rung;
        - a last step whose relative update exceeds :attr:`tolerance` fails the
          update test, so again the residual test ended it;
        - otherwise the update test *was* met at that step, and this says so
          without also claiming the residual test was not.

        Returns
        -------
        str
            ``"residual"``, ``"update"``, or ``""`` for a band that has not
            closed or that reported no step.
        """
        if not self.closed or not self.steps:
            return ""
        last = self.steps[-1]
        if last.forced or last.update > self.tolerance:
            return "residual"
        return "update"

    def note(self) -> str:
        """Return the sentence the panel prints under this band.

        Every branch says something a reader could not infer from the drawing.
        An empty band in particular says *why* it is empty, because the two
        reasons are different facts about the solve and the silence is the same.
        """
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
            parts.append(f"the relative update fell to {self.tolerance:.0e} at the last step")
        if self.minimum_damping < 1.0:
            parts.append(f"damping down to {self.minimum_damping:.3g}")
        if self.forced_steps:
            parts.append(f"{self.forced_steps} forced (NUM-16)")
        return ", ".join(parts)


def _decimate(steps: list[Step], limit: int) -> list[Step]:
    """Return at most ``limit`` of ``steps``, keeping the first and the last.

    Evenly spaced by index rather than by value, so the decision is a function of
    how many steps there were and not of what they were — a decimation that chose
    by curvature would make the drawn shape depend on the drawing.
    """
    if len(steps) <= limit:
        return list(steps)
    stride = (len(steps) - 1) / (limit - 1)
    kept = [steps[min(len(steps) - 1, round(index * stride))] for index in range(limit)]
    if kept[-1] is not steps[-1]:
        kept[-1] = steps[-1]
    return kept


@dataclass
class ConvergenceModel:
    """The live plot's state, driven by the rung and step events and nothing else.

    Every transition happens in :meth:`rung`, :meth:`step` and :meth:`settle`, so
    the panel is a pure function of an event stream a test can write by hand.
    """

    state: ConvergenceState = "idle"
    bands: list[Band] = field(default_factory=list)
    omitted_samples: int = 0
    """Samples dropped for being non-positive, which a logarithmic axis cannot
    place. A residual of exactly zero is exact convergence; saying it was omitted
    is the truthful alternative to drawing it somewhere it is not."""

    def reset(self) -> None:
        """Return to the state of a run that has not reported anything."""
        self.state = "idle"
        self.bands = []
        self.omitted_samples = 0

    def rung(
        self, name: str, stage: int, index: int, total: int, reporting: bool, tolerance: float
    ) -> None:
        """Open a band for a rung the solve has announced.

        ``total`` is accepted and not kept: the ladder's length is the number of
        bands opened, and a stored total would be a second source for it that a
        cancelled run would leave disagreeing with the first.
        """
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
        """Record one accepted Newton step inside the band most recently opened.

        Raises
        ------
        ValueError
            If no rung has been announced. The hook's contract is that
            :meth:`rung` precedes the steps it scopes, and a step attributed to
            no rung would be drawn in whichever band happened to be last.
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
            Whether the run *finished*, as opposed to failing or being cancelled.
            A finished run walked the whole pipeline, so a finished run that
            reported no rung had its solve answered from the artefact store —
            which is the one state an empty plot must never be left to imply.
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

    # -- what the widget draws -------------------------------------------------

    @property
    def x_range(self) -> tuple[float, float]:
        """The horizontal extent of the whole ladder, in band widths."""
        return 0.0, sum(band.width for band in self.bands) or 1.0

    def extent(self, band: Band) -> tuple[float, float]:
        """Return one band's ``(start, end)`` on the x-axis."""
        start = sum(earlier.width for earlier in self.bands[: self.bands.index(band)])
        return start, start + band.width

    def points(self, band: Band, series: Series) -> tuple[tuple[float, float], ...]:
        """Return one band's polyline for one series, as ``(x, log₁₀ y)``.

        Non-positive samples are omitted rather than clamped: a logarithm of
        them does not exist, and a point placed at the axis floor would be drawn
        as a number the solve never produced.
        """
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
        """Whole decades enclosing every drawn sample of both series.

        ``(-1, 1)`` when nothing has been drawn yet, so a caller mapping to
        pixels never divides by a zero span.
        """
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
        """Return the decade ticks of :attr:`y_range`, thinned to at most ``limit``.

        Decades and never a "nice" linear division: the axis is a logarithm, and
        a tick at 2.5 decades labels a number nobody reads.
        """
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
        """Count and record the non-positive samples the axis cannot place.

        Called by the panel once the run settles rather than on every event, so
        that the count reported is of the whole run.
        """
        self.omitted_samples = sum(
            1
            for band in self.bands
            for step in band.steps
            for value in (step.residual, step.update)
            if value <= 0.0
        )
        return self.omitted_samples
