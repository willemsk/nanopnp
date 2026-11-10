---
type: Reference Settings
title: F. Differences that cannot be removed
description: Differences that cannot be removed.
tags:
- comsol
- reference-settings
sources:
- id: comsol-report
  resource: COMSOL Multiphysics 5.4 model report of 22 May 2020
  title: COMSOL model report (5.4)
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
---

## F. Differences that cannot be removed

| Difference | Consequence |
|---|---|
| COMSOL's `tds.streamline`, `tds.crosswind`, `spf.streamlinens`, `spf.crosswindns` are not exported | nanopnp's `reference` mode implements SUPG and a Do Carmo–Galeão-type crosswind (NUM-14), but not bit-for-bit the same operator. The stabilisation term is therefore an **irreducible systematic** in any comparison, bounded only by mesh refinement |
| "Approximate residual" is a COMSOL-internal choice | Their residual used in the stabilisation is not the exact strong residual |
| Mesh generator | Netgen vs COMSOL's mesher — element counts can match, elements cannot |
| Degrees of freedom | **NOT IN REPORT**; cannot be matched or checked |
| Linear solver internals | PARDISO ordering/pivoting defaults NOT IN REPORT; irrelevant to the converged solution, relevant only to timings |
| Newton type and termination technique | NOT IN REPORT; only the damping bounds and rel. tol. are reproducible |
| Scaling | NOT IN REPORT; COMSOL's automatic variable scaling affects the convergence path and the meaning of "rel. tol. 1e-6" |
| Evaluation boundary for the current | NOT IN REPORT; the paper's main text names the cis reservoir boundary, the grounded one ([C.10](04-physics-settings.md)) |
| `rhoq_pore` interpolation grid | The gridded charge table itself is not in the report — only the function's units (1/m²) and extrapolation mode. Our charge pipeline regenerates it from structure, so the fixed-charge field will differ in detail |
| Geometry polygon | 190 vertices printed in §2.2.2 and reproducible, but our contour pipeline generates its own |
| P1+P1 vs P2/P1 flow | The default Taylor–Hood pair differs by construction, and only the converged velocity field can agree; the `reference` mode permits the equal-order pair (NUM-03, NUM-14) |
