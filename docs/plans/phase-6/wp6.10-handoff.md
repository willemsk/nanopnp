# WP6.10 hand-off

## Step

Implement: items 4 and 5 done; item 6, the thirteen walks, is the `RUN` this note hands back. Item 7 is next.

## Done

- `44d2dd8` feat: the readers read the terms' one statement (WP6.10 item 4)
- `b8ffdf7` test: the term modules are recorded and reach no backend (WP6.10 item 5), with item 4's tick
- this note's commit, `docs: WP6.10 hand-off, implement`: item 5 ticked

PR #227's body still describes the plan alone; item 7 brings it to the tree (REST, `gh api`: the GitHub MCP server
fails to connect).

## Measured

- Tier 2 at `c435a3c2`, the whole `-m tier2` selection: 220 passed in 4,264 s, the 23 `slow` tests most of it
  (`test_num07_weight_order_on_example_05` 3,974 s, the same on `2ba10ab9`).
- `tests/tier2/test_current_routes.py` with `tests/tier1/test_solution_state.py` at item 4's tree: 39 passed, 29 s.
- `tests/tier1/test_kernel.py`: 12 passed, 21 s; its finite assembly under PHY-23 and `reference` on the 1.5 nm
  cylinder takes 3.4 s.
- `test_backend_guard.py` with `test_layering.py`: 36 passed, 51 s.

## Decided

- `PecletDiagnostic.expression` defaults to `numerics/gates.py:PECLET_EXPRESSION`, today's string;
  `solve/continuation.py:_report_peclet` passes `"||b_i|| h_K / (2 D_i), b_i = " + kernel.wind_text(...)`, since
  `numerics` may not import `physics`.
- `validation/modularity.py` gains `accepted_term_modules` and `module_references`; VER-65's two tests read them.
- The plan's item 4 Outcome records the rest (NUM-14's bullet reworded beside its added sentence).
- For a Tier 2 check use `-m "tier2 and not slow"`, and hand back `RUN` for anything over about 4 minutes.

## Open

None put to the author. REV-302 (PHY-23 with a stabilised mode assembles fifty times slower) stays open for the
ship's report.

## Next

First read `.git/wp6.10/walks.log`. Item 6 is done when its `number stability` section lists thirteen walks and the
log shows no failure and no skip; a failed or skipped VER-62 walk is `BLOCKED`, and a walk drifting beyond 10⁻⁸ is
investigated under D7, never re-recorded to fit. Then tick item 6 (`[x]` with no sha, as it commits nothing) with an
Outcome listing each walk's largest drift, and start item 7, the records, at
`specification/05-software-design/04-component-design.md` (the NOTEs of §5.4.1 and §5.4.4), reading the plan's
item 7 and `.claude/skills/np-implement/finish.md` first. `docs/design/kernel.md` lines 72, 87 and 169 still name
`species_flux`.
