# COMSOL reference settings — the published model report

Source: **`clya_epnp-ns_report.pdf`**, the COMSOL Multiphysics auto-generated model report for the
2D-axisymmetric ePNP-NS model of ClyA-AS, distributed as the ESI of Willems et al., *Nanoscale*
**12**, 16775–16795 (2020), DOI `10.1039/D0NR03114C`. Read in full from the project store.

| Field | Value |
|---|---|
| Report title | Nanopore ePNP-NS modelling |
| Author / company | Kherim Willems / imec vzw |
| Report date | 22 May 2020, 17:07 |
| Model file | `npgrid_clya_v8_NaCl_report.mph` (`D:\repos\comsol\clya\`) |
| COMSOL version | **5.4, build 388** |
| Products | COMSOL Multiphysics + **Chemical Reaction Engineering Module** |
| Unit system | SI; geometry length unit **nm** |
| Document length | **162 numbered pages** |

Report's own summary: *"the full implementation of the ePNP-NS equations … all used parameters,
variables, functions, geometries, solver settings and mesh settings needed to reproduce the
results."*

**Pagination correction.** This file previously recorded the ESI as 143 pages. 143 is the ToC page
number of §5 *Results*; the document runs to p. 162. **[verified]**

All values below are transcribed from the report. Anything the report does not print is marked
**NOT IN REPORT** — meaning COMSOL's default applied and was not exported, not that the setting
was off.

---

## 1. Document map

| § | Heading | Pages |
|---|---|---|
| 1.1 | Parameters | 3–5 |
| 2.1 | Definitions (variables, functions, couplings) | 6–21 |
| 2.2 | Geometry | 22–31 |
| 2.3 | Electrostatics | 31–66 |
| 2.4 | Transport of Diluted Species | 66–94 |
| 2.5 | Laminar Flow | 94–121 |
| 2.6 | Multiphysics | 121–122 |
| 2.7 | **Mesh** | 122–131 |
| 3 | **Study 1: Demo** (Stationary; Solver Configurations §3.2) | 132–134 |
| 4 | **Study 2: Full sweep** (Parametric Sweep §4.1; Solver Configurations §4.3) | 135–142 |
| 5.1 | Derived Values | 143–145 |
| 5.2–5.3 | Wall-distance / concentration correction plots | 146–154 |
| 5.4 | Mesh quality (skewness plots, **no numbers**) | 155–157 |
| 5.5–5.6 | EDL and pore charge density plots | 158–162 |

---

## A. Mesh (§2.7)

Mesh tag `mesh2`. Built from explicit Free Triangular + Size nodes, i.e. **user-controlled**; the
report never prints the sequence-type label. Sizes are in **nm**.

### A.1 Statistics

| Quantity | Value |
|---|---|
| Triangles | **120 917** |
| Edge elements | 1 879 |
| Vertex elements | 196 |
| **Minimum element quality** | **0.6378** |
| **Average element quality** | **0.9765** |
| Quality measure | NOT IN REPORT (§5.4 plots are labelled *skewness*) |
| **Degrees of freedom** | **NOT IN REPORT** |

Element type is triangular throughout — no quads, no mapped mesh.

### A.2 Size nodes

`Off` in the report means the override checkbox is cleared, so the value is inherited from the
global Size node and the printed number is inactive. Active values in **bold**.

| Node | Level / selection | Max size | Min size | Curvature | Narrow regions | Growth rate | Predefined |
|---|---|---|---|---|---|---|---|
| `size` **Size (global)** | whole model | **10** | **0.001** | **0.25** | NOT IN REPORT | **1.05** | Finer, Custom |
| `size1` Size (reservoir boundary) | Boundaries 195–196 | **5** | 0.025 (Off) | 0.25 (Off) | Off | 1.25 (Off) | Finer, Custom |
| `size5` **Size (pore boundary)** | Boundaries 7–29, 31–152, 154–194 (sel. *Nanopore*) | **0.05** | **0.001** | **0.25** | NOT IN REPORT | **1.05** | Finer, Custom |
| `size6` Size (symmetry axis inside pore) | Boundaries 3–4 | **0.075** | 0.04 (Off) | 0.25 (Off) | Off | Off | Finer, Custom |
| `size3` Size (reservoir domain) | Domain 1 (*Reservoir*) | 2.8 (Off) | 0.04 (Off) | 0.25 (Off) | Off | **1.04** | Finer, Custom |
| `size2` Size (pore domain) | Domain 2 (*Nanopore*) | **0.1** | 0.004 (Off) | 0.2 (Off) | Off | Off | Extremely fine, Custom |

`size3` and `size6` set **Calibrate for = Fluid dynamics**; the others do not print a calibration.

### A.3 Mesh operations

| Node | Type | Selection |
|---|---|---|
| `ftri1` Free Triangular (not pore) | Free Triangular | Domains 1, 3 (reservoir + membrane); children `size1`, `size5`, `size6`, `size3` |
| `ftri2` Free Triangular (pore) | Free Triangular | Remaining (Domain 2); child `size2` |

**No Boundary Layers node exists.** No Distribution, Mapped, Corner Refinement, Adapt or Refine
node exists. The wall is resolved purely by the 0.05 nm boundary size with growth rate 1.05.
Boundary-layer parameters (number of layers, stretching factor, first-layer thickness) are
therefore **not applicable**, not merely absent. **[verified]**

---

## B. Solver (§3, §4)

Both studies are stationary and **share identical solver settings**. Hardware: 12-core AMD,
Windows 10, 32.22 GB, single socket ("beasty").

### B.1 Studies

| | Study 1 "Demo" | Study 2 "Full sweep" |
|---|---|---|
| Step | Stationary | Parametric Sweep → Stationary |
| Geometric nonlinearity | Off | Off |
| Mesh | `mesh2` | `mesh2` |
| Discretisation (per interface) | `physics` for es, tds, spf | same |
| Compute time | 3 min 10 s | **41 h 3 min 51 s** |

### B.2 Sweeps (§4.1, §4.2.1, §4.3.1)

Outer **Parametric Sweep**, sweep type **Parameter switch**:

| Switch | Cases | Case numbers |
|---|---|---|
| Enabled Physics | All | `range(1,1,5)` |
| Electrolyte | User defined | 1 |

The five Enabled Physics cases are the ablation set (full ePNP-NS, no WDF, no CDF, no SMP,
classical PNP-NS) — *inference* from the `enable_*` parameters and the ESI ablation figures; the
report does not name the cases.

Inner stationary **Parametric 1 (p1)** / Study extensions:

| Setting | Value |
|---|---|
| Sweep type | **All combinations** |
| Run continuation for | **Manual** |
| **Continuation parameter** | **`V_bias`** |
| On error | Store empty solution |
| Distribute parameters (cluster) | On |

| Parameter | Value list | Unit | Count |
|---|---|---|---|
| `V_bias` | `range(-500,100,-300)`, `range(-200,25,-125)`, `range(-100,10,100)`, `range(125,25,200)`, `range(300,100,500)` | mV | 35 |
| `c_salt` | 5, 10, 25, 50, 75, 100, 125, 150, 200, 250, 300, 400, 500, 750, 1000, 1500, 2000, 2500, 3000, 4000, 5000 | mM | 21 |

735 (V, c) combinations per physics case; 3 675 solves total. The `V_bias` continuation is the
"use solution from previous step" mechanism — no separate auxiliary-sweep node exists.

### B.3 Nonlinear solver — Fully Coupled 1 (`fc1`)

**Fully coupled. No segregated solver, no segregation groups.** **[verified]**

| Setting | Value |
|---|---|
| Linear solver | Direct 1 |
| **Initial damping factor** | **0.2** |
| **Minimum damping factor** | **1.0 × 10⁻²** |
| Recovery damping factor | 0.2 |
| **Maximum number of iterations** | **100** |
| Newton type (constant / automatic / automatic highly nonlinear) | NOT IN REPORT |
| Restriction for step-size increase | NOT IN REPORT |
| Termination technique | NOT IN REPORT |
| Tolerance factor | NOT IN REPORT |
| Residual/solution termination criterion | NOT IN REPORT |

The presence of *initial*, *minimum* and *recovery* damping factors means the damping was
**variable with a lower bound of 0.01**, started at 0.2. **[verified]**

### B.4 Stationary Solver 1 (`s1`) and linear solver

| Setting | Value |
|---|---|
| **Relative tolerance** | **1 × 10⁻⁶** |
| Absolute tolerance | NOT IN REPORT |
| Reuse sparsity pattern (Advanced) | On |
| Results while solving (Study 2) | Probes: None |
| **Direct solver** | **PARDISO** |
| **Pivoting perturbation** | **1.0 × 10⁻¹³** |
| Memory allocation factor | NOT IN REPORT |
| Preordering algorithm | NOT IN REPORT |
| Row preordering | NOT IN REPORT |
| Multithreaded forward/backward substitution | NOT IN REPORT |
| Scaling (automatic / manual / none) | NOT IN REPORT |
| Manual scale values | NOT IN REPORT |

Dependent variables solved as one block: `comp1.cneg`, `comp1.cpos`, `comp1.p`,
`comp1.u = {u, w}`, `comp1.V`.

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
ion transport and the flow. The open question in `06-numerics-fem.md` §4 is settled against our
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

`0.62e1` = **6.2 nm⁻¹**, with **`+0.01`** inside the exponent. Confirms index item 1 exactly.
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
concentration**, confirming index ruling 3. **[verified]**

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
breaks the relation at finite `c`. Consistent with index item 4.

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
| Dielectric-gradient force | **Absent** — confirms index item 3. **[verified]** |
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
This matches the rule in `CLAUDE.md` and `06-numerics-fem.md` §7. The evaluation boundary is
**NOT IN REPORT**. **[verified]**

Pore averages use `is_inside_pore`, `is_inside_pore_bulk` (`wdf.wd > 0.5 nm`) and
`is_inside_pore_surface` (`wdf.wd <= 0.5 nm`), integration order 4.

---

## D. Contradictions with the rest of this knowledge base

| # | KB statement | Report says | Action |
|---|---|---|---|
| 1 | `09` (this file): stabilisation OPEN, both branches live | **Streamline + crosswind ON in tds and spf; crosswind = Do Carmo and Galeão; approximate residual; isotropic off** | Settle `06-numerics-fem.md` §4; the "no stabilisation" policy is *not* like-for-like |
| 2 | `06-numerics-fem.md` §5: "PARDISO direct + Newton with a lower-bounded variable damping factor", unverified provenance | **Confirmed exactly**: PARDISO, pivot perturbation 1e-13, damping 0.2 initial / 0.01 minimum / 0.2 recovery, 100 iterations, fully coupled | Mark **[verified]**, cite this file |
| 3 | Index ruling 2: permittivity fit = authors' Buchner values (29.50, 11.74); "confirmed by the 42.12 cap" | **The model used Gavish: `epsr_ms = 30.08`, `epsr_alpha = 11.5`**, matching the ESI text | **Settled: the shipped model used Gavish, so those govern.** With 30.08/11.5, `εr(5.3 M) = 42.67`; with 29.50/11.74, 42.13. The stale 42.12 cap came from the Buchner fit, **not** from what was solved. Ruling 2, index §"Still open" and `01` §8 E5 now record Gavish as governing; `SPECIFICATION.md` §4.6 erratum 6 carries the arithmetic. **[verified]** |
| 4 | `09` (this file): ESI is 143 pages | 162 pages; 143 is the ToC page of §5 | Corrected above |
| 5 | `06-numerics-fem.md` §8: mesh design = boundary layers, `h₁ ≈ λ_D/5`, ~15 geometric layers | **No boundary-layer mesh at all**; isotropic free triangles, 0.05 nm on the pore wall, growth 1.05, 120 917 triangles | Our BL mesh is a deliberate deviation; keep it, but do not describe it as matching COMSOL |
| 6 | `06-numerics-fem.md` §8: "no discretisation error bar" | Report gives element counts and quality (0.6378 / 0.9765) but **no DOF and no convergence study** | Narrow the claim: quality yes, convergence no |
| 7 | Index item 1: wall function `1 − exp(−6.2(d + 0.01))` | Verbatim `1 - exp(-0.62e1*(wdf.dwd + 0.01))` | Confirmed **[verified]** |
| 8 | Index item 3: no dielectric-gradient body force | Body Force is `E·ρ_ion` only | Confirmed **[verified]** |
| 9 | Index ruling 3: `⟨c⟩` = arithmetic mean of ion concentrations | `cdf.dcav = (cdf.dcpos + cdf.dcneg)*0.5` | Confirmed **[verified]** |
| 10 | Index ruling 5: `ε_protein` = 20 | `epsr_nanopore = 20`; `epsr_membrane = 3.2` | Confirmed **[verified]** |

---

## E. What we must replicate for a like-for-like comparison

Ordered by expected effect on the ionic-current QoI.

| # | Setting to match | Value | Why it matters |
|---|---|---|---|
| 1 | **TDS stabilisation** | streamline + crosswind on, crosswind = Do Carmo and Galeão, approximate residual, isotropic off | Adds a residual-based term to the transport operator that our unstabilised solve does not have; biases the current on any practical mesh |
| 2 | **Flow element pair + stabilisation** | P1+P1 with streamline + crosswind | Their pressure stabilisation is what makes equal-order legal; a Taylor-Hood P2/P1 solve is a *different* discretisation of the same PDE |
| 3 | **Convective term form** | Conservative form | Changes the assembled operator and the mass balance at coarse resolution |
| 4 | **Discretisation orders** | V quadratic, c quadratic, u/w/p linear | Directly sets the EDL resolution per element |
| 5 | **Wall-distance definition** | closest-point general extrusion onto the **pore surface only**, membrane excluded, Euclidean | Sets every wall correction; including the membrane would change EOF and current near the mouth |
| 6 | **Permittivity parameters** | `epsr_ms = 30.08`, `epsr_alpha = 11.5`, `epsr0 = 78.15` | See D3 — this is what was solved, whatever the ruling says |
| 7 | **Concentration clamps** | `cdf` argument clamped to [10⁻⁶ M, 5.3 M]; charge density clamped to `c ≥ 0` | Without them the fits extrapolate and Newton diverges at 5 M |
| 8 | **ε values** | pore 20, membrane 3.2 | Sets the fixed-charge screening |
| 9 | **Mesh resolution** | 0.05 nm max on the pore wall, growth 1.05, 0.1 nm in the pore domain, 0.001 nm global min, ~1.2 × 10⁵ triangles, min quality ≥ 0.64 | Comparable resolution, not identical elements |
| 10 | **Nonlinear strategy** | fully coupled, damping 0.2 → min 0.01, ≤ 100 iterations, rel. tol. 1e-6 | Same converged state; different paths are fine as long as the tolerance matches |
| 11 | **Continuation** | ramp `V_bias`, reuse previous solution | Determines which branch is found at high bias / low salt |
| 12 | **Current extraction** | variational boundary flux, integration order 4 | Cross-section integrals of the CG flux disagree at the percent level |
| 13 | **Steric flux weak form** | as printed in C.6, `α_i = k_i/(1 − Σ c_j v_j)` | Sign and prefactor as given; index item 2 |

## F. Differences that cannot be removed

| Difference | Consequence |
|---|---|
| COMSOL's `tds.streamline`, `tds.crosswind`, `spf.streamlinens`, `spf.crosswindns` are not exported | We can implement SUPG + a Do Carmo–Galeão-type crosswind, but not bit-for-bit the same operator. The stabilisation term is therefore an **irreducible systematic** in any comparison, bounded only by mesh refinement |
| "Approximate residual" is a COMSOL-internal choice | Their residual used in the stabilisation is not the exact strong residual |
| Mesh generator | Netgen vs COMSOL's mesher — element counts can match, elements cannot |
| Degrees of freedom | **NOT IN REPORT**; cannot be matched or checked |
| Linear solver internals | PARDISO ordering/pivoting defaults NOT IN REPORT; irrelevant to the converged solution, relevant only to timings |
| Newton type and termination technique | NOT IN REPORT; only the damping bounds and rel. tol. are reproducible |
| Scaling | NOT IN REPORT; COMSOL's automatic variable scaling affects the convergence path and the meaning of "rel. tol. 1e-6" |
| Evaluation boundary for the current | NOT IN REPORT; choose a boundary and state it |
| `rhoq_pore` interpolation grid | The gridded charge table itself is not in the report — only the function's units (1/m²) and extrapolation mode. Our charge pipeline regenerates it from structure, so the fixed-charge field will differ in detail |
| Geometry polygon | 190 vertices printed in §2.2.2 and reproducible, but our contour pipeline generates its own |
| P1+P1 vs P2/P1 flow | If we keep Taylor-Hood, the flow discretisation differs by construction; only the converged velocity field can agree, not the operator |
