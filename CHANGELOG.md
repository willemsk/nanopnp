# Changelog

Every notable change to nanopnp, newest first. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the versions are the git tags of
[SPECIFICATION.md](SPECIFICATION.md) §2.7:

- a **release** `vX.Y.Z` closes a phase, one minor version per phase: v0.1 is Phase 0, v0.2 is
  Phase 1, v0.3 is Phase 2, v0.4 is Phase 3, v0.5 is Phase 4 (polish and user testing), v0.6 is
  Phase 5 (the graphical interface) and v0.7 is Phase 6 (the validated release), before the
  stable v1.0 (§8.2.6);
- a **work-package pre-release** `vX.Y.Z-alpha.N` marks the merge of the N-th work package toward
  that release; from Phase 5, the package `WP5.N` (`WP5.02` is `v0.6.0-alpha.2`). A package merged
  before the previous release takes no tag, and its entry waits under `## [Unreleased]` (§8.4.1).

The package version comes from the tag (hatch-vcs). A commit between two tags installs as a
development version that names it, for example `0.2.0a11.dev3+g1a2b3c4`, and that is the version
every provenance manifest records (FR-25). The versions were renumbered on 30 September 2026
(`SPECIFICATION.md` §8.2.4 D1): Phase 1's tags were `v0.5.0-alpha.1` to `v0.5.0` and
Phase 2's were `v0.9.0-alpha.1` to `v0.9.0-alpha.9`. A manifest written before then records the old
version, and this file's sections carry the new names. Each entry names the requirements it discharges. The
evidence is in the work package's plan under [docs/plans/](docs/plans), not here.

## [Unreleased]

WP5.01: the workbench design study, Phase 5's first package, in the second lane beside Phase 4. It
merges before `v0.5.0` and takes no tag, so its entry waits here (`SPECIFICATION.md` §8.2.17 S15,
S19). It critiques the Qt shell, holds a design round with the author, draws the areas as choice
panels and two whole-workbench mockups, and writes the design document and its requirements. No
`src/`, `tests/`, case schema or public API changes (S1). The
[plan](docs/plans/wp5.01-workbench-design-study.md) records the work.

### Added

- **`/np-gui` with five levels**: `render`, `review`, `publish`, `collect` and `grill`; the
  `gui-reviewer` agent; and the scripts `.claude/scripts/gui/shoot.cjs` and `capture_qt.py`
  (§8.2.17 S22).
- **The design document** `docs/design/workbench.md`, on the documentation site. It gives the Qt
  shell's capability list and critique, four suites in a project (Molecular, Continuum, Study,
  Analysis), the look and feel with its tokens in `docs/design/tokens.css`, the tools, the four live
  links, the project folder, the guided route, the later tools, and the decision log WB-01 to WB-32.
- **The concept boards, style tile, choice panels and mockups A and B** under `docs/design/`, with
  their generators and review records. Mockup A is chosen and revised.
- **`SPECIFICATION.md`**: FR-31 to FR-43 and QR-16; the browser shell's restatements of P3, IF-09,
  QR-10, CON-09, the packaging NOTE of ADR-004, RSK-13, VER-43, VER-44, VER-55 and VER-60, each a
  NOTE that replaces its clause when Qt leaves (S17); and the rulings of §8.2.18 on the inherited
  review rows.
- **Open items** REV-134 to REV-139 and REV-141, ruled in §8.2.19: REV-134 carried until Qt leaves;
  protonation to move before the density, the protonated density the validated default (REV-135, a NOTE
  beside PHY-16); REV-136 and the sweep's design round to `/np-plan amend 5`; REV-137, REV-138 and
  REV-141 to WP5.02. REV-140 was raised and fixed in the same package. The review raised REV-142, fixed by
  restoring the charge and radius edits to FR-38 (U6), and REV-143, the control edge's contrast, to WP5.02 (U7).

## [0.5.0-alpha.23]

WP57: an idealised pore as geometry, and the Python interface rebuilt on a `Case` and a `Session`
(`SPECIFICATION.md` §8.2.21 W4, W7; §8.2.22 X1 to X8; §8.2.23 Y1 to Y11; UT-02, UT-10; `MOD-11`; REV-111,
REV-120, REV-122, REV-144, REV-145, REV-153, REV-155, REV-157). The
[plan](docs/plans/wp57-idealised-pore-and-python-interface.md) records the work.

### Added

- **`geometry.pore` and `numerics.mesh.maxh_nm`**: a cylindrical pore is declared in the case (radius) and
  meshed by stage 6 under `numerics.mesh` (`maxh_nm`, `wall_h_nm`), like any other pore. It meshes to VER-62's
  recorded mesh (`546c34f4…`) bit for bit. `maxh_nm` and `wall_h_nm` are refused beside `inputs.mesh`.
- **`nanopnp geometry cylinder --out FILE.yaml`** writes the geometry as a region file that `nanopnp plot` draws;
  **`nanopnp mesh FILE|reference`** meshes a geometry file and prints its groups and hash (VER-32).
- **`boundary_conditions.wall_charge_C_m2`**: a uniform fixed surface charge on the lumen wall, a boundary condition of the
  Poisson equation, checked against Grahame's relation and the Gauss balance (PHY-09, VER-77).
- **`Case` and `Session`** (`nanopnp.api`). A `Case` is the case document: `Case.load`, `loads`, `cylinder`,
  `from_structure(..., orient=...)` and `with_`, which edits by copy and takes dotted keys, unique leaf names
  or a whole typed block. The blocks are public in `nanopnp.case` (`Charge`, `Mesh`, ...) and frozen.
  A `Session(store, write=..., workspace=...)` holds the store and runs, opens, sweeps and describes every case,
  the command line's, the sweep runner's and the window's included; each run takes its own `progress`,
  `cancel`, `on_stage`, `on_solve` and `on_artefact`.
- **`session.register_stage(function)`**: a function whose parameters name stages is a stage of one's own, keyed
  by the digest of its code and its inputs; it belongs to that session.
- **`RunResult.plot_field`, `plot_cutline`, `field_choices`, `quantity_rows`** and **`SweepResult.plot_iv`,
  `figure`** draw from what a run or a sweep returns; `SweepResult` also holds `dataset`, `plan`, `directory`
  and `rows`.
- **`SolveHook.rung_solved(name, seconds, iterations)`**: the end of a continuation rung; the progress line
  prints the manifest's seconds for the last rung (REV-157).
- **A correction file by path**: `electrolyte.parameters` and a correction's `model` may name a file by an
  absolute or case-relative path; its hash enters the stage-8 key and the manifest, and it is listed as a
  deviation (REV-122).
- **`post.forces.check_force_surface`** refuses a force surface whose two sides are not one pair of materials,
  exit 4 (NUM-29, QR-12; REV-120). **`validation.examples.untagged_commands`** finds a console command that no
  test runs (REV-155).

### Changed

- **A relative path in a case is read beside the case file**, as a correction file already was, so a case runs
  the same from any folder. A case held in memory carries the directory of the file it came from, so an edited
  copy and a member of a sweep over it read what the case file read; only a case that never had a file reads
  against the working directory. Migration: run from the case's folder no longer matters; a case written for
  another working directory needs its paths made relative to the file.
