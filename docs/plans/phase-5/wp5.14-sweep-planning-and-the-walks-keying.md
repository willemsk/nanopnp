# WP5.14 — Sweep planning and the walk's keying

**Status: planned, not started.** Planned 10 November 2026 on `main` (`d3420d8`). It inherits §8.2.36 AL22, and
CODE_REVIEW_036's candidates 2 and 6 with their corrections C2.1 to C2.4 and C6.1, settled with the author on 6 and
7 November 2026.

This plan belongs to [the Phase 5 plan](phase-5-workbench.md). `SPECIFICATION.md` governs. An identifier here points to
a clause and never restates it.

## In brief

**What changes.** Nothing a user computes or sees moves. Planning a sweep from Python stops writing its files twice
through a temporary folder. The library also stops preparing each point of a sweep again for the forecast, again for
the run and twice more for the neighbour it starts from: on a three-point test sweep, thirteen preparations become six.
A point run in another process prepares only itself and its neighbour. Inside the library, the three places that work
out which stored results a run would reuse become one, so the suites that follow change one place.

**Cost.** About five sessions, three to six agent hours and eight of your touches, the specification's estimate for a
clean-up package; its twin, the case-file clean-up, measured one session and one agent hour. No new library. Sweeps
start slightly sooner.

**What could go wrong.** A point could start cold instead of from its neighbour, or reuse the wrong stored result. The
tests that check warm starts run, with the recorded example numbers and the example sweep that runs on two processes;
a moved number is undone, never re-pinned. A plan moved to another folder could use points prepared for the old one;
a test moves a plan and checks that it reads the new folder's files. The forecast could stop matching what the run
rebuilds; its existing test compares them point by point.

**Your call.** None. You settled the designs on 6 and 7 November and placed them here on 8 November. The plan's own
choices keep today's behaviour and every refusal a sweep makes today.

## Execution brief

**Scope.** REV-221 and REV-220: [CODE_REVIEW_036](../../code_reviews/CODE_REVIEW_036.md)'s candidates 2 and 6, whose
sketches the items cite, re-read against WP5.13's code. **Depends on:**
WP5.13 (merged). WP5.15 follows in this lane. **Requirements:** FR-24, FR-27, FR-39; VER-61, VER-62, VER-64, VER-72.
**Constrained by:** AL22 (no key and no golden moves), §5.3.4's refusals before a member is built, AC1 (a public read
rather than a private field), `.claude/rules/python.md` (imports at the top). **Implementing session:** Sonnet, high effort. Tag
`v0.6.0-alpha.14`.

