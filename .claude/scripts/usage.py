"""Report a session's tokens by model and its sub-agent spawns by type (WP43 D14; J8).

The input is a Claude Code transcript (``*.jsonl``, one record per line) or a JSON list of
session ``result`` events saved from ``list_events``. The script prints the input, cache-read,
cache-creation and output tokens for each model and the count of sub-agent spawns for each
agent type. It reports and gates nothing. The transcript format is internal to Claude Code and
may change, so a record of a shape it does not know stops the script, naming the line.

Gate minutes are in ``nanopnp-gate.log`` (D11), not here.

Run it as ``uv run .claude/scripts/usage.py <transcript.jsonl>``.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

FIELDS = ("input", "cache read", "cache creation", "output")
TRANSCRIPT_KEYS = (
    "input_tokens",
    "cache_read_input_tokens",
    "cache_creation_input_tokens",
    "output_tokens",
)
RESULT_KEYS = ("inputTokens", "cacheReadInputTokens", "cacheCreationInputTokens", "outputTokens")
SPAWNERS = {"Agent", "Task"}


class UnknownFormatError(ValueError):
    """A record has a shape this script does not know."""


def _add(tokens: dict[str, Counter[str]], model: str, usage: object, keys: tuple[str, ...]) -> None:
    if not isinstance(usage, dict):
        raise UnknownFormatError("usage is not an object")
    for field, key in zip(FIELDS, keys, strict=True):
        value = usage.get(key, 0)
        if not isinstance(value, int):
            raise UnknownFormatError(f"{key} is not an integer")
        tokens.setdefault(model, Counter())[field] += value


def _transcript_record(
    record: object, tokens: dict[str, Counter[str]], spawns: Counter[str], seen: set[str]
) -> None:
    """Add one transcript record. A message split over several records is counted once."""
    if not isinstance(record, dict) or "type" not in record:
        raise UnknownFormatError("not a record with a type")
    if record["type"] == "result" and "modelUsage" in record:
        for model, usage in record["modelUsage"].items():
            _add(tokens, str(model), usage, RESULT_KEYS)
        return
    if record["type"] != "assistant":
        return
    message = record.get("message")
    if not isinstance(message, dict) or "usage" not in message:
        raise UnknownFormatError("assistant record without message.usage")
    content = message.get("content", [])
    for block in content if isinstance(content, list) else []:
        if isinstance(block, dict) and block.get("name") in SPAWNERS:
            spawns[str(block.get("input", {}).get("subagent_type", "(unnamed)"))] += 1
    identifier = str(message.get("id", ""))
    if identifier and identifier in seen:
        return
    seen.add(identifier)
    _add(tokens, str(message.get("model", "(unknown)")), message["usage"], TRANSCRIPT_KEYS)


def read(path: Path) -> tuple[dict[str, Counter[str]], Counter[str]]:
    """Return the tokens by model and the spawn counts by agent type in ``path``.

    Raises
    ------
    UnknownFormatError
        With the line number (or ``list`` index) of a record of an unknown shape.
    """
    tokens: dict[str, Counter[str]] = {}
    spawns: Counter[str] = Counter()
    seen: set[str] = set()
    text = path.read_text(encoding="utf-8")
    if text.lstrip().startswith("["):
        records = json.loads(text)
        numbered = [(f"item {number}", record) for number, record in enumerate(records, 1)]
    else:
        numbered = []
        for number, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                numbered.append((f"line {number}", json.loads(line)))
            except json.JSONDecodeError as error:
                raise UnknownFormatError(f"line {number}: not JSON ({error.msg})") from error
    for where, record in numbered:
        try:
            _transcript_record(record, tokens, spawns, seen)
        except UnknownFormatError as error:
            raise UnknownFormatError(f"{where}: {error}") from error
    return tokens, spawns


def main(argv: list[str] | None = None) -> int:
    """Run the command line and return the process exit status."""
    parser = argparse.ArgumentParser(description="Report tokens by model and spawns by type.")
    parser.add_argument("file", type=Path, help="a transcript (*.jsonl) or a JSON list of results")
    arguments = parser.parse_args(argv)
    try:
        tokens, spawns = read(arguments.file)
    except UnknownFormatError as error:
        sys.stderr.write(f"usage.py: unknown format at {error}\n")
        return 1
    sys.stdout.write("model".ljust(32) + "".join(f"{field:>16}" for field in FIELDS) + "\n")
    for model, counts in sorted(tokens.items()):
        sys.stdout.write(model.ljust(32) + "".join(f"{counts[f]:>16,}" for f in FIELDS) + "\n")
    sys.stdout.write("\nsub-agent spawns\n")
    for agent, count in sorted(spawns.items()):
        sys.stdout.write(f"{agent.ljust(32)}{count:>16,}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
