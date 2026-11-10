---
type: Background
title: 2. Poisson–Boltzmann and Debye–Hückel
description: "The Poisson-Boltzmann equation, its APBS normalised form, the Debye-Hückel linearisation and its validity, and the electrostatic energy."
tags:
- electrokinetics
- background
sources:
- id: thesis
  resource: https://github.com/willemsk/phdthesis-text
  title: Willems, PhD thesis (LaTeX source)
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
---

## 2. Poisson–Boltzmann and Debye–Hückel

```
laplacian(phi) = -(1/(eps0*eps_r)) * sum_i [ N_A*c_i0*z_i*e*exp(-z_i*e*phi/(kB*T)) ]
```

[`eq:nanopores_pbe`] **[verified][^thesis]**. APBS's normalised form (potential in `kT/e`) splits charge into fixed and mobile; for a
1:1 salt the mobile part collapses to `rho_mob = -kappa_bar^-2 * sinh(phi)`, where `kappa_bar` absorbs bulk
concentration **and an ion-accessibility mask** excluding ions from the protein interior
[`eq:electrostatics_scdm_salt`] **[verified][^thesis]**.

**Linearised PB (Debye–Hückel)**, valid for `|z_i*e*phi|/(kB*T) < 1` (`|phi| < ~26 mV`):
`laplacian(phi) = kappa^2*phi`, `kappa = 1/lambda_D` [`eq:nanopores_pbe_linear`] **[verified][^thesis]**.

> **Erratum.** The thesis prints the prefactor with `z_i` to the *first* power; that sum is zero for any
> electroneutral bulk. It must be `z_i^2`, which is what reproduces `kappa^2`. Implement `z_i^2`.

**Validity** [§`sec:np:edl`]: PB is mean-field — point charges in a structureless dielectric, no ion–ion
correlations **[verified][^thesis]**. Care is needed above a few `kT/e` surface potential and for anything needing specific ion–ion
or ion–water chemistry (unverified). Nevertheless PB captured measured selectivity reversals and DNA-translocation
ability across ClyA, FraC and PlyAB variants [ch. 3, `electrostatics.tex`] (unverified).

**Energy.** `G(phi,eps) = ∫_Omega [ rho_fix*phi - (eps/2)*(grad phi)^2 - kappa_bar^-2*(cosh(phi)-1) ] dr`
[`eq:pbe_energy`]; the interaction energy of placing a particle in a pore is the three-solve difference
`dG_elec = G(pore+part) - G(pore) - G(part)` [`eq:electrostatic_energy`] **[verified][^thesis]**. Magnitudes: 38 kT for ssDNA through
WtFraC vs 14 kT through ReFraC; ~60 kT for dsDNA through ClyA's constriction at 0.15 M, ~10 kT at 2.5 M **[verified][^thesis]**.
Its gradient splits into three named terms [`eq:nanopores_electrostatic_force`]: **RF** (reaction field ≡
Coulomb), **DB** (dielectric boundary, from `grad eps`; repulsive when a low-`eps_r` analyte displaces water
in a constriction), and **IB** (ionic boundary — EDL screening, always reduces RF) **[verified][^thesis]**.

[^thesis]: Willems, PhD thesis, LaTeX source, `github.com/willemsk/phdthesis-text` at `43d0f0f`; the `.tex` file and label beside each claim locate it.
