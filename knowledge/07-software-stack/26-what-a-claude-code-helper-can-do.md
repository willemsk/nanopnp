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
`/np-carry` gives each step of a package to one (`SPECIFICATION.md` §8.4.4). Probed on the cloud host
with a helper on Sonnet at high effort. [verified][^probe]

### Its tools

- It has `Artifact`, `Bash`, `Edit`, `Glob`, `Grep`, `ListAgents`, `Read`, `ReportFindings`, `SearchPlugins`, `SendUserFile`, `ShowOnboardingRolePicker`, `Skill`, `SuggestPluginInstall`, `SuggestSkills`, `ToolSearch`, `Write`, `SubagentHandback`, `mcp__ccd_session__dismiss_task`, `mcp__ccd_session__spawn_task`, `mcp__Claude_Docs__batch`, `mcp__Claude_Docs__guide`, `mcp__Claude_Docs__update` and the `mcp__claude-code-remote__*` session tools, and, deferred, `TaskCreate`, `TaskGet`, `TaskList`, `TaskStop`, `TaskUpdate`, `SendMessage`, `Monitor`, `CronCreate`, `CronDelete`, `CronList`, `WebFetch`, `WebSearch`, `ArtifactComments`, `ArtifactData`, `EnterWorktree`, `ExitWorktree`, `NotebookEdit`, `ListSkills`, `ListPlugins`, `ListConnectors`, the `mcp__github__*`, `mcp__Context7__*`, `mcp__Claude_Docs__*` and other `mcp__*` tools that a system message names.
- It has no `Agent` and no `AskUserQuestion`, and `ToolSearch` returns no schema for `Agent` or `AskUserQuestion`.
- `TaskCreate`, `TaskGet`, `TaskList` and `TaskUpdate` are deferred, and `ToolSearch` loads their schemas.
- Its `TaskList` returns the main session's 8 tasks (#1 in progress, #2 to #8 pending), which are the 8 items of WP6.05.

[^probe]: Probe of 2026-11-24: the helper listed its tools and called `ToolSearch` with `select:Agent,AskUserQuestion,TaskCreate`; the result held one schema, for `TaskCreate`.
