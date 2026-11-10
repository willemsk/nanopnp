"""The settings overlay: theme, density, spacing, the 3D view's background and the key bindings."""

from __future__ import annotations

import json
from collections.abc import Callable

from nicegui import events, ui

from nanopnp.gui.web import commands, settings, theme
from nanopnp.gui.web.shell import Shell

__all__ = ["Overlay"]

SYSTEM = "system"
FOLLOW = {SYSTEM: "Follow the system", "light": "Light", "dark": "Dark"}
DENSITIES = {"medium": "Medium", "compact": "Compact"}
SPACINGS = {"default": "Default", "tight": "Tight"}
BACKGROUNDS = {"near-black": "Near-black", "theme": "The theme's", "white": "White"}


class Overlay:
    """The settings dialog of one page; a change is saved at once and applied to the page."""

    def __init__(self, shell: Shell) -> None:
        self.shell = shell
        self.applied: Callable[[], object] = lambda: None
        self.capturing: str | None = None
        self.dialog: ui.dialog
        self.theme_select: ui.select
        self.duplicate_button: ui.button
        self.duplicate_hint: ui.label
        self.colours: ui.column
        self.keys: ui.column

    def open(self) -> None:
        """Show the dialog."""
        self.dialog.open()

    # -- the settings -------------------------------------------------------

    def _change(self, **fields: object) -> None:
        current = self.shell.settings
        for identifier, value in fields.items():
            current = current.with_user(identifier, value)
        self.shell.settings = current
        settings.save(current)
        ui.run_javascript(theme.appearance(self.shell.settings))
        self.applied()

    def _options(self) -> dict[str, str]:
        return {**FOLLOW, **{name: f"{name} (yours)" for name in theme.user_themes()}}

    def _chosen(self) -> theme.Theme:
        return theme.load(self.shell.settings.theme) or theme.shipped()["light"]

    def _choose_theme(self, name: str) -> None:
        self._change(theme=name)
        self.duplicate_button.set_enabled(name != SYSTEM)
        self.duplicate_hint.set_visibility(name == SYSTEM)
        self._fill_colours()

    def _duplicate(self) -> None:
        copy = theme.duplicate(self._chosen())
        self.theme_select.set_options(self._options(), value=copy.name)
        self._change(theme=copy.name)
        self._fill_colours()

    def _edit_colour(self, name: str, token: str, value: str) -> None:
        if not theme.HEX.match(value):
            return
        own = theme.user_themes()[name]
        own.colours[token] = value
        theme.save(own)
        ui.run_javascript(theme.appearance(self.shell.settings))

    def _fill_colours(self) -> None:
        self.colours.clear()
        with self.colours:
            if self.shell.settings.theme == SYSTEM:
                ui.label("The system's choice of light or dark; pick one to see its colours.")
                return
            chosen = self._chosen()
            editable = chosen.name not in theme.shipped()
            if not editable:
                ui.label("A shipped theme is read-only; duplicate it to change its colours.")
            for token, value in chosen.colours.items():
                if editable:
                    ui.input(
                        token,
                        value=value,
                        validation={"#rrggbb": lambda v: bool(theme.HEX.match(v))},
                        on_change=lambda e, n=chosen.name, t=token: self._edit_colour(
                            n, t, e.value
                        ),
                    ).props("dense outlined")
                else:
                    ui.label(f"{token} {value}")

    # -- the key bindings ---------------------------------------------------

    def _fill_keys(self) -> None:
        chords = commands.bindings(self.shell.keys)
        self.keys.clear()
        with self.keys:
            for entry in commands.COMMANDS:
                with ui.row().classes("items-center no-wrap w-full"):
                    ui.label(entry.title).classes("key-title")
                    ui.button(
                        "Press a chord…, Escape cancels"
                        if self.capturing == entry.id
                        else chords[entry.id] or "Unbound",
                        on_click=lambda _, i=entry.id: self._capture(i),
                    ).props(
                        f'flat dense no-caps data-control=key-{entry.id} aria-label="Rebind '
                        f'{entry.title}, now {chords[entry.id] or "unbound"}"'
                    )
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
            self._change(keys=keys)
            self._send_chords()
        self._fill_keys()

    def _reset_keys(self) -> None:
        self._change(keys={})
        self._send_chords()
        self._fill_keys()

    def _send_chords(self) -> None:
        ui.run_javascript(f"window.frameChords = {json.dumps(commands.chords(self.shell.keys))}")

    def _release(self) -> None:
        # A dialog dismissed by its backdrop must not leave the next chord to be taken as a binding.
        if self.capturing is not None:
            self.capturing = None
            ui.run_javascript("window.frame.capturing = false")
            self._fill_keys()

    def _close(self) -> None:
        self._release()
        self.dialog.close()

    # -- the dialog ---------------------------------------------------------

    def build(self) -> None:
        """Build the dialog, closed."""
        current = self.shell.settings
        ui.on("chord", self._on_chord)
        with (
            ui.dialog() as self.dialog,
            ui.card().classes("settings").props("data-control=settings"),
        ):
            ui.label("Settings").classes("text-h6")
            self.theme_select = ui.select(
                self._options(),
                value=current.theme if current.theme in self._options() else SYSTEM,
                label="Theme",
                on_change=lambda e: self._choose_theme(e.value),
            ).props("outlined dense data-control=settings-theme")
            self.duplicate_button = ui.button(
                "Duplicate this theme", on_click=self._duplicate
            ).props("flat dense no-caps data-control=theme-duplicate")
            self.duplicate_button.set_enabled(current.theme != SYSTEM)
            self.duplicate_hint = ui.label("Pick Light or Dark above to duplicate it.").classes(
                "muted"
            )
            self.duplicate_hint.set_visibility(current.theme == SYSTEM)
            with ui.expansion("Colours").props("data-control=theme-colours"):
                with ui.column().classes("gap-1") as self.colours:
                    pass
            ui.label("Density").classes("rail-heading")
            ui.toggle(
                DENSITIES, value=current.density, on_change=lambda e: self._change(density=e.value)
            ).props("no-caps data-control=settings-density")
            ui.label("Spacing").classes("rail-heading")
            ui.toggle(
                SPACINGS, value=current.spacing, on_change=lambda e: self._change(spacing=e.value)
            ).props("no-caps data-control=settings-spacing")
            ui.label("3D view background").classes("rail-heading")
            ui.toggle(
                BACKGROUNDS,
                value=current.viewer_background,
                on_change=lambda e: self._change(viewer_background=e.value),
            ).props("no-caps data-control=settings-background")
            ui.label("Key bindings").classes("rail-heading")
            with (
                ui.column().classes("gap-1 w-full").props("data-control=settings-keys") as self.keys
            ):
                pass
            ui.button("Close", on_click=self._close).props("flat no-caps")
        self.dialog.on("hide", self._release)
        self._fill_colours()
        self._fill_keys()
