---
name: np-plan
description: Plan nanopnp work at a level and commit it — the project, a phase, an amendment to a phase in flight, or one work package — then, after a compaction, review the plan, fix it and summarise it for approval. Use when asked to plan or re-plan the project, a phase or a work package, or on /np-plan.
argument-hint: <project | phase n | amend n | wp n> [review]
---

# Plan: `$ARGUMENTS`

1. The first argument is the level, the second its number n (for `wp`, `54` or `5.01`). A last argument
   `review` asks for the level's review. A missing or unknown level, or a level other than `project`
   without n: print `Usage: /np-plan <project | phase n | amend n | wp n> [review]` and stop.
2. Read the core, `${CLAUDE_SKILL_DIR}/../../workflow/core.md` (`.claude/workflow/core.md`).
3. Read the level's file beside this one: `${CLAUDE_SKILL_DIR}/<level>.md`, one of `project.md`,
   `phase.md`, `amend.md` and `wp.md`. `project`, `phase` and `amend` also read `rulings.md` beside
   it.
4. Read `${CLAUDE_SKILL_DIR}/review.md`. Without `review`, follow the level's file; it ends with
   `review.md`'s *The pause*. With `review`, follow `review.md`'s *The review*, against the level's caps
   and sections.
