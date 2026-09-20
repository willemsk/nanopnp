# WP14 — The packaging probe and the desktop shell

**Status: planned, not started.** Written 20 September 2026, after WP7–WP13 delivered the case
schema and artefact chain (WP7), mesh ingestion and the reference geometry (WP8), external charge
and dielectric fields (WP9), case-driven runs, the CLI and IF-07 field output (WP10), the sweep
runner (WP11), the `reference` stabilisation mode (WP12) and the Tier-3 comparison harness (WP13).

It inherits four things and invents none of them. **The FR-27 stage plumbing** — the `Progress` and
`CancelToken` protocols, `Cancelled`, `check_cancelled`, `report`, and their threading through
`run_case`, `run_document` and `SolveStage` (`core/stages.py`, `io/run.py`, `solve/stage.py`).
**The case schema and its dotted-path machinery** (WP7) — `CaseDocument` with `extra="forbid"`,
`field_at`, `value_at`, `substitute` and `render_problems`, which is what makes an editor
*generated* rather than hand-written. **The run directory** (WP10) — `manifest.json`, `case.yaml`
and the run record, which is the shape a result panel reads. **The spawned-worker discipline**
(WP11) — `multiprocessing.get_context("spawn")` carrying plain data across the boundary, which the
background solver copies rather than re-invents.

