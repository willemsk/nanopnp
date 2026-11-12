"""The Continuum suite's tool pages: a tool list, a pane of the model's values, the (r, z) view."""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar
from urllib.parse import urlencode

from nicegui import events, ui

from nanopnp.gui.assess import (
    Assessed,
    AssessFailed,
    Assessment,
    AssessProcess,
    AssessRequest,
    Seeded,
)
from nanopnp.gui.geometry import ProfileEditor, lookup_table
from nanopnp.gui.web.continuum import ContinuumModel
from nanopnp.gui.web.frame import Views, heading
from nanopnp.gui.web.plane import (
    COLOURINGS,
    DOMAINS,
    IMAGES,
    MATERIAL_COLOURS,
    PARTS,
    mesh_quality,
)
from nanopnp.gui.web.screens import Tool
from nanopnp.gui.web.shell import Shell
from nanopnp.gui.web.tools import _Pane, current_name
from nanopnp.io.project import STORE_FOLDER
from nanopnp.mesh.sizing import SIZES, case_sizes

__all__ = ["continuum_page", "current_continuum"]

IMAGE_TITLES = {
    "density": "Density section, stage 2",
    "mean": "Mean, stage 3",
    "cn_variance": "Cn variance, stage 3",
    "raw_variance": "Raw variance, stage 3",
}
COLOUR_TITLES = {"material": "Material", "sicn": "SICN", "gamma": "Gamma"}
TIMES = "\N{MULTIPLICATION SIGN}"
BINS = 10
"""The histogram's bars, each a tenth of the quality's range."""
QUALITY_FLOOR = 0.3
"""The quality gate's floor on SICN and gamma (section 5.2.2), marked on the histogram."""
POINT_GROUP = "structure.symmetry.point_group"
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
"""The Mesh tool's parts (WB-41): the part, its group, the case path that sizes it, and its row
of section 5.2.2's table, which ``SizeTable`` names; the wall's size is ``auto`` or typed."""
IDEALISED_PARTS = frozenset({"electrolyte", "membrane", "wall", "global"})
"""The parts an idealised pore's mesh sizes: its global size and its wall's."""
DOMAIN_FIELDS: dict[str, tuple[str, ...]] = {
    "protein": ("charge.exclusion_offset_nm",),
    "exclusion": ("charge.exclusion_offset_nm",),
    "membrane": ("geometry.membrane.thickness_nm", "geometry.membrane.centre_z_nm"),
    "electrolyte": ("geometry.reservoir.radius_nm", PORE_RADIUS),
}
"""The Region tool's values each domain picked shows."""
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
        self.look: dict[str, str] = {"image": "mean", "colour": "material", "band": "", "pick": ""}
        # A part or a domain named by the address opens picked.
        for part, _, path, _ in PART_ROWS:
            if path == focus and tool.id == "mesh" and not self.look["pick"]:
                self.look["pick"] = "global" if part == "membrane" else part
        self.parts_box: ui.column
        self.part_box: ui.column
        self.domain_select: ui.select
        self.vertex: int | None = None
        self.assess: AssessProcess | None = None
        self.assessed: Assessment | str | None = None
        self.folder = Path()
        self.edit_box: ui.column
        self.histogram_box: ui.column
        self.picked_label: ui.label
        self.vertex_r: ui.number
        self.vertex_z: ui.number
        self.walked = () if self.model is None else self.model.walked()
        self.supplied = None if self.model is None else self.model.own_outline()
        # A tool whose stage a supplied outline drops builds nothing.
        if self.stage is not None and self.model is not None and self.stage not in self.walked:
            self.stage = None

    # -- the pane's own parts --------------------------------------------------

    def before_fields(self) -> None:
        if self.tool.id == "region":
            self.domain_choice()
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

    async def pair(self, molecular: object) -> None:
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
        await self.show()

    def own_status(self) -> None:
        if self.model is None:
            return
        said = SUPPLIED.get(self.supplied or "", "reads no structure")
        if self.tool.id == "geometry" and "contour" not in self.walked:
            ui.label(
                f"This model {said}: stages 2 to 4 do not run, so their values are not read. "
                "Its outline is drawn and edited here."
            )
        elif self.supplied is not None:
            ui.label(f"This model {said}, so it reads no molecular model.")
        elif (molecular := self.model.molecular()) is not None:
            ui.label(f"Built alone over molecular model {molecular}.")
        else:
            ui.label("The project holds no molecular model for this model to be built over.")

    def unbuilt(self, tool_id: str) -> str | None:
        stage = {"geometry": "contour", "region": "region", "mesh": "mesh"}.get(tool_id)
        if self.model is None or stage is None or stage in self.walked or not self.usable():
            return None
        return "outline supplied" if self.supplied == "inputs.profile" else "supplied"

    def field(self, path: str, body: dict[str, Any], changed: bool, exposed: bool) -> None:
        super().field(path, body, changed, exposed)
        # A supplied outline: stages 2 to 4 do not run, so their values are shown, not set.
        if (
            self.model is not None
            and path.startswith(OUTLINE_STAGES)
            and "contour" not in self.walked
        ):
            control = self.controls[path]
            if isinstance(control, ui.select | ui.number | ui.input):
                control.disable()

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
            ).props(
                'dense outlined options-dense data-control=plane-image aria-label="Picture"'
            ).set_enabled(self.model is not None and "contour" in self.walked)
        heading("Outline", 2)
        self.edit_box = ui.column().classes("w-full gap-1").props("data-control=contour-edit")
        self.show_edit()
        ui.label(
            "Later: the pore's (r, z) domain drawn by hand, with lines, arcs and booleans, "
            "comes with the sketcher in a later phase."
        ).classes("later later-banner")

    # -- the outline's editor ----------------------------------------------------------

    def measurable(self) -> bool:
        """Say whether an edit can be measured: the model walks stages 2 to 4 over a structure."""
        return "contour" in self.walked

    def show_edit(self) -> None:
        self.edit_box.clear()
        model = self.model
        with self.edit_box:
            if model is None:
                ui.label("No continuum model is open, so there is no outline to edit.").classes(
                    "later"
                )
                return
            editor = model.editor()
            if editor is None:
                with ui.row().classes("items-center no-wrap"):
                    # An outline is there to edit once stage 4 is built, or where it is supplied.
                    outlined = model.profile() is not None or (
                        model.states().get("contour") == "built"
                    )
                    ui.button("Edit outline", on_click=self.start_edit).props(
                        "outline dense no-caps data-control=contour-start"
                    ).set_enabled(self.usable() and outlined and not self.assessing())
                    if self.measurable():
                        ui.button("Seed from the map", on_click=self.seed).props(
                            "outline dense no-caps data-control=contour-seed"
                        ).set_enabled(self.usable() and not self.assessing())
                ui.label(
                    "Edit the built outline, or the one the model supplies; a loop stage 4 "
                    "refused is seeded from the stored map."
                ).classes("later")
                self.show_assessment()
                return
            ui.label(
                f"{len(editor.vertices)} vertices, edited from {editor.parent_name}; not saved."
            ).props("data-control=contour-state")
            with ui.row().classes("items-center no-wrap"):
                ui.button(icon="sym_o_undo", on_click=self.undo).props(
                    'flat dense aria-label="Undo the last edit" data-control=contour-undo'
                ).set_enabled(editor.can_undo)
                ui.button(icon="sym_o_redo", on_click=self.redo).props(
                    'flat dense aria-label="Redo the edit undone" data-control=contour-redo'
                ).set_enabled(editor.can_redo)
                ui.button("Delete vertex", on_click=self.delete_vertex).props(
                    "outline dense no-caps data-control=contour-delete"
                ).set_enabled(self.vertex is not None)
                ui.button("Measure", on_click=self.measure_edit).props(
                    "outline dense no-caps data-control=contour-measure"
                ).set_enabled(self.measurable() and not self.assessing())
            if self.vertex is not None and self.vertex < len(editor.vertices):
                r, z = editor.vertices[self.vertex]
                with self.named(f"Vertex {self.vertex}"):
                    with ui.row().classes("items-center no-wrap"):
                        self.vertex_r = (
                            ui.number(value=round(r, 4), suffix="nm", step=0.01)
                            .props('dense outlined data-control=contour-r aria-label="r, in nm"')
                            .style("width: 7.5rem")
                        )
                        self.vertex_z = (
                            ui.number(value=round(z, 4), suffix="nm", step=0.01)
                            .props('dense outlined data-control=contour-z aria-label="z, in nm"')
                            .style("width: 7.5rem")
                        )
                        ui.button("Move", on_click=self.move_vertex).props(
                            "outline dense no-caps data-control=contour-move"
                        )
            else:
                ui.label(
                    "Pick a vertex in the view to move or delete it; double-click an edge to "
                    "insert one."
                ).classes("later")
            problem = editor.problem
            if problem is not None:
                self.card("warn", "The loop would not load", problem, None)
            if not self.measurable():
                ui.label(
                    "This model reads no structure to measure an edit against; a study that "
                    "pairs it with a molecular model runs the checks."
                ).classes("later")
            self.show_assessment()
            with ui.row().classes("items-center no-wrap"):
                ui.button("Discard edit…", on_click=self.ask_discard).props(
                    "flat dense no-caps data-control=contour-discard"
                )
                ui.button("Save edit…", on_click=self.ask_save).props(
                    "unelevated dense no-caps color=primary data-control=contour-save"
                ).set_enabled(problem is None)

    def show_assessment(self) -> None:
        said = self.assessed
        if said is None:
            if self.assessing():
                ui.label("Measuring the loop…").props("role=status")
            return
        if isinstance(said, str):
            self.card("err", "Not measured", said, None)
            return
        if said.passed:
            ui.label("✓ The loop meets every check of stage 4.").classes("state-ok")
            return
        for refusal in said.failures:
            self.card("err", f"Fails the {refusal.criterion} check", refusal.message, None)

    def assessing(self) -> bool:
        return self.assess is not None and self.assess.running

    def start_assess(self, vertices: tuple[tuple[float, float], ...] | None) -> None:
        model = self.model
        case = None if model is None else model.case()
        if model is None or case is None or self.assessing():
            return
        self.folder = Path(tempfile.mkdtemp(prefix="nanopnp-assess-"))
        written = self.folder / f"{model.name}.case.yaml"
        written.write_text(case.dumps(), encoding="utf-8")
        self.assess = AssessProcess(
            AssessRequest(
                case=str(written), store=str(model.project.root / STORE_FOLDER), vertices=vertices
            )
        )
        self.assessed = None
        self.assess.start()
        self.show_edit()

    async def poll_assess(self) -> None:
        if self.assess is None or self.model is None:
            return
        ended = not self.assess.running
        for event in self.assess.drain():
            if isinstance(event, Assessed):
                self.assessed = event.assessment
            elif isinstance(event, Seeded):
                seed = event.seed
                self.model.hold_edit(
                    ProfileEditor.from_seed(seed.vertices, digest=seed.digest, name=seed.name)
                )
                self.assessed = seed.assessment
            elif isinstance(event, AssessFailed):
                self.assessed = event.message
            ended = True
        if ended:
            self.assess = None
            shutil.rmtree(self.folder, ignore_errors=True)
            self.show_edit()
            await self.show()

    async def start_edit(self) -> None:
        if self.model is None:
            return
        try:
            self.model.start_edit()
        except ValueError as error:
            ui.notify(str(error), type="negative", multi_line=True)
            return
        await self.edited()

    def seed(self) -> None:
        self.start_assess(None)

    def measure_edit(self) -> None:
        editor = None if self.model is None else self.model.editor()
        if editor is not None:
            self.start_assess(tuple(editor.vertices))

    async def edited(self) -> None:
        self.assessed = None
        # The view first: the control that asked runs its script in its own slot, which the
        # box's rebuild deletes.
        await self.show()
        self.show_edit()

    async def undo(self) -> None:
        editor = None if self.model is None else self.model.editor()
        if editor is not None and editor.undo():
            await self.edited()

    async def redo(self) -> None:
        editor = None if self.model is None else self.model.editor()
        if editor is not None and editor.redo():
            await self.edited()

    async def move_vertex(self) -> None:
        editor = None if self.model is None else self.model.editor()
        r, z = self.vertex_r.value, self.vertex_z.value
        if editor is None or self.vertex is None or r is None or z is None:
            return
        editor.move(self.vertex, float(r), float(z))
        await self.edited()

    async def delete_vertex(self, index: int | None = None) -> None:
        editor = None if self.model is None else self.model.editor()
        chosen = self.vertex if index is None else index
        if editor is None or chosen is None:
            return
        try:
            editor.delete(chosen)
        except (ValueError, IndexError) as error:
            ui.notify(str(error), type="warning", multi_line=True)
            return
        self.vertex = None
        await self.edited()

    def ask_discard(self) -> None:
        with ui.dialog() as dialog, ui.card().classes("dialog").props("data-control=confirm"):
            heading("Discard the edit?", 2)
            ui.label("The edited outline is not saved; the model keeps its own.")
            with ui.row().classes("justify-end w-full"):
                ui.button("Cancel", on_click=dialog.close).props("flat no-caps autofocus")
                ui.button("Discard edit", on_click=lambda: self.discard(dialog)).props(
                    "no-caps color=negative data-control=confirm-accept"
                )
        dialog.open()

    async def discard(self, dialog: ui.dialog) -> None:
        dialog.close()
        if self.model is not None:
            self.model.drop_edit()
        self.vertex = None
        await self.edited()

    def ask_save(self) -> None:
        if self.model is None:
            return
        with ui.dialog() as dialog, ui.card().classes("dialog").props("data-control=contour-ask"):
            heading("Save the edit as a continuum model", 2)
            ui.label(
                "The new model supplies the edited outline as inputs.profile. A study runs it with "
                "its molecular model's structure and charge."
            ).classes("later")
            name = ui.input("Name", value=f"{self.model.name}-edit").props(
                "autofocus outlined dense data-control=contour-name"
            )
            with ui.row().classes("justify-end w-full"):
                ui.button("Cancel", on_click=dialog.close).props("flat no-caps")
                ui.button("Save", on_click=lambda: self.save_edit(dialog, name)).props(
                    "unelevated no-caps color=primary data-control=contour-save-accept"
                )
        dialog.open()

    def save_edit(self, dialog: ui.dialog, name: ui.input) -> None:
        model = self.model
        chosen = str(name.value or "").strip()
        if model is None or not chosen:
            name.error = "Give the new model a name."
            return
        try:
            model.save_edit(chosen)
        except ValueError as error:
            name.error = str(error).replace(f"{model.project.root}/", "")
            return
        dialog.close()
        model.project.open_item(f"continuum/{chosen}")
        ui.run_javascript("window.location.assign('/continuum/geometry')")

    # -- the view's events ---------------------------------------------------------

    def listen(self) -> None:
        self.built.listen("plane_pick", self.on_plane_pick)
        self.built.listen("plane_insert", self.on_plane_insert)
        self.built.listen("plane_delete", self.on_plane_delete)
        self.built.listen("plane_value", self.on_plane_value)

    def on_plane_pick(self, event: events.GenericEventArguments) -> None:
        layer, index = str(event.args.get("layer", "")), int(event.args.get("index", 0))
        if layer == "contour" and self.tool.id == "geometry":
            self.vertex = index
            self.show_edit()
        elif layer == "mesh" and self.tool.id == "mesh":
            self.show_element(index)
        elif layer.startswith("domain-") and self.tool.id == "region":
            self.domain_select.set_value(layer.removeprefix("domain-"))

    async def on_plane_insert(self, event: events.GenericEventArguments) -> None:
        editor = None if self.model is None else self.model.editor()
        if editor is None or self.tool.id != "geometry":
            return
        self.vertex = editor.insert(int(event.args.get("edge", 0)))
        await self.edited()

    async def on_plane_delete(self, event: events.GenericEventArguments) -> None:
        if self.tool.id == "geometry":
            await self.delete_vertex(int(event.args.get("index", 0)))

    async def on_plane_value(self, event: events.GenericEventArguments) -> None:
        path, value = str(event.args.get("path", "")), event.args.get("value")
        if path not in self.controls or not isinstance(value, int | float):
            return
        self.write(path, float(value))
        control = self.controls[path]
        if isinstance(control, ui.number):
            self.writing = False
            try:
                control.value = float(value)
            finally:
                self.writing = True
        await self.show()

    async def tick(self) -> None:
        await self.poll_assess()
        await super().tick()

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
            self.domain_select.set_enabled(self.model is not None)

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
                            ui.label(f"{int(count)}").classes("histogram-count")
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
                f"{title} of {len(quality)} elements, least {np.min(quality):.3f}; {below} at or "
                f"under the floor of {QUALITY_FLOOR:g}. A bar fills its elements in the view."
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
        quality = _mapping(held["mesh"].summary.get("quality"))
        sicn, gamma = quality.get("min_sicn"), quality.get("min_gamma")
        passed = all(isinstance(v, int | float) and v > QUALITY_FLOOR for v in (sicn, gamma))
        glyph, word = ("✓", "passed") if passed else ("✕", "failed")
        ui.label(
            f"{glyph} Quality gate {word}: least SICN {self.text(sicn, 'dimensionless')}, least "
            f"gamma {self.text(gamma, 'dimensionless')}; each must exceed {QUALITY_FLOOR:g}."
        ).classes("state-ok" if passed else "state-err").props("data-control=mesh-gate")

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
                source = "typed" if typed.get(path) is not None else "table"
                found[part] = (getattr(base, row), source)
        return found

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

    def show_parts(self) -> None:
        self.parts_box.clear()
        sizes, used, changed, scale = self.part_sizes(), self.used(), self.changed(), self.scale()
        wall_used = self.built_wall_nm()
        with self.parts_box:
            with ui.row().classes("parts-head no-wrap w-full"):
                ui.label("Mesh parts")
                ui.label(f"size used, {TIMES} {scale:g}")
            group = None
            for part, grouped, path, _ in PART_ROWS:
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
                    size = self.text(base * scale, "nm")
                typed = path in changed and part != "membrane"
                picked = self.look.get("pick") == part
                button = (
                    ui.button(on_click=lambda _, p=part: self.pick_part(p))
                    .props(
                        f"flat dense no-caps align=left data-control=mesh-part-{part} "
                        f"aria-pressed={str(picked).lower()} "
                        f'aria-label="{PARTS[part]}: {size}{", " + source if source else ""}"'
                    )
                    .classes("parts-row" + (" parts-child" if grouped else ""))
                )
                button.set_visibility(typed or not self.modified_only)
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
                    "Pick a part, in the list or the view, to size it: a blank size takes "
                    "section 5.2.2's table, and the size scale multiplies every size."
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
            said = f"Blank takes section 5.2.2's {table:g} nm"
            if part == "membrane":
                said = f"The membrane takes the global size. {said}"
            base, _ = self.part_sizes().get(part, (None, ""))
            gives = (
                "" if base is None else f"; {TIMES} {scale:g} gives {self.text(base * scale, 'nm')}"
            )
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
        self.quality_verdict()
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
        if self.tool.id == "geometry" and "contour" in held:
            summary = held["contour"].summary
            constriction = _mapping(summary.get("constriction"))
            rows.append(("Stage 4's checks", "✓ passed", None))
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
        query = urlencode({"tool": self.tool.id, **{k: v for k, v in self.look.items() if v}})
        return f"/api/continuum/{self.model.name}/plane?{query}"

    async def show(self) -> None:
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
