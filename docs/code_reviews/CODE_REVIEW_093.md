# Code review 093: /np-chore, the second review's doubts ruled

2026-11-26 · branch `chore/np-chore`, head `d74eaa1` on base `56eeebe` (the head CODE_REVIEW_092 read) · scope: one
commit, 8 files, +47 and −18, read from `git diff 56eeebe...d74eaa1`, with the chore's statement in place of a plan:
the author ruled "do all fixes" on CODE_REVIEW_092's findings 8 to 12. Against §8.4.4, §8.4.5, §8.2.57 BG2, BG3,
BG5 and BG6, and REV-295. Read in place: `.claude/workflow/core.md` (*The package's PR and branch*, *Gate and push*),
`land.sh`, the `land` recipe, `duplicates.py`, the other skills' front matter, `np-reviewer.md` · reviewer:
`np-reviewer`, Opus 5.5 at high effort · status: completed.

Static review: no `gate.sh run`. Probes: `decisions.py`, `duplicates.py` and `links.py` after the fixes, all passing;
`pytest -m records`, 3 passed. No code under `src/` or `tests/` changed, so the physics and numerics axis has nothing
to read, and no test is due (§8.2.13 N1). The commit adds no permission line.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Medium | `.claude/skills/np-chore/SKILL.md:44` | Axis 2, BG5. "Run `git fetch origin main` and `duplicates.py` again just before it … If `main` moved, rebase on it": `duplicates.py` reads the working tree alone, so run before the rebase it checks the tree CI already passed and cannot see a number the moved `main` added. The rebase of a pushed branch also needs `--lease` (core, step 7), or `land.sh` step 4 rebases the rewritten branch back on `origin/<branch>` | Fixed in `fcad87b`: fetch, rebase where `main` moved, then `duplicates.py` on the rebased tree, and land with `--lease <the sha last pushed>` where the branch was pushed; §8.4.4, BG5's consequence and REV-295's text say the same order |
| 2 | Medium | `.claude/skills/np-chore/SKILL.md:46`; §8.4.4; BG3's consequence | Axis 2, BG3. A commit after the review is reviewed "unless it is Markdown alone", while BG3 and step 6 always review `.claude/skills/`, `.claude/agents/` and `.claude/workflow/`, whose files are Markdown: a fix to `SKILL.md` or `core.md` after the review would go unread. The gap came from CODE_REVIEW_092's own recommendation 10 | Fixed in `fcad87b`: "unless it is Markdown alone outside the paths step 6 always reviews", in the skill, §8.4.4 and BG3's consequence. The author may reword the record's column |
| 3 | Low | `specification/history/holds-now.yaml:492-495`; BG6's last column | Axis 2. BG6's sentence was written into §8.4.5 (and §8.4.4), but its entry and column named §8.4.4 and the skill alone; BG3's and BG5's new consequences, the red-CI split and the re-run before the land, live in the skill, which their entries did not name | Fixed in `fcad87b`: BG6 names §8.4.5; BG3 and BG5 name `.claude/skills/np-chore/`; `decisions.md` rewritten |
| 4 | Low | `.claude/skills/np-chore/SKILL.md:10` | Axis 1. The opening cited "BG1 to BG5" beside BG6 | Fixed in `fcad87b` |
| 5 | Low | `.claude/skills/np-chore/SKILL.md:45` | Axis 2, BG3 against §8.4.5, a doubt. A red CI's failure other than format and lint goes to a fresh `np-builder`, but a failed land, whose gate runs the same `mypy` and tests, the session fixes itself, on Sonnet 5.5 at medium where the chore touches no `src/` or `tests/`. The ruling spoke of a red CI alone | Left to the author. Recommendation: a land's failure other than format and lint follows the red CI's rule, to a fresh `np-builder` |
| 6 | Low | `.claude/skills/np-chore/SKILL.md:17` | Axis 2, BG2, a doubt. "A worktree on a `claude/np-carry-*` or package branch": a package's branch has no name pattern (core, *The package's PR and branch*, finds it from the PR's title), so a session cannot tell from `git worktree list` which other branch is a package's | Left to the author. Recommendation: refuse on any worktree besides this one whose branch holds commits past `origin/main`, which needs no name |

The pass fixed four findings and left two, both doubts.

## Checked and found true

- **`disable-model-invocation` is a valid skill key.** No other skill and no knowledge note uses it; the installed
  Claude Code, 2.1.332, reads `disable-model-invocation` from a skill's front matter in its skill loader, beside
  `user-invocable`, so the model cannot start `/np-chore` and the author's `/np-chore` still does. The description
  "Use only on /np-chore" agrees.
- **The records agree.** After the fixes the skill, §8.4.4's bullet, §8.4.5's sentence, BG2 to BG6 and their
  `holds-now.yaml` entries, the history index's entry and REV-295's row and section say the same; `decisions.md`
  matches the records, and the counts (493 rulings, 295 REV rows) are the generator's.
- **Findings 8, 10, 11 and 12 are carried as ruled.** The dead hand-off-note refusal is gone, the checks say they see
  this checkout alone, the after-review review and the red-CI split are in the skill, §8.4.4 and BG3, and the model
  sentence is in §8.4.5, §8.4.4 and the skill. Finding 9's repository setting is REV-295, `process`, `open`.
- **The skill and the core.** Step 7 now names the core's step 7 and its `--lease` for a rewritten branch; the
  red-CI split matches §8.4.5's ship rule and the core's "give it to a fresh `np-builder`". BF11 stands: the chore's
  session lands, and no helper can start the skill.

## Not assessed

- `just land` on this branch and the chore's CI, which the chore's session runs.
- The repository setting REV-295 asks for.
