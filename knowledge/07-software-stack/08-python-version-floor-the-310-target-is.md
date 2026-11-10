---
type: Library Behaviour
title: 8. Python 3.11 floor and the 3.14 development interpreter
description: Why the floor is 3.11, and what the 3.14 development interpreter changes.
tags:
- software
- library-behaviour
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
sources:
- id: wp17-plan
  resource: docs/plans/phase-2/wp17-case-schema-v2.md
  title: WP17 case schema v2 plan (Python 3.11 floor and wheel resolution)
- id: wp43-plan
  resource: docs/plans/phase-4/wp43-development-loop.md
  title: WP43 development loop plan, D12 (CPython 3.14 VER-62 check)
tested_with:
  mdanalysis: 2.10.0
  griddataformats: 1.2.0
  pdb2pqr: 3.8.0
  ngsolve: 6.2.2606
  numpy: 2.5.2
  scipy: 1.18.0
  mypy: 2.3.1
verified:
- by: process:arithmetic
  at: '2026-10-16T00:00:00Z'
---

## 8. Python 3.11 floor and the 3.14 development interpreter {#8-python-version-floor-the-310-target-is-not-free}

**The floor is 3.11 [verified][^wp17-plan]** (§8.2.2 B4, WP17; QR-09). MDAnalysis 2.10 and
GridDataFormats 1.1 and later require Python ≥ 3.11, so a set naming them with
`requires-python = ">=3.10"` cannot resolve. With `requires-python = ">=3.11,<3.15"`, `uv lock`
resolves one version of each package across the range (`uv.lock`).

`ngsolve` 6.2.2606 publishes wheels for cp311 to cp314 on manylinux_2_28_x86_64,
macosx_10_15_universal2 and win_amd64: twelve wheels, no gaps (`uv.lock`).

With all extras enabled (`structure`, `gui`, `gmsh`, dev group), the resolved lock contains **no
sdist-only package**: every dependency, `ngsolve`, `PySide6`, `gmsh`, `pdb2pqr`, `MDAnalysis`,
`scikit-image` and `h5py` included, installs from a binary wheel **[verified][^wp17-plan]**. Nothing
in the dependency set contradicts CON-07.

**The development interpreter is 3.14, and it computes VER-62's numbers as 3.12 does [verified][^wp43-plan].**
`uv.lock` splits its resolution only at 3.12, so 3.12 and 3.14 install the same version of every
package (NumPy 2.5.2, SciPy 1.18.0, NGSolve 6.2.2606), each from a wheel (cp314, abi3 or pure Python; none built from source). On CPython
3.14.6, `linux-x86_64` with NumPy's dispatch capped at `X86_V3` (`NPY_DISABLE_CPU_FEATURES`, as CI
and the gate set it), the six walk files of the number-stability golden passed under `--extended` (now `--nightly`):
all seven walks deploy their recorded reference mesh, and the largest relative drift against the
golden recorded on 3.12 is 6.9 × 10⁻¹⁴ (example 01's `eof_m3_s`; every other walk at or below
2.7 × 10⁻¹⁵), 12 October 2026 (WP43, D12). Every locked package has a cp314 wheel on Linux, macOS
and Windows except `watchdog` on macOS arm64, which only the `docs` group pulls and the
documentation builds on ubuntu. PROPKA needs the 3.14 shim of `03-charge-and-electrostatics.md` there as everywhere.

---

[^wp17-plan]: `docs/plans/phase-2/wp17-case-schema-v2.md` and `SPECIFICATION.md` §8.2.2 B4 (Python 3.11 floor and pre-floor 3.10 observations).
[^wp43-plan]: `docs/plans/phase-4/wp43-development-loop.md`, D12 (CPython 3.14.6 VER-62 golden drift check).

