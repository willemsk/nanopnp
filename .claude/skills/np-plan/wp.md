# Plan a work package

`/np-plan wp <n>` is step 1 of the implementation workflow. It turns a package of the phase plan
(`/np-plan phase`) into a plan that `/np-implement` can execute without deciding again anything that
matters. The plan is a commit under `docs/plans/`, not a chat message.

## Before writing anything

1. If the package is not in its phase plan, or is listed **Provisional**, it goes through
   `/np-plan amend` first.
2. Read `knowledge/index.md`, then the sections of the files that the package touches. Read
   `.claude/rules/physics-numerics.md` and `.claude/rules/python.md`. The plan must obey both, and a
   path-scoped rule does not load while you write only Markdown.
3. Read `SPECIFICATION.md` §8.1, the sections that the package implements, and its Appendix A rows.
   Collect:
   - the `FR-`/`QR-`/`CON-`/`PHY-`/`NUM-`/`VER-`/`VAL-`/`RSK-` identifiers it discharges;
   - the `IF-` interfaces it satisfies and the `ADR-` decisions that constrain it;
   - each open `OPN-` in this area. Closing one is a spec edit; `## Open questions` is for it.
4. Read the package's scope, phase decisions and verification rows. Follow a dependency link only if
   it constrains this package. If the brief is absent or stale, repair it from the phase and WP
   headings.
5. Survey the code that the package builds on (the core, *Models and executors*): what exists, which
   empty package reserves a slot, which seams take the argument you need.
6. Do not search the web for the model equations or their parameters (`CLAUDE.md`). Check each
   library API that the plan names against its current documentation (Context7).

## Grounding the plan

The plan is for an implementer on Sonnet who has not seen this session. An item marked for a
sub-agent is for the smaller model that executes it (§8.2.16 R11). When the decisions are drafted,
and before you commit, read yourself the code that each decision and work item changes or relies
on. Settle each point the implementer would otherwise guess (§8.2.15 Q1). For each, ask:

- **Where.** Which function, class or constant changes, named `path:symbol`? Is it the seam the
  change belongs in, or a caller of that seam?
- **Does it run.** Trace the call path of the change. Does it run on the default path, or only when
  a caller passes a hook, an option or an extra? A recording on an optional callback records nothing
  for a caller who passes no callback.
- **Shapes.** What does it read and write: types, fields, units, payload keys and file formats? Give
  a new file or record its exact layout.
- **Variants.** Which forms does its input take: supplied or generated, cached before or after the
  change, an extra installed or not, an optional upstream stage present or absent? Name the variant
  that the obvious path misses, and say what happens to it.
- **Rows.** Which registry entries, `modularity-layering.yaml` rows (static or string, with their
  finding) and public names does it add? Which existing guard reads them?
- **Tests.** How does each test get the object it checks: the fixture, the store, the working
  directory, and the commands an existing example already runs? Name an existing helper to reuse
  before you write a new one.

Each answer is a fact, verified at the commit the plan is written on. It goes into `### Grounding`,
or into its decision if it changes the choice. A fact that changes a decision is a decision, and the
decision moves. Then read the plan as its implementer. Can you write each work item without opening a
file that the plan does not name, and without a choice between two behaviours? If not, the plan is
not finished.

## Scope of one work package

One PR, green on tiers 1 and 2 before the next package of its lane starts. If a package cannot be verified by the
end of its own PR, it is two packages. Prefer the split that lets an analytic benchmark localise an
error to one term (§7.1).

## What to write

`docs/plans/wp<n>-<slug>.md`:

| Section | Content |
|---|---|
| Title + status | `# WP<n> — <name>`, then **Status: planned, not started**, the date, and what it inherits |
| Normativity note | One paragraph: the phase plan it belongs to, that `SPECIFICATION.md` governs, that identifiers are pointers |
| `## In brief` | Before the Execution brief; the core's template |
| `## Execution brief` | Current scope, dependencies, requirement pointers, the model and effort of the implementing session, and the subsections below. The plan holds **at most 3,500 words outside its Outcome annotations, and at most 1,500 of them outside `### Grounding` and `### Implementation details`** (a longer plan is a review finding, §8.2.13 N3; §8.2.15 Q1; §8.2.16 R11). Link evidence; do not retell earlier packages |
| `### Decisions` | A table `Decision \| Choice \| Why/source`, **at most six rows**. **This is the deliverable.** Resolve now each choice that affects correctness |
| `### Grounding` | The facts of *Grounding the plan*, grouped by decision (`D1`, `D2`, …), one bullet each: `path:symbol`, what it does today and what the change does to it. Facts only: no alternatives, no history, no restated specification. Cite symbols, not line numbers, which drift |
| `### Implementation details` | Optional, at most 1,000 words: the exact steps, layouts, commands and file formats an item needs when a smaller model executes it, grouped by item. Steps, not design: a choice belongs in *Decisions* |
| `### Work items` | A checklist in dependency order, one commit per item: `- [ ] 3. <files and deliverable> (D4); done when <tests> pass. **Executor:** <main, or a sub-agent type on a model>`. For an item outside the test scope (`SPECIFICATION.md` §8.2.13 N1): done when the code and review say so. Name the files in backticks. After a group of items, a checkpoint item: `- [ ] 5. Compaction checkpoint. **Executor:** main` (§8.2.16 R11) |
| `### Verification` | Test file, tier, identifiers, oracle, tolerance source and command, for in-scope tests only (§8.2.13 N1). Each claimed in-scope `VER-`/`VAL-` is here; the done-criterion of an out-of-scope item is "the code and review say so" (N3) |
| `### Out of scope` | Deferrals and their owner |
| `### Open questions` | Author rulings needed before implementation; ask the blocking ones before you commit |

The plan is an index and an execution contract. It has no per-item design and no `## Design`
heading. A new derivation that carries load goes into the specification, and the plan links it. If
the word caps and six decisions cannot hold the correctness-critical choices and their facts, split
the package. Never omit a required check or a grounding fact to meet a count.

Review checks each plan from WP44 on against these caps (§8.2.13 N3).

### Work items

Leave the boxes unticked; `/np-implement` ticks them. **Each item names its executor** (§8.2.16 R6,
R11): `main`, or a sub-agent type and model, for example `general-purpose` on Haiku.

- A sub-agent takes only an item that is independent and mechanical, and whose checks it can run: a
  sweep, a slice, a rename, a fixed list of edits.
- An item that needs judgement on normative text, physics or numerics stays `main`.
- *Implementation details* covers a Haiku item in full, so that the item chooses nothing.

The plan commits no tests: the implementer writes each test with its item, from the *Verification*
rows. If a decision says *never*, *always* or *every*, its verification row lists each point of
failure, with one assertion each. An oracle looser than its decision is a defect.

### `docs/plans/current.md`

Link the planned package and its live dependencies. Its word target is in its *Handoff Rules*.

## Finishing

1. A necessary spec amendment goes in the same commit, and the plan says so. If the author rules
   while the package is planned, write the ruling as `rulings.md`, beside this file, says.
2. Commit `docs: WP<n> implementation plan`, with the identifiers in the body. Gate and push (the
   core): another session on another machine can work from the branch.
3. Open the PR by the core's *PR contract*. It is the package's PR, and `/np-implement` reuses it.
   The body's In brief is the plan's. *What this delivers* says that the plan is in and the
   implementation follows. *Verification* ticks only the plan's gate, and says that the review waits
   for `/np-ship`.
4. Report the path, the PR, the close calls, what the grounding pass changed, each spec amendment and
   the open questions. Then stop: implementation is `/np-implement`, in a separate turn.
