# Current work

Updated 25 September 2026. Navigation only: `SPECIFICATION.md` governs. Check the
requested branch and its WP status before resuming; this brief is not evidence that
an unmerged branch has shipped.

## Position

- Phase 1 ([solver core](phase-1-solver-core.md)) is **closed** as `v0.5.0` (§8.2.3). The COMSOL
  attribution (C1) and the 12-core reference sweep (C2) land as addenda to its report.
- Phase 2 ([geometry pipeline](phase-2-geometry-pipeline.md)) is **in progress**: WP17 is
  merged (PR [#38](https://github.com/willemsk/nanopnp/pull/38), `v0.9.0-alpha.1`), WP18 is
  delivered on its branch, and WP19–WP25 are planned (rulings B1–B7, §8.2.2).
- **WP18** ([structure ingestion, stage 1](wp18-structure-ingestion.md)) is **delivered** on
  `claude/wp-plan-18-2f2174`, with its PR open and independent review pending. **Next:**
  `/wp-ship` in a fresh session; after merge, tag `v0.9.0-alpha.2`; then `/wp-plan 19`.

## What Phase 2 must not re-decide

Each item is recorded in full where it points. Read it there first.

- **The schema moved once**, to `nanopnp/case/v2` in WP17, with the key set of the §5.3.1 v2 NOTE.
  A later need widens an existing key's value set, and does not add a key. The schema string no
  longer keys a solve. → §8.2.2 B3; WP17 D1; the §5.3.2 NOTE.
- **`inputs.profile` and `inputs.pqr` are accepted and refused** through `_UNCONSUMED_INPUTS` in
  `io/case.py`. The package that delivers the consuming stage removes the entry (WP21, Phase 3).
- **`physics.solid_permittivities` is the only place ε_protein and ε_membrane are set**, and contour
  tuning parameters and gate thresholds are never case keys (author rulings, 24 September 2026).
  → WP17 D2, D3.
- **Python 3.11–3.14**, held together by VER-47. → §8.2.2 B4.
- **VAL-05 has two legs**: vendored 2WCD, gated at Tier 2; the author's ensemble, Tier 3, which the
  phase gate requires. → §8.2.2 B2; §7.4.
- **No HOLE on the default path** (B5). **The contour script is read before WP20 is planned**
  (B6). **Gmsh arrives in WP23, optional, and FR-20 is Phase 3's** (B7). → §8.2.2.
- **Stage 4 emits `nanopnp/profile/v1`** and stage 3 fills `RadialGrid`: the existing schemas.
  → phase plan, Design decisions.
- **Stage 1's frame is fixed.** The axis is on z at r = 0, and `z = â·x` keeps the file's axial
  coordinate. +z is the file's +z, which must point to *cis*. Stage 5 applies `centre_z_nm`. The
  van der Waals radius belongs to stage 2. mmCIF is read by gemmi. → the §5.3.1 NOTE on
  `structure:`; WP18 D2, D8, D10.
- **`refuse_walk`** (`io/case.py`) stops runs and sweeps past the last delivered stage; WP19
  extends it. → WP18 D1.
- **The vendored 2WCD is in its crystal frame**, 22.9° from z, and stage 1 refuses it; WP22's
  Tier-2 leg must orient it, as the stage-one test does. → WP18 D16 Outcome.

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

- **The G9 axial offset**, and **the ensemble's frame spacing and the paper's 50 frames**, for
  VAL-05. They are the author's, before WP22. The archive is `prod5_clya_as.{pdb,dcd}`: 98 frames,
  protein only, with no time metadata. The MD frame suggests G9 ≈ 0 (`.knowledge/04` §1.1).
- **The van der Waals radius set** of the original density map. The author's, before WP19; the
  contour script may carry it (B6).
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
| The seams Phase 2 builds on | `density/grid.py` (`RadialGrid`); `mesh/profile.py`; `mesh/reference.py` (`ReferenceGeometry`); `core/stages.py`; `io/run.py`; `io/case.py` (`_require_runnable`) |
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
