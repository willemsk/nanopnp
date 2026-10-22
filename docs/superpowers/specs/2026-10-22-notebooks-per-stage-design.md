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
- **Reactivity does the bookkeeping.** Editing a value re-runs that stage's cells and the cells after
  them, never the ones before.
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
   `run_mesh = case_mesh.run(upto="mesh", only=True)`.
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
| region | `geometry.membrane.*`, `geometry.reservoir.*`, `geometry.analyte.*` |
| mesh | `numerics.mesh.*` (`backend`, `size_scale`, `wall_h_nm`, `boundary_layer`) |
| protonation | `charge.ph`, `charge.forcefield`, `charge.titration` |
| charge | `charge.smearing.*`, `charge.exclusion_offset_nm`, `charge.dielectric_transition_nm`, `physics.solid_permittivities` |
| materials | `electrolyte.*` (concentration, temperature, driver, corrections) |
| solve | `boundary_conditions.*`, `physics.*`, `numerics.nonlinear.*`, `continuation`, `stabilisation`, `elements`, `linear` |
| qoi | `outputs` |

The rule for the curated list: a scalar or an enumerated choice a user could reasonably vary; never an
identity or provenance field (`schema`, `name`, file paths) and never a field that needs another
artefact to make sense. The builder checks each against the schema.

Three things are outside the case and get a cell of the same shape:

- **How the cylinder mesh is built** (notebooks 03 and 05): the `nanopnp mesh cylinder` arguments, such
  as `--maxh-nm`, are plain values in the mesh block; the block then points `inputs.mesh.path` at the
  result. This is the author's "how it was built".
- **Structure preparation** (01, 02 and 06): the values `prepare.py` takes, in the structure block.
- **The sweep** (04 and 05): an `axes` dict of path, values and origin, written out as the sweep
  document, then run and collected. The sweep values are edited as numbers like everything else.

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

A notebook that starts mid-pipeline (02, 03, 04) opens with one **setup cell**, labelled as such, that
runs the upstream stages with a plain `run(upto=…)`; its blocks then use `only=True`. Without it, the
first `only=True` cell would find an empty store.

## My calls (the author may overrule any of them)

- All six notebooks are restructured, so 01 to 04 are slices of what 05 and 06 show whole. I did not
  merge them: the area notebooks stay the short route to one part of the pipeline.
- Plain values are literals equal to the example's, not reads from the case, so the file shows what the
  run uses. A wrong path fails loudly through `Case` (`UnknownCasePathError`); a value equal to the
  default records no deviation.
- With no Run button, **opening 06 for the first time runs its whole walk, about eleven minutes**; later
  opens read the store. A user who wants a gate can set marimo's lazy runtime. Not designed here.
- The notebooks' READMEs, the WP51 plan's D5 and Outcome, `CHANGELOG.md` and a ruling in §8.2.14 are
  updated in the same commits: P5's "figures and widgets" becomes "a block of cells per stage".

## To verify first

- That `run(upto=stage, only=True)` takes every stage before it from the store in the order the
  notebooks run, including a branch (protonation reads only the structure) and the stage after the
  mesh. The code in `pipeline/run.py` says so; the first step of the plan proves it on 02 and 06.
- That each curated setting moves exactly its stage's hash and the hashes after it.

## Left to the builder

The exact curated settings per stage, the wording of the descriptions, the helper (if any) that formats
a stage's record and summary, and the order in which the six notebooks are converted. 05 first is
sensible: it is fast and covers a sweep.
