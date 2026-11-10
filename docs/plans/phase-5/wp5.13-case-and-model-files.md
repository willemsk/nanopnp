# WP5.13 — Case and model files

**Status: delivered, 10 November 2026.** Planned 10 November 2026 on `main` (`ae01061`). It inherits §8.2.36 AL22 and AL23,
and CODE_REVIEW_036's candidates 1 and 5 with their corrections C0 to C1.5 and C5.1, settled with the author on 6 and
7 November 2026.

This plan belongs to [the Phase 5 plan](phase-5-workbench.md). `SPECIFICATION.md` governs. An identifier here points to
a clause and never restates it.

## In brief

**What changes.** Nothing a user computes or sees moves. Inside the library, reading a case file becomes one reader
that understands named models and variables, in place of two readers, one of which refused them. Editing a case in
Python takes one pass instead of two. The files a case names are found in one place instead of four, and a model
file's record keeps its checked contents, so the project's changed list no longer strips the file's header itself. The suites that
follow then extend one place each. Two refusal messages get shorter: asked to give a model or a variable to a case
that has none, they say to write it in the case file.

**Cost.** About five sessions, three to six agent hours and eight of your touches, the specification's estimate for a
clean-up package. No new library, and no change in speed.

**What could go wrong.** The new reader could resolve a case slightly differently, which would rebuild stored results.
Every stored fingerprint and the recorded example numbers are checked, and a moved one is undone, never re-pinned. An
edited case could read a file beside the wrong folder. A test covers each kind of edit: a plain case, a case with
variables, and a study with one of its models swapped. Planning found one kind the reviewed design missed; the plan
covers it. Importing into a project could write different files; the existing import tests compare the keys and the
files.

**Your call.** None. You settled the designs on 6 and 7 November and placed them here on 8 November. The plan's own
two choices keep today's behaviour.

## Execution brief

**Scope.** REV-217 and REV-219: CODE_REVIEW_036's candidates 1 and 5, re-read against WP5.09's code. **Depends on:**
WP5.09 (merged). WP5.14 follows in this lane. **Requirements:** FR-39, FR-25, FR-32, FR-34, IF-03; VER-61, VER-62,
VER-72. **Constrained by:** AL22 (no key and no golden moves), F4 and G6 (`nanopnp/case/v0.6` stays), MOD-13's split
bound, `.claude/rules/python.md` (imports at the top). **Implementing session:** Sonnet, high effort. Tag
`v0.6.0-alpha.13`.

**Amended when it lands:** §5.3.1's NOTE on `models:`, its substitution sentence in item 2 and its reader sentence in
item 3 (AL23; D1.3), and its NOTE on `variables:` in item 3 (AL23). The plan's commit amends no clause.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 One reader pair | `io/models.py:read_case(path, *, model)` and `read_case_text(text, *, base, source, model)` replace `read` and `reads`. `io/case.py` keeps `validate_mapping` and loses `read_case`, `read_case_text` and `_validate`. `pipeline/case.py:load_case` and `loads_case` stay the registry-checked seams. The `io` case modules import one way, `models` → `variables` → `case_paths` → `case`, all at the top; `case.py`'s `TYPE_CHECKING` import of the two records stays, for annotations | CODE_REVIEW_036 D1.1, D1.2, D1.5 and C1.5, ruled by the author on 7 November 2026; AL23 |
| D2 One input-path seam | `io/case_paths.py` holds `_cursor`, `input_paths(source)` over a document or a mapping (the path fields without `models.*`, and the correction files a case names by path), `rewrite_inputs(body, rewrite) -> bool` and `rebase_inputs(body, base)`. `correction_paths`, `io/project.py:item_inputs` and its `rewrite_inputs`, `io/models.py:_rebased` and `_correction_leaves`, and `api/case.py:_rebased_paths` go, and so does every merge of the first two | D1.4 and C1.3, ruled by the author on 7 November 2026 |
| D3 One substitution | `substitute(document, assignments, *, base=None)`. A `base` rebases the relative input paths after the edits in each branch: the model swap (`ModelRecord.carried` gains `base` and rebases the study layer before `_resolve`), the variables branch (`VariableRecord.carried` gains `base`) and the plain one. `Case.with_` calls it once. The two refusals say "write models: in the case file" and "write variables: in the case file" | D1.3, C1.1 and C1.2, ruled by the author on 7 November 2026; decided by the plan for the swap branch, which the reviewed sketch returned unrebased |
| D4 A model file carries its body | `ModelFile.body` is the merge layer: the owned keys without `HEADER_KEYS`, rebased beside the file unless `rebase=False`. `read_model_file(kind, path, *, rebase=True, source=None)` replaces `_read_model_file` and `check_model_file`, and `_resolve` merges `found.body`. `Project._copy_model` still reads the file as written | D5.1 and C5.1, ruled by the author on 7 November 2026; decided by the plan for `_copy_model`, since a copy keeps `exposes:` and the relative paths as written |
| D5 The split and the changed list | `io/models.py:split_case_layers(raw, *, pinned)` splits a case by `owner_of`, using the module's `_put`. `Project._split` calls it, and `api/project.py:_put` goes. `mapping_changes` skips each path whose first component is a header key or `models`, and `api/project.py:_body` loses `keep` | D5.2, ruled by the author on 7 November 2026 |
| D6 Nothing moves | No artefact key, golden, layering edge or public name changes. `modularity-layering.yaml` and `nanopnp.PUBLIC` are untouched. Only the two substitution messages change | AL22, ruled by the author; VER-61, VER-62, VER-72; decided by the plan for what is checked |

