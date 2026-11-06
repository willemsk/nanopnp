# Code review 036: architectural deepening review (`io`, `pipeline`, `sweep`, `geometry`, `mesh`, `structure`, `charge`, `api`)

2026-11-06 · branch `improve_codebase_architecture` · scope: whole repository (`src/nanopnp/`, `specification/05-software-design/`, `docs/project/modularity-layering.yaml`, `docs/project/review-findings.md`, `docs/project/review-items.md`) · focus: module depth, interface seams, locality of change and elimination of cross-module pass-throughs (`/improve-codebase-architecture`)

## Summary

A full architectural review of `src/nanopnp` examined the subpackage boundaries against the recorded layering (`docs/project/modularity-layering.yaml`, `VER-61`), the deferred-import guard (`VER-72`), the Phase 5 workbench architecture (`docs/plans/phase-5-workbench.md`, `docs/plans/wp5.09-the-physics-model.md`) and the review register (`docs/project/review-items.md`).

Six shallow seams were identified, explored and settled with the author through interactive design rounds:

1. **Candidate 1 — Collapse Case file reading, substitution and input-path rebasing** (`io/case.py`, `io/case_paths.py`, `io/variables.py`, `io/models.py`, `io/project.py`, `pipeline/case.py`, `api/case.py`)
2. **Candidate 2 — Deepen Sweep planning and member execution in memory** (`sweep/plan.py`, `api/sweep.py`, `api/session.py`, `pipeline/run.py`)
3. **Candidate 3 — Unify the Stage-5 Region seam and delete `CylindricalPoreGeometry` (`REV-170`, `MOD-03`)** (`geometry/region.py`, `geometry/pore.py`, `geometry/analyte.py`, `mesh/primitives.py`, `mesh/idealised.py`, `mesh/generate.py`, `mesh/ingest.py`, `plot/data.py`, `post/indicator.py`, `cli/building.py`)
4. **Candidate 4 — Concentrate effective atom radii and Charge edit scaling in `ProtonationTable`** (`structure/protonated.py`, `charge/edits.py`, `charge/kernel.py`, `density/radii.py`, `density/stage.py`, `geometry/contour.py`)
5. **Candidate 5 — Type Model files and absorb metadata stripping into `io/models.py`** (`io/models.py`, `io/defaults.py`, `api/project.py`)
6. **Candidate 6 — Merge dry-run rebuild forecasting into the pipeline stage walker** (`pipeline/run.py`, `pipeline/forecast.py`, `sweep/forecast.py`)

---

## Provisional findings and `REV` / `MOD` updates

### Updates to existing findings

| ID | Area | Status change | Summary of update |
|---|---|---|---|
| **REV-170** | coupling | `open` → settled design ready for WP5.12 (or earlier structural pass) | Unifies `RegionRecord` and `IdealisedRegionRecord` behind a `Stage5Region` protocol and `RegionOutlines` value object in `geometry/region.py`, moves `edge.maxh = wall_h_nm` out of `geometry/pore.py` into `mesh/`, deletes `mesh/primitives.py:CylindricalPoreGeometry` in favour of `geometry/pore.py:CylinderPore` + `mesh/primitives.py:mesh_cylinder_pore()`, and removes all five `isinstance(record, IdealisedRegionRecord)` branches outside Qt. |
| **MOD-03** | layering | `accepted` static edge (`geometry -> mesh`) → **removed** | Deleting `CylindricalPoreGeometry` and typing `PoreWithAnalyte.pore` as `CylinderPore` in `geometry/analyte.py` removes the sole `if TYPE_CHECKING:` import from `geometry` up to `mesh`, shrinking `edges:` in `docs/project/modularity-layering.yaml`. |
| **REV-199** | performance | `fixed` → regression on `api.sweep.plan_sweep` identified and closed | `build_plan` seeded `plan.__dict__["resolved_members"]` on a `frozen=True` dataclass, which `dataclasses.replace(staged, base_path=...)` in `api/sweep.py:plan_sweep` silently dropped when moving the plan out of its `.staging-*` folder. Replaced by an explicit `_resolved_members: tuple[ResolvedCase, ...] | None = field(default=None, repr=False, compare=False)` field on `SweepPlan` plus in-memory planning (`base: CaseDocument | None = None`), and extended to `run_point` and `_parent_artefact` so sweep execution reuses the resolved members too. |
| **REV-200** | coupling | `fixed` → completed by moving `VariableRecord` to `io/variables.py` | Moving `VariableRecord` from `io/models.py` into `io/variables.py` beside `Resolution` and `Variable` places the variable resolution and its record in one module while keeping the top-level `io` import graph strictly acyclic (`case.py -> case_paths.py -> variables.py -> models.py`). |

### Provisional new findings (`REV-217` to `REV-220`)

