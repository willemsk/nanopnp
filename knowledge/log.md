# Log

Entries are the dated events the notes record, newest first; git holds every earlier edit.

## 2026-11-10
* **Update**: The background notes state the current: the current is the boundary flux by the two routes of FR-23, never the cross-section integral; "Quantities the thesis computes" cites FR-23 and PHY-21; the Einstein drift points to its tested home; the relaxation time keeps all three terms; the electro-osmotic divergence belongs to the thin-EDL form; the λ_D table names its permittivity (WP5.12; §8.2.36 AL17). ([9. Quantities the thesis computes](02-electrokinetics-background/09-quantities-the-software-must-compute.md), [1. The electrical double layer](02-electrokinetics-background/01-the-electrical-double-layer.md))
* **Update**: ClyA carries −60 e and the validated ClyA-AS model −72 e, two constructs (ruling 8); the 27-mutation list covers five of the eight AS mutations and repeats ClyA-RR₅₆K's Q8K, which is open (OPN-04); the two glossaries hold one definition each (WP5.12). ([3. ClyA in depth](03-nanopore-biology/03-clya-in-depth-the-reference-system.md), [Still open](00-orientation/06-still-open.md))
* **Update**: The provenance note states AL17's rule, a rule's home its clause and a measurement's its concept, and the knowledge index says when to read each directory (WP5.12; §8.2.36 AL17). ([Provenance and how to extend this](00-orientation/04-provenance-and-how-to-extend-this.md))
* **Update**: The software-stack concepts state the current rules: a stage never picks its own workspace, the floor is Python 3.11, the GUI table names NiceGUI, FastAPI, uvicorn and Mol*, the licence summary is a table read from the installed metadata, the local assets are the external sources, and the superseded GL shim, the 3.10 analysis, four suite-time tables and the removed coverage and recorder machinery leave; versions point to `uv.lock` (WP5.12). ([7. Local assets](07-software-stack/07-local-assets.md), [6. Licence summary](07-software-stack/06-licence-summary.md), [12. The suite's BLAS threads](07-software-stack/12-the-suites-blas-threads-buy-nothing.md))
* **Record**: The import costs of the case schema and the view-models move from the GUI note to the CLI's import budget (WP5.12). ([9. The CLI's import budget](07-software-stack/09-the-clis-import-budget-measured.md))
* **Update**: The benchmark ladder points to §7's rows and keeps what the specification lacks; §2.8 states VER-19's exact far field and VER-21's Henry reference; the COMSOL oracle is optional (RSK-14); the model-report reconciliation keeps the permittivity arithmetic, and the like-for-like table says what nanopnp does for each setting (WP5.12; §8.2.36 AL17). ([Tier 2 — Analytic benchmarks](08-validation-benchmarks/02-tier-2-analytic-benchmarks-minutes.md), [D. Reconciliations with the model report](09-comsol-reference-settings/05-contradictions-with-the-rest-of-this.md))
* **Update**: The ClyA-AS concepts state the rulings as current: the 0.15 M radial-potential row is no regression target (ruling 7), pore averages carry the `2πr` Jacobian (ruling 6), nanopnp does not build the reference's field-point charge, the net-charge target is `Q_net` to 10⁻³, closed gaps are one line each, and 2WCD against the reference polygon is stated at the corrected `Z_MD` = 5.655 nm with 5.63 nm as one sensitivity line (WP5.12; §8.2.36 AL15, AL17). ([1. Geometry pipeline](04-clya-geometry-and-charge/01-geometry-pipeline-as-executed.md), [8. Gaps and ambiguities](04-clya-geometry-and-charge/08-gaps-and-ambiguities-questions-for-the.md))
* **Update**: The delivered polygon's measurements point to `data/geometry/README.md` and the §5.2.1 NOTE, and §5.2's radius-band NOTE points to the measured margins (WP5.12; §8.2.36 AL17). ([4. Mesh](04-clya-geometry-and-charge/04-mesh.md), [1. Geometry pipeline](04-clya-geometry-and-charge/01-geometry-pipeline-as-executed.md))
* **Update**: The analyte concepts state rulings 4, 5 and 9 as current, and the PlyAB note is retitled for what it holds; the pore's charge pipeline and the pore's EOF and pressure targets become pointers to the ClyA-AS concepts (WP5.12; §8.2.36 AL15, AL17). ([10. The continuum force computation](05-analyte-and-forces/11-correction-continuum-force-computation.md), [2. Charge representation](05-analyte-and-forces/03-charge-representation-both-forms-and.md))
* **Record**: The drag, Maxwell and Henry measurements of VER-19 to VER-21 move, with their markers, from the analyte gaps to the Tier-2 test evidence (WP5.12). ([Tier-2 test evidence: electro-osmosis, electrophoresis and the force routes](05-analyte-and-forces/13-tier-2-test-evidence-electro-osmosis.md))

