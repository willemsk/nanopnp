---
name: np-chore
description: Make one change outside the work-package flow — a branch from main, the change, a review where it is not Markdown alone, the land, and a pull request the author merges. Use only on /np-chore.
argument-hint: "<what to change>"
disable-model-invocation: true
---

# Chore: `$ARGUMENTS`

A chore is one change with no plan, no package number and no lane (§8.2.57 BG1 to BG6). The author
merges it; nothing tags it. The author starts the session for it on Sonnet 5.5 at medium effort, or on
Opus 5.5 at high where the change touches `src/` or `tests/` (§8.4.5; BG6).

1. With no argument print `Usage: /np-chore <what to change>` and stop. Read the core,
   `${CLAUDE_SKILL_DIR}/../../workflow/core.md`, *Gate and push*.
2. `git fetch origin main`, then **refuse**, and say why, if any holds: the working tree is dirty;
   the session's branch holds commits past `origin/main`; `git worktree list` shows another
   worktree whose branch holds commits past `origin/main`; the session was started by `/np-carry`,
   or is a helper, the reviewer or a worker. These checks see this checkout alone: that no carry
   runs elsewhere is the author's start of the session. A helper, the reviewer or a worker names
   the chore in its hand-back or its reply, for the author to start in a session of its own, and
   makes it nowhere.
3. Use the branch the harness binds to the session, if any, reset to `origin/main`, where
   `origin/<that branch>` is absent or holds no commit past `origin/main`: `just land` rebases on
   `origin/<branch>` and would bring that branch's commits into the chore unreviewed. Otherwise
   `git switch -c chore/<slug> origin/main`, with a slug no branch on `origin` has.
4. Make the change. A change to specified behaviour edits its clause in the same commit
   (`CLAUDE.md`); `src/` changes keep the test scope (§8.2.13 N1) and, for a public-surface break,
   `CHANGELOG.md`. A choice for the author follows `.claude/workflow/author.md`. A new numbered
   item (a ruling, a `REV` row, a code review) takes the next number on `origin/main`; run
   `uv run .claude/scripts/decisions.py` and `index_records.py` where *Gate and push* step 1
   says, and `uv run .claude/scripts/duplicates.py` until it passes.
5. Commit with a conventional subject, the identifiers in the body.
6. **Review**, unless every changed path is `*.md`. Always review a change to
   `.claude/settings*.json`, `.claude/hooks/`, `.githooks/`, `.claude/agents/`, `.claude/skills/`,
   `.claude/workflow/` or `.github/workflows/`. Where a changed path is under `src/`, `tests/`,
   `.githooks/` or `.claude/scripts/`, is a `.py`, `.sh` or `.cjs` file, or is `justfile`, first run
   the hunt on the committed head, directly from this session, never inside an `Agent` (§8.2.61 BK1
   to BK5):

   ```
   Skill(skill="code-review", args="high --max-findings all <branch> -- Report only: edit, commit and write nothing. Static review: run no tests, benchmark, sweep, gate.sh or pytest --nightly.")
   ```

   Start `np-reviewer` in the foreground, its model and effort its own,
   with the base `origin/main`, the head sha, and the chore's statement in a paragraph in place of
   a plan: what it changes and why, and every permission line it adds. Add: "judge a permission or
   workflow change for what a session could do with it that the statement does not say". End it
   with `The hunt's findings: <the findings, or none>` where the hunt ran. A finding
   it leaves to the author, that outlives the session, is a `REV` row in
   `docs/project/review-findings.md`, with a section in `review-items.md`, owned by the current phase
   (§8.4.6); commit it before the land. A small finding it leaves is fixed in this session, its diff
   reviewed as step 7 says, and gets no row (§8.2.58 BH1).
7. **Land**: `uv run just land <log>` in the background, then wait in the foreground, as *Gate and
   push* says. Push only the session's own branch; if the harness refuses it, stop and say so.
   Just before each land run `git fetch origin main`: CI's check ran on a `main` that may since have
   moved. If `main` moved, rebase on it (core, step 7), then run `duplicates.py` on the rebased tree,
   which it alone reads, and land with `--lease <the sha last pushed>` where the branch was pushed.
   Of a failed land or a red CI, this session fixes only format and lint, with `uv run ruff format .`
   and `uv run ruff check --fix .`; any other failure goes to a fresh `np-builder` in the foreground,
   with the failing log (§8.2.57 BG3; §8.2.58 BH1). A commit made after the review, for a failed
   land, a red CI or the author's word on the PR, is reviewed on its own diff by `np-reviewer` at
   `effort: "medium"` unless it is Markdown alone outside the paths step 6 always reviews. Then land
   again.
8. Open a PR titled `chore: <what>` from `.github/pull_request_template.md`: keep *What this
   delivers* (with each permission line the change adds), *Specification changes* (`None.` where
   so) and *Verification*; drop the other sections. Give the review's outcome and the commit
   hash. End it with the attribution lines the session was given.
9. Report the PR and stop. A chore is not a lane: an open package rebases on `main` at its ship
   (`np-ship/wp.md` §1; core, step 7), as `just land` never rebases on `main`, and corrects its
   ticks. Ask the author whether to watch the PR.
