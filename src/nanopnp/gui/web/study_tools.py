"""The Study suite's tool pages: a study as its run sees it, its values, sweep, charge and runs."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar, Literal, cast

import yaml
from nicegui import events, ui
from nicegui.elements.mixins.text_element import TextElement
from nicegui.elements.mixins.validation_element import ValidationElement

from nanopnp.api.project import StudyValue
from nanopnp.core.hashing import decode_floats
from nanopnp.gui.convergence import ConvergenceModel
from nanopnp.gui.web.builds import REFUSED
from nanopnp.gui.web.chart_view import ChartView
from nanopnp.gui.web.frame import Views, heading
from nanopnp.gui.web.physics_tools import _field_tex, _mtext, _tex
from nanopnp.gui.web.plane import ROLE_TITLES
from nanopnp.gui.web.queue import Entry
from nanopnp.gui.web.runs import (
    RUNG_COLUMNS,
    convergence_chart,
    queue_run,
    queue_sweep,
    recorded_convergence,
    rung_rows,
    sweep_file,
    sweep_label,
    write_sweep,
)
from nanopnp.gui.web.screens import Tool, field_control
from nanopnp.gui.web.shell import Shell
from nanopnp.gui.web.study import StudyModel, reached
from nanopnp.gui.web.tools import (
    FIELDS,
    STAGE_TITLES,
    UNITS,
    _Pane,
    _range,
    _view_table,
    current_name,
)
from nanopnp.io.case_paths import case_fields, schema_default, value_at
from nanopnp.io.models import MODEL_KINDS, Kind, owner_of
from nanopnp.physics.models import case_model, role_conditions
from nanopnp.physics.terms import CONDITIONS
from nanopnp.pipeline.run import RUN_RECORD_FILENAME
from nanopnp.sweep.document import Axis, load_sweep
from nanopnp.sweep.forecast import Forecast, forecast
from nanopnp.sweep.plan import SweepPlan, build_plan

__all__ = ["current_study", "study_page"]

MODEL_PATHS = tuple(f"models.{kind}" for kind in MODEL_KINDS)
KIND_TITLES = {"molecular": "Molecular", "continuum": "Continuum", "physics": "Physics"}
QUANTITY_UNITS = {"V": "volt", "A": "ampere", "S": "siemens"}
"""The units of the scalar quantities Runs lists, by the symbol their names end in."""
RUNS_LISTED = 12
"""How many of a study's run records Runs lists, the newest first."""

PHYSICS_SHOWN: tuple[tuple[str, str], ...] = (
    ("physics.model", "Model"),
    ("physics.flow", "Flow"),
    ("electrolyte.parameters", "Parameter set"),
    ("electrolyte.concentration_M", "Concentration, M"),
    ("electrolyte.temperature_K", "Temperature, K"),
    ("boundary_conditions.bias_V", "Bias, V"),
    ("boundary_conditions.ground", "Grounded side"),
    ("numerics.stabilisation", "Stabilisation"),
)
"""The physics a study's Overview lists, by case path, each with its name."""


def current_study(shell: Shell) -> StudyModel | None:
    """Return the study the Study tools show: the one the pane chose, else the open or first one."""
    project = shell.bench.project
    if project is None:
        return None
    names = project.items("study")
    chosen = shell.study if shell.study in names else current_name(shell, "study")
    return None if chosen is None else StudyModel(project, chosen, shell.queue)


def _text(value: object) -> str:
    if value is None:
        return "unset"
    if isinstance(value, bool):
        return "on" if value else "off"
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, list | tuple):
        return ", ".join(_text(entry) for entry in value) or "none"
    return str(value)


def _sets(body: Mapping[str, Any], path: str) -> bool:
    node: Any = body
    for part in path.split("."):
        if not isinstance(node, Mapping) or part not in node:
            return False
        node = node[part]
    return True


_STAGE_WORDS = {
    **{stage: title[0].lower() + title[1:] for stage, title in STAGE_TITLES.items()},
    "case": "case",
    "materials": "materials",
    "solve": "solve",
    "qoi": "quantities",
    "report": "report",
}
"""Each stage's name in words, as a sweep's table of points lists what a point builds."""


def _default(path: str) -> object:
    try:
        has_default, default = schema_default(path)
    except KeyError:
        return None
    return default if has_default else None


# A number with an exponent and no point, which YAML 1.1 reads as text.
_EXPONENT = re.compile(r"[+-]?(?:\d+\.?\d*|\.\d+)[eE][+-]?\d+")


def _parsed(text: str) -> object:
    # As YAML reads it, a number, a word or a list; 1e-3 is the number a person typed.
    try:
        found = yaml.safe_load(text)
    except yaml.YAMLError:
        return text
    if isinstance(found, str) and _EXPONENT.fullmatch(found.strip()):
        return float(found)
    return found


SweepMode = Literal["every", "stepped"]
SWEEP_MODES: dict[SweepMode, str] = {"every": "Every combination", "stepped": "Stepped list"}
"""The two ways a sweep's rows make its points, with the title each shows."""

STEPS = "steps"
"""The name of a stepped list's one axis."""


def _sweep_rows(axes: Sequence[Axis]) -> tuple[SweepMode, list[tuple[str, list[Any]]]] | None:
    # One axis of assignments is a stepped list; axes of one path each are crossed. A file
    # written by hand in another form has no rows.
    if len(axes) == 1 and axes[0].assignments is not None:
        steps = axes[0].points()
        paths = list(dict.fromkeys(path for step in steps for path in step))
        if any(set(step) != set(paths) for step in steps):
            return None
        rows: list[tuple[str, list[Any]]] = []
        for path in paths:
            values = [step[path] for step in steps]
            rows.append((path, values[:1] if all(v == values[0] for v in values) else values))
        return "stepped", rows
    if all(axis.path is not None and axis.values is not None for axis in axes):
        return "every", [(str(axis.path), list(axis.values or ())) for axis in axes]
    return None


def _axis_names(rows: Sequence[tuple[str, Sequence[Any]]], kept: Sequence[Axis]) -> list[str]:
    # An axis keeps the name its file gives it, else takes its path's last part; one that another
    # axis already holds takes its whole path, as a sweep's axes are named apart.
    named = {axis.path: axis.name for axis in kept if axis.path is not None}
    names: list[str] = []
    for path, _ in rows:
        name = named.get(path) or path.rpartition(".")[2]
        names.append(path if name in names else name)
    return names


