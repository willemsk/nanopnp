"""The workbench's frame: title bar, activity bar, project rail, bottom panel and their commands."""

from __future__ import annotations

import os
import signal
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from nicegui import events, ui

from nanopnp.api.case import Case
from nanopnp.api.project import Problem, Project
from nanopnp.core.paths import remember_project
from nanopnp.core.public import __version__
from nanopnp.gui.web import commands, theme
from nanopnp.gui.web.overlay import Overlay
from nanopnp.gui.web.screens import SUITES
from nanopnp.gui.web.shell import Shell
from nanopnp.gui.web.states import Workbench
from nanopnp.io.defaults import Change
from nanopnp.io.project import ItemKind, Suite, SuiteLayout

__all__ = ["frame", "listed_changes"]

KINDS: tuple[tuple[ItemKind, str, Suite], ...] = (
    ("molecular", "Molecular models", "molecular"),
    ("continuum", "Continuum models", "continuum"),
    ("physics", "Physics models", "continuum"),
    ("study", "Studies", "study"),
    ("comparison", "Comparisons", "analysis"),
)
PANELS = ("queue", "log", "changes", "problems")
RAIL_FOLDED_PERCENT = 4.0
RAIL_LIMITS = (RAIL_FOLDED_PERCENT, 40.0)
BOTTOM_LIMITS = (40.0, 100.0)
GLOSSARY = (
    ("Project", "A folder of models, studies, comparisons, inputs, runs and stored results."),
    (
        "Model",
        "A molecular, a continuum or a physics model: the prepared structure, the pore and its "
        "mesh, or the equations, the salt and the voltage.",
    ),
    ("Study", "Pairs one model of each kind, overrides any of their values, and is run."),
    ("Override", "A value a study sets in place of its model's."),
    ("Queue", "The builds and runs waiting, running and done."),
)


def listed_changes(project: Project) -> list[tuple[str, tuple[Change, ...]]]:
    """Return each item's changed values, a study's own overrides but not its models' values."""
    listed: list[tuple[str, tuple[Change, ...]]] = []
    kinds: tuple[ItemKind, ...] = ("molecular", "continuum", "physics", "study")
    for kind in kinds:
        for name in project.items(kind):
            try:
                found = project.changes(kind, name)
                if kind == "study" and project.study(name).models_record is not None:
                    found = tuple(c for c in found if c.kind == "override")
            except Exception:  # an item that does not load is listed as a problem
                continue
            if found:
                listed.append((f"{kind}/{name}", found))
    return listed


