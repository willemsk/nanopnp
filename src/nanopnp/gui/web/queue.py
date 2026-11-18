"""The workbench's run queue and log, kept by the server for the bottom panel."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.gui.run_model import RunModel

__all__ = ["Entry", "Queue", "Status"]

Status = Literal["waiting", "running", "done", "failed"]

_GLYPH = {"waiting": "○", "running": "▶", "done": "✓", "failed": "✕"}

logger = logging.getLogger(__name__)


@dataclass(eq=False)
class Entry:
    """One build or run in the queue.

    Parameters
    ----------
    suite
        The suite whose model the entry builds, which the frame marks while it runs; empty for a
        study's run.
    study
        The study a run or a sweep's member runs; empty for a build.
    start
        Starts the entry's walk once a slot is free; None where nothing waits to start.
    poll
        Reads what the running walk has said, and moves the entry when it ends.
    cancel
        Asks the running walk to stop at its next check.
    run
        A study's run or a sweep's member: the events its convergence in the Runs tool draws.
    after
        The entries that end before this one starts, as a sweep's earlier waves.
    """

    number: int
    label: str
    status: Status = "waiting"
    suite: str = ""
    start: Callable[[], None] | None = field(default=None, repr=False)
    poll: Callable[[], None] | None = field(default=None, repr=False)
    cancel: Callable[[], None] | None = field(default=None, repr=False)
    run: RunModel | None = field(default=None, repr=False)
    after: tuple[Entry, ...] = field(default=(), repr=False)
    study: str = ""

    def state(self) -> str:
        """Return the entry's state as its glyph and word."""
        return f"{_GLYPH[self.status]} {self.status}"

    def line(self) -> str:
        """Return the entry as a glyph, a word and its label."""
        return f"{self.state()}  {self.label}"

    @property
    def ended(self) -> bool:
        """Whether the entry is done or failed."""
        return self.status in ("done", "failed")


@dataclass
class Queue:
    """The builds and runs waiting, running and done, and the log lines they wrote.

    Parameters
    ----------
    limit
        How many entries run at once, the user's *Solves at once*.
    moved
        Counts each change of an entry or the log, so a window redraws only after one.
    """

    entries: list[Entry] = field(default_factory=list)
    log: list[str] = field(default_factory=list)
    limit: int = 1
    moved: int = 0

    def add(
        self,
        label: str,
        status: Status = "waiting",
        *,
        suite: str = "",
        start: Callable[[], None] | None = None,
        poll: Callable[[], None] | None = None,
        cancel: Callable[[], None] | None = None,
        run: RunModel | None = None,
        after: tuple[Entry, ...] = (),
    ) -> Entry:
        """Append an entry and say so in the log; one with ``start`` waits for :meth:`pump`."""
        entry = Entry(len(self.entries) + 1, label, status, suite, start, poll, cancel, run, after)
        self.entries.append(entry)
        self.say(f"queued {label}")
        return entry

    def set(self, entry: Entry, status: Status) -> None:
        """Move an entry to a status and say so in the log."""
        entry.status = status
        self.say(f"{status} {entry.label}")

    def say(self, line: str) -> None:
        """Add a line to the log."""
        self.log.append(line)
        self.moved += 1

    def running(self) -> int:
        """Return how many entries run now."""
        return sum(entry.status == "running" for entry in self.entries)

    def pump(self) -> tuple[Entry, ...]:
        """Start waiting entries, in order, while fewer than :attr:`limit` run.

        An entry whose earlier entries in ``after`` have not all ended keeps waiting; the
        entries after it may start. Return the entries started.
        """
        started: list[Entry] = []
        free = self.limit - self.running()
        for entry in self.entries:
            if free <= 0:
                break
            if entry.status != "waiting" or entry.start is None:
                continue
            if not all(earlier.ended for earlier in entry.after):
                continue
            self.set(entry, "running")
            start, entry.start = entry.start, None
            try:
                start()
            except Exception as error:
                # A walk that cannot start, as a child the system refuses, ends its entry alone.
                logger.warning("%s did not start: %s", entry.label, error)
                self.set(entry, "failed")
                self.say(f"{entry.label} did not start: {error}")
                continue
            started.append(entry)
            free -= 1
        return tuple(started)

    def tick(self) -> None:
        """Read what each running entry has said, then start what the freed slots allow."""
        for entry in self.entries:
            if entry.status == "running" and entry.poll is not None:
                entry.poll()
        self.pump()

    def drop(self, entry: Entry) -> None:
        """End a waiting entry unstarted, or ask a running one to stop."""
        if entry.status == "waiting":
            entry.start = None
            self.set(entry, "failed")
            self.say(f"cancelled {entry.label}")
        elif entry.status == "running" and entry.cancel is not None:
            entry.cancel()

    def stop(self) -> None:
        """Drop every waiting and running entry, as the server does when it stops."""
        for entry in self.entries:
            self.drop(entry)

    def status_line(self) -> str:
        """Return the one line the frame always shows."""
        if not self.entries:
            return "Queue empty"
        counts = {name: sum(e.status == name for e in self.entries) for name in _GLYPH}
        shown = [f"{counts[name]} {name}" for name in _GLYPH if counts[name]]
        return "Queue: " + ", ".join(shown)