| Provisional ID | Area | Severity | Location | Finding |
|---|---|---|---|---|
| **REV-217** | coupling | low | `src/nanopnp/io/case.py`, `src/nanopnp/io/models.py`, `src/nanopnp/io/case_paths.py`, `src/nanopnp/io/project.py`, `src/nanopnp/api/case.py` | **Case reading, substitution and input-path discovery are split across four `io` modules and `api/case.py`.** `io.case.read_case` refuses `models:` and `variables:` while `io.models.read` resolves them; `Case.with_` calls `substitute()` twice and re-implements path rebasing (`_rebased_paths`); and input-file discovery is implemented three times (`io/case_paths.py`, `io/models.py:_rebased`, `io/project.py:item_inputs`). |
| **REV-218** | coupling | low | `src/nanopnp/structure/protonated.py`, `src/nanopnp/charge/edits.py`, `src/nanopnp/density/radii.py`, `src/nanopnp/density/stage.py`, `src/nanopnp/geometry/contour.py` | **Effective atom radii and atom-to-residue indexing are split across `structure`, `charge`, `density` and `geometry`.** `resolve_protonated_radii` returns unscaled CHARMM radii that `density/stage.py` must manually multiply by `radius_scales(table)`; atom-to-residue indexing is duplicated between `charge/edits.py:_owner` and `density/radii.py:resolve_protonated_radii`; and `RadiusEdit` scaling is assembled separately in `protonated.py`, `charge/edits.py` and `geometry/contour.py`. |
| **REV-219** | interface | low | `src/nanopnp/io/models.py`, `src/nanopnp/io/defaults.py`, `src/nanopnp/api/project.py` | **`ModelFile` discards its validated body, leaving `api/project.py` to re-parse YAML and strip `schema`/`name` by hand.** `_read_model_file` validates and rebases a model file's body and then discards it from `ModelFile`; `api/project.py` re-loads model YAML via `_body(keep=...)` and duplicates `io/models.py:_put` and layer splitting (`_split`). |
| **REV-220** | coupling | low | `src/nanopnp/pipeline/run.py`, `src/nanopnp/pipeline/forecast.py`, `src/nanopnp/sweep/forecast.py` | **Pipeline stage keying is implemented three times (`_walk`, `stored_upstream`, `keyed_walk`).** Each loop independently resolves `StageDescription`, constructs store-aware stages, filters `offered()` upstream artefacts and queries `Store` for `key_is_artefact` vs payload-bearing artefacts, while `stored_upstream` omits custom `stages`. |

---

## Candidate 1: Collapse Case file reading, substitution and input-path rebasing (`REV-217`, `REV-200`)

### 1. Architectural diagnosis

Today, reading a case, substituting assignments into it, and discovering or rebasing the input file paths it names are spread across five modules:

- **Two competing `io` reader pairs**: `io/case.py` defines `read_case(path)` and `read_case_text(text)`, which explicitly refuse `models:` and `variables:` (`io/case.py:2178-2199`), while `io/models.py` defines `read(path)` and `reads(text)`, which resolve `variables:` and `models:` and then call `validate_mapping`. Every production caller (`pipeline/case.py`, `api/case.py`, `sweep/plan.py`) wants a case reader that resolves variables and models; only tests that specifically test the refusal call `read_case` on a study or variable-bearing file.
- **Double `substitute()` and duplicate rebasing in `Case.with_`**: `api/case.py:Case.with_` (`lines 256-288`) splits `assignments` into `models.*` vs other keys, calls `substitute()` once for `models.*` and a second time for the remaining keys, and when `self._source.base` is set and `self.models_record is None`, runs its own `_rebased_paths()` helper to resolve relative input paths against `self._source.base` and mutates the result via `model_copy(update=...)`.
- **Three copies of input-path discovery**:
  1. `io/case_paths.py` has `path_fields()` + `correction_paths(document)` (which takes a `CaseDocument`).
  2. `io/models.py:540-560` has `_correction_leaves()` + `_rebased(body, directory)` (which walks a raw `dict[str, Any]`).
  3. `io/project.py:139-189` has `_correction_leaves()` + `item_inputs(body)` + `rewrite_inputs(body, rewrite)` (which walks a `Mapping[str, Any]` and skips `models.*`).
- **`VariableRecord` misplaced in `io/models.py`**: `VariableRecord` (`io/models.py:191-301`) is a subclass of `io/variables.py:Resolution`, placed in `io/models.py` only because `VariableRecord.carried` calls `read_mapping`.

### 2. Settled decisions

