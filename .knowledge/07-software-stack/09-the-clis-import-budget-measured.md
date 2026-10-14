---
type: Library Behaviour
title: 9. The CLI's import budget, measured
---

## 9. The CLI's import budget, measured **[tested]** {#9-the-clis-import-budget-measured}

`import nanopnp.cli` costs **55.6 ms cumulative** (`python -X importtime`), and a cold subprocess
that imports it and exits takes **0.082 s**. `import ngsolve` alone is ~370 ms, and the physics and
mesh modules at module scope would take the package's own share from 56 ms to 424 ms. A sweep
dispatching a job array pays that per process, which is what the deferred-import rule of
`CLAUDE.md` buys. `import numpy` alone is ~67 ms, which is why `core/hashing.py` detects arrays by
duck-typing rather than importing NumPy **[tested]**.

Two mechanisms keep it there, and both are load-bearing rather than tidy:

- **The stage registry holds descriptions beside `"module:attribute"` target strings**, and
  `nanopnp.core.stages.create` is the only function that resolves one. `nanopnp stage --list`
  therefore answers from data. Asserted in a subprocess: after `main(["stage", "--list"])` no
  module matching `ngsolve*` or `netgen*` is in `sys.modules` **[tested]**.

- **The IF-02 exit-code table is keyed on `f"{cls.__module__}:{cls.__qualname__}"` strings**, and
  `classify` walks `type(error).__mro__` looking each name up. Classifying an error therefore
  imports no exception module — which matters because the table names classes in `solve`, `mesh`,
  `charge` and `post`, and a table of *class objects* would import all four at CLI start.
  Asserted the same way, on the table's own module list **[tested]**.

The MRO walk is not incidental: it is what makes a subclass of a classified exception inherit its
exit code, so a narrower gate error added later is still a `4` rather than falling to `1`.

