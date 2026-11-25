# The workflow core

Each level of `/np-plan`, `/np-implement` and `/np-ship` reads this file, then its own (§8.4.4).

## Reading order

Read the plan of the level, then what the level's file lists. `/np-plan` reads
`docs/plans/current.md` first; `/np-implement` and `/np-ship` open it when they update it.

## The branch

On `main`, switch to this session's development branch. With none, stop and ask before you write.

## The package's PR and branch

`/np-implement` and `/np-ship` work on the head of the package's PR, never inferred from
`git branch --show-current`. `WP<n>` reads `WP54` in Phase 4 and `WP5.01` from Phase 5 (§8.4.4).

1. Find the PR among the open PRs against `main`. With `wp <n>`, a match is a title that has `WP<n>`
   and an em dash after it; with none, a title that names a package.
   - One match: take it. Several: ask.
   - None, and the plan is on `main`: `/np-implement` works on the session's branch, on the package
     `current.md` names next if `wp <n>` is absent.
   - None otherwise: ask for the PR or branch.
2. Run `git fetch origin <head>`. If a local `<head>` has commits that `origin/<head>` lacks, check it
   out, keep them, and gate and push them; otherwise run `git checkout -B <head> origin/<head>`.
   Never reset a branch that holds unpushed commits. Read the plan from this tree.
3. The command authorises pushes to that head, whatever a session instruction says about its own
   branch. If the harness refuses the push, stop and say so.

## Two lanes

§8.4.4 rules the two lanes. While two package PRs are open:

- `/np-implement` and `/np-ship` take `wp <n>`. Without it, ask which package.
- Edit only your lane's position line of `current.md`.
- After a rebase on `main`, renumber each new item of every register §8.4.4 lists from one above the
  highest on `main`, with every reference, until `uv run .claude/scripts/duplicates.py` passes.

## Normativity

`SPECIFICATION.md` is normative. The plan points into it and never restates it; where they disagree,
the plan is wrong. Behaviour the specification does not permit is a **spec amendment**: decide it now
and write it in the same commit, with the identifier, the NOTE, and an amended tolerance with its
derivation. Never diverge quietly, and never slacken a tolerance to fit a number (the steward's
*Tier 2 failures*). State each rule in the present tense; history goes in the log, `CHANGELOG.md`,
the plans and §8.2.

## Models and executors

Fable 5.2 at high effort plans, or Opus 5.5 at `xhigh` where the author picks it at the plan's
start; Opus 5.5 at high builds and reviews; Sonnet 5.5 at medium ships and runs `/np-carry`'s main
session (`CLAUDE.md`, *Models*; §8.4.5; §8.2.56 BF1, BF9). The author picks a session's model, so each
pause's prompt names the model of the next step. A survey goes to Sonnet, or to Haiku where *Models* allows; read what it
returns before you use it. Physics and numerics decisions stay in this session.

## Records

| Record | Gets |
|---|---|
| `SPECIFICATION.md` | Normative changes only: amendments, NOTEs, argued tolerances |
| `specification/history/` | A ruling round's record (`np-plan/rulings.md`) |
| `knowledge/` | Durable findings (`CLAUDE.md`, *Durable learnings*) |
| The WP's plan | The current Execution brief; short `> **Outcome — <what changed>.**` annotations that link the evidence; the numbers the plan asks for |
| `docs/project/review-findings.md` | A `REV-nn` row for each item left open (`CLAUDE.md`, *Open items*) |

## Gate and push

**A main session lands; a helper commits** (§8.2.56 BF11). `/np-carry`'s main session, or the
session that runs `/np-plan`, `/np-implement` or `/np-ship` itself, runs `just land` and waits on it.
A helper of `/np-carry`, the reviewer and a worker commit under the commit hook and land nothing: a
helper hands back with `land: yes` (`helper.md`). Steps 1 and 7 are the committer's.

**`just land` runs steps 1 to 6** and stops at the first failure (§8.2.56; `.claude/scripts/land.sh`).
Start it with Bash `run_in_background`, `uv run just land <log>`, then wait in the same turn, in the
foreground, `until grep -q '^exit ' <log>; do sleep 10; done`, waiting again if the 10-minute limit
ends the wait. Its last lines are `land: pushed <sha>` or `land: failed at <step>`, and `exit <status>`.
Fix a failure and run it again, or under `/np-carry` give it to a fresh `np-builder`; end the turn
only on a push. The steps it runs, which a session runs by hand where `land` cannot:

1. Before a commit that adds or changes a decision (a ruling, a plan's `Dn` row, a `REV`, `MOD`,
   `OPN` or `WB` row), run `uv run .claude/scripts/decisions.py`; before one that adds a plan or a
   review, `uv run .claude/scripts/index_records.py`. Commit what they write: the gate refuses a
   decisions page that differs from the records.
2. `git status` is clean.
3. If the change touches a documentation source, run `uv run just docs` first, and commit the
   navigation it rewrites in `mkdocs.yml`. The sources are `SPECIFICATION.md`, `specification/`,
   `knowledge/`, `CHANGELOG.md`, `examples/*/README.md`, `data/corrections/`, `docs/` outside `plans/`
   and `code_reviews/`, `mkdocs.yml`, and docstrings in `src/`.
4. Rebase on an existing `origin/<head>`, unless step 7 rewrote the branch on `main`.
5. Run the push gate and push only a tree it passed (§8.4.2; §7.6). A pass of the commit hook never
   stands in for it.
   1. Start it with Bash `run_in_background`:
      `.claude/hooks/gate.sh run > <log> 2>&1; echo "exit $?" >> <log>`, or `uv run just gate <log>`.
   2. Wait in the same turn, in the foreground: `until grep -q '^exit ' <log>; do sleep 10; done`.
      If the 10-minute limit ends the wait, wait again.
   3. Push when the log ends in `exit 0`, and end the turn only then: a turn that ends on an
      unpushed commit trips the environment's stop hook.
6. Run `git push -u origin <branch>`. On a network failure, retry after 2, 4, 8 and 16 s.
7. `main` keeps a linear history. Bring a branch up to it with `git rebase origin/main`, never a
   merge. Where the branch carries commits that `main` took in another form, as a plan's PR merged
   before its implementation, rebuild it on `origin/main` from its own new commits
   (`git cherry-pick`). Push a rewritten branch with
   `git push --force-with-lease=<branch>:<the sha last pushed>`, on the package's own branch only, or
   land it with `uv run just land <log> --lease <the sha last pushed>`, the log first. A tick names its commit's sha, so the next commit corrects the ticks a rewrite moved.

## Finishing

`finish.md` beside this file holds *The author's page*, *The PR contract* and *Report and stop*. Read
it before you open or update a pull request or write a level's report.
