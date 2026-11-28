"""The Physics suite's tool pages: a physics model's values, shown inside the study picked."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar
from urllib.parse import urlencode

from nicegui import run, ui
from nicegui.elements.mixins.text_element import TextElement

from nanopnp.core.paths import correction_source, names_a_path
from nanopnp.gui.web.builds import REFUSED
from nanopnp.gui.web.chart import Chart
from nanopnp.gui.web.frame import Views, heading
from nanopnp.gui.web.physics import PhysicsModel
from nanopnp.gui.web.plane import (
    ROLE_TITLES,
    electrolyte_chart,
    ion_text,
    mesh_stored,
    physics_chart,
    shown_solids,
)
from nanopnp.gui.web.screens import CORRECTED, Tool, field_control
from nanopnp.gui.web.shell import Shell
from nanopnp.gui.web.tools import FIELDS, _Pane, _value_of, current_name
from nanopnp.io.models import Kind, owner_of
from nanopnp.io.switches import SWITCHES, governing, switch_at
from nanopnp.materials.corrections import load_corrections
from nanopnp.mesh.ingest import SOLID_MATERIALS
from nanopnp.mesh.primitives import PERMITTIVITY_EXEMPT
from nanopnp.physics.models import Term, case_model, declaration, role_conditions
from nanopnp.physics.terms import CONDITIONS, Symbol, symbols_in, written
from nanopnp.pipeline.checks import APPLIED_WALLS, options_at

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.api.case import Case
    from nanopnp.io.resolved import ResolvedCase

__all__ = ["current_physics", "physics_page"]

MODEL = "physics.model"
ORDERS = ("numerics.elements.phi", "numerics.elements.c")
"""The two element orders that must be equal: setting one sets the other."""
CONCENTRATION = "electrolyte.concentration_M"
SPECIES = "electrolyte.species"
PERMITTIVITIES = "physics.solid_permittivities"
VARIABLE_DENSITY = "physics.variable_density"
FLOW = "physics.flow"
DIELECTRIC = "physics.dielectric_gradient_forces"
NEEDS_FLOW = "Dielectric forces need the flow."
DENSITY_CORRECTION = "electrolyte.corrections.density.model"
WALL_CHARGE = "boundary_conditions.wall_charge_C_m2"
LATER = ", later"
"""What an option this release does not apply says after its name."""
STERIC = (
    "electrolyte.corrections.steric.model",
    "electrolyte.corrections.steric.a_ion_nm",
    "electrolyte.corrections.steric.a_water_nm",
)
WALL_DISTANCE = ("numerics.wall_distance.sources", "numerics.wall_distance.max_distance_nm")
UNSET_CONCENTRATION = "Type the concentration. It has no default. "
COMPOSER = (
    "Later: the composer builds a model from registered terms. It comes in a later phase. Until "
    "then, choose a registered model."
)

# The change of model each window last made and the values it changed, by project and model,
# which Undo writes back; kept across the page's rebuild that shows the change.
_CHOSEN: dict[tuple[Path, str], tuple[str, dict[str, Any]]] = {}


def current_physics(shell: Shell) -> PhysicsModel | None:
    """Return the physics model the tools edit, shown in the study the window chose for it."""
    project, name = shell.bench.project, current_name(shell, "physics")
    if project is None or name is None:
        return None
    return PhysicsModel(project, name, shell.queue, shown_in=shell.shown_in.get(name))


class _PhysicsPane(_Pane[PhysicsModel]):
    kind: ClassVar[str] = "physics"
    model_kind: ClassVar[Kind] = "physics"

    def __init__(self, shell: Shell, tool: Tool, built: Views, focus: str) -> None:
        super().__init__(shell, tool, built, focus, current_physics(shell))
        self.look: dict[str, str] = {"pick": "", "mesh": ""}
        self.flags: dict[str, bool] = {}
        self.groups: dict[str, tuple[str, ...]] = {}
        self.later_box: ui.element
        self.view_box: ui.element
        self.roles_box: ui.element

    # -- the model and the study it is shown in ---------------------------------------------

    def build_pane(self) -> None:
        # What runs after an event's handler, such as a redraw of the view, waits here.
        self.later_box = ui.element("div").classes("hidden")
        super().build_pane()

    def soon(self, then: Callable[[], Any]) -> None:
        with self.later_box:
            ui.timer(0.01, then, once=True)

    def usable(self) -> bool:
        return self.model is not None and bool(self.model.body())

    def declared_unread(self) -> frozenset[str]:
        try:
            return declaration(str(self.model.shown(MODEL))).unread if self.model else frozenset()
        except KeyError:
            return frozenset()

    def aside(self, path: str) -> str | None:
        if self.model is None:
            return None
        held = {
            key: value
            for key, value in self.model.study_values().items()
            if key == path or key.startswith(f"{path}.")
        }
        if not held:
            return None
        unit = FIELDS[path].unit if path in FIELDS else ""
        # A value per material is one leaf: each material is said with its own number.
        flat = {
            f"{key}.{name}" if isinstance(value, dict) else key: number
            for key, value in held.items()
            for name, number in (value.items() if isinstance(value, dict) else [(None, value)])
        }
        said = ", ".join(
            f"{value} {unit or ''}".strip()
            if key == path
            else f"{key.removeprefix(path + '.')} {value}"
            for key, value in flat.items()
        )
        study = self.model.within()
        return f"Study {study} sets its own value, {said}. This field shows the model's value."

    def solids(self) -> tuple[str, ...]:
        if self.model is None:
            return ()
        # The case as shown, though the study refuses it: its stored mesh names its solids.
        stored = shown_solids(self.shown_case(), self.model.project.session().store)
        if stored is not None:
            return stored
        # No mesh to read: every solid a pore may hold, so a refused one can be given its value.
        held = self.model.shown(PERMITTIVITIES)
        named = set(held) if isinstance(held, dict) else set()
        return tuple(sorted(named | (SOLID_MATERIALS - PERMITTIVITY_EXEMPT)))

    def subject(self) -> str:
        if self.project is not None and self.model is None:
            return "The project has no physics model. Import a case to add one."
        return super().subject()

    def before_cards(self) -> None:
        # The study the model is shown in comes first: the cards below it speak of that study.
        model = self.model
        if model is None or self.project is None:
            return
        studies = list(self.project.items("study"))
        with self.named("Shown in"):
            if studies:
                ui.select(
                    studies, value=model.within(), on_change=lambda e: self.show_in(str(e.value))
                ).props(
                    "dense outlined options-dense data-control=physics-shown-in "
                    'aria-label="The study the model is shown in"'
                )
            else:
                ui.label("No study. The model is shown over the continuum model.").classes("later")

    def show_in(self, study: str) -> None:
        if self.model is None:
            return
        self.shell.shown_in[self.model.name] = study
        self.soon(self.built.reopen)

    def own_status(self) -> None:
        if self.model is None:
            return
        study = self.model.within()
        if study is None:
            ui.label("The project has no study. The model is shown over its continuum model.")
        elif self.model.names_this(study):
            ui.label("The study uses this model.")
        else:
            ui.label("A preview in place of the study's own model. Nothing in the study changes.")

    def show_status(self) -> None:
        self.status.clear()
        with self.status:
            if self.model is None:
                ui.label(self.subject())
                return
            self.own_status()

    def show_cards(self, problem: str | None, refusal: tuple[str, str] | None) -> None:
        self.cards.clear()
        self.flagged = None
        with self.cards:
            if problem is not None and self.model is not None:
                # Saved and shown, not refused: the study's own values may be what is wrong. It
                # blocks the study's run where the study runs with this model; elsewhere it is
                # a preview, which blocks nothing.
                study = self.model.within()
                own = study is not None and self.model.names_this(study)
                path = self.problem_path(problem)
                kind = "err" if own or study is None else "warn"
                # A value the physics model does not hold is named where it is held.
                owner = None if path is None else owner_of(path)
                if study is not None and owner in ("molecular", "continuum"):
                    title = f"Study {study} cannot run. Its {owner} model has a problem."
                elif study is not None and owner == "study":
                    title = f"Study {study} cannot run. One of its own values has a problem."
                elif study is None:
                    title = "No case forms"
                elif own:
                    title = f"Study {study} cannot run with this model"
                else:
                    title = f"Preview: study {study} cannot run with this model"
                self.card(kind, title, problem, path)
            for key, text in self.warnings():
                self.card("warn", "Warning", text, None, dismiss=key)

    # -- a field ----------------------------------------------------------------------------

    def field(self, path: str, body: dict[str, Any], changed: bool, exposed: bool) -> None:
        super().field(path, body, changed, exposed)
        if path == MODEL:
            # A change of model's note stands under the row that made it.
            self.chosen_note()
        model = self.model
        control = self.controls[path]
        if path in APPLIED_WALLS and isinstance(control, ui.select):
            # The walls this release applies, and the rest named as later.
            labels = {
                option: option.replace("_", " ") + ("" if option == APPLIED_WALLS[path] else LATER)
                for option in options_at(path) or ()
            }
            self.writing = False
            try:
                control.set_options(labels, value=control.value)
            finally:
                self.writing = True
            control.props(f':option-disable="o => String(o.label).endsWith({LATER!r})"')
        self.electrolyte_hints(path, control)
        if model is None:
            return
        name = str(model.shown(MODEL))
        try:
            declared = declaration(name)
        except KeyError:
            return
        why = None
        record = switch_at(path)
        if record is not None:
            honoured = declared.switches[record.name]
            # A switch held at a value the model runs with is disabled; one the model cannot
            # run with stays free, so the refusal's remedy can be made.
            state = "on" if honoured[0] else "off"
            if len(honoured) == 1 and bool(model.shown(path)) == honoured[0]:
                why = f"{name} keeps {_label(path).lower()} {state}. It cannot change."
                if path == VARIABLE_DENSITY and any(
                    DENSITY_CORRECTION.startswith(leaf) for leaf in declared.unread
                ):
                    # A density no correction moves is constant, whatever the switch says.
                    why = f"{name} reads no density correction, so the density is constant."
            elif len(honoured) == 1:
                with self.rows[path]:
                    ui.label(f"{name} needs {_label(path).lower()} {state}.").classes("field-hint")
            elif path == DIELECTRIC and not model.shown(FLOW):
                # PHY-23 adds the force and each ion's term together, and the force needs a flow.
                if not model.shown(path):
                    why = NEEDS_FLOW
                else:
                    with self.rows[path]:
                        ui.label(NEEDS_FLOW).classes("field-hint")
        elif any(path == leaf or leaf.startswith(f"{path}.") for leaf in declared.unread):
            where = "above" if self.tool.id == "equations" else "in Equations"
            why = f"{name} does not read this value. Choose another model {where}."
        if why is not None and isinstance(control, ui.select | ui.number | ui.input | ui.switch):
            control.disable()
            # Said where it is seen: a title alone does not reach a keyboard.
            self.rows[path].props(f'title="{why}"')
            with self.rows[path]:
                ui.label(why).classes("field-hint")

    def holds(self, tool_id: str, problem: str) -> tuple[str, str, str] | None:
        model = self.model
        path = None if model is None else self.problem_path(problem)
        found = None if path is None else self.tool_of(path)
        if model is None or found is None or found[0].id != self.suite.id:
            return None
        if found[1].id != tool_id:
            return None
        # The study's own model blocks its run; a preview in another study blocks nothing.
        study = model.within()
        if study is None or model.names_this(study):
            return "✕", "blocked: the study cannot run with the model", "state-err"
        return "●", "preview: the study cannot run with the model", "state-warn"

    def electrolyte_hints(self, path: str, control: ui.element) -> None:
        """Say under an electrolyte value what the parameter set gives for it."""
        if path == SPECIES:
            listed = self.ions()
            control.props(f'title="The ions the parameter set gives: {listed}"')
            if isinstance(control, ui.label):
                control.set_text(listed or "none set")
        if path == CONCENTRATION and isinstance(control, ui.number):
            fitted = self.fitted()
            said = "" if control.value is not None else UNSET_CONCENTRATION
            if fitted is not None:
                said += f"Fitted from {fitted[0]:g} to {fitted[1]:g} M."
            control.props(f'hint="{said.strip()}"')
        if path in STERIC[1:] and isinstance(control, ui.number) and control.value is None:
            given = self.set_diameters()
            if path in given:
                control.props(f'hint="{given[path]} in the set"')

    def problem_path(self, problem: str) -> str | None:
        """Return the field a shown case's refusal names, its solid's row or another suite's."""
        model = self.model
        if model is None:
            return None
        path = model.refused_path(problem)
        if path is not None and path.startswith(PERMITTIVITIES):
            # A missing permittivity names its solid: its row takes the mark.
            # A name in quotes is the one refused; a bare one may be listed as allowed.
            named = [solid for solid in self.solids() if f"'{solid}'" in problem] or [
                solid for solid in self.solids() if solid in problem
            ]
            return f"{PERMITTIVITIES}.{named[0]}" if named else path
        if path is not None:
            return path
        # A value of the study's continuum model: its field, in the Continuum suite.
        return next((key for key in sorted(FIELDS, key=len, reverse=True) if key in problem), None)

    def lead(self, path: str | None) -> str | None:
        record = None if path is None else switch_at(path)
        if self.model is not None and path is not None and record is not None:
            name = str(self.model.shown(MODEL))
            try:
                declared = declaration(name)
                honoured = declared.switches[record.name]
            except KeyError:
                return super().lead(path)
            if len(honoured) == 1:
                # Each switch the model cannot run with, in one line: each is its own refusal.
                wrong = [
                    (_label(each.path).lower(), held[0])
                    for each in SWITCHES
                    if len(held := declared.switches[each.name]) == 1
                    and bool(self.model.shown(each.path)) != held[0]
                ]
                turns = [
                    f"{_listed([label for label, on in wrong if on is state])} "
                    f"{'on' if state else 'off'}"
                    for state in (True, False)
                    if any(on is state for _, on in wrong)
                ]
                if turns:
                    return f"Turn {' and '.join(turns)}. {name} cannot run otherwise."
            if path == DIELECTRIC and not self.model.shown(FLOW):
                return "Turn dielectric forces off, or turn the flow on."
        if path is not None and path.startswith(f"{PERMITTIVITIES}."):
            solid = path.rpartition(".")[2]
            return f"Type the relative permittivity of the {solid}. It has no default."
        return super().lead(path)

    def ions(self) -> str:
        if self.model is None:
            return ""
        resolved = self.model.resolved()
        if resolved is not None:
            return ", ".join(ion_text(ion.name) for ion in resolved.electrolyte.species)
        held = self.model.shown(SPECIES)
        return (
            ", ".join(ion_text(str(ion.get("name"))) for ion in held if isinstance(ion, dict))
            if isinstance(held, list)
            else ""
        )

    def set_diameters(self) -> dict[str, str]:
        """Return the steric diameters the parameter set gives, by the field they fill."""
        if self.model is None:
            return {}
        try:
            document = load_corrections(self.parameter_set())
        except (ValueError, OSError, KeyError):
            return {}
        ions = sorted({f"{ion.steric_diameter_nm:g}" for ion in document.species.values()})
        return {
            STERIC[1]: f"{' or '.join(ions)} nm",
            STERIC[2]: f"{document.solvent.water_steric_diameter_nm:g} nm",
        }

    def fitted(self) -> tuple[float, float] | None:
        if self.model is None:
            return None
        try:
            return load_corrections(self.parameter_set()).concentration_validity_M
        except (ValueError, OSError, KeyError):
            return None

    def parameter_set(self) -> str:
        """Return the model's parameter set: a shipped name, or a file found as a case finds it."""
        named = str(self.model.shown("electrolyte.parameters")) if self.model else ""
        if self.model is None or not names_a_path(named):
            return named
        base = self.model.project.path("physics", self.model.name).parent
        return str(correction_source(named, base=base))

    def mark(self, path: str, changed: bool) -> None:
        # A table's row holds several values: its mark shows while any of them is changed.
        self.flags[path] = changed
        group = self.groups.get(path, (path,))
        super().mark(path, any(self.flags.get(other, False) for other in group))

    def write(self, path: str, value: Any) -> None:  # noqa: ANN401 - a field's value
        if self.model is None or not self.writing:
            return
        if path == MODEL and value is not None:
            self.choose(str(value))
            return
        super().write(path, value)
        # The two orders are equal or the study refuses them: the other follows, once written.
        if path in ORDERS and value is not None and self.model.shown(path) == value:
            other = ORDERS[1 - ORDERS.index(path)]
            if self.model.shown(other) != value:
                super().write(other, value)
                control = self.controls[other]
                self.writing = False
                try:
                    if isinstance(control, ui.select):
                        control.value = value
                finally:
                    self.writing = True

    def reset(self, path: str) -> None:
        if self.model is None:
            return
        own = self.body()
        for each in ORDERS if path in ORDERS else (path,):
            if _value_of(own, each) is not None:
                super().reset(each)

    def after_write(self, path: str) -> None:
        super().after_write(path)
        if path.startswith("electrolyte.corrections.") and path.endswith(".model"):
            self.correction_parts(path)
        if self.tool.view in ("plane", "chart"):
            self.soon(self.show)

    def correction_parts(self, path: str) -> None:
        """Enable a correction's bulk and wall parts while its model is not none, and name it."""
        if self.model is None:
            return
        chosen = self.model.shown(path)
        select = self.controls.get(path)
        if isinstance(select, ui.select):
            select.props(f'title="{chosen}"')
        idle = self.idle() or path in self.declared_unread()
        base = path.removesuffix(".model")
        for part in ("concentration", "wall"):
            box = self.controls.get(f"{base}.{part}")
            if isinstance(box, ui.checkbox):
                box.set_enabled(not idle and chosen != "none")

    def choose(self, chosen: str) -> None:
        model = self.model
        if model is None:
            return
        try:
            earlier = model.project.choose_physics(model.name, chosen)
        except (ValueError, KeyError) as error:
            ui.notify(str(error).replace(f"{model.project.root}/", ""), type="negative")
            return
        if earlier:
            _CHOSEN[(model.project.root, model.name)] = (chosen, earlier)
        model.dismiss()
        self.built.changes_moved()
        self.soon(self.built.reopen)

    def chosen_note(self) -> None:
        model = self.model
        if model is None:
            return
        held = _CHOSEN.get((model.project.root, model.name))
        if held is None:
            return
        chosen, earlier = held
        lines = []
        for path, before in earlier.items():
            if path == MODEL:
                continue
            label = FIELDS[path].label if path in FIELDS else path
            now = model.shown(path)
            was = "unset" if before is None else before
            lines.append(f"{label}: {was} → {now}" if path in FIELDS else f"{label}: {was} removed")
        with (
            ui.element("div")
            .classes("note-card note-info")
            .props("role=status data-control=physics-chosen")
        ):
            with ui.row().classes("items-center no-wrap note-head"):
                ui.label("●").props("aria-hidden=true")
                ui.label(f"Model set to {chosen}").classes("note-title")
            if lines:
                ui.label("These values changed:").classes("note-short")
                with ui.element("ul").classes("note-list"):
                    for line in lines:
                        TextElement(tag="li", text=line)
            else:
                ui.label("No other value changed.").classes("note-short")
            with ui.row().classes("items-center"):
                ui.button("Undo", on_click=self.undo).props(
                    "outline dense no-caps data-control=physics-undo"
                )
                ui.button("Dismiss", on_click=self.forget).props("flat dense no-caps")

    def undo(self) -> None:
        model = self.model
        if model is None:
            return
        held = _CHOSEN.pop((model.project.root, model.name), None)
        if held is None:
            return
        for path, value in held[1].items():
            # A value unset since the change is already as it was; each other is written back,
            # so one refused leaves the rest restored.
            if value is None and _value_of(self.body(), path) is None:
                continue
            try:
                model.project.set_value("physics", model.name, path, value)
            except ValueError as error:
                ui.notify(str(error).replace(f"{model.project.root}/", ""), type="negative")
        self.built.changes_moved()
        self.soon(self.built.reopen)

    def forget(self) -> None:
        if self.model is not None:
            _CHOSEN.pop((self.model.project.root, self.model.name), None)
        self.soon(self.built.reopen)

    # -- each tool's own section -------------------------------------------------------------

    def equations_section(self) -> None:
        ui.label(COMPOSER).classes("later later-banner").props("data-control=composer-later")

    def electrolyte_section(self) -> None:
        body, changed = self.body(), self.changed()
        heading("Corrections", 2)
        with (
            ui.element("div")
            .classes("corrections")
            .props('data-control=tool-parts role=table aria-label="Corrections"')
        ):
            with ui.element("div").classes("corrections-row corrections-head").props("role=row"):
                for text in ("", "Property", "Model", "Bulk", "Wall", ""):
                    ui.label(text).props("role=columnheader")
            for name in CORRECTED:
                self.correction_row(name, changed)
        for path in STERIC:
            self.field(path, body, path in changed, path in self.exposed())
        heading("Distance to the wall", 2)
        for path in WALL_DISTANCE:
            self.field(path, body, path in changed, path in self.exposed())

    def correction_row(self, name: str, changed: set[str]) -> None:
        paths = tuple(
            f"electrolyte.corrections.{name}.{part}" for part in ("model", "concentration", "wall")
        )
        unread = self.declared_unread()
        model = self.model
        chosen = model.shown(paths[0]) if model else "none"
        idle = self.idle() or paths[0] in unread
        with (
            ui.element("div")
            .classes("corrections-row")
            .props(f'role=row data-field="{paths[0]}"') as row
        ):
            mark = ui.label("◆").classes("changed mark").props("aria-hidden=true")
            ui.label(name.capitalize()).props("role=rowheader")
            options = list(options_at(paths[0]) or ())
            select = ui.select(
                options,
                value=chosen if chosen in options else None,
                on_change=lambda e, p=paths[0]: self.write(p, e.value),
            ).props(
                # The small face, so most of the model's name shows beside its arrow.
                f"dense outlined options-dense "
                f"data-control={field_control(paths[0])} "
                f'aria-label="{FIELDS[paths[0]].label} correction"'
            )
            select.set_enabled(not idle)
            # The column cuts a long name: its whole is the select's tooltip.
            select.props(f'title="{chosen}"')
            self.controls[paths[0]] = select
            for path, part in zip(paths[1:], ("bulk", "wall"), strict=True):
                box = ui.checkbox(
                    value=bool(model.shown(path)) if model else True,
                    on_change=lambda e, p=path: self.write(p, bool(e.value)),
                ).props(
                    f"dense data-control={field_control(path)} "
                    f'aria-label="{name.capitalize()}, {part} part"'
                )
                box.set_enabled(not idle and chosen != "none")
                self.controls[path] = box
            reset = ui.button(
                icon="sym_o_undo", on_click=lambda _, ps=paths: self.reset_row(ps)
            ).props(
                f'flat dense aria-label="Reset {name}" data-control=reset-{field_control(paths[0])}'
            )
        if paths[0] in unread:
            row.props(
                f'title="{model.shown(MODEL) if model else ""} does not read this correction"'
            )
        for path in paths:
            self.rows[path] = row
            self.marks[path] = (mark, reset)
            self.groups[path] = paths
        for path in paths:
            self.mark(path, path in changed)

    def reset_row(self, paths: tuple[str, ...]) -> None:
        held = self.changed()
        for path in paths:
            if path in held:
                self.reset(path)

    def conditions_section(self) -> None:
        model = self.model
        resolved = None if model is None else model.resolved()
        geometry = None if resolved is None else resolved.document.geometry
        if geometry is not None and geometry.pore is not None:
            # A wall charge is read beside an idealised pore alone.
            self.field(
                WALL_CHARGE,
                self.body(),
                WALL_CHARGE in self.changed(),
                WALL_CHARGE in self.exposed(),
            )
        heading("Boundaries", 2)
        store = model.project.session().store if model is not None else None
        stored = model is not None and store is not None and mesh_stored(self.shown_case(), store)
        ui.checkbox(
            "Show mesh",
            value=stored and self.look["mesh"] == "1",
            on_change=lambda e: self.restyle("mesh", "1" if e.value else ""),
        ).props("dense data-control=physics-show-mesh").set_enabled(stored)
        if model is not None and not stored:
            ui.label(
                "The shown study cannot run, so no mesh is shown."
                if model.resolved() is None
                else "No mesh is stored for the shown study. Build it in Continuum \u203a Mesh."
            ).classes("field-hint")
        self.roles_box = (
            ui.column()
            .classes("parts w-full gap-0")
            .props('data-control=physics-roles role=group aria-label="Boundary roles"')
        )
        self.show_roles()

    def shown_case(self) -> Case | None:
        """Return the shown case as the view draws it: formed, though the study may refuse it."""
        if self.model is None:
            return None
        try:
            return self.model.project.physics_case(self.model.name, self.model.within())
        except REFUSED:
            return None

    def show_roles(self) -> None:
        self.roles_box.clear()
        model = self.model
        resolved = None if model is None else model.resolved()
        with self.roles_box:
            if model is None:
                ui.label("No model is open, so no role is shown.").classes("later")
                return
            if resolved is None:
                ui.label("The study cannot run with the model, so no role is shown.").classes(
                    "later"
                )
                return
            try:
                roles = role_conditions(case_model(resolved), resolved.ground)
            except (ValueError, KeyError) as error:
                ui.label(f"The roles cannot be read: {error}").classes("later")
                return
            for name, texts in roles.items():
                picked = self.look["pick"] == name
                title = ROLE_TITLES.get(name, name.capitalize())
                if name == resolved.ground:
                    title = f"{title}, grounded"
                with (
                    ui.button(on_click=lambda _, n=name: self.pick(n))
                    .classes("parts-row")
                    .props(
                        f"flat dense no-caps align=left data-control=role-{name} "
                        f"aria-pressed={'true' if picked else 'false'}"
                    )
                ):
                    with ui.column().classes("gap-0 w-full"):
                        ui.label(title).classes("parts-name")
                        # A condition names its field; one written alike for each ion shows once.
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
            used = [_field_tex(name) for texts in roles.values() for name in texts]
            used += [
                CONDITIONS.get(text, ("", text))[0]
                for texts in roles.values()
                for text in texts.values()
            ]
            heading("Symbols", 3)
            _symbols(symbols_in(used))

    async def pick(self, name: str) -> None:
        self.look["pick"] = "" if self.look["pick"] == name else name
        await self.show()
        self.show_roles()

    def fitted_for(self, path: str) -> tuple[float, float] | None:
        """Return the range the corrections are fitted over, beside the concentration."""
        return self.fitted() if path == CONCENTRATION else None

    # -- the view -----------------------------------------------------------------------------

    def after_refresh(self) -> None:
        if self.tool.view != "page":
            return
        self.view_box.clear()
        with self.view_box:
            if self.model is None:
                ui.label(self.subject()).classes("later")
            elif self.tool.id == "equations":
                self.draw_equations()

    def term_state(self, term: Term) -> str | None:
        """Return why a term is not in force, or None where it is."""
        if self.model is None:
            return None
        for record in governing(term.name):
            if not self.model.shown(record.path):
                return f"{_label(record.path)} is off."
        if term.correction is not None and self.model.shown(term.correction) == "none":
            return f"{FIELDS[term.correction].label} is none."
        return None

    def draw_equations(self) -> None:
        model = self.model
        if model is None:
            return
        name = str(model.shown(MODEL))
        try:
            declared = declaration(name)
        except KeyError:
            ui.label(f"No model has the name {name}.").classes("later")
            return
        shown = written(declared.terms, lambda term: self.term_state(term) is None)
        heading("Equations", 2)
        # The symbols' table stands below the equations: one link reaches it.
        ui.link("What each symbol means", "#equations-symbols").classes("field-hint").props(
            "data-control=equations-symbols-link"
        )
        with ui.element("div").classes("terms").props("data-control=equations-terms"):
            for item in shown:
                with ui.element("section").classes("term"):
                    with ui.row().classes("term-head items-baseline no-wrap"):
                        ui.label(item.term.name).classes("term-name")
                        clauses = dict.fromkeys(term.clause for term in (item.term, *item.joined))
                        ui.label(", ".join(clauses)).classes("term-clause")
                    _tex(item.equation, display=True, classes="term-equation")
                    for each in item.defines:
                        _tex(each, display=True, classes="term-define")
                    for note in item.notes:
                        _mtext(note, "term-note")
        off = [(term, self.term_state(term)) for term in declared.terms]
        if any(why for _, why in off):
            heading("Not in force", 3)
            with ui.element("ul").classes("terms-off").props("data-control=equations-off"):
                for term, why in off:
                    if why:
                        TextElement(tag="li", text=f"{term.name} ({term.clause}). {why}")
        heading("Symbols", 3).props("id=equations-symbols")
        texts = [item.equation for item in shown]
        texts += [each for item in shown for each in (*item.defines, *item.notes)]
        _symbols(symbols_in(texts))
        resolved = model.resolved()
        if resolved is None:
            ui.label(
                "The shown study cannot run with the model, so the fields are not shown. The "
                "equations follow the model's own switches."
            ).classes("later")
            return
        try:
            built = case_model(resolved)
        except (ValueError, KeyError) as error:
            ui.label(f"The model does not build: {error}").classes("later")
            return
        heading("Fields", 3)
        _table(
            ("Field", "Element", "Order", "Domain"),
            [
                (
                    _field_tex(field.name),
                    ELEMENTS.get(field.element, field.element),
                    f"P{field.order}",
                    "every domain" if field.domain is None else field.domain.replace("|", ", "),
                )
                for field in built.fields
            ],
            tex=(0,),
        )
        heading("Corrections in force", 3)
        _corrections_in_force(resolved)
        heading("Stabilisation", 3)
        ui.label(resolved.stabilisation)

    def plane_url(self) -> str | None:
        if self.model is None:
            return None
        query = {"tool": self.tool.id, "within": self.model.within() or "", **self.look}
        asked = urlencode({key: value for key, value in query.items() if value})
        return f"/api/physics/{self.model.name}/plane?{asked}"

    async def show(self) -> None:
        if self.tool.view == "page":
            # Ready once the equations are drawn in their own faces.
            await ui.run_javascript(
                "document.fonts.ready.then(() => { window.frameMath?.draw(document); "
                "document.body.dataset.screenReady = '1'; })",
                timeout=10,
            )
            return
        if self.tool.view == "chart":
            # None only while the server stops.
            chart = await run.io_bound(self.chart)
            if chart is not None:
                await self.built.show_chart(chart)
            return
        await self.built.show_plane(self.plane_url(), "" if self.model else self.subject())

    def chart(self) -> Chart:
        """Return Electrolyte's graphs of the model inside the study shown.

        A model that forms no case, as one with no salt, still draws its own block's curves
        against the driver, which read no salt.
        """
        model = self.model
        if model is None or self.project is None:
            return physics_chart(None, note=self.subject())
        try:
            # A case the study refuses still loads: the chart says it does not resolve.
            case: Case | None = self.project.physics_case(model.name, model.within())
        except REFUSED:
            case = None
        if case is None:
            electrolyte = model.own_electrolyte()
            if electrolyte is not None:
                return electrolyte_chart(electrolyte, None)
        return physics_chart(case)

    async def restyle(self, what: str, value: str) -> None:
        self.look[what] = value
        await self.show()


