# The workflow core

Each level of `/np-plan`, `/np-implement` and `/np-ship` reads this file, then its own file, which
does not repeat this one (§8.4.4; §8.2.16 R5, R12). Plans before WP53 name the commands
`/phase-plan`, `/wp-plan`, `/wp-implement` and `/wp-ship`.

## Reading order

Read `docs/plans/current.md`, then the plan of the level, then what the level's file lists.
`uv run .claude/scripts/clause.py <ID>` prints a clause with its NOTEs and rulings. If `.venv` is
not current, run `uv sync --all-extras --frozen`.

## The branch

On `main`, switch to the development branch of this session. If the session has no such branch,
stop and ask before you write.

## The package's PR and branch

`/np-implement` and `/np-ship` work on the head of the package's PR. The session's own branch forks
from `main` and is not that head. Never infer the head from `git branch --show-current`.

1. List the open PRs against `main`. Take the PR whose title contains `WP<n>` and an em dash after
   it. With no `wp <n>`, take the one open PR whose title names a package. If several match, ask
   for the number. If none matches and the plan is on `main`, `/np-implement` works on the session's
   branch; otherwise ask for the PR number or the branch.
2. Run `git fetch origin <head>`, then `git checkout -B <head> origin/<head>`. Read `current.md` and
   the plan from this tree: until the merge, only this tree has them.
3. The command authorises pushes to that head. A session instruction to push only to its own branch
   does not override this. If the harness refuses the push, stop and say so.

## Normativity

`SPECIFICATION.md` is normative. The plan points into it and never restates it. If they disagree,
the plan is wrong. If the plan needs behaviour that the specification does not permit, that is a
**spec amendment, decided now and written in the same commit**. Never diverge quietly.

A change to what the finished software does changes `SPECIFICATION.md` **in the same commit**: the
identifier, the NOTE, the amended tolerance and its derivation. Never slacken a tolerance to fit a
number (the steward's *Tier 2 failures* section says why).

State each rule in the present tense. History goes in the log, `CHANGELOG.md`, the plans and §8.2.

## Models and executors

Use Haiku for an easy mechanical item and Sonnet by default. Use Opus only after Sonnet fails on the
item (`CLAUDE.md`, *Models*). Give a survey to Haiku or Sonnet, and read the lines it returns before
you use them. Keep each physics and numerics decision in this session.

## Records

| Record | Gets |
|---|---|
| `SPECIFICATION.md` | Amendments, NOTEs, argued tolerances: normative changes only |
| `specification/history/` | The table of a ruling round, with its lines in `history/index.md` (`np-plan/rulings.md`) |
| `knowledge/<file>.md` | Durable findings, as `CLAUDE.md`'s *Durable learnings* says |
| `docs/plans/wp<n>-*.md` | The current Execution brief; short `> **Outcome — <what changed>.**` annotations that link the evidence; the measured numbers the plan asks for |
| `docs/project/review-findings.md` | A `REV-nn` row for each item left open, as `CLAUDE.md`'s *Open items* says: a deferral, a known limitation, a question for the author (§8.2.8 H12) |

## The In brief

A phase plan, a work-package plan and a pull request start with this section:

```markdown
## In brief

At most 250 words, no backticks or identifiers; for a reader who does not code.

**What changes.** What the reader will notice, and why it matters.
**Cost.** Time, money or speed, in plain units.
**What could go wrong.** Each risk, and how it would be noticed.
**Your call.** Each decision the author owns, as a question, with *Recommendation:* and one reason.
```

## Gate and push

1. `git status` is clean.
2. Run `.claude/hooks/gate.sh run` as `CLAUDE.md`'s *Commands* say, and wait for it in the same
   turn. Never push a tree that the gate has not passed: the push guard refuses it.
3. If the change touches a source of the documentation, also run the strict documentation build
   of `CLAUDE.md`'s *Commands*. The sources are `SPECIFICATION.md`, `specification/`, `knowledge/`,
   `docs/` outside `plans/` and `code_reviews/`, and the docstrings in `src/`.
4. Push with `git push -u origin <branch>`. On a network failure, retry four times, after 2, 4, 8
   and 16 s.

## The PR contract

Open or reuse the branch's PR against `main`; do not ask again. First look for an open PR with this
exact head and base `main`, and verify its repository, head and base before you reuse it. Keep human edits and
review evidence. If you cannot create the PR, report the blocker and the pushed branch.

The title of a package's PR is `feat: WP<n> — <what it delivers>`, or `fix:` if
the package fixes findings. The PR of a plan level takes the subject of its commit as its title.

The body starts with `## In brief` (the template above). Then it fills in
`.github/pull_request_template.md`: its sections, and its Verification checklist, ticked only for
what ran. Give numbers, not adjectives: rates with their meshes, route agreement, timings, each
with its stabilisation mode. Never omit "Specification changes"; "None." is an
answer. Link derivations and tables; do not copy them. End with the attribution footer of this
session. On a reused PR, bring the body to the current state of the tree, and keep human edits. If
the review changes a decision of the author, update the In brief.

When the PR exists and `docs/plans/wp<n>-*.md` does not have its line, write
`PR: [#<n>](<url>), branch <head>` under the plan's title. Commit it as `docs: record WP<n>'s PR`.
Then gate and push again: the commit is a new tree, and the push guard checks each tree.

## Report and stop

Each level ends with the report that its file names, and then stops. The next step is a separate
invocation. Implementing and shipping are separate sessions, so the review starts fresh.
