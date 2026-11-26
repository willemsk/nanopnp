---
type: Ruling Record
title: "8.2.58 A REV row is for an item that outlives its session, agreed 26 November 2026"
description: "Records the author's ruling that a REV row is kept only for a deferral, a doubt only the author can settle, or a finding larger than a small edit, and that a small finding is fixed in the session that finds it, a review not being done until each is fixed."
---

#### 8.2.58 A REV row is for an item that outlives its session, agreed 26 November 2026

Ruling by the author on 26 November 2026, while `/np-chore` was being reviewed: the review had left two small findings
(REV-296, REV-297) that a session could fix at once, and each had become a permanent row. The two questions were put
through `AskUserQuestion`, each with options and their consequences. The letter series continues at BH.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| BH1 | **A `REV` row is for an item that outlives the session that found it.** Offered that line (*the recommendation*), a severity line and a size-of-fix line, the author chose the first; and offered that a small finding left over goes in the report and the PR body only (*the recommendation*), or is always fixed in the session, the author chose "Always fixed in the session, no exceptions" | A deferral to a later package, a doubt only the author can settle, or a finding whose fix is more than a small edit is a row. A small finding, a doubt among them where its fix moves no ruling, is fixed in the session: `np-reviewer` fixes it, the ship has `np-builder` fix one it left, and a chore's session fixes it, so a review, a ship and a chore are not done until each is fixed. This amends §8.2.8 H12's and §8.2.56 BF5's rows for such items. REV-296 and REV-297 are fixed as their recommendations say and closed, which amends §8.2.57 BG3's failed land and BG2's worktree refusal | §8.4.4; §8.4.6; `CLAUDE.md` *Open items*; `.claude/agents/np-reviewer.md`, `.claude/skills/np-ship/wp.md`, `np-chore/`, `.claude/workflow/core.md`, `author.md`, in this commit; `np-shipper.md`, `helper.md`, `finish.md`, `np-gui/`, `np-plan/review.md` and `np-implement/finish.md` at its review (CODE_REVIEW_094) |
