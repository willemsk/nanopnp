# Changelog

Every notable change to nanopnp, newest first. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the versions are the git tags of
[SPECIFICATION.md](SPECIFICATION.md) §2.7:

- a **release** `vX.Y.Z` closes a phase, one minor version per phase: v0.1 is Phase 0, v0.2 is
  Phase 1, v0.3 is Phase 2, v0.4 is Phase 3 and v1.0 is Phase 4;
- a **work-package pre-release** `vX.Y.Z-alpha.N` marks the merge of the N-th work package toward
  that release.

The package version comes from the tag (hatch-vcs). A commit between two tags installs as a
development version that names it, for example `0.2.0a11.dev3+g1a2b3c4`, and that is the version
every provenance manifest records (FR-25). The versions were renumbered on 30 September 2026
(`SPECIFICATION.md` §2.7, the Versioning NOTE): Phase 1's tags were `v0.5.0-alpha.1` to `v0.5.0` and
Phase 2's were `v0.9.0-alpha.1` to `v0.9.0-alpha.9`. A manifest written before then records the old
version, and this file's sections carry the new names. Each entry names the requirements it discharges. The
evidence is in the work package's plan under [docs/plans/](docs/plans), not here.

## [0.4.0-alpha.8] - 2026-10-03

WP33: the tier 1–2 suite's duration cut without losing a check, under the §7.6 NOTE on a gated
test's runtime. Serial test time 1,508.9 s → 1,334.5 s, and the four-worker wall 458 s → 394 s.
No assertion, tolerance or oracle changes.

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
  APBS's order at 1.6 (`.knowledge/07` §3). At Tier 3, recorded: the ClyA-AS ensemble from the
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
  render `SPECIFICATION.md` and `.knowledge/` verbatim.
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
