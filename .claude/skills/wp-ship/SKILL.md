---
name: wp-ship
description: Ship a finished nanopnp work package — gate, push, open the PR, send /code-review xhigh --fix to a fresh subagent on the PR branch, then drive CI to green. Use when the user says the work package is finished, asks to open the PR for it, to review and ship it, or invokes /wp-ship.
---

# Ship a work package

Steps 3 and 4 of the implementation workflow, run as one unbroken sequence. Invoking this skill *is*
the user asking for a pull request; open it without asking again. Everything after that — the review
pass, the fixes, the CI watch — happens without a further prompt, because the point of the skill is
that the user does not have to babysit it.

## 1. Preflight

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

## 3. Open the PR

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

End with the attribution footer this session's instructions specify for pull request descriptions.
Mirror `.github/pull_request_template.md` instead if one has appeared since.

Then subscribe to the PR's activity (`subscribe_pr_activity`) so CI results and review comments
wake this session.

## 4. Review pass, in a fresh subagent

This session carries the reasoning behind every decision the implementation made — which is exactly
why it cannot be the one to check that reasoning. Hand the review to a subagent that starts cold, on
a different model, so it evaluates the diff rather than its own prior conclusions:

```
Agent(subagent_type="general-purpose", model="sonnet", run_in_background=false,
      description="Fresh-context code review of WP<n>",
      prompt="Run the code-review skill (via the Skill tool) with args 'xhigh --fix <pr-number>' "
             "against pull request <pr-number> in this repository. Apply its fixes to the working "
             "tree but do not commit or push — leave them staged as an uncommitted diff. Report back "
             "every finding, fixed and unfixed, with file, line and a one-sentence rationale.")
```

Run it in the foreground (`run_in_background: false`) — the next step depends on its result and
there is nothing else productive to do meanwhile. No isolation/worktree: it edits this session's
working tree directly, so its diff lands where step 4.1 below reads it.

`--fix` writes to the working tree; it does not commit. So, back in this session:

1. Read every applied fix as a diff. A review finding from a cheaper, colder model is a hypothesis,
   not a verdict — confirm it against the specification and the plan before keeping it. Revert any
   fix that is wrong, and say in the PR thread why it was wrong; a reviewer proposing a change that
   would violate a spec clause is the case this step exists to catch. This confirmation is the
   safety net for running the pass on a cheaper model — do not skip it.
2. Findings the pass raised but could not fix: fix them yourself here, or record them in the PR body
   under **Deliberately not done** with the reason. Do not leave a confirmed finding unmentioned.
3. Re-run the gate.
4. Commit — `fix: close the review gaps in <what>`, identifiers in the body — and push to the PR
   branch. The commits belong on the branch, not in a comment.

Where a finding is architectural or would widen the package, put it to the user rather than acting:
scope decisions are the author's.

## 5. Drive to green

Follow `.claude/skills/steward/SKILL.md` — the repo's conventions for CI failures, which also apply
automatically when a PR event wakes the session later.

The rule that governs the whole step: **a red or conflicted PR is work now, at every wake, whatever
its review state.** Never end a wake on this PR having done nothing about a failure. Either a fix is
pushed, or a comment on the PR says exactly what is failing and why it is not this PR's to fix.

Keep a self check-in scheduled roughly an hour out (`send_later`) until the PR is merged or closed,
re-arming it each time it fires; webhook events do not reliably cover CI success or new pushes. Do
not poll with `sleep`. If nothing changed, re-arm silently — do not message the user to say so.

## 6. Report once

When CI is green and the PR is mergeable, tell the user in one message: the PR link, the checks that
passed, what the review pass changed, and anything left for them to decide. Then stop; the merge is
theirs.
