# Plan a phase

`/np-plan phase <n>`. The level above `/np-plan wp`: turn a row of `SPECIFICATION.md` §8.1 into the
author's rulings and a sequence of work packages, each small enough for one PR. The deliverables
are a ruling record in `specification/history/` and `docs/plans/phase-<n>-<slug>.md`, committed
together. A package's own decisions are `/np-plan wp <n>`'s; this level decides only what spans
packages.

`/np-plan phase <n>` plans Phase n in **two turns**: a ruling round, then the write-up.
`/np-plan amend <n>` amends the phase in flight (`amend.md`).

## Turn 1 — the ruling round

Nothing is committed in this turn.

### 1. Preconditions

1. If a `docs/plans/phase-<n>-*.md` exists, this is an amendment: read `amend.md` beside this
   file and follow it.
2. Phase n−1 is closed: its close package has merged, its end-of-phase report is written and its
   `vX.Y.0` tag is published or is the author's next step. If not, say so **first** and put the
   close first in the round: finish it, or rule that Phase n overlaps it and what Phase n may not
   do before it lands.
3. Versions agree, as `rulings.md` says.

### 2. Collect what the phase inherits

Read what `rulings.md`'s *What a phase inherits* lists, keeping a list of every item that needs a
decision.

### 3. Survey the codebase

Delegate a survey (the core, *Models*) of what the phase builds on: what exists, what is
refused today naming a later phase, which seams take what the phase needs. From it write the
**"true of the codebase today"** list yourself: five or so facts, each naming its file and function.

### 4 and 5. Draft the decisions and put them to the author

As `rulings.md` says.

## Turn 2 — the write-up

### Breaking the phase into packages

- **One PR per package**, green on tiers 1 and 2 before the next. A package that cannot be verified
  by the end of its own PR is two packages.
- **Order by evidence** (§7.1): a closed form before 2WCD, 2WCD before the ensemble.
- **An opening study goes first and fixes only itself.** Plan it in full and list the rest as
  **provisional** (scope in a sentence, what each waits on, no identifiers); `/np-plan amend` plans
  them after the study reports.
- **The close package is last**, planned now: it resolves or carries each open decision, re-runs
  the end-of-phase numbers on its own tree, writes the report, sets the `CHANGELOG.md` section and
  `CITATION.cff`, and its last commit on `main` takes the release tag (§2.7 Versioning NOTE).
  `/np-ship phase <n>` ships it.
- Number packages on from the highest `wp<n>`; proposed `VER-`/`VAL-` continue from Appendix A's.

### What to write

**The ruling record**, as `rulings.md` says, its title `Phase <n−1> exit and Phase <n> decisions,
agreed <date>`. Amend each clause the rulings change, and §8.1's row if the deliverable, gate or
estimate moved.

**`docs/plans/phase-<n>-<slug>.md`**, in the voice of `phase-3-charge-pipeline.md`:

| Section | Content |
|---|---|
| Title + status | `# Phase <n> (<name>): <what it achieves>`, **Status: planned, not started**, packages as planned, the date, the release `v0.<n+1>` |
| `## In brief` | Right after the status; the core's template |
| Normativity note | First paragraph of `## Context`, never in the In brief: `SPECIFICATION.md` governs, identifiers are pointers, the rulings are §8.2.<k> |
| `## Context` | The question the phase answers; its gate; the "true of the codebase today" list; the `RSK-` it retires; what it excludes and where each goes |
| `## Design decisions` | `Decision \| Choice \| Why`, each citing its §8.2.<k> ruling |
| `## Conventions established by earlier phases` | Inherited rules no package re-decides, each with its pointer |
| `## Work packages` | `### WP<n> — <name> (<identifiers>)`: scope, identifiers, proposed `VER-`/`VAL-` with oracle, Tier 3 legs. Provisional ones say so and what they wait on. Close last. Tags `v0.<n+1>.0-alpha.N` |
| `## Open decisions` | `# \| Decision \| Owner and status`, with the rulings just taken as **Settled by the author, <date>** |
| `## What the author supplies` | `Item \| Needed by \| If it does not arrive` |
| `## Verification` | Gate commands; a `Package \| Tier \| Identifiers` table listing in-scope tests only (N1); **The phase is complete when:** the numbered criteria with test, tolerance, prediction and ruled fallback |
| `## End-of-phase report` | Only the list of numbers it must report, each with the test that logs it; the close fills it |

Target 1,500 words, excluding the report.

Review checks every phase plan from Phase 4 on against these caps (§8.2.13 N3).

**`docs/plans/current.md`**: replace the position with Phase n planned and `/np-plan wp <n>` next,
replace the "not to be re-decided" entries the rulings supersede, and keep its In brief and word
target (its *Handoff Rules*). `CLAUDE.md` and the skills change only if a ruling changes the
workflow.

### Finishing

1. Commit on the working branch: `docs: Phase <n> plan and the author's rulings (§8.2.<k>)`, with
   identifiers and ruling numbers in the body.
2. Gate, push and open the PR as `rulings.md`'s *Finishing* says, its body naming the package
   sequence. The author merges it before the first package is planned.
3. Report the paths, the PR, the rulings, the package sequence with what is provisional, the open
   decisions and owners, **what the author must supply and when**, and the next step. Then stop.
