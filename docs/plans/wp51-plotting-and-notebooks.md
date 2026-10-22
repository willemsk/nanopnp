# WP51 — The plotting library and the notebooks

**Status: planned, not started.** Written 22 October 2026. Inherits WP50 and §8.2.14.

The [Phase 4 plan](phase-4-polish-and-user-testing.md) owns the phase. `SPECIFICATION.md` governs;
where this plan and it disagree, this plan is wrong. Identifiers are pointers, never restatements.

## In brief

**What changes.** In a notebook, every step's result shows itself as a picture, from the atoms to
the solved fields and a sweep's curves; without the plotting add-on, as a short summary. Four
notebooks run nightly, so they cannot go stale before the sessions.

**Cost.** About a week. Each push gains seconds; the pictures reuse the checks' runs.

**What could go wrong.** A picture could mislabel a unit or swap the radial and axial axes;
tests check the conversions, and the author looks before the merge. A plotting import could slow
every start-up; a test fails if one reaches the default path.

**Your call.**
- Should anything join the top-level public names? *Recommendation:* no; results
  display themselves.

## Execution brief

Scope: the Phase 4 plan's WP51; FR-30; §8.2.14 P2 to P6; REV-123. Depends on WP50.
Tag `v0.5.0-alpha.17`. Models: Sonnet; Haiku for items 1 and 7. Item 3 touches `solve/` and
`post/` without changing a number; `physics-reviewer` reads it.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 Layout and names | `plot/__init__.py` exports `figure(artefact, *, inputs=None)` → `matplotlib.figure.Figure`. `plot/data.py` turns an artefact into arrays in SI and the model frame and never imports Matplotlib. `plot/figures.py` has one `<stage>_figure(artefact, inputs)` each, building a `Figure` without `pyplot`. Display units (nm, M, V) come from one table and are named on every axis. `RunResult` gains `resolved: ResolvedCase \| None = None`, set by the walk, and `figure(stage)`, which calls `core.stages.draw`, so `pipeline` gains no edge to `plot`. **No name joins `PUBLIC`** | P3; F4. `pyplot` is global state a widget's re-run would leak |
| D2 Registry and display | `register` takes `figure: str \| None = None`, a `module:function` validated as `target` is. `register_figure(schema, target)` serves the sweep dataset, which no stage emits. Also `FIGURE_FREE = frozenset({"case", "report"})` and `figure_target(schema)`. `draw(artefact, inputs)` imports the target and calls it. A `ModuleNotFoundError` naming `matplotlib`, raised at the call because figures import it inside, becomes `MissingExtraError` naming `plot`. The base `Artefact` dispatches on schema, because `Store.get` returns the base class. `_repr_mimebundle_(include=None, exclude=None)` on `Artefact` and `RunResult` returns `text/plain` always, plus `text/html` holding the summary and an embedded PNG. Only `MissingExtraError` falls back to text. `RunResult` shows its stage records and quantities, with the solve's figure or else its last figured stage's | P6. marimo and Jupyter both read `_repr_mimebundle_` (Context7). `core → plot` is a `string` row with MOD-15, as `core → solve` is |
| D3 What a figure reads | `inputs` is the walk's `StageInputs`, built through `offered`. A bare artefact draws what its payload and summary carry; where that is nothing, it shows text naming `result.figure(stage)`. That covers materials, and a supplied mesh (examples 01 to 03), whose stage-6 artefact has no payload; with inputs, the mesh figure reads `deployed_mesh(inputs.resolved, artefact)`. Two functions factored within `post/` serve the fields, leaving IF-07's export unchanged: `restored(inputs, solution)`, from the report stage, and `sampled_fields(solution, scales)`, from `export_fields`. `_instrumented`'s `on_rung` and `on_step` record every event, hook or none, and the stage writes them as `newton_history.json`: `{"rungs": [{"name", "stage", "steps": [{"iteration", "residual", "update", "damping", "trials", "forced"}]}]}`. A payload is outside the digest, so the hash, the manifest and VER-62 hold; an older cached artefact draws "history not recorded". A sweep is drawn from `SweepArtefact.summary["rows"]` | FR-30. `NewtonResult.summary` drops the history. One sampling path for figure and export |
| D4 The figures | All in (r, z), r ≥ 0, in stage 1's frame. **1** atoms at r = hypot(x, y). **2** the density's axial section. **3** the reduced map and its azimuthal variance. **4** the contour, over the map given inputs. **5** the named regions. **6** element size h and SICN, with the 0.3 floor marked. **7a** each titratable site's charge. **7** the stored charge and ε_r grids. **8** each correction over **⟨c⟩ = (1/n)Σcᵢ, the driver `evaluate` takes, not the ionic strength**, validity range shaded, and over d, the distance to the nearest pore boundary, from 0. **10** potential, concentrations, velocity, pressure, and residual and damping per rung, titled with model and stabilisation mode. **11** the quantities as a table. **Sweep** each scalar quantity against the swept axis, any point not `ok` marked | The physics rules; the Phase 4 plan's "ionic strength" is corrected here |
| D5 Extras and notebooks | `plot = ["matplotlib>=3.8"]`; `notebook = ["nanopnp[plot]", "marimo>=<the release uv resolves>"]`; `examples = ["nanopnp[plot]"]`. Each `notebooks/NN-<area>/` holds a `README.md` with `<!-- example: run -->` commands, the notebook and its case files: **01-geometry** example 06's case to `mesh`; **02-charge** example 07's to `materials`; **03-solve** example 02's ePNP-NS case; **04-sweep** example 03's charged sweep. Each ends `if __name__ == "__main__": app.run()`. Widgets: 01 a stage selector; 02 that and the salt concentration; 03 the bias; 04 a point selector showing its row. A widget edits the case through `CaseDocument.model_copy(update=...)`, never the internal `with_section`. The defaults are the example's values, so a headless run solves the example's case | P5; `copy_example` keeps `../../` paths valid, as for example 07 |
| D6 Clauses | `plot` follows `post` in `LAYER_ORDER`. `modularity-layering.yaml` gains the `core → plot` row and `plot`'s downward static rows; `upward:` and `deferred_upward:` stay empty. VER-65 stays at eleven: `plot` reaches the backend only through `post` and `solve`. §5.1 and `CLAUDE.md` gain `plot/`; `CHANGELOG.md` lists the API additions, the extras and the payload. REV-123 is set `fixed` | P3, P6; H12 |

