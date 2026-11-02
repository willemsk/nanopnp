# Code review 025: WP59, the architecture review's fixes

Reviewed: PR 148, base `dca78f153e73e049527c0d8e914d9c35c8b068ac`, head `e00436f0482485bf4fce9d2ac731bf6412cc988e`.
Level: xhigh, with `--fix`. Status: completed. Static review: no benchmark, sweep, cost study, `gate.sh` or
`pytest --nightly` was run. After the fixes: `ruff check`, `ruff format --check` and `mypy` pass on the two edited
modules, and `tests/tier1/test_newton.py`, `test_nan_gates.py` and `test_mesh_generate.py` pass (40 tests).

The diff touches `api/case.py`, `api/session.py`, `cli/__init__.py`, `io/manifest.py`, `mesh/generate.py`,
`numerics/newton.py`, `pipeline/run.py`, one Tier 1 test, six case files and the prose. These were checked against
their callers: `Case.load`, `Case.source`, `Case.__hash__`, `Session.check`, `Session.read`, the four command-line
routes, the moved run constants, the non-finite Newton branch and the wall guard. No QoI moves. `cli/__init__.py`
imports nothing from `pipeline`.

## Findings

1. **The empty-wall guard cannot fire** (correctness). `MeshData._validate` refuses a boundary name that no edge
   uses, so `edges_of("wall")` never returns an empty array. A mesh without wall segments has no `wall` group, and
   `edges_of` raises a bare `KeyError` before the guard runs. That error is not the gate's error, and it does not
   take the gate's exit code. **Fixed:** `wall_statistics` now tests that the group is present before reading it, and
   raises `WallSizeGateError` naming the groups the mesh does carry. The CHANGELOG line now says the same.
2. **`raise_on_failure` misdescribes the new raise** (correctness of the contract). The parameter said "Raise
   NewtonDivergenceError at the iteration cap", and the Raises section listed only `ValueError`. Since D5, a
   non-finite trial residual at minimum damping raises whatever the flag says. A caller passing
   `raise_on_failure=False` to read `result.converged` would get an exception the docstring rules out. **Fixed:** the
   parameter and the Raises section now name both raises and the restored state.
3. **`plot` of a run reads the run directory twice** (efficiency, altitude). `Session(write=False).read(target)`
   reads and checks `run.json`, `manifest.json` and `case.yaml` once. `Session(holding).open(target)` then does all of
   it again through `open_run`. The CLI also copies `open_run`'s rule for choosing the store. The root cause is that
   `Session.open` always passes `self.store`, so it can never use the store the record names. **Skipped:** fixing it
   means a store override on `Session.open` (or a session that remembers no store was given), which changes the
   public API that D3 and IF-01's NOTE fix.
4. **Example 05's case header still states the old path rule** (documentation, REV-169). The header of
   `examples/05-clya-reference/clya-0.5M-plus50mV.case.yaml` said the mesh path "resolves against the working
   directory", which is the claim REV-169 corrected in the other six files. **Fixed:** the header now says a relative
   path is read beside the case file. Only the comment changed, so the case identity is unchanged.
5. **"`cli` imports nothing from `pipeline`" is not true** (documentation). `cli/reference.py` imports
   `nanopnp.pipeline.checks` at module level, and the plan's D4 keeps that edge. **Fixed:** the CHANGELOG and the
   Phase 4 plan's WP59 entry now say `cli/__init__.py`.
6. **`Case.__eq__` and `__hash__` disagree across types** (correctness, pre-existing). `Case == CaseDocument`
   compares the two dumps and can be true. A plain `CaseDocument` keeps pydantic's frozen hash, which either differs
   or raises on its `dict` fields. "Equal cases hash equal" therefore holds only between two `Case` objects.
   **Skipped:** this was not introduced here. The cross-type equality is documented behaviour.
7. **`Session.check` dumps an edited case only to read its base** (efficiency). `case.source.base` builds the whole
   `CaseSource`, and for an edited or in-memory case that runs `dumps()`, a YAML dump. `validate case-hash` also
   computes the stage selection and then discards it. **Skipped:** the cheap fix reads `case._base`, which is the
   private-field read D1 removed. The cost is about a millisecond.
8. **A missing case file is now named by its absolute path** (output). `Case.load` reads `given.resolve()`, so
   `nanopnp validate case missing.yaml` reports the resolved path. `load_case` named the path as typed, and the
   CHANGELOG says "Their output is unchanged". **Skipped:** this is cosmetic and only on an error path.
9. **The damping cut was written out three times** (simplification). D5 added a third copy of
   `max(settings.minimum_damping, damping * settings.recovery_damping)`. **Fixed:** all three now call one local `cut`.
   The behaviour is the same.
10. **The renamed test kept the old verification date** (provenance). In
    `knowledge/06-numerics-fem/14-tier-1-test-evidence-newtons.md`, the `verified` entry now names the new test, but
    its `at` still read 14 October 2026. The test did not exist until 1 November. **Fixed:** `at` is now
    `2026-11-01`.
11. **`Session.read` uses nothing from the session** (simplification). `_inspect` and `_plot` each build a throwaway
    `Session(write=False)`, which works out a default store root from the working directory, just to call a method
    that uses neither the store nor the session's own stages. **Skipped:** D3 fixes the method's shape as an instance
    method.

## Decided in `/np-ship`

All six applied fixes were read as diffs and kept; the empty-wall guard was confirmed against `MeshData._validate`
(`mesh/adapter.py`), which refuses a boundary name no edge uses. Finding 8 is fixed here: `Case.load` reads the path as
given, so a missing file is named as typed. Findings 3, 7 and 11 are REV-173, open for the author. Finding 6 predates
the package and is documented behaviour. The physics review of the numerics diff found no defect; its doubts on the
order of the divergence and the state gates, and on a non-finite Newton direction, are REV-172, open for the author.
