"""A suite's tool pages, the tool list and a pane of the model's values; Molecular's 3D view."""

from __future__ import annotations

import json
import math
import tempfile
import typing
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager, nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, Generic, Literal, TypeVar

from nicegui import events, run, ui
from nicegui.elements.mixins.text_element import TextElement
from nicegui.elements.mixins.validation_element import ValidationElement

from nanopnp.api.project import Project
from nanopnp.core.stages import walk_order
from nanopnp.gui.web import numbers, settings
from nanopnp.gui.web.builds import BuiltModel
from nanopnp.gui.web.frame import Views, heading
from nanopnp.gui.web.link import _chain_id
from nanopnp.gui.web.molecular import MolecularModel
from nanopnp.gui.web.molview import (
    COLOURINGS,
    REPRESENTATIONS,
    ChargeColours,
    frame_count,
    residues,
    titration_states,
)
from nanopnp.gui.web.screens import (
    CORRECTED,
    STAGE_RUNNING,
    SUITES,
    Tool,
    field_control,
    tool_for,
    tool_view,
)
from nanopnp.gui.web.settings import SETTINGS
from nanopnp.gui.web.shell import Shell
from nanopnp.io.case import ChargeEdit, Membrane
from nanopnp.io.case_paths import schema_default
from nanopnp.io.models import read_model_file
from nanopnp.io.project import INPUTS_FOLDER, ItemKind, split_reference
from nanopnp.pipeline.checks import options_at
from nanopnp.structure.orient import (
    PreparationRecord,
    orient_pore,
    prepared_pore,
    protein_chains,
)
from nanopnp.structure.protonated import parent_residue

__all__ = [
    "FIELDS",
    "OVERLAY_MOST",
    "Field",
    "charge_colours",
    "current_model",
    "current_name",
    "tool_page",
]

OVERLAY_MOST = 10
"""The most frames the view draws over one another."""

LINKED_NOTE = ("prepare", "ensemble", "protonation")
"""The tools whose values a linked variant reads from its parent."""
CARD_SHORT = 200
"""A card shows this much of a message; the rest unfolds."""
MEMBRANE_OFF_NM = 0.01
"""How far the registration residues' centre may lie from the membrane's before Prepare warns."""
STRUCTURE_SUFFIXES = (".pdb", ".ent", ".cif", ".mmcif", ".gz")


@dataclass(frozen=True)
class Field:
    """How a tool's pane shows one case value.

    Parameters
    ----------
    kind
        ``text``, ``number``, ``choice`` among the values the schema accepts at the path,
        ``chains``, a pick among the structure file's chains that also takes a typed group,
        ``list``, which the pane shows and a tool of its own edits, ``switch``, on or off, or
        ``materials``, a number per material the pane's ``solids`` names.
    """

    label: str
    kind: Literal["text", "number", "choice", "chains", "list", "switch", "materials"] = "text"
    unit: str = ""
    hint: str = ""


FIELDS: dict[str, Field] = {
    "structure.source.path": Field("Structure file", hint="A PDB or mmCIF file"),
    "structure.source.chains": Field("Chains", "chains", hint="all"),
    "structure.symmetry.point_group": Field("Point group", hint="C1, or Cn of the ring"),
    "structure.symmetry.axis": Field("Axis", "choice"),
    "structure.ensemble.trajectory": Field("Trajectory", hint="None: the file's models"),
    "structure.ensemble.frames.count": Field("Frames kept", "number"),
    "structure.ensemble.frames.last_ns": Field("Time window", "number", unit="ns"),
    "charge.ph": Field("pH", "number"),
    "charge.forcefield": Field("Force field", "choice"),
    "charge.titration": Field("Titration", "choice"),
    "charge.edits": Field("Residue edits", "list"),
    "geometry.density.grid_spacing_nm": Field("Grid spacing", "number", unit="nm"),
    "geometry.density.sharpness": Field("Kernel sharpness", "number"),
    "geometry.density.atoms": Field("Atoms smeared", "choice"),
    "geometry.contour.isolevel": Field("Isolevel", "number"),
    "geometry.contour.smoothing": Field("Smoothing", "choice"),
    "geometry.contour.simplify_tol_nm": Field("Simplification", "number", unit="nm"),
    "geometry.membrane.thickness_nm": Field("Membrane thickness", "number", unit="nm"),
    "geometry.membrane.centre_z_nm": Field("Membrane centre, z", "number", unit="nm"),
    "geometry.reservoir.radius_nm": Field("Reservoir radius", "number", unit="nm"),
    "charge.exclusion_offset_nm": Field("Ion-exclusion offset", "number", unit="nm"),
    "geometry.pore.radius_nm": Field("Pore radius", "number", unit="nm"),
    "numerics.mesh.backend": Field("Mesher", "choice"),
    "numerics.mesh.size_scale": Field("Size scale", "number"),
    "numerics.mesh.maxh_nm": Field("Global size", "number", unit="nm", hint="the table's"),
    "numerics.mesh.sizes.protein_nm": Field("Protein", "number", unit="nm", hint="the table's"),
    "numerics.mesh.sizes.electrolyte_nm": Field(
        "Electrolyte", "number", unit="nm", hint="the table's"
    ),
    "numerics.mesh.sizes.arc_nm": Field("Outer boundary", "number", unit="nm", hint="the table's"),
    "numerics.mesh.sizes.axis_in_pore_nm": Field(
        "Axis in the pore", "number", unit="nm", hint="the table's"
    ),
    "numerics.mesh.wall_h_nm": Field("Wall", "number", unit="nm", hint="auto"),
    "physics.model": Field("Model", "choice"),
    "physics.flow": Field("Flow", "switch"),
    "physics.variable_density": Field("Variable density", "switch"),
    "physics.inertia": Field("Inertia", "switch"),
    "physics.dielectric_gradient_forces": Field("Dielectric forces", "switch"),
    "numerics.elements.phi": Field("Potential, φ", "choice"),
    "numerics.elements.c": Field("Concentrations, c", "choice"),
    "numerics.elements.u": Field("Velocity, u", "choice"),
    "numerics.elements.p": Field("Pressure, p", "choice"),
    "numerics.stabilisation": Field("Stabilisation", "choice"),
    "electrolyte.parameters": Field("Parameter set", "choice"),
    "electrolyte.species": Field("Ions", "list"),
    "electrolyte.concentration_M": Field("Concentration", "number", unit="M"),
    "electrolyte.temperature_K": Field("Temperature", "number", unit="K"),
    "electrolyte.driver": Field("Driver", "choice"),
    **{
        f"electrolyte.corrections.{name}.{part}": Field(
            f"{name.capitalize()}{'' if part == 'model' else ', ' + part}",
            "choice" if part == "model" else "switch",
        )
        for name in CORRECTED
        for part in ("model", "concentration", "wall")
    },
    "electrolyte.corrections.steric.model": Field("Steric flux", "choice"),
    "electrolyte.corrections.steric.a_ion_nm": Field(
        "Ion diameter", "number", unit="nm", hint="default"
    ),
    "electrolyte.corrections.steric.a_water_nm": Field(
        "Water diameter", "number", unit="nm", hint="default"
    ),
    "numerics.wall_distance.sources": Field("Wall boundaries", hint="a pattern of names"),
    "numerics.wall_distance.max_distance_nm": Field("Distance cap", "number", unit="nm"),
    "boundary_conditions.bias_V": Field("Bias", "number", unit="V"),
    "boundary_conditions.ground": Field("Grounded side", "choice"),
    "boundary_conditions.walls.ion_flux": Field("Ion flux at walls", "choice"),
    "boundary_conditions.walls.slip": Field("Flow at walls", "choice"),
    "boundary_conditions.wall_charge_C_m2": Field("Wall charge", "number", unit="C/m²"),
    "physics.solid_permittivities": Field("Solid permittivities", "materials"),
}
"""Every value a suite's tool sets, by case path."""

# The stage each tool's build walks to, the build's name and the colouring its view opens with;
# a tool with no stage builds nothing.
BUILDS: dict[str, tuple[str | None, str, str]] = {
    "prepare": ("structure", "Build ensemble", "chain"),
    "ensemble": ("structure", "Build ensemble", "chain"),
    "protonation": ("protonation", "Build molecular model", "charge"),
    "edit": ("protonation", "Build molecular model", "changed"),
    "view": (None, "", "charge"),
    "geometry": ("contour", "Build geometry", ""),
    "region": ("region", "Build region", ""),
    "mesh": ("mesh", "Build mesh", ""),
    "equations": (None, "", ""),
    "electrolyte": (None, "", ""),
    "conditions": (None, "", ""),
    "exposed": (None, "", ""),
}