## 2026-11-09
* **Update**: The numerics concepts point to §6 for the formulation table, the weak forms, the scales, the stabilisation policy, the Newton settings, the ladder, the fallbacks, the solver choice and the current's indicator form, and keep what building them measured; the NGSolve-traps note is retitled for what it holds and its sections run in reading order (WP5.12; §8.2.36 AL17). ([Numerics overview](06-numerics-fem/00-overview.md), [NGSolve traps and measured numerics facts](06-numerics-fem/09-ngsolve-traps-found-by-implementing.md))
* **Update**: The ePNP-NS concepts back §4, which governs; their copies of §4's symbols, equations and correction forms become pointers, the reference's charge construction is labelled as the one nanopnp does not reproduce, and the errata are numbered as §4.6's six rows, E5 added (WP5.12; §8.2.36 AL15 to AL17). ([ePNP-NS — the physics behind §4](01-physics-epnpns/00-overview.md), [8. Errata in the source](01-physics-epnpns/08-errata-in-the-source-with-the-arithmetic.md))
* **Record**: The sodium diffusivity cap at 5.3 M is 8.113 × 10⁻¹⁰ m² s⁻¹ from the governing coefficients; the thesis's rounded ones give 8.127 × 10⁻¹⁰ (WP5.12; §8.2.37 AM13). ([8. Errata in the source](01-physics-epnpns/08-errata-in-the-source-with-the-arithmetic.md))
* **Update**: The limiting-current benchmark's two lessons move from the physics notes to the benchmark ladder's §2.5; the Langevin cutoff's evidence becomes a pointer to the physics note (WP5.12). ([Tier 2 — Analytic benchmarks](08-validation-benchmarks/02-tier-2-analytic-benchmarks-minutes.md), [Tier-1 test evidence: the Langevin cutoff](06-numerics-fem/12-tier-1-test-evidence-the-langevin.md))
* **Record**: VAL-06's budget split, agreement margins, charge-zeroing check and ring results move here from §7.4's NOTE (WP5.11). ([3. Charge and electrostatics](07-software-stack/03-charge-and-electrostatics.md))
* **Record**: The ion-exclusion shell's resampling bound, the division of its `wall` edges and the two alternatives set aside move here from §5.2 (WP5.11). ([2. Model geometry and conventions](04-clya-geometry-and-charge/02-model-geometry-and-conventions.md))
* **Record**: The Einstein-ratio range is per ion, 1.21–1.67 × kT/e for Na⁺ and 1.13–1.28 for Cl⁻, so the stabilisation's Péclet factor is 0.60–0.88 (WP5.11). ([4. Stabilisation](06-numerics-fem/04-stabilisation.md))
* **Record**: xenon and import-linter trialled on the tree: import-linter's layers contract repeats VER-61 with less, xenon's radon measure disagrees with ruff's `C901` on 15 of 22 functions; neither is recommended (WP5.10). ([25. xenon and import-linter](07-software-stack/25-complexity-and-import-contract-tools.md))

## 2026-11-05
* **Record**: A workbench shortcut is matched in the page and the command runs on the server; Quasar paints its panels, cards and menus white whatever the theme (WP5.08). ([5. GUI and packaging](07-software-stack/05-gui-and-packaging.md))

## 2026-11-04
* **Record**: pint with a `Fraction` registry converts units exactly; 0.25.3 is the newest release that supports Python 3.11 (WP5.07). ([24. pint with a Fraction registry](07-software-stack/24-pint-with-a-fraction-registry-exact-units.md))

