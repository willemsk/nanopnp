# WP6.11 hand-off

## Step

Plan, second helper of two: the plan is committed with the author's three rulings and its self-check is run. The
build has not started.

## Done

- `74503c2` `docs: WP6.11 plan draft` (the first helper).
- `6e98ccf` `docs: WP6.11 implementation plan`: the plan at **planned, not started**; the record
  `specification/history/63-wp611s-plan-switches-as-data-and-the-forces.md` (§8.2.63 BM1 to BM3), its lines in the
  history's index and `holds-now.yaml`; the Phase 6 plan's WP6.11 entry and open decision 20, with the entry as it
  read in `phase-6-record.md`; `docs/plans/current.md`; the decisions page and the plans' index.

## Measured

- The plan: 3,203 words; 1,643 outside Grounding and Implementation details (at most 1,650); 773 in Implementation
  details (at most 1,100); 266 in the In brief (at most 275).
- The Phase 6 plan without its report: 2,729 words (at most 2,750). `docs/plans/current.md`: 700 (at most 700).
- `uv run .claude/scripts/links.py`: 0 broken paths.

## Decided

- The author's answers, each the recommended one: the key is `numerics.log_variables` (BM1, D2); the ladder refuses
  it (BM2, D5); the workbench's Equations tool shows it (BM3, D7).
- The self-check moved four things in the draft, each now in the plan:
  - *Grounding* D4: `tests/tier1/test_physics_models.py` matches one refusal of the model, by "log branch", not
    two. The exclusion's message keeps those words, and the model's written refusal stays until item 2's record.
  - *Grounding* D5: `tests/tier1/test_case_schema.py` holds a kept test of the ladder's refusal, on the four
    switches. It gains the key, with a row in *Verification*, and the file is in items 1 and 2.
  - The row "An unset key moves no key" asked for two documents that are equal by construction. It asks for the
    key's absence from the parameters and for a hash recorded on the unedited tree.
  - *Out of scope*: the ladder carrying the log branch names Phase 7's speed-up (BC24) as the one that may reopen it.
- The package's pull request is #230, `feat: WP6.11 — switches as data and the forces`, opened at `155c38f`; the
  land brings it to the plan's commits. Its gate box is unticked until that land.

## Open

None.

## Next

1. The main session puts the manager's summary of the `DONE` hand-back to the author and waits for the approval.
2. The helper that follows runs `/np-implement wp 6.11`: it reads `.claude/workflow/helper.md`,
   `.claude/skills/np-implement/SKILL.md` and `wp.md`, then
   `docs/plans/phase-6/wp6.11-switches-as-data-and-the-forces.md`, and starts at work item 1,
   `src/nanopnp/io/switches.py` with four records.
3. Before item 2's first edit it records `CaseArtefact(VALIDATED_DEFAULT_CASE).hash`, the literal of the row "An
   unset key moves no key":

   ```bash
   uv run python -c "from nanopnp.io.artefact import CaseArtefact; from nanopnp.io.defaults import VALIDATED_DEFAULT_CASE; print(CaseArtefact(VALIDATED_DEFAULT_CASE).hash)"
   ```