### Work items

- [ ] 1. Extras, `uv.lock`, layer order, record, §5.1, `CLAUDE.md`, an empty `plot/` (D5, D6); done
  when `tests/tier1/test_layering.py` and `test_backend_guard.py` pass.
- [ ] 2. The figure registry, `draw`, `_repr_mimebundle_`, the `RunResult` additions (D1, D2); done
  when `test_figure_classification_both_ways` passes.
- [ ] 3. `restored`, `sampled_fields`, `newton_history.json` (D3); done when Tier 1 and examples
  01's and 02's Tier 2 modules pass unchanged and `physics-reviewer` finds nothing.

*Compaction checkpoint: after item 3; resume from this plan and `git log`.*

- [ ] 4. `plot/data.py` and `plot/figures.py` for stages 1 to 8 and the sweep, registered (D3, D4);
  done when the Tier 1 data-layer tests pass.
- [ ] 5. Stages 10 and 11; the per-push smoke tests, the grid sample and the import guard (D4); done
  when the Tier 2 modules for examples 01 and 02 pass.
- [ ] 6. The smoke tests for examples 03, 06 and 07; done when they pass with `--nightly`.

*Compaction checkpoint: after item 6; resume from this plan and `git log`.*

- [ ] 7. `notebooks/` and `tests/tier2/test_notebooks.py` (D5); by hand once, a raising cell exits
  non-zero (Outcome); done when the test passes with `--nightly`.
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
| `test_every_figure_draws_and_displays`, in 01's and 02's ePNP-NS modules; 03's, 06's, 07's nightly | 2 | A helper in `tests/tier2/conftest.py` chdirs into the copied example and calls `run_document` on its case with `Store(example / "store")` and the README's `upto`; every `StageRecord.cached` is true; each figure has an axis; each artefact's and the `RunResult`'s `text/html` embeds a PNG | Exact |
| `test_default_import_and_walk_load_no_plotting`, in 01 | 2 | A subprocess, in the example, imports `nanopnp` and `nanopnp.plot` and re-walks; no `matplotlib` or `marimo` in `sys.modules` | Exact |
| `test_notebook_runs_headless[<notebook>]`, `tests/tier2/test_notebooks.py` | 2, nightly | Each directory has a `run` command; each exits 0 | Exit codes |

Commands: `uv run pytest <file>`, with `--nightly` for the nightly rows.

### Out of scope

FR-28's figure export (v0.7); the GUI's plots (Phase 5, M3); the notebooks on the site
(documentation increment 4); session 04 (WP52).

### Open questions

None blocking. The *Your call* defaults to its recommendation; a contrary ruling adds a line to
`core/public.py`.
