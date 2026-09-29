# Current work

Updated 29 September 2026. Navigation only: `SPECIFICATION.md` governs. This brief is not
evidence that an unmerged branch has shipped.

## Position

- Phase 1 ([solver core](phase-1-solver-core.md)) is **closed** as `v0.5.0` (§8.2.3).
- Phase 2 ([geometry pipeline](phase-2-geometry-pipeline.md)) is **in progress**. WP17 to WP24
  are merged (to be tagged up to `v0.9.0-alpha.8`).
- **WP25** ([documentation increment 2](wp25-geometry-docs-and-example.md), criterion 5) is
  **delivered on its branch**, awaiting `/wp-ship` and merge as `v0.9.0-alpha.9`.
- **Phase criterion 3 stays open until `tests/tier3/test_val05_ensemble.py` runs on
  `$NANOPNP_REFERENCE_DATA`**. That run also pins `Z_MD`, and its numbers go into the
  [WP22 Outcomes](wp22-val05-reference-geometry.md#outcomes).
- **Next:** once WP25 merges, the end-of-phase report and `v0.9.0` wait only on criterion 3.

## What Phase 2 must not re-decide

Each is recorded in full where it points.

- **The schema moved once**, to `nanopnp/case/v2` (WP17). A later need widens an existing key's
  value set, and does not add a key. → §8.2.2 B3; WP17 D1.
- **`inputs.pqr` is accepted and refused** through `_UNCONSUMED_INPUTS` in `io/case.py` until
  Phase 3 consumes it. `inputs.profile` is stage 5's.
- **`physics.solid_permittivities` alone sets ε_protein and ε_membrane**; gate thresholds are never
  case keys. → WP17 D2, D3.
- **Python 3.11–3.14**, held by VER-47. → B4.
- **No HOLE on the default path** (B5). **Gmsh is optional** (B7): it meshes stage 5's region
  through `region_graph`, its settings are never case keys, its tests take `gmsh_module`, and the
  bundle carries it (B8). → §5.2.2 NOTE; WP23 D1–D4, D8, D10, D11.
- **Stage 4 emits `nanopnp/profile/v1` in the stage-1 frame**, spacing ≥ h and feature size
  > 2h, gated against the probe radius. → §5.2.1 and its NOTEs; WP20 D5, D9–D12.
- **Stage 1's frame is fixed**: axis on z at r = 0, `z = â·x`, +z to *cis*; stage 5 applies
  `centre_z_nm`. → the §5.3.1 NOTE on `structure:`; WP18 D2, D8, D10.
- **Stages 5 and 6 are settled:** the widest-margin chord; `auto` is
  `size_scale × min(0.05 nm, λ_D/5)`; a generated mesh is keyed on its recipe, records its content
  hash, and is read only through `deployed_mesh`.
  → WP21 D3, D7, D9–D13 and Outcomes; the §5.2.1 and §5.3.1 NOTEs.
- **VAL-05 is settled** (author, 28 September 2026): gated on `ε_G`, rms and `Δr_c`, per leg;
  nothing is fitted; only `nanopnp.validation.geometry` computes it. → §7.4 NOTE on VAL-05;
  WP22 D3–D6 and Outcomes.
- **The reference polygon's `pqr2grid` offset is recorded, never corrected.** → `.knowledge/04`
  §1.2, §1.4.
- **Density radii are CHARMM Rmin/2**; **the Cₙ average is a harmonic projection**. → §5.3.1
  NOTE on `geometry.density`; WP19.
- **The vendored 2WCD is in its crystal frame**; tests orient it through `prepared_2wcd`, and
  example 06 through its own `prepare.py`. → WP18 D16 Outcome; WP25 D4.
- **The geometry tab adds views, no physics**; hand edits are stage-1-frame `hand-edit` profiles
  through `inputs.profile`. → §8.2.2 B8, B9; WP24.
- **Lengths at the interchange boundary follow the reader.** The 3D density map is written in
  ångströms (B10); `.npz` and the `field1` grids stay in nm. An export is an output location and
  moves no key. → the IF-05 and IF-02 export NOTEs; WP25 D6, D7 and Outcomes.
- **An example's tag names its exit**: `run` and `plan` 0, `refused` 4. → VER-46; WP25 D10.

## Inherited from Phase 1, still binding

- **A callback is not an input**; a watched run keys the same artefact. → VER-44.
- **The public API is `nanopnp.PUBLIC`**; adding a name is a decision in
  `tests/tier1/test_public_api.py`. → the IF-01 NOTE.
- **Every phase documents what it ships**, commands run verbatim (VER-46). → WP16.
- **Generated references are built, never committed.**

## What is still somebody else's

- **The COMSOL exports** (WP13), against
  [`docs/validation/comsol-export-contract.md`](../validation/comsol-export-contract.md). Until they
  land every report carries `golden_source: self`.
- **The Read the Docs project** and **`$NANOPNP_REFERENCE_DATA` on the nightly runner**.

## Dependencies To Read On Demand

| Need | Read |
|---|---|
| VAL-05's harness and records | `validation/geometry.py`; WP22 Outcomes; `.knowledge/04` §1.4 |
| Phase 2 scope and rulings | `phase-2-geometry-pipeline.md`; `SPECIFICATION.md` §5.2–§5.2.2, §8.2.2 |
| The ClyA pipeline as executed, and gaps G1–G13 | `.knowledge/04-clya-geometry-and-charge.md` |
| Structure, geometry and meshing libraries | `.knowledge/07-software-stack.md` §2, §4, §8 |
| The desktop shell | `gui/`; WP15 and WP24 Outcomes; `.knowledge/07` §5 |
| The geometry guide, exports and example 06 | `docs/guide/structures.md`, `docs/guide/geometry.md`; `cli/export.py`; `examples/06-pdb-to-mesh/`; WP25 Outcomes |
| The seams Phase 2 builds on | `geometry/region.py` (`RegionStage`, `RegionRecord`, `build_region`, `region_graph`); `mesh/generate.py` (`mesh_region`), `mesh/sizing.py` and `mesh/gmsh_backend.py`; `mesh/ingest.py` (`MeshStage`, `deployed_mesh`); `geometry/contour.py`; `mesh/profile.py`; `core/stages.py`; `io/run.py`; `io/case.py` |
| Case schema, dotted paths and option sets | `SPECIFICATION.md` §5.3.1 and its NOTEs; `io/case.py` |
| Shell, packaging and licence constraints | ADR-004, CON-07, CON-09, CON-10, CON-11; `.knowledge/07-software-stack.md` §5–§6 |

A delivered plan's Outcomes override its decisions table; read them together.

## Handoff Rules

Replace this brief's position and live dependencies when planning or finishing a
package; no delivery diary. At most 800 words; measurements and derivations stay in their
owning records.

The full quality gate and independent shipping review remain required. Tier 3 is
recorded, not a push gate. No scientific requirement changes in this brief.
