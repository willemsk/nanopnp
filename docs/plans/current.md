# Current work

Updated 1 October 2026 (WP29 planned). This file is navigation only, and `SPECIFICATION.md` governs. It is not
evidence that an unmerged branch has shipped.

## Position

- Phase 1 ([solver core](phase-1-solver-core.md)) is **closed** as `v0.2.0` (§8.2.3; formerly
  `v0.5.0`, §8.2.4 D1).
- Phase 2 ([geometry pipeline](phase-2-geometry-pipeline.md)) is **closed** as `v0.3.0`, with
  criterion 3 waived: the ensemble's ε_G is −5.56 % against 5 % (§8.2.4 D7). `Z_MD` is 5.655 nm.
- Phase 3 ([charge pipeline](phase-3-charge-pipeline.md), release `v0.4.0`) is **in progress**:
  WP26–WP32. [WP26](wp26-physics-model-interface.md) (FR-20, VER-56) and
  [WP27](wp27-protonation.md) (FR-12, VER-57) are **merged**, tagged `v0.4.0-alpha.1` and `.2`.
  [WP28](wp28-charge-deposition.md) (FR-13, FR-14, QR-03; VER-01, VER-02, VER-58), deposition on
  the deployed mesh, is **merged** (`c6c0c0d`). [WP29](wp29-val06-apbs.md) (VAL-06, the phase
  gate) is **planned, not started**, its tolerance ruled. **Next: `/wp-implement`** on WP29.

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
- **`protonation` is stage 7's first half**, after `mesh`. From WP28 both halves run when the case
  protonates and its model declares `fixed_charge` (WP27 D3 retired). PROPKA decides every state.
  Registration leaves PDB2PQR's flipped amides and rings out. → §5.2 stage 7 note; PHY-16 step-3
  NOTE; §5.3.1 NOTEs on the protonation keys and `inputs:`.
- **The deposit** is element-wise of the potential's order, in the model frame, gated per plane
  against the source atoms, and read only from stage 7's artefact (WP28). A structure case solves
  charged by default. → PHY-16 NOTE on the deposition; §4.4 NOTE on the producer path.
- **The exclusion shell is in Phase 3 (WP30)**, off by default. → §8.2.4 D5; FR-15.
- **Tier 3 compares the published I–V and in-pore averages**, and gates v1.0, not Phase 3.
  → VAL-16, VAL-17; §8.2.4 D6.
- **The gate is 2WCD at Tier 2**, and the ensemble is recorded at Tier 3. → the phase plan's
  *Design decisions*.
- **Layers read a model's declaration, never its name or class** (VER-56 walks the source): WP28
  produces a charge only for a model declaring `fixed_charge`. → §5.4.3 NOTE.
- **VAL-06 compares interiors**, with our solution on APBS's faces. Its tolerance (3 % max, 1 %
  rms, 1.5 % axis, in a budget of half of each) is not re-argued after the run. → §7.4 NOTE.
- **`poisson` is the VAL-06 target**, runnable with solids and `inputs.charge`. It adds one
  quadrature order for the `r` weight; the coupled models do not, which is open, and which leaves
  them one order short on a deposited source (WP28 D13). → PHY-21 NOTE; NUM-07 NOTE on the `r`
  weight.

## Inherited from Phases 1 and 2, still binding

- **The VAL-05 ensemble test fails on the archive by design** (§8.2.4 D7): a waiver, not a
  regression.
- **Schema v2 is frozen**: a need widens a value set, never adds a key (§8.2.2 B3).
  `physics.solid_permittivities` alone sets ε_protein and ε_membrane (WP17 D2, D3).
- **The public API is `nanopnp.PUBLIC`**. Adding a name is a decision in
  `tests/tier1/test_public_api.py`.
- **A callback is not an input**: a watched run keys the same artefact (VER-44).
- **A generated mesh is read only through `deployed_mesh`**, keyed on its recipe, with its content
  hash recorded (WP21 D10, D12).
- **Stage 1's frame is fixed**: the axis on z at r = 0, +z towards *cis*; stage 5 applies
  `centre_z_nm`. Tests orient the vendored 2WCD through `prepared_2wcd` (WP18 D16).
- **Lengths at the interchange boundary follow the reader.** A 3D map is in Å (B10), and (r, z)
  grids stay in nm.
- **Every phase documents what it ships**, and its commands run verbatim (VER-46).
- **Generated references are built, never committed.** A new payload is declared in `PAYLOADS`
  and exercised by `--selftest`.

## What is still somebody else's

- **The data behind the paper's published figures**, conventions declared (VAL-16, VAL-17), for
  v1.0; the COMSOL field exports are no longer asked for (§8.2.4 D6).
- **The Read the Docs project**, and **`$NANOPNP_REFERENCE_DATA` on the nightly runner**.
- **OPN-04**, the ClyA-AS mutation list, which is the provenance of `Q_net`.
- **The archived PQRs**, extracted under `$NANOPNP_REFERENCE_DATA` for WP27's and WP28's Tier 3
  (neither yet run).

## Dependencies To Read On Demand

| Need | Read |
|---|---|
| Phase 3 scope, decisions and packages | `phase-3-charge-pipeline.md`; `SPECIFICATION.md` §4.4, §5.2 stage 7, §8.2.4 |
| The consumer path, and why it aliases | VER-29; §4.4 NOTEs; `.knowledge/04` §3.2; `.knowledge/06` §8.1.1 |
| The physics-model interface | `docs/project/physics-models.md`; the WP26 plan's Outcomes; `physics/models.py` |
| PDB2PQR, PROPKA and APBS facts | `.knowledge/07` §3, incl. *as a per-frame driver*; `density/radii.py` and `data/radii/` |
| The protonation artefact | `charge/protonation.py` (`ProtonationTable`); WP27 Outcomes; `protonated_2wcd` |
| APBS by maps, and VAL-06's construction | The WP29 plan, *Design* §1–§6; `.knowledge/07` §3 *APBS 3.4.1 driven by maps* |
| The deposition and its gates | The WP28 plan and Outcomes; `.knowledge/04` §3.3; `charge/kernel.py`, `deposit.py`, `fields.py`, `stage.py` |
| A charged 2WCD walk in a test | `seeded_protonated_2wcd` (`tests/conftest.py`); `tests/tier2/test_charge_2wcd.py` |
| Case schema, option sets and supply chains | §5.3.1 and its NOTEs; `io/case.py` (`Charge`, `SUPPLY_CHAINS`, `_require_runnable`) |
| The desktop shell | `gui/`; WP24 Outcomes; `.knowledge/07` §5 |

A delivered plan's Outcomes override its decisions table, so read the two together.

## Handoff Rules

When planning or finishing a package, replace this brief's position and live dependencies. It is
not a delivery diary. Keep it to 800 words at most; measurements and derivations stay in the
records that own them.

The full gate and the independent shipping review remain required. Tier 3 is recorded, not
gated. No scientific requirement changes in this brief.
