"""The Continuum suite's tool pages: a tool list, a pane of the model's values, the (r, z) view."""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any, ClassVar, Concatenate, ParamSpec, TypeVar
from urllib.parse import urlencode

from nicegui import events, ui

from nanopnp.gui.geometry import lookup_table
from nanopnp.gui.web.continuum import ContinuumModel
from nanopnp.gui.web.frame import Views, heading
from nanopnp.gui.web.plane import (
    COLOURINGS,
    DOMAINS,
    MATERIAL_COLOURS,
    PARTS,
    mesh_quality,
)
from nanopnp.gui.web.screens import Tool
from nanopnp.gui.web.shell import Shell
from nanopnp.gui.web.tools import _Pane, current_name
from nanopnp.io.models import Kind
from nanopnp.mesh.quality import QUALITY_FLOOR
from nanopnp.mesh.sizing import SIZES, case_sizes

__all__ = ["continuum_page", "current_continuum"]

COLOUR_TITLES = {"material": "Material", "sicn": "SICN", "gamma": "Gamma"}
TIMES = "\N{MULTIPLICATION SIGN}"
BINS = 10
"""The histogram's bars, each a tenth of the quality's range."""
PORE_RADIUS = "geometry.pore.radius_nm"
OUTLINE_STAGES = ("geometry.density.", "geometry.contour.")
"""The values of stages 2 to 4, which a supplied outline leaves unread."""
GLOBAL = "numerics.mesh.maxh_nm"
WALL = "numerics.mesh.wall_h_nm"
PART_ROWS: tuple[tuple[str, str, str, str | None], ...] = (
    ("protein", "Domains", "numerics.mesh.sizes.protein_nm", "protein_nm"),
    ("electrolyte", "Domains", "numerics.mesh.sizes.electrolyte_nm", "electrolyte_nm"),
    ("membrane", "Domains", GLOBAL, "global_nm"),
    ("wall", "Boundaries", WALL, None),
    ("arc", "Boundaries", "numerics.mesh.sizes.arc_nm", "arc_nm"),
    ("axis", "Boundaries", "numerics.mesh.sizes.axis_in_pore_nm", "axis_in_pore_nm"),
    ("global", "", GLOBAL, "global_nm"),
)
"""The Mesh tool's parts: the part, its group, the case path that sizes it, and its row of the
default sizes, which ``SizeTable`` names; the wall's size is ``auto`` or typed."""
IDEALISED_PARTS = frozenset({"membrane", "wall", "global"})
"""The parts an idealised pore's mesh sizes: its global size and its wall's. A typed
``numerics.mesh.sizes`` entry is refused beside ``geometry.pore``, so none of those rows is one."""
IDEALISED_FIXED = frozenset({"geometry.membrane.centre_z_nm", "numerics.mesh.backend"})
"""The values an idealised pore refuses away from their defaults: it sits at 0, meshed by netgen."""
DOMAIN_FIELDS: dict[str, tuple[str, ...]] = {
    "protein": ("charge.exclusion_offset_nm",),
    "exclusion": ("charge.exclusion_offset_nm",),
    "membrane": ("geometry.membrane.thickness_nm", "geometry.membrane.centre_z_nm"),
    "electrolyte": ("geometry.reservoir.radius_nm", PORE_RADIUS),
}
"""The Region tool's values each domain picked shows."""
TOOL_STAGES = {
    "density": "symmetry",
    "outline": "contour",
    "region": "region",
    "mesh": "mesh",
}
"""The stage each tool of a continuum model builds to."""
SUPPLIED = {
    "geometry.pore": "declares an idealised pore (geometry.pore)",
    "inputs.profile": "supplies its outline (inputs.profile)",
    "inputs.mesh": "supplies its mesh (inputs.mesh)",
}

_S = TypeVar("_S", bound="_Pane[Any]")
_P = ParamSpec("_P")


def _keyed(method: Callable[Concatenate[_S, _P], None]) -> Callable[Concatenate[_S, _P], None]:
    # A section redrawn by an event reads the model's case and keys its walk once, as the
    # pane's build and refresh do: each read alone re-keys the walk.
    @functools.wraps(method)
    def keyed(self: _S, /, *args: _P.args, **kwargs: _P.kwargs) -> None:
        with self.keyed_once():
            method(self, *args, **kwargs)

    return keyed


