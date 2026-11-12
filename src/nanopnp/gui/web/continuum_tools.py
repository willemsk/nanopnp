"""The Continuum suite's tool pages: a tool list, a pane of the model's values, the (r, z) view."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, ClassVar
from urllib.parse import urlencode

from nicegui import ui
from nicegui.elements.mixins.text_element import TextElement

from nanopnp.gui.web.continuum import ContinuumModel
from nanopnp.gui.web.frame import Views, heading
from nanopnp.gui.web.plane import COLOURINGS, IMAGES
from nanopnp.gui.web.screens import Tool
from nanopnp.gui.web.shell import Shell
from nanopnp.gui.web.tools import _Pane, current_name
from nanopnp.mesh.sizing import case_sizes

__all__ = ["continuum_page", "current_continuum"]

IMAGE_TITLES = {
    "density": "Density, section y = 0 (stage 2)",
    "mean": "Mean over the chains (stage 3)",
    "cn_variance": "Variance about the Cn average (stage 3)",
    "raw_variance": "Variance of the raw map (stage 3)",
}
COLOUR_TITLES = {"material": "Material", "sicn": "SICN", "gamma": "Gamma"}
TIMES = "\N{MULTIPLICATION SIGN}"
POINT_GROUP = "structure.symmetry.point_group"
PORE_RADIUS = "geometry.pore.radius_nm"
PARTS = {
    "global_nm": "Global",
    "protein_nm": "Protein",
    "electrolyte_nm": "Reservoir",
    "arc_nm": "Outer boundary",
    "axis_in_pore_nm": "Axis in the pore",
}
"""Each row of the size table the Mesh tool shows, by its field of ``SizeTable``."""
SUPPLIED = {
    "geometry.pore": "declares an idealised pore (geometry.pore)",
    "inputs.profile": "supplies its outline (inputs.profile)",
    "inputs.mesh": "supplies its mesh (inputs.mesh)",
}


def current_continuum(shell: Shell) -> ContinuumModel | None:
    """Return the continuum model the tools edit: the open one, else the project's first."""
    project, name = shell.bench.project, current_name(shell, "continuum")
    if project is None or name is None:
        return None
    return ContinuumModel(project, name, shell.queue)


