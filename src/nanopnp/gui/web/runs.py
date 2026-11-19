"""A study's runs and sweeps in the queue, and a run unfolded to its convergence."""

from __future__ import annotations

import json
import logging
import math
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, cast

import yaml

from nanopnp.api.project import Project
from nanopnp.gui.convergence import RESIDUAL, UPDATE, Band, ConvergenceModel
from nanopnp.gui.run_model import RunControl
from nanopnp.gui.solver import RunRequest, SolverProcess
from nanopnp.gui.web.chart import Axis as ChartAxis
from nanopnp.gui.web.chart import Band as ChartBand
from nanopnp.gui.web.chart import Chart, Panel, Series
from nanopnp.gui.web.plane import SERIES
from nanopnp.gui.web.queue import Entry, Queue
from nanopnp.io.artefact import SWEEP_SCHEMA
from nanopnp.io.manifest import MANIFEST_FILENAME, RUN_RECORD_FILENAME
from nanopnp.io.project import FOLDERS, RUNS_FOLDER, STORE_FOLDER, SWEEPS_FOLDER, ItemKind
from nanopnp.io.store import Store, atomic_write_bytes
from nanopnp.plot.data import NewtonRung, newton_history
from nanopnp.sweep.collect import collect
from nanopnp.sweep.document import Axis, load_sweep, loads_sweep
from nanopnp.sweep.plan import build_plan, read_plan, write_plan

__all__ = [
    "OTHER_SOLVE_NOTE",
    "RUNG_COLUMNS",
    "SERVED_NOTE",
    "convergence_chart",
    "queue_run",
    "queue_sweep",
    "recorded_convergence",
    "rung_rows",
    "sweep_file",
    "sweep_label",
    "write_sweep",
]

logger = logging.getLogger(__name__)

RUNG_COLUMNS: list[dict[str, str]] = [
    {"name": "number", "label": "#", "field": "number", "align": "right"},
    {"name": "rung", "label": "Rung", "field": "rung", "align": "left"},
    {"name": "steps", "label": "Steps", "field": "steps", "align": "right"},
    {"name": "closed_on", "label": "Closed on", "field": "closed_on", "align": "left"},
    {"name": "last", "label": "Last update", "field": "last", "align": "right"},
    {"name": "damping", "label": "Least damping", "field": "damping", "align": "right"},
    {"name": "forced", "label": "Forced", "field": "forced", "align": "right"},
    {"name": "note", "label": "Note", "field": "note", "align": "left"},
]
"""The columns of a run's rung table."""

_CLOSED = {"residual": "residual test", "update": "update test", "": "—"}

_AXES = ("Newton step", "residual and relative update")


def _request(
    project: Project,
    case: Path,
    *,
    threads: int,
    upto: str | None = None,
    plan: Path | None = None,
    index: int | None = None,
) -> RunRequest:
    return RunRequest(
        case=str(case),
        store=str(project.root / STORE_FOLDER),
        upto=upto,
        runs=str(project.root / RUNS_FOLDER),
        threads=threads,
        plan=None if plan is None else str(plan),
        index=index,
    )


def _queued(
    queue: Queue,
    label: str,
    request: RunRequest,
    *,
    after: tuple[Entry, ...] = (),
    then: Callable[[], None] | None = None,
    study: str = "",
) -> Entry:
    process = SolverProcess(request)
    control = RunControl(process=process)
    entry = queue.add(
        label, start=process.start, cancel=process.cancel, run=control.model, after=after
    )
    entry.study = study
    # Called by the queue as the entry ends, so a member dropped unstarted counts as one ended.
    entry.then = then

    def poll() -> None:
        model = control.poll()
        if not model.settled or entry.ended:
            return
        if model.diagnosis:
            queue.say(f"{label}: {model.diagnosis}")
        queue.set(entry, "done" if model.state == "finished" else "failed")

    entry.poll = poll
    return entry


def queue_run(
    queue: Queue, project: Project, study: str, *, threads: int = 1, upto: str | None = None
) -> Entry:
    """Queue a study's walk, which writes its record into ``runs/<study>/``.

    It starts when the queue has a slot, its solve pinned to ``threads``.
    """
    request = _request(project, project.path("study", study), threads=threads, upto=upto)
    entry = _queued(
        queue, f"{study} run" if upto is None else f"{study} to {upto}", request, study=study
    )
    queue.pump()
    return entry


def sweep_label(study: str, index: int, total: int) -> str:
    """Return the queue's label of a sweep's point, its index counted from 0."""
    return f"{study} sweep, point {index + 1} of {total}"


def sweep_file(project: Project, study: str) -> Path:
    """Return the file a study's sweep is kept in."""
    return project.root / SWEEPS_FOLDER / f"{study}.sweep.yaml"


