# GitHub Copilot app host map

> This host has not been verified live. REV-166 to REV-168 record the open probes, accepted. Treat no
> substitute below as tested.

This file maps each Claude Code tool the workflow names to its Copilot substitute. Contract: [core](../core.md).

## What Copilot reads

| Source | On Copilot |
|---|---|
| `CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md` | All three load. `AGENTS.md` points to `CLAUDE.md` and imports nothing, so `CLAUDE.md` loads once |
| `.claude/rules/*.md` | Path-scoped instructions by their `paths:` globs, read on demand as on Claude Code |
| `.claude/agents/*.md` | Custom agents of the `task` tool. Pass `model` and `reasoning_effort` at the call (*Models*) |
| `.claude/skills/*/SKILL.md` | Skills: `/np-plan`, `/np-implement`, `/np-ship`, `/np-gui`, `steward` |
| `.claude/settings.json` hooks | The `Bash` and `Edit` matchers run |
| `.claude/settings.json` `permissions` | Not read. Tool approvals are the app's settings, per machine |
| `.github/hooks/nanopnp.json` | Copilot only. It gates `write_bash` through `.agents/hooks/adapter.sh` and refuses the GitHub MCP write tools |
| `.githooks/pre-push` | Git's own hook. It runs on either host and for the app's buttons, once the clone sets `core.hooksPath` |

When `COPILOT_CLI` is set, `session-start.sh` prints its summary as `{"additionalContext": …}`. That is
the only form Copilot reads. Open probes: REV-166 to REV-168.

## Questions

Use `ask_user`, one question per call, and at most four calls in a row. Put the recommended option
first and mark it *(Recommended)*. `ask_user` has no preview, so put each option's lines of
*Putting a choice to the author* (`.claude/workflow/author.md`) (you get, it costs, undo, it touches) in the question. Copilot always
offers a free answer, so add no "Other". Never ask in plain text.

## Agents and models

