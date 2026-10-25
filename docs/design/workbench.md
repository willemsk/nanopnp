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
bar or unit, and the status bar keeps "running" after a run ends. The author's verdict on each
screen, keep, change or drop, follows here once collected.
