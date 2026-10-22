---
name: np-ship
description: Ship a finished nanopnp work package or close a phase — gate, push, reuse its PR, run /code-review xhigh --fix, drive CI to green; a phase also checks its close and tags the release. Use when asked to ship, review or open the PR for a package, close a phase, or on /np-ship.
argument-hint: "[wp n | phase n]"
---

# Ship: `$ARGUMENTS`

1. Read the core, `${CLAUDE_SKILL_DIR}/../../workflow/core.md` (`.claude/workflow/core.md`).
2. `wp <n>`, or no argument: read `${CLAUDE_SKILL_DIR}/wp.md`, beside this file, and follow it.
   `phase <n>`: read `${CLAUDE_SKILL_DIR}/phase.md` and follow it; it runs `wp.md` too.
3. Any other argument: print `Usage: /np-ship [wp n | phase n]` and stop.
