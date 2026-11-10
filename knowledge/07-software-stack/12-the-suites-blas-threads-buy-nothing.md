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
sources:
- id: wp33-plan
  resource: docs/plans/phase-3/wp33-test-durations.md
  title: WP33 test durations plan (suite timing and BLAS thread measurements)
- id: wp43-plan
  resource: docs/plans/phase-4/wp43-development-loop.md
  title: WP43 development loop plan, D8 (3.14 timings and coverage sysmon)
- id: wp44-plan
  resource: docs/plans/phase-4/wp44-simplify-the-loop.md
  title: WP44 simplify the loop plan (test-impact selection removal)
tested_with:
  pytest: 9.1.1
  pytest-xdist: 3.8.0
  filelock: 3.32.3
  pyyaml: 6.0.3
verified:
- by: process:arithmetic
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_corrections.py::test_fr16_an_edited_correction_file_is_read_again_in_the_same_process
  at: '2026-10-16T00:00:00Z'
---

## 12. The suite's BLAS threads buy nothing; parallelism has to come from workers **[verified][^wp33-plan]** {#12-the-suites-blas-threads-buy-nothing-parallelism-has-to-come-from-workers}

Measured on four cores over Tiers 1 and 2, then 923 tests. Serially the suite takes 6m10s whether
or not the BLAS threads are pinned to one. Pinned, it uses half the CPU time, so the threads were
spinning, not computing: the systems here are too small to split. Under `pytest-xdist`,
`-n 4 --dist loadfile`, unpinned workers oversubscribe the cores and the suite gets *slower* (7m20s).
With `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS` and `MKL_NUM_THREADS` all set to 1 it takes 3m19s.
CI and the commit gate therefore run `-n auto --dist loadfile` with the three pinned.

`--dist loadfile` keeps each module's fixtures in one worker, so a module-scoped solve is paid once,
as it is serially. A failure that appears only under `-n` means a test depends on the order it runs
in, or on state another module leaves behind, and that is a real isolation defect.

`tests/conftest.py`'s `seeded_2wcd` computes 2WCD's stages 1 to 3 once per session, under a
`FileLock` in a directory every worker shares, and copies those artefacts into each test's own fresh
store. The store is content-addressed, so the bytes are the ones the test's own walk would write.
Tests that assert a *cold* computation (VER-55's build, the example executors, the VER-49 budget) do
not take the seed.

`-m tier2` on the command line *replaces* the default `not slow` filter and pulls in the `slow`
tests. Pass `-m 'tier2 and not slow'` to time what the gate runs.

`tests/tier1/test_gui_widgets.py` runs serially and alone. A test that waited 60 s for a real browser
page passed twice under `-n auto` on a 3-core macOS runner and then failed once, while the other two
workers were in the heavy solver modules; Chromium's helper processes starved of CPU is the likely
cause, not proven.

What profiling the suite taught, each measured (WP33, 3 October 2026):

- **Profile before sharing.** In VER-58's grounded-sphere test the mesh was 3 s and the lattice
  0.08 s of a 21 s solve; the closed-form oracle at 257,750 quadrature points was 19.4 s. A test's
  own oracle can be the cost, and evaluating it once per mesh rather than once per deposit order is
  sharing, not weakening it. A periodic trapezoid rule over an integrand even in `θ` can be summed on
  `[0, π]` with interior points doubled: the same rule, 7× cheaper there, equal to 9.5 × 10⁻¹⁶.
- **On 2WCD, stage 4 is 0.41 s and the C-alpha registration 3 ms; the default-size mesh is 8.2 s.**
  Seeding to the mesh is what saves time; seeding to the contour saves nothing.
- **An NGSolve mesh pickles to the bit, and a `.vol` does not**: the text format moved the ClyA
  reference mesh's vertices by up to 5.6 × 10⁻¹⁷ nm, enough to change its geometry digest.
- **Under the serial order, the first file to ask for a session seed carries it.** Read a per-file
  time with that in mind; between two like runs a single file's time also varies by up to 20 %.
- **`copy.deepcopy` and per-call `TypeAdapter` construction** were half of `build_plan` on the
  3,675-member sweep (12.3 s → 7.0 s once removed, WP33 D12).
- **Parsing the correction YAML dominated planning until it was cached by text.** PyYAML's pure-Python
  parser was 92 % of planning the 3,675-point reference sweep (29.4 s against 4.3 s cached); the cache
  is keyed on the file text, not on path and mtime, so an edit is re-parsed however quickly it was
  written (source: `materials/corrections.py`, `_parse`). **[tested: tests/tier1/test_corrections.py::test_fr16_an_edited_correction_file_is_read_again_in_the_same_process]**
- **A walk is slow because it composes the stages, not because it repeats a check**: the executed
  examples and the 2WCD walks were 3 % of the tests and 59 % of the test time.

### 12.1 Two traps a per-test recording meets **[verified][^wp44-plan]** {#121-test-impact-selection-was-built-measured-and-removed}

A recorder of what each test touched was built and removed (§8.2.11 L2). What it taught stays true:

- **A warm `functools` cache hides a dependency from every test but the first**, so a recording of
  what a test touched must empty the caches first (`validation/modularity.py` caches its parse of
  every module).
- **A throwaway index must keep the real index's mtime.** Git re-reads an entry as racy only when
  the file is no older than the index file, and under `core.checkStat=minimal` it compares only
  whole-second mtimes and sizes. Copied with a fresh mtime, the index hid a same-size edit made in
  its second, and `git add -A` wrote the old tree. Copy it with `cp -p`; `gate.sh` does.
- **`sys._getframe` raises an audit event of its own**, and a `co_filename` can be `<frozen runpy>`
  or `<string>`, which `realpath` resolves against the working directory.

### 12.2 Collection order under xdist's `loadfile` **[verified][^wp43-plan]** {#122-where-the-time-goes-on-314-and-coverages-sysmon-core}

pytest-xdist 3.8's `loadfile` (a `LoadScopeScheduling`) re-sorts the files by their number of tests,
most first, unless `--no-loadscope-reorder` is passed, so the collection order only breaks ties.
Measured back to back on a quiet machine (12 October 2026), every schedule sat on the longest file's
floor and the spread between two like runs, 22 s, was as large as any difference between schedules:
no collection order buys time.

[^wp33-plan]: `docs/plans/phase-3/wp33-test-durations.md` (suite BLAS thread and extended-test timing measurements).
[^wp43-plan]: `docs/plans/phase-4/wp43-development-loop.md`, D8 and item 10 (CPython 3.14.6 suite timings and the collection order under xdist).
[^wp44-plan]: `docs/plans/phase-4/wp44-simplify-the-loop.md` and `SPECIFICATION.md` §8.2.11 L2 (test-impact selection measurements and removal).
