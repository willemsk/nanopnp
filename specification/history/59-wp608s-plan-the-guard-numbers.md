---
type: Ruling Record
title: "8.2.59 WP6.08's plan: the guard numbers, agreed 26 November 2026"
description: "Records the author's rulings at WP6.08's plan: six of the model's settings get stored reference numbers before the kernel is rebuilt, the three §8.2.53 BC3 names and the simpler stabilisation and the two flow switches beside them; and the numbers are held in the reference environment alone, the guard tests skipping on macOS and Windows."
---

#### 8.2.59 WP6.08's plan: the guard numbers, agreed 26 November 2026

Rulings by the author on 26 November 2026, at `/np-plan wp 6.08`, the first plan carried the lean way (§8.2.56 BF7),
on branch `claude/zealous-planck-aio2ty`. The planning helper first checked the claim of §8.2.53 BC3 at its source:
of VER-62's seven walks, five take every switch of the model at its validated default and two take the flow off, so
none takes PHY-23's terms, the log branch or a stabilisation mode, and no Tier 1 or Tier 2 test solves the flow with
`physics.variable_density` or `physics.inertia` false. It measured each of six settings on example 02's ePNP-NS case
and handed two questions back, which the main session put through `AskUserQuestion`, each with its options and
previews. The author chose the recommendation on each. The letter series continues at BI.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| BI1 | **Six settings get guard numbers, not three.** §8.2.53 BC3 names PHY-23's terms, the log branch of NUM-02 and NUM-14's mode. Offered all six (*the recommendation*), the three names alone, and the three with the simpler stabilisation, the author chose "All six (Recommended)" | The package stores a walk for each of the three, and for `numerics.stabilisation: supg` (NUM-11), `physics.variable_density: false` and `physics.inertia: false` with the flow solved. This widens the Phase 6 plan's WP6.08 entry, which is rewritten, and settles the first part of its open decision 14. The six walks take about 270 s on one core of the nightly run | The Phase 6 plan's WP6.08 entry, its open decision 14 and its criterion 12, in this commit; open: WP6.08 (VER-80) |
| BI2 | **The guard numbers are held in the reference environment alone.** A guard asks whether a change moved a number, which one environment answers (§7.6's NOTE on a golden asserted on more than one platform). Offered Linux only (*the recommendation*) and all three platforms by VER-62's rule, the author chose "Linux only (Recommended)" | Outside `linux-x86_64/X86_V3` each guard test skips before its walk and names the environment; no record of macOS or Windows is folded, and no nightly run fails once to print one. VER-62's seven walks still ask every platform whether its answer is right. The kernel's last package holds the guard numbers on Linux (§8.2.53 BC4) | Open: WP6.08 (VER-80; §7.6's NOTE on the per-push selection) |
