---
type: Specification
title: "4. Physics specification (normative)"
description: "States the normative ePNP-NS physics: domains and symbols, governing equations, empirical corrections, fixed charge, dielectric model and switches."
---

## 4. Physics specification (normative)

This section states the mathematical model. Requirements carry `PHY-nn` IDs and use the keywords
of §1.5. Symbols follow Willems K. et al., *Nanoscale* **12**, 16775–16795 (2020) and
the concepts under `knowledge/01-physics-epnpns/`. Where the reference and the published text differ, the COMSOL
model report governs and §4.6 records the divergence.

### 4.1 Domains, boundaries and symbols

#### 4.1.1 Domains and boundaries

| Name | Region | Equations and conditions |
|---|---|---|
| `Ω_w` | electrolyte: both reservoirs and the pore lumen | Poisson, Nernst–Planck, Navier–Stokes |
| `Ω_p` | pore protein | Poisson |
| `Ω_m` | lipid bilayer | Poisson |
| `Ω_a` | analyte body, when one is present (FR-21) | Poisson |
| `Ω` | `Ω_w ∪ Ω_p ∪ Ω_m ∪ Ω_a` | Poisson |
| `Γ_w,c`, `Γ_w,t` | exterior reservoir boundaries, cis and trans | Dirichlet φ, c; stress-free |
| `Γ_m` | exterior bilayer boundary | zero charge |
| `Γ_p+m` | interior interface, fluid to protein and membrane | dielectric continuity, no-flux, no-slip |
| `Γ_a` | analyte surface | dielectric continuity, no-flux, no-slip; the NUM-28 force is taken over it |
| `r = 0` | symmetry axis | axis conditions |

NOTE: reference geometry is a hemispherical reservoir of radius R = 250 nm on each side and a
DPhPC bilayer of thickness 2.8 nm.

#### 4.1.2 Symbols

| Symbol | Meaning | Units |
|---|---|---|
| `φ` | electric potential | V |
| `V_bias` | applied bias on `Γ_w,t` | V |
| `c_i`, `c_bulk` | concentration of ion *i*; reservoir value | mol m⁻³ |
| `u`, `p`, `σ` | fluid velocity; pressure; stress tensor | m s⁻¹; Pa; Pa |
| `J_i`, `β_i` | molar flux of ion *i*; its steric flux vector | mol m⁻² s⁻¹; m⁻¹ |
| `Φ` | packing fraction `Σ_j N_A a_j³ c_j` | 1 |
| `ρ_pore`, `ρ_ion` | fixed protein space charge; mobile charge `F Σ_i z_i c_i` | C m⁻³ |
| `σ_s` | prescribed surface charge density | C m⁻² |
| `⟨c⟩`, `d` | average ion concentration; wall distance (§4.1.3) | mol L⁻¹; nm |
| `D_i`, `μ_i` | diffusivity; mobility of ion *i* | m² s⁻¹; m² V⁻¹ s⁻¹ |
| `η`, `ϱ`, `ε_r` | viscosity; mass density; relative permittivity | Pa s; kg m⁻³; 1 |
| `a_i`, `a_0`, `z_i` | steric diameter ion / water; valence | m; m; 1 |
| `ε_0`, `F` | 8.85419 × 10⁻¹² F m⁻¹; 96485.33 C mol⁻¹ | — |
| `R`, `N_A` | 8.314463 J mol⁻¹ K⁻¹; 6.022 × 10²³ mol⁻¹ | — |
| `T`, `V_T` | 298.15 K; thermal voltage `RT/F` = 25.693 mV | — |

#### 4.1.3 Derived scalar fields

**PHY-01.** The correction driver `⟨c⟩` SHALL be the arithmetic mean of the ion concentrations,
`⟨c⟩ = (1/n) Σ_i c_i` over the n solved species, with each `c_i` clamped to
[1 × 10⁻⁶ M, 5.3 M] before the average is taken (COMSOL: `(cdf.dcpos + cdf.dcneg)*0.5`). The
ionic-strength form `½ Σ_i z_i² c_i` SHALL be available as a separately named option.

Rationale: the published prose calls `⟨c⟩` the local ionic strength. The two coincide for a
symmetric 1:1 salt, so the published results do not discriminate; the arithmetic mean is what the
model evaluates and generalises unambiguously to multivalent species.

**PHY-02.** The wall distance `d` SHALL be the distance to the nearest pore boundary, with the
membrane excluded from the distance source set. `d` SHALL be computed once per mesh as a continuous field
(eikonal solve or screened-Poisson smoothing). The validated default is that field unsmoothed: it is
C⁰, with gradient jumps across element edges. Mollification to C¹ (the `smoothing_length_nm` pass of
NUM-31) is a deviation, off by default.

Rationale: the reference model used a general-extrusion operator over the pore boundaries only;
electrolyte properties near the bilayer do not affect the pore's figures of merit. That field was
unsmoothed. Mollification is an implementation change, not a model change, and is required because
`D`, `μ` and `η` all depend on `d`, so a kinked `d` enters the Jacobian.

NOTE (the driver clamp): the wall functions of PHY-11 are stated for `d̄ ≥ 0`, and the ion form
`1 − exp(−P₁(d̄ + P₂))` has its root at `d̄ = −P₂`. A negative sample of a discrete distance field
therefore does not attenuate `D_i` and `μ_i`, it reverses their sign, giving an anti-diffusion
operator in the one neighbourhood where the wall correction is supposed to hold ions back. The
driver SHALL be clamped to `max(d̄, 0)` before any wall form evaluates it, exactly as PHY-13
requires of the concentration driver, and the clamp SHALL be applied where the correction reads the
driver so that adding an electrolyte inherits it. The clamp is a floor on a discretisation artefact
and SHALL NOT be relied on to make an under-resolved field admissible; NUM-34 is what decides that.

