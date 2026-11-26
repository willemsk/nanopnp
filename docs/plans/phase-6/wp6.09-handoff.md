# WP6.09 hand-off

## Step

Implement, done: items 8 and 9 ticked, the PR opened. Opus 5.5 at high effort built. The next step is the ship.

## Done

- `bdd540d` docs: the kernel's design page (item 8: `docs/design/kernel.md`, its line in `mkdocs.yml`)
- `3869ebf` docs: WP6.09's records (item 9)
- this note's commit, `docs: WP6.09 hand-off, implement`, which ticks item 9
- PR #224, `feat: WP6.09 — the kernel's design and its prototype`, opened on `ccr-d29ea716-fd3bw4` against `main`
  at `381cd05`; the land brings it to this note's commit

## Measured

- `uv run just docs`: passed after item 8 and after item 9.
- The page: about 4,200 words, against D7's "about 3,500".
- `docs/plans/current.md`: 669 words; its In brief 146.
- PR #224's In brief: 267 words.
- Helper 4's own cost was not measured (no `usage.py` in a helper); the PR's Measured line says the main session
  measures it.

## Decided

- D4's one contradiction: today's `advective_velocity` leaves out PHY-23's decrement, which no clause rules. It is
  REV-300 (numerics, low, open), the page's choice 2 for the round, and section 8.7 of the knowledge note. Not a
  defect fixed here (D8).
- The kernel is priced at four packages: about 12 sessions, 9 to 16 agent hours and 19 touches, from the prototype's
  0.7 agent hours and WP6.06's (3.3 h) and WP6.08's (1.5 h) measured lines.
- `holds-now.yaml`: besides BC2 and BJ1 to BJ3 as the plan says, AZ1's and BC5's `open:` now name the round on the
  kernel's design, since both pointed at WP6.09.
- The PR's Tier 2 entries in the page's package table were set from each VER's subject: package 1 carries VER-14 to
  VER-18, VER-42 and VER-77; package 3 VER-12, VER-13 and VER-31.
- `/np-gui render` was not run: the page is Markdown, not a screen.

## Open

None.

## Next

`/np-ship wp 6.09`, Sonnet 5.5 at medium effort, on PR #224, head `ccr-d29ea716-fd3bw4` after the land. First
action: read `.claude/skills/np-ship/SKILL.md` and its `wp.md`, then start the review of the page
`docs/design/kernel.md` and the records of `3869ebf` against the plan
`docs/plans/phase-6/wp6.09-the-kernels-design.md` (D7, item 8, item 9). The prototype is read with
`git show 1b5f5e3:<path>`, never checked out.
