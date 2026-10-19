---
name: wp-plan
description: Write the implementation plan for a nanopnp work package into docs/plans/ and commit it. Use when the user asks to plan a work package, start WP7, or invokes /wp-plan. Planning or amending a whole phase is /phase-plan.
---

# Plan a work package

Step 1 of the implementation workflow: turn a package of the phase plan (`/phase-plan`) into a plan
detailed enough that `/wp-implement` can execute it without re-deciding anything that matters. The
plan is a commit under `docs/plans/`, not a chat message.

`SPECIFICATION.md` is normative. The plan points into it and never restates it; where they disagree
the plan is wrong. Behaviour the plan needs and the specification does not permit is a **spec
amendment, decided now and written in the same commit**, never a quiet divergence.

## Before writing anything

1. Read `knowledge/index.md`, then the sections of the files the package touches. Read
   `.claude/rules/physics-numerics.md` and `.claude/rules/python.md`: the plan must respect both,
   and a path-scoped rule does not load while you write only Markdown.
2. Read `SPECIFICATION.md` §8.1, the sections the package implements, and its Appendix A rows.
   Collect the `FR-`/`QR-`/`CON-`/`PHY-`/`NUM-`/`VER-`/`VAL-`/`RSK-` identifiers it discharges, the
   `IF-` interfaces it satisfies, the `ADR-` decisions that constrain it and any `OPN-` open in
   this area (closing one is a spec edit; `## Open questions` is for it). `.claude/scripts/clause.py
   <ID>` prints a clause with its NOTEs and rulings.
3. Read `docs/plans/current.md`, then the package's scope, phase decisions and verification rows.
   Follow dependency links only where they constrain this package. If the brief is absent or
   stale, repair it from the phase and WP headings. A package not in its phase plan, or listed
   **Provisional**, goes through `/phase-plan amend` first.
4. Survey the code the package builds on: what exists, what is an empty package reserving a slot,
   which seams take the argument you need. Delegate a survey to Haiku or Sonnet (`CLAUDE.md`, *Models*) and read the lines it
   returns before relying on them; keep every physics and numerics decision yourself.
5. Do not search the web for the model equations or their parameters (`CLAUDE.md`).

## Scope of one work package

One PR, green on tiers 1 and 2 before the next starts. A package that cannot be verified by the end
of its own PR is two packages. Prefer the split that lets an analytic benchmark localise an error to
a single term (§7.1).

## What to write

`docs/plans/wp<n>-<slug>.md`:

| Section | Content |
|---|---|
| Title + status | `# WP<n> — <name>`, then **Status: planned, not started**, the date, and what it inherits |
| Normativity note | One paragraph: the phase plan it belongs to, that `SPECIFICATION.md` governs, that identifiers are pointers |
| `## In brief` | Before the Execution brief; the template below |
| `## Execution brief` | Current scope, dependencies, requirement pointers and the subsections below. The plan holds **at most 1,500 words outside its Outcome annotations** (`tests/tier1/test_plan_shape.py` fails a longer one); link evidence rather than retelling earlier packages |
| `### Decisions` | A table `Decision \| Choice \| Why/source`, **at most six rows**. **This is the deliverable.** Resolve every choice that affects correctness now |
| `### Work items` | A checklist in dependency order, one commit per item: `- [ ] 3. <files and deliverable> (D4); done when <tests> pass`, or, for an item outside the test scope (`SPECIFICATION.md` §8.2.13 N1), done when the code and review say so. Name the files in backticks. After a group of items, a line *Compaction checkpoint: after item N; resume from this plan and `git log`.* |
| `### Verification` | Test file, tier, identifiers, oracle, tolerance source and command, for in-scope tests only (§8.2.13 N1). Every claimed in-scope `VER-`/`VAL-` appears here; an out-of-scope item's done-criterion is "the code and review say so" (N3) |
| `### Out of scope` | Deferrals and their owner |
| `### Open questions` | Author rulings needed before implementation; ask blocking ones before committing |

The plan is an index and execution contract, with no per-item design and no `## Design` heading. A
derivation that is new and load-bearing goes into the specification, which the plan links. If 1,500 words
and six decisions cannot hold the correctness-critical choices, split the package; never omit a
required check to meet a count.

### The In brief

```markdown
## In brief

At most 250 words, no backticks or identifiers; for a reader who does not code.

**What changes.** What the reader will notice, and why it matters.
**Cost.** Time, money or speed, in plain units.
**What could go wrong.** Each risk, and how it would be noticed.
**Your call.** Each decision the author owns, as a question, with *Recommendation:* and one reason.
```

`tests/tier1/test_plan_shape.py` checks every plan from WP44 on.

### Work items

Leave the boxes unticked; `/wp-implement` ticks them. The plan commits no tests: the implementer writes
each with its item from the *Verification* rows. Where a decision says *never*, *always* or *every*, its
verification row enumerates each point of failure with one assertion each: an oracle looser than its
decision is a defect.

### `docs/plans/current.md`

Link the planned package and its live dependencies; its word target is in its *Handoff Rules*.

## Finishing

1. A needed spec amendment goes in the same commit, and the plan says so.
2. Commit on the working branch (on `main`, switch to the branch this session was given, or stop
   and ask): `docs: WP<n> implementation plan`, identifiers in the body. A plan-only change runs
   ruff and the tests (`CLAUDE.md`, *Commands*). Then `git push -u origin <branch>`: another session on another machine may work from it.
3. Report the path, the close calls, any spec amendment and
   the open questions. Then stop; implementation is `/wp-implement`, a separate turn.
