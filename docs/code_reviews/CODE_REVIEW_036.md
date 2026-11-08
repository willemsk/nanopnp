# Code review 036: architectural deepening review (`io`, `pipeline`, `sweep`, `geometry`, `mesh`, `structure`, `charge`, `api`)

2026-11-06 · branch `improve_codebase_architecture` · scope: whole repository (`src/nanopnp/`, `specification/05-software-design/`, `docs/project/modularity-layering.yaml`, `docs/project/review-findings.md`, `docs/project/review-items.md`) · focus: module depth, interface seams, locality of change and elimination of cross-module pass-throughs (`/improve-codebase-architecture`)

## Summary

A full architectural review of `src/nanopnp` examined the subpackage boundaries against the recorded layering (`docs/project/modularity-layering.yaml`, `VER-61`), the deferred-import guard (`VER-72`), the Phase 5 workbench architecture (`docs/plans/phase-5/phase-5-workbench.md`, `docs/plans/phase-5/wp5.09-the-physics-model.md`) and the review register (`docs/project/review-items.md`).

Six shallow seams were identified, explored and settled with the author through interactive design rounds:

1. **Candidate 1 — Collapse Case file reading, substitution and input-path rebasing** (`io/case.py`, `io/case_paths.py`, `io/variables.py`, `io/models.py`, `io/project.py`, `pipeline/case.py`, `api/case.py`)
2. **Candidate 2 — Deepen Sweep planning and member execution in memory** (`sweep/plan.py`, `api/sweep.py`, `api/session.py`, `pipeline/run.py`)
3. **Candidate 3 — Unify the Stage-5 Region seam and delete `CylindricalPoreGeometry` (`REV-170`, `MOD-03`)** (`geometry/region.py`, `geometry/pore.py`, `geometry/analyte.py`, `mesh/primitives.py`, `mesh/idealised.py`, `mesh/generate.py`, `mesh/ingest.py`, `plot/data.py`, `post/indicator.py`, `cli/building.py`)
4. **Candidate 4 — Concentrate effective atom radii and Charge edit scaling in `ProtonationTable`** (`structure/protonated.py`, `charge/edits.py`, `charge/kernel.py`, `density/radii.py`, `density/stage.py`, `geometry/contour.py`)
5. **Candidate 5 — Type Model files and absorb metadata stripping into `io/models.py`** (`io/models.py`, `io/defaults.py`, `api/project.py`)
6. **Candidate 6 — Merge dry-run rebuild forecasting into the pipeline stage walker** (`pipeline/run.py`, `pipeline/forecast.py`, `sweep/forecast.py`)

### Sequencing

None of the six candidates changes code before WP5.09 (the physics model) is merged. The author directed on 7 November 2026 that the changes this review settles land **after WP5.09, following from a Phase 5 amendment** (`/np-plan amend 5`). The amendment rules D1.1's change to a normative clause (`specification/05-software-design/03-1-case-file.md`, the `read_case` refusals of `models:` and `variables:`) in `specification/history/`, and places the candidates in packages after WP5.09. REV-170 stays accepted for WP5.17 (§8.2.34 AJ10) unless the amendment moves it. Each design below is re-read against the code as WP5.09 leaves it, which adds `physics` to `MODEL_KINDS`, a `models.physics` path and `exposes:`. The corrections in the last section bind the amendment.

---

## Findings and `REV` / `MOD` updates

### Updates to existing findings

| ID | Area | Status change | Summary of update |
|---|---|---|---|
| **REV-170** | coupling | `accepted` (WP5.17, §8.2.34 AJ10); unchanged until the post-WP5.09 amendment rules | Unifies `RegionRecord` and `IdealisedRegionRecord` behind a `Stage5Region` protocol and `RegionOutlines` value object in `geometry/region.py`, moves `edge.maxh = wall_h_nm` out of `geometry/pore.py` into `mesh/`, deletes `mesh/primitives.py:CylindricalPoreGeometry` in favour of `geometry/pore.py:CylinderPore` + `mesh/primitives.py:mesh_cylinder_pore()`, and removes all six `isinstance(record, IdealisedRegionRecord)` branches outside Qt (five in the library and `gui/geometry.py:617` in the workbench). |
| **MOD-03** | layering | `accepted` static edge (`geometry -> mesh`) → **removed** | Deleting `CylindricalPoreGeometry` and typing `PoreWithAnalyte.pore` as `CylinderPore` in `geometry/analyte.py` removes the sole `if TYPE_CHECKING:` import from `geometry` up to `mesh`, shrinking `edges:` in `docs/project/modularity-layering.yaml`. |
| **REV-199** | performance | `fixed`, unchanged; its regression in `plan_sweep` is recorded as **REV-221**, open | `build_plan` seeded `plan.__dict__["resolved_members"]` on a `frozen=True` dataclass, which `dataclasses.replace(staged, base_path=...)` in `api/sweep.py:plan_sweep` silently dropped when moving the plan out of its `.staging-*` folder. `plan_sweep(...).forecast()` therefore resolves every member again. Candidate 2 settles the fix; see its corrections. |
| **REV-200** | coupling | `fixed`, unchanged | Moving `VariableRecord` into `io/variables.py` was considered and is withdrawn: `VariableRecord.carried` calls `io/models.py:read_mapping`, and `models.py` imports `variables.py`, so the move adds a cycle (see the corrections, C1.5). |

### New findings (`REV-217` to `REV-221`)

Registered in `docs/project/review-findings.md` and `docs/project/review-items.md`, open until the post-WP5.09 amendment rules.

| ID | Area | Severity | Location | Finding |
|---|---|---|---|---|
| **REV-217** | coupling | low | `src/nanopnp/io/case.py`, `src/nanopnp/io/models.py`, `src/nanopnp/io/case_paths.py`, `src/nanopnp/io/project.py`, `src/nanopnp/api/case.py` | **Case reading, substitution and input-path discovery are split across four `io` modules and `api/case.py`.** `io.case.read_case` refuses `models:` and `variables:` while `io.models.read` resolves them; `Case.with_` calls `substitute()` twice and re-implements path rebasing (`_rebased_paths`); and input-file discovery is implemented four times (`io/case_paths.py:input_paths` + `correction_paths`, `io/models.py:_rebased`, `io/project.py:item_inputs`, and their merge in `api/case.py:_rebased_paths` and `api/sweep.py:plan_sweep`). |
| **REV-218** | coupling | low | `src/nanopnp/structure/protonated.py`, `src/nanopnp/charge/edits.py`, `src/nanopnp/density/radii.py`, `src/nanopnp/density/stage.py`, `src/nanopnp/geometry/contour.py` | **Effective atom radii and atom-to-residue indexing are split across `structure`, `charge`, `density` and `geometry`.** `resolve_protonated_radii` returns unscaled CHARMM radii that `density/stage.py` must manually multiply by `radius_scales(table)`; atom-to-residue indexing is duplicated between `charge/edits.py:_owner` and `density/radii.py:resolve_protonated_radii`; and `RadiusEdit` scaling is assembled separately in `protonated.py`, `charge/edits.py` and `geometry/contour.py`. |
| **REV-219** | interface | low | `src/nanopnp/io/models.py`, `src/nanopnp/io/defaults.py`, `src/nanopnp/api/project.py` | **`ModelFile` discards its validated body, leaving `api/project.py` to re-parse YAML and strip `schema`/`name` by hand.** `_read_model_file` validates and rebases a model file's body and then discards it from `ModelFile`; `api/project.py` re-loads model YAML via `_body(keep=...)` and duplicates `io/models.py:_put` and layer splitting (`_split`). |
| **REV-220** | coupling | low | `src/nanopnp/pipeline/run.py`, `src/nanopnp/pipeline/forecast.py`, `src/nanopnp/sweep/forecast.py` | **`stored_upstream` and `keyed_walk` re-implement the keying that `_Walk` already holds.** `_Walk.describe`, `_Walk.inputs` and `_Walk.construct` serve the run; `stored_upstream` and `pipeline/forecast.py:keyed_walk` each resolve the description, build the stage, filter `offered()` and query the `Store` on their own, and `stored_upstream` omits custom `stages`. |
| **REV-221** | performance | low | `src/nanopnp/api/sweep.py`, `src/nanopnp/sweep/plan.py` | **`plan_sweep` drops the members `build_plan` resolved.** `build_plan` stores them as `plan.__dict__["resolved_members"]`, and `plan_sweep`'s `replace(staged, base_path=...)` builds a fresh `SweepPlan` without them, so `plan_sweep(...).forecast()` resolves every member again. The staged members were resolved beside the `.staging-*` directory, so the fix re-resolves or re-keys them beside the final directory rather than carrying them. |

