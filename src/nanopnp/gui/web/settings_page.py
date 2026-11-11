"""The settings page at ``/settings``: search, sections, whose values, and one row per setting."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal, Protocol

from nicegui import events, ui
from nicegui.elements.mixins.text_element import TextElement
from pydantic import JsonValue, ValidationError

from nanopnp.gui.web import commands, settings, theme
from nanopnp.gui.web.settings import SECTIONS, SETTINGS, Setting
from nanopnp.gui.web.shell import Shell
from nanopnp.io.store import StoreError

__all__ = ["Frame", "SettingsPage", "size_text"]

Scope = Literal["user", "project"]
SYSTEM = "system"
TOGGLE_MOST = 3
"""A list of at most this many choices is a toggle; a longer one is a select."""
COLOUR_NAMES = {
    "bg": "Background",
    "panel": "Panel",
    "sel": "Selection",
    "line": "Divider",
    "control-edge": "Control edge",
    "ink": "Text",
    "muted": "Quiet text",
    "accent": "Accent",
    "accent-ink": "Text on the accent",
    "focus": "Focus ring",
    "ok": "Done",
    "warn": "Warning",
    "err": "Error",
    "changed": "Changed mark",
    "canvas-3d": "3D view background",
    "canvas-3d-ink": "3D view text",
    "canvas-plot": "Plot background",
    "canvas-plot-ink": "Plot text",
}
"""Each theme colour's name on the page; the token's own name is the file's."""


class Frame(Protocol):
    """What the settings page asks of the frame around it."""

    def applied(self) -> None:
        """Apply the settings now held to the page: its look, its chords and its numbers."""

    def listen(self, event: str, handler: Callable[[events.GenericEventArguments], object]) -> None:
        """Route a page-wide event to ``handler``, replacing the last sub-page's."""


def size_text(size_bytes: int) -> str:
    """Return a size in bytes as the reader reads one: ``0 B``, ``12.3 MB``, ``1.05 GB``."""
    value = float(size_bytes)
    for unit in ("B", "kB", "MB", "GB"):
        if value < 1000 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.3g} {unit}"
        value /= 1000
    raise AssertionError("unreachable")


def _heading(text: str, level: int) -> TextElement:
    return TextElement(tag=f"h{level}", text=text).classes(f"heading heading-{level}")


