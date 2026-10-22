# The notebooks, one block of cells per stage

Design of 22 October 2026, from the author's review of the WP51 notebooks (PR #119). Nothing here is
built yet. It amends `SPECIFICATION.md` §8.2.14 P5 and the WP51 plan's D5.

## Intent

A notebook should teach the pipeline: **the stages and the steps between them**, with every setting a
user could reasonably want to adjust in front of them. Today a notebook is one `case.run(upto=…)` call and
a stage dropdown, so the stages are hidden behind the call. The author wants each stage to have its own
cell or cells, where they can read what the stage takes in, change its settings, run it and see what
came out.

## Goals

- **One block of cells per stage**, in pipeline order, in each of the six notebooks.
- **Every reasonable setting of a stage is in its block**, as a plain value the user edits in the code.
  The author's examples: for the mesh, its coarseness and how it was built; for protonation, the pH and
  the force field; for the sweep, the sweep values.
- **Strictness.** A stage's cell runs that stage alone and takes everything upstream from the store; it
  never silently recomputes an earlier stage.
- **Reactivity does the bookkeeping.** Running an edited settings cell re-runs the cells after it (marimo's
  default `autorun`), never the ones before; marimo does not re-run a cell the moment its text changes.
- A headless run still solves the example's own case: the values are the example's values.

## Non-goals and anti-goals

- **No widgets.** The stage dropdown, the bias and salt sliders, the Run button, the figure-size slider
  and the zoom switch go. The author's words: the focus is the stages and the steps, "not building a
  semi-GUI". Widgets "can come later" and are not designed here.
- **No library re-implementation.** A cell calls the public API (`nanopnp.Case`); it does not rebuild a
  stage's typed inputs by hand (the rejected option 3 below).
- Not a failure if a notebook reads long. A notebook that is compact but hides the stages is the failure.

## Constraints

- marimo forbids one name defined in two cells, so a stage's case is a new name, not a reassignment.
- Each notebook runs headless in the nightly (`test_notebook_runs_headless`), the exit status being the
  oracle. Total nightly time stays close to today's (06 takes about 11 minutes, 05 under a minute).
- A stage reads its settings from the case, so a setting only moves the hashes of the stages that read
  it. Cells are ordered so that this matches the pipeline.
- `Case` (§8.2.14 P8) is the only editing interface. No new public name is planned.

## Approaches

1. **A chain of `Case` objects and one `run(upto=stage)` per stage.** Each stage re-runs upstream
   cached.
2. **The same, with `only=True`.** Each cell computes its own stage and refuses to recompute an earlier
   one, naming it if the store lacks it (`MissingUpstreamError`). **The author's choice.**
3. **Call each stage's own function with typed inputs**, as `nanopnp stage <name>` does. Rejected: each
   notebook would rebuild the pipeline's input assembly by hand and bypass the walk's cache and manifest.

## The stage block

Four cells per stage, in this order:

1. **Description.** A heading and a sentence on what the stage does, then its inputs, the artefact it
   emits and its schema, read from the stage registry (`registered_stages()`), so the notebook cannot
   disagree with the code (FR-27).
2. **Settings.** A dict of dotted case paths to plain values, one line each, a short comment on what it
   changes. It lists every setting the stage reads that a user would reasonably adjust, each at the
   example's value. A leaf name is allowed only where unique (P8); the block uses dotted paths, so the
   field named is the field changed.
3. **Run.** `case_mesh = case_region.with_(**mesh_settings)`, then
   `run_mesh = case_mesh.run(upto="mesh", only=True)`, both in one cell, and the cell names the previous
   block's `run_region`, so marimo's dependency order cannot run it before the stage it needs is stored.
4. **Show.** The stage's record (short hash, recomputed or cached), the artefact's summary and
   `run_mesh.figure("mesh", scale=scale)`.

The chain's names are `case_<stage>` and `run_<stage>`. A single display cell at the top holds
`scale = 1.5` and `interactive = False`, plain values, in place of the slider and the switch. The
figure cell uses `mo.mpl.interactive` when `interactive` is true.

### Where a stage's settings come from

