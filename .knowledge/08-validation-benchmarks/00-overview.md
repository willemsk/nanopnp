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

Four tiers, cheapest first. Tiers 1–2 run on every commit; Tier 3 nightly; Tier 4 gates releases.
Formulas below are stated in full so an agent can implement a test without leaving this file. Each
was checked numerically where marked `[verified]`.

---

