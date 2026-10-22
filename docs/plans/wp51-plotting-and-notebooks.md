# WP51 — The plotting library and the notebooks

**Status: planned, not started.** Written 22 October 2026. Inherits WP50 as shipped (§8.2.13) and
the Phase 4 amendment of 22 October 2026 (§8.2.14 P1 to P7).

The [Phase 4 plan](phase-4-polish-and-user-testing.md) owns the phase. `SPECIFICATION.md` governs;
where this plan and it disagree, this plan is wrong. Identifiers are pointers, never restatements.

## In brief

**What changes.** In a notebook, every step's result shows itself as a picture: the atoms, the
density, the pore's outline, the mesh, the charges, the corrections, the solved fields with the
solver's convergence, the numbers, and a sweep's curves. Without the plotting add-on, a result
shows a short text summary. Four notebooks run every night, so they cannot go stale before the
sessions.

**Cost.** About a week. Each push gains seconds; the pictures reuse the checks' runs.

**What could go wrong.** A picture could mislabel a unit or swap the radial and axial directions;
tests check the conversions, and the author looks before the merge. A plotting import could slow
every start-up; a test fails if one reaches the default path.

**Your call.**
- Should anything be added to the program's top-level public names? *Recommendation:* no; results
  display themselves, and a name added now is one more to keep.

## Execution brief

Scope: the Phase 4 plan's WP51; FR-30; §8.2.14 P2 to P6; REV-123. Depends on WP50.
Tag `v0.5.0-alpha.17`. Models: Sonnet; Haiku for items 1 and 7. Item 3 touches `solve/` and
`post/` without changing a number; `physics-reviewer` reads it.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 Layout and names | `plot/__init__.py` exports `figure(artefact, *, inputs=None)` → `matplotlib.figure.Figure`. `plot/data.py` turns an artefact into arrays in SI and the model frame and never imports Matplotlib. `plot/figures.py` has one `<stage>_figure(artefact, inputs)` each, building a `Figure` without `pyplot`, so no re-run leaks a global figure. Display units (nm, M, V) come from one table and are named on every axis. `RunResult` gains `resolved: ResolvedCase \| None = None`, set by the walk, and `figure(stage)`. **No name joins `PUBLIC`** | P3; F4 |
| D2 Registry and display | `core.stages.register` takes `figure: str \| None = None`, a `module:function` validated as `target` is. `register_figure(schema, target)` serves the sweep dataset, which no stage emits. `FIGURE_FREE = frozenset({"case", "report"})`. `figure_target(schema)` maps a schema to its target. `draw(artefact, inputs)` imports the target and calls it; a missing `matplotlib` raises `MissingExtraError` naming `plot`. The base `Artefact` dispatches on its schema, since `Store.get` returns the base class. `Artefact` and `RunResult` implement `_repr_mimebundle_`: `text/plain` always, and `text/html` (the summary with the figure as an embedded PNG). Only `MissingExtraError` falls back to text; any other error propagates | P6. Both marimo and Jupyter read `_repr_mimebundle_` (marimo, *Displaying objects*, via Context7). The targets are string edges, as the stage targets are (VER-61) |
| D3 What a figure reads | `inputs` is the walk's `StageInputs`, built by `RunResult.figure` through `offered`. A bare artefact draws what its payload and summary carry; where that is nothing (materials), it shows its text naming `result.figure(stage)`. Fields come through two functions factored within `post/`, the IF-07 export unchanged: `restored(inputs, solution)`, from the report stage, and `sampled_fields(solution, scales)`, from `export_fields`. The solve stage writes `newton_history.json` from the events its `SolveHook` reports; a payload is outside the digest, so the hash, the manifest and VER-62 hold, and an older cached artefact draws "history not recorded". A sweep is drawn from `SweepArtefact.summary["rows"]`, not importing `sweep` | FR-30. `NewtonResult.summary` drops the history. One sampling path for figure and export |
| D4 The figures | All in (r, z), r ≥ 0, in stage 1's frame. **1** atoms at r = hypot(x, y). **2** the density's axial section. **3** the reduced map and its azimuthal variance. **4** the contour, over the map given inputs. **5** the named regions. **6** element size h and SICN, with the 0.3 floor marked. **7a** each titratable site's charge. **7** the stored charge and ε_r grids. **8** each correction over **⟨c⟩ = (1/n)Σcᵢ, the driver `evaluate` takes, not the ionic strength**, with the validity range shaded, and over d, the distance to the nearest pore boundary, from 0. **10** potential, concentrations, velocity and pressure, plus residual and damping per rung, titled with the model and the stabilisation mode. **11** the quantities as a table. **Sweep** each scalar quantity against the swept axis, with any point not `ok` marked | The physics rules. The Phase 4 plan's "against ionic strength" is corrected in this commit |
| D5 Extras and notebooks | `plot = ["matplotlib>=3.8"]`; `notebook = ["nanopnp[plot]", "marimo>=<the release uv resolves>"]`; `examples = ["nanopnp[plot]"]`. Each `notebooks/NN-<area>/` holds a `README.md` with `<!-- example: run -->` commands, the notebook and its case files: **01-geometry** example 06's case to `mesh`; **02-charge** example 07's to `materials`; **03-solve** example 02's ePNP-NS case; **04-sweep** example 03's charged sweep. Each ends `if __name__ == "__main__": app.run()` and has a stage selector plus at most two widgets over case fields. The widget defaults are the example's values, so a headless run solves the example's case | P5. `copy_example` keeps the depth, so `../../` paths resolve as example 07's do |
| D6 Clauses | `plot` follows `post` in `LAYER_ORDER` and `modularity-layering.yaml`, with no upward edge. VER-65's set stays at eleven, since `plot` reaches the backend only through `post` and `solve`. §5.1 and `CLAUDE.md`'s structure list gain `plot/`. `CHANGELOG.md` lists the new keyword, `register_figure`, the `RunResult` additions, the extras and the payload. REV-123 is set `fixed` | P3, P6; H12 |

