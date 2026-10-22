# Re-plan the project

`/np-plan project` re-plans the phases ahead of the one in flight: their order, scope, gates,
estimates and releases. A phase in flight is amended by `/np-plan amend <n>`, and a phase is broken
into packages by `/np-plan phase <n>`; this level decides only what spans phases (§8.2.16 R5).

The same two turns apply as for `phase.md`: the ruling round, then the write-up.

## Turn 1 — the ruling round

Nothing is committed in this turn.

1. Read `docs/plans/current.md`; §8.1, every row; §2.7 and its Versioning NOTE; §3's Release
   column; §8.3; §8.4; `specification/history/index.md`, reading a record only where a ruling bears
   on a later phase; §10's open `OPN-` items and §9's `RSK-` register; the phase plan in flight, its
   *Open decisions* and the end-of-phase report of the last closed phase; and every later phase plan
   or input note under `docs/plans/`.
2. Versions agree, as `rulings.md` says.
3. Draft the decisions and put them to the author as `rulings.md` says. Each names the phases it
   moves, and for each phase its deliverable, gate, estimate and release.

## Turn 2 — the write-up

In one commit, `docs: re-plan the project (§8.2.<k>)`:

- the ruling record, as `rulings.md` says;
- §8.1's rows, §3's Release column, §2.7's Versioning NOTE and §8.3, where the rulings move them;
- every later phase plan or input note the rulings move; the phase in flight only through
  `/np-plan amend`, named as the next step;
- `docs/plans/current.md`: its position, its "not to be re-decided" entries and its In brief,
  within its *Handoff Rules*.

Gate, push and open its PR as `rulings.md`'s *Finishing* says, its body naming the phases as
re-planned.

Report the paths, the PR, the rulings, the phases as they now stand, the open decisions and owners,
and the next step. Then stop.
