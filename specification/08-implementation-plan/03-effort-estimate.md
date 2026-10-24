---
type: Specification
title: "8.3 Effort estimate"
description: "Estimates effort to the validated release: 6 to 9 part-time months without the desktop GUI, 9 to 14 with it."
---

### 8.3 Effort estimate

Estimate to the validated release (v0.7, Phase 6; §8.2.5 E2, §8.2.6 F1) without the desktop GUI: 6–9
months of part-time work. With the desktop GUI: 9–14 months. Both figures are for one person; the
calendar halves at full-time effort. Since §8.2.6 F1 the GUI phase precedes the validated release, so
the second figure is the one that applies, and Phase 4, which neither figure counts, adds 4–6 weeks
(§8.2.9 I5). Neither figure counts the workbench's tool phases (§8.2.17 S7), whose estimates their
own plans set.

Factors making the work more tractable:

- The reference implementation is retained as a differential-testing oracle, with reference
  solutions available on demand.
- The v1 target is 2D axisymmetric and steady, so a direct sparse solve stays viable to about
  2–5 × 10⁶ DOF and MPI is off the critical path.
- The parallelism required is many independent serial solves, which is job-array dispatch rather
  than domain decomposition.
- The physics is published, validated and CC-BY-4.0: correction functions, parameters and
  implementation details are in the ESI, the thesis source and the model report.
- The final pore polygon is published and the table is in the repository (§5.2.1), so solver work
  can proceed on it as a fixture.
- The reference mesh used isotropic grading only, with no boundary layers.

Factors making the work less tractable:

- The contour to CAD to mesh handoff: a raw iso-contour of an ensemble-averaged density is a
  many-hundred-vertex polyline with sub-Ångström wiggles and near-tangential self-approaches at the
  constriction.
- Newton convergence with the corrections active, which makes `D`, `μ`, `ε` and `ϱ` functions of
  local ionic strength and wall distance.
- The desktop GUI, the largest single scope item and the strongest constraint on the backend.
- The analyte net force, a near-cancellation of two terms of about 10 pN and opposite sign.
- A single maintainer.

Throughput datum: the reference sweep of 3,675 solves (5 physics cases × 35 bias values × 21 salt
concentrations) took 41 h on 12 cores. A full-envelope sweep is a day-scale job.

NOTE (QR-06): the scaling claim is about *independent* workers. Processes sharing one linear-algebra
thread pool are not independent, and a scaling curve measured without the thread counts pinned per
worker (§5.3.4) reports the pool rather than the dispatch. A throughput figure SHALL likewise be
computed over the members that were actually solved, cache hits being dictionary lookups that would
otherwise report unbounded throughput for a resumed sweep.

---
