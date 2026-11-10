# The workflow core

Each level of `/np-plan`, `/np-implement` and `/np-ship` reads this file, then its own (§8.4.4;
§8.2.16 R5, R12). Plans before WP53 name the commands `/phase-plan`, `/wp-plan`, `/wp-implement` and
`/wp-ship`.

## Reading order

1. On a host other than Claude Code, read `hosts.md` beside this file before the rest.
2. Read `docs/plans/current.md`, the plan of the level, then what the level's file lists.
3. `uv run .claude/scripts/clause.py <ID>` prints a clause with its NOTEs and rulings.
4. A stale `.venv` takes `uv sync --all-extras --frozen` (`CLAUDE.md`, *Setup*).

## The branch

On `main`, switch to this session's development branch. With no such branch, stop and ask before you
write.

## The package's PR and branch

`/np-implement` and `/np-ship` work on the head of the package's PR. Never infer the head from
`git branch --show-current`. A package's n is `54` in Phase 4 and `5.01` from Phase 5 (§8.4.4), so
`WP<n>` reads `WP54` or `WP5.01`.

1. Find the PR among the open PRs against `main`:
   1. With `wp <n>`, a match is a title that has `WP<n>` and an em dash after it. With no `wp <n>`,
      it is a title that names a package.
   2. One match: take it.
   3. Several: ask.
   4. None, and the plan is on `main`: `/np-implement` works on the session's branch.
   5. None otherwise: ask for the PR or branch.
2. Run `git fetch origin <head>`.
   - If a local `<head>` has commits that `origin/<head>` lacks, check it out, keep them, and gate and
     push them.
   - Otherwise run `git checkout -B <head> origin/<head>`.
   - Never reset a branch that holds unpushed commits.
   - Read `current.md` and the plan from this tree.
3. The command authorises pushes to that head, whatever a session instruction says about its own
   branch. If the harness refuses the push, stop and say so.

## Two lanes

The rule of the two lanes, the current phase and the next phase's design study, is §8.4.4's; this
section is a session's conduct under it. While two package PRs are open:

- `/np-implement` and `/np-ship` take `wp <n>`. Without it, ask which package.
- `current.md` holds one position line per lane. Edit only your lane's line.
- A package merged before its previous phase's release: its tag and its `CHANGELOG.md` entry follow
  `CONTRIBUTING.md`, *Versions and releases*.
- After you merge `main`, renumber each new item of every register §8.4.4 lists. Start one above the
  highest on `main`, change every reference, and repeat until `uv run .claude/scripts/duplicates.py`
  passes.

## Host coordination

- One host drives a branch at a time (§8.2.25 AA4). It is named `host: claude-code` or
  `host: copilot` in the lane line of `docs/plans/current.md` and in the PR's **Verification**
  checkpoint. If the other host is named and the branch moved within the hour, ask before you write.
- Hosts never share a working tree. The two-lane cap and the renumbering above apply across hosts.
- Before each push, merge `origin/<head>`. Never force-push a branch the other host may hold.

## Normativity

`SPECIFICATION.md` is normative. The plan points into it and never restates it. Where they disagree,
the plan is wrong. Behaviour the specification does not permit is a **spec amendment**: decide it now
and write it in the same commit. Never diverge quietly.

A change to what the finished software does changes `SPECIFICATION.md` **in the same commit**: the
identifier, the NOTE, and the amended tolerance with its derivation. Never slacken a tolerance to fit
a number (the steward's *Tier 2 failures*). State each rule in the present tense. History goes in the
log, `CHANGELOG.md`, the plans and §8.2.

## Models and executors

`CLAUDE.md` sets the models (*Models*). A survey goes to Sonnet, or to Haiku where *Models* allows;
read what it returns before you use it. Physics and numerics decisions stay in this session.

## Records

| Record | Gets |
|---|---|
| `SPECIFICATION.md` | Amendments, NOTEs, argued tolerances: normative changes only |
| `specification/history/` | The table of a ruling round, its line in `history/index.md` and where each ruling holds now in `history/holds-now.yaml` (`np-plan/rulings.md`) |
| `knowledge/<file>.md` | Durable findings (`CLAUDE.md`, *Durable learnings*) |
| `docs/plans/phase-<p>/wp<n>-*.md` | The current Execution brief; short `> **Outcome — <what changed>.**` annotations that link the evidence; the numbers the plan asks for |
| `docs/project/review-findings.md` | A `REV-nn` row, with its section in `review-items.md`, for each item left open: a deferral, a known limitation, a question for the author (§8.2.8 H12) |

## The author's page

*The In brief*, the section a plan and a pull request start with, and *Putting a choice to the author*
are in `author.md` beside this file (§8.2.33 AI7). Read it at a step that writes an In brief or puts
a choice to the author.

## Gate and push

1. Before each commit that adds or changes a decision (a ruling, a plan's `Dn` row, a `REV`, `MOD`,
   `OPN` or `WB` row), run `uv run .claude/scripts/decisions.py`; before each that adds a plan or a
   review, run `uv run .claude/scripts/index_records.py`. Commit what they write with the change.
   The gate refuses a decisions page that differs from the records (§8.4.4).
2. `git status` is clean.
3. If the change touches a documentation source, run the strict documentation build of `CLAUDE.md`'s
   *Commands* first, and commit the navigation it rewrites in `mkdocs.yml`. The sources are:
   `SPECIFICATION.md`, `specification/`, `knowledge/`, `CHANGELOG.md`, `examples/*/README.md`,
   `data/corrections/`, `docs/` outside `plans/` and `code_reviews/`, `mkdocs.yml`, and docstrings in
   `src/`.
4. Run the gate before a push as `CLAUDE.md`'s *Commands* say (on Copilot, `hosts/copilot.md`), and
   push only a tree it passed (§8.4.2).
5. Run `git push -u origin <branch>`. On a network failure, retry after 2, 4, 8 and 16 s.

## The PR contract

Open or reuse the branch's PR against `main` without asking. Reuse one only after you verify its
repository, its exact head and its base `main`. Keep human edits and review evidence. If you cannot
create the PR, report the blocker and the pushed branch.

Titles: `feat: WP<n> — <what it delivers>`, or `fix:` for a package that fixes findings. A plan
level's PR takes its commit's subject.

The body starts with `## In brief` (`author.md`). It then fills in `.github/pull_request_template.md`, and ticks the
Verification checklist only for what ran. Give numbers, not adjectives: rates with their meshes, route
agreement, timings, each with its stabilisation mode. Never omit "Specification changes"; "None." is
an answer. Link derivations and tables; do not copy them. End with this session's attribution footer.
On a reused PR, bring the body to the tree's current state. If the review changes an author's
decision, update the In brief.

## Report and stop

Each level ends with the report its file names, then stops. `/np-implement` pauses after its report
for a compaction; `/np-ship` then runs in that session or a fresh one, and a finding against a decision
the implementing session took goes to the author (§8.2.33 AI4). A level of `/np-plan` pauses after its report for a compaction,
and `/np-plan <level> [n] review` then reviews the plan and summarises it for approval
(`np-plan/review.md`).

Each report, and each pause for a compaction, ends with the line that
`uv run .claude/scripts/usage.py --label <level>` prints: the session's cost since the level's command,
in §8.3's units, with its tokens by model. The PR's **Measured** section gains the line (§8.4.5;
§8.2.37 AM11).
