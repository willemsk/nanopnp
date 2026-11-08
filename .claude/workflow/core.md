# The workflow core

Each level of `/np-plan`, `/np-implement` and `/np-ship` reads this file, then its own (§8.4.4;
§8.2.16 R5, R12). Plans before WP53 name the commands `/phase-plan`, `/wp-plan`, `/wp-implement` and
`/wp-ship`.

## Reading order

1. Read `docs/plans/current.md`, the plan of the level, then what the level's file lists.
2. `uv run .claude/scripts/clause.py <ID>` prints a clause with its NOTEs and rulings.
3. A stale `.venv` takes `uv sync --all-extras --frozen` (`CLAUDE.md`, *Setup*).
4. On a host other than Claude Code, read `hosts.md` beside this file first.

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

At most two lanes run (§8.4.4): the current phase, one package at a time, and the next phase's design
study. The study changes no `src/`, `tests/`, case schema or public API before the current phase's
release. While two package PRs are open:

- `/np-implement` and `/np-ship` take `wp <n>`. Without it, ask which package.
- `current.md` holds one position line per lane. Edit only your lane's line.
- A package merged before its previous phase's release takes no alpha tag. Its `CHANGELOG.md` entry
  goes under `## [Unreleased]` (§8.4.1).
- A clause the study restates goes beside it, tagged for the study's release.
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

`CLAUDE.md` sets the models (*Models*). A survey goes to Haiku or Sonnet; read what it returns before
you use it. Physics and numerics decisions stay in this session.

## Records

| Record | Gets |
|---|---|
| `SPECIFICATION.md` | Amendments, NOTEs, argued tolerances: normative changes only |
| `specification/history/` | The table of a ruling round, with its lines in `history/index.md` (`np-plan/rulings.md`) |
| `knowledge/<file>.md` | Durable findings (`CLAUDE.md`, *Durable learnings*) |
| `docs/plans/phase-<p>/wp<n>-*.md` | The current Execution brief; short `> **Outcome — <what changed>.**` annotations that link the evidence; the numbers the plan asks for |
| `docs/project/review-findings.md` | A `REV-nn` row for each item left open: a deferral, a known limitation, a question for the author (§8.2.8 H12) |

## The In brief

A phase plan, a work-package plan and a pull request start with this section:

```markdown
## In brief

About 250 words, up to 10% over (275), no backticks or identifiers; for a reader who does not code.

**What changes.** What the reader will notice, and why it matters.
**Cost.** Time, money or speed, in plain units.
**What could go wrong.** Each risk, and how it would be noticed.
**Your call.** Each decision the author owns, as a question, with *Recommendation:* and one reason.
```

## Putting a choice to the author

Every choice the workflow puts to the author carries what a reader who does not code needs to judge
its impact: a ruling round, a work-package decision, a disputed review finding (§8.2.33 AI7). The
question dialog may be all the author sees, so the context lives in it, not in the chat.

- **The question** says, in the reader's words, what is decided, what happens today, and why it is
  open: what the specification, the phase or the design leaves undecided. An identifier only follows
  its words, in brackets.
- **Each option's description**, one or two sentences: what the user will see or do differently.
- **Each option's preview**, short lines in Markdown:
  - **You get:** the change for the user, with a concrete example: a command, a screen, a file;
  - **It costs:** time in days, and what it adds, delays or leaves out;
  - **Undo:** easy (a setting, or one later package), costly (a re-plan or a migration) or one-way
    (a file format users write, deleted data, a published release);
  - **It touches:** the later packages, other users and the clauses it moves, in words;
  - for the recommended option, **Why:** the one reason, and **It would change if:** what would make
    another option better.
  A layout or a screen gets a small text sketch in the preview.
- **At most three questions in a call**, the ones that change others first. Before the first call,
  the chat gets a short brief of the round: what is decided, what is settled already, and what each
  answer feeds.
- **When the author asks for more,** with a question back, a free answer that picks nothing, or
  "explain": give what was asked (an example, a sketch, the cost, what comparable tools do), then ask
  again. Never record a ruling the author did not make. If the context asked for is of a kind this
  list lacks, add it here in the same commit, so the next round gives it unprompted.

## Gate and push

1. `git status` is clean.
2. If the change touches a documentation source, run the strict documentation build of `CLAUDE.md`'s
   *Commands* first, and commit the navigation it rewrites in `mkdocs.yml`. The sources are:
   `SPECIFICATION.md`, `specification/`, `knowledge/`, `CHANGELOG.md`, `examples/*/README.md`,
   `data/corrections/`, `docs/` outside `plans/` and `code_reviews/`, `mkdocs.yml`, and docstrings in
   `src/`.
3. Run `.claude/hooks/gate.sh run` as `CLAUDE.md`'s *Commands* say, and wait for it in the same turn.
   Never push a tree the gate has not passed. The push guard refuses it.
4. Run `git push -u origin <branch>`. On a network failure, retry after 2, 4, 8 and 16 s.

## The PR contract

Open or reuse the branch's PR against `main` without asking. Reuse one only after you verify its
repository, its exact head and its base `main`. Keep human edits and review evidence. If you cannot
create the PR, report the blocker and the pushed branch.

Titles: `feat: WP<n> — <what it delivers>`, or `fix:` for a package that fixes findings. A plan
level's PR takes its commit's subject.

The body starts with `## In brief`. It then fills in `.github/pull_request_template.md`, and ticks the
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
