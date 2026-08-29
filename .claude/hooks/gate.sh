#!/usr/bin/env bash
# The push gate of CLAUDE.md, enforced before Claude Code makes a commit.
#
# CLAUDE.md says "Before committing, run the whole gate". This hook makes that
# structural rather than something to remember: a PreToolUse hook on Bash that
# does nothing unless the command is a `git commit`, and denies the tool call
# when any stage fails, handing the failing output back so it can be fixed
# first. `git commit --no-verify` skips it, matching git's own convention.
#
# It is wired up in .claude/settings.json. The matcher is the bare Bash tool
# rather than an `if: Bash(git commit*)` filter, because that filter is a
# prefix match and would miss the compound form `git add -A && git commit ...`.
set -uo pipefail

payload=$(cat)
command=$(printf '%s' "$payload" | jq -r '.tool_input.command // ""' 2>/dev/null) || exit 0

# A `git commit` as a command word, not `git commit-graph` and not a bare
# mention. Anything else leaves the tool call untouched.
# The regex lives in a variable: bash parses an unquoted =~ operand as shell
# syntax first, and a bare "(" inside it is a syntax error, not a pattern.
commit_re='(^|[;&|(]|[[:space:]])git([[:space:]]+-[^[:space:]]+)*[[:space:]]+commit([[:space:]]|$)'
[[ $command =~ $commit_re ]] || exit 0
[[ $command == *--no-verify* ]] && exit 0

root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
cd "$root" || exit 0
[[ -f pyproject.toml && -d src/nanopnp ]] || exit 0

deny() {
    jq -n --arg reason "$1" '{
        hookSpecificOutput: {
            hookEventName: "PreToolUse",
            permissionDecision: "deny",
            permissionDecisionReason: $reason
        }
    }'
    exit 0
}

check() {
    local name=$1
    shift
    local output
    if ! output=$("$@" 2>&1); then
        deny "The commit was not made: the gate failed at \`${name}\`.

CLAUDE.md requires the whole gate — ruff check, ruff format --check, mypy src/,
pytest — to pass before committing. Fix this, then commit again. To commit
anyway, add --no-verify.

Last 40 lines of \`$*\`:

$(printf '%s' "$output" | tail -40)"
    fi
}

check "ruff check"          uv run ruff check .
check "ruff format --check" uv run ruff format --check .
check "mypy --strict"       uv run mypy src/
check "pytest"              uv run pytest -q

exit 0
