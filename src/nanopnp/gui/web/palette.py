"""The command palette: Quasar's searchable select over every command and every setting."""

from __future__ import annotations

from collections.abc import Callable, Mapping

from nicegui import events
from nicegui.element import Element

from nanopnp.gui.web import commands

__all__ = ["Palette", "options"]


def options(keys: Mapping[str, str], *, has_project: bool) -> list[dict[str, object]]:
    """Return the palette's options: each command and setting, with its chord and why it cannot run.

    An option's ``words`` are the lower-case title and keywords the palette matches typed words in.
    """
    chords = commands.bindings(keys)
    found: list[dict[str, object]] = []
    for entry in (*commands.COMMANDS, *commands.setting_commands()):
        if entry.id == "palette":
            continue
        reason = commands.unavailable(entry, has_project=has_project)
        found.append(
            {
                "id": entry.id,
                "title": entry.title,
                "words": " ".join((entry.title, *entry.keywords)).lower(),
                "chord": chords.get(entry.id, ""),
                "disable": reason is not None,
                "reason": reason or "",
            }
        )
    return found


class Palette(Element, component="assets/palette.js"):
    """The palette's searchable select, which reports the command chosen."""

    def __init__(self, on_choose: Callable[[str], object]) -> None:
        """Build the select, empty until the page sets its options."""
        super().__init__()
        self._props["options"] = []
        self._props["text"] = ""
        self.on("choose", lambda event: self._chosen(event, on_choose))

    def prepare(self, choices: list[dict[str, object]], text: str = "") -> None:
        """Set the options and the text typed when the palette next opens."""
        self._props["options"] = choices
        self._props["text"] = text
        self.update()

    @staticmethod
    def _chosen(event: events.GenericEventArguments, then: Callable[[str], object]) -> None:
        then(str(event.args))
