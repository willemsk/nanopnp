# WP6.09 hand-off

## Step

Implement, second helper: item 4 done; item 5's three runs, and item 6's push attempt, handed back as one `RUN`.
Opus 5.5 at high effort built.

## Done

- `1b5f5e3` chore: prototype, the 3D trial (item 4), on the local branch `prototype/wp6.09-kernel`, above
  `0867e2d` and `241606f`; not pushed (D2: item 6 pushes it)
- this note's commit, `docs: WP6.09 hand-off, implement`: item 4's tick and Outcome, on `ccr-d29ea716-fd3bw4`

## Measured

- `prototype/three_d.py`: 7 s wall; the plan's item 4 Outcome holds its numbers.
- The commit hook on the prototype: passed (one ruff retry for line length).

## Decided

- Item 5's three runs and item 6's single push attempt go in one `RUN`, in the plan's order, each with its own log
  under `/home/user/nanopnp/.git/`: `wp609-walks.log`, `wp609-control.log`, `wp609-gate.log`, `wp609-push.log`.
  The push follows run 3 in the same command, so no land replaces the prototype's stamp first. Each log ends
  `exit <status>`; the push log opens with the sha pushed.
- The 3D VER-17 mesh is the fluid alone (lumen and two half-ball reservoirs); the membrane is not meshed. The page
  says so beside the count.

## Open

None.

## Next

A fresh helper for `/np-implement wp 6.09`, Opus 5.5 at high effort, at item 5. First action: read the four logs
under `/home/user/nanopnp/.git/` (above), with the branch `ccr-d29ea716-fd3bw4` checked out.

- Walks: thirteen walks listed under `number stability`, no failure, no skip; example 01 within 10⁻⁸, else
  `BLOCKED` with the log (D5 b). Other misses are reported, never tuned.
- Control: it must fail on its stored numbers; a pass is `BLOCKED` (D5 d).
- Gate: ends `exit 0`; record its counts and time.
- Push: `exit 0` and `git ls-remote origin refs/heads/prototype/wp6.09-kernel` printing the logged sha ticks
  item 6. If `origin` refused it, run item 6's `git bundle create` from the plan's *Implementation details* and
  hand back `ASK` for the author's push; if the hook refused it for want of a stamp, item 6 says what follows.

Then write item 5's Outcome (each walk's largest drift and mode, the control's drift, the gate's counts and time,
the prototype's sha `1b5f5e3`) and tick items 5 and 6, then item 7's checkpoint.