Use `task` with `agent_type` (a built-in or a custom agent's name), `model` and `reasoning_effort`
(*Models*). If `$ARGUMENTS` or `${CLAUDE_SKILL_DIR}` appears literally, read it so: the arguments are
the text after the command, and the directory is `.claude/skills/<name>/`.

### Models

Both hosts use the same Claude models (§8.2.25 AA7). Pass `model` at every `task` call that names an
agent or a plan's executor. Pass `reasoning_effort` too where a row gives one. If an id is missing
from the Copilot plan, take the nearest of the same tier and say so.

| Tier | Copilot `model` |
|---|---|
| Haiku | `claude-haiku-5.5` |
| Sonnet | `claude-sonnet-5.5` |
| Opus | `claude-opus-5.5` |

| Agent | Tier | `reasoning_effort` | Note |
|---|---|---|---|
| `physics-reviewer` | Opus | `high` | |
| `gui-reviewer` | Opus | `high` | |
| `ci-log-classifier` | Haiku | — | `omitClaudeMd` has no Copilot equivalent, so it may see `CLAUDE.md` |
| Built-in `code-review` | Sonnet | `xhigh` | Narrower than the Claude Code review (*Code review*) |

## Code review

Never call a skill named `code-review` on Copilot. The name resolves to whatever the machine has
installed. For `np-ship/wp.md` §4 and `np-plan/review.md`'s *The review*, call the built-in
`code-review` agent through `task` (*Models*).
Give it:

- the PR number;
- the base and head SHAs under **Verification**;
- `git diff origin/main...HEAD`;
- §4's brief.

The agent is read-only and reports only high-confidence bugs. This session therefore writes
`docs/code_reviews/CODE_REVIEW_NNN.md`. The file holds the base and head, the completed status, the
findings (an empty list is valid) and the line *Not assessed: the repository's standards, conformance
to the specification and the plan, and findings below high confidence.* §4's evidence rule and steps
1 to 3 then apply to the fixes. The narrower scope is a reason to ship from Claude Code.

## CI

The workflow uses a PR subscription, and Copilot has none. After a push in `np-ship/wp.md` §5 or the
steward, do three things: write the checkpoint into the PR's **Verification** (with `host: copilot`),
report *automation limit: re-run `/np-ship wp <n>` when CI ends*, and stop (§8.2.25 AA3).

On the §0.3 resume path, read the live PR state first. Then act on what you find:

- **Pending CI or unknown mergeability:** record any change and hand off again.
- **A new failed check or a conflict:** apply the steward's failure classes. After you gate and push a
  fix, checkpoint and stop.
- **Green and mergeable:** continue to §6.
- **Blocked otherwise:** report and hand off.
- **A merged or closed PR:** handle it as the steward says.

Never wait on CI with `sleep` or a loop. Keep the app's agent merge off. It would fix CI outside the
steward's failure classes.

## Safety hooks

- The gate refuses with an exit-0 structured denial (§8.2.26 AB1). `refuse()` in `gate.sh` prints
  `permissionDecision` top-level beside `hookSpecificOutput` on purpose: Copilot documents only the
  top-level form. Keep both.
- A timed-out hook lets the command through. The entries carry 1800 s.
- The gate reads one command. Never commit or push by typing into a running shell.
- The Commit and Push buttons run only git's hooks. Never use them.
- Hooks fire only on a WSL host. A `\\wsl.localhost\` path from `git rev-parse --show-toplevel`
  means both gates run by hand (`CLAUDE.md`, *Commands*).

Until REV-166 closes (its row in `docs/project/review-findings.md` gives its state), run the gate by
hand before each commit (`CLAUDE.md`'s hook-mode command, which stamps the tree) and `gate.sh run`
before each push. If a refusal or timeout is not honoured, the stop rule of the Copilot plan (§8.2.25
AA6) forbids Copilot commits until it is fixed.

## Session operations

- Start `.claude/hooks/gate.sh run > <log> 2>&1; echo "exit $?" >> <log>` with the shell tool's
  `mode: "async"`, and wait for its completion notice. Or run the `until grep` loop as a sync call
  with `initial_wait` up to 600 s, and issue it again until it ends. Never use `nohup`, `setsid` or `&`.
- At a `/compact` checkpoint, or at the pause of `/np-plan` or `/np-implement`, tick, gate, push, print the prompt and end the
  turn. The author compacts or starts a new session with it. The automatic checkpoint is off here: its Stop,
  PreCompact and `compact` hooks do not run, and `checkpoint.sh save` prints `off` under `COPILOT_CLI`.
- The scratchpad `<s>` is the `files/` directory of the session folder, which the session context
  names. Without it, use `${TMPDIR:-/tmp}/nanopnp-scratch/<branch>/`.
- Use the app's GitHub MCP for reads, or `gh` in WSL. Its file-write tools are refused, because they
  commit on GitHub where no gate runs. Add Context7 in the app, under Customize → MCP.
- The Claude web environment's stop hook is absent. Still end no turn on an unpushed commit.
- The commit trailer is `Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>`.

## GUI artefacts

`np-gui render` and `review` work. Artifact tools are unavailable, so run `publish` and `collect` on
Claude Code. `grill` needs publication first, so hand it off to Claude Code.

## Machine setup

1. Install the app at 1.1.14 or later, with **Settings → WSL hosts (Preview)** on. Open the WSL
   checkout as a WSL host. The agent's shell and every hook then run in Linux (§8.2.25 AA2).
2. In WSL, have `uv`, `jq`, `git`, a passing `gh auth status`, and Node with Playwright and Chromium
   for `np-gui render`. Run `uv sync --all-extras`, then `.claude/hooks/gate.sh run` once.
3. In the clone, run `git config core.hooksPath .githooks`. It covers every worktree of the clone,
   including a Claude Code checkout of it, where it is harmless: a Claude push needs the stamp
   already. `git config --unset core.hooksPath` undoes it.
4. Set Settings → Sessions → App instructions (per machine, not committed): "Run every command in WSL
   bash. Never use the app's Commit or Push buttons; commit and push through the shell, so the gate
   runs. Never commit by typing into a running shell. Leave agent merge off."
5. Add Context7 under Customize → MCP, and set tool approvals as wanted.
