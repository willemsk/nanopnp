# Code review 048: WP5.13, case and model files

2026-11-10 · PR #177, branch `claude/gallant-goldberg-dt74nq`, head `d0a8d5e` on base `ae01061` · scope: the PR's
23 files, the code and tests read in full with each touched function, every caller of a changed or removed name
(`input_paths`, `rewrite_inputs`, `rebase_inputs`, `read_case`, `read_case_text`, `read_model_file`,
`split_case_layers`, `mapping_changes`, `substitute`), the specification, traceability and register edits · focus:
whether the one reader, the one substitution and the one input-path seam hold today's behaviour (AL22, D6), and what
the moved split and model-file reader carry with them · status: completed.

Static review (`/np-ship wp 5.13`, `/code-review xhigh --fix`). No gate, benchmark or nightly walk ran; `/np-ship`
gates the fixes. Ruff, mypy on the five edited modules and `tests/tier1/test_models.py`, `test_case.py`,
`test_project.py`, `test_case_fields.py` and `test_variables.py` ran on the fixed tree and pass.

Probed and found to hold: one script ran 23 edits and 4 imports against `main` (`ae01061`, as a worktree) and the
head, each in one folder. It covered `with_()`, an edit, `substitute(case, {})`, a relative edit, a swap of either
model, a swap with an edit, a swap after an edit, and variable edits. It ran each on a plain case, a case with
variables, a study with a relative override and a study with variables, then imported each into a project and read
back `changes`, `problems` and `linked`. Every hash, dump, study form, override, expression, written item file, changed
list and problem is byte-identical before and after, and again after this review's fixes. `rebase_inputs` skips
`models.*` in each branch, so no model path is rebased twice. `read_mapping` validates a plain case without rebasing
it, so `validation/costs.py` reads 2WCD's relative structure path as `io/case.py:read_case` did. No test, guide,
knowledge concept or example names a removed reader or helper.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | High | `io/models.py:split_case_layers`, `api/project.py:Project._split` | The split sends a leaf to the study only when its path equals a pinned expression path, and gives the owning model nothing. A case writing `bias_V: v` imports a physics model without `bias_V`, so `_verify` refuses it ("do not form a case"). A case writing `electrolyte.species.0.z: zz` puts the expression in the physics model, since `leaves` yields the list whole; `read_model_file` refuses that. §5.3.5 says the study resolves to the case it was split from. The fault predates WP5.13 and is identical at `main`; `study_layer` pins by prefix and keeps the model's number | Recorded, REV-233: the fix changes the model files every import with an expression writes, against D6, so the author rules on it. The author ruled to fix it in WP5.13; `/np-ship` fixed it afterwards (REV-233 `fixed`) |
| 2 | Low | `cli/reference.py`, the `models` notes | `nanopnp reference` and the generated case-file reference still say "a reader that does not resolve models refuses the block". D1 removed that reader, and §5.3.1 now says every case reader resolves `models:` | Fixed: "every reader of a case file resolves the block" |
| 3 | Low | `io/models.py:read_model_file` | The refusal of an expression in a model file walks the body with `entered[part] if isinstance(entered, Mapping) else entered`. That walk does not descend a list, so an expression at `electrolyte.species.0.z` reports the whole species list as what "you entered". `_value_in`, in the same module, already walks lists | Fixed: `entered = _value_in(body, expression)`; the refusal now names `'zz'` |
| 4 | Low | `io/models.py:split_case_layers`, `io/defaults.py:_METADATA_KEYS` | A file's metadata keys are written twice: the split hard-codes `("schema", "name", "models")` and `defaults.py` builds `{*HEADER_KEYS, "models"}`. The two already differ on `exposes` | Fixed: `io/models.py:METADATA_KEYS` beside `HEADER_KEYS`, read by both. A valid case holds no `exposes`, so no split moves |
| 5 | Low | `api/project.py:Project._problems_of` | Checks each model file with `read_model_file(kind, location)`, whose default rebases every relative input path by `Path.resolve()`, for a body it discards. A resolve that raises `OSError` or `RuntimeError` is outside the four exceptions the check catches | Fixed: `rebase=False`; the refusals are raised before the rebase, so none moves |
| 6 | Low | `io/project.py`, the module docstring | Still says the module holds "the paths an item of a project names". Those functions, `item_inputs` and `rewrite_inputs`, moved to `io/case_paths.py` (D2); the module keeps the project file, its folders and item names and references | Fixed: the docstring names what the module holds, without the identifier `.claude/rules/python.md` keeps out of prose |
| 7 | Low | `specification/a-traceability-matrix.md`, FR-34 | The plan's Verification row 4 tests FR-34's changed list (`mapping_changes` of a model file and of its body, `models:` never a change), but only FR-39's and FR-25's rows name the new tests | Fixed: FR-34's row names `tests/tier1/test_models.py` for WP5.13 |
| 8 | Low | `io/models.py:ModelFile.body` | The record is `frozen`, but `body` is the mutable dict `read_model_file` built. Every document a study derives shares it through `ModelRecord.attached`, and `_merge` places its nested dicts by reference into the merged mapping when one model holds a block alone. No code mutates either today; a suite that edits `files[i].body` in place would change every derived record | No change: nothing mutates it, and WP5.15, the first suite to read the body, decides whether to copy it |
| 9 | Low | `io/case_paths.py:_cursor`, `input_paths` | `input_paths` accepts any `Mapping`, and copies the top level with `dict(source)`. `_cursor` descends only `dict`, where the removed `io/project.py:_at` descended any `Mapping`, so a nested non-dict mapping would hide its paths | No change: every caller passes a parsed YAML body or a `model_dump`, which are dicts throughout |

Not findings:

- `decisions.md` moves REV-217 and REV-219 from "author" to "session, own call" and the author count from 514 to 512.
  `decisions.py` reads the decider from the ruling column, which becomes the WP link, as for every REV row a package
  fixed (REV-01 onward).
- `validation/costs.py` passes `model=CaseDocument`, the default. Without it, mypy has no argument to bind the
  reader's type variable to and asks for an annotation of the result (probed).
- `tests/tier1/test_models.py:split_case` now skips `None` leaves, as `Project._split` did; the old helper wrote
  them. No model or study file the tests compare depends on a written `null`.
