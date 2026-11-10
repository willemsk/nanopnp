---
type: Overview
title: Validation and verification — the benchmark ladder (overview)
description: 'The benchmark ladder: four tiers from unit tests to experimental reproduction.'
tags:
- validation
- overview
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
---

# Validation and verification — the benchmark ladder

Four tiers, cheapest first. Tiers 1–2 run on every push; Tier 3 nightly; Tier 4 gates releases.
`SPECIFICATION.md` §7 states each benchmark, its oracle and its tolerance; these notes point to
those rows and keep what the specification lacks, checked where marked `[tested: <test>]` or
`[verified]`. The measured values and why each tolerance is set are in the test-evidence notes:
`knowledge/07-software-stack/21-…` and `22-…` (Tier 2), `knowledge/05-analyte-and-forces/13-…`
(the force routes) and `07-tier-3-test-evidence-run-times-of-the.md` (Tier 3).

---

