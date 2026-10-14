---
type: Library Behaviour
title: 12. The suite's BLAS threads buy nothing; parallelism has to come from workers
description: The suite's BLAS threads buy nothing; parallelism has to come from workers.
tags:
- software
- library-behaviour
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
---

## 12. The suite's BLAS threads buy nothing; parallelism has to come from workers **[tested: pending]** {#12-the-suites-blas-threads-buy-nothing-parallelism-has-to-come-from-workers}

Tiers 1 and 2 were measured on four cores, 923 tests, after the VER-36 fix. Serially the suite takes
6m10s whether or not the BLAS threads are pinned to one. Pinned, it uses half the CPU time
(6m07s of user time against about 12 min), so the threads were spinning, not computing: the systems
here are too small to split. Under `pytest-xdist`, `-n 4 --dist loadfile`, unpinned workers
oversubscribe the cores and the suite gets *slower* (7m20s, 26 min of user time). With
`OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS` and `MKL_NUM_THREADS` all set to 1 it takes 3m19s. CI and
the commit gate therefore run `-n auto --dist loadfile` with the three pinned, and the long pole is
`tests/tier2/test_stabilised_mode.py`, whose module fixture (146 s) cannot be split across workers
(`knowledge/06-numerics-fem/04-stabilisation.md#433-on-a-stable-element-pair-the-flow-terms-cost-an-order-and-20-the-time`).

Re-measured on 30 September 2026, four cores, 1504 tests in the default selection (tiers 1 and 2,
`not slow`, the GUI file apart). Before the changes below: **353 s wall, 1147 s of test time**. The
long pole was still `test_stabilised_mode.py` at 259 s, and six Tier-2 files each walked stages 2 and
3 of the prepared 2WCD (19.7 s and 12.2 s). Two changes, neither touching a weak form or a tolerance:

- the MMS sources are built with shared subexpressions (`knowledge/06-numerics-fem/04-stabilisation.md#433-on-a-stable-element-pair-the-flow-terms-cost-an-order-and-20-the-time`), which took
  that module from 259 s to 60 s;
- `tests/conftest.py`'s `seeded_2wcd` computes 2WCD's stages 1 to 3 once per session, under a
  `FileLock` in a directory every worker shares, and copies those artefacts into each test's own
  fresh store. The store is content-addressed, so the bytes are the ones the test's own walk would
  write. Tests that assert a *cold* computation (VER-55's build, the example executors, the VER-49
  budget) do not take the seed.

After both: **271 s wall, 852 s of test time**, every test passing. `-m tier2` on the command line
*replaces* the default `not slow` filter and pulls in the `slow` tests: the example-05 ClyA solve alone
is about 30 min on one core. Pass `-m 'tier2 and not slow'` to time what the gate runs.

`--dist loadfile` keeps each module's fixtures in one worker, so a module-scoped solve is paid once,
as it is serially. A failure that appears only under `-n` means a test depends on the order it runs
in, or on state another module leaves behind, and that is a real isolation defect.

One test measures wall time and therefore fails under xdist for a different reason.
`test_ver44_the_shipped_renderer_reaches_a_document_with_no_network` waits 60 s for a real
QtWebEngine page. On a 3-core macOS runner it passed twice under `-n auto` and then failed once
(run 113), in the window where the other two workers were in the heavy solver modules. That points
to Chromium's helper processes being starved of CPU. It is not proven, because macOS was not
reproducible from here. CI and the gate therefore run `tests/tier1/test_gui_widgets.py` serially and
alone. The wait and the assertion are unchanged.

Re-measured on 3 October 2026 for WP33, one core, `OMP_NUM_THREADS=1`, the same four-core
container, 1,781 tests: **1,508.9 s of test time before and 1,334.5 s after**; four workers under
`-n auto --dist loadfile`, 458 s and 394 s of wall clock. Example 07 alone is 312 s, cold by design.
What was learnt on the way, each measured:

- **Profile before sharing.** In VER-58's grounded-sphere test the mesh was 3 s and the lattice
  0.08 s of a 21 s solve; the closed-form oracle at 257,750 quadrature points was 19.4 s. A test's
  own oracle can be the cost, and evaluating it once per mesh rather than once per deposit order is
  sharing, not weakening it. A periodic trapezoid rule over an integrand even in `θ` can be summed on
  `[0, π]` with interior points doubled: the same rule, 7× cheaper there, equal to 9.5 × 10⁻¹⁶.
- **On 2WCD, stage 4 is 0.41 s and the C-alpha registration 3 ms; the default-size mesh is 8.2 s.**
  Seeding to the mesh is what saves time; seeding to the contour saves nothing.
- **An NGSolve mesh pickles to the bit, and a `.vol` does not**: the text format moved the ClyA
  reference mesh's vertices by up to 5.6 × 10⁻¹⁷ nm, enough to change its geometry digest.
- **Under the serial order, the first file to ask for a session seed carries it** (`charge_2wcd`,
  99.9 s of setup). Read a per-file time with that in mind; between two baseline runs a single
  file's time also varied by up to 20 %.
- **`copy.deepcopy` and per-call `TypeAdapter` construction** were half of `build_plan` on the
  3,675-member sweep (12.3 s → 7.0 s once removed, WP33 D12).
- **Parsing the correction YAML dominated planning until it was cached by text.** PyYAML's pure-Python
  parser was 92 % of planning the 3,675-point reference sweep (29.4 s against 4.3 s cached); the cache
  is keyed on the file text, not on path and mtime, so an edit is re-parsed however quickly it was
  written (source: `materials/corrections.py`, `_parse`). **[tested: pending]**
