# WP6.08 hand-off

## Step

Plan, second helper of two: done. The plan is written, checked by `np-plan/review.md`'s self-check and committed; the
author's approval is next, then the build. Fable 5.2 at high effort planned.

## Done

- `3dfbe6f` docs: WP6.08 plan draft (the first helper)
- `444733a` chore: duplicates.py skips a helper's hand-off note
- `a4d492e` docs: WP6.08 implementation plan: the plan, record 59 (BI1, BI2), REV-298, the Phase 6 plan and its
  record, `current.md`, the input note, the decisions page and the plans index
- this note's commit, `docs: WP6.08 hand-off, plan`

## Measured

- 3,211 words in the plan: 985 in `### Grounding`, 727 in `### Implementation details`, 1,499 outside both; the caps
  are 3,850, 1,100 and 1,650. The In brief has 275 words, its limit.
- 700 words in `docs/plans/current.md`, its limit.
- Run again by this helper under the gate's SIMD cap, one thread, on mesh `546c34f4…`: `supg` 33 s, `reference` 69 s,
  the log branch 25 s. The stabilisation currents are −3.001e-13 A (Cl⁻) and −7.009e-13 A (Na⁺) under `supg`, and
  −3.002e-13 A and −7.013e-13 A under `reference`.
- `duplicates.py` exited 1 with the note beside the plan, and exits 0 with the fix.

## Decided

- The author ruled D1 "All six (Recommended)" and D2 "Linux only (Recommended)": BI1 and BI2 of §8.2.59.
- D7 changed from the draft: the numbers are recorded first, and one `RUN` after item 1's commit takes VER-62's seven
  walks and the six guard walks together. The package changes no `src/`, so the one run shows that VER-62 passes on
  the tree and repeats the guard numbers. The draft had the seven walks run before the record.
- VER-80's row, §7.6's NOTE, Appendix A's line and `CHANGELOG.md` go with item 1, not with the plan's commit: no test
  reads §7.3's rows, and the clause would name a file that holds no guard walk yet.
- A walk needs a workspace of its own: the solve stage refuses a folder that holds an earlier run's files.
- CI's `docs` job runs `duplicates.py`, which counted the hand-off note as a second WP6.08 plan and would have failed
  the package's pull request until the ship deletes the note. Fixed as a small finding (§8.2.58 BH1), as REV-293 was
  for `index_records.py`; no row.
- The Phase 6 plan's WP6.07 entry and status line said "awaiting its merge"; PR 219 is merged and `v0.7.0-alpha.7`
  is published, so both are corrected.
- `docs/plans/current.md`'s cost of the rest of the phase is the sum of the Phase 6 plan's entries after WP6.08: 33
  sessions, 19 to 36 agent hours, 51 touches.

## Open

None. The plan's `### Open questions` is empty.

## Next

After the author approves the plan, a fresh `np-builder` for `/np-implement wp 6.08`:

1. Read `docs/plans/phase-6/wp6.08-the-guard-numbers.md`; start at work item 1, with its *Implementation details*.
2. Write `tests/tier2/test_guard_numbers.py`, record under the cap in two calls, fold with
   `uv run python tests/tier2/data/merge_number_stability.py <dir>`, write the clauses, commit.
3. Hand back `RUN` with item 2's command, whose log is `<git dir>/wp608-walks.log`.

The package's pull request is #221, opened by this helper on `claude/zealous-planck-aio2ty` with the plan's In brief;
the build reuses it and brings its body to the tree's state (`.claude/workflow/finish.md`, *The PR contract*).
