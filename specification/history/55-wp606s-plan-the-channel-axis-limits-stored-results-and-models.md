---
type: Ruling Record
title: "8.2.55 WP6.06's plan: the channel axis's limits, its stored results and the models, agreed 25 November 2026"
description: "Records the author's rulings at WP6.06's plan: the channel axis's two limits stay at 0.015 nm and 0.03 nm whatever 2WCD measures after the fix; a stored first stage whose axis came from the channel is computed again once, through a revision in its key that ring cases do not carry; and Opus 5.5 implements the package and Fable 5.2 ships it."
---

#### 8.2.55 WP6.06's plan: the channel axis's limits, its stored results and the models, agreed 25 November 2026

Rulings by the author on 25 November 2026, at `/np-plan wp 6.06`, the first plan `/np-carry` carried (§8.2.53 BC10),
on branch `claude/np-carry-wp-6-06-g7y44p`, after WP6.05's merge. The planning helper handed three questions back
and the main session put them through `AskUserQuestion`, each with its context, three options and previews: what
the two limits set from 2WCD become if the fix moves what 2WCD measures, which the Phase 6 plan's open decision 11
asked for before the fix was measured on it; whether a stored result of a channel-axis case is computed again, which
§5.3.2's NOTE on the solution payload leaves to the author (REV-77); and the two models (§8.2.50 AZ20, AZ21). The
author chose the recommendation on each and gave no free text. One point was settled by the plan's measurement, told
to the author in the round's brief and not asked: the fix is made at the cause the plan found, the edges of the
diagram that the code drops beside a tetrahedron with no centre, and not at the tie that REV-279 and §8.2.51 BA8
name, since a tie-robust centre alone still locked 11 of 21 seven-fold trial walls. After the rulings the plan
measured 2WCD on a prototype of the fix: its axis, its centroid and its 28 centres are the same to the last bit.
The letter series continues at BE.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| BE1 | **The channel axis's two limits stay, whatever 2WCD measures after the fix.** `axis: z` is admitted within 0.015 nm of the channel's axis, and a centre more than 0.03 nm from the line is warned of. Each was set at twice a number measured on 2WCD (0.0073 nm and 0.0148 nm; REV-239; §8.2.39 AO4). Offered that the limits stay (*the recommendation*), that each follows as twice the new measurement, and that a limit only ever rises, the author chose "The limits stay (Recommended)" | A file admitted or unwarned on v0.6 is not refused or warned of because a limit moved. Where the fix moves a measured number, the NOTE and VER-48 take the new number beside the unchanged limit, and the package reports the move. The package stops and comes back to the author only if 2WCD itself would be warned of or refused. This settles the Phase 6 plan's open decision 11 | The Phase 6 plan's open decision 11 and its row of what the author supplies, in this commit; open: WP6.06 (§5.2's NOTE on stage 1 and VER-48, only where a measurement moves) |
| BE2 | **A stored first stage whose axis came from the channel is computed again once.** Stage 1's key carries a revision of the channel's method where the channel gives the axis, under C1 or `symmetry.axis: cavity`, and nowhere else. Offered that those cases are computed again once (*the recommendation*), that stored results are kept with a line in the changelog, and that every pore's first stage is computed again, the author chose "Recompute those cases once (Recommended)" | A result that v0.6 stored for such a case is not found on v0.7: the pore is aligned again and the case's later stages run again, once. A ring's key, its stored results and VER-62's stored numbers do not move. A later change that moves a channel's axis raises the revision. A pore prepared by `prepared_pore` needs none: its file is keyed by the method's code | open: WP6.06 (§5.3.2's NOTE on the solution payload; `structure/stage.py`) |
| BE3 | **Opus 5.5 implements WP6.06 and Fable 5.2 ships it**, each at high effort. Offered that pair (*the recommendation*), Fable 5.2 for both, and Sonnet 5.5 to implement, the author chose "Opus 5.5 builds, Fable 5.2 ships (Recommended)" | The plan names each edit and each number, and leaves the clauses' wording and the measurement of 2WCD to the implementing session. The ship starts in a fresh helper and does not chain from the implementing one | The WP6.06 plan, in this commit |
