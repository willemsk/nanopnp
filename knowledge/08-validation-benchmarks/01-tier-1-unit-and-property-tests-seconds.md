---
type: Benchmark
title: Tier 1 — Unit and property tests (seconds)
description: Tier 1, unit and property tests, with their check values.
tags:
- validation
- benchmark
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:tests/tier1/test_charge_quadrature.py::test_qr03_an_explicit_rule_below_num07_s_floor_is_refused
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_corrections.py::test_ver03_bulk_properties_at_the_validity_limit
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_corrections.py::test_ver04_nernst_einstein_holds_at_infinite_dilution
  at: '2026-10-16T00:00:00Z'
---

## Tier 1 — Unit and property tests (seconds)

- Charge conservation through Gaussian smearing and azimuthal projection, evaluated **on the
  deployed FE mesh**, not the source grid: `|∫ρ_fixed·2πr dr dz − Q_net|/|Q_net| < 10⁻³`. Also
  check per-z-slice cumulative charge against the PQR sorted by z — this catches Jacobian errors
  that cancel globally.
- Every correction model reproduces its published check values (see `knowledge/01-physics-epnpns/08-errata-in-the-source-with-the-arithmetic.md`):
  `f^w_D(0) = 0.0601`, `f^w_D(0.75) = 0.9910`, `η₀/η^w(0) = 0.3790`, `η₀/η^w(1.45) = 0.9876`,
  `η(5.3 M) = 1.752 × 10⁻³ Pa s`, `ϱ(5.3 M) = 1194 kg m⁻³`, `D_Na(5.3 M) = 8.13 × 10⁻¹⁰`,
  `D_Cl(5.3 M) = 1.071 × 10⁻⁹`. **[tested: tests/tier1/test_corrections.py::test_ver03_bulk_properties_at_the_validity_limit]**
- Nernst–Einstein consistency of the infinite-dilution values: `μ_i⁰ = D_i⁰/V_T` to 4 significant
  figures. **[tested: tests/tier1/test_corrections.py::test_ver04_nernst_einstein_holds_at_infinite_dilution]**
- **Einstein-relation drift test.** `D_i/μ_i` is *not* `kT/e` at finite concentration — the ratio
  drifts to 1.2–1.7 × `kT/e` between 0.15 and 3 M because D and μ were fitted independently. Assert
  the drift matches expectation rather than asserting the Einstein relation. This is also why
  Poisson–Boltzmann is a *separate model*, not the PNP solver at zero bias.
- Wall-distance field is C¹ after mollification.
- Integration order ≥ 3 asserted on every form containing `1/r`; a unit test integrating a known
  `1/r`-weighted quantity on an axis-touching mesh (order 2 returns NaN — see
  `knowledge/06-numerics-fem/02-axisymmetric-weak-forms.md#22-quadrature-verified-experimentally`). **[tested: tests/tier1/test_charge_quadrature.py::test_qr03_an_explicit_rule_below_num07_s_floor_is_refused]**
- Packing fraction `Σ_j N_A a_j³ c_j < 1` enforced.
- Case-file schema round-trips; mesh quality gates fire on known-bad input.

---

