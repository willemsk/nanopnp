# WP43 — The development loop

**Status: planned, not started.** 12 October 2026. Inherits WP42's tree (`v0.5.0-alpha.8`),
WP33's suite levers and seeds (`.knowledge/07` §12), and the gate of WP23 to WP32
(`.claude/hooks/gate.sh`).

Part of [Phase 4](phase-4-polish-and-user-testing.md), under §8.2.10 J1 to J12. `SPECIFICATION.md`
governs; identifiers here are pointers into it, and where this plan and the specification disagree,
the plan is wrong.

## In brief

**What changes.** Today every commit waits about 3.5 minutes for tests, every push about 9.5, and
each pull request about 10 to 19 minutes in CI. After this package a commit runs only the tests
its change can affect, about a minute. The full check runs once before a push, in the background.
A pull request runs one fast Linux check, about 4 to 5 minutes. The long end-to-end walks and the
other platforms run after the merge, nightly and before a release. Python 3.14 becomes the working
version. Each kind of AI helper gets a fixed job and model, and the instructions every session
reads shrink by a third.

**Cost.** About a week of work, absorbed in the phase's 4 to 6 weeks.

**What could go wrong.**
- The commit check could miss a test a change affects. A test plants changes and proves every
  route is caught, and CI still runs everything.
- A walk-only or platform-only break now appears after the merge and is fixed forward.
- Python 3.14 could move a recorded number. That stops the package for your ruling.

**Your call.**
- The full pre-push check will likely take 6.5 to 8 minutes, not 5: one example's solve alone takes
  about 5 minutes and cannot be shortened within the rules. *Recommendation:* re-set that budget to
  8 minutes at the close, since it no longer blocks work.
- After the merge, make the single check "CI result" the one required check in branch protection.
  *Recommendation:* yes.

## Execution brief

Scope is §8.2.10 J2 to J5 and J7 to J11, as the Phase 4 plan's WP43 entry lists it, with J10's
move of the walks off the pull request. The brief runs over its 1,200 words and holds sixteen
decisions, because J1 ruled one package. The parts share one bootstrap order (D1) and one set of
budgets (D9), and the order cannot be split across two pull requests without re-running the old
gate on the new suite.

How the package answers the author's five requests of 11 October 2026:

| Request | Answered by |
|---|---|
| 1. A commit gate that is fast, permanently | D2–D7: affected tests only on commit, one background push gate per push with a guard, cheap follow-ups. D11 makes it last: CI fails a budget overrun and any test file over its ceiling, and the gate logs every run |
| 2. CI as effective and efficient as possible | D10, J4, J10: one sharded Linux leg per pull request, the platforms and walks after the merge, nightly older Pythons, a release matrix, timeouts, caching, one required check |
| 3. Python 3.15 and lazy imports | Not adopted (J6; OPN-09 sets when to revisit). D12 moves the working version to 3.14 instead |
| 4. Orchestration, accuracy, tokens, context | D13–D14, Design §9, §10 and §14: four defined agents with fixed models and tools, enforced by a hook, a clause script in place of a reading agent, checked retrieval, path-scoped rules, every duplicated passage reduced to one source, a reading set at least 30 % smaller, counting the rule files a package loads (J11), and a usage script |
| 5. A plain summary in every plan | D15, Design §12: the In brief template in the three planning skills and the PR body, tested on every plan from WP43 |

