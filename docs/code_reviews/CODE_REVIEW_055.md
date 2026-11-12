# Code review 055: WP5.17's plan, the Continuum suite

2026-11-12 · PR #184, branch `claude/nice-franklin-h4k3zg`, the plan commit `7b90537` on `c6b85ce` · scope: the commit's
13 files. The plan was read in full against the code it names: `geometry/region.py` (`read_region`, `write_region`),
`geometry/pore.py` (`CylinderPore`, `IdealisedRegionRecord`), `geometry/analyte.py` (`PoreWithAnalyte`,
`AnalyteInBoxGeometry`), `mesh/primitives.py:CylindricalPoreGeometry`, `mesh/idealised.py`, `mesh/defaults.py`,
`mesh/generate.py:generate`, `mesh/ingest.py` (`MeshStage.key`, `_recipe`, `_sizing`, `forecast_parameters`),
`mesh/sizing.py:SizeTable`, `charge/stage.py` (`check_stored_frame`, the fields stage), `plot/data.py` (imports,
`region_drawing`), `pipeline/checks.py` (`_check_profile`, `_check_pore`, `_check_solid_permittivity_keys`,
`_check_physics_switches`), `pipeline/run.py:selected_stages`, `core/stages.py`'s inputs of region, mesh and charge,
`io/resolved.py:deposits_charge`, `io/case.py` (`Mesh`, `Electrolyte`), `io/artefact.py:CaseArtefact`,
`io/models.py:_merge_all`, `io/project.py:ProjectFile`, `api/project.py` (`BUILD_LAYER`, `BUILD_UPTO`, `kept_artefacts`,
`_built_stages`, `_build_case`, `_checked_write`), `api/case.py:Case.cylinder`, `gui/geometry.py:ProfileEditor`,
`gui/assess.py:AssessRequest`, `gui/web/` (`screens.py`, `pages.py`, `frame.py:Route`, `tools.py`, `molecular.py`,
`states.py`, `__init__.py`), `tests/conftest.py:prepared_2wcd`, `tests/tier1/test_gui_viewmodels.py` and the VER-62
walk files. VER-62's clause, ruling record 40 and `.claude/skills/np-plan/wp.md`'s caps and sections were read against
the plan · level: high, with `--fix` · status: completed.

Static review (`/np-plan wp 5.17 review`). No test and no gate ran; the review turn gates afterwards. Word counts after
the fixes: 3,229 in all (cap 3,850), 1,647 outside Grounding and Implementation details (cap 1,650), 648 in
Implementation details (cap 1,100), 273 in the In brief (cap 275).

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | High | Implementation details, item 5 | `_build_case` merged the paired molecular model's body, its `structure:`, under every continuum model; `pipeline/checks.py:_check_pore` refuses `structure:` beside `geometry.pore`, so an idealised continuum model built alone would be refused, against AP2 and the FR-39 row | Fixed: the molecular body is merged only where the continuum body holds neither `geometry.pore` nor `inputs.profile`, as AP2 reads; D4's grounding adds the refusal |
| 2 | Medium | D1's grounding; item 1 | Six class-branch sites were named. Missed: `generate`'s third branch (the `exclusion` flag), `charge/stage.py:check_stored_frame` (the membrane's centre, 0.0 for a pore) and the fields stage's narrowing assert; `RegionOutlines` had no centre for the frame check | Fixed: nine sites named; `RegionOutlines` adds `membrane_centre_z_nm`, which `check_stored_frame` reads; `generate`'s one `match` picks recipe and mesher, its flag `record.has_exclusion`; the assert stays, guarded by the case's refusal |
| 3 | Medium | Implementation details, item 2 step 4 | `mesh_pore_with_analyte` was built over `geometry.shape()` with no `size_wall`, and `PoreWithAnalyte.shape` kept passing `wall_h_nm` to a `name_edges` that no longer sizes: the force benchmarks' meshes would move, and step 8 would fail with no instruction | Fixed: `PoreWithAnalyte.shape` loses `wall_h_nm`; the function, in `mesh/primitives.py`, calls `size_wall` before `GenerateMesh(maxh, grading=0.2)` |
| 4 | Medium | Verification, VER-62 row | The command omitted `tests/tier2/test_exclusion_2wcd_walk.py`, which holds VER-62's shell walk | Fixed: added |
| 5 | Medium | Implementation details, item 5 | `merge_layers` was "`_merge_all` made public" with one list, but `_merge_all(models, study)` takes a study apart | Fixed: `merge_layers(layers)` is the fold that `_merge_all` calls with the study appended; D4's grounding gives the signature |
| 6 | Medium | Verification, `test_region.py` row | The Tier 1 oracle said the 2WCD charge chain walks; protonating the dodecamer alone takes about a minute | Fixed: the oracle is the stages `selected_stages` holds; the Tier 2 null-edit test walks |
| 7 | Low | Work item 2 | The Sonnet item amended VER-61's normative text; `wp.md` keeps normative judgement on `main` | Fixed: item 3, on `main`, amends VER-61 |
| 8 | Low | In brief | A typed size failing the quality check was said to be refused "at its field"; the gate runs at the mesh's build and names a gate, not a case path | Fixed: "refuses the build" |
| 9 | Low | In brief | "the original charge exactly" against the Tier 2 oracle's 10⁻¹² relative | Fixed: "to twelve digits" |
| 10 | Low | Implementation details, item 5 | The pair was added to `_built_stages`' key, whose stamp already hashes the merged case text and its input files | Fixed: the stamp is kept; D4's grounding says why |
| 11 | Low | D5's grounding | `numerics.mesh.sizes` enters `CaseArtefact`'s hash over the whole dump, so every case artefact's and run's key moves; the grounding said only that stages 1 to 6 do not | Fixed: D5's grounding states it and the PR is to say so |

No finding changes a ruling of the author.
