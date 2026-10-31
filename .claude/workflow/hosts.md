# Hosts other than Claude Code

The workflow runs on Claude Code and on the GitHub Copilot app, and either host runs any step on
either lane (§8.4.4; §8.2.25 AA1). `.claude/` is the single source. This file maps each Claude
Code construct that the workflow files name to its substitute on Copilot; on Claude Code, ignore
it. The plan and its review are `docs/plans/copilot-host.md`.

## What Copilot reads

Seen in app 1.1.34 (runtime 1.0.102), 31 October 2026.

| Source | On Copilot |
|---|---|
| `CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md` | All three load. `AGENTS.md` imports `CLAUDE.md`, so `CLAUDE.md` loads twice |
| `.claude/rules/*.md` | Loaded as path-scoped instructions by their `paths:` globs, read on demand as on Claude Code |
| `.claude/agents/*.md` | Listed as custom agents of the `task` tool. Pass `model` and `reasoning_effort` at the call (*Models*) |
| `.claude/skills/*/SKILL.md` | Listed as skills; `/np-plan`, `/np-implement`, `/np-ship`, `/np-gui`, `steward` |
| `.claude/settings.json` hooks | Run, with Claude's payload; the `Bash` matcher takes `bash` and `powershell`, not `write_bash` |
| `.claude/settings.json` `permissions` | Not read. Tool approvals are the app's settings, per machine |
| `.github/hooks/nanopnp.json` | Copilot only: gates `write_bash`, formats after `edit` and `create`, refuses the GitHub MCP write tools |
| `.githooks/pre-push` | git's own hook, on either host and for the app's buttons, once the clone sets `core.hooksPath` |

The agent's shell has `COPILOT_CLI=1`; Claude Code does not set it. `session-start.sh` uses it to
print its summary as `{"additionalContext": …}`, the only form Copilot reads.

## The gate on Copilot

- `gate.sh` refuses with exit 2, the reason on stderr and one JSON object with a top-level
  `permissionDecision` beside `hookSpecificOutput`. Both hosts block on exit 2.
- A hook that times out lets the command through on both hosts. The gate's entries carry
  `timeout: 1800`; whether Copilot honours it is REV-166.
- `gate.sh` lets an unparseable `tool_input` through (`jq … || exit 0`), and Copilot passes a
  string when the arguments are not JSON. The `write_bash` path through `.agents/hooks/adapter.sh`
  refuses one.
- `gate.sh` reads one command. It cannot see a `cd` typed earlier into a running shell, or a command
  recalled by a key. Never commit or push by typing into a running shell.
- The app's Commit and Push buttons run git's hooks, not the agent's. `pre-push` refuses an unstamped
  push; nothing gates a commit made by a button, so never use them.
