# Plan: run the nanopnp workflow in the GitHub Copilot app beside Claude Code

Planning, not requirements: `SPECIFICATION.md` governs. Phase 6 below writes the specification change that
this plan needs.

## In brief

**What changes.** The author can run a second coding assistant, the GitHub Copilot desktop app, beside Claude
Code on the same project, and it obeys the same rules: the same instructions, the same safety checks before
each commit and push, the same reviewers and the same three-step planning, building and shipping routine.
Either assistant can pick up any step.

**Cost.** About an hour of setup and checks by hand in the Copilot app, then one small change to the
project's tooling and its process text, built by Copilot and shipped from Claude Code. No program code
changes.

**What could go wrong.** Copilot could skip a safety check: its hooks let a command through when they run
out of time, and its own commit and push buttons run no hooks at all. The setup sets a long time limit and
adds a check git itself runs before a push. The two assistants could also trip over each other on one
branch; one assistant drives a branch at a time, and the branch says which.

**Your call.** Nothing waits on you; the three choices (Windows with the project in WSL, either assistant
for any step, Copilot stops and reports rather than waiting for the automated checks) are made.

## Context

The author wants the GitHub Copilot desktop app to work as a second agent host, running concurrently with
Claude Code. It should get the same instructions, path rules, hooks (the commit gate, the push guard, auto-format,
session start), sub-agents and the `/np-plan`, `/np-implement`, `/np-ship`, `/np-gui` and steward workflows.

The author has decided three things:
- **Host:** the Copilot app on Windows, with the checkout in WSL.
- **Division:** the hosts are **interchangeable**, so either one runs any step on either lane.
- **CI:** in Copilot, `/np-ship` reports an automation limit and stops instead of waiting on CI.

The repo is already halfway portable. `AGENTS.md` imports `@CLAUDE.md`, and `.agents/hooks/adapter.sh` translates
Antigravity hook payloads into what `.claude/hooks/gate.sh` and `format.sh` expect. The Copilot app shares Copilot
CLI's customisation model (verified against GitHub Docs, Oct 2026):

| Copilot reads natively | So nothing to do |
|---|---|
| `CLAUDE.md`, `AGENTS.md` (with `@path` imports expanded) | instructions load as-is |
| `.claude/skills/*/SKILL.md` (also `.github/skills`, `.agents/skills`) | `/np-plan`, `/np-implement`, `/np-ship`, `/np-gui`, `steward` appear as skills |
| `.claude/settings.json` hooks (Copilot CLI: "cross-tool … also read"); PascalCase events get Claude-style snake_case payloads and tool names | possibly the gate fires unchanged — **verify, see Phase 0** |

| Copilot needs its own file | Claude source |
|---|---|
| `.github/instructions/*.instructions.md` (`applyTo:` glob; **no** `@` import expansion) | `.claude/rules/*.md` (`paths:`) |
| `.github/agents/<name>.agent.md` (frontmatter `name, description, tools, model, include-custom-instructions`; `Read, Grep, Glob` map to `read`/`search`) | `.claude/agents/*.md` (`model: haiku/sonnet/opus`, `effort`, `omitClaudeMd` not understood) |
| `.github/hooks/*.json` (`version: 1`; camelCase events `sessionStart`, `preToolUse`, `postToolUse`; stdin `{cwd, toolName, toolArgs}`; deny = stdout `{"permissionDecision":"deny","permissionDecisionReason":…}`; non-zero exit **denies** (fail-closed); **timeout allows** (fail-open, default 30 s); sessionStart consumes only `{"additionalContext": …}`) | `.claude/settings.json` hooks |

**Design rule:** `.claude/` stays the single source of truth. Everything Copilot-specific is either a thin pointer
or a generated file under `.github/`, plus one mapping document, `.claude/workflow/hosts.md`. The weak forms are
not the only thing kept from being written twice: the workflow is not duplicated either.

## Gaps the plan closes (Claude-only constructs used by the workflow)

