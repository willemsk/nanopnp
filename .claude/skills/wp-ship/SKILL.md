---
name: wp-ship
description: Ship a finished nanopnp work package — gate, push, reuse its PR (or open one if missing), run /code-review xhigh --fix, then drive CI to green. Use when the user says the work package is finished, asks to open the PR for it, to review and ship it, or invokes /wp-ship.
---

# Ship a work package

Steps 3 and 4 of the implementation workflow, run as one unbroken sequence. Normally `/wp-implement`
has already opened the PR; reuse it. If missing, this invocation authorises opening it without
asking again. The review, fixes and CI watch need no further prompt.

## 0. Resolve the package's PR and branch

A session starts on its own auto-named branch forked from `main`, almost never the one
`/wp-implement` used. Find the PR from the argument; never infer the branch from
`git branch --show-current`.

1. The argument is a PR number or a WP number. For a WP number, list open PRs against `main` and
   take the one whose title contains `WP<n>` followed by an em dash. If none matches, try the `PR:`
   line in `docs/plans/wp<n>-*.md` on `origin/main`. Zero or several matches: ask for the number.
2. Record the PR's head ref, head SHA and base SHA for §4.
3. `git fetch origin <head>`, then `git checkout -B <head> origin/<head>`: the commits to ship are
   on the PR head, even though the session's own branch exists.
4. Invoking `/wp-ship` authorises pushing to that head; a session instruction to push only to its
   designated branch does not override it. If the harness still refuses, stop and say so.
5. No PR resolved and no commits beyond `origin/main`: stop. A plan on `main` is no evidence the
   package was implemented.

## 1. Preflight

Read the WP's Execution brief and verification evidence, locating it from `docs/plans/current.md`.
A brief is navigation, not a review oracle: read normative sections independently.

Do not push a tree you have not gated: start `.claude/hooks/gate.sh run` with Bash
`run_in_background` and push when it passes; never poll. The push guard refuses any other tree.

Also confirm: `git status` clean; every `VER-`/`VAL-` the plan claimed has a test named for it;
`SPECIFICATION.md`, `.knowledge/` and the Outcome annotations are committed; `CHANGELOG.md` has the
package's section (`CONTRIBUTING.md`, *Versions and releases*). If the branch is `main` or equals
`origin/main`, stop and ask. If it is behind `main`, merge `main` in and re-gate.

## 2. Push

`git push -u origin <head>`. On a network failure retry four times with 2, 4, 8 and 16 s backoff.

## 3. Open or reuse the PR

Reuse the PR from §0. Only when §0 found none and the branch carries the package's commits, look up
an open PR for this exact head targeting `main` before creating one; verify repository, head and
base before reusing it, and preserve human edits and review evidence. This section is also the
creation contract `/wp-implement` follows; it starts no review or monitoring.

Base `main`. Title: `feat: WP<n> — <what it delivers>` (`fix:` where the package fixes findings).

Body: it opens with `## In brief` (the template in `wp-plan`; at most 250 words, no backticks or
identifiers), then `.github/pull_request_template.md` filled in: its sections and its Verification
checklist, ticking only what was run. It carries numbers, not adjectives: rates with their meshes,
route-agreement figures, timings, and the stabilisation mode each was measured under.
"Specification changes" is never omitted; "None." is an answer. Link derivations and tables rather than copying them. End with the attribution footer this session
specifies. When the review changes anything the author would decide, update the In brief.

## 4. Review pass

Subscribe to the PR's activity (`subscribe_pr_activity`) so CI results and review comments wake
this session. Read `.claude/rules/physics-numerics.md` and `.claude/rules/python.md` now: the review
and your adjudication of its fixes need them, and a path-scoped rule does not load while you read
only the diff.

Run the review from this session, invoking the skill directly and never wrapped in an `Agent`:

```
Skill(skill="code-review", args="xhigh --fix <pr-number>")
```

Wrapped, it returned no findings; called directly it forks its own review agent.

**The pass must produce evidence that it completed, not that it edited files.** Wait for the
review skill's final report, which must establish the reviewed revision, completed status and the
findings (an explicitly empty list is valid) with any it could not assess or fix, and correlate it
with the SHAs recorded in §0. Zero findings needs no retry. Missing evidence permits one retry after
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
3. If fixes changed the tree, start `.claude/hooks/gate.sh run` again in the background and push
   when it passes.
4. Commit accepted changes as `fix: close the review gaps in <what>`, identifiers in the body, and
   push to the PR branch. A clean review needs no empty commit.

Then record the pass under **Verification**: what was invoked, how many findings came back and
survived step 1, the reviewed base and head SHAs, and any fix commits, distinguishing the
independently reviewed revision from the fixes adjudicated here. Put a finding that is
architectural or would widen the package to the user; scope is the author's.

## 5. Drive to green

Follow `.claude/skills/steward/SKILL.md`, which also applies when a PR event wakes the session
later: its *Bounded wakes* set the polling, fallback check-ins and what counts as a new failure.
Never poll with `sleep`, and report a missing subscription or scheduler as an automation limit.

## 6. Report once

When CI is green and the PR is mergeable, tell the user in one message: the PR link, the checks
that passed, what the review changed, anything left for them to decide, and the tag for the last
commit on `main` after the merge (`CONTRIBUTING.md`). The merge and the tag are theirs. Cancel any
outstanding fallback check-in, then stop. A later event with a new head, failure, conflict or
actionable review restarts attention under `steward`.
