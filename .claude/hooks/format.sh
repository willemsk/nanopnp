#!/usr/bin/env bash
# Format a Python file as soon as Claude Code edits it, so formatting drift
# never reaches the gate (.claude/hooks/gate.sh), where it costs a round trip.
#
# A PostToolUse hook on Edit|Write|MultiEdit, wired up in .claude/settings.json.
# It runs `ruff format` and sorts imports (`--select I`) and nothing else: a
# general `ruff check --fix` would delete an import added one edit before its
# first use (F401), mid-change. It never blocks and never speaks; the gate is
# still what decides.
set -uo pipefail

path=$(jq -r '.tool_input.file_path // ""' 2>/dev/null) || exit 0
[[ $path == *.py && -f $path ]] || exit 0

root=$(git -C "$(dirname "$path")" rev-parse --show-toplevel 2>/dev/null) || exit 0
cd "$root" || exit 0
[[ -f pyproject.toml ]] || exit 0

uv run --quiet ruff format --quiet "$path" >/dev/null 2>&1
uv run --quiet ruff check --quiet --fix --select I "$path" >/dev/null 2>&1
exit 0
