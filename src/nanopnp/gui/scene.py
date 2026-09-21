"""The field viewer's view-model: which field, which file, and whether it drew.

Qt-free and NGSolve-free, like the rest of the view-model layer, so that every
rule the viewer enforces is asserted on the push gate rather than on the two
matrix jobs where ``PySide6.QtWidgets`` imports at all
(`.knowledge/07-software-stack.md` §5).

**The field list is the solution's, never this package's.** The render child
enumerates the model's own declared fields and names them with
:func:`nanopnp.io.fields.attribute_name`, which is the vocabulary the IF-07
export writes and carries the unit in the name. Nothing here invents a name, a
unit or an order, so the picture and the file cannot disagree about what a
number means.

**A loaded document is not a drawn picture.** Qt reaches ``loadFinished(True)``
on a page whose renderer never arrived, leaving ``webgui is not defined`` in a
console nobody sees. So the viewer runs one readiness probe after the load and
this model turns its answer into one of three readings: the scene initialised,
the renderer never arrived, or the scene threw while initialising. Each gets a
diagnostic naming the renderer source it tried, because a blank panel that
reported success is exactly the failure QR-12 is written against.

The second and third are told apart by a flag the document sets *before* it
tries, never by the exception's text: ``new webgui.Scene()`` on a page whose
renderer never loaded raises ``ReferenceError: webgui is not defined``, from the
same line a real scene failure raises from, so matching on the message would make
a renderer's wording into an interface and would call a missing script a broken
scene.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal, TypeAlias

from nanopnp.gui.render import Rendered, RenderFailed, RenderRequest, renderer_source

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Iterable

    from nanopnp.gui.render import RenderEvent

__all__ = ["SceneModel", "SceneState"]

SceneState: TypeAlias = Literal["idle", "rendering", "loading", "drawn", "blank", "failed"]
"""Where the viewer is.