**Amended when it lands:** §5.3.4's sentence "The plan resolves each member once, and the forecast and the run read
those members." (D3; item 3). The plan's commit amends no clause.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 Planning in memory | `sweep/plan.py:build_plan(document, *, source=None, base=None, check_meshes=True)`. Given `base`, it reads no file at the base path: it checks the model files, and resolves the members, beside `base.models_record.base` for a study and beside `document.base_path(source).parent` otherwise. `api/sweep.py:plan_sweep` builds the plan in memory from the edited `case`, writes the base case and the sweep file once into `store.sweep_directory(name, plan.hash)` and moves the plan there with `replace(base_path=...)`; no `.staging-*` directory | D2.1 and C2.1, ruled by the author on 7 November 2026; decided by the plan for the directory an in-memory study is read beside |
| D2 Members keyed on their directory | `SweepPlan` gains `_resolved_members` and `_resolved_beside`, fields with `compare=False, repr=False`. `resolved_members` returns them while `_resolved_beside == base_path.parent.resolve()`, else runs `base_case()` once, resolves and caches with `_resolved_beside` absolute. `held_member(index) -> ResolvedCase | None` returns a held member and never resolves. `build_plan` passes the members it resolved; `read_plan` passes none | D2.2 and C2.2, ruled by the author on 7 November 2026; decided by the plan for `held_member`, a public read as AC1 gave `Session` for `Case`, and for the absolute directory |
| D3 A member resolved where it is held | `run_point` calls `plan.base_case()` before every member, as today, then takes its point and its parent from `held_member`, or resolves only those two. `run_document`, `stored_upstream` and `Session._walk` take `resolved: ResolvedCase | None = None` beside the document, and refuse one whose `document` is another object. `_parent_artefact` keys the parent's solve on that one resolved case and passes `session.own_stages` | D2.3 and C2.3, ruled by the author on 7 November 2026; decided by the plan for the keyword (D2.3's text, against candidate 6's sketch, which passes either type in one parameter) and for keeping §5.3.4's check before each member |
| D4 The session's walk stays | `Session._walk` and `Session._member` stay; `_walk` forwards `resolved` | D2.4 and C2.4, ruled by the author on 7 November 2026 |
| D5 One keying walk | `_Walk.keyed(name)` builds a stage to key only, with the store where it takes one and never a workspace; `_Walk.stored(name, key) -> tuple[bool, Artefact | None]` looks it up. `stored_upstream` and `keyed_walk` build a `_Walk` through `_keying_walk` and use `describe`, `inputs`, `keyed` and `stored`; `stored_upstream` gains `stages` and takes a `key_is_artefact` stage's key with no store read. The run keeps `construct`; `_resolve_stage`'s `substitute` branch reads through `stored` | D6.1 and C6.1, ruled by the author on 7 November 2026; decided by the plan for `_resolve_stage`, so that the payload lookup is one method |
| D6 One module | `FORECAST_SCHEMA`, `Identity`, `_NotBuiltPayload`, `_standing_in` and `keyed_walk` move into `pipeline/run.py`, whose `__all__` gains the three public names; `pipeline/forecast.py` goes; `sweep/forecast.py` imports from `pipeline.run` | D6.2, ruled by the author on 7 November 2026 |
| D7 Nothing moves | No artefact key, golden, layering edge, public name or command output changes. §5.3.4 says what a run in another process resolves | AL22, ruled by the author; VER-61, VER-62, VER-72; decided by the plan for what is checked |

### Grounding

