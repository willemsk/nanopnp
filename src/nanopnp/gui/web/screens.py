"""The workbench's screen registry: each screen's path and the controls it declares."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["SCREENS", "Screen", "screen"]


@dataclass(frozen=True)
class Screen:
    """One screen: its design identifier, its path and its ``data-control`` names.

    Parameters
    ----------
    id
        The identifier the design documents and mockups use.
    controls
        Every ``data-control`` the screen carries in every state, visible once the screen is ready.
    """

    id: str
    path: str
    controls: tuple[str, ...]


SCREENS: tuple[Screen, ...] = (
    Screen("home", "/", ("state", "stages", "open-charge")),
    Screen("st-charge", "/charge", ("molecule", "strip", "map", "link-chip", "unlink", "status")),
)


def screen(identifier: str) -> Screen:
    """Return the screen with this identifier."""
    for entry in SCREENS:
        if entry.id == identifier:
            return entry
    raise KeyError(f"no screen {identifier!r}; the screens are {', '.join(s.id for s in SCREENS)}")
