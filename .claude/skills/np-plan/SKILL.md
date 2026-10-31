---
name: np-plan
description: Plan nanopnp work at a level and commit it — the project, a phase, an amendment to a phase in flight, or one work package. Use when asked to plan or re-plan the project, a phase or a work package, or on /np-plan.
argument-hint: <project | phase n | amend n | wp n>
---

# Plan: `$ARGUMENTS`

If `$ARGUMENTS` or `${CLAUDE_SKILL_DIR}` appears literally, the arguments are the text after the
command and the directory is `.claude/skills/np-plan/` (`.claude/workflow/hosts.md`).

1. The first argument is the level, the second its number n (for `wp`, `54` or `5.01`). A missing or unknown level, or a
   level other than `project` without n: print `Usage: /np-plan <project | phase n | amend n | wp n>`
   and stop.
2. Read the core, `${CLAUDE_SKILL_DIR}/../../workflow/core.md` (`.claude/workflow/core.md`).
3. Read the level's file beside this one: `${CLAUDE_SKILL_DIR}/<level>.md`, one of `project.md`,
   `phase.md`, `amend.md` and `wp.md`. `project`, `phase` and `amend` also read `rulings.md` beside
   it.
4. Follow the level's file.
