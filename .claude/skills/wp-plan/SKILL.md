---
name: wp-plan
description: Write the implementation plan for a nanopnp work package or phase into docs/plans/ and commit it. Use when the user asks to plan a work package, plan the next phase, start WP7, break a phase into work packages, or invokes /wp-plan.
---

# Plan a work package

Step 1 of the implementation workflow: turn a line in `SPECIFICATION.md` §8.1 into a plan detailed
enough that `/wp-implement` can execute it without re-deciding anything that matters. The plan is a
commit under `docs/plans/`, not a chat message.

`SPECIFICATION.md` is normative. This plan is a pointer into it, never a restatement of it, and
where the two disagree the plan is the thing that is wrong. Behaviour the plan needs and the
specification does not permit is a **spec amendment, decided now and written in the same commit** —
never a quiet divergence.

## Before writing anything

1. Read `.knowledge/00-index.md`, then the relevant sections of the files the package touches.
2. Read `SPECIFICATION.md` §8.1 (phases and gates), the sections the package implements, and its
   rows in Appendix A. Collect the exact `FR-`/`QR-`/`CON-`/`PHY-`/`NUM-`/`VER-`/`VAL-`/`RSK-`
   identifiers the package discharges — the plan is written around them. Also collect the `IF-`
   interfaces it must satisfy, the `ADR-` decisions that constrain it, and any `OPN-` the
   specification leaves open in this area: an `OPN-` is what `## Open questions` is *for*, and
   closing one is a spec edit, not a plan note.
3. Read `docs/plans/current.md`, then the requested package's scope, applicable phase decisions
   and verification rows. Follow dependency links only where they constrain this package; do not
   read all delivered summaries or the two most recent WP plans by default. If the brief is absent
   or stale, locate the requested phase/WP headings and repair the brief from those sources.
   For legacy plans without an execution brief, read Decisions, Work items, Verification and the
   Outcomes that amend them; open Design sections only for the decisions this package depends on.
4. Survey the code the package builds on: what exists, what is an empty package reserving a slot,
   which seams already take the argument you need. Delegate this survey (`Explore`, Sonnet — see
   `.claude/model-policy.md`); keep every physics and numerics decision yourself, on Opus.
5. **Do not search the web for the model equations, the correction functions or their parameters.**
   `.knowledge/01-physics-epnpns.md` is the normative reference (`CLAUDE.md`).

## Scope of one work package

One PR, green on tiers 1 and 2 before the next starts. A package that cannot be verified by the end
of its own PR is two packages. Prefer the split that lets an analytic benchmark localise an error to
a single term — that ordering is the point of §7.1 and it is what makes a failure diagnosable.

## What to write

`docs/plans/wp<n>-<slug>.md` for a work package; `docs/plans/phase-<n>-<slug>.md` for a phase.

### A work-package plan

| Section | Content |
|---|---|
| Title + status | `# WP<n> — <name>`, then **Status: planned, not started**, the date, and what it inherits from the packages before it |
| Normativity note | One paragraph: which phase plan it belongs to, that `SPECIFICATION.md` governs, that identifiers are pointers |
| `## Execution brief` | Current scope and dependencies, requirement/section pointers, and the subsections below. Target at most 1,200 words; link evidence rather than retelling prior packages |
| `### Decisions` | A table `Decision \| Choice \| Why/source`. **This is the deliverable.** Resolve choices that affect correctness before implementation; give a short reason and a link to the derivation where needed |
| `### Work items` | Files, deliverables and identifiers, in dependency order; include any required Design section to read before touching that item |
| `### Verification` | Test file, tier, identifiers, assertion/oracle, tolerance source and command. Every claimed `VER-`/`VAL-` appears here |
| `### Out of scope` | Deferrals and their owner |
| `### Open questions` | Author rulings needed before implementation. Ask blocking questions before committing |
| `## Design` | Only new load-bearing derivations, in full arithmetic, with signs and units. Link existing specification/knowledge sections instead of reproducing them. This evidence is outside the brief's word budget |

The brief is an index and execution contract, not a substitute for normative sources or derivations.
If its budget cannot hold the correctness-critical decisions, split the package or state why it must
exceed the target; never omit a required check to meet a word count.

Leave the **Outcome** annotations out. They are blockquotes `> **Outcome — <what changed>.**` added
in place by `/wp-implement` when predictions change. A plan whose predictions hold needs no invented
corrections. Keep the execution brief current; preserve superseded reasoning as labelled history.

### A phase plan

Same voice, one level up: `## Context` (what the phase is *for*, and what it deliberately excludes),
`## Design decisions` spanning the phase, `## Conventions established by <earlier phase>`,
`## Work packages` as `### WP<n> — <name>` with a paragraph of scope and its identifiers each,
`## Open decisions`, `## Verification`, and an empty `## End-of-phase report` naming the numbers the
phase must report. Amendments to the specification's own phase definition go in `SPECIFICATION.md`
§8.2.x, not here.

Keep `docs/plans/current.md` as the bounded entry point (target 800 words): current phase/WP links,
status, live dependency constraints and open decisions. Replace obsolete entries; do not append
completed-package histories. Existing detailed phase summaries remain available on demand.

## Rules the plan must respect

Everything in `CLAUDE.md` under *Physics ground rules* and *Numerics rules*, in particular:
corrections are data not code; classical PNP-NS is a configuration; deviations from the validated
model go behind a flag, default off, and are recorded in the FR-25 manifest; assert, don't hope; a
gate failure aborts with the quantity and its location; integration order ≥ 3 on every form carrying
`1/r`; hard cases are reached by continuation.

## Finishing

1. If a spec amendment is needed, edit `SPECIFICATION.md` in the same commit and say so in the plan.
   Update `docs/plans/current.md` to link the planned package and its live dependencies.
2. Commit on the working branch (create one from `main` if you are on `main`):
   `docs: WP<n> implementation plan`, with the identifiers it discharges in the body.
   The gate hook runs the whole gate, tests included; a docs-only commit passes it unchanged.
   Then `git push -u origin <branch>`. The plan is the brief `/wp-implement` works from, and it may
   be a different session on a different machine — an unpushed commit is one reclaimed container
   away from gone.
3. Report to the user: the path, the decisions that were close calls, any spec amendment made, and
   the open questions — then stop. Implementation is `/wp-implement`, and it is a separate turn.
