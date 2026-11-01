# WP59 — The architecture review's fixes: the case owns its source, one route for every caller

**Status: in progress (items 1 to 4 done).** Written 1 November 2026, grounded in the code at `dca78f1` (§8.2.15 Q1).
Inherits §8.2.27 AC1, AC2 and AC5, the verdicts of [CODE_REVIEW_024](../code_reviews/CODE_REVIEW_024.md) and the
test scope (§8.2.13 N1, N3). Tag `v0.5.0-alpha.25`, after the merge.

The [Phase 4 plan](phase-4-polish-and-user-testing.md)'s WP59 entry sets this scope; `SPECIFICATION.md` governs, and
where it and this plan disagree this plan is wrong. Identifiers are pointers into it.

## In brief

An outside review found parts of the program reaching past each other's front doors. This package fixes the ones
the author accepted, before the release the browser workbench builds on.

**What changes.** A calculation read from a file states openly the text, file and folder its runs record, so the
session no longer reads its private parts. Two equal calculations now also count as one in a set. The commands that
check a case, print its reference fingerprint, read a finished run and draw a run's figure go through the session the
workbench will use. A solve that meets an invalid number at its smallest step stops at once, saying where, instead of
running a hundred useless steps. A mesh with no pore wall is refused by name. Six sample case files find their mesh
beside themselves.

**Cost.** Three to five days. No result moves.

**What could go wrong.** A command could print something different; the checks on every example's commands would
show it. The solver change could stop a solve that used to finish; no recorded solve meets an invalid number, and the
checks before each push would show one that did.

**Your call.** Are the three new names right: where a case came from, a case checked as a run would check it, and a
finished run's record read without its stored results? *Recommendation:* yes; each is one job the workbench needs.

## Execution brief

Scope: §8.2.27 AC1, AC2, AC5; verdicts 1 to 9 of CODE_REVIEW_024 as AC1 places them. Depends on WP58, merged at
`dd45e59`. It discharges NUM-16's NOTE on a non-finite trial residual and IF-01's NOTE on the interface, and touches
IF-02, FR-10, FR-25 and QR-12; VER-45, VER-61, VER-62 and VER-65 stay green. **Implementing session: Sonnet, high
effort**; the Newton item and every normative edit stay in the main session. No library API is new.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| **D1 The case owns its source** | A frozen dataclass `CaseSource(text, path, base)` in `api/case.py`, read through the property `Case.source`. `text` is the text the case was read from while unedited, else `dumps()`; `path` the resolved file of an unedited `Case.load`, else `None`; `base` the resolved directory relative paths are read against, else `None`. `Case.load` resolves the path once. `Session.run` reads `case.source` and no private field | Verdicts 1, 3; AC1. One public read serves the session and the workbench's server |
| **D2 The rest of the seam** | `Case.__hash__` hashes a frozen form of `model_dump()`, so equal cases hash equal. Each preset loads its correction file once. Rebasing is not moved, and `with_` keeps its second validation | Verdicts 2, 4 to 6. The api rebases in one function, which the sweep reaches through `with_()`; `resolve`'s rebasing is the run's, a layer down; `input_paths` and `correction_paths` only enumerate. The second pass costs 1.0 ms |
| **D3 Two session methods** | `Session.check(case, *, files=True) -> CaseCheck`: checks the files the case names (unless `files=False`), resolves it against `case.source.base`, and lists the stages a run of it walks, the session's own included; `CaseCheck(resolved, stages)` is a frozen dataclass in `api/session.py`. `Session.read(directory, *, manifest=None, record=None) -> RecordedRun`: the run directory's case, manifest and run record, checked against each other, without its store or a resolution. No name enters `nanopnp.PUBLIC`; IF-01's NOTE names both methods and `case.source` | Verdict 7; AC1. `open` resolves the case, which fails once a correction file moved, and `inspect` must still read that run. `manifest` and `record` keep REV-157's single read. `StageInfo` is the precedent for a returned type outside `PUBLIC` |
| **D4 The command line's route** | `validate case` and `validate case-hash` (the review's `check` and `explain`) call `Case.load` and `Session.check`; `inspect` calls `Session.read`; `plot` of a run calls `Session.read` for the store its record names, then `Session.open`. `RUN_SCHEMA` and `RUN_RECORD_FILENAME` move to `io/manifest.py`, so `cli/__init__.py` imports nothing from `pipeline/`. No `modularity-layering.yaml` row changes | Verdict 7; AC1. `cli/reference.py` and `cli/reading.py`'s annotations keep the `cli → pipeline` static edge, and every other edge the change uses exists |
| **D5 A non-finite trial residual** | In `damped_newton`, a trial residual that `math.isfinite` refuses cuts the damping above the minimum, as a rejected trial does; at the minimum the state is restored to the iterate the step started from and `NewtonDivergenceError` names the residual, the iteration and the damping, whatever `raise_on_failure` says. A finite residual that fails to fall is still a forced step | AC2; verdict 8; NUM-16's NOTE |
| **D6 The empty wall and REV-169** | `wall_statistics` raises `WallSizeGateError` when the `wall` group holds no segment. The six case files name the mesh beside themselves, `clya-reference.msh` and `../../sweeps/clya-reference.msh`, and their comments, and `docs/scripts/capture_gui.py`'s, say a relative path is read beside the case file | Verdict 9; AC5. The gate's own error keeps exit code 4; the mesh path enters no case identity |

