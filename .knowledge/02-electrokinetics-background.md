# Electrokinetics background — double layers, PB, electro-osmosis, selectivity, conductance

**Status:** background. Sources: CC-BY-4.0 thesis `willemsk/phdthesis-text` —
`chapters/electrostatics/electrostatics.tex` (ch. 4) and `chapters/nanopores/nanopores.tex` (ch. 2,
§`sec:np:physical_perspective`, where this thesis actually develops the EDL/EOF/access-resistance theory),
plus a few definitions from `chapters/transport/transport.tex` (ch. 6). Governing equations are **not**
repeated here — see `01-physics-epnpns.md`. Items marked **[std]** are standard results the thesis does *not*
state; they are needed by the software but must not be attributed to the thesis.

## 1. The electrical double layer

**Bjerrum length** — separation at which Coulomb energy between two elementary charges equals `kB*T`
[`eq:nanopores_bjerrum_length`]: `lambda_B = e^2/(4*pi*eps0*eps_r*kB*T) ≈ 0.7 nm` (water, room T). Comparable
to the radius of many biological pores, so electrostatics is never a perturbation here.

**Debye length** — thickness of the diffuse layer and the screening length [`eq:nanopores_debye_length`]:

```
lambda_D = sqrt( eps0*eps_r*kB*T / (e^2*N_A*sum_i c_i0*z_i^2) ) = (8*pi*lambda_B*N_A*I)^(-1/2)
I = 0.5*sum_i c_i0*z_i^2      (ionic strength)
```

`c_i0` bulk molar conc., `z_i` valence. `lambda_D ∝ I^(-1/2)`:

| NaCl (M) | 0.01 | 0.05 | 0.1 | 1 | >3 |
|---|---|---|---|---|---|
| `lambda_D` (nm) | 3.1 | 1.4 | 0.97 | 0.31 | <0.2 |

**Gouy–Chapman–Stern structure** (the thesis names the layers, not the model,
`fig:nanopores_edl_overview`): a **Stern** layer of semi-permanently bound, partly dehydrated counterions
(thickness `lambda_S ~ 0.1 nm`, one ionic radius — used only in the EDL relaxation time; ePNP-NS has **no
explicit Stern layer**), and a **diffuse (Gouy–Chapman)** layer of mobile excess counterions / depleted
co-ions decaying over ~`lambda_D`.

**Surface vs zeta potential [std].** `psi_0` is the potential at the wall; `zeta` is the potential at the
hydrodynamic shear plane (~Stern/diffuse boundary) and is what electrokinetic experiments report,
`|zeta| <= |psi_0|`. The thesis never uses `zeta`: solving the full ion distribution on an atomistic charge
map makes zeta an *output* diagnostic. Any zeta the software reports must state its shear-plane convention.

**Grahame equation [std]** — converts between fixed-charge and fixed-potential wall specifications (symmetric
z:z salt): `sigma_s = sqrt(8*eps0*eps_r*kB*T*c0*N_A) * sinh(z*e*psi_0/(2*kB*T))`; linearised
`sigma_s = eps0*eps_r*psi_0/lambda_D`.

**Confinement.** In a ~1 nm-radius pore EDLs overlap even at 0.1 M [§`sec:np:edl`], causing concentration
depletion/enrichment, surface conductance, permselectivity and pre-concentration. The interior is then not
electroneutral anywhere — the regime where bulk-fitted electrolyte properties are least justified (01 §4) and
where every thin-EDL formula below fails.

**Timescale separation.** EDL relaxation `tau ~ lambda_D*L/D` [`eq:nanopores_relaxation_time`] is 0.1–10 ns
(4.5 ns for L=10 nm, D=2 nm²/ns, `lambda_D`=1 nm) versus 1 µs–1 s analyte dwell times. This is the formal
justification for solving ions and water at **steady state** with the analyte fixed [§`sec:np:dynamics`].

