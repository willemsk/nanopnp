---
type: Erratum
title: 8. Errata in the source, with the arithmetic
description: "Six errata in the printed sources, numbered as §4.6's rows, each with the arithmetic that settles it."
tags:
- physics
- erratum
sources:
- id: thesis
  resource: https://github.com/willemsk/phdthesis-text
  title: Willems, PhD thesis (LaTeX source)
- id: comsol-report
  resource: COMSOL Multiphysics 5.4 model report of 22 May 2020
  title: COMSOL model report (5.4)
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:arithmetic
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier1/test_corrections.py::test_ver03_bulk_properties_at_the_validity_limit
  at: '2026-11-09T00:00:00Z'
- by: process:tests/tier1/test_corrections.py::test_ver03_ion_wall_function_check_values
  at: '2026-11-09T00:00:00Z'
- by: process:tests/tier1/test_corrections.py::test_ver04_nernst_einstein_holds_at_infinite_dilution
  at: '2026-11-09T00:00:00Z'
- by: process:tests/tier1/test_knowledge_arithmetic.py::test_permittivity_cap_gavish_and_buchner_at_5_3_m
  at: '2026-10-16T00:00:00Z'
---

## 8. Errata in the source, with the arithmetic

Six errata, numbered as the rows of `SPECIFICATION.md` §4.6, which states the correct forms. E1 to
E4 were found by reproducing the thesis's own stated check values, E5 against the literature value
for water, and E6 from the COMSOL model report. Numbers below are computed, not asserted.

**E1 — The D/μ wall function sign.** Thesis eq. 5.23 (`eq:epnpns_distance_d`) prints
`1 − exp(−P₁(d − P₂))`; Table 5.1 prints `1 − exp(−P₁(d + P₂))`. With `P₁ = 6.2`, `P₂ = 0.01`:

| form | `f(0)` | `f(0.75)` | matches stated 0.06 / 0.99? |
|---|---|---|---|
| **`(d + P₂)`** | **+0.0601** | **+0.9910** | **yes** |
| `(d − P₂)` | −0.0640 | +0.9898 | no — negative at the wall |

**The `+` form (Table 5.1) is correct.** The running text prints Simakov's minus, which the thesis's
own check values do not reproduce (`04-rationale-worth-preserving.md`).
**[tested: tests/tier1/test_corrections.py::test_ver03_ion_wall_function_check_values]**

**E2 — `P₁ = 6.2 nm⁻¹`, not 62 and not 0.62.**

| `P₁` | `f(0)` | `f(0.75)` |
|---|---|---|
| 62 | 0.4621 | 1.0000 |
| **6.2** | **0.0601** | **0.9910** |
| 0.62 | 0.0062 | 0.3757 |

Only 6.2 reproduces the thesis's stated 0.06 and 0.99. Using 0.62 would suppress ion motility
throughout a narrow pore (only 38 % of bulk at 0.75 nm from the wall) and would badly
under-predict conductance. Table 5.2 lists 6.2, sourced from Simakov 2010.
**[tested: tests/tier1/test_corrections.py::test_ver03_ion_wall_function_check_values]**

**E3 — Mobility exponent.** Table 5.1 lists `μ_Na⁰ = 5.192 × 10⁻⁴ m² s⁻¹ V⁻¹`; Table 5.2's note
(b) gives the scaling as `10⁻⁸`. Nernst–Einstein settles it: with `V_T = RT/F = 25.693 mV`,
`μ = D/V_T` gives 5.1922 × 10⁻⁸ (Na⁺) and 7.9089 × 10⁻⁸ (Cl⁻) — matching Table 5.2 to four
figures. **`10⁻⁸` is correct.** **[tested: tests/tier1/test_corrections.py::test_ver04_nernst_einstein_holds_at_infinite_dilution]**

**E4 — Viscosity cap.** The text states `η(c > 5.3 M) = 1.75 × 10⁻⁴ Pa s`. Evaluating the fit at
5.3 M gives **1.752 × 10⁻³ Pa s**. The printed value is also unphysical — it is *below* pure
water's 8.904 × 10⁻⁴, whereas salt raises viscosity. The other caps agree with the printed ones:
`ϱ(5.3 M) = 1194 kg m⁻³` (stated 1.19 × 10³), `D_Na = 8.11 × 10⁻¹⁰` (stated 0.81 × 10⁻⁹),
`D_Cl = 1.071 × 10⁻⁹` (stated 1.07 × 10⁻⁹). `D_Na` is 8.113 × 10⁻¹⁰ from the governing COMSOL
coefficients (PHY-12); the thesis's rounded ones give 8.127 × 10⁻¹⁰.
**[tested: tests/tier1/test_corrections.py::test_ver03_bulk_properties_at_the_validity_limit]**

**E5 — Viscosity scaling.** Table 5.2 lists `P₀ = 0.8904` for `η^c` under note (c), "Unit and
scaling: 10⁻⁴ Pa s", which implies `η⁰ = 8.904 × 10⁻⁵ Pa s`. Hai-Lang 1996, the table's own
source, gives 8.904 × 10⁻⁴ Pa s for water at 298.15 K, as Table 5.1 prints, and 8.904 × 10⁻⁵ is an
order of magnitude below water at that temperature: the scaling is `10⁻³` **[verified][^table-5-2]**.

**E6 — Which permittivity parameters were actually used (settled).** The text says the
authors "opted to make use of the parameters given by Gavish for NaCl at 298.15 K
(`P₁ = 30.08`, `P₂ = 11.5`)" rather than their own fit to Buchner 1999
(`P₁ = 29.50 ± 1.32`, `P₂ = 11.74 ± 0.21`). The stated cap `ε_r(5.3 M) = 42.12` is reproduced
by the **own fit**, not by Gavish's:

| parameters | `ε_r(5.3 M)` |
|---|---|
| **Gavish (30.08, 11.5)** | **42.67** ← what the model used |
| own fit (29.50, 11.74) | 42.13 ← matches the *stale* stated 42.12 |

Settled from the COMSOL model report (2026-08): the model parameter table and the solver log both
record `epsr_ms = 30.08`, `epsr_alpha = 11.5` — Gavish's values — so **those govern**
(`SPECIFICATION.md` §1.6 and §4.6 row 6). The printed `42.12` is the stale cap: it follows from the
authors' own Buchner fit, which the model did *not* use, so the cap with the parameters actually
used is `42.67`. An earlier author recollection favouring the Buchner fit is superseded by the
model file. The difference is ~1 % in `ε_r` at saturation and negligible below ~1 M **[tested: tests/tier1/test_knowledge_arithmetic.py::test_permittivity_cap_gavish_and_buchner_at_5_3_m]** **[verified][^comsol-report]**.

---

[^comsol-report]: COMSOL model report (5.4).
[^table-5-2]: Thesis `chapters/epnpns/epnpns.tex` at `43d0f0f`: Table 5.2, the `η^c` row and note (c)
    (lines 940-941 and 963); Table 5.1's `η⁰` = 8.904 × 10⁻⁴ Pa s, cited to Hai-Lang 1996 (line 480).
