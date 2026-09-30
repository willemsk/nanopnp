# WP26 — The physics-model interface (FR-20)

**Status: planned, not started.** 30 September 2026. The first package of Phase 3. It inherits the
six registered models of PHY-21 (`physics/models.py`), the NUM-18 ladder (`solve/continuation.py`),
the frozen case schema v2 (§8.2.2 B3), the stage-7 consumer path (WP9) and the stage-10 key of
§5.3.2. Nothing in it depends on Phase 2's verdict.

This plan belongs to [Phase 3](phase-3-charge-pipeline.md). `SPECIFICATION.md` governs; identifiers
here are pointers into it. The spec amendments this package needs are made in this plan's commit:
the PHY-21 NOTE on the electrostatic models as case-file models, the §5.3.1 NOTE on a solid without
a permittivity, the §5.3.1 NOTE on `outputs:`, and the §5.4.3 NOTE on what a model declares.

## Execution brief

**Scope.** Make the §5.4.3 interface the only route to a model, so one added as one class runs from
a case file to stage 12 with no other edit (FR-20; QR-14, second half). Eleven modules outside
`physics/` branch on `COUPLED_MODELS`, a model name or `isinstance` today (*Design* §1). The survey
also found that **no electrostatic model can run from a case file**: every shipped mesh has a
membrane, the mesh gate demands its permittivity, and resolve refuses solids for all three. `pb`
never receives its Debye length either. WP26 makes `poisson` the VAL-06 target and lets `pb` and
`pb-linear` run on a solid-free mesh. PHY-24 is untouched.

**Read first.** §5.4.3, PHY-21 and their NOTEs; §5.3.1 NOTEs on `outputs:` and on a solid without a
permittivity; §6.5 NOTE; `physics/models.py`.

### Decisions

| # | Decision | Choice | Why/source |
|---|---|---|---|
| D1 | Unit of declaration | `register_model(name, builder, declaration)`. A frozen `ModelDeclaration` is per **name**: `epnp-ns`, `pnp-ns` and `pnp` share a class. `declaration(name)` reads it without building | Resolve decides before a model exists; PHY-21 |
| D2 | Declaration fields | `options` (`model_options` keys); `switches` (value set honoured per `flow`, `variable_density`, `inertia`, `dielectric_gradient_forces`); `solids`; `coefficients` ⊆ {`fixed_charge`, `solid_fraction`}; `wall_distance`; `strategies`; `quantities`; `transport`; `reports_newton` | Each replaces an inventoried branch (*Design* §1) |
| D3 | Built-model members | The protocol gains `scales`, `essential_boundaries(boundaries)` (field → pattern), `species` (empty for one field) and `relative_permittivity(solution)`. `cold_state` takes `initial_concentrations` everywhere and refuses it where `species` is empty | Read off `CoupledModel` today |
| D4 | Transport capability | A `TransportModel` protocol holds exactly the `CoupledModel` members used outside `physics/`. `transport_model(solution)` returns it when declared, else refuses naming the model. mypy checks that `CoupledModel` satisfies it | Replaces `isinstance`; NUM-27 stays defined for transport only |
| D5 | Options and keys | `model_options` is the case's candidate set filtered by `declaration.options`, byte-identical for all but `poisson`, so five models' stage-10 keys do not move. `poisson` gains `solid_permittivities`, and its key moves with its operator | §5.3.2; VER-34 |
| D6 | Operating point | Every builder receives the case's `electrolyte` and `concentration_M` outside `model_options`, as coupled builders do today | One call site |
| D7 | `poisson` | New class `PoissonModel`: `ε̃ ∇φ̃` against `ρ̃_pore` over all of Ω on the NUM-09 mesh-unit scales. Fluid `ε̃ = 1` (`ε_r,f⁰`), solids `ε_p/ε_r,f⁰`, `χ` blended. Declares solids and both coefficients; no `d`, strategy `none`, no quantities | PHY-21 NOTE; ruling 13; §8.2.4 D3 |
| D8 | One permittivity | The material split and `χ` blend leave `CoupledModel.permittivity` for one function taking the fluid's `ε̃`: `ε_r,f(⟨c⟩)` or 1 | No second copy; VER-30 |
| D9 | `pb`, `pb-linear` | With the case electrolyte they default `λ_D` to `scales.debye_length_nm`. The builder refuses any salt but a symmetric monovalent one | PHY-21 NOTE; FR-19 |
| D10 | Builder refusals | `resolve` builds the model once and re-raises a builder refusal naming `physics.model`. Building imports no NGSolve | QR-12; CLI import tests |
| D11 | Case refusals | An unhonoured switch value, undeclared solids or `inputs.charge`/`inputs.eps_r`, an unadmitted strategy and an undeclared `outputs:` quantity are refused from the declaration, naming model, key and admitted values. `pnp` admits `none` only, as §6.5 already forces | §5.3.1 NOTEs |
| D12 | Mesh gate | `essential_boundaries` supplies the concentration, no-slip and axis requirements; distance sources are required only under `wall_distance`. A solid under a model without solids is refused as such | §5.3.1 NOTE |
| D13 | Solve | `single_rung` passes `wall_distance_nm`, `fixed_charge` (on `model.scales`) and `solid_fraction` by declaration, and runs the wall-distance gate only where `d` is read. `reports_newton` decides `_instrumented`'s callback | *Design* §1 |
| D14 | The ladder | Stays in `solve/continuation.py`, its rungs built through `create` and equal to today's. The top rung is `resolved.model`, replacing `== "epnp-ns"`. `default_ladder` is the source walk's one exemption | §5.4.3 NOTE; §6.5 |
| D15 | Stages 11, 12 | Without `transport`, stage 11 records the bias and an empty selection and builds no indicator; the transport path is unchanged. Export and GUI take `scales` and `relative_permittivity` from any model | Stage 12 walkable for `poisson` |
| D16 | Public API | `PhysicsModel`, `TransportModel`, `ModelDeclaration`, `register_model`, `registered_models` join `nanopnp.PUBLIC` | FR-20; `test_public_api.py` |
| D17 | Scalars "as before" | The three coupled models' stage-11 scalars on the quickstart case, before and after on one machine, bitwise, in the Outcomes. No cross-platform numeric golden | Netgen meshes are not bitwise portable |

