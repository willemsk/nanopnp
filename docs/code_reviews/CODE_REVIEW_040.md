# Code review 040: the fourth amendment of the Phase 5 plan (§8.2.36)

2026-11-08 · branch `ccr-ffafd419-mwhw6f`, the plan commit `69d2a0d` on `main` at `ed12cc6` (willemsk/nanopnp#168) · scope:
the amendment's 42 files, the Phase 5 plan, the ruling record §8.2.36 and the renumbering of WP5.10 to WP5.17 to WP5.15
to WP5.22 across the tree · focus: the plan's claims against the code, its decisions against the rulings, its
verification rows, its caps and sections · status: completed.

Static review of a plan commit (`/np-plan amend 5 review`, `/code-review --fix`), run at `high`. The commit was first
moved from the audit branch onto `main`, where the audit had merged with identical content. The plan's claims were
checked against `io/case.py`, `io/models.py`, `io/case_paths.py`, `io/defaults.py`, `pipeline/run.py`,
`pipeline/forecast.py`, `sweep/plan.py`, `api/sweep.py`, `api/session.py`, `api/project.py`, `structure/protonated.py`
and `mesh/primitives.py`, and WP5.13 and WP5.14 against CODE_REVIEW_036's decisions D1.1 to D6.2 and corrections C0 to
C6.1. They agree. Every renumbered reference was compared with the old one and with the numbering of its date (3
November, AG1; 5 November, AJ10). Each quote in CODE_REVIEW_039's evidence was compared with the file and line it cites.
No test and no `gate.sh` ran; the review turn gates afterwards. Thirteen findings: eleven fixed, one folded into
REV-216, one needing no change.

| # | Where | Finding | Outcome |
|---|---|---|---|
| 1 | `docs/project/review-items.md` (REV-139) | "The Sweep tool … is WP5.11's" was written under the 3 November numbering, when WP5.11 was the Study suite. The renumbering applied the 5 November table and made it WP5.16, the Molecular suite. | Fixed: WP5.19. |
| 2 | `docs/code_reviews/CODE_REVIEW_039/raw/probes.md` | Seven quotes of 3 November text took the 5 November table: Analysis WP5.17, Continuum WP5.15 twice, Study WP5.16, Qt's removal WP5.18, the close WP5.19. Two "WP5.09, the Molecular suite" stayed unmapped, and the cut-line quote did not match its file. Each now disagrees with the line it cites. | Fixed: each quote matches its cited line. |
| 3 | `docs/code_reviews/CODE_REVIEW_039/decisions.md`, `decisions.json` | The same mistake in the register's AG1 quote and in AG6's and AG7's package (WP5.17 and WP5.16 for WP5.20 and WP5.19). WP5.10 builds the generated decisions page from this prototype. | Fixed. |
| 4 | `SPECIFICATION.md`, `specification/index.md`, `specification/08-implementation-plan/index.md`, `02-rulings.md` | Six places still said the rulings run "§8.2.1 to §8.2.35" after the commit added §8.2.36. | Fixed in the live text; the audit's dated evidence keeps its range. |
| 5 | `docs/plans/phase-5-workbench.md` (*Design decisions*) | "then two of the six architecture clean-ups; the other two open the suites" counts four. AL22 puts four in WP5.13 and WP5.14. | Fixed: "four of the six … in two packages". |
| 6 | `docs/plans/phase-5-workbench.md` (WP5.10) | The entry plans a decisions writer, an index writer, the architecture page, the archive migration and a link check. It does not name the prototypes CODE_REVIEW_039 built and rehearsed in `.claude/scripts/audit/`. | Fixed: the entry starts from them. |
| 7 | `docs/plans/phase-5-workbench.md` (*Verification*, WP5.10 and WP5.12) | "The link check" and "the marker check" are named by no tool. They are `links.py` and `markers.py` of the audit. | Fixed: the rows name them. |
| 8 | `docs/plans/phase-5-workbench.md` (WP5.10) | WP5.10 changes the kept scripts in §8.4.4 and §8.4.5. `CLAUDE.md` still says "three scripts in `.claude/scripts/`", and no package owns that line. | Fixed: WP5.10 changes it with §8.4.5. |
| 9 | `docs/plans/phase-5-workbench.md` (*Context*) | "`mesh/primitives.py` has three geometries". It defines four: `SlabGeometry`, `CylinderGeometry`, `AxialSlabGeometry`, `CylindricalPoreGeometry`. | Fixed. |
| 10 | `docs/plans/phase-5-workbench.md` (*What the author supplies*) | The row has every suite in WP5.16 to WP5.20 prototyped on 2WCD. Physics is prototyped on example 01's NaCl case (AJ8; CODE_REVIEW_034, finding 3). | Fixed. |
| 11 | `specification/history/index.md` | AJ2, AJ3, AJ5, AJ10 and AK1 to AK3 still held "open: WP5.09" after WP5.09 merged. The commit touched these lines and left that part stale. | Fixed: each names the clause it now holds, and keeps open only the later packages. |
| 12 | `docs/plans/phase-5-workbench.md` | The plan is about 6,500 words against the 1,500-word target (§8.2.11 L7; AI15). The amendment adds about 1,200. | Folded into REV-216, with the new count. WP5.11 moves the delivered narratives (AL18; AUD-244). |
| 13 | `CHANGELOG.md` (WP5.08), `docs/design/reviews/2026-11-05-frame.md` | 3 November's "WP5.09" for the settings' guards and the palette maps to WP5.16. The plan now places REV-204, REV-208 and REV-211 in WP5.15. | No change: dated records mapped as AL26 rules. The open items carry the current placement. |

## Checked and in order

- §8.2.36's front matter, heading, table and letter series. Twenty-seven lines in the history index. The record's
  navigation in `mkdocs.yml`.
- §8.1's Phase 5 row: 7 + 3.5 + 13 to 16 weeks gives 24 to 27.
- `current.md` is under its 700 words, and its In brief under 250. The plan's In brief is 274 words, within its 275.
- The eight Phase 5 changelog entries AL14 moves. WP5.02 to WP5.09 carry tags, and WP5.01, merged before `v0.5.0`,
  stays under `## [Unreleased]`. Tags `v0.6.0-alpha.8` and `alpha.9` are published.
- AL23's amendment of §5.3.1 (lines 281 and 317) waits for WP5.13 and its code, as AG10's and AK's amendments did. No
  test pins the refusal it removes.
- The WP5.13 and WP5.14 entries agree with CODE_REVIEW_036's D1.1 to D6.2 and corrections C0 to C6.1. Every symbol
  they name exists at this head with the shape they assume.