### 4.2 Governing equations

**PHY-03.** Poisson's equation SHALL be solved over the whole domain `Ω`, with piecewise
permittivity and a volumetric fixed charge in the solid domains:

```
−∇·( ε_0 ε_r(⟨c⟩, x) ∇φ ) = ρ_pore(x) + ρ_ion ,      ρ_ion = F Σ_i z_i c_i
```

**PHY-04.** The steady size-modified Nernst–Planck equation SHALL be solved on `Ω_w` for each
species i:

```
∇·J_i = 0
J_i = −[ D_i(⟨c⟩,d) ∇c_i  +  z_i μ_i(⟨c⟩,d) c_i ∇φ  +  D_i(⟨c⟩,d) β_i c_i  −  u c_i ]
```

**PHY-05.** The steric flux enters the flux bracket with a positive sign; the bracket is then
negated. The steric flux vector SHALL be

```
            (a_i³ / a_0³) · Σ_j N_A a_j³ ∇c_j
    β_i  =  ─────────────────────────────────
              1 − Σ_j N_A a_j³ c_j
```

with `a_i = 0.5 nm` for all ions (maximum packing 13.3 M) and `a_0 = 0.311 nm` for water (maximum
packing 55.2 M). The reference implementation is

```
smp.alpha_cpos*cpos*(smp.rad3_cpos*(−tds.D_cposrr*cposr − …) + smp.rad3_cneg*(…))
```

The sum over j SHALL retain all species; it SHALL NOT be collapsed to a self-interaction term.

Rationale: the `a_i³/a_0³` prefactor makes the steric drive species-dependent; it evaluates to
4.16 for the reference NaCl parameters and is therefore not a normalisation that can be dropped.

**PHY-06.** The solver SHALL assert `Φ = Σ_j N_A a_j³ c_j < 1` at every nonlinear iteration and
SHALL fail with the offending coordinate if the assertion is violated. `β_i` is singular at
`Φ = 1`.

**PHY-07.** The flow SHALL be solved on `Ω_w` in the variable-density incompressible formulation
of Axelsson et al. (2015), as three equations:

```
u·∇ϱ = 0                                             (density continuity)
(u·∇)(ϱu) + ∇·σ = f                                  (momentum)
∇·(ϱu) − u·∇ϱ = 0                                    (velocity continuity)
σ = p I − η [ ∇u + (∇u)ᵀ ]
```

In the reference model the density-continuity contribution is supplied as the hand-added weak term
`(u*d(rho,r) + w*d(rho,z))*test(p)`.

**PHY-08.** The body force SHALL be the electrostatic force on the mobile ionic charge only:

```
f = ρ_ion E = −( F Σ_i z_i c_i ) ∇φ
```

Rationale: the published model contains no dielectric-gradient (Korteweg–Helmholtz) body force
`−½|∇φ|²∇(ε_0 ε_r)` and no dielectric-decrement term `−½|∇φ|² ∂ε/∂c_i` in the Nernst–Planck flux,
although `ε_r` varies with `⟨c⟩`; the model report records `spf.Fr = es.Er*scd_ions` and
`spf.Fz = es.Ez*scd_ions` and nothing further. Both terms are available together behind one switch
(§4.5), default off. The published agreement with experiment was obtained without them, and
including one without the other is thermodynamically inconsistent.

**PHY-09.** Boundary conditions SHALL be as follows.

| Boundary | φ | c_i | u, p |
|---|---|---|---|
| `Γ_w,c` (cis) | `φ = 0` | `c_i = c_bulk` | `σ·n = 0` (no normal stress) |
| `Γ_w,t` (trans) | `φ = V_bias` | `c_i = c_bulk` | `σ·n = 0` |
| `Γ_p+m` (fluid to protein, fluid to membrane) | continuity of `n·D`, `D = ε_0 ε_r ∇φ`; on the wall of an idealised pore where `σ_s` is set, `n·(D_s − D_f) = σ_s`, `n` from solid to electrolyte (NOTE below) | `n·J_i = 0` | `u = 0` (no-slip) |
| `Γ_m` (exterior membrane boundary) | `n·D = 0` (zero charge) | not solved | not solved |
| Analyte surface (when present) | dielectric interface, optional `σ_s` | `n·J_i = 0` | `u = 0` |
| `r = 0` (axis) | natural | natural | `u_r = 0` (essential) |

Rationale: `∂_r φ = ∂_r c_i = ∂_r u_z = 0` on the axis are natural conditions under the `r`-weighted
axisymmetric forms. Imposing them as Dirichlet conditions is a modelling error.

NOTE (a wall surface charge, PHY-09, FR-20, QR-13; §8.2.22 X3, REV-144): on the pore wall `wall` of
an idealised pore (§5.3.1, `geometry.pore`), `boundary_conditions.wall_charge_C_m2` sets a uniform
surface charge density `σ_s`. With `n` the unit normal from the solid into the electrolyte, Gauss's
law across the wall is `ε_0 ε_r,s ∂_n φ_s − ε_0 ε_r,f ∂_n φ_f = σ_s`; with the table's
`D = ε_0 ε_r ∇φ`, `n·(D_s − D_f) = σ_s`. In the weak form of PHY-03 it is the surface term
`∫_wall σ_s v dS` on the right-hand side, with the same sign as `∫ ρ_pore v dV`, under the measure of
the volume terms (`2π r ds` against `2π r dr dz`; where the `2π` is dropped it is dropped from both),
added once to the one expression of the forms. It is an input, not a correction (PHY-22): it is recorded with the case's
inputs and is no deviation, and `0`, its default, adds no term, so a case without it solves exactly
as before. The concentrations and the flow see it only through `φ`. VER-77 checks it.