## 2026-11-03
* **Record**: Pinning a protonation state by holding a residue's key out of `apply_pka_values` and applying the patch, and the neighbour a pin can move (WP5.04). ([23. Pinning a protonation state](07-software-stack/23-pinning-a-protonation-state-through-apply-pka-values.md))
* **Update**: PDB2PQR's CHARMM residue and hydrogen names: a protonated GLU or ASP keeps its parent name, so the radius comes from the state patch, not the residue name (WP5.03). ([PDB2PQR's residue and hydrogen names, and the protonated density](04-clya-geometry-and-charge/14-pdb2pqrs-residue-and-hydrogen-names-and-the-protonated-density.md))
* **Update**: PDB2PQR 3.8.0 writes terminal patches as `NTER` and `CTER`, has no `docutils` pin and keeps `CHARMM.DAT` unchanged; the `structure` extra takes 3.8 (REV-175). ([3. Charge and electrostatics](07-software-stack/03-charge-and-electrostatics.md))

## 2026-11-02
* **Update**: What the framework spike taught about NiceGUI with Mol*: the ready flag, the long timeout, and no camera move under software GL (WP5.02). ([5. GUI and packaging](07-software-stack/05-gui-and-packaging.md))

## 2026-11-01
* **Update**: A non-finite Newton trial residual aborts at minimum damping and cuts the damping above it; it is no longer a forced step (WP59 D5). ([Tier-1 test evidence: Newton's counterexamples](06-numerics-fem/14-tier-1-test-evidence-newtons.md))

## 2026-10-30
* **Update**: The no-MPI claim is narrowed to the lock file and the build configuration, and the rectification sentence no longer asserts that a fixed-charge asymmetry alone rectifies (WP57; REV-111, REV-155). ([1. FEM backend](07-software-stack/01-fem-backend-ngsolvenetgen.md), [7. Ionic current rectification](02-electrokinetics-background/07-ionic-current-rectification.md))
* **Update**: The notes on the import cost and on the stage workspace name the Python interface, `Case` and `Session`, in place of `load_case`, `resolve` and `run_case` (WP57). ([5. GUI and packaging](07-software-stack/05-gui-and-packaging.md), [A stage's workspace](07-software-stack/11-a-stages-workspace-falls-back-to-the.md))

## 2026-10-29
* **Update**: Rectification needs an axial asymmetry of the geometry or of the fixed charge, not of the geometry alone (WP55's physics review of the sweep session). ([7. Ionic current rectification](02-electrokinetics-background/07-ionic-current-rectification.md))

## 2026-10-24
* **Update**: Added the offscreen Qt and headless Playwright section to 07-software-stack/05 and marked the libEGL shim as superseded (WP5.01). ([5. GUI and packaging](07-software-stack/05-gui-and-packaging.md))

## 2026-10-21
* **Add**: A glossary of the project's shorthands: specification identifier prefixes, the NUM-18 ladder and its rungs, review registers and the pipeline terms. ([Glossary of project terminology and shorthands](00-orientation/07-glossary.md))

## 2026-10-19
* **Update**: Marked the advice to mollify the wall-distance field and the advice to apply field-wise row scaling as superseded by the CODE_REVIEW_010 rulings (PHY-02, NUM-31, NUM-10). ([1. Symbols](01-physics-epnpns/01-symbols.md), [7. Implementation notes carried forward](01-physics-epnpns/07-implementation-notes-carried-forward.md), [3. Nondimensionalisation](06-numerics-fem/03-nondimensionalisation.md))
* **Update**: Stated that the validated wall-distance field is the unsmoothed C⁰ field and that C¹ mollification is a deviation, off by default (author ruling, CODE_REVIEW_010). ([8. Mesh resolution and adaptivity](06-numerics-fem/08-mesh-resolution-and-adaptivity.md))
* **Update**: Retargeted the `[tested: …]` markers that named a test deleted by the test scope (WP50, §8.2.13 N3): 31 markers became `[verified]` on their source footnote, or were dropped where the concept has none, and `pending.yaml` was removed.
* **Update**: Removed the empty `****` markers that retargeting left in nine concepts, the empty `verified:` key of concept 13, and the present-tense statements about `--extended`, `no_cover` and `test_plan_shape.py` that WP50 made false (WP50 review).

## 2026-10-18
* **Update**: Stated that `ngsolve/__init__.pyi` ships only in the Linux wheel, so the stub test checks it where present. ([16. NGSolve's bundled stubs cannot type](07-software-stack/16-ngsolves-bundled-stubs-cannot-type.md))
* **Update**: Repointed the six source citations that named plan files which do not exist (`wp18`, `wp20`, `wp21`, `wp28`, `wp30`, `wp32`) at the plans that do, and re-wired the claims for the 1 M NaCl conductivity, the zero-bias route check, the telescoping round-off statistics, the trailing-NUL behaviour and the fluid-only indicator to tests that assert them (WP48 review).
* **Update**: Corrected the integration-order example to the tested fourth-degree polynomial and synchronised the specification's maintenance text with the closed, zero-pending ledger (WP48 review).
* **Update**: Linked executable force-scale arithmetic to its existing assertions, recorded the exercised gemmi version, and restricted the FEM wheel table to its checked lockfile range (WP48 review).
* **Update**: Repaired historical plan addresses and viewer attribution, pinned hashing, singular-system and sweep measurements to their immutable records, and separated historical magnitudes from current reproductions (WP48 review).

## 2026-10-16
* **Update**: Backed all 63 remaining domain claims across the bundle with Tier-1 and Tier-2 test evidence and immutable plan records, reducing total pending claims across the knowledge bundle to zero and lowering the ceiling to 0 (WP48 item 8).
* **Update**: Backed all 51 pending NGSolve-trap `Library Behaviour` claims in `06-numerics-fem/09-ngsolve-traps-found-by-implementing.md` with Tier-1 and Tier-2 test evidence (`tests/tier1/test_ngsolve_traps.py` and existing suites) and historical commit footnotes, lowering the pending ceiling from 114 to 63 (WP48 item 7).
* **Update**: Backed all 90 pending software-stack `Library Behaviour` claims across `07-software-stack/01..16` with Tier-1 and Tier-2 test evidence (`tests/tier1/test_library_behaviour.py` and existing suites), lowering the pending ceiling from 204 to 114 (WP48 item 6).
* **Update**: Recorded `tested_with` package-version mappings across all seventeen `Library Behaviour` concepts and enforced non-empty `tested_with` mappings in VER-68 (WP48 item 5).
* **Update**: Replaced every executable `[verified]` arithmetic and closed-form claim across the bundle with Tier-1 test evidence (`tests/tier1/test_knowledge_arithmetic.py` and existing Tier-1 suites), reducing `verified_unsourced` to zero (WP48 item 4).
* **Update**: Backed all 100 pending Test Evidence claims across the seventeen Test Evidence concepts with explicit test assertions or immutable historical records (WP48 item 3).
* **Update**: Linked source footnotes and immutable plan records to report readings, topological/calculus identities and standalone archive observations across the bundle, including the ten unsourced COMSOL reference-settings claims (WP48 item 2).

## 2026-10-14
* **Update**: The folder lost its leading dot and is now `knowledge/`; every citation follows.
* **Update**: The notes became a bundle of concepts, one idea each, with a header, a ledger of test-backed claims and this log (WP47).
* **Update**: Recorded how the documentation build treats the bundle ([13. Documentation tooling: MkDocs, Material and Zensical](07-software-stack/13-documentation-tooling-mkdocs-material.md)).

## 2026-10-12
* **Record**: The Python version floor, and what a 3.10 target would cost. ([8. Python version floor — the 3.10 target is not free](07-software-stack/08-python-version-floor-the-310-target-is.md))
* **Record**: The suite's BLAS threads buy nothing; parallelism has to come from workers. ([12. The suite's BLAS threads buy nothing; parallelism has to come from workers](07-software-stack/12-the-suites-blas-threads-buy-nothing.md))
* **Record**: The sub-agent frontmatter keys that code.claude.com documented on 12 October 2026 are the set that tests/tier1/test_plan_shape.py checks ([Tier-1 test evidence: stores, paths, OCC names, NaN and reduction tolerances (WP45 item 23)](07-software-stack/19-tier-1-test-evidence-stores-paths-occ.md))

## 2026-10-06
* **Record**: After import nanopnp.io.case the only nanopnp subpackages in sys.modules are core and io , 6 October 2026 ([5. GUI and packaging](07-software-stack/05-gui-and-packaging.md))

## 2026-10-05
* **Record**: Within one `<platform>-<machine>` key, NumPy's SIMD dispatch moves a PDB-derived mesh (WP35 review, 5 October 2026) ([8.1 NGSolve traps found by implementing this — all silent](06-numerics-fem/09-ngsolve-traps-found-by-implementing.md))

## 2026-10-04
* **Record**: The axisymmetric weak forms, the axis and the quadrature order that avoids NaN (WP34). ([2. Axisymmetric weak forms](06-numerics-fem/02-axisymmetric-weak-forms.md))

## 2026-10-03
* **Record**: The suite's BLAS threads buy nothing; parallelism has to come from workers. ([12. The suite's BLAS threads buy nothing; parallelism has to come from workers](07-software-stack/12-the-suites-blas-threads-buy-nothing.md))

## 2026-10-02
* **Record**: Netgen keeps every ring vertex and rounds each edge's segment count, so a shell's wall fails the gate in bands of wall target (WP30 review, 2 October 2026, netgen 6.2.2606) ([8.1 NGSolve traps found by implementing this — all silent](06-numerics-fem/09-ngsolve-traps-found-by-implementing.md))
* **Record**: Read from the shipped webgui.js and from the scenes the render child writes, 2 October 2026 (WP31 D8) ([5. GUI and packaging](07-software-stack/05-gui-and-packaging.md))

## 2026-10-01
* **Record**: The fixed-charge pipeline: the delivered table, the 1.25 % aliasing and the closed-form kernel. ([3. Fixed-charge pipeline](04-clya-geometry-and-charge/03-fixed-charge-pipeline.md))
* **Record**: PDB2PQR 3.7.1 and PROPKA 3.5.1 as a per-frame driver , 1 October 2026 ([3. Charge and electrostatics](07-software-stack/03-charge-and-electrostatics.md))

## 2026-09-30
* **Record**: The geometry pipeline as executed, with measurements on the MD archive, the contour script and 2WCD. ([1. Geometry pipeline, as executed](04-clya-geometry-and-charge/01-geometry-pipeline-as-executed.md))
* **Record**: The axisymmetric weak forms, the axis and the quadrature order that avoids NaN (WP26 implementation session). ([2. Axisymmetric weak forms](06-numerics-fem/02-axisymmetric-weak-forms.md))
* **Record**: Stabilisation: the mode as built and what each term does (test-suite timing work). ([4. Stabilisation](06-numerics-fem/04-stabilisation.md))
* **Record**: Package facts, read from PyPI's metadata on 30 September 2026 : pdb2pqr 3.7.1 is BSD-3, a pure-Python wheel, and requires Python ≥ 3.11, < 4 ([3. Charge and electrostatics](07-software-stack/03-charge-and-electrostatics.md))
* **Record**: Re-measured on 30 September 2026, four cores, 1504 tests in the default selection (tiers 1 and 2, not slow, the GUI file apart) ([12. The suite's BLAS threads buy nothing; parallelism has to come from workers](07-software-stack/12-the-suites-blas-threads-buy-nothing.md))

## 2026-09-29
* **Record**: The geometry pipeline as executed, with measurements on the MD archive, the contour script and 2WCD. ([1. Geometry pipeline, as executed](04-clya-geometry-and-charge/01-geometry-pipeline-as-executed.md))
* **Record**: DensityMap.read exported .map and failed to read it back until WP25 did so , 29 September 2026 ([2. Structure, trajectory and density](07-software-stack/02-structure-trajectory-and-density.md))
* **Record**: Gmsh facts, measured on 4.15.2 with netgen 6.2.2606, Linux (WSL2), 29 September 2026 (WP23; the implementation is mesh/gmsh_backend.py, the evidence the WP23 plan's Design and Outcomes) ([4. Geometry, meshing and I/O](07-software-stack/04-geometry-meshing-and-io.md))
* **Record**: Measured 29 September 2026 on a Linux rebuild of the probe recipe in this container (WP24 D16, D17): PyInstaller 6.22.3, MDAnalysis 2.10.0, gemmi 0.7.5, scikit-image 0.26.0, Shapely 2.1.2 with GEOS 3. ... ([5. GUI and packaging](07-software-stack/05-gui-and-packaging.md))

## 2026-09-28
* **Record**: Answered by the author, 28 September 2026: it was. The delivered 185-vertex polygon was made with pqr2grid's radial binning at L = 15 nm (h = 0.05 nm), so w/h = 31/30.05 = 1.03161 and r_a = 0.96935 r ... ([1. Geometry pipeline, as executed](04-clya-geometry-and-charge/01-geometry-pipeline-as-executed.md))
* **Record**: Measured on 2WCD, 28 September 2026 (§1.4): ±0.1 of isolevel moves the bulk-resistor conductance by about ±5 % ([8. Gaps and ambiguities (questions for the author)](04-clya-geometry-and-charge/08-gaps-and-ambiguities-questions-for-the.md))
* **Record**: NGSolve traps found by implementing the model, all of them silent (codebase review of 28 September 2026, CR-2). ([8.1 NGSolve traps found by implementing this — all silent](06-numerics-fem/09-ngsolve-traps-found-by-implementing.md))
* **Record**: The GUI and packaging stack: PySide6, the web viewer and PyInstaller (codebase review of 28 September 2026). ([5. GUI and packaging](07-software-stack/05-gui-and-packaging.md))
* **Record**: The tolerance is therefore taken relative to max(1, E_k) (codebase review of 2026-09-28, CR-7) ([Tier 3 — COMSOL differential tests (hours, nightly)](08-validation-benchmarks/03-tier-3-comsol-differential-tests-hours.md))

## 2026-09-26
* **Record**: Read on 26 September 2026 (SPECIFICATION.md OPN-02, closed) ([1. Geometry pipeline, as executed](04-clya-geometry-and-charge/01-geometry-pipeline-as-executed.md))
* **Record**: Stage 6 (WP21) measures the wall segment lengths over the resolved target, at the §5.2.2 sizes otherwise; netgen 6.2.2606, Linux, 26 September 2026 ([8. Mesh resolution and adaptivity](06-numerics-fem/08-mesh-resolution-and-adaptivity.md))
* **Record**: Measured with scikit-image 0.26.0 on 26 September 2026 ([4. Geometry, meshing and I/O](07-software-stack/04-geometry-meshing-and-io.md))
* **Record**: Read, 26 September 2026: create_polygon_contour in the author's pqr2grid (~/repos/pqr2grid, MIT, 2019) ([7. Local assets](07-software-stack/07-local-assets.md))

## 2026-09-25
* **Record**: The author ruled on 25 September 2026 that R_i is the CHARMM Rmin/2 of PDB2PQR's CHARMM.DAT, the set carried by the reference ensemble's per-frame PQR files (§1.1) ([1. Geometry pipeline, as executed](04-clya-geometry-and-charge/01-geometry-pipeline-as-executed.md))
* **Record**: The structure, trajectory and density libraries and how they behave. ([2. Structure, trajectory and density](07-software-stack/02-structure-trajectory-and-density.md))
* **Record**: That copyleft is file-level, so it is fine used unmodified as a separate package (CON-09, amended 25 September 2026) ([6. Licence summary](07-software-stack/06-licence-summary.md))

## 2026-09-24
* **Record**: Resolved, 24 September 2026 : the floor is now 3.11 (§8.2.2 B4, WP17) ([8. Python version floor — the 3.10 target is not free](07-software-stack/08-python-version-floor-the-310-target-is.md))

## 2026-09-23
* **Record**: Found by WP16 (23 September 2026) when a CLI test asserted that a refused nanopnp mesh wrote nothing to stdout; every nanopnp run on an MSH case had been writing the same stray line, which a caller pa ... ([4. Geometry, meshing and I/O](07-software-stack/04-geometry-meshing-and-io.md))
* **Record**: Read 23 September 2026 from the publishers' own announcements ([13. Documentation tooling: MkDocs, Material and Zensical](07-software-stack/13-documentation-tooling-mkdocs-material.md))

## 2026-09-22
* **Record**: The GUI and packaging stack: PySide6, the web viewer and PyInstaller. ([5. GUI and packaging](07-software-stack/05-gui-and-packaging.md))

## 2026-09-21
* **Record**: Measured 21 September 2026 on the default ladder of an epnp-ns case at 0.1 M and 20 mV, twelve rungs on a cheap cylindrical pore ([5. Nonlinear solution](06-numerics-fem/05-nonlinear-solution.md))
* **Record**: Measured 21 September 2026, P2 GridFunction on a unit-square mesh, Draw(gf, mesh, order=k, show=False).GetData() then json.dumps ([5. GUI and packaging](07-software-stack/05-gui-and-packaging.md))

## 2026-09-20
* **Record**: Chosen for the bundle, one-dir (ADR-004, amended 20 September 2026) ([5. GUI and packaging](07-software-stack/05-gui-and-packaging.md))

## 2026-09-06
* **Record**: Measured directly (6 September 2026; too large to vendor, so it is named by $NANOPNP_REFERENCE_DATA and Tier 3 skips without it) ([3. Fixed-charge pipeline](04-clya-geometry-and-charge/03-fixed-charge-pipeline.md))

## 2026-09-02
* **Record**: The licences of the dependencies. ([6. Licence summary](07-software-stack/06-licence-summary.md))
