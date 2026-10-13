# WP44 — Simplify the loop

**Status: planned, not started.** 13 October 2026. Inherits WP43's merged loop (to be removed in
part) and the rulings of §8.2.11 L2, L3, L6, L7, L8. Tag `v0.5.0-alpha.10`.

`docs/plans/phase-4-polish-and-user-testing.md` owns the phase. `SPECIFICATION.md` governs; the
identifiers below are pointers. This plan follows its own L7 rule: under 1,500 words, six decisions,
no per-item design, no planned tests.

## In brief

The automatic checks that run when you save work and when you share it grew into a large, slow
machine. This package replaces it with plain rules and removes the code that served the old ones.

**What changes.** Saving a piece of work runs the style checks and every quick test, always the
same ones. Sharing it runs everything once, in the background, and refuses to go ahead until that
run passed. The tools that picked tests, timed them and policed their speed are deleted, along with
the rules about which AI model may do which work. Plans for later packages become short enough to
read in one sitting and can be paused and resumed.

**Cost.** Saving should take about a minute and a half; sharing eight to nine minutes; a review
build under six minutes. These are reported, not enforced. Changed-line test coverage is now checked
only after sharing, so a miss shows up one step later.

**What could go wrong.** Running every quick test may still feel slow, and would show in the
measured time. Splitting the review build in two halves by file may be uneven; the measured time
would show it. Removing the model rules removes a safeguard for the riskiest work; the review step
still reads that work.

**Your call.** Two agent helpers stay (physics review and log reading) and two go. *Recommendation:*
keep that, since only those two were ever used for more than lookups.

## Execution brief

Scope: L2, L3, L6, L7, L8 only. The prose rule (L4, L5) is WP45. Depends on WP43 as merged. Clauses
pointed at: §7.6 table and NOTEs, Appendix A (VER-72, VER-73, VER-74), §8.2.10 J2 to J11, §8.2.11,
`CLAUDE.md` *Commands*, `.knowledge/07` §12, REV-80 to REV-83.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| Commit hook | `gate.sh` in hook mode runs `uv lock --check`, ruff check, ruff format check, mypy, then `pytest tests/tier1` as xdist runs it (default selection, no `extended`). A change that `prose-only.sh` calls prose runs ruff alone. The stamp skips an unchanged tree | L2. Tier 1 walks marked `extended` run at the push |
| Push gate | `gate.sh run` runs ruff, format, mypy and `pytest --extended` over the whole suite, no coverage, once. It writes the stamp. `NANOPNP_REQUIRE_GMSH=1` stays. The skills start it with `run_in_background` | L3; J10 stands |
| Push guard | Kept (author, 13 October). A `git push` passes only if the stamp names the tree of `HEAD` with `extended`; tag-only pushes and `--no-verify` pass. Predicted size of `gate.sh`: about 250 lines, of which the guard is about 50 | Author ruling; the plan reports the size |
| Shards | Two pull-request shards by `--shard i/N`: the sorted file list, file `k` to shard `k mod N`. No durations. Measured on the recorded durations: 840 s against 1,009 s of CPU, 1.2 times the ideal. A hand list of the heaviest files is the fallback if CI's critical path exceeds 7 minutes | L3. Smallest rule that holds near 6 minutes; tier splitting would be 332 s against 1,517 s |
| Agents | Delete `agent-guard.sh` and its hook entry, `reading_set.py`, `usage.py`, `model-policy.md`, `test_agent_roster.py`, and the agents `surveyor` and `gate-runner`. Keep `physics-reviewer`, `ci-log-classifier` and `clause.py`. The policy line lives in `CLAUDE.md`: Haiku for easy mechanical items, Sonnet by default, Opus after Sonnet has failed. The `[Opus]` marks go from the skills | L6. The roster test's clause, rule-loading and In brief checks move, not vanish |
| Plan shape | VER-72 gains (g): a plan from WP44 on holds at most 1,500 words, at most six rows under *Decisions*, no `## Design` heading, and an In brief of at most 250 words. The skills drop the Design section, the planned-test step and the `[Opus]` mark, and ask for compaction checkpoints | L7, L8; no dollar gate. VER-73 and VER-74 are withdrawn, their numbers not reused |

### Work items

Each item carries the clause edits for what it changes. One commit each; tick on completion.