### 4.3 Empirical corrections

**PHY-10.** Every concentration- and wall-dependent property SHALL be evaluated as
`X(⟨c⟩, d) = X⁰ · f^c(c̄) · f^w(d̄)`, with `c̄ = ⟨c⟩/(1 M)`, `d̄ = d/(1 nm)`.

**PHY-11.** The functional forms SHALL be:

| Property | `f^c` | `f^w` |
|---|---|---|
| `D_i` | `(1 + P₁c̄^½ + P₂c̄ + P₃c̄^{3/2} + P₄c̄²)⁻¹`, separate coefficients per ion | `1 − exp(−P₁(d̄ + P₂))` |
| `μ_i` | same form, own per-ion coefficients | `1 − exp(−P₁(d̄ + P₂))`, same coefficients as `D_i` |
| `η` | `1 + P₁c̄^½ + P₂c̄ + P₃c̄² + P₄c̄^{7/2}` (Jones–Dole) | `1 + exp(−P₁(d̄ − P₂))` |
| `ϱ` | `1 + P₁c̄ + P₂c̄²` | — |
| `ε_r,f` | `1 − (1 − P₁/P₀)·L(3P₂c̄/(P₀ − P₁))`, `L(x) = coth x − 1/x` | — |

The two wall functions carry opposite offset signs, `(d̄ + P₂)` for `D` and `μ` and `(d̄ − P₂)` for
`η`; both are verified in §4.6.

**PHY-12.** The coefficients SHALL be those of the COMSOL model report
(`npgrid_clya_v8_NaCl_report.mph`, COMSOL 5.4 build 388, 2020-05-22) for NaCl at 298.15 K, at the
precision below.

| Quantity | `X⁰` | P₁ | P₂ | P₃ | P₄ | Cap at 5.3 M |
|---|---|---|---|---|---|---|
| `D_Na⁺` | 1.334 × 10⁻⁹ m² s⁻¹ | 0.202 | −0.3048 | 0.219 | −0.03124 | 0.81 × 10⁻⁹ m² s⁻¹ |
| `D_Cl⁻` | 2.032 × 10⁻⁹ m² s⁻¹ | 0.149 | −0.04933 | 0.03392 | 0.01431 | 1.07 × 10⁻⁹ m² s⁻¹ |
| `μ_Na⁺` | 5.192 × 10⁻⁸ m² V⁻¹ s⁻¹ | 0.7907 | −0.3529 | 0.1459 | 0.009241 | 1.74 × 10⁻⁸ m² V⁻¹ s⁻¹ |
| `μ_Cl⁻` | 7.909 × 10⁻⁸ m² V⁻¹ s⁻¹ | 0.6289 | −0.4286 | 0.2123 | −0.01068 | 3.21 × 10⁻⁸ m² V⁻¹ s⁻¹ |
| `η` | 8.904 × 10⁻⁴ Pa s | 0.007558 | 0.07769 | 0.01192 | 5.951 × 10⁻⁴ | 1.75 × 10⁻³ Pa s |
| `ϱ` | 997.0 kg m⁻³ | 0.04047 | −6.149 × 10⁻⁴ | — | — | 1.19 × 10³ kg m⁻³ |
| `ε_r,f` | 78.15 (`P₀`) | 30.08 (`epsr_ms`) | 11.5 (`epsr_alpha`) | — | — | 42.67 |
| `f^w` for `D`, `μ` | — | 6.2 nm⁻¹ | 0.01 nm | — | — | — |
| `f^w` for `η` | — | 3.36 nm⁻¹ | 1.47 × 10⁻¹ nm | — | — | — |
| `t_Na⁺` (auxiliary) | 0.3963 | 9.38 × 10⁻² | 2.86 × 10⁻³ | −1.88 × 10⁻² | 4.51 × 10⁻³ | — |

Fit standard errors and R² (0.99 throughout, except 0.97 for the η wall function and 0.98 for
`t_Na⁺`) are carried in `data/corrections/willems2020_nacl.yaml`. The transport-number fit is
auxiliary, not evaluated at solve time: it derives per-ion mobilities from molar conductivity via
`μ_i(c) = Λ(c) t_i(c) / (z_i F)`, `t_Cl = 1 − t_Na`. Self-consistency values a conformance test
SHALL reproduce: `f^w_D(0) = 0.06`, `f^w_D(0.75 nm) = 0.99`, `η⁰/η^w(0) = 0.37`,
`η⁰/η^w(1.45 nm) = 0.99`.

NOTE: the density coefficients differ from the thesis table by more than rounding, `P₁ = 0.04047`
(thesis 4.06 × 10⁻²) and `P₂ = −6.149 × 10⁻⁴` (thesis −6.39 × 10⁻⁴, 3.8 % apart). The COMSOL values
govern.

**PHY-13.** The fits are valid over 0–5.3 M. Above 5.3 M every property SHALL be clamped to its
cap value from the table above, and each clamp activation SHALL be logged with the location and
property. Diffusivities between 4 M and 5.3 M are extrapolated (no experimental data above 4 M)
and SHALL be documented as such.

**PHY-14.** `μ_i` SHALL be derived from `D_i⁰`, not fitted independently. The reference model sets
`l0 = e² N_A /(k_B T) · D0` and `mu = l0 · L(c) · f_w(d) / F²`, that is

```
μ_i = D_i⁰ · L_i^c(⟨c⟩) · f_i^w(d) / (RT)
```

where `L_i^c` are the conductivity-fitted coefficients (`l1…l4` above) and `f_i^w` the shared ion
wall function. In this form `μ_i` is a molar mobility in mol m² J⁻¹ s⁻¹ and the drift term carries
an explicit factor F; multiplying by F recovers the tabulated `μ_i` in m² V⁻¹ s⁻¹ used in PHY-04.

