# WP12 — Reference-matching stabilised mode

**Status: delivered, 14 September 2026; the three questions it opened were closed by author ruling,
13 September 2026.** Written 13 September 2026, after WP7 (case schema, artefacts,
manifest), WP8 (mesh ingestion and quality), WP9 (external fields), WP10 (case-driven runs, the CLI,
field output) and WP11 (the sweep runner). It inherits a solver whose stabilisation mode is recorded
everywhere and applied nowhere: `CoupledModel.stabilisation` exists, reaches the provenance, the
solve descriptor, the warm-start gate and the FR-25 manifest, and `SUPPORTED_STABILISATIONS` is
`frozenset({"none"})`, so every path that carries the mode has been exercised with exactly one value.

This package belongs to `docs/plans/phase-1-solver-core.md`. `SPECIFICATION.md` governs: where this
file and the specification disagree, the specification is right and this file is wrong. Every
`NUM-`, `VER-`, `PHY-`, `QR-` and `IF-` identifier below is a pointer into it, never a restatement.
Seven amendments this plan needs are made to `SPECIFICATION.md` in the same commit and are listed
under **Specification amendments** at the end.

## Context

Phase 1's gate is *Tier 1 and Tier 2 pass; Tier 3 enabled and differences attributed* — attribution,
not agreement. §7.4 makes the 1 % field / 0.5 % QoI targets conditional on two preconditions, and
this package builds the first of them: the reference ran **with** consistent stabilisation in both
the transport and the flow interfaces, on **P1+P1** velocity and pressure, so an unstabilised
Taylor–Hood solve is a different discretisation of the same PDE and per-cent-level disagreement is
an implementation difference rather than a defect (`.knowledge/09-comsol-reference-settings.md` §C.1,
RSK-18, closed). Until the matching mode exists, WP13 has one number against a golden and no way to
say what fraction of it is the stabilisation.

The three preceding packages left this one a clean seam and one unfinished requirement each:

- **The mode is plumbed but empty.** `CoupledModel.provenance["stabilisation"]`
  (`src/nanopnp/physics/models.py:550`) → `LadderResult.stabilisation`
  (`src/nanopnp/solve/continuation.py:244`) → `manifest.stabilisation_group`
  (`src/nanopnp/io/manifest.py:245`), and the solve descriptor gates on it
  (`src/nanopnp/solve/state.py:130`, VER-34, VER-37). Two of those tests currently use the strings
  `"streamline"`, `"crosswind"`, `"supg"` and `"reference"` as *arbitrary differing values* to prove
  the gate fires. WP12 is where one of them becomes real.
- **NUM-03 is half done.** `numerics.elements` is read (`src/nanopnp/io/case.py:1094`) and the
  equal-order pair is refused unconditionally (`models.py:458`, message `"inf-sup"`). The reference
  used quadratic `φ` and `c` with **linear** `u` and `p`, and `CoupledModel.order` currently governs
  `φ`, `c` *and* `u` together, so that configuration is not expressible at all.
- **NUM-11 is half done.** "The production solve SHALL run without stabilisation" holds because
  nothing else exists; "SUPG SHALL be available behind a flag" does not.
- **NUM-12 is not started.** Nothing evaluates `Pe_h` anywhere. `specialcf.mesh_size` is unused in
  the whole package; the only element-size concept is a diagnostic string
  (`src/nanopnp/solve/linear.py:324`).

The risk this retires is the half of **RSK-09** that is ours rather than the reference's. RSK-09
says the reference carries no mesh convergence study, so part of any Tier-3 residual may originate in
it; §Design below shows that the reference's *own* transport stabilisation adds artificial streamline
diffusion in the ratio `Pe_h²` to the physical diffusivity — `ζ̃²/100` on a mesh built to its own
NUM-30 resolution rule, so **9 % inside the double layer at `ζ̃ = 3` and 0.09 % in the pore lumen**.
That is not a bound on the reference's discretisation error, but it is the first quantified term in
it, and it is the term WP13's `Δ_stab` is made of.

## Decisions taken before implementation

