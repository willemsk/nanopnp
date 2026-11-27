# WP6.10 hand-off

## Step

Implement: done. Items 1 to 7 ticked; the package waits for `/np-ship wp 6.10`.

## Done

- `64112a8c` docs: WP6.10's records (item 6 ticked with its Outcome; item 7)
- this note's commit, `docs: WP6.10 hand-off, implement`
- PR #227's body brought to the tree by REST (`gh api -X PATCH repos/willemsk/nanopnp/pulls/227`); the GitHub MCP
  server fails to connect and `gh pr view` hits GraphQL, which is refused.

## Measured

- The thirteen walks at `5eeb55e3`, linux-x86_64/X86_V3: 43 passed in 406.49 s, all same-mesh, none failed or
  skipped; largest relative drift 2.898e-12 (`2wcd-charged`), none re-pinned.

## Decided

- `holds-now.yaml`: BL5 now holds in NUM-12's and NUM-14's NOTEs, §5.4.4 and VER-81; BL6 in §5.4.1, QR-13 and VER-65,
  open on WP6.12 for MOD-10; BL1 and BC1 open on WP6.11 and WP6.12.
- MOD-10 stays `deferred`, with a *Built for the coupled models* paragraph in `docs/project/modularity.md`; it closes
  at WP6.12.
- `docs/design/kernel.md` keeps its pre-WP6.10 tense: a sentence under its opening says *today* means `5332fbd`.
- No `usage.py` line was taken (a helper skips it); the PR's **Measured** keeps the plan's line alone.

## Open

None put to the author. REV-302 (PHY-23 under a stabilised mode assembles fifty times slower) stays open for the
ship's report.

## Next

Run `/np-ship wp 6.10` (Sonnet 5.5, medium) from `.claude/skills/np-ship/wp.md` §0: PR #227, head
`claude/relaxed-heisenberg-axbj47`; read the PR through `gh api repos/willemsk/nanopnp/pulls/227`.
