---
type: Ruling Record
title: "8.2.2 Phase 2 decisions, agreed 24 September 2026"
description: "Records the author's Phase 2 rulings, agreed 24 September 2026, and the commit that amends any clause each changes."
---

#### 8.2.2 Phase 2 decisions, agreed 24 September 2026

Rulings by the author, taken while planning Phase 2 (`docs/plans/phase-2-geometry-pipeline.md`).
Where a ruling changes a clause, the clause is amended in the commit named in the last column.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| B1 | Phase 2 starts only after the Phase 1 end-of-phase report has merged (tag `v0.2.0`) and the author has recorded the double-click observation of amendment A4 | The start condition of §8.1 is met as written, not amended: criterion 4 and RSK-13 close on the observation | None |
| B2 | VAL-05 is measured on two inputs. The public 2WCD entry (wwPDB, CC0) is vendored as test data and gated at Tier 2 to a looser tolerance. The author's 50-frame ClyA-AS ensemble, or the prepared structure it came from, is archived under `NANOPNP_REFERENCE_DATA` and run at Tier 3. The Phase 2 gate requires the ensemble leg | 2WCD lacks residues 1–7 at the *trans* constriction and the MD relaxation, so only the ensemble can be held to a tight tolerance. The 2WCD leg still exercises the whole pipeline on every push | §7.4 VAL-05, in the Phase 2 plan's commit. The tolerances are stated in the VAL-05 work package |
| B3 | The case schema moves **once**, to `nanopnp/case/v2`, in the first Phase 2 work package. That move carries every key Phases 2 and 3 are foreseen to need, among them stage-4 hand substitution under `inputs:` and the membrane's axial position. A v1 document reads losslessly as v2 | The §5.3.1 compatibility rule stands: adding a key moves the version, and it moves once rather than once per phase | §5.3.1, in the first Phase 2 work package |
| B4 | The Python floor rises to 3.11 (Python 3.10 reaches end of life in October 2026) | One MDAnalysis (2.10) and one GridDataFormats (1.2) across the supported range, as §2.6 names them. The IF-05 NOTE's conditional CCP4 write side is retired | QR-09 and §2.5, in the Phase 2 plan's commit. The IF-05 NOTE, `requires-python` and the CI matrix change with the code, in the first Phase 2 work package |
| B5 | The radius-profile criterion of stage 3 and §5.2.1 is checked against a probe-radius profile computed in project code on the aligned structure. HOLE, through `mdahole2`, becomes an optional cross-check that skips when absent | HOLE is a compiled binary with no wheel, so it cannot sit on the end-user path (CON-07, QR-09) | §5.2 stage 3 and §5.2.1, in the Phase 2 plan's commit |
| B6 | The author's contour script is available (OPN-02) | It is read before the contour work package is planned, as RSK-06 intends. The specified pipeline remains the fallback | §10 OPN-02, in the Phase 2 plan's commit |
| B7 | FR-20 moves to Phase 3. The optional Gmsh mesher adapter of ADR-002 is delivered in Phase 2 | Phase 2 stays on the geometry chain. The Gmsh backend is optional and never imported on the default path (CON-10) | §8.1 NOTE, in the Phase 2 plan's commit |
| B8 | The desktop bundle carries the optional Gmsh backend (while planning WP24) | `numerics.mesh.backend: gmsh` runs in the bundle; netgen stays the default, so CON-10 holds. The bundle is already GPL-2+ under CON-11, so Gmsh's licence adds no obligation; the packaging probe imports and exercises it and the licence notice names it | The ADR-004 packaging NOTE and VER-55, with the WP24 code |
| B9 | The shell's contour editor may start from a loop stage 4's gate refused (while planning WP24) | A refused gate writes no artefact (QR-12), so otherwise there is nothing to override. The loop is recomputed from the stored stage-3 map by stage 4's own conditioning; the edit is saved as a supplied profile with `provenance.source: hand-edit`, gated as §5.2.1's NOTE on a supplied fixture states, and stages 5 and 6 apply their gates unchanged. The §5.2.1 criteria are measured and shown, not enforced | The §5.3.1 NOTE on `geometry.contour`, in the WP24 plan's commit |
| B10 | The stage-2 density map is exported in ångströms (while planning WP25) | CCP4/MRC defines the cell in ångströms, and viewers read OpenDX in ångströms, so the map overlays the aligned structure's PDB export, which is in ångströms by its format. Inside the package, and in the native `.npz`, lengths stay in nm. The `field1` grids stay in nm, as their header declares | The IF-05 NOTE on length units and VER-49, in the WP25 plan's commit. `DensityMap.export` and `read` change with the WP25 code |

