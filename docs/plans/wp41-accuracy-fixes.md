# WP41 — The accuracy fixes

**Status: delivered, 8 October 2026.** Written 7 October 2026 at `f5d17cc`, after WP40 was delivered as
`v0.5.0-alpha.6`. It inherits everything the [current brief](current.md) lists as not to be
re-decided, and in particular:

- VER-62's golden and §8.2.9 I4's pre-ruled path: an accuracy fix of REV-07 or REV-08 may move it,
  only within a bound this plan argues before any code changes;
- E4's ruling that the coupled models' `r`-weight order is Phase 6's (NUM-07 NOTE; WP28 D13);
- WP40's rule that a refusal names its requirement, and VER-67;
- WP38's split: `pipeline/checks.py` refuses at resolution, and the stage guards repeat it.

This is the seventh work package of the [Phase 4 plan](phase-4-polish-and-user-testing.md), the
first of the three that §8.2.9 I1 and I2 add. It fixes REV-06 to REV-09, REV-17 and REV-26.
`SPECIFICATION.md` governs, and the identifiers below are pointers into it. **This commit amends
the specification**: the §5.3.1 NOTEs on `inputs:` and on `inputs.charge`, `inputs.eps_r` state a
supplied field's frame (D1). The amendments for REV-07 (the PHY-19 NOTE, one rule) and REV-08
(NUM-16's NOTE) are decided here, their text fixed in *Design* §6, and written in the commits that
move the golden, as I4 requires. The brief runs past its 1,200-word target, and the package is not
split: §8.2.9 I2 rules these six items one package, and I4 requires D3's and D5's bounds to be
registered in it before any code moves. Their evidence is in *Design*.

## Execution brief

### Scope

Six items, each a property a number depends on that today holds by convention (§8.2.9 I2):

| Item | Today | Fix |
|---|---|---|
| REV-06 | A supplied field's frame is unstated beside a moved structure | D1 |
| REV-07 | The gate integrates a supplied field at order 8; the source assembles it at order 3 | D2, D3 |
| REV-08 | One norm over all fields; the residual test closes rungs with the flow 8 × 10⁻⁶ off | D4, D5 |
| REV-09 | A clamp of the ionic-strength driver is never logged | D7 |
| REV-17 | A reworded stabilisation `note` refuses a warm start | D8 |
| REV-26 | `LadderResult` defaults a missing stabilisation record to `none` and `{}` | D9 |

**Breaks** (F4; `CHANGELOG.md`): the solve of a case with a supplied field, and every converged
number, move within D3's and D5's bounds; the electrostatic models' provenance names its mode, so
their stored states do not warm-start across the change (VER-37); a model recording no mode is
refused by `LadderResult`. `nanopnp/field/v1` gains an optional key, a widening that keeps the
identifier, and the case schema does not move. Exit codes do not change (VER-47).

Pointers: QR-03, PHY-13, PHY-19, NUM-07, NUM-13, NUM-16, FR-25, FR-27, IF-05, QR-12, VER-37,
VER-44, VER-62; the §5.3.1 NOTEs on `inputs:` and `inputs.charge`, `inputs.eps_r`; the §4.4 NOTEs;
§8.2.7 G10; §8.2.9 I2, I4; the six items of [the register](../project/review-items.md). No `OPN-`
is open here, and no identifier is new.

### Decisions

| # | Decision | Choice | Why/source |
|---|---|---|---|
| D1 | A supplied field's frame (REV-06) | The model frame, applied unshifted. `FieldDocument` gains optional `model_frame_centre_z_nm: float \| None` (finite); stage 7's export writes its atoms' `shift_z_nm`. `read_fields` refuses a declared value other than `resolved.membrane.centre_z_nm` when `resolved.generates_mesh`, `FieldDocumentError`, text in *Design* §5. Undeclared is read as model frame | Stage 7 exports in the model frame, so the round trip is exact. Refusing an *undeclared* field beside `centre_z_nm ≠ 0` would refuse documents that ran, a narrowing that moves the case schema (G6). Spec amended here (*Design* §4) |
| D2 | One quadrature rule for a supplied field (REV-07) | `FIELD_QUADRATURE_ORDER = 8` in `charge/fields.py`; class attribute `quadrature_order` on `ChargeField` (8) and `DepositedCharge` (`None`: model default). `Measures.volume` and `Measures.integrate` take `rule_order`, an explicit NGSolve rule on every element type of the mesh, refusing `rule_order < 3` naming NUM-07, and refusing it beside `singular` or `extra_order`. The source in every model (`charge_source(fixed_charge, …, rule_order=…)`, threaded from `ResolvedFields.charge` through the ladder) and the gate's total, cumulative (8) and refined (11) legs use it | Order 3 fails its own order/order+3 agreement on a resolved 0.5 nm field (1.2 × 10⁻²); order 8 passes (4.9 × 10⁻⁵ < `QUADRATURE_TOL`). An explicit rule makes source and gate one rule to 4 × 10⁻¹⁶ (*Design* §1). A deposit's total is exact at order 3, and its rule is E4's |
| D3 | REV-07's golden bound (I4) | Per walk, 3 × the prototype's measured drift: `example-02-epnpns` 2.9 × 10⁻⁵, `example-02-classical` 2.7 × 10⁻⁵, `example-03-charged` 1.1 × 10⁻⁵. Every other walk holds 10⁻⁸ | The prototype is D2's operator; the factor covers the darwin and win32 meshes (*Design* §3) |
| D4 | NUM-16's test per field (REV-08) | Converged ⇔ `‖R‖ ≤ atol` (10⁻¹²), or an unforced step with `max_f ‖δu_f‖ / max(‖u_f‖, ρ · max(‖u‖, reference_norm)) ≤ rtol`, `f` each component of the product space, `ρ = NewtonSettings.field_floor_ratio = 10⁻⁶`. The relative residual test `‖R‖ ≤ rtol ‖R₀‖` closes nothing. `NewtonStep.update` records that maximum. No case key moves | Measured: the residual test closed all but one rung of the seven walks; on one rung of example 03 it left the velocity 8.2 × 10⁻⁶ and the pressure 2.0 × 10⁻⁶ off with the ions at 2 × 10⁻⁸. A per-field update test alone would change nothing (*Design* §2) |
| D5 | REV-08's golden bound (I4) | Per walk `2 D_w + 10⁻⁸`, `D_w` the drift to a solve converged at 10⁻¹³: `example-03-charged` 6.8 × 10⁻⁷, `example-07` 5.2 × 10⁻⁸, `2wcd-charged` 1.6 × 10⁻⁶; the other four hold 10⁻⁸ | D4 stops each rung at the same or a later iterate of one sequence, so the move is at most the old stopping error plus the new one (*Design* §2, §3) |
| D6 | Re-pinning (I4) | Items 1 and 2 each re-pin, in their own commit with the clause, every mesh the session deploys: the three `linux-x86_64` levels, by `NPY_DISABLE_CPU_FEATURES`, through `merge_number_stability.py --replace`, the drift and its bound in the commit body. The darwin and win32 cylinder meshes are re-pinned by `/wp-ship` from CI's printed records, each checked against the same bound, before merge | A session cannot deploy another OS's mesh; the fold mechanism exists for exactly this (WP35 D14). A drift beyond its bound stops the package (I4) |
| D7 | The driver clamp (REV-09) | `report_clamp_activations` also logs the correction driver, recomputed by `average_concentration` over the samples, labelled `correction driver (<ionic strength\|average>)`, and counts it | The model clamps the driver; the species log cannot see `I = 6 M` from 2 M and 4 M. Under `average` it never fires (PHY-13) |
| D8 | The warm start's stabilisation gate (REV-17) | `model.stabilisation_provenance` moves from `SPACE_KEYS` to `OPERATOR_KEYS`: recorded when it differs. Mode and constants stay gated by `stabilisation`, `model.stabilisation`, `model.stabilisation_parameters` | Every registered mode's `mode` and `terms` follow from its name and parameters; the rest is prose. Leaf entries cannot do it: VER-37's partition requires each entry to cover a leaf of the `none` descriptor |
| D9 | The empty mapping (REV-26) | `poisson`, `pb`, `pb-linear` record `stabilisation: none`, `{}` and `create("none").provenance`. `LadderResult.stabilisation*` and the rung record read without a default, raising `ValueError` on a missing or non-mapping entry (*Design* §5) | A model with no transport term has mode `none`, and says so; a lost record is then distinguishable from it (NUM-13) |
| D10 | Order | REV-07, then REV-08, each moving the golden against its own bound; D5 was measured on REV-07's prototype. Items 3–6 move no number | One golden move per commit |

### Work items

- [x] 656232a non-Opus 1. [Opus] — a quadrature rule threaded through the solve; a wrong seam moves numbers inside every tolerance. Read *Design* §1, §3, §6 first. `numerics/measures.py` (`rule_order`), `charge/fields.py`, `charge/deposit.py`, `solve/state.py`, `solve/continuation.py`, `physics/models.py`; the PHY-19 and NUM-07 NOTE text of *Design* §6; `.knowledge/06` §8.1 **[tested]**; the re-pin of D3, D6 (D2, D3). Done when `test_charge_quadrature.py` passes, `test_charge_fields.py` and `test_dielectric_field.py` (VER-30) stay green, and the three walks move within D3 and the other four not at all.
- [x] 0328546 non-Opus 2. [Opus] — a convergence criterion; a mistake ends rungs early inside every tolerance. Read *Design* §2, §3, §6 first. `numerics/newton.py`; NUM-16's NOTE; `.knowledge/06` §5 **[tested]**; the NUM-16 prose of `gui/convergence.py` and `gui/widgets/convergence.py` (QR-11); the re-pin; the gate's duration before and after, in the commit body (D4, D5, D6). Done when `test_newton_per_field.py` and the zero-field test pass and the walks move within D5.
- [x] 3a15a72 non-Opus 3. [Opus] — a frame check and its refusal text. `charge/fields.py`, `charge/stage.py` (`read_fields`, `_field_document`) (D1). Done when `test_field_frame.py` passes.
- [x] b9d4a78 non-Opus 4. [Opus] — a missing log is silent. `materials/electrolyte.py` (D7). Done when `test_phy13_a_clamp_of_the_ionic_strength_driver_is_logged` passes.
- [x] 5f021fe non-Opus 5. [Opus] — a key's classification. `solve/state.py` (D8). Done when `test_warm_start_descriptor.py` passes with the mode-settings test.
- [x] 4ff74f3 non-Opus 6. [Opus] — a refusal and a default removed. `physics/models.py`, `solve/continuation.py` (D9). Done when `test_ladder_stabilisation.py` passes.
- [x] 7. [any] Records: REV-06 to REV-09, REV-17, REV-26 `fixed`; `CHANGELOG.md` `0.5.0-alpha.7` with the breaks and both re-pins; this plan's status, the phase plan, the brief. Done when VER-63, VER-72 and the strict docs build pass.

### Verification

| Test | Tier | Identifiers | Oracle |
|---|---|---|---|
| `tests/tier1/test_charge_quadrature.py` (planned here) | 1 | QR-03, PHY-19, NUM-07 | Source applied to `v = 1` equals `mesh_integral_C` to 10⁻¹², areal and volume; refined equals order 11; every `charge_source(fixed_charge, …)` in `physics/models.py` passes `rule_order`; `rule_order` 2, or beside `singular`/`extra_order`, refused; `DepositedCharge.quadrature_order is None` |
| `tests/tier1/test_newton_per_field.py` (planned here) | 1 | NUM-16 | A 10³ linear block and a 0.1 quadratic block both end within 10⁻⁶ of their roots (today the small one ends 1.2 × 10⁻³ off); the last step is unforced, `update ≤ rtol`. Item 2 adds: a block whose root is 0 converges against the floor, and a warm start onto its own state closes in one step |
| `tests/tier1/test_field_frame.py` (planned here) | 1 | FR-27, IF-05, QR-12 | The key reads and defaults to `None`; declared 0 beside a generated mesh at 2 nm is refused with *Design* §5's text, for each key; equal, undeclared and supplied-mesh frames read; the export declares its shift |
| `test_electrolyte.py::test_phy13_a_clamp_of_the_ionic_strength_driver_is_logged` (planned here) | 1 | PHY-13 | 2 M divalent and 4 M monovalent: one record, the exact text of *Design* §5, count 1; `average`: none, count 0 |
| `test_warm_start_descriptor.py::test_ver37_a_reworded_stabilisation_note_loads_and_is_recorded` (planned here) | 1 | VER-37 | Loads, `differing == ("model.stabilisation_provenance",)`. Item 5 adds: every registered mode's `mode`, `terms` equal its name and `",".join(terms)` |
| `tests/tier1/test_ladder_stabilisation.py` (planned here) | 1 | NUM-13, FR-25 | Every registered model names a registered mode, with mappings, `none` and `{}` without transport; each missing or non-mapping entry refused with *Design* §5's text |
| The seven VER-62 walks | 2 | VER-62, §8.2.9 I4 | Items 1 and 2 against D3 and D5; items 3–6 at 10⁻⁸ |
| VER-37's partition, VER-62's file checks, VER-44's convergence tests | 1 | VER-37, VER-62, VER-44 | Unchanged |

Commands: `uv run pytest <file> -v`; the walks under `NANOPNP_RECORD_STABILITY=rec` at each
dispatch level (D6); `.claude/hooks/gate.sh run`.

### Out of scope

- The coupled models' `r`-weight order, and a deposit's source rule: Phase 6 (E4; WP28 D13).
- Refusing an undeclared field beside `centre_z_nm ≠ 0`: a narrowing (G6), not ruled.
- A per-field residual test; an inert `numerics.stabilisation` under an electrostatic model: VER-71, WP42.
- The solid fraction's integrals, which enter no charge: unchanged.

### Open questions

None. REV-06's frame and whether NUM-16's test becomes per field were this plan's to settle from
measurement (phase plan, *Open decisions*): D1 and D4.

## Design

All measurements: this container (`linux-x86_64`, NumPy dispatch `AVX512_SPR`, NGSolve 6.2.2606),
`f5d17cc`, one thread, each walk on its golden reference mesh ("same-mesh" for all seven). The
instrumentation was an environment-gated patch of `numerics/newton.py` and `physics/models.py`,
reverted and not committed.

### 1. REV-07: which rule is right

**What each side evaluates.** `Measures.integrate` floors its order at 5 and adds the singular
bonus, so the gate integrates an areal field at order 8 and a volume field at 5. NGSolve assembles
`fixed_charge · v · r · dx` at its own estimate: the load vector applied to `v = 1` equals
`Integrate(·, order=3)` to 4 × 10⁻¹⁶ (the order-4 rule gives the same number) **[tested]**.

**Measured** on example 02's mesh (`nanopnp mesh cylinder`, 392 elements), relative to `Q_grid`
(−6 e exactly by construction):

| Field | Order 3 (source) | Order 6 (source, `singular=True`) | Order 8 (gate) | Order 11 (refined) |
|---|---|---|---|---|
| Example 02 ring (`r` 2.6, `z` 0) | +5.1e-6 | +2.9e-6 | +4.1e-6 | +7.9e-7 |
| Example 03 ring (`z` 1.5) | +3.7e-5 | +7.4e-6 | −1.9e-6 | −4.8e-6 |
| Alternating, λ = 0.5 nm | +1.2e-2 | −6.4e-4 | +2.0e-5 | −2.9e-5 |
| Alternating, λ = 0.2 nm | −8.8e-1 | +1.1e-1 | −2.0e-2 | +3.5e-3 |
| Alternating, λ = 0.07, 0.035 nm | aliased at every order, as `.knowledge/06` §8.1.1 | | | |

The alternating field is the ring's Gaussian times `0.3 + cos(2π r/λ)`, on a 0.005 nm grid, scaled
to −6 e. **The quadrature's own error** is its order/order+3 agreement, the measure
`QUADRATURE_TOL = 10⁻⁴` already gates. At λ = 0.5 nm, order 3 against 6 differs by 1.2 × 10⁻²,
and 8 against 11 by 4.9 × 10⁻⁵. So the gate passed a field whose solve carried a charge 1.2 % off,
twelve times QR-03's budget: the hazard REV-07 suspected. Order 8 is the lowest measured order
whose own agreement holds on the resolved field; at λ ≤ 0.2 nm no order does, and the agreement gate
refuses the field, as PHY-19's NOTE requires.

**One rule, exactly.** `ngs.dx(intrules={ngs.TRIG: ngs.IntegrationRule(ngs.TRIG, 8)})` in a
`LinearForm`, and in a residual `BilinearForm` applied to zero, gives the same number as
`ngs.Integrate(·, order=8)` to 4 × 10⁻¹⁶ **[tested]**. So the source and the gate can share a
rule, rather than two bonuses on two different base orders.

**A deposit is not affected.** With `v = 1` its integrand `ρ_h · r` is degree 3, and orders 3 to 8
agree to 6 × 10⁻¹⁴ on an L2 P2 field **[tested]**. Its total is exact at the source's order, and
`q_mesh_e` cannot move. The per-entry error that remains is WP28 D13's, which E4 leaves to Phase 6.

### 2. REV-08: what one norm hides

Each Newton step's direction was split into the product space's components. A second run converged
at `rtol = 10⁻¹³`, `atol = 10⁻¹⁵`. Its iterates repeat the default run's up to the default's
closure, so the direction at the default's closing iterate is, to second order, that state's
per-field error.

| Walk | Rungs closed by the residual test | Worst per-field error at default closure | `D_w` (QoI, default → converged) | Newton steps, D4 / today |
|---|---|---|---|---|
| example-01 | 24 of 24 | `u` 7.7e-11, `p` 1.1e-10; ions 5e-13 | 3.8e-13 | 130 / 118 |
| example-02 (both) | 30 of 30 | ions 2.3e-8; flow 3.1e-10 | 1.8e-10, 9.0e-11 | 213 / 186 |
| example-03-charged | 34 of 34 | **`u` 8.2e-6, `p` 2.0e-6**; ions 2.2e-8 (one rung) | 3.4e-7 | 228 / 200 |
| example-07 | 16 of 17 | ions 5.1e-7, `u` 1.4e-7 | 2.1e-8 | 107 / 92 |
| 2wcd-charged (PNP) | 1 of 1 | ions 3.2e-7 | 8.1e-7 | 31 / 30 |
| 2wcd-shell | 1 of 1 | 8.3e-11 | 2.5e-10 | 34 / 33 |

The example 03 rung is a sweep member warm-started from its neighbour, entry residual 196. The
residual test's target was 1.96 × 10⁻⁴; the step that met it left the global update at 9.0 × 10⁻⁹,
which also hides the flow. A per-field *update* test beside the residual test would change nothing,
because no rung reached it, so D4 makes the update test the criterion and keeps only the absolute
floor beside it. The warm-start idempotence NUM-16's NOTE protects is the update test's: a state
already converged has a near-zero direction and closes in one step.

**The floor.** A field that is exactly zero at a rung (`φ` at a zero-bias rung, `u` in an
uncharged pore) needs one. Its direction was 10⁻²⁹ in these runs. `ρ = 10⁻⁶` tests a field smaller
than a millionth of the state's norm absolutely at `rtol · ρ · ‖u‖`, about 10⁻¹¹; every velocity on
the walks is at least 3 × 10⁻⁵ of `‖u‖` (example 01), so each is tested on its own norm.

**D4 is stricter, rung by rung.** Without floors, `‖δ‖²/‖u‖² = Σ‖δ_f‖² / Σ‖u_f‖² ≤ max_f
‖δ_f‖²/‖u_f‖²`, so the per-field maximum is at least the global ratio. A floored field changes the
sum by under `M ρ²`, about 5 × 10⁻¹². Dropping the relative residual test removes a sufficient
condition. So D4 closes each rung at the same or a later iterate of the same sequence. Under D4,
every field of every simulated closure was within 9 × 10⁻¹¹ of its root (example 01's velocity; 3 × 10⁻¹² elsewhere).

**Cost.** 3 % (2WCD) to 16 % (example 07) more Newton steps. Item 2 records the gate's durations
before and after; §7.6 NOTE's levers make tests cheaper and do not forbid a fix its price.

### 3. The bounds and the re-pin

REV-07's prototype was D2's operator: the coupled source at an explicit order-8 rule. Its drift
against the golden, per walk, is the largest over every quantity:

| Walk | REV-07 drift (largest) | D3 bound | `D_w` after REV-07 | D5 bound |
|---|---|---|---|---|
| example-01 | 0 (no field) | 10⁻⁸ | 3.8e-13 | 10⁻⁸ |
| example-02-epnpns | 9.8e-6 (`eof_m3_s`) | 2.9e-5 | 9.0e-11 | 1.0e-8 |
| example-02-classical | 8.9e-6 (`eof_m3_s`) | 2.7e-5 | 1.8e-10 | 1.0e-8 |
| example-03-charged | 3.6e-6 (`currents_A[Cl-]`) | 1.1e-5 | 3.4e-7 | 6.8e-7 |
| example-07 | 0 (deposit) | 10⁻⁸ | 2.1e-8 | 5.2e-8 |
| 2wcd-charged | 0 (deposit) | 10⁻⁸ | 8.1e-7 | 1.6e-6 |
| 2wcd-shell | 0 (deposit) | 10⁻⁸ | 2.5e-10 | 1.0e-8 |

The total charge moved by only 1.0 × 10⁻⁶ and 3.9 × 10⁻⁵, but the distribution moved more, so
D3 is set from the measured QoI drift, not from the charge. D5's bounds lie inside VER-35's
10⁻⁶ nonlinear tolerance. D3's are a discretisation change of a few parts in 10⁵, far inside each
walk's physical significance and the golden's 10⁻³ ceiling.

D5: the old state is `D_w` from the converged one, and the new is within round-off of it, so the
move is at most `D_w` plus the new stopping error. `2 D_w + 10⁻⁸` allows for both, and the floor
is the same-mesh tolerance.

The darwin and win32 cylinder meshes give values within 10⁻⁹ of the linux mesh (the walks'
mesh-moved tolerance is 10⁻⁸), so the same drifts and bounds apply to their records.

### 4. REV-06: the frame

Stage 5 maps a profile point from the stage-1 frame by `z_m = z_s − c`, with `c` the case's
`centre_z_nm`. Stage 7 shifts the atoms by the same `c` (`charge/stage.py` `frame_shift_nm`) and
exports the lattice in `z_m`. A field written for a case with `c_d` puts a feature from `z_s` at
`z_s − c_d`. Applied in a case with `c`, it lands where the structure's `z_s − c_d + c` is: off by
`c − c_d` along `z`. With `c_d` declared, that offset is computable and refused when non-zero. When
nothing is declared, the statement that a supplied field is in the model frame is the contract,
which the export already keeps.

### 5. Texts

`{key}` is `charge` or `eps_r`; values are written with `:g`, the offset with `:+g`.

| Site | Text |
|---|---|
| D1, `read_fields` | `inputs.{key} declares model_frame_centre_z_nm {declared} nm and geometry.membrane.centre_z_nm is {centre} nm: the field was written in another model frame than the mesh stage 5 generates, so every feature would sit {centre − declared} nm along z from where it was written (section 5.3.1 NOTE on inputs.charge, inputs.eps_r); export the field from this case, or correct the declaration` |
| D7, the driver | Label `correction driver (ionic strength)` or `correction driver (average)`, through `log_clamp_activations`' existing format: `{label}: concentration correction clamped at 5.3 M for 1 sample(s); peak driver 6 M is outside the fit range. worst at (1.0, 2.0)` |
| D9, missing | `model {name!r} records no {key} in its provenance; every model names its stabilisation mode, that mode's parameters and their provenance, 'none' where it assembles no transport term (NUM-13, section 5.3.3)` |
| D9, not a mapping | `model {name!r} records {key} as {type(value).__name__}, not a mapping (NUM-13, section 5.3.3)` |
| D2, below the floor | Names `rule_order`, its value and NUM-07's minimum of 3 |
| D2, combined | Names `rule_order` and the argument passed beside it |

### 6. The clauses items 1 and 2 amend

**Item 1**, a new paragraph at the end of the §4.4 NOTE on the consumer leg (PHY-19): *"A supplied
field's source term and every leg of its conservation check SHALL be evaluated by one explicit
integration rule, of order 8, so that the gate measures the charge the solve assembles. NGSolve's
own estimate for the source was order 3, and on a 0.5 nm alternating field the deployed mesh
resolves it put the solved charge 1.2 × 10⁻² from the grid's while the order-8 gate passed at
2 × 10⁻⁵ (WP41 D2, REV-07). A deposited charge keeps the model's default: its total is exact there,
and its per-entry order is NUM-07's open question."* And one sentence in the NUM-07 NOTE on the `r`
weight: *"A supplied field's source term is assembled at order 8 (PHY-19's NOTE on one rule), which
settles that term and not this question."*

**Item 2**, NUM-16's NOTE on the relative tolerance, replacing its last two sentences: *"The
implementation therefore converges on a relative-update test evaluated on the undamped Newton
direction, field by field: for every field `f`, `‖δu_f‖ ≤ rtol · max(‖u_f‖, 10⁻⁶ · max(‖u‖, 1))`,
or when the residual is at its absolute floor, 10⁻¹². One norm over all fields is dominated by the
largest, and the residual relative to its entry value is one norm too: measured on the seven gated
walks, it closed every rung but one, and on a warm-started rung of example 03 it left the velocity
8.2 × 10⁻⁶ and the pressure 2.0 × 10⁻⁶ relatively unconverged with the ions at 2 × 10⁻⁸ (WP41 D4,
REV-08). A step that failed to reduce the residual never counts as convergence."*
