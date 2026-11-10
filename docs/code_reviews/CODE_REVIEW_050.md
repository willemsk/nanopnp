# Code review 050: WP5.14, sweep planning and the walk's keying

2026-11-10 · PR #179, branch `ccr-7c47497f-c6db5h`, head `1629949` on base `58e64ae` · scope: the PR's 19 files, the code
and tests read in full with each touched function (`pipeline/run.py`: `_Walk`, `_keying_walk`, `_given`,
`_resolve_stage`, `run_document`, `stored_upstream`, `keyed_walk`, `_forecast_digest`; `sweep/plan.py`: `SweepPlan`,
`build_plan`, `read_plan`, `_gate_meshes`; `api/sweep.py`: `plan_sweep`, `_parent_artefact`, `run_point`, `run_plan`,
`_announce`, `_pool`, `Sweep`; `api/session.py:_walk`, `_member`; `sweep/forecast.py`), every caller of a changed or
removed name (`stored_upstream`, `run_document`, `keyed_walk`, `resolved_members`, `held_member`, `build_plan`,
`pipeline.forecast`), `pipeline/case.py:resolve`, `io/case_paths.py:substitute` and `input_paths`, the CLI's sweep
actions, the specification, traceability and register edits · focus: whether the in-memory plan, the members keyed on
their directory and the one keying walk keep every key, refusal and warm start (AL22, D7) · status: completed.

Static review (`/np-ship wp 5.14`, `/code-review xhigh --fix`). No gate, benchmark, sweep or nightly walk ran;
`/np-ship` gates the fixes. Ruff and mypy on the edited modules, and `tests/tier1/test_sweep_plan.py`,
`test_forecast.py`, `test_stages.py`, `test_models.py` and `test_variables.py` (58 tests), ran on the fixed tree and
pass.

Probed and found to hold: one script planned a two-value bias sweep with `plan_sweep` from each example case file,
against `main` (`58e64ae`, as a worktree) and the head. Thirteen of the fifteen plan; example 03's two ask for a
rectification that two positive biases cannot pair, and both trees refuse them. Every plan hash, base hash and planned input
file is identical, so no sweep directory moves, and on the head the store's copy of each base passes `base_case()`. An own stage
walks after every stage of the pipeline, so passing `session.own_stages` to `_parent_artefact`'s lookup moves no solve
key. `_given` refuses a resolved case of another document, and every caller passes `resolved.document` with it.
`_resolve_stage` handles a `key_is_artefact` stage before its `substitute` branch, so `_Walk.stored` changes no
count of hits or misses there.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Medium | `api/sweep.py:plan_sweep`, `sweep/plan.py:build_plan` | `plan_sweep` refuses a relative input path in the case, not in an axis value. The staging directory refused one by accident: the members were resolved beside it, where no such file is. Planned in memory, a non-study's members are resolved beside `.` and a study's beside its directory. Probed: a cylinder swept over `electrolyte.parameters: [params.yaml, willems2020_nacl]` from a folder holding `params.yaml` is now planned. The working directory's file enters the plan's digests and hash, and then every member fails to resolve beside the store's copy (`no correction file at …/sweeps/cylinder-…/params.yaml`). At `main`, the plan was refused before anything was written | Fixed: `plan_sweep` refuses an axis value naming an input file by a relative path, as it refuses one in the case, through one `_relative_inputs` helper. Models and variables are not inputs and are skipped. A value that `substitute` refuses is left to `build_plan`'s own refusal. The probe now ends in that refusal. `CHANGELOG.md` says so. Reading such a value beside the case file, as §5.3.1's NOTE on a relative path reads an edit, would be a ruling for the author (REV-189 was one for `models.*`) |
| 2 | Low | `tests/tier1/test_stages.py:test_fr27_the_upstream_lookup_keys_own_stages_as_the_walk_does` | The test feeds `elements`, which `stored_upstream` drops with `[:-1]`, so no stage of one's own is keyed. Mutated so that `_Walk.keyed` ignores `own`, the test still passed: it shows only that `selected_stages` receives `stages` | Fixed: a second stage `tally(elements)` is fed, so `elements` is keyed through `_Walk.keyed` and read through `_Walk.stored`. The mutation now fails the test. Verification row 3 says so |
| 3 | Low | `sweep/plan.py:build_plan`, the `base` parameter | The docstring says that no file is read at the base path. It does not say where the members of an in-memory base are resolved: beside a study's directory, and otherwise beside the base path's directory, which is `.` (the working directory) when there is no `source` | Fixed: the parameter's line says so |
| 4 | Low | `docs/plans/current.md`, the In brief | "a sweep planned from Python prepares its points six times where it took thirteen". Those counts are for the three-point test sweep; in general the cost is two resolutions per member where it was about four | Fixed: "a three-point sweep" |
| 5 | Low | `docs/plans/index.md` | Item 6 changed the status lines of the WP plan and the Phase 5 plan but did not run `index_records.py`. The index still quotes WP5.14 as "planned, not started" and the phase as "the clean-up WP5.14 planned" | Fixed: the index is regenerated, along with `docs/code_reviews/index.md` for this report |
| 6 | Low | `api/sweep.py:plan_sweep` | The plan's `base_hash` is now the in-memory case's hash, where it was the hash of the store's copy read back. A case whose `dumps(study=…)` text did not read back to the same hash would plan, write its directory, and then have every member refused by `base_case()` | No change: the probe above shows identical hashes for every example, and Verification row 4 checks a plain base and one with variables. No case was found that fails to round-trip |
| 7 | Low | `api/sweep.py:plan_sweep` | `replace(planned, base_path=…)` carries over the members resolved beside `.` or the study's directory. `held_member` never serves them, and they stay in memory until the first `resolved_members` replaces them | No change: C2.2 keys the members on their directory rather than dropping them, and a one-axis sweep holds a few members |
| 8 | Low | `sweep/plan.py:SweepPlan.resolved_members`, `held_member`; `pipeline/run.py:_forecast_digest` | The check that members are held and beside the base is written twice, and `_forecast_digest` takes `resolved` beside `inputs`, whose `resolved` it is | No change: both are D2's and item 1's sketches as written, two lines each |
| 9 | Low | `specification/05-software-design/03-4-sweeps.md`, `api/sweep.py:run_point` | "The forecast and a run in the same process read those members." A plan from `plan_sweep` that is run through `run_plan(…, indices=…)`, or through `run_point`, before any forecast resolves each point and its parent: only `resolved_members` resolves a moved plan's members again. `Sweep.run` forecasts first, so its run reads them | No change: D3 rules that a member resolves only its point and its parent, and the sentence holds for `Sweep.run` and for a whole plan run in the process that planned it |

Not findings:

- `decisions.md` moves REV-220 and REV-221 from "author" to "session, own call", and the author count from 519 to 517.
  `decisions.py` reads the decider from the ruling column, which becomes the WP link, as for every REV row a package
  fixed.
- `pipeline/forecast.py` is gone (D6). Only dated records name it: the plans, the reviews, `CHANGELOG.md`'s alpha.7
  entry and `decisions.md`.
- `pipeline/run.py` is 1,391 lines; MOD-13's bound covers only the modules of the `io` split (CODE_REVIEW_049, 9).