Every setting named so far is a field of the case schema, which is already grouped by the stage that
reads it:

| Stage | Case fields (curated by the builder) |
|---|---|
| structure | `structure.source.*` (chains, selection, variant), `structure.ensemble.*`, `structure.symmetry.*` |
| density | `geometry.density.*` |
| symmetry | `structure.symmetry.point_group`, `axis` |
| contour | `geometry.contour.*` |
| region | `geometry.membrane.*`, `geometry.reservoir.*`, `geometry.analyte.*`, `charge.exclusion_offset_nm` (it moves the region's key) |
| mesh | `numerics.mesh.*` (`backend`, `size_scale`, `wall_h_nm`, `wall_for_concentration_M`, `boundary_layer`) |
| protonation | `charge.ph`, `charge.forcefield`, `charge.titration` |
| charge | `charge.smearing.*`, `charge.dielectric_transition_nm`, `physics.solid_permittivities` |
| materials | `electrolyte.*` (concentration, temperature, driver, corrections) |
| solve | `boundary_conditions.*`, `physics.*`, `numerics.nonlinear.*`, `continuation`, `stabilisation`, `elements`, `linear` |
| qoi | `outputs` |

The rule for placing a setting: it lives in the block of the **earliest stage whose hash it moves**, or an
`only=True` cell would find an earlier stage missing. Two cases need care. `charge.exclusion_offset_nm` moves the
region's key, so it is in the region block. And for a *generated* mesh (06) the Debye length sizes the wall, so the
salt moves the mesh key above 1.474 M (see *The mesh and the salt*), measured: 0.3 M moves materials and solve, 2.0 M
moves the mesh as well. The temperature would too, but the shipped parameter set refuses any other than 298.15 K, so it is
not a notebook setting. The spike checked each setting by moving it (*What the spike found*).

The rule for the curated list: a scalar or an enumerated choice a user could reasonably vary; never an
identity or provenance field (`schema`, `name`, file paths) and never a field that needs another
artefact to make sense. The builder checks each against the schema.

Three things are outside the case and get a cell of the same shape:

- **How the cylinder mesh is built** (notebooks 03 and 05): the `nanopnp mesh cylinder` arguments, such
  as `--maxh-nm`, are plain values in the mesh block; the block names the file by its arguments, so an
  edited value cannot silently reuse an old `pore.msh`, and points `inputs.mesh.path` at the result. This is the author's "how it was built".
- **Structure preparation** (01, 02 and 06): the values `prepare.py` takes, in the structure block.
- **The sweep** (04 and 05): an `axes` dict of path, values and origin, written out as the sweep
  document, then run and collected. The sweep's `base` is the edited case, written into the example's own
  directory (the base is re-read from disk, and its relative mesh and charge paths resolve there), and the plan
  is rebuilt when it changes. A sweep computes its own members; the engine has no `only`. The sweep values are edited as numbers like everything else.

## The mesh and the salt

`wall_h_nm: auto` is `size_scale × min(0.05 nm, λ_D/5)`, and the 0.05 nm ceiling governs up to 1.474 M, so
salts below that already share one mesh (VER-53). The author chose to make the design point explicit anyway:
a new field `numerics.mesh.wall_for_concentration_M` takes λ_D at that concentration instead of the run's
own. Every salt at or above it reuses the one mesh; above it the wall is coarser than λ_D/5, which the manifest
records as it does today (logged, not refused). The field is refused beside an explicit `wall_h_nm` and beside a
supplied `inputs.mesh`, where it would move nothing (§5.3.1). It is its own commit, before the notebooks.

## Which notebooks

All six take the pattern; the author's examples run through them.

| Notebook | Blocks |
|---|---|
| 01-geometry | structure, density, symmetry, contour, region, mesh |
| 02-charge | protonation, charge, materials |
| 03-solve | solve, qoi (the mesh, charge and materials stages are the setup cell) |
| 04-sweep | the sweep |
| 05-cylinder | mesh, charge, materials, solve, qoi, sweep |
| 06-2wcd | structure through qoi, eleven blocks |

A notebook that starts mid-pipeline (02, 03) opens with one **setup cell**, labelled as such, that
runs the upstream stages with a plain `run(upto=…)`; its blocks then use `only=True`. Without it, the
first `only=True` cell would find an empty store.

## My calls (the author may overrule any of them)

- All six notebooks are restructured, so 01 to 04 are slices of what 05 and 06 show whole. I did not
  merge them: the area notebooks stay the short route to one part of the pipeline.
- Plain values are literals equal to the example's, not reads from the case, so the file shows what the
  run uses. A wrong path fails loudly through `Case` (`UnknownCasePathError`); a value equal to the
  default records no deviation.
- With no Run button, `python 06-2wcd/notebook.py` and `marimo run` walk all eleven stages the first time, about
  eleven minutes. `marimo edit` does not run the cells on open in marimo's default configuration (`auto_instantiate`
  is off), so the user starts the walk there; later runs read the store.
