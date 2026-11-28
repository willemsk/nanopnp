# Code review 103: WP6.11, switches as data and the forces

2026-11-28 · PR #230, branch `ccr-27befe84-ows69p`, head `6c21f59` on base `e42272a` · scope: 50 files, +1347 and
−370, read from `git diff e42272a...6c21f59`, against
[the plan](../plans/phase-6/wp6.11-switches-as-data-and-the-forces.md), VER-82, VER-81 (c), VER-80, FR-40 (in part),
FR-25, NUM-02, NUM-18, NUM-28, NUM-29, VER-71, VER-22, PHY-21, PHY-23, REV-298 and §8.2.62 BL7, §8.2.63 BM1 to BM3 ·
reviewer: `np-reviewer`, Opus 5.5 at high effort, with six hunt findings · status: completed.

Probes: the analyte-force refusal driven in scratch on the validated default case with the log key and
`analyte_force`, the concentration part on, off, and a wall part applied; the Equations tool's new conflict helpers
on a stand-in model for flow off, the log key on and PHY-23's switch on; `governing` on PHY-23's force and on Poisson.
`uv run pytest` of `test_switches.py`, `test_case_schema.py`, `test_forces.py`, `test_qoi_stage.py`,
`test_model_interface.py`, `test_gui_screens.py`, `test_physics_model.py` and `test_case_leaves.py` after the fixes:
173 passed, 142 skipped (the browser and `slow` tests). No benchmark, sweep, `gate.sh run` or `--nightly`. Line
numbers are the reviewed head's.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Medium | `src/nanopnp/pipeline/checks.py:1100-1116` | Axis 2 and 3, NUM-02's NOTE and D10's purpose (a force the log branch cannot give fails before the solve, not after it). The check refuses `analyte_force` beside the log key only where the permittivity's concentration fit applies, but `flow.permittivity_gradient` raises on the log branch wherever `permittivity_varies`, which a wall fit (`fw` of the solvent's permittivity, which `PermittivityBlock` admits) makes true with the concentration part off. Such a case solves and then fails at extraction. Hunt finding 1. Confirmed | Fixed in `32901ab`: the check refuses where either part applies and is on, naming each leaf; NUM-02's NOTE and the CHANGELOG say so |
| 2 | Low | `src/nanopnp/io/switches.py:422-428` | Axis 2, §5.4.4's rule that a term is in force with each switch its records require. `governing` follows `requires` one level, so a chain would leave a term in force with a required switch off. No chain exists among the five records. Hunt finding 3. Doubt | Fixed in `32901ab`: the closure runs until the set stops growing |
| 3 | Low | `src/nanopnp/gui/web/physics_tools.py:275-281`, `:367-368` | Axis 2, BM3 and D7 (the Equations tool reads the records). The held state, the hint and the lead are one hard-coded rule for PHY-23's switch without the flow, so the new exclusion of the log key and PHY-23's switch is never shown and the case is refused only at the run. Hunt finding 2. Confirmed | Fixed in `32901ab`: both places read `conflicts` of the records; the dielectric-without-flow text keeps its sense ("With flow off, dielectric forces cannot be on.") |
| 4 | Low | `CHANGELOG.md:29-33` | Axis 1, `python.md`'s rule that a public break goes into `CHANGELOG.md`. `ModelDeclaration` now demands the honoured values of `log_variables`, so a declaration of four switches given to `register_model` raises at import; the entry did not say so. Hunt finding 5. Confirmed | Fixed in `32901ab`: a **Changed** line |
| 5 | Low | `src/nanopnp/io/switches.py:319-326` | Axis 1, §8.4.2: `Switch`'s docstring cites "section 5.4.4" and "FR-25". Hunt finding 6. Confirmed | Fixed in `32901ab` |
| 6 | Low | `src/nanopnp/physics/flow.py:85-117` (outside the diff) | Axis 3, PHY-23 (the force is `−½|∇φ|²∇(ε_0 ε_r)`, the whole gradient). `permittivity_gradient` takes the chain rule over the concentrations alone, so a permittivity wall fit's `∂ε_r/∂d ∇d` enters neither PHY-23's force nor NUM-28's `f_KH` and omitted term, while the Maxwell stress of the domain route carries it: a plausible wrong split. `Electrolyte.relative_permittivity` says "there is no wall correction", but `PermittivityBlock` admits an `fw` and the builder applies it. The shipped file has none, so no shipped case reaches it. Doubt | Left to the author. Recommendation: refuse an `fw` on the solvent permittivity when a correction file is loaded, as `_IonPropertyBlock` refuses one per species, until a package writes the wall term; that changes what a correction file admits, so it is a ruling, not a review edit |

The hunt's findings:

| Hunt | Outcome |
|---|---|
| 1. The log branch's force refusal misses a wall fit | Fixed in `32901ab` (finding 1) |
| 2. The Equations tool shows no exclusion | Fixed in `32901ab` (finding 3) |
| 3. `governing` is not transitive | Fixed in `32901ab` (finding 2) |
| 4. The honoured-values refusal cites PHY-21 for the log key | Refuted. PHY-21 defines each model by the equations it solves; `pb`, `pb-linear` and `poisson` solve no Nernst–Planck equation, so NUM-02's branch of it is outside the model, which is what the refusal says. The refusal is of the model's scope, as for the four physics switches, and NUM-02 governs only how a model that solves the equation discretises it |
| 5. The CHANGELOG omits the declaration's new contract | Fixed in `32901ab` (finding 4) |
| 6. Identifiers in `Switch`'s docstring | Fixed in `32901ab` (finding 5) |

## Checked and found true

- **The records.** Five records in the plan's order with the plan's paths, defaults, terms and relations; `flow`
  names Variable density, as the plan's grounding says it must. `io/switches.py` imports nothing of the package
  (VER-61). `Term.switches` derives from the records, and each declaration states the five names.
- **Every list derived.** `SWITCH_PATHS`, `MODEL_SWITCH_PATHS` and the validated default read the records;
  `deviations` and `CoupledModel._deviations` both report `numerics.log_variables` (FR-25); `_LADDER_PHYSICS` is
  gone and the ladder refuses every record off its default, naming its path and `numerics.continuation: none`
  (NUM-18's NOTE; BM2).
- **The key (D2, D6).** `Numerics.log_variables`, owned by the physics model's file; deleted from the case artefact's
  parameters and from `model_options` at false, so `VALIDATED_DEFAULT_CASE`'s hash is the pre-key literal and the
  pinned solve keys hold; `_COUPLED_OPTIONS` passes it at true; `pb`, `pb-linear` and `poisson` honour false alone
  (VER-71's probe).
- **The conflicts.** The model and the case check refuse the same `conflicts`; the model's message keeps "log
  branch"; the requires remedy is read from the declaration as before.
- **The forces (D8, NUM-28, PHY-23).** The hydrodynamic half is `−∫σ:∇w + ∫(Σf)·w` over the densities in force,
  the inertia entering as `−Re ϱ̃ (∇ũ)ũ`, so the sign of the momentum equation's left side is kept; the
  electromagnetic half subtracts the ionic and the dielectric density's work whether in force or not; the omitted
  term is `−∫f_KH·w`, zero exactly when PHY-23's force is among the context's terms. The blend replaces
  `inputs.solid` for the forces alone, so the hydrodynamic half reads the density the solve assembled. The measure
  and the fluid region are the context's, the integration order `Measures`' own; no `1/r` form changed.
- **The test of the split.** It writes the three densities from the coefficients, independently of the kernel, and
  requires the inertia's and the dielectric density's work to exceed 10⁻⁹ of their half, so an omitted density
  cannot pass; the solid-fraction variants use PHY-23's NOTE's blended gradient.
- **The specification.** NUM-02's and NUM-18's NOTEs, §5.3.1's listings and NOTE, §5.4.3's and §5.4.4's NOTEs, VER-80,
  VER-81 (c), VER-82 and Appendix A's FR-25 and FR-40 rows change with the code; the ruling record 8.2.63 and
  `holds-now.yaml` carry BM1 to BM3.
- **The test scope.** VER-82's four tests and VER-81 (c)'s are core mechanisms or physics; the NUM-18 refusal's
  fifth case extends a kept test; `test_variables.py` now checks the key it meant, as `log_variables` holds the word.
  No test is outside the scope.

## Not assessed

- Item 5's run (`test_guard_numbers.py`, `test_force_convergence.py`) and the stored-force comparison of item 4 are
  read from the plan's Outcomes, not repeated.
- The workbench's rendering of the new hints in a browser.
- The plan's D10 row and its rendered line in `decisions-closed.md` still say "the concentration fit"; the
  specification, which governs, now says either fit.