class _Frame:
    def __init__(self, shell: Shell, suite: Suite, panel: str | None) -> None:
        self.shell = shell
        self.suite = suite
        project = shell.bench.project
        layout = project.layout.get(suite, SuiteLayout()) if project else SuiteLayout()
        self.layout = layout
        self.rail_folded = layout.rail_folded
        self.bottom_folded = layout.bottom_folded and panel is None
        self.panel = panel if panel in PANELS else "queue"
        self.outer: ui.splitter
        self.inner: ui.splitter
        self.tabs: ui.tabs
        self.dialog: ui.dialog
        self.palette: ui.dialog
        self.palette_input: ui.input
        self.palette_list: ui.column
        self.panel_root: ui.column
        self.overlay = Overlay(shell)
        self._listed: list[tuple[str, tuple[Change, ...]]] | None = None
        self._problems: tuple[Problem, ...] | None = None
        self.fold_button: ui.button
        self.toggle_button: ui.button
        self.actions: dict[str, Callable[[], object]] = {
            "palette": self.open_palette,
            "settings": self.overlay.open,
            "panel-toggle": self.toggle_panel,
            "changes": lambda: self.show_panel("changes"),
            "problems": lambda: self.show_panel("problems"),
            "layout-reset": self.reset_layout,
            "project-new": lambda: self.ask("New project", "Folder", self.new_project),
            "project-open": lambda: self.ask("Open project", "Folder", self.open_project),
            "project-import": lambda: self.ask("Import case", "Case file", self.import_case),
            "project-export": lambda: self.ask("Export project", "Destination", self.export),
            "glossary": self.glossary,
            "about": lambda: ui.notify(f"nanopnp {__version__}"),
            "quit": lambda: os.kill(os.getpid(), signal.SIGTERM),
            **{f"suite-{suite.id}": self.go(f"/{suite.id}") for suite in SUITES},
        }

    # -- what the page shows of the project ---------------------------------

    # Loading every item is the costly part, so a page builds each list once.
    def listed(self) -> list[tuple[str, tuple[Change, ...]]]:
        project = self.shell.bench.project
        if self._listed is None:
            self._listed = [] if project is None else listed_changes(project)
        return self._listed

    def problems(self) -> tuple[Problem, ...]:
        project = self.shell.bench.project
        if self._problems is None:
            self._problems = () if project is None else project.problems()
        return self._problems

    # -- commands -----------------------------------------------------------

    def go(self, path: str) -> Callable[[], object]:
        return lambda: ui.navigate.to(path)

    def run(self, identifier: str) -> None:
        action = self.actions.get(identifier)
        if action is None:
            ui.notify(f"{commands.command(identifier).title} is not available yet")
            return
        action()

    def on_command(self, event: events.GenericEventArguments) -> None:
        self.run(str(event.args["id"]))

    # -- the project's own commands ----------------------------------------

    def ask(self, title: str, label: str, then: Callable[[Path], object]) -> None:
        with ui.dialog() as dialog, ui.card().props("data-control=ask"):
            ui.label(title).classes("text-h6")
            field_ = ui.input(label).props("autofocus data-control=ask-input")

            def accept() -> None:
                try:
                    then(Path(field_.value).expanduser())
                except (ValueError, OSError) as error:
                    ui.notify(str(error), type="negative")
                    return
                dialog.close()

            field_.on("keydown.enter", accept)
            with ui.row():
                ui.button("Cancel", on_click=dialog.close).props("flat no-caps")
                ui.button(title, on_click=accept).props("no-caps")
        dialog.open()

    def switch(self, project: Project) -> None:
        self.shell.bench = Workbench(project.name, project=project, queue=self.shell.queue)
        remember_project(project.root)
        ui.navigate.to("/molecular")

    def new_project(self, folder: Path) -> None:
        self.switch(Project.create(folder))

    def open_project(self, folder: Path) -> None:
        self.switch(Project.open(folder))

    def import_case(self, path: Path) -> None:
        project = self.shell.bench.project
        if project is None:
            raise ValueError("open or create a project first")
        name = project.import_case(Case.load(path))
        self.shell.queue.log.append(f"imported {path.name} as study {name}")
        ui.navigate.to("/study")

    def export(self, destination: Path) -> None:
        project = self.shell.bench.project
        if project is None:
            raise ValueError("open or create a project first")
        written = project.export(destination)
        self.shell.queue.log.append(f"exported the project to {written}")
        ui.notify(f"Exported to {written}")

    def glossary(self) -> None:
        with ui.dialog() as dialog, ui.card().props("data-control=glossary"):
            ui.label("Glossary").classes("text-h6")
            for term, meaning in GLOSSARY:
                ui.label(f"{term}: {meaning}")
            ui.button("Close", on_click=dialog.close).props("flat no-caps")
        dialog.open()

    # -- the layout ---------------------------------------------------------

    def save_layout(self) -> None:
        project = self.shell.bench.project
        if project is None:
            return
        rail = self.layout.rail_percent
        bottom = self.layout.bottom_percent
        if not self.rail_folded:
            rail = min(max(float(self.outer.value), RAIL_LIMITS[0] + 1.0), RAIL_LIMITS[1])
        if not self.bottom_folded:
            bottom = min(max(100.0 - float(self.inner.value), 1.0), 100.0 - BOTTOM_LIMITS[0])
        self.layout = SuiteLayout(
            rail_percent=rail,
            bottom_percent=bottom,
            rail_folded=self.rail_folded,
            bottom_folded=self.bottom_folded,
        )
        project.save_layout(self.suite, self.layout)

    def apply_layout(self) -> None:
        self.outer.value = RAIL_FOLDED_PERCENT if self.rail_folded else self.layout.rail_percent
        self.inner.value = 100.0 if self.bottom_folded else 100.0 - self.layout.bottom_percent
        self.panel_root.set_visibility(not self.bottom_folded)
        self.fold_button.props(f"aria-expanded={str(not self.rail_folded).lower()}")
        self.toggle_button.props(f"aria-expanded={str(not self.bottom_folded).lower()}")

    def fold_rail(self) -> None:
        self.rail_folded = not self.rail_folded
        self.apply_layout()
        self.save_layout()
        ui.navigate.reload()

    def toggle_panel(self) -> None:
        self.bottom_folded = not self.bottom_folded
        self.apply_layout()
        self.save_layout()

    def show_panel(self, name: str) -> None:
        self.tabs.value = name
        if self.bottom_folded:
            self.toggle_panel()

    def reset_layout(self) -> None:
        self.layout = SuiteLayout()
        self.rail_folded, self.bottom_folded = self.layout.rail_folded, self.layout.bottom_folded
        self.apply_layout()
        project = self.shell.bench.project
        if project is not None:
            for suite in SUITES:
                project.save_layout(suite.id, self.layout)
        ui.navigate.reload()

    # -- the palette --------------------------------------------------------

    def open_palette(self) -> None:
        self.palette_input.value = ""
        self.fill_palette("")
        self.palette.open()

    def fill_palette(self, text: str) -> None:
        wanted = text.strip().lower()
        chords = commands.bindings(self.shell.keys)
        self.palette_list.clear()
        with self.palette_list:
            matching = [
                entry
                for entry in commands.COMMANDS
                if entry.id != "palette" and (not wanted or wanted in entry.title.lower())
            ]
            if not matching:
                ui.label("No command matches.").classes("muted")
            for entry in matching:
                with (
                    ui.button(on_click=lambda _, i=entry.id: self.choose(i))
                    .props("flat no-caps data-control=palette-item")
                    .classes("w-full")
                ):
                    ui.label(entry.title).classes("key-title")
                    ui.label(chords[entry.id]).classes("muted")

    def choose(self, identifier: str) -> None:
        self.palette.close()
        self.run(identifier)

    def first_match(self) -> None:
        wanted = self.palette_input.value.strip().lower()
        if not wanted:
            return
        for entry in commands.COMMANDS:
            if entry.id != "palette" and wanted in entry.title.lower():
                self.choose(entry.id)
                return

    # -- the pieces ---------------------------------------------------------

    def title_bar(self) -> None:
        bench = self.shell.bench
        changed = sum(len(found) for _, found in self.listed())
        chords = commands.bindings(self.shell.keys)
        with ui.row().classes("titlebar items-center no-wrap"):
            for menu in commands.MENUS:
                with ui.button(menu.capitalize()).props(f"flat no-caps data-control=menu-{menu}"):
                    with ui.menu():
                        for entry in commands.COMMANDS:
                            if entry.menu != menu:
                                continue
                            chord = chords[entry.id]
                            with ui.menu_item(on_click=lambda i=entry.id: self.run(i)):
                                ui.item_section(entry.title)
                                if chord:
                                    ui.item_section(chord).props("side")
            ui.label(bench.project.name if bench.project else "No project").classes(
                "project-name"
            ).props("data-control=project-name")
            ui.space()
            with ui.button(on_click=lambda: self.run("changes")).props(
                "flat no-caps data-control=changed-count"
            ):
                ui.label("◆").classes("changed")
                ui.label(f"{changed} changed")
            ui.button(
                f"Command palette  {chords['palette']}".rstrip(), on_click=self.open_palette
            ).props("flat no-caps data-control=palette-open")

    def activity_bar(self) -> None:
        with ui.column().classes("activitybar gap-0"):
            for suite in SUITES:
                current = suite.id == self.suite
                ui.button(suite.title, on_click=self.go(f"/{suite.id}")).props(
                    f"flat no-caps data-control=suite-{suite.id}"
                    + (' aria-current="page"' if current else "")
                ).classes("suite-button")

    def rail(self) -> None:
        bench = self.shell.bench
        project = bench.project
        with ui.column().classes("rail gap-1").props("data-control=rail"):
            self.fold_button = ui.button(
                icon="chevron_left" if not self.rail_folded else "chevron_right",
                on_click=self.fold_rail,
            ).props("flat dense aria-label='Fold the project rail' data-control=rail-fold")
            if self.rail_folded:
                if project is not None and project.current:
                    ui.label(project.current.split("/")[-1][:1].upper()).props(
                        f'title="{project.current}"'
                    )
                return
            if project is None:
                ui.label("No project open.").classes("muted")
                for identifier in ("project-new", "project-open"):
                    ui.button(
                        commands.command(identifier).title, on_click=self.actions[identifier]
                    ).props(f"flat dense no-caps data-control={identifier}").classes("w-full")
                return
            ui.label(project.current or "No item open").classes("rail-open")
            for kind, title, suite in KINDS:
                ui.label(title).classes("rail-heading")
                for name in project.items(kind):
                    item = f"{kind}/{name}"
                    ui.button(name, on_click=lambda _, i=item, s=suite: self.open_item(i, s)).props(
                        "flat dense no-caps"
                        + (' aria-current="true"' if item == project.current else "")
                    ).classes("rail-item list-row w-full")

    def open_item(self, item: str, suite: str) -> None:
        project = self.shell.bench.project
        if project is not None:
            project.open_item(item)
        ui.navigate.to(f"/{suite}")

    def status_bar(self) -> None:
        bench = self.shell.bench
        problems = len(self.problems()) or (1 if bench.project is None and bench.refusal else 0)
        with ui.row().classes("statusbar items-center no-wrap"):
            ui.label(self.shell.queue.status_line()).props("data-control=queue-status")
            ui.space()
            self.toggle_button = ui.button("Queue and log", on_click=self.toggle_panel).props(
                "flat dense no-caps data-control=panel-toggle"
            )
            ui.button(
                f"✕ {problems} problem{'' if problems == 1 else 's'}"
                if problems
                else "✓ No problems",
                on_click=lambda: self.run("problems"),
            ).props("flat dense no-caps data-control=problems-count")

    def bottom_panel(self) -> None:
        with ui.column().classes("bottom-panel w-full gap-0") as self.panel_root:
            with ui.tabs().props("align=left").classes("w-full") as self.tabs:
                for name in PANELS:
                    ui.tab(name, label=name.capitalize()).props(f"data-control=panel-tab-{name}")
            self.tabs.set_value(self.panel)
            with ui.column().classes("panel-body w-full"):
                with ui.tab_panels(self.tabs, value=self.panel).classes("w-full"):
                    with ui.tab_panel("queue"):
                        with ui.column().props("data-control=queue-list"):
                            for entry in self.shell.queue.entries or []:
                                ui.label(entry.line())
                            if not self.shell.queue.entries:
                                ui.label("Nothing is queued.")
                    with ui.tab_panel("log"):
                        with ui.column().props("data-control=log-list"):
                            for line in self.shell.queue.log or ["The log is empty."]:
                                ui.label(line)
                    with ui.tab_panel("changes"):
                        self.changes_list()
                    with ui.tab_panel("problems"):
                        self.problems_list()

    def changes_list(self) -> None:
        with ui.column().classes("w-full").props("data-control=changes-list"):
            groups = self.listed()
            if not groups:
                ui.label("No value is away from its default.")
            for item, found in groups:
                kind, name = item.split("/")
                ui.label(item).classes("rail-heading")
                for change in found:
                    mark = "◇" if change.kind == "override" else "◆"
                    other = "model" if change.kind == "override" else "default"
                    was = change.model if change.kind == "override" else change.default
                    with ui.row().classes("items-center no-wrap"):
                        ui.label(f"{mark} {change.path} = {change.value}").classes("changed")
                        ui.label(f"{other}: {'none' if was is None else was}").classes("muted")
                        ui.button(
                            "Reset",
                            on_click=lambda _, k=kind, n=name, p=change.path: self.reset(k, n, p),
                        ).props(
                            "flat dense no-caps data-control=reset "
                            f"aria-label='Reset {change.path}'"
                        )

    def reset(self, kind: str, name: str, path: str) -> None:
        project = self.shell.bench.project
        if project is None:
            return
        try:
            project.reset(kind, name, path)  # type: ignore[arg-type]
        except ValueError as error:
            ui.notify(str(error), type="negative")
            return
        self.shell.queue.log.append(f"reset {path} of {kind}/{name}")
        ui.navigate.to(f"/{self.suite}?panel=changes")

    def problems_list(self) -> None:
        bench = self.shell.bench
        project = bench.project
        with ui.column().classes("w-full").props("data-control=problems-list"):
            found = self.problems()
            if project is None and bench.refusal:
                ui.label(f"✕ refused: {bench.refusal}").classes("refused")
            elif not found:
                ui.label("No problem.")
            for problem in found:
                where = f" at {problem.path}" if problem.path else ""
                with (
                    ui.button(
                        on_click=lambda _, i=problem.item, s=problem.suite: self.open_item(i, s),
                    )
                    .props("flat dense no-caps data-control=problem-item")
                    .classes("w-full list-row")
                ):
                    ui.label(f"✕ refused: {problem.item}{where}: {problem.message}").classes(
                        "refused"
                    )

    def palette_dialog(self) -> None:
        with ui.dialog() as self.palette, ui.card().classes("palette"):
            self.palette_input = ui.input(
                placeholder="Type a command",
                on_change=lambda e: self.fill_palette(e.value or ""),
            ).props("autofocus outlined dense aria-label='Command' data-control=palette-input")
            self.palette_input.on("keydown.enter", self.first_match)
            with ui.column().classes("w-full gap-0").props("data-control=palette-list") as lst:
                self.palette_list = lst
        self.fill_palette("")


