# WP54 — The notebooks and figures revised

**Status: in progress; items 1 to 10 done.** Written 28 October 2026 from the author's notes,
[notebooks-review-for-wp54.md](notebooks-review-for-wp54.md), and the rulings they carry
(§8.2.20 V1 to V5). Inherits WP51 as shipped (§8.2.14 P2 to P10) and WP53's commands.

The [Phase 4 plan](phase-4-polish-and-user-testing.md) owns the phase. `SPECIFICATION.md` governs;
where this plan and it disagree, this plan is wrong. Identifiers are pointers, never restatements.

## In brief

The six notebooks become a way to work with the program from Python, not a replay of example files.

**What changes.** A notebook builds a pore in a line of typed Python, runs it, and shows the result:
the potential in millivolts, centred on zero; the ion concentrations against the bulk, so depletion
shows; the flow with its direction; profiles along the axis and across the pore; and the mesh as a
whole beside a close-up of the pore. A sweep of voltages is one call. The protein notebooks start
from the deposited entry and share one store, so the long steps run once. Moving a slider redraws
at once; a slow step waits for a submit button. At each pause in the work you get a private page of
each notebook to read and comment on.

**Cost.** About a week. The nightly run grows by the protein notebooks' first walk, then shrinks,
since they share it. A push does not grow.

**What could go wrong.** The shared store could hide a stale result; it is keyed by content, as every
run is. The published pages do not recompute when a slider moves; they show the defaults.

**Your call.**
- Your notes give the cylinder a uniform wall charge, which the case file cannot say without a
  change of format, which you ruled out. Should the cylinder notebooks use the ring of charge the
  examples already use? *Recommendation:* yes; the format change waits for its own package.

## Execution brief