def _written(
    mode: SweepMode,
    rows: Sequence[tuple[str, Sequence[Any]]],
    labels: dict[str, str],
    kept: Sequence[Axis] = (),
) -> list[Axis]:
    # Each axis keeps the origin its file gives it while its values still reach it: the origin
    # roots the sweep's warm starts.
    origins = {axis.path: axis.origin for axis in kept if axis.path is not None}
    if mode == "every":
        crossed: list[Axis] = []
        for name, (path, values) in zip(_axis_names(rows, kept), rows, strict=True):
            origin = origins.get(path, 0)
            crossed.append(
                Axis(
                    name=name,
                    path=path,
                    values=cast("Any", list(values)),
                    origin=origin if origin < len(values) else 0,
                )
            )
        return crossed
    longest = max(len(values) for _, values in rows)
    for path, values in rows:
        if len(values) not in (1, longest):
            raise ValueError(
                f"Give each row of a stepped list 1 value or {longest} values. "
                f"{labels.get(path, path)} has {len(values)}."
            )
    steps = [
        {path: values[0] if len(values) == 1 else values[step] for path, values in rows}
        for step in range(longest)
    ]
    stepped = next((axis.origin for axis in kept if axis.assignments is not None), 0)
    origin = stepped if stepped < longest else 0
    return [Axis(name=STEPS, assignments=cast("Any", steps), origin=origin)]