def current_continuum(
    shell: Shell, model_type: type[ContinuumModel] = ContinuumModel
) -> ContinuumModel | None:
    """Return the continuum model the tools edit: the open one, else the project's first."""
    project, name = shell.bench.project, current_name(shell, "continuum")
    if project is None or name is None:
        return None
    return model_type(project, name, shell.queue)


class _ContinuumPane(_Pane[ContinuumModel]):
    """A pane of a continuum model's tools: its pick of a molecular model, its region and mesh."""

    kind: ClassVar[str] = "continuum"
    model_kind: ClassVar[Kind] = "continuum"
    model_type: ClassVar[type[ContinuumModel]] = ContinuumModel
    """What the pane reads the continuum model as."""

    def __init__(self, shell: Shell, tool: Tool, built: Views, focus: str) -> None:
        super().__init__(shell, tool, built, focus, current_continuum(shell, self.model_type))
        self.look: dict[str, str] = {"image": "mean", "colour": "material", "band": "", "pick": ""}
        # A part or a domain named by the address opens picked.
        for part, _, path, _ in PART_ROWS:
            if path == focus and tool.id == "mesh" and not self.look["pick"]:
                self.look["pick"] = "global" if part == "membrane" else part
        self.parts_box: ui.column
        self.part_box: ui.column
        self.domain_select: ui.select
        self.histogram_box: ui.column
        self.picked_label: ui.label
        self.walked: tuple[str, ...] = ()
        self.supplied: str | None = None

    def build_pane(self) -> None:
        # Read in the pane's one keyed read: what the model walks, and what it supplies itself.
        model = self.model
        self.walked = () if model is None else model.walked()
        self.supplied = None if model is None else model.own_outline()
        # A tool whose stage a supplied outline drops builds nothing.
        if self.stage is not None and model is not None and self.stage not in self.walked:
            self.stage = None
        super().build_pane()

    # -- the pane's own parts --------------------------------------------------

    def before_fields(self) -> None:
        if self.tool.id == "region":
            self.domain_choice()
        if self.tool.id == "mesh":
            self.quality_verdict()
        self.built_over()

    def built_over(self) -> None:
        """Draw the pick of the molecular model the model is built over, where it reads one."""
        model = self.model
        if model is None or self.project is None or not self.usable():
            return
        # A model drawing its own pore reads no molecular model.
        if self.supplied is not None and model.molecular() is None:
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

    async def pair(self, molecular: object) -> None:
        if self.model is None:
            return
        try:
            self.model.pair(str(molecular) if molecular else None)
        except ValueError as error:
            ui.notify(str(error), type="negative")
            return
        self.model.dismiss()
        # The stages it walks follow the pairing, and with them the pane's values and actions.
        await self.built.reopen()

    def own_status(self) -> None:
        if self.model is None:
            return
        said = SUPPLIED.get(self.supplied or "", "reads no structure")
        if self.supplied is not None:
            ui.label(f"This model {said}, so it reads no molecular model.")
        elif (molecular := self.model.molecular()) is not None:
            ui.label(f"Built over molecular model {molecular}, outside any study.")
        else:
            ui.label("The project holds no molecular model for this model to be built over.")

    def signature(self) -> object:
        return self.model is not None and self.model.editor() is not None

    async def building_shown(self) -> None:
        await self.show()

    def build_held(self) -> str | None:
        if self.model is not None and self.model.editor() is not None:
            return (
                "Save the edited outline or discard it first, in Meso \u203a Outline: a build "
                "reads the model's file."
            )
        return None

    def unbuilt(self, tool_id: str) -> str | None:
        stage = TOOL_STAGES.get(tool_id)
        if self.model is None or stage is None or stage in self.walked or not self.usable():
            return None
        return "outline supplied" if self.supplied == "inputs.profile" else "supplied"

    def field(self, path: str, body: dict[str, Any], changed: bool, exposed: bool) -> None:
        super().field(path, body, changed, exposed)
        # A supplied outline: stages 2 to 4 do not run, so their values are shown, not set; and an
        # idealised pore refuses a centre or a mesher of its own.
        unread = path.startswith(OUTLINE_STAGES) and "contour" not in self.walked
        fixed = path in IDEALISED_FIXED and self.supplied == "geometry.pore"
        if self.model is not None and (unread or fixed):
            control = self.controls[path]
            if isinstance(control, ui.select | ui.number | ui.input):
                control.disable()

    def listen(self) -> None:
        self.built.listen("plane_pick", self.on_plane_pick)
        self.built.listen("plane_value", self.on_plane_value)

    def on_plane_pick(self, event: events.GenericEventArguments) -> None:
        layer, index = str(event.args.get("layer", "")), int(event.args.get("index", 0))
        if layer == "mesh" and self.tool.id == "mesh":
            self.show_element(index)
        elif layer.startswith("domain-") and self.tool.id == "region":
            self.domain_select.set_value(layer.removeprefix("domain-"))

    async def on_plane_value(self, event: events.GenericEventArguments) -> None:
        path, value = str(event.args.get("path", "")), event.args.get("value")
        if path not in self.controls or not isinstance(value, int | float):
            return
        control = self.controls[path]
        # A value the pane shows but does not set is not set from its label on the drawing.
        if not getattr(control, "enabled", True):
            return
        self.write(path, float(value))
        if isinstance(control, ui.number):
            self.writing = False
            try:
                control.value = float(value)
            finally:
                self.writing = True
        await self.show()

    def region_section(self) -> None:
        # An idealised pore is declared by its radius, which only such a model holds.
        if self.supplied == "geometry.pore":
            self.field(PORE_RADIUS, self.body(), PORE_RADIUS in self.changed(), False)
            self.mark(PORE_RADIUS, PORE_RADIUS in self.changed())
        ui.label(
            "Later: drawing and editing the domains by hand, with CAD tools, comes with the "
            "sketcher in a later phase."
        ).classes("later later-banner")

    # -- Region's domains ---------------------------------------------------------------

    def domains(self) -> list[str]:
        """Return the domains the model's region holds, the smallest first."""
        case = None if self.model is None else self.model.case()
        named = list(DOMAINS)
        if self.supplied == "geometry.pore":
            named.remove("protein")
        if case is None or case.charge is None or not case.charge.exclusion_offset_nm:
            named.remove("exclusion")
        return named

    def domain_choice(self) -> None:
        options = {"": "All domains", **{name: DOMAINS[name] for name in self.domains()}}
        with self.named("Domain"):
            self.domain_select = ui.select(
                options,
                value=self.look["pick"] if self.look["pick"] in options else "",
                on_change=lambda e: self.pick_domain(str(e.value or "")),
            ).props(
                "dense outlined options-dense data-control=region-domain "
                'aria-label="The domain whose values the pane shows; pick one in the view too"'
            )
            self.domain_select.set_enabled(self.model is not None and self.usable())

    async def pick_domain(self, domain: str) -> None:
        self.look["pick"] = domain
        changed = self.changed()
        for path in self.rows:
            self.mark(path, path in changed)
        await self.show()

    def mark(self, path: str, changed: bool) -> None:
        super().mark(path, changed)
        domain = self.look.get("pick", "")
        if self.tool.id == "region" and domain:
            shown = path in DOMAIN_FIELDS.get(domain, ())
            self.rows[path].set_visibility(shown and (changed or not self.modified_only))

    @_keyed
    def show_element(self, index: int) -> None:
        import numpy as np

        model = self.model
        if model is None:
            return
        sicn, gamma = mesh_quality(model, "sicn"), mesh_quality(model, "gamma")
        if sicn is None or gamma is None or index >= len(sicn):
            return
        self.picked_label.text = (
            f"Element {index}: SICN {np.round(sicn[index], 3)}, gamma {np.round(gamma[index], 3)}"
        )

    @_keyed
    def show_histogram(self) -> None:
        import numpy as np

        self.histogram_box.clear()
        colour = self.look["colour"]
        quality = (
            None if self.model is None or colour == "material" else mesh_quality(self.model, colour)
        )
        with self.histogram_box:
            if quality is None:
                ui.label(
                    "Colour the elements by SICN or gamma to see their spread; a bar fills its "
                    "elements in the view."
                ).classes("later")
                return
            counts, edges = np.histogram(quality, bins=BINS, range=(0.0, 1.0))
            most = max(int(counts.max()), 1)
            table = lookup_table("viridis")
            title = COLOUR_TITLES[colour]
            with ui.element("div").classes("histogram-plot"):
                with (
                    ui.row()
                    .classes("histogram no-wrap items-end")
                    .props(f'role=group aria-label="{title} of the elements"')
                ):
                    for low, high, count in zip(edges[:-1], edges[1:], counts, strict=True):
                        band = f"{low:.1f},{high:.1f}"
                        pressed = str(self.look.get("band") == band).lower()
                        r, g, b, _ = table[round(0.5 * (low + high) * (len(table) - 1))]
                        # The whole column answers a click, so an empty bar is still a target.
                        with (
                            ui.button(on_click=lambda _, b=band: self.outline(b))
                            .props(
                                f"flat dense aria-pressed={pressed} data-control=histogram-bar "
                                f'aria-label="{title} {low:.1f} to {high:.1f}: '
                                f'{int(count)} elements"'
                            )
                            .classes("histogram-bar")
                        ):
                            shown = f"{count / 1000:.1f}k" if count >= 1000 else f"{int(count)}"
                            ui.label(shown).classes("histogram-count")
                            ui.element("div").classes("histogram-fill").style(
                                f"height:{2 + 56 * int(count) / most:.0f}px;"
                                f"background:#{r:02x}{g:02x}{b:02x}"
                            )
                # The gate's floor between its bars, and the quality's axis under them.
                ui.element("div").classes("histogram-floor").style(
                    f"left:{100 * QUALITY_FLOOR:g}%"
                ).props(f'title="The quality gate\'s floor, {QUALITY_FLOOR:g}"')
                with ui.element("div").classes("histogram-axis").props("aria-hidden=true"):
                    for tick in (0.0, QUALITY_FLOOR, 0.5, 1.0):
                        ui.label(f"{tick:g}").style(f"left:{100 * tick:g}%")
            below = int(np.count_nonzero(quality <= QUALITY_FLOOR))
            ui.label(
                f"{title} of {len(quality)} elements; {below} at or under the floor of "
                f"{QUALITY_FLOOR:g}. A bar fills its elements in the view."
            ).classes("later")

    async def outline(self, band: str) -> None:
        self.look["band"] = "" if self.look.get("band") == band else band
        # The view first: the bar that asked is rebuilt with the histogram.
        await self.show()
        self.show_histogram()

    def quality_verdict(self) -> None:
        held = {} if self.model is None or not self.usable() else self.model.artefacts()
        if "mesh" not in held:
            ui.label(
                f"Quality gate: SICN and gamma each above {QUALITY_FLOOR:g}; not built yet."
            ).props("data-control=mesh-gate")
            return
        # A stored mesh passed its gate: stage 6 refuses one below the floor it records.
        quality = _mapping(held["mesh"].summary.get("quality"))
        sicn, gamma = quality.get("min_sicn"), quality.get("min_gamma")
        floor = quality.get("floor", QUALITY_FLOOR)
        ui.label(
            f"✓ Quality gate passed: least SICN {self.text(sicn, 'dimensionless')}, least "
            f"gamma {self.text(gamma, 'dimensionless')}; each must exceed {floor}."
        ).classes("state-ok").props("data-control=mesh-gate")

    # -- the mesh's parts ---------------------------------------------------------------

    def part_sizes(self) -> dict[str, tuple[float | None, str]]:
        """Return each part's base size in nm and where it comes from: typed, table or auto."""
        case = None if self.model is None or not self.usable() else self.model.case()
        if case is None:
            return {}
        mesh = case.numerics.mesh
        base = case_sizes(case)
        typed: dict[str, float | None] = {GLOBAL: mesh.maxh_nm}
        typed |= {f"numerics.mesh.sizes.{k}": v for k, v in mesh.sizes.model_dump().items()}
        found: dict[str, tuple[float | None, str]] = {}
        for part, _, path, row in PART_ROWS:
            if row is None:
                wall = mesh.wall_h_nm
                found[part] = (None, "auto") if wall == "auto" else (float(wall), "typed")
            elif part == "membrane":
                found[part] = (base.global_nm, "global")
            else:
                source = "typed" if typed.get(path) is not None else "default"
                found[part] = (getattr(base, row), source)
        return found

    def built_table(self) -> dict[str, float]:
        """Return the scaled sizes the built mesh used, by ``SizeTable`` row, or {} unbuilt.

        The store holds the mesh only while its key matches the model's values now.
        """
        held = {} if self.model is None or not self.usable() else self.model.artefacts()
        if "mesh" not in held:
            return {}
        table = _mapping(_mapping(held["mesh"].parameters.get("sizing")).get("table"))
        return {k: float(v) for k, v in table.items() if isinstance(v, int | float)}

    def next_table(self) -> dict[str, float]:
        """Return the scaled sizes the next build uses, from the library's table."""
        case = None if self.model is None or not self.usable() else self.model.case()
        if case is None:
            return {}
        return {
            k: float(v)
            for k, v in case_sizes(case).scaled(self.scale()).summary().items()
            if isinstance(v, int | float)
        }

    def built_wall_nm(self) -> float | None:
        """Return the wall size the built mesh used, scaled, or None unbuilt."""
        held = {} if self.model is None or not self.usable() else self.model.artefacts()
        if "mesh" not in held:
            return None
        sizing = _mapping(held["mesh"].parameters.get("sizing"))
        value = _mapping(sizing.get("wall")).get("wall_h_nm")
        return float(value) if isinstance(value, int | float) else None

    def used(self) -> set[str]:
        """Return the parts this model's mesh is sized by: none for a supplied mesh."""
        if self.supplied == "inputs.mesh":
            return set()
        if self.supplied == "geometry.pore":
            return set(IDEALISED_PARTS)
        return {row[0] for row in PART_ROWS}

    def scale(self) -> float:
        case = None if self.model is None or not self.usable() else self.model.case()
        return case.numerics.mesh.size_scale if case is not None else 1.0

    @_keyed
    def show_parts(self) -> None:
        self.parts_box.clear()
        sizes, used, changed, scale = self.part_sizes(), self.used(), self.changed(), self.scale()
        wall_used = self.built_wall_nm()
        built = self.built_table()
        table = built or self.next_table()
        with self.parts_box:
            with ui.row().classes("parts-head no-wrap w-full"):
                ui.label("Mesh parts")
                if self.model is not None and self.usable():
                    said = "size used" if built else "size the build uses"
                    ui.label(f"{said}, {TIMES} {scale:g}")
            group = None
            for part, grouped, path, row in PART_ROWS:
                if grouped and grouped != group:
                    group = grouped
                    ui.label(grouped).classes("parts-group")
                base, source = sizes.get(part, (None, ""))
                if self.model is None:
                    size, source = "—", ""
                elif part not in used:
                    size, source = "—", "not used"
                elif base is None:
                    size = self.text(wall_used, "nm") if wall_used is not None else "auto"
                else:
                    size = self.text(table.get(row or "", base * scale), "nm")
                typed = path in changed and part != "membrane"
                picked = self.look.get("pick") == part
                button = (
                    ui.button(on_click=lambda _, p=part: self.pick_part(p), color=None)
                    .props(
                        f"flat dense no-caps align=left data-control=mesh-part-{part} "
                        f"aria-pressed={str(picked).lower()} "
                        f'aria-label="{PARTS[part]}: {size}{", " + source if source else ""}"'
                    )
                    .classes("parts-row" + (" parts-child" if grouped else ""))
                )
                button.set_visibility(typed or not self.modified_only)
                button.set_enabled(self.model is not None and self.usable())
                with button:
                    swatch = ui.element("span").classes(
                        "parts-swatch" if part in MATERIAL_COLOURS else "parts-line"
                    )
                    if part in MATERIAL_COLOURS:
                        swatch.style(f"background:{MATERIAL_COLOURS[part]}")
                    ui.label(PARTS[part]).classes("parts-name")
                    ui.label("◆" if typed else "").classes("changed parts-mark")
                    ui.label(size).classes("parts-size")
                    ui.label(source).classes("parts-source")

    @_keyed
    def show_part(self) -> None:
        """Open the picked part's one field, with the table's value and the size it gives."""
        for path in [p for p in self.rows if p in self.tool.parts]:
            self.rows.pop(path, None)
            self.marks.pop(path, None)
            self.controls.pop(path, None)
        self.part_box.clear()
        part = self.look.get("pick", "")
        with self.part_box:
            if not part:
                ui.label(
                    "Pick a part, in the list or the view, to size it: a blank size uses the "
                    "default, and the size scale multiplies every size."
                ).classes("later")
                return
            path = next(row[2] for row in PART_ROWS if row[0] == part)
            heading(PARTS[part], 3)
            if self.model is not None and part not in self.used():
                why = (
                    "This model supplies its mesh (inputs.mesh), so no size is read."
                    if self.supplied == "inputs.mesh"
                    else "An idealised pore's mesh reads only the global and wall sizes."
                )
                ui.label(why).classes("later")
                return
            body = self.body()
            if path == WALL and _value_of_wall(body) == "auto":
                body = {}
            super().field(path, body, path in self.changed(), path in self.exposed())
            self.mark(path, path in self.changed())
            control = self.controls[path]
            row = next(entry[3] for entry in PART_ROWS if entry[0] == part)
            scale = self.scale()
            if row is None:
                ui.label(
                    "Blank is auto: a fifth of the Debye length at the salt the mesh is sized "
                    f"for, at most 0.05 nm, {TIMES} the size scale {scale:g}."
                ).classes("later")
                return
            table = getattr(SIZES, row)
            control.props(f'placeholder="{table:g}"')
            said = f"Blank uses the default, {table:g} nm"
            if part == "membrane":
                said = f"The membrane takes the global size. {said}"
            scaled = (self.built_table() or self.next_table()).get(row)
            gives = "" if scaled is None else f"; {TIMES} {scale:g} gives {self.text(scaled, 'nm')}"
            ui.label(f"{said}{gives}.").classes("later")

    async def pick_part(self, part: str) -> None:
        self.look["pick"] = "" if self.look.get("pick") == part else part
        # The view first: the row that asked is rebuilt with the list.
        await self.show()
        self.show_parts()
        self.show_part()

    def on_modified(self, event: events.ValueChangeEventArguments[Any]) -> None:
        super().on_modified(event)
        if self.tool.id == "mesh":
            self.show_parts()

    def after_write(self, path: str) -> None:
        super().after_write(path)
        if self.tool.id == "mesh" and path in self.tool.parts:
            self.show_parts()

    def mesh_section(self) -> None:
        case = None if self.model is None else self.model.case()
        self.parts_box = (
            ui.column()
            .classes("parts w-full gap-0")
            .props('data-control=tool-parts role=group aria-label="Mesh parts"')
        )
        self.show_parts()
        self.part_box = ui.column().classes("part-card w-full gap-1")
        self.show_part()
        if case is not None and case.electrolyte is not None:
            salt = self.text(case.electrolyte.concentration_M, "molar")
            ui.label(
                f"Built alone at {salt}, its wall sized for that salt; a study at another salt "
                "builds its own mesh."
            ).classes("later").props("data-control=mesh-salt")
        ui.label(
            "Later: refinement regions drawn by hand, and boundary layers, come in a later phase."
        ).classes("later later-banner")
        heading("Elements", 2)
        with self.named("Coloured by"):
            ui.select(
                {name: COLOUR_TITLES[name] for name in COLOURINGS},
                value=self.look["colour"],
                on_change=lambda e: self.restyle("colour", str(e.value)),
            ).props(
                'dense outlined options-dense data-control=plane-colour aria-label="Coloured by"'
            ).set_enabled(self.model is not None)
        self.histogram_box = ui.column().classes("w-full gap-1")
        self.show_histogram()
        self.picked_label = ui.label("").classes("later").props("role=status")

    def readout(self) -> list[tuple[str, str, Callable[[], None] | None]]:
        model = self.model
        if model is None:
            return []
        held = model.artefacts()
        rows: list[tuple[str, str, Callable[[], None] | None]] = []
        if self.tool.id == "region" and "region" in held:
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
        query = urlencode({"tool": self.tool.id, **{k: v for k, v in self.look.items() if v}})
        return f"/api/continuum/{self.model.name}/plane?{query}"

    async def show(self) -> None:
        if self.tool.view == "page":
            await self.show_page()
            return
        note = "" if self.model is not None else self.subject()
        await self.built.show_plane(self.plane_url(), note)

    async def restyle(self, what: str, value: str) -> None:
        self.look[what] = value
        if what == "colour":
            self.look["band"] = ""
            self.show_histogram()
        await self.show()


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _value_of_wall(body: dict[str, Any]) -> object:
    return _mapping(_mapping(body.get("numerics")).get("mesh")).get("wall_h_nm")


def continuum_page(shell: Shell, tool: Tool) -> Callable[..., None]:
    """Return the page of one Continuum tool, which the frame's sub-pages build."""

    def page(built: Views, field: str = "") -> None:
        shell.last_tool["continuum"] = tool.id
        _ContinuumPane(shell, tool, built, field).build()

    return page
