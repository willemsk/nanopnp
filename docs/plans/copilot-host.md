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
changes; the three hook scripts change a little.

**What could go wrong.** Copilot could let a commit past the safety check without anyone noticing. It already
runs Claude Code's hook settings, but the check refuses in a format Copilot does not document, a hook that runs
out of time lets the command through, and Copilot has ways to commit that no hook watches: typing into a
running shell, GitHub's file tools, and the app's own Commit and Push buttons. The setup makes the check refuse
in a form both assistants obey, runs it once rather than twice, blocks the unwatched paths, and adds a check
git itself runs before a push. Phase 0 proves each of these before anything is built, and stops the plan if
one fails. The two assistants could also trip over each other on one branch; one assistant drives a branch at
a time, and the branch says which.

**Your call.** Nothing waits on you; the three choices (Windows with the project in WSL, either assistant
for any step, Copilot stops and reports rather than waiting for the automated checks) are made. The review of
this plan keeps them and records the app features they pass over (see Gaps).

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
CLI's customisation model (verified against GitHub Docs, Oct 2026, and in app 1.1.34 on Windows with a WSL host,
2026-10-31):

| Copilot reads natively | So |
|---|---|
| `CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md` (`@path` imports expanded in all three) | instructions load as-is. `AGENTS.md` imports `CLAUDE.md`, and only identical files are de-duplicated, so expect `CLAUDE.md` twice (Phase 0) |
| `.claude/skills/*/SKILL.md` (also `.github/skills`, `.agents/skills`) | `/np-plan`, `/np-implement`, `/np-ship`, `/np-gui`, `steward` appear as skills |
| `.claude/settings.json` hooks ("Cross-tool `.claude/settings.json` and `.claude/settings.local.json` files in the repository are also read") | **all three fire**, beside any `.github/hooks` file; every source's hooks for an event run, in order. Not "nothing to do": see the next table |

What the Claude hooks do on Copilot today (from the hooks reference; Phase 0 confirms):

| Hook in `.claude/settings.json` | On Copilot |
|---|---|
| `PreToolUse` `Bash` → `gate.sh` | Fires. A PascalCase event gets the VS Code payload (`hook_event_name`, `session_id`, `cwd`, `tool_name`, `tool_input` parsed), which `gate.sh` reads as it is. Claude matcher semantics map `Bash` to Copilot's `bash` and `powershell`, but not `write_bash`. **The refusal does not land.** `gate.sh` refuses with `hookSpecificOutput.permissionDecision` and exit 0. Copilot documents only a top-level `permissionDecision`, and output without one "uses default behavior". So the gate can run, fail, and still let the commit through |
| `PostToolUse` `Edit\|Write\|MultiEdit` → `format.sh` | A silent no-op. Copilot's `edit` and `create` tools name the file `path`, and `format.sh` reads only `.tool_input.file_path`. Whether Claude matcher semantics apply to `PostToolUse` is undocumented; the reference states them for `PreToolUse` |
| `SessionStart` → `session-start.sh` | Runs, with its side effects (fetch, fast-forward of `main`), but the summary is dropped: Copilot consumes only a JSON `{"additionalContext": …}` |
| `timeout: 1800` | Read as an alias of `timeoutSec`. A timed-out command hook is **fail-open** on Copilot (and on Claude Code), so this must hold (Phase 0) |

| Copilot needs its own file | Claude source |
|---|---|
| `.github/instructions/*.instructions.md` (`applyTo:` comma-separated globs; **no** `@` import expansion) | `.claude/rules/*.md` (`paths:`); Copilot does not read `.claude/rules/` |
| `.github/agents/<name>.agent.md` (frontmatter `name`, `description` required; `tools`, `model`, `include-custom-instructions`). Claude's `Read, Grep, Glob` are accepted tool aliases, so no mapping | `.claude/agents/*.md` (`model: haiku/sonnet/opus`, `effort`, `omitClaudeMd` not understood); Copilot is not documented to read `.claude/agents/` |
| `.github/hooks/*.json` (`version: 1`; camelCase events; stdin `{sessionId, timestamp, cwd, toolName, toolArgs}`; `matcher` is a regex anchored `^(?:…)$`; deny = one stdout object `{"permissionDecision":"deny","permissionDecisionReason":…}`, or exit 2; any non-timeout failure **denies**; a timeout **allows**, default 30 s). Needed only for tools Claude Code does not have | none |

