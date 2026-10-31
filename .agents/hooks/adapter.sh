#!/usr/bin/env bash
# .agents/hooks/adapter.sh
# Payload and protocol adapter from Antigravity, and from GitHub Copilot's own tools, to the Claude Code hooks.
#
#   adapter.sh <event> [--dialect antigravity|copilot]
#
# antigravity, the default (.agents/hooks.json), answers {"decision": ...} and exits 0. copilot
# (.github/hooks/nanopnp.json) reads {toolName, toolArgs, cwd}, refuses with the reason on stderr, a
# top-level permissionDecision on stdout and exit 2, and allows silently.
set -uo pipefail

event=${1:-}
dialect=antigravity
[[ ${2:-} == --dialect ]] && dialect=${3:-}
case $dialect in
  antigravity | copilot) ;;
  *)
    printf '%s\n' "adapter.sh: unknown dialect \`$dialect\`." >&2
    exit 2
    ;;
esac
# The directory the host ran the tool in, kept before moving to the repo root:
# gate.sh gates the payload's `cwd`, so a commit made in a git worktree is gated
# against that worktree and not against the main checkout.
host_cwd=$PWD
repo_root=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
cd "$repo_root"

# A Windows-side path as the native Linux one: a WSL network path (\\wsl.localhost\<distro>\...
# or \\wsl$\<distro>\..., either slash, any distribution) loses its prefix, and a drive path
# (C:\...) becomes /mnt/c/...
normalise() {
  jq -rn --arg p "$1" '$p
    | if . == "" then .
      else
        gsub("\\\\"; "/")
        | sub("^//wsl(\\.localhost|\\$)/[^/]+"; ""; "i")
        | sub("^(?<d>[A-Za-z]):/"; "/mnt/" + (.d | ascii_downcase) + "/")
      end' 2>/dev/null || printf '%s' "$1"
}

refuse() {
  if [[ $dialect == copilot ]]; then
    printf '%s\n' "$1" >&2
    jq -n --arg reason "$1" '{permissionDecision: "deny", permissionDecisionReason: $reason}' 2>/dev/null
    exit 2
  fi
  jq -n --arg reason "$1" '{"decision": "deny", "reason": $reason}' 2>/dev/null \
    || printf '%s\n' '{"decision": "deny", "reason": "The commit gate refused the call (is jq installed?)"}'
  exit 0
}

allow() {
  [[ $dialect == copilot ]] || jq -n '{"decision": "allow"}'
  exit 0
}

# Copilot sends toolArgs as an object, or as a JSON string.
copilot_args='(.toolArgs | if type == "string" then fromjson else . end) // {}'

case "$event" in
  pre-tool)
    input=$(cat)
    if [[ $dialect == copilot ]]; then
      # write_bash types `.input` into a running shell, where {enter} is the Enter key.
      cmd_jq="$copilot_args"' | (.command // .input // "") | gsub("\\{enter\\}"; "\n"; "i")'
      cwd_jq='.cwd // ""'
    else
      cmd_jq='.toolCall.args.CommandLine // .tool_input.command // ""'
      cwd_jq='.toolCall.args.Cwd // .cwd // ""'
    fi
    # An unparseable payload (no jq, malformed JSON) is a refusal, not an allow:
    # a command this shim cannot read may be a commit. Only a payload that parses
    # and carries no command (not a shell tool call) is let through.
    if ! cmd=$(printf '%s' "$input" | jq -r "$cmd_jq" 2>&1); then
      refuse "The commit gate could not read the tool call payload: ${cmd:-is jq installed?}"
    fi
    [[ -n "$cmd" ]] || allow
    cwd=$(printf '%s' "$input" | jq -r "$cwd_jq" 2>/dev/null || true)
    cwd=$(normalise "$cwd")
    [[ -n "$cwd" && -d "$cwd" ]] || cwd=$host_cwd

    # Synthesize Claude Code PreToolUse payload for gate.sh
    claude_payload=$(jq -n --arg cmd "$cmd" --arg cwd "$cwd" '{"tool_name": "Bash", "tool_input": {"command": $cmd}, "cwd": $cwd}')

    # gate.sh allows with no output or a {systemMessage} pass note, and refuses with exit 2
    # and a deny object on stdout. Any other exit status, a deny, or stdout this shim cannot
    # parse is a refusal: a gate that crashed or was not executable has not passed.
    exit_code=0
    errors=$(mktemp 2>/dev/null) || errors=""
    output=$(printf '%s' "$claude_payload" | .claude/hooks/gate.sh 2>"${errors:-/dev/null}") || exit_code=$?
    stderr_text=""
    if [[ -n $errors ]]; then
      stderr_text=$(cat "$errors")
      rm -f "$errors"
    fi
    decision=none
    if [[ -n "$output" ]]; then
      decision=$(printf '%s' "$output" | jq -r '.permissionDecision // .hookSpecificOutput.permissionDecision // "none"' 2>/dev/null) ||
        decision=unparseable
    fi

    if [[ $exit_code -ne 0 || $decision == deny || $decision == unparseable ]]; then
      reason=$(printf '%s' "$output" | jq -r '.permissionDecisionReason // .hookSpecificOutput.permissionDecisionReason // empty' 2>/dev/null || true)
      [[ -n "$reason" ]] || reason="The commit gate did not pass (exit ${exit_code}):
$(printf '%s\n%s' "$output" "$stderr_text" | tail -40)"
      refuse "$reason"
    fi
    allow
    ;;

  post-tool)
    input=$(cat)
    # Antigravity (.toolCall.args.TargetFile), Claude (.tool_input.file_path) or Copilot (.toolArgs.path).
    if [[ $dialect == copilot ]]; then
      path_jq="$copilot_args"' | .path // .file_path // ""'
    else
      path_jq='.toolCall.args.TargetFile // .tool_input.file_path // ""'
    fi
    norm_path=$(printf '%s' "$input" | jq -r "$path_jq" 2>/dev/null) || exit 0
    norm_path=$(normalise "$norm_path")
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
