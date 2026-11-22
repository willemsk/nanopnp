# WP6.01 — The Windows leg: the stall named and bounded, the failures fixed

**Status: in progress.** Written 22 November 2026, grounded in the code at `2b1a468` (the Phase 6 plan's
merge). Inherits §8.2.49 AY4 and §8.2.50 AZ4, AZ7 and AZ8 (ruled at this plan), REV-277 and the test scope (§8.2.13
N1, N3). Its last commit on `main` takes `v0.7.0-alpha.1` (§8.4.1).

The [Phase 6 plan](phase-6-library-foundations.md)'s WP6.01 entry sets this scope; `SPECIFICATION.md` governs, and
where it and this plan disagree this plan is wrong. Identifiers are pointers into it.

## In brief

**What changes.** The Windows test run has hung since 3 November, so nothing has been tested on Windows for three
weeks. This package names the test that hangs and the tests that fail, fixes each at its cause, and adds a time limit
per test, so a future hang fails within ten minutes and names its test instead of silently using up the whole run.
Two faults a Windows user would meet are fixed on the way: the developer server's stop could kill it outright and
leave its worker running, and two bundled chart and formula libraries fail their integrity check after a Windows
checkout. As you ruled today, pull requests stay tested on Linux alone, and the three systems are checked on a branch
only at a phase's close.

**Cost.** About five sessions, three to six hours of agent work and eight times you act, as the Phase 6 plan
estimates from Phase 5's text and clean-up packages. One CI run on the three systems, about 40 minutes of machine
time. A user pays nothing.

**What could go wrong.** The hang's cause could be in the web server library on Windows rather than in our code:
the package then stops and puts the choice to you; no test is skipped on Windows. The time limit could cut a slow
but healthy test: the limit is ten times the slowest test measured today.

**Your call.** Settled on 22 November 2026: the three systems are checked on a branch only at a phase's close.
Nothing else is yours before the merge.

## Execution brief

Scope: the Phase 6 plan's WP6.01 entry, REV-277, and AZ8's ship rule. Depends on nothing; the Phase 6 plan is merged
at `2b1a468`. It claims no new identifier and writes no new test: the failing tests are the oracles (N1, N3).
**Implementing session: Opus 5.5, high effort** (§8.4.5); no item goes to a sub-agent, as each needs the CI evidence
read in this session. The APIs named are pytest-timeout 2.4's `timeout` ini key, marker and Windows `thread` method
(checked with Context7) and the GitHub Actions dispatch.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| **D1 Evidence before the fix** | Item 1 lands D2's guard and D3's bounded read, with no fix, and dispatches `ci.yml` on the branch. Its Windows leg ends with a summary that names each failure and the stalled test. Pre-registered: the stall is `test_ver78_the_reloading_server_prints_its_line_and_stops_with_its_input`; the failures include `test_con09_the_vendored_libraries_are_unmodified[katex]` and `[uplot]`, and the one at result 620. A miss is recorded in item 1's Outcome and fixed by D4's rule | AY4 ("names the failing test and the stall"); REV-277's recommendation; decided by the plan |
| **D2 A stall is a named failure** | `pytest-timeout>=2.4` joins the `dev` group. `[tool.pytest.ini_options]` sets `timeout = 600`; `tests/conftest.py` gives an item marked `nightly` or `slow` `timeout(7200)` unless it carries its own `timeout` marker. The composite action adds `--durations=20`. `nightly-issue` also fires on a `cancelled` leg. §7.6 gains a NOTE | The slowest per-push test is 46 s on four cores; example 05's own bound is 7,200 s; decided by the plan |
| **D3 The screens tests bound what they wait for** | `test_gui_screens.py:_start` reads the ready line with a 120 s bound, captures the server's standard error, and on expiry kills the server and fails with the command and the error's tail. Every server a test or fixture starts is killed in its `finally` or teardown | `_start` blocks in `readline()` with no bound; decided by the plan |
| **D4 A fix is at the cause** | Each named failure and the stall are fixed where they arise. A Windows skip, an `xfail`, a deselection, a raised limit or a slackened assertion is not a fix. If the cause is outside this repository and has no fix here, the package stops and the choice goes to the author | AY4 ("no waiver"); the steward's rules; decided by the plan |
| **D5 The two faults found by reading** | `.gitattributes` marks `src/nanopnp/gui/web/assets/katex/**` and `.../uplot/**` `-text`. `gui/web/server.py:_watch_input` stops the reloading supervisor with `_thread.interrupt_main(signal.SIGINT)`, not `os.kill(os.getpid(), signal.SIGINT)` | Grounding D5; decided by the plan |
| **D6 Where the three platforms are checked** | A pull request's CI stays on Linux. A package's `/np-ship` reads no platform leg. `/np-ship phase` dispatches `ci.yml` on the close's head and stops while a `platforms` leg is not `success`. This package's own done-criterion is one dispatch on its branch, three legs green | Ruled by the author at this plan, §8.2.50 AZ8, narrowing AY4; closes the Phase 6 plan's open decision 4 |
| **D8 The push gate skips the tests for prose since its last pass** | `gate.sh run` judges a change prose against the branch's last commit whose tree passed `run`, or against `main` before the first pass; `specification/history/holds-now.yaml` counts as prose, its one check moved from a Tier 1 test into `decisions.py --check`, which the gate and CI run on every change | Asked by the author at `/np-implement`: a plan pushed after code waited seven minutes for the whole suite. Decided by this session; tooling, no clause changes |
| **D7 The records** | REV-277 is set `fixed` with the names and causes; its "since 10 November" is corrected to run 621, 3 November. `CHANGELOG.md` gains `## [0.7.0-alpha.1]` | §8.4.6; `CONTRIBUTING.md`, *Versions and releases*; decided by the plan |

