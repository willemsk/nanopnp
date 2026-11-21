---
type: Specification
title: "5.6 Architecture decisions"
description: "Records the architecture decisions, beginning with NGSolve as the single production backend against which the weak forms are stated once (§5.4.1)."
---

### 5.6 Architecture decisions

#### ADR-001 FEM backend

Decision: NGSolve 6.2.2606+ (LGPL-2.1) as the single production backend; the weak forms are stated
once against it (§5.4.1).

| Alternative | Assessment |
|---|---|
| DOLFINx 0.11 | Best numerics, best documentation, PETSc SNES, largest community. JIT-compiles, so the end user needs a C++ compiler; its README states PETSc and petsc4py are not available on Windows and that Visual Studio must be installed. Heavyweight conda environment. API break every 8.5 months on average: v0.8 (Apr 2024) retired the legacy `ufl.FiniteElement` constructor, v0.9 (Oct 2024) moved `Function.vector` to `Function.x.petsc_vec`, v0.10 (Oct 2025) renamed `dolfinx.io.gmshio` to `dolfinx.io.gmsh`, v0.11 (Jun 2026) |
| Firedrake 2026.4 | Excellent solver composition, and EchemFEM already runs on it. No Windows support, no binary wheels, PETSc built from source |
| scikit-fem 12 | BSD-3, 0.2 MB wheel, trivially bundleable, but Newton, block assembly, preconditioning and stabilisation are hand-rolled and MPI is token |
| SfePy 2026.2 | BSD-3 and covers coupled multi-field, but PyPI ships sdist only, parallel support is self-described work-in-progress, and it is effectively single-maintainer |
| PyMFEM, deal.II | No symbolic language, no automatic differentiation; Jacobian integrators for a five-field system must be hand-coded |

Grounds: self-contained wheels (15 MB Windows, 44 MB macOS universal2) for Python 3.11–3.14 on all
three operating systems, no compiler at runtime; Netgen built in, so the default path never links
GPL Gmsh; product spaces `X = V*Q` giving the five-field monolithic system and Taylor–Hood
directly; symbolic differentiation giving `Newton(a, gfu, dampfactor=...)`; axisymmetric assembly
as `... * x * dx`; embeddable webgui (three.js); a decade of API stability. DOLFINx and Firedrake would each need a second
backend for the desktop path, so the weak forms would be maintained twice indefinitely.