- The notebooks' READMEs, the WP51 plan's D5 and Outcome, `CHANGELOG.md` and a ruling in §8.2.14 are
  updated in the same commits: P5's "figures and widgets" becomes "a block of cells per stage".

## To verify first

- That `run(upto=stage, only=True)` takes every stage before it from the store in the order the
  notebooks run, including a branch (protonation reads only the structure) and the stage after the
  mesh. The code in `pipeline/run.py` says so; the first step of the plan proves it on 02 and 06.
- That each curated setting moves exactly its stage's hash and the hashes after it.

## What the spike found

Run on 2WCD (example 07's case) from an empty store, 22 October 2026 (WP51 item 10; the scripts were thrown away).

- **The order holds.** `run(upto=stage, only=True)` for the eleven stages in notebook order computes the target and
  takes every other stage of its closure from the store, including the branch (`protonation` walks `case`, `structure`,
  `protonation`) and the stages after the mesh. A second pass finds every target cached. An empty store refuses the first
  call naming `structure`. The `case` and `materials` stages are their own keys, so a first run reports them
  computed; the show cell does not read that as a recompute. The solve took 401 s on the 4x coarse mesh and the walk
  about eleven minutes.
- **Each setting moves its stage first.** Moving a setting and keying every stage on the stored upstream:
  `structure.symmetry.point_group` → structure; `geometry.density.*` → density (the grid spacing also moves symmetry and
  contour, which read the grid); `geometry.contour.*` → contour; `geometry.membrane.*`, `geometry.reservoir.*` and
  `charge.exclusion_offset_nm` → region (`membrane.centre_z_nm` also moves the charge deposit); `numerics.mesh.*` → mesh;
  `charge.ph`, `charge.forcefield` → protonation; `charge.smearing.*`, `charge.dielectric_transition_nm` → charge;
  `electrolyte.concentration_M` → materials, then solve, and the mesh too at 2.0 M; `boundary_conditions.bias_V`,
  `numerics.stabilisation`, `numerics.wall_distance.*` → solve; `outputs` → qoi.
- **A geometry setting needs a `geometry:` block in the case.** `Case.with_` refuses to add a section from defaults
  (`with_section` allows only `charge`), and no shipped case carries `geometry:`. A block spelled at the defaults
  (`geometry: {}`) moves no stage key, so the example case for 06 (and 01 if it needs it) spells the block out; the edit
  goes in the same commit as the notebook.
- **Two curated lists are shorter than the table says.** `electrolyte.temperature_K` is refused (the parameters are
  fitted at 298.15 K), and `physics.inertia` and its siblings are refused, because the NUM-18 ladder fixes the path.
  The solve block lists `bias_V`, `stabilisation` and `wall_distance` and not the `physics` switches.
- **Reactivity costs a re-solve.** Running an edited early block autoruns every later block, the solve included.
  Marimo's `on_cell_change = "lazy"` marks them stale instead; `pyproject.toml` can set it for the project
  (`[tool.marimo.runtime]`), and headless runs are unaffected. Item 14 sets it and checks it in `marimo edit`.

## Left to the builder

The exact curated settings per stage, the wording of the descriptions, the helper (if any) that formats
a stage's record and summary, and the order in which the six notebooks are converted. 05 first is
sensible: it is fast and covers a sweep.
