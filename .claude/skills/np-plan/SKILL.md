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
4. Without `review`, follow the level's file; it ends with *The pause* below. With `review`, read
   `${CLAUDE_SKILL_DIR}/review.md` and follow its *The review*, against the level's caps and sections.

## The pause

The level's commit names, in `docs/plans/current.md`, `/np-plan <level> [n] review` as the next step,
before the level's own next step. After the level's report:

1. Print a prompt in a `text` block. It holds `/compact`, the level and n, the plan's path, the PR, the
   commit, the close calls that the plan's text does not hold, and "resume with
   `/np-plan <level> [n] review`".
2. End the turn. The author compacts and resumes. A skill cannot run `/compact` itself.
