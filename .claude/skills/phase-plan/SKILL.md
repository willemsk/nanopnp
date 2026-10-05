---
name: phase-plan
description: Plan a nanopnp phase — collect what the previous phase carries, put the phase's design decisions to the author as a ruling round, then write the rulings into SPECIFICATION.md §8.2, the phase plan into docs/plans/ and commit it. Also amends a phase in flight (re-plan after an opening study, add or drop a work package). Use when the user asks to plan the next phase, plan phase 4, break a phase into work packages, re-plan or amend a phase, or invokes /phase-plan.
---

# Plan a phase

The level above `/wp-plan`: turn a row of `SPECIFICATION.md` §8.1 into the author's rulings and a
sequence of work packages, each small enough for one PR. The deliverables are a §8.2.x rulings
section and `docs/plans/phase-<n>-<slug>.md`, committed together. A work package's own decisions are
still `/wp-plan <n>`'s; this skill decides only what spans packages.

`SPECIFICATION.md` is normative. The phase plan points into it and never restates it. A ruling that
changes a clause amends that clause in the same commit, and the §8.2.x row names the clause.

Invocations:

| Form | What it does |
|---|---|
| `/phase-plan <n>` | Plans Phase n: **two turns**, a ruling round and then the write-up (below) |
| `/phase-plan amend [<n>]` | Amends the phase in flight: re-plans provisional packages after an opening study reports, adds or drops a package, or records a re-plan of later phases (§ *Amending a phase*) |

## Turn 1 — the ruling round

Nothing is committed in this turn. It ends with the author's rulings in hand.

### 1. Preconditions

1. Check the branch. If it is `main`, switch to the development branch this session was given; if
   none was given, stop and ask (the same rule as `wp-plan` and `wp-implement`).
2. If a `docs/plans/phase-<n>-*.md` already exists, this is an amendment: switch to
   § *Amending a phase* now, before the checks below, which belong to a phase not yet planned.
3. Phase n−1 is closed: its close package has merged, its end-of-phase report is written, and its
   `vX.Y.0` tag is published (step 4) or is the author's next step. If it is not, say so **before
   anything else** and put the close first in the ruling round: finish it (its own package, or
   `/phase-plan amend <n−1>` if it was never planned), or rule that Phase n overlaps it. An overlap
   is itself a ruling (Phase 3 started before `v0.3.0`), and it names what Phase n may not do before
   the close lands (for example, tag). Phase 2's plan merged before Phase 1's end-of-phase report
   existed, and the branch had to be restarted from `main`; that is the case this step prevents.
