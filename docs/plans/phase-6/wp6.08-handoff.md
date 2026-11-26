# WP6.08 hand-off

## Step

Implement, first helper: item 1 done and committed; item 2's run handed back as `RUN`. Opus 5.5 at high effort built.

## Done

- `cdb67aa` test: the guard numbers of six settings off the validated default (item 1: the guard file, the six
  records folded into `number_stability.json`, VER-80's row, §7.6's nightly NOTE, Appendix A, `CHANGELOG.md`)
- this note's commit, `docs: WP6.08 hand-off, implement`: item 1's tick, the plan's status line, the plans index

## Measured

- Recorded under the gate's SIMD cap, one thread, `CI` unset: all six on mesh `546c34f4fb4b…` and
  `linux-x86_64/X86_V3`. The fold added 118 lines to `number_stability.json` and removed none.
- Seconds a walk, the record's calls: `guard-dielectric` 113 (its call), `guard-reference` 68.4, `guard-supg` 33.2,
  `guard-log` 25.2, `guard-constant-density` 8.6, `guard-no-inertia` 8.3; the second call 144 s in all.
- Against the folded file, `-k "density or inertia"`: both walks same-mesh, largest relative drift 0.000e+00;
  `tests/tier1/test_number_stability_file.py` 7 passed.

## Decided

- The skip message reads `the guard numbers are held in linux-x86_64/X86_V3 alone, not <environment>`.
- No *Grounding* fact was found untrue; the plan's text is unchanged but for the tick and the status line.

## Open

None.

## Next

The main session has run item 2's command (the plan's *Implementation details*, *Item 2, the run*) and gives its
log's path, `<git dir>/wp608-walks.log`. A fresh `np-builder` for `/np-implement wp 6.08`:

1. Read the log. Done when it shows no failure and no skip and its `number stability on linux-x86_64/X86_V3`
   section lists thirteen walks. A failed or skipped VER-62 walk: hand back `BLOCKED`. A guard walk beyond 10⁻⁸:
   investigate, never re-record.
2. Item 2 is the checkpoint: read `.claude/skills/np-implement/finish.md`'s compaction checkpoint, tick item 2
   (`[x]` with no sha of its own, as the item makes no commit; name the log's numbers in its Outcome under item 3).
3. Item 3, the records, in `docs/plans/phase-6/wp6.08-the-guard-numbers.md`'s *Implementation details*: the
   knowledge section in `knowledge/06-numerics-fem/16-tier-2-test-evidence-ladder-walks-block.md`,
   `specification/history/holds-now.yaml` (BI1, BI2, BC3), the plan's Outcome with the thirteen drifts, the Phase 6
   plan's entry and `docs/plans/current.md`; then `finish.md`'s *Finishing*, PR #221's body to the tree.
