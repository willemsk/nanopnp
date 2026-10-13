---
name: phase-plan
description: Plan a nanopnp phase — collect what the previous phase carries, put the phase's design decisions to the author as a ruling round, then write the rulings into SPECIFICATION.md §8.2, the phase plan into docs/plans/ and commit it. Also amends a phase in flight (re-plan after an opening study, add or drop a work package). Use when the user asks to plan the next phase, plan phase 4, break a phase into work packages, re-plan or amend a phase, or invokes /phase-plan.
---

# Plan a phase

The level above `/wp-plan`: turn a row of `SPECIFICATION.md` §8.1 into the author's rulings and a
sequence of work packages, each small enough for one PR. The deliverables are a §8.2.x rulings
section and `docs/plans/phase-<n>-<slug>.md`, committed together. A package's own decisions are
`/wp-plan <n>`'s; this skill decides only what spans packages.

`SPECIFICATION.md` is normative. The plan points into it and never restates it. A ruling that
changes a clause amends that clause in the same commit, and the §8.2.x row names the clause.

`/phase-plan <n>` plans Phase n in **two turns**: a ruling round, then the write-up.
`/phase-plan amend [<n>]` amends the phase in flight (*Amending a phase*).

## Turn 1 — the ruling round

Nothing is committed in this turn.

### 1. Preconditions

1. On `main`, switch to the development branch this session was given; if none, stop and ask.
2. If a `docs/plans/phase-<n>-*.md` exists, this is an amendment: go to *Amending a phase*.
3. Phase n−1 is closed: its close package has merged, its end-of-phase report is written and its
   `vX.Y.0` tag is published or is the author's next step. If not, say so **first** and put the
   close first in the round: finish it, or rule that Phase n overlaps it and what Phase n may not
   do before it lands.
4. Versions agree before a new one is named: §2.7 and its Versioning NOTE, §3's Release column,
   §8.1, `CHANGELOG.md`, `current.md` and the published tags (`git ls-remote --tags origin
   'v0.*'`; a hosted clone is shallow). One minor per phase. A disagreement goes into the round.

### 2. Collect what the phase inherits

Read in this order, keeping a list of every item that needs a decision:

1. `docs/plans/current.md`, then `.knowledge/00-index.md`, then
   `.claude/rules/physics-numerics.md` and `.claude/rules/python.md` (a path-scoped rule does not
   load while you write only Markdown).
2. `SPECIFICATION.md` §8.1: Phase n's row and its GUI and documentation increments; then every
   §8.2.x section, newest first, for rulings that already bind Phase n. A ruling taken is cited,
   never re-asked.
3. The previous phase plan: its `## End-of-phase report` (above all what it **carries**), its open
   `## Open decisions` rows, and every **Live for later packages** line in its delivered summaries
   and WP Outcomes.
4. §10's open `OPN-` items and §9's `RSK-` register: which this phase retires or could close.
5. Any input note under `docs/plans/` that names this phase: its decisions bind, its open
   questions join the round.
6. Appendix A: requirements tagged for this phase's version and not yet discharged.

### 3. Survey the codebase

Delegate a survey (`.claude/model-policy.md`) of what the phase builds on: what exists, what is
refused today naming a later phase, which seams take what the phase needs. From it write the
**"true of the codebase today"** list yourself: five or so facts, each naming its file and function.

### 4. Draft the decisions

A phase decision is one that more than one package depends on or the author must own: order of
evidence, a choice every later package inherits, scope and deferrals, a new dependency, a spec
amendment, versioning and the close. Always cover:

- **the gate, pre-registered.** Each completion criterion names its test, tolerance and where the
  tolerance was argued, a predicted value where one can be made, and the **fallback on a miss**:
  investigate, re-argue the tolerance (a spec amendment, never a quiet slackening), or waive and
  carry;
- **what the author supplies**: archive data, rulings only they can give, observations by a person
  (QR-10), each with the package that needs it and what happens if it does not arrive;
- **who merges and who tags.** The author merges. A session may not be able to push tags, so say
  whether the close tags or prints the commands, and whether it takes the release tag alone, with
  no `-alpha.N` (as §8.2.5 E5 ruled for Phase 3).

Draft each decision as one question with its identifiers, two to four options (consequence for
correctness, scope, gate cost, clause amended) and a recommendation first, with why. Also draft the
**work-package sequence**, the numbered **completion criteria** (each checkable by a named test or
observation) and what the phase **excludes**, with where each goes.

### 5. Put it to the author

Ask through `AskUserQuestion`, at most four questions a call, each carrying the clause at stake,
the cost of each option and what is already ruled. Ask the decisions that change the package
sequence first, then the sequence, then the rest. Record a prose ruling in the author's words.
Without `AskUserQuestion`, put the questions in one numbered message and end the turn. A scope
change the author volunteers is a ruling: record it, then re-check what it moves.

Stop when every decision is ruled or left open with an owner. Never write the plan on a guess: an
unruled correctness-relevant decision is asked, or carried into `## Open decisions` with the
package that must settle it.

## Turn 2 — the write-up

### Breaking the phase into packages

- **One PR per package**, green on tiers 1 and 2 before the next. A package that cannot be verified
  by the end of its own PR is two packages.
