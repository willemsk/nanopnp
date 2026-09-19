# WP13 — Tier 3 harness and the COMSOL comparison

**Status: delivered, 18 September 2026.** Written 18 September 2026, after WP7–WP12 delivered the case
schema and artefact chain (WP7), mesh ingestion and the reference geometry (WP8), external charge
and dielectric fields (WP9), CLI runs and field output (WP10), the sweep runner (WP11) and the
`reference` stabilisation mode (WP12).

It inherits, and depends on, four things. The **reference geometry and its 44,316-element mesh**
(WP8) — the comparison is meaningless on any other geometry. The **case document and its content
hash** (WP7) — a golden that does not name the case it answers is not evidence. The **sweep
planner's dotted-path substitution and warm-start forest** (WP11) — the attribution ladder is a
sweep, not a second dispatch path. And the **`supg` and `reference` stabilisation modes with the
element pair configurable per field** (WP12, `numerics.elements`) — without those the ladder has
only one rung.

This package belongs to [the Phase 1 delivery plan](phase-1-solver-core.md) and implements its
[WP13 section](phase-1-solver-core.md#wp13--tier-3-harness-and-the-comsol-comparison).
`SPECIFICATION.md` governs: where this plan and the specification disagree, this plan is the thing
that is wrong. Every `VAL-`, `NUM-`, `QR-`, `RSK-` and `IF-` identifier below is a pointer into it,
never a restatement of it. Two amendments are made in the same commit as this plan and are named in
**Spec and plan amendments** below.

## Execution brief

### Scope

Build the machinery by which a COMSOL reference solution becomes evidence: the **export contract**
the author fills, the **probe grid** we specify, the **golden archive format**, the **comparison**
and its norms, and the **attribution ladder** that decomposes a discrepancy into the parts we chose
and the part that could be a defect. Enable the nightly Tier-3 job.

Discharges **VAL-01, VAL-02, VAL-03, VAL-04**; retires **RSK-14**; bounds **RSK-09**. Touches
**QR-02** (through VAL-01/VAL-02), **QR-12** (every gate below aborts naming the quantity and its
location), **IF-07** and **NUM-23…NUM-27** (the QoIs compared are the ones §6.7 already extracts).

**WP13 does not make VAL-01 or VAL-02 a gate.** §7.4 makes the 1 % and 0.5 % targets conditional on
the stabilised mode existing *and* the meshes being convergence-matched. WP12 delivered the first;
the second is not this package's to achieve. Tier 3 stays recorded, not gated (§7.1, §7.6).

### Requirement and section pointers

| Need | Read |
|---|---|
| What Tier 3 is and what it accepts | `SPECIFICATION.md` §7.4, and the §7.1 NOTE on `$NANOPNP_REFERENCE_DATA` |
| What must be matched for like-for-like | `.knowledge/09-comsol-reference-settings.md` §C.2, §C.10, §E, §F |
| The QoIs and their signs | `SPECIFICATION.md` §6.7 (NUM-23…NUM-27), in particular the NOTE on sign |
| What the stabilised mode costs the current | `wp12-reference-stabilised-mode.md`, Outcomes in Design §3 and §4; the phase plan's "Inherited by WP13" paragraphs |
| The reference geometry and its mesh | `wp8-mesh-ingestion-quality-reference.md`; `data/geometry/clya_reference_profile.yaml` |
| Sweep documents and the warm-start forest | `wp11-sweep-runner.md`; `docs/sweeps/README.md` |

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| Frozen case set (VAL-03) | **Five cases**: 0.05 M and 3 M × ±200 mV, plus 0.5 M / +50 mV. Validated ePNP-NS configuration throughout, on the WP8 reference mesh | Author ruling, 18 September 2026, closing the phase plan's open decision. The four corners span the experimental envelope and give VAL-02 a matched opposite-bias pair at each salt, so `RR` is comparable and not merely `I`; the centre point distinguishes a discrepancy linear in bias from one quadratic in it. The §7.5.1 analyte case is **excluded** — it brings VAL-11…VAL-14 machinery into Phase 1 for no gain to the phase gate |
| Transport format of the export | **COMSOL `%Grid`/`%Data` text tables**, one file per field per case, as the author already produces | Author ruling, 18 September 2026. `nanopnp.density.grid._read_comsol` already reads exactly this format, and VAL-15 verified it against the delivered 77 MB `prod5_clya_charge` table to 4.7 × 10⁻¹². Adopting a second reader would put an unverified parser between the reference and every number this phase reports |

| Archive format of the golden | **`.npz` plus a typed manifest**, produced from the text tables by `nanopnp validate ingest-golden`; the raw text and the `.mph` are archived beside it | §7.4 says "compressed arrays with the generating model archived alongside". `%Grid` is the transport format, `.npz` the archival one; the conversion is where the unit, sign and hash declarations are checked once rather than on every nightly run |
| Where goldens live | `$NANOPNP_REFERENCE_DATA`, **never vendored**; a Tier-3 test whose golden is absent **skips** | §7.1 NOTE, already implemented as `core.paths.reference_file`. Five cases × four fields × two refinements is not a repository file |
| Probe grid ownership | **Ours**, a `nanopnp/probe/v1` document of named tensor-product patches, checked in beside the frozen cases, content-hashed into every golden manifest | Phase plan decision "Tier-3 comparison surface". COMSOL interpolates onto our grid, so the comparison does not depend on COMSOL's mesh and a re-export cannot silently move the sample points |
| Transpose protection | **Every patch asserts `n_r ≠ n_z`** at construction, with the message naming the `%Data` row order | `%Data` rows are `[i_z, i_r]`. On a square patch a transposed read is silently plausible and wrong everywhere; a non-square patch turns it into a shape error. Cheapest gate in the package |
| Domain masking | Each field's probe set is the points inside its `definedon` materials **whose four `±margin_nm` neighbours are also inside** (default `margin_nm = 0.05`, the reference's own wall element size). The golden's NaN set must agree; disagreement **aborts**, naming the worst point and its distance | NGSolve returns **0**, silently, outside `definedon`; a `c_i` norm taken over the membrane is then dominated by fabricated zeros and reads as agreement. The margin keeps the mask off the boundary-resolution lottery, so a residual disagreement is a real geometry difference — the WP8 unmapped-group gate, one layer out |
| Units and sign contract | The manifest **must** declare, per field, the COMSOL expression and its unit, and for the current the **evaluation boundary** and which electrode it references. A golden missing any of them is **refused**, naming what is missing | `.knowledge/09` §F records that the evaluation boundary is NOT IN REPORT, so it can only come from the author. A `mol/L` export is a factor 1000 and would present as a physics failure; a `trans`-referenced current negates every conductance (§6.7 NOTE). The loader converts to the §6.7 convention and **records the flip in the report** |
| Field norms | Per field, three numbers: `rel_L2_r` (the *r*-weighted axisymmetric relative L², the VAL-01 quantity), `rel_l2` (unweighted, the axis diagnostic), and `max_abs_rel` **with its (r, z)** | The `r` weight vanishes on axis, which is exactly where the `1/r` forms and NUM-06 fail. Gating on `rel_L2_r` alone would hide the failure mode these forms are most prone to. The located maximum is QR-12's "naming the quantity and its location" |
| Pressure gauge | `p` is compared **gauge-free**: the *r*-weighted mean is removed from both fields and the norm is taken against `‖g − ⟨g⟩‖`; the removed constant is reported | COMSOL's pressure gauge is not ours and is not in the report. Comparing `p` raw makes a gauge offset read as a 100 % discrepancy, which looks like a flow defect and is not one |
| Attribution ladder | **Four rungs**, not three: `none`+P2/P1 → `supg`+P2/P1 → `reference`+P2/P1 → `reference`+P1/P1 | Amends the phase plan's three-rung decision, on WP12's inherited finding that `reference` on a Taylor–Hood pair converges at **0.98** where `supg` converges at **2.01**. Without the `supg` rung the middle delta conflates the transport stabilisation with a first-order flow operator and attributes nothing. `supg.permits_equal_order` is `False`, so that rung is P2/P1 by construction. Derivation: §Design 1 |
| What the ladder reports | `Δ_total = E₀`, `Δ_transport = E₁ − E₀`, `Δ_flow = E₂ − E₁`, `Δ_pair = E₃ − E₂`, `Δ_resid = E₃`, with the identity `Δ_total + Δ_transport + Δ_flow + Δ_pair = Δ_resid` **asserted to round-off** | The identity is free by construction and is the only thing that catches a rung run against a different golden or a stale probe grid. §Design 1 |
| `Δ_stab` against `stabilisation_currents_A` | The report carries **both**, labelled as different quantities | §6.7's `stabilisation_currents_A` is the stabilisation's contribution to the current from **one** run; `Δ_transport` is a difference of two runs' distances from a third object. WP12 measured the two agreeing to 1.55 × 10⁻³ of the current on its benchmark; they are not the same quantity and a report that conflated them would be quoting an agreement as a definition |
| How the ladder is dispatched | As a **checked-in sweep document**, `docs/validation/comsol-ladder.sweep.yaml`, axes `rung` (4) × `case` (5) | Reuses WP11's substitution, warm-start forest, job-array dispatch and collector. A second dispatch path for twenty solves is a second set of failure modes for no capability |
| Warm starts across rungs | **Forbidden**: the `rung` axis changes the element spaces and the assembled operator, so each rung is its own warm-start component and climbs the ladder cold. Verified by a Tier-1 test that a warm start across an element-space change is **refused**, not silently accepted | §5.3.2's partition, and WP12's finding that `reference` at two `C_cw` values are different operators. Reading a converged vector onto a different space is the one warm-start error that produces a plausible wrong number rather than a failure |
| VAL-04 | The **published mesh and one uniform refinement**, on the centre case only. The harness reports `Δ_ref = ‖g_fine − g_coarse‖/‖g_fine‖` per field and per QoI, and marks a comparison **reference-limited** when `Δ_resid < Δ_ref` | Author ruling, 18 September 2026. RSK-09 needs a bound, not a field. "Reference-limited" is the honest verdict when our residual is below the reference's own discretisation error, and it is the number the end-of-phase report owes |
| Self-golden path | `nanopnp validate export-golden` writes a golden from **our own** run in the archive format. Tier 2 round-trips one solution through it (Δ must vanish to 10⁻¹⁴); Tier 3 runs the **full four-rung ladder** against a self-golden on the cheap VER-11 benchmark pore | The phase plan requires the harness be exercisable before the exports land, "which tests the machinery and nothing else, and the report says so". The report carries `golden_source: self` and every consumer of it must print that |
| Nightly CI | Enable the stubbed `tier3` job on `schedule` + `workflow_dispatch`, `continue-on-error: true`, uploading the report as an artefact. It **skips**, visibly, without the archive | §7.6, §7.1. Tier 3 is recorded, not gated; a job that failed on an absent archive would make the tier unrunnable off the machine that holds it |