- **D1.1 (`io` Case reader seam)**: Fold `io.models.read` and `reads` into `io/case.py:read_case(path, *, model=CaseDocument)` and `read_case_text(text, *, base=None, source="<string>", model=CaseDocument)` so every `io` reader resolves `variables:` and `models:` directly. Amend `specification/05-software-design/03-1-case-file.md` lines 281–282 and 316–317 to remove the refusal of `models:` and `variables:` on `read_case`.
- **D1.2 (`pipeline/case.py` seam)**: Keep `load_case` and `loads_case` in `pipeline/case.py` as thin registry-checked seams (`read_case` / `read_case_text` + `check_document`).
- **D1.3 (Single-pass `substitute` with `base`)**: Add `base: Path | None = None` to `io/case_paths.py:substitute(document, assignments, *, base=None)` so model swaps, variable resolution, field edits and relative input-path rebasing happen in a single pass. Simplify the two `substitute()` refusal messages when a case has no `models:` or `variables:` to `"write models:/variables: in the case file"`.
- **D1.4 (Unified input-path seam in `io/case_paths.py`)**: Consolidate input-file discovery, rebasing and rewriting in `io/case_paths.py` as `input_paths(source: CaseDocument | Mapping[str, Any]) -> dict[str, str]`, `rewrite_inputs(body: dict[str, Any], rewrite: Callable[[str, str], str | None]) -> bool`, and `rebase_inputs(body: dict[str, Any], base: Path) -> dict[str, Any]`. Delete `correction_paths()`, `io/project.py:item_inputs()`, `io/models.py:_rebased()` and `api/case.py:_rebased_paths()`.
- **D1.5 (`VariableRecord` home and acyclic `io` imports)**: Move `VariableRecord` to `io/variables.py` beside `Resolution` and `Variable`. Keep the top-level `io` module import graph strictly acyclic (`case.py -> case_paths.py -> variables.py -> models.py`) under `VER-61` and `VER-72` by using function-level imports where `case.py` or `case_paths.py` delegates to `models.py`.

### 3. Concrete code changes

#### `src/nanopnp/io/case_paths.py` — unified input-path seam and single-pass `substitute`

```python
# Before (scattered across io/case_paths.py, io/models.py, io/project.py, and api/case.py):
# - io/case_paths.py: correction_paths(document: CaseDocument) -> dict[str, Path]
# - io/models.py: _rebased(body: dict[str, Any], directory: Path) -> dict[str, Any]
# - io/project.py: item_inputs(body: Mapping[str, Any]) -> dict[str, str]
# - api/case.py: _rebased_paths(base: Path, values: Mapping[str, FieldValue]) -> dict[str, FieldValue]

# After (in src/nanopnp/io/case_paths.py):
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

And `substitute` in `src/nanopnp/io/case_paths.py` handles model swaps, variable assignments, leaf edits and optional `base` rebasing in one pass:

```python
# After (in src/nanopnp/io/case_paths.py):
def substitute(
    document: D,
    assignments: Mapping[str, FieldValue],
    *,
    base: Path | None = None,
) -> D:
    """Return a validated copy of ``document`` with ``assignments`` applied at their dotted paths."""
    model_swaps = {p: v for p, v in assignments.items() if p == "models" or p.startswith("models.")}
    rest = {p: v for p, v in assignments.items() if p not in model_swaps}
    current = document
    if model_swaps:
        record = current.models_record
        if record is None:
            bad = next(iter(model_swaps))
            raise CaseValidationError(
                f"{bad}: this case names no model files; write models: in the case file"
            )
        current = record.carried(current, model_swaps)
    if not rest:
        return current
    variables = current.variables_record
    if any(p == "variables" or p.startswith("variables.") for p in rest):
        if variables is None:
            bad = next(p for p in rest if p == "variables" or p.startswith("variables."))
            raise UnknownCasePathError(
                f"{bad!r}: this case defines no variables; write variables: in the case file"
            )
        return variables.carried(current, rest, base=base)
    if variables is not None:
        return variables.carried(current, rest, base=base)
    # Plain document without variables: validate, apply edits, rebase if base is given, re-attach models.
    ...
```

#### `src/nanopnp/api/case.py` — `Case.with_` collapses to a single `substitute` call

```python
# Before (src/nanopnp/api/case.py:256-288):
        if self._source.base is not None and self.models_record is None:
            values = _rebased_paths(self._source.base, values)
        models = {k: v for k, v in values.items() if k == "models" or k.startswith("models.")}
        rest = {k: v for k, v in values.items() if k not in models}
        updated = substitute(self, models) if models else self
        if rest:
            updated = substitute(updated, rest)
        if self._source.base is not None and updated.models_record is None:
            rebased = _rebased_paths(
                self._source.base, {p: value_at(updated, p) for p in rest if p in updated.expressions}
            )
            for path, value in rebased.items():
                ...

# After (src/nanopnp/api/case.py):
        updated = substitute(self, values, base=self._source.base)
