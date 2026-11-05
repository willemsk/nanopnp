---
type: Ruling Record
title: "8.2.33 WP5.08's plan: a user's colour themes and the plan's review, agreed 5 November 2026"
description: "Records the author's ruling at WP5.08's plan: the workbench's settings offer a theme selector and a colour modifier, as a modern code editor's do, so a user chooses among the shipped light and dark themes and themes of their own and edits each colour of one; a user's theme sets its own contrast; and, added after the plan, every level of the planning command ends with a review after a compaction and a summary for the person who approves the plan."
---

#### 8.2.33 WP5.08's plan: a user's colour themes and the plan's review, agreed 5 November 2026

Ruling by the author on 5 November 2026, at `/np-plan wp 5.08`, after WP5.07's merge. T8 (§8.2.18) has a user adjust or
choose a theme, its colours, density, spacing and the 3D view's background, saved per user. The plan asked through
`AskUserQuestion` whether the frame's settings offer the light and dark modes, the density, the spacing and the 3D
background, with a user's own colours deferred past v0.6, or also a colour theme of the user's own, checked against the
contrast target. The author chose the second, in their words: "Also allow a color themes. I think this can be like the
theme selector/modifier under settings of many modern IDEs." While the plan was written, the author
added: "User set themes define their own contrast, no need for us to worry about that." The letter
series continues at AI.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| AI1 | **The settings offer a theme selector and a colour modifier, as a modern code editor's do.** A user chooses the system's choice of the shipped light and dark themes, either one, or a theme of their own, a plain file saved per user that names its base, light or dark, and the colour tokens it changes. A shipped theme is read-only; it is duplicated to be modified. Each colour of a user's theme is edited in the settings. A user's theme sets its own contrast: the workbench does not check it | QR-16's target binds the shipped themes, which the render check measures; a user's theme is the user's choice. About two days in WP5.08, with no contrast measure in the shell | QR-16, in this commit; the theme itself, open: WP5.08 |
| AI2 | *Added 5 November 2026, at WP5.08's plan.* **Every level of `/np-plan` ends with a review after a compaction.** The level's own call pushes the plan, opens its PR, reports and pauses; the author compacts, and `/np-plan <level> [n] review` runs `/code-review medium --fix --max-findings all` on the branch, fixes or records each finding, gates and pushes again. The author, after a code review of this plan that the author ran by hand: "I would like for the compaction, code-review, and manager summary to be part of the np-plan skill." Asked how, since a skill cannot run `/compact`, the author chose a pause and a resume over a reviewer sub-agent or a review in the same context, and every level over the work package alone | The review reads the plan in a context that did not write it; one more turn and one review per plan | §8.4.4, in this commit; `.claude/skills/np-plan/review.md` |
| AI3 | *Added 5 November 2026, at WP5.08's plan.* **The review ends with a summary for the person who approves the plan,** in the chat, as the final report: what it delivers, what it builds on, each decision in plain words, the rulings, what the checks changed, how the work runs and is verified, what it leaves out, its risks and what the approver must do. The author chose the chat over a comment on the PR or a shareable page | A reader who does not code can approve from it | §8.4.4, in this commit; `.claude/skills/np-plan/review.md` |
