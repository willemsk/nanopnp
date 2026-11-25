---
type: Library Behaviour
title: '26. What a Claude Code helper can do (WP6.05)'
description: What a general-purpose helper that the Agent tool starts can and cannot do, which decides how /np-carry splits a package between its main session and its helpers.
tags:
- software
- library-behaviour
- workflow
sources:
- id: wp6.05-plan
  resource: docs/plans/phase-6/wp6.05-the-orchestrator.md
  title: WP6.05 plan, D1, D2 and D6
generated:
  by: claude-code/0.7.0-alpha.4
  at: '2026-11-24T00:00:00Z'
tested_with:
  claude-code: 2.1.331
---

## 26. What a Claude Code helper can do (WP6.05)

A *helper* is a `general-purpose` agent that a session's `Agent` tool starts with an empty context.
`/np-carry` gives each step of a package to one, and its main session serves what a helper cannot do
(`SPECIFICATION.md` §8.4.4). Probed on the cloud host with a helper on Sonnet at high effort, started
in the foreground by a main session on Opus 5.5. [verified][^probe]

### What it cannot do

- It has no `Agent` and no `AskUserQuestion`, and `ToolSearch` returns no schema for either. It
  cannot start an agent or ask the author: the main session does both for it.

### What it can do

- **Keep the task list.** `TaskCreate`, `TaskGet`, `TaskList` and `TaskUpdate` are deferred and
  load. Its `TaskList` returned the main session's eight tasks: a helper and its main session share
  one task list, the one the app shows.
- **Commit under the commit gate.** Its `git commit` ran `.claude/hooks/gate.sh`, which wrote
  `hook development 206 … passed` to `<git dir>/nanopnp-gate.log`, a file that did not exist before.
- **Run the push gate and push.** It started `gate.sh run` with `run_in_background`, waited on the
  log in the foreground (`gate: passed, 480 s.`, `exit 0`) and pushed the branch.
- **Resume.** `SendMessage` to a finished helper's id resumes it with its context: asked after it had
  finished, it gave its commit's subject from memory, without a tool.
- **Hand back.** Its last message reaches the main session as a message from its id, through its
  `SubagentHandback` tool.
- **Reach the session service.** It has the `mcp__claude-code-remote__*` tools, `send_message`,
  `create_session` and `subscribe_pr_activity` among them, and, deferred, `SendMessage` and the
  `mcp__github__*` tools. Not probed: which conversation a PR event wakes when a helper
  subscribes. `/np-carry` has its main session hold the subscription (`SPECIFICATION.md` §8.4.4).

### The main session's `Agent` tool

It takes `model` (`sonnet`, `opus`, `haiku`, `fable`) and `effort`. Its description asks that
`effort` be set only where an instruction asks for it, so `/np-carry` asks for `high`. [verified][^probe]

### A project agent file (WP6.07)

- **Its front matter sets the agent's model, effort and tools.** `.claude/agents/<name>.md` takes
  `name`, `description`, `model`, `effort` and `tools`; the `Agent` tool's description says an agent
  type's model, effort and tools come from that front matter, and that a `model` passed on the call
  overrides it. The physics reviewer and the GUI reviewer carry `effort: high`. [verified][^agents]
- **A file is loaded when the session starts.** An agent file written during a session is not found
  by that session's `Agent` tool: it lists the types it loaded at start. So a new agent is probed from
  the next session. [verified][^agents]
- **Opus 5.5 runs at `medium` effort where none is given**, Sonnet 5.5 at `high`; so a file of either
  names its effort. [verified][^api]
- **The four helpers run as their files say, and start small.** Each probe's transcript records the
  model and the effort it ran at; a tool list keeps out every other tool, and the task tools and the
  GitHub tools a file names come deferred and load through `ToolSearch`. An agent cannot name its own
  effort level: its context does not state it. [verified][^helpers]

  | Agent | Model | Effort | Context at its first call |
  |---|---|---|---|
  | `np-planner` | `claude-fable-5-2` | high | 12,670 tokens |
  | `np-builder` | `claude-opus-5-5` | high | 12,679 tokens |
  | `np-shipper` | `claude-sonnet-5-5` | medium | 12,834 tokens |
  | `np-reviewer` | `claude-opus-5-5` | high | 12,644 tokens |

  A `general-purpose` helper started at 73k to 76k tokens (WP6.06's post-mortem, §8.2.56).
- **A project's settings do not disable an account's plugins.** With `enabledPlugins` setting twelve
  of the claude.ai account's plugins `false` in `.claude/settings.json`, a session started on that
  tree still loaded them: the PDF viewer plugin's tools came back from `ToolSearch`. A helper's tool
  list keeps them out; the main session keeps them until the account disables them. [verified][^plugins]

[^probe]: Probe of 24 November 2026 for WP6.05's item 1, on the claude.ai cloud host (Linux), Claude
    Code 2.1.331, at commit `0212383`. The helper listed its tools, called `ToolSearch` with
    `select:Agent,AskUserQuestion,TaskCreate` (one schema came back, for `TaskCreate`) and
    `select:TaskList,TaskGet,TaskUpdate` (three), called `TaskList` once, wrote this note's first
    version, committed it, ran the push gate and pushed. It was resumed twice by `SendMessage`. A
    probe of the same day at `8b54c5f` found no task tools in a helper (the plan's *Grounding*).
[^agents]: WP6.07's item 1, 25 November 2026, on the claude.ai cloud host (Linux), Claude Code
    2.1.332. The four helper agents' files were written, and `Agent` with `subagent_type:
    "np-shipper"` returned "Agent type 'np-shipper' not found" with the list of the types loaded at
    start. The `Agent` tool's description is that version's.
[^helpers]: REV-289's probe, 25 November 2026, in the session after the one that wrote the files,
    Claude Code 2.1.332 on the cloud host: each agent started once in the foreground with a one-line
    task, and its sub-agent transcript read for `message.model`, the first call's input, cache-read and
    cache-write tokens, and the `effort` its entries record.
[^plugins]: WP6.07, 25 November 2026, Claude Code 2.1.332 on the cloud host: the session restarted on
    `659983c`'s tree, whose settings held the block, and `ToolSearch` `+pdf display` returned
    `mcp__plugin_pdf-viewer_pdf__display_pdf`.
[^api]: The Claude API skill bundled with Claude Code 2.1.332, its *Thinking & Effort* table: Opus 5.5's
    effort defaults to `medium`, Sonnet 5.5's to `high`.