### Grounding

Facts at `dca78f1`.

**D1.**

- `api/case.py:Case` holds `_path`, `_text`, `_base` as `PrivateAttr`s. `Case.load` sets `_path = Path(path)`
  unresolved and passes `base=source.resolve().parent` to `loads`, which resolves `base` and sets `_text`.
- `api/session.py:Session.run` passes `case._text` (or `case.dumps()`), `case._path` and `case._base` to `_walk`. No
  other module reads them; `api/reproduce.py` calls `Case.load(case_path, base=...)`.
- `pipeline/run.py:input_files` resolves `case_path` again and records it, and `_run_key` reads digests and the case
  hash, not the path: resolving in `load` moves no key and no recorded field.
- A preset goes through `_built`, which calls `loads(json.dumps(document))`: its text is that JSON. D1 keeps it.
- `with_` returns a copy with `_text` and `_path` unset and `_base` the source's; `tests/tier1/test_case.py` checks
  that a run of an edited case records `dumps()` and no case file.

**D2.**

- `Case.__eq__` compares `model_dump()`; `__hash__` hashes `dumps()`, so `bias_V=-0.0` and `0.0` compare equal and
  hash apart. Python's `hash(-0.0) == hash(0.0)`, and a frozen form keeps `==`: a dict becomes a `frozenset` of its
  items, a list or tuple a `tuple`.
- `cylinder` calls `_electrolyte` (one load) and `load_corrections(parameters).dielectrics` (a second);
  `from_structure` the same. `materials/corrections.py:load_corrections` caches only the parse.
- `api/sweep.py:plan_sweep` calls `case.with_()` to rebase, then refuses any path still relative.

**D3.**

- `pipeline/run.py:read_run(directory, *, manifest_document=, record_document=)` returns `RecordedRun(directory,
  document, manifest, record)` and raises `FileNotFoundError` or `ManifestHashError`. `open_run` calls it, looks the
  artefacts up and calls `resolve`, which raises `CaseValidationError` for a missing correction file.
- `Session.open` passes `store=self.store`, so it never reads the store a record names.
- `pipeline/run.py:selected_stages(resolved, upto, *, stages=)` lists the stages; `pipeline/checks.py:
  check_referenced_files(document, *, base=)` raises `FileNotFoundError` naming the key.
- `Session` imports `pipeline` inside its methods; `test_public_api.py` checks that `import nanopnp` imports no numpy
  or NGSolve, so the new methods import inside too.
- `cli/reference.py:render_api_reference` documents only `PUBLIC`'s names; `StageInfo` is not among them.
- `tests/tier1/test_public_api.py` holds one test, the import cost: the test scope withdrew the list of names, so a
  public method is decided in review and stated in IF-01's NOTE (§3.1). The Phase 4 plan's entry is corrected here.

**D4.**

- `cli/__init__.py:_validate_case` calls `load_case`, `check_referenced_files` (unless `--schema-only`), `resolve`
  and `selected_stages`, all against `Path(args.case).resolve().parent`; `_validate_case_hash` calls `load_case`,
  `resolve` and `validation.comsol.case_identity`; `_inspect` calls `read_run` with the document it parsed; `_plot`
  calls `open_run(target, store=store)`, `store` `None` without `--store`. The review's line numbers name these four.
- `load_case` is `check_document(read_case(path))`; `Case.load` is `check_document(read_case_text(...))` over the
  file's bytes: the same document and the same errors.
