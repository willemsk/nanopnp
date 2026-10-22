---
type: Specification
title: "7.5 Tier 4 experimental reproduction"
description: "Lists the Tier 4 experimental reproduction activities (VAL-07 onward), each with its acceptance criterion against experiment."
---

### 7.5 Tier 4 experimental reproduction

| ID | Activity | Acceptance criterion |
|---|---|---|
| **VAL-07** | Conductance versus salt concentration | Experimental range 0.05–3 M, simulated range 0.005–5 M; agreement with experiment no worse than the source paper's own agreement |
| **VAL-08** | I–V response and rectification `α(V_b)` over ±200 mV | Agreement with experiment no worse than the source paper's own agreement, over the full ±200 mV envelope |
| **VAL-09** | Cation transport number `t_Na⁺` | Agreement with experiment no worse than the source paper's own agreement |
| **VAL-10** | Classical PNP-NS ablation | The uncorrected model reproduces the published over-estimation of current, in the same direction and of the same order |

Rationale (VAL-08): a ±150 mV envelope would drop the highest-|V| quarter, where rectification is
largest and Newton convergence hardest.

Rationale (VAL-10): reproducing the documented failure of the uncorrected model is as diagnostic as
reproducing the success of the corrected one.

### 7.5.1 Analyte force validation targets

The analyte force and PMF capability has a published continuum reference: Huang et al.,
*Angew. Chem. Int. Ed.* **61**, e202206227 (2022), DOI `10.1002/anie.202206227`. That work solved
the full ePNP-NS system in COMSOL 5.5, 2D-axisymmetric, with haemoglobin represented as a body of
revolution of height 6.7 nm and width 5.8 nm carrying a uniform volumetric charge
`rho_part = q_Hb/V`, scanned over −100 ≤ z ≤ 100 nm, and integrated the force to a PMF.

| ID | Activity | Acceptance criterion |
|---|---|---|
| **VAL-11** | Force components against the PlyAB reference | At `V_b` = +50 mV, `q_Hb` = −4 e, 300 mM NaCl: `F^em` and `F^hd` each of magnitude approximately 10 pN and of opposite sign, `F^em` directed towards *trans* and `F^hd` towards *cis* |
| **VAL-12** | PMF minima | Energy minima recovered at z = −2.5 nm and z = +5.25 nm |
| **VAL-13** | Residual current on lumen entry | Simulated residual current falls to approximately 40 % on lumen entry; experimental `I_res` for HbA is 18.5 ± 0.4 % and 40.2 ± 0.7 % |
| **VAL-14** | Electro-osmotic force coefficient, ClyA | `F_eo` = 9 pN at −50 mV, equivalently 0.178 pN/mV, corresponding to `N_eo` = 15.5 ± 0.9 e |

NOTE: `F^em` and `F^hd` nearly cancel, so the accuracy requirement on each integral (NUM-29) is set
by the residual rather than by the magnitude of either term.

NOTE: the ACS Nano 2019 trapping work is not a continuum analyte calculation. It uses equilibrium
Poisson–Boltzmann in APBS on a coarse-grained bead model with a one-dimensional analytic rate
model, and provides no stress-tensor force profile. Detail in
`knowledge/05-analyte-and-forces/11-correction-continuum-force-computation.md`.

