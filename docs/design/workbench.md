# Workbench design

The design of the browser workbench that replaces the Qt desktop shell in v0.6 (Phase 5,
§8.2.17 S1 to S24). This document is written by the WP5.01 design study: today's shell first, then
the design round with the author, the areas and the requirements. Until the study ends, only the
sections below are settled.

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
(REV-135).

## Decision log

The design round's rulings, in the author's words where they gave them (§8.2.17 S21). The
organisation round ran on 25 October 2026 over four concept boards, C1 *model builder*, C2
*molecular workspace*, C3 *project and runs* and C4 *guided routes*, kept in
`docs/design/concepts/`; the author ruled for a hybrid in the round, the marks on the boards following later.
Each ruling was played back and confirmed. The look-and-feel round followed the same day over a
style tile of three directions, *instrument*, *notebook* and *molecular*, kept in `docs/design/style/`;
its tokens are `docs/design/tokens.css`.

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
| WB-18 | Density | Medium, adjustable | 13.5 px type and 30 px rows by default; a compact setting of 12.5 px and 26 px, saved per user |
| WB-19 | Theme and default | Both themes, following the system | Light and dark, both held to WCAG 2.2 AA; the default follows the operating system, with a switch |
| WB-20 | Accent and colour maps | One accent and semantic colours each with a glyph; "User-chosen maps" | One accent for selection, the primary action and focus; built, stale and refused in green, amber and red, each with a glyph and a word. viridis (cividis for colour-vision deficiency) and a diverging map centred on zero with its unit are the defaults, charge always opening diverging (VER-60); any Matplotlib map may be chosen per plot, rainbow included, and the plot records which |
| WB-21 | Type, numbers and units | One sans and monospace numbers | Inter, shipped with the application; numbers in tabular figures, a narrow no-break space before the SI unit with an engineering prefix (1.234 nS), scientific notation only where no prefix fits; sizes in rem with a 12 px floor |
| WB-22 | Icons | Icon with text; icon alone with a tooltip in dense toolbars | One open-source icon set across the suites; every icon-only control has an accessible name and names its shortcut |
| WB-23 | Motion | Functional only | Under 200 ms, none under reduced motion; a run shows "rung 7 of N", never a percentage the solver cannot report |
| WB-24 | Accessibility and the keyboard | WCAG 2.2 AA, full keyboard | Non-text contrast of controls, focus rings and colour bars included; a keyboard path for every canvas action, a residue picked from a list as on the canvas; the render check gains a non-text contrast measure. A quality requirement in the specification |
| WB-25 | Tone and glossary | Plain and precise, with a glossary | A refusal states the rule, the value entered, the case path and a remedy; each technical term links to one glossary |
| WB-26 | What the pictures are drawn on | Black for the 3D view, the theme for plots | The Molecular suite's 3D view is always near-black; (r, z) views and plots follow the theme and export on white; every colour bar is outlined at 3:1 so its low end never dissolves |
| WB-27 | The direction the tokens start from | The molecular direction, with instrument's dark theme | `docs/design/tokens.css` |
| WB-28 | The changed-from-default mark | Its own mark, on changed values only | A filled diamond in its own colour, never the accent, showing the default and a per-field reset; a study override (WB-16) an outlined diamond; the frame's count (WB-03) a button opening the list |
| WB-29 | Where studies are made | Its own suite. The author, picking on the choice panels (RE1): "Now that I see the organisation, I think 'Study' should be its own fully fledged suite next to Molecular, Continuum, and Analysis" | Four suites and a run queue: *Molecular*, *Continuum*, *Study* (pairing the models, the overrides, the sweep, the charge on the mesh, a run's progress) and *Analysis* (the results explorer and the comparisons). Amends WB-02 and WB-11; §8.1's Phase 5 row says so |

