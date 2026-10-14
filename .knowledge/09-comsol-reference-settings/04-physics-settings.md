---
type: Reference Settings
title: C. Physics settings
---

## C. Physics settings

### C.1 Stabilisation — RESOLVED: it was ON, in both interfaces

**Transport of Diluted Species (§2.4.1)** — *Consistent stabilization*:

| Setting | Value |
|---|---|
| **Streamline diffusion** | **On** |
| **Crosswind diffusion** | **On** |
| **Equation residual** | **Approximate residual** |
| **Crosswind diffusion type** | **Do Carmo and Galeão** |
| Streamline diffusion type | NOT IN REPORT (COMSOL 5.4 TDS default: *Streamline upwind Petrov–Galerkin*) |
| *Inconsistent stabilization*: isotropic diffusion | **Off** |
| Advanced: **convective term** | **Conservative form** |

**Laminar Flow (§2.5.1)** — *Consistent stabilization*:

| Setting | Value |
|---|---|
| **Streamline diffusion** | **On** |
| **Crosswind diffusion** | **On** |
| Streamline / crosswind type, tuning parameters | NOT IN REPORT |
| *Inconsistent stabilization*: isotropic diffusion | **Off** |
| Use pseudo time stepping for stationary equation form | Automatic from physics |
| CFL number expression | Automatic |

Both terms are assembled — the report prints the weak contributions:

| Weak expression | Integration order | Selection |
|---|---|---|
| `2*tds.streamline*(isScalingSystemDomain==0)*pi*r` | 4 | Domain 1 |
| `2*tds.crosswind*(isScalingSystemDomain==0)*pi*r` | **6** | Domain 1 |
| `2*spf.streamlinens*pi*r` | 2 | Domain 1 |
| `2*spf.crosswindns*pi*r` | 2 | Domain 1 |

The internal definitions of `tds.streamline`, `tds.crosswind`, `spf.streamlinens`,
`spf.crosswindns` are **NOT IN REPORT** — COMSOL does not export them.

**Pseudo-time stepping was effectively inactive.** The report lists the help variable
`spf.usePseudoTimeStepping = 0`, and the pseudo-time weak term is gated on it:
`2*(spf.usePseudoTimeStepping>0)*spf.rho*spf.tsti*(-(u-nojac(u))*test(u)-(w-nojac(w))*test(w))*pi*r`
→ identically zero. `spf.localCFLvalue` and `spf.geometryLengthScale = 6.25 × 10⁻⁸ m` are defined
but unused. **[verified]**

**Consequence.** The published currents were computed **with** consistent stabilisation in both the
ion transport and the flow. The open question in `.knowledge/06-numerics-fem/04-stabilisation.md` is settled against our
current policy. Note also that the flow uses **P1+P1** (equal-order) elements, which are LBB-unstable
without stabilisation — for the Navier–Stokes part the stabilisation is *load-bearing*, not cosmetic.

### C.2 Discretisation order per field

| Field | Shape function | Domain |
|---|---|---|
| `V` electric potential | **Lagrange, quadratic** | 1–3 (reservoir, pore, membrane) |
| `cpos`, `cneg` | **Lagrange, quadratic** | 1 (reservoir) |
| `u`, `w` velocity | **Lagrange, linear** | 1 |
| `p` pressure | **Lagrange, linear** | 1 |

Laminar Flow interface setting: **Discretization of fluids = P1 + P1**. Electrostatics: *Electric
potential = Quadratic*. TDS: *Concentration = Quadratic*. Component *Geometry shape order =
Automatic*; the solver log reports **Geometry shape order: Linear**.

Weak-form integration orders as exported: Electrostatics 4; TDS diffusive/migration/convective 4;
TDS crosswind 6; steric flux 4; Laminar Flow momentum, continuity, stabilisation and density
continuity 2.

### C.3 Wall-distance operator

Not COMSOL's wall-distance interface. A **General Extrusion** coupling with closest-point search:

| Item | Value |
|---|---|
| Coupling type | **General extrusion** |
| Operator name | **`wde`** |
| Entity level / selection | Boundary; *Wall distance boundary* = **Boundaries 7–29, 31–152, 154–194** (the `Nanopore` selection) |
| Destination map | `{r, z}` |
| Mesh search method | **Closest point** |
| Distance variable | `wdf.wd = sqrt((r - wde(r))^2 + (z - wde(z))^2)` [m] |
| Dimensionless | `wdf.dwd = wdf.wd[1/nm]` |

The selection is the **pore surface only** — the membrane boundaries are excluded, confirming the
KB convention for `d`. **[verified]**

Two further couplings:

