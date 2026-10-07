# Sub-agent model policy

Which model a delegated task runs on. Referenced from `CLAUDE.md`; it applies to *every* `Agent`
call in this repository, and to whoever implements a plan (*Who implements a plan*). The skills cite it where they delegate, so there is no list of them here to
keep in step.

## The rule

**The failure mode decides the model, not the size of the task.**

- If getting it wrong produces a **plausible wrong answer** — a number that looks right, a sign that
  flips a trapping landscape, a tolerance that passes for the wrong reason — it runs on **Opus**.
  This project's whole verification strategy exists because plausible wrong answers are the
  characteristic failure of this model (QR-12, RSK-03, RSK-04). A cheaper model that is right 90 %
  of the time is not 90 % as useful here; it is a source of results nobody can trust.
- If the failure mode is **loud** — an import error, a lint diagnostic, a type error, a test that
  fails at the assertion — it runs on **Sonnet**. The gate catches it, the cost of a wrong attempt
  is one retry, and there is no way for a mistake to survive into a recorded number.

Length, file count and token budget do not enter into it. Rewriting three hundred lines of
docstrings is a Sonnet task; deciding one sign in one weak form is an Opus task.

## Opus

- Deriving or amending a weak form, a scaling, a QoI extraction route, or any of §4 / §6 of the
  specification.
- Writing or amending `SPECIFICATION.md`, including every NOTE and every argued tolerance.
- Authoring a work-package or phase plan (`docs/plans/`) — the decisions table is the deliverable.
- Diagnosing a failing Tier 2 benchmark, a convergence-rate loss, a Newton divergence, or a
  disagreement between two extraction routes.
- Any change to `physics/`, `solve/`, `post/`, `materials/forms.py`, or the correction YAML.
- Reviewing a diff for physics correctness directly, and confirming or reverting every finding the
  `wp-ship` §4 review pass raises — that confirmation, not the pass itself, is what keeps a proposed
  fix from becoming a plausible wrong one.
- Judging whether a `.knowledge/` finding is `[tested]`, `[verified]` or neither.

## Sonnet

- `Explore` searches: where is X defined, which files reference Y, does this seam already exist.
- Mechanical refactors with the target spelled out: renames, import moves, `Path` for `os.path`,
  deferred-import compliance, British-spelling sweeps.
- Docstrings, type annotations, and `mypy --strict` fixes that do not change behaviour.
- Test scaffolding from a plan that already states the tolerances, the tier and the assertions.
- Running the gate, the tiers or a benchmark and summarising the output.
- `uv.lock` refreshes, CI YAML edits, packaging and devcontainer chores.
- Reading a long log and reporting the failing line.

## Haiku

Only for bulk mechanical retrieval where the result is checked immediately — listing files,
counting matches. Rarely worth the spawn.

## Who implements a plan

The policy binds whoever implements a plan, on any model or harness, not only `Agent` calls: the
gate cannot tell a plausible wrong answer from a right one.

- `/wp-plan` marks each work item `[Opus]` or `[any]`.
- Any session may do an `[any]` item. A session that is not Opus may also do an `[Opus]` item, at
  extra effort and on the record:
  1. Before writing the implementation, it runs the item's planned tests (strict `xfail`, written
     on Opus at plan time) and confirms each fails. If the item has none, it first writes tests
     from the plan's decision and verification rows, with exact assertions, as strict `xfail`
     markers in a commit of their own (`test:`), and only then implements.
  2. The item's commit body states the decision it implements, and every sign, unit, tolerance and
     route it relied on, citing the plan's decision row and the specification clause.
  3. It ticks the item `[x] <short sha> non-Opus`, and the PR body lists every such item, and any
     tests it wrote, under **Done outside Opus**.
- `/wp-ship`'s Opus review confirms each **Done outside Opus** item (and the tests, where the
  session wrote them) against its decision row before the package counts as reviewed.
- A session unsure of its model is not Opus.

## Applying it

Pass the model explicitly and say why in one clause, so the choice is visible and the user can
redirect it:

```
Agent(subagent_type="Explore", model="sonnet",
      description="Find the wall-distance seams", prompt="…")
```

> Delegating the contour-extraction survey to Sonnet — read-only search, loud failure mode.

The user may override at any time ("do that one on Opus"), and an override stands for the rest of
the session unless they say otherwise. When a task straddles the boundary — a mechanical edit
*inside* `physics/`, say — take Opus: the asymmetry of the two errors is not close.

## Cost discipline

A sub-agent starts cold and re-derives context this session already has. Delegate when the work is
genuinely separable (a survey, an independent implementation, a long test run), not to parallelise
thinking. Two or three at once is a lot; the orchestrator stays on Opus and keeps every physics
decision itself.
