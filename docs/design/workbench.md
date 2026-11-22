# Workbench design

The design of the browser workbench, which replaced the Qt desktop shell in v0.6 (Phase 5,
§8.2.17 S1 to S24), written by the WP5.01 design study: today's shell critiqued, a design round with
the author on the organisation and the look and feel, the areas drawn as choice panels and then as two
whole workbenches, and the requirements. Each ruling is a `WB-nn` row of the *Decision log*, in the
author's words. The pictures it rests on are kept beside it and are not part of the site:
the concept boards in `docs/design/concepts/`, the style tile in `docs/design/style/`, the choice
panels in `docs/design/choices/`, the whole-workbench mockups in `docs/design/mockups/` (A, the one
chosen, in `a/`), the scripts that write them in `docs/design/generators/`, and each round's verdicts
and review in `docs/design/reviews/`, and WP5.02's framework spike in `docs/design/spike/` (its report,
`report.md`, and the two windows' pictures). The tokens are `docs/design/tokens.css`.

**What is live and what is record.** Live design: *Purpose and users*, *The areas* to *The shell's
reading of artefacts*, the *Decision log* and the *Glossary*. Record: *Today's shell*, whose capability
list, Q01 to Q41, WP5.27 checked in the workbench before Qt was removed
([the record](reviews/2026-11-21-qt-capabilities.md)), with the critique and the verdicts; *Restated
clauses*, which are now the clauses' own text in the specification; and *Inherited rows*.

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
builder, mesh builder, physics assigner, results analyser, ...". The design round placed them in six
suites (WB-01, WB-02, WB-29, WB-34, WB-43). Each area offers at v0.6 what the library verifies; its later parts carry a
later-phase banner and no working control (S7).

| Area | Suite | Its tools | What it draws on at v0.6 | Later |
|---|---|---|---|---|
| Molecular viewer and editor | Molecular | Prepare structure, Ensemble, Protonation, Charge edit, View | The structure, its frames, ensemble and symmetry; stage 7's protonation and PQR; structure preparation, a Phase 5 library capability (WB-14) | The structural mutator (S4) |
| (added by WB-43) | Meso | Density, Outline, Charge map | A continuum model drawn from the molecular model it is built over, beside the molecule cut at its axis: stage 2's density and the atoms nearest a point; stage 3's map, stage 4's outline and its hand edit (`inputs.profile`), the atoms an edit moves; stage 7's charge on the mesh, a residue named once with its copies; the charge in 3D and its mean about the axis over the molecule (AT2; WB-49) | A free list of the structure's layers (WB-49; REV-265) |
| Geometry builder | Meso, Continuum | Outline (Meso), Region | Stages 4 and 5: the outline and its hand edit, the membrane and the reservoir | The sketcher (S5) |
| Mesh builder | Continuum | Mesh | Stage 6 and its quality report; the size scale and the per-part sizes | Refinement regions drawn by hand; boundary layers |
| Physics assigner | Physics | Equations, Electrolyte, Conditions, Exposed values | A **physics model**: a registered model and its switches, the electrolyte and its corrections, the boundary conditions and walls, the solid permittivities, the element orders and the stabilisation (WB-34) | The composer (S3), in this suite |
| (added by the round) | Study | Overview, Study setup, Sweep, Runs | A study pairing one molecular, one continuum and one physics model, its overrides and sweep, and its runs; its graph's charge opens Meso's Charge map on its pair (AT3) | |
| Results analyser | Analysis | Results, the tree of results (WB-54) | The run record, the quantities of interest, the fields, the sweeps, two runs compared | Figure, field and case export (FR-28, v0.7) |

## Organisation

**The principle** is "suites in a project" (WB-01): the project folder and its run queue are the frame,
and the six suites sit inside it, shown in two groups (WB-02, WB-29, WB-34, WB-43). Four **build** the project's
models: Molecular a **molecular model** (the prepared structure, its ensemble and protonation), Meso and
Continuum a **continuum model** (Meso its pore and charge drawn from a molecular model, adding no kind of
model; Continuum the region and the mesh), Physics a **physics model** (the
equations, the electrolyte, the boundary conditions and their discretisation). Two **use** them: Study a
**study** that pairs one model of each kind and runs it, Analysis the results and their comparisons (WB-11).
Models are items of the project's library, so one molecular model serves many continuum runs, and one
physics model many pores, without being rebuilt. Each model declares the values it exposes, with their
units, ranges and defaults, which the Study suite lists first (WB-35).

**The frame**, from the mockups (`docs/design/mockups/a/`):

- the *title bar*: the menus, the changed-from-default count and the command palette (WB-09, WB-28);
- the *activity bar* on the left: the six suites in their two groups, *Build* and *Use*, each an icon with
  its name (WB-34, WB-43);
- the *project rail*: the project's name at its head, as the tree's root and in the browser tab's title,
  then the open item, the library of models, the studies and the comparisons, folding to the open item and
  unfolding to the project tree (WB-36);
- in each suite, the *tool list*, then the selected tool's *settings*, docked on the left of its *live view*
  (WB-05, WB-07). Every tool docks its settings the same way: in the author's words, marking the mockups,
  "Consistency is key here!";
- the *bottom panel*: the run queue and the log, folded to one line; a run's line opens its convergence in
  Study › Runs' view (WB-02; RE2; WB-45); in Analysis, the tables *Probes*, *Quantities* and *Cut values* beside
  them (WB-59); the Python console a later phase (WB-10).

**Always on screen** (WB-03): the project rail, at least folded; the changed count, opening a list of one line
per value changed from its default and per study override, or at a toggle one dense table of them grouped by
model and study, each with its value, default, unit and reset and leading to its field, while every tool pane and
the settings filter to the changed values (WB-28, WB-36; FR-34; REV-237); and the queue's status line. The list stays open to additions as the design grows.

**State is never hidden** (WB-32): every setting of a tool is on its pane, none in a sub-menu; a setting
is guarded against being changed by accident, the means left to the shell's package; and every value away
from its default carries its mark.

**The frame is built from the components NiceGUI ships through Quasar** (WB-33): the application layout and
its drawers, the tree, the dense table, the searchable select, the icon font and NiceGUI's sub-pages, the
tokens fed into Quasar's colour variables; a part is written by hand only where no component serves it.

**The settings** are one declared list (WB-37): each setting has its section, its scope (the user's, or the
project's, which overrides the user's where both are allowed), its default, its description and search words,
and when it applies, and the settings page, its search and the palette's setting commands follow from it. A
value that can change a result is never a setting; it belongs to a model or a study and its manifest. The one
exception is threads per solve, which can move a result at rounding, so each run's record states it (§8.2.38 AN1).
v0.6's list (AN3): appearance and accessibility holds the theme, the density, the spacing, the 3D view's
background, the user's colours and reduced motion; keyboard and editing guards the key bindings and a guard that
asks before a reset, *Reset layout* or *Quit*; runs and storage the recent projects, opening the last project at
start, the store's size cap and its two clean-up actions, one for what no run uses and one for every result
(AN5); units and numbers the significant figures and the number style, which a project may also set, as it may
the store's cap; and a Compute section, solves at once and threads per solve (AN1). No setting reaches the
network yet. The list is a registry that a later package or a plugin extends, and nothing in it precludes a
remote connection (a WSL instance, a compute server) or a plugin (custom physics) (AN2).

**Several items are open at once** (WB-04); a variant is derived from its parent and shown as its
difference: a molecular model's variant is linked to its parent by default, holding only its residue edits, or a
full copy on request (§8.2.39 AO3); two runs are compared as a Data node of the tree of results (WB-54). **A refusal** shows at its field and in
the problems list, naming the rule, the value, the case path and a remedy (WB-12, WB-25). **The layout** is a designed
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
- one accent for selection, the primary action and focus; built in green, what blocks a run in red, what
  blocks nothing, as a stale stage or a preview, in amber, and information, as a building stage, in blue,
  each with a glyph and a word (WB-20, WB-40, WB-42); a changed value's own mark, a filled diamond, and a
  study's override an outlined one (WB-28);
- viridis (cividis for colour-vision deficiency) and a diverging map centred on zero by default, charge
  always diverging (VER-60), any Matplotlib map per plot, recorded with it (WB-20);
- Inter, numbers in tabular figures, a narrow no-break space before an SI unit with an engineering prefix
  (WB-21); icons with text, or alone with a tooltip in dense toolbars (WB-22); motion functional only,
  under 200 ms (WB-23);
