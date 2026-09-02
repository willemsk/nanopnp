<!--
Delete the sections that do not apply — except "Specification changes", where
"None." is the answer and silence is not.

A work package delivered through /wp-ship fills this in automatically.
-->

## What this delivers

<!-- One paragraph. Then the new or substantially changed modules by path. -->

## Identifiers discharged

<!-- Every FR-/QR-/CON-/PHY-/NUM-/VER-/VAL-/RSK- this PR closes or implements,
     against the test or module that does it. Appendix A traceability is
     mechanical if this table is right. -->

| Identifier | Discharged by |
|---|---|
|  |  |

## Specification changes

<!-- Every amendment and NOTE, with the argument. A tolerance is never slackened
     to accommodate a number: say why the specified *reference* was the wrong
     quantity, or say "None." -->

None.

## Measured

<!-- Numbers, with the configuration that produced them: convergence rates and
     the meshes they were measured on, route-agreement figures, timings and
     DOF counts, minimum damping factor and the rung that needed it, and the
     stabilisation mode every number was measured under. A rate quoted without
     its meshes is not evidence. -->

## Deliberately not done

<!-- What a reader will expect here and not find, what owns it next, and any
     switch left behind a flag with its default. -->

## Verification

- [ ] `uv run ruff check . && uv run ruff format --check . && uv run mypy src/ && uv run pytest` green on this branch
- [ ] Every `VER-`/`VAL-` claimed above has a test named for the requirement, in the tier directory that marks it
- [ ] No test was skipped, `xfail`ed, or had its tolerance loosened to make this pass
- [ ] `uv.lock` regenerated if `pyproject.toml` moved
- [ ] Any switch away from the validated default is opt-in, default off, and recorded in the FR-25 manifest
- [ ] Durable findings written into `.knowledge/`, marked **[tested]** or **[verified]** with their source
- [ ] `docs/plans/` updated — Outcome annotations where a prediction was wrong, and the work-package section of the phase plan

<!-- Tiers 3 and 4 do not run in CI. If either was run locally, say so and give
     the result; if a `slow` benchmark backs a claim above, name it. -->
