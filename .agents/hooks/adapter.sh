#!/usr/bin/env bash
# .agents/hooks/adapter.sh
# Bidirectional payload and protocol adapter between Antigravity and Claude Code hooks.
set -uo pipefail

event=${1:-}
# The directory the host ran the tool in, kept before moving to the repo root:
# gate.sh gates the payload's `cwd`, so a commit made in a git worktree is gated
# against that worktree and not against the main checkout.
host_cwd=$PWD
repo_root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "$repo_root"

case "$event" in
  pre-tool)
    input=$(cat)
    # Extract command from Antigravity (.toolCall.args.CommandLine) or Claude (.tool_input.command)
    # An unparseable payload (no jq, malformed JSON) is a refusal, not an allow:
    # a command this shim cannot read may be a commit. Only a payload that parses
    # and carries no command (not a shell tool call) is let through.
    if ! cmd=$(printf '%s' "$input" | jq -r '.toolCall.args.CommandLine // .tool_input.command // ""' 2>&1); then
      jq -n --arg err "$cmd" '{"decision": "deny", "reason": ("The commit gate could not read the tool call payload: " + $err)}' 2>/dev/null \
        || printf '%s\n' '{"decision": "deny", "reason": "The commit gate could not read the tool call payload (is jq installed?)"}'
      exit 0
    fi
    if [[ -z "$cmd" ]]; then
      jq -n '{"decision": "allow"}'
      exit 0
    fi
    cwd=$(printf '%s' "$input" | jq -r '.toolCall.args.Cwd // .cwd // ""' 2>/dev/null || true)
    [[ -n "$cwd" && -d "$cwd" ]] || cwd=$host_cwd

    # Synthesize Claude Code PreToolUse payload for gate.sh
    claude_payload=$(jq -n --arg cmd "$cmd" --arg cwd "$cwd" '{"tool_name": "Bash", "tool_input": {"command": $cmd}, "cwd": $cwd}')

    # Execute gate.sh. In hook mode it prints a JSON denial on stdout and nothing
    # when it allows, so any exit status other than 0, or any output that is
    # not a parsed "allow", is a refusal: a gate that crashed, was not
    # executable, or wrote something this shim cannot parse has not passed.
    exit_code=0
    output=$(printf '%s' "$claude_payload" | .claude/hooks/gate.sh 2>&1) || exit_code=$?

    if [[ $exit_code -ne 0 || -n "$output" ]]; then
      reason=$(printf '%s' "$output" | jq -r '.hookSpecificOutput.permissionDecisionReason // empty' 2>/dev/null || true)
      [[ -n "$reason" ]] || reason="The commit gate did not pass (exit ${exit_code}):
$(printf '%s' "$output" | tail -40)"
      jq -n --arg reason "$reason" '{"decision": "deny", "reason": $reason}'
      exit 0
    fi

    # Allowed
    jq -n '{"decision": "allow"}'
    exit 0
    ;;

  post-tool)
    input=$(cat)
    # Extract and normalise file path from Antigravity (.toolCall.args.TargetFile) or Claude (.tool_input.file_path).
    # Normalise a Windows-side path to the native Linux one: a WSL network path
    # (\\wsl.localhost\<distro>\... or \\wsl$\<distro>\..., either slash, any
    # distribution) loses its prefix, and a drive path (C:\...) becomes /mnt/c/...
    norm_path=$(printf '%s' "$input" | jq -r '
      (.toolCall.args.TargetFile // .tool_input.file_path // "")
      | if . == "" then empty
        else
          gsub("\\\\"; "/")
          | sub("^//wsl(\\.localhost|\\$)/[^/]+"; ""; "i")
          | sub("^(?<d>[A-Za-z]):/"; "/mnt/" + (.d | ascii_downcase) + "/")
        end
    ' 2>/dev/null || true)
    if [[ -z "$norm_path" ]]; then
      exit 0
    fi

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
