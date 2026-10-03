# nanopnp

**Continuum simulation of biological nanopores** with the extended Poisson–Nernst–Planck and
Navier–Stokes (ePNP-NS) framework of Willems *et al.*, *Nanoscale* **12**, 16775–16795 (2020)
([10.1039/D0NR03114C](https://doi.org/10.1039/D0NR03114C)). nanopnp is an open-source Python
reimplementation of that model, which was built in COMSOL Multiphysics.

Given a pore geometry, an electrolyte and an applied bias, nanopnp solves the coupled electrostatics,
ion transport and flow at steady state on a 2D-axisymmetric finite-element mesh. It returns the
ionic current and conductance, the transport numbers, the current rectification and the
electro-osmotic flow rate. It is built around three rules:

- **A result carries its provenance.** Every run writes a manifest recording its inputs by content
  hash, the library versions, the mesh and its quality, the solver settings, the stabilisation mode,
  and every switch set away from the validated model. A run whose manifest cannot reconstruct it
  does not count as a result.
- **Gates, not hope.** A mesh sliver, a negative concentration, a charge field that does not
  conserve its declared charge, or two current-extraction routes that disagree each abort the run,
  naming the quantity and where it failed. nanopnp does not return a plausible wrong answer.
- **The model is data and configuration.** The fitted corrections live in data files, and
  classical PNP-NS is ePNP-NS with its corrections switched off, not a second code path.

!!! warning "Pre-alpha: toward the v0.4 scope"
    The solver core, the case file, the command line, parameter sweeps, provenance, the desktop
    shell and the v0.3 geometry pipeline, from a PDB structure to a mesh, are delivered. The v0.4
    charge pipeline, which protonates the structure and deposits its charge on the mesh, is
    delivered on `main` as alpha releases toward v0.4. Nothing here is a validated release yet, and the comparison against the paper's
    published results gates v1.0.

## Where to start

| You want to… | Read |
|---|---|
| Run your first case | [Getting started](getting-started.md), then [example 01](_generated/examples/01-quickstart.md) |
| Understand what a run is made of | [Concepts](guide/concepts.md) |
| Write a case file | [Case files](guide/case-files.md) and the [case-file reference](_generated/reference/case-file.md) |
| Run a sweep on a cluster | [Sweeps and HPC](guide/sweeps.md) and [example 05](_generated/examples/05-clya-reference.md) |
| Script it from Python | [Example 04](_generated/examples/04-python-api.md) and the [API reference](_generated/reference/api.md) |
| Use the desktop application | [Desktop shell](guide/desktop.md) |
| Know exactly what is solved | [The model](model/index.md): the specification and knowledge base, verbatim |

## Who it is for

The specification names three kinds of user (§2.4). **Method developers** script the API, change
the physics, and need full introspection. **Collaborating computational scientists** drive
reproducible, case-file runs and sweeps from the command line. **Experimental nanopore
laboratories** want a desktop application: choose a pore, set the salt and the voltage, and get a
prediction. The first two are served today. The third is served by the desktop shell from a
development install. A double-clickable Windows build of the packaging probe has been confirmed on
a real desktop; a bundled shell and installers come later.