### Grounding

**D1.**
- `io/case.py:_validate` refuses a mapping that holds `models` or `variables`, then calls `validate_mapping`. Its
  only production callers are `read_case` and `read_case_text`, which `validation/costs.py` calls three times, on the
  quick-start and on 2WCD. Neither case holds models or variables, so the resolving reader returns equal documents.
  No test calls either reader or the refusal.
- `io/models.py:read` resolves the file and reads it beside its directory through `reads`, which calls
  `read_mapping`. `read_mapping` resolves the variables first, then the models. `VariableRecord.carried` also calls
  it, so it stays.
- `pipeline/case.py:load_case` and `loads_case` call `read` and `reads`, then `check_document`. `api/case.py:Case.loads`
  calls `reads(text, base=..., source=..., model=cls)`.
- `io/case.py` imports `io/models.py` only under `TYPE_CHECKING`. `models.py` imports `case`, `case_paths` and
  `variables` at the top, `variables.py` imports `case` and `case_paths`, and `case_paths.py` imports `case`.
- `tests/tier1/test_layering.py:SPLIT_BOUND` caps `io/case.py` (852 lines today) and `io/case_paths.py` (697) at 1,266 each.

**D2.**
- `path_fields()` returns seven input fields and `models.molecular`, `models.continuum` and `models.physics`.
  `input_paths(document)` walks a `model_dump`, where `models` is excluded, so it never meets `models.*`; a mapping
  does.
- `correction_paths(document)` keeps `electrolyte.parameters` and each `corrections.<property>.model` that
  `names_a_path`. `api/case.py:_rebased_paths` and `api/sweep.py:plan_sweep` merge the two.
- `io/models.py:_rebased` walks `path_fields()` and the correction leaves of a model body, `models.*` included, but
  `_read_model_file` refuses a model holding `models:` before it rebases.
- `io/project.py:item_inputs` skips `models.*` and an installed correction name. `rewrite_inputs` returns the changed
  paths. `Project.embed` and `_export_plan` test the result for truth; `_rebase` and `_comparable` ignore it.
  `Project.linked` and `_problems_of` call `item_inputs`.
- `io/models.py:ModelRecord.check_dropped` calls `_cursor`.

**D3.**
- `Case.with_` calls `substitute` and `check_document`, then `_rebased_paths(edited, self._base)`, which is empty when
  `_base` is `None`, then `substitute` and `check_document` again.
- `substitute` has three branches. A `models.*` path goes to `record.carried(document, moved)`, which returns when
  nothing else is assigned; a case with variables goes to `variables.carried`; otherwise it edits a dump and calls
  `_revalidated`.
- A swap-only `with_` today rebases the study's own relative paths in its second pass. Probed at `ae01061`: a study
  overriding `electrolyte.corrections.diffusivity.model` with `params.yaml` gets it absolute from
  `with_({"models.continuum": …})` and as written from a bare `substitute`. The reviewed sketch returns from the model
  branch first.
- `ModelRecord.carried` builds `study_layer(document, self)`, drops `models` and calls `_resolve`, after `resolve` when
  the case has variables. `VariableRecord.carried` writes the expressions back into a dump, sets `models` to the
  record's paths, applies the edits and calls `read_mapping`.
- A model's own input paths are absolute already, since `_read_model_file` rebases each body beside its file. Only
  the study's keys and overrides can be relative.
