---
type: Ruling Record
title: "8.2.35 WP5.09's plan: the physics model's boundaries and the exposed values, agreed 6 November 2026"
description: "Records the author's rulings at WP5.09's plan: the physics model owns the wall-distance field the corrections read; a continuum model's automatic wall size follows the salt of the physics model its study pairs it with, the design-concentration pin staying an optional continuum setting; and each kind of model has a default list of exposed values, which a model file may replace with its own."
---

#### 8.2.35 WP5.09's plan: the physics model's boundaries and the exposed values, agreed 6 November 2026

Ruling by the author on 6 November 2026, at `/np-plan wp 5.09`, after the third `/np-plan amend 5` (§8.2.34). AJ3
placed the equations, the electrolyte, the boundary conditions, the solid permittivities and the discretisation in the
physics model, and left two values unplaced: `numerics.wall_distance`, the PHY-02 distance field the wall corrections
read, and the coupling of `numerics.mesh.wall_h_nm: auto` to the electrolyte's Debye length, which the split puts in
another model than the mesh. AJ5 left where a model's exposed values are declared to this plan. The survey read
`io/models.py`'s ownership table, the stage-6 key, which carries the resolved wall size and not the salt
(`mesh/sizing.py` `WallSize.key`), and the design document's Physics suite, whose *Exposed values* tool edits a model's
list. Three questions were put through `AskUserQuestion` in one call, each with its context, options and previews. The
author took each recommendation. The letter series continues at AK.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| AK1 | **The physics model owns `numerics.wall_distance`**, its sources and its saturation distance, beside the corrections that read it (*the recommendation*, against the continuum model and against the study, which owned it before) | A physics model fixes its corrected equations completely, wall behaviour included, and carries them to every pore it is reused with; a study may still override it, and a value away from the validated one stays a recorded deviation. No key moves | §5.3.1's NOTE on `models:`, in this commit; open: WP5.09 |
| AK2 | **A continuum model's `wall_h_nm: auto` follows the salt of the physics model its study pairs it with**, as a case written inline does; `numerics.mesh.wall_for_concentration_M` stays the continuum model's optional pin (*the recommendation*, against an import that writes the pin at the case's salt and against a pin every continuum model must carry) | Every stage key is unchanged and VER-53 stands. One pore paired with physics models below about 1.474 M shares one mesh; above it, each salt builds its own, as today, and the sweep's forecast warns of it (AG5). The wall's validated accuracy is kept at every salt | §5.3.1's NOTE on `models:`, in this commit; open: WP5.09 |
| AK3 | **Each kind of model has a default list of exposed values, and a model file may replace it with its own `exposes:` list** (*the recommendation*, against a list written into every model file and against a fixed list per kind). The default lists are AJ5's: concentration and bias on a physics model, pH on a molecular model, the mesh's size scale on a continuum model. An entry's unit is its field's and its default is the model's own value | Model files stay short and an import writes no list; WP5.18's *Exposed values* tool writes a model's list, and WP5.19's Study suite reads it. No key moves | §5.3.1's NOTE on `models:`, in this commit; open: WP5.09, WP5.18, WP5.19 |