### Grounding

Facts at `2b1a468`, read from the code and from the runs through `mcp__github__*`.

**D1.**

- Run 614 (`773bb65`, 2 November) is the last push run on `main` whose Windows leg passed. Run 621 (`f1e54f0`,
  3 November), the first push after WP5.02 added `tests/tier1/test_gui_screens.py`, and every later push run, ends at
  the 40-minute limit. The nightly Windows legs meet 240 minutes (3.14) and 30 minutes (3.11 to 3.13, Tier 1 alone)
  where Linux and macOS take 3 to 5 minutes for Tier 1.
- Run 844's Windows leg (1,954 items) and run 839's 3.11 leg (1,758 items) each report all but 9 results; each shows
  one `F`, at result 620. Pytest printed no summary, so neither is named.
- `pytest-xdist` 3.8 with `--dist loadfile` reorders files by size: `test_gui_screens.py`, 149 items, the largest,
  goes first and alone to one worker of two. In it, the reloading test is followed by exactly 8 items.
- `ci.yml` dispatched without `full` takes mode `main`: `platforms` runs the per-push selection on the three
  platforms, then `nanopnp gui --selftest`. A dispatch's `ref` is a branch, not a commit.

**D2.**

- The local per-push selection, four cores, `-n auto --dist loadfile`: 1,812 passed, 142 skipped, 234 s; slowest
  46.2 s (`test_models.py::test_fr39_a_model_built_alone_keys_as_its_study_walk`, setup), then 41.0 s and 28.4 s.
- pytest-timeout: `timeout` ini key, `PYTEST_TIMEOUT`, `--timeout`, then the marker, which wins; `0` disables. The
  default method is `signal` where `SIGALRM` exists and `thread` on Windows; `thread` dumps the stacks and calls
  `os._exit(1)`, so xdist reports the worker crashed while running the named test and starts another.
- `src/` and `tests/` use no `SIGALRM`, `signal.alarm` or `setitimer`.
- `tests/conftest.py:pytest_collection_modifyitems` (`trylast`) already filters `nightly` items; the timeout marker is
  added there, to the kept items.
- `.github/actions/tier12/action.yml` runs `uv run pytest -rs -n auto --dist loadfile`, with `--nightly -m "(tier1
  or tier2) and slow"` first when `NIGHTLY` is true. `ci.yml:nightly-issue`'s condition reads
  `contains(needs.*.result, 'failure')`; a leg at its limit is `cancelled`.
- `.claude/hooks/gate.sh` runs `uv run pytest -q -rsfE -n auto --dist loadfile`; the ini key reaches it unchanged.

**D3.**

- `test_gui_screens.py:_start` starts `[sys.executable, *entry, "--no-browser", ...]` with `stderr=DEVNULL` and
  returns after `process.stdout.readline()`, unbounded. The fixtures `running` and `solved` close standard input and
  `process.wait(STOP_WITHIN_S)` without a kill; a `TimeoutExpired` leaves the server running.