class _ContinuumPane(_Pane[ContinuumModel]):
    kind: ClassVar[str] = "continuum"

    def __init__(self, shell: Shell, tool: Tool, built: Views, focus: str) -> None:
        super().__init__(shell, tool, built, focus, current_continuum(shell))
        self.look: dict[str, str] = {"image": "mean", "colour": "material"}
        self.walked = () if self.model is None else self.model.walked()
        self.supplied = None if self.model is None else self.model.own_outline()
        # A tool whose stage a supplied outline drops builds nothing.
        if self.stage is not None and self.model is not None and self.stage not in self.walked:
            self.stage = None

    # -- the pane's own parts --------------------------------------------------

    def before_fields(self) -> None:
        model = self.model
        if model is None or self.project is None:
            return
        if self.supplied is not None:
            return
        names = list(self.project.items("molecular"))
        chosen = model.molecular()
        with self.named("Built over"):
            picked = ui.select(
                names,
                value=chosen if chosen in names else None,
                on_change=lambda e: self.pair(e.value),
            ).props(
                "dense outlined options-dense data-control=continuum-molecular "
                'aria-label="The molecular model it is built over"'
            )
            picked.set_enabled(bool(names) and self.usable())

    def pair(self, molecular: object) -> None:
        if self.model is None:
            return
        try:
            self.model.pair(str(molecular) if molecular else None)
        except ValueError as error:
            ui.notify(str(error), type="negative")
            return
        self.model.dismiss()
        self.shown_state = ""
        self.refresh()
        ui.timer(0.05, self.show, once=True)

    def own_status(self) -> None:
        if self.model is None:
            return
        said = SUPPLIED.get(self.supplied or "", "reads no structure")
        if self.tool.id in ("geometry", "contour") and "contour" not in self.walked:
            ui.label(f"This model {said}: stages 2 to 4 do not run, so this tool builds nothing.")
        elif self.supplied is not None:
            ui.label(f"This model {said}, so it reads no molecular model.")
        elif (molecular := self.model.molecular()) is not None:
            ui.label(
                f"Built alone over molecular model {molecular}, at 0.15 M NaCl; a study at "
                "another salt builds its own mesh."
            )
        else:
            ui.label("The project holds no molecular model for this model to be built over.")

    def geometry_section(self) -> None:
        case = None if self.model is None else self.model.case()
        if case is not None and case.structure is not None:
            group = case.structure.symmetry.point_group
            with self.named("Point group"):
                ui.link(
                    f"{group}, set in Prepare",
                    f"/molecular/prepare?field={POINT_GROUP}",
                ).props("data-control=geometry-point-group")
        heading("Picture", 2)
        with self.named("Drawn under the outline"):
            ui.select(
                {name: IMAGE_TITLES[name] for name in IMAGES},
                value=self.look["image"],
                on_change=lambda e: self.restyle("image", str(e.value)),
            ).props('dense outlined options-dense data-control=plane-image aria-label="Picture"')

    def contour_section(self) -> None:
        """Contour draws its outline over stage 3's mean; the editor is its own section."""

    def region_section(self) -> None:
        # An idealised pore is declared by its radius, which only such a model holds.
        if self.supplied == "geometry.pore":
            self.field(PORE_RADIUS, self.body(), PORE_RADIUS in self.changed(), False)

    def mesh_section(self) -> None:
        case = None if self.model is None else self.model.case()
        if case is not None:
            mesh = case.numerics.mesh
            typed = {"global_nm": mesh.maxh_nm, **mesh.sizes.model_dump()}
            base = case_sizes(case)
            heading("Sizes used", 2)
            with ui.element("dl").classes("readout-list").props("data-control=mesh-sizes"):
                for name, title in PARTS.items():
                    used = getattr(base, name)
                    whose = "typed" if typed.get(name) is not None else "the table's"
                    TextElement(tag="dt", text=title)
                    TextElement(
                        tag="dd",
                        text=f"{self.text(used, 'nm')}, {whose}, {TIMES} {mesh.size_scale:g} "
                        f"= {self.text(used * mesh.size_scale, 'nm')}",
                    )
        heading("Elements", 2)
        with self.named("Coloured by"):
            ui.select(
                {name: COLOUR_TITLES[name] for name in COLOURINGS},
                value=self.look["colour"],
                on_change=lambda e: self.restyle("colour", str(e.value)),
            ).props(
                'dense outlined options-dense data-control=plane-colour aria-label="Coloured by"'
            )

    def readout(self) -> list[tuple[str, str, Callable[[], None] | None]]:
        model = self.model
        if model is None:
            return []
        held = model.artefacts()
        rows: list[tuple[str, str, Callable[[], None] | None]] = []
        if self.tool.id in ("geometry", "contour") and "contour" in held:
            summary = held["contour"].summary
            constriction = _mapping(summary.get("constriction"))
            rows.append(("Vertices", str(summary.get("vertex_count", "?")), None))
            rows.append(
                (
                    "Narrowest radius",
                    f"{self.text(constriction.get('r_nm'), 'nm')} at z = "
                    f"{self.text(constriction.get('z_nm'), 'nm')}",
                    None,
                )
            )
            rows.append(
                ("Smallest feature", self.text(summary.get("min_feature_size_nm"), "nm"), None)
            )
        elif self.tool.id == "region" and "region" in held:
            areas = _mapping(held["region"].summary.get("face_areas_nm2"))
            for name, area in areas.items():
                rows.append((f"Area, {name}", self.text(area, "nm²"), None))
        elif self.tool.id == "mesh" and "mesh" in held:
            summary = held["mesh"].summary
            quality = _mapping(summary.get("quality"))
            rows.append(("Elements", str(summary.get("elements", "?")), None))
            rows.append(("Least SICN", self.text(quality.get("min_sicn"), "dimensionless"), None))
            rows.append(("Least gamma", self.text(quality.get("min_gamma"), "dimensionless"), None))
        return rows

    # -- the view ----------------------------------------------------------------

    def plane_url(self) -> str | None:
        if self.model is None:
            return None
        query = urlencode({"tool": self.tool.id, **self.look})
        return f"/api/continuum/{self.model.name}/plane?{query}"

    async def show(self) -> None:
        note = "" if self.model is not None else self.subject()
        await self.built.show_plane(self.plane_url(), note)

    async def restyle(self, what: str, value: str) -> None:
        self.look[what] = value
        await self.show()


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def continuum_page(shell: Shell, tool: Tool) -> Callable[..., None]:
    """Return the page of one Continuum tool, which the frame's sub-pages build."""

    def page(built: Views, field: str = "") -> None:
        shell.last_tool["continuum"] = tool.id
        _ContinuumPane(shell, tool, built, field).build()

    return page
