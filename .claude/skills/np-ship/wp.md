# Ship a work package

`/np-ship [wp <n>]` runs steps 3 and 4 of the implementation workflow as one sequence, without a
stop. Usually `/np-implement` has opened the PR: reuse it. If there is no PR and the author names the
branch, this invocation authorises you to open the PR without asking again. The review, the fixes
and the CI watch need no further prompt.

## 0. Resolve the package's PR and branch

1. Find them as the core's *The package's PR and branch* says. If no open PR matches, list the
   closed PRs against `main` (the REST route `pulls?state=closed`) with the same title rule. If one of
   them is merged, go to §7.
2. If no PR is found and the branch has no commits beyond `origin/main`, stop. A plan on `main` does
   not show that the package was implemented.
3. If the PR's **Verification** records a completed review, and the only commits after its reviewed
   head are the recorded fix commits and the review's report commit, subscribe to the PR's activity
   (§4) and go to §5. A review adds its own commits, so the current head is never the reviewed head.

## 1. Preflight

Read the WP's Execution brief and its verification evidence. A brief is navigation, not a review
oracle: read the normative sections independently.

Confirm these:

- Each in-scope `VER-`/`VAL-` that the plan claims has its test (`SPECIFICATION.md` §8.2.13 N1, N3).
  The review checks each other claimed identifier against the code.
- `SPECIFICATION.md`, `knowledge/` and the Outcome annotations are committed.
- `CHANGELOG.md` has the package's section (`CONTRIBUTING.md`, *Versions and releases*).

If the branch is `main` or equals `origin/main`, stop and ask. If it is behind `main`, merge `main`
into it, and renumber as the core's *Two lanes* says. Then run `uv run .claude/scripts/duplicates.py`
and renumber until it passes.

## 2. Push

If §1 changed the tree, or `<head>` is ahead of `origin/<head>`, gate and push to `<head>` (the
core).

## 3. Open or reuse the PR

Reuse the PR from §0. Open a PR by the core's *PR contract* only if §0 found none and the branch has
the package's commits. This section starts no review and no monitoring.

## 4. Review pass

Subscribe to the PR's activity (`subscribe_pr_activity`), so that CI results and review comments wake
this session. Read `.claude/rules/physics-numerics.md` and `.claude/rules/python.md` now. The review
and your decisions on its fixes need them, and a path-scoped rule does not load while you read only
the diff.

**Test scope first.** Before the review, read the tests that the PR adds or changes
(`git diff origin/main...HEAD -- tests/`) against the test scope (`CLAUDE.md`, *Testing*;
`SPECIFICATION.md` §8.2.13 N1). Read the diffs in physics and numerics areas with the `physics-reviewer` agent. Delete each test
outside the scope in its own commit, `test: drop tests outside the test scope`, with the identifiers
in the body (N5). The gate runs before each commit.

Push each pre-review commit, the test drops included (the core's *Gate and push*). Then write the
PR's head and base SHAs under its **Verification**. The review covers that head, and the record
stays after a compaction.

A PR that changes a screen runs `/np-gui review` and `/np-gui publish`, links the gallery under
**Verification**, and runs `/np-gui collect` before the merge.

Run the review from this session. Call the skill directly, never inside an `Agent`:

```
Skill(skill="code-review", args="xhigh --fix <pr-number> out=docs/code_reviews/ -- Static review. A finding is never fixed by adding an off-category test (§8.2.13 N1). Run no benchmark, sweep, cost study, gate.sh or pytest --nightly; /np-ship gates the fixes afterwards. Run a command in the foreground only if it ends within 240 s. Start any longer command in the background and poll it with waits of at most 240 s each, re-issuing a wait that ends.")
```

Inside an `Agent`, the skill returned no findings. Called directly, it starts its own review agent.

The review agent's prompt cache lives five minutes, against one hour here. Each longer pause in it,
in a test run, a foreground command or a wait, writes its whole context again (about 300k tokens,
twice in WP49); a poll every 240 s costs about a tenth of that. So the commit hook, `gate.sh run` and
full test runs stay in this session, never in the reviewer. Keep the review without gaps. Do not
lengthen the cache life: a one-hour write costs more, and pays only when a long pause cannot be
avoided. The gate in step 3 below, not the reviewer, verifies the fixes.

**The pass must give evidence that it completed, not that it edited files.** Wait for the review
skill's final report. It must give the reviewed revision, the completed status, the findings (an
empty list is valid), and the findings it could not assess or fix. Compare it with the SHAs
recorded above.

- Zero findings need no retry.
- If the evidence is missing, you may retry once, after the first dispatch has finished or failed.
  Never run two at the same time. If completion is still not shown, stop before §5 and report it.
- An unavailable review tool is a blocker.
- If the PR's base or head changes during the review, review the new changes first.

`--fix` writes to the working tree and does not commit. Then, in this session:

1. Read each applied fix as a diff. A finding is a hypothesis: confirm it against the specification
   and the plan. Revert a wrong fix, and give the reason in the PR thread. This step stays in this
   session.
2. For each finding that the pass could not fix: fix it here, or record a `REV-nn` row in
   `docs/project/review-findings.md` with its section in `review-items.md` (§8.2.8 H12), and list it
   in the PR body under **Deliberately not done**. A row the author has not ruled on is `open`: put
   it to the author before the report. Never leave a confirmed finding unmentioned, or only in the
   PR body.
3. Commit the accepted changes and the review's report as `fix: close the review gaps in <what>`,
   with the identifiers in the body. A clean review commits its report alone, as
   `docs: code review <NNN>`. Gate and push (the core).

Then record the pass under **Verification**: what you invoked, how many findings came back and how
many survived step 1, the reviewed base and head SHAs, and the fix commits. Keep the independently
reviewed revision apart from the fixes decided here. Give the user each finding that is
architectural or that would make the package wider: scope is the author's decision.

## 5. Drive to green

Follow `.claude/skills/steward/SKILL.md`. It also applies when a PR event wakes the session later.
Its *Bounded wakes* set the polling, the fallback check-ins and what counts as a new failure. Never
wait on CI with `sleep`. Report a missing subscription or scheduler as an automation limit.

## 6. Report once

When CI is green and the PR is mergeable, tell the user in one message: the PR link, the checks that
passed, what the review changed, what is left for them to decide, and the tag that the last commit
on `main` gets after the merge, or that it gets none (`CONTRIBUTING.md`). While the other lane has
a PR open, say that whichever merges second needs `/np-ship` again on the new `main` before its
merge (§8.4.4). The merge is theirs; `/np-ship` after the merge
pushes the tag (§7). Cancel each open fallback check-in and unsubscribe from the PR's activity, so
that the merge does not wake a cold session. Then stop. A later `/np-ship` resumes, and subscribes
again if the PR is still open.

## 7. After the merge

The package's last commit on `main` gets its tag: `vX.Y.Z-alpha.N` from its `CHANGELOG.md` section
(`CONTRIBUTING.md`, *Versions and releases*), or the release tag for a close (`phase.md`). A
package merged before its previous phase's release gets no tag, although its section names a
release (the core's *Two lanes*): report that, and stop.

1. Fetch `main`: a hosted clone is shallow. The merge sha is the `merge_commit_sha` of the merged PR.
2. If `git ls-remote --tags origin <tag>` lists the tag, report it and stop.
3. If the access of this session allows it (§8.4.1), run `git tag -a <tag> <merge sha> -m "<tag>"`
   and `git push origin <tag>`. Otherwise print the two commands for the author.
4. Report the tag, pushed or printed, and stop.
