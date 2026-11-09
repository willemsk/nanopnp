"""Measure a Claude Code session's cost in the units of §8.3 (§8.2.37 AM10, AM11).

Reads the session's transcript, ``<config>/projects/<project>/<session>.jsonl``, and the transcripts
of its sub-agents beside it, and prints one Markdown line for a report or a pull request:

    Measured (review): 2 sessions, 1.4 agent hours, 4 touches; claude-opus-5-5 0.20 M out, 43 M
    cached

- **Sessions** are context windows: one, and one more for each compaction (``compact_boundary``)
  after the window's first prompt.
- **Agent hours** add the gaps between consecutive events of the main transcript, less the waits
  for the author: the gap before a prompt the author typed, the time an ``AskUserQuestion`` call
  waits for its answer, and any gap over 30 minutes, taken as the author away.
- **Touches** are the prompts the author typed (a command, ``/compact`` or a message) and the
  answered ``AskUserQuestion`` calls.
- **Tokens** count each API message once, by model, over the main transcript and its sub-agents':
  the output tokens, thinking included, and the input read from the prompt cache.

The window opens at the last prompt that ran an ``/np-`` command, or at the ``/compact`` typed just
before it; at ``--since`` (an ISO time, or a
git commit, whose author time is taken), or with ``--all`` at the session's start. The session
is ``$CLAUDE_CODE_SESSION_ID``'s, else the newest transcript of the project. Where none exists, as
on another host, the line says "not measured" and the exit status is 0.

Run it as ``uv run .claude/scripts/usage.py [--label <level>] [--since <time|commit> | --all]``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
AWAY_S = 30 * 60
NOT_TYPED = ("<local-command-stdout>", "<local-command-caveat>", "<task-notification>")


def _transcript() -> Path | None:
    config = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))
    project = config / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(ROOT))
    session = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    if session and (project / f"{session}.jsonl").is_file():
        return project / f"{session}.jsonl"
    found = sorted(project.glob("*.jsonl"), key=lambda path: path.stat().st_mtime)
    return found[-1] if found else None


def _events(path: Path) -> list[dict[str, Any]]:
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict) and event.get("timestamp"):
            event["_t"] = datetime.fromisoformat(event["timestamp"]).timestamp()
            events.append(event)
    return sorted(events, key=lambda event: event["_t"])


def _blocks(event: dict[str, Any]) -> list[dict[str, Any]]:
    content = (event.get("message") or {}).get("content")
    return (
        [block for block in content if isinstance(block, dict)] if isinstance(content, list) else []
    )


def _typed(event: dict[str, Any]) -> bool:
    """Return whether ``event`` is a prompt the author typed."""
    if event.get("type") != "user" or event.get("isMeta") or event.get("isCompactSummary"):
        return False
    content = (event.get("message") or {}).get("content")
    if isinstance(content, list):
        if any(block.get("type") == "tool_result" for block in _blocks(event)):
            return False
        content = " ".join(str(block.get("text", "")) for block in _blocks(event))
    return isinstance(content, str) and not content.lstrip().startswith(NOT_TYPED)


def _start(events: list[dict[str, Any]], since: str | None, everything: bool) -> float:
    if everything or not events:
        return events[0]["_t"] if events else 0.0
    if since:
        if not re.match(r"\d{4}-\d{2}-\d{2}", since):
            since = subprocess.run(
                ["git", "log", "-1", "--format=%aI", since],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        return datetime.fromisoformat(since).timestamp()
    typed = [event for event in events if _typed(event)]
    commands = [index for index, event in enumerate(typed) if "/np-" in json.dumps(event)]
    if not commands:
        return events[0]["_t"]
    first = commands[-1]
    if first and "<command-name>/compact" in json.dumps(typed[first - 1]):
        first -= 1
    return float(typed[first]["_t"])


def measure(path: Path, start: float) -> dict[str, Any]:
    """Return the sessions, agent hours, touches and tokens by model of ``path`` from ``start``."""
    events = [event for event in _events(path) if event["_t"] >= start]
    asked = {
        block["id"]
        for event in events
        for block in _blocks(event)
        if block.get("type") == "tool_use" and block.get("name") == "AskUserQuestion"
    }
    seconds, touches, sessions = 0.0, 0, 1
    for before, event in zip([None, *events], events, strict=False):
        answered = any(block.get("tool_use_id") in asked for block in _blocks(event))
        touches += _typed(event) or answered
        sessions += event.get("subtype") == "compact_boundary"
        gap = event["_t"] - before["_t"] if before else 0.0
        if not (_typed(event) or answered or gap > AWAY_S):
            seconds += gap
    opening = next((event for event in events if _typed(event)), None)
    if opening is not None and "<command-name>/compact" in json.dumps(opening):
        sessions -= 1
    tokens: Counter[tuple[str, str]] = Counter()
    seen: set[str] = set()
    for transcript in [path, *sorted((path.parent / path.stem / "subagents").glob("*.jsonl"))]:
        for event in _events(transcript):
            message = event.get("message") or {}
            usage, key = message.get("usage"), message.get("id") or event.get("uuid")
            if event.get("type") != "assistant" or not usage or key in seen or event["_t"] < start:
                continue
            seen.add(key)
            model = str(message.get("model", "unknown"))
            tokens[model, "out"] += usage.get("output_tokens") or 0
            tokens[model, "cached"] += usage.get("cache_read_input_tokens") or 0
    models = sorted({model for model, _ in tokens})
    return {
        "sessions": sessions,
        "agent_hours": round(seconds / 3600, 1),
        "touches": touches,
        "tokens": {
            model: {kind: tokens[model, kind] for kind in ("out", "cached")} for model in models
        },
    }


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}" + ("" if number == 1 else "es" if noun.endswith("ch") else "s")


def main() -> int:
    """Print the measured line, or "not measured" where there is no transcript."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--label", default="session", help="the level measured, for the line")
    window = parser.add_mutually_exclusive_group()
    window.add_argument("--since", help="an ISO time or a git commit that opens the window")
    window.add_argument("--all", action="store_true", help="measure the whole session")
    parser.add_argument("--json", action="store_true", help="print the measurement as JSON")
    args = parser.parse_args()
    path = _transcript()
    if path is None:
        print(f"Measured ({args.label}): not measured, no Claude Code transcript on this host.")
        return 0
    result = measure(path, _start(_events(path), args.since, args.all))
    if args.json:
        print(json.dumps(result, indent=2))
        return 0
    spend = ", ".join(
        f"{model} {use['out'] / 1e6:.2f} M out, {use['cached'] / 1e6:.0f} M cached"
        for model, use in result["tokens"].items()
    )
    print(
        f"Measured ({args.label}): {_count(result['sessions'], 'session')}, "
        f"{result['agent_hours']} agent hours, {_count(result['touches'], 'touch')}; "
        f"{spend or 'no tokens'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