```

### 4. Why this improves the architecture & overall impact

- **Maintainability**: Adding a new path-bearing field or a new model kind (such as WP5.09's `models.physics`) no longer requires updating three separate path-discovery functions (`case_paths.py`, `models.py`, `project.py`) and two `substitute` callers.
- **Extensibility**: `input_paths`, `rewrite_inputs` and `rebase_inputs` form a single deep seam in `io/case_paths.py` that works identically on a `CaseDocument` or an unvalidated YAML mapping (`study`, `molecular`, `continuum`, or `physics` model file).
- **Simplicity**: Eliminates `io.models.read` / `reads` in favour of `io.case.read_case` / `read_case_text`, removes `_rebased_paths` and the double-substitution dance from `Case.with_`, and places `VariableRecord` in `io/variables.py` alongside `Resolution`.

---

## Candidate 2: Deepen Sweep planning and member execution in memory (`REV-199`)

### 1. Architectural diagnosis

In the current codebase, planning and executing a sweep across `api/sweep.py`, `sweep/plan.py` and `api/session.py` crosses the disk boundary unnecessarily and loses cached work at the seam:

1. **Staging directory round-trip in `api/sweep.py:plan_sweep`**: When `plan_sweep(case, ...)` is called on an in-memory `Case` (`api/sweep.py:166-210`), it creates a temporary `.staging-*` folder inside `sweeps/`, writes `base.case.yaml` there, calls `build_plan(base_path, ...)` so `build_plan` can read `base.case.yaml` back from disk, moves the staged files to `sweeps/<name>-<hash[:8]>/`, and then calls `dataclasses.replace(staged, base_path=target / BASE_CASE_FILENAME)`.
2. **Silent loss of `resolved_members` (`REV-199` regression)**: `build_plan` attaches the resolved members to the frozen `SweepPlan` via `plan.__dict__["resolved_members"] = tuple(resolved)` (`sweep/plan.py:258`). Because `resolved_members` is a `@cached_property` and not a dataclass field, `dataclasses.replace(staged, base_path=...)` in `plan_sweep` constructs a fresh `SweepPlan` instance **without** `"resolved_members"` in `__dict__`. Calling `plan_sweep(...).forecast()` immediately re-reads `base.case.yaml`, re-substitutes every point and re-resolves every member!
3. **Re-substitution and re-resolution during `run_point` and `_parent_artefact`**: Even when `plan.resolved_members` is populated, `api/sweep.py:run_point` calls `plan.case(index)` (re-substituting from `base_case()`) and passes the `CaseDocument` to `Session._member` -> `Session._walk` -> `run_document`, which calls `resolve(document)` again. Worse, `_parent_artefact` (`api/sweep.py:296-310`) calls `plan.case(point.parent)` and `stored_upstream(parent_case, ...)`, which calls `resolve(parent_case)` yet again for every warm-started point!
4. **Shallow pass-throughs `Session._member` and `Session._walk`**: `Session._member` and `Session._walk` (`api/session.py:224-279`) exist only to forward arguments to `pipeline.run.run_document`.

### 2. Settled decisions

- **D2.1 (In-memory `build_plan`)**: Allow `sweep/plan.py:build_plan` to accept `base: CaseDocument | None = None` alongside `base_path: str | Path` so `api/sweep.py:plan_sweep` plans directly in memory and writes `base.case.yaml` and `sweep.yaml` once to the final `sweeps/<name>-<hash[:8]>/` directory without a `.staging-*` directory.
- **D2.2 (First-class `_resolved_members` field on `SweepPlan`)**: Replace `plan.__dict__["resolved_members"]` with a non-compared dataclass field `_resolved_members: tuple[ResolvedCase, ...] | None = field(default=None, repr=False, compare=False)` on `SweepPlan`, populated on construction and preserved across `dataclasses.replace()`.
- **D2.3 (Reuse `plan.resolved_members` in `run_point` and `_parent_artefact`)**: Keep the disk tamper check in `plan.base_case()`, then index `plan.resolved_members[index]` and `plan.resolved_members[point.parent]` in `run_point` and `_parent_artefact`. Allow `pipeline/run.py:run_document` and `stored_upstream` to accept `CaseDocument | ResolvedCase` (or an optional `resolved: ResolvedCase | None = None`) so neither the point nor its warm-start parent is re-substituted or re-resolved.
- **D2.4 (Delete `Session._member` and `Session._walk`)**: Have `Session.run` and `api/sweep.py:run_point` call `pipeline.run.run_document` directly (passing `store=session.store, stages=session.own_stages`), and delete `Session._member` and `Session._walk`.

### 3. Concrete code changes

#### `src/nanopnp/sweep/plan.py` — preserve `_resolved_members` and support in-memory `base`

```python
# Before (src/nanopnp/sweep/plan.py:59-106, 250-259):
@dataclass(frozen=True)
class SweepPlan:
    schema: str
    base_name: str
    base_sha256: str
    ...
    base_variables: Mapping[str, Any] | None = None

    @cached_property
    def resolved_members(self) -> tuple[ResolvedCase, ...]:
        base = self.base_case()
        return tuple(
            resolve_case(_substituted(base, self.points[index].assignments), base=self._base_dir)
            for index in range(self.size)
        )
...
    plan = SweepPlan(...)
    plan.__dict__["resolved_members"] = tuple(resolved)
    return plan

