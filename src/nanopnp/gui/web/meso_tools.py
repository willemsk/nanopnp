"""The Meso suite's tool pages: a continuum model's pore drawn from its molecular model."""

from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar
from urllib.parse import urlencode

from nicegui import ui

from nanopnp.gui.web.continuum_tools import _ContinuumPane
from nanopnp.gui.web.frame import Views
from nanopnp.gui.web.screens import Tool
from nanopnp.gui.web.shell import Shell
from nanopnp.io.models import Kind

__all__ = ["meso_page"]


class _MesoPane(_ContinuumPane):
    kind: ClassVar[str] = "meso"
    model_kind: ClassVar[Kind] = "continuum"

    def __init__(self, shell: Shell, tool: Tool, built: Views, focus: str) -> None:
        super().__init__(shell, tool, built, focus)
        if tool.id == "density":
            self.look["image"] = "density"
        if tool.id == "charge":
            # Stage 7 is no continuum model's own stage: it is built over the molecular model.
            self.stage = None

    def subject(self) -> str:
        model = self.model
        if self.project is None or model is None:
            return super().subject()
        molecular = model.molecular()
        over = f", over molecular model {molecular}" if molecular is not None else ""
        return f"Continuum model {model.name}{over}"

    def density_section(self) -> None:
        self.picture_choice()

    def outline_section(self) -> None:
        self.picture_choice()
        self.outline_editor()

    def charge_section(self) -> None:
        ui.label("The charge map is not drawn here yet.").classes("later")

    def plane_url(self) -> str | None:
        if self.model is None:
            return None
        query = urlencode({"tool": "geometry", **{k: v for k, v in self.look.items() if v}})
        return f"/api/continuum/{self.model.name}/plane?{query}"

    def scene_url(self) -> tuple[str | None, str]:
        model = self.model
        molecular = None if model is None else model.molecular()
        if molecular is None:
            return None, ""
        colour = "charge" if self.tool.id == "charge" else "chain"
        query = urlencode({"colour": colour, "side": 1, "clip": 1})
        return f"/api/molecular/{molecular}/scene?{query}", f"{molecular}:meso:{colour}"

    async def show(self) -> None:
        scene, key = self.scene_url()
        await self.built.show_pair(scene, self.plane_url(), key)


def meso_page(shell: Shell, tool: Tool) -> Callable[..., None]:
    """Return the page of one Meso tool, which the frame's sub-pages build."""

    def page(built: Views, field: str = "") -> None:
        shell.last_tool["meso"] = tool.id
        _MesoPane(shell, tool, built, field).build()

    return page
