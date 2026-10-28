# Code review: PR 133, WP54, the ship fixes

28 October 2026 · `5562f31..86d5b46` (`claude/laughing-knuth-lvswt0`) · effort: xhigh, with `--fix` · status:
completed

**Scope.** A static review of the two commits since CODE_REVIEW_017's head, `96181c2` and `86d5b46`:
`mesher_identity` and the cylinder mesh key, `debye_wall_nm` and `ionic_strength_of_M`, `SolutionFields`
(`bulk_mol_m3`, `wall_extent_nm`) and the memoised `solution_fields`, `field_triangulation`, `lumen_window_nm`,
the sweep's staging directory, `prepared_pore`, `cis_referenced_bias_V`, and the notebooks' use of them.
CODE_REVIEW_017's findings are not repeated.

## Summary

The commits do what V14 to V17 say, and the numbers they touch agree: the in-memory sweep names the directory
the sweep file's plan names (checked by a probe), `wall_extent_nm` reads (2.0, 3.0) nm on a 2 nm, 6 nm
cylinder and the lumen window (5.0, 7.0) nm, and `prepared_pore` raises no off-axis warning on 2WCD.

What is left is at the edges of the new helpers:

- **Two of the ship's rulings are weaker in code than in prose.** `bulk_mol_m3` is one scalar copied to every
  species, and the lumen window reads *every* `wall` edge, which on a protein mesh includes the protein's outer
  face in the reservoir.
- **`sweep()`** built the whole plan twice, from a staging directory named by process id.
- **Menus and caches.** `field_menu` offered fields a model does not hold; the caches in `post/export.py` and
  `plot/data.py` are module state.
- **Prose after V14.** Notebook 05 still said the Debye wall is `λ_D/5` and meshes again for each salt.

## What was fixed and what was run

Eight findings are fixed in the working tree, uncommitted. Only fast commands were run: `ruff check` and
`ruff format --check` on `src` and `notebooks`; `mypy` on the seven edited modules; `tests/tier1/test_case_handle.py`,
`test_figures.py`, `test_structure_axis.py` (35 passed) and the notebook, public-API, layering, backend-guard and
sweep-plan tests (72 passed, 1 skipped); probes of `mesher_identity`, `structure_file`, `wall_extent_nm`,
`mesh_elements`, `prepared_pore` on 2WCD and `sweep()` against the file plan. No benchmark, sweep, gate or
`--nightly` walk was run, and no test was added.

| Severity | Count |
|---|---:|
| High | 0 |
| Medium | 1 |
| Low | 14 |

## Findings and their outcome

