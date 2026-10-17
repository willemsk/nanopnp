# Current work

Updated 17 October 2026 (WP48 delivered; all 361 open claims resolved). Navigation only; `SPECIFICATION.md` governs;
an unmerged branch is not shipped.

## In brief

Phase 4 tidies the program before others rely on it. The simpler loop, the trimmed code, the fifteen
small fixes and the reference notes are built. The notes were ten long files; they are a hundred and
twenty-one short pages, one idea each, in a folder per note. Every claim in the notes is now backed:
calculations by fast automated tests, software behaviour by checked library assertions and version
records, and historical measurements by exact citations to earlier work. The list of waiting claims
is empty, and the check refuses any new unbacked claim. No computed result moved. It now waits for
review in a fresh session.

**Your call:** the user testing protocol is next. *Recommendation:* proceed with planning the
sessions once this work package merges.

## Position

- Phases 1 to 3 are **closed** as `v0.2.0`, `v0.3.0` (§8.2.4 D7) and `v0.4.0`.
- **Phase 4** ([polish and user testing](phase-4-polish-and-user-testing.md)), `v0.5.0`, is
  **in progress** (§8.2.7 G1–G12; §8.2.8 H1–H12; §8.2.9 I1–I5; §8.2.10 J1–J12). WP35 to WP45 are
  merged ([loop](wp44-simplify-the-loop.md), [prose](wp45-prose-strip.md)); tags to `v0.5.0-alpha.11`
  are the author's step.
- **WP46, the small fixes** ([plan](wp46-small-fixes.md)), is **delivered** (§8.2.9 I2; fifteen
  `REV-nn` rows `fixed`), tag `v0.5.0-alpha.12` after the merge.
- **WP47, the OKF bundle** ([plan](wp47-okf-bundle.md)), is **delivered** (§8.2.7 G12; VER-68), tag
  `v0.5.0-alpha.13` after the merge.
- **WP48, the OKF backfill** ([plan](wp48-okf-backfill.md)), is **delivered** (§8.2.7 G3, G8; VER-68;
  REV-103 closed), tag `v0.5.0-alpha.14` after the merge. Next: `/wp-ship`; then WP49 (protocol;
  the author's sessions; fixes from WP50).

## Not to be re-decided

- **Versions:** one minor per phase; the close takes `v0.5.0` alone (E2, F2, G11). → §2.7 NOTE.
- **The development loop** (§8.2.11): lint, types and Tier 1 on commit; one push gate without coverage; one
  pull-request leg on Python 3.14; Haiku, then Sonnet, then Opus; plans of at most 1,500 words with
  compaction checkpoints; two agents, and WP45's fresh worker per item as a trial (L9); prose only on the public API; `## In brief`. Floor 3.11. → §8.2.10 J4–J6,
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
| The loop as shipped | `wp44-simplify-the-loop.md` |
| The small fixes as shipped | `wp46-small-fixes.md`; `CHANGELOG.md` `0.5.0-alpha.12`; `docs/project/review-items.md` |
| The knowledge bundle as shipped | `wp47-okf-bundle.md`; `knowledge/index.md`; `src/nanopnp/validation/okf.py` (VER-68) |
| The OKF backfill as shipped | `wp48-okf-backfill.md`; `knowledge/pending.yaml`; §8.2.7 G3, G8 |
| Phase 4 scope and packages | `phase-4-polish-and-user-testing.md`; §8.2.6 F3–F6, §8.2.7, §8.2.8 |
| The OKF decisions | `okf-knowledge-bundle.md` (K1–K11); §8.2.7 G3, G8, G12; `okf-converter-rules.md` |

## Handoff Rules

When planning or finishing a package, replace this brief's position and live dependencies. Keep
it to 700 words, opening with an In brief of at most 250 words (no backticks or identifiers) that
ends in **Your call**; measurements stay in the records that own them.
