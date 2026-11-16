---
type: Ruling Record
title: "8.2.42 PHY-23's terms without the flow and under a solid fraction, agreed 16 November 2026"
description: "Records the author's rulings on REV-250, taken at WP5.18's ship: the dielectric-gradient switch is refused where no flow is solved and greyed in the Physics tools while the flow is off; and under a solid fraction both of its terms differentiate PHY-20's blend, built in WP5.18."
---

#### 8.2.42 PHY-23's terms without the flow and under a solid fraction, agreed 16 November 2026

Rulings by the author on 16 November 2026, at `/np-ship wp 5.18`, on REV-250. WP5.18 item 1's physics review found
that the dielectric-gradient switch, a deviation off by default, departed from PHY-23 in two ways. `pnp`, and `epnp-ns`
with the flow off on a single rung, assembled the Nernst–Planck term alone, where PHY-23 SHALL NOT permit either term
in isolation. Where a solid fraction `χ` reaches into the electrolyte, both terms differentiated the fluid's
`ε_r,f(⟨c⟩)` alone, though PHY-20's NOTE blends `ε_r = χ ε_p + (1 − χ) ε_r,f`. The force therefore lacked
`(ε_p − ε_r,f) ∇χ` and the factor `1 − χ`, and the decrement lacked `1 − χ`. Two questions went through
`AskUserQuestion` in one call, beside round 2's fields question. The first came back as a question ("Can that switch
not be automatically disabled (greyed out), or switched off when the flow is off?") and was asked again with that
answered. The letter series continues at AR.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| AR1 | **The switch is refused where no flow is solved, and greyed in the Physics tools while the flow is off.** In a case file a switch cannot be dropped silently, because the manifest would record a deviation the solve never carried (§5.3.3). It is therefore run or refused, and the author chose *refused* (*the recommendation*), over amending PHY-23 to admit the Nernst–Planck term alone, and over the GUI also turning the switch off when the flow is turned off | `pnp` declares `dielectric_gradient_forces: false` only. `physics.flow: false` beside the switch is refused naming PHY-23, with the remedy. The Physics tools grey the switch while the flow is off, and always in `pnp`, saying "Dielectric forces need the flow."; a switch left on is marked at its field with "Turn dielectric forces off, or turn the flow on." `pnp`'s Equations no longer writes the decrement | PHY-23's NOTE and the design document's Equations row, in WP5.18 |
| AR2 | **Under a solid fraction both terms differentiate the blend, built now.** The author chose this over refusing the switch beside a solid fraction until it was built (*the recommendation*), amending PHY-23 to differentiate the fluid's permittivity alone, and leaving it open | The force is `−½ ε_0 |∇φ|² [(1 − χ) ∇ε_r,f + (ε_p − ε_r,f) ∇χ]`. The decrement takes `(1 − χ) ∂ε_r,f/∂c_i`. `∇χ` is the exact derivative of the bilinear interpolant `χ` is evaluated by, because NGSolve differentiates a `VoxelCoefficient` to zero with no error. NUM-28's domain route takes the blend in its Maxwell stress, and the indicator current the blended decrement. The jump where the nearest solid changes is REV-257. The Equations tool writes `∇ε_r` and its definition | PHY-23's NOTE, in WP5.18 |
