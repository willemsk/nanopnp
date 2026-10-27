# Workbench design

The design of the browser workbench that replaces the Qt desktop shell in v0.6 (Phase 5,
§8.2.17 S1 to S24), written by the WP5.01 design study: today's shell critiqued, a design round with
the author on the organisation and the look and feel, the areas drawn as choice panels and then as two
whole workbenches, and the requirements. Each ruling is a `WB-nn` row of the *Decision log*, in the
author's words. The pictures it rests on are kept beside it and are not part of the site:
the concept boards in `docs/design/concepts/`, the style tile in `docs/design/style/`, the choice
panels in `docs/design/choices/`, the whole-workbench mockups in `docs/design/mockups/` (A, the one
chosen, in `a/`), the scripts that write them in `docs/design/generators/`, and each round's verdicts
and review in `docs/design/reviews/`. The tokens are `docs/design/tokens.css`.

## Purpose and users

The workbench is the one graphical program of nanopnp: in the author's words "a fully fledged
workbench", "the perfect merge of PyMol and COMSOL" (S2), in which every part of the work, from the
molecule to the conductance, is built, inspected and changed beside a live picture of it. It is a thin
shell: the physics, the numbers and every check live in the library and reach the shell as
artefacts (QR-13; RSK-15), and no screen is built for a capability Tiers 1 and 2 do not verify.

It serves the three personas of §2 at once, one interface with no separate modes (WB-08):

| Persona | What they come for | What the workbench gives them |
|---|---|---|
| P1, method developers | A scriptable API, sweeps, changing the physics, full introspection | Every stage's artefact opened from the tool that built it; a project folder of plain files their scripts and notebooks read (S11); sweeps over any value (REV-139); the physics composer and a Python console in later phases (S3; WB-10); the compact density (WB-18) |
| P2, collaborating computational scientists | Case files the command line runs, reproducible cases, sensible defaults | Each run writes its resolved case file with its manifest, which `nanopnp run` runs as it is (FR-25; WB-11); every value away from its default marked and counted (WB-28; WB-03) |
| P3, experimental nanopore laboratories | No Python: select a PDB, set salt and voltage, obtain a prediction and a picture | One install command and `nanopnp gui` (S12); the guided route from a structure to a conductance (QR-10; WB-08); plain text, a refusal that says what to type, and a glossary (WB-25) |

## Today's shell

The Qt shell of v0.5 (`nanopnp-gui <case> [--store <dir>]`; IF-09) is one window of seven tabs over
one case file: *Case*, *Geometry*, *Charge*, *Run*, *Convergence*, *Result* and *Fields*. The study
pictured each tab and each of its views on example 07 (`2wcd.case.yaml`, 2WCD with its charge
deposited) by `/np-gui render qt`: 22 pictures in four states (opened, a refused field, after
*Build charge*, after *Run*), and the three 3D views pictured apart in a browser.

### The capability list

One row per control or view that does something. Before the Qt shell leaves, the browser shell
offers each row, or the author has ruled it dropped (§8.2.17 S13). The *Source* column names the
widget in `src/nanopnp/gui/widgets/` at the commit this list was taken from.

