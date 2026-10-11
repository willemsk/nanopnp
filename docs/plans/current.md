# Current work

Updated 11 October 2026 (WP42 delivered; Phase 4 amended, WP43 next). Navigation only; `SPECIFICATION.md` governs;
nothing here is evidence an unmerged branch shipped.

## In brief

The project is in Phase 4, which tidies the program before anyone else relies on it. Next comes a
short package that makes the automatic checks fast: about a minute per commit instead of 3.5,
and one full check per push instead of several. It also gives each kind of AI helper a fixed job
and model, so that sessions cost less. **Your call:** whether the phase estimate grows by a week.

## Position

- Phases 1 to 3 are **closed** as `v0.2.0`, `v0.3.0` (criterion 3 waived, §8.2.4 D7) and `v0.4.0`
  (§8.2.5 E1, E5).
- **Phase 4** ([polish and user testing](phase-4-polish-and-user-testing.md)), `v0.5.0`, is
  **in progress** (§8.2.7 G1–G11; §8.2.8 H1–H12; §8.2.9 I1–I5; §8.2.10 J1–J9). WP35 to WP42 delivered, as
  `v0.5.0-alpha.1` to `v0.5.0-alpha.8`, the last two [WP41](wp41-accuracy-fixes.md) and
  [WP42](wp42-verification-checks.md).
- **Next: WP43, the development loop** (§8.2.10 J1–J9): `/wp-plan 43`. It covers the commit
  hook, the push gate, CI, Python 3.14, the agent roster and the `## In brief` summaries.
- Then WP44, the small fixes (I1, I2); WP45–WP47 (OKF bundle, backfill, protocol); then the
  author's sessions and the second amendment, fixes from WP48.
- Phase 5 (`v0.6.0`) is the GUI (F5), Phase 6 (`v0.7.0`) validation (F1); v1.0 is OPN-08.

## Not to be re-decided

- **Versions:** one minor per phase; a retired name is never reused, except `v0.5.0` (E2, F2).
  The close takes `v0.5.0` alone; the session pushes the tags it can (G11). → §2.7 NOTE.
- **The development loop:** affected tests on commit, one push gate, a single pull-request leg on
  Python 3.14, budgets of 60 s, 5 min and 6 min, a defined agent roster, and `## In brief`. The
  floor stays 3.11. → §8.2.10 J1–J9; OPN-09.
- **Phase 4's shape:** accepted refactors before the protocol (G2); two OKF packages and a
  ratchet (G3, G8); checked findings logs (G4); protocol scripts gated, findings only from the
  author's sessions (G7); the VER-62 golden (G10). → §8.2.7.
- **The `MOD-nn` rulings** stand. → §8.2.8.
- **Phase 3's charge pipeline** stands as delivered. → §8.2.4; VER-59, VER-60.
- **No payload records wall-clock time** (VER-23). **A gated test gets cheaper only by §7.6's
  four levers** (WP33).
- **A moved edge edits `modularity-layering.yaml` in the same commit (VER-61). `upward:` stays
  empty, and `backend:` grows only by ruling (VER-65). A VER-62 miss is reverted, or ruled and
  re-pinned (G10, I4).** → `docs/project/contributing.md`.
- **What a package leaves open is a `REV-nn` row** until it is resolved (H12). A row placed in
  Phase 4 is `fixed` by the close (I3).
- **A stage declares its walk facts and its reads in the registry, and defines `key`** (VER-64;
  WP36 D3–D5, WP38 D11).
- **Tier 3 compares the published I–V and in-pore averages**, gating v0.7 (VAL-16, VAL-17; F1).
- **Layers read a model's declaration, never its name or class** (VER-56). → §5.4.3 NOTE.
- **A refusal names its requirement and the release that schedules it** (VER-67; WP40 D1–D4).
- **Only `poisson` adds a quadrature order for the `r` weight**; Phase 6 decides (E4, F1).
  → NUM-07 NOTE.
- **A golden's identity carries the stage-7 recipe** (E3; OPN-07, closed). → VAL-03.

## Inherited from Phases 1 and 2, still binding

- **The VAL-05 ensemble test fails on the archive by design** (§8.2.4 D7).
- **The schema and `nanopnp.PUBLIC` may change until v1.0** (F4). A move takes the release's
  identifier, `nanopnp/case/v0.5` (G6; §5.3.1 NOTE); each break is listed in `CHANGELOG.md`.
- **A callback is not an input** (VER-44). **A generated mesh is read only through
  `deployed_mesh`** (WP21). **Stage 1's frame is fixed**; tests use `prepared_2wcd`.
- **Every phase documents what it ships**, and the commands in that documentation run verbatim
  (VER-46). **Generated references are built, never committed.**

## What is still somebody else's

- **The paper's figure data**, for VAL-16 and VAL-17 at v0.7 (§8.2.4 D6), and E1's ensemble legs.
- **The Read the Docs project**; **`$NANOPNP_REFERENCE_DATA` on the nightly runner**.
- **OPN-04**, the ClyA-AS mutation list. **OPN-08**, what stable v1.0 contains.
- **The user-testing sessions, and the rulings on each `UT-nn`, `MOD-11`, any residual cycle
  (H6) and any WP41 drift beyond its bound (I4).**
- **The archived PQRs** for WP27–WP29's Tier 3; Phase 6 reports them (E1, F1).

## Dependencies To Read On Demand

| Need | Read |
|---|---|
| The desktop shell, its hooks and the probe bundle | The WP24 and WP31 plans and Outcomes; `gui/`; `.knowledge/07` §5; ADR-004 |
| Phase 4 scope and packages | `phase-4-polish-and-user-testing.md`; §8.2.6 F3–F6, §8.2.7, §8.2.8 |
| The OKF package's binding decisions | `okf-knowledge-bundle.md` (K1–K11); §8.2.7 G3, G8, G9 |
| The findings being fixed | `docs/project/modularity.md`, `modularity-layering.yaml`; `review-items.md` and the two logs |
| Case schema and supply chains | §5.3.1 NOTEs; `io/case.py`, `io/case_paths.py`, `io/resolved.py` (the base); `pipeline/case.py`, `pipeline/checks.py` (resolution and its checks) |
| The loop's measurements | §8.2.10's preamble; the Phase 4 plan's *Context*; `.claude/hooks/gate.sh`; `.github/workflows/ci.yml` |

The Outcomes of a delivered plan override its decisions table, so read the two together.

## Handoff Rules

When planning or finishing a package, replace this brief's position and live dependencies. Keep
it to 800 words; measurements stay in the records that own them. The full gate and the
independent shipping review stay required.
