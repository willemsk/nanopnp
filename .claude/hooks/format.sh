#!/usr/bin/env bash
# Format a Python file as soon as an agent edits it, so formatting drift
# never reaches the gate (.claude/hooks/gate.sh), where it costs a round trip.
#
# A PostToolUse hook on Edit|Write, wired up in .claude/settings.json;
# accepts a path object or a raw `apply_patch` string.
# It runs `ruff format` and sorts imports (`--select I`) and nothing else: a
# general `ruff check --fix` would delete an import added one edit before its
# first use (F401), mid-change. It never blocks and never speaks; the gate is
# still what decides.
set -uo pipefail

payload=$(cat)
cwd=$(printf '%s' "$payload" | jq -r '.cwd // ""' 2>/dev/null) || exit 0
while IFS= read -r -d '' path; do
    [[ $path == /* || -z $cwd ]] || path=$cwd/$path
    [[ $path == *.py && -f $path ]] || continue
    (
        root=$(git -C "$(dirname "$path")" rev-parse --show-toplevel 2>/dev/null) || exit 0
        cd "$root" || exit 0
        [[ -f pyproject.toml ]] || exit 0
        uv run --quiet ruff format --quiet "$path" >/dev/null 2>&1
        uv run --quiet ruff check --quiet --fix --select I "$path" >/dev/null 2>&1
    )
done < <(printf '%s' "$payload" | jq -j '
    def paths:
        if type == "object" then .file_path // .path // empty
        elif type == "string" and startswith("*** Begin Patch\n") then
            split("\n")[] |
            select(test("^\\*\\*\\* (Update File|Add File|Move to): ")) |
            sub("^\\*\\*\\* (Update File|Add File|Move to): "; "")
        else empty end;
    .tool_input // empty | paths | select(type == "string" and length > 0) | . + "\u0000"
' 2>/dev/null)
exit 0