- Hooks need a WSL host session. In the native Windows app on a `\\wsl.localhost\` path, the session
  is a folder, not a repository, and no repository hook fires: run both gates of `CLAUDE.md`'s
  *Commands* by hand, in WSL, before each commit and push.

## Substitutes

| Claude Code (where) | Copilot |
|---|---|
| `$ARGUMENTS`, `${CLAUDE_SKILL_DIR}` (each `SKILL.md`) | If either appears literally, the arguments are the text after the command and the directory is `.claude/skills/<name>/` |
| `AskUserQuestion` (`np-plan/rulings.md`, `np-gui/grill.md`) | `ask_user`, one question per call, with its options as choices, the recommended one first and marked *(Recommended)*. "At most four per call" becomes at most four calls in a row. A free answer is always offered, so add no "Other". Never ask in plain text; the numbered-message fallback is not used |
| `Agent` with a type and a model | `task` with `agent_type` (a built-in or a custom agent's name), `model` and `reasoning_effort` (*Models*) |
| A `/compact` checkpoint (§8.4.4) | Do the checkpoint as written: tick, gate, push, print the prompt, end the turn. The author compacts, or starts a new session with the prompt. The app also compacts by itself |
| `run_in_background` and the `until grep` wait (`CLAUDE.md`, *Commands*) | The shell tool's `mode: "async"`: start `.claude/hooks/gate.sh run > <log> 2>&1; echo "exit $?" >> <log>` and wait for its completion notice, or run the `until grep` loop as a sync call with `initial_wait` up to 600 s, issued again until it ends. Never `nohup`, `setsid` or `&` |
| `Skill(code-review …)` (`np-ship/wp.md` §4) | *Code review* below |
| `subscribe_pr_activity`, fallback check-ins (`np-ship/wp.md` §4 to §6, steward *Bounded wakes*) | *CI* below |
| `mcp__github__*` | The app's GitHub MCP for reads, or `gh` in WSL. Its write tools are refused: they commit on GitHub where no gate runs |
| Artifact tools (`np-gui publish`, `collect`) | None. Run these two levels on Claude Code. `render` and `review` work on Copilot |
| The scratchpad `<s>` (`np-gui`) | The session folder's `files/` directory, which the session context names; else `${TMPDIR:-/tmp}/nanopnp-scratch/<branch>/` |
| Context7 MCP | Add it in the app, Customize → MCP |
| The Claude web environment's stop hook | None; still end no turn on an unpushed commit |
| The commit trailer | `Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>` |

## Models

The tiers of §8.4.5 are the same Claude models on either host (§8.2.25 AA7). Pass `model`, and
`reasoning_effort` where a row gives one, at every `task` call that names an agent or a plan's
executor: whether Copilot reads `model:` and `effort:` from `.claude/agents/` is REV-167. What is
offered depends on the Copilot plan and the organisation's policy; if an id is missing, take the
nearest id of the same tier and say so.

| Tier | Claude Code | Copilot `model` |
|---|---|---|
| Haiku | `haiku` | `claude-haiku-5.5` |
| Sonnet | `sonnet` | `claude-sonnet-5.5` |
| Opus | `opus` | `claude-opus-5.5` |

| Agent | Tier | `reasoning_effort` | Note |
|---|---|---|---|
| `physics-reviewer` | Opus | `high` | |
| `gui-reviewer` | Sonnet | `high` | |
| `ci-log-classifier` | Haiku | — | `omitClaudeMd` has no Copilot equivalent, so it may see `CLAUDE.md` (REV-167) |

## Code review

`code-review` is not a repository skill. On Copilot the name resolves to whatever skill the machine
has installed, so never call a skill by that name there. Instead, `np-ship/wp.md` §4 calls the
built-in `code-review` agent through `task` with `reasoning_effort: "xhigh"`, giving it the PR
number, the base and head SHAs recorded under **Verification**, `git diff origin/main...HEAD` and
§4's brief. The agent is read-only and reports only high-confidence bugs and logic errors. So this
session writes `docs/code_reviews/CODE_REVIEW_NNN.md`: the reviewed base and head, the completed
status, the findings (an empty list is valid), and a line *Not assessed: the repository's standards,
conformance to the specification and the plan, and findings below high confidence.* §4's evidence
rule and its steps 1 to 3 then apply to the fixes this session makes. The narrower scope is a reason
to ship from Claude Code.

## CI

Copilot has no PR subscription the workflow uses. At `np-ship/wp.md` §5 and in the steward: push,
write the checkpoint into the PR's **Verification** (with `host: copilot`), report *automation
limit: re-run `/np-ship wp <n>` when CI ends*, and stop (§8.2.25 AA3). Never wait on CI with
`sleep` or a loop. `np-ship/wp.md` §0 step 3 resumes. The app's agent merge stays off on nanopnp
pull requests: it would fix CI outside the steward's failure classes.

## Machine setup

1. The app at 1.1.14 or later, with **Settings → WSL hosts (Preview)** on. Open the WSL checkout as
   a WSL host; the agent's shell and every hook then run in Linux (§8.2.25 AA2).
2. In WSL: `uv`, `jq`, `git`, `gh auth status`, and Node with Playwright and Chromium for
   `np-gui render`. Run `uv sync --all-extras`, then `.claude/hooks/gate.sh run` once.
3. In the clone: `git config core.hooksPath .githooks`. It covers every worktree of the clone,
   including a Claude Code checkout of it, where it is harmless: a Claude push needs the stamp
   already. `git config --unset core.hooksPath` undoes it.
4. Settings → Sessions → App instructions (per machine, not committed): "Run every command in WSL
   bash. Never use the app's Commit or Push buttons; commit and push through the shell, so the gate
   runs. Never commit by typing into a running shell. Leave agent merge off."
5. Context7 under Customize → MCP; tool approvals as wanted.

## Not yet checked

Built before the plan's Phase 0 probes ran (§8.2.25 AA6). Until REV-166 is closed, run the gate by
hand before each commit and push on Copilot, as on a folder session.

- **REV-166**: the hook probes. Which sources fire and in what order; the payload names
  (`write_bash`'s `.input`, a string or object `toolArgs`, the MCP tool names); whether
  `COPILOT_CLI` reaches a hook; whether Claude's `PostToolUse` matcher takes `edit` and `create`;
  whether the exit-2 refusal lands with its reason; whether `timeout: 1800` is honoured.
- **REV-167**: the app's behaviour. Whether the Commit and Push buttons pass `--no-verify`; whether
  `$ARGUMENTS` is substituted; whether `/compact` can be called by hand; whether a coding session has
  the session-automation tool; whether `CLAUDE.md` can be turned off for Copilot alone; how
  `model:`, `effort:` and `omitClaudeMd` in `.claude/agents/` are treated.
- **REV-168**: the plan's live verification, in the Copilot app and as a regression in Claude Code.