| Consequence | Detail and mitigation |
|---|---|
| MPI | Pip wheels are serial-only (verified on 6.2.2606: NGSolve's shared objects reference no MPI symbol and mpi4py is not installed; `netgen-mesher` ships two optional MPI plugins, `ng_openmpi.so` and `ng_mpich.so`, whose MPI symbols only a system MPI library resolves); parallel mesh generation, adaptive refinement and multigrid are unsupported. This costs v1 nothing: 2D axisymmetric solves are direct-solver territory and sweeps parallelise at the job level |
| No MUMPS in the wheel | The wheel reports `USE_MUMPS: False` (also `USE_HYPRE`, `USE_PARDISO`, `USE_MKL`), and `inverse="mumps"` raises `SparseMatrix::InverseMatrix: no inverse available for type mumps`. MUMPS needs a source build with MPI, reintroducing the compiler dependency this decision exists to avoid. The desktop path uses UMFPACK or scipy SuperLU (CON-08); the reference COMSOL model used PARDISO, equally absent from the wheel |
| Direct-solver performance | Whether UMFPACK factorises the coupled five-field system at production mesh size in acceptable time and memory is a Phase 0 exit criterion (§8.2, QR-07) |
| 3D phase | Mitigations in order: prototype 3D scaling before committing; route parallel solves through ngsPETSc to reach PETSc fieldsplit and AMG; if 3D scaling proves fatal, add a DOLFINx backend for HPC only, through the interface shape of §5.4.1, taking EchemFEM (LLNL, MIT, Firedrake) as the reference implementation of SUPG-stabilised Nernst–Planck |

#### ADR-002 Meshing backend and the Gmsh licence

Decision: mesher adapters, Netgen (LGPL-2.1) as default and Gmsh (GPLv2+) as optional backend.
Boundary layers, when FR-11 adds them after 1.0, take the geometric construction of §5.2.2, so that
the default path does not depend on Netgen's less-mature 2D boundary-layer generator.

| Alternative | Assessment |
|---|---|
| Gmsh as default | Best boundary-layer tooling for this problem, but the `gmsh` PyPI wheel is GPLv2+ and use through its Python API is linking, which would make the core library GPL |
| Netgen only, no adapter | Forgoes the Gmsh size-field algebra for users who accept GPL, at no gain |
| MeshPy, TetGen 1.5, pygmsh, pygalmesh | Excluded by CON-12: Triangle's distribution restriction, AGPLv3, and staleness respectively |

Consequences: the core library stays permissively licensable and functional without Gmsh (CON-10);
Gmsh is the `gmsh` extra, and an installation without it is complete.

**Delivered** (WP23, VER-54). `numerics.mesh.backend: gmsh` meshes the region
stage 5 assembled with `netgen.occ`, read from its named edges into Gmsh's built-in kernel, under the
size field of the §5.2.2 NOTE on the Gmsh backend, and joins netgen's route at the MSH 4.1 writer,
so every gate is shared. Gmsh assembles no region of its own. Boundary layers remain FR-11, after
v1.0.

#### ADR-003 Project licence

Decision: BSD-3-Clause core library with GPL-compatible optional extras. No institutional
constraint applies.

| Alternative | Assessment |
|---|---|
| GPL core, Gmsh in the default path | Deferred, not foreclosed: the package has no other GPL entanglement, so this stays a one-line relicense should GPL become acceptable |
| PyQt for a desktop shell | Rejected: GPL-3 or commercial only (CON-09) |
| An installation defaulting to scipy SuperLU | Rejected on measurement (§6.6): SuperLU was OOM-killed on the reference-sized factorisation, so a SuperLU-default installation cannot run the published case. The installed workbench defaults to UMFPACK through NGSolve's wheel and carries the GPL-2+ obligation that follows, which `nanopnp --env` states; the library itself stays BSD-3 and depends on neither (CON-11) |

Consequences: BSD-3 maximises adoption where both academic and industrial reuse matter and matches
the scientific Python stack. Dependencies are compatible: NGSolve and Netgen LGPL-2.1 (dynamic
linking), MDAnalysis LGPLv3, PDB2PQR BSD, APBS BSD-3, scikit-image BSD-3, Shapely BSD-3, meshio
MIT, NiceGUI MIT, FastAPI BSD-3. Gmsh is GPLv2+, hence optional. The repository carries a `CITATION.cff`
pointing at the Nanoscale paper and the software DOI (CON-14).

#### ADR-004 Graphical interface

Decision (§8.2.12 M3; §8.2.30 AF4): a browser workbench, NiceGUI on FastAPI in `gui/web/`,
distributed as the `gui` extra (§8.2.17 S17). A background solver process communicates over a
queue, so the interface stays responsive and shows live convergence.

| Alternative | Assessment |
|---|---|
| A PySide6 (Qt) desktop shell | Superseded: the shell of Phases 1 to 4, removed at WP5.27 for the browser workbench (§8.2.12 M3; §8.2.17 S12, S17) |
| PyQt6 shell | Rejected: GPL-3 only |
| Local web application: FastAPI plus browser frontend wrapped in `pywebview` | Chosen for Phase 5 as the decision above, without `pywebview` (§8.2.12 M3; the desktop-wrapper NOTE) |
| Defer the interface to a terminal phase | Rejected on two failure modes: an interface bolted on at the end exposes the API's accidental structure rather than the user's workflow, and a nine-month gap before any non-programmer touches the tool is a nine-month gap in shaping feedback |

NOTE (packaging). The workbench SHALL be distributed as the package with its `gui` extra, installed
by one documented `uv` command, with no bundle (§8.2.17 S12). Its front end SHALL ship prebuilt inside
the wheel, so no user builds it (CON-07), and the shipped renderer SHALL stay an unmodified, separate
file (CON-09). The server's self-test, `nanopnp gui --selftest`, SHALL exercise once each, failing
naming the payload: NGSolve and Netgen meshing a square, and a server child serving the shipped
renderer, compared by its bytes; MDAnalysis and gemmi reading a structure, scikit-image's contour
extraction and Shapely's polygon checks through GEOS, and Gmsh where its extra is installed; PDB2PQR
and PROPKA protonating a nine-residue peptide at two pH values, whose two net charges it requires, so
that PROPKA's parameter file out of reach fails naming PROPKA. An extension that imports and then
cannot load its library is RSK-13's failure, which an import alone does not detect: Gmsh's Python
module imports with its library missing and fails on its first call
(`knowledge/07-software-stack/05-gui-and-packaging.md`). The background solver process SHALL be started
with the `spawn` start method: it is the only one Windows has, and a forked child would inherit the
server's event loop and its already-imported numerical libraries.

Consequences: every pipeline stage must be independently invocable, cancellable, progress-reporting
and introspectable (FR-27), which §5.1 requires on scientific grounds in any case, so the interface
is a thin shell over the stage objects the CLI drives (IF-09). Each release from v0.2 onward ships
a usable graphical surface over the functionality existing at that release (QR-11); the per-phase
increments are in §8.1.

NOTE (the desktop wrapper, v0.6). The browser shell SHALL NOT preclude a desktop wrapper, such as
Electron, that spawns its server and loads its address; no wrapper is built before 1.0 (§8.2.17 S12;
§8.2.30 AF1). The front end SHALL reach its server only through relative URLs, SHALL fetch nothing
from a network at run time, and SHALL choose a file or folder through the server rather than by a
browser upload. `nanopnp gui --no-browser --port 0` SHALL start the server on the loopback interface,
write one ready line naming its address to standard output, and stop its builds and their child
processes when its standard input closes or it receives an interrupt or termination signal. The server
SHALL refuse a request whose `Host` is not a loopback name, and one that carries neither the
per-launch token of the address it printed nor the cookie that token sets.

NOTE (the front end, v0.6). The workbench's front end SHALL be written in Python with NiceGUI, on the
FastAPI server of the desktop-wrapper NOTE; it has no build step, and NiceGUI's own Vue layer ships
prebuilt (CON-07). JavaScript SHALL be the bridge to a renderer and nothing else. The renderers are Mol*
for the molecule, as its unmodified standalone bundle served as separate files (CON-09), and, from the tree of results' package (WP5.22, moved to Phase 6 by
§8.2.47 AW1),
Plotly (plotly.js, MIT) as NiceGUI ships it, unmodified, for every plot of y against x and every (r, z) view:
maps, meshes, drawings and the field turned about the axis, each axis linear or logarithmic, a
square-root axis drawn as its root with ticks in its own units, its range typed by the user (WB-57,
restating §8.2.45 AU1). Until that package lands, `webgui` draws meshes and fields (VER-44), a canvas the
(r, z) maps, and uPlot 1.6.32 (MIT), vendored unmodified as separate files beside Mol* and KaTeX
(CON-09), every plot of y against x. A call
that starts the viewer from Python SHALL pass a timeout longer than the viewer's start, and a screen SHALL
set `data-screen-ready` only when its viewer has built and drawn once. The author chose NiceGUI over
a React application on the spike's six measures (`docs/design/spike/report.md`; §8.2.30 AF4).

#### ADR-005 Two levels of pluggability

Decision: correction models as data files (level 1) and physics models as classes (level 2), per
§5.5, so that a user comfortable with a little coding can modify or add implementations
transparently and Poisson–Boltzmann is available alongside PNP-NS.

| Alternative | Assessment |
|---|---|
| One extension point, data files only | Insufficient: `pb` and `pb-linear` have a different field set and solve strategy, which no coefficient file expresses |
| One extension point, code only | Makes a new electrolyte a patch to the source tree and loses per-result recording of the parameter version |
| A general symbolic PDE framework | Rejected as N1; the validation surface would be unbounded |

Consequences: a new electrolyte or surface is a data file rather than a code change (FR-16); every
result records which correction version produced it (FR-25); PNP-NS is a configuration of ePNP-NS
rather than separate code (FR-18, PHY-21); Poisson–Boltzmann is a distinct model rather than the
PNP solver at zero bias (PHY-24); correction-by-correction differential testing is a sweep (§7.4).
