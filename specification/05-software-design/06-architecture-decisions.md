---
type: Specification
title: "5.6 Architecture decisions"
description: "Records the architecture decisions, beginning with NGSolve as the single production backend behind the abstraction of §5.4.1."
---

### 5.6 Architecture decisions

#### ADR-001 FEM backend

Decision: NGSolve 6.2.2606+ (LGPL-2.1) as the single production backend, behind the abstraction of
§5.4.1.

| Alternative | Assessment |
|---|---|
| DOLFINx 0.11 | Best numerics, best documentation, PETSc SNES, largest community. JIT-compiles, so the end user needs a C++ compiler; its README states PETSc and petsc4py are not available on Windows and that Visual Studio must be installed. Heavyweight conda environment. API break every 8.5 months on average: v0.8 (Apr 2024) retired the legacy `ufl.FiniteElement` constructor, v0.9 (Oct 2024) moved `Function.vector` to `Function.x.petsc_vec`, v0.10 (Oct 2025) renamed `dolfinx.io.gmshio` to `dolfinx.io.gmsh`, v0.11 (Jun 2026) |
| Firedrake 2026.4 | Excellent solver composition, and EchemFEM already runs on it. No Windows support, no binary wheels, PETSc built from source |
| scikit-fem 12 | BSD-3, 0.2 MB wheel, trivially bundleable, but Newton, block assembly, preconditioning and stabilisation are hand-rolled and MPI is token |
| SfePy 2026.2 | BSD-3 and covers coupled multi-field, but PyPI ships sdist only, parallel support is self-described work-in-progress, and it is effectively single-maintainer |
| PyMFEM, deal.II | No symbolic language, no automatic differentiation; Jacobian integrators for a five-field system must be hand-coded |

Grounds: self-contained wheels (15 MB Windows, 44 MB macOS universal2) for Python 3.10–3.14 on all
three operating systems, no compiler at runtime; Netgen built in, so the default path never links
GPL Gmsh; product spaces `X = V*Q` giving the five-field monolithic system and Taylor–Hood
directly; symbolic differentiation giving `Newton(a, gfu, dampfactor=...)`; axisymmetric assembly
as `... * x * dx`; embeddable webgui (three.js); a decade of API stability. DOLFINx and Firedrake would each need a second
backend for the desktop path, so the weak forms would be maintained twice indefinitely.

| Consequence | Detail and mitigation |
|---|---|
| MPI | Pip wheels are serial-only (verified: no MPI symbols in any shipped `.so`, no mpi4py); parallel mesh generation, adaptive refinement and multigrid are unsupported. This costs v1 nothing: 2D axisymmetric solves are direct-solver territory and sweeps parallelise at the job level |
| No MUMPS in the wheel | The wheel reports `USE_MUMPS: False` (also `USE_HYPRE`, `USE_PARDISO`, `USE_MKL`), and `inverse="mumps"` raises `SparseMatrix::InverseMatrix: no inverse available for type mumps`. MUMPS needs a source build with MPI, reintroducing the compiler dependency this decision exists to avoid. The desktop path uses UMFPACK or scipy SuperLU (CON-08); the reference COMSOL model used PARDISO, equally absent from the wheel |
| Direct-solver performance | Whether UMFPACK factorises the coupled five-field system at production mesh size in acceptable time and memory is a Phase 0 exit criterion (§8.2, QR-07) |
| 3D phase | Mitigations in order: prototype 3D scaling before committing; route parallel solves through ngsPETSc to reach PETSc fieldsplit and AMG; if 3D scaling proves fatal, add a DOLFINx backend for HPC only behind the existing abstraction, taking EchemFEM (LLNL, MIT, Firedrake) as the reference implementation of SUPG-stabilised Nernst–Planck |

#### ADR-002 Meshing backend and the Gmsh licence

Decision: mesher adapters, Netgen (LGPL-2.1) as default and Gmsh (GPLv2+) as optional backend, with
the geometric boundary-layer construction of §5.2.2 so the default path does not depend on Netgen's
less-mature 2D boundary-layer generator.