STAGE_TITLES = {
    "structure": "Ensemble",
    "protonation": "Protonation",
    "density": "Density",
    "symmetry": "Reduction to (r, z)",
    "contour": "Contour",
    "region": "Region",
    "mesh": "Mesh",
}
# Each state's glyph and word (the glyph never stands alone), and its colour class.
STATES = {
    "empty": ("○", "not built", "state-none"),
    "building": ("●", "building", "state-run"),
    "built": ("✓", "built", "state-ok"),
    "refused": ("✕", "blocked", "state-err"),
}
EDIT_STATES = typing.get_args(typing.get_args(ChargeEdit.model_fields["state"].annotation)[0])
EDIT_KINDS = {
    "state": "Protonation state",
    "charge_change_e": "Charge change",
    "radius_scale": "Radius scale",
}

STATES_COLUMNS = [
    {"name": "group", "label": "Group", "field": "group", "align": "left", "sortable": True},
    {"name": "kind", "label": "Kind", "field": "kind", "align": "left", "sortable": True},
    {"name": "pka", "label": "pKa", "field": "pka", "sortable": True},
    {"name": "applied_e", "label": "Residue's charge, e", "field": "applied_e", "sortable": True},
    {"name": "expected_e", "label": "State expects, e", "field": "expected_e", "sortable": True},
    {"name": "state", "label": "State", "field": "state", "align": "left", "sortable": True},
]


def charge_colours(shell: Shell) -> ChargeColours:
    """Return the colour a positive charge takes, as the user's setting has it."""
    return "red" if shell.settings.value("charge_colours") == "red-positive" else "blue"


def current_name(shell: Shell, kind: ItemKind) -> str | None:
    """Return the model of a kind the tools edit: the open one, else the project's first."""
    project = shell.bench.project
    if project is None:
        return None
    names = project.items(kind)
    if not names:
        return None
    if project.current:
        current_kind, current = split_reference(project.current)
        if current_kind == kind and current in names:
            return current
    return names[0]


def current_model(shell: Shell) -> MolecularModel | None:
    """Return the molecular model the tools edit: the open one, else the project's first."""
    project, name = shell.bench.project, current_name(shell, "molecular")
    if project is None or name is None:
        return None
    return MolecularModel(project, name, shell.queue)


_DRAFTS: dict[tuple[Path, str], dict[str, Any]] = {}
# A structure file's chains, by its path and modification time: reading them loads the file.
_CHAINS: dict[tuple[Path, int], tuple[str, ...]] = {}


def _draft(model: MolecularModel | None) -> dict[str, Any]:
    fresh = {
        "tilt": None,
        "azimuth": None,
        "cis_end": "wider",
        "registration": "",
        "centre": 0.0,
        "typed": False,
    }
    if model is None:
        return fresh
    return _DRAFTS.setdefault((model.project.root, model.name), fresh)


def _listed(chains: str) -> list[str]:
    return [entry.strip() for entry in chains.split(",") if entry.strip()]


def _value_of(body: Any, path: str) -> Any:  # noqa: ANN401 - a parsed YAML body
    cursor = body
    for part in path.split("."):
        if not isinstance(cursor, dict) or part not in cursor:
            return None
        cursor = cursor[part]
    return cursor


def _default_of(path: str) -> Any:  # noqa: ANN401 - whatever the schema declares
    try:
        has_default, default = schema_default(path)
    except KeyError:
        return None
    return default if has_default else None


def _axis_of(tilt_deg: float, azimuth_deg: float) -> tuple[float, float, float]:
    tilt, azimuth = math.radians(tilt_deg), math.radians(azimuth_deg)
    return (
        math.sin(tilt) * math.cos(azimuth),
        math.sin(tilt) * math.sin(azimuth),
        math.cos(tilt),
    )


def _angles_of(axis: tuple[float, float, float]) -> tuple[float, float]:
    x, y, z = axis
    if z < 0:
        x, y, z = -x, -y, -z
    tilt = math.degrees(math.acos(max(-1.0, min(1.0, z / math.sqrt(x * x + y * y + z * z)))))
    tilt = round(tilt, 3)
    # An axis along z has no azimuth to speak of.
    return tilt, round(math.degrees(math.atan2(y, x)), 3) if tilt else 0.0


def _registration(text: str) -> tuple[int, int] | None:
    if not text.strip():
        return None
    first, _, last = text.partition(":")
    try:
        return int(first), int(last)
    except ValueError:
        raise ValueError(
            f"registration residues {text!r}: give the first and the last as 164:186"
        ) from None


ModelT = TypeVar("ModelT", bound=BuiltModel)


