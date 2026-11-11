"""The fixture states ``nanopnp gui --state`` boots, and the walk of a case into a state."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.api.case import Case
from nanopnp.api.project import Project
from nanopnp.api.session import Session
from nanopnp.core.errors import EXIT_CASE, EXIT_GATE, classify
from nanopnp.gui.web import settings
from nanopnp.gui.web.queue import Queue
from nanopnp.io.store import StaleEntry, Store, StoreError
from nanopnp.validation.charged_tube import write_charged_tube, write_dielectric_tube

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.gui.web.link import Link

__all__ = ["STATES", "Workbench", "boot", "boot_case", "boot_project", "cap_store"]

logger = logging.getLogger(__name__)

STATES: tuple[str, ...] = ("empty", "charged-tube", "uncharged", "refused")
"""The names ``--state`` takes: no case, a case walked to its charge, one walked to a stage 7 that
carries no charge from a structure, and a case refused."""

NO_STRUCTURE_CHARGE = (
    "The charge of this case does not come from a structure, so there is no residue to link."
)


@dataclass(frozen=True)
class Workbench:
    """What a screen shows: a project, or a case walked to its charge, or the reason it was not."""

    name: str
    case: Path | None = None
    stages: tuple[str, ...] = ()
    link: Link | None = None
    refusal: str | None = None
    notice: str | None = None
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
    from nanopnp.gui.web.link import Link

    label = name or case.stem
    try:
        result = Session(Store(work / "store"), write=False).run(Case.load(case), upto="charge")
    except Exception as error:
        # A case refused (exit 3) or a gate that aborted the walk (exit 4) is a state to show, as a
        # schema refusal is; any other failure is a fault and ends the server.
        if classify(error) not in {EXIT_CASE, EXIT_GATE}:
            raise
        return Workbench(label, case=case, refusal=str(error))
    link = Link.from_run(result)
    return Workbench(
        label,
        case=case,
        stages=tuple(result.artefacts),
        link=link,
        notice=None if link is not None else NO_STRUCTURE_CHARGE,
    )


def boot_project(project: Project, queue: Queue | None = None) -> Workbench:
    """Walk a project's first study to the charge stage; a refusal is kept as text.

    The walk writes no run record, and its entry goes into the queue.
    """
    queue = queue if queue is not None else Queue()
    studies = project.items("study")
    if not studies:
        return Workbench(project.name, project=project, queue=queue)
    study = studies[0]
    entry = queue.add(f"{study} to charge", "running")
    session = project.session()
    session.write = False
    try:
        result = session.run(project.study(study), upto="charge")
    except Exception as error:
        if classify(error) not in {EXIT_CASE, EXIT_GATE}:
            raise
        queue.set(entry, "failed")
        # The project's own folder is not shown: the problems list names the item relative to it.
        said = str(error).replace(f"{project.root}/", "")
        return Workbench(project.name, project=project, refusal=said, queue=queue)
    queue.set(entry, "done")
    from nanopnp.gui.web.link import Link

    held = frozenset(artefact.hash for artefact in result.artefacts.values())
    cap_store(project, held)
    link = Link.from_run(result)
    return Workbench(
        project.name,
        project=project,
        stages=tuple(result.artefacts),
        link=link,
        notice=None if link is not None else NO_STRUCTURE_CHARGE,
        queue=queue,
        held=held,
    )


def boot(state: str, work: Path) -> Workbench:
    """Return the named state: its fixture case imported into a project in ``work``, and walked."""
    if state == "empty":
        return Workbench("empty")
    if state not in STATES:
        raise ValueError(f"no state {state!r}; the states are {', '.join(STATES)}")
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
    return boot_project(project)
