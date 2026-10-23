# Code review: PR 124, WP53's workflow commands and the session-start hook

23 October 2026 · `e4b52bc..dd1adfc` (`ccr-a62c64fc-ixc0r7`) · scope: the pull request's diff ·
focus: correctness, convention · effort: xhigh, with `--fix` · status: completed

## Summary

The pull request moves four skills into three commands over a shared core, writes the session-start
hook's fast-forward, and repoints the live mentions. It adds no code under `src/` and no test. The
rules moved are largely intact; a sentence-by-sentence comparison of the four old skills against the new
files found no dropped rule that changes behaviour. The defects are in the new connective text and in
the hook.

The most serious: the core resets the package's branch with `git checkout -B` on every `/np-implement`
resume, which discards the commits of an item that were committed but not pushed (finding 1). The
`/np-ship` resume shortcut (§0.3) can never fire, because a review always adds its own commits, and it
would also skip the PR subscription that §6 promises (finding 2). R7, a ruling with no clause to amend,
has no home in §8.4, against R3 and the pull request's own `rulings.md` (finding 3). The core runs the
strict documentation build after the gate, and the build rewrites the tracked `mkdocs.yml` when a ruling
adds a `history/` record, so the first `/np-plan phase` leaves a dirty, ungated file (finding 4).

Nine findings are fixed in the working tree, uncommitted; two are left to `/np-ship` and the
author. The hook was exercised on ten scratch repositories before and after the fix (clean, dirty and
diverged `main`, a feature branch, a detached `HEAD`, a missing origin, a linked worktree, a
`--depth 1` clone). No test was added or run, and the push gate and the strict documentation build were
not run.

| Severity | Count |
|---|---:|
| Medium | 4 |
| Low | 7 |

## Findings and their outcome

