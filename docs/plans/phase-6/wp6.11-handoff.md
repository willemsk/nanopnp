# WP6.11 hand-off

## Step

Implement: items 1 to 4 are done and ticked; item 5, the run, is handed back as `RUN` a second time, the guard
walks alone under the gate's SIMD cap; item 6, the records, is next.

## Done

- `cd0d299` `feat: the switch records, every list of switches derived` (item 1).
- `0dd7ec9` `feat: numerics.log_variables, the log branch's case key` (item 2).
- `eba39c4` `docs: WP6.11 hand-off, implement` (item 3, the checkpoint).
- `40a24a5` `feat: the force split reads the kernel's force densities` (item 4).
- `c6fd6b4` `docs: WP6.11 hand-off, implement`, ticking item 4.
- This commit: `docs: WP6.11 hand-off, implement`, the plan's run command given the gate's cap, and the first
  run's Outcome.

## Measured

- For the PR's Measured, as the main session gave them: plan, 1 session, 2 sub-agents, 1.1 agent hours, 3 touches;
  claude-fable-5-2 0.18 M out, 30 M cached; claude-opus-5-5 0.01 M out, 2 M cached. Implement, first helper,
  1 session, 1 sub-agent, 0.4 agent hours, 0 touches; claude-opus-5-5 0.06 M out, 15 M cached. Reading of the
  first window: 10,577 words of project text before the first edit; 13,286 tokens at the start, 104,626 at the edit.
- `CaseArtefact(VALIDATED_DEFAULT_CASE).hash`, pinned as `DEFAULT_CASE_HASH`:
  `fddada5f03d5e951e54a95804e19f2006f056412c4b4a7d9ae86d08d9fed071c`, unchanged since `9ca84ad`.
- Item 4: the eight variants' forces move by 2.6 × 10⁻¹⁶ of the larger half at most.
- Item 5, first run, on `2d7936d`, `linux-x86_64/AVX512_SPR`, no cap: `tests/tier2/test_force_convergence.py`
  5 passed (the `slow` corrected case among them); the six guard walks skipped; 103.76 s; `exit 0`.

## Decided

- The first run lacked `NPY_DISABLE_CPU_FEATURES`, which the gate and CI set, so the host was not the reference
  environment and `test_guard_numbers.py` skipped each walk (BI2). The plan's command now carries the cap and the
  thread pins. The force tests passed in the first run and are not run again.
- Records for item 6, from the first helper: `CHANGELOG.md` (the new key `numerics.log_variables`;
  `physics.models.SWITCHES` removed; `Term`'s `switches` field now a property; `physics.coupled` exports
  `BODY_FORCE`, `DIELECTRIC_FORCE` and `term`), Appendix A's FR-40 row (VER-82), and `docs/design/kernel.md`'s
  switch table, which predates `Variable density` under `flow` and the exclusion's move to the log record.
- The item-4 script sits uncommitted in `.git/wp6.11/forces.py`, its stored values in `.git/wp6.11/forces.json`.

## Open

None.

## Next

Read the log the prompt gives (`.git/wp6.11/run-guard.log`). It must show the six guard walks of
`tests/tier2/test_guard_numbers.py` passed, none skipped or failed. If one skipped, check the environment it names
against `linux-x86_64/X86_V3` and stop with `BLOCKED`. If one failed, stop at that failure and fix it (never a
tolerance; a moved number goes by VER-62's ruling for WP6.10 to WP6.12). If all passed, tick item 5 (`[x]` with no
sha) in `docs/plans/phase-6/wp6.11-switches-as-data-and-the-forces.md`, add the second run's numbers to its
Outcome, then start item 6, the records, reading `.claude/skills/np-implement/finish.md` when the last item is done.