# After (src/nanopnp/sweep/plan.py):
@dataclass(frozen=True)
class SweepPlan:
    schema: str
    base_name: str
    base_sha256: str
    ...
    base_variables: Mapping[str, Any] | None = None
    _resolved_members: tuple[ResolvedCase, ...] | None = field(
        default=None, repr=False, compare=False
    )

    @property
    def resolved_members(self) -> tuple[ResolvedCase, ...]:
        """Return every member's resolved case, checked against ``base_path`` when on disk."""
        base = self.base_case()
        if self._resolved_members is not None:
            return self._resolved_members
        built = tuple(
            resolve_case(_substituted(base, self.points[index].assignments), base=self._base_dir)
            for index in range(self.size)
        )
        object.__setattr__(self, "_resolved_members", built)
        return built
```

#### `src/nanopnp/api/sweep.py` — direct in-memory planning and zero re-resolution in `run_point`

```python
# Before (src/nanopnp/api/sweep.py:194-210):
    staging = Path(tempfile.mkdtemp(prefix=".staging-", dir=sweeps))
    try:
        staged_base = staging / BASE_CASE_FILENAME
        staged_base.write_text(case.dumps(), encoding="utf-8")
        staged = build_plan(staged_base, axes=axes, where=where, ...)
        target = session.store.sweep_directory(staged.base_name, staged.content_hash)
        ...
        plan = dataclasses.replace(staged, base_path=target / BASE_CASE_FILENAME)
        write_plan(plan, target / PLAN_FILENAME)
        return Sweep(plan, session=session, directory=target)
    finally:
        shutil.rmtree(staging, ignore_errors=True)

# After (src/nanopnp/api/sweep.py):
    planned = build_plan(
        base_path=case.source.path or Path(BASE_CASE_FILENAME),
        base=case,
        base_text=case.dumps(),
        axes=axes,
        where=where,
        ...,
    )
    target = session.store.sweep_directory(planned.base_name, planned.content_hash)
    target.mkdir(parents=True, exist_ok=True)
    base_file = target / BASE_CASE_FILENAME
    if not base_file.exists():
        atomic_write_bytes(base_file, case.dumps().encode("utf-8"))
    plan = dataclasses.replace(planned, base_path=base_file)
    if not (target / PLAN_FILENAME).exists():
        write_plan(plan, target / PLAN_FILENAME)
    return Sweep(plan, session=session, directory=target)
```

And in `run_point` / `_parent_artefact` (`src/nanopnp/api/sweep.py`):

```python
# After (src/nanopnp/api/sweep.py):
def _parent_artefact(
    plan: SweepPlan, point: SweepPoint, session: Session
) -> tuple[Artefact | None, str | None]:
    if point.parent is None:
        return None, None
    parent_resolved = plan.resolved_members[point.parent]
    upstream = stored_upstream(parent_resolved, store=session.store, feeding="solve")
    ...
