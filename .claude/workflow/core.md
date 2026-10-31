# The workflow core

Each level of `/np-plan`, `/np-implement` and `/np-ship` reads this file, then its own (§8.4.4;
§8.2.16 R5, R12). Plans before WP53 name them `/phase-plan`, `/wp-plan`, `/wp-implement`, `/wp-ship`.

## Reading order

Read `docs/plans/current.md`, the plan of the level, then what the level's file lists.
`uv run .claude/scripts/clause.py <ID>` prints a clause with its NOTEs and rulings. A stale `.venv`
takes `uv sync --all-extras --frozen`. On a host other than Claude Code, read `hosts.md` beside this
file and use its substitutes.

## The branch

On `main`, switch to this session's development branch. With no such branch, stop and ask before
you write.

## The package's PR and branch

`/np-implement` and `/np-ship` work on the head of the package's PR, never on the session's own
branch: do not infer the head from `git branch --show-current`. A package's n is `54` in Phase 4
and `5.01` from Phase 5 (§8.4.4), so `WP<n>` reads `WP54` or `WP5.01`.

1. Take the open PR against `main` whose title has `WP<n>` and an em dash after it; with no
   `wp <n>`, the one whose title names a package. If several match, ask. If none matches and the
   plan is on `main`, `/np-implement` works on the session's branch; otherwise ask for the PR or
   branch.
2. Run `git fetch origin <head>`. If a local `<head>` has commits that `origin/<head>` lacks, check it
   out, keep them, and gate and push them. Otherwise run `git checkout -B <head> origin/<head>`.
   Never reset a branch that holds unpushed commits. Read `current.md` and the plan from this tree.
3. The command authorises pushes to that head, whatever a session instruction says about its own
   branch. If the harness refuses the push, stop and say so.

## Two lanes

At most two lanes run (§8.4.4): the current phase, one package at a time, and the next phase's
design study, which changes no `src/`, `tests/`, case schema or public API before the current
phase's release. While two package PRs are open:

- `/np-implement` and `/np-ship` take `wp <n>`; without it, ask which package.
- `current.md` holds one position line per lane. Edit only your lane's line.
- A package merged before its previous phase's release takes no alpha tag; its `CHANGELOG.md`
  entry goes under `## [Unreleased]` (§8.4.1).
- A clause the study restates goes beside it, tagged for the study's release.
- After merging `main`, renumber each new item of every register §8.4.4 lists, from one above the
  highest on `main`, with every reference, until `uv run .claude/scripts/duplicates.py` passes.

## Normativity

`SPECIFICATION.md` is normative; the plan points into it and never restates it, and where they
disagree the plan is wrong. Behaviour the specification does not permit is a **spec amendment,
decided now and written in the same commit**. Never diverge quietly.

A change to what the finished software does changes `SPECIFICATION.md` **in the same commit**: the
identifier, the NOTE, the amended tolerance and its derivation. Never slacken a tolerance to fit a
number (the steward's *Tier 2 failures*). State each rule in the present tense; history goes in the
log, `CHANGELOG.md`, the plans and §8.2.

## Models and executors

Haiku for an easy mechanical item, Sonnet by default, Opus only after Sonnet fails on it
(`CLAUDE.md`, *Models*). A survey goes to Haiku or Sonnet; read what it returns before using it.
Physics and numerics decisions stay in this session.

## Records

| Record | Gets |
|---|---|
| `SPECIFICATION.md` | Amendments, NOTEs, argued tolerances: normative changes only |
| `specification/history/` | The table of a ruling round, with its lines in `history/index.md` (`np-plan/rulings.md`) |
| `knowledge/<file>.md` | Durable findings (`CLAUDE.md`, *Durable learnings*) |
| `docs/plans/wp<n>-*.md` | The current Execution brief; short `> **Outcome — <what changed>.**` annotations linking the evidence; the numbers the plan asks for |
| `docs/project/review-findings.md` | A `REV-nn` row for each item left open: a deferral, a known limitation, a question for the author (§8.2.8 H12) |

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
2. If the change touches a documentation source (`SPECIFICATION.md`, `specification/`,
   `knowledge/`, `CHANGELOG.md`, `examples/*/README.md`, `data/corrections/`, `docs/` outside
   `plans/` and `code_reviews/`, `mkdocs.yml`, docstrings in `src/`), run the strict documentation
   build of `CLAUDE.md`'s *Commands* first, and commit the navigation it rewrites in `mkdocs.yml`.
3. Run `.claude/hooks/gate.sh run` as `CLAUDE.md`'s *Commands* say, and wait for it in the same
   turn. Never push a tree the gate has not passed: the push guard refuses it.
4. `git push -u origin <branch>`; on a network failure, retry after 2, 4, 8 and 16 s.

## The PR contract

Open or reuse the branch's PR against `main` without asking. Reuse one only after verifying its
repository, exact head and base `main`. Keep human edits and review evidence. If
you cannot create the PR, report the blocker and the pushed branch.

Titles: `feat: WP<n> — <what it delivers>`, or `fix:` for a package fixing findings; a plan level's
PR takes its commit's subject.

The body starts with `## In brief`, then fills in `.github/pull_request_template.md`, its
Verification checklist ticked only for what ran. Give numbers, not adjectives (rates with their
meshes, route agreement, timings), each with its stabilisation mode. Never omit "Specification
changes"; "None." is an answer. Link derivations and tables; do not copy them. End with this
session's attribution footer. On a reused PR, bring the body to the tree's current state. If the
review changes an author's decision, update the In brief.

## Report and stop

Each level ends with the report its file names, then stops. Implementing and shipping are separate
sessions, so the review starts fresh.