> **Outcomes against this table.**
>
> *Transport format* — one table per field **per patch**, not per field. A COMSOL Grid
> evaluation takes one tensor-product grid and the probe grid is a union of five patches, so
> the contract is `<field>__<patch>.txt`; `read_grid` reads exactly one table per file, which
> is what keeps the VAL-15-verified reader in place rather than teaching it a multi-block
> dialect. The naming is mechanical (`nanopnp.validation.comsol.table_name`), so neither the
> author nor the ingest keeps a list. `docs/validation/comsol-export-contract.md` section 2 is
> the contract.
>
> *What the ladder reports* — the second half of that row's rationale is **wrong**, and the
> gate it asked for was built separately. `E₀ + (E₁ − E₀) + (E₂ − E₁) + (E₃ − E₂) = E₃`
> telescopes for *any* four numbers, so a rung compared against a re-exported golden satisfies
> it exactly as cleanly as one compared against the right golden: the identity cannot catch
> what the row claims it catches. It is asserted anyway — it fails on a slip in forming or
> assigning the deltas, which is worth having — and `attribute()` compares the golden, probe
> and case hashes across the four rungs and the retained point count per field, which is what
> actually does the job. The algebra is pinned by
> `tests/tier1/test_attribution.py::test_val01_the_identity_cannot_see_a_stale_golden`, so the
> claim is not reintroduced; the reasoning is in `.knowledge/08-validation-benchmarks.md`,
> "The telescoping identity catches a slip, not a stale golden".

