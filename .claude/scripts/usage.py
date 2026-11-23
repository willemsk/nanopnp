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
is ``$CLAUDE_CODE_SESSION_ID``'s, else the newest transcript of the project. Where none exists,
the line says "not measured" and the exit status is 0.

Run it as ``uv run .claude/scripts/usage.py [--label <level>] [--since <time|commit> | --all]``.

``--reading`` measures instead what each window that an ``/np-`` command opens read before its first
``Edit``, ``Write`` or ``NotebookEdit`` (§8.2.50 AZ9): the words of project text (instructions,
records and the tree's ``CLAUDE.md``), of code and of command output, the tokens at the window's
start and at that edit, and the ten largest files of project text. A change made through a shell
command does not end the count (AZ17). A file counts when a ``Read`` or a command that only prints
files gives it: ``cat``, ``head``, ``tail`` or ``sed -n``, alone or piped through ``cut``, ``head``
or ``tail``, with ``cd``, ``echo``, ``wc``, ``ls`` and ``pwd`` between; files of code printed with
it make the result command output (AZ16). A session's first window is the one no message precedes;
the reading limit binds it for ``/np-implement`` (AZ15).
``--transcript`` names a transcript; ``--pages`` reads instead the transcripts of agents that paged
other sessions with the session service's ``list_events`` (AZ10), one session per paged id. A page
holds no typed prompt and no skill text, so a paged session's windows open at its first message and
after each compaction, and its window prompt is not counted. Run it
as ``uv run .claude/scripts/usage.py --reading [--transcript <jsonl> | --pages <jsonl> ...]
[--json]``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
from collections import Counter
from datetime import datetime
from itertools import pairwise
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
AWAY_S = 30 * 60
NOT_TYPED = ("<local-command-stdout>", "<local-command-caveat>", "<task-notification>")
SKILL_TEXT = "Base directory for this skill:"
CONTINUED = "This session is being continued from a previous conversation"
EDITS = ("Edit", "Write", "NotebookEdit")
PRINTERS = ("cat", "head", "tail", "sed")
# Commands whose output is a line or two, and filters that only shorten what a printer prints.
QUIET = ("cd", "echo", "wc", "ls", "pwd")
FILTERS = ("cut", "head", "tail")
DISCARDS = ("2>/dev/null", "2>&1")
PROJECT = {"instructions", "records"}
LIST_EVENTS = "mcp__claude-code-remote__list_events"
RECORD_DIRS = ("/docs/", "/specification/", "/knowledge/")
RECORD_NAMES = ("SPECIFICATION.md", "CHANGELOG.md", "CONTRIBUTING.md", "README.md")
CODE_DIRS = ("/src/", "/tests/", "/examples/", "/data/")
LINE_NUMBER = re.compile(r"(?m)^\s*\d+\t")
NUMBERED_CAT = re.compile(r"\bcat\s+-\w*n")
COMMAND_NAME = re.compile(r"<command-name>\s*/?([\w:-]+)\s*</command-name>")
# The command, not a path that holds its name, as `.claude/skills/np-plan/wp.md` does.
NP_COMMAND = re.compile(r"(?<![\w.])/(np-[\w-]+)")
RUNS_CLAUSE = re.compile(
    r"\buv run (?:-\S+ )*\S*clause\.py\b|\bpython3? \S*clause\.py\b|\bjust clause\b"
)


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


def _text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            str(block.get("text", ""))
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return ""


def _path_class(path: str, root: str) -> str:
    # A path outside the tree, such as a saved tool result, is commands.
    if path.startswith(("/", "~")) and not path.startswith(f"{root}/"):
        return "commands"
    path = path if path.startswith("/") else f"/{path}"
    name = path.rsplit("/", 1)[-1]
    if path.endswith((".py", ".sh", ".cjs", ".js", ".html", ".css")):
        return "code"
    if "/.claude/" in path or path.endswith("CLAUDE.md"):
        return "instructions"
    if any(part in path for part in RECORD_DIRS) or name in RECORD_NAMES:
        return "records"
    if any(part in path for part in CODE_DIRS):
        return "code"
    return "commands"


def _segments(command: str) -> list[list[str]] | None:
    try:
        words = shlex.split(command, comments=True)
    except ValueError:
        return None
    segments: list[list[str]] = [[]]
    for word in words:
        if word in ("&&", ";"):
            segments.append([])
        elif word.endswith(";") and word != ";":
            segments[-1].append(word[:-1])
            segments.append([])
        else:
            segments[-1].append(word)
    return [kept for segment in segments if (kept := [w for w in segment if w not in DISCARDS])]


def _printed_files(command: str) -> list[str] | None:
    # The files of a command that only prints them. Any other command, a pipe into anything but a
    # shortening filter, or a redirection gives None.
    files: list[str] = []
    for segment in _segments(command) or []:
        head, *args = segment
        if head in QUIET:
            continue
        if "|" in args:
            args, piped = args[: args.index("|")], args[args.index("|") :]
            follows = [after for before, after in pairwise([*piped, ""]) if before == "|"]
            if any(name not in FILTERS for name in follows):
                return None
        if head not in PRINTERS or any(arg in (">", ">>", "<") for arg in args):
            return None
        if head == "sed":
            if not args or args[0] != "-n" or len(args) < 3:
                return None
            args = args[2:]
        operands, skip = [], False
        for arg in args:
            if skip:
                skip = False
            elif arg in ("-n", "-c") and head in ("head", "tail"):
                # head's and tail's count; cat's -n numbers the lines and takes no value.
                skip = True
            elif not arg.startswith("-"):
                operands.append(arg)
        if not operands:
            return None
        files += operands
    return files or None


def _classify(call: dict[str, Any], root: str) -> tuple[str, str | None]:
    # One file has one name in a window's list, read by its full path or from the tree's root.
    def shown(path: str) -> str:
        return path.removeprefix(f"{root}/")

    name, given = call.get("name"), call.get("input") or {}
    if name == "Read" and given.get("file_path"):
        return _path_class(str(given["file_path"]), root), shown(str(given["file_path"]))
    if name == "Grep" and given.get("path"):
        return _path_class(str(given["path"]), root), shown(str(given["path"]))
    if name == "Bash":
        command = str(given.get("command", ""))
        # A run of the script prints records; a command that only names its file does not.
        if RUNS_CLAUSE.search(command):
            return "records", "clause.py"
        files = _printed_files(command)
        if files:
            classes = {_path_class(path, root) for path in files}
            # Instructions and records printed together are project text. The result does not say
            # where one file ends, so the first file's class takes the words.
            if len(classes) == 1 or classes <= PROJECT:
                names = " ".join(dict.fromkeys(shown(path) for path in files))
                return _path_class(files[0], root), names
    return "commands", None


def _page_events(path: Path) -> dict[str, list[dict[str, Any]]]:
    calls: dict[str, str] = {}
    pages: list[tuple[str, str]] = []
    for event in _events(path):
        for block in _blocks(event):
            if block.get("type") == "tool_use" and block.get("name") == LIST_EVENTS:
                calls[block["id"]] = str((block.get("input") or {}).get("session_id", ""))
            elif block.get("type") == "tool_result" and block.get("tool_use_id") in calls:
                text = _text(block.get("content"))
                saved = re.search(r"saved to (\S+?\.txt)", text)
                if saved and Path(saved.group(1)).is_file():
                    text = Path(saved.group(1)).read_text(encoding="utf-8")
                pages.append((calls[block["tool_use_id"]], text))
    found: dict[str, dict[str, dict[str, Any]]] = {}
    for session, text in pages:
        start, end = text.find('{"ccr"'), text.rfind("}")
        if start < 0:
            continue
        try:
            data = json.loads(text[start : end + 1])["ccr"]["data"]
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
        for raw in data:
            kind = "assistant" if "assistant" in raw else "user" if "user" in raw else None
            if kind is None:
                continue
            inner = raw[kind].get("internal_anthropic_catchall") or {}
            if inner.get("parent_tool_use_id") or not inner.get("timestamp"):
                continue
            event = {
                "type": kind,
                "message": inner.get("message") or {},
                "timestamp": inner["timestamp"],
                "_t": datetime.fromisoformat(inner["timestamp"]).timestamp(),
                "session": session,
                "page": True,
            }
            if "isMeta" in inner:
                event["isMeta"] = inner["isMeta"]
            key = raw[kind].get("uuid") or f"{inner['timestamp']}{json.dumps(event['message'])}"
            found.setdefault(session, {})[key] = event
    return {
        session: sorted(events.values(), key=lambda event: event["_t"])
        for session, events in found.items()
    }


def _np_command(text: str) -> re.Match[str] | None:
    # A prompt that runs a command names it in a tag, and its arguments may name another: a
    # /compact prompt that carries the next step holds `/np-` and opens no window.
    named = COMMAND_NAME.search(text)
    if named and not named.group(1).startswith("np-"):
        return None
    return NP_COMMAND.search(text)


def _window_name(event: dict[str, Any]) -> str:
    text = _text((event.get("message") or {}).get("content"))
    command = _np_command(text)
    args = re.search(r"<command-args>(.*?)</command-args>", text, re.S)
    rest = args.group(1) if args else text[command.end() :] if command else ""
    return " ".join([command.group(1) if command else "np-", *rest.split()[:2]])


def _tokens(event: dict[str, Any]) -> int:
    usage = (event.get("message") or {}).get("usage") or {}
    return sum(
        usage.get(field) or 0
        for field in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
    )


def reading(events: list[dict[str, Any]], claude_md: int) -> list[dict[str, Any]]:
    """Return what each ``/np-`` window of one session's ``events`` read before its first edit."""
    if events and events[0].get("page"):
        continued = {
            index
            for index, event in enumerate(events)
            if event.get("type") == "user"
            and _text((event.get("message") or {}).get("content")).startswith(CONTINUED)
        }
        opens = sorted({0} | continued)
    else:
        opens = [
            index
            for index, event in enumerate(events)
            if _typed(event)
            and _np_command(_text((event.get("message") or {}).get("content")))
            and not _text((event.get("message") or {}).get("content"))
            .lstrip()
            .startswith(SKILL_TEXT)
        ]
    # The session's own checkout, which a transcript measured from another one names in `cwd`.
    root = next((str(event["cwd"]) for event in events if event.get("cwd")), str(ROOT))
    windows = []
    for number, first in enumerate(opens):
        last = opens[number + 1] if number + 1 < len(opens) else len(events)
        before = [
            event for event in events[:first] if event.get("type") == "assistant" and _tokens(event)
        ]
        words: Counter[str] = Counter()
        files: Counter[str] = Counter()
        calls: dict[str, dict[str, Any]] = {}
        page = bool(events[first].get("page"))
        if not page:
            words["instructions"] += len(_text(events[first]["message"].get("content")).split())
        start_tokens, edit_tokens, edited = None, None, False
        for event in events[first + (not page) : last]:
            if event.get("type") == "assistant" and _tokens(event):
                start_tokens = start_tokens if start_tokens is not None else _tokens(event)
                edit_tokens = _tokens(event)
            text = _text((event.get("message") or {}).get("content"))
            if event.get("type") == "user" and text.lstrip().startswith(SKILL_TEXT):
                # The project's own skill: the user's and a plug-in's also sit in a `.claude/`.
                own = f"{root}/.claude/" in text.split("\n", 1)[0]
                words["instructions" if own else "commands"] += len(text.split())
            for block in _blocks(event):
                if block.get("type") == "tool_use":
                    calls[block.get("id", "")] = block
                    edited = edited or block.get("name") in EDITS
                elif block.get("type") == "tool_result" and block.get("tool_use_id") in calls:
                    call = calls[block["tool_use_id"]]
                    kind, path = _classify(call, root)
                    result = _text(block.get("content"))
                    command = str((call.get("input") or {}).get("command", ""))
                    if call.get("name") == "Read" or (path and NUMBERED_CAT.search(command)):
                        result = LINE_NUMBER.sub("", result)
                    count = len(result.split())
                    words[kind] += count
                    if path and kind in ("instructions", "records"):
                        files[path] += count
            if edited:
                break
        project = words["instructions"] + words["records"] + claude_md
        windows.append(
            {
                "session": events[first].get("session", ""),
                "window": (
                    ("after compaction" if first else "start")
                    if events[first].get("page")
                    else _window_name(events[first])
                ),
                "first": start_tokens is not None and not before,
                "edit": edited,
                "project": project,
                "instructions": words["instructions"],
                "records": words["records"],
                "claude_md": claude_md,
                "code": words["code"],
                "commands": words["commands"],
                "tokens_start": start_tokens or 0,
                "tokens_edit": edit_tokens or 0,
                "files": dict(files.most_common()),
                "read_order": list(files),
            }
        )
    return windows


def _reading_line(window: dict[str, Any]) -> str:
    largest = ", ".join(f"{path} {count:,}" for path, count in list(window["files"].items())[:10])
    edit = "the first edit" if window["edit"] else "the window's end (no edit)"
    return (
        f"Reading ({window['session']}, {window['window']}, "
        f"{'first window' if window['first'] else 'later window'}): "
        f"{window['project']:,} words of project text before {edit} "
        f"(instructions {window['instructions']:,}; records {window['records']:,}; "
        f"CLAUDE.md {window['claude_md']:,}); code {window['code']:,}; "
        f"commands {window['commands']:,}; {window['tokens_start']:,} tokens at the start, "
        f"{window['tokens_edit']:,} at the {'edit' if window['edit'] else 'end'}; "
        f"largest: {largest or 'none'}"
    )


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
    parser.add_argument("--reading", action="store_true", help="measure the reading (AZ9)")
    parser.add_argument("--transcript", type=Path, help="the transcript to read with --reading")
    parser.add_argument(
        "--pages", type=Path, nargs="+", help="transcripts of agents that paged sessions"
    )
    args = parser.parse_args()
    if (args.transcript or args.pages) and not args.reading:
        parser.error("--transcript and --pages need --reading")
    if args.transcript and args.pages:
        parser.error("--reading takes --transcript or --pages, not both")
    if args.reading:
        if args.since or args.all:
            parser.error("--reading takes no --since or --all")
        return _main_reading(args.transcript, args.pages, args.json)
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


def _main_reading(transcript: Path | None, pages: list[Path] | None, as_json: bool) -> int:
    claude_md = len((ROOT / "CLAUDE.md").read_text(encoding="utf-8").split())
    sessions: dict[str, list[dict[str, Any]]] = {}
    if pages:
        for page in pages:
            for session, events in _page_events(page).items():
                merged = {
                    json.dumps(event, sort_keys=True): event for event in sessions.get(session, [])
                }
                merged.update({json.dumps(event, sort_keys=True): event for event in events})
                sessions[session] = sorted(merged.values(), key=lambda event: event["_t"])
    else:
        found = transcript or _transcript()
        if found is None:
            print("Reading: not measured, no Claude Code transcript on this host.")
            return 0
        sessions[found.stem] = [{**event, "session": found.stem} for event in _events(found)]
    windows = [window for events in sessions.values() for window in reading(events, claude_md)]
    if as_json:
        print(json.dumps(windows, indent=2))
    else:
        print("\n".join(_reading_line(window) for window in windows) or "Reading: no /np- window")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