| Decision | Choice | Why |
|---|---|---|
| Where the stabilisation lives | A new `src/nanopnp/physics/stabilisation.py` holding a `StabilisationModel` protocol, a `_REGISTRY`/`register`/`create` triple and a `NoStabilisation` entry named `none` — the shape of `materials/models.py` one level up. `SUPPORTED_STABILISATIONS` becomes the registry's key set rather than a literal | PHY-22's rule generalised, which the phase plan already committed to: "off" is a *named model*, not a code branch. It also makes the ablation of §7.4 a configuration sweep rather than three code paths, and it is the only shape under which `CoupledModel.residual_form` gains no `if` on the mode |
| The registered modes | Three. `none` assembles nothing. `supg` assembles the transport streamline term only. `reference` assembles transport streamline **and** crosswind **and** the flow GLS and grad-div terms, and is the only mode that permits an equal-order velocity–pressure pair | NUM-11 and NUM-14 are *different* requirements: NUM-11 wants SUPG behind a flag for coarse continuation meshes, NUM-14 wants the reference's whole setting table. One mode cannot discharge both, and collapsing them would make the WP13 attribution ladder unable to separate the transport term from the flow pair |
| What `reference` does on a Taylor–Hood pair | Assembles the flow stabilisation anyway | The phase plan's attribution ladder is `none`+P2/P1 → `reference`+P2/P1 → `reference`+P1/P1, so the middle configuration must be "the whole stabilisation, the stable pair". The flow terms are consistent (§Design), so on a stable pair they are asymptotically inert rather than wrong, and the measurement of *how* inert is one of this package's outputs |
| The advective velocity | `b̃_i = z_i μ̃_i ∇φ̃ + D̃_i β̃_i − Pe ũ` — migration, the steric drift and convection, the whole non-diffusive part of the PHY-04 flux bracket | `species_flux` already assembles the bracket term by term in exactly this order (`nernst_planck.py:260-277`); taking `b̃_i` as the migration term alone would stabilise an operator the solver does not solve, and the steric drift is the term that diverges when its sign is wrong |
| `τ` for the streamline term | `τ_i = (h_K / 2‖b̃_i‖)·ψ(Pe_K)`, `ψ(q) = min(q, 1)`, `Pe_K = ‖b̃_i‖ h_K/(2 D̃_i)` | The form §6.4.1 already names, from Chaudhry, Comer, Aksimentiev & Olson (*Commun. Comput. Phys.* **15**, 93, 2014) — the same paper that reports the spurious negative concentrations near charged nanopore walls this mode is supposed to remove. Choosing a different `ψ` would put a numerics constant in Python that the specification already fixes |
| `h_K` | `ngsolve.specialcf.mesh_size`, **measured** to be exactly `sqrt(2|K|)` on triangles — 2.4 × 10⁻¹⁵ relative over 14 elements, which is the leg length of the right isoceles triangle of the same area and 0.931 × the side of the equilateral one | A direction-dependent streamline length `h_b = 2/Σ_a\|b̂·∇N_a\|` needs per-element basis gradients NGSolve does not expose as a coefficient function. The isotropic measure is standard, the 7 % gap to the edge length sits inside the tuning constant, and pinning the definition by measurement rather than by assumption is what keeps `τ` reproducible when NGSolve changes. Recorded in `.knowledge/06-numerics-fem.md` as **[tested]** |
| What "Approximate residual" means here | **Every second derivative of a trial field is dropped**, leaving `R̃_i = b̃_i·∇c̃_i − s̃_i`, with `s̃_i` the manufactured or case source when one is present | It is the setting the reference ran (NUM-14's table) and COMSOL does not export what it means, so it is defined here rather than guessed. Dropping the *whole* divergence rather than the half that survives keeps the residual a pure advective residual, which is what `τ` was derived for, and it is what makes the term free of `1/r` — see §Design |
| The consequence of that, faced rather than hidden | The streamline term is **inconsistent by construction**: on the exact solution `R̃_i = −∇·(D̃∇c̃) + axis terms ≠ 0`. §Design derives that the added error is `O(h²)` in L², so the stabilised MMS rate is **predicted to fall from 3 to 2**, and a rate below 2 is a defect in the term rather than a property of the scheme | This is the load-bearing prediction of the package. A plan that said "MMS still converges" would have the implementer chase a phantom bug for a day when it converges at 2. The phase plan already asked for "a measured rate" rather than an asserted one; this says what to expect and what would falsify it |
| The crosswind term | A Do Carmo–Galeão-*type* term, written out in §Design: `Σ_K ν_K ∫_K (P_b ∇c̃_i)·∇w r dr dz`, `P_b = I − b̂⊗b̂`, `ν_K = max(0, C_cw h_K ‖R̃_i‖ / (2‖∇c̃_i‖) − D̃_i)`, `C_cw = 1` | `.knowledge/09` §F: COMSOL's `tds.crosswind` is **not exported**, so bit-for-bit matching is impossible and the term is an irreducible systematic in any comparison. What is reproducible is the *family* — residual-scaled, acting across the streamline, switching itself off where the solution is smooth — and the arithmetic that follows from it, which §Design carries |
| The crosswind switches itself off | Exactly. `‖R̃_i‖ = ‖b̃_i·∇c̃_i‖ ≤ ‖b̃_i‖‖∇c̃_i‖`, so `ν_K ≤ D̃_i (C_cw Pe_K − 1)` and **`ν_K ≡ 0` wherever `C_cw·Pe_K ≤ 1`** | With `C_cw = 1` the crosswind term is a no-op on every mesh that satisfies NUM-30, and it activates on exactly the elements where NUM-12's warning fires. One trigger, two consequences: the order-6 quadrature of NUM-15 is paid only where it buys something, and "the crosswind contributed nothing on this mesh" becomes a reportable measurement rather than an assumption |
| Which mesh verifies the crosswind, then | A deliberately coarse one, `Pe_K > 1`, where **plain Galerkin trips the NUM-17 positivity gate and `reference` does not** | A term that is identically zero on every test mesh is untested. This is also the only assertion in the package that shows the stabilisation doing what stabilisation is *for*, and it is the exact failure Chaudhry et al. report — the one §6.4.1 cites |
| The flow stabilisation | One GLS term with the test operator `(Re ρ̃ (ũ·∇)v + ∇q)` against the approximate momentum residual `R̃_m = ∇p̃ + Re ρ̃(ũ·∇)ũ − f̃ − s̃_u`, parameter `τ_m = [(2Re ρ̃‖ũ‖/h_K)² + (4η̃/h_K²)²]^{−1/2}`; plus a grad-div term `τ_c ∫ (d̂iv v)(d̂iv ũ) r`, `τ_c = Re ρ̃‖ũ‖h_K/2` | GLS carries momentum-SUPG and PSPG in one term with one parameter — less code than two terms, and the `∇q·∇p̃` piece it contains is precisely what makes the equal-order pair legal (NUM-03). At `Re = 6 × 10⁻⁴` the convective branch of `τ_m` is five orders below the viscous one and `τ_c ≈ 9 × 10⁻⁶` (§Design): both are numerically inert here and are assembled anyway, so the mode is not silently specific to this Reynolds number |
| The equal-order gate | `models.py:458` becomes conditional: `velocity_order <= pressure_order` is refused unless the resolved stabilisation model reports `permits_equal_order`. The refusal keeps naming inf-sup **and** now names the mode that would permit it | QR-12's shape. A user who asked for P1/P1 and got "not inf-sup stable" with no route forward will hard-code `order=1` somewhere worse |
| A third element order | `CoupledModel` gains `velocity_order: int | None = None`, defaulting to `order`. `order` continues to govern `φ` and `c`; `pressure_order` continues to govern `p` | The reference is `φ` P2, `c` P2, `u` P1, `p` P1, which the present two-order model cannot express. Defaulting to `order` means every existing caller — the ladder, `single_rung`, every Phase-0 test — is unchanged, and the new field is inert until a case asks for it |
| `numerics.elements` validation | `_resolve` keeps requiring `phi` and `c` to be one order and stops requiring `u` to join them; `u` and `p` are read independently and passed as `velocity_order` and `pressure_order` | The check at `case.py:1097` currently folds `u` into the `phi`/`c` equality, which is what makes the reference configuration unreachable from a case file at all. `φ` and `c` stay coupled because they share `order` on the model and nothing this phase needs separates them |
| Stabilisation parameters are evaluated at the **iterate**, not at the trial function | `τ_i`, `ν_K`, `τ_m` and `τ_c` are built from the solution `GridFunction`'s components, which NGSolve treats as data rather than as something to differentiate. `residual_form` gains `state: GridFunction | None = None` for that purpose | This is COMSOL's `nojac()` in one line and it needs no new Newton hook: NGSolve assembles the residual with the current iterate's `τ` automatically and omits `∂τ/∂u` from the linearisation. The converged fixed point is unchanged — at convergence the lagged parameter *is* the current one — while `max(0, ·)` and `1/‖∇c̃‖` stay out of the Jacobian, where they would wreck the damping policy NUM-16 tunes |
| Which Newton criterion carries the mode | The relative-update test on the undamped direction, already implemented and already normative in the NUM-16 NOTE | Relagging `τ` between iterations perturbs the residual by the size of the update, so a residual-only test can stall at the floor. The criterion that fixes warm starts fixes this for the same reason, which is why nothing new is needed here beyond saying so |
| Integration orders | `extra_order=4` on the streamline and flow terms, `extra_order=6` on the crosswind, through `Measures.volume`. The grad-div term is `singular=True` | NUM-15's numbers. `Measures` takes a quadrature **bonus**, not an absolute order (`measures.py:85-113`), so `extra_order=n` guarantees the assembled order is *at least* `n`; overshoot costs quadrature points, not correctness. NUM-15 gains a NOTE saying so. The grad-div integrand carries `u_r/r`, so NUM-07's minimum applies and the reference's order 2 for `spf` is superseded — which the §6.2 NOTE already declares in advance |
| Nothing else carries `1/r` | The streamline, crosswind and GLS integrands contain no `1/r`, because the approximate residual never forms the axisymmetric divergence | A consequence of the approximate-residual choice worth stating: the NUM-07 trap that returns NaN at order 2 does not arise for three of the four new terms. Stated so that a later change to a *full* residual knows it has to revisit this |
| **The stabilisation enters the NUM-24 current** | `I_i = 2π F z_i S_I [ ∫_Ω J̃_i·∇ψ r dr dz + S_i(c̃; ψ) ]`, where `S_i` is the species' stabilisation form evaluated with `ψ` as the test function | NUM-25's reaction flux *is* the assembled residual evaluated at `ψ`, and the assembled residual now contains `S_i`. Leave the indicator route alone and the two routes differ by exactly `S_i(ψ)` — which is the per-cent quantity the mode exists to measure, so NUM-26's `10⁻³` gate would fail on every stabilised solve for the one reason that is not a bug. §6.7 gains the NOTE |
| That difference is reported, not just absorbed | `2π F z_i S_I S_i(ψ)` per species goes into the solve summary and the FR-25 manifest as `stabilisation_current_A` | NUM-11's rationale — "SUPG biases the current quantity of interest" — becomes a number on every stabilised run, computed from the same assembled form rather than by differencing two solves. It is also exactly the input WP13's `Δ_stab` needs, available from one run instead of two |
| NUM-12's `Pe_h` | Evaluated on the **converged top rung**, per species, over the NUM-17 sampler; warns naming the species, the value and its `(r, z)` when `Pe_K ≥ 1`; records `max_cell_peclet` per species in the summary and the manifest. It runs in **every** mode, `none` included | NUM-12 says "the solver SHALL evaluate `Pe_h` on the assembled mesh" without qualification, and a diagnostic that only runs when the stabilisation is on is a diagnostic that never runs in production. There is no `∇φ̃` before the solve, so "on the assembled mesh" means on the assembled mesh's converged state. It reuses `FieldSampler`, which the gates build anyway |
| `Pe_h` is evaluated from `μ̃_i/D̃_i`, not from the printed formula | `Pe_K = ‖b̃_i‖h_K/(2D̃_i)`; the recorded value names the formula it used | §6.4.1 prints `Pe_h = ½\|z_i\|\|∇φ̃\|h̃`, which is the Einstein relation assumed. PHY-14 and VER-05 say `D_i/μ_i` drifts to 1.2–1.7 × kT/e between 0.15 M and 3 M, so the printed form **overestimates** the cell Péclet by that factor. Harmless in direction — the warning fires early — but a formula whose own knowledge base forbids it elsewhere should not be the one implemented. NUM-12 gains a NOTE |
| A gate, or a warning? | A **warning**. `Pe_K ≥ 1` does not abort | NUM-12 says warning, and it is a mesh-resolution statement rather than a wrong answer: §Design shows the NUM-30 rule puts `Pe_h` at `\|ζ̃\|/10` independently of concentration, so a mesh that violates it is under-resolved in a way NUM-34 and the NUM-26 route agreement already refuse on stronger grounds |
| Threading the mode through the ladder | `default_ladder` gains `stabilisation: str = "none"` and `velocity_order`/`pressure_order`, applied to **every** rung; `solve/state.ladder` passes them from the resolved case | NUM-18's NOTE forbids reading four *physics* switches from the case when the ladder is selected, because the ladder's path is fixed. Stabilisation is not one of the four and is not a physics switch: it is a property of the discretisation, so every rung must carry it or the top rung's warm start crosses two operators — which the VER-37 gate would refuse anyway, at hour twenty-two |
| No per-rung stabilisation schedule | The mode is uniform across the ladder. NUM-11's "SUPG on the coarse continuation mesh, off for the final solve" is expressed as **two cases** — a coarse-mesh case in `supg` and a fine-mesh case in `none` — which the sweep runner already dispatches | A ladder whose top rung changes discretisation makes that rung a cold solve in a different operator while presenting as a warm one, and the descriptor gate refuses exactly that crossing. Two cases say the same thing and each carries its own honest manifest |
| `numerics.stabilisation` gains `supg` | The `Literal` widens from `{none, reference}` to `{none, supg, reference}`. The schema id stays `nanopnp/case/v1`, under a rule written into §5.3.1 in this commit: **widening the accepted value set of an existing key is compatible and does not move the version; adding, removing, renaming or narrowing a key does** | WP7 froze the schema and WP11 established that a change to it is a version rather than an edit. That rule needs a boundary or the first new correction model moves the version too. Every document that validated against `v1` still validates, and the mode a run actually solved is in its manifest, so no `v1` artefact becomes ambiguous. **Author ruling, 13 September 2026: keep `supg`, widen the schema.** The freeze needed a boundary before the first new correction model reached it, and this is the cheapest place to draw it |
| `C_cw`, and where tuning constants live | `C_cw = 1.0`, `C_pspg` and the `ψ` cut-off are module constants in `physics/stabilisation.py`, each cited to the section it came from. **Not** case-file fields | They are numerics constants of a named mode, not fitted physical parameters: a case file that could retune the stabilisation would make "the `reference` mode" mean a different operator per run while the manifest recorded one word. If WP13's attribution needs a sensitivity study, it registers a second mode — which is what the registry is for. **Author ruling, 13 September 2026: module constants.** A C_cw swept from a case file would be a second source of truth for what `reference` means, and the deviation diff of §5.3.3 would have to learn that a non-default numerics constant is a deviation |
| The manifest's stabilisation group | Gains the mode's `parameters` and `provenance` mappings, exactly as a correction model contributes its own | §5.3.3 wants enough to reconstruct the run. "reference" alone does not distinguish `C_cw = 1` from `C_cw = 0.35`, and the group already has the shape (`manifest.py:245`) |
| No new dependency | Everything is NGSolve coefficient functions and `specialcf.mesh_size` | Nothing here needs a library, and CON-07 keeps the end-user path free of one |

## Design

### 1. What SUPG adds, exactly: the ratio is `Pe_h²`

With `ψ(q) = min(q, 1)` and `Pe_K = ‖b̃‖h_K/(2D̃) < 1`, the streamline parameter is

```
τ = (h_K / 2‖b̃‖) · Pe_K = h_K² / (4 D̃)
```

and the term it adds, `τ (b̃·∇c̃)(b̃·∇w)`, is an artificial diffusivity of `τ‖b̃‖²` along the
streamline. Against the physical `D̃`:

```
τ‖b̃‖² / D̃  =  ( ‖b̃‖ h_K / 2D̃ )²  =  Pe_K²
```

— exact, and independent of every material parameter. Now put NUM-30's resolution rule into it.
NUM-30 sets `h = λ_D/5`, and inside the double layer `‖∇φ̃‖ ≈ |ζ̃|/λ̃`, so

```
Pe_h = ½ |z_i| |ζ̃| λ̃ / (5 λ̃) = |z_i| |ζ̃| / 10
```

independently of concentration — which is where §6.4.1's `Pe_h = |z_i||ζ̃|/10` comes from, and which
this plan checks at both ends of the envelope: at 1 M, `λ_D = 0.304 nm`, `h̃ = 0.0304`,
`‖∇φ̃‖ = 19.7`, `Pe_h = 0.300`; at 0.05 M, `λ_D = 1.357 nm`, `h̃ = 0.1357`, `‖∇φ̃‖ = 4.42`,
`Pe_h = 0.300`. Therefore **the added artificial diffusion is `ζ̃²/100`**: 4 % at `ζ̃ = 2`, 9 % at
`ζ̃ = 3`, 16 % at `ζ̃ = 4`.

The closed form is the result; the `ζ̃` values above are **illustrative substitutions**, not the
reference pore's. Its pore-averaged `ζ̃` at 1 M is not in the knowledge base and is not needed to
plan the work — it comes out of this package's own stabilised run beside `stabilisation_current_A`,
and the end-of-phase report quotes the measured one (open question 3, closed).

That is inside the double layer. In the pore lumen the potential gradient is set by the bias over the
pore length — `0.2 V / 13 nm / V_T × a` gives `‖∇φ̃‖ ≈ 1.2` — and with `h̃ ≈ 0.05` that is
`Pe_h = 0.03` and an added diffusion of **0.09 %**. The stabilisation is therefore a
double-layer effect by three orders of magnitude, which is precisely why it reaches the current of a
*charged* pore at the per-cent level and leaves VER-17's uncharged pore nearly alone. Applying the
`μ̃_i/D̃_i` correction of PHY-14 (1.2–1.7 between 0.15 M and 3 M) scales every `Pe_h` above by
0.59–0.83 and every added diffusion by its square, 0.35–0.69.

These are the numbers WP13 will subtract. They are predictions, and the Tier-2 measurement of
`stabilisation_current_A` against the unstabilised current is what checks them.

> **Outcome — `Pe_K²` is confirmed, and the single-run number *is* the two-run bias.** Measured on
> the VER-11 benchmark pore (2 nm lumen, 13 nm membrane, 0.5 M, +50 mV, −0.05 C/m², `maxh` 5.0 nm and
> `wall_h` 0.4 nm, `reference`), where the diagnostic reports `max Pe_K = 0.775`:
> `stabilisation_current_A` sums to **−1.9059 × 10⁻¹¹ A, −8.14 % of the current**, and solving the
> same pore on the same mesh in `none` gives a current larger by **7.38 %**. The two agree to
> `1.55 × 10⁻³` of the current, so the NUM-26 NOTE's claim — the bias is reportable from a single run
> rather than from a difference of two — holds as arithmetic and not only as an intention. The reason
> it does is worth keeping: the *bare* `∫ J̃_i·∇ψ` integral is almost mode-independent
> (2.5327 × 10⁻¹⁰ A in `reference` against 2.5288 × 10⁻¹⁰ A in `none`, 0.15 % apart), so essentially
> the whole difference between the two currents lives in `S_i(ψ)`.
>
> 8 % is larger than the per-cent this section predicts, and consistently so: that estimate is for a
> mesh meeting NUM-30, where `Pe_h = 0.300` and the added diffusivity ratio `Pe_K²` is 0.09. This
> benchmark's mesh is deliberately coarser — it is sized for the solve and no finer — and at
> `Pe_K = 0.775` the ratio is 0.60. The closed form survives the test; only the substitution changes.
> VER-42 is where the number is watched under refinement.

### 2. Why the crosswind term is identically zero on the production mesh

The term is

```
Σ_K ν_K ∫_K (P_b ∇c̃_i) · ∇w  r dr dz ,   P_b = I − b̂⊗b̂ ,   b̂ = b̃_i/‖b̃_i‖
ν_K = max( 0 ,  C_cw h_K ‖R̃_i‖ / (2‖∇c̃_i‖)  −  D̃_i ) ,   C_cw = 1
```

with `P_b = 0` and `ν_K = 0` wherever `‖b̃_i‖` falls below a floor — there is no crosswind without a
wind. In production `s̃_i = 0`, so `R̃_i = b̃_i·∇c̃_i` exactly, and Cauchy–Schwarz gives
`‖R̃_i‖ ≤ ‖b̃_i‖‖∇c̃_i‖`. Substituting:

```
ν_K  ≤  max( 0 , C_cw h_K ‖b̃_i‖ / 2  −  D̃_i )  =  D̃_i · max( 0 , C_cw Pe_K − 1 )
```

so `ν_K ≡ 0` whenever `C_cw Pe_K ≤ 1`. With `C_cw = 1` and `Pe_h = |ζ̃|/10` from §1, the crosswind
term contributes **nothing** anywhere on a mesh built to NUM-30, and it activates on exactly the
elements where NUM-12's warning fires. Three consequences, all of them load-bearing:

1. The order-6 quadrature NUM-15 demands is paid only on elements where the term is nonzero.
2. "The crosswind contributed zero" is a measurement this package reports, not an assumption — and
   it is an honest part of WP13's attribution, because the reference's crosswind was presumably
   equally inert on *its* mesh, whose minimum quality was 0.6378 at ~1.2 × 10⁵ triangles.
3. The term is untestable on a production-resolution mesh, which is why the Tier-2 case for it is a
   deliberately coarse mesh at `Pe_K > 1` — the regime where plain Galerkin produces the negative
   concentrations Chaudhry et al. report and the NUM-17 positivity gate already detects.

The upper bound also says the term can never add more diffusion than brings the effective cell
Péclet to `1/C_cw`, so it cannot run away: `ν_K` is bounded by `D̃_i(Pe_K − 1)` and vanishes
continuously at `Pe_K = 1`. It is not differentiable there, which is the second reason the parameter
is evaluated at the iterate rather than differentiated through Newton.

### 3. Consistency, and the MMS rate this package predicts

On the exact solution the approximate residual is not zero:

```
R̃_i(c) = b̃_i·∇c − s̃_i = ∇·(D̃∇c) + (axis terms) = O(1)
```

because the diffusive second derivative is exactly what "Approximate residual" drops. The crosswind
term is unaffected — §2 shows `ν_K → 0` as `h → 0` for any bounded residual, so it switches off
before it can pollute a rate. The streamline term is not: its consistency error in the weak residual
is `τ ‖b̃‖ ‖R̃‖ ‖∇w‖ = (h²/4D̃)‖b̃‖·O(1)·‖∇w‖`, an `O(h²)` perturbation of a bilinear form whose
coercivity is `D̃‖∇w‖²`. The added error is therefore `O(h²)` in `H¹` — the same order as the P2
Galerkin error — and `O(h²)` in `L²`, where P2 would otherwise give `O(h³)`.

**Prediction: the stabilised MMS rate is 2, not VER-18's 3.** A measured rate near 2 confirms the
term; a rate near 3 means the streamline term is not being assembled at all (a real risk, given §2's
finding that the *other* term is legitimately zero); a rate below 2 is a defect — most likely the
manufactured source `s̃_i` left out of `R̃_i`, which is the single easiest mistake to make here and
the reason `residual_form`'s `sources` mapping must reach the stabilisation term.

The second Tier-2 assertion is the other side of the same statement: the stabilised and unstabilised
*currents* must approach each other under refinement, at `O(h²)` by §1's `Pe_h²` ratio. Two
independent routes to the same conclusion, and the one that matters for §7.4 is the second, because
it is the one that says the two discretisations are discretisations of the same PDE.

> **Outcome — the prediction is right about the term it is about, and the section attributes it to
> the wrong mode.** `supg` — the streamline term alone — converges at **2.012 and 2.040** on
> `maxh` 0.4/0.2/0.1 nm, against `none`'s 3.55 and 3.11 on the identical meshes. NUM-14's prediction
> is confirmed to within 2 %. But this section, and the verification table below, asked for that rate
> from **`reference`**, which also assembles the flow pair; measured there it is **0.984**. The gated
> rate therefore moved to `supg`, which is the mode that isolates the term the prediction is about,
> and `reference`'s is measured and recorded (§4's Outcome carries the attribution). The project's
> own rule decided it: an analytic test that localises the error to a single term beats a whole-model
> comparison that localises nothing.
>
> The section's falsification clauses need one correction each. "A rate near 3 means the streamline
> term is not being assembled at all" — true, and the *other* cause of a rate near 3 is the one this
> section names as producing a rate **below** 2: the manufactured source left out of `R̃_i`. This
> problem is diffusion-dominated (`max Pe_K ≤ 0.084`), so `s̃_i` is the dominant part of `R̃_i` and
> withholding it does not corrupt the residual, it erases it — the rate rose to **2.907**, and the
> floor, which deliberately has no ceiling, passed it. The deliberate-mistake test is therefore
> asserted on the term's *footprint* against the unstabilised error on the same mesh, which separates
> by a factor of 24 to 212 and does not depend on which way the rate moves. Recorded in
> `.knowledge/06` §4.3.4; VER-42 gains the clause.

