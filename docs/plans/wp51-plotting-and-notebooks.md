# WP51 — The plotting library and the notebooks

PR: [#119](https://github.com/willemsk/nanopnp/pull/119), branch ccr-10787f91-npvpk1

**Status: delivered, 22 October 2026.** Written 22 October 2026; grounded in the code at `1eb209d`
(§8.2.15 Q1). Inherits WP50 as shipped (§8.2.13) and the Phase 4 amendment (§8.2.14 P1 to P7).

The [Phase 4 plan](phase-4-polish-and-user-testing.md) owns the phase. `SPECIFICATION.md` governs;
where this plan and it disagree, this plan is wrong. Identifiers are pointers, never restatements.

## In brief

The author asked to see what every step of the pipeline produces, and to try the program by hand.

**What changes.** In a notebook, every step's result shows itself as a picture: the atoms, the
density, the pore's outline, the mesh, the charges, the corrections, the solved fields with the
solver's convergence, the numbers, and a sweep's curves. Without the plotting add-on, a result
shows a short text summary. Six notebooks run every night, so they cannot go stale before the
sessions.

**Cost.** About a week of work. Each push gains a few seconds, since the pictures reuse runs the
checks already make.

**What could go wrong.** A picture could mislabel a unit or swap the radial and axial directions;
tests check the conversions, and the author looks before the merge. A plotting import could slow
every user's start-up; a test fails if one reaches the default path.

**Your call.**
- Should anything be added to the program's top-level public names? *Recommendation:* no; results
  display themselves, and a name added now is one more to keep.

## Execution brief

Scope: the Phase 4 plan's WP51; FR-30; §8.2.14 P2 to P6; REV-123. Depends on WP50, merged. Tag
`v0.5.0-alpha.17`. Models: Sonnet by default; Haiku for items 1 and 7. Item 3 touches `solve/` and
`post/` without changing a number, and `physics-reviewer` reads its diff.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 Layout and names | `plot/__init__.py` exports `figure(artefact, *, inputs=None)`, which returns a `matplotlib.figure.Figure`. `plot/data.py` turns an artefact into arrays in SI and the model frame and never imports Matplotlib. `plot/figures.py` has one `<stage>_figure(artefact, inputs)` per figure, each building a `Figure` without `pyplot`. Display units (nm, M, V) come from one table and are named on every axis. `RunResult` gains `resolved` and `figure(stage)`. **No name joins `PUBLIC`** | P3; F4. `pyplot` is global state that a widget's re-run would leak |
| D2 Registry and display | `register` takes `figure=`, a `module:function`. `register_figure(schema, target)` serves the sweep dataset, which no stage emits. `FIGURE_FREE` is `case` and `report`. `draw(artefact, inputs)` resolves a schema's target and calls it; a missing Matplotlib becomes `MissingExtraError` naming `plot`. `Artefact` and `RunResult` implement `_repr_mimebundle_`: `text/plain` always, plus `text/html` holding the summary and an embedded PNG. Only `MissingExtraError` falls back to text | P6. marimo and Jupyter both read `_repr_mimebundle_` (marimo, *Displaying objects*, via Context7) |
| D3 What a figure reads | `inputs` is the walk's own `StageInputs`. A bare artefact draws what its payload and summary carry; where that is nothing, it shows text naming `result.figure(stage)`. Fields are read through the export's own restore and sampling, factored out of `post/` with the IF-07 export unchanged. The solve stage writes its Newton history as a payload. A sweep is drawn from its `io` artefact's rows | FR-30: "from the stored artefacts alone". One sampling path for figure and export |
| D4 The figures | All in (r, z), r ≥ 0, in stage 1's frame. **1** the atoms at r = hypot(x, y). **2** the density's axial section. **3** the reduced map and its variance. **4** the contour, over the map when inputs are given. **5** the named regions. **6** element size h and SICN, with the 0.3 floor marked. **7a** each titratable residue's charge. **7** the stored charge and ε_r grids. **8** each correction against **the driver the electrolyte declares**, with the validity range shaded. That is ⟨c⟩ = (1/n)Σcᵢ by default, the ionic strength only where the corrections file says so, and the axis is labelled to match. Each is also drawn against d, the distance to the nearest pore boundary, from 0. **10** the potential, the concentrations, the velocity and the pressure, plus residual and damping per rung, titled with the model and the stabilisation mode. **11** the quantities, as a table. **Sweep** the current (nA) and the electro-osmotic flow rate (µm³/s) large against the swept axis, then each other scalar quantity, with any point not `ok` marked (P9). `scale` enlarges any figure; the notebooks add a size slider and a zoom-and-pan switch | The physics rules. The Phase 4 plan's "ionic strength" is corrected |
| D5 Extras and notebooks | `plot = ["matplotlib>=3.8"]`; `notebook = ["nanopnp[plot]", "marimo>=<the release uv resolves>"]`; `examples = ["nanopnp[plot]"]`. One directory per notebook, `notebooks/NN-<area>/`: **01-geometry** example 06's case to `mesh`; **02-charge** example 07's case to `materials`; **03-solve** example 02's ePNP-NS case; **04-sweep** example 03's charged sweep. Each is run headless from its README, every night. Each has at most two widgets, and their defaults are the example's values, so a headless run solves the example's own case | P5 |
| D6 Clauses | `plot` follows `post` in the layer order, with no upward edge, and VER-65's set stays at eleven. §5.1 and `CLAUDE.md`'s structure list gain `plot/`. `CHANGELOG.md` lists the API additions, the extras and the new payload. REV-123 is set `fixed` | P3, P6; H12 |

### Grounding

**D1**
- `pipeline/run.py:RunResult` is a frozen dataclass. It gains `resolved: ResolvedCase | None = None`, which the walk sets from `_Walk.resolved`. `figure(stage)` builds `StageInputs(resolved=self.resolved, upstream=offered(stage, self.artefacts, own=False))` and calls `core.stages.draw`, so `pipeline` gains no edge to `plot`. `tests/tier1/test_public_api.py` does not pin `RunResult`'s fields.

**D2**
- `core/stages.py:StageEntry` gains `figure: str | None = None`. `register` checks it with `target`'s rule, one `:`.
- `register_figure` writes a separate `_FIGURES: dict[str, str]` keyed by schema. `_register_builtins` calls it for `"nanopnp/sweep/v0.5"` as a literal, since `core` does not import `io` at run time.
- `figure_target(schema)` looks at the registered stages' `artefact_schema` first, then `_FIGURES`. A schema with no target, such as `ChargeGridArtefact`'s, displays as text.
- Figures import Matplotlib inside the function, so `draw` catches a `ModuleNotFoundError` whose `name` starts with `matplotlib` around the *call*, not the import as `create` does.
- `io/store.py:Store.get` returns the base `Artefact`, never the subclass. So `io/artefact.py:Artefact._repr_mimebundle_(self, include=None, exclude=None)` dispatches on `self.schema`, importing `core.stages` (`io → core`, an existing edge). The PNG is `Figure.savefig(BytesIO(), format="png", dpi=100)`, base64-encoded into an `<img>` tag.
- `RunResult` shows a table of `StageRecord.summary()` rows and `quantities`, with the solve's figure if it has one, else that of its last stage that has one.
- Layering: `modularity-layering.yaml` gains `{from: core, to: plot, relation: string, finding: MOD-15}`, as `core → solve` is recorded, and `plot`'s downward `static` rows.

**D3**
- The upstream a figure needs comes from `inputs.upstream`, by stage name: `mesh`, `symmetry` for the contour, `charge`, `materials`.
- `solve/stage.py:SolveStage._instrumented`: its `on_rung` and `on_step` closures run on every solve. `on_step` is passed as `callback` only where `declaration(rung.model.name).reports_newton`. The closures append to a record whether or not `self._solve_hook` is set, and `run` writes it beside `_write`'s payload as `newton_history.json`: `{"rungs": [{"name", "stage", "steps": [{"iteration", "residual", "update", "damping", "trials", "forced"}]}]}`. A non-reporting rung has `steps: []`.
- `io/artefact.py:Artefact.hash` covers the schema, parameters and inputs only. The manifest copies `solve.summary`, not the payload (`pipeline/run.py`). An artefact cached before WP51 lacks the file and draws "history not recorded".
- `post/stage.py:ReportStage._export` has a restore block: `read_fields`, then `restore(state_path, resolved=..., mesh_artefact=..., fields=..., charge_artefact=...)`. That block becomes `post/export.py:restored(inputs, solution)`. `export_fields`'s per-field loop becomes `sampled_fields(solution, scales)`, returning the two `P2Nodes` sets and the whole and restricted arrays: `sample_at`, then `exp` on `logarithmic_fields`, then `field_scale`. Both callers keep their output. Draw with `Triangulation` on `P2Nodes.points_nm`, using the corner columns `cells[:, :3]`.
- Stage 6: `mesh/ingest.py:MESH_PAYLOAD` exists only for a generated mesh. A supplied mesh, as in examples 01 to 03, has an empty payload. With inputs, the mesh figure reads `deployed_mesh(inputs.resolved, artefact).data` (`MeshData`: `vertices` in nm, `triangles`) and `.quality` (`QualityReport.sicn`). Bare, it reads `adapter.read(payload["mesh"], format="msh41")`, or shows text when the payload is empty.
- The payload readers, keyed by each module's `PAYLOAD_NAME`:
  - `structure/ensemble.py:AlignedEnsemble.read` gives `positions_nm` `(frames, atoms, 3)`.
  - `density/map.py:DensityMap.read` gives `values` on `grid`.
  - `symmetry/reduce.py:ReducedMap.read` gives `r_nm`, `z_nm`, `mean` and `cn_variance`.
  - The contour's `"profile"` is read by `geometry/profile.py:load_profile`.
  - `geometry/region.py:read_region` gives a `RegionRecord`.
  - `charge/protonation.py:ProtonationTable.read` gives `residue_*` and `residue_charge_e`.
  - `density/grid.py:read_grid(path, format="npz")` reads the charge stage's `charge`, `lattice` and `eps_r` keys (`charge/stage.py`).
- Stage 8: `inputs.resolved.electrolyte.corrections` maps each property to a `CorrectionModel`. Its `evaluate(c_avg_M, wall_distance_nm)` takes the driver value in mol/L directly and uses `NUMPY_OPS` by default. The validity range is `FittedCorrection.validity_M`.
- `materials/electrolyte.py:Electrolyte.driver` is `"average"` or `"ionic_strength"`, and `average_concentration` forms either from the species' concentrations. So the curve's x values are driver values, labelled ⟨c⟩ or I by `driver`. The d curve is drawn at the case's `concentration_M`, given as the driver value and labelled as such.
- The sweep: `io/artefact.py:SweepArtefact.summary["rows"]` is a list of `MemberResult.row()`, each with `status`, `assignments` (case path → value) and `quantities`. The swept axis is the assignment that varies.

**D5**
- `validation/examples.py:copy_example` puts a copy at `root/examples/<name>`, the same depth as `notebooks/<name>`. A notebook prepares its own input (its first cell runs example 06's `prepare.py`, or `nanopnp mesh cylinder`, when the file is missing), so its README names no `../` path. `test_notebook_runs_headless` copies the examples and the 2WCD entry the notebook reads beside it. `run_tagged` resolves `python` to `sys.executable`.
- Each notebook ends `if __name__ == "__main__": app.run()`.
- Widgets:
  - 01 has a stage selector.
  - 02 has a stage selector and the salt concentration.
  - 03 has the bias.
  - 04 has a point selector showing that point's row.
- A widget edits the case through `CaseDocument.model_copy(update=...)`, never the internal `with_section`, and runs `run_document(document, store=Store("store"), upto=...)`.

**Tests**
- Examples 01's and 02's modules have a module-scoped `ran` fixture. It copies the example and runs its README with `--store store`. Example 01's mesh comes from `nanopnp mesh cylinder --out pore.msh`, and its case resolves `pore.msh` against the working directory.
- A helper in `tests/tier2/conftest.py`, `cached_run(example, case, upto=None)`, chdirs with `monkeypatch`, then calls `run_document(load_case(case), store=Store(example / "store"), upto=upto)`. For 06 the README's run is `--upto mesh`. For 07, `2wcd.case.yaml` runs the whole pipeline, and only `from-pqr` and `switches` stop at `charge`.

### Work items

- [x] 1. Extras, `uv.lock`, `LAYER_ORDER`, the layering record, §5.1, `CLAUDE.md`, an empty
  `plot/` (D5, D6); done when `tests/tier1/test_layering.py` and `test_backend_guard.py` pass.
- [ ] 2. The figure registry, `draw`, `_repr_mimebundle_` and the `RunResult` additions (D1, D2);
  done when `test_figure_classification_both_ways` passes.
- [x] 3. `restored`, `sampled_fields` and `newton_history.json` (D3); done when Tier 1 and examples
  01's and 02's Tier 2 modules pass unchanged and `physics-reviewer` finds nothing.

*Compaction checkpoint: after item 3; resume from this plan and `git log`.*

- [x] 4. `plot/data.py` and `plot/figures.py` for stages 1 to 8 and the sweep, registered (D3, D4);
  done when the Tier 1 data-layer tests pass.
- [x] 5. Stages 10 and 11; `cached_run`; the per-push smoke tests, the grid sample and the import
  guard (D4); done when examples 01's and 02's Tier 2 modules pass.
- [x] 6. The smoke tests for examples 03, 06 and 07; done when they pass with `--nightly`.

*Compaction checkpoint: after item 6; resume from this plan and `git log`.*

- [x] 7. `notebooks/` and `tests/tier2/test_notebooks.py` (D5). Once, by hand, a notebook with a
  raising cell must exit non-zero, recorded in the Outcome; done when the test passes with `--nightly`.
- [x] 8. `CHANGELOG.md`, REV-123, the Outcome (each notebook's nightly seconds and the push gate's
  added seconds), `current.md` and the Phase 4 plan (D6); done when `.claude/hooks/gate.sh run` and
  the strict documentation build pass.

### Verification

FR-30 is named in commit bodies, not test names (N3); no figure is compared with a baseline image
(P4). VER-61, VER-62 and VER-65 run unchanged. The Tier 1 rows are in `tests/tier1/test_figures.py`;
"01" is `tests/tier2/test_examples_01_quickstart.py`.

| Test | Tier | Oracle | Tolerance |
|---|---|---|---|
| `test_figure_classification_both_ways` | 1 | Each builtin stage either declares a figure or is in `FIGURE_FREE`, never both; each target, the sweep's included, names a function | Exact |
| `test_structure_atoms_land_at_r_hypot_in_metres` | 1 | An atom at known (x, y, z) in nm gives r = hypot(x, y) and z, in m | 1e-12 relative |
| `test_mesh_size_and_sicn_are_si_per_element` | 1 | Two triangles: h in m, and SICN equal to `element_quality`'s, per element | 1e-12 relative |
| `test_correction_curve_follows_the_declared_driver` | 1 | For each of the `average` and `ionic_strength` drivers, each curve's values equal `evaluate`'s at its x values, the axis names that driver, and the shaded band is `validity_M` | 1e-12 relative |
| `test_sweep_curves_keep_failed_points` | 1 | Rows come out ordered by axis value, with the point not `ok` kept and marked | Exact |
| `test_field_on_a_grid_matches_sample_at`, in 01 | 2 | On the cached run, a 5 × 5 fluid grid gives `sample_at` × `field_scale` at the same nm points, for the potential and the exponentiated concentrations, with r before z | 1e-12 relative |
| `test_every_figure_draws_and_displays`, in 01's and 02's ePNP-NS modules; nightly in 03's, 06's and 07's | 2 | Under `cached_run`, every `StageRecord.cached` is true. Each declared figure has an axis. Each artefact's and the `RunResult`'s `text/html` embeds a PNG | Exact |
| `test_default_import_and_walk_load_no_plotting`, in 01 | 2 | A subprocess in the copied example imports `nanopnp` and `nanopnp.plot` and re-walks; neither `matplotlib` nor `marimo` is in `sys.modules` | Exact |
| `test_notebook_runs_headless[<notebook>]`, `tests/tier2/test_notebooks.py` | 2, nightly | Each directory has a `run` command, and each exits 0 | Exit codes |

Commands: `uv run pytest <file>`, with `--nightly` for the nightly rows.

### Out of scope

- FR-28, exporting figures from a run: v0.7.
- The GUI's own plots, and whether the browser shell reads `plot/data.py`: Phase 5 (M3, P3).
- The notebooks on the documentation site: documentation increment 4. Session 04's notebook: WP52.

### Open questions

None blocking. The *Your call* defaults to its recommendation; a contrary ruling adds a line to
`core/public.py`.

> **Outcome — every stage has a figure, and every artefact and run result displays itself.** Measured on
> 4 cores, 22 October 2026. `plot/` holds the data layer and thirteen figures. After the author's review `nanopnp.Case` joined `PUBLIC` (§8.2.14 P8), so a notebook edits a case with one call.
> A sweep's figure now leads with the I-V curve and the flow rate, `figure(..., scale=)` enlarges any figure, and each notebook has a size slider and a zoom-and-pan switch (P9); 05 runs headless in 41.6 s with example 03 outputting `eof_rate`.
> The per-push gate gains about 13 s: the figure test is 5.9 s on example 02 and 5.4 s on example 01, and
> the import guard, grid sample and Tier 1 data tests together a second; both examples' walks were
> already in the gate. The notebooks run nightly in 73.8 s (01), 6.4 s (02; shorter than 01, its cache
> provenance not examined), 26.9 s (03) and 41.7 s (04); the end-to-end notebooks take 45.3 s (05, cylinder) and 658.7 s (06, 2WCD, whose walk runs headless as the Run button cannot be pressed). The notebooks prepare their own input in a first cell. By hand, once: a marimo script with a cell
> that raises exits 1, so the nightly test fails on a stale notebook. Corrections to the plan:
> `cached_run` calls `run_case`, since `run_document` needs the case text; the Newton history of the
> Poisson-Boltzmann rung has `steps: []` (that rung reports no steps); `test_field_export.py` patches
> `post.export`, where `read_fields` now lives; the notebooks' files are `notebook.py`, and ruff
> ignores D100, ANN and B018 under `notebooks/`. **The figures of stages 1 to 5 and 7 have passed
> only their smoke tests; the author must look at every figure and notebook before the merge.**