- **`post.forces.check_force_surface` compares the sides of a force surface by material, not by domain name**
  (NUM-29's NOTE, amended; REV-163). `electrolyte`, `cis` and `trans` are three names for one fluid, so a body
  straddling the seam between the lumen and a reservoir on a supplied mesh now passes; a surface meeting a
  fluid on one side and a solid on the other is still refused.
- **The case schema** (`nanopnp/case/v0.5`) gains `geometry.pore`, `numerics.mesh.maxh_nm` and
  `boundary_conditions.wall_charge_C_m2`; the definition titles of its JSON Schema change (the root is `Case`).
- **`Session.sweep`** returns a `SweepResult`; sweep members walk through the session's store.
- **`MOD-11`**: `with_section` and `register` stay internal; the API page names `Case.with_` and
  `session.register_stage`.
- **Notebooks 01 to 06, examples 01 to 04 and sessions 01 to 05** import only `nanopnp` and declare the pore
  in the case instead of meshing it first.
- **The knowledge base**: the no-MPI claim keeps what the lock file and the configuration show; the
  rectification sentence no longer asserts that a fixed-charge asymmetry alone rectifies (REV-111, REV-155).
  `inspect run --section charge` is example 07's reading of the manifest's charge group.

### Fixed

- **The nightly walks of examples 06 and 07** (the failure of the `v0.5.0-alpha.22` release run): example 07's
  step 3 reads the manifest's `charge` group with `inspect run --section charge`, since `inspect` prints a
  reading; the tests of examples 06 and 07 compare the absolute path a manifest records.
- **The review's fixes** ([CODE_REVIEW_021](docs/code_reviews/CODE_REVIEW_021.md)): `poisson` adds the `r`-weight
  quadrature order to its surface-charge term as it does to its stiffness and its volumetric source (NUM-07's
  NOTE; no number moves at P2); a surface charge applied to a boundary matching nothing is refused on every
  model, through one guard (NUM-06, QR-12); `register_stage` refuses a name outside `[a-z][a-z0-9_-]*` and a
  keyword-only or variadic parameter, as §5.5's NOTE lists; `untagged_commands` reads a command written with a
  `uv run` prefix, which VER-46's check had passed over; `reopen` and `sweep_isolevels` read a relative path
  beside the case file, as the walk does; `stage --list` answers from the registry alone; and
  `check_force_surface` matches boundary edges in one pass and refuses a surface no element owns.
- **The review's open items** ([CODE_REVIEW_021](docs/code_reviews/CODE_REVIEW_021.md), ruled by the author):
  a correction file named by a path keys stage 8 and the solve by its content and its file name, not by where
  it sits, so one calculation in two folders keys one artefact (REV-158); two correction files of one file name
  are refused rather than keyed as one; an edited case, a sweep member and the sweep's own plan read a relative
  path beside the case file, and a factory case resolves a path-named `parameters` as it already resolved
  `charge` (REV-159); the manifest refuses rather than records a null hash for a correction file it cannot find
  (REV-161). The surface charge's sign is written once, in `physics.poisson.surface_charge_term`, which takes
  the side of the equation the term is added to; every model and both Poisson-Boltzmann branches go through it,
  so `PoissonModel`'s sign is the one VER-77 and VER-31 exercise (REV-162). `default_ladder` refuses a
  Dirichlet wall potential and a wall surface charge together, which are two wall models for one wall
  (REV-164). The Gauss-balance benchmark records its own two quadrature errors, 8e-7 in the radial rule and
  1.4e-5 in Simpson, measured by refining each: its `rel=1e-3` assertion has a factor of 48 in hand, and no
  tolerance changed (REV-165).

### Removed

Each break, with its migration:

- **`nanopnp mesh cylinder`**. Declare the pore (`geometry.pore`, `numerics.mesh`) in the case; or write the
  geometry with `nanopnp geometry cylinder --out FILE.yaml` and mesh it with `nanopnp mesh FILE.yaml`.
  `mesh_cylinder` leaves the public names with it.
- **`run_case`**. `Session(store).run(Case.load(path), upto=..., only=...)`; the hooks are arguments of `run`.
- **The public names `run_document`, `resolve`, `load_case`, `loads_case`, `dump_case`, `dumps_case`,
  `CaseDocument`, `plan_from_document`, `run_plan`, `Stage` and `registered_stages`.** They stay importable
  from their modules (`nanopnp.pipeline.run`, `nanopnp.pipeline.case`, `nanopnp.io.case`,
  `nanopnp.core.stages`, `nanopnp.api.sweep`); for a case use `Case.load`, `Case.loads` and `Case.dumps`.
- **`Case.cylinder(..., store=...)`, `Case.run` and the `"debye"` wall**. Build the case, then
  `Session(store, write=...).run(case)`; `wall_h_nm` is a number or `"auto"`.
- **`nanopnp.sweep.sweep`**. `session.sweep(case, axis=..., values=...)`, or `nanopnp.api.sweep.sweep`.
- **The `check_routes` stage option and `QoIStage.deviations`** (REV-160). The NUM-26 cross-check between the
  two current routes is always run; no case, session or command line could ever turn it off, so the deviation
  it contributed could never be recorded. `indicator_band_nm` and `extension_shell_nm` stay as what they are:
  settings of stage 11 read when it is invoked directly, with no route from a case file.
- **`nanopnp.pipeline.reproduce`**. `nanopnp.api.reproduce.reproduce`.
- **`SolveHook` gains a method.** An implementation adds `rung_solved`; a no-op is enough.

## [0.5.0-alpha.22]

WP56: the command line read by a person, the fix of the first user-testing round's command-line findings
(`SPECIFICATION.md` §8.2.21 W2 to W6, W8; UT-01 to UT-09, UT-11, UT-12; REV-154). The
[plan](docs/plans/wp56-command-line-read-by-a-person.md) records the work.

### Added

- **`nanopnp plot TARGET [STAGE] --out PATH`**: draws a stage's figure of a case, of a finished run directory
  (default `solve`) or of a sweep, to `.png`, `.svg` or `.pdf`. A wrong suffix, an unknown stage, a stage with no
  figure, or a case file without a stage is refused before anything runs (FR-44).
- **`nanopnp inspect A B`**: two run directories compared, the case fields that differ, each run's deviations
  from the validated model, and each quantity side by side with `(B − A)/|A|`; `--json` gives the same.
- **`--progress/--no-progress` on `run` and `stage`**: each stage and continuation rung on standard error as it
  starts, with each rung's accepted Newton steps and seconds; on by default when standard error is a terminal.
  Standard output and `--json` do not change.
- **`reference/field-document.md`**: the field document's keys, generated from the models, beside the case-file
  reference.
- `pipeline.run.read_run` and `open_run`, and `sweep.collect.read_dataset`: one reader of a run directory and of
  a sweep dataset. `Manifest.from_document` rebuilds a manifest and refuses one whose hash no longer matches,
  exiting 3 (`ManifestHashError`; QR-08).

### Changed

- **`nanopnp inspect` reads by schema**: a run as a summary (model, stages, rungs with their Newton steps and
  seconds, quantities, every deviation, or the reason a group did not run), a sweep dataset as a table with its
  rectification ratios, a stored artefact as its schema, key, parameters and summary. `--section GROUP` prints
  one group of a manifest. `--json` prints what it printed before (IF-02).
- **The wall-distance refusal names a setting the run reads**: `numerics.mesh.wall_h_nm` for a mesh the case
  generates, and for a supplied mesh its file and `nanopnp mesh cylinder --wall-h-nm` (NUM-34, QR-12; REV-154).
- **Help**: `mesh cylinder` groups its flags as geometry and mesh; `reproduce` says when a run fails to
  reproduce; `sweep run` says how workers are pinned to threads.
- Session 03's coarse case is `wall-100.case.yaml`, after its mesh (UT-08).

### Fixed

- **A field document that states its charge twice with opposite signs is refused when read**: a form's charge
  parameter (`gaussian_ring`'s `charge_e`) and `q_net_e` of opposite sign, or one zero beside the other, exit 4
  naming both keys, and the producer leg of the conservation check names both for a form (QR-03, PHY-19, QR-12).

## [0.5.0-alpha.21]

WP55: the user-testing protocol. Five sessions that the author runs as a nanopore modeller would, a log for
what they find, and a nightly test that keeps every session's commands working (`SPECIFICATION.md` §8.2.6 F3,
§8.2.7 G7). No `src/` change. The [plan](docs/plans/wp55-user-testing-protocol.md) records the work.

### Added

- **`docs/user-testing/protocol.md`**: how to install the release into a fresh environment, copy one session
  out, time-box it and record what happens. Sessions: the command line, the model's corrections and the salt,
  mesh refinement and a refused mesh, the Python interface in a notebook with a stage of one's own, and a sweep
  over voltage and salt. Each states a task and a property of the model to expect, never a number.
- **`docs/user-testing/findings.md`**: the empty `UT-nn` log, ruled at the second `/np-plan amend 4`.
- **VER-69**, `tests/tier2/test_user_testing_sessions.py` (nightly): each session's tagged commands run as
  written on VER-46's runner, and none is left untagged.

## [0.5.0-alpha.20]

WP54: the notebooks and figures revised, the library's cylinder and case factories, a one-axis sweep in Python,
and the notebooks and stage figures rebuilt on one plotting layer (`SPECIFICATION.md` §8.2.20 V1 to V17). The
[plan](docs/plans/wp54-notebooks-and-figures-revised.md) records the work.

### Added

- **`nanopnp.mesh_cylinder`** (and `nanopnp.mesh.generate_cylinder`): the CLI's cylindrical-pore mesher moves
  into the library and the public surface, and the CLI calls it (FR-37, as amended).
- **`nanopnp.orient_pore`**, structure preparation in the library: it keeps the chains named, estimates the
  pore axis, points +z at the end the user names *cis* and places a registration centroid on the axis.
  Example 06's `prepare.py` calls it, and `core.paths.structure_file` takes a full file name, searching
  `tests/data/structures/` in a checkout (FR-37, §8.2.20 V1).
- **`Case.cylinder` and `Case.from_structure`**: factories that build a case on the validated ePNP-NS model,
  with its species, corrections and solid permittivities read from the parameter file (FR-30, §8.2.20 V3).
- **`nanopnp.sweep.sweep(case, axis=, values=, origin=)`**, returning a `Sweep` whose `run()` plans, runs and
  collects the dataset (FR-30, VER-36).
- **`RunResult.current_nA`, `conductance_nS` and `fields`**: the run's current, conductance and solved fields
  in SI (FR-30).
- **Panels in `nanopnp.plot`**: `plot_field`, `plot_mesh`, `plot_axial_cutline`, `plot_radial_cutline` and
  `plot_iv`, with `plot_charge` and `mark_constriction` in `nanopnp.plot.panels`, and the cutlines in
  `nanopnp.plot.data` (FR-30).
- **Notebook 05**, the cylindrical pore, in four steps: the mesh, its wall sized fixed or at λ_D/5, the solve,
  profiles along and across the pore on debounced sliders, and the I-V sweep of the cis ring (FR-30,
  §8.2.20 V2, V8, V9).
- **`Case.cylinder(wall_h_nm="debye")`** sizes the pore wall as NUM-30 does, `min(0.05 nm, λ_D/5)` of the
  case's salt; the fixed 0.35 nm stays the default (NUM-30, §8.2.20 V9, V14).
- **`nanopnp.structure.prepared_pore`** writes `orient_pore`'s file once, named by the source's bytes and the
  choices, and `plot.data.field_menu` and `default_potential_range_mV` give the notebooks their menu and
  default range (FR-37, FR-30, §8.2.20 V17).
- **`plot_field(halfrange=)`** sets the colour scale's reach about zero, and `nanopnp.plot.data.qoi_rows`
  lists the quantities of interest in display units (FR-30, §8.2.20 V6).
- **`plot_mesh(edges_only=True)`** draws the element edges alone, in grey on white (FR-30, §8.2.20 V12).

### Changed

- **`Case.load` makes relative input paths absolute** against the case file (FR-25, QR-08).
- **`SolutionFields` and `solution_fields` move to `nanopnp.post.export`**, keeping the six-node cells (FR-30).
- **The stage figures are rebuilt on the panels**: the potential in mV centred on zero; each concentration as
  log10(c/c_bulk); u_z with streamlines; the mesh as its edges, the whole domain by size and the lumen by SICN,
  with a λ_D/5 bar;
  the charge about zero with the χ = 0.5 contour; the constriction and the operating concentration marked; the
  rectification ratios and G on the I-V (FR-30, NUM-30).
- **Notebooks 01, 02 and 06 run on `orient_pore` and `Case.from_structure`**, from the deposited 2WCD entry,
  with no `os.chdir`, `only=True` or call into an example: one case in all three, so they share their stages
  from the store; the preparation, protonation, salt and solve in forms, the contour's isolevel on a slider,
  and 06's solved fields one figure each, as in 03 (FR-30, FR-37, §8.2.20 V1, V2). 01 and 06 choose the mesh
  size scale and show a measured table of its cost; 01's isolevel spans 0.01 to 0.99 and shows a gate's
  refusal in place of the figures; 06 shows its stage figures and Newton history in one row of tabs
  (§8.2.20 V10 to V12).
- **`Case.from_structure` writes the `geometry` block** at its defaults, so `with_` can edit a contour or
  membrane setting; the stage keys do not move.
- **Notebooks 03 and 04 run on `Case.cylinder`**, from a shared store (`$NANOPNP_STORE`, else
  `notebooks/.store`), with form-gated solves, one figure per field and debounced cutline sliders (FR-30,
  §8.2.20 V2). Their figures pan and zoom in a running notebook, and the potential's colour range is a
  slider, by default twice the bias (§8.2.20 V6, V7).

### Fixed

- **A `Case.load` run reproduces.** The run records the case as held in memory, so a reproduction checks the
  case file it wrote (FR-25, QR-08).
- **A sweep's panels share the cis-referenced bias and keep failed points**; a failed point whose side of the
  ground is unknown is left off (FR-30).
- **The code review's findings** (§8.2.20 V16, V17): `sweep()` accepts numpy values and names its directory by the
  plan's hash; `plot_iv` refuses a sweep that is not over the bias; the case's path fields are read from the
  schema; `structure_file` tries a name as given before adding `.pdb`; `Case.cylinder`'s cached mesh is keyed by
  the mesher's identity; a solve is restored once for its figures and `RunResult.fields`; forces show in pN; the
  concentration panels draw against the bulk the solve imposed on each species, and the lumen close-up is read
  from the pore wall (FR-30, NUM-30).

`orient_pore` logs a warning where its registration centroid is more than 0.1 nm off the estimated axis
(§8.2.20 V15). REV-146, REV-147, REV-148, REV-150 and REV-152 are fixed; REV-151 (centring on the axis) waits for
its own package, and REV-149 (changing residues in notebook 01) is deferred by §8.2.20 V13.

## [0.5.0-alpha.19] - 2026-10-22

WP53: the workflow, three commands with levels, workers and a current checkout (`SPECIFICATION.md`
§8.2.16 R5 to R7, R12).

### Changed

- **The workflow is three commands with levels.** `/np-plan <project | phase n | amend n | wp n>`,
  `/np-implement [wp n]` and `/np-ship [wp n | phase n]` replace `/phase-plan`, `/wp-plan`,
  `/wp-implement` and `/wp-ship`, with no aliases. Each `SKILL.md` routes to a shared core,
  `.claude/workflow/core.md`, and the file of its level, so an invocation loads only the rules it
  needs. `/np-plan project` re-plans the project; `/np-ship phase n` confirms a phase's close and
  tags its release.
- **Rulings and amendments are written where §8.2.16 R3 and R4 put them**: a ruling's table to a new
  `specification/history/` record, its standing rule to §8.4, and a phase plan's amendment to the
  phase's record.
- **The session-start hook keeps the checkout current.** It fetches `origin main` into the primary
  checkout, fast-forwards a clean `main` that is behind it, and warns when the checkout lacks its
  commits. Nothing in it fails the session.
- **The workflow was reviewed and reworded.** A review fixed 21 inefficiencies, contradictions and
  flaky steps: among them, `/np-implement` and `/np-ship` find the package's PR the same way, the
  gate has one waiting rule, and `/np-ship` tags after the merge. The text follows ASD-STE100's
  writing rules.
- `CLAUDE.md`, §8.4.3, §8.4.4 and the live pointers name the new commands.

## [0.5.0-alpha.18] - 2026-10-22

WP52: the documents, the specification and the plans split (`SPECIFICATION.md` §8.2.16 R2 to R4, R9, R10).

### Changed

- **The specification is a bundle.** `SPECIFICATION.md` is the entry point, with the reading rule and a
  map from section and identifier to file; the text is in `specification/`, one file per numbered
  section, with §5, §7 and §8 split by subsection, and the Phase 0 exit criteria and §8.2.1 to §8.2.16
  moved verbatim to `specification/history/`. No clause is reworded. §11 gains three rows.
- **§8.4, the development process.** The rulings in force that no clause carries, restated once, each
  with its ruling. `specification/history/index.md` lists where each of the 119 rulings holds now.
- **`.claude/scripts/clause.py`** reads the bundle and prints every definition of an identifier, each
  labelled with its file and line range. The site copies the bundle, its navigation is generated from
  the bundle's index pages as the knowledge base's is, and the guide's anchored links point into it.
- **The Phase 4 plan states its current scope.** Its amendments and its earlier text are in
  `docs/plans/phase-4-record.md`.

## [0.5.0-alpha.17] - 2026-10-22

WP51: the plotting library and the notebooks (`SPECIFICATION.md` §8.2.14 P1 to P6; FR-30).

### Added

- **`numerics.mesh.wall_for_concentration_M`.** Sizes `wall_h_nm: auto` at the Debye length of a design
  concentration, so a salt sweep above 1.474 M can share one mesh. The run's own NUM-30 ratio is still
  recorded. Refused beside an explicit `wall_h_nm`. FR-10, VER-53; §8.2.14 P10.
- **I-V and flow figures, and larger figures.** A sweep's figure leads with the I-V curve (nA) and the
  electro-osmotic flow rate (µm³/s); `plot.figure` and `RunResult.figure` take `scale`; the notebooks
  take a `scale` and an `interactive` value. Example 03's charged case now outputs `eof_rate`
  (§8.2.14 P9).
- **`nanopnp.plot`**, behind the `plot` extra (Matplotlib): `plot.figure(artefact, inputs=None)` draws
  the figure of any stage's artefact and of a sweep. Figures of the aligned atoms, the density, the
  reduced map, the contour, the regions, the mesh, the protonation states, the charge and dielectric
  grids, the corrections against the driver the electrolyte declares, the solve (fields, Newton
  history, continuation rungs) and the quantities. No name joins `PUBLIC` (F4). `plot` follows `post`
  in the layer order and imports no backend; `modularity-layering.yaml` records it (VER-61).
- **Notebook display.** `Artefact` and `RunResult` answer `_repr_mimebundle_` (text and HTML with the
  figure embedded). `RunResult` gains `resolved` and `figure(stage)`.
- **Stage registry.** `core.stages.register(..., figure="module:function")`, `register_figure`,
  `figure_target`, `draw` and `FIGURE_FREE` (`case`, `report`). Every builtin stage declares a figure or
  is figure-free; `draw` turns a missing Matplotlib into `MissingExtraError` naming `plot`.
- **A new payload.** The solve stage writes `newton_history.json` (payload key `newton_history`): per
  rung, the residual, update, damping and trials of every Newton step. An artefact cached before this
  release lacks it and draws "history not recorded".
- **Extras.** `plot`, `notebook` (`plot` and marimo) and `examples` (`plot`).
- **`nanopnp.Case`** (`pipeline/handle.py`, in `PUBLIC`): `Case.load(path, store=...)`, `case.run(upto=..., bias_V=0.1)`, `case.with_(...)` and `case[name]`. A field is named by its dotted case-file path or by a leaf name only one field ends in; a shared name is refused. §8.2.14 P8.
- **`notebooks/`**: six marimo notebooks (geometry, charge, solve, sweep, and the cylindrical pore and 2WCD each end to end), each run headless every night. Each is one block of cells per stage: what the stage is, its settings as plain values (dotted case paths, edited through `nanopnp.Case`), the line that runs it with `only=True`, and what it stored; no widgets. Notebooks 02 and 03 start mid-pipeline and open with a labelled set-up cell. A notebook prepares its own input (the structure, or the pore mesh), so nothing is run before it. `pyproject.toml` sets marimo's `on_cell_change = "lazy"`, so editing a cell marks the later ones stale instead of re-running the solve.

### Changed

- `post/export.py` gains `restored` and `sampled_fields`, the one restore and sampling path of the
  IF-07 export and the figures. The export's output is unchanged.

## [0.5.0-alpha.16] - 2026-10-19

WP50: the test scope (`SPECIFICATION.md` §8.2.13 N1 to N5).

### Changed

- **Tests only where a silent wrong answer is possible** (N1): 378 Tier 1 tests of repository
  self-checks, interface wording and refusals are deleted; the physics, numerics, core mechanisms and
  the licence and architecture guards stay.
- **`nightly` replaces `extended`** (N4): `pytest --nightly`; the per-push selection holds example 01
  and example 02's ePNP-NS leg with their VER-62 goldens; a failed nightly run opens an issue.
- **VER-63, VER-67, VER-68 and VER-75 are withdrawn; VER-72 keeps its import guard** (N3).
- **Review gaps closed:** the VER-62 golden-file, solution-state, VER-71 classification, charge-input, manifest-group and VER-76 tests stay or are restored; the OKF and findings-log check functions are deleted (REV-117, REV-118 fixed).

### Removed

- The coverage job, `diff-cover` and `pytest-cov` (N2); `knowledge/pending.yaml`.

## [0.5.0-alpha.15] - 2026-10-18

WP49: the cost study (`SPECIFICATION.md` §8.2.12 M2; REV-112, REV-113; VER-76).

### Added

- **The case schema as JSON Schema** (VER-76): `nanopnp.io.case_paths.case_json_schema()` and
  `schema_leaves`, generated from the case document's own model; the documentation build publishes
  it as `reference/case.schema.json`. A test fails when its leaves and `case_fields()` differ.
- **The cost-study script** (REV-112): `python -m nanopnp.validation.costs`, whose record is
  `docs/project/cost-study.json`. The measurement found no cost over its threshold: stage 1 projects
  to 1.14 GB at 1,000 frames (limit 4 GB), building forms is at most 0.33 % of stage 10 (limit 5 %)
  and store IO at most 0.51 % of a cold walk (limit 10 %), so nothing was changed. The review's
  harness fixes raise the last two to at most 0.54 % and 0.69 %; the record is re-run at the Phase 4
  close (REV-116).

### Fixed

- **Main's CI on macOS and Windows** (VER-72): the check of the ngsolve stub file runs only where the
  wheel ships it.

## [0.5.0-alpha.14] - 2026-10-17

WP48: the OKF bundle backfilled and the pending ledger closed (`SPECIFICATION.md` §8.2.7 G3, G8,
VER-68; REV-103 closed). No code path of the solver changes, and VER-62 is untouched.

- **The ledger closed** (G3, G8): all 361 open claims from WP47 are resolved. `pending.yaml` is empty
  (`{}`), `CEILING` is 0, and `[tested: pending]` is refused unconditionally in `nanopnp.validation.okf`
  and `test_okf_bundle.py`.
- **The claims backed** (VER-68): all 100 pending test-evidence claims are backed by assertions on
  existing computations and D5 source citations; 90 library behaviour claims are backed in
  `tests/tier1/test_library_behaviour.py`; 51 NGSolve trap claims are backed in
  `tests/tier1/test_ngsolve_traps.py`; 63 physics and numerics domain claims are backed across
  existing domain suites and `tests/tier1/test_knowledge_arithmetic.py`.
- **The verified audit** (G8, REV-103): all 56 `[verified]` markers across the bundle are audited. 15
  deterministic checks in `tests/tier1/test_knowledge_arithmetic.py` cover executable calculations, and
  source readings and historical observations carry source footnotes (`verified_unsourced` is 0).
- **Library Behaviour versions** (VER-68): all 17 `Library Behaviour` concepts declare non-empty
  `tested_with` mappings matching `uv.lock`. Missing, non-mapping, empty, empty-version and stale
  metadata are refused.
- **Specification amendment**: `VER-68` (3) updated so `[tested: pending]` is refused and trailing
  WP47-ceiling wording replaced with empty `pending.yaml` and zero ceiling; (5) holds a package
  that `uv.lock` resolves at two versions to the older one; §11's description of the ledger follows.

## [0.5.0-alpha.13] - 2026-10-14

WP47: the knowledge base as an Open Knowledge Format bundle (`SPECIFICATION.md` §8.2.6 F6, §8.2.7
G12, VER-68). No code path of the solver changes, and VER-62 is untouched.

- **The folder** is `knowledge/`, no longer `.knowledge/`: the bundle is published and tested, so it is
  no longer hidden. Every citation, the check's patterns, the gate and the documentation build follow.
- **The bundle** (VER-68): `knowledge/` is a directory per note and a concept per `##` section,
  121 in all, each with a header (`type` from a closed list, `sources`, `generated`, `verified`), an
  `index.md` per directory, a root `index.md` declaring `okf_version: "0.2"`, `log.md` and
  `pending.yaml`. The old files `knowledge/0N-*.md` are gone: **a citation of one is a break**, and
  every address in the repository, the plans and this file's released sections names a bundle path.
- **The check** (VER-68): `nanopnp.validation.okf` and `tests/tier1/test_okf_bundle.py` refuse a
  concept without a typed header, an address that reaches no concept or heading, a legacy
  `knowledge/0N §x` form, a `[tested: …]` naming no test, a bare `[tested]`, a `verified` list that
  differs from the claims, a footnote that is no source, an older `tested_with`, and a pending list
  that differs from the files or exceeds 361. `markdown` joins the `dev` group, so the comparison of
  heading ids with the documentation build runs in every test leg.
- **The navigation** (G12 7): the knowledge base's menu is generated from the `index.md` files into
  `mkdocs.yml` by `docs/scripts/generate.py`; a stale block fails Tier 1. The pinned correction file's
  comment now names the errata concept, which moves the pinned v0.5 solve key (VER-59); nothing computed moves.
- **The ledger** (G3, G8): 69 claims name a test, 314 are `[tested: pending]` and 47 `[verified]`
  claims name no source; WP48 empties the list.
- **The gate** (VER-45): `prose-only.sh` reads `knowledge/` and any Markdown that cites it as
  not prose; the documentation site renders the bundle through its index pages, with the
  `footnotes` extension.

## [0.5.0-alpha.12] - 2026-10-14

WP46: the small fixes (`SPECIFICATION.md` §8.2.9 I2). Fifteen register rows are fixed, each with
its test; no computed number moves beyond round-off, and VER-62 holds.

- **Radial grid `.npz`** (VER-29, REV-14): carries `origin_nm` and `spacing_nm` and reads them back
  bit for bit; an axes-only file still reads; `charge/stage.py` deposits the grid it summed.
- **Stage-6 key** (VER-53, VER-54, REV-16): leaves the Debye length out, so a salt sweep below
  about 1.5 M meshes once. Stored stage-6 keys change once, so an existing store re-meshes once.
  The manifest's `sizing` block takes its Debye entries from the run's own case, not from the
  summary of the mesh another salt stored.
- **`Store.put`** (VER-26, REV-18): stages the entry in a sibling directory and renames it; the
  first complete entry stays and every writer returns it.
- **Stage 1 refusals** (VER-48, REV-19, REV-57): a trajectory with no frame, a second Cα at one
  residue and a chain split across the periodic box (consecutive Cα over 1.0 nm apart) are refused
  naming the file, residue, or chain, pair, frame and distance; a DCD's frame times come from its
  header without decoding.
- **Density maps** (VER-49, REV-40): an interchange map whose spacing lies outside 0.025 to 0.05 nm
  is refused saying maps are written in ångströms.
- **Example 05** (REV-15): `#SBATCH` values are written raw, and one sbatch cannot read is refused.
- **VAL-05** (REV-59): `attribute_to_construction` refuses a `strict=False` comparison with
  `GeometryComparisonError`.
- **Housekeeping** (REV-43, REV-49, REV-50, REV-51): `chain_characters` lives in
  `structure/ensemble.py` (a chain-key overflow raises `EnsembleFormatError`, exit 4, not
  `PQRError`); `Measures.at_order`; the axis-weight test uses `innermost_crossings`; `ReopenedRun`
  carries its `ResolvedCase`. REV-24 measured no duplicate (one build per solve).
- The shipping skill and the steward unsubscribe from a green, mergeable PR after one report.
- **Review fixes** (REV-98 to REV-102): `Store.put` returns a stored key's entry before copying
  anything and removes staging directories a killed put left more than a day ago; the charge-grid
  key names `lattice_record`, so stored charge grids are deposited again once; `frame_times`
  decodes the frames when a DCD reader has no header attribute.

**Breaking.** A stage that writes a payload and is constructed without `workspace=` raises
`MissingWorkspaceError` naming the argument; it no longer picks a directory under the default store
root (REV-25, REV-55). A caller that built `MeshStage()` or any other stage by hand passes
`workspace=<directory>`, which the stage writes into; a run through `run_case` or the CLI already
does. The structure, density, symmetry, contour, region and solve stages refuse at the start of
their run, before the work they would lose; `ReportStage` hands its workspace to the solve it runs
when no solve artefact is offered. A stage also refuses a workspace that already holds files
(`WorkspaceInUseError`, REV-98), because a second run would overwrite what the first run's
artefact points at: give it an empty directory, or construct it with `overwrite_workspace=True`
(`run_case(..., overwrite_workspace=True)` for a walk) to replace them.

## [0.5.0-alpha.11] - 2026-10-14

WP45: the prose strip (`SPECIFICATION.md` §8.2.11 L4 amended, L5, L9, L10; VER-75). Docstrings and
comments fall from 33.0 % to 10.6 % of the lines of `src/nanopnp` and from 18.8 % to 2.1 % of `tests/`,
with no instruction changed (`.claude/scripts/same_tree.py` proves every commit). L4 now asks a condensed
docstring on every public function, class and method, NumPy-style parameters where name and type do not
say, none on a test or private code; ruff's D101 to D103 and D106 now hold in `src/nanopnp`. Derivations found nowhere else moved to `knowledge/`. It discharges
VER-75; REV-93 to REV-97 are fixed, REV-91 is deferred and REV-92 declined.

## [0.5.0-alpha.10] - 2026-10-13

WP44: the loop simplified (`SPECIFICATION.md` §8.2.11 L2, L3, L4 in rule, L6 to L9). A commit runs the
lock check, ruff, the format check, mypy and all of Tier 1; the push gate runs the whole suite with
`--extended` once, without coverage, and the push guard stays; a pull request's two shards are Tier 1 and
Tier 2. The impact recorder, selector and map, the budget enforcer, the duration record, the agent guard
and roster, `model-policy.md` and two agents are deleted; the CI-log classifier runs on Haiku (L9). A plan holds at most 1,500 words and six
decisions (VER-72 g); the docstring and comment rule is written down and D101 to D107 and D417 are off.
VER-73 and VER-74 are withdrawn. REV-80 and REV-81 are fixed by removal.

## [0.5.0-alpha.9] - 2026-10-12

WP43: the development loop (`SPECIFICATION.md` §7.6, §8.2.10 J1 to J12). A commit runs only the
tests a recorded impact map finds its change to touch, the push gate runs once in the background
and follows up on its selection, and a pull request runs one ubuntu leg in two shards, the
platforms and the `extended` walks after a merge, nightly and before a release. Python 3.14 is the
working version. It discharges VER-73 and VER-74 and §8.2.10 J2 to J5 and J7 to J11, and leaves
REV-80 to REV-83 open for the author's ruling on the missed budgets.

### Added

- **VER-74:** `tests/impact.py`, a pytest plugin that records each test's executed functions,
  read files, listed directories and started processes through `sys.monitoring` and audit hooks,
  and a selector that falls back to the development selection, naming why, whenever a change is
  one it cannot attribute. `gate.sh map` records the map; the commit hook selects from it.
- **VER-73:** `.github/budgets.yaml` and `.github/scripts/ci_budget.py`: CI fails a pull-request run
  whose critical path, or any development-selection file, exceeds its budget by more than 50 %;
  the gate logs its own times to `<git-dir>/nanopnp-gate.log`.
- The push guard: the commit hook refuses a branch push whose tree `gate.sh run` has not passed in
  full (J3). After a pass, `gate.sh run` follows up with the selection of the change since the
  passed tree, under coverage and `diff-cover` against it.
- `--shard i/N` in `tests/conftest.py`, packing whole files by `tests/durations.json`.
- The agent roster in `.claude/agents/` (gate-runner, surveyor, ci-log-classifier,
  physics-reviewer), `.claude/scripts/clause.py`, and `.claude/hooks/agent-guard.sh` on every
  `Agent` call (J8); `.claude/scripts/reading_set.py` and `usage.py` (J11).
- `## In brief`, a plain-language summary of at most 250 words, in every plan from WP43 on, the
  Phase 4 plan, `current.md` and the pull-request body (J9).

### Changed

- **Breaking (contributors):** a pull request runs lint, the documentation build and the
  development selection in two shards on ubuntu, Python 3.14; `CI result` is the one required
  check and posts `ci/tested-tree`. macOS, Windows and the `extended` walks run after a merge,
  nightly and before a release; `full: true` runs the release matrix (§7.6, J4, J10).
- The working Python is 3.14 (`.python-version`); VER-62 holds on it at round-off (J5).
- The `extended` walks run without coverage; changed-line coverage is over the development
  selection (§7.6 NOTE).
- `CLAUDE.md`, the skills and the model policy are cut to their word targets, with the physics and
  Python rules in path-scoped `.claude/rules/`; an Execution brief is capped at 1,600 words (J11).

### Fixed

- `clause.py` prints on a cp1252 console.
- The push guard answers a `git push` only where one runs: a commit message, an `echo` or a pull
  request body that names it is text, and `bash -c 'git push'` is a push (VER-74, J3).
- The selection names no test file that is gone, and the hook takes pytest's exit 5 for a new
  file whose tests the marker expression deselects; `gate.sh map` installs a map only from a green
  run, and the recorder empties the source's `functools` caches before each test, so a test a warm
  cache served still depends on what it answered (VER-74).
- `--strict-markers` knows `no_cover` without pytest-cov; the agent guard also reads `Task`; the
  development container runs the working Python.

## [0.5.0-alpha.8] - 2026-10-10

WP42: the verification checks (`SPECIFICATION.md` §5.3.1, §5.4.3; §8.2.7 G6; §8.2.9 I1, I2).
Every comparison in a gate module outside `gui/` is verified against passing NaNs;
every case leaf is classified and verified either to alter the assembled forms or stage keys,
or to be declared unread or provenance-only; case schema moves to `nanopnp/case/v0.5`, retiring
pre-release `v1` and `v2` identifiers; models declare and refuse non-default leaves they do not read;
the `pnp` model honours only `flow: false`, `variable_density: false`, and `inertia: false`;
inf-sup checks are gated on flow models; Example 06 stage-7 keys and per-ion Einstein ratios are pinned;
and duplicated test fixtures and constants are consolidated. It resolves REV-11, REV-12, REV-13,
REV-23, REV-29, REV-34, REV-42, REV-44, REV-48, REV-66, REV-71, REV-74, REV-75, REV-76, REV-77,
REV-72, REV-73, REV-78, and REV-79, discharging VER-70, VER-71, QR-12,
FR-25, PHY-13, PHY-21, PHY-22, IF-03, VER-56, and VER-62 (at 10⁻⁸).

### Added

- **VER-70:** AST gate lint `nanopnp.validation.modularity.nan_permissive_gates` ensuring gate checks
  do not pass NaNs, with 38 comparisons rewritten to negated forms and six recorded exemptions (QR-12).
- **VER-71:** Case leaf taxonomy in `nanopnp.validation.case_leaves` classifying all 105 case leaves
  across seven kinds (`solve`, `solver`, `stage`, `post`, `fixed`, `checked`, `provenance`).
- `ModelDeclaration.unread` declaring unread leaves per model, with `pipeline.checks._check_unread`
  refusing cases that set unread leaves to non-default values (PHY-21).
- `materials.models.applies_part` and `pipeline.checks._check_correction_parts` refusing disabled
  correction parts where no fit exists (PHY-22), and `_check_driver` refusing `ionic_strength` on 1:1 salts (PHY-13).
- Consolidated root fixtures in `tests/conftest.py`: `cylindrical_pore_case`, `val05_frozen_case`,
  `as_yaml`, `reference_triangles`, `d10_figures`, and `exclusion_2wcd`.

### Changed

- **Breaking:** Retired `nanopnp/case/v1` and `nanopnp/case/v2` schemas entirely. Cases declare
  `schema: nanopnp/case/v0.5` (G6).
- **Breaking:** Models refuse unread case leaves set away from schema defaults (PHY-21).
- **Breaking:** The `pnp` model honours only `variable_density: false` and `inertia: false` (REV-42).
- **Breaking:** The load-time inf-sup check runs only when `numerics.elements.u` is read by the model
  and `physics.flow` is true (REV-66).
- **Breaking:** Stage 10's key carries `algorithm_revision` (`SOLVE_ALGORITHM_REVISION`, bumped by
  any change that moves a converged number) and the Newton record's `field_floor_ratio`, and a supplied
  charge field's artefact carries its `quadrature_order`; a solution stored by an earlier build misses
  and is solved again (REV-71, §5.3.2). The `-v` flag given before and after a subcommand adds up (REV-78).
