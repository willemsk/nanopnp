# WP19 — Density map and symmetry reduction (stages 2 and 3)

**Status: delivered, 25 September 2026.** Written 25 September 2026, after WP18 merged as
`v0.9.0-alpha.2` (PR [#39](https://github.com/willemsk/nanopnp/pull/39)). This package inherits
stage 1's frame: the axis is on z at r = 0, z = â·x keeps the file's axial coordinate, and the
aligned ensemble carries an atom table (element, name, residue name, number, insertion code, chain)
but **no radius** (WP18 D10). It also inherits `refuse_walk`, which it extends. The van der Waals
radius set this package needs was an open author question. It was **ruled on 25 September 2026**,
while this plan was written (D3).

This is a work package of the [Phase 2 plan](phase-2-geometry-pipeline.md). `SPECIFICATION.md`
governs: where this file and the specification disagree, the specification is right and this file
is wrong. Requirement identifiers here are pointers into it, never restatements of it. This plan's
commit amends the specification in five places, listed under [Pointers](#pointers).

## Execution brief

### Scope

The package delivers pipeline stages 2 and 3:

- **Stage 2, `density`:** the ensemble-averaged probabilistic-union density on a 3D Cartesian
  grid, with per-atom widths from the CHARMM radius set (FR-04). It is exportable to OpenDX and
  CCP4 (IF-05).
- **Stage 3, `symmetry`:** the Cₙ average and the azimuthal reduction to an (r, z) `RadialGrid`
  mean (FR-05). The Cₙ-averaged and the raw azimuthal variance are first-class outputs (FR-06,
  CON-04, RSK-07).
- **Walk and resolution:** a `structure:` case now walks to stage 3, and a walk past it is refused
  naming stage 4 (WP20). The `geometry:` block is accepted beside `structure:`.

It adds VER-49 and VER-50, and closes the phase plan's open decision on the Cₙ averaging method
(D7).

**This brief runs to about 3,000 words, over its 1,200-word target.** Its decisions fix a radius
set, a sampling grid, an averaging method and a variance definition. Stage 4's contour, WP22's
VAL-05 comparison and Phase 3's dielectric field all inherit these. Every tolerance below is
measured, and splitting the package would separate the variance from the mean it is defined
against.

### Pointers

- **Normative:** the §5.3.1 NOTE on `geometry.density`, added in this commit, is the contract for
  both stages. Also normative: FR-04 to FR-06, CON-04, IF-05, FR-27 and QR-12; §5.2 rows 2–3 and
  their design notes; §5.3.2.
- **Amended in this commit:**
  1. The §5.3.1 NOTE on `geometry.density` is new.
  2. The §5.3.1 NOTE on `structure:` gains the stage-4 walk sentence.
  3. §5.2 rows 2–3 and their design notes change. The inner-bin interpolation is dropped, the Cₙ
     average is taken in the harmonic basis, and the radius-profile check moves to the §5.2.1
     gate that already holds it.
  4. §5.3.2 splits the stage 2–3 row from stage 7's.
  5. A NOTE under FR-05 and FR-06 in §3.2 points to the contract.
- **Knowledge:** `.knowledge/04` §1.1 has the reference ensemble's PQR files and the frame
  spacing they imply. `.knowledge/07` §2 has deposition cost, annular binning and the Cₙ
  projection, all measured.
- **Code:**
  - `structure/ensemble.py` (`AlignedEnsemble.read`).
  - `density/grid.py` (`RadialGrid`, `write_grid`, `_grid_data_module`).
  - `core/stages.py` (`register`, `_register_builtins`).
  - `core/paths.py` (`correction_file` pattern).
  - `io/run.py` (`PIPELINE`, `_selected`, `WORKSPACE_STAGES`, `_WEIGHTS`,
    `STRUCTURE_RECORD_KEYS`).
  - `io/case.py` (`DensitySpec`, `_PIPELINE_SECTIONS`, `STRUCTURE_WALK`, `refuse_walk`,
    `_require_runnable`).
  - `io/defaults.py` (`CONFIGURATION_PATHS`).
  - `tests/tier1/test_structure_stage.py` (`_prepared_rotation`, `_dodecamer`).

### Decisions

| # | Decision | Choice | Why / source |
|---|---|---|---|
| D1 | Stages and walk | Stage 2 is `density`: number 2, inputs `("case", "structure")`, schema `nanopnp/density/v1`, target `nanopnp.density.stage:DensityStage`. Stage 3 is `symmetry`: number 3, inputs `("case", "density")`, schema `nanopnp/reduced/v1`, target `nanopnp.symmetry.stage:SymmetryStage`. Neither has an `extra`. `PIPELINE` becomes `("case", "structure", "density", "symmetry", "mesh", …)`, and `_selected` drops both stages without `structure:`. `STRUCTURE_WALK` gains both stages, and the refusal names stage 4 and WP20. Both stages are workspace stages | Stage name = module name, as `structure`, `mesh` and `charge` already are. Stage 2 imports only numpy and scipy (both core), and its export defers gridData as `density/grid.py` already does |
| D2 | `geometry:` resolution | `_PIPELINE_SECTIONS` loses `geometry`. `geometry:` is accepted on a case carrying `structure:`. Beside `inputs.mesh` it is refused naming both, by the upstream rule. With neither, the existing "describes no run" refusal stands. In `resolve()`: `grid_spacing_nm` outside [0.025, 0.05] is refused naming FR-04, and `sharpness` ≤ 0 is refused. Neither is a pydantic narrowing | The §5.3.1 NOTE; WP18 D4's rule that value checks are refusals, so the schema does not move |
| D3 | Radius set | **CHARMM Rmin/2 by (residue, atom)**, transcribed from PDB2PQR 3.7's `dat/CHARMM.DAT` (BSD-3) into `data/radii/pdb2pqr_charmm.yaml`. The file holds radii in Å as printed, the source file's sha256, and the notice. `kernel: gaussian_vdw` binds to this set. The lookup order is: (1) the residue, with `HID/HIE/HIP` read as `HSD/HSE/HSP`; (2) `HIS`, looked up in `HSD`, `HSE` and `HSP`, refused where their radii disagree; (3) the atom aliases `ILE CD1 → CD` and `OXT → OT2`; (4) the patch residues `NTER`, `CTER`, `GLYP` and `PROP`. Anything else is refused naming chain, residue number, residue and atom. There is no element fallback | **Author ruling, 25 September 2026.** Every radius in the reference ensemble's PQR files equals `CHARMM.DAT` [tested], [Design §4](#4-the-radius-set). A guessed radius is a plausible wrong geometry |
| D4 | Density field | Each frame gets its own map, `ρ_f = −expm1(Σ_i log1p(−g_i))` with `g_i = exp(−d²/(σR_i)²)`, accumulated in float64. A term is kept iff `g_i ≥ ε = 10⁻⁶` (a sphere, not a cube), and is floored at `ln 2⁻⁵³`. The ensemble map is the **mean of the per-frame maps**. It is stored float32 | FR-04; `.knowledge/04` §1. The union runs over one frame's atoms; a union across frames would thicken every wall. [Design §1](#1-the-union-density) |
| D5 | Grid | Nodes sit at integer multiples of `h = grid_spacing_nm` in the stage-1 frame, so the axis is a node column and the grid is canonical. In x and y the grid is square and symmetric, with half-width `I·h`, `I = ⌈(max r_atom + max d_cut)/h⌉ + 1`, taken over all frames. z is bounded by the atoms' extent ± `max d_cut`, snapped outward. The spare ring makes every nonzero cell lie wholly inside the outermost annulus | Makes the reduction conserve the map exactly ([Design §3](#3-annular-weights)) |
| D6 | Deposition | Vectorised over atoms grouped by radius, with a cube stencil masked to the sphere. The scatter is `np.bincount` over a z-slab, never `np.add.at` and never a full-grid `minlength`. The loops run slabs outer and frames inner. numpy and scipy are deferred inside functions. Progress is reported per slab, and cancellation is checked per slab | A prototype took 31 s for 2WCD with a full-grid bincount per batch ([Design §5](#5-runtime-and-memory)) |
| D7 | Cₙ average | **Taken in the angular harmonic basis on the unrotated map.** The mean needs no average, because the Cₙ average does not move it. The Cₙ variance is `2Σ_{k≥1}|c_kn|²`, with no rotated deposition and no interpolation. `n = 1` returns the raw variance | Closes the phase plan's open decision. Exact, and it costs one deposition per frame instead of n. Bilinear map rotation lowers the peak Cₙ variance by 3–6 %. [Design §2](#2-the-rotational-average-as-a-harmonic-projection) |
| D8 | Binning | Bins are `r_j = j·h` for j = 0…I, each with half-width h/2. Bin 0 is the disc r < h/2, the axis cell alone. The weights are exact cell–annulus overlap areas, from the `atan2` closed form, in one sparse matrix reused over z. **No bin is interpolated** | FR-05. [Design §3](#3-annular-weights): the weights sum to the exact areas to 4e-13, and interpolating bins 1–2 was worse than binning somewhere in every scheme tried. §5.2 amended |
| D9 | Variance | First the binned mean is **detrended**: the even cubic spline of `μ_j`, taken at each cell's own radius, is subtracted. The Cₙ variance then uses harmonics `kn ≤ π r_j/h`. The raw azimuthal variance is `Σw δ²/A − (Σw δ/A)²`. Below `r = nh/π` nothing is resolved; the artefact records that radius and the per-bin harmonic count. The variance is recorded, not gated | Without detrending, an axisymmetric ring reads a Cₙ variance of 1.9e-4 against a real C12 signal of 8.7e-4. With it, the reading is ≤ 2.3e-7. [Design §3](#3-annular-weights). No threshold is specified (RSK-07) |
| D10 | Artefacts | `DensityMap` is a 3D `.npz` (compressed), float32, indexed `[z, y, x]`, with a JSON header: grid, radius-set name and digest, σ, ε, frames, atom counts by element, hydrogen count. It has `export()` and `read()` for `.dx`, `.ccp4` and `.mrc` through gridData, transposed to gridData's x-first order. `ReducedMap` is an `.npz` holding `mean`, `cn_variance` and `raw_variance` as float64 `[z, r]`, plus `harmonics[r]` and a header. Its `grids()` returns three `RadialGrid`s, which export through `write_grid` | IF-05, both directions for 3D; `RadialGrid` is the (r, z) schema stage 4 reads (phase plan) |
| D11 | Keys | Stage 2: `content_hash("nanopnp/density/v1", {geometry.density, radius set name + file sha256, ε, floor}, inputs=(stage-1 key,))`. Stage 3: `content_hash("nanopnp/reduced/v1", {n, Δr, detrend: "even-cubic", harmonics: "nyquist"}, inputs=(stage-2 key,))`. Payload digests are recorded and re-checked (VER-23) | §5.3.2. A code constant that moves a number is in the key |
| D12 | Errors | `DensityInputError` is a radius refusal. `DensityGateError` fires when the map is not finite or leaves [0, 1] by more than float32 round-off, naming the voxel. Both map to `EXIT_GATE` | QR-12; the precedent of WP18 D12 |
| D13 | Manifest | `geometry_and_mesh` gains `density` (grid, radius set and digest, frames, atoms, hydrogens) and `reduction` (n, bins, unresolved radius, and the maximum Cₙ and non-Cₙ variance with their (r, z)). Both come from the summaries | FR-25; WP18 D14 |
| D14 | Test fixture | `_prepared_rotation` and `_dodecamer` move from `test_structure_stage.py` into a root `tests/conftest.py` session fixture, `prepared_2wcd`. It writes chains A–L of the vendored 2WCD, rigidly moved into an admitted frame | Tiers 1 and 2 need it here, and WP22 needs it next (WP18 D16 Outcome) |
| D15 | Public API | No new name | IF-01 NOTE; WP18 D15 |

> **Outcome — D3's lookup lives in `density/radii.py`, and three rules were sharpened.** The
> radius set is its own module rather than part of `union.py`, because stage 2 and the tests both
> read it without the deposition. What executing D3 against `CHARMM.DAT` fixed:
>
> - **The patches are residue-specific.** A residue is patched by `NTER` and `CTER`, `GLY` by
>   `GLYP` and `CTER`, and `PRO` by `PROP` and `CTER`. These rules are data, in the file.
> - **An unknown residue is refused before the patches are consulted.** Otherwise `NTER` names
>   `CA` and places an unknown residue's backbone without a word.
> - **`HIS` agreement is counted among the histidines that name the atom.** `HE2` is in HSE and
>   HSP but not HSD, and they agree, so it resolves. `HD2` and `HE1` disagree and are refused. The
>   §5.3.1 NOTE now says "every one of those three that names the atom".
> - **A zero radius is refused.** `DUM` has one, and a zero-width kernel deposits nothing.
>
> 2WCD resolves all 26,844 atoms: 216 `ILE CD1` through the alias, and 120 `HIS` atoms by
> agreement (`.knowledge/07` §2).

> **Outcome — D5 spares one z node at each end too, and D6 groups by stencil, not by radius.**
> z runs from `⌊(z_min − d)/h⌋ − 1` to `⌈(z_max + d)/h⌉ + 1`, so the NOTE's "one cell to spare"
> holds axially as well as radially. Atoms are grouped by stencil half-width `m = ⌈d/h + ½⌉`,
> and each group gathers a separable Gaussian `e_x e_y e_z` over the spherical offset set of its
> widest member. The scatter is a `np.bincount` over a z-slab of at most 4e6 cells, 1e6 terms at
> a time. 2WCD deposits in 17.0 s and runs stages 1–3 in a 0.47 GB peak, against the ≤ 60 s and
> < 1.5 GB of [Design §5](#5-runtime-and-memory).

> **Outcome (review, PR #40) — cancellation is per frame, and three gaps closed.** With frames
> inner, D6's per-slab check left the ClyA-AS run 8 checks in 980 s, about 2 min to honour a
> cancel. Cancellation and progress are now checked per frame within a slab, and each frame's
> node indices are computed there, so memory no longer grows with the frame count. Three other
> changes came out of the review:
>
> - A DX or CCP4 file whose origin is off the lattice of its spacing is now refused. Before, it
>   was rounded onto the lattice, which moved every value by up to h/2.
> - A non-finite `sharpness` is refused. Before, it crashed in the grid builder.
> - The radius refusal names the first failing atom in file order.

> **Outcome — two switches exist for the tests alone.** `deposit(float64=True)` keeps the map in
> float64, for VER-49's 1e-15 closed forms. `reduce_map(detrend=False)` skips D9's detrend, for
> VER-50's discrimination check. Neither is reachable from a case, and the stage-3 key records
> `detrend: "even-cubic"`.

> **Outcome — D14's conftest also holds a synthetic C12.** `synthetic_c12` writes an exact
> C12 of 12 chains × 8 alanines as a PDB, and `c12_assembly` returns the generator, so VER-50's
> invariance test can turn it before deposition.

### Work items

1. **Radius data** (D3). Write `data/radii/pdb2pqr_charmm.yaml` with a `nanopnp/radii/v1` header.
   The schema is a pydantic model with `name`, `source` (file, version, sha256, licence) and
   `residues` (residue → atom → radius in Å). The aliases are also data. Add `radii_file()` in
   `core/paths.py` and a `LICENSES-BUNDLE.md` row. Read [Design §4](#4-the-radius-set) first.
2. **`density/union.py`** (D4–D6). Radius lookup; the grid; slab deposition; the frame mean.
   Write the closed-form tests **first** ([Design §1](#1-the-union-density)).
3. **`density/map.py`** (D10). `DensityMap`, `.npz` IO, `digest()`, export and read through
   gridData.
4. **`symmetry/annular.py`** (D8). Overlap weights and the sparse bin matrix. Phase 3's FR-13
   projection reuses it. Read [Design §3](#3-annular-weights) first.
5. **`symmetry/reduce.py`** (D7, D9). Mean, detrend, harmonics, variances and `ReducedMap`. Read
   [Design §2](#2-the-rotational-average-as-a-harmonic-projection) first.
6. **The stage modules and the registry** (D1, D11, D12): `density/stage.py`, `symmetry/stage.py`,
   and `EXIT_CODES` in `cli/errors.py`.
7. **Case, walk and manifest** (D1, D2, D13). `io/case.py`, `io/run.py`, and the reasons in
   `io/defaults.py` for `geometry.density.kernel`, `geometry.contour.smoothing` and
   `geometry.analyte.shape`. The `DensitySpec` field descriptions state the NOTE, so VER-45 carries
   it.
8. **Tests and the fixture** (D14), per [Verification](#verification).
9. **Specification, changelog and knowledge.** Add VER-49 and VER-50 to §7.2, with the text below.
   Map them in Appendix A: FR-04 → VER-49; FR-05 → VER-01, VER-50; FR-06 → VER-50;
   CON-04 → VER-50; IF-05 adds both. Recount the coverage line. Write `CHANGELOG.md`
   `[0.9.0-alpha.3]`. Add Outcomes here and update `current.md`.

### Verification

**VER-49** (for §7.2): *The density map.*

- One atom gives `g` exactly, and two atoms give `g₁ + g₂ − g₁g₂`.
- On random clusters with coincident atoms, the map stays finite and within [0, 1].
- The truncated map differs from the untruncated one, at every voxel, by no more than the sum of
  `g/(1 − g)` over the terms dropped there.
- Two frames of one displaced atom average to `(g_a + g_b)/2`, not to their union.
- The grid nodes are multiples of h, the axis is a node column, and every retained term lies inside
  the box.
- Each lookup route of D3 resolves. An unknown atom, and a `HIS` hydrogen whose radius the three
  histidines disagree on, are each refused by name.
- The shipped table equals `CHARMM.DAT`.
- The map round-trips through `.npz`, OpenDX and CCP4.
- Out-of-range `grid_spacing_nm` and `sharpness` are refused.
- A `structure:` case walks to stage 3, and a full walk or sweep is refused naming stage 4.
  `geometry:` beside `inputs.mesh` is refused, and so is `geometry:` without `structure:`.
- The stages are listed without importing their modules.

**VER-50** (for §7.2): *The reduction to (r, z).*

- The annular weights sum to `2πjh²` (and to `πh²/4` for bin 0) to 1e-11. Each interior cell's
  weights sum to `h²`, and the integral of a map is conserved.
- An off-axis Gaussian matches the closed forms of [Design §2](#2-the-rotational-average-as-a-harmonic-projection)
  for the mean, the Cₙ variance and the raw variance.
- Axisymmetric inputs give no variance, while the same computation without detrending does. This
  makes the test discriminating.
- A `cos(mθ)` modulation gives `b²/2` for both variances when n | m. Otherwise it gives a Cₙ
  variance of zero and a raw variance of `b²/2`.
- A synthetic C12 assembly's reduction is unchanged by a 90° turn to round-off, and by a 30° turn
  within the off-axis tolerances.
- The artefact round-trips and exports.

| Test | Tier | Identifiers | Oracle | Tolerance and source |
|---|---|---|---|---|
| `tests/tier1/test_density.py::test_ver49_closed_forms` | 1 | VER-49, FR-04 | One atom; two atoms 0.2 nm apart | 1e-15 in float64 and 6e-8 in the float32 store |
| `…::test_ver49_union_is_bounded` | 1 | VER-49, QR-12 | 500 random atoms, 10 of them coincident | finite; within [0, 1]; the gate fires on an injected NaN, naming the voxel |
| `…::test_ver49_truncation_bound` | 1 | VER-49 | 200 atoms: truncated against a brute-force ε = 0 evaluation | at each voxel, `|Δρ| ≤ Σ_dropped g/(1−g) + 1e-15`. The maximum is logged (predicted ≈ 1e-5, [Design §1](#1-the-union-density)) |
| `…::test_ver49_frames_average_not_union` | 1 | VER-49, FR-04 | One atom in two frames, 0.3 nm apart | `(g_a+g_b)/2` to 1e-7. The union differs by more than 1e-2 at the midpoint |
| `…::test_ver49_grid_is_canonical` | 1 | VER-49 | Frames permuted; atoms moved by less than h | Identical node set; axis column present; the box contains every term |
| `…::test_ver49_radius_lookup` | 1 | VER-49, QR-12 | Each D3 route; `ILE CD1`; `OXT`; HSE's `HT1`; an unknown residue; a `HIS HD2` | Exact radii. `DensityInputError` names chain, residue number, residue and atom |
| `…::test_ver49_radius_table_matches_charmm_dat` | 1 | VER-49 | pdb2pqr's `CHARMM.DAT` (the `structure` extra) | Exact, every entry. Skips without pdb2pqr |
| `…::test_ver49_map_round_trip_and_export` | 1 | VER-49, IF-05, FR-27 | `.npz`, `.dx` and `.ccp4` on a small map. The key is stable across processes, and a hand edit is recorded | origin, spacing and shape exact; values within each format's precision, as VER-29 states it |
| `…::test_ver49_resolution_and_walk_rules` | 1 | VER-49, IF-02 | Spacings 0.02 and 0.06; σ = 0; `upto="symmetry"`; a full walk; a sweep; `geometry:` with `inputs.mesh`; `geometry:` alone | Each is refused naming the key, the stage or both keys |
| `tests/tier1/test_reduction.py::test_ver50_annular_weights_are_exact` | 1 | VER-50, FR-05 | Closed-form annulus areas; a random map inside the disc | 1e-11 relative (measured 4e-13); conservation to 1e-12 |
| `…::test_ver50_off_axis_gaussian_closed_forms` | 1 | VER-50, FR-05, FR-06 | w ∈ {0.15, 0.2} nm; r_i ∈ {1, 1.7, 2, 5} nm; n ∈ {7, 12}; h = 0.05 | Mean ≤ 1e-3 (3.5e-4 measured). Cₙ variance ≤ 3e-5 (1.2e-5), and ≤ 2 % at its peak (0.8 %). Raw variance ≤ 1e-3 (3.2e-4) |
| `…::test_ver50_axisymmetric_input_has_no_variance` | 1 | VER-50, FR-06, CON-04 | An on-axis Gaussian; rings at 0.4 and 2 nm; w ∈ {0.15, 0.2}; n ∈ {7, 12} | Cₙ ≤ 1e-6 (2.3e-7). Raw ≤ 5e-5 (1.9e-5). Undetrended, the 2 nm ring reads a Cₙ variance above 1e-4 (1.9e-4) |
| `…::test_ver50_cos_modulation` | 1 | VER-50, FR-05, FR-06 | `0.4e(r) + 0.2e(r)cos(mθ)`, with `e = exp(−(r−3)²/0.64)`, m ∈ {n, 2n, 5, 6, 3} | At r ≥ 1 nm and relative to the peak: when n \| m, both variances are within 5e-3 of `b²/2` (1.5e-3). Otherwise Cₙ ≤ 1e-3 (7.1e-5) and raw within 5e-3 (1.2e-3). Mean ≤ 1e-3 (2.5e-4) |
| `…::test_ver50_cn_invariance` | 1 | VER-50, FR-05 | A synthetic C12 of 12 × 40 atoms, run through stage 2, turned by 90° and by 30° | 90°: 1e-12. 30°: within the off-axis tolerances |
| `…::test_ver50_unresolved_region_and_artefact` | 1 | VER-50, FR-27, VER-23 | `harmonics` is 0 below `nh/π`, and the header names that radius. `.npz` round trip; `RadialGrid` export; hand edit | exact |
| `test_stages.py`, `test_cli.py`, `test_manifest.py`, `test_case_schema*.py` (existing) | 1 | VER-25, VER-32, VER-24, VER-45 | Registry names; modules not imported by a listing; the new errors classified; the reasons updated; the `geometry:` refusal tests moved to D2 | — |
| `tests/tier2/test_density_2wcd.py::test_ver49_ver50_2wcd_to_stage_three` | 2 | VER-49, VER-50 | `run_case(upto="symmetry")` on `prepared_2wcd`: every atom resolves; bounds; conservation; `cn ≤ raw + 1e-4`; lumen open (`μ(0, z) < 0.25` over the central 80 % of the Cα extent); runtimes logged | Conservation 1e-9 relative. The rest are inequalities |
| `…::test_ver49_2wcd_budget` (`slow`) | 2 | VER-49 | Wall-clock and peak RSS of stages 2 and 3 | Recorded, never gated. Predicted ≤ 60 s and < 1.5 GB ([Design §5](#5-runtime-and-memory)) |
| `tests/tier3/test_density_ensemble.py::test_ver50_clya_as_ensemble` | 3 | VER-49, VER-50 | `prod5_clya_as` with `frames: {count: 50}` to stage 3. Stride ⌊98/50⌋ = 1 ending on the last frame gives DCD frames 48–97, the paper's final 5 ns (`.knowledge/04` §1.1); the test asserts those indices. Records runtime, memory, and the maximum Cₙ and non-Cₙ variance with their (r, z). Skips without the archive | Indices exact; the rest recorded |

```bash
uv run pytest tests/tier1/test_density.py tests/tier1/test_reduction.py -v
uv run pytest tests/tier2/test_density_2wcd.py -v --log-cli-level=INFO
uv run pytest -m slow tests/tier2/test_density_2wcd.py --log-cli-level=INFO
uv run pytest -m tier3 tests/tier3/test_density_ensemble.py -v
.claude/hooks/gate.sh run
```

> **Outcome — delivered as tabled, with one test added.** `test_density.py` holds 29 tests and
> `test_reduction.py` 33, and both Tier-2 tests pass. `.claude/hooks/gate.sh run` passed on
> 25 September 2026. The measured numbers are in `.knowledge/07` §2. What moved:
>
> - **VER-50's invariance test gained a 15° turn.** A 30° turn is one of the assembly's own
>   symmetries, so it agrees to the float32 rounding and tests nothing about the grid. A 15° turn
>   moves the mean by 5.5e-4 and each variance by 0.26 % of its 0.175 peak. It is asserted against
>   the off-axis test's 1e-3 for the mean, and against 1 % of the peak for each variance, which is
>   inside that test's 2 %.
> - **The undetrended 2 nm ring reads 1.17e-4 to 2.3e-4** across the widths and orders, against
>   the plan's 1.9e-4. The 1e-4 floor that makes the test discriminating still holds.
> - **The OpenDX round trip allows 5e-7 + 2⁻²⁴**, because the float32 map is rounded again on
>   read. CCP4 and MRC are exact once the spacing is read at `%.7g`.
> - **2WCD: 17.0 s and 6.9 s for stages 2 and 3, at a 0.47 GB peak.** The slice integrals are
>   conserved to 6.1e-16, and the axis bin is empty over the central 80 % of the Cα extent.
> - **Tier 3, the ClyA-AS ensemble: DCD frames 48–97 exactly.** 54,075 atoms, 27,134 of them
>   hydrogens, on a 339 × 293 × 293 grid. Stage 2 took 980.6 s, 19.6 s a frame, inside the
>   predicted 15–25 min; part of the run shared the machine with the gate. Stage 3 took 9.9 s, and
>   the session peaked at 0.56 GB. The largest C12 variance is 0.171, at r = 4.70 nm and
>   z = 6.55 nm. The largest non-C12 variance is 0.088, at r = 2.00 nm and z = −1.70 nm, inside
>   the lumen and nine times the crystal's. WP22 records the variance along the contour.

### Out of scope

- **Contour, probe-radius profile and the FR-08 gate** go to WP20. **VAL-05** and the isolevel
  sensitivity go to WP22.
- **Export commands and the GUI views** go to WP24. **The guide and example 06** go to WP25.
- **The dielectric field from the density** (FR-15) and **the charge projection** (FR-13) belong
  to Phase 3. FR-13 reuses D8's weights.
- **A variance threshold.** None is specified. WP22 records ClyA's variance along the contour.
- **A supplied density map.** No `inputs:` key exists for one, and adding a key would move the
  schema (§8.2.2 B3).
- **The frame-to-frame (temporal) variance.**
- **Hydrogen handling.** `structure.source.selection` decides which atoms are deposited, and the
  hydrogen count is recorded (D10).

### Open questions

None. The radius set is ruled (D3). The three questions this plan carried to WP22 were answered
by the author on 25 September 2026 (`.knowledge/04` §1.1, §8):

1. **Frame spacing: 100 ps.** The archived PQR files are all the frames. Matched by coordinates,
   the DCD's frames are PQRs 02–99 in time order, so the paper's final 5 ns are DCD frames 48–97.
2. **Hydrogens: included.** The density was built from the full-atom trajectory, which is what
   D10's hydrogen count records. WP22 must account for the vendored 2WCD having none.
3. **G9: 0 in the MD frame**, which was centred on the middle of the bilayer.

## Design

### 1. The union density

`ρ_f(x) = 1 − Π_i (1 − g_i(x))`, with `g_i = exp(−|x − a_i|²/w_i²)` and `w_i = σ R_i`. Each
factor lies in [0, 1], so `ρ_f` does too. With `S = Σ_i log1p(−g_i) ≤ 0`, `ρ_f = −expm1(S)`, which
is accurate at both ends. At an atom centre `g = 1` and `log1p(−1) = −∞`, so a term is floored at
`ln 2⁻⁵³ = −36.74`; then `1 − ρ ≤ 1.1e-16`, below float64's spacing at 1.

**Truncation.** A term is kept iff `g_i ≥ ε`, that is `|x − a_i| ≤ d_i = w_i √ln(1/ε)`. With
`√ln 10⁶ = 3.7169`, the CHARMM Cα radius 2.275 Å and σ = 0.93, `w = 0.2116` nm and
`d = 0.786` nm: a stencil half-width of 16 cells at h = 0.05. If `T(x)` is the set of dropped
terms, then `S_exact = S_trunc + Σ_T log1p(−g_i)` and
`|ρ_exact − ρ_trunc| = e^{S_trunc}(1 − e^{−δ}) ≤ δ ≤ Σ_T g_i/(1 − g_i)`. That per-voxel bound is
what VER-49 asserts. For its size, integrate the Gaussian tail over the shell beyond `d` at the
protein's heavy-atom density (about 58 nm⁻³):
`4πn w³ ∫_{3.717}^∞ u²e^{−u²} du ≈ 58 · 4π · 0.0095 · 1.9e-6 ≈ 1.3e-5`. That is the predicted
maximum error, four orders of magnitude below the 0.25 isolevel.

**Frames.** FR-04's ensemble average is `ρ̄ = (1/F)Σ_f ρ_f`. A union across frames,
`1 − Π_f Π_i(1 − g)`, would count a fluctuating side chain as present wherever it ever was, and
would thicken every wall. VER-49's two-frame test tells the two apart by `g_a g_b/2`.

### 2. The rotational average as a harmonic projection

At fixed (r, z), write `ρ(θ) = Σ_m c_m e^{imθ}`, with `c_{−m} = c̄_m`. Rotation by α maps
`ρ(θ) → ρ(θ − α)` and `c_m → c_m e^{−imα}`. The Cₙ average `P_n ρ = (1/n)Σ_{k<n} ρ(θ − 2πk/n)`
therefore has coefficients `c_m · (1/n)Σ_k e^{−2πimk/n} = c_m·[n | m]`. Hence:

- `⟨P_n ρ⟩_θ = c_0 = ⟨ρ⟩_θ`: FR-05's order leaves the mean unchanged;
- `Var_θ(P_n ρ) = 2Σ_{k≥1}|c_{kn}|²`, the FR-06 statistic;
- `Var_θ(ρ) = 2Σ_{m≥1}|c_m|²`. The difference `2Σ_{n∤m}|c_m|²` is the variation that is not
  Cₙ-symmetric: chain asymmetry and thermal disorder.

CON-04's widening comes from the Cₙ structure the reduction discards, so the Cₙ variance is the
first-class output. The difference is reported beside it.

**Closed forms (VER-50's oracle).** For one Gaussian at `(r_i, 0, z_i)`, let
`E = exp(−(r² + r_i² + Δz²)/w²)` and `β = 2 r r_i/w²`. Then `exp(β cos θ) = Σ_m I_m(β) e^{imθ}`
gives `c_m = E I_m(β)`. So the mean is `E I₀(β)`, the Cₙ variance is `2E²Σ_{k≥1} I_{kn}(β)²`, and
by `Σ_m I_m(β)² = I₀(2β)` the raw variance is `E² I₀(2β) − (E I₀(β))²`. For numerical evaluation,
`E I_m(β) = exp(−((r − r_i)² + Δz²)/w²)·ive(m, β)`, which cannot overflow.

**The three methods, measured.** Peak Cₙ variance for a C12 ring (n = 12, h = 0.05 nm; scratch
prototype, 25 September 2026):

| Case | Closed form | Harmonic projection (D7) | Exact rotated copies, binned | Bilinear map rotation |
|---|---|---|---|---|
| w = 0.2, r_i = 2 | 8.660e-4 | −0.42 % | −1.39 % | −3.8 % |
| w = 0.15, r_i = 1.7 | 8.469e-4 | −0.70 % | −2.44 % | −6.1 % |
| w = 0.2, r_i = 5 | 5.376e-4 | −0.29 % | −1.40 % | −3.3 % |
| Cost per frame | — | 1 deposition | n depositions | 1 deposition + n interpolations |

Bilinear rotation is also not Cₙ-symmetric in its own error: the k = 0, 3, 6 and 9 copies are
exact grid permutations and the other eight are smoothed. It biases the variance low, which hides
RSK-07 rather than exposing it.

### 3. Annular weights

For `X, Y ≥ 0`, let `G(X, Y; R)` be the area of `{0 ≤ x ≤ X, 0 ≤ y ≤ Y, x² + y² ≤ R²}`. Clip X
and Y to R. Let `x* = √((R − Y)(R + Y))`, and let `F(x) = ½(x s + R² atan2(x, s))` with
`s = √((R − x)(R + x))`. Then `G = min(X, x*)·Y + [X > x*](F(X) − F(x*))`. The disc's overlap
with a cell `[x₀, x₁] × [y₀, y₁]` is `G₁₁ − G₀₁ − G₁₀ + G₀₀`, with G extended oddly in each sign.
The overlap with an annulus is the difference of two discs.

**Conditioning [tested].** Writing F with `asin(x/R)` leaves the weights summing to the exact
annulus areas only to 2.3e-7. `asin` is ill-conditioned as x → R, and the error is amplified by
R². The `atan2` form gives 4.0e-13.

**Bins.** `r_j = jh`, with the annulus `[(j − ½)h, (j + ½)h]`, and bin 0 the disc of radius h/2,
which lies inside the axis cell. So `μ_0` is the exact axis sample. With the D5 spare ring, each
cell with ρ ≠ 0 lies inside the outer circle, and its weights sum to h². Hence
`Σ_j μ_j A_j = Σ_p ρ_p h²` slice by slice.

**Inner bins [tested].** Three variants were compared on bins 1–2 (the §5.2 note's "innermost 2–3
bins interpolated") over 15 on- and off-axis Gaussians: the binned value; linear interpolation in
r² from the axis sample to bin 3; and an even quartic through the axis, bin 3 and bin 4. In
bins 1–2 the binned error reached 6× that of bins 3–5. Each interpolant was still worse than
binning in some cases (up to 7.6e-2 against 2.9e-2). The note compensated for centre-assigned binning, whose annulus areas
are wrong near the axis, and exact weights remove the cause.

**Detrending [tested].** A cell's value varies with its radius inside a bin of width h. Binned,
that radial gradient reads as azimuthal variance: about `(∂ρ/∂r)² h²/12`, or 3.8e-3 for a ring
with w = 0.2 nm. It also aliases into the harmonic estimates. The fix is to subtract
`μ̃(r_p, z)`, the cubic spline through `(r_j, μ_j)` extended evenly about r = 0 so that
`μ̃′(0) = 0`, before either variance is computed. On axisymmetric inputs:

| Input (n = 12) | Cₙ, raw | Cₙ, linear detrend | Cₙ, even-cubic detrend | Raw variance, raw → even-cubic |
|---|---|---|---|---|
| On-axis Gaussian, w = 0.2 | 4.2e-5 | 4.1e-7 | 4.7e-8 | 5.7e-3 → 1.1e-5 |
| Ring r₀ = 2, w = 0.2 | 1.9e-4 | 5.4e-6 | 2.0e-8 | 7.0e-3 → 3.6e-6 |
| Ring r₀ = 2, w = 0.15 | 2.3e-4 | 1.4e-5 | 9.9e-8 | 1.2e-2 → 1.6e-5 |
| Ring r₀ = 0.4, w = 0.15 | 1.3e-4 | 2.6e-5 | 1.5e-7 | 1.1e-2 → 1.9e-5 |

**Resolution.** A ring of circumference `2πr_j` sampled at h resolves `m < πr_j/h`. The Cₙ
variance therefore sums `k = 1 … K_j = ⌊πr_j/(nh)⌋`. Below `r = nh/π` (0.19 nm for C12 at
0.05 nm), `K_j = 0` and nothing is resolved. There, `c_{kn} ∝ r^{kn}`, and a pore's axis is lumen.
The artefact records `K_j` and the radius rather than presenting the zero as measured.

### 4. The radius set

The author's archive `md_data/prod5_trajectory_last_10ns/prod5_trajectory_last_10ns.7z` holds
99 files, `prod5_protein_aligned_100ps_NN.pdb.pqr`. They were written by PDB2PQR 2.1.1 with
`--with-ph=7.5 --ph-calc-method=propka --ff=charmm --ffout=charmm --chain`, and each holds 54,075
atoms, 27,134 of them hydrogens. Frame 01 has 318 distinct (residue, atom) pairs. 313 of them
carry exactly the radius of PDB2PQR 3.7.1's `CHARMM.DAT`. The other five, `GLU HT1–HT3` and
`HSE OT1–OT2`, are that file's `NTER` and `CTER` patch entries, with equal radii [tested]. The radii
are CHARMM Rmin/2 (the file's header: "Radius and epsilon from par_all27_prot_na.prm"). By
element they span C 1.80–2.275, N 1.85, O 1.70–1.77, S 2.00 and H 0.2245–1.468 Å.

The vendored 2WCD (chains A–L, 26,844 atoms, no hydrogens) differs from `CHARMM.DAT` in exactly
two ways: `ILE CD1` (216 atoms), which CHARMM calls `CD`, and `HIS` (120 atoms), which CHARMM
splits into `HSD`, `HSE` and `HSP`. Those three agree on every heavy-atom radius and disagree on
`HD2` (1.468 against 0.9) and `HE1` (0.9 against 0.7). Hence D3's rule: a `HIS` atom resolves
only where the three agree. The author's MD files use CHARMM names directly.

### 5. Runtime and memory

A scratch prototype, not the implementation, took **31.2 s** for one deposition of the 2WCD
dodecamer: 26,844 atoms, h = 0.05, ε = 1e-6, a 295 × 287 × 341 grid in the crystal frame. It used
a full-grid `bincount` per 256-atom batch, and allocating that 231 MB array 105 times dominates
the cost. Slab-wise scatter removes it.

In the aligned frame, D5's grid is about 270 × 270 × 340 = 2.5e7 cells: 99 MB in float32, which
is the phase plan's ≈ 90 MB. Predicted peak memory is the float32 map, plus one float64 slab, plus
the stencil batch, plus stage 3's per-slab detrend: under 1.5 GB.

The harmonics cost `K_max ≈ π · 6.8/(12 · 0.05) ≈ 35` sparse products with 1.5e5 nonzeros over
340 slices, a few seconds. Stage 2 is therefore predicted at ≤ 60 s for 2WCD at 0.05 nm. The
paper's 50-frame ensemble costs 50 depositions: about 15–25 min at Tier 3, with hydrogens adding
about half again. An n-copy average would have cost 12 times that: 3–5 h.
