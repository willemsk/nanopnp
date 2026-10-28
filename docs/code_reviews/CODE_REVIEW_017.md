# Code review: PR 133, WP54, the notebooks and figures revised

28 October 2026 · `45fb8ca..5562f31` (`claude/laughing-knuth-lvswt0`) · effort: xhigh, with `--fix` · status:
completed

**Scope.** This was a static review of the 20 commits of the branch against `main`: `src/nanopnp/`
(`structure/orient.py`, `mesh/cylinder.py`, `pipeline/handle.py`, `pipeline/run.py`, `post/export.py`,
`plot/{data,figures,panels}.py`, `sweep/inmemory.py`, `core/paths.py`, the CLI's `mesh` command), the six
notebooks and their READMEs, example 06's `prepare.py`, the new and changed tests, `specification/` (FR-30, §8.2.20
V1 to V13), `CHANGELOG.md`, `docs/project/` and the layering record. `specification/`, `knowledge/` and the plans
were read only to check a claim made in the code.

## Summary

The package does what its plan says. `orient_pore` reproduces the retired `prepare.py` step for step: the chain
selection, the covariance axis, the sign test, Rodrigues' rotation and the registration shift agree, so the example
goldens are not moved. The cylinder mesher moved out of the CLI without losing its gates. The panels read the
solved fields in physical units, and the cutlines use the same four-triangle split of each P2 cell as the tests
assume. `ruff check`, `ruff format --check` and `mypy src/` pass on the branch.

The defects found are at the Python API's edges, not in the physics:

- **`sweep()`** raised a bare `RepresenterError` for the most common Python input, a numpy array of values.
- **`plot_iv`** drew a non-bias sweep as a bias sweep.
- **The case-path contract.** `Case.load` now rebases relative paths, while the guide still says they resolve
  against the working directory, and `with_` does not rebase.
- **The caches** of `Case.cylinder` and of the notebooks' prepared structure are keyed by their parameters alone.
- **Duplicated knowledge.** A hand-kept list of the schema's path fields, a second Debye length, a second sweep
  directory name and three copies of the notebooks' preparation.

## What was fixed and what was run

Six findings are fixed in the working tree and three more in part, uncommitted; the rest are left for `/np-ship`
or the author. Only fast commands were run:

- `ruff check` and `ruff format --check` on `src`, `tests`, `notebooks`, `examples` and `docs`;
- `mypy src/` before the fixes, and `mypy` on the six edited modules after them;
- `tests/tier1/test_case_handle.py`, `test_figures.py`, `test_run.py::test_run_result_current_and_conductance_in_nano_units`
  and `test_sweep_plan.py::test_in_memory_sweep_matches_the_sweep_file_plan` (19 passed);
- small probes of `sweep()` with list, array and array-element values, of `plot_iv` on a concentration sweep, of
  `Case.cylinder` with numpy arguments and of `structure_file`, before and after the fixes;
- the schema's `Path`-typed fields against `_PATH_FIELDS` (equal);
- the import weight of `nanopnp.pipeline.run` and `nanopnp.pipeline.handle` (no `numpy`, `ngsolve`, `netgen`,
  `matplotlib` or `MDAnalysis`).

No benchmark, sweep, gate, documentation build or `--nightly` walk was run, and no test was added.

| Severity | Count |
|---|---:|
| High | 0 |
| Medium | 3 |
| Low | 12 |

## Findings and their outcome

