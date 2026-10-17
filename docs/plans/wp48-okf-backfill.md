# WP48 — The OKF backfill

**Status: in progress**, 16 October 2026. Inherits WP47 as delivered (the OKF bundle and its
check VER-68), WP45's prose rule (§8.2.11 L4) and the input note `okf-knowledge-bundle.md` (K5 to K8;
G3, G8).

Amended after [plan review](../code_reviews/CODE_REVIEW_007.md), 15 October 2026 (REV-108 to REV-110).

The Phase 4 plan owns the phase ([phase plan](phase-4-polish-and-user-testing.md), *OKF backfill*).
`SPECIFICATION.md` governs; identifiers are pointers. The backfill discharges the second half of G3
and G8, emptying `knowledge/pending.yaml` and resolving REV-103.

## In brief

The reference notes hold three hundred and sixty-one claims waiting for tests or sources. This package finishes that ledger and checks calculations that already cite a source but still need a test.

**What changes.** Each claim gets evidence that establishes what it actually says. Calculations and software behaviour get tests; readings of reports get citations. Historical measurements stay dated observations, separate from properties tested today. All library-behaviour pages record the versions used, and automatic checks refuse missing metadata and unfinished claims.

**Cost.** Nine commits. The opening inventory establishes the effort and additional test cost; existing computations are reused where possible. Full reference experiments are not assumed to fit into small unit tests.

**What could go wrong.** A documented result may no longer hold, or its original record may be missing. Record the discrepancy rather than weakening a test or attaching evidence that proves less than the claim.

**Your call.** Should historical numerical experiments, as well as timings, cite their original records? *Recommendation:* yes, with the date and conditions preserved and their general conclusions tested separately.

## Execution brief

Scope: 361 pending claims (314 tested-pending, 47 unsourced), all 56 `[verified]` markers including
nine already sourced, and all 17 `Library Behaviour` concepts across the bundle. Resolve REV-103
and close G3's ratchet at zero. Depends on merged WP47 (`031fb14`). No new identifier; tests name
the claim or existing requirement they discharge. Review fixes amend the plan, not the implementation.
Models (`CLAUDE.md`): Sonnet by default; Haiku for mechanical header and citation updates; Opus only
if Sonnet fails.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 Claim inventory and linking | Classify each pending marker and every verified marker by exact assertion, evidence, owning item and cost. Reuse an existing computation only where its assertions establish the claim; otherwise add a discriminating test or apply D5. Node IDs resolve by syntax tree under G12 | G3, K5; a valid test name alone is not evidence |
| D2 Arithmetic and source readings | Audit all 56 verified markers. Executable arithmetic becomes tested, including the sourced isolated-atom isolevel and both permittivity-cap passages. Split mixed claims. Source readings retain footnotes registered in `sources[].id`; synchronise the exact `verified` actor set, retaining `process:arithmetic` for remaining verified claims | G8, K7, REV-103; a source footnote does not exempt arithmetic |
| D3 Library behaviour and versions | Select all 17 concepts by type, including the numerics traps page. Require non-empty `tested_with` mappings; record relevant versions actually exercised and confirm agreement with the lock before updating metadata. Add negative tests for missing, non-mapping, empty and stale metadata. Use minimal reproductions only for properties they establish | F6, K8, VER-68; do not stamp an untested version |
| D4 Physics and numerics | Reuse domain suites and fixtures; add explicit assertions with tolerances justified by the analytic oracle or measured portability, not historical error digits. Audit remaining claims across every directory. Investigate mismatches and correct documentary errors with evidence; model changes need separate author approval | G3, §7.1; no weakened oracle or duplicated full solve merely to fill a ledger |
| D5 Historical observations | Across the bundle, separate current properties from dated timings, environment observations and numerical experiments. Only the historical record becomes source-backed verified, with immutable commit/document location and conditions. Test general conclusions separately. A missing source remains unresolved; reproduce it at an explicitly assessed cost or seek an author ruling | G8; no substitution of a toy result for a reference measurement, or source citation for executable arithmetic |
| D6 Closure | Empty `pending.yaml`, set `CEILING = 0`, refuse pending markers even with a permissive caller ceiling, and retain unsourced-claim refusals. Amend VER-68 (3), (5) and its trailing WP47-ceiling wording; close REV-103 only after D2's full audit. Preserve AST resolution and existing ledger/source checks | G3, G12; fixture tests prove each refusal |