- the Molecular 3D view near-black by default, a user setting (WB-26, WB-30); (r, z) views and plots on the
  theme, exported on white; every colour bar outlined at 3:1 (WB-26).

**The words** follow five rules (WB-52):

1. A title, heading or field label is a plain noun phrase: *Rungs*, *Values*, *Boundary conditions*.
2. No "its" or "their" where the noun alone reads.
3. No clause or question as a heading ("What…", "How…", "As a … lists it").
4. A pointer to another place is a link, and the sentence says what to do there: "Start one in Study › Runs."
5. Sentences stay short and active; messages and refusals follow ASD-STE100 (WB-42).

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
| Q01 to Q04 | Window | `nanopnp gui [<project>]` opens the project; the browser tab and the project rail name it (WB-36); the queue and the problems list say what runs and what was refused; closing stops the builds and their child processes |
| Q05 to Q08 | Case | Each field in the tool that sets it, checked as it is typed and refused at the field (WB-12); the study's *Overview* shows the resolved case file; a section is added by the tool that uses it; a build or run validates and writes the case first; a setting with no field of its own is set in Study setup's *More values*, which offers every case path the study's lists do not show, by its path and a typed value, and a supplied input by import (§8.2.47 AW10) |
| Q09 | Geometry | *Open structure…* in Molecular, Prepare structure |
| Q10 to Q12, Q23 | Geometry | Each Continuum tool's *Build*, queued; the tool list's status per tool; *Cancel* in the queue; a tool's record under its *Checks*, the log in the bottom panel |
| Q13 | Geometry | Prepare structure's orientation gate and its checks |
| Q14, Q15 | Geometry | Meso's Density and Outline: the density section and the reduced maps with their colour bars, the key of the lines drawn over them; a point of the density names the residues its atoms reach first |
| Q16 to Q20 | Geometry | Meso's Outline, *Edit outline*: move (by its typed r and z, which is the capability WP5.27 checks, §8.2.47 AW7; dragging with Phase 7's polish pass, WP5.26 before AW1, after Qt has left), insert and delete vertices, *Undo*, *Redo*, *Measure*, *Seed from the map*, *Save edit…*; the residues the edit moves into the water and into the protein |
| Q21 | Geometry | The Region tool, each domain picked in the view |
| Q22 | Geometry | Mesh, sizes and quality: the parts' tree, the element count, the quality gate and its histogram, the worst elements located |
| Q24 to Q26, Q30 | Charge | Meso's *Charge map*, built by *Build charge map* over the continuum model's molecular model, with its conservation checks |
| Q27 | Charge | Molecular, Protonation, its residue states, Q<sub>net</sub> and the PROPKA warnings |
| Q28, Q29 | Charge | Charge map: the lattice and the deployed density in (r, z) beside the molecule, linked (S6), a residue named once with its copies |
| Q31 to Q34 | Run | *Run study*; *Cancel* on the running entry in Study › Runs; the running entry's "stage i of N: name, rung x of N" in the queue (WB-23) and the run's lines in the log (§8.2.47 AW9) |
| Q35, Q36 | Convergence | A run picked in Study › Runs or opened from its queue line: the convergence plot across the view, the rung table in the pane (WB-45) |
| Q37, Q38 | Result | The results explorer: the run's folder and its quantities, in the quantities tile; *Open in Runs* (WP5.21), which WP5.27 checks. From Phase 7's tree of results (§8.2.47 AW1; §8.2.49 AY1): *Data › Shown run* names the run, its folder in the tooltip, with *Open in Runs*; its quantities in the bottom panel's *Quantities* (WB-54, WB-59, WB-63) |
| Q39 | Result | The quantities tile's *Changed from the validated default*, from the run's manifest (WP5.21); from the tree, beside the quantities (WB-59) |
| Q40, Q41 | Fields | The results explorer's field tile: its quantity, its colour map and range, as a map or on the solve's mesh, the renderer's message in place of a view that does not draw (WP5.21, WB-53), which WP5.27 checks. From the tree: a plot group's surface, its expression, colour map and range, *Show mesh* for the solve's mesh (WB-56, WB-57) |

Five details of rows Q13, Q14, Q18, Q21, Q22, Q26, Q27, Q29 and Q30 are carried to Phase 7, and the Qt shell leaves
without them (REV-274; §8.2.47 AW11; §8.2.49 AY1).

## Tools

Each tool has its settings and its live view (S6). The mockup screen named is in `docs/design/mockups/a/`.