ELEMENTS = {"h1": "Lagrange, scalar", "vector_h1": "Lagrange, vector"}
"""The words for each finite-element family a field takes."""


def _label(path: str) -> str:
    return FIELDS[path].label if path in FIELDS else path


def _field_tex(name: str) -> str:
    # An ion's concentration takes its charge raised.
    if name.startswith("c_"):
        ion = name.removeprefix("c_")
        base = ion.rstrip("+-")
        charge = ion[len(base) :]
        return rf"c_{{\mathrm{{{base}}}^{{{charge}}}}}" if charge else rf"c_{{\mathrm{{{base}}}}}"
    return {"potential": r"\phi", "velocity": r"\mathbf{u}", "pressure": "p"}.get(name, name)


def _corrections_in_force(resolved: ResolvedCase) -> None:
    corrections = resolved.document.electrolyte.corrections
    held = []
    for prop in CORRECTED:
        choice = getattr(corrections, prop)
        if choice.model != "none":
            parts = [
                part for part, on in (("bulk", choice.concentration), ("wall", choice.wall)) if on
            ]
            held.append(f"{prop.capitalize()}: {choice.model}, {' and '.join(parts) or 'no part'}")
    if corrections.steric.model != "none":
        held.append(f"Steric flux: {corrections.steric.model}")
    if held:
        with ui.element("ul").classes("terms-off"):
            for line in held:
                TextElement(tag="li", text=line)
    else:
        ui.label("None. Each correction is the none model.")


