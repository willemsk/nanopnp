# Code review 046: WP5.12, the knowledge base and the guide

2026-11-10 · PR #175, branch `claude/wizardly-wozniak-353gtq`, head `0dddea8` on base `f818e91` · scope: the PR's
165 files, the code, tests, specification and guide changes read in full, the knowledge base by every added line
and by the paths and anchors it names · focus: each repointed citation against the clause or concept it names,
each number against its source (the thesis at `43d0f0f`, the code, the specification), what a cut paragraph's
pointer leads to, `markers.py`'s code-span skip · status: completed.

Static review (`/np-ship wp 5.12`, `/code-review xhigh --fix`). No test or gate ran; `/np-ship` gates the fixes.
Probed and found to hold: thesis eq. 5.23 is `eq:epnpns_distance_d` and prints `(d − P₂)`, counted from
`epnpns.tex`'s numbered rows; the line citations of `01/01`, `01/03`, `01/04` and errata E5 (`epnpns.tex`:815,
640-646, 665-666, 679-680, 844-848, 940-941, 963, 480); `D_Na(5.3 M)` from PHY-12's coefficients is 8.1134e-10;
§5.2's NOTEs on stages 1 and 2 exist and hold the rules the repointed messages cite; NUM-24's NOTE grounds cis, as
Appendix B's new row says; `09/08` §8.3 holds the 0.2 nm screened-Poisson measurement `physics/distance.py` cites;
errata E1 holds the 0.75 nm figure `physics/coefficients.py` cites; every repository path an added line names exists,
but for `tests/tier1/test_workflow_hooks.py`, cited through `git show 3782c43` as a deleted file; the guide's
commands (`nanopnp gui`, `project new|import|embed|export`, `store prune`, `reproduce`) and keys
(`geometry.density.atoms`, `electrolyte.corrections.diffusivity.model`) exist; the explicit anchors kept with old
slugs (`06/04` §4.3.3, `07/12` §12.1 and §12.2) are kept for inbound links. `links.py --anchors`: 0 broken paths
and the 7 known anchor misses; `markers.py`'s report is byte-identical before and after its fix.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Medium | `docs/guide/charge.md`:16 | "changing the pH or a charge edit re-runs the density, the contour and the mesh": stage 2 keys on the protonation key with its `charge_change_e` edits dropped (§5.3.1 NOTE on `charge.edits`; `density/stage.py` `atoms_key`), so such an edit shares its parent's density, contour and mesh; a `state` or `radius_scale` edit does re-run them | Fixed: the sentence names the pH, `state` and `radius_scale`, and says a `charge_change_e` edit shares its parent's stages |
| 2 | Low | `.claude/scripts/audit/markers.py` `_prose_lines` | Backticks are paired within one line, so a code span that wraps onto the next line of its paragraph shifts the pairing there and can blank a `[verified]` or `[tested:]` marker between two spans. Three knowledge lines wrap a span today; none hides a marker | Fixed: an unclosed backtick carries to the next line, and a blank line or a fence ends it; the report is unchanged |
| 3 | Low | `docs/design/workbench.md` WB-34 | The consequence cell reads "§8.2.34 AJ2, AJ3", but the row quotes AJ4's ruling ("Suite now, composer next"), `holds-now.yaml` says AJ4 holds in WB-34, and the replaced cell cited AJ2 to AJ4 | Fixed: "§8.2.34 AJ2 to AJ4" |
| 4 | Low | `knowledge/01-physics-epnpns/07`, the `d` note | The pointer for why `d` travels with the solution leads to `06/15`'s restore bullet, a test's rationale; the reason, that the screened-Poisson field is not bit-reproducible so a re-solved field is another operator, is `06/07` §7.1.2 | Fixed: the note states the reason and points to §7.1.2, and to `06/15` for the test |
| 5 | Low | `docs/guide/case-files.md`:33 | "the reference's *validated default* column" names no reference and links none | Fixed: links the case-file reference, whose column is *Validated default* |
| 6 | Low | `CHANGELOG.md`, Fixed | Names `structure/` and `density/` only; the package also changed two `io/defaults.py` descriptions and two `physics/` comments (AUD-216, AUD-351) | Fixed: the line names them |

Not findings: REV-231 (`structure/axis.py`'s margins pointer) stays open, since D6, the author's ruling, allows
no other edit under `src/`; REV-232's doubts are recorded and unchanged by this review.
