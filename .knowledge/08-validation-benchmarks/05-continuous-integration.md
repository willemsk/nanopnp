---
type: Benchmark
title: Continuous integration
---

## Continuous integration

| Tier | When | Gate |
|---|---|---|
| 1, 2 | every push | must pass |
| 3 | nightly + pre-release | must pass |
| 4 | pre-release | must pass |

Every run emits a provenance manifest: input hashes, library versions, mesh hash, solver settings,
correction parameter file version, and which corrections were enabled.

