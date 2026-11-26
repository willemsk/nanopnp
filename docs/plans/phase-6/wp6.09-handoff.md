# WP6.09 hand-off

## Step

Implement, third helper: items 5 and 6 ticked from the main session's `RUN`, and item 7's compaction checkpoint ticked.
Opus 5.5 at high effort built.

## Done

- this note's commit, `docs: WP6.09 hand-off, implement`, on `ccr-d29ea716-fd3bw4`: item 5's and item 6's Outcomes,
  the ticks of items 5 to 7, the plan's status line
- the prototype `1b5f5e3` is on `origin/prototype/wp6.09-kernel` (`git ls-remote` checked)

## Measured

- Run 1, thirteen walks: 43 passed, 426 s with `-n auto`; example 01 8.7 × 10⁻¹⁴. The plan's item 5 Outcome holds
  each walk.
- Run 2, the control: exit 1, four setup errors in 10.9 s; the run's currents drift 2.5 × 10⁻³ and 4.0 × 10⁻³ from
  the stored total current.
- Run 3, the push gate: passed, 474 s, tree `c0171d4`.
- Logs: `/home/user/nanopnp/.git/wp609-{walks,control,gate,push}.log`.

## Decided

- The control's refusal counts as D5 (d)'s miss. `nanopnp run` exits 4 at the NUM-24/NUM-25 route check
  (6.5 × 10⁻³ against 10⁻³) before the golden is read; the test fails, only the dropped term causes it, and the
  refusal shows that the solve reads the composition (the reaction flux comes from the composed form; the indicator
  writes the steric flux from the state). The page's *what the prototype showed* says so, and notes that the route
  check is itself a guard against a term the form drops but the post-processing keeps.

## Open

None.

## Next

A fresh helper for `/np-implement wp 6.09`, Opus 5.5 at high effort, at item 8, on `ccr-d29ea716-fd3bw4`. First
action: read the plan `docs/plans/phase-6/wp6.09-the-kernels-design.md` whole (D7, *Implementation details* item 8,
and the Outcomes of items 2, 4 to 6, which hold every number the page cites), then `docs/design/workbench.md` and
`mkdocs.yml`'s Project section for the page's form. The prototype's code is read with
`git show 1b5f5e3:src/nanopnp/physics/kernel.py` (and `models.py`, `stabilisation.py`, `prototype/`), never by
checking the branch out. Write `docs/design/kernel.md`, add its line under `Workbench design` in `mkdocs.yml`, and
run `uv run just docs` before the commit.
