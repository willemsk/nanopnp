---
type: Reference Settings
title: B. Solver (§3, §4)
description: The COMSOL studies, sweeps and solver settings.
tags:
- comsol
- reference-settings
sources:
- id: esi
  resource: https://www.rsc.org/suppdata/d0/nr/d0nr03114c/d0nr03114c1.pdf
  title: Electronic supplementary information of the paper
- id: comsol-report
  resource: COMSOL Multiphysics 5.4 model report of 22 May 2020
  title: COMSOL model report (5.4)
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:arithmetic
  at: '2026-10-14T00:00:00Z'
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

