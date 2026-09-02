# Phase 0 consolidation: audit and remediation plan

**Status: audit complete, 2 September 2026. The Phase 0 spike is in excellent health — tiers 1 and
2 green (309 passed), `mypy --strict` and `ruff` clean, no defect found that produces a wrong
number. Three provenance/boundary risks are carried into Phase 1; everything else is a reserved-slot
gap that the release plan already schedules. Remediation is one short phase (A) plus two small
architecture packages (B); documentation (C) is a single reconciliation.**

This is a consolidation audit of the merged Phase 0 work (WP1–WP6), written after reading
`SPECIFICATION.md`, the `.knowledge/` base, and every module of `src/nanopnp/`. It touches no `src/`
or `tests/` file. `SPECIFICATION.md` governs; where this plan and the specification disagree, the
specification is right and this plan is wrong.

---

## 1. Executive summary

**The spike is sound, and the honest headline is that there is nothing here that produces a
plausible wrong number.** The parts of the code where such an error would live were read line by
line, and each holds:

- the correction forms (`materials/forms.py`) — both wall functions carry the opposite offset signs
  of PHY-11 (`exponential_saturation_plus`, `logistic_plus`), `P₁ = 6.2 nm⁻¹`, the Gavish
  permittivity parameters, and match the §4.3 check values;
- the steric flux (`physics/nernst_planck.py:114`) — `β_i` enters the bracket with `+` and the
  bracket is negated once (PHY-05); the sum runs over all species; the `a_i³/a_0³` prefactor is kept;
- the constants (`core/constants.py`) — one CODATA-2018 source of truth, `F = e N_A`, `R = k_B N_A`,
  each cited;
- the axisymmetric measures (`physics/measures.py`) — the `1/r` guarantee is a bonus of ≥ 3 in its
  own right (not a deficit against an unknowable estimate), and `bonus_intorder` is refused at the
  seam;
- the QoI routes (`post/qoi.py`) — both current routes, cross-checked in total **and per species**,
  `2π` restored exactly once, the cis-electrode sign pinned by VER-17;
- the force split (`post/forces.py`) — all three routes with the NUM-28 consistency terms, route C
  as the oracle on the split (RSK-04);
- the NUM-17 gates (`solve/gates.py`) — positivity, packing and the potential cap, sampled on the
  fluid-restricted P2 nodal set, each aborting with the field and location.