def _tex(latex: str, *, display: bool = False, classes: str = "") -> ui.element:
    element = ui.element("div" if display else "span").classes(f"tex {classes}".strip())
    element.props["data-tex"] = latex
    if display:
        element.props["data-display"] = "1"
    return element


def _mtext(text: str, classes: str = "") -> ui.element:
    # The sentence's mathematics stands between `$` signs.
    element = ui.element("div").classes(f"mtext {classes}".strip())
    element.props["data-mtext"] = text
    return element


def _symbols(symbols: tuple[Symbol, ...]) -> None:
    with ui.element("table").classes("view-table").props("data-control=equations-symbols"):
        with ui.element("thead"), ui.element("tr"):
            for text in ("Symbol", "Meaning", "Unit"):
                TextElement(tag="th", text=text).props("scope=col")
        with ui.element("tbody"):
            for symbol in symbols:
                with ui.element("tr"):
                    with ui.element("td"):
                        _tex(symbol.tex)
                    with ui.element("td"):
                        _mtext(symbol.meaning)
                    TextElement(tag="td", text=symbol.unit)


def _table(
    head: tuple[str, ...], rows: list[tuple[str, ...]], *, tex: tuple[int, ...] = ()
) -> None:
    with ui.element("table").classes("view-table"):
        with ui.element("thead"), ui.element("tr"):
            for text in head:
                TextElement(tag="th", text=text).props("scope=col")
        with ui.element("tbody"):
            for row in rows:
                with ui.element("tr"):
                    for k, text in enumerate(row):
                        if k in tex:
                            with ui.element("td"):
                                _tex(str(text))
                        else:
                            TextElement(tag="td", text=str(text))


def physics_page(shell: Shell, tool: Tool) -> Callable[..., None]:
    """Return the page of one Physics tool, which the frame's sub-pages build."""

    def page(built: Views, field: str = "") -> None:
        shell.last_tool["physics"] = tool.id
        _PhysicsPane(shell, tool, built, field).build()

    return page


def _listed(items: list[str]) -> str:
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}"
