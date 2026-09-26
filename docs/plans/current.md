# Current work

Updated 26 September 2026. Navigation only: `SPECIFICATION.md` governs. This brief is not
evidence that an unmerged branch has shipped.

## Position

- Phase 1 ([solver core](phase-1-solver-core.md)) is **closed** as `v0.5.0` (§8.2.3); C1 and C2
  land as addenda to its report.
- Phase 2 ([geometry pipeline](phase-2-geometry-pipeline.md)) is **in progress**. WP17 to WP20
  are merged (PRs [#38](https://github.com/willemsk/nanopnp/pull/38) to
  [#41](https://github.com/willemsk/nanopnp/pull/41), `v0.9.0-alpha.1` to `alpha.4`). WP22–WP25
  are planned in the phase plan (rulings B1–B7, §8.2.2).
- **WP21** ([stages 5 and 6, CAD assembly and meshing](wp21-cad-assembly-and-meshing.md)) is
  **delivered** on `claude/wp-plan-21-eea388`, awaiting `/wp-ship`. It becomes `v0.9.0-alpha.5`.
- **Next: WP22**, VAL-05 against the reference geometry (phase plan §WP22), after WP21 merges.

## What Phase 2 must not re-decide

Each item is recorded in full where it points. Read it there first.

- **The schema moved once**, to `nanopnp/case/v2` (WP17). A later need widens an existing key's
  value set, and does not add a key. → §8.2.2 B3; WP17 D1.
- **`inputs.pqr` is accepted and refused** through `_UNCONSUMED_INPUTS` in `io/case.py` until
  Phase 3 consumes it. `inputs.profile` is stage 5's.
- **`physics.solid_permittivities` alone sets ε_protein and ε_membrane**; gate thresholds are never
  case keys. → WP17 D2, D3.
- **Python 3.11–3.14**, held together by VER-47. → §8.2.2 B4.
- **VAL-05 has two legs**: vendored 2WCD, gated at Tier 2; the author's ensemble, Tier 3, which the
  phase gate requires. → §8.2.2 B2; §7.4.
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
- **2WCD's axial registration is WP22's.** WP21's Tier-2 walk registers it at the *trans* tip
  plus 1.85 nm, a test choice and not a VAL-05 claim. → WP21 Outcomes.
- **Open for WP22, from the author:** the reference polygon's binning and hand edit. → WP20 Open
  questions.
- **The density's radii are CHARMM Rmin/2**, with no element fallback; **the Cₙ average is a
  harmonic projection**. → the §5.3.1 NOTE on `geometry.density`; WP19 D3, D7, D9.
- **For VAL-05 (WP22), answered by the author:** G9 is 0 in the MD frame, the paper's 50 frames
  are DCD frames 48–97, and the density included hydrogens. → `.knowledge/04` §1.1, §8.
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
