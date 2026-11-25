# Code review 091: WP6.07, the findings pulled in and BF10 and BF11

2026-11-25 · PR #219, head `20873b1` on base `db4d63c` (the head CODE_REVIEW_090's fixes left) · scope: the diff of
the findings the author pulled in, 38 files, +390 and −241, read from `git diff db4d63c...20873b1`, not a full pass
(§8.2.56 BF8): REV-290 to REV-293 (`ac4fb37`, `5806145`, `693d25f`), the renumbering 6.09 → 6.07, 6.07 → 6.08,
6.08 → 6.09 (BF10, `f9f4554`), and BF11 (`20873b1`). Against §7.6, §8.4.2, §8.4.4, §8.4.5, §8.2.56 BF1, BF8, BF10
and BF11 and §8.2.54 BD1. Read in place: `.claude/workflow/core.md` (*Gate and push*), `land.sh`, the `land` and
`gate` recipes, `gate.sh`'s prose path, `ci.yml`'s `changes`, `lint` and `docs` jobs, the steward's *Bounded wakes*,
`np-plan/wp.md`'s *Finishing* and `tests/tier1/test_written_architecture.py` · reviewer: `np-reviewer`, Opus 5.5 at
medium effort · status: completed.

Static review: no `gate.sh`, no `pytest`, no benchmark. Probes: `prose-only.sh` on `gate.sh`, `decisions.py`,
`index_records.py`, `settings.json`, a `src/` Markdown file, the script itself and this diff's own paths (code, as
`prose-only.sh` changed); `ruff check . --show-files`, which walks `.claude/scripts/` and its `gui/` folder; a search of
`tests/` for any read of `.claude/` or of the repository's tree. No code under `src/` or `tests/` changed, so the
physics and numerics axis has nothing to read, and no test is due (§8.2.13 N1, N3).

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Medium | `.claude/skills/np-ship/wp.md:118`, §5 | Axis 2, BF11 and the steward's *Bounded wakes*. After §4 the shipper holds the reviewer's commits and `docs: WP<n> review recorded`, unpushed, and §4 step 3 gives them to "its `WAIT` of §5". But §5 first follows the steward, which reads the live PR: its checks are those of the head landed before the review. Green there, a shipper goes on to §6, reports green and hands back `DONE`; the land then pushes the review's fixes, and no helper drives their CI. The same holds for any shipper that committed since the last land | Fixed: a helper that committed since the last land reads no CI and hands back `WAIT`, `land: yes`, first |
| 2 | Low | `.claude/skills/np-ship/wp.md:86`, §4 | Axis 2, BF11 against `np-carry` §4. The shipper records the head under **Verification** before the land; the land may add its own commits (the registers, the navigation) or rebase, and the main session then gives the reviewer the landed sha. The reply's head no longer matches the recorded one, so the next shipper reads the pass as incomplete and starts the reviewer again | Fixed: under `/np-carry` the reply may name a head whose commits after the recorded one are `just land`'s own |
| 3 | Low | `specification/history/holds-now.yaml:489` | Axis 2, BF11's last column: it changes `CLAUDE.md`'s *The gate* and *Implementation workflow*; the entry names only the first | Fixed |
| 4 | Low | `docs/plans/phase-6/wp6.07-the-lean-carry.md:5` | Axis 2, BF11. The plan's opening still inherits "§8.2.56 BF1 to BF10", while its Outcome, the Phase 6 plan's entry and the changelog carry BF11 | Fixed |
| 5 | Low | `specification/history/holds-now.yaml:488` | Axis 2, BF10. The entry names §8.4.1 as where BF10 holds, while BF10's own row says "§8.4.1 is unchanged" and amends §8.2.54 BD1. The project's entries name an amended ruling on the amended side (BD1's entry names BF10), so leaving BD1 out follows the convention; naming §8.4.1 may be meant as the rule BF10 keeps. A doubt | Not fixed: the wording is the author's ruling record. Recommendation: `'the Phase 6 plan; the WP6.07 plan; §8.4.1, unchanged'`, or drop §8.4.1 |

The pass fixed four findings and left one, a doubt.

## Checked and found true

- **The renumbering (BF10).** Every reference in the plans, registers, records, knowledge, changelog, `mkdocs.yml`,
  `land.sh` and `holds-now.yaml` that names the lean carry, the guard numbers or the kernel's design pairs it with
  WP6.07, WP6.08 and WP6.09; the kernel's packages start at WP6.10; no link reaches the old file names. What still
  reads the old numbers is what BF10 keeps: CODE_REVIEW_090, §8.2.50's AZ2, AZ4 and AZ5 and the Phase 6 record's
  quotations (BA4's numbering), and REV-292's finding.
- **Prose, the gate and CI agree.** `prose-only.sh` exits 1 for `.claude/scripts/decisions.py` before it reaches
  `.claude/*`, and 0 for the rest of `.claude/`. The gate on a prose tree skips the lock check, `mypy` and the suite
  and runs ruff, the decisions page's check and the `records` tests; CI's `lint` job now runs ruff on every change
  and `mypy` on code alone, and its `docs` job the decisions check, the links and the strict build. §7.6, §8.4.2,
  `CLAUDE.md` *The gate*, the gate's header and the script's header say the same. Ruff walks `.claude/scripts/`.
- **No test reads a path now counted as prose.** The one test that reads `.claude/` is
  `test_written_architecture.py`, which loads `decisions.py` alone, and `decisions.py` imports nothing else under
  `.claude/`; its `--check` runs on a prose change through the gate and CI directly.
- **The land and hand-back flow.** `helper.md`'s table and `land:` line, `np-carry` §4's *Land first*, the core's
  *Gate and push*, `np-implement/wp.md` and `finish.md`, `np-ship/wp.md` and the three agents' files agree: every
  hand-back kind carries `land:`; the main session lands before it serves, a worker's `DONE` included; a failed land
  goes to a fresh `np-builder`; the reviewer and workers commit and land nothing. Each stage's commits reach a land:
  the plan's through its `ASK` and `DONE`, each checkpoint's and the last item's through `DONE`, the pre-review
  commits through `REVIEW`, the review's through §4's `WAIT` (finding 1), a red CI's fix through `WAIT` or the
  builder's `DONE`. `RUN` is landed first, and no helper or agent starts while a land or a `RUN` runs.
- **REV-290 to REV-293.** Both agents list the four PR tools; the shipper fixes only format and lint and reruns a
  flaky runner once, every other failure going to `np-builder`, in the agent, the skill, §8.4.4, §8.4.5 and
  `CLAUDE.md`; `index_records.py` skips `*-handoff.md` under `docs/plans/` by an absolute path, as `render` passes.

## Not assessed

- `just land` end to end on this tree, the push gate and the strict documentation build, which the main session runs.
- Whether a helper's first PR edit before `origin/<head>` exists is picked up by the next helper: only the note's
  **Next** carries it; WP6.08's carry shows it.