- **Breaking:** `physics.variable_density: false` beside a density correction that applies no varying
  fit, and `physics.dielectric_gradient_forces: true` beside a permittivity correction with no
  concentration fit, are refused: each was recorded as a deviation and never applied (REV-73, PHY-22).
- **Breaking:** The models' `fixed_charge` is a `FixedCharge` (a density with the integration rule it
  is assembled with) and `fixed_charge_rule_order` is gone from the models and from
  `default_ladder`; a bare density is refused with a `TypeError` (REV-72, PHY-19).
- `exclusion_shell` refuses a non-finite profile coordinate with a `RegionGateError` naming the vertex
  (REV-79, QR-12).
- Stage-10 solve hashes re-recorded for `pnp-ns`, `pnp`, `pb`, and `pb-linear` under amended case
  variants, with fingerprints proven bit-identical to the unedited cases when unread checks are lifted (VER-56).
- Example 06 stage-7 keys pinned in `test_validation_identity.py` (REV-13).
- Per-ion Einstein ratios (Na⁺, Cl⁻) pinned to within 1e-3 in `test_corrections.py` (REV-23).
- The drawn slab is solved once per module in `tests/tier2/test_stern_layer.py` via `drawn_slab` fixture (REV-44).
- The number-stability golden is unchanged at 10⁻⁸ (VER-62).

### Migrating a case file to nanopnp/case/v0.5

Cases written for pre-release schemas update their schema identifier to `nanopnp/case/v0.5`:

- **Schema identifier:** Change `schema: nanopnp/case/v2` (or `v1`) to `schema: nanopnp/case/v0.5`.
- **Model unread leaves:** Ensure keys not read by the selected `physics.model` remain at their schema defaults. For electrostatic models (`pb`, `pb-linear`, `poisson`), omit fluid and correction blocks; for `pnp`, omit viscosity and density correction blocks.
- **PNP switches:** For `physics.model: pnp`, specify `variable_density: false` and `inertia: false` (or leave at default `flow: false`).

## [0.5.0-alpha.7] - 2026-10-08

WP41: the accuracy fixes (`SPECIFICATION.md` §4.4, §5.3.1 NOTEs on `inputs:`, `inputs.charge`,
`inputs.eps_r`, NUM-07, NUM-16; §8.2.9 I2, I4). Fixed charge assembly threads an explicit order-8
quadrature rule through all models; Newton converges on a per-field relative-update criterion
with an absolute residual floor; a supplied field's model frame is declared and checked against
mesh generation; the ionic-strength correction driver clamp is logged and counted; stabilisation
provenance is classified as operator keys so prose rewrites do not fail warm starts; electrostatic
models explicitly record stabilisation `none` and `LadderResult` refuses missing or non-mapping
entries. It resolves REV-06, REV-07, REV-08, REV-09, REV-17, and REV-26, discharging QR-03,
NUM-07, NUM-13, NUM-16, PHY-13, PHY-19, FR-25, FR-27, IF-05, QR-12, and VER-37.

### Added

- Optional `model_frame_centre_z_nm` field to `FieldDocument` (`nanopnp/field/v1`), exported by stage 7
  and validated on mesh generation (FR-27, IF-05, QR-12).