### Work items

- [x] 6f6027f 1. Record the per-claim inventory under this plan's Outcome; measure test-cost assumptions and assign every claim to items 2-8 (D1-D5). Existing empty-ledger/zero-ceiling fixtures need no new scaffold. Done when the inventory reconciles 361 pending, 56 verified and 17 library concepts without omitted or double-counted claims.

> **Outcome — item 1.** Reconciled inventory across all 90 concepts: **361 pending claims** in 55 concepts (`314 tested_pending` + `47 verified_unsourced`), **56 `[verified]` claims** in 25 concepts (`47 verified_unsourced` + `9 verified_sourced`, giving `370` audited claim markers in total), and **17 `Library Behaviour` concepts** (`06-numerics-fem/09-ngsolve-traps-found-by-implementing.md` plus 16 concepts in `07-software-stack/`, including `07-local-assets.md` with zero pending markers). Baseline verification of `test_okf_bundle.py`, `test_plan_shape.py`, `test_plan_records.py` and `test_prose_share.py` (70 tests) runs in 8.59 s; new Tier-1 checks reuse miniature meshes and cached fixtures to stay under 5 s additional wall time, while Tier-2 assertions attach to existing module-scoped solves.
>
> | Concept | Type | `tested: pending` (count: lines) | `verified` unsourced (count: lines) | `verified` sourced (count: lines) | Owning items |
> |---|---|---|---|---|---|
> | `01-physics-epnpns/03-the-corrections.md` | Physics | 1: L61 | 0 | 0 | 8 |
> | `01-physics-epnpns/07-implementation-notes-carried-forward.md` | Physics | 5: L39,L44,L49,L54,L58 | 0 | 0 | 8 |
> | `01-physics-epnpns/08-errata-in-the-source-with-the-arithmetic.md` | Erratum | 0 | 0 | 1: L77 | 2, 4 |
> | `04-clya-geometry-and-charge/01-geometry-pipeline-as-executed.md` | Pipeline | 12: L68,L78,L81,L83,L86,L107,L119,L131,L165,L168,L179,L234 | 4: L97,L99,L108,L162 | 1: L49 | 2, 4, 8 |
> | `04-clya-geometry-and-charge/02-model-geometry-and-conventions.md` | Pipeline | 5: L41,L60,L70,L74,L98 | 3: L63,L69,L98 | 0 | 2, 4, 8 |
> | `04-clya-geometry-and-charge/03-fixed-charge-pipeline.md` | Pipeline | 4: L49,L78,L119,L146 | 1: L144 | 0 | 2, 4, 8 |
> | `04-clya-geometry-and-charge/04-mesh.md` | Pipeline | 1: L19 | 0 | 0 | 8 |
> | `04-clya-geometry-and-charge/08-gaps-and-ambiguities-questions-for-the.md` | Open Item | 3: L23,L40,L67 | 0 | 0 | 2 |
> | `04-clya-geometry-and-charge/09-tier-1-test-evidence-contours-and.md` | Test Evidence | 3: L45,L46,L47 | 0 | 0 | 3 |
> | `04-clya-geometry-and-charge/10-tier-1-test-evidence-the-derived.md` | Test Evidence | 1: L16 | 0 | 0 | 3 |
> | `04-clya-geometry-and-charge/11-tier-1-test-evidence-the-val-05-harness.md` | Test Evidence | 2: L21,L24 | 0 | 0 | 3 |
> | `04-clya-geometry-and-charge/12-tier-2-test-evidence-quadrature-gates.md` | Test Evidence | 4: L25,L26,L30,L31 | 0 | 0 | 3 |
> | `04-clya-geometry-and-charge/13-tier-3-test-evidence-the-charged-tube.md` | Test Evidence | 2: L20,L23 | 0 | 0 | 3 |
> | `05-analyte-and-forces/05-force-computation-the-analytic-model.md` | Domain | 1: L50 | 0 | 0 | 8 |
> | `05-analyte-and-forces/10-gaps-and-ambiguities.md` | Open Item | 1: L25 | 0 | 0 | 8 |
> | `05-analyte-and-forces/12-tier-1-test-evidence-analyte-bodies.md` | Test Evidence | 1: L22 | 0 | 0 | 3 |
> | `05-analyte-and-forces/13-tier-2-test-evidence-electro-osmosis.md` | Test Evidence | 5: L21,L22,L23,L25,L27 | 0 | 0 | 3 |
> | `06-numerics-fem/02-axisymmetric-weak-forms.md` | Numerics | 3: L63,L77,L93 | 0 | 0 | 8 |
> | `06-numerics-fem/04-stabilisation.md` | Numerics | 7: L88,L135,L168,L188,L221,L231,L251 | 3: L69,L118,L272 | 0 | 4, 8 |
> | `06-numerics-fem/05-nonlinear-solution.md` | Numerics | 8: L54,L63,L95,L109,L119,L140,L147,L161 | 1: L101 | 0 | 4, 8 |
> | `06-numerics-fem/06-linear-solvers.md` | Numerics | 1: L30 | 0 | 0 | 8 |
> | `06-numerics-fem/07-quantities-of-interest-and-the-flux-trap.md` | Numerics | 12: L44,L64,L83,L109,L131,L149,L154,L181,L208,L235,L253,L258 | 4: L35,L227,L264,L269 | 0 | 2, 4, 8 |
> | `06-numerics-fem/08-mesh-resolution-and-adaptivity.md` | Numerics | 3: L46,L65,L92 | 0 | 1: L37 | 2, 8 |
> | `06-numerics-fem/09-ngsolve-traps-found-by-implementing.md` | Library Behaviour | 51: L19,L49,L56,L62,L70,L85,L93,L102,L112,L118,L126,L131,L140,L146,L155,L162,L192,L203,L213,L234,L236,L247,L290,L332,L345,L358,L370,L389,L398,L415,L420,L426,L434,L438,L442,L447,L458,L467,L475,L483,L484,L488,L492,L497,L504,L512,L524,L526,L548,L558,L560 | 3: L283,L576,L587 | 0 | 4, 5, 7 |
> | `06-numerics-fem/13-tier-1-test-evidence-the-domain.md` | Test Evidence | 1: L24 | 0 | 0 | 3 |
> | `06-numerics-fem/14-tier-1-test-evidence-newtons.md` | Test Evidence | 2: L26,L27 | 0 | 0 | 3 |
> | `06-numerics-fem/15-tier-1-test-evidence-scaling-the-wall.md` | Test Evidence | 11: L22,L23,L24,L25,L26,L28,L29,L30,L32,L33,L34 | 0 | 0 | 3 |
> | `06-numerics-fem/16-tier-2-test-evidence-ladder-walks-block.md` | Test Evidence | 6: L29,L31,L32,L33,L34,L35 | 0 | 0 | 3 |
> | `06-numerics-fem/17-tier-3-test-evidence-the-mesh-geometry.md` | Test Evidence | 3: L15,L16,L17 | 0 | 0 | 3 |
> | `07-software-stack/01-fem-backend-ngsolvenetgen.md` | Library Behaviour | 5: L19,L22,L24,L30,L34 | 0 | 0 | 5, 6 |
> | `07-software-stack/02-structure-trajectory-and-density.md` | Library Behaviour | 18: L20,L21,L27,L32,L48,L53,L61,L63,L80,L89,L110,L114,L127,L133,L152,L164,L196,L210 | 1: L185 | 0 | 4, 5, 6 |
> | `07-software-stack/03-charge-and-electrostatics.md` | Library Behaviour | 10: L25,L45,L93,L103,L108,L113,L128,L143,L197,L212 | 4: L33,L111,L116,L194 | 0 | 2, 4, 5, 6 |
> | `07-software-stack/04-geometry-meshing-and-io.md` | Library Behaviour | 17: L34,L37,L46,L56,L66,L72,L83,L94,L98,L105,L111,L128,L150,L199,L203,L204,L212 | 1: L214 | 0 | 4, 5, 6 |
> | `07-software-stack/05-gui-and-packaging.md` | Library Behaviour | 16: L22,L26,L46,L59,L77,L128,L141,L169,L181,L190,L234,L271,L313,L329,L340,L352 | 3: L102,L120,L157 | 0 | 2, 4, 5, 6 |
> | `07-software-stack/06-licence-summary.md` | Library Behaviour | 1: L20 | 0 | 0 | 5, 6 |
> | `07-software-stack/07-local-assets.md` | Library Behaviour | 0 | 0 | 0 | 5 |
> | `07-software-stack/08-python-version-floor-the-310-target-is.md` | Library Behaviour | 8: L15,L22,L26,L46,L48,L56,L59,L63 | 0 | 0 | 5, 6 |
> | `07-software-stack/09-the-clis-import-budget-measured.md` | Library Behaviour | 4: L13,L20,L27,L33 | 0 | 0 | 5, 6 |
> | `07-software-stack/10-canonical-is-the-on-disk-format-not.md` | Library Behaviour | 1: L27 | 1: L35 | 0 | 4, 5, 6 |
> | `07-software-stack/11-a-stages-workspace-falls-back-to-the.md` | Library Behaviour | 1: L13 | 0 | 0 | 5, 6 |
> | `07-software-stack/12-the-suites-blas-threads-buy-nothing.md` | Library Behaviour | 5: L13,L76,L77,L87,L106 | 0 | 0 | 5, 6 |
> | `07-software-stack/13-documentation-tooling-mkdocs-material.md` | Library Behaviour | 1: L38 | 0 | 0 | 5, 6 |
> | `07-software-stack/14-a-windows-checkout-rewrites-the-bytes-a.md` | Library Behaviour | 1: L13 | 0 | 0 | 5, 6 |
> | `07-software-stack/15-an-npz-is-reproducible-bytes-only-if.md` | Library Behaviour | 1: L16 | 1: L32 | 0 | 2, 5, 6 |
> | `07-software-stack/16-ngsolves-bundled-stubs-cannot-type.md` | Library Behaviour | 1: L13 | 0 | 0 | 5, 6 |
> | `07-software-stack/19-tier-1-test-evidence-stores-paths-occ.md` | Test Evidence | 4: L22,L24,L25,L26 | 0 | 0 | 3 |
> | `07-software-stack/20-tier-1-test-evidence-import-costs.md` | Test Evidence | 2: L24,L27 | 0 | 0 | 3 |
> | `07-software-stack/21-tier-2-test-evidence-budgets-timings.md` | Test Evidence | 3: L22,L24,L25 | 0 | 0 | 3 |
> | `07-software-stack/22-tier-2-test-evidence-analytic.md` | Test Evidence | 45: L42,L43,L44,L45,L46,L47,L49,L50,L51,L53,L54,L56,L57,L59,L60,L61,L62,L63,L64,L66,L67,L68,L69,L70,L71,L74,L75,L76,L77,L78,L79,L80,L83,L84,L85,L86,L87,L88,L91,L92,L93,L94,L95,L96,L97 | 0 | 0 | 3 |
> | `08-validation-benchmarks/01-tier-1-unit-and-property-tests-seconds.md` | Benchmark | 0 | 3: L25,L27,L35 | 0 | 4 |
> | `08-validation-benchmarks/02-tier-2-analytic-benchmarks-minutes.md` | Benchmark | 1: L30 | 2: L27,L56 | 0 | 4, 8 |
> | `08-validation-benchmarks/03-tier-3-comsol-differential-tests-hours.md` | Benchmark | 5: L49,L90,L114,L116,L123 | 2: L81,L101 | 0 | 4, 8 |
> | `08-validation-benchmarks/07-tier-3-test-evidence-run-times-of-the.md` | Test Evidence | 5: L19,L20,L21,L23,L24 | 0 | 0 | 3 |
> | `09-comsol-reference-settings/00-overview.md` | Overview | 0 | 1: L47 | 0 | 2 |
> | `09-comsol-reference-settings/02-mesh-27.md` | Reference Settings | 0 | 1: L65 | 0 | 2 |
> | `09-comsol-reference-settings/03-solver-3-4.md` | Reference Settings | 0 | 2: L71,L87 | 0 | 2 |
> | `09-comsol-reference-settings/04-physics-settings.md` | Reference Settings | 0 | 6: L103,L128,L145,L223,L246,L282 | 1: L64 | 2 |
> | `09-comsol-reference-settings/05-contradictions-with-the-rest-of-this.md` | Erratum | 0 | 0 | 5: L29,L33,L34,L35,L36 | 2, 4 |
> | **Total (58 concepts; 17 Library Behaviour)** | — | **314** | **47** | **9** (`56` verified) | Items 2–8 |
>
> **Partition by work item (361 pending -> 0; 56 verified audited; 17 `Library Behaviour` concepts):**
> - **Item 2 (source readings & standalone archive observations):** 21 `verified_unsourced` (`04-02:L63,L69`, `06-07:L35,L227,L269`, `07-03:L33,L111,L116`, `07-05:L120,L157`, `07-15:L32`, and the 10 COMSOL markers `09-00:L47`, `09-02:L65`, `09-03:L71,L87`, `09-04:L103,L128,L145,L223,L246,L282`), 9 `verified_sourced` (`01-08:L77`, `04-01:L49` and `09-05:L29` split into source reading + Item 4 arithmetic; `06-08:L37`, `09-04:L64`, `09-05:L33,L34,L35,L36` retained as source readings), and 10 standalone archive/reference `tested_pending` records (`04-01:L68,L78,L83,L86,L234`, `04-03:L49,L78`, `04-08:L23,L40,L67`), lowering `CEILING` by 31 (`361 -> 330`).
> - **Item 3 (Test Evidence):** 100 `tested_pending` across the 14 `Test Evidence` concepts (assertions on existing computations or D5 source footnotes for historical timings), lowering `CEILING` by 100 (`330 -> 230`).
> - **Item 4 (Tier-1 arithmetic & verified audit):** the remaining 26 `verified_unsourced` (`04-01:L97,L99,L108,L162`, `04-02:L98`, `04-03:L144`, `06-04:L69,L118,L272`, `06-05:L101`, `06-07:L264`, `06-09:L283,L576,L587`, `07-02:L185`, `07-03:L194`, `07-04:L214`, `07-05:L102`, `07-10:L35`, `08-01:L25,L27,L35`, `08-02:L27,L56`, `08-03:L81,L101`) plus the 3 arithmetic halves split from `01-08:L77`, `04-01:L49` and `09-05:L29`, lowering `CEILING` by 26 (`230 -> 204`) and completing the 56-marker `[verified]` audit.
> - **Item 5 (`tested_with` metadata & enforcement):** all 17 `Library Behaviour` concepts (`06-09` and `07-01`..`07-16`), plus `VER-68` (5) enforcement and negative fixtures (`CEILING` stays `204`).
> - **Item 6 (software-stack `Library Behaviour`):** 90 `tested_pending` across `07-01`..`07-16` (assertions in existing suites or `test_library_behaviour.py`, with historical timings/build records routed through D5), lowering `CEILING` by 90 (`204 -> 114`).
> - **Item 7 (NGSolve traps):** 51 `tested_pending` in `06-numerics-fem/09-ngsolve-traps-found-by-implementing.md` (assertions in existing suites or `test_ngsolve_traps.py`, with historical reference experiments routed through D5), lowering `CEILING` by 51 (`114 -> 63`).
> - **Item 8 (remaining domain claims):** 63 `tested_pending` across `01-physics-epnpns` (6), `04-clya-geometry-and-charge` (15), `05-analyte-and-forces` (2), `06-numerics-fem` (34) and `08-validation-benchmarks` (6), lowering `CEILING` by 63 (`63 -> 0`).
- [x] 91db08e 2. Resolve source readings and historical observations throughout `knowledge/`, including the ten unsourced COMSOL markers (D2, D5). Split mixed claims; preserve immutable evidence. Done when the assigned inventory rows and bundle checks pass.