``blank`` and ``failed`` are separate because they fail at different places and
have different remedies: ``failed`` is the render child refusing — no run, no
converged state, a state the stage-10 gate would not restore — and ``blank`` is a
document that loaded without drawing anything."""


@dataclass
class SceneModel:
    """The viewer panel's state: driven by render events and by the readiness probe.

    Parameters
    ----------
    renderer
        Where the host document fetches its renderer from, carried so the
        diagnostics can name it. Read through
        :func:`~nanopnp.gui.render.renderer_source` and not from the constant
        beside it, because that function is the one place the day the renderer
        is shipped as package data has to change. A plain default rather than a
        ``dataclasses.field``: this class already has an attribute called
        ``field``, and in a class body that name shadows the module's.
    """

    state: SceneState = "idle"
    fields: tuple[str, ...] = ()
    field: str = ""
    document: Path | None = None
    scene: Path | None = None
    elements: int = 0
    diagnosis: str = ""
    renderer: str = renderer_source()

    def reset(self) -> None:
        """Return to the state of a viewer that has been shown no run."""
        self.state = "idle"
        self.fields = ()
        self.field = ""
        self.document = None
        self.scene = None
        self.elements = 0
        self.diagnosis = ""

    def request(self, run: str | Path, *, field: str = "") -> RenderRequest:
        """Return the request for one field of one run, and enter ``rendering``.

        Parameters
        ----------
        run
            The run directory.
        field
            An attribute name this solution offers, or ``""`` for the model's
            first field. Not validated here: the field vocabulary belongs to the
            solution, and the render child is what holds it — a check here would
            be this package keeping a second copy of it.
        """
        self.state = "rendering"
        self.diagnosis = ""
        self.document = None
        self.scene = None
        return RenderRequest(run=str(run), field=field, renderer=self.renderer)

    def consume(self, events: Iterable[RenderEvent]) -> None:
        """Apply every render event, in order."""
        for event in events:
            self._apply(event)

    def _apply(self, event: RenderEvent) -> None:
        """Apply one render event."""
        if isinstance(event, Rendered):
            self.fields = tuple(event.fields)
            self.field = event.field
            self.document = Path(event.document)
            self.scene = Path(event.scene)
            self.elements = event.elements
            self.diagnosis = ""
            self.state = "loading"
        elif isinstance(event, RenderFailed):
            self.state = "failed"
            self.diagnosis = event.message
            self.document = None
            self.scene = None
        else:
            raise TypeError(
                f"{type(event).__name__} is a RenderEvent this model does not apply; a variant "
                "added to the union needs a branch here rather than a default"
            )

    def loaded(self, ok: bool) -> None:
        """Record ``loadFinished``, which says nothing about the picture.

        A failed load is terminal and says so. A successful one moves nothing:
        the state stays ``loading`` until :meth:`probed` reports what the
        document actually did, because ``loadFinished(True)`` is reached by a
        page whose renderer never arrived.

        Guarded like :meth:`probed`, and for the same reason: ``loadFinished``
        belongs to whatever document the view last held, which after a refused
        render is not the one this model is reporting. Ungated, a late failure
        would replace the gate's own message — the thing this module exists to
        pass through verbatim — with "the document at None did not load".
        """
        if self.state not in ("loading", "blank", "drawn"):
            return
        if not ok:
            self.state = "blank"
            self.diagnosis = (
                f"the document at {self.document} did not load. Nothing was drawn, and the "
                "scene file beside it is what a reader would have to open instead"
            )

    def probed(self, answer: str | None) -> None:
        """Apply the readiness probe's answer (:func:`~nanopnp.gui.render.readiness_script`).

        Parameters
        ----------
        answer
            The JSON the probe returned, or ``None`` when the evaluation itself
            produced nothing. ``None`` and unparseable are the same fact — the
            document did not answer — and get the same diagnostic.
        """
        if self.state not in ("loading", "blank", "drawn"):
            return
        report = self._report(answer)
        if report is None:
            self.state = "blank"
            self.diagnosis = (
                "the readiness probe returned nothing, so whether the scene drew is unknown; the "
                f"document was loaded from {self.document}"
            )
            return
        if report.get("ready"):
            self.state = "drawn"
            self.diagnosis = ""
            return
        self.state = "blank"
        error = str(report.get("error") or "")
        # ``renderer_loaded`` and not the exception's text. A page whose renderer
        # never arrived throws ``ReferenceError: webgui is not defined`` from the
        # same line a genuine scene failure throws from, so the two are one
        # exception unless the document says which it was — and matching on the
        # message would make a renderer's wording into an interface.
        if not report.get("renderer_loaded"):
            self.diagnosis = (
                f"the document loaded but its renderer was not there. It is fetched from "
                f"{self.renderer}, so a machine with no route to it shows an empty panel; the "
                f"scene itself is beside the document, at {self.scene}"
            )
        elif error:
            self.diagnosis = (
                f"the document loaded and its renderer was reached at {self.renderer}, but the "
                f"scene did not initialise: {error}"
            )
        else:
            self.diagnosis = (
                f"the document loaded and its renderer was reached at {self.renderer}, but the "
                "scene neither initialised nor reported why"
            )

    @staticmethod
    def _report(answer: str | None) -> dict[str, object] | None:
        """Return the probe's answer as a mapping, or ``None`` if it gave none."""
        if not answer:
            return None
        try:
            parsed = json.loads(answer)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    @property
    def summary(self) -> str:
        """Return the line the panel shows above the view."""
        if self.state == "idle":
            return "no run has been shown yet"
        if self.state == "rendering":
            return "restoring the converged state and building the scene"
        if self.state in ("failed", "blank"):
            return self.diagnosis
        drawn = f"{self.field} over {self.elements} element{'s' if self.elements != 1 else ''}"
        return drawn if self.state == "drawn" else f"{drawn}: loading"