- `tests/tier1/test_cli.py::test_val03_validate_case_hash_matches_every_rung_of_the_ladder` compares the command with
  `case_identity(resolve(load_case(case)))`; `test_backend_registries.py` checks `validate case`'s exit code; the
  Tier 2 example walks run `inspect`.
- `io/manifest.py` holds `MANIFEST_SCHEMA`, `MANIFEST_FILENAME` and `CASE_FILENAME`. `cli/reading.py` imports
  `RecordedRun` and `StageRecord` under `TYPE_CHECKING`, which VER-61 counts as `static`.

**D5.**

- `numerics/newton.py:damped_newton` takes a trial when `trial_residual < current or at_minimum`, so a NaN at the
  minimum is a forced step. `NewtonDivergenceError` is raised only at the iteration cap; `core/errors.py` maps it to
  the convergence exit code.
- Callers: `physics/pb.py:solve_pb_recorded` and `physics/models.py:CoupledModel.solve`, neither passing
  `raise_on_failure`; `solve/continuation.py` re-raises a rung's error unchanged.
- `tests/tier1/test_newton.py::test_num16_a_nan_trial_residual_at_minimum_damping_is_a_forced_step` asserts today's
  behaviour, and `knowledge/06-numerics-fem/14-tier-1-test-evidence-newtons.md` cites it. Run at `dca78f1`:
  `sqrt(u) − 0.1` from `u = 4` gives NaN at damping 1 and, with `minimum_damping=1e-2`, residual 0.777 at damping
  0.2, two trials, not forced. `800 − exp(−u)` from `u = 0` gives NaN too, not inf: no cheap form yields an infinite
  norm, and `math.isfinite` takes inf by the same branch.

**D6.**

- `mesh/generate.py:wall_statistics` calls `np.argmax` on the `wall` lengths, which raises a bare `ValueError` when the
  group is empty; `MeshData.edges_of` already raises `KeyError` naming the groups when it is absent.
  `WallSizeGateError(criterion, measured, threshold, where)` maps to the gate exit code.
- The six files: `docs/sweeps/phase1-reference.case.yaml` and `docs/validation/cases/clya-*.case.yaml`, each with
  `inputs.mesh.path: docs/sweeps/clya-reference.msh` and a header saying the path resolves against the working
  directory. `docs/sweeps/README.md` writes the mesh to `docs/sweeps/clya-reference.msh`.
- `validation.comsol.case_identity` of the five frozen cases is the same with either base: `0128dd1854ff`,
  `4db46a9d821b`, `1b48e22b656c`, `0e263b472108`, `1e26bf4a0c11`. `test_sweep_plan.py` plans the reference sweep
  with `check_meshes=False`, and no test reads the mesh.

### Implementation details

**Item 1.** In `api/case.py`, before `Case`:

```python
@dataclass(frozen=True)
class CaseSource:
    """The text, file and base directory a run of a case records."""

    text: str
    path: Path | None
    base: Path | None
```

`Case.source` is a property returning `CaseSource(self._text if self._text is not None else self.dumps(), self._path,
self._base)`. In `load`: `given = Path(path)`, `resolved = given.resolve()`, read `resolved.read_bytes()`, call `loads`
with `base=resolved.parent if base is None else base` and `source=str(given)`, set `case._path = resolved`.
`__hash__` returns `hash(_frozen(self.model_dump()))`, `_frozen(value: object) -> Hashable` a module function. Change
`_electrolyte(parameters, concentration_M)` to `_electrolyte(parameters, concentration_M, corrections)`; each preset
binds `corrections = load_corrections(parameters)` once and reads `.dielectrics` from it. `Session.run`: `source =
case.source`, then `case_text=source.text, case_path=source.path, base=source.base`. Add `CaseSource` to `__all__`.

**Item 2.** Move `RUN_SCHEMA` and `RUN_RECORD_FILENAME` from `pipeline/run.py` into `io/manifest.py` and import them
back into `pipeline/run.py`, so every `from nanopnp.pipeline.run import RUN_RECORD_FILENAME` still works. In
`api/session.py`:

```python
@dataclass(frozen=True)
class CaseCheck:
    """A case resolved as a run would resolve it, and the stages a run of it walks."""

    resolved: ResolvedCase
    stages: tuple[str, ...]
```

