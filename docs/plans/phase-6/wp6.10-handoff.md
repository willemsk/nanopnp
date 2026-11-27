# WP6.10 hand-off

## Step

Implement: items 1 and 2 done, item 3 (the compaction checkpoint) ticked in this note's commit. Item 4 is next.

## Done

- `e482296` feat: the kernel's records, operators and geometry (WP6.10 item 1)
- `750c63f` feat: the coupled residual composed from registered terms (WP6.10 item 2)
- this note's commit, `docs: WP6.10 hand-off, implement`: items 2 and 3 ticked

PR #227, `feat: WP6.10 — the composition`, opened by REST (`gh api`); the GitHub MCP server failed to connect. Its
body still describes the plan alone; item 7 brings it to the tree.

## Measured

- The stored operator: `.git/wp6.10/stored.npz`, written from `2ba10ab9` by `.git/wp6.10/compare_operators.py
  --write`; `--against <file>` compares (about 110 s, the two PHY-23 stabilised variants taking 100 s of it).
  Both are uncommitted, in the git dir.
- The comparison's numbers and the PHY-23 timing are in the plan's item 2 Outcome and REV-302.
- Tier 1 green at `750c63f` (the commit hook). Tier 2 at the same tree is the `RUN` this note hands back.

## Decided

- Item 2 rewrote `post/qoi.py:stabilisation_currents` on the kernel (`model.context`, `TRANSPORT_SLOTS`,
  `kernel.integrand`, `Measures.integrate`), since it read the deleted `transport_states` and `indicator_term`.
  Item 4 still owes `indicator_currents` (it calls `species_flux`), `cell_peclet`'s new signature with the solid
  fraction, `_report_peclet`, `PecletDiagnostic.expression`, the two NOTEs and VER-81's row.
- `CoupledModel.context` binds `terms=self.terms_in_force()`, so a reader calls `stabilisation.transport_state`
  on it directly. `cell_peclet(state, wall_distance_nm)` already reads the whole wind through it, decrement
  included; item 4 adds the solid fraction.
- `Context.field` is the slot's test field, bound with its species; the flux closing and the stabilisation read
  `context.tests[context.require_field()]`.
- `test_stabilisation.py`'s `_built` builds a hand context with Nernst–Planck, Steric flux and Advection;
  `test_num14_advective_velocity_is_the_flux_bracket_of_species_flux` still calls `species_flux`, so item 4
  carries it to the flux slot's contributions, as `test_nernst_planck.py`'s `species_flux` tests.

## Open

None put to the author. REV-302 (PHY-23 with a stabilised mode assembles fifty times slower) is open for the
ship's report. A parallel Tier 2 run at `750c63f` had passed two thirds with no failure when it was stopped;
the main session runs it whole (`RUN`, its log `.git/wp6.10/tier2.log`). Already green before the stop:
`test_stabilised_mode.py`, `test_current_routes.py`, `test_ladder.py`, `test_electroosmosis.py` (34 passed).

## Next

First read `.git/wp6.10/tier2.log`. A failure there is item 2's: fix it, with its test's assertion and tolerance
kept, and commit before item 4. Then a fresh `np-builder` for `/np-implement wp 6.10`: read `docs/plans/phase-6/wp6.10-the-composition.md`, then start
item 4 at `src/nanopnp/post/qoi.py:indicator_currents`, which becomes the `flux` slot's integrand closed with `ψ`
(the plan's *Item 4, the readers*); then delete `nernst_planck.py:species_flux` and its `NGSOLVE_OPERATORS`
import, and run

```bash
uv run pytest tests/tier1/test_kernel.py tests/tier1/test_nernst_planck.py tests/tier1/test_stabilisation.py tests/tier2/test_current_routes.py -q
```

Item 6 is a `RUN` hand-back.
