---
type: Ruling Record
title: "8.2.20 WP54's notebooks and figures, agreed 28 October 2026"
description: "Records the author's rulings on WP54's scope, taken in the review of WP51's notebooks and figures: structure preparation in the library, the notebooks reactive on the store, typed case factories with the schema unchanged, the field figures in physical units, and a published notebook at each checkpoint."
---

#### 8.2.20 WP54's notebooks and figures, agreed 28 October 2026

Rulings by the author, written in `docs/plans/notebooks-review-for-wp54.md` §7.1 as A1 to A4 on
28 October 2026, where they settle four conflicts between the author's notes and the specification
(§8.2.16 R8 left WP54's scope to that document). V5 was given the same day, while the package was
planned. The letter series continues at V; V1 to V4 are the document's A1 to A4.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| V1 | **Structure preparation enters the library in WP54**, as `nanopnp.structure.orient_pore`: it estimates the pore axis, keeps the chains named, points +z at the end the user names, and places a registration centroid on the axis. Notebooks 01, 02 and 06 then run from the deposited 2WCD entry | FR-37's library half is v0.5; the workbench surfaces it in v0.6 (WB-14). Example 06's `prepare.py` calls it. REV-41's `prepare` command stays with later work (§8.2.18 T3) | FR-37 and its Appendix A row, and the Phase 4 plan's WP54 entry, in this commit |
| V2 | **The notebooks run on the store, not in a fixed order** (*amends P5's "no widgets"*): no `only=True`, no `os.chdir`, one gitignored store shared by the six notebooks; a debounced slider drives only a fast stage or a view of a solved field, and a slow stage reads its settings from a submitted form | A changed value re-runs what it moves and takes the rest from the cache. The three 2WCD notebooks reuse one walk to the materials. The nightly run still exits 0 headless, a form's unsubmitted value falling back to its defaults | P5's pointer, in this commit; the notebooks, in WP54 |
| V3 | **The case schema stays as it is; the notebooks build cases with typed factories**, `Case.cylinder(...)` and `Case.from_structure(...)`. `Case.cylinder` meshes into the store, under a name keyed by its parameters, and sets `inputs.mesh.path`. Builders by section (`with_density`, `with_numerics`) wait for Phase 5 | IF-02 and `nanopnp/case/v0.5` do not move. A value the schema cannot say (a uniform wall surface charge) is not a factory argument | None; the Phase 4 plan's WP54 entry, in this commit |
| V4 | **The field figures read in physical units** (*amends P9 and FR-30*): the potential in mV on a scale centred at 0 mV; the mesh as the whole domain beside the lumen, with λ_D/5 marked; the signed axial velocity with streamlines in the lumen; axial and radial cutlines of any solved field, exported from `nanopnp.plot` | P9's `scale` and `interactive` values leave the notebooks; `figure(scale=)` stays. The cutlines are read from the stored P2 nodes, with no second restore | FR-30 and its Appendix A row, in this commit; P9's pointer, in this commit |
| V5 | **Each compaction checkpoint of WP54 publishes the notebooks revised so far as private artifacts for the author's steering.** *Added 28 October 2026, at WP54's plan.* The implementing session exports each notebook with `marimo export html`, publishes it, and ends the turn with the links | The export runs the notebook once and shows its widgets at their defaults; there is no kernel behind the page, and NGSolve has no browser build, so a moved slider recomputes nothing there. The author's comments are read before the next item starts | None; the WP54 plan |