- `Measures.volume` and `Measures.integrate` accept explicit `rule_order` (NUM-07, PHY-19).
- `field_floor_ratio: float = 1e-6` in `NewtonSettings` (NUM-16).

### Changed

- **Breaking:** A case with a supplied fixed-charge field solves with its source assembled at order 8,
  matching the conservation gate to 4 × 10⁻¹⁶; the number-stability golden moves within D3's bounds
  (2.9 × 10⁻⁵ on `example-02-epnpns`, 2.7 × 10⁻⁵ on `example-02-classical`, 1.1 × 10⁻⁵ on
  `example-03-charged`; 10⁻⁸ elsewhere) (QR-03, PHY-19).
- **Breaking:** Newton convergence stops on per-field relative updates (`max_f ||δu_f|| / max(||u_f||, ρ max(||u||, 1)) ≤ rtol`)
  or absolute residual floor 10⁻¹²; the relative residual test `||R|| ≤ rtol ||R0||` no longer closes
  rungs; the golden moves within D5's bounds (1.6 × 10⁻⁶ on `2wcd-charged`, 6.8 × 10⁻⁷ on
  `example-03-charged`, 5.2 × 10⁻⁸ on `example-07`; 10⁻⁸ elsewhere) (NUM-16).
- **Breaking:** Electrostatic models (`poisson`, `pb`, `pb-linear`) record stabilisation `none`,
  `{}` and `create("none").provenance`. `LadderResult.stabilisation*` and per-rung records read
  without defaults, raising `ValueError` on missing or non-mapping entries (NUM-13, FR-25).
- **Breaking:** `model.stabilisation_provenance` is moved from `SPACE_KEYS` to `OPERATOR_KEYS`
  in `solve/state.py`; differences are recorded in the solution manifest rather than refusing
  valid warm starts (VER-37).
- Both golden stability re-pins applied to every recorded mesh under D3 and D5 bounds: the three
  `linux-x86_64` levels, and the darwin-arm64 and win32-AMD64 cylinder meshes from CI's printed
  records. Every walk's mesh-moved tolerance is unchanged.

## [0.5.0-alpha.6] - 2026-10-07

WP40: the stale refusals (`SPECIFICATION.md` §5.3.1 NOTEs on `inputs:` and `numerics.nonlinear`;
§8.2.8 H1, H8). Every refusal that schedules a feature names its requirement and either the
release that schedules it or that none does. It fixes `MOD-14` and discharges VER-67 and IF-02.
No number moves, and no stage key changes (VER-62).

### Added

- **VER-67**: `nanopnp.validation.modularity.tagged_releases` reads the tagged releases from this
  file's milestone headings, and `stale_release_literals` finds every non-docstring string of the
  package naming one; a Tier-1 test keeps the package free of them. `requirement_releases` and
  `release_pairing_mismatches` also find a string pairing one requirement with a release its row
  in §3.2 does not give.
- A Tier-1 test fails on an `inputs:` key the resolved case does not carry, `input_files` does not
  hash or no stage reads (VER-47).

### Changed

- **Breaking:** `inputs.mesh: artefact:` is refused when the case is resolved, so `nanopnp validate
  case` exits 3 on it where it exited 0; `run` refused it at stage 6 before, with the same exit
  code. The text names REV-62, deferred to v0.6.
- **Breaking:** The refusal texts of `inputs.mesh`, `inputs.charge` and `inputs.eps_r` named by
  store hash, of `numerics.nonlinear.strategy: hybrid` and of `numerics.nonlinear.damping:
  backtracking`, and the configuration reason of `numerics.mesh.backend`, name their requirement
  rather than a release that has shipped. Exit codes do not change (VER-47).
- Internal `pipeline.checks._UNCONSUMED_INPUTS` and `_UNREAD_CHARGE_KEYS`, both empty, are removed
  with their refusal loops. `validation.modularity.VERSION_LITERAL` matches any `vX.Y`.

## [0.5.0-alpha.5] - 2026-10-06

WP39: the backend registries (`SPECIFICATION.md` §5.1, §5.3.1, §5.5; §8.2.8 H5 to H7, H11, H12;
§8.2.9 I3). The mesher, linear solver and stabilisation mode each become a registry in uniform
shape; `numerics.mesh.backend`, `numerics.linear.solver` and `numerics.stabilisation` become
strings validated against them. It fixes `MOD-06`, `MOD-07` and `MOD-16`, asserts H6's target
acyclic `top` relation, and resolves REV-05, REV-36, REV-37 and REV-38, discharging VER-66,
QR-14, IF-03 and QR-11. `core/public.py` empties both upward layering lists. No number moves, and
no stage key changes (VER-62).

### Added

- **Backend registries**: `nanopnp.mesh.meshers` (`register_mesher`, `registered_meshers`,
  `create_mesher`), `nanopnp.numerics.linear` (`register_solver`, `registered_solvers`,
  `create_solver`), matching `nanopnp.physics.stabilisation`.
- **`nanopnp.core.public`** holds `__version__` and `PUBLIC` (REV-05).
- **Subpackage acyclicity**: VER-61 asserts that the `top` subpackage import relation has no
  components of more than one subpackage (H6).

### Changed

- **Breaking:** The JSON schema of `numerics.mesh.backend`, `numerics.linear.solver` and
  `numerics.stabilisation` is now `str` rather than a closed enumeration. Every valid document
  remains valid; unregistered values are refused by `check_document` and on validation (F4).
- **Breaking:** Internal `numerics.linear.AVAILABLE_SOLVERS` and `mesh.generate.gmsh_backend` are
  removed, and `mesh.generate.mesh_shape` moves to `mesh.meshers.mesh_shape` (IF-01, D2).
- **Stage-6 recipe:** a mesher whose settings name an entry every backend shares (`backend`,
  `wall`, `table`, `grading`, `gate` or `exclusion`) is refused rather than merged over it, which
  would key two different meshes alike.
- **Gmsh session cleanup:** A borrowed session leaves the caller's logger untouched (REV-36).
  Failure of `gmsh.initialize()` raises `GmshInitialisationError`, translated to
  `MissingExtraError` naming `gmsh` and the initialisation's own remedy (REV-37). Each undo step
  is recorded once its change is made and every one runs, in reverse order, so a session this
  module opened is finalised even when the setup fails, a borrowed session's model is never removed
  in place of one that was never added, and a cleanup failure is a note on the error in flight
  rather than raised over it (REV-38).

## [0.5.0-alpha.4] - 2026-10-06

WP38: the `io` split (`SPECIFICATION.md` §5.1; §8.2.8 H1, H6, H12; §8.2.9 I3). `io` is the base
layer, directly above `core`, and a new subpackage, `nanopnp.pipeline`, is the assembler above the
stages. It fixes `MOD-04`, `MOD-15`, the `io/case.py` part of `MOD-13`, and `MOD-03`, whose only
upward edge left is `cli -> nanopnp`. It resolves REV-03, REV-27, REV-54 and REV-63, extending
VER-45, VER-61, VER-64 and VER-65. No number moves, and no artefact key changes (VER-62).

### Added

- **`nanopnp validate case <file>`** loads and resolves a case and makes every check a run makes
  before it meshes, printing the model, the stabilisation and the stages a run would walk; a
  refusal exits 3 with a run's text. `--json` prints the same as an object (REV-27).

### Changed

- **A stage is handed the resolved case.** `StageInputs(case=…)` is `StageInputs(resolved=…)`, a
  `ResolvedCase` the assembler builds once, and `solve.state.restore` takes `resolved=`. Anyone
  implementing `Stage` reads `inputs.resolved` rather than resolving `inputs.case`.
- **`ResolvedCase.physics_model()` and `.model_declaration()` are removed.** The declaration and
  the essential boundaries are the fields `ResolvedCase.declaration` and
  `ResolvedCase.essential_boundaries`, and `physics.models.case_model(resolved)` builds the model.
- **`load_case` and `loads_case` refuse an inf-sup-unstable element pair**, and an unregistered
  model, stabilisation mode or linear solver, when the case is loaded rather than when it is
  resolved; the text is unchanged (NUM-03, IF-03). The desktop shell's commit refuses them too
  (QR-11). A document with an uninstalled correction or parameter file reports that first, alone.
- **`nanopnp run --upto X` walks the stages X reads, and no others** (REV-63): `--upto protonation`
  on example 07 is `case`, `structure`, `protonation`. `--upto materials` therefore no longer
  meshes or builds the charge. Each stage is handed only the artefacts it declares; `solve`
  declares `charge`, and `qoi` and `report` declare `mesh` and `charge` (FR-27, VER-64).
- **`pipeline.run.stored_upstream` takes `feeding=`**, the stage whose inputs it gathers (`"solve"`
  by default), instead of walking to `materials`.
- The solution-field names `POTENTIAL`, `VELOCITY`, `VELOCITY_AXIS`, `PRESSURE` and
  `PRESSURE_MEAN` live in `nanopnp.io.vocabulary` (REV-03). `physics.models` no longer exports
  `VELOCITY_AXIS` or `PRESSURE_MEAN`.
- Six of `PUBLIC`'s module strings move: `load_case`, `loads_case` and `resolve` are at
  `nanopnp.pipeline.case`, and `run_case`, `run_document` and `RunResult` at
  `nanopnp.pipeline.run`. Their meaning is unchanged, and `from nanopnp import …` is unaffected.
  The type-checker mirror is checked module by module (REV-54, VER-45).
- No import path is kept at an old location (IF-01: internal paths are not API):

  | Was | Is |
  |---|---|
  | `nanopnp.io.case`'s `load_case`, `loads_case`, `resolve`, `CaseStage`, `GRID_SPACING_RANGE_NM` | `nanopnp.pipeline.case` |
  | `nanopnp.io.case`'s `registry_options`, `options_at`, `PROFILE_KEYS`, `SMEARING_KEYS`, `PROTONATION_KEYS` | `nanopnp.pipeline.checks` |
  | `nanopnp.io.case`'s `ResolvedCase`, `ResolvedStructure`, `ResolvedProtonation`, `SOLVE_IRRELEVANT_PROVENANCE`, `parse_chains` | `nanopnp.io.resolved` |
  | `nanopnp.io.case`'s `UnknownCasePathError`, `FieldReference`, `field_at`, `case_fields`, `schema_default`, `field_description`, `field_bounds`, `value_at`, `substitute`, `with_profile`, `with_section`, `NEUTRAL_SECTIONS`, `SEQUENCE_INDEX` | `nanopnp.io.case_paths` |
  | `nanopnp.io.case.build_model` | `nanopnp.physics.models.build_case_model` |
  | `nanopnp.io.run` | `nanopnp.pipeline.run` |
  | `nanopnp.io.reproduce` | `nanopnp.pipeline.reproduce` |
  | `nanopnp.io.fields` | `nanopnp.post.export` |
  | `nanopnp.mesh.primitives`'s `POTENTIAL`, `VELOCITY`, `VELOCITY_AXIS`; `nanopnp.physics.models`'s `PRESSURE`, `PRESSURE_MEAN` | `nanopnp.io.vocabulary` |

## [0.5.0-alpha.3] - 2026-10-06

WP37: the cycle cuts outside `io`, the exit codes, and the backend guard (`SPECIFICATION.md`
§8.2.8 H1, H3, H6, H11). It fixes `MOD-05` of the modularity findings log and works toward
`MOD-03`, discharging VER-65 under QR-13 and extending VER-61. No number moves: the moves change no
arithmetic, and no artefact key changes (VER-62).

### Changed

- **A new subpackage, `nanopnp.numerics`, holds the solver kernel**, below the weak forms and the
  ladder (H11). Every module-scope import that pointed up the layer order outside `io` is cut, so
  the five-subpackage cycle `MOD-03` measured outside `io` is gone; only `cli -> nanopnp`, which
  closes no cycle, is left, for WP39. Nothing in `PUBLIC` moves, and
  no import path is kept at an old location (IF-01: internal paths are not API). Anyone who
  imported a moved module should import it from its new home:

  | Was | Is |
  |---|---|
  | `nanopnp.solve.gates` | `nanopnp.numerics.gates` |
  | `nanopnp.solve.linear` | `nanopnp.numerics.linear` |
  | `nanopnp.solve.newton` | `nanopnp.numerics.newton` |
  | `nanopnp.physics.measures` | `nanopnp.numerics.measures` |
  | `nanopnp.mesh.distance` | `nanopnp.physics.distance` |
  | `nanopnp.mesh.profile` | `nanopnp.geometry.profile` |
  | `nanopnp.materials.fields`, except `blend` and `nearest_solid_permittivity` | `nanopnp.charge.dielectric` |
  | `nanopnp.mesh.primitives.TOL_NM` | `nanopnp.geometry.tolerance.TOL_NM` |
  | `nanopnp.physics.models`'s `POTENTIAL`, `VELOCITY`, `VELOCITY_AXIS`, `CoupledBoundaries`, `DEFAULT_BOUNDARIES` | `nanopnp.mesh.primitives` (`physics.models` still re-exports the last three) |
  | `nanopnp.cli.errors` | `nanopnp.core.errors` (`nanopnp.cli.errors` is removed) |

- **The exit-code table and `classify` live in `nanopnp.core.errors`** (`MOD-05`), so the sweep
  runner, the example walker and the desktop shell no longer import the CLI. The codes are
  unchanged (VER-47).
- **`resolve_wall_size` and `case_debye_length_nm` take `permittivity_0`**, the case's
  `eps_r,f0`, as a keyword argument, so meshing reads no correction file of its own. Stage 6 and
  the mesh stage pass `resolved.electrolyte.permittivity_0`; a sweep plan reads the same number
  from the parameter file.
- `ResolvedCase.model_declaration()` returns the case model's declaration, beside
  `physics_model()`.

### Added

- **VER-65, the backend guard** (QR-13, H3): the subpackages that import NGSolve or Netgen, in any
  of the four kinds, equal the `backend:` list of `docs/project/modularity-layering.yaml`, twelve
  of them. A new one fails naming the module and the line; one that stops fails until the record
  shrinks.
- **VER-61's upward ratchet**: the module-scope edges pointing up the layer order equal the file's
  `upward:` list, so an import cut by moving it under `TYPE_CHECKING` cannot come back unnoticed.
  It holds the nine edges into `io`, which WP38 cuts, and `cli -> nanopnp`.
- **VER-61's deferred ratchet** (§8.2.8 H12): the edges pointing up the layer order from an import
  inside a function equal the file's `deferred_upward:` list, so a cut cannot come back as a
  deferred import (WP37 D12). It holds `gui -> nanopnp`. Every row of either ratchet names its
  finding.
- **The review register** (§8.2.8 H12): `docs/project/review-findings.md`, `REV-nn`, with
  `docs/project/review-items.md`, keeps what a work package's implementation or review leaves
  open until it is resolved. VER-63 checks it.
- **The commit gate's prose rule** treats `SPECIFICATION.md` and the findings reports as read by
  tests, so an edit to a ruling or a finding's heading runs VER-63 (REV-10). `CLAUDE.md` exempts
  `scipy` from the import rule and one `%` over a whole numeric array from the f-string rule
  (REV-21, REV-22).

## [0.5.0-alpha.2] - 2026-10-05

WP36: the stage protocol and the walk (`SPECIFICATION.md` §8.2.8 H1). It fixes `MOD-01`,
`MOD-02` and `MOD-12` of the modularity findings log, discharging VER-64 under FR-27 and IF-01.
Every walk computes what it computed before: the order, the keys and the work are unchanged
(VER-62).

### Changed

- **`nanopnp.Stage` gains `key(inputs)`**, returning the artefact `run` will produce without its
  payload. **Break:** a stage written outside the package must now define it. The case and
  materials stages define it too, and their `run` returns their `key`.
- **The walk reads each stage's facts from the registry.** `StageDescription` gains six required
  keyword-only fields: `takes_workspace`, `takes_store`, `key_is_artefact`, `weight`,
  `needs_section` and `optional_inputs`. `registered_stages()` descriptions and
  `nanopnp stage --list --json` carry them, an additive change. A description built by hand must
  now give all six.
