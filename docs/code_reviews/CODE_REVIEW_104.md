# Code review 104: WP6.11's ship, the wall term and the compiled kernel (REV-303, REV-302)

2026-11-28 · PR #230, branch `ccr-27befe84-ows69p`, head `a84efce` on base `c598dcd` · scope: two commits, 21 files,
+196 and −51, read from `git diff c598dcd...a84efce`, against REV-303's ruling ("Write the wall term") and REV-302's
section in `docs/project/review-items.md`, PHY-22, PHY-23, NUM-28, QR-13, CON-07 and §5.4.1 · reviewer:
`np-reviewer`, Opus 5.5 at high effort, with no hunt findings · status: completed.

Probes: `permittivity_gradient` on the shipped file with an analytic distance (`x + 0.25`) at the base and at the
head; NGSolve's `Diff` in a grid function an expression does not contain (a `ZeroCoefficientFunction`, which a
product and a sum fold away), `grad` of a composite expression (raises), and `Diff` in a composite expression (a
silent zero); `Compile(realcompile=False)` on a form with trial proxies and grid functions, against the tree: the
residual and the Jacobian equal exactly, and a compiled function reads a grid function's later values. `uv run
pytest` of `test_nernst_planck.py`, `test_forces.py`, `test_kernel.py` and `test_physics_models.py` after the fix: 77
passed. No benchmark, sweep, `gate.sh run` or `--nightly`. Line numbers are the reviewed head's.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Low | `src/nanopnp/physics/nernst_planck.py:177-180` | Axis 3, PHY-23 and NUM-28 (the gradient where the permittivity takes no wall fit is the chain rule in `c~_i` alone). `state_gradient` takes `ops.grad(distance)` wherever the distance is not a number, before the zero `Diff` can fold it. An analytic distance, which `PhysicsModel.solve` accepts (`test_fr23_…` passes `x + 0.25`), is a composite expression whose `grad` NGSolve does not define, so PHY-23's terms and NUM-28's `f_KH` on the shipped file, with no wall fit, raise an opaque `NgException` where the base returned the gradient (probe: `(-3.674e-3, -1.470e-3)` at the base, a raise at the head). The pipeline's distance is always a grid function, so no case reaches it. Confirmed | Fixed in `05135ee`: the `d` part is taken only where the permittivity's correction applies a wall fit (`NondimensionalCoefficients.permittivity_reads_wall`); the probe returns the base's value, and the expression is unchanged elsewhere, the term having been a folded zero |
| 2 | Low | `specification/05-software-design/04-component-design.md:21` | Axis 2, §5.4.1. `compile` joins the `Operators` protocol, which the kernel calls on each slot's integrand, but the table of what the context's operators hold did not name it. Doubt | Fixed in `d515692` |

## Checked and found true

- **The chain rule and the sign (REV-303).** `∇ε~_r = Σ_i (∂ε~_r/∂c~_i)∇c~_i + (∂ε~_r/∂d)∇d`, and the decrement's
  `∇(∂ε~_r/∂c~_i)` takes `∂²ε~_r/∂c~_i∂d ∇d` through the same function; the force keeps `−½|∇φ~|²∇ε~_r`. The
  derivatives are taken in `variables.variables`, the objects `coefficients.concentrations` holds in the primitive
  branch, as the replaced sum of `permittivity_sensitivity` was. The wall factor's floor `IfPos(d, d, 0)` has the
  branch derivative, one wherever `d > 0`.
- **The log branch.** `permittivity_gradient` and `excess_potential_gradient` raise before `state_gradient` is reached.
- **The solid blend.** `blend_gradient` and `blend_sensitivity` receive the whole fluid gradient, so the blend's
  `(1 − χ)∇ε_r,f` carries the wall part (PHY-23's NOTE).
- **No default expression changes.** `willems2020_nacl` has no permittivity `fw`; at the head the `d` part was a
  `ZeroCoefficientFunction` that folds out of the product and the sum, and after finding 1 it is not formed.
- **The partner check (PHY-22).** A wall fit alone, applied and on, now satisfies PHY-23's switch; `reads_wall` then
  makes the solve's distance a field, so `permittivity_varies` holds and the force is not zero.
- **The tests are independent oracles.** VER-81's split writes `∂ε~_r/∂d = ε~_r P₁e/(1 − e)` by hand from the fixture's
  `exponential_saturation_plus`, agrees with `domain_force` and the omitted term to 10⁻¹², and requires the wall part's
  work to exceed 10⁻³ of the dielectric work, so a dropped `d` part fails by nine orders. PHY-23's test compares both
  terms against a central difference in space of the blended `ε~_r` and of the decrement's potential, which contain
  the distance as a grid function; the fit's `∂ε/∂d` near `d = 0.1` to `0.8` is of order one, far above the 10⁻⁶ and
  10⁻⁵ tolerances. The fixture is built from the shipped file, and no fitted parameter enters `src/`.
- **A composite distance with a wall fit.** It still raises in `grad`, which is a refusal, not a plausible wrong
  answer; `Diff` in such an expression would be a silent zero, which the raise precedes.
- **The compile (REV-302).** `kernel.py` calls `context.ops.compile` and imports no backend; the NGSolve construct is in
  `physics/backend.py` alone (QR-13, §5.4.1, VER-65). `realcompile=False` builds the step list in Python and calls no
  C++ compiler (CON-07). The compiled function reads grid functions live, so the lagged wind and the state update as
  before; the residual and Jacobian agree exactly in the probe, as the commit's twelve-variant numbers say. The
  integration order is unchanged: VER-81's one-slot test passes.
- **The records.** REV-302 and REV-303 are `fixed` in `review-findings.md`, each with its section's **Fixed** (and for
  REV-303 **Ruled**) paragraph, in the decisions registers, the knowledge file's two bullets with their footnote and
  `[tested:]` markers, and `knowledge/log.md`; PHY-22's, PHY-23's and NUM-28's NOTEs state the code's behaviour.

## Not assessed

- The commit's timings (39.8 s to 0.38 s under `reference`; 19.1 s to 0.28 s under `supg`) are read, not repeated.
- Tier 2's walks on the compiled kernel; the gate ran Tier 1.
- §4.5's switch table lists the permittivity's leaves as (`model`, `concentration`), the validated file's, without
  the `wall` leaf a fitted file can use; a line this diff did not touch.
