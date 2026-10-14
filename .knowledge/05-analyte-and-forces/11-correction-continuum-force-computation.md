---
type: Domain
title: '10. CORRECTION — continuum force computation DOES exist: PlyAB (Angew. Chem.
  2022)'
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
**re-implementation**, not an invention, with regression targets in §10.6.

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

