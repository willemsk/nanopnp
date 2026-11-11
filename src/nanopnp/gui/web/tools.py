"""The Molecular suite's tool pages: a pane of the model's values beside the 3D view."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from nicegui import ui
from nicegui.elements.mixins.disableable_element import DisableableElement
from nicegui.elements.mixins.text_element import TextElement
from nicegui.elements.mixins.validation_element import ValidationElement

from nanopnp.api.project import Project
from nanopnp.gui.web.frame import Views, heading
from nanopnp.gui.web.molecular import STAGES, MolecularModel
from nanopnp.gui.web.molview import COLOURINGS, REPRESENTATIONS
from nanopnp.gui.web.screens import Tool, field_control
from nanopnp.gui.web.shell import Shell
from nanopnp.io.case_paths import schema_default
from nanopnp.io.models import read_model_file
from nanopnp.io.project import split_reference
from nanopnp.pipeline.checks import options_at

__all__ = ["FIELDS", "Field", "current_model", "tool_page"]


@dataclass(frozen=True)
class Field:
    """How a tool's pane shows one case value.

    Parameters
    ----------
    kind
        ``text``, ``number``, ``choice`` among the values the schema accepts at the path, or
        ``list``, which the pane shows and a tool of its own edits.
    """

    label: str
    kind: Literal["text", "number", "choice", "list"] = "text"
    unit: str = ""
    hint: str = ""


FIELDS: dict[str, Field] = {
    "structure.source.path": Field("Structure file", hint="A PDB or mmCIF file"),
    "structure.source.chains": Field(
        "Chains", hint="all, a list such as A,B,C, or groups such as A+B,C+D"
    ),
    "structure.symmetry.point_group": Field("Point group", hint="C1, or Cn of the ring"),
    "structure.symmetry.axis": Field("Axis", "choice"),
    "structure.ensemble.trajectory": Field(
        "Trajectory", hint="Without one, the models of the structure file"
    ),
    "structure.ensemble.frames.count": Field("Frames kept", "number"),
    "structure.ensemble.frames.last_ns": Field("Window from the last frame", "number", unit="ns"),
    "charge.ph": Field("pH", "number"),
    "charge.forcefield": Field("Force field", "choice"),
    "charge.titration": Field("Titration", "choice"),
    "charge.edits": Field("Residue edits", "list"),
}
"""Every value a Molecular tool sets, by case path."""

# The stage each tool's build walks to, and the colouring its view opens with.
BUILDS: dict[str, tuple[str, str, str]] = {
    "prepare": ("structure", "Build ensemble", "chain"),
    "ensemble": ("structure", "Build ensemble", "chain"),
    "protonation": ("protonation", "Build molecular model", "charge"),
    "edit": ("protonation", "Build molecular model", "changed"),
    "view": ("protonation", "Build molecular model", "charge"),
}

STAGE_TITLES = {"structure": "Ensemble", "protonation": "Protonation"}
STATE_WORDS = {
    "empty": "not built",
    "building": "building…",
    "built": "built",
    "refused": "refused",
}


def current_model(shell: Shell) -> MolecularModel | None:
    """Return the molecular model the tools edit: the open one, else the project's first."""
    project = shell.bench.project
    if project is None:
        return None
    names = project.items("molecular")
    if not names:
        return None
    name = names[0]
    if project.current:
        kind, current = split_reference(project.current)
        if kind == "molecular" and current in names:
            name = current
    return MolecularModel(project, name, shell.queue)


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


