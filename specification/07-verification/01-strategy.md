---
type: Specification
title: "7.1 Strategy and ordering"
description: "Sets out the verification strategy: the four test tiers, their runtimes, frequencies and roles in the phase gates."
---

### 7.1 Strategy and ordering

| Tier | Content | Runtime | Frequency | Role |
|---|---|---|---|---|
| 1 | Unit and property tests (§7.2) | seconds | every push | Acceptance gate for Phases 0 and 1 |
| 2 | Analytic benchmarks (§7.3) | minutes | every push; the walks nightly (§7.6) | Acceptance gate for Phases 0 and 1 |
| 3 | Cross-implementation comparison (§7.4) | hours | nightly and on demand, once Tier 2 passes | Recorded, not gated, until §7.4 preconditions hold |
| 4 | Experimental reproduction (§7.5) | hours | before a tagged release | Release gate |

Tiers 1 and 2 are the acceptance gate for Phases 0 and 1. Tier 3 runs only after Tier 2 passes.
Tier 4 gates releases.

NOTE (the test scope; §8.2.13 N1, N3): a test is written only for code that could silently give a
wrong answer or that drives a core mechanism: physics and numerics, content hashing and cache keys,
the store, case resolution, the stage walk and cancellation, warm start, reproducibility, the
manifest's deviations, the solution state and the number-stability goldens, and the licence and
architecture guards (CON-10, CON-12, VER-61, VER-65, a module importing no backend). A refusal is
tested only where it is a numerical or physical gate. Each entry point keeps a thin smoke test. A
`VER-` or `VAL-` row outside that scope stays normative and is verified at review; a row that says
so in its text is not discharged by a test, and no test is added to discharge it. Deleting a test
outside the scope is allowed; no tolerance is slackened and no test inside it weakened.

Rationale: an analytic test localises an error to a single term, so a Debye–Hückel failure points
at the axis condition or the r-weighted Poisson form and an MMS failure at the hoop-strain term. A
whole-model comparison localises nothing, so a per-cent-level discrepancy found first offers no
route to a cause and invites adjusting the solver until the number matches.

NOTE (Tier-3 reference files are named, not vendored): the archived golden files Tier 3 compares
against are too large to carry in the repository — the delivered ClyA charge table alone is 77 MB
of text — and no lossy reduction of one is a fair reference: cropping the ClyA table at a
`10⁻⁶` relative threshold still costs 28 MB, and subsampling it by four moves its planar integral
by 1.5 %, which is fifteen times QR-03's budget. The archive SHALL therefore be located by the
environment variable `NANOPNP_REFERENCE_DATA`, naming a directory of files by name, and a Tier-3
test whose file is absent SHALL **skip** rather than fail: Tier 3 is recorded and not gated, so an
unavailable reference is missing evidence, not a defect. Tier 1 and Tier 2 SHALL NOT read the
archive, so the push gate is unaffected by whether it is present.