## 2. Poisson–Boltzmann and Debye–Hückel

```
laplacian(phi) = -(1/(eps0*eps_r)) * sum_i [ N_A*c_i0*z_i*e*exp(-z_i*e*phi/(kB*T)) ]
```

[`eq:nanopores_pbe`]. APBS's normalised form (potential in `kT/e`) splits charge into fixed and mobile; for a
1:1 salt the mobile part collapses to `rho_mob = -kappa_bar^-2 * sinh(phi)`, where `kappa_bar` absorbs bulk
concentration **and an ion-accessibility mask** excluding ions from the protein interior
[`eq:electrostatics_scdm_salt`].

**Linearised PB (Debye–Hückel)**, valid for `|z_i*e*phi|/(kB*T) < 1` (`|phi| < ~26 mV`):
`laplacian(phi) = kappa^2*phi`, `kappa = 1/lambda_D` [`eq:nanopores_pbe_linear`].

> **Erratum.** The thesis prints the prefactor with `z_i` to the *first* power; that sum is zero for any
> electroneutral bulk. It must be `z_i^2`, which is what reproduces `kappa^2`. Implement `z_i^2`.

**Validity** [§`sec:np:edl`]: PB is mean-field — point charges in a structureless dielectric, no ion–ion
correlations. Care is needed above a few `kT/e` surface potential and for anything needing specific ion–ion
or ion–water chemistry. Nevertheless PB captured measured selectivity reversals and DNA-translocation
ability across ClyA, FraC and PlyAB variants.

**Energy.** `G(phi,eps) = ∫_Omega [ rho_fix*phi - (eps/2)*(grad phi)^2 - kappa_bar^-2*(cosh(phi)-1) ] dr`
[`eq:pbe_energy`]; the interaction energy of placing a particle in a pore is the three-solve difference
`dG_elec = G(pore+part) - G(pore) - G(part)` [`eq:electrostatic_energy`]. Magnitudes: 38 kT for ssDNA through
WtFraC vs 14 kT through ReFraC; ~60 kT for dsDNA through ClyA's constriction at 0.15 M, ~10 kT at 2.5 M.
Its gradient splits into three named terms [`eq:nanopores_electrostatic_force`]: **RF** (reaction field ≡
Coulomb), **DB** (dielectric boundary, from `grad eps`; repulsive when a low-`eps_r` analyte displaces water
in a constriction), and **IB** (ionic boundary — EDL screening, always reduces RF).

## 3. PB vs PNP — equilibrium vs non-equilibrium

PB has no diffusion coefficients and cannot represent flux under bias; PNP(-NS) adds dynamics and PB is its
zero-flux limit. Setting `J_i = 0`, `u = 0` in the NP flux (01 §2.2, no steric term):

```
D_i*grad(c_i) + z_i*mu_i*c_i*grad(phi) = 0   =>   c_i = c_i0 * exp( -z_i*phi / (D_i/mu_i) )
```

This is Boltzmann **only if** `D_i/mu_i = V_T = kB*T/e = R*T/F = 25.693 mV` (Nernst–Einstein). The thesis
warns Nernst–Einstein holds only at infinite dilution and "should not be used at finite concentrations (even
though it often is)" [text after `eq:nanopores_nernst_planck`].

> **Consequence, computed from `data/corrections/willems2020_nacl.yaml`:** ePNP-NS fits `D_i(c)` and `mu_i(c)`
> to independent datasets, so their ratio drifts from `V_T`. `D_Na/mu_Na` = 26.2, 31.1, 37.7, 42.8 mV at
> `<c>` = 0.001, 0.15, 1.0, 3.0 M (i.e. up to 1.67×`V_T`); `D_Cl/mu_Cl` = 26.1, 29.1, 31.4, 32.8 mV.
> **The equilibrium limit of ePNP-NS is therefore not a Boltzmann distribution**, and the two species do not
> even share an effective thermal voltage. A "Poisson–Boltzmann" mode is a genuinely different model, not the
> PNP solver at zero bias. Give PB its own `kT/e`, and print `D_i/mu_i` vs `V_T` as a solve-time diagnostic.

