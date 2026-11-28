# WP6.11 hand-off, ship (the pulled-in items)

## Step

Ship, after the review was recorded and landed at 957e96a (PR #230). CI on that head not yet read. The author pulled in
REV-303 and REV-302 (`np-ship/wp.md` §4, item 1; §8.2.56 BF5).

## Done

- 957e96a docs: WP6.11 review recorded (before this step).
- This step: this note only.

## Measured

Cost so far (carry): 1 session, 9 sub-agents, 2.2 agent hours, 4 touches.

## Decided

- REV-303: the author ruled "Write the wall term", against the reviewer's recommendation to refuse. The permittivity
  gradient takes the wall fit's `dε/dd ∇d`, so PHY-23's force and NUM-28's split include it, with a check against the
  Maxwell stress.
- REV-302: "Pull it in". A builder measures first which side (lagged or trial) dominates, tries the cheaper fix, stays
  out of the terms (§5.4.1).
- Not pulled in: REV-294, REV-295, REV-299 (process), REV-301 (WP6.14).

## Open

None.

## Next

1. `np-builder` fixes REV-303 (one commit, `fix:`), then REV-302 (a second commit, `perf:`/`fix:`), and sets each row
   `fixed` in `docs/project/review-findings.md` and `review-items.md` in its commit (§8.4.6).
2. After the land, hand back `REVIEW` (`np-reviewer`, `effort: medium`) on the diff of the two fix commits alone.
3. Then update the PR #230 body (Deliberately not done: drop REV-302 and REV-303), hand back `WAIT, land: yes`, and read
   CI on the landed head (`np-ship/wp.md` §5).
