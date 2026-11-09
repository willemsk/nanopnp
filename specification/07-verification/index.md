---
type: Specification
title: "7. Verification and validation plan"
description: "The verification and validation plan: the test tiers, their VER and VAL activities, and continuous integration."
---

## 7. Verification and validation plan

Verification activities carry `VER-nn` identifiers and establish that the software solves the
specified equations correctly. Validation activities carry `VAL-nn` identifiers and establish that
those equations describe the physical system. The structure follows IEEE 1012.

Print one row with `uv run .claude/scripts/clause.py VER-nn`; do not read a table whole. A §7.2
row may carry its Tier 2 and Tier 3 halves: the tier of a test is its directory (§7.3, the NOTE on
VER-26), and `clause.py` prints the whole row.

The subsections, one file each:

* [7.1 Strategy and ordering](01-strategy.md) - Sets out the verification strategy: the four test tiers, their runtimes, frequencies and roles in the phase gates.
* [7.2 Tier 1 unit and property tests](02-tier-1.md) - Lists the Tier 1 unit and property tests (VER-01 onward), each with its acceptance criterion.
* [7.3 Tier 2 benchmarks and converged-solve tests](03-tier-2.md) - Specifies the Tier 2 benchmarks against closed-form solutions, which verify the axisymmetric weak forms, axis treatment and coupling, and the tests that need a converged solve.
* [7.4 Tier 3 cross-implementation comparison](04-tier-3.md) - Specifies the Tier 3 cross-implementation comparison against the paper's published current–voltage relationships and in-pore averages.
* [7.5 Tier 4 experimental reproduction](05-tier-4.md) - Lists the Tier 4 experimental reproduction activities (VAL-07 onward), each with its acceptance criterion against experiment.
* [7.6 Continuous integration](06-continuous-integration.md) - Maps each CI trigger, a pull request, a push to main, or the nightly run, to the tiers and platforms it runs.