### 4. The flow terms at `Re = 6 × 10⁻⁴`

`NondimensionalCoefficients.reynolds` is `ρ₀ ε V_T²/η₀²`, length-independent, **6 × 10⁻⁴**
(`coefficients.py:234`). Put that into the Shakib parameter with `h̃ ≈ 0.03` and `‖ũ‖ ~ 1`:

```
(2 Re ρ̃ ‖ũ‖ / h_K)  =  2 · 6e−4 / 0.03   =  4.0e−2
(4 η̃ / h_K²)        =  4 / 9.0e−4        =  4.4e+3
τ_m = [ (4.0e−2)² + (4.4e+3)² ]^(−1/2)   =  2.25e−4  =  h_K²/(4η̃) to five figures
```

The convective branch is **five orders** below the viscous one: at this Reynolds number the flow
stabilisation is pure PSPG, and the `τ_m ∫∇q·∇p̃` piece inside the GLS operator is the whole of what
makes the equal-order pair legal. The grad-div parameter is `τ_c = Re ρ̃‖ũ‖h_K/2 = 9 × 10⁻⁶`,
numerically inert by the same margin. Both are assembled regardless, so that a later case at a
Reynolds number this project does not yet reach is not silently running a Stokes-only stabilisation.

The momentum residual is approximate on the same rule — `R̃_m = ∇p̃ + Re ρ̃(ũ·∇)ũ − f̃ − s̃_u`, the
viscous second derivative dropped — so it carries no `1/r`. The grad-div term does, through
`d̂iv u = ∂_r u_r + u_r/r + ∂_z u_z` (NUM-05), and takes `singular=True`: the reference assembled its
flow stabilisation at integration order 2, and the §6.2 NOTE already declares NUM-07 to govern
irrespective of that.

