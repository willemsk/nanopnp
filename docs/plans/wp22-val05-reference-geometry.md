# WP22 — VAL-05: the pipeline against the reference geometry

**Status: delivered, 28 September 2026.** Written 28 September 2026. WP21 has merged (tagged
`v0.9.0-alpha.5`), and so has the CODE_REVIEW_002 follow-up on `main`. This package inherits the
whole geometry chain: stages 1–4 (WP18–WP20), which emit `nanopnp/profile/v1` in the stage-1 frame,
and stages 5–6 (WP21), which apply `geometry.membrane.centre_z_nm` and mesh under the D9 wall-size
gate. It also inherits the prepared 2WCD fixture in `tests/conftest.py`, the ensemble archive's
Tier-3 pattern in `tests/tier3/test_density_ensemble.py`, and `innermost_crossings` and
`plane_crossings`. It builds no new stage.

This is a work package of the [Phase 2 plan](phase-2-geometry-pipeline.md), and it is the phase
gate: criterion 3 of the plan's *Verification*. `SPECIFICATION.md` governs. Where this file and the
specification disagree, the specification is right and this file is wrong. Requirement identifiers
here are pointers into the specification, never restatements of it. This plan's commit adds the
§7.4 NOTE on VAL-05, the metric, the registration and the tolerances. It also records the
author's rulings of 28 September 2026 in `.knowledge/`.

## Execution brief

### Scope

- **VAL-05, both legs of §8.2.2 B2.** The 2WCD leg runs stages 1–6 in Tier 2 and is gated on every
  push. The ClyA-AS ensemble leg reads `$NANOPNP_REFERENCE_DATA`, runs at Tier 3 and skips visibly
  without the archive. Each leg compares the lumen radius profile and the constriction radius with
  the delivered 185-vertex polygon over `z ∈ [−1.85, 12.25]` nm, in the model frame.
- **The comparison as code**, `nanopnp.validation.geometry`. It holds the metric, the axial
  registration, the tolerances and the attribution model, so the tests and the end-of-phase report
  compute one set of numbers.
- **Recorded, not gated** (phase plan, WP22): the isolevel sensitivity (G2); the FR-06 variance
  along z; the generated mesh against the reference figures; one frozen case's conductance on the
  generated mesh against the reference mesh. Also recorded is the attribution of the offset to the
  reference's construction, which the author's answers of 28 September 2026 make possible.

**This brief runs to about 2,200 words, over its 1,200-word target.** The decisions table carries two author rulings, D4 and D5, and one attribution, D7. Each changes what a pass or a miss of the phase gate means, so none of them is cut to fit.

### Pointers

- **Normative:** VAL-05 (§7.4) and the §7.4 NOTE this commit adds; §8.2.2 B2; §5.2 stages 1–6;
  §5.2.1 (the fixture, the DECISION on the geometry of record, the radius band NOTE); §5.2.2 (the
  reference mesh figures); FR-06, FR-07, FR-09, FR-10; QR-12; §7.1 (Tier 3 is recorded).
