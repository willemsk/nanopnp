# Current work

Updated 30 September 2026. This file is navigation only, and `SPECIFICATION.md` governs. It is not
evidence that an unmerged branch has shipped.

## Position

- Phase 1 ([solver core](phase-1-solver-core.md)) is **closed** as `v0.2.0` (§8.2.3). It was
  released as `v0.5.0` before the renumbering of §8.2.4 D1.
- Phase 2 ([geometry pipeline](phase-2-geometry-pipeline.md)) is **closed** as `v0.3.0`, with
  criterion 3 waived: the ensemble's ε_G is −5.56 % against 5 % (§8.2.4 D7). `Z_MD` is 5.655 nm.
- **After this report merges, the author** runs `.github/scripts/renumber-tags.sh --apply`, then
  tags the merge commit `v0.3.0`.
- Phase 3 ([charge pipeline](phase-3-charge-pipeline.md), release `v0.4.0`) is **planned**:
  WP26–WP32. [WP26](wp26-physics-model-interface.md), the physics-model interface (FR-20), is
  planned. **Next: `/wp-implement`**.

## What Phase 3 must not re-decide

Each is recorded in full where it points.

- **Versions:** one minor per phase, and a retired tag name is never reused. → §2.7 Versioning
  NOTE; §8.2.4 D1; `.github/renumbered-tags.txt`.
- **The kernel is the closed-form azimuthal mean of each atom's 3D Gaussian**, deposited on the
  deployed mesh and renormalised per atom. No 3D charge grid is built, and the 0.005 nm (r, z) grid
  is the export and the producer leg. → PHY-16 steps 4–6 and their NOTE, PHY-18; §8.2.4 D2.
- **VAL-06 runs APBS from `apbs-binary`**, test-only, required on Linux and macOS. It has a gated
  like-for-like leg and a recorded leg from the PQR. → VAL-06; §8.2.4 D3.
- **Protonation is per frame.** `inputs.pqr` is a single- or multi-MODEL PQR, and the schema does
  not move. → §8.2.4 D4.
- **The exclusion shell is in Phase 3 (WP30)**, off by default. → §8.2.4 D5; FR-15.
- **Tier 3 compares the published I–V and in-pore averages**, and gates v1.0, not Phase 3.
  → VAL-16, VAL-17; §8.2.4 D6.
- **The gate is 2WCD at Tier 2**, and the ensemble is recorded at Tier 3. → the phase plan's
  *Design decisions*.
- **After WP26, layers read a model's declaration, never its name or class**: WP28 produces a
  charge only for a model declaring `fixed_charge`. → §5.4.3 NOTE.

## Inherited from Phases 1 and 2, still binding

- **The VAL-05 ensemble test fails on the archive by design** (§8.2.4 D7): a waiver, not a
  regression.
- **Schema v2 is frozen**: a need widens a value set, never adds a key (§8.2.2 B3).
  `physics.solid_permittivities` alone sets ε_protein and ε_membrane (WP17 D2, D3).
- **A callback is not an input**, and a watched run keys the same artefact (VER-44).
  `ArtefactHook` keys nothing.
- **The public API is `nanopnp.PUBLIC`**. Adding a name is a decision in
  `tests/tier1/test_public_api.py`.
- **A generated mesh is read only through `deployed_mesh`**, keyed on its recipe, with its content
  hash recorded (WP21 D10, D12).
- **Stage 1's frame is fixed**: the axis is on z at r = 0 and +z is towards *cis*. Stage 5 applies
  `centre_z_nm`. The vendored 2WCD is in its crystal frame, so tests orient it through
  `prepared_2wcd` (WP18 D16).
- **Lengths at the interchange boundary follow the reader.** A 3D map is in Å (B10), and (r, z)
  grids stay in nm.
- **Every phase documents what it ships**, and its commands run verbatim (VER-46). An example's tag
  names its exit.
- **Generated references are built, never committed.** A new compiled or data-bearing payload is
  declared in `PAYLOADS` and exercised by `--selftest`.

## What is still somebody else's

- **The data behind the paper's published figures**, with each quantity's conventions declared
  (VAL-16, VAL-17), for v1.0. The COMSOL field exports are no longer asked for (§8.2.4 D6).
- **The Read the Docs project**, and **`$NANOPNP_REFERENCE_DATA` on the nightly runner**.
- **OPN-04**, the ClyA-AS mutation list, which is the provenance of `Q_net`.

## Dependencies To Read On Demand

| Need | Read |
|---|---|
| Phase 3 scope, decisions and packages | `phase-3-charge-pipeline.md`; `SPECIFICATION.md` §4.4, §5.2 stage 7, §8.2.4 |
| The consumer path stage 7 has today | `charge/stage.py`, `charge/fields.py`; VER-29, VER-30; WP9 plan |
| Why the consumer leg aliases | §4.4 NOTEs; `.knowledge/04` §3–§3.2; `.knowledge/06` §8.1.1 |
| The physics-model seams (WP26) | The WP26 plan's *Design* §1 inventory; `physics/models.py` |
| PDB2PQR, PROPKA and APBS facts | `.knowledge/07` §3; `density/radii.py` and `data/radii/` |
| The reduction the charge reuses | `symmetry/annular.py`; VER-50 |
| Case schema, option sets and supply chains | §5.3.1 and its NOTEs; `io/case.py` (`Charge`, `SUPPLY_CHAINS`, `_require_runnable`) |
| The desktop shell | `gui/`; WP24 Outcomes; `.knowledge/07` §5 |

A delivered plan's Outcomes override its decisions table, so read the two together.

## Handoff Rules

When planning or finishing a package, replace this brief's position and live dependencies. It is
not a delivery diary. Keep it to 800 words at most; measurements and derivations stay in the
records that own them.

The full quality gate and the independent shipping review remain required. Tier 3 is recorded and
is not a push gate. No scientific requirement changes in this brief.
