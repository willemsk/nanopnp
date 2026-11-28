# WP6.11 hand-off

## Step

Plan, first helper of two: the draft is committed and three decisions are with the author. No PR is open.

## Done

- `docs: WP6.11 plan draft`, with this note: `docs/plans/phase-6/wp6.11-switches-as-data-and-the-forces.md`, every
  section drafted on the recommended answers.

## Measured

- The plan: 3,153 words; 1,651 outside Grounding and Implementation details (cap 1,650); 750 in Implementation
  details; 271 in the In brief.
- The forces through the kernel's densities against today's `post/forces.py`, on six variants: at most
  6.4 × 10⁻¹⁶ relative.
- `tests/tier2/test_force_routes.py` with `tests/tier1/test_forces.py` and `test_manifest.py`: 55 passed in 19 s.

## Decided

- The planning model: Fable 5.2 at high (the author, at the carry's start).
- No clause is amended in the plan's commit: each amendment is written in the item that builds it, as WP6.10 did.

## Open

Put to the author in the `ASK` hand-back, each with its recommendation first:

1. "Where in a case file should the new setting live that makes a run solve for the logarithm of each ion
   concentration? Today no case file can turn this on: only a script can, and the run's record does not name it.
   You ruled that it becomes a case setting (BL7) and left its place to this plan. Both places behave the same;
   they differ in what the setting is filed as: a way of computing, or a part of the physical model." Options:
   "With the numerical settings (Recommended)", "With the physics switches". It feeds D2.
2. "Should a run on the logarithm be allowed with the stepwise start (the continuation ladder, the default way a
   hard case is reached)? Today the ladder fixes the model's on-off settings itself, and a case that sets one
   differently beside it is refused and told to run as a single direct solve. The stored reference run on the
   logarithm is such a single solve. Neither the specification nor the phase plan says what the new setting does
   beside the ladder. The second option is the more general one: it lets the logarithm reach cases that a single
   solve cannot." Options: "Refused beside the ladder (Recommended)", "The ladder carries it". It feeds D5.
3. "Should the workbench show the new setting? Today its Equations tool lists the model's four on-off settings
   from a list written in the code. This package reads that list from the records, so a fifth appears unless it
   is held back. The phase plan says only that the kernel changes no screen, and the workbench is rebuilt in
   Phase 8." Options: "Shown with the other switches (Recommended)", "Case file only for now". It feeds D7.

## Next

1. Read `helper.md`, `np-plan/SKILL.md`, the core, `wp.md`, `rulings.md` and `review.md`, then the draft.
2. Record the three answers as `rulings.md` says: a new record
   `specification/history/63-wp611s-plan-switches-as-data-and-the-forces.md` (§8.2.63, BM1 to BM3), its line in
   `specification/history/index.md`, and a line a ruling in `holds-now.yaml`.
3. In the draft, set D2, D5 and D7 to "Ruled by the author" with the answer. Where an answer is not the
   recommended one, change what follows from it in every section; the ladder carrying the branch adds a stored
   walk and widens the package, so check the caps and BL2. Set the status to **planned, not started**, the In
   brief's *Your call* to the approval alone and *Open questions* to "None".
4. Update `docs/plans/current.md` and the Phase 6 plan's open decision 20.
5. Run *The self-check*, then `uv run .claude/scripts/decisions.py` and
   `uv run .claude/scripts/index_records.py`; commit `docs: WP6.11 implementation plan`; open the PR
   `WP6.11 — Switches as data and the forces` if `origin/<head>` exists; hand back `DONE`, `land: yes`.