`mypy --strict` passes on 45 files with **zero** `type: ignore`, `cast(`, or widened `Any`
annotation in the package; `ruff check` and `ruff format --check` are clean. The tests are named for
the requirement they discharge, and the Tier-2 tolerances are tight and, where argued (VER-16's 3 %
space-charge film, VER-21's 15 % Smoluchowski limit), argued in the §7.3 idiom the amendment
precedent established — not slackened to pass.

What remains is **provenance completeness and one data boundary**, all bearing on Phase 1 rather than
on any Phase-0 number, plus the reserved-slot pipelines the release plan defers. The plan below is
therefore deliberately short.

---

## 2. Audit findings

Ranked within each dimension by capacity to produce a wrong number that nobody detects. **Defect** =
something is wrong; **gap** = something is absent; **risk** = something correct now that will bite in
Phase 1. Severity is Low/Med/High.

### 2.1 Test-suite semantic integrity

No tautological tests, no return-type-only assertions, no mock-validation theatre were found. Every
Tier-2 benchmark asserts a physical quantity against a closed form or a measured convergence order.

- **[risk, Low]** No finding of a masking tolerance. The two tolerances that are *loose relative to
  a naive expectation* are both legitimate and documented: VER-16 asserts `rel=0.03` on the limiting
  current (`tests/tier2/test_pnp_benchmarks.py:191`) because a Tier-2-budget film is
  space-charge-limited (plan §WP5; converges to 1.017 at 2000 nm), and VER-21 allows 15 % against
  Smoluchowski (`tests/tier2/test_electrophoretic_mobility.py`) because Henry's own function is
  11.5 % below `εζ/η` at the largest affordable κa (§7.3 amendment). Both are the §7.3 precedent, not
  a violation of it. **What each still admits:** VER-16 at 3 % would pass a current wrong by ~2× the
  film's own discretisation error; that is bounded by the monotone-approach assertion beside it
  (`currents[-1] < 0.1*ohmic`, `> 0.75*limiting`), so the tolerance is not load-bearing alone. No
  action.
- **[observation]** Invariant coverage is complete for what Phase 0 solves: charge conservation is
  Phase 3 (VER-01/02, below); positivity, packing < 1 and the flux-route agreement (FR-23, QR-04)
  are all asserted in Tier 1/2 (`test_ver08_*`, `test_num26_*`, `test_ver11_*`); the mesh-quality
  gate (QR-12/VER-10) is the one named invariant with no test — see 2.2.

### 2.2 Coverage and physical-limit auditing

VER identifiers with a real, traceable Phase-0 test: **VER-03, 04, 05, 06, 07, 08, 11, 12, 13, 14,
15, 16, 17, 18, 19, 20, 21, 22.** Each names its requirement (`test_ver17_access_conductance_matches_maxwell_hall`),
discharges it, and traces its reference value to `.knowledge/` or the spec (e.g. VER-03 to the §4.3
check values; VER-04 to `μ⁰ = D⁰/V_T`; VER-05 to the `.knowledge/01` §3.0 drift table).

Gaps, all distinguished as *missing test for a not-yet-built stage* rather than *missing
requirement* — none is a defect, and the release plan (§2.7, §8.1) schedules each:

- **[gap, —] VER-01, VER-02** (charge conservation, per-z-slice) — `charge/` is an empty reserved
  slot; Phase 3. Correctly absent.
- **[gap, —] VER-09 / FR-26** (case-file round-trip) — `io/` is empty; the case schema is Phase 1 by
  the plan's own design decision to keep Phase-0 config unfrozen. Correctly absent. See 2.3 on the
  unused `pydantic` dependency.
- **[gap, Med] VER-10 / QR-12** (mesh quality gate, min SICN/gamma > 0.3, worst element reported).
  `mesh/primitives.py` builds real Netgen meshes via `netgen.occ` but carries **no** quality gate
  (`grep` for `sicn|gamma|quality|optimize` in `mesh/` hits only a docstring word). RSK-05/VER-10
  is nominally a Phase-2 detection, but the gate is a v0.5 (QR-12) requirement and the meshes it
  would guard already exist. Bringing a thin gate forward is cheap and closes a named invariant —
  see WP-B3 (optional).

**Convergence evidence.** The suite verifies spatial order exactly where the specification puts that
burden: VER-18 (MMS) asserts measured rates `> 2.8` for the P2 fields and `> 1.8` for the P1
pressure (`tests/tier2/test_mms.py:118,128`), and VER-19 asserts a drag rate `> 1.5` on top of the
1 % tolerance. The electrostatic and transport benchmarks (VER-12…VER-17) assert single-mesh
tolerances rather than orders — which is correct: §7.3 designates VER-18 as "the only route that
verifies the `u_r/r²` term and the axis treatment," and the DH-cylinder O(h³) result lives in
`.knowledge/06` §8.3 as a measured fact rather than a gate. **Conclusion: convergence order is
verified where it localises an error; no additional order-of-convergence test is owed in Phase 0.**

Limits not yet claimed by any identifier (candidates for Phase 1, not Phase-0 defects): a
Robin/mixed-BC benchmark, a steric-wall (finite-size) boundary limit, and a bulk-truncation
sensitivity study for VER-17 beyond the two reservoir sizes already recorded. These are *missing
requirements*, so their fix is a specification change, not a test — noted for the Phase-1 planning
conversation, not scheduled here.

### 2.3 Architecture and interface harmonisation

The stage contract holds: `CoupledModel` and the correction models expose typed `.provenance`,
declared `.fields`, and content is carried on typed `ModelSolution` / `LadderResult` artefacts
(FR-27). The weak forms are written once against the `Measures`/coefficient seam with no
backend-specific construct in `physics/` outside the deliberate deferred `import ngsolve` (QR-13,
CON-06). The empty subpackages (`structure/ density/ symmetry/ charge/ io/ sweep/ gui/`) are
reserved slots, and nothing outside them has grown their responsibility — verified by grep; the
materials/physics/solve/post layers own only their own concerns.

- **[risk, Med] Stabilisation mode is absent from every provenance record (FR-25, NUM-13, §5.3.3).**
  `CoupledModel.provenance` (`src/nanopnp/physics/models.py:501`) records model, fields, switches,
  deviations, scales and materials but **not** the stabilisation mode; the ladder record
  (`src/nanopnp/solve/continuation.py:239`) likewise omits it. Across the whole package the word
  appears only in docstrings — no provenance key holds it. The mode is trivially `none` in Phase 0
  (NUM-11, unstabilised), but §6.4/§7.4 make it load-bearing: "a number recorded without its
  stabilisation mode is not comparable," and Phase 1's COMSOL comparison must attribute a per-cent
  discrepancy to *stabilised-vs-unstabilised* rather than to a bug. A manifest that cannot state the
  mode cannot do that attribution — which is precisely how a real discrepancy becomes a plausible
  wrong number nobody can localise. **This is the top-ranked risk.** Fix: WP-B1.
- **[risk, Low] Correction files cross the one Phase-0 serialisation boundary as a raw
  `dict[str, Any]`** (`src/nanopnp/materials/corrections.py:22,48`; consumed by
  `materials/models.py:275,303`). CLAUDE.md's rule — "Pydantic models at every serialisation
  boundary … never pass raw dicts across a stage boundary" — is met nowhere because the boundary is
  hand-validated: a renamed or missing coefficient key surfaces as a `KeyError` deep in
  `_property_node`/assembly rather than as the key-naming diagnostic IF-03 sets as the house
  standard. `pydantic` is already a declared dependency (below) and unused, so the fix has no new
  cost. Fix: WP-B2. This is also the *template* the Phase-1 case-file schema (FR-26/VER-09) will
  copy, so it is worth fixing before it is copied.
- **[gap, Low] `pydantic` is a declared dependency but imported nowhere in `src/`** (`grep`
  confirms; only `pyproject.toml`). The plan's design note ("a small pydantic model in `core/`") was
  never built because Phase-0 config is programmatic. Harmless, but it is dead weight until WP-B2 or
  Phase 1 uses it; do not remove it (Phase 1 needs it), just record that it is currently unused.
- **[observation] Provenance is assembled ad hoc** from component `.provenance`/`.summary` rather
  than by an `io/` manifest writer (IF-08/FR-25). Correct for a spike; the unified manifest is Phase
  1. The stabilisation-mode fix (WP-B1) must land in the component records so the eventual manifest
  inherits it.

### 2.4 Units, constants and numerics

- SI-internally / units-in-the-name is upheld (`radius_nm`, `bias_V`, `temperature_K`,
  `c_avg_M`, `wall_distance_nm`); the boundary conversions live in one place each
  (`electrolyte.MOLAR_PER_SI`, `coefficients.mesh_unit_scales`).
- **NUM-09/NUM-10/NUM-27 scale factors are applied exactly once.** `coefficients.py` refuses any
  `length_nm ≠ 1.0` (the mesh unit) with a diagnostic; `post/qoi.py:81` restores `2π` once and says
  so; `post/forces.py` inherits the convention and does not re-apply it (verified — the WP6 trap).
  Constants resolve to `core/constants.py` alone, each cited.
- **Corrections are data, not code:** every fitted coefficient and `ε_protein`/`ε_membrane` live in
  `data/corrections/willems2020_nacl.yaml`; no coefficient is hardcoded in Python (grep clean).
- Integration order ≥ 3 on every `1/r` form is asserted at the seam and tested (VER-07,
  `test_ver07_order_two_returns_nan_on_an_axis_touching_mesh`).
- The current is never a cross-section CG-flux integral (NUM-23); both sanctioned routes are
  cross-checked (`post/qoi.extract`).
- Newton tests the relative update on the undamped direction and never calls a residual-raising step
  converged (`solve/newton.py`, `test_num16_*`).
- **[risk, Low–Med] PHY-13 clamp-activation logging is implemented and unit-tested but not wired
  into any solve or QoI path.** `Electrolyte.report_clamp_activations` /
  `log_clamp_activations` (`src/nanopnp/materials/electrolyte.py:458,523`) satisfy PHY-13's
  "logged with location and property," and `test_phy13_*` exercises them — but the only caller
  outside tests is nothing: `grep` finds no reference in `solve/`, `physics/` or `post/`. A real run
  at high salt near a charged wall (where the counter-ion driver can exceed 5.3 M) therefore clamps
  the correction driver **silently**, which `.knowledge/01` §3 names explicitly as "a plausible
  source of confusion." The clamp itself is correct (PHY-13 cap); it is the *silence* that violates
  the requirement. Fix: WP-A1.
- **[observation] Unspecified-but-justified constants.** `SATURATED_WALL_DISTANCE_NM = 3.0`
  (`coefficients.py:52`), `INTERIOR_OFFSET = 1e-4` and `PACKING_WARNING = 0.8` (`gates.py`) carry no
  `NUM-`/`PHY-` identifier. Each is documented and empirically calibrated. They are findings only in
  the sense that they are unspecified; changing them would be a regression, not a fix (see §4).

### 2.5 Documentation conflict reconciliation

Reconciled in the SPECIFICATION → `.knowledge/` → code → docstring order.

- **[verified consistent, no action] `T_H` sign convention.** `post/forces.py` returns
  `−pI + 2η sym∇u` (the momentum-assembly convention) while `.knowledge/05` §4 prints its negative.
  This is the deliberate opposite-sign pair the audit brief flags; the code's docstring pins which
  convention it holds, and route C (the reaction force) is the oracle that would catch a slip. No
  change — "fixing" this is a bug.
- **[verified consistent, no action] Bias orientation.** `post/qoi.py:31` and NUM-24's amended sign
  agree: `ψ = 1` on cis (grounded, `φ = 0`), positive current trans→cis, `G > 0` — matching VER-17.
- **[doc item, Low] The permittivity-parameter question is recorded as "still open" in
  `.knowledge/00-index.md` (#5) and `.knowledge/01` §8 (E5), but the code and the spec have in fact
  settled it.** `data/corrections/willems2020_nacl.yaml:125` and `forms.gavish_langevin` commit to
  the model-report Gavish values (30.08, 11.5), which govern per §1.6 and §4.6 erratum 6. The
  knowledge base's own "open" framing now lags the shipped decision; this is a documentation
  reconciliation, not a code defect (the code is correct against the governing authority). Fix:
  WP-C1.

### 2.6 Documentation clarity, conciseness and tone

Docstrings are NumPy-style throughout, British-spelled, with units named and an equation/identifier
reference rather than a derivation. No academic throat-clearing or spec-restating paragraphs were
found; where a module explains *why* (the `steric_flux` warning, the `Measures` `1/r` note) it is
earning its place by preventing a specific known error. **No clarity finding rises to an action.**
One cosmetic note, not scheduled: `logistic_plus`'s name refers to its leading `1 + exp` sign while
its *offset* is minus — the docstring already disambiguates, so this is left alone.

---

## 3. Phased action plan

Delivery is one work package per PR through `/wp-plan → /wp-implement → /wp-ship`, each green on
tiers 1 and 2 before the next starts. Every step has a machine-checkable acceptance criterion. **No
step changes specified behaviour**, so none amends `SPECIFICATION.md` — except WP-B3, which is
flagged where it would.

### Phase A — provenance/logging remediation (the wrong-number-adjacent items first)

**WP-A1 — Wire PHY-13 clamp logging into the solve/extract path.** Call
`Electrolyte.report_clamp_activations` over the converged concentrations (fluid-restricted sampler,
as the gates do) from the QoI-extraction or end-of-solve diagnostic, so a real high-salt run emits
the clamp record PHY-13 requires.
- *Acceptance:* a new Tier-2 test `test_phy13_a_high_salt_solve_logs_the_clamp` drives a
  near-wall high-salt point and asserts (via `caplog`) the clamp warning fires with a location; and
  `grep -rl report_clamp_activations src/nanopnp/{solve,post}` is non-empty. Existing 309 tests stay
  green.

### Phase B — architecture alignment

**WP-B1 — Record the stabilisation mode in provenance (FR-25, NUM-13, §5.3.3).** Add a
`stabilisation` field (value `"none"` this phase) to `CoupledModel.provenance` and to
`LadderResult.summary`, sourced from the model/solve settings rather than a literal, so NUM-14's
stabilised mode populates it automatically when Phase 1 adds it.
- *Acceptance:* `test_fr25_provenance_records_the_stabilisation_mode` asserts the key is present and
  equals `"none"` in both the model provenance and the ladder record; existing FR-25 tests updated
  and green.

**WP-B2 — Validate correction files through a typed schema at load.** Replace the raw-dict return of
`load_corrections` with a `pydantic` (or `dataclass` + validator) model, rejecting an unknown or
missing coefficient key with a diagnostic that names the key — mirroring IF-03. Removes the
`dict[str, Any]` boundary and gives the yet-unused `pydantic` dependency its first use.
- *Acceptance:* `test_corrections_reject_an_unknown_key_naming_it` and
  `test_corrections_reject_a_missing_coefficient` pass; `grep 'dict\[str, Any\]' src/nanopnp/materials`
  is empty; VER-03 and the materials tests stay green. No behaviour change on a valid file.

### Phase C — documentation harmonisation

**WP-C1 — Reconcile the permittivity "still open" note.** Update `.knowledge/00-index.md` (#5) and
`.knowledge/01` §8 (E5) to record that the shipped model and §4.6 erratum 6 have settled on the
model-report Gavish parameters (30.08, 11.5) as governing, keeping the author-query history as
resolved rather than open. No `src/` or `SPECIFICATION.md` change.
- *Acceptance:* the two knowledge files and `SPECIFICATION.md` §4.6 state the same status; a grep
  for the stale "ask the author"/"open" framing on the permittivity cap returns nothing; docs-only
  diff.

### Optional (bring Phase-2 work forward only if capacity allows)

**WP-B3 — A mesh quality gate for the analytic primitives (VER-10, QR-12).** Add a min-SICN/gamma
> 0.3 gate with worst-element reporting to `mesh/primitives.py`, and a `test_ver10_*`. **This does
not change specified behaviour but does discharge a v0.5 requirement early**; it is optional because
RSK-05/VER-10 is a Phase-2 detection point and the analytic primitives are not yet the risk they
guard against. If taken, it needs no spec amendment (QR-12 already mandates the gate).

---

## 4. Explicitly not doing

Each considered and rejected, with the reason. This list is as much of the deliverable as the
findings.

- **Not touching the `T_H` sign convention** (`post/forces.py` vs `.knowledge/05` §4). The opposite
  signs are deliberate and documented, and route C is the oracle that would catch a real slip.
  Aligning them would either double-negate the force or desync the docstring from the assembly.
- **Not "tightening" `SATURATED_WALL_DISTANCE_NM`, `INTERIOR_OFFSET`, or `PACKING_WARNING`.** Each is
  empirically calibrated (the offset is the measured 1e-4 that beats point-location tolerance; the
  saturation distance is the bulk sentinel that avoids the `f^w(0)=0.06` wall trap). Changing them
  reintroduces the exact silent failures their comments record.
- **Not hoisting `ngsolve`/`netgen`/`numpy` to module scope.** The deferred imports are a measured
  FR-27 cost (a sweep introspects stages without assembling); hoisting is a regression, not a
  cleanup.
- **Not adding VER-01/VER-02 (charge), VER-09/FR-26 (case round-trip), or the `io/`/`charge/`/
  `sweep/` implementations.** These are Phase 1/3 by the release plan (§2.7, §8.1); pulling them into
  a Phase-0 consolidation would be scope creep, and they are correctly-empty reserved slots, not
  defects.
- **Not converting the whole configuration to the `nanopnp/case/v1` schema.** Freezing the case file
  against a spike's needs is the wrong shape (plan design decision); WP-B2 validates only the
  correction-file boundary that already exists.
- **Not implementing SUPG / the NUM-14 stabilised mode now.** It is optional and belongs with the
  Phase-1 COMSOL comparison; WP-B1 records the *mode* so that comparison can be made, which is the
  Phase-0-appropriate half.
- **The repository traps, left upheld, not "fixed":** no zero-bias PNP run is proposed as a
  Gouy–Chapman/Debye–Hückel benchmark (PHY-24); no test asserts `D_i/μ_i = kT/e` at finite
  concentration (VER-05/PHY-14); `⟨c⟩` stays the arithmetic mean and `d` stays pore-only (PHY-01/
  PHY-02); the wall-function signs and `6.2 nm⁻¹` stand; classical PNP-NS stays a configuration, not
  a branch; `dielectric_gradient_forces` stays default-off (PHY-23). The audit confirms the code
  *upholds* each of these; none is a finding.
