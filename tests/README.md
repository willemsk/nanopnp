# Test suite

One directory per verification tier of `SPECIFICATION.md` §7.1. The tier marker is
applied by each directory's `conftest.py`, so placing a file decides its tier.

| Directory | Tier | Runtime | Frequency |
|---|---|---|---|
| `tier1/` | Unit and property tests (§7.2, VER-01 … VER-11) | seconds | every push |
| `tier2/` | Analytic benchmarks (§7.3, VER-12 … VER-22) | minutes | every push, except the walks marked `nightly` |
| `tier3/` | Cross-implementation comparison (§7.4): the published results (VAL-16, VAL-17), COMSOL fields where exported (VAL-01 … VAL-04), VAL-05, VAL-06, VAL-15 | hours | nightly |
| `tier4/` | Experimental reproduction (§7.5, VAL-07 … VAL-14) | hours | before a release |

A test that walks the pipeline end to end, an executed example or the 2WCD entry through the
stages, is marked `nightly` (`pytestmark = pytest.mark.nightly`). `uv run pytest` leaves `nightly`
and `slow` tests out; `uv run pytest --nightly` runs them. The per-push selection (§7.6) still runs
example 01, while it solves in under 60 s, and example 02's charged ePNP-NS walk, even where they are
marked `nightly`. Never mark an analytic benchmark `nightly`: it is the test that localises a failure.
`slow` is different: a `slow` test is measured and recorded, and no push gates it.

Write a test only where it is in the test scope (`SPECIFICATION.md` §8.2.13 N1): physics and numerics,
core mechanisms, and the licence and architecture guards. Each entry point keeps a thin smoke test. A
new test's name or first line says which silent failure it catches, for example
`test_ver03_correction_check_values`. A requirement identifier is named in a test only where the
requirement is physics, numerics or a core mechanism; other identifiers are verified at review.
