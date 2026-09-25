# WP18 — Structure ingestion, alignment and the Cₙ axis (stage 1)

**Status: planned, not started.** Written 25 September 2026. It builds on WP17, merged
25 September 2026 as PR #38 and tagged `v0.9.0-alpha.1`. WP18 inherits:

- the `nanopnp/case/v2` `structure:` block and its keys (`source.path`, `selection`, `chains`,
  `variant`, `ensemble.frames`, `symmetry.point_group`, `symmetry.axis: auto | z`);
- the stage registry and the lazy `create()` (WP7, VER-25);
- the artefact store and `content_hash` (§5.3.2, VER-23);
- the exit-code enumeration (VER-32);
- the switch classification (VER-24).

The package belongs to [Phase 2, geometry pipeline](phase-2-geometry-pipeline.md) §WP18.
`SPECIFICATION.md` governs, and every identifier below points into it. Where this plan and the
specification disagree, the plan is wrong.

**Spec amendments made in this plan's commit:**

- §2.6 gains gemmi.
- CON-09 accepts MPL-2.0 used unmodified.
- The §5.2 stage-1 tools cell and design note are amended; the note now carries the measured
  principal-axis drift.
- §5.3.1 gains the NOTE on `structure:`, which is the normative stage-1 contract.
- §5.3.2's stage-1 artefact row is amended.

VER-48 and its Appendix A rows are added by the implementation, as the phase plan provides. The
mmCIF reader and the axis-sign convention are **author rulings of 25 September 2026**.

## Execution brief

### Scope

The package delivers pipeline stage 1:

- read a structure (PDB or mmCIF) and an optional trajectory (DCD, XTC, TRR or NetCDF) (IF-04);
- select frames and superpose them on a reference frame's Cα set (FR-01);
- find the Cₙ axis by chain-permutation superposition and put it on z at r = 0 (FR-02);
- check the oligomeric state, aborting on missing chains (FR-03, QR-12);
- emit a content-hashed aligned-ensemble artefact (FR-27);
- register the stage, so that `nanopnp stage structure case.yaml` runs it.

No later stage exists yet, so a full walk of a `structure:` case is refused naming stage 2 (the
§5.3.1 NOTE). 2WCD is vendored (B2). The schema does not move.

**This brief runs to about 2,700 words, over its 1,200-word target; the two tables are most of it.** The decisions fix the model
frame and the sign of the axis, which every later stage inherits. They are kept together rather
than split, because the gates, the frame and the artefact form one contract verified by one set of
oracles.

### Pointers

- §5.3.1 NOTE on `structure:`, which is normative. Stage 1 is built to it.
- The §5.2 stage-1 row and design note; §5.3.2 (artefact keys, canonical serialisation, workspace
  locality); FR-01 to FR-03, IF-04, FR-27, QR-12 and CON-07 to CON-09.