class _StudyPane(_Pane[StudyModel]):
    kind: ClassVar[str] = "study"
    model_kind: ClassVar[Kind] = "study"

    def __init__(self, shell: Shell, tool: Tool, built: Views, focus: str) -> None:
        super().__init__(shell, tool, built, focus, current_study(shell))
        self.later_box: ui.element
        self.view_box: ui.element
        self.values_box: ui.column
        self.variables_box: ui.column
        self.axes_box: ui.column
        self.queue_box: ui.column
        self.sweep_mode: SweepMode = "every"
        self.rungs_box: ui.column
        self.run_summary: ui.label | None = None
        # What the view drew: a queued run's number, state and counts, or a recorded run's folder.
        self.run_seen: tuple[int, str, int, int] | tuple[str, str] | None = None

    # -- the study shown ----------------------------------------------------------------------

    def build_pane(self) -> None:
        # What runs after an event's handler, such as a reopened page, waits here.
        self.later_box = ui.element("div").classes("hidden")
        super().build_pane()

    def soon(self, then: Callable[[], Any]) -> None:
        with self.later_box:
            ui.timer(0.01, then, once=True)

    def exposed(self) -> set[str]:
        # A study exposes nothing: its models do, and Study setup lists what they expose.
        return set()

    def idle(self) -> bool:
        # A study refused by a model it names is mended at its fields, so they stay open.
        return self.model is None

    def subject(self) -> str:
        if self.project is not None and self.model is None:
            return "The project has no study. Pair three models with New study."
        if self.model is None:
            return super().subject()
        return f"Study {self.model.name}"

    def before_fields(self) -> None:
        project = self.project
        if project is None:
            return
        studies = list(project.items("study"))
        with self.named("Study"):
            if studies and self.model is not None:
                ui.select(
                    studies,
                    value=self.model.name,
                    on_change=lambda e: self.show_study(str(e.value)),
                ).props(
                    "dense outlined options-dense data-control=study-pick "
                    'aria-label="The study shown"'
                )
            else:
                ui.label("No study yet.").classes("later")
            # An icon, so the study's name keeps the row's width.
            ui.button(icon="sym_o_add", on_click=self.ask_new).props(
                'flat dense data-control=study-new aria-label="New study…" title="New study…"'
            )

    def show_study(self, name: str) -> None:
        self.shell.study = name
        self.soon(self.built.reopen)

    def models(self) -> dict[str, str]:
        """Return the model of each kind the study names, by kind."""
        if self.model is None:
            return {}
        named = self.model.body().get("models")
        if not isinstance(named, dict):
            return {}
        return {kind: Path(str(path)).stem for kind, path in named.items() if kind in MODEL_KINDS}

    def ask_new(self) -> None:
        project = self.project
        if project is None:
            return
        with ui.dialog() as dialog, ui.card().classes("study-new"):
            heading("New study", 2)
            name = ui.input("Name").classes("w-full")
            name.props("dense outlined data-control=study-new-name autofocus")
            chosen: dict[str, ui.select] = {}
            for kind in MODEL_KINDS:
                names = list(project.items(kind))
                chosen[kind] = ui.select(
                    names, value=names[0] if names else None, label=f"{KIND_TITLES[kind]} model"
                ).classes("w-full")
                chosen[kind].props(f"dense outlined options-dense data-control=study-new-{kind}")
            with ui.row().classes("justify-end w-full"):
                ui.button("Cancel", on_click=dialog.close).props("flat dense no-caps")
                ui.button("Create study", on_click=lambda: self.create(dialog, name, chosen)).props(
                    "unelevated dense no-caps color=primary data-control=study-new-create"
                )
        dialog.open()

    def create(self, dialog: ui.dialog, name: ui.input, chosen: dict[str, ui.select]) -> None:
        project = self.project
        if project is None:
            return
        picked = [str(chosen[kind].value or "") for kind in MODEL_KINDS]
        try:
            project.new_study(str(name.value or ""), *picked)
        except ValueError as error:
            name.error = str(error).replace(f"{project.root}/", "")
            return
        dialog.close()
        self.shell.study = str(name.value)
        self.built.changes_moved()
        self.soon(self.built.reopen)

    # -- writing the study ------------------------------------------------------------------

    def put(self, path: str, value: Any) -> None:  # noqa: ANN401 - a field's value
        if self.model is not None:
            self.model.project.set_study_value(self.model.name, path, value)

    def options(self, path: str) -> list[Any]:
        if path in MODEL_PATHS and self.project is not None:
            return list(self.project.items(cast("Any", path.removeprefix("models."))))
        return super().options(path)

    def shown_value(self, path: str, body: dict[str, Any]) -> Any:  # noqa: ANN401 - a field's value
        if path in MODEL_PATHS:
            return self.models().get(path.removeprefix("models."))
        return super().shown_value(path, body)

    def after_write(self, path: str) -> None:
        super().after_write(path)
        if self.tool.id == "setup":
            self.show_values()
            self.show_view()
        if path in MODEL_PATHS:
            # Another model changes every value the study lists.
            self.soon(self.built.reopen)

    def run_study(self) -> None:
        if self.model is None:
            return
        threads = int(str(self.shell.settings.value("threads_per_solve")))
        queue_run(self.shell.queue, self.model.project, self.model.name, threads=threads)
        ui.notify(f"Study {self.model.name} is queued. Runs draws its convergence.")
        self.built.queue_moved()

    def own_actions(self, ready: bool, building: bool) -> None:
        if self.tool.id in ("overview", "setup", "runs"):
            run = ui.button("Run study", on_click=self.run_study).props(
                "unelevated dense no-caps color=primary data-control=study-run"
            )
            runnable = self.model is not None and self.model.problem() is None
            run.set_enabled(runnable)
            if not runnable:
                said = "No study to run" if self.model is None else "The study forms no case"
                run.props(f'title="{said}"')
        elif self.tool.id == "sweep":
            run = ui.button("Run sweep", on_click=self.run_sweep).props(
                "unelevated dense no-caps color=primary data-control=sweep-run"
            )
            sweepable = bool(self.axes()) and self.usable()
            run.set_enabled(sweepable)
            if not sweepable:
                said = "No study to sweep" if self.model is None else "Add an axis to sweep"
                run.props(f'title="{said}"')

    def show_status(self) -> None:
        self.status.clear()
        with self.status:
            if self.model is None:
                ui.label(self.subject())
                return
            named = self.models()
            paired = ", ".join(f"{kind} {named[kind]}" for kind in MODEL_KINDS if kind in named)
            ui.label(f"Study {self.model.name} pairs {paired or 'no model'}.")
            if self.model.problem() is not None:
                ui.label("It forms no case. The message below names the value to correct.")

    def show_cards(self, problem: str | None, refusal: tuple[str, str] | None) -> None:
        self.cards.clear()
        self.flagged = None
        with self.cards:
            if problem is not None and self.model is not None:
                self.card(
                    "err", "The study forms no case", problem, self.model.refused_path(problem)
                )
            if refusal is not None and self.model is not None:
                named = self.model.refused_path(refusal[1])
                self.card("err", f"The build was blocked at {refusal[0]}", refusal[1], named)

    def after_refresh(self) -> None:
        self.show_view()
        if self.tool.id == "runs":
            self.show_runs()

    # -- the views ----------------------------------------------------------------------------

    def show_view(self) -> None:
        if self.tool.view != "page":
            return
        self.view_box.clear()
        with self.view_box:
            if self.model is None:
                ui.label(self.subject()).classes("later")
            else:
                getattr(self, f"{self.tool.id}_view")()

    async def show(self) -> None:
        graphed = json.dumps(self.tool.id == "setup" and self.model is not None)
        # Ready once the graph has drawn, where the page draws one.
        await ui.run_javascript(
            "new Promise((done) => { const t0 = Date.now(); const tick = () => {"
            f"if (!{graphed} || document.querySelector('[data-control=study-graph] svg')"
            " || Date.now() - t0 > 8000) { document.body.dataset.screenReady = '1'; done(); }"
            " else setTimeout(tick, 50); }; tick(); })",
            timeout=15,
        )

    # -- Overview -----------------------------------------------------------------------------

    def overview_section(self) -> None:
        model = self.model
        if model is None:
            return
        heading("Models", 2)
        with ui.column().classes("w-full gap-1").props("data-control=overview-models"):
            for kind, name in self.models().items():
                with ui.row().classes("items-center no-wrap"):
                    ui.label(f"{KIND_TITLES[kind]} model").classes("field-label")
                    ui.button(name, on_click=lambda _, k=kind, n=name: self.open_model(k, n)).props(
                        f"flat dense no-caps data-control=overview-open-{kind} "
                        f'aria-label="Open {kind} model {name}"'
                    )
        heading("Physics model", 2)
        case = model.case()
        if case is None:
            ui.label("The study forms no case, so its physics is not shown.").classes("later")
        else:
            overridden = set(case.overrides)
            record = case.models_record
            files = () if record is None else record.files
            own = model.body()
            rows: list[tuple[str, ...]] = []
            for path, label in PHYSICS_SHOWN:
                try:
                    value = value_at(case, path)
                except (KeyError, ValueError):
                    continue
                # Who sets it, said in words: the study, a model's file, else the default.
                if path in overridden:
                    owner = "\u25c7 the study"
                elif _sets(own, path):
                    owner = "the study"
                else:
                    owner = next(
                        (f"{file.kind} {file.name}" for file in files if _sets(file.body, path)),
                        "default",
                    )
                rows.append((label, _text(value), owner))
            _view_table(("Value", "Set to", "Set by"), rows, "overview-physics")
        heading("Sweep", 2)
        axes = self.axes()
        if axes:
            offered = self.axis_paths()
            for axis in axes:
                named = offered.get(str(axis.path), str(axis.path))
                ui.label(f"{named}: {_text(axis.values)}").classes("field-hint")
        else:
            ui.label("No sweep. Sweep varies a value, a variable or a model.").classes("later")
        heading("Runs", 2)
        records, solved = model.records(), model.runs()
        ui.label(
            f"{len(records)} run{'' if len(records) == 1 else 's'} recorded, "
            f"{len(solved) or 'none'} solved."
        ).classes("field-hint")

    def open_model(self, kind: str, name: str) -> None:
        if self.project is None:
            return
        self.project.open_item(f"{kind}/{name}")
        ui.navigate.to(f"/{kind}")

    def overview_view(self) -> None:
        model = self.model
        case = None if model is None else model.case()
        heading("The case the study runs", 2)
        if case is None:
            ui.label("The study forms no case, so there is no case file to show.").classes("later")
            return
        # What the study's files set, with the whole resolved case a click away.
        ui.label(
            "The values the models and the study set. The whole case adds each default."
        ).classes("field-hint")
        # One block at a time: the whole case shows in place of the set values.
        whole = ui.switch("Show the whole case").props("dense data-control=overview-whole-case")
        set_only = ui.code(case.dumps(set_only=True), language="yaml").classes("case-file")
        set_only.props("data-control=overview-case")
        every = ui.code(case.dumps(), language="yaml").classes("case-file")
        every.bind_visibility_from(whole, "value")
        set_only.bind_visibility_from(whole, "value", backward=lambda shown: not shown)
        resolved = None if model is None else model.resolved()
        if resolved is None:
            return
        try:
            roles = role_conditions(case_model(resolved), resolved.ground)
        except (KeyError, ValueError):
            return
        heading("Boundary conditions", 3)
        # As Physics, Conditions writes them: each field's condition as mathematics.
        with ui.column().classes("gap-1").props("data-control=overview-roles"):
            for role, texts in roles.items():
                title = ROLE_TITLES.get(role, role.capitalize())
                ui.label(f"{title}, grounded" if role == resolved.ground else title).classes(
                    "parts-name"
                )
                written_out: set[tuple[str, str]] = set()
                for field_name, text in texts.items():
                    latex, words = CONDITIONS.get(text, ("", text))
                    shown_as = (latex or _field_tex(field_name), words)
                    if shown_as in written_out:
                        continue
                    written_out.add(shown_as)
                    with ui.row().classes("role-text items-baseline no-wrap gap-2"):
                        _tex(shown_as[0])
                        _mtext(words, "role-words")

    # -- Study setup ----------------------------------------------------------------------------

    def setup_section(self) -> None:
        heading("Values", 2)
        self.values_box = ui.column().classes("w-full gap-1").props("data-control=study-values")
        heading("Variables", 2)
        self.variables_box = (
            ui.column().classes("w-full gap-1").props("data-control=study-variables")
        )
        self.show_values()

    def listed(self) -> tuple[StudyValue, ...]:
        if self.model is None:
            return ()
        try:
            return self.model.project.study_values(self.model.name)
        except REFUSED:
            return ()

    def show_values(self) -> None:
        if self.tool.id != "setup":
            return
        self.values_box.clear()
        self.variables_box.clear()
        if self.model is None:
            # No study: nothing to list or add to.
            return
        # A value the pane's own fields set is not listed again.
        listed = tuple(value for value in self.listed() if value.path not in self.tool.fields)
        named = self.models()
        with self.values_box:
            # Each model's values under its name, molecular, continuum then physics, then the
            # study's own.
            for kind in (*MODEL_KINDS, "study"):
                own = [value for value in listed if value.kind == kind]
                if not own:
                    continue
                title = (
                    "The study's own"
                    if kind == "study"
                    else f"{KIND_TITLES[kind]} {named.get(kind, '')}"
                )
                ui.label(title.strip()).classes("values-group")
                for value in own:
                    self.value_row(value)
            if not listed:
                said = (
                    "The values show once the study forms a case."
                    if self.model.problem() is not None
                    else "No model exposes a value, and the study sets none."
                )
                ui.label(said).classes("later")
            self.more_values({value.path for value in listed})
        with self.variables_box:
            self.variable_rows()

    def value_row(self, value: StudyValue) -> None:
        if value.name != value.path:
            shown = value.name
        elif value.path in FIELDS:
            shown = FIELDS[value.path].label
        else:
            # A value no tool names: its last part, the whole path in its title.
            shown = value.path.rpartition(".")[2].replace("_", " ")
        unit = "" if value.unit in ("", "dimensionless") else UNITS.get(value.unit, value.unit)
        named = f'data-control={field_control(value.path)} aria-label="{shown}"'
        default = _default(value.path)
        # A study's override is the outlined diamond; its own key, or a model's value away from
        # its default, the filled one.
        if value.study is not None:
            mark = "◆" if value.kind == "study" else "◇"
        elif value.model is not None and default is not None and value.model != default:
            mark = "◆"
        else:
            mark = ""
        with ui.element("div").classes("field-row").props(f'data-field="{value.path}"'):
            ui.label(mark).classes("changed mark").props("aria-hidden=true")
            ui.label(shown).classes("field-label").props(f'title="{value.path}"')
            current = value.value
            if isinstance(current, int | float) and not isinstance(current, bool):
                control: ui.element = ui.number(
                    value=current,
                    suffix=unit or None,
                    min=value.low,
                    max=value.high,
                    on_change=lambda e, p=value.path: self.write_value(p, e.value, e.sender),
                ).props(f"dense outlined debounce=500 {named}")
            else:
                control = ui.input(
                    value="" if current is None else _text(current),
                    on_change=lambda e, p=value.path: self.write_value(
                        p, _parsed(str(e.value)) if e.value else None, e.sender
                    ),
                ).props(f"dense outlined debounce=500 {named}")
            reset = ui.button(
                icon="sym_o_undo", on_click=lambda _, p=value.path: self.write_value(p, None, None)
            ).props(f'flat dense aria-label="Reset {shown}"')
            reset.set_visibility(value.study is not None)
            if value.study is not None and value.kind != "study":
                hint = f"The study's own. The {value.kind} model gives {_text(value.model)}."
            elif mark and value.kind != "study":
                hint = f"Set in the {value.kind} model. The default is {_text(default)}."
            else:
                hint = ""
            if hint:
                ui.label(hint).classes("field-hint")
            if value.low is not None or value.high is not None:
                ui.label(f"Range {_range(value.low, value.high)}").classes("field-hint")
        self.controls[value.path] = control

    def write_value(self, path: str, value: object, sender: object) -> None:
        if self.model is None:
            return
        try:
            self.model.project.set_study_value(self.model.name, path, cast("Any", value))
        except ValueError as error:
            said = str(error).replace(f"{self.model.project.root}/", "")
            if isinstance(sender, ValidationElement):
                sender.error = said
            else:
                ui.notify(said, type="negative", multi_line=True)
            return
        if isinstance(sender, ValidationElement):
            sender.error = None
        self.model.dismiss()
        self.built.changes_moved()
        self.show_values()
        self.show_view()

    def more_values(self, listed: set[str]) -> None:
        offered = {
            field.path: FIELDS[field.path].label if field.path in FIELDS else field.path
            for field in case_fields()
            if owner_of(field.path) in MODEL_KINDS
            and field.path not in listed
            and not field.path.startswith(("inputs.", "models."))
        }
        with ui.column().classes("study-adder w-full gap-1"):
            ui.label("More values").classes("field-label")
            adding = ui.select(offered, value=None, with_input=True).classes("w-full")
            adding.props(
                'dense outlined options-dense data-control=study-more aria-label="A value to set"'
            )
            row = ui.row().classes("items-center no-wrap w-full")
        with row:
            typed = (
                ui.input(placeholder="its value")
                .classes("col")
                .props('dense outlined data-control=study-more-value aria-label="Value"')
            )
            ui.button(
                icon="sym_o_add",
                on_click=lambda: (
                    self.write_value(str(adding.value), _parsed(str(typed.value or "")), typed)
                    if adding.value and typed.value
                    else None
                ),
            ).props('flat dense aria-label="Set the value chosen" data-control=study-more-add')

    def variable_rows(self) -> None:
        case = None if self.model is None else self.model.case()
        defined = {} if case is None else dict(case.variables)
        for name, entry in defined.items():
            with ui.element("div").classes("field-row").props(f'data-field="variables.{name}"'):
                ui.label("").classes("mark")
                ui.label(name).classes("field-label")
                said = entry.get("expression", entry.get("value"))
                unit = entry.get("unit", "dimensionless")
                ui.label(f"{_text(said)} {'' if unit == 'dimensionless' else unit}".strip())
                ui.button(
                    icon="sym_o_close", on_click=lambda _, n=name: self.set_variable(n, None, "")
                ).props(f'flat dense aria-label="Remove variable {name}"')
        if not defined:
            ui.label("The study defines no variable.").classes("later")
        with ui.column().classes("study-adder w-full gap-1"):
            ui.label("New variable").classes("field-label")
            row = ui.row().classes("items-center no-wrap w-full")
        with row:
            called = (
                ui.input(placeholder="name")
                .classes("col-4")
                .props(
                    'dense outlined data-control=variable-name aria-label="The variable\'s name"'
                )
            )
            typed = (
                ui.input(placeholder="value or expression")
                .classes("col")
                .props(
                    'dense outlined data-control=variable-value aria-label="Value or expression"'
                )
            )
            ui.button(
                icon="sym_o_add",
                on_click=lambda: self.set_variable(
                    str(called.value or ""), typed.value, "", called
                ),
            ).props('flat dense aria-label="Define the variable"')

    def set_variable(
        self, name: str, typed: object, unit: str, sender: object | None = None
    ) -> None:
        model = self.model
        if model is None or not name:
            return
        parsed = _parsed(str(typed)) if typed not in (None, "") else None
        number = (
            parsed if isinstance(parsed, int | float) and not isinstance(parsed, bool) else None
        )
        expression = str(typed) if parsed is not None and number is None else None
        try:
            model.project.set_variable(
                model.name,
                name,
                value=None if number is None else float(number),
                expression=expression,
                unit=unit or "dimensionless",
            )
        except ValueError as error:
            said = str(error).replace(f"{model.project.root}/", "")
            if isinstance(sender, ValidationElement):
                sender.error = said
            else:
                ui.notify(said, type="negative", multi_line=True)
            return
        self.built.changes_moved()
        self.show_values()

    def setup_view(self) -> None:
        heading("The study as a graph", 2)
        ui.label("Each model feeds the charge map or the solve. Pick a part to open it.").classes(
            "field-hint"
        )
        # Mermaid's default security, never loose; its text no smaller than the pane's.
        config = {"themeVariables": {"fontSize": "14px"}}
        ui.mermaid(self.graph(), config, on_node_click=self.on_node).classes("study-graph").props(
            "data-control=study-graph"
        )

    def graph(self) -> str:
        named = self.models()
        case = None if self.model is None else self.model.case()
        outputs = list(case.outputs) if case is not None else []
        # Top to bottom: the pane's column is tall and narrow, so the labels keep their size.
        lines = ["flowchart TB"]
        for kind in MODEL_KINDS:
            lines.append(
                f'  node_{kind}["{KIND_TITLES[kind]} model<br/>{named.get(kind, "none")}"]'
            )
        lines += [
            '  node_charge(["Charge map"])',
            '  node_solve(["Solve"])',
            "  node_molecular --> node_charge",
            "  node_continuum --> node_charge",
            "  node_charge --> node_solve",
            "  node_physics --> node_solve",
        ]
        for output in outputs:
            lines.append(f'  node_solve --> node_output_{output}["{output.replace("_", " ")}"]')
        return "\n".join(lines)

    async def on_node(self, event: events.MermaidNodeClickEventArguments) -> None:
        node = event.node_id.removeprefix("node_")
        if node == "charge":
            self.open_charge_map()
        elif node in MODEL_KINDS:
            await self.go_to(f"models.{node}")
        elif node == "solve":
            await self.go_to("numerics.continuation")
        elif node.startswith("output_"):
            await self.go_to("outputs")

    def open_charge_map(self) -> None:
        """Open Meso's Charge map on the study's continuum model, over its molecular model."""
        project, named = self.project, self.models()
        continuum, molecular = named.get("continuum"), named.get("molecular")
        if project is None or continuum is None:
            return
        try:
            if molecular is not None and project.molecular_for(continuum) != molecular:
                project.set_built_with(continuum, molecular)
        except ValueError as error:
            ui.notify(str(error), type="negative")
            return
        project.open_item(f"continuum/{continuum}")
        ui.navigate.to("/meso/charge")

    # -- Sweep ----------------------------------------------------------------------------------

    def axes(self) -> tuple[Axis, ...]:
        if self.model is None:
            return ()
        source = sweep_file(self.model.project, self.model.name)
        if not source.is_file():
            return ()
        try:
            return tuple(load_sweep(source).axes)
        except (*REFUSED, TypeError):
            return ()

    def plan(self) -> tuple[SweepPlan | None, Forecast | None, str | None]:
        if self.model is None or not self.axes():
            return None, None, None
        source = sweep_file(self.model.project, self.model.name)
        try:
            plan = build_plan(load_sweep(source), source=source, check_meshes=False)
            return plan, forecast(plan, store=self.model.project.session().store), None
        except (*REFUSED, TypeError) as error:
            return None, None, str(error).replace(f"{self.model.project.root}/", "")

    def sweep_section(self) -> None:
        heading("Axes", 2)
        self.axes_box = ui.column().classes("w-full gap-1").props("data-control=sweep-axes")
        self.show_axes()
        # The table of points follows its points' runs in the queue.
        self.sweep_seen: tuple[tuple[int, str], ...] | None = None
        ui.timer(1.0, self.follow_sweep)

    def axis_paths(self) -> dict[str, str]:
        """Return what an axis can vary: each value the study lists, each variable, each model."""
        offered = {f"models.{kind}": f"{KIND_TITLES[kind]} model" for kind in MODEL_KINDS}
        for value in self.listed():
            unit = "" if value.unit in ("", "dimensionless") else UNITS.get(value.unit, value.unit)
            offered[value.path] = f"{value.name}, {unit}" if unit else value.name
        case = None if self.model is None else self.model.case()
        for name in () if case is None else case.variables:
            offered[f"variables.{name}"] = f"Variable {name}"
        return offered

    def sweep_rows(self) -> tuple[SweepMode, list[tuple[str, list[Any]]]] | None:
        """Return the sweep as the pane edits it: its mode and a row per path, or None."""
        axes = self.axes()
        if not axes:
            return self.sweep_mode, []
        return _sweep_rows(axes)

    def show_axes(self) -> None:
        self.axes_box.clear()
        found = self.sweep_rows()
        if found is not None:
            self.sweep_mode = found[0]
        _, forecasted, refused = self.plan()
        warned = forecasted.warnings() if forecasted is not None else ()
        offered = self.axis_paths()
        with self.axes_box:
            if found is None:
                ui.label(
                    "The sweep's file writes its axes in another form. Edit them in the file."
                ).classes("later")
                for axis in self.axes():
                    ui.label(f"{axis.name}: {_text(axis.points())}").classes("field-hint")
            else:
                self.mode_row()
                self.axis_rows(found[1], offered, warned)
            if refused:
                with ui.element("div").classes("note-card note-err").props("role=alert"):
                    ui.label("The sweep does not plan").classes("note-title")
                    ui.label(refused).classes("note-short")
            if self.model is None or found is None:
                return
            if not found[1]:
                ui.label("No axis yet. Add one over a value, a variable or a model.").classes(
                    "later"
                )
            self.axis_adder(offered)

    def mode_row(self) -> None:
        with self.named("Points"):
            ui.toggle(
                dict(SWEEP_MODES),
                value=self.sweep_mode,
                on_change=lambda e: self.set_mode(cast("SweepMode", e.value)),
            ).props('dense no-caps data-control=sweep-mode aria-label="Combine rows as"').classes(
                "sweep-mode"
            )
        hint = (
            "Each combination of the rows' values is a point."
            if self.sweep_mode == "every"
            else "Point k takes each row's k-th value. A row of one value keeps it at every point."
        )
        ui.label(hint).classes("field-hint").props("data-control=sweep-mode-hint")

    def axis_rows(
        self,
        rows: Sequence[tuple[str, Sequence[Any]]],
        offered: dict[str, str],
        warned: Sequence[str],
    ) -> None:
        names = _axis_names(rows, self.axes())
        for index, (path, values) in enumerate(rows):
            with ui.element("div").classes("field-row").props(f"data-control=sweep-axis-{index}"):
                ui.label("").classes("mark")
                ui.label(offered.get(path, path)).classes("field-label")
                ui.input(
                    value=", ".join(_text(v) for v in values),
                    on_change=lambda e, i=index: self.set_axis(i, None, str(e.value or "")),
                ).props(f'dense outlined debounce=800 aria-label="Values of {path}"')
                ui.button(
                    icon="sym_o_close", on_click=lambda _, i=index: self.remove_axis(i)
                ).props(f'flat dense aria-label="Remove the axis over {path}"')
                if self.sweep_mode == "every":
                    for line in warned:
                        if f"axis {names[index]!r}" in line:
                            ui.label(f"● {line}").classes("field-hint field-warn-text")
        if self.sweep_mode == "stepped":
            for line in warned:
                ui.label(f"● {line}").classes("field-hint field-warn-text")

    def axis_adder(self, offered: dict[str, str]) -> None:
        with ui.column().classes("study-adder w-full gap-1"):
            ui.label("Add axis").classes("field-label")
            adding = ui.select(offered, value=None, label="Variable").classes("w-full")
            adding.props(
                'dense outlined options-dense data-control=sweep-add aria-label="Variable"'
            )
            row = ui.row().classes("items-center no-wrap w-full")
        with row:
            values = (
                ui.input(label="Values (comma-separated)")
                .classes("col")
                .props('dense outlined data-control=sweep-add-values aria-label="Values"')
            )
            ui.button(
                icon="sym_o_add",
                on_click=lambda: self.set_axis(
                    None, str(adding.value or ""), str(values.value or "")
                ),
            ).props('flat dense aria-label="Add the axis" data-control=sweep-add-axis')

    def set_axis(self, index: int | None, path: str | None, typed: str) -> None:
        found = self.sweep_rows()
        values = [_parsed(part.strip()) for part in typed.split(",") if part.strip()]
        if found is None or not values:
            return
        mode, rows = found
        if index is None:
            if not path:
                return
            rows.append((path, values))
        else:
            rows[index] = (rows[index][0], values)
        self.write_rows(mode, rows)

    def remove_axis(self, index: int) -> None:
        found = self.sweep_rows()
        if found is None:
            return
        self.write_rows(found[0], [row for k, row in enumerate(found[1]) if k != index])

    def set_mode(self, mode: SweepMode) -> None:
        found = self.sweep_rows()
        if found is None or not found[1]:
            self.sweep_mode = mode
            self.show_axes()
            return
        if not self.write_rows(mode, found[1]):
            self.show_axes()

    def write_rows(self, mode: SweepMode, rows: Sequence[tuple[str, Sequence[Any]]]) -> bool:
        """Write the rows as the mode writes them, or remove the sweep without a row."""
        model = self.model
        if model is None:
            return False
        try:
            if rows:
                axes = _written(mode, rows, self.axis_paths(), self.axes())
                write_sweep(model.project, model.name, axes)
            else:
                sweep_file(model.project, model.name).unlink(missing_ok=True)
        except (*REFUSED, TypeError, ValueError) as error:
            ui.notify(str(error), type="negative", multi_line=True)
            return False
        self.sweep_mode = mode
        self.show_axes()
        self.show_view()
        self.refresh()
        return True

    def run_sweep(self) -> None:
        model = self.model
        if model is None:
            return
        threads = int(str(self.shell.settings.value("threads_per_solve")))
        try:
            queued = queue_sweep(self.shell.queue, model.project, model.name, threads=threads)
        except (*REFUSED, TypeError) as error:
            ui.notify(str(error).replace(f"{model.project.root}/", ""), type="negative")
            return
        ui.notify(f"{len(queued)} points of the sweep are queued, wave by wave.")
        self.built.queue_moved()

    def sweep_view(self) -> None:
        heading("The sweep's points", 2)
        plan, found, refused = self.plan()
        if plan is None:
            ui.label(refused or "No sweep yet: each point is a run once an axis is added.").classes(
                "later"
            )
            return
        names = list(plan.points[0].assignments) if plan.points else []
        built = found.points if found is not None else ()
        offered = self.axis_paths()
        states = self.point_states(len(plan.points))
        _view_table(
            (
                "Point",
                *(offered.get(name, name) for name in names),
                "Wave",
                "Stages it builds",
                "State",
            ),
            [
                (
                    str(point.index + 1),
                    *(_text(point.assignments.get(name)) for name in names),
                    str(point.wave + 1),
                    ", ".join(_STAGE_WORDS.get(stage, stage) for stage in built[point.index])
                    if point.index < len(built)
                    else "",
                    states[point.index],
                )
                for point in plan.points
            ],
            "sweep-points",
        )
        ui.label(
            "Wave: a point starts from the solution of a point in the wave before it, "
            "so it waits for that wave. State: the point's run in the queue."
        ).classes("field-hint").props("data-control=sweep-wave-hint")
        if plan.rectification:
            ui.label(
                f"Rectification pairs {len(plan.pairs)} points by their resolved bias."
            ).classes("field-hint")

    def point_states(self, total: int) -> list[str]:
        """Return each point's state: the last queue entry that ran it, else not queued."""
        model = self.model
        latest = {
            entry.label: entry
            for entry in self.shell.queue.entries
            if model is not None and entry.study == model.name
        }
        return [
            latest[label].state() if label in latest else "\u25cb not queued"
            for label in (
                sweep_label("" if model is None else model.name, index, total)
                for index in range(total)
            )
        ]

    def follow_sweep(self) -> None:
        """Draw the sweep's points again when a point's run moves in the queue."""
        if self.tool.id != "sweep" or self.model is None:
            return
        seen = tuple(
            (entry.number, entry.status)
            for entry in self.shell.queue.entries
            if entry.study == self.model.name
        )
        if seen != self.sweep_seen:
            changed = self.sweep_seen is not None
            self.sweep_seen = seen
            if changed:
                self.show_view()

    # -- Runs -------------------------------------------------------------------------------------

    def runs_section(self) -> None:
        heading("In the queue", 2)
        self.queue_box = ui.column().classes("w-full gap-1").props("data-control=runs-queue")
        self.rungs_box = ui.column().classes("w-full gap-1").props("data-control=runs-rungs")
        # The picked run's plot and table follow it while it runs.
        ui.timer(0.5, self.follow_run)

    def study_entries(self, *, every: bool = False) -> list[Entry]:
        """Return the queue's runs of the study shown: the last ones, or with ``every`` all."""
        model = self.model
        if model is None:
            return []
        found = [
            entry
            for entry in self.shell.queue.entries
            if entry.run is not None and entry.study == model.name
        ]
        return found if every else found[-RUNS_LISTED:]

    def picked_run(self) -> Entry | None:
        """Return the run whose convergence the view shows: the one opened, else the last."""
        # Among them all: the queue's *Open* can name a run older than the last ones listed.
        entries = self.study_entries(every=True)
        for entry in entries:
            if entry.number == self.shell.run_shown:
                return entry
        return entries[-1] if entries else None

    def show_runs(self) -> None:
        self.queue_box.clear()
        picked = self.picked_run()
        with self.queue_box:
            entries = self.study_entries()
            if picked is not None and picked not in entries:
                # An older run opened from the queue is listed first, so it shows as the one picked.
                entries = [picked, *entries]
            for entry in entries:
                with ui.row().classes("items-center no-wrap gap-1"):
                    shown = (
                        self.recorded() is None
                        and picked is not None
                        and entry.number == picked.number
                    )
                    ui.button(entry.line(), on_click=lambda _, e=entry: self.pick_run(e)).props(
                        f"flat dense no-caps align=left data-control=runs-pick-{entry.number} "
                        f"aria-pressed={'true' if shown else 'false'}"
                    ).classes("runs-pick" + (" runs-picked" if shown else ""))
                    if not entry.ended:
                        ui.button("Cancel", on_click=lambda _, e=entry: self.cancel_entry(e)).props(
                            "outline dense no-caps data-control=runs-cancel"
                        )
            if not entries:
                ui.label(
                    "Nothing is queued. Click Run study to start a run; its convergence is "
                    "drawn in the view."
                ).classes("later")
        recorded = self.recorded()
        if recorded is not None:
            self.show_rungs(recorded_convergence(Path(recorded)))
        else:
            self.show_rungs(
                None if picked is None or picked.run is None else picked.run.convergence
            )

    def recorded(self) -> str | None:
        """Return the recorded run the view unfolds, by directory, or None for a queued one."""
        shown = self.shell.recorded_shown
        if shown is None or self.model is None:
            return None
        return shown if Path(shown) in self.model.records() else None

    def show_rungs(self, convergence: ConvergenceModel | None) -> None:
        self.rungs_box.clear()
        if convergence is None:
            return
        # A rung to a row, its note on a row of its own under it; the table scrolls in the pane.
        columns = [column for column in RUNG_COLUMNS if column["field"] != "note"]
        with self.rungs_box:
            heading("Rungs", 2)
            with (
                ui.element("div").classes("table-scroll rungs-scroll"),
                ui.element("table").classes("run-rungs").props("data-control=run-rungs"),
            ):
                with ui.element("thead"), ui.element("tr"):
                    for column in columns:
                        with ui.element("th").props(f"scope=col align={column['align']}"):
                            ui.label(column["label"])
                with ui.element("tbody"):
                    for row in rung_rows(convergence):
                        with ui.element("tr"):
                            for column in columns:
                                with ui.element("td").classes(f"align-{column['align']}"):
                                    ui.label(str(row[column["field"]]))
                        if row["note"]:
                            with (
                                ui.element("tr").classes("rung-note"),
                                ui.element("td").props(f"colspan={len(columns)}"),
                            ):
                                ui.label(row["note"]).classes("field-hint")

    def pick_run(self, entry: Entry) -> None:
        self.shell.run_shown = entry.number
        self.shell.recorded_shown = None
        self.run_seen = None
        self.show_runs()
        self.follow_run()

    def follow_run(self) -> None:
        """Draw the picked run's convergence again where its run said more."""
        if self.tool.id != "runs":
            return
        recorded = self.recorded()
        if recorded is not None:
            self.follow_recorded(recorded)
            return
        picked = self.picked_run()
        run = None if picked is None else picked.run
        seen = (
            None
            if picked is None or run is None
            else (
                picked.number,
                run.convergence.state,
                len(run.convergence.bands),
                sum(len(band.steps) for band in run.convergence.bands),
            )
        )
        if seen == self.run_seen:
            return
        changed_run = self.run_seen is None or seen is None or self.run_seen[0] != seen[0]
        self.run_seen = seen
        if changed_run:
            self.show_runs()
        elif picked is not None and picked.run is not None:
            self.show_rungs(picked.run.convergence)
        if picked is None or run is None or self.run_summary is None:
            return
        self.runs_chart.element.classes(remove="runs-plot-none")
        # The chart counts the samples its axis cannot place, so the line above it does not.
        self.run_summary.text = f"{picked.label}: {run.convergence.headline}"
        self.runs_chart.show(convergence_chart(run.convergence))

    def follow_recorded(self, recorded: str) -> None:
        """Draw a recorded run's convergence, replayed from its stored history (VER-44)."""
        if self.run_seen == ("recorded", recorded) or self.run_summary is None:
            return
        self.run_seen = ("recorded", recorded)
        self.show_runs()
        convergence = recorded_convergence(Path(recorded))
        name = Path(recorded).name[:12]
        if convergence is None:
            self.runs_chart.element.classes("runs-plot-none")
            self.run_summary.text = f"Recorded run {name}: its solve recorded no Newton history."
            return
        self.runs_chart.element.classes(remove="runs-plot-none")
        # The served and other-solve notes end the headline, above the chart.
        self.run_summary.text = f"Recorded run {name}: {convergence.headline}"
        self.runs_chart.show(convergence_chart(convergence))

    def pick_recorded(self, directory: Path) -> None:
        shown = str(directory)
        self.shell.recorded_shown = None if self.shell.recorded_shown == shown else shown
        self.run_seen = None
        self.refresh_records()
        self.follow_run()

    def open_result(self, directory: Path) -> None:
        self.shell.result_shown = str(directory)
        ui.navigate.to("/analysis/explorer")

    def cancel_entry(self, entry: Any) -> None:  # noqa: ANN401 - a queue's entry
        self.shell.queue.drop(entry)
        self.built.queue_moved()
        self.shown_state = ""
        self.refresh()

    def runs_view(self) -> None:
        heading("Convergence", 2)
        self.run_summary = ui.label("").classes("run-summary").props("data-control=runs-summary")
        self.runs_chart = ChartView("runs-plot", "runs-plot", classes="run-plot runs-plot")
        if self.picked_run() is None:
            self.run_summary.text = "Nothing is queued. Click Run study to start a run."
            # No frame stands empty: the plot's host shows once a run is picked.
            self.runs_chart.element.classes("runs-plot-none")
        self.run_seen = None
        heading("Recorded runs", 2)
        self.records_box = ui.column().classes("w-full")
        self.refresh_records()

    def refresh_records(self) -> None:
        """List the study's recorded runs, each a button that unfolds its convergence."""
        model = self.model
        self.records_box.clear()
        records = () if model is None else model.records()
        with self.records_box:
            if not records:
                ui.label("No run is recorded yet. Run study records one.").classes("later")
                return
            head = ("Written", "Reached", "Quantities", "Threads", "Convergence", "Result")
            # The table scrolls inside its tile, so the last column is never cut off.
            with (
                ui.element("div").classes("table-scroll"),
                ui.element("table").classes("view-table").props("data-control=runs-records"),
            ):
                with ui.element("thead"), ui.element("tr"):
                    for text in head:
                        TextElement(tag="th", text=text).props("scope=col")
                with ui.element("tbody"):
                    for index, directory in enumerate(records[:RUNS_LISTED]):
                        self.record_row(index, directory)

    def record_row(self, index: int, directory: Path) -> None:
        stages = reached(directory)
        done = "qoi" in stages
        record = decode_floats(
            json.loads((directory / RUN_RECORD_FILENAME).read_text(encoding="utf-8"))
        )
        quantities = record.get("quantities") if isinstance(record, dict) else None
        # The scalar quantities, each in its unit with its prefix: the bias, the current, the
        # conductance.
        said = ", ".join(
            f"{base} {self.text(value, QUANTITY_UNITS[symbol])}"
            for name, value in (quantities.items() if isinstance(quantities, dict) else ())
            for base, _, symbol in [name.rpartition("_")]
            if symbol in QUANTITY_UNITS
            and isinstance(value, int | float)
            and not isinstance(value, bool)
        )
        written = datetime.fromtimestamp((directory / RUN_RECORD_FILENAME).stat().st_mtime)
        cells = (
            written.strftime("%d %b %Y, %H:%M"),
            "solved" if done else f"to its {stages[-1] if stages else 'start'}",
            said or "none",
            "no solve"
            if "solve" not in stages
            else _text(record.get("threads"))
            if isinstance(record, dict)
            else "",
        )
        pressed = self.shell.recorded_shown == str(directory)
        with ui.element("tr"):
            for text in cells:
                TextElement(tag="td", text=str(text))
            with ui.element("td"):
                # A recorded run is picked as a queued one is: its convergence across the view.
                ui.button(
                    directory.name, on_click=lambda _, d=directory: self.pick_recorded(d)
                ).props(
                    f"flat dense no-caps data-control=runs-record-{index} "
                    f"aria-pressed={'true' if pressed else 'false'} "
                    f'aria-label="Show the convergence of run {directory.name}"'
                ).classes("runs-pick" + (" runs-picked" if pressed else ""))
            with ui.element("td"):
                if done:
                    ui.button("Result", on_click=lambda _, d=directory: self.open_result(d)).props(
                        f"flat dense no-caps data-control=runs-result-{index} "
                        f'aria-label="Open the result of run {directory.name}"'
                    )


def study_page(shell: Shell, tool: Tool) -> Callable[..., None]:
    """Return the page of one Study tool, which the frame's sub-pages build."""

    def page(built: Views, field: str = "") -> None:
        shell.last_tool["study"] = tool.id
        _StudyPane(shell, tool, built, field).build()

    return page