- **A stage whose case drops one of its required inputs is not walked**, and naming it as the
  walk's target is refused, naming the input. `optional_inputs` lists the inputs a stage runs
  without; every built-in stage declares the ones a case can drop, so no built-in walk changes.
- **The walk runs the stages in registration order**, read by the new
  `nanopnp.core.stages.walk_order()`, with the case stage registered first. A stage registered
  later is walked after the built-in ones.
- **`register()` refuses more**: an input that is neither `case_path` nor a stage registered
  before it, a progress weight that is not finite and positive, and an optional input that is not
  one of the stage's inputs. A walk refuses a `needs_section` that names no case section.

### Removed

- `nanopnp.io.run`'s `PIPELINE`, `PAYLOAD_FREE`, `STRUCTURE_STAGES`, `WORKSPACE_STAGES` and
  `STORE_STAGES`. They were never in `PUBLIC` (IF-01), but anyone who imported them should use
  `walk_order()` and `describe(name).<fact>` instead.

### Added

- **VER-64, stage conformance**: every registered stage defines `describe`, `key(inputs)` and
  `run(inputs, *, progress, cancel)`, read from the syntax tree. Each declared fact is checked
  against the code it describes, and `io/run.py` writes no collection of stage names.
- **The `PUBLIC` mirror check** (`MOD-12`, under VER-45): `nanopnp.PUBLIC` and its
  `TYPE_CHECKING` re-exports name the same set.

## [0.5.0-alpha.1] - 2026-10-05

WP35: the modularity exploration (`SPECIFICATION.md` §8.2.7 G1, G4, G10). It measures the
architecture against FR-16, FR-20, FR-27, QR-13, QR-14, ADR-002 and ADR-005 and logs 17 findings,
`MOD-01` to `MOD-17`, for the author to rule. It refactors nothing: every file of `src/`, `data/`
and `examples/` computes as it did at `v0.4.0`.

### Added

- **The modularity report** (`docs/project/modularity.md`) and its findings log
  (`docs/project/modularity-findings.md`), with the measurements page generated from
  `nanopnp.validation.modularity` on every documentation build.
- **VER-61, the layering guard**: the subpackage import relation, read from the syntax tree in
  four kinds, equals `docs/project/modularity-layering.yaml` in both directions, and module-level
  imports stay acyclic.
- **VER-62, the number-stability golden**: seven gated walks assert their quantities against
  values recorded on `v0.4.0`'s tree, keyed by the deployed mesh: at 10⁻⁸ relative on a recorded
  mesh, and at a tolerance derived from the measured spread between recorded meshes (capped at
  10⁻³) on an unseen one, except in the pinned reference environment, where an unseen mesh fails.
  `nanopnp.validation.stability` holds the mechanism for any later golden. The largest drift per
  walk, and which comparison it answered, is printed at the end of a run.
- **NumPy's SIMD dispatch is capped at `X86_V3`** in CI and the commit gate
  (`NPY_DISABLE_CPU_FEATURES`), so every x86-64 Linux leg deploys the same PDB-derived mesh.
- **VER-63, the findings-log check**: every `docs/**/*findings.md` is parsed and checked, and a
  log whose header says `closed` refuses a row that is not terminal.

### Changed

- `.github/scripts/prose-only.sh` reads a `*findings.md` as not prose, so a ruling edit runs the
  check that reads it.

Discharges VER-61, VER-62 and VER-63.

## [0.4.0] - 2026-10-04

**Phase 3, the charge pipeline.** A PDB entry, or a supplied PQR, is protonated with PDB2PQR and
PROPKA, and its fixed charge is deposited on the deployed mesh as the closed-form azimuthal mean of
each atom's Gaussian. It is gated for conservation per plane and handed to the solve. The run goes
from a structure to a current. VAL-06 compares our Poisson with APBS on 2WCD: max 0.41 %, rms
0.10 % and axis 0.23 %, against 3 %, 1 % and 1.5 %. The phase closes on its Tier 1 and Tier 2
evidence. The ensemble legs that need the author's archive are carried to Phase 6
(`SPECIFICATION.md` §8.2.5 E1, §8.2.6 F1). The end-of-phase report is in
[docs/plans/phase-3-charge-pipeline.md](docs/plans/phase-3-charge-pipeline.md).

The release gathers nine work packages, each tagged except the last:

- WP26, the physics-model interface (`v0.4.0-alpha.1`);
- WP27, protonation and the PQR artefact (`v0.4.0-alpha.2`);
- WP28, fixed-charge deposition on the deployed mesh (`v0.4.0-alpha.3`);
- WP29, VAL-06 against APBS (`v0.4.0-alpha.4`);
- WP30, the derived dielectric and the ion-exclusion shell (`v0.4.0-alpha.5`);
- WP31, the charge pipeline in the desktop shell (`v0.4.0-alpha.6`);
- WP32, documentation increment 3 and example 07 (`v0.4.0-alpha.7`);
- WP33, the test suite's duration (`v0.4.0-alpha.8`);
- WP34, the phase close, described here and tagged `v0.4.0` alone (§8.2.5 E5).

### Added

- **A golden's case identity names a deposited charge and a derived `χ`** (VAL-03; §8.2.5 E3;
  closes OPN-07). A depositing case's identity carries the structure, the protonation and the
  kernel's parameters. A deriving case's carries the dielectric transition and the structure, and
  a non-zero `charge.exclusion_offset_nm` now moves any case's. pH, force field, titration,
  `smearing.sharpness`, the structure and a PQR's contents move it. The export lattice's spacing,
  the element order and the protonation gates' tolerances do not. Non-producer identities, every
  solve key and `fields.charge` are unchanged. `nanopnp validate case-hash` on a `structure:` case
  needs the `structure` extra and its files on disk; `validate compare` and `export-golden` read
  the structure and protonation the run recorded instead.
- `Measures.weight_extra_order`, the seam NUM-07's measurement runs through. No case key reaches it,
  and at 0 every form is unchanged. The measurement is in the NUM-07 NOTE. One extra quadrature
  order for the `r` weight leaves VER-18's finest-pair rates unchanged and lowers its error at fixed `h`. On
  example 05 it moves no compared number by more than 7.6 × 10⁻⁸ relative. Phase 6 decides.
- `SPECIFICATION.md` §8.2.5 (E1–E5) and §8.2.6 (F1–F6), and the Phase 3 end-of-phase report.

### Changed

- **The phases are re-planned** (§8.2.6). Phase 4 is polish and user testing (v0.5), opened by an
  exploration of the architecture's modularity. Phase 5 is the graphical interface (v0.6). The
  validated release is Phase 6 (v0.7). Stable v1.0 follows, its content the author's (OPN-08). The
  repository's mentions of the validated release now say v0.7 and Phase 6, including FR-21's
  `geometry.analyte` refusal, which now names v0.7.
- **The case schema and the public API may change in any phase before v1.0** (§8.2.6 F4,
  superseding "stable from v0.2 onward"). Each break will be listed here with its migration.
- `with_section` stays out of `nanopnp.PUBLIC`. Phase 4's API pass reviews it with the rest of the
  surface.

### Removed

- `.github/scripts/renumber-tags.sh`, which ran once on 30 September 2026. Re-run after Phase 4's
  first tag, it would retire live tags. `.github/renumbered-tags.txt` is removed too: `release.yml`
  now checks `CITATION.cff` against the version only for the highest milestone tag, so
  re-dispatching an older milestone's release no longer needs a list of exceptions (§2.7,
  Versioning NOTE). The stray retired tag `v0.5.0-alpha.5` is deleted from origin, and the
  `v0.5.0` names are now Phase 4's (§8.2.5 E2, §8.2.6 F2).

## [0.4.0-alpha.8] - 2026-10-03

WP33: the tier 1–2 suite's duration cut without losing a check, under the §7.6 NOTE on a gated
test's runtime. Serial test time 1,508.9 s → 1,334.5 s, and the four-worker wall 458 s → 394 s.
No kept test's tolerance or oracle changes; seven duplicated tests are removed and one recorded
test is `slow`, as listed below.

### Changed

- **Planning a sweep is faster**: the §8.3 reference sweep's 3,675 members plan in 7.0 s rather than
  12.3 s. A correction file's cached parse is copied structurally rather than with `copy.deepcopy`,
  and a case field's validator is built once per declared type (VER-36's assertions unchanged).
- **The shared 2WCD seed runs to the default-size mesh**, and the protonation starts from stage 1,
  so under `pytest-xdist` PROPKA no longer waits for the density. Each seeded module asserts the
  stages it reads `cached`.
- **VER-58 computes each mesh, lattice and closed form once** and is split into two files; the
  ClyA reference mesh is generated once per session; the duplicated climbs of the stabilised-mode,
  solution-state and VER-55 files are shared or coarsened where their gates allow (VER-34, VER-42,
  VER-49, VER-55, VER-58, VER-59, NUM-12, NUM-14, NUM-17).
- **`uv run pytest` is the development selection**: it leaves out the 54 `extended` tests, the
  executed examples and the 2WCD walks, and runs in 168 s on four workers rather than 394 s.
  `uv run pytest --extended` is the whole of Tiers 1–2. CI runs it on every push, on every leg, and
  so does `.claude/hooks/gate.sh run` before a skill pushes; the commit hook runs the development
  selection (§7.6 NOTE, VER-46).
- VAL-05's recorded frozen-case conductance on 2WCD is `slow`.

### Removed

- Seven Tier-1 tests whose claim another test on every push already gates on the same input: a
  refactor pin on the wall size, the profile fixture's digest and conditioning, the packaged
  correction file's existence, the example-tag literal, and two schema-constant checks.

## [0.4.0-alpha.7] - 2026-10-03

WP32: documentation increment 3, the charge pipeline documented and executed (QR-15 in part), the
seventh package of Phase 3 and its phase criterion 7. No weak form, gate, tolerance or case key
changes. Stage 7's artefacts stop recording wall-clock time, and their schema versions move to v2.

### Added

- **The guide page *From a structure to a charge*** (`docs/guide/charge.md`): protonation and its
  keys, `inputs.pqr` and the `.pqr` export, the deposit and why it is not interpolated, the
  conservation report and where to read it, the two FR-15 switches, and which models take a charge.
  *Charge and permittivity fields* becomes the supplied-field page, and the case-file, provenance,
  concepts, geometry, desktop and physics-model pages link the new one.
- **Example 07, from a PDB entry to a charged run** (VER-46). The prepared 2WCD entry walks every
  stage to an ePNP-NS solve, exports its PQR and its charge, deposits the same charge from the PQR
  supplied back, turns both FR-15 switches on, and shows the exported lattice refused by stage 7's
  quadrature-agreement check when supplied back through `inputs.charge`. Its test asserts `Q_net`
  against the PQR's charge column, each conservation leg and worst plane against its tolerance,
  `t₊ > ½`, the FR-23 route agreement, the PQR's byte-identical deposit, and the switches'
  deviations.
- **The examples' executor mirrors a sibling example** that a command names by `../`, so example 07
  runs example 06's `prepare.py` rather than a copy of it.

### Changed

- **Stage 7 records no wall-clock time** (VER-23). `deposit.npz`, the `charge-grid` summary and the
  `charge` summary drop their `seconds`; the timings go to the log, and the stage's total stays in
  the run record. The same deposit now writes the same bytes, and two charged runs of one case share
  a manifest. Stage 7's schemas move to `nanopnp/fields/v2` and `nanopnp/charge-grid/v2`, so an
  entry stored before this release is a cache miss and stage 7 runs once more, rather than serving
  the old timings into a new manifest.
- **The case editor's bounded numbers** (VER-60). A bounded integer is a `QSpinBox` stepping by
  one, and a field that admits `null` is never a spin box, which cannot say "unset". No field of
  today's schema changes widget.

### Removed

- `ChargeWidget.build` and its `store` argument, which nothing called: the window builds the charge
  through the Geometry tab and calls `follow`.

## [0.4.0-alpha.6] - 2026-10-02

WP31: GUI increment 3, the charge pipeline surfaced in the desktop shell (IF-09, QR-10, QR-11), the
sixth package of Phase 3 and its phase criterion 6. No weak form, gate, tolerance, stage key or case
key changes; every number the shell shows is read from a stage's own artefact.

### Added

- **The Charge tab.** *Build charge* runs stages 1 to 7 (`upto: charge`) on the Geometry tab's run
  control, and the tab shows four panes. *Protonation* shows the titratable groups of each frame,
  with applied charge, pKa, expected charge, the recorded unapplied states, per-chain differences
  and warnings. *Charge map* shows the export lattice in the model frame, reduced by
  trapezoid-weighted block means that keep its recorded charge to 10⁻¹², on a diverging scale
  centred on zero, with the worst planes marked. *Deployed field* shows the coefficient the solve
  assembles, ρ or the derived χ, drawn by the render child into `viewer/charge.*` and
  `viewer/chi.*`. *Conservation* shows each leg against its recorded tolerance, and a leg not run
  with its reason.
- **Bounded numbers and *Add section* in the case editor.** A number whose schema declares both
  bounds, such as `charge.ph`, is a spin box over exactly that range, and it writes only on an
  edit. *Add section* writes an empty section, for the sections whose empty form resolves exactly
  as their absence (`io.case.NEUTRAL_SECTIONS`, today `charge` alone).
- **The probe carries PDB2PQR and PROPKA** (RSK-13, CON-11). `--selftest` protonates
  `GLU 18`–`LEU 26` of 2WCD chain A, shipped as `data/structures/2wcd-a-18-26.pdb`, at pH 2 and
  pH 8, and requires 0 e and −3 e. A missing PDB2PQR data tree fails naming `pdb2pqr`. Charges that
  ignore the pH, or a missing `propka.cfg`, fail naming `propka`. The licence notice gains both,
  and PDB2PQR's own dependencies.
- **VER-60.** The views, the render child and the probe at Tier 1 on a charged tube and the 2WCD
  fragment, and the prepared 2WCD dodecamer at Tier 2: its picture carries −60 e to 10⁻¹², its
  conservation view is its record, and its protonation view shows −60 e, no chain difference and
  `CYS 285` and the `LYS 8` N-terminus unapplied in every chain.

### Changed

- PROPKA, MDAnalysis and GridDataFormats are collected into the bundle as source files rather than
  into its module archive, so that each LGPL component can be replaced in place (ADR-004's
  packaging NOTE).
- The IF-09 vocabulary check matches `propka` only as a string literal, and gains `CHARMM`,
  `PEOEPB` and `SWANSON`.

## [0.4.0-alpha.5] - 2026-10-02

WP30: the dielectric field and the ion-exclusion shell (FR-15), the fifth package of Phase 3. Both
switches stay off by default, the validated model, and at 0 every key and record is unchanged.

### Added

- **The ion-exclusion shell** (`charge.exclusion_offset_nm`, `a`). Stage 5 dilates the profile by
  `a` with round joins, closes it by `2h_c`, fills and records any pocket it encloses, resamples
  its ring at arc length near `h_c`, and gates the ring. The shell is a fourth domain, `exclusion`, carved against an unchanged membrane. `wall`
  moves to its outer surface, so the no-slip and no-flux surfaces and the PHY-02 distance source
  move with it. Its seams are `interface`. It is meshed at the wall size, and on netgen each of its
  `wall` edges is cut into `⌈L/(1.1 h)⌉` equal segments, so it meshes at every wall target the
  salt range resolves to, 3 M included. An offset that closes the
  constriction is refused naming the z interval, and so is an outer surface deeper than
  `max(h_c²/a, a/100)` inside the offset.
- **The derived solid fraction** (`charge.dielectric_transition_nm`, `δ`). Stage 7 builds
  `χ = S(s/δ + 1/2)`, a C¹ cubic step over the signed distance to the profile's water-facing part,
  on a `δ/20` lattice, with every solid but the protein held at 1. It is gated by VER-30's range
  and registration gates, and the solve, the restore and the export read it from stage 7's
  artefact.