---

## Candidate 1: Collapse Case file reading, substitution and input-path rebasing (`REV-217`, `REV-200`)

### 1. Architectural diagnosis

Today, reading a case, substituting assignments into it, and discovering or rebasing the input file paths it names are spread across five modules:

- **Two competing `io` reader pairs**: `io/case.py` defines `read_case(path)` and `read_case_text(text)`, which explicitly refuse `models:` and `variables:` (`io/case.py:_validate`, lines 786-793), while `io/models.py` defines `read(path)` and `reads(text)`, which resolve `variables:` and `models:` and then call `validate_mapping`. Every production caller except `validation/costs.py` (`pipeline/case.py`, `api/case.py`, and `sweep/plan.py` through `load_case`) wants a case reader that resolves variables and models; only tests that specifically test the refusal call `read_case` on a study or variable-bearing file.
- **Double `substitute()` and duplicate rebasing in `Case.with_`**: `api/case.py:Case.with_` (lines 172-202) normalises each edit through `_assign`, calls `substitute()` and `check_document` once for the edits, then computes `_rebased_paths(edited, self._base)` (every relative input and correction path of the copy, resolved against `self._base`) and calls `substitute()` and `check_document` a second time to apply them, setting `_base` on each copy.
- **Four copies of input-path discovery**:
  1. `io/case_paths.py` has `path_fields()` + `input_paths(document)` (lines 617-627, `Path` fields only) + `correction_paths(document)` (lines 630-638), both taking a `CaseDocument`; `api/case.py:_rebased_paths` and `api/sweep.py:plan_sweep` (line 190) each merge the two.
  2. `io/models.py:540-560` has `_correction_leaves()` + `_rebased(body, directory)` (which walks a raw `dict[str, Any]`).
  3. `io/project.py:139-189` has `_correction_leaves()` + `item_inputs(body)` + `rewrite_inputs(body, rewrite)` (which walks a `Mapping[str, Any]` and skips `models.*`).
  4. The `_cursor` helper these walks share lives in `io/models.py:563`, above `io/case_paths.py` in the import order.
- **`VariableRecord` misplaced in `io/models.py`**: `VariableRecord` (`io/models.py:191-301`) is a subclass of `io/variables.py:Resolution`, placed in `io/models.py` only because `VariableRecord.carried` calls `read_mapping`.

### 2. Settled decisions

