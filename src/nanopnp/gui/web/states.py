"""The fixture states ``nanopnp gui --state`` boots, and the walk of a case into a state."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from nanopnp.api.case import Case
from nanopnp.api.project import Project
from nanopnp.api.session import Session
from nanopnp.api.sweep import run_plan
from nanopnp.core.errors import EXIT_CASE, EXIT_GATE, classify
from nanopnp.gui.web import settings
from nanopnp.gui.web.queue import Queue
from nanopnp.gui.web.runs import write_sweep
from nanopnp.io.project import STORE_FOLDER
from nanopnp.io.store import StaleEntry, Store, StoreError
from nanopnp.pipeline.case import resolve
from nanopnp.pipeline.run import selected_stages
from nanopnp.sweep.collect import collect
from nanopnp.sweep.document import Axis, load_sweep
from nanopnp.sweep.plan import build_plan, write_plan
from nanopnp.validation.charged_tube import write_charged_tube, write_dielectric_tube

__all__ = [
    "SOLVED",
    "STATES",
    "Workbench",
    "boot",
    "boot_case",
    "boot_project",
    "cap_store",
    "opening_stage",
]

logger = logging.getLogger(__name__)

STATES: tuple[str, ...] = ("empty", "charged-tube", "uncharged", "refused")
"""The names ``--state`` takes: no case, a case walked to its charge, one walked to a stage 7 that
carries no charge from a structure, and a case refused."""

SOLVED = "solved"
"""The state VER-78 (o) alone opens, outside :data:`STATES`: the charged tube solved at its 0.05 V,
a sweep of its bias over -0.05 and 0.05 V, and comparison ``tube-bias`` of the run with the sweep's
point at -0.05 V."""

_BIAS = "boundary_conditions.bias_V"


@dataclass(frozen=True)
class Workbench:
    """What a screen shows: a project, or a case walked to its charge, or the reason it was not."""

    name: str
    case: Path | None = None
    stages: tuple[str, ...] = ()
    refusal: str | None = None
    project: Project | None = None
    queue: Queue = field(default_factory=Queue, compare=False)
    held: frozenset[str] = frozenset()
    """The store digests of the walk the window shows, which no run record names."""


GB = 10**9


def cap_store(project: Project, held: frozenset[str] = frozenset()) -> tuple[StaleEntry, ...]:
    """Bring the project's store under the user's or the project's cap, removing unused results.

    Nothing is removed where no cap is set, or while a walk in any program holds the store; a
    store that cannot be cleaned now is left as it is, and the next walk or opening tries again.
    """
    cap = settings.load().with_project(project.settings).value("store_cap_gb")
    if not isinstance(cap, float | int):
        return ()
    try:
        return project.clean_store(cap_bytes=int(cap * GB), holding=held)
    except (StoreError, OSError) as error:
        logger.warning("the store's cap was not applied: %s", error)
        return ()


def boot_case(case: Path, work: Path, *, name: str | None = None) -> Workbench:
    """Walk a case file to the charge stage in a store under ``work``; a refusal is kept as text."""
    label = name or case.stem
    try:
        result = Session(Store(work / "store"), write=False).run(Case.load(case), upto="charge")
    except Exception as error:
        # A case refused (exit 3) or a gate that aborted the walk (exit 4) is a state to show, as a
        # schema refusal is; any other failure is a fault and ends the server.
        if classify(error) not in {EXIT_CASE, EXIT_GATE}:
            raise
        return Workbench(label, case=case, refusal=str(error))
    return Workbench(label, case=case, stages=tuple(result.artefacts))


def opening_stage(project: Project, study: str) -> str:
    """Return the stage a project's opening walk takes a study to: the charge, else the mesh.

    A study whose charge is neither deposited nor supplied runs no charge stage.
    """
    try:
        case = project.study(study)
        wanted = selected_stages(resolve(case, base=case.source.base), None)
    except (ValueError, KeyError, OSError):
        # A study that does not resolve is refused by the walk itself, naming why.
        return "charge"
    return "charge" if "charge" in wanted else "mesh"


def boot_project(project: Project, queue: Queue | None = None) -> Workbench:
    """Walk a project's first study to the charge stage, else to its mesh; keep a refusal as text.

    The walk writes no run record, and its entry goes into the queue.
    """
    queue = queue if queue is not None else Queue()
    studies = project.items("study")
    if not studies:
        return Workbench(project.name, project=project, queue=queue)
    study = studies[0]
    upto = opening_stage(project, study)
    entry = queue.add(f"{study} to {upto}", "running")
    session = project.session()
    session.write = False
    try:
        result = session.run(project.study(study), upto=upto)
    except Exception as error:
        if classify(error) not in {EXIT_CASE, EXIT_GATE}:
            raise
        queue.set(entry, "failed")
        # The project's own folder is not shown: the problems list names the item relative to it.
        said = str(error).replace(f"{project.root}/", "")
        return Workbench(project.name, project=project, refusal=said, queue=queue)
    queue.set(entry, "done")
    held = frozenset(artefact.hash for artefact in result.artefacts.values())
    if upto == "charge":
        held |= _charge_map(project, study, queue)
    cap_store(project, held)
    return Workbench(
        project.name, project=project, stages=tuple(result.artefacts), queue=queue, held=held
    )


def _continuum_of(project: Project, study: str) -> str | None:
    try:
        body = yaml.safe_load(project.path("study", study).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    named = body.get("models") if isinstance(body, dict) else None
    path = named.get("continuum") if isinstance(named, dict) else None
    name = Path(path).stem if isinstance(path, str) else None
    return name if name in project.items("continuum") else None


def _charge_map(project: Project, study: str, queue: Queue) -> frozenset[str]:
    """Walk a study's continuum model to the charge as Meso builds it; return what it stored.

    The walk is the continuum model's charge case, its run record under the store's ``runs/``,
    so Meso's Charge map opens on its deployed charge; a refusal is left to Meso to say.
    """
    continuum = _continuum_of(project, study)
    if continuum is None:
        return frozenset()
    try:
        # A model that draws its own pore deposits no molecule's charge: nothing to walk.
        case = project.charge_case(continuum)
    except ValueError:
        return frozenset()
    entry = queue.add(f"{continuum} to charge", "running")
    try:
        result = Session(Store(project.root / STORE_FOLDER)).run(case, upto="charge")
    except Exception as error:
        if not isinstance(error, ValueError) and classify(error) not in {EXIT_CASE, EXIT_GATE}:
            raise
        queue.set(entry, "failed")
        return frozenset()
    queue.set(entry, "done")
    return frozenset(artefact.hash for artefact in result.artefacts.values())


def boot(state: str, work: Path) -> Workbench:
    """Return the named state: its fixture case imported into a project in ``work``, and walked."""
    if state == "empty":
        return Workbench("empty")
    if state not in (*STATES, SOLVED):
        raise ValueError(f"no state {state!r}; the states are {', '.join((*STATES, SOLVED))}")
    write = write_dielectric_tube if state == "uncharged" else write_charged_tube
    case = write(work / state)
    project = Project.create(work / state / "project", name=state)
    project.import_case(Case.load(case))
    if state == "refused":
        # A model file the schema refuses: the project holds it, and lists it as a problem.
        model = project.path("continuum", project.items("continuum")[0])
        text = model.read_text(encoding="utf-8")
        if "radius_nm: 30.0" not in text:
            raise ValueError(f"{model} holds no radius_nm: 30.0 for the refused state to replace")
        model.write_text(text.replace("radius_nm: 30.0", "radius_nm: wide"), encoding="utf-8")
    if state == SOLVED:
        _solve(project)
    return boot_project(project)


def _solve(project: Project) -> None:
    """Solve a project's study, sweep its bias over -0.05 and 0.05 V, and compare the two runs."""
    study = project.items("study")[0]
    session = project.session()
    run = session.run(project.study(study))
    points = [{_BIAS: -0.05}, {_BIAS: 0.05}]
    source = write_sweep(project, study, [Axis(name="bias", assignments=points)])
    plan = build_plan(load_sweep(source), source=source, check_meshes=False)
    directory = session.store.sweep_directory(plan.name, plan.hash)
    write_plan(plan, directory)
    members = run_plan(plan, directory, session=session)
    collect(plan, directory, members=members)
    minus = next(
        member
        for member in members
        if member.assignments.get(_BIAS) == -0.05 and member.directory is not None
    )
    assert minus.directory is not None
    project.new_comparison(
        "tube-bias",
        run.directory.relative_to(project.root).as_posix(),
        Path(minus.directory).relative_to(project.root).as_posix(),
    )