- `gui/web/server.py:_serve_dev` binds no listening socket itself: uvicorn 0.54's `Config.bind_socket` binds without
  `listen`, so `_announce` connects only once the spawned worker listens. After `ANNOUNCE_WAIT_S` (60 s) it returns
  having printed nothing, and the supervisor keeps serving: `_start`'s read then never returns.

**D5.**

- `.gitattributes` marks `src/nanopnp/gui/web/assets/molstar/** -text` alone. `katex/katex.min.css` holds one LF and
  `uplot/uPlot.iife.min.js` two; a Windows checkout with `core.autocrlf` rewrites them
  ([knowledge 07/14](../../../knowledge/07-software-stack/14-a-windows-checkout-rewrites-the-bytes-a.md)), and
  `test_con09_the_vendored_libraries_are_unmodified` hashes the bytes against `NOTICE.md`. KaTeX came on 16 November,
  uPlot on 19 November, both behind the stall.
- `server.py:_watch_input` runs in a daemon thread of the supervisor process. On Windows `os.kill` with a signal other
  than `CTRL_C_EVENT` or `CTRL_BREAK_EVENT` calls `TerminateProcess` with that number as exit code: the supervisor
  exits 2 and its spawned worker is orphaned. uvicorn's `BaseReload.startup` installs `signal_handler` for `SIGINT`;
  `_thread.interrupt_main(signal.SIGINT)` runs it in the main thread on every platform (Python 3.10+).
- The reloading test asserts `process.wait(STOP_WITHIN_S) == 0` after closing standard input: on Windows it reads 2.

**D6.**

- `.claude/skills/np-ship/wp.md` §5 follows the steward; `.claude/skills/np-ship/phase.md` step 3 lists the close's
  confirmations, with no CI dispatch. `.claude/skills/steward/SKILL.md` describes `platforms` as running after a merge.

### Implementation details

**Item 1.** `uv add --group dev "pytest-timeout>=2.4"`, then `uv lock`. In `pyproject.toml`'s
`[tool.pytest.ini_options]` add `timeout = 600`. In `tests/conftest.py:pytest_collection_modifyitems`, after the
filter, for each kept item with a `nightly` or `slow` marker and no `timeout` marker,
`item.add_marker(pytest.mark.timeout(7200))`; name the two constants `PER_TEST_TIMEOUT_S = 600` (beside the ini key,
in a comment) and `LONG_TEST_TIMEOUT_S = 7200`. In `action.yml`, `run=(uv run pytest -rs --durations=20 -n auto
--dist loadfile)`. In `ci.yml:nightly-issue`, `if: always() && needs.changes.outputs.mode == 'nightly' &&
(contains(needs.*.result, 'failure') || contains(needs.*.result, 'cancelled'))`, and its `failed` filter selects
both results.

`_start` keeps its signature and return. It passes `stderr=` a `tempfile.TemporaryFile(mode="w+",
encoding="utf-8")` opened in `_start`; a daemon `threading.Thread` puts `process.stdout.readline()` on a
`queue.Queue`; `get(timeout=READY_WAIT_S)` with `READY_WAIT_S = 120`. On `queue.Empty`: kill, wait 10 s, read the
file's last 4,000 characters, and `pytest.fail(f"no ready line within {READY_WAIT_S} s from {command}: {tail}")`.
After the ready line `_start` closes its handle of the file; the server keeps its own. The fixtures' teardowns and each
test's `finally` call `process.kill()` after the bounded wait, as the contract test already does.

§7.6 gains `NOTE (a stalled test; WP6.01)`: every pytest run of the gate and of CI bounds each test, 600 s in the
per-push selection and 7,200 s for a `nightly` or `slow` test, so a hang fails naming its test; a leg cancelled at its
limit opens the nightly issue as a failed one does.

Commit, gate, push. Dispatch: `mcp__github__actions_run_trigger`, `run_workflow`, `workflow_id: ci.yml`, `ref:` the
branch, no inputs; confirm the run's head SHA. Poll `actions_get` `get_workflow_run` with waits of at most 240 s. From
the Windows leg's log (`get_job_logs`, `tail_lines: 400`) copy the `FAILED` lines, the crashed-worker line and the
slowest durations into item 1's Outcome, with the run's number.

**Item 2.** The two D5 edits. The reloading test then asserts exit 0 unchanged. For each other name item 1 found,
read the stack and the captured error, fix at the cause by D4, and give the cause in one line of the Outcome. Gate,
push, dispatch again as in item 1; repeat until the three `platforms` legs and their self-tests are green.