Rationale: `μ_i⁰ = D_i⁰/V_T` therefore holds at infinite dilution by construction. At finite
concentration `D` and `μ` carry different concentration corrections (`cdf.D_*` fitted to
self-diffusion data, `cdf.L_*` to conductivity data), so `D_i/μ_i` drifts to 1.2–1.7 × kT/e between
0.15 M and 3 M. Poisson–Boltzmann is therefore a separate model, not the PNP solver at zero bias.
Tests SHALL assert the expected drift profile rather than `D_i/μ_i = kT/e`.

**PHY-15.** The implementation SHALL NOT apply a reduction of ion motility by the ratio of ion
radius to pore radius. If such a correction is added later it SHALL be an opt-in experimental
model.

Rationale: Simakov and Pederson include this term; the source work excluded it, extrapolation to
ions whose hydrodynamic radius is comparable to a solvent molecule being questionable.

### 4.4 Fixed charge and dielectric model

**PHY-16.** The volumetric fixed charge `ρ_pore` SHALL be produced by the following pipeline.

| Step | Operation | Normative settings |
|---|---|---|
| 1 | Structure preparation | strip waters and ligands, verify oligomeric state, fill loops |
| 2 | Ensemble | aligned MD frames (reference: 50, from the last 5 ns of a 30 ns run) |
| 3 | Protonation, partial charges | PDB2PQR 3.7+ driving PROPKA at pH 7.5 with the CHARMM force field: `--ff=CHARMM --ffout=CHARMM --with-ph=7.5 --titration-state-method=propka --drop-water --keep-chain`; record `Q_net = Σ_i q_i` |
| 4 | Per-atom smearing | normalised 3D Cartesian Gaussian `ρ_i(x) = q_i e π^(−3/2) w_i^(−3) exp(−\|x − x_i\|²/w_i²)`, width `w_i = 0.5 · R_i` (`R_i` from the PQR) |
| 5 | Azimuthal projection | the exact azimuthal mean of step 4, in closed form: `ρ̄_i(r, z) = q_i e π^(−3/2) w_i^(−3) exp(−((r − r_i)² + (z − z_i)²)/w_i²) · Ĩ₀(2 r r_i/w_i²)`, with `Ĩ₀(x) = e^(−x) I₀(x)` and `r_i = (x_i² + y_i²)^(1/2)`; summed over the atoms and averaged over the frames. The Cₙ average is contained in the azimuthal mean |
| 6 | Assembly | `ρ_pore = Σ_i ρ̄_i`, deposited onto an element-wise field on the deployed mesh by `r`-weighted L² projection, each atom's element integrals renormalised to `q_i e` (PHY-18). The areal density `2πr ρ_pore`, sampled on a 0.005 nm (r, z) grid extending ≥ 4 w_max beyond the protein, is the exported artefact and the producer leg's grid. A supplied areal density keeps the reference's assembly, `scd_pore = if(r < 0.01[nm], 0, e_const * rhoq_pore(r,z) / (2*π*r))` [C m⁻³] |
| 7 | Conservation check | `\|∫ρ_pore · 2πr dr dz − Q_net\| / \|Q_net\| < 10⁻³` |

NOTE (PHY-16 steps 4–6; §8.2.4 D2): smearing each atom on a 3D grid at 0.005 nm and binning the
grid to (r, z) by exact annular volume is not what the pipeline does. The closed form of step 5 is
that construction's limit as the spacing goes to zero, without its cost, which would be about 10¹³
voxel updates for the 50-frame ClyA ensemble. Step 6 deposits onto the
deployed mesh rather than sampling a grid there, which removes the aliasing of the consumer leg
that the §4.4 NOTE measures on the delivered table. The reference built its table from a 2D Gaussian
in (r, z) divided by `2πr` at the field point (`knowledge/04-clya-geometry-and-charge/08-gaps-and-ambiguities-questions-for-the.md`, gap G4). PHY-17 forbids that
construction, so it is not reproduced. Off the axis the two carry the same charge and the same
z-marginal, and differ pointwise by `(r − r_i)/(2 r_i)` of the local value: first order in
`w_i/r_i` and odd about the atom, so the 3D construction's radial centroid lies `w_i²/(4 r_i)`
further out (`knowledge/04-clya-geometry-and-charge/03-fixed-charge-pipeline.md#33-the-closed-form-kernel-on-the-0005-nm-lattice` [tested]). The difference on the ClyA
ensemble is measured at Tier 3 rather than accommodated.

NOTE (PHY-16 step 3, protonation as run; WP27): PDB2PQR SHALL be run
once per selected frame (§8.2.4 D4) on that frame's heavy atoms, with every hydrogen and every water
removed (PDB2PQR 3.7.1's `--drop-water` drops only `HOH` and `WAT`; WP27
review) and every protonation-variant residue name (`HSD`, `HSE`, `HSP`, `HID`, `HIE`, `HIP`, `ASH`, `ASPP`,
`GLH`, `GLUP`, `LYN`, `LSN`, `CYM`, `TYM`, `ARN`) written as its titratable parent, so that the
states are PROPKA's at the case's pH and not the source file's. The disulfide name `CYX`, which
PDB2PQR writes under `SWANSON` and `PEOEPB`, is read as `CYS` the same way (WP27 review: without it every disulfide-bonded cysteine named a residue the ensemble does
not hold). PDB2PQR 3.7.1 treats `HSD` and
`HSE` as fixed residues that PROPKA does not titrate, and refuses `HSE` with its hydrogens present,
so a CHARMM-named MD frame passed through verbatim would pin every histidine. The reference passed
its frames verbatim to PDB2PQR 2.1.1, and its PQRs keep `HSE`; the difference is measured at Tier 3
rather than reproduced. Under CHARMM, PDB2PQR cannot represent a neutral terminus, `CYS⁻`, `LYS⁰`,
`TYR⁻` or `ARG⁰`, and keeps the standard state where PROPKA prefers one of these; it never applies
PROPKA's terminal pKa at all. Every such residue SHALL be recorded per frame as an unapplied state,
derived by comparing each residue's applied charge with the sum of PROPKA's group states at the pH,
never parsed from log text. On 2WCD at pH 7.5 these are `CYS 285` (pKa 6.25) in every chain, and
the N-terminus of `LYS 8` wherever its pKa, 7.48 to 7.50 across the chains, falls below the pH. They are the validated model's states, so they are recorded and
not gated. The protonation states of the chains of a homo-oligomer are not symmetrised: a residue
whose charge differs between chains of identical sequence is recorded as a per-chain diagnostic.