Scope: the author's notes, Areas A to D, under V1 to V5; FR-30 and FR-37 as amended in this commit.
Depends on WP53. Claims FR-30's and FR-37's new tests; VER-61, VER-62 and VER-65 stay green. Tag `v0.5.0-alpha.20`. Implementing session: Sonnet, high effort. A `physics-reviewer` pass on items 2 and 7 (units,
the bulk reference, the sign of u_z). Three slices (cylinder API, figures, structure), each ending
in a checkpoint that publishes the notebooks revised so far (V5).

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 Library entry points | `nanopnp.mesh.mesh_cylinder` (the CLI's path, moved); `nanopnp.structure.orient_pore`, `cis_end` required; `structure_file` takes a full file name, falling back to `tests/data/structures/` in a checkout (the 2.4 MB entry stays out of the wheel); `Case.cylinder` and `Case.from_structure`, the validated ePNP-NS model, corrections and solid permittivities from the parameter file; `Case.load` makes relative input paths absolute against the case file. `mesh_cylinder` and `orient_pore` join `PUBLIC` | V1, V3. FR-37 forbids a rule for one pore, so the flip is the user's. No permittivity is written in Python (`CLAUDE.md`) |
| D2 In-memory sweep | `nanopnp.sweep.sweep(case, axis=, values=, origin=0)` writes `base.case.yaml` and `sweep.yaml` into `<store>/sweeps/<name>-<hash12>/` and returns a `Sweep` whose `run(workers=1)` plans, runs and collects, returning the `SweepArtefact`. `SweepPlan` is unchanged. A relative input path is refused. `sweep` stays out of `PUBLIC` | Members and parallel workers re-read the base from disk, so an in-memory base is a second code path. `import nanopnp.sweep.plan` would shadow a top-level `sweep` |
| D3 Field figures | Potential in mV, `CenteredNorm(vcenter=0)`; concentrations as log₁₀(c/c_bulk), centred at 0, c_bulk from the case; signed u_z centred at 0, with `streamplot` on a 60 × 120 grid over the lumen window; the deposited charge centred at 0 with the χ = 0.5 contour; marks for the stage-4 constriction and the operating concentration; each rectification ratio and G at the smallest positive bias on the sweep. Every panel is a function of `plot/panels.py` taking `ax=` | V4. `TwoSlopeNorm` raises on one-signed data. Stage figures and notebooks call the same panels |
| D4 Cutlines and `RunResult` | `SolutionFields` and `solution_fields` move to `post/export.py` and keep the six-node cells; `plot` splits each P2 triangle into four linear ones before any triangulation. `axial_cutline` and `radial_cutline` interpolate with `LinearTriInterpolator`, the potential on the whole domain and the rest on the fluid, so a radial line is NaN in the solid. `RunResult.current_nA`, `conductance_nS` (from `conductance_S`, `None` at zero bias) and `fields` | V4; the notes' E1: no second restore. Midside values make a cutline exact at the P2 nodes. P6: no layer imports `plot` |
| D5 Mesh figure | The whole domain by element size; beside it the lumen window (r ≤ 5 nm, \|z\| ≤ 10 nm by default) by SICN with the wireframe and a λ_D/5 bar, from `case_debye_record(inputs.resolved)`, else the artefact's `sizing`, else none | V4; NUM-30 on the mesh. A supplied mesh has no `sizing` |
| D6 Notebooks | No `os.chdir`, `importlib`, CLI call, `only=True` or `scale`/`interactive` cell. Store: `$NANOPNP_STORE`, else `notebooks/.store` (gitignored). A slow stage (orientation, structure to mesh, protonation, solve, sweep) reads a `.form()`'s value, `None` falling back to the defaults; a debounced slider drives only the contour or a view of a solved field. 01, 02 and 06 call `Case.from_structure` with identical arguments, so they share stages 1 to 8 | V2, V5. The nightly submits nothing, so it runs the defaults |

### Grounding

**D1**
- `cli/__init__.py:_mesh` builds `CylindricalPoreGeometry(...)`, calls `generate(maxh_nm=, wall_h_nm=, check_quality=False)`, then writes a `.partial` file, applies `{"default": "interface"}`, gates (`check_quality`, `check_radii`) and renames. The reference shape shares the write block.
- Defaults live in `mesh/defaults.py`; `mesh/__init__.py` holds only a docstring.
- `core/paths.py:structure_file(name)` appends `.pdb` and looks in `data/structures/`, which holds only `2wcd-a-18-26.pdb` (the GUI probe's `FRAGMENT`). `2wcd.pdb.gz` is in `tests/data/structures/`, sha256 in its README. `pyproject.toml` force-includes `data/` in the wheel.
- `examples/06-pdb-to-mesh/prepare.py` holds the algorithm: covariance eigenvector, sign by the mean C-α radius of the top and bottom fifths, Rodrigues rotation, the registration centroid to `CENTROID_Z_NM`. MDAnalysis positions are Å.
- `io/resolved.py:parse_chains` returns `None` for `all`; `structure/read.py` matches a chain by `chainID`, or `segid` where the chain column is blank.
- `pipeline/handle.py:Case.load` calls `load_case(path)` and stores `Path(path)`; nothing rebases. Path-bearing fields: `inputs.{mesh,charge,eps_r,profile,pqr}.path` (`SuppliedArtefact`), `structure.source.path`, `structure.ensemble.trajectory`.
- Stage 1 keys files by digest (`structure/stage.py:structure_parameters`), and the solve keys on `solve_provenance`; only `CaseArtefact` (stage 9) and the qoi key carry the path text, so rebasing moves those two hashes.
- `io/case.py`: `CorrectionChoiceSpec.model` defaults to `none`, `StericSpec.model` to `none`; the examples set each to the parameter file's name and `borukhov`. `Electrolyte.from_parameter_file(name)` gives `protein_permittivity`, `membrane_permittivity` and species valences.
- No `surface_charge` exists in the case schema (REV-144). `examples/02-charged-pore/ring.field.yaml` places its ring 0.6 nm behind a 2.0 nm wall in a 6 nm membrane, so the factory keeps the CLI's defaults.
- `core/public.py:PUBLIC` already lists `plan_from_document` and `run_plan`; `modularity-layering.yaml` already has `core → mesh`, `core → structure` (string, MOD-15) and `nanopnp → sweep`.

**D2**
- `sweep/plan.py:build_plan` reads the base from `document.base_path(source)`; `SweepPlan.base_case()` re-reads and re-hashes it for each member; `_check_files` resolves recorded paths against the working directory.
- `sweep/run.py:run_plan(plan, directory, store=, workers=)` writes member records under `directory`; `workers > 1` needs `directory/plan.json` (`write_plan`). `sweep/collect.py:collect(plan, directory)` writes `dataset.json` and returns the `SweepArtefact`.
- `SweepDocument.Axis` takes `name`, `path`, `values`, `origin` (an index). Schema `nanopnp/sweep/v0.5`.

**D3**
- `plot/data.py:DISPLAY["potential"]` is `Display("V", 1.0)`; `plot/figures.py:solve_figure` hard-codes `("potential", …, "V", 1.0, "RdBu_r")` and plots `|u|` on `magma`.
- `geometry/contour.py` writes `summary["constriction"] = {"r_nm", "z_nm"}` on stage 4.
- `plot/data.py:charge_grids` returns `"solid_fraction"` (χ) from the `eps_r` payload; `CorrectionCurves.at_driver_M` holds the operating point.
- `collect` writes `summary["rectification"]` as `{forward, reverse, bias_V, rectification}`, already in the cis-referenced convention; each row's `quantities` holds `conductance_S` and `bias_V`.
- Matplotlib 3.11.1 and marimo 0.25.2 in the lock: `CenteredNorm(vcenter, halfrange)`; `streamplot` accepts the masked arrays `LinearTriInterpolator` returns (checked 28 October 2026).

**D4**
- `post/export.py:P2Nodes` orders points vertices first; `cells` is Triangle_6 with midsides `(0,1), (1,2), (2,0)` at columns 3, 4, 5. `sampled_fields` returns `omega`, `omega_w`, `whole`, `restricted`; keys from `attribute_name`: `phi_V`, `u_m_s` (`(n, 2)`, `(r, z)`), `p_Pa`, `<field>_mol_m3`.
- `plot/data.py:solution_fields` keeps `cells[:, :3]` today; its callers are `solve_figure` and `tests/tier2/test_examples_01_quickstart.py`.
- `pipeline/run.py:RunResult.figure` builds `StageInputs(resolved=, upstream=offered(stage, artefacts, own=False))`; `quantities` is the qoi summary, empty before stage 11. There is no `pipeline → post` or `pipeline → plot` edge.

**D5**
- `mesh_figure` draws size and SICN, shared y. `mesh/generate.py` puts `sizing.debye_target_nm` on a generated mesh; `mesh/sizing.py:case_debye_record(resolved)` returns it for any case.

**D6**
- `tests/tier2/test_notebooks.py` (nightly) copies each notebook and its examples to `tmp_path` and runs the README's `run` tag with `validation/examples.py:run_tagged`, which inherits the environment.
- Under `python notebook.py` an unsubmitted `.form()` has value `None`; `slider(debounce=True)` exists.

### Implementation details

**Item 1.** `src/nanopnp/mesh/cylinder.py`: `write_gated_msh(generated, out) -> tuple[MeshData, QualityReport, dict[str, str]]`, the CLI's block verbatim, and `mesh_cylinder(*, pore_radius_nm=…, membrane_thickness_nm=…, reservoir_radius_nm=…, maxh_nm=…, wall_h_nm=…, out: Path) -> Path`, defaults from `mesh/defaults.py`; `ValueError` when the pore is not narrower than the reservoir. `cli:_mesh` calls them and maps `ValueError` to `parser.error`. `mesh/__init__.py` exports it lazily, as `nanopnp/__init__.py` does (a `TYPE_CHECKING` import and `__getattr__`); the same pattern for `structure`, `sweep` and `plot`.

**Item 2.** `Case.cylinder(*, pore_radius_nm, membrane_thickness_nm, reservoir_radius_nm, concentration_M, bias_V, charge=None, parameters="willems2020_nacl", maxh_nm, wall_h_nm, outputs=("current", "transport_numbers", "eof_rate"), name="cylinder", store=None, write=True)`, the mesh defaults from `mesh/defaults.py`. The mesh path is `<store.root>/meshes/cylinder-<short(content_hash("nanopnp/mesh/cylinder", parameters), 12)>.msh`, written only if absent. `inputs.mesh = {path, format: msh41, groups: {default: interface}}`; `inputs.charge = {path: <absolute>, format: field1}` when given. The document is built as a dict and validated by `loads_case`, never assembled from models by hand. `physics.solid_permittivities = {membrane: <file value>}` for the cylinder, and `{protein, membrane}` for `from_structure(path, *, point_group, chains="all", concentration_M, bias_V, parameters=…, size_scale=1.0, outputs=…, name=None, store=None, write=True)`, which sets `structure.source`, `charge: {}` and `numerics.mesh.size_scale`. A missing store is `Store()`.

**Item 3.** `src/nanopnp/sweep/inmemory.py`: `sweep()`, the `Sweep` dataclass. The hash is `content_hash("nanopnp/sweep/v0.5", {"sweep": <document dict>}, {"base_case": CaseArtefact(document).hash})`. `axis` accepts a leaf name through `pipeline/handle.py:_path_of`.

**Item 6.** `plot/panels.py`: `plot_field(fields, quantity, *, ax=None, zoom_nm=None, relative_to_M=None)`, `plot_mesh(elements, *, ax=None, zoom_nm=None, debye_target_nm=None)`, `plot_axial_cutline(fields, quantity, *, r_nm=0.0, ax=None)`, `plot_radial_cutline(fields, quantity, *, z_nm=0.0, ax=None)`, `plot_iv(artefact, *, ax=None, annotate=True)`; each returns its `Axes` and builds a `Figure` when `ax` is `None`. `quantity` is an attribute key, or `"potential"` (`phi_V`), `"u_z"` (`u_m_s[:, 1]`), `"u_r"`. `data.subdivided(cells) -> (4n, 3)`.

**Items 4, 8 and 12.** The first cell of each notebook:

```python
here = Path(__file__).resolve().parent
store = Store(os.environ.get("NANOPNP_STORE") or here.parent / ".store")
```

`notebooks/.gitignore` holds `.store/`. A slow stage reads its form in a later cell than the one
defining it: `settings = solve_form.value or SOLVE_DEFAULTS`, the defaults a module-level dict in the
form's cell. A slider is `mo.ui.slider(..., debounce=True)`. Cutline and zoom views read
`run.fields` once, in their own cell, so a slider never re-samples the solution. 03 and 05 pass
`charge=(here.parents[1] / "examples" / "02-charged-pore" / "ring.field.yaml")`, 04 the
`03-iv-sweep/cis-ring.field.yaml`, and the CLI's cylinder defaults; nothing is written outside the
store.

**Item 11.** `orient_pore(source, *, chains="all", cis_end, registration_residues=None,
centroid_z_nm=0.0, out) -> Path`; `registration_residues` a `(first, last)` pair, `None` meaning
every selected C-α. MDAnalysis and NumPy are imported in the function; a missing MDAnalysis raises
`core.stages.MissingExtraError` naming `structure`. A degenerate covariance raises `ValueError`
with the eigenvalues, as `prepare.py` does. `structure_file(name)` keeps a bare stem working
(`<stem>.pdb`, the GUI probe's call) and looks in `tests/data/structures/` after `STRUCTURES_DIR`
only when the package runs from a checkout (`_REPO_DATA` exists). `prepare.py` keeps its command
line and calls `orient_pore(..., chains="A,B,C,D,E,F,G,H,I,J,K,L", cis_end="wider",
registration_residues=(8, 292), centroid_z_nm=5.655)`.

**Checkpoints (5, 10, 14).** Load the `artifact-design` skill. For each notebook revised so far:
`NANOPNP_STORE=notebooks/.store uv run marimo export html notebooks/<nn>/notebook.py -o <scratchpad>/wp54-<nn>.html`.
Read the export, publish it with the Artifact tool (same file path each time, so the URL stays;
`icon: "notebook"`), and end the turn with the links, a three-line progress note, the questions for
steering, and `/compact`. At the next turn, read the comments (`ArtifactComments`) and adjust before
the next item; a change of scope is a ruling (`rulings.md`).

### Work items

- [x] c1db2b8 1. `src/nanopnp/mesh/cylinder.py`, `mesh/__init__.py`, `cli/__init__.py` (D1); done when `tests/tier1/test_cli.py` passes. **Executor:** `general-purpose` on Sonnet.
- [x] 3effa2c 2. `pipeline/handle.py` (`cylinder`, `from_structure`, `load` rebasing), `post/export.py` (`SolutionFields` moved, six-node cells), `plot/data.py`, `pipeline/run.py` (`current_nA`, `conductance_nS`, `fields`), `modularity-layering.yaml` (`pipeline → post`) (D1, D4); done when the item's Verification rows and `test_layering.py` pass. **Executor:** main.
- [x] 1d1664d 3. `src/nanopnp/sweep/inmemory.py`, `sweep/__init__.py` (D2); done when its row passes. **Executor:** main.
- [x] 65b049f 4. `notebooks/03-solve`, `notebooks/04-sweep`, their READMEs, `notebooks/.gitignore`, `tests/tier2/test_notebooks.py` (D6, figures as they stand); done when `uv run pytest tests/tier2/test_notebooks.py -k "03 or 04"` passes. **Executor:** main.
- [x] 5. Checkpoint: publish 03, 04. **Executor:** main.

> **Outcome — slice 1 (items 1 to 5).**
> - Item 1 also exports `generate_cylinder`, the ungated mesher, because the CLI prints the
>   gated mesh's report and `mesh_cylinder` returns only the path.
> - Item 2 lands `plot.data.subdivided`, planned for item 6, since the solve figure needs it once
>   the cells are six-node. `field_path` and `input_paths` in `pipeline/handle.py` are public for
>   the sweep. The model name is read from `VALIDATED_DEFAULT_CASE` (VER-56). The cylinder mesh
>   key's schema is `nanopnp/mesh/cylinder/v0.5`.
> - Grounding missed that `Case.run` recorded the case file's path beside the dumped text, so a
>   reproduction of a `Case.load` run failed its case check; with rebasing it always would.
>   `Case.run` now records the case as held in memory (`case_path=None`), and `Case.load`
>   keeps the resolved source. A rebased case hash also depends on where the files live.
> - The physics review found the cylinder's 0.35 nm wall coarser than NUM-30's `λ_D/5`:
>   REV-146, a question for the author.
> - The notebook test compares `git status` before and after each notebook, rather than asking
>   for an empty one, so a dirty development tree does not fail it.
> - V5 pages: the marimo export pulls its styles from a CDN the artifact frame blocks, so each
>   page is rebuilt from the export's embedded cells and outputs, the widgets drawn at their
>   defaults.
- [x] 694fa53 6. `plot/panels.py`, `plot/data.py` (`subdivided`, cutlines), `plot/__init__.py` (D3, D4); done when its rows pass. **Executor:** main.
- [x] 6664262 7. `plot/figures.py` rebuilt on the panels: solve, charge, contour, materials, sweep, mesh (D3, D5); done when `test_figures.py` and `test_every_figure_draws_and_displays` pass. **Executor:** main.
- [x] 87036fd 8. `notebooks/05-cylinder`; 03's cutline slider and field selector (D6); done when the notebook test passes for 03 and 05. **Executor:** main.
- [x] 4ab1443 9. `CHANGELOG.md` entries for items 1 to 8; the strict documentation build of `CLAUDE.md`'s *Commands* passes. **Executor:** `general-purpose` on Haiku.
- [x] 10. Checkpoint: publish 03 to 05. **Executor:** main.
> **Outcome — slice 2 (items 6 to 10).**
> - Steering from checkpoint 1: the author did not want every figure in one panel. Notebooks 03 and
>   05 show each solved field as its own figure, in tabs, and 04 shows the I-V panel on its own with
>   the full sweep figure in an accordion. The stage figures stay one per stage.
> - Item 6 adds `plot_charge` and `mark_constriction` beside the five planned panels, a
>   `relative_to_M` keyword on the cutlines, and `plot.data.field_values`, `sampled` and
>   `LUMEN_NM`; `DISPLAY["potential"]` is mV. The cutline test's floor is relative to the field's
>   size, since a grounded node holds round-off about zero.
> - The physics review of items 6 and 7 found a sweep's I-V panel drew against the recorded bias
>   while its neighbours drew the assigned one, lost a failed point, and joined the groups of a
>   two-axis sweep; fixed in 3f0b588 (`plot.data.cis_referenced_bias_V`). A λ_D/5 bar read from a
>   stored mesh is labelled "as meshed", since a shared mesh records the first member's salt. Not
>   fixed: REV-147 (the lumen window is fixed) and REV-148 (one bulk for every species).
> - The checkpoint pages render marimo's tabs as working tabs; the rest stays static.
- [ ] 11. `src/nanopnp/structure/orient.py`, `structure/__init__.py`, `core/paths.py:structure_file`, `examples/06-pdb-to-mesh/prepare.py` as a wrapper, REV-136's section (D1); done when its row and VER-46 for example 06 pass. **Executor:** main.
- [ ] 12. `notebooks/01-geometry`, `02-charge`, `06-2wcd` on `Case.from_structure` (D6); done when the notebook test passes for all six. **Executor:** main.
- [ ] 13. `core/public.py`, `nanopnp/__init__.py`, `modularity-layering.yaml` (`nanopnp → mesh`, `nanopnp → structure`), `CHANGELOG.md` (D1); done when `test_public_api.py` and `test_layering.py` pass. **Executor:** main.
- [ ] 14. Checkpoint: publish all six. **Executor:** main.

### Verification

| Test (file, tier) | Identifier | Oracle and tolerance |
|---|---|---|
| `test_orient_pore_puts_a_tilted_ring_on_z_with_the_named_end_cis` (`test_structure_axis.py`, 1) | FR-37 | A tilted C₈ ring of C-α, one end wider: axis within 0.5° of z; `cis_end` puts the named end at +z; centroid at `centroid_z_nm` ±1e-3 nm; two calls write identical bytes |
| `test_case_load_rebases_relative_inputs_on_the_case_file` (`test_case_handle.py`, 1) | — | From another working directory, each path is absolute, beside the case |
| `test_in_memory_sweep_matches_the_sweep_file_plan` (`test_sweep_plan.py`, 1) | VER-36 | The plan of `sweep(case, …)` has the base hash and point ids of `plan_from_document` over the same files |
| `test_cutline_matches_the_p2_nodes_on_the_axis` (`test_examples_01_quickstart.py`, 2) | FR-30 | At each P2 node on r = 0, the axial cutline equals the node's value, rel 1e-12; a corner-only triangulation fails at the midsides |
| `test_radial_cutline_is_masked_outside_the_fluid` (`test_figures.py`, 1) | FR-30 | Two hand-built P2 triangles: a linear field exact (1e-12) inside, NaN outside |
| `test_potential_panel_is_millivolts_centred_at_zero` (`test_figures.py`, 1) | FR-30 | φ = 0.02 V everywhere: the colour data reads 20 mV and the norm's `vcenter` is 0, with no exception |
| `test_concentration_panel_is_log_relative_to_bulk` (`test_figures.py`, 1) | FR-30 | c = 2 c_bulk reads log₁₀ 2; c_bulk taken in M instead of mol/m³ is off by 3 |
| `test_run_result_current_and_conductance_in_nano_units` (`test_run.py`, 1) | — | 2e-9 A and 4e-8 S read 2 nA and 40 nS; `None` stays `None`; without stage 11 it raises naming `qoi` |
| `test_notebook_runs_headless` (`test_notebooks.py`, 2, nightly) | FR-30 | In place, order 01 to 06, one module-scoped store (`NANOPNP_STORE` via `pytest.MonkeyPatch.context()`); exit 0; `git status --porcelain notebooks examples` empty |
| `test_layering.py`, `test_backend_guard.py`, `test_public_api.py` (1) | VER-61, VER-65, VER-45 | Kept green; `structure` stays out of the backend set |

### Out of scope

A wall surface charge (REV-144); builders by section (REV-145); a multi-axis sweep from Python;
the `prepare` command (REV-41); the notebooks on the site (documentation increment 4).

### Open questions

None blocking; the In brief's question defaults to the ring fields.