> **Outcome — item 2.** Resolved 31 pending markers across 13 concepts (`21 verified_unsourced` + `10 tested_pending`), split the three mixed source/arithmetic passages (`01-08:L77`, `04-01:L49`, `09-05:L29`), synchronised `verified` actor sets and `knowledge/pending.yaml`, and lowered `CEILING` from `361` to `330`.
- [x] 694d239 3. Back the 100 pending Test Evidence markers with assertions on existing computations where possible; route historical portions through D5 (D1). Done when affected tests and bundle checks pass; mere test-name resolution is insufficient.

> **Outcome — item 3.** Backed all 100 pending `Test Evidence` markers across the 17 `Test Evidence` concepts (`04-09..13`, `05-12..13`, `06-13..17`, `07-19..22`, `08-07`), added explicit assertions in the cited Tier-1 and Tier-2 suites and fast contract checks in `tests/tier1/test_reproduce_diagnostics.py` and `tests/tier2/test_envelope.py`, routed historical pre-WP45 docstring and plan timings through D5 source footnotes, synchronised `verified` actor sets and `knowledge/pending.yaml`, and lowered `CEILING` from `330` to `230`.
- [x] 57254c6 4. Link or add Tier-1 arithmetic tests, using `tests/tier1/test_knowledge_arithmetic.py` where no suitable test exists (D2). Include the nine sourced markers in the audit. Done when every executable calculation has an asserting test and affected tests pass.

