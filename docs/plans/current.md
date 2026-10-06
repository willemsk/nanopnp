# Current work

Updated 6 October 2026 (WP38 merged; WP39 planned). Navigation only; `SPECIFICATION.md` governs;
nothing here is evidence an unmerged branch shipped.

## Position

- Phases 1 to 3 are **closed** as `v0.2.0`, `v0.3.0` (criterion 3 waived, §8.2.4 D7) and `v0.4.0`
  (§8.2.5 E1, E5).
- **Phase 4** ([polish and user testing](phase-4-polish-and-user-testing.md)), `v0.5.0`, is
  **in progress** (§8.2.7 G1–G11; §8.2.8 H1–H12; §8.2.9 I1–I5). WP35 to WP38 merged, as
  `v0.5.0-alpha.1` to `v0.5.0-alpha.4`.
- [WP39, the backend registries](wp39-backend-registries.md), is **planned** (`v0.5.0-alpha.5`):
  mesher, solver and stabilisation registries; `__version__` and `PUBLIC` to `core/public.py`,
  emptying both upward lists (REV-05); H6 asserted; REV-36 to REV-38. **Next: `/wp-implement`.**
- Then WP40 (refusals), WP41–WP43 (the review register's fixes; I1, I2), WP44–WP46 (OKF bundle,
  backfill, protocol); then the author's sessions and the second amendment, fixes from WP47.
- Phase 5 (`v0.6.0`) is the GUI (F5), Phase 6 (`v0.7.0`) validation (F1); v1.0 is OPN-08.

## Not to be re-decided

- **Versions:** one minor per phase; a retired name is never reused, except `v0.5.0` (E2, F2).
  The close takes `v0.5.0` alone; the session pushes the tags it can (G11). → §2.7 NOTE.
- **Phase 4's shape:** accepted refactors before the protocol (G2); two OKF packages and a
  ratchet (G3, G8); checked findings logs (G4); protocol scripts gated, findings only from the
  author's sessions (G7); the VER-62 golden (G10). → §8.2.7.
- **The `MOD-nn` rulings:** `MOD-09`, `MOD-18` to Phase 5 (H4, H10); `MOD-11` after the
  sessions (H2); QR-13 restated (H3); an acyclic `top` relation, never forced (H6); three backend
  registries (H7); kernel in `numerics/` (H11). → §8.2.8.
- **Phase 3's charge pipeline** stands as delivered. → §8.2.4; VER-59, VER-60.
- **No payload records wall-clock time** (VER-23). **A gated test gets cheaper
  only by the §7.6 NOTE's four levers** (WP33).
- **An edge moved edits `modularity-layering.yaml` in the same commit (VER-61); a VER-62 miss is
  reverted, or ruled and re-pinned (G10); WP41 re-pins only within a bound argued first (I4).** → `docs/project/contributing.md`.
- **`upward:` only shrinks, and is empty from WP39; `backend:` grows only by ruling** (VER-61, VER-65). A cut removes a
  dependency, never defers it (WP37 D12).
- **What a package leaves open is a `REV-nn` row** of `docs/project/review-findings.md` until it
  is resolved (H12), written by `/wp-implement` and `/wp-ship`. A row placed in Phase 4 is
  `fixed` by the close (§8.2.9 I3).
- **A stage declares its walk facts in the registry and defines `key`.** The walk runs stages in
  registration order (VER-64; WP36 D3–D5). A stage declares every upstream artefact it reads and is
  handed only those; a walk runs its target's input closure (WP38 D11).
- **Tier 3 compares the published I–V and in-pore averages**, gating v0.7 (VAL-16, VAL-17; F1).
- **Layers read a model's declaration, never its name or class** (VER-56). → §5.4.3 NOTE.
- **Only `poisson` adds a quadrature order for the `r` weight**; Phase 6 decides (E4, F1).
  → NUM-07 NOTE.
- **A golden's identity carries the stage-7 recipe** (E3; OPN-07, closed). → VAL-03.

## Inherited from Phases 1 and 2, still binding

- **The VAL-05 ensemble test fails on the archive by design** (§8.2.4 D7).
- **The schema and `nanopnp.PUBLIC` may change until v1.0** (§8.2.6 F4, superseding B3). A move
  takes the release's identifier, `nanopnp/case/v0.5` first, fixed at the tag; an earlier one
  reads as its upgrade (G6; §5.3.1 NOTE). Each break is decided in `test_public_api.py` and listed
  in `CHANGELOG.md`.
  `physics.solid_permittivities` alone sets ε_protein and ε_membrane.
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
| Stages, registries and the walk | `core/stages.py`; `pipeline/run.py`; `physics/models.py` and `docs/project/physics-models.md`; `materials/models.py` |
| Case schema and supply chains | §5.3.1 NOTEs; `io/case.py`, `io/case_paths.py`, `io/resolved.py` (the base); `pipeline/case.py`, `pipeline/checks.py` (resolution and its checks) |
| The backend registries | WP39 D1–D7; `physics/stabilisation.py` (the shape copied); §5.5, QR-14 |

The Outcomes of a delivered plan override its decisions table, so read the two together.

## Handoff Rules

When planning or finishing a package, replace this brief's position and live dependencies. Keep
it to 800 words; measurements stay in the records that own them. The full gate and the
independent shipping review stay required.