| Suite | Tool | Settings | Live view | Screen |
|---|---|---|---|---|
| Molecular | Prepare structure | The structure file, the chains, the axis tilt (estimated or typed), the flip, the membrane's centre; the orientation gate; *Save prepared structure* | 3D: the axis and the membrane slab, drawn from the values typed in the pane and stepped by the arrow keys; dragging them by handles comes later (§8.2.39 AO2; REV-238) | `m-prepare` |
| Molecular | Ensemble | The source (a trajectory or the structure alone), the stride, the frames used with their Q<sub>net</sub> | 3D, one frame or the frames overlaid | `m-ensemble` |
| Molecular | Protonation | The pH, the force field, the titration; *Build molecular model*; the residue states | 3D and the residue strip, each residue with its sign | `m-protonation` |
| Molecular | Charge edit | A titratable residue's protonation state, an integer change of its charge on its titratable group, or a scale on a residue's radii, on every chain, saved as a variant with its difference from its parent: linked by default, holding only its edits and following its parent, or a full copy on request (§8.2.19 U6; §8.2.31 AG9 to AG11; §8.2.39 AO3) | 3D, the residue picked or chosen from a list | `m-charge` |
| Molecular | View | The representation, the colouring, the background, the slab, the clip; a residue list | 3D, with the charge's diverging bar | `m-view` |
| Molecular | Exposed values | *Expose* at the list's head; each value the model exposes with its name, unit, range and default (WB-35); the one place a molecular model's list changes (WB-48) | The list as the Study suite shows it | none yet |
| Meso | Density | Stage 2: the grid, the kernel's sharpness, the atoms smeared; the point group (Prepare's); the picture; *Build density*, over the molecular model chosen in the pane, Continuum's *Built over* (§8.2.40 AP2); the residues whose atoms reach a picked point first, each at its distance in its atom's kernel widths (§8.2.44 AT1); the structure's look (WB-49) | Mol*, side on and cut at the axis, by chain, beside (r, z): the density section or a reduced map with its colour bar and the membrane; a residue's atoms marked at (r, z) | `g-geometry` |
| Meso | Outline | Stages 3 and 4: the isolevel, the smoothing, the simplification; stage 4's verdict; *Build outline*; *Edit outline* on the built or supplied outline, and *Save edit…*, a continuum model holding the edited outline, which a study runs with its molecular model's structure and charge (§8.2.40 AP1); the residues the edit moves into the water and into the protein, each with its copies, atoms and charge per copy and frame (AT1); a supplied outline's stage 2 to 4 values read-only (WB-41); the structure's look (WB-49) | Mol*, cut at the axis, by chain, beside (r, z): a reduced map with its colour bar, the outline and the probe radius, a key naming each line; the editor over them; a residue's atoms marked | `g-contour` |
| Meso | Charge map | *Build charge map*: the continuum model walked over its molecular model to stage 7 (`Project.charge_case`); the lattice or the deployed charge; the charged residues, each named once with its charge per copy (REV-259); the structure's look and the map's range (WB-49); the overlay, each volume at its level (AT2); the conservation checks | Mol*, side on and cut at the axis with a *One subunit* switch (WB-44), by charge, the overlay's isosurfaces over it, beside (r, z), its scale opening on the 99th percentile of the charge's size, through a dark middle on the dark theme, linked both ways | `st-charge` |
| Continuum | Region | The membrane's thickness and centre, the reservoir's radius, the ion-exclusion offset, or an idealised pore's radius; the continuum model is the one place they are set (WB-40) | (r, z): each domain its own shape, picked in the view to bring its values to the pane's head; each value typed on the drawing as in the pane (WB-41) | `g-region` |
| Continuum | Mesh | The mesher, the size scale, and a tree of the mesh's parts (the domains, the boundaries, the global size), each with the size it gets and its source, a part picked opening its one field, typed as a base the scale multiplies (§8.2.40 AP3, AP4; WB-41); *Build mesh* and its quality gate, its verdict and limits first | (r, z) mesh by material, SICN or gamma, the picked part drawn; by quality, the histogram with its axis, counts and the 0.3 floor, a bar filling its elements | `s-size`, `s-quality` |
| Continuum | Exposed values | As Molecular's, for a continuum model's values, the mesh's size scale among them (WB-48) | The list as the Study suite shows it | none yet |
| Physics | Equations | The registered model and its switches; the element orders and the stabilisation; the composer's place, with its later-phase banner (WB-34). Choosing another model sets each switch it does not honour to the value it does and removes each value it refuses, one note listing every change with *Undo* (§8.2.41 AQ2). A switch the model holds at one value is greyed, saying why, and so are the dielectric-gradient forces while the flow is off (PHY-23's NOTE; §8.2.42 AR1) | The model's equations set as mathematics, each written whole with its corrections; the fields; a table of the symbols (WB-42) | none yet |
| Physics | Electrolyte | The parameter set, the ions, the concentration, the temperature, the driver; a table of the corrections, a row per property with its bulk and wall parts; the steric flux; the wall distance's sources picked from the boundaries | Two plots, one above the other: each correction's factor against the driver on a square-root axis, the fitted range and the operating value marked; then against the distance to the wall (WB-42) | `p-electrolyte` |
| Physics | Conditions | The bias, the ground, the walls, the wall charge beside an idealised pore; one permittivity per solid; each boundary role's condition, set as mathematics | (r, z) of the shown study's region, each role along its named edges, picked in the view or the list; *Show mesh* (WB-42) | `p-boundaries` |
| Physics | Exposed values | *Expose* at the list's head; each value the model exposes with its name, unit, range and default (WB-35); the one place a physics model's list changes (WB-42) | The list as the Study suite shows it | none yet |
| Study | Overview | The three models, the sweep, the overrides, the changed values, the runs, the physics run | The values the models and the study set, none unset; *Show the whole case* unfolds the resolved case file (WB-46) | `st-overview` |
| Study | Study setup | The models, their exposed values first and *More values* (WB-35), the overrides, the outputs; *Run study* | A form, or the same study as a graph (RE1) | `st-form`, `st-graph` |
| Study | Sweep | The axes, each over a value, a variable or a model, with what it rebuilds; *Every combination* or *Stepped list* (WB-46) | The points as a table: each point's values, its warm start's order and its state (WB-46) | `st-sweep` |
| Study | Runs | *Run study*; the recorded runs; the picked run's rung table; Cancel, the log | The picked run's convergence across the view, a running one updating; a run's queue line opens it here (RE2; WB-45) | `st-runs` |
| Analysis | Results | The tree of results (WB-54): *Data* (a run, a sweep's runs, two runs compared, a revolution), *Definitions* (WB-58), *Probes and cuts*, *Quantities* (WB-59) and *Plot groups*; the selected node's settings under it, one column (WB-55); a new tree from what the run provides (WB-62) | The selected plot group, or two side by side (WB-55), drawn by Plotly (WB-57): a 2D group's surface, contours, arrows, outline and *Show mesh*, two runs mirrored first, side by side or as their difference (WB-63); a 1D group's line along a cut, point graph or global plot; a 3D group's revolution (WB-56). Until Phase 7's tree of results (WP5.22 before §8.2.47 AW1; §8.2.49 AY1): WP5.21's results explorer and Comparison | `a-explorer`, `a-compare-side`, `a-compare-diff`; the tree's boards in `concepts/tree/` |

Every Physics tool shows its model inside a study picked in the pane, *Shown in*: that study with this physics model in place of its own and the study's own values of the physics model's keys left out, each marked beside its field with an outlined diamond (WB-28). It opens on the first study that names the model, else the project's first; a project with no study shows the model over its continuum model as that model is built alone. A value the shown study cannot run with is shown at its field, naming the study (§8.2.41 AQ1).

## The four live links

S6's four pairs are linked both ways by default and stay linked until unlinked; any other pairing is a
link the user pins (WB-06). A linked view carries a chip naming the link, with *Unlink*.

1. **A residue and the charge map**: a residue picked in the 3D view, the residue strip or a list selects its
   deployed charge in Meso's Charge map, and a point of the charge map selects the residue it came from,
   its copies together.
2. **A geometry and its parameters**: the region's thickness and radius, typed on the drawing or in the pane,
   are one value; the contour's vertices in the table and on the editor are one selection.
3. **A field and its probes and cuts**: a click on the map places the axial cut or a probe, to 0.01 nm, and typed
   values move them; the cut's chart and the probes' rows follow, on both runs' maps in a comparison. Probes and
   cuts are nodes of the tree, shared by every plot group that draws their data (WB-54). Dragging the cut's line is
   Phase 7's polish pass's (WP5.26 before §8.2.47 AW1; REV-267).
4. **A run and its result**: a done run's *Result* in the queue, and a recorded run in Study › Runs, opens it in
   Analysis as *Data › Shown run*, as does a point of its I–V; every plot group following it redraws, and the view
   names the run and opens it in Runs (WP5.21; WB-61).

## The project folder

The workbench's document is a plain folder (S11), readable without the workbench:

```text
<project>/
  nanopnp-project.yaml        the project file: no physics
  models/molecular/<name>.yaml
  models/continuum/<name>.yaml
  models/physics/<name>.yaml
  studies/<name>.yaml
  results.yaml                the tree of results (WB-60)
  inputs/                     the input files copied in; a linked one stays where it lies
  runs/<study>/<run>/         each run's resolved case file, manifest and results
  sweeps/                     each sweep's records
  store/                      the artefact store
```

**The project file** holds the schema identifier, the project's name, the library's index (models and studies
by file), the open items, the layout of each suite (its panels' sizes and folds) and the project's own settings
(WB-37). The density and the theme are the user's, not the project's (WB-18, WB-19). A model or study file names its
components and its values away from the defaults; a run resolves them to one complete case file, written
with its manifest, which the command line runs as it is (FR-25; WB-11). The references are a case-schema
change for a shell package after `v0.5.0` (S1; REV-136).

**Import and inputs.** A case file imports into the project, split into its two models and its study
(`nanopnp project import`); the study computes exactly what the case did. A case that names model files
brings them along under their names. Each input file is copied into `inputs/` or, with `--link`, kept where
it lies, and a linked one is copied in later (`project embed`); a project with links works only where they
resolve, and the problems list says which do not (FR-32; AI9, AI10).

**The export** writes a portable copy of the folder: the project file, the models, studies and the results file,
the inputs (a linked one copied in), and each run's case file, manifest and results, never an opaque archive
(S11). The store's intermediate
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
4. Set the salt, which has no default: Physics, Electrolyte.
5. Set the bias, the study's override: Study, Study setup.
6. Pair the models in a study and run.
7. Follow the run in the queue.
8. Read the conductance in Analysis, in the bottom panel's *Quantities* (WB-59).

## Later tools

Each later tool is a library capability and a phase of its own, before validation: the composer is Phase 8, the
structural mutator Phase 9 and the sketcher Phase 10 (S7; §8.2.49 AY2). The mockups draw where each will sit, with the later-phase banner and no working control.

- **The physics composer** (S3), in the Physics suite (WB-34), composes a model from registered building blocks: a field set, weak-form
  contributions, boundary conditions and a solve strategy (FR-20), in `physics/` with its own tests. It opens
  from the Equations tool, and the model it composes joins the registry that tool's list reads. Its
  architecture leaves room for equations the user types: the model list stays the registry, a composed
  model is a project item like any other, and the composer's blocks are data. Typed equations would amend
  QR-13 and RSK-15, and no tier could verify them; that amendment is not scheduled.
- **The structural mutator** (S4) replaces a side chain in 3D and re-runs the density, the contour, the mesh
  and the charge, library first with a vetted dependency. It opens from Charge edit, beside the charge-level
  edit v0.6 builds.
- **The sketcher** (S5) draws the (r, z) domain by hand: lines, arcs, booleans and named boundaries, meshed
  by the library. It opens from Meso's Outline and Region. The solve stays 2D axisymmetric.

Smaller later parts, each drawn with its banner: the Python console (WB-10), the ribbon (WB-09), docked and
modal tools (WB-07), refinement regions and boundary layers in Mesh (REV-136), partial protonation, a
fractional charge at the pH (FR-43; §8.2.18 T6), and figure export (FR-28).

## The shell's reading of artefacts

The shell holds no physics and computes no number (QR-13; RSK-15). The server reads each artefact from the
store through the library and sends its data, with names and units, to the browser, which draws it. The
browser shell's pictures come from `plot/data.py` (`density_section`, `contour_polygon_m`, `mesh_of`,
`protonation_charges`, `charge_grids`, `newton_history`, `sweep_curves`, and `post/export.py`'s
`solution_fields`); the duplicates
in `gui/` (`gui/geometry.py`'s `density_section`, `reduced_image` and `ImageModel`) retire with Qt. This
settles Phase 5's open decision 4. Every number shown is read from its stage's artefact, floats decoded as
the command line decodes them (REV-134), and a number no artefact supplies is not shown. Meshes and fields
are drawn by the shipped renderer, unmodified and a separate file (CON-09). The front end is NiceGUI over
FastAPI (ADR-004's NOTE, the front end, v0.6; §8.2.30 AF4).

### The renderers

One renderer draws each kind of picture (REV-137). Each ships as a separate file, unmodified where it is a
third party's.

| Picture | Renderer | Where it is | Licence |
|---|---|---|---|
| The molecule in 3D | Mol*, as its standalone bundle (`molstar.js`, `molstar.css`) | `src/nanopnp/gui/web/assets/molstar/` | MIT (CON-09) |
| Plots and (r, z) views, from Phase 7's tree of results (WP5.22 before §8.2.47 AW1) | Plotly (plotly.js 3.1.1), as NiceGUI 3.18 ships it for `ui.plotly`, unmodified, its own toolbar hidden: every chart, map, mesh and (r, z) drawing, the solve's mesh as a layer and the field turned about the axis (WB-57) | NiceGUI's `nicegui/elements/plotly/dist`, served from the server's origin | MIT (CON-09) |
| Fields on the mesh, until that package | npm `webgui` 0.2.39, served at `/vendor/webgui`; a host page fetches its scene from `/api/analysis/scene` (WP5.21) | `src/nanopnp/gui/assets/webgui/` | LGPL-2.1-or-later, with three.js (MIT) and dat.gui (Apache-2.0) (CON-09) |
| Maps and the mesh in (r, z), until that package | A canvas the page draws from the data of `plot/data.py`, the Continuum suite's mesh among them (WP5.17); a map's colours from the workbench's five maps or any of Matplotlib's (`gui/geometry.py:lookup_table`, AU2) | `src/nanopnp/gui/web/` | BSD-3-Clause |
| Plots, until that package | uPlot 1.6.32 (`uPlot.iife.min.js`, `uPlot.min.css`), served at `/vendor/uplot`; `gui/web/chart.py`'s chart drawn by `assets/chart.js`: Electrolyte's two plots, Runs' convergence, the I–V and the cuts (AU1; the library is chosen again with REV-268's tree) | `src/nanopnp/gui/web/assets/uplot/` | MIT (CON-09) |
| The study as a graph | Mermaid, as NiceGUI ships it for `ui.mermaid` (WP5.19) | NiceGUI's `nicegui/elements/mermaid/dist`, served from the server's origin | MIT |
| Equations and conditions | KaTeX 0.19.1 (`katex.min.js`, `katex.min.css`, its fonts), from the LaTeX of `physics/terms.py` (WP5.18) | `src/nanopnp/gui/web/assets/katex/` | MIT (CON-09) |

Until that package (WB-57), the results explorer asks four controls of its field view: zoom, a colour scale for each quantity, the mesh
on or off, and a framed opening view (the author's verdicts on today's shell). Read from the shipped
`webgui.js`, `webgui` serves two of them whole and the rest in part:

| Control | Served by `webgui` | How |
|---|---|---|
| Zoom | Yes | The mouse wheel and drag of the scene's orbit controls |
| The mesh on or off | Yes | The *Objects* folder has one check box each for *Surface*, *Wireframe* and *Edges* |
| A colour scale for each quantity | In part | One colour map per scene: *Colormap* sets its minimum, maximum and autoscale. A scene holds one quantity, so a scale for each quantity is one scene each; `gui/render.py` writes the range into the scene |
| A framed opening view | Through its settings | No control re-frames the scene, but the scene's `gui_settings.camera` sets the opening camera: the host page writes it from the map's close-up before the scene loads (WP5.21) |

The 200 ms line (WB-23) is not measured for the whole picture. On a container with no GPU, Mol* alone
needs about 800 ms to repaint a selection, and the front end's own share is 14 to 26 ms
(`docs/design/spike/report.md`). WP5.19's `.claude/scripts/gui/redraw.cjs` times a pick on the charge map. Headless
on 2WCD, the markers' paint took 297 ms median and 380 ms p95, of which the server took 167 / 243 ms, and Mol*'s second
frame 745 / 827 ms. The measurement on a GPU and the front end's fix go to a performance package (§8.2.42 AR7;
REV-258).

## Restated clauses

The clauses that gated the Qt shell were restated for the browser shell, each as a NOTE beside its
clause, and WP5.27 made each NOTE the clause's text (S17; WP5.01 D5). In brief:

| Clause | Today | For the browser shell |
|---|---|---|
| IF-09 | A desktop graphical interface: case editing, run control, convergence, fields | A graphical workbench served locally and opened in the browser by `nanopnp gui`: the six suites, the run queue and the project folder, a thin shell over the IF-01 stage objects through a network API |
| P3 | A desktop application | The workbench, installed with one documented command: select a PDB, set salt and voltage, obtain a prediction and a picture |
| QR-10 | Unaided in the desktop application | Unaided in the workbench, from the install to a conductance and a field picture, by the guided route or without it |
| VER-43 | The schema walk, registry options, refusal at the field, spawned run control, cancellation, exit classes; PySide6 and the packaging probe | Kept for the workbench's forms and the server's run control; the view-models import no front-end framework and no NGSolve; the packaging probe's part is replaced by the server's self-test of every payload the walk needs, failing naming it |
| VER-44 | The convergence hook and the field viewer, in Qt WebEngine | Kept: the hook, its two silences, the rung reading, the renderer shipped unmodified and pinned; the scene served to the browser as a file; the self-test in place of the probe's |
| VER-55 | The geometry pipeline in the Geometry tab | Kept for the Continuum tools: the artefact hook, the picture's orientation, the contour editor's edits and refusals, the derived case, the mesh drawn by material; the view-models import no front-end framework |
| VER-60 | The charge pipeline in the Charge tab | Kept for Protonation, Charge edit and Meso's Charge map: the charge map, the conservation view, the protonation view, the deployed coefficient; a bounded field accepts exactly its schema bounds, a nullable one can say "unset"; the Charge map drives a continuum model's walk over its molecular model to `upto: charge` |
| CON-09 | PySide6 under the LGPL; the renderer unmodified as a separate file | The PySide6 clause lapses; the renderer clause binds the browser shell; a front-end dependency WP5.02 chooses is permissive, or LGPL or MPL used unmodified as a separate file |
| ADR-004's packaging NOTE | A one-dir PyInstaller bundle with its probe | Lapses with the bundle: the workbench is the package with its `gui` extra, the front end prebuilt inside it; the solver process is still spawned |
| RSK-13 | Desktop packaging defeated by a binary dependency | The workbench's install defeated by a binary dependency: every payload a wheel; CI installs the `gui` extra on Linux, macOS and Windows and runs the self-test |

The new requirements are §3's FR-31 to FR-43 and QR-16, each with its Appendix A row: the suites (FR-31),
the project folder (FR-32), the four live links (FR-33), the changed marks and no hidden state (FR-34), the
refusal at its field (FR-35), the guided route (FR-36), structure preparation (FR-37), the charge-level
mutator (FR-38), the study's overrides and sweeps (FR-39), and the accessibility target (QR-16); the
composer (FR-40), the structural mutator (FR-41), the sketcher (FR-42) and fractional protonation (FR-43)
are tagged for later phases.
CON-08 and CON-11 name the installed workbench in place of the bundle and the desktop path (REV-141).

## Inherited rows

Fourteen deferred review rows and three modularity findings waited on this document (Phase 5 open decision
3). The author ruled them on 27 October 2026, as proposed but for MOD-09, which the author brought into v0.6:
[§8.2.18 T1 to T5](../_generated/model/specification/history/18-the-workbench-design-studys-rulings-agreed-27-oct.md)
holds the rulings, and the [review register](../_generated/project/review-findings.md) each row's state.

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
should address in one way or another." WB-33 to WB-38 come from the third `/np-plan amend 5`, on 5 November 2026, after
the author's verdicts on WP5.08's frame (`docs/design/reviews/2026-11-05-frame.md`; §8.2.34). WB-39 comes from the
author's verdicts on WP5.16's Molecular drafts, collected on 11 November 2026. WB-54 to WB-63 come from WP5.22's design round on the tree of results, on 21 November 2026, over the
boards in `docs/design/concepts/tree/`, drawn on 2WCD's solved fields; each was played back and confirmed.

| # | Question | Ruling (author's words) | Consequence |
|---|---|---|---|
| WB-01 | The organising principle | "Suites in a project": C3's project folder and run queue as the frame, the parts as suites inside it, each in C1's pattern of tool list, settings and live view, C4's routes over them | The workbench is neither one tab per pipeline stage nor one canvas; S2's "distinct tabs for each part of the workflow" becomes suites, and §8.1's Phase 5 row says so |
| WB-02 | How many top-level parts | Three parts and a run queue | *Molecular*, *Continuum* (geometry, mesh, physics) and *Analysis* (the results explorer). Running is not a part: a queue present in every suite, from whose entries convergence and the log open. Amended by WB-29: four suites, *Study* the fourth. Amended by WB-34: five suites, Physics the fifth |
| WB-03 | What is always on screen | The project browser, the changed-from-default marks and the run queue with its status; "there will likely be other useful things to keep on the screen, but this should grow naturally as the design gets clearer" | FR-25's switches stay visible as a count that opens their list (agenda point 10); the list of what is always on screen stays open to additions |
| WB-04 | Cases open at once, and comparison | Several open; a comparison is a saved document | A variant is derived from its parent and shown as a difference from it; a comparison is a project item pairing runs on one colour scale |
| WB-05 | Where the live views live | A canvas per suite; "for certain tools a custom view (or maybe overlay or popup) would be more convenient" | Molecular draws in 3D, Continuum in (r, z), Analysis fields and plots; a tool may bring its own view, overlay or popup |
| WB-06 | How a selection travels | "Explicit links", with S6's four pairs linked by default | A residue and the charge map, a geometry and its parameters, a field and its probes and cuts, a run and its result follow each other until unlinked; any other pairing is a link the user pins. S6 stands |
| WB-07 | How tools appear in a suite | A tool list beside the selected tool's settings; "the plumbing should be there for docking and modal editors if the tool calls for it" | v0.6 builds the list; the frame allows docked and modal tools later |
| WB-08 | Expert and guided use | One interface with routes | QR-10's guided run is a route through the suites, highlighting the next tool and filling defaults, left at any step; a value changed from its default is marked |
| WB-09 | How commands are reached | Menus, a command palette and keyboard shortcuts, and a ribbon: "the approach [taken] by AutoCAD is quite comprehensive. Let's focus on getting 1 up and running, while making sure the plumbing for 3 is there" | v0.6 builds the menus, the palette and the shortcuts, every command reachable by keyboard; the ribbon is a later addition the frame allows |
| WB-10 | A Python console for P1 | A later phase | The project folder stays plain files that scripts and notebooks read; the mockups show the console with a later-phase banner |
| WB-11 | Running, reuse and the library | One component per suite; a case references them; each suite builds its own, and the solve runs in a study. The author: "a single molecular suite output can be used for multiple continuum runs without recomputing. This alludes again to building a library of components that can be re-used" | A **molecular model** (the prepared structure, its ensemble and protonation) and a **continuum model** (the protein geometry, the region and the mesh) are named items of the project library, each built by its suite. A **study** (in its own suite, WB-29) pairs one of each, assembles the charge on the mesh and solves; the queue holds builds and studies, and a sweep may range over components. A case names its components and resolves at run time to one complete case file, written with the run's manifest, which the command line still runs (FR-25); the references are a case-schema change for a shell package after `v0.5.0` (S1). Amended by WB-34: a **physics model** is the third kind, and a study pairs one of each |
| WB-12 | Where a refusal shows | At the field, and in a problems list | A field refused at entry turns red with a message naming the rule, the value entered and the case path; a build refused later marks its queue entry and lists the refusal, which jumps to the tool and field |
| WB-13 | Who arranges the layout | A designed default per suite, saved | Panels resize and fold, and later dock (WB-07); the arrangement and the open cases are saved in the project file (S11), never in a case; *Reset layout* restores the default |
| WB-14 | Preparing a structure | "Prepare tool in v0.6"; asked against S4's "structure preparation stays out of the library until its phase", "Amend: in Phase 5" | Structure preparation becomes a Phase 5 library capability first, in `structure/` with its Tier 1 tests: the axis estimated, the chains chosen, and the flip and the membrane's place set by the user in the 3D view, with no rule specific to one pore. The Molecular suite's *Prepare* tool surfaces it in v0.6. §8.1's Phase 5 deliverable says so; the Phase 5 plan's packages follow at `/np-plan amend 5` |
| WB-15 | The author's unfinished notes on the contour and the region | "Region is separate" | Stages 1 to 4 fold into the protein geometry tool; the membrane and the reservoirs, stage 5's region, are a Continuum tool of their own |
| WB-16 | Where the physics and the conditions belong | "a hybrid is in order here, much like in COMSOL. The default BCs should be defined in the continuum model, with potential overrides in the study (e.g., for sweeping or ramping)" | The continuum model holds the physics defaults: the model, the electrolyte and the boundary conditions. A study overrides any of them, for a sweep or a ramp, and marks each override as it marks a switch. A study may also override any other value of the models it names; the Study suite offers the physics defaults first (§8.2.31 AG12). The library keeps each override as the case's `Case.overrides` and in the manifest beside the model's value, and an override moves only the stages that read it (FR-39; WP5.05). Amended by WB-34: the physics defaults are the physics model's, which a study overrides |
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
| WB-29 | Where studies are made | Its own suite. The author, picking on the choice panels (RE1): "Now that I see the organisation, I think 'Study' should be its own fully fledged suite next to Molecular, Continuum, and Analysis" | Four suites and a run queue: *Molecular*, *Continuum*, *Study* (pairing the models, the overrides, the sweep, the charge on the mesh, a run's progress) and *Analysis* (the results explorer and the comparisons). Amends WB-02 and WB-11; §8.1's Phase 5 row says so. Amended by WB-34: five suites, in two groups |
| WB-30 | The 3D view's background, reopening WB-26 | The author, marking the style tile's *molecular* direction: "Maybe the always black viewer is not needed, better to be user adjustable" | The Molecular suite's 3D view is near-black by default; the View tool sets it to near-black, the theme or white, saved per user, as part of the user's theme (§8.2.18 T8). The colour bars stay outlined at 3:1 on each |
| WB-31 | The spacing, reopening WB-18 | The author, on the same direction: "Spacings can be even tighter" | The default theme's gaps and padding tighten at both densities (`--gap` 6 px and `--pad` 8 px by default, 4 px and 6 px compact); the type and the row heights stay, the targets at least 24 px (WB-24). Spacing is a user setting of the theme (§8.2.18 T8); its tight value is `--gap` 4 px and `--pad` 5.3 px, 2.7 px and 4 px at compact density (`data-spacing="tight"` in `tokens.css`) |
| WB-32 | Hidden state | The author, marking the *model builder* board: "One of my major gripes with COMSOL though, is the sheer amount of "state" a GUI-based run has, and that everything is hidden in menu's or sub-menus, where an accidental click or scroll may invertedly change a settings" | Every setting of a tool is on its pane, never in a sub-menu; a setting is guarded against an accidental change, the means (the mouse wheel among them) left to the shell's package, the wheel rule "not a literal constraint" (§8.2.18 T8); every value away from its default is marked (WB-28) and counted (WB-03), and a study's overrides are listed with it (FR-34) |
| WB-33 | What the frame is built from | The author, asked whether the frame is rebuilt on the components NiceGUI ships through Quasar before the suites, after asking for "only long-term viable solutions and re-use of existing components/templates/frameworks where possible": "Rebuild on Quasar first" | §8.2.34 AJ1 |
| WB-34 | Building against using, and where physics lives | The author, marking the suites: "I wonder if we need to make a further distinction in the suites between those that build components (molecular, continuum, physics), those that use components (study, analysis?)". Asked, the author chose physics as a reusable model, then five suites in two groups, and on its contents: "I think the physics suite should allow you to build/edit the actual equations, the effectively build the physics part. It should then allow for exposing certain relevant knobs and parameters to the other suites (like concentrations, bias voltage, etc). Kind of like in COMSOL, but with an extra "interface" layer to the other suites." Put back against S3 and S7: "Suite now, composer next" | §8.2.34 AJ2 to AJ4. Amended by WB-43: six suites, Meso second in the Build group |
| WB-35 | The "interface layer" between the suites | "Knobs first, rest reachable" | §8.2.34 AJ5 |
| WB-36 | Showing what changed, and the project's name | The author, marking the changed list: "Spacing seems very generous. How is this kind of change tracking typically done in programs like `nanopnp`?", and on the name: "looks like a menu item". Shown how VS Code, JetBrains and COMSOL do it: "Mark, filter and dense table" | §8.2.34 AJ7 |
| WB-37 | Which settings, where they are kept, when they apply | The author, marking the settings: "The settings window should have a navigation menu on the left, with search, and a settings panel on the right. Much like how this is done in Claude Code and other IDE editors. Further, we should discuss and brainstorm on which settings we should include, and how they are stored and applied." Asked: "One declared list, two scopes", with appearance and accessibility, keyboard and editing guards, runs and storage, and units and numbers, adding: "Compute settings, network settings, ... I think we need to do some research here." At WP5.15's plan, after a survey of COMSOL, ParaView, ChimeraX, VS Code and JupyterLab: compute settings with threads per solve, no network settings yet, and the larger list with the store's clean-up, as two actions | §8.2.34 AJ9; §8.2.38 AN1 to AN5 |
| WB-38 | How a suite is designed | The author, marking the charge screen: "Looks very rudimentary still. I think we need to discuss a bit on how the design and functionality can go hand in hand." Asked: "Prototype on 2WCD, then build" | §8.2.34 AJ8 |
| WB-39 | The Molecular round: where a pane stands, the charge colours, the settings, the folded bar | The author, marking the Molecular drafts on 2WCD (`reviews/2026-11-11-molecular.md`): "Pane to the left. Consistency is key."; "in biochemistry, blue is positive and red is negative", and asked how far, "Everywhere, and choosable"; on the settings, "Window over the tool. When working, I don't want to navigate away from the tool to change a setting"; on a tool's two actions, "why not both side-by-side?"; on the folded bar, icons with state | Every tool's pane is on the left of its view. Charge and potential draw positive blue and negative red in the 3D view, on the maps and in the figures, the direction a setting (amends WB-20's diverging default). The settings open as a window over the open tool (amends WB-37's page). A tool's saving action and its build stand side by side. Folded, the activity bar and rail are a strip of the suites' icons, each with its state |
| WB-40 | The Molecular round's second marks: the stages, the word for a stopped build, a suite's icon, the membrane, a file picker | The author, marking the finished tools (`reviews/2026-11-12-molecular.md`): "the step cards should just be merged in with the tool menu items, including the progress bar"; of "refused" and "refusal", "it sounds forced", and asked for a word, "Blocked"; of the suite's page of links, asked what its icon opens, "The last tool"; "Perhaps we can put upper+lower leaflet, and make sure this is synced somehow with the continuum membrane position/thickness?", and asked how, "Draw the study's leaflets"; "I would like to add the browse button still here", and asked which, "Both" | Each tool in a suite's list is a card with the state of the stage it builds, that state's word and, while it builds, a thin moving bar along its foot; the pane has no stage bar. A build a check stops is *blocked*: the state's word, the card's title, "blocked by the axis check", and the problems list; a field it names reads "See the message above." (amends WB-20's and WB-12's word). A suite's icon opens the tool last used in it, its first the first time; a suite whose first tool has no page yet keeps its own page. Prepare draws the membrane's two leaflets, at the centre less and plus half the thickness of the first study that names the model, else the schema's defaults, names that study, and warns where the prepared registration residues sit off its centre; the continuum model stays the one place they are set. *Open structure…* takes a file from the system's own picker, copied into the project's inputs; the workbench's own browser, which returns a path, comes with the project dialogs (REV-235). A model read from a PQR file draws its atoms in View, coloured by their residues' charge |
| WB-41 | The Continuum round: one geometry tool, Region's domains, the mesh's parts, the tool list | The author, marking the Continuum drafts (`reviews/2026-11-12-continuum.md`): of Contour, "Can this not be merged with protein geometry?", and of its name, "Maybe this should be more general "Pore geometry"?", and asked, "Merge as Pore geometry"; of Region, "it should be expanded to allows visualisation and editing of ALL regions, including membrane and reservoirs [...] allow each domain to be selected separately", and asked how far now, "Domains now, CAD later"; of the sizes, "Let's brainstorm further on this", and of three drawn layouts preferred the tree, "I like this because it is also extensible"; of the tool list, "Maybe a more subtle approach with the Just the tool name on the left + status symbols/dots on the right? When selected, it should have a different background shading." | Continuum's tools are Pore geometry, Region and Mesh. Pore geometry builds stages 2 to 4, draws the maps and the outline, and edits the outline in its own pane (WB-15's fold, the contour with it); for a model that supplies its outline it draws and edits that one, its stage 2 to 4 values read-only. Region draws each domain as its own shape, the membrane stopping at the protein, and a domain picked brings its values to the pane; the CAD tooling comes with the sketcher (FR-42; REV-244). Mesh lists its parts as a tree, the domains and the boundaries, then the global size, each with the size it gets and its source; a part picked is drawn and opens its one field. A suite's tool list is a list of rows, not cards: the tool's name on the left, its state's glyph on the right with the word in its name and tooltip, the selected tool shaded, a building stage's bar along its row's foot (amends WB-40's card). Amended by WB-43: Pore geometry's maps and outline are Meso's Density and Outline, and Continuum's tools are Region and Mesh |
| WB-42 | The Physics round: the equations set as mathematics, the geometry under the boundaries, two plots, the status colours, plain words | The author, marking the Physics drafts (`reviews/2026-11-16-physics.md`): of Equations, "Can we write and render the equation with LaTeX (or a better equivalent)? Consistency is very important."; of Conditions, "I would not use the mesh for the BCs, but just the final geometry." and "Perhaps we can have a checkbox "Show mesh""; of Electrolyte, "Add second plot for wall distance (2 rows likely fits best)", and of four drawn axes, "B. is fine"; of a refusal, "Can we enforce simple sentences in ASD-STE100 language? For the colors: - if it is blocking --> red (=error), - if it is not blocking --> orange (=warning), - if it is informational --> blue (=info)", and asked, "Rewrite library texts now"; of *Expose*, asked, "Physics only, discuss the rest" | Every equation and boundary condition the workbench shows is LaTeX drawn by KaTeX, written whole with its corrections, and a table under it defines each symbol with its unit. Conditions draws stage 5's region with each boundary role along its named edges; *Show mesh* draws the stored mesh over it. Electrolyte draws two plots, one above the other: the factors against the concentration driver on a square-root axis, then against the distance to the wall. Status takes three colours, each with a glyph: red and ✕ for what blocks a run, the warning colour and ● for what does not, blue for information, a building stage's ● among it (amends WB-20). Messages, the library's refusals among them, follow ASD-STE100's writing rules (FR-35's NOTE). A physics model's exposed values are edited in Exposed values alone (REV-252) |
| WB-43 | The Study round: a bridge suite between Molecular and Continuum | The author, marking Charge on the mesh (`reviews/2026-11-18-study.md`): "Should this tool be part of the Study suite, or of the meso-scale suite? I'm not sure what it would be used for in the study... Let's discuss what the purpose and goals of this tool are, and take it from there."; asked, "With meso, I really meant a new suite that forms a (potentially bidirectional) bridge between the molecular and continuum suites. Another tool that could fit there is the contour creation tool. I want you to take a holistic look at the suites and their tools, and give me your opinion."; shown the view, "Yes, in its own package" | A bridge suite, in the Build group between Molecular and Continuum, holds *Density*, *Outline* (the outline's creation and edit, from Pore geometry) and *Charge map* (from Study's Charge on the mesh). Each pairs Mol* with the (r, z) view, linked both ways: a residue finds its patch, a point its residue, an edited outline the atoms it cuts. It adds no kind of model. It is built in a package of its own, with its own round; until then Charge on the mesh stays in Study (§8.2.42 AR8; REV-259). Amends WB-34 and WB-41 when it lands |
| WB-44 | Mol* beside an (r, z) view | "Mol* should definitely look at the side view, and likely even better a cross-section or a single sub-unit."; asked, "Both, a toolbar switch" | Mol* beside an (r, z) view opens side on, the near half of the pore cut away at the axis, so it shows the map's cut. A *One subunit* button in its toolbar shows chain A alone, and back |
| WB-45 | Where a run's convergence is drawn | Of the run unfolded in the queue: "I think the rungs plots need to move to a main window somehow. To be discussed how best to implement."; asked, "Runs tool's main view" | A run picked in Study › Runs, or opened from its queue line, draws its convergence across the main view, a running one updating; its rung table stands in the pane. The queue's line no longer unfolds to the plot (amends RE2) |
| WB-46 | Overview's case, the sweep's two modes, *New study* | Of Overview: "I would show only what is set, with the option to unfold to full."; of Sweep: "Can we implement two ways to run the sweep in case of multiple variables: 1) every combination possible 2) as a stepped list, where each variable must have a list of the same length (or a single value, and then it is kept constant)", and asked of its view, "A table in both modes"; of *New study*: "+ icon is sufficient." | Overview shows the values the models and the study set, with *Show the whole case* unfolding the resolved case. A sweep runs *Every combination* of its axes, or a *Stepped list* whose values step together, each a list of one length or one value held constant; its view is a table of points in both modes. *New study* is the + beside the study's select |
| WB-47 | A field's message, its text and a field of several boxes | Of REV-256's mockups: "Keep the "Today" variant for the Error, the Proposed for the box." | A field's message stays under its box (WB-12). The box's text is drawn at its label's size. A field of several boxes is one box with shaded rows, each row keeping its own changed mark, reset and default, the box a 3:1 edge (REV-256) |
| WB-48 | Where a molecular or continuum model's exposed values are chosen | Asked at the Study round (REV-252), "A list tool per suite" | Molecular and Continuum each have an Exposed values tool, as Physics has, with *Expose* at its head; no field carries an *Expose* checkbox |
| WB-49 | The Meso round: the charge map's range and dark middle, the structure's look, the overlay | The author, marking the Meso drafts (`reviews/2026-11-19-meso.md`): of Charge map, "Charges are barely visible on the map. Maybe needs adjustable ranges? On the structure: having some display options like molecular surface, sticks, spheres, etc. would be good. In cartoon mode, selecting a residue could change the style of the side-chain to sticks or spheres for example. Think about this yourself, and then give me options."; asked, "Clip, and let me change it" and "On all three Meso screens"; of a picked residue, "Solve this in a holistic way, offering the ability to change/configure the representations in a flexible way", then "A free list of layers"; of the dark theme, "middle on dark"; the other picks kept | Meso's charge map, the lattice and the deployed charge, opens its colour scale on the 99th percentile of the charge's size; a *Map range* field sets it, and the bar's ends read ≤ and ≥ where values pass them. On the dark theme the map's diverging scale runs through a dark middle. Each Meso tool sets how Mol* draws the structure (*Structure*: Cartoon, Ball and stick, Spheres, Surface), kept per tool for the window; a free list of the structure's layers, each with what it draws, its style, its colour and its opacity, comes in a package of its own (REV-265). The suite keeps its name, *Meso*, and the pair its width; the charge in 3D and its mean about the axis are kept (AT2); the residues stay a strip of buttons; the mesh's edges stay on; Outline gains no radius against z and no vertex list |
| WB-50 | The Analysis round: the 3D view, the map's outline, *Side by side*, the rebuild and the rungs | The author, marking the Analysis drafts (`reviews/2026-11-20-analysis.md`): of the 3D view, "1) map's scale 2) on 3) not sure I understand what you mean 4) background follows theme 5) Switch is fine, but it is a very large button now. I think for these kind of switches we need a more subtle, space-efficient solution.", and asked, "Open on the pore"; of the map, "No global percentile for now", asked, "Keep as built", and "Showing the outline can be an toggled option"; of *Side by side*, "Maybe this could also be made in a \"mirrored\" configuration, with one solution on the left (mirrored), and the other one on the right, all in the same plot."; of the rebuild, "Not sure what the value of this is", and asked, "Keep, as 'Solve again'"; of Runs' rungs, "The rung descriptions look like pieces of text, while it seems it may be better shown as a table?" | The explorer's field tile switches *Map* and *3D* with a small switch in its title bar, as Comparison's views do in its pane: the frame's switch at the heading's height. The 3D view opens on the map's colour range (a component's vector on the renderer's own; a comparison's pair on the side-by-side scale), handed to the renderer high to low where positive is blue, so its signs read as the map's (WB-39), with its wireframe, on the pore's close-up, *Whole domain* on request, its background the theme's. A map's scale keeps the 99th percentile of what the close-up draws (WB-49). An *Outline* option draws the fluid's boundary off the axis over a map. Comparison gains *Mirrored*: the two runs as one map, the first reflected about the axis, on one scale, the cut and the probes on both sides. A cleaned run offers *Solve again*, which says it takes as long as the first solve; its check speaks only when a number moved (QR-08). Runs' rungs are a table, *Rungs* (WB-52); a click places the cut or a probe to 0.01 nm |
| WB-51 | Analysis as an editable tree of results, and the charts' library | Of the explorer: "a lot of screen real-estate is being given to the \"Results\" explorer tool settings. This should be more efficiently organized. Perhaps a good way would be to organize the different views into an customizable editable tree, like it is done in COMSOL. Plots and graphs would be generated using different plotting tools (surface, scatters, etc) based on existing/newly defined variables/constants. This will likely need a new grilling and a dedicated WP."; of the probes, "Pane of their own, like in COMSOL."; of the quantities, "Make the QoIs which are shown customizable."; of uPlot, "Let's revisit the uplot choice, it seem to be rather limiting in capabilities. Given the scope of the kind of plots that we need create here, we should explore alternatives."; asked where, "New package, before speed", and which library, "Decide with the tree" | A design round puts the tree to the author, then a package of its own builds it after WP5.21 and before the performance package (WP5.24; both moved by §8.2.47 AW1, and Phase 7's since §8.2.49 AY1), which times the tree: groups of plots over a run's existing and newly defined variables and constants, probes in a pane of their own, the quantities shown chosen. The round chooses the chart library from the plot types the tree needs (AU1 restated there; NiceGUI ships Plotly and ECharts); WP5.21 ships its tiles and uPlot as they are (REV-268) |
| WB-52 | The workbench's wording | Of Runs: "\"Its rungs\" --> \"The rungs\": I would like to remove these kind of \"way-of-wording\" throughout the package (other example: \"What the model shows.\", \"Study's Runs starts one\"). Let's discuss how."; asked how, "Examples first"; marking the examples and the draft rule, "take" on each | The words follow five rules (*Look and feel*): plain noun phrases for titles, headings and labels; no "its" where the noun reads; no clause as a heading; a pointer is a link saying what to do there; short active sentences, ASD-STE100 for messages. The sixteen strings taken are applied in WP5.21 (*Rungs*, *Physics model*, *Boundary conditions*, …); the polish package (WP5.26, moved by §8.2.47 AW1, and Phase 7's since §8.2.49 AY1) sweeps every other screen's text by the rules, with a check (REV-269) |
| WB-53 | The Analysis round 2: the mesh view, the map drawn whole, the outline, charts above numbers | The author, marking the Analysis suite as it went to merge (`reviews/2026-11-20-analysis-2.md`): of the field tile, "The field should not be cut off within a small rectangle, but shown fully."; of the outline, "Outline line width is too thick. It should show the full outline."; of the cut, "Put graph at the top, values below."; of the 3D view, "This seems to be mesh and mesh Quality colouring, not 3D?" and "This is mesh view, not 3D?"; asked what the view should be, "Mesh now, 3D in tree" | A map is drawn over the whole domain, or a comparison's over the fluids' overlap, on the close-up's scale beneath the close-up, so the field fills the view past the pore; the view still opens on the pore. The outline is drawn 1 px wide with a 1 px halo, whole, to the domain's edge. The explorer's charts stand above its numbers: the field, the I–V, the axial cut, then the quantities. The view of the field on the solve's (r, z) mesh, drawn face-on by the renderer, is named *Mesh*, not *3D* (*Map · Mesh*; Comparison's *Mesh*). A true 3D view, the (r, z) field turned about the axis and cut open, is one of the plot types REV-268's design round puts to the author |
| WB-54 | The tree's branches | Asked how the Analysis suite's tree of results is organised, over boards T1 to T3 (`concepts/tree/`; `reviews/2026-11-21-tree.md`): "COMSOL's branches (T1)" | Analysis is one tool, the tree of results: *Data* (a run, a sweep's runs, a comparison of two runs, a revolution about the axis), *Definitions*, *Probes and cuts*, *Quantities* and *Plot groups*, each plot group naming its data. A comparison is a Data node, not a tool or a project item of its own (amends WB-04; FR-32), and the tree takes the tool list's place in Analysis (WB-07) Data's single run is reopened by the verdicts (REV-273). |
| WB-55 | Where the tree and its settings stand, and how many plot groups show | "One, or two side by side"; "Under the tree" | The selected plot group fills the view; *Split* pins a second beside it, such as a map and the line along its cut, so link 3 redraws in sight; the split is saved in the layout (WB-13). The tree and the selected node's settings stack in one 300 px column on the left of the view (WB-39) Reopened by the verdicts: an editor-like view area and a properties pane of its own (REV-273). |
| WB-56 | The plot types | Over board P1: "Every type on P1" | A 2D group layers a surface, contours, arrows and the outline, and draws two runs mirrored, side by side or as their difference; a 1D group draws a line along a cut, a probe's value against a swept value (a point graph), or a quantity against a swept value as lines or markers; a 3D group turns the (r, z) field about the axis, a quarter cut away (WB-53). Each reads what the library samples, with its Tier 1 test (RSK-15). Streamlines come later |
| WB-57 | The chart library, its reach and the mesh view | Over boards L1 and L2: "Plotly"; of its reach, "Every plot and every map" (*against the recommendation*, every plot with the canvas kept for the editors), then asked which maps, "Every (r, z) view", and where, "All in WP5.22" (*against the recommendation*, each with the package that reworks it); of the mesh view, "A layer; webgui leaves" | Plotly (plotly.js 3.1.1, MIT, as NiceGUI ships it, unmodified; CON-09) draws every chart and every (r, z) view: Analysis's tree, Electrolyte's two plots, Runs' convergence, Meso's Density, Outline with its editor and Charge map, Continuum's Region and Mesh, and Physics' Conditions. uPlot (restating AU1), the shell's canvas and NGSolve's `webgui` leave, so each kind of picture has one renderer (REV-137). Plotly's own toolbar is hidden for the workbench's (WB-24); a square-root axis is drawn as its root with ticks in its own units. *Show mesh* draws the solve's mesh over a 2D group, as WB-42's does. WP5.22 moves every view, with a round of verdicts on Meso, Continuum and Physics; WP5.24 times the 200 ms line on Plotly (WB-23) |
| WB-58 | Variables and constants | "A library list and expressions" | *Definitions* holds constants (a number with its unit) and variables, picked from a list the library registers (space charge, flow speed, each ion's current density) or typed as an expression of the fields, the constants, r, z and the run's quantities, parsed by the study variables' whitelist with units checked (AG2). The library evaluates a variable at each sampled point, each field read by its cell's P2 basis (REV-270); the shell computes nothing (QR-13; RSK-15) |
| WB-59 | The tables and the quantities shown | "Bottom panel tabs"; "Checked and ordered in the node" | *Probes*, *Quantities* and *Cut values* are tabs of the bottom panel beside the queue and the log (amends WB-02's panel); a probe's r or z typed in its row moves it on the map. The Quantities node lists every quantity a run records, each checked and ordered by drag or by keyboard, saved with the tree; a new tree shows the current, the conductance, the transport number, each ion's current and the bias |
| WB-60 | How the tree is saved | Asked of one file per plot group, "I option 2 more scalable?"; shown that the tree holds settings only, so either form loads at once, and that a file per group merges and copies better at the cost of a check across files, then asked again: "One results file per project" (*against the recommendation*, a results folder with a file per plot group) | One tree per project, in `results.yaml` (`nanopnp/results/v0.8`, the release that ships it: G6; §8.2.47 AW1; §8.2.49 AY1) beside the project file: its Data, Definitions, Probes and cuts, Quantities and Plot groups. A project's `comparisons/` files are read once into its Data, and the folder goes (FR-32; F4) |
| WB-61 | The run a link opens, and the run shown | "Shown run becomes it"; "Newest, until a run is picked" | Link 4 opens a run as *Data › Shown run*: a done run's *Result*, a recorded run in Study › Runs and a point of the I–V each retarget it, and every plot group following it redraws. Shown run follows its study's newest run until a run is picked; *Follow newest* restores that Reopened by the verdicts: Data holds every run (REV-273). |
| WB-62 | The tree before the user builds one | "Defaults from what the run provides" | On first opening, `results.yaml` is written with *Shown run*, the study's sweep if any, and a plot group for each thing the run provides: the potential, each ion's concentration, the flow if solved, the line along the axis, and the I–V when the bias is swept; then the six quantities. The defaults follow what the model declares (AH1), never its name, so QR-10's route opens on a result |
| WB-63 | Two runs in one view, and a run's name | "Mirrored first, all three kept"; "A label, else by what differs" (*against the recommendation*, by what differs alone) | A 2D group over a comparison opens *Mirrored*: the first run reflected to r < 0, one scale, the cut and the probes on both halves; *Side by side* and *Difference* stay its other views. A Data node may carry a label the user types; otherwise a run is named by its study and the values it sets away from the study's own ("2wcd-charged, −50 mV"), told apart by its time where two are alike, the folder's digits in its tooltip and in *Open in Runs* |

## Glossary

The one glossary every technical term in the workbench links to (WB-25). Physics terms are the knowledge
base's and the specification's; these are the workbench's own.

| Term | Meaning |
|---|---|
| Artefact | What a stage writes: typed, stored, keyed by the hash of its inputs and settings (FR-27) |
| Blocked | A build a check stops, or a value the library declines at its field, shown with the rule, the value, the case path and a remedy (WB-12, WB-40) |
| Case file | One complete description of a run, which the command line runs (`nanopnp/case`); the unit of reproducibility |
| Changed mark | A filled diamond on a value set away from its default; an outlined one on a study's override (WB-28) |
| Comparison | Two runs as one Data node of the tree of results, drawn on one colour scale, mirrored, side by side or as their difference (WB-04, WB-54, WB-63) |
| Continuum model | A library item built in the Meso and Continuum suites: the pore's outline and charge drawn from a molecular model, the region and the mesh (WB-11, WB-34, WB-41, WB-43) |
| Data node | A node of the tree of results naming what a plot group draws: a run, a sweep's runs, two runs compared or a revolution about the axis (WB-54) |
| Default mesh sizes | The element size each part of a generated mesh takes when none is typed: global 10 nm, protein 0.1 nm, electrolyte 2.8 nm, the reservoir's arc 5 nm, the pore's axis 0.075 nm, and the wall a fifth of the Debye length, at most 0.05 nm; the size scale multiplies each (WB-41) |
| Exposed value | A value a model declares for the other suites, with its name, unit, range and default, such as a physics model's concentration and bias; the Study suite lists it first (WB-35) |
| Gate | A check a stage passes before its artefact is used, such as the orientation gate or the mesh's quality gate |
| Later phase | A tool drawn with its banner and no working control: designed, not built in v0.6 (S7) |
| Library | The project's models and studies, each reused without being rebuilt |
| Live link | Two views that select together until unlinked (S6; WB-06) |
| Meso | The suite between Molecular and Continuum that draws a continuum model's pore and charge from the molecular model it is built over, beside the molecule; it adds no kind of model (WB-43) |
| Molecular model | A library item built in the Molecular suite: the prepared structure, its ensemble and protonation (WB-11) |
| Override | A value a study sets in place of a named model's, for a sweep or a ramp; any value of the models it names, their exposed values first (WB-35). It is recorded in the manifest beside the model's value, and a value equal to the model's is none (WB-16; FR-39; §8.2.31 AG12) |
| Physics model | A library item built in the Physics suite: the equations chosen from the registry, the electrolyte, the boundary conditions and their discretisation, reused across pores (WB-34) |
| Plot group | A node of the tree of results that draws one view of its data: a 2D map with its layers, a 1D plot or a 3D revolution (WB-54, WB-56) |
| Project | The folder that holds the library, the runs, the store and the project file (S11) |
| Queue | The builds and runs waiting, running and done, always on screen (WB-02, WB-03) |
| Resolved case file | The one complete case file a study's run resolves to, written with its manifest (FR-25) |
| Route | A guided path through the suites, a layer over them (WB-08) |
| Rung | One step of the continuation ladder, from an easy problem to the one asked for; a run shows "rung x of N" (WB-23) |
| Schematic | A drawing that shows where a field lies, not its values |
| Store | Where artefacts are kept, keyed by their hash |
| Study | A Study-suite item pairing one molecular, one continuum and one physics model with its overrides and sweep, and running it (WB-11, WB-29, WB-34) |
| Suite | One of the six parts of the workbench: Molecular, Meso, Continuum and Physics, which build models, and Study and Analysis, which use them (WB-02, WB-29, WB-34, WB-43) |
| Switch | A setting away from its validated default, recorded in every result's manifest (FR-25) |
| Tool | One task in a suite, with its settings docked beside its live view (WB-07) |
| Tree of results | The Analysis suite's one tool: Data, Definitions, Probes and cuts, Quantities and Plot groups, saved in `results.yaml` (WB-54, WB-60) |
| Variant | A model derived from a parent and shown as its difference from it, such as a residue's charge changed (WB-04) |