```

### 4. Why this improves the architecture & overall impact

- **Maintainability**: `_resolved_members` is an explicit dataclass field rather than a hidden `__dict__` mutation on a frozen dataclass, eliminating a subtle state-loss bug across `dataclasses.replace`.
- **Extensibility**: `stored_upstream` and `run_document` accepting `CaseDocument | ResolvedCase` lets any caller that has already resolved a case (such as `SweepPlan`, `keyed_walk` or the GUI runner) pass it straight into the pipeline without repeating `pipeline.case.resolve()`.
- **Simplicity**: Removes temporary `.staging-*` directories from `plan_sweep`, deletes `Session._member` and `Session._walk`, and cuts member resolution during a sweep from $3N$ times (build + forecast + run/warm-start) to $1N$.

---

## Candidate 3: Unify the Stage-5 Region seam and delete `CylindricalPoreGeometry` (`REV-170`, `MOD-03`)

### 1. Architectural diagnosis

As recorded in `REV-170` (`docs/project/review-items.md:2236-2257`), Stage 5's region payload and idealised cylinder geometry suffer from three coupled structural defects:

1. **Five `isinstance(record, IdealisedRegionRecord)` branches outside Qt**: `geometry/region.py:read_region` returns `RegionRecord | IdealisedRegionRecord`, and every consumer has to branch on the concrete type:
   - `mesh/generate.py:239` (`idealised_recipe` vs `resolve_wall_size`)
   - `mesh/generate.py:254` (`mesh_idealised` vs `mesh_region`)
   - `mesh/ingest.py:624-626` (`_sizing` checking `isinstance(record, IdealisedRegionRecord)` and `record.exclusion is not None`)
   - `plot/data.py:209` (`region_drawing` building `RegionDrawing` differently for `IdealisedRegionRecord` vs `RegionRecord`)
   - `cli/building.py:80` (`_mesh` checking `if not isinstance(record, IdealisedRegionRecord):`)
2. **Mesh sizing leaked into `geometry/pore.py`**: `CylinderPore.name_edges` (`geometry/pore.py:83`) sets `edge.maxh = wall_h_nm` on `"wall"` edges, mixing stage-6 Netgen mesh sizing into stage-5 geometry construction.
3. **Duplicate cylinder class and the `MOD-03` (`geometry -> mesh`) upward import edge**:
   - `geometry/pore.py:CylinderPore` (`radius_nm`, `membrane_thickness_nm`, `reservoir_radius_nm`) builds the OCC shape.
   - `mesh/primitives.py:CylindricalPoreGeometry` (`pore_radius_nm = 2.0`, `membrane_thickness_nm = 13.0`, `reservoir_radius_nm = 50.0`) wraps `CylinderPore` just to add `.generate(maxh_nm=..., wall_h_nm=..., check_quality=...)`.
   - `geometry/analyte.py:14` imports `CylindricalPoreGeometry` from `nanopnp.mesh.primitives` under `if TYPE_CHECKING:`, which is the **only** import keeping the upward edge `- {from: geometry, to: mesh, relation: static, finding: MOD-03}` in `docs/project/modularity-layering.yaml`!

### 2. Settled decisions

- **D3.1 (Shared `Stage5Region` interface and `RegionOutlines` in `geometry/region.py`)**: Define `RegionOutlines` (`pore_nm`, `membrane_nm`, `exclusion_nm`, `membrane_half_thickness_nm`, `reservoir_radius_nm`, `z_extent_nm`) and a `Stage5Region` protocol in `geometry/region.py`. Implement `.outlines_nm() -> RegionOutlines`, `.has_exclusion -> bool`, and `.is_idealised -> bool` on both `RegionRecord` and `IdealisedRegionRecord` so `plot/data.py`, `mesh/ingest.py`, and `cli/building.py` never call `isinstance(record, IdealisedRegionRecord)`.
- **D3.2 (Move `edge.maxh = wall_h_nm` from `geometry/pore.py` to `mesh/`)**: `CylinderPore.shape()` and `CylinderPore.name_edges()` in `geometry/pore.py` only name OCC faces and edges (`"axis"`, `"wall"`, `"membrane"`, `"membrane_outer"`, `"cis"`, `"trans"`, `"interface"`). `mesh/idealised.py` sets `edge.maxh = wall_h_nm` on `"wall"` edges before Netgen meshing, preserving identical OCC topology and `VER-62` mesh hashes.
- **D3.3 (Delete `CylindricalPoreGeometry` and drop `MOD-03`)**: Give `CylinderPore` in `geometry/pore.py` default dimensions (`radius_nm: float = 2.0`, `membrane_thickness_nm: float = 13.0`, `reservoir_radius_nm: float = 50.0`), provide `mesh_cylinder_pore(pore: CylinderPore = CylinderPore(), *, maxh_nm: float = DEFAULT_MAXH_NM, wall_h_nm: float = DEFAULT_CYLINDER_WALL_H_NM, check_quality: bool = True) -> GeneratedMesh` in `mesh/primitives.py` (delegating to `mesh/idealised.py`), update `geometry/analyte.py:PoreWithAnalyte`, `post/indicator.py:lumen_band`, and test callers, and remove `- {from: geometry, to: mesh, relation: static, finding: MOD-03}` from `docs/project/modularity-layering.yaml`.
- **D3.4 (Single entry point in `mesh/generate.py`)**: Have `mesh_region(record, sizing)` and `region_recipe(record, sizing)` in `mesh/generate.py` dispatch polymorphically on `record.is_idealised` / `Stage5Region` so `MeshStage.key` and `MeshStage.run` call one function for both region kinds.

### 3. Concrete code changes

#### `src/nanopnp/geometry/region.py` & `src/nanopnp/plot/data.py` — `RegionOutlines` and `Stage5Region`

```python
# In src/nanopnp/geometry/region.py:
@dataclass(frozen=True)
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
    def shape(self, *, wall_h_nm: float | None = None) -> TopoDS_Shape:
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
    def shape(self) -> TopoDS_Shape:
        ...
        self.name_edges(glued)
        return glued

# And in src/nanopnp/mesh/idealised.py:
def _set_wall_maxh(shape: TopoDS_Shape, wall_h_nm: float) -> None:
    for edge in shape.edges:
        if edge.name == "wall":
            edge.maxh = wall_h_nm
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
- **Simplicity**: Deletes `CylindricalPoreGeometry` as a duplicate class, keeps CAD topology in `geometry/` and Netgen sizing in `mesh/`, and leaves `VER-62`'s golden mesh hashes untouched.

---

## Candidate 4: Concentrate effective atom radii and Charge edit scaling in `ProtonationTable` (`REV-218`)

### 1. Architectural diagnosis

