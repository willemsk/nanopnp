#!/bin/bash
# The automatic checkpoint: a compaction checkpoint of /np-implement, or its pause before /np-ship,
# that goes on instead of ending the turn, when the author opts in.
#
#   NANOPNP_AUTO_CHECKPOINT=1  /np-implement's compaction checkpoints go on to the next item
#   NANOPNP_AUTO_SHIP=1        /np-implement's pause after its report goes on into /np-ship
#
# No hook can start a compaction, so Claude Code's own auto-compaction, when the context fills, takes
# the checkpoint's place. This script carries the checkpoint's prompt across it:
#
#   checkpoint.sh save <implement|ship> <plan> <wp n>   the prompt on stdin. With the switch on, saves
#                  it under .git and prints `on`; with it off, or without jq, clears any saved one
#                  and prints `off`.
#   checkpoint.sh clear                                  forgets the saved checkpoint.
#   checkpoint.sh                                        hook mode, the payload on stdin:
#     PreCompact              prints the saved prompt, which becomes the compaction's instructions;
#     SessionStart (compact)  prints it again with the command to resume, into the compacted context;
#     Stop                    blocks once a turn that ends while the saved checkpoint has work left.
#
# The prompt is saved only for the branch it was written on. Nothing here may fail a session: every
# error exits 0 and says nothing.
set -uo pipefail

root=${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}
cd "$root" 2>/dev/null || exit 0
dir=$(git rev-parse --path-format=absolute --git-path nanopnp-checkpoint 2>/dev/null) || exit 0
branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)

# Only Claude Code runs the three hooks (.claude/workflow/hosts/copilot.md), so another host's switch
# is off whatever the environment says. Hook mode needs jq: without it the switch is off too.
switch_on() {
    [ -z "${COPILOT_CLI:-}" ] || return 1
    command -v jq >/dev/null 2>&1 || return 1
    case $1 in
        implement) [ "${NANOPNP_AUTO_CHECKPOINT:-}" = 1 ] ;;
        ship) [ "${NANOPNP_AUTO_SHIP:-}" = 1 ] ;;
        *) return 1 ;;
    esac
}

case ${1:-} in
    save)
        kind=${2:-} plan=${3:-} wp=${4:-}
        if [ -z "$kind" ] || [ -z "$plan" ] || [ -z "$wp" ]; then
            echo "usage: checkpoint.sh save <implement|ship> <plan> <wp n>" >&2
            exit 2
        fi
        if ! switch_on "$kind"; then
            rm -rf "$dir"
            echo off
            exit 0
        fi
        rm -rf "$dir" && mkdir -p "$dir" || exit 1
        printf '%s\n' "$kind" >"$dir/kind"
        printf '%s\n' "$branch" >"$dir/branch"
        printf '%s\n' "$plan" >"$dir/plan"
        printf '%s\n' "$wp" >"$dir/wp"
        cat >"$dir/prompt"
        echo on
        exit 0
        ;;
    clear)
        rm -rf "$dir"
        exit 0
        ;;
    "") ;;
    *)
        echo "usage: checkpoint.sh [save <implement|ship> <plan> <wp n> | clear]" >&2
        exit 2
        ;;
esac

# Hook mode.
payload=$(cat)
[ -d "$dir" ] || exit 0
command -v jq >/dev/null 2>&1 || exit 0
kind=$(cat "$dir/kind" 2>/dev/null) || exit 0
saved_branch=$(cat "$dir/branch" 2>/dev/null) || exit 0
plan=$(cat "$dir/plan" 2>/dev/null) || exit 0
wp=$(cat "$dir/wp" 2>/dev/null) || exit 0
# The switch was read when the prompt was saved, from the Bash tool's environment: a hook may not see
# a variable set in a settings file's `env`.
[ "$saved_branch" = "$branch" ] || exit 0

event=$(printf '%s' "$payload" | jq -r '.hook_event_name // ""' 2>/dev/null)

# The first unticked work item of the plan, as "13", or nothing when every item is ticked.
next_item() {
    grep -m1 -E '^- \[ \] [0-9]+\.' "$plan" 2>/dev/null | sed -E 's/^- \[ \] ([0-9]+)\..*/\1/'
}

if [ "$kind" = implement ]; then
    resume="/np-implement wp $wp"
    switch=NANOPNP_AUTO_CHECKPOINT
else
    resume="/np-ship wp $wp"
    switch=NANOPNP_AUTO_SHIP
fi
# A saved checkpoint outlives the session that saved it; this tells a later one how to drop it.
stale="If $switch is not 1 in your environment, the checkpoint is stale: run .claude/hooks/checkpoint.sh clear and go on with what the author asked."

case $event in
    PreCompact)
        printf 'The automatic checkpoint (%s=1) saved this prompt for the compaction:\n\n' "$switch"
        cat "$dir/prompt"
        ;;
    SessionStart)
        [ "$(printf '%s' "$payload" | jq -r '.source // ""' 2>/dev/null)" = compact ] || exit 0
        printf -- '- automatic checkpoint (%s=1): the compaction carried the prompt below. Go on with %s now, without waiting for the author. %s\n\n' "$switch" "$resume" "$stale"
        cat "$dir/prompt"
        ;;
    Stop)
        [ "$(printf '%s' "$payload" | jq -r '.stop_hook_active // false' 2>/dev/null)" = true ] && exit 0
        if [ "$kind" = implement ]; then
            item=$(next_item)
            if [ -z "$item" ]; then
                rm -rf "$dir"
                exit 0
            fi
            reason="The automatic checkpoint is on ($switch=1): a compaction checkpoint does not end the turn. Go on with item $item of $plan; Claude Code compacts when the context fills, and the hooks carry the checkpoint's prompt across. If the turn ends for something the author must answer, end it again. $stale"
        else
            reason="The automatic pause is on ($switch=1): go on into $resume now (the np-ship skill with \"wp $wp\"). If the turn ends for something the author must answer, end it again. $stale"
        fi
        jq -n --arg reason "$reason" '{decision: "block", reason: $reason}'
        ;;
esac
exit 0
