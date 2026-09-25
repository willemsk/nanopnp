# Changelog

Every notable change to nanopnp, newest first. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the versions are the git tags of
[SPECIFICATION.md](SPECIFICATION.md) §2.7:

- a **release** `vX.Y.Z` closes a phase's release scope (v0.1 is Phase 0, v0.5 is Phase 1, v0.9 is
  Phases 2–3, v1.0 is Phase 4);
- a **work-package pre-release** `vX.Y.Z-alpha.N` marks the merge of the N-th work package toward
  that release.

The package version comes from the tag (hatch-vcs). A commit between two tags installs as a
development version that names it, for example `0.5.0a11.dev3+g1a2b3c4`, and that is the version
every provenance manifest records (FR-25). Each entry names the requirements it discharges. The
evidence is in the work package's plan under [docs/plans/](docs/plans), not here.

## [Unreleased]

## [0.9.0-alpha.2] - 2026-09-25

WP18: structure ingestion, alignment and the Cₙ axis, pipeline stage 1.

### Added

- Stage 1, `structure`. `nanopnp stage structure case.yaml` reads a PDB or mmCIF file, optionally
  gzipped, and an optional DCD, XTC, TRR or NetCDF trajectory (IF-04). It selects frames by
  `last_ns` and `count` and superposes each on the earliest selected frame's C-alpha (FR-01). It
  finds the Cₙ axis by chain-permutation superposition and puts it on z at r = 0, keeping the file's
  axial coordinate (FR-02). It emits a content-hashed `nanopnp/structure/v1` artefact: an `.npz`
  ensemble with its atom table and gate record, exportable as a PDB and a DCD (FR-27). mmCIF is read
  by gemmi, now in the `structure` extra (MPL-2.0).
- The oligomeric state is checked (FR-03). A blank element, an alternate location, a chain count
  other than the point group's n, a missing listed chain, a chain under half the most complete one's
  C-alpha, and a residue-name disagreement between chains are each refused, naming the atom or the
  chain (QR-12). So are a selection MDAnalysis cannot parse, a trajectory that does not hold the
  structure's atoms, and an mmCIF model whose atoms are not model 1's in order. The element and
  alternate-location refusals apply to the chains `source.chains` lists.
- Symmetry gates on the axis: the chains' spacing, the cyclic rotation angle, and a 10° limit
  between the axis and the file's z, whose +z must point to *cis*. `symmetry.axis: z` is admitted
  only within 0.01 nm of the detected axis (§5.3.1 NOTE on `structure:`).
- The manifest records the structure and trajectory digests, and stage 1's axis, gates, frames
  and drift (FR-25).
- A stage whose optional extra is missing is refused when it is created, naming the extra.
- VER-48, and `tests/data/structures/`: the wwPDB entry 2WCD, byte for byte.

### Changed

- A case carrying `structure:` resolves without `inputs.mesh`, and a walk past stage 1 is refused,
  naming stage 2; a sweep over such a case is refused when its plan is built. `structure:` beside
  `inputs.mesh` is refused.
- `structure.source.chains` is `all` or a comma-separated list, such as `A,B,C`.

## [0.9.0-alpha.1] - 2026-09-24

