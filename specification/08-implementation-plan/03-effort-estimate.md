---
type: Specification
title: "8.3 Effort estimate"
description: "Estimates the work to the validated release in sessions, agent hours and the author's touches, from the measured cost of comparable packages."
---

### 8.3 Effort estimate

The work is done by agents in Claude Code, and its cost is stated in three units (§8.2.37 AM10):

- **sessions**, the context windows it takes, each ended by a compaction the author runs. A package
  takes at least four: its plan, the plan's review, its implementation and its shipping, and one more
  for each compaction checkpoint of its implementation;
- **agent hours**, the hours an agent works on it, waits for the gate and CI included and waits for
  the author excluded;
- **the author's touches**, each time the author acts: a command, a compaction, a question round, a
  verdict, an approval, a merge or a tag.

The calendar follows from when the author returns and is not estimated. An estimate is taken from
the measured cost of comparable packages, which `.claude/scripts/usage.py` reads from each session's
transcript (§8.4.5; AM11), never from a developer's days. Measured from the first commit to the
last on `main`, waits for the author included, Phase 5's library steps WP5.03 to WP5.06 took 1 to 3
hours each, and WP5.07, WP5.08 and WP5.10, which add a mechanism, a screen or the rules, 7 to 11.

Estimate to the validated release (v0.12, Phase 11; §8.2.5 E2, §8.2.6 F1; §8.2.49 AY1, AY2), from 22 November
2026, after Phase 5's release. Phase 5's last thirteen packages were estimated on 9 November at about 74 sessions,
66 to 132 agent hours and 122 touches (AM12), and its measured packages give the rates: a text or clean-up package
about 5 sessions, 3 to 6 agent hours and 8 touches, and a shell package about 6 sessions, 6 to 12 agent hours and 10
touches. Each phase's own round estimates it again:

| Work | Sessions | Agent hours | Touches |
|---|---|---|---|
| Phase 6, the cleanup and the library's foundations: about 15 packages at the text and clean-up rate, the Windows leg, the cleanup, the restructure, the model's open terms, the tolerances, the exports, the refusals and the speed-up among them (§8.2.49 AY1, AY3, AY4, AY6) | 75 | 45 to 90 | 120 |
| Phase 7, the workbench rebuilt: about 14 packages at the shell rate, its foundations and the packages Phase 5's seventh amendment moved (§8.2.47 AW1), and the author's design rounds | 85 | 85 to 170 | 140 |
| Phases 8 to 10, the composer, the structural mutator and the sketcher: not estimated; each round sets its own (§8.2.17 S7; §8.2.49 AY2) | — | — | — |
| Phase 11, validation and release: about seven packages, and the machine time of its Tier 3 and Tier 4 runs (the datum below) | 40 | 35 to 70 | 70 |

A ruling round, a plan and a ship session on Fable 5.2 cost about a quarter to a half more in model spend than on
Opus 5.5 (§8.2.49 AY7); the units above do not change.

Factors making the work more tractable:

- The published results serve as the oracle (VAL-16, VAL-17); field-level reference solutions are
  used where exports exist (VAL-01 to VAL-04, not required).
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
concentrations) took 41 h. A full-envelope sweep is a day-scale job.

NOTE (QR-06): the scaling claim is about *independent* workers. Processes sharing one linear-algebra
thread pool are not independent, and a scaling curve measured without the thread counts pinned per
worker (§5.3.4) reports the pool rather than the dispatch. A throughput figure SHALL likewise be
computed over the members that were actually solved, cache hits being dictionary lookups that would
otherwise report unbounded throughput for a resumed sweep.

---