| # | Tab | Control or view | What it does | Source |
|---|---|---|---|---|
| Q01 | Window | Command line `nanopnp-gui <case> [--store <dir>]` | Opens one case file for editing, over a chosen artefact store; a case that does not validate is refused with its exit code | `app.py:main` |
| Q02 | Window | Window title | Names the open case file | `app.py:MainWindow` |
| Q03 | Window | Status bar | Says what was last started (a build, a run) or why it was refused | `app.py:MainWindow` |
| Q04 | Window | Closing the window | Stops the Geometry and Charge builds and their child processes | `app.py:MainWindow.closeEvent` |
| Q05 | Case | One typed field per case path | Edits every field of the case schema: a check box for a flag, a list for a choice, a multiple selection, a whole or real number box with its bounds, or text read as YAML; a field whose section is absent is disabled with a tooltip saying why | `case_editor.py:CaseEditorWidget` |
| Q06 | Case | Per-field staging | Checks each edit against its field as it is typed; a refused field's label turns red and the status line says why | `case_editor.py:_setter` |
| Q07 | Case | *Add section: <name>* buttons | Writes an empty optional section, which resolves as its absence, so its fields can be edited | `case_editor.py:add_section` |
| Q08 | Case | Commit and save | Validates the whole case and writes the case file before each build and run; a refused case stops there with each problem listed in the status line | `case_editor.py:commit`, `app.py:_saved_case` |
| Q09 | Geometry | *Load structure…* | Picks a PDB, mmCIF or PQR file and stages it as the case's structure | `geometry.py:_pick_structure` |
| Q10 | Geometry | *Build geometry* | Walks the saved case through stages 1 to 6 in a child process; offered only for a case whose stages 5 and 6 build its mesh | `geometry.py:build` |
| Q11 | Geometry | *Cancel* | Cancels the build | `geometry.py:_stop` |
| Q12 | Geometry | Stage list | One row per planned stage with its status and stored hash, updated as the walk lands; selecting a row shows that stage | `geometry.py:_show_rows` |
| Q13 | Geometry | Stage 1 summary | The alignment record: point group, axis, chain order, the angle, orientation and spacing gates with their measured values, frames | `geometry.py:_show_row` |
| Q14 | Geometry | Stage 2 picture | The density section at y = 0 in the stage-1 frame, with the membrane slab and the grid record | `geometry.py:GeometryCanvas.show_image` |
| Q15 | Geometry | Stage 3 picture and quantity list | The (r, z) map, choosing *mean*, *cn_variance* or *raw_variance* | `geometry.py:_requantity` |
| Q16 | Geometry | Stage 4 contour editor | The extracted contour over the mean map, edited by hand: drag a vertex, double-click an edge to insert one, Delete or *Delete vertex* to remove one (never below three) | `geometry.py:GeometryCanvas` |
| Q17 | Geometry | *Undo*, *Redo* | Steps through the contour edits | `geometry.py:_step_back`, `_step_forward` |
| Q18 | Geometry | *Measure criteria* | Measures the §5.2.1 contour criteria on the edit against the stored stages, in a child process, and marks where the first failed criterion sits | `geometry.py:measure` |
| Q19 | Geometry | *Seed from refusal* | Recomputes a refused contour from the stored stage-3 map so it can be edited | `geometry.py:seed` |
| Q20 | Geometry | *Save edit* | Writes the edited profile and a derived case that uses it; the original case is unchanged | `geometry.py:_save_edit` |
| Q21 | Geometry | Stage 5 picture | The region: the model-frame profile, the membrane slab and chord, with the assembly record | `geometry.py:GeometryCanvas.show_outline` |
| Q22 | Geometry | Stage 6 mesh view | The mesh in 3D (WebGL), with the element count, the materials, the worst SICN and gamma and where they sit, and the wall-size gate | `geometry.py:_mesh_lines` |
| Q23 | Geometry | Details pane and status line | The selected stage's record as text; what the build is doing or why it stopped | `geometry.py` |
| Q24 | Charge | *Build charge* | Walks the saved case through stage 7 on the Geometry tab's walk; declined, with its reason, for a case that deposits no charge | `charge.py`, `app.py:build_charge` |
| Q25 | Charge | *Cancel* | Cancels the build | `charge.py:_control_cancel` |
| Q26 | Charge | Stage list | Stage 7's protonation and charge assembly, with status and hash | `charge.py` |
| Q27 | Charge | *Protonation* pane | Per titratable group: chain, residue, applied and expected charge, pKa, unapplied; a frame list with each frame's net charge; the PDB2PQR and PROPKA record and warnings | `charge.py:_show_frame` |
| Q28 | Charge | *Charge map* pane | The areal charge density in (r, z), diverging about zero, with the worst planes of the lattice and mesh legs marked | `charge.py:ChargeCanvas` |
| Q29 | Charge | *Deployed field* pane | The deployed charge or χ on the mesh in 3D (WebGL), with the colour range, the materials and the dielectric's source | `charge.py:_draw` |
| Q30 | Charge | *Conservation* pane | The conservation legs (producer, consumer, quadrature, worst planes) against their tolerances, and the solid-share record | `charge.py` |
| Q31 | Run | *Run* | Commits and saves the case, then solves it in a child process | `run_control.py`, `app.py:start_run` |
| Q32 | Run | *Cancel* | Cancels the run | `run_control.py:_stop` |
| Q33 | Run | Progress bar and stage line | The stage reached, of the walk's stages | `run_control.py` |
| Q34 | Run | Log | Each stage's events and each Newton iteration's residual, as they arrive | `run_control.py` |
| Q35 | Convergence | Live plot | Residual and relative update per Newton step on a log scale, banded by continuation rung, redrawn every 250 ms | `convergence.py:ConvergencePlot` |
| Q36 | Convergence | Summary and rung notes | Rungs and steps; per rung, the test that ended it, the last value against its tolerance, and the smallest damping | `convergence.py:ConvergenceWidget` |
| Q37 | Result | Run directory | Where the run's artefacts are stored | `result.py` |
| Q38 | Result | Quantities of interest | Every scalar quantity the run extracted | `result.py:show_outcome` |
| Q39 | Result | Deviations from the validated default | Every switch set away from the validated default, or that there is none (FR-25) | `result.py:_render_deviations` |
| Q40 | Fields | Field list | Chooses one field of the finished run to draw | `viewer.py:_reselect` |
| Q41 | Fields | Field view | The chosen field on the mesh in 3D (WebGL), with a colour bar; the renderer's own controls; a diagnostic in place of the view when it does not draw | `viewer.py:ViewerWidget` |

Two views are absent from the list because the shell lacks them: the structure itself (stage 1
shows its record but no picture of the molecule) and any reading of a field at a point or along a
line.

### The critique

The GUI reviewer read the 22 pictures and the three browser pictures against QR-10's guided run,
Nielsen's heuristics and WCAG 2.2 AA: 50 findings, two of them blocking the run. The Result tab
prints each number as the store's float wrapper, so the current cannot be read (REV-134), and the
field view opens on the whole 250 nm domain, where the pore is two pixels wide. Across the shell,
stage records and gates are shown as raw dictionaries without a verdict, pictures carry no colour
bar or unit, and the status bar keeps "running" after a run ends.

### The author's verdicts

The author marked 20 of the 22 screens *change* and 2 *keep* (the Run tab and the refusal), and
dropped none, so every row of the capability list stays; the notes move rows, they remove none. The
record, screen by screen and with each disposition, is
`docs/design/reviews/2026-10-25-qt-shell.md`. In the author's words, the case editor "should not be
the first point of entry" and may stay "as an 'overview' feature"; there should be "3 more
independent major parts of the workbench: 1) molecular, 2) continuum, 3) analysis, each with their
own sub-tasks and tools"; stages 1 to 5 "should be part of a protein geometry tool in the geometry
suite"; protonation "should be moved before building the geometry"; convergence merges into a run
suite; and the result and field views become "a fully fledged results explorer and plotter suite",
with zooming, colour scales and the mesh on or off, "much like how COMSOL handles this today". One
note raises a physics question, whether the density should see the protonation chosen later
(REV-135): ruled yes, protonation moving before the geometry stages in the pipeline as well (§8.2.19 U2).

## The areas

The author named the workbench's areas, the list left open (S24): "Molecular viewer/editor, geometry
builder, mesh builder, physics assigner, results analyser, ...". The design round placed them in four
suites (WB-01, WB-02, WB-29). Each area offers at v0.6 what the library verifies; its later parts carry a
later-phase banner and no working control (S7).