This package belongs to [the Phase 1 delivery plan](phase-1-solver-core.md) and implements the
first half of its [WP14 section](phase-1-solver-core.md#wp14--the-packaging-probe-and-the-desktop-shell).
`SPECIFICATION.md` governs: where this plan and the specification disagree, this plan is the thing
that is wrong. Every `IF-`, `QR-`, `CON-`, `FR-`, `ADR-` and `RSK-` identifier below is a pointer
into it, never a restatement of it. Four amendments are made in the same commit as this plan and are
named in **Spec and plan amendments** below.

## Execution brief

### Scope

Two deliverables, in this order. **The packaging probe, first**: a trivial application importing
PySide6, `QtWebEngineWidgets`, NGSolve and `ngsolve.webgui` in one process, built into a Windows
bundle by a CI job on every push. It is the RSK-13 detector amendment A2 deferred out of Phase 0,
and a bundle that will not build is worth knowing about before the editor is written. **Then the
shell's first half**: the case editor generated from the frozen schema, run control with the solver
in a spawned background process, and a result panel over the WP10 run directory.

Discharges the case-editing and run-control halves of **IF-09**; closes the deferred **§8.2
criterion 4** and retires **RSK-13**; discharges **CON-09** mechanically and carries **CON-11**'s
licence notice into the bundle. Touches **FR-27**, **QR-12** and **CON-13**.

**WP14 does not complete QR-11.** The live convergence plot and the `webgui` field viewer bound to a
real solution are **WP15**; QR-11 is discharged by the two together, inside Phase 1. The split falls
where the data does: run control needs only the `(fraction, message)` the `Progress` protocol
already carries, and a convergence plot needs the `NewtonStep` record, which no hook forwards
(§Design 2).

This brief exceeds the 1,200-word target. The decisions table is the deliverable and every row
below settles a correctness or licensing question before implementation; the verification table
must carry every identifier claimed. Neither was cut to meet the count.

### Requirement and section pointers

| Need | Read |
|---|---|
| What the shell must cover and what it may not become | `SPECIFICATION.md` IF-09, QR-10, QR-11, ADR-004, RSK-15 |
| The Phase-1 GUI increment as specified | `SPECIFICATION.md` §8.1's GUI-increment table, §8.2 criterion 4, §8.2.1 amendments A2 and A4 |
| The stage plumbing the shell consumes | `src/nanopnp/core/stages.py` (`Progress`, `CancelToken`, `CancelFlag`, `Cancelled`); `io/run.py`'s `run_case`; `solve/stage.py`'s `_instrumented` |
| The schema and its dotted paths | `SPECIFICATION.md` §5.3.1 and every NOTE under it; `src/nanopnp/io/case.py` (`field_at`, `value_at`, `substitute`, `render_problems`); `src/nanopnp/io/defaults.py` (`SWITCH_PATHS`, `CONFIGURATION_PATHS`) |
| Licences the bundle carries | `SPECIFICATION.md` CON-07, CON-09, CON-11, ADR-003; `.knowledge/07-software-stack.md` §5 and §6 |
| The spawned-worker discipline to copy | `src/nanopnp/sweep/run.py` module docstring and `_worker`/`_pool` |
| The exit-code contract the shell must agree with | `SPECIFICATION.md` §3.1's IF-02 NOTE; `src/nanopnp/cli/errors.py` |

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| Shell technology | **PySide6 native**. ADR-004's local-web-app alternative (FastAPI + `pywebview`) is **closed** in this commit | Author ruling, 20 September 2026, closing the alternative ADR-004 left "on the table… the choice may wait until Phase 1". PySide6 is already the `gui` extra and is named in §2.6 and CON-09; `QWebEngineView` hosting NGSolve webgui is **[tested]** in `.knowledge/07` §5 |
| Packaging tool | **PyInstaller**, one-dir, not one-file | Author ruling, 20 September 2026. ADR-004 named briefcase or conda-constructor; PyInstaller is the third candidate `.knowledge/07` §5 lists and the sharpest RSK-13 detector — it resolves the four binary payloads or names the one that defeats it. One-dir: §Design 3. ADR-004 amended in this commit |
| Where the bundle is built and verified | A **`windows-latest` CI job builds it on every push** and uploads the artefact; `--selftest` launches it headlessly there; the **author double-clicks it once**, and that observation closes §8.2 criterion 4 | Author ruling, 20 September 2026, closing the phase plan's open decision. CI makes RSK-13 a continuous detector rather than a one-off; "double-clickable on a user's desktop" is a human observation, not a process exit code |
| Is the bundle job gated? | **Yes** — a failed build fails CI. It is demoted to `continue-on-error` only if PyInstaller proves flaky for reasons outside this repository, and that demotion is recorded with the failure that caused it | RSK-13's detection value is entirely in being loud. A probe nobody looks at is amendment A2 again |
| What the probe must import | PySide6 `QtWidgets`, **`QtWebEngineWidgets`**, `ngsolve`, `netgen`, `ngsolve.webgui`, in one process | Those are the binary payloads RSK-13 is about. A probe omitting Qt WebEngine tests the easy half (§Design 3) |
| How the editor is generated | By walking **`CaseDocument.model_fields`**, not `model_json_schema()` | JSON Schema loses the container kinds, the `schema` alias and `_check_registries`, and the walk yields the dotted paths `SWITCH_PATHS`, `field_at` and the sweep planner already speak — so the editor and the FR-25 manifest index the case the same way. Full argument: §Design 1 |
| One walker, not two | `tests/tier1/test_manifest.py`'s ad-hoc switch enumeration is **replaced** by the new `case_fields()` walk, which both it and the editor consume | Two walks over one schema drift, and the one that drifts silently is the one no test reads. Moving it also makes the editor's "every field is editable, in both directions" test mechanical rather than a second list |
| The editor holds no vocabulary of its own | Every enumeration comes from the schema (`Literal` via `get_args`) or a runtime registry (`registered_models`, `registered_stabilisations`, `AVAILABLE_SOLVERS`, `available_corrections`). **No default, unit or option list is written in `gui/`** | A second source of truth for `numerics.stabilisation`'s values is a GUI offering a mode the solver does not apply — a manifest describing a run that never happened, which §5.3.3 exists to prevent |
| Two-stage validation | Per-field on edit through `FieldReference.validate`; whole-document on commit through `substitute` + `CaseDocument`, rendered by `render_problems` | `field_at` already gives the first and §5.3.4 already requires the second. The user sees the *same* diagnostic text the CLI prints for the same mistake, which is one error vocabulary rather than two |
| The unit of work is a **case file on disk** | The shell opens, edits, saves and runs a file; it never runs an unsaved document | §5.3.1: the case file is the unit of reproducibility. A run from an in-memory document emits a manifest naming an input that does not exist — a result that cannot reconstruct its run |
| Qt never touches the view-model | `gui/case_model.py`, `gui/run_model.py` and `gui/solver.py` import **no PySide6**; `gui/app.py` and `gui/widgets/` do. Asserted on `sys.modules` | The discipline `cli/__init__.py` states for itself and the assertion VER-25, VER-27 and VER-32 already use. It is also what lets Tier 1 test the shell on every matrix job, including those where Qt cannot be imported at all (§Design 4) |
| The solver runs in a **spawned** process | `multiprocessing.get_context("spawn")`, one process per run, taking plain data (case path, store root, run directory) and posting typed picklable events on a `Queue` | ADR-004 requires a background process. `spawn` because a forked child inherits the parent's Qt event loop and its already-imported NumPy, and because it is the only start method Windows has (`sweep/run.py`'s own reason) |
| Cancellation crosses as an **`Event`** | `gui/solver.py` supplies `EventCancel`, an adapter over `multiprocessing.Event` satisfying `CancelToken`. `core/stages.py` gains no `multiprocessing` import | `CancelFlag` is an in-process boolean and says so. The protocol is what crosses, not the class |
| **No thread pinning** in the GUI worker | Unlike `sweep/run.py`, the run process does not call `pin_threads` | The sweep pins because N workers sharing one thread pool are not N independent workers and QR-06's scaling claim would measure the pool. One interactive solve has no such claim and wants the threads |
| Failure reporting | The run process classifies its own exception through `cli/errors.classify` and reports the **§3.1 exit class**; the shell shows that class and the QR-12 diagnostic, no traceback unless asked | A GUI failure and a CLI failure on the same case must be the same diagnosis. A second classification is a second contract to keep in step |
| Tier-1 tests construct no Qt object | `tests/tier1/test_gui_viewmodels.py` imports no PySide6. A separate `tests/tier1/test_gui_widgets.py` constructs widgets under `QT_QPA_PLATFORM=offscreen` and **skips on `(ImportError, OSError)`** | Measured: `from PySide6 import QtWidgets` raises `ImportError: libEGL.so.1` in this development container (PySide6 6.11.2) — the same "wheel imports, GL-dependent payload dlopens and fails headless" mode `tests/tier1/test_mesh_quality.py` already handles for gmsh. §Design 4 |
| No apt packages on the push gate | Linux CI installs nothing beyond the wheels; widget construction is exercised on the **`windows-latest` and `macos-latest`** matrix jobs, where Qt's platform plugin works unaided | §Design 4. Two of CON-13's three platforms is the better claim anyway |
| Licence notice | `packaging/LICENSES-BUNDLE.md`, collected into the bundle and reachable from the probe's window: BSD-3 (nanopnp), LGPL-2.1 (NGSolve/Netgen), LGPL-3 (PySide6/Qt), **GPL-2+ (SuiteSparse UMFPACK, inside the NGSolve wheel) — under which the bundle as a whole is distributed** | CON-11 requires the bundle to state the obligations its default solver creates. A licence statement cannot be retrofitted to something already distributed |

