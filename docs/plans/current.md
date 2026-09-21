# Current work

Updated 21 September 2026. Navigation only: `SPECIFICATION.md` governs. Check the
requested branch and its WP status before resuming; this brief is not evidence that
an unmerged branch has shipped.

## Position

- Phase: [Phase 1, solver core](phase-1-solver-core.md).
- Delivered: **WP7–WP15**. Phase 1 has no further planned package; the next step is the
  end-of-phase report of `SPECIFICATION.md` §8.1 and the phase plan's §Verification, then
  planning Phase 2.
- WP15's record: [`wp15-live-convergence-and-viewer.md`](wp15-live-convergence-and-viewer.md).
  **QR-11 is discharged by WP14 and WP15 together**, and IF-09 is complete: the shell now has
  five panels over one run — the schema-generated case editor, run control over a spawned solver
  process, the live convergence plot, the result panel and the `webgui` field viewer.
- Tier 3 is recorded, not gated, and stays that way. WP13 delivered its harness; see
  [`wp13-tier3-comsol-comparison.md`](wp13-tier3-comsol-comparison.md).

## What WP15 established that later work must not re-decide

- **A rung reports no Newton step for two unrelated reasons.** On the reference ladder, two rungs
  of twelve take no damped-Newton callback (their models are not `CoupledModel`) and three more are
  coupled rungs that converged *on entry*, `damped_newton` returning before its first step. The
  silence is identical from outside, so `SolveHook.rung` carries `reporting` from the same test
  that injects the callback. Annotating a warm-started rung "not a Newton solve" is false.
  → `.knowledge/06-numerics-fem.md` §5.1 **[tested]**; VER-44.
- **Which NUM-16 test closed a rung is not knowable, only the exclusion is.** The two tests are not
  exclusive and the residual test short-circuits. A forced last step, or a last relative update
  above the rung's own tolerance, each leave the residual test as the only candidate; otherwise the
  update test is reported as met without claiming the residual test was not. → VER-44.
- **A callback is not an input.** `io/run.py` rebinds the solve stage *after* its artefact key has
  been taken, delivered by the `SolveReporting` capability so eleven stages gain no keyword. A run
  watched from the shell keys the artefact a command-line run keys, asserted on the hash *and* on
  the store's hit counter. → `tests/tier1/test_solve_hook.py`.
- **`NewtonResult.summary()` must stay free of per-iteration data.** It reaches the stage-10
  artefact's summary, which is inside the §5.3.2 content hash; a series there would make every
  solve its own cache entry and move the hash of every run in every store.
- **The scene is a display artefact.** `viewer/` inside the run directory is never registered and
  never hashed, and one field's pair is kept at a time: at reference mesh size a scene is 23–39 MB
  and it is written twice — once as data, once embedded in the host document. → WP15 D9's Outcome.

## What is still somebody else's

- **OQ-1, the renderer's redistribution.** `ngsolve.webgui`'s document fetches an
  LGPL-2.1-or-later renderer from `cdn.jsdelivr.net`. Shipping it as package data is what makes a
  double-clicked bundle draw a field with no network; it is a CON-09 amendment and the author's
  call. Until then the viewer's readiness probe reports a document that loaded without its
  renderer as a diagnostic naming the source. It is one constant, `gui/render.renderer_source()`,
  plus WP15 work item 15 — and it could not have been implemented here regardless: the CDN answers
  this container's proxy with 403.
- **The double-click.** The gated `windows-latest` `bundle` job builds the one-dir bundle, runs
  `--selftest` and uploads it on every push. Only the author can observe that it double-clicks;
  until that is recorded, **§8.2 criterion 4 stays outstanding and RSK-13 stays open**, exactly as
  amendment A4 leaves them.
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

Two claims in the WP13 plan's decision table are corrected by its own Outcomes and must
not be read as current: the telescoping identity does **not** catch a rung compared
against a stale golden (the hash and point-count gates do), and the export is one table
per field **per patch**, not per field. Three in the WP15 plan's are corrected by its
Outcomes: D1's `rung` signature, D3's single reason for a silent rung, and D6's claim that
the closing test is knowable.

## Handoff Rules

Replace this brief's current position and live dependencies when planning or
finishing a package; do not append a delivery diary. Target at most 800 words.
Keep measurements and derivations in their owning records, and preserve existing
historical sections there. Load those sections only when a decision, implementation
or review needs their evidence.

The full quality gate and independent shipping review remain required. Tier 3 is
recorded, not a push gate. No scientific requirement changes in this brief.
