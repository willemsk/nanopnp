---
type: Benchmark
title: Tier 2 — Analytic benchmarks (minutes)
description: Tier 2, analytic benchmarks, with their formulas.
tags:
- validation
- benchmark
sources:
- id: thesis
  resource: https://github.com/willemsk/phdthesis-text
  title: Willems, PhD thesis (LaTeX source)
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:tests/tier1/test_knowledge_arithmetic.py::test_gouy_chapman_and_debye_huckel_closed_forms
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_knowledge_arithmetic.py::test_limiting_current_depletion_debye_and_mobility_ratios
  at: '2026-11-09T00:00:00Z'
- by: process:tests/tier2/test_exclusion_stern.py::test_ver59_the_drop_across_a_generated_shell_obeys_gausss_law
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_exclusion_stern.py::test_ver59_the_potential_is_logarithmic_across_the_shell
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_exclusion_stern.py::test_ver59_the_shell_drop_is_a_tenth_of_the_wall_potential_or_more
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_pnp_benchmarks.py::test_ver16_current_saturates_at_the_limiting_value
  at: '2026-11-09T00:00:00Z'
---

## Tier 2 — Analytic benchmarks (minutes)

### 2.1 Gouy–Chapman, 1:1 electrolyte
VER-12 states the closed form, Grahame's relation and the tolerance (`SPECIFICATION.md` §7.2). The
potential and Grahame's relation are mutually consistent to 6 digits by numerical differentiation. **[tested: tests/tier1/test_knowledge_arithmetic.py::test_gouy_chapman_and_debye_huckel_closed_forms]**

### 2.1.1 Gouy–Chapman–Stern through stage 5: Gauss's law across a cylindrical shell **[tested: tests/tier2/test_exclusion_stern.py::test_ver59_the_drop_across_a_generated_shell_obeys_gausss_law]** **[tested: tests/tier2/test_exclusion_stern.py::test_ver59_the_potential_is_logarithmic_across_the_shell]** **[tested: tests/tier2/test_exclusion_stern.py::test_ver59_the_shell_drop_is_a_tenth_of_the_wall_potential_or_more]** {#211-gouychapmanstern-through-stage-5-gausss-law-across-a-cylindrical-shell}

A planar Stern layer (VER-31) cannot be posed through stage 5, whose region is axisymmetric, so
VER-59 poses it on a long tube, `r ∈ [3, 5]` nm, with stage 5's shell of `a` = 0.25 nm on its lumen
side. On a plane where `φ` is flat in `z`, the charge-free shell carries the flux of the mobile
charge it encloses:

```
φ(R − a) − φ(R) = λ_enc ln(R/(R − a)) / (2π ε₀ ε_r,f⁰),   λ_enc = F Σ z_i ∫₀^{R−a} c_i 2πr dr
```

and `φ` takes the mean of its ends at `√(R(R − a))`. The trap: `∂φ/∂z = 0` by symmetry is not
enough, because Gauss's law in the shell needs `∂²φ/∂z² = 0` too. **With the bilayer on the analysis
plane the drop missed the closed form by 6 %**: the membrane (`ε` = 3.2) against the body's outer
side curves `φ` in `z` across the 2 nm body. With the bilayer moved 12 nm away
(`geometry.membrane.centre_z_nm` = −12 on a 30 nm tube) the drop is 6.5365 mV against 6.5357 mV,
1.3e-4 relative, at 0.1 M, `pnp`, zero bias, the default sizes (49,629 triangles, 44 s to stage 10),
and the geometric-mean point is the mean of the ends to 2e-6 of the drop. At `size_scale` 2 the
agreement is 3.6e-3: what moves is `λ_enc`, the lumen's concentration integral, not the drop. The
shell is 17.8 % of the wall potential (−36.8 mV), so a shell holding ions cannot pass.
`tests/tier2/test_exclusion_stern.py`.

### 2.2 Debye–Hückel in a cylinder
VER-13's closed form satisfies `∇²φ = φ/λ_D²` in cylindrical coordinates to 6 digits. **[tested: tests/tier1/test_knowledge_arithmetic.py::test_gouy_chapman_and_debye_huckel_closed_forms]**
**The cleanest single test of the axisymmetric Poisson weak form and the axis BC**: it exercises
the `r`-weighted measure and the natural condition at `r = 0` with an exact answer.

