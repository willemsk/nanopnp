# Current work

Updated 20 September 2026. Navigation only: `SPECIFICATION.md` governs. Check the
requested branch and its WP status before resuming; this brief is not evidence that
an unmerged branch has shipped.

## Position

- Phase: [Phase 1, solver core](phase-1-solver-core.md).
- Delivered: WP7–WP14. Next: **WP15, the live convergence plot and the `webgui` field
  viewer** — scoped in the phase plan, not yet planned. WP14's record:
  [`wp14-gui-shell-packaging-probe.md`](wp14-gui-shell-packaging-probe.md).
- **QR-11 is discharged by WP14 and WP15 together.** WP14 delivered the packaging probe,
  the schema-generated case editor, run control over a spawned solver process and the
  result panel. WP15 adds the structural `NewtonStep` hook, the plot fed from it, and a
  field viewer bound to a real solution.
- Tier 3 is recorded, not gated, and stays that way. WP13 delivered its harness; see
  [`wp13-tier3-comsol-comparison.md`](wp13-tier3-comsol-comparison.md).

## Live constraints on WP15

- **Qt cannot be constructed in the development container.** `from PySide6 import QtWidgets`
  raises `ImportError: libEGL.so.1` (PySide6 6.11.2) — `QtWidgets`, not only WebEngine. So
  `gui/case_model.py`, `gui/run_model.py` and `gui/solver.py` import no PySide6, asserted on
  `sys.modules` in a fresh process, and the convergence and viewer models must do the same.
  Widget construction is exercised on the `windows-latest` and `macos-latest` matrix jobs under
  `QT_QPA_PLATFORM=offscreen` and skips on `(ImportError, OSError)` elsewhere. The push gate
  installs no system packages. A local `LD_LIBRARY_PATH` shim exists for developer use only
  (`.knowledge/07` §5).
- **The residual reaches the caller only inside a `:.3e` string.** `SolveStage._instrumented`
  formats it into a progress message; a plot's subject is six or more orders of magnitude of it.
  WP15 adds a structural hook forwarding the `NewtonStep` and **must not** parse the message.
  `gui/solver.py`'s `RunEvent` union is where the variant joins, beside `Stage`; the `StageHook`
  WP14 added to `run_document` is the pattern to copy.
- **`on_step` is injected only for a `CoupledModel` rung**, so the electrostatic rungs of the
  NUM-18 ladder emit no steps and a plot assuming a continuous stream would show an unexplained
  gap. `on_rung` is the per-rung hook beside it.
- **The bundle is distributed under GPL-2+** (CON-11: UMFPACK ships inside the NGSolve wheel and
  is the bundle default), while the library stays BSD-3. `packaging/LICENSES-BUNDLE.md` says so
  and `nanopnp-probe --selftest` fails if it did not travel with the bundle.
- **`ngsolve.webgui` wants a live `GridFunction`**, which lives in the *run* process; the IF-07
  XDMF export WP10 writes is a P2 node set for a reader, not a scene. Which the viewer consumes
  is WP15's decision. Its HTML also fetches the renderer from a CDN, so `loadFinished` says the
  document loaded, never that the picture drew.

## What is still somebody else's

- **The double-click.** The gated `windows-latest` `bundle` job builds the one-dir bundle and
  runs `--selftest` on every push, and uploads it. Only the author can observe that it
  double-clicks; until that is recorded, **§8.2 criterion 4 stays outstanding and RSK-13 stays
  open**, exactly as amendment A4 leaves them.
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
| What WP15 must build and the two facts it designs around | `phase-1-solver-core.md` §WP15; `wp14-gui-shell-packaging-probe.md` §Design 2 and its Outcomes |
| The shell as delivered | `src/nanopnp/gui/` — `case_model.py`, `run_model.py`, `solver.py`, `widgets/`, `app.py`, `probe.py` |
| The FR-27 plumbing and the stage hook | `src/nanopnp/core/stages.py` (`Progress`, `CancelToken`, `StageHook`); `io/run.py`'s `run_case`; `solve/stage.py`'s `_instrumented` |
| The case schema, its dotted paths and its option sets | `SPECIFICATION.md` §5.3.1 and its NOTEs; `src/nanopnp/io/case.py` (`case_fields`, `field_at`, `options_at`, `registry_options`, `substitute`, `render_problems`) |
| Shell, packaging and licence constraints | `SPECIFICATION.md` ADR-004, CON-07, CON-09, CON-11, CON-13, §8.2 criterion 4, §8.2.1 A4; `.knowledge/07-software-stack.md` §5–§6 |
| What Tier 3 is and how to drive it | `wp13-tier3-comsol-comparison.md`; `docs/validation/comsol-export-contract.md`; `nanopnp validate --help` |
| Stabilisation findings inherited from WP12 | `wp12-reference-stabilised-mode.md` Outcomes in Design 3 and 4 |
| Reference geometry, field inputs, runs and sweeps | Phase plan: WP8, WP9, WP10, WP11; `docs/sweeps/README.md` |
| Reference settings and equations | `.knowledge/00-index.md`, then 01, 06, 08 and 09; the specification remains normative |

Two claims in the WP13 plan's decision table are corrected by its own Outcomes and must
not be read as current: the telescoping identity does **not** catch a rung compared
against a stale golden (the hash and point-count gates do), and the export is one table
per field **per patch**, not per field.

## Handoff Rules

Replace this brief's current position and live dependencies when planning or
finishing a package; do not append a delivery diary. Target at most 800 words.
Keep measurements and derivations in their owning records, and preserve existing
historical sections there. Load those sections only when a decision, implementation
or review needs their evidence.

The full quality gate and independent shipping review remain required. Tier 3 is
recorded, not a push gate. No scientific requirement changes in this brief.
