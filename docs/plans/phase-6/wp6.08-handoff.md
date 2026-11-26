# WP6.08 hand-off

## Step

Ship, first helper: §0 to §4 up to the review. PR #221 (head `claude/zealous-planck-aio2ty`) reused; the review has not run.

## Done

- Preflight clean: CHANGELOG `0.7.0-alpha.8` present, `duplicates.py` passes, branch equals `origin/<head>` at `4d0ceff`, based on `origin/main` `f571e72`.
- PR body's Verification now records the review's base `f571e722951ec8992de2192ea6a569f56bff9fc1` and head `4d0ceffd43db96af5d4189808568d04d8f88fab4`.
- This note's commit, `docs: WP6.08 hand-off, ship`; the land adds `just land`'s own commits, which the reviewer's head may carry.

## Measured

Numbers of the PR's Measured are the PR's; the ship adds none yet.

## Decided

Nothing new.

## Open

None.

## Next

Hand `REVIEW` was served by the main session. The next helper reads the reviewer's reply: check it shows base, head, commits, report path and each finding. Then fix a small left finding via `WORKER` (`np-builder`), give each other finding a `REV` row in `docs/project/review-findings.md` and `review-items.md`, delete this note, add the plan's Outcome with the package's measured cost (PR Measured lines plus this session's), commit as `docs: WP6.08 review recorded`, update the PR's Verification, and hand back `WAIT` with `land: yes`.
