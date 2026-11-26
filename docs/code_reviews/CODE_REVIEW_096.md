# Code review 096: the chore that brings the ship's docs to their merged state (§8.4.4)

2026-11-26 · branch `chore/ship-current-md`, head `98a696f` on base `faa3666` · scope: 2 commits, 2 files, +8 and −5,
read from `git diff faa3666...98a696f`, against the chore's statement (no plan), §8.4.4, `.claude/workflow/core.md`
(*Two lanes*, *Records*, *Gate and push*), `np-ship/wp.md` and `phase.md`, `np-implement/finish.md`, `np-carry/SKILL.md`,
`steward/SKILL.md`, `.claude/workflow/author.md`, `CONTRIBUTING.md`'s *Versions and releases* and `CLAUDE.md` ·
reviewer: `np-reviewer`, Opus 5.5 at high effort · status: completed.

Static review of Markdown under `docs/plans/` and `.claude/skills/`: no code, test or permission line changed. Probes:
`origin/main`'s log and the `v0.7.0-alpha.8` tag on the remote; the WP6.08 plan's ticks and Outcome shas against
`origin/main`; the In brief's and `current.md`'s word counts after the fixes (168 and 651).

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Medium | `.claude/skills/np-ship/wp.md:100` | Axis 2, the statement. "Bring every document to its merged state" has no bound: a ship session could rewrite `CHANGELOG.md`, `CITATION.cff`, a clause or a knowledge note in `docs: WP<n> review recorded`, a commit no reviewer reads. The statement names `current.md`, the Status lines and the ticks. Confirmed | Fixed: the step names those records alone |
| 2 | Medium | `.claude/skills/np-ship/wp.md:101-102` | Axis 1, §8.4.4 ("each package edits only its own" position line) and the core's *Two lanes*. The step has the ship drop a line from *Next* and name the next step, with no exception while two lanes are open, so a ship could rewrite the other lane's line | Fixed: with two lanes open the step edits only its lane's position line |
| 3 | Low | `.claude/skills/np-ship/wp.md:102-103` | Axis 2. "Status lines and ticks likewise" names no merged state: `np-implement/finish.md` sets `delivered, <date>`, a phase close reads "closes at the merge and the tag", and a tick has no merged form. A session could write a "merged" status no other skill knows, or tick an item left unticked with its reason and row. Doubt | Fixed: the Status lines read delivered as `finish.md` says, with no "awaiting its merge"; the ticks name the branch's commits; an unticked item stays unticked |
| 4 | Medium | `docs/plans/current.md:7-18`, `:23-24` | Axis 2, `current.md`'s *Handoff Rules* ("finishing a package replaces the position"). Commit `11a150b` brought *Next* and one position line to the merged state but left the In brief ("built and awaits its review"; *Your call*: "merge the package") and "WP6.01 to WP6.07 merged, tagged to `v0.7.0-alpha.7`", which contradicts the WP6.08 line below it. The new step also left the In brief out, so every ship would leave it stale on `main`. Confirmed | Fixed: the In brief is rewritten for the next step, with the package's measured cost from its Outcome; the position reads WP6.01 to WP6.08 merged, tagged to `v0.7.0-alpha.8`; the step has the ship rewrite the In brief |
| 5 | Low | `.claude/skills/np-ship/wp.md:105` | Axis 1. A line of 135 characters among lines wrapped at about 100 | Fixed: rewrapped, no word changed |
| 6 | Medium | `.claude/workflow/core.md:105`; `np-ship/wp.md` §4 step 3 | Axis 2, the statement's "no docs commit after the merge". GitHub's rebase merge rewrites every commit: WP6.08's ticks `cdb67aa` and `645bc83`, its reviewed head `17e3111` and its fix `3f88e59` are not on `main`. The core says "the next commit corrects the ticks a rewrite moved", and a merge is such a rewrite, so either a commit follows the merge or the ticks name commits outside `main`. This predates the chore, but the chore's claim rests on it. Doubt | Left to the author. *Recommendation:* the core says that a tick and an Outcome sha name the branch's commit, kept reachable by the PR's `refs/pull/<n>/head`, and that a merge's rewrite is not corrected; the other choice, a merge that keeps the shas, would change how the author merges |

The pass fixed five findings and left one.

## Checked and found true

- **The anticipated wording conflicts with no skill.** `/np-carry` reads its stage from the PR's state and the
  branch's subjects, not from `current.md`; `np-ship/wp.md` §0.1 sends a merged PR to §7, and §0.3's resume list
  still names `docs: WP<n> review recorded` as the last commit. `np-ship/phase.md` already has `current.md` point at
  the next phase before the review. `np-implement/finish.md` writes the built state first, and this step replaces it
  in a later commit. The steward writes no document. §8.4.4 does not fix when `current.md` changes, so no clause
  moves.
- **The branch cannot mislead.** `current.md`'s header says an unmerged branch is not shipped. If §7's dispatch
  fails, `main` says "tagged" until the author runs the printed commands, which §7 step 4 always prints; the tag is
  fixed by `CONTRIBUTING.md` from the package's number, so the merge order of two lanes does not change it.
- **No permission.** The diff touches no `.claude/settings*.json`, hook, agent or workflow file. The tag push stays §7's.
- **WP6.08 is merged and tagged.** `faa3666` is on `origin/main` and the remote lists `v0.7.0-alpha.8`.

## Not assessed

- `just land` on this branch and its CI, which the session that started the review runs.