| Construct (where) | Copilot substitute |
|---|---|
| `$ARGUMENTS`, `${CLAUDE_SKILL_DIR}` (every `SKILL.md`) | No substitution in Copilot. Add one line per SKILL.md: arguments are the text after `/np-x`; the dir is `.claude/skills/np-x/` |
| `AskUserQuestion` (`np-plan/rulings.md`, `np-gui/grill.md`) | the `ask_user` tool; the four-questions-per-call rule stays |
| `Agent` + sub-agent type and model (`np-implement/wp.md`, `np-plan/wp.md`, steward, core *Models*) | the `task` tool, or a custom agent by name; models are the same Claude tiers picked in Copilot, so §8.4.5 holds |
| `/compact` checkpoints (§8.4.4) | `/compact` if the app has it (Phase 0); otherwise end the turn and start a new session with the printed prompt |
| `run_in_background` + `until grep` wait (CLAUDE.md *Commands*) | `setsid nohup bash -c '.claude/hooks/gate.sh run > LOG 2>&1; echo "exit $?" >> LOG' &`, then the same `until grep` loop in the foreground |
| `Skill(code-review xhigh --fix …)` (`np-ship/wp.md` §4) | on Copilot: the app's built-in code-review agent (Phase 0) on `origin/main...HEAD` at its most thorough setting, writing `docs/code_reviews/CODE_REVIEW_NNN.md` with the same evidence (reviewed SHA, completed status, findings, not-assessed). Fixes are applied in the session as today |
| `subscribe_pr_activity`, fallback check-ins (`np-ship/wp.md` §4–6, steward *Bounded wakes*) | none. Push, record the checkpoint in the PR's Verification, report "automation limit: re-run `/np-ship wp <n>` when CI ends", and stop. §0 step 3 already resumes |
| `mcp__github__*` | the app's built-in GitHub MCP, or `gh` in WSL |
| Artifact tools (`np-gui publish`, `collect`) | none. Those two levels stay on Claude Code. `render` and `review` work on Copilot (Playwright and Chromium in WSL) |
| Scratchpad `<s>` (`np-gui`) | `${TMPDIR:-/tmp}/nanopnp-scratch/<branch>/` |
| Context7 MCP | add it in the app under Customize → MCP |
| `permissions.allow` (`.claude/settings.json`) | the app's tool-approval settings (manual, per machine) |

## Phase 0: machine setup and discovery (manual, in the Copilot app; about 1 h)

1. Update the app to version 1.1.14 or later, and turn on **Settings → WSL hosts (Preview)**. Open the WSL checkout
   (`~/nanopnp`) as a WSL host. Fallback A: run the Linux AppImage inside WSLg (gist by xing5). Fallback B, a last
   resort: the native Windows app with `wsl.exe` wrappers. That needs `powershell` hook entries and unwrapping of
   `bash -lc '…'` before the gate, because `gate.sh`'s `commit_re` does not match a `git` that follows a quote,
   so a wrapped commit would go ungated.
2. In WSL, check `uv`, `jq`, `git`, `gh auth status`, and `node` with Playwright and Chromium for `np-gui render`.
   Then run `uv sync --all-extras` and `.claude/hooks/gate.sh run` by hand once.
3. Use a **separate worktree or clone** from any local Claude Code checkout: `git worktree add ../nanopnp-copilot`.
   `gate.sh` gates the payload's `cwd`, so worktrees are safe.
4. Discovery. Record each answer in `.claude/workflow/hosts.md` (Phase 3):
   - Check whether the session sees `CLAUDE.md` and `AGENTS.md`, and whether it duplicates them. Ask the agent which
     instruction files it loaded. If they are doubled, disable `AGENTS.md` for Copilot only.
   - Check whether the five skills are listed under Customize → Skills.
   - **Check whether `.claude/settings.json` hooks fire in the app.** Add a throwaway `.github/hooks/probe.json` with
     `sessionStart`, `preToolUse` and `postToolUse` entries that run `cat >> /tmp/copilot-hook-<event>.json`. Run a
     shell command, an edit and a file create, then save the payloads as fixtures and delete the probe. If the
     Claude hooks also fire, the gate runs twice. That is harmless, because the stamp makes the second run a no-op,
     but note it.
   - The tool names (`bash`, `edit`, `create`) and whether `toolArgs` is a JSON string or an object.
   - The model ids the picker shows for Claude Haiku, Sonnet and Opus.
   - Whether the `task` tool accepts a model, whether `/compact` exists, and which built-in review agent or
     `/review` command exists.
   - Whether a `setsid nohup … &` process survives the end of the tool call.
   - Whether the app's own Commit and Push buttons run hooks. Assume they do not.

## Phase 1: instructions and rules (Copilot task, Sonnet)

- Write `.claude/scripts/copilot_sync.py`. It generates, and with `--check` verifies:
  - `.github/instructions/<rule>.instructions.md` for each `.claude/rules/*.md`. Frontmatter
    `applyTo: "<paths joined by commas>"`; the body is one line: "Read and follow `.claude/rules/<rule>.md` in full
    before editing a file it covers."
  - `.github/agents/<name>.agent.md` for each `.claude/agents/*.md` (Phase 2).
  Follow the style of `.claude/scripts/clause.py` and `duplicates.py`, which are run with `uv run`. Use PyYAML for
  frontmatter if it is already in the lock. Don't add a dependency.
- `.github/copilot-instructions.md`: one line pointing to `CLAUDE.md` (and `.claude/workflow/hosts.md` on this
  host), so cloud-agent sessions that skip `CLAUDE.md` still find it.
