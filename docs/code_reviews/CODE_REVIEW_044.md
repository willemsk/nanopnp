# Code review 044: WP5.11, the specification's text and the agent instructions

2026-11-09 · PR #173, branch `ccr-0bd2808a-l1k5c2`, head `2ed85b4` on base `b15c162` · scope: the PR's diff, 80
files, read in full: `.github/workflows/tag.yml`, the specification bundle, `CLAUDE.md`, `AGENTS.md`,
`CONTRIBUTING.md`, `README.md`, `.claude/` (rules, skills, workflow), the Phase 5 plan and record, the WP5.11 plan,
`docs/project/`, the moved `knowledge/` text and the CODE_REVIEW_039 records · focus: each rewritten claim against
the code and CI, the SHALLs whose wording moved, the text AUD-113 and AUD-244 moved and every pointer to its old
home, the procedures that now point to one home, the `tag.yml` fix · status: completed.

Static review (`/np-ship wp 5.11`, `/code-review xhigh --fix`). No test, gate or benchmark ran; the ship turn gates
the fixes. Probed: §5.1's diagram draws exactly the `inputs` edges of `core/stages.py`; both §5.3.1 examples pass
`nanopnp validate case` once the files they name exist; each of the 148 listed findings reads `fixed` with its
item's commit in the register; the SHALLs number 517; the measurements cut from §4, §6 and §7.4 stand in
`knowledge/04/03` §3.2, `06/02` §2.2, `06/05`, `06/06` §6.1, `06/07` §7 and `07/03`; `StageInfo` has the seven
fields IF-01's NOTE lists; `Store.run_directory` names `runs/<name>-upto-<stage>-<hash>` as §5.3.3 says;
`Pe` = 0.385 at ε_r 78.15 and η 0.890 mPa·s; `tag.yml`'s capture removes the SIGPIPE under `pipefail`, and no
other early-exit pipeline runs under `pipefail` in CI. After the fixes: `decisions.py --check`, `links.py` (1,484
links, 0 broken, 2 known), `duplicates.py` and the strict site build pass; the decisions page re-renders MOD-13's
row; the SHALLs still number 517.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Medium | `CONTRIBUTING.md`, *Versions and releases* | AL14 makes this section the one home of the tag rule, and `np-ship/phase.md` step 5 and `np-ship/wp.md` §7 now only point to it; it never said that a close takes `vX.Y.0` alone, and its first bullet tags every merged package `-alpha.N`, so a close would carry both tags §8.4.1 forbids | Fixed: the bullet states the close's tag and its `## [X.Y.0]` heading |
| 2 | Medium | `README.md`, *Three ways in* | "Both show live convergence plots and a field viewer": the browser workbench registers the suites' bodies, the changes, problems, settings and palette screens and the charge screen (`gui/web/screens.py`), with no convergence plot or field viewer yet | Fixed: the workbench's suites are being built in Phase 5; the Qt shell has those views until it leaves |
| 3 | Medium | §7.6 | AUD-142's "Every solve SHALL write a provenance manifest" narrows the SHALL from every run: `pipeline/run.py` writes a manifest for every walk, a truncated one included, which §5.3.3's `upto-` directory names. A changed SHALL that the code exceeds is not one D2 lets land unasked | Fixed: "Every pipeline run, a walk stopped before the end included", which keeps the meaning and still reads apart from a CI run |
| 4 | Medium | §7.6, *Before a tagged release* | The row runs Tier 3 on Python 3.11 to 3.14 on the three platforms; `ci.yml`'s `tier3` job runs on ubuntu, Python 3.14, `continue-on-error` | Fixed: Tiers 1 and 2 in full on the matrix, Tier 3 on ubuntu 3.14, recorded and not gated |
| 5 | Low | `.claude/workflow/core.md`, *Gate and push* step 4 | "Push only a tree it passed (§8.4.4)": §8.4.4 holds no push rule; it is §8.4.2's first bullet | Recorded: `.claude/` is the implementing session's or the author's to edit, not a review sub-agent's |
| 6 | Low | §5.2, stage 8's gate | "Clamps above 5.3 M logged with location and property"; AM1's PHY-13 now logs location and species, as `log_clamp_activations` does | Fixed |
| 7 | Low | VER-48; `knowledge/07/02`; `src/` refusal texts | AUD-113 moved stage 1's refusals and thresholds and stage 2's radius set and union to §5.2's NOTEs, and VER-49 and VER-50 were repointed, but VER-48 and `knowledge/07/02` still cite the §5.3.1 NOTE on `structure:`, as do refusal texts and comments in `structure/axis.py` (15, 262), `structure/read.py` (140, 287) and `io/defaults.py` (96); `density/union.py` (333) and `density/radii.py` (180, 254) cite the §5.3.1 NOTE on `geometry.density`. Each resolves in one hop through that NOTE's new pointer | Fixed for VER-48 and the knowledge concept; the `src/` texts recorded, since WP5.11 changes no code (*Out of scope*) |
| 8 | Low | §7.3, VER-62's test-file cell | `tests/tier2/test_examples_*.py` omits the two 2WCD walks the row names, `test_pipeline_2wcd.py` (`2wcd-charged`) and `test_exclusion_2wcd_walk.py` (`2wcd-shell`) | Fixed |
| 9 | Low | FR-18 | "The physics models of PHY-21" at v0.2 includes `pb` and `pb-linear`, which FR-19 tags v0.4: one model under two releases | Fixed: FR-18 names its four models; PHY-21 keeps the no-separate-path rule |
| 10 | Low | CODE_REVIEW_039 `findings.md`, `redundancy-map.md`, `sediment.md` | Each says it was written "at `HEAD`": `register.py --at HEAD` writes the literal, and `maps.py` defaults to it, so the record names no tree | Fixed: `20fb8bc`, the commit that wrote them. The scripts' literal recorded (`.claude/scripts/audit/`): `--at` should resolve to a sha |
| 11 | Low | `docs/project/modularity.md`, MOD-13 | The new Outcome, "fixed, WP38", contradicts the Ruled and Placed paragraphs above it: WP5.08 split `cli/__init__.py` | Fixed in the report and the log row; the decisions page re-rendered |
| 12 | Low | `specification/index.md` | The §5, §7 and §8 lines keep their old descriptions, while the PR gives those index files front matter with new ones and updates the §1 and §6 lines | Fixed from the front matter |
| 13 | Low | WP5.11 Outcome; REV-216's section | The Phase 5 plan "holds 4,297 words"; `wc -w` gives 4,273 at the head | Fixed: 4,243 after finding 16's move |
| 14 | Low | `CONTRIBUTING.md`, *The gate* | Both gate lists omit the decisions page's check that the commit hook and the push gate run (CODE_REVIEW_042 #8 found the same in `CLAUDE.md`) | Fixed |
| 15 | Low | `tag.yml` | Under `set -e`, a commit without `CHANGELOG.md` now ends at the assignment with git's message, not the `::error::` annotation the pipeline gave | Fixed: `\|\| changelog=""`, so the grep reports it |
| 16 | Low | Phase 5 plan, *What the author supplies* | Two WP5.01 rows ("WP5.01 waits") stay after WP5.01 merged; the record took only three supplied rows | Fixed: both move to the record's supplied rows |
| 17 | Low | `.claude/skills/np-gui/grill.md` | The step now defers to *Putting a choice to the author*, which lacks the two rules it dropped: two to four options, the recommended first, marked *(Recommended)* | Recorded (`.claude/`) |
| 18 | Low | `.claude/workflow/core.md`, *Two lanes* | Still restates the no-tag rule in full, one of the five restatements Grounding D3 lists for AL14, now with a pointer | Recorded (`.claude/`) |
| 19 | Low | `knowledge/07/01` | It now defers the MPI consequences to ADR-001, which says "verified: no MPI symbols in any shipped `.so`", and keeps "The shipped binaries are not scanned for MPI symbols". `nm -D` over the installed `ngsolve` and `netgen` libraries finds no `MPI_` symbol | Recorded for WP5.12: the concept's claim needs its marker and log line |
| 20 | Low | `SPECIFICATION.md`, *Identifier to file* | The new paragraph repeats the table row: "A ruling is one or two letters and a number" | Fixed: the repeat goes |
| 21 | Low | `CLAUDE.md`, *Project structure* | "`core/` units, constants, provenance, caching" against §5.1's corrected row: provenance and the store are `io/`'s | Recorded (`CLAUDE.md`) |
| 22 | Low | `docs/plans/index.md` | Not re-run after items 10 and 12, as the core's *Gate and push* asks: it listed WP5.11 "planned, not started" and the phase plan's old status line | Fixed: `index_records.py` re-run, with this report's index line |

The recorded findings 5, 7 (`src/`), 10 (the scripts), 17, 18, 19 and 21 are for `/np-ship` to fix or to carry as
`REV-nn` rows.

## What `/np-ship` did with the recorded findings

- 5 and 18: `.claude/workflow/core.md` cites §8.4.2 for the push rule, and *Two lanes* points to
  `CONTRIBUTING.md` for a package merged before its phase's release instead of restating the rule.
- 7: carried as REV-226, which the author accepted for WP5.12; WP5.11 changes nothing under `src/`.
- 10: `register.py` and `maps.py` resolve their ref to a short sha (`commit()`); both rerun at `20fb8bc`
  reproduce the three records byte for byte.
- 17: `.claude/workflow/author.md` gains the rule `grill.md` dropped: two to four options a question,
  the recommended one first with *(Recommended)*.
- 19: the scan was wrong. NGSolve 6.2.2606's shared objects reference no MPI symbol, but `netgen-mesher`
  ships `ng_openmpi.so` and `ng_mpich.so`, whose MPI symbols only a system MPI library resolves.
  ADR-001's MPI row says so, and the concept points to it.
- 21: `CLAUDE.md`'s `core/` and `io/` lines follow §5.1.
