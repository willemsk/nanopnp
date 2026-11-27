# WP6.10 hand-off

## Step

Ship: the preflight, the PR's body and the review's start are done. The review waits on the hunt.

## Done

- Preflight: CHANGELOG carries `## [0.7.0-alpha.10]`; the branch is on `main` (base `5332fbdb`); `duplicates.py` passes.
- PR #227's body: the implement Measured, the reading counts and the Tier 2 note added, and the reviewed base and head
  under Verification (REST `gh api -X PATCH`; the GitHub MCP server fails to connect).
- This note's commit, `docs: WP6.10 hand-off, ship`.

## Measured

- Tier 2 with the `slow` tests: 220 passed in 71 min; `test_num07_weight_order_on_example_05` alone 3,974 s, the same on
  `2ba10ab9` within 1%, so not a WP6.10 regression.
- The thirteen walks: 43 passed in 406 s, largest drift 2.898e-12. REV-302 stays open.
- Implement helpers' reading: 10,185, 8,942 and 6,790 words before the first edit.

## Decided

None.

## Open

None put to the author.

## Next

Reviewer reply in hand: §4 of `.claude/skills/np-ship/wp.md`, items 1 to 4: fix small findings by `WORKER`
(`np-builder`), delete this note, record REV-302 in the PR's **Deliberately not done** (already there), write the
`docs: WP6.10 review recorded` commit (current.md, Status lines, Outcome with the summed cost), and hand back `WAIT`.
