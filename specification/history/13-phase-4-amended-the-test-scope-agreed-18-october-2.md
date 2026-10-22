---
type: Ruling Record
title: "8.2.13 Phase 4 amended: the test scope, agreed 18 October 2026"
description: "Records the rulings on the test scope, agreed 18 October 2026, after measuring about 1,880 test functions."
---

#### 8.2.13 Phase 4 amended: the test scope, agreed 18 October 2026

Rulings by the author, taken in a brainstorm on 18 October 2026 and through `/phase-plan amend 4`
after WP49 was delivered. The input is the approved design
`docs/superpowers/specs/2026-10-18-test-pruning-design.md`. Measured that day: about 1,880 test
functions (2,403 collected) in 48,000 lines, against 50,000 lines of `src/`; of Tier 1's ~1,650, about
770 test physics, numerics or core mechanisms, about 620 interface refusals and wiring, about 250
the repository itself. The growth was driven by changed-line coverage, a test per claimed identifier,
test-backed knowledge claims and repository self-checks that make a Markdown edit run the suite.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| N1 | **The test scope.** A test is written only for code that could silently give a wrong answer or that drives a core mechanism: physics and numerics (weak forms, corrections, Newton and its gates, stabilisation, quadrature, charge deposition, dielectric, wall distance, forces, QoI, scaling, continuation, mesh quality and sizing, the analytic benchmarks, MMS); core mechanisms (content hashing and cache keys, the store, case resolution, the stage walk and cancellation, warm start, reproducibility, the manifest's deviations, the solution state, the number-stability goldens); and the licence and architecture guards only (CON-10's `gmsh` import, CON-12's lock, VER-61, VER-65, and a module importing no backend). A refusal test stays only where the refusal is a numerical or physical gate. Each entry point keeps a thin smoke test. A new test says which silent failure it catches | Roughly half the suite is deleted: input-validation refusals and message wording, CLI and GUI wiring, schema field lists, defaults, and every repository self-check that is not a guard. No tolerance is loosened and no kept test is weakened or rewritten | §7.1 to §7.3, `CLAUDE.md`, `CONTRIBUTING.md`, `tests/README.md` and `.claude/rules/python.md`, in WP50 |
| N2 | **No coverage gate.** CI's `coverage` job, `diff-cover` and the `# pragma: no cover - <reason>` convention go | Supersedes L3's coverage clause and VER-72 (f) | §7.6's coverage NOTE, `ci.yml`, the skills, in WP50 |
| N3 | **A requirement needs a test named for it only where it is physics, numerics or a core mechanism.** Other identifiers stay normative and are verified at review. The repository self-checks are withdrawn, their numbers not reused: VER-63, VER-67, VER-68, VER-72 except its guard parts, VER-75, and the self-check parts of VER-45 and VER-46 (the strict documentation build stays in CI). A `[tested: <test>]` marker naming a deleted test is retargeted to a surviving test of the same claim, else becomes `[verified]` on its source footnote, else is dropped; `knowledge/pending.yaml` goes | Supersedes G3's ratchet, G4's test, G8 and F6's "test-backed" ledger. Phase 4's criteria that read a withdrawn check are verified by the close at review, reading the same logs | Appendix A, §7.2, §7.3, §8.1's Phase 4 and Documentation rows, `knowledge/`, in WP50 |
| N4 | **Every push runs Tier 1, the Tier 2 tests that neither walk the pipeline nor carry `slow`, example 01 while it solves in under 60 s, and one charged walk, example 02's ePNP-NS pore with its VER-62 golden.** Everything else in Tiers 1 and 2 runs nightly, under a `nightly` marker that replaces `extended`; the user-testing scripts run nightly. A failed nightly run opens an issue and blocks nothing. A push to `main` keeps its three platforms on the per-push selection. A tagged release keeps its full run | Supersedes J10 and G7's push-gate clause. The push gate drops from about 8 minutes. A golden on another walk is caught by the night after its merge | §7.6, `ci.yml`, `release.yml` unchanged, `gate.sh`, `pyproject.toml`, `tests/conftest.py`, in WP50 |
| N5 | **Prevention is the judgement rule of N1, plus a reviewer step.** `/wp-ship` reads the pull request's added and changed tests against N1 before `/code-review` and deletes each one outside it, in its own commit; a review finding is never closed by an off-category test. Plans list only in-scope tests. No test checks the rule | Test growth is bounded by review, not by a count | The skills and the pull-request template, in WP50 |
| N6 | **The test scope is WP50, before the protocol.** The protocol becomes WP51 and the fix packages are numbered from WP52. Tag `v0.5.0-alpha.16` | The protocol's scripts are written onto N4's split | The Phase 4 plan, in this commit. **Renumbered, 22 October 2026** (§8.2.14 P1): the protocol is WP52, the fixes from WP53 |
| N7 | **The phase estimate stands** at 4–6 weeks | WP50 is absorbed, as WP43 and WP49 were (J12, M5) | None |