- [ ] 1. Rewrite `.claude/hooks/gate.sh` to the two modes and the guard of D1 to D3; delete `tests/impact.py`, `tests/tier1/test_impact_selection.py`, `tests/tier1/test_loop_budgets.py`, the map mode and the `CLAUDE.md` map row; cut `tests/tier1/test_workflow_hooks.py` and `tests/tier1/test_push_guard.py` to what remains. Edit §7.6 (the development-selection and coverage NOTEs) and `.knowledge/07` §12. Done when those two files and `uv run pytest tests/tier1` pass.
- [ ] 2. Delete `.github/budgets.yaml`, `.github/scripts/ci_budget.py` and `tests/durations.json`; replace the packing in `tests/conftest.py` by D4 and rewrite `tests/tier1/test_shard_packing.py` (every file in exactly one shard; the shards cover the suite; `0/2` and `3/2` refused). Done when that test and `tests/tier1` pass.
- [ ] 3. In `.github/workflows/ci.yml`, drop the budget steps from `coverage`, update the header, keep two shards and diff-cover; withdraw the VER-73 NOTE in §7.6. Done when the workflow parses as YAML and the pull-request leg passes.

*Compaction checkpoint: after item 3, resume from this plan and `git log`.*

- [ ] 4. Delete the agent framework of D5; move the clause, rule-loading and In brief checks to `tests/tier1/test_plan_shape.py`, adding D6's checks; edit `.claude/settings.json`, §8.2.10 J8 and J11 (pointers to L6) and Appendix A (VER-72 (g); VER-73, VER-74 withdrawn). Done when `tests/tier1/test_plan_shape.py` passes, and fails on a toy plan of 1,501 words, seven decisions, a Design heading, and an In brief of 251 words, one case each.
- [ ] 5. Rewrite the five skills under `.claude/skills/` (`wp-plan`, `wp-implement`, `wp-ship`, `phase-plan`, `steward`), `CLAUDE.md` (*Commands*, *Implementation workflow*, the model line) and `CONTRIBUTING.md` to match D1 to D6. Done when none of them names a deleted file (checked by `grep` in item 6) and `uv run pytest tests/tier1/test_plan_shape.py` passes.

*Compaction checkpoint: after item 5.*

- [ ] 6. Close. Run `.claude/hooks/gate.sh run` in the background; time one commit hook, the push gate and the pull-request critical path; write them under Outcomes below against the predictions (hook about 90 s, push gate 8 to 9 minutes, pull request under 6 minutes) and the size of `gate.sh`. Mark REV-80 and REV-81 `fixed` by removal, update `docs/plans/current.md` and the Phase 4 plan, add a `CHANGELOG.md` line. Done when `grep -rn "impact.py\|ci_budget\|model-policy\|agent-guard\|reading_set" . --exclude-dir=.git --exclude-dir=.venv --exclude-dir=code_reviews` finds only history (plans, review records, the changelog).

### Verification

| Test | Tier | Identifier | Oracle |
|---|---|---|---|
| `tests/tier1/test_workflow_hooks.py` | 1 | L2, L3 | In a toy repository with a fake `uv`: a commit runs the five commands in order and stops at the first failure, naming it; a prose-only change runs ruff alone; an unchanged tree is not re-run |
| `tests/tier1/test_push_guard.py` | 1 | L3 | A push of an unstamped tree, or a tree stamped without `extended`, is refused; a stamped tree, a tags-only push and `--no-verify` pass; text that only names a push is not one |
| `tests/tier1/test_shard_packing.py` | 1 | L3 | Shards partition any file list; refusal text for `0/2`, `3/2` |
| `tests/tier1/test_plan_shape.py` | 1 | VER-72 (g) | The four toy failures of item 4; every plan from WP44 on passes; `current.md` and phase plans keep the In brief check |
| Whole suite | 1–2 | — | `uv run pytest --extended` via `gate.sh run`; VER-62 unchanged |

Run: `uv run pytest tests/tier1` per item; `gate.sh run` once at item 6.

### Out of scope

The prose rule and strip (WP45); any change to what a test asserts; CI's post-merge and nightly
jobs (J4 stands); the usage-cost figure (L8).

### Open questions

None blocking. The agent helpers kept are the author's call above.