class _Pane(Generic[ModelT]):
    """One tool's page of a suite: its list of tools, its pane of values, its build and its view.

    A suite's own pane adds its sections, its readout and its view.
    """

    kind: ClassVar[str]
    """The suite the pane's tools belong to."""

    def __init__(
        self, shell: Shell, tool: Tool, built: Views, focus: str, model: ModelT | None
    ) -> None:
        self.shell = shell
        self.tool = tool
        self.built = built
        self.focus = focus
        self.model = model
        self.suite = next(suite for suite in SUITES if suite.id == self.kind)
        self.stage, self.build_title, self.colouring = BUILDS[tool.id]
        self.rows: dict[str, ui.element] = {}
        self.marks: dict[str, tuple[ui.label, ui.button]] = {}
        self.controls: dict[str, ui.element] = {}
        self.writing = True
        self.modified_only = False
        self.was_building = False
        self.shown_state = ""
        self.dismissed: set[str] = set()
        self.busy = False
        self.flagged: str | None = None
        self.linked_to: str | None = None
        self.status: ui.element
        self.cards: ui.column
        self.actions: ui.row
        self.readout_box: ui.column

    # -- what a suite's pane adds --------------------------------------------------

    def before_fields(self) -> None:
        """Draw what the pane shows above the tool's values."""

    def idle(self) -> bool:
        """Say whether the tool's values are shown but not set here."""
        return not self.usable()

    def readout(self) -> list[tuple[str, str, Callable[[], None] | None]]:
        """Return the built stage's figures this tool shows: a name, a value, what opens it."""
        return []

    def warnings(self) -> list[tuple[str, str]]:
        """Return the warnings the tool shows, each as a key and a text."""
        return []

    def own_status(self) -> None:
        """Say what the suite's model lacks for its tools, where it lacks something."""

    def own_actions(self, ready: bool, building: bool) -> None:
        """Draw the tool's own actions, before its build."""

    def own_cards(self) -> None:
        """Draw the tool's own notes, after the refusals and warnings."""

    def unbuilt(self, tool_id: str) -> str | None:
        """Return why a tool's stage does not run for this model, its state's word, or None."""
        return None

    def solids(self) -> tuple[str, ...]:
        """Return the materials a ``materials`` field has a row for."""
        return ()

    def aside(self, path: str) -> str | None:
        """Return what a field's outlined diamond says of a value set elsewhere, or None."""
        return None

    def after_refresh(self) -> None:
        """Bring what the tool's own sections show up to date with the model."""

    async def show(self) -> None:
        """Show the model in the suite's view."""

    # -- what the model holds ------------------------------------------------

    @property
    def project(self) -> Project | None:
        return self.shell.bench.project

    def body(self) -> dict[str, Any]:
        return {} if self.model is None else self.model.body()

    def changed(self) -> set[str]:
        if self.model is None:
            return set()
        try:
            listed = self.model.project.changes(self.model.kind, self.model.name)
        except (ValueError, OSError):
            return set()
        return {change.path for change in listed}

    def exposed(self) -> set[str]:
        if self.model is None:
            return set()
        try:
            location = self.model.project.path(self.model.kind, self.model.name)
            return {value.path for value in read_model_file(self.model.kind, location).exposed}
        except (ValueError, OSError):
            return set()

    def usable(self) -> bool:
        return self.model is not None and self.model.problem() is None

    def text(self, value: object, unit: str | None = None) -> str:
        chosen = self.shell.settings
        return numbers.shown(
            value,
            unit,
            figures=int(str(chosen.value("significant_figures"))),
            style="powers" if chosen.value("number_style") == "powers" else "prefixes",
        )

    def keyed_once(self) -> AbstractContextManager[None]:
        """Read the model and key its walk once while the pane is drawn."""
        return nullcontext() if self.model is None else self.model.keyed_once()

    def build(self) -> None:
        with self.keyed_once():
            self.build_pane()
        ui.timer(1.0, self.tick)
        ui.timer(0.1, self.start, once=True)

    def build_pane(self) -> None:
        with ui.element("div").classes("tool-page"):
            self.tool_list()
            with ui.column().classes("tool-pane").props("data-control=tool-pane"):
                heading(self.tool.title, 1)
                if self.model is not None:
                    ui.label(self.subject()).classes("tool-subject")
                self.status = ui.element("div").props("data-control=tool-status role=status")
                self.status.classes("tool-status")
                self.actions = ui.row().classes("tool-actions items-center no-wrap")
                self.cards = ui.column().classes("tool-cards")
                if self.tool.fields or self.tool.parts:
                    ui.checkbox("Modified only", on_change=self.on_modified).props(
                        "dense data-control=tool-modified"
                    )
                body, changed, exposed = self.body(), self.changed(), self.exposed()
                self.before_fields()
                for path in self.tool.fields:
                    self.field(path, body, path in changed, path in exposed)
                getattr(self, f"{self.tool.id}_section")()
                self.readout_box = ui.column().classes("readout")
                self.readout_box.props("data-control=tool-readout")
            if tool_view(self.suite, self.tool) == "page":
                # A view the page draws itself, beside the pane, in place of the frame's.
                self.view_box = ui.element("div").classes("tool-view")
                self.view_box.props(
                    f'data-control=tool-view role=region aria-label="{self.tool.title}"'
                )
        self.listen()
        self.refresh()

    def covering(self, running: str | None) -> str | None:
        """Return the stage of the suite's tools a running stage builds toward, or None.

        A walk runs the stages before a tool's own, such as a continuum model's molecular
        stages, under the first tool whose stage comes at or after the one running.
        """
        if running is None:
            return None
        order = walk_order()
        built = [BUILDS[tool.id][0] for tool in self.suite.tools]
        later = [s for s in built if s is not None and order.index(s) >= order.index(running)]
        return min(later, key=order.index) if later else None

    def signature(self) -> object:
        """Return what else of the pane a refresh redraws when it changes."""
        return None

    def build_held(self) -> str | None:
        """Return why the tool's build waits, such as an edit not yet saved, or None."""
        return None

    def listen(self) -> None:
        """Route the view's events to the pane."""

    def subject(self) -> str:
        if self.project is None:
            return "No project is open. Create or open one from the File menu."
        if self.model is None:
            return f"The project holds no {self.kind} model."
        return f"{self.suite.title} model {self.model.name}"

    def tool_list(self) -> None:
        """Draw the suite's tools, each with the state of the stage it builds and its progress."""
        named = f'aria-label="{self.suite.title} tools"'
        with ui.element("nav").classes("tool-list").props(named):
            self.tool_links: dict[str, tuple[ui.link, ui.label, ui.label, ui.linear_progress]] = {}
            for tool in self.suite.tools:
                link = ui.link(target=f"/{self.kind}/{tool.id}").classes("tool-link")
                link.props(f"data-control=tool-link-{tool.id} data-state=none")
                if tool.id == self.tool.id:
                    link.classes("tool-link-open").props("aria-current=page")
                # A row: the tool's name, its stage's glyph on the right, the state's word in the
                # row's name and tooltip.
                with link:
                    ui.label(tool.title).classes("tool-name")
                    glyph = ui.label("").classes("tool-glyph").props("aria-hidden=true")
                    word = ui.label("").classes("tool-word").props("aria-hidden=true")
                    bar = ui.linear_progress(show_value=False).props("indeterminate size=3px")
                    bar.classes("tool-progress").set_visibility(False)
                self.tool_links[tool.id] = (link, glyph, word, bar)

    @contextmanager
    def named(self, label: str) -> Iterator[tuple[ui.element, ui.label]]:
        """Open one row of the pane for a control that sets no case value: its name, then it."""
        with ui.element("div").classes("field-row") as row:
            ui.label("").classes("mark")
            name = ui.label(label).classes("field-label")
            yield row, name

    def field(self, path: str, body: dict[str, Any], changed: bool, exposed: bool) -> None:
        spec = FIELDS[path]
        value = _value_of(body, path)
        shown = value if value is not None else _default_of(path)
        control_name = field_control(path)
        named = f'data-control={control_name} aria-label="{spec.label}"'
        with ui.element("div").classes("field-row").props(f'data-field="{path}"') as row:
            mark = ui.label("◆").classes("changed mark").props("aria-hidden=true")
            aside = self.aside(path)
            if aside is None:
                ui.label(spec.label).classes("field-label")
            else:
                # A value set elsewhere that this one stands in for: the outlined diamond.
                with ui.element("div").classes("field-label"):
                    ui.label(spec.label)
                    ui.label("◇").classes("aside-mark").props(
                        f'role=img aria-label="{aside}" title="{aside}"'
                    )
            control: ui.element
            if spec.kind == "switch":
                control = ui.switch(
                    value=bool(shown), on_change=lambda e, p=path: self.write(p, bool(e.value))
                ).props(f"dense {named}")
            elif spec.kind == "materials":
                held = shown if isinstance(shown, dict) else {}
                control = ui.column().classes("materials w-full gap-1")
                control.props(f'data-control={control_name} role=group aria-label="{spec.label}"')
                with control:
                    for solid in self.solids():
                        with ui.row().classes("material-row items-center no-wrap w-full"):
                            ui.label(solid).classes("material-name")
                            ui.number(
                                value=held.get(solid),
                                on_change=lambda e, p=path, m=solid: self.write_material(
                                    p, m, e.value
                                ),
                            ).props(
                                f'dense outlined debounce=500 aria-label="{spec.label}, {solid}"'
                            ).set_enabled(not self.idle())
                    if not self.solids():
                        ui.label("The shown pore holds no solid.").classes("later")
            elif spec.kind == "list":
                entries = shown if isinstance(shown, list) else []
                text = f"{len(entries)} edit{'' if len(entries) == 1 else 's'}"
                control = ui.label(text).props(f"data-control={control_name}")
            elif spec.kind == "chains":
                listed = [] if shown in (None, "all") else _listed(str(shown))
                control = ui.select(
                    listed,
                    value=listed,
                    multiple=True,
                    with_input=True,
                    new_value_mode="add-unique",
                    on_change=lambda e, p=path: self.write(p, ",".join(e.value) or None),
                ).props(
                    f'dense outlined use-chips options-dense placeholder="{spec.hint}" {named} '
                    'title="Pick the chains, or type A+B and Enter for a group; none for all"'
                )
            elif spec.kind == "choice":
                options = list(options_at(path) or ())
                control = ui.select(
                    options,
                    value=shown if shown in options else None,
                    on_change=lambda e, p=path: self.write(p, e.value),
                ).props(f"dense outlined options-dense {named}")
            elif spec.kind == "number":
                control = ui.number(
                    # A number that defaults to a word, such as the wall's auto, shows blank.
                    value=shown if isinstance(shown, int | float) else None,
                    suffix=spec.unit or None,
                    placeholder=spec.hint or None,
                    on_change=lambda e, p=path: self.write(p, e.value),
                ).props(f"dense outlined debounce=500 {named}")
            else:
                control = ui.input(
                    value="" if shown is None else str(shown),
                    placeholder=spec.hint,
                    on_change=lambda e, p=path: self.write(p, e.value or None),
                ).props(f"dense outlined debounce=500 {named}")
            reset = ui.button(icon="sym_o_undo", on_click=lambda _, p=path: self.reset(p)).props(
                f'flat dense aria-label="Reset {spec.label}" data-control=reset-{control_name}'
            )
            # A value is exposed to studies once the model sets it; an unset one has nothing to
            # expose.
            if spec.kind == "number" and (value is not None or exposed):
                ui.checkbox(
                    "Expose",
                    value=exposed,
                    on_change=lambda e, p=path: self.expose(p, bool(e.value)),
                ).props(f'dense aria-label="Expose {spec.label} to studies"').set_enabled(
                    not self.idle()
                )
        # A model that reads a PQR has no structure for these values to act on, and a linked
        # variant reads them from its parent.
        if self.idle() and isinstance(control, ui.select | ui.number | ui.input | ui.switch):
            control.disable()
        self.rows[path] = row
        self.marks[path] = (mark, reset)
        self.controls[path] = control
        self.mark(path, changed)

    def mark(self, path: str, changed: bool) -> None:
        mark, reset = self.marks[path]
        mark.classes(remove="invisible") if changed else mark.classes(add="invisible")
        reset.classes(remove="invisible") if changed else reset.classes(add="invisible")
        self.rows[path].set_visibility(changed or not self.modified_only)

    def on_modified(self, event: events.ValueChangeEventArguments[Any]) -> None:
        self.modified_only = bool(event.value)
        changed = self.changed()
        for path in self.rows:
            self.mark(path, path in changed)

    def write(self, path: str, value: Any) -> None:  # noqa: ANN401 - a field's value
        if self.model is None or not self.writing:
            return
        control = self.controls[path]
        if value is None and _value_of(self.body(), path) is None:
            return
        try:
            self.model.project.set_value(self.model.kind, self.model.name, path, value)
        except ValueError as error:
            # Refused at its field: the rule, the value entered and the case path.
            said = str(error).replace(f"{self.model.project.root}/", "")
            if isinstance(control, ValidationElement):
                control.error = said
            else:
                ui.notify(said, type="negative")
            return
        if isinstance(control, ValidationElement):
            control.error = None
        self.after_write(path)

    def write_material(self, path: str, material: str, value: object) -> None:
        """Write one material's number of a ``materials`` field; a blank removes it."""
        held = _value_of(self.body(), path)
        mapping = dict(held) if isinstance(held, dict) else {}
        if isinstance(value, int | float):
            mapping[material] = float(value)
        else:
            mapping.pop(material, None)
        self.write(path, mapping or None)

    def reset(self, path: str) -> None:
        if self.model is None:
            return
        try:
            self.model.project.set_value(self.model.kind, self.model.name, path, None)
        except ValueError as error:
            ui.notify(str(error), type="negative")
            return
        control = self.controls[path]
        self.writing = False
        try:
            default = _default_of(path)
            if isinstance(control, ui.input):
                control.value = "" if default is None else str(default)
            elif isinstance(control, ui.switch | ui.checkbox):
                control.value = bool(default)
            elif isinstance(control, ui.number | ui.select):
                control.value = default
            if isinstance(control, ValidationElement):
                control.error = None
        finally:
            self.writing = True
        self.after_write(path)

    def after_write(self, path: str) -> None:
        if path in self.marks:
            self.mark(path, path in self.changed())
        # A value's change answers the last refusal; the next build says whether it holds.
        if self.model is not None:
            self.model.dismiss()
        self.built.changes_moved()
        self.shown_state = ""
        self.refresh()

    def expose(self, path: str, on: bool) -> None:
        if self.model is None:
            return
        try:
            self.model.project.set_exposed(self.model.kind, self.model.name, path, on)
        except ValueError as error:
            ui.notify(str(error), type="negative")

    def measure(self, value: object, unit: str) -> str:
        return f"{self.text(value, '')}°" if unit == "deg" else self.text(value, unit)

    def gate_text(self, gate: dict[str, Any]) -> str:
        measured = next((v for k, v in gate.items() if k.startswith("measured")), None)
        limit = next((v for k, v in gate.items() if k.startswith(("limit", "budget"))), None)
        unit = "deg" if any(key.endswith("_deg") for key in gate) else "nm"
        return f"{self.measure(measured, unit)} of {self.measure(limit, unit)} allowed"

    def show_readout(self) -> None:
        self.readout_box.clear()
        rows = self.readout()
        with self.readout_box:
            if not rows:
                return
            heading("Built", 2)
            with ui.element("dl").classes("readout-list"):
                for name, value, opens in rows:
                    TextElement(tag="dt", text=name)
                    with ui.element("dd"):
                        if opens is None:
                            ui.label(value)
                        else:
                            ui.button(value, on_click=opens).props(
                                f'flat dense no-caps aria-label="{name}: {value}"'
                            )

    def refresh(self) -> None:
        with self.keyed_once():
            self.refresh_pane()

    def refresh_pane(self) -> None:
        model = self.model
        states = model.states() if model is not None and self.usable() else {}
        problem = None if model is None else model.problem()
        refusal = None if model is None else model.refusal()
        running = None if model is None else model.running_stage()
        signature = json.dumps(
            [states, problem, refusal, running, self.signature(), sorted(self.dismissed)]
        )
        if signature == self.shown_state:
            return
        self.shown_state = signature
        self.show_status()
        self.show_actions(running is not None, problem is None and bool(states))
        self.show_cards(problem, refusal)
        covering = self.covering(running)
        for tool_id, (link, glyph, word, bar) in self.tool_links.items():
            stage = BUILDS[tool_id][0]
            state = states.get(stage) if stage else None
            title = next(tool.title for tool in self.suite.tools if tool.id == tool_id)
            look = STATES[state][2] if state else ""
            glyph.text = STATES[state][0] if state else ""
            glyph.classes(replace=f"tool-glyph {look}")
            word.text = STATES[state][1] if state else ""
            if (reason := self.unbuilt(tool_id)) is not None:
                glyph.text, word.text = "\N{EN DASH}", reason
                glyph.classes(replace="tool-glyph state-none")
            elif problem is not None and stage is not None:
                # A file that forms no case blocks every stage the suite builds.
                look = STATES["refused"][2]
                glyph.text, word.text = STATES["refused"][0], "blocked: the file forms no case"
                glyph.classes(replace=f"tool-glyph {look}")
            word.classes(replace=f"tool-word {look}")
            bar.set_visibility(stage is not None and stage == covering)
            if stage is not None and stage == covering:
                bar.props(f'aria-label="{STAGE_RUNNING.get(running or "", running)}"')
            named = f"{title}{', ' + word.text if word.text else ''}"
            link.props(f'data-state={state or "none"} aria-label="{named}" title="{named}"')
        self.show_readout()
        self.after_refresh()
        self.built.queue_moved()
        self.built.problems_moved()

    def show_status(self) -> None:
        """Say why nothing can be built here; the tool list carries each stage's state."""
        self.status.clear()
        with self.status:
            if self.model is None:
                ui.label(self.subject())
                return
            if self.model.problem() is not None:
                ui.label("Nothing can be built until the model's file forms a case.")
                return
            self.own_status()

    def show_actions(self, building: bool, ready: bool) -> None:
        self.actions.clear()
        model = self.model
        running = None if model is None else model.running_stage()
        with self.actions:
            self.own_actions(ready, building)
            if self.stage is None:
                return
            text = STAGE_RUNNING.get(running or "", self.build_title) if building else None
            held = self.build_held()
            build = ui.button(text or self.build_title, on_click=self.on_build).props(
                "unelevated dense no-caps color=primary data-control=tool-build"
            )
            build.set_enabled(ready and not building and held is None)
            if held is not None:
                build.props(f'title="{held}"')
            if building:
                ui.button("Cancel", on_click=self.on_cancel).props(
                    "outline dense no-caps data-control=tool-cancel"
                ).classes("tool-cancel")

    def show_cards(self, problem: str | None, refusal: tuple[str, str] | None) -> None:
        self.cards.clear()
        for path, control in self.controls.items():
            if isinstance(control, ValidationElement) and path == self.flagged:
                control.error = None
        self.flagged = None
        with self.cards:
            if problem is not None and self.model is not None:
                named = self.model.refused_path(problem)
                self.card("err", "The model's file forms no case", problem, named)
            if refusal is not None and self.model is not None:
                named = self.model.refused_path(refusal[1])
                check = f"the {FIELDS[named].label.lower()} check" if named in FIELDS else "a check"
                title = f"{STAGE_TITLES.get(refusal[0], refusal[0])} blocked by {check}"
                self.card("err", title, refusal[1], named)
            for key, text in self.warnings():
                self.card("warn", "Warning", text, None, dismiss=key)
            self.own_cards()

    def card(
        self, kind: str, title: str, text: str, path: str | None, *, dismiss: str | None = None
    ) -> None:
        glyph = "✕" if kind == "err" else "●"
        short = text
        if len(text) > CARD_SHORT:
            head = text[:CARD_SHORT]
            cut = max(head.rfind(". "), head.rfind("; "), head.rfind(", "), head.rfind(" "))
            short = head[:cut].rstrip(",;.")
        whole = short == text
        with (
            ui.element("div")
            .classes(f"note-card note-{kind}")
            .props(f"role={'alert' if kind == 'err' else 'status'} data-control=tool-{kind}")
        ):
            with ui.row().classes("items-center no-wrap note-head"):
                ui.label(glyph).props("aria-hidden=true")
                ui.label(title).classes("note-title")
            ui.label(text if whole else f"{short}…").classes("note-short")
            if not whole:
                with (
                    ui.expansion("The whole message")
                    .props("dense dense-toggle")
                    .classes("note-more")
                ):
                    ui.label(text)
            with ui.row().classes("items-center"):
                if path in self.controls:
                    self.flag(path, text)
                    ui.button(
                        f"Go to {FIELDS[path].label}", on_click=lambda _, p=path: self.go_to(p)
                    ).props("outline dense no-caps data-control=note-field")
                elif path in FIELDS and (tool := tool_for(self.suite.id, path)) is not None:
                    ui.button(
                        f"Go to {FIELDS[path].label}, in {tool.title}",
                        on_click=lambda _, t=tool, p=path: ui.navigate.to(
                            f"/{self.kind}/{t.id}?field={p}"
                        ),
                    ).props("outline dense no-caps data-control=note-field")
                if dismiss is not None:
                    ui.button("Dismiss", on_click=lambda _, k=dismiss: self.dismiss(k)).props(
                        "flat dense no-caps"
                    )

    def flag(self, path: str, text: str) -> None:
        control = self.controls[path]
        if isinstance(control, ValidationElement):
            control.error = "See the message above."
            self.flagged = path

    async def go_to(self, path: str) -> None:
        name = field_control(path)
        await ui.run_javascript(
            f"(() => {{ const e = document.querySelector('[data-control={name}]');"
            "const i = e?.matches('input') ? e : e?.querySelector('input');"
            "(i || e)?.focus(); (i || e)?.scrollIntoView({block: 'center'}); })()",
            timeout=10,
        )

    def dismiss(self, key: str) -> None:
        self.dismissed.add(key)
        self.refresh()

    async def on_build(self) -> None:
        model = self.model
        if model is None or self.stage is None or model.building:
            return
        try:
            model.build(self.stage)
        except ValueError as error:
            ui.notify(str(error), type="negative", multi_line=True)
        self.was_building = model.building
        # The view first: the refresh rebuilds the box that holds the button that asked.
        if model.running_stage() is not None:
            await self.building_shown()
        self.refresh()

    async def building_shown(self) -> None:
        """Show in the view that a build has started, where the view says so."""

    def on_cancel(self) -> None:
        if self.model is not None:
            self.model.cancel()
        self.refresh()

    async def tick(self) -> None:
        model = self.model
        if model is None:
            return
        building = model.building
        if building or self.was_building:
            self.refresh()
        if self.was_building and not building:
            self.was_building = False
            await self.show()
        self.was_building = building

    async def start(self) -> None:
        await self.built.settled()
        await self.show()
        if self.focus in self.controls:
            await self.go_to(self.focus)


