# Code review 047: WP5.13's plan, case and model files

2026-11-10 · PR #176, branch `claude/upbeat-hamilton-hi7qux`, the plan commit `44d8e89` on `ae01061` · scope: the
commit's 5 files, read in full: `docs/plans/phase-5/wp5.13-case-and-model-files.md`, the Phase 5 plan,
`docs/plans/current.md`, `docs/plans/index.md`, `docs/project/decisions.md` · focus: each claim the plan makes about
the code against the code at the head; each decision against §5.3.1, §8.2.36 AL22 and AL23, and CODE_REVIEW_036's
settled designs D1.1 to D1.5, D5.1 and D5.2 with their corrections; how each verification row's test gets the object
it checks; the plan against `.claude/skills/np-plan/wp.md`'s caps and sections · status: completed.

Static review of a plan commit (`/np-plan wp 5.13 review`, `/code-review medium --fix`). No test or gate ran; the
review turn gates the fixes. Probed and found to hold:

- **Readers and imports.** `io/case.py:_validate` refuses `models` and `variables`. `validation/costs.py` calls
  `read_case` three times and is its only production caller; no test calls `read_case`, `read_case_text`,
  `item_inputs`, `rewrite_inputs`, `correction_paths` or `check_model_file`. `pipeline/case.py` imports `read`
  and `reads`, and `api/case.py` imports `reads`. The `io` imports already run `models` → `variables` →
  `case_paths` → `case`. The three readers' documents compare equal across `CaseDocument` and `Case`.
- **The edit.** `Case.with_` makes its two passes. `substitute`'s model branch returns before any rebase.
  `ModelRecord.carried` and `VariableRecord.carried` are as the grounding states.
- **Input paths.** `path_fields()` holds the seven input fields and the three `models.*` fields. Only
  `api/case.py:_rebased_paths` and `api/sweep.py:plan_sweep` call `input_paths`, and both merge it with
  `correction_paths`, so widening `input_paths` moves no other caller. `Project.embed` and `_export_plan` test
  `rewrite_inputs` for truth; `_rebase` and `_comparable` ignore its result.
- **Model files.** `ModelFile` is `eq=False` and holds `exposed`. `mapping_changes` carries each value in its
  `Change`.
- **Counts and spec text.** `substitute` has six callers without a base: three in `sweep/plan.py`, two in
  `validation/costs.py`, one in `gui/case_model.py`. §5.3.1 holds each sentence the plan replaces, wrapped
  across lines. `holds-now.yaml` gives AL22 `open: WP5.13, WP5.14, WP5.16, WP5.17` and AL23 `open: WP5.13`.
- **Caps.** The words fit before and after the fixes: 2,674 in all, 1,431 outside *Grounding* and *Implementation
  details*, 571 in the details, and an In brief of 273.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Medium | Verification, row 4 | Compares `mapping_changes` of the model file with that of `read_model_file(...).body`. The default body is rebased, so *Params* reads `params.yaml` in the file and an absolute path in the body. `Change.value` differs, and the assertion fails on correct code | Fixed: compared with the body read with `rebase=False` |
| 2 | Medium | Verification, row 1 | "The quick-start split in three … the study's record names three files". The quick-start has no molecular key, so `split_case` writes only `continuum.yaml` and `physics.yaml` | Fixed: the split by `split_case`, whose record names its two files |
| 3 | Medium | In brief | Says the project reads a model file's contents from the reader instead of parsing the file again for its changed list. D5, as CODE_REVIEW_036 D5.2 settled it, keeps `Project.changes` on `mapping_changes(_body(...))`; only the header stripping and `keep` go | Fixed: the record keeps its checked contents, and the changed list no longer strips the header itself. The rulings are unchanged |
| 4 | Low | Implementation details, item 3 | "whose import becomes `from nanopnp.io.models import read_case`". `validation/costs.py`'s line also imports `dump_case`, which stays in `io/case.py` | Fixed: `read_case` from `nanopnp.io.models`, `dump_case` kept |
| 5 | Low | Verification, rows 1 and 2 | Name `a` and `v` without definitions. Row 1 does not say whether its variables case is split; `split_case` would put the expression into `continuum.yaml`, which a model refuses | Fixed: `a: {value: 1, unit: nm}` on the inline quick-start; `v: {value: 50, unit: mV}` |
| 6 | Low | Decisions, D1 | "all at the top", but `io/case.py` keeps its `TYPE_CHECKING` import of `ModelRecord` and `VariableRecord` for annotations; an implementer could read it as an upward import to remove | Fixed: D1 says it stays |
| 7 | Low | Grounding, D1 | `SPLIT_BOUND` "caps `io/case.py` and `io/case_paths.py` (697 lines today)"; `io/case.py` has 852 lines | Fixed: both counts, each module capped at 1,266 |
| 8 | Low | Implementation details, item 5 | `tests/tier1/test_models.py:split_case` splits a case with its own `_leaves` and `_put`, which `split_case_layers` will own | Fixed: the helper builds its layers with `split_case_layers` |

Not findings:

- The `decisions.md` row for D6 runs its excerpt into the *Why/source* column. That is `decisions.py`'s excerpt of
  a short choice, the same for every plan, not the plan's text.
- The phase plan's WP5.13 entry still says the project "parses no model file again (D5.2)", quoting the ruling. The
  plan's *Planned* note beside it says the project still reads the files it copies or edits.