| Area | Suite | Its tools | What it draws on at v0.6 | Later |
|---|---|---|---|---|
| Molecular viewer and editor | Molecular | Prepare structure, Ensemble, Protonation, Charge edit, View | The structure, its frames, ensemble and symmetry; stage 7's protonation and PQR; structure preparation, a Phase 5 library capability (WB-14) | The structural mutator (S4) |
| Geometry builder | Continuum | Protein geometry, Contour, Region | Stages 2 to 5: the density, the reduction to (r, z), the contour and its hand edit (`inputs.profile`), the membrane and the reservoir | The sketcher (S5) |
| Mesh builder | Continuum | Mesh: sizes, quality | Stage 6 and its quality report; the size scale and the per-part sizes | Refinement regions drawn by hand; boundary layers |
| Physics assigner | Continuum | Physics defaults: boundaries, model and electrolyte | The registered models, the electrolyte and its corrections, the boundary conditions and walls, as the continuum model's defaults (WB-16) | The composer (S3) |
| (added by the round) | Study | Overview, Study setup, Sweep, Charge on the mesh, Runs | A study pairing a molecular and a continuum model, its overrides and sweep, stage 7's charge on the mesh, and its runs | Sweeps over variables (REV-139) |
| Results analyser | Analysis | Results explorer, Comparison | The run record, the quantities of interest, the fields, the sweeps | Figure, field and case export (FR-28, v0.7) |

## Organisation

**The principle** is "suites in a project" (WB-01): the project folder and its run queue are the frame,
and the four suites, *Molecular*, *Continuum*, *Study* and *Analysis*, sit inside it (WB-02, WB-29). A suite
builds one kind of thing: Molecular a **molecular model** (the prepared structure, its ensemble and
protonation), Continuum a **continuum model** (the protein geometry, the region, the mesh and the physics
defaults), Study a **study** that pairs one of each and runs it, Analysis the results and their comparisons
(WB-11). Models are items of the project's library, so one molecular model serves many continuum runs
without being rebuilt.

**The frame**, from the mockups (`docs/design/mockups/a/`):

- the *title bar*: the menus, the project's name, the changed-from-default count and the command palette
  (WB-09, WB-28);
- the *activity bar* on the left: the four suites, each an icon with its name;
- the *project rail*: the open item, then the library, the studies and the comparisons, folding to the open
  item and unfolding to the project tree;
- in each suite, the *tool list*, then the selected tool's *settings*, docked on the left of its *live view*
  (WB-05, WB-07). Every tool docks its settings the same way: in the author's words, marking the mockups,
  "Consistency is key here!";
- the *bottom panel*: the run queue and the log, folded to one line, unfolding to a run's convergence
  (WB-02; RE2); the Python console a later phase (WB-10).

**Always on screen** (WB-03): the project rail, at least folded; the changed count, opening the list of
every value changed from its default and every study override, grouped by model (WB-28; FR6); and the
queue's status line. The list stays open to additions as the design grows.

**State is never hidden** (WB-32): every setting of a tool is on its pane, none in a sub-menu; a setting
is guarded against being changed by accident, the means left to the shell's package; and every value away
from its default carries its mark.

**Several items are open at once** (WB-04); a variant is derived from its parent and shown as its
difference, and a comparison is a saved project item. **A refusal** shows at its field and in the problems
list, naming the rule, the value, the case path and a remedy (WB-12, WB-25). **The layout** is a designed
default per suite, resized and folded by the user, saved in the project file, with *Reset layout* (WB-13).

## Look and feel

**The direction** borrows each suite's idiom from the tools the author named and harmonises them in one
token set (WB-17): ChimeraX's 3D view in Molecular, COMSOL's and AutoCAD's tree and graphics in
Continuum, COMSOL's plot settings in Analysis, VS Code's palette and quiet chrome for the frame. The tokens
start from the style tile's *molecular* direction, with *instrument*'s dark theme (WB-27).