- Personal app instructions (Settings → Sessions → App instructions; machine-specific, not committed): "Run every
  command in WSL bash; never use the app's Commit or Push buttons; commit and push through the shell so the gate
  runs."

## Phase 2: sub-agents (same task)

- `copilot_sync.py` maps each `.claude/agents/*.md` as follows:
  - `name`, `description` and the body are copied verbatim.
  - `tools` is kept (`Read, Grep, Glob` maps to `read`/`search`).
  - `model` goes through a table (`haiku`, `sonnet`, `opus` → the Copilot ids from Phase 0), held in the script.
  - `include-custom-instructions: true`, or `false` where `omitClaudeMd: true` (`ci-log-classifier`).
  - `effort` is dropped.
- The output is `physics-reviewer`, `gui-reviewer` and `ci-log-classifier` as `.agent.md` files. The header comment
  in each says "generated by `.claude/scripts/copilot_sync.py`; edit `.claude/agents/`".
- `.claude/hooks/session-start.sh` runs `uv run .claude/scripts/copilot_sync.py --check`. A drift is a printed
  warning, never a failure, matching its existing warn-only rule (§8.4.2).

## Phase 3: hooks (Copilot task, Sonnet; physics-free but gate-critical)

- Extend `.agents/hooks/adapter.sh` with a dialect argument instead of a new adapter:
  `adapter.sh <event> [--dialect antigravity|copilot]`. The default stays `antigravity`.
  - **pre-tool / copilot:**
    - Read `.toolArgs`, decoding it with `fromjson` when it is a string, then take `.command`.
    - Normalise the payload `cwd` with the same WSL/drive jq expression already used for file paths. Factor that
      expression into a shell function shared by both.
    - Call `gate.sh` exactly as today.
    - Translate gate.sh's `hookSpecificOutput.permissionDecision{,Reason}` into top-level
      `{"permissionDecision":"deny","permissionDecisionReason":…}`; emit `{"permissionDecision":"allow"}`
      otherwise. An unparseable payload keeps the existing **deny** rule.
  - **post-tool / copilot:** take `.toolArgs.path // .toolArgs.file_path` (from Phase 0 fixtures), then call
    `format.sh` as today.
  - **session-start / copilot:** capture `session-start.sh` stdout and emit `{"additionalContext": <text>}`.
- Add `.github/hooks/nanopnp.json`:

  ```json
  {"version": 1, "hooks": {
    "sessionStart": [{"type": "command", "bash": "bash \"$(git rev-parse --show-toplevel)/.agents/hooks/adapter.sh\" session-start --dialect copilot", "timeoutSec": 600}],
    "preToolUse":  [{"type": "command", "matcher": "bash", "bash": "… pre-tool --dialect copilot", "timeoutSec": 1800}],
    "postToolUse": [{"type": "command", "matcher": "edit|create", "bash": "… post-tool --dialect copilot", "timeoutSec": 60}]}}
  ```

  `timeoutSec: 1800` matters. A timeout is **fail-open** in Copilot, and `gate.sh`'s budget is 1500 s.
- If Phase 0 shows that `.claude/settings.json` hooks also fire in the app, leave both. The stamp de-duplicates.
  If they fire **and fail** (for example because `CLAUDE_PROJECT_DIR` is unset), note it in `hosts.md`. The
  existing `$(git rev-parse --show-toplevel)` fallback should cover it.
- Optional, recommended because app buttons bypass agent hooks: add a git-native `pre-push` in `.githooks/pre-push`
  that refuses a push whose tree lacks the `push` stamp. It reuses `gate.sh`'s stamp reader through a new
  `gate.sh check-push` mode. The Copilot worktree opts in with `git config core.hooksPath .githooks`; nothing
  changes for other checkouts.

## Phase 4: workflow portability (Copilot task, Sonnet; prose only)

- **New `.claude/workflow/hosts.md`** holds the gap table above as the normative mapping, the Phase 0 findings, the
  model-id table, and the CI rule: "on a host without PR subscriptions: push, checkpoint, report the automation
  limit, stop".
- `.claude/workflow/core.md`, *Reading order*, gets one sentence: "On a host other than Claude Code, read
  `hosts.md` beside this file and use its substitutes."
- Each of the five `SKILL.md` files gets one line under the heading: "If `$ARGUMENTS` or `${CLAUDE_SKILL_DIR}`
  appears literally, the arguments are the text after the command, and the directory is
  `.claude/skills/<name>/`."
- `np-ship/wp.md` §4 gets one paragraph: the code-review substitute per `hosts.md`, with the same evidence rule.
  §5 points to `hosts.md` for the CI rule.
- `steward/SKILL.md`, *Bounded wakes*, gets one line pointing to `hosts.md`. The no-sleep rule is unchanged.
- `np-gui/SKILL.md` states that `publish` and `collect` need Claude Code's artifact tools; on another host, stop and
  say so.