### Work items

In dependency order. Read §Design 1 before the ladder, §Design 2 before the norms, §Design 3 before
the loader.

| # | Files | Deliverable | Identifiers |
|---|---|---|---|
| 1 | `src/nanopnp/validation/probe.py` | `ProbeDocument` (`nanopnp/probe/v1`), `ProbePatch` with the `n_r ≠ n_z` assertion, `ProbeGrid` with per-field masks and the margin rule, content hash, and `write_comsol_axes()` emitting the `%Grid` axis lines the author pastes into COMSOL | QR-12 |
| 2 | `docs/validation/probes/clya-reference.probe.yaml` | The probe grid for the reference geometry: patches `pore`, `mouth_cis`, `mouth_trans`, `reservoir`, plus the near-axis line. Extents and spacings fixed here, hashed, never regenerated | VAL-01 |
| 3 | `docs/validation/cases/*.case.yaml` (5) | The frozen cases, derived from `docs/sweeps/phase1-reference.case.yaml` with the validated ePNP-NS corrections on, at the five operating points | VAL-03 |
| 4 | `docs/validation/comsol-export-contract.md` | The contract the author fills: file naming, one `%Grid` table per field, the expression and unit for each, the evaluation boundary and sign declaration, the refinement label, and what is archived beside them | VAL-03, RSK-14 |
| 5 | `src/nanopnp/validation/comsol.py` | `GoldenManifest` and `Golden` (pydantic, `extra="forbid"`), `ingest_golden()` reading the `%Grid` tables via `density.grid.read_grid` and writing the `.npz`, `load_golden()` with the unit/sign/hash refusals of §Design 3 | VAL-03, IF-07 |
| 6 | `src/nanopnp/validation/compare.py` | `sample_on_probe(solution, grid)`, `FieldComparison`, `QoIComparison`, the three norms, the gauge-free pressure path, the mask-agreement gate | VAL-01, VAL-02, QR-02, QR-12 |
| 7 | `src/nanopnp/validation/attribution.py` | `Rung`, `LADDER` (the four rungs as dotted-path assignments), `AttributionReport` with the five deltas and the asserted identity, `Δ_ref` and the `reference-limited` verdict, JSON and markdown writers | VAL-01, VAL-02, VAL-04, RSK-09 |
| 8 | `docs/validation/comsol-ladder.sweep.yaml` | The ladder as a sweep: `rung` × `case`, rooted at the easy corner | FR-24 (reuse) |
| 9 | `src/nanopnp/cli/__init__.py` | `nanopnp validate` with `export-grid`, `ingest-golden`, `export-golden`, `compare`, `report` | IF-02, FR-27 |
| 10 | `.github/workflows/ci.yml` | The nightly Tier-3 job, un-stubbed | §7.6 |
| 11 | `SPECIFICATION.md`, `docs/plans/phase-1-solver-core.md`, `docs/plans/current.md` | The two amendments below; the phase plan's VAL-03 open-decision row closed; `current.md` repointed at WP13 | — |