def write_sweep(project: Project, study: str, axes: Sequence[Axis]) -> Path:
    """Write a study's sweep over ``axes`` and return its file.

    An axis over ``models.<kind>`` takes model names, written as their files beside the study.

    Raises
    ------
    CaseValidationError
        If the axes form no sweep document, such as two of one name; nothing is written.
    """
    written: list[dict[str, Any]] = []
    for axis in axes:
        drawn = axis.model_dump(exclude_none=True, exclude_defaults=True)
        drawn["name"] = axis.name
        if axis.path is not None and axis.path.startswith("models.") and axis.values is not None:
            folder = FOLDERS[cast("ItemKind", axis.path.removeprefix("models."))]
            drawn["values"] = [
                value if str(value).endswith(".yaml") else f"../{folder}/{value}.yaml"
                for value in axis.values
            ]
        written.append(drawn)
    document = {
        "schema": SWEEP_SCHEMA,
        "name": study,
        "base": f"../{FOLDERS['study']}/{study}.yaml",
        "axes": written,
    }
    target = sweep_file(project, study)
    text = yaml.safe_dump(document, sort_keys=False)
    # Read back before it is written: a file its loader refuses would hide every axis.
    loads_sweep(text, source=str(target))
    # A new project has no sweeps folder until its first sweep.
    target.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(target, text.encode("utf-8"))
    return target


def queue_sweep(
    queue: Queue, project: Project, study: str, *, threads: int = 1
) -> tuple[Entry, ...]:
    """Plan a study's sweep, write the plan, and queue one entry per point, wave by wave.

    A point starts once every point of the earlier waves has ended, as its warm start needs;
    the dataset is collected when the last ends.
    """
    source = sweep_file(project, study)
    # The members' meshes are gated by their own walks, in the children, not here.
    plan = build_plan(load_sweep(source), source=source, check_meshes=False)
    directory = project.session().store.sweep_directory(plan.name, plan.hash)
    plan_file = write_plan(plan, directory)
    entries: list[Entry] = []
    earlier: dict[int, list[Entry]] = {}

    def gather() -> None:
        if not all(entry.ended for entry in entries):
            return
        try:
            collect(read_plan(plan_file), directory)
        except (OSError, ValueError, RuntimeError) as error:
            logger.warning("the sweep %s was not collected: %s", plan.name, error)
            queue.say(f"{study} sweep not collected: {error}")
            return
        queue.say(f"collected {study} sweep into {directory.relative_to(project.root)}")

    total = len(plan.points)
    for point in plan.points:
        after = tuple(e for wave, held in earlier.items() if wave < point.wave for e in held)
        request = _request(project, plan_file, threads=threads, plan=plan_file, index=point.index)
        label = sweep_label(study, point.index, total)
        entry = _queued(queue, label, request, after=after, then=gather, study=study)
        entries.append(entry)
        earlier.setdefault(point.wave, []).append(entry)
    queue.pump()
    return tuple(entries)


def _silence(band: Band) -> str:
    if band.steps:
        return ""
    if band.reporting is None:
        return "no step recorded"
    if not band.reporting:
        return "no Newton steps"
    return "converged on entry" if band.closed else ""


SERVED_NOTE = (
    "This run's solve was served from the store; the steps are those of the solve that made it"
)
"""The note a replayed record adds when its run took its solve from the store."""


def recorded_convergence(directory: Path) -> ConvergenceModel | None:
    """Return a recorded run's convergence, replayed from its solve's stored Newton history.

    None where the run reached no solve, the store no longer holds it, or the solve predates the
    history. A rung recorded without its tolerance takes the run's resolved Newton tolerance.
    """
    record = json.loads((directory / RUN_RECORD_FILENAME).read_text(encoding="utf-8"))
    artefacts = record.get("artefacts")
    solve = artefacts.get("solve") if isinstance(artefacts, dict) else None
    root = record.get("store")
    if not isinstance(solve, dict) or not root:
        return None
    artefact = Store(Path(str(root))).get(str(solve["schema"]), str(solve["hash"]), mark=False)
    rungs = None if artefact is None else newton_history(artefact)
    if artefact is None or rungs is None:
        return None
    # The solve's key holds the tolerance it ran with, whatever the release's default now is.
    newton = artefact.parameters.get("newton")
    keyed = newton.get("relative_tolerance") if isinstance(newton, dict) else None

    model = ConvergenceModel()
    for index, rung in enumerate(rungs):
        tolerance = rung.tolerance if rung.tolerance is not None else keyed
        model.rung(
            rung.name,
            rung.stage,
            index,
            len(rungs),
            rung.reporting,
            float(tolerance) if isinstance(tolerance, int | float) else math.nan,
        )
        model.bands[-1].forced_known = rung.forced is not None
        trials = rung.trials if rung.trials is not None else [1] * len(rung.iteration)
        forced = rung.forced if rung.forced is not None else [False] * len(rung.iteration)
        for step in range(len(rung.iteration)):
            model.step(
                int(rung.iteration[step]),
                float(rung.residual[step]),
                float(rung.update[step]),
                float(rung.damping[step]),
                int(trials[step]),
                bool(forced[step]),
            )
    model.settle(finished=True)
    model.count_omitted()
    stages = record.get("stages")
    if not _made_by(rungs, directory):
        model.note = OTHER_SOLVE_NOTE
    elif isinstance(stages, list) and any(
        isinstance(entry, dict) and entry.get("stage") == "solve" and entry.get("cached")
        for entry in stages
    ):
        model.note = SERVED_NOTE
    return model