WP17: case schema v2 and the Python 3.11 floor ([#38](https://github.com/willemsk/nanopnp/pull/38)).
The first work package of Phase 2 and its one breaking change.

### Changed

- The case schema is `nanopnp/case/v2`. It adds `inputs.profile`, `inputs.pqr`,
  `structure.source.selection`, `geometry.membrane.centre_z_nm`, `charge.exclusion_offset_nm`,
  `charge.dielectric_transition_nm` and `numerics.mesh.size_scale`. It renames
  `structure.source.pdb` to `path`, and removes `charge.eps_protein` and `geometry.membrane.eps_r`:
  `physics.solid_permittivities` is the one place a solid's permittivity is set (IF-03, VER-47).
- A `nanopnp/case/v1` file is still read, as its v2 upgrade. The upgrade renames and moves only what
  the file wrote, and refuses a v1 file carrying a v2 key or a permittivity that disagrees with the
  map (FR-26).
- The schema string no longer keys a solve. The v1 key carried it, so every solve stored before
  this release re-solves once; the materials key is unchanged. The COMSOL export contract's
  `case_hash` for `clya-0.5M-plus50mV` is now `e266057d…` (§5.3.2 NOTE).
- Python 3.11–3.14. The `structure` extra requires MDAnalysis 2.10, GridDataFormats 1.2 and
  pdb2pqr 3.7, and CCP4 grids are written on every supported interpreter (QR-09, IF-05, VER-29).

### Added

- `charge.exclusion_offset_nm` and `charge.dielectric_transition_nm` are switches: a non-zero value
  is listed as a deviation in the manifest (FR-25).
- A supplied artefact beside one downstream of it on the same chain, and `size_scale` other than 1
  beside `inputs.mesh`, are refused naming both. `inputs.profile` and `inputs.pqr` are refused,
  naming the stage that will read them (FR-27).

### Fixed

- A Windows checkout keeps the bytes of `data/`. With `core.autocrlf` it rewrote the correction
  file's line endings, so the file hashed to another version and the materials key differed from
  every other platform's (FR-25, VER-47).

## [0.5.0] - 2026-09-24

**Phase 1, the solver core.** The verified Phase 0 physics becomes a product that others can run
and reproduce: a case file goes in, and a manifest, fields and a dataset come out. It runs on an
externally supplied mesh and charge field. It has full quantity-of-interest extraction, a frozen
`nanopnp/case/v1` schema, a sweep runner, a Tier-3 COMSOL comparison harness, a desktop shell and a
documentation site. Tiers 1 and 2 pass, and Tier 3 is enabled and verified. Under
`SPECIFICATION.md` §8.2.3, the attribution of differences against COMSOL is outstanding until the
author's reference exports exist. The end-of-phase report is in
[docs/plans/phase-1-solver-core.md](docs/plans/phase-1-solver-core.md).

The release gathers ten work packages, each tagged, each with its own entry in this file:

- WP7, the case-file schema, content-addressed artefacts and the provenance manifest
  (`v0.5.0-alpha.1`);
- WP8, mesh ingestion, quality gates and the reference geometry (`v0.5.0-alpha.2`);
- WP9, external charge and dielectric fields (`v0.5.0-alpha.3`);
- WP10, case-driven runs, the command line and field output (`v0.5.0-alpha.4`);
- WP11, the sweep runner (`v0.5.0-alpha.5`);
- WP12, the reference-matching stabilised mode (`v0.5.0-alpha.6`);
- WP13, the Tier-3 harness and the COMSOL comparison (`v0.5.0-alpha.7`);
- WP14, the packaging probe and the desktop shell (`v0.5.0-alpha.8`);
- WP15, live convergence monitoring and the field viewer (`v0.5.0-alpha.9`);
- WP16, user documentation and worked examples (`v0.5.0-alpha.10`).

### Added

- The Phase 1 end-of-phase report, and the §8.2.3 amendment that closes the phase.
- The Phase 2 delivery plan, `docs/plans/phase-2-geometry-pipeline.md`
  ([#36](https://github.com/willemsk/nanopnp/pull/36)), with the author's rulings recorded as
  `SPECIFICATION.md` §8.2.2. QR-09 is amended to Python 3.11–3.14, taking effect in the code with
  WP17.
- Versions come from git tags through hatch-vcs, and every earlier work package and milestone is
  tagged retroactively. CI and Read the Docs fetch the full history so the version resolves.
- `.github/workflows/release.yml` builds every version tag and publishes a GitHub Release, with this
  file's section as its notes, for each milestone.
- This changelog, which the documentation site also shows under *Project → Release notes*.

### Changed

- The README is reorganised around badges, highlights, status and roadmap, installation, and
  citation, and carries the same facts as before.
- `pyproject.toml` declares the supported Python versions and platforms and the project's links.

## [0.5.0-alpha.10] - 2026-09-23

WP16: user documentation and worked examples ([#34](https://github.com/willemsk/nanopnp/pull/34)).

### Added

- A documentation site (MkDocs and Material), built strictly on every push (VER-45). The case-file,
  command-line, exit-code and API references are generated from their sources, and the model pages
  render `SPECIFICATION.md` and `.knowledge/` verbatim.
- Five worked examples, among them a SLURM job-array run of the ClyA reference. A test executes
  each README's commands verbatim against a model property (VER-46).
- `nanopnp mesh cylinder|reference` writes a gated MSH 4.1 mesh (VER-32).
- `nanopnp.__all__` is a lazily resolved public API of twenty names (IF-01).

### Fixed

- Every checked-in reference case mapped a `default` group that the reference mesh does not carry.

## [0.5.0-alpha.9] - 2026-09-22

WP15: live convergence monitoring and the webgui field viewer
([#32](https://github.com/willemsk/nanopnp/pull/32)).

### Added

- A structural solve hook (`SolveHook`) that reports each rung and each accepted Newton step,
  including the undamped relative update. Watched and unwatched runs share one artefact key.
- The desktop shell's live convergence plot, and a webgui field viewer that renders a restored
  solution in a spawned child process.
- The webgui renderer ships with the package, byte-identical to the vendored npm tarball.

Completes IF-09 and discharges QR-11 and VER-44.

## [0.5.0-alpha.8] - 2026-09-21

WP14: the packaging probe and the desktop shell ([#31](https://github.com/willemsk/nanopnp/pull/31)).

### Added

- `nanopnp-probe`, together with a gated `windows-latest` job that builds it as a PyInstaller
  bundle and self-tests it on every push. This is the RSK-13 detector of amendment A4.
- The PySide6 desktop shell (`nanopnp-gui`): case editing and run control over the stage objects,
  and no physics of its own.
- `case_fields()`, `options_at()` and `registry_options()`. These walk `nanopnp/case/v1` once, so
  the editor's options come from the schema and the live registries.

Discharges the case-editing and run-control halves of IF-09, VER-43, and CON-09. §8.2 criterion 4
stays open until the author double-clicks a built bundle.

## [0.5.0-alpha.7] - 2026-09-20

WP13: the Tier-3 harness and the COMSOL comparison
([#30](https://github.com/willemsk/nanopnp/pull/30)).

### Added

- The comparison surface `nanopnp/probe/v1` and the golden archive `nanopnp/golden/v1`. A golden
  that leaves its unit, its evaluation boundary or its sign reference unstated is refused.
- Field norms: the r-weighted and unweighted relative L², and the located maximum. Also a four-rung
  attribution ladder, with a *reference-limited* verdict.
- `nanopnp validate`, and the nightly Tier-3 job, which is recorded and not gated.
- The COMSOL export contract, `docs/validation/comsol-export-contract.md`.

Discharges VAL-01 to VAL-04, retires RSK-14 and bounds RSK-09.

## [0.5.0-alpha.6] - 2026-09-18

WP12: the reference-matching stabilised mode ([#28](https://github.com/willemsk/nanopnp/pull/28)).

### Added

- Stabilisation as a registry of named models: `none`; `supg`, the streamline term on transport;
  and `reference`, the streamline and crosswind terms plus the flow GLS and grad-div pair.
  Switching the mode is a configuration, not a code branch.

Discharges NUM-03, NUM-12, NUM-14 and NUM-15, completes NUM-11, and adds VER-41 and VER-42.

## [0.5.0-alpha.5] - 2026-09-13

WP11: the sweep runner ([#26](https://github.com/willemsk/nanopnp/pull/26)).

### Added

- The `nanopnp/sweep/v1` document: a base case plus axes of dotted-path assignments, taken as a
  Cartesian product. Every point is re-validated against the frozen case schema.
- A warm-start forest, so each point runs as an independent job while starting from a converged
  neighbour. `nanopnp sweep plan`, `sweep run` and `sweep collect` implement it, and
  `sweep run --index` runs one member, so that one member is one job-array task.
- The wall-distance clamp and its NUM-34 gate.

Discharges FR-24, measures QR-06, and adds VER-36 to VER-40.

## [0.5.0-alpha.4] - 2026-09-07

WP10: case-driven runs, the command line and field output
([#24](https://github.com/willemsk/nanopnp/pull/24)).

### Added

- The run driver (`io/run.py`), which walks the stage graph and writes the manifest, the run record
  and the artefacts. Stage 11 extracts the quantities of interest and stage 12 writes the report.
- The `nanopnp` command line, whose exit codes are enumerated (IF-02). `nanopnp reproduce` re-solves
  a run and compares every recorded number (QR-08).
- IF-07 field export as XDMF with HDF5, on the P2 node set. Also `nanopnp/solution/v2`, the persisted
  converged state and operator used for warm starts.

Discharges IF-01, IF-02, IF-07, FR-27 and QR-08, and adds VER-32 to VER-35.

## [0.5.0-alpha.3] - 2026-09-07

WP9: external charge and dielectric fields ([#21](https://github.com/willemsk/nanopnp/pull/21)).

### Added

- `RadialGrid` and the `nanopnp/field/v1` document for gridded (r, z) fields: `.npz` natively,
  OpenDX and MRC through the `structure` extra, and the reference model's `%Grid` table read-only.
- Fixed-charge assembly with PHY-18's axis guard, and a charge-conservation report whose producer and
  consumer legs are kept separate. Also the §4.4 dielectric blend on a supplied solid fraction, and
  the `exclusion` material.
- Stage 7 (`FieldStage`), wired into the case, the continuation ladder and the manifest.

Discharges the consumer halves of FR-14, FR-15, QR-03, PHY-18 and PHY-19, and the read side of
IF-05. Adds VER-29 to VER-31 and VAL-15.

## [0.5.0-alpha.2] - 2026-09-05

WP8: mesh ingestion, quality gates and the reference geometry
([#19](https://github.com/willemsk/nanopnp/pull/19)).

### Added

- `MeshData`, the mesher-adapter seam, with a content hash over a canonical form. MSH 4.1 read and
  write, and MSH 2.2 as the archival format.
- The mapping from physical groups to the vocabulary, with diagnostics that name both sides of a
  mismatch.
- SICN and gamma element-quality gates at 0.3. A failure reports the worst element and its location.
- The ClyA reference geometry, assembled from the delivered 185-vertex pore profile, which also ships
  as the §5.2.1 regression fixture.

Discharges IF-06, VER-10 and QR-12, and adds VER-27 and VER-28.

## [0.5.0-alpha.1] - 2026-09-04

WP7: the case-file schema, content-addressed artefacts and the provenance manifest
([#17](https://github.com/willemsk/nanopnp/pull/17)).

### Added

- The frozen `nanopnp/case/v1` schema. An unknown key is rejected, naming the key and its block, and
  a v0.9 section is refused rather than ignored.
- Content-addressed artefacts, and a result store that uses the content hash as the cache key.
- The eight-group provenance manifest of §5.3.3. Its Deviations group is computed by diffing against
  the validated-default case.
- The `Stage` protocol of FR-27, covering the registry, progress reporting and cooperative
  cancellation.

Discharges IF-03, IF-08, FR-25, FR-26, FR-27 and VER-09, and adds VER-23 to VER-26.

## [0.1.0] - 2026-09-02

**Phase 0, the spike.** The coupled, steady, axisymmetric ePNP-NS system solves on an analytic pore
and is verified against analytic benchmarks. Phase 0 is met on §8.2 criteria 1 to 3. Criterion 4,
the desktop bundle, is deferred by amendment A2 and discharged in Phase 1 under A4. The COMSOL
comparison moved to Phase 1 under A3.

The release gathers six work packages, each of which is tagged and has its own entry in this file:

- WP1, the correction registry and the materials layer (`v0.1.0-alpha.1`);
- WP2, the axisymmetric forms, benchmark geometries and wall-distance field (`v0.1.0-alpha.2`);
- WP3, the scaling, damped Newton, solver gates and factorisation benchmark (`v0.1.0-alpha.3`);
- WP4, the coupled ePNP-NS model and the MMS machinery (`v0.1.0-alpha.4`);
- WP5, the continuation ladder, QoI extraction and envelope (`v0.1.0-alpha.5`);
- WP6, the analyte bodies and force benchmarks (`v0.1.0-alpha.6`).

### Added

- Consolidation ([#13](https://github.com/willemsk/nanopnp/pull/13)). PHY-13 clamp logging now runs
  on the QoI extraction path. The stabilisation mode is recorded in every provenance record (FR-25),
  and correction files are validated through a typed schema at load (FR-16).

## [0.1.0-alpha.6] - 2026-09-02

WP6: analyte bodies and force benchmarks ([#8](https://github.com/willemsk/nanopnp/pull/8)).

### Added

- A rigid analyte body of revolution on the axis, treated as a hard dielectric (part of FR-21,
  brought forward by amendment A1).
- The axial force by three routes: the domain form of NUM-28, the surface form, and the variational
  reaction force. The last is the oracle on the electric–hydrodynamic split (RSK-04).
- VER-19 to VER-22 (Stokes drag, Maxwell stress, Henry's mobility limits, route agreement) and a
  NUM-29 convergence study.

## [0.1.0-alpha.5] - 2026-09-02

WP5: the continuation ladder, QoI extraction and the envelope
([#7](https://github.com/willemsk/nanopnp/pull/7), [#9](https://github.com/willemsk/nanopnp/pull/9)).

### Added

- The nine-stage continuation ladder of NUM-18, warm-started from rung to rung, with the corrections
  enabled last.
- The ionic current by the ψ-domain indicator and by the variational reaction flux, with their
  agreement checked before any number is returned (NUM-24 to NUM-27). The transport number,
  rectification, conductance and EOF are derived from the same integrals.
- VER-11 and VER-17, and the §8.2 criterion 2 envelope as a measured, non-gating run.

### Fixed

- An electrolyte's correction switches were a record, not its behaviour: the classical rungs
  evaluated the full correction set.
- NUM-24's printed sign was wrong for its own electrode convention, and the specification is
  amended.

Discharges FR-17, FR-23 and QR-04, and retires RSK-03.

## [0.1.0-alpha.4] - 2026-08-31

WP4: the coupled ePNP-NS system on the analytic pore ([#6](https://github.com/willemsk/nanopnp/pull/6)).

### Added

- Nernst–Planck with the PHY-05 steric term. Taylor–Hood P2/P1 flow with the hoop-strain term,
  variable density and the ionic body force. The dielectric-gradient forces are opt-in (PHY-23).
- The `PhysicsModel` registry: `epnp-ns`, `pnp-ns`, `pnp`, `pb`, `pb-linear` and `poisson`.
  `pnp-ns` is `epnp-ns` with every correction set to `none`.
- Method-of-manufactured-solutions machinery on the full coupled axisymmetric system.

Discharges VER-14, VER-15, VER-16 and VER-18, and implements FR-20, NUM-02, NUM-03 and NUM-05.

## [0.1.0-alpha.3] - 2026-08-30

WP3: scaling, damped Newton, solver gates and the factorisation benchmark
([#4](https://github.com/willemsk/nanopnp/pull/4)).

### Added

- NUM-09 nondimensionalisation and NUM-10 field-wise row scaling.
- Damped Newton with the reference settings as defaults (NUM-16).
- The positivity, packing and potential gates, each of which aborts naming the field and the
  location (NUM-17, PHY-06).
- UMFPACK with a SuperLU fallback (NUM-21), and the factorisation benchmark of §8.2 criterion 3.

Discharges VER-08 and §8.2 criterion 3.

## [0.1.0-alpha.2] - 2026-08-30

WP2: axisymmetric forms, benchmark geometries and the wall-distance field
([#3](https://github.com/willemsk/nanopnp/pull/3)).

### Added

- The axisymmetric measure, which enforces integration order ≥ 3 on every form carrying `1/r`
  (VER-07).
- Analytic geometries, graded towards the wall (NUM-30), and the mollified wall-distance field
  (PHY-02, NUM-31).
- The `poisson`, `pb` and `pb-linear` models; `pb` is a distinct model (PHY-24). Also the
  variational reaction flux (NUM-25).

Discharges VER-06, VER-07, VER-12 and VER-13.

## [0.1.0-alpha.1] - 2026-08-28

WP1: the correction registry and the materials layer
([#2](https://github.com/willemsk/nanopnp/pull/2)).

### Added

- The five functional forms of PHY-11, each written once and dispatchable over NumPy or NGSolve.
- The `CorrectionModel` registry, with `none` registered rather than branched on, which makes
  PNP-NS a configuration (PHY-21, PHY-22).
- `⟨c⟩` as the arithmetic mean with logged per-species clamping (PHY-01, PHY-13), and `μ_i` derived
  from `D_i⁰` (PHY-14).

Discharges VER-03, VER-04 and VER-05.

[Unreleased]: https://github.com/willemsk/nanopnp/compare/v0.5.0-alpha.10...HEAD
[0.5.0-alpha.10]: https://github.com/willemsk/nanopnp/compare/v0.5.0-alpha.9...v0.5.0-alpha.10
[0.5.0-alpha.9]: https://github.com/willemsk/nanopnp/compare/v0.5.0-alpha.8...v0.5.0-alpha.9
[0.5.0-alpha.8]: https://github.com/willemsk/nanopnp/compare/v0.5.0-alpha.7...v0.5.0-alpha.8
[0.5.0-alpha.7]: https://github.com/willemsk/nanopnp/compare/v0.5.0-alpha.6...v0.5.0-alpha.7
[0.5.0-alpha.6]: https://github.com/willemsk/nanopnp/compare/v0.5.0-alpha.5...v0.5.0-alpha.6
[0.5.0-alpha.5]: https://github.com/willemsk/nanopnp/compare/v0.5.0-alpha.4...v0.5.0-alpha.5
[0.5.0-alpha.4]: https://github.com/willemsk/nanopnp/compare/v0.5.0-alpha.3...v0.5.0-alpha.4
[0.5.0-alpha.3]: https://github.com/willemsk/nanopnp/compare/v0.5.0-alpha.2...v0.5.0-alpha.3
[0.5.0-alpha.2]: https://github.com/willemsk/nanopnp/compare/v0.5.0-alpha.1...v0.5.0-alpha.2
[0.5.0-alpha.1]: https://github.com/willemsk/nanopnp/compare/v0.1.0...v0.5.0-alpha.1
[0.1.0]: https://github.com/willemsk/nanopnp/compare/v0.1.0-alpha.6...v0.1.0
[0.1.0-alpha.6]: https://github.com/willemsk/nanopnp/compare/v0.1.0-alpha.5...v0.1.0-alpha.6
[0.1.0-alpha.5]: https://github.com/willemsk/nanopnp/compare/v0.1.0-alpha.4...v0.1.0-alpha.5
[0.1.0-alpha.4]: https://github.com/willemsk/nanopnp/compare/v0.1.0-alpha.3...v0.1.0-alpha.4
[0.1.0-alpha.3]: https://github.com/willemsk/nanopnp/compare/v0.1.0-alpha.2...v0.1.0-alpha.3
[0.1.0-alpha.2]: https://github.com/willemsk/nanopnp/compare/v0.1.0-alpha.1...v0.1.0-alpha.2
[0.1.0-alpha.1]: https://github.com/willemsk/nanopnp/releases/tag/v0.1.0-alpha.1
