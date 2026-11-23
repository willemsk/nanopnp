---
type: Ruling Record
title: "8.2.52 Phase 6 amended: the ground-up review planned, agreed 23 November 2026"
description: "Records the author's rulings at /np-plan amend 6, which plans the ground-up review as WP6.04 and numbers the axis package WP6.05: the author rules on the review's proposals before the axis fix is built; and the review designs for the whole program as it is specified today, what is built and what is planned up to version 1."
---

#### 8.2.52 Phase 6 amended: the ground-up review planned, agreed 23 November 2026

Rulings by the author on 23 November 2026, at `/np-plan amend 6`, on branch `claude/practical-cerf-81g9zz`. This is
the amendment that §8.2.51 BA8, BA10 and BA11 asked for: it plans the ground-up review as WP6.04, numbers the axis
package WP6.05, and lists the rest of Phase 6 as provisional, by scope and without numbers. The versions agreed before
it: §2.7, §3, §8.1, `CHANGELOG.md`, `docs/plans/current.md` and the published tags all give v0.7 for Phase 6, with
`v0.7.0-alpha.3` the last tag, so WP6.04 takes `v0.7.0-alpha.4` and WP6.05 `v0.7.0-alpha.5` (§8.4.1). The round read
the Phase 6 plan, §8.2.51, the input note, REV-279 with the knowledge base's note on 2WCD's channel axis, and
`structure/stage.py`, which gives the channel's axis only under C1 or `axis: cavity`. BA4, BA8 and BA10 to BA13 were
cited and not asked again. Two questions went through `AskUserQuestion` in one call, each with its context, options
and previews. The author chose against the recommendation once (BB1) and with it once (BB2). Three decisions that
belong to one package were left to its plan and are open decisions of the Phase 6 plan: how the review guards
against reasoning from the program as it is, where its report lives, and what VER-48's two limits become if the fix
moves 2WCD's measured axis. The letter series continues at BB.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| BB1 | **The author rules on the review's proposals before the axis fix is built.** BA8 made the axis package firm and BA11 placed it after WP6.04's merge; neither said whether it comes before or after the ruling round on the review. The session offered the axis fix first and the round after it (*the recommendation*: the fix is independent of the review, and the report gets reading time while the fix is built), the rulings first, and no fixed order. The author chose "Rulings first" (*against the recommendation*) | The order is WP6.04, the ruling round at `/np-plan project`, a further `/np-plan amend 6`, then WP6.05, the axis package, then what that amendment plans. WP6.05 keeps its number and stays firm: a declined proposal leaves it as BA8 has it. Its plan is written after the round, on the phase as the round leaves it, so a proposal of the review on how a pore's axis is found is ruled before the fix is built. The fault of REV-279 stays in the program for the length of the round | §2.7's v0.7 row; §8.1's Phase 6 row; the input note; the Phase 6 plan, in this commit; BA8's and BA11's place for the axis package is amended by this row; open: the round after WP6.04 |
| BB2 | **The review designs for the whole program as it is specified today, what is built and what is planned.** BA10 asks how the program would be built "given what the program is now", and BA12 opens the requirements to it; neither says whether the start-over design covers only what v0.6 does. The session offered one design for the whole program as specified, built and planned (*the recommendation*: BA1 keeps all three tools before validation, so a design that leaves them out could need a second restructure), a design for today's program with the planned work only checked for fit, and both designs side by side. The author chose "Today and the plan" | WP6.04's design covers §3 in full: what v0.6 delivers, and what §2.7 plans up to v0.13, which is the rebuilt workbench, the composer, the mutator with fractional protonation, the sketcher, the analyte forces, and validation with the release. BA12 stands: the review may propose to change or drop any of those requirements, and each proposal names its clause. The estimate of BA10 is unchanged | §2.7's v0.7 row; §8.1's Phase 6 row; the input note; the Phase 6 plan, in this commit; open: WP6.04 |
