# Current work

Updated 20 September 2026. Navigation only: `SPECIFICATION.md` governs. Check the
requested branch and its WP status before resuming; this brief is not evidence that
an unmerged branch has shipped.

## Position

- Phase: [Phase 1, solver core](phase-1-solver-core.md).
- Delivered: WP7–WP13. Current: **WP14, the packaging probe and the desktop shell** —
  planned, not started. Plan: [`wp14-gui-shell-packaging-probe.md`](wp14-gui-shell-packaging-probe.md).
- **The §8.1 GUI increment is now two packages.** WP14 is the packaging probe, the
  schema-generated case editor and run control; **WP15** is the live convergence plot
  and the `webgui` field viewer. The cut is where the data changes: run control needs
  only the `(fraction, message)` the `Progress` protocol already carries, a convergence
  plot needs the `NewtonStep` record, and no hook forwards it yet. QR-11 is discharged
  by the two together, inside Phase 1.
- Three decisions closed on 20 September 2026 and written into the specification in the
  WP14 plan's commit: the shell is **PySide6 native** (ADR-004's local-web-app
  alternative is rejected), the packaging tool is **PyInstaller, one-dir**, and the
  Windows bundle is built by a **gated `windows-latest` CI job on every push**, with the
  author's double-click closing §8.2 criterion 4 (§8.2.1 amendment A4).
- Tier 3 is recorded, not gated, and stays that way. WP13 delivered its harness; see
  [`wp13-tier3-comsol-comparison.md`](wp13-tier3-comsol-comparison.md).

## Live constraints on WP14

- **Qt cannot be constructed in the development container.** Measured 20 September 2026:
  `from PySide6 import QtWidgets` raises `ImportError: libEGL.so.1` (PySide6 6.11.2) —
  `QtWidgets`, not only WebEngine. The Tier-1 GUI suite therefore imports no PySide6;
  widget construction is exercised on the existing `windows-latest` and `macos-latest`
  matrix jobs under `QT_QPA_PLATFORM=offscreen`, and skips on `(ImportError, OSError)`
  elsewhere. The push gate installs no system packages.
- **`import nanopnp.io.case` costs 622 ms and imports neither `ngsolve` nor `numpy`.**
  So the editor enumerates and validates the whole schema without the solver; NGSolve is
  imported in the spawned run process, on the far side of the boundary.
- **The bundle is distributed under GPL-2+** (CON-11: UMFPACK ships inside the NGSolve
  wheel and is the bundle default), while the library stays BSD-3. The notice ships with
  the first bundle, not later.

## What is still somebody else's

- **The COMSOL exports do not exist yet** (WP13). The author's, against
  [`docs/validation/comsol-export-contract.md`](../validation/comsol-export-contract.md).
  Until they land every report carries `golden_source: self`, and
  `tests/tier3/test_comsol_comparison.py` skips the archive comparison visibly.
- **Two declarations only the author can make**: which boundary `tds.ntflux_i` was
  evaluated on, and which electrode the exported current references.
- **`$NANOPNP_REFERENCE_DATA` on the nightly runner** is still open.
- **The double-click.** Only the author can observe it; until it is recorded, §8.2
  criterion 4 stays outstanding and RSK-13 stays open.

## Dependencies To Read On Demand

| Need | Read |
|---|---|
| What WP14 builds and why each choice was made | `wp14-gui-shell-packaging-probe.md`, Decisions and §Design |
| The FR-27 plumbing the shell consumes | `src/nanopnp/core/stages.py`; `io/run.py`'s `run_case`; `solve/stage.py`'s `_instrumented` |
| The case schema and its dotted paths | `SPECIFICATION.md` §5.3.1 and its NOTEs; `src/nanopnp/io/case.py`; `src/nanopnp/io/defaults.py` |
| Shell, packaging and licence constraints | `SPECIFICATION.md` ADR-004, CON-07, CON-09, CON-11, CON-13, §8.2 criterion 4, §8.2.1 A4; `.knowledge/07-software-stack.md` §5–§6 |
| The spawned-worker discipline to copy | `src/nanopnp/sweep/run.py` module docstring, `_worker`, `_pool` |
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