Practically: PB is solved over the whole domain (protein + membrane included), needs no flux BCs, and takes
only fixed charge, bulk concentration and the permittivity map; it yields potentials and energies. Only
PNP-NS yields current, selectivity and flow.

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

## 5. Electrophoresis and the force on a charged body

| Force | Expression | Label |
|---|---|---|
| Electrophoretic | `F_ep = ∫_V rho*E dV = q*E` | `eq:nanopores_lorentz_force` |
| Dielectrophoretic | `F_dep = (p·grad)E` | `eq:nanopores_dep_force` |
| Electric, exact | `F_ele = ∮_Gamma (T_M·n) dGamma`, `T_M = eps*E*E - 0.5*eps*(E·E)*Id` | `eq:nanopores_electric_force` |
| Drag, 1st order | `F_drag = -6*pi*eta*R_h*u` | `eq:nanopores_drag_force` |
| Hydrodynamic, exact | `F_hyd = ∮_Gamma (T_H·n) dGamma`, `T_H = p*Id - eta*(grad u + grad u^T)` | `eq:nanopores_hydrodynamic_force` |

`q*E` is strictly valid only in a uniform field. The **stress-tensor forms assume nothing about particle shape
or field uniformity and are what to implement**; `T_H` also captures pressure build-up ahead of a
translocating particle, which Stokes drag does not. Typical in-pore EP/EO forces: **1–100 pN** (ClyA at
−50 mV: ~3 mV/nm → ~4 pN on a +10 e protein; a 5 nm sphere in 100 mm/s flow → ~4 pN). Reynolds ~5e-4, always
laminar. EP dominates for DNA; for proteins the balance is even or EO-dominated — which is how ClyA captures
proteins *against* the field.

**Electrophoretic mobility [std]:** `mu_ep = v_drift/E`; `q/(6*pi*eta*R_h)` in the thick-EDL (Hückel) limit,
`eps0*eps_r*zeta/eta` in the thin-EDL (Smoluchowski) limit — the exact negative of `mu_eo`. The thesis computes
forces directly instead. Do not use "effective charge" shortcuts without stating the EOF assumption: for dsDNA
in ClyA, EOF is estimated to halve it from −2 to −1 e/bp.

## 6. Selectivity, transport number, reversal potential

`t_Na = P_Na/(P_Na + 1) = G_Na/(G_Na + G_Cl)` [`eq:tna`] — the fraction of current carried by Na⁺;
`P_Na = G_Na/G_Cl` is the permeability ratio. `t > 0.5` cation-selective. Bulk NaCl `t_Na0 = 0.3963`.

Experimentally, `t` comes from the **reversal potential** `V_rev` (the bias at which `I = 0` under a cis/trans
salt gradient), converted via the **Goldman–Hodgkin–Katz** equation. The thesis lists three reasons this is
not the simulated quantity: GHK ignores EOF-carried flux; GHK assumes Nernst–Einstein at all concentrations;
and since selectivity depends on ionic strength, a gradient measurement reports selectivity at an undetermined
intermediate concentration. Example: measured `t_Na = 0.66` for ClyA vs simulated 0.57 at 1 M (cis) and 0.84
at 0.15 M (trans) — the measurement sits near their average. Simulated ClyA-AS is cation-selective up to
~2 M, bottoming at `t_Na = 0.45` at 5 M (still 1.27× bulk), and selectivity is voltage-dependent.

## 7. Ionic current rectification