class SettingsPage:
    """The settings page of one window; a change is checked, saved at once and applied."""

    def __init__(self, shell: Shell, frame: Frame, chosen: str = "") -> None:
        """Prepare the page; ``chosen`` names a setting to scroll to, as a palette command does."""
        self.shell = shell
        self.frame = frame
        self.chosen = chosen if chosen in SETTINGS else ""
        self.scope: Scope = "user"
        self.text = ""
        self.modified_only = False
        self.capturing: str | None = None
        self.body: ui.column
        self.keys_box: ui.column | None = None
        self.colours: ui.column | None = None
        self.clean_dialog: ui.dialog
        self.clean_message: ui.label
        self.clean_everything = False
        self.marks: dict[str, tuple[ui.label, ui.label, ui.button]] = {}

    # -- values in the chosen scope -----------------------------------------

    def _project_values(self) -> dict[str, JsonValue]:
        project = self.shell.bench.project
        return {} if project is None else dict(project.settings)

    def _shown(self, setting: Setting) -> JsonValue:
        # A project's own value, else the user's, which the project then inherits.
        if self.scope == "project" and setting.id in self._project_values():
            return self._project_values()[setting.id]
        return self.shell.settings.user.get(setting.id, setting.default)

    def _modified(self, setting: Setting) -> bool:
        if self.scope == "project":
            return setting.id in self._project_values()
        return setting.id in self.shell.settings.user

    def _write(self, setting: Setting, value: object) -> None:
        try:
            checked = setting.validate(value)
        except ValidationError as error:
            ui.notify(f"{setting.title}: {error.errors()[0]['msg']}", type="negative")
            return
        project = self.shell.bench.project
        if self.scope == "project" and project is not None and setting.per_project:
            project.save_setting(setting.id, checked)
            self.shell.settings = self.shell.settings.with_project(project.settings)
        else:
            self.shell.settings = self.shell.settings.with_user(setting.id, checked)
            settings.save(self.shell.settings)
        self.frame.applied()
        self._mark(setting, modified=self._modified(setting))

    def _reset(self, setting: Setting) -> None:
        project = self.shell.bench.project
        if self.scope == "project" and project is not None and setting.per_project:
            project.save_setting(setting.id, None)
            self.shell.settings = self.shell.settings.with_project(project.settings)
        else:
            self.shell.settings = self.shell.settings.without_user(setting.id)
            settings.save(self.shell.settings)
        self.frame.applied()
        self._refresh()

    # -- the page -----------------------------------------------------------

    def build(self) -> None:
        """Build the page: the section list and search beside the rows."""
        self.frame.listen("chord", self._on_chord)
        project = self.shell.bench.project
        with ui.row().classes("settings-page no-wrap w-full"):
            with (
                ui.element("nav")
                .classes("settings-nav column no-wrap")
                .props('aria-label="Settings sections" data-control=settings-sections')
            ):
                ui.input("Search settings", on_change=lambda e: self._search(e.value or "")).props(
                    "outlined dense clearable data-control=settings-search"
                )
                for identifier, title in SECTIONS.items():
                    ui.button(
                        title, on_click=lambda _, i=identifier: self._scroll_to(f"section-{i}")
                    ).props("flat dense no-caps").classes("list-row w-full")
            with ui.column().classes("settings-panel"):
                _heading("Settings", 1)
                with ui.row().classes("items-center"):
                    scope = ui.toggle(
                        {"user": "User", "project": "Project"},
                        value="user",
                        on_change=lambda e: self._choose_scope(e.value),
                    ).props('no-caps aria-label="Whose values" data-control=settings-scope')
                    if project is None:
                        scope.disable()
                        scope.props('title="Open a project to set its own values"')
                    ui.checkbox("Modified only", on_change=self._choose_modified).props(
                        "data-control=settings-modified"
                    )
                with ui.column().classes("w-full gap-2") as self.body:
                    pass
        self._clean_dialog_build()
        self._refresh()

    def _search(self, text: str) -> None:
        self.text = text
        self._refresh()

    def _choose_scope(self, scope: Scope) -> None:
        self.scope = scope
        self._refresh()

    def _choose_modified(self, event: events.ValueChangeEventArguments[bool | None]) -> None:
        self.modified_only = bool(event.value)
        self._refresh()

    def _scroll_to(self, html_id: str) -> None:
        ui.run_javascript(
            f"document.getElementById('{html_id}')?.scrollIntoView({{block: 'start'}})"
        )

    def _listed(self, setting: Setting) -> bool:
        if self.scope == "project" and not setting.per_project:
            return False
        if self.modified_only and not self._modified(setting):
            return False
        return setting in settings.search(self.text)

    def _refresh(self) -> None:
        self.keys_box = self.colours = None
        self.marks = {}
        self.body.clear()
        with self.body:
            shown = 0
            for identifier, title in SECTIONS.items():
                found = [s for s in settings.rows(identifier) if self._listed(s)]
                store = (
                    identifier == "runs"
                    and self.scope == "user"
                    and not self.text
                    and not self.modified_only
                )
                if not found and not store:
                    continue
                with (
                    ui.element("section")
                    .classes("settings-section w-full")
                    .props(f"id=section-{identifier}")
                ):
                    _heading(title, 2)
                    for setting in found:
                        self._row(setting)
                        shown += 1
                    if store:
                        self._store_block()
            if not shown:
                ui.label("No setting matches.").classes("muted").props("role=status")

    def _row(self, setting: Setting) -> None:
        modified = self._modified(setting)
        chosen = " setting-chosen" if setting.id == self.chosen else ""
        with (
            ui.element("div")
            .classes(f"setting-row w-full{chosen}")
            .props(f"id=setting-{setting.id} data-control=setting-{setting.id}")
        ):
            with ui.row().classes("items-center no-wrap gap-1"):
                mark = ui.label("◆").classes("changed mark").props("aria-hidden=true")
                _heading(setting.title, 3)
                word = ui.label("changed").classes("muted")
            ui.label(setting.description).classes("muted")
            if setting.applies != "at once":
                ui.label(f"Applies at the {setting.applies}.").classes("muted")
            if self.scope == "user" and self.shell.settings.source(setting.id) == "project":
                ui.label(
                    f"The open project sets this: {self.shell.settings.value(setting.id)}."
                ).classes("muted")
            self._control(setting)
            reset = ui.button(
                "Reset to default", on_click=lambda _, s=setting: self._reset(s)
            ).props(
                f'flat dense no-caps aria-label="Reset {setting.title}" '
                f"data-control=reset-{setting.id}"
            )
        self.marks[setting.id] = (mark, word, reset)
        self._mark(setting, modified=modified)

    def _mark(self, setting: Setting, *, modified: bool) -> None:
        # The mark, its word and the reset follow a write without rebuilding the row's control.
        for element in self.marks.get(setting.id, ()):
            element.style(f"visibility:{'visible' if modified else 'hidden'}")
        if setting.id in self.marks:
            self.marks[setting.id][2].set_visibility(modified)

    def _control(self, setting: Setting) -> None:
        value = self._shown(setting)
        control = f"settings-{setting.id}"
        if setting.id == "theme":
            self._theme_control(str(value))
        elif setting.id == "keys":
            with ui.column().classes("gap-1 w-full").props(f"data-control={control}") as box:
                self.keys_box = box
                self._fill_keys()
        elif setting.choices is not None and len(setting.choices) <= TOGGLE_MOST:
            ui.toggle(
                dict(setting.choices),
                value=value,
                on_change=lambda e, s=setting: self._write(s, e.value),
            ).props(f'no-caps aria-label="{setting.title}" data-control={control}')
        elif setting.choices is not None:
            ui.select(
                dict(setting.choices),
                value=value,
                label=setting.title,
                on_change=lambda e, s=setting: self._write(s, e.value),
            ).props(f"outlined dense data-control={control}")
        elif isinstance(setting.default, bool):
            ui.switch(
                setting.title,
                value=bool(value),
                on_change=lambda e, s=setting: self._write(s, e.value),
            ).props(f"data-control={control}")
        elif setting.id == "store_cap_gb":
            # A project's empty value is no value of its own: the user's cap then holds.
            ui.number(
                "Gigabytes; empty for no cap"
                if self.scope == "user"
                else "Gigabytes; empty for your own cap",
                value=value if isinstance(value, float | int) else None,
                on_change=lambda e, s=setting: self._write(s, e.value),
            ).props(f"outlined dense clearable debounce=600 data-control={control}")
        else:
            ui.number(
                setting.title,
                value=value if isinstance(value, float | int) else None,
                precision=0,
                on_change=lambda e, s=setting: self._write(
                    s, None if e.value is None else int(e.value)
                ),
            ).props(f"outlined dense debounce=600 data-control={control}")

    # -- the theme ----------------------------------------------------------

    def _theme_options(self) -> dict[str, str]:
        shipped = dict(SETTINGS["theme"].choices or {})
        return {**shipped, **{name: f"{name} (yours)" for name in theme.user_themes()}}

    def _theme_control(self, value: str) -> None:
        options = self._theme_options()
        ui.select(
            options,
            value=value if value in options else SYSTEM,
            label="Theme",
            on_change=lambda e: self._choose_theme(str(e.value)),
        ).props("outlined dense data-control=settings-theme")
        duplicate = ui.button("Duplicate this theme", on_click=self._duplicate).props(
            "flat dense no-caps data-control=theme-duplicate"
        )
        duplicate.set_enabled(value != SYSTEM)
        if value == SYSTEM:
            ui.label("Pick Light or Dark above to duplicate it.").classes("muted")
        with ui.expansion("Colours").props("data-control=theme-colours"):
            with ui.column().classes("gap-1") as self.colours:
                self._fill_colours()

    def _chosen_theme(self) -> theme.Theme:
        return theme.load(self.shell.settings.theme) or theme.shipped()["light"]

    def _choose_theme(self, name: str) -> None:
        self._write(SETTINGS["theme"], name)
        self._refresh()

    def _duplicate(self) -> None:
        copy = theme.duplicate(self._chosen_theme())
        self._write(SETTINGS["theme"], copy.name)
        self._refresh()

    def _edit_colour(self, name: str, token: str, value: str) -> None:
        if not theme.HEX.match(value):
            return
        own = theme.user_themes()[name]
        own.colours[token] = value
        theme.save(own)
        self.frame.applied()

    def _fill_colours(self) -> None:
        if self.shell.settings.theme == SYSTEM:
            ui.label("The system's choice of light or dark; pick one to see its colours.")
            return
        chosen = self._chosen_theme()
        editable = chosen.name not in theme.shipped()
        if not editable:
            ui.label("A shipped theme is read-only; duplicate it to change its colours.")
        for token, value in chosen.colours.items():
            with ui.row().classes("items-center no-wrap gap-2"):
                ui.element("span").classes("swatch").style(f"background:{value}").props(
                    "aria-hidden=true"
                )
                if editable:
                    ui.input(
                        COLOUR_NAMES.get(token, token),
                        value=value,
                        validation={"#rrggbb": lambda v: bool(theme.HEX.match(v))},
                        on_change=lambda e, n=chosen.name, t=token: self._edit_colour(
                            n, t, e.value
                        ),
                    ).props("dense outlined")
                else:
                    ui.label(f"{COLOUR_NAMES.get(token, token)} {value}")

    # -- the key bindings ---------------------------------------------------

    def _fill_keys(self) -> None:
        if self.keys_box is None:
            return
        chords = commands.bindings(self.shell.keys)
        self.keys_box.clear()
        with self.keys_box:
            for entry in commands.COMMANDS:
                with ui.row().classes("items-center no-wrap w-full"):
                    ui.label(entry.title).classes("key-title")
                    ui.button(
                        "Press a chord, or Escape to cancel"
                        if self.capturing == entry.id
                        else chords[entry.id] or "Unbound",
                        on_click=lambda _, i=entry.id: self._capture(i),
                    ).props(
                        f'flat dense no-caps data-control=key-{entry.id} aria-label="Rebind '
                        f'{entry.title}, now {chords[entry.id] or "unbound"}"'
                    ).classes("" if chords[entry.id] else "key-unbound")
                    if entry.id in self.shell.keys:
                        ui.button(
                            icon="close", on_click=lambda _, i=entry.id: self._clear_key(i)
                        ).props(f'flat dense round aria-label="Reset the chord of {entry.title}"')
            ui.button("Reset the keys", on_click=self._reset_keys).props("flat dense no-caps")

    def _capture(self, identifier: str) -> None:
        self.capturing = identifier
        ui.run_javascript("window.frame.capturing = true")
        self._fill_keys()

    def _on_chord(self, event: events.GenericEventArguments) -> None:
        identifier, self.capturing = self.capturing, None
        if identifier is None:
            return
        chord = str(event.args["chord"])
        if chord == "Escape":
            self._fill_keys()
            return
        why = commands.refusal(identifier, chord, self.shell.keys)
        if why is not None:
            ui.notify(why, type="negative")
        else:
            keys = {**self.shell.keys, identifier: chord}
            if chord == commands.command(identifier).shortcut:
                del keys[identifier]
            self._write(SETTINGS["keys"], keys)
        self._fill_keys()

    def _clear_key(self, identifier: str) -> None:
        self._write(SETTINGS["keys"], {k: v for k, v in self.shell.keys.items() if k != identifier})
        self._fill_keys()

    def _reset_keys(self) -> None:
        self._write(SETTINGS["keys"], {})
        self._fill_keys()

    # -- the store ----------------------------------------------------------

    def _store_block(self) -> None:
        project = self.shell.bench.project
        with ui.element("div").classes("setting-row w-full").props("id=setting-store"):
            _heading("The store", 3)
            if project is None:
                ui.label("Open a project to see its store.").classes("muted").props(
                    "data-control=store-usage"
                )
                return
            usage = project.store_usage(self.shell.bench.held)
            ui.label(
                f"The store holds {size_text(usage.total_bytes)} in {usage.entries} results; "
                f"the project's runs and this window keep {size_text(usage.kept_bytes)} of it."
            ).props("role=status data-control=store-usage")
            with ui.row():
                ui.button(
                    "Remove the unused results…", on_click=lambda: self._ask_clean(everything=False)
                ).props("outline no-caps data-control=store-clean-unused")
                ui.button(
                    "Remove every result…", on_click=lambda: self._ask_clean(everything=True)
                ).props("outline no-caps color=negative data-control=store-clean-all")

    def _clean_dialog_build(self) -> None:
        with (
            ui.dialog() as self.clean_dialog,
            ui.card().classes("dialog").props("data-control=store-clean"),
        ):
            _heading("Remove stored results?", 2)
            self.clean_message = ui.label("")
            with ui.row().classes("justify-end w-full"):
                ui.button("Cancel", on_click=self.clean_dialog.close).props(
                    "flat no-caps autofocus"
                )
                ui.button("Remove", on_click=self._clean).props(
                    "no-caps color=negative data-control=store-clean-accept"
                )

    def _ask_clean(self, *, everything: bool) -> None:
        project = self.shell.bench.project
        if project is None:
            return
        usage = project.store_usage(self.shell.bench.held)
        freed = usage.total_bytes if everything else usage.total_bytes - usage.kept_bytes
        what = (
            "Every stored result goes, and a run rebuilds what it next needs."
            if everything
            else "Every result no run, sweep or this window uses goes."
        )
        self.clean_everything = everything
        self.clean_message.text = f"{what} This frees about {size_text(freed)}."
        self.clean_dialog.open()

    def _clean(self) -> None:
        self.clean_dialog.close()
        project = self.shell.bench.project
        if project is None:
            return
        try:
            removed = project.clean_store(
                everything=self.clean_everything, holding=self.shell.bench.held
            )
        except (StoreError, OSError) as error:
            ui.notify(str(error), type="warning")
            return
        freed = sum(entry.size_bytes for entry in removed)
        said = f"removed {len(removed)} stored results, {size_text(freed)}"
        self.shell.queue.log.append(said)
        ui.notify(said[0].upper() + said[1:])
        self._refresh()