> **Outcome — item 4.** Audited all 56 `[verified]` markers across the bundle (including the 9 sourced markers), linked existing Tier-1 tests or added 15 deterministic arithmetic tests in `tests/tier1/test_knowledge_arithmetic.py` covering the remaining 26 `verified_unsourced` markers and the 3 arithmetic passages split in item 2 (`01-08:L77`, `04-01:L49`, `09-05:L29`), synchronised `verified` actor sets and `knowledge/pending.yaml` (zero `verified_unsourced` remaining), and lowered `CEILING` from `230` to `204`.

*Compaction checkpoint: after item 4; resume from this plan and `git log`.*

- [x] bae78fa 5. Add `tested_with` to all 17 concepts after relevant checks run; implement metadata-presence fixtures and enforcement in `validation/okf.py` and `test_okf_bundle.py`, amending VER-68 (5) together (D3). Done when each negative fixture fails for its intended reason and the real bundle passes.

> **Outcome — item 5.** Verified installed runtime versions against `uv.lock`, populated non-empty `tested_with` mappings across all 17 `Library Behaviour` concepts (`06-09` and `07-01..16`), enforced non-empty `tested_with` mappings in `src/nanopnp/validation/okf.py` with negative fixtures for missing, non-mapping, empty, empty-version and stale metadata in `tests/tier1/test_okf_bundle.py`, and amended `VER-68` (5) in `SPECIFICATION.md` (`CEILING` remains `204`).
- [x] 6808960 6. Back software behaviours using existing suites or `tests/tier1/test_library_behaviour.py` (D3). Done when assigned assertions, metadata and bundle checks pass.