### Work items

In dependency order. Read §Design 3 before item 2, §Design 1 before item 5, §Design 2 before item 7.

| # | Files | Deliverable | Identifiers |
|---|---|---|---|
| 1 | `src/nanopnp/gui/probe.py` | The probe application: `build_window()` returning a `QMainWindow` with a `QWebEngineView` showing a `ngsolve.webgui` scene of a unit-square mesh and a pane naming the resolved versions and the licence notice; `main(argv)` with `--selftest` (construct offscreen, wait for `loadFinished`, exit 0) | RSK-13, §8.2 criterion 4 |
| 2 | `packaging/nanopnp-probe.spec`, `packaging/LICENSES-BUNDLE.md`, `pyproject.toml` | The PyInstaller one-dir spec collecting `ngsolve`, `netgen` and the Qt WebEngine payload; the CON-11 licence notice; `[project.scripts] nanopnp-probe`; `PySide6.*` added to the mypy overrides if its shipped stubs do not satisfy `--strict`; a `packaging` dependency group carrying `pyinstaller` | CON-11, CON-07, QR-09 |
| 3 | `.github/workflows/ci.yml` | The `bundle` job: `windows-latest`, py3.12, `uv sync --all-extras --group packaging`, build, `--selftest`, upload the artefact. Gated. `QT_QPA_PLATFORM=offscreen` on the widget step of the existing Windows and macOS matrix jobs | RSK-13, CON-13 |
| 4 | `src/nanopnp/io/case.py` | `case_fields() -> tuple[FieldReference, ...]`: every editable dotted path of `nanopnp/case/v1` in declaration order, walking `model_fields` through `X \| None`, mappings and sequences exactly as `field_at` resolves them | IF-03, FR-27 |
| 5 | `src/nanopnp/io/defaults.py`, `tests/tier1/test_manifest.py` | `SWITCH_PATHS`/`CONFIGURATION_PATHS` verified against `case_fields()` rather than against a second walk; the test's local enumeration deleted | FR-25 |
| 6 | `src/nanopnp/gui/case_model.py` | The editor view-model: `CaseEditor` over a `CaseDocument` and `case_fields()`, per-field `validate`, whole-document `commit()` through `substitute`, `problems()` rendered by `render_problems`, `save()`/`load()`. No PySide6 import | IF-09, IF-03, QR-12 |
| 7 | `src/nanopnp/gui/solver.py` | The bridge: `RunEvent` (a frozen, picklable union — `Started`, `Stage`, `Progress`, `Finished`, `Failed`, `Cancelled`), `EventCancel`, `QueueProgress`, `_worker(payload)` calling `run_case`, and `SolverProcess` with `start()`, `cancel()`, `drain() -> tuple[RunEvent, ...]`. No PySide6 import | FR-27, IF-09, §3.1 IF-02 NOTE |
| 8 | `src/nanopnp/gui/run_model.py` | The run-control view-model: the state machine (`idle → running → finished/failed/cancelled`), the monotone fraction, the message log, and the `RunResult` record read back from the run directory. No PySide6 import | IF-09, FR-27 |
| 9 | `src/nanopnp/gui/widgets/` | `CaseEditorWidget` (a form built from `case_fields()`; `Literal` → combo box, `bool` → check box, numeric → validated line edit), `RunControlWidget` (start, cancel, progress bar, log), `ResultWidget` (the scalar QoIs and the manifest's Deviations group) | IF-09, QR-11 in part |
| 10 | `src/nanopnp/gui/app.py`, `pyproject.toml` | `main(argv)` assembling the window; `[project.scripts] nanopnp-gui` | IF-09 |
| 11 | `SPECIFICATION.md`, `docs/plans/phase-1-solver-core.md`, `docs/plans/current.md`, `.knowledge/07-software-stack.md` | The four amendments below; the phase plan's WP14/WP15 split and its closed open decision; `current.md` repointed; the measured Qt and import facts recorded | — |

### Verification

Gate: `uv run ruff check . && uv run ruff format --check . && uv run mypy src/ && uv run pytest`.
**VER-43** is added to `SPECIFICATION.md` §7.2 in this commit; every row below discharges part
of it, and no row claims a `VER-` or `VAL-` identifier that is not here.

| Test file | Tier | Identifiers | Assertion and oracle | Tolerance source |
|---|---|---|---|---|
| `tests/tier1/test_case_fields.py::test_if09_case_fields_enumerates_the_whole_schema` | 1 | VER-43, IF-09, IF-03 | Every path `case_fields()` yields resolves through `field_at`, and every field of every model reachable from `CaseDocument` appears — **in both directions**, so a field added later fails here rather than becoming silently uneditable | Exact (structural) |
| `tests/tier1/test_case_fields.py::test_fr25_switch_paths_are_the_same_walk` | 1 | VER-43, FR-25 | `SWITCH_PATHS ∪ CONFIGURATION_PATHS` classifies exactly the switch-typed paths `case_fields()` yields, in both directions | Exact (structural) |
| `tests/tier1/test_gui_viewmodels.py::test_if09_the_view_models_import_no_qt_and_no_ngsolve` | 1 | VER-43, IF-09, CON-09, FR-27 | In a fresh process, importing `gui.case_model`, `gui.run_model` and `gui.solver` leaves `PySide6`, `PyQt5`, `PyQt6`, `ngsolve` and `netgen` absent from `sys.modules` | Exact (`sys.modules`) |
| `tests/tier1/test_gui_viewmodels.py::test_if09_editor_refuses_a_value_the_schema_refuses` | 1 | VER-43, IF-09, IF-03, QR-12 | A bad value at a known path is refused at the field, naming the path, the value and the declared type, before any document is substituted into; the document is unchanged | Exact (structural) |
| `tests/tier1/test_gui_viewmodels.py::test_if09_editor_reports_registry_problems_as_the_cli_does` | 1 | VER-43, IF-09, QR-12 | A document naming an unregistered stabilisation mode produces the *same* `render_problems` text the CLI prints for the same file | Exact (string identity) |
| `tests/tier1/test_gui_viewmodels.py::test_if09_editor_offers_only_what_the_schema_and_registries_name` | 1 | VER-43, IF-09, FR-16 | The option list at every `Literal`-typed path equals `get_args` of its annotation, and the registry-backed paths equal the live registries. No option list is written in `gui/` | Exact (structural) |
| `tests/tier1/test_gui_viewmodels.py::test_if09_run_model_fraction_is_monotone_and_ends_at_one` | 1 | VER-43, FR-27 | Driven by a synthetic event stream, the run view-model's fraction is monotone in [0, 1] and ends at 1; out-of-order events do not move it backwards | Exact (structural) |
| `tests/tier1/test_gui_viewmodels.py::test_if09_failure_carries_the_cli_exit_class` | 1 | VER-43, IF-09, §3.1 | For one case of each of the case, gate, convergence and cancellation classes, the view-model reports the class `cli.errors.classify` returns for the same exception | Exact |
| `tests/tier1/test_gui_solver_process.py::test_fr27_a_spawned_run_reports_progress_and_finishes` | 1 | VER-43, FR-27, IF-09 | A real spawned run of a cheap case posts `Started`, at least one `Progress`, and `Finished`; the run directory it names holds `manifest.json`, `case.yaml` and the run record; the events pickle | Exact (structural) |
| `tests/tier1/test_gui_solver_process.py::test_fr27_cancelling_a_spawned_run_writes_no_artefact` | 1 | VER-43, FR-27, §5.3.2 | Cancelling mid-run yields `Cancelled` naming where it stopped, the child exits, and the store holds no artefact for that case | Exact (structural) |
| `tests/tier1/test_gui_widgets.py::test_if09_the_form_binds_every_schema_field` | 1 | VER-43, IF-09, QR-11 | Under `QT_QPA_PLATFORM=offscreen`: the built form's bound paths equal `case_fields()`, editing a widget moves the document, and no pixel is asserted. **Skips on `(ImportError, OSError)`** | Exact (structural); skip rule per §Design 4 |
| `tests/tier1/test_gui_probe.py::test_rsk13_the_probe_names_the_payloads_it_must_carry` | 1 | VER-43, RSK-13, CON-11 | The probe's declared import set is exactly PySide6 `QtWidgets`, `QtWebEngineWidgets`, `ngsolve`, `netgen`, `ngsolve.webgui`; the licence notice names BSD-3, LGPL-2.1, LGPL-3 and GPL-2+ and states the bundle's own licence. Runs without constructing Qt | Exact (structural) |
| CI job `bundle` (`windows-latest`) | — | VER-43, RSK-13, §8.2 criterion 4, CON-13 | PyInstaller builds the one-dir bundle and `nanopnp-probe.exe --selftest` exits 0. Gated; the artefact is uploaded for the author's double-click | Pass/fail |

Placing a file under `tests/tier1/` is what marks its tier (`tests/tier1/conftest.py`).

### Out of scope

| Deferred | Owner |
|---|---|
| The live convergence plot off the `damped_newton` callback | **WP15**. It needs a structural `NewtonStep` hook in `solve/stage.py` that does not exist (§Design 2) |
| The `webgui` field viewer bound to a real solution | **WP15**. WP14's probe renders a trivial scene; binding one to a `ModelSolution` is the viewer |
| QR-10 — an experimentalist runs a case unaided | The GUI track's own gate, §8.1, not Phase 1's. Phase-1 criterion 5 asks only that the increment run a case on the author's platform |
| macOS and Linux installers | post-1.0 per §8.1's GUI table. WP14 builds a Windows bundle because that is what §8.2 criterion 4 names |
| Geometry, charge, sweep and figure-export surfaces | Phases 2, 3 and 4 per §8.1's GUI-increment table |
| A GUI over any unvalidated capability | RSK-15. Nothing in `gui/` exposes a switch the solver does not honour |

### Open questions

None blocking. Two the author answers **after the first bundle runs**, not before implementation:

1. **Does `--selftest` reach `loadFinished` under `QT_QPA_PLATFORM=offscreen` on a Windows
   runner?** QtWebEngine wants a rasteriser. If `QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu` does not
   suffice, the selftest degrades — by rule, recorded in the plan — to constructing the
   `QWebEngineView` and exiting, which is still the binary-dependency detector RSK-13 asks for.
2. **Does the bundle double-click?** Only the author can say. That observation closes §8.2
   criterion 4; until it is recorded, the criterion stays outstanding and RSK-13 stays open, exactly
   as amendment A2 left it.

## Spec and plan amendments

Made in the same commit as this plan.

1. **ADR-004** — the local-web-application alternative is closed in favour of the PySide6 shell,
   decided at WP14; PyInstaller is named beside briefcase and conda-constructor as the tool the
   probe uses, one-dir, with the LGPL-3 and QtWebEngine reasons; the background process is recorded
   as `spawn`.
2. **§8.2.1, new amendment A4** — how criterion 4 is discharged: built by a gated Windows CI job on
   every push, launched headlessly by `--selftest` there, and closed by the author's double-click.
3. **§7.2, new row VER-43** — the desktop shell's view-model layer, the schema walk, the
   solver-process bridge, the exit-class agreement and the probe's payload set.
4. **Appendix A** — `IF-09`, `QR-11` and `CON-09` move from "None yet" to VER-43, and the coverage
   sentence is corrected.

## Design

### 1. Why the editor is generated from `model_fields`, not `model_json_schema()`

`model_json_schema()` is never called anywhere in this codebase today, and adopting it here would be
adopting a lossy projection. Three things the editor needs do not survive it.

**The container kinds.** `field_at` already distinguishes `"model"`, `"mapping"` and `"sequence"`,
and the distinction is load-bearing for an editor exactly as it is for the sweep planner: a mapping
entry may be *created* (`physics.solid_permittivities.membrane`), a model field may not, and a
sequence index must already exist. JSON Schema expresses the shapes but not that rule, so the editor
would re-derive it — a second copy of a rule `io/case.py` already states.

**The alias.** `CaseDocument.schema_id` is written `schema:` in the file. A form keyed on JSON
Schema property names would offer `schema_id`, which is not a key any case file may carry.

**The validation that matters.** `extra="forbid"` is a document property, but `_check_registries` is
not in the JSON Schema at all: it asks the *installed* registries whether `physics.model`,
`numerics.stabilisation`, `numerics.linear.solver` and every correction name resolve to something
present. A form generated from JSON Schema would happily offer a stabilisation mode this build does
not register, which is precisely the case §5.3.3 says must be impossible — a manifest recording a
mode the solver never applied.

Walking `model_fields` gives all three for free, and gives the dotted paths as a by-product. That
matters beyond convenience: `SWITCH_PATHS`, `field_at`, `value_at`, `substitute` and every sweep axis
already index this schema by dotted path. An editor that indexed it any other way would be the only
component in the package that did.

Measured, 20 September 2026 **[tested]**: `import nanopnp.io.case` costs 622 ms and leaves **neither
`ngsolve` nor `numpy` in `sys.modules`**. So the editor can enumerate, display and validate the whole
schema without the solver ever being imported — which is what keeps a GUI that is only browsing a
case as cheap as the CLI's 56 ms budget intends stage introspection to be. NGSolve is imported by the
*run* process, on the far side of the boundary, when the user asks for a solve.

### 2. What crosses the process boundary, and the seam the WP14/WP15 split falls on

`run_case` already takes `progress: Progress | None` and `cancel: CancelToken | None`, and
`run_document` already threads both through every stage with `_slice()` mapping each stage's own
fraction into its share. Nothing about that plumbing needs to change for run control. What needs
building is the transport.

Three things cross, all plain and picklable:

- **Into the child**: the case path, the store root and the run directory, as strings — re-resolved
  inside the child rather than pickled live, which is `sweep/run.py`'s own rule and is what makes the
  child identical to a CLI invocation of the same case.
- **Out of the child**: `RunEvent` values on a `Queue`. `QueueProgress` satisfies the `Progress`
  protocol by putting `(fraction, message)` on it.
- **Into the child, continuously**: cancellation, as a `multiprocessing.Event`. `CancelFlag` is an
  in-process boolean and its own docstring says so; `EventCancel` wraps the `Event` and satisfies
  `CancelToken`, and `core/stages.py` gains no `multiprocessing` import for it — the *protocol* is
  what crosses, not the class.

Now the seam. `SolveStage._instrumented` builds `on_step(step: NewtonStep)`, which calls
`check_cancelled` and then `report(progress, …, f"iteration {step.iteration}, residual
{step.residual:.3e}")`. The residual reaches the caller **only inside a formatted string**. For a
progress bar and a log that is exactly right and nothing is missing. For a convergence plot it is
not: the plot's whole subject is six or more orders of magnitude of residual decrease, and `:.3e`
keeps three significant figures of it.

So WP15 must add a structural hook that forwards the `NewtonStep` itself — trivially picklable, five
plain fields — and **must not** recover the residual by parsing the progress message. A number
obtained by regex from a display format is a number whose precision is a formatting decision, and the
first person to widen that format would move the plot without touching it.

Two further facts WP15 will need and WP14 should not pre-empt: `on_step` is injected only when
`isinstance(rung.model, CoupledModel)` (`solve/stage.py`), so the electrostatic rungs of the NUM-18
ladder emit no steps at all, and a plot that assumed a continuous stream across the ladder would show
a gap it cannot explain. `on_rung` is the per-rung hook beside it.

### 3. What makes the probe a detector rather than a demonstration

RSK-13 is "desktop packaging defeated by a binary dependency". A probe answers it only if it carries
every binary dependency the real shell will. Four payloads:

| Payload | Why it is the risk |
|---|---|
| `PySide6.QtWidgets` | Qt's own platform plugins and their system-library dependencies. Measured here: it fails in this container (below) |
| `PySide6.QtWebEngineWidgets` | By a wide margin the largest and most packaging-hostile — a Chromium build, a separate helper executable, and a resource tree a bundler must be told about |
| `ngsolve`, `netgen` | Compiled extensions plus data files, and the wheels chosen for CON-07 in the first place |
| `ngsolve.webgui` | The scene generator; `WebGLScene.GenerateHTML()` is what makes it embeddable (`.knowledge/07` §1, **[tested]**) |

A probe omitting QtWebEngine tests the easy half and would have retired RSK-13 without touching the
dependency most likely to defeat it.

One-dir rather than one-file, for two independent reasons. **LGPL-3**: PySide6 and Qt are used under
the LGPL option (CON-09), which requires that a recipient be able to replace the covered libraries;
a directory of shared libraries satisfies that directly, and an opaque self-extracting executable
invites the argument. **QtWebEngine**: its helper process is a separate executable that a one-file
extractor must locate at runtime in a temporary directory, which is a failure mode with nothing to
do with this project.

The licence notice is not paperwork. CON-11 says the redistributable bundle defaults to UMFPACK,
which is GPL-2+ and ships inside the NGSolve wheel, and that the bundle "SHALL be distributed under
the resulting GPL-2+ obligations and SHALL state them in its licence notice". So the bundle's own
licence is GPL-2+ while the library remains BSD-3, and the notice must say exactly that — written
with the first bundle, because retrofitting a licence statement to something already distributed is
not a thing that can be done.

### 4. Where a Qt object can be constructed, measured

Measured in this development container, 20 September 2026 **[tested]**, PySide6 6.11.2:

```
from PySide6 import QtWidgets            -> ImportError: libEGL.so.1: cannot open shared object file
from PySide6 import QtWebEngineWidgets   -> ImportError: libEGL.so.1: cannot open shared object file
```

Not just WebEngine: **`QtWidgets` itself** cannot be imported. This is the same failure class
`tests/tier1/test_mesh_quality.py` already handles for the gmsh wheel — the package imports, a
GL-dependent payload dlopens, and the exception is `ImportError` or `OSError` depending on which
library is missing — which is why the skip idiom is `except (ImportError, OSError)` and not
`pytest.importorskip`.

Three consequences, and they are the reason the view-model layer is Qt-free rather than merely
tidy:

1. **The Tier-1 GUI suite must run where Qt cannot be imported**, because that includes this
   development container and may include `ubuntu-latest`. Making the view-models Qt-free means the
   behaviour of the editor, the validation, the run state machine and the process bridge is asserted
   on **every** matrix job, all five Python versions, rather than on whichever ones happen to have
   `libegl1`.
2. **Widget construction is exercised where the product is a desktop product.** The existing
   `windows-latest` and `macos-latest` matrix jobs already run `uv sync --all-extras`, so PySide6 is
   installed there and Qt's platform plugin works unaided; `QT_QPA_PLATFORM=offscreen` is all the
   widget test needs. That is a better claim than a Linux job with hand-installed system packages
   could make, because it is made on two of the three platforms CON-13 names.
3. **The push gate installs no system packages.** A gate that needs `apt` to test a GUI has quietly
   taken on a portability promise per runner image, and CON-07's whole posture is that nothing on the
   user path needs a build step. If the Linux widget coverage is ever wanted, it belongs in a
   separate, non-gating job that says what it installed.
