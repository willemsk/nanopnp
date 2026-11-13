---
type: Ruling Record
title: "8.2.41 WP5.18's plan: the study a physics model is shown in, and what a change of model sets, agreed 13 November 2026"
description: "Records the author's rulings at WP5.18's plan: each Physics tool shows its physics model inside a study picked in the pane, that study's own physics values left out, or over the project's continuum model where the project holds no study; and choosing another registered model sets the switches it honours and removes the values it refuses, listing each change with an undo."
---

#### 8.2.41 WP5.18's plan: the study a physics model is shown in, and what a change of model sets, agreed 13 November 2026

Rulings by the author on 13 November 2026, at `/np-plan wp 5.18`, after WP5.17's merge as `v0.6.0-alpha.17`. The
survey found that a physics model has no build of its own and no pore, that a study naming it is checked for the
model's switches only when it resolves, and that the design document's Conditions tool draws "the open study's
geometry" without saying which study, or what a model no study names is shown on. It found too that a change of
registered model is almost never valid alone: `pnp` honours the flow off only, and `pnp-ns` reads no correction. Two
questions went through `AskUserQuestion` in one call, each with its context, options and previews. The author took
each recommendation. The letter series continues at AQ.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| AQ1 | **Each Physics tool shows its physics model inside a study picked in the pane.** *Shown in* lists every study of the project; the case shown is that study with this physics model in place of its own and the study's own values of the physics model's keys left out, so every value the pane shows is the case's. It opens on the first study that names the model, else the project's first study; a project with no study shows the model over its continuum model as that model is built alone. The author chose this (*the recommendation*), over the studies that name the model alone and over a fixed reference pore | Conditions draws the shown study's pore and its boundaries; a value the shown study cannot run with is shown at its field, naming the study, and a study's own value of a physics key is marked beside the field with an outlined diamond (WB-28). The rule is the sweep's over `models.physics` (FR-39 (b)), so the Study suite reuses it | The design document's Physics rows, in this commit; §5.3.1's NOTE on model files, in WP5.18 |
| AQ2 | **Choosing another registered model in Equations sets each switch it does not honour to the value it does, and removes each value it refuses**: a leaf it does not read set away from its default, solid permittivities where it carries no solid, and a wall charge where it takes none. One note lists every change, with *Undo*, which writes the earlier values back. The author chose this (*the recommendation*), over writing the model alone and naming one value to change at a time | ePNP-NS to PNP turns off the flow, the variable density and the inertia, and resets the viscosity and density corrections and the velocity and pressure orders; a study's own value the model refuses, such as its continuation, stays the study's and is shown at its field. The model's declaration decides, never its name (§5.4.3's NOTE) | The design document's Equations row, in this commit; §5.3.1's NOTE on model files, in WP5.18 |
