---
paths:
  - "src/nanopnp/physics/**"
  - "src/nanopnp/numerics/**"
  - "src/nanopnp/solve/**"
  - "src/nanopnp/post/**"
  - "src/nanopnp/materials/**"
  - "src/nanopnp/charge/**"
  - "src/nanopnp/mesh/**"
  - "src/nanopnp/validation/**"
  - "data/corrections/**"
  - "tests/tier2/**"
  - "tests/tier3/**"
---

## Physics ground rules

- **Corrections are data, not code.** Parameters live in `data/corrections/*.yaml`; a new electrolyte
  never touches solver code.
- **Classical PNP-NS is a configuration, not a branch.** Each correction is independently switchable;
  disabling one selects the `none` model, not a code branch.
- **Deviations from the validated model go behind a flag, default off**, and must be verified against
  COMSOL before becoming default (e.g. dielectric-gradient body force, mollified distance field, an
  added mobility correction).
- **`⟨c⟩` is `(1/n)Σcᵢ`, not the ionic strength**; they coincide only for a symmetric 1:1 salt. `d` is the distance to the nearest **pore**
  boundary; the membrane is excluded.
- **Einstein holds only at infinite dilution.** `D_i/μ_i` drifts to 1.2–1.7 × kT/e between 0.15 M
  and 3 M. Never assert `D_i/μ_i = kT/e` at finite concentration
  (VER-05, PHY-14). Poisson–Boltzmann is not "PNP at zero bias" (PHY-24).
- **Ion wall function: `1 − exp(−6.2(d̄ + 0.01))`** — plus, 6.2 nm⁻¹. The viscosity wall function takes
  a minus. Steric `β_i` enters the flux bracket with `+`, and the bracket is negated; a flipped sign
  diverges.

## Numerics rules

- **Assert, don't hope.** Charge conservation, packing fraction < 1, concentration positivity at every
  Newton iterate, mesh quality (min SICN/gamma > 0.3). A gate failure aborts with a diagnostic naming
  the gate, quantity and location (QR-12). Never return a plausible wrong answer.
- **Integration order ≥ 3 on every form carrying `1/r`** (VER-07); order 2 samples `r = 0` and gives NaN.
- **Never compute ionic current from a cross-section integral of the CG flux.** Use the indicator form
  or the variational reaction flux, and cross-check both (FR-23, QR-04; `knowledge/06-numerics-fem/07-quantities-of-interest-and-the-flux-trap.md`).
- **Newton convergence needs the relative update on the undamped direction as well as the residual**;
  residual alone breaks warm starts. Never call a step that raised the residual convergence.
- **Reach hard cases by continuation, not a cold solve** (FR-17); warm-start sweeps from a converged
  neighbour.
- **Record the stabilisation mode with every number.** COMSOL ran streamline and crosswind
  stabilisation on; results are not comparable until matched (§6.4, §7.4).