`alpha(V_bias) = G(+V_bias)/G(-V_bias)` [`eq:icr`]. Requires **both** charged walls **and** axial geometric
asymmetry (intrinsic, or induced by gating/electrostriction). ClyA rectifies strongly (negative interior; cis
~6 nm vs trans ~3.3 nm entries). `alpha` rises monotonically with `|V_bias|`, but versus concentration is
**non-monotonic**, peaking at 0.15 M and decaying to 1 at saturating salt. The peak coincides with the
slope change of the negative-bias conductance — evidence of a mechanism change (co-ion exclusion) rather than
geometry. There is a matching EO rectification `alpha_Q = G_Q(+V)/G_Q(-V)`, passing through 1 near 0.45 M.

## 8. Access resistance and conductance decomposition

`R_total = R_pore + 2*R_access` [§`sec:np:potential`]. Access (a.k.a. convergence/spreading) resistance is the
cost of funnelling current from bulk into the aperture — a property of the reservoir, and it does not vanish
as the pore shortens.

```
R_pore   = 4*L/(pi*sigma*d^2)              R_access = 1/(2*sigma*d)
I        = dV*sigma*(4*L/(pi*d^2) + 1/d)^-1  ==  dV*sigma*2*pi*d_c
d_c      = (1/(2*pi)) * (4*L/(pi*d^2) + 1/d)^-1
```

`sigma` electrolyte conductivity (constant in bulk, **position-dependent in a pore**), `L` length, `d`
diameter. Profiles follow from `dphi/dz = I/(sigma*S(z))` with `S = pi*d^2/4` inside, `pi*z^2` outside
[`eq:nanopores_potential_profile`, `eq:nanopores_efield_profile`]: outside, `phi ∝ 1/z` and `E ∝ 1/z^2` (a
short-ranged but non-zero capture field); inside a uniform cylinder `E` is constant; in a real pore `E`
tracks `1/S(z)`, so a 2× diameter change is a 4× field change. Baseline: d = 3 nm, L = 10 nm, 0.15 M KCl →
G ≈ 1 nS → 100 pA at 0.1 V ≈ 6e8 ions/s.

| Decomposition | Terms |
|---|---|
| Series | `1/G = R_pore + 2*R_access` |
| Per species | `G = G_Na + G_Cl` (gives `t_Na`) |
| Bulk vs surface | bulk-electrolyte + EDL/counterion conduction; ClyA is bulk-dominated above ~0.15 M, counterion-dominated below (co-ions excluded) |
| Per mechanism | migration + diffusion + convection (the three NP flux terms); the convective term is absent from GHK and is not negligible |

## 9. Quantities the software must compute

| Quantity | Definition | Model |
|---|---|---|
| `I` | `∫ F*sum_i z_i*(n·J_i) dS` on a reservoir boundary | PNP-NS |
| `G`, per-species `G_i` | `I/V_bias` | PNP-NS |
| `t_Na` | `G_Na/(G_Na+G_Cl)` | PNP-NS |
| `alpha` | `G(+V)/G(-V)` | PNP-NS, both signs |
| `V_rev` | bias where `I = 0` under asymmetric reservoirs | PNP-NS + root find |
| `Q`, `G_Q`, `alpha_Q` | `∫(n·u) dS` [`eq:flowrate`], `Q/V_bias` | NS |
| Fields `phi`, `c_i`, `u`, `p` | primary unknowns | PNP-NS |
| `lambda_D`, local `<c>`, EDL charge | diagnostics; also drive the corrections | any |
| On-axis `phi(z)` vs circuit model | access-resistance sanity check | PNP-NS |
| Force on analyte | Maxwell + hydrodynamic stress-tensor surface integrals | PNP-NS |
| `dG_elec` landscape | `G(pore+part) - G(pore) - G(part)` | **PB** |
| Averaged potential maps | radial `phi_r(r,z)`, cylindrical `phi_z(z)` | **PB** |

The last two are why PB must be a first-class selectable model: the whole electrostatics chapter — selectivity
rationalisation, DNA translocation barriers, pore-engineering guidance — rests on PB alone, at a fraction of
the cost of a PNP-NS solve.