`check` imports `resolve`, `check_referenced_files` and `selected_stages` inside; with `files`, it calls
`check_referenced_files(case, base=case.source.base)` first, then `resolved = resolve(case, base=case.source.base)` and
`selected_stages(resolved, None, stages=self._own)`. `read` returns `read_run(directory, manifest_document=manifest,
record_document=record)`; its docstring names the two parameters as the files already parsed and float-decoded.
`ResolvedCase` and `RecordedRun` are imported under `TYPE_CHECKING`. IF-01's NOTE on the interface gains, after the
`session.open` clause: "`session.check(case)` resolves a case as a run would, checking the files it names, and lists
the stages a run walks, without running one; `session.read(directory)` reads a run directory's case, manifest and
record, without its store; `case.source` is the text, file and base directory a run of the case records."

**Item 3.** `_validate_case`: `case = Case.load(args.case)`, `checked = Session(write=False).check(case, files=not
getattr(args, "schema_only", False))`; the payload and lines read `case.name`, `checked.resolved.model`,
`checked.resolved.stabilisation` and `checked.stages`, unchanged in content. `_validate_case_hash`:
`case_identity(Session(write=False).check(Case.load(args.case), files=False).resolved)`. `_inspect`: `session =
Session(write=False)`; `reading.comparison(session.read(args.target), session.read(args.other))`; the run branch calls
`session.read(target.parent, manifest=..., record=...)` with today's two conditionals. `_plot`'s run branch:
`recorded = Session(write=False).read(target)`, `named = recorded.record.get("store")`, `holding = store if store is
not None else Store(str(named) if named else None)`, `result = Session(holding, write=False).open(target)`; the
refusals that follow are unchanged. Import `RUN_SCHEMA` and `RUN_RECORD_FILENAME` from `nanopnp.io.manifest`.

**Item 5.** After `trial_residual = residual_norm()`:

```python
if not math.isfinite(trial_residual):
    if at_minimum:
        solution.vec.data = previous
        raise NewtonDivergenceError(
            f"damped Newton step {iteration} reached a non-finite trial residual "
            f"({trial_residual}) at the minimum damping {damping:.3g}; the state is restored "
            f"to the iterate the step started from, residual {current:.3e} (NUM-16)"
        )
    damping = max(settings.minimum_damping, damping * settings.recovery_damping)
    continue
```

Drop the NaN comment of the branch below. The error's docstring: "Newton stopped without converging: at its iteration
cap, or on a non-finite trial residual at minimum damping." NUM-16's NOTE, after the NOTE on the relative tolerance:
"NOTE on a non-finite trial residual (§8.2.27 AC2). A trial step whose residual is NaN or infinite is a broken state,
not a step that fails to reduce the residual, so the acceptance above does not reach it. Above the minimum damping it
cuts the damping as a rejected trial does; at the minimum the solve restores the iterate the step started from and
raises a divergence naming the residual, the iteration and the damping."

**Item 6.** In `wall_statistics`, after `segments = data.edges_of("wall")`: if `len(segments) == 0`, raise
`WallSizeGateError("wall segments", "none", "at least one", f"the mesh's wall group is empty; its groups are
{list(data.boundaries)}")`. Set `inputs.mesh.path` to `clya-reference.msh` in `docs/sweeps/phase1-reference.case.yaml`
and to `../../sweeps/clya-reference.msh` in the five frozen cases; rewrite each header's sentence on the path to "A
relative `inputs.mesh.path` is read beside this file (section 5.3.1)." `capture_gui.py`'s comment on `os.chdir`
becomes "the mesh command writes pore.msh here, beside the case file that names it".

### Work items

- [x] f98b2ff 1. `src/nanopnp/api/case.py`, `src/nanopnp/api/session.py`: `CaseSource`, `Case.source`, the path resolved in
  `load`, the hash, the corrections loaded once, `Session.run` on `case.source` (D1, D2); done when
  `uv run pytest tests/tier1/test_case.py tests/tier1/test_session.py tests/tier1/test_materials_path.py` passes and the
  review says so. **Executor:** main
- [x] 60448e7 2. `src/nanopnp/api/session.py`, `src/nanopnp/io/manifest.py`, `src/nanopnp/pipeline/run.py`,
  `specification/03-requirements.md`: `Session.check`, `CaseCheck`, `Session.read`, the two constants moved, IF-01's
  NOTE (D3); done when `uv run pytest tests/tier1/test_public_api.py tests/tier1/test_session.py
  tests/tier1/test_layering.py` passes. **Executor:** main