**Item 3.** `np-ship/phase.md` step 3 gains a confirmation: dispatch `ci.yml` on the close's branch, as item 1
does, and stop while a `platforms` leg is not `success`. The steward's `platforms` paragraph adds that a pull request
and a package's ship read no platform leg, and the close does (AZ8). REV-277's row reads `fixed`, its section gains
**Fixed** with the names, causes and run numbers. `CHANGELOG.md`: `## [0.7.0-alpha.1]` with *Fixed*: `nanopnp gui
--dev` stops on closed input on Windows; the vendored KaTeX and uPlot keep their bytes on a Windows checkout; each
item-2 fix a user meets; and *Changed* (development): each test bounded at 600 s.

### Work items

- [x] 1. f04c9a8 `pyproject.toml`, `uv.lock`, `tests/conftest.py`, `tests/tier1/test_gui_screens.py`,
  `.github/actions/tier12/action.yml`, `.github/workflows/ci.yml`, §7.6 (D1, D2, D3); done when the gate passes and
  the dispatched run's Windows leg ends with a summary naming its failures and the stall. **Executor:** main

  > **Outcome — the stall and the failures named.** [Run 851](https://github.com/willemsk/nanopnp/actions/runs/45035649973)
  > (dispatch at `05a4ee3`): ubuntu 8 min and macOS 10 min green; the Windows leg ended in 11 min 50 s, "4 failed,
  > 1797 passed, 152 skipped", no worker crashed and no test met 600 s. The stall is the predicted one:
  > `test_ver78_the_reloading_server_prints_its_line_and_stops_with_its_input`, "no ready line within 120 s", its
  > standard error empty. The failures: `test_con09_the_vendored_libraries_are_unmodified[katex]`
  > (`katex.min.css`) and `[uplot]` (`uPlot.iife.min.js`), as predicted; and, at result 620, not predicted,
  > `test_ver48_the_channel_axis_gates_fire` (`test_structure_axis.py:625`), the tilted wall's axis read 11.38°
  > against 12 ± 0.005°. Slowest: the reloading test 120.0 s, then 71.1 s (`test_sweep.py` setup) and 60.7 s.
- [ ] 2. `.gitattributes`, `src/nanopnp/gui/web/server.py`, and each file item 1's names lead to (D4, D5); done when
  a dispatched run on the branch has the three `platforms` legs and their self-tests green. **Executor:** main
- [ ] 3. Compaction checkpoint. **Executor:** main
- [ ] 4. `.claude/skills/np-ship/phase.md`, `.claude/skills/steward/SKILL.md`, `docs/project/review-findings.md`,
  `review-items.md`, `CHANGELOG.md`, `docs/plans/current.md` (D6, D7); done when the strict documentation build and
  `decisions.py --check` pass and the review says so. **Executor:** main
- [x] 5. 174b238 `.claude/hooks/gate.sh`, `.github/scripts/prose-only.sh`, `.claude/scripts/decisions.py`,
  `tests/tier1/test_written_architecture.py`, `CLAUDE.md` (D8), done first, at the author's request; done when a
  push of prose after a passing `run` skips the lock check, the types and pytest. **Executor:** main

### Verification

| Test | Tier | Identifiers | Oracle | Tolerance source | Command |
|---|---|---|---|---|---|
| `test_ver78_the_reloading_server_prints_its_line_and_stops_with_its_input` | 1 | VER-78 | Exit 0 within 10 s of closed input, on Windows | its clause | the dispatched run |
| `test_con09_the_vendored_libraries_are_unmodified[katex]`, `[uplot]` | 1 | CON-09 | Each file's sha256 in its `NOTICE.md`, on a Windows checkout | its clause | the dispatched run |
| The tests item 1 names | 1, 2 | theirs | Unchanged assertions, on the three platforms | their clauses | the dispatched run |
| Tiers 1 and 2, per-push selection | 1, 2 | AY4 | 0 failed on ubuntu, macOS and Windows, each under 40 min, with the self-test | §8.1's Phase 6 gate | `.claude/hooks/gate.sh run`; the dispatched run |

### Out of scope

- A pull request's CI on Windows or macOS, and a package's ship reading a platform leg (AZ8).
- The screens' tests in Chromium on Windows or macOS: the `platforms` legs install no browser (CON-13's row).
- The Windows leg's speed beyond its limit; the speed-up is WP6.17's (AZ6).

### Open questions

None. The one put to the author is ruled (AZ8).
