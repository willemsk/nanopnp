---
name: wp-ship
description: Ship a finished nanopnp work package — gate, push, reuse its PR (or open one if missing), run /code-review xhigh --fix, then drive CI to green. Use when the user says the work package is finished, asks to open the PR for it, to review and ship it, or invokes /wp-ship.
---

# Ship a work package

Steps 3 and 4 of the implementation workflow, run as one unbroken sequence. Normally `/wp-implement`
has already opened the PR; reuse it. If missing, this invocation authorises opening it without asking
again. The review pass, fixes and CI watch happen without a further prompt.

## 1. Preflight

Read the requested WP's Execution brief and verification evidence, using `docs/plans/current.md`
only to locate it. For legacy plans, start with Decisions, Work items, Verification and correcting
Outcomes. Read normative sections and relevant derivations independently when assessing a claim;
do not reload the entire phase history to write the PR. A brief is navigation, not a review oracle.

Do not push a tree you have not gated.

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src/ && uv run pytest
```

Also confirm: `git status` clean; every `VER-`/`VAL-` the plan claimed has a test named for it;
`SPECIFICATION.md`, `.knowledge/` and the plan's Outcome annotations are committed; `uv.lock` is
current if `pyproject.toml` moved (CI runs `UV_FROZEN`, so a stale lock fails every job).

If the branch is `main`, stop and ask. If the branch is behind `main`, merge `main` in and re-gate.

## 2. Push

`git push -u origin <branch>`. On a network failure retry four times with 2 s, 4 s, 8 s, 16 s backoff.

## 3. Open or reuse the PR

Look up an open PR for this repository and exact head branch targeting `main` before creating one.
Verify the repository, head and base match before reusing it; do not create a duplicate on a resumed
invocation. Preserve existing human edits and review evidence when updating its implementation
summary. This section is also the PR creation contract used by `/wp-implement`; it does not start
review or monitoring.

Base `main`. Title: the conventional-commit summary of the package —
`feat: WP<n> — <what it delivers>`.

Body, in this order. It is the reviewer's brief and the record of the package, so it carries numbers,
not adjectives:

- **What it delivers** — one paragraph, plus the new modules by path.
- **Identifiers discharged** — the `VER-`/`VAL-`/`FR-`/`NUM-`/`PHY-` list, each against the test or
  the module that discharges it.
- **Specification changes** — every amendment and NOTE, with why it was the specification that was
  wrong rather than the number that was accommodated. Empty is a fine answer; silence is not.
- **Measured** — the convergence rates with their meshes, route-agreement figures, timings, minimum
  damping, and the stabilisation mode they were measured under.
- **Deliberately not done** — deferrals, flags left default-off, and what owns them next.
- **Verification** — which tiers were run and the result; anything only run locally because CI
  does not carry it (Tier 3, `slow`).

Keep each section concise. Link full derivations, measurement tables and requirement matrices at
the reviewed revision instead of duplicating them; retain the key results and explicit deferrals.

End with the attribution footer this session's instructions specify for pull request descriptions.
Mirror `.github/pull_request_template.md` instead if one has appeared since.

## 4. Review pass

Subscribe to the PR's activity (`subscribe_pr_activity`) from this shipping session so CI results
and review comments wake the session responsible for review and stewardship.

Run the review against the PR, from this session:

```
Skill(skill="code-review", args="xhigh --fix <pr-number>")
```

Invoke the skill directly. Do **not** wrap it in an `Agent` call, as this step did after
`48f5f63`: the wrapped form returned no findings and no fixes, run after run, and WP9
shipped that way with a 1e9 error in `RadialGrid.integral(radial=True)` still in it. Verified: the
direct call forks its own review agent and returns the finished findings into the calling turn.
Inferred, from the `Skill` tool's contract that such a pass can return asynchronously: a subagent
runs one prompt and is then torn down, leaving no turn for that result to return into. The mechanism
is a hypothesis; the empty results are not.

The cold-context property this step exists for comes from the skill running its own forked pass, and
from `/wp-implement` never chaining into `/wp-ship` — not from an extra agent in between, which only
adds a relay that can drop the report.

**The pass must produce evidence that it completed, not evidence that it edited files.** Record the
PR base and head SHAs before invoking it. Read the installed review skill's completion contract and
wait for its actual final report; an acknowledgement or an unfinished asynchronous dispatch is not
completion. The returned report must establish the reviewed revision/scope, completed status and
findings (an explicitly empty list is valid), including any items it could not assess or fix.
Correlate that evidence with the recorded SHAs; do not manufacture a completion record from the
caller's expectations or from `git status`.

A completed review with zero findings needs no retry or edits. Findings without automatic fixes
are also valid and go through the steps below. Missing/incomplete completion evidence permits one
retry after the original dispatch has finished or been confirmed failed, never a concurrent duplicate.
If completion still cannot be established, stop before §5 and report the invocation and missing
evidence. An unavailable review tool is a blocker, not permission to mark the package reviewed.
If the PR base/head changes during review, reconcile the changed diff and review any uncovered
changes before accepting the report; evidence for an old revision does not certify a new one.

`--fix` writes to the working tree; it does not commit. So, back in this session:

1. Read every applied fix as a diff. A review finding is a hypothesis, not a verdict — confirm it
   against the specification and the plan before keeping it. Revert any fix that is wrong, and say
   in the PR thread why it was wrong; a reviewer proposing a change that would violate a spec clause
   is the case this step exists to catch. That confirmation is what keeps a proposed fix from
   becoming a plausible wrong one — do not skip it.
2. Findings the pass raised but could not fix: fix them yourself here, or record them in the PR body
   under **Deliberately not done** with the reason. Do not leave a confirmed finding unmentioned.
3. If fixes changed the tree, re-run the full gate.
4. Commit accepted changes — `fix: close the review gaps in <what>`, identifiers in the body — and
  push to the PR branch. No empty commit or cosmetic edit is needed for a clean review. The commits
  belong on the branch, not in a comment; the commit hook remains mandatory.

Then record the pass in the PR body under **Verification**: what was invoked, how many findings came
back, how many survived step 1, the reviewed base/head SHAs, and any resulting fix commits. Distinguish
the independently reviewed revision from the fixes adjudicated and gated in this session.

Where a finding is architectural or would widen the package, put it to the user rather than acting:
scope decisions are the author's.

## 5. Drive to green

Follow `.claude/skills/steward/SKILL.md` — the repo's conventions for CI failures, which also apply
automatically when a PR event wakes the session later.

Use the bounded wake policy in `steward` below its environment section. New failures and conflicts
require action regardless of review state; unchanged, already-diagnosed human blockers do not require
another investigation or duplicate comment. Keep at most one fallback check-in, stop it at green and
mergeable or explicit handoff, and never poll with `sleep`. Missing subscription/scheduler tools must
be reported as an automation limit; do not claim a watch was established when it was not.

## 6. Report once

When CI is green and the PR is mergeable, tell the user in one message: the PR link, the checks that
passed, what the review pass changed, and anything left for them to decide. Cancel any outstanding
fallback check-in (or make an already queued wake a no-op), then stop; the merge is theirs. A later
event with a new head, failure, conflict or actionable review restarts attention under `steward`.
