# Code review: PR 137, WP56, the command line read by a person

30 October 2026 · `597818c..686ff0b` (`ccr-97ce3942-omk2ue`) · effort: xhigh, with `--fix` · status: completed

**Scope.** A static review of the WP56 branch: `nanopnp plot`, the `inspect` readings and comparison
(`cli/reading.py`), `--progress`, `read_run`, `open_run`, `read_dataset`, `Manifest.from_document`, the
wall-distance remedy, the field document's charge stated twice, the field-document reference, the help text, and the
specification, plan, changelog and example changes that go with them.

## Summary

The reading, the plot command and the charge-sign check do what W2 to W5 ask on the paths the examples walk.
Fifteen findings. The weaknesses are at the edges of the new readers: records they were not written for, a run
directory edited by hand, and an extra that is missing.

- **`inspect` refused what IF-02 says it lists.** IF-02 says a record of another schema is listed key by key, and
  that `--json` is the record unchanged by the reading. A manifest of an older build now exited 3. `--json` failed
  wherever the text reading failed: a missing or edited `case.yaml`, a `dataset.json` without its plan, a case that
  no longer validates.
- **`read_run` trusted `case.yaml`.** The manifest's hash covers the case hash but not the case text, and nothing
  compared `case.yaml` with either. An edited `case.yaml` changed what `inspect A B` reported as the case diff and
  what `plot RUN` drew with. `reproduce` already refuses this case.
- **`plot CASE STAGE` ran the walk before it checked for the `plot` extra.** Without matplotlib, the solve ran in
  full and then exited 3.
- **Records**: Appendix A named the FR-44 refusal test that the last commit deleted. The generated CLI reference left
  out the `plot`, `reproduce` and `sweep run` descriptions that W6 asks it to carry. Example 01 still described the
  old `inspect` output.

## What was fixed and what was run

Eleven are fixed.

- `_inspect` checks each record's `schema` against this build's. A record of another schema is listed key by key,
  and `--json` without `--section` prints the record before any reading is built.
- `read_run` compares `case.yaml` with the manifest's case text and refuses a difference with `ManifestHashError`
  (exit 3). It parses the text it has already read.
- `_plot` refuses a missing matplotlib (`MissingExtraError`, exit 3) before it reads or walks anything. It takes a
  `run.json` or `manifest.json` path as its run directory, as `inspect` already does.
- `Manifest.from_document` recomputes the hash inside its guard, so a group of the wrong shape exits 3, not 1.
  `_json_file` refuses a file that is not JSON in the same way.
- `_type_name` no longer calls `tuple[X, ...]` or a mixed 2-tuple a "pair".
- `render_cli_reference` prints a command's description when it differs from its help line.
- `stage_line` takes a `StageRecord`.
- Appendix A's FR-44 row and example 01's README are corrected.

The following were run and pass: ruff, `ruff format --check` and `mypy src/`; the Tier 1 manifest, CLI,
source-convention and charge-field tests (78 passed); example 01's Tier 2 file (10 passed, 24.9 s), which
exercises `open_run` and `plot`. A copy of example 01's run was checked by hand. A manifest marked
`nanopnp/manifest/v0.4` is listed key by key. An edited `case.yaml` is refused in text, and `--json` still prints the
manifest. `plot run/run.json mesh` writes the PNG.

## Not fixed

These four are recorded as REV-157.

1. **The last rung's time on stderr includes the solve's work after the ladder.** `_Progress` closes a rung only
   when the next rung or stage starts. The time printed for the top rung therefore includes the Péclet measurement
   and the write of the state to the store, and it disagrees with the manifest's rung `seconds`. A fix needs an
   end-of-rung call on `SolveHook`, which the GUI's hook would also take.
2. **Two readers of a run directory remain.** `validation/runs.py` (`_record`, and the store fallback in
   `reopen`) duplicates `pipeline.run._json_file` and `open_run`, so the commit's "one reader" holds only for the
   CLI. Moving `reopen` onto `read_run` is a change to `validation/` that WP56 did not plan.
3. **`inspect` of a run reads the manifest twice.** It is read once raw and once through `read_run`, and
   `Manifest.hash` is recomputed on every `document()` call. The cost is small, kilobytes.
4. **`wall_distance_remedy` keeps a `None` branch that cannot be reached.** `generates_mesh` is
   `resolved.mesh is None`, so the else branch always has a supplied mesh; reading `resolved.mesh.path` would drop
   the fallback.
