---
type: Specification
title: "Appendix A. Requirements traceability matrix"
description: "Maps each requirement of §3 to the activity of §7 that demonstrates it, marking those with none yet specified."
---

## Appendix A. Requirements traceability matrix

Each requirement of §3 is mapped to the activity of §7 that demonstrates it. "None yet" records
that no verification or validation activity has been specified; it is not a statement that none is
needed.

| Requirement | Verification or validation activity |
|---|---|
| IF-01 | VER-25, VER-32, VER-45 (the public surface, the modules its mirror imports from, and its import cost) |
| IF-02 | VER-32, VER-38, VER-45 (the generated command-line and exit-code references), VER-46 (every documented command executed) |
| IF-03 | VER-09, VER-36 (dotted-path substitution against the schema), VER-47 (case schema v0.5), VER-71 (the v0.5 refusals of a value never applied), VER-57 (`inputs.pqr` read, registered and refused; the protonation keys' refusals); the registry and inf-sup refusals made at load (`tests/tier1/test_case_schema.py`); that `nanopnp validate case` and the shell's commit give them in a run's text is verified at review (§8.2.13 N3) |
| IF-04 | VER-48 (PDB, mmCIF and each trajectory format read; PDB and mmCIF of one entry agree), VER-32 (the aligned ensemble exported as a PDB and a DCD) |
| IF-05 | VER-29, VER-49 (the density map in `.npz`, OpenDX and CCP4, in ångströms at the file boundary), VER-50 (the reduced map exported as radial grids), VER-32 and VER-46 (the map exported from the command line and overlaid on its structure), VAL-15 |
| IF-06 | VER-27 |
| IF-07 | VER-33 |
| IF-08 | VER-24, VER-35 |
| IF-09 | VER-43, VER-44, VER-55 (the geometry pipeline built, inspected and hand-edited from the shell), VER-60 (the charge pipeline built and inspected from the shell, every number read from its stage's artefact) |
| FR-01 | VER-48 (frame window, superposition on the earliest frame's C-alpha, Kabsch against MDAnalysis) |
| FR-02 | VER-48 (the permutation axis against a known axis, and against principal axes) |
| FR-03 | VER-48 (missing, surplus and truncated chains, residue names and the point group refused) |
| FR-04 | VER-49 (the union density, its truncation bound, the frame average and the radius set) |
| FR-05 | VER-01 (shared annular-volume integration), VER-50 (exact annular weights and the harmonic Cₙ average) |
| FR-06 | VER-50 (the Cₙ and raw variance against closed forms), VAL-05 (the largest Cₙ and non-Cₙ variance and where, recorded on both legs: `tests/tier2/test_val05_2wcd.py`, `tests/tier3/test_val05_ensemble.py`) |
| FR-07 | VER-51 (marching squares against exact and closed-form level sets, the morphology, Taubin and the conditioning), VAL-05 (the stage-4 polygon against the reference: `tests/tier1/test_val05_geometry.py`, the harness; `tests/tier2/test_val05_2wcd.py`; `tests/tier3/test_val05_ensemble.py`) |
| FR-08 | VER-51 (each §5.2.1 gate criterion fires on constructed input; the radius band against the probe profile) |
| FR-09 | VER-28, VER-52 (the membrane junction derived on any profile), VER-59 (the ion-exclusion shell assembled from the profile's offset, the membrane unchanged), VAL-05 (stage 5's model-frame polygon is the compared one: `tests/tier2/test_val05_2wcd.py`, `tests/tier3/test_val05_ensemble.py`) |
| FR-10 | VER-10, VER-53 (the size fields, the wall-size gate and the generated mesh's gates), VER-59 (the shell meshed at the wall size, through the same gates, on the parallelogram and on 2WCD), VER-54 (the same region meshed by the optional Gmsh backend through the same gates, and solved on both backends' meshes), VAL-05 (the generated mesh against §5.2.2's figures, and one frozen case's conductance on it against the fixture's, recorded: `tests/tier2/test_val05_2wcd.py`, `tests/tier3/test_val05_ensemble.py`) |
| FR-11 | None yet |
| FR-12 | VER-57 (the protonation stage: the force field's own charges, PROPKA's states, unapplied states recorded, the PQR artefact and `inputs.pqr`), VAL-06 (the protonated 2WCD's potential against APBS, and the recorded leg from its PQR: `tests/tier2/test_val06_2wcd.py`; the archived PQRs: `tests/tier3/test_val06_archive.py`), VER-46 (example 07: `Q_net` against the exported PQR, and the PQR supplied back) |
| FR-13 | VER-01, VER-02, VER-58, VAL-06 (the export lattice hat-weighted onto APBS's grid, against the deposit's potential: `tests/tier1/test_apbs_maps.py`, `tests/tier2/test_val06_ring.py`, `tests/tier2/test_val06_2wcd.py`), VER-46 (example 07: the same deposit from the exported PQR) |
| FR-14 | VER-01, VER-02, VER-29 (the deployed-mesh half), VER-58 (the deposit onto the deployed mesh), VAL-15, VER-46 (example 07: the conservation report read from the manifest, and the re-supplied lattice refused) |
| FR-15 | VER-30, VER-31, VER-59 (the shell and the derived `chi` from the one stage-4 profile, both off by default: `tests/tier1/test_exclusion_shell.py`, `tests/tier1/test_derived_dielectric.py`, `tests/tier2/test_exclusion_keys.py`, `tests/tier2/test_exclusion_stern.py`, `tests/tier2/test_exclusion_2wcd.py`, `tests/tier2/test_stern_layer.py`), VAL-06 (the assembled permittivity as APBS's staggered harmonic maps: `tests/tier1/test_apbs_maps.py`, `tests/tier2/test_val06_ring.py`, `tests/tier2/test_val06_2wcd.py`), VER-46 (example 07: both switches listed as deviations, with the `exclusion` material meshed) |
| FR-16 | VER-03 |
| FR-17 | VER-08, VER-16, VER-18 |
| FR-18 | VER-13, VAL-10 |
| FR-19 | VER-12, VER-13 |
| FR-20 | VER-56 (a model defined as one class in the test tree, registered at run time, runs from a case file through stages 10 to 12; no layer outside `physics/` names a model) |
| FR-21 | VER-20, VER-22 |
| FR-22 | VER-19, VER-21, VER-22 |
| FR-23 | VER-11, VER-38 (the two-point ratio), VAL-16 (the published currents, transport numbers, rectification and flow rate) |
| FR-24 | VER-36, VER-37, VER-38 |
| FR-25 | VER-24, VER-26 (manifest emitted per §7.6), VER-71 (no case leaf accepted and never applied) |
| FR-26 | VER-09, VER-26, VER-47 (a v1 document and its v2 rewrite are one run) |
| FR-27 | VER-23, VER-25, VER-26, VER-32, VER-34, VER-51 (the stage-4 payload is an `inputs.profile` document), VER-52, VER-53 (stages 5 and 6 keyed and walked to stage 12), VER-55 (each stage's artefact reported as it is stored, by a hook that keys nothing), VER-57 (the protonation stage cached per frame, its export read back exactly through `inputs.pqr`), VER-60 (both halves of stage 7 reported as each is stored, and a cancelled charge build writing no artefact), VER-64 (every stage keyed before it runs, the facts the walk reads and the upstream artefacts it reads declared by the stage, and a walk running its target's input closure) |
| FR-28 | None yet |
| FR-29 | None yet |
| FR-30 | `test_figure_classification_both_ways`, `test_every_figure_draws_and_displays` (examples 01 and 02 per push; 03, 06 and 07 nightly), `test_field_on_a_grid_matches_sample_at`, `test_default_import_and_walk_load_no_plotting`, `test_notebook_runs_headless` (nightly), `test_case_leaf_name_shared_by_two_fields_is_refused` (P8), `test_sweep_figure_draws_current_in_nanoamperes_and_scales` (P9), by §8.2.14 P4 |
| FR-31 | None yet; the workbench's packages after WP5.02 (`/np-plan amend 5`) |
| FR-32 | None yet; a Phase 5 library package before the workbench surfaces it (REV-136); then the workbench |
| FR-33 | None yet; the workbench's packages after WP5.02 (`/np-plan amend 5`) |
| FR-34 | None yet; the workbench's packages after WP5.02 (`/np-plan amend 5`) |
| FR-35 | None yet; the workbench's packages after WP5.02 (`/np-plan amend 5`) |
| FR-36 | None yet; the workbench's packages after WP5.02 (`/np-plan amend 5`); QR-10's observation at the close |
| FR-37 | None yet; a Phase 5 library package before the workbench surfaces it (REV-136) |
| FR-38 | None yet; the charge-level mutator, Phase 5 |
| FR-39 | None yet; a Phase 5 library package before the workbench surfaces it (REV-136); REV-139 |
| FR-40 | None yet; the composer phase |
| FR-41 | None yet; the structural-mutator phase |
| FR-42 | None yet; the sketcher phase |
| FR-43 | None yet; a later phase, its library package writing its physics first (§8.2.18 T6) |
| QR-01 | VER-12 to VER-22, in particular VER-17 and VER-18 |
| QR-02 | VAL-16, VAL-17 (gating v0.7); VAL-01, VAL-02 (kept, not required) |
| QR-03 | VER-01, VER-29, VER-58, VAL-15 |
| QR-04 | VER-11, VER-40 (the route disagreement as a resolution gate), VER-42 (the identity under a stabilisation mode) |
| QR-05 | VAL-07, VAL-08, VAL-09 |
| QR-06 | VER-39 (measured, recorded, not gated) |
| QR-07 | None yet (§8.2 criterion 3) |
| QR-08 | VER-26 for manifest sufficiency; VER-34, VER-35 for QoI reproduction; VER-53 (a regenerated mesh's content hash against the recorded one) |
| QR-09 | VER-47 (the declared interpreter range agrees with §2.5); the wheel-only install itself is exercised by the §7.6 matrix, not asserted by a test |
| QR-10 | None yet; Phase 5's gate, observed by a person (§8.2.6 F5) |
| QR-11 | VER-43, VER-44, VER-55, VER-60 |
| QR-12 | VER-10, VER-32, VER-40, VER-41, VER-48 (the stage-1 input and symmetry gates), VER-49 (the radius refusal and the density bounds gate), VER-51 (each contour gate criterion names its value, threshold and (r, z)), VER-52 (each stage-5 criterion likewise), VER-53 (the wall-size gate names the segment), VER-54 (the region graph's refusals name the edge's midpoint), VER-57 (each protonation gate names its frame), VER-59 (the shell's refusals name the z interval or the edge, and the derived `chi`'s gates name the material), VER-70 (no gate comparison passes a NaN) |
| QR-13 | VER-65 (the subpackages reaching NGSolve or Netgen equal a recorded set, in both directions). The §5.4.1 interface is absent (`MOD-10`), deferred to Phase 6 by §8.2.8 H3, which restated QR-13 as the single statement of the weak forms plus this guard |
| QR-14 | VER-03 (a correction is a data file), VER-56 (a physics model is one class), VER-66 (a backend registry is one registration) |
| QR-15 | VER-45, VER-46 — the documentation part only, delivered incrementally by the §8.1 documentation track; the JOSS submission and the DOI-archived release remain unverified until v0.7 |
| QR-16 | None yet; WP5.02 extends the render check to non-text contrast (REV-138), and each workbench package reviews its screens against it |
| CON-01 | None yet |
| CON-02 | VER-20, VER-22 |
| CON-03 | None yet |
| CON-04 | VER-50 (axisymmetric inputs read no variance, and a Cₙ turn leaves the reduction unchanged) |
| CON-05 | VAL-07 (residual discrepancy below 0.05 M) |
| CON-06 | None yet |
| CON-07 | None yet |
| CON-08 | §6.6 measurement table (§8.2 criterion 3, discharged) |
| CON-09 | VER-43 (no PyQt module is reachable from the shell's import paths); VER-44 (the shipped renderer is byte-identical to the npm tarball kept as its source, whose SHA-512 is npm's published integrity); VER-55 (nor from the geometry view-models'); VER-60 (nor from the charge view-models', which import neither PDB2PQR nor PROPKA) |
| CON-10 | VER-27 (the default ingestion path imports no Gmsh), VER-53 (nor does generating a mesh through stages 5 and 6), VER-54 (nor resolving or keying a case that names the Gmsh backend; without the extra that backend is refused naming it), VER-55 (nor do the geometry view-models; the bundle carries it as the optional backend, §8.2.2 B8) |
| CON-11 | §6.6 measurement table — measured; the conflict it exposed is resolved by CON-11 and ADR-003. VER-43 asserts that the bundle's licence notice states the resulting GPL-2+ obligation, and the probe refuses to start without it; VER-55 adds the geometry payloads, Gmsh (GPL-2+) and Shapely's GEOS (LGPL-2.1) among them, each exercised by the probe; VER-60 adds PDB2PQR (BSD-3) and PROPKA (LGPL-2.1, collected as source files), exercised by protonating a peptide at two pH values |
| CON-12 | VER-54 (the lock names none of Triangle, MeshPy, TetGen, pygmsh or pygalmesh, and the `gmsh` API is called directly) |
| CON-13 | VER-43 in part (the Windows bundle builds and launches headlessly on every push; widget construction is asserted on `windows-latest` and `macos-latest`). Linux *desktop* Qt is deliberately not asserted: the push gate installs no system packages, and PySide6 does not import on the runner image |
| CON-14 | None yet |

Coverage: 57 of the 67 requirements in §3 have a specified activity; 10 are recorded as "none yet",
predominantly interface, portability, licensing and documentation requirements whose demonstration
is by inspection rather than by test. QR-07 is counted as "none yet", its entry
naming §8.2 criterion 3 as the measurement it is still waiting for rather than as one it has. VER-61 and VER-62 verify Phase 4's gate (§8.1; §8.2.7 G1 and G10), VER-72 the import guard, rather than a requirement
of §3, so they leave the count unchanged. VER-76 checks the published case schema against the fields the editors walk and leaves it unchanged. VER-63, VER-67, VER-68, VER-73, VER-74 and VER-75 are withdrawn (§8.2.11 L2, L3; §8.2.13 N3).

---
