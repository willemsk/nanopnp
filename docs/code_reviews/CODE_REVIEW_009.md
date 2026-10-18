# Code review: WP49, the cost study

18 October 2026. `/code-review xhigh --fix` of PR #107 (`feat: WP49, the cost study (VER-76;
REV-112, REV-113)`), run inline: ten finder angles, deduplication without verification, one gap
sweep. Fixes were applied to the working tree and not committed. The shipping session adjudicates
them.

## Revision

- Base: `812ed12842eb09c4ddd2668f1c44bdb796711354` (`origin/main`, the merge base).
- Head: `73558d8deecae052f16a3104162c494ce0e238b4` (`claude/wp-implement-49-oejjuz`).
- Scope: the three-dot diff, 18 files. The code under review is `validation/costs.py`,
  `io/case_paths.py` (VER-76), `docs/scripts/generate.py`, `core/errors.py`, `cli/reference.py` and
  their tests.
- Outcome: 15 findings, all fixed in the working tree. The committed record still has to be
  re-measured with the fixed harness (*What the fixes leave*).

## Findings

The harness's own measurements were checked against the walk it instruments. Three patches never
reach the call sites a walk uses, so A8 and A16 were under-counted, which contradicts "the timers
count generously" (WP49 plan). Each such finding below was reproduced in this container before it
was fixed.

### R1. The peak-memory test fails on Windows (high, fixed)

`test_peak_memory_is_a_positive_number_of_megabytes` calls `_peak_rss_mb()`, which raises
`CostStudyError` where `resource` is absent. On push to main and nightly, CI runs Tier 1 on
`windows-latest` (`ci.yml`, `platforms`), so main would go red there again. This is the failure
class item 9 of the plan fixed. The test now asserts the refusal where `resource` is absent.

### R2. A8 never timed `ladder` (high, fixed)

`solve/stage.py` imports `ladder` with `from nanopnp.solve.state import ladder`. Resolving
`SOLVE_RUN` imports that module before the A8 patch is installed. `SolveStage.run` therefore
calls the unpatched function, and the ladder's models and CFs (D3) were never counted. The
patch was confirmed absent from `nanopnp.solve.stage.ladder` during an instrumented block.

### R3. A16 never timed the mesh payload (high, fixed)

`mesh/ingest.py` imports `read` and `write_msh41` by name. The mesh stage's write and every stage's
read-back of `mesh.msh` called the originals. The same holds for `read_grid` and `write_grid` in
`charge/stage.py`.

### R4. A16 timed only the opening of each `.npz` (medium, fixed)

`np.load` returns a lazy `NpzFile`. Every reader reads its arrays inside its own `with` block,
after the patched `numpy.load` has returned, for example `solve/state.py`'s
`{name: archive[name] ...}`. The decompression went untimed, and the record shows reads at 0.01 %
of the 2WCD walk. D4 names "each payload type's write and read", but the module did not list them.
`A16_IO` is now `A16_WRITES` plus `A16_READS`. These add each payload type's `write`/`read`
(`AlignedEnsemble`, `DensityMap`, `ReducedMap`, `Deposit`, `ProtonationTable`), `read_grid` and
`write_grid`, `write_profile` and `load_profile`, `write_region` and `read_region`, and the
solution's `save` and `restore`.

### R5. `BilinearForm.__iadd__` was patched on the wrapper (medium, fixed)

`instrument` resolved and patched names one at a time, so `ngsolve.BilinearForm` was already a
wrapper function when `ngsolve.BilinearForm.__iadd__` was resolved. `functools.wraps` had copied
the class `__dict__` into the wrapper, so the name resolved, and the test's `getattr(...) is found`
passed. But the patch landed on the wrapper, and `+=` on a real form was never timed. Every name is
now resolved before any is replaced.

### R6. The two walks shared one process (medium, fixed)

D4 requires "a cold walk (empty store, fresh process) of each case". `measure_walks` ran the
2WCD walk in the process the quick-start had warmed. Each walk now runs in a child (`_walk`), as
A1 already did.

### R7. The record could not say what produced it (medium, fixed)

`main` overwrote `environment` on every leg and kept the other legs' older blocks. It merged walk
entries, so an older `a16.share` could sit beside a newer `wall_s`. `environment_record` also
recorded no dirty state. The committed record names `4deb53e`, which predates the A8/A16 code, and
the version string `.d20261018` shows a dirty tree. The environment is now kept per leg. Each leg
block carries its own denominator (`stage10_s`, `wall_s`), the record carries a `dirty` flag, and
`all` starts from an empty record. CLAUDE.md, *Provenance*: "one that cannot reconstruct the run is
not a result".

### R8. `instrument` restored the wrong object (medium, fixed)

The restore wrote back `getattr(owner, name)`, not the class-dictionary entry. A wrapped
`staticmethod` received `self`. A `classmethod` came back as a bound method. An inherited method
left a shadowing attribute in the subclass. R4's readers are classmethods, so this had to be fixed
with it. Descriptors are now kept, and an inherited attribute is deleted on exit.

### R9. A timing test raced the scheduler (low, fixed)

`test_a_nested_call_of_one_category_counts_once` slept twice for 50 ms and allowed 40 ms of
overshoot. Only 10 ms separated a pass from the double-count it guards against, on loaded macOS
runners under `-n auto`. `CategoryTimer` now takes a clock, and both nesting tests use a fake one.

### R10. The stub test stopped checking the Linux wheel (low, fixed)

Making the check conditional for macOS and Windows also dropped it on Linux. The knowledge
concept marks as `[tested: ...]` the claim that the Linux wheel ships `__init__.pyi`. Linux now
asserts the file again.

### R11. `ε_protein` was hard-coded in Python (convention, fixed)

`A1_CASE` wrote `solid_permittivities: {protein: 20.0, membrane: 3.2}` through `.format()`.
CLAUDE.md, *Do NOT*: "Hard-code correction coefficients, `ε_protein` or any fitted parameter in
Python". `.claude/rules/python.md`: "f-strings, never `%`/`.format()`". The template also put
unescaped paths into YAML. The A1 case is now the shipped 2WCD example with `charge` dropped and an
ensemble added through `substitute`, then written by `dump_case`. For stages 1 and 2 it is the
same case.

### R12. The example cases were rewritten as text (low, fixed)

`_quickstart_case` and `_charged_case` rewrote the example YAML with `str.replace("path: ...")`.
If an example's spelling changed, that would silently no-op, and the walk would read a relative
`pore.msh` from whatever directory it ran in. Both now use `substitute` and `dump_case`.

### R13. The mesher was not found on Windows (low, fixed)

`Path(sys.executable).with_name("nanopnp")` misses `nanopnp.exe`. The harness now uses
`shutil.which` beside the interpreter and refuses by name when none is found.

### R14. Coverage exemptions gave false reasons (convention, fixed)

`_fresh`, `_split_io` and `main` were exempt as "runs minutes-long walks on the protein case".
None of them runs a walk, and `main` held R7's merge logic untested. CLAUDE.md: "write the tests
with the item". `main`, `walk_entry` (extracted from `measure_walks`), `_a1_case`, `_nanopnp` and
`_run_child` are now covered. Each remaining exemption states what it runs, and `_fresh` is gone.

### R15. `_split_io` repeated the write list (cleanup, fixed)

`_split_io` restated the write names in a second tuple and stacked two `instrument` calls on one
group. A write added to `A16_IO` alone would have been timed as a read. It is now one call over
`A16_WRITES` and `A16_READS`.

## Not reported, below the cap

- `docs/scripts/generate.py` writes `case.schema.json` outside the `rendered` mapping, counts it
  with `+ 1` as a page, and relies on the loop having created `reference/`.
- `environment_record` re-implements `nanopnp.io.manifest.environment()`. Reusing it would change
  the record's shape, so that is left to the author.
- `test_ver76_an_extra_case_field_fails` compares a hand-built tuple with `schema_leaves`. It never
  substitutes `case_fields` into the equality the first test asserts.

## What the fixes leave

The fixed harness was run once into a scratch file, on the dirty tree, while other jobs were
loading the container (walls 1.3 to 1.8 times the committed ones). Each walk ran in its own child
through the new case builders, and nothing is over its threshold:

- A8: 0.03 % on 2WCD and 0.54 % on the quick-start (was 0.33 %).
- A16: 0.69 % on 2WCD, with reads at 0.18 % (were 0.01 %). On the quick-start, 0.64 %, with reads
  at 0.55 %.

The A1 leg's 16- and 32-frame children completed through `_a1_case`; the run was stopped during
the 64-frame child. These figures show that the harness works. They are not the record.

The harness now measures what D3 and D4 define, so `docs/project/cost-study.json` and the numbers
quoted from it no longer come from the committed script. Those are the plan's Outcome, the phase
plan's *Delivered* line, `CHANGELOG.md` and REV-112 in `review-items.md`. The record is also in the
old shape. After the fixes are committed, run `uv run python -m nanopnp.validation.costs all` on a
clean tree, then commit the record and the re-quoted numbers.
