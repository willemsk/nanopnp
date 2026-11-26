# WP6.08 hand-off

## Step

Implement, second helper: all three items done and committed, PR #221's body brought to the tree. The build is
finished; the ship is next. Opus 5.5 at high effort built.

## Done

- `cdb67aa` test: the guard numbers of six settings off the validated default (item 1)
- `8cce00f` docs: WP6.08 hand-off, implement (first helper's note)
- `2aa21d8` docs: WP6.08 item 2, the run of the thirteen walks
- `645bc83` docs: WP6.08 records, the guard walks' shifts and drifts (item 3)
- this note's commit, `docs: WP6.08 hand-off, implement`: item 3's tick

## Measured

- Item 2's run at `8cce00f` (`<git dir>/wp608-walks.log`): 43 passed, no skip, 294.7 s; thirteen walks, all
  same-mesh; each guard walk's largest drift 0.000e+00; VER-62's largest 2.898e-12 (`2wcd-charged`).
- Shifts from `example-02-epnpns` on mesh `546c34f4…`, recomputed from the stored hex values: current 3.6e-8 and
  flow 2.8e-8 at constant density, flow 4.7e-9 without inertia (the plan's *Grounding* reads 3.7e-8 and 4.8e-9 from
  its own default run; the knowledge section and the PR take the stored values).
- `docs/plans/current.md` 694 words, its In brief 170; the PR's In brief 274.

## Decided

- Item 2's tick commit, `2aa21d8`, is its own commit (the compaction checkpoint) though the item makes no other
  change; item 3 followed in the same helper, as the last note's Next asked.
- `holds-now.yaml`: BC3 reads `…its stored numbers widened by BI1, held by VER-80`.
- PHY-23, NUM-02, NUM-11 and NUM-14 are named in the PR as exercised, not discharged.
- No `usage.py` line for this helper (a helper skips it); the PR's Measured carries the plan's and item 1's lines
  the main session gave.

## Open

None.

## Next

A fresh helper for `/np-ship wp 6.08`, Sonnet 5.5 at medium effort (§8.2.56 BF1): read
`.claude/skills/np-ship/SKILL.md` and its `wp.md`, and start at §0 from PR #221 (head after the land of this note's
commit). The review of the code by `np-reviewer` comes first; the ship deletes this note in its commit after the
review.