NOTE (protonation before the density, §8.2.19 U2). When the library package that `/np-plan amend 5`
names lands, step 3's protonation runs on the aligned ensemble before stage 2, and stage 2 smears the
protonated frames, PDB2PQR's atoms, each with the radius the §5.3.1 NOTE on `geometry.density` takes
for it, so a protonation state or a charge-level
variant moves the density, the contour and the mesh as well as the charge. That is the validated
default. Smearing the hydrogens as loaded, as the reference did from its MD frames, becomes a switch
away from it, recorded in the manifest (FR-25) and set by the reference-reproduction cases (VAL-03's
golden, Tier 3). The package amends this clause, FR-04, §5.2's stage 2 and 7 rows and its stage-7
design note; re-pins VER-62's golden for each walk whose mesh it moves, or sets the switch on that
walk, by the author's ruling (§8.2.7 G10); and adds a Tier 1 test that a changed protonation state
moves the density. Until then the text above holds.

NOTE (PHY-16 steps 4–6, the deposition as run; WP28): the closed form of
step 5 SHALL be evaluated on the export lattice of step 6, whose spacing is
`charge.smearing.grid_spacing_nm` and which carries a node on `r = 0`. Each atom's kernel is cut
to a patch of half-width `6 w_i` about it in `r` and `z`, which leaves out `1 − erf(6)² =
4.3 × 10⁻¹⁷` of its charge. Its trapezoid sum on the lattice is then renormalised to `q_i e`, divided
by the number of frames. That renormalisation is PHY-18's: on the lattice the sum is exact to
10⁻¹⁵ off the axis, but an atom within a few `w_i` of the axis is short by `h²/(6 w_i²)`
(`knowledge/04-clya-geometry-and-charge/03-fixed-charge-pipeline.md#33-the-closed-form-kernel-on-the-0005-nm-lattice`). A spacing above half the smallest `w_i` of a charged atom SHALL be refused
naming that atom. The lattice and the atoms are in the model frame, `z ← z −
geometry.membrane.centre_z_nm` when the case generates its mesh, as stage 5 moves the profile, and
unshifted beside a supplied mesh. Atoms of zero charge are not deposited. The `r`-weighted L²
projection of step 6 is onto discontinuous polynomials of the potential's element order on each
triangle, with its integrals taken by the lattice's trapezoid rule, each node counted in the one
element containing it. Every test function of the potential's space is a polynomial of that order on
each element, so the assembled source equals the lattice integral of the kernel against every test
function, and the projection adds no error of its own. The charge is deposited on every material, as
the reference applied `ρ_pore` across all computational domains (`knowledge/04-clya-geometry-and-charge/03-fixed-charge-pipeline.md`). The deposit
SHALL be refused, naming the quantity and its location (QR-12), where lattice charge falls on no
element of the mesh, or where less than half of `Σ|q_i|` has its atom centres in solid materials,
which is how a structure in another frame than its mesh shows.

**PHY-17.** Smearing SHALL be performed in 3D Cartesian space and only then averaged azimuthally.
A Gaussian applied directly in (r, z) leaks charge across `r = 0` and SHALL NOT be used.

**PHY-18.** Where an areal density is converted to a volume density, as for a supplied
`areal_charge_density` (§5.3.1 NOTE on `inputs.charge`), the conversion SHALL carry the
`1/(2π r)` factor and the axis guard `r < 0.01 nm → 0` of the reference model. The closed form of
PHY-16 step 5 is a volume density, regular on the axis, and needs neither. Deposition SHALL
conserve charge by renormalising each atom's kernel to `q_i e` on the deployed mesh
(§8.2.4 D2). The quintic B-spline partition of unity, the other
option this clause first named, belongs to a Cartesian grid, and the producer no longer builds one.

**PHY-19.** The conservation assertion of step 7 SHALL be evaluated on the deployed finite-element
mesh, not on the source Cartesian grid. Per-z-slice cumulative charge SHALL additionally be checked
against the PQR sorted by z.

Rationale: the axis guard deletes charge, and bin-centre division by `2πr` near the axis can be
wrong by orders of magnitude. A globally satisfied check can hide a compensating Jacobian error,
which the per-slice check detects.

**PHY-20.** Relative permittivities SHALL be:

| Domain | `ε_r` | Source | Status |
|---|---|---|---|
| `Ω_p` (protein) | 20 | Li/Li/Zhang/Alexov 2013 | calibration parameter, reported in every output |
| `Ω_m` (membrane) | 3.2 | Gramse 2013 (DPhPC) | fixed |
| `Ω_w` (electrolyte) | `78.15 · f^c(c̄)` per PHY-11 and PHY-12 | Gavish 2016 | concentration-dependent |
| `Ω_a` (analyte) | 20 by default, as for `Ω_p` | Li/Li/Zhang/Alexov 2013 | calibration parameter, reported in every output |

