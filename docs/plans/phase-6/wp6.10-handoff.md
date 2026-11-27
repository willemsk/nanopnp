# WP6.10 hand-off

## Step

Plan: done, by one helper. The plan is written, self-checked (`np-plan/review.md`) and committed; no decision went
to the author, so there was no `ASK` and no second helper. The author's approval is next, then the build.

## Done

- `21e1292` docs: WP6.10 implementation plan
- this note's commit, `docs: WP6.10 hand-off, plan`

## Measured

- 3,644 words in the plan: 896 in `### Grounding`, 1,099 in `### Implementation details`, 1,649 outside both; the
  caps are 3,850, 1,100 and 1,650. The In brief has 273 words of 275.
- 700 words in `docs/plans/current.md`, its limit. 2,750 words in the Phase 6 plan without its report, its limit: an
  edit of it by the build's last item must not add a word.
- 0 open pull requests for this package; `origin/claude/relaxed-heisenberg-axbj47` does not exist yet, and the
  branch started at `origin/main`, `5332fbd`.
- VER-80, REV-301, record 62 and letter BL are the highest in use; the plan claims VER-81 and no other.
- D2's quadrature measurements are in the plan's `### Grounding`; their scripts were scratch and are gone.

## Decided

- The planning model: the author chose Fable 5.2 at high effort (§8.2.56 BF9), and it wrote the plan.
- Nothing was put to the author. The phase plan's open decision 19 hands the slots' cut, each slot's rule and the
  operators' names to this plan; BL1, BL2, BL5 and BL6 rule the rest; no choice changes what a user sees beyond
  BL5's.
- The close calls, each in the plan and none in a record yet:
  - D2 merges the inertia with the two forces as one slot, with the inertia stated as the force density
    `−Re ρ̃ (∇ũ)ũ`, which the design's table kept apart. A bolder cut, the viscous stress with the pressure, moved
    a rule by 6.0 × 10⁻⁴ and was refused.
  - BL5 is read to keep the decrement's `∇∇φ̃` in the approximate residual; NUM-14's NOTE gains a sentence for it.
  - The manifest's Péclet expression is derived from the drifts in force. At the default it is today's string; a
    classical or `pnp` run's string loses the drifts it does not have.
  - Item 6 runs all thirteen stored walks, where the phase entry asked for the two push walks and the stabilised
    guards.
- The clause amendments are written by the items that build them, not by the plan's commit, as WP6.08's were.
- The self-check moved three things: `BackendImport`'s fields are `path` and `target`; `permittivity_gradient`
  keeps its signature and returns `None`, so `post/forces.py` needs no operators; a source keeps its own slot
  though it agrees with another in all four properties.

## Open

None. The plan's `### Open questions` is empty.

## Next

1. The main session lands this branch. Then the package's pull request is opened, by the next helper if the main
   session does not: title `docs: WP6.10 implementation plan`, base `main`, its body the plan's In brief, then
   `.github/pull_request_template.md` filled in (`.claude/workflow/finish.md`, *The PR contract*): the plan is in
   and the implementation follows; the code's review waits for the ship; no specification change in this commit.
2. After the author approves, a fresh `np-builder` for `/np-implement wp 6.10`: read
   `docs/plans/phase-6/wp6.10-the-composition.md` and start at work item 1. Its first action, before any edit of
   `src/`:

   ```bash
   git fetch origin prototype/wp6.09-kernel
   mkdir -p "$(git rev-parse --git-dir)/wp6.10"
   git show FETCH_HEAD:prototype/compare_operators.py > "$(git rev-parse --git-dir)/wp6.10/compare_operators.py"
   ```

   Then change the script as *The comparison* says and write the twelve variants' file from the unedited tree.
3. Item 6 is a `RUN` hand-back; item 3 is a compaction checkpoint.
