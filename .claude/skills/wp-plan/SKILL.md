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

1. Read `.knowledge/00-index.md`, then the `.knowledge/` files the package touches.
2. Read `SPECIFICATION.md` §8.1 (phases and gates), the sections the package implements, and its
   rows in Appendix A. Collect the exact `FR-`/`QR-`/`CON-`/`PHY-`/`NUM-`/`VER-`/`VAL-`/`RSK-`
   identifiers the package discharges — the plan is written around them.
3. Read the phase plan in `docs/plans/` and the two most recent WP plans. They carry conventions
   established by merged work that the specification does not repeat, and the house structure below.
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
| `## Context` | What the preceding packages built and what they deliberately did not; the empty slots this fills; the risk it retires, named (`RSK-nn`) and quantified |
| `## Decisions taken before implementation` | A table `Decision \| Choice \| Why`. **This is the deliverable.** Every choice an implementer would otherwise make at 2 a.m. — how the body enters the mesh, which route is the oracle, what runs classical and why, what stays behind a flag — decided here with the reason, so implementation is execution rather than design |
| `## Design` | The load-bearing derivations, in full arithmetic. The identity behind a numerics clause, the term it hides, the sign, the tolerance in both SI and nondimensional units. Anything the specification must gain as a NOTE, written out ready to paste |
| Work items | A table of files against what each delivers and which identifiers it discharges. Name new modules and the subpackage they belong to (§5.1) |
| `## Verification` | A table `test file \| tier \| identifiers \| what it asserts`, with the tolerance and where it comes from. Every `VER-`/`VAL-` the package claims appears here |
| `## Out of scope` | What a reader will expect and not get, and which release owns it |
| `## Open questions` | Anything needing the author's ruling before implementation starts. Ask these before committing if they block the work |

Leave the **Outcome** annotations out. They are blockquotes `> **Outcome — <what changed>.**` added
in place by `/wp-implement` as predictions turn out wrong, and a plan whose predictions all held is
a plan that was not specific enough.

### A phase plan

Same voice, one level up: `## Context` (what the phase is *for*, and what it deliberately excludes),
`## Design decisions` spanning the phase, `## Conventions established by <earlier phase>`,
`## Work packages` as `### WP<n> — <name>` with a paragraph of scope and its identifiers each,
`## Open decisions`, `## Verification`, and an empty `## End-of-phase report` naming the numbers the
phase must report. Amendments to the specification's own phase definition go in `SPECIFICATION.md`
§8.2.x, not here.

## Rules the plan must respect

Everything in `CLAUDE.md` under *Physics ground rules* and *Numerics rules*, in particular:
corrections are data not code; classical PNP-NS is a configuration; deviations from the validated
model go behind a flag, default off, and are recorded in the FR-25 manifest; assert, don't hope; a
gate failure aborts with the quantity and its location; integration order ≥ 3 on every form carrying
`1/r`; hard cases are reached by continuation.

## Finishing

1. If a spec amendment is needed, edit `SPECIFICATION.md` in the same commit and say so in the plan.
2. Commit on the working branch (create one from `main` if you are on `main`):
   `docs: WP<n> implementation plan`, with the identifiers it discharges in the body.
   The gate hook runs; a docs-only commit passes it unchanged.
3. Report to the user: the path, the decisions that were close calls, any spec amendment made, and
   the open questions — then stop. Implementation is `/wp-implement`, and it is a separate turn.
