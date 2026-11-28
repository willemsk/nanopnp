---
type: Ruling Record
title: "8.2.63 WP6.11's plan: switches as data and the forces, agreed 28 November 2026"
description: "Records the author's rulings at WP6.11's plan: the log branch's case key is `numerics.log_variables`, filed with the numerical settings; the continuation ladder refuses the key, which a single solve runs; and the workbench's Equations tool shows it with the other switches."
---

#### 8.2.63 WP6.11's plan: switches as data and the forces, agreed 28 November 2026

Rulings by the author on 28 November 2026, at `/np-plan wp 6.11` under `/np-carry`, on branch
`ccr-27befe84-ows69p`. §8.2.62 BL7 made NUM-02's log branch a case key and left its path to this plan. The planning
helper read the phase entry against the code first. `io/case.py` holds the model's four switches under `physics:`
and the stabilisation's mode under `numerics:`; the NUM-18 ladder fixes the four switches and refuses a case that
sets one differently, and builds no rung on the log branch; and the workbench's Equations tool lists the switches
from a tuple in `physics/models.py`, which the package replaces by the switch records. The helper handed three
questions back, which the main session put through `AskUserQuestion` in one call, each with its options and
previews. The author chose the recommendation on each. The letter series continues at BM.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| BM1 | **The log branch's key is `numerics.log_variables`, with the numerical settings.** BL7 left the key's path open. The two places behave the same and differ in what the key is filed as: a way of computing, or a part of the physical model. Offered the numerical settings (*the recommendation*: NUM-02 is a choice of discretisation, as `numerics.stabilisation` is) and the physics switches, the author chose "With the numerical settings (Recommended)" | The key is a Boolean, false by default. The physics model's file owns it, as it owns `numerics.stabilisation`. Its switch record names that path, excludes PHY-23's switch, and a `true` is a deviation in the manifest (FR-25; BL7). It settles the first half of the Phase 6 plan's open decision 20 | §5.3.1 and NUM-02, with WP6.11; the Phase 6 plan's open decision 20, in this commit |
| BM2 | **The continuation ladder refuses the log key.** NUM-18's NOTE has the ladder read no switch of the model and refuse a case that sets one differently; neither it nor the phase entry names the new key, and the stored guard run on the log branch is a single solve. Offered the refusal (*the recommendation*: the ladder is a fixed path, and carrying the branch adds a stored walk and widens the package) and the ladder carrying the branch on its rungs, the more general of the two, the author chose "Refused beside the ladder (Recommended)" | A case with `numerics.log_variables: true` under `numerics.continuation: default_ladder` is refused at the case check, which names `numerics.continuation: none` as the remedy. The ladder's rungs stay on the primitive concentrations, and the package stores no new walk. The branch reaches no case that a single solve cannot reach | NUM-18's NOTE, with WP6.11 |
| BM3 | **The workbench shows the log key with the other switches.** The Equations tool lists the model's four switches from a list written in the code. The package reads that list from the records, so a fifth appears unless it is held back; the phase entry says only that the kernel changes no screen, and the workbench is rebuilt in Phase 8. Offered the key shown (*the recommendation*) and the key in the case file alone until then, the author chose "Shown with the other switches (Recommended)" | The Equations tool lists the records' five switches, the fifth labelled "Log concentrations". A model that honours one value of it holds it there, as it holds any switch. No screen's layout changes | None; `gui/web/tools.py`'s field list, with WP6.11 |