- **Order by evidence** (§7.1): a closed form before 2WCD, 2WCD before the ensemble.
- **An opening study goes first and fixes only itself.** Plan it in full and list the rest as
  **provisional** (scope in a sentence, what each waits on, no identifiers); `/phase-plan amend`
  plans them after the study reports.
- **The close package is last**, planned now: it resolves or carries each open decision, re-runs
  the end-of-phase numbers on its own tree, writes the report, sets the `CHANGELOG.md` section and
  `CITATION.cff`, and its last commit on `main` takes the release tag (§2.7 Versioning NOTE).
- Number packages on from the highest `wp<n>`; proposed `VER-`/`VAL-` continue from Appendix A's.

### What to write

**`SPECIFICATION.md` §8.2.x**, a subsection `#### 8.2.<k> Phase <n−1> exit and Phase <n>
decisions, agreed <date>`. Rulings continue the letter series, numbered from 1, in the existing
table form `| # | Decision | Consequence | Clause changed, and when |`. Amend each clause they
change, and §8.1's row if the deliverable, gate or estimate moved.

**`docs/plans/phase-<n>-<slug>.md`**, in the voice of `phase-3-charge-pipeline.md`:

| Section | Content |
|---|---|
| Title + status | `# Phase <n> (<name>): <what it achieves>`, **Status: planned, not started**, packages as planned, the date, the release `v0.<n+1>` |
| `## In brief` | Right after the status; the template below |
| Normativity note | First paragraph of `## Context`, never in the In brief: `SPECIFICATION.md` governs, identifiers are pointers, the rulings are §8.2.<k> |
| `## Context` | The question the phase answers; its gate; the "true of the codebase today" list; the `RSK-` it retires; what it excludes and where each goes |
| `## Design decisions` | `Decision \| Choice \| Why`, each citing its §8.2.<k> ruling |
| `## Conventions established by earlier phases` | Inherited rules no package re-decides, each with its pointer |
| `## Work packages` | `### WP<n> — <name> (<identifiers>)`: scope, identifiers, proposed `VER-`/`VAL-` with oracle, Tier 3 legs. Provisional ones say so and what they wait on. Close last. Tags `v0.<n+1>.0-alpha.N` |
| `## Open decisions` | `# \| Decision \| Owner and status`, with the rulings just taken as **Settled by the author, <date>** |
| `## What the author supplies` | `Item \| Needed by \| If it does not arrive` |
| `## Verification` | Gate commands; a `Package \| Tier \| Identifiers` table; **The phase is complete when:** the numbered criteria with test, tolerance, prediction and ruled fallback |
| `## End-of-phase report` | Only the list of numbers it must report, each with the test that logs it; the close fills it |

Target 3,000 words, excluding the report.

### The In brief

```markdown
## In brief

At most 250 words, no backticks or identifiers; for a reader who does not code.

**What changes.** What the reader will notice, and why it matters.
**Cost.** Time, money or speed, in plain units.
**What could go wrong.** Each risk, and how it would be noticed.
**Your call.** Each decision the author owns, as a question, with *Recommendation:* and one reason.
```

`tests/tier1/test_agent_roster.py` checks every phase plan from Phase 4 on.

**`docs/plans/current.md`**: replace the position with Phase n planned and `/wp-plan <n>` next,
replace the "not to be re-decided" entries the rulings supersede, and keep its In brief and word
target (its *Handoff Rules*). `CLAUDE.md` and the skills change only if a ruling changes the
workflow.

### Finishing

1. Commit on the working branch: `docs: Phase <n> plan and the author's rulings (§8.2.<k>)`, with
   identifiers and ruling numbers in the body. A Markdown-only change outside `packaging/`, `src/`,
   `data/` and `examples/` runs ruff alone (`.github/scripts/prose-only.sh`), except `docs/plans/`,
   which also runs the tests that read plans.
2. Before the push, run the strict documentation build from `CLAUDE.md`'s *Commands* (the
   amended specification renders in it, and CI's `docs` job gates every push), start
   `.claude/hooks/gate.sh run` with Bash `run_in_background`, and push when it passes
   (`git push -u origin <branch>`).
3. Report the paths, the rulings, the package sequence with what is provisional, the open
   decisions and owners, **what the author must supply and when**, and the next step. Then stop.

## Amending a phase

`/phase-plan amend` keeps a phase plan true. It is the only route for planning provisional
packages after an opening study reports (read its report and findings log, put the decisions it
raises to the author as in Turn 1 steps 4–5, then replace the provisional entries), adding or
dropping a package mid-phase (the author's reason, its place, its identifiers), and re-planning
later phases (the rulings, §8.1's rows and any later plans or input notes).

The same two turns apply. New rulings get a new §8.2.x subsection; a superseded ruling gains only a
pointer. An amended package entry gains a
`> **Amended, <date>.**` blockquote (what changed, the ruling); the original paragraph stays. Update the plan's **Status**, `## Open decisions`, `## What the author supplies`,
`## Verification`, the Execution brief of every planned package the change moves, and
`docs/plans/current.md`, all in the one commit, `docs: amend the Phase <n> plan — <what changed>`.
Gate and push as in *Finishing*, report and stop.

## Rules the plan must respect

`.claude/rules/physics-numerics.md` and `.claude/rules/python.md`, and `/wp-plan`'s rules on
normativity and spec amendments.
