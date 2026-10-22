# Ship a work package

`/np-ship [wp <n>]`. Steps 3 and 4 of the implementation workflow, run as one unbroken sequence.
Normally `/np-implement` has already opened the PR; reuse it. If there is none, and the author
names the branch, this invocation authorises opening it without asking again. The review, fixes and CI watch need no further prompt.

## 0. Resolve the package's PR and branch

1. Resolve them as the core's *The package's PR and branch* says. If no open PR matches and a
   merged one does, go to §7.
2. No PR resolved and no commits beyond `origin/main`: stop. A plan on `main` is no evidence the
   package was implemented.
3. If the PR's **Verification** records a completed review at the current head, go to §5.

## 1. Preflight

Read the WP's Execution brief and verification evidence, locating it from `docs/plans/current.md`.
A brief is navigation, not a review oracle: read normative sections independently.

Confirm: every in-scope `VER-`/`VAL-` the plan claimed
has its test (`SPECIFICATION.md` §8.2.13 N1, N3), and each other claimed identifier is checked against the code at review;
`SPECIFICATION.md`, `knowledge/` and the Outcome annotations are committed; `CHANGELOG.md` has the
package's section (`CONTRIBUTING.md`, *Versions and releases*). If the branch is `main` or equals
`origin/main`, stop and ask. If it is behind `main`, merge `main` in.

## 2. Push

If §1 changed the tree, or `<head>` is ahead of `origin/<head>`, gate and push to `<head>` (the
core).

## 3. Open or reuse the PR

Reuse the PR from §0. Only when §0 found none and the branch carries the package's commits, open
one by the core's *PR contract*; this section starts no review or monitoring.

## 4. Review pass

Subscribe to the PR's activity (`subscribe_pr_activity`) so CI results and review comments wake
this session. Read `.claude/rules/physics-numerics.md` and `.claude/rules/python.md` now: the review
and your adjudication of its fixes need them, and a path-scoped rule does not load while you read
only the diff.

**Test scope first.** Before the review, read the pull request's added and changed tests
(`git diff origin/main...HEAD -- tests/`) against the test scope of `SPECIFICATION.md` §8.2.13 N1: a
test stays only if it guards physics or numerics, a core mechanism, or a licence or architecture
guard, or is a thin entry-point smoke test, or a refusal that is a numerical or physical gate. Read
the diffs in physics and numerics areas with the `physics-reviewer` agent. Delete each test outside
that scope in its own commit, `test: drop tests outside the test scope`, with the identifiers in
the body (N5). The gate runs before each commit.

Push every pre-review commit, the test drops included (the core's gate and push), then write the
PR's head and base SHAs under its **Verification**: the review covers that head, and the record
survives a compaction.

Run the review from this session, invoking the skill directly and never wrapped in an `Agent`:

```
Skill(skill="code-review", args="xhigh --fix <pr-number> out=docs/code_reviews/ -- Static review. A finding is never fixed by adding an off-category test (§8.2.13 N1). Run no benchmark, sweep, cost study, gate.sh or pytest --nightly; /np-ship gates the fixes afterwards. Run a command in the foreground only if it ends within 240 s. Start any longer command in the background and poll it with waits of at most 240 s each, re-issuing a wait that ends.")
```

Wrapped, it returned no findings; called directly it forks its own review agent.

That agent has its own prompt cache, never this session's: a five-minute one, where this session's is
one hour. Any pause over five minutes in it, such as a long test run or a wait on a background job,
re-writes its whole context (about 300k tokens in WP49, twice). A foreground command that runs past
five minutes costs the same as a wait, and the commit hook, `gate.sh run` and a full test run all do:
they belong in this session, whose one-hour cache carries them, never in the reviewer. A background
job polled every 240 s costs about a tenth of one rewrite per poll. Keep the review gap-free; do not
lengthen the cache TTL instead, since a one-hour write costs more than a five-minute one and pays only
when a long pause cannot be avoided. The fixes are verified by the gate in step 3, not by the reviewer.

**The pass must produce evidence that it completed, not that it edited files.** Wait for the
review skill's final report, which must establish the reviewed revision, completed status and the
findings (an explicitly empty list is valid) with any it could not assess or fix, and correlate it
with the SHAs recorded above. Zero findings needs no retry. Missing evidence permits one retry after
the first dispatch has finished or failed, never a concurrent duplicate; if completion still cannot
be established, stop before §5 and report it. An unavailable review tool is a blocker. If the PR
base or head changes during review, review the uncovered changes first.

`--fix` writes to the working tree and does not commit. Back in this session:

1. Read every applied fix as a diff. A finding is a hypothesis: confirm it against the
   specification and the plan, and revert a wrong fix with the reason in the PR thread. This stays
   in this session.
2. A finding the pass could not fix: fix it here, or record a `REV-nn` row in
   `docs/project/review-findings.md` with its section in `review-items.md` (§8.2.8 H12) and list it
   in the PR body under **Deliberately not done**. One the author has not ruled on is `open`; put
   it to the author before the report. Never leave a confirmed finding unmentioned, or only in the
   PR body.
3. Commit accepted changes and the review's report as `fix: close the review gaps in <what>`,
   identifiers in the body; a clean review commits its report alone, `docs: code review <NNN>`.
   Gate and push (the core).

Then record the pass under **Verification**: what was invoked, how many findings came back and
survived step 1, the reviewed base and head SHAs, and any fix commits, distinguishing the
independently reviewed revision from the fixes adjudicated here. Put a finding that is
architectural or would widen the package to the user; scope is the author's.

## 5. Drive to green

Follow `.claude/skills/steward/SKILL.md`, which also applies when a PR event wakes the session
later: its *Bounded wakes* set the polling, fallback check-ins and what counts as a new failure.
Never wait on CI with `sleep`, and report a missing subscription or scheduler as an automation limit.

## 6. Report once

When CI is green and the PR is mergeable, tell the user in one message: the PR link, the checks
that passed, what the review changed, anything left for them to decide, and the tag for the last
commit on `main` after the merge (`CONTRIBUTING.md`). The merge is theirs; `/np-ship` after the
merge pushes the tag (§7). Cancel any
outstanding fallback check-in and unsubscribe from the PR's activity, so the merge does not wake a
cold session, then stop. A later `/np-ship` resumes: it subscribes again if the PR is still open.

## 7. After the merge

The package's last commit on `main` takes its tag: `vX.Y.Z-alpha.N` from its `CHANGELOG.md` section
(`CONTRIBUTING.md`, *Versions and releases*), or the release tag for a close (`phase.md`). Fetch
`main` (a hosted clone is shallow), then `git tag -a <tag> <merge sha> -m "<tag>"` and
`git push origin <tag>`, if this session's access allows it (§8.4.1); otherwise print the two
commands for the author. Report the tag, pushed or printed, and stop.
