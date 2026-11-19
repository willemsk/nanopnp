# Code review 064: WP5.21's plan, the Analysis suite

2026-11-19 · branch `ccr-1df7b52e-xmkcc4`, the plan commit `e9d61b4` on `2eaf29f` · scope: the commit's 10 files. The
plan was read in full against the code it names: `post/export.py` (`SolutionFields`, `sampled_fields`,
`solution_fields`), `plot/data.py` (`sampled`, `field_values`, `field_triangulation`, `subdivided`, `NewtonRung`,
`newton_history`), `charge/deposit.py:locate`, `pipeline/run.py` (`open_run`, `RunResult.fields`), `gui/render.py`
(`render`, `render_charge`, `_write_scene`, `_state_path`, `RenderProcess`), `gui/convergence.py`, `gui/solver.py`
(`RunRequest`, `_worker`), `solve/stage.py:_instrumented`, `api/project.py` (`runs`, `_problems_of`, `_export_plan`,
`clean_store`, `set_study_value`), `api/reproduce.py:reproduce`, `api/sweep.py`, `sweep/run.py:MemberResult`,
`gui/web/runs.py`, `states.py`, `screens.py`, `frame.py`, `pages.py`, `plane.py`, `gui/geometry.py:lookup_table`,
`tests/tier1/test_project.py`, `test_study_runs.py`, `test_field_export.py`, `test_gui_screens.py`; each decision
against FR-32, FR-33, VER-44, ADR-004's NOTE and §8.2.45 AU1 to AU3, AG6 and AN5; the plan against
`.claude/skills/np-plan/wp.md`'s sections and caps · level: medium, with `--fix` · status: completed.

Static review: no test and no `gate.sh` ran; the review turn gates afterwards. `links.py` and `decisions.py` ran after
the fixes.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Important | D3; Item 2 | A run's scene is named by its field alone, and `render` unlinks every other `scene-*`: the explorer's own-range scene and the comparison's joint-range scene of one run overwrite each other, so "written once" serves whichever came last, and VER-78 (o)'s one `funcmin` depends on order | Fixed: a ranged scene's stem carries the range's digest; the sweep keeps the asked pair and the field's unranged pair, so a run's scenes stay bounded (each is tens of megabytes at the reference mesh); the server reuses a file by name |
| 2 | Important | Item 7; VER-44 | VER-44 omits and counts a sample no log axis can place; the move to uPlot, with axes the user switches (AU1), carried no rule for it, and uPlot draws non-positive values on a log axis unchecked | Fixed: `chart.js` nulls a value ≤ 0 on a log axis and the note counts it; the replay row asserts it |
| 3 | Important | Item 1; `test_analysis.py` row | The grid's spacing was given but not its counts or centres, so the row's "a cell 10⁻³ nm inside both fluids" could not be placed by the test, and two implementers would build different grids | Fixed: `n_r = ceil(width / spacing)`, centres at `low + (i + ½)·width / n_r` |
| 4 | Important | D4, D5; Item 8 | AU1 names Comparison's cut and AU3 puts the cut and probes on both maps; FR-33 links a field and its probes "until unlinked". No decision, route or check carried either | Fixed: D5 puts the pair's cut and probes on both maps, a series per run; `compare/{name}/cut`; D4's *Remove* unlinks; (o) checks the two series |
| 5 | Important | `test_project.py`, `test_study_runs.py` rows | Neither file solves anything today (`test_project.py` walks to `charge`; `test_study_runs.py` replays a written ladder), and the rows did not say how they get two solved runs at two biases or a live solve to compare against (wp.md, *Tests*) | Fixed: a grounding note; Item 3's fixture, the second run through `set_study_value`; Item 4's live solve through `on_solve` |
| 6 | Important | Item 6 | `/vendor/webgui` was to be mounted in `pages.py` beside Mol* and KaTeX, which mount from `gui/web/assets/`; webgui lives in `gui/assets/webgui/`. The Sonnet item would mount a missing folder | Fixed: Item 6 names `render.py:RENDERER_DIRECTORY`; grounding says where it is |
| 7 | Nit | Item 9; `states.py:boot` | `boot` refuses any state outside `STATES`, and the plan keeps `solved` out of it without changing the guard | Fixed: `boot`'s guard admits it; `write_sweep` and `run_plan` named by module |
| 8 | Nit | D9; Item 8 | `RunRequest` carries strings (`case`, `store`, `runs`, `plan`); the plan did not say what a rebuild sends or how the child finds the project for `Project.rebuild` | Fixed: `RunRequest.rebuild`, the run directory; the child opens the project above `runs` |
| 9 | Nit | D7; Item 7 | `lookup_table`'s five house names (`diverging`, `diverging_dark`, …) are not Matplotlib's; the plan did not say whether they stay, nor which map "diverging" means, nor the dark theme's | Fixed: the house names looked up first, then `matplotlib.colormaps` |
| 10 | Nit | D5; Item 3 | `ComparisonFile.quantity` had no default while `new_comparison(name, first, second)` takes none | Fixed: `potential` |
| 11 | Nit | VER-78 (o) row | The row checked a fetch of `scene-*.json`, while Item 8's route is `/api/analysis/scene?run=&field=`; the assertion could never match | Fixed: the row names the route |
| 12 | Nit | `test_analysis.py` row | The row built the fields "through `sampled_fields`", which returns `SampledFields`; Item 1 builds `SolutionFields` with `fields_of` | Fixed |
| 13 | Nit | Item 1 | `sampled` calling `field_at` dropped `field_triangulation`'s cache, built once for a figure and a slider: each cut would locate on the whole mesh again | Fixed: `field_at` keeps the last four located splits by identity |
| 14 | Nit | D6, D8 | REV-253's WP5.18 points (the fitted range's shading, the dark swatch) and REV-260's lead with the conductance were claimed with their rows but not placed | Fixed: grounding places them with the round (D12) |

Fourteen findings, all fixed in the plan. None changes an author's ruling. The words outside *Grounding* and
*Implementation details* stand at 1,650, the cap with its 10%: the In brief was shortened to hold the fixes. The plan
holds 12 decisions against the guideline of about six; the plan's report should say why.
