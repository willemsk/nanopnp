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
| [`data/corrections/`](data/corrections) | Fitted correction parameters, one file per electrolyte |

## Quick start

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync --all-extras
uv run pytest
uv run nanopnp --env
```

## Licence

BSD-3-Clause. See [`LICENSE`](LICENSE) and [`CITATION.cff`](CITATION.cff).