| Operator | Type | Selection | Maps |
|---|---|---|---|
| `pre` (pore radius extrusion) | General extrusion | Boundaries 7–17, 19, 21–22, 24, 32, 37–65, 67–69, 73–78, 80–91, 93–99, 104–107, 109–111, 114–119 | dest `{z, }`, source `{z, }`, closest point |
| `cip` (central integration projection) | General projection | Domain 1 | dest `z`, source `{z, r}` |

### C.4 Correction functions — exact COMSOL expressions

Wall-distance factors (`wdf`), whole model:

| Variable | Expression |
|---|---|
| `wdf.enable` | `if(enable_wdf == 0, 0, 1)` |
| `wdf.D_wd_cpos`, `wdf.D_wd_cneg` | `if(wdf.enable == 0, 1, 1 - exp(-0.62e1*(wdf.dwd + 0.01)))` |
| `wdf.mu_wd_cpos` | `wdf.D_wd_cpos` (mobility reuses the diffusion factor) |
| `wdf.mu_wd_cneg` | `wdf.D_wd_cneg` |
| `wdf.eta_wd` | `if(wdf.enable == 0, 1, 1 + exp(-wdf.a*(wdf.dwd - wdf.r0)))` |
| `wdf.rho_wd` | `if(wdf.enable == 0, 1, 1)` — **density wall correction not implemented** |
| `wdf.a` | 3.36096 |
| `wdf.r0` | 0.14716 |

`0.62e1` = **6.2 nm⁻¹**, with **`+0.01`** inside the exponent. Confirms trap 1 of `.knowledge/00-orientation/02-the-five-things-most-likely-to-trip-you.md` exactly.
**[verified]**

Concentration factors (`cdf`), whole model:

| Variable | Expression |
|---|---|
| `cdf.dcpos` | `if(cpos<1e-6[M], 1e-6, if(cpos>cmax, cmax[L/mol], cpos[L/mol]))` |
| `cdf.dcneg` | as above with `cneg` |
| **`cdf.dcav`** | **`(cdf.dcpos + cdf.dcneg)*0.5`** — arithmetic mean, clamped to [10⁻⁶ M, `cmax`] |
| `cdf.D_cpos` | `if(enable_cdf_mob == 0, 1, 1/(1 + d1_cpos*cdf.dcav^0.5 + d2_cpos*cdf.dcav + d3_cpos*cdf.dcav^(3/2) + d4_cpos*cdf.dcav^2))` |
| `cdf.D_cneg` | as above with `d*_cneg` |
| `cdf.L_cpos` / `cdf.L_cneg` | same form with `l*_cpos` / `l*_cneg` |
| `cdf.rho_c` | `if(enable_cdf_rho == 0, 1, 1 + rho1*cdf.dcav + rho2*cdf.dcav^2)` |
| `cdf.eta_c` | `if(enable_cdf_eta== 0, 1, 1 + eta1*cdf.dcav^0.5 + eta2*cdf.dcav + eta3*cdf.dcav^2 + eta4*cdf.dcav^3.5)` |
| `cdf.epsr_c` | `if(enable_cdf_epsr == 0, 1, 1 - (1 - epsr_ms/epsr0)*(coth((3*epsr_alpha*cdf.dcav)/(epsr0 - epsr_ms)) - (epsr0 - epsr_ms)/(3*epsr_alpha*cdf.dcav)))` |

The clamp `cmax = 5.3 M` caps every concentration correction; `cdf.dcav` is the **average ion
concentration**, confirming ruling 3 of `.knowledge/00-orientation/05-author-rulings-2026-08-these-override.md`. **[verified]**

Assembled local properties:

| Variable | Expression | Unit |
|---|---|---|
| `D_cpos` | `d0_cpos*cdf.D_cpos*wdf.D_wd_cpos` | m²/s |
| `D_cneg` | `d0_cneg*cdf.D_cneg*wdf.D_wd_cneg` | m²/s |
| `mu_cpos` | `(1/F_const^2) * l0_cpos*cdf.L_cpos*wdf.mu_wd_cpos` | s·mol/kg |
| `mu_cneg` | `(1/F_const^2) * l0_cneg*cdf.L_cneg*wdf.mu_wd_cneg` | s·mol/kg |
| `eta` | `eta0*cdf.eta_c*wdf.eta_wd` | Pa·s |
| `rho` | `rho0*cdf.rho_c*wdf.rho_wd` | kg/m³ |
| `epsr_water` | `epsr0*cdf.epsr_c` | 1 |
| `epsr_nanopore` | **20** | 1 |
| `epsr_membrane` | **3.2** | 1 |