### 2.3 Electro-osmosis in a cylindrical capillary
VER-14: Rice & Whitehead (1965), coupled Poisson + Stokes.

### 2.4 Helmholtz–Smoluchowski limit
VER-15: the asymptotic correctness of the coupled solve.

### 2.5 1D steady PNP with limiting current
Bazant, Chu & Bayly, *SIAM J. Appl. Math.* **65**, 1463 (2005). Tests the full PNP system. At the
largest bias the current reaches the electroneutral limiting value to 3 %. **[tested: tests/tier2/test_pnp_benchmarks.py::test_ver16_current_saturates_at_the_limiting_value]**

- **Two errors can cancel and hide both.** The benchmark passed for a while at the wrong film
  length *because* of a second bug, an electrolyte whose correction switches said off while its
  resolved models stayed on (`knowledge/01-physics-epnpns/07-implementation-notes-carried-forward.md`).
  A 100 nm film is space-charge-limited and reads 14 % high against the electroneutral closed form
  (not tested). The silently-active corrections broke the Einstein relation, `mu/mu0` = 0.63
  against `D/D0` = 0.92 at 1 M, **[tested: tests/tier1/test_knowledge_arithmetic.py::test_limiting_current_depletion_debye_and_mobility_ratios]**
  and pulled the current down by about as much. Fixing either alone turns a passing benchmark red.
- **The screening length that matters at a depleted electrode is not the bulk one.** `lambda_D` goes
  as `c^(-1/2)`, so at 1e-3 of bulk it is thirty-two times larger — 9.6 nm at 1 M. **[tested: tests/tier1/test_knowledge_arithmetic.py::test_limiting_current_depletion_debye_and_mobility_ratios]**
  A benchmark that justifies its geometry with the bulk value can be an order of magnitude out. The
  signature of a space-charge-limited film is that the plateau current stops depending on the
  electrode concentration at all (not tested).

### 2.6 Maxwell–Hall access conductance
VER-17, with its NOTE on Hall's factor of two: the frequently copied access term is wrong by 2×, so
a correct solver would fail a gate set on it.

### 2.7 Method of manufactured solutions
VER-18, on the full coupled axisymmetric system with `r`-weighted forms: **the only way to verify
the `u_r/r²` hoop term and the axis treatment.**

### 2.8 Analyte force benchmarks
The thesis's trapping work used equilibrium APBS on a bead model with a 1D analytic rate model,
with no stress-tensor integrals and no force profile (see `knowledge/05-analyte-and-forces/01-read-this-first-the-acs-nano-2019-work.md`–§9). The
only published force profile is Angew. Chem. 2022 (`knowledge/05-analyte-and-forces/11-correction-continuum-force-computation.md`), which gives main-text targets
(`knowledge/05-analyte-and-forces/11-correction-continuum-force-computation.md#106-validation-targets-plyab-hb`) but no code or field data. Verify against analytics first, then those targets:

- Stokes drag on a sphere in the exact Stokes far field, with no confinement correction (VER-19).
- Maxwell stress on a dielectric sphere in a uniform field, the zero test with its `qE₀` anchor (VER-20).
- Electrophoretic mobility against Henry's function, Hückel at small `κa` and the Smoluchowski gap
  under 15 % (VER-21).
- Domain-form vs surface-form force must agree (VER-22; `knowledge/06-numerics-fem/07-quantities-of-interest-and-the-flux-trap.md`).

### Measured values

The measured values and why each tolerance is set: `knowledge/07-software-stack/21-tier-2-test-evidence-budgets-timings.md`
and `22-tier-2-test-evidence-analytic.md` (Tier 2), `knowledge/05-analyte-and-forces/13-tier-2-test-evidence-electro-osmosis.md`
(the force routes and electrophoresis), and `knowledge/08-validation-benchmarks/07-tier-3-test-evidence-run-times-of-the.md` (Tier 3).

---

