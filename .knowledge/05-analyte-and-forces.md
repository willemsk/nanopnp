# Analyte bodies and forces — what the thesis actually contains

**Status:** authoritative *for what the source says*, and explicitly negative where the source is
silent. Transcribed from `chapters/trapping/trapping.tex` (= Willems, Ruić, Biesemans et al.,
*ACS Nano* **13**(9), 9980–9992, 2019) and `chapters/trapping_appendix/trapping_appendix.tex`, with
supporting material from `chapters/nanopores/nanopores.tex` (background theory),
`chapters/electrostatics/electrostatics.tex` (APBS method), `chapters/transport/transport.tex`
(ch. 6) and `chapters/conclusion/conclusion.tex`. Governing equations, corrections and symbols live
in `knowledge/01-physics-epnpns.md` and are not repeated here.

---

## 0. Read this first — the ACS Nano 2019 work contains no continuum analyte

**There is no ePNP-NS simulation of an analyte anywhere in the thesis.** The trapping chapters
solve (a) equilibrium Poisson–Boltzmann in **APBS** for a coarse-grained bead analyte, and (b) a
**1-D analytic double-barrier rate model** fitted to experimental dwell times. No Maxwell-stress
integral, no hydrodynamic-stress integral, no ALE/moving mesh, no analyte surface in a
Navier–Stokes domain, no computed force profile F(z). The single force number quoted (9 pN) comes
from a **fitted charge parameter**, not a stress integral.

> **⚠ SUPERSEDED IN PART — read §10 first.** Everything in this section remains true *of the thesis
> and of ACS Nano 2019*. But the conclusion once drawn from it — that no continuum force computation
> exists anywhere in this body of work — is **wrong**. Willems published exactly that calculation
> for PlyAB + haemoglobin in **Angew. Chem. Int. Ed. 2022, 61, e202206227**, after the thesis. See
> **§10**. The "future work" sentence below was written *before* that paper existed.

