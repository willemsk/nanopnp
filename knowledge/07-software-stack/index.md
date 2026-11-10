# Software stack — libraries, versions, licences, gotchas

* [Software stack — libraries, versions, licences, gotchas (overview)](00-overview.md) - The libraries, versions, licences and gotchas of the software stack.
* [1. FEM backend — NGSolve/Netgen](01-fem-backend-ngsolvenetgen.md) - The FEM backend NGSolve and Netgen: what the wheels hold and lack, and prior art; the alternatives are ADR-001's.
* [2. Structure, trajectory and density](02-structure-trajectory-and-density.md) - The structure, trajectory and density libraries and how they behave.
* [3. Charge and electrostatics](03-charge-and-electrostatics.md) - The charge and electrostatics tools PDB2PQR, PROPKA and APBS, as the pipeline drives them.
* [4. Geometry, meshing and I/O](04-geometry-meshing-and-io.md) - The geometry, meshing and I/O libraries.
* [5. GUI and packaging](05-gui-and-packaging.md) - The GUI and packaging stack: NiceGUI with Mol*, the Qt shell, the web viewer and PyInstaller.
* [6. Licence summary](06-licence-summary.md) - The licences of the dependencies.
* [7. Local assets](07-local-assets.md) - The external sources the knowledge base cites, and where each lives.
* [8. Python 3.11 floor and the 3.14 development interpreter](08-python-version-floor-the-310-target-is.md) - Why the floor is 3.11, and what the 3.14 development interpreter changes.
* [9. The CLI's import budget, measured](09-the-clis-import-budget-measured.md) - The import costs of the command line, the case schema and the view-models, and what keeps NGSolve and NumPy out of them.
* [10. `canonical()` is the on-disk format, not only the hash input](10-canonical-is-the-on-disk-format-not.md) - canonical() is the on-disk format, not only the hash input.
* [11. A stage never picks its own workspace](11-a-stages-workspace-falls-back-to-the.md) - A stage built without a workspace is refused; the run driver makes a fresh scratch under the store in use.
* [12. The suite's BLAS threads buy nothing; parallelism has to come from workers](12-the-suites-blas-threads-buy-nothing.md) - The suite's BLAS threads buy nothing; parallelism has to come from workers.
* [13. Documentation tooling: MkDocs, Material and Zensical](13-documentation-tooling-mkdocs-material.md) - Documentation tooling: MkDocs, Material and Zensical.
* [14. A Windows checkout rewrites the bytes a hash identifies](14-a-windows-checkout-rewrites-the-bytes-a.md) - A Windows checkout rewrites the bytes a hash identifies.
* [15. An `.npz` is reproducible bytes only if nothing in it moves with the clock](15-an-npz-is-reproducible-bytes-only-if.md) - An .npz is reproducible bytes only if nothing in it moves with the clock.
* [16. NGSolve's bundled stubs cannot type-check, so the aliases in `core/typing.py` are `Any`](16-ngsolves-bundled-stubs-cannot-type.md) - NGSolve's bundled stubs cannot type-check, so the aliases in core/typing.py are Any.
* [Tier-1 test evidence: the viewer and the positivity gate](17-tier-1-test-evidence-the-viewer-and-the.md) - What the Tier-1 tests of the viewer and the positivity gate establish.
* [Tier-1 test evidence: the mesh seam and the layering ratchet](18-tier-1-test-evidence-the-mesh-seam-and.md) - What the Tier-1 tests of the mesh seam and the layering ratchet establish.
* [Tier-1 test evidence: stores, paths, OCC names, NaN and reduction tolerances](19-tier-1-test-evidence-stores-paths-occ.md) - What the Tier-1 tests of stores, paths, OCC names, NaN and reduction tolerances establish.
* [Tier-1 test evidence: import costs, trajectory precision and the gate's pipefail trap](20-tier-1-test-evidence-import-costs.md) - What the Tier-1 tests of import costs, trajectory precision and the gate's pipefail trap establish.
* [Tier-2 test evidence: budgets, timings and reference checks](21-tier-2-test-evidence-budgets-timings.md) - What the Tier-2 tests of budgets, timings and reference checks establish.
* [Tier-2 test evidence: analytic benchmarks and reference checks](22-tier-2-test-evidence-analytic.md) - What the Tier-2 tests of analytic benchmarks and reference checks establish.
* [23. Pinning a protonation state through PDB2PQR's apply_pka_values (WP5.04)](23-pinning-a-protonation-state-through-apply-pka-values.md) - How to hold a residue in a chosen protonation state during PDB2PQR 3.8's call, why renaming the input cannot do it, and what the pin moves besides the residue.
* [24. pint with a Fraction registry converts exactly, and formats nothing (WP5.07)](24-pint-with-a-fraction-registry-exact-units.md) - Why the case's units go through pint with Fraction magnitudes, what that registry converts exactly, which version the Python 3.11 floor allows, and the calls that raise.
* [25. xenon and import-linter beside ruff's C901 and VER-61 (WP5.10)](25-complexity-and-import-contract-tools.md) - What xenon and import-linter report on nanopnp, what each adds over ruff's complexity rules and the layering test, and why neither is adopted.
