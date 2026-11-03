"""The fixture states ``nanopnp gui --state`` boots, and the walk of a case into a state."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.api.case import Case
from nanopnp.api.session import Session
from nanopnp.core.errors import EXIT_CASE, EXIT_GATE, classify
from nanopnp.io.store import Store
from nanopnp.validation.charged_tube import write_charged_tube

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.gui.web.link import Link

__all__ = ["STATES", "Workbench", "boot", "boot_case"]

STATES: tuple[str, ...] = ("empty", "charged-tube", "refused")
"""The names ``--state`` takes: no case, a case walked to its charge, and a case refused."""


@dataclass(frozen=True)
class Workbench:
    """What a screen shows: a case walked to its charge, or the reason it was not."""

    name: str
    case: Path | None = None
    stages: tuple[str, ...] = ()
    link: Link | None = None
    refusal: str | None = None


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
    return Workbench(label, case=case, stages=tuple(result.artefacts), link=Link(result))


def boot(state: str, work: Path) -> Workbench:
    """Return the named state, writing and walking its case in ``work``."""
    if state == "empty":
        return Workbench("empty")
    if state not in STATES:
        raise ValueError(f"no state {state!r}; the states are {', '.join(STATES)}")
    case = write_charged_tube(work / state)
    if state == "refused":
        case.write_text(
            case.read_text(encoding="utf-8").replace(
                "concentration_M: 1.0", "concentration_M: -1.0"
            ),
            encoding="utf-8",
        )
    return boot_case(case, work / state, name=state)
