# WP6.08 hand-off

## Step

Plan, first helper of two (`np-plan/wp.md`, *Under `/np-carry`, the plan is two helpers*). The draft is committed
with its `### Decisions` and `### Grounding`; D1 and D2 are put to the author. Fable 5.2 at high effort planned.

## Done

- `3dfbe6f` docs: WP6.08 plan draft
- this note's commit, `docs: WP6.08 hand-off, plan`

## Measured

- 1,607 words in the draft, 747 of them outside `### Grounding`; the caps are 3,850 and 1,650.
- 6 walks, about 270 s on one core; each walk's seconds and shift are in the draft's table under D1.
- 0 open pull requests against `main`; the branch `claude/zealous-planck-aio2ty` started at `origin/main`, `f571e72`.
- VER-79, REV-297, record 58 and letter BH are the highest in use: the next are VER-80, REV-298, record 59, BI.

## Decided

- The seven walks of VER-62 that the build runs first are named by file, which runs a `nightly` test without the
  flag: `tests/tier2/test_examples_01_quickstart.py`, `test_examples_02_classical.py`, `test_examples_02_epnpns.py`,
  `test_examples_03_iv_sweep.py`, `test_examples_07_pdb_to_charged_run.py`, `test_pipeline_2wcd.py` and
  `test_exclusion_2wcd_walk.py`. Their time is not measured: the item is a `RUN` hand-back.
- The guard tests are one new file, `tests/tier2/test_guard_numbers.py`: one `Store` for the module, one test function
  a walk with its name written out, `test_ver80_<walk>_…`.
- The recording is `NANOPNP_RECORD_STABILITY=<dir>` on the guard file under the gate's SIMD cap, then
  `uv run python tests/tier2/data/merge_number_stability.py <dir>`, then the file again with no variable set.
- VER-80's row goes into §7.3 with the item that adds the test, not with the plan's commit: check first whether a
  records test wants a clause's test file to exist. Appendix A and `CHANGELOG.md` take a line with it.
- The phase plan's line "VER-62's stored numbers cover the default switches alone: the review's claim, not checked"
  is now checked (the draft, D1), and its open decision 14 and criterion 12 are settled by the plan; the final commit
  rewrites those lines and `docs/plans/current.md`, whose *Next* still names WP6.07's ship.
- The measured shifts of the two flow switches are a durable finding for `knowledge/`, with the item that records.

## Open

Put to the author, verbatim in the hand-back:

1. Which of the model's optional settings get stored reference numbers before the kernel is rebuilt: all six, the
   three BC3 names, or the three and the simpler stabilisation (D1).
2. On which machines the new numbers are held: Linux only, or all three platforms (D2).

## Next

A fresh `np-plan` helper, with the author's two answers in its prompt:

1. Read `docs/plans/phase-6/wp6.08-the-guard-numbers.md`, then `.claude/skills/np-plan/rulings.md`, *Where the
   rulings are written*.
2. Record the answers as BI1 and BI2 in a new `specification/history/59-wp608s-plan-the-guard-numbers.md`, with its
   line in `specification/history/index.md` and two lines in `holds-now.yaml`. Rewrite D1 and D2 to what was ruled.
   If D1 is narrowed, drop the walks ruled out, in D1, D3, D6 and the Grounding table's use. If D2 is "all three",
   remove the skip, and give the fold of the macOS and Windows records an owner in `### Out of scope`: a chore after
   the first nightly run, as a `REV` row.
3. Add REV-298 for D4's finding (`docs/project/review-findings.md`, `review-items.md`), owned by WP6.09's design.
4. Write the rest of the plan (`np-plan/wp.md`, *What to write*): the status line, the In brief, the work items,
   `### Verification`, `### Out of scope`, `### Open questions`; amend the phase plan and `current.md`.
5. Run `uv run .claude/scripts/decisions.py` and `uv run .claude/scripts/index_records.py`, then the self-check of
   `np-plan/review.md`, and commit `docs: WP6.08 implementation plan`.
