# Ship a work package

`/np-ship [wp <n>]` runs the review and the CI watch after `/np-implement` as one sequence, without a
stop. It runs on Sonnet 5.5 at medium effort (§8.2.56 BF1): in a fresh session, in the implementing
session after its compaction where that runs on the same model (§8.2.33 AI4), or as `np-shipper`
under `/np-carry`. Of code and tests it fixes only a red CI's format and lint: the reviewer and
`np-builder` write every other fix. Where this file says to gate and push, a session run directly
lands as the core says; `np-shipper` commits, goes on to its next hand-back and gives it `land: yes`,
or `lease <sha>` after a rebase on `main`, and the main session lands (§8.2.56 BF11).
Usually `/np-implement` has opened the PR: reuse it. If there is no PR and the author names the branch,
this invocation authorises you to open the PR without asking again. The review, the fixes and the CI
watch need no further prompt.

## 0. Resolve the package's PR and branch

Run `.claude/hooks/checkpoint.sh clear`: an automatic pause that led here is spent
(`np-implement/finish.md`, *Finishing*).

1. Find them as the core's *The package's PR and branch* says. If no open PR matches, list the closed
   PRs against `main` (the REST route `pulls?state=closed`) with the same title rule. If one of them is
   merged, go to *7. After the merge* below.
2. If no PR is found and the branch has no commits beyond `origin/main`, stop. A plan on `main` does
   not show that the package was implemented.
3. **Resuming after a review.** Suppose the PR's **Verification** records a completed review, and
   the only commits after its reviewed head are a helper's `docs: WP<n> hand-off, …`, the
   reviewer's commits, `just land`'s own (`docs: the decisions page and the indexes`, `docs: the
   navigation`) and `docs: WP<n> review recorded`. Then subscribe to the PR's activity (§4) and go to §5. A review adds its own commits, so
   the current head is never the reviewed head.

## 1. Preflight

Read the WP's Execution brief and its verification evidence. A brief is navigation, not a review
oracle: read the normative sections independently.

Confirm these:

- Each in-scope `VER-`/`VAL-` that the plan claims has its test (`SPECIFICATION.md` §8.2.13 N1, N3).
  The review checks each other claimed identifier against the code.
- `SPECIFICATION.md`, `knowledge/` and the Outcome annotations are committed.
- `CHANGELOG.md` carries the package's entry as `CONTRIBUTING.md`'s *Versions and releases* says. A
  package that takes a tag has the heading `tag.yml` greps (`grep -qF '## [X.Y.Z-alpha.N]' CHANGELOG.md`).

