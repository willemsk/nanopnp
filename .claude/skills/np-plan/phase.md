# Plan a phase

`/np-plan phase <n>` is the level above `/np-plan wp`. It turns a row of `SPECIFICATION.md` §8.1 into
the author's rulings and a sequence of work packages, each small enough for one PR. It delivers a
ruling record in `specification/history/` and `docs/plans/phase-<n>-<slug>.md`, in one commit. A
package's own decisions belong to `/np-plan wp <n>`; this level decides only what spans packages.

`/np-plan phase <n>` plans Phase n in **two turns**: a ruling round, then the write-up.
`/np-plan amend <n>` amends the phase in flight (`amend.md`).

## Turn 1 — the ruling round

Commit nothing in this turn.

### 1. Preconditions

1. If a `docs/plans/phase-<n>-*.md` exists, this is an amendment: read `amend.md` beside this file
   and follow it.
2. Phase n−1 is closed: its close package has merged, its end-of-phase report is written, and its
   `vX.Y.0` tag is published or is the author's next step. If not, say so **first**, and put the
   close first in the round. Either finish it, or get a ruling that Phase n overlaps it and what
   Phase n must not do before it lands.
3. Versions agree, as `rulings.md` says.

### 2. Collect what the phase inherits

Read what `rulings.md`'s *What a phase inherits* lists. Keep a list of each item that needs a
decision.

### 3. Survey the codebase

Give a survey (the core, *Models and executors*) of what the phase builds on: what exists, what is
refused today with the name of a later phase, which seams take what the phase needs. From it, write
the **"true of the codebase today"** list yourself: about five facts, each with its file and
function.

### 4 and 5. Draft the decisions and put them to the author

As `rulings.md` says.

## Turn 2 — the write-up

### Breaking the phase into packages

- **One PR per package**, green on tiers 1 and 2 before the next in its lane. If a package cannot be verified by
  the end of its own PR, it is two packages.
- **Order by evidence** (§7.1): a closed form before 2WCD, 2WCD before the ensemble.
- **An opening study goes first and fixes only itself.** Plan it in full. List the other packages as
  **provisional**: scope in one sentence, what each waits on, no identifiers. `/np-plan amend` plans
  them after the study reports.
- **The close package is last**, and you plan it now. It resolves or carries each open decision,
  runs the end-of-phase numbers again on its own tree, writes the report, and sets the
  `CHANGELOG.md` section and `CITATION.cff`. Its last commit on `main` gets the release tag (§2.7
  Versioning NOTE). `/np-ship phase <n>` ships it.
- Number the packages on from the highest `wp<n>`. Proposed `VER-`/`VAL-` continue from Appendix
  A's.

### What to write

**The ruling record**, as `rulings.md` says, with the title `Phase <n−1> exit and Phase <n>
decisions, agreed <date>`. Amend each clause that the rulings change, and §8.1's row if the
deliverable, gate or estimate moved.

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

Target 1,500 words, without the report.

Review checks each phase plan from Phase 4 on against these caps (§8.2.13 N3).

**`docs/plans/current.md`**: replace the position with Phase n planned and `/np-plan wp <n>` next,
or add that line beside Phase n−1's while it is open (the core's *Two lanes*).
Replace the "not to be re-decided" entries that the rulings supersede. Keep its In brief and its word
target (its *Handoff Rules*). `CLAUDE.md`, `.claude/workflow/` and the skills change only if a ruling changes the
workflow.

### Finishing

1. Commit on the working branch: `docs: Phase <n> plan and the author's rulings (§8.2.<k>)`, with
   the identifiers and ruling numbers in the body.
2. Gate, push and open the PR as `rulings.md`'s *Finishing* says; its body names the package
   sequence. The author merges it before the first package is planned.
3. Report the paths, the PR, the rulings, the package sequence and which packages are provisional,
   the open decisions and their owners, **what the author must supply and when**, and the next step.
   Then stop.
