## 7. Verification and validation plan

Verification activities carry `VER-nn` identifiers and establish that the software solves the
specified equations correctly. Validation activities carry `VAL-nn` identifiers and establish that
those equations describe the physical system. The structure follows IEEE 1012.

The subsections, one file each:

* [7.1 Strategy and ordering](01-strategy.md) - Sets out the verification strategy: the four test tiers, their runtimes, frequencies and roles in the phase gates.
* [7.2 Tier 1 unit and property tests](02-tier-1.md) - Lists the Tier 1 unit and property tests (VER-01 onward), each with its acceptance criterion.
* [7.3 Tier 2 analytic benchmarks](03-tier-2.md) - Specifies the Tier 2 analytic benchmarks, which verify the axisymmetric weak forms, axis treatment and coupling against closed-form solutions.
* [7.4 Tier 3 cross-implementation comparison](04-tier-3.md) - Specifies the Tier 3 cross-implementation comparison against the paper's published current–voltage relationships and in-pore averages.
* [7.5 Tier 4 experimental reproduction](05-tier-4.md) - Lists the Tier 4 experimental reproduction activities (VAL-07 onward), each with its acceptance criterion against experiment.
* [7.6 Continuous integration](06-continuous-integration.md) - Maps each CI trigger, a pull request, a push to main, or the nightly run, to the tiers and platforms it runs.
