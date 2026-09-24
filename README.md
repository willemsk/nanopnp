# nanopnp

**Continuum simulation of biological nanopores, in open-source Python.**

[![CI](https://github.com/willemsk/nanopnp/actions/workflows/ci.yml/badge.svg?branch=main&event=push)](https://github.com/willemsk/nanopnp/actions/workflows/ci.yml?query=branch%3Amain)
[![Documentation](https://img.shields.io/readthedocs/nanopnp?label=docs)](https://nanopnp.readthedocs.io/)
[![Version](https://img.shields.io/github/v/tag/willemsk/nanopnp?include_prereleases&sort=semver&label=version)](CHANGELOG.md)
[![Status: pre-alpha](https://img.shields.io/badge/status-pre--alpha-orange)](#status-and-roadmap)
[![Python 3.10–3.14](https://img.shields.io/badge/python-3.10%E2%80%933.14-blue)](pyproject.toml)
[![Licence: BSD-3-Clause](https://img.shields.io/badge/licence-BSD--3--Clause-blue)](LICENSE)
<br>
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![mypy: strict](https://img.shields.io/badge/mypy-strict-2a6db2)](https://mypy.readthedocs.io/en/stable/command_line.html#cmdoption-mypy-strict)
[![Paper DOI](https://img.shields.io/badge/paper-10.1039%2FD0NR03114C-b31b1b)](https://doi.org/10.1039/D0NR03114C)
[![Open in GitHub Codespaces](https://img.shields.io/badge/Codespaces-open-181717?logo=github)](https://codespaces.new/willemsk/nanopnp)

`nanopnp` implements the **ePNP-NS** framework of Willems et al., *Nanoscale* **12**, 16775–16795
(2020) ([10.1039/D0NR03114C](https://doi.org/10.1039/D0NR03114C)), and replaces a COMSOL
Multiphysics workflow. You give it a pore geometry, an electrolyte and an applied bias. It solves
the extended Poisson–Nernst–Planck / Navier–Stokes equations at steady state on a 2D-axisymmetric
finite-element mesh, and returns the ionic current and conductance, the transport numbers, the
current rectification and the electro-osmotic flow rate. Every result carries a provenance manifest
that can reconstruct the run.

## Highlights

- **The validated model, and its ablations.** The ePNP-NS corrections to the diffusivity, mobility,
  permittivity, viscosity and density can each be switched independently. Their fitted parameters
  live in versioned data files, not in code. Classical PNP-NS is a configuration, not a branch,
  and `pnp`, `poisson`, `pb` and `pb-linear` are separate named models.
- **Numbers you can trust or none at all.** The ionic current is extracted by two independent
  routes, and their agreement is checked before any value is returned. Concentration positivity,
  packing fraction and mesh element quality are all gated. A failed gate aborts with the gate, the
  quantity and its location, never with a plausible wrong answer.
- **Hard cases by continuation.** A staged ladder, warm-started from rung to rung, reaches high
  salt and high bias rather than relying on a cold solve.
- **Reproducible by construction.** A case file (`nanopnp/case/v1`) is the unit of work. Every
  stage emits a content-hashed artefact, and every run records its inputs, library versions,
  solver settings, stabilisation mode and every switch set away from the validated default.
  `nanopnp reproduce` re-solves a run and checks every number.
- **Sweeps and clusters.** Any case field can be swept. Each point is an independent job that
  starts from a converged neighbour, so a sweep maps directly onto an HPC job array.
- **Three ways in.** The `nanopnp` command line, a Python API of twenty stable names, and a PySide6
  desktop shell with live convergence plots and a field viewer.
- **Comparable with the reference.** A reference-matching stabilised mode and a Tier-3 harness
  compare results field by field against COMSOL exports.

## Status and roadmap

**Pre-alpha.** The solver core, the case file, the command line, parameter sweeps, provenance, a
desktop shell, and the user documentation with five worked examples are implemented and tested.
Meshes and charge maps are either supplied from outside or generated for an idealised pore or the
ClyA reference geometry. Building them from a PDB structure is v0.9. Nothing is a validated
release yet, and the comparison against the reference COMSOL model is recorded but not yet passed.

| Release | Phase | Scope | State |
|---|---|---|---|
| v0.1 | 0 | Spike: the coupled model on an analytic pore, the continuation ladder, analytic benchmarks | **released**, [`v0.1.0`](CHANGELOG.md#010---2026-09-02) |
| v0.5 | 1 | Solver core: external meshes and fields, QoI extraction, frozen case schema, API, CLI, sweeps | **released**, [`v0.5.0`](CHANGELOG.md#050---2026-09-24) |
| v0.9 | 2–3 | Full pipeline from a PDB structure: density, symmetry reduction, contour, mesh, PDB2PQR charges | **planned**, [Phase 2 plan](docs/plans/phase-2-geometry-pipeline.md) |
| v1.0 | 4 | Validated release: V&V suite in CI, tutorials, JOSS submission, DOI archive | planned |

Each merged work package is tagged `vX.Y.Z-alpha.N` toward its phase's release, and the package
version is derived from the tag. The history is in [`CHANGELOG.md`](CHANGELOG.md), and the full
release plan is in [`SPECIFICATION.md`](SPECIFICATION.md) §2.7 and §8.

## Installation

`nanopnp` is not on PyPI yet; that comes with v1.0. Install it from source with
[uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/willemsk/nanopnp.git
cd nanopnp
uv sync --all-extras
```

Clone the full history rather than `--depth 1`: the version is read from the nearest git tag. The
default install is the solver core and uses binary wheels only. The extras add:

| Extra | Adds |
|---|---|
| `gui` | The PySide6 desktop shell, `nanopnp-gui` |
| `examples` | Matplotlib, for the worked examples' plots |
| `structure` | The structure-to-mesh pipeline's dependencies (v0.9) |
| `gmsh` | The optional gmsh mesher backend (GPL-2+, never on the default path) |

A VS Code Dev Container and a GitHub Codespace configuration are in
[`.devcontainer/`](.devcontainer) if you would rather not install anything locally.

## Quick start

This is [example 01](examples/01-quickstart/README.md):

```bash
cd examples/01-quickstart
uv run nanopnp mesh cylinder --out pore.msh
uv run nanopnp run quickstart.case.yaml --store store --run-dir run
uv run nanopnp inspect run
uv run nanopnp reproduce run
```

It meshes an idealised pore, solves the validated ePNP-NS model on it, reads the run's provenance
back, and re-solves it to check that every number reproduces. The
[worked examples](examples/) go on to a charged pore, an I–V sweep, the Python API, and the ClyA
reference geometry on a cluster.

To run the test suite: `uv run pytest`. To build the documentation: `uv sync --all-extras --group
docs && uv run docs/scripts/generate.py && uv run mkdocs build --strict` (`uv sync` is exact, so
naming only `--group docs` would uninstall the extras).

## Documentation

The documentation covers a user guide, the five worked examples, and generated case-file,
command-line and API references. It is built from [`docs/`](docs) with MkDocs and will be hosted at
[nanopnp.readthedocs.io](https://nanopnp.readthedocs.io/) once that project is connected. The
model pages render the specification and the knowledge base verbatim.

| Path | Content |
|---|---|
| [`SPECIFICATION.md`](SPECIFICATION.md) | Requirements, physics, design, numerics and V&V plan |
| [`CHANGELOG.md`](CHANGELOG.md) | Every tagged version, and what each work package delivered |
| [`.knowledge/`](.knowledge/00-index.md) | Verified knowledge base: physics, numerics, biology, tooling |
| [`examples/`](examples) | Five worked examples, each executed by a test |
| [`docs/`](docs) | The documentation site's sources (`mkdocs.yml` at the root) |
| [`data/corrections/`](data/corrections) | Fitted correction parameters, one file per electrolyte |
| [`docs/validation/`](docs/validation) | The Tier-3 comparison surface: the frozen cases, the probe grid, and the COMSOL export contract |
| [`packaging/`](packaging) | The desktop bundle: its PyInstaller recipe and its licence notice |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | How to report a finding, set up, and get a change accepted |
| [`CLAUDE.md`](CLAUDE.md) | Working instructions for coding agents and new contributors |

## Citing

If you use `nanopnp`, please cite both the software and the paper it implements. GitHub's
*Cite this repository* reads the software citation from [`CITATION.cff`](CITATION.cff). The
paper is:

```bibtex
@article{willems2020accurate,
  title   = {Accurate modeling of a biological nanopore with an extended continuum framework},
  author  = {Willems, Kherim and Rui{\'c}, Dino and Lucas, Florian L. R. and Barman, Ujjal and
             Verellen, Niels and Hofkens, Johan and Maglia, Giovanni and Van Dorpe, Pol},
  journal = {Nanoscale},
  volume  = {12},
  pages   = {16775--16795},
  year    = {2020},
  doi     = {10.1039/D0NR03114C}
}
```

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Findings are more welcome than fixes. If a benchmark
disagrees with a known answer, or two extraction routes disagree with each other, please open a
**Verification finding** issue. That is evidence, and it is worth more than a green test suite.

Participation is under the [Code of Conduct](CODE_OF_CONDUCT.md).

## Licence

BSD-3-Clause. See [`LICENSE`](LICENSE) and [`CITATION.cff`](CITATION.cff).

The **desktop bundle** is a different matter: its default direct linear solver is SuiteSparse
UMFPACK, which is GPL-2+ and ships inside the NGSolve wheel, so the bundle as a whole is
distributed under GPL-2+ while the library stays BSD-3. See
[`packaging/LICENSES-BUNDLE.md`](packaging/LICENSES-BUNDLE.md), which travels with every bundle.