- **VER-59.** The goldens of the zero-key case, recorded before the code changed
  (`tests/tier2/test_exclusion_keys.py`). The shell's geometry and refusals, and the dielectric's
  step, gates and refusals, at Tier 1. Gauss's law across a generated shell on a cylindrical tube at
  Tier 2, to 1.3e-4 against 1 % (`tests/tier2/test_exclusion_stern.py`). VER-31's slab rebuilt from
  a generated shell. 2WCD with the shell meshed at 0.15 M and at 3 M, and with both switches walked
  to stage 12.

### Changed

- `exclusion`'s mean `χ` is held below 1/2 rather than 0.1, for a supplied `χ` as for a derived
  one (VER-30).
- The case refuses either key beside `inputs.mesh` or without a profile, `δ` beside
  `inputs.eps_r` or a model declaring no solid fraction, `0 < δ < h_c` and `0 < a ≤ 2h_c`. The
  "not delivered" refusal of the two keys is gone.

## [0.4.0-alpha.4] - 2026-10-01

WP29: VAL-06, Poisson against APBS, the fourth package of Phase 3 and the third leg of its gate.

### Added

- **VAL-06's driver**, `nanopnp.validation.apbs`. It gives APBS 3.4.1 our electrostatic problem
  as maps on one cubic grid. Stage 7's export lattice goes on as hat weights, conserving its charge
  and first moments to round-off. The assembled permittivity goes on as three staggered maps, each
  edge the harmonic mean of eight samples. Our solution goes on the box faces (`bcfl map`). The
  driver runs APBS and samples both potentials on the probes: nested-grid nodes in the fluid, at
  least 0.3 nm from every solid and 0.4 nm inside the faces. A box that would cut the charge is
  refused, naming the face. An APBS run that fails or hangs is named, with the end of its log.
- **The gated leg** (`tests/tier2/test_val06_2wcd.py`). `poisson` is solved at `P2` and `P3` on
  the protonated 2WCD and compared with APBS at 0.1 nm. The refinement budget (APBS at 0.1 against
  0.2 nm, plus ours `P3` against `P2`) must lie within half the tolerance, and the charge must
  move the probes by at least 10 `τ_rms`, before the agreement is read. The tolerance is 3 % max,
  1 % rms and 1.5 % on the axis, and 2WCD measures 0.41 %, 0.10 % and 0.23 % (`SPECIFICATION.md`
  §7.4, the NOTE on VAL-06). The report is written as JSON.
- **A closed-form benchmark** (`tests/tier2/test_val06_ring.py`): a Gaussian ring in a grounded
  dielectric sphere, summed as a three-region Legendre series. APBS and our `P2` are each held to
  half the tolerance of it, and eight broken constructions of the maps must each exceed that.
- Under `-m slow`: the recorded leg, with APBS's own `spl4` charge and `smol` surface from the PQR
  and our membrane imposed, compared per probe ring. Also a focused 0.05 nm grid, which measures
  APBS's order at 1.6 (`knowledge/07-software-stack/03-charge-and-electrostatics.md`). At Tier 3, recorded: the ClyA-AS ensemble from the
  archived PQRs (`tests/tier3/test_val06_archive.py`).
- The test-only dependency group `apbs` (`apbs-binary` 3.4.1.1 on Linux x86_64 and macOS), a
  default group so that the gate runs VAL-06. It never reaches a wheel (CON-07).

### Changed

- CI sets `NANOPNP_REQUIRE_APBS=1` on every leg but Windows, so VAL-06 fails rather than skips
  where the wheel exists. Windows has none, and skips by name under `-rs`.
- The driver's three refusals (`BoxError`, `ApbsError`, `Val06Error`) exit 4, as gates. The
  VER-32 enumeration now counts `AssertionError` as a root, which it had missed.

## [0.4.0-alpha.3] - 2026-10-01

WP28: fixed-charge deposition on the deployed mesh and its gates (FR-13, FR-14, QR-03's producer
path; retires RSK-08), the third package of Phase 3.

### Added

- **Stage 7 deposits the fixed charge.** The `charge` stage sums PHY-16 step 5's closed-form
  azimuthal mean of each atom's 3D Gaussian over the `protonation` artefact's atoms and frames, on
  a 0.005 nm (r, z) export lattice in the model frame, each atom renormalised to its own charge. It
  deposits the sum on the deployed mesh by `r`-weighted L² projection, as element-wise
  polynomials of the potential's order, so the assembled source is the lattice's integral against
  every test function (PHY-16 NOTE on the deposition, VER-58).
- **Its gates**: the producer leg (lattice against `Q_net`), the consumer leg (mesh against
  lattice), the quadrature agreement and the boundary ring, and the cumulative charge below 12
  planes compared with the source atoms in closed form, for the lattice and for the mesh, each at
  10⁻³ (VER-01, VER-02; §4.4 NOTE on the producer path). Lattice charge falling on no element, or
  less than half of `Σ|q_i|` centred in the solids, is refused naming its location or the share and
  the frame shift (QR-12).
- The lattice is its own cached artefact, `nanopnp/charge-grid/v1`, keyed without the mesh, so a
  change of mesh size or element order re-deposits without re-summing.
- `nanopnp stage charge CASE --export X.yaml` writes the lattice as a `field1` document and its
  `.npz`, which reads back through `inputs.charge` to the same digest; `.dx`, `.mrc` and `.ccp4`
  write the grid (IF-05).
- The manifest's Charge group records `Q_net`, the conservation report, the solid share, each
  material's charge, the lattice and deposit sizes, and the timings (FR-25).

### Changed

- **A `structure:` or `inputs.pqr` case solves charged.** Where the case protonates and its model
  declares `fixed_charge`, a walk runs `protonation` and `charge`; otherwise the manifest records
  them as not run, with the reason (WP27 D3 retired). `inputs.pqr` beside a model without a fixed
  charge is refused naming the model.
- The solve, the restore of a solved state and the `rho_fixed` export read a deposited charge only
  from stage 7's artefact; a producer case handed none is refused naming stage 7. The stage-7
  artefact names the `protonation` and `charge_grid` artefacts among its inputs.
- `charge.smearing.sharpness` is read, a switch whose validated default is 0.5, and
  `charge.smearing.grid_spacing_nm` a configuration value; a spacing above half the narrowest
  kernel width is refused naming the atom. `charge.smearing.axis_cutoff_nm` away from its default is
  refused naming PHY-18, and either smearing key is refused beside `inputs.charge` or where the case
  has nothing to deposit.
- The PHY-16 NOTE on the reference's 2D construction is corrected: the two constructions differ
  pointwise at first order in `w_i/r_i`, odd about each atom, and carry the same charge and z-marginal.

## [0.4.0-alpha.2] - 2026-10-01

WP27: protonation, the PDB2PQR driver and the PQR artefact (FR-12; adds to IF-03, FR-27, QR-12),
the second package of Phase 3.

### Added

- **A `protonation` stage**, the first half of stage 7, runs PDB2PQR 3.7 with PROPKA on every frame
  of stage 1's ensemble with PHY-16 step 3's flags at `charge.ph` and `charge.forcefield`, and emits
  a per-frame atom table in stage 1's frame: each atom's charge and radius, `Q_net` per frame, and
  every titratable residue's charge, histidine tautomer and PROPKA pKa. A state PDB2PQR cannot apply
  under CHARMM, `CYS 285` of 2WCD and a terminal pKa among them, is recorded as unapplied, derived
  from PROPKA's groups and never from the log (PHY-16 step-3 NOTE). It shares the number 7 with
  `charge`, so stages 8 to 12 keep their numbers (§5.2). Until WP28's deposition reads it, a walk
  runs it only when it names it, as `nanopnp stage protonation` (VER-57).
- Each frame is cached under its own key, the digest of the heavy-atom PDB PDB2PQR is given, so a
  changed frame selection re-protonates only the frames it adds. PDB2PQR and PROPKA's warnings are
  collected, counted and logged once each.
- **`inputs.pqr` runs**: a PQR of one frame, or one `MODEL` per frame, read by PDB2PQR's fixed
  columns with a whitespace-separated fallback, and refused naming the line where the two disagree.
  Beside `structure:` each frame is registered to its stage-1 frame to 0.01 Å, and a frame count,
  a residue or a frame that does not match is refused naming the frame. It needs no extra.
- `nanopnp stage protonation CASE --export X.pqr` writes the artefact as a PQR in stage 1's frame,
  which supplied back through `inputs.pqr` gives the atom table bit for bit (IF-02 export NOTE).
- The manifest's Charge group records the protonation: `Q_net` per frame beside the structure's
  `variant`, the force field, pH, titration, PDB2PQR and PROPKA versions, the unapplied states, the
  radii checked against the stage-2 CHARMM table, and the registration. PROPKA's version is
  recorded among the distributions.

### Changed

- `charge.ph` is a number in [0, 14], and `charge.forcefield` one of `CHARMM`, `PEOEPB` and
  `SWANSON`: AMBER, PARSE and TYL06 give charged atoms a zero radius. `charge.titration` and
  `charge.forcefield` are switches whose validated defaults are `propka` and `CHARMM`, listed as
  deviations when set otherwise.
- A case carrying `charge:` resolves. `charge.ph` away from its default is refused beside
  `titration: none`; a protonation key away from its default is refused beside `inputs.pqr` or
  `inputs.charge`, or where the case has nothing to protonate; and `charge.smearing`,
  `charge.exclusion_offset_nm` and `charge.dielectric_transition_nm` away from their defaults are
  refused naming the stage that will read them (WP28, WP30).
- A protonation gate exits 4; a malformed or mismatched `inputs.pqr` exits 3 (IF-02).

## [0.4.0-alpha.1] - 2026-09-30

WP26: the physics-model interface (FR-20, QR-14), the first package of Phase 3.

### Added

- **A model is one class and a declaration.** `register_model(name, builder, declaration)`
  registers a model with a `ModelDeclaration` readable before anything is built: the options its
  builder takes, the switch values it honours, whether it carries solids, which supplied
  coefficients it accepts, whether it reads the PHY-02 distance field, the continuation strategies
  it admits, the quantities it provides, and whether it solves transport. Case validation, the
  mesh gate, the solve, stage 11, the IF-07 export and the GUI read the declaration and the built
  model's members, and no longer the model's name or class (§5.4.3 NOTE, VER-56).
- `PhysicsModel`, `TransportModel`, `ModelDeclaration`, `register_model` and `registered_models` are
  public (IF-01).
- **`poisson` runs from a case file**: electrostatics over the whole domain with the membrane and
  protein at their `physics.solid_permittivities`, the fluid at `ε_r,f⁰`, and `inputs.charge` and
  `inputs.eps_r` accepted. It is the configuration VAL-06 compares with APBS (PHY-21 NOTE).
- **`pb` and `pb-linear` run from a case file** on a mesh with no solid domain, with the Debye
  length of the case's own salt, temperature and `ε_r,f⁰`. A salt that is not symmetric
  monovalent is refused (FR-19).
- A developer page, *Adding a physics model*, walks `poisson` through the interface.

### Changed

- `nanopnp.physics.models.register(name, builder)` is replaced by
  `register_model(name, builder, declaration)`: a model cannot be registered without saying what it
  admits. A builder must return a model under the name it is registered by, and only `epnp-ns` and
  `pnp-ns`, the models the NUM-18 ladder ends at, may admit `numerics.continuation: default_ladder`.
- Every refusal a declaration makes names the model, the key and the values or models that are
  admitted. `pnp` admits `numerics.continuation: none` only, as §6.5 already required. An
  `outputs:` word the model does not provide is refused when the case is resolved rather than at
  stage 11: `pnp` does not provide `eof_rate` or `analyte_force`, and the electrostatic models
  provide no quantity (`outputs: []` or `[fields]`).
- For a model without solids, a mesh carrying a solid domain is refused naming the model and the
  domain, rather than asking for a `solid_permittivities` entry the case would then refuse; a case
  that generates its mesh, which always carries a membrane and a protein, is refused when resolved.
- The stage-10 key of every model runnable before this release, the model of every rung of the
  NUM-18 ladder, and the coupled models' stage-11 scalars on the quick-start case are unchanged,
  the scalars bit for bit (VER-56).

### Fixed

- A `pnp-ns` case that left its corrections on, the schema default, solved and was then refused at
  stage 10: whether the distance field is read was asked of the case's electrolyte, which `pnp-ns`
  overrides to `none`. It is now asked of the model the case builds, the rule each ladder rung
  already followed, so such a case stores and restores its state, and its results equal the same
  case with every correction written as `none`, bit for bit. No stored state is affected, because
  this configuration never stored one.

## [0.3.0] - 2026-09-30

**Phase 2, the geometry pipeline.** A PDB entry or an MD trajectory becomes a gated mesh by six
stages: alignment on the Cₙ axis, a smeared density map, the reduction to (r, z), the contour, the
region and the mesh, on netgen or the optional Gmsh backend. Each stage stores a content-hashed
artefact, can be exported and hand-edited, and is shown in the desktop shell. VAL-05 compares the
generated ClyA geometry with the published reference polygon. The 2WCD leg passes on every push.
The ensemble leg passes on the constriction radius (−0.039 nm) and the rms (0.089 nm), and misses
ε_G at −5.56 % against 5 %. The author waived that miss (`SPECIFICATION.md` §8.2.4 D7), and the
tolerance is unchanged. The end-of-phase report is in
[docs/plans/phase-2-geometry-pipeline.md](docs/plans/phase-2-geometry-pipeline.md).

The release gathers nine work packages, each tagged, each with its own entry in this file:

- WP17, case schema v2 and the Python 3.11 floor (`v0.3.0-alpha.1`);
- WP18, structure ingestion, alignment and the Cₙ axis (`v0.3.0-alpha.2`);
- WP19, the density map and the reduction to (r, z) (`v0.3.0-alpha.3`);
- WP20, contour extraction, conditioning and its gate (`v0.3.0-alpha.4`);
- WP21, CAD assembly and meshing from a profile (`v0.3.0-alpha.5`);
- WP22, VAL-05 against the reference geometry (`v0.3.0-alpha.6`);
- WP23, the optional Gmsh mesher backend (`v0.3.0-alpha.7`);
- WP24, the geometry pipeline in the desktop shell (`v0.3.0-alpha.8`);
- WP25, documentation increment 2 and example 06 (`v0.3.0-alpha.9`).

### Added

- The Phase 2 end-of-phase report, and `SPECIFICATION.md` §8.2.4 D7, which closes the phase.
- The Phase 3 delivery plan, `docs/plans/phase-3-charge-pipeline.md` (WP26–WP32), with the author's
  rulings recorded as §8.2.4 D2–D5. These cover the closed-form charge kernel deposited on the
  deployed mesh, VAL-06 against APBS, per-frame protonation and the exclusion shell.
- VAL-16 and VAL-17: Tier 3 compares the paper's published current–voltage relationships and
  in-pore averages, and that comparison gates v1.0 (§8.2.4 D6).
- `.github/renumbered-tags.txt` and `.github/scripts/renumber-tags.sh`, which re-create the retired
  tags under their new names.

### Changed

- **Versions are renumbered so that the minor version names the phase** (§8.2.4 D1). Phase 1's
  `v0.5.0` is now `v0.2.0`, and Phase 2's `v0.9.0-alpha.N` are now `v0.3.0-alpha.N`. `release.yml`
  skips its `CITATION.cff` check for a renamed tag.
- The COMSOL field comparison, VAL-01 to VAL-04, is kept but no longer required. The export
  contract says so.
- `SPECIFICATION.md` §2.6 and CON-09: PROPKA is LGPL-2.1, not BSD.

### Fixed

- `Z_MD`, the MD structure's Cα centroid that registers 2WCD axially, is 5.655 nm, not 5.63 nm. The
  old constant included residue 7, and the ensemble measures 5.6553 nm over residues 8–292. The 2WCD
  leg's ε_G moves from −8.08 % to −8.49 %, and example 06's `prepare.py` places the centroid at the
  corrected height (VAL-05, WP22 D6).

