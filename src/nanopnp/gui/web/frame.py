"""The workbench's frame: title bar, activity bar, project rail, bottom panel and their commands."""

from __future__ import annotations

import asyncio
import json
import os
import signal
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol
from urllib.parse import parse_qs, urlsplit

from nicegui import context, events, ui
from nicegui.elements.mixins.text_element import TextElement

from nanopnp.api.case import Case
from nanopnp.api.project import Problem, Project
from nanopnp.core.paths import recent_projects, remember_project
from nanopnp.core.public import __version__
from nanopnp.gui.web import commands, theme
from nanopnp.gui.web.builds import refusals
from nanopnp.gui.web.glossary import GLOSSARY
from nanopnp.gui.web.numbers import Style, shown
from nanopnp.gui.web.palette import Palette, options
from nanopnp.gui.web.screens import GROUPS, SUITES, tool_for
from nanopnp.gui.web.screens import Suite as SuiteScreen
from nanopnp.gui.web.settings_page import SettingsPage
from nanopnp.gui.web.shell import Shell
from nanopnp.gui.web.states import Workbench, cap_store
from nanopnp.io.case_paths import SEQUENCE_INDEX
from nanopnp.io.defaults import Change
from nanopnp.io.project import (
    BOTTOM_PX_LIMITS,
    ITEM_SUITES,
    RAIL_PX_LIMITS,
    ItemKind,
    Suite,
    SuiteLayout,
    split_reference,
)
from nanopnp.io.variables import field_unit

__all__ = ["Route", "Views", "current_suite", "frame", "heading", "listed_changes"]


@dataclass(frozen=True)
class Route:
    """One path of the workbench: the suite it belongs to, and the view the frame shows beside it.

    Parameters
    ----------
    suite
        The suite the path belongs to, or None for a page of no suite, such as the settings.
    view
        ``molecule`` for the Mol* host the frame owns, ``plane`` for its (r, z) canvas, each
        built once and never rebuilt; else None.
    """

    suite: Suite | None
    view: Literal["molecule", "plane"] | None = None


KINDS: tuple[tuple[ItemKind, str], ...] = (
    ("molecular", "Molecular models"),
    ("continuum", "Continuum models"),
    ("physics", "Physics models"),
    ("study", "Studies"),
    ("comparison", "Comparisons"),
)
PANELS = ("queue", "log", "changes", "problems")
DIALOGS = ("glossary", "about")
"""The dialogs ``?dialog=`` opens, by command."""
BAR_PX = 88
"""The activity bar's width; the drawer is the bar and the rail."""
FOLDED_BAR_PX = 48
"""The drawer's width folded: the suites' icons alone."""
RAIL_PX = RAIL_PX_LIMITS
BOTTOM_PX = BOTTOM_PX_LIMITS


def listed_changes(
    project: Project, refused: frozenset[str] = frozenset()
) -> list[tuple[str, tuple[Change, ...] | None]]:
    """Return each item's changed values, a study's own overrides but not its models' values.

    An item that does not load, or one of ``refused`` (``<kind>/<name>``, the items the problems
    list holds), is listed with None: its values are not counted.
    """
    listed: list[tuple[str, tuple[Change, ...] | None]] = []
    for kind, _ in KINDS:
        for name in project.items(kind):
            if f"{kind}/{name}" in refused:
                listed.append((f"{kind}/{name}", None))
                continue
            try:
                found = project.changes(kind, name)
                if kind == "study" and project.study(name).models_record is not None:
                    found = tuple(c for c in found if c.kind == "override")
            except Exception:  # an item that does not load is listed as a problem
                listed.append((f"{kind}/{name}", None))
                continue
            if found:
                listed.append((f"{kind}/{name}", found))
    return listed


def _unit(path: str) -> str | None:
    # The unit table names a sequence's fields at its first index.
    generic = ".".join(SEQUENCE_INDEX if part.isdigit() else part for part in path.split("."))
    try:
        return field_unit(generic)
    except KeyError:  # a leaf that takes no number
        return None


CHANGE_COLUMNS = [
    {"name": "mark", "label": "", "field": "mark", "align": "center"},
    {"name": "field", "label": "Field", "field": "field", "align": "left"},
    {"name": "value", "label": "Value", "field": "value", "align": "right"},
    {"name": "default", "label": "Default or model's", "field": "default", "align": "right"},
    {"name": "reset", "label": "", "field": "reset", "align": "right"},
]

# The table's body: a group row per item, a row per change, and one row for an item that does not
# load. The buttons report to the server through the table's own events.
CHANGE_BODY = r"""
<q-tr v-if="props.row.group" :props="props" class="group-row">
  <q-td colspan="100%"><span class="group-title">{{ props.row.item }}</span></q-td>
</q-tr>
<q-tr v-else-if="props.row.broken" :props="props">
  <q-td colspan="100%">
    <q-btn flat dense no-caps class="refused" :label="props.row.text"
      @click="() => $parent.$emit('problems')" />
  </q-td>
</q-tr>
<q-tr v-else :props="props">
  <q-td key="mark" :props="props">
    <span class="changed" aria-hidden="true">{{ props.row.mark }}</span>
    <span class="sr-only">{{ props.row.word }}</span>
  </q-td>
  <q-td key="field" :props="props">
    <q-btn flat dense no-caps :label="props.row.field" :title="'Open ' + props.row.field"
      @click="() => $parent.$emit('open', props.row)" />
  </q-td>
  <q-td key="value" :props="props" class="changed">{{ props.row.value }}</q-td>
  <q-td key="default" :props="props" class="muted">{{ props.row.default }}</q-td>
  <q-td key="reset" :props="props">
    <q-btn outline dense no-caps label="Reset" data-control="reset"
      :aria-label="'Reset ' + props.row.field + ' of ' + props.row.item"
      @click="() => $parent.$emit('reset', props.row)" />
  </q-td>
</q-tr>
"""


