# Current work

Updated 22 October 2026 (§8.2.16). Navigation only; `SPECIFICATION.md` governs; an
unmerged branch is not shipped.

## In brief

Phase 4 tidies the program before others rely on it. Three packages precede the testing
sessions: the specification and this phase's plan split into what holds today and their history;
the working instructions rebuilt as three commands with levels; and the notebooks and figures
revised from the author's notes.

**Your call:** should the phase estimate grow to five to seven weeks? *Recommendation:* yes.

## Position

- Phases 1 to 3 are **closed** as `v0.2.0`, `v0.3.0` (§8.2.4 D7) and `v0.4.0`.
- **Phase 4** ([polish and user testing](phase-4-polish-and-user-testing.md)), `v0.5.0`, is
  **in progress** (§8.2.7 to §8.2.16). WP35 to WP51 are delivered; tags to `v0.5.0-alpha.17` are
  the author's step.
- **Amended 22 October 2026** (§8.2.16 R1): [WP52](wp52-specification-and-plans-split.md), the
  documents, is **planned**; next: **`/wp-implement`**. Then WP53, the workflow, and WP54, the notebooks revised; then [WP55](wp55-user-testing-protocol.md),
  the protocol, **planned**; then the author's sessions, and fixes from WP56.

## Not to be re-decided

- **Versions:** one minor per phase; the close takes `v0.5.0` alone (E2, F2, G11). → §2.7 NOTE.
- **The development loop** (§8.2.11): Tier 1 on commit; one push gate; one pull-request leg on
  Python 3.14; Haiku, Sonnet, then Opus; plans grounded in the code (Q1); two agents; workers for
  independent batches (L9, R6); prose only on the public API. Floor 3.11. → §8.2.10
  J4–J6, J9; §8.2.15; OPN-09.
- **The documents and the workflow** (§8.2.16): specification and plans read current by default,
  history on demand; `/plan`, `/implement`, `/ship` with levels; WP54's scope open. → R2 to R11.
- **The test scope** (§8.2.13): tests only for physics, numerics, core mechanisms and the licence
  and architecture guards; no coverage gate; walks nightly but for examples 01 and 02. → N1 to N5.
- **Figures:** Matplotlib in `plot/`, below `pipeline`, importing no backend; figures declared in
  the stage registry; marimo notebooks, nightly. → §8.2.14 P2 to P6; FR-30.
- **Cost fixes follow measurement against registered thresholds** (§8.2.12 M2). **Phase 5
  builds a browser shell; the Qt shell stays gated until then** (M3).
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

- **The paper's figure data** for VAL-16 and VAL-17 (§8.2.4 D6); E1's ensemble legs.
- **The Read the Docs project**; **`$NANOPNP_REFERENCE_DATA` on the nightly runner**.
- **OPN-04**, the mutation list; **OPN-08**, what v1.0 contains.
- **The notes on the notebooks and figures, for WP54's plan.** **The user-testing sessions, and
  the rulings on each `UT-nn`, `MOD-11`, any residual cycle (H6) and any WP41 drift (I4).** **The archived PQRs** for WP27–WP29's Tier 3.

## Dependencies To Read On Demand

| Need | Read |
|---|---|
| The documents | `wp52-specification-and-plans-split.md`; §8.2.16 R2 to R4, R9, R10; §11 |
| The workflow | The Phase 4 plan's WP53; §8.2.16 R5 to R7 |
| The notebooks revised | The Phase 4 plan's WP54; `wp51-plotting-and-notebooks.md`; §8.2.14; FR-30 |
| The protocol | `wp55-user-testing-protocol.md`; §8.2.7 G7, §8.2.8 H2, §8.2.13 N4; VER-46 |

## Handoff Rules

When planning or finishing a package, replace this brief's position and live dependencies. Keep
it to 700 words, opening with an In brief of at most 250 words (no backticks or identifiers) that
ends in **Your call**; measurements stay in the records that own them.