- `api/sweep.py:plan_sweep` calls `case.with_()` to make relative paths absolute before it refuses one.
  `test_fr39_a_study_resolves_to_its_case_written_inline` asserts `resolved == twin.with_()`.
- `sweep/plan.py` (three calls), `validation/costs.py` (two) and `gui/case_model.py` call `substitute` without a
  base, so their result is unchanged.

**D4.**
- `ModelFile` holds `kind`, `name`, `path`, `sha256` and `exposed`. It is `eq=False` and never serialised whole:
  `pipeline/run.py:input_files` reads `kind` and `path`, and the manifest reads only `ModelRecord.overrides`. `models`
  is outside every dump, equality and hash, so a body on the record moves no key.
- `_resolve` takes the second element of `_read_model_file`'s tuple as the layer it merges. `_merge` copies each
  block it descends, and `validate_mapping` copies into the model, so the merge mutates no body.
- `api/project.py:_problems_of` calls `check_model_file` and catches `CaseValidationError`, `FileNotFoundError`,
  `ValueError` and `KeyError`.
- `Project._copy_model` reads `file.path`'s YAML whole, rebases it beside `file.path.parent` into `inputs/`, and
  compares its text with an existing item to reuse it.

**D5.**
- `Project._split` builds the four layers from `leaves(raw)`, skipping `None`, pinning `case.expressions` to the
  study and writing with its own `_put`, which equals `io/models.py:_put`. It pops `schema` and `name` from the study
  layer. `leaves` yields `variables` as one leaf, which the study owns.
- `mapping_changes` reports no change for `schema`, `name`, `exposes` or `variables`, which have no schema default,
  and one for `models.<kind>`, whose default is `None` (probed at `ae01061`). Stripping `HEADER_KEYS` in `_body`
  therefore changes no model's list.
- `_body(location, keep=True)` serves `reset`, `_problems_of`, `_export_plan` and `_bodies`; `changes` alone strips.
  `io/defaults.py` imports `Kind`, `leaves` and `owner_of` from `io/models.py` already.

**D6.**
- No `io` function changes its subpackage. Each changed caller (`api/`, `pipeline/`, `validation/`) imports `io`
  already.

### Implementation details

**Item 1.** In `io/case_paths.py`, move `_cursor` from `io/models.py` unchanged. Add:

```python
@cache
def _input_leaves() -> tuple[tuple[str, bool], ...]:
    own = tuple((p, False) for p in path_fields() if not p.startswith("models."))
    corrections = (
        "electrolyte.parameters",
        *(f"electrolyte.corrections.{n}.model" for n in CORRECTION_PROPERTIES),
    )
    return (*own, *((p, True) for p in corrections))
```

`input_paths(source: CaseDocument | Mapping[str, Any]) -> dict[str, str]` dumps a document
(`by_alias=True, mode="json"`), else reads the mapping. For each leaf it takes `_cursor`'s parent and keeps a `str`
value, a correction leaf's only where `names_a_path`. `rewrite_inputs(body, rewrite) -> bool` sets each leaf whose
`rewrite(dotted, value)` returns another string. `rebase_inputs(body, base) -> dict[str, Any]` rewrites each
non-absolute value to `str((base.resolve() / value).resolve())` and returns `body`. Delete `correction_paths`.
`io/models.py:_read_model_file` calls `rebase_inputs(body, path.parent)`; delete `_rebased`, `_correction_leaves` and
`_cursor`, and import `_cursor` from `case_paths`. In `io/project.py`, delete `_input_fields`, `item_inputs`,
`rewrite_inputs` and `_at`. `api/project.py` imports `input_paths` and `rewrite_inputs` from `case_paths`.
`api/case.py:_rebased_paths` and `api/sweep.py:plan_sweep` read `input_paths(case)` alone. Run ruff for the imports
left unused.

**Item 2.** `substitute(document, assignments, *, base: Path | None = None)` follows CODE_REVIEW_036's sketch, with
`current = record.carried(current, moved, base=base)` in the model branch, `variables.carried(current, rest,
base=base)` in the variables branch, and `rebase_inputs(payload, base)` after the edits and before `_revalidated` in
the plain one. `ModelRecord.carried(..., *, base=None)` calls `rebase_inputs(study, base)` after
`study.pop("models")`. `VariableRecord.carried(..., *, base=None)` calls it on `mapping` after the edits, before
`read_mapping`. The refusals read `f"<{document.name}>: {paths}: the case names no model; write models: in the case
file"` and `f"…: the case defines no variables; write variables: in the case file"`. `Case.with_` ends:

