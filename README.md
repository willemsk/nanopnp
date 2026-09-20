# nanopnp

Open-source Python continuum simulation of biological nanopores: an implementation of the
**ePNP-NS** framework of Willems et al., *Nanoscale* **12**, 16775–16795 (2020)
([10.1039/D0NR03114C](https://doi.org/10.1039/D0NR03114C)), replacing a COMSOL Multiphysics
workflow.

`nanopnp` takes an atomistic structure, an electrolyte and an applied bias, and returns ionic
conductance, transport numbers, current rectification, electro-osmotic flow rate, and the axial
force and potential of mean force on an embedded analyte — by solving the extended
Poisson–Nernst–Planck / Navier–Stokes equations at steady state on a 2D-axisymmetric finite-element
mesh generated from the structure.

**Status: pre-alpha.** The specification and the verified knowledge base are complete; the solver
is not yet implemented.

## Documents

| Path | Content |
|---|---|
| [`SPECIFICATION.md`](SPECIFICATION.md) | Requirements, physics, design, numerics and V&V plan |
| [`.knowledge/`](.knowledge/00-index.md) | Verified knowledge base: physics, numerics, biology, tooling |
| [`CLAUDE.md`](CLAUDE.md) | Working instructions for coding agents and new contributors |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | How to report a finding, set up, and get a change accepted |
| [`data/corrections/`](data/corrections) | Fitted correction parameters, one file per electrolyte |
| [`docs/validation/`](docs/validation) | The Tier-3 comparison surface: the frozen cases, the probe grid, and the COMSOL export contract |
| [`packaging/`](packaging) | The desktop bundle: its PyInstaller recipe and its licence notice |

## Quick start

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync --all-extras
uv run pytest
uv run nanopnp --env
```

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