`l0_i = (e_const^2*N_A_const)/(k_B_const*T_system)*d0_i` — mobility is derived from the
infinite-dilution diffusivity by Einstein, then the *independent* concentration fit `cdf.L_i`
breaks the relation at finite `c`. Consistent with trap 4 of `.knowledge/00-orientation/02-the-five-things-most-likely-to-trip-you.md`.

### C.5 Parameters (§1.1)

| Name | Expression | Value |
|---|---|---|
| `V_bias` | `-150[mV]` | −0.15 V |
| `T_system` | `25[degC]` | 298.15 K |
| `c_salt`, `c_cis`, `c_trans` | `500[mM]` | 500 mol/m³ |
| `r_reservoir` | `250[nm]` | 2.5 × 10⁻⁷ m |
| `d_membrane` | `2.8[nm]` | 2.8 × 10⁻⁹ m |
| `enable_wdf`, `enable_cdf`, `enable_smp`, `enable_cdf_rho`, `enable_cdf_epsr`, `enable_cdf_eta`, `enable_cdf_mob` | 1 | all corrections on |
| `a_cpos`, `a_cneg` | `0.5[nm]` | steric diameter → 13.284 M cap |
| `a_sol` | `0.311[nm]` | water → 55.2 M |
| `z_cpos`, `z_cneg` | 1, −1 | |
| `epsr0` | 78.15 | |
| **`epsr_alpha`** | **11.5** | total excess polarisation |
| **`epsr_ms`** | **30.08** | limiting permittivity at saturation |
| `rho0` | `0.997[g/cm^3]` | 997 kg/m³ |
| `rho1`, `rho2` | 4.047 × 10⁻², −6.149 × 10⁻⁴ | |
| `eta0` | `8.904e-4[Pa*s]` | |
| `eta1`…`eta4` | 7.558 × 10⁻³, 7.769 × 10⁻², 1.192 × 10⁻², 5.951 × 10⁻⁴ | |
| `d0_cpos`, `d0_cneg` | 1.334 × 10⁻⁹, 2.032 × 10⁻⁹ m²/s | |
| `d1…d4_cpos` | 0.202, −0.3048, 0.219, −0.03124 | |
| `d1…d4_cneg` | 0.149, −0.04933, 0.03392, 0.01431 | |
| `l1…l4_cpos` | 0.7907, −0.3529, 0.1459, 0.009241 | |
| `l1…l4_cneg` | 0.6289, −0.4286, 0.2123, −0.01068 | |
| `cmax` | `5.3[M]` | 5300 mol/m³ |

### C.6 Steric flux (size-modified PNP)

Implemented as **two Weak Contribution nodes** on Domain 1 — *Steric Flux Vector (cpos)* (§2.4.8)
and *(cneg)* (§2.4.9) — not through a built-in feature. Quadrature: *automatic*. Assembled at
integration order 4.

```
smp.enable*smp.alpha_cpos*cpos*(
    smp.rad3_cpos*((-tds.D_cposrr*cposr - tds.D_cposrz*cposz)*test(cposr)
                 + (-tds.D_cposzr*cposr - tds.D_cposzz*cposz)*test(cposz))
  + smp.rad3_cneg*((-tds.D_cposrr*cnegr - tds.D_cposrz*cnegz)*test(cposr)
                 + (-tds.D_cposzr*cnegr - tds.D_cposzz*cnegz)*test(cposz)))
```

(the `cneg` node is the same with `cpos`↔`cneg` swapped in the prefactor and diffusivities).

| Variable | Expression |
|---|---|
| `smp.rad3_i` | `N_A_const*a_i^3` (m³/mol) |
| `smp.k_i` | `smp.rad3_i/smp.rad3_solvent` |
| `smp.conc_rad3_sum` | `cpos*smp.rad3_cpos + cneg*smp.rad3_cneg` |
| **`smp.alpha_i`** | **`smp.k_i/(1 - smp.conc_rad3_sum)`** |
| `smp.conc_max_i` | `1/smp.rad3_i` |

Also defined (diagnostics, not assembled): `smp.sflux_*` flux components, `smp.nsflux_*`,
`smp.sfluxMag_*`, `smp.sfluxRes_*`, and chemical potentials
`muchem_i = pot_es_i + pot_ch_i + pot_st_i` with
`pot_st_i = -k_B_const*T_system*smp.k_i*log(1 - cpos*smp.rad3_cpos - cneg*smp.rad3_cneg)`.

Transcription defect: `smp.sfluxRes_cpos` contains `tds.D_cnegzz*cposz` where the pattern requires
`tds.D_cposzz*cnegz`. It is a **post-processing residual diagnostic only** — it does not enter any
weak form, so results are unaffected. **[verified]**

