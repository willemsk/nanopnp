# Code review 026: WP60, the Phase 4 close

Reviewed: PR 149, base `a800a45abe788d5eadf523efd1a197f206c84ad7`, head `c307024b91e3b7297d38a5589fc592b2ced9785d`.
Level: xhigh, with `--fix`. Status: completed. Static review: no benchmark, sweep, cost study, `gate.sh` or
`pytest --nightly` was run.

The diff touches one module, `validation/costs.py` (the quick-start leg of the cost study), and prose: the workflow
files (`CLAUDE.md`, `core.md`, the `np-*` skills, the steward skill and the Copilot map), `CHANGELOG.md`'s `[0.5.0]`
section, `CITATION.cff`, the front pages, the two findings logs, the review register, the ruling index and the
Phase 4 plan's end-of-phase report. No test is added or changed, and no physics or numerics code moves.

Checked:

- The workflow rewrite against `origin/main`, file by file. Every number, identifier, command and section reference
  survives, or moves to the file that owns its rule. The WP plan's caps moved from `CLAUDE.md` to
  `np-plan/wp.md`, and the compaction checkpoint lives in `np-implement/wp.md`. Both still match §8.4.4.
- The `[0.5.0]` section: WP(34+N) maps to `alpha.N` for all 25 pre-releases, and release.yml's notes extraction
  takes the `[0.5.0]` section alone. The removed public names still exist in their modules, apart from
  `mesh_cylinder` (finding 1). `nanopnp.PUBLIC` holds 19 names.
- The registers: 173 `REV` rows, 129 `fixed`, none `open`. The ruling index has no `open:` marker naming a Phase 4
  package. The cost record's three environment blocks name `db952e3`, `dirty: false`, and its shares are the ones
  the report quotes.
- The WP60 plan: 2,553 words outside its Outcomes, 1,426 outside Grounding and Implementation details, five
  decisions. All are within the caps.

## Findings

1. **The changelog says `mesh_cylinder` stays in its module** (correctness). The `[0.5.0]` break list put
   `mesh_cylinder` among the names that "stay in their modules". It was deleted with `nanopnp mesh cylinder` in
   `alpha.23`. **Fixed:** it has its own entry, with the migration to `geometry.pore`.
2. **The phase report reopens a ruled miss** (correctness). *What the phase carries* said that the author "may
   re-argue or accept" the commit-hook and push-gate misses. Verdict 11, the In brief and the PR record that the
   author accepted both on 2 November 2026. **Fixed:** it says so, and leaves re-arguing to a later phase.
3. **The README calls Phase 5 a desktop application** (correctness). This release edits the v0.6 row, but the row
   still read "then the desktop application". §8.1 and §8.2.17 S1 make it a browser workbench that replaces the Qt
   shell. **Fixed.**
4. **Trailing whitespace in `np-implement/wp.md`** (conventions; `git diff --check`). **Fixed.**
5. **The quick-start leg copies the shipped case** (simplification). `_quickstart_case` round-trips the case into
   the scratch directory, although the case has no relative paths and the walk runs with `write=False`.
   **Skipped:** the committed cost record names `db952e3` as the harness that produced it, and the copy changes no
   number.

Not assessed: the numbers measured on CI and in the cost study were not re-run (static review).
