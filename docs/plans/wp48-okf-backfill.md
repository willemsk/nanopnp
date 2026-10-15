# WP48 — The OKF backfill

**Status: planned, not started**, 15 October 2026. Inherits WP47 as delivered (the OKF bundle and its
check VER-68), WP45's prose rule (§8.2.11 L4) and the input note `okf-knowledge-bundle.md` (K5 to K8;
G3, G8).

The Phase 4 plan owns the phase ([phase plan](phase-4-polish-and-user-testing.md), *OKF backfill*).
`SPECIFICATION.md` governs; identifiers are pointers. The backfill discharges the second half of G3
and G8, emptying `knowledge/pending.yaml` and resolving REV-103.

## In brief

The reference notes now record every idea on its own page, with three hundred and sixty-one claims waiting for tests or cited sources. This package finishes that ledger.

**What changes.** Every remaining claim in the reference notes gets its proof. Claims about tests that already run are connected directly to those tests. The forty-seven claims waiting for sources are resolved, with source readings citing their original reports and math verified by small automatic checks. The silent library traps and software behaviors documented during development get fast checks that run in fractions of a second. Every software notes page records the exact library versions it was tested against. When finished, the list of waiting claims becomes empty, and a permanent check refuses any claim without a test or source.

**Cost.** Nine commits; about a day of work; no noticeable addition to test run times because new checks are small unit tests.

**What could go wrong.** A test might fail to reproduce a documented trap if library behavior changed; that would be a genuine finding to record rather than a reason to weaken a test.

**Your call.** Machine run times from earlier computers cannot be tested repeatably in automated suites. Should those historical timings cite the earlier project plans where they were measured? *Recommendation:* yes, cite the plans with notes rather than trying to assert stopwatch times in tests.

## Execution brief

Scope: backfill all 361 open claims in `knowledge/pending.yaml`, give library-behaviour concepts their
`tested_with` headers, resolve REV-103, and close G3's ratchet with `CEILING = 0`. Depends on WP47 as
merged (`031fb14`). No new requirement identifier; each new test is named for the claim it backs.
Models (`CLAUDE.md`): Sonnet by default; Haiku for mechanical header and citation updates; Opus only
if Sonnet fails.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 Test-evidence linking | Claims in test-evidence concepts (`knowledge/07-software-stack`, `knowledge/06-numerics-fem`, `knowledge/05-analyte-and-forces`, `knowledge/08-validation-benchmarks`) that state results of existing test files are resolved to their exact test function node IDs (`tests/...::test_...`). Where an existing test runs the computation without asserting the specific figure, one assertion is added to that test | G3, G8, K5; §7.6. Reuses existing solves and fixtures with zero new solver cost and zero gate slowdown |
| D2 Unsourced resolution (REV-103) | All 47 unsourced `[verified]` claims are classified: (a) 10 in `knowledge/09-comsol-reference-settings` get `[^comsol-report]` footnotes; (b) source readings in `knowledge/07-software-stack` get source footnotes; (c) executable arithmetic (e.g. in `knowledge/04-clya-geometry-and-charge`, `knowledge/06-numerics-fem`, `knowledge/08-validation-benchmarks`) is backed by hermetic unit tests in `tests/tier1/test_knowledge_arithmetic.py` | G8, REV-103. Source readings cite their document; executable arithmetic is verified by code |
| D3 Library Behaviour & `tested_with` | Every `type: Library Behaviour` concept in `knowledge/07-software-stack` gains a `tested_with:` mapping pinned to `uv.lock`. Silent library traps (`knowledge/06-numerics-fem/09-ngsolve-traps-found-by-implementing.md` and `knowledge/07-software-stack`) get fast unit tests in `tests/tier1/test_ngsolve_traps.py` and `tests/tier1/test_library_behaviour.py` using minimal 1D/2D toy meshes or pure Python/NumPy constructs | K8; §7.6 runtime NOTE. Unit tests verify the library traps in milliseconds without running full-pore solves |
| D4 Domain physics & numerics claims | Claims in `knowledge/01-physics-epnpns`, `knowledge/04-clya-geometry-and-charge`, `knowledge/05-analyte-and-forces`, `knowledge/06-numerics-fem` (outside traps) are backed by node IDs of existing unit/benchmark tests or new assertions in existing test files (`test_materials.py`, `test_geometry_pipeline.py`, `test_forces.py`, `test_solve.py`) | G3; §7.1. Extends existing domain test suites rather than proliferating redundant fixtures |
| D5 Historical timings & non-executable facts | Wall-clock runtimes on earlier hardware (`knowledge/08-validation-benchmarks` and `knowledge/07-software-stack`) and historical environment observations stay `[verified]` with a footnote pointing to the plan or commit where measured (`[^wp22-plan]`, `[^wp29-plan]`, `[^wp33-plan]`), avoiding non-deterministic clock assertions in tests | G8; §7.6. Hermetic tests must not gate on machine-specific wall-clock durations |
| D6 Ratchet close & VER-68 tightening | `knowledge/pending.yaml` is emptied (`{}`); `CEILING` in `tests/tier1/test_okf_bundle.py` is set to 0; `validation/okf.py` refuses `[tested: pending]` (G3); VER-68 clause (3) in Appendix A is amended; REV-103 is marked `fixed` | G3, G12; VER-68. The ratchet permanently closes; any future unbacked claim fails the push gate |

