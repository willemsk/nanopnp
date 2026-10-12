# Sub-agent model policy

Which model a delegated task runs on, for *every* `Agent` call here and for whoever implements a
plan (*Who implements a plan*).

## The rule

**The failure mode decides the model, not the size of the task.** A mistake that yields a
**plausible wrong answer** (a number that looks right, a flipped sign, a tolerance that passes for
the wrong reason) runs on **Opus** (QR-12, RSK-03). A **loud** failure (an import error, a lint diagnostic, a
failing assertion) runs on **Sonnet**: the gate catches it.

- **Opus:** weak forms, scalings and QoI routes (§4, §6); `SPECIFICATION.md`; plans; diagnosing a
  Tier 2 failure or a disagreement between routes; any change to `physics/`, `solve/`, `post/`,
  `materials/forms.py` or the correction YAML; confirming or reverting every `wp-ship` §4 finding;
  judging a `.knowledge/` finding `[tested]` or `[verified]`.
- **Sonnet:** `Explore` searches; mechanical refactors with the target spelled out; behaviour-free
  docstrings and annotations; test scaffolding from stated assertions; running the gate;
  `uv.lock`, CI YAML and packaging; reading a long log.
- **Haiku:** bulk mechanical retrieval only, as the `surveyor`: paths and counts. **Retrieval is
  checked:** the caller reads the returned line range itself before relying on it. Clauses by
  identifier come from `.claude/scripts/clause.py`, not an agent.

When a task straddles the boundary, take Opus.

## Enforcement

`.claude/agents/` fixes the model, tools and effort of `gate-runner` (Sonnet), `surveyor` (Haiku),
`ci-log-classifier` (Sonnet) and `physics-reviewer` (Opus). A call's `model` overrides its file's,
so `.claude/hooks/agent-guard.sh`, a PreToolUse hook on `Agent`, refuses a roster agent called with
another model and any other agent called without an explicit `model`. Name the agent when delegating;
the user may override.

## Who implements a plan

The policy binds whoever implements a plan, on any model: the gate cannot tell a plausible wrong
answer from a right one.

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

Delegate only separable work, not to parallelise thinking. The orchestrator keeps every physics
decision.