**Design rule:** `.claude/` stays the single source of truth. Everything Copilot-specific is either a thin pointer
or a generated file under `.github/`, plus one mapping document, `.claude/workflow/hosts.md`. The weak forms are
not the only thing kept from being written twice: the workflow is not duplicated either. The hooks follow the same
rule more strictly: Copilot already runs `.claude/settings.json`, so its three scripts are made host-neutral rather
than wrapped a second time.

## Gaps the plan closes (Claude-only constructs used by the workflow)

| Construct (where) | Copilot substitute |
|---|---|
| `$ARGUMENTS`, `${CLAUDE_SKILL_DIR}` (every `SKILL.md`) | Not documented for Copilot (Phase 0). Add one line per SKILL.md: arguments are the text after `/np-x`; the dir is `.claude/skills/np-x/` |
| `AskUserQuestion` (`np-plan/rulings.md:55-58`, `np-gui/grill.md:21`) | the `ask_user` tool, which takes **one question per call** (optional choices; a free-text answer is always offered). The runtime forbids asking in plain text. "Up to four per call" becomes "up to four calls in a row"; the numbered-message fallback is not used on Copilot |
| `Agent` + sub-agent type and model (`np-implement/wp.md`, `np-plan/wp.md`, steward, core *Models*) | the `task` tool, with `agent_type` (a built-in or a custom agent's name), `model` and `reasoning_effort`. The runtime passes a model or effort only when instructions require one explicitly, so core *Models* and `hosts.md` name them. Claude's `effort` becomes `reasoning_effort` at the call, because `.agent.md` has no effort field. §8.4.5 holds for the tier; the version can differ by host (record both in `hosts.md`) |
| `/compact` checkpoints (§8.4.4) | the app compacts long conversations by itself; whether `/compact` can be called by hand is a Phase 0 check. Otherwise end the turn and start a new session with the printed prompt |
| `run_in_background` + `until grep` wait (CLAUDE.md *Commands*) | the shell tool's own async mode: start `.claude/hooks/gate.sh run > LOG 2>&1; echo "exit $?" >> LOG` with `mode: "async"`, then wait for its completion notice, or run the same `until grep` loop as a sync call (`initial_wait` up to 600 s, re-issued). **Not** `setsid nohup … &`: the runtime forbids detaching by hand, and a detached process needs approval outside the sandbox |
| `Skill(code-review xhigh --fix …)` (`np-ship/wp.md` §4) | `code-review` is not a repo skill. On Claude Code it comes from the environment; on Copilot the name resolves to whatever skill the machine has installed (on the author's machine, an unrelated plugin), so never call it by name there. Substitute: the built-in `code-review` agent through `task`, with `reasoning_effort: "xhigh"` and the §4 brief and `origin/main...HEAD` in the prompt. It is read-only and reports only high-confidence bugs and logic errors. So the main session writes `docs/code_reviews/CODE_REVIEW_NNN.md` with the same evidence (reviewed SHA, completed status, findings, and a not-assessed line naming standards, spec conformance and anything below high confidence) and applies the fixes. The narrower scope is one more reason to ship from the other host |
| `subscribe_pr_activity`, fallback check-ins (`np-ship/wp.md` §4–6, steward *Bounded wakes*) | Copilot does have the means: session automations wake the same session on a schedule, and "agent merge" drives a pull request through CI failures and review comments by itself. The decision stands: push, record the checkpoint in the PR's Verification, report "automation limit: re-run `/np-ship wp <n>` when CI ends", and stop. §0 step 3 already resumes. A scheduled wake inside the steward's bounded wakes is the later upgrade. **Agent merge stays off** on nanopnp pull requests: it would fix CI outside the steward's failure-class rules |
| `mcp__github__*` | the app's built-in GitHub MCP for reads, or `gh` in WSL. Its write tools (`github-push_files`, `github-create_or_update_file`, `github-delete_file`) make commits on GitHub that no gate sees; Phase 3 denies them |
| Artifact tools (`np-gui publish`, `collect`) | no drop-in. The app has canvas extensions (side-panel views with actions) and chat attachments, but nothing like the artifact `db` collections those two levels use (`verdicts`, `ArtifactData`). They stay on Claude Code; a canvas port is separate work. `render` and `review` work on Copilot (Playwright and Chromium in WSL) |
| Scratchpad `<s>` (`np-gui`) | the session folder's `files/` directory, which the app names in each session's context; `${TMPDIR:-/tmp}/nanopnp-scratch/<branch>/` if there is none |
| Context7 MCP | add it in the app under Customize → MCP |
| `permissions.allow` (`.claude/settings.json`) | the app's tool-approval settings (manual, per machine). Copilot is not documented to read `permissions` from `.claude/settings.json` |
| The Claude web environment's stop hook for an unpushed commit (CLAUDE.md) | none needed; an `agentStop` hook could copy it later |

## Phase 0: machine setup and discovery (manual, in the Copilot app; about 1 h)

1. Update the app to version 1.1.14 or later, and turn on **Settings → WSL hosts (Preview)**. Open the WSL checkout
   (`~/nanopnp`) as a WSL host. This works in app 1.1.34 with an Arch distribution (2026-10-31). On a WSL host the
   agent's shell and every command hook run in Linux. The two fallbacks are **not supported for gated work**:
   - A, the Linux AppImage inside WSLg, is a community gist, not a GitHub build.
   - B, the native Windows app on the `\\wsl.localhost\` path, fails three ways. Windows git refuses the share as
     "dubious ownership" (seen in the app's own log for another WSL repo). Every `command` hook, Claude's included,
     would run in PowerShell and fail, and a failing `preToolUse` hook denies, so every shell call is refused. And
     `gate.sh`'s `commit_re` does not match a `git` that follows a quote, so `bash -lc '…'` wrappers go ungated.
2. In WSL, check `uv`, `jq`, `git`, `gh auth status`, and `node` with Playwright and Chromium for `np-gui render`.
   Then run `uv sync --all-extras` and `.claude/hooks/gate.sh run` by hand once.
3. Let the app create a worktree for each session, its default. Don't use its "branch" workspace type on a checkout
   that Claude Code also uses. No manual `git worktree add` is needed. `gate.sh` gates the payload's `cwd`, which is
   the session's worktree.
4. Discovery. Record each answer in `.claude/workflow/hosts.md` (Phase 4).

   **Already known** (app 1.1.34, 2026-10-31; re-check on the day):
   - Hook sources, payloads and matchers as in Context. Hooks for one event run in order, and any deny blocks.
   - `ask_user` takes one question per call. `task` takes `agent_type`, `model` and `reasoning_effort`; the built-in
     agents include `explore`, `task`, `general-purpose`, `code-review`, `rubber-duck`, `research` and
     `security-review`.
   - The Claude model ids offered: `claude-haiku-4.5`, `claude-haiku-5.5`, `claude-sonnet-5`, `claude-sonnet-5.5`,
     `claude-opus-4.8`, `claude-opus-5`, `claude-opus-5.5`. The table: `haiku` → `claude-haiku-5.5`, `sonnet` →
     `claude-sonnet-5.5`, `opus` → `claude-opus-5.5`. What is offered depends on the Copilot plan and org policy.
   - Background runs use the shell tool's async mode (Gaps).
   - The GitHub MCP tools as the app names them: `github-push_files`, `github-create_or_update_file`,
     `github-delete_file`, `github-merge_pull_request`, `github-update_pull_request_branch`.
   - The commit trailer the app asks for: `Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>`.
   - The app's git actions shell out to the git CLI (app log), so git's own hooks run for its Commit and Push
     buttons. Agent hooks do not, because a button is not a tool call.

   **To check:**
   - **Probe the hooks.** Add throwaway entries for every event, in `.github/hooks/probe.json` and in an untracked
     `.claude/settings.local.json`, that run `{ env; cat; } >> /tmp/copilot-hook-<source>-<event>.log`. Run a shell
     command, an edit, a file create, a `write_bash` into an async shell and a GitHub MCP read. Save the payloads as
     fixtures, then delete the probes. Record:
     - which sources fire and in which order, and whether Claude's `PostToolUse` matcher catches `edit` and `create`;
     - the argument names: `bash` `.command`, `edit` and `create` `.path`, `write_bash` (likely `.input`), and whether
       camelCase `toolArgs` arrives as a string or an object;
     - whether `CLAUDE_PROJECT_DIR` is set, and which variable tells Copilot from Claude Code;
     - the names the MCP tools carry in a hook payload.
   - **Probe the refusal.** A `PreToolUse` probe that prints `gate.sh`'s current `hookSpecificOutput` deny and exits
     0: is the command refused? Then one that prints the reason on stderr and a top-level deny on stdout and exits 2
     (Phase 3's form): is it refused, and does the agent see the reason?
   - **Probe the time limit.** A `PreToolUse` probe with `timeout: 60` that sleeps 40 s and then denies. Refused means
     `timeout` is honoured. Let through means the default 30 s applies, and the gate would fail open after 30 s.
   - Whether the session sees `CLAUDE.md` twice, and where the app lets one instruction file be turned off for
     Copilot only (the CLI has `/instructions`).
   - Whether the five skills are listed under Customize → Skills, and whether `$ARGUMENTS` is substituted.
   - Whether `/compact` can be called by hand.
   - Whether a coding session has the session-automation tool (for the later CI upgrade).
   - Whether the app's Commit and Push buttons pass `--no-verify`.

   **Stop rule.** If no refusal form is obeyed, or `timeout` is not honoured, stop: Copilot does not commit on
   this project until it is fixed.

## Phase 1: instructions and rules (Copilot task, Sonnet)

- Write `.claude/scripts/copilot_sync.py`. It generates, and with `--check` verifies:
  - `.github/instructions/<rule>.instructions.md` for each `.claude/rules/*.md`. Frontmatter
    `applyTo: "<paths joined by commas>"`; the body is one line: "Read and follow `.claude/rules/<rule>.md` in full
    before editing a file it covers."
  - `.github/agents/<name>.agent.md` for each `.claude/agents/*.md` (Phase 2).
  Follow the style of `.claude/scripts/clause.py` and `duplicates.py`, which are run with `uv run`. Use PyYAML for
  frontmatter if it is already in the lock. Don't add a dependency.
- `.github/copilot-instructions.md`: Copilot loads it beside `CLAUDE.md` and `AGENTS.md`, and Claude Code does not,
  so it is the place for the Copilot-only pointer: "You are not Claude Code: follow `CLAUDE.md`, and read
  `.claude/workflow/hosts.md` for the substitutes." Name `CLAUDE.md` in plain text; an `@CLAUDE.md` import would
  load it a third time.
- Personal app instructions (Settings → Sessions → App instructions; machine-specific, not committed): "Run every
  command in WSL bash; never use the app's Commit or Push buttons; commit and push through the shell so the gate
  runs; never commit by typing into a running shell; leave agent merge off."

## Phase 2: sub-agents (same task)

- `copilot_sync.py` maps each `.claude/agents/*.md` as follows:
  - `name`, `description`, `tools` and the body are copied verbatim. Copilot accepts `Read, Grep, Glob` as aliases.
  - `model` goes through a table (`haiku`, `sonnet`, `opus` → the Copilot ids from Phase 0), held in the script.
  - `include-custom-instructions: true`, or `false` where `omitClaudeMd: true` (`ci-log-classifier`).
  - `effort` has no `.agent.md` field. It goes into `hosts.md`'s model table and is passed as `reasoning_effort`
    when the agent is called through `task`.
- The output is `physics-reviewer`, `gui-reviewer` and `ci-log-classifier` as `.agent.md` files. The header comment
  in each says "generated by `.claude/scripts/copilot_sync.py`; edit `.claude/agents/`".
- `.claude/hooks/session-start.sh` runs `uv run .claude/scripts/copilot_sync.py --check`. A drift is a printed
  warning, never a failure, matching its existing warn-only rule (§8.4.2).

## Phase 3: hooks (Copilot task, Sonnet; physics-free but gate-critical)

One hook path, not two. Copilot already runs the three hooks in `.claude/settings.json`, so those scripts become
host-neutral, and `.github/hooks` holds only what Claude Code has no equivalent of. A second `bash` gate in
`.github/hooks` would run the whole gate twice on every failing commit: hooks for one event run in order, hook mode
takes no lock, and the stamp spares the second run only after a pass. And the Claude path would still fail open on
its own whenever the second file was not loaded.

- **`gate.sh` refuses in a form both hosts document.** `deny()` writes the reason to stderr, prints one JSON object
  carrying both `hookSpecificOutput` (as today) and a top-level `permissionDecision`/`permissionDecisionReason`, and
  exits 2. Claude Code blocks on exit 2 whatever the JSON says, and uses the decision's reason or stderr. Copilot
  denies on exit 2 and merges the stdout JSON. If Phase 0 shows Copilot already obeys today's shape, leave
  `gate.sh` alone. The `jq … || exit 0` lines still let an unparseable payload through; Copilot passes `tool_input`
  as a string when the arguments are not JSON. That is unchanged for Claude Code; note it in `hosts.md`.
- **`.agents/hooks/adapter.sh` keeps working.** It already treats any non-zero exit as a refusal. Have it read the
  reason from stdout alone, as `.permissionDecisionReason // .hookSpecificOutput.permissionDecisionReason`, because
  stderr now carries the reason too and the merged `2>&1` output no longer parses.
- **`format.sh`** reads `.tool_input.file_path // .tool_input.path`. If Phase 0 shows Claude's `PostToolUse` matcher
  does not catch `edit` and `create`, add a Copilot `postToolUse` entry for `edit|create` (below). Claude Code
  never reads it, so nothing runs twice.
- **`session-start.sh`**, when not under Claude Code (the variable from Phase 0), prints its summary as one
  `{"additionalContext": …}` object. Its side effects are unchanged and still run once per session.
- **`.github/hooks/nanopnp.json`**, Copilot-only tools:

  ```json
  {"version": 1, "hooks": {
    "preToolUse": [
      {"type": "command", "matcher": "write_bash",
       "bash": "bash \"$(git rev-parse --show-toplevel)/.agents/hooks/adapter.sh\" pre-tool --dialect copilot",
       "timeoutSec": 1800},
      {"type": "command", "matcher": "github-(push_files|create_or_update_file|delete_file)",
       "bash": "echo '{\"permissionDecision\":\"deny\",\"permissionDecisionReason\":\"nanopnp: commit and push through the shell, so the gate runs (.claude/workflow/hosts.md).\"}'",
       "timeoutSec": 10}]}}
  ```

  The MCP names follow Phase 0. `adapter.sh pre-tool --dialect copilot` reads `.toolArgs`, decoding it with
  `fromjson` when it is a string, takes `.command // .input`, normalises `cwd` with the WSL/drive jq expression
  already used for file paths (factor it into one shell function), calls `gate.sh`, and passes a refusal through.
  An unparseable payload keeps the existing **deny** rule. `gate.sh` cannot see a `cd` typed earlier into the same
  shell, which is why the personal instructions also forbid committing that way. If Phase 0 asks for it, a
  `postToolUse` entry for `edit|create` calls `adapter.sh post-tool --dialect copilot`, which takes
  `.toolArgs.path // .toolArgs.file_path` and calls `format.sh`.
- **Required, not optional: a git-native `pre-push`** in `.githooks/pre-push`. The app's buttons run git's hooks but
  no agent hook. It refuses a push whose tree lacks the `push` stamp, through a new `gate.sh check-push` mode that
  reuses the stamp reader and the hook's exemptions (tags, deletions). Run `git config core.hooksPath .githooks` in
  the WSL clone. That writes the clone's shared config, so it covers every worktree of the clone: the app's
  per-session worktrees (needed) and any Claude Code checkout of the same clone (harmless, because a Claude push
  already needs the stamp). Other clones, including Claude Code cloud sessions, are untouched. Phase 0 checks that
  the buttons don't pass `--no-verify`.
- Optional, same PR: Claude Code has the same MCP hole (`mcp__github__push_files`, `create_or_update_file`,
  `delete_file`). The workflow uses none of them, so a `permissions.deny` for the three in `.claude/settings.json`
  closes it.

## Phase 4: workflow portability (Copilot task, Sonnet; prose only)

- **New `.claude/workflow/hosts.md`** holds the gap table above as the normative mapping, the Phase 0 findings, the
  model-id table (tier, id per host, effort), and the CI rule: "on a host without PR subscriptions: push,
  checkpoint, report the automation limit, stop".
- `.claude/workflow/core.md`, *Reading order*, gets one sentence: "On a host other than Claude Code, read
  `hosts.md` beside this file and use its substitutes."
- Each of the five `SKILL.md` files gets one line under the heading: "If `$ARGUMENTS` or `${CLAUDE_SKILL_DIR}`
  appears literally, the arguments are the text after the command, and the directory is
  `.claude/skills/<name>/`."
- `np-ship/wp.md` §4 gets one paragraph: the code-review substitute per `hosts.md`, with the same evidence rule and
  the not-assessed line. §5 points to `hosts.md` for the CI rule.
- `np-plan/rulings.md` and `np-gui/grill.md` each get one line: on Copilot, `ask_user` takes one question per call,
  per `hosts.md`.
- CLAUDE.md *Commands* gets one line pointing to `hosts.md` for the background run on Copilot.
- `steward/SKILL.md`, *Bounded wakes*, gets one line pointing to `hosts.md`. The no-sleep rule is unchanged.
- `np-gui/SKILL.md` states that `publish` and `collect` need Claude Code's artifact tools; on another host, stop and
  say so.

## Phase 5: running both hosts concurrently (interchangeable)

These rules go into `hosts.md` and get one bullet in §8.4.4:

- **One host per branch at a time.**
  - The lane line in `docs/plans/current.md` and the PR's Verification checkpoint name the host driving it:
    `host: claude-code | copilot`.
  - A host that finds the other named and the branch moved within the hour asks before writing.
- **Never share a working tree.** The app gives each session its own worktree; Claude Code cloud sessions already
  have their own clone.
- **The fresh-session rule (§8.4.4) is per session, not per host.** Shipping on the other host is encouraged
  because it gives an independent review, but it is not required.
- The two-lane cap, the renumbering after a second-lane merge and `duplicates.py` are unchanged; they already cover
  concurrency.
- **Commit trailers:** Copilot commits carry the trailer the app asks for,
  `Co-authored-by: Copilot App <223556219+Copilot@users.noreply.github.com>`, instead of the Claude trailer.
- **Agent merge stays off** on nanopnp pull requests (Gaps).
- Before each push, rebase onto or merge `origin/<head>`. Never force-push a branch the other host may hold.

## Phase 6: specification and docs (same PR as Phases 1–5)

- §8.4.4 (`specification/08-implementation-plan/04-development-process.md`) gets a bullet saying that the workflow
  runs on Claude Code and on the GitHub Copilot app. `.claude/` is the single source. Both hosts run the hooks in
  `.claude/settings.json`; Copilot reads the rest through `.github/{instructions,agents,hooks}` (generated or
  pointers), and `.claude/workflow/hosts.md` maps the substitutes. One host drives a branch at a time.
- If §8.4.2 describes how the gate refuses, it gets the exit-2 form and the `pre-push` check.
- §8.4.5 gets a bullet: the model tiers are the same Claude models on either host.
- `specification/history/` gets the ruling record, with its line in `history/index.md`. Follow
  `np-plan/rulings.md`, whose rule is that every ruling lands in a clause.
- `CLAUDE.md` gets a 3-line *Other hosts* note pointing to `hosts.md`, and its *Commands* table gets
  `uv run .claude/scripts/copilot_sync.py [--check]`.
- `CHANGELOG.md` gets an `## [Unreleased]` line.

Ship it all as **one PR**, `chore: run the workflow on the GitHub Copilot app too`. It is outside the WP sequence
(no `src/` or `tests/` change). Branch from `main`.

## Executing this plan in Copilot

1. Do Phase 0 by hand. Stop if its stop rule fires.
2. Give the Copilot agent (Claude Sonnet) this file and the prompt: "Implement Phases 1–6 of
   `docs/plans/copilot-host.md`, one commit per phase, Phase 3 first. Until Phase 3 is committed, run
   `.claude/hooks/gate.sh run` yourself before every commit and push, as `CLAUDE.md` *Commands* say." Until then,
   Copilot's own refusals may not land (Context), so the gate is run by hand.
3. Ship it from **Claude Code** with `/np-ship`. That gives the cross-host review, proves the changed `gate.sh`
   still refuses on Claude Code, and lets Claude drive CI to green.

## Verification

- **Hook replay, offline in WSL.** Pipe each Phase 0 fixture into the hook Copilot runs for it: the VS Code
  `PreToolUse` fixtures into `gate.sh`, and the `write_bash` fixtures into `adapter.sh pre-tool --dialect copilot`:
  - `git commit -m x` on a dirty tree that fails ruff exits 2, with the reason on stderr and a top-level deny on
    stdout.
  - The same command on a clean, passing tree prints nothing and exits 0.
  - `git -C . commit` is gated.
  - `git push` without a stamp is refused.
  - `ls` is allowed.
  - A malformed `write_bash` payload is refused.
  - `format.sh` formats a `.py` file given a `path` fixture.
  - `session-start.sh` prints one `{"additionalContext": …}` object off Claude Code, and plain text under it.
  - The Antigravity fixtures still give the old `{"decision":…}` shape, with the reason, which shows no regression.
- **Live, in the Copilot app:**
  - Ask the agent to commit a deliberate ruff violation. It must be refused, the reason must reach the agent, and
    the gate must run once (one gate log, about one gate's time).
  - Fix the violation and commit. The commit must pass.
  - Type a commit into an async shell (`write_bash`) on a failing tree. It must be refused.
  - Ask the agent to change a file with GitHub's MCP file tools. It must be refused.
  - Push before `gate.sh run`. The push must be refused.
  - Press the app's Push button on an unstamped tree. `pre-push` must refuse it.
  - Run `gate.sh run` in async mode and wait for it, then push. The push must go through.
  - Edit a `.py` file and check that `format.sh` ran.
  - Open a new session and check that the session-start text appears.
- **Live, in Claude Code (regression):** a failing commit is refused and shows the reason; a push without the stamp
  is refused; the session-start text still appears; `format.sh` still runs.
- **Sub-agents:** `physics-reviewer`, called through `task` with `reasoning_effort: "high"` on a small diff, returns
  findings and edits nothing. `ci-log-classifier` sees no `CLAUDE.md`.
- **Workflow dry run:** `/np-plan wp <next>` in Copilot up to the `ask_user` questions (one per call), then cancel.
  `/np-implement` on a trivial docs-only test branch should gate, push, open the PR and report the automation limit.
- **Drift check:** edit a `paths:` glob in `.claude/rules/python.md`. The next session start warns until
  `copilot_sync.py` is rerun.
- The repo gate passes: `.claude/hooks/gate.sh run`, then
  `uv sync --all-extras --group docs && uv run docs/scripts/generate.py && uv run mkdocs build --strict`, because
  `SPECIFICATION.md` changes.

## Review notes (Copilot app 1.1.34, 2026-10-31)

An adversarial review from inside the Copilot app changed the first draft as follows:

- **The gate could fail open.** The draft said the Claude hooks "possibly" fire, and that a second run would be
  harmless. They do fire, but their refusal shape (`hookSpecificOutput`, exit 0) is not one Copilot documents. The
  stamp does not stop a second, full run after a failing gate, because hook mode takes no lock and the stamp is
  written only on a pass. Phase 3 now keeps one hook path and refuses with exit 2, which both hosts document.
- **Unwatched commit paths** were missing: `write_bash`, and the GitHub MCP write tools. Phase 3 gates the first
  and denies the second.
- **`format.sh` is a no-op on Copilot** (`path` against `file_path`), and **the session-start text is dropped**
  (plain text against `additionalContext`).
- **`core.hooksPath` is shared by every worktree of a clone**, so "nothing changes for other checkouts" was wrong.
  It is harmless for Claude and needed for the app's per-session worktrees. The `pre-push` check is now required,
  because the app's buttons do run git's hooks.
- **Fallbacks A and B are unsupported.** The WSL host works.
- Corrected substitutes: `ask_user` takes one question per call; background runs use the shell's async mode, not
  `nohup`; the built-in code-review agent is narrower than the Claude skill, so the session writes the report; PR
  automation and artifact-like features do exist, though the decisions stand; agent merge stays off; the trailer
  is the app's own.
- Filled in from the app: model ids, `task` parameters, built-in agents, MCP tool names, and the fact that
  `.agent.md` takes Claude's tool names as they are.

Sources: [Customize the Copilot app](https://docs.github.com/en/copilot/how-tos/github-copilot-app/customize-github-copilot-app),
[CLI hooks reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-hooks-reference),
[Customization cheat sheet](https://docs.github.com/enterprise-cloud@latest/copilot/reference/customization-cheat-sheet),
[Custom instructions (CLI)](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions),
[Custom agents configuration](https://docs.github.com/en/copilot/reference/custom-agents-configuration),
[Agent skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills),
[Claude Code hooks (exit code 2)](https://code.claude.com/docs/en/hooks),
[WSL support issue (github/app#136)](https://github.com/github/app/issues/136).