**The tokens** are `docs/design/tokens.css`, CSS custom properties on `:root`, redefined for the dark
theme: surfaces, text, one accent, the semantic colours, the canvases, the colour maps, the type scale, the
density, focus and motion. They are the default theme: a user adjusts it or chooses another (its colours,
density, spacing and the 3D view's background), saved per user, every theme held to the same
accessibility target (WB-30, WB-31). In short, the default:

- medium density by default, 13.5 px type and 30 px rows, and a compact setting of 12.5 px and 26 px, saved
  per user; the gaps and padding tight at both (WB-18, WB-31);
- light and dark, following the operating system, with a switch (WB-19);
- one accent for selection, the primary action and focus; built, stale and refused in green, amber and red,
  each with a glyph and a word (WB-20); a changed value's own mark, a filled diamond, and a study's
  override an outlined one (WB-28);
- viridis (cividis for colour-vision deficiency) and a diverging map centred on zero by default, charge
  always diverging (VER-60), any Matplotlib map per plot, recorded with it (WB-20);
- Inter, numbers in tabular figures, a narrow no-break space before an SI unit with an engineering prefix
  (WB-21); icons with text, or alone with a tooltip in dense toolbars (WB-22); motion functional only,
  under 200 ms (WB-23);
- the Molecular 3D view near-black by default, a user setting (WB-26, WB-30); (r, z) views and plots on the
  theme, exported on white; every colour bar outlined at 3:1 (WB-26).

**The accessibility target** is WCAG 2.2 AA with full keyboard operation (WB-24): text at 4.5:1, controls,
focus rings and colour bars at 3:1, targets of at least 24 × 24 px, a keyboard path for every canvas action
(a residue picked from a list as on the canvas), reduced motion honoured. The render check measures text
contrast and targets; non-text contrast is REV-138.

## Tabs or areas

S2 asked for "distinct tabs for each part of the workflow"; the round answered with suites (WB-01), and
§8.1's Phase 5 row says so. Today's seven tabs, one per stage, retire with Qt. Every row of the capability
list has a place in the workbench before Qt leaves (S13):

| Rows | Today's tab | In the workbench |
|---|---|---|
| Q01 to Q04 | Window | `nanopnp gui [<project>]` opens the project; the title bar names it; the queue and the problems list say what runs and what was refused; closing stops the builds and their child processes |
| Q05 to Q08 | Case | Each field in the tool that sets it, checked as it is typed and refused at the field (WB-12); the study's *Overview* shows the resolved case file; a section is added by the tool that uses it; a build or run validates and writes the case first |
| Q09 | Geometry | *Open structure…* in Molecular, Prepare structure |
| Q10 to Q12, Q23 | Geometry | Each Continuum tool's *Build*, queued; the tool list's status per tool; *Cancel* in the queue; a tool's record under its *Checks*, the log in the bottom panel |
| Q13 | Geometry | Prepare structure's orientation gate and its checks |
| Q14, Q15 | Geometry | Protein geometry's layers: the density map and the azimuthal variance |
| Q16 to Q20 | Geometry | The Contour tool: drag, insert and delete vertices, *Undo*, *Redo*, *Measure criteria*, *Seed from refusal*, *Save edit…* |
| Q21 | Geometry | The Region tool |
| Q22 | Geometry | Mesh, sizes and quality: the element count, the quality gate, the worst elements located |
| Q24 to Q26, Q30 | Charge | The study's *Charge on the mesh*, queued by *Run study*, with its conservation checks |
| Q27 | Charge | Molecular, Protonation, its residue states, Q<sub>net</sub> and the PROPKA warnings |
| Q28, Q29 | Charge | Charge on the mesh: the deployed density in (r, z) beside the molecule, linked (S6) |
| Q31 to Q34 | Run | *Run study*; *Cancel* in the queue; the queue's "rung x of N" (WB-23); the log |
| Q35, Q36 | Convergence | A run unfolded in the queue: the convergence plot and the rung table |
| Q37, Q38 | Result | The results explorer: the run's item in the project, its quantities tile |
| Q39 | Result | The changed count and its list; the run's manifest |
| Q40, Q41 | Fields | The results explorer's field tile, with its quantity, its colour map and the renderer's diagnostic in place of a view that does not draw |

## Tools

Each tool has its settings and its live view (S6). The mockup screen named is in `docs/design/mockups/a/`.

| Suite | Tool | Settings | Live view | Screen |
|---|---|---|---|---|
| Molecular | Prepare structure | The structure file, the chains, the axis tilt (estimated or typed), the flip, the membrane's centre; the orientation gate; *Save prepared structure* | 3D: the axis and the membrane slab, dragged by their handles | `m-prepare` |
| Molecular | Ensemble | The source (a trajectory or the structure alone), the stride, the frames used with their Q<sub>net</sub> | 3D, one frame or the frames overlaid | `m-ensemble` |
| Molecular | Protonation | The pH, the force field, the titration; *Build molecular model*; the residue states | 3D and the residue strip, each residue with its sign | `m-protonation` |
| Molecular | Charge edit | A residue's protonation state, charge or radius, on every chain, saved as a variant (§8.2.19 U6) | 3D, the residue picked or chosen from a list | `m-charge` |
| Molecular | View | The representation, the colouring, the background, the slab, the clip; a residue list | 3D, with the charge's diverging bar | `m-view` |
| Continuum | Protein geometry | Stages 2 to 4: the grid and kernel, the point group, the isolevel; *Build geometry* | (r, z): the density, the variance, the contour and the probe-radius profile as layers | `g-geometry` |
| Continuum | Contour | The isolevel, the smoothing, the simplification; the vertices; the gate | (r, z) editor over the map; the radius against z | `g-contour` |
| Continuum | Region | The membrane's thickness, the reservoir's radius; its centre read from Prepare | (r, z), each value typed on the drawing as in the pane | `g-region` |
| Continuum | Mesh | The mesher, the elements, the size scale and the per-part sizes; *Build mesh* and its quality gate | (r, z) mesh; by quality, the histogram selecting the elements it outlines | `s-size`, `s-quality` |
| Continuum | Physics defaults | Each boundary's condition; the model, the salt, the ions, the corrections and the permittivities | (r, z), a boundary picked in the view or the list | `p-boundaries`, `p-electrolyte` |
| Study | Overview | The two models, the sweep, the overrides, the changed values, the runs, the physics run | The resolved case file | `st-overview` |
| Study | Study setup | The models, the overrides, the outputs; *Run study* | A form, or the same study as a graph (RE1) | `st-form`, `st-graph` |
| Study | Sweep | The parameters, each with what it rebuilds; variables | The runs as a matrix, each cell a run | `st-sweep` |
| Study | Charge on the mesh | The pair of models | 3D and (r, z) side by side, linked; the conservation checks | `st-charge` |
| Study | Runs | Cancel, the log | A run unfolded in the queue, wherever the user is (RE2) | `st-runs` |
| Analysis | Results explorer | The run, the bias, the tiles; each tile's quantity and map | Tiles: a field, the I–V, the quantities, an axial cut | `a-explorer` |
| Analysis | Comparison | The two runs, the bias, the quantity | Side by side on one scale, or their difference | `a-compare-side`, `a-compare-diff` |

## The four live links

S6's four pairs are linked both ways by default and stay linked until unlinked; any other pairing is a
link the user pins (WB-06). A linked view carries a chip naming the link, with *Unlink*.

1. **A residue and the charge map**: a residue picked in the 3D view, the residue strip or a list selects its
   deployed charge in the study's charge on the mesh, and a point of the charge map selects the residue it
   came from.
2. **A geometry and its parameters**: the region's thickness and radius, typed on the drawing or in the pane,
   are one value; the contour's vertices in the table and on the editor are one selection.
3. **A field and its probes and cuts**: an axial cut or a probe drawn on the field updates its tile, and
   moving the cut's line on the field moves it.
4. **A run and its result**: a done run in the queue or the study's runs opens its result in Analysis, and a
   result names and opens the run that made it.

## The project folder

The workbench's document is a plain folder (S11), readable without the workbench:

```text
<project>/
  nanopnp-project.yaml        the project file: no physics
  models/molecular/<name>.yaml
  models/continuum/<name>.yaml
  studies/<name>.yaml
  comparisons/<name>.yaml
  runs/<study>/<run>/         each run's resolved case file and manifest
  store/                      the artefact store
```

**The project file** holds the schema identifier, the project's name, the library's index (models, studies,
comparisons by file), the open items, and the layout of each suite (its panels' sizes and folds). The
density and the theme are the user's, not the project's (WB-18, WB-19). A model or study file names its
components and its values away from the defaults; a run resolves them to one complete case file, written
with its manifest, which the command line runs as it is (FR-25; WB-11). The references are a case-schema
change for a shell package after `v0.5.0` (S1; REV-136).

**The export** writes a portable copy of the folder: the project file, the models, studies and comparisons,
and each run's case file, manifest and results, never an opaque archive (S11). The store's intermediate
artefacts are left out unless asked for, each being rebuilt from its case. Exporting figures and fields
from a run is FR-28, v0.7.

## Install and start

The workbench installs with one documented `uv` command, the package with its `gui` extra, and starts with
`nanopnp gui`, which starts the local server and opens the browser on it (S12). Solves run on the user's
machine, in a spawned process; the browser speaks to the server through a network API, so a remote server
can be added later without a redesign. v0.6 has no login and no multi-user use. The front end ships as
prebuilt files inside the package, so no user builds anything (CON-07; S8). QR-10's observation includes
the install. The PyInstaller bundle and the packaging probe leave with Qt.

## The guided route

QR-10's guided run is a route through the suites (WB-08), a layer over the one interface that dictates none
of its design: in the author's words, marking the concept boards, "perhaps only as a tuturial mode? I don't
want it to dictate the design" (`c4-guided-routes`). It starts from a clean project; at each step it dims the
window, lifts the next control with a card beside it (*Back*, *Next*, *Leave the route*), fills defaults,
and marks any value the user changes. *Next* refuses a step whose value is missing or out of range, naming
the range. The route of the mockups (`docs/design/mockups/a/00-guided-route.html`):

1. Load and prepare 2WCD: Molecular, Prepare structure.
2. Build the molecular model with the defaults, pH 7.5 from PROPKA: Molecular, Protonation.
3. Build the continuum model with the defaults, the mesh at the reference size: Continuum, Mesh.
4. Set the salt, which has no default: Continuum, Physics defaults.
5. Set the bias, the study's override: Study, Study setup.
6. Pair the models in a study and run.
7. Follow the run in the queue.
8. Read the conductance in the results explorer.

## Later tools

Each later tool is a library capability and a phase of its own, ordered against validation when Phase 5
closes (S7). The mockups draw where each will sit, with the later-phase banner and no working control.

- **The physics composer** (S3) composes a model from registered building blocks: a field set, weak-form
  contributions, boundary conditions and a solve strategy (FR-20), in `physics/` with its own tests. It opens
  from Physics defaults, and the model it composes joins the registry the *Model* list reads. Its
  architecture leaves room for equations the user types: the model list stays the registry, a composed
  model is a project item like any other, and the composer's blocks are data. Typed equations would amend
  QR-13 and RSK-15, and no tier could verify them; that amendment is not scheduled.
- **The structural mutator** (S4) replaces a side chain in 3D and re-runs the density, the contour, the mesh
  and the charge, library first with a vetted dependency. It opens from Charge edit, beside the charge-level
  edit v0.6 builds.
- **The sketcher** (S5) draws the (r, z) domain by hand: lines, arcs, booleans and named boundaries, meshed
  by the library. It opens from Contour and Region. The solve stays 2D axisymmetric.

Smaller later parts, each drawn with its banner: the Python console (WB-10), the ribbon (WB-09), docked and
modal tools (WB-07), refinement regions and boundary layers in Mesh (REV-136), partial protonation, a
fractional charge at the pH (FR-43; §8.2.18 T6), and figure export (FR-28).

## The shell's reading of artefacts

The shell holds no physics and computes no number (QR-13; RSK-15). The server reads each artefact from the
store through the library and sends its data, with names and units, to the browser, which draws it. The
browser shell's pictures come from `plot/data.py` (`density_section`, `contour_polygon_m`, `mesh_of`,
`protonation_charges`, `charge_grids`, `newton_history`, `solution_fields`, `sweep_curves`); the duplicates
in `gui/` (`gui/geometry.py`'s `density_section`, `reduced_image` and `ImageModel`) retire with Qt. This
settles Phase 5's open decision 4. Every number shown is read from its stage's artefact, floats decoded as
the command line decodes them (REV-134), and a number no artefact supplies is not shown. Meshes and fields
are drawn by the shipped renderer, unmodified and a separate file (CON-09); the molecule's renderer and the
explorer's controls are REV-137, chosen by WP5.02's spike (S8).

## Restated clauses

The clauses that gate the Qt shell are restated for the browser shell. Each restatement is a NOTE beside
its clause, tagged for v0.6, and replaces it in the package that removes Qt (S17; WP5.01 D5). In brief:

| Clause | Today | For the browser shell |
|---|---|---|
| IF-09 | A desktop graphical interface: case editing, run control, convergence, fields | A graphical workbench served locally and opened in the browser by `nanopnp gui`: the four suites, the run queue and the project folder, a thin shell over the IF-01 stage objects through a network API |
| P3 | A desktop application | The workbench, installed with one documented command: select a PDB, set salt and voltage, obtain a prediction and a picture |
| QR-10 | Unaided in the desktop application | Unaided in the workbench, from the install to a conductance and a field picture, by the guided route or without it |
| VER-43 | The schema walk, registry options, refusal at the field, spawned run control, cancellation, exit classes; PySide6 and the packaging probe | Kept for the workbench's forms and the server's run control; the view-models import no front-end framework and no NGSolve; the packaging probe's part is replaced by the server's self-test of every payload the walk needs, failing naming it |
| VER-44 | The convergence hook and the field viewer, in Qt WebEngine | Kept: the hook, its two silences, the rung reading, the renderer shipped unmodified and pinned; the scene served to the browser as a file; the self-test in place of the probe's |
| VER-55 | The geometry pipeline in the Geometry tab | Kept for the Continuum tools: the artefact hook, the picture's orientation, the contour editor's edits and refusals, the derived case, the mesh drawn by material; the view-models import no front-end framework |
| VER-60 | The charge pipeline in the Charge tab | Kept for Protonation, Charge edit and Charge on the mesh: the charge map, the conservation view, the protonation view, the deployed coefficient; a bounded field accepts exactly its schema bounds, a nullable one can say "unset"; the study drives the walk to `upto: charge` |
| CON-09 | PySide6 under the LGPL; the renderer unmodified as a separate file | The PySide6 clause lapses; the renderer clause binds the browser shell; a front-end dependency WP5.02 chooses is permissive, or LGPL or MPL used unmodified as a separate file |
| ADR-004's packaging NOTE | A one-dir PyInstaller bundle with its probe | Lapses with the bundle: the workbench is the package with its `gui` extra, the front end prebuilt inside it; the solver process is still spawned |
| RSK-13 | Desktop packaging defeated by a binary dependency | The workbench's install defeated by a binary dependency: every payload a wheel; CI installs the `gui` extra on Linux, macOS and Windows and runs the self-test |

The new requirements are §3's FR-31 to FR-43 and QR-16, each with its Appendix A row: the suites (FR-31),
the project folder (FR-32), the four live links (FR-33), the changed marks and no hidden state (FR-34), the
refusal at its field (FR-35), the guided route (FR-36), structure preparation (FR-37), the charge-level
mutator (FR-38), the study's overrides and sweeps (FR-39), and the accessibility target (QR-16); the
composer (FR-40), the structural mutator (FR-41), the sketcher (FR-42) and fractional protonation (FR-43)
are tagged for later phases.
CON-08 and CON-11 still name the bundle and the desktop path: REV-141.

## Inherited rows

Fourteen deferred review rows and three modularity findings waited on this document (Phase 5 open decision
3). Each was proposed a ruling here, and the author ruled them on 27 October 2026 (§8.2.18 T1 to T5): as
proposed, but for MOD-09, which the author brought into v0.6 (T4).

| Row | What it is | Ruling |
|---|---|---|
| REV-20 | No `freeze_support` for a frozen shell | `wontfix`: no frozen executable remains once the bundle leaves (S12) |
| REV-28 | The viewer renders every finished run eagerly | `deferred` to the Analysis package: a field is drawn when a tile opens it |
| REV-30 | The viewer's scene is written twice | `deferred` to the Analysis package, which writes each scene once and serves it |
| REV-31 | The bundle's size is not recorded | `wontfix`: no bundle; the install's size is the package's |
| REV-32 | Old store entries neither migrated nor removed | `deferred` to the project-folder package: the library lists entries of an older schema and removes them on request, the workbench offering it |
| REV-39 | A supplied `inputs.profile` gets no contour editor | `deferred` to the Continuum package: the Contour tool opens on any profile, extracted or supplied |
| REV-41 | No `prepare` command, `upto` on reproduce, or region export | `prepare` with structure preparation (WB-14); `upto` on reproduce `deferred` to the Study package; region export with FR-28, v0.7 |
| REV-45 | The derived χ field has no export | `deferred` to FR-28, v0.7 |
| REV-52 | `deviations` and `SolveReporting` off the stage protocol | `deferred` to the first shell package: the workbench reads both of every stage, for the changed count and the queue, so they join the protocol as optional members, library first |
| REV-56 | The contour editor's check runs on the Qt thread; unsaved edits dropped | `wontfix` for the Qt code; the Contour tool checks off the interface's thread and asks before discarding an edit |
| REV-62 | A mesh named by store key is refused | `deferred` to the named-model capability (REV-136), which references a continuum model's mesh |
| REV-65 | The Windows bundle has no `mesh` command | `wontfix`: no bundle; the command line installs with the package everywhere |
| REV-67 | No public registration functions for backend registries | `deferred` to the composer phase, with MOD-11 |
| REV-114 | The shell moves from Qt to a browser | `fixed` by this document and the restated clauses; the package that removes Qt makes them the text |
| MOD-09 | Outputs and steric models are closed enumerations | Brought into v0.6 by the author (T4): both become registries in a Phase 5 library package, so a new quantity of interest needs no schema edit. Proposed: `deferred` to the composer phase |
| MOD-13 (its command-line part) | `cli/__init__.py` past review size | `deferred` to the package that adds `nanopnp gui`, which splits the command line as it adds the command |
| MOD-18 | The Geometry tab views only the stages it knows | `wontfix` for the Qt tab; the workbench lists stages from the registry, and a stage without a view of its own shows its record and verdict |

## Decision log

The design round's rulings, in the author's words where they gave them (§8.2.17 S21). The
organisation round ran on 25 October 2026 over four concept boards, C1 *model builder*, C2
*molecular workspace*, C3 *project and runs* and C4 *guided routes*, kept in
`docs/design/concepts/`; the author ruled for a hybrid in the round, the marks on the boards following later.
Each ruling was played back and confirmed. The look-and-feel round followed the same day over a
style tile of three directions, *instrument*, *notebook* and *molecular*, kept in `docs/design/style/`;
its tokens are `docs/design/tokens.css`. WB-29 came from the author's picks on the choice panels.
WB-30 to WB-32 come from the author's notes on the concept boards and the style tile, collected with
the verdicts on the mockups, where a note contradicting a ruling reopened it; played back, the author
restated them (§8.2.18 T8): "I think many of these should fall under user settings or even a "theme"
approach. The mouse wheel not changing a field was not a literal constraint, just an annoyance that we
should address in one way or another."

| # | Question | Ruling (author's words) | Consequence |
|---|---|---|---|
| WB-01 | The organising principle | "Suites in a project": C3's project folder and run queue as the frame, the parts as suites inside it, each in C1's pattern of tool list, settings and live view, C4's routes over them | The workbench is neither one tab per pipeline stage nor one canvas; S2's "distinct tabs for each part of the workflow" becomes suites, and §8.1's Phase 5 row says so |
| WB-02 | How many top-level parts | Three parts and a run queue | *Molecular*, *Continuum* (geometry, mesh, physics) and *Analysis* (the results explorer). Running is not a part: a queue present in every suite, from whose entries convergence and the log open. Amended by WB-29: four suites, *Study* the fourth |
| WB-03 | What is always on screen | The project browser, the changed-from-default marks and the run queue with its status; "there will likely be other useful things to keep on the screen, but this should grow naturally as the design gets clearer" | FR-25's switches stay visible as a count that opens their list (agenda point 10); the list of what is always on screen stays open to additions |
| WB-04 | Cases open at once, and comparison | Several open; a comparison is a saved document | A variant is derived from its parent and shown as a difference from it; a comparison is a project item pairing runs on one colour scale |
| WB-05 | Where the live views live | A canvas per suite; "for certain tools a custom view (or maybe overlay or popup) would be more convenient" | Molecular draws in 3D, Continuum in (r, z), Analysis fields and plots; a tool may bring its own view, overlay or popup |
| WB-06 | How a selection travels | "Explicit links", with S6's four pairs linked by default | A residue and the charge map, a geometry and its parameters, a field and its probes and cuts, a run and its result follow each other until unlinked; any other pairing is a link the user pins. S6 stands |
| WB-07 | How tools appear in a suite | A tool list beside the selected tool's settings; "the plumbing should be there for docking and modal editors if the tool calls for it" | v0.6 builds the list; the frame allows docked and modal tools later |
| WB-08 | Expert and guided use | One interface with routes | QR-10's guided run is a route through the suites, highlighting the next tool and filling defaults, left at any step; a value changed from its default is marked |
| WB-09 | How commands are reached | Menus, a command palette and keyboard shortcuts, and a ribbon: "the approach [taken] by AutoCAD is quite comprehensive. Let's focus on getting 1 up and running, while making sure the plumbing for 3 is there" | v0.6 builds the menus, the palette and the shortcuts, every command reachable by keyboard; the ribbon is a later addition the frame allows |
| WB-10 | A Python console for P1 | A later phase | The project folder stays plain files that scripts and notebooks read; the mockups show the console with a later-phase banner |
| WB-11 | Running, reuse and the library | One component per suite; a case references them; each suite builds its own, and the solve runs in a study. The author: "a single molecular suite output can be used for multiple continuum runs without recomputing. This alludes again to building a library of components that can be re-used" | A **molecular model** (the prepared structure, its ensemble and protonation) and a **continuum model** (the protein geometry, the region and the mesh) are named items of the project library, each built by its suite. A **study** (in its own suite, WB-29) pairs one of each, assembles the charge on the mesh and solves; the queue holds builds and studies, and a sweep may range over components. A case names its components and resolves at run time to one complete case file, written with the run's manifest, which the command line still runs (FR-25); the references are a case-schema change for a shell package after `v0.5.0` (S1) |
| WB-12 | Where a refusal shows | At the field, and in a problems list | A field refused at entry turns red with a message naming the rule, the value entered and the case path; a build refused later marks its queue entry and lists the refusal, which jumps to the tool and field |
| WB-13 | Who arranges the layout | A designed default per suite, saved | Panels resize and fold, and later dock (WB-07); the arrangement and the open cases are saved in the project file (S11), never in a case; *Reset layout* restores the default |
| WB-14 | Preparing a structure | "Prepare tool in v0.6"; asked against S4's "structure preparation stays out of the library until its phase", "Amend: in Phase 5" | Structure preparation becomes a Phase 5 library capability first, in `structure/` with its Tier 1 tests: the axis estimated, the chains chosen, and the flip and the membrane's place set by the user in the 3D view, with no rule specific to one pore. The Molecular suite's *Prepare* tool surfaces it in v0.6. §8.1's Phase 5 deliverable says so; the Phase 5 plan's packages follow at `/np-plan amend 5` |
| WB-15 | The author's unfinished notes on the contour and the region | "Region is separate" | Stages 1 to 4 fold into the protein geometry tool; the membrane and the reservoirs, stage 5's region, are a Continuum tool of their own |
| WB-16 | Where the physics and the conditions belong | "a hybrid is in order here, much like in COMSOL. The default BCs should be defined in the continuum model, with potential overrides in the study (e.g., for sweeping or ramping)" | The continuum model holds the physics defaults: the model, the electrolyte and the boundary conditions. A study overrides any of them, for a sweep or a ramp, and marks each override as it marks a switch |
| WB-17 | References | COMSOL, ChimeraX and PyMOL, VS Code, AutoCAD and Fusion: "Given that the tool we are building will borrow features from all these tools, it makes sense that we borrow the looks/approach as well for [their] respective suites. The challenge will be to do this in a sleek, modern, and harmonized way" | Each suite borrows its idiom: ChimeraX's 3D view in Molecular, COMSOL's and AutoCAD's tree and graphics in Continuum, COMSOL's plot settings in Analysis, VS Code's palette and quiet chrome for the frame; one token set harmonises them |
| WB-18 | Density | Medium, adjustable | 13.5 px type and 30 px rows by default; a compact setting of 12.5 px and 26 px, saved per user. Amended by WB-31: tighter spacing |
| WB-19 | Theme and default | Both themes, following the system | Light and dark, both held to WCAG 2.2 AA; the default follows the operating system, with a switch |
| WB-20 | Accent and colour maps | One accent and semantic colours each with a glyph; "User-chosen maps" | One accent for selection, the primary action and focus; built, stale and refused in green, amber and red, each with a glyph and a word. viridis (cividis for colour-vision deficiency) and a diverging map centred on zero with its unit are the defaults, charge always opening diverging (VER-60); any Matplotlib map may be chosen per plot, rainbow included, and the plot records which |
| WB-21 | Type, numbers and units | One sans and monospace numbers | Inter, shipped with the application; numbers in tabular figures, a narrow no-break space before the SI unit with an engineering prefix (1.234 nS), scientific notation only where no prefix fits; sizes in rem with a 12 px floor |
| WB-22 | Icons | Icon with text; icon alone with a tooltip in dense toolbars | One open-source icon set across the suites; every icon-only control has an accessible name and names its shortcut |
| WB-23 | Motion | Functional only | Under 200 ms, none under reduced motion; a run shows "rung 7 of N", never a percentage the solver cannot report |
| WB-24 | Accessibility and the keyboard | WCAG 2.2 AA, full keyboard | Non-text contrast of controls, focus rings and colour bars included; a keyboard path for every canvas action, a residue picked from a list as on the canvas; the render check gains a non-text contrast measure. A quality requirement in the specification |
| WB-25 | Tone and glossary | Plain and precise, with a glossary | A refusal states the rule, the value entered, the case path and a remedy; each technical term links to one glossary |
| WB-26 | What the pictures are drawn on | Black for the 3D view, the theme for plots | The Molecular suite's 3D view is always near-black; (r, z) views and plots follow the theme and export on white; every colour bar is outlined at 3:1 so its low end never dissolves. Amended by WB-30: the 3D view's background is a user setting |
| WB-27 | The direction the tokens start from | The molecular direction, with instrument's dark theme | `docs/design/tokens.css` |
| WB-28 | The changed-from-default mark | Its own mark, on changed values only | A filled diamond in its own colour, never the accent, showing the default and a per-field reset; a study override (WB-16) an outlined diamond; the frame's count (WB-03) a button opening the list |
| WB-29 | Where studies are made | Its own suite. The author, picking on the choice panels (RE1): "Now that I see the organisation, I think 'Study' should be its own fully fledged suite next to Molecular, Continuum, and Analysis" | Four suites and a run queue: *Molecular*, *Continuum*, *Study* (pairing the models, the overrides, the sweep, the charge on the mesh, a run's progress) and *Analysis* (the results explorer and the comparisons). Amends WB-02 and WB-11; §8.1's Phase 5 row says so |
| WB-30 | The 3D view's background, reopening WB-26 | The author, marking the style tile's *molecular* direction: "Maybe the always black viewer is not needed, better to be user adjustable" | The Molecular suite's 3D view is near-black by default; the View tool sets it to near-black, the theme or white, saved per user, as part of the user's theme (§8.2.18 T8). The colour bars stay outlined at 3:1 on each |
| WB-31 | The spacing, reopening WB-18 | The author, on the same direction: "Spacings can be even tighter" | The default theme's gaps and padding tighten at both densities (`--gap` 6 px and `--pad` 8 px by default, 4 px and 6 px compact); the type and the row heights stay, the targets at least 24 px (WB-24). Spacing is a user setting of the theme (§8.2.18 T8) |
| WB-32 | Hidden state | The author, marking the *model builder* board: "One of my major gripes with COMSOL though, is the sheer amount of "state" a GUI-based run has, and that everything is hidden in menu's or sub-menus, where an accidental click or scroll may invertedly change a settings" | Every setting of a tool is on its pane, never in a sub-menu; a setting is guarded against an accidental change, the means (the mouse wheel among them) left to the shell's package, the wheel rule "not a literal constraint" (§8.2.18 T8); every value away from its default is marked (WB-28) and counted (WB-03), and a study's overrides are listed with it (FR-34) |

## Glossary

The one glossary every technical term in the workbench links to (WB-25). Physics terms are the knowledge
base's and the specification's; these are the workbench's own.

| Term | Meaning |
|---|---|
| Artefact | What a stage writes: typed, stored, keyed by the hash of its inputs and settings (FR-27) |
| Case file | One complete description of a run, which the command line runs (`nanopnp/case`); the unit of reproducibility |
| Changed mark | A filled diamond on a value set away from its default; an outlined one on a study's override (WB-28) |
| Comparison | A saved project item pairing two runs on one colour scale, side by side or as their difference (WB-04) |
| Continuum model | A library item built in the Continuum suite: the protein geometry, the region, the mesh and the physics defaults (WB-11) |
| Gate | A check a stage passes before its artefact is used, such as the orientation gate or the mesh's quality gate |
| Later phase | A tool drawn with its banner and no working control: designed, not built in v0.6 (S7) |
| Library | The project's models, studies and comparisons, each reused without being rebuilt |
| Live link | Two views that select together until unlinked (S6; WB-06) |
| Molecular model | A library item built in the Molecular suite: the prepared structure, its ensemble and protonation (WB-11) |
| Override | A value a study sets in place of its continuum model's default, for a sweep or a ramp (WB-16) |
| Project | The folder that holds the library, the runs, the store and the project file (S11) |
| Queue | The builds and runs waiting, running and done, always on screen (WB-02, WB-03) |
| Refusal | A value or a build the library declines, shown at its field with the rule, the value, the case path and a remedy (WB-12) |
| Resolved case file | The one complete case file a study's run resolves to, written with its manifest (FR-25) |
| Route | A guided path through the suites, a layer over them (WB-08) |
| Rung | One step of the continuation ladder, from an easy problem to the one asked for; a run shows "rung x of N" (WB-23) |
| Schematic | A drawing that shows where a field lies, not its values |
| Store | Where artefacts are kept, keyed by their hash |
| Study | A Study-suite item pairing one molecular and one continuum model with its overrides and sweep, and running it (WB-11, WB-29) |
| Suite | One of the four parts of the workbench: Molecular, Continuum, Study, Analysis (WB-02, WB-29) |
| Switch | A setting away from its validated default, recorded in every result's manifest (FR-25) |
| Tool | One task in a suite, with its settings docked beside its live view (WB-07) |
| Variant | A model derived from a parent and shown as its difference from it, such as a residue's charge changed (WB-04) |

