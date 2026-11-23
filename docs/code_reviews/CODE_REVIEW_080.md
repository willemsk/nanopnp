# Code review 080: the Phase 6 plan amended, the ground-up review planned (§8.2.52)

2026-11-23 · branch `claude/practical-cerf-81g9zz` at `c963a79` on `main` (`5b1e7fb`) · scope: the plan commit's 16
files, read from `git diff main...HEAD`. Read in place: `.claude/skills/np-plan/` (`amend.md`, `phase.md`,
`rulings.md`, `review.md`, `SKILL.md`), `.claude/workflow/author.md`, `.claude/scripts/index_records.py`, §2.7, §5.2's
NOTE on stage 1, §8.1, §8.3, §8.4.1, VER-48, records 51 and 52, `holds-now.yaml`, REV-239 and REV-279, knowledge
04/15, `src/nanopnp/structure/` (`stage.py`, `cavity.py`, `orient.py`), `tests/tier1/test_structure_axis.py` and
`test_structure_stage.py` · level: medium asked, high as the reviewer reports it, with `--fix` · status: completed.

Static review of a plan commit: no test and no `gate.sh` run. Read-only checks were run: `wc -w` on the plan without
its report, on its In brief, on `current.md` and its In brief; `git ls-remote --tags` for `v0.7*` and `copilot-host`;
`clause.py VER-48` and `clause.py 8.4.1`; `git grep` for the package numbers WP6.06 to WP6.18 and for every caller of
`channel_axis`; the sums of the In brief's cost against §8.1 and §8.3. After the fixes `index_records.py` and
`decisions.py` were re-run. The plan holds 2,724 words without its report, against 2,750; its In brief 275, against
275; `current.md` 699, against 700, and its In brief 223.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Important | `docs/plans/index.md`, the record's line; `phase-6-record.md` | The index gives the record's status as "in progress. Delivered: WP6.01, WP6.02, WP6.03 … WP6.04 to WP6.18 provisional until it rules (§8.2.50)". `index_records.py` takes a file's first bold `**Status: …**` span, and the record's only one is the plan's old Status line, quoted by this amendment. A reader of the index finds the superseded numbering stated as the record's own state | Fixed: the record carries its own Status line under its header, as `phase-5-record.md` does, and the index is written again |
| 2 | Important | The plan, *True of the codebase today*, first fact | "`structure/stage.py` `align` takes that axis only under C1 or `axis: cavity`" is true of `align`, and the fact reads as the whole list of what takes the channel's axis. `structure/orient.py` `_channel_line` calls `cavity.channel_axis` from each of three starts where no covariance axis stands apart, which is `orient_pore`'s and `nanopnp prepare`'s route for a pore with no ring. REV-239 records that it "shares the weakness". WP6.05's plan would start from a survey one caller short, and the notice of a changed axis would miss a prepared file | Fixed: the fact names both callers. The prediction on VER-62 stands: no example case sets C1 or `axis: cavity`. Whether a walk's prepared file took `orient_pore`'s channel route was not run |
| 3 | Important | The plan, WP6.05's entry and criterion 8 | The criterion asks 10⁻⁶ rad "on every perturbed draw" of the wall with the ragged rim, and the entry names VER-48's gate test as the test. That test reads the tilt from the orientation gate's refusal, which `gate_channel` prints to two decimals, and admits 11.995° to 12.005°: it resolves 2 × 10⁻⁴ rad. No test perturbs a wall today; the 10⁻⁶ rad is the recovery test's, on walls tilted 8° and 35°, and REV-279's 3 of 8 draws are of the 12° wall. As written the criterion has no test that can read its number | Fixed in the entry: the draws read `cavity.channel_axis` itself. Which walls and how many draws is WP6.05's plan's |
| 4 | Important | The plan, open decision 11 and criterion 8 | "VER-48's two limits": the two limits of REV-239 are §5.2's NOTE on stage 1's, the straightness limit of 0.03 nm and the `axis: z` budget of 0.015 nm, each twice a number measured on 2WCD (0.0148 nm and 0.0073 nm). The same NOTE states the method the fix changes, a centre as the mean of the spaces within 0.001 nm of the widest. The criterion amends VER-48 alone on a move, and measures only the 0.0073 nm; the 0.0148 nm the other limit rests on is not named | Fixed: the entry says §5.2's NOTE takes the new method and 2WCD's numbers; decision 11 names §5.2's limits; criterion 8 names both numbers and both clauses |
| 5 | Nit | The plan, criterion 7 | "Ruled by the author or carried with its owner", then "The phase does not close on an unruled one". A carried proposal is unruled, so the second sentence withdraws what the first and §8.1's gate allow | Fixed: "on one neither ruled nor carried" |
| 6 | Nit | The plan, the WP6.01 and WP6.03 entries' live lines | "REV-279 waits for the rescoping round", which has placed it in WP6.05. "The tag `copilot-host` waits for the author's push", while the tag is on the remote, `current.md` says pushed, and this amendment removed its row from *What the author supplies* | Fixed: both lines say what holds; the old ones are in the record |
| 7 | Nit | The plan, the ruling round's entry, the Status line and *What the author supplies* | WP6.05 is "planned" in the Status line and in `current.md`, "`/np-plan amend 6` then plans WP6.05" in the round's entry, and "stays unplanned" in the table. BB1 has the further amendment plan what is left and WP6.05's own plan written after the round | Fixed: the amendment "confirms WP6.05's entry", and the table says its plan stays unwritten |
| 8 | Nit | `phase-6-record.md`, the new section | §8.2.16 R4 asks for the replaced text quoted as it was. The section quotes ten passages and gives the rest in a closing paragraph: the Context's paragraph on the rulings, the risks and exclusions, the design rows on the field reading and the speed, and the work packages' lead with its estimate of 5 sessions a package | Fixed: those passages are quoted. The In brief and the report's two lines stay summarised |
| 9 | Nit | The plan, open decision 11 against criterion 8 | The decision is the author's "before any measurement", and the criterion's prediction rests on whether a plane of 2WCD holds a split tie, "which WP6.05's plan measures first" | Fixed: "before the fix is measured" |
| 10 | Nit | §2.7's v0.7 row; record 52, BB2's last cell | §8.1's Phase 6 row takes BB2's reach and BB1's order. §2.7's v0.7 row describes the same review and the same fix and takes neither. Nothing in it contradicts a ruling: it gives content and no order | Fixed in the review turn: §2.7's v0.7 row takes the reach and the order in §8.1's words, and BB1's and BB2's last cells and `holds-now.yaml` name §2.7. Neither ruling changes |