| Alternative | Assessment |
|---|---|
| Gmsh as default | Best boundary-layer tooling for this problem, but the `gmsh` PyPI wheel is GPLv2+ and use through its Python API is linking, which would make the core library GPL |
| Netgen only, no adapter | Forgoes the Gmsh size-field algebra for users who accept GPL, at no gain |
| MeshPy, TetGen 1.5, pygmsh, pygalmesh | Excluded by CON-12: Triangle's distribution restriction, AGPLv3, and staleness respectively |

Consequences: the core library stays permissively licensable and functional without Gmsh (CON-10);
the contents of the distributed desktop bundle remain a later decision.

**Delivered** (WP23, VER-54). `numerics.mesh.backend: gmsh` meshes the region
stage 5 assembled with `netgen.occ`, read from its named edges into Gmsh's built-in kernel, under the
size field of the §5.2.2 NOTE on the Gmsh backend, and joins netgen's route at the MSH 4.1 writer,
so every gate is shared. Gmsh assembles no region of its own. Boundary layers remain FR-11, after
v1.0, and whether the bundle carries Gmsh remains the later decision above.

#### ADR-003 Project licence

Decision: BSD-3-Clause core library with GPL-compatible optional extras. No institutional
constraint applies.

| Alternative | Assessment |
|---|---|
| GPL core, Gmsh in the default path | Deferred, not foreclosed: the package has no other GPL entanglement, so this stays a one-line relicense should GPL become acceptable |
| PyQt for the desktop shell | Rejected: GPL-3 or commercial only. PySide6 (LGPL-3) is used instead (CON-09) |
| Bundle defaulting to scipy SuperLU | Rejected on measurement (§6.6): SuperLU was OOM-killed on the reference-sized factorisation, so a SuperLU-default bundle cannot run the published case. The bundle defaults to UMFPACK and carries the GPL-2+ obligations that follow, stated in its licence notice; the library itself stays BSD-3 and depends on neither (CON-11) |

Consequences: BSD-3 maximises adoption where both academic and industrial reuse matter and matches
the scientific Python stack. Dependencies are compatible: NGSolve and Netgen LGPL-2.1 (dynamic
linking), MDAnalysis LGPLv3, PDB2PQR BSD, APBS BSD-3, scikit-image BSD-3, Shapely BSD-3, meshio
MIT, PySide6 LGPL-3. Gmsh is GPLv2+, hence optional. The repository carries a `CITATION.cff`
pointing at the Nanoscale paper and the software DOI (CON-14).

#### ADR-004 Desktop application

Decision: Python core, PySide6 (LGPL-3) shell, NGSolve webgui in a `QWebEngineView` for field
rendering, and a background solver process communicating over a queue so the interface stays
responsive and can show live convergence. Packaged with PyInstaller, briefcase or
conda-constructor. The graphical surface grows from Phase 1 onward.

| Alternative | Assessment |
|---|---|
| PyQt6 shell | Rejected: GPL-3 only |
| Local web application: FastAPI plus browser frontend wrapped in `pywebview` | **Rejected**, closing the deferral below. The stage interface did stay clean — the walk takes a `Progress` callback and a `CancelToken`, and every stage is introspectable without importing it (FR-27) — so the alternative remained available and was declined on its own merits: it buys a hosted future and an SSH port-forward this project has no requirement for, and pays in a second rendering path for the same webgui scene. Originally recorded as "on the table… the choice may wait until Phase 1", which is where it was made |
| Defer the interface to a terminal phase | Rejected on two failure modes: an interface bolted on at the end exposes the API's accidental structure rather than the user's workflow, and a nine-month gap before any non-programmer touches the tool is a nine-month gap in shaping feedback |

