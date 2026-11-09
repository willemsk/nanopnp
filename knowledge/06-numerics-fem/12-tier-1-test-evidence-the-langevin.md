---
type: Test Evidence
title: 'Tier-1 test evidence: the Langevin cutoff (WP45 item 21)'
description: What the Tier-1 tests of the Langevin cutoff establish, recorded at WP45 item 21.
tags:
- numerics
- test-evidence
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:tests/tier1/test_electrolyte.py::test_langevin_is_accurate_across_the_series_cutoff
  at: '2026-10-14T00:00:00Z'
---

## Tier-1 test evidence: the Langevin cutoff (WP45 item 21)

The Langevin cutoff, `x = 3e-4`, and why `L(1.1e-8)` evaluated to exactly zero at a cutoff of 1e-8:
`knowledge/01-physics-epnpns/07-implementation-notes-carried-forward.md`, its last note. **[tested: tests/tier1/test_electrolyte.py::test_langevin_is_accurate_across_the_series_cutoff]**
