"""The Meso suite's tool pages: a continuum model's pore and charge, drawn from its molecule."""

from __future__ import annotations

import json
import math
import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import ClassVar, Literal, cast
from urllib.parse import urlencode

from nicegui import context, events, run, ui
from nicegui.elements.mixins.text_element import TextElement

from nanopnp.gui.assess import (
    Assessed,
    AssessFailed,
    Assessment,
    AssessProcess,
    AssessRequest,
    Seeded,
)
from nanopnp.gui.geometry import ProfileEditor
from nanopnp.gui.render import ChargeRequest, RenderedElements, RenderFailed, RenderProcess
from nanopnp.gui.web.continuum_tools import SUPPLIED, _ContinuumPane, _keyed, _mapping
from nanopnp.gui.web.frame import Views, heading
from nanopnp.gui.web.meso import MesoModel
from nanopnp.gui.web.molview import pqr_frame, study_side_view
from nanopnp.gui.web.plane import IMAGES, STAGE_THREE
from nanopnp.gui.web.screens import Tool
from nanopnp.gui.web.shell import Shell
from nanopnp.gui.web.tools import charge_colours
from nanopnp.io.models import Kind
from nanopnp.io.project import STORE_FOLDER
from nanopnp.plot.data import OVERLAY_SMOOTHING_NM

__all__ = ["meso_page"]

IMAGE_TITLES = {
    "density": "Density section, stage 2",
    "mean": "Mean, stage 3",
    "cn_variance": "Cn variance, stage 3",
    "raw_variance": "Raw variance, stage 3",
}
POINT_GROUP = "structure.symmetry.point_group"
PORE_TOOLS = ("density", "outline")
"""The tools of stages 2 to 4, which a supplied outline leaves unbuilt."""
NEAR_LISTED = 5
"""The residues a point of the density names, the nearest first."""
MOVED_LISTED = 12
"""The residues each side of an edit lists, the most atoms first."""
OVERLAY_TITLES = {"full": "Charge in 3D", "revolved": "Its mean about the axis"}
"""The overlay's two volumes, as its pane names them."""
OVERLAY_LEVEL = 0.1
"""A volume's isosurfaces open at this share of its largest magnitude."""

# The deployed charge's render, one per run record, kept for the server's life: a window that
# closes while it draws does not start it again.
_RENDERS: dict[Path, RenderProcess] = {}

_SUPERSCRIPT = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")


def _science(value: float, figures: int = 3) -> str:
    # A mantissa times a power of ten, its minus signs U+2212 as the pane writes them.
    if value == 0:
        return "0"
    mantissa, exponent = f"{value:.{figures - 1}e}".split("e")
    power = f"10{str(int(exponent)).translate(_SUPERSCRIPT)}"
    text = power if float(mantissa) == 1.0 else f"{mantissa}\u2009\u00d7\u200910" + power[2:]
    return text.replace("-", "\u2212")