### Verification

Every test names the requirement it discharges. Command for the gate:
`uv run ruff check . && uv run ruff format --check . && uv run mypy src/ && uv run pytest`.

| Test file | Tier | Identifiers | Assertion and oracle | Tolerance source |
|---|---|---|---|---|
| `tests/tier1/test_probe_grid.py::test_val01_probe_patch_refuses_square_grid` | 1 | VAL-01, QR-12 | A patch with `n_r == n_z` aborts, naming the `%Data` row order | Exact (structural) |
| `tests/tier1/test_probe_grid.py::test_val01_probe_mask_excludes_points_within_margin` | 1 | VAL-01 | On the WP8 reference mesh, no retained `c_i` probe point lies within `margin_nm` of a non-electrolyte material; the dropped count is recorded in the document | `margin_nm = 0.05`, the reference's wall element size (`.knowledge/09` §A.2) |
| `tests/tier1/test_comsol_golden.py::test_val03_golden_refuses_undeclared_units_and_sign` | 1 | VAL-03, QR-12 | A manifest missing the unit, the evaluation boundary or the sign reference is refused, naming what is missing; a `mol/L` declaration is refused rather than silently scaled | Exact (structural) |
| `tests/tier1/test_comsol_golden.py::test_val03_grid_table_round_trips_through_npz` | 1 | VAL-03 | A `%Grid` table written and re-ingested reproduces its array bit-for-bit and its hashes | `0` (bitwise) |
| `tests/tier1/test_comsol_golden.py::test_val03_trans_referenced_current_is_flipped_and_recorded` | 1 | VAL-03, NUM-24 | A golden declaring `trans` comes back with the §6.7 sign and the report says the flip happened | Exact |
| `tests/tier1/test_comparison_norms.py::test_val01_relative_l2_on_a_known_field` | 1 | VAL-01 | On an analytic pair whose *r*-weighted and unweighted relative L² are integrable in closed form, both norms match the closed form | 10⁻¹² relative, quadrature-limited |
| `tests/tier1/test_comparison_norms.py::test_val01_axis_defect_is_invisible_to_the_weighted_norm` | 1 | VAL-01, NUM-06 | A field perturbed only near `r = 0` leaves `rel_L2_r` below 10⁻³ while `rel_l2` exceeds 10⁻¹ — the reason both are reported | Constructed; §Design 2 |
| `tests/tier1/test_comparison_norms.py::test_val01_pressure_gauge_offset_does_not_register` | 1 | VAL-01 | Adding a constant to `p` leaves the reported discrepancy unchanged, and the removed constant is reported | 10⁻¹⁴ relative |
| `tests/tier1/test_comparison_norms.py::test_val01_mask_disagreement_aborts_with_location` | 1 | VAL-01, QR-12 | A golden whose NaN set disagrees aborts, naming the worst point's `(r, z)` and its distance | Exact (structural) |
| `tests/tier1/test_attribution.py::test_val01_ladder_identity_holds_on_synthetic_errors` | 1 | VAL-01, VAL-02 | On four synthetic rung errors the five deltas satisfy `Δ_total + Δ_transport + Δ_flow + Δ_pair = Δ_resid` | 10⁻¹⁴ absolute |
| `tests/tier1/test_attribution.py::test_val04_reference_limited_verdict` | 1 | VAL-04, RSK-09 | `Δ_resid < Δ_ref` yields `reference-limited`; `Δ_resid > Δ_ref` does not | Exact (structural) |
| `tests/tier1/test_attribution.py::test_val01_ladder_rungs_are_separate_warm_start_components` | 1 | VAL-01, §5.3.2 | Planning the ladder sweep places each rung in its own component; a warm start across an element-space change is refused, naming the spaces | Exact (structural) |
| `tests/tier2/test_self_golden_round_trip.py::test_val01_self_golden_reproduces_its_own_solution` | 2 | VAL-01, VAL-02 | One converged VER-11 benchmark solve exported as a golden and compared against itself: every field norm and every QoI error vanishes | 10⁻¹⁴ relative (`%.17g` round-trips float64 exactly) |
| `tests/tier3/test_comsol_comparison.py::test_val01_val02_val04_attribution_against_the_archive` | 3 | VAL-01, VAL-02, VAL-04 | The four-rung ladder on the five frozen cases against the archived goldens; the five deltas, `Δ_ref` and the verdict are **recorded**, not gated. **Skips** when `$NANOPNP_REFERENCE_DATA` is unset or lacks the golden | §7.4 targets recorded; §7.1 skip rule |
| `tests/tier3/test_comsol_comparison.py::test_val01_full_ladder_against_a_self_golden` | 3 | VAL-01 | The full four-rung ladder on the benchmark pore against a self-golden: the identity holds, `Δ_resid` is the rung that generated it and vanishes, and the report carries `golden_source: self` | 10⁻¹⁴ on the generating rung; identity to 10⁻¹⁴ |

