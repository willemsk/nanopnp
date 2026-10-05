# Current work

Updated 5 October 2026 (WP36 planned). Navigation only; `SPECIFICATION.md`
governs; nothing here is evidence an unmerged branch shipped.

## Position

- Phases 1 to 3 are **closed** as `v0.2.0`, `v0.3.0` (criterion 3 waived, §8.2.4 D7) and `v0.4.0`
  (§8.2.5 E1, E5).
- **Phase 4** ([polish and user testing](phase-4-polish-and-user-testing.md)), `v0.5.0`, is
  **in progress** (§8.2.7 G1–G11; §8.2.8 H1–H9), estimated at 3–5 weeks. WP35 merged as
  `v0.5.0-alpha.1`, and the author has ruled all 17 `MOD-nn` (§8.2.8).
- **Next: `/wp-implement`** for WP36, the stage protocol and the walk (`MOD-01`, `MOD-02`,
  `MOD-12`; [plan](wp36-stage-protocol-and-walk.md)). Then WP37 (cycle cuts, exit codes, backend
  guard), WP38 (`io` split), WP39 (backend registries, and H6's acyclicity target measured), WP40
  (stale refusals), WP41 (OKF bundle), WP42 (backfill), WP43 (user-testing protocol). The author's sessions follow, and a second amendment plans and
  numbers the fixes, the documentation increment and the close.
- Phase 5 (`v0.6.0`) is the GUI (F5), Phase 6 (`v0.7.0`) validation (F1); v1.0 is OPN-08.

## Not to be re-decided

Each is recorded in full where it points.

- **Versions:** one minor per phase; a retired name is never reused, except `v0.5.0` for Phase 4
  (E2, F2). The close takes `v0.5.0` alone, and the session pushes each tag if its access allows
  it (G11). → §2.7 NOTE; §8.2.4 D1; the head of `CHANGELOG.md`.
- **Phase 4's shape:** accepted refactors before the protocol (G2); two OKF packages and a
  ratchet (G3, G8); checked findings logs (G4); protocol scripts gated, findings only from the
  author's sessions (G7); the VER-62 golden (G10). → §8.2.7.
- **The `MOD-nn` rulings:** `MOD-11` waits for the sessions (H2); QR-13 restated and the backend
  confined (H3); an acyclic `top` relation, a miss ruled, never forced (H6); three backend
  registries, no schema move (H7). → §8.2.8.
- **Phase 3's charge pipeline**: the closed-form kernel on the deployed mesh (D2; WP28),
  protonation per frame (D4), VAL-06's tolerance (D3), WP30's switches off (VER-59), charges
  read from artefacts (VER-60). → §8.2.4.
- **No payload records wall-clock time** (VER-23). **A gated test gets cheaper
  only by the §7.6 NOTE's four levers** (WP33).
- **An edge moved edits `modularity-layering.yaml` in the same commit (VER-61); a VER-62 miss is
  reverted, or ruled and re-pinned (G10).** → `docs/project/contributing.md`.
- **Tier 3 compares the published I–V and in-pore averages**, gating v0.7 (VAL-16, VAL-17; F1).
- **Layers read a model's declaration, never its name or class** (VER-56). → §5.4.3 NOTE.
- **Only `poisson` adds a quadrature order for the `r` weight**; Phase 6 decides (E4, F1).
  → NUM-07 NOTE.
- **A golden's identity carries the stage-7 recipe** (E3; OPN-07, closed). → VAL-03.

## Inherited from Phases 1 and 2, still binding

- **The VAL-05 ensemble test fails on the archive by design** (§8.2.4 D7).
- **The schema and `nanopnp.PUBLIC` may change until v1.0** (§8.2.6 F4, superseding B3). A move
  takes the release's identifier, `nanopnp/case/v0.5` first. It may change between alpha packages,
  it is fixed at the tag, and an earlier identifier reads as its upgrade (§8.2.7 G6; the §5.3.1
  NOTE). An API change is decided in `test_public_api.py`, and each break goes in `CHANGELOG.md`.
  `physics.solid_permittivities` alone sets ε_protein and ε_membrane.
- **A callback is not an input** (VER-44). **A generated mesh is read only through
  `deployed_mesh`** (WP21 D10, D12). **Stage 1's frame is fixed**; tests use `prepared_2wcd`.
- **Every phase documents what it ships**, and the commands in that documentation run verbatim
  (VER-46). **Generated references are built, never committed.**

## What is still somebody else's

- **The paper's figure data**, for VAL-16 and VAL-17 at v0.7 (§8.2.4 D6), and E1's ensemble legs.
- **The Read the Docs project**; **`$NANOPNP_REFERENCE_DATA` on the nightly runner**.
- **OPN-04**, the ClyA-AS mutation list. **OPN-08**, what stable v1.0 contains.
- **Phase 4's rulings on each `UT-nn`, on `MOD-11` after the sessions, on any residual cycle
  (H6), and the user-testing sessions themselves** (G4, G7; §8.2.8).
- **The archived PQRs** for WP27–WP29's Tier 3; Phase 6 reports them (E1, F1).

## Dependencies To Read On Demand

| Need | Read |
|---|---|
| The desktop shell, its hooks and the probe bundle | The WP24 and WP31 plans and Outcomes; `gui/`; `.knowledge/07` §5; ADR-004 |
| Phase 4 scope and packages | `phase-4-polish-and-user-testing.md`; §8.2.6 F3–F6, §8.2.7, §8.2.8 |
| The OKF package's binding decisions | `okf-knowledge-bundle.md` (K1–K11); §8.2.7 G3, G8, G9 |
| The findings being fixed | `docs/project/modularity.md`, its findings log and `modularity-layering.yaml` |
| Stages, registries and the walk | `core/stages.py`; `io/run.py`; `physics/models.py` and `docs/project/physics-models.md`; `materials/models.py` |
| Case schema and supply chains | §5.3.1 NOTEs; `io/case.py` |

The Outcomes of a delivered plan override its decisions table, so read the two together.

## Handoff Rules

When planning or finishing a package, replace this brief's position and live dependencies. It is
not a delivery diary. Keep it to 800 words at most; measurements and derivations stay in the
records that own them. The full gate and the independent shipping review remain required. Tier 3
is recorded, not gated.
