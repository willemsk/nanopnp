# Re-plan the project

`/np-plan project` plans again the phases after the phase in flight: their order, scope, gates,
estimates and releases. `/np-plan amend <n>` amends the phase in flight. `/np-plan phase <n>` breaks a
phase into packages. This level decides only what spans phases (§8.2.16 R5), unless a ruling opens
more (*A rescoping round*).

It has the same two turns as `phase.md`: the ruling round, then the write-up.

## Turn 1 — the ruling round

Commit nothing in this turn.

1. Read these:
   - `docs/plans/current.md`; each row of §8.1; §2.7 and its Versioning NOTE; §3's Release column;
     §8.3; §8.4;
   - `specification/history/holds-now.yaml`, with the history index for the records, and a record
     only where a ruling bears on a later phase;
   - §10's open `OPN-` items and §9's `RSK-` register;
   - the phase plan in flight, its *Open decisions*, and the end-of-phase report of the last closed
     phase;
   - each later phase plan or input note under `docs/plans/`.
2. Versions agree, as `rulings.md` says.
3. Draft the decisions and put them to the author as `rulings.md` says. Each decision names the
   phases it moves, and for each phase its deliverable, gate, estimate and release.

## A rescoping round

A round is a rescoping round when a ruling opens the project's scope, as §8.2.50 AZ7 does. It keeps
the two turns, and Turn 1 changes in three ways.

1. **It also reads** §3's requirements in full; each tool and phase of §8.1; OPN-08; the Outcome of
   the last cleanup package; `docs/project/architecture-survey.md`; and the measured cost of the last
   closed phase, in its end-of-phase report.
2. **It may open** any requirement, tool or phase, and each ruling that the opening ruling names. A
   decision that opens one says what is kept, cut or added, and why.
3. **The phase in flight** is changed only by naming `/np-plan amend <n>` as the next step: the round
   rules what is left of the phase, and the amendment plans it.

Turn 2 then also writes §3's requirements and §8.1's tools where the rulings move them.

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
owners, and the next step. Then pause as `SKILL.md`'s *The pause* says.