Tier 3 is run by `uv run pytest -m tier3 -v`, nightly and on demand, never on the push gate. Tiers 1
and 2 read no archived file (§7.1).

> **Outcome — delivered, with three departures from the table above, each for a reason.**
>
> `test_val01_probe_mask_excludes_points_within_margin` is in `tests/tier1/test_probe_grid.py` as
> written and runs against the real WP8 reference mesh (about 7 s, module-scoped). Its third
> assertion is not the margin rule restated: every retained point is probed at four **diagonal**
> offsets of `margin/2`, whose normal component against any boundary is at most `margin/2` and is
> therefore implied by the axis-aligned test the mask actually applies. Two points with unambiguous
> answers — `(4.05, 6.0)` nm inside the pore protein, `(0.05, 30.0)` nm in open reservoir — pin the
> sign of the whole mask.
>
> `test_val01_ladder_rungs_are_separate_warm_start_components` covers the **plan-time** half:
> planning the checked-in ladder gives four roots, one per rung, with no forest edge crossing the
> rung axis, and every path `LADDER` writes is a `WARM_START_BARRIERS` entry. The **run-time** half
> is `tests/tier1/test_warm_start_descriptor.py::test_val01_a_warm_start_across_an_element_order_is_refused`,
> which lives there because that is where the converged-neighbour fixture already is; splitting it
> saved a second solve and put the assertion beside the gate it is about. Note what that test
> found: the key that fires is `fields`, not `model.elements`, because an element order cannot move
> without moving the per-field discretisation record and `ndof` with it, and `fields` comes first in
> `SPACE_KEYS`. `model.elements` is the same fact gated on the same side, and is the belt to
> `fields`'s braces.
>
> `test_val03_grid_table_round_trips_through_npz` and the Tier-2 self-golden round trip assert
> **exactly `0`**, not `10⁻¹⁴`: `%.17g` round-trips `float64` by definition, `NaN` included, so any
> difference at all is a defect in the transport format rather than a rounding budget being spent.
>
> Three tests were added beyond the table, each for a failure its set would not have seen.
> `test_val01_the_same_defect_at_the_wall_is_visible_to_both`: without it the axis test is
> consistent with `rel_L2_r` merely being small whenever few points move.
> `test_val01_mask_disagreement_names_the_furthest_point_not_the_first`: a one-element fringe and a
> block three spacings deep are different diagnoses, and the reported distance is what separates
> them. `test_val03_the_ladder_members_answer_the_five_frozen_cases`: the link that makes the
> golden's `case_hash` gate mean anything — every ladder member's identity is one of the five
> frozen cases', and all four rungs of each case share it.


### Out of scope

| Deferred | Owner |
|---|---|
| Producing the COMSOL exports themselves | The author, against the contract of work item 4 |
| Convergence-matching the meshes — §7.4's second precondition | Not scheduled. WP13 *measures* whether it holds; achieving it is a later decision informed by `Δ_ref` |
| Making VAL-01/VAL-02 a gate | Phase 4, and only once both §7.4 preconditions hold |
| The §7.5.1 analyte case in the reference set | Excluded by the author ruling; revisit with VAL-11…VAL-14 |
| VAL-05 (contour against the published polygon) and VAL-06 (APBS) | Phases 2 and 3 |
| VAL-15's producer-side fix — depositing the charge table onto the FE space | v0.9 stage 7, per `tests/tier3/test_reference_charge_map.py` |

### Open questions

None blocking. Three the author answers **at export time**, not before implementation — the loader
refuses a golden that leaves any of them unstated, which is the point:

1. **The evaluation boundary COMSOL used for `tds.ntflux_i`**, and which electrode the reported
   current references. NOT IN REPORT (`.knowledge/09` §F); only the author can supply it.
2. **Whether the model exports `p`**, and its gauge. If it does not, the pressure comparison is
   recorded as unavailable rather than skipped silently.
3. **Whether `$NANOPNP_REFERENCE_DATA` can be made available to the nightly runner.** If not, Tier 3
   is a local and on-demand tier and the CI job records a visible skip; nothing else changes.

## Delivered

**18 September 2026.** All eleven work items landed; nothing deferred.