@contextmanager
def frame(
    shell: Shell,
    suite: Suite,
    *,
    panel: str | None = None,
    palette: bool = False,
    dialog: str | None = None,
) -> Iterator[None]:
    """Build the frame around a suite's page; the page's own content is the ``with`` body."""
    built = _Frame(shell, suite, panel)
    ui.add_head_html(
        '<script src="/frame.js"></script><link rel="stylesheet" href="/frame.css">'
        f"<script>window.frameChords = {theme.script_json(commands.chords(shell.keys))};"
        f"{theme.appearance(shell.settings)}</script>"
    )
    ui.on("command", built.on_command)
    with ui.element("div").classes("frame"):
        built.title_bar()
        with ui.element("div").classes("frame-main"):
            built.activity_bar()
            with ui.splitter(
                value=RAIL_FOLDED_PERCENT if built.rail_folded else built.layout.rail_percent,
                limits=RAIL_LIMITS,
                on_change=lambda: built.save_layout(),
            ).classes("frame-split") as built.outer:
                with built.outer.before:
                    built.rail()
                with built.outer.after:
                    with ui.splitter(
                        horizontal=True,
                        value=100.0 if built.bottom_folded else 100.0 - built.layout.bottom_percent,
                        limits=BOTTOM_LIMITS,
                        on_change=lambda: built.save_layout(),
                    ).classes("frame-split") as built.inner:
                        with built.inner.before:
                            with ui.element("div").classes("suite-main"):
                                yield
                        with built.inner.after:
                            built.bottom_panel()
        built.status_bar()
    built.palette_dialog()
    built.overlay.build()
    built.apply_layout()
    if palette:
        built.open_palette()
    if dialog == "settings":
        built.overlay.open()
