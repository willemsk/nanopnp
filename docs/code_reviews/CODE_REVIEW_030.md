# Code review 030: WP5.05, named models and study overrides

Reviewed head `bd255f0b67efdd7442903d751b2c3cbc4844713f` against base `4153bdd4f08906ea4a1a3d0d256a64a3c2e12c5a`
(PR 155). Status: completed. Static review at `xhigh`. Fifteen findings; eleven fixed, four recorded.

| # | Where | Finding | Outcome |
|---|---|---|---|
| 1 | `pipeline/run.py` | `stored_upstream` built every stage with `create(name)` and no store, and the mesh stage now keys a mesh named by `inputs.mesh.artefact` from the store. `api/sweep.py:_parent_artefact` calls it for every member with a parent, so in a sweep over a case naming a stored mesh every member but the roots failed with `ValueError` ("built without a store"). | Fixed: a stage that takes the store is built with it, as `_Walk.construct` builds it. |
| 2 | `io/models.py` | `_prune` kept a named model's block that the pruning emptied as `{}`. A study override that adds a supplied artefact the model lacks (`inputs.pqr`, `inputs.profile`) put `SuppliedArtefact()` in the view, which `_exactly_one_source` refuses, so the study was refused as "a model cannot be reused alone". `Case.with_({"inputs.profile.path": ...})` succeeded, and its `dumps(study=True)` then failed to read back, as a sweep or a model swap of it did. | Fixed: an emptied block of a named model is dropped from the view; a mixed block (`charge`, `inputs`) keeps `{}`. |
| 3 | `io/models.py` | `ModelRecord.carried` accepted a kind the study does not name. `study_layer` writes every leaf of an unnamed kind from the defaulted document, so each schema default overrode the newly named model: naming a continuum model whose `physics.variable_density` is `false` left it `true`, recorded as an override. | Fixed: refused, naming the path; §5.3.1's NOTE on `models:` and §5.3.4 say so. |
| 4 | `io/case_paths.py` | `substitute` moved only `models.<kind>` paths. A `models` assignment on a study (`with_(models=None)`, a sweep axis over `models`) was set into the payload and overwritten by `record.paths`, so it did nothing; and on a case naming no model, `with_({"models.continuum": ...})` validated a document whose `models:` no resolver read, equal to the case before it. | Fixed: a `models` mapping is taken as its `models.<kind>` paths, dropping the models is refused, and a case naming no model is refused naming the readers that resolve one; §5.3.1 says so. |
| 5 | `io/models.py` | `_resolve` ordered the origins `[continuum, molecular, study]` and `_origin` keeps the first of a tie, so a study's own invalid override was reported `[from <continuum file>]`, the file whose value it replaced. | Fixed: the study comes first, as the merge's precedence runs; the view's refusal reads the pruned study, so a model's value is never laid on the study. |
| 6 | `io/case_paths.py` | `with_profile` and `with_section` re-validated a dump that `models` is excluded from, so on a study they returned a plain case: its record, overrides and model files left the manifest. | Fixed: one helper, `_revalidated`, carries the record and recomputes the overrides for `substitute`, `with_profile` and `with_section`. |
| 7 | `io/models.py` | A study that drops a mixed block (`with_({"charge": None})`) records each model-owned leaf as an override to `None`, and its study form writes `charge: {ph: null, ...}`, which does not read back. | Recorded, REV-187: how a dropped shared block is written is the author's ruling. |
| 8 | `gui/render.py` | The renderers asked for the stage-6 artefact only when `resolved.mesh is None`, so a run on a stored mesh whose artefact had left the store fell through to `deployed_mesh`'s `KeyError` instead of the named refusal. | Fixed: `_mesh_need` asks for it unless the mesh is a supplied file; `deployed_mesh`'s docstring names the stored case. |
| 9 | `validation/comsol.py` | `_upstream` builds stages without a store, so a case naming a stored mesh has no mesh key there. | Recorded, REV-188: no frozen COMSOL case names a stored mesh. |
| 10 | `api/sweep.py` | `plan_sweep` resolves relative `models.*` axis values against the working directory, while `Case.with_` reads the same value beside the study. | Recorded, REV-189: a question for the author; the comment states the working directory as intended. |
| 11 | `io/case.py` | `CaseDocument` keeps pydantic's equality, which counts the `models` field and the record (compared by identity), against §5.3.1's "left out of every ... equality". `Case` is unaffected. | Recorded, REV-190: changing a frozen model's equality also moves its hash. |
| 12 | `api/case.py`, `io/case.py`, `io/models.py`, `sweep/plan.py` | Four new comments carried `FR-39` (and `WB-11`); `.claude/rules/python.md`: "Requirement identifiers live in the names of in-scope tests and commit messages, not in prose." | Fixed. |
| 13 | `tests/tier1/test_mesh_ingest.py` | The new test imported `yaml`, `Case`, `Session` and `Store` inside its body; `.claude/rules/python.md` defers only costly or optional packages. | Fixed: imported at the top. |
| 14 | `io/models.py` | `_blocks()` built a frozenset of every block path on each recursion of `_compare`, `_merge`, `_prune` and `_flat`, once per leaf of every `substitute`; `_rebased` rebuilt `_correction_leaves()` on every iteration. | Fixed: both cached. |
| 15 | `io/models.py` | `_leaves` repeated `_flat`'s walk. | Fixed: `_leaves` reads `_flat`, which takes a prefix. |

Not findings: `ModelRecord.attached` writes the private attribute of a frozen model, which pydantic allows; `models`
in `path_fields()` reaches no dump, since `input_paths` reads a dump `models` is excluded from; the stored mesh is
not gated at stage 6, and every consumer re-ingests and gates it through `deployed_mesh`; the sweep plan's skip of a
stored mesh's NUM-34 gate leaves the gate to the member's solve, as for a generated mesh.

Checked on the fixes: `ruff check`, `ruff format --check`, `mypy src/`, and Tier 1 without
`tests/tier1/test_gui_widgets.py` (1492 passed, 8 skipped). Each fix was reproduced before and after with a scratch
script over the quickstart and 2WCD examples split into models.

Not assessed: Tier 2 (`test_named_models.py`) and the walks, which `/np-ship` gates.
