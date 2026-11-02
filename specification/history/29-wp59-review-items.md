---
type: Ruling Record
title: "8.2.29 WP59's review items, agreed 2 November 2026"
description: "Records the author's rulings on the items WP59's review left open: the state gates speak before a non-finite trial's divergence, a non-finite Newton direction is named as the linear solve's, a session opens a run from the store its record names unless it was given one, and WP59's three public names stand; and, at WP60's plan, the source's prose share at the close is accepted as measured."
---

#### 8.2.29 WP59's review items, agreed 2 November 2026

Rulings by the author on 2 November 2026, during `/np-ship wp 59`, on the items the review of
[CODE_REVIEW_025](../../docs/code_reviews/CODE_REVIEW_025.md) and its physics pass left open, REV-172 and REV-173, and on
the question the package's PR put. Four questions were put through `AskUserQuestion` in one call; the author took the
recommendation on each and asked that the items be resolved in WP59's PR. The letter series continues at AE. One more question was put on the same day, at WP60's plan, and taken as recommended (AE5).

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| AE1 | **At minimum damping, the NUM-17 state gates are checked on a trial with a non-finite residual before the divergence is raised.** A violation raises the gate's error, naming the field and its location; otherwise the divergence of AC2 is raised. The state is restored either way | A broken concentration or packing fraction keeps the QR-12 diagnostic and the gate's exit code it had before WP59; the extra gate pass runs on the abort path only. REV-172 is fixed | NUM-16's NOTE, in WP59 |
| AE2 | **A non-finite Newton direction raises a divergence naming the linear solve**, before any trial, with the state unchanged | A singular or poisoned linear solve is reported as such, instead of as a non-finite residual after the damping cuts; one norm per iteration | NUM-16's NOTE, in WP59 |
| AE3 | **A session opens a recorded run from its own store if it was given one, else from the store the run's record names; `Session.read` needs no session** | `nanopnp plot` of a run reads the run directory once, and the rule for choosing the store lives in `open_run` alone. The milliseconds `Session.check` spends dumping an edited case to obtain its base are accepted. REV-173 is fixed | IF-01's NOTE, in WP59 |
| AE4 | **WP59's three public names stand**: `case.source`, `session.check(case)` and `Session.read(directory)` | `v0.5.0` fixes them as the interface the workbench's server calls | None |
| AE5 *Added 2 November 2026, at WP60's plan.* | **The source's prose share at the close is accepted as measured**: 11.9 % of `src/nanopnp` at `a800a45`, above the 11.4 % L10 accepted, and 2.7 % of `tests/`, within its 3 %. The rise is the docstrings the prose rule requires on the public interface WP57 and WP59 added (`api/` is 20.3 %), and the share stays under the 12.48 % ceiling the withdrawn VER-75 recorded | Criterion 11's prose item is met without a strip pass, and the close reports the share it re-measures. A later rise is not covered by this ruling | The Phase 4 plan's criterion 11, at WP60's plan |
