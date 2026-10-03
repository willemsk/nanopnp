# WP33 — The test suite's duration, cut without losing a check

**Status: planned, not started.** Written 3 October 2026, beside the WP32 plan and after WP31 merged
on `main` (`35524c1`). WP33 starts after WP32 merges. WP32 adds example 07, which will be the
longest Tier 2 file, and it changes three test files this package also touches. WP33 inherits:

- the four tiers and their markers, and `slow` deselected by default (`pyproject.toml`);
- CI's `-n auto --dist loadfile`, under which a file is the unit of scheduling (`.github/workflows/ci.yml`);
- the session fixtures of `tests/conftest.py`, shared across xdist workers through a `FileLock` and
  a `READY` marker (WP27 D17; commit `35524c1`).

This is a work package of the [Phase 3 plan](phase-3-charge-pipeline.md), added at the author's
request on 3 October 2026, ahead of the phase close. It is maintenance, not a §8.1 increment.
`SPECIFICATION.md` governs, and identifiers below are pointers into it. **Spec amendment, made in
this commit:** a §7.6 NOTE on a gated test's runtime, which states the rule every decision below
follows.

## Execution brief

### Scope

The author asked for every test to be reviewed, to cut its duration without losing its core
function. Tiers 1 and 2 took **1,420 s of test time serially** (23 min 59 s wall clock, one core,
3 October 2026, at `35524c1`; [Design §1](#1-the-baseline)). Tier 2 was 1,147 s of that and Tier 1
273 s. Twenty files of 124 carry 78 % of it. On CI the tier 1–2 step took 4.6 to 11.5 min per leg.

Every file was surveyed for what it computes, what it asserts, and why its expensive settings were
chosen. Most of the cost is the same work done twice: inside a file, across files, or behind a lock
another worker is waiting on. The rest is resolution that only a logged number needs. This package
removes that, file by file, under one rule (D1). Each change is measured before and after.

Touches §7.6 (the new NOTE), and the tests of VER-01, VER-02, VER-10, VER-18, VER-29, VER-34,
VER-36, VER-37, VER-42, VER-46, VER-48, VER-49, VER-52, VER-53, VER-55, VER-58, VER-59, VER-60,
VAL-05, VAL-06, NUM-12, NUM-14 and NUM-17. No requirement's assertion changes. **The brief is about
1,900 words, over its 1,200 target**, because each file's decision needs its own reason.

### Pointers

| Need | Read |
|---|---|
| The rule | §7.1; §7.6 and the NOTE this commit adds; `CLAUDE.md` *Testing* |
| The shared fixtures | `tests/conftest.py` `prepared_2wcd`, `seeded_2wcd`, `protonated_2wcd`, `seeded_protonated_2wcd`; `.knowledge/07` §12 on the seed and on cold-by-design tests |
| The baseline | [Design §1](#1-the-baseline); the serial command under *Verification* |
| Each file's constraints | The docstrings and constant comments the decisions cite. Each records a measured reason for its setting, and that reason binds |

### Decisions

| # | Decision | Choice | Why/source |
|---|---|---|---|
| D1 | The rule | A gated test may get cheaper in four ways only. (a) It **shares identical work**: the same inputs computed once. (b) It **drops work nothing asserts**, where the result only reaches a log. (c) It **coarsens a discretisation** where every gate it carries is measured to pass at the coarser setting with at least 3× headroom. (d) It **is split** across files, so the scheduler can run its parts at once. Never allowed: loosening a tolerance, weakening an oracle, warming a test that asserts a cold computation, or leaving a gated identifier without a per-push test. A test moves to `slow` only if another per-push test gates the same claim on the same kind of input. Written as a §7.6 NOTE in this commit | The author's "without losing their core function", made checkable. (c)'s 3× is the headroom the suite already asks of a gate that must be able to fail (WP29 D8's "half the tolerance" is 2×; 3× allows for platform spread) |
| D2 | The 2WCD seed | Two changes. **First, protonation stops waiting for stages 2–3.** `protonated_2wcd` depends on a stage-1 seed instead of `seeded_2wcd`, so PROPKA (about 64 s) runs while another worker computes the density and the reduction (about 32 s). **Second, the seed runs on to stage 4 and the 0.15 M default-size mesh**: the contour, the C-alpha registration, the region and the mesh, once. The modules whose cases resolve to those keys copy them, and assert them `cached` as they now assert stages 1–3. That removes the stage-4 walk and registration from seven modules, and a default-size mesh from each module whose key matches | Lever (a). The locks currently serialise the first ~96 s of every 2WCD file behind one worker. Protonation reads only stage 1 (`charge/protonation.py`). The registration is computed identically in `val05`, `pipeline`, `exclusion`, `charge`, `val06`, `gui_geometry` and `contour_2wcd`. Which mesh keys match is the implementer's to assert, not to assume |
| D3 | Cold by design | `test_examples_06`, `test_examples_07` (WP32), `test_gui_geometry_2wcd`'s spawned build, and VER-49's budget **stay cold**. They take no seed | Each asserts a cold walk (`.knowledge/07` §12; VER-46 runs a README verbatim; VER-55 asserts `not event.cached`) |
| D4 | `test_charge_potential.py` (137 s, no fixtures) | **Share the mesh and the lattice.** The mesh for each `(r_i, near)` is built once and serves both deposit orders. The lattice for each `r_i` is summed once, because it depends on neither `near` nor the order. Then **split** the two `r_i` parametrisations into two files, so neither is a 100 s floor. Levels, `H`, `ARC_NM` and the rate gates are unchanged. The 0.2 nm level stays: VER-58 asserts a rate under two halvings | Levers (a) and (d). Today each of 12 solves rebuilds its mesh and re-sums a lattice at `H` = 0.0025 nm (`_solve_error`). The `H` and `ARC_NM` comments record why both are fine, and neither moves |
| D5 | `test_gui_geometry_2wcd.py` (61 s) | The build, both edits and the re-run go to `numerics.mesh.size_scale` 4. Stages 1–3 stay cold | Lever (c). VER-55's claims (cold build, `assess` equal to the gate record, null edit keeps the content hash, moved vertex moves it) are about the shell's plumbing and the stage-4 gate, and none depends on element size. The three default-size meshes are about 25 s. The default-size 2WCD mesh stays gated by `test_pipeline_2wcd` (VER-53) |
| D6 | `test_exclusion_stern.py` (59 s) | **Measure the three gates at `size_scale` 2. Adopt it only if each clears D1's 3×.** The comment at :228 records 3.6 × 10⁻³ at `size_scale` 2 against a 10⁻² gate (2.8×), which already fails the bar on one gate. So this is expected to stay at the default sizes, and the Outcome says which | Lever (c), honestly bounded. A gate at 2.8× headroom is not one to coarsen |
| D7 | `test_exclusion_2wcd.py` (84 s) | The shell-mesh tests seed from `seeded_2wcd` alone. Only the charged walk takes the protonated seed. **Split** that walk into `test_exclusion_2wcd_walk.py`. The 3 M mesh stays: it is the real-structure regression of `11bc2c8`, and the synthetic test covers only the mechanism | Levers (a) and (d). Today the whole module waits on PROPKA for one test |
| D8 | `test_stabilised_mode.py` (56 s) | `_climb(0.2, "reference", −0.05)` becomes a module fixture read by NUM-14's test and by the current-convergence loop, which climbs the identical case. `COARSE_PORE.generate` is memoised per size. `unstabilised_errors` stays: the withheld-source and comparison tests need VER-18's meshes in this module (`MMS_SIZES_NM` comment) | Lever (a) |
| D9 | `test_solution_state.py` (40 s, Tier 1) | One mesh per module. The `solved` fixture is produced by `SolveStage.run` and restored from its payload, so the wiring test reads it instead of climbing a third time. The `supg` climb stays | Lever (a). The round-trip tests then exercise the stage's own state, which is at least as strong. The module's one-mesh comment (`WALL_H_NM`) already argues the mesh |
| D10 | The ClyA reference mesh | Meshed once per session at the default size, under a `FileLock`, and read by `test_probe_grid`, `test_charge_conservation`, `test_reference_geometry` and `test_region_reference`'s comparison mesh. Each test then asserts on its own copy | Lever (a). It is built five times today, three of them in `test_region_reference` |
| D11 | Stage 1 on the 26,844-atom dodecamer | `test_structure_stage.py` aligns it once into a module store. Tests that need a miss copy the store and remove the entry, and tests that need a hit copy it as it is | Lever (a). About eight tests align the same file in fresh stores |
| D12 | The 3,675-member reference sweep | **Profile `build_plan` first.** If one hotspot accounts for most of the 4.4 ms per member (for example, re-validating the base document per member), fix it in `sweep/`, with VER-36's assertions unchanged. Otherwise leave it. `test_examples_plan` runs the same plan verbatim as a subprocess, and stays | Lever (a) inside the product. A user's sweep of the same size waits the same 16 s, so a fix helps them too. Not taken blind |
| D13 | `test_density.py`'s VER-49 round trip (21 s, Tier 1) | **Profile first.** If writing the five interchange formats of the whole map dominates, the formats are exercised on the stage's map cropped to its occupied box, and the header and lattice assertions keep their full form. Otherwise unchanged | Levers (a) and (b), conditional on measurement |
| D14 | Files kept as they are | `test_val06_2wcd` (the P2 and P3 deposits and three APBS runs are each asserted; it benefits from D2), `test_sweep` (warm against cold needs all five climbs), `test_examples_01`–`03` (README verbatim; `reproduce` is QR-08's oracle), `test_val06_ring` (each broken construction must fail on its own), `test_electrophoretic_mobility` (κa = 16.5 is the stated budget limit), `test_current_routes` (the regime points are the claims) and `test_pipeline_2wcd` | Their costs are their claims. Listed so that nobody re-reviews them |
| D15 | Targets | Measured on the same machine, serially, against the baseline re-measured on WP32's merge commit. **At least 180 s of serial tier 1–2 test time saved**, which is about 13 % of today's 1,420 s; 240 s if D12 or D13 lands. **No file except the cold examples over 90 s.** Tier 1 under 220 s. The CI legs' times are recorded too. Missing a target is recorded as an Outcome. It is never a reason to weaken a test | An absolute saving, because example 07 will add about 420 s of cold run to the baseline that no lever here may touch (D3). The baseline must include it to be honest. The estimate of the savings is in [Design §2](#2-where-the-time-goes-and-what-each-decision-saves) |

### Work items

1. **Baseline** on WP32's merge commit: the serial command below, keeping `durations.xml`
   ([Design §1](#1-the-baseline)).
2. **`tests/conftest.py`** (D2, D10): the stage-1 seed, protonation on it, the seed extended to the
   mesh, and the reference-mesh session fixture. Read `.knowledge/07` §12 first.
3. **The files** (D4–D9, D11), in the order of D's numbering. Each change is followed by that file's
   serial time, before and after, in the Outcomes.
4. **The conditionals** (D6, D12, D13): profile, then take or leave, with the evidence.
5. **Re-measure** (D15). Then record the result in `.knowledge/07` §12 (measured facts about the
   suite), the phase plan's WP33 entry, `current.md`, and `CHANGELOG.md` under `0.4.0-alpha.8`.

### Verification

| Check | Tier | Identifiers | Assertion | Tolerance |
|---|---|---|---|---|
| Every changed file | its own | as listed in Touches | Every assertion and tolerance is unchanged. The diff of each file's `assert` lines is empty except for `cached` assertions added by D2 and D10 | exact |
| `test_charge_potential_*.py` | 2 | VER-58 | The rates and errors equal the pre-change run's to 10⁻¹². It is the same computation, shared | 10⁻¹² |
| `test_solution_state.py` | 1 | VER-34 | The bit-for-bit round trip passes on the stage's own state | exact |
| The seeds | 2 | — | A module that copies the extended seed asserts each seeded stage `cached`. A cold-by-design test asserts none is | exact |
| The suite | 1, 2 | VER-45 | `uv run pytest` green, and the gate | — |
| The targets | — | — | D15, recorded | — |

Baseline and re-measure command, one core, as Design §1 ran it:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 QT_QPA_PLATFORM=offscreen \
  uv run pytest -q --durations=60 --junitxml=durations.xml -o junit_duration_report=total
```

Then the parallel form CI runs (`-n auto --dist loadfile`), with its wall clock recorded.

### Out of scope

| Item | Owner |
|---|---|
| Tier 3 and `slow` tests | Not gated, so not a push cost |
| Example 07's own runtime | WP32 D9 |
| A different xdist distribution mode | Rejected: `loadfile` is what lets module fixtures run once, and D4 and D7 split files instead |
| Speeding up the solver or the mesher | Not this package. D12 is the only product change, and it is conditional |

### Open questions

None blocking. D6 is expected to keep the default sizes, and says so.

## Design

### 1. The baseline

`uv run pytest -q --durations=60 --junitxml=…`, serial, one core, `OMP_NUM_THREADS=1`, at
`35524c1`, 3 October 2026 **[tested]**. 1,760 passed, 17 skipped and 41 deselected in 23 min 55 s.
Test time was 1,420 s: Tier 2 1,147 s and Tier 1 273 s, over 124 files. The five slowest files
are 39 % of it, ten are 58 %, twenty 78 % and thirty 87 %.

| File | s | Where the time is |
|---|---|---|
| `tier2/test_charge_2wcd.py` | 141.6 | 141 s setup: the session seed and protonation (about 96 s), then its own walk to stage 7 at default sizes |
| `tier2/test_charge_potential.py` | 137.4 | 12 solves, each rebuilding its mesh and re-summing a lattice |
| `tier2/test_val06_2wcd.py` | 130.4 | 130 s setup: the seed and protonation, P2 and P3 deposits, three APBS runs |
| `tier2/test_exclusion_2wcd.py` | 84.3 | the charged walk 49 s, the 3 M mesh 20 s, setup 14.5 s |
| `tier2/test_examples_06_pdb_to_mesh.py` | 64.8 | a cold walk to two meshes (by design) |
| `tier2/test_gui_geometry_2wcd.py` | 61.5 | a cold build and three default-size meshes |
| `tier2/test_exclusion_stern.py` | 58.7 | one default-size walk to a solve |
| `tier2/test_stabilised_mode.py` | 56.4 | MMS sequences, ten climbs, one of them duplicated |
| `tier2/test_sweep.py` | 45.8 | five ladder climbs, warm and cold |
| `tier2/test_examples_03_iv_sweep.py` | 44.1 | six solves through the README |
| `tier1/test_solution_state.py` | 40.0 | three ladder climbs on one case |
| `tier2/test_val05_2wcd.py` | 39.0 | two frozen-case solves, and the stage-4 walk and mesh |
| `tier2/test_pipeline_2wcd.py` | 32.3 | the charged walk 21.8 s, the default-size mesh 9.8 s |
| `tier1/test_density.py` | 31.2 | VER-49's round trip 20.9 s |
| `tier2/test_region_reference.py` | 29.1 | three reference meshes |

On CI at the same commit, the tier 1–2 pytest step took 10 min 49 s on Linux 3.12 (with
coverage), 11 min 28 s on Windows, 11 min 19 s on macOS, and 7 min 30 s, 4 min 38 s and 8 min 16 s
on Linux 3.11, 3.13 and 3.14. Under `--dist loadfile` a leg can finish no sooner than its longest
file, and the shared 2WCD seed holds every 2WCD file for its first ~96 s, behind one worker.

### 2. Where the time goes, and what each decision saves

These are estimates from the survey, before any measurement. The Outcomes replace them.

| Decision | Estimated saving (serial) | Effect on a CI leg |
|---|---|---|
| D2 | 30–50 s (stage 4 and the registration ×7; the matching meshes) | ~30 s off the lock-held critical path |
| D4 | 50–80 s | the 137 s floor becomes two files of about 30 s |
| D5 | ~20 s | — |
| D7 | — | the shell tests no longer wait on PROPKA |
| D8, D9, D11 | 20–30 s together | — |
| D10 | 20–25 s | — |
| D12, D13 | 0–35 s, if taken | — |

That is about 160–240 s of 1,420, or 11–17 %, before the conditionals, which is where D15's 180 s
comes from. Its 240 s needs D12 or D13 to land. If the measured saving falls short, D15 records the
shortfall rather than reaching for a lever D1 forbids.
