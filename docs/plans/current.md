# Current work

Updated 18 October 2026 (WP49 delivered; Phase 4 amended for the test scope). Navigation only; `SPECIFICATION.md` governs; an unmerged
branch is not shipped.

## In brief

Phase 4 tidies the program before others rely on it; the loop, the code, the notes and the cost
study are done. The tests have outgrown their use, so the next package deletes those that guard
nothing that could silently go wrong, keeps the physics, the numerics, the core machinery and the
licence and architecture guards, and runs the long examples nightly. Then comes the protocol for the
author's testing sessions.

**Your call:** none open; the case-file format ships in the documentation only. *Recommendation:*
keep it so until the browser page needs a command.

## Position

- Phases 1 to 3 are **closed** as `v0.2.0`, `v0.3.0` (§8.2.4 D7) and `v0.4.0`.
- **Phase 4** ([polish and user testing](phase-4-polish-and-user-testing.md)), `v0.5.0`, is
  **in progress** (§8.2.7 to §8.2.13). WP35 to WP49 are delivered ([WP49](wp49-cost-study.md));
  tags to `v0.5.0-alpha.15` are the author's step. Browser shell to Phase 5 (§8.2.12 M3).
- **Amended 18 October 2026** (§8.2.13): **WP50, the test scope** (N1 to N5), before the protocol,
  is **planned** ([plan](wp50-test-scope.md)). Next: `/wp-implement`, then WP51 (protocol; the author's sessions; fixes from WP52).

## Not to be re-decided

- **Versions:** one minor per phase; the close takes `v0.5.0` alone (E2, F2, G11). → §2.7 NOTE.
- **The development loop** (§8.2.11): Tier 1 on commit; one push gate; one pull-request leg on
  Python 3.14; Haiku, Sonnet, then Opus; capped plans; two agents (L9); prose only on the public
  API. Floor 3.11. → §8.2.10 J4–J6, J9; OPN-09.
- **The test scope** (§8.2.13): tests only for physics, numerics, core mechanisms and the licence
  and architecture guards; no coverage gate; a test per identifier only in that scope; walks nightly
  but for examples 01 and 02; `/wp-ship` deletes off-category tests. → N1 to N5.
- **Cost fixes follow measurement against thresholds registered before it** (§8.2.12 M2).
  **Phase 5 builds a browser shell; the Qt shell stays gated until it is replaced** (M3).
- **Phase 4's shape:** refactors before the protocol (G2); findings only from the author's sessions
  (G7, its scripts nightly by N4); the VER-62 golden (G10). → §8.2.7. The `MOD-nn` rulings stand (§8.2.8).
- **A moved edge edits `modularity-layering.yaml` in the same commit (VER-61)**; a VER-62 miss is
  reverted, or ruled and re-pinned (G10, I4).
- **What a package leaves open is a `REV-nn` row** until resolved (H12); Phase 4's are `fixed` by
  the close (I3).
- **Layers read a model's declaration, never its name** (VER-56). **A refusal names its requirement
  and release** (VER-67). **Only `poisson` adds a quadrature order for `r`** (E4; NUM-07 NOTE).
  **A golden carries the stage-7 recipe** (E3; VAL-03).
- **The schema and `nanopnp.PUBLIC` may change until v1.0** (F4); a move takes the release's
  identifier, `nanopnp/case/v0.5` (G6), and is listed in `CHANGELOG.md`.
- **A callback is not an input** (VER-44). **A generated mesh is read only through
  `deployed_mesh`.** **Stage 1's frame is fixed.** **Every phase documents what it ships** (VER-46).

## What is still somebody else's

- **The paper's figure data**, for VAL-16 and VAL-17 at v0.7 (§8.2.4 D6), and E1's ensemble legs.
- **The Read the Docs project**; **`$NANOPNP_REFERENCE_DATA` on the nightly runner**.
- **OPN-04**, the mutation list; **OPN-08**, what v1.0 contains.
- **The user-testing sessions, and the rulings on each `UT-nn`, `MOD-11`, any residual cycle
  (H6) and any WP41 drift beyond its bound (I4).** **The archived PQRs** for WP27–WP29's Tier 3.

## Dependencies To Read On Demand

| Need | Read |
|---|---|
| The test scope | `wp50-test-scope.md`; §8.2.13; `docs/superpowers/specs/2026-10-18-test-pruning-design.md` |
| The loop as shipped | `wp44-simplify-the-loop.md` |
| Phase 4 scope and packages | `phase-4-polish-and-user-testing.md`; §8.2.6 F3–F6, §8.2.7, §8.2.8 |
| The OKF bundle | `wp47-okf-bundle.md`, `wp48-okf-backfill.md` |
| The OKF decisions | `okf-knowledge-bundle.md` (K1–K11); §8.2.7 G3, G8, G12; `okf-converter-rules.md` |

## Handoff Rules

When planning or finishing a package, replace this brief's position and live dependencies. Keep
it to 700 words, opening with an In brief of at most 250 words (no backticks or identifiers) that
ends in **Your call**; measurements stay in the records that own them.
