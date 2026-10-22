---
type: Ruling Record
title: "8.2 Phase 0 exit criteria"
description: "States the four Phase 0 exit criteria, all four of which SHALL be met."
---

### 8.2 Phase 0 exit criteria

All four SHALL be met.

1. All Tier 2 analytic benchmarks (VER-12 to VER-22) pass, including MMS convergence at O(h³) in L²
   for P2 on the full coupled axisymmetric system. This is the primary criterion: it establishes
   that the physics and the axisymmetric discretisation are correct, independently of any other
   implementation.
2. Converged solutions across the full 0.05–3 M × ±200 mV envelope with all corrections active,
   obtained from the continuation ladder, with no negative concentrations at any Newton step.
3. UMFPACK or scipy SuperLU factorises a production-sized problem, about 1.2 × 10⁵ cells with five
   fields, in acceptable time and memory on a laptop. The reference mesh size sets the target.
4. A trivial PySide6 and NGSolve `webgui` application builds into a working double-clickable bundle
   on Windows.

COMSOL comparison is not a Phase 0 gate. Tier 3 runs once criterion 1 is met, and early
disagreement at the per-cent level is expected for the reasons in §7.4.
