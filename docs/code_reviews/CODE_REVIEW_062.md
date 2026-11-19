# Code review 062: WP5.20's plan, the meso suite

2026-11-19 · branch `claude/inspiring-carson-p9b9uc`, the plan commit `fdd812b` on `dbe34da` · scope: the commit's 11
files. The plan was read in full against the code it names: `io/project.py` (`Suite`, `SUITES`, `ITEM_SUITES`),
`gui/web/screens.py` (`Suite`, `Tool`, `SUITES`, `VIEWS`, `tool_for`, `SCREENS`), `gui/web/tools.py` (`BUILDS`, `_Pane`,
`tool_of`, `holds`, `subject`), `gui/web/builds.py` (`BuiltModel`, `_MODELS`, `_KINDS`, `refusals`, `build`),
`gui/web/frame.py` (`open_field`, `problems`, `problem_rows`, `mark_suite`), `gui/web/study.py`, `gui/web/continuum.py`,
`gui/web/molview.py`, `gui/web/assets/bridge.js`, the vendored Mol* 5.13.1, `api/project.py` (`BUILD_UPTO`,
`kept_artefacts`, `_built_stages`, `build_case`, `_build_case`, `molecular_for`, `_problems_of`, `_build_layer`),
`io/store.py` (`run_directory`, `evict`), `plot/data.py` (`residue_key`, `ResidueCharges`), `charge/kernel.py`
(`source_atoms`, `check_spacing`, `volume_density`), `charge/stage.py` (`gate_parameters`, `produced_gates`),
`charge/dielectric.py:_inside`, `density/stage.py`, `structure/read.py` (`chain_keys`, `select`),
`structure/stage.py`'s header, `geometry/region.py:_profile_identity`, `pipeline/case.py`, `pipeline/checks.py`,
`validation/apbs.py:write_dx`, `validation/charged_tube.py`, `.claude/scripts/gui/render_shell.py` and `redraw.cjs`,
`tests/tier1/test_gui_screens.py`, `test_study_charge.py` and `test_project.py`; VER-60, VER-78, FR-31, FR-33, FR-39,
§5.3.1's and §5.3.5's NOTEs; the ruling record §8.2.44, `holds-now.yaml`, the Phase 5 entry and record;
`.claude/skills/np-plan/wp.md` for the sections and caps · level: high, with `--fix` · status: completed.