`ProtonationTable` (`structure/protonated.py`) is the stage-7 protonation payload read by stage 2 (`density`), stage 4 (`geometry/contour.py` via `RadiusEdit`), and stage 7 (`charge/edits.py`, `charge/kernel.py`). Currently, operations that belong to `ProtonationTable` and its radius edits leak across four subpackages:

1. **Unscaled radii returned by `resolve_protonated_radii`**: `density/radii.py:resolve_protonated_radii(name, table)` resolves CHARMM van der Waals radii for `table` but ignores the table's own radius edits (`table.header["edits"]`), forcing `density/stage.py:162-163` to remember to call `radii = resolve_protonated_radii(...)` and then multiply `radii_nm = radii.radii_nm * radius_scales(table)`. Any caller of `resolve_protonated_radii` that forgets the second step silently gets unedited radii.
2. **Duplicated atom-to-residue indexing**: Both `charge/edits.py:_owner(table)` (`lines 74-96`) and `density/radii.py:resolve_protonated_radii` (`lines 209-229`) build a `(chain, resid, icode) -> residue_index` dictionary from `table.residue_chain`, `table.residue_resid`, `table.residue_icode` and map every atom's `(chain, resid, icode)` to its residue index in `0 .. len(table.residue_name) - 1`.
3. **Scattered `RadiusEdit` conversion**: `structure/protonated.py:radius_scales(table)` parses `table.header["edits"]` into `RadiusEdit = (parent, resid, icode, factor)` tuples; `geometry/contour.py:probe_radius_edits(resolved)` converts `resolved.protonation.edits` (`ResolvedEdit`) into `RadiusEdit` tuples; and `geometry/contour.py:gate_inputs` calls `residue_radius_scales(ensemble.resname, ensemble.resid, ensemble.icode, radius_edits)`.

### 2. Settled decisions

- **D4.1 (Methods on `ProtonationTable` and scaled `resolve_protonated_radii`)**: Add `table.atom_residue_index() -> np.ndarray` and `table.radius_scales() -> np.ndarray` as methods on `ProtonationTable` in `structure/protonated.py`. Have `density/radii.py:resolve_protonated_radii(name, table)` apply `table.radius_scales()` internally so its returned `ResolvedRadii.radii_nm` are already the effective radii (and `density/stage.py` simply uses `radii.radii_nm`). Use `table.atom_residue_index()` in both `charge/edits.py` (replacing `_owner(table)`) and `density/radii.py:resolve_protonated_radii`.
- **D4.2 (Unified `radius_scales_for` and `probe_radius_edits` in `structure/protonated.py`)**: Provide a unified `radius_scales_for(resname, resid, icode, edits)` (and `radius_edits_of(edits)`) in `structure/protonated.py` that accepts either `RadiusEdit` tuples, `ResolvedEdit` objects, or header edit dicts, so `ProtonationTable.radius_scales()`, `density/radii.py`, and `geometry/contour.py` share one edit-to-scale path. Also update `charge/kernel.py:20` to import `ProtonationTable` from `nanopnp.structure.protonated`.

### 3. Concrete code changes

#### `src/nanopnp/structure/protonated.py` — `atom_residue_index()`, `radius_scales()`, and `radius_scales_for()`

