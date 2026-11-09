---
type: Numerics
title: 6. Linear solvers
description: "UMFPACK and SuperLU measured at production size, which NUM-21's NOTE cites; NUM-21 and NUM-22 state the solver choices."
tags:
- numerics
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:tests/tier2/test_factorisation_benchmark.py::test_criterion3_superlu_is_a_licence_fallback_not_a_performance_one
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_factorisation_benchmark.py::test_criterion3_umfpack_factorises_a_production_sized_problem
  at: '2026-10-16T00:00:00Z'
---

## 6. Linear solvers

NUM-21 states the solver per path, why direct is right in 2D, and the wheel's missing MUMPS; §6.1
below is the measurement its NOTE cites.

### 6.1 Measured: UMFPACK and SuperLU at production size **[tested: tests/tier2/test_factorisation_benchmark.py::test_criterion3_umfpack_factorises_a_production_sized_problem]** **[tested: tests/tier2/test_factorisation_benchmark.py::test_criterion3_superlu_is_a_licence_fallback_not_a_performance_one]** {#61-measured-umfpack-and-superlu-at-production-size}

The five-field system of NUM-01 on the analytic cylindrical pore — `φ` P2 on all of Ω, `c_±` P2,
`u` P2 vector and `p` P1 on the fluid only — assembled with every coupling block present, then
factorised. One configuration per process, because `ru_maxrss` is a high-water mark and successive
factorisations in one process report the largest so far. Development laptop, WSL2, 24 cores, 15 GB.

| cells | DOF | nonzeros | UMFPACK | peak RSS | SuperLU | peak RSS |
|---|---|---|---|---|---|---|
| 1.50 × 10⁴ | 1.43 × 10⁵ | 8.4 × 10⁶ | 4.4 s | 855 MB | 24.0 s | 2593 MB |
| 3.84 × 10⁴ | 3.68 × 10⁵ | 2.2 × 10⁷ | 14.0 s | 2157 MB | 140.3 s | 8656 MB |
| 1.09 × 10⁵ | 1.04 × 10⁶ | 6.2 × 10⁷ | 41.1 s | 6171 MB | OOM-killed | > 15.4 GB |

**UMFPACK is comfortably viable at the reference mesh size**: 41 s and 6.2 GB at 1.09 × 10⁵ cells.
Its memory grows almost linearly in DOF (×2.52, ×2.86 for DOF ratios ×2.57, ×2.84), consistent with
the O(N log N) fill quoted above, and its time grows as roughly N^1.1 — better than the O(N^1.5)
worst case, which is what good nested dissection on a 2D mesh buys.

**SuperLU is a licence fallback, not a performance one.** It costs ≈ 3.4× the memory and 6–10× the
time, and both gaps widen with size: its time scales as ≈ N^1.8 and its memory superlinearly. At the
reference mesh size it was OOM-killed twice at 15.4 GB anonymous RSS; extrapolating the two smaller
points puts it near 28 GB and ~15 minutes. Converting the NGSolve matrix to scipy CSR costs a
further 0.2–0.7 s and is not the bottleneck.

The consequence bears on CON-11 and ADR-003: **a redistributable bundle cannot simply swap GPL-2+
UMFPACK for BSD SuperLU and keep the same capability.** At half the reference mesh size SuperLU
works but is ten times slower; at the reference size it does not run on a 15 GB laptop at all. If
the copyleft dependency has to go, the replacement is the iterative `PCFIELDSPLIT` path, not
SuperLU.

**Iterative path (held in reserve, required for 3D):** NUM-22. FEniCSx-pctools (arXiv:2402.02523)
shows how such nested field-split specifications are automated.

---