### Work items

1. `physics/models.py`: `ModelDeclaration`, `register_model`, `declaration`, `TransportModel`,
   `transport_model`, the D3 members; the shared permittivity function (D8); `PoissonModel` (D7);
   `ElectrostaticModel` reduced to `pb`/`pb-linear` with D9. Read *Design* §2 first.
2. `io/case.py`: delete `COUPLED_MODELS`; `_check_physics_switches`, `_model_options`, the strategy
   check and a new outputs check read the declaration (D5, D10, D11).
3. `mesh/ingest.py` (D12); `solve/state.py`, `solve/stage.py`, `solve/continuation.py` (D13, D14).
4. `post/qoi.py`, `post/forces.py`, `post/stage.py`, `gui/render.py`, `validation/mms.py`: type
   against `TransportModel` and reach it through `transport_model` (D4, D15).
5. `nanopnp/__init__.py` (D16); `docs/project/physics-models.md`, which walks `PoissonModel` as the
   worked example, in the nav; `CHANGELOG.md` under `v0.4.0-alpha.1`.
6. `SPECIFICATION.md`: VER-56's row in §7 and the Appendix A rows FR-20 → VER-56, QR-14 → VER-03 and
   VER-56.

### Verification

| Test | Tier | Identifiers | Oracle and tolerance |
|---|---|---|---|
| `tests/tier1/test_model_interface.py` | 1 | VER-56 | An AST walk of `src/nanopnp/` outside `physics/` finds no concrete model class, no `COUPLED_MODELS` and no comparison with a registered model name, `default_ladder` excepted. Each D11 and D12 refusal names model, key and admitted values; `pb` beside `inputs.charge` is refused (PHY-24). Five models' `solve_provenance` hashes equal a golden recorded from `main` first (D5), and so do the ladder's rung models |
| `tests/tier1/test_model_interface.py` | 1 | VER-56 | A forwarding class wrapping `pnp` in the test tree, registered at run time and subclassing no shipped model, runs from a case file through stages 10–12. The stage-11 summary and the state vector equal `pnp`'s on the same case bitwise, and `type(solution.model)` is the wrapper at stage 11 |
| `tests/tier1/test_model_interface.py` | 1 | VER-56, FR-19 | `pb-linear` and `poisson` cases on a solid-free slab mesh equal direct API solves on the same mesh (the `pb-linear` one with `λ_D` from `case_debye_length_nm`) to 1e-12 relative. A `poisson` case with solids and a supplied `volume_charge_density` equals the API solve with `fields.charge.assemble(scales)` likewise |
| `tests/tier2/test_poisson_layers.py` | 2 | VER-56, PHY-20 | The three-layer capacitor of *Design* §3 at P2, with element edges on `z = a, b`, reproduces the piecewise-quadratic closed form to 1e-10 of `max|φ̃|`. P2 contains the exact solution, so any larger error is a scale, sign or permittivity defect |
| Existing VER-30, VER-34, VER-45, VER-47 and Tier 2 | 1, 2 | — | Unchanged: the blend (D8), the state round trip, generated references and the case corpus |

`uv run pytest tests/tier1/test_model_interface.py tests/tier2/test_poisson_layers.py -v`, then the
full gate.

### Out of scope

