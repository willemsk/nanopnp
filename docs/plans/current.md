# Current work

Updated 28 September 2026. Navigation only: `SPECIFICATION.md` governs. This brief is not
evidence that an unmerged branch has shipped.

## Position

- Phase 1 ([solver core](phase-1-solver-core.md)) is **closed** as `v0.5.0` (§8.2.3); C1 and C2
  land as addenda to its report.
- Phase 2 ([geometry pipeline](phase-2-geometry-pipeline.md)) is **in progress**. WP17 to WP21
  are merged (`v0.9.0-alpha.1` to `alpha.5`). WP23–WP25 are planned in the phase plan (§8.2.2).
- **WP22** ([VAL-05 against the reference geometry](wp22-val05-reference-geometry.md)) is
  **implemented** on `claude/dreamy-gates-seojm6`, PR open. Next: `/wp-ship` in a fresh session;
  it becomes `v0.9.0-alpha.6`. The 2WCD leg passes at Tier 2. **Phase criterion 3 stays open until
  `tests/tier3/test_val05_ensemble.py` runs on `$NANOPNP_REFERENCE_DATA`**; that run also pins
  `Z_MD`, and its numbers go into the WP22 Outcomes. Then WP23, the Gmsh backend.

## What Phase 2 must not re-decide

Each item is recorded in full where it points. Read it there first.

- **The schema moved once**, to `nanopnp/case/v2` (WP17). A later need widens an existing key's
  value set, and does not add a key. → §8.2.2 B3; WP17 D1.
- **`inputs.pqr` is accepted and refused** through `_UNCONSUMED_INPUTS` in `io/case.py` until
  Phase 3 consumes it. `inputs.profile` is stage 5's.
- **`physics.solid_permittivities` alone sets ε_protein and ε_membrane**; gate thresholds are never
  case keys. → WP17 D2, D3.
- **Python 3.11–3.14**, held together by VER-47. → §8.2.2 B4.
- **No HOLE on the default path** (B5). **Gmsh arrives in WP23, optional** (B7). → §8.2.2.
- **Stage 4 emits `nanopnp/profile/v1` in the stage-1 frame**, spacing ≥ h and feature size
  > 2h, gated against the probe radius. → §5.2.1 and its NOTEs; WP20 D5, D9–D12.
- **Stage 1's frame is fixed**: axis on z at r = 0, `z = â·x`, +z to *cis*; stage 5 applies
  `centre_z_nm`. → the §5.3.1 NOTE on `structure:`; WP18 D2, D8, D10.
- **Stages 5 and 6 are settled:** the membrane's inner edge is the widest-margin chord inside the
  body; edges are named by face adjacency; `auto` is `size_scale × min(0.05 nm, λ_D/5)` at
  `ε_r,f⁰`; a generated mesh is keyed on its recipe, records its content hash, needs both solid
  permittivities and passes the wall-size gate; consumers read it only through `deployed_mesh`.
  → WP21 D3, D7, D9–D13 and Outcomes; the §5.2.1 and §5.3.1 NOTEs.
- **VAL-05 is settled** (author, 28 September 2026) on both B2 legs: gated on `ε_G`, rms and
  `Δr_c`; ensemble 5 %, 0.1 nm, 0.1 nm at `centre_z_nm = 0` (G9), frames 48–97; 2WCD 10 %, 0.1 nm,
  0.2 nm, registered by its Cα centroid at `Z_MD = 5.63` nm. Nothing is fitted. Only
  `nanopnp.validation.geometry` computes it. D2's plane rule binds the gated comparison, not the
  recorded sweep. → §7.4 NOTE on VAL-05; WP22 D3–D6 and Outcomes.
- **The reference polygon was binned by `pqr2grid` at L = 15 nm and hand-edited**, with vertices
  moved. That offset is attributed and recorded, and never corrected. → `.knowledge/04` §1.2,
  §1.4; ruling 14.
- **The density's radii are CHARMM Rmin/2**, with no element fallback; **the Cₙ average is a
  harmonic projection**. → the §5.3.1 NOTE on `geometry.density`; WP19 D3, D7, D9.
- **The vendored 2WCD is in its crystal frame**; tests orient it through `prepared_2wcd` in
  `tests/conftest.py`. → WP18 D16 Outcome.

## Inherited from Phase 1, still binding

- **A callback is not an input**; a watched run keys the same artefact. → VER-44.
- **The public API is `nanopnp.PUBLIC`**; adding a name is a decision in
  `tests/tier1/test_public_api.py`. → the IF-01 NOTE.
- **Every phase documents what it ships**; documented commands run verbatim (VER-46). → WP16 D4,
  D8, D9.
- **Generated references are rendered at build time, never committed.**

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
| The seams Phase 2 builds on | `geometry/region.py` (`RegionStage`, `RegionRecord`, `build_region`); `mesh/generate.py` and `mesh/sizing.py`; `mesh/ingest.py` (`MeshStage`, `deployed_mesh`); `geometry/contour.py`; `mesh/profile.py`; `core/stages.py`; `io/run.py`; `io/case.py` |
| Case schema, dotted paths and option sets | `SPECIFICATION.md` §5.3.1 and its NOTEs; `io/case.py` |
| Shell, packaging and licence constraints | ADR-004, CON-07, CON-09, CON-10, CON-11; `.knowledge/07-software-stack.md` §5–§6 |

A delivered plan's Outcomes override its decisions table; read them together.

## Handoff Rules

Replace this brief's current position and live dependencies when planning or
finishing a package; do not append a delivery diary. Target at most 800 words.
Keep measurements and derivations in their owning records, and preserve existing
historical sections there. Load those sections only when a decision, implementation
or review needs their evidence.

The full quality gate and independent shipping review remain required. Tier 3 is
recorded, not a push gate. No scientific requirement changes in this brief.