**D1.**
- `build_plan` loads the base with `load_case(base_path)`, checks the model files beside `base_path.parent`, resolves
  every point beside it, records `files` from those members (they enter the plan's hash) and gates the meshes on them.
- `plan_sweep` calls `case.with_()`, refuses any relative input path, writes each `models.*` value absolute beside
  `case.models_record.base`, and dumps a study with its model files by absolute path. A member therefore names the
  same files beside any directory. It writes both files into `.staging-*`, builds, writes them again and `replace`s
  `base_path`; it is `build_plan`'s only in-memory caller.
- `SweepDocument.base_path(None)` returns `base` as written, `base.case.yaml`, whose parent is `.`; `resolve` reads `.`
  against the working directory. `ModelRecord.base` is the study's directory.
- Probed at `d3420d8`: the edited `Case` hashes as its `dumps(study=...)` text reads back through `loads_case`, for
  the quick-start, the quick-start with `variables:`, its study split in three, and that study edited; and
  `_variables_as_written` agrees. So `base_case()` accepts the store's copy of an in-memory base.
- `api/sweep.py` imports `tempfile` for the staging directory alone.
- `plan_sweep` reads the in-memory plan only for its `hash` before `replace`. A study's members are held beside the
  study's directory, never that plan's `base_path.parent` (`.`), so that plan serves none of them.

**D2.**
- `resolved_members` is a `cached_property`; `build_plan` seeds `plan.__dict__["resolved_members"]` after its two
  `replace` calls (`files`, and `_gate_meshes`'s `wall_distance`), and `replace` drops the seed.
- Probed: `replace` copies a field whose name starts with an underscore, `compare=False` keeps it out of `==`, and
  `object.__setattr__` sets it on the frozen instance. `read_plan` constructs a `SweepPlan` from the file alone.
- Probed: a plan built in `a/`, moved by `replace(base_path=b/...)`, resolves `electrolyte.parameters: params.yaml`
  to `b/params.yaml` today only because the cache is dropped; carrying it would serve `a/params.yaml`.
- `sweep/forecast.py:forecast` reads `plan.resolved_members`; nothing else in `src/` or `tests/` does.
- `pipeline.case.resolve` reads `base` through `Path.resolve()`, against the working directory when it is relative;
  a relative `base_path` compared as written would serve members resolved before a `chdir`.

**D3.**
- Probed at `d3420d8` on a three-point bias sweep of `test_forecast.py`'s case: `plan_sweep` resolves 3 times,
  `forecast()` 3, `run()` 7 (each member once, each parent twice), a second forecast 0; `run_point` on the plan read
  back resolves 3 times. The whole took 1.0 s.
- `run_point` calls `plan.base_case()` (base hash, variables as written, input-file digests) outside its `try`, then
  `_parent_artefact`, then `plan.case(index, base=base)`; `Session._member()._walk` calls `run_document`, which
  resolves. `_parent_artefact` calls `plan.case(parent)`, `stored_upstream` (which resolves) and `resolve` again.
- `run_plan` calls `_announce`, a forecast, only when `indices is None`, so an in-process run of a whole plan holds
  its members. `_worker` reads the plan with `read_plan`; `_pool` starts workers only for `workers > 1`. The CLI's
  `sweep run --index` calls `run_point`, `--wave` passes indices, and example 03 runs `sweep run --workers 2`.
- `Sweep.run` writes the plan and runs `self.plan`, the object `Sweep.forecast()` reads.
- `pipeline.case.resolve` puts the document it is given in `ResolvedCase.document`. On the sweep path,
  `sweep/plan.py`, `pipeline/run.py` and `api/sweep.py` import it by name.

**D4.**
- `Session._walk` passes `workspace`, `overwrite_workspace`, `write` and the own stages; its callers are `Session.run`
  and `run_point`. `ResolvedCase` is already imported in `api/session.py` under `TYPE_CHECKING`.

**D5.**
- `stored_upstream(document, *, store, feeding="solve", base=None)` resolves, builds each stage with
  `create(name, store=store)` or `create(name)` and keys it on `offered(name, artefacts)`; it has no `stages`, so a
  feeding stage of one's own is unknown to `selected_stages`. Its callers are `_parent_artefact`, `gui/assess.py`
  (`feeding="contour"`) and `tests/tier1/test_case_fields.py`.
- `_Walk.construct` makes a scratch directory under `store.root/tmp` for a `takes_workspace` stage.
- `Store.get` counts no hit or miss; `_resolve_stage` counts them.

**D6.**
- `pipeline/forecast.py` (124 lines) is imported only by `sweep/forecast.py`; `pipeline/run.py` has 1,230 lines and
  no `SPLIT_BOUND`. `stage_sets()` reads only module-level assignments, so `keyed_walk`'s `"case"` is not one.
  VER-79 checks §5.1's rows per subpackage, not per module. `sweep` → `pipeline` is a static edge already.

### Implementation details

**Item 1.** In `pipeline/run.py`, add `Forecastable` and `NotBuilt` to the `core.stages` import, `Iterator` and
`NamedTuple`, and move `FORECAST_SCHEMA`, `Identity`, `_NotBuiltPayload` and `_standing_in` unchanged. To `_Walk` add
CODE_REVIEW_036's `keyed` and `stored` as sketched. Add:

```python
def _keying_walk(
    resolved: ResolvedCase, store: Store, stages: Mapping[str, FunctionStage] | None
) -> _Walk:
    return _Walk(
        document=resolved.document,
        resolved=resolved,
        store=store,
        arguments={},
        workspace=None,
        only=True,
        own=dict(stages or {}),
    )


def _given(
    document: CaseDocument, resolved: ResolvedCase | None, base: Path | None
) -> ResolvedCase:
    if resolved is None:
        return resolve(document, base=base)
    if resolved.document is not document:
        raise ValueError(
            f"the resolved case {resolved.name!r} was not resolved from the document "
            f"{document.name!r} passed with it"
        )
    return resolved
```

`stored_upstream(document, *, store, feeding="solve", base=None, stages=None, resolved=None)` is the sketch with
`_given` and `_keying_walk`, its message unchanged. `keyed_walk` is the sketch; `_forecast_digest(name, stage,
description, inputs, resolved, identities) -> str` holds today's `NotBuilt` branch up to `content_hash`. `run_document`
gains `resolved=None` last and builds its walk with `resolved=_given(document, resolved, base)`. `_resolve_stage`'s
`substitute` branch reads `_, found = walk.stored(name, key)`. `__all__` gains `FORECAST_SCHEMA`, `Identity` and
`keyed_walk`. Delete `pipeline/forecast.py`; `sweep/forecast.py` imports `Identity, keyed_walk` from
`nanopnp.pipeline.run`. Each new parameter gets a line in its function's *Parameters*: `resolved`, "the document
already resolved against `base`, so it is not resolved again; another document's is refused"; `stages`, "stages of
one's own, keyed as the walk keys them".

**Item 2.** In `sweep/plan.py`, `SweepPlan` gains the two fields after `variables` and the sketched
`resolved_members` property, and:

```python
def held_member(self, index: int) -> ResolvedCase | None:
    """Return one member as the plan holds it resolved beside its base case, or None."""
    if self._resolved_members is None or self._resolved_beside != self.base_path.parent.resolve():
        return None
    return self._resolved_members[self.point(index).index]
```

`build_plan` takes `base: CaseDocument | None = None`. With none, it loads as today and `beside = base_path.parent`;
given one, `beside = base.models_record.base if base.models_record is not None else base_path.parent`.
`_check_model_files` and `_resolve_every_point` take `beside`, and `replace(plan, files=..., _resolved_members=resolved,
_resolved_beside=beside.resolve())` replaces the seed, whose two lines go. `base`'s *Parameters* line: "the base case already
read, so no file is read at the sweep's base path".

**Item 3.** `plan_sweep` keeps its checks and its `document`, then builds
`build_plan(loads_sweep(text), base=case, check_meshes=check_meshes)`, writes the two files into
`store.sweep_directory(name, planned.hash)` and returns `Sweep(replace(planned, base_path=(directory /
BASE_FILENAME).resolve()), directory, session)`; delete the staging comment, the `sweeps` lines and `tempfile`. `run_point` takes
`held = plan.held_member(index)`, `document = held.document if held is not None else plan.case(index, base=base)`, and
passes `resolved=held` to `_walk`, which gains `resolved: ResolvedCase | None = None` last and passes it to
`run_document`. `_parent_artefact` takes the parent from `held_member`, else
`resolve(plan.case(point.parent, base=base), base=beside)`, and calls
`stored_upstream(resolved.document, resolved=resolved, store=session.store, stages=session.own_stages)` and
`SolveStage().key(StageInputs(resolved=resolved, upstream=upstream))`. In §5.3.4 the sentence becomes: "The plan
resolves each member once, beside its base case, and the forecast and a run in the same process read those members;
a plan moved to another directory resolves them again there, and a member run in another process resolves only its
own point and its parent."

**Item 6.** In `review-findings.md`, REV-220 and REV-221 become `fixed`, with a *Fixed* line in `review-items.md`. In
`holds-now.yaml`, AL22 reads `'§8.1''s Phase 5 row; the Phase 5 plan; open: WP5.16, WP5.17'`. Run `decisions.py`. Add
`## [0.6.0-alpha.14]` to `CHANGELOG.md`.

### Work items

- [x] 9d29935 1. `src/nanopnp/pipeline/run.py`, `src/nanopnp/pipeline/forecast.py` (deleted), `src/nanopnp/sweep/forecast.py`,
  `tests/tier1/test_stages.py`: one keying walk in one module (D5, D6); done when row 3 and row 4's forecast tests
  pass. **Executor:** main.
- [x] 7948fac 2. `src/nanopnp/sweep/plan.py`, `tests/tier1/test_sweep_plan.py`: members keyed on their directory and planning in
  memory (D1, D2); done when row 2 and VER-36's tests pass. **Executor:** main.
- [ ] 3. `src/nanopnp/api/sweep.py`, `src/nanopnp/api/session.py`, `specification/05-software-design/03-4-sweeps.md`,
  `tests/tier1/test_forecast.py`, `tests/tier1/test_sweep_plan.py`: in-memory `plan_sweep` and members resolved where
  held (D1, D3, D4); done when rows 1 and 4 and FR-39's sweep tests pass. **Executor:** main.
- [ ] 4. Compaction checkpoint. **Executor:** main.
- [ ] 5. `.claude/hooks/gate.sh run`, `uv run pytest tests/tier2/test_examples_03_iv_sweep.py` and the strict
  documentation build, since items 1 to 3 change docstrings and §5.3.4: row 5. **Executor:** main.
- [ ] 6. The records of *Implementation details*; FR-39's Appendix A row names rows 1 and 2, FR-27's row 3; Outcome
  notes; the phase plan's heading; `current.md`. Done when the review says so. **Executor:** main.

### Verification

Each row runs by `uv run pytest <file> -k <word>`. *Counted* is a fixture that wraps `nanopnp.pipeline.case.resolve`
and sets it, with `monkeypatch.setattr`, on `nanopnp.sweep.plan`, `nanopnp.pipeline.run` and `nanopnp.api.sweep`,
recording each document's `name`. *Light* is `test_forecast.py:_plan`'s case, moved into a `_case()` helper.

| Test | Tier | Identifiers | Oracle and tolerance | `-k` |
|---|---|---|---|---|
| 1 `test_fr39_a_planned_sweep_resolves_each_member_once` in `test_forecast.py` | 1 | FR-39, FR-24 | Under *Counted*: `plan_sweep` of *Light* over `bias_V` `[0.0, 0.05, 0.1]` records each point's name once, then its `forecast()` and `run()` record each once more, and a second `forecast()` none; counting from after it is built, `_plan`'s plan from a file records none through `forecast` and `run_plan`; `run_point(read_plan(planned.directory / PLAN_FILENAME), 2, ...)` records the names of point 2 and of its parent once each, and afterwards that plan's `held_member(i) is None` for each `i`; every member is `ok` | `each_member_once` |
| 2 `test_fr39_a_plan_moved_to_another_directory_resolves_its_members_there` in `test_sweep_plan.py` | 1 | FR-39 | `BASE` with `parameters: params.yaml`, written in `a/` and copied to `b/`, each beside a copy of the shipped `willems2020_nacl.yaml` named `params.yaml`, planned from `a/` by `_sweep` and `plan_from_document`: the first member's `correction_files["electrolyte.parameters"]` is `a/params.yaml`; after `replace(plan, base_path=b / "base.yaml")`, `held_member(0) is None`, then it is `b/params.yaml` from `resolved_members` and, after that, from `held_member(0)`; the original plan still gives `a/`; `read_plan(write_plan(...)).held_member(0) is None` | `moved_to_another` |
| 3 `test_fr27_the_upstream_lookup_keys_own_stages_as_the_walk_does` in `test_stages.py` | 1 | FR-27, VER-64 | As `test_fr27_a_function_stage_is_keyed_by_its_code_and_its_inputs` sets it up, the quick-start with `elements(mesh)` registered, run to `elements`: `stored_upstream(case, store=session.store, feeding="elements", stages=session.own_stages, base=case.source.base)` names the run's stage records but `elements`, each hash equal to the run's artefact; the same with `resolved=resolve(case, base=case.source.base)`; `sorted(store.root.rglob("*"))` is unchanged by both | `own_stages_as_the_walk` |
| 4 `test_fr39_the_forecast_equals_the_stages_the_walk_rebuilds`, `test_fr39_the_forecast_never_runs_a_stage`; `test_in_memory_sweep_matches_the_sweep_file_plan` gains `held.plan.base_case()` returning for `BASE` and for `BASE` with `variables: {v: {value: 50, unit: mV}}` and `bias_V: v` swept over `concentration_M` | 1 | FR-39, VER-64, VER-36 | Unchanged oracles; the store's copy of an in-memory base passes its hash and variables checks | `forecast or in_memory` |
| 5 The VER-62 walks of examples 01, 02 and 03; VER-37 and VER-38 in `tests/tier2/test_sweep.py` and `test_sweep_generated_mesh.py`; `test_layering.py`, `test_stage_conformance.py` | 1, 2 | VER-62, VER-37, VER-38, VER-61, VER-72, VER-64 | Walks unmoved at 10⁻⁸, no re-pin; each warm member warm; no new edge or deferred import; no stage set in `pipeline/run.py` | `gate.sh run`; example 03 by its file |

### Out of scope

- Re-keying a `plan_sweep` plan's members to the store's directory rather than resolving them again: C2.2 settles
  resolving again, so a sweep planned in Python resolves each member once to plan it and once beside its files.
- The atom radii (REV-218): WP5.16. The stage-5 region seam (REV-170, MOD-03): WP5.17.
- `gui/assess.py`'s lookup, which keeps its call.

### Open questions

None.
