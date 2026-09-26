# Current work

Updated 26 September 2026. Navigation only: `SPECIFICATION.md` governs. Check the
requested branch and its WP status before resuming; this brief is not evidence that
an unmerged branch has shipped.

## Position

- Phase 1 ([solver core](phase-1-solver-core.md)) is **closed** as `v0.5.0` (§8.2.3). The COMSOL
  attribution (C1) and the 12-core reference sweep (C2) land as addenda to its report.
- Phase 2 ([geometry pipeline](phase-2-geometry-pipeline.md)) is **in progress**. WP17, WP18
  and WP19 are merged (PRs [#38](https://github.com/willemsk/nanopnp/pull/38),
  [#39](https://github.com/willemsk/nanopnp/pull/39) and
  [#40](https://github.com/willemsk/nanopnp/pull/40), `v0.9.0-alpha.1` to `alpha.3`). WP21–WP25
  are planned (rulings B1–B7, §8.2.2).
- **WP20** ([stage 4, the contour](wp20-contour-extraction.md)) is **delivered** on
  `claude/wp-plan-20-e8e1e9`. Its PR awaits `/wp-ship` and becomes `v0.9.0-alpha.4`.
- **WP21** (stages 5 and 6, CAD assembly and meshing from a profile) is **next** for `/wp-plan`,
  once WP20 has merged.

## What Phase 2 must not re-decide

Each item is recorded in full where it points. Read it there first.

- **The schema moved once**, to `nanopnp/case/v2` in WP17, with the key set of the §5.3.1 v2 NOTE.
  A later need widens an existing key's value set, and does not add a key. The schema string no
  longer keys a solve. → §8.2.2 B3; WP17 D1; the §5.3.2 NOTE.
- **`inputs.profile` and `inputs.pqr` are accepted and refused** through `_UNCONSUMED_INPUTS` in
  `io/case.py` until their consumer lands (WP21, Phase 3).
- **`physics.solid_permittivities` is the only place ε_protein and ε_membrane are set**, and contour
  tuning parameters and gate thresholds are never case keys (author rulings, 24 September 2026).
  → WP17 D2, D3.
- **Python 3.11–3.14**, held together by VER-47. → §8.2.2 B4.
- **VAL-05 has two legs**: vendored 2WCD, gated at Tier 2; the author's ensemble, Tier 3, which the
  phase gate requires. → §8.2.2 B2; §7.4.
- **No HOLE on the default path** (B5). **The contour script has been read** (B6; WP20 D2).
  **Gmsh arrives in WP23, optional, and FR-20 is Phase 3's** (B7). → §8.2.2.
- **Stage 4 emits `nanopnp/profile/v1` in the stage-1 frame**, `source: pipeline`, the document
  `inputs.profile` reads. Its size target is h, not the stage-6 wall size; its region is closed and
  opened by 2h; its band is `[−h, +1.5 nm]` against the probe radius. It guarantees spacing ≥ h
  and feature size > 2h. → §5.2.1 and its NOTEs; WP20 D5, D9–D12 and the handoff to WP21.
- **Stage 1's frame is fixed**: axis on z at r = 0, `z = â·x`, +z to *cis*; stage 5 applies
  `centre_z_nm`. → the §5.3.1 NOTE on `structure:`; WP18 D2, D8, D10.
- **`refuse_walk`** (`io/case.py`) stops runs and sweeps past stage 4, naming stage 5. WP21
  moves it on and lifts `_require_runnable`'s mesh refusal. → WP18 D1; WP19 D1; WP20 D1.
- **Open for WP22, from the author:** did the reference polygon use `pqr2grid`'s binning, and
  what did its hand edit do? → WP20 Open questions; Design §7.
- **The density's radii are CHARMM Rmin/2** by residue and atom, with no element fallback
  (author ruling, 25 September 2026); the probe profile uses the same set. **The Cₙ average is a
  harmonic projection**; below `n h/π` the variance is unresolved, not zero. → the §5.3.1 NOTE on
  `geometry.density`; WP19 D3, D7, D9.
- **For VAL-05 (WP22), answered by the author:** G9 is 0 in the MD frame, the paper's 50 frames
  are DCD frames 48–97, and the density included hydrogens. → `.knowledge/04` §1.1, §8.
- **The vendored 2WCD is in its crystal frame** and stage 1 refuses it; the tests orient it through
  the `prepared_2wcd` fixture in `tests/conftest.py`. → WP18 D16 Outcome; WP19 D14.

## Inherited from Phase 1, still binding

- **A callback is not an input**; a watched run keys the same artefact. → VER-44.
- **The public API is `nanopnp.PUBLIC`**; adding a name is a decision in
  `tests/tier1/test_public_api.py`. → the IF-01 NOTE.
- **Every phase documents what it ships**; documented commands run verbatim under VER-46, and no
  number appears as a result unless a test asserts it. → WP16 D4, D8, D9.
- **Generated references are rendered at build time, never committed.**
- **A generated mesh maps only NGSolve's `default` seam**; the reference geometry maps nothing.
  → WP16 D7's Outcome.

## What is still somebody else's

- **The COMSOL exports** (WP13), against
  [`docs/validation/comsol-export-contract.md`](../validation/comsol-export-contract.md). Until they
  land every report carries `golden_source: self`, and Tier 3 skips the archive comparison visibly.
  They include the `tds.ntflux_i` boundary and the current's reference electrode.
- **The Read the Docs project** (slug `nanopnp`) and **`$NANOPNP_REFERENCE_DATA` on the nightly
  runner**.

## Dependencies To Read On Demand

| Need | Read |
|---|---|
| What Phase 1 owes its report | `phase-1-solver-core.md` §Verification, §End-of-phase report; `SPECIFICATION.md` §8.1, §8.2 |
| Phase 2 scope and rulings | `phase-2-geometry-pipeline.md`; `SPECIFICATION.md` §5.2–§5.2.2, §8.2.2 |
| The ClyA pipeline as executed, and gaps G1–G13 | `.knowledge/04-clya-geometry-and-charge.md` |
| Structure, geometry and meshing libraries | `.knowledge/07-software-stack.md` §2, §4, §8 |
| The seams Phase 2 builds on | `geometry/contour.py` (`ContourStage`, the gate); `geometry/probe.py`; `mesh/profile.py` (`PoreProfile`, `write_profile`, `feature_sizes`); `mesh/reference.py` (`ReferenceGeometry`, `plane_crossings`); `symmetry/reduce.py` (`ReducedMap`); `core/stages.py`; `io/run.py`; `io/case.py` (`_require_runnable`, `refuse_walk`) |
| Case schema, dotted paths and option sets | `SPECIFICATION.md` §5.3.1 and its NOTEs; `io/case.py` |
| Shell, packaging and licence constraints | ADR-004, CON-07, CON-09, CON-10, CON-11; `.knowledge/07-software-stack.md` §5–§6 |

A delivered plan's Outcomes override its decisions table; read them together (WP13 and WP15
especially).

## Handoff Rules

Replace this brief's current position and live dependencies when planning or
finishing a package; do not append a delivery diary. Target at most 800 words.
Keep measurements and derivations in their owning records, and preserve existing
historical sections there. Load those sections only when a decision, implementation
or review needs their evidence.

The full quality gate and independent shipping review remain required. Tier 3 is
recorded, not a push gate. No scientific requirement changes in this brief.
