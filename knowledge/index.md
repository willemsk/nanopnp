---
okf_version: "0.2"
---

# nanopnp knowledge base

Each line says when to read the directory; `00-orientation/01-files.md` holds the same map.

* [Orientation](00-orientation/index.md) - Read first: the traps, the conventions, the author rulings, the open items, and when to read each note.
* [ePNP-NS — the physics behind §4](01-physics-epnpns/index.md) - Read first for physics work, before implementing, testing or reviewing model behaviour: the concepts behind `SPECIFICATION.md` §4, which governs — the weak form, the measured Einstein ratio, the rationale and the errata. Workflow-only and mechanical tasks need not load it.
* [Electrokinetics background — double layers, PB, electro-osmosis, selectivity, conductance](02-electrokinetics-background/index.md) - Read for the underlying theory: double layers, Poisson–Boltzmann, electro-osmosis, selectivity, rectification.
* [Nanopore biology and electrophysiology — what the model is a model *of*](03-nanopore-biology/index.md) - Read for domain grounding: the pores, ClyA, electrophysiology, the glossary.
* [ClyA-AS — geometry, fixed charge, and validation targets](04-clya-geometry-and-charge/index.md) - Read before touching the structure, geometry, mesh or charge stages, or a ClyA-AS validation target.
* [Analyte bodies and forces: the thesis's trapping work, the PlyAB force reference, and the tests](05-analyte-and-forces/index.md) - Read before analyte or force work: the thesis's trapping work, the 2022 PlyAB continuum force reference, and the tests.
* [Numerics — FEM formulation, solvers, and quantities of interest](06-numerics-fem/index.md) - Read before an assembly, solver or QoI change: weak forms, solvers, continuation, QoI extraction, and the NGSolve traps.
* [Software stack — libraries, versions, licences, gotchas](07-software-stack/index.md) - Read before adding or changing a dependency: library behaviour, licences, and why a dependency was chosen or rejected.
* [Validation and verification — the benchmark ladder](08-validation-benchmarks/index.md) - Read when writing a test or interpreting a validation failure.
* [COMSOL reference settings — the published model report](09-comsol-reference-settings/index.md) - Read before assuming our discretisation matches the reference's: the original COMSOL mesh, solver and stabilisation settings, from the 5.4 model report. **Their stabilisation was ON** in transport and flow.