`src/nanopnp/validation/` gains `probe.py` (the `nanopnp/probe/v1` document, the `n_r ≠ n_z`
refusal, the margined per-field masks with the axis **mirrored** rather than clipped, and
`write_comsol_axes`), `comsol.py` (`nanopnp/golden/v1`, the five refusals — `case_hash` and `probe_hash` asked at
ingest *and* at every comparison, the unit, the sign and the archive's own `golden_hash` — the
`%Grid` writer that is the format's only one, and `case_identity`, which drops the discretisation
entries of `model_options` and keeps its physics switches), `compare.py` (the three norms, the gauge-free
pressure path, the mask gate), `attribution.py` (the four rungs, five deltas, `Δ_ref`, the verdict
and both report writers) and `runs.py` (reopening a finished run without re-solving it).
`nanopnp validate` gains six actions, and the nightly Tier-3 job is enabled, `continue-on-error`,
uploading the report.

Two things outside the package changed. `sweep/plan.py` gained `WARM_START_BARRIERS`: an axis over a
path a warm start cannot cross now **severs** the forest at plan time, so each rung of the ladder is
its own component rooted cold rather than a chain the run would build and `load_initial` would
refuse member by member. And `io/fields.py`'s node sampler and scale lookup became public
(`sample_at`, `field_scale`), because the probe comparison samples the same fields at points of its
own and the carrier trick those functions implement is the whole reason a sample on an interface
node is right; a second implementation would be a second chance to get it wrong.

### Measurements

The probe grid: 6 205 points over five patches, hash
`0d347ffcb1eb782eb87a1802ef4521b304ee2b72cdb2e2ce400689a3cbf4a9d4`. On the WP8 reference mesh the
`potential` mask retains all 6 205 and the `c_i` mask 5 963, of which 29 are dropped by the margin
rule rather than by the bare point test — the number that says the margin is doing something.

The four-rung ladder against a self-golden on the VER-11 benchmark pore (708 elements, 0.5 M,
+50 mV, −0.05 C/m², validated ePNP-NS with the flow on, `Δ_resid = 0` by construction) runs in
**75 s** and is tabulated in `.knowledge/08-validation-benchmarks.md`, "Measured: the attribution
ladder on the VER-11 benchmark pore". The headline: `Δ_transport` carries 88 % of the potential's
distance and 0.3 % of `velocity_r`'s, while `Δ_flow` carries 90 % of `velocity_r`'s. A three-rung
ladder would have reported one number that is 88 % transport stabilisation for one field and 90 %
flow operator for another, and attributed neither — which is the decision to split at `supg`,
measured rather than argued.

Planning the checked-in ladder: 20 points, 3 waves, **4 roots**, one per rung, no edge crossing the
rung axis, and all 20 members resolving to exactly the five frozen case identities.

### Not this package's to do

The COMSOL exports themselves (the author, against `docs/validation/comsol-export-contract.md`) and
convergence-matching the meshes (§7.4's second precondition; WP13 *measures* whether it holds
through `Δ_ref`, and achieving it is a later decision). VAL-01 and VAL-02 remain **recorded, not
gated**, per §7.1 and §7.6.

---

## Spec and plan amendments

Both made in the commit that adds this plan.

1. **`SPECIFICATION.md` §7.4** gains a NOTE naming the five frozen cases of VAL-03 and VAL-04's
   refinement pair, closing the scope question §7.4 left open. The acceptance criteria are
   unchanged.

> **Outcome — two further §7.4 amendments landed with the implementation.** VAL-03's acceptance
> criterion now requires the archive to *declare*, per field, its source expression and unit, and
> for the current its evaluation boundary and which electrode it references, a golden leaving any
> of those unstated being refused rather than interpreted — the evaluation boundary is NOT IN
> REPORT (`.knowledge/09` §F), so it can only come from the author and a build that guessed would
> guess again on every nightly run. And a new NOTE fixes the comparison surface: the probe grid is
> ours and content-hashed into every golden, the mask carries the `±0.05 nm` margin and aborts on a
> residual disagreement rather than intersecting, **the VAL-01 quantity is the `r`-weighted
> relative L²** and the unweighted one and the located maximum are reported beside it, and the
> pressure is compared gauge-free. Without that NOTE, "< 1 % relative L² error per field" did not
> say which relative L².
2. **`docs/plans/phase-1-solver-core.md`** — the "Attribution, not agreement" decision row is
   amended from three rungs to four, citing WP12's measured 0.98 convergence rate for `reference`
   on a Taylor–Hood pair; the "VAL-03 export scope" open-decision row is closed with the author's
   ruling of 18 September 2026.

No scientific requirement changes. No weak form changes. No correction parameter changes.

---

## Design

The derivations this package leans on. Outside the execution brief's word budget.

### 1. The attribution ladder, and why three rungs do not attribute

Let `g` be a golden field on the probe grid `P`, and `s_k` our solution in configuration `k` sampled
on the same `P`. Define the discrepancy functional

```
E_k = ‖s_k − g‖ / ‖g‖
```

in the norm of §2 below. The four configurations, in the order a reader should read them:

