"""The field viewer's view-model: which field, which file, and whether it drew."""

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


@dataclass
class SceneModel:
    state: SceneState = "idle"
    fields: tuple[str, ...] = ()
    field: str = ""
    document: Path | None = None
    scene: Path | None = None
    elements: int = 0
    diagnosis: str = ""
    renderer: str = renderer_source()

    def reset(self) -> None:
        self.state = "idle"
        self.fields = ()
        self.field = ""
        self.document = None
        self.scene = None
        self.elements = 0
        self.diagnosis = ""

    def request(self, run: str | Path, *, field: str = "") -> RenderRequest:
        self.state = "rendering"
        self.diagnosis = ""
        self.document = None
        self.scene = None
        return RenderRequest(run=str(run), field=field, renderer=self.renderer)

    def consume(self, events: Iterable[RenderEvent]) -> None:
        for event in events:
            self._apply(event)

    def _apply(self, event: RenderEvent) -> None:
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
        if self.state not in ("loading", "blank", "drawn"):
            return
        if not ok:
            self.state = "blank"
            self.diagnosis = (
                f"the document at {self.document} did not load. Nothing was drawn, and the "
                "scene file beside it is what a reader would have to open instead"
            )

    def probed(self, answer: str | None) -> None:
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
        # renderer_loaded and not the exception text: a missing renderer throws ReferenceError from
        # the same line as a real scene failure, and matching the message would make the renderer's
        # wording an interface.
        if not report.get("renderer_loaded"):
            self.diagnosis = (
                f"the document loaded but its renderer was not there. It is shipped with the "
                f"package and loaded from {self.renderer}, so this installation is missing it; "
                f"the scene itself is beside the document, at {self.scene}"
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
        if not answer:
            return None
        try:
            parsed = json.loads(answer)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    @property
    def summary(self) -> str:
        if self.state == "idle":
            return "no run has been shown yet"
        if self.state == "rendering":
            return "restoring the converged state and building the scene"
        if self.state in ("failed", "blank"):
            return self.diagnosis
        drawn = f"{self.field} over {self.elements} element{'s' if self.elements != 1 else ''}"
        return drawn if self.state == "drawn" else f"{drawn}: loading"