> **Outcome — the two GLS rows do not share an orientation.** The section above reads as though one
> signed GLS term serves both rows. It does not. The velocity row is the coercive orientation and
> takes a `+`; the continuity row is written `−∫ q ρ̃ d̂iv ũ`, which is *minus* the orientation in
> which `+τ_m ∫∇q·∇p̃` is the stabilising pressure block, so the pressure-test piece takes a `−`.
> One signed term for both stabilises one row and destabilises the other, giving the saddle
> structure `[[A, B], [Bᵀ, −C]]` rather than `[[A, B], [Bᵀ, +C]]`. The streamline and crosswind
> terms *do* share an orientation with each other — both `−`, the sign of the Galerkin diffusion
> they augment in this flux-form residual — which is what makes the flow pair the exception worth
> writing down.

> **Outcome — the flow terms are not asymptotically inert on a stable pair; they cost an order and
> 20× the time.** The decisions table justifies assembling them on a Taylor–Hood pair with "the flow
> terms are consistent (§Design), so on a stable pair they are asymptotically inert rather than
> wrong". The first clause contradicts this section, which says in its own third paragraph that the
> momentum residual drops the viscous second derivative; the rest follows from that and is wrong.
> Measured on VER-18's problem, where `max Pe_K ≤ 0.084` and the crosswind viscosity is therefore
> identically zero (sampled, both species), so that `reference` minus `supg` **is** the flow pair:
>
> | | `c_Na+` rate | velocity L² at `maxh` 0.4 nm | Newton | wall clock at 0.4 / 0.2 nm |
> |---|---|---|---|---|
> | `none` | 3.55, 3.11 | 2.7567e−04 | 5 | 0.8 s · 4.7 s |
> | `supg` | 2.01, 2.04 | 2.7617e−04 | 5 | 7.2 s · 25.1 s |
> | `reference` | 0.98, and 0.70 for `Cl−` | 3.4483e−02 | 31 | 126 s · 436 s |
>
> PSPG's consistency error enters the continuity equation weighted by `τ_m ≈ h̃²/4η̃` against a test
> *gradient*, which is `O(h)` and not `O(h²)`. The velocity error, which no transport term can reach
> — `supg` moves it by 0.2 % — rises by a factor of 125, which is what makes this an attribution
> rather than an inference.
>
> **The decision itself stands.** NUM-14's table records the flow row's equation residual as *not
> recorded in the report*, so the approximation is this project's rather than the reference's; and
> RSK-18 records that the reference ran its flow stabilisation on a **P1/P1** pair, where the term is
> what makes the pair admissible at all. No configuration the reference itself ran loses an order.
> Making `reference` drop the flow terms on a stable pair would make the mode's meaning depend on the
> element pair while the manifest recorded one word, which is worse than the cost. What changes is
> what is claimed: the middle rung of the §7.4 attribution ladder is first-order accurate, and the
> `Δ_stab` measured there is the flow pair's rather than the transport term's. Recorded in
> `.knowledge/06` §4.3.3; NUM-14 gains the bullet and VER-42 the clause.

