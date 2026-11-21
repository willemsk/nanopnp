# Code review 068: WP5.27's plan, Qt's removal and the short guide

2026-11-21 · branch `ccr-be3ad089-2fgjo6`, the plan commit `7fec489` on `0a7c24f` · scope: the commit's 13 files. The
plan `docs/plans/phase-5/wp5.27-qts-removal-and-the-short-guide.md`; the Phase 5 plan's WP5.27 entry, its verification
row and criterion 3; the record's *Amended 21 November 2026* section; §8.2.47 AW9 to AW11 and their `holds-now.yaml`
lines; §8.1's Phase 5 gate; the design document's rows Q05 to Q08 and Q31 to Q34; REV-274; `current.md`. Checked
against the code at this head: `gui/run_model.py`, `gui/solver.py`, `gui/convergence.py`, `gui/web/queue.py`,
`gui/web/runs.py`, `gui/web/frame.py`, `gui/web/study_tools.py`, `api/project.py:set_study_value`, `io/models.py`,
`io/manifest.py`, `gui/web/analysis.py`, `gui/geometry.py`, `gui/charge.py`, `gui/render.py`, `gui/probe.py`,
`gui/web/server.py`, `cli/workbench.py`, `core/errors.py`, `core/paths.py`, `solve/stage.py`, `pipeline/run.py`,
`pyproject.toml`, `ci.yml`, the `tier12` action, `gate.sh`, `justfile`, `docs/scripts/generate.py`, `mkdocs.yml`,
`render_shell.py` and the tests the plan names · level: high as called, with `--fix` · status: completed.

Static review: no `gate.sh` and no test run; the review turn gates afterwards. Two read-only measurements were run:
the case paths *More values* offers before and after D3, and what importing the server loads. `decisions.py` was
re-run after the fixes; `decisions.py --check` and `links.py` pass.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Important | The plan, *Implementation details*, item 7, `gui/geometry.py`'s list | `STAGE_1_FRAME` is on the list of names to delete. `reduced_image` and `density_section` set `frame=STAGE_1_FRAME`, and both stay: `gui/web/plane.py` and `meso_tools.py` import them. Followed as written, the removal breaks Meso's Density and the reduced map | Fixed: the name is off the list, and *Grounding* D5 says who reads it |
| 2 | Important | The plan, item 1, `progress_line()` | The rung is appended "while the stage is the rung's", and `rung` is cleared on `Started` only. `Rung.stage` is the continuation ladder's stage (`solve/stage.py`'s `on_rung` passes `rung.stage`), not the walk's `Stage.index`, so the two cannot be compared; a comparison of them shows the rung on the wrong stage or never, and a rung kept after the solve stage shows "rung 5 of 5" under the QoI stage | Fixed: `rung` is cleared on each `Stage` too and appended while it is set; *Grounding* D2 states what `Rung.stage` is |
| 3 | Important | The plan, work items 6 to 8 | The items do not hold one by one. Item 6 moves `PayloadError`, `FRAGMENT` and the exercise helpers out of `gui/probe.py`, which lives until item 7 with `test_gui_probe.py`, whose tests require the probe to import each payload it declares. Item 7 deletes `probe.py`, so `licence_notice`, and the notice's force-include, while the notice moves and its tests are item 8's: item 7's "Tier 1 passes" cannot be met, and its wheel carries no notice | Fixed: item 6 copies the helpers and leaves the probe whole; item 7 takes the notice's move with the removal and deletes `test_gui_probe.py`; item 8 keeps `nanopnp --env` and the manifest's row |
| 4 | Important | The plan, D7; *Grounding* D7 | `nanopnp --env` states the notice's path, and the plan names no home for that path once `gui/probe.py:licence_notice` leaves. `cli/workbench.py` builds `--env` and may not import `gui` statically (VER-61; the `cli -> gui` row is a string row), so the obvious home, the new `gui/web/selftest.py`, adds an upward edge | Fixed: `core/paths.py:LICENCE_NOTICE`, beside `PACKAGE_ROOT`, read by the command line and by the notice's tests |
| 5 | Important | The plan, *Verification*, the self-test's row | "A renderer URL that answers other bytes fails naming `ngsolve.webgui`": the self-test starts the real server as a child, which serves the shipped file. The row did not say how the test gets a server that answers other bytes | Fixed: the check is `_exercise_renderer(expected: Path)`, and the test passes a file of other bytes; the row is reworded |
| 6 | Important | The plan, *Verification*, FR-25's row; D4 | The oracle is that the tile says "None" only at `count` 0. The sentence is written by `analysis_tools.py`'s NiceGUI tile, which a Tier 1 test in `test_analysis.py` cannot read; `AnalysisModel.deviations` returns the lines | Fixed: the oracle is the returned list, empty only at `count` 0; item 3 says the test writes a `manifest.json` into `tmp_path` |
| 7 | Nit | The plan, item 1, the poll | The poll now copies every `RunModel.log` line, the `failed (…): message` and `cancelled: where` lines among them, and still says `{label}: {diagnosis}` itself, so a failed run's message is logged twice | Fixed: the poll no longer says the diagnosis; *Grounding* D2 states the repeat |
| 8 | Nit | The plan, *Grounding* D5 and item 7 | `tests/tier1/test_gui_widgets.py` is also named by `justfile`'s `test-parallel`, whose second line would fail on the deleted file. `ci.yml` has two `--ignore` calls, not three. The steward skill also describes the `bundle` job, `.gitignore` excepts the probe's spec, and `gui/__init__.py`'s docstring calls the package the PySide6 shell | Fixed: the grounding and item 7's list name them |
| 9 | Nit | The plan, *Grounding* D3; §8.2.47 AW10 | Dropping the `owner_of` test adds eleven paths, not the nine the grounding and AW10 count: `numerics.continuation` and `outputs` come too. Both are settings without a field, so AW10's rule covers them; `outputs` is a list, typed as YAML | Fixed in the grounding. AW10's text is the author's and stands: its nine are examples of its rule |
| 10 | Nit | The plan, D6 and D9; the restated VER-43, VER-44 | The restated rows say the self-test "imports NGSolve, Netgen and the shipped renderer in one process" and "fails when the shipped renderer does not reach its document". D6 fetches the renderer from a server child and compares its bytes; no browser loads it. D9 corrected three sentences and not these | Fixed: D9 corrects four, the self-test's among them. `test_gui_screens.py` still draws the renderer in Chromium |
| 11 | Nit | `specification/history/47-phase-5-amended-the-early-close.md`, AW9 | The *Clause changed* cell says the design document's row Q31 to Q34 is "unchanged"; this commit rewrites that row | Fixed: the cell names the row as changed in this commit |
| 12 | Nit | The plan, *Grounding* D10 | "244 links": this commit's REV-274 section adds one from `review-items.md` to the plan | Fixed: 245 |
| 13 | Nit | The plan, item 1, the running shot | `render_shell.py`'s study group clicks *Run study* in the light `shell-study-tube-run` shot and waits 12 s; the dark shots find the run ended. The plan did not say which shot takes the click or that the dark scheme cannot show a running entry | Fixed: the new shot is light only, comes first, takes the click and waits 2 s |