- **Knowledge:** `.knowledge/04` §1 (the isolevel, G2), §1.1 (the archive, the Cα centroid, G9),
  §1.2 (the script and its erratum, now attributed), §1.3, §2, §4, §8 G2, G3 and G9; `.knowledge/09`
  (the reference's quality measure is not stated).
- **Evidence inherited:** [WP20 Design §7](wp20-contour-extraction.md#7-against-the-reference-polygon-recorded-for-wp22)
  (the ensemble against the polygon); [WP21 Outcomes](wp21-cad-assembly-and-meshing.md#verification)
  (the 2WCD walk and its test-time registration).
- **Amended in this commit:** §7.4, a NOTE on VAL-05 (D2–D7). `.knowledge/04` §1.2 and §1.4 (new),
  and `.knowledge/00-index.md` author ruling 14, which closes *Still open* 3. The phase plan's
  *VAL-05 tolerances* open decision is marked settled.
- **Code:** `geometry/contour.py` (`innermost_crossings`, `lumen_change`, the stage-4 record);
  `mesh/profile.py` (`plane_crossings`, `load_profile`); `geometry/region.py` (`RegionRecord`, its
  model-frame vertices); `structure/ensemble.py` (`AlignedEnsemble`); `io/run.py` (`run_case`,
  `upto`); `core/paths.py` (`reference_file`); `tests/conftest.py` (`prepared_2wcd`);
  `tests/tier2/test_pipeline_2wcd.py` (`registered`); `tests/tier3/test_density_ensemble.py`.

### Decisions

| # | Decision | Choice | Why / source |
|---|---|---|---|
| D1 | Where the comparison lives | `src/nanopnp/validation/geometry.py`, new. `compare_profiles(ours, reference) -> ProfileComparison`, a pydantic model. `register_by_centroid(...)`, the `TOLERANCES` per leg, `pqr2grid_radius(...)` and the isolevel sweep helper. No new public name | One implementation for both legs and for the end-of-phase report. `validation/` already holds the Tier-3 harness. IF-01 NOTE |
| D2 | Comparison surface | Both polygons in the **model frame**. Ours is the stage-5 `RegionRecord`'s vertices, asserted equal to stage 4's minus `centre_z_nm`. The planes are the 282 mid-planes `z_k = −1.85 + (k + ½)·0.05` nm over the reference's extent. The lumen radius is `innermost_crossings` on each plane. Ours must cross every plane except within 2h = 0.1 nm of the reference's tips (−1.85, 12.25). A missing plane elsewhere fails, naming z (QR-12) | The spacing is the density grid's h and WP20 Design §7's surface, so the numbers continue. Reading stage 5 checks the model-frame shift as the pipeline applies it. The tip band admits a rounded end one plane short, as 2WCD is at −1.794 nm |
| D3 | Metric | Three numbers are gated. **`ε_G`** is the first-order relative conductance change of a bulk series resistor on replacing the reference lumen by ours, `2 Σ_k (Δ_k/r_k) r_k⁻² / Σ_k r_k⁻²`, with `Δ = r_ours − r_ref` and `r = r_ref`. The **rms Δ** is over the compared planes. **`Δr_c`** is the difference in constriction radius, each polygon's minimum lumen radius over `z ∈ [−1.85, 1.6]`, located separately. Recorded beside them: the mean and the located max \|Δ\|, the exact series ratio, the outer surface (the second crossing) mean and rms, both tips, and the constriction and cis-lumen means | [Design §1](#1-the-metric). "Argued from `G ∝ r²`" (phase plan) is made a number, not an adjective. The constriction window is `.knowledge/04` §2's trans constriction |
| D4 | Ensemble tolerance, the phase gate | **\|ε_G\| ≤ 5 %, \|Δr_c\| ≤ 0.1 nm, rms Δ ≤ 0.1 nm.** Gated at Tier 3, whose verdict is recorded (§7.1) | **Author ruling, 28 September 2026.** [Design §2](#2-the-tolerances): the 25 % level is the method's own unjustified choice (G2), and ±0.1 of isolevel moves ε_G by about ±5 %. 0.1 nm is 2h, the stage-4 closing radius below which features are erased by design. Predicted from WP20 Design §7: ε_G ≈ −4.5 %, Δr_c = −0.040 nm, rms ≈ 0.09 nm. So the prediction passes narrowly, and it is not tuned |
| D5 | 2WCD tolerance, gated on every push | **\|ε_G\| ≤ 10 %, \|Δr_c\| ≤ 0.1 nm, rms Δ ≤ 0.2 nm** | **Author ruling, 28 September 2026**, "looser" per B2. 2WCD lacks residues 1–7, its hydrogens and the MD relaxation. WP20 Design §7 puts its lumen 0.067 nm narrower than the ensemble's, about 4 % of G. Measured on 2WCD on 28 September 2026: −8.08 %, −0.0205 nm, 0.158 nm ([Design §4](#4-measured-on-2wcd)) |
| D6 | Axial registration | **Ensemble:** `centre_z_nm = 0` in the stage-1 frame (G9, author ruling 12). Stage 1 keeps the file's axial coordinate (`z′ = â·x`, WP18 D8). **2WCD:** registered to the MD frame by Cα centroid. `centre_z_nm = z̄_Cα − Z_MD`, where z̄_Cα is the stage-1-frame centroid of the Cα of residues 8–292, chains A–L. `Z_MD = 5.63 nm` is the same centroid of the MD structure. The Tier-3 leg measures `Z_MD` on the 50-frame ensemble mean and asserts it within 0.01 nm of the constant. No offset is fitted. The rms-optimal offset is recorded as a diagnostic, never used. `test_pipeline_2wcd.py` switches from its *trans* tip + 1.85 nm to this registration | [Design §3](#3-the-axial-registration). Residues 8–292 are common to both structures, so the MD's residue 7 cannot bias the centroid. On the prepared 2WCD the centroid gives 4.5727 nm, and the fit 4.580. Fitting would absorb part of what VAL-05 measures. `Z_MD` is `.knowledge/04` §1.1's 56.3 Å, pinned by Tier 3. One registration of 2WCD in the suite, as WP21's Outcomes defer to this package |
| D7 | Attribution to the reference's construction | Recorded on both legs, never gated. Our conditioned contour is mapped through `pqr2grid`'s binning at **L = 15 nm, h = 0.05 nm**, `r_a = (r/w − ½)h` with `w/h = (2L + 1)/(2L + h) = 1.03161`, and compared with the polygon. The residual is attributed to the hand edit. Conditioning's share is stage 4's own record (`lumen_change`). Constants are cited to `.knowledge/04` §1.2 | **Author, 28 September 2026:** the polygon was made with `pqr2grid`'s binning at L = 15 nm, and the hand edit moved vertices. On 2WCD the erratum alone gives ε_G = −16.0 % and a lumen 0.242 nm narrower than the polygon's, so the hand edit widened the lumen by about 0.24 nm ([Design §4](#4-measured-on-2wcd)). This is why G3's ±1 % floor cannot be reached by construction |
| D8 | Isolevel sensitivity (G2) | Stage 4 re-run on the cached reduced map at isolevels {0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50}, each compared per D3. A level whose stage-4 gate refuses is recorded with its refusal and not raised. The isolevel at which ε_G crosses zero is recorded as a diagnostic. **Asserted on 2WCD:** ε_G is strictly increasing across the passing levels | The case default stays 0.25 (phase plan, *Nothing is tuned to the target*). The union density's superlevel sets are nested, so the raw lumen cannot narrow as the level rises. The measured steps, 2.0–5.3 pp, dwarf the conditioning's 0.01 nm rms. So the assertion is a model property, and it catches a sign or ordering error. 2WCD crosses zero near 0.41 |
| D9 | Frozen-case conductance | Uncharged `pnp`, flow off, every correction `none`, 1 M NaCl, +50 mV, ground *cis*, stabilisation `none`. It is solved on the generated mesh and on the fixture's mesh through `inputs.profile`, at one `size_scale`: 2 at Tier 2 and 1 at Tier 3. `G_gen/G_ref − 1` is recorded beside ε_G. Not gated | Phase plan: recorded. Uncharged at 1 M, so G is geometric and ε_G's proxy can be checked against a solve. Access resistance dilutes it, and the difference is the evidence. The same `size_scale` makes the two meshes like for like. WP21 put the fixture's generic mesh within 0.1 % of `ReferenceGeometry`'s |
| D10 | Mesh against the reference figures | Recorded from the stage-6 summary at the default sizes: triangles, minimum SICN and gamma, and the mean. Set beside 120,917 triangles, 0.6378 and 0.9765, with the note that the reference's quality measure is not stated (`.knowledge/09`) | §5.2.2; phase plan *End-of-phase report* |
| D11 | FR-06 variance | Recorded from the stage-3 summary on both legs: the largest Cₙ and non-Cₙ variance and their (r, z) | Phase plan: recorded along z. RSK-07 is a documented criterion, not a threshold |
| D12 | Tier-3 store | The ensemble store becomes a session-scoped fixture in `tests/tier3/conftest.py`, shared by `test_density_ensemble.py` and `test_val05_ensemble.py`. Stages 1–3 are deposited once per nightly session | The 50-frame deposition costs about 16 min (WP20 Design §6). `loadfile` does not apply at Tier 3, which runs serially |
| D13 | Where results go | `ProfileComparison` is logged at INFO as YAML by each test. The numbers are transcribed into this plan's Outcomes and `.knowledge/04` §1.4 | §7.1: Tier 3 is recorded, and this is how WP19–WP21 recorded theirs. A report schema is the end-of-phase report's business |

### Work items

1. **`validation/geometry.py`** (D1–D3, D6, D7). Read Design §1 and §3 first. `ProfileComparison`
   carries names with units (`rms_nm`, `constriction_ours_nm`, `conductance_deviation`). Each
   tolerance failure raises naming the leg, the quantity, the value, the threshold and the located
   z (QR-12). NumPy is deferred, per `CLAUDE.md`.
2. **Tier 2, `tests/tier2/test_val05_2wcd.py`** (D5, D6, D8–D11), on its own module store (the
   `loadfile` rule of `test_contour_2wcd.py`). `test_pipeline_2wcd.py`'s `registered` switches to
   `register_by_centroid` (D6). Its docstring and WP21's registration note are updated.
3. **Tier 3, `tests/tier3/test_val05_ensemble.py`** (D4, D6–D12). DCD frames 48–97 are asserted, as
   `test_density_ensemble.py` does. `Z_MD` is pinned. The ensemble store moves to the tier's
   conftest (D12).
4. **Specification and knowledge.** Appendix A: the FR-07, FR-09 and FR-10 rows name the VAL-05
   test files, and FR-06 gains VAL-05 (recorded). `.knowledge/04` §1.4 takes the measurements
   again from the implementation. The docs page that lists the validation tiers names VAL-05. Write
   CHANGELOG `v0.9.0-alpha.6`.

### Verification

| Test file | Tier | Identifiers | Assertion / oracle | Tolerance source |
|---|---|---|---|---|
| `tests/tier1/test_val05_geometry.py` | 1 | VAL-05 (the harness) | A polygon compared with itself gives zeros. A lumen scaled by `(1 + s)` gives `ε_G = 2s` to first order, and the exact ratio to `(1 + s)²` for a uniform scale. `Δr_c` locates the minimum of each polygon separately. A missing plane outside the tip band fails, naming z, and inside it is admitted. Each tolerance fires on a constructed profile, naming leg, quantity, value, threshold and z. `pqr2grid_radius(1.65, 15, 0.05) = 1.5744` and `(5.66) = 5.4615`. `register_by_centroid` on a translated synthetic C12 returns the translation. Importing the module imports no NumPy | Closed forms; `.knowledge/04` §1.2's check values to 1e-4 nm |
| `tests/tier2/test_val05_2wcd.py` | 2 | VAL-05 (2WCD leg), FR-06, FR-07, FR-09, FR-10 | The prepared 2WCD through stages 1–5, registered per D6. The D5 tolerances pass, and every plane outside the tip band is crossed. The D8 sweep is strictly increasing in ε_G. Recorded: D7, D9 (at `size_scale` 2), D10 (default sizes), D11 and the fitted offset | D5 (author ruling). Prediction: Design §4 |
| `tests/tier3/test_val05_ensemble.py` | 3 | VAL-05 (ensemble leg, the phase gate), FR-06 | DCD frames 48–97 through stages 1–5 at `centre_z_nm = 0`. The D4 tolerances pass. `Z_MD` lies within 0.01 nm of 5.63. Recorded: D7, D8, D9 (at `size_scale` 1), D10 and D11. Skips naming the variable without the archive | D4 (author ruling). Prediction: WP20 Design §7 |

```bash
uv run pytest tests/tier1/test_val05_geometry.py
uv run pytest tests/tier2/test_val05_2wcd.py tests/tier2/test_pipeline_2wcd.py --log-cli-level=INFO
uv run pytest -m tier3 tests/tier3/test_val05_ensemble.py --log-cli-level=INFO   # needs the archive
```

Runtime: the 2WCD file costs stages 1–4 (about 42 s, measured), seven stage-4 re-runs (about 1 s
each), one default-size mesh (7 s) and two `size_scale` 2 solves. If it exceeds three minutes, D9
moves to `slow` and is logged there.

### Outcomes

> **Outcome — every work item is delivered; the ensemble leg's verdict awaits a run on the
> archive.** `nanopnp.validation.geometry` holds D1–D8, and three test files discharge VAL-05:
> 24 tests in `tests/tier1/test_val05_geometry.py`, 4 in `tests/tier2/test_val05_2wcd.py` and 3 in
> `tests/tier3/test_val05_ensemble.py`. This session had no `$NANOPNP_REFERENCE_DATA`, so the
> Tier-3 leg skips here, naming the variable. Its code was exercised end to end against a stand-in
> archive: the prepared 2WCD, shifted to put its C-alpha centroid at 5.63 nm and written as 98
> jittered frames. That run checks the code paths and says nothing about the ensemble's numbers.
> Its 22.5-minute session deposited the density once for both files (D12), and every record ran,
> including the frozen case at `size_scale` 1: 45,449 triangles, with the fixture at WP21's 44,316.
> Both gated tests refused as designed, each naming its quantity. The stand-in's hand-placed
> centroid missed `Z_MD` by 0.0145 nm, and its 2WCD polygon's `|ε_G|` of 8.23 % exceeded the
> ensemble's 5 %.
> The phase gate's verdict, `Z_MD` and the D7–D11 records go here when the nightly runner or the
> author runs `uv run pytest -m tier3 tests/tier3/test_val05_ensemble.py --log-cli-level=INFO`.

> **Outcome — the 2WCD leg passes D5, as predicted to the last digit.** ε_G = −8.08 % (exact
> series −8.19 %), Δr_c = −0.0205 nm (1.6295 nm at z = −1.475 against 1.650 at −1.225), rms
> 0.158 nm. 281 of 282 planes are crossed. The one missed, z = −1.825, is in the tip band. D7:
> binned through the erratum, ε_G = −16.01 % and the lumen mean Δ is −0.242 nm, so the hand edit
> widened the lumen by 0.24 nm and moved the outer surface out by 0.19 nm. Conditioning moved the
> lumen by at most 0.039 nm, rms 0.010. Registration: centroid 10.2027 nm, `centre_z_nm`
> 4.5727 nm. The full record is [`.knowledge/04`](../../.knowledge/04-clya-geometry-and-charge.md)
> §1.4.

> **Outcome — D8's sweep compares a level on the planes both polygons cross, not under D2's rule.**
> The body shortens at both tips as the level rises. At 0.50 it spans z = −1.684 to 11.907 nm and
> misses ten planes, six of them outside the tip band, so D2's strict rule refused a level that
> stage 4 passes, and the sweep lost its zero crossing. D2 binds the gated comparison.
> `compare_profiles(..., strict=False)` serves the recorded sweep, which logs each level's uncrossed
> planes. The §7.4 NOTE says so. The sweep then reproduces Design §4's table: −13.23, −10.08,
> −8.08, −5.81, −3.26, −0.40 and +4.87 %, strictly increasing, crossing zero at 0.408. Stage 4
> passed at every level.

> **Outcome — D6's rms-optimal offset is 4.5827 nm, not 4.580.** It is scanned on a 0.005 nm grid
> about the centroid's 4.5727 nm. The prototype's grid ran from 4.2 nm, so the minimum lies between
> the two, 0.007–0.010 nm from the centroid's. It is recorded and never used.

> **Outcome — D9 and D10 on 2WCD, recorded.** The frozen case at `size_scale` 2 gives
> `G_gen/G_ref − 1` = −6.57 % against ε_G's −8.08 %: 1.3786e-8 S on 14,162 triangles, against
> 1.4756e-8 S on the fixture's 14,511. Access resistance takes about a fifth of the first-order
> figure. At the default sizes the mesh has 44,998 triangles, minimum SICN 0.6267, mean 0.9867,
> minimum gamma 0.5222 and mean 0.9848, beside the reference's 120,917, 0.6378 and 0.9765. D11:
> the largest Cₙ variance is 0.204 at (5.40, 12.95) nm and the largest non-Cₙ variance 0.0095 at
> (1.65, 3.10) nm, both in the stage-1 frame. At one thread the file runs in about two minutes,
> within the three-minute budget, so D9 stays in Tier 2.

> **Outcome — the registration in `test_pipeline_2wcd.py` is D6's.** Its default-size mesh becomes
> the 44,998 triangles above, and its walk's currents become 4.15e-11 A (Na⁺) and 6.15e-11 A
> (Cl⁻). WP21's registration note carries the change.

> **Outcome — the default-size count, re-measured by WP23 (29 September 2026).** At `2bb1a34`, after
> `32fecf1` changed how the C-alpha centroid is computed, the 2WCD mesh at the default sizes has
> 44,762 triangles, means 0.9862 and 0.9843, with unchanged minima. `.knowledge/04` §1.4 carries the
> figure, and WP23's Outcomes the Gmsh mesh beside it.

### Out of scope

- **The charged frozen case** on a generated mesh: Phase 3 (FR-12 to FR-15). D9 is uncharged.
- **Gmsh-meshed figures** for D10: WP23 re-runs D10 on its backend for the end-of-phase report.
- **The GUI's comparison view and hand edit** (WP24). **Example 06 and the guide** (WP25).
- **The end-of-phase report** itself, written after WP25 from D13's records.
- **Changing the isolevel default, or fitting anything to the polygon.** D8 records and never
  selects.
- **HOLE through `mdahole2`**: optional (B5), not built.
- **Reconstructing the author's pre-edit polygon.** D7 attributes, and does not rebuild.

### Open questions

None blocks implementation. The author answered three on 28 September 2026: the tolerances (D4,
D5), the polygon's provenance (`pqr2grid` binning, and a hand edit that moved vertices) and L =
15 nm (D7). One number is pinned, not asked. `Z_MD` is 5.63 nm from `.knowledge/04` §1.1, to
0.005 nm. The first Tier-3 run measures it. If it differs by more than 0.01 nm, the constant and
the 2WCD figures are corrected in the Outcomes.

## Design

### 1. The metric

A pore of lumen radius `r(z)` filled with electrolyte of conductivity σ has the series resistance
`R = ∫ dz / (σ π r²)` [verified]. Perturbing `r → r + Δ`:

```
δR/R = −2 ∫ (Δ/r³) dz / ∫ r⁻² dz          (first order)
δG/G = −δR/R = 2 ∫ (Δ/r) · r⁻² dz / ∫ r⁻² dz
```

On uniform planes the integrals are sums, which gives D3's `ε_G`. The weight `r⁻²` is why the
constriction counts: on the reference, `Σ r⁻²` splits almost equally between the 3.45 nm of the
*trans* constriction (r ≈ 1.65–2 nm) and the 10.65 nm of the *cis* lumen (r ≈ 3 nm). A uniform
relative error s gives `ε_G = 2s`, which is the `G ∝ r²` of the phase plan.

Three approximations are named, and each makes `ε_G` an upper bound on the conductance effect.
Access resistance in series dilutes it. Surface conduction, which dominates at low salt, scales
with r rather than r² and halves it. Electrolyte past the pore ends is ignored. D9 measures the
dilution on a solve. On 2WCD the first-order and exact series values differ by 0.11 pp (−8.08 %
against −8.19 %), so first order suffices at these sizes.

### 2. The tolerances

G3 put the floor at ±1 % on G because the vertex list was then unavailable. The list has since
been delivered, and its construction is now known (D7). It passed through a binning erratum worth
about −8 pp of ε_G on 2WCD, and then through a hand edit worth about +8 pp. Neither step is part
of the method the pipeline implements, so no honest reproduction reaches ±1 %.

The ruling ties the ensemble tolerance to the method's own definitional uncertainty instead. The
25 % isolevel is unjustified in the source (G2). Measured on 2WCD (Design §4), ε_G moves by 4.3 pp
from 0.20 to 0.30 and by 5.4 pp from 0.30 to 0.40. So ±0.1 of isolevel is about ±5 %, and a
pipeline cannot be held tighter than the definition of the wall it extracts. The rms and
constriction bounds are 2h. Stage 4's closing and opening erase features below 2h by design
(§5.2.1 NOTE on the contour's size target), so a radius difference within 2h is inside the
pipeline's stated resolution.

The ensemble prediction is from WP20 Design §7: lumen mean Δ −0.075 nm, rms 0.089, constriction
1.610 against 1.650. Scaled by the 2WCD ratio of ε_G to the mean Δ, that gives ε_G ≈ −4.5 %. It
passes, with margin on the rms and Δr_c, and narrowly on ε_G. A miss is a finding recorded against
the phase gate, not a reason to move the tolerance.

### 3. The axial registration

The model frame puts z = 0 at the membrane centre. The MD frame already has that (G9), and stage 1
keeps a file's axial coordinate, so the ensemble needs no shift. The vendored 2WCD sits wherever
its test-time preparation put it (`tests/conftest.py`: tilted 4°, shifted 1.2 nm along z). It
must be placed in the MD frame, which needs one number the MD structure fixes.

The Cα centroid is that number. It is an average over 3,420 atoms (12 chains × 285 residues). It
is insensitive to side-chain placement and to the termini, and it is measured on the aligned
structure in the frame stage 5 shifts. Residues 8–292 are common to both structures. The MD's
residue 7 would pull its centroid about 0.025 nm towards *trans* (12 atoms about 7 nm below the
centroid, over 3,432).

Measured on the prepared 2WCD: z̄_Cα = 10.2027 nm, so `centre_z_nm = 4.5727` nm. The
rms-optimal offset over 4.2–5.0 nm at 0.005 nm steps is 4.580 nm, only 0.007 nm away, which is
independent support for the centroid choice. It also implies `Z_MD ≈ 5.623` nm, consistent with
§1.1's 5.63. WP21's *trans* tip + 1.85 nm gives 4.6289: 0.056 nm off, and it moves ε_G by 0.7 pp.

### 4. Measured on 2WCD

A scratch prototype, run on 28 September 2026, and not the implementation. It used stages 1–4 at
the defaults on the prepared 2WCD (161 vertices, stage-1 frame z extent 2.779–16.910 nm) and D6's
registration. The polygon comparison ran on the 282 D2 planes, 281 of them crossed. The missing
one is at −1.825, inside the tip band.

| Isolevel | ε_G | Exact series | Mean Δ (nm) | rms Δ (nm) | r_c ours (nm), at z |
|---|---|---|---|---|---|
| 0.15 | −13.24 % | −13.06 % | −0.201 | 0.222 | 1.581 at −1.475 |
| 0.20 | −10.08 % | −10.31 % | −0.164 | 0.193 | 1.607 at −1.175 |
| **0.25** | **−8.08 %** | −8.19 % | −0.132 | **0.158** | **1.6295** at −1.475 |
| 0.30 | −5.81 % | −5.98 % | −0.100 | 0.128 | 1.642 at −1.425 |
| 0.35 | −3.26 % | −3.49 % | −0.064 | 0.100 | 1.670 at −1.475 |
| 0.40 | −0.40 % | −0.67 % | −0.022 | 0.078 | 1.678 at −1.425 |
| 0.50 | +4.87 % | +4.55 % | +0.054 | 0.106 | 1.708 at −1.375 |

The reference's constriction is 1.650 nm at z = −1.225. At 0.25 the constriction segment's mean Δ
is −0.051 nm and the *cis* lumen's is −0.158 nm. The located max \|Δ\| is 0.333 nm at z = 3.375.
The outer surface's mean Δ is −0.023 nm, rms 0.154. Under WP21's registration the same contour
gives −7.38 %, rms 0.159 and max 0.360 nm at z = 1.775.

**With the L = 15 nm erratum applied** (D7): ε_G = −16.01 %, lumen mean Δ −0.242 nm (constriction
−0.139, *cis* lumen −0.275), and outer surface −0.191 nm. So the pre-edit polygon, if 2WCD stood in
for the ensemble, would have been 16 % less conductive than the delivered one. The hand edit
widened the lumen by about a quarter of a nanometre and moved the outer surface out by about
0.19 nm. The ensemble's version of this number is the Tier-3 leg's to record.

Stage times: structure 0.6 s, density 24.9 s, symmetry 16.2 s, contour 0.5 s. Each re-run of
stage 4 on the cached map took 0.9–1.6 s, probe included.
