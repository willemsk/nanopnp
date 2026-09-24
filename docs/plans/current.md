# Current work

Updated 24 September 2026. Navigation only: `SPECIFICATION.md` governs. Check the
requested branch and its WP status before resuming; this brief is not evidence that
an unmerged branch has shipped.

## Position

- Phase 1 ([solver core](phase-1-solver-core.md)) is **closed**: WP7–WP16, and the end-of-phase
  report, released as `v0.5.0` under `SPECIFICATION.md` §8.2.3. The COMSOL attribution is
  outstanding on the author's exports (C1), and so is the 12-core reference sweep (C2). Each lands
  as an addendum to that report.
- Phase 2 ([geometry pipeline](phase-2-geometry-pipeline.md)) is **planned, not started**:
  WP17–WP25, with the author's rulings B1–B7 recorded in `SPECIFICATION.md` §8.2.2.
- **WP17** ([case schema v2 and the 3.11 floor](wp17-case-schema-v2.md)) is **in progress** on
  `claude/wp-plan-17-211905`. Ruling B1 is met: the author's double-click was recorded on
  24 September 2026 (the NOTE to `SPECIFICATION.md` §8.2.1), closing Phase 0 criterion 4 and
  retiring RSK-13. Its first commit freezes the v1 case corpus and its solve keys **on unchanged
  code**, before any schema edit (WP17 D7).

## What Phase 2 must not re-decide

Each item is recorded in full where it points. Read it there first.

- **The schema moves once**, to `nanopnp/case/v2` in WP17, with the key set of the §5.3.1 v2 NOTE.
  A later need widens an existing key's value set, and does not add a key. → §8.2.2 B3; WP17 D1.
- **`physics.solid_permittivities` is the only place ε_protein and ε_membrane are set**, and contour
  tuning parameters and gate thresholds are never case keys (author rulings, 24 September 2026).
  → WP17 D2, D3.
- **Python 3.11–3.14.** QR-09 is amended; `pyproject.toml`, the CI matrix and the IF-05 NOTE follow
  in WP17. → §8.2.2 B4.
- **VAL-05 has two legs**: vendored 2WCD, gated at Tier 2; the author's ensemble, Tier 3, which the
  phase gate requires. → §8.2.2 B2; §7.4.
- **No HOLE on the default path**: the radius profile is an in-project probe-radius profile.
  → §8.2.2 B5; §5.2.1.
- **The contour script is read before WP20 is planned.** → §8.2.2 B6; OPN-02; RSK-06.
- **Gmsh arrives in WP23, optional; FR-20 is Phase 3's.** → §8.2.2 B7.
- **Stage 4 emits `nanopnp/profile/v1`** and stage 3 fills `RadialGrid`: the existing schemas.
  → phase plan, Design decisions.

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

- **The G9 axial offset** and the **ensemble archive** (format, frames, lipids) for VAL-05. The
  author's, before WP22.
- **The COMSOL exports** (WP13), against
  [`docs/validation/comsol-export-contract.md`](../validation/comsol-export-contract.md). Until they
  land every report carries `golden_source: self`, and Tier 3 skips the archive comparison visibly.
  This also covers the two declarations only the author can make: which boundary `tds.ntflux_i` was
  evaluated on, and which electrode the exported current references.
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

Their own Outcomes later corrected some decision-table claims, so don't read these as current:
WP13's telescoping identity catching a stale golden, and its per-field export; WP15's D1 `rung`
signature, D3's single reason for a silent rung, D6's knowable closing test, and D13's CDN.

## Handoff Rules

Replace this brief's current position and live dependencies when planning or
finishing a package; do not append a delivery diary. Target at most 800 words.
Keep measurements and derivations in their owning records, and preserve existing
historical sections there. Load those sections only when a decision, implementation
or review needs their evidence.

The full quality gate and independent shipping review remain required. Tier 3 is
recorded, not a push gate. No scientific requirement changes in this brief.
