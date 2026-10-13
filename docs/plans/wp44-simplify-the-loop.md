# WP44 — Simplify the loop

PR: [#96](https://github.com/willemsk/nanopnp/pull/96), branch claude/friendly-maxwell-o1alsq

**Status: delivered, 13 October 2026.** Inherits WP43's merged loop and the rulings of §8.2.11 L2, L3, L6, L7, L8. Tag `v0.5.0-alpha.10`.

The Phase 4 plan owns the phase. `SPECIFICATION.md` governs; identifiers are pointers. This plan
follows L7: under 1,500 words, six decisions, no per-item design, no planned tests.

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
measured time. Splitting the review build in two halves may be uneven; the measured time
would show it. Removing the model rules removes a safeguard for the riskiest work; the review step
still reads that work.

**Your call.** Two agent helpers stay (physics review and log reading) and two go. *Recommendation:*
keep that, since only those two were ever used for more than lookups.

## Execution brief

Scope: L2, L3, L4's rule edit, L6, L7, L8. The tree strip and VER-75 are WP45. Depends on WP43 as
merged. Clauses: §7.6, Appendix A (VER-72 to VER-74), §8.2.10 J2 to J11, §8.2.11, `.knowledge/07` §12, REV-80 to REV-83.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| Commit hook | `gate.sh` in hook mode runs `uv lock --check`, ruff check, ruff format check, mypy, then Tier 1 without the `extended` marker, `tests/tier1/test_gui_widgets.py` excluded and run serially afterwards as today. Gmsh is required only for a change to Gmsh's own code or tests, as today. A change `prose-only.sh` calls prose runs ruff alone; an unchanged tree is not re-run | L2. No Tier 1 test is `extended`; all sixteen such files are in Tier 2 |
| Push gate | `gate.sh run` takes the lock, runs ruff, format, mypy and `pytest --extended` over the whole suite, no coverage, with the Gmsh and APBS requirements set, once; it stamps the tree `extended` only on a pass and only if the tree did not change meanwhile. The skills start it with `run_in_background` | L3; J10 stands |
| Push guard | Kept (author, 13 October). A `git push` passes only if the stamp names the tree of `HEAD` with `extended`; tag-only pushes and `--no-verify` pass; text that only names a push is no push. All of today's recognition cases survive. The size is not predicted: item 1 reports it against the phase plan's 300 lines for the whole of `gate.sh` | Author ruling |
| Shards | The two pull-request shards are Tier 1 and Tier 2, by `-m tier1` and `-m tier2`. The `--shard` option, the packing and `durations.json` go. On the development selection (778 s) that is 332 s against 447 s, 1.15 times the ideal | L3, smallest rule. A split of the heaviest files by hand is the fallback if CI's critical path exceeds 7 minutes |
| Agents | Delete `agent-guard.sh` and its hook entry, `reading_set.py`, `usage.py`, `model-policy.md`, `test_agent_roster.py`, and the agents `surveyor` and `gate-runner`. Keep `physics-reviewer`, `ci-log-classifier` and `clause.py`. The rule, Haiku for easy mechanical items, Sonnet by default, Opus after Sonnet has failed, lives in `CLAUDE.md`; the `[Opus]` marks go from the skills | L6. The roster test's clause, rule-loading and In brief checks move, not vanish |
| Plan shape and prose rule | VER-72 gains (g): a plan from WP44 on holds at most 1,500 words, at most six *Decisions* rows, no `## Design` heading and an In brief of at most 250 words; the skills drop the Design section, the planned-test step and the `[Opus]` mark, and ask for compaction checkpoints and a 1,500-word phase plan. The prose rule of L4 is written into `python.md`, `CLAUDE.md`, `pyproject.toml` and `CONTRIBUTING.md` here | L4, L7, L8. VER-73 and VER-74 are withdrawn, numbers not reused; L8 withdraws J7's token figure and J11 |

### Work items

Each item carries the clause edits for what it deletes or changes. One commit each; tick on completion.

- [x] 0af3891 1. Rewrite `.claude/hooks/gate.sh` to D1 to D3. Delete `tests/impact.py`, `tests/tier1/test_impact_selection.py`, the map mode and the `gate.sh map` allowance in `.claude/settings.json`; cut `tests/tier1/test_workflow_hooks.py` and `tests/tier1/test_push_guard.py` to the cases of Verification. Edit §7.6's development-selection and coverage NOTEs, the VER-74 row and Appendix A's summary, `.knowledge/07` §12, `CLAUDE.md` (map row, coverage lines) and `.github/scripts/prose-only.sh`'s comments. Done when `uv run pytest tests/tier1` passes.
- [x] item 2 (this commit) 2. Delete `.github/budgets.yaml`, `.github/scripts/ci_budget.py`, `tests/durations.json` and `tests/tier1/test_loop_budgets.py`; remove `--shard` and the packing from `tests/conftest.py`; rewrite `tests/tier1/test_shard_packing.py` as a test of the kept `no_cover` marker, renamed off VER-73; in `.github/workflows/ci.yml` run the tiers as the two shards and drop the budget steps. Withdraw the VER-73 row and §7.6's budget NOTE. Done when `tests/tier1` passes and the workflow parses as YAML.

*Compaction checkpoint: after item 2; resume from this plan and `git log`.*

- [x] 40a2bac 3. Delete the agent framework of D5; move the clause, rule-loading and In brief checks to `tests/tier1/test_plan_shape.py` with D6's caps; edit the hook entry in `.claude/settings.json`, §8.2.10 J8 and J11 (pointers to L6 and L8) and VER-72 (g). Also edit `.github/scripts/prose-only.sh` where it names the roster test. Done when `test_plan_shape.py` passes and fails on a toy plan of 1,501 words, one of seven decisions, one with a Design heading and one with an In brief of 251 words.
- [x] f2c0761 4. Write L4's rule into `.claude/rules/python.md`, `pyproject.toml` (D101 to D107 and D417 off, D100 kept) and `CONTRIBUTING.md`; change WP45's phase-plan text to the strip alone. Done when `uv run ruff check .` passes.

*Compaction checkpoint: after item 4.*

- [x] 8c8c7f5 5. Rewrite the five skills under `.claude/skills/` and `CLAUDE.md` (*Commands*, *Implementation workflow*, the model line) to match D1 to D6. Done when `uv run pytest tests/tier1/test_plan_shape.py` passes.
- [x] 6. Close. Run `.claude/hooks/gate.sh run` in the background; time one commit hook, the push gate and the pull-request critical path, and the line count of `gate.sh`; record them under Outcomes against the predictions (hook about 90 s, push gate 8 to 9 minutes, pull request under 6) and the phase plan's 300 lines. Mark REV-80 and REV-81 `fixed` by removal, update `current.md` and the Phase 4 plan, add a `CHANGELOG.md` line. Done when `git grep -n -E "impact\.py|ci_budget|budgets\.yaml|durations\.json|model-policy|agent-guard|reading_set|usage\.py|surveyor|gate-runner|gate\.sh map|\[Opus\]"` matches only `docs/plans/`, `docs/project/`, `docs/code_reviews/`, `CHANGELOG.md` and the withdrawn or superseded rows of `SPECIFICATION.md`.

### Verification

`test_workflow_hooks.py` and `test_push_guard.py` (L2, L3: the five steps in order and the first failure named, the GUI file apart, prose runs ruff alone, an unchanged tree is not re-run, `run` passes `--extended` and no `--cov`, stamps only a pass and only an unchanged tree, takes the lock; every push-recognition case); `test_pull_request_shards.py` (the markers partition the selection); `test_plan_shape.py` (VER-72 g, with the four toy failures); the whole suite by `gate.sh run`; VER-62 unchanged.

### Out of scope

The tree strip and VER-75 (WP45); any product test's assertion; CI's post-merge and nightly jobs; a cost figure.

> **Outcome — measured 13 October 2026, 4 cores, Python 3.14.6.** Commit hook 187 to 220 s (1,966 Tier 1 tests; predicted 90 s: Tier 1 is longer than the 332 CPU-seconds assumed). Push gate 509 s (predicted 8 to 9 minutes). Pull-request critical path: first CI run. `gate.sh` 561 lines against 300; 273 are the kept push guard. REV-80 and REV-81 fixed.
