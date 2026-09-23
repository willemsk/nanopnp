# Current work

Updated 23 September 2026. Navigation only: `SPECIFICATION.md` governs. Check the
requested branch and its WP status before resuming; this brief is not evidence that
an unmerged branch has shipped.

## Position

- Phase: [Phase 1, solver core](phase-1-solver-core.md).
- Delivered: **WP7–WP16**. WP16 opened §8.1's documentation track:
  [`wp16-user-docs-and-examples.md`](wp16-user-docs-and-examples.md).
- **Next: the end-of-phase report** of `SPECIFICATION.md` §8.1 and the phase plan's §Verification
  and §End-of-phase report, then planning Phase 2. No work package is planned.
- **IF-09 is complete and QR-11 discharged** by WP14 and WP15 together:
  [`wp15-live-convergence-and-viewer.md`](wp15-live-convergence-and-viewer.md).

## What WP15 and WP16 established that later work must not re-decide

Each is recorded in full where it points; read it there first.

- **Two silences.** A rung reports no Newton step either because its model takes no callback or
  because it converged on entry, and the hook carries which it was. → VER-44;
  `.knowledge/06-numerics-fem.md` §5.1.
- **A callback is not an input**: a watched run keys the same artefact as an unwatched one.
  → `tests/tier1/test_solve_hook.py`.
- **The renderer ships with the package**, byte-identical to the npm tarball in `third_party/`.
  → `test_ver44_vendored_renderer_matches_npm_integrity`.
- **A bundle needs OCCT and OpenBLAS collected explicitly.** → `.knowledge/07-software-stack.md` §5.
- **Every phase documents what it ships** (§8.1 track, the QR-15 NOTE). A documented command is
  executed by VER-46, verbatim, through `nanopnp.validation.examples`. No number appears in the
  docs as a result unless a test asserts it. The model pages are the specification and
  `.knowledge/` rendered verbatim, never restated. → WP16 D4, D8, D9.
- **The public API is `nanopnp.PUBLIC`**, twenty lazily resolved names; adding one is a decision
  made in `tests/tier1/test_public_api.py`. → the IF-01 NOTE.
- **Generated references are rendered at build time, never committed**: `nanopnp.cli.reference`
  and `docs/scripts/generate.py`. A new case field, flag or exit class appears without a docs edit.
- **Material for MkDocs is in maintenance mode**: `mkdocs<2`, no build hooks, and a Zensical
  migration when it supports cross-references (`.knowledge/07-software-stack.md` §13).
- **A generated mesh maps only NGSolve's `default` seam**; the reference geometry maps nothing.
  A case written against it uses `groups: {}`. → WP16 D7's Outcome.

## What is still somebody else's

- **The Read the Docs project**: the author creates it (slug `nanopnp`) and connects the
  repository; `.readthedocs.yaml` is in place and CI's `docs` job builds the same site.
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
| Documentation: site, examples, their executor | `mkdocs.yml`; `docs/scripts/`; `examples/`; `src/nanopnp/validation/examples.py`; `src/nanopnp/cli/reference.py` |
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
