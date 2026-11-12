"""The workbench's run queue and log, kept by the server for the bottom panel."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

__all__ = ["Entry", "Queue", "Status"]

Status = Literal["waiting", "running", "done", "failed"]

_GLYPH = {"waiting": "○", "running": "▶", "done": "✓", "failed": "✕"}


@dataclass
class Entry:
    """One build or run in the queue.

    Parameters
    ----------
    suite
        The suite whose model the entry builds, which the frame marks while it runs; empty for a
        study's run.
    """

    number: int
    label: str
    status: Status = "waiting"
    suite: str = ""

    def line(self) -> str:
        """Return the entry as a glyph, a word and its label."""
        return f"{_GLYPH[self.status]} {self.status}  {self.label}"


@dataclass
class Queue:
    """The builds and runs waiting, running and done, and the log lines they wrote."""

    entries: list[Entry] = field(default_factory=list)
    log: list[str] = field(default_factory=list)

    def add(self, label: str, status: Status = "waiting", *, suite: str = "") -> Entry:
        """Append an entry and say so in the log."""
        entry = Entry(len(self.entries) + 1, label, status, suite)
        self.entries.append(entry)
        self.log.append(f"queued {label}")
        return entry

    def set(self, entry: Entry, status: Status) -> None:
        """Move an entry to a status and say so in the log."""
        entry.status = status
        self.log.append(f"{status} {entry.label}")

    def status_line(self) -> str:
        """Return the one line the frame always shows."""
        if not self.entries:
            return "Queue empty"
        counts = {name: sum(e.status == name for e in self.entries) for name in _GLYPH}
        shown = [f"{counts[name]} {name}" for name in _GLYPH if counts[name]]
        return "Queue: " + ", ".join(shown)