Coupled ePNP-NS with an embedded particle is **future work** (`conclusion.tex
§sec:con:perspectives`: "*low-hanging fruits: … (2) computing the net force exerted on
translocating analyte molecules … the full electrophoretic and hydrodynamic force landscape*").
Spec G5 is therefore a **new capability**; its only anchors are (i) the APBS energy landscape,
(ii) the fitted N_eo ≈ +15.5 e, (iii) the pore-only ePNP-NS fields of ch. 6.

---

## 1. Analyte geometry (APBS bead model)

`trapping.tex §sec:trapping:methods`, `fig:trapping_apbs_model`.

| Item | Value |
|---|---|
| Analyte | *E. coli* DHFR + C-terminal polypeptide tag ("DHFR_Ntag_X") |
| Representation | coarse-grained beads, treated as **pseudo-atoms** in a PQR file |
| Body | **7 beads**, r = 0.8 nm (1.6 nm dia.), spherical arrangement, **0.8 nm** spacing → ~3.2 nm overall |
| Tag | **9 beads**, r = 0.5 nm (1.0 nm dia.), **linear** string, **0.6 nm** spacing, one bead per 3 residues (α-helix) |
| Body of revolution? | **No** — but deliberately built to be *nearly* axially symmetric |
| Positioning | placed on the **pore central z-axis** with custom Python + Biopython |
| Scan | z_body = **−12.5 nm → +27.5 nm** rel. bilayer centre, **0.5 nm** steps inside the pore |
| Per position | **new PQR + full APBS solve** (Cartesian grid). No ALE, no moving mesh, no remesh — the concept does not apply to a finite-difference PB solver |
| Real DHFR size | 3.5–4 nm; ClyA *trans* constriction 3.3 nm dia. × 4 nm; *cis* lumen 5.5 nm dia. × 10 nm; pore length **L = 14 nm** |

Two stated reasons for coarse-graining (`trapping.tex`, "Energy landscape of DHFR in ClyA"):
(1) "*the high degree of axial symmetry in the bead model resulted in a free energy that was
independent of the precise orientation of DHFR*" — the author already relies on the analyte being
effectively a body of revolution; (2) the **shrunken body** (3.2 vs 3.5–4 nm) lets it pass the
3.3 nm constriction without atom overlap, since APBS cannot model conformational change.
Consequence, verbatim: the **energy maxima "should be viewed as indicative and not absolute."**

## 2. Charge representation — both forms, and where each is used

**(a) Analyte, ACS Nano 2019 — discrete per-bead point charges, B-spline discretised.** Each bead
carries the net charge of the residues it represents; PDB2PQR assigns CHARMM36 radii/charges at
pH 7.5, and APBS spreads charge onto its grid with cubic B-splines (`chgm spl2`, `srfm spl2`).
Body beads: **Q_i = N_body/7** each. Tag beads: **δ_i = −3 … +3 e**.

> **Internal inconsistency.** `fig:trapping_apbs_model` and `§methods` give Q_i = **−1.43 e**
> (7 × −1.43 = −10 e = N_body of DHFR-4S); the running text gives Q_i = **−1.7143 e**
> (7 × = −12 e = N_body of the -I/-C/-O1 variants). Both are self-consistent for *different*
> variants. Implement as `Q_i = N_body / 7`.

**(b) Pore, ePNP-NS ch. 6 — Gaussian-smeared charge, "surface" then volumetric.** `transport.tex
eq:scdpore`. Written as a 2-D areal density in the (r,z) half-plane:

```
σ_pore(r,z) = Σ_i [ e·δ_i / (π (s·R_i)²) ] · exp( −[(r−r_i)² + (z−z_i)²] / (s·R_i)² )
```

with sharpness `s = 0.5`, R_i the CHARMM36 atom radius, r_i = sqrt(x_i²+y_i²), each atom
pre-weighted by the azimuthal factor δ_i/(2π r_i), grid spacing **0.005 nm**. Then, *inside
COMSOL*, "*the surface charge density σ_pore(r,z) was imported as a 2-D linear interpolation
function and **converted into a pseudo-3-D volumetric charge density by normalization over the
local circumference of each element (2πr)***", "*applied across all computational domains*".
Check: ∫ρ dV = **−72.9 e** vs −72 e atomistic (1.2 % error).

The two forms are therefore **one pipeline at two stages** — areal in (r,z), volumetric after the
1/(2πr) conversion — not two competing models. **No analyte-surface charge density σ_s appears
anywhere in the thesis**; an σ_s option on an analyte boundary is a new modelling choice, default
it off.

## 3. Dielectric constant and boundary conditions

| Quantity | Trapping / APBS (`trapping.tex §methods`) | ePNP-NS (`01-physics-epnpns.md`) |
|---|---|---|
| Solute (protein) ε_r | **10** (cites Li 2013) | **20** (ε_r,p, cites Li 2013) |
| Solvent ε_r | 78.15 | 78.15 × ε_r,f^c(⟨c⟩) |
| Salt | 0.150 M monovalent, ion radius 0.2 nm | full ePNP |
| Solver | non-linear PBE `npbe`, `mg-auto`, `bcfl mdh`; coarse box 40×40×110 nm @ 0.138/0.138/0.122 nm; focused box 15×15×70 nm @ 0.052 nm | FEM |

The **ε_p = 10 vs 20 conflict is real and unexplained** — same reference, two chapters. Make it a
config value.

**Analyte boundary conditions: not specified anywhere in the thesis**, because no analyte appeared
in the transport model. The only BCs given are pore + membrane (`n·J_i = 0`, `u = 0`, ε jump;
`01-physics-epnpns.md §2`). Reusing those three on an analyte surface is an *inference* — mark it
as such in code.

## 4. Force computation — the analytic model actually used

`trapping_appendix.tex §sec:trapping_appendix:single_barrier_system`. Both external forces are
assumed **constant along the pore** (linear potential drop over L = 14 nm), i.e. spatially uniform
1-D scalars, not fields:

```
F_ep  = e · N_net · V_b / L            (eq:forceep,     N_net = N_body + N_tag)
F_eo  = e · N_eo  · V_b / L            (eq:osmoticforce)
E_ep(x) = −F_ep·x + b_ep ,  E_osm(x) = −F_osm·x + b_osm
ΔE^cis = −F·Δx_cis ,  ΔE^trans = +F·Δx_trans
```

`N_eo` = **equivalent osmotic charge number** — "*the number of charges that must be added to DHFR
to create an equal electrophoretic force*"; asserted to be "*an invariant related solely to the size
and shape of the molecule*". That is the entire force model: **no Maxwell stress, no
dielectric-gradient term, no pressure/viscous decomposition, no surface integral.**

The *general* framework the author endorses (background ch. 2, `nanopores.tex`; adopted by the spec):

```
F_ele = ∮_Γ (T_E · n) dΓ ,   T_E = ε E E − ½ ε (E·E) I        (eq:nanopores_electric_force)
F_hyd = ∮_Γ (T_H · n) dΓ ,   T_H = p I − η[∇u + (∇u)ᵀ]        (eq:nanopores_hydrodynamic_force)
```

magnetic terms of T_E set to zero. The full-tensor form captures **both EP and dielectrophoretic**
contributions (F_DEP = (p·∇)E) with no shape assumption; Stokes' law F_d = −6πηaU is only a
first-order stand-in valid outside the pore. `conclusion.tex` (l. 180) makes it a finding: the
5–30 atm pressure hotspots mean the pressure term is non-negligible, "*confirming the importance of
using the full hydrodynamic stress tensor to calculate the force, rather than just the Stokes'
drag*". T_H is the **same** tensor as in the momentum equation (`01-physics-epnpns.md §2.3`), so η
is the corrected position-dependent viscosity — the integrand inherits the wall correction.

**Sign, resolved [tested].** `T_H = p I − η[∇u + (∇u)ᵀ]` as printed above is the *negative* of the
Cauchy stress the momentum equation is written in, which is `T_H = −p I + 2 η sym ∇u` with
`∇·T_H + f = Re ϱ(u·∇)u` — a positive pressure pushing outward. NUM-28 and
`post/forces.hydrodynamic_stress` use the momentum-equation convention, because the domain form is
derived from that divergence and mixing the two flips the force. The two conventions give the same
physics and opposite numbers, so the rule is: whichever is chosen, the tensor in the force integral
and the tensor in the residual must be the same one. `T_M = ε(E ⊗ E − ½|E|²I)` has no such ambiguity
— `E` appears twice, so the sign of `E` cannot leak into it.

## 5. From energy landscape to rates (no Boltzmann inversion, no Kramers)

The PMF is built **forward** (energy → rates), never inverted from a force profile.

1. **Equilibrium landscape:** `E_elec(z) = G_pore+part − G_pore − G_part` (`electrostatics.tex
   eq:electrostatic_energy`), one APBS triple per z.
2. **Tilt by bias** (`trapping.tex eq:external_energy_model`), N_tot = N_body + N_tag + N_eo:
   `E_ext = N_tot·(V_b/14 nm)·(z − 11 nm)` for −3 < z < 11 nm; `0` for z ≥ 11 nm; `N_tot·V_b` for
   z < −3 nm. Total `E_V = E_elec + E_ext`.
3. **Escape rate:** from a Boltzmann kinetic-energy distribution, energy-independent density of
   states Z, step transmission `c(E)=c₀·θ(E−ΔG)` → `k = Z c₀ exp(−ΔG/kT) ≡ k₀ exp(−ΔG/kT)`.
   Arrhenius, **not Kramers** — no friction or curvature prefactor anywhere.
4. **Double barrier:** `1/τ = k = k_eff^cis·exp(−ΔG^cis/kT) + k_eff^trans·exp(−ΔG^trans/kT)`,
   ΔG = ΔG_steric,0 + ΔG_static,0 + N_tag·e·Ψ_tag ∓ (N_net+N_eo)·e·(Δx/L)·V_b (`eq:double_barrier_complex`).
5. **Translocation probability:** `P_trans = k^trans/(k^cis + k^trans)` (`eq:ptrans`).
6. **Dwell-time statistics:** single bound state → exponential, τ = 1/k, Var = τ². Multi-state →
   sum of exponentials whose expectation is the **arithmetic mean of the level lifetimes**
   (`eq:tau_arithmetic_mean`) — hence the experimental τ is a plain mean.

## 6. Electro-osmosis vs electrophoresis

The dimensionless characterisation is `N_eo` itself, and the ratio `N_eo / |N_net|`:

| Quantity | Value |
|---|---|
| N_eo (fitted, all DHFR_Ntag_O2 simultaneously) | **+15.5 ± 0.9 e** |
| N_net over the variant series | −9 … −4 e (opposite sign) |
| ⇒ EOF/EP force ratio | **1.7× … 3.9×**, EOF wins at every tag charge |
| Context | 99 % of proteins carry |q| ≤ 10 e → EOF "quantitatively confirmed" as the dominant capture force (`conclusion.tex`) |
| Reynolds number (background) | ρ v d/η ≈ **5 × 10⁻⁴** for d = 5 nm, v = 0.1 m/s — laminar |

No Péclet, Dukhin or Debye-ratio number is used.

## 7. Validation targets

**Forces / fields** (V_b negative = *cis*→*trans*; F_eo pushes *cis*→*trans*, i.e. **into** the pore):

| Quantity | Value | Condition |
|---|---|---|
| F_eo | **≈ 9 pN** (0.178 pN/mV; recompute: 8.87 pN) | V_b = −50 mV, N_eo = 15.5, L = 14 nm |
| F_ep on DHFR_7_O2 (N_net = −6) | 3.4 pN, opposing | same |
| Axial field | ≈ 3.5 × 10⁶ V/m | −50 mV over 14 nm |
| Coulomb force, 10 e protein (background) | ≈ 4 pN | `nanopores.tex` |
| Stokes drag, 5 nm sphere at 0.1 m/s (background) | ≈ 4 pN | `nanopores.tex` |
| EOF velocity, ch. 6 ePNP-NS | **0.07 m/s** (lumen centre), **0.21 m/s** (constriction) | −100 mV, 0.5 M |
| EOF conductance Q/V | 1.85 → **11.3** (peak, 0.5 M) → 4.00 nm³ ns⁻¹ V⁻¹ | −150 mV, 0.005 → 5 M |
| Pressure hotspots | 5–30 atm at z ≈ 11, 4.5, −1 nm | 0.15 M, 0 mV |

**Landscape geometry (APBS, DHFR_Ntag_O2):** minimum z_body = **+3 nm**; *cis* max **+5.7 nm**;
*trans* max **−0.6 nm**; Δx_trans = **3.5 nm** (fixed); Δx_cis = 2.7 nm at equilibrium but
**5.21 ± 1.32 nm** fitted — the *cis* barrier vanishes above |V_b| ≈ 50 mV and relocates to the
*cis* entry (z ≈ 10–13 nm).

**Barrier gradients [kT per elementary charge]:**

| Source | trans | cis |
|---|---|---|
| APBS, per extra **body** negative charge (−10→−13 e) | 1.46 | 0.04 |
| APBS, per extra **tag** positive charge (+4→+9 e) | 0.875 | 0.621 |
| Fitted Ψ_tag (Table `tab:fitting_params_complex`) | **0.860 ± 0.078** | **0.218 ± 0.167** |

**Fitted attempt rates:** ln(k_eff^trans/Hz) = −3.44 ± 1.24 (3.21 × 10⁻² Hz);
ln(k_eff^cis/Hz) = 7.39 ± 1.02 (1.62 × 10³ Hz). Fixed: N_body = −13, L = 14 nm, Δx_trans = 3.5 nm.

**Peak dwell times τ_thresh and threshold voltages |V_thresh|** (complex model, DHFR_Ntag_O2, 150 mM
NaCl / 15 mM Tris pH 7.5 / 28 °C):

| N_tag | +4 | +5 | +6 | +7 | +8 | +9 |
|---|---|---|---|---|---|---|
| τ_thresh [s] | 2.28 | 4.16 | 7.59 | 13.9 | 25.3 | 46.2 |
| \|V_thresh\| [mV] | 87.3 | 79.2 | 73.0 | 68.1 | 64.1 | 60.4 |

≈ 5.2–5.4 mV less bias per added tag charge. Also: P_trans = **0.002 %** at zero bias and zero tag
charge; V(P_trans = 99.9 %) shifts −130 → −85 mV over N_tag +4 → +9 while the *cis* (0.01 %) line
moves only −40 → −35 mV; DHFR_5_O2 τ = 0.32 ± 0.17 s at −60 mV; I_res ≈ 67–75 % (L1), 46–58 % (L2),
~39 % (L3); NADPH k_on = 1.39–2.03 × 10³ s⁻¹ mM⁻¹, k_off = 56–71 s⁻¹ at −60 mV; residual current
rises ≈ 2.5 % from −60 → −100 mV (position shift, not stretching — unfolding needs 27 pN apo /
98 pN NADPH-bound).

## 8. Stated limitations, and off-axis behaviour

- Bead model is **on-axis only**; free energy declared orientation-independent *by construction*
  (near-axial symmetry). Off-axis positions were never computed.
- Energy **maxima are "indicative and not absolute"** — the body was shrunk to avoid overlap in the
  constriction, so real steric blocking is under-represented. All steric physics is dumped into the
  constants ΔG_steric,0, absorbed into k_eff.
- The model depends on **N_tag only**; variants with identical N_body but different charge
  *locations* (DHFR-4I / -4C / -4O1) differ 10-fold in dwell time and are **not** describable
  (`trapping_appendix.tex §sec:trapping_appendix:body_charge_variations`). Verdict: a location-aware
  analytic model "*would drastically increase in complexity*", use refined APBS or MD. Charges far
  from the tag are harmless; charges near it effectively renormalise N_tag.
- Multiple current levels (L1/L2/L3) imply **several axial minima**, uninvestigated — a v1 F(z)
  sweep should resolve them.
- Generally, `conclusion.tex`: axisymmetric averaging "*imposes an inherent limit on the accuracy*",
  smears corrugation, and puts some charge in the electrolyte rather than the dielectric. 3D is the
  long-term fix; 2D-axisymmetric is kept for speed/screening.

## 9. Gaps and ambiguities

1. **Stress-tensor forces on an analyte are absent from the trapping chapters.** The tensor
   expressions come from background ch. 2 and were never evaluated for an analyte *in the thesis*.
   **Partly superseded — see §10:** they *were* evaluated, for PlyAB + haemoglobin, in Angew. Chem.
   2022; §10.6 gives regression targets. Analytic tests (isolated sphere: Maxwell integral → qE;
   Stokes sphere → 6πηaU) remain the right first check.

   **Done, and they were the right first check [tested]** (WP6, `tests/tier2/`). On a P2 sphere of
   radius 1 nm in a box of radius 10 nm, `a = 1 nm` mesh units, the numbers are:

   | Check | Measured | Reference |
   |---|---|---|
   | Stokes drag, three meshes (VER-19) | 0.430870, 0.430522, 0.430500 pN | `6πηaU` = 0.430491 pN |
   | its relative error | 8.80 × 10⁻⁴ → 7.11 × 10⁻⁵ → 1.98 × 10⁻⁵ | rates 3.63 and 1.85 per halving |
   | Maxwell integral on an uncharged dielectric sphere (VER-20) | −8.6 × 10⁻⁸ pN (domain), +7.0 × 10⁻⁵ pN (surface) | 0 |
   | `F = qE₀` anchor, −4 e at 5.1 MV/m (VER-20) | −8.21704 pN (domain), −8.18903 pN (surface) | −8.23281 pN, i.e. 0.19 % and 0.53 % |
   | Henry mobility at κa = 0.50 / 2.08 / 16.47 (VER-21) | `μ̃_e/ζ̃` = 0.661, 0.704, 0.872 | `2f(κa)/3` = 0.676, 0.711, 0.885 |

   Two findings worth carrying forward. **The far field decides whether VER-19 measures anything**:
   a uniform stream at `R = 10a` gives 1.285 × the drag, the `1 + (9/4)(a/b)` wall correction of a
   sphere in a concentric container, so the exact Stokes field has to be imposed instead. And **the
   zero test cannot stand alone**: a net force of zero on a polarised sphere is invariant under a
   uniform scale factor, so the `qE₀` anchor is what pins the magnitude of the Maxwell route, which
   has no reaction-route oracle because `φ` is not constrained on the body's surface.
2. **"Surface charge density vs smeared volumetric charge" resolves to one pipeline, not two
   models** (§2). If the author meant a genuine σ_s on an analyte boundary in other work, it is not
   in the thesis — ask.
3. **ε_protein = 10 (trapping) vs 20 (ePNP-NS)**, same citation. Unresolved.
4. **Body bead charge printed as both −1.43 e and −1.7143 e** (§2a). Resolve as N_body/7.
5. **`eq:threshold_voltage_complex` has a typo:** it prints `log(Δx_trans / Δx_trans)` ≡ 0;
   re-deriving dk/dV_b = 0 gives `log(Δx_trans / Δx_cis)`. Check with the fitted parameters
   (kT/e = 25.69 mV): corrected → 87.7 mV (N_tag +4), 61.1 mV (+9) vs published 87.3 / 60.4; the
   zero term gives 85.1 / 59.6. **The corrected form reproduces the published table.**
6. **Sign convention is sloppy:** V_b is negative throughout, yet V_thresh is tabulated positive
   (the leading minus makes it a magnitude). Pick one convention and assert it in tests.
7. **`f(t) = k·e^{−kT}`** (`trapping_appendix.tex §single_bound_state`) is a typo for `k·e^{−kt}`;
   the correct exponent appears two lines later.
8. **Δx_cis is ill-defined by the author's own admission** (voltage-dependent barrier location) — a
   fit parameter, not a geometric constant. A v1 PMF that locates the *cis* barrier should report
   against both 2.7 nm and 5.21 nm.
9. **Caption/text conflict:** `trapping_translocation_voltage` says the threshold voltage
   "increases" ≈5.21 mV per tag charge; the text says "decrease of ≈5 mV". Both describe |V_thresh|
   falling 87.3 → 60.4 mV; the caption means the signed value.
10. **N_eo "depends solely on size and shape"** — untested, and exactly what a v1 F(z) sweep can
    falsify: check whether F_hyd/V_b is constant across salt and bias at fixed geometry. Hypothesis,
    not result.

---

## 10. CORRECTION — continuum force computation DOES exist: PlyAB (Angew. Chem. 2022)

**Source.** G. Huang, K. Willems, … G. Maglia, *"PlyAB Nanopores Detect Single Amino Acid
Differences in Folded Haemoglobin from Blood"*, **Angew. Chem. Int. Ed. 61 (34), e202206227
(2022)**, DOI `10.1002/anie.202206227`, open access, PMC9541544. Published **after** the thesis, so
absent from `chapters/`. Facts below come from the **main text + Figure 2 caption** (Europe PMC
full-text XML). The **Supporting Information could not be retrieved** here (Wiley robots-blocked,
PMC captcha, `research.rug.nl`/`chemrxiv.org` egress-blocked); the ChemRxiv preprint
`60e73fa0b95bdd4c74603428` is an **earlier version with no simulations at all**. Anything the main
text does not state is marked **UNVERIFIED**, not guessed.

### 10.1 What exactly is corrected

§0's sentence *"There is no ePNP-NS simulation of an analyte anywhere in the thesis"* is **still
true**, and §§1–5 (APBS bead model, 1-D double-barrier rate model, fitted N_eo = +15.5 e) remain a
correct description of **ACS Nano 2019** — do not discard them. What was wrong is the **inference**
drawn in §0 and §9.1: that no continuum force computation exists anywhere in this body of work, and
that spec G5 is a new capability. **It exists.** Here an analyte sits inside the ePNP-NS domain and
**F(z) is computed by the solver**. The tensor framework quoted in §4 as "the *general* framework
the author endorses" is the one he **actually implemented**. G5 is therefore a
**re-implementation**, not an invention; §9.1's "Nothing to regress against" is superseded by §10.6.

### 10.2 The continuum model

| Item | Value | Evidence |
|---|---|---|
| Solver | **COMSOL Multiphysics v5.5**, finite element | *"…used to numerically solve the extended Poisson-Nernst-Planck-Navier-Stokes (ePNP-NS) equations"* |
| Model | **full ePNP-NS**, not reduced | same quote |
| Dimensionality | **2-D axisymmetric** | *"2D-axisymmetric continuum modelling"* |
| Steady state | assumed (stationary fields per position) | UNVERIFIED |
| Domains | *"PlyAB, the lipid bilayer, and Hb were modelled as **solid dielectric blocks**"* | verbatim |
| Pore charge | **all-atom homology model of PlyAB-E1**, *"maintaining the corrugated surface and complex charge distribution"*; `ρ_pore` drawn **inside the solid dielectric** | = the §2(b) smeared-charge pipeline |
| Electrolyte | **300 mM NaCl, pH 7.5** | matches experiment |
| Sweep | **−100 ≤ z_Hb ≤ 100 nm**, **0 ≤ V_b ≤ +100 mV**, **0 ≤ q_Hb ≤ −20 e** | verbatim |
| z step | UNVERIFIED (heatmaps at z = −10, −5, −2.5, 2, 5.25 nm) | |

Sign convention: **negative z = *trans*, positive z = *cis***; *"a positive force means that Hb is
pushed up, i.e., towards cis"*. Hb is scanned *trans* → *cis*.

### 10.3 The analyte

| Item | Value |
|---|---|
| Analyte | Haemoglobin (HbA / HbS / HbF), ~64 kDa tetramer |
| Geometry | **idealised**: *"approximated by a smooth cylinder-like particle (h = 6.7 nm, w = 5.8 nm)"* — a **body of revolution** |
| From PDB? | **No.** `2DN1` is cited for the cartoon and the charge-vs-pH curve, **not** to build the simulated body. Provenance of 6.7/5.8 nm UNVERIFIED |
| Charge model | **smeared volumetric**: *"uniform charge density (ρ_part = q_Hb/V)"*. **Not** a surface charge density σ_s |
| Net charge | pH 7.5: **HbA −3.74 e**, **HbS −1.74 e**, *"calculated from their molecular structures"*. Production runs used **q_Hb = −4 e** (≡ pH ≈ 7.55 HbA, ≈ 7.75 HbS) |
| ε_r of Hb | **UNVERIFIED** (SI). Candidates from §3: 10 or 20 |
| Surface BCs | **UNVERIFIED** (SI). The §3 inference (`n·J_i = 0`, no-slip, ε jump) is now *more* plausible — Hb is a "solid dielectric block" like the pore — but still unconfirmed |

This settles §9.2 in favour of **volumetric smeared charge for the analyte too**. An analyte σ_s
still has no textual support anywhere; keep it off by default.

### 10.4 The force computation — what is and is not stated

Two forces are computed by the solver and summed:

```
F^tot(z_Hb) = F^hd(z_Hb) + F^em(z_Hb)
```

verbatim: *"This produced a detailed description of the ionic and water currents flowing through the
pore, together with the **hydrodynamic (F^hd)** and **electromechanical (F^em)** forces acting on
the Hb molecule"*; *"The sum of these forces … represents the total external force exerted on Hb at
equilibrium."*

**Critical negative result, checked explicitly:** the strings *"stress tensor"*, *"Maxwell"* and
*"integrated over"* **do not appear anywhere in the main text or captions**. No integral expression,
no integration surface, no COMSOL operator names — that detail lives in the unreachable SI. Hence:

- **CONFIRMED:** the analyte force comes out of the ePNP-NS solve, split into exactly **two** terms.
- **STRONG INFERENCE, not verified:** "electromechanical force" is COMSOL's own label for its
  **Force Calculation** feature, which integrates the **Maxwell stress tensor over the exterior
  boundaries of the selected domain** — i.e. `F_ele = ∮_Γ(T_E·n)dΓ`, `T_E = εEE − ½ε(E·E)I` of §4,
  over the **Hb surface**; `F^hd = ∮_Γ(T_H·n)dΓ`, `T_H = pI − η[∇u+(∇u)ᵀ]`, same surface. Matches §4
  term-for-term and `conclusion.tex`'s insistence on full T_H over Stokes drag.
- **NOT decomposed** into electrophoretic / electro-osmotic / drag. The split is **electromechanical
  vs hydrodynamic** — tensor-native. Do not expect an F_ep/F_eo split from the published curves.
- **Mesh handling: UNVERIFIED.** No mention of ALE, moving mesh or remeshing; a parametric sweep
  with remesh per z_Hb is likely but unstated.

### 10.5 Force → energy landscape → Brownian dynamics

Verbatim: *"the cumulative integration of F^tot over z yields the potential energy landscape
(ΔU^tot = −∫F^tot dz)"* — a **direct PMF-from-force construction**, the opposite direction from §5,
where the thesis builds energy first and never inverts a force. Then *"1D Brownian dynamics (BD)
simulations … in which thermal fluctuations were added on top of the energy landscapes"*, yielding
*"a current trace, but also a position trace"* — simulated electrophysiology from the PMF. BD
parameters (D, timestep, friction) **UNVERIFIED**.

### 10.6 Validation targets (PlyAB + Hb)

| Quantity | Value | Condition |
|---|---|---|
| \|F^em\|, \|F^hd\| | **≈ ±10 pN**, *"closely matched but opposing magnitudes"*; **F^em → *trans* entry, F^hd → *cis* entrance** | V_b = +50 mV, q_Hb = −4 e |
| F^tot zeros | several; two are minima of ΔU^tot | same |
| Energy minima | **z_Hb = −2.5 nm** (→ level L₂) and **z_Hb = +5.25 nm** (→ level L₁) | same |
| Separating maximum | caption prints **z_Hb = −2.5 nm**, which is one of the minima — **apparent typo**, true value UNVERIFIED (plausibly ≈ +2.5 nm) | same |
| Simulated I_res(z) | **100 % → 40 %** on entering the lumen, *"remains stable at 40 % until Hb reaches the cis constriction"* | same |
| Experimental I_res, L₁ | **18.5 ± 0.4 %** (HbA), **17.6 ± 0.3 %** (HbS) | +50 mV, 300 mM NaCl |
| Experimental I_res, L₂ | **40.2 ± 0.7 %** (HbA), **37.9 ± 0.4 %** (HbS) | same |
| L₂ dwell times τ_D,2 | **1.7 ± 0.5 ms** (HbA), **0.8 ± 0.2 ms** (HbS) | same |
| Barrier heights (kT), EOF velocity, capture rate, open-pore conductance | **not given numerically in the main text — UNVERIFIED**; Fig. 2c shows \|U\| heatmaps only | |

Note the near-cancellation `F^em ≈ −F^hd`: the landscape is a **small difference of two ~10 pN
numbers**. Any reimplementation must resolve F^tot to well under 1 pN, which sets the accuracy bar
for both stress integrals — this is the single most important numerical lesson here.

### 10.7 PlyAB geometry (thesis-verified, `nanopores.tex §sec:np:plyab`, `electrostatics.tex`)

| Item | Value |
|---|---|
| PDB (full pore, cryo-EM, Cα only) | **4V2T** (Lukoyanova & Kondos 2015); monomers **4OEB** (PlyA), **4OEJ** (PlyB) |
| Oligomeric state | **13-fold symmetry**, 39 chains, **(BA₂)₁₃** = 26 PlyA + 13 PlyB |
| Mass | **1067 kDa** (thesis caption; ">1000 kDa" in text) |
| Overall | mushroom, **height 13 nm**, head Ø **22 nm**, stem Ø **9 nm** |
| *cis* chamber | conical, **3 nm** high, **10.5 nm** entry Ø |
| Constriction | **5.5 nm** Ø at 3 nm depth |
| *trans* lumen | cylindrical β-barrel, **10 nm** long, **7.2 nm** Ø |
| Interior charge | *"predominantly negatively charged, particularly at the constriction and in the middle of the lumen"* |
| Variant simulated in the 2022 paper | **PlyAB-E1** — all-atom homology model. **Not** a thesis variant; the thesis covers WT, **E2** (PlyA C62S/C94S; PlyB N26D, N107D, G218R, A328T, C441A, A464V) and **R** (…, K255E, E260R, E270R, …). The E1 mutation list is **UNVERIFIED** |
| Net charge of pore | **UNVERIFIED** (no number in either source) |

Homology pipeline (thesis `electrostatics.tex §sec:elec:methods:molec`, marked "adapted from
Huang-2020" — i.e. the same pipeline the 2022 paper used): PyMOL `align` of the soluble monomers
onto the cryo-EM Cα's → MODELLER `automodel` → Flex-EM annealing → symmetry-constrained MDFF (NAMD).

### 10.8 Still unknown (needs the SI, or the author)

1. **Explicit force integrals and integration surface** — §10.4 is inference, not quotation.
2. **ε_r of Hb** and the Hb-surface BCs; **mesh strategy per z_Hb** (remesh vs ALE).
3. **Barrier heights in kT**, BD parameters, EOF velocities, capture rates, open-pore conductance.
4. **PlyAB-E1 mutation list and net charge.**
5. Which corrections (`01-physics-epnpns.md`) were active, notably ε_r,f^c(⟨c⟩).
6. Highest-value next target: the SI of the **companion paper** — Huang, Willems, Bartelds, Van
   Dorpe, Soskine, Maglia, *Nano Lett.* **20**, 3819–3827 (2020), "Electro-Osmotic Vortices Promote
   the Capture of Folded Proteins by PlyAB Nanopores", DOI `10.1021/acs.nanolett.0c00877`
   (`mypapers.bib @Huang-2020`; possibly PMC7227020). **Not retrieved** — egress-blocked here.
