"""The workbench's command registry: one list for the menus, the palette and the shortcuts."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass

from nanopnp.gui.web.settings import SETTINGS

__all__ = [
    "BROWSER_KEPT",
    "COMMANDS",
    "MENUS",
    "Command",
    "bindings",
    "chords",
    "command",
    "refusal",
    "setting_commands",
]

MENUS: tuple[str, ...] = ("file", "view", "help")


@dataclass(frozen=True)
class Command:
    """One command: its identifier, its title, the menu that lists it and its default chord.

    Parameters
    ----------
    id
        The identifier the menus, the palette, the key listener and the settings share.
    menu
        ``file``, ``view`` or ``help``; the palette lists every command whatever its menu.
    shortcut
        The default chord, such as ``Ctrl+K``, or empty where the command has none.
    keywords
        Words the palette finds the command by, besides its title.
    """

    id: str
    title: str
    menu: str
    shortcut: str = ""
    keywords: tuple[str, ...] = ()


COMMANDS: tuple[Command, ...] = (
    Command("project-new", "New project…", "file"),
    Command("project-open", "Open project…", "file"),
    Command("project-import", "Import case…", "file"),
    Command("project-export", "Export project…", "file"),
    Command("settings", "Settings…", "file", "Ctrl+,"),
    Command("quit", "Quit", "file"),
    Command("suite-molecular", "Molecular suite", "view", "Alt+Shift+1"),
    Command("suite-continuum", "Continuum suite", "view", "Alt+Shift+2"),
    Command("suite-study", "Study suite", "view", "Alt+Shift+3"),
    Command("suite-analysis", "Analysis suite", "view", "Alt+Shift+4"),
    Command("panel-toggle", "Toggle the bottom panel", "view", "Alt+Shift+J"),
    Command("changes", "Changed values", "view", "Alt+Shift+D"),
    Command("problems", "Problems", "view", "Alt+Shift+P"),
    Command("layout-reset", "Reset layout", "view"),
    Command("glossary", "Glossary", "help"),
    Command("about", "About", "help"),
    Command("palette", "Command palette", "view", "Ctrl+K"),
)

PALETTE_ALSO = "F1"
"""A second chord of the palette, which the settings do not rebind."""

# The chords a browser keeps for itself: a page never receives them, so a command cannot take one.
BROWSER_KEPT: frozenset[str] = frozenset(
    {
        "Ctrl+T",
        "Ctrl+W",
        "Ctrl+N",
        "Ctrl+Tab",
        "Ctrl+Shift+T",
        "Ctrl+Shift+N",
        "Ctrl+Shift+W",
        "Ctrl+Shift+P",
        *(f"Ctrl+{digit}" for digit in range(1, 10)),
    }
)


def command(identifier: str) -> Command:
    """Return the command with this identifier."""
    for entry in COMMANDS:
        if entry.id == identifier:
            return entry
    raise KeyError(f"no command {identifier!r}")


def bindings(keys: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return each command's chord: the user's ``keys`` over the defaults.

    A chord of ``""`` in ``keys`` unbinds its command.
    """
    chosen = dict(keys or {})
    return {entry.id: chosen.get(entry.id, entry.shortcut) for entry in COMMANDS}


def chords(keys: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return the command each chord runs, which the page hands the key listener."""
    table = {chord: identifier for identifier, chord in bindings(keys).items() if chord}
    table.setdefault(PALETTE_ALSO, "palette")
    return table


def refusal(identifier: str, chord: str, keys: Mapping[str, str] | None = None) -> str | None:
    """Return why ``chord`` cannot be bound to ``identifier``, or None where it can."""
    if not chord:
        return None
    if chord in BROWSER_KEPT:
        return f"{chord} is kept by the browser, so a page never receives it"
    holder = chords(keys).get(chord)
    if holder is not None and holder != identifier:
        return f"{chord} is bound to {command(holder).title!r}"
    return None


SETTING_COMMAND = "setting-"
"""The prefix of a command that opens one setting on the settings page."""


def setting_commands() -> Iterator[Command]:
    """Yield one palette command per declared setting, which opens it on the settings page."""
    for setting in SETTINGS.values():
        yield Command(
            f"{SETTING_COMMAND}{setting.id}",
            f"Settings: {setting.title}",
            "file",
            keywords=setting.keywords,
        )