### 5. The current identity, written out

NUM-25's variational reaction flux is *the assembled residual* evaluated against a test function
equal to 1 on one electrode. Once the residual contains `S_i`, so does the reaction flux. NUM-24's
indicator form does not, unless it is told to. The NUM-26 NOTE already establishes why the two are
the same integral — `ψ` differs from the boundary indicator by a legitimate test function of the
converged residual — and that argument is what forces the amendment: the residual the argument refers
to is the one actually assembled. So

```
I_i = 2π F z_i S_I [ ∫_Ω J̃_i·∇ψ  r dr dz  +  S_i(c̃; ψ) ]
```

and `NUM-26`'s `1 × 10⁻³` tolerance is unchanged, because both routes again evaluate one integral.
Without the second term the two routes would differ by `S_i(ψ)` — from §1, a per-cent quantity — and
the Tier-2 route-agreement check would fail on every stabilised solve for the one reason that is not
a defect. The same number, `2π F z_i S_I S_i(ψ)`, is reported per species as
`stabilisation_current_A`: NUM-11's "SUPG biases the current quantity of interest", made a number
from one run.

### 6. `h_K` is `sqrt(2|K|)` — measured

`ngsolve.specialcf.mesh_size` on a 2D triangular element returns `sqrt(2|K|)`, verified elementwise
on a 14-element unstructured mesh of the unit square to a maximum relative deviation of
2.4 × 10⁻¹⁵. For the equilateral triangle of side `a` that is `a√(√3/2) = 0.9306 a`, so the measure
sits 7 % below the edge length — inside the tuning constant, and constant across element shapes to
within the shape factor. This goes into `.knowledge/06-numerics-fem.md` §2 as **[tested]**, because
every `τ` in this package is defined against it and a silent change to NGSolve's convention would
retune the whole mode with no diagnostic.

> **Outcome — `specialcf.mesh_size` also evaluates pointwise, which is what makes the NUM-12
> diagnostic possible.** Verified before it was relied on: `mesh(x, y)` returns the containing
> element's `h_K` at a located point, not only inside a quadrature loop. The `Pe_h` diagnostic is
> therefore a sampler over the P2 nodal set rather than an element loop, and reuses `FieldSampler`
> unchanged as the plan's work-items table assumed.

### 7. The zero-wind linearisation, found in implementation