## Phase 5: running both hosts concurrently (interchangeable)

These rules go into `hosts.md` and get one bullet in §8.4.4:

- **One host per branch at a time.**
  - The lane line in `docs/plans/current.md` and the PR's Verification checkpoint name the host driving it:
    `host: claude-code | copilot`.
  - A host that finds the other named and the branch moved within the hour asks before writing.
- **Never share a working tree.** Use separate worktrees or clones. Claude Code cloud sessions already have their
  own clone.
- **The fresh-session rule (§8.4.4) is per session, not per host.** Shipping on the other host is encouraged
  because it gives an independent review, but it is not required.
- The two-lane cap, the renumbering after a second-lane merge and `duplicates.py` are unchanged; they already cover
  concurrency.
- **Commit trailers:** Copilot commits carry `Co-Authored-By: GitHub Copilot <…>` instead of the Claude trailer.
- Before each push, rebase onto or merge `origin/<head>`. Never force-push a branch the other host may hold.

## Phase 6: specification and docs (same PR as Phases 1–5)

- §8.4.4 (`specification/08-implementation-plan/04-development-process.md`) gets a bullet saying that the workflow
  runs on Claude Code and on the GitHub Copilot app. `.claude/` is the single source. Copilot reads it through
  `.github/{instructions,agents,hooks}` (generated or pointers), and `.claude/workflow/hosts.md` maps the
  substitutes. One host drives a branch at a time.
- §8.4.5 gets a bullet: the model tiers are the same Claude models on either host.
- `specification/history/` gets the ruling record, with its line in `history/index.md`. Follow
  `np-plan/rulings.md`, whose rule is that every ruling lands in a clause.
- `CLAUDE.md` gets a 3-line *Other hosts* note pointing to `hosts.md`, and its *Commands* table gets
  `uv run .claude/scripts/copilot_sync.py [--check]`.
- `CHANGELOG.md` gets an `## [Unreleased]` line.

Ship it all as **one PR**, `chore: run the workflow on the GitHub Copilot app too`. It is outside the WP sequence
(no `src/` or `tests/` change). Branch from `main`.

## Executing this plan in Copilot

1. Do Phase 0 by hand.
2. Give the Copilot agent (Claude Sonnet) this file and the prompt: "Implement Phases 1–6 of
   `docs/plans/copilot-host.md`, one commit per phase. Run the gate as `CLAUDE.md` *Commands* say, before
   committing and pushing."
3. Ship it from **Claude Code** with `/np-ship`. That gives the cross-host review, and Claude can drive CI to green.


## Verification

- **Hook replay, offline in WSL.** Pipe each Phase 0 fixture into
  `adapter.sh pre-tool --dialect copilot` with these commands:
  - `git commit -m x` on a dirty tree that fails ruff gives `deny` with the reason.
  - The same command on a clean, passing tree gives `allow`.
  - `git -C . commit` is gated.
  - `git push` without a stamp gives `deny`.
  - `ls` gives `allow`.
  - A malformed payload gives `deny`.
  - The Antigravity fixtures still give the old `{"decision":…}` shape, which shows no regression.
- **Live, in the Copilot app:**
  - Ask the agent to commit a deliberate ruff violation. It must be refused.
  - Fix the violation and commit. The commit must pass.
  - Push before `gate.sh run`. The push must be refused.
  - Run `gate.sh run` in the background and wait, then push. The push must go through.
  - Edit a `.py` file and check that `format.sh` ran.
  - Open a new session and check that the session-start text appears.
- **Sub-agents:** `/agent physics-reviewer` on a small diff returns findings and edits nothing. `ci-log-classifier`
  sees no `CLAUDE.md`.
- **Workflow dry run:** `/np-plan wp <next>` in Copilot up to the `ask_user` questions, then cancel.
  `/np-implement` on a trivial docs-only test branch should gate, push, open the PR and report the automation limit.
- **Drift check:** edit a `paths:` glob in `.claude/rules/python.md`. The next session start warns until
  `copilot_sync.py` is rerun.
- The repo gate passes: `.claude/hooks/gate.sh run`, then
  `uv sync --all-extras --group docs && uv run docs/scripts/generate.py && uv run mkdocs build --strict`, because
  `SPECIFICATION.md` changes.

Sources: [Customize the Copilot app](https://docs.github.com/en/copilot/how-tos/github-copilot-app/customize-github-copilot-app),
[CLI hooks reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-hooks-reference),
[Customization cheat sheet](https://docs.github.com/enterprise-cloud@latest/copilot/reference/customization-cheat-sheet),
[Custom instructions (CLI)](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions),
[Custom agents configuration](https://docs.github.com/en/copilot/reference/custom-agents-configuration),
[Agent skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills),
[WSL support issue (github/app#136)](https://github.com/github/app/issues/136).