| # | Location | Finding | Outcome |
|---|---|---|---|
| 1 | `.claude/workflow/core.md` *The package's PR and branch*, step 2 | `git checkout -B <head> origin/<head>` resets the local branch to the remote. `/np-implement` makes one commit per item and pushes only at a checkpoint or at the end, and the core runs this step again on each resume. Commits made since the last push (or after a refused push, which the same section anticipates) are orphaned and the plan's ticks, read from `origin`, send the session back over the items. | Fixed: a local `<head>` with commits that `origin/<head>` lacks is checked out and pushed through *Gate and push*; only otherwise is it reset. |
| 2 | `.claude/skills/np-ship/wp.md` §0.3; `np-ship/phase.md` step 4 | "If the PR's Verification records a completed review at the current head, go to §5." The pass ends with a `fix:` commit or a `docs: code review` commit, so the current head is never the reviewed head and the shortcut never fires; a resumed `/np-ship` reviews again (about 600k tokens) and moves the head again. Where it is read loosely, it jumps over §4's subscription although §6 says a later `/np-ship` "subscribes again". `phase.md` also sent a resumed close through §4 although §0.3 said §5. | Fixed: §0.3 holds when the only commits after the reviewed head are the recorded fixes and the report, subscribes first, and `phase.md` step 4 runs §5 and §6 in that case. |
| 3 | `specification/history/index.md` R7; §8.4 | R7 is a standing rule of process (the hook writes to the author's checkout only by a fast-forward of a clean `main`) with no clause to amend. R3 and §8.4.4 ("Every ruling lands in a current clause. One with no clause to amend is written here once"), and the pull request's own `rulings.md`, put it in §8.4. The index sent it to a script path, which is none of the index's stated homes (a clause, a §8.4 rule, `superseded`, `open`, `spent`). | Fixed: a §8.4.2 bullet states the hook's behaviour in the present tense, and the index reads `R7 - §8.4.2`. |
| 4 | `.claude/workflow/core.md` *Gate and push*, steps 2 and 3 | The strict build ran after the gate. `docs/scripts/generate.py` rewrites the tracked `mkdocs.yml` navigation when a page is new, and `rulings.md` makes every ruling round a new `history/` record, so the first `/np-plan phase`, `amend` or `project` leaves an uncommitted, ungated `mkdocs.yml` after the gate (the push guard reads `HEAD`'s tree, so the push still goes and sends a stale navigation). The old `phase-plan` built first. The list of sources also left out `CHANGELOG.md`, `examples/*/README.md`, `data/corrections/` and `mkdocs.yml`, which `generate.py` copies into the site, so a change to only one of them skipped the build that CI runs. | Fixed: the build comes first, commits any navigation change, and the list names the missing sources. |
| 5 | `.claude/hooks/session-start.sh` (primary checkout block) | The hook compares the primary checkout's `HEAD` with `origin/main`, but a session in a linked worktree (`claude --worktree`) reads the worktree's own skills. A worktree on a branch forked before the latest `main` printed only "main (the primary checkout, …) fast-forwarded", which reads as current, and nothing about its own stale skills. | Fixed: when the root is a linked worktree and the fetch succeeded, a warning names a worktree `HEAD` that lacks `origin/main`. Checked on the scratch repositories (a worktree on a feature branch, and one on a stale `main` with the primary on another branch). |
| 6 | `.claude/skills/np-plan/amend.md` (opening and step 5) | "It has the same two turns as `phase.md`", which `/np-plan amend` does not load. `phase.md` and `project.md` carry "Commit nothing in this turn"; `amend.md` and `rulings.md` do not, so an amendment session may commit before the author has ruled. Step 5 said "Report, and stop" with no content, against the core's "the report that its file names". | Fixed: "Commit nothing in the ruling round" and the report's content, as `phase.md` gives it. |
| 7 | `.claude/skills/np-ship/wp.md` §0.1 and §7 | §0.1 sends a merged PR to §7, but the core lists open PRs only, so the route cannot be reached. §7 names `<merge sha>` without saying where it comes from, and a second `/np-ship` after the tag is pushed runs `git tag -a` and `git push` on an existing tag. | Fixed: §0.1 lists the closed PRs by the REST route (GraphQL is not available to a hosted session), §7 takes the merge sha from the PR and stops when `git ls-remote --tags` lists the tag. |
| 8 | `docs/plans/wp53-workflow-commands.md` item 11; `docs/project/review-findings.md` | D2's caps (core 900, an invocation 2,200, all files 7,000) are exceeded (974; 2,282 to 2,995; 7,409). The overshoot is recorded in the plan's Outcome and the pull request body only. `CLAUDE.md`, *Open items*: "a finding not fixed, a deferral … are `REV-nn` rows … until the commit that resolves one sets it `fixed`"; §8.4.6: "A pull request body is never its only record". | Fixed: REV-125, `open`, with a recommendation. The author rules whether the caps or the files give way. |
| 9 | `.claude/skills/steward/SKILL.md` *The environment* | Still said "Start it with Bash `run_in_background` … and push when it passes", while `CLAUDE.md` and the core now say to wait for the gate in the same turn. A session woken by a PR event follows the steward and ends its turn on an unpushed commit, which trips the stop hook. The pull request states that "the gate has one waiting rule". | Fixed: the steward points to `CLAUDE.md`'s *Commands* and the same-turn wait. |
| 10 | `.claude/workflow/core.md` *The PR contract*, last paragraph; `np-plan/wp.md` Finishing 3; `np-implement/wp.md` Finishing | The `PR:` line is still written under every plan's title, as its own commit followed by a full gate run and a push, but item 9 removed the only reader (`/np-ship` no longer falls back to it, and the core finds the PR by title). | Not fixed: plan item 9 decided "the `PR:` line is no lookup fallback, and is written only when missing". Drop the step, or restore the fallback in the core. For the author. |
| 11 | `.claude/workflow/core.md` *The package's PR and branch*, step 1 | The PR is found by `WP<n>` and an em dash in the title. A PR whose title a person edits to use a hyphen, or to drop the `WP<n>` token, is not found. A second package's plan PR makes "the one open PR that names a package" ambiguous, so `/np-implement` and `/np-ship` with no argument always ask while two plans are open. | Not fixed: the lookup is the pull request's decision (D1); the cost is an extra question. For `/np-ship` to record if the author wants a sturdier key (the `PR:` line, finding 10, would be one). |

## Verified and found clean

- Every cross-reference of the new files resolves: `CLAUDE.md`'s *Models*, *Open items*, *Durable
  learnings*, *Commands* and *Testing*; `CONTRIBUTING.md`'s *Versions and releases*; the history
  record's format and the index's two kinds of line; `phase-3-charge-pipeline.md`; `phase-4-record.md`'s
  header.
- No live file outside the records names an old command: `grep` over `.claude/`, `.github/`, `tests/`,
  `docs/project/`, `CONTRIBUTING.md` and `README.md` finds only the core's opening and `CLAUDE.md`'s
  "Plans before WP53" sentence. No test reads `.claude/`.
- `SKILL.md` front matter parses as plain YAML, `name` equals the directory, and the routers name the
  files they load.
- §8.4.1 allows the tag push in `np-ship` §7 (the session pushes it if its access allows, otherwise
  prints the commands).
- The hook, on ten scratch repositories, after the fix: a clean `main` behind is fast-forwarded and
  reported; a dirty, a diverged, a branch, a detached and a missing-origin checkout each print one warning
  and write nothing; a current `main` prints nothing; a `--depth 1` clone fast-forwards; a linked
  worktree reports the primary and its own state. `bash -n` is clean. A failing `uv sync` is a warning
  line, as the plan states.
- The WP53 plan holds 2,833 words outside its Outcome annotations (1,495 outside *Grounding* and
  *Implementation details*) and six decisions, within its own caps.

## Not run

The push gate, the test suites, `--nightly`, `shellcheck` (not installed) and the strict documentation
build (the `docs` group is not synced here). `/np-ship` gates the fixes; CI's `docs` job builds the
site.

## Disposition (`/np-ship`)

To be filled in by `/np-ship`: findings 10 and 11 are left to it and the author, as REV rows if the
author wants them kept.