- **Where the suite's time goes** **[tested: pending]**, after WP33. The 54 `extended` tests are the
  executed examples and the 2WCD walks. They are 3 % of the tests and 59 % of the test time: the
  development selection without them is 542.9 s of test time and 168 s of four-worker wall, against
  1,334.5 s and 394 s with them. Deleting duplicated or history-pinning tests recovered about 1 s.
  A walk is slow because it composes the stages, not because it repeats a check.
- **pytest: a custom option, not `addopts -m`, for a selection a named file should override.**
  `--extended` is read in the root conftest's `pytest_collection_modifyitems`, which keeps an
  `extended` item whose file is named on the command line. A `-m` in `addopts` would deselect it
  even then, and the user would have to restate the whole marker expression.

### 12.1 Test-impact selection was built, measured and removed **[tested: pending]** {#121-test-impact-selection-was-built-measured-and-removed}

WP43 built a recorder (`sys.monitoring` `PY_START`, `DISABLE` after the first hit, re-armed per
test) and a selector for the commit hook; WP44 deleted both (§8.2.11 L2). Recording cost about 1 %
(four shared cores, `-n auto --dist loadfile`, Python 3.12.3, 2,129 tests: 239.8 s without and
240.0 s with it; coverage's per-test contexts cost +83 %). Selection did not pay: most past commits
fell back to the whole development selection, and the recorder, selector and map were about 1,400
lines of code and test. What stays true:

- **A warm `functools` cache hides a dependency from every test but the first**, so a recording of
  what a test touched must empty the caches first (`validation/modularity.py` caches its parse of
  every module).
- **A throwaway index must keep the real index's mtime.** Git re-reads an entry as racy only when
  the file is no older than the index file, and under `core.checkStat=minimal` it compares only
  whole-second mtimes and sizes. Copied with a fresh mtime, the index hid a same-size edit made in
  its second, and `git add -A` wrote the old tree. Copy it with `cp -p`; `gate.sh` does.
- **`sys._getframe` raises an audit event of its own**, and a `co_filename` can be `<frozen runpy>`
  or `<string>`, which `realpath` resolves against the working directory.

### 12.2 Where the time goes on 3.14, and coverage's `sysmon` core **[tested: pending]** {#122-where-the-time-goes-on-314-and-coverages-sysmon-core}

Measured for WP43 D8 on 12 October 2026: CPython 3.14.6, coverage 7.15.4, pytest-cov 7.1.0, four
cores shared with another agent's runs, `-n 4 --dist loadfile`, BLAS threads 1,
`NPY_DISABLE_CPU_FEATURES` at the X86_V3 cap, the GUI file left out, tree `f2e48e9` plus the
ordering conftest (the order's re-measurement, below, on a quiet machine). Each figure carries the 1-minute load average at its start and end.

- **Per-file time**, from a `--durations=0` log of the development selection with `--extended`
  (2,176 passed; 510 s wall, load 0.5 rising to 3.9): 1,849 s of test time in 141 files, of which
  the 16 wholly `extended` files are 1,070 s and the development selection 778 s. Example 07 alone
  is 416 s, the 2WCD VAL-06 and charge walks 128 s and 125 s. No file mixes `extended` and
  development tests. The longest development file is 60.5 s (`test_exclusion_stern.py`); the median
  file 2.0 s.
- **Longest-first order is inert under xdist's defaults.** pytest-xdist 3.8's `loadfile` (a
  `LoadScopeScheduling`) re-sorts the files by their number of tests, most first, unless
  `--no-loadscope-reorder` is passed (`--loadscope-reorder` defaults to true), so the collection
  order only breaks ties, and example 07, which holds few tests, still starts late. Re-measured on
  a quiet machine (WP43 item 10, tree `4d9c306`, load under 1 at the first start; the same flags,
  `--extended`, no coverage), back to back: **534 s and 512 s** in the default schedule with the
  order, **477 s** without a duration record (path order, then re-sorted), and **474 s** with
  the order and `--no-loadscope-reorder`. The spread between the two like runs, 22 s, is as large
  as any difference between schedules; every run sits on example 07's floor, 421 to 477 s alone, so
  no order can gain more than the minute above it. The same 2,213 tests pass in each. The earlier
  measurement under another agent's load (937 s ordered against 830 s in path order) is noise of
  the same kind.
- **`COVERAGE_CORE=sysmon` against `ctrace`**, the development selection under
  `--cov=src/nanopnp --cov-branch`, 2,118 passed: **292 s** (load 4.4 to 6.7) against **511 s**
  (6.7 to 7.8). The two XML reports are byte-identical once the `timestamp` attribute is removed:
  21,879 lines and 5,058 branches valid, 18,888 and 3,944 covered. **coverage 7.15 already
  defaults to `sysmon` on CPython 3.14 and later** (`coverage/env.py`, `SYSMON_DEFAULT`), with
  branch coverage, so the gate and CI use it without configuration; pinning `core` in
  `pyproject.toml` would make every coverage run on 3.11 to 3.13 warn and fall back.
- **pytest-cov's `no_cover` marker stops coverage for the call phase only**
  (`pytest_runtest_call`): a fixture's setup is still measured. The root conftest puts it on every
  `extended` item, so the walks no longer pay the tracer in their calls, where their time is.

