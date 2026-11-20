# Code review 065: WP5.21, the Analysis suite

2026-11-20 · PR #194, branch `ccr-797cfb5c-04dgls`, head `a5c0922` on base `08b178c` · scope: the PR's diff
(`gh pr diff 194`), 72 files. The source read in full through six angles: line by line with each touched function,
removed behaviour, callers, language pitfalls, wrappers and caches, and `CLAUDE.md` with `.claude/rules/python.md`.
Then a sweep for gaps. Read closely: `post/fields.py`, `post/export.py`, `api/reproduce.py`, `api/project.py`,
`solve/stage.py`, `pipeline/run.py`, `io/project.py`, `plot/data.py`, `gui/render.py`, `gui/solver.py`,
`gui/convergence.py`, `gui/geometry.py`, `gui/web/analysis.py`, `analysis_tools.py`, `pages.py`, `runs.py`, `chart.py`,
`chart_view.py`, `assets/chart.js`, `plane.py`, `physics_tools.py`, `study_tools.py`, `frame.py`, `states.py` and
`.claude/scripts/gui/render_shell.py`. The vendored uPlot was not read; CON-09 serves it unmodified. · level: xhigh,
with `--fix` · status: completed.

Static review: no `gate.sh` and no `--nightly` run. After the fixes, `ruff` and `mypy src/` passed. So did
`test_study_runs.py`, `test_figures.py` and `test_analysis.py`, and VER-78 (o)'s four browser tests.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Important | `gui/web/analysis.py:AnalysisModel.choices` | The explorer's runs were ordered by reversed folder name, a hash or `upto-<stage>-<hash>`, not newest first. A study holding a run stopped at its charge opened on that run, which has no fields | Fixed: ordered by the record file's time, newest first, as Study's records are |
| 2 | Important | `analysis_tools.py:comparison` | A comparison whose run's fields failed to write never checked `_FAILED`: each tick it started a render child again, restoring the solve, and never said why | Fixed: a failed read is said and not started again |
| 3 | Important | `analysis_tools.py:comparison` | A comparison of a run cleaned from the store, or one never solved, said "Reading the two runs' fields…" forever | Fixed: each run that cannot draw is named, with why; a cleaned run points to *Solve again* in the explorer |
| 4 | Important | `analysis_tools.py:comparison_tiles` | The 3D pair of a component (u_r, u_z) got the component's signed joint range. The renderer colours the vector it draws by its norm (`funcdim==2 → eval=3`), so the scale clipped, and a range across zero reversed the colours of a magnitude | Fixed: `analysis.py:size_range`, the vector's size over both runs' nodes; the caption says so |
| 5 | Important | `assets/chart.js` | A drag that zooms ends in a click on `plot.over`, and the click handler then picked the sample under the pointer. On the I–V chart this picked a run and redrew, undoing the zoom | Fixed: only a click where the press was asks; the pick carries its y |
| 6 | Important | `analysis_tools.py:comparison_controls` | Changing a comparison's quantity kept the range typed for the previous one, in its unit | Fixed: the quantity is set with `range: None`, as the explorer's own quantity change does |
| 7 | Important | `analysis_tools.py:_kept` | The maps cache was read, filled and evicted from `run.io_bound` threads and the image routes' threadpool with no lock: two evictions at once raise KeyError | Fixed: `_MAPS_LOCK` |
| 8 | Important | `analysis_tools.py:comparison_tiles` | The page let `comparison_maps`' KeyError, a quantity one run lacks, and ValueError, fluids that do not overlap, escape; the image route catches both | Fixed: caught; the status says why the comparison does not draw |
| 9 | Nit | `gui/web/runs.py:queue_rebuild` | *Solve again* on a sweep member filed its entry under `runs`, the folder above a member's run in the store | Fixed: the explorer passes the choice's study |
| 10 | Nit | `gui/render.py:render` | The explorer's ranged scene and a comparison's ranged scene of one run evicted each other, so going between the two tools re-rendered each time | Fixed: the field's latest other ranged scene stays too, which keeps a run's scenes bounded at three of one field |
| 11 | Nit | `runs.py:_made_by` | `entry.get("rung")` ran on a rung entry that is not a mapping | Fixed |
| 12 | Nit | `analysis_tools.py:on_chart_pick` | An I–V point was matched by its bias alone, so a failed member or another run at that bias could win | Fixed: a run that ended well, at the bias and the current |
| 13 | Nit | `io/artefact.py:FIELD_NORMS` | The docstring named only the L2 norm | Fixed: all three numbers |
| 14 | Nit | `chart_view.py:_typed` | The hint read "From is below To" where From was not | Fixed: "From must be below To" |
| 15 | Nit | `plot/figures.py:_silence` | With every rung reporting and none stepping, the note still offered "takes no Newton callback" | Fixed |
| 16 | Nit | `runs.py:recorded_convergence` | The replay read only the store a record names, while `Project.run_state` reads the project's first: a project moved by hand showed no convergence for runs Analysis called solved | Fixed: Runs passes the project's store, read first |
| 17 | Nit | `render_shell.py:draw_analysis` | The render pre-drew an unranged scene and a joint-range pair, which the pages no longer ask for | Fixed: the explorer's opening map range and the pair's range, as the pages compute them |
| 18 | Nit | new code prose, `analysis.py` and others | Requirement identifiers in comments and docstrings, against `.claude/rules/python.md` | Fixed after the pass, which had skipped it: the fifteen in the package's prose are dropped; NUM-16, cited as the source of the floor's constant, stays |

Eighteen findings: eight important, ten nits, all fixed; the pass skipped the eighteenth, and the shipping session
fixed it. None changes a ruling of the author: finding 4 holds AU3's one range for the pair, on the quantity the
renderer colours. Finding 10 widens code review 064's bound by one scene.
