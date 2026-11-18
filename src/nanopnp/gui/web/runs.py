"""A study's runs and sweeps in the queue, and a run unfolded to its convergence."""

from __future__ import annotations

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
from nanopnp.gui.web.plane import SERIES, Plane
from nanopnp.gui.web.queue import Entry, Queue
from nanopnp.io.artefact import SWEEP_SCHEMA
from nanopnp.io.project import FOLDERS, RUNS_FOLDER, STORE_FOLDER, SWEEPS_FOLDER, ItemKind
from nanopnp.io.store import atomic_write_bytes
from nanopnp.sweep.collect import collect
from nanopnp.sweep.document import Axis, load_sweep, loads_sweep
from nanopnp.sweep.plan import build_plan, read_plan, write_plan

__all__ = [
    "RUNG_COLUMNS",
    "convergence_plane",
    "queue_run",
    "queue_sweep",
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
    if not band.reporting:
        return "no Newton steps"
    return "converged on entry" if band.closed else ""


def convergence_plane(model: ConvergenceModel) -> Plane:
    """Return a run's convergence plot: a band per rung, the residual and the update on decades.

    A silent rung's band says which silence it is; no threshold is drawn, the tolerance being
    the rung's own. A solve served from the store draws nothing and says so.
    """
    if not model.bands:
        return Plane("plot", _AXES, (0.0, 1.0, -1.0, 1.0), (), (model.summary,))
    x_low, x_high = model.x_range
    y_low, y_high = model.y_range
    layers: list[dict[str, Any]] = []
    for index, band in enumerate(model.bands):
        layers.append(
            {
                "id": f"rung-{index}",
                "kind": "band",
                "x": list(model.extent(band)),
                "label": band.name,
                # A band too narrow for its name shows the rung's number, as the table does.
                "short": str(index + 1),
                "note": _silence(band),
                "shaded": index % 2 == 0,
                "panel": 0,
            }
        )
    for series, title, colour, dash in (
        (RESIDUAL, "Residual", SERIES[0], []),
        (UPDATE, "Relative update", SERIES[1], [5, 3]),
    ):
        for index, band in enumerate(model.bands):
            points = model.points(band, series)
            if not points:
                continue
            layers.append(
                {
                    "id": f"{series}-{index}",
                    "kind": "line",
                    "title": title,
                    "points_nm": [value for point in points for value in point],
                    "colour": colour,
                    "dash": dash,
                    "marks": True,
                    "panel": 0,
                }
            )
    step = max(1, math.ceil((x_high - x_low) / 8))
    panel = {
        "axes": list(_AXES),
        "extent_nm": [x_low, x_high, y_low, y_high],
        "scale": "linear",
        "ticks": [float(tick) for tick in range(0, math.floor(x_high) + 1, step)],
        "y_scale": "log",
        "y_ticks": list(model.ticks()),
    }
    # The count of samples omitted is in the summary the entry shows above the plot.
    return Plane("plot", _AXES, (x_low, x_high, y_low, y_high), tuple(layers), panels=(panel,))


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
                "steps": str(len(band.steps)) if band.reporting else "—",
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