```python
# In src/nanopnp/structure/protonated.py:
class ProtonationTable:
    ...

    def atom_residue_index(self) -> np.ndarray:
        """Return each atom's index into ``residue_*`` (0 .. len(residue_name) - 1)."""
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
                index[(str(chain), int(resid), str(icode))]
                for chain, resid, icode in zip(
                    self.chain.tolist(), self.resid.tolist(), self.icode.tolist(), strict=True
                )
            ],
            dtype=np.intp,
        )

    def radius_scales(self) -> np.ndarray:
        """Return the factor of each atom's radius that the table's radius edits set, 1 elsewhere."""
        edits = self.header.get("edits")
        return radius_scales_for(
            self.resname,
            self.resid,
            self.icode,
            edits if isinstance(edits, list) else (),
        )
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

- **D5.1 (`ModelFile.body` and `read_model_file` in `io/models.py`)**: Add `body: Mapping[str, Any]` (the validated model content without metadata keys) to `ModelFile` and expose `read_model_file(kind, path, *, rebase=True, source=None) -> ModelFile` in `io/models.py` (replacing `check_model_file`).
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
- **Extensibility**: Directly supports WP5.09 (`The physics model`), which adds `physics` to `MODEL_KINDS` and `exposes:` to `physics` model files (`docs/plans/wp5.09-the-physics-model.md`). With `split_case_layers` and `_METADATA_KEYS` in `io/`, `Project.import_case` and `Project.changes` automatically generalize across all `MODEL_KINDS`.
- **Simplicity**: Removes duplicate `_put` and `_body(..., keep=False)` from `api/project.py` and makes `ModelFile` carry the validated body it already parsed.

---

## Candidate 6: Merge dry-run rebuild forecasting into the pipeline stage walker (`REV-220`)

### 1. Architectural diagnosis

Walking the selected stages of a `ResolvedCase` to compute their `StageInputs`, construct each `Stage` (passing `store=store` when `description.takes_store` is true), compute `stage.key(inputs)` and check whether the `Store` already holds the artefact is written three times:

1. `pipeline/run.py:_Walk` + `_walk` + `_resolve_stage` (`lines 541-584, 727-763, 1130-1198`)
2. `pipeline/run.py:stored_upstream` (`lines 1099-1127`) — which also forgot to accept `stages: Mapping[str, FunctionStage] | None = None`
3. `pipeline/forecast.py:keyed_walk` (`lines 51-124`) — a 124-line file imported only by `src/nanopnp/sweep/forecast.py:10` (`from nanopnp.pipeline.forecast import Identity, keyed_walk`).

### 2. Settled decisions

- **D6.1 (Unify stage keying in `pipeline/run.py`)**: Extract a shared stage-keying helper on `_Walk` in `pipeline/run.py` (handling stage description, store-aware stage construction, `offered()` `StageInputs`, and store lookup for both `key_is_artefact` and payload-bearing stages) and use it across `_walk()`, `stored_upstream()`, and `keyed_walk()`.
- **D6.2 (Delete `src/nanopnp/pipeline/forecast.py`)**: Move `FORECAST_SCHEMA`, `Identity`, `_NotBuiltPayload`, and `keyed_walk` into `src/nanopnp/pipeline/run.py`, update `src/nanopnp/sweep/forecast.py` to import `Identity` and `keyed_walk` from `nanopnp.pipeline.run`, and delete `src/nanopnp/pipeline/forecast.py`.

### 3. Concrete code changes

#### `src/nanopnp/pipeline/run.py` — shared `_Walk` keying methods used by `_walk`, `stored_upstream`, and `keyed_walk`

```python
# In src/nanopnp/pipeline/run.py:
@dataclass
class _Walk:
    ...

    def stored(self, name: str, key: Artefact) -> tuple[bool, Artefact | None]:
        """Return (is_in_store, stored_artefact_or_key) without running ``name``."""
        if self.describe(name).key_is_artefact:
            return self.store.contains(key), key
        found = self.store.get(key.schema, key.hash)
        return (found is not None), found
```

With `_Walk.describe(name)`, `_Walk.inputs(name)`, `_Walk.construct(name)` and `_Walk.stored(name, key)` shared in `pipeline/run.py`:

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
        stage = walk.construct(name)
        key = stage.key(walk.inputs(name))
        held, stored = walk.stored(name, key)
        if not held and not walk.describe(name).key_is_artefact:
            raise MissingUpstreamError(
                f"stage {name!r} of case {walk.document.name!r} produces {key.schema} "
                f"{key.short_hash}, which is not in the store at {store.root}"
            )
        assert stored is not None
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
        stage = walk.construct(name)
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

- **Maintainability**: Stage construction, `StageInputs` assembly, and store-hit semantics (`key_is_artefact` vs `store.get`) are defined once on `_Walk` in `pipeline/run.py`. Any change to how stages are constructed or keyed automatically applies to live runs, warm-start parent lookups, and dry-run sweep forecasts.
- **Extensibility**: `stored_upstream` gains support for custom `FunctionStage` extensions (`stages=`) and `ResolvedCase` inputs for free.
- **Simplicity**: Deletes `src/nanopnp/pipeline/forecast.py` (124 lines) and removes duplicated stage-walking boilerplate.

---

## Overall codebase impact summary

| Dimension | Architectural effect across all 6 candidates |
|---|---|
| **Layering (`VER-61`, `VER-72`)** | Eliminates the `MOD-03` (`geometry -> mesh`) static upward edge from `docs/project/modularity-layering.yaml`; keeps top-level imports in `io` (`case.py -> case_paths.py -> variables.py -> models.py`) strictly acyclic with zero new `upward` or `deferred_upward` edges. |
| **Modules deleted / consolidated** | Deletes `src/nanopnp/pipeline/forecast.py` and `mesh/primitives.py:CylindricalPoreGeometry`; moves `VariableRecord` into `src/nanopnp/io/variables.py`; folds `io.models.read`/`reads` into `io.case.read_case`/`read_case_text`; deletes `Session._member` and `Session._walk`. |
| **Locality of change (WP5.09+ readiness)** | Concentrating input-path discovery in `io/case_paths.py` and model-file reading / layer splitting in `io/models.py` means WP5.09 (`The physics model`) and future workbench suites (WP5.10–WP5.15) extend a single seam rather than patching parallel walkers in `io/`, `api/`, `mesh/`, and `plot/`. |
| **Performance & correctness** | Fixes the `REV-199` `dataclasses.replace` cache drop on `SweepPlan._resolved_members`, eliminates `.staging-*` disk round-trips in `plan_sweep`, prevents unscaled CHARMM radii in `resolve_protonated_radii`, and preserves all `VER-62` golden hashes. |
