# Code review 049: WP5.14's plan, sweep planning and the walk's keying

2026-11-10 · branch `ccr-af640486-wb2fom`, the plan commit `0962016` on `d3420d8` · scope: the commit's 5 files, read
in full: `docs/plans/phase-5/wp5.14-sweep-planning-and-the-walks-keying.md`, the Phase 5 plan, `current.md`, the plan
index and `decisions.md`; against the code at the head: `sweep/plan.py` (`SweepPlan`, `build_plan`, `read_plan`),
`api/sweep.py` (`plan_sweep`, `_parent_artefact`, `run_point`, `run_plan`, `_worker`, `_pool`, `_announce`, `Sweep`),
`api/session.py` (`_walk`, `_member`, `own_stages`), `pipeline/run.py` (`_Walk`, `_resolve_stage`, `run_document`,
`stored_upstream`, `_walk`), `pipeline/forecast.py`, `sweep/forecast.py`, `pipeline/case.py:resolve`,
`io/models.py:ModelRecord.carried`, every caller of `stored_upstream`, `run_document`, `keyed_walk` and
`resolved_members`, and the tests the Verification rows extend (`test_forecast.py`, `test_sweep_plan.py`,
`test_stages.py`, `test_layering.py`) · focus: each claim about the code, each decision against CODE_REVIEW_036's D2.1
to D2.4, D6.1, D6.2 and C2.1 to C6.1 and AL22, each row's way to its object, and `wp.md`'s sections and caps · status:
completed.

Static review (`/np-plan wp 5.14 review`, `/code-review medium --fix`). No test or gate ran; the review turn gates.

Found to hold: thirteen preparations become six (3 to plan, 3 for the forecast beside the store's directory, 0 for the
run, whose `_announce` fills the held members); `run()` resolves 7 today (3 members, 2 parents twice). `Session._walk`'s
callers are `Session.run` and `run_point`; `stored_upstream`'s are `_parent_artefact`, `gui/assess.py` and
`test_case_fields.py`; only `sweep/forecast.py` imports `pipeline/forecast.py` and only it reads `resolved_members`.
An own stage is walked after the pipeline, so passing `session.own_stages` to `_parent_artefact`'s lookup moves no
solve key. A `models.*` swap on a case without `models:` is refused by `ModelRecord.carried`'s absence at resolve, so
D1's `.` for a non-study base loses no refusal. The caps hold: 2,718 words, 1,571 outside *Grounding* and
*Implementation details* (cap 1,650), 521 in the latter; the In brief is 263 words. §5.3.4's quoted sentence is there
verbatim, and amending it with item 3 follows WP5.13's precedent.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Medium | D2, item 2 `held_member` | `_resolved_beside` was compared with `base_path.parent` as written. `resolve` reads a relative `base` through `Path.resolve()` against the working directory, and D3 now serves held members to the run, where `run_point` resolved afresh before. A plan with a relative base path run after a `chdir` would run members resolved against the old directory, with a manifest naming the new one | Fixed: the fields hold `beside.resolve()`, compared with `base_path.parent.resolve()`; a grounding bullet states why |
| 2 | Low | Verification row 2 | The row read `b/params.yaml` "from both `resolved_members` and `held_member(0)`". `held_member` never resolves, so on the moved plan it is `None` until `resolved_members` runs; an implementer asserting `held_member(0)` first fails, or weakens the row to pass | Fixed: `held_member(0) is None` after the move, then `resolved_members`, then `held_member(0)` |
| 3 | Low | Verification row 1 | Counting only from after `plan_sweep` returns leaves the planning third of "thirteen become six" unchecked: a `build_plan` that resolved every member twice would pass | Fixed: `plan_sweep` records each name once, then `forecast()` and `run()` once more |
| 4 | Low | D5, item 1 | Name `_resolve_stage`'s "`only` branch"; the function's parameter and branch are `substitute` (`walk.only and index < len(stages) - 1`) | Fixed: "`substitute` branch" in both |
| 5 | Low | D1 | "Given `base`, it reads no file" overstates C2.1: the plan still checks model files, digests the input files and gates the meshes | Fixed: "reads no file at the base path", as the item's *Parameters* line says |
| 6 | Low | D1, D2 | The in-memory plan's members are held beside the study's directory for a study and beside `.` otherwise, while its `base_path.parent` is `.`: a study's pre-move plan serves none of its members, and its `resolved_members` would load `./base.case.yaml`. Harmless only because `plan_sweep` reads that plan for its hash alone | Fixed: a grounding bullet states it, so no later caller relies on the pre-move plan |
| 7 | Low | Item 3 | Deleting the staging directory leaves `plan_sweep`'s `sweeps = store.root / "sweeps"` and its `mkdir` as dead code; `directory.mkdir(parents=True)` makes the folder | Fixed: item 3 deletes the `sweeps` lines too |
| 8 | Low | Execution brief, D2 | Cited AC1 as "a caller reads no private field". AC1 rules that `Session` reads no private field of `Case`, and `run_point` already calls `session._member()._walk` | Fixed: AC1 cited for a public read, as it gave `Session` for `Case` |
| 9 | Low | D6 | `pipeline/run.py` grows from 1,230 lines past 1,300 with the moved module, above the 1,266-line bound MOD-13 set for the `io` split's modules. No guard covers `run.py`, as the grounding says | No change: D6 is the author's ruling, and no clause bounds `run.py` |

Not findings:

- `current.md`'s "tag `.13` unpushed": `.10` to `.12` are on `origin`, and `.13` is not yet made.
- `decisions.md` counts 7 new author rows; regenerated after the fixes, and `links.py` finds no broken path.