Requirements: **VER-74** (new, the selection's soundness), **VER-73** (new, the budgets), VER-46
and VER-62 (their cadence moves; their assertions do not), VER-72 (d) (the planned markers), QR-09,
CON-07, CON-10. Clauses amended in this package: §7.6's table and its three NOTEs, a budget NOTE,
Appendix A rows for VER-73 and VER-74, `CLAUDE.md` *Setup*, *Commands* and the gate lines,
`.claude/model-policy.md`, the five skills and `.knowledge/07` §12. J10 to J12 were written into
§8.2.10 in this plan's commit.

Dependencies: none open. WP44 is measured against this package's reading set (J11).

### Decisions

| # | Decision | Choice | Why / source |
|---|---|---|---|
| D1 | Order | The plan's planned tests first; then the selection (items 1–2) before anything relies on it; Python 3.14 (item 4) before the timings that are budgeted on it; the context work last | J2: the fast hook is trusted only once VER-74 holds. Until item 2 lands, commits run the old hook |
| D2 | The impact tool | **A recorder of our own**: `tests/impact.py`, a pytest plugin (`-p impact --impact-record=PATH --impact-source=src/nanopnp`). It notes each code object a test starts through `sys.monitoring` `PY_START`, on a free tool id, with each event disabled after its first hit and re-armed per test. A fixture scoped wider than a function is recorded once and credited to every test that requests it. Audit hooks note a test that starts a process (`subprocess.Popen`, `os.system`, `os.exec*`, `os.posix_spawn`) and every source file it opens as data. Python 3.12 or later; on 3.11 it refuses, naming the version | Measured: coverage's per-test contexts cost +83 % (dev selection 363 s against 199 s) and credit a module or session fixture to the first test alone, which under-selects. pytest-testmon traces through coverage too, is a new dependency, and has the same fixture gap. An import graph misses registry dispatch (`create()`). Design §1 |
| D3 | The map | JSON at `$(git rev-parse --git-common-dir)/nanopnp-impact/map.json`, schema `nanopnp/impact/v1`. It records the tree it was recorded on (the `git add -A` tree, as the gate's stamp), the source root, and per test node id: the functions as `path::qualname` (identities only; what changed is read from the git objects, Design §6), the source files read, whether it starts a process, and whether it is `extended`. Each xdist worker writes its own part, which the selector merges. It is written by every push-gate run and by `gate.sh map` | A worktree shares it. A fresh container has none and falls back. Keyed by qualname, so a line shift elsewhere in the file changes nothing |
| D4 | What a change selects | Cumulative from the map's tree to the working tree. A change inside a function body selects every test that started that function, or a function nested in it. A changed source file selects every test that read it as data. Any change under the source root selects every process-starting test. A changed `tests/**/test_*.py` selects itself. Markdown outside `src/` selects nothing. Selection is by whole file: every test in a file with any selected test. **Everything else falls back**, naming the path in its reason: a module-level, class-body, signature or decorator change, an added, deleted or renamed module, a non-Python file, any `conftest.py`, `pyproject.toml`, `uv.lock`, a hook or a workflow, or a map missing (`no impact map`), corrupt (`unreadable`) or from an unknown tree (`tree`) | The routes by which a test can depend on a change, each one planned in `test_impact_selection.py`. Whole files keep module fixtures sound. Design §1 |
| D5 | The commit hook | Lock check, ruff, format, mypy. Then `impact.select`, without `extended` (J2): the selected node ids under `-n auto --dist loadfile`, or none. On a fallback, the development selection, and the hook's output names the reason. The pass is stamped `impact`. Gmsh and the GUI file are handled as now. `/wp-implement`, `/wp-ship` and the steward start `gate.sh map` in the background as their first step, so the second commit of a fresh container is already fast | 60 s target (J7). Measured on the current map: a typical one-module change selects about 30 to 50 s of wall time on 4 cores. Changes to `core/`, `physics/` and `numerics/` select most of the suite (Design §3) |
| D6 | Soundness, stated | Design §1: if no function a test started, no source file it read, no module-level statement and no non-Python file changed, then the test executes as before. Residuals: non-determinism (a fixed seed or the clock), which is outside the claim, as it is for CI | `[Opus]`: a gap here passes silently. VER-74 enumerates the routes; CI's full run stays the authority (J3) |
| D7 | The push gate | `gate.sh run` started with Bash `run_in_background`, so the session is woken when it ends and never polls. It reports only failures. **A push guard** in `gate.sh`'s hook mode refuses `git push` unless the stamp names `HEAD^{tree}` with `extended`. It runs nothing. A tag-only push and `--no-verify` pass. **The follow-up** (J3): after a pass on tree P, `run` on tree T selects with `include_extended=True` from P's map. It runs that selection under coverage and runs diff-cover on the lines changed since P, comparing against a commit object made from P (`git commit-tree`). The map and stamp then move to T. A fallback runs the whole gate | A push never goes out ungated, and a one-line fix no longer re-runs 2,000 tests. The follow-up's soundness is Design §2. The residual is a change that removes the only coverage of a line changed *before* P; CI's full diff-cover catches it |
| D8 | Suite speed | Three things, each with its lever, and nothing more. (a) **Ordering, longest file first** from a committed `tests/durations.json`. Files missing from it take the median. It is regenerated by `tests/impact.py durations` from a `--durations=0` log. This is §7.6's fourth lever by scheduling: no test changes. (b) **The `extended` tests carry `no_cover`** (J10: coverage is over the development selection). The walks no longer pay coverage's +33 %. (c) **`COVERAGE_CORE=sysmon`** on 3.14, if it is faster and its XML report is identical on the same tree; otherwise stay on ctrace. Not done: the 2WCD seeds are already shared across workers under a lock (`tests/conftest.py`, `seeded_2wcd`). Example 07 stays cold (§7.6), and its 285 s solve is not coarsened: `t+` is 0.543 against a gate of ½, under three times its headroom. Four BLAS threads leave it unchanged (measured: 285 s and 289 s) | The four levers (§7.6 NOTE, WP33). Design §3 |
| D9 | Budget predictions | Commit hook about 50 s for a typical change, ≤60 s. Push gate 6.5 to 8 min: **a predicted miss of J7's 5 min**, set by example 07 (477 s alone, measured). PR critical path about 4 to 5 min, ≤6. Reading set ≤6,894 words (J11) | A miss is reported with its cause and ruled (J7). The In brief recommends re-setting the push gate to 8 min |
| D10 | CI (J4, J10) | **Pull request**, ubuntu 3.14: `changes`; `lint` (lock, ruff, format, mypy); `docs`; `tests (shard i/2)`, the development selection under coverage, files assigned to shards by longest-first bin-packing from `tests/durations.json` (`--shard i/2`, the conftest); `coverage` (`coverage combine`, then diff-cover against the base, then the VER-73 check); and **`CI result`**, which needs them all and is the one required check. **Push to `main`**: macOS-3.14 and Windows-3.14 run Tiers 1–2 with `--extended`, plus the GUI file serially and the bundle. Ubuntu runs the `extended` walks, and the development selection too unless the merged tree equals the tree the PR's `CI result` passed, read from a `ci/tested-tree` commit status on the PR head. **Nightly**: Tier 3, and 3.11, 3.12 and 3.13 on ubuntu, macOS and Windows with `UV_NO_BUILD=1` running Tier 1, all `continue-on-error`. **Release**: `ci.yml` gains `workflow_call` with `full: true` (the three platforms × 3.11–3.14, `--extended`), which `release.yml` needs before it builds. Every job gets a `timeout-minutes` (lint and docs 10, shards 20, platforms 40, bundle 30, nightly 30, tier3 60). The apt step is cached (`awalsh128/cache-apt-pkgs-action`, pinned by tag as the other actions are). `docs` syncs `--no-default-groups --group docs`; `lint` drops the `apbs` group | Two shards: the dev selection is about 720 s of test time under coverage, so about 90 s a shard on 4 vCPU (public repository) plus about 100 s of long files. One required check stops shard or matrix renames from touching branch protection. A fork PR cannot post the status, so it is never skipped on that ground (safe). Design §4 |
| D11 | VER-73 | `.github/budgets.yaml`: `commit_hook_s: 60`, `push_gate_s: 300`, `pull_request_critical_path_s: 360`, `file_ceiling_s: 90`, `margin: 0.5`. The file ceiling makes the hook's budget last: no development-selection file may take over 90 s × 1.5 in CI's junit durations (`check_files(durations, ceiling_s, margin)`), because the hook's wall time is bounded below by its longest selected file. This is WP33 D15's ceiling, made a check. `.github/scripts/ci_budget.py` gives `critical_path_s(jobs)` (first start to last completion) and `check(jobs, budget_s, margin) -> (passed, message)`. Its message names the measured value, the budget and the margin as a percentage, says "over budget" when it passes inside the margin, and names an unfinished job. CI's `coverage` job reads the run's jobs through the API and fails past budget × 1.5. A hook run over 90 s prints an over-budget notice and never fails on it (Design §7). The local budgets are logged by `gate.sh` to `<git-dir>/nanopnp-gate.log`, as time, mode, selection size and tree, and reported by the usage script. VER-73 supersedes WP33 D15's targets; REV-47's close reports both | Margin from the measured spread: the same suite took 8m11s and 13m07s on one day (1.6×), so a 50 % excess is beyond the variance already seen. A tighter margin would fail on runner noise alone. Design §5 |
| D12 | Python 3.14 (J5) | First, the five VER-62 walks on 3.14 under the X86_V3 cap, on Linux: the deployed mesh hashes must be the recorded ones and each number must hold at 10⁻⁸. Any move stops the package (G10). Then macOS and Windows on 3.14 through a `workflow_dispatch` of the branch. Then `.python-version` → 3.14, CI's pins, `CLAUDE.md` ("developed on 3.14") and `.knowledge/07`. `requires-python` is unchanged | `[Opus]`: a moved golden is a plausible wrong number. Wheels: every locked package has a cp314 wheel on all three platforms, except `watchdog` on macOS arm64 (docs group only; docs run on ubuntu) |
| D13 | The roster (J8) | **Four agents** in `.claude/agents/`: `gate-runner` (sonnet; Bash, Read; `effort: low`), which runs a named gate stage or selection and returns failures only; `surveyor` (haiku; Read, Grep, Glob; `effort: low`), which locates and counts, with paths, for the caller to check; `ci-log-classifier` (sonnet; Read, Grep, Glob), which classifies a fetched log against the steward's table; `physics-reviewer` (opus; Read, Grep, Glob; `effort: high`). The first three set `omitClaudeMd: true`; the reviewer loads `CLAUDE.md`. **Clauses by identifier come from a script**, `.claude/scripts/clause.py <ID>…`, not an agent: it prints the identifier's row or section and every NOTE and §8.2 ruling that names it, verbatim with line ranges. **A PreToolUse hook enforces the roster**, `.claude/hooks/agent-guard.sh` on `Agent`: it refuses a roster agent called with a `model` other than its file's, and any other agent called without an explicit `model`, each naming the model policy. The model policy points at the agent files and the hook as its enforcement, and gives Haiku checked retrieval | Author, 12 October 2026 (§8.2.10 J8, amended). A script cannot miss a NOTE its search covers and costs no model; an agent copying text verbatim pays a cold start and output tokens, and the text lands in the caller anyway. `omitClaudeMd` (Claude Code 2.1.271+; 2.1.296 here) saves `CLAUDE.md`'s words on every retrieval spawn. `high`, not `xhigh`, for the reviewer: the added benefit does not repay the cost now (author). A call's `model` overrides the file's, and nothing else stops a `general-purpose` spawn on the session's model, hence the hook. Unknown keys are ignored silently (docs), hence `test_agent_roster.py` |
| D14 | Leaner context (J8, J11) | `.claude/rules/physics-numerics.md` (paths `src/nanopnp/{physics,numerics,solve,post,materials,charge,mesh,validation}/**`, `data/corrections/**`, `tests/tier2/**`, `tests/tier3/**`) takes *Physics ground rules* and *Numerics rules*, and `.claude/rules/python.md` (paths `src/**/*.py`, `tests/**/*.py`, `.claude/scripts/**/*.py`, `.github/scripts/**/*.py`, `docs/scripts/**/*.py`) takes *Coding conventions*. Each is moved verbatim, not rewritten. A path-scoped rule loads only when a matching file is read or edited, so `/phase-plan`, `/wp-plan` and `/wp-ship` §4 read both explicitly. **J11's count includes the rule files a package triggers**: `reading_set.py` adds each rule file whose `paths` match a file the plan's Work items name, so moving text into a rule file does not count as a cut when the package's work loads it again. The Execution brief is capped at 1,600 words for J11: `/wp-plan`'s 1,200-word target becomes this limit, and `reading_set.py` fails a brief over it. With the fixed files at their targets (4,500 words, plus about 190 for the Python rules and 340 for the physics rules), a full brief still leaves the set under 6,894 (author, 12 October 2026: a tighter cap would cost the plan detail; no brief since WP35 met 1,200). The script also prints the set without the brief, so the fixed files' own cut is visible beside the total. Word targets: `CLAUDE.md` 1,300; `wp-implement` 1,000; `wp-plan` 1,100; `wp-ship` 1,200; `steward` 1,500; `phase-plan` 1,800; model policy 500; `current.md` 700; `.knowledge/00-index.md` 1,000. `.claude/scripts/reading_set.py <plan>` counts J11's set. `.claude/scripts/usage.py` reports a transcript's tokens by model and its sub-agent spawns by type, nothing more, and fails naming an unknown format | J11 baseline, counted at `d630f85`: 2,074 + 1,558 + 902 + 1,566 + 850 + 2,899 (WP42's brief) = **9,849 words**. WP44 must be ≤6,894. The baseline is unchanged by counting rule files: at `d630f85` their text was inside `CLAUDE.md` and counted there. Paths widened to every module whose code the physics and numerics rules govern (author, 12 October 2026). `usage.py` reads an internal format and gates nothing, so it stays small (author) |
| D15 | `## In brief` (J9) | A template in `phase-plan`, `wp-plan` and `wp-implement`, and in the PR body `wp-implement` writes: at most 250 words; what changes and why, the cost, what could go wrong and how it would be noticed; then **Your call**, each item with a recommendation. **No code or identifiers**: the section holds no backtick and nothing shaped like a requirement identifier (`VER-62`, `§7.6`, `D13`). Item 9 trims the Phase 4 plan's In brief to the limit (385 words today, its last paragraph moved under the next heading) | `test_agent_roster.py` checks the skills, every work-package plan from WP43 on and every phase plan from Phase 4 on, `current.md` included; J9 asks for text readable without code or identifiers, and a test is what keeps it so (author, 12 October 2026) |
| D16 | Records | VER-73 and VER-74 rows in Appendix A; §7.6's table, its development-selection and coverage NOTEs, and a budget NOTE; `CHANGELOG.md` under `v0.5.0-alpha.9`; a REV-nn row for each missed budget | H12, J7 |

### Work items

- [x] 89e7bb2 1. [Opus] — under-selection passes silently. `tests/impact.py`: the recorder plugin, its merge
  and `select()` (D2–D4; build from Design §6). Measure the recorder's overhead on the development selection: ≤10 %, or
  the item stops for a re-plan. Done when every test in `tests/tier1/test_impact_selection.py`
  passes with its markers removed.

  > **Outcome — the planned `toy` fixture shared the module's map.** It returned the
  > module-scoped map path itself, and the `corrupt` and `unknown-tree` cases overwrite it, so
  > every later case read a damaged map and no implementation could pass. Each test now gets its
  > own copy. The author approved the fix on 12 October 2026; no assertion changed.

  > **Outcome — the recorder costs about 1 %.** Development selection, `-n auto --dist loadfile`,
  > BLAS threads pinned, 4 cores shared with other agents (load 2.5 to 3.4), tree `0dbf490`
  > (`493b72f` plus the item's module), Python 3.12.3, 2,129 tests recorded:
  >
  > | Round | Without recorder | With recorder | Overhead |
  > |---|---|---|---|
  > | 1 | 239.8 s | 240.0 s | +0.1 % |
  > | 2 | 252.8 s | 256.2 s | +1.4 % |
  >
  > The map is 6.8 MB. 144 tests start a process; 27 functions run at import or collection. A body
  > change to `total_current` in `post/qoi.py` selects 1,038 tests in 54 files, in 0.46 s: 21
  > files call into `qoi.py`, and the process starters and the source readers make up the rest.
  > Not re-measured on 3.14: the merge of item 4 was not available to this session.

  > **Outcome — the routes as built go beyond D4, each selecting more, never less** (accepted by
  > the author in principle, 12 October 2026):
  > - Markdown read as data selects its readers. Markdown that `prose-only.sh` does not call prose
  >   (the specification, findings logs, example READMEs) also selects the process starters, whose
  >   children may read it unseen.
  > - A function started at import or collection, outside any test, is listed in the map, and a
  >   change to it falls back: the registries' `register`, `CaseDocument`'s validators.
  > - A changed test file also selects every test file that names it (`git grep -w`), as
  >   `test_axis_weight_order.py` imports `test_mms`.
  > - An added test file selects itself, by path, instead of falling back.
  > - Directories a test lists are recorded, so an added or deleted Markdown or test file selects
  >   the tests that globbed its directory.
  > - Wide fixtures and test modules' bodies are recorded as scopes of their own and merged across
  >   xdist workers, so a seed loaded from disk on one worker still credits the code that another
  >   worker ran to compute it.
- [x] f04766a 2. [Opus] — a hook that skips a test is silent. `gate.sh`: the hook runs D5, adds `gate.sh
  map`, and stamps `impact` (Design §7). The skills' first step starts `gate.sh map`. Amend §7.6's
  development-selection NOTE and `CLAUDE.md` *Commands*, and add VER-74 to Appendix A, from the
  Design §11 drafts. Read Design §1 first. Done when `test_workflow_hooks.py` and `test_impact_selection.py` pass, and a planted body
  change in `post/qoi.py` commits through the hook in ≤60 s.

  > **Outcome — most past commits would have fallen back, and imports alone never forced it.**
  > Of the last 15 non-merge commits touching `src/` that this clone holds a parent for (`a93f5e3`
  > to `d630f85`), D4's rules applied to each parent-to-commit diff fall back on 12. The causes:
  > another module-level change in 10, a changed data, case or fixture file in 5, an added module in
  > 2, one function started at import, and an import change in 4. An import change was never the
  > only cause. The rule that costs the hook most is therefore D4's module-level fallback as a
  > whole, not imports; these commits are whole review rounds, larger than a typical commit.

  > **Outcome — the throwaway index keeps the real index's mtime.** With `core.checkStat=minimal`
  > (this container's global configuration), git compares whole-second mtimes and sizes, and it
  > re-reads an entry as racy only when the file is no older than the index file. A copy with a fresh
  > mtime hid a same-size edit made in the index's second: seen once, under load, as a planted
  > decorator change that selected nothing. `tests/impact.py` copies with `shutil.copy2` and
  > `gate.sh`'s stamp with `cp -p`; `test_ver74_a_same_size_edit_in_the_index_second_is_seen` fails
  > on the old copy.
  > **Outcome — the hook misses 60 s on a `post/qoi.py` change: 115 s and 155 s
  > ([REV-80](../project/review-items.md#rev-80-a-source-change-selects-every-process-starting-test-file-so-the-commit-hook-misses-its-60-s-budget)).**
  > 4 cores, Python 3.14.6, map recorded on the parent (2,136 tests, 249 s under the recorder), BLAS
  > threads 1. A planted body change in `rectification_ratio` selected 866 tests in 40 files and
  > committed in 115 s; one in `total_current`, 1,012 tests, in 155 s. The process-starting files
  > (151 tests in 30 files) take 64.7 s alone: D4's "any source change selects every process
  > starter", widened to whole files, is the floor, not the change's own callers (8 tests for
  > `rectification_ratio`). D9's prediction of 30 to 50 s did not count that floor. The fallback rate
  > of past commits is [REV-81](../project/review-items.md#rev-81-most-past-commits-would-fall-back-to-the-development-selection).
  > The orchestrator's review added two fixes: the selector's stderr is never read as a node id
  > (`14d759e`), and a selected GUI file stays serial.

- [x] 5f5704b 3. [Opus] — the follow-up's coverage claim is a soundness argument. Make `gate.sh run`
  background-safe: a PID file, failures only, the follow-up rule (D7) and the gate log. Add the push
  guard. Update the `wp-implement`, `wp-ship` and `steward` skills to start the gate in the
  background and push on its pass. Amend §7.6's coverage NOTE. Read Design §2 and §7 first. Done when
  `test_push_guard.py` passes unmarked and a one-line follow-up runs only its selection.
  > **Outcome — the follow-up runs only its selection, but a source change still costs 685 s of
  > 966 s.** 4 cores, Python 3.14, BLAS threads 1, with another agent running its own suites in
  > parallel on the same machine, so both timings are inflated. A full `gate.sh run` on `5f5704b`
  > passed in 966 s and recorded 2,202 tests. A one-line docstring change in `rectification_ratio`
  > (`post/qoi.py`; `6eb7f9a`) was committed, then `gate.sh run` followed up from that pass: 955 tests
  > in 50 files, 685 s, diff-cover against the pass's commit. It passed, and the map and the stamp
  > moved to the new tree. That is 43 % of the tests for 71 % of the time. The floor is REV-80's: any
  > source change selects every process-starting file. With `--extended`, those files include six
  > example walks, example 07's 477 s among them, so a follow-up after any source change costs about
  > 8 minutes, whatever its size. A change to tests or prose alone does not pay it. A follow-up
  > after a fix confined to tests, or after nothing at all, is the cheap case; for a source fix, the
  > floor stays until the process starters are attributed per function (REV-80's remedy).
  > Three decisions beyond Design §7, each erring safe:
  > - The stamp's commit object has the merge base as its parent, and diff-cover runs two-dot
  >   (`--diff-range-notation=..`). Three-dot against a parentless commit has no merge base. A moved
  >   merge base, as after a rebase, runs the whole gate.
  > - A pass whose tree changed while it ran stamps nothing and exits 1.
  > - The push guard judges each refspec's source tree, not only `HEAD`'s. It refuses `--all`,
  >   `--mirror` and `--branches`, and it refuses a push in the same command as a commit.
  > The coverage NOTE carries the follow-up only. Its J10 half, that coverage leaves out the
  > `extended` walks, describes item 5's `no_cover` and lands with it.
- [x] 05af299 4. [Opus] — a moved golden is a plausible wrong number. Run VER-62 on 3.14 (D12); if anything
  moves, stop and report to the author. Then the macOS and Windows dispatch, `.python-version`, CI's
  pins, `CLAUDE.md` and `.knowledge/07`. Done when the five walks pass on 3.14 at 10⁻⁸ with
  unchanged mesh hashes, and the dispatch is green. Ticked with the macOS and Windows dispatch pending: it
  needs the branch pushed.

  > **Outcome — VER-62 holds on 3.14 on Linux.** CPython 3.14.6, `linux-x86_64/X86_V3` (the
  > `NPY_DISABLE_CPU_FEATURES` cap of CI and the gate), the same locked versions as 3.12. The six
  > walk files under `--extended`, `-n 2 --dist loadfile`: 26 passed, none skipped, 423 s wall. All
  > seven walks deploy their recorded reference mesh (same-mesh mode); largest relative drift
  > 6.9 × 10⁻¹⁴ (example 01, `eof_m3_s`), every other walk ≤ 2.7 × 10⁻¹⁵. Per file (setup + calls):
  > example 07 421 s, the 2WCD pipeline 148 s, the shell walk 53 s, example 03 46 s, example 01
  > 25 s, example 02 21 s. CI's ubuntu matrix now carries 3.12 in place of 3.14, which the `check`
  > job runs, so VER-47's 3.11–3.14 still holds. `.knowledge/07` §8.
- [x] 2e84650 5. [any] Suite order and coverage (D8): `tests/durations.json`, the longest-first order,
  `no_cover` on `extended`, and the `sysmon` measurement. Done when `gate.sh run` passes and the
  timings are recorded in `.knowledge/07` §12.

  > **Outcome — `sysmon` is already in effect, and faster.** coverage 7.15 defaults to it on
  > CPython 3.14 with branch coverage; on the development selection it took 292 s against
  > `ctrace`'s 511 s, with byte-identical XML reports, so nothing is configured. The order's own
  > gain could not be measured: another agent's runs held the load at 2 to 8 on the 4 cores, and
  > the ordered and path-ordered `--extended` runs took 937 s and 830 s back to back. Item 10
  > re-measures it. `.knowledge/07` §12.2.
- [ ] 6. [Opus] — §7.6 is normative text. CI (D10): `ci.yml`, `release.yml`, the shard option in
  `tests/conftest.py`, the status post, timeouts, apt cache and trims (Design §4, §8). Amend §7.6's table and its
  development-selection NOTE (J4, J10). Done when the PR's `CI result` is green, a dispatch with
  `full: true` is green, and the step summary shows the shard times.

  > **Outcome — built and checked locally; the CI evidence is pending a push.** `actionlint`
  > 1.7.12 with `shellcheck` passes both workflows. The two shards partition the development
  > selection (2,147 tests: 1,145 and 1,002, no test or file in both), 399.1 s and 399.2 s of
  > recorded time. Four deviations, each found while building: **the nightly also runs the
  > platforms' `--extended` legs**, because §8.2.10 J10 says the nightly runs the walks, which
  > D10's nightly list omits; **the release matrix is its own job, `full-matrix`**, with the
  > Python versions literal, because VER-47's test reads them from the workflow (it now reads that
  > job, its assertion unchanged); **`UV_NO_BUILD` covers the dependency step only**, because uv
  > refuses it for the project's own editable install; and **`coverage` needs `lint` and `docs`
  > too**, so every job its critical-path check measures has ended. Jobs that sync fewer groups
  > than the default run `uv run --no-sync`, or `uv run` would sync them back. A dispatch of
  > `release.yml` re-releases an existing tag without the full matrix.
- [ ] 7. [any] VER-73 (D11): `.github/budgets.yaml`, `.github/scripts/ci_budget.py`, the CI step,
  the gate log, §7.6's budget NOTE and the Appendix A row. Done when `test_loop_budgets.py` passes
  unmarked and the PR run reports its critical path.
- [x] 9804c08 8. [any] The roster and the model policy (D13; Design §9, §10): the four agent files,
  `.claude/scripts/clause.py`, `.claude/hooks/agent-guard.sh` registered on `Agent` in
  `.claude/settings.json`, and the model policy. Done when `test_agent_roster.py`'s roster, clause
  and guard tests pass unmarked.
- [x] 7b916c0 9. [any] Leaner context and summaries (D14, D15): the rules files with D14's paths, the
  explicit reads in `phase-plan`, `wp-plan` and `wp-ship` §4, the trims to the targets by Design
  §14's map, `reading_set.py` and `usage.py` (Design §13), the In brief template (Design §12), and
  the Phase 4 plan's In brief trimmed to 250 words, and `wp-plan`'s brief target raised from 1,200 to 1,600 words (D14). Done when the In brief and reading-set tests
  pass unmarked and `reading_set.py` reports each target met.
- [ ] 10. [any] Close: measure the four budgets on this tree (the hook on three one-module changes:
  `post/qoi.py`, `io/case.py`, `physics/poisson.py`). Add a REV-nn row per miss, update
  `CHANGELOG.md` (`v0.5.0-alpha.9`) and the Phase 4 plan's WP43 entry, and leave the REV-47 note.
  Done when `gate.sh run` passes and the numbers are in the PR body.

### Verification

| Test | Tier | Identifiers | Oracle | Command |
|---|---|---|---|---|
| `tier1/test_impact_selection.py` | 1 | VER-74 | Each route of D4 selects its tests, by node id; each fallback names its path; the walks are excluded unless asked for; xdist and serial maps select alike | `uv run pytest tests/tier1/test_impact_selection.py` |
| `tier1/test_push_guard.py` | 1 | J3 | No branch push without `HEAD^{tree} extended`; a hook pass never stands in; a tag-only push, `--no-verify` and other commands pass | as above, by file |
| `tier1/test_loop_budgets.py` | 1 | VER-73 | The recorded budgets are J7's, the file ceiling 90 s and the margin 0.5. A budget below the measured value beyond the margin fails, naming all three. An unfinished job fails. A file over its ceiling beyond the margin fails, naming it | as above |
| `tier1/test_agent_roster.py` | 1 | J8, J9, J11 | Four agents with exact models, tools and effort; `omitClaudeMd` on the three retrieval agents and not on the reviewer; no unknown key; `clause.py VER-62` prints its Appendix A row and every §8.2 ruling naming it, and fails on an unknown identifier; the guard refuses a roster agent's other model and a non-roster agent without one, and passes the rest; the rule files carry D14's paths; `reading_set.py` counts a triggered rule file and fails a brief over 1,600 words; the skills carry the In brief; every plan from WP43 and Phase 4, and `current.md`, opens with one of ≤250 words, no backtick and no identifier | as above |
| `tier1/test_workflow_hooks.py` | 1 | J2, J3 | Existing; extended in items 2 and 3 for `map`, the `impact` stamp and the follow-up | as above |
| The five VER-62 walks on 3.14 | 2 | VER-62 | Mesh hashes as recorded; numbers at 10⁻⁸ | `uv run --python 3.14 pytest --extended <the five files>` |
| The budgets | — | J7, VER-73 | Item 10's measurements against D9 | item 10 |

Each planned test is `xfail(strict=True, reason="planned: WP43 …")` and turns green by removing the
marker. A test that already passes today, such as a tag push passing the guard, is unmarked: it
guards what must not change.

### Out of scope

- PEP 810 and Python 3.15 (OPN-09, J6).
- The user-level Stop hook (`~/.claude/stop-hook-git-check.sh`), which is not the repository's. The
  skills push as soon as the background gate passes.
- Pinning actions by SHA. They stay pinned by tag, as now. This is a later chore if the author wants
  it.
- Coarsening example 07, or caching seeds across runs: the first breaks §7.6's headroom rule, and
  the second gives a test a store its code did not write.
- A map seeded from CI: artefact downloads need a token in the container.

### Open questions

None blocking. At the merge, the author makes `CI result` the required check, if branch protection
has any.

## Design

### 1. Why the selection is sound (D2, D4, D6)

A test's outcome is a function of the code it executes, the files it reads and its environment.
Take the map recorded on tree P and the working tree T.

1. **Import-time code.** A module's top-level statements run at import, outside any test, and run
   alike at T only if they are unchanged. These are module-level code, class bodies, signatures with
   their defaults, and decorators, which can register a function under a name others look up. A
   change to any of them falls back.
2. **Functions.** Take a test t that started functions F at P, and suppose no function in F changed
   body. Each executes statement for statement as at P, so t's control flow reaches only functions
   in F, and so on inductively. The first point of divergence would have to be a changed statement
   in a function t executed, which contradicts the assumption.
3. **Fixtures.** Code a wider-scoped fixture runs executes in the setup of whichever test asks first.
   The recorder credits it to every test that requests the fixture, so a change to it selects all
   of them, not just the first (`test_ver74_a_function_only_a_session_fixture_calls_selects_every_user`).
   Selecting whole files keeps module fixtures and their readers together.
4. **Outside the trace.** A child process is not traced, so a test that starts one is selected by
   any source change. A source file read as text, as by VER-72's checks, is a file dependency. Any
   other non-Python file falls back, because C code can read it unseen.
5. **Cumulative.** Selecting from P, not from HEAD, keeps step 2's premise true across commits made
   after the map. A test's executed set can change only through a changed function, which is itself
   selected.
6. **Residuals.** Non-determinism is outside the claim, as it is for CI. A Python older than 3.12
   cannot record, so it falls back.

VER-74 plants one change per route. CI's full run on every pull request remains the authority (J3).

### 2. The follow-up's coverage (D7)

After a pass on P, diff-cover against main covered every changed line. A follow-up T needs, for each
line changed since P, the coverage the full run would give.

- **Lines executed by an unselected test.** By §1, such a test executes at T exactly what it did at
  P. It started no changed function, so it executes no line changed since P.
- **Every other such line.** It can be executed only by a selected test, and the follow-up runs every
  selected test under coverage.
- **So for lines changed since P,** the subset's coverage equals the full run's.

A line changed between main and P keeps P's verdict. The exception is a follow-up that removes that
line's only coverage, and CI's full diff-cover catches that. Coverage is a union, so a subset never
covers more than the full run: a subset pass can never hide a line the full run fails.

### 3. Measurements and predictions (4 cores, `d630f85`, 11–12 October 2026)

| Quantity | Measured | After WP43 (predicted) |
|---|---|---|
| Hook, pytest stage | 199 s (development selection) | Median one-module change about 30–50 s; `core/`, `physics/`, `numerics/` 2–3 min |
| Dev selection with per-test coverage contexts | 363 s (+83 %) | Not used (D2) |
| Process-starting test files | 34 files, about 130 s of plain test time | About 35 s of the hook's wall when any source changes |
| Example 07, alone | run block 477 s: PROPKA 107 s, solve 285 s; 487 s and 289 s with 4 BLAS threads | Unchanged (cold, §7.6) |
| Push gate | 527 s with coverage | 6.5–8 min: walks without coverage, longest first; example 07 is the floor |
| PR critical path | ≈10.5 min, 13–19 min a full run | 4–5 min |

The selection estimates come from the coverage map of the first row's run: function-level selection
over 122 modules, with the process-starting files added.

### 4. CI after WP43

```text
pull_request:  changes ─┬─ lint ───────────────┐
                        ├─ docs ───────────────┤
                        ├─ tests (shard 1/2) ─┐ ├─ CI result  (the required check;
                        └─ tests (shard 2/2) ─┴─ coverage ─┘    posts ci/tested-tree)
push to main:  changes ─┬─ ubuntu-3.14: extended walks [+ dev selection unless tree tested]
                        ├─ macos-3.14, windows-3.14: --extended, GUI file serial
                        └─ bundle (Windows)
nightly:       tier3; 3.11/3.12/3.13 × ubuntu/macos/windows, UV_NO_BUILD=1, Tier 1 (recorded)
release (tag): ci.yml workflow_call full=true → build → release
```

### 5. VER-73's margin

Same-day reruns of the same suite took 8m11s and 13m07s on ubuntu, and 9m58s and 15m26s on
Windows: a spread of 1.55 to 1.60. A margin below 0.5 would fail on runner noise alone, while a
50 % excess over budget is beyond any spread seen. CPU time was considered and rejected: the API
reports wall time per job, and the budget J7 states is a wait.

### 6. `tests/impact.py`, the implementer's sketch (D2–D4)

The module is a pytest plugin and a command line. It imports nothing from `nanopnp`, so it records
a toy repository as well as this one.

```python
# Plugin, loaded by -p impact (the root conftest does not load it by default).
def pytest_addoption(parser): ...    # --impact-record=PATH, --impact-source=src/nanopnp
def pytest_configure(config): ...    # only with --impact-record: refuse on < 3.12, naming the version;
                                     # claim a free sys.monitoring tool id from (3, 4), else fail naming both;
                                     # sys.addaudithook(_audit) once (audit hooks cannot be removed)
# One collector per active scope; every active collector receives each event.
#   pytest_runtest_protocol (hookwrapper)   -> collector for item.nodeid (setup, call and teardown)
#   pytest_fixture_setup (hookwrapper)      -> collector for fixturedef.scope != "function",
#                                              keyed f"{fixturedef.baseid}::{fixturedef.argname}"
# A push calls sys.monitoring.restart_events() so events disabled under the previous
# collector fire again; the PY_START callback adds the code object and returns DISABLE.
# At a test's end, its record takes the union of every wider fixture it requested
# (item._fixtureinfo.name2fixturedefs[name][-1] for name in item.fixturenames).

def _identity(code) -> str | None:
    # code.co_filename under the source root, else None.
    # qualname cut at the first ".<locals>": a nested def, lambda or genexpr counts as its outer function.
    # "<module>" and class-body code (no def) -> None: import-time code is D4's fallback.
    return f"{relpath}::{outer_qualname}"

def _audit(event, args):
    # subprocess.Popen, os.system, os.exec, os.posix_spawn, os.spawn -> starts_process = True
    # open: str or bytes paths only; under the source root -> files.add(relpath);
    #       __pycache__/x.cpython-3XX.pyc counts as x.py (an import read in a test over-selects: safe)
```

The map file, written on `pytest_sessionfinish`: a worker (`config.workerinput` exists) writes
`PATH.<workerid>.part`, and the controller merges the parts into `PATH`. A serial run writes `PATH`
directly. The tree is computed as `gate.sh` computes its stamp: `git add -A` into a throwaway
index, then `git write-tree`.

```json
{"schema": "nanopnp/impact/v1", "tree": "<40 hex>", "source": "src/nanopnp",
 "tests": {"tests/tier1/test_x.py::test_y[a]": {
     "functions": ["src/nanopnp/post/qoi.py::current"], "files": ["src/nanopnp/core/paths.py"],
     "process": false, "extended": false}}}
```

The map holds identities only. The selector finds what changed from the git objects:

```python
@dataclass(frozen=True)
class Selection:
    fallback: str | None        # e.g. "src/nanopnp/core/constants.py: module-level change"
    tests: tuple[str, ...]      # node ids, sorted; whole files (D4)

def select(repo: Path, map_path: Path, *, include_extended: bool = False) -> Selection:
    # 1. read the map: missing -> "no impact map at <path>"; bad JSON or schema -> "map unreadable: <why>";
    #    `git cat-file -e <tree>` fails -> "map tree <id> is not in this repository"
    # 2. T = the working tree's tree (as above); changed = git diff --name-status --no-renames P T
    # 3. per path: *.md outside the source root -> ignore; tests/**/test_*.py modified -> select its node ids;
    #    *.py under the source root, status M -> compare skeleton(P) with skeleton(T), else fall back
    #    "<path>: module-level change"; changed bodies -> functions; anything else -> fall back "<path>: <status>"
    # 4. tests = users of changed functions | readers of changed files | (process starters if any source changed)
    #    | changed test files; widen to whole files; drop extended unless include_extended
```

`skeleton(source)` parses the module and replaces the body of every `FunctionDef` and
`AsyncFunctionDef` with `pass`, keeping decorators, arguments, defaults and annotations. It returns
`ast.dump(tree, include_attributes=False)`. Two skeletons that are equal except for added
functions under fresh names still fall back: it is simpler, and only slower. `body(source,
qualname)` is the dump of that function's body. A docstring edit therefore selects the function's
tests.

The command line, which `gate.sh` uses:
- `uv run python tests/impact.py select --map M [--extended]` prints node ids, one per line.
  - A fallback prints `FALLBACK: <reason>` and exits 3.
  - An empty selection prints nothing and exits 0.
- `uv run python tests/impact.py merge --map M --part P --tree T` replaces P's tests in M and sets
  M's tree to T. It is used by the follow-up.
- `uv run python tests/impact.py durations LOG` writes `tests/durations.json` from a `--durations=0`
  log, summing setup, call and teardown per file. Its format is
  `{"schema": "nanopnp/durations/v1", "files": {"tests/tier2/test_x.py": 51.4}}`, with seconds from
  a 4-worker run. Regenerate it at each package's close if a file moved by more than 20 %.

### 7. `gate.sh` after WP43 (D5, D7)

```text
hook mode, command matches git push (a regex like the commit regex):
  --no-verify among its options          -> allow
  every refspec a tag, or --tags only    -> allow
  stamp has "<HEAD^{tree}> extended"     -> allow
  else deny: "The push was not made: no passing push gate for HEAD's tree. Run
             .claude/hooks/gate.sh run (in the background), then push. --no-verify skips this."
  (it runs no uv command; test_push_guard.py's fake uv proves it)

hook mode, git commit (as now, then):
  prose only -> ruff alone (unchanged)
  lock, ruff, format, mypy
  out=$(uv run python tests/impact.py select --map "$map")   # exit 3 -> fallback
    fallback -> development selection, as today, reason printed in the deny text if it fails
    empty    -> no pytest
    else     -> uv run pytest -q -rsfE -n auto --dist loadfile <ids>   (-n 0 if < 20 ids)
  stamp "<state> impact"; log line

run:
  as now, plus -p impact --impact-record="$map.new"; extended items carry no_cover (conftest);
  on pass: mv "$map.new" "$map"; commit=$(git commit-tree <state> -m gate) ; stamp "<state> extended <commit>"
  follow-up: a stamp "<P> extended <commitP>" with P != state, the map's tree == P, and select --extended
    without a fallback -> run only those ids with --extended --cov ... and -p impact --impact-record="$part";
    diff-cover --compare-branch=<commitP>; on pass: impact.py merge; stamp "<state> extended <commit>"
  any fallback -> the whole run, as today

map:  pytest's development selection with -p impact --impact-record, no coverage; writes the map
      and stamps nothing. Started in the background by the skills' first step.

log:  <git-dir>/nanopnp-gate.log, one line per run:
      ISO time, mode (hook|run|follow-up|map), selection (impact|development|extended), test count,
      seconds, tree, result. A hook run over 90 s (60 s x 1.5) prints a one-line "over budget" notice; it never fails on it.
```

The stamp keeps one line per selection, so a later commit-hook pass cannot overwrite the `extended`
line that the push guard reads.

### 8. CI, the parts that are easy to get wrong (D10)

```yaml
# tests shard, pull request:
- run: uv run pytest -rs -n auto --dist loadfile --ignore=tests/tier1/test_gui_widgets.py
         --shard ${{ matrix.shard }}/2 --cov=src/nanopnp --cov-branch --cov-report=
         --junitxml=junit-${{ matrix.shard }}.xml
  env: {COVERAGE_FILE: .coverage.shard${{ matrix.shard }}}
- uses: actions/upload-artifact@v7      # .coverage.shard*, junit-*.xml; include-hidden-files: true
# coverage: download both; uv run coverage combine; uv run coverage xml; diff-cover as today;
#           then uv run python .github/scripts/ci_budget.py --run ${{ github.run_id }} (GH_TOKEN)
#           and the per-file check from the junit durations (D11).
# CI result:
  needs: [changes, lint, docs, tests, coverage]
  if: always()
  run: fail if any needs.*.result is failure or cancelled
  # then, on pull_request from this repository only (continue-on-error for forks):
  gh api repos/$REPO/statuses/$HEAD_SHA -f state=success -f context=ci/tested-tree
        -f description="$(git rev-parse HEAD^{tree})"
  permissions: {statuses: write}
# push to main, in changes:
  head=$(gh api repos/$REPO/commits/$SHA/pulls --jq '.[0].head.sha // empty')
  tested=$(gh api repos/$REPO/commits/$head/statuses --jq '[.[]|select(.context=="ci/tested-tree")][0].description // empty')
  dev_needed=$([[ -n $tested && $tested == $(git rev-parse HEAD^{tree}) ]] && echo false || echo true)
```

`--shard i/N` lives in `tests/conftest.py`, beside `--extended`. Files are sorted by
`tests/durations.json`, longest first, with a missing file taking the median. Each goes to the
least-loaded shard, and ties go to the lower index. A file's tests are never split across shards.
The same ordering puts the items longest file first when no shard is given (D8 a).

### 9. The agent files (D13), verbatim to start from

Four files, each the frontmatter plus a body of at most 150 words. The body states the job, what
to return and what never to do.

```markdown
---
name: gate-runner
description: Runs a named gate stage or pytest selection for nanopnp and returns only the failures. Use for a long or noisy run whose log should stay out of the caller's context.
model: sonnet
tools: Bash, Read
effort: low
omitClaudeMd: true
---
Run exactly the command you are given, under `uv run`, with OMP/OPENBLAS/MKL_NUM_THREADS=1. Return:
PASS with the summary line, or FAIL with each failing node id and the first assertion or error line
under it, at most 40 lines in all. Never edit a file, re-run with other options, or diagnose.
```

The `surveyor` (haiku, `effort: low`, `omitClaudeMd: true`) finds files, symbols and counts,
returning paths with line numbers, and never judges. The `ci-log-classifier` (sonnet,
`omitClaudeMd: true`) is given a log file path. It returns the failing step, the first error,
quoted, and the steward's failure class, quoted from `.claude/skills/steward/SKILL.md` *Failure
classes*; the caller confirms the class on the quoted lines before standing down on a failure. A
Tier 2 failure it only labels "physics evidence: Opus". The `physics-reviewer` (opus,
`effort: high`, loads `CLAUDE.md`) reviews a diff or a named function against the cited
specification, `.claude/rules/physics-numerics.md` and `.knowledge/01`. It returns findings with
file:line, sign and unit, and edits nothing.

**`.claude/scripts/clause.py <ID>…`** replaces a specification-reading agent. For each identifier
(`VER-62`, `FR-16`, `§7.6`, `J8`) it prints, with line ranges: the identifier's defining row or
heading's section; every NOTE whose text names it; and every §8.2 ruling row that names it. It
matches whole identifiers (`VER-6` never matches `VER-62`), exits non-zero on one with no
definition, naming it, and is run with `uv run`. The skills call it wherever they read a cited
clause.

**`.claude/hooks/agent-guard.sh`**, a PreToolUse hook on `Agent`, reads the payload with `jq`, as
`gate.sh` does. With `subagent_type` naming a file in `.claude/agents/`, it refuses a `model` other
than that file's. With any other type, `fork` aside, it refuses a call without `model`. Each refusal
is a `deny` naming the agent, the models and `.claude/model-policy.md`. It passes everything else,
and a payload it cannot parse.

**Checked retrieval** is the model policy's new Haiku rule. The caller verifies anything it relies
on by reading the returned line range itself, which is one `Read` with `offset` and `limit`.

### 10. Who delegates what (D13, D14)

| Skill step | Today | After |
|---|---|---|
| `wp-plan` survey | `Explore` (Sonnet) | `surveyor` for "where/how many"; `clause.py` for clause text |
| `wp-implement` start | reads `00-index`, spec sections | `gate.sh map` in the background; `clause.py` for each cited identifier, never the whole section |
| `wp-implement` / `wp-ship` gate | foreground `gate.sh run`, polled | Bash `run_in_background`; on failure, `gate-runner` re-runs the failing ids alone |
| `wp-ship` §4 confirmation | the session (Opus) | unchanged, after reading both rule files; `physics-reviewer` only for a second opinion on a Tier 2 or physics finding |
| `steward` CI failure | the session reads the log | `ci-log-classifier` on the fetched log; Tier 2 stays with the session on Opus |
| `phase-plan` exploration | ad hoc | `surveyor`; measurements by `gate-runner` |

### 11. Clause drafts (item owners copy these and adjust only to match the measured facts)

- **§7.6 table (item 6)**:
  - a pull request runs Tiers 1 and 2 without the `extended` walks, on ubuntu, Python 3.14;
  - a push to `main` runs Tiers 1 and 2 in full on ubuntu, macOS and Windows, Python 3.14;
  - nightly runs Tier 3, and Tier 1 on Python 3.11 to 3.13 on the three platforms, recorded and
    not gated;
  - before a tagged release, Tiers 1 to 4, Python 3.11 to 3.14, on the three platforms;
  - every push, prose-only pushes included, runs VER-45's strict documentation build.
- **The development-selection NOTE (item 2, then item 6)**:
  - "CI runs these tests on every push, on every leg" becomes "on every push to `main`, nightly
    and before a release, and the push gate before every push (§8.2.10 J10)";
  - "the commit hook runs the development selection" becomes "the commit hook runs the tests a
    test-impact selection finds the change to touch, falling back to the development selection
    (VER-74)".
- **The coverage NOTE (item 3)**:
  - coverage is measured over the development selection, not the extended one, and the `extended`
    tests run without it (J10);
  - `gate.sh run`'s follow-up measures it over the selected tests, against the passed tree, by
    Design §2's argument.
- **The budget NOTE (item 7)**: the four budgets of J7, the 50 % margin of VER-73 with Design §5's
  argument, and the 90 s ceiling per file.
- **VER-73's row**:
  - CI's coverage job fails a pull-request run whose critical path, from the first job's start to
    the last needed job's completion, exceeds `pull_request_critical_path_s` by more than `margin`;
  - it fails any development-selection file whose recorded duration exceeds `file_ceiling_s` by
    more than `margin`;
  - shown to fail on a recorded run set below its measurement (§8.2.10 J7).
- **VER-74's row**:
  - a change planted in a function's body selects every test that started it, directly, through
    a fixture of any scope, or by reading its file;
  - a change under the source root selects every test that starts a process;
  - a module-level, signature or decorator change, a non-Python file, a configuration file and a
    missing or foreign map each fall back, naming the path;
  - shown on a recorded toy repository (§8.2.10 J2).

### 12. The In brief template (D15), for the three skills and the PR body

```markdown
## In brief

At most 250 words, no code or identifiers needed; written for a reader who does not code.

**What changes.** What the reader will notice, and why it matters.
**Cost.** Time, money or speed, in plain units.
**What could go wrong.** Each risk, and how it would be noticed.
**Your call.** Each decision the author owns, as a question, with *Recommendation:* and one reason.
```

The PR body that `wp-implement` writes opens with this. `wp-ship` keeps it current when the review
changes anything an author would decide.

### 13. The two scripts (D14)

- **`.claude/scripts/reading_set.py <plan.md> [--at <rev>]`** prints each file of J11's set with its
  word count (`str.split`), the brief's count (the text from `## Execution brief` to the next `## `
  heading), each rule file whose `paths` match a path the plan's *Work items* name in backticks,
  and the total, then the total without the brief. It fails on a brief over 1,600 words. With
  `--at`, it reads the files at that revision through `git show`.
  `--at d630f85 docs/plans/wp42-verification-checks.md` must print 9,849 (no rule files existed).
- **`.claude/scripts/usage.py <file>`** reads a Claude Code transcript (`*.jsonl`) or a JSON list of
  session `result` events, saved by an agent from `list_events`. It prints the tokens (input, cache
  read, cache creation and output) by model, and the sub-agent spawns by type. Gate minutes are
  `nanopnp-gate.log`'s (D11), not this script's. An unknown record shape stops it, naming the
  line. The transcript format is internal to Claude
  Code and may change, so the script reports and gates nothing.

### 14. Where to cut, file by file (D14; surveyed 12 October 2026)

Each figure is cut needed against the target. A **single source** keeps the text, and every other
copy becomes a pointer of at most one line. Sections are named, not numbered by line, because items
2 and 3 move text first.

| File | Words → target | Cut first |
|---|---|---|
| `CLAUDE.md` | 1,549 counted (after the three rule sections move) → 1,300 | *Commands* and the gate lines are rewritten once, by items 2–3. The *Implementation workflow*'s sub-agent and non-Opus paragraphs become one-line pointers to the model policy. *Git*'s tag procedure points to `CONTRIBUTING.md`. *Durable learnings* points to `.knowledge/00-index.md` |
| `wp-implement` | 1,558 → 1,000 | The non-Opus paragraph (source: the model policy). The failure-mode list, which wrongly says `CLAUDE.md` names it: cut to one clause. Henry/Smoluchowski (source: the steward). "Flake" (source: the steward). The PR contract (source: `wp-ship` §3). The tag steps (source: `CONTRIBUTING.md`). The rationale clause of the `main`-branch check |
| `wp-plan` | 1,416 → 1,100 | "Everything in CLAUDE.md under Physics…" (*Rules the plan must respect*) becomes "read `.claude/rules/physics-numerics.md`". The web-search rule (source: `CLAUDE.md`). The Outcome-history paragraphs. The prose-only finishing detail (source: `CLAUDE.md` *Commands*) |
| `wp-ship` | 1,696 → 1,200 | §4's completion-evidence prose and the `48f5f63`/WP9 story: keep "invoke directly, never in an `Agent`". §4's Opus-confirmation paragraph (source: the model policy). §5's polling and wake text: one line pointing to the steward's *Bounded wakes*. §1's re-gate: the push guard now enforces it |
| `steward` | 2,128 → 1,500 | *What CI runs* is rewritten whole for D10, and it becomes CI's single description (`CLAUDE.md` keeps only commands). *Failure classes*: the VER-62 row cut to three sentences, and the run-113 story to a pointer. *Fixes stay in scope*: the constraints list points to `CLAUDE.md` *Do NOT* |
| `phase-plan` | 2,551 → 1,800 | The phase anecdotes in Turn 1 and Turn 2 (Phase 1–3 histories, the renumbering story, WP33/34 examples) become a pointer to §8.2. The restated physics and web-search rules. The gate lines in *Finishing* and *Amending* |
| Model policy | 850 → 500 | *The rule*'s rationale (QR-12, RSK-03) becomes one sentence. *Applying it*'s example becomes "name the agent". *Cost discipline* becomes one line. *Who implements a plan* stays whole, as the single source |
| `current.md` | 889 → 700 | *Not to be re-decided*: one line per ruling with its pointer, no restatement. *Position*: no delivered-package list |
| `00-index.md` | 1,566 → 1,000 | *Five things* and *Conventions* become pointers to `01`, `02`, `06` and the rule files (wall function, Einstein, `1/r`, `⟨c⟩`). *Author rulings*: drop the dated narration (rulings 2, 8, 11–14 tails) and the restated permittivity and ruling-7 tails |

The current.md word target moves from 800 to 700 in one place, its *Handoff rules*; the skills
point there rather than restating it. The command chain is stated once, in `CLAUDE.md` *Commands*.