Static review of a plan commit: no test and no `gate.sh` ran during the review. The review turn gates afterwards.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Important | Item 3; Verification row 3 | `charge_volumes`' default spacing of 0.3 nm is several times the deposit's kernel width (0.5 × the PQR radius, about 0.05 to 0.1 nm); stage 7 refuses a lattice above w/2 (`kernel.check_spacing`). Each Gaussian falls between nodes, the isosurfaces alias, and the row's "sums to the charge per frame to 10⁻⁶" cannot hold | Put to the author at the review: the overlay is drawn on a 0.2 nm grid, each kernel widened to at least 0.4 nm, both volumes alike (§8.2.44 AT4); a spacing above half the narrowest widened width raises; the test samples at a quarter of it |
| 2 | Important | Item 7 | Both volumes' default level is a tenth of `|full|`'s maximum; `revolved` peaks about `√π w / (2π r_i)` lower, a hundredfold at 3 nm, so its isosurface draws nothing | Fixed: each volume's level from its own maximum |
| 3 | Important | Item 5 | `_Pane.holds: ClassVar[ModelKind]` collides with the existing method `_Pane.holds(tool_id, problem)`, which `physics_tools.py` overrides and `tools.py` calls | Fixed: `_Pane.model_kind` |
| 4 | Important | D3; Item 5 | Routing by value misses `api/project.py:_problems_of`, which sets `Problem.suite` from `ITEM_SUITES` (api cannot import the screens), and `frame.py`'s problem rows and `mark_suite`, which use it: a refused `geometry.contour` value opens and badges Continuum. `BuiltModel.build` enters a build with `suite=self.kind`, so a Meso build marks Continuum running | Fixed: `Frame.problems` re-places each problem by `place`; a build's queue entry names its suite |
| 5 | Important | D3; Item 6 | `MesoModel` shares `ContinuumModel`'s `_MODELS` slot `(root, "continuum", name)`: a Meso charge build shows in, and blocks, Continuum's tools, its stage-7 refusal lands on them, and `refusals` rebuilds it as `ContinuumModel`, whose `paths` miss the charge's | Fixed: `BuiltModel.slot`, `"meso"` for `MesoModel`; `_held`, `_KINDS` and `refusals` key by it; `MesoModel.paths` the study's |
| 6 | Important | Item 2 | `_built_stages(kind, name, upto)` forms its case by `build_case` and caches by `(kind, name)`; "adds `_built_stages` over `charge_case`" has no seam, and the mesh and charge entries would evict each other, rekeying a walk at every `kept_artefacts` | Fixed: `_built_stages` takes the case and caches by `(kind, name, upto)` |
| 7 | Important | *Amended when it lands* | `charge_case` layers the molecular model under a supplied outline, where §5.3.1's NOTE says such a model reads none, and its record goes under the store's `runs/`, where §5.3.5's NOTE puts a run under `runs/<study>/`; neither NOTE was listed | Fixed: both NOTEs listed |
| 8 | Important | D4; Item 6 | The study graph's charge node opens a charge built at the build layer, without the study's overrides or physics (element order, solids), and writes *Built over* to the project file on a click; Study then keeps no view of its own charge. This changes what an existing user sees, and the plan decided it | Put to the author at the review: the plan's choice kept, a study's own charge shown nowhere (§8.2.44 AT3, against the recommendation, which was Charge map reading the study's run record) |
| 9 | Important | D6; Item 1 | Density's `nearest` ranks by "kernel widths" from the table's radius, but stage 2's widths are `geometry.density.sharpness` (0.93) times `resolve_protonated_radii`' CHARMM radii, and under `geometry.density.atoms: as_loaded` its atoms are stage 1's ensemble, not the protonation table (the grounding's claim held only for the default) | Fixed: `DensityAtoms` follows `density/stage.py` in both modes; the grounding corrected; the test row covers both |
| 10 | Important | D5; Item 1 | `ResidueCopies` maps the header's chains, which `chain_keys` may name by `segid` (`PROA`), to keys whose chain `residue_key` cuts to one character; under the channel axis mode the units need not number `n`. Either maps copies wrongly | Fixed: chains named as `residue_key` names them; a shared first character, or units other than `n`, stand alone; the test row adds a segid C3 |
| 11 | Important | Item 9 | The check `render_shell.py --only meso` lacks the output directory, so it prints its usage and exits 64; `redraw.cjs --help` throws "unknown option". The 2WCD cache is filled only for its four named groups, not `meso` | Fixed: the out-directory named and exit 0 required, `node --check` for the script, `meso` added to the cache's groups |
| 12 | Important | Item 6 | `states.boot_project` walks the first study, its record under `runs/<study>/`; Charge map reads the store's `runs/<c>-upto-charge-*`, so in VER-78's states and the `2wcd` render no record or deployed field is found | Fixed: `boot_project` also walks the charge case as `MesoModel.request` asks |
| 13 | Nit | Item 1 | "`charge_e`, the charge per copy the group's sum over copies" reads as the total, and the strip's threshold was left to either | Fixed: the sum divided by `copies`, the threshold on it |
| 14 | Nit | Verification row 3 | `full` is a Cartesian grid; its mean over 360 azimuths needs values off the nodes, which no named function gives | Fixed: `full_at(points)` |
| 15 | Nit | Item 1 | `Count(atoms, charge_e)` "per copy" over every frame left whether atoms are counted once per frame | Fixed: per copy and per frame |
| 16 | Nit | Item 3 | "The widths are `source_atoms`'" without saying the positions; `source_atoms` shifts z into the model frame, while the grid is in stage 1's | Fixed: `table.positions_nm`, unshifted |
| 17 | Nit | D1 | "Shortcuts follow the bar" moves every suite's chord after Molecular by one, a change an existing user meets (wp.md: the author's) | No change needed: AN7 rules that the shortcuts follow the bar, an existing user's chords moving with it; the round's question was removed |

The fixes keep both rulings (AT1, AT2); the author ruled findings 1 and 8 at the review as AT4 and AT3. The plan's
counts after the fixes and the rulings: 3,593 words; 1,632 outside *Grounding* and *Implementation details*, within the
cap with its allowance; *Implementation details* 982; the In brief 193. Nine decision rows, as before.
