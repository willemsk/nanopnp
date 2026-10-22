---
name: np-implement
description: Implement a planned nanopnp work package, keep the specification, knowledge base and plan in step, then gate, push and open its PR. Use when asked to implement or build a work package, execute its plan, or on /np-implement.
argument-hint: "[wp n]"
---

# Implement: `$ARGUMENTS`

1. Read the core, `${CLAUDE_SKILL_DIR}/../../workflow/core.md` (`.claude/workflow/core.md`).
2. Read the level's file beside this one, `${CLAUDE_SKILL_DIR}/wp.md`, and follow it.
3. `wp <n>` names the package. With no argument, take the package `docs/plans/current.md` names
   for this step; if it names none or several, ask. Any other argument: print
   `Usage: /np-implement [wp n]` and stop.