> **Outcome — a term whose value is exactly zero can still make the Jacobian singular.** The plan
> has no section on this because nothing predicted it. `reference` aborted on the first
> linearisation of ladder stage 4 with `UmfpackInverse: Numeric factorization failed`, naming no
> form and no term. The cause is that NGSolve evaluates `d/du ‖g‖ = (g·∂g/∂u)/‖g‖` numerically and
> never folds away the structural zero that `∂g/∂u` is for a lagged grid function: at `g = 0`
> exactly the entry is `0/0`, and the `NaN` survives multiplication by that zero. `Assemble` is
> clean; only `AssembleLinearization` carries it, which is why
> `test_num14_every_term_vanishes_at_a_state_with_no_wind` — which asserts the same state through
> `Apply` — passes in every mode and caught none of it.
>
> `b̃_i = z_i μ̃_i ∇φ̃ + D̃_i β̃_i − Pe ũ` is **exactly** zero at every rung below stage 4 (zero bias,
> zero charge, no flow), so this is the ordinary path rather than a corner of the envelope. The
> guard is `MAGNITUDE_FLOOR = WIND_FLOOR² = 1e−60` inside every root `_magnitude` takes: the
> perturbation to a magnitude of order 1 is `5e−61`, and the derivative becomes `0/1e−30 = 0`
> exactly. The scalar sibling `|s| = IfPos(s, s, −s)` was already immune, because `IfPos`
> differentiates branchwise with no division — the module had the hazard right for scalars and
> missed it for vectors.
>
> Gated by `test_ver41_the_linearisation_is_finite_at_the_zero_wind_cold_state`, parametrised over
> all three modes and asserted on the **assembled Jacobian entries**: a residual-norm check reports
> zero, not `NaN`. VER-41 gains the clause and NUM-14 a NOTE requiring the floor.

## Work items

| File | What it delivers | Identifiers |
|---|---|---|
| `src/nanopnp/physics/stabilisation.py` (new) | `StabilisationModel` protocol (`name`, `parameters`, `provenance`, `permits_equal_order`, `transport_term`, `flow_term`, `indicator_term`); `NoStabilisation`, `StreamlineStabilisation`, `ReferenceStabilisation`; `_REGISTRY` / `register` / `registered_stabilisations` / `create`; `element_size()`; `advective_velocity()`; `cell_peclet()`; the tuning constants with their citations | NUM-11, NUM-14, NUM-15, PHY-22 |
| `src/nanopnp/physics/models.py` | `SUPPORTED_STABILISATIONS` from the registry; `velocity_order` field and its use in `space()`; the conditional inf-sup gate; `residual_form(..., state=)` adding the transport and flow terms; `provenance` gains the element orders and the mode's parameters | NUM-03, NUM-13, NUM-14 |
| `src/nanopnp/solve/gates.py` | `PecletDiagnostic` — a warning, not a gate; reuses `FieldSampler`; reports the species, the value, its `(r, z)` and the element count above 1 | NUM-12, QR-12 |
| `src/nanopnp/solve/continuation.py` | `default_ladder(..., stabilisation=, velocity_order=, pressure_order=)`, threaded onto every rung's `_coupled` model; `LadderResult.summary()` gains `max_cell_peclet` and `stabilisation_current_A` | NUM-12, NUM-13, NUM-18 |
| `src/nanopnp/solve/state.py` | `ladder()` passes the mode and the two orders from the resolved case; the descriptor's field record already carries per-field order and needs only the velocity order to be genuinely independent | NUM-03, VER-34, VER-37 |
| `src/nanopnp/solve/stage.py` | Runs the `Pe_h` diagnostic on the converged top rung; carries its numbers and `stabilisation_current_A` into the artefact summary | NUM-12, FR-25 |
| `src/nanopnp/io/case.py` | `NumericsSpec.stabilisation` widened to `{none, supg, reference}`; `_resolve`'s element check stops folding `u` into the `phi`/`c` equality; `_model_options` gains `velocity_order` | IF-03, NUM-03, §5.3.1 |
| `src/nanopnp/io/defaults.py` | Nothing moves: `numerics.stabilisation` is already a diffable path with validated default `none`, so `supg` and `reference` register as deviations for free | FR-25, §5.3.3 |
| `src/nanopnp/io/manifest.py` | `stabilisation_group` gains the mode's `parameters` and `provenance`, and the per-species `stabilisation_current_A` and `max_cell_peclet` | FR-25, NUM-13, §5.3.3 |
| `src/nanopnp/post/qoi.py` | `indicator_currents` adds `S_i(c̃; ψ)`; `stabilisation_currents()` reports the contribution per species; `RouteAgreement` unchanged | NUM-24, NUM-26, QR-04 |
| `.knowledge/06-numerics-fem.md` | §2: `specialcf.mesh_size = sqrt(2|K|)` **[tested]**. §4: the mode as built, the `Pe_h²` ratio, the crosswind's `C_cw Pe_K ≤ 1` switch-off, and the `Re = 6 × 10⁻⁴` flow arithmetic **[verified]** | — |
| `SPECIFICATION.md` | The seven amendments below, in this commit | NUM-03, NUM-12, NUM-14, NUM-15, NUM-24, NUM-26, §5.3.1, §7.2, §7.3 |

> **Outcome — five rows landed somewhere other than where this table put them.**
>
> - **No `SUPPORTED_STABILISATIONS`.** A frozen tuple beside a live registry is a second record of
>   one fact, and the two can disagree the moment a mode is registered. `physics/models.py` queries
>   `registered_stabilisations()` directly, and `equal_order_stabilisations()` is the derived
>   membership the inf-sup message needs.
> - **The inf-sup condition is one predicate, `physics.models.inf_sup_problem`, with two callers.**
>   The table gives the gate to `models.py` and the widened literal to `io/case.py`, which would
>   have put the same condition in both — and the one that mattered would be whichever ran first.
>   `io/case.py` calls the predicate and wraps its message in the case file's own `elements`
>   vocabulary.
> - **`stabilisation_current_A` is in `post/qoi.py`, not on `LadderResult`.** It is a
>   post-processing integral over the fluid, evaluated through
>   `CoupledModel.transport_states` — the same states the residual was assembled from, which is
>   what keeps NUM-26 an identity rather than two constructions that happen to agree. `LadderResult`
>   carries the `Pe_h` measurement and the mode's parameters; the current lives with the other
>   currents.
> - **`solve/stage.py` is unchanged.** The diagnostic runs in `run_ladder`, because every path to a
>   converged solution goes through it and no caller can then skip it, and the stage already splats
>   `result.summary()`. A different file gained the one line the table expected here:
>   `post/stage.py`, whose `always` set had to learn `stabilisation_currents_A` is provenance rather
>   than a selectable quantity.
> - **`solve/state.py` gained three `SPACE_KEYS` entries, not zero.** `model.elements`,
>   `model.stabilisation_parameters` and `model.stabilisation_provenance`: the mode *name* alone
>   would let a warm start cross between `reference` at `C_cw = 1` and `reference` at
>   `C_cw = 0.35`, which are different operators, and `model.elements` restates the three orders in
>   the case file's vocabulary on the same side of the gate so the two records cannot disagree.
>   `RungResult` also gained `stabilisation`, so the per-rung record says which mode each rung was
>   assembled in rather than only the top one.

## Verification

