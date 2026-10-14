---
type: Reference Settings
title: F. Differences that cannot be removed
---

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
