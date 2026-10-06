---
name: wp-plan
description: Write the implementation plan for a nanopnp work package into docs/plans/ and commit it. Use when the user asks to plan a work package, start WP7, or invokes /wp-plan. Planning or amending a whole phase is /phase-plan.
---

# Plan a work package

Step 1 of the implementation workflow: turn a package of the phase plan (`/phase-plan`) into a plan
detailed enough that `/wp-implement` can execute it without re-deciding anything that matters. The plan is a
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
   A package that is not in its phase plan, or that the plan lists as **Provisional**, is not
   planned here: it goes through `/phase-plan amend` first.
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

`docs/plans/wp<n>-<slug>.md`. A phase plan is not this skill's: `/phase-plan <n>` plans a phase,
with a ruling round before the write-up, and `/phase-plan amend` changes one in flight.

### A work-package plan

| Section | Content |
|---|---|
| Title + status | `# WP<n> — <name>`, then **Status: planned, not started**, the date, and what it inherits from the packages before it |
| Normativity note | One paragraph: which phase plan it belongs to, that `SPECIFICATION.md` governs, that identifiers are pointers |
| `## Execution brief` | Current scope and dependencies, requirement/section pointers, and the subsections below. Target at most 1,200 words; link evidence rather than retelling prior packages |
| `### Decisions` | A table `Decision \| Choice \| Why/source`. **This is the deliverable.** Resolve choices that affect correctness before implementation; give a short reason and a link to the derivation where needed |
| `### Work items` | A checklist in dependency order, one commit per item: `- [ ] 3. [Opus] — <reason>. <files and deliverable> (D4); done when <tests> pass`. See *Work items* below. Include any required Design section to read before touching that item |
| `### Verification` | Test file, tier, identifiers, assertion/oracle, tolerance source and command. Every claimed `VER-`/`VAL-` and every planned test appears here |
| `### Out of scope` | Deferrals and their owner |
| `### Open questions` | Author rulings needed before implementation. Ask blocking questions before committing |
| `## Design` | Only new load-bearing derivations, in full arithmetic, with signs and units. Link existing specification/knowledge sections instead of reproducing them. This evidence is outside the brief's word budget |

The brief is an index and execution contract, not a substitute for normative sources or derivations.
If its budget cannot hold the correctness-critical decisions, split the package or state why it must
exceed the target; never omit a required check to meet a word count. A brief over 1,200 words or
about ten decisions splits the package or says why not in its first paragraph.

### Work items

- Each item is marked `[Opus]` or `[any]` in the item itself (`.claude/model-policy.md`, *Who
  implements a plan*). `[Opus]`: a mistake would pass the gate as a plausible wrong answer
  (physics, numerics, a refusal or its text, a cleanup or error path, a classification, a key);
  give the reason in one clause. `[any]`: anything whose failure is loud. Unsure means `[Opus]`.
- Each item is one commit, with a done-criterion naming the tests that then pass.
- Leave the boxes unticked; `/wp-implement` ticks them.

### Planned tests

Coverage sees neither missing code nor an untaken arm of a conditional expression, and an
implementer's own tests check what was built rather than what was decided. So for every `[Opus]`
decision whose failure would be a silent pass, this plan's commit writes the tests, with exact
assertions: the refusal and remedy text, the state after the failure. Each is a strict expected
failure until implemented:

```python
@pytest.mark.xfail(strict=True, reason="planned: WP<n> D<k>")
```

A planned test imports new code inside its body, so its file collects before the code exists.
VER-72 fails a `planned:` marker that is not strict, names no existing plan, or outlives its
package's delivery.

Where a decision says *never*, *always* or *every*, its verification row enumerates each point of
failure (each setup step, each cleanup step) with one assertion each. An oracle looser than its
decision is a defect of the plan.

Leave the **Outcome** annotations out. They are blockquotes `> **Outcome — <what changed>.**` added
in place by `/wp-implement` when predictions change. A plan whose predictions hold needs no invented
corrections. Keep the execution brief current; a plan is a record, so its Outcomes may keep the
history of what changed.

### `docs/plans/current.md`

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
2. Commit on the working branch — if you are on `main`, switch to the development branch this
   session was given, and if none was given, stop and ask (the same rule as `wp-implement`):
   `docs: WP<n> implementation plan`, with the identifiers it discharges in the body.
   The gate hook sees a prose-only change (Markdown outside `packaging/`, `src/`, `data/` and `examples/`, other than a `*findings.md`
   log; see
   `.github/scripts/prose-only.sh`) and runs ruff alone. A plan that also commits its planned tests,
   or moves code, data or the YAML under `docs/sweeps/` or `docs/validation/`, pays for the whole
   gate; each planned test must report `xfailed`, not `error`.
   Then `git push -u origin <branch>`. The plan is the brief `/wp-implement` works from, and it may
   be a different session on a different machine — an unpushed commit is one reclaimed container
   away from gone.
3. Report to the user: the path, the decisions that were close calls, any spec amendment made, the
   `[Opus]` items and the planned tests, and the open questions — then stop. Implementation is `/wp-implement`, and it is a separate turn.
