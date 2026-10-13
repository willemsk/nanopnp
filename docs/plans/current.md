# Current work

Updated 13 October 2026 (WP43 merged; WP44 next). Navigation only; `SPECIFICATION.md` governs;
an unmerged branch is not shipped.

## In brief

The project is in Phase 4, which tidies the program before anyone else relies on it. The package
meant to speed up the automatic checks was merged, but it did not deliver: commits still wait two
to four minutes, and the session that built it cost about four times a normal one. You have ruled
a simpler course. Two packages come next. The first swaps the clever machinery for plain rules:
a commit runs the style checks and every quick test, the full check runs once before a push, plans
stay under a page and a half, and cheaper AI models do routine work. The second removes most
comments and explanations from the code and proves by machine that nothing else changed.
**Your call:** should the rule that blocks a push until the full check passed stay?
*Recommendation:* yes, it is small and makes the check hard to skip.

## Position

- Phases 1 to 3 are **closed** as `v0.2.0`, `v0.3.0` (§8.2.4 D7) and `v0.4.0`.
- **Phase 4** ([polish and user testing](phase-4-polish-and-user-testing.md)), `v0.5.0`, is
  **in progress** (§8.2.7 G1–G11; §8.2.8 H1–H12; §8.2.9 I1–I5; §8.2.10 J1–J12). WP35 to WP42 are
  delivered, as `v0.5.0-alpha.1` to `.8`.
- **WP43, the development loop**, is merged ([wp43-development-loop.md](wp43-development-loop.md)); tag
  `v0.5.0-alpha.9` is the author's step. It missed its speed budgets (REV-80, REV-81) and is
  simplified by §8.2.11.
- **Next: WP44, simplify the loop**, then **WP45, the prose strip** (§8.2.11 L1 to L8); then WP46
  the small fixes, WP47–WP49 (OKF bundle, backfill, protocol); the author's sessions; fixes from
  WP50. Phase 5 (`v0.6.0`) is the GUI, Phase 6 (`v0.7.0`) validation; v1.0 is OPN-08.

## Not to be re-decided

- **Versions:** one minor per phase; the close takes `v0.5.0` alone (E2, F2, G11). → §2.7 NOTE.
- **The development loop** (§8.2.11): lint, types and Tier 1 on commit; one push gate without coverage; one
  pull-request leg on Python 3.14; Haiku, then Sonnet, then Opus; plans of at most 1,500 words with
  compaction checkpoints; prose only on the public API; `## In brief`. Floor 3.11. → §8.2.10 J4–J6,
  J9; OPN-09.
- **Phase 4's shape:** refactors before the protocol (G2); two OKF packages and a ratchet (G3, G8);
  checked findings logs (G4); protocol findings only from the author's sessions (G7); the VER-62
  golden (G10). → §8.2.7. The `MOD-nn` rulings stand (§8.2.8).
- **A moved edge edits `modularity-layering.yaml` in the same commit (VER-61)**; a VER-62 miss is
  reverted, or ruled and re-pinned (G10, I4).
- **What a package leaves open is a `REV-nn` row** until resolved (H12); Phase 4's are `fixed` by
  the close (I3).
- **A stage declares its walk facts and reads in the registry, and defines `key`** (VER-64).
- **Tier 3 compares the published I–V and pore averages**, gating v0.7 (VAL-16, VAL-17).
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
| Phase 4 scope and packages | `phase-4-polish-and-user-testing.md`; §8.2.6 F3–F6, §8.2.7, §8.2.8 |
| The OKF decisions | `okf-knowledge-bundle.md` (K1–K11); §8.2.7 G3, G8, G9 |

## Handoff Rules

When planning or finishing a package, replace this brief's position and live dependencies. Keep
it to 700 words, opening with an In brief of at most 250 words (no backticks or identifiers) that
ends in **Your call**; measurements stay in the records that own them.
