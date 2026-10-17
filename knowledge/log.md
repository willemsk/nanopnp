# Log

Entries are the dated events the notes record, newest first; git holds every earlier edit.

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
