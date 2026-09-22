#!/usr/bin/env bash
# The push gate of CLAUDE.md, enforced before Claude Code makes a commit.
#
# CLAUDE.md says "Before committing, run the whole gate". This hook makes that
# structural rather than something to remember: a PreToolUse hook on Bash that
# does nothing unless the command is a `git commit`, and denies the tool call
# when any stage fails, handing the failing output back so it can be fixed
# first. `git commit --no-verify` (or `-n`) skips it, matching git's own
# convention.
#
# Two ways in:
#   gate.sh          hook mode: reads the PreToolUse payload on stdin
#   gate.sh run      runs the gate directly, prints each stage, exits non-zero
#                    on failure; what the skills call instead of the && chain
#
# It is wired up in .claude/settings.json. The matcher is the bare Bash tool
# rather than an `if: Bash(git commit*)` filter, because that filter is a
# prefix match and would miss the compound form `git add -A && git commit ...`.
#
# What is gated is the working tree, not the index: a compound
# `git add -A && git commit` reaches this hook before the `add` has run.
#
# Two things keep it from costing the full ~8 minutes on every commit:
# - a tree state that already passed (by either entry point) is not re-run;
#   the stamp is the tree id of the working copy, so any edit invalidates it;
# - when every changed path is prose (*.md, docs/, .knowledge/), the lock
#   check, mypy and pytest are skipped: no test and no module reads those
#   files. Anything else is code, data/corrections/*.yaml and this hook included.
#
# The stages share one budget (NANOPNP_GATE_BUDGET_S, default 1500 s), kept
# below the hook timeout in settings.json (1800 s). A gate that overruns its
# budget denies the commit; it must never be the harness's timeout that ends
# it, because an interrupted hook is not a refusal.
set -uo pipefail

mode=hook
[[ ${1:-} == run ]] && mode=run

if [[ $mode == hook ]]; then
    payload=$(cat)
    command=$(printf '%s' "$payload" | jq -r '.tool_input.command // ""' 2>/dev/null) || exit 0

    # A `git commit` as a command word, not `git commit-graph` and not a bare
    # mention. Anything else leaves the tool call untouched.
    # The regex lives in a variable: bash parses an unquoted =~ operand as shell
    # syntax first, and a bare "(" inside it is a syntax error, not a pattern.
    #
    # Global options sit between `git` and `commit`, and the ones below take
    # their value as a *separate* token: matching only `-[^space]+` stops at
    # that value and lets `git -C /repo commit` through the gate silently. Each
    # of these therefore consumes the token after it; every other option
    # consumes nothing.
    #
    # The last group captures the commit's own arguments, up to the next
    # command separator or line break, so that a heredoc body is not part of it.
    git_opt='[[:space:]]+(-[Cc]|--git-dir|--work-tree|--namespace|--exec-path|--config-env)[[:space:]]+[^[:space:]]+|[[:space:]]+-[^[:space:]]+'
    seg="[^;&|"$'\n'"]"
    commit_re="(^|[;&|(]|[[:space:]])git(${git_opt})*[[:space:]]+commit(\$|[[:space:]]${seg}*)"
    [[ $command =~ $commit_re ]] || exit 0

    # --no-verify / -n count only as options of that commit: quoted strings
    # are removed first, so `-m "document --no-verify"` is still gated.
    args=${BASH_REMATCH[${#BASH_REMATCH[@]} - 1]}
    args=$(printf '%s' "$args" | sed -E "s/\"[^\"]*\"//g; s/'[^']*'//g")
    set -f
    for token in $args; do
        [[ $token == --no-verify || $token == -n ]] && exit 0
    done
    set +f
fi

root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
cd "$root" || exit 0
[[ -f pyproject.toml && -d src/nanopnp ]] || exit 0

# Match CI: a uv.lock that pyproject.toml has moved away from is a failure,
# not something `uv run` should quietly rewrite.
export UV_LOCKED=1

# The tree the working copy would commit as with `git add -A`, built in a
# throwaway index: content-addressed, independent of HEAD and of how the
# changes are later split into commits, so a gated tree carved into several
# commits pays for the gate once.
state_hash() {
    local index
    index=$(mktemp) || return 1
    cp "$(git rev-parse --git-path index)" "$index" 2>/dev/null
    GIT_INDEX_FILE=$index git add -A >/dev/null 2>&1 &&
        GIT_INDEX_FILE=$index git write-tree 2>/dev/null
    rm -f "$index"
}

stamp_file="$(git rev-parse --git-dir)/nanopnp-gate.pass"
state=$(state_hash) || state=""

say() { [[ $mode == run ]] && printf '%s\n' "$*"; return 0; }

if [[ -n $state && -f $stamp_file && $(cat "$stamp_file") == "$state" ]]; then
    say "gate: this tree state already passed; nothing to re-run."
    exit 0
fi

docs_only=true
while IFS= read -r path; do
    [[ -z $path ]] && continue
    case $path in
        *.md | docs/* | .knowledge/*) ;;
        *) docs_only=false; break ;;
    esac
done < <({ git diff --name-only HEAD; git ls-files --others --exclude-standard; } 2>/dev/null)

if [[ $mode == run ]]; then
    lead="The gate"
else
    lead="The commit was not made: the gate"
fi

fail() {
    local reason=$1
    if [[ $mode == run ]]; then
        printf '%s\n' "$reason" >&2
        exit 1
    fi
    jq -n --arg reason "$reason" '{
        hookSpecificOutput: {
            hookEventName: "PreToolUse",
            permissionDecision: "deny",
            permissionDecisionReason: $reason
        }
    }'
    exit 0
}

budget=${NANOPNP_GATE_BUDGET_S:-1500}
deadline=$((SECONDS + budget))
have_timeout=false
command -v timeout >/dev/null 2>&1 && have_timeout=true

check() {
    local name=$1
    shift
    local remaining=$((deadline - SECONDS))
    local output status
    say "gate: ${name}"
    if ((remaining <= 0)); then
        status=124
        output="(no budget left)"
    elif $have_timeout; then
        output=$(timeout "$remaining" "$@" 2>&1)
        status=$?
    else
        output=$("$@" 2>&1)
        status=$?
    fi
    ((status == 0)) && return 0

    if ((status == 124)); then
        fail "${lead} ran out of its ${budget} s budget at \`${name}\`.

A gate that cannot finish is not a pass. Find what made \`$*\` slow (pytest
--durations=10), or raise NANOPNP_GATE_BUDGET_S together with the hook timeout
in .claude/settings.json. To commit anyway, add --no-verify.

Last 40 lines:

$(printf '%s' "$output" | tail -40)"
    fi
    fail "${lead} failed at \`${name}\`.

CLAUDE.md requires the whole gate — ruff check, ruff format --check, mypy src/,
pytest — to pass before committing. Fix this, then commit again. To commit
anyway, add --no-verify.

Last 40 lines of \`$*\`:

$(printf '%s' "$output" | tail -40)"
}

# The lock first: under UV_LOCKED a stale lock would otherwise surface as a
# confusing failure of whichever `uv run` stage came first.
$docs_only || check "uv lock --check" uv lock --check
check "ruff check"          uv run ruff check .
check "ruff format --check" uv run ruff format --check .
if $docs_only; then
    say "gate: only prose changed; lock check, mypy and pytest skipped."
else
    check "mypy --strict"   uv run mypy src/
    check "pytest"          uv run pytest -q
fi

[[ -n $state ]] && printf '%s\n' "$state" >"$stamp_file"
say "gate: passed."
exit 0