## [0.3.0-alpha.9] - 2026-09-29

WP25: documentation increment 2, the geometry pipeline (Phase 2 criterion 5). The tag also
carries the fixes of CODE_REVIEW_003, which merged after WP24.

### Added

- `nanopnp stage <name> <case> --export PATH` writes the artefact a stage stored, in the format
  the suffix names: the aligned ensemble as a PDB with a DCD beside it; the density map as `.npz`,
  OpenDX or CCP4/MRC; the reduced map as `.npz`; the stage-4 profile and a stage-6 mesh byte for
  byte. A stage or suffix it does not write exits 2 before any stage runs, and a failed write
  leaves no file. No key moves (the IF-02 export NOTE, IF-05, VER-32).
- Two user-guide pages: *Structures and trajectories*, for stage 1, and *From a structure to a
  mesh*, for stages 2 to 6, the membrane's registration, hand edits and exports (QR-15 in part).
- Example `06-pdb-to-mesh`. The deposited 2WCD entry is refused by stage 1's orientation gate; a
  preparation script that uses no nanopnp code orients it; the prepared entry is walked to a gated
  mesh, its artefacts are exported, and the exported profile meshes to the same mesh again as a
  supplied input. Executed at Tier 2 (VER-46).
- The example executor's `refused` tag: every command of such a block must exit `4`, the gate
  class, and a command that exits otherwise fails naming both codes (VER-46).

### Changed

- **The density map's OpenDX and CCP4/MRC files are in ångströms** (§8.2.2 B10), the unit
  molecular viewers read and the one the PDB export is in. `DensityMap.read` converts back to nm.
  A map exported by an earlier version is in nm and must be exported again. The `.npz` and the
  `(r, z)` field grids stay in nm (IF-05, VER-49).
- `DensityMap.read` names the GridDataFormats reader instead of letting it guess from the
  extension, which it could not do for `.map` (IF-05).
- The getting-started page lists all four extras, `structure` and `gmsh` included.

### Fixed

Findings of [CODE_REVIEW_003](docs/code_reviews/CODE_REVIEW_003.md), the Phase 2 review. CR-1 to
CR-7, CR-9, CR-11 and CR-13 each have a regression test that fails on the previous code.

- A run or build child that dies without reporting (the OOM killer, a fault in a compiled
  library) now settles the run as `failed`; the Run and Geometry tabs no longer stay locked
  (CR-1, FR-27).
- A truncated walk (`nanopnp run --upto`, **Build geometry**) writes its own run directory
  and no longer replaces the run record of a full run of the same case (CR-2, QR-08, FR-25).
- `structure.ensemble.frames.last_ns` keeps its inclusive window on DCDs whatever the sign of
  the float32 timestep's rounding error (CR-3, FR-01).
- Stage 5 accepts a step whose flat edge lies on a bilayer plane; the §5.2.1 NOTE on the
  membrane junction says so (CR-4, FR-09).
- `read_plan` re-derives each point's id and the plan hash, and refuses an edited plan (CR-6).
- `run_case` reads the case file once (CR-10); `load_profile` reads a `Path` as a path whatever
  its suffix (CR-11).
- A sweep plan records the content hash of every input file its points name and keeps it in its own
  hash. Building a member refuses a file that has changed or gone, naming the path and both
  digests. **Existing plan files must be re-planned**, and sweep directory names move (CR-5, QR-12).
- The assess and render helper processes report when they die without answering, and the Geometry
  tab says so instead of showing "measuring" or "drawing" for ever (CR-7).
- `AlignedEnsemble.export` keeps chains distinct when their keys are longer than one character:
  each gets a single character and the key goes in the segid columns (CR-9).
- `structure.source.variant` no longer keys stage 1 or enters its payload header, so relabelling does
  not re-align the ensemble. **Every stored structure artefact and everything keyed on it re-keys
  once**; case hashes do not move (CR-13, OPN-04).
- Stage 2's `canonical_grid` no longer copies the float32 ensemble to float64 (CR-8); the packaging
  probe writes its scene to a private temporary directory (CR-12).

## [0.3.0-alpha.8] - 2026-09-29

WP24: the geometry pipeline surfaced in the desktop shell (Phase 2 criterion 4).

### Added

- A **Geometry** tab, after Case, builds stages 1 to 6 from the shell (`upto: mesh`, in the run's
  spawned child and with its cancel token) and shows each stage's artefact as it lands. It shows
  the structure record, the density section, the (r, z) mean and both variances, the contour,
  the region, and the mesh by material beside its quality figures. Every picture names its frame
  (IF-09, QR-11, FR-27).
- A contour editor. It moves, inserts and deletes vertices with undo and redo, and never smooths.
  An edit is saved as a `nanopnp/profile/v1` document with `provenance.source: hand-edit`, and a
  derived case, written by the new `nanopnp.io.case.with_profile`, runs it through
  `inputs.profile`. The original case file is never modified.
- The §5.2.1 criteria are measured on an edit in a spawned child, against the case's own stored
  stages, and are shown but not enforced. A contour stage 4 refused can seed the editor
  (§8.2.2 B9).
- `ArtefactHook` (`on_artefact` on `run_case`) reports each stage's schema, hash and cache state
  after the artefact is in the store. It is bound after every key is taken, so it moves no key.
- `nanopnp.geometry.contour.measure`: stage 4's gate without its raise. `gate` is now built on it,
  and its messages and record are unchanged.
- The packaging probe carries and exercises MDAnalysis, gemmi, scikit-image, Shapely (with GEOS)
  and Gmsh, and fails naming the payload that does not work. The bundle carries Gmsh as the
  optional backend (§8.2.2 B8), and its licence notice names every new payload.
- VER-55 at Tiers 1 and 2, the latter on the prepared 2WCD.

### Changed

- The profile loader's messages for a negative radius and for coincident vertices now name the
  vertex index. `ContourGateError` carries the (r, z) it names as numbers, `location_nm`.
- `profile_digest` moved to `nanopnp.mesh.profile`. `nanopnp.geometry.region` re-exports it.

## [0.3.0-alpha.7] - 2026-09-29

WP23: the optional Gmsh mesher backend of ADR-002.

### Added

- `numerics.mesh.backend: gmsh` meshes a generated region with Gmsh, through the `gmsh` API called
  directly (CON-12). Gmsh meshes the region stage 5 assembled with `netgen.occ`, read from its named
  edges into Gmsh's built-in kernel, and assembles none of its own. The mesh joins netgen's route at
  the MSH 4.1 writer, so the naming, permittivity, quality and wall-size gates are the ones a netgen
  mesh passes. Its size field applies §5.2.2's table and states as graded fields what netgen does
  implicitly: grading from each domain's boundary, refinement near short edges, and the membrane
  held to its own thickness (§5.2.2 NOTE on the Gmsh backend's size field; FR-10, QR-12).
- The stage-6 key names the backend and, for Gmsh, its algorithm, smoothing and size-field rules.
  Netgen's recipe is byte-identical to before, so no stored key moves. The mesher's version is
  recorded beside the key in the mesh's sizing record (§5.3.1 NOTE on `numerics.mesh`).
- VER-54 at Tiers 1 and 2: the region graph against the record, the same region through the same
  gates on both backends, and WP22's frozen case on both backends' meshes within 1e-3 (measured
  1.24e-4). The VAL-05 tests record the Gmsh mesh beside netgen's (WP22 D10).

### Changed

- `backend: gmsh` is no longer a case refusal. Without the `gmsh` extra, stage 6 refuses the run
  naming the extra and the import error, a missing native library included (exit code 3, CON-10).
- CI lists every skip with its reason (`-rs`), and sets `NANOPNP_REQUIRE_GMSH=1` on every leg, so
  a Gmsh test fails rather than skips when `gmsh` does not import. The ubuntu jobs install the X
  and GL libraries the gmsh wheel loads.

## [0.3.0-alpha.6] - 2026-09-28

WP22: VAL-05, the geometry pipeline against the reference pore polygon, and the Phase 2 gate. The
tag also carries the codebase-review fixes merged on `main` since `v0.3.0-alpha.5`, listed under
*Fixed* and *Changed*.

### Added

- `nanopnp.validation.geometry`, the VAL-05 harness. It compares a model-frame polygon with the
  delivered 185-vertex table on the 282 mid-planes of its z extent. It gates three quantities per
  leg: `ε_G`, the first-order relative conductance change of a bulk series resistor; the rms lumen
  deviation; and `Δr_c`, the difference of the two *trans* constriction radii, each located on its
  own polygon. A plane the generated polygon leaves uncrossed outside 2h of a tip is refused naming
  z, and a tolerance failure names the leg, the quantity, the value, the threshold and where (QR-12).
  It also registers a structure to the MD frame by its C-alpha centroid, maps a polygon through the
  reference's `pqr2grid` binning erratum at L = 15 nm, and sweeps the isolevel on a cached map
  (§7.4 NOTE on VAL-05).
- VAL-05's 2WCD leg at Tier 2, gated to the author's 10 %, 0.1 nm and 0.2 nm. It records the
  attribution to the reference's construction, the isolevel sweep, the mesh against §5.2.2's figures,
  one frozen case's conductance on the generated mesh against the fixture's, and the Cₙ variance
  (FR-06, FR-07, FR-09, FR-10).
- VAL-05's ensemble leg at Tier 3, the Phase 2 gate, gated to 5 %, 0.1 nm and 0.1 nm on DCD frames
  48–97 at `centre_z_nm = 0`. It pins the MD structure's C-alpha centroid, 5.63 nm, to 0.01 nm, and
  skips naming `NANOPNP_REFERENCE_DATA` without the archive.

### Fixed

- The permittivity is no longer evaluated where the ions do not exist (author ruling 13). The ion-exclusion
  shell and the water share of a solid-fraction blend inside a solid are ion-free water, `ε_r,f⁰`,
  set as such; before, the salt correction was evaluated on concentrations that read zero there
  and happened to land near 78.15 by the clamp. Where the blend reaches into the fluid it now honours
  `χ` and goes towards the nearest solid's `ε_p`; before, the fluid side discarded `χ`. The exported
  `eps_r` field carries the blend the solve used (PHY-20, FR-15, VER-30, §4.4 NOTE).
- A sweep over a case that generates its mesh warm-starts. The member runner keyed each parent from
  its bare case, which raised for every generated mesh and was caught as a cold fallback, so every
  member climbed the full continuation ladder. The parent is now keyed through the artefacts its own
  walk stored, and only a parent that has not run falls back cold; any other error fails that member
  rather than the sweep (FR-24, VER-37).
- `numerics.wall_distance.max_distance_nm` set away from 3.0 nm is recorded as a deviation, and a
  cap, `electrolyte.concentration_M` or `boundary_conditions.bias_V` that is not finite (or, for
  the first two, not positive) is refused at resolve time, so a sweep plan rejects it in seconds
  (FR-25, PHY-02, QR-12).
- A field comparison over a mask that retains no probe point is refused rather than reported as
  exact agreement, and the probe grid's point lookup treats only NGSolve's "not in mesh" error as
  outside the mesh (VAL-01, QR-12).
- The attribution ladder's identity check is relative to the largest `E_k`. At an absolute 1e-14 it
  aborted a correct report whenever the golden was small enough for `E_k` to exceed about 10
  (VAL-04).
- A golden archive whose manifest records no `golden_hash` is refused instead of loading unchecked.
- The manifest's Materials group hashes every correction file the models read, not only the
  reference one (FR-25).
- A correction file carrying a per-species `fw` on an ion diffusivity or mobility is refused. The
  ion properties take the file's shared `ion_wall_function`, and the per-species fit was accepted
  and never applied (FR-16, PHY-11).

- A case whose `electrolyte.temperature_K` differs from the temperature its parameter file is
  fitted at is refused, naming both. The solve took every property and `V_T` from the file while
  the manifest recorded the case's temperature (FR-16, FR-25).
- A case asking for a wall condition other than `slip: no_slip` and `ion_flux: no_flux` is refused.
  Nothing applied the other values, which were recorded in the manifest all the same (FR-25).
- A case with `ground: trans` reported a negative conductance and an inverted rectification ratio.
  Stage 11 now reports its quantities against the cis-referenced bias, and a sweep orients its
  rectification pairs by the biases the members recorded (NUM-24, NUM-27).
- The MSH reader refuses a mesh carrying quads, curved triangles or any other cell that is not a
  straight-sided triangle or a line segment, as the NGSolve reader already did. It dropped them with
  a debug log, leaving a hole whose edge took the free condition (IF-06, QR-12).
- The NUM-26 route-agreement check fails when either current is not finite, in total and per
  species. A NaN reaction-flux route compared as agreeing and was recorded as checked (QR-04).
- A supplied field document whose `q_net_e` or `axis_cutoff_nm` is NaN or infinite is refused. A
  NaN `q_net_e` switched off three of the five charge-conservation gates (VER-29, QR-12).
- `nanopnp reproduce` reports a quantity that became NaN or infinite, or stopped being one, as a
  drift. The NaN difference passed the tolerance test and the run was declared reproduced (QR-08).
- A zero-bias case runs through stage 11. The transport number and the conductance are reported as
  undefined there, and the NUM-26 route check, a relative difference of two round-off currents, is
  not applied and is recorded as not applied; before, every zero-bias case aborted whatever
  `outputs:` asked for (NUM-26, NUM-27).
- The VAL-01 mask gate leaves the margin band out, as the norms already did. It compared our
  margin-shrunk mask with the golden's raw one, so a COMSOL export, which has values next to every
  interface, would have been refused as a geometry difference on every concentration field (VAL-01).
- The stage-8 key hashes every correction file a case reads, not only `electrolyte.parameters`. A
  correction model naming a second file took its fits from there, and an edit to it was served
  from the store unchanged. A case reading one file keeps its key (FR-16, FR-25).
- `dielectric_gradient_forces: true` with the permittivity correction off, or its concentration
  part off, assembles with a zero sensitivity instead of raising `AttributeError` (PHY-23).
- A run removes its scratch workspace under `<store>/tmp` when it ends. The store holds a copy of
  every payload, so each member of a sweep left a duplicate of its mesh, field export and solution
  on disk (QR-06).
- Damped Newton counts a NaN trial residual accepted at minimum damping as a forced step, which is
  never convergence. It counted as unforced, so convergence could be declared on the update alone
  with a NaN residual (NUM-16).
- A correction file edited while a process runs, the GUI or an in-process sweep, is read again for
  its fit coefficients. They were cached by model name, so the result mixed new reference values
  with old fits under the new key (FR-16).
- The truncation gate on a supplied field no longer treats a first grid column on the axis as a cut
  edge. Charge on the axis aborted as "the supplied grid is truncated", though the padding there
  discards nothing (VER-29).
- Sweep member records, run manifests, their case copies, run records, sweep plans and datasets are
  written atomically, as the store's files already were, so collection never reads a torn record
  written by a member still running. Temporaries carry a random token as well as the process id,
  which repeats across the hosts of a job array (QR-06).
- The packing-fraction, potential-increment and wall-distance gates fail on a NaN sample, as the
  positivity gate already did, and a pore profile with a NaN or infinite vertex is refused naming
  it; each passed NaN through a `>`-style comparison (NUM-17, NUM-34, QR-12).
- A supplied charge or solid-fraction grid carrying a NaN sample aborts at the conservation and
  range gates, naming the leg and the location, instead of passing them: every leg became NaN and
  every check was written `value > tolerance` (PHY-19, QR-03, VER-30, QR-12).
- VAL-04's `Δ_ref` is taken over the probe points the rungs' errors are: the margin band beside
  every interface is left out of it too. It kept the band, where a COMSOL export has values and the
  two refinements disagree most, so the verdict read "reference-limited" too readily. `nanopnp
  validate report` takes the band from a rung's own grid, and `compare.golden_grid`, whose masks
  were all true, is removed (VAL-04, §7.4 NOTE).
- A golden's `case_hash` carries the contents of a supplied charge or `ε_r` field, as stage 7 keys
  them. Two cases differing only in their charge table shared one identity, so a golden of one was
  accepted for the other. A case supplying no field, every frozen case among them, keeps its hash
  (VAL-03).
- The stage-7 key carries the element order its conservation integrals are taken at and, with a
  dielectric field, the solid materials its per-material means are classified by. A second order
  was served the first order's artefact, and its manifest recorded that order's conservation. A
  case supplying a field re-solves once (FR-25, §5.3.2).

### Changed

- The Tier-2 2WCD walk registers the structure by its C-alpha centroid, the VAL-05 registration,
  rather than by its *trans* tip plus 1.85 nm.
- The Tier-3 ensemble store is session-scoped, so a nightly session deposits the 50 frames once.
- The gate sample points of a mesh are built and located once per mesh and material set rather than
  twice per continuation rung and three more times per solve, about 36 s a rung at 145k elements.
- Stage 2 evaluates each atom's stencil only over the z planes of the slab being deposited, so the
  map is unchanged to the bit and a 0.025 nm grid deposits about 1.4 times faster; at 0.05 nm the
  time is unchanged (FR-04).
- Stage 1 holds one float64 copy of the ensemble rather than three: the frames are read into one
  array and moved into the model frame in place (FR-01).
- Stage 12 reads a supplied field table once, for its restore and for the exported fixed charge,
  rather than twice.

## [0.3.0-alpha.5] - 2026-09-26

WP21: CAD assembly and meshing from a profile, pipeline stages 5 and 6.

### Added

- Stage 5, `region`. It moves stage 4's profile, or a supplied `inputs.profile`, into the model
  frame by `geometry.membrane.centre_z_nm`, and fits the bilayer to it. The membrane's inner edge
  is the chord between the two planes' lumen-adjacent body intervals with the widest margin to the
  profile, found on a 63 × 63 grid. The pore, the bilayer and the electrolyte are assembled with
  OCC and glued, and every edge is named by the faces it separates (FR-09). The stage writes a
  declarative `nanopnp/region/v1` record from which the region is rebuilt.
- Stage 5's gate (QR-12): each plane crosses the profile at least twice, the chord clears the
  profile by 0.01 nm, each domain is one face, the profile lies inside the reservoir, and the
  membrane meets the body at the lumen-adjacent interval's outer end. A plane cut more than twice
  always splits a domain, and is refused by the one-face criterion. Each failure names the
  criterion, the value, the threshold and the (r, z).
- Stage 6 generates a mesh from stage 5's region (FR-10). `wall_h_nm: auto` resolves to
  `size_scale × min(0.05 nm, λ_D/5)` with λ_D at the reference permittivity; the rest of §5.2.2's
  size table scales with `size_scale`. The mesh is written as MSH 4.1 and read back through the
  ingestion gates, so a generated mesh passes every gate a supplied one does, including the
  solid-permittivity check. A wall-size gate then refuses a `wall` whose mean segment exceeds
  1.15 × its target or whose longest exceeds 2.0 ×, naming the segment.
- A generated mesh is keyed on its recipe and records its content hash. Every consumer reads the
  stage-6 file rather than regenerating it, and a reproduction whose mesh hashes differently is
  refused naming both hashes (QR-08).
- The manifest records the region (frame shift, chord, clearance, junction, face areas) and the
  sizing (the resolved wall size and its source, λ_D, `size_scale`, the wall-size statistics and
  the NUM-30 ratio) (FR-25).
- On the ClyA fixture the derived region meshes to the drawn reference's 44,316 triangles. The
  prepared 2WCD meshes at the default sizes, with 44,688 triangles and minimum SICN 0.7111, and
  walks to stage 12.
- VER-52, VER-53.

### Changed

- A `structure:` case, and a case supplying `inputs.profile`, walk the whole pipeline, and a sweep
  over either plans. A case with neither a mesh nor a profile nor a structure is refused.
- `structure`, `geometry` and `inputs.profile` are warm-start barriers in a sweep, and so is a salt
  or temperature axis whose values resolve to more than one wall size.
- Beside `inputs.mesh`, any `numerics.mesh` key away from its default is refused naming it.
  `numerics.mesh.backend: gmsh` is refused naming WP23, `boundary_layer: true` naming FR-11 and an
  analyte on a generated mesh naming FR-21.
- The reference geometry builds its region through stage 5's assembly, keeping its drawn corners;
  its mesh hash is unchanged. `ReferenceGeometryError` is replaced by stage 5's `RegionGateError`.
- RSK-05 is retired.

## [0.3.0-alpha.4] - 2026-09-26

WP20: contour extraction, conditioning and its gate, pipeline stage 4.

### Added

- Stage 4, `contour`. It finds the isolevel contour of stage 3's mean by sub-pixel marching
  squares, placing each point by the grid's own axes, so bin j sits at its centre. The closed
  loops are assembled into the region above the level, and a contour left open at the grid's
  edge is refused (FR-07). The region is closed and then opened by a disc of radius 2h, which
  removes gaps and fins under 4h (0.2 nm at the default grid), fills the holes left and records
  them, and admits exactly one component. The loop is resampled at h/2, smoothed by ten Taubin
  passes, simplified by Douglas–Peucker at `simplify_tol_nm`, and thinned until no edge is
  shorter than h.
- The gate (FR-08, QR-12): a valid, simple loop clear of the axis, every edge at least h, a local
  feature size above 2h, and the lumen radius within `[−h, +1.5 nm]` of a frame-mean probe
  radius computed on the aligned structure. Each failure names the criterion, the value, the
  threshold and the (r, z). The gate's size target is the density grid spacing, not the mesh's
  wall size, so the geometry does not depend on the electrolyte.
- The stage emits `nanopnp/profile/v1` with `provenance.source: pipeline`, the same document
  `inputs.profile` reads, written by a new `write_profile`. Its summary and the manifest record
  the conditioning and the gate. On 2WCD the stage takes under a second and passes with a
  feature size of 0.157 nm and a band of +0.062 to +0.908 nm.
- VER-51.

### Changed

- A `structure:` case walks to stage 4. A full walk and a sweep are refused naming stage 5, CAD
  assembly.
- `geometry.contour.isolevel` outside (0, 1) and `geometry.contour.simplify_tol_nm` outside
  (0, h) are refused naming the value.
- The author's contour script was read, and its index-to-radius erratum is recorded (OPN-02,
  closed; RSK-06, retired).

