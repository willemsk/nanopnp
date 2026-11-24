# Code review 084: Phase 6 amended, the packages after the review numbered (§8.2.54)

2026-11-24 · branch `claude/np-plan-amend-6-8e71eb` at `ee7c7a2` on `main` (`b0cfbb2`) · scope: the two plan
commits' 15 files, +423 and −176, read from `git diff origin/main...HEAD`. Read in place: `.claude/skills/np-plan/`
(`SKILL.md`, `amend.md`, `phase.md`, `review.md`, `rulings.md`), §8.1's Phase 6 row, §8.3, §8.4.1, §8.2.52 and
§8.2.53, and the code each claim rests on · level: medium, with `--fix` · status: completed.

Static review of prose: no test and no `gate.sh` run. Read-only checks were run: `clause.py` on VER-62, RSK-15,
NUM-14 and PHY-23; `grep` for each code fact the plan states; the plan's word count by section. The review ran in
the session that wrote the plan, without a compaction between them: the `/compact` line reached the session as
pasted text. After the fixes `decisions.py` and `index_records.py` were re-run.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Important | The Phase 6 plan, as a whole | About 3,760 words without its report, against the level's 2,500 with a 10% allowance (`phase.md`; §8.4.4). The amendment added four package entries, seven open decisions and five criteria and tightened nothing | Fixed: 2,748 words. The delivered packages are one table, the settled open decisions one row, and three design rows that a ruling or a criterion already holds are gone; every check and grounding fact stays. The record quotes what was folded |
| 2 | Important | The plan, WP6.08's entry and its verification row | The prototype is thrown away, and the row checked only that the merged tree holds none of it. Nothing said how the reported result, example 01's walk held to 10⁻⁸, could be run again once the code is gone, though the author rules the design on it | Fixed: the package reports the commit that holds the prototype, the command that ran the walk and its stabilisation mode |
| 3 | Important | The plan, WP6.07's entry | The guard numbers were stored "as VER-62's are" with no tree named. VER-62's golden is recorded on a tree that computes as `v0.4.0` does; a guard number recorded again during a kernel package would make the last package's check pass on a moved value | Fixed: recorded once, on WP6.07's own tree, on which VER-62 passes and which no kernel package has touched; a regression reference with no independent oracle; a later change is a re-pin by ruling (G10) |
| 4 | Nit | `phase-6-record.md`, the new section | It left out replaced text: the Context's first paragraph, the design rows on the review and on old runs, the WP6.04 entry, criteria 4 and 8 and one line of the report. `rulings.md` asks for each amended entry quoted as it was | Fixed: each is quoted, with the entries of WP6.01 to WP6.03 and the settled open decisions that fix 1 folded |
| 5 | Pre-existing | The input note, Phase 6's table | The kernel's row cited MOD-13 and the installed packages' row MOD-11; both are `fixed` in the modularity register. BC1's row names MOD-10 alone | Fixed: both pointers are gone; MOD-10 and REV-67 stay |
| 6 | Nit | The plan, *Context* | "About eight touches" a package was cited to §8.3, which gives the four sessions; the eight touches are BC10's | Fixed: BC10 beside §8.3 |
| 7 | Nit | `docs/plans/current.md`, *Position* | The next step was the review. After the review it is the level's own (`review.md`, step 4) | Fixed: `/np-plan wp 6.05`, on Fable 5.2, once the amendment's pull request is merged |

## Checked and found true

- **The record.** §8.2.54 has the front matter, the heading, the paragraph on how the round was taken and the
  table's four columns; BD1 quotes the author's answer; the history index, the `mkdocs.yml` entry and BD1's line in
  `holds-now.yaml` are present; `decisions.py --check` passes. Ten earlier lines of `holds-now.yaml` name WP6.05 to
  WP6.08 where they named a package by its scope.
- **The renumbering.** No live text names the axis package WP6.05: the plan, the input note, REV-279's row and
  section, `holds-now.yaml`, §8.2.52's opening text and BB1, §8.2.53's BC3 and BC10 read WP6.06. BB1 carries the
  pointer to BD1. §8.2.50's AZ4 and AZ5, the code reviews 080 and 083 and the record's quotations keep theirs, as
  the author confirmed.
- **The order and the checks** are BC3's, BC2's and BC4's, and §8.1's Phase 6 gate holds each criterion of the plan
  but two that the plan adds for its packages: the orchestrator's three facts (BC10's consequence) and the guard
  numbers' prior check (BC3's).
- **The estimate.** 43 sessions, 26 to 49 agent hours and 66 touches are §8.1's and §8.3's, from seven parts; the
  round on the design, 2 sessions and 3 touches, is named beside them and is in neither clause, as the round on
  the review was not.
- **The code facts.** `structure/cavity.py` holds `channel_axis`, `structure/stage.py` `align`,
  `physics/models.py` `SWITCHES`, a closed tuple of four names, and `CoupledModel`, `physics/terms.py` the
  dataclass `Term`, and `post/forces.py` `_domain_force`. A push runs two of VER-62's seven walks (§7.6).
- **The versions.** `v0.7.0-alpha.1` to `-alpha.4` are published; `-alpha.4` is on `9a2d773`. WP6.05 to WP6.08
  take `-alpha.5` to `-alpha.8` by §8.4.1's rule, in the order they merge.
- **The In briefs.** The plan's holds 263 words and `current.md`'s 212, neither with a backtick or an identifier,
  each ending in **Your call**. `current.md` holds 699 words against 700.

## Not assessed

- The 468 s and 539 s of the push gate, the 3 of 8 draws that lock, and the nine names the workbench reads: each is
  carried from BC15, REV-279 and review 083, and was not measured again.
- Whether VER-62's walks cover the default switches alone: the plan says it is unchecked, and WP6.07 checks it.
