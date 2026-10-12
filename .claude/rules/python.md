---
paths:
  - "src/**/*.py"
  - "tests/**/*.py"
  - ".claude/scripts/**/*.py"
  - ".github/scripts/**/*.py"
  - "docs/scripts/**/*.py"
---

## Coding conventions

- `from __future__ import annotations` in every module; type hints on every signature; `mypy --strict` clean.
- NumPy-style docstrings on public functions.
- SI internally; units in the name at the boundary (`radius_nm`, `bias_V`). No bare floats in interfaces.
- British spelling in prose and identifiers (`normalise`, `analyse`).
- `pathlib.Path`, never `os.path`. f-strings, never `%`/`.format()` (exceptions: one `%` over a whole
  numeric array as in `validation/apbs.py`'s `write_dx`; lazy `logging` arguments).
- Pydantic models at every serialisation boundary; never raw dicts across a stage boundary.
- `logging`, never `print()`, outside the CLI's own output. No `import *`.
- Cite the source (`.knowledge/` file or specification section) of every physical constant and fit
  coefficient in a comment.
- **Imports at the top of the module.** Exceptions, imported inside the function that uses them:
  `ngsolve`, `netgen`, `numpy`, `scipy`, `meshio`, `h5py` (import cost; stage modules are imported
  just to introspect), and an optional extra's package in a module that must work without it (a
  missing extra is refused naming it). A module reached only through `create()`, such as
  `structure/read.py`, imports its extra at the top. Defer nothing else; VER-72 (a) checks it.
