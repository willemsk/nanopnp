# Getting started

## Install

nanopnp needs Python 3.11 to 3.14 on Linux, macOS or Windows. Every dependency ships as a binary
wheel, including the NGSolve finite-element library, so no compiler is needed. It is not yet on
PyPI. Install it from the repository:

```bash
pip install "nanopnp @ git+https://github.com/willemsk/nanopnp"
```

Four optional extras:

- `structure`, for building a geometry from a protein structure (stages 1 to 4:
  [Structures and trajectories](guide/structures.md));
- `gui`, for the desktop shell;
- `gmsh`, the optional mesher backend, which is GPL-licensed and never needed;
- `examples`, for the worked examples' plots.

For example, `pip install "nanopnp[structure,gui] @ git+https://github.com/willemsk/nanopnp"`.

### From a checkout

A development checkout uses [uv](https://docs.astral.sh/uv/), which installs exactly the locked
versions the test suite runs against:

```bash
git clone https://github.com/willemsk/nanopnp
cd nanopnp
uv sync --all-extras
uv run nanopnp --env
```

The `gmsh` mesher backend remains in its optional extra (`nanopnp[gmsh]`, included by `uv sync --all-extras`)
and is never a default end-user dependency (CON-10). `uv` manages Python dependencies but cannot install
system packages. On Linux, the Gmsh wheel dynamically links native OpenGL and X11 libraries:

- **Arch Linux:** `sudo pacman -S glu libxft libxinerama libxcursor`
- **Debian / Ubuntu:** `sudo apt-get install -y --no-install-recommends libglu1-mesa libxft2 libxinerama1 libxcursor1`

Without these system packages, importing `gmsh` fails with an `OSError` (`libGLU.so.1: cannot open shared object file`).

In a checkout, put `uv run` in front of every command in this documentation: `uv run nanopnp run
case.yaml`.

## Check the installation

```bash
nanopnp --env
```

`nanopnp --env` prints the version and the Python interpreter. It also prints where the correction
data files are, and where artefacts will be stored: the directory `$NANOPNP_STORE` names, or
`nanopnp-store/` in the working directory.

## Your first run

[Example 01](_generated/examples/01-quickstart.md) is four commands: generate a mesh, run a case,
inspect the run, and reproduce it. Copy `examples/01-quickstart/` from the repository and run them
from inside it. Then read [Concepts](guide/concepts.md) for what those four commands did.

## Where results go

A run writes two kinds of output:

- **The store**, `--store` or `$NANOPNP_STORE`, holds every stage's artefact under its content hash.
  It is a cache: a second run of the same case, or of a case that shares its upstream stages, is
  served from it.
- **The run directory**, `--run-dir`, or `runs/<name>-<hash>/` inside the store, holds the three
  files that describe one run: `manifest.json`, `case.yaml` and `run.json`.

`nanopnp inspect <run directory>` reads a run back, and `nanopnp reproduce <run directory>`
re-solves it and checks that every number comes back.