```python
edited = check_document(
    substitute(self, assignments, base=self._base), source=f"<{self.name} edited>"
)
assert isinstance(edited, Case)
edited._base = self._base
return edited
```

Delete `_rebased_paths`. In §5.3.1, "refused likewise, naming the readers that resolve it" becomes "refused likewise,
saying to write `models:` in the case file".

**Item 3.** Rename `io/models.py:read` and `reads` to `read_case` and `read_case_text`, with the same bodies and
`Raises` naming `CaseValidationError`. Delete `io/case.py:read_case`, `read_case_text` and `_validate`. The module's
docstring ends "validating and writing". Update `pipeline/case.py`, `api/case.py:Case.loads` and
`validation/costs.py`, which imports `read_case` from `nanopnp.io.models` and keeps `dump_case` from `io/case`. In §5.3.1, replace "A reader
that does not resolve models, `read_case`, SHALL refuse a document carrying `models:`, naming the readers that do
(`Case.load`, `pipeline.case.load_case`)." with "Every case reader resolves `models:`: `read_case` and
`read_case_text`, and `Case.load` and `pipeline.case.load_case` through them." In the `variables:` NOTE, "so a reader
that does not resolve variables (`read_case`) never sees one;" becomes "which every case reader resolves again;".

**Item 5.** `ModelFile` gains `body: Mapping[str, Any] = field(default_factory=dict)` after `exposed`.
`read_model_file` is today's `_read_model_file` with `location = Path(path)`; the not-a-file message uses `source`
when given, else `str(location)`. The body is `rebase_inputs(body, location.parent)` when `rebase`, else as written.
`_resolve` appends `(str(paths[kind]), found.body)`. Add:

```python
def split_case_layers(
    raw: Mapping[str, Any], *, pinned: AbstractSet[str] = frozenset()
) -> dict[Kind, dict[str, Any]]:
    layers: dict[Kind, dict[str, Any]] = {kind: {} for kind in (*MODEL_KINDS, "study")}
    for path, value in leaves(raw):
        if value is None or path.split(".", 1)[0] in ("schema", "name", "models"):
            continue
        _put(layers["study" if path in pinned else owner_of(path)], path, value)
    return layers
```

`Project._split` takes `split_case_layers(raw, pinned=frozenset(case.expressions))` and drops its two pops.
`io/defaults.py` adds `_METADATA_KEYS = frozenset({*HEADER_KEYS, "models"})`, and `mapping_changes` filters on the
first component. `_body(location)` returns the mapping whole. `_problems_of` calls `read_model_file(kind, location)`. `tests/tier1/test_models.py:split_case` builds its layers with `split_case_layers`.

**Item 7.** In `review-findings.md`, REV-217 and REV-219 become `fixed`, with a *Fixed* line in `review-items.md`. In
`holds-now.yaml`, AL22 reads `open: WP5.14, WP5.16, WP5.17`, and AL23 drops `open:`. Run `decisions.py`. Add
`## [0.6.0-alpha.13]` to `CHANGELOG.md`.

### Work items

- [x] 62e3295 1. `src/nanopnp/io/case_paths.py`, `src/nanopnp/io/models.py`, `src/nanopnp/io/project.py`,
  `src/nanopnp/api/project.py`, `src/nanopnp/api/case.py`, `src/nanopnp/api/sweep.py`, `tests/tier1/test_case.py`:
  the input-path seam (D2); done when row 3 and FR-32's rows pass. **Executor:** main.
- [x] e756024 2. `src/nanopnp/io/case_paths.py`, `src/nanopnp/io/models.py`, `src/nanopnp/api/case.py`,
  `specification/05-software-design/03-1-case-file.md`, `tests/tier1/test_models.py`: one substitution (D3); done when
  row 2 and FR-39's rows pass. **Executor:** main.
- [x] 30b055a 3. `src/nanopnp/io/models.py`, `src/nanopnp/io/case.py`, `src/nanopnp/pipeline/case.py`,
  `src/nanopnp/api/case.py`, `src/nanopnp/validation/costs.py`, the same clause, `tests/tier1/test_models.py`: one
  reader pair (D1); done when row 1 passes. **Executor:** main.
- [x] 4. Compaction checkpoint. **Executor:** main.
- [x] ffa9bcc 5. `src/nanopnp/io/models.py`, `src/nanopnp/io/defaults.py`, `src/nanopnp/api/project.py`,
  `tests/tier1/test_models.py`: typed model files and the split (D4, D5); done when row 4 and FR-32's and FR-34's rows
  pass. **Executor:** main.