| Test file | Tier | Identifiers | What it asserts |
|---|---|---|---|
| `tests/tier1/test_stabilisation.py` (new) | 1 | VER-41, NUM-11, NUM-12, NUM-14, NUM-15, QR-12 | `specialcf.mesh_size` equals `sqrt(2\|K\|)` elementwise to better than `10⁻¹²` on an unstructured mesh, so the `τ` definitions are pinned to a measured convention rather than an assumed one; the registry lists exactly `none`, `supg`, `reference` and `create` refuses an unknown name listing the three; `NoStabilisation` returns `None` from both term builders and the residual it produces is *identical* to the unstabilised one, asserted on the assembled vector rather than on the mode string; `τ_i` equals `h²/(4D̃)` wherever `Pe_K < 1` and `h/(2‖b̃‖)` wherever `Pe_K > 1`, at the crossover to round-off; `ν_K` is exactly zero on every element with `C_cw Pe_K ≤ 1` and positive on one constructed above it, bounded by `D̃(C_cw Pe_K − 1)`; `P_b b̃ = 0` and `P_b` is idempotent; the crosswind and streamline terms are requested at `extra_order` 6 and 4 and the grad-div term at `singular=True`, asserted on the `Measures` call rather than on the number; `permits_equal_order` is true for `reference` alone; an equal-order pair is refused in `none` and in `supg` naming inf-sup *and* the mode that would permit it, and accepted in `reference`; `velocity_order` defaults to `order` so every pre-existing model is unchanged; `PecletDiagnostic` warns naming the species, the value and its `(r, z)` on a constructed field with `Pe_K > 1`, is silent below it, and runs in `none` |
| `tests/tier1/test_case_schema.py` (extended) | 1 | VER-09, IF-03, NUM-03 | `stabilisation: supg` validates and `stabilisation: streamline` is refused naming the three modes; `elements: {phi: P2, c: P2, u: P1, p: P1}` resolves to `order=2, velocity_order=1, pressure_order=1`; `{phi: P2, c: P1, ...}` is still refused naming the two fields that must agree; the widened literal leaves the schema id at `nanopnp/case/v1` and every existing fixture round-trips to identical provenance |
| `tests/tier1/test_physics_models.py` (extended) | 1 | NUM-03, NUM-13, FR-25 | The conditional inf-sup gate replaces the unconditional one; `provenance` carries `stabilisation`, the three element orders and the mode's parameters, and two models differing only in `C_cw` do not share a provenance digest |
| `tests/tier1/test_manifest.py` (extended) | 1 | FR-25, NUM-13, §5.3.3 | The stabilisation group carries the mode, its parameters and its provenance; a run in `supg` or `reference` appears under Deviations without the manifest writer being told about the new value; `stabilisation_current_A` and `max_cell_peclet` are present on a stabilised run and recorded as not run on an unstabilised one rather than defaulted to zero |
| `tests/tier2/test_stabilised_mode.py` (new) | 2 | VER-42, NUM-14, NUM-15, VER-18 | On the VER-18 manufactured solution at the three existing refinement levels, the `reference` mode converges at a **measured** rate, reported rather than asserted exact, and gated only from below at 1.8 — §Design predicts 2 and explains why not 3; the same run with the manufactured source deliberately withheld from `R̃_i` converges at a visibly worse rate, so the wiring mistake the prediction warns about is caught by a test rather than by a puzzled afternoon; the `none` mode on the same meshes still gives VER-18's 3, unchanged; the stabilised and unstabilised **currents** on the WP10 reference pore approach each other under refinement at the `O(h²)` §1 predicts, with the measured ratio reported |
| `tests/tier2/test_stabilised_mode.py` (same file) | 2 | VER-42, NUM-12, NUM-17 | On a mesh coarse enough that `Pe_K > 1` in the double layer, plain Galerkin trips the NUM-17 positivity gate and `reference` converges without tripping it — the failure Chaudhry et al. report and §6.4.1 cites; on that mesh the crosswind is active on a reported non-zero fraction of elements and the `Pe_h` warning names the same elements; on the production-resolution mesh the crosswind contributes exactly zero, asserted on the assembled term and not inferred from the current |
| `tests/tier2/test_current_routes.py` (extended) | 2 | NUM-24, NUM-26, QR-04, VER-11 | With `reference` active the NUM-24 and NUM-25 routes agree to better than NUM-26's `1 × 10⁻³`, which they do only because the indicator route carries `S_i(ψ)`; with that term deliberately removed they disagree by the reported `stabilisation_current_A`, so the test measures the identity rather than asserting it; `stabilisation_current_A` is of the per-cent order §1 predicts and is zero in `none` |
| `tests/tier2/test_ladder.py` (extended) | 2 | NUM-13, NUM-18 | A ladder run in `reference` reports that mode from every rung, not only the top one; a warm start across the two modes is refused by the existing VER-37 descriptor gate naming `stabilisation` and both values |
| `tests/tier2/test_stabilised_mode.py` (same file, `slow`) | 2 | VER-42, NUM-03 | The equal-order P1/P1 pair converges in `reference` on the reference pore and produces a velocity field agreeing with the Taylor–Hood solve to a reported relative L², and the same pair in `none` is refused before assembly. Recorded, not gated: it is the third rung of WP13's attribution ladder and its number is the input, not the verdict |

> **Outcome — every prediction §Design made about the coarse mesh held, and the numbers are
> these.** `tests/tier2/test_stabilised_mode.py` runs the pore of the route-agreement file at
> `maxh` 5 nm, 0.5 M, +50 mV.
>
> | Claim | Configuration | Measured |
> |---|---|---|
> | Plain Galerkin loses positivity | `wall_h` 1.0 nm, −0.12 C/m², 313 elements, `max Pe_K = 4.712` | `none` aborts on rung `4-ramp-charge-1.00` with `Na+ = −72.9` at `(r, z) = (1.001, −4.376)` nm; `reference` converges in 126 Newton iterations over the ten classical rungs |
> | Crosswind active, and only above unit Péclet | the same mesh | active at 125 of 1 344 fluid samples for `Na+` and 123 for `Cl−`, peak `ν_K` 3.71 and 5.61; **zero** samples active at `Pe_K ≤ 1` |
> | Crosswind identically zero when resolved | `wall_h` 0.2 nm, −0.05 C/m², 1 491 elements, `max Pe_K = 0.457` | the assembled crosswind linear form has `max |entry| = 0.000e+00` for both species |
> | The two modes' currents converge together | `wall_h` 0.8 / 0.4 / 0.2 nm, −0.05 C/m² | `\|I_ref − I_none\|/\|I_none\|` = 2.00 × 10⁻¹, 7.38 × 10⁻², 1.99 × 10⁻²; rates **1.441** and **1.889** |
> | Equal order, recorded not gated | `wall_h` 0.4 nm, P1/P1 in `reference`, stage 6 | velocity 6.86 × 10⁻² relative *r*-weighted L² from Taylor–Hood, 34 Newton iterations either way |
>
> Two things the plan did not say. The current-difference rate **approaches 2 from below** — 1.441
> on the coarse interval — so the plan's own "assert the ratio falls, report the rate" was the right
> call and a fixed floor of 1.8 would have failed the first interval for no defect; the gate is
> therefore the monotone fall plus 1.5 on the finest interval. And the crosswind containment is
> asserted **sample by sample** rather than as a comparison of fractions, which is stronger than the
> plan's wording and is what §4.3 of the knowledge base actually licenses.
>
> The charge had to be raised from the route file's −0.05 C/m² to −0.12 C/m² to reach the regime at
> all. Below about −0.10 C/m² on the coarse mesh both modes converge and the comparison measures
> nothing; well above it — a 1.5 nm pore at 0.05 M and −0.30 C/m², `wall_h` 1.0 nm — *both* modes lose
> positivity, `reference` merely reaching −0.385 where `none` reaches −0.826. The claim "the
> stabilised mode does not trip the gate" is therefore true of a band and not of the whole
> coarse-mesh regime, which is what the recorded configuration pins down.