| `k` | `numerics.stabilisation` | `numerics.elements.u` / `.p` | What it is |
|---|---|---|---|
| 0 | `none` | P2 / P1 | Our production default (NUM-11). Taylor–Hood, unstabilised |
| 1 | `supg` | P2 / P1 | Transport stabilisation only. `supg.permits_equal_order` is `False`, so this rung *cannot* be run at equal order |
| 2 | `reference` | P2 / P1 | Transport **and** flow GLS, on an inf-sup-stable pair |
| 3 | `reference` | P1 / P1 | The reference's own discretisation (`.knowledge/09` §C.2, §E rows 1, 2, 4) |

and the reported deltas

```
Δ_total     = E₀                  our production configuration's distance from the reference
Δ_transport = E₁ − E₀             the transport stabilisation, measured at second order
Δ_flow      = E₂ − E₁             the flow GLS term added on a Taylor-Hood pair
Δ_pair      = E₃ − E₂             the element pair, P2/P1 to P1/P1
Δ_resid     = E₃                  the like-for-like residual — the only part that can be a defect
```

The identity

```
Δ_total + Δ_transport + Δ_flow + Δ_pair = E₀ + (E₁ − E₀) + (E₂ − E₁) + (E₃ − E₂) = E₃ = Δ_resid
```

is free by construction. Assert to 10⁻¹⁴ absolute on the telescoped sum.

> **Outcome — the sentence that stood here was wrong**, in the same way the Decisions table's
> "What the ladder reports" row was: it claimed the identity "holds only if all four rungs were
> compared against the same golden on the same probe grid with the same masks", and that a rung
> run against a re-exported golden breaks it. It does not — the sum telescopes for *any* four
> numbers. The identity is asserted because it catches a slip in forming or assigning the deltas
> (and, since the review, a non-finite rung error); the stale-golden gate is `attribute()`
> comparing the golden, probe and case hashes across the four rungs and the retained point count
> per field. Pinned by
> `tests/tier1/test_attribution.py::test_val01_the_identity_cannot_see_a_stale_golden`.

**Why the phase plan's three rungs are not enough.** The phase plan specified
`none`+P2/P1 → `reference`+P2/P1 → `reference`+P1/P1, calling the first delta `Δ_stab`. WP12 then
measured, on the VER-11 benchmark pore, an MMS L² convergence rate of **0.984** for `reference` on a
Taylor–Hood pair against **2.012** for `supg` on the same meshes and the same manufactured solution.
That is a full order lost, and it is lost in the flow operator: the GLS term's pressure-test content
is what makes P1/P1 legal, and on a pair that is already inf-sup stable it is a first-order
perturbation of a second-order discretisation. So the phase plan's `Δ_stab` is a sum of two
different things — the transport stabilisation, which is what NUM-11 warns about and what §7.4 is
trying to attribute, and a first-order flow operator, which is an artefact of running `reference`
on a pair it was not designed for. Splitting the rung at `supg` separates them at a cost of one
solve per case, and `supg` is second-order on this pair by WP12's own measurement, so
`Δ_transport` is a clean number. Without the split, the middle delta attributes nothing, which is
the one thing the phase gate asks for.

**What each delta may and may not be called.** `Δ_resid` is the like-for-like number and the one
§7.4's targets apply to. `Δ_total` is what our shipped default does. `Δ_transport` is the transport
stabilisation's contribution *to the distance from the golden* — it is **not**
`stabilisation_currents_A`, which §6.7 extracts from a single run as the stabilisation form
evaluated against the indicator. WP12 measured those two agreeing to 1.55 × 10⁻³ of the current on
its benchmark (−8.14 % from one run against 7.38 % from a difference of two), which is evidence that
both are measuring the same physics, not licence to print one as the other. The report carries both
under distinct names.

**Cost.** Five cases × four rungs = twenty solves on the 44,316-element reference mesh, cold within
each rung (see below), warm-started across cases within a rung. The 3 M / ±200 mV corners are the
FR-17 envelope's hard ones and climb the full NUM-18 ladder. Hours, which is what §7.1 budgets Tier
3 for; the measured wall clock is a number the end-of-phase report owes.

**Why the rungs cannot warm-start into each other.** Rungs 0→1 and 2→3 change the assembled
operator; 2→3 also changes the velocity space from P2 to P1. §5.3.2's warm-start partition forbids
crossing either. Reading a converged coefficient vector onto a different space is not an error that
announces itself — it either raises on a length mismatch (harmless) or, where the spaces happen to
share a dimension, silently seeds Newton with a meaningless state that may still converge, to
something. The Tier-1 test asserts refusal rather than trusting the length check.

### 2. The norms, and why two of them

The probe grid is a union of tensor-product patches of uniform spacing, so the midpoint rule gives
each retained point `p` the weight `w_p = Δr Δz` of its patch. The axisymmetric L² norm on such a
grid is

```
‖v‖²_r = Σ_{p ∈ P_f}  w_p · r_p · v_p²
```