- [x] 51a4c40 6. `.claude/hooks/gate.sh run` and the strict documentation build, since items 2 and 3 change §5.3.1 and
  docstrings: row 5. **Executor:** main.
- [ ] 7. The records of *Implementation details*; FR-39's and FR-25's Appendix A rows name rows 1 to 4; Outcome notes;
  the phase plan's heading; `current.md`. Done when the review says so. **Executor:** main.


> **Outcome — the swap branch rebases.** Row 2 holds a study's relative override absolute after a swap-only `with_`
> and after a swap with an edit, and `substitute(case, {})` keeps it as written (e756024).

> **Outcome — the header goes to no layer.** `split_case_layers` skips `schema`, `name` and `models`, so
> `tests/tier1/test_models.py:split_case` writes the study's header itself, and `Project._split` drops its two pops;
> the project's import tests pass unchanged (ffa9bcc).

> **Outcome — nothing moved.** The push gate passed in 227 s at 51a4c40 with the VER-62 walks of examples 01 and 02
> unmoved, no re-pin, no new layering edge and `SPLIT_BOUND` holding; the strict documentation build passed with
> `mkdocs.yml` unchanged.

### Verification

Rows 1, 2 and 4 are in `tests/tier1/test_models.py`, row 3 in `tests/tier1/test_case.py`; each runs by
`uv run pytest <file> -k <word>`. *Params* is a copy of `data/corrections/willems2020_nacl.yaml` named `params.yaml`
beside the case, which names it relatively at `electrolyte.parameters` and `corrections.diffusivity.model`.

| Test | Tier | Identifiers | Oracle and tolerance | `-k` |
|---|---|---|---|---|
| 1 `test_fr39_every_case_reader_resolves_a_study_and_its_variables` | 1 | FR-39 | The quick-start split by `split_case`, and the quick-start inline with `a: {value: 1, unit: nm}` and `radius_nm: 2*a`: `read_case`, `read_case_text(text, base=folder)`, `load_case` and `Case.load` give `==` documents with one `CaseArtefact` hash; the study's record names its two files, continuum and physics (the quick-start has no molecular key); each variables record holds `{"geometry.pore.radius_nm": "2*a"}` | `every_case_reader` |
| 2 `test_fr25_every_edit_reads_a_relative_path_beside_its_case` | 1 | FR-25, FR-39 | One assertion per branch, each path `== str((folder / "params.yaml").resolve())`: a plain case's `with_()`; a case with `v: {value: 50, unit: mV}` and `bias_V: v` after `with_(outputs=["current"])`, its expression kept; a study overriding `corrections.diffusivity.model` with *Params* after a swap-only `with_({"models.continuum": …})` and after `with_(bias_V=0.1)`. `substitute(case, {})` leaves `"params.yaml"` | `relative_path_beside` |
| 3 `test_fr25_a_case_and_its_mapping_name_the_same_input_files` | 1 | FR-25 | For the quick-start with *Params* and for 2WCD, `input_paths(document) == input_paths(mapping)` and the installed name `willems2020_nacl` is absent; a study file's mapping gives no `models.*`; `rebase_inputs` makes each relative value absolute and leaves an absolute one | `same_input_files` |
| 4 `test_fr39_a_model_file_carries_the_body_its_study_merges` | 1 | FR-39, FR-34 | The quick-start's physics model with *Params* and an `exposes:` list: `read_model_file(...).body` holds no `schema`, `name` or `exposes`; *Params* is absolute, and as written with `rebase=False`; `mapping_changes` of the file equals that of the body read with `rebase=False`; `mapping_changes({"models": {"physics": "x.yaml"}}) == ()` | `carries_the_body` |
| 5 The VER-62 walks; FR-39's, FR-32's and FR-34's rows of Appendix A; `test_layering.py` | 1, 2 | VER-62, VER-61, VER-72 | Walks unmoved at 10⁻⁸, no re-pin; every existing study, model, variable and project test passes through the one reader; no new edge; `SPLIT_BOUND` holds | `gate.sh run` |

### Out of scope

- `pipeline/case.py:_rebased` and `_absolute`, which resolve a typed input against the base at run time: no review
  finding names them.
- Moving `VariableRecord` into `io/variables.py`: withdrawn (C1.5; REV-200).
- The sweep's planning and the walk's keying, REV-220 and REV-221: WP5.14.
- The suites that read `ModelFile.body`: WP5.15 onward.

### Open questions

None.