4. Versions agree everywhere before a new one is named: §2.7's table and Versioning NOTE, the
   Release column of §3, §8.1, the head of `CHANGELOG.md`, `current.md` and the published tags
   (`git ls-remote --tags origin 'v0.*'`; a hosted session clones shallow, and its `git tag -l`
   lists only the tags its truncated history reaches). One minor per phase: packages
   `v0.<m>.0-alpha.N`, and the release `v0.<m>.0` on the commit that merges the end-of-phase report
   (the §2.7 Versioning NOTE). A disagreement goes into the ruling round; it is not resolved
   silently, and it is not left for the close (it forced a renumbering of every tag in the middle of
   Phase 3's planning).

### 2. Collect what the phase inherits

Read, in this order, and keep a list of every item that needs a decision:

1. `docs/plans/current.md`, then `.knowledge/00-index.md`.
2. `SPECIFICATION.md` §8.1: Phase n's row (deliverable, gate, estimate) and its GUI and
   documentation increments. Then every §8.2.x section, newest first, for rulings that already bind
   Phase n. A ruling already taken is cited, never re-asked.
3. The previous phase plan: its `## End-of-phase report` (above all, what it **carries**), its
   `## Open decisions` rows still open, and every **Live for later packages** line in its delivered
   summaries and in the Outcomes of its WP plans.
4. §10's open `OPN-` items and §9's `RSK-` register: which ones this phase is scheduled to retire
   or could close. Closing an `OPN-` is a spec edit.
5. Any decided-not-planned input note under `docs/plans/` that names this phase (for example,
   `okf-knowledge-bundle.md` for Phase 4). Its decisions are binding; its open questions join the
   ruling round.
6. Appendix A: which requirements are tagged for this phase's version and not yet discharged.

### 3. Survey the codebase

Delegate a survey (`Explore`, Sonnet — `.claude/model-policy.md`; a missed file is a loud failure)
of what the phase builds on: what exists, what is an empty package reserving a slot, what is
refused today naming a later phase, which seams already take what the phase needs. From it, write
the **"true of the codebase today"** list yourself — five or so facts that shape every package, as
in Phase 3's `## Context`. Each fact names its file and function. Keep every physics and numerics
judgement on Opus.

### 4. Draft the decisions

A phase decision is one that more than one work package depends on, or that the author must own:
the order of evidence, a kernel or a discretisation choice that every later package inherits, what
goes in this phase and what is deferred, a dependency that enters the lock, a spec amendment the
phase needs, versioning and the close. Always cover:

- **the gate, pre-registered.** Each completion criterion names its test, its tolerance and where
  that tolerance was argued, a predicted value where one can be made, and the **fallback on a
  miss**: investigate, re-argue the tolerance (a spec amendment, never a quiet slackening), or
  waive and carry. Phases 1 and 2 each closed only after a fresh ruling on a criterion they did
  not meet (§8.2.3 C1, §8.2.4 D7); a fallback ruled now turns that into a recorded step;
- **what the author supplies**: data from their archive or machine (Tier 3 runs, reference sets,
  figure data), rulings only they can give, and observations by a person (QR-10). Each with the
  package that needs it and what happens if it does not arrive;
- **who merges and who tags.** The author merges. A session's GitHub access may not push tags, so
  the plan says whether the close tags or prints the commands for the author, and whether the close
  takes the release tag alone, with no `-alpha.N` beside it (as §8.2.5 E5 ruled for Phase 3).

Draft each decision with:

- the question, in one sentence, with the identifiers it touches;
- two to four options, each with its consequence for correctness, scope and the push gate's
  cost, and the clause it would amend;
- a recommendation, first in the list, and why.

Also draft, for the author to see alongside the decisions:

- the **work-package sequence** (§ *Breaking the phase into packages*), with each package's scope in
  a sentence and its proposed identifiers;
- the **completion criteria**, numbered, each one checkable by a named test or an observation;
- what the phase **deliberately excludes**, and where each exclusion goes.

### 5. Put it to the author

Ask through `AskUserQuestion`, at most four questions a call, with enough context in each question
and option that the author can rule without scrolling back: the clause at stake, the cost of each
option, and what is already ruled. Ask the decisions that change the work-package sequence first,
then the sequence itself, then the rest. A ruling the author gives in prose is recorded in their
words. Where the session has no `AskUserQuestion`, put the questions in one message, numbered, and
end the turn there: the author's reply opens Turn 2.

A scope change the author volunteers mid-round (Phase 3's move of Tier 3 to the published I–V
curves) is a ruling like any other: record it, then re-check which drafted decisions and packages it
moves before asking the rest.

Stop when every decision is ruled or explicitly left open with an owner. Do not write the plan on a
guess: an unruled correctness-relevant decision is either asked or carried into `## Open decisions`
with the package that must settle it.

## Turn 2 — the write-up

### Breaking the phase into packages

- **One PR per package**, green on tiers 1 and 2 before the next starts. A package that cannot be
  verified by the end of its own PR is two packages.
- **Order by evidence**: a closed form before 2WCD, 2WCD before the ensemble (§7.1). An interface
  that later packages read goes first (Phase 3's WP26).
- **An opening study goes first and fixes only itself.** When the §8.1 row opens the phase with a
  study, report or design document (Phase 4's modularity report, F3; Phase 5's design document,
  F5), plan that package in full and list the rest as **provisional**: scope in a sentence, what
  each waits on, no identifiers claimed. `/phase-plan amend` plans them after the study reports.
- **The GUI and documentation increments** of §8.1 are packages of their own, after the work they
  surface.
- **The close package is always last**, planned now: it resolves or carries each open decision,
  re-runs the end-of-phase report's numbers on its own tree, writes the report, sets the
  `CHANGELOG.md` section and `CITATION.cff` for the release, and its last commit on `main` takes
  the release tag `v0.<n+1>.0` (the §2.7 Versioning NOTE). The NOTE would also give that commit a
  `-alpha.N`; taking the release tag alone is a ruling of the round (step 4), as §8.2.5 E5 was
  for Phase 3. It is not improvised at the end of the phase.
- Number packages on from the highest existing `wp<n>`. Proposed `VER-`/`VAL-` identifiers continue
  from the highest in Appendix A, and each package claims its own when it implements them.

### What to write

**`SPECIFICATION.md` §8.2.x**, a new subsection `#### 8.2.<k> Phase <n−1> exit and Phase <n>
decisions, agreed <date>` (or `Phase <n> decisions` when there is nothing to record about the
exit). Rulings continue the letter series (the next after F is G), numbered from 1, in the
existing table form: `| # | Decision | Consequence | Clause changed, and when |`. A sentence above
the table says when and while doing what the rulings were taken. Amend each clause the rulings
change, and §8.1's row if the deliverable, gate or estimate moved.

**`docs/plans/phase-<n>-<slug>.md`**, in the voice of `phase-3-charge-pipeline.md`:

| Section | Content |
|---|---|
| Title + status | `# Phase <n> (<name>): <what it achieves>`, then **Status: planned, not started**, with the packages listed as planned (`/wp-implement` moves each to a delivered list), the date, and the release `v0.<n+1>` |
| Normativity note | That `SPECIFICATION.md` governs, that identifiers are pointers, and that the rulings are §8.2.<k> and are not re-argued here |
| `## Context` | The question the phase answers; its gate; the "true of the codebase today" list; the `RSK-` it retires; what it deliberately excludes and where each goes |
| `## Design decisions` | `Decision \| Choice \| Why`, each citing its §8.2.<k> ruling. What each package's `/wp-plan` will decide instead is said in one line above the table |
| `## Conventions established by earlier phases` | The inherited rules no package re-decides, each with its pointer. Bring forward the previous phase plan's list, dropping what has been superseded |
| `## Work packages` | `### WP<n> — <name> (<identifiers>)`: a paragraph of scope, the identifiers it discharges, the proposed `VER-`/`VAL-` with their oracle, its Tier 3 legs (recorded). Provisional packages say **Provisional** and what they wait on. The close package last. Tags `v0.<n+1>.0-alpha.N` |
| `## Open decisions` | `# \| Decision \| Owner and status`: everything not ruled, with the package that must settle it, and the rulings just taken as **Settled by the author, <date>** (§8.2.<k> <id>) |
| `## What the author supplies` | `Item \| Needed by \| If it does not arrive`: data, runs on the author's machine, observations, the merge and the tag |
| `## Verification` | The gate commands; a `Package \| Tier \| Identifiers` table; then **The phase is complete when:** the numbered criteria, each with its test, tolerance, prediction and ruled fallback |
| `## End-of-phase report` | Empty except for the list of numbers it must report, each with the test that will log it. The close package fills it |

Target 3,000 words for the plan, excluding the end-of-phase report. Link derivations; do not
reproduce them.

**`docs/plans/current.md`**: replace the position with Phase n planned, the first package and its
`/wp-plan <n>` as the next step; replace the "not to be re-decided" entries the new rulings
supersede; keep it to 800 words.

**`CLAUDE.md`, the skills and the session-start hook** are not touched unless a ruling changes the
workflow itself.

### Finishing

1. Commit on the working branch: `docs: Phase <n> plan and the author's rulings (§8.2.<k>)`, with
   the identifiers and ruling numbers in the body. A plan that only touches Markdown outside
   `packaging/`, `src/`, `data/` and `examples/` is prose-only and the gate hook runs ruff alone
   (`.github/scripts/prose-only.sh`).
2. Before the push, run `.claude/hooks/gate.sh run` (`CLAUDE.md`, *Git*) and the strict
   documentation build as `CLAUDE.md`'s *Commands* table gives it: the build renders the amended
   specification, and CI's `docs` job gates it on every push, prose-only ones included. Then
   `git push -u origin <branch>`. The plan is the brief every package's `/wp-plan` starts from, and
   it may be read from another session on another machine.
3. Report to the author: the paths, the rulings as recorded, the package sequence with what is
   provisional, the open decisions and their owners, **what the author must supply and when**, and
   the next step (`/wp-plan <first WP>`). Then stop. Planning a package is `/wp-plan`, in its own turn.

## Amending a phase

`/phase-plan amend` keeps a phase plan true when the work changes it. It is the only route for:

- **planning provisional packages** after an opening study reports: read the study's report and
  its findings log, put the decisions it raises to the author (Turn 1, steps 4–5), then replace the
  provisional entries with full ones;
- **adding or dropping a package mid-phase** (as WP33 and WP34 were added to Phase 3): the author's
  reason, where it sits in the sequence, and its identifiers;
- **re-planning later phases** (as §8.2.6 F1–F6 did while Phase 3 was open): the rulings, §8.1's
  rows, and the later phase plans or input notes that exist.

The same two turns apply: rulings first, then the write-up. New rulings get a new §8.2.x
subsection. An agreed ruling's text is not rewritten: one that a new ruling supersedes gains only a
pointer to it, as §8.2.3 C1 points to §8.2.4 D6. In the phase plan, an amended package entry gains a
`> **Amended, <date>.**` blockquote stating what changed and the ruling behind it; the original
paragraph stays, because the plan is a record. Update the plan's **Status** line, `## Open
decisions`, `## What the author supplies`, `## Verification`, the Execution brief of every planned
package the change moves, and `docs/plans/current.md`, all in the one commit. Commit as
`docs: amend the Phase <n> plan — <what changed>`, gate it as in *Finishing*, push, report and
stop.

## Rules the plan must respect

Everything in `CLAUDE.md` under *Physics ground rules* and *Numerics rules*; the rules of `/wp-plan`
on normativity and spec amendments; and **do not search the web for the model equations, the
correction functions or their parameters** (`.knowledge/01-physics-epnpns.md` is normative).