## [0.3.0-alpha.3] - 2026-09-25

WP19: the density map and the reduction to (r, z), pipeline stages 2 and 3.

### Added

- Stage 2, `density`. Each frame is deposited as the probabilistic union `1 − Π(1 − g_i)` of
  Gaussians of width `σ R_i`, with each term kept where `g_i ≥ 10⁻⁶`, and the ensemble map is the
  mean of the per-frame maps (FR-04). The grid's nodes are multiples of the spacing, so the axis
  is a node column. The stage emits a content-hashed `nanopnp/density/v1` artefact, an `.npz` map
  exportable as OpenDX or CCP4/MRC (IF-05, FR-27). A NaN or a value outside [0, 1] aborts the run,
  naming the voxel (QR-12). 2WCD at 0.05 nm deposits in about 17 s with a peak RSS under 0.5 GB.
- The radius set: CHARMM Rmin/2 by residue and atom, transcribed from PDB2PQR 3.7.1's
  `CHARMM.DAT` into `data/radii/pdb2pqr_charmm.yaml` (BSD-3-Clause; its notice is in
  `LICENSES-BUNDLE.md`), with the histidine, atom-alias and terminal-patch rules as data. An atom
  the set does not name is refused, naming its chain, residue number, residue and atom. There is
  no fallback by element.
- Stage 3, `symmetry`. The map is binned in (r, z) by the exact areas of overlap between grid
  cells and annuli. The Cₙ average is taken in the angular harmonic basis, with neither rotated
  copies nor interpolation (FR-05). The stage reports the Cₙ azimuthal variance after detrending,
  the raw variance, and each bin's harmonic count, with the radius below which nothing is resolved
  (FR-06, CON-04). It emits `nanopnp/reduced/v1`, exportable as three radial grids.
- The manifest records the density and reduction parameters, the radius set's digest, the
  element counts and the variance maxima (FR-25).
- VER-49 and VER-50. A shared `tests/conftest.py` holds the prepared 2WCD and a synthetic C12
  assembly.

### Changed

- A `structure:` case walks to stage 3. A full walk and a sweep are refused naming stage 4,
  contour extraction. The `geometry:` block is read, and it is refused beside `inputs.mesh`.
- `geometry.density.grid_spacing_nm` outside [0.025, 0.05] nm and a non-positive
  `geometry.density.sharpness` are refused naming the value.

## [0.3.0-alpha.2] - 2026-09-25

WP18: structure ingestion, alignment and the Cₙ axis, pipeline stage 1.

### Added

- Stage 1, `structure`. `nanopnp stage structure case.yaml` reads a PDB or mmCIF file, optionally
  gzipped, and an optional DCD, XTC, TRR or NetCDF trajectory (IF-04). It selects frames by
  `last_ns` and `count` and superposes each on the earliest selected frame's C-alpha (FR-01). It
  finds the Cₙ axis by chain-permutation superposition and puts it on z at r = 0, keeping the file's
  axial coordinate (FR-02). It emits a content-hashed `nanopnp/structure/v1` artefact: an `.npz`
  ensemble with its atom table, insertion codes included, and gate record, exportable as a PDB and
  a DCD (FR-27). mmCIF is read
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

## [0.3.0-alpha.1] - 2026-09-24

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

## [0.2.0] - 2026-09-24

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
  (`v0.2.0-alpha.1`);
- WP8, mesh ingestion, quality gates and the reference geometry (`v0.2.0-alpha.2`);
- WP9, external charge and dielectric fields (`v0.2.0-alpha.3`);
- WP10, case-driven runs, the command line and field output (`v0.2.0-alpha.4`);
- WP11, the sweep runner (`v0.2.0-alpha.5`);
- WP12, the reference-matching stabilised mode (`v0.2.0-alpha.6`);
- WP13, the Tier-3 harness and the COMSOL comparison (`v0.2.0-alpha.7`);
- WP14, the packaging probe and the desktop shell (`v0.2.0-alpha.8`);
- WP15, live convergence monitoring and the field viewer (`v0.2.0-alpha.9`);
- WP16, user documentation and worked examples (`v0.2.0-alpha.10`).

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

## [0.2.0-alpha.10] - 2026-09-23

WP16: user documentation and worked examples ([#34](https://github.com/willemsk/nanopnp/pull/34)).

### Added

- A documentation site (MkDocs and Material), built strictly on every push (VER-45). The case-file,
  command-line, exit-code and API references are generated from their sources, and the model pages
  render `SPECIFICATION.md` and `knowledge/` verbatim.
- Five worked examples, among them a SLURM job-array run of the ClyA reference. A test executes
  each README's commands verbatim against a model property (VER-46).
- `nanopnp mesh cylinder|reference` writes a gated MSH 4.1 mesh (VER-32).
- `nanopnp.__all__` is a lazily resolved public API of twenty names (IF-01).

### Fixed

- Every checked-in reference case mapped a `default` group that the reference mesh does not carry.

## [0.2.0-alpha.9] - 2026-09-22

WP15: live convergence monitoring and the webgui field viewer
([#32](https://github.com/willemsk/nanopnp/pull/32)).

### Added

- A structural solve hook (`SolveHook`) that reports each rung and each accepted Newton step,
  including the undamped relative update. Watched and unwatched runs share one artefact key.
- The desktop shell's live convergence plot, and a webgui field viewer that renders a restored
  solution in a spawned child process.
- The webgui renderer ships with the package, byte-identical to the vendored npm tarball.

Completes IF-09 and discharges QR-11 and VER-44.

## [0.2.0-alpha.8] - 2026-09-21

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

## [0.2.0-alpha.7] - 2026-09-20

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

## [0.2.0-alpha.6] - 2026-09-18

WP12: the reference-matching stabilised mode ([#28](https://github.com/willemsk/nanopnp/pull/28)).

### Added

- Stabilisation as a registry of named models: `none`; `supg`, the streamline term on transport;
  and `reference`, the streamline and crosswind terms plus the flow GLS and grad-div pair.
  Switching the mode is a configuration, not a code branch.

Discharges NUM-03, NUM-12, NUM-14 and NUM-15, completes NUM-11, and adds VER-41 and VER-42.

## [0.2.0-alpha.5] - 2026-09-13

WP11: the sweep runner ([#26](https://github.com/willemsk/nanopnp/pull/26)).

### Added

- The `nanopnp/sweep/v1` document: a base case plus axes of dotted-path assignments, taken as a
  Cartesian product. Every point is re-validated against the frozen case schema.
- A warm-start forest, so each point runs as an independent job while starting from a converged
  neighbour. `nanopnp sweep plan`, `sweep run` and `sweep collect` implement it, and
  `sweep run --index` runs one member, so that one member is one job-array task.
- The wall-distance clamp and its NUM-34 gate.

Discharges FR-24, measures QR-06, and adds VER-36 to VER-40.

## [0.2.0-alpha.4] - 2026-09-07

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

## [0.2.0-alpha.3] - 2026-09-07

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

## [0.2.0-alpha.2] - 2026-09-05

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

## [0.2.0-alpha.1] - 2026-09-04

WP7: the case-file schema, content-addressed artefacts and the provenance manifest
([#17](https://github.com/willemsk/nanopnp/pull/17)).

### Added

- The frozen `nanopnp/case/v1` schema. An unknown key is rejected, naming the key and its block, and
  a v0.3 or v0.4 section is refused rather than ignored.
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

[Unreleased]: https://github.com/willemsk/nanopnp/compare/v0.2.0-alpha.10...HEAD
[0.2.0-alpha.10]: https://github.com/willemsk/nanopnp/compare/v0.2.0-alpha.9...v0.2.0-alpha.10
[0.2.0-alpha.9]: https://github.com/willemsk/nanopnp/compare/v0.2.0-alpha.8...v0.2.0-alpha.9
[0.2.0-alpha.8]: https://github.com/willemsk/nanopnp/compare/v0.2.0-alpha.7...v0.2.0-alpha.8
[0.2.0-alpha.7]: https://github.com/willemsk/nanopnp/compare/v0.2.0-alpha.6...v0.2.0-alpha.7
[0.2.0-alpha.6]: https://github.com/willemsk/nanopnp/compare/v0.2.0-alpha.5...v0.2.0-alpha.6
[0.2.0-alpha.5]: https://github.com/willemsk/nanopnp/compare/v0.2.0-alpha.4...v0.2.0-alpha.5
[0.2.0-alpha.4]: https://github.com/willemsk/nanopnp/compare/v0.2.0-alpha.3...v0.2.0-alpha.4
[0.2.0-alpha.3]: https://github.com/willemsk/nanopnp/compare/v0.2.0-alpha.2...v0.2.0-alpha.3
[0.2.0-alpha.2]: https://github.com/willemsk/nanopnp/compare/v0.2.0-alpha.1...v0.2.0-alpha.2
[0.2.0-alpha.1]: https://github.com/willemsk/nanopnp/compare/v0.1.0...v0.2.0-alpha.1
[0.1.0]: https://github.com/willemsk/nanopnp/compare/v0.1.0-alpha.6...v0.1.0
[0.1.0-alpha.6]: https://github.com/willemsk/nanopnp/compare/v0.1.0-alpha.5...v0.1.0-alpha.6
[0.1.0-alpha.5]: https://github.com/willemsk/nanopnp/compare/v0.1.0-alpha.4...v0.1.0-alpha.5
[0.1.0-alpha.4]: https://github.com/willemsk/nanopnp/compare/v0.1.0-alpha.3...v0.1.0-alpha.4
[0.1.0-alpha.3]: https://github.com/willemsk/nanopnp/compare/v0.1.0-alpha.2...v0.1.0-alpha.3
[0.1.0-alpha.2]: https://github.com/willemsk/nanopnp/compare/v0.1.0-alpha.1...v0.1.0-alpha.2
[0.1.0-alpha.1]: https://github.com/willemsk/nanopnp/releases/tag/v0.1.0-alpha.1