- [x] 8e75f10 3. `src/nanopnp/cli/__init__.py`: `_validate_case`, `_validate_case_hash`, `_inspect` and `_plot`'s run branch on
  `Case` and `Session` (D4); done when `uv run pytest tests/tier1/test_cli.py tests/tier1/test_backend_registries.py
  tests/tier1/test_layering.py tests/tier2/test_examples_02_classical.py` passes and `grep -n "nanopnp.pipeline"
  src/nanopnp/cli/__init__.py` prints nothing. **Executor:** `general-purpose` on Sonnet
- [x] 4. Compaction checkpoint. **Executor:** main
- [ ] 5. `src/nanopnp/numerics/newton.py`, `tests/tier1/test_newton.py`, `specification/06-numerics.md`,
  `knowledge/06-numerics-fem/14-tier-1-test-evidence-newtons.md`, `knowledge/log.md`: the guard, NUM-16's NOTE, the
  forced-NaN test replaced by *Verification*'s test, the knowledge line rewritten for it (D5); done when
  `uv run pytest tests/tier1/test_newton.py tests/tier1/test_newton_per_field.py` passes. **Executor:** main
- [ ] 6. `src/nanopnp/mesh/generate.py`, the six case files, `docs/scripts/capture_gui.py` (D6); done when
  `uv run pytest tests/tier1/test_mesh_generate.py tests/tier1/test_sweep_plan.py tests/tier1/test_cli.py` passes and
  the scratch script of *Verification* prints the five identities. **Executor:** `general-purpose` on Haiku
- [ ] 7. `CHANGELOG.md` (`## [0.5.0-alpha.25]`: Added, the three names; Changed, the Newton abort; Fixed, the hash, the
  resolved path, the empty wall, REV-169), `docs/guide/python.md` (one paragraph on `session.check` and
  `session.read` beside *Reopen a recorded run*), REV-169 `fixed` in `docs/project/review-findings.md` and
  `review-items.md`, the Phase 4 plan's entry and `current.md`; done when the strict documentation build passes.
  **Executor:** main

### Verification

| Test or check | Tier | Identifier | Oracle | Tolerance source | Command |
|---|---|---|---|---|---|
| `tests/tier1/test_newton.py::test_num16_a_non_finite_trial_residual_aborts_at_minimum_damping_and_cuts_above_it`, replacing the forced-NaN test | 1 | NUM-16 | `sqrt(u) − 0.1` from `u = 4`, on the existing test's slab: at damping 1 and minimum 1, `NewtonDivergenceError` matching `non-finite`, `step 1` and `damping 1`, and `Norm(state − before) == 0`; at minimum 10⁻², one step, damping 0.2, trials 2, finite residual, not forced | exact: the restore is a copy; the cut is the recovery factor | `uv run pytest tests/tier1/test_newton.py` |
| A finite residual that fails to fall is still forced | 1 | NUM-16 | `test_num16_minimally_damped_step_is_accepted_not_aborted`, kept | exact | as above |
| The layering is unchanged | 1 | VER-61 | `test_layering.py`, `modularity-layering.yaml` untouched | exact | `uv run pytest tests/tier1/test_layering.py` |
| The backend set and the golden | 1, 2 | VER-65, VER-62 | `test_backend_guard.py` at eleven; `test_stability_golden.py`, `test_idealised_pore.py` at zero drift | 10⁻⁸ (VER-62) | `.claude/hooks/gate.sh run` |
| `import nanopnp` stays cheap | 1 | VER-45 | `test_public_api.py` | exact | `uv run pytest tests/tier1/test_public_api.py` |
| The commands print what they printed | 1, 2 | — | `test_cli.py`'s case-hash test, `test_backend_registries.py`'s exit code, the examples' `inspect` | exact | `.claude/hooks/gate.sh run` |
| The frozen identities hold | — | — | *Grounding* D6's five prefixes, `case_identity(resolve(load_case(p), base=p.resolve().parent))` | exact | a scratch script |

The hash, the methods and the empty-wall refusal, an input refusal before the gate measures, get no test (N1).

### Out of scope

| Deferred | Owner |
|---|---|
| Verdicts 12, 13: the stage-5 region interface | REV-170, Phase 5 (AC3) |
| Verdicts 14 to 18: the unmeasured costs and internal checks | REV-171, Phase 6 (AC4) |
| Verdicts 10, 11, 19 to 22, and `target_nm ≤ 0` | Not taken |
| The Qt shell's reads of `pipeline/` | Leave with it (§8.2.17) |
| A non-finite residual on the entry state | Not ruled |
| The workflow prose | WP60 (AC6) |

### Open questions

None blocks. The three names are the In brief's *Your call*; review decides them (N3).
