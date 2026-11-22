# Code review 072: the project's re-plan, Phases 6 to 11 (§8.2.49)

2026-11-22 · branch `claude/quirky-clarke-ctfb7z` at `1a7caa5` on `main` (`a94f2aa`) · scope: the plan commit's 47
files, read from `git diff origin/main...HEAD`. Read in place: `.claude/skills/np-plan/` (`project.md`, `rulings.md`,
`SKILL.md`, `review.md`), `.claude/skills/np-implement/wp.md`, `docs/plans/current.md`, §8.3, VER-62 with its rulings,
`holds-now.yaml` · level: high, with `--fix` · status: completed.

Static review of a plan commit: no test and no `gate.sh` run. Read-only checks were run: searches for `v0.7`,
`Phase 6` and `nanopnp/results/` outside the history; the published tags (`git ls-remote --tags origin 'v0.9*'`
returns none); `created_at` in `io/manifest.py`; the tests and sources for the FR-21 refusal's text; the model names
in `.claude/`; the `claude-api` skill's table (cached 3 November 2026) for AY7's prices and Opus 5.5's default
effort; §8.3's arithmetic against its rates; `current.md`'s word counts. After the fixes, `decisions.py` and
`index_records.py` were re-run, and `current.md` holds 697 words, its In brief 199.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Important | §8.1, the gates of Phases 8 to 11 | AY4 rules that every phase from Phase 6 closes with Tiers 1 and 2 passing on Linux, macOS and Windows, and names "§8.1's gates from Phase 6" as the clause changed. Only Phases 6 and 7 say so. Phase 8's gate, which 9 and 10 take, asks its own Tier 1 and Tier 2 tests, and Phase 11's asks Tiers 3 and 4 alone, so a tool phase or the validated release could close on a red platform leg | Fixed: Phase 8's and Phase 11's gates name the three platforms (AY4) |
| 2 | Important | `docs/design/workbench.md`, WB-60 | §5.3.5 renames the results file's schema `nanopnp/results/v0.8`, the release that ships it; WB-60's ruling in the design document still reads `nanopnp/results/v0.7`. The tree's package would meet two schema names | Fixed: WB-60 reads `v0.8` (AY1); `decisions.py` re-run |
| 3 | Important | `docs/design/workbench.md`, the Analysis suite's row and WB-52 | The commit moves the document's mentions of the tree, the polish pass and the layers to Phase 7, but two are left: "Until Phase 6's tree of results" and "the polish package (WP5.26, moved to Phase 6 by §8.2.47 AW1)". Phase 6 now builds neither | Fixed: both name Phase 7 (AY1) |
| 4 | Important | `.claude/skills/np-plan/SKILL.md`, *The pause*; `.claude/skills/np-implement/wp.md`, its two prompts | AY7, §8.4.5 and the core say each pause's prompt names the next step's model, because the author picks it. The three lists of what a prompt holds were not changed, so a session that follows its list prints a prompt without the model, and the author starts the review or the ship on whichever model was last picked | Fixed: each list names the model of the next step, by the core's *Models and executors*; AY7's cell names the two files |
| 5 | Nit | `docs/plans/current.md`, In brief | "changes no number a user sees", two sentences before "the known gaps in the equations are closed in the next phase". AY1 and §2.7 say none but those the equations package re-pins | Fixed: "except where an equation is corrected"; three sentences shortened to keep the cap, 697 words |
| 6 | Nit | §5.4.1's NOTE; Appendix A, QR-13; `docs/plans/sessions/phases-6-to-11.md` | §8.2.8 H1 and H3 deferred the backend interface (MOD-10) and the rest of MOD-13 to "Phase 6", which was validation. The two clauses still say Phase 6, which is now the library's restructure, and the input note places neither | Fixed: the note's *Open decisions* gains the question, owned by `/np-plan phase 6`. The two clauses are left: "Phase 6 or a later plan" still holds |
| 7 | Nit | §8.2.49, AY6's last cell | The commit annotates FR-28's Release and `holds-now.yaml` names it for AY6; the record's cell names only the register's rows and NUM-04's NOTE | Fixed: the cell names FR-28's Release |
| 8 | Nit | §2.7, the v0.8 row | The row lists the moved packages without the performance package, which §8.1's Phase 7 row and the input note hold | Fixed: the row names it |
| 9 | Nit | `docs/project/architecture-survey.md`, its head | "read REV-272 and the Phase 6 plan" for a finding's outcome; the workbench's findings are Phase 7's | Fixed: it names both plans |
| 10 | Nit | `docs/project/review-findings.md` and `review-items.md`, REV-274's title | "Five details the Qt panels show are carried to Phase 6", in a row whose owner now reads Phase 7 | Fixed at the review turn: the title, its one link in the register and the section's five markers read Phase 7; no other file links the anchor |
| 11 | Nit | `docs/user-testing/findings.md` | Three entries say FR-28 or REV-60 is "Phase 6", one with `v0.7`; each is still true by number, and the file is a dated log | No change: a record of its date, and each entry is still true by number; not a defect |

Checked and found true: the record's count of nine questions (five recommendations, two free answers, two against);
AY7's prices, the cached read on both models and Opus 5.5's default effort; no `v0.9*` tag is published, and a
manifest carries `created_at`; no test holds the FR-21 refusal's version; §8.3's Phase 6 and Phase 7 rows are their
package counts times the stated rates; each moved review row agrees with its *Placed* line, the input note and
`holds-now.yaml`; five of AW1's six packages are Phase 7's and the refusals Phase 6's; the documentation increment
AW3 waits on is increment 7; the reviewers' agents stay on Opus at high effort (AN9); `project.md`'s Turn 2 list (the
record, §8.1, §3's Release column, §2.7's NOTE, §8.3, the input note, `current.md`) is met; `current.md` is within
its 700 and 250 words, its In brief without backticks or identifiers.

## Added at the review turn

Two calls the plan made were written in §8.2.49 as consequences of a ruling, without the mark that the author did
not rule them. The record now says so in its own text: the library's refusals in Phase 6 (AY1) are the plan's
placement, confirmed at `/np-plan phase 6`; the git tag (AY5) is the plan's reading of "a tag in the commit",
confirmed at the cleanup's plan. Both were already rows of the input note's *Open decisions*.