OTHER_SOLVE_NOTE = (
    "The store's history under this solve's key is not the one this run recorded: its rungs or "
    "their steps differ from the run's manifest, so these steps are another solve's"
)
"""The note a replayed record adds when the stored history differs from the run's manifest."""


def _made_by(rungs: Sequence[NewtonRung], directory: Path) -> bool:
    # A rebuild, or a warm-started solve of an evicted key, rewrites the history under the key the
    # record names; the run's own manifest keeps each rung's name and Newton iterations.
    try:
        manifest = json.loads((directory / MANIFEST_FILENAME).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return True
    solver = manifest.get("solver") if isinstance(manifest, dict) else None
    run = solver.get("run") if isinstance(solver, dict) else None
    recorded = run.get("rungs") if isinstance(run, dict) else None
    if not isinstance(recorded, list):
        return True
    if len(recorded) != len(rungs):
        return False
    for entry, rung in zip(recorded, rungs, strict=True):
        newton = entry.get("newton") if isinstance(entry, dict) else None
        steps = newton.get("iterations", 0) if isinstance(newton, dict) else 0
        if entry.get("rung") != rung.name or steps != len(rung.iteration):
            return False
    return True


def convergence_chart(model: ConvergenceModel) -> Chart:
    """Return a run's convergence chart: a band per rung, the residual and the update on decades.

    A silent rung's band says which silence it is, and each curve breaks at every band's start,
    so none is drawn across a rung. No threshold is drawn, the tolerance being the rung's own. A
    solve served from the store draws nothing and says so.
    """
    x_label, y_label = _AXES
    named = "The convergence of the run"
    if not model.bands:
        empty = Panel(ChartAxis(x_label, range=(0.0, 1.0)), ChartAxis(y_label, "log", (0.1, 10.0)))
        return Chart((empty,), notes=(model.summary,), label=f"{named}: nothing drawn")
    x_low, x_high = model.x_range
    y_low, y_high = model.y_range
    bands = tuple(
        ChartBand(
            f"rung-{index}",
            model.extent(band),
            label=band.name,
            # A band too narrow for its name shows the rung's number, as the table does.
            short=str(index + 1),
            note=_silence(band),
            shaded=index % 2 == 0,
        )
        for index, band in enumerate(model.bands)
    )
    series: list[Series] = []
    for kind, title, colour, dash in (
        (RESIDUAL, "Residual", SERIES[0], ()),
        (UPDATE, "Relative update", SERIES[1], (5.0, 3.0)),
    ):
        x: list[float] = []
        y: list[float | None] = []
        for band in model.bands:
            x.append(model.extent(band)[0])
            y.append(None)
            for at, value in model.samples(band, kind):
                x.append(at)
                y.append(value)
        series.append(Series(kind, title, tuple(x), tuple(y), colour, dash, marks=True))
    step = max(1, math.ceil((x_high - x_low) / 8))
    panel = Panel(
        ChartAxis(
            x_label,
            range=(x_low, x_high),
            ticks=tuple(float(tick) for tick in range(0, math.floor(x_high) + 1, step)),
        ),
        ChartAxis(
            y_label,
            "log",
            range=(10.0**y_low, 10.0**y_high),
            ticks=tuple(10.0**decade for decade in model.ticks()),
        ),
    )
    return Chart(
        (panel,),
        tuple(series),
        bands,
        label=f"{named}: {', '.join(band.name for band in model.bands)}",
    )


def rung_rows(model: ConvergenceModel) -> list[dict[str, str]]:
    """Return a run's rung table: each rung's steps, the test that closed it, and its damping."""
    rows: list[dict[str, str]] = []
    for index, band in enumerate(model.bands):
        stepped = bool(band.steps)
        last = band.steps[-1].update if stepped else None
        rows.append(
            {
                "key": str(index),
                "number": str(index + 1),
                "rung": band.name,
                "steps": str(len(band.steps)) if band.reporting or band.steps else "—",
                "closed_on": _CLOSED[band.closed_on()],
                "last": "—"
                if last is None
                else f"{last:.2e} {'≤' if last <= band.tolerance else '>'} {band.tolerance:.0e}",
                "damping": f"{band.minimum_damping:.3g}" if stepped else "—",
                "forced": str(band.forced_steps),
                "note": band.note(),
            }
        )
    return rows