Checked and found true: `RunModel._apply` logs every event but `Rung` and `Iteration`, and `ConvergenceModel.rung`
discards `total`; `Entry.run` is the model `RunControl.poll` fills; `watch_queue` redraws on `Queue.moved`;
`case_fields()` gives 122 paths and `FIELDS` covers 74; the six paths through a list index are offered today;
`set_study_value` refuses a variable and a header key; `_deviations_payload` writes `count`, `switches` and
`contributed`, and `AnalysisModel.deviations` reads `switches` alone; only `gui/app.py`, `gui/probe.py` and
`gui/widgets/` import PySide6; every other name on item 7's list has no reader outside Qt and the tests the plan
changes; no `gui -> x` layering edge is lost; `superlu` is a registered solver; importing the server loads `fastapi`,
`nicegui` and `uvicorn` and no NGSolve, Netgen or structure payload; the server takes `--no-browser --state empty`,
answers `/api/health` and serves `RENDERER_DIRECTORY` at `/vendor/webgui`; `MissingExtraError` is `EXIT_CASE`, 3;
the `tier12` action runs in `platforms` and `full-matrix`; `environment()` maps `DISTRIBUTIONS` and
`check_environment` reports drift alone; `desktop.md` is linked from the five places named; the six shots of the
guide exist under those names; only the four register pages link into `plans/` or `code_reviews/`; REV-274's five
points match the code; `0a7c24f` is on `main`; `current.md` holds 700 words. The plan has every section of
`.claude/skills/np-plan/wp.md`; each decision ends with its source; ten decisions against a guideline of six.

The plan's words after the fixes and the review turn's trim of eight words, by `wc -w`: 3,149 in all (cap 3,850);
1,646 outside *Grounding* and *Implementation details*, their two headings counted outside (cap 1,650); 759 in
*Implementation details* (cap 1,100).

Thirteen findings, all fixed: six important and seven nits. No fix changes a ruling of the author. Finding 10 changes
which sentences D9 corrects when the clauses land, in the plan's own decision.
