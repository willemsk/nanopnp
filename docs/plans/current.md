# Current work

Updated 3 October 2026 (WP34 planned). This file is navigation only; `SPECIFICATION.md` governs.
Nothing here is evidence that an unmerged branch has shipped.

## Position

- Phase 1 ([solver core](phase-1-solver-core.md)) is **closed** as `v0.2.0` (§8.2.3; §8.2.4 D1).
- Phase 2 ([geometry pipeline](phase-2-geometry-pipeline.md)) is **closed** as `v0.3.0`, with
  criterion 3 waived (§8.2.4 D7). `Z_MD` is 5.655 nm.
- Phase 3 ([charge pipeline](phase-3-charge-pipeline.md), release `v0.4.0`) is **in progress**.
  - WP26–WP33 are **merged**, with `main` at `4375797`, and tagged `v0.4.0-alpha.1` to `.8`.
  - [WP34](wp34-phase-3-close.md), the phase close (§8.2.5 E1–E5), is **planned**, to be tagged
    `v0.4.0`. **Next: `/wp-implement`** on WP34.
- **Phase 4 is released as `v0.5.0`**, not v1.0, and reuses the retired `v0.5.0` names (§2.7
  Versioning NOTE; §8.2.5 E2). Stable v1.0's content is OPN-08, the author's.

## What Phase 3 must not re-decide

Each is recorded in full where it points.

- **Versions:** one minor per phase, and a retired tag name is never reused. → §2.7 NOTE; §8.2.4
  D1; `.github/renumbered-tags.txt`.
- **The kernel is the closed-form azimuthal mean** of each atom's 3D Gaussian. It is deposited on
  the deployed mesh and renormalised per atom, and no 3D grid is built. → PHY-16 steps 4–6, PHY-18;
  §8.2.4 D2.
- **VAL-06 runs APBS from `apbs-binary`.** It is test-only and required (`NANOPNP_REQUIRE_APBS=1`)
  on every CI leg except Windows. Its tolerance is not re-argued. → VAL-06 and its §7.4 NOTE; WP29
  D11, D12.
- **Protonation is per frame.** It is stage 7's first half, run after `mesh`. → §8.2.4 D4; §5.2
  stage-7 note.
- **The deposit** is element-wise at the potential's order, gated per plane against the atoms, and
  read only from stage 7's artefact. → PHY-16 NOTE on the deposition; WP28.
- **WP30's two switches are built from the stage-4 profile**: `χ` read only from stage 7's
  artefact, the shell a stage-5 dilation. Both are off by default, and at 0 every key is unchanged
  (VER-59). → §4.4 NOTE on the derived solid fraction; §5.2.1 NOTE on the shell; WP30 Outcomes.
- **The shell reads every charge number from a stage's artefact**, and the bundle collects its
  Python LGPL payloads as source. → ADR-004 packaging NOTE; VER-60; the WP31 Outcomes.
- **No payload or stage-7 summary records wall-clock time** (VER-23; WP32 D15).
- **A gated test gets cheaper only by the §7.6 NOTE's four levers.** → the WP33 Outcomes.
- **Tier 3 compares the published I–V and in-pore averages**, and gates v0.5, Phase 4's release
  (VAL-16, VAL-17; §8.2.5 E2).
- **Layers read a model's declaration, never its name or class** (VER-56). → §5.4.3 NOTE.
- **`poisson` adds one quadrature order for the `r` weight; the coupled models do not.** WP34
  measures it, and Phase 4 decides (§8.2.5 E4). → PHY-21 NOTE; NUM-07 NOTE.

## Inherited from Phases 1 and 2, still binding

- **The VAL-05 ensemble test fails on the archive by design** (§8.2.4 D7).
- **Schema v2 is frozen**: a new need widens a value set and never adds a key (§8.2.2 B3).
  `physics.solid_permittivities` alone sets ε_protein and ε_membrane.
- **The public API is `nanopnp.PUBLIC`**, and adding to it is a decision made in
  `tests/tier1/test_public_api.py`.
- **A callback is not an input** (VER-44). **A generated mesh is read only through
  `deployed_mesh`** (WP21 D10, D12). **Stage 1's frame is fixed**, and tests orient 2WCD through
  `prepared_2wcd`.
- **Every phase documents what it ships**, and the commands in that documentation run verbatim
  (VER-46). **Generated references are built, never committed.**

## What is still somebody else's

- **The data behind the paper's published figures**, needed for VAL-16 and VAL-17 at v0.5
  (§8.2.4 D6). The ensemble legs Phase 3 waived (§8.2.5 E1) need the same archive.
- **The Read the Docs project**, and **`$NANOPNP_REFERENCE_DATA` on the nightly runner**.
- **OPN-04**, the ClyA-AS mutation list. **OPN-08**, what stable v1.0 contains.
- **The archived PQRs** for WP27–WP29's Tier 3, none of which has run yet.

## Dependencies To Read On Demand

| Need | Read |
|---|---|
| Phase 3 scope and packages | `phase-3-charge-pipeline.md`; §4.4, §5.2 stage 7, §8.2.4 |
| The physics-model interface | `docs/project/physics-models.md`; `physics/models.py` |
| The desktop shell, its hooks and the probe bundle | The WP24 and WP31 plans and Outcomes; `gui/`; `.knowledge/07` §5; ADR-004 |
| The deposition and stage 7 | The WP28 plan and Outcomes; `charge/stage.py` |
| Example 07 and the charge guide | The WP32 plan and Outcomes; `examples/07-pdb-to-charged-run/`; `docs/guide/charge.md`; `validation/examples.py` |
| PDB2PQR, PROPKA and APBS | `.knowledge/07` §3; the WP29 plan |
| Case schema and supply chains | §5.3.1 NOTEs; `io/case.py` |

The Outcomes of a delivered plan override its decisions table, so read the two together.

## Handoff Rules

When planning or finishing a package, replace this brief's position and live dependencies. It is
not a delivery diary. Keep it to 800 words at most; measurements and derivations stay in the
records that own them. The full gate and the independent shipping review remain required. Tier 3
is recorded, not gated.
