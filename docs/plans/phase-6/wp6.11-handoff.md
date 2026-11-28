# WP6.11 hand-off

## Step

Implement: done. Items 1 to 6 are ticked, both Status lines and `current.md` updated, and PR #230's body brought to
the tree. The ship (`/np-ship wp 6.11`) is next.

## Done

- `cd0d299` `feat: the switch records, every list of switches derived` (item 1).
- `0dd7ec9` `feat: numerics.log_variables, the log branch's case key` (item 2).
- `eba39c4` `docs: WP6.11 hand-off, implement` (item 3, the checkpoint).
- `40a24a5` `feat: the force split reads the kernel's force densities` (item 4).
- `2ac73dd` `docs: WP6.11 hand-off, implement`, the run's command given the gate's cap (item 5's `RUN`).
- `8e18208` `docs: WP6.11 records, REV-298 fixed` (item 6; item 5 ticked with its Outcome).
- This commit: `docs: WP6.11 hand-off, implement`, ticking item 6.

## Measured

- Item 5, second run, on `2ac73dd`, `linux-x86_64/X86_V3`, under the cap: `tests/tier2/test_guard_numbers.py`
  6 passed, none skipped, 230 s; largest relative drift 5.046e-16 (`guard-supg`), `guard-log` 4.093e-16.
- The PR's Measured holds the plan's and the first implement helper's usage lines as the main session gave them;
  this helper's usage line is not yet in it (a helper skips `usage.py`).

## Decided

- `holds-now.yaml`: BL7 and BM1 to BM3 now name their clauses, no longer `open: WP6.11`; BL1 and BC1 stay open for
  WP6.12 alone.
- The design page's switch table is brought to the records, and its *nine names* table says `SWITCHES` moved to
  `io.switches` as a tuple of records, no alias.
- `docs/project/physics-models.md`'s abridged `poisson` registration now matches the live one (switches from the
  records, `COEFFICIENTS`, `terms`).
- The item-4 script and its values stay uncommitted in `.git/wp6.11/`.

## Open

None.

## Next

Run `/np-ship wp 6.11` on PR #230, head `ccr-27befe84-ows69p` (Sonnet 5.5, medium), starting at
`.claude/skills/np-ship/wp.md` §0. The tag after the merge is `v0.7.0-alpha.11`.