- **D1.1 (`io` Case reader seam)**: One reader pair, `read_case(path, *, model=CaseDocument)` and `read_case_text(text, *, base=None, source="<string>", model=CaseDocument)`, resolves `variables:` and `models:` directly. It lives at the top of the `io` case stack, in `io/models.py` (corrected by C1.5): `io/case.py` keeps `validate_mapping` and loses its refusing readers, so no import runs upward. Amend `specification/05-software-design/03-1-case-file.md` lines 281–282 and 316–317 to remove the refusal of `models:` and `variables:` on `read_case`.
- **D1.2 (`pipeline/case.py` seam)**: Keep `load_case` and `loads_case` in `pipeline/case.py` as thin registry-checked seams (`read_case` / `read_case_text` + `check_document`).
- **D1.3 (Single-pass `substitute` with `base`)**: Add `base: Path | None = None` to `io/case_paths.py:substitute(document, assignments, *, base=None)` so model swaps, variable resolution, field edits and relative input-path rebasing happen in a single pass. Simplify the two `substitute()` refusal messages when a case has no `models:` or `variables:` to `"write models:/variables: in the case file"`.
- **D1.4 (Unified input-path seam in `io/case_paths.py`)**: Consolidate input-file discovery, rebasing and rewriting in `io/case_paths.py`, with `_cursor` moved down from `io/models.py`, as `input_paths(source: CaseDocument | Mapping[str, Any]) -> dict[str, str]` (today's `input_paths` widened to correction files; every caller that merges `correction_paths` into it drops the merge in the same commit), `rewrite_inputs(body: dict[str, Any], rewrite: Callable[[str, str], str | None]) -> bool`, and `rebase_inputs(body: dict[str, Any], base: Path) -> dict[str, Any]`. Delete `correction_paths()`, `io/project.py:item_inputs()`, `io/models.py:_rebased()` and `api/case.py:_rebased_paths()`.
- **D1.5 (acyclic `io` imports)**: The `io` case modules import one way, `models.py -> variables.py -> case_paths.py -> case.py` (each imports the one after it), with every import at the top of the module (`.claude/rules/python.md`). `VariableRecord` stays in `io/models.py`, since its `carried` calls `read_mapping` there; the earlier proposal to move it into `io/variables.py` is withdrawn (C1.5).

### 3. Concrete code changes

#### `src/nanopnp/io/case_paths.py` — unified input-path seam and single-pass `substitute`

```python
# Before (scattered across io/case_paths.py, io/models.py, io/project.py, and api/case.py):
# - io/case_paths.py: input_paths(document: CaseDocument) -> dict[str, str]  (Path fields only)
# - io/case_paths.py: correction_paths(document: CaseDocument) -> dict[str, str]
# - io/models.py: _rebased(body: dict[str, Any], directory: Path) -> dict[str, Any]
# - io/project.py: item_inputs(body: Mapping[str, Any]) -> dict[str, str]
# - api/case.py: _rebased_paths(case: CaseDocument, base: Path | None) -> dict[str, FieldValue]
# - api/sweep.py:plan_sweep merges input_paths and correction_paths to refuse relative paths

# After (in src/nanopnp/io/case_paths.py; _cursor moves here from io/models.py):
@cache
def _input_leaves() -> tuple[tuple[str, bool], ...]:
    """Return (dotted_path, is_correction) for every leaf that may name an input file."""
    own = tuple((path, False) for path in path_fields() if not path.startswith("models."))
    corrections = (
        ("electrolyte.parameters", True),
        *((f"electrolyte.corrections.{name}.model", True) for name in CORRECTION_PROPERTIES),
    )
    return (*own, *corrections)


def input_paths(source: CaseDocument | Mapping[str, Any]) -> dict[str, str]:
    """Return {dotted_path: written_path} for every input file that ``source`` names."""
    body = (
        source.model_dump(by_alias=True, mode="json")
        if isinstance(source, CaseDocument)
        else source
    )
    found: dict[str, str] = {}
    for dotted, is_correction in _input_leaves():
        parent, last = _cursor(body, dotted)
        value = parent.get(last) if parent is not None else None
        if not isinstance(value, str):
            continue
        if is_correction and not names_a_path(value):
            continue
        found[dotted] = value
    return found


def rewrite_inputs(body: dict[str, Any], rewrite: Callable[[str, str], str | None]) -> bool:
    """Replace each input path of ``body`` where ``rewrite(path, value)`` returns a new string."""
    changed = False
    for dotted in input_paths(body):
        parent, last = _cursor(body, dotted)
        assert parent is not None
        replacement = rewrite(dotted, str(parent[last]))
        if replacement is not None and replacement != parent[last]:
            parent[last] = replacement
            changed = True
    return changed


def rebase_inputs(body: dict[str, Any], base: Path) -> dict[str, Any]:
    """Resolve every relative input path in ``body`` against ``base``."""
    directory = base.resolve()
    rewrite_inputs(
        body,
        lambda _, value: None if Path(value).is_absolute() else str((directory / value).resolve()),
    )
    return body
```

And `substitute` in `src/nanopnp/io/case_paths.py` handles model swaps, variable assignments, leaf edits and optional `base` rebasing in one pass. The model-swap step keeps today's `_model_assignments` expansion of a whole `models:` block and the `field_at(path).validate` check of each swap, and both refusals stay `CaseValidationError`, which `Case.with_` documents:

```python
# After (in src/nanopnp/io/case_paths.py):
def substitute(
    document: D,
    assignments: Mapping[str, FieldValue],
    *,
    base: Path | None = None,
) -> D:
    """Return a validated copy of ``document`` with ``assignments`` applied at their dotted paths."""
    named = {p: v for p, v in assignments.items() if p == "models" or p.startswith("models.")}
    rest = {p: v for p, v in assignments.items() if p not in named}
    current = document
    if named:
        record = current.models_record
        if record is None:
            raise CaseValidationError(
                f"<{document.name}>: {', '.join(sorted(named))}: the case names no model; "
                "write models: in the case file"
            )
        moved = _model_assignments(named)
        for path, value in moved.items():
            field_at(path).validate(value)
        current = record.carried(current, moved)
    if not rest:
        return current
    variables = current.variables_record
    named_variables = sorted(p for p in rest if p == "variables" or p.startswith("variables."))
    if variables is None and named_variables:
        raise CaseValidationError(
            f"<{document.name}>: {', '.join(named_variables)}: the case defines no variables; "
            "write variables: in the case file"
        )
    if variables is not None:
        # VariableRecord.carried gains the same keyword-only ``base``.
        return variables.carried(current, rest, base=base)
    # Plain document without variables: validate, apply edits, rebase if base is given, re-attach models.
    ...
```

#### `src/nanopnp/api/case.py` — `Case.with_` collapses to a single `substitute` call

```python
# Before (src/nanopnp/api/case.py:185-202):
        assignments: dict[str, FieldValue] = {}
        for name, value in given.items():
            self._assign(field_path(name), value, assignments)
        source = f"<{self.name} edited>"
        edited = check_document(substitute(self, assignments), source=source)
        assert isinstance(edited, Case)
        edited._base = self._base
        rebased = _rebased_paths(edited, self._base)
        if rebased:
            edited = check_document(substitute(edited, rebased), source=source)
            assert isinstance(edited, Case)
            edited._base = self._base
        return edited

# After (src/nanopnp/api/case.py):
        assignments: dict[str, FieldValue] = {}
        for name, value in given.items():
            self._assign(field_path(name), value, assignments)
        edited = check_document(
            substitute(self, assignments, base=self._base), source=f"<{self.name} edited>"
        )
        assert isinstance(edited, Case)
        edited._base = self._base
        return edited
```

### 4. Why this improves the architecture & overall impact

- **Maintainability**: Adding a new path-bearing field or a new model kind (such as WP5.09's `models.physics`) no longer requires updating four separate path-discovery sites (`case_paths.py`, `models.py`, `project.py` and the `api` merges) and two `substitute` calls.
- **Extensibility**: `input_paths`, `rewrite_inputs` and `rebase_inputs` form a single deep seam in `io/case_paths.py` that works identically on a `CaseDocument` or an unvalidated YAML mapping (`study`, `molecular`, `continuum`, or `physics` model file).
- **Simplicity**: Leaves one reader pair, `read_case` / `read_case_text` in `io/models.py`, in place of two, and removes `_rebased_paths` and the second substitution from `Case.with_`.

---

## Candidate 2: Deepen Sweep planning and member execution in memory (`REV-199`)

### 1. Architectural diagnosis

In the current codebase, planning and executing a sweep across `api/sweep.py`, `sweep/plan.py` and `api/session.py` crosses the disk boundary unnecessarily and loses cached work at the seam:

1. **Staging directory round-trip in `api/sweep.py:plan_sweep`**: When `plan_sweep(case, ...)` is called (`api/sweep.py:155-240`), it opens a `tempfile.TemporaryDirectory(prefix=".staging-")` inside `sweeps/`, writes the base case and the sweep file there, calls `build_plan(loads_sweep(text, ...), source=staging / SWEEP_FILENAME)` so `build_plan` can read the base case back from disk, writes both files again into `store.sweep_directory(name, staged.hash)`, and then calls `replace(staged, base_path=(directory / BASE_FILENAME).resolve())`.
2. **Silent loss of `resolved_members` (`REV-221`, a regression of `REV-199`)**: `build_plan` attaches the resolved members to the frozen `SweepPlan` via `plan.__dict__["resolved_members"] = resolved` (`sweep/plan.py:654`). Because `resolved_members` is a `@cached_property` and not a dataclass field, `dataclasses.replace(staged, base_path=...)` in `plan_sweep` constructs a fresh `SweepPlan` instance **without** `"resolved_members"` in `__dict__`. Calling `plan_sweep(...).forecast()` re-reads the base case, re-substitutes every point and re-resolves every member. The dropped members were resolved beside the staging directory, which is deleted by then, so they are not safe to carry over either.
3. **Re-substitution and re-resolution during `run_point` and `_parent_artefact`**: Even when `plan.resolved_members` is populated, `api/sweep.py:run_point` calls `plan.case(index, base=base)` (re-substituting from `base_case()`) and passes the `CaseDocument` to `Session._member` -> `Session._walk` -> `run_document`, which calls `resolve(document)` again. `_parent_artefact` (`api/sweep.py:243-275`) calls `plan.case(point.parent, base=base)` and `stored_upstream(document, ..., base=beside)`, which calls `resolve(parent_case)` yet again for every warm-started point!
4. **`Session._member` and `Session._walk`**: `Session._walk` (`api/session.py:146-181`) forwards to `pipeline.run.run_document` with the session's `store`, `workspace`, `overwrite_workspace`, `write` and own stages; `Session._member` (lines 359-364) builds a session with no workspace that keeps the own stages, so a sweep member writes its run directory and shares no stage workspace.

### 2. Settled decisions

- **D2.1 (In-memory `build_plan`)**: `sweep/plan.py:build_plan(document, *, source=None, base: CaseDocument | None = None, check_meshes=True)` takes the base case in memory. Given `base`, it neither reads `base_path` nor checks model files beside it: the model files are checked beside the case's own directory. `api/sweep.py:plan_sweep` builds the plan in memory (its hash does not depend on where the base lies), writes the base case and the sweep file once into `store.sweep_directory(name, plan.hash)`, and points `base_path` there, without a `.staging-*` directory.
- **D2.2 (Resolved members keyed on their directory)**: Replace `plan.__dict__["resolved_members"]` with two non-compared fields, `_resolved_members: tuple[ResolvedCase, ...] | None` and `_resolved_beside: Path | None` (the directory they were resolved beside). `resolved_members` returns the held members only while `_resolved_beside == base_path.parent`; otherwise it runs `base_case()`'s tamper check once, resolves, and caches. A `replace(base_path=...)` therefore never serves members resolved beside another directory.
- **D2.3 (Reuse the resolved members where they are held)**: `run_point` and `_parent_artefact` take a member from `plan.resolved_members` only when the plan already holds them for its directory (an in-process `run_plan`). `_worker`, which reads the plan from disk, resolves only its own point and its parent; it never fills the whole tuple to run one point. `pipeline/run.py:run_document` and `stored_upstream` accept a `resolved: ResolvedCase | None = None` beside the document, so a held member is not resolved again.
- **D2.4 (Keep `Session._walk` and `Session._member`)**: Withdrawn. `Session._walk` carries the session's `workspace`, `overwrite_workspace` and `write` into `run_document`, and `Session._member` holds the rule that a sweep member takes no workspace of its session's. Calling `run_document` with `store=` and `stages=` alone would drop both.

### 3. Concrete code changes

#### `src/nanopnp/sweep/plan.py` — members keyed on their directory, and an in-memory `base`

```python
# Before (src/nanopnp/sweep/plan.py:151-236, 647-655):
@dataclass(frozen=True)
class SweepPlan:
    name: str
    base_path: Path
    base_hash: str
    ...
    variables: Mapping[str, Canonicalisable] = field(default_factory=dict)

    @cached_property
    def resolved_members(self) -> tuple[ResolvedCase, ...]:
        return _resolve_every_point(self.base_case(), self, beside=self.base_path.parent)
...
    resolved = _resolve_every_point(base, plan, beside=base_path.parent)
    ...
    plan.__dict__["resolved_members"] = resolved
    return plan

# After (src/nanopnp/sweep/plan.py):
@dataclass(frozen=True)
class SweepPlan:
    name: str
    base_path: Path
    base_hash: str
    ...
    variables: Mapping[str, Canonicalisable] = field(default_factory=dict)
    _resolved_members: tuple[ResolvedCase, ...] | None = field(
        default=None, repr=False, compare=False
    )
    _resolved_beside: Path | None = field(default=None, repr=False, compare=False)

    @property
    def resolved_members(self) -> tuple[ResolvedCase, ...]:
        """Return every member resolved once beside the base case, in plan order."""
        beside = self.base_path.parent
        if self._resolved_members is not None and self._resolved_beside == beside:
            return self._resolved_members
        built = _resolve_every_point(self.base_case(), self, beside=beside)
        object.__setattr__(self, "_resolved_members", built)
        object.__setattr__(self, "_resolved_beside", beside)
        return built
```

#### `src/nanopnp/api/sweep.py` — in-memory planning

```python
# Before (src/nanopnp/api/sweep.py:224-240):
    with tempfile.TemporaryDirectory(dir=sweeps, prefix=".staging-") as scratch:
        staging = Path(scratch)
        atomic_write_bytes(staging / BASE_FILENAME, base_text)
        atomic_write_bytes(staging / SWEEP_FILENAME, text.encode("utf-8"))
        staged = build_plan(
            loads_sweep(text, source=str(staging / SWEEP_FILENAME)),
            source=staging / SWEEP_FILENAME,
            check_meshes=check_meshes,
        )
    directory = store.sweep_directory(name, staged.hash)
    directory.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(directory / BASE_FILENAME, base_text)
    atomic_write_bytes(directory / SWEEP_FILENAME, text.encode("utf-8"))
    plan = replace(staged, base_path=(directory / BASE_FILENAME).resolve())
    return Sweep(plan, directory, session)

# After (src/nanopnp/api/sweep.py):
    planned = build_plan(loads_sweep(text), base=case, check_meshes=check_meshes)
    directory = store.sweep_directory(name, planned.hash)
    directory.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(directory / BASE_FILENAME, base_text)
    atomic_write_bytes(directory / SWEEP_FILENAME, text.encode("utf-8"))
    # Members resolve again beside the final directory, on first use (D2.2).
    plan = replace(planned, base_path=(directory / BASE_FILENAME).resolve())
    return Sweep(plan, directory, session)
```

And in `_parent_artefact` (`src/nanopnp/api/sweep.py`), for a plan that holds its members:

```python
# After (src/nanopnp/api/sweep.py):
    parent_resolved = plan.resolved_members[point.parent]
    upstream = stored_upstream(
        parent_resolved.document,
        resolved=parent_resolved,
        store=session.store,
        base=plan.base_path.parent,
    )
    key = SolveStage().key(StageInputs(resolved=parent_resolved, upstream=upstream))
```

### 4. Why this improves the architecture & overall impact

- **Maintainability**: The resolved members are explicit fields keyed on the directory they were resolved beside, rather than a hidden `__dict__` entry on a frozen dataclass that `replace` drops (REV-221).
- **Extensibility**: `stored_upstream` and `run_document` accepting a `resolved` case lets any caller that has already resolved one (such as `SweepPlan`, `keyed_walk` or the GUI runner) pass it into the pipeline without repeating `pipeline.case.resolve()`.
- **Simplicity**: Removes the `.staging-*` directory from `plan_sweep`. An in-process sweep resolves each member once for the forecast and the run; a pooled worker resolves its own point and parent only.

---

## Candidate 3: Unify the Stage-5 Region seam and delete `CylindricalPoreGeometry` (`REV-170`, `MOD-03`)

### 1. Architectural diagnosis

As recorded in `REV-170` (`docs/project/review-items.md:2236-2257`), Stage 5's region payload and idealised cylinder geometry suffer from three coupled structural defects:

1. **Six `isinstance(record, IdealisedRegionRecord)` branches outside Qt**: `geometry/region.py:read_region` returns `RegionRecord | IdealisedRegionRecord`, and every consumer has to branch on the concrete type:
   - `mesh/generate.py:239` (`idealised_recipe` vs `resolve_wall_size`)
   - `mesh/generate.py:254` (`mesh_idealised` vs `mesh_region`)
   - `mesh/ingest.py:624-625` (`_sizing` setting `idealised=` and `exclusion=` from `isinstance(record, IdealisedRegionRecord)`)
   - `plot/data.py:209` (`region_drawing` building `RegionDrawing` differently for `IdealisedRegionRecord` vs `RegionRecord`)
   - `cli/building.py:80` (`_mesh` checking `if not isinstance(record, IdealisedRegionRecord):`)
   - `gui/geometry.py:617` (the NiceGUI workbench's region view; the five above are in the library)
2. **Mesh sizing leaked into `geometry/pore.py`**: `CylinderPore.name_edges` (`geometry/pore.py:83`) sets `edge.maxh = wall_h_nm` on `"wall"` edges, mixing stage-6 Netgen mesh sizing into stage-5 geometry construction. `CylinderPore.shape(wall_h_nm=...)` forwards it, and `geometry/analyte.py:PoreWithAnalyte.shape` calls `self.pore.name_edges(glued, wall_h_nm=wall_h_nm)` (line 256).
3. **Duplicate cylinder class and the `MOD-03` (`geometry -> mesh`) upward import edge**:
   - `geometry/pore.py:CylinderPore` (`pore_radius_nm`, `membrane_thickness_nm`, `reservoir_radius_nm`, no defaults) builds the OCC shape; `shape(name_mouths=True)` names the lumen-reservoir seams `interface` by default.
   - `mesh/primitives.py:CylindricalPoreGeometry` (`pore_radius_nm = DEFAULT_PORE_RADIUS_NM`, `membrane_thickness_nm = 13.0`, `reservoir_radius_nm = 50.0`) wraps `CylinderPore` to add defaults, `.generate(maxh_nm=..., wall_h_nm=..., check_quality=...)`, and `shape(name_mouths=False)`, which leaves the seams in netgen's `default` group.
   - `geometry/analyte.py:14` imports `CylindricalPoreGeometry` from `nanopnp.mesh.primitives` under `if TYPE_CHECKING:`, which is the **only** import keeping the upward edge `- {from: geometry, to: mesh, relation: static, finding: MOD-03}` in `docs/project/modularity-layering.yaml`!

### 2. Settled decisions

- **D3.1 (Shared `Stage5Region` interface and `RegionOutlines` in `geometry/region.py`)**: Define `RegionOutlines` (`pore_nm`, `membrane_nm`, `exclusion_nm`, `membrane_half_thickness_nm`, `reservoir_radius_nm`, `z_extent_nm`) and a `Stage5Region` protocol in `geometry/region.py`. Implement `.outlines_nm() -> RegionOutlines`, `.has_exclusion -> bool`, and `.is_idealised -> bool` on both `RegionRecord` and `IdealisedRegionRecord` so `plot/data.py`, `mesh/ingest.py`, `cli/building.py` and `gui/geometry.py` never call `isinstance(record, IdealisedRegionRecord)`.
- **D3.2 (Move `edge.maxh = wall_h_nm` from `geometry/pore.py` to `mesh/`)**: `CylinderPore.shape()` and `CylinderPore.name_edges()` in `geometry/pore.py` only name OCC faces and edges (`"axis"`, `"wall"`, `"membrane"`, `"membrane_outer"`, `"cis"`, `"trans"`, `"interface"`). `mesh/idealised.py` and the analyte mesher set the wall size through `mesh/sizing.py`'s existing `apply_sizes` / `edge_size` (no new sizing loop) before Netgen meshing, preserving identical OCC topology. `PoreWithAnalyte.shape` drops its `wall_h_nm` argument to `name_edges` in the same commit.
- **D3.3 (Delete `CylindricalPoreGeometry` and drop `MOD-03`)**: Give `CylinderPore` in `geometry/pore.py` default dimensions (`pore_radius_nm: float = 2.0`, `membrane_thickness_nm: float = 13.0`, `reservoir_radius_nm: float = 50.0`), provide `mesh_cylinder_pore(pore: CylinderPore = CylinderPore(), *, maxh_nm: float = DEFAULT_MAXH_NM, wall_h_nm: float = DEFAULT_CYLINDER_WALL_H_NM, name_mouths: bool = False, check_quality: bool = True) -> GeneratedMesh` in `mesh/primitives.py` (delegating to `mesh/idealised.py`; `name_mouths=False` keeps today's boundary groups for every caller of `CylindricalPoreGeometry`), update `geometry/analyte.py:PoreWithAnalyte`, `post/indicator.py:lumen_band`, and test callers, and remove `- {from: geometry, to: mesh, relation: static, finding: MOD-03}` from `docs/project/modularity-layering.yaml`.
- **D3.4 (Single entry point in `mesh/generate.py`)**: Have `mesh_region(record, sizing)` and `region_recipe(record, sizing)` in `mesh/generate.py` dispatch polymorphically on `record.is_idealised` / `Stage5Region` so `MeshStage.key` and `MeshStage.run` call one function for both region kinds.

### 3. Concrete code changes

#### `src/nanopnp/geometry/region.py` & `src/nanopnp/plot/data.py` — `RegionOutlines` and `Stage5Region`

```python
# In src/nanopnp/geometry/region.py:
@dataclass(frozen=True, eq=False)
class RegionOutlines:
    """The 2D (r, z) polygon outlines of a stage-5 region in nm."""

    pore_nm: np.ndarray
    membrane_nm: np.ndarray
    exclusion_nm: np.ndarray | None
    membrane_half_thickness_nm: float
    reservoir_radius_nm: float
    z_extent_nm: tuple[float, float]


class Stage5Region(Protocol):
    """Any stage-5 region record that read_region returns."""

    @property
    def is_idealised(self) -> bool: ...
    @property
    def has_exclusion(self) -> bool: ...
    def outlines_nm(self) -> RegionOutlines: ...
```

Then `plot/data.py:region_drawing` (`lines 201-244`) shrinks from 44 lines with an `isinstance` branch to 18 lines with zero branching:

```python
# After (in src/nanopnp/plot/data.py):
def region_drawing(artefact: Artefact) -> RegionDrawing | None:
    """Return the region record's outlines, or None without its payload."""
    path = _payload(artefact, REGION_PAYLOAD)
    if path is None:
        return None
    record = read_region(path)
    outlines = record.outlines_nm()
    return RegionDrawing(
        pore_m=outlines.pore_nm * _NM,
        membrane_m=outlines.membrane_nm * _NM,
        exclusion_m=None if outlines.exclusion_nm is None else outlines.exclusion_nm * _NM,
        membrane_half_thickness_m=outlines.membrane_half_thickness_nm * _NM,
        reservoir_radius_m=outlines.reservoir_radius_nm * _NM,
        z_extent_m=(outlines.z_extent_nm[0] * _NM, outlines.z_extent_nm[1] * _NM),
        record=record,
    )
```

#### `src/nanopnp/geometry/pore.py` & `src/nanopnp/mesh/idealised.py` — move `wall_h_nm` sizing into `mesh/`

```python
# Before (src/nanopnp/geometry/pore.py:55-84):
    def shape(self, *, wall_h_nm: float | None = None, name_mouths: bool = True) -> Shape:
        ...
        self.name_edges(glued, wall_h_nm=wall_h_nm)
        return glued

    def name_edges(self, glued: TopoDS_Shape, *, wall_h_nm: float | None = None) -> None:
        ...
            elif self._on_wall(r, z, half_m, eps):
                edge.name = "wall"
                if wall_h_nm is not None:
                    edge.maxh = wall_h_nm

# After (src/nanopnp/geometry/pore.py):
    def shape(self, *, name_mouths: bool = True) -> Shape:
        ...
        self.name_edges(glued)
        return glued

# And in src/nanopnp/mesh/idealised.py, through the sizing mesh/ already has:
    shape = record.geometry().shape(name_mouths=name_mouths)
    for edge in shape.edges:
        size = edge_size(str(edge.name), z_mid(edge), wall_h_nm=wall_h_nm, ...)
        if size is not None:
            edge.maxh = size
```

#### `src/nanopnp/geometry/analyte.py` & `docs/project/modularity-layering.yaml` — eliminate `MOD-03`

```python
# Before (src/nanopnp/geometry/analyte.py:13-22):
if TYPE_CHECKING:
    from netgen.occ import TopoDS_Shape
    from nanopnp.mesh.primitives import CylindricalPoreGeometry


@dataclass(frozen=True)
class PoreWithAnalyte:
    pore: CylindricalPoreGeometry
    analyte: SphereAnalyte


# After (src/nanopnp/geometry/analyte.py):
from nanopnp.geometry.pore import CylinderPore


@dataclass(frozen=True)
class PoreWithAnalyte:
    pore: CylinderPore
    analyte: SphereAnalyte
```

### 4. Why this improves the architecture & overall impact

- **Maintainability**: Closes `REV-170` and `MOD-03` in one stroke. `geometry` no longer imports `mesh` even under `if TYPE_CHECKING:`, shrinking `docs/project/modularity-layering.yaml`.
- **Extensibility**: Adding a second idealised pore shape (e.g. a conical or hourglass pore) only requires implementing the `Stage5Region` methods in `geometry/pore.py`; `plot/data.py`, `mesh/ingest.py`, `mesh/generate.py` and `cli/building.py` work without new `isinstance` branches.
- **Simplicity**: Deletes `CylindricalPoreGeometry` as a duplicate class and keeps CAD topology in `geometry/` and Netgen sizing in `mesh/`. With `name_mouths=False` carried into `mesh_cylinder_pore` and the wall size set before meshing, the meshes and `VER-62`'s golden hashes are unchanged; the implementing package confirms that with the VER-62 test, not by argument.

---

## Candidate 4: Concentrate effective atom radii and Charge edit scaling in `ProtonationTable` (`REV-218`)

### 1. Architectural diagnosis

`ProtonationTable` (`structure/protonated.py`) is the stage-7 protonation payload read by stage 2 (`density`), stage 4 (`geometry/contour.py` via `RadiusEdit`), and stage 7 (`charge/edits.py`, `charge/kernel.py`). Currently, operations that belong to `ProtonationTable` and its radius edits leak across four subpackages:

1. **Unscaled radii returned by `resolve_protonated_radii`**: `density/radii.py:resolve_protonated_radii(name, table)` resolves CHARMM van der Waals radii for `table` but ignores the table's own radius edits (`table.header["edits"]`), forcing `density/stage.py:162-163` to remember to call `radii = resolve_protonated_radii(...)` and then multiply `radii_nm = radii.radii_nm * radius_scales(table)`. Any caller of `resolve_protonated_radii` that forgets the second step silently gets unedited radii.
2. **Duplicated atom-to-residue indexing**: Both `charge/edits.py:_owner(table)` (lines 74-96) and `density/radii.py:resolve_protonated_radii` (lines 209-229) build a `(chain, resid, icode) -> residue_index` dictionary from `table.residue_chain`, `table.residue_resid`, `table.residue_icode` and map every atom's `(chain, resid, icode)` to its residue index. They differ on an atom with no residue row: `_owner` raises `KeyError`, while `resolve_protonated_radii` maps it to `-1` and leaves it unpatched (`residues >= 0`).
3. **Scattered `RadiusEdit` conversion**: `structure/protonated.py:radius_scales(table)` parses `table.header["edits"]` into `RadiusEdit = (parent, resid, icode, factor)` tuples; `geometry/contour.py:probe_radius_edits(resolved)` converts `resolved.protonation.edits` (`ResolvedEdit`) into `RadiusEdit` tuples; and `geometry/contour.py:gate_inputs` calls `residue_radius_scales(ensemble.resname, ensemble.resid, ensemble.icode, radius_edits)`.

### 2. Settled decisions

- **D4.1 (Methods on `ProtonationTable` and scaled `resolve_protonated_radii`)**: Add `table.atom_residue_index() -> np.ndarray` and `table.radius_scales() -> np.ndarray` as methods on `ProtonationTable` in `structure/protonated.py`. Have `density/radii.py:resolve_protonated_radii(name, table)` apply `table.radius_scales()` internally so its returned `ResolvedRadii.radii_nm` are already the effective radii (and `density/stage.py` simply uses `radii.radii_nm`). Use `table.atom_residue_index()` in both `charge/edits.py` (replacing `_owner(table)`) and `density/radii.py:resolve_protonated_radii`. It maps an atom with no residue row to `-1`, as `resolve_protonated_radii` does today; `charge/edits.py` refuses a `-1` it would edit, naming the atom, where `_owner` raised a bare `KeyError`.
- **D4.2 (One edit-to-scale path in `structure/protonated.py`)**: Keep `residue_radius_scales(resname, resid, icode, edits: Sequence[RadiusEdit])` as the one scaling function, typed on `RadiusEdit` alone. Each other encoding converts to `RadiusEdit` at its own boundary: the table's header edits in `ProtonationTable.radius_edits()` (today's parsing in `radius_scales`), and a case's `ResolvedEdit`s in `geometry/contour.py:probe_radius_edits`. `ProtonationTable.radius_scales()`, `density/radii.py` and `geometry/contour.py` then share one path, with no function that tells three edit shapes apart. Also update `charge/kernel.py:20` to import `ProtonationTable` from `nanopnp.structure.protonated`.

### 3. Concrete code changes

#### `src/nanopnp/structure/protonated.py` — `atom_residue_index()` and `radius_scales()`

```python
# In src/nanopnp/structure/protonated.py:
class ProtonationTable:
    ...

    def atom_residue_index(self) -> np.ndarray:
        """Return each atom's index into ``residue_*``, -1 for an atom with no residue row."""
        import numpy as np

        index = {
            (str(chain), int(resid), str(icode)): number
            for number, (chain, resid, icode) in enumerate(
                zip(
                    self.residue_chain.tolist(),
                    self.residue_resid.tolist(),
                    self.residue_icode.tolist(),
                    strict=True,
                )
            )
        }
        return np.array(
            [
                index.get((str(chain), int(resid), str(icode)), -1)
                for chain, resid, icode in zip(
                    self.chain.tolist(), self.resid.tolist(), self.icode.tolist(), strict=True
                )
            ],
            dtype=np.intp,
        )

    def radius_scales(self) -> np.ndarray:
        """Return the factor of each atom's radius that the table's radius edits set, 1 elsewhere."""
        return residue_radius_scales(self.resname, self.resid, self.icode, self.radius_edits())
```

#### `src/nanopnp/density/radii.py` & `src/nanopnp/density/stage.py` — `resolve_protonated_radii` returns effective scaled radii

```python
# Before (src/nanopnp/density/stage.py:162-163):
            radii = resolve_protonated_radii(KERNEL_RADII[spec.kernel], table)
            radii_nm = radii.radii_nm * radius_scales(table)

# After (in src/nanopnp/density/radii.py:resolve_protonated_radii):
    residues = table.atom_residue_index()
    ...
    return ResolvedRadii(
        radii_nm=radii_A * ANGSTROM_TO_NM * table.radius_scales(),
        name=radius_set.name,
        sha256=radius_set_digest(name),
    )

# And in src/nanopnp/density/stage.py:162:
            radii = resolve_protonated_radii(KERNEL_RADII[spec.kernel], table)
            radii_nm = radii.radii_nm
```

### 4. Why this improves the architecture & overall impact

- **Maintainability**: Eliminates a temporal-coupling hazard where callers of `resolve_protonated_radii` could forget to multiply by `radius_scales(table)`, and removes duplicate atom-to-residue indexing loops in `charge/edits.py` and `density/radii.py`.
- **Extensibility**: `ProtonationTable` becomes a self-contained domain object for frame slicing, atom-to-residue mapping and radius-edit scaling.
- **Simplicity**: Shrinks `charge/edits.py`, `density/radii.py`, `density/stage.py` and `geometry/contour.py` while keeping all edit parsing in `structure/protonated.py`.

---

## Candidate 5: Type Model files and absorb metadata stripping into `io/models.py` (`REV-219`)

### 1. Architectural diagnosis

In `io/models.py`, `_read_model_file(kind, path, source)` reads a model YAML file, checks its `schema` and `name`, rejects `models:` and variable expressions, checks that every leaf belongs to `owner_of(leaf) == kind`, strips `("schema", "name")` into `body`, and returns `(ModelFile(kind, name, path, sha256), _rebased(body, path.parent))`.

Because `ModelFile` discards `body` and `_read_model_file` is private:
- `api/project.py` defines its own `_body(location, *, keep=False)` (`lines 670-677`) that calls `yaml.safe_load` and strips `("schema", "name")` when `keep=False`.
- The only reason `_body(location)` ever stripped `("schema", "name")` was for `api/project.py:401`: `mapping_changes(_body(self.path(kind, name)))`, because `io/defaults.py:mapping_changes` did not ignore `"schema"` and `"name"` (and a model file's `schema: nanopnp/molecular-model/v0.6` differs from `CaseDocument`'s default `schema: nanopnp/case/v0.6`).
- `api/project.py` also duplicates `io/models.py:_put` verbatim (`api/project.py:658` vs `io/models.py:725`) and implements case-to-model layer splitting (`Project._split`, `lines 307-334`) outside `io/models.py`.

### 2. Settled decisions

- **D5.1 (`ModelFile.body` and `read_model_file` in `io/models.py`)**: Add `body: Mapping[str, Any]` (the validated model content without metadata keys) to `ModelFile` and expose `read_model_file(kind, path, *, rebase=True, source=None) -> ModelFile` in `io/models.py` (replacing `check_model_file`). The sketches assume the code as WP5.09 leaves it: `ModelKind` names the literal type of `MODEL_KINDS` once it holds `physics` (today `Literal["molecular", "continuum"]`, with no alias), and `exposes` is the key WP5.09 adds to a model file.
- **D5.2 (`split_case_layers` in `io/models.py` and metadata filtering in `io/defaults.py:mapping_changes`)**: Move `split_case_layers` (splitting a case mapping into owned model layers and the `study` layer, keeping `expressions` pinned to `study`) into `io/models.py`, sharing `_put`. Have `io/defaults.py:mapping_changes` ignore metadata keys (`"schema"`, `"name"`, `"models"`, `"exposes"`) directly, eliminating the `keep: bool = False` flag on `_body` in `api/project.py`.

### 3. Concrete code changes

#### `src/nanopnp/io/models.py` — `ModelFile.body`, `read_model_file`, and `split_case_layers`

```python
# In src/nanopnp/io/models.py:
@dataclass(frozen=True, eq=False)
class ModelFile:
    """One model file a study read: its kind, its name, its location, its digest and its body."""

    kind: ModelKind
    name: str
    path: Path
    sha256: str
    body: Mapping[str, Any] = field(default_factory=dict)


def read_model_file(
    kind: ModelKind,
    path: str | Path,
    *,
    rebase: bool = True,
    source: str | None = None,
) -> ModelFile:
    """Read and validate a model file; rebase its relative input paths when ``rebase`` is True."""
    location = Path(path)
    label = source if source is not None else str(location)
    ...
    body = {key: value for key, value in raw.items() if key not in ("schema", "name")}
    ...
    content = rebase_inputs(copy.deepcopy(body), location.parent) if rebase else body
    return ModelFile(kind, name, location, file_hash(location), content)


def split_case_layers(
    raw: Mapping[str, Any],
    *,
    pinned: AbstractSet[str] = frozenset(),
) -> dict[Kind, dict[str, Any]]:
    """Split a case mapping into its model layers and the study layer by ``owner_of``."""
    layers: dict[Kind, dict[str, Any]] = {kind: {} for kind in (*MODEL_KINDS, "study")}
    for path, value in leaves(raw):
        if value is None or path in ("schema", "name", "models"):
            continue
        target: Kind = "study" if path in pinned else owner_of(path)
        _put(layers[target], path, value)
    return layers
```

#### `src/nanopnp/io/defaults.py` — `mapping_changes` ignores document metadata keys

```python
# Before (src/nanopnp/io/defaults.py:301-304):
def mapping_changes(body: Mapping[str, Any]) -> tuple[Change, ...]:
    """Return each leaf of a case or model mapping that is away from its default, by path."""
    found = (_away(path, value) for path, value in leaves(body))
    return tuple(sorted((c for c in found if c is not None), key=lambda c: c.path))


# After (src/nanopnp/io/defaults.py):
_METADATA_KEYS: frozenset[str] = frozenset({"schema", "name", "models", "exposes"})


def mapping_changes(body: Mapping[str, Any]) -> tuple[Change, ...]:
    """Return each leaf of a case or model mapping that is away from its default, by path."""
    found = (
        _away(path, value)
        for path, value in leaves(body)
        if path.split(".", 1)[0] not in _METADATA_KEYS
    )
    return tuple(sorted((c for c in found if c is not None), key=lambda c: c.path))
```

### 4. Why this improves the architecture & overall impact

- **Maintainability**: Model-file parsing, ownership checking and case-to-model splitting live in one place (`io/models.py`), rather than being split between `io/models.py` and `api/project.py`.
- **Extensibility**: Directly supports WP5.09 (`The physics model`), which adds `physics` to `MODEL_KINDS` and `exposes:` to `physics` model files (`docs/plans/phase-5/wp5.09-the-physics-model.md`). With `split_case_layers` and `_METADATA_KEYS` in `io/`, `Project.import_case` and `Project.changes` automatically generalize across all `MODEL_KINDS`.
- **Simplicity**: Removes duplicate `_put` and `_body(..., keep=False)` from `api/project.py` and makes `ModelFile` carry the validated body it already parsed.

---

## Candidate 6: Merge dry-run rebuild forecasting into the pipeline stage walker (`REV-220`)

### 1. Architectural diagnosis

Walking the selected stages of a `ResolvedCase` to compute their `StageInputs`, construct each `Stage` (passing `store=store` when `description.takes_store` is true), compute `stage.key(inputs)` and check whether the `Store` already holds the artefact is written three times. The run's walk already has the shared pieces as `_Walk.describe`, `_Walk.inputs` and `_Walk.construct` (`pipeline/run.py:554-582`); the other two loops do not use them:

1. `pipeline/run.py:_Walk` + `_walk` + `_resolve_stage` (`lines 541-584, 727-763, 1130-1198`)
2. `pipeline/run.py:stored_upstream` (`lines 1099-1127`) — which also forgot to accept `stages: Mapping[str, FunctionStage] | None = None`
3. `pipeline/forecast.py:keyed_walk` (`lines 51-124`) — a 124-line file imported only by `src/nanopnp/sweep/forecast.py:10` (`from nanopnp.pipeline.forecast import Identity, keyed_walk`).

### 2. Settled decisions

- **D6.1 (Unify stage keying in `pipeline/run.py`)**: Use `_Walk.describe` and `_Walk.inputs` in `stored_upstream()` and `keyed_walk()`, and add `_Walk.keyed(name)`, which builds a stage for keying only: `create(name, store=...)` when the description takes the store, and no workspace. `_Walk.construct` makes a scratch workspace for a `takes_workspace` stage, so a forecast or an upstream lookup that called it would write directories to the store. Add `_Walk.stored(name, key)` for the payload-bearing lookup; a `key_is_artefact` stage keeps returning its key with no store I/O in `stored_upstream`.
- **D6.2 (Delete `src/nanopnp/pipeline/forecast.py`)**: Move `FORECAST_SCHEMA`, `Identity`, `_NotBuiltPayload`, and `keyed_walk` into `src/nanopnp/pipeline/run.py`, update `src/nanopnp/sweep/forecast.py` to import `Identity` and `keyed_walk` from `nanopnp.pipeline.run`, and delete `src/nanopnp/pipeline/forecast.py`.

### 3. Concrete code changes

#### `src/nanopnp/pipeline/run.py` — shared `_Walk` keying methods used by `_walk`, `stored_upstream`, and `keyed_walk`

```python
# In src/nanopnp/pipeline/run.py:
@dataclass
class _Walk:
    ...

    def keyed(self, name: str) -> Stage:
        # Built to compute a key only: no workspace, so no scratch directory is made.
        if name in self.own:
            return self.own[name]
        if self.describe(name).takes_store:
            return create(name, store=self.store)
        return create(name)

    def stored(self, name: str, key: Artefact) -> tuple[bool, Artefact | None]:
        if self.describe(name).key_is_artefact:
            return self.store.contains(key), key
        found = self.store.get(key.schema, key.hash)
        return (found is not None), found
```

With `_Walk.describe(name)`, `_Walk.inputs(name)`, `_Walk.keyed(name)` and `_Walk.stored(name, key)` shared in `pipeline/run.py`:

```python
# stored_upstream in src/nanopnp/pipeline/run.py:
def stored_upstream(
    case: CaseDocument | ResolvedCase,
    *,
    store: Store,
    feeding: str = "solve",
    base: Path | None = None,
    stages: Mapping[str, FunctionStage] | None = None,
) -> dict[str, Artefact]:
    """Return the artefacts a walk hands ``feeding``, read from the store without running a stage."""
    resolved = case if isinstance(case, ResolvedCase) else resolve(case, base=base)
    walk = _Walk(
        document=resolved.document,
        resolved=resolved,
        store=store,
        arguments={},
        workspace=None,
        only=True,
        own=dict(stages or {}),
    )
    for name in selected_stages(resolved, feeding, stages=walk.own)[:-1]:
        key = walk.keyed(name).key(walk.inputs(name))
        if walk.describe(name).key_is_artefact:
            walk.artefacts[name] = key
            continue
        _, stored = walk.stored(name, key)
        if stored is None:
            raise MissingUpstreamError(
                f"stage {name!r} of case {walk.document.name!r} produces {key.schema} "
                f"{key.short_hash}, which is not in the store at {store.root}"
            )
        walk.artefacts[name] = stored
    return walk.artefacts
```

And `keyed_walk` lives right beside `stored_upstream` in `pipeline/run.py`, using the exact same `_Walk` instance:

```python
# keyed_walk in src/nanopnp/pipeline/run.py:
def keyed_walk(
    resolved: ResolvedCase,
    *,
    store: Store,
    stages: Mapping[str, FunctionStage] | None = None,
    planned: set[str],
) -> dict[str, Identity]:
    """Return each stage's identity for ``resolved``, running none of them."""
    walk = _Walk(
        document=resolved.document,
        resolved=resolved,
        store=store,
        arguments={},
        workspace=None,
        only=True,
        own=dict(stages or {}),
    )
    identities: dict[str, Identity] = {}
    for name in selected_stages(resolved, None, stages=walk.own):
        description = walk.describe(name)
        stage = walk.keyed(name)
        inputs = walk.inputs(name)
        try:
            key = stage.key(inputs)
        except NotBuilt:
            digest = _forecast_digest(name, stage, description, inputs, resolved, identities)
            built = digest not in planned
            planned.add(digest)
            identities[name] = Identity(digest, built)
            walk.artefacts[name] = Artefact(
                schema=description.artefact_schema,
                parameters={"forecast": digest},
                payload=_NotBuiltPayload(name),
            )
            continue
        held, stored = walk.stored(name, key)
        walk.artefacts[name] = stored if stored is not None else _standing_in(key, name)
        built = not held and key.hash not in planned
        if not held:
            planned.add(key.hash)
        identities[name] = Identity(key.hash, built)
    return identities
```

### 4. Why this improves the architecture & overall impact

- **Maintainability**: Stage description, `StageInputs` assembly, keying-only construction and store-hit semantics (`key_is_artefact` vs `store.get`) are defined once on `_Walk` in `pipeline/run.py`. Any change to how stages are constructed or keyed automatically applies to live runs, warm-start parent lookups, and dry-run sweep forecasts.
- **Extensibility**: `stored_upstream` gains support for custom `FunctionStage` extensions (`stages=`) and `ResolvedCase` inputs for free.
- **Simplicity**: Deletes `src/nanopnp/pipeline/forecast.py` (124 lines) and removes duplicated stage-walking boilerplate.

---

## Overall codebase impact summary

| Dimension | Architectural effect across all 6 candidates |
|---|---|
| **Layering (`VER-61`, `VER-72`)** | Eliminates the `MOD-03` (`geometry -> mesh`) static upward edge from `docs/project/modularity-layering.yaml`; keeps the `io` case modules importing one way (`models.py -> variables.py -> case_paths.py -> case.py`), all at the top of the module, with zero new `upward` or `deferred_upward` edges. |
| **Modules deleted / consolidated** | Deletes `src/nanopnp/pipeline/forecast.py` and `mesh/primitives.py:CylindricalPoreGeometry`; replaces `io.models.read`/`reads` and the refusing `io.case.read_case`/`read_case_text` with one resolving pair in `io/models.py`; moves `_cursor` into `io/case_paths.py`. `VariableRecord`, `Session._member` and `Session._walk` stay. |
| **Locality of change (after WP5.09)** | The candidates land after WP5.09 (`The physics model`), by a Phase 5 amendment. Concentrating input-path discovery in `io/case_paths.py` and model-file reading / layer splitting in `io/models.py` then lets the later workbench suites extend a single seam rather than patching parallel walkers in `io/`, `api/`, `mesh/`, and `plot/`; the refactor itself covers the `physics` kind WP5.09 adds. |
| **Performance & correctness** | Fixes the `REV-221` `dataclasses.replace` cache drop on `SweepPlan` by keying the held members on their directory, eliminates the `.staging-*` round-trip in `plan_sweep`, and prevents unscaled CHARMM radii in `resolve_protonated_radii`; the `VER-62` golden hashes are to be confirmed unchanged by their test. |

## Corrections from the review of this report (7 November 2026)

`/code-review high` of this report against the code found the following; each is folded into the candidate above and binds the post-WP5.09 amendment.

| # | Candidate | Correction |
|---|---|---|
| C1.1 | 1 | The `substitute` sketch keeps `_model_assignments` (a whole `models:` block expands to `models.<kind>`, a non-mapping is refused) and `field_at(path).validate` for each model swap. Both refusals stay `CaseValidationError`, not `UnknownCasePathError` (a `KeyError`). The duplicated `variables.carried` branch is one call; `VariableRecord.carried` gains `base`. |
| C1.2 | 1 | `Case.with_` keeps `_assign`, `check_document` and `_base` on the copy. `Case` has no `_source`; the base is `self._base`. The quoted Before is the code at `api/case.py:185-202`. |
| C1.3 | 1 | `input_paths` already exists (Path fields only). Widening it to correction files removes the `correction_paths` merges in `api/case.py` and `api/sweep.py` in the same commit. `_cursor` moves down into `io/case_paths.py`. |
| C1.5 | 1 | The `io` imports run `models.py -> variables.py -> case_paths.py -> case.py`. Moving `VariableRecord` into `variables.py`, or the resolving reader into `case.py`, would need an upward import that `.claude/rules/python.md` forbids deferring. The resolving `read_case` pair lives in `io/models.py`, and `VariableRecord` stays there. |
| C2.1 | 2 | `build_plan` takes the base in memory and, given it, reads no file at `base_path`. The earlier sketch's `case.source.path or Path(...)` read the unedited file or the working directory. |
| C2.2 | 2 | The held members are keyed on the directory they were resolved beside, and `base_case()` runs once when the cache fills. Carrying them across `replace(base_path=...)` served members resolved beside the deleted staging directory. |
| C2.3 | 2 | A pooled `_worker` reads the plan from disk and resolves only its point and parent. Indexing `resolved_members` there resolved all N members per point, O(N²) per sweep. |
| C2.4 | 2 | `Session._walk` and `Session._member` stay: they carry the workspace, `write` and `overwrite_workspace` settings and the member's no-workspace rule. |
| C3.1 | 3 | Six branches, not five: `gui/geometry.py:617` is in the NiceGUI workbench. |
| C3.2 | 3 | `CylinderPore`'s field is `pore_radius_nm`. `mesh_cylinder_pore` passes `name_mouths=False`, as `CylindricalPoreGeometry.shape` does; otherwise the mouth seams become `interface` boundaries and the meshes change. `PoreWithAnalyte.shape` drops `wall_h_nm` with `name_edges`. The wall size goes through `mesh/sizing.py`, not a new loop. `RegionOutlines` takes `eq=False`, since its fields are arrays. |
| C4.1 | 4 | `atom_residue_index` maps an atom without a residue row to `-1`, as `resolve_protonated_radii` does; `charge/edits.py` refuses such an atom by name. |
| C4.2 | 4 | `residue_radius_scales` stays typed on `RadiusEdit`; each other encoding converts at its own boundary. |
| C5.1 | 5 | `ModelKind` and `exposes` are post-WP5.09 names; the sketches are re-read against WP5.09's code. |
| C6.1 | 6 | `_Walk.describe`, `inputs` and `construct` already exist. Keying uses a new `_Walk.keyed`, never `construct`, which makes scratch workspaces. `stored_upstream` does no store I/O for a `key_is_artefact` stage. |
| C0 | all | Line references and Before blocks are corrected to the code at `8a9b5ce`. REV-217 to REV-221 are registered open, to land after WP5.09 by a Phase 5 amendment. REV-170 stays accepted for WP5.17 until that amendment rules. |
