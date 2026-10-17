---
type: Library Behaviour
title: 8. Python version floor — the 3.10 target is not free
description: The Python version floor, and what a 3.10 target would cost.
tags:
- software
- library-behaviour
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
sources:
- id: wp17-plan
  resource: docs/plans/wp17-case-schema-v2.md
  title: WP17 case schema v2 plan (Python 3.11 floor and wheel resolution)
- id: wp43-plan
  resource: docs/plans/wp43-development-loop.md
  title: WP43 development loop plan, D12 (CPython 3.14 VER-62 check)
tested_with:
  mdanalysis: 2.10.0
  griddataformats: 1.2.0
  pdb2pqr: 3.7.1
  ngsolve: 6.2.2606
  numpy: 2.5.2
  scipy: 1.18.0
  mypy: 2.3.1
verified:
- by: process:arithmetic
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_library_behaviour.py::test_ngsolve_wheel_table_and_config_flags
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_library_behaviour.py::test_pyproject_requires_python_311_and_griddata_12
  at: '2026-10-16T00:00:00Z'
---

## 8. Python version floor — the 3.10 target is not free

**Resolved, 24 September 2026 [tested: tests/tier1/test_library_behaviour.py::test_pyproject_requires_python_311_and_griddata_12]: the floor is now 3.11** (§8.2.2 B4, WP17). With
`requires-python = ">=3.11,<3.15"` and the `structure` extra at `MDAnalysis>=2.10`,
`GridDataFormats>=1.2`, `pdb2pqr>=3.7`, `uv lock` resolves one version of each across the range:
MDAnalysis 2.10.0, GridDataFormats 1.2.0, pdb2pqr 3.7.1. The 3.10 splits the lock carried for
numpy, scipy, scikit-image and tifffile went with it. The rest of this section is the analysis that
led there.

Resolved with `uv 0.12.5`, August 2026, against live PyPI **[verified][^wp17-plan]**.

The specification asks for Python 3.10–3.14 (QR-09). The FEM backend delivers: `ngsolve` 6.2.2606
publishes wheels for **cp310 through cp314 on manylinux_2_28_x86_64, macosx_10_15_universal2 and
win_amd64** — fifteen wheels, no gaps **[verified][^wp17-plan]**.

The *structure* pipeline does not. Both of the versions named in the specification have dropped
Python 3.10:

| Package | Version in SPECIFICATION.md §2.6 | Requires |
|---|---|---|
| MDAnalysis | 2.10.0 | Python ≥ 3.11 |
| GridDataFormats | 1.2.0 (and 1.1.0) | Python ≥ 3.11 |

A dependency set naming both and `requires-python = ">=3.10"` is **unsatisfiable** — uv fails
resolution for the 3.10 split rather than silently excluding it. Two ways out: lower the floors to
the last releases that still support 3.10 (MDAnalysis 2.7, GridDataFormats 1.0.2), which is what
`pyproject.toml` currently does with a comment, so that 3.11+ still resolves to the specified
versions; or raise the project floor to 3.11 and amend QR-09. The choice becomes forced the moment
the geometry pipeline needs an API that only MDAnalysis 2.10 has.

Separately, and more happily: with all extras enabled (`structure`, `gui`, `gmsh`, dev group), the
resolved lock contains **no sdist-only package** — every dependency, `ngsolve`, `PySide6`, `gmsh`,
`pdb2pqr`, `MDAnalysis`, `scikit-image` and `h5py` included, installs from a binary wheel
**[tested: tests/tier1/test_library_behaviour.py::test_ngsolve_wheel_table_and_config_flags]**. Nothing in the current dependency set contradicts CON-07.

**The local gate cannot see a 3.10 floor break; only the CI matrix can [verified][^wp17-plan].** The gate of
`CLAUDE.md` runs on the development interpreter — 3.14 — so a 3.11+ stdlib API compiles, typechecks
and passes every test locally while failing `tier 1-2 (ubuntu-latest, py3.10)` at *collection*.
`datetime.UTC` is the worked example: it is 3.11+, `datetime.timezone.utc` is the equivalent
available across the whole supported range, and the import error takes down every test module that
transitively reaches it rather than one assertion.

Typechecking at the floor would catch this class — `mypy --python-version=3.10` reports
`Module "datetime" has no attribute "UTC"  [attr-defined]` on a two-line file **[verified][^wp17-plan]** — but it
cannot currently be run over `src/`: NumPy's own bundled stubs use a PEP 695 `type` statement, and
mypy aborts the whole check with `numpy/__init__.pyi:737: error: Type statement is only supported in
Python 3.12 and greater  [syntax]` before reaching project code **[verified][^wp17-plan]**. So the guard is the
3.10 matrix job, and reproducing a matrix-only failure means `uv run --python 3.10 --all-extras
pytest`, which resolves and installs a separate 3.10 environment in about a minute.

**The development interpreter is 3.14, and it computes VER-62's numbers as 3.12 does [verified][^wp43-plan].**
`uv.lock` splits its resolution only at 3.12, so 3.12 and 3.14 install the same version of every
package (NumPy 2.5.2, SciPy 1.18.0, NGSolve 6.2.2606), each from a wheel (cp314, abi3 or pure Python; none built from source). On CPython
3.14.6, `linux-x86_64` with NumPy's dispatch capped at `X86_V3` (`NPY_DISABLE_CPU_FEATURES`, as CI
and the gate set it), the six walk files of the number-stability golden pass under `--extended`:
all seven walks deploy their recorded reference mesh, and the largest relative drift against the
golden recorded on 3.12 is 6.9 × 10⁻¹⁴ (example 01's `eof_m3_s`; every other walk at or below
2.7 × 10⁻¹⁵), 12 October 2026 (WP43, D12). Every locked package has a cp314 wheel on Linux, macOS
and Windows except `watchdog` on macOS arm64, which only the `docs` group pulls and the
documentation builds on ubuntu. PROPKA needs the 3.14 shim of §3 there as everywhere.

---

[^wp17-plan]: `docs/plans/wp17-case-schema-v2.md` and `SPECIFICATION.md` §8.2.2 B4 (Python 3.11 floor and pre-floor 3.10 observations).
[^wp43-plan]: `docs/plans/wp43-development-loop.md`, D12 (CPython 3.14.6 VER-62 golden drift check).

