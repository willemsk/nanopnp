# Today's alternatives

What a start-over could choose today in six areas, for [the ground-up review](../ground-up-review.md). Six
`general-purpose` agents on Sonnet 5.5, at high effort, surveyed one area each on 24 November 2026. Each covered
today's choice, each library a [blind design](design-a.md) names, and its own additions, and returned one table with
its sources. The tables stand as returned, unedited but for a heading set in bold and the escapes the page needs (an
asterisk, an angle bracket, two source numbers side by side). A cell marked "not verified" is the agent's own word.
The facts a proposal rests on were then checked again by the main session, under *Checked at the source* at the end,
and where the two differ the check governs.

## The brief

Each agent read this text, then its area's choice and needs, which each section repeats:

```text

You survey today's alternatives for ONE technology area of a scientific Python program, as of 24 November 2026.

The program, nanopnp (the repository at /home/user/nanopnp; open source), solves the steady, 2D-axisymmetric, extended
Poisson-Nernst-Planck and Navier-Stokes equations in a biological nanopore with finite elements. Its pipeline is
structure -> geometry -> mesh -> solve -> analyse. It supports Python 3.11 to 3.14 on Windows, macOS and Linux, is
installed from wheels with no compiler, no source build and no JIT on the user's machine, takes only permissive or
LGPL/MPL dependencies on its default path (a GPL library may only be an optional backend), and has one maintainer.
A review now asks what a start-over would choose. You supply facts for it, not a design.

Candidates to cover:
1. today's choice (named below);
2. each library or tool that the three blind designs name for your area. Read section 3, "The technologies", and
   where it bears on your area section 4, of docs/project/ground-up-review/design-a.md, design-b.md and design-c.md.
   Stop reading each file at its heading "After the unblinding". Read nothing else in the repository.
3. your own additions: what a careful engineer would also consider today (the area's note below suggests some).

Return, and nothing else:
(a) ONE Markdown table, one row per candidate, with exactly these columns:
    | Candidate | Named by | Licence | Wheels | Meets the needs | Last release | Lacks |
    - Named by: "today", "A", "B", "C" (a blind design, as first choice or runner-up: say which), "survey" (yours).
    - Licence: the SPDX name, from the project's own licence file or PyPI metadata.
    - Wheels: for the latest release, which of Windows (win_amd64), macOS (arm64, x86_64) and Linux (manylinux
      x86_64, aarch64) have binary wheels for CPython 3.11, 3.12, 3.13 and 3.14, or that the package is pure Python
      (py3-none-any), or that there is no wheel and how it installs instead (conda-forge, a source build, npm...).
      For a JavaScript library say how it would reach a pip user (vendored files, a wheel that bundles it).
    - Meets the needs: each need of the area's note below, as yes / partly / no with three to eight words.
    - Last release: version and date.
    - Lacks: what the candidate is missing for this program, in one or two short sentences.
    Each cell that states a fact ends with a source number like [3]. A cell you could not verify says "not verified"
    and why. Do not fill a version, date, wheel tag or licence from memory.
(b) A numbered list of sources: the address and what it showed. Prefer primary sources: the PyPI JSON API
    (https://pypi.org/pypi/<name>/json lists each file of the latest release with its platform and Python tags and
    its upload date), the project's licence file, its documentation, its release page.
(c) At most 150 words: which candidate the table favours from nothing, the runner-up, and the one fact that could
    overturn it.

Rules. Web search and fetch are for libraries and tools only: never search for the model's equations, its correction
functions or its parameters. Write no file in the repository, run no git command, commit nothing, start no agent.
At most 1,300 words in all. A table row is one line.
```