class _MolecularPane(_Pane[MolecularModel]):
    kind: ClassVar[str] = "molecular"

    def __init__(self, shell: Shell, tool: Tool, built: Views, focus: str) -> None:
        super().__init__(shell, tool, built, focus, current_model(shell))
        # A model read from a PQR file may hold no chain to draw as a cartoon: its atoms show.
        atoms = self.model is not None and not self.model.has_structure()
        self.look: dict[str, Any] = {
            "representation": "spacefill" if atoms else "cartoon",
            "colour": self.colouring,
            "frame": 0,
            "overlay": False,
            "clip": False,
        }
        # What Prepare holds between a visit and a save, kept for the window: no case value does.
        self.prepare = _draft(self.model)
        # Edits made on a model that is no variant and holds none, until they are saved as one.
        self.staged: list[dict[str, Any]] = []
        self.edits_box: ui.column
        self.bar_box: ui.element
        self.picked: ui.select | None = None

    def usable(self) -> bool:
        return self.model is not None and self.model.has_structure()

    def idle(self) -> bool:
        # A model that reads a PQR has no structure for these values to act on, and a linked
        # variant reads them from its parent.
        return not self.usable() or self.linked_to is not None

    def before_fields(self) -> None:
        self.linked_to = self.parent()
        if self.linked_to is not None and self.tool.id in LINKED_NOTE:
            ui.label(
                f"A linked variant of {self.linked_to}: these values are its parent's. "
                "Change them there, or edit this variant's residues in Charge edit."
            ).classes("later").props("data-control=tool-linked")
        if self.tool.id == "prepare":
            self.open_button()

    def listen(self) -> None:
        self.built.listen("mol_pick", self.on_pick)

    def signature(self) -> object:
        return len(self.staged)

    def own_status(self) -> None:
        if self.model is not None and not self.model.has_structure():
            ui.label(
                "This model reads its atoms and charges from a PQR file, so it has no "
                "structure to prepare, align or protonate."
            )

    def own_actions(self, ready: bool, building: bool) -> None:
        if self.tool.id == "prepare":
            ui.button("Save prepared structure", on_click=self.save_prepared).props(
                "outline dense no-caps data-control=prepare-save"
            ).set_enabled(ready and not building)
        if self.tool.id == "edit" and not self.in_place():
            ui.button("Save as variant…", on_click=self.save_variant).props(
                "outline dense no-caps data-control=variant-open"
            ).set_enabled(ready and bool(self.staged))

    def own_cards(self) -> None:
        if self.tool.id == "view" and self.model is not None and self.usable():
            missing = [
                STAGE_TITLES[stage]
                for stage, state in self.model.states().items()
                if state != "built"
            ]
            if missing:
                ui.label(
                    f"Not built: {', '.join(missing)}. Build it in its tool; the view shows "
                    "what is built, else the structure file."
                ).classes("later")

    def after_refresh(self) -> None:
        if hasattr(self, "bar_box"):
            self.bar_box.set_visibility(self.charged())

    async def start(self) -> None:
        await super().start()
        await self.offer_chains()

    def parent(self) -> str | None:
        """Return the model a linked variant reads its values from, or None for any other."""
        if self.model is None:
            return None
        try:
            location = self.model.project.path("molecular", self.model.name)
            held = read_model_file("molecular", location).variant_of
        except (ValueError, OSError):
            return None
        return Path(held.model).stem if held is not None and held.linked else None

    def variant(self) -> bool:
        if self.model is None:
            return False
        try:
            location = self.model.project.path("molecular", self.model.name)
            return read_model_file("molecular", location).variant_of is not None
        except (ValueError, OSError):
            return False

    def open_button(self) -> None:
        opened = ui.button("Open structure…", on_click=self.open_structure).props(
            "outline dense no-caps data-control=open-structure"
        )
        if self.model is None:
            opened.disable()

    def inputs(self) -> list[str]:
        if self.project is None:
            return []
        folder = self.project.root / INPUTS_FOLDER
        if not folder.is_dir():
            return []
        return sorted(
            entry.name
            for entry in folder.iterdir()
            if entry.is_file() and entry.name.lower().endswith(STRUCTURE_SUFFIXES)
        )

    def open_structure(self) -> None:
        with ui.dialog() as dialog, ui.card().classes("dialog"):
            heading("Open structure", 2)
            names = self.inputs()
            if names:
                ui.label("In the project's inputs:").classes("field-label")
                with ui.column().classes("w-full gap-0").props("data-control=input-files"):
                    for name in names:
                        ui.button(name, on_click=lambda _, n=name: self.use_input(dialog, n)).props(
                            "flat dense no-caps align=left"
                        ).classes("list-row w-full")
            with ui.row().classes("w-full items-center no-wrap"):
                path = (
                    ui.input("A PDB or mmCIF file on this computer")
                    .props(
                        'dense outlined data-control=structure-path placeholder="/path/to/pore.pdb"'
                    )
                    .classes("col")
                )
                # The system's own file picker; the file it gives is uploaded, not named.
                picker = (
                    ui.upload(
                        auto_upload=True,
                        max_files=1,
                        on_upload=lambda e: self.add_upload(dialog, path, e),
                    )
                    .props(f'accept="{",".join(STRUCTURE_SUFFIXES)}"')
                    .classes("hidden")
                )
                ui.button("Browse…", on_click=lambda: picker.run_method("pickFiles")).props(
                    "outline dense no-caps data-control=structure-browse"
                )
            ui.label("The file is copied into the project's inputs.").classes("later")
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=dialog.close).props("flat no-caps")
                ui.button("Add and use", on_click=lambda: self.add_input(dialog, path)).props(
                    "unelevated no-caps color=primary"
                )
        dialog.open()

    def add_input(self, dialog: ui.dialog, path: ui.input) -> None:
        if self.project is None or not str(path.value or "").strip():
            path.error = "Give the file's path."
            return
        try:
            copied = self.project.add_input(str(path.value).strip())
        except ValueError as error:
            path.error = str(error)
            return
        self.use_input(dialog, copied.name)

    async def add_upload(
        self, dialog: ui.dialog, path: ui.input, event: events.UploadEventArguments
    ) -> None:
        """Copy a file the system's picker gave into the project's inputs, and use it."""
        if self.project is None:
            return
        name = Path(event.file.name).name
        with tempfile.TemporaryDirectory(prefix="nanopnp-upload-") as folder:
            held = Path(folder) / name
            await event.file.save(held)
            try:
                copied = self.project.add_input(held)
            except ValueError as error:
                path.error = str(error).replace(f"{folder}/", "")
                return
        self.use_input(dialog, copied.name)

    def use_input(self, dialog: ui.dialog, name: str) -> None:
        dialog.close()
        if self.project is not None:
            held = self.project.root / INPUTS_FOLDER / name
            self.set_source(self.project.input_path("molecular", held))

    def set_source(self, value: str) -> None:
        path = "structure.source.path"
        self.write(path, value)
        control = self.controls.get(path)
        if isinstance(control, ui.input):
            self.writing = False
            try:
                control.value = value
            finally:
                self.writing = True

    def source(self) -> Path | None:
        case = None if self.model is None else self.model.case()
        if case is None or case.structure is None:
            return None
        return Path(case.structure.source.path)

    def record(self) -> PreparationRecord | None:
        source = self.source()
        if source is None:
            return None
        beside = source.with_suffix(".prepare.json")
        try:
            return PreparationRecord.model_validate_json(beside.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def raw_source(self) -> Path | None:
        """Return the file a preparation reads: the one a prepared file was made from, else it."""
        source, record = self.source(), self.record()
        if source is None or record is None:
            return source
        original = source.with_name(record.source.name)
        return original if original.is_file() else source

    def prepare_section(self) -> None:
        record = self.record()
        if record is not None and not self.prepare["typed"]:
            tilt, azimuth = _angles_of(record.axis)
            self.prepare.update(
                tilt=tilt if record.method == "typed" else None,
                azimuth=azimuth if record.method == "typed" else None,
                cis_end=record.cis_end,
                registration=(
                    ""
                    if record.registration_residues is None
                    else f"{record.registration_residues[0]}:{record.registration_residues[1]}"
                ),
                centre=record.centroid_z_nm,
            )
        membrane, study = (Membrane(), None) if self.model is None else self.model.membrane()
        if record is None and not self.prepare["typed"]:
            self.prepare["centre"] = membrane.centre_z_nm
        usable = self.usable()
        heading("Orientation", 2)
        ui.label(
            "Left empty, the axis is estimated when the structure is saved."
            if record is None
            else f"Prepared from {record.source.name}, its axis {record.method}."
        ).classes("later")
        with self.named("Tilt"):
            self.tilt = ui.number(
                value=self.prepare["tilt"],
                suffix="°",
                min=0,
                max=90,
                step=0.5,
                on_change=lambda e: self.prepare.update(tilt=e.value, typed=True),
            ).props('dense outlined data-control=prepare-tilt aria-label="Tilt, in degrees"')
            self.tilt.set_enabled(usable)
        with self.named("Azimuth"):
            self.azimuth = ui.number(
                value=self.prepare["azimuth"],
                suffix="°",
                min=-180,
                max=180,
                step=1,
                on_change=lambda e: self.prepare.update(azimuth=e.value, typed=True),
            ).props('dense outlined data-control=prepare-azimuth aria-label="Azimuth, in degrees"')
            self.azimuth.set_enabled(usable)
        with ui.row().classes("items-center no-wrap"):
            ui.button("Estimate", on_click=self.estimate).props(
                "outline dense no-caps data-control=prepare-estimate"
            ).set_enabled(usable)
            ui.button("Flip", on_click=self.flip).props(
                "outline dense no-caps data-control=prepare-flip"
            ).set_enabled(usable)
            self.cis = ui.label(self.cis_text()).props("data-control=prepare-cis")
        heading("Membrane", 2)
        with self.named("Registration"):
            ui.input(
                value=self.prepare["registration"],
                placeholder="first:last, as 164:186",
                on_change=lambda e: self.prepare.update(registration=e.value or "", typed=True),
            ).props(
                "dense outlined data-control=prepare-registration "
                'aria-label="Registration residues, first and last"'
            ).set_enabled(usable)
        with self.named("Centre, z"):
            ui.number(
                value=self.prepare["centre"],
                suffix="nm",
                step=0.1,
                on_change=lambda e: self.prepare.update(centre=e.value or 0.0, typed=True),
            ).props(
                'dense outlined data-control=prepare-centre aria-label="Centre, z, in nm"'
            ).set_enabled(usable)
        ui.label(
            "The registration residues' centre, or every C-alpha's without them, is placed on "
            "the axis at this height."
        ).classes("later")
        shape = (
            f"centred at {self.text(membrane.centre_z_nm, 'nm')}, "
            f"{self.text(membrane.thickness_nm, 'nm')} thick"
        )
        ui.label(
            f"The leaflets drawn are study {study}'s membrane, {shape}, set in its continuum model."
            if study is not None
            else f"No study names this model yet: the leaflets drawn are the default membrane, "
            f"{shape}."
        ).classes("later").props("data-control=prepare-membrane")

    def cis_text(self) -> str:
        return f"cis (+z): the {self.prepare['cis_end']} end"

    def flip(self) -> None:
        self.prepare["cis_end"] = "narrower" if self.prepare["cis_end"] == "wider" else "wider"
        self.prepare["typed"] = True
        self.cis.text = self.cis_text()

    def choices(self, *, typed: bool) -> dict[str, Any]:
        case = None if self.model is None else self.model.case()
        chains = "all"
        if case is not None and case.structure is not None:
            chains = str(case.structure.source.chains).replace("+", ",")
        tilt, azimuth = self.prepare["tilt"], self.prepare["azimuth"]
        axis = None
        if typed and tilt is not None:
            axis = _axis_of(float(tilt), float(azimuth or 0.0))
        return {
            "chains": chains,
            "cis_end": self.prepare["cis_end"],
            "registration_residues": _registration(str(self.prepare["registration"])),
            "centroid_z_nm": float(self.prepare["centre"] or 0.0),
            "axis": axis,
        }

    async def estimate(self) -> None:
        source = self.raw_source()
        if source is None or self.busy:
            return
        self.busy = True
        notice = ui.notification("Estimating the axis…", spinner=True, timeout=None)
        try:
            chosen = self.choices(typed=False)
            with tempfile.TemporaryDirectory(prefix="nanopnp-estimate-") as folder:
                out = Path(folder) / "estimate.pdb"
                await run.io_bound(lambda: orient_pore(source, out=out, **chosen))
                record = PreparationRecord.model_validate_json(
                    out.with_suffix(".prepare.json").read_text(encoding="utf-8")
                )
        except (ValueError, OSError) as error:
            ui.notify(str(error), type="negative", multi_line=True)
            return
        finally:
            notice.dismiss()
            self.busy = False
        tilt, azimuth = _angles_of(record.axis)
        self.tilt.value, self.azimuth.value = tilt, azimuth
        ui.notify(f"Axis estimated by the {record.method}: {tilt:g}° from the file's z.")

    async def save_prepared(self) -> None:
        model, source = self.model, self.raw_source()
        if model is None or source is None or self.busy:
            return
        self.busy = True
        notice = ui.notification("Preparing the structure…", spinner=True, timeout=None)
        try:
            chosen = self.choices(typed=True)
            folder = model.project.root / INPUTS_FOLDER
            written = await run.io_bound(lambda: prepared_pore(source, directory=folder, **chosen))
            if written is None:
                return
        except (ValueError, OSError) as error:
            ui.notify(str(error), type="negative", multi_line=True)
            return
        finally:
            notice.dismiss()
            self.busy = False
        self.prepare["typed"] = False
        self.set_source(model.project.input_path("molecular", written))
        ui.notify(f"Saved {INPUTS_FOLDER}/{written.name}; building the ensemble.")
        await self.on_build()

    def ensemble_section(self) -> None:
        heading("Frames shown", 2)
        count = 1 if self.model is None else frame_count(self.model)
        self.frame_label = ui.label(f"Frame 1 of {count}").classes("later")
        self.frame_slider = ui.slider(
            min=1,
            max=max(count, 2),
            value=1,
            on_change=lambda e: self.restyle("frame", int(e.value) - 1),
        ).props('label snap aria-label="Frame shown" data-control=ensemble-frame')
        self.frame_slider.set_enabled(count > 1)
        ui.checkbox(
            f"Overlay the frames (the first {OVERLAY_MOST})",
            on_change=lambda e: self.restyle("overlay", bool(e.value)),
        ).props("dense data-control=ensemble-overlay").set_enabled(count > 1)

    def protonation_section(self) -> None:
        self.find_residue()
        self.colour_bar()

    def find_residue(self) -> None:
        listed = dict(residues(self.model)) if self.model is not None else {}
        with self.named("Find a residue"):
            self.picked = ui.select(
                listed,
                with_input=True,
                clearable=True,
                on_change=lambda e: self.select(e.value),
            ).props(
                'dense outlined options-dense data-control=find-residue aria-label="Find a residue"'
            )
        self.picked.set_enabled(bool(listed))

    async def select(self, key: object) -> None:
        if key:
            await ui.run_javascript(f"nano.show({json.dumps(str(key))})", timeout=10)

    def on_pick(self, event: events.GenericEventArguments) -> None:
        key = str(event.args.get("key", ""))
        if self.picked is not None and key in self.picked.options:
            self.picked.value = key
        if self.tool.id == "edit" and key:
            self.on_pick_edit(key)

    def show_states(self) -> None:
        if self.model is None:
            return
        rows = titration_states(self.model)
        for row in rows:
            row["state"] = "● left unapplied" if row["unapplied"] else "applied"
        with ui.dialog() as dialog, ui.card().classes("dialog dialog-wide"):
            heading("Titratable groups, first frame", 2)
            search = ui.input(placeholder="Filter, as GLU or unapplied").props(
                "dense outlined clearable"
            )
            table = ui.table(columns=STATES_COLUMNS, rows=rows, row_key="id", pagination=15).props(
                "dense flat data-control=states-table"
            )
            table.bind_filter_from(search, "value")
            table.on("row-click", lambda e: self.select(e.args[1]["key"]))
            ui.label("A row selects its residue in the 3D view.").classes("later")
            with ui.row().classes("w-full justify-end"):
                ui.button("Close", on_click=dialog.close).props("flat no-caps")
        dialog.open()

    def show_listed(self, title: str, lines: list[str], keys: list[str] | None = None) -> None:
        with ui.dialog() as dialog, ui.card().classes("dialog dialog-wide"):
            heading(title, 2)
            with ui.column().classes("listed gap-0").props("data-control=listed"):
                for index, line in enumerate(lines or ["None."]):
                    if keys is None or index >= len(keys):
                        ui.label(line)
                        continue
                    ui.button(line, on_click=lambda _, k=keys[index]: self.select(k)).props(
                        "flat dense no-caps align=left"
                    ).classes("list-row w-full")
            if keys:
                ui.label("A row selects its residue in the 3D view.").classes("later")
            with ui.row().classes("w-full justify-end"):
                ui.button("Close", on_click=dialog.close).props("flat no-caps")
        dialog.open()

    def edits(self) -> list[dict[str, Any]]:
        held = _value_of(self.body(), "charge.edits")
        if not isinstance(held, list):
            case = None if self.model is None else self.model.case()
            if case is None or case.charge is None:
                return []
            held = [edit.model_dump(exclude_none=True) for edit in case.charge.edits]
        return [dict(entry) for entry in held] + self.staged

    def in_place(self) -> bool:
        """Say whether an edit is written to the model itself: a variant, or one holding edits."""
        return self.variant() or bool(_value_of(self.body(), "charge.edits"))

    def edit_section(self) -> None:
        usable = self.usable()
        names: dict[str, str] = {}
        if self.model is not None:
            for key, label in residues(self.model):
                # An edit names the parent residue; a protonated table names its state (HSD).
                resname, _, number = label.split(",")[0].partition(" ")
                names.setdefault(f"{parent_residue(resname)} {number}", key)
        self.residue_keys = names
        heading("Edit a residue", 2)
        ui.label("An edit acts on the residue in every chain and frame.").classes("later")
        with self.named("Residue"):
            self.edit_residue = ui.select(
                list(names),
                with_input=True,
                on_change=lambda e: self.select(names.get(str(e.value))),
            ).props('dense outlined options-dense data-control=edit-residue aria-label="Residue"')
        self.edit_residue.set_enabled(usable and bool(names))
        with self.named("Edit"):
            self.edit_kind = ui.select(EDIT_KINDS, value="state", on_change=self.on_kind).props(
                'dense outlined options-dense data-control=edit-kind aria-label="Edit"'
            )
        self.edit_kind.set_enabled(usable)
        with self.named("State") as (self.state_row, _):
            self.edit_state = ui.select(list(EDIT_STATES)).props(
                'dense outlined options-dense data-control=edit-state aria-label="State"'
            )
        self.edit_state.set_enabled(usable)
        with self.named(EDIT_KINDS["charge_change_e"]) as (self.number_row, self.number_name):
            self.edit_number = ui.number(suffix="e", step=1).props(
                "dense outlined data-control=edit-number "
                f'aria-label="{EDIT_KINDS["charge_change_e"]}"'
            )
        self.number_row.set_visibility(False)
        ui.button("Add edit", on_click=self.add_edit).props(
            "outline dense no-caps data-control=edit-add"
        ).set_enabled(usable)
        heading("Edits", 2)
        self.edits_box = ui.column().classes("w-full gap-0").props("data-control=edit-list")
        self.show_edits()

    def on_kind(self, event: events.ValueChangeEventArguments[Any]) -> None:
        kind = str(event.value)
        self.state_row.set_visibility(kind == "state")
        self.number_row.set_visibility(kind != "state")
        self.number_name.text = EDIT_KINDS[kind]
        self.edit_number.props(f'aria-label="{EDIT_KINDS[kind]}"')
        self.edit_number.props(f"suffix={'e' if kind == 'charge_change_e' else 'times'}")
        self.edit_number.props(f"step={1 if kind == 'charge_change_e' else 0.05}")

    def on_pick_edit(self, key: str) -> None:
        for label, held in self.residue_keys.items():
            if held.split(":")[1] == key.split(":")[1]:
                self.edit_residue.value = label
                return

    def add_edit(self) -> None:
        residue, kind = self.edit_residue.value, str(self.edit_kind.value)
        if not residue:
            ui.notify("Choose a residue first, in the list or in the 3D view.", type="warning")
            return
        value: object = self.edit_state.value if kind == "state" else self.edit_number.value
        if value is None or value == "":
            ui.notify(f"Give the {EDIT_KINDS[kind].lower()}.", type="warning")
            return
        if kind == "charge_change_e":
            change = float(str(value))
            if not change.is_integer():
                ui.notify("A charge change is a whole number of e.", type="warning")
                return
            value = int(change)
        self.put_edits([*self.edits(), {"residue": str(residue), kind: value}])

    def remove_edit(self, index: int) -> None:
        held = self.edits()
        del held[index]
        self.put_edits(held)

    def put_edits(self, edits: list[dict[str, Any]]) -> None:
        model = self.model
        if model is None:
            return
        if self.in_place():
            try:
                model.project.set_value("molecular", model.name, "charge.edits", edits or None)
            except ValueError as error:
                ui.notify(
                    str(error).replace(f"{model.project.root}/", ""),
                    type="negative",
                    multi_line=True,
                )
                return
            self.after_write("charge.edits")
            control = self.controls.get("charge.edits")
            if isinstance(control, ui.label):
                control.text = f"{len(edits)} edit{'' if len(edits) == 1 else 's'}"
        else:
            self.staged = edits
            self.shown_state = ""
            self.refresh()
        self.show_edits()

    def show_edits(self) -> None:
        self.edits_box.clear()
        held = self.edits()
        with self.edits_box:
            if not held:
                ui.label("None.").classes("later")
            for index, entry in enumerate(held):
                with ui.row().classes("items-center no-wrap w-full edit-row"):
                    ui.label(_edit_text(entry)).classes("col")
                    ui.button(
                        icon="sym_o_close", on_click=lambda _, i=index: self.remove_edit(i)
                    ).props(f'flat dense aria-label="Remove the edit of {entry.get("residue")}"')
            if self.staged:
                ui.label("Not saved yet: save them as a variant.").classes("state-warn")

    def save_variant(self) -> None:
        model = self.model
        if model is None:
            return
        if not self.staged:
            ui.notify("Add an edit first; a variant holds its parent's values and its edits.")
            return
        with ui.dialog() as dialog, ui.card().classes("dialog"):
            heading("Save as variant", 2)
            name = ui.input("Name", value=f"{model.name}-variant").props(
                "dense outlined data-control=variant-name"
            )
            kind = ui.radio(
                {
                    "linked": "Linked: follows its parent's values",
                    "copy": "Full copy: holds every value itself",
                },
                value="linked",
            ).props("dense data-control=variant-kind")
            with ui.row().classes("w-full justify-end"):
                ui.button("Cancel", on_click=dialog.close).props("flat no-caps")
                ui.button(
                    "Save", on_click=lambda: self.write_variant(dialog, name, kind.value == "copy")
                ).props("unelevated no-caps color=primary data-control=variant-save")
        dialog.open()

    def write_variant(self, dialog: ui.dialog, name: ui.input, copy: bool) -> None:
        model = self.model
        if model is None:
            return
        chosen = str(name.value or "").strip()
        try:
            model.project.save_variant(model.name, chosen, self.staged, copy=copy)
            model.project.open_item(f"molecular/{chosen}")
        except ValueError as error:
            name.error = str(error).replace(f"{model.project.root}/", "")
            return
        dialog.close()
        # The frame is built again around the variant, now the open item.
        ui.run_javascript("window.location.assign('/molecular/edit')")

    def view_section(self) -> None:
        # A model read from a PQR file has atoms and charges to draw, though no structure.
        usable = self.usable() or (self.model is not None and self.model.pqr() is not None)
        with self.named("Representation"):
            ui.select(
                dict(REPRESENTATIONS),
                value=self.look["representation"],
                on_change=lambda e: self.restyle("representation", str(e.value)),
            ).props(
                "dense outlined options-dense data-control=view-representation "
                'aria-label="Representation"'
            ).set_enabled(usable)
        with self.named("Colour by"):
            ui.select(
                dict(COLOURINGS),
                value=self.look["colour"],
                on_change=lambda e: self.restyle("colour", str(e.value)),
            ).props(
                'dense outlined options-dense data-control=view-colour aria-label="Colour by"'
            ).set_enabled(usable)
        background = SETTINGS["viewer_background"]
        with self.named("Background"):
            ui.select(
                dict(background.choices or {}),
                value=self.shell.settings.value("viewer_background"),
                on_change=lambda e: self.set_background(str(e.value)),
            ).props(
                "dense outlined options-dense data-control=view-background "
                f'aria-label="{background.title}"'
            )
        ui.checkbox(
            "Cut away the front half", on_change=lambda e: self.restyle("clip", bool(e.value))
        ).props("dense data-control=view-clip").set_enabled(usable)
        self.find_residue()
        self.colour_bar()

    def set_background(self, value: str) -> None:
        self.shell.settings = self.shell.settings.with_user("viewer_background", value)
        settings.save(self.shell.settings)
        self.built.applied()

    def charged(self) -> bool:
        if self.look["colour"] != "charge" or self.model is None:
            return False
        return "protonation" in self.model.artefacts() or self.model.pqr() is not None

    def colour_bar(self) -> None:
        low, high = ("red", "blue") if charge_colours(self.shell) == "blue" else ("blue", "red")
        with ui.column().classes("w-full gap-0") as self.bar_box:
            ui.label("Residue charge").classes("field-label")
            with (
                ui.element("div")
                .classes("colour-bar")
                .props(
                    'role="img" aria-label="Residue charge, from minus one e in '
                    f'{low} to plus one e in {high}"'
                )
            ):
                ui.label("\N{LESS-THAN OR EQUAL TO} \N{MINUS SIGN}1 e")
                with ui.element("span").classes("colour-bar-plate"):
                    ui.element("span").classes(f"colour-bar-scale positive-{high}").props(
                        "data-colorbar"
                    )
                ui.label("\N{GREATER-THAN OR EQUAL TO} +1 e")
        self.bar_box.set_visibility(self.charged())

    def readout(self) -> list[tuple[str, str, Callable[[], None] | None]]:
        """Return the built stage's figures this tool shows: a name, a value, what opens it."""
        model = self.model
        if model is None:
            return []
        held = model.artefacts()
        structure = held["structure"].summary if "structure" in held else None
        table = held["protonation"].summary if "protonation" in held else None
        rows: list[tuple[str, str, Callable[[], None] | None]] = []
        if self.tool.id == "prepare" and structure is not None:
            axis = _mapping(structure.get("axis"))
            # A header written before the channel's axis names no method: a permutation's.
            rows.append(("Axis found by", str(axis.get("method", "permutation")), None))
            for name, gate in _mapping(structure.get("gates")).items():
                if name == "straightness":
                    # The straightness limit warns and does not refuse (§5.2's NOTE on stage 1).
                    held = _mapping(gate)
                    rows.append(
                        (
                            "Straightness",
                            f"{self.measure(held.get('measured_nm'), 'nm')}, warned above "
                            f"{self.measure(held.get('limit_nm'), 'nm')}",
                            None,
                        )
                    )
                    continue
                rows.append((f"Gate, {name}", self.gate_text(_mapping(gate)), None))
            check = _mapping(structure.get("frame_check"))
            if check:
                rows.append(
                    ("Aligned frame, tilt", self.measure(check.get("tilt_deg"), "deg"), None)
                )
        elif self.tool.id == "ensemble" and structure is not None:
            frames = _mapping(structure.get("frames"))
            used = frames.get("indices")
            rows.append(("Frames used", str(len(used) if isinstance(used, list) else "?"), None))
            rows.append(("Frames available", str(frames.get("available", "?")), None))
            rows.append(("Atoms", str(structure.get("atoms", "?")), None))
            rows.append(
                ("Chains, in ring order", _joined(structure.get("chains_cyclic_order")), None)
            )
            drift = structure.get("drift_deg")
            if isinstance(drift, list) and drift:
                rows.append(("Largest axis drift", self.measure(max(drift), "deg"), None))
            if table is not None:
                rows.append(("Net charge per frame", _joined(table.get("q_net_e"), " e"), None))
        elif self.tool.id in {"protonation", "edit", "view"} and table is not None:
            rows.append(("Net charge per frame", _joined(table.get("q_net_e"), " e"), None))
            rows.append(("Residues", str(table.get("residues", "?")), None))
            groups = len(titration_states(model))
            rows.append(("Titratable groups", f"{groups} groups…", self.show_states))
            unapplied = table.get("unapplied")
            listed = unapplied if isinstance(unapplied, list) else []
            rows.append(
                (
                    "States left unapplied",
                    f"{len(listed)} states…" if listed else "0",
                    (
                        lambda: self.show_listed(
                            "States left unapplied", _unapplied(listed), _unapplied_keys(listed)
                        )
                    )
                    if listed
                    else None,
                )
            )
            warned = _warnings(table.get("warnings"))
            rows.append(
                (
                    "PDB2PQR and PROPKA warnings",
                    f"{len(warned)} warnings…" if warned else "0",
                    (lambda: self.show_listed("PDB2PQR and PROPKA warnings", warned))
                    if warned
                    else None,
                )
            )
        return rows

    def warnings(self) -> list[tuple[str, str]]:
        """Return the warnings the tool shows as a key and a text: its stage's, the membrane's."""
        if self.model is None or self.tool.id not in {"prepare", "ensemble"}:
            return []
        found = self.membrane_warning() if self.tool.id == "prepare" else []
        held = self.model.artefacts()
        listed = held["structure"].summary.get("warnings") if "structure" in held else None
        if isinstance(listed, list):
            found.extend((str(text), str(text)) for text in listed)
        return [(key, text) for key, text in found if key not in self.dismissed]

    def membrane_warning(self) -> list[tuple[str, str]]:
        """Warn where the prepared registration residues sit off the paired study's membrane."""
        record = self.record()
        if self.model is None or record is None or record.registration_residues is None:
            return []
        membrane, study = self.model.membrane()
        off = record.centroid_z_nm - membrane.centre_z_nm
        if abs(off) <= MEMBRANE_OFF_NM:
            return []
        whose = f"study {study}'s membrane" if study is not None else "the default membrane"
        centre = self.text(membrane.centre_z_nm, "nm")
        text = (
            f"The registration residues' centre is at z = {self.text(record.centroid_z_nm, 'nm')}"
            f" and {whose} is centred at {centre}, so the pore sits {self.text(abs(off), 'nm')} "
            f"off it. Set Centre, z to {centre} and save, or move the membrane in the continuum "
            "model."
        )
        return [(f"membrane-{record.centroid_z_nm}-{membrane.centre_z_nm}", text)]

    def scene_url(self) -> tuple[str | None, str]:
        model = self.model
        if model is None or model.case() is None:
            return None, ""
        if not model.has_structure() and model.pqr() is None:
            return None, ""
        held = model.artefacts()
        form = "table" if "protonation" in held else "ensemble" if "structure" in held else "file"
        side = int(self.tool.id == "prepare")
        url = (
            f"/api/molecular/{model.name}/scene?representation={self.look['representation']}"
            f"&colour={self.look['colour']}&frame={self.look['frame']}"
            f"&overlay={int(self.look['overlay'])}&side={side}&clip={int(self.look['clip'])}"
        )
        return url, f"{model.name}:{form}:{side}:{int(self.look['clip'])}"

    async def show(self) -> None:
        url, key = self.scene_url()
        await self.built.show_molecule(url, key)

    async def restyle(self, what: str, value: object) -> None:
        self.look[what] = value
        if what == "frame" and hasattr(self, "frame_label") and self.model is not None:
            self.frame_label.text = f"Frame {int(str(value)) + 1} of {frame_count(self.model)}"
        if hasattr(self, "bar_box"):
            self.bar_box.set_visibility(self.charged())
        await self.show()

    async def offer_chains(self) -> None:
        """Offer the structure file's chains in the Chains field, once the file is read."""
        control = self.controls.get("structure.source.chains")
        source = self.raw_source()
        if not isinstance(control, ui.select) or source is None or not source.is_file():
            return
        key = (source, source.stat().st_mtime_ns)
        if key not in _CHAINS:
            try:
                found = await run.io_bound(protein_chains, source)
            except (ValueError, OSError):
                return
            if found is None:
                return
            _CHAINS[key] = found
        chosen = list(control.value or [])
        self.writing = False
        try:
            control.set_options([*_CHAINS[key], *(c for c in chosen if c not in _CHAINS[key])])
            control.value = chosen
        finally:
            self.writing = True


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _joined(value: object, unit: str = "") -> str:
    if not isinstance(value, list):
        return "?"
    return ", ".join(f"{item}{unit}" for item in value).replace("-", "\N{MINUS SIGN}")


def _unapplied(listed: list[object]) -> list[str]:
    lines = []
    for entry in listed:
        row = _mapping(entry)
        lines.append(
            f"{row.get('residue', '?')}, chain {row.get('chain', '?')}: applied "
            f"{row.get('applied_e', '?')} e, PROPKA's state expects {row.get('expected_e', '?')} e"
            f" ({row.get('frames', '?')} frame{'' if row.get('frames') == 1 else 's'})"
        )
    return lines


def _unapplied_keys(listed: list[object]) -> list[str]:
    keys = []
    for entry in listed:
        row = _mapping(entry)
        number = str(row.get("residue", "")).split(" ")[-1]
        keys.append(f"{_chain_id(str(row.get('chain', '')))}:{number}")
    return keys


def _warnings(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(entry) for entry in value]
    if not isinstance(value, dict):
        return []
    lines = []
    for message, count in value.items():
        # A message kept as a tuple's text reads as its parts.
        said = " ".join(str(message).strip("()").replace("'", "").replace(",", "").split())
        times = f" ({count} times)" if isinstance(count, int) and count > 1 else ""
        lines.append(f"● {said}{times}")
    return lines


def _edit_text(entry: object) -> str:
    if not isinstance(entry, dict):
        return str(entry)
    rest = ", ".join(
        f"{EDIT_KINDS.get(str(key), str(key)).lower()} {value}"
        for key, value in entry.items()
        if key != "residue"
    )
    return f"{entry.get('residue', '?')}: {rest}"


def tool_page(shell: Shell, tool: Tool) -> Callable[..., None]:
    """Return the page of one Molecular tool, which the frame's sub-pages build."""

    def page(built: Views, field: str = "") -> None:
        shell.last_tool["molecular"] = tool.id
        _MolecularPane(shell, tool, built, field).build()

    return page