The charge producer (WP27, WP28); VAL-06 and its tolerance (WP29); a new model bringing its own
continuation (after v1.0); a prescribed `ρ_ion`; per-model schema defaults (schema v2 is frozen).

### Open questions

None blocking. The close calls are D9 (making `pb` runnable) and D14 (one named exemption rather
than moving `default_ladder`), and the author may overrule either without touching the rest.

## Design

### 1. Dispatch inventory (surveyed 30 September 2026 on `8064a55`)

| Site | Branch today | Replaced by |
|---|---|---|
| `io/case.py` `COUPLED_MODELS`, resolve's continuation check, `_check_ladder_can_honour`, `_check_physics_switches`, `_model_options` | name set, `== "pnp"` | D2 `strategies`, `switches`, `solids`, `coefficients`, `options` |
| `mesh/ingest.py` `required_names` | `in COUPLED_MODELS`, `!= "pnp"` | D3 `essential_boundaries`; D2 `wall_distance` |
| `solve/state.py` `single_rung`, `ladder` | `in COUPLED_MODELS`, `isinstance`, `== "epnp-ns"` | D6, D13, D14 |
| `solve/stage.py` `_rungs` | `isinstance` | D2 `reports_newton` |
| `solve/continuation.py` `_log_branch`, `transfer`, `_report_peclet`, `_coupled` | `isinstance`, direct construction | `TransportModel`, `species`, `create` |
| `post/qoi.py`, `post/forces.py` `_coupled` | `isinstance` | `transport_model` |
| `post/stage.py` export, `_permittivity`; `gui/render.py` | `isinstance` | `scales`, `relative_permittivity` |
| `validation/mms.py` | annotation | `TransportModel` |

Measured with the quickstart case and `continuation: none`: `pb`, `pb-linear` and `poisson` are
first refused for the default `flow`, `variable_density` and `inertia`. With those false, all three
are refused by the ingest gate for the membrane's missing permittivity, which resolve would refuse
if supplied.

### 2. Poisson's nondimensional form

On the mesh-unit scales (`a = 1 nm`, `V_T = RT/F`, `ε_ref = ε_0 ε_r,f⁰`), `φ̃ = φ/V_T` and
`ρ̃ = ρ a²/(ε_ref V_T)`, which is `Scales.charge_density_C_m3`. Then
`∫ ε̃ ∇φ̃·∇v r dr dz = ∫ ρ̃ v r dr dz` with `ε̃ = ε_r/ε_r,f⁰`: 1 in the fluid, 3.2/78.15 = 0.04095 in
the membrane. This is the coupled model's Poisson block with `ρ_ion = 0` and the fluid at its
`c → 0` value. `ε_r,f⁰ = 78.15` is from `data/corrections/willems2020_nacl.yaml`, Gavish 2016.

### 3. The three-layer capacitor [verified]

`z ∈ [0, L]`, fluid on `[0, a)` and `[b, L]`, membrane on `[a, b)`, uniform `ρ_0` everywhere,
`φ(0) = 0`, `φ(L) = V`, natural on `r = R` and the axis. The solution does not depend on `r`. Gauss
gives `D(z) = D_0 + ρ_0 z`, continuous across both interfaces, and
`φ(z) = −[D_0 F₁(z) + ρ_0 F₂(z)]` with `F₁ = ∫₀ᶻ ds/(ε_0 ε_r)` and `F₂ = ∫₀ᶻ s ds/(ε_0 ε_r)`.
`φ(L) = V` fixes `D_0 = −(V + ρ_0 I₂)/I₁`, where

- `I₁ = (a + L − b)/(ε_0 ε_f) + (b − a)/(ε_0 ε_s)`
- `I₂ = (a² + L² − b²)/(2 ε_0 ε_f) + (b² − a²)/(2 ε_0 ε_s)`

Check values at `L = 10`, `a = 4`, `b = 6` nm, `ε_f = 78.15`, `ε_s = 3.2`, `ρ_0 = −1.0 × 10⁷ C m⁻³`
(about ClyA's −72 e over 400 nm³), `V = 0.05 V` and 298.15 K:

- `D_0 = 0.049391 C m⁻²`
- `φ(4 nm) = −0.169903 V`, `φ(5 nm) = −0.324892 V` (−12.6454 `V_T`), `φ(6 nm) = −0.126940 V`

Obtained by quadrature of the piecewise integrand, and checked against the closed forms of `I₁` and
`I₂` to 2 × 10⁻¹⁶. A finite-difference residual of `−(εφ′)′ − ρ_0` vanishes in each layer, and `D`
is continuous at `z = a`. `φ` is piecewise quadratic in `z`. The P2 space on a mesh whose edges lie
on `z = a` and `z = b` contains it exactly. The r-weighted integrands are cubic, which order-3
quadrature integrates exactly, so the Galerkin solution equals the closed form up to the linear
solve's round-off.
