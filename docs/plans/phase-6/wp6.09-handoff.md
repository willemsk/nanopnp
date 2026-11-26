# WP6.09 hand-off

## Step

Implement, first helper: items 1 to 3 done; the compaction checkpoint (item 3) hands back here. Opus 5.5 at high
effort built.

## Done

- `241606f` chore: prototype, the composition and the comparison (item 1), on the local branch
  `prototype/wp6.09-kernel`, forked from `origin/main` at `45b9798`; not pushed (D2: item 6 pushes it)
- `0867e2d` chore: prototype, one expression for the drift and the force density (item 2), same branch
- this note's commit, `docs: WP6.09 hand-off, implement`: the ticks of items 1 to 3 and item 2's Outcome, on the
  package's branch `ccr-d29ea716-fd3bw4`

## Measured

- The comparison at `0867e2d`: ten variants within 10⁻¹², largest 2.1e-16 (residual), 1.2e-16 (Jacobian); the
  plan's item 2 Outcome holds the rest. Run time 22 s.
- The commit hook on the prototype: 182 s and 163 s, both passed.

## Decided

- `_reference_residual_form` and `_reference_flow_residual` keep today's body; `_reference_transport_state` and
  `_reference_flow_state` keep today's state builders, so the reference's stabilisation reads today's written
  drift and force, not the terms'. The comparison therefore checks item 2's drift against today's.
- `StabilisationModel` gained `flow_contributions` (the three flow integrands), which `flow_term` now sums; the
  kernel's stabilisation slots read the integrands by index. `TransportState` gained `drift`, which
  `advective_velocity` returns where set.
- `--slots` compares each slot with today's integral of the same index (`SumOfIntegrals[i]`, built with
  `Integral.MakeBFI()`); it prints the slot names where the counts differ.
- Item 1 found no defect in today's code, so no `REV` row so far.

## Open

None.

## Next

A fresh helper for `/np-implement wp 6.09`, Opus 5.5 at high effort, at item 4. First action: `git checkout
prototype/wp6.09-kernel` (the local branch; if it is missing from the clone, stop with `BLOCKED`: its two commits
exist nowhere else), then write `prototype/three_d.py` as the plan's *Implementation details*, item 4, says, and run
`uv run python prototype/three_d.py`. Commit it on the prototype as `chore: prototype, the 3D trial`, check out
`ccr-d29ea716-fd3bw4`, and record its printed result as item 4's Outcome with the tick. Item 5's three runs are `RUN`
hand-backs whose commands check the prototype out first and the package's branch last.