class _MesoPane(_ContinuumPane):
    """A Meso tool's page: the molecule cut at its axis beside its (r, z) reduction."""

    kind: ClassVar[str] = "meso"
    model_kind: ClassVar[Kind] = "continuum"
    model_type: ClassVar[type[MesoModel]] = MesoModel

    def __init__(self, shell: Shell, tool: Tool, built: Views, focus: str) -> None:
        super().__init__(shell, tool, built, focus)
        self.look["image"] = "density" if tool.id == "density" else "mean"
        self.vertex: int | None = None
        self.assess: AssessProcess | None = None
        self.assessed: Assessment | str | None = None
        self.folder = Path()
        self.edit_box: ui.column
        self.vertex_r: ui.number
        self.vertex_z: ui.number
        self.near_box: ui.column
        self.near: list[tuple[str, float]] = []
        self.charge_box: ui.column
        self.layer: Literal["lattice", "deployed"] = "lattice"
        self.residue = ""
        self.linked = True
        self.drawn_render: str | None = None
        self.overlay: dict[str, float] = {}
        self.peaks: dict[str, float] | None = None
        self.computing = False

    @property
    def meso(self) -> MesoModel | None:
        """The continuum model as Meso reads it, over its molecular model."""
        return cast("MesoModel | None", self.model)

    def subject(self) -> str:
        model = self.model
        if self.project is None or model is None:
            return super().subject()
        molecular = model.molecular()
        over = f", over molecular model {molecular}" if molecular is not None else ""
        return f"Continuum model {model.name}{over}"

    def before_fields(self) -> None:
        if self.tool.id == "outline":
            self.outline_verdict()
        self.built_over()

    def own_status(self) -> None:
        model = self.model
        if model is None:
            return
        molecular = model.molecular()
        if self.tool.id in PORE_TOOLS and "contour" not in self.walked:
            said = SUPPLIED.get(self.supplied or "", "reads no structure")
            where = "here" if self.tool.id == "outline" else "in Outline"
            ui.label(
                f"This model {said}: stages 2 to 4 do not run, so their values are not read. "
                f"Its outline is drawn and edited {where}."
            )
        elif molecular is not None:
            ui.label(f"Drawn from molecular model {molecular}, outside any study.")
        else:
            ui.label("The project holds no molecular model for this model to be drawn from.")

    def signature(self) -> object:
        model = self.meso
        editing = model is not None and model.editor() is not None
        if model is None or self.tool.id != "charge":
            return editing
        record = model.charge_record()
        return [editing, str(record) if record else None, self.drawn_render]

    def readout(self) -> list[tuple[str, str, Callable[[], None] | None]]:
        model = self.model
        if model is None or self.tool.id != "outline":
            return []
        held = model.artefacts()
        if "contour" not in held:
            return []
        # The vertices and the narrowest radius lead the pane, with stage 4's verdict.
        summary = held["contour"].summary
        return [("Smallest feature", self.text(summary.get("min_feature_size_nm"), "nm"), None)]

    def after_refresh(self) -> None:
        if self.tool.id == "charge":
            self.show_charge()

    # -- the sections ---------------------------------------------------------------------------

    def density_section(self) -> None:
        self.picture_choice(IMAGES, "Drawn", "density")
        heading("Atoms near a point", 2)
        self.near_box = ui.column().classes("w-full gap-1").props("data-control=density-near")
        self.show_near()

    def outline_section(self) -> None:
        self.picture_choice(STAGE_THREE, "Drawn under the outline", "symmetry")
        self.outline_editor()

    def outline_verdict(self) -> None:
        held = {} if self.model is None or not self.usable() else self.model.artefacts()
        if "contour" not in held:
            return
        # A stored outline passed stage 4's checks: the stage refuses one that does not.
        summary = held["contour"].summary
        narrowest = _mapping(summary.get("constriction"))
        ui.label(
            f"✓ Stage 4's checks passed: narrowest radius {self.text(narrowest.get('r_nm'), 'nm')} "
            f"at z = {self.text(narrowest.get('z_nm'), 'nm')}, "
            f"{summary.get('vertex_count', '?')} vertices."
        ).classes("state-ok").props("data-control=contour-verdict")

    def picture_choice(self, images: tuple[str, ...], label: str, stage: str) -> None:
        """Draw the point group the map is averaged over and the picture the view draws."""
        case = None if self.model is None else self.model.case()
        if case is not None and case.structure is not None:
            group = case.structure.symmetry.point_group
            with self.named("Point group"):
                ui.link(
                    f"{group}, set in Prepare",
                    f"/molecular/prepare?field={POINT_GROUP}",
                ).props("data-control=geometry-point-group")
        heading("Picture", 2)
        with self.named(label):
            ui.select(
                {name: IMAGE_TITLES[name] for name in images},
                value=self.look["image"],
                on_change=lambda e: self.restyle("image", str(e.value)),
            ).props(
                'dense outlined options-dense data-control=plane-image aria-label="Picture"'
            ).set_enabled(self.model is not None and stage in self.walked)

    def outline_editor(self) -> None:
        """Draw the outline's editor."""
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

    @_keyed
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
                        mapped = model.states().get("symmetry") == "built"
                        ui.button("Seed from the map", on_click=self.seed).props(
                            "outline dense no-caps data-control=contour-seed"
                        ).set_enabled(self.usable() and mapped and not self.assessing())
                if self.measurable():
                    ui.label(
                        "Edit the built outline. If stage 4 blocks the outline, Seed from the "
                        "map traces a loop from the stored map to edit."
                    ).classes("later")
                self.show_assessment()
                return
            parent = (
                "stage 4's outline"
                if editor.parent_name.startswith("contour-")
                else f"the outline {editor.parent_name}"
            )
            state = (
                f"Editing {parent}: {len(editor.vertices)} vertices, edited; not saved."
                if editor.can_undo
                else f"Editing {parent}: no change yet."
            )
            ui.label(state).props("data-control=contour-state")
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
                # One row each, as the pane's values: side by side they leave no width to read.
                with self.named(f"Vertex {self.vertex}, r"):
                    self.vertex_r = ui.number(value=round(r, 4), suffix="nm", step=0.01).props(
                        'dense outlined data-control=contour-r aria-label="r of the vertex, in nm"'
                    )
                with self.named(f"Vertex {self.vertex}, z"):
                    self.vertex_z = ui.number(value=round(z, 4), suffix="nm", step=0.01).props(
                        'dense outlined data-control=contour-z aria-label="z of the vertex, in nm"'
                    )
                ui.button("Move vertex", on_click=self.move_vertex).props(
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
            self.show_moved(editor)

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
        # One that ended is still held until the next tick reads its answer and removes its folder.
        if model is None or case is None or self.assess is not None:
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
            self.refresh()
            await self.show()

    async def start_edit(self) -> None:
        if self.model is None:
            return
        try:
            self.model.start_edit()
        except ValueError as error:
            ui.notify(str(error), type="negative", multi_line=True)
            return
        # The refresh deletes the button this click came from, and with it the slot's client.
        client = context.client
        await self.edited()
        # The editor opens at the pane's foot: bring it into view.
        client.run_javascript(
            "document.querySelector('[data-control=contour-edit]')"
            "?.scrollIntoView({block: 'start', behavior: 'smooth'})"
        )

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
        self.refresh()

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
        ui.run_javascript("window.location.assign('/meso/outline')")

    # -- the view's events ---------------------------------------------------------

    async def on_plane_insert(self, event: events.GenericEventArguments) -> None:
        editor = None if self.model is None else self.model.editor()
        if editor is None or self.tool.id != "outline":
            return
        self.vertex = editor.insert(int(event.args.get("edge", 0)))
        await self.edited()

    async def on_plane_delete(self, event: events.GenericEventArguments) -> None:
        if self.tool.id == "outline":
            await self.delete_vertex(int(event.args.get("index", 0)))

    # -- Charge map --------------------------------------------------------------------------

    def charge_section(self) -> None:
        self.charge_box = ui.column().classes("w-full gap-2").props("data-control=charge-pane")

    def show_charge(self) -> None:
        model = self.meso
        self.charge_box.clear()
        with self.charge_box:
            if model is None:
                return
            with ui.row().classes("items-center no-wrap"):
                toggle = ui.toggle(
                    {"lattice": "Lattice map", "deployed": "Deployed on the mesh"},
                    value=self.layer,
                    on_change=lambda e: self.choose_layer(str(e.value)),
                ).props('dense no-caps data-control=charge-layer aria-label="What the map draws"')
                toggle.set_enabled(model.artefacts().get("charge") is not None)
            charges = model.charges()
            if charges is not None:
                # A link only where the residues are on the map.
                with ui.row().classes("items-center no-wrap"):
                    ui.badge("Linked" if self.linked else "Not linked").props(
                        "data-control=charge-link-state"
                    )
                    ui.button("Unlink" if self.linked else "Link", on_click=self.toggle_link).props(
                        "flat dense no-caps data-control=charge-link"
                    )
            if charges is None:
                said = (
                    "Correct the value the message above names, then build the charge."
                    if model.problem() is not None
                    else "Build the charge map to see it."
                    if model.artefacts().get("charge") is None
                    else "The charge does not come from a structure, so no residue is linked."
                )
                ui.label(said).classes("later").props("data-control=charge-residue")
            else:
                picked = (
                    f"Residue {self.residue}. Pick another on the map, the molecule or the list."
                    if self.residue
                    else "Pick a residue on the map, the molecule or the list."
                )
                ui.label(picked).props("data-control=charge-residue role=status")
                with (
                    ui.element("div")
                    .classes("charge-strip")
                    .props('role=group aria-label="Charged residues"')
                ):
                    for key, name, charge_e, copies in charges.residues():
                        # Its sign beside its name: the list is read for where the charge is.
                        sign = f"{charge_e:+.0f}".replace("-", "\u2212")
                        each = f", each of {copies} copies" if copies > 1 else ""
                        ui.button(
                            f"{key} {name} {sign}", on_click=lambda _, k=key: self.select(k)
                        ).props(
                            f"flat dense no-caps data-control=charge-strip-item "
                            f"aria-pressed={'true' if key == self.residue else 'false'} "
                            f'title="{name} {key}, {charge_e:+.2f} e{each}"'
                        ).classes("strip-item")
            self.overlay_rows()
            self.conservation_rows()
            self.render_note()

    def overlay_rows(self) -> None:
        model = self.meso
        heading("Overlay", 2)
        built = model is not None and model.artefacts().get("charge") is not None
        ui.label(
            f"Smoothed to {self.text(OVERLAY_SMOOTHING_NM, 'nm')}: each charged atom's Gaussian "
            "widened to at least that width, drawn over the structure at plus and minus a level."
        ).classes("later").props("data-control=overlay-smoothing")
        if self.computing:
            ui.label("Computing the overlay…").props("role=status data-control=overlay-busy")
        for which, title in OVERLAY_TITLES.items():
            with ui.row().classes("items-center no-wrap"):
                ui.checkbox(
                    title,
                    value=which in self.overlay,
                    on_change=lambda e, w=which: self.toggle_overlay(w, bool(e.value)),
                ).props(f"dense data-control=overlay-{which}").set_enabled(
                    built and not self.computing
                )
                if which in self.overlay and self.peaks is not None:
                    level = (
                        ui.number(
                            value=float(f"{self.overlay[which]:.3g}"),
                            min=0.0,
                            format="%.3g",
                            suffix="e/nm³",
                            on_change=lambda e, w=which: self.set_level(w, e.value),
                        )
                        .props(
                            f"dense outlined data-control=overlay-level-{which} "
                            f'aria-label="{title}: the isosurfaces\' level, in e/nm³"'
                        )
                        .style("width: 9rem")
                    )
                    level.props(f'title="Largest magnitude {self.peaks[which]:.3g} e/nm³"')

    async def toggle_overlay(self, which: str, on: bool) -> None:
        model = self.meso
        if model is None:
            return
        # A redraw deletes the checkbox that asked, and its slot: what follows runs in the box's.
        with self.charge_box:
            if not on:
                self.overlay.pop(which, None)
            elif self.peaks is None:
                self.computing = True
                self.show_charge()
                shown = await run.io_bound(model.volumes)
                self.computing = False
                if shown is None:
                    ui.notify("This model deposits no charge to overlay.", type="warning")
                    self.show_charge()
                    return
                self.peaks = {
                    "full": float(abs(shown.full).max()),
                    "revolved": float(abs(shown.revolved).max()),
                }
            if on and self.peaks is not None:
                self.overlay[which] = OVERLAY_LEVEL * self.peaks[which]
            self.show_charge()
            await self.show()

    async def set_level(self, which: str, value: object) -> None:
        if which not in self.overlay or not isinstance(value, int | float) or value <= 0:
            return
        self.overlay[which] = float(value)
        await self.show()

    def conservation_rows(self) -> None:
        model = self.meso
        view = None if model is None else model.conservation()
        heading("Conservation", 2)
        if view is None:
            built = model is not None and model.artefacts().get("charge") is not None
            said = (
                "The charge record holds no conservation check: no structure deposits it."
                if built
                else "No charge is built, so nothing is checked yet."
            )
            ui.label(said).classes("later")
            return
        with ui.element("table").classes("view-table legs").props("data-control=charge-legs"):
            with ui.element("thead"), ui.element("tr"):
                for text in ("Leg", "Relative error", "Tolerance", "Verdict"):
                    TextElement(tag="th", text=text).props("scope=col")
            with ui.element("tbody"):
                for leg in view.legs:
                    ratio = leg.ratio
                    # The verdict's glyph and word, in its state's colour.
                    glyph, word, look = (
                        ("", leg.reason or "not run", "state-none")
                        if leg.value is None
                        else ("\u2713", "within", "state-ok")
                        if ratio is not None and ratio <= 1.0
                        else ("\u2715", "over", "state-err")
                    )
                    with ui.element("tr"):
                        # Where the leg is worst, under its name: the pane holds four columns.
                        with ui.element("td"):
                            ui.label(leg.name)
                            if leg.location:
                                ui.label(leg.location).classes("field-hint")
                        TextElement(tag="td", text="" if leg.value is None else _science(leg.value))
                        TextElement(
                            tag="td",
                            text="" if leg.tolerance is None else _science(leg.tolerance, 1),
                        )
                        TextElement(tag="td", text=f"{glyph} {word}".strip()).classes(look)
        figures = view.figures
        shown = [
            (name, figures.get(key))
            for key, name in (
                ("q_net_e", "Net charge"),
                ("q_grid_e", "On the lattice"),
                ("q_mesh_e", "On the mesh"),
            )
        ]
        with ui.element("dl").classes("readout-list").props("data-control=charge-figures"):
            for name, value in shown:
                if isinstance(value, int | float) and math.isfinite(float(value)):
                    TextElement(tag="dt", text=name)
                    TextElement(tag="dd", text=f"{float(value):+.4f} e")

    def render_note(self) -> None:
        model = self.meso
        if model is None or self.layer != "deployed":
            return
        record = model.charge_record()
        process = None if record is None else _RENDERS.get(record)
        if record is None:
            ui.label("Build the charge map: the deployed charge is read from its record.")
        elif model.elements() is None and process is not None and process.running:
            ui.label("Drawing the deployed charge…").props("role=status")

    async def choose_layer(self, layer: str) -> None:
        self.layer = "deployed" if layer == "deployed" else "lattice"
        if self.layer == "deployed":
            self.start_render()
        await self.redraw()
        self.shown_state = ""
        self.refresh()

    def start_render(self) -> None:
        model = self.meso
        record = None if model is None else model.charge_record()
        if model is None or record is None or model.elements() is not None:
            return
        held = _RENDERS.get(record)
        if held is not None and (held.running or not held.answered):
            return
        process = RenderProcess(ChargeRequest(run=str(record), elements=True))
        process.start()
        _RENDERS[record] = process

    # -- Density's point ---------------------------------------------------------------------

    def show_near(self) -> None:
        self.near_box.clear()
        model = self.meso
        atoms = None if model is None else model.residue_atoms()
        with self.near_box:
            if not self.near:
                ui.label(
                    "Click the picture to name the residues whose atoms reach the point first: "
                    "stage 2's density is a union of its atoms, so each is ranked by its distance "
                    "in its own atom's kernel width."
                ).classes("later")
                return
            for key, widths in self.near:
                name = "" if atoms is None else atoms.name(key)
                copies = 0 if atoms is None else len(atoms.copies(key))
                each = f", each of {copies} copies" if copies > 1 else ""
                ui.button(
                    f"{key} {name}  {widths:.1f} widths", on_click=lambda _, k=key: self.select(k)
                ).props(
                    "flat dense no-caps align=left data-control=density-near-item "
                    f"aria-pressed={'true' if key == self.residue else 'false'} "
                    f'title="{name} {key}: its nearest atom {widths:.2f} kernel widths away{each}"'
                ).classes("strip-item")

    # -- the atoms an edit moves -------------------------------------------------------------

    def show_moved(self, editor: ProfileEditor) -> None:
        import numpy as np

        model = self.meso
        atoms = None if model is None else model.residue_atoms()
        if atoms is None or not editor.start or len(editor.vertices) < 3:
            return
        moved = atoms.moved(np.asarray(editor.start), np.asarray(editor.vertices))
        with ui.column().classes("w-full gap-1").props("data-control=contour-moved"):
            for title, rows in (("Into the water", moved.out), ("Into the protein", moved.in_)):
                heading(title, 3)
                if not rows:
                    ui.label("No atom crosses the outline this way.").classes("later")
                    continue
                ordered = sorted(rows.items(), key=lambda row: -row[1].atoms)
                for key, count in ordered[:MOVED_LISTED]:
                    name = atoms.name(key)
                    copies = len(atoms.copies(key))
                    each = f", each of {copies} copies" if copies > 1 else ""
                    sign = f"{count.charge_e:+.2f}".replace("-", "\u2212")
                    ui.button(
                        f"{key} {name}  {count.atoms:.1f} atoms, {sign} e",
                        on_click=lambda _, k=key: self.select(k),
                    ).props(
                        "flat dense no-caps align=left data-control=contour-moved-item "
                        f"aria-pressed={'true' if key == self.residue else 'false'} "
                        f'title="{name} {key}: per copy and frame{each}"'
                    ).classes("strip-item")
                if len(ordered) > MOVED_LISTED:
                    ui.label(f"and {len(ordered) - MOVED_LISTED} more residues.").classes("later")

    # -- the views' events -------------------------------------------------------------------

    def listen(self) -> None:
        super().listen()
        self.built.listen("plane_insert", self.on_plane_insert)
        self.built.listen("plane_delete", self.on_plane_delete)
        self.built.listen("plane_point", self.on_point)
        self.built.listen("mol_pick", self.on_mol)

    def on_plane_pick(self, event: events.GenericEventArguments) -> None:
        layer, index = str(event.args.get("layer", "")), int(event.args.get("index", 0))
        if layer == "contour" and self.tool.id == "outline":
            self.vertex = index
            self.show_edit()
            return
        super().on_plane_pick(event)

    async def on_point(self, event: events.GenericEventArguments) -> None:
        model = self.meso
        if model is None:
            return
        r, z = float(event.args["r"]), float(event.args["z"])
        if self.tool.id == "density":
            atoms = model.density_atoms()
            # The section's x is r on its right half; its left half is the same pore.
            self.near = [] if atoms is None else atoms.nearest(abs(r), z, NEAR_LISTED)
            self.show_near()
            if self.near:
                await self.select(self.near[0][0])
            return
        charges = model.charges()
        if charges is None or not self.linked:
            return
        found = charges.at(r, z)
        if found:
            await self.select(found[0][0])

    async def on_mol(self, event: events.GenericEventArguments) -> None:
        if self.tool.id != "charge" or self.linked:
            await self.select(str(event.args.get("key", "")), move=False)

    def group(self, key: str) -> tuple[str, tuple[str, ...]] | None:
        """Return the key a residue is named by and its copies' keys, or None where none is."""
        model = self.meso
        if model is None or not key:
            return None
        if self.tool.id == "charge":
            charges = model.charges()
            if charges is None or key not in charges:
                return None
            return charges.group(key), charges.copies(key)
        atoms = model.residue_atoms()
        if atoms is None or not atoms.copies(key):
            return None
        return atoms.group(key), atoms.copies(key)

    async def select(self, key: str, *, move: bool = True) -> None:
        found = self.group(key)
        if found is None:
            return
        self.residue, copies = found
        # The views first: the refresh rebuilds the box that holds the button that asked.
        await self.redraw()
        if move:
            await ui.run_javascript(f"nano.show({json.dumps(list(copies))})", timeout=30)
        if self.tool.id == "density":
            self.show_near()
        elif self.tool.id == "outline":
            self.show_edit()
        self.shown_state = ""
        self.refresh()

    async def tick(self) -> None:
        await self.poll_assess()
        await super().tick()
        model = self.meso
        if model is None or self.tool.id != "charge" or self.layer != "deployed":
            return
        record = model.charge_record()
        process = None if record is None else _RENDERS.get(record)
        if process is None:
            return
        for event in process.drain():
            if isinstance(event, RenderFailed):
                ui.notify(f"The deployed charge was not drawn: {event.message}", type="negative")
            elif isinstance(event, RenderedElements):
                self.drawn_render = event.path
                self.shown_state = ""
                self.refresh()
                await self.redraw()

    def toggle_link(self) -> None:
        self.linked = not self.linked
        self.shown_state = ""
        self.refresh()

    # -- the views ---------------------------------------------------------------------------

    async def redraw(self) -> None:
        """Draw the map again, the molecule kept: a pick or a layer changes the map alone."""
        url = self.plane_url()
        await ui.run_javascript(f"nano.plane({json.dumps(url) if url else 'null'}, '')", timeout=60)

    def scene_key(self) -> str:
        model = self.meso
        if model is None:
            return ""
        table = model.artefacts().get("protonation")
        if table is not None:
            return table.hash[:16]
        pqr = model.pqr()
        return "" if pqr is None or not pqr.is_file() else f"pqr-{pqr.stat().st_mtime_ns}"

    def scene_url(self) -> str | None:
        model = self.meso
        key = self.scene_key()
        if model is None or not key:
            return None
        colour = "charge" if self.tool.id == "charge" else "chain"
        charge = model.artefacts().get("charge")
        if charge is not None:
            # The overlay is the charge's: a new charge takes a new address.
            key = f"{key}-{charge.hash[:12]}"
        query = {"colour": colour, "positive": charge_colours(self.shell), "v": key}
        for which, level in self.overlay.items():
            query[which] = f"{level:.6g}"
        table = model.table()
        seen = study_side_view(table, None if table is not None else pqr_frame(model.pqr()))
        if seen is not None and seen.chain is not None:
            # A pore of two chains or more can show one subunit alone.
            query["subunit"] = "0"
        return f"/api/meso/{model.name}/scene?{urlencode(query)}"

    def plane_url(self) -> str | None:
        model = self.meso
        if model is None:
            return None
        if self.tool.id != "charge":
            query = {"tool": self.tool.id, "image": self.look["image"], "residue": self.residue}
            return (
                f"/api/meso/{model.name}/plane?{urlencode({k: v for k, v in query.items() if v})}"
            )
        charge = model.artefacts().get("charge")
        if charge is None:
            return None
        drawn = {
            "layer": self.layer,
            "residue": self.residue,
            "positive": charge_colours(self.shell),
            "v": charge.hash[:12],
        }
        return f"/api/meso/{model.name}/charge/plane?{urlencode(drawn)}"

    async def show(self) -> None:
        await self.built.show_pair(self.scene_url(), self.plane_url(), self.scene_key())


def meso_page(shell: Shell, tool: Tool) -> Callable[..., None]:
    """Return the page of one Meso tool, which the frame's sub-pages build."""

    def page(built: Views, field: str = "") -> None:
        shell.last_tool["meso"] = tool.id
        _MesoPane(shell, tool, built, field).build()

    return page