### C.7 Fixed charge

| Item | Value |
|---|---|
| Variable | `scd_pore = if(r<0.01[nm], 0, e_const*rhoq_pore(r, z)/(2*pi*r))` [C/m³] |
| Source | Interpolation function **`rhoq_pore`** ("Gridded charge of pore"), arguments m, m, function unit **1/m²** |
| Extrapolation | **Specific value** |
| Applied by | *Space Charge Density (nanopore)* (§2.3.12), **Domains 1–3** |
| Weak form | `-2*es.scd2.rhoq*test(V)*es.d*pi*r`, order 4 |
| Ion charge | `scd_ions = F_const*(scd.cpos*tds.z_cpos + scd.cneg*tds.z_cneg)`, *Space Charge Density (ions)* (§2.3.11), **Domain 1 only** |
| Positivity clamp | `scd.cpos = if(cpos<0, 0, cpos)`, `scd.cneg = if(cneg<0, 0, cneg)` |

The `2πr` divisor converts a per-length gridded charge into a volumetric density; the `r<0.01 nm`
guard removes the axis singularity. The clamp means **negative concentrations never feed Poisson**
during Newton iterations.

### C.8 Body force, couplings, boundary conditions

| Item | Value |
|---|---|
| Body Force (§2.5.8) | `spf.Fr = es.Er*scd_ions`, `spf.Fz = es.Ez*scd_ions` |
| Dielectric-gradient force | **Absent** — confirms trap 3 of `.knowledge/00-orientation/02-the-five-things-most-likely-to-trip-you.md`. **[verified]** |
| Density Continuity (§2.5.9) | weak contribution `(u*d(spf.rho, r) + w*d(spf.rho, z))*test(p)` |
| Multiphysics | Potential Coupling 1 (es → tds); Flow Coupling 1 (spf → tds) |
| Ground | Boundaries 196, 198 |
| Electric Potential `V_bias` | Boundaries 195, 197 |
| Concentration BC | Boundaries 195–196, `{if(z<0, c_trans, c_cis), if(z<0, c_trans, c_cis)}`, elemental constraints |
| No Flux | Boundaries 7–28, 30, 32, 37–65, 67–69, 73–78, 80–91, 93–99, 104–107, 109–111, 114–121, 134, 136–139, 143–194; *Include convection = Off* |
| Wall | same selection, **No slip**, translational velocity automatic from frame |
| Open Boundary | Boundaries 195–196, **Normal stress = 0** |
| Axial Symmetry | Boundaries 1–6 (all three interfaces) |
| Constraints | Elemental; weak constraints Off; reaction terms on all physics (symmetric) |
| Initial guess | `V_init` linear ramp inside pore; `cpos_init`/`cneg_init` linear ramp inside pore, bulk outside |

### C.9 Geometry (§2.2)

| Item | Value |
|---|---|
| Space dimension | 2 (axisymmetric) |
| Domains / boundaries / vertices | 3 / 198 / 196 |
| Reservoir | half-circle, radius `r_reservoir` = 250 nm, sector 180°, rotation 270° |
| Membrane | polygon, thickness `d_membrane` = 2.8 nm, inner radius 2 → 3.5 nm taper, out to 250 nm |
| Pore | 190-vertex polygon, z from −1.85 to +12.25 nm |
| Pore extent variables | `z_cis = 12.25[nm]`, `z_trans = -1.85[nm]` |

### C.10 Quantities of interest (§5.1)

| Expression | Description |
|---|---|
| `F_const*(tds.z_cpos*tds.ntflux_cpos+tds.z_cneg*tds.ntflux_cneg)` | current |
| `.../V_bias` | conductance (also per-ion variants) |
| `u*nr+w*nz` | water current; `/V_bias` → water conductance |
| Integration order | **4** |

`tds.ntflux_i = tds.bndFlux_i = if(r>0.001/sqrt(sqrt(mean(emetric2))), -0.5*dflux_spatial(c_i)/(pi*r), NaN)`
— i.e. the **variational/reaction boundary flux**, not a cross-section integral of the CG flux.
This matches the rule in `CLAUDE.md` and `.knowledge/06-numerics-fem/07-quantities-of-interest-and-the-flux-trap.md`. The evaluation boundary is
**NOT IN REPORT**. **[verified]**

Pore averages use `is_inside_pore`, `is_inside_pore_bulk` (`wdf.wd > 0.5 nm`) and
`is_inside_pore_surface` (`wdf.wd <= 0.5 nm`), integration order 4.

---

