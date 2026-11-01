# Code review 024: architecture review after WP57, checked against the code

Supplied by the author on 1 November 2026: an architecture review rendered as HTML and an execution plan, both written
against `main` at `8a3488cd22df644bf5c50d78b36b0a3bddae9733` (after WP57) with the Qt shell excluded, which the browser
workbench replaces (§8.2.12 M3; §8.2.17). They are kept verbatim beside this report:
[architecture-review.html](CODE_REVIEW_024/architecture-review.html) (six candidates) and
[execution-plan.md](CODE_REVIEW_024/execution-plan.md) (decisions D1 to D6, twenty-one work items).

Checked by the `/np-plan amend 4` session against `main` at `dd45e59`, which adds WP58 to the reviewed tree. Every claim
below was read in the code; the costs marked *measured* were timed on that tree with `Case.cylinder(concentration_M=1.0,
bias_V=0.1)`. The author ruled what is taken in §8.2.27 AC1 to AC6.

Status: completed. Taken into WP59 (AC1, AC2, AC5) and WP60 (AC6); carried as REV-170 (AC3) and REV-171 (AC4).

## Verdicts

| # | Claim (source) | Verdict | Evidence | Ruling |
|---|---|---|---|---|
| 1 | `Session.run` reads `Case._text`, `_path`, `_base` (D1; candidate 2) | **Holds** | `api/session.py:120-123` | WP59 (AC1) |
| 2 | `Case.__hash__` disagrees with `__eq__` (D1) | **Holds, narrower than stated** | `bias_V=-0.0` and `0.0` compare equal and hash apart (*measured*). The cross-process remark does not apply: Python's hash contract is per process | WP59 (AC1) |
| 3 | `Case.load` keeps `_path` unresolved (D1) | **Holds** | `api/case.py:62`; `_base` is resolved, `_path` is not | WP59 (AC1) |
| 4 | `Case.with_` substitutes and validates twice (D1) | **Holds, cost negligible** | The second pass runs only when a relative path is rebased; `with_` costs 1.0 ms per edit (*measured*) | WP59, as part of the seam, if it falls out of item 1 (AC1) |
| 5 | `cylinder` and `from_structure` load the corrections twice (D1) | **Holds, cost negligible** | `api/case.py:291` after `_electrolyte` | WP59 (AC1) |
| 6 | Relative-path rebasing is split across four places (D1) | **Holds** | `api/case.py` `_rebased_paths`, `pipeline/case.py`, `io/case_paths.py`, `api/sweep.py` | WP59 judges at its plan whether the seam absorbs them (AC1) |
| 7 | CLI `check`, `explain`, `inspect` import `pipeline.case` and `pipeline.run` (candidate 6) | **Holds** | `cli/__init__.py:289-292, 815-817, 871` | WP59 (AC1) |
| 8 | Newton keeps a NaN trial residual as a forced step (D3) | **Holds, milder than stated** | `numerics/newton.py:245-249` takes it deliberately. Under PNP the positivity gate (`not value > 0.0`) refuses the NaN state at the next check; under PB no gate does, and the solve runs to 100 iterations before `NewtonDivergenceError`. A forced step never counts towards convergence, so no NaN is returned as converged | WP59, with NUM-16's NOTE (AC2) |
| 9 | `wall_statistics` raises a raw `ValueError` on an empty wall (D5 b) | **Holds** | `mesh/generate.py:91-93`, `np.argmax` of an empty array. `target_nm` is schema-validated | WP59 (AC1) |
| 10 | `np.nan_to_num` turns `+inf` SICN into `1.8e308`, passing the gate (D5 a) | **Does not hold** | SICN and gamma are bounded by 1 by construction (`2 det J ≤ ‖J‖²_F`; the inradius ratio); non-finite vertices give NaN, mapped to 0, which fails the gate | Not taken |
| 11 | The idealised region drawing omits the cis and trans reservoir outlines (D2) | **Does not hold** | Neither branch of `plot/data.py:region_drawing` draws reservoirs; the branches differ only in `z_extent_m` | Not taken |
| 12 | Six `isinstance(…, IdealisedRegionRecord)` branches (candidate 1) | **Five outside the GUI** | `mesh/generate.py` ×2, `mesh/ingest.py`, `plot/data.py`, `cli/__init__.py`; the sixth, `gui/geometry.py`, leaves with Qt | REV-170, Phase 5 (AC3) |
| 13 | `CylinderPore` and `CylindricalPoreGeometry` duplicate dimensions; `name_edges` sets `maxh` in `geometry/` (D2) | **Holds** | `geometry/pore.py:83`; `mesh/primitives.py` | REV-170, Phase 5 (AC3) |
| 14 | PB's residual is rebuilt after the solve, breaching QR-13 (D3; candidate 3) | **Partly** | The weak form is written once, `nonlinear_pb_residual`; `physics/models.py:1393` builds a second unassembled `BilinearForm` from `self.residual_form`. No form is written twice; the cost is one symbolic build | REV-171, Phase 6 (AC4) |
| 15 | The sweep planner can retain each point's solve key, so warm starts skip re-resolution (D4; candidate 4) | **Does not hold as proposed** | A generated mesh's solve key depends on the parent's stage-6 artefact, which exists only after the parent runs; `api/sweep.py:247-250` records the bug a bare-case key caused. A resolve costs 1.5 ms (*measured*) against a solve of seconds to minutes. Memoising the correction loads holds but saves milliseconds | REV-171, Phase 6 (AC4) |
| 16 | `NondimensionalCoefficients` rebuilds symbolic trees per species; boundary checks repeat in four modules (D4; candidate 5) | **Holds, unmeasured** | `post/qoi.py`, `post/indicator.py`, `post/reaction_flux.py`, `post/forces.py`, `physics/distance.py` | REV-171, Phase 6 (AC4) |
| 17 | Argument checks: `locate` `cell_nm > 0`, `reduce_map` `n ≥ 1`, uniform contour axes, `resample` zero-length loop (D5 c to e) | **Hold, internal callers only** | Each value comes from a schema-validated field or a caller in the same subpackage | REV-171, where a check guards a public entry (AC4) |
| 18 | Efficiency: `enforce_spacing` `O(n²)`, the density slab loop, the per-harmonic product, the dense bucket grid (D5 c to e) | **Hold, unmeasured** | §8.2.12 M2: a cost fix follows a measurement against a registered threshold | REV-171, Phase 6 (AC4) |
| 19 | `current.md`, the README, `getting-started.md`, `docs/index.md` stale (D6) | **Spent by WP58** | Seven examples, the six extras and the v0.5 scope are in place on `dd45e59`; `current.md` is rewritten by this amendment | Not taken |
| 20 | `CONTRIBUTING.md:61` says 3.11 to 3.13 (D6) | **Does not hold** | The sentence follows CI's run on 3.14: "Python 3.11 to 3.13 runs too" is right | Not taken |
| 21 | REV-116 open without a ruling (D6) | **Does not hold** | Ruled 18 October 2026: WP59's close re-runs the cost record; it moves with the close to WP60 | Not taken |
| 22 | `comsol-ladder.sweep.yaml:49` cites a removed `resolve` (D6) | **Does not hold** | `pipeline.case.resolve` exists; the comment describes what refuses the rung | Not taken |
| 23 | `findings.md` header prose and its pre-WP57 names (D6) | **Read at the close** | Both logs' headers are set to `closed` by the close (criterion 5) | WP60's existing scope |
| 24 | CLAUDE.md and the `np-*` skills rewritten in Simplified Technical English, prose deduplicated (D6) | **A workflow change** | §8.4 governs workflow prose and its word caps | WP60 (AC6) |

## In light of Phase 5

The workbench's server is a second caller of `Case` and `Session` (§8.2.23 Y8; `docs/design/workbench.md`, Q05 to Q08,
WB-11, WB-12): it checks a case as it is edited, shows the resolved case, and reads a run. Verdicts 1 to 7 decide
whether that server calls a public interface or reaches into `pipeline/` as the CLI does today. They land before
`v0.5.0`, the release Phase 5 builds on (§8.2.17 S1, S15), so the shell packages start on the interface they will use.

The stage-5 region interface (verdicts 12, 13) is left for the shell: `plot/data.region_drawing` already gives the
shell one drawing for both kinds, and the pore-shape sketcher, a later tool phase, brings a third kind that would
shape the interface better than two do. The sweep seam waits for the sweep's design round (REV-139, §8.2.19 U4).

## What was not checked

The HTML's diagrams were not rendered. No item was timed beyond the two costs marked *measured*; the efficiency
claims of verdicts 16 and 18 stay claims until Phase 6 measures them.
