#!/usr/bin/env bash
# .agents/hooks/adapter.sh
# Bidirectional payload and protocol adapter between Antigravity and Claude Code hooks.
set -uo pipefail

event=${1:-}
repo_root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "$repo_root"

input=$(cat)

case "$event" in
  pre-tool)
    # Extract command from Antigravity (.toolCall.args.CommandLine) or Claude (.tool_input.command)
    cmd=$(printf '%s' "$input" | jq -r '.toolCall.args.CommandLine // .tool_input.command // ""' 2>/dev/null || true)
    if [[ -z "$cmd" ]]; then
      jq -n '{"decision": "allow"}'
      exit 0
    fi

    # Synthesize Claude Code PreToolUse payload for gate.sh
    claude_payload=$(jq -n --arg cmd "$cmd" '{"tool_name": "Bash", "tool_input": {"command": $cmd}}')

    # Execute gate.sh
    output=$(printf '%s' "$claude_payload" | .claude/hooks/gate.sh 2>&1) || exit_code=$?
    exit_code=${exit_code:-0}

    # Inspect if gate.sh denied the tool call
    decision=$(printf '%s' "$output" | jq -r '.hookSpecificOutput.permissionDecision // empty' 2>/dev/null || true)
    if [[ "$decision" == "deny" ]]; then
      reason=$(printf '%s' "$output" | jq -r '.hookSpecificOutput.permissionDecisionReason // "Commit gate check failed"' 2>/dev/null || true)
      jq -n --arg reason "$reason" '{"decision": "deny", "reason": $reason}'
      exit 0
    fi

    # Allowed
    jq -n '{"decision": "allow"}'
    exit 0
    ;;

  post-tool)
    # Extract file path from Antigravity (.toolCall.args.TargetFile) or Claude (.tool_input.file_path)
    raw_path=$(printf '%s' "$input" | jq -r '.toolCall.args.TargetFile // .tool_input.file_path // ""' 2>/dev/null || true)
    if [[ -z "$raw_path" ]]; then
      exit 0
    fi

    # Normalize Windows network path (\\wsl.localhost\Arch\... or //wsl.localhost/Arch/...) to native Linux path
    norm_path=$(printf '%s' "$raw_path" | sed -E 's|^[\\/]{2}wsl\.localhost[\\/]Arch||I; s|\\|/|g')

    # Synthesize Claude Code PostToolUse payload for format.sh
    claude_payload=$(jq -n --arg p "$norm_path" '{"tool_name": "Edit", "tool_input": {"file_path": $p}}')

    # Execute format.sh
    printf '%s' "$claude_payload" | .claude/hooks/format.sh >/dev/null 2>&1 || true
    exit 0
    ;;

  session-start)
    if [[ -f .claude/hooks/session-start.sh ]]; then
      .claude/hooks/session-start.sh
    fi
    exit 0
    ;;

  *)
    exit 0
    ;;
esac
