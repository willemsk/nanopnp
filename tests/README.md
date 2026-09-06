# Test suite

One directory per verification tier of `SPECIFICATION.md` §7.1. The tier marker is
applied by each directory's `conftest.py`, so placing a file decides its tier.

| Directory | Tier | Runtime | Frequency |
|---|---|---|---|
| `tier1/` | Unit and property tests (§7.2, VER-01 … VER-11) | seconds | every push |
| `tier2/` | Analytic benchmarks (§7.3, VER-12 … VER-22) | minutes | every push |
| `tier3/` | COMSOL cross-implementation comparison (§7.4, VAL-01 … VAL-06, VAL-15) | hours | nightly |
| `tier4/` | Experimental reproduction (§7.5, VAL-07 … VAL-14) | hours | before a release |

Name each test for the requirement it discharges — `test_ver03_correction_check_values`,
`test_val05_contour_against_published_polygon` — so that the traceability matrix in
Appendix A can be checked mechanically.