class Views(Protocol):
    """What a sub-page asks of the frame's view region."""

    async def show_molecule(self, scene_url: str | None, key: str = "") -> None:
        """Show the Mol* host, built once, with the scene at ``scene_url``; mark the screen ready.

        ``key`` names the structure the scene draws: the camera is kept while it stays the same.
        """

    async def show_plane(self, url: str | None, note: str = "") -> None:
        """Show the (r, z) canvas, built once, with the drawing at ``url``; mark the screen ready.

        With no address the canvas is empty but for ``note``; the view keeps its pan and zoom
        while the drawing's frame stays the same.
        """

    def changes_moved(self) -> None:
        """Count and list the changed values again, after a tool wrote one."""

    def queue_moved(self) -> None:
        """Show the queue's one line again, after a build started or ended."""

    def problems_moved(self) -> None:
        """Count and list the problems again, after a build was refused or its refusal answered."""

    async def reopen(self) -> None:
        """Build the open sub-page again, as if it were opened anew; the view region is kept."""

    async def settled(self) -> None:
        """Wait until what the address opened in the frame, such as the palette, has opened."""

    def applied(self) -> None:
        """Apply the settings now held to the page: its look, its chords and its numbers."""

    def listen(self, event: str, handler: Callable[[events.GenericEventArguments], object]) -> None:
        """Route a page-wide event to ``handler``, replacing the last sub-page's."""


