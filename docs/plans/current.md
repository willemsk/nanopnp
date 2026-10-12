# Current work

Updated 12 October 2026 (WP42 delivered; WP43 next). Navigation only; `SPECIFICATION.md` governs;
an unmerged branch is not shipped.

## In brief

The project is in Phase 4, which tidies the program before anyone else relies on it. Next comes a
short package that speeds the automatic checks: about a minute per commit instead of 3.5, and one
full check per push. It also gives each kind of AI helper a fixed job and model, and keeps plans
readable without code. **Your call:** at its close, whether the pre-push
check's 5-minute target becomes 8, since one example alone takes about 5. *Recommendation:* yes,
because it no longer blocks work.

## Position

- Phases 1 to 3 are **closed** as `v0.2.0`, `v0.3.0` (§8.2.4 D7) and `v0.4.0`.
- **Phase 4** ([polish and user testing](phase-4-polish-and-user-testing.md)), `v0.5.0`, is
  **in progress** (§8.2.7 G1–G11; §8.2.8 H1–H12; §8.2.9 I1–I5; §8.2.10 J1–J12). WP35 to WP42 are
  delivered, as `v0.5.0-alpha.1` to `.8`.
- **Next: WP43, the development loop** (§8.2.10 J1–J12), planned in
  [wp43-development-loop.md](wp43-development-loop.md). Item 4 (VER-62 on 3.14)
  may stop it (G10).
- Then WP44, the small fixes; WP45–WP47 (OKF bundle, backfill, protocol); the author's sessions;
  fixes from WP48. Phase 5 (`v0.6.0`) is the GUI, Phase 6 (`v0.7.0`) validation; v1.0 is OPN-08.

## Not to be re-decided

- **Versions:** one minor per phase; the close takes `v0.5.0` alone (E2, F2, G11). → §2.7 NOTE.
- **The development loop:** affected tests on commit, one push gate, one pull-request leg on
  Python 3.14, a defined agent roster, `## In brief`. Floor 3.11; estimate 4–6 weeks. → §8.2.10;
  OPN-09.
- **Phase 4's shape:** refactors before the protocol (G2); two OKF packages and a ratchet (G3, G8);
  checked findings logs (G4); protocol findings only from the author's sessions (G7); the VER-62
  golden (G10). → §8.2.7. The `MOD-nn` rulings stand (§8.2.8).
- **Phase 3's charge pipeline** stands as delivered (§8.2.4).
- **No payload records wall-clock time** (VER-23). **A gated test gets cheaper only by §7.6's four
  levers** (WP33).
- **A moved edge edits `modularity-layering.yaml` in the same commit (VER-61)**; a VER-62 miss is
  reverted, or ruled and re-pinned (G10, I4).
- **What a package leaves open is a `REV-nn` row** until resolved (H12); Phase 4's are `fixed` by
  the close (I3).
- **A stage declares its walk facts and reads in the registry, and defines `key`** (VER-64).
- **Tier 3 compares the published I–V and pore averages**, gating v0.7 (VAL-16, VAL-17).
- **Layers read a model's declaration, never its name** (VER-56). **A refusal names its requirement
  and release** (VER-67). **Only `poisson` adds a quadrature order for `r`** (E4; NUM-07 NOTE).
  **A golden carries the stage-7 recipe** (E3; VAL-03).
- **The VAL-05 ensemble test fails on the archive by design** (§8.2.4 D7).
- **The schema and `nanopnp.PUBLIC` may change until v1.0** (F4); a move takes the release's
  identifier, `nanopnp/case/v0.5` (G6), and is listed in `CHANGELOG.md`.
- **A callback is not an input** (VER-44). **A generated mesh is read only through
  `deployed_mesh`.** **Stage 1's frame is fixed**; tests use `prepared_2wcd`. **Every phase
  documents what it ships**, its commands run verbatim (VER-46).

## What is still somebody else's

- **The paper's figure data**, for VAL-16 and VAL-17 at v0.7 (§8.2.4 D6), and E1's ensemble legs.
- **The Read the Docs project**; **`$NANOPNP_REFERENCE_DATA` on the nightly runner**.
- **OPN-04**, the mutation list; **OPN-08**, what v1.0 contains.
- **The user-testing sessions, and the rulings on each `UT-nn`, `MOD-11`, any residual cycle
  (H6) and any WP41 drift beyond its bound (I4).** **The archived PQRs** for WP27–WP29's Tier 3.

## Dependencies To Read On Demand

| Need | Read |
|---|---|
| The desktop shell and the probe bundle | The WP24 and WP31 plans; `gui/`; `.knowledge/07` §5; ADR-004 |
| Phase 4 scope and packages | `phase-4-polish-and-user-testing.md`; §8.2.6 F3–F6, §8.2.7, §8.2.8 |
| The OKF decisions | `okf-knowledge-bundle.md` (K1–K11); §8.2.7 G3, G8, G9 |
| Case schema and supply chains | §5.3.1 NOTEs; `io/case.py`, `io/resolved.py`; `pipeline/case.py`, `pipeline/checks.py` |

## Handoff Rules

When planning or finishing a package, replace this brief's position and live dependencies. Keep
it to 700 words, opening with an In brief of at most 250 words (no backticks or identifiers) that
ends in **Your call**; measurements stay in the records that own them.
