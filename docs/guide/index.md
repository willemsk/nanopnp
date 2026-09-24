# User guide

The guide explains how nanopnp works and how to drive it. It does not explain the physics: the
model is documented by [the specification and the knowledge base](../model/index.md), rendered
verbatim, and the guide points into them by identifier (`PHY-`, `NUM-`, `FR-`) instead of restating
an equation.

| Page | What it covers |
|---|---|
| [Concepts](concepts.md) | Case, stages, artefacts, the store, the manifest |
| [Case files](case-files.md) | The `nanopnp/case/v2` document, its sections and dotted paths |
| [Meshes](meshes.md) | Supplying a mesh, the group vocabulary, the quality gate, the generators |
| [Charge and permittivity fields](fields.md) | Field headers, the three quantities, the conservation gate |
| [Running and exit codes](running.md) | `run`, `stage`, `inspect`, `reproduce`; logging; exit codes |
| [Sweeps and HPC](sweeps.md) | Sweep documents, waves, warm starts, job arrays, rectification |
| [Outputs and quantities](outputs.md) | What a run reports, its sign convention, and the two current routes |
| [Provenance and deviations](provenance.md) | The manifest's eight groups, and deviations from the validated model |
| [Stabilisation modes](stabilisation.md) | `none`, `supg` and `reference`, and why the default is `none` |
| [Desktop shell](desktop.md) | The case editor, run control, convergence plot and field viewer |
