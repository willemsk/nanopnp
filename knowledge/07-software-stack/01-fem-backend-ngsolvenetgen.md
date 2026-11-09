---
type: Library Behaviour
title: 1. FEM backend — NGSolve/Netgen
description: 'The FEM backend NGSolve and Netgen: what the wheels hold and lack, and prior
  art; the alternatives are ADR-001''s.'
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
- by: process:tests/tier1/test_ngsolve_traps.py::test_ngsolve_trap_gouy_chapman_reaction_flux_and_solver_facts
  at: '2026-11-08T00:00:00Z'
---

## 1. FEM backend — NGSolve/Netgen

**Chosen backend.** `ngsolve` / `netgen-mesher` **6.2.2606** (29 Jun 2026), **LGPL-2.1-only**.

| Fact | Value |
|---|---|
| Locked wheels | cp311–cp314, all three OSes. win_amd64 14–15.5 MB, macOS universal2 43–45 MB |
| Compiler at runtime | **not needed** — forms are evaluated by the compiled C++ core. `Compile(realcompile=True)` is opt-in and *does* need one |
| Mixed spaces | `X = V*Q` product spaces; Taylor–Hood directly |
| Newton | `ngsolve.solvers.Newton(a, gfu, dampfactor=...)`, symbolic differentiation for the Jacobian **[tested: tests/tier1/test_library_behaviour.py::test_ngsolve_newton_and_webgui_api]** |
| Axisymmetric | one-liner: `... * x * dx` where `x` is the radial coordinate. Natural but **undocumented** |
| Rendering | `ngsolve.webgui` / `netgen.webgui`; `WebGLScene.GenerateHTML()` makes it embeddable **[tested: tests/tier1/test_library_behaviour.py::test_ngsolve_newton_and_webgui_api]** |
| Meshing | Netgen built in, with OpenCASCADE geometry — no external mesher needed |
| API stability | remarkably stable for a decade |

**Alternatives and consequences:** ADR-001 (`specification/05-software-design/06-architecture-decisions.md`)
holds the alternatives, the second-backend argument and the MPI and MUMPS consequences. Tested here:

1. **No MPI and no MUMPS, PARDISO, HYPRE or MKL in the wheels, as far as the lock file and the
   build configuration show** — `mpi4py` is not a locked package, and `ngsolve.config` reports
   MUMPS, PARDISO and MKL False
   **[tested: tests/tier1/test_ngsolve_traps.py::test_ngsolve_trap_gouy_chapman_reaction_flux_and_solver_facts]**,
   and HYPRE False as well (ADR-001). The shipped binaries are not scanned for MPI symbols. The linear solvers:
   `knowledge/06-numerics-fem/06-linear-solvers.md`.
2. **2D boundary layers are immature.** Python API is
   `netgen.meshing.Mesh.BoundaryLayer2(domain, thicknesses, make_new_domain=True, boundaries=[])`
   (binding C++ `GenerateBoundaryLayer2`). The forum carries an unresolved Aug 2024 report of the
   generator failing to fill a zone adjacent to the new advancing front. Separately, the *3D*
   `Mesh.BoundaryLayer` now unconditionally raises *"Call syntax has changed! Pass a list of
   BoundaryLayerParameters to the GenerateMesh call instead"* — a trap when porting 2D code to 3D.

### 1.1 Why not the alternatives

ADR-001 holds the assessment of DOLFINx, Firedrake, scikit-fem, SfePy, PyMFEM and deal.II.

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