class _Pane:
    def __init__(self, shell: Shell, tool: Tool, built: Views, focus: str) -> None:
        self.shell = shell
        self.tool = tool
        self.built = built
        self.focus = focus
        self.model = current_model(shell)
        self.stage, self.build_title, colouring = BUILDS[tool.id]
        self.look = {"representation": "cartoon", "colour": colouring}
        self.rows: dict[str, ui.element] = {}
        self.marks: dict[str, tuple[ui.label, ui.button]] = {}
        self.controls: dict[str, ui.element] = {}
        self.writing = True
        self.modified_only = False
        self.was_building = False
        self.status: ui.label
        self.readout_box: ui.column
        self.detail: ui.label
        self.build_button: ui.button

    # -- what the model holds ------------------------------------------------

    @property
    def project(self) -> Project | None:
        return self.shell.bench.project

    def body(self) -> dict[str, Any]:
        if self.model is None:
            return {}
        try:
            location = self.model.project.path("molecular", self.model.name)
            return dict(read_model_file("molecular", location, rebase=False).body)
        except (ValueError, OSError):
            return {}

    def changed(self) -> set[str]:
        if self.model is None:
            return set()
        try:
            listed = self.model.project.changes("molecular", self.model.name)
        except (ValueError, OSError):
            return set()
        return {change.path for change in listed}

    def exposed(self) -> set[str]:
        if self.model is None:
            return set()
        try:
            location = self.model.project.path("molecular", self.model.name)
            return {value.path for value in read_model_file("molecular", location).exposed}
        except (ValueError, OSError):
            return set()

    # -- the pane -------------------------------------------------------------

    def build(self) -> None:
        with ui.column().classes("tool-pane").props("data-control=tool-pane"):
            heading(self.tool.title, 1)
            ui.label(self.subject()).classes("muted")
            with ui.row().classes("items-center"):
                self.build_button = ui.button(self.build_title, on_click=self.on_build).props(
                    "unelevated no-caps color=primary data-control=tool-build"
                )
            self.status = ui.label().props("data-control=tool-status role=status")
            self.detail = ui.label().classes("refused")
            ui.checkbox("Modified only", on_change=self.on_modified).props(
                "data-control=tool-modified"
            )
            body, changed, exposed = self.body(), self.changed(), self.exposed()
            for path in self.tool.fields:
                self.field(path, body, path in changed, path in exposed)
            if self.tool.id == "view":
                self.view_controls()
            self.readout_box = ui.column().classes("readout").props("data-control=tool-readout")
            self.drafts()
        self.refresh()
        ui.timer(1.0, self.tick)
        ui.timer(0.1, self.start, once=True)

    def subject(self) -> str:
        if self.project is None:
            return "No project is open."
        if self.model is None:
            return "The project holds no molecular model."
        return f"Molecular model {self.model.name}"

    def field(self, path: str, body: dict[str, Any], changed: bool, exposed: bool) -> None:
        spec = FIELDS[path]
        value = _value_of(body, path)
        shown = value if value is not None else _default_of(path)
        control_name = field_control(path)
        with ui.element("div").classes("field-row").props(f'data-field="{path}"') as row:
            mark = ui.label("◆").classes("changed mark").props("aria-hidden=true")
            control: ui.element
            if spec.kind == "list":
                entries = shown if isinstance(shown, list) else []
                text = "; ".join(_edit_text(entry) for entry in entries) or "None"
                with ui.column().classes("field-list").props(f"data-control={control_name}"):
                    ui.label(spec.label).classes("field-label")
                    control = ui.label(text)
            elif spec.kind == "choice":
                options = list(options_at(path) or ())
                control = ui.select(
                    options,
                    label=spec.label,
                    value=shown if shown in options else None,
                    on_change=lambda e, p=path: self.write(p, e.value),
                ).props(f"dense outlined data-control={control_name}")
            elif spec.kind == "number":
                control = ui.number(
                    spec.label,
                    value=shown,
                    suffix=spec.unit or None,
                    on_change=lambda e, p=path: self.write(p, e.value),
                ).props(f"dense outlined debounce=500 data-control={control_name}")
            else:
                control = ui.input(
                    spec.label,
                    value="" if shown is None else str(shown),
                    on_change=lambda e, p=path: self.write(p, e.value or None),
                ).props(
                    f'dense outlined debounce=500 data-control={control_name} hint="{spec.hint}"'
                )
            reset = ui.button(icon="sym_o_undo", on_click=lambda _, p=path: self.reset(p)).props(
                f'flat dense aria-label="Reset {spec.label}" data-control=reset-{control_name}'
            )
            if spec.kind == "number":
                ui.checkbox(
                    "Expose",
                    value=exposed,
                    on_change=lambda e, p=path: self.expose(p, bool(e.value)),
                ).props(f'dense aria-label="Expose {spec.label} to studies"')
        if self.model is None and isinstance(control, ui.select | ui.number | ui.input):
            control.disable()
        self.rows[path] = row
        self.marks[path] = (mark, reset)
        self.controls[path] = control
        self.mark(path, changed)

    def view_controls(self) -> None:
        ui.select(
            dict(REPRESENTATIONS),
            label="Representation",
            value=self.look["representation"],
            on_change=lambda e: self.restyle("representation", str(e.value)),
        ).props("dense outlined data-control=view-representation")
        ui.select(
            dict(COLOURINGS),
            label="Colour by",
            value=self.look["colour"],
            on_change=lambda e: self.restyle("colour", str(e.value)),
        ).props("dense outlined data-control=view-colour")

    # -- what the build gave ---------------------------------------------------

    def readout(self) -> list[tuple[str, str]]:
        """Return the built stage's figures this tool shows, as (name, value)."""
        model = self.model
        if model is None:
            return []
        held = model.artefacts()
        structure = held["structure"].summary if "structure" in held else None
        table = held["protonation"].summary if "protonation" in held else None
        rows: list[tuple[str, str]] = []
        if self.tool.id == "prepare" and structure is not None:
            axis = _mapping(structure.get("axis"))
            rows.append(("Axis found by", str(axis.get("method", "permutation"))))
            for name, gate in _mapping(structure.get("gates")).items():
                rows.append((f"Gate, {name}", _gate_text(_mapping(gate))))
            check = _mapping(structure.get("frame_check"))
            if check:
                rows.append(("Aligned frame, tilt", f"{_number(check.get('tilt_deg'))}°"))
        elif self.tool.id == "ensemble" and structure is not None:
            frames = _mapping(structure.get("frames"))
            used = frames.get("indices")
            rows.append(("Frames used", str(len(used) if isinstance(used, list) else "?")))
            rows.append(("Frames available", str(frames.get("available", "?"))))
            rows.append(("Atoms", str(structure.get("atoms", "?"))))
            rows.append(("Chains, in ring order", _joined(structure.get("chains_cyclic_order"))))
            drift = structure.get("drift_deg")
            if isinstance(drift, list) and drift:
                rows.append(("Largest axis drift", f"{_number(max(drift))}°"))
        elif self.tool.id in {"protonation", "edit", "view"} and table is not None:
            rows.append(("Q_net per frame", _joined(table.get("q_net_e"), " e")))
            rows.append(("Residues", str(table.get("residues", "?"))))
            unapplied = table.get("unapplied")
            count = len(unapplied) if isinstance(unapplied, list) else 0
            rows.append(("States PROPKA asked for and the force field lacks", str(count)))
            rows.append(("PDB2PQR and PROPKA warnings", str(len(_mapping(table.get("warnings"))))))
        return rows

    def show_readout(self) -> None:
        self.readout_box.clear()
        rows = self.readout()
        with self.readout_box:
            if not rows:
                return
            heading("Built", 2)
            with ui.element("dl").classes("readout-list"):
                for name, value in rows:
                    TextElement(tag="dt", text=name).classes("muted")
                    TextElement(tag="dd", text=value)

    # -- the controls laid out for the prototype round ----------------------------

    def drafts(self) -> None:
        if self.tool.id == "ensemble":
            return
        with ui.column().classes("draft w-full"):
            ui.label("Laid out for your verdict; not wired yet.").classes("later")
            drafted: list[ui.element] = []
            if self.tool.id == "prepare":
                heading("Axis", 2)
                with ui.row().classes("items-center no-wrap w-full"):
                    drafted.append(ui.number("Tilt", suffix="°").props("dense outlined"))
                    drafted.append(ui.number("Azimuth", suffix="°").props("dense outlined"))
                with ui.row().classes("items-center"):
                    drafted.append(ui.button("Estimate").props("outline no-caps"))
                    drafted.append(ui.button("Flip").props("outline no-caps"))
                heading("Membrane", 2)
                drafted.append(
                    ui.input("Registration residues").props('dense outlined hint="As 164:186"')
                )
                drafted.append(ui.number("Centre, z", suffix="nm").props("dense outlined"))
                drafted.append(ui.button("Save prepared structure").props("outline no-caps"))
            elif self.tool.id == "protonation":
                drafted.append(ui.button("Residue states…").props("outline no-caps"))
            elif self.tool.id == "edit":
                heading("Edit a residue", 2)
                drafted.append(
                    ui.select([], label="Residue", with_input=True).props("dense outlined")
                )
                drafted.append(
                    ui.select(
                        ["Protonation state", "Charge change", "Radius scale"], label="Edit"
                    ).props("dense outlined")
                )
                drafted.append(ui.input("Value").props("dense outlined"))
                drafted.append(ui.button("Add edit").props("outline no-caps"))
                heading("Save", 2)
                drafted.append(ui.input("Variant name").props("dense outlined"))
                drafted.append(
                    ui.radio(["Linked to its parent", "Full copy"], value="Linked to its parent")
                )
                drafted.append(ui.button("Save as variant…").props("outline no-caps"))
            elif self.tool.id == "view":
                drafted.append(ui.checkbox("Clip at the axis"))
                ui.link("3D background, in Settings", "/settings?setting=viewer_background")
                with (
                    ui.element("div")
                    .classes("colour-bar")
                    .props('role="img" aria-label="Residue charge, from minus one to plus one e"')
                ):
                    ui.label("\u22121 e")
                    ui.element("span").classes("colour-bar-scale")
                    ui.label("+1 e")
            for element in drafted:
                if isinstance(element, DisableableElement):
                    element.disable()

    def mark(self, path: str, changed: bool) -> None:
        mark, reset = self.marks[path]
        mark.classes(remove="invisible") if changed else mark.classes(add="invisible")
        reset.set_visibility(changed)
        self.rows[path].set_visibility(changed or not self.modified_only)

    def on_modified(self, event: Any) -> None:  # noqa: ANN401 - NiceGUI's event
        self.modified_only = bool(event.value)
        changed = self.changed()
        for path in self.rows:
            self.mark(path, path in changed)

    # -- writing ---------------------------------------------------------------

    def write(self, path: str, value: Any) -> None:  # noqa: ANN401 - a field's value
        if self.model is None or not self.writing:
            return
        control = self.controls[path]
        if value is None and _value_of(self.body(), path) is None:
            return
        try:
            self.model.project.set_value("molecular", self.model.name, path, value)
        except ValueError as error:
            # Refused at its field: the rule, the value entered and the case path (WB-12).
            said = str(error).replace(f"{self.model.project.root}/", "")
            if isinstance(control, ValidationElement):
                control.error = said
            else:
                ui.notify(said, type="negative")
            return
        if isinstance(control, ValidationElement):
            control.error = None
        self.after_write(path)

    def reset(self, path: str) -> None:
        if self.model is None:
            return
        try:
            self.model.project.set_value("molecular", self.model.name, path, None)
        except ValueError as error:
            ui.notify(str(error), type="negative")
            return
        control = self.controls[path]
        self.writing = False
        try:
            default = _default_of(path)
            if isinstance(control, ui.input):
                control.value = "" if default is None else str(default)
            elif isinstance(control, ui.number | ui.select):
                control.value = default
            if isinstance(control, ValidationElement):
                control.error = None
        finally:
            self.writing = True
        self.after_write(path)

    def after_write(self, path: str) -> None:
        self.mark(path, path in self.changed())
        self.built.changes_moved()
        self.refresh()

    def expose(self, path: str, on: bool) -> None:
        if self.model is None:
            return
        try:
            self.model.project.set_exposed("molecular", self.model.name, path, on)
        except ValueError as error:
            ui.notify(str(error), type="negative")

    # -- the build and its state ----------------------------------------------

    def refresh(self) -> None:
        model = self.model
        self.detail.text = ""
        if model is None:
            self.status.text = self.subject()
            self.build_button.disable()
            return
        problem = model.problem()
        if problem is not None:
            self.status.text = "The model's file forms no case."
            self.detail.text = problem
            self.build_button.disable()
            return
        if not model.has_structure():
            self.status.text = (
                "This model reads its atoms and charges from a PQR file, so it has no "
                "structure to prepare, align or protonate."
            )
            self.build_button.disable()
            return
        states = model.states()
        self.status.text = " · ".join(
            f"{STAGE_TITLES[stage]}: {STATE_WORDS[states[stage]]}" for stage in STAGES
        )
        refusal = model.refusal()
        if refusal is not None:
            self.detail.text = f"{STAGE_TITLES.get(refusal[0], refusal[0])} refused: {refusal[1]}"
        self.build_button.enable()
        self.build_button.text = "Cancel build" if model.building else self.build_title
        self.show_readout()

    def on_build(self) -> None:
        model = self.model
        if model is None:
            return
        if model.building:
            model.cancel()
        else:
            try:
                model.build(self.stage)
            except ValueError as error:
                ui.notify(str(error), type="negative")
        self.was_building = model.building
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

    # -- the view ----------------------------------------------------------------

    def scene_url(self) -> tuple[str | None, str]:
        model = self.model
        if model is None or model.case() is None or not model.has_structure():
            return None, ""
        held = model.artefacts()
        form = "table" if "protonation" in held else "ensemble" if "structure" in held else "file"
        url = (
            f"/api/molecular/{model.name}/scene?representation={self.look['representation']}"
            f"&colour={self.look['colour']}"
        )
        return url, f"{model.name}:{form}"

    async def show(self) -> None:
        url, key = self.scene_url()
        await self.built.show_molecule(url, key)

    async def restyle(self, what: str, value: str) -> None:
        self.look[what] = value
        await self.show()

    async def start(self) -> None:
        await self.built.settled()
        await self.show()
        if self.focus in self.controls:
            name = field_control(self.focus)
            await ui.run_javascript(
                f"document.querySelector('[data-control={name}]')?.querySelector('input')?.focus()",
                timeout=10,
            )


def _mapping(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _number(value: object) -> str:
    return f"{value:.3g}" if isinstance(value, int | float) else "?"


def _joined(value: object, unit: str = "") -> str:
    if not isinstance(value, list):
        return "?"
    return ", ".join(f"{item}{unit}" for item in value)


def _gate_text(gate: dict[str, Any]) -> str:
    measured = next((v for k, v in gate.items() if k.startswith("measured")), None)
    limit = next((v for k, v in gate.items() if k.startswith(("limit", "budget"))), None)
    unit = "°" if any(key.endswith("_deg") for key in gate) else " nm"
    return f"{_number(measured)}{unit} of {_number(limit)}{unit} allowed"


def _edit_text(entry: object) -> str:
    if not isinstance(entry, dict):
        return str(entry)
    rest = ", ".join(f"{key} {value}" for key, value in entry.items() if key != "residue")
    return f"{entry.get('residue', '?')}: {rest}"


def tool_page(shell: Shell, tool: Tool) -> Callable[..., None]:
    """Return the page of one Molecular tool, which the frame's sub-pages build."""

    def page(built: Views, field: str = "") -> None:
        _Pane(shell, tool, built, field).build()

    return page
