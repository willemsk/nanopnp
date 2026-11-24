---
type: Ruling Record
title: "8.2.54 Phase 6 amended: the packages after the review numbered, agreed 24 November 2026"
description: "Records the author's ruling at /np-plan amend 6, which plans what is left of Phase 6 after the rulings on the ground-up review: the packages are numbered in the order they are built, so the orchestrator's package is WP6.05, the axis fix WP6.06, the guard numbers WP6.07 and the kernel's design WP6.08, and the earlier references to the axis package's number are rewritten."
---

#### 8.2.54 Phase 6 amended: the packages after the review numbered, agreed 24 November 2026

Ruling by the author on 24 November 2026, at `/np-plan amend 6`, on branch `claude/np-plan-amend-6-8e71eb`. This is
the amendment that §8.2.52 BB1 and §8.2.53 BC3 and BC7 asked for: it plans what is left of Phase 6 as the rulings on
the ground-up review leave it. The versions agreed before it but for one point, corrected here: §2.7, §3, §8.1 and
`CHANGELOG.md` give v0.7 for Phase 6, and the tag `v0.7.0-alpha.4` is published, which `docs/plans/current.md`
still called the author's to push. The round read the Phase 6 plan, §8.2.52, §8.2.53, the input note, §8.1's Phase 6
row, §8.3, §8.4.1, the ground-up review's GU-01, and the open rows of the review register that Phase 6 owns. The
order of the packages (BC3), the checks of the kernel (BC2, BC4) and the place of each later proposal (BC7) were
cited and not asked again. One question went through `AskUserQuestion`, with its context, three options and
previews; the author gave a free answer, against the recommendation. Four points are the session's reading of
rulings already taken and were not asked: that the author rules the kernel's design at a further `/np-plan amend 6`,
after WP6.08 merges, as BC2, BC10 and the amendment's route have it; that the first two packages the orchestrator
carries are WP6.06 and WP6.07; that the author sets the target for a package's touches at that further amendment;
and that the Phase 6 plan's file keeps its first name. After the write-up the session asked whether the two code
reviews and the quotations of the plan's record should also take the new number; the author answered "Keep as
written". The letter series continues at BD.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| BD1 | **Phase 6's packages are numbered in the order they are built, and the earlier references to the axis package's number are rewritten.** BC3 and BC10 put the orchestrator's package before the axis fix, which BB1 had numbered WP6.05. A package's tag takes its number (§8.4.1), and a run's record takes its version from the nearest tag, so the tags must rise along the history. The session offered the axis fix kept at WP6.05, with the orchestrator WP6.06 merged first and untagged (*the recommendation*: no earlier record would need a correction), the numbers in build order with a pointer on each earlier ruling, and the numbers kept with the tags out of order. The author answered: "Simply reorder by build order, and rewrite the old references to 6.05 in a clean way." (*against the recommendation*) | WP6.05 is the orchestrator's package, WP6.06 the axis fix, WP6.07 the guard numbers and WP6.08 the kernel's design. Each takes `v0.7.0-alpha.N` by its number, as §8.4.1 has it. The kernel's packages, the installed packages and the close take their numbers from WP6.09, at the amendment that rules the design. Each reference that named the axis package WP6.05 reads WP6.06: in the Phase 6 plan, the input note, REV-279's row and section, `holds-now.yaml`, §8.2.52's opening text and BB1, and §8.2.53's BC3 and BC10. Three kinds of text stay as written, which the author confirmed the same day: §8.2.50's AZ4 and AZ5, whose WP6.05 is the typed run record of a numbering that BA4 replaced; the code reviews 080 and 083, which report on a tree of their date; and the quotations in the Phase 6 plan's record, whose new section says how to read them | The Phase 6 plan; the input note; REV-279; §8.2.52's text and BB1; §8.2.53's BC3 and BC10, in this commit. BB1's number for the axis package is amended by this row |
