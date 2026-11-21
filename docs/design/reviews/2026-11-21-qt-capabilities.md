# The Qt shell's capabilities in the workbench

WP5.27's capability check (D1; §8.2.47 AW7, AW11): each row Q01 to Q41 of the design document's capability list
against the screen the design document's *Tabs or areas* gives it, before anything of Qt is deleted. The shots are
the `shell` render of WP5.27's items 1 to 3 (`/np-gui render shell`, all groups, then the `study` group again with
the running, log and *More values* shots), light scheme unless named. A verdict is `present`, `present as ruled
(AW7)`, `carried (REV-274, point n)` or `missing`; a row carried shows the rest of its capability and leaves the
named detail to Phase 6. No row is `missing`. The `gui-reviewer` checked each row against its shot; where the capability sits below a
shot's fold, the row names the code that draws it, read in its place.

| Q | Capability | Where in the browser | Shot | Verdict |
|---|---|---|---|---|
| Q01 | Open one case, over a store | `nanopnp gui [<project>]` opens the project, its store in `store/`; a case is imported by `nanopnp project import` | `shell-2wcd-molecular` | present |
| Q02 | The title names the case | The project rail names the project and its models | `shell-2wcd-molecular` | present |
| Q03 | What was last started, or why it was refused | The status line's queue and problems; the Problems tab | `shell-study-tube-running`, `shell-refused-problems` | present |
| Q04 | Closing stops the builds | The server stops the queue and its child processes as it stops (`server.py:build_app`'s lifespan) | none: the code | present |
| Q05 | A typed field per case path | Each field in the tool that sets it; Study setup's *More values* for a path with no field | `shell-2wcd-p-electrolyte`; `shell-study-more-solver`, the path it wrote under *The study's own* (the list itself below the fold) | present |
| Q06 | A field checked as typed, refused at the field | A field's refusal under the field (WB-12); checked as it is typed, which a still shot cannot show | `shell-continuum-refused` (Isolevel), `shell-refused-c-region` | present |
| Q07 | Add an optional section | A section is written by the tool that uses it; *More values* writes any other path (`study_tools.py:more_values`) | `shell-study-more-solver` | present |
| Q08 | Validate and save before a build or run | *Run study* and each *Build* write and validate the case first; a refused one is listed in Problems | `shell-study-tube-running`, `shell-continuum-refused` | present |
| Q09 | Load a structure | Molecular, Prepare structure, *Open structure…* | `shell-2wcd-m-prepare-open` | present |
| Q10 | Build the geometry | Each Continuum tool's *Build*, queued | `shell-2wcd-c-mesh`, `shell-continuum-building` | present |
| Q11 | Cancel the build | The building tool's *Cancel* (`tools.py`'s `tool-cancel`) | `shell-continuum-building` | present |
| Q12 | The stage list | The tool list's status per tool | `shell-2wcd-continuum` | present |
| Q13 | Stage 1's alignment record | Prepare structure's *Built* readout: the axis found and each gate with its value (`tools.py`, the `prepare` readout), below the fold | `shell-2wcd-m-prepare` | carried (REV-274, point 5) |
| Q14 | Stage 2's density section | Meso, Density, with its colour bar | `shell-meso-density` | carried (REV-274, point 5) |
| Q15 | Stage 3's (r, z) map and its quantity | Meso, Outline, the reduced maps | `shell-meso-outline` | present |
| Q16 | The contour editor | Meso, Outline, *Edit outline*: a vertex moved by its typed r and z, inserted and deleted | `shell-meso-outline-moved` | present as ruled (AW7) |
| Q17 | *Undo*, *Redo* | *Edit outline*'s *Undo* and *Redo* | `shell-2wcd-m-outline-edit` | present |
| Q18 | *Measure criteria* | *Edit outline*'s *Measure*; each failed criterion a card "Fails the … check" (`meso_tools.py:show_assessment`), not shot | `shell-meso-outline-moved` | carried (REV-274, point 2) |
| Q19 | *Seed from refusal* | Outline's *Seed from the map* | `shell-meso-outline` | present |
| Q20 | *Save edit* | *Edit outline*'s *Save edit…* | `shell-2wcd-m-outline-edit` | present |
| Q21 | Stage 5's region | Continuum, Region, each domain picked | `shell-2wcd-c-region-domain` | carried (REV-274, point 5) |
| Q22 | Stage 6's mesh | Continuum, Mesh: parts, element count, the quality gate and histogram, the worst elements | `shell-2wcd-c-mesh-sicn`, `shell-2wcd-c-mesh-part` | carried (REV-274, point 5) |
| Q23 | Details pane and status line | A tool's *Built* readout and its gate line; the bottom panel's log | `shell-2wcd-c-mesh`, `shell-study-tube-log` | present |
| Q24 | Build charge | Meso, Charge map, *Build charge map* | `shell-meso-charge` | present |
| Q25 | Cancel the charge build | The building tool's *Cancel*, as for Q11 (a charge build's not shot) | `shell-molecular-building` | present |
| Q26 | Stage 7's list entry | The tool list's status | `shell-2wcd-meso` | carried (REV-274, point 5) |
| Q27 | Protonation | Molecular, Protonation: the residue states, Q<sub>net</sub>, the PROPKA warnings | `shell-2wcd-m-protonation` (Q<sub>net</sub> per frame), `shell-2wcd-m-protonation-states`, `shell-2wcd-m-protonation-warnings` | carried (REV-274, point 1) |
| Q28 | The charge map | Meso, Charge map, the lattice in (r, z) beside the molecule, linked | `shell-meso-charge-picked` | present |
| Q29 | The deployed field | Charge map's deployed charge | `shell-meso-charge-deployed` | carried (REV-274, point 3) |
| Q30 | Conservation | Charge map's *Conservation* section, its legs and charges (`meso_tools.py:conservation_rows`), below the fold; the worst planes in the map's key | `shell-meso-charge` | carried (REV-274, point 4) |
| Q31 | Run | Study setup's *Run study* | `shell-study-tube-running` | present |
| Q32 | Cancel the run | Study › Runs, *Cancel* on the running entry (`study_tools.py`'s `runs-cancel`) | none: the code; the running entry in `shell-study-tube-running` | present |
| Q33 | The stage reached | The running entry's line: "stage 7 of 9: solve, rung 9 of 17" | `shell-study-tube-running` | present |
| Q34 | The run's log | The run's lines in the bottom panel's Log, after the queue's (`runs.py:_queued`'s `poll`), below the panel's edge | `shell-study-tube-log` | present |
| Q35 | The live convergence plot | Study › Runs, the convergence across the view | `shell-study-tube-convergence` | present |
| Q36 | The rung notes | Study › Runs, the rung table | `shell-study-tube-convergence` | present |
| Q37 | The run directory | The quantities tile's *Folder* (`analysis_tools.py`), below the fold; *Open in Runs* | `shell-analysis-explorer` | present |
| Q38 | The quantities of interest | The results explorer's quantities tile | `shell-analysis-explorer-rebuild` | present |
| Q39 | The deviations | The quantities tile's *Changed from the validated default*, switches and contributed entries (`analysis.py:AnalysisModel.deviations`, tested), below the fold | `shell-analysis-explorer` | present |
| Q40 | The field list | The results explorer's field tile, its quantity chosen | `shell-analysis-explorer` | present |
| Q41 | The field view | The field as a map or on the solve's mesh, with its colour bar | `shell-analysis-explorer-on-mesh` | present |
