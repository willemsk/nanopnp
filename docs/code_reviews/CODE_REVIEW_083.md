# Code review 083: the project re-planned, the ground-up review ruled (§8.2.53)

2026-11-24 · branch `claude/wp-6-04-findings-review-ada48p` at `130da9b` on `main` (`9a2d773`) · scope: the plan
commit's 34 files, +644 and −532, read from `git show HEAD`. Read in place: `.claude/skills/np-plan/` (`SKILL.md`,
`project.md`, `review.md`, `rulings.md`), the clauses the rulings cite, and the code each claim rests on · level:
high, with `--fix` · status: completed.

Static review of prose: no test and no `gate.sh` run. Read-only checks were run: `clause.py` on NUM-18, FR-17,
QR-07, QR-09, QR-14, NUM-33, PHY-08 and B4; `decisions.py --check`; `links.py`, with and without `--anchors`; the
sums of §8.3's four changed rows and of Appendix A's coverage line; `grep` for each code fact a ruling rests on and
for every live mention of Phases 6 to 8, of `v0.7` to `v0.9`, of QR-11 and of the four sections removed from the
workbench design. After the fixes `decisions.py` and `index_records.py` were re-run.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Important | §5.5, *Boundary of the framework (N1)* | BC5 rewords N1 to admit a term a developer writes, and §5.5 still said "Users do not write weak forms": two statements of one exclusion disagreed in the same tree | Fixed: §5.5's sentence is N1's new text; BC5's row and its `holds-now.yaml` line name it |
| 2 | Important | §2.6, the line on the front end's drawing; `docs/design/workbench.md`, the Analysis row of the suites' table | Both still placed the tree of results in "Phase 7" by AY1. BC7 makes it Phase 8's, and ADR-004's twin sentence said Phase 8 on AY1's authority alone | Fixed: Phase 8's, citing BC7, in all three places |
| 3 | Important | `holds-now.yaml`, AW7, AW9 and AW10 | Each line said that the ruling holds in "the design document's row Q16 to Q20" (Q31 to Q34; Q05 to Q08). BC12 removed those rows with *Tabs or areas*, so the register pointed a reader at text that is not there | Fixed: each line says that the row left the document with its section and that the tree at `9a2d773` holds it. The status of each ruling is unchanged |
| 4 | Important | §8.1, Phase 6's gate | The gate named the stored numbers the kernel must reproduce, and no criterion for the kernel's own Tier 1 and Tier 2 tests (FR-40; BC1's consequence) or for a term found in an installed package (BC5's consequence). The old composer row carried the first, and it was removed with the row | Fixed: both criteria are in the gate, each with its ruling |
| 5 | Nit | §8.2.2 B4; §8.2.10 J6; BC22's row; the input note's Python row | BC22 raises the floor that B4 set and J6 confirmed, and neither row carried the pointer `rulings.md` asks of an amended ruling. The clauses left to the package were QR-09 and §8.4.2, without §2.5's table, which VER-47 compares with the declared range | Fixed: a pointer in each first cell and in `holds-now.yaml`; §2.5 named in BC22's row and in the input note |
| 6 | Nit | §7.2, the rows of VER-43, VER-44, VER-55, VER-60 and VER-66 | Each still cited QR-11, which BC11 withdraws. BC11 says that the four shell rows stay traced under IF-09 and the requirements of their own rows | Fixed: QR-11 leaves the five lists; BC11's row names the change. `tests/tier1/test_backend_registries.py` named QR-11 in its docstring: the review left it, and the review turn removed the identifier |
| 7 | Nit | `docs/project/ground-up-review.md`, the status line | "The rulings differ from it in eight places": eight is the number of choices against the session's recommendation. Against the report's own verdicts the rulings differ in more: GU-01, GU-03, GU-05, GU-10, GU-12, GU-13, GU-14, GU-19 and GU-22 at least | Fixed: "several places" |
| 8 | Nit | The input note, *Open decisions*; the Phase 6 plan, line 82 | BC3 and BC10 put the orchestrator's package before WP6.05, which keeps its number (BB1). The note's row spoke of "packages after WP6.05", and the Phase 6 plan gives WP6.05 the tag `v0.7.0-alpha.5`, which the package that merges first would take | Fixed in the note: the row names the order, the numbers and the tags as the amendment's to settle. The Phase 6 plan is changed only by `/np-plan amend 6` (not fixed here) |
| 9 | Nit | `docs/plans/current.md`, *Not to be re-decided* | The entries on BA7 and BA14 (a session may restructure on the push gate; the nightly walks are not asked), on AY4 and AZ8 (the platforms a gate asks) and on Fable 5.2 planning are gone, while BC4 rests on BA14 by name. The file holds 697 words against 700 | Left by the review, fixed at the review turn: the entries on BA7 and BA14 and on AY4 and AZ8 are back, within 700 words. The entry on H12 and the words on Fable 5.2 planning left the page; `CLAUDE.md` states both |
| 10 | Pre-existing | Appendix A, the coverage line | The line says 22 requirements are "none yet"; 21 rows say so. Before this commit it said 17 where 16 rows did. The commit's own arithmetic is right: five rows added, QR-11 not counted | Left by the review, fixed at the review turn: the line says 66 of the 87 and 21, as the rows do. Which row the older count held is not known; the clone's history starts after it |