| # | Location | Finding | Outcome |
|---|---|---|---|
| 1 | `post/export.py` `wall_extent_nm` (386); `plot/data.py` `mesh_elements` (258), `lumen_window_nm` | The window is 2.5 wall radii out and two past the wall's ends, where the wall is the largest `r` and `|z|` of every `wall` edge. On a protein region `name_region` names every protein edge facing the electrolyte `wall`, the outer face in the reservoir included, so the "lumen" is sized by the protein's outer radius. REV-147 asked for "the pore's axial extent and its largest lumen radius". 2WCD's mean C-alpha radius at the wider end is 4.3 nm, so the window reaches at least 11 nm out (2.5 × 4.3) where the fixed one was 5 by 10, and the streamline grid (`STREAM_GRID`) is spread over it. Not run on a 2WCD mesh; read from `name_region`. | Not fixed: reading the lumen from the region record, or from the wall edges whose neighbour is the lumen, changes V16 and is the author's ruling. |
| 2 | `post/export.py` `DIRICHLET_BULK` (379), `solution_fields` (423) | `bulk_mol_m3` is `field_scale(...) * 1.0` per species, and `field_scale` returns one concentration scale for every field. It repeats the default `values.get(name, 1.0)` of `CoupledModel.solve` instead of reading what was imposed, so a solve with `concentration_values` set, or a species with its own scale, is drawn against the wrong bulk again. REV-148 and V16 call it the value "the solve imposed ... for that species", and the tier-2 test can only pass when all are 1. | Not fixed: the model should expose its essential data; or say in V16 that the bulk is the case's concentration. |
| 3 | `plot/data.py` `field_menu` | The menu listed `u_z`, `u_r` and `p_Pa` for any model. A Poisson, PB or PNP solution holds none, so the notebooks' tabs raised `KeyError: no field 'u_z'`. `solve_figure` guarded the same fields with its own rule, from the union of both domains, where the menu read `fluid` only. | Fixed: the menu offers what `whole` and `fluid` hold, and `solve_figure` takes its panels from `field_menu(fields, radial=False)`. |
| 4 | `sweep/inmemory.py` `sweep` | The plan was built twice, once in `.staging-<pid>` to read its hash and once in the final directory, so `_resolve_every_point` and the file digests ran twice for every point, and the plan's warnings were logged twice. The directory named by process id is shared by two threads of one process, or by two containers on one store (pid 1), and `rmtree` by one removes the other's files; a killed run leaves it for good, `_sweep_staging` covering only artefact parents. | Fixed: one build in `tempfile.TemporaryDirectory(dir=sweeps, prefix=".staging-")`, then `replace(staged, base_path=...)`; the hash does not depend on `base_path`. A probe gives the file plan's directory and hash, and no staging directory is left. |
| 5 | `notebooks/05-cylinder/notebook.py` (68, 82), `README.md` | After V14 the Debye wall is `min(0.05 nm, λ_D/5)`: 0.05 nm below about 1.5 M, the same mesh for every such salt. The notebook said "λ_D/5 of the salt ... meshes again for each new salt" and labelled the option "λ_D/5 of the salt". | Fixed: prose, label and README say stage 6's target, at most 0.05 nm, meshing again above about 1.5 M. |
| 6 | `mesh/cylinder.py` `mesher_identity` (40) | The list of sources omits `geometry/tolerance.py`, whose `TOL_NM` decides which edges `CylindricalPoreGeometry.name_edges` calls `wall` and `axis`; it includes `ingest.py`, a stage module, for `apply_groups` alone. A hand-kept list drifts: `GMSH_FIELD_RULES` names the recipe instead. | Fixed in part: `tolerance.py` is in the list. The list stays hand-kept. |
| 7 | `sweep/inmemory.py` `_plain` | `.item()` raises `ValueError` for an array of more than one element (`values=np.array([[1, 2], [3, 4]])` for a list-valued field) and leaves a list of numpy scalars alone. | Fixed: `tolist()` turns a numpy scalar and an array alike into plain Python. |
| 8 | `post/export.py` `_RESTORED_FIELDS` (382), `plot/data.py` `_TRIANGULATIONS` (591) | Two module-level caches hold strong references: two solved fields and four triangulations of a whole mesh live as long as the process. Eviction (`del d[next(iter(d))]`) and the list scan are not thread-safe for a shell with worker threads. The triangulation is matched by array identity, where a `cached_property` on the fields would die with them. | Not fixed: a design choice (a cache on `SolutionFields`, or a lock). |
| 9 | `pipeline/handle.py` `Case.cylinder` docstring | "sizes it as NUM-30 does" puts a requirement identifier in a docstring; `.claude/rules/python.md`: "Requirement identifiers live in the names of in-scope tests and commit messages, not in prose." | Fixed: the identifier is out of the new lines. |
| 10 | `core/paths.py` `structure_file` | The error for a missing `x.pdb` read "no structure file 'x.pdb' (or 'x.pdb.pdb')". Reproduced. | Fixed: a name already ending in `.pdb` is tried once, and the message lists what was tried. |
| 11 | `structure/orient.py` `prepared_pore` (184, 207) | The digest covers `orient.py` alone, not `structure/read.py` (`load_universe`, `chain_keys`), `parse_chains` or the MDAnalysis version, which decide the output as much; V17 words it "this module's code". The call used a dict and `# type: ignore[arg-type]`. | Fixed in part: explicit keywords, no ignore. The digest is unchanged: widening it renames every prepared file. |
| 12 | `post/export.py` `wall_extent_nm` (386); `plot/data.py` `mesh_elements` (258) | "Largest `r` and `|z|` of the `wall`" is computed twice, once over the netgen mesh with a Python loop, once over `MeshData`. A change to one (finding 1) leaves the other. | Not fixed: one definition belongs with finding 1's ruling. |
| 13 | `pipeline/handle.py` `_debye_wall_nm` (279) | REV-152 lists "Duplicated Debye length" as fixed. The sum and the cap are shared, but `_debye_wall_nm` still calls `debye_length_nm` with its own permittivity and temperature, as `case_debye_length_nm` does for a document; the test pins the two at three concentrations only. | Not fixed: `mesh.sizing` should hold one function of species, permittivity and temperature. REV-152's "fixed" is too wide. |
| 14 | `notebooks/05-cylinder/notebook.py` (93) | The residue of CODE_REVIEW_017 finding 11: this range bounds notebook 03's pore radius at 2.2 nm because the ring sits 2.6 nm out, and leaves notebook 05's slider, with the same ring (`cis-ring.field.yaml`), at 5.0 nm. | Not fixed: the mesh step alone can use a wider pore, so a bound is the author's call. |
| 15 | `plot/data.py` `cis_referenced_bias_V` (765), `plot/figures.py` (450) | A failed point of unknown sign is now NaN, and Matplotlib draws no marker at a NaN x, but `sweep_figure`'s title still reads "N point(s) not ok, marked x". | Not fixed: the title should count those it draws; a wording change for the author. |

## Checks that held

- **The sweep directory.** `sweep()` gives the file plan's hash and directory for the same base file name; the
  plan's `base_path` is the final directory's; a numpy array of values plans the same directory as a list.
- **`Case.cylinder`'s key.** `mesher_identity` costs about 0.25 ms; the test that remakes the mesh when it
  changes passes.
- **`_path_fields`.** The `Path`-typed fields of the schema are the seven of the old list.
- **`wall_extent_nm` and the units.** The mesh is in nm: (2.0, 3.0) on a 2 nm, 6 nm cylinder.
- **`prepared_pore`.** Written whole or not at all; the second call returns the first file.
- **Lint and types.** `ruff` and `mypy` pass on what was touched.

## Disposition at ship

- **Finding 1 confirmed and fixed** on a 2WCD mesh (scale 4): the lumen window was 14.2 by 23.8 nm, set by the
  protein's outer face (r up to 5.7 nm), against 9.1 by 19.7 nm from the wall's point nearest the axis in each
  1 nm slice (`post.export.lumen_extent_nm`, shared with `plot.data.mesh_elements`, which also closes finding 12).
  `test_lumen_window_follows_the_lumen_not_the_proteins_outer_face` guards it; V16's text is corrected.
- **Fixed in the review's working tree:** findings 3, 4, 5, 7, 9, 10 and, in part, 6 and 11, read as diffs and kept.
- **Fixed here:** finding 14 (notebook 05's radius stops at 2.2 nm), finding 15 (the sweep title says "where the bias
  is known") and finding 8 in part (the restore cache takes a lock).
- **Open, REV-153:** findings 2 and 13, the unfixed parts of 6, 8 and 10, with a recommendation to leave them.