If the branch is `main` or equals `origin/main`, stop and ask. If it is behind `main`, rebase it on
`main` (the core's *Gate and push*, step 7) and renumber as the core's *Two lanes* says. Then run
`uv run .claude/scripts/duplicates.py` and renumber until it passes.

## 2. Push

If §1 changed the tree, or `<head>` is ahead of `origin/<head>`, gate and push to `<head>` (the core).
`np-shipper` goes on: its `REVIEW` hand-back carries the land.

## 3. Open or reuse the PR

Reuse the PR from §0. Open a PR by the *PR contract* of `.claude/workflow/finish.md` only if §0 found none and the branch has
the package's commits. This section starts no review and no monitoring.

## 4. Review pass

Subscribe to the PR's activity (`subscribe_pr_activity`), so that CI results and review comments wake
this session; a helper of `/np-carry` skips it, as its main session holds the subscription.

**The test scope is the reviewer's.** A test the PR adds or changes outside the test scope
(`CLAUDE.md`, *Testing*; `SPECIFICATION.md` §8.2.13 N1) is a finding of its first axis, and the
reviewer drops it as a fix, with the identifiers in the body (N5); this session deletes no test.

Push each pre-review commit (the core's *Gate and push*); `np-shipper` gives its `REVIEW` hand-back
`land: yes`, and the main session lands before it starts the reviewer. Then write the PR's
head and base SHAs under its **Verification**. The review covers that head, and the record stays after
a compaction.

A PR that changes a screen runs `/np-gui review` and `/np-gui publish`, links the gallery under
**Verification**, and runs `/np-gui collect` before the merge.

**The review** is one pass by `np-reviewer`, on Opus 5.5 at high effort: standards, the
specification and the physics and numerics together, and it fixes and commits what it confirms
(§8.2.56 BF4). Start it in the foreground from this session with `Agent`, `subagent_type:
"np-reviewer"`, passing no model and no effort. A helper of `/np-carry` hands back `REVIEW` with the
prompt and ends; a fresh helper goes on with the reply. The prompt:

```text
Review PR #<number> of WP<n>, base <sha>, head <sha>; its plan is <path>. The clauses it cites:
<identifiers>. Drop each test outside the test scope in its own commit, `test: drop tests outside
the test scope`. Run no benchmark, sweep, gate.sh or pytest --nightly.
```

**The reply must show that the pass completed**: the reviewed base and head, which match the SHAs
recorded above, or under `/np-carry` a head whose commits after the recorded one are `just land`'s
own, as the land before the review may add them (§8.2.56 BF11), its commits, the report's path and each finding with its outcome. Zero findings is
valid. If the reply lacks that evidence, start the reviewer once more, never two at a time; if it
still lacks it, stop before §5 and report it. Then, in this session:

1. **A small finding** the reviewer left is fixed now, by `np-builder` (a helper hands back `WORKER`), its
   diff reviewed as below; it gets no row (§8.2.58 BH1). **Each other finding left to the author** is a
   `REV-nn` row, `open` (`CLAUDE.md`, *Open items*), with the
   reviewer's recommendation, listed in the PR body under **Deliberately not done**. The PR merges as
   reviewed; the report of §6 names each row, and the author may pull one in (§8.2.56 BF5). A finding
   pulled in is fixed by `np-builder` (a helper hands back `WORKER`) and its diff alone reviewed by
   `np-reviewer` at `effort: "medium"` (BF8), never a full pass.
2. Delete the hand-off note, `docs/plans/phase-<p>/wp<n>-handoff.md`, if there is one.
3. Bring these records to their merged state now, so that no commit is needed after the merge; the
   tag itself stays §7's. `docs/plans/current.md` says the package is merged and tagged (the tag of
   §6, or that it gets none), drops the `/np-carry`/`/np-ship` line from *Next*, names the next step
   and rewrites its In brief for that step (`author.md`). With two lanes open it edits only its lane's
   position line (the core's *Two lanes*). The package's and the phase plan's **Status** lines read
   delivered, as `np-implement/finish.md` says, with no "awaiting its merge". The ticks name this
   branch's commits (the core's *Gate and push*, step 7); an item left unticked stays unticked.
4. Commit the rows, the deletion, the plan's Outcome and those records as
   `docs: WP<n> review recorded`, with the identifiers in the body. The Outcome takes the package's
   measured cost: the PR's **Measured** lines and this session's so far, summed, beside the In
   brief's estimate (§8.4.5). Gate and push (the core); `np-shipper` gives its `WAIT` of §5
   `land: yes`, which pushes the reviewer's commits with this one.

Then record the pass under **Verification**: the reviewer's report, how many findings it fixed and how
many it left, the reviewed base and head SHAs, and its fix commits. Give the user each finding that
is architectural or that would make the package wider: scope is the author's decision. A restructure
of code the package works with, which changes no behaviour, is neither (§8.4.4).

## 5. Drive to green

Follow `.claude/skills/steward/SKILL.md`. It also applies when a PR event wakes the session later. Of a
red CI this session fixes only format and lint, with `uv run ruff format .` and `uv run ruff check --fix .`,
and reruns a job that failed on a flaky runner once, the steward's infrastructure failure. Every other
failure, the docs, a stale lock, `mypy`, a lint that `--fix` leaves, a test or a numerical gate, goes to
`np-builder` with the log the CI-log classifier classed (a helper hands back `WORKER`,
`agent: np-builder`); this session writes no other fix (§8.2.56 BF1). A helper's format or lint fix
goes out with its `WAIT`, `land: yes`; the builder's fix is landed before its reply comes back
(§8.2.56 BF11). A helper that has committed since the last land, as after §4, reads no CI: the PR's
checks are still those of the head before its commits, so it hands back `WAIT`, `land: yes`, first,
and the helper the event wakes reads CI on the landed head. The steward's
*Bounded wakes* set the polling, the fallback check-ins and what counts as a new failure. Never wait on
CI with `sleep`. Report a missing subscription or scheduler as an automation limit.

## 6. Report once

When CI is green and the PR is mergeable, tell the user in one message:

- the PR link and the checks that passed;
- what the review changed, and each `REV` row it left, which they may pull in before the merge;
- the package's measured cost beside its estimate, and this session's `usage.py` line;
- the tag that the last commit on `main` gets after the merge, or that it gets none
  (`CONTRIBUTING.md`);
- the full tag commands, each in its own `bash` block, ending the message (step 4 of *7. After the merge*, below), with
  `origin/main` for the merge commit: they are right only if run before anything else merges.

While the other lane has a PR open, say that whichever merges second needs `/np-ship` again on the new
`main` before its merge (§8.4.4). The merge is theirs; `/np-ship` after the merge pushes the tag (*7. After the merge*, below).
Cancel each open fallback check-in and unsubscribe from the PR's activity, so that the merge does not
wake a cold session. Then stop. A later `/np-ship` resumes, and subscribes again if the PR is still
open.

## 7. After the merge

The tag is the one `CONTRIBUTING.md`'s *Versions and releases* gives, or none. With none, report that,
and stop.

1. Fetch `main`: a hosted clone is shallow. The merge sha is the `merge_commit_sha` of the merged PR.
2. If `git ls-remote --tags origin <tag>` lists the tag, report it and stop.
3. Dispatch `.github/workflows/tag.yml` on `main` with `tag` and `sha` (`actions_run_trigger`, or
   `gh workflow run tag.yml --ref main -f tag=<tag> -f sha=<merge sha>` where `gh` is installed). Both are
   allowed in `.claude/settings.json`; if one is refused, use the other before you hand back `BLOCKED`. A
   rebase merge gives the PR no `merge_commit_sha`: the sha is the PR's last commit on `main`. It checks the
   tag, the commit and its changelog section, pushes the annotated tag and starts `release.yml` with the
   full matrix (§8.2.33 AI8). Wait for its run, as the steward's *Bounded wakes* say, and read its
   result. A cloud session never pushes a tag itself: its git credentials push only its own branch, and
   GitHub refuses a `refs/tags/` push with HTTP 403 (AI5). Only if the dispatch is refused, and the
   session is not a cloud session (`CLAUDE_CODE_REMOTE` is not `true`), push the tag as the commands
   below do.
4. Report the tag: pushed by the workflow, by this session, or not pushed and why, with the run's link.
   Always end the report with the full commands, the merge sha written out, each in its own `bash`
   block, so that the author can copy them. The first dispatches the workflow; the other three push the
   tag by hand from the author's own clone, if the workflow cannot:

   ```bash
   gh workflow run tag.yml --ref main -f tag=<tag> -f sha=<merge sha>
   ```

   ```bash
   git fetch origin main
   ```

   ```bash
   git tag -a <tag> <merge sha> -m "<tag>"
   ```

   ```bash
   git push origin <tag>
   ```

   Then stop.