NOTE (packaging). The redistributable bundle SHALL be built one-**dir**
rather than one-file, for two independent reasons. PySide6 and Qt are used under the LGPL option
(CON-09), which requires that a recipient be able to replace the covered libraries; a directory of
shared libraries satisfies that plainly. And Qt WebEngine runs a separate helper executable, which a
one-file extractor must locate at runtime inside a temporary directory. The bundle SHALL carry the
licence notice CON-11 requires, stating that the bundle as a whole is distributed under GPL-2+
because its default linear solver is, while the library itself remains BSD-3. The packaging probe
SHALL carry, and its `--selftest` SHALL exercise once each, failing naming the payload: PySide6's
widgets and Qt WebEngine, NGSolve, Netgen and `ngsolve.webgui` (§8.2.1 A4), and since WP24 the
geometry pipeline's compiled payloads, MDAnalysis and gemmi reading a structure, scikit-image's
contour extraction, Shapely's polygon checks through GEOS, and Gmsh meshing a square (§8.2.2 B8).
An extension that imports and then cannot load its library is RSK-13's failure, which an import
alone does not detect: Gmsh's Python module imports with its library missing and fails on its first
call (`knowledge/07-software-stack/05-gui-and-packaging.md`). Since WP31 the bundle also carries the charge
pipeline's protonation payloads, PDB2PQR and PROPKA, with the data files each reads beside its own
modules. `--selftest` protonates a nine-residue peptide at two pH values and requires the two net
charges measured for it, so that a bundle missing PROPKA's parameter file fails naming PROPKA,
where a single run without titration would pass (WP31 D14). A
pure-Python payload used under the LGPL SHALL be collected as source files on disk, and not into
the bundle's module archive: a module inside the archive cannot be replaced in place, and the
one-dir layout exists so that an LGPL component can be. That applies to PROPKA (LGPL-2.1),
MDAnalysis and GridDataFormats (LGPL-3.0-or-later) (WP31 D15). The background solver
process SHALL be started with the `spawn` start method: it is the only one Windows has, and a forked
child would inherit both the parent's Qt event loop and its already-imported numerical libraries.

Consequences: every pipeline stage must be independently invocable, cancellable, progress-reporting
and introspectable (FR-27), which §5.1 requires on scientific grounds in any case, so the interface
is a thin shell over the stage objects the CLI drives (IF-09). Each release from v0.2 onward ships
a usable graphical surface over the functionality existing at that release (QR-11); the per-phase
increments are in §8.1.

NOTE (the browser shell, 18 October 2026). The author ruled that Phase 5 replaces the PySide6 shell
with a browser shell: a local server in `gui/` over the existing view-models and a browser front end
(§8.2.12 M3). The rejection of a local web application above is withdrawn. The decision and the
packaging NOTE stand for the Qt shell until Phase 5's design document restates the shell's gating
clauses and the browser shell meets them; then PySide6, the Qt widgets and the PyInstaller bundle
leave. The consequences above hold for either shell.

NOTE (the browser shell, v0.6). When the package that removes the Qt shell lands, the packaging
NOTE above reads: "The workbench SHALL be distributed as the package with its `gui` extra, installed
by one documented `uv` command, with no bundle (§8.2.17 S12). Its front end SHALL ship prebuilt inside
the wheel, so no user builds it (CON-07), and the shipped renderer SHALL stay an unmodified, separate
file (CON-09). The server's self-test SHALL exercise once each, failing naming the payload: NGSolve,
Netgen and the renderer reaching its document; MDAnalysis and gemmi reading a structure,
scikit-image's contour extraction and Shapely's polygon checks through GEOS, and Gmsh where its extra
is installed; PDB2PQR and PROPKA protonating a nine-residue peptide at two pH values, whose two net
charges it requires, so that PROPKA's parameter file out of reach fails naming PROPKA. The
background solver process SHALL be started with the `spawn` start method: it is the only one Windows
has, and a forked child would inherit the server's event loop and its already-imported numerical
libraries." Until then the packaging NOTE gates the Qt shell (§8.2.17 S17). The decision above is
restated by WP5.02's spike, which records the front end chosen (§8.2.17 S8).

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
