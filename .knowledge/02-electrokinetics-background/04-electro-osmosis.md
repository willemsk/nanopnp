---
type: Background
title: 4. Electro-osmosis
description: Electro-osmosis in a charged pore.
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

## 4. Electro-osmosis

The tangential field acts on the EDL's net charge and friction transfers it to water
[`eq:nanopores_edl_force`]: `f_EDL = rho_ion*E`, `rho_ion = F*sum_i z_i*c_i` — the same body force already in
the ePNP-NS momentum equation. Analytical reference (charged cylinder, low surface potential)
[`eq:nanopores_eof_rate`]:

```
Q = -(pi*a^2/(eta*kappa)) * H(kappa*a) * E_z * sigma_s ,   H(x) = I_2(x)/I_1(x)
```

`a` pore radius, `eta` viscosity, `kappa = 1/lambda_D`, `sigma_s` wall charge density, `I_n` modified Bessel
functions; `H` is the EDL-overlap correction.

- **Thin EDL** (`kappa*a >> 1`): `H -> 1`. Substituting the linearised Grahame relation
  `sigma_s = eps*kappa*zeta` recovers **Helmholtz–Smoluchowski [std]**: slip velocity
  `u_slip = -(eps0*eps_r*zeta/eta)*E_t`, EO mobility `mu_eo = -eps0*eps_r*zeta/eta`, plug flow.
- **Thick EDL** (`kappa*a <~ 1`): `H < 1`, overlapping layers, no plug flow, thin-EDL formulas invalid.
  `Q ∝ kappa^-1 ∝ I^(-1/2)` diverges as `I -> 0` — an artefact of the infinite-cylinder assumption; real
  pores are limited by end effects, the hydrodynamic analogue of access resistance.
- **Direction:** with the field for negative walls, against it for positive walls.
- **Axial profile:** `v(z) = Q/S(z)` [`eq:nanopores_eof_velocity`] — velocity scales with inverse local
  cross-section and decays as `1/z^2` outside the pore.

**Simulated reality (ClyA-AS, ePNP-NS)** [transport.tex]: at −100 mV / 0.5 M, centre-line water velocity is
~0.07 m/s in the lumen, ~0.21 m/s in the constriction. The radial profile is **parabolic, not plug**, at
low/moderate salt (EDL overlap makes the body force fill the cross-section, like Stokes flow), flattening to
plug only above ~0.5 M. EO conductance `G_Q = Q/V_bias` peaks non-monotonically near 0.5 M.

**Flow reversal.** Reversing wall charge reverses EOF: ReFraC's D10R flips the constriction potential from
≈−2.5 to ≈+5 kT/e, reversing both selectivity and EOF [§`sec:elec:frac`]. Where different pore regions carry
opposite charge the contributions compete — the "electro-osmotic tug of war" in PlyAB-R (positive
constriction vs negative lumen): net direction ambiguous, magnitude certainly suppressed, enough for
electrophoresis to win [§`sec:elec:plyab`].

**Slip length** `b_s` [§`sec:np:eof`]: 0 for rough hydrophilic protein walls, →∞ for carbon nanotubes; for
biological pores "closer to 0" — justifying the no-slip BC.

**Independent water-flux estimate** from selectivity alone [`eq:water_flux_permeability`]:
`J_w = N_w*(I/e)*(1 - P_K/P_Cl)/(1 + P_K/P_Cl)`, `v = J_w*V_w/(pi*R^2)` with `N_w ≈ 10` waters per ion,
`V_w ≈ 0.03 nm^3`. Verified: WtFraC at −50 mV gives 6.1e9 s⁻¹ → 58 mm/s (pH 7.5) and 2.5e9 s⁻¹ → 24 mm/s
(pH 4.5) at R = 1 nm. Underestimates the true flux (ignores EDL drag on bulk fluid); useful as a cheap
regression target.

