# Implementation review: WP48, the OKF backfill

18 October 2026. Completed Standards and Spec reviews of PR #104 using the installed
Matt Pocock code-review skill, substituted for the unavailable direct review tool with
the author's permission. The two axes ran independently; fixes were adjudicated and
applied in the shipping session, not by the reviewers.

## Revision

- Base: `0ff2d619961ead3a70f39a9f551567ecca5b6c4f` (`main`).
- Head: `53110c78043306afcffcc2e6e59001fc92010952` (`feat/wp48-okf-backfill`).
- Comparison: the three-dot diff between those commits, 102 files and 12 commits.
- Standards: completed, three findings; no baseline smell findings.
- Spec: the first dispatch was partial because its tools could not inspect git history.
  One sequential retry completed the full-diff review and returned seven findings.
- All ten reported findings were accepted. The source-path finding appears on both
  axes, giving nine distinct finding groups. All are fixed below; none is deferred.

## Standards

### S1. ARM baseline features were disabled (high, fixed)

The [CPU-feature test](../../tests/tier1/test_ngsolve_traps.py) disabled NEON and ASIMD
unconditionally. They are baseline instructions on ARM macOS, so NumPy refuses to
import. This violates the cross-platform test contract of SPECIFICATION section 7.6.
The test now selects feature names foreign to the host architecture rather than
disabling that architecture's baseline. The changed test passes on the local x86-64
runtime; an ARM runner was not available for local execution.

### S2. Historical source paths did not exist (medium, fixed)

Eight source entries named nonexistent WP18, WP20, WP21, WP28, WP30 or WP32 plan
filenames. This violated CLAUDE.md's sourced-learning rule. Corrected those paths and
their footnotes, pinning them to the reviewed base revision. Every local or immutable
registered source target now resolves. This overlaps Spec Q3.

### S3. Hashing timings cited a circular source (medium, fixed)

The [case-identity timing claim](../../knowledge/07-software-stack/03-charge-and-electrostatics.md)
cited WP29, which did not contain the measurements. The source is now the
`case_identity` docstring at `1761f15c`, before WP45 removed it, which records the
84 MB table, 9.2 MB structure and import timings. The text labels these as historical
observations, not performance guarantees.

## Spec

### Q1. The integration example named the wrong polynomial (medium, fixed)

The [NGSolve note](../../knowledge/06-numerics-fem/09-ngsolve-traps-found-by-implementing.md)
claimed the unit-square integral of `x^3` was 0.2, while its test integrates `x^4`.
Under D1 and D4, corrected the polynomial to `x^4` and replaced the unsupported exact
low-order result with the underintegration property the test asserts.

### Q2. Toy tests were attached to historical magnitudes (medium, fixed)

The same note attached a scalar-Poisson test to five-field, two-solver singular-system
magnitudes, and a recording-only throughput test to historical efficiencies. D5
requires the actual historical record, not a toy substitute. Pinned the five-field
record to `0f8b57b` and the sweep setup and timing figures to `5abcf42`; retained the
tests for the current general properties and explicitly separated the two kinds of
evidence. No historical solve was rerun and no numerical oracle was loosened.

### Q3. Sources were invalid or misattributed (medium, fixed)

Besides S2's paths, the [fixed-colour-range claim](../../knowledge/07-software-stack/05-gui-and-packaging.md)
cited WP15 instead of WP31 D8. It now cites the actual viewer decision at the pinned
base revision. This closes the D1/D5 evidence mismatch, not just name resolution.

### Q4. Force arithmetic stayed source-only (medium, fixed)

The [force-scale calculation](../../knowledge/06-numerics-fem/07-quantities-of-interest-and-the-flux-trap.md)
remained verified rather than tested, contrary to G8. Linked the existing tests of
the common azimuthal factor, length-independent force scale and 0.1 pN conversion,
and synchronised the concept's verification actors.

### Q5. Gemmi's exercised version was missing (medium, fixed)

The [structure-library concept](../../knowledge/07-software-stack/02-structure-trajectory-and-density.md)
described gemmi behavior but omitted its version, contrary to F6, K8 and D3. Added
`gemmi: 0.7.5` after checking agreement between the runtime and lock and running the
cited parser and wheel checks.

### Q6. Wheel coverage exceeded the assertions (medium, fixed)

The [FEM wheel table](../../knowledge/07-software-stack/01-fem-backend-ngsolvenetgen.md)
said cp310-cp314, while the cited test checks the twelve locked cp311-cp314 wheels.
D1 requires evidence for the exact assertion. Narrowed the claim to the locked
range and the size intervals that its test actually asserts. Python support and
dependencies are unchanged.

### Q7. Section 11 still permitted pending claims (medium, fixed)

SPECIFICATION section 11 still described WP47's ceiling of 361 and admitted pending
markers, contradicting the amended VER-68 contract. Updated it to the closed ledger,
zero ceiling and G8's tested-arithmetic rule. This synchronises existing requirements;
it adds no new behavior.

## Verification And Limits

- Focused CPU-feature check: 1 passed.
- Integration example plus bundle checks: 34 passed.
- Force, wheel, gemmi and bundle checks: 39 passed.
- NGSolve traps plus bundle checks after provenance fixes: 42 passed, with one
  SciPy sparse-format conversion warning.
- Structured source-target check: all 46 local or immutable registered resources resolve.
- Full gate, strict documentation build, fix commit and final CI state are recorded
  in PR #104's Verification section after execution.

The review inspected the full diff and followed selected evidence into existing
assertions and immutable records. It did not independently reproduce all 361 claims,
the original MD/COMSOL artifacts, historical timings or an ARM runtime. The initial
head above was independently reviewed; the subsequent fixes were checked in this
session against the specification, plan, source records and focused tests. No model,
solver path, tolerance, dependency or number-stability golden changed. No finding
from this review remains open and no architectural decision is requested.

Standards: 3 accepted findings, worst high; Spec: 7 accepted findings, worst medium.

## Integration With The Concurrent Review

The local, uncommitted fixes above were rebased onto the concurrent review commits
`a617aaf` and `12aea8b` on 18 October 2026. Their validator, regression-test and
documentation fixes are retained. Nine files conflicted when the local patch was
reapplied: historical citations retain the immutable sources, section 11 retains
the tested-arithmetic rule, both log entries are preserved, and ARM detection also
covers 32-bit ARM. Both reviews' distinct changes remain in the combined tree.

The incoming review's unresolved no-MPI-symbols claim remains recorded as
[REV-111](../project/review-items.md#rev-111-the-no-mpi-symbols-claim-is-backed-only-by-the-lock-file);
it is not closed by this integration. This section records conflict adjudication,
not an independent re-review of the incoming commits. The combined NGSolve-trap
and bundle checks passed all 43 tests; PR #104 records the subsequent full gate,
documentation build and integration commit.