The front end's brief gave NiceGUI 3 and 15,000 lines of the program's own JavaScript and CSS. A message corrected the
second to 1,700 and 1,800 lines beside bundles shipped unmodified, [as measured](evidence.md#size); the agent found
NiceGUI 4.0.0 itself.


## The simulation engine

**Today's choice.** NGSolve 6.2.2606 or later with Netgen, LGPL-2.1.

**The needs**, numbered as the table's *Meets the needs* cells number them:

1. axisymmetric weak forms written by the user, an r-weighted measure on an (r, z) mesh;
2. second-order Lagrange and Taylor–Hood (P2/P1) elements on curved triangles;
3. a symbolic or automatic Jacobian of a nonlinear coupled weak form of five fields;
4. a direct sparse solve at 10⁶ unknowns reachable from the wheel;
5. adjoint or sensitivity support: a transposed Jacobian solve, automatic adjoints;
6. a path to 3D and to a time-dependent solve without changing the library;
7. runs from a pip wheel on all three systems with no compiler and no JIT at run time.

**The report, as returned.**

Two things to know first. I tested NGSolve only on the Linux x86_64 cp313 wheel in a clean venv. I did not run the Windows or macOS wheels. DOLFINx has no release on pypi.org; the only wheels are dev builds on Test PyPI.

**(a) Table**

| Candidate | Named by | Licence | Wheels | Meets the needs | Last release | Lacks |
|---|---|---|---|---|---|---|
| NGSolve + netgen-mesher | today; A first; B first; C first | LGPL-2.1-only [1]\[2] | cp310–cp314: win_amd64, macOS universal2 (arm64+x86_64), manylinux_2_28 x86_64. No aarch64 file in any release [1]\[2] | (1) yes, r-weighted forms ran (r=x+0.1) [3]. (2) yes, `Curve(2)` mesh with P2 and P1 spaces ran [3]. (3) yes, `AssembleLinearization` gave the Jacobian of a coupled nonlinear form [3]. (4) partly: wheel has UMFPACK, SparseCholesky and SuperLU, but no MKL, Pardiso or MUMPS; a 653k-dof P2/P1 stand-in took 50 s to factor [3]. (5) partly: no automatic adjoint; `mat.T.Inverse` failed, so a transposed solve goes through SciPy or reassembly [3]. (6) partly: Netgen 3D is available; time stepping not tested. (7) yes for Windows, macOS and x86 Linux, no compiler needed in my run [3]; run-time C++ compile (`Compile(realcompile=True)`) not verified, docs page returned HTTP 500 | 6.2.2608, 2026-10-01 [1] | No Linux aarch64 wheel. No Pardiso or MUMPS in the Linux wheel (Windows and macOS not tested). The 50 s factor at 653k dofs came from a stand-in form on a shared machine. Whether linking UMFPACK (SuiteSparse) affects the LGPL claim: not verified. |
| FEniCSx / DOLFINx (basix, ffcx) | B runner-up; C runner-up; A runner-up | LGPL-3.0-or-later for DOLFINx and ffcx; MIT for basix [4]\[7] | pypi.org: no dolfinx [4]. Test PyPI dev build only: cp312-abi3, win_amd64, macOS arm64+x86_64, manylinux_2_34 x86_64+aarch64 [4]. Docs say wheels are beta, Python 3.12+ [5]. | (1) not verified (UFL form language, not tested). (2) not verified. (3) not verified; UFL derivative is the known mechanism. (4) partly: wheels have SuperLU_DIST, no PETSc [5]. (5) not verified. (6) not verified. (7) no: forms are JIT-compiled and Windows needs Visual Studio [5]; PETSc not available on Windows [5]. | v0.11.0 on 2026-06-09 and v0.11.0.post0 on 2026-06-10 (year not shown on the page) [6]; basix and ffcx 0.11.0 on 2026-06-09 [7] | Breaks the no-JIT and no-compiler rule on the end-user path. Windows has no PETSc. Pip wheels are beta and off pypi.org. |
| scikit-fem | A third; B third (with JAX linearisation) | BSD (PyPI classifier; no SPDX field) [8] | py3-none-any [8] | (1) not verified. (2) partly: `MeshTri2`, `ElementTriP2`, `ElementVector`, `ElementTriP1` import [8]; curved-element use not tested. (3) no automatic Jacobian in the docs; A and B say hand-written or JAX [8]. (4) partly: SciPy SuperLU only; pypardiso optional [13]. (5) no. (6) partly: 3D tets listed [8]; time-dependent not tested. (7) yes, pure Python, no JIT. | 12.0.2, 2026-06-05 [8] | No automatic linearisation, so every new term needs a hand-derived Jacobian. No parallelism, no adjoint tooling. |
| Firedrake | survey | LGPL-3.0-or-later [9] | None. sdist only; install builds PETSc from source and needs a system C compiler [9] | (1) not verified. (2) not verified. (3) not verified (UFL). (4) not verified. (5) not verified. (6) not verified. (7) no: no native Windows; macOS ARM only; source build [9] | 2026.10.0, 2026-10-02 [9] | Fails the no-compiler wheel rule outright. |
| PyMFEM (`mfem`) | survey | BSD-3-Clause [10] | cp311–cp314: macOS arm64 (macOS 14), manylinux x86_64. No Windows, no macOS x86_64, no aarch64 [10] | (1) not verified. (2) not verified. (3) no automatic Jacobian in the docs I read; MFEM's usual route is hand-coded integrators (not verified). (4) not verified; README does not say which direct solvers the wheel has [10]. (5) not verified. (6) not verified. (7) partly: no Windows wheel | 4.10.0.1, 2026-10-27 [10] | No Windows wheel, no weak-form language. |
| SfePy | survey | BSD (PyPI classifier) [11] | None. sdist only [11] | (1) to (6) not verified. (7) no: source build | 2026.3, 2026-09-29 [11] | No wheels. |
| JAX-FEM | survey | GPL-3.0 per its LICENSE file; the PyPI classifier says BSD, so the two conflict [12] | py3-none-any, but depends on JAX [12] | (3) partly: JAX autodiff, by design (not tested). (1), (2), (4) to (6) not verified. (7) partly: JAX itself ships wheels; not checked | 0.0.12, 2026-06-13 [12] | GPL on the default path (CON-10-style rule). Version 0.0.x. |

Not covered (cap of nine, weakest dropped): deal.II (no PyPI package; Python bindings not verified), FreeFEM (v4.17 per its release page; licence and release year not verified, no wheels) and FEniCS legacy (no PyPI package).

**(b) Sources**

1. https://pypi.org/pypi/ngsolve/json: 6.2.2608 uploaded 2026-10-01; LGPL-2.1-only; wheel tags as listed; requires netgen-mesher, numpy and ngsolve-openblas (not on macOS). Across all releases there is no aarch64 file.
2. https://pypi.org/pypi/netgen-mesher/json: 6.2.2608, same date and tags; depends on netgen-occt.
3. My run, with scratch scripts under `scratchpad/tech/engine_mine/`: `uv pip install ngsolve==6.2.2608` on cp313 Linux. `ngsolve.config` shows USE_UMFPACK True and USE_MKL, USE_MUMPS and USE_PARDISO False. `Inverse()` accepted `sparsecholesky`, `umfpack`, `superlu` and `masterinverse`. It rejected `pardiso` ("MKL Pardiso is not available"), `mumps` and `superlu_dist`. A five-field P2/P1 nonlinear form with an r weight assembled and linearised. `a.mat.T.Inverse(...)` failed with "BaseMatrix::InverseMatrix not available". UMFPACK factored 653,259 dofs in 50 s on a shared machine; the solve time printed 0.0 s and is not usable.
4. https://pypi.org/pypi/fenics-dolfinx/json returned 404. https://test.pypi.org/pypi/fenics-dolfinx/json showed 0.12.0.dev202611190210 (2026-11-19), LGPL-3.0-or-later, with the wheel tags above.
5. https://github.com/FEniCS/dolfinx/blob/main/README.md: beta wheels twice a week on Test PyPI, no PETSc, SuperLU_DIST included; Windows needs Visual Studio because of JIT; PETSc not on Windows.
6. https://github.com/FEniCS/dolfinx/releases: v0.11.0 (9 June) and v0.11.0.post0 (10 June), year not shown.
7. https://pypi.org/pypi/fenics-basix/json and https://pypi.org/pypi/fenics-ffcx/json: 0.11.0, 2026-06-09. basix is MIT with cp311 and cp312 wheels; ffcx is LGPL-3.0-or-later, pure Python.
8. https://pypi.org/pypi/scikit-fem/json: 12.0.2, 2026-06-05, py3-none-any. https://scikit-fem.readthedocs.io/en/latest/ lists tri, quad, tet and hex meshes and does not mention an automatic Jacobian. A local import check found `MeshTri2`, `ElementTriP2`, `ElementVector` and `ElementTriP1`.
9. https://pypi.org/pypi/firedrake/json: 2026.10.0, 2026-10-02, sdist only. https://www.firedrakeproject.org/install.html: no native Windows, Intel Macs unsupported, PETSc built from source.
10. https://pypi.org/pypi/mfem/json: 4.10.0.1, 2026-10-27, BSD-3-Clause, wheel tags as listed. https://github.com/mfem/PyMFEM: README (outdated on Python versions) says BSD-3-Clause and mentions no Windows.
11. https://pypi.org/pypi/sfepy/json: 2026.3, 2026-09-29, sdist only.
12. https://pypi.org/pypi/jax-fem/json: 0.0.12, 2026-06-13. https://github.com/tianjuxue/jax-fem/blob/main/LICENSE is GPLv3.
13. https://pypi.org/pypi/pypardiso/json: 0.4.7, 2025-11-02, BSD-3-Clause, py3-none-any. Its MKL dependency was not verified.

**(c) Verdict**

From nothing, the table favours NGSolve. It is the only candidate here that gives automatic linearisation, curved P2/P1 and 3D on win_amd64, macOS and x86 Linux from wheels, with no compiler (checked on Linux only). The runner-up is scikit-fem, which has the simplest install but needs hand-written Jacobians. DOLFINx would be the runner-up on features, but its JIT and Windows-without-PETSc rule it out.

The fact that could overturn this is direct-solve speed. In my run the Linux wheel had no Pardiso or MUMPS, and UMFPACK took 50 s for 653k dofs. At 10^6 dofs with five fields that may be too slow or too memory-hungry. The missing aarch64 Linux wheel is the other gap.


## Geometry and mesh

**Today's choice.** Netgen with its OpenCascade kernel as the default mesher; Gmsh (GPL-2.0-or-later) as an optional backend; scikit-image for the contour, Shapely for the polylines, meshio for interchange. Triangle, MeshPy and TetGen are excluded for their licences.

**The needs**, numbered as the table's *Meets the needs* cells number them:

1. a 2D domain of several named regions built from spline or polyline contours, with named boundaries;
2. graded and anisotropic refinement toward charged walls, size fields set from Python;
3. curved second-order elements that follow the geometry;
4. mesh adaptation driven by an error estimate, with the geometry kept;
5. a path to 3D: tetrahedra from a surface or a CAD solid;
6. a quality report (minimum angle, aspect ratio) readable from Python;
7. runs from a pip wheel on all three systems with no compiler.

**The report, as returned.**

**(a) Table**

| Candidate | Named by | Licence | Wheels | Meets the needs | Last release | Lacks |
|---|---|---|---|---|---|---|
| Netgen + OpenCascade (`netgen-mesher`, with `ngsolve`) | today; A, B, C first choice | LGPL-2.1-only [1] | cp310-cp314: win_amd64, macOS universal2, manylinux x86_64; no Linux aarch64 [1]\[2] | 1 yes: named OCC faces, spline edge meshed [3]; 2 partly: per-face/edge maxh, grading; boundary-layer API exists, 2D anisotropy not verified [3]; 3 yes: `Curve(2)` ran [3]; 4 yes: `Refine()` on curved mesh ran; error-driven flags not run [3]; 5 yes: OCC solids, tets (docs, not run); 6 partly: `CalcMinMaxAngle`, `GetQualityHistogram` exist, bare call gave 0,0 [3]; 7 partly: no Linux aarch64 [1] | 6.2.2608, 2026-10-01 [1] | No Linux aarch64 wheel. Quality report unproven. Size fields are weaker than Gmsh's (B, C). |
| Gmsh (`gmsh`) | today (optional backend); A, B, C runner-up | GPL-2.0-or-later plus an exception for combining with Netgen, OpenCASCADE, METIS, ParaView only [4]\[5] | py2.py3-none: win_amd64, macOS x86_64 and arm64, manylinux x86_64; no Linux aarch64 [4] | 1 yes: physical groups (not run); 2 yes: distance/threshold fields from Python (docs, not run); 3 yes: order-2 on CAD; 4 partly: remesh from a background field, no bisection with geometry kept (C); 5 yes; 6 yes: element quality API, not verified; 7 partly: no Linux aarch64 [4] | 4.15.2, 2026-03-24 [4] | GPL: the exception names no permissive Python caller, so it stays an optional plug-in. Meshes must be imported into the engine. |
| scikit-image + Shapely + meshio | today; A (skimage), C (skimage+Shapely) | BSD-3-Clause (skimage: classifier only) [6]; BSD-3-Clause [7]; MIT classifier [8] | skimage and Shapely: cp311-cp314, all five platforms [6]\[7]; meshio py3-none-any [8] | Support only, no meshing: yes for contour extraction, polyline conditioning (simplify, offset, close) and interchange | skimage 0.26.0, 2025-12-20 [6]; Shapely 2.2.0, 2026-10-07 [7]; meshio 5.3.5, 2024-01-31 [8] | Does no meshing. meshio has had no release for 22 months. |
| pytetwild (fTetWild) | A (3D) | MPL-2.0 (classifier) [9] | cp311 and cp312-abi3 (covers 3.12+): win_amd64, macOS arm64, manylinux x86_64 and aarch64; no macOS x86_64 [9] | 1 no: surface to tets; 2 no: global edge-length control only (not verified); 3 no: linear tets; 4 no; 5 yes: robust tets from a surface; 6 not verified; 7 partly: no macOS x86_64 [9] | 0.4.2, 2026-08-17 [9] | 3D only. No named boundaries or curving. Alpha status (classifier). |
| ngsxfem (PyPI `xfem`) | A runner-up (3D) | LGPL-3.0 (LICENSE file) [10] | cp310-cp314: win_amd64, macOS universal2, manylinux x86_64; pins `ngsolve==6.2.2608` [10] | 1 partly: level-set regions; 2 partly: on a background mesh; 3 yes: isoparametric level-set map; 4 yes: NGSolve refinement; 5 yes: 2D and 3D cut-FEM; 6 no (not verified); 7 partly: no Linux aarch64 [10] | 2.1.2608, 2026-10-26 [10] | Walls are not body-fitted, so exact no-slip walls and a 0.05 nm wall layer are hard. Locked to one NGSolve build. |
| cadquery-ocp + build123d | survey | cadquery-ocp Apache-2.0; build123d Apache-2.0 (PyPI) [11]\[12] | cadquery-ocp cp311-cp314: win_amd64, macOS arm64 and x86_64, manylinux x86_64 and aarch64 [11]; build123d py3-none-any [12] | CAD kernel only: yes for 1 and 5 (revolved spline solids, named faces); no mesher: 2, 3, 4, 6 no | OCP 8.0.1.1.0, 2026-10-05 [11]; build123d 0.13.0, 2026-09-21 [12] | No mesher. Duplicates the OCC that `netgen-mesher` already ships. OCCT licence not verified. |
| mmgpy (MMG) | survey | wrapper MIT [13]; MMG LGPL-3.0-or-later [14] | cp311-cp314: win_amd64, macOS arm64 only, manylinux x86_64 and aarch64 [13] | 1 no; 2 yes: metric-driven, 2D (MmgMesh2D) [13]; 3 no: no curved elements (not verified); 4 yes: remesh by size field; 5 yes: 3D and surface; 6 not verified; 7 partly: no macOS x86_64 [13] | 0.18.0, 2026-11-02 [13] | Remeshes an existing mesh and keeps no CAD geometry. Young wrapper. Needs a mesh in, and a way to move fields. |
| CGAL Python bindings (`cgal`) | survey | GPL-3.0-or-later (classifier) [15] | cp38-cp312 only: win_amd64, macOS x86_64 and arm64, manylinux x86_64; none for 3.13, 3.14 [15] | Not verified beyond wheels; fails 7 for 3.13/3.14 | 6.0.1.post202410241521, 2024-10-25 [15] | GPL. Wheels stop at 3.12. Last release 13 months ago. |
| dmsh | survey | LicenseRef-Proprietary; needs `stonefish-license-manager` [16] | py3-none-any style (cp310-cp315-none-any) [16] | 1 partly: 2D shapes; 2 partly: size function; 3 no; 4 no; 5 no; 6 not verified; 7 yes | 0.3.9, 2026-11-09 [16] | Proprietary licence with a licence manager at install time. 2D only, no curving. |
| pygmsh | survey | GPL-3.0-or-later (classifier) [17] | py3-none-any; requires `gmsh` [17] | Needs of Gmsh through a wrapper | 7.1.17, 2022-01-28 [17] | GPL. Unmaintained for four years. |

**(b) Sources**
1. https://pypi.org/pypi/netgen-mesher/json: 6.2.2608, LGPL-2.1-only, 15 wheels, depends on `netgen-occt==7.8.1`.
2. https://pypi.org/pypi/ngsolve/json: 6.2.2608, LGPL-2.1-only, same platform set.
3. My run of the cp313 manylinux wheel of 1 in a scratch venv: OCC faces glued, spline edge, named material, `Curve(2)`, `Refine()` (212 to 848 triangles). `CalcMinMaxAngle` returned (0,0).
4. https://pypi.org/pypi/gmsh/json: 4.15.2, GPLv2+, four wheels.
5. https://gitlab.onelab.info/gmsh/gmsh/-/raw/master/LICENSE.txt: the exception text.
6. https://pypi.org/pypi/scikit-image/json.
7. https://pypi.org/pypi/shapely/json.
8. https://pypi.org/pypi/meshio/json.
9. https://pypi.org/pypi/pytetwild/json.
10. https://pypi.org/pypi/xfem/json, plus the LICENSE and README at github.com/ngsxfem/ngsxfem.
11. https://pypi.org/pypi/cadquery-ocp/json.
12. https://pypi.org/pypi/build123d/json.
13. https://pypi.org/pypi/mmgpy/json, plus the README at github.com/kmarchais/mmgpy.
14. https://raw.githubusercontent.com/MmgTools/mmg/master/LICENSE.
15. https://pypi.org/pypi/cgal/json.
16. https://pypi.org/pypi/dmsh/json.
17. https://pypi.org/pypi/pygmsh/json.
18. docs/project/ground-up-review/design-a.md, design-b.md and design-c.md, up to "After the unblinding", for the "Named by" column.

**(c) Verdict**

Netgen with OpenCascade is favoured: it ships in the engine wheel, is LGPL, and my run showed curved, named, refinable 2D meshes. scikit-image, Shapely and meshio support it.

Gmsh is the runner-up and stays optional, because its exception covers only Netgen, OpenCASCADE, METIS and ParaView.

The fact that could overturn this is the wall layer. Netgen's 2D anisotropic or boundary-layer meshing at a 1 nm Debye length (0.05 nm at the wall) is not verified. If it fails, Gmsh's boundary-layer fields would be needed. Netgen also has no Linux aarch64 wheel.


## Linear and nonlinear solvers

**Today's choice.** A fully coupled, damped Newton iteration written in the program, with a continuation ladder; SuiteSparse UMFPACK (GPL-2.0-or-later) as built into the NGSolve wheel, the default, and scipy's SuperLU (BSD) as the fallback.

**The needs**, numbered as the table's *Meets the needs* cells number them:

1. a direct factorisation of an unsymmetric indefinite sparse matrix at 10⁶ unknowns in 2D within a laptop's memory;
2. threads, and re-use of the symbolic factorisation across Newton steps;
3. a transposed solve with the same factors, for adjoints;
4. reachable from Python by a pip wheel on Windows, macOS and Linux with no compiler;
5. a licence that fits a permissive or LGPL default path;
6. a path to 3D, where a direct solve stops being enough;
7. for the nonlinear layer: line search or trust region, continuation with step control, pseudo-arclength.

**The report, as returned.**

**Area: linear and nonlinear solvers.** Needs 1-7 are those of the brief. Y = yes, P = partly, N = no.

(a)

| Candidate | Named by | Licence | Wheels | Meets the needs | Last release | Lacks |
|---|---|---|---|---|---|---|
| UMFPACK inside the `ngsolve` wheel (`inverse="umfpack"`; default when `mkl` is absent) | today; A (engine-bundled), C (engine-built-in) | UMFPACK GPL-2.0-or-later (own file, "alternate licences on request") [4]; NGSolve LGPL-2.1-only [1] | ngsolve 6.2.2608: cp311-314 on win_amd64, macOS universal2, manylinux x86_64. **No Linux aarch64** [1] | 1 Y: 1.16M-dof Stokes-type saddle+convection, 21 s, 6.2 GB peak, 4 cores [3]; 2 P: threads only via BLAS (CPU 2.8x wall) [3], `Update()` refactors [3], symbolic reuse in the C API [5]; 3 Y: `inv.T` right to 1e-14 [3]; 4 Y; 5 P: GPL (see note); 6 N: direct only, `ngs2petsc.py` ships [2]; 7 N | NGSolve 6.2.2608, 2026-10-01 [1]. UMFPACK version in the wheel: not verified | GPL code is linked into the LGPL libngla (strings in the wheel [2]). No GPU or MPI path. Whether `Update()` reuses the symbolic step: not verified. |
| SuperLU via scipy `splu` (the fallback) | today; B (open floor); C (fallback) | BSD-3-Clause (scipy); SuperLU file is the LBNL-modified BSD [7]\[8] | scipy 1.18.1: win_amd64, win_arm64, macOS x86_64 and arm64, manylinux x86_64 and aarch64, cp312-314. **Requires-Python >=3.12, so no 3.11** [7] | 1 P: 5277 dof in 0.55 s vs UMFPACK 0.15 s [3]; 1M-dof figure none found; 2 N: serial, no reuse API [3]\[7]; 3 Y: `solve(trans="T")` [2]\[3]; 4 Y; 5 Y; 6 N; 7 N | scipy 1.18.1, 2026-08-21 [7] | Slower than UMFPACK in my runs; for 3D it needs an iterative layer on top. The solver in NGSolve's own "superlu" type is this same scipy call [2]. |
| Intel MKL PARDISO (`mkl` wheel; `ngsolve` loads it at run time; `pypardiso`) | A (when present); B (where found); C (via pypardiso) | MKL: Intel Simplified Software License (proprietary); pypardiso BSD-3-Clause [9] | mkl 2026.2.1: win_amd64 and manylinux x86_64 only, **no macOS, no aarch64**. pypardiso 0.4.7: py3-none-any [9] | 1 Y: 1.16M dofs, 9.4 s, 3.3 GB (scalar) [3]; 2 Y: the `pardiso` call has separate phases (ngsolve `Update` 0.21 s vs 0.37 s first) [3]; 3 Y: `iparm[11]=2` [10] and `inv.T` right to 1e-14 [3]; 4 P: not on macOS; 5 N for bundling, fine as optional; 6 N; 7 N | mkl 2026.2.1, 2026-11-12; pypardiso 0.4.7, 2025-11-02 [9] | The `ngsolve` wheel does **not** link PARDISO: `mkl_pardiso.py` finds `mkl_rt` through the pip `mkl` package and makes it the default if found [2]\[3]. Without `mkl` the default is UMFPACK [3]. Vendor says MKL's PARDISO is based on 2006 code [14]. |
| Panua-Pardiso 8.x | survey | Proprietary, per-machine key by e-mail [14] | No PyPI package `panua-pardiso` (404) [14]; Python interface page exists, not verified; the wheel route was not found | 1-3 not verified; 4 N: no pip wheel found; 5 N; 6 not verified; 7 N | 8.2, February 2024 [14] | Licence key bound to the machine breaks "pip install and go"; cannot be a default. |
| MUMPS | B (runner-up as default); A (when present); C (3D, via PETSc) | CeCILL-C [13] | PyPI: `python-mumps` 0.0.6 and `pymumps` 0.4.0 are **sdist only** [11]. conda-forge: `mumps-seq` 5.8.2 on win-64, macOS, Linux; `mumps-mpi` has **no win-64** [12] | 1 Y by design, figure none found; 2 Y: OpenMP, MPI, `JOB=1/2/3` separate [13]; 3 Y: `ICNTL(9)` [13]; 4 N: no wheel; 5 P: CeCILL-C is weak-copyleft (library-level), not read against LGPL; 6 Y: MPI, BLR, out-of-core [13]; 7 N | MUMPS 5.9.2, November 2026 [13]; PyPI 0.0.6, 2026-01-11 [11] | No wheel on any system: a pip user needs a compiler or conda. |
| PETSc KSP and SNES through `petsc4py` | A (cluster container); C (3D, runner-up everywhere) | BSD-2-Clause [11] | PyPI `petsc` and `petsc4py` 3.26.1: **sdist only** (pip builds from source) [11]\[15]. conda-forge: linux-64, linux-aarch64, osx-64, osx-arm64, **no win-64** [12] | 1 P: delegates to MUMPS, SuperLU_DIST, UMFPACK; 2 Y: via the factor package; 3 Y: `KSPSolveTranspose` [15]; 4 N; 5 Y: BSD; 6 Y: `PCFIELDSPLIT`, AMG [15]; 7 Y: `newtonls` (bt line search), `newtontr`, `newtonal` arc-length [15] | 3.26.1, 2026-10-31 [11] | No wheel: contradicts the compiler-free, Windows-included install. Its continuation is arc-length, not a bias ladder with corrections. |
| SuperLU_DIST | survey (reached through PETSc) | BSD-3-Clause per conda-forge; file is the LBNL variant [12]\[16] | No PyPI package (404); conda-forge 9.2.1 on osx and linux, no win-64 [12] | 1 P: MPI, aimed at clusters; 2 P: not verified; 3 not verified; 4 N; 5 Y; 6 P: a direct solver; 7 N | 9.2.1, conda upload 2026-06-09 [12] | A distributed solver for a one-machine 2D case; no wheel. |
| STRUMPACK | survey | LBNL BSD variant (file text; SPDX id inferred) [16] | No PyPI package, not on conda-forge under `strumpack` or `strumpack-mpi` [16] | 1 P: multifrontal with low-rank compression, figures none found; 2 P: MPI and OpenMP, not verified; 3 not verified; 4 N; 5 Y; 6 P: used as a preconditioner; 7 N | 8.1.0, October 2026 [16] | Source build only, so no. |
| KLU (SuiteSparse) through `klujax` | survey | KLU LGPL-2.1+ [17]; klujax declares LGPL-2.0-only on PyPI [17] | klujax 0.5.3, cp311-314: win_amd64, win_arm64, macOS **arm64 only**, manylinux x86_64 and aarch64 [17] | 1 P: designed for circuit matrices, fill on 2D meshes unmeasured; 2 P: `klu_refactor` reuses ordering, serial [17]; 3 Y: `klu_tsolve` [17]; 4 P: needs jax, no macOS x86_64; 5 Y: LGPL; 6 N; 7 N | 0.5.3, 2026-11-06 [17] | KLU's own guide targets SPICE-like circuits [17]; dependency on JAX for a solver call. |
| `scipy.optimize.newton_krylov` | survey | BSD-3-Clause [7] | Same scipy wheels (3.11 not covered by 1.18.1) [7] | 1 N; 2 N; 3 N; 4 Y; 5 Y; 6 P: default lgmres, `inner_M` preconditioner given by the user; 7 P: `line_search='armijo'`, no continuation [18] | scipy 1.18.1, 2026-08-21 [7] | Jacobian-free (finite-difference Jacobian action); the exact Jacobian from the weak forms is not used; no preconditioner for the saddle block. |
| Hand-written damped Newton plus continuation | today; B, C (own Newton) | the project's own | pure Python, no dependency | 1-3 given by the chosen solver; 7 Y: whatever is written (line search, step control, arc-length are the author's work); 6 Y by choice of solver | none | Maintenance by one person; pseudo-arclength has no package here (PETSc's `newtonal` is the only maintained one found [15]). |

Note on licence (need 5), from the licences' own texts: the GPL FAQ [6] says linking a GPL work "statically or dynamically" makes a combined work covered by the GPL as a whole, and that whether two pieces are one program depends on the mechanism and semantics of communication. nanopnp does not link UMFPACK itself: it calls NGSolve. But NGSolve's libngla holds UMFPACK inside one shared object [2], so a nanopnp shipping with `ngsolve` as a dependency is a downstream user of a binary that contains GPL-2.0-or-later code. Whether that binds nanopnp is a legal question; I found no statement from either project. Davis offers alternative licences [4].

(b) Sources
1. https://pypi.org/pypi/ngsolve/json : 6.2.2608, 2026-10-01, LGPL-2.1-only, file list, requires_dist.
2. The three cp314 ngsolve wheels, downloaded from files.pythonhosted.org and inspected (strings, readelf, `ngsolve/la.pyi`, `solvers/mkl_pardiso.py`, `directsolvers.py`): solver list sparsecholesky/umfpack/pardiso; PARDISO not linked; UMFPACK built in; SuperLU through scipy with `SolveTrans`.
3. My own runs, ngsolve 6.2.2608 + scipy 1.18.1 + mkl, Python 3.13, Linux x86_64, 4 cores, 15 GB shared VM (timings varied up to 10x between identical runs): scalar P2 convection-diffusion 1.16M dofs (UMFPACK 10 s, 3.2 GB; PARDISO 9.4 s, 3.3 GB); Taylor-Hood Stokes plus convection 1.16M dofs (UMFPACK 21 s, 6.2 GB); transposed solves agree to 1e-14. Not a coupled PNP-NS matrix.
4. https://raw.githubusercontent.com/DrTimothyAldenDavis/SuiteSparse/dev/UMFPACK/Doc/License.txt : GPL-2.0+; KLU file: LGPL-2.1+.
5. SuiteSparse `UMFPACK/Doc/UMFPACK_UserGuide.tex` (same repository): `UMFPACK_At` solve; symbolic reuse for the same pattern.
6. https://www.gnu.org/licenses/gpl-faq.html : GPLStaticVsDynamic, MereAggregation, LinkingWithGPL.
7. https://pypi.org/pypi/scipy/json : 1.18.1, 2026-08-21, wheels, Requires-Python >=3.12; `splu` and `use_solver` docstrings (own run).
8. https://raw.githubusercontent.com/xiaoyeli/superlu/master/License.txt : LBNL-modified BSD.
9. https://pypi.org/pypi/mkl/json and /pypi/pypardiso/json.
10. https://www.intel.com/content/www/us/en/docs/onemkl/developer-reference-c/2025-0/pardiso-iparm-parameter.html : `iparm[11]` transposed solve.
11. PyPI JSON for python-mumps, pymumps, petsc, petsc4py, scikit-umfpack, scikit-sparse (all sdist only; scikit-sparse 0.5.1 2026-11-11, scikit-umfpack 0.4.2 2025-07-08).
12. https://api.anaconda.org/package/conda-forge/{petsc,petsc4py,mumps-seq,mumps-mpi,python-mumps,superlu_dist} : platforms and dates.
13. https://mumps-solver.org/index.php?page=dwnld (CeCILL-C; 5.9.2 Nov 2026) and https://mumps-solver.org/doc/userguide_5.9.2.pdf (ICNTL(9), JOB phases, OpenMP, out-of-core).
14. https://panua.ch/pardiso/ : 8.2 of Feb 2024, key-file licence, MKL's PARDISO is the 2006 code; https://pypi.org/pypi/panua-pardiso/json is 404.
15. https://petsc.org/release/ pages SNESType, SNESNEWTONAL, SNESLineSearchType, PCFIELDSPLIT, KSPSolveTranspose, install.
16. https://raw.githubusercontent.com/pghysels/STRUMPACK/master/{LICENSE,CHANGELOG}; https://raw.githubusercontent.com/xiaoyeli/superlu_dist/master/License.txt.
17. https://pypi.org/pypi/klujax/json; SuiteSparse `KLU/Include/klu.h`, `KLU/Doc/KLU_UserGuide.tex`.
18. `scipy.optimize.newton_krylov` signature (own run).
19. docs/project/ground-up-review/design-{a,b,c}.md, section 3, for who names what.

(c) Favoured from nothing: the current layering, NGSolve's bundled UMFPACK as default with scipy SuperLU as the floor and MKL PARDISO optional where the pip `mkl` exists (Windows and Linux x86_64 only). Runner-up: MUMPS with PETSc for 3D, from conda-forge. The fact that could overturn it: the default solver binary has GPL code inside an LGPL-labelled library. If that is not acceptable, the default falls to SuperLU, which is slower and serial, or to MKL on two systems. Also, scipy 1.18.1 does not install on Python 3.11.


## The front end and visualisation

**Today's choice.** A browser workbench served locally by the package: NiceGUI over FastAPI and uvicorn, with Plotly for charts and (r, z) maps, Mol\* for the structure, Matplotlib for the library's figures, and Playwright for its tests. PyQt is excluded for its licence.

**The needs**, numbered as the table's *Meets the needs* cells number them:

1. reaches the user by `pip install` alone: no Node.js, no build step and no compiler on the user's machine;
2. a permissive licence for everything shipped;
3. an application of several screens over a project folder: forms from a schema, a run queue with live progress, cancel;
4. a map of a scalar field on an unstructured mesh of about 10⁵ cells that pans and zooms smoothly, with cuts and probes, and a path to a 3D field view;
5. a 3D view of a protein structure;
6. accessibility to WCAG 2.2 AA with the stock components, and end-to-end tests in a headless browser;
7. the burden on one maintainer, a physicist with no front-end experience who directs coding agents.

**The report, as returned.**

Note on the brief: PyPI shows NiceGUI at 4.0.0 (4 Nov 2026), not 3 [1]\[2]. I used your correction: about 1,700 lines of JS and 1,800 of CSS, with Mol\*, KaTeX, uPlot and NGSolve webgui vendored. I could not read the GitHub API (blocked), so contributor counts are not verified. "Releases/12 mo" is counted from PyPI release history [1].

(a)

| Candidate | Named by | Licence | Wheels | Meets the needs | Last release | Lacks |
|---|---|---|---|---|---|---|
| NiceGUI (Quasar, FastAPI) | today | MIT [1] | py3-none-any, 8.2 MB; classifiers 3.11-3.15 [1] | 1 yes (wheel bundles JS); 2 yes; 3 yes (run.cpu_bound, schema forms not built in); 4 partly (ui.plotly, ui.scene three.js, no mesh-map element) [4]; 5 partly (vendored Mol\*); 6 partly (Quasar ARIA layer, no WCAG claim) [5]; 7 partly: 16.4k stars [3], 23 releases/12 mo, majors 2.0 Aug 2024, 3.0 Oct 2025, 4.0 Nov 2026 | 4.0.0, 2026-11-04 [1] | Majors yearly; 4.0 silently changed prop names, DOM IDs, spawn default, empty-input values [2]. No field-map or WCAG evidence. |
| TypeScript/React + Vite + FastAPI, bundle in wheel (Vega-Lite, Observable Plot) | A first; B first | MIT (FastAPI 0.165.0), BSD-3 (uvicorn 0.54.0), BSD-3 (vega-lite 6.5.0), ISC (Plot 0.6.19) [21]\[9] | Server py3-none-any [21]. Bundle: CI runs `npm ci` and `vite build`, a build hook copies `dist/` into the wheel; jupyterlab does this (py3-none-any, 17.3 MB) [18] | 1 yes, user needs no Node; 2 yes; 3 yes, all hand-built; 4 yes, via vtk.js or WebGL; 5 yes (Mol\*); 6 partly, own effort; 7 no: second language | FastAPI 0.165.0, 2026-11-18 [21] | Maintainer needs Node, a lockfile, a CI build, npm updates and TS skill; agents write all UI code. |
| trame + vtk.js or PyVista | C first; A, B runner-up | Apache-2.0 (trame), BSD-3 (trame-vtk, vtk), MIT (PyVista) [6]\[7] | trame, trame-vtk, trame-vuetify, trame-vtklocal, pyvista py3-none-any [6]. vtk: cp311-cp314 on win_amd64, macOS x86_64+arm64, manylinux x86_64+aarch64, 80-140 MB each [7] | 1 yes (large vtk); 2 yes; 3 partly, Vuetify forms, long jobs not verified; 4 yes, server or client rendering, 3D native; 5 no, Mol\* embed needed; 6 not verified; 7 partly: 712 stars [8], 4 releases/12 mo, 4.0.0 Sep 2026 after 3.0.0 Jul 2023 | trame 4.0.0, 2026-09-09 [6] | Small community; vtk wheel 80-140 MB; local rendering depends on trame-vtklocal; no run-queue pattern shown. |
| Panel (HoloViz) | survey | BSD [12] | py3-none-any, 20.6 MB; classifiers 3.12-3.15 [12] | 1 yes; 2 yes; 3 partly, widgets and async, no schema forms verified; 4 not verified (Bokeh, VTK, Plotly panes); 5 not verified; 6 not verified; 7 yes: 47 releases/12 mo, 1.0 May 2023 | 1.10.1, 2026-11-23 [12] | Requires Python 3.12 or later: fails the 3.11 floor. |
| Dash | survey | MIT [13] | py3-none-any, 9.3 MB; 3.10-3.14 [13] | 1 yes; 2 yes; 3 partly, callbacks, background jobs not verified; 4 partly, Plotly figures; 5 not verified; 6 not verified; 7 partly: 3.0 Mar 2025, 4.0 Feb 2026 | 4.5.1, 2026-11-19 [13] | Two majors in 12 months; callback model fits forms, not a run queue. |
| Streamlit | survey | Apache-2.0 [14] | py3-none-any, 11.2 MB; 3.11-3.15 [14] | 1 yes; 2 yes; 3 no: script-rerun model, not verified here; 4 partly, Plotly or custom component; 5 not verified; 6 not verified; 7 yes: 23 releases/12 mo | 1.67.0, 2026-11-05 [14] | Rerun-on-interaction model is a poor fit for multi-screen state, queue and cancel. |
| Solara | survey | MIT [15] | py3-none-any, 1.5 MB [15] | 1 yes; 2 yes; 3 partly, React-style, long jobs not verified; 4 not verified; 5 not verified; 6 not verified; 7 partly: 32 releases/12 mo, one main author | solara-ui 1.66.3, 2026-11-10 [15] | Small community; pre-built-view ecosystem is thin. |
| Reflex | survey | Apache-2.0 [16] | py3-none-any, 0.3 MB [16]; compiles to a React app and uses bun [16] | 1 partly, bun is a non-Python runtime tool, setup timing not verified; 2 yes; 3 yes, generic; 4 not verified; 5 not verified; 6 not verified; 7 no: pre-1.0, 83 releases/12 mo | 0.11.0, 2026-11-12 [16] | Node-family toolchain on the user's machine; fast-moving pre-1.0 API. |
| marimo; anywidget; JupyterLab extension | survey; A (anywidget) | Apache-2.0 (marimo); MIT (anywidget); BSD (JupyterLab) [17]\[18] | All py3-none-any; marimo 39.5 MB, JupyterLab 17.3 MB [17]\[18] | 1 yes; 2 yes; 3 no: notebook model, not a project-folder app; 4 yes via widgets; 5 yes via widgets; 6 not verified; 7 partly: marimo pre-1.0, JupyterLab 4.0 May 2023 | marimo 0.25.2, 2026-10-19; anywidget 0.11.0, 2026-04-27; JupyterLab 4.6.6, 2026-11-06 [17]\[18] | A notebook, not a multi-screen application; useful as a secondary delivery of views. |
| Desktop shell: PySide6; pywebview; Tauri | survey | PySide6 LGPL-3.0-only OR GPL [19]; pywebview BSD [20]; Tauri not verified | PySide6 6.12.0: abi3 for win_amd64, macOS universal2, manylinux_2_34 x86_64, manylinux_2_39 aarch64, 82-116 MB [19]. pywebview py3-none-any [20]. Tauri: not fetched | PySide6: 1 yes; 2 yes (LGPL); 3-5 yes, all hand-built; 6 not verified; 7 no (C++-style API). pywebview: wraps a web app, needs WebView2/.NET on Windows and GTK/WebKit system packages on Linux [20] | PySide6 6.12.0, 2026-10-08 [19]; pywebview 6.2.1, 2026-04-15 [20] | PySide6 doubles the UI work; pywebview has Linux system dependencies; Tauri needs a Rust build and signed installers (B rejects on cost) [23]. |
| Field-map libs: plotly.js, vtk.js, deck.gl, regl | A (vtk.js); B (own WebGL2); C (trame) | MIT, BSD-3, MIT, MIT [9] | Vendored JS: plotly.js-dist-min 4.3.0; vtk.js via trame-vtk; pydeck 0.9.3 py3-none-any, 11.4 MB, bundles deck.gl, version not verified [21] | plotly.js: 4 partly: mesh3d takes i/j/k triangles with per-vertex intensity [10]; speed at 1e5 cells and top-down 2D not verified; no cuts or probes. vtk.js: 4 yes, 3D path. deck.gl: not verified. regl: low-level | plotly.js 4.3.0, 2026-11-10; vtk.js 38.1.0, 2026-11-18; deck.gl 9.4.2, 2026-11-24; regl 2.1.1, 2024-11-12 [9] | regl has had no release since Nov 2024. None verified at 1e5 cells; a 1e5-cell benchmark is the open test. |
| Molecular viewers: Mol\*, NGL, 3Dmol.js | today (Mol\*); A, B (Mol\*) | MIT, MIT, BSD-3 [9] | Vendored JS, as today; no pip wheel found | Mol\*: 5 yes, used by EMBL-EBI via pdbe-molstar [11]; 1k stars; README calls v6 a "prototype" [11]. NGL, 3Dmol.js: 5 not verified | molstar 5.13.1, 2026-10-08; ngl 2.5.0, 2026-09-03; 3dmol 3.0.0, 2026-11-22 [9] | Mol\* bundle is large, build details not verified. |

(b) Sources
1. https://pypi.org/pypi/nicegui/json, and the same pattern for dash, streamlit, panel, solara-ui, reflex, marimo, anywidget, jupyterlab, pyside6, pywebview, pyvista, pydeck, fastapi, uvicorn, plotly: version, licence, files, release history
2. https://github.com/zauberzeug/nicegui/releases: 4.0 and 3.x breaking changes
3. https://github.com/zauberzeug/nicegui: 16.4k stars
4. https://nicegui.io/documentation/section_data_elements: ui.plotly, ui.uplot, ui.scene, ui.anywidget; no WCAG claim
5. https://quasar.dev/options/accessibility: ARIA layer, no blanket WCAG conformance
6. PyPI JSON for trame, trame-vtk, trame-vuetify, trame-vtklocal, pyvista
7. https://pypi.org/pypi/vtk/json: wheels and sizes
8. https://github.com/Kitware/trame: 712 stars, Apache-2.0
9. https://registry.npmjs.org/&lt;pkg&gt;: molstar, ngl, 3dmol, plotly.js-dist-min, @kitware/vtk.js, deck.gl, regl, vega-lite, @observablehq/plot
10. https://plotly.com/javascript/3d-mesh/: mesh3d with i/j/k and intensity
11. https://github.com/molstar/molstar: MIT, 1.0k stars, "v6 prototype"
12-21. The PyPI JSON of source 1, by package: 12 panel; 13 dash; 14 streamlit; 15 solara-ui; 16 reflex (plus https://reflex.dev/docs/getting-started/installation/: bun, React); 17 marimo and anywidget; 18 jupyterlab; 19 pyside6 and pyside6-essentials; 20 pywebview (plus https://pywebview.flowrl.com/guide/installation.html: WebView2, GTK/WebKit); 21 fastapi, uvicorn, pydeck
22. https://pypi.org/pypi/plotly/json: plotly 7.1.0, 2026-09-15, MIT
23. /home/user/nanopnp/docs/project/ground-up-review/design-a.md, design-b.md, design-c.md, section 3

(c) From nothing, the table favours NiceGUI 4: it installs as one pure wheel, ships Quasar and Plotly/uPlot/three.js, and has the smallest Python-only maintenance load. Runner-up: React + FastAPI with the bundle in the wheel, which gives the most design freedom for the field map but adds a Node build. The fact that could overturn this: whether plotly.js (mesh3d) or the vendored NGSolve webgui pans and zooms a 1e5-triangle scalar map smoothly with cuts and probes. If neither does, a vtk.js or own-WebGL view is needed inside any shell. A second fact: a WCAG 2.2 AA audit of Quasar was not found.


## Storage, formats and many-run dispatch

**Today's choice.** A YAML case file validated by pydantic 2 models, with a generated JSON schema; a content-addressed result store on the local disk, arrays in HDF5 through h5py, a JSON provenance manifest beside each result; meshio for interchange and VTK export; pint for units; the program's own sweep runner, with no workflow engine.

**The needs**, numbered as the table's *Meets the needs* cells number them:

1. fields on an unstructured mesh, with the mesh, stored once and read back partially and fast;
2. a format that ParaView and other tools open without the program;
3. a record of a run that can reconstruct it, and whether a standard is worth adopting;
4. safe concurrent writes from many processes on a shared cluster file system;
5. many runs at once, where a run may warm-start from a neighbour's solution, on a laptop and on a SLURM cluster, with resume;
6. reaches the user by a pip wheel on all three systems with no compiler and no service to run;
7. long-term readability of results.

**The report, as returned.**

(a)

| Candidate | Named by | Licence | Wheels | Meets the needs | Last release | Lacks |
|---|---|---|---|---|---|---|
| h5py (HDF5) | today; A (VTKHDF layout); B (+XDMF sidecar); C runner-up | BSD-3-Clause [1] | win_amd64, macOS arm64+x86_64, manylinux x86_64+aarch64 for cp311-cp314 [1] | 1 yes (chunked slicing; not verified here); 2 partly (needs VTKHDF layout or XDMF sidecar); 3 no; 4 partly (one writer; locking trouble on NFS/Lustre) [27]\[28]; 5 n/a; 6 yes; 7 yes (HDF5 format; not verified) | 3.16.0, 2026-03-06 [1] | No multi-writer; HDF5 file locks fail or hang on some network file systems unless disabled [28]. |
| Zarr 3 | C; A and B runner-up | MIT [2] | pure py3-none-any; 3.2 and later need Python >=3.12, so 3.11 resolves an older 3.1 line [2] | 1 partly (chunk reads yes; no mesh convention); 2 no (no ParaView reader found; not verified); 3 no; 4 yes (distinct chunks, atomic-write store) [24]; 5 n/a; 6 yes; 7 partly (v3 is new; v2 to v3 broke) | 3.4.2, 2026-10-27 [2] | Same-chunk writes need outside coordination [24]; Python 3.11 gets stale releases; not viewable in ParaView. |
| xarray + netCDF4 (UGRID) | B runner-up (NetCDF); C runner-up (HDF5/NetCDF); survey (UGRID) | xarray Apache-2.0 [3]; netCDF4 MIT [4] | xarray pure; netCDF4 cp311 abi3 wheels for macOS and Linux (x86_64, arm64/aarch64) plus win_amd64 cp311-cp314 [4] | 1 yes (UGRID mesh in netCDF4; xugrid MIT reads it [22]); 2 partly (ParaView netCDF reading of UGRID not verified); 3 partly (attributes only); 4 no (HDF5 locking); 5 n/a; 6 yes; 7 yes (not verified) | xarray 2026.9.0, 2026-09-29 [3]; netCDF4 1.7.5.1.post1, 2026-10-29 [4] | UGRID v1.0 is a CF-extending proposal describing corner nodes only [30]; no P2 node convention; multi-writer as for HDF5. |
| meshio (VTU, XDMF export) | today; B (XDMF); C (VTU) | MIT [5] | pure py3-none-any [5] | 1 partly (XDMF+HDF5, time series) [29]; 2 yes (VTU, XDMF open in ParaView) [29]; 3 no; 4 n/a; 5 n/a; 6 yes; 7 yes (XDMF 3.0 page edited 2022-12) [33] | 5.3.5, 2024-01-31 [5] | No release for 22 months; VTKHDF not listed [29]; handling of quadratic P2 cells not verified (XDMF lists Triangle_6 [33]). |
| VTKHDF via PyVista / VTK | A | pyvista MIT [6]; vtk BSD (PyPI classifier) [7] | pyvista pure; vtk cp311-cp314 on all five platforms [7] | 1 yes (UnstructuredGrid, spec 2.8) [23]; 2 yes (ParaView 5.13 writer, 6.0 reader work) [31]; 3 no; 4 as HDF5; 5 n/a; 6 yes; 7 partly (spec "not considered complete") [23] | pyvista 0.49.2, 2026-10-28 [6]; vtk 9.7.2, 2026-11-05 [7] | Heavy vtk dependency (size not verified); spec incomplete; whether h5py alone can write it is my inference, not verified. |
| ADIOS2 | survey | Apache (PyPI classifier) [8] | no win_amd64; macOS and Linux for cp311 and cp312 abi3 (covers 3.12+) [8] | 1 partly (not verified); 2 partly (ParaView reader not verified); 3 no; 4 partly (not verified); 5 n/a; 6 no (no Windows wheel); 7 partly | 2.13.0.1001, 2026-10-27 [8] | No Windows wheel; HPC streaming focus. |
| Parquet via pyarrow | A; B | Apache-2.0 [9] | all five platforms, cp311-cp314 [9] | 1 no; 2 no; 3 no; 4 partly (one file per run, my inference); 5 n/a; 6 yes; 7 yes (not verified) | 26.0.1, 2026-11-03 [9] | Tables only, not fields; large wheel (size not verified). |
| SQLite / DuckDB index | B (SQLite, disposable); survey | SQLite stdlib (licence not verified); DuckDB MIT [10] | DuckDB cp311 plus cp312 abi3, all five platforms [10] | 3 partly (query layer); 4 SQLite no on network file systems [25], DuckDB one read-write process, file locks need care on NAS [26]; 5 partly (query done runs); 6 yes; 7 yes (not verified) | DuckDB 2.0.1, 2026-11-20 [10] | Unsafe as shared store on a cluster file system; only fit as a rebuildable index. |
| RO-Crate (rocrate); W3C PROV (prov); CodeMeta | A, B, C (runner-up) | rocrate Apache-2.0 [11]; prov MIT [12] | both pure py3-none-any [11]\[12] | 3 partly (packaging and JSON-LD, spec 1.2 Recommendation 2025-06-04) [32]; run-record profiles not verified; PROV and CodeMeta specs not fetched; 6 yes; 7 yes | rocrate 0.16.0, 2026-10-06 [11]; prov 3.3.0, 2026-11-08 [12] | No field set for solver settings or stage hashes; adds a layer over the JSON manifest. |
| concurrent.futures + joblib | today; A and B (stdlib pool) | joblib BSD-3-Clause [13]; stdlib licence not verified | joblib pure [13] | 5 partly (one node only; chains hand-built; resume hand-built); 6 yes | joblib 1.6.0, 2026-08-31 [13] | No cluster dispatch. |
| submitit / plain SLURM array | C (submitit); today (array scripts) | MIT [14] | pure py3-none-any [14] | 5 partly (Slurm and local executors [34]; job-array use not stated there); 6 yes; no daemon | 1.5.4, 2025-12-17 [14] | No chain or resume logic; README says Python 3.11+, PyPI says >=3.8 [34]\[14]. |
| Snakemake | A, B, C (runner-up) | MIT [18] | pure py3-none-any, Python >=3.11 [18] | 5 partly (file-based resume yes; warm-start chains awkward per C, not verified); 6 yes | 9.27.2, 2026-11-15 [18] | Second language; Windows weakness (B's claim) not verified. |
| Dask / Ray / Parsl | A (Dask); survey | Dask BSD-3-Clause [15]; Ray Apache 2.0 [16]; Parsl Apache 2.0 [17] | Dask, Parsl pure; Ray win_amd64, macOS arm64, Linux, but no macOS x86_64 and no sdist [16] | 5 partly (scheduler processes; SLURM integration not verified); 6 partly (pip yes, runtime service no) | Dask 2026.11.0, 2026-11-23 [15]; Ray 2.60.1, 2026-11-23 [16]; Parsl 2026.11.23, 2026-11-23 [17] | Heavy for chains of dependent solves; extra runtime processes. |
| pydantic 2 + PyYAML (+ pint) | today; A, C (pydantic); B (JSON Schema) | pydantic MIT; PyYAML MIT [19]; pint BSD-3-Clause [21] | pydantic pure, pydantic-core and PyYAML wheels on all five platforms cp311-cp314 [19]; pint pure [21] | case schema: versioned, schema generated, comments survive (ruamel) | pydantic 2.14.4, 2026-11-19; PyYAML 6.0.4, 2026-11-20 [19]; pint 0.26.2, 2026-10-19 [21] | pint 0.26 needs Python >=3.12 [21]. Alternatives: tomllib stdlib; msgspec BSD-3 (wheels all five, 0.22.0, 2026-09-29), LinkML Apache-2.0 (pure, 1.12.1), jsonschema MIT (pure, 4.26.0) [20]. |

(b) Sources
1. https://pypi.org/pypi/h5py/json: 3.16.0, BSD-3-Clause, wheel list.
2. https://pypi.org/pypi/zarr/json: 3.4.2, MIT, pure, release history shows Python >=3.12 from 3.2.
3. https://pypi.org/pypi/xarray/json: 2026.9.0, Apache-2.0, pure.
4. https://pypi.org/pypi/netCDF4/json: wheel tags, MIT.
5. https://pypi.org/pypi/meshio/json: 5.3.5, 2024-01-31, MIT, pure.
6. https://pypi.org/pypi/pyvista/json: 0.49.2, MIT, pure.
7. https://pypi.org/pypi/vtk/json: 9.7.2, wheel list.
8. https://pypi.org/pypi/adios2/json: wheel tags, no Windows.
9. https://pypi.org/pypi/pyarrow/json.
10. https://pypi.org/pypi/duckdb/json.
11. https://pypi.org/pypi/rocrate/json.
12. https://pypi.org/pypi/prov/json.
13. https://pypi.org/pypi/joblib/json.
14. https://pypi.org/pypi/submitit/json.
15. https://pypi.org/pypi/dask/json and /distributed/json.
16. https://pypi.org/pypi/ray/json: no macOS x86_64 wheel.
17. https://pypi.org/pypi/parsl/json.
18. https://pypi.org/pypi/snakemake/json.
19. https://pypi.org/pypi/pydantic/json, /pydantic-core/json, /PyYAML/json.
20. https://pypi.org/pypi/msgspec/json, /linkml/json, /jsonschema/json.
21. https://pypi.org/pypi/pint/json: 0.26.x needs Python >=3.12.
22. https://pypi.org/pypi/xugrid/json: 0.15.3, MIT.
23. https://docs.vtk.org/en/latest/vtk_file_formats/vtkhdf_file_format/index.html: spec 2.8, UnstructuredGrid, "not considered complete".
24. https://zarr.readthedocs.io/en/stable/user-guide/performance/: safe writes to separate chunks on atomic-write stores.
25. https://www.sqlite.org/useovernet.html: network file systems unsafe for concurrent access.
26. https://duckdb.org/docs/2.0/connect/concurrency.html: one read-write process.
27. https://docs.h5py.org/en/stable/swmr.html: single writer, many readers.
28. https://support.hdfgroup.org/documentation/hdf5/latest/_file_lock.html (via search): locking problems on NFS and parallel file systems.
29. https://github.com/nschloe/meshio: XDMF and VTU listed, VTKHDF not mentioned.
30. https://ugrid-conventions.github.io/ugrid-conventions/: v1.0, corner nodes.
31. https://www.kitware.com/vtkhdf-file-format-2025-status-update/ and ParaView 5.13 notes (search snippets): writer and reader support.
32. https://www.researchobject.org/ro-crate/specification/1.2/index.html: 1.2, 2025-06-04; 1.3 listed.
33. https://www.xdmf.org/index.php/XDMF_Model_and_Format: XDMF 3.0, edited 2022-12-01, Triangle_6.
34. https://github.com/facebookincubator/submitit: Slurm and local executors, MIT.

(c) The table favours the present stack: one HDF5 file per run, written by one process, with a JSON manifest, pydantic and YAML, a process pool and a plain or submitit SLURM array. VTU or XDMF export covers ParaView. Zarr 3 is the runner-up, for the sweep dataset only. Its concurrent chunk writes are the one real gain [24], but 3.2 and later need Python >=3.12 [2]. The fact that could overturn this: whether ParaView shows P2 fields from XDMF (Triangle_6 is listed [33]) or VTKHDF without resampling. This was not verified.


## Structure and charge preparation, and distribution

**Today's choice.** MDAnalysis for structures, trajectories and alignment; gemmi for mmCIF; PDB2PQR with PROPKA for protonation, charges and radii, as the paper prescribes; APBS as a test-time cross-check; GridDataFormats for grids. A pure-Python wheel with extras, not yet on PyPI, developed with uv; no installer, no conda package, no container image.

**The needs**, numbered as the table's *Meets the needs* cells number them:

1. reads PDB and mmCIF, with biological assemblies and symmetry operations;
2. reads molecular-dynamics trajectories (DCD, XTC, TRR, NetCDF);
3. repairs a structure: missing atoms, missing residues, alternate locations;
4. assigns protonation at a pH, and partial charges and radii from a named force field;
5. binary or pure wheels on Windows, macOS and Linux for Python 3.11 to 3.14;
6. licence fit (permissive, LGPL or MPL).

For a distribution channel the cell answers instead: what the user must have installed first; whether it works
offline and behind a proxy; what the maintainer builds and signs for a release; whether it carries the compiled
dependencies.

**The report, as returned.**

**(a) Table** (checked 24 Nov 2026. "Local test" = CPython 3.14.6 venv made with uv, packages installed from PyPI, no compiler [14].)

| Candidate | Named by | Licence | Wheels | Meets the needs | Last release | Lacks |
|---|---|---|---|---|---|---|
| MDAnalysis (+ hard dependency GridDataFormats) | today; A, C (trajectories) | LGPL-3.0-or-later [1] | cp311-314: win_amd64, macOS arm64+x86_64, manylinux x86_64+aarch64 [1] | 1 partly: PDB, mmCIF via gemmi (new in 2.11, optional extra), no assemblies [1]\[14]; 2 yes: DCD, XTC, TRR, NC readers (NetCDF needs the netCDF4 extra) [14]; 3 no; 4 no, reads PQR only [14]; 5 yes [1]; 6 yes (LGPL) | 2.11.0, 2026-10-21 [1] | Cannot expand assemblies, repair or protonate. Hard dependencies include matplotlib and scipy [1]. |
| gemmi | today; A, B, C (reading) | MPL-2.0 [2] | cp311-314: win_amd64, macOS arm64+x86_64, manylinux x86_64+aarch64 (+musllinux) [2] | 1 yes: `make_assembly`, `expand_ncs`; read 1UBQ, built its assembly [14]; 2 no; 3 partly: `remove_alternative_conformations`, no atom or residue building [14]; 4 no; 5 yes; 6 yes | 0.7.5, 2026-03-02 [2] | No trajectories, no protonation, no charges. |
| Biopython | C (reading, runner-up) | LicenseRef-Biopython-License-Agreement per PyPI; BSD-3 option not verified [3] | cp311-314: win_amd64, macOS arm64 only, manylinux x86_64+aarch64 [3] | 1 partly: MMCIFParser, no assembly code found [14]; 2 no; 3 no; 4 no; 5 partly: no macOS x86_64; 6 yes | 1.88, 2026-08-06 [3] | No assemblies, repair, protonation or trajectories. |
| Biotite | A, runner-up | BSD-3-Clause [4] | cp312-315 only: win_amd64, macOS arm64 only, manylinux x86_64+aarch64; none for 3.11 [4] | 1 yes: `get_assembly`, `list_assemblies` [14]; 2 yes: XTC, TRR, DCD, NetCDF via biotraj [14]; 3 no: `repair` only infers elements and names [14]; 4 no: only `partial_charges` [14]; 5 no: needs Python ≥3.12; 6 yes | 2.0.0, 2026-10-18 [4] | Drops Python 3.11 and macOS x86_64. No force-field charges or pH. |
| MDTraj | A (runner-up) | LGPL-2.1-or-later [5] | cp312-314: win_amd64, macOS universal2, manylinux x86_64+aarch64; none for 3.11 [5] | 1 partly: PDB, PDBx file class, assemblies not found [14]; 2 yes: DCD, XTC, TRR, NetCDF loaders [14]; 3 no; 4 no; 5 no: needs Python ≥3.12; 6 yes | 1.11.2, 2026-10-05 [5] | Drops Python 3.11. Trajectory analysis only. |
| ProDy | survey | MIT [6] | One wheel only: cp312 manylinux_2_35 x86_64; others build from sdist [6] | 1 yes: `buildBiomolecules`, `parseMMCIF` [14]; 2 partly: DCD found, no XTC, TRR or NetCDF [14]; 3 no; 4 no; 5 no; 6 yes | 2.6.1, 2025-08-19 [6] | Needs a compiler on most platforms, which breaks CON-07. |
| PDBFixer + OpenMM (force fields via openmmforcefields) | A, B, C (optional extra) | MIT [7]; OpenMM: PyPI says PSF/BSD-like [8], conda-forge says LGPL-3.0-or-later [15]; openmmforcefields MIT [12] | PDBFixer: sdist only, no wheel; pure Python, built here on 3.14 with no compiler [7]\[14]. OpenMM cp311-314: win_amd64, macOS universal2, manylinux x86_64+aarch64 [8]. openmmforcefields: sdist only [12] | 1 partly: OpenMM readers, assemblies not verified; 2 no; 3 yes: `findMissingResidues`, `findMissingAtoms`, `addMissingAtoms`, `applyMutations` [14]; 4 partly: `addMissingHydrogens(pH, forcefield)`; named force field through OpenMM, not run; 5 yes; 6 partly: licence differs by source | PDBFixer 1.12.0, 2026-02-06 [7]; OpenMM 8.6.1, 2026-09-11 [8]; openmmforcefields 0.15.1, 2026-02-26 [12] | The only repair route. PDBFixer has a single PyPI release. Its pH rule is generic, with no PROPKA. openmmforcefields is conda-first (0.16.0 there [15]). |
| PDB2PQR + PROPKA | today; A, B, C | PDB2PQR BSD-3 [9]; PROPKA LGPL-2.1 [10] | Both py3-none-any [9]\[10] | 1 partly: mmCIF and PDB in, run on 1UBQ [14]; 2 no; 3 partly: adds missing heavy atoms and hydrogens, no missing residues; 4 yes: PROPKA at `--with-ph`, AMBER/CHARMM/PARSE/TYL06/PEOEPB/SWANSON charges and radii, run on 3.14 [14]; 5 yes; 6 yes | PDB2PQR 3.8.0, 2026-10-24 [9]; PROPKA 3.5.1, 2024-01-02 [10] | PROPKA has had no release for 23 months. No assemblies; a symmetric oligomer must be assembled first. |
| pKAI | survey (ML pKa) | MIT [11] | py3-none-any, but 1.2.0 needs torch<2, which has wheels to cp311 only [11] | 1 no; 2 no; 3 no; 4 partly: pKa only, no charges or radii; 5 no on 3.12+; 6 yes | 1.2.0, 2022-08-03 [11] | Stale. The 1.1 release resolves with torch 2.15 on 3.14, not run [14]. Heavy torch dependency. |
| GridDataFormats | today | LGPL-3.0-or-later [13] | py3-none-any [13] | OpenDX and CCP4 grids: reads them, not run; 5 yes; 6 yes | 1.2.0, 2026-05-23 [13] | Already a hard dependency of MDAnalysis [1]. |
| Channel: PyPI wheels, pip / uv / `uvx` / pipx | today; A, B, C | uv MIT OR Apache-2.0 [23]; pipx MIT [23] | Carries compiled dependencies as wheels; ngsolve wheels are 15-44 MB each [22], the brief's ~100 MB total not re-measured | Needs nothing first with uv (installer, then it downloads Python from python-build-standalone) [16]; with pip, Python ≥3.11. Offline: `--offline` and cache [16], first run needs network. Proxy: HTTP(S)_PROXY, SSL_CERT_FILE, Python mirror setting [16]. Maintainer: build one wheel and sdist per release; no signing needed (not verified) | uv 0.13.9, 2026-11-17; pipx 1.19.1, 2026-11-23 [23] | The PDBFixer route is a sdist only [7]. |
| Channel: conda-forge + pixi | C (runner-up); A, B (rejected) | pixi BSD-3 [15] | Carries compiled dependencies as conda packages; conda-forge has MDAnalysis 2.11.0, gemmi 0.7.5, pdb2pqr 3.8.0, pdbfixer 1.12, openmm 8.6.1 and apbs 3.4.1 on 5 platforms or noarch [15] | Needs pixi first. Offline: `--offline`, cache; proxy and mirrors configurable; PyPI resolution can still need network [17]. Maintainer: a feedstock recipe per release, no signing | pixi 0.84.2, 2026-11-13 [15] | No `ngsolve` package on conda-forge (404) [15], so the engine would still come from PyPI. |
| Channel: container (Docker, Apptainer) | B, C (clusters) | Apptainer licence not checked | Carries everything, compiled dependencies included; image size not measured | Needs a container runtime. Apptainer runs `docker://` images as a regular user and can pull once to a SIF file [20]; Docker Hub rate limits apply [20]. Maintainer: build and push an image per release, one per architecture | not applicable | No Windows or macOS desktop path (not verified). Proxy behaviour not verified. |
| Channel: frozen installer (PyInstaller, Briefcase, constructor, pixi-pack) | A, B (rejected on signing cost), C | PyInstaller GPL-2.0-or-later with a special exception for non-free programs [19]; Briefcase BSD-3 [21]; constructor, pixi-pack BSD-3 [15] | Bundles everything, Python and compiled dependencies included | Needs nothing first; works offline. pixi-pack makes a self-extracting executable [18]. Maintainer: build on each OS, since PyInstaller cannot cross-build [19]; signing and notarisation not verified (Briefcase page silent [21]) | PyInstaller 6.22.3, 2026-09-12 [19]; Briefcase 0.4.7, 2026-10-27 [21]; pixi-pack 0.7.12, 2026-11-07 [15] | Per-OS builds and certificates for one maintainer. |

**(b) Sources**
1. https://pypi.org/pypi/MDAnalysis/json: 2.11.0, wheel tags, LGPLv3+ text, dependency list.
2. https://pypi.org/pypi/gemmi/json: 0.7.5, MPL-2.0, wheel tags.
3. https://pypi.org/pypi/biopython/json: 1.88, licence, wheel tags.
4. https://pypi.org/pypi/biotite/json: 2.0.0, BSD-3-Clause, Python ≥3.12.
5. https://pypi.org/pypi/mdtraj/json: 1.11.2, LGPL-2.1-or-later, Python ≥3.12.
6. https://pypi.org/pypi/prody/json: 2.6.1, one wheel plus sdist.
7. https://pypi.org/pypi/pdbfixer/json: sdist only, single release 1.12.0, MIT.
8. https://pypi.org/pypi/openmm/json: 8.6.1, wheel tags, licence string.
9. https://pypi.org/pypi/pdb2pqr/json: 3.8.0, py3-none-any, BSD text.
10. https://pypi.org/pypi/propka/json: 3.5.1, 2024-01-02, LGPL v2.1.
11. https://pypi.org/pypi/pkai/json (also /pkai/1.1/json and /torch/1.13.1/json): torch<2 pin; torch 1.13.1 has wheels to cp311.
12. https://pypi.org/pypi/openmmforcefields/json: 0.15.1, sdist only, MIT.
13. https://pypi.org/pypi/GridDataFormats/json: 1.2.0, LGPL-3.0-or-later.
14. Local test (scratchpad venv, CPython 3.14.6): installed the packages, listed MDAnalysis readers and parsers, ran gemmi `make_assembly` and pdb2pqr on 1UBQ mmCIF (https://files.rcsb.org/download/1UBQ.cif), and listed biotite, mdtraj, prody, Bio.PDB and pdbfixer APIs.
15. https://api.anaconda.org/package/conda-forge/&lt;name&gt;: versions, licences and platforms; ngsolve returns 404.
16. https://docs.astral.sh/uv/concepts/tools/, /reference/environment/, /concepts/python-versions/.
17. https://pixi.prefix.dev/latest/reference/pixi_configuration/: proxy, mirrors, offline.
18. https://raw.githubusercontent.com/Quantco/pixi-pack/main/README.md: self-extracting executable.
19. https://pyinstaller.org/en/stable/operating-mode.html and https://pypi.org/pypi/pyinstaller/json.
20. https://apptainer.org/docs/user/latest/docker_and_oci.html.
21. https://briefcase.beeware.org/en/stable/reference/platforms/macOS/app.html and https://pypi.org/pypi/briefcase/json.
22. https://pypi.org/pypi/ngsolve/json: 6.2.2608 wheel sizes.
23. https://pypi.org/pypi/uv/json and /pipx/json.

**(c)** From nothing, the table favours today's stack: gemmi (assemblies, MPL), MDAnalysis (trajectories), PDB2PQR with PROPKA (pH, charges, radii). Both PDB2PQR and PROPKA are pure Python and ran on 3.14. It ships on PyPI, installed with `uvx`/uv. PDBFixer stays an optional extra for missing residues. Runner-up: Biotite, which does assemblies and trajectories under BSD-3, but drops Python 3.11 and macOS x86_64. PDB2PQR would still do the charges. The conda-forge/pixi channel is the runner-up channel. One fact could overturn the choice: PROPKA has had no release since 2024-01-02. If that stops working on a new Python, protonation and charges have no pure-wheel replacement. pKAI is stale and needs torch.

## Checked at the source

The main session checked these itself on 24 November 2026, each by the command shown. A proposal of the report rests
on a fact of this section, or says that the fact is an agent's.

**Releases and wheels.** `curl -s https://pypi.org/pypi/<name>/json`, the version, `requires_python`, the upload date
and the wheels' platform tags read from it; the locked version from `uv.lock`:

| Package | Latest, date | Needs Python | Wheels, or the lack | The program locks |
|---|---|---|---|---|
| `ngsolve` | 6.2.2608, 2026-10-01 | 3.10 or later | Windows x86-64, macOS universal, Linux x86-64; none for Linux on ARM | 6.2.2606 |
| `nicegui` | 4.0.0, 2026-11-04 | 3.11 or later | pure Python | 3.18.0 |
| `scipy` | 1.18.1, 2026-08-21 | 3.12 or later | all three systems | 1.17.1 on Python 3.11, 1.18.0 above |
| `Pint` | 0.26.2, 2026-10-19 | 3.12 or later | pure Python | 0.25.3, held below 0.26 |
| `zarr` | 3.4.2, 2026-10-27 | 3.12 or later | pure Python | not used |
| `panel` | 1.10.1, 2026-11-23 | 3.12 or later | pure Python | not used |
| `MDAnalysis` | 2.11.0, 2026-10-21 | 3.11 or later | all three systems | 2.10.0 |
| `gmsh` | 4.15.2, 2026-03-24 | not stated | Windows, macOS, Linux x86-64; none for Linux on ARM | optional |
| `mkl` | 2026.2.1, 2026-11-12 | not stated | Windows and Linux x86-64 only; none for macOS | not used |
| `pdbfixer` | 1.12.0, 2026-02-06 | not stated | no wheel, a source archive only | not used |
| `fenics-dolfinx` | none: the address answers 404 | | | not used |

`curl https://api.anaconda.org/package/conda-forge/ngsolve` answers 404: conda-forge has no NGSolve.

Four of the libraries surveyed have dropped Python 3.11 in their newest release (SciPy, Pint, Zarr, Panel), and the
surveys add Biotite and MDTraj. The program's floor of 3.11 already holds two of its own dependencies at an older
line.

**The engine's wheel**, as installed (`uv run python`, NGSolve 6.2.2606, Linux x86-64):

- `ngsolve.config` reads `USE_UMFPACK` true and `USE_MKL`, `USE_PARDISO`, `USE_MUMPS` and `USE_HYPRE` false.
- `mat.Inverse(freedofs, inverse=<name>)` on a P2 convection–diffusion matrix: `umfpack`, `sparsecholesky` and
  `superlu` return a solver; `pardiso` answers "MKL Pardiso is not available. Ensure that MKL is installed"; `mumps`
  answers "no inverse available".
- `ngsolve/solvers/mkl_pardiso.py`, 251 lines, looks for `mkl_rt` at run time and, where the `mkl` package of pip
  supplies it, calls `SetDefaultInverseType("pardiso")`. PARDISO is therefore one `pip install mkl` away on Windows and
  Linux x86-64, and not on macOS.
- **A transposed solve with the same factors exists.** `inv.T` of the UMFPACK inverse solved the transposed system to
  a residual of 1.9 × 10⁻¹⁶ against `scipy`'s transpose of the same matrix. The engine survey's failure of
  `mat.T.Inverse` is another call and no obstacle to an adjoint.
- `inv.Update()` runs. Whether it repeats the symbolic analysis is not shown by it; REV-60 records that the program's
  own loop repeats it.

**The program's own use.** `grep -rn 'Compile(' src/nanopnp` prints one line, in `validation/mms.py`: the weak forms
of a solve are evaluated as uncompiled expression trees. `uv run nanopnp --env` prints "this installation is used under
GPL-2+: its default linear solver, UMFPACK, is GPL-2+ (the library is BSD-3-Clause)": the question the solver survey
raises about the licence is one the program already answers to its user (CON-11).

**Not checked, and why.** The two timings of a direct solve are the agents' own runs on this shared container and
disagree: 50 s to factor 653,000 unknowns of a stand-in form in one, 21 s and 6.2 GB for 1.16 million unknowns of a
Stokes matrix with convection in the other, which also saw times vary tenfold between identical runs. Neither matrix is
the model's. What a direct solve of the model costs at 10⁶ unknowns, with UMFPACK and with PARDISO, is a question for a
trial (the report, *What stays open*). The smoothness of a field map of 10⁵ cells in plotly.js, and whether ParaView
shows a second-order field from XDMF or VTKHDF without resampling, are the same kind.
