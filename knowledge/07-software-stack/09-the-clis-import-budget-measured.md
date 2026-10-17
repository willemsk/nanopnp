---
type: Library Behaviour
title: 9. The CLI's import budget, measured
description: The command line's import budget, measured.
tags:
- software
- library-behaviour
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
tested_with:
  ngsolve: 6.2.2606
  numpy: 2.5.2
verified:
- by: process:tests/tier1/test_cli.py::test_ver32_classifying_imports_no_exception_module
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_cli.py::test_ver32_stage_list_imports_no_stage_module
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_library_behaviour.py::test_cli_deferred_imports_and_hashing_duck_typing
  at: '2026-10-16T00:00:00Z'
---

## 9. The CLI's import budget, measured **[tested: tests/tier1/test_library_behaviour.py::test_cli_deferred_imports_and_hashing_duck_typing]** {#9-the-clis-import-budget-measured}

`import nanopnp.cli` costs **55.6 ms cumulative** (`python -X importtime`), and a cold subprocess
that imports it and exits takes **0.082 s**. `import ngsolve` alone is ~370 ms, and the physics and
mesh modules at module scope would take the package's own share from 56 ms to 424 ms. A sweep
dispatching a job array pays that per process, which is what the deferred-import rule of
`CLAUDE.md` buys. `import numpy` alone is ~67 ms, which is why `core/hashing.py` detects arrays by
duck-typing rather than importing NumPy **[tested: tests/tier1/test_library_behaviour.py::test_cli_deferred_imports_and_hashing_duck_typing]**.

Two mechanisms keep it there, and both are load-bearing rather than tidy:

- **The stage registry holds descriptions beside `"module:attribute"` target strings**, and
  `nanopnp.core.stages.create` is the only function that resolves one. `nanopnp stage --list`
  therefore answers from data. Asserted in a subprocess: after `main(["stage", "--list"])` no
  module matching `ngsolve*` or `netgen*` is in `sys.modules` **[tested: tests/tier1/test_cli.py::test_ver32_stage_list_imports_no_stage_module]**.

- **The IF-02 exit-code table is keyed on `f"{cls.__module__}:{cls.__qualname__}"` strings**, and
  `classify` walks `type(error).__mro__` looking each name up. Classifying an error therefore
  imports no exception module — which matters because the table names classes in `solve`, `mesh`,
  `charge` and `post`, and a table of *class objects* would import all four at CLI start.
  Asserted the same way, on the table's own module list **[tested: tests/tier1/test_cli.py::test_ver32_classifying_imports_no_exception_module]**.

The MRO walk is not incidental: it is what makes a subclass of a classified exception inherit its
exit code, so a narrower gate error added later is still a `4` rather than falling to `1`.

