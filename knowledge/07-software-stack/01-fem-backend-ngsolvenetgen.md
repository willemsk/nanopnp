---
type: Library Behaviour
title: 1. FEM backend — NGSolve/Netgen
description: 'The FEM backend NGSolve and Netgen: why not the alternatives, and prior
  art.'
tags:
- software
- library-behaviour
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
tested_with:
  ngsolve: 6.2.2606
  netgen-mesher: 6.2.2606
verified:
- by: process:tests/tier1/test_library_behaviour.py::test_ngsolve_newton_and_webgui_api
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_library_behaviour.py::test_ngsolve_wheel_table_and_config_flags
  at: '2026-10-16T00:00:00Z'
---

## 1. FEM backend — NGSolve/Netgen

**Chosen backend.** `ngsolve` / `netgen-mesher` **6.2.2606** (29 Jun 2026), **LGPL-2.1-only**.

| Fact | Value |
|---|---|
| Locked wheels | cp311–cp314, all three OSes. win_amd64 14–15.5 MB, macOS universal2 43–45 MB **[tested: tests/tier1/test_library_behaviour.py::test_ngsolve_wheel_table_and_config_flags]** |
| Compiler at runtime | **not needed** — forms are evaluated by the compiled C++ core. `Compile(realcompile=True)` is opt-in and *does* need one |
| Mixed spaces | `X = V*Q` product spaces; Taylor–Hood directly |
| Newton | `ngsolve.solvers.Newton(a, gfu, dampfactor=...)`, symbolic differentiation for the Jacobian **[tested: tests/tier1/test_library_behaviour.py::test_ngsolve_newton_and_webgui_api]** |
| Axisymmetric | one-liner: `... * x * dx` where `x` is the radial coordinate. Natural but **undocumented** |
| Rendering | `ngsolve.webgui` / `netgen.webgui`; `WebGLScene.GenerateHTML()` makes it embeddable **[tested: tests/tier1/test_library_behaviour.py::test_ngsolve_newton_and_webgui_api]** |
| Meshing | Netgen built in, with OpenCASCADE geometry — no external mesher needed |
| API stability | remarkably stable for a decade |

**Known limitations, both verified:**

1. **No MPI in the wheels** — no MPI symbols in any shipped `.so`, no mpi4py **[tested: tests/tier1/test_library_behaviour.py::test_ngsolve_wheel_table_and_config_flags]**. Parallel
   mesh generation, parallel adaptive refinement and parallel multigrid are documented as
   unsupported. Irrelevant for 2D axisymmetric v1 (direct solves; sweeps parallelise at job level);
   becomes real in 3D. Mitigations: ngsPETSc, or a DOLFINx backend for HPC only.
2. **No MUMPS/PARDISO/HYPRE/MKL in the wheels** — `ngsolve.config` reports all False **[tested: tests/tier1/test_library_behaviour.py::test_ngsolve_wheel_table_and_config_flags]**.
   See `knowledge/06-numerics-fem/06-linear-solvers.md`.
3. **2D boundary layers are immature.** Python API is
   `netgen.meshing.Mesh.BoundaryLayer2(domain, thicknesses, make_new_domain=True, boundaries=[])`
   (binding C++ `GenerateBoundaryLayer2`). The forum carries an unresolved Aug 2024 report of the
   generator failing to fill a zone adjacent to the new advancing front. Separately, the *3D*
   `Mesh.BoundaryLayer` now unconditionally raises *"Call syntax has changed! Pass a list of
   BoundaryLayerParameters to the GenerateMesh call instead"* — a trap when porting 2D code to 3D.

### 1.1 Why not the alternatives

| | Verdict |
|---|---|
| **DOLFINx 0.11.0** (9 Jun 2026, LGPL-3) | Best numerics, best docs, PETSc SNES, `MixedFunctionSpace`/`extract_blocks` for fieldsplit. **But it JIT-compiles.** README verbatim: *"PETSc and petsc4py are not available on Windows. Because FEniCS uses just-in-time compilation it necessary to install [Microsoft Visual Studio]"*. Structurally cannot become a double-clickable app. API breaks every ~8.5 months on average (0.8 Apr 2024 retired legacy `ufl.FiniteElement`; 0.9 Oct 2024 `Function.vector`→`Function.x.petsc_vec`; 0.10 Oct 2025 `io.gmshio`→`io.gmsh`). |
| **Firedrake 2026.4.x** (LGPL-3) | Excellent solver composition; **EchemFEM** already exists on it. No native Windows, no binary wheels, PETSc from source. Disqualified by the desktop requirement. |
| **scikit-fem 12.0.2** (BSD-3, 0.178 MB wheel) | Trivially bundleable, but you hand-roll Newton, block assembly, preconditioning, stabilisation; MPI is token. Good for prototyping. |
| **SfePy 2026.2** (BSD-3) | Genuinely permissive, covers coupled multi-field, but PyPI ships **sdist only**, parallel is self-described WIP, effectively single-maintainer. Weakest 5-year bet. |
| **PyMFEM 4.8 / deal.II** | No symbolic language, no AD — hand-coded Jacobian integrators for a five-field system. Non-starter. |

**The decisive argument:** choosing DOLFINx or Firedrake means needing a *second* backend for the
desktop app anyway, i.e. writing and maintaining the ePNP-NS weak forms twice, forever.

### 1.2 Prior art worth mining

| Project | Framework | Licence | Status | Use |
|---|---|---|---|---|
| **LLNL/echemfem** | Firedrake | **MIT** | active, JOSS 2024 | Best reference for SUPG-stabilised Nernst–Planck, GMPNP finite-size effects, NS/NS-Brinkman flow. No axisymmetric support. |
| **mitschabaude/nanopores** | FEniCS 2016.2, **Python 2** | MIT | dormant | *The* PNP–Stokes nanopore paper (JCP 338:452, 2017). Mine the goal-oriented adaptivity and molecule-in-pore approach. **Do not try to run it.** |
| pdelab/PyPNP | legacy dolfin | GPL-3 | dormant | No — dead API + GPL. |
| CINPLA/KNPsim | legacy FEniCS | GPL-3 | dormant | Electroneutral KNP, no flow. |
| divyabohra/GMPNP | legacy FEniCS | research artifact | dormant | 1D/3D GMPNP reference only. |
| mrshariati/FEMCorrosionSimulation | legacy FEniCS | research artifact | ~2021 | AFC/FCT flux-corrected PNP stabilisation reference. |

---

