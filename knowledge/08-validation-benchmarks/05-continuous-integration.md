---
type: Benchmark
title: Continuous integration
description: Continuous integration.
tags:
- validation
- benchmark
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
---

## Continuous integration

| Tier | When | Gate |
|---|---|---|
| 1, 2 | every push | must pass |
| 3 | nightly + pre-release | must pass |
| 4 | pre-release | must pass |

Every run emits a provenance manifest: input hashes, library versions, mesh hash, solver settings,
correction parameter file version, and which corrections were enabled.