### Work items

- [ ] 1. `tests/tier1/test_okf_bundle.py`, `src/nanopnp/validation/okf.py` (D6): test scaffolding for empty `pending.yaml` and `CEILING = 0` handling; done when existing tests pass with the test fixture updated.
- [ ] 2. `knowledge/09-comsol-reference-settings`, `knowledge/07-software-stack` (D2, D5): add `[^comsol-report]` footnotes to the 10 reference settings and source footnotes to PyPI/tool readings; update `pending.yaml` and frontmatter `verified:`; done when `check_pending` passes with ceiling 345.
- [ ] 3. `knowledge/07-software-stack/22-tier-2-test-evidence-analytic.md`, `knowledge/06-numerics-fem`, `knowledge/05-analyte-and-forces`, `knowledge/08-validation-benchmarks` (D1, D5): resolve all 89+ test-evidence claims to concrete node IDs in `tests/tier1/` and `tests/tier2/`; update `verified:` actors and `pending.yaml`; done when `check_pending` passes with ceiling 250.
- [ ] 4. `tests/tier1/test_knowledge_arithmetic.py`, `knowledge/04-clya-geometry-and-charge`, `knowledge/06-numerics-fem`, `knowledge/08-validation-benchmarks` (D2): add Tier 1 tests for executable arithmetic claims (binning radial displacement, SUPG/PSPG ratios, concentration derivatives); link inline; update `pending.yaml`; done when `test_knowledge_arithmetic.py` and `check_pending` pass with ceiling 225.

*Compaction checkpoint: after item 4; resume from this plan and `git log`.*

- [ ] 5. `knowledge/07-software-stack` (D3): add `tested_with:` metadata headers to all `Library Behaviour` concepts, pinned to `uv.lock`; done when `test_ver68_the_bundle_conforms` passes without finding.
- [ ] 6. `tests/tier1/test_library_behaviour.py`, `knowledge/07-software-stack` (D3): add Tier 1 unit tests for library behaviors (MDAnalysis, gemmi, shapely, gridDataFormats, PySide6 import guards, CLI import budgets); link inline; update `pending.yaml`; done when `test_library_behaviour.py` and `check_pending` pass with ceiling 150.
- [ ] 7. `tests/tier1/test_ngsolve_traps.py`, `knowledge/06-numerics-fem/09-ngsolve-traps-found-by-implementing.md` (D3): add Tier 1 unit tests for silent NGSolve traps on minimal meshes (trial vs gridfunction linearization, P2 boundary indicator integral, order floor); link inline; update `pending.yaml`; done when `test_ngsolve_traps.py` and `check_pending` pass with ceiling 75.
- [ ] 8. `knowledge/01-physics-epnpns`, `knowledge/04-clya-geometry-and-charge`, `knowledge/05-analyte-and-forces`, `knowledge/06-numerics-fem`, `tests/tier1/test_materials.py`, `tests/tier1/test_geometry_pipeline.py`, `tests/tier1/test_forces.py` (D4): back remaining domain claims with test node IDs or added assertions; update frontmatter and `pending.yaml`; done when `check_pending` passes with ceiling 15.

*Compaction checkpoint: after item 8; resume from this plan and `git log`.*

- [ ] 9. `src/nanopnp/validation/okf.py`, `tests/tier1/test_okf_bundle.py`, `knowledge/pending.yaml`, `SPECIFICATION.md`, `docs/project/review-findings.md`, `docs/project/review-items.md` (D6): empty `pending.yaml` (`{}`), set `CEILING = 0`, update `validation/okf.py` to refuse `[tested: pending]`, amend Appendix A VER-68 (3), mark REV-103 `fixed`; done when `test_okf_bundle.py` and `.claude/hooks/gate.sh run` pass.

### Verification

Tier 1 unless stated; command `uv run pytest tests/tier1/test_okf_bundle.py tests/tier1/test_knowledge_arithmetic.py tests/tier1/test_library_behaviour.py tests/tier1/test_ngsolve_traps.py`, then `.claude/hooks/gate.sh run`.

| Test | Identifiers | Oracle and tolerance |
|---|---|---|
| `tests/tier1/test_okf_bundle.py` | VER-68, G3 | All bundle tests pass with `CEILING = 0` and empty `pending.yaml`; `[tested: pending]` refused |
| `tests/tier1/test_knowledge_arithmetic.py` | VER-68, G8 | Exact arithmetic assertions match closed forms to machine precision or specified digits |
| `tests/tier1/test_library_behaviour.py` | VER-68, K8 | Library behaviors match stated properties; `tested_with` versions match `uv.lock` |
| `tests/tier1/test_ngsolve_traps.py` | VER-68 | NGSolve traps reproduce the exact documented behaviors and workarounds |
| `tests/tier1/` and `tests/tier2/` suite | VER-61, VER-62, VER-63 | All existing unit and analytic benchmarks remain green; VER-62 golden at 10⁻⁸ unchanged |

### Out of scope

The user-testing protocol (WP49); upgrading pinned library versions in `uv.lock`; changing physical model formulations or COMSOL reference values.

### Open questions

None blocking. Historical machine run times (In brief, *Your call*) default to D5 unless ruled.