The dielectric and ion-exclusion contours SHALL be built from the same Gaussian density field,
with the transition to `ε_w` smoothed over 1–2 Å and the ion-exclusion contour offset outward by
the hydrated-ion radius. `ε_p` and that offset are fitted, not measured, and SHALL be surfaced in
the case file.

NOTE (the smoothed dielectric is a blend, PHY-11, PHY-12, PHY-20): a smoothed transition **to `ε_w`**
cannot be expressed as a static `ε_r` field, because `ε_w = ε_r,f⁰ · ε_r,f^c(⟨c⟩)` and `⟨c⟩` is
solved for. A supplied dielectric field SHALL therefore be a solid fraction `χ ∈ [0, 1]`, and the
permittivity SHALL be

```
ε_r(r, z) = χ(r, z) · ε_p  +  (1 − χ(r, z)) · ε_r,f(⟨c⟩)
```

with the 1–2 Å transition carried by `χ` alone. Setting `χ` to the sharp material indicator
reproduces PHY-20's piecewise assignment exactly, so the smoothed field is a refinement of the
validated model rather than a replacement for it, and is recorded as a deviation when supplied. An
absolute `ε_r` field SHALL be refused, naming this clause: accepting one would silently disable the
permittivity correction while the run continued to report ePNP-NS. The mesh still carries the
material split, so Nernst–Planck is still not solved inside the protein; the field smooths the
coefficient, not the domain.

The two branches of the blend SHALL be evaluated where they have a meaning (author ruling 13). `⟨c⟩` has no meaning inside a solid, because ions do not exist
there in the model, so `ε_r,f(⟨c⟩)` SHALL be evaluated only in the fluid materials; the water share
of the blend inside a solid material, and in the ion-exclusion shell, is ion-free water, `ε_r,f⁰`.
`ε_p` is the element's own solid permittivity inside a solid material and, where the 1–2 Å
transition reaches past the mesh boundary into the fluid or the shell, the permittivity of the
nearest solid material, whose solid fraction `χ` there is. A single `ε_p` for the whole field would
blend the fluid beside the membrane towards the protein. With `χ` the sharp material indicator every
one of these choices drops out, and PHY-20's piecewise assignment is recovered exactly.

NOTE (the `2πr` cancels, PHY-16, PHY-19): under the axisymmetric volume element `dV = 2πr dr dz`,
the Jacobian and the `1/(2πr)` of PHY-16 step 6 cancel identically, so

```
∫_Ω ρ_pore · 2πr dr dz  =  ∫_{Ω, r ≥ r_guard} rhoq_pore(r, z) dr dz
```

and the conservation check of step 7 is **blind to the Jacobian** for an `areal_charge_density`
source: an error in how `r` enters cancels against itself. This is the compensating error PHY-19's
rationale names. Two consequences are normative. First, the check SHALL be reported as two legs — a
producer leg comparing the planar integral of the source grid against the declared `Q_net`, and a
consumer leg comparing the integral over the deployed mesh against that planar integral — each gated
at QR-03's tolerance, so that a failure names which side of the interface it belongs to; where no
`Q_net` is declared, the producer leg SHALL be recorded as not run and the consumer leg SHALL still
gate. Second, the per-`z`-slice cumulative check SHALL be evaluated against a Lipschitz weight of
stated width rather than a step, applied identically to both sides, since a step is integrated
inside every element the plane crosses and its quadrature error exceeds the tolerance it is meant to
enforce.

NOTE (the consumer leg is a resolution question, not a tolerance one, QR-03, PHY-19): measured on
the delivered ClyA `rhoq_pore` table — 1401 x 3401 at 0.005 nm, `r` in [0, 7] nm, `z` in
[-3.5, 13.5] nm — the producer leg is `4.7 x 10^-12` (`Q_grid = -71.999999999663 e` against a
declared `-72 e`) while the consumer leg on the WP8 reference mesh, 44 316 elements graded to
0.05 nm at the pore wall, is `9.9 x 10^-3`: ten times QR-03's budget, from a field the producer
delivered essentially exactly. Neither refinement route closes it. Refining `h` to 3 463 372
elements leaves the leg at `-1.1 x 10^-2` — *worse* than at 44 316, and non-monotone in between —
and raising the quadrature to order 37 on the fixed mesh oscillates through `+5.9 x 10^-4`,
`-3.0 x 10^-3`, `+2.8 x 10^-3` without settling. The cause is that the field's own structure is
below element scale: along the densest `z` the table changes sign 49 times, with extrema a median
0.035 nm apart, so pointwise quadrature of the bilinear interpolant is aliased rather than
inaccurate, and an aliased integral converges in neither `h` nor order.

Three consequences are normative. First, **the tolerance SHALL NOT be slackened to accommodate
this**: 10^-3 is what a conserved deposition achieves and the gate stays there, so a field whose
structure the deployed mesh cannot carry is refused rather than integrated badly. Second, the
quadrature-agreement gate is what SHALL name that case — on the delivered table it fires first, at
`9.3 x 10^-3` against its own `10^-4`, and reports that the mesh under-resolves the supplied field
rather than that charge was lost. Third, the remedy is on the **producer** side and is out of scope
until it exists (FR-13, FR-14, Phase 3): a charge deposited onto the finite-element space and
rescaled to `Q_net` conserves by construction, where sampling somebody else's interpolant at
quadrature points cannot. Until then a supplied `areal_charge_density` of this character SHALL be
ingested only with the gate's verdict recorded in the manifest.

