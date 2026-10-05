# Current work

Updated 5 October 2026 (Phase 4 planned). Navigation only; `SPECIFICATION.md`
governs; nothing here is evidence an unmerged branch shipped.

## Position

- Phases 1 to 3 are **closed** as `v0.2.0`, `v0.3.0` (criterion 3 waived, §8.2.4 D7) and `v0.4.0`
  (§8.2.5 E1, E5).
- **Phase 4** ([polish and user testing](phase-4-polish-and-user-testing.md)), `v0.5.0`, is
  **planned, not started** (§8.2.7 G1–G11). WP35, the modularity exploration, is planned in full.
  Everything after it is provisional until `/phase-plan amend 4`. **Next: `/wp-plan 35`**.
- After WP35 the author rules every `MOD-nn` finding. `/phase-plan amend 4` then plans these, in
  order: the refactors, the OKF bundle and its backfill, and the user-testing protocol. The
  author's sessions follow, and a second amendment plans the fixes, the documentation increment
  and the close.
- Phase 5 (`v0.6.0`) is the GUI (F5), Phase 6 (`v0.7.0`) validation (F1); v1.0 is OPN-08.

## Not to be re-decided

Each is recorded in full where it points.

- **Versions:** one minor per phase; a retired name is never reused, except `v0.5.0` for Phase 4
  (E2, F2). The close takes `v0.5.0` alone, and the session pushes each tag if its access allows
  it (G11). → §2.7 NOTE; §8.2.4 D1; the head of `CHANGELOG.md`.
- **Phase 4's shape:** a report and guard, with no refactor in that PR (G1); every accepted
  refactor before the protocol (G2); two OKF packages joined by a ratchet (G3, G8); findings logs
  in the repository, checked, with a closable header (G4); protocol scripts executed by the gate,
  and findings only from the author's sessions (G7); a number-stability golden at 10⁻⁸ (G10).
  → §8.2.7; the Phase 4 plan.
- **Phase 3's charge pipeline**: the closed-form azimuthal kernel, deposited element-wise on the
  deployed mesh (§8.2.4 D2; PHY-16 to PHY-18; WP28); protonation per frame (D4); VAL-06 from
  `apbs-binary`, with its tolerance not re-argued (D3; WP29); WP30's switches off by default
  (VER-59); and the shell reads every charge number from an artefact (VER-60).
- **No payload or stage-7 summary records wall-clock time** (VER-23). **A gated test gets cheaper
  only by the §7.6 NOTE's four levers** (WP33).
- **Tier 3 compares the published I–V and in-pore averages**, gating v0.7 (VAL-16, VAL-17; F1).
- **Layers read a model's declaration, never its name or class** (VER-56). → §5.4.3 NOTE.
- **Only `poisson` adds a quadrature order for the `r` weight.** WP34 measured the coupled
  models through `Measures.weight_extra_order`, a seam no key reaches, and Phase 6 decides (E4,
  F1). → NUM-07 NOTE; `.knowledge/06` §2.2.
- **A golden's identity carries the stage-7 recipe** of a deposited charge or a derived `χ`, so a
  `structure:` case needs the `structure` extra to have one (E3; OPN-07, closed). → VAL-03;
  `validation/comsol.py`.

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
- **Phase 4's rulings on each `MOD-nn` and `UT-nn`, and the user-testing sessions themselves**
  (G4, G7).
- **The archived PQRs** for WP27–WP29's Tier 3; Phase 6 reports them (E1, F1).

## Dependencies To Read On Demand

| Need | Read |
|---|---|
| The desktop shell, its hooks and the probe bundle | The WP24 and WP31 plans and Outcomes; `gui/`; `.knowledge/07` §5; ADR-004 |
| Phase 4 scope and packages | `phase-4-polish-and-user-testing.md`; §8.2.6 F3–F6, §8.2.7 |
| The OKF package's binding decisions | `okf-knowledge-bundle.md` (K1–K11); §8.2.7 G3, G8, G9 |
| Stages, registries and the walk | `core/stages.py`; `io/run.py`; `physics/models.py` and `docs/project/physics-models.md`; `materials/models.py` |
| Case schema and supply chains | §5.3.1 NOTEs; `io/case.py` |

The Outcomes of a delivered plan override its decisions table, so read the two together.

## Handoff Rules

When planning or finishing a package, replace this brief's position and live dependencies. It is
not a delivery diary. Keep it to 800 words at most; measurements and derivations stay in the
records that own them. The full gate and the independent shipping review remain required. Tier 3
is recorded, not gated.
