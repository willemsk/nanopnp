# Current work

Updated 18 October 2026 (WP49 delivered). Navigation only; `SPECIFICATION.md` governs; an unmerged
branch is not shipped.

## In brief

Phase 4 tidies the program before others rely on it; the loop, the code, the notes and now the cost
study are done. Three suspected costs were measured and none came near its limit, so nothing was
changed: the biggest protein ensemble would need about a quarter of the memory limit, building
equations is under half a percent of a solve, and saving results is about half a percent of a run.
The case-file format is now published in a standard machine-readable form, and a check fails if it
and the program disagree. Main's failing test on Mac and Windows is fixed. Next is the protocol for
the author's testing sessions.

**Your call:** none open; the format ships in the documentation only. *Recommendation:* keep it so
until the browser page needs a command.

## Position

- Phases 1 to 3 are **closed** as `v0.2.0`, `v0.3.0` (§8.2.4 D7) and `v0.4.0`.
- **Phase 4** ([polish and user testing](phase-4-polish-and-user-testing.md)), `v0.5.0`, is
  **in progress** (§8.2.7 to §8.2.12). WP35 to WP45 are
  merged ([loop](wp44-simplify-the-loop.md), [prose](wp45-prose-strip.md)); tags to `v0.5.0-alpha.11`
  are the author's step.
- **WP46 to WP49 are delivered** ([WP48](wp48-okf-backfill.md), [WP49](wp49-cost-study.md)); tags
  `v0.5.0-alpha.12` to `.15`.
- **Amended 18 October 2026** (§8.2.12): review claims already met declined (REV-115); browser
  shell to Phase 5 (M3). **WP49, the cost study** (M2; REV-112, REV-113; VER-76), found every cost
  under its threshold (`docs/project/cost-study.json`). Next: WP49 merged, then WP50 (protocol; the
  author's sessions; fixes from WP51).

## Not to be re-decided

- **Versions:** one minor per phase; the close takes `v0.5.0` alone (E2, F2, G11). → §2.7 NOTE.
- **The development loop** (§8.2.11): Tier 1 on commit; one push gate; one pull-request leg on
  Python 3.14; Haiku, Sonnet, then Opus; capped plans; two agents (L9); prose only on the public
  API. Floor 3.11. → §8.2.10 J4–J6, J9; OPN-09.
- **Cost fixes follow measurement against thresholds registered before it** (§8.2.12 M2).
  **Phase 5 builds a browser shell; the Qt shell stays gated until it is replaced** (M3).
- **Phase 4's shape:** refactors before the protocol (G2); findings only from the author's sessions
  (G7); the VER-62 golden (G10). → §8.2.7. The `MOD-nn` rulings stand (§8.2.8).
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
| The loop as shipped | `wp44-simplify-the-loop.md` |
| Phase 4 scope and packages | `phase-4-polish-and-user-testing.md`; §8.2.6 F3–F6, §8.2.7, §8.2.8 |
| The cost study and the review verdicts | `wp49-cost-study.md`; Phase 4 plan, WP49's thresholds; §8.2.12; `review-items.md` REV-112 to REV-115 |
| The OKF bundle and backfill | `wp47-okf-bundle.md`, `wp48-okf-backfill.md`; `validation/okf.py` (VER-68) |
| The OKF decisions | `okf-knowledge-bundle.md` (K1–K11); §8.2.7 G3, G8, G12; `okf-converter-rules.md` |

## Handoff Rules

When planning or finishing a package, replace this brief's position and live dependencies. Keep
it to 700 words, opening with an In brief of at most 250 words (no backticks or identifiers) that
ends in **Your call**; measurements stay in the records that own them.