> **Outcome — item 6.** Backed all 90 pending `Library Behaviour` markers across `07-software-stack/01..16` with deterministic assertions in `tests/tier1/test_library_behaviour.py` (18 tests covering NGSolve OCC/meshing/element-order contracts, MDAnalysis/GridDataFormats density round-trips, PROPKA/PDB2PQR protonation contracts, packaging/dependency/Python-floor/MkDocs/parallelism invariants) and existing Tier-1/Tier-2 suites, synchronised `verified` actor sets and `knowledge/pending.yaml`, and lowered `CEILING` from `204` to `114`.
- [x] 52bd4f1 7. Back NGSolve traps using existing suites or `tests/tier1/test_ngsolve_traps.py`; historical reference experiments follow D5 (D3). Done when properties and workarounds are asserted and affected tests pass.

> **Outcome — item 7.** Backed all 51 pending `Library Behaviour` markers in `knowledge/06-numerics-fem/09-ngsolve-traps-found-by-implementing.md` with 9 targeted tests in `tests/tier1/test_ngsolve_traps.py`, wave-width assertions in `tests/tier1/test_sweep_plan.py`, existing Tier-1/Tier-2 suites and D5 footnotes for historical commit records (`0ea0789`, `c27c35c`, `6c0a249`, `1a2e383`, `7597814`), synchronised `verified` actor sets and `knowledge/pending.yaml`, and lowered `CEILING` from `114` to `63`.
- [ ] 8. Resolve every remaining inventory row across `knowledge/` using domain tests (D4). Done when the full audit passes, all relevant tests run, and no unresolved claim remains.