## Checked and found true

- **The record.** The 25 proposals GU-01 to GU-25 each fall under one of BC1 to BC24. Sixteen choices of the
  recommendation, eight against it and the request to be asked one by one make the 26 questions with BC10's free
  answer. The front matter, the heading, the table's columns, the history index, the `mkdocs.yml` entry and the 24
  lines of `holds-now.yaml` are as `rulings.md` asks; `decisions.py --check` passes.
- **The clauses each row says it changed in this commit** are changed: FR-03, FR-20, FR-22, FR-28, FR-29, FR-31,
  FR-32, FR-36, FR-40, FR-45 to FR-49, IF-01, IF-09, QR-07's NOTE, QR-11, CON-08, N1, ADR-001, ADR-004, ADR-005's
  NOTE, §5.3.5, §5.4.1's NOTE, NUM-18's, NUM-21's and NUM-32's NOTEs, §6's three pointers, RSK-15, OPN-08, §2.7,
  §8.1, §8.3 and Appendix A.
- **The sums.** §8.3's Phase 6 row: 43 sessions, 26 to 49 agent hours and 66 touches from its seven parts. Phase 7:
  68, 56 to 111 and 108. Phase 8: 88, 87 to 173 and 144. Phase 12: 26, 22 to 43 and 44. §8.1 and `current.md`
  repeat them without a difference.
- **The code facts.** The workbench imports nine names of `physics/`: `SWITCHES`, `Term`, `case_model`,
  `declaration` and `role_conditions` of `models`, and `CONDITIONS`, `Symbol`, `symbols_in` and `written` of
  `terms`. `geometry.pore.shape` is `Literal["cylinder"]`. `symmetry.point_group` is the field FR-03 now names.
  Nothing under `src/` or in `pyproject.toml` reads entry points. Pint is pinned below 0.26. VER-62 holds seven
  walks at 10⁻⁸ on a mesh it holds, and a push runs two of them (BA14). REV-156 gives the 62 % and the 24 %.
  BC24's "six rungs" is REV-283's count of `default_ladder`, which this review did not count again.
- **The versions.** `main` is `9a2d773`, which holds WP6.04; the tags `v0.7.0-alpha.1` to `-alpha.3` are published
  and `-alpha.4` is not, as `current.md` says. The commit named in the workbench design, `9a2d773`, is on `main`.
- **The phase in flight.** The Phase 6 plan is unchanged, and `current.md` names `/np-plan project review` and then
  `/np-plan amend 6`. Its In brief holds 231 words, no identifier and no backtick, and ends in **Your call**.
- **The links.** `links.py` finds no broken path and no anchor that this commit broke; no file links into the four
  removed sections.
- **The guards that read these files.** `validation/modularity.py` pairs a requirement with a release only for a
  row whose Release cell is a bare version, and no string under `src/` names `v0.7` to `v0.9` or a phase number.

## Not assessed

- Whether pull request 213 is the one that merged WP6.04, and the count of nine `AskUserQuestion` calls: neither
  can be read from the tree.
- The costs BC15 quotes for the browser tests, and what the engine's code does with pip's `mkl`: the record says
  itself that the second was read and not run.
- The strict documentation build (`uv run just docs`), which the gate runs.

## For the author

- Finding 9: the review turn chose what left *Not to be re-decided*; name another entry if H12's should return.
- Finding 8: `/np-plan amend 6` settles whether the orchestrator's package takes a number below WP6.05's tag or
  WP6.05 gives up `v0.7.0-alpha.5`.
