# Re-plan the project

`/np-plan project` plans again the phases after the phase in flight: their order, scope, gates,
estimates and releases. `/np-plan amend <n>` amends the phase in flight, and `/np-plan phase <n>`
breaks a phase into packages. This level decides only what spans phases (§8.2.16 R5).

It has the same two turns as `phase.md`: the ruling round, then the write-up.

## Turn 1 — the ruling round

Commit nothing in this turn.

1. Read these:
   - `docs/plans/current.md`; each row of §8.1; §2.7 and its Versioning NOTE; §3's Release column;
     §8.3; §8.4;
   - `specification/history/index.md`, and a record only where a ruling bears on a later phase;
   - §10's open `OPN-` items and §9's `RSK-` register;
   - the phase plan in flight, its *Open decisions*, and the end-of-phase report of the last closed
     phase;
   - each later phase plan or input note under `docs/plans/`.
2. Versions agree, as `rulings.md` says.
3. Draft the decisions and put them to the author as `rulings.md` says. Each decision names the
   phases it moves, and for each phase its deliverable, gate, estimate and release.

## Turn 2 — the write-up

In one commit, `docs: re-plan the project (§8.2.<k>)`:

- the ruling record, as `rulings.md` says;
- §8.1's rows, §3's Release column, §2.7's Versioning NOTE and §8.3, where the rulings move them;
- each later phase plan or input note that the rulings move. Change the phase in flight only through
  `/np-plan amend`, named as the next step;
- `docs/plans/current.md`: its position, its "not to be re-decided" entries and its In brief, within
  its *Handoff Rules*.

Gate, push and open its PR as `rulings.md`'s *Finishing* says; its body names the phases as planned
again.

Report the paths, the PR, the rulings, the phases as they now are, the open decisions and their
owners, and the next step. Then stop.