> **Outcome — item 8.** Backed all 63 remaining domain claims across the bundle (16 concepts across `01-physics-epnpns`, `04-clya-geometry-and-charge`, `05-analyte-and-forces`, `06-numerics-fem`, and `08-validation-benchmarks`) with Tier-1/Tier-2 test assertions (`test_corrections.py`, `test_electrolyte.py`, `test_knowledge_arithmetic.py`, `test_mesh_profile.py`, `test_contour.py`, `test_val05_2wcd.py`, `test_region.py`, `test_charge_kernel.py`, `test_solution_state.py`, and existing suites) and D5 immutable commit and plan records, reduced pending claims across the entire bundle to zero (`pending.yaml` is `{}`), and lowered `CEILING` to 0 in `tests/tier1/test_okf_bundle.py`.

*Compaction checkpoint: after item 8; resume from this plan and `git log`.*

- [ ] 9. Close the ratchet in `validation/okf.py`, `test_okf_bundle.py`, `pending.yaml` and the specification; replace fixtures that accepted pending claims, close REV-103 in both registers, and update current-work navigation (D6). Done when closure fixtures and the full gate pass.

Each batch synchronises inline evidence, source definitions, actors and `knowledge/log.md`, regenerates
`pending.yaml`, and lowers `CEILING` to the measured remainder. Inventory-derived counts replace
guessed milestones; metadata work need not reduce the pending count.

