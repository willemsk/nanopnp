# Code review 099: the Phase 6 plan's amendment after the rulings on the kernel's design (§8.2.62 BL1 to BL10)

2026-11-27 · branch `ccr-4940d566-rjlh0x`, head `61eb515` on base `061b512` · scope: two commits, 28 files, +676
and −312, read from `git diff origin/main...HEAD`, against `.claude/skills/np-plan/amend.md`, `phase.md`,
`rulings.md` and `review.md`, `.claude/workflow/author.md`, §8.2.62, §5.4, §5.5, §7.3, §8.1, §8.3 and `CLAUDE.md` ·
reviewer: the `/code-review` hunt at its medium level, Fable 5.2 at high effort, with `--fix` · status: completed.

Static review of a plan commit: Markdown and one YAML file, nothing under `src/` or `tests/`. No test and no gate
ran; the review turn gates afterwards. Probes: each line of the plan's "true of the codebase today" against
`src/nanopnp/` at this head; `tests/tier2/data/number_stability.json` for the walks; `tests/tier2/test_access_conductance.py`
for VER-17's model; the costs summed again; the word counts by `wc -w`. Line numbers are the reviewed head's.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Medium | `docs/plans/phase-6/phase-6-library-foundations.md:188` | WP6.10 rewrites the stabilisation's wind, and its verification row asked only VER-62's two push walks. The stored numbers that take a stabilised mode are VER-80's `guard-reference` and `guard-supg`, which are nightly and held in the reference environment alone. A term lost from the wind would merge and be met at WP6.12, where BL2's "one named change undone" can no longer name one change of one package. The design page's own table had "VER-80 nightly" for this package | Fixed: the row adds VER-80's stabilised guards |
| 2 | Medium | the plan, line 193; §5.5's NOTE | The row "a term from an installed package, proposed" did not say how the test gets an installed package. §5.5 has the library read the entry-point group once a process at the first use of any registry, so a fixture that appears inside the test process is never read, and a patched `entry_points` shows neither the command line nor the workbench finding it (criterion 6) | Fixed: the row names a fixture distribution found by a fresh process |
| 3 | Medium | the plan, line 105; §5.4.4 | WP6.10 claimed "§5.4.4's first four tests", and the third of them is PHY-23's switch bringing both terms or neither, which the verification table and the design page give to WP6.11, the package that writes the switch records | Fixed: §5.4.4 lists the wind's test third and the switch's fourth, and WP6.10 claims the first three |
| 4 | Medium | the plan, line 189; REV-298 | WP6.11 turns the log branch into a case key recorded as a deviation (BL7), and its row held no assertion that a run on the log branch names it in its manifest: the failure REV-298 was opened for. The design page's Tier 1 line for it was dropped | Fixed: the row adds it |
| 5 | Medium | the plan, WP6.11; `src/nanopnp/io/defaults.py:19,228` | "Every list of switches and deviations is derived from the records." Two of those lists, `SWITCH_PATHS` and `deviations`, are in `io/`, which imports `core` alone at run time, and the records are the kernel's, in `physics/`. Deriving them as written adds an edge `io` to `physics` (VER-61). Neither the plan nor the design page says where the records live. Plausible | Fixed: open decision 20 gives it to WP6.11's plan |
| 6 | Medium | the plan, criteria 1 and 14, decision 22 | The marks of the 3D direct solve are measured on one machine, and criterion 1 asks Tiers 1 and 2 on three platforms' CI runners with no waiver. Nothing says which machine the marks stand for, or whether the benchmark is `slow` or `nightly` | Fixed: decision 22 names CI's runners and the benchmark's marker |
| 7 | Low | the plan, criterion 13, decision 21 | "Three meshes, each half the size of the last" names no sizes. Halved twice from the trial's 0.4 the finest has about 310,000 unknowns, more than the 260,406 that WP6.14 measures first because it may not fit | Fixed: decision 21 sets the three sizes at WP6.13's plan |
| 8 | Low | `specification/05-software-design/04-component-design.md:30-33`; QR-13 | §5.4.1's NOTE and QR-13 said `CoupledModel` assembles directly against NGSolve until the kernel's last package merges; the plan composes the coupled residual and removes `residual_form`'s body at WP6.10, the first | Fixed: the coupled forms until WP6.10, the single-field models' until WP6.12 |
| 9 | Low | `specification/05-software-design/index.md:18` | The index line of §5.4 still read "the weak forms stated once against NGSolve"; the file's description was rewritten and §5.5's line was updated | Fixed |
| 10 | Low | the plan, criterion 8; `docs/project/review-findings.md` REV-301 | WP6.14 takes REV-301's three citations, and neither criterion 8 nor the row named it, so the plan was the only record of the owner | Fixed: the criterion, the row and the item's section name WP6.14 |
| 11 | Low | the plan, the verification table | WP6.14 had no row; its quality gates' tests stood in WP6.15's | Fixed: a row of its own |
| 12 | Low | the plan, line 190; QR-14 | WP6.12 restates VER-56 for a model as a list of terms, and QR-14's "only one class" was amended only at WP6.16 | Fixed: WP6.12's row restates QR-14's clause with VER-56 |
| 13 | Low | `specification/history/62-…md`, rows BL2 and BL6 | `rulings.md`: "The ruling's row names the clause." BL6's row left out QR-13 and Appendix A's QR-13 row, both amended in the commit, and BL2's left out §8.4.4, which `holds-now.yaml` names | Fixed |
| 14 | Low | the same record, its first paragraph | "The session recommended against the design page twice, in BL3 and BL5." BL6's row and the design page's *What the author ruled*, item 4, show a third: the recommendation changed after the author's question | Fixed: three times, BL6 after the question |
| 15 | Low | `docs/plans/current.md`, *Not to be re-decided* | `phase.md` has the amendment replace the entries that the rulings supersede. The entry on the continuation trial (BC24), which no ruling of this round touches, is gone, and BC16's and BC20's statements are reduced to a citation | Fixed in the review turn: the three entries are restored, and the prototype's line and the round's cost, which the plan holds, make the room |
| 16 | Low | the plan, `## Work packages` | `phase.md` asks each entry for its proposed `VER-`/`VAL-` with oracle, numbered on from Appendix A's. The entries are "planned by scope" with unnumbered proposals, a third state beside planned and provisional | Fixed in the review turn: the proposals are VER-81 to VER-85, and WP6.14's gates restate VER-10 |

