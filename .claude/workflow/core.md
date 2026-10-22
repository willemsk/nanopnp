# The workflow core

Every level of `/np-plan`, `/np-implement` and `/np-ship` reads this file, then the file of its
level, which does not repeat it (§8.4.4; §8.2.16 R5, R12). Plans written before WP53 name the
commands `/phase-plan`, `/wp-plan`, `/wp-implement` and `/wp-ship`.

## Reading order

`docs/plans/current.md` first, then the plan the level works on; then what the level's file lists.
`uv run .claude/scripts/clause.py <ID>` prints a clause with its NOTEs and rulings.
`uv sync --all-extras --frozen` if `.venv` is not current.

## The branch

On `main`, switch to the development branch this session was given; if none was given, stop and
ask before writing anything.

## The package's PR and branch

`/np-implement` and `/np-ship` work on the package's PR head, not on the session's own branch,
which is forked from `main`. Never infer the head from `git branch --show-current`.

1. List open PRs against `main` and take the one whose title contains `WP<n>` followed by an em
   dash; with no `wp <n>`, the one open PR whose title names a package. Several: ask for the
   number. None: `/np-implement` works on the session's branch if the plan is on `main`; otherwise
   ask for the PR number or the branch.
2. `git fetch origin <head>`, then `git checkout -B <head> origin/<head>`. Read `current.md` and the
   plan from this tree: until the merge, they exist only there.
3. Invoking the command authorises pushing to that head; a session instruction to push only to its
   designated branch does not override it. If the harness still refuses, stop and say so.

## Normativity

`SPECIFICATION.md` is normative. The plan points into it and never restates it; where they disagree
the plan is wrong. Behaviour the plan needs and the specification does not permit is a **spec
amendment, decided now and written in the same commit**, never a quiet divergence.

A change to what the finished software does changes `SPECIFICATION.md` **in the same commit**: the
identifier, the NOTE, the amended tolerance, with the derivation. A tolerance is never slackened to
fit a number (the steward's *Tier 2 failures* section says why).

State every rule in the present tense; history lives in the log, `CHANGELOG.md`, plans and §8.2.

## Models and executors

Models (`CLAUDE.md`): Haiku for an easy mechanical item, Sonnet by default, Opus only after Sonnet
has failed on the item. Delegate a survey to Haiku or Sonnet (`CLAUDE.md`, *Models*) and read the
lines it returns before relying on them; keep every physics and numerics decision yourself.

## Records

| Record | Gets |
|---|---|
| `SPECIFICATION.md` | Amendments, NOTEs, argued tolerances: normative changes only |
| `specification/history/` | A ruling round's table, with its lines in `history/index.md` (`np-plan/rulings.md`) |
| `knowledge/<file>.md` | Durable findings as concepts, each claim marked `[tested: <test>]` or `[verified]` with its source, and a line in `knowledge/log.md` (see `knowledge/index.md`) |
| `docs/plans/wp<n>-*.md` | The current Execution brief and concise `> **Outcome — <what changed>.**` annotations linking the evidence; measured numbers the plan requested |
| `docs/project/review-findings.md` | A `REV-nn` row, with its section in `review-items.md`, for every item left open: a deferral, a known limitation, a question for the author (§8.2.8 H12). A row the package resolves is set `fixed` |

## The In brief

A phase plan, a work-package plan and a pull request open with it:

```markdown
## In brief

At most 250 words, no backticks or identifiers; for a reader who does not code.

**What changes.** What the reader will notice, and why it matters.
**Cost.** Time, money or speed, in plain units.
**What could go wrong.** Each risk, and how it would be noticed.
**Your call.** Each decision the author owns, as a question, with *Recommendation:* and one reason.
```

## Gate and push

`git status` is clean. Do not push a tree you have not gated: run `.claude/hooks/gate.sh run` as
`CLAUDE.md`'s *Commands* say, waiting for it in the same turn, and push when it passes. The push
guard refuses any other tree. The push is `git push -u origin <branch>`. On a network failure retry four times with 2, 4, 8
and 16 s backoff. A Markdown-only change outside `packaging/`, `src/`, `data/` and `examples/` runs
ruff alone (`.github/scripts/prose-only.sh`); CI's documentation build still runs. A change to
the documentation's sources (`SPECIFICATION.md`, `specification/`, `knowledge/`, `docs/` outside
`plans/` and `code_reviews/`, a docstring in `src/`) also runs the strict documentation build from
`CLAUDE.md`'s *Commands* before the push.

## The PR contract

Open or reuse the branch's PR against `main` without asking again. Look up an open PR for this
exact head targeting `main` before creating one; verify repository, head and base before reusing it,
and preserve human edits and review evidence. If creation is blocked, report the blocker and the
pushed branch.

Base `main`. A package's title: `feat: WP<n> — <what it delivers>` (`fix:` where the package fixes
findings); a plan level's PR takes its commit's subject.

Body: it opens with `## In brief` (the template above), then `.github/pull_request_template.md` filled in: its sections and its Verification
checklist, ticking only what was run. It carries numbers, not adjectives: rates with their meshes,
route-agreement figures, timings, and the stabilisation mode each was measured under.
"Specification changes" is never omitted; "None." is an answer. Link derivations and tables rather
than copying them. End with the attribution footer this session specifies. On a reused PR, bring the
body to the tree's current state, keeping human edits. When the review changes anything the author
would decide, update the In brief.

Once the PR exists, if `docs/plans/wp<n>-*.md` lacks it, write `PR: [#<n>](<url>), branch <head>`
under its title, commit it (`docs: record WP<n>'s PR`), and gate and push again: the commit is a
new tree, and the push guard names the tree.

## Report and stop

Each level ends with the report its file names, then stops. The next step is a separate invocation;
implementing and shipping are separate sessions, so the review starts fresh.
