"""The Physics suite's tool pages: a physics model's values, shown inside the study picked."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar
from urllib.parse import urlencode

from nicegui import ui
from nicegui.elements.mixins.text_element import TextElement

from nanopnp.gui.web.builds import REFUSED
from nanopnp.gui.web.frame import Views, heading
from nanopnp.gui.web.physics import PhysicsModel
from nanopnp.gui.web.plane import ROLE_TITLES, shown_solids
from nanopnp.gui.web.screens import CORRECTED, Tool, field_control
from nanopnp.gui.web.shell import Shell
from nanopnp.gui.web.tools import FIELDS, _Pane, _value_of, current_name
from nanopnp.io.models import exposable_paths, read_model_file
from nanopnp.materials.corrections import load_corrections
from nanopnp.physics.models import SWITCHES, Term, case_model, declaration, role_conditions
from nanopnp.pipeline.checks import APPLIED_WALLS, options_at

__all__ = ["current_physics", "physics_page"]

MODEL = "physics.model"
ORDERS = ("numerics.elements.phi", "numerics.elements.c")
"""The two element orders that must be equal: setting one sets the other."""
CONCENTRATION = "electrolyte.concentration_M"
SPECIES = "electrolyte.species"
PERMITTIVITIES = "physics.solid_permittivities"
WALL_CHARGE = "boundary_conditions.wall_charge_C_m2"
LATER = ", later"
"""What an option this release does not apply says after its name."""
STERIC = (
    "electrolyte.corrections.steric.model",
    "electrolyte.corrections.steric.a_ion_nm",
    "electrolyte.corrections.steric.a_water_nm",
)
WALL_DISTANCE = ("numerics.wall_distance.sources", "numerics.wall_distance.max_distance_nm")
AGAINST = {"driver": "Concentration driver", "distance": "Distance to the wall"}
COMPOSER = (
    "Later: the composer, which builds a model from registered terms, comes in its own phase. "
    "Until then a model is one of those registered."
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

    def __init__(self, shell: Shell, tool: Tool, built: Views, focus: str) -> None:
        super().__init__(shell, tool, built, focus, current_physics(shell))
        self.look: dict[str, str] = {"against": "driver", "pick": ""}
        self.flags: dict[str, bool] = {}
        self.groups: dict[str, tuple[str, ...]] = {}
        self.later_box: ui.element
        self.view_box: ui.element
        self.roles_box: ui.element
        self.exposed_box: ui.column

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
        said = ", ".join(
            f"{key.removeprefix(path + '.') or 'value'} {value}" for key, value in held.items()
        )
        study = self.model.within()
        return f"Study {study} sets its own ({said}); left out here, so this is the model's"

    def solids(self) -> tuple[str, ...]:
        if self.model is None:
            return ()
        stored = shown_solids(self.model.case(), self.model.project.session().store)
        if stored is not None:
            return stored
        held = self.model.shown(PERMITTIVITIES)
        return tuple(held) if isinstance(held, dict) else ()

    def subject(self) -> str:
        if self.project is not None and self.model is None:
            return "The project holds no physics model: import a case to add one."
        return super().subject()

    def before_fields(self) -> None:
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
                ui.label("No study: over the project's continuum model").classes("later")
        self.chosen_note()

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
            ui.label(
                "Shown over the project's continuum model, as it is built alone: the project "
                "holds no study."
            )
        else:
            ui.label(
                f"Shown in study {study}, with this model in place of its own; the study's own "
                "values of the model's keys are left out."
            )

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
                # Saved and shown, not refused: the study's own values may be what is wrong.
                study = self.model.within()
                title = f"Study {study} cannot run with this model" if study else "No case forms"
                self.card("err", title, problem, self.model.refused_path(problem))
            for key, text in self.warnings():
                self.card("warn", "Warning", text, None, dismiss=key)

    # -- a field ----------------------------------------------------------------------------

    def field(self, path: str, body: dict[str, Any], changed: bool, exposed: bool) -> None:
        super().field(path, body, changed, exposed)
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
        if path == SPECIES:
            listed = self.ions()
            control.props(f'title="The ions the parameter set gives: {listed}"')
            if isinstance(control, ui.label):
                control.set_text(listed or "none set")
        if path == CONCENTRATION and isinstance(control, ui.number):
            fitted = self.fitted()
            if fitted is not None:
                control.props(f'hint="Fitted from {fitted[0]:g} to {fitted[1]:g} M"')
        if model is None:
            return
        name = str(model.shown(MODEL))
        try:
            declared = declaration(name)
        except KeyError:
            return
        why = None
        if path.startswith("physics.") and path.removeprefix("physics.") in SWITCHES:
            honoured = declared.switches[path.removeprefix("physics.")]
            if len(honoured) == 1:
                state = "on" if honoured[0] else "off"
                why = f"{name} holds {FIELDS[path].label.lower()} {state}: it honours no other"
        elif any(path == leaf or leaf.startswith(f"{path}.") for leaf in declared.unread):
            why = f"{name} does not read this value"
        if why is not None and isinstance(control, ui.select | ui.number | ui.input | ui.switch):
            control.disable()
            self.rows[path].props(f'title="{why}"')

    def ions(self) -> str:
        if self.model is None:
            return ""
        resolved = self.model.resolved()
        if resolved is not None:
            return ", ".join(ion.name for ion in resolved.electrolyte.species)
        held = self.model.shown(SPECIES)
        return (
            ", ".join(str(ion.get("name")) for ion in held if isinstance(ion, dict))
            if isinstance(held, list)
            else ""
        )

    def fitted(self) -> tuple[float, float] | None:
        if self.model is None:
            return None
        try:
            return load_corrections(
                str(self.model.shown("electrolyte.parameters"))
            ).concentration_validity_M
        except (ValueError, OSError, KeyError):
            return None

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
        if self.tool.view == "plane":
            self.soon(self.show)

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
            .classes("note-card note-ok")
            .props("role=status data-control=physics-chosen")
        ):
            with ui.row().classes("items-center no-wrap note-head"):
                ui.label("●").props("aria-hidden=true")
                ui.label(f"Model set to {chosen}").classes("note-title")
            ui.label(
                "Changed with it, so the model can run: " + "; ".join(lines) + "."
                if lines
                else "Nothing else changed with it."
            ).classes("note-short")
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
            try:
                model.project.set_value("physics", model.name, path, value)
            except ValueError as error:
                ui.notify(str(error).replace(f"{model.project.root}/", ""), type="negative")
                break
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
        heading("Plot", 2)
        with self.named("Plotted against"):
            ui.select(
                AGAINST,
                value=self.look["against"],
                on_change=lambda e: self.restyle("against", str(e.value)),
            ).props(
                "dense outlined options-dense data-control=physics-against "
                'aria-label="Plotted against"'
            )

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
                f"dense outlined options-dense data-control={field_control(paths[0])} "
                f'aria-label="{FIELDS[paths[0]].label} correction"'
            )
            select.set_enabled(not idle)
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
        self.roles_box = (
            ui.column()
            .classes("parts w-full gap-0")
            .props('data-control=physics-roles role=group aria-label="Boundary roles"')
        )
        self.show_roles()

    def show_roles(self) -> None:
        self.roles_box.clear()
        model = self.model
        resolved = None if model is None else model.resolved()
        with self.roles_box:
            if resolved is None:
                ui.label("The roles are listed once the shown study runs with the model.").classes(
                    "later"
                )
                return
            try:
                roles = role_conditions(case_model(resolved), resolved.ground)
            except (ValueError, KeyError) as error:
                ui.label(f"The model's roles do not read: {error}").classes("later")
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
                        for field_name, text in texts.items():
                            ui.label(f"{field_name}: {text}").classes("role-text")

    async def pick(self, name: str) -> None:
        self.look["pick"] = "" if self.look["pick"] == name else name
        await self.show()
        self.show_roles()

    def exposed_section(self) -> None:
        self.exposed_box = ui.column().classes("w-full gap-1").props("data-control=exposed-list")
        self.show_exposed()

    def show_exposed(self) -> None:
        self.exposed_box.clear()
        model = self.model
        with self.exposed_box:
            if model is None:
                return
            listed = self.listed()
            fitted = self.fitted()
            for entry in listed:
                with ui.element("div").classes("exposed-row").props(f'data-field="{entry.path}"'):
                    # The value first, on a line of its own; then its name, range and removal.
                    label = FIELDS[entry.path].label if entry.path in FIELDS else entry.path
                    ui.label(f"{label}, {entry.unit}" if entry.unit else label).classes(
                        "exposed-path"
                    )
                    ui.input(
                        value=entry.name,
                        on_change=lambda e, v=entry: self.expose_as(
                            v.path, str(e.value), (v.low, v.high)
                        ),
                    ).props(f'dense outlined debounce=800 aria-label="Name of {entry.path}"')
                    hint = fitted if entry.path == CONCENTRATION else None
                    low = ui.number(
                        value=entry.low,
                        placeholder=None if hint is None else f"{hint[0]:g}",
                        on_change=lambda e, v=entry: self.expose_as(
                            v.path, v.name, (e.value, v.high)
                        ),
                    ).props(f'dense outlined debounce=800 aria-label="Lowest {entry.name}"')
                    high = ui.number(
                        value=entry.high,
                        placeholder=None if hint is None else f"{hint[1]:g}",
                        on_change=lambda e, v=entry: self.expose_as(
                            v.path, v.name, (v.low, e.value)
                        ),
                    ).props(f'dense outlined debounce=800 aria-label="Highest {entry.name}"')
                    for control in (low, high):
                        control.set_enabled(self.usable())
                    ui.button(
                        icon="sym_o_close", on_click=lambda _, v=entry: self.unexpose(v.path)
                    ).props(f'flat dense aria-label="Stop exposing {entry.name}"')
            if not listed:
                ui.label("The model exposes no value: its studies list none first.").classes(
                    "later"
                )
            offered = {
                path: FIELDS[path].label if path in FIELDS else path
                for path in exposable_paths("physics")
                if path not in {entry.path for entry in listed}
            }
            with self.named("Expose"):
                adding = ui.select(offered, value=None).props(
                    "dense outlined options-dense data-control=exposed-add "
                    'aria-label="A value to expose"'
                )
                adding.set_enabled(self.usable() and bool(offered))
                ui.button(
                    icon="sym_o_add",
                    on_click=lambda: (
                        self.expose_as(str(adding.value), None, None) if adding.value else None
                    ),
                ).props('flat dense aria-label="Expose the value chosen"')

    def listed(self) -> tuple[Any, ...]:
        if self.model is None:
            return ()
        try:
            location = self.model.project.path("physics", self.model.name)
            return read_model_file("physics", location).exposed
        except REFUSED:
            return ()

    def expose_as(self, path: str, label: str | None, span: tuple[object, object] | None) -> None:
        model = self.model
        if model is None:
            return
        low, high = span if span is not None else (None, None)
        ranged = (
            (float(low), float(high))
            if isinstance(low, int | float) and isinstance(high, int | float)
            else None
        )
        try:
            model.project.set_exposed(
                "physics", model.name, path, True, label=label or None, span=ranged
            )
        except ValueError as error:
            ui.notify(str(error).replace(f"{model.project.root}/", ""), type="negative")
            return
        self.show_exposed()
        self.after_refresh()

    def unexpose(self, path: str) -> None:
        model = self.model
        if model is None:
            return
        try:
            model.project.set_exposed("physics", model.name, path, False)
        except ValueError as error:
            ui.notify(str(error), type="negative")
            return
        self.show_exposed()
        self.after_refresh()

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
            else:
                self.draw_exposed()

    def term_state(self, term: Term) -> str | None:
        """Return why a term is off, or None where it is on."""
        if self.model is None:
            return None
        for switch in term.switches:
            path = f"physics.{switch}"
            if not self.model.shown(path):
                return f"{FIELDS[path].label.lower()} is off"
        if term.correction is not None and self.model.shown(term.correction) == "none":
            return f"{FIELDS[term.correction].label.lower()} is none"
        return None

    def draw_equations(self) -> None:
        model = self.model
        if model is None:
            return
        name = str(model.shown(MODEL))
        try:
            declared = declaration(name)
        except KeyError:
            ui.label(f"No model is registered as {name}.").classes("later")
            return
        heading(f"What {name} solves", 2)
        with ui.element("ul").classes("terms").props("data-control=equations-terms"):
            for term in declared.terms:
                off = self.term_state(term)
                with ui.element("li").classes(f"term {'term-off' if off else 'term-on'}"):
                    with ui.row().classes("term-head items-baseline no-wrap"):
                        ui.label(term.name).classes("term-name")
                        ui.label(term.clause).classes("term-clause")
                        ui.label("on" if off is None else f"off: {off}").classes("term-state")
                    ui.label(term.equation).classes("term-equation")
        resolved = model.resolved()
        if resolved is None:
            ui.label(
                "The shown study does not run with the model, so its fields are not listed; the "
                "terms follow the model's own switches."
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
            [(f.name, f.element, f"P{f.order}", f.domain or "every domain") for f in built.fields],
        )
        heading("Corrections in force", 3)
        corrections = resolved.document.electrolyte.corrections
        held = []
        for prop in CORRECTED:
            choice = getattr(corrections, prop)
            if choice.model != "none":
                parts = [
                    part
                    for part, on in (("bulk", choice.concentration), ("wall", choice.wall))
                    if on
                ]
                held.append(
                    f"{prop.capitalize()}: {choice.model} ({' and '.join(parts) or 'no part'})"
                )
        if corrections.steric.model != "none":
            held.append(f"Steric flux: {corrections.steric.model}")
        ui.label("; ".join(held) + "." if held else "None: every correction is the none model.")
        heading("Stabilisation", 3)
        ui.label(resolved.stabilisation)

    def draw_exposed(self) -> None:
        heading("As a study lists it", 2)
        listed = self.listed()
        if not listed:
            ui.label("None: a study lists no value of this model first.").classes("later")
            return
        _table(
            ("Name", "Value", "Unit", "Range"),
            [
                (
                    entry.name,
                    "unset" if entry.default is None else self.text(entry.default, None),
                    entry.unit or "none",
                    _range(entry.low, entry.high),
                )
                for entry in listed
            ],
        )

    def plane_url(self) -> str | None:
        if self.model is None:
            return None
        query = {"tool": self.tool.id, "within": self.model.within() or "", **self.look}
        asked = urlencode({key: value for key, value in query.items() if value})
        return f"/api/physics/{self.model.name}/plane?{asked}"

    async def show(self) -> None:
        if self.tool.view == "page":
            await ui.run_javascript("document.body.dataset.screenReady = '1'", timeout=10)
            return
        await self.built.show_plane(self.plane_url(), "" if self.model else self.subject())

    async def restyle(self, what: str, value: str) -> None:
        self.look[what] = value
        await self.show()


def _range(low: float | None, high: float | None) -> str:
    if low is None and high is None:
        return "any"
    if high is None:
        return f"from {low:g}"
    return f"up to {high:g}" if low is None else f"{low:g} to {high:g}"


def _table(head: tuple[str, ...], rows: list[tuple[str, ...]]) -> None:
    with ui.element("table").classes("view-table"):
        with ui.element("thead"), ui.element("tr"):
            for text in head:
                TextElement(tag="th", text=text).props("scope=col")
        with ui.element("tbody"):
            for row in rows:
                with ui.element("tr"):
                    for text in row:
                        TextElement(tag="td", text=str(text))


def physics_page(shell: Shell, tool: Tool) -> Callable[..., None]:
    """Return the page of one Physics tool, which the frame's sub-pages build."""

    def page(built: Views, field: str = "") -> None:
        shell.last_tool["physics"] = tool.id
        _PhysicsPane(shell, tool, built, field).build()

    return page
