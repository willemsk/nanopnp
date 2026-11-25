---
type: Ruling Record
title: "8.2.56 WP6.09's plan: the lean carry, agreed 25 November 2026"
description: "Records the author's rulings after WP6.06's post-mortem: Fable 5.2 only plans, Sonnet 5.5 runs the carry's main session and ships with Opus 5.5 on a red CI, Opus 5.5 builds and reviews; a helper that waits ends with a hand-off note and a fresh helper continues; the plan checks itself; one Opus review at the ship holds the physics questions; a finding left to the author is an open item by default; each helper lists its tools and the unused plugins are disabled; and the change is a package planned and built in the post-mortem's conversation, before WP6.07."
---

#### 8.2.56 WP6.09's plan: the lean carry, agreed 25 November 2026

Rulings by the author on 25 November 2026, after WP6.06 merged, in the conversation that carried it. The author
stopped the carry before its CI and asked for a post-mortem, as the workflow was too usage heavy, naming four
causes: Fable used beyond planning, resumes of paused helpers after expired caches, repeated code reviews, and dear
models on mechanical steps. The session measured the transcripts: Fable did 85% of the package's token-weighted
work; the three `code-review` forks ran on Fable because a fork takes the main session's model; resumes after a gap
of more than five minutes rewrote 2.2 M tokens of cache, about 22% of Fable's share; about 130 of 570 helper tool
calls were mechanical; and every helper started at 73k to 76k tokens, mostly unused MCP tools. Seven decisions were
put one by one through `AskUserQuestion`, each with options and previews. The author chose the recommendation on
six and a third option on the first, and gave no free text. The letter series continues at BF.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| BF1 | **Fable 5.2 only plans; Sonnet 5.5 ships, with Opus 5.5 on a red CI.** Fable 5.2 runs the plan's helpers; Sonnet 5.5 runs `/np-carry`'s main session and the ship; Opus 5.5 builds and reviews. Offered that Sonnet ships (*the recommendation*), that Opus ships, and that Sonnet ships with a CI failure that is a test or a numerical gate going to a fresh Opus helper, the author chose "Sonnet, Opus on a red CI" | Each role's model is fixed in its agent file and no longer proposed per plan; the ship escalates a red CI that is not lint, format or a flaky runner to Opus with the classified log | Supersedes §8.2.50 AZ20 and AZ21; open: WP6.09 (§8.4.5; `CLAUDE.md` *Models*) |
| BF2 | **A helper that waits ends with a hand-off note; a fresh helper continues.** Offered the note and a fresh helper (*the recommendation*), all questions up front, and default answers vetoed in the pull request, the author chose "Hand-off note, fresh helper (Recommended)" | No helper is resumed after the author, a worker or a review answers; the plan stage is two helpers, survey-measure-ask and write | Supersedes the resume of §8.2.54 BD2; open: WP6.09 (§8.4.4, §8.4.5; `.claude/workflow/helper.md`) |
| BF3 | **The plan checks itself; no review run of the plan.** Offered a self-check (*the recommendation*), a Sonnet read at low effort, and the review kept on Opus, the author chose "Self-check, no review run (Recommended)" | `/np-plan wp n review` becomes the self-check and the approval summary | open: WP6.09 (§8.4.4) |
| BF4 | **One Opus review at the ship, with the physics questions in it.** Offered one Opus review at high (*the recommendation*), the physics reviewer alone where physics changes, and both, the author chose "One Opus review, physics in it (Recommended)" | A project agent `np-reviewer` on Opus at high reviews standards, specification and numerics once; no separate physics reviewer at the ship and no `code-review` fork | open: WP6.09 (§8.4.4, §8.4.5) |
| BF5 | **A finding left to the author is an open item by default.** Offered the open item (*the recommendation*), always a follow-up package, and the author's call each time, the author chose "Open item by default (Recommended)" | The pull request merges as reviewed; a finding the author pulls in gets a review of its own diff on Sonnet at low effort, never a full pass | open: WP6.09 (§8.4.4, §8.4.6) |
| BF6 | **Each helper lists its tools, and the unused plugins are disabled.** Offered both (*the recommendation*), tool lists only, and the author removing the plugins from the account, the author chose "Tool lists, and disable plugins (Recommended)" | Helpers start near the physics reviewer's 14k tokens; the project's settings disable each plugin it never uses | open: WP6.09 (`.claude/agents/`, `.claude/settings.json`) |
| BF7 | **The change is a package planned and built here, before WP6.07.** Offered a package planned in the conversation (*the recommendation*), an amendment of Phase 6 through `/np-plan amend 6`, and direct edits with no package, the author chose "A package planned here (Recommended)" | WP6.09 is planned, built and shipped on Opus 5.5 in the post-mortem's conversation, with no helper; WP6.07 is the first package carried the lean way and measures it | The Phase 6 plan and the WP6.09 plan, in this commit |
