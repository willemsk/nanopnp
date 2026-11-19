---
type: Ruling Record
title: "8.2.45 WP5.21's plan: a borrowed chart library, any colour map, and the comparison's two views, agreed 19 November 2026"
description: "Records the author's rulings at WP5.21's plan: every plot of the workbench is drawn by a borrowed chart library whose axes the user sets; any Matplotlib colour map is offered per map and recorded with a comparison; and Comparison draws two runs side by side as two maps on one grid, or switched to two 3D field views on one range."
---

#### 8.2.45 WP5.21's plan: a borrowed chart library, any colour map, and the comparison's two views, agreed 19 November 2026

Rulings by the author on 19 November 2026, at `/np-plan wp 5.21`, after WP5.20's merge. The survey found three
choices that the phase entry and the design document leave open. REV-253 asked for tunable plot axes "with the analysis
suite", with a plotting module built or borrowed. WB-20 rules any Matplotlib colour map per plot, which REV-240 placed
with Analysis, while the workbench installs no Matplotlib. FR-32's side-by-side view had no renderer named, beside
AG6's difference on a grid. Three questions went through `AskUserQuestion` in one call, each with its context, options
and previews, after a brief of what the plan had settled. The letter series continues at AU.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| AU1 | **Every plot of the workbench is drawn by a borrowed chart library, and the user sets its axes.** Asked how the Analysis suite gives tunable plot axes (REV-253), the author chose "Borrow a chart library" (*against the recommendation*, which was a scale and a range built into the workbench's own plots), over building them and over leaving the axes fixed | uPlot 1.6.32 (MIT, no dependencies) is vendored unmodified as separate files, beside Mol* and KaTeX. It draws every plot of x against y: the explorer's I–V and axial cut, Comparison's cut, Electrolyte's two plots and Runs' convergence. Each axis is linear or logarithmic, and Electrolyte's driver stays on a square-root axis. The user types each axis's range, zooms by dragging and reads values by hovering. The (r, z) canvas keeps maps, meshes and drawings. About one session and two to three agent hours more | ADR-004's NOTE (the front end, v0.6), the design document's renderer table and REV-253, open: WP5.21 |
| AU2 | **The workbench offers any Matplotlib colour map per map, and a comparison records its map.** The author chose "Any Matplotlib map" (*the recommendation*), over six maps copied in and over leaving the two built-in maps | The `gui` extra gains Matplotlib. Each field map and each comparison offers every registered map by name, and its reverse. A comparison's file records its map. Viridis and the diverging map stay the defaults, and charge opens diverging (VER-60). The 3D field view keeps the renderer's own map. About one agent hour; the install grows by about 10 MB of ready-built wheels | §2.6's NOTE on the workbench's dependencies and REV-240's colour-map point, open: WP5.21; WB-20 holds as written |
| AU3 | **Comparison draws two runs side by side as two maps on one grid, and *On the mesh* switches the pair to two 3D field views on one range.** The author chose "Both, switchable" (*against the recommendation*, which was the two maps alone), over the maps alone and over the 3D views alone | The pair opens as two maps of AG6's grid on one colour scale, with the cut and the probes on both. *On the mesh* redraws the pair as two `webgui` scenes, each fixed to the two runs' joint range. The difference stays the grid's map. About one session more. On 2WCD's coarse round mesh, each scene is a few megabytes | The design document's Comparison row, open: WP5.21 |
