# WP6.11 hand-off

## Step

Implement: items 1 to 4 are done and ticked; item 5, the run, is handed back as `RUN`; item 6, the records, is next.

## Done

- `cd0d299` `feat: the switch records, every list of switches derived` (item 1).
- `0dd7ec9` `feat: numerics.log_variables, the log branch's case key` (item 2).
- `eba39c4` `docs: WP6.11 hand-off, implement` (item 3, the checkpoint).
- `40a24a5` `feat: the force split reads the kernel's force densities` (item 4).
- This commit: `docs: WP6.11 hand-off, implement`, ticking item 4.

## Measured

- For the PR's Measured, as the main session gave them: plan, 1 session, 2 sub-agents, 1.1 agent hours, 3 touches;
  claude-fable-5-2 0.18 M out, 30 M cached; claude-opus-5-5 0.01 M out, 2 M cached. Implement, first helper,
  1 session, 1 sub-agent, 0.4 agent hours, 0 touches; claude-opus-5-5 0.06 M out, 15 M cached. Reading of the
  first window: 10,577 words of project text before the first edit; 13,286 tokens at the start, 104,626 at the edit.
- `CaseArtefact(VALIDATED_DEFAULT_CASE).hash`, pinned as `DEFAULT_CASE_HASH`:
  `fddada5f03d5e951e54a95804e19f2006f056412c4b4a7d9ae86d08d9fed071c`, unchanged since `9ca84ad`.
- Item 4: the eight variants' forces move by 2.6 × 10⁻¹⁶ of the larger half at most (the plan's Outcome holds
  each). The item's files (`test_forces.py`, `test_force_routes.py`, `test_kernel.py`, `test_maxwell_sphere.py`):
  47 passed in 14 s (`-n auto`). The new test's five cases: 0.9 s.

## Decided

- `_Integrands` holds the kernel context, with `inputs.solid` set to the blend wherever a solid fraction is given;
  the surface route reads `terms.context.measures`. The private `_domain_force`, `_surface_force` and
  `_dielectric_gradient_residual` lost their `measures` argument; no public signature moved.
- The item-4 script sits uncommitted in `.git/wp6.11/forces.py`, its stored values in `.git/wp6.11/forces.json`.
- Records for item 6, from the first helper: `CHANGELOG.md` (the new key `numerics.log_variables`;
  `physics.models.SWITCHES` removed; `Term`'s `switches` field now a property; `physics.coupled` exports
  `BODY_FORCE`, `DIELECTRIC_FORCE` and `term`), Appendix A's FR-40 row (VER-82), and `docs/design/kernel.md`'s
  switch table, which predates `Variable density` under `flow` and the exclusion's move to the log record.

## Open

None.

## Next

Item 5 ran as the `RUN` this hand-back names. First action: read the log the prompt gives (the run wrote
`.git/wp6.11/run.log`) and check it shows the six guard walks of `tests/tier2/test_guard_numbers.py` and the tests
of `tests/tier2/test_force_convergence.py`, none failed or skipped. If any failed, stop at that failure and fix it
(never a tolerance). If it passed, tick item 5 (`[x]` with no sha: it made no commit) and its run's numbers as an
Outcome in `docs/plans/phase-6/wp6.11-switches-as-data-and-the-forces.md`, then start item 6, the records, in that
plan's list, reading `.claude/skills/np-implement/finish.md` when the last item is done.