- `.knowledge/07-software-stack.md` §2 (axis detection, mmCIF, trajectory times) and
  `.knowledge/04-clya-geometry-and-charge.md` §1.1 (the author's archive).
- Code: `core/stages.py` (`register`, `create`); `io/run.py` (`PIPELINE`, `_selected`,
  `WORKSPACE_STAGES`, `_WEIGHTS`, `_manifest`); `io/case.py` (`Structure`, `_require_runnable`,
  `_PIPELINE_SECTIONS`); `io/defaults.py` (`CONFIGURATION_PATHS`); `cli/errors.py`; the lazy
  optional-import pattern in `density/grid.py:_grid_data_module`.

### Decisions

| # | Decision | Choice | Why / source |
|---|---|---|---|
| D1 | Stage identity and walk | The stage is named `structure`, number 1, with inputs `("case",)` and schema `nanopnp/structure/v1`. Its target is `nanopnp.structure.stage:StructureStage`. `PIPELINE` becomes `("case", "structure", "mesh", …)`, and `_selected` drops `structure` when the case has no `structure:` section. `resolve()` accepts `structure:`, while `geometry:` and `charge:` stay refused. `inputs.mesh` becomes optional **only** when `structure:` is present. A walk past stage 1 on a `structure:` case is refused (`UnsupportedCaseSection`, naming stage 2 and WP19). The refusal is one function of `(resolved, upto)`, called by `run_document` and by the sweep plan builder, so a sweep is refused when its plan is built | §5.3.1 NOTE (last paragraph). `structure:` beside `inputs.mesh` in a full walk would hash an input nothing reads (the `inputs:` NOTE). Stage 1 alone runs through `nanopnp stage structure` (IF-02) |
| D2 | Readers | Extensions `.pdb`, `.ent`, `.cif` and `.mmcif`, each optionally `.gz`; anything else is refused naming the accepted set. PDB and every trajectory format are read by MDAnalysis. mmCIF is read by **gemmi** into an MDAnalysis `Universe` (`Universe.empty` plus topology attributes, with coordinates through `MemoryReader`), so everything downstream sees one object. Chains come from gemmi's `auth_asym_id`. Coordinates convert from Å to nm exactly once, in `structure/read.py` | **Author ruling, 25 September 2026.** MDAnalysis 2.10 has no mmCIF reader [tested] (`.knowledge/07` §2). gemmi 0.7.5 is MPL-2.0 with wheels for cp311–cp314 on all three platforms, so CON-07 and QR-09 hold. §2.6 and CON-09 are amended |
| D3 | Atom validity | Elements come from the file and are never guessed. Alternate locations are refused. The chain key is the chain identifier, or the segment identifier where that is blank, and the key used is recorded | §5.3.1 NOTE. A guessed element is a plausible wrong radius in WP19 |
| D4 | Oligomeric state (FR-03) | The point group is parsed as `C<n>`, n ≥ 1, as a resolution-time refusal. The number of chains must equal `n`, and a missing listed chain is named. Each chain must carry at least half the Cα of the most complete chain (coverage ≥ 0.5). Residue names must agree at every shared residue number, with `HSD/HSE/HSP/HID/HIE/HIP` read as `HIS`. Every check here is a refusal in `resolve()` or the stage, **never** a pydantic narrowing | §5.3.1 NOTE. Narrowing a key's value set would move the schema (§5.3.1 compatibility rule). Measured: residue names agree at every Cα in 2WCD and the MD archive |
| D5 | Frames | The ensemble is the trajectory's frames if one is given, else the source file's models. `last_ns` uses the recorded times and is refused if it exceeds span + interval. `count` takes the stride `⌊N/count⌋` ending on the last frame, and is refused if `count > N`. Indices and `times_ns` are recorded as read | §5.3.1 NOTE; [Design §3](#3-trajectory-time-metadata). The author's DCD reads 1 ps per frame |
| D6 | Superposition (FR-01) | An in-project Kabsch fit (SVD with the determinant sign fixed), unweighted, over every Cα of the selection. Each selected frame is fitted to the **earliest selected** frame, and the rotation is applied to every atom. RMSD is recorded per frame. It is checked against MDAnalysis `rotation_matrix` in a test | The same routine serves the axis fit. `AlignTraj` writes files the stage does not want |
| D7 | Axis (FR-02) | Computed on the ensemble-mean Cα structure over the Cα common to every chain. (1) The initial axis is the top eigenvector of the symmetric part of `(1/n)Σ_j R_{0→j}`. (2) Chains are ordered by the azimuth of their centroids. (3) **Cyclic permutation superposition** of the whole assembly, with the chain at position k mapped to position k+1. (4) The axis is the eigenvector of eigenvalue 1, through the Cα centroid. Gates: spacing within 90°/n, rotation angle within 1° of 360/n. Per-frame axes are recorded as drift, **not gated**. `auto` refuses C1 | FR-02 read literally, with ordering that does not trust chain labels. [Design §1](#1-the-axis), [§4](#4-measurements-and-threshold-margins) |
| D8 | Sign and frame | **Sign:** â points along the file's +z, with a gate at 10°. **Transform:** `x′ = Q(x − p)` with `p = c − (c·â)â`, so `z′ = â·x`. `Q` is the minimal rotation taking â to ẑ, followed by a turn about z that puts the first chain in file order on +x; the others run counter-clockwise, and their order is recorded. `centre_z_nm` is **not** applied here; stage 5 applies it (WP21) | **Author ruling, 25 September 2026.** `z = â·x` makes `centre_z_nm` read "in the structure's frame" as the §5.3.1 example says. [Design §1](#1-the-axis) |
| D9 | `axis: z` | Takes the file's z axis through the origin with no rotation. When n ≥ 2 the detected axis is still computed, and `z` is refused when its lateral displacement exceeds 0.01 nm anywhere over the Cα axial extent. C1 requires `z` and is recorded as unchecked. `structure.symmetry.axis` stays in `CONFIGURATION_PATHS` with its reason updated: `z` is admitted only inside the displacement budget | [Design §2](#2-the-displacement-budget). Measured: 2WCD passes at 0.007 nm, and the MD frame fails at 0.09 nm |
| D10 | Artefact | `AlignedEnsemble` is a frozen dataclass whose payload is a `.npz` holding: `positions_nm`, float32 `(frames, atoms, 3)`; the atom table (`element`, `name`, `resname`, `resid`, `chain`). The header holds: source and trajectory digests; the selection, chain key and chains in cyclic order; `n`; the frames (indices, `times_ns`, interval); the per-frame superposition RMSD; the axis in the file frame (â, p in nm); `Q`; the gate measurements and their thresholds; the per-frame axis drift; the orientation rule; `variant`. It carries **no van der Waals radius**. `export()` writes a PDB topology and a DCD through MDAnalysis | §5.3.2 amended. The radius is a density-kernel parameter, so it belongs in stage 2's key (WP19) and not stage 1's. It amends the phase plan's stage-artefact row |
| D11 | Key | `content_hash(schema, parameters)`, where the parameters are the resolved `structure:` block with each file replaced by its content digest. The payload digest is recorded and re-checked on load (the VER-23 hand-edit rule). The stage is a workspace stage | §5.3.2 canonical-serialisation and workspace-locality NOTEs. The key never depends on payload bits, which LAPACK may vary across platforms |
| D12 | Errors | `StructureInputError` covers files, elements, alternate locations, chains, coverage and frames. `SymmetryGateError` covers spacing, angle, orientation and `axis: z` displacement. Both map to `EXIT_GATE`. `MissingExtraError` lives in `core/stages.py` and maps to `EXIT_CASE`; `create()` raises it when a registered stage's `extra` is not installed, naming the extra, the module and `uv sync --all-extras` | QR-12; IF-02 exit NOTE. The registry entry (not `StageDescription`) gains `extra: str \| None`, so VER-25's description is unchanged |
| D13 | Imports | MDAnalysis and gemmi are imported at the top of `structure/read.py` (reached only through `create`). `structure/axis.py` is pure numpy, with numpy deferred inside functions. `nanopnp stage --list` imports neither MDAnalysis nor gemmi, which is asserted | The phase plan's optional-dependency rule; `CLAUDE.md` import rule |
| D14 | Manifest | The Inputs group gains the structure and trajectory digests. The Geometry group gains a `structure` record (axis, gates, frames, drift), taken from the artefact summary and never recomputed | FR-25, §5.3.3 |
| D15 | Public API | No new `nanopnp.__all__` name. The stage is reached through the registry, and WP25 decides what to document | IF-01 NOTE; `test_public_api.py` makes adding a name a decision |
| D16 | Vendored 2WCD | The wwPDB entry goes in as `tests/data/structures/2wcd.pdb.gz` and `2wcd.cif.gz`, byte-for-byte as downloaded, with a README giving the URL, date, sha256 and CC0. Add `tests/data/** -text` to `.gitattributes`. It is shared with the WP22 Tier-2 leg | B2. The file digest enters the stage-1 key, and a CRLF rewrite would move it (`.knowledge/07` §14) |

### Work items

1. **Dependencies and data** (D2, D16). Run `uv add --optional structure "gemmi>=0.7"`, add a mypy
   override for `gemmi`, then run `uv lock`. Vendor 2WCD with its README and add the
   `.gitattributes` rule.
2. **`structure/axis.py`** (D6–D9): Kabsch, chain order, cyclic fit, gates, frame transform and
   displacement, all on numpy arrays with no MDAnalysis. Write its synthetic tests **first**; they
   need only numpy. Read Design §1–§2 before starting.
3. **`structure/read.py`** (D2–D5): readers, the mmCIF-to-`Universe` bridge, chain grouping, the
   element and alternate-location checks, the common Cα set, and frame selection. Read Design §3.
4. **`structure/ensemble.py`** (D10, D11): `AlignedEnsemble`, `.npz` IO, `digest()`, `export()`.
5. **`structure/stage.py`** plus the registry (D1, D12, D13): the `register` entry with
   `extra="structure"`, `MissingExtraError`, and `EXIT_CODES` for the three new types.
6. **Case and walk** (D1, D4, D9): in `io/case.py`, resolution accepts `structure:`, `inputs.mesh`
   becomes conditional, and the point-group, chains and frames refusals go in. In `io/run.py`:
   `PIPELINE`, `_selected`, the walk refusal, `WORKSPACE_STAGES`, `_WEIGHTS` and the manifest
   records (D14). The sweep plan builder calls the walk refusal. `io/defaults.py` gets the reason
   text. The `Structure` field descriptions state the NOTE, so the generated case reference
   (VER-45) carries it.
7. **Spec, changelog, knowledge.** Add VER-48 to §7.2 (text in Verification below). Map IF-04,
   FR-01, FR-02 and FR-03 to it in Appendix A and recount the coverage line. Add the `CHANGELOG.md`
   section `v0.9.0-alpha.2`. Add Outcomes here where a prediction moved, and update `current.md`.

### Verification

VER-48 (to add to §7.2): *Structure ingestion, the Cₙ axis and the oligomeric state.*

- A synthetic Cₙ assembly (n = 7, 8, 12) about a known tilted and offset axis recovers that axis to
  round-off when exact. With per-atom noise, it recovers the axis within the 0.01 nm displacement
  budget, and a principal-axes estimate on the same isotropic-moment input does not.
- A missing chain, a coverage shortfall, a residue-name disagreement, an irregular spacing, a wrong
  rotation angle, a non-cyclic point group and `auto` on C1 are each refused naming the quantity.
- An axis more than 10° from the file's z, and an `axis: z` beyond the displacement budget, are
  refused naming the angle or displacement.
- PDB and mmCIF of one entry read to the same atom table and coordinates. Each trajectory format
  reads.
- A `last_ns` beyond the recorded span and a `count` beyond the window are refused.
- A rigidly moved frame superposes to zero RMSD. The aligned output re-detects its own axis as z
  through r = 0.
- The artefact round-trips and exports.
- The registry lists the stage without importing MDAnalysis or gemmi, and a missing extra is named.

| Test | Tier | Identifiers | Oracle | Tolerance and source |
|---|---|---|---|---|
| `tests/tier1/test_structure_axis.py::test_ver48_exact_cn_assembly_recovers_its_axis` (n = 7, 8, 12) | 1 | VER-48, FR-02 | Known â and p under a 35° tilt and an (3, −1.5, 40) nm offset | `‖â × â_true‖ ≤ 1e-9`, offset ≤ 1e-9 nm (measured 6e-14°) |
| `…::test_ver48_permutation_meets_the_budget_where_principal_axes_do_not` | 1 | VER-48, FR-02 | The isotropic-moment synthetic of Design §5, fixed seed, σ = 0.02 nm | Permutation displacement ≤ 0.01 nm over the extent (predicted ≈ 0.003 nm: 0.019° over a 4.4 nm half-extent, plus 0.0012 nm offset); principal-axes displacement > 0.01 nm. Both values are logged. Not σ = 0.1 nm: there the permutation estimate itself reaches about 0.013 nm |
| `…::test_ver48_gates_fire` (parametrised) | 1 | VER-48, FR-03, QR-12 | Twelve chains in a 6 × 2 arrangement claimed as C12 (spacing); a D6-like assembly (angle); C1 with `auto`; an axis 30° from the file's z; `axis: z` offset by 0.02 nm | Each raises `SymmetryGateError` whose message names the gate and the measured value |
| `…::test_ver48_kabsch_matches_mdanalysis` | 1 | VER-48, FR-01 | `rotation_matrix` on a random rigid move | 1e-12 on the rotation entries |
| `tests/tier1/test_structure_stage.py::test_ver48_rigid_move_superposes_to_zero` | 1 | VER-48, FR-01 | Frames `R_k x + t_k` of 2WCD chains A–B | RMSD ≤ 1e-5 nm (float32 at about 10 nm) |
| `…::test_ver48_2wcd_pdb_and_mmcif_agree` | 1 | VER-48, IF-04 | Same atom table; coordinates equal | ≤ 5e-5 nm (PDB precision of 0.001 Å, plus float32) |
| `…::test_ver48_each_trajectory_format_reads` | 1 | VER-48, IF-04 | DCD, XTC, TRR and NCDF written from a 2WCD subset | Exact for DCD, TRR and NCDF; ≤ 1e-3 nm for XTC (its precision) |
| `…::test_ver48_frame_selection_and_the_time_gate` | 1 | VER-48, FR-01 | Stride indices; a DCD without a timestep plus `last_ns` is refused, naming the span; `count > N` is refused | exact |
| `…::test_ver48_input_refusals` | 1 | VER-48, FR-03, QR-12 | A blank element, alternate locations, chain K removed, an explicit list naming chain M, a truncated chain, `point_group: D6` | Each is refused naming the atom or chain |
| `…::test_ver48_2wcd_runs_as_stage_one` | 1 | VER-48, FR-01–FR-03 | `run_case(upto="structure")` on the vendored entry: 12 chains, 285 common Cα, gates pass. Re-detecting the axis on the output gives ẑ through r = 0 | ≤ 1e-6 rad and ≤ 1e-6 nm (float32 output). Measured values logged, not asserted |
| `…::test_ver48_artefact_round_trip_and_export` | 1 | VER-48, FR-27, VER-23 | `.npz` round trip; the key is stable across processes; a hand edit reads as substituted; the exported PDB and DCD reload | exact (DCD float32) |
| `…::test_ver48_walk_rules` | 1 | VER-48, IF-02 | A full walk on a `structure:` case is refused naming stage 2; `upto="structure"` runs; `upto="structure"` on a case with no `structure:` is refused; a sweep over a `structure:` case is refused at plan build | — |
| `test_stages.py` / `test_cli.py` / `test_manifest.py` (existing walks) | 1 | VER-25, VER-32, VER-24 | The stage is listed in a fresh process with no `MDAnalysis` or `gemmi` in `sys.modules`; the three new errors are classified; the updated reason holds; a missing extra raises `MissingExtraError` naming `structure` | — |
| `tests/tier3/test_structure_ensemble.py::test_ver48_clya_as_ensemble` | 3 | VER-48 | `$NANOPNP_REFERENCE_DATA/prod5_clya_as.{pdb,dcd}`, all frames: gates pass, and the drift, RMSD and tilt are recorded. Skips without the archive | recorded, not gated |

Commands:

```bash
uv run pytest tests/tier1/test_structure_axis.py tests/tier1/test_structure_stage.py -v
uv run pytest -m tier3 tests/tier3/test_structure_ensemble.py -v
.claude/hooks/gate.sh run
```

### Out of scope

- **Structure preparation**, including re-orienting a flipped file, missing residues, mutations
  and PDBFixer. This is the phase plan's exclusion; the §5.3.1 NOTE makes +z → *cis* the file's
  contract.
- **The radius set and the density** go to WP19. **Applying `centre_z_nm`** goes to WP21. **The
  probe-radius profile** goes to WP20.
- **VAL-05** goes to WP22. An **export CLI command** and **the GUI view** go to WP24. **The guide**
  goes to WP25.

### Open questions

None block WP18. Carried to their owners:

1. **Frame spacing of `prod5_clya_as.dcd`, and which frames were the paper's 50.** The author
   recalls a span of about 10 ns. Their answer on the sampling arrived truncated, so this is
   unresolved. For WP22; the Tier-3 test here takes all 98 frames.
2. **The van der Waals radius set the original density used.** For WP19, from the author or the
   contour script (B6).
3. **G9.** The MD frame's extent suggests `centre_z_nm` ≈ 0 (`.knowledge/04` §1.1). For the author,
   before WP22.

## Design

### 1. The axis

For an exact Cₙ assembly with generator `R = R(â, 2π/n)`, Rodrigues gives
`R(θ) = cos θ I + sin θ [â]× + (1 − cos θ) â âᵀ`. Since `Σ_{k=0}^{n−1} cos(2πk/n) = Σ sin(2πk/n) = 0`
for n ≥ 2, it follows that `Σ_k R^k = n â âᵀ`. The symmetrised average of chain 0's rotations onto
every chain is therefore the projector onto the axis, **whatever the chain labels**. Its top
eigenvector orders the chains by azimuth without trusting their lettering.

The reported axis is FR-02's: the eigenvector of eigenvalue 1 of the single rotation that
superposes the ordered assembly onto its cyclic permutation. The two point sets are the same atoms
in a different order, so their centroids coincide. The fitted transform is therefore a pure
rotation about the Cα centroid `c`, and the axis passes through `c`.

The chain-0 average differs from the cyclic fit by up to 1.12° on single MD frames, so it only
orders the chains.

The sign follows the file's +z (D8). The foot of the perpendicular from the file origin,
`p = c − (c·â)â`, gives `z′ = â·(x − p) = â·x`, so the file's axial coordinate survives the
transform.

### 2. The displacement budget

Azimuthal averaging about an axis displaced laterally by `e` from the true one smears a wall at
radius `R` over `R ± e cos φ`. For a sharp wall (protein at `ρ > R`), the averaged occupancy at `ρ`
is `P(cos φ < (ρ − R)/e) = 1 − arccos((ρ − R)/e)/π`. Setting this equal to the 0.25 isolevel gives
`(ρ − R)/e = cos(3π/4) = −0.707`. **The 25 % contour moves inward by 0.71 e.** For a smooth wall of
width `w ≫ e`, the shift is second order, `O(e²/w)`, so 0.71 e bounds it.

At the ClyA constriction, `r ≈ 1.65 nm`. With `G ∝ r²`, `e = 0.01 nm` gives
`δG/G ≤ 2 × 0.71 × 0.01/1.65 = 0.86 %`, below the ±1 % floor of gap G3. So **e ≤ 0.01 nm**.

Tilt and offset combine as `e(h) = |h| sin θ + δ` over the Cα axial extent `h` about the foot. For
2WCD, θ = 0.047°, δ = 0.0012 nm and |h| ≤ 7.2 nm, which gives e = 0.007 nm, so `z` passes. For the
MD frame, θ = 0.69° over 7.6 nm gives 0.09 nm, so `z` is refused. Its conductance error would be
about 8 %.

### 3. Trajectory time metadata

MDAnalysis reads a DCD written without a timestep as 1.0 ps per frame, and XTC, TRR or NCDF as 0 ps
[tested]. The author's DCD spans 0.097 ns by its metadata, for about 10 ns of production. With
`last_ns: 5`, a window taken on trust would be the whole file. The span gate refuses it:
`5 > 0.097 + 0.001`. A `last_ns` inside a wrong span cannot be caught, which is why the times are
recorded as read.

The stride `⌊N/count⌋`, ending on the last frame, reproduces "50 frames from the last 5 ns, every
100 ps" on a 1000-frame window at 5 ps per frame: the stride is 20, which is 100 ps. It also keeps
the spacing uniform where a rounded `linspace` would not.

### 4. Measurements and threshold margins

These were measured on 25 September 2026, using the scratch scripts of the planning session (not
kept) and the author's archive (`.knowledge/04` §1.1).

| Quantity | 2WCD | 6MRT | MD frame 0 | MD, 98 frames | Threshold | Margin |
|---|---|---|---|---|---|---|
| Chains / common Cα | 12 / 285 | 12 / 285 | 12 / 286 | — | n; coverage ≥ 0.5 | — |
| Rotation angle − 30° | 0.001° | 0.000° | 0.031° | ≤ 0.031° | 1° | 32× |
| Worst spacing error | 0.19° | 0.25° | 1.23° | ≤ 1.57° | 7.5° (90°/n) | 4.8× |
| Permutation RMSD | 0.026 nm | 0.014 nm | 0.19 nm | 0.16–0.20 nm | recorded | — |
| Axis tilt from file z | 0.047° | 0.006° | 0.69° | 0.689° (mean) | 10° (`auto`) | 14× |
| Axis drift between frames | — | — | — | ≤ 0.010° | recorded | — |
| Principal-axis drift | — | — | — | ≤ 1.54° | (not used) | — |
| Frame RMSD to frame 0 | — | — | — | 0.095–0.22 nm | recorded | — |

The spacing threshold catches a mislabelled point group of the right chain count (a 6 × 2
arrangement gives gaps of 0° and 60°). The angle threshold catches a dihedral assembly, whose best
cyclic fit is a two-fold turn.

### 5. The principal-axes synthetic

Each chain is 285 points with `ρ ~ U(2, 5)` nm, `φ` inside ±80 % of its wedge, and
`z ~ U(−h/2, h/2)`. The test rescales `z` so that the sample moments satisfy `⟨z²⟩ = ⟨ρ²⟩/2`
exactly. This makes the assembly's covariance isotropic, so the principal axes are undetermined
before noise is added. It is then replicated n times, perturbed by independent noise σ per atom, and
moved by the known tilt and offset.

Measured over 20 seeds, with near-isotropic sampling rather than exact rescaling:

- **σ = 0.02 nm:** the permutation error is ≤ 0.019° with offset ≤ 0.0012 nm. The principal-axis
  error is up to 6.2°.
- **σ = 0.1 nm:** the permutation error is ≤ 0.095° with offset ≤ 0.006 nm. The principal-axis
  error reaches 24°.

The test fixes one seed and asserts the budget comparison rather than a transcribed angle.
