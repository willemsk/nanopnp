# GitHub Copilot app host mapping

The shared contract is [the workflow core](../core.md); [the host index](../hosts.md) selects this
file. The plan and its review are `docs/plans/copilot-host.md`.

## What Copilot reads

Seen in app 1.1.34 (runtime 1.0.102), 31 October 2026. A separate WSL shell reported Copilot CLI
1.0.105; these are different version identifiers.

| Source | On Copilot |
|---|---|
| `CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md` | All three load. `AGENTS.md` imports `CLAUDE.md`, so `CLAUDE.md` loads twice |
| `.claude/rules/*.md` | Loaded as path-scoped instructions by their `paths:` globs, read on demand as on Claude Code |
| `.claude/agents/*.md` | Listed as custom agents of the `task` tool. Pass `model` and `reasoning_effort` at the call (*Models*) |
| `.claude/skills/*/SKILL.md` | Listed as skills; `/np-plan`, `/np-implement`, `/np-ship`, `/np-gui`, `steward` |
| `.claude/settings.json` hooks | The `Bash` and `Edit` matchers ran in the WSL probe; other tools and hook sources remain under REV-166 |
| `.claude/settings.json` `permissions` | Not read. Tool approvals are the app's settings, per machine |
| `.github/hooks/nanopnp.json` | Configured for Copilot only: gates `write_bash`, formats after `edit`, `create` and `apply_patch`, refuses the GitHub MCP write tools. A probe in this source fired in a fresh session; this file's write-tool paths and revised matcher remain unverified live under REV-166 |
| `.githooks/pre-push` | Git's own hook, on either host and for the app's buttons, once the clone sets `core.hooksPath` |

The WSL probe's shared shell and edit hooks had `COPILOT_CLI` and `CLAUDE_PROJECT_DIR` set;
Claude Code does not set `COPILOT_CLI`. `session-start.sh` uses it to print its summary as
`{"additionalContext": …}`, the only form Copilot reads. The session-start hook itself was not
reprobed.

## Questions

Use `ask_user`, one question per call, at most four calls in a row. Put the recommended option
first and mark it *(Recommended)*; include each option's consequence in the question if the tool
has no choice descriptions. A free answer is always offered, so add no "Other". Never ask in plain
text; the numbered-message fallback is not used.

## Agents and models

Use `task` with `agent_type` (a built-in or a custom agent's name), `model` and
`reasoning_effort` (*Models*). If `$ARGUMENTS` or `${CLAUDE_SKILL_DIR}` appears literally, the
arguments are the text after the command and the directory is `.claude/skills/<name>/`.

### Models

The tiers of §8.4.5 are the same Claude models on either host (§8.2.25 AA7). Pass `model`, and
`reasoning_effort` where a row gives one, at every `task` call that names an agent or a plan's
executor: whether Copilot reads `model:` and `effort:` from `.claude/agents/` is REV-167. What is
offered depends on the Copilot plan and the organisation's policy; if an id is missing, take the
nearest id of the same tier and say so.

| Tier | Copilot `model` |
|---|---|
| Haiku | `claude-haiku-5.5` |
| Sonnet | `claude-sonnet-5.5` |
| Opus | `claude-opus-5.5` |

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

## Safety hooks

- `gate.sh` writes the reason on stderr and one JSON object with a top-level
  `permissionDecision` beside `hookSpecificOutput`. It exits 0 on Copilot and 2 on Claude Code
  (§8.2.26 AB1); inability to emit the JSON exits 2. In the WSL probe, both exit-0 decision
  shapes blocked the shell command and gave the reason, whereas exit 2 blocked with only a generic
  message. The Copilot-specific hook file's refusal is not yet verified live.
- A hook that times out lets the command through on both hosts. The gate's entries carry
  `timeout: 1800`. A fresh-session probe with each source configured for 60 seconds completed a
  40-second denial, beyond the 30-second default; the full 1,800-second limit was not measured.
- `gate.sh` lets an unparseable `tool_input` through (`jq … || exit 0`), and Copilot passes a
  string when the arguments are not JSON. The `write_bash` path through `.agents/hooks/adapter.sh`
  refuses one.
- `gate.sh` reads one command. It cannot see a `cd` typed earlier into a running shell, or a command
  recalled by a key. Never commit or push by typing into a running shell.
- The app's Commit and Push buttons run Git's hooks, not the agent's. `pre-push` refuses an unstamped
  push; nothing gates a commit made by a button, so never use them.
- Hooks need a WSL host session. In the native Windows app on a `\\wsl.localhost\` path, the session
  is a folder, not a repository, and no repository hook fires: run both gates of `CLAUDE.md`'s
  *Commands* by hand, in WSL, before each commit and push.

Until REV-166 is closed, run the gate by hand before each commit and push on Copilot. If no refusal
form is obeyed or a configured timeout is not honoured, the Phase 0 stop rule forbids Copilot
commits until fixed.

## Session operations

- Start `.claude/hooks/gate.sh run > <log> 2>&1; echo "exit $?" >> <log>` with the shell tool's
  `mode: "async"` and wait for its completion notice, or run the `until grep` loop as a sync call
  with `initial_wait` up to 600 s, issued again until it ends. Never `nohup`, `setsid` or `&`.
- At a `/compact` checkpoint, tick, gate, push, print the prompt and end the turn. The author
  compacts, or starts a new session with the prompt. The app also compacts by itself.
- The scratchpad `<s>` is the session folder's `files/` directory, which the session context names;
  else `${TMPDIR:-/tmp}/nanopnp-scratch/<branch>/`.
- Use the app's GitHub MCP for reads, or `gh` in WSL. Its file-write tools are refused: they commit
  on GitHub where no gate runs. Add Context7 in the app, Customize → MCP.
- The Claude web environment's stop hook is absent; still end no turn on an unpushed commit.
- The commit trailer is `Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>`.

## GUI artifacts

`np-gui render` and `review` work on Copilot. Artifact tools are unavailable: run `publish` and
`collect` on Claude Code. `grill` needs publication before asking, so it cannot complete on
Copilot; hand it off to Claude Code rather than asking without the published boards.

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

- **REV-166**: in a fresh WSL repository session, preinstalled `.github/hooks` and
  `.claude/settings.local.json` probes both fired before and after shell, patch and GitHub MCP read
  calls. Each source blocked with an exit-0 structured denial and its reason, and with exit 2 and a
  generic reason; each also blocked after a 40-second sleep under a 60-second timeout. Sample
  ordering and tool shapes are in the REV record, not a guarantee of total order. The GitHub probe
  named patch calls `apply_patch`; the Claude source named them `Edit` with a raw patch string.
  The shared formatter handles its multiple paths; the Copilot adapter and matcher now handle
  `apply_patch` too, but that revised hook path has only been replayed offline. `write_bash`, GitHub
  MCP write tools and a distinct create tool were unavailable, so their payloads, matchers and
  actual adapter paths remain unverified. Sanitised payloads are in `.claude/hooks/fixtures/`.
- **REV-167**: the app's behaviour. Whether the Commit and Push buttons pass `--no-verify`; whether
  `$ARGUMENTS` is substituted; whether `/compact` can be called by hand; whether a coding session has
  the session-automation tool; whether `CLAUDE.md` can be turned off for Copilot alone; how
  `model:`, `effort:` and `omitClaudeMd` in `.claude/agents/` are treated.
- **REV-168**: the plan's live verification, in the Copilot app and as a regression in Claude Code.