| # | Location | Finding | Outcome |
|---|---|---|---|
| 1 | `src/nanopnp/sweep/inmemory.py`, `sweep` | `values` went into `yaml.safe_dump` and `content_hash` as given. An element of `np.linspace(...)` is `numpy.float64`, which YAML cannot represent. Reproduced: `sweep(case, axis="bias_V", values=np.array([-0.05, 0.05]))` raised `RepresenterError: cannot represent an object` from deep in the call. A list of floats worked. | Fixed: each value passes through `_plain`, which takes a numpy scalar's `.item()`. An array, a list of array elements and a list of floats now plan the same directory. |
| 2 | `src/nanopnp/plot/panels.py`, `plot_iv` (line 379) | `plot_iv` is public and exported, but checked only that a current is reported. For a sweep over another axis it plotted the current against the recorded bias, constant across points, and put each failed point at its assigned value times 1000, labelled mV. Reproduced on a concentration sweep: the failed point at 0.2 M sat at x = 200 mV. | Fixed: a sweep whose axis is not `bias_V` is refused, naming the axis. `sweep_figure` already calls it only for the bias axis. |
| 3 | `src/nanopnp/pipeline/handle.py`, `Case.load` (line 95), `Case.with_`; `docs/guide/case-files.md` | `Case.load` now makes relative input paths absolute beside the case file (CHANGELOG, deliberate). The guide's section "Paths in a case resolve against the working directory" and `running.md` still say they never do. A path set afterwards with `with_` or a `run` edit is not rebased, so one case has two rules for one kind of field. `Path.resolve()` also follows a symlinked case file, so its inputs resolve beside the link's target. | Fixed in part: the guide now states the exception and the `with_` rule. Not changed: whether `with_` should rebase against `source`, which is a behaviour the author rules. |
| 4 | `src/nanopnp/pipeline/handle.py`, `Case.cylinder` (line 154) | The cached mesh is named by its geometry numbers alone. Nothing in the key says which mesher, netgen version or gate produced it, so a fixed mesher or a tightened gate leaves the old file in `meshes/` in use, silently. Stage 6 keys its recipe for this reason. The `{"default": "interface"}` group map written into the case is also a copy of what `write_gated_msh` decides, and `mesh_cylinder` returns only the path. | Not fixed: the key needs a mesher identity that is cheap to read (`netgen` must not be imported here). Raise as a REV row, or bump `CYLINDER_MESH_SCHEMA` when the mesher changes. |
| 5 | `src/nanopnp/pipeline/handle.py`, `_PATH_FIELDS` | A hand-kept list of the schema's file-naming fields drives `Case.load`'s rebasing and `sweep()`'s relative-path refusal. A path field added to the schema would be skipped by both, and the case would read against the wrong directory. | Fixed: `_path_fields()` reads them off `case_fields()` by their `Path` annotation, cached. Its result equals the old list today. |
| 6 | `src/nanopnp/plot/figures.py`, `solve_figure`; `src/nanopnp/pipeline/run.py`, `RunResult.fields`; `plot/data.py`, `sampled` | §8.2.20 V4 asks for cutlines "with no second restore". `run.figure("solve")` restores and samples the state again although `run.fields` holds it (notebook 06 calls both, and `_repr_mimebundle_` draws the solve figure too). `sampled` also builds a `Triangulation` and trifinder of the whole fluid mesh on each call: twice per frame of `_streamlines`, and twice per slider move in notebooks 03, 05 and 06. | Not fixed: sharing the fields means a cache keyed by the artefact hash or a change to `draw`'s signature. `solve_figure` lost its production `assert` (finding 12). |
| 7 | `src/nanopnp/pipeline/handle.py`, `_debye_wall_nm` (line 278) | It re-derives the ionic strength and Debye length that `mesh.sizing.ionic_strength_M` and `case_debye_length_nm` hold, from the parameter file instead of a case. The two share the 1:1 assumption of REV-148, so a change to one will not reach the other. The test pins them equal only at 0.1 and 1 M. | Not fixed: the mesh is needed before the document exists. Move the sum and the length into one function of the species and the permittivity. |
| 8 | `src/nanopnp/sweep/inmemory.py`, `sweep` | The directory was built as `store.root / "sweeps" / f"{name}-{short(digest, 12)}"`, which is `Store.sweep_directory`. It is keyed on its own digest, not `plan.hash`, so `nanopnp sweep plan` on the `sweep.yaml` it wrote names another directory. | Fixed in part: it calls `Store.sweep_directory` (the same path). The digest still differs from `plan.hash`. |
| 9 | `src/nanopnp/structure/orient.py`, `orient_pore` (line 154) | The lateral shift uses the centroid of the registration residues, not the pore axis. For a ring all chains of which hold the residues, the two coincide, which is why the retired script and the tests were right. Where a chain lacks some of the residues, the whole structure moves sideways by the offset and the axis is off z, so `symmetry.axis: z` can refuse it. | Not fixed: the prepared 2WCD file would change bytes, and with it the goldens of examples 06 and 07. Rule it, or document that the subset must be symmetric. |
| 10 | `notebooks/01-geometry`, `02-charge`, `06-2wcd` | The preparation (a `sha256` key of the form values, the `orient_pore` call, the `Case.from_structure` call) is copied three times, and the field-view and cutline cells three times more in 03, 05 and 06. The stages are shared only while the copies stay byte-identical. The key leaves out the source entry and `orient_pore`'s own version, and `orient_pore` writes `out` in place, so a call that dies mid-write leaves a file that `prepared.is_file()` then accepts. | Not fixed: a library helper that prepares into the store atomically is a design choice. |
| 11 | `notebooks/03-solve`, `05-cylinder` | The ring field has its centre at r = 2.6 nm and z = 1.5 nm and is built for the 2 nm, 6 nm pore. The pore radius slider runs to 5 nm and the membrane thickness to 2 nm, so for a radius over about 3 nm the ring lies in the lumen and for a thin membrane in the reservoir. The run still converges and the notebook still says "the ring's charge sits in the membrane". | Not fixed: bound the sliders, or place the ring from the geometry. |
| 12 | `src/nanopnp/plot/figures.py`, `solve_figure` | `assert fields is not None` inside the panel loop narrowed a type with a statement that `-O` removes, once per panel. | Fixed: the loop sits under `if fields is not None`. |
| 13 | `src/nanopnp/core/paths.py`, `structure_file` | A name with any suffix was taken as a full file name, else `.pdb` was added. A stem with a dot (`model.v2`) could never be found. | Fixed: the name is tried as given, then with `.pdb`. |
| 14 | `src/nanopnp/pipeline/run.py`, `RunResult.fields` | One message served two causes: a run that did not reach the solve, and a run with no resolved case (as one read back from disk). The second read "which this run did not reach". | Fixed: two messages. |
| 15 | `docs/design/workbench.md`; `docs/plans/wp54-notebooks-and-figures-revised.md` item 3 | The design lists `solution_fields` among `plot/data.py`'s functions and the plan names `handle.py:_path_of`. Both moved in this branch. | Fixed in `workbench.md`. The plan's line is a record and stays. |

## Checks that held

- **`orient_pore` against `prepare.py`.** The axis test, the sign test (`top > bottom` for `wider`), the rotation
  (`R` takes the axis onto +z and a vector on -z turns by pi about x) and the order `(p - c) R^T + target` are the
  retired script's, with the chains now read as `chainID`, or `segid` where blank.
- **`subdivided` and `P2Nodes`.** Columns 3 to 5 are the midsides of edges (0, 1), (1, 2), (2, 0), as `_MIDSIDES`
  builds them, so the four sub-triangles are consistent.
- **Imports.** `nanopnp.pipeline.run` and `nanopnp.pipeline.handle` load neither the heavy packages nor Matplotlib.
- **The sweep pairing.** `cis_referenced_bias_V` and `collect._rectification` agree on the sign under `ground: trans`,
  and `plot_iv`'s annotation reads the forward point's group through `curves.index`.
- **Ruling V9.** `_debye_wall_nm` is stage 6's `lambda_D / 5` at `eps_r,f0`, with `DEBYE_FRACTION` shared.
- **Lint and types.** `ruff` and `mypy src/` pass.
