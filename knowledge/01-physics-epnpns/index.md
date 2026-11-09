# ePNP-NS — the physics behind §4

* [ePNP-NS — the physics behind §4 (overview)](00-overview.md) - The status of the ePNP-NS concepts and how they relate to SPECIFICATION.md §4.
* [1. Symbols](01-symbols.md) - Points to §4.1.2 for the symbols and explains the two easily misread ones, ⟨c⟩ and d.
* [2. Governing equations](02-governing-equations.md) - The Poisson weak form, with pointers to PHY-03 to PHY-09 for the equations, domains and boundaries.
* [3. The corrections](03-the-corrections.md) - The infinite-dilution values and their sources, the data behind the fits and the measured Einstein ratio; §4.3 states the corrections.
* [4. Rationale worth preserving](04-rationale-worth-preserving.md) - Why the ion wall offset is 0.01 nm, why the viscosity wall function was fitted inverted, and why bulk fits are used near walls.
* [5. Fixed charge from structure](05-fixed-charge-from-structure.md) - The reference's fixed-charge construction, which nanopnp does not reproduce, and the geometry density map's separate sharpness factor.
* [6. Reference case](06-reference-case.md) - The ClyA-AS reference case: structure, electrolyte, bias, temperature, solver and validated quantities.
* [7. Implementation notes carried forward](07-implementation-notes-carried-forward.md) - Implementation lessons for the physics, from the source work and from building nanopnp: the unsmoothed d, damped Newton, the packing assert, a saturated d, switches versus resolved models, the Langevin cutoff.
* [8. Errata in the source, with the arithmetic](08-errata-in-the-source-with-the-arithmetic.md) - Six errata in the printed sources, numbered as §4.6's rows, each with the arithmetic that settles it.
* [9. Source files](09-source-files.md) - Where the thesis source is and what each of its chapter files holds.
