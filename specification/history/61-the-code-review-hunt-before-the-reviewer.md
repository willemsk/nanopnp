---
type: Ruling Record
title: "8.2.61 The code-review hunt before the reviewer, agreed 27 November 2026"
description: "Records the author's rulings that a package's ship, and a chore that changes code, the git hooks, the GUI's scripts and the justfile among it, run the /code-review skill at high in the main session, report-only, and hand its findings to np-reviewer, which checks and fixes each in its one pass; this amends §8.2.56 BF4's no code-review fork."
---

#### 8.2.61 The code-review hunt before the reviewer, agreed 27 November 2026

Rulings by the author on 27 November 2026, at `/np-chore`, on branch `ccr-a1bfde87-pka0hj`. The author noted that the
workflow had dropped the `/code-review` skill and asked why. The session traced it: until WP6.07, `/np-ship` called
`Skill(skill="code-review", args="xhigh --fix --max-findings all <pr>")` from the shipping session, with the note
"Inside an `Agent` the skill returns no findings; called directly, it starts its own review agent" (`np-ship/wp.md` at
`5b1e7fb`); §8.2.56 BF4 then made `np-reviewer` the one review, with no `code-review` fork, after the post-mortem found
the three forks of WP6.06 had run on Fable, the main session's model. A helper has no `Agent` tool, so it cannot run the
skill; the main session can, and its forks now take Sonnet 5.5, the model of a ship and of `/np-carry`'s main session.
The carry's main session edits nothing (§8.4.4), so a hunt that fixes would break that rule. Three questions went
through `AskUserQuestion` in one call, each with options and previews. The author chose the recommendation on each.
The letter series continues at BK.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| BK1 | **The `/code-review` hunt runs first, report-only, and `np-reviewer` checks and fixes its findings.** Offered the hunt first with the reviewer fixing (*the recommendation*: one fixer, and the main session still edits nothing), the reviewer first with the hunt fixing after as before WP6.07, and the hunt reporting only with its findings left as rows, the author chose "Hunt first, reviewer fixes (Recommended)" | The session that starts the full review, the ship's or `/np-carry`'s main session, calls the skill directly, never inside an `Agent`, on the reviewed head, and adds its findings to `np-reviewer`'s prompt. The reviewer judges each on its axes, fixes what it confirms as it fixes its own, and lists each in its one report with its outcome. A helper hands back `REVIEW` as before; the main session runs the hunt before it starts the reviewer | Amends §8.2.56 BF4's "no `code-review` fork"; §8.4.4; §8.4.5; `CLAUDE.md` *Implementation workflow*; `.claude/agents/np-reviewer.md`, `.claude/skills/np-ship/wp.md`, `np-carry/`, `np-chore/`, `.claude/workflow/helper.md`, in this commit |
| BK2 | **The hunt runs at `high`.** Offered `high` (*the recommendation*: the reviewer checks each finding, so `xhigh`'s extra uncertain findings mostly add sifting), `xhigh` as before WP6.07, and `medium`, the author chose "high (Recommended)" | `code-review high --max-findings all <head branch>`, with no `--fix` | §8.4.4, in this commit |
| BK3 | *Its paths are widened by BK4.* **The hunt runs at a package's ship and on a chore that changes code.** Offered ships and code chores (*the recommendation*), ships only, and every review, the medium-effort review of a pulled-in fix's diff included, the author chose "Ships, and code chores (Recommended)" | A chore runs it where a changed path is under `src/` or `tests/`, or is a `.py` or `.sh` file; a chore of workflow text or settings, and the review of a fix's own diff, keep `np-reviewer` alone | §8.4.4; `.claude/skills/np-chore/`, in this commit |
| BK4 | **The chore's hunt also covers the git hooks, the GUI's scripts and the justfile.** Ruled later the same day, on the chore's review ([CODE_REVIEW_098](../../docs/code_reviews/CODE_REVIEW_098.md)): BK3's paths let code without those endings past the hunt, `.githooks/pre-push`, `.claude/scripts/gui/*.cjs` and `justfile`. Offered adding `.githooks/` and `.cjs` files (*the recommendation*: the justfile lists commands), adding the justfile as well, and keeping BK3, the author chose "Also the justfile" | A chore runs the hunt where a changed path is under `src/`, `tests/` or `.githooks/`, is a `.py`, `.sh` or `.cjs` file, or is `justfile`; YAML workflows and settings keep `np-reviewer` alone | Widens BK3's paths; §8.4.4; `.claude/skills/np-chore/`, in this commit |
