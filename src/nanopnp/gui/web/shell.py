"""What the workbench's pages share: the project or case now open, and the user's settings."""

from __future__ import annotations

from dataclasses import dataclass, field

from nanopnp.gui.web import settings as user_settings
from nanopnp.gui.web.queue import Queue
from nanopnp.gui.web.settings import Settings
from nanopnp.gui.web.states import Workbench

__all__ = ["Shell"]


@dataclass
class Shell:
    """What the pages share: the workbench now open and the user's settings."""

    bench: Workbench
    settings: Settings = field(default_factory=user_settings.load)
    last_tool: dict[str, str] = field(default_factory=dict)
    """The tool last opened in each suite, by suite: the one its icon opens."""
    changes_view: str = "list"
    """How the Changes tab shows the changed values: ``list``, a line each, or ``table``."""
    shown_in: dict[str, str] = field(default_factory=dict)
    """The study each physics model is shown in, by model, as its tools' *Shown in* chose."""
    study: str | None = None
    """The study the Study suite's tools show, as their pane's *Study* chose; None for the first."""
    run_shown: int | None = None
    """The queue entry whose convergence the Runs tool shows, by number; None for the last."""
    looks: dict[str, str] = field(default_factory=dict)
    """How Mol* draws the structure on each Meso tool, by ``meso/<tool>``, as its pane chose."""
    result_shown: str | None = None
    """The run directory the results explorer shows; None for the shown study's latest."""
    recorded_shown: str | None = None
    """The recorded run whose convergence the Runs tool unfolds, by directory; None for none."""

    @property
    def keys(self) -> dict[str, str]:
        """The user's key bindings, by command identifier."""
        return self.settings.keys

    @property
    def queue(self) -> Queue:
        """The queue of the workbench now open, which a switch of project keeps."""
        return self.bench.queue