## Checked and found true

`v0.7.0-alpha.1` to `v0.7.0-alpha.3` and `copilot-host` are published, so WP6.04 takes `v0.7.0-alpha.4` and WP6.05
`v0.7.0-alpha.5` by §8.4.1. Record 52 has its front matter, heading, paragraph and table as `rulings.md` asks; the
series continues at BB; `holds-now.yaml` has one line for BB1 and BB2, in order; BA8 and BA11 carry only a pointer
in their first cell and keep their text; the index and `mkdocs.yml` list the record. The In brief's cost is §8.1's
and §8.3's: 9, 2, 4 and 50 sessions make `current.md`'s 65, and the hours and touches make 53 to 106 and 101.
`structure/stage.py` `align` sets `channel = axis_mode == "cavity" or n == 1`. REV-279's numbers are as the plan
gives them: 3 of 8 draws, 0.22° to 0.62° off. VER-48 holds 10⁻⁶ rad for the wall and 0.0073 nm to 10⁻⁴ nm for 2WCD,
and `test_ver48_2wcd_channel_axis_agrees_with_its_ring_axis` builds its own store for the `cavity` run, so it meets
a changed method with no stale artefact. No live file outside the records gives a package number from WP6.06 to
WP6.18. The plan has each section `phase.md` lists, and `current.md` names `/np-plan amend 6 review` before the
level's own next step.

## Not assessed

- What the author answered at the two questions: the session's transcript was not read.
- The six unchanged facts of *True of the codebase today*.
- Whether 2WCD's 28 planes hold a split tie, on which criterion 8's prediction rests: it needs a run.
- The estimates beyond their arithmetic.

The author's rulings BB1 and BB2 are unchanged by the fixes.