the `2π` cancelling in every ratio reported. `P_f` is field `f`'s retained probe set (§3 below).
This is the discretisation of `∫_Ω v² r dr dz`, the norm the axisymmetric weak forms of §6.2 are
posed in, and `rel_L2_r = ‖s − g‖_r / ‖g‖_r` is therefore the VAL-01 quantity.

It is also blind on the axis. The weight `r_p` is `0.005 nm` on the near-axis line and `3.5 nm` at
the pore wall, so a defect confined to the first column of probe points contributes of order
`10⁻³` of what the same defect contributes at the wall — and the axis is precisely where the
`1/r` forms of §6.2 and the NUM-06 natural condition are fragile, and where §7.1's own warning
about integration order lives. A comparison that reported only `rel_L2_r` would be least sensitive
exactly where this implementation is most likely to be wrong. So the unweighted

```
rel_l2 = ( Σ_{p ∈ P_f} (s_p − g_p)² / Σ_{p ∈ P_f} g_p² )^{1/2}
```

is reported beside it, weighting every probe point alike, and `max_abs_rel` with its `(r, z)` is
reported beside both so a reader has a location and not just a magnitude (QR-12). The Tier-1 test
`test_val01_axis_defect_is_invisible_to_the_weighted_norm` constructs the case that makes this
concrete: a perturbation supported within one patch spacing of the axis, sized so `rel_L2_r < 10⁻³`
while `rel_l2 > 10⁻¹`.

**Pressure.** `p` enters the momentum equation only through `∇p`, so any solution is a solution with
a constant added unless a Dirichlet condition pins it; COMSOL's pin is not ours and is not in the
model report. Comparing raw `p` would make a gauge offset `c` contribute `|c| · ‖1‖_r / ‖g‖_r`,
which for a reservoir-scale grid and a small physical pressure is of order 1 — a 100 % discrepancy
that is not a discrepancy at all. So for `p` alone both fields have their *r*-weighted mean removed
first,

```
ĝ = g − ⟨g⟩_r ,   ŝ = s − ⟨s⟩_r ,   ⟨v⟩_r = Σ w_p r_p v_p / Σ w_p r_p
```

and `rel_L2_r` is `‖ŝ − ĝ‖_r / ‖ĝ‖_r`. The removed constants and their difference are reported: a
large gauge difference is not a defect but it is worth seeing.

### 3. The golden contract, and the three refusals

A `Golden` is refused, by name, unless its manifest carries all of:

| Field | Why the absence is fatal |
|---|---|
| `comsol_version`, `model_file`, `export_date` | §7.4 requires the generating model archived alongside. A golden that cannot name what produced it is not evidence |
| `case_hash` | WP7's content hash of the frozen case. A golden compared against a different case is the most expensive kind of wrong answer, and nothing else detects it |
| `probe_hash` | The probe document's content hash. An edited probe grid silently moves the sample points, which is the failure the phase plan chose *our* grid to prevent |
| `refinement` — `published` or `refined_1` | VAL-04's two levels. Mixing them into one `Δ_ref` inverts its meaning |
| per field: `expression`, `unit` | The expected set is `V` [V], `cpos`/`cneg` [mol/m³], `u`/`w` [m/s], `p` [Pa] (`.knowledge/09` §C.2, §C.10). A `mol/L` export is a factor 1000; scaled silently it reads as a 99.9 % discrepancy, which looks like a physics failure and is a units failure |
| `current_boundary`, `current_sign_reference` | NOT IN REPORT (`.knowledge/09` §F): only the author knows. §6.7's NOTE fixes our convention — positive current flows trans → cis, referenced to the grounded cis electrode — and records that an earlier revision carrying the opposite sign negated every conductance. A `trans`-referenced golden is flipped on load and **the flip is printed in the report**, because a silent sign convention is how a rectification ratio comes out reciprocal |

The mask agreement is the fourth refusal and the one that is not about metadata. COMSOL's grid
export writes `NaN` outside the solved domain; ours is the set of points inside the field's
`definedon` materials. These are two independent statements about the same geometry, so comparing
them tests the geometry — but only if the comparison is not a coin flip on points that sit within
an element of the boundary. Hence the margin: a point is retained for field `f` only if it and its
four `±margin_nm` neighbours all lie in `f`'s materials, with `margin_nm = 0.05` by default, the
reference model's own maximum element size on the pore wall (`.knowledge/09` §A.2). With the margin
in place a residual mask disagreement is a real difference between our reference geometry and the
one the export was made from, and it aborts naming the worst point's `(r, z)` and its distance from
the nearest retained point of the other mask.

The remaining trap is the `%Data` row order. `_read_comsol` already documents it as `[i_z, i_r]`,
matching `RadialGrid`'s own layout, and the reader checks that every row has one value per `r`
sample — which catches a ragged file but **not** a cleanly transposed square one. Requiring
`n_r ≠ n_z` on every patch converts that case into a shape error at ingest. It costs nothing: no
physically motivated patch has a reason to be square, and the assertion message says why it is
refused so the next author does not quietly make one.
