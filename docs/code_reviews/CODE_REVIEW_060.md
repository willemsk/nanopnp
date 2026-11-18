# Code review 060: WP5.19, the Study suite

2026-11-18 · PR #189, branch `ccr-ff91f6e7-ohlzgc`, head `e0332dd` on base `096f7fa` · scope: the package's 88 files,
the source and tests read in full through ten angles (line by line, removed behaviour, callers, language pitfalls,
wrappers, reuse, simplification, efficiency, altitude, conventions) and a sweep: `api/reproduce.py` (`upto`, the
charge group, the cached-store guard), `api/project.py` (`new_study`, `set_study_value`, `set_variable`,
`study_values`, `_checked_study`, `export` and its plan), `api/sweep.py` (`run_point`'s hooks), `sweep/plan.py`
(`_pairs` after the resolve), `sweep/run.py` (`pin_threads`), `pipeline/case.py` (`_outline_spacing`,
`_outline_h_c`), `pipeline/checks.py` (`check_exclusion_offset`), `io/resolved.py` (`shell_spacing_nm`),
`geometry/region.py`, `solve/stage.py` (`_threads`), `pipeline/run.py` (`RunResult.threads`), `plot/data.py`
(`ResidueCharges`), `gui/solver.py` (`_worker`, `_member`), `gui/render.py` (`render_charge_elements`), and
`gui/web/` (`study.py`, `study_tools.py`, `runs.py`, `queue.py`, `builds.py`, `frame.py`, `pages.py`, `plane.py`,
`molview.py`, `tools.py`, `physics_tools.py`, `states.py`, `settings.py`, `screens.py`, `bridge.js`, `plane.js`) ·
level: xhigh, with `--fix` · status: completed.

Static review: no benchmark, sweep or `gate.sh` ran. Finding 1 was reproduced on the charged tube walked to its
charge, `reproduce(upto="mesh")` and `upto="protonation"` refused, and passes after the fix; finding 5's guard was
run the same way. `tests/tier2/test_reproducibility.py` (13) and the study, runs and export tests of Tier 1 (7) pass
after the fixes; `ruff` and `mypy` are clean on the edited modules. `/np-ship` gates the fixes.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | High | `api/reproduce.py`, `reproduce` | `upto` short of stage 7 on a run that reached it compares the manifest's charge group against a walk that did not run stage 7; `compare` refuses it as "a changed case rather than a changed number", so `nanopnp reproduce --upto mesh` fails on every charged run | Fixed: the charge group is compared where the walk reached the record's last stage or ran stage 7 |
| 2 | Medium | `gui/web/runs.py`, `_queued`; `queue.py` | A sweep's dataset is collected only from a member's `poll`; a member dropped before it starts, or one whose start is refused, ends without it, so a sweep whose last members end that way is never collected | Fixed: `Entry.then`, called by `Queue.set` once as the entry ends, however it ends |
| 3 | Medium | `gui/web/study_tools.py`, `_written` | Each axis is named by its path's last part, so axes over `geometry.pore.radius_nm` and `geometry.reservoir.radius_nm` share a name; `write_sweep` writes a file its loader refuses, Sweep then shows no axis, and the next axis added overwrites the file | Fixed: a taken name gives way to the whole path; `write_sweep` reads the document back before it writes |
| 4 | Medium | `gui/web/study_tools.py`, `_sweep_rows`, `_written` | An edit of any row rewrites every axis without its `origin` or its file's name, so a hand-written sweep's warm-start forest is re-rooted at index 0 and its warnings no longer match their rows | Fixed: each axis keeps its name and, while its values reach it, its origin; the warnings match by the written name |
| 5 | Medium | `api/reproduce.py`, `reproduce` | The QR-08 guard refuses a served solve only; `upto` short of the solve into the store that holds the run serves every stage and reports the run reproduced, comparing the record with itself | Fixed: a walk with no solve whose every stage was served is refused, naming the store |
| 6 | Low | `gui/web/study_tools.py`, `picked_run` | The run opened from the frame's queue is looked for among the study's last 12 entries only; *Open* on an older one shows the last run's convergence | Fixed: looked for among every entry, and listed first when older |
| 7 | Low | `api/project.py`, `_export_plan` | An input no item names is placed at `source.resolve().relative_to(inputs/)`, which raises for a link in `inputs/` to a file outside it | Fixed: placed at its path as listed |
| 8 | Low | `api/project.py`, `_report_path` | A copy exported without its store records no store, so a second export of that copy puts two results of one name from different report folders at one path, and one is lost | Fixed: a result under the run's own `results/` keeps its path there |
| 9 | Low | `api/project.py`, `_write_export` | With `store=True` on a project that holds no store, each copied record names a store the copy lacks | Fixed: the store is named only where it is copied |
| 10 | Low | `gui/web/study_tools.py`, `_parsed` | YAML 1.1 reads `1e-3` as text, so an exponent typed without a point is written as a string, and a variable typed so becomes an expression | Fixed: an exponent with no point reads as its number |
| 11 | Low | `gui/web/study_tools.py`, `variable_rows` | *New variable* has no unit: every variable defined in the pane is dimensionless, and one used at a field with a unit, as `boundary_conditions.bias_V`, is refused | Open: REV-263 (a control of the pane's design) |
| 12 | Low | `pipeline/checks.py`; `gui/case_model.py` | The exclusion-offset refusal moved from `check_document` into `resolve`, so `Case.load` and the case editor's `commit` accept an offset at most `2 h_c` beside a derived outline, which they refused before; `commit`'s comment says it refuses what the CLI refuses | Open: REV-263 (whether the derived outline's half stays at load) |
| 13 | Low | `gui/web/study_tools.py`, `plan` | Sweep builds the plan, resolving every point, and its forecast, keying every member's walk, in both `show_axes` and `sweep_view`, on the event loop, and again at each move of the queue | Open: REV-263 (a cache must follow the store as well as the files) |
| 14 | Low | `gui/web/study.py`, `records`, `charge_record` | Charge on the mesh's refresh signature reads every run record of the study each second | Open: REV-263 |
| 15 | Low | `plot/data.py`, `ResidueCharges.at` | One kernel call per near atom in a Python loop; the kernel is elementwise, but its signature takes floats, so a vector call needs `charge/kernel.py`'s signature widened | Open: REV-263 |
| 16 | Low | `solve/stage.py`, `_threads` | The count is `OPENBLAS_NUM_THREADS` alone, so a run pinned through `OMP_NUM_THREADS` or `MKL_NUM_THREADS` alone records `None`, the libraries' own default | Not changed: D7 and FR-25's text name the variable; the pane and pool pin all three |
| 17 | Low | `gui/web/study_tools.py`, `_table`, `_range` | Both re-implement `tools.py`'s `_view_table` and `_range`, which the same package added | Fixed: `_view_table` takes the table's control, and Study calls both |
| 18 | Low | `gui/web/study_tools.py`, `study_entries` | Its branch for a run entry with no study is dead, every run entry carrying its study, and its prefix match would list study `ab`'s runs under `a` | Fixed: matched by the study alone |
| 19 | Low | `gui/web/study_tools.py` | `_science`, `_sets`, `_default` and `_parsed` carry docstrings, which `.claude/rules/python.md` (in-code prose, which `CLAUDE.md` names) gives no private code: "No docstring on a test or on private code" | Fixed: a comment where the code cannot say why |
| 20 | Low | `gui/web/` (6 modules) | Twenty requirement identifiers, WB-21 to WB-48, REV-255 and VER-44, were added to comments and docstrings; `.claude/rules/python.md`: "Requirement identifiers live in the names of in-scope tests and commit messages, not in prose" | Fixed: the identifiers taken out of the Python; `frame.css`'s comment is outside the rule |

Not findings:

- `threads` in the solve's summary moves no key: `Artefact.hash` covers the schema, parameters and inputs only, and a
  solve served from the store states the count it was solved with, as VER-62's test asserts.
- `pin_threads` runs before the spawned child imports anything that loads NumPy or NGSolve.
- `_pairs` dumps each member without `name`; `exclude={"variables"}` names no field, and the variables are outside the
  dump already, so the key is the resolved case less its bias.
- `render_charge_elements` takes the solve's own rule order for the charge; its means times each element's volume of
  revolution sum to `q_mesh_e`, which VER-60's test checks to 10⁻¹².
- `_outline_h_c`'s bound is named the right way round: a spacing held down is held at the coarsest grid.

## Fixes

| File | Change |
|---|---|
| `src/nanopnp/api/reproduce.py` | Findings 1, 5 |
| `src/nanopnp/gui/web/queue.py` | Finding 2 |
| `src/nanopnp/gui/web/runs.py` | Findings 2, 3, 20 |
| `src/nanopnp/gui/web/study_tools.py` | Findings 3, 4, 6, 10, 17 to 20 |
| `src/nanopnp/gui/web/tools.py` | Findings 17, 20 |
| `src/nanopnp/api/project.py` | Findings 7 to 9 |
| `src/nanopnp/gui/web/frame.py`, `physics_tools.py`, `screens.py` | Finding 20 |
| `docs/project/review-findings.md`, `review-items.md` | Findings 11 to 15 in REV-263 |