### Work items

- [ ] 1. The extras and `uv.lock`; the layer order, the record, §5.1 and `CLAUDE.md`; an empty
  `plot/` (D5, D6); done when `tests/tier1/test_layering.py` and `test_backend_guard.py` pass.
- [ ] 2. `core/stages.py`'s figure registry and `draw`; `_repr_mimebundle_`; the `RunResult` additions
  (D1, D2); done when `test_figure_classification_both_ways` passes.
- [ ] 3. `post/export.py`'s `restored` and `sampled_fields`; the solve stage's `newton_history.json`
  (D3); done when Tier 1 and the Tier 2 modules for examples 01 and 02 pass unchanged and
  `physics-reviewer` reports no finding.

*Compaction checkpoint: after item 3; resume from this plan and `git log`.*

- [ ] 4. `plot/data.py` and `plot/figures.py` for stages 1 to 8 and the sweep, registered (D3, D4);
  done when the Tier 1 data-layer tests pass.
- [ ] 5. Stages 10 and 11; the per-push smoke tests, the grid sample and the import guard (D4); done
  when the Tier 2 modules for examples 01 and 02 pass.
- [ ] 6. The smoke tests for examples 03, 06 and 07; done when they pass with `--nightly`.

*Compaction checkpoint: after item 6; resume from this plan and `git log`.*

- [ ] 7. `notebooks/` and `tests/tier2/test_notebooks.py` (D5). Once, by hand, a notebook with a
  raising cell must exit non-zero, recorded in the Outcome; done when the test passes with `--nightly`.
- [ ] 8. `CHANGELOG.md`, REV-123, the Outcome (notebook and push-gate seconds), `current.md`, the
  Phase 4 plan (D6); done when `gate.sh run` and the strict documentation build pass.

### Verification

FR-30 is named in commit bodies, not test names (N3); no baseline image (P4). VER-61, VER-62 and
VER-65 run unchanged. Tier 1 rows are `tests/tier1/test_figures.py`; "01" is
`tests/tier2/test_examples_01_quickstart.py`.

| Test | Tier | Oracle | Tolerance |
|---|---|---|---|
| `test_figure_classification_both_ways` | 1 | Each builtin stage declares a figure or is in `FIGURE_FREE`, never both; each target names a function | Exact |
| `test_structure_atoms_land_at_r_hypot_in_metres` | 1 | An atom at known (x, y, z) gives r = hypot(x, y) and z, in m | 1e-12 relative |
| `test_mesh_size_and_sicn_are_si_per_element` | 1 | Two triangles: h in m; SICN equals `element_quality`'s per element | 1e-12 relative |
| `test_correction_driver_is_mean_concentration_not_ionic_strength` | 1 | A 2:1 salt's driver is (1/n)Σcᵢ, not the ionic strength; the factor is `evaluate`'s there | 1e-12 relative |
| `test_sweep_curves_keep_failed_points` | 1 | Rows ordered by axis value; the point not `ok` kept and marked | Exact |
| `test_field_on_a_grid_matches_sample_at`, in 01 | 2 | A 5 × 5 fluid grid gives `sample_at` × `field_scale` at the same nm points, potential and exponentiated concentrations, r before z | 1e-12 relative |
| `test_every_figure_draws_and_displays`, in 01's and 02's ePNP-NS modules; 03's, 06's, 07's nightly | 2 | The re-walk on the fixture's store hits the cache everywhere; each figure has an axis; each artefact's and the `RunResult`'s `_repr_mimebundle_` embeds a PNG in `text/html` | Exact |
| `test_default_import_and_walk_load_no_plotting`, in 01 | 2 | A subprocess imports `nanopnp` and `nanopnp.plot` and re-walks the case; no `matplotlib` or `marimo` in `sys.modules` | Exact |
| `test_notebook_runs_headless[<notebook>]`, `tests/tier2/test_notebooks.py` | 2, nightly | Each directory has a `run` command; each exits 0 | Exit codes |

Commands: `uv run pytest <file>`, with `--nightly` for the nightly rows.

### Out of scope

- FR-28, exporting figures from a run: v0.7.
- The GUI's own plots, and whether the browser shell reads `plot/data.py`: Phase 5 (M3, P3).
- The notebooks on the site: documentation increment 4. Session 04: WP52.

### Open questions

None blocking. The *Your call* defaults to its recommendation; a contrary ruling adds a line to
`core/public.py`.
