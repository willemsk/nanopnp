# Software stack — libraries, versions, licences, gotchas

* [Software stack — libraries, versions, licences, gotchas (overview)](00-overview.md) - The libraries, versions, licences and gotchas of the software stack.
* [1. FEM backend — NGSolve/Netgen](01-fem-backend-ngsolvenetgen.md) - The FEM backend NGSolve and Netgen: why not the alternatives, and prior art.
* [2. Structure, trajectory and density](02-structure-trajectory-and-density.md) - The structure, trajectory and density libraries and how they behave.
* [3. Charge and electrostatics](03-charge-and-electrostatics.md) - The charge and electrostatics tools PDB2PQR, PROPKA and APBS, as the pipeline drives them.
* [4. Geometry, meshing and I/O](04-geometry-meshing-and-io.md) - The geometry, meshing and I/O libraries.
* [5. GUI and packaging](05-gui-and-packaging.md) - The GUI and packaging stack: PySide6, the web viewer and PyInstaller.
* [6. Licence summary](06-licence-summary.md) - The licences of the dependencies.
* [7. Local assets](07-local-assets.md) - The local assets the project keeps.
* [8. Python version floor — the 3.10 target is not free](08-python-version-floor-the-310-target-is.md) - The Python version floor, and what a 3.10 target would cost.
* [9. The CLI's import budget, measured](09-the-clis-import-budget-measured.md) - The command line's import budget, measured.
* [10. `canonical()` is the on-disk format, not only the hash input](10-canonical-is-the-on-disk-format-not.md) - canonical() is the on-disk format, not only the hash input.
* [11. A stage's workspace falls back to the process store root, not the run's store](11-a-stages-workspace-falls-back-to-the.md) - A stage's workspace falls back to the process store root, not the run's store.
* [12. The suite's BLAS threads buy nothing; parallelism has to come from workers](12-the-suites-blas-threads-buy-nothing.md) - The suite's BLAS threads buy nothing; parallelism has to come from workers.
* [13. Documentation tooling: MkDocs, Material and Zensical](13-documentation-tooling-mkdocs-material.md) - Documentation tooling: MkDocs, Material and Zensical.
* [14. A Windows checkout rewrites the bytes a hash identifies](14-a-windows-checkout-rewrites-the-bytes-a.md) - A Windows checkout rewrites the bytes a hash identifies.
* [15. An `.npz` is reproducible bytes only if nothing in it moves with the clock](15-an-npz-is-reproducible-bytes-only-if.md) - An .npz is reproducible bytes only if nothing in it moves with the clock.
* [16. NGSolve's bundled stubs cannot type-check, so the aliases in `core/typing.py` are `Any`](16-ngsolves-bundled-stubs-cannot-type.md) - NGSolve's bundled stubs cannot type-check, so the aliases in core/typing.py are Any.
* [Tier-1 test evidence: the viewer and the positivity gate (WP45 item 21)](17-tier-1-test-evidence-the-viewer-and-the.md) - What the Tier-1 tests of the viewer and the positivity gate establish, recorded at WP45 item 21.
* [Tier-1 test evidence: the mesh seam and the layering ratchet (WP45 item 22)](18-tier-1-test-evidence-the-mesh-seam-and.md) - What the Tier-1 tests of the mesh seam and the layering ratchet establish, recorded at WP45 item 22.
* [Tier-1 test evidence: stores, paths, OCC names, NaN and reduction tolerances (WP45 item 23)](19-tier-1-test-evidence-stores-paths-occ.md) - What the Tier-1 tests of stores, paths, OCC names, NaN and reduction tolerances establish, recorded at WP45 item 23.
* [Tier-1 test evidence: import costs, trajectory precision and the gate's pipefail trap (WP45 item 24)](20-tier-1-test-evidence-import-costs.md) - What the Tier-1 tests of import costs, trajectory precision and the gate's pipefail trap establish, recorded at WP45 item 24.
* [Tier-2 test evidence: budgets, timings and reference checks (WP45 item 25)](21-tier-2-test-evidence-budgets-timings.md) - What the Tier-2 tests of budgets, timings and reference checks establish, recorded at WP45 item 25.
* [Tier-2 test evidence: analytic benchmarks and reference checks (WP45 item 26)](22-tier-2-test-evidence-analytic.md) - What the Tier-2 tests of analytic benchmarks and reference checks establish, recorded at WP45 item 26.
