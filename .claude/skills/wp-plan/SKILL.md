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
5. Do not search the web for the model equations or their parameters (`CLAUDE.md`). Check every
   library API the plan names against its current documentation (Context7).

## Grounding the plan

The plan is written for an implementer on Sonnet who has not seen this session. Once the decisions
are drafted, and before committing, read the code each decision and work item changes or relies on,
yourself, and settle every point the implementer would otherwise guess at (§8.2.15 Q1). For each,
ask:

- **Where.** Which function, class or constant changes, named `path:symbol`. Is it the seam the
  change belongs in, or a caller of it?
- **Does it run.** Trace the call path the change rides on. Does it run on the default path, or only
  when a caller passes a hook, an option or an extra? A recording hung on an optional callback
  records nothing for the caller who passes none.
- **Shapes.** What it reads and writes: types, fields, units, payload keys and file formats. A new
  file or record is given its exact layout.
- **Variants.** Every form its input takes: supplied or generated, cached before or after the
  change, an extra installed or not, an optional upstream stage present or absent. Name the
  variant the obvious path misses, and say what happens to it.
- **Rows.** The registry entries, `modularity-layering.yaml` rows (static or string, with their
  finding) and public names it adds, and which existing guard reads them.
- **Tests.** How each test obtains the object it checks: the fixture, the store, the working
  directory and the commands an existing example already runs. Name an existing helper to reuse
  before writing one.

Each answer is a fact, verified at the commit the plan is written on. It goes into
`### Grounding`, or into its decision where it changes the choice. A fact that changes a decision
is a decision, and the decision moves. Then read the plan as its implementer would. For each work
item, could it be written without opening a file the plan does not name, and without choosing
between two behaviours? If not, the plan is not finished.

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
| `## Execution brief` | Current scope, dependencies, requirement pointers and the subsections below. The plan holds **at most 2,500 words outside its Outcome annotations, at most 1,500 of them outside `### Grounding`** (a longer one is a review finding, §8.2.13 N3; §8.2.15 Q1); link evidence rather than retelling earlier packages |
| `### Decisions` | A table `Decision \| Choice \| Why/source`, **at most six rows**. **This is the deliverable.** Resolve every choice that affects correctness now |
| `### Grounding` | The facts of *Grounding the plan*, grouped by decision (`D1`, `D2`, …), one bullet each: `path:symbol`, what it does today and what the change does to it. Facts only: no alternatives, no history and no restated specification. Cite symbols, not line numbers, which drift |
| `### Work items` | A checklist in dependency order, one commit per item: `- [ ] 3. <files and deliverable> (D4); done when <tests> pass`, or, for an item outside the test scope (`SPECIFICATION.md` §8.2.13 N1), done when the code and review say so. Name the files in backticks. After a group of items, a line *Compaction checkpoint: after item N; resume from this plan and `git log`.* |
| `### Verification` | Test file, tier, identifiers, oracle, tolerance source and command, for in-scope tests only (§8.2.13 N1). Every claimed in-scope `VER-`/`VAL-` appears here; an out-of-scope item's done-criterion is "the code and review say so" (N3) |
| `### Out of scope` | Deferrals and their owner |
| `### Open questions` | Author rulings needed before implementation; ask blocking ones before committing |

The plan is an index and execution contract, with no per-item design and no `## Design` heading. A
derivation that is new and load-bearing goes into the specification, which the plan links. If the
word caps and six decisions cannot hold the correctness-critical choices and the facts they rest
on, split the package; never omit a required check or a grounding fact to meet a count.

### The In brief

```markdown
## In brief

At most 250 words, no backticks or identifiers; for a reader who does not code.

**What changes.** What the reader will notice, and why it matters.
**Cost.** Time, money or speed, in plain units.
**What could go wrong.** Each risk, and how it would be noticed.
**Your call.** Each decision the author owns, as a question, with *Recommendation:* and one reason.
```

Review checks every plan from WP44 on against these caps (§8.2.13 N3).

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
3. Open or reuse the branch's PR against `main` without asking, by the lookup and title/body contract
   of `wp-ship` §3 (do not invoke that skill). It is the package's PR: `/wp-implement` reuses it.
   The body's In brief is the plan's, *What this delivers* says the plan is in and implementation
   follows, and *Verification* ticks only the plan's gate, with review pending `/wp-ship`. Then
   write `PR: [#<n>](<url>), branch <head>` under the plan's title, commit it
   (`docs: record WP<n>'s PR`), gate and push as above. If creation is blocked, report the blocker
   and the pushed branch.
4. Report the path, the PR, the close calls, what the grounding pass changed, any spec amendment
   and the open questions. Then stop; implementation is `/wp-implement`, a separate turn.