class _Frame:
    def __init__(
        self, shell: Shell, routes: Mapping[str, Route], path: str, panel: str | None
    ) -> None:
        self.shell = shell
        self.routes = routes
        self.suite = self.route(path).suite or current_suite(shell)
        self.in_suite = self.route(path).suite is not None
        self.path = path
        self.layout = self.suite_layout(self.suite)
        if panel:
            self.layout = self.layout.model_copy(update={"bottom_folded": False})
        self.panel = panel if panel in PANELS else "queue"
        self.suite_buttons: dict[str, ui.button] = {}
        self.separators: dict[str, ui.element] = {}
        self.rail_box: ui.column
        self.changes_table: ui.table
        self.changed_label: ui.label
        self.queue_label: ui.label
        self.view: ui.element
        self.hosts: dict[str, ui.element] = {}
        self.drawer: ui.left_drawer
        self.tabs: ui.tabs
        self.dialog: ui.dialog
        self.palette: ui.dialog
        self.palette_select: Palette
        self.opening: asyncio.Event | None = None
        self.panel_root: ui.column
        self.listeners: dict[str, Callable[[events.GenericEventArguments], object]] = {}
        self.tree: ui.tree | None = None
        self.ask_dialog: ui.dialog
        self.ask_title: TextElement
        self.ask_input: ui.input
        self.ask_button: ui.button
        self.ask_then: Callable[[Path], object] = lambda _: None
        self.confirm_dialog: ui.dialog
        self.confirm_title: TextElement
        self.confirm_message: ui.label
        self.confirm_button: ui.button
        self.confirm_then: Callable[[], object] = lambda: None
        self.glossary_dialog: ui.dialog
        self.about_dialog: ui.dialog
        self._listed: list[tuple[str, tuple[Change, ...] | None]] | None = None
        self._problems: tuple[Problem, ...] | None = None
        self.fold_button: ui.button
        self.dark: ui.dark_mode
        self.toggle_button: ui.button
        self.actions: dict[str, Callable[[], object]] = {
            "palette": lambda: self.open_palette(),
            "settings": self.open_settings,
            "panel-toggle": self.toggle_panel,
            "changes": lambda: self.show_panel("changes"),
            "problems": lambda: self.show_panel("problems"),
            "layout-reset": lambda: self.confirm(
                "Reset the layout?",
                "Every suite's rail and panel go back to their first sizes.",
                "Reset layout",
                self.reset_layout,
            ),
            "project-new": lambda: self.ask("New project", "Folder", self.new_project),
            "project-open": lambda: self.ask("Open project", "Folder", self.open_project),
            "project-import": lambda: self.ask("Import case", "Case file", self.import_case),
            "project-export": lambda: self.ask("Export project", "Destination", self.export),
            "glossary": lambda: self.glossary_dialog.open(),
            "about": lambda: self.about_dialog.open(),
            "quit": self.ask_quit,
            **{f"suite-{suite.id}": self.go(f"/{suite.id}") for suite in SUITES},
        }

    # -- what the page shows of the project ---------------------------------

    # Loading every item is the costly part, so a page builds each list once.
    def listed(self) -> list[tuple[str, tuple[Change, ...] | None]]:
        project = self.shell.bench.project
        if self._listed is None:
            refused = frozenset(problem.item for problem in self.problems())
            self._listed = [] if project is None else listed_changes(project, refused)
        return self._listed

    def problems(self) -> tuple[Problem, ...]:
        project = self.shell.bench.project
        if self._problems is None:
            self._problems = () if project is None else (*project.problems(), *refusals(project))
        return self._problems

    # -- commands -----------------------------------------------------------

    def go(self, path: str) -> Callable[[], object]:
        return lambda: ui.navigate.to(path)

    def suite_path(self, suite: SuiteScreen) -> str:
        """Return where a suite's icon goes: its last tool used, else its first, else its page.

        A suite whose first tool has no page yet keeps its own page.
        """
        first = f"/{suite.id}/{suite.tools[0].id}" if suite.tools else ""
        if first not in self.routes:
            return f"/{suite.id}"
        last = f"/{suite.id}/{self.shell.last_tool.get(suite.id, '')}"
        return last if last in self.routes else first

    def reload_to(self, path: str) -> None:
        # A new project rebuilds the whole frame, so the browser loads the page afresh.
        ui.run_javascript(f"window.location.assign({json.dumps(path)})")

    # -- the path -----------------------------------------------------------

    def route(self, path: str) -> Route:
        bare = urlsplit(path).path.rstrip("/") or "/"
        found = self.routes.get(bare)
        if found is not None:
            return found
        return Route(current_suite(self.shell))

    def suite_layout(self, suite: Suite) -> SuiteLayout:
        project = self.shell.bench.project
        return project.layout.get(suite, SuiteLayout()) if project else SuiteLayout()

    def on_path(self, path: str) -> None:
        # A key capture begun on the settings page ends with it, or the next chord would be bound.
        ui.run_javascript(
            "document.body.dataset.screenReady = '0';"
            "if (window.frame) window.frame.capturing = false;"
        )
        route = self.route(path)
        self.path = path
        self.in_suite = route.suite is not None
        if route.suite is not None and route.suite != self.suite:
            self.suite = route.suite
            self.layout = self.suite_layout(route.suite).model_copy(
                update={"bottom_folded": self.layout.bottom_folded}
            )
            self.apply_layout()
            self.sync_separators()
        self.mark_suite()
        if route.view is None:
            self.view.set_visibility(False)
        query = parse_qs(urlsplit(path).query)
        if query.get("panel", [""])[0] in PANELS:
            self.show_panel(query["panel"][0])
        if query.get("palette"):
            self.open_palette(query["palette"][0])
        if query.get("dialog", [""])[0] in DIALOGS:
            self.run(query["dialog"][0])

    def mark_suite(self) -> None:
        # Each suite's state, which the folded bar shows beside its icon: a problem, else a build
        # of its model running.
        troubled = {problem.suite for problem in self.problems()}
        running = {entry.suite for entry in self.shell.queue.entries if entry.status == "running"}
        for identifier, button in self.suite_buttons.items():
            if self.in_suite and identifier == self.suite:
                button.props('aria-current="page"')
            else:
                button.props(remove="aria-current")
            title = next(suite.title for suite in SUITES if suite.id == identifier)
            state = (
                "problem" if identifier in troubled else "running" if identifier in running else ""
            )
            button.classes(remove="suite-problem suite-running")
            if state:
                button.classes(add=f"suite-{state}")
            said = {"problem": ", a problem", "running": ", a build running", "": ""}[state]
            button.props(f'title="{title}{said}" aria-label="{title}{said}"')

    def open_settings(self, setting: str = "") -> None:
        """Open the settings as a window over what is shown, at one setting where one is named."""
        if self.path.startswith("/settings"):
            return
        with ui.dialog() as dialog, ui.card().classes("settings-window"):
            ui.button(icon="sym_o_close", on_click=dialog.close).props(
                'flat dense aria-label="Close the settings" data-control=settings-close'
            ).classes("settings-close")
            SettingsPage(self.shell, self, setting).build()
        dialog.open()
        if setting:
            ui.timer(
                0.3,
                lambda: ui.run_javascript(
                    f"document.getElementById('setting-{setting}')?.scrollIntoView()"
                ),
                once=True,
            )

    def show_host(self, name: str) -> None:
        """Show the view region with one host in it, the other hidden but kept."""
        self.view.set_visibility(True)
        for host, element in self.hosts.items():
            element.set_visibility(host == name)

    async def show_molecule(self, scene_url: str | None, key: str = "") -> None:
        """Show the frame's Mol* host, built once, with a scene; mark the screen ready."""
        self.show_host("molecule")
        argument = "null" if scene_url is None else json.dumps(scene_url)
        # A long timeout: Mol* builds in seconds on a machine with no GPU.
        await ui.run_javascript(f"nano.scene({argument}, {json.dumps(key)})", timeout=60)

    async def show_plane(self, url: str | None, note: str = "") -> None:
        """Show the frame's (r, z) canvas, built once, with a drawing; mark the screen ready."""
        self.show_host("plane")
        argument = "null" if url is None else json.dumps(url)
        await ui.run_javascript(f"nano.plane({argument}, {json.dumps(note)})", timeout=60)

    def queue_moved(self) -> None:
        """Show the queue's one line again, after a build started or ended."""
        self.queue_label.text = self.shell.queue.status_line()
        self.mark_suite()

    async def reopen(self) -> None:
        """Build the open sub-page again, as if it were opened anew; the view region is kept."""
        await context.client.sub_pages_router.refresh()

    def problems_moved(self) -> None:
        """Count and list the problems again, after a build was refused or its refusal answered."""
        self._problems = None
        text = self.problems_text()
        if text == self.problems_button.text:
            return
        self.problems_button.text = text
        found = bool(self.problems())
        self.problems_button.classes(
            add="state-err" if found else "state-ok", remove="state-ok" if found else "state-err"
        )
        self.problems_box.clear()
        with self.problems_box:
            self.problem_rows()
        self.mark_suite()

    def changes_moved(self) -> None:
        """Count and list the changed values again, after a tool wrote one."""
        self._listed = None
        self._problems = None
        self.changed_label.text = self.changed_text(self.changed_count())
        rows = self.change_rows()
        self.changes_table.rows = rows
        self.changes_table.update()
        self.changes_lines.clear()
        with self.changes_lines:
            self.change_lines(rows)

    def run(self, identifier: str) -> None:
        if identifier.startswith(commands.SETTING_COMMAND):
            setting = identifier.removeprefix(commands.SETTING_COMMAND)
            self.open_settings(setting)
            return
        action = self.actions.get(identifier)
        if action is None:
            ui.notify(f"{commands.command(identifier).title} is not available yet")
            return
        action()

    def applied(self) -> None:
        """Apply the settings now held to the page: its look, its chords and its numbers."""
        chords = theme.script_json(commands.chords(self.shell.keys))
        ui.run_javascript(
            f"{theme.appearance(self.shell.settings)}window.frameChords = {chords};"
            "window.nano && window.nano.background();"
        )
        self.dark.set_value(theme.dark(self.shell.settings))
        # The changed table is built once per window, so the figures and number style reach it here.
        self.changes_table.rows = self.change_rows()
        self.changes_table.update()

    def listen(self, event: str, handler: Callable[[events.GenericEventArguments], object]) -> None:
        """Route a page-wide event to ``handler``, replacing the last sub-page's."""
        # ui.on subscribes the whole page, so a sub-page's own subscription would outlive it.
        if event not in self.listeners:
            ui.on(event, lambda e, name=event: self.listeners[name](e))
        self.listeners[event] = handler

    def on_command(self, event: events.GenericEventArguments) -> None:
        self.run(str(event.args["id"]))

    # -- the project's own commands ----------------------------------------

    def ask(self, title: str, label: str, then: Callable[[Path], object]) -> None:
        self.ask_title.text = title
        self.ask_input.label = label
        self.ask_input.value = ""
        self.ask_button.text = title
        self.ask_then = then
        self.ask_dialog.open()

    def accept(self) -> None:
        text = (self.ask_input.value or "").strip()
        # An empty field would read as the server's own folder.
        if not text:
            ui.notify(f"Type a {self.ask_input.label.lower()} first", type="warning")
            return
        try:
            self.ask_then(Path(text).expanduser())
        except (ValueError, OSError) as error:
            ui.notify(str(error), type="negative")
            return
        self.ask_dialog.close()

    def confirm(self, title: str, message: str, action: str, then: Callable[[], object]) -> None:
        if self.shell.settings.value("confirm") is False:
            then()
            return
        self.confirm_title.text = title
        self.confirm_message.text = message
        self.confirm_button.text = action
        self.confirm_then = then
        self.confirm_dialog.open()

    def confirmed(self) -> None:
        self.confirm_dialog.close()
        self.confirm_then()

    def ask_quit(self) -> None:
        running = [e.label for e in self.shell.queue.entries if e.status == "running"]
        message = "The workbench stops, and its page with it."
        if running:
            message += f" Running now, and stopped with it: {', '.join(running)}."
        self.confirm("Quit the workbench?", message, "Quit", self.quit)

    def quit(self) -> None:
        os.kill(os.getpid(), signal.SIGTERM)

    def switch(self, project: Project) -> None:
        self.shell.bench = Workbench(project.name, project=project, queue=self.shell.queue)
        remember_project(project.root)
        cap_store(project)
        self.reload_to("/molecular")

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
        self.reload_to("/study")

    def export(self, destination: Path) -> None:
        project = self.shell.bench.project
        if project is None:
            raise ValueError("open or create a project first")
        written = project.export(destination)
        self.shell.queue.log.append(f"exported the project to {written}")
        ui.notify(f"Exported to {written}")

    # -- the layout ---------------------------------------------------------

    def save_layout(self) -> None:
        project = self.shell.bench.project
        if project is not None:
            project.save_layout(self.suite, self.layout)

    def drawer_width(self) -> int:
        return BAR_PX + self.layout.rail_px

    def apply_layout(self) -> None:
        self.drawer.props(f"width={self.drawer_width()} mini-width={FOLDED_BAR_PX}")
        if self.layout.rail_folded:
            self.drawer.props("mini")
        else:
            self.drawer.props(remove="mini")
        self.panel_root.style(f"height:{self.layout.bottom_px}px")
        self.panel_root.set_visibility(not self.layout.bottom_folded)
        expanded = str(not self.layout.rail_folded).lower()
        self.fold_button.props(f"aria-expanded={expanded}")
        self.fold_button.props(
            f"icon={'chevron_left' if not self.layout.rail_folded else 'chevron_right'}"
        )
        self.toggle_button.props(f"aria-expanded={str(not self.layout.bottom_folded).lower()}")

    def sync_separators(self) -> None:
        # A drag starts from the separator's own value, so a suite's or a reset's sizes reach it.
        for name, value in (("rail", self.layout.rail_px), ("panel", self.layout.bottom_px)):
            if name in self.separators:
                self.separators[name].props(f"aria-valuenow={value}")

    def on_separator(self, event: events.GenericEventArguments) -> None:
        name, value, done = str(event.args["name"]), int(event.args["value"]), event.args["done"]
        if name == "rail":
            low, high = RAIL_PX
            self.layout = self.layout.model_copy(update={"rail_px": min(max(value, low), high)})
        elif name == "panel":
            low, high = BOTTOM_PX
            self.layout = self.layout.model_copy(update={"bottom_px": min(max(value, low), high)})
        else:
            return
        self.apply_layout()
        # Saved on release only: a drag is many steps, and the project file is written once.
        if done:
            self.save_layout()

    def fold_rail(self) -> None:
        self.layout = self.layout.model_copy(update={"rail_folded": not self.layout.rail_folded})
        self.apply_layout()
        self.save_layout()

    def toggle_panel(self) -> None:
        self.layout = self.layout.model_copy(
            update={"bottom_folded": not self.layout.bottom_folded}
        )
        self.apply_layout()
        self.save_layout()

    def show_panel(self, name: str) -> None:
        self.tabs.value = name
        if self.layout.bottom_folded:
            self.toggle_panel()

    def reset_layout(self) -> None:
        self.layout = SuiteLayout(bottom_folded=self.layout.bottom_folded)
        self.apply_layout()
        self.sync_separators()
        project = self.shell.bench.project
        if project is not None:
            # The suite shown keeps its panel open or folded, as the window shows it.
            for suite in SUITES:
                project.save_layout(
                    suite.id, self.layout if suite.id == self.suite else SuiteLayout()
                )

    # -- the palette --------------------------------------------------------

    def open_palette(self, text: str = "") -> None:
        has_project = self.shell.bench.project is not None
        self.palette_select.prepare(options(self.shell.keys, has_project=has_project), text)
        self.palette.open()

    def choose(self, identifier: str) -> None:
        self.palette.close()
        self.run(identifier)

    # -- the pieces ---------------------------------------------------------

    def title_bar(self) -> None:
        changed = self.changed_count()
        chords = commands.bindings(self.shell.keys)
        with ui.row().classes("titlebar items-center no-wrap"):
            for menu in commands.MENUS:
                with ui.button(menu.capitalize()).props(f"flat no-caps data-control=menu-{menu}"):
                    with ui.menu():
                        section: str | None = None
                        for entry in commands.COMMANDS:
                            if entry.menu != menu:
                                continue
                            if section is not None and entry.section != section:
                                ui.separator()
                            section = entry.section
                            chord = chords[entry.id]
                            with ui.menu_item(on_click=lambda i=entry.id: self.run(i)):
                                ui.item_section(entry.title)
                                if chord:
                                    ui.item_section(chord).props("side")
            ui.space()
            with ui.button(on_click=lambda: self.run("changes")).props(
                "flat no-caps aria-live=polite data-control=changed-count"
            ):
                # With no project open there is nothing to count, so no mark and no number.
                if self.shell.bench.project is not None:
                    ui.label("◆").classes("changed").props("aria-hidden=true")
                self.changed_label = ui.label(self.changed_text(changed))
            ui.button(
                f"Command palette  {chords['palette']}".rstrip(), on_click=self.open_palette
            ).props("flat no-caps data-control=palette-open")

    def activity_bar(self) -> None:
        with (
            ui.element("nav")
            .classes("activitybar column items-center")
            .props('aria-label="Suites"')
        ):
            for group, title in GROUPS.items():
                with (
                    ui.element("div")
                    .classes("suite-group")
                    .props(f'role=group aria-label="{title}"')
                ):
                    ui.label(title).classes("suite-group-title").props("aria-hidden=true")
                    for suite in SUITES:
                        if suite.group != group:
                            continue
                        self.suite_buttons[suite.id] = (
                            ui.button(
                                suite.title,
                                icon=suite.icon,
                                on_click=lambda _, s=suite: ui.navigate.to(self.suite_path(s)),
                            )
                            .props(f"flat no-caps stack data-control=suite-{suite.id}")
                            .classes("suite-button")
                        )
        self.mark_suite()

    def separator(self, name: str, *, vertical: bool, value: int, limits: tuple[int, int]) -> None:
        label = "Resize the project rail" if vertical else "Resize the bottom panel"
        self.separators[name] = ui.element("div").classes(
            f"separator separator-{'vertical' if vertical else 'horizontal'}"
        )
        self.separators[name].props(
            f"role=separator tabindex=0 data-separator={name} "
            f"aria-orientation={'vertical' if vertical else 'horizontal'} "
            f"aria-valuemin={limits[0]} aria-valuemax={limits[1]} aria-valuenow={value} "
            f'aria-label="{label}" data-control=separator-{name}'
        )

    def rail(self) -> None:
        with (
            ui.element("nav")
            .classes("rail column no-wrap gap-1")
            .props('aria-label="Project" data-control=rail')
        ):
            self.fold_button = ui.button(on_click=self.fold_rail).props(
                "flat dense aria-label='Fold the project rail' data-control=rail-fold"
            )
            with ui.column().classes("w-full gap-1") as self.rail_box:
                self.rail_items()

    def rail_items(self) -> None:
        project = self.shell.bench.project
        with ui.column().classes("q-mini-drawer-hide w-full gap-1"):
            if project is None:
                self.no_project()
                return
            nodes = [
                {
                    "id": "project",
                    "label": project.name,
                    "selectable": False,
                    "children": [
                        {
                            "id": kind,
                            "label": title,
                            "selectable": False,
                            "children": [
                                {"id": f"{kind}/{name}", "label": name}
                                for name in project.items(kind)
                            ],
                        }
                        for kind, title in KINDS
                    ],
                }
            ]
            self.tree = (
                ui.tree(nodes, on_select=self.on_tree)
                .props("dense no-transition")
                .props('aria-label="Project items" data-control=rail-tree')
                .classes("rail-tree w-full")
            )
            self.tree.expand()
            if project.current:
                self.tree.select(project.current)

    def no_project(self) -> None:
        heading("No project open", 2).classes("rail-heading")
        for identifier in ("project-new", "project-open"):
            ui.button(commands.command(identifier).title, on_click=self.actions[identifier]).props(
                f"flat dense no-caps data-control={identifier}"
            ).classes("list-row w-full")
        recent = recent_projects(int(str(self.shell.settings.value("recent_projects"))))
        if not recent:
            return
        heading("Recent projects", 2).classes("rail-heading")
        with ui.element("ul").classes("plain-list w-full").props("data-control=recent-projects"):
            for folder in recent:
                with ui.element("li"):
                    ui.button(folder.name, on_click=lambda _, f=folder: self.open_recent(f)).props(
                        f'flat dense no-caps title="{folder}"'
                    ).classes("list-row w-full")

    def open_recent(self, folder: Path) -> None:
        # A recent folder may no longer hold a project of this release.
        try:
            self.open_project(folder)
        except (ValueError, OSError) as error:
            ui.notify(str(error), type="negative")

    def on_tree(self, event: events.ValueChangeEventArguments[str | None]) -> None:
        item = event.value
        if not item or "/" not in item:
            return
        kind, _ = split_reference(item)
        self.open_item(item, ITEM_SUITES[kind])

    def open_item(self, item: str, suite: str) -> None:
        project = self.shell.bench.project
        if project is not None and project.current != item:
            project.open_item(item)
            self.rail_box.clear()
            with self.rail_box:
                self.rail_items()
        ui.navigate.to(f"/{suite}")

    def status_bar(self) -> None:
        problems = self.problems_count()
        with ui.row().classes("statusbar items-center no-wrap"):
            self.queue_label = ui.label(self.shell.queue.status_line()).props(
                "role=status data-control=queue-status"
            )
            ui.space()
            self.toggle_button = ui.button("Queue and log", on_click=self.toggle_panel).props(
                "flat dense no-caps data-control=panel-toggle"
            )
            self.problems_button = (
                ui.button(self.problems_text(), on_click=lambda: self.run("problems"))
                .props("flat dense no-caps aria-live=polite data-control=problems-count")
                .classes("state-err" if problems else "state-ok")
            )

    def problems_count(self) -> int:
        bench = self.shell.bench
        return len(self.problems()) or (1 if bench.project is None and bench.refusal else 0)

    def problems_text(self) -> str:
        problems = self.problems_count()
        if not problems:
            return "✓ No problems"
        return f"✕ {problems} problem{'' if problems == 1 else 's'}"

    def bottom_panel(self) -> None:
        with ui.column().classes("bottom-panel w-full gap-0") as self.panel_root:
            self.separator("panel", vertical=False, value=self.layout.bottom_px, limits=BOTTOM_PX)
            with ui.tabs().props("align=left no-caps dense").classes("w-full") as self.tabs:
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

    def changed_text(self, changed: int) -> str:
        return f"{changed} changed" if self.shell.bench.project is not None else "No project"

    def changed_count(self) -> int:
        return sum(len(found) for _, found in self.listed() if found is not None)

    def change_rows(self) -> list[dict[str, object]]:
        figures = int(str(self.shell.settings.value("significant_figures")))
        style: Style = (
            "powers" if self.shell.settings.value("number_style") == "powers" else "prefixes"
        )
        rows: list[dict[str, object]] = []
        for item, found in self.listed():
            rows.append({"key": item, "group": True, "item": item})
            if found is None:
                text = "not counted: it does not load; open Problems"
                rows.append({"key": f"{item}#broken", "broken": True, "item": item, "text": text})
                continue
            for change in found:
                unit = _unit(change.path)
                was = change.model if change.kind == "override" else change.default
                rows.append(
                    {
                        "key": f"{item}#{change.path}",
                        "item": item,
                        "field": change.path,
                        "mark": "◇" if change.kind == "override" else "◆",
                        "word": "override" if change.kind == "override" else "changed",
                        "value": shown(change.value, unit, figures=figures, style=style),
                        "default": shown(was, unit, figures=figures, style=style),
                    }
                )
        return rows

    def changes_list(self) -> None:
        # The changed values a line each, or as the table: the author tries the shorter list
        # beside the table.
        rows = self.change_rows()
        with ui.column().classes("w-full gap-0").props("data-control=changes-list"):
            ui.toggle(
                {"list": "List", "table": "Table"},
                value=self.shell.changes_view,
                on_change=lambda e: self.show_changes_as(str(e.value)),
            ).props('dense no-caps aria-label="Show the changes as" data-control=changes-view')
            self.changes_lines = (
                ui.column()
                .classes("changes-lines w-full gap-0")
                .props("data-control=changes-lines")
            )
            with self.changes_lines:
                self.change_lines(rows)
            self.changes_table = (
                ui.table(
                    columns=CHANGE_COLUMNS, rows=rows, row_key="key", pagination={"rowsPerPage": 0}
                )
                .props(
                    "dense flat hide-pagination wrap-cells data-control=changes-table "
                    'no-data-label="No value is away from its default."'
                )
                .classes("changes-table w-full")
            )
        self.changes_table.add_slot("body", CHANGE_BODY)
        self.changes_table.on("reset", self.on_reset)
        self.changes_table.on("open", self.on_open_field)
        self.changes_table.on("problems", lambda: self.show_panel("problems"))
        self.show_changes_as(self.shell.changes_view)

    def show_changes_as(self, view: str) -> None:
        self.shell.changes_view = view if view in ("list", "table") else "list"
        self.changes_lines.set_visibility(self.shell.changes_view == "list")
        self.changes_table.set_visibility(self.shell.changes_view == "table")

    def change_lines(self, rows: list[dict[str, object]]) -> None:
        if not any("field" in row or row.get("broken") for row in rows):
            ui.label("No value is away from its default.").classes("muted")
        for row in rows:
            item = str(row["item"])
            if row.get("broken"):
                ui.button(
                    f"✕ {item}: {row['text']}", on_click=lambda: self.show_panel("problems")
                ).props("flat dense no-caps align=left").classes("changes-line refused")
                continue
            if row.get("group"):
                continue
            path = str(row["field"])
            kind, name = split_reference(item)
            with ui.row().classes("changes-line items-center no-wrap w-full"):
                ui.label(str(row["mark"])).classes("changed").props("aria-hidden=true")
                ui.button(
                    path, on_click=lambda _, i=item, f=path: self.open_field(i, f), color=None
                ).props(
                    f'flat dense no-caps title="Open {path}" data-control=changes-line'
                ).classes("changes-field")
                ui.label(f"{row['value']}").classes("changed changes-value")
                was = (
                    f"the model's {row['default']}, overridden"
                    if row["word"] == "override"
                    else f"default {row['default']}"
                )
                ui.label(was).classes("muted")
                ui.space()
                ui.label(item).classes("muted changes-item")
                ui.button(
                    "Reset", on_click=lambda _, k=kind, n=name, f=path: self.ask_reset(k, n, f)
                ).props(
                    f'flat dense no-caps data-control=reset aria-label="Reset {path} of {item}"'
                )

    def on_reset(self, event: events.GenericEventArguments) -> None:
        kind, name = split_reference(str(event.args["item"]))
        self.ask_reset(kind, name, str(event.args["field"]))

    def on_open_field(self, event: events.GenericEventArguments) -> None:
        self.open_field(str(event.args["item"]), str(event.args["field"]))

    def open_field(self, item: str, field: str) -> None:
        kind, _ = split_reference(item)
        project = self.shell.bench.project
        if project is not None and project.current != item:
            project.open_item(item)
            self.rail_box.clear()
            with self.rail_box:
                self.rail_items()
        suite = ITEM_SUITES[kind]
        tool = tool_for(suite, field)
        page = f"/{suite}/{tool.id}" if tool is not None else f"/{suite}"
        ui.navigate.to(f"{page if page in self.routes else f'/{suite}'}?field={field}")

    def ask_reset(self, kind: str, name: str, path: str) -> None:
        self.confirm(
            f"Reset {path}?",
            f"{kind}/{name} goes back to the default of {path}.",
            "Reset",
            lambda: self.reset(kind, name, path),
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
        self.changes_moved()

    def problems_list(self) -> None:
        self.problems_box = ui.column().classes("w-full").props("data-control=problems-list")
        with self.problems_box:
            self.problem_rows()

    def problem_rows(self) -> None:
        bench = self.shell.bench
        found = self.problems()
        if bench.project is None and bench.refusal:
            ui.label(f"✕ blocked: {bench.refusal}").classes("refused")
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
                ui.label(f"✕ blocked: {problem.item}{where}: {problem.message}").classes("refused")

    def dialogs(self) -> None:
        recent = recent_projects(int(str(self.shell.settings.value("recent_projects"))))
        with (
            ui.dialog() as self.ask_dialog,
            ui.card().classes("dialog").props("data-control=ask"),
        ):
            self.ask_title = heading("", 2)
            self.ask_input = ui.input("Folder").props(
                "autofocus outlined dense data-control=ask-input"
            )
            self.ask_input.on("keydown.enter", self.accept)
            if recent:
                ui.label("Recent projects").classes("muted")
                with ui.element("ul").classes("plain-list w-full"):
                    for folder in recent:
                        with ui.element("li"):
                            ui.button(
                                str(folder),
                                on_click=lambda _, f=folder: self.ask_input.set_value(str(f)),
                            ).props("flat dense no-caps").classes("list-row w-full")
            with ui.row().classes("justify-end w-full"):
                ui.button("Cancel", on_click=self.ask_dialog.close).props("flat no-caps")
                self.ask_button = ui.button("", on_click=self.accept).props("no-caps")
        with (
            ui.dialog() as self.confirm_dialog,
            ui.card().classes("dialog").props("data-control=confirm"),
        ):
            self.confirm_title = heading("", 2)
            self.confirm_message = ui.label("")
            with ui.row().classes("justify-end w-full"):
                ui.button("Cancel", on_click=self.confirm_dialog.close).props(
                    "flat no-caps autofocus"
                )
                self.confirm_button = ui.button("", on_click=self.confirmed).props(
                    "no-caps color=negative data-control=confirm-accept"
                )
        with (
            ui.dialog() as self.glossary_dialog,
            ui.card().classes("dialog glossary").props("data-control=glossary"),
        ):
            heading("Glossary", 2)
            with ui.element("dl").classes("glossary-list").props('tabindex=0 aria-label="Terms"'):
                for term, meaning in GLOSSARY:
                    TextElement(tag="dt", text=term).classes("glossary-term")
                    TextElement(tag="dd", text=meaning).classes("glossary-meaning")
            ui.button("Close", on_click=self.glossary_dialog.close).props("flat no-caps").classes(
                "self-end"
            )
        with (
            ui.dialog() as self.about_dialog,
            ui.card().classes("dialog").props("data-control=about"),
        ):
            heading("About nanopnp", 2)
            ui.label(f"Version {__version__}")
            ui.label(
                "The ePNP-NS model of biological nanopores, from structure to current, "
                "without COMSOL."
            )
            ui.label("Open source under the BSD 3-Clause licence.").classes("muted")
            ui.button("Close", on_click=self.about_dialog.close).props("flat no-caps").classes(
                "self-end"
            )

    def palette_dialog(self) -> None:
        with ui.dialog() as self.palette, ui.card().classes("palette"):
            self.palette_select = Palette(self.choose).classes("w-full")
        self.palette.on("show", self.palette_shown)

    async def palette_shown(self) -> None:
        await self.palette_select.run_method("type")
        if self.opening is not None:
            self.opening.set()

    async def settled(self) -> None:
        """Wait until what the address opened in the frame, such as the palette, has opened."""
        if self.opening is not None:
            # A long timeout: the page reports itself ready anyway rather than never.
            with suppress(TimeoutError):
                await asyncio.wait_for(self.opening.wait(), timeout=20)
            self.opening = None


@contextmanager
def frame(
    shell: Shell,
    routes: Mapping[str, Route],
    *,
    panel: str | None = None,
    palette: str | None = None,
    dialog: str | None = None,
) -> Iterator[Views]:
    """Build the frame once for the page; the ``with`` body builds the sub-pages it routes.

    The frame follows the path as the sub-pages change it: the current suite, its layout and
    the view region beside the sub-page.
    """
    router = context.client.sub_pages_router
    project = shell.bench.project
    # The project's values over the user's, as the project file holds them now.
    shell.settings = shell.settings.with_project(project.settings if project else {})
    built = _Frame(shell, routes, router.current_path, panel)
    ui.add_head_html(
        '<script src="/frame.js"></script><link rel="stylesheet" href="/frame.css">'
        f"<script>window.frameChords = {theme.script_json(commands.chords(shell.keys))};"
        f"{theme.appearance(shell.settings)}</script>"
    )
    colours()
    built.dark = ui.dark_mode(theme.dark(shell.settings))
    ui.on("command", built.on_command)
    ui.on("separator", built.on_separator)
    with ui.header(elevated=False).classes("frame-header q-pa-none"):
        built.title_bar()
    with (
        ui.left_drawer(value=True, fixed=True)
        .classes("frame-drawer q-pa-none")
        .props("behavior=desktop persistent") as built.drawer
    ):
        with ui.element("div").classes("drawer-row"):
            built.activity_bar()
            built.rail()
        built.separator("rail", vertical=True, value=built.layout.rail_px, limits=RAIL_PX)
    with ui.footer(elevated=False).classes("frame-footer q-pa-none column no-wrap"):
        built.bottom_panel()
        built.status_bar()
    with ui.element("div").classes("main-row suite-main") as main:
        # The view region: one Mol* host and one (r, z) canvas, outside the sub-pages, so a route
        # change keeps them.
        with ui.element("div").classes("view-region") as built.view:
            built.hosts["molecule"] = ui.element("div").props("id=mol data-control=molecule")
            built.hosts["plane"] = ui.element("div").props("id=plane data-control=plane")
        built.view.set_visibility(False)
        with ui.element("div").classes("sub-page"):
            yield built
    # A stable target outside the sub-pages, which a route change does not rebuild.
    ui.skip_link("Skip to the suite", target=main)
    ui.page_title(project.name if project is not None else "nanopnp workbench")
    router.on_path_changed(built.on_path)
    built.dialogs()
    built.palette_dialog()
    built.apply_layout()
    if palette:
        built.opening = asyncio.Event()
        built.open_palette(palette)
    if dialog in DIALOGS:
        built.run(dialog)


def heading(text: str, level: int) -> TextElement:
    """Return a heading of this level, ``h1`` to ``h6``, in the frame's type scale."""
    return TextElement(tag=f"h{level}", text=text).classes(f"heading heading-{level}")


def current_suite(shell: Shell) -> Suite:
    """Return the suite of the project's current item, Molecular where none is open."""
    current = shell.bench.project.current if shell.bench.project else None
    try:
        kind, _ = split_reference(current or "")
    except ValueError:
        return "molecular"
    return ITEM_SUITES[kind]


def colours() -> None:
    """Point Quasar's colour variables at the theme's tokens, so every component takes them."""
    ui.colors(
        primary="var(--accent)",
        secondary="var(--muted)",
        accent="var(--accent)",
        dark="var(--panel)",
        dark_page="var(--bg)",
        positive="var(--ok)",
        negative="var(--err)",
        info="var(--accent)",
        warning="var(--warn)",
    )
