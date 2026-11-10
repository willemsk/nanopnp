---
type: Library Behaviour
title: 9. The CLI's import budget, measured
description: The import costs of the command line, the case schema and the view-models, and what keeps NGSolve and NumPy out of them.
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
- by: process:tests/tier1/test_gui_viewmodels.py::test_if09_the_view_models_import_no_qt_and_no_ngsolve
  at: '2026-11-10T00:00:00Z'
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

### 9.1 `nanopnp.io.case` pulls in neither NGSolve nor NumPy {#nanopnpiocase-pulls-in-neither-ngsolve-nor-numpy-and-costs-250350-ms}

Measured 20 September 2026 on the development interpreter (3.12). After `import nanopnp.io.case`,
`"ngsolve" in sys.modules` and `"numpy" in sys.modules` are both `False`. The cost is pydantic and
PyYAML building the case model tree (`nanopnp/case/v1` then, `nanopnp/case/v0.6` now), paid once.

So a caller can enumerate, display and validate an entire case document without the solver — which
is what lets a schema-generated editor stay near the CLI's 56 ms stage-introspection budget in
spirit, with NGSolve imported only in whatever process actually solves. `io/case.py` imports only
`core` at run time: the registry checks that need `materials` and `physics` live in
`pipeline/checks.py`. After `import nanopnp.io.case` the only `nanopnp` subpackages in
`sys.modules` are `core` and `io` **[tested: tests/tier1/test_library_behaviour.py::test_cli_deferred_imports_and_hashing_duck_typing]**, 6 October 2026. `import nanopnp.pipeline.case`,
which holds the case loader and the resolver that `Case.load` and `Session.run` call, also loads `charge`, `density`, `geometry`, `materials`,
`mesh`, `numerics` and `physics`, and still leaves `ngsolve` and `numpy` out of `sys.modules`; that
holds because those modules defer their own NGSolve and NumPy imports.

**Measured 20 September 2026 on an idle container, not asserted: 349 ms cold (no `__pycache__`), 253 ms
warm.** **Treat the absolute number as machine-dependent and the ratio as the fact**: importing the case schema costs roughly what one
NGSolve import (~370 ms) costs, and the load-bearing half — neither `ngsolve` nor `numpy` in
`sys.modules` afterwards — is re-confirmed and is not a timing claim at all.

### 9.2 The desktop shell's view-model layer costs what the schema costs {#the-desktop-shells-view-model-layer-costs-what-the-schema-costs}

Measured 20 September 2026, best of three on an idle container, warm cache, not asserted:

| Module | Cost | What it pulls in |
|---|---|---|
| `nanopnp.io.case` | 253 ms | pydantic and PyYAML building the case model tree (`nanopnp/case/v1` then, `nanopnp/case/v0.6` now) |
| `nanopnp.gui.case_model` | 251 ms | the above, and about a millisecond of its own |
| `nanopnp.gui.run_model` | 273 ms | the above, plus `io/manifest.py` and `pipeline/run.py` |
| `nanopnp.gui.solver` | 73 ms | `core/errors.py` and `multiprocessing`; everything else is deferred into the child |
| `nanopnp.gui.probe` | 59 ms | `core/paths.py` only — every payload is deferred |
| `nanopnp.cli` | 62 ms | the comparison, and the budget the deferred-import rule protects |

After importing all three view-models, **none** of `PySide6`, `PyQt5`, `PyQt6`, `ngsolve`, `netgen`
or `numpy` is in `sys.modules`, asserted in a subprocess **[tested: tests/tier1/test_gui_viewmodels.py::test_if09_the_view_models_import_no_qt_and_no_ngsolve]**. The
editor therefore enumerates and validates the whole schema at the cost of the schema, and a shell
that is only browsing a case never pays for a solver or a toolkit.
