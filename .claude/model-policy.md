# Sub-agent model policy

Which model a delegated task runs on. Referenced from `CLAUDE.md`; it applies to *every* `Agent`
call in this repository, and to the session implementing a plan whatever model it runs on (*Who
implements a plan*). The skills cite it where they delegate, so there is no list of them here to
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

The policy binds **whoever implements**, not only the `Agent` calls a Claude session makes. A
session may run on another model, Claude or not, through another harness, with the same skills and
gate. The gate cannot tell a plausible wrong answer from a right one, and that is exactly the
failure the rule above exists for.

- `/wp-plan` marks every work item `[Opus]` or `[any]`, and an `[Opus]` item says in one clause why
  (`.claude/skills/wp-plan/SKILL.md`).
- An `[Opus]` item is done only in an Opus session. A session on any other model implements the
  `[any]` items in plan order up to the first `[Opus]` item, commits and ticks each one, and then
  **stops** there, without skipping ahead to later `[any]` items: it reports the `[Opus]` items left, and it neither implements them, drafts them
  for later, nor opens the PR. The next Opus session resumes from the first unticked item
  (`.claude/skills/wp-implement/SKILL.md`).
- A session that cannot tell which model it runs on treats itself as not Opus.

WP39 shows why this is a rule and not advice. Its plan said in a sentence that D3, D7, D8 and D11
"run on Opus"; the implementing session was another model, nothing enforced the sentence, and all
three defects its review then found were in D11, each having passed the gate.

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
