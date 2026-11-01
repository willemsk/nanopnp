---
name: np-implement
description: Implement a planned nanopnp work package, keep the specification, knowledge base and plan in step, then gate, push and open its PR. Use when asked to implement or build a work package, execute its plan, or on /np-implement.
argument-hint: "[wp n]"
---

# Implement: `$ARGUMENTS`

1. An argument other than `wp <n>` (`54` or `5.01`) or none: print `Usage: /np-implement [wp n]` and stop.
2. Read the core, `${CLAUDE_SKILL_DIR}/../../workflow/core.md` (`.claude/workflow/core.md`).
3. Read the level's file beside this one, `${CLAUDE_SKILL_DIR}/wp.md`, and follow it. `wp <n>`
   names the package; with no argument, the core's *The package's PR and branch* finds it.
