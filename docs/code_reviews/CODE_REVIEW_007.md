# Plan review: WP48, the OKF backfill

15 October 2026. Three medium findings, addressed in the plan during this review.
No implementation or knowledge claims were changed.

## Findings

### 1. Sourced arithmetic escaped the planned audit (REV-108)

Original D2 and item 4 classified only the 47 unsourced verified claims. G8 applies to executable
arithmetic even when it already has a source footnote. Nine verified markers are sourced and
therefore escape the pending ledger. Three contain calculations: the
[isolated-atom isolevel](../../knowledge/04-clya-geometry-and-charge/01-geometry-pipeline-as-executed.md),
the [permittivity erratum](../../knowledge/01-physics-epnpns/08-errata-in-the-source-with-the-arithmetic.md),
and its [reference-settings counterpart](../../knowledge/09-comsol-reference-settings/05-contradictions-with-the-rest-of-this.md).
The last concept has no pending entry. Emptying the ledger could leave G8 incomplete.

**Fixed in the plan:** D2 audits all 56 verified markers, separates documentary readings from
calculations and requires tests for the calculations. Item 4 and verification include sourced
arithmetic explicitly. Execution of that audit remains WP48 work.

### 2. Version scope and acceptance did not establish completeness (REV-109)

Original D3 and item 5 limited metadata to the software-stack directory. There are 17 Library
Behaviour concepts: 16 there and [the NGSolve-traps concept](../../knowledge/06-numerics-fem/09-ngsolve-traps-found-by-implementing.md)
under numerics. F6 requires metadata regardless of directory.

The current `_check_tested_with` accepts missing, non-mapping and empty metadata. All 17 concepts
lack it today, yet the original completion test passes. It cannot establish that the backfill
was performed.

**Fixed in the plan:** D3 selects by type across the bundle; item 5 requires negative fixtures,
presence enforcement and the accompanying VER-68 amendment. Versions must be exercised, not
copied from the lock without validation. Validator changes remain WP48 work.

### 3. Historical numerical experiments did not fit the proposed evidence route (REV-110)

Original D1 assumed another assertion on an existing computation, D3 promised minimal toy tests,
and D5 explicitly covered timings and environment observations. Some pending markers instead
record numerical experiments absent from their current cited tests:

- [Limiting-current evidence](../../knowledge/07-software-stack/22-tier-2-test-evidence-analytic.md)
  gives ratios at 100, 400, 1000 and 2000 nm. The current
  [fixture](../../tests/tier2/test_pnp_benchmarks.py#L17) runs only 2000 nm.
- [The aliasing experiment](../../knowledge/06-numerics-fem/09-ngsolve-traps-found-by-implementing.md)
  gives errors on meshes up to 3,463,372 elements and integration orders up to 37.

An extra assertion cannot establish uncomputed results, and a toy mesh cannot establish the
recorded reference errors. Reproducing them literally contradicts zero additional solver cost.

**Fixed in the plan:** D1 inventories evidence and cost first. D5 separates dated measurements
with immutable sources from current properties requiring tests; absent evidence is unresolved.
The unconditional cost promise and guessed intermediate ceilings are removed. Exact historical
error digits are not automatically made cross-platform tolerances.

## Method and checks

- Luna agents (`GPT-5.6 Luna`) performed retrieval and classification; their findings were
  checked against the repository before use.
- Executed YAML parsing agrees with `okf.pending_counts`: 361 claims in 55 concepts, comprising
  314 pending tests and 47 unsourced verified claims. The original total was correct.
- Baseline bundle tests: 32 passed. Review-register and bundle checks together: 57 passed
  before the plan amendment.
- This was not a numerical verification of every claim. No solver gate or historical experiment
  was run. The plan still requires those checks appropriate to each claim during implementation.

The fixes above close plan-review findings only, not REV-103 or the WP48 implementation.