A supplied field's source term and every leg of its conservation check SHALL be evaluated by one
explicit integration rule, of order 8, so that the gate measures the charge the solve assembles.
NGSolve's own estimate for the source was order 3, and on a 0.5 nm alternating field the deployed
mesh resolves it put the solved charge 1.2 × 10⁻² from the grid's while the order-8 gate passed at
2 × 10⁻⁵ (WP41 D2, REV-07). A deposited charge keeps the model's default: its total is exact there,
and its per-entry order is NUM-07's open question.

NOTE (the producer path's conservation report, PHY-19, FR-14, QR-03; WP28): for a deposited charge, the producer leg compares the trapezoid integral of the exported
lattice with `Q_net`, the mean over frames of `Σ q_i`. The consumer leg compares the deployed field,
integrated at the solve's order, with the lattice. Both are exact by construction, the first by
per-atom renormalisation and the second because each element carries its lattice charge, so they
guard the construction and SHALL be shown to fail on a broken one. The discriminating check is the
per-plane one, and PHY-19 names its reference: **the source atoms**, not the lattice. Azimuthal
averaging keeps each atom's z-marginal, a Gaussian of variance `w_i²/2`, so under the weight
`½ erfc((z − p)/s)` atom `i` contributes `q_i · ½ erfc((z_i − p)/√(s² + w_i²))` below plane `p`
exactly. On this path the weight SHALL be that Gaussian-smoothed step, with `s = 0.5 nm`, and both
the lattice and the deployed field SHALL agree with the atoms at every plane to QR-03's tolerance.
The consumer path keeps its linear ramp. The smoothed weight is Lipschitz, as the NOTE above
requires, and smooth: a polynomial of the deposit's order approximates it to about `0.064 h³ |W'''|`
on an element of size `h`, `6 × 10⁻⁴` on ClyA's 0.1 nm protein elements. A 0.2 nm ramp's kinks
leave `h/(16 s) = 0.03` there, which is too little margin for a gate meant to discriminate. The
planes span the atoms' z-extent. The guard deficit the exported lattice would suffer if re-read
through `inputs.charge` is recorded beside the legs.

NOTE (the derived solid fraction, FR-15, PHY-20; WP30): a non-zero
`charge.dielectric_transition_nm`, `δ`, makes stage 7 derive `χ` from the stage-4 profile as stage 5
placed it in the model frame. Let `W` be the profile's water-facing part, meaning its edges, split
at the bilayer planes, whose outward side is not membrane. Let `s` be the distance to `W`, positive
inside the body and negative outside. Then

```
χ = S(s/δ + 1/2),   S(x) = 3x² − 2x³ on [0, 1],  0 below it,  1 above it
```

which is C¹, is exactly `1/2` on `W`, and changes only where `|s| < δ/2`. On every solid material
other than `protein` `χ` SHALL be 1, because the membrane is analytic and not drawn from the
density, and its interface stays sharp. `χ` is built from the profile and not by remapping the
stage-3 mean. The mesh's material interface is the conditioned profile, and conditioning moves it
off the raw isolevel by up to the closing radius. A remap would put its 1/2-level on that isolevel
and give it a width that varies with `|∇ρ|`. The limit δ → 0 of the profile's `χ` is the material
indicator, and therefore PHY-20's piecewise assignment exactly. FR-15's "same density field" holds
because the shell is offset from the same profile (§5.2.1 NOTE on the ion-exclusion shell).

`χ` is sampled at the nodes of a lattice of spacing `δ/20` and read bilinearly, as a supplied field
is. The lattice covers the body's bounding box widened by `δ` and clipped at `r = 0`, so its
boundary samples are 0 by construction. Away from the profile's vertices the interpolation error is
then at most `0.75 (h/δ)² = 1.9 × 10⁻³` (WP30 plan, *Design* §1). A `δ` below
`geometry.density.grid_spacing_nm` would be finer than the grid the contour is placed on, and SHALL
be refused naming both keys.

VER-30's range and registration gates apply, with one amendment that holds for every `χ`, supplied
or derived. `exclusion` lies wholly on the water side of the dielectric contour, so its mean `χ`
SHALL be below 1/2. The fluid ceiling does not apply to it, because a 1–2 Å transition into a thin
shell exceeds that ceiling: a planar shell of width `a` averages `3δ/(32a)`.

### 4.5 Model variants and switches

**PHY-21.** The following physics models SHALL be selectable by name in the case file.

| Model | Equations solved | Corrections |
|---|---|---|
| `epnp-ns` | Poisson + size-modified NP + variable-density NS | all, per §4.3 |
| `pnp-ns` | Poisson + NP + NS | none (`β_i = 0`, all factors 1) |
| `pnp` | Poisson + NP, `u ≡ 0` | selectable |
| `pb` | nonlinear Poisson–Boltzmann | n/a |
| `pb-linear` | linearised Poisson–Boltzmann (Debye–Hückel) | n/a |
| `poisson` | Poisson only, prescribed `ρ_ion` or none | n/a |

Classical PNP-NS SHALL be recovered exactly by setting `β_i = 0` and
`ε_r,f^c = D_i^c = μ_i^c = η^c = ϱ^c = 1` and `D_i^w = μ_i^w = η^w = 1`; no separate code path is
permitted for it.

NOTE (the electrostatic models as case-file models, PHY-20, PHY-24, FR-19, FR-20; WP26): `poisson` solves `∇·(ε_0 ε_r ∇φ) = −ρ_pore` over all of Ω, with the fixed
charge, `physics.solid_permittivities` and the §4.4 `χ` taken as the coupled models take them. It
carries no mobile ions, so the fluid is ion-free water at `ε_r,f⁰` whatever the permittivity
correction (author ruling 13), and `ρ_ion` is none: case schema v2 has no key that prescribes one.
This is the configuration VAL-06 compares with APBS. `pb` and `pb-linear` take `λ_D` from the case,
at `ε_r,f⁰`, the case temperature and `c_0` with unit valence (NUM-09), and SHALL be refused for any
electrolyte other than a symmetric monovalent salt, for which that `λ_D` and the `sinh` form are
exact. They carry no solids, no fixed charge and no `χ`: their screening term is posed on all of Ω,
so a solid domain would screen as if it held ions. They are therefore run only on a mesh with no
solid domain, and an ingested mesh that carries one SHALL be refused naming the model and the
domain (§5.3.1 NOTE on a solid without a permittivity).

**PHY-22.** The corrections SHALL be independently switchable, each resolving to a named model in
the correction registry, with "off" a named model rather than a code branch.

| Switch | Default | Effect when off |
|---|---|---|
| `diffusivity_correction` | on | `f_D^c = f_D^w = 1` |
| `mobility_correction` | on | `f_μ^c = f_μ^w = 1` |
| `viscosity_correction` | on | `f_η^c = f_η^w = 1` |
| `permittivity_correction` | on | `ε_r,f = 78.15` |
| `density_correction` | on | `ϱ = 997.0 kg m⁻³` |
| `steric` | on | `β_i = 0` |
| `variable_density_flow` | on | constant-density Stokes/NS |
| `inertia` | on | Stokes flow (reference model retained inertia; Re ≈ 10⁻⁴) |
| `dielectric_gradient_forces` | off | no Korteweg–Helmholtz body force, no dielectric-decrement term in the NP flux |

NOTE (a switch with nothing to switch; WP42): `concentration: false` or `wall: false` on a property
whose selected correction model applies no such fit SHALL be refused, naming each such part and its
model, because the FR-25 manifest would record a deviation the solve never applies. `none` applies
neither fit, and `willems2020_nacl` has no wall fit for the permittivity or the density. For the
same reason `electrolyte.driver: ionic_strength` SHALL be refused for an electrolyte of two species
of unit valence, for which `I = ½ Σ z_i² c_i` equals `⟨c⟩` exactly (PHY-13; VER-71). Two switches
beside a partner leaf are refused on the same ground (REV-73): `variable_density: false` where the
density correction applies no fit that varies the density (the flow is of constant density already),
and `dielectric_gradient_forces: true` where the permittivity correction applies no concentration fit
(`dε/dc = 0`, so the force vanishes).

**PHY-23.** `dielectric_gradient_forces` SHALL enable both the momentum term
`−½|∇φ|²∇(ε_0 ε_r)` and the Nernst–Planck term `−½|∇φ|² ∂ε/∂c_i` together, and SHALL NOT permit
either in isolation. Enabling it is a deviation from the validated model and SHALL be recorded in
the run provenance.

**PHY-24.** Poisson–Boltzmann SHALL be implemented as a distinct model, not as the PNP solver
evaluated at zero bias (see PHY-14 and ADR-005).

### 4.6 Errata in the source material

Each row records a statement in the published source that the implementation SHALL NOT follow.
Evidence values are computed, not asserted.

| # | Source statement | Correct form | Evidence |
|---|---|---|---|
| 1 | Thesis eq. 5.11 prints the D/μ wall function as `1 − exp(−P₁(d̄ − P₂))` | offset is `(d̄ + P₂)`, as in Table 5.1 | `(d̄+P₂)`: f(0) = +0.0601, f(0.75) = +0.9910, matching the stated 0.06 and 0.99; `(d̄−P₂)`: f(0) = −0.0640, negative at the wall |
| 2 | ESI writes the wall coefficient as `0.62e1`, read in circulation as 62 or 0.62 | `P₁ = 6.2 nm⁻¹` (Table 5.2, Simakov 2010) | f(0)/f(0.75): 62 → 0.4621/1.0000; 0.62 → 0.0062/0.3757; 6.2 → 0.0601/0.9910, the only match |
| 3 | Table 5.1 lists `μ_Na⁰ = 5.192 × 10⁻⁴ m² V⁻¹ s⁻¹` | exponent is 10⁻⁸, per Table 5.2 note (b) | `μ = D⁰/V_T`, `V_T = 25.693 mV`: 5.1922 × 10⁻⁸ (Na⁺), 7.9089 × 10⁻⁸ (Cl⁻), matching Table 5.2 to four figures |
| 4 | Text states `η(c > 5.3 M) = 1.75 × 10⁻⁴ Pa s` | cap is 1.75 × 10⁻³ Pa s | the fit at 5.3 M gives 1.752 × 10⁻³ Pa s; 1.75 × 10⁻⁴ is below pure water (8.904 × 10⁻⁴) while salt raises viscosity. Other caps verified: ϱ = 1194 kg m⁻³, `D_Na` = 8.13 × 10⁻¹⁰, `D_Cl` = 1.071 × 10⁻⁹ m² s⁻¹ |
| 5 | Table 5.2 lists viscosity `P₀ = 0.8904` under a 10⁻⁴ scaling note, implying 8.904 × 10⁻⁵ Pa s | `η⁰ = 8.904 × 10⁻⁴ Pa s`; the scaling is 10⁻³ | Hai-Lang 1996 gives 8.904 × 10⁻⁴ Pa s for water at 298.15 K; 8.904 × 10⁻⁵ is an order of magnitude below any aqueous value |
| 6 | Thesis prints the permittivity cap `ε_r(5.3 M) = 42.12`, reproducible only from the authors' own Buchner-1999 fit (29.50, 11.74) | the model used Gavish's NaCl parameters (30.08, 11.5); the cap is 42.67 | the model parameter table and the solver log both record `epsr_ms = 30.08`, `epsr_alpha = 11.5`; these give 42.67 at 5.3 M against the Buchner fit's 42.13, so the printed cap is stale. An earlier author recollection favouring the Buchner fit is superseded by the model file |