- [ ] 10. Document Gmsh's optional Linux runtime prerequisites in the development setup guidance: keep the `gmsh` Python wheel in its extra, explain that `uv` cannot install distribution packages, and give the Arch (`glu`, `libxft`, `libxinerama`, `libxcursor`) and Debian/Ubuntu equivalents. Done when the strict documentation build passes; do not make Gmsh a default end-user dependency.

### Verification

Run affected tests, then `.claude/hooks/gate.sh run` and the strict documentation build from
`CLAUDE.md`. New test files below are used only where existing suites cannot house the checks.

| Test | Identifiers | Oracle and tolerance |
|---|---|---|
| `tests/tier1/test_okf_bundle.py` | VER-68, G3, K8 | Empty ledger passes; pending fails even above zero ceiling; unsourced verified fails at zero; missing, non-mapping, empty and stale metadata fail |
| Existing arithmetic tests or `test_knowledge_arithmetic.py` (Tier 1) | G8 | Independent closed forms or documented digits; all 56 markers classified, including sourced arithmetic |
| Existing library tests or `test_library_behaviour.py`, `test_ngsolve_traps.py` (Tier 1) | VER-68, K8 | Each current property and workaround reproduced; exercised versions recorded; historical observations have immutable sources |
| Tiers 1-2 and affected existing tests | VER-61, VER-62, VER-63 | Existing oracles unchanged; number-stability golden unchanged; measured additional cost reported |
| Generator and `mkdocs build --strict` | VER-45, VER-68 | Sources, footnotes and links render without warnings |

### Out of scope

The user-testing protocol (WP49); upgrading pinned library versions in `uv.lock`; changing physical model formulations or COMSOL reference values.

### Open questions

None blocking. D5 governs historical observations; missing evidence or unaffordable reproduction
becomes an author question, never an automatic closure.
