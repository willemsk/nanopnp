# Current work

Updated 23 September 2026. Navigation only: `SPECIFICATION.md` governs. Check the
requested branch and its WP status before resuming; this brief is not evidence that
an unmerged branch has shipped.

## Position

- Phase: [Phase 1, solver core](phase-1-solver-core.md).
- Delivered: **WP7–WP15**. **Planned, not started: WP16**, user documentation and worked
  examples: [`wp16-user-docs-and-examples.md`](wp16-user-docs-and-examples.md). After WP16 come
  the end-of-phase report of `SPECIFICATION.md` §8.1 and the phase plan's §Verification, and then
  planning Phase 2.
- WP16 opens §8.1's **documentation track**. From here on, every phase documents what it ships,
  and its examples are executed by VER-46. Amended: §8.1, the QR-15, IF-01 and IF-02 NOTEs.
- **IF-09 is complete and QR-11 discharged** by WP14 and WP15 together:
  [`wp15-live-convergence-and-viewer.md`](wp15-live-convergence-and-viewer.md).
- Tier 3 is recorded, not gated, and stays that way. WP13 delivered its harness; see
  [`wp13-tier3-comsol-comparison.md`](wp13-tier3-comsol-comparison.md).

## What WP15 established that later work must not re-decide

Each is recorded in full where it points; read it there first.

- **Two silences.** A rung reports no Newton step either because its model takes no callback or
  because it converged on entry, and the hook carries which it was. Only the *exclusion* of a
  NUM-16 test is knowable. → VER-44; `.knowledge/06-numerics-fem.md` §5.1.
- **A callback is not an input.** A watched run keys the same artefact as an unwatched one, and
  `NewtonResult.summary()` stays free of per-iteration data, because it is inside the §5.3.2 hash.
  → `tests/tier1/test_solve_hook.py`.
- **The scene is a display artefact**: never registered and never hashed. → WP15 D9's Outcome.
- **The renderer ships with the package** (OQ-1, CON-09 amended), byte-identical to the npm
  tarball in `third_party/`; an NGSolve upgrade that moves the pin fails the gate.
  → `test_ver44_vendored_renderer_matches_npm_integrity`.
- **A bundle needs OCCT and OpenBLAS collected explicitly.** → `.knowledge/07-software-stack.md` §5.

## What WP16 must hold to

- **No number in the docs that no test asserts**, and **no restated equation**: the model pages
  are `SPECIFICATION.md` and `.knowledge/` rendered verbatim (WP16 D4, D9).
- **`import nanopnp` stays solver-free**: the public surface is lazy (the IF-01 NOTE, VER-45).
- **Material for MkDocs is in maintenance mode**: pin `mkdocs<2`, keep `mkdocs.yml`
  Zensical-readable, and use no build hooks (`.knowledge/07-software-stack.md` §13).

## What is still somebody else's

- **The Read the Docs project** (WP16): the author creates it and connects the repository.
- **The double-click.** The gated `windows-latest` `bundle` job builds the one-dir bundle, runs
  `--selftest` and uploads it on every push. Its selftest now also fails when the shipped renderer
  does not reach its page. Only the author can observe that it double-clicks and draws; until that
  is recorded, **§8.2 criterion 4 stays outstanding and RSK-13 stays open**, as amendment A4 leaves
  them.
- **The COMSOL exports do not exist yet** (WP13). The author's, against
  [`docs/validation/comsol-export-contract.md`](../validation/comsol-export-contract.md).
  Until they land every report carries `golden_source: self`, and
  `tests/tier3/test_comsol_comparison.py` skips the archive comparison visibly.
- **Two declarations only the author can make**: which boundary `tds.ntflux_i` was evaluated on,
  and which electrode the exported current references.
- **`$NANOPNP_REFERENCE_DATA` on the nightly runner** is still open.

## Dependencies To Read On Demand

| Need | Read |
|---|---|
| What Phase 1 owes its end-of-phase report | `phase-1-solver-core.md` §Verification and §End-of-phase report; `SPECIFICATION.md` §8.1, §8.2 |
| The shell as delivered | `src/nanopnp/gui/` — `case_model.py`, `run_model.py`, `solver.py`, `convergence.py`, `scene.py`, `render.py`, `widgets/`, `app.py`, `probe.py` |
| The solve hook and the FR-27 plumbing | `src/nanopnp/core/stages.py` (`Progress`, `CancelToken`, `StageHook`, `SolveHook`, `SolveReporting`); `io/run.py`'s `run_case` and `_resolve_stage`; `solve/stage.py`'s `_instrumented` and `with_solve_hook` |
| The case schema, its dotted paths and its option sets | `SPECIFICATION.md` §5.3.1 and its NOTEs; `src/nanopnp/io/case.py` (`case_fields`, `field_at`, `options_at`, `registry_options`, `substitute`, `render_problems`) |
| Shell, packaging and licence constraints | `SPECIFICATION.md` ADR-004, CON-07, CON-09, CON-11, CON-13, §8.2 criterion 4, §8.2.1 A4; `.knowledge/07-software-stack.md` §5–§6 |
| What Tier 3 is and how to drive it | `wp13-tier3-comsol-comparison.md`; `docs/validation/comsol-export-contract.md`; `nanopnp validate --help` |
| Stabilisation findings inherited from WP12 | `wp12-reference-stabilised-mode.md` Outcomes in Design 3 and 4 |
| Reference geometry, field inputs, runs and sweeps | Phase plan: WP8, WP9, WP10, WP11; `docs/sweeps/README.md` |
| Reference settings and equations | `.knowledge/00-index.md`, then 01, 06, 08 and 09; the specification remains normative |

Decision-table claims corrected by their own Outcomes, not to be read as current: WP13's
telescoping identity catching a stale golden, and its per-field export; WP15's D1 `rung`
signature, D3's single reason for a silent rung, D6's knowable closing test, and D13's CDN.

## Handoff Rules

Replace this brief's current position and live dependencies when planning or
finishing a package; do not append a delivery diary. Target at most 800 words.
Keep measurements and derivations in their owning records, and preserve existing
historical sections there. Load those sections only when a decision, implementation
or review needs their evidence.

The full quality gate and independent shipping review remain required. Tier 3 is
recorded, not a push gate. No scientific requirement changes in this brief.