> **Outcome — the warm-start refusal is a Tier 1 test, not a Tier 2 one.** The row above puts both
> ladder assertions in `tests/tier2/test_ladder.py`, on the reasoning that a mode crossing is
> something a ladder does. It is not: `load_initial` gates the descriptor *before* any form is
> assembled, so the refusal needs a stored `state.npz` and a case document and no solve at all. It
> landed in `tests/tier1/test_warm_start_descriptor.py`, beside the `neighbour` fixture and the other
> five `SPACE_KEYS` crossings it is a sibling of, where it runs in the same seconds they do and reads
> as one more row of the same table rather than as an aside in a benchmark. Tier 2's
> `test_ladder.py` keeps the per-rung mode record, which does need the climb. The identifiers are
> unchanged; only the tier directory is.

**Tolerance provenance.** The MMS floor of 1.8 is `2 − 0.2`, the margin `tests/tier2/test_mms.py`
already allows on its rate of 3, unchanged. `1 × 10⁻³` is NUM-26's declared route tolerance,
unchanged since WP5. The `O(h²)` current convergence is not gated on a constant: the *ratio* between
successive levels is asserted to fall, and the measured rate is reported, because §1 predicts the
coefficient and not the constant in front of it. Nothing here tightens an existing tolerance.

Two constants the plan did not foresee, both floors with their measured headroom recorded beside
them rather than thresholds fitted to a number. `WITHHELD_FOOTPRINT_FACTOR = 5` gates the collapse of
the stabilisation's footprint when the manufactured source is withheld; measured 24 to 212, so the
floor carries five times its own margin. `FLOW_PAIR_VELOCITY_FACTOR = 10` gates how much of the
velocity error the flow pair owns in the `reference` measurement; measured 125. Each is a floor
because the quantity it bounds is a *separation* that the implementation should widen, not meet.

## Out of scope

- **The Tier-3 comparison itself.** WP13 owns the goldens, the probe grid and the attribution
  ladder. This package produces the configurations that ladder compares and the number `Δ_stab` is
  made of; it compares nothing against COMSOL.
- **A full (second-derivative) residual.** `Operator("hesse")` would restore consistency and VER-18's
  rate 3, at the cost of no longer matching NUM-14's "Approximate residual". It is a second
  registered mode when somebody wants it, and the registry is why that costs no restructuring.
- **Bit-for-bit agreement with COMSOL's `tds.streamline`, `tds.crosswind`, `spf.streamlinens` and
  `spf.crosswindns`.** Not exported, therefore not reachable; `.knowledge/09` §F names this an
  irreducible systematic bounded only by mesh refinement, and §Design's `O(h²)` convergence of the
  two currents is how this package bounds it.
- **Isotropic (inconsistent) diffusion and pseudo-time stepping.** The reference had the first off
  and gated the second to zero; implementing either would be a deviation from the validated model
  wearing the word "reference".
- **Stabilising the Poisson equation.** It carries no advective operator and the reference's
  Electrostatics interface has no stabilisation section.
- **A direction-dependent `h_b`.** Needs per-element basis gradients NGSolve does not expose as a
  coefficient function; the isotropic measure and the tuning constant absorb it.
- **Per-rung and per-mesh stabilisation schedules**, and any automatic selection of the mode from a
  measured `Pe_h`. The mode is declared in the case file and recorded in the manifest; a solver that
  chose its own discretisation would make two runs of one case file two different runs.
- **Calibrating `C_cw` against the reference.** There is nothing to calibrate against.

## Open questions

All three are closed. They were put to the author on 13 September 2026, before implementation
started, and the rulings are folded into the Decisions table above.

| # | Question | Ruling |
|---|---|---|
| 1 | Should `C_cw`, `τ_m`'s `ψ` cut-off and the PSPG coefficient be case-file fields? | **Closed, 13 September 2026 — module constants.** They are numerics constants of a named mode, not fitted physical parameters, and a case that could retune them would make `reference` mean a different operator per run while the manifest recorded one word. A variant is a second registered entry, which is what the registry is for; a `C_cw` sweep in WP13 is therefore a sweep over mode names, not over a number |
| 2 | Is `supg` worth widening `numerics.stabilisation`, and with it the §5.3.1 schema-widening rule? | **Closed, 13 September 2026 — keep `supg`, widen the schema.** It discharges the unfinished half of NUM-11 and gives WP13's attribution a fourth rung separating the transport streamline term from the crosswind and the flow pair. The freeze needed a compatibility boundary before the first new correction model reached it, and a value-set widening — under which every `v1` document that validated still validates — is the cheapest place to draw one |
| 3 | Which `ζ̃` should §Design's `ζ̃²/100` headline quote? | **Closed, 13 September 2026 — `ζ̃ = 3` stands as illustrative.** The closed form is the deliverable and the value is a substitution. The measured pore-averaged `ζ̃` at 1 M comes out of this package's own stabilised run alongside `stabilisation_current_A`, and the end-of-phase report quotes that one. Nothing here blocks |

## Specification amendments

Made in the same commit, each because the plan would otherwise diverge from the specification rather
than implement it.

| # | Where | What |
|---|---|---|
| 1 | §5.3.1, `numerics.stabilisation` | Value set widened to `none \| supg \| reference`, with a NOTE stating the compatibility rule: **widening the accepted value set of an existing key does not move the schema version; adding, removing, renaming or narrowing a key does.** |
| 2 | §5.3.1, `numerics.elements` | NOTE: `phi` and `c` carry one order; `u` is independent of them and `p` independent of both; an order for `u` at or below `p`'s requires a stabilisation mode supplying the flow stabilisation of §6.4.2 (NUM-03) |
| 3 | NUM-12 | NOTE: the printed `Pe_h = ½\|z_i\|\|∇φ̃\|h̃` assumes the Einstein relation, which PHY-14 and VER-05 forbid at finite concentration; the implementation evaluates `‖b̃_i‖h_K/(2D̃_i)` and records which formula produced the number. The printed form overestimates by `D_i/(μ_i V_T) ∈ [1.2, 1.7]`, so it errs towards warning early |
| 4 | NUM-14 | NOTE fixing the three things the reference's setting names do not: what "Approximate residual" is taken to mean (every second derivative of a trial field dropped), that the crosswind is a Do Carmo–Galeão-*type* term because COMSOL's own is not exported, and that the "conservative form" row costs nothing because §6.2's Nernst–Planck weak form is already the divergence form |
| 5 | NUM-15 | NOTE: "at integration order *n*" is realised as a lower bound, because the quadrature order reaching the backend is a bonus over an integrand-dependent estimate rather than an absolute; overshoot costs quadrature points and not correctness |
| 6 | NUM-24, NUM-26, §5.3.3 | NOTE: under a stabilisation mode the indicator functional of NUM-24 carries the stabilisation form evaluated with `ψ` as its test function, because NUM-25's reaction flux is the assembled residual and the assembled residual contains it; NUM-26's tolerance is unchanged, and the difference between the two terms is reported as the stabilisation's contribution to the current (NUM-11). §5.3.3's Stabilisation row is extended to carry that contribution, the mode's tuning parameters and the largest cell Péclet number per species |
| 7 | §7.2, §7.3, Appendix A | **VER-41** (Tier 1, the stabilisation terms, the registry, the element-pair gate and the `Pe_h` diagnostic) and **VER-42** (Tier 2, the stabilised mode: the measured MMS rate, the coarse-mesh positivity result, the crosswind's activation set, the two currents converging, and the equal-order pair). QR-12 gains VER-41 and QR-04 gains VER-42 in the traceability matrix; no requirement moves out of "none yet", so the coverage count is unchanged |
