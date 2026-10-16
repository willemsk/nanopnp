# WP48 — The OKF backfill

**Status: planned, not started**, 15 October 2026. Inherits WP47 as delivered (the OKF bundle and its
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

- [ ] 1. Record the per-claim inventory under this plan's Outcome; measure test-cost assumptions and assign every claim to items 2-8 (D1-D5). Existing empty-ledger/zero-ceiling fixtures need no new scaffold. Done when the inventory reconciles 361 pending, 56 verified and 17 library concepts without omitted or double-counted claims.
- [ ] 2. Resolve source readings and historical observations throughout `knowledge/`, including the ten unsourced COMSOL markers (D2, D5). Split mixed claims; preserve immutable evidence. Done when the assigned inventory rows and bundle checks pass.
- [ ] 3. Back the 100 pending Test Evidence markers with assertions on existing computations where possible; route historical portions through D5 (D1). Done when affected tests and bundle checks pass; mere test-name resolution is insufficient.
- [ ] 4. Link or add Tier-1 arithmetic tests, using `tests/tier1/test_knowledge_arithmetic.py` where no suitable test exists (D2). Include the nine sourced markers in the audit. Done when every executable calculation has an asserting test and affected tests pass.

*Compaction checkpoint: after item 4; resume from this plan and `git log`.*

- [ ] 5. Add `tested_with` to all 17 concepts after relevant checks run; implement metadata-presence fixtures and enforcement in `validation/okf.py` and `test_okf_bundle.py`, amending VER-68 (5) together (D3). Done when each negative fixture fails for its intended reason and the real bundle passes.
- [ ] 6. Back software behaviours using existing suites or `tests/tier1/test_library_behaviour.py` (D3). Done when assigned assertions, metadata and bundle checks pass.
- [ ] 7. Back NGSolve traps using existing suites or `tests/tier1/test_ngsolve_traps.py`; historical reference experiments follow D5 (D3). Done when properties and workarounds are asserted and affected tests pass.
- [ ] 8. Resolve every remaining inventory row across `knowledge/` using domain tests (D4). Done when the full audit passes, all relevant tests run, and no unresolved claim remains.

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
