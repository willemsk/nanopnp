#!/usr/bin/env bash
# The roster guard of WP43 D13 (SPECIFICATION.md §8.2.10 J8): a PreToolUse hook on `Agent`
# (older Claude Code versions name the same tool `Task`, and so does this hook).
#
# A call's `model` overrides the agent file's, and a spawn without one inherits the
# session's. This hook keeps the two honest:
#   - a roster agent (a file in .claude/agents/) called with a `model` other than its
#     file's is denied;
#   - any other agent, `fork` aside, called without an explicit `model` is denied.
# Each denial names the agent, the models and .claude/model-policy.md. Everything else
# passes, and so does a payload that cannot be parsed. Reads the payload with jq, as
# gate.sh does.
set -uo pipefail

payload=$(cat)
tool=$(printf '%s' "$payload" | jq -r '.tool_name // ""' 2>/dev/null) || exit 0
[[ $tool == Agent || $tool == Task ]] || exit 0
type=$(printf '%s' "$payload" | jq -r '.tool_input.subagent_type // ""' 2>/dev/null) || exit 0
model=$(printf '%s' "$payload" | jq -r '.tool_input.model // ""' 2>/dev/null) || exit 0
session_dir=$(printf '%s' "$payload" | jq -r '.cwd // ""' 2>/dev/null) || session_dir=""

# The agent files live beside this hook, whichever tree the session runs in.
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd) || root=${session_dir:-.}

deny() {
    jq -n --arg reason "$1" '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $reason}}'
    exit 0
}

[[ $type == fork ]] && exit 0

file="$root/.claude/agents/$type.md"
if [[ -n $type && $type != */* && -f $file ]]; then
    declared=$(sed -n '/^---$/,/^---$/{s/^model:[[:space:]]*//p;}' "$file" | head -n 1 | tr -d '[:space:]')
    if [[ -n $model && -n $declared && $model != "$declared" ]]; then
        deny "Agent '$type' is defined with model '$declared' in .claude/agents/$type.md; the call asks for '$model'. Omit the model or pass '$declared'. See .claude/model-policy.md."
    fi
    exit 0
fi

if [[ -z $model ]]; then
    deny "Agent '${type:-general-purpose}' was called without an explicit model, so it would run on the session's. Pass model (opus, sonnet or haiku) by the failure mode of the task. See .claude/model-policy.md."
fi
exit 0