The pass fixed fourteen findings and the review turn the other two. To hold the plan's cap, criterion 3 now points to VER-62's three
conditions where it repeated them, and open decisions 15 and 16 share a row; no check is dropped.

## Checked and found true

- **The plan's grounding.** `CoupledModel.residual_form`, `_flow_state` and `_flow_residual` exist in
  `physics/models.py`; `SWITCHES` is a tuple of four that `io/defaults.py` `SWITCH_PATHS` holds again;
  `log_variables` is reached through `models.create` alone; the ionic force is written in `flow.py`
  `electrical_body_force`, `_flow_state` and `post/forces.py` `_integrands`; `advective_velocity` sums the
  electromigration, steric and advective drifts and no decrement; `ngs.Id(2)` is in `stabilisation.py` and
  `post/forces.py` and `ngs.y` in `post/indicator.py`; `from_ngsolve` refuses a 3D mesh; `Measures.volume` builds
  rules for `SEGM`, `TRIG` and `QUAD` and no `TET`; `PUBLIC` holds `register_model` and `registered_models` and no
  other registering name.
- **The stored walks.** The file holds thirteen, VER-62's seven and VER-80's six; none holds a cell Péclet number.
  VER-17's test solves `pnp`.
- **The costs.** The seven packages and the close sum to 24 sessions, 20 to 37 agent hours and 38 touches; the
  kernel to 9, 8 to 16 and 15; the 3D packages to 9, 8 to 15 and 15; §8.1's and §8.3's row to 41, 30 to 56 and 64.
- **The caps.** The plan without its report is 2,742 words after the fixes, under 2,750; its In brief 259, without
  backticks or identifiers; `current.md` 700, naming `/np-plan amend 6 review` before the level's next step.
- **The record.** The replaced text is in `phase-6-record.md`, quoted; open decision 18 was closed by WP6.07
  (REV-288 `fixed`); the ten rulings count seven with the recommendation, two against and one in the author's words;
  each has its line in `holds-now.yaml`, quoted where YAML needs it.
