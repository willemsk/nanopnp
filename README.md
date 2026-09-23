# nanopnp

Open-source Python continuum simulation of biological nanopores: an implementation of the
**ePNP-NS** framework of Willems et al., *Nanoscale* **12**, 16775–16795 (2020)
([10.1039/D0NR03114C](https://doi.org/10.1039/D0NR03114C)), replacing a COMSOL Multiphysics
workflow.

`nanopnp` takes a pore geometry, an electrolyte and an applied bias, and returns the ionic current
and conductance, the transport numbers, the current rectification and the electro-osmotic flow rate,
by solving the extended Poisson–Nernst–Planck / Navier–Stokes equations at steady state on a
2D-axisymmetric finite-element mesh. Every result carries a provenance manifest that can reconstruct
the run.

**Status: pre-alpha, v0.5 scope.** The solver core, the case file, the command line, parameter
sweeps, provenance, and a desktop shell are implemented and tested. Meshes and charge maps are
supplied from outside, or generated for an idealised pore or the ClyA reference geometry. Building
them from a PDB structure (the geometry and charge pipeline) is v0.9. Nothing is a validated release
yet. The comparison against the reference COMSOL model is recorded, not yet passed.

**Documentation:** a user guide, five worked examples, and generated case-file, command-line and
API references, built from [`docs/`](docs) with MkDocs and hosted at
[nanopnp.readthedocs.io](https://nanopnp.readthedocs.io/) once that project is connected.

## Documents

| Path | Content |
|---|---|
| [`SPECIFICATION.md`](SPECIFICATION.md) | Requirements, physics, design, numerics and V&V plan |
| [`.knowledge/`](.knowledge/00-index.md) | Verified knowledge base: physics, numerics, biology, tooling |
| [`CLAUDE.md`](CLAUDE.md) | Working instructions for coding agents and new contributors |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | How to report a finding, set up, and get a change accepted |
| [`examples/`](examples) | Five worked examples, each executed by a test |
| [`docs/`](docs) | The documentation site's sources (`mkdocs.yml` at the root) |
| [`data/corrections/`](data/corrections) | Fitted correction parameters, one file per electrolyte |
| [`docs/validation/`](docs/validation) | The Tier-3 comparison surface: the frozen cases, the probe grid, and the COMSOL export contract |
| [`packaging/`](packaging) | The desktop bundle: its PyInstaller recipe and its licence notice |

## Quick start

Requires [uv](https://docs.astral.sh/uv/). This is [example 01](examples/01-quickstart/README.md):

```bash
uv sync --all-extras
cd examples/01-quickstart
uv run nanopnp mesh cylinder --out pore.msh
uv run nanopnp run quickstart.case.yaml --store store --run-dir run
uv run nanopnp inspect run
uv run nanopnp reproduce run
```

It meshes an idealised pore, solves the validated ePNP-NS model on it, reads the run's provenance
back, and re-solves it to check that every number reproduces. The [worked examples](examples/) go on
to a charged pore, an I–V sweep, the Python API, and the ClyA reference geometry on a cluster.

To run the test suite: `uv run pytest`. To build the documentation: `uv sync --group docs && uv run
docs/scripts/generate.py && uv run mkdocs build --strict`.

A VS Code Dev Container and a GitHub Codespace configuration are in
[`.devcontainer/`](.devcontainer) if you would rather not install anything locally.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Findings are more welcome than fixes: if a benchmark
disagrees with a known answer, or two extraction routes disagree with each other, please open a
**Verification finding** issue — that is evidence, and it is worth more than a green test suite.

Participation is under the [Code of Conduct](CODE_OF_CONDUCT.md).

## Licence

BSD-3-Clause. See [`LICENSE`](LICENSE) and [`CITATION.cff`](CITATION.cff).

The **desktop bundle** is a different matter: its default direct linear solver is SuiteSparse
UMFPACK, which is GPL-2+ and ships inside the NGSolve wheel, so the bundle as a whole is
distributed under GPL-2+ while the library stays BSD-3. See
[`packaging/LICENSES-BUNDLE.md`](packaging/LICENSES-BUNDLE.md), which travels with every bundle.
