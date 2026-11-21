# Code review 067: the seventh Phase 5 amendment, the early close placed

2026-11-21 · branch `claude/adoring-albattani-iw6y0g`, the plan commit `f5aa334` on `3971b30` · scope: the commit's 20
files. The Phase 5 plan's status, In brief, context, design decisions, the *Moved to Phase 6* table, WP5.27, WP5.28, its
open decisions, supply rows, verification row and criteria; the record's *Amended 21 November 2026* section; §8.2.47 and
its `holds-now.yaml` lines; §2.7, FR-32's and FR-36's Release, §8.1, §8.3, OPN-08 and Appendix A; the design document's
moved mentions; the review register's placements. Checked against the code at this head: which modules import PySide6,
what `gui/web/` imports from the top-level `gui/*.py`, `io/manifest.py:DISTRIBUTIONS`, `pyproject.toml`'s ruff
selection and `nanopnp-gui` script, `tests/tier1/test_layering.py`, the self-tests in `gui/app.py` and `gui/probe.py`,
and the published tags · level: medium as called, with `--fix` · status: completed.

Static review: no `gate.sh` and no test run; the review turn gates afterwards. `decisions.py --check` and `links.py`
were run and pass.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Important | `docs/design/workbench.md`, *Tabs or areas*, rows Q37 to Q41 | WP5.27 checks every row Q01 to Q41 present "in the browser workbench as it stands", and a miss keeps Qt. The tree round rewrote Q37, Q38, Q40 and Q41 to name the tree of results (*Data › Shown run*, the bottom panel's *Quantities*, a plot group's surface), which AW1 moves to Phase 6, after Qt leaves. Read as written, four rows miss | Fixed: each row names WP5.21's explorer, as it read before the tree round, as what WP5.27 checks, then the tree's form from Phase 6. The plan's WP5.27 entry says so |
| 2 | Important | Phase 5 plan, WP5.27 and its verification row | The entry reads as a removal. The restated clauses it makes the text (VER-43, VER-44, VER-55, ADR-004's packaging NOTE, RSK-13) ask a *server's self-test* in the packaging probe's place, run by CI on three platforms. The code has a self-test only in `gui/app.py` and `gui/probe.py`, which leave; `gui/web/` and `cli/` have none. The verification row cited the four rows "as their clauses" with no test that reaches the self-test | Fixed: the entry names the self-test as work the package adds; the row names its check |
| 3 | Important | `docs/design/workbench.md`, row Q16 to Q20; the plan's WP5.27 | Q16 is "drag a vertex". The browser row gave dragging to WP5.26, which ran before Qt's removal and now runs after it. The plan did not say whether a vertex moved by typed r and z meets the row | Fixed, then ruled: put to the author at the review turn, who chose that the typed move counts (§8.2.47 AW7); the row and the entry say so |
| 4 | Nit | Phase 5 plan, WP5.27 | "The Qt-only halves of `gui/geometry.py` and `gui/charge.py`" is true, but the survey's inventory also has `gui/app.py`, `case_model.py` and `scene.py` Qt-only, `pyproject.toml` ships the `nanopnp-gui` script, and `io/manifest.py:DISTRIBUTIONS` records `PySide6` in every manifest. The entry named none. The browser shell also imports `gui/convergence.py`, `run_model.py`, `solver.py`, `render.py` and `assess.py`, which stay whole | Fixed: the entry names the modules and the script, and leaves the manifest's row to the package's plan, since removing it changes what a manifest records |
| 5 | Nit | §8.1, Phase 6's row | §2.7's v0.7 row, §8.1's GUI increment 6 and §8.3 give Phase 6 the moved packages; its own row still read "Full V&V suite in CI, documentation, JOSS paper" at "about ten packages: 50 to 60 sessions" | Fixed: the row names the moved packages and §8.3's 30 sessions beside its own |
| 6 | Nit | §8.3, the moved packages' row | "WP5.22 to WP5.26 with the guided route" at 30 sessions is five packages at six; AW1 counts six packages, and WP5.27 keeps its whole six sessions in Phase 5's row | Fixed: the row says the route's share stays counted in WP5.27 until the scope round |
| 7 | Nit | Phase 5 plan, WP5.28, open decision 5 and the end-of-phase report | The In brief recommends settling the tool phases' order at Phase 6's scope round, and open decision 5 allows it; WP5.28 still "orders the tool phases", and the report lists their order | Fixed: both allow the handing |
| 8 | Nit | Phase 5 plan, verification row of WP5.19 and the end-of-phase report | The row cites "the 200 ms measure (criterion 6)"; criterion 6 now says the measure is not this phase's. The report still lists the click-to-redraw time with no word on the GPU measure | Fixed: the row names Phase 6; the report says headless |
| 9 | Nit | Phase 5 plan, verification row of WP5.27 | "The capability list, Q01 to Q41" stands in a row of Tiers 1 and 2; no test holds it, and criterion 3 is checked by a person | Fixed: checked at review against the rendered screens (N3) |
| 10 | Nit | `specification/history/holds-now.yaml`, AG7 | AG7 held "the Phase 5 plan's criterion 6", which no longer states the 200 ms rule | Fixed: open at Phase 6's performance package; the decisions page regenerated |
| 11 | Nit | FR-35's NOTE; QR-16 | The NOTE sends every text REV-254 lists to the refusals package, but REV-254's suites' words go with the polish pass. QR-16's keyboard path for canvas actions moved with the polish pass, and unlike FR-35 nothing beside the clause said so | Fixed: the NOTE names both packages; v0.6 shipping with QR-16's gaps was put to the author at the review turn, who chose to ship with the gap noted (§8.2.47 AW8); the NOTE beside QR-16 names REV-236, REV-245 and REV-266 |
| 12 | Nit | `docs/guide/index.md`; `docs/design/workbench.md`, WB-51 | The guide's index says WP5.27 "rewrites the guide for the workbench" (AW3: a short guide). WB-51's consequence names WP5.24 with no word on where it went, where WB-52's was edited (AW4) | Fixed |
| 13 | Nit | REV-271's section | "About 4,100 words" | Fixed: about 4,200 after this review's additions; AW5 keeps the length |
| 14 | Nit | §5.3.5 | `results.yaml` keeps the schema identifier `nanopnp/results/v0.6` though the file now arrives in v0.7 | Fixed by the review turn: `nanopnp/results/v0.7`, the release that ships the file (§8.2.7 G6), in §5.3.5 and WB-60 |
| 15 | Pre-existing | `docs/design/workbench.md`, link 3 | "Dragging the cut's line is … (REV-238)": REV-238 is Prepare's handles, placed in the structural mutator's phase, not the polish pass | Fixed by the review turn: the drag is a point of REV-267, which link 3 now cites |
| 16 | Pre-existing | `docs/plans/index.md`, the record's line | "in progress; WP5.01 delivered (awaiting `/np-ship`)" is the record's first status, read by `index_records.py` | Fixed by the review turn: the record has a status line of its own |

Checked and found true: `v0.6.0-alpha.20` and `v0.6.0-alpha.21` are published; only `gui/app.py`, `gui/probe.py` and
`gui/widgets/` import PySide6; `gui/web/` imports the halves of `gui/geometry.py` and `gui/charge.py` the survey lists;
ruff selects `C901` and `PLR0913`, and `test_layering.py` is VER-61's (AW6); §8.3's shell row is nine packages at six
sessions and §8.1's thirteen packages sum to 74 sessions, 66 to 132 hours and 122 touches; every register row not
`fixed`, `declined` or `wontfix` names WP5.27, a Phase 6 package, a later phase or the Copilot session plan; the restated
NOTEs read (P3, IF-09, QR-10, CON-09, VER-43, VER-44, VER-55) depend on no moved package; the record quotes the status, the In brief, the rows and
the entries as they were; §8.2.47 has its front matter, its index line, its nav line and one `holds-now.yaml` line a
ruling; the In brief holds 262 words with no identifier and `current.md` 700, naming `/np-plan amend 5 review` next;
`decisions.py --check` and `links.py` pass.

Sixteen findings, all fixed: three important and eleven nits, and two pre-existing. Findings 3 and 11 each named a
consequence of AW1 for the author; both were put to the author at the review turn and ruled as §8.2.47 AW7 and AW8.
After the review turn `current.md` names `/np-plan wp 5.27` next.
