# Licences of the nanopnp desktop bundle

**This bundle is distributed under the GNU General Public License, version 2 or later
(GPL-2+).** The nanopnp library itself is BSD-3-Clause and remains so; the bundle's licence is
GPL-2+ because its default linear solver, SuiteSparse UMFPACK, is GPL-2+ and is linked into the
NGSolve wheel the bundle carries. `SPECIFICATION.md` CON-11 requires this to be stated here, and
§6.6 records the measurement behind defaulting to UMFPACK: scipy's BSD-licensed SuperLU was
OOM-killed on the reference-sized factorisation, so a SuperLU-default bundle could not run the
published case. SuperLU remains selectable at run time (`numerics.linear.solver: superlu`); a
bundle configured that way is still distributed under GPL-2+, because UMFPACK ships inside it
regardless of which solver a case selects.

| Component | Licence | What it is here |
|---|---|---|
| nanopnp | BSD-3-Clause | This application and the library it drives |
| NGSolve, Netgen | LGPL-2.1 | Finite-element backend and mesher, dynamically linked |
| Open CASCADE Technology (`netgen-occt`) | LGPL-2.1 with the OCCT exception | Netgen's CAD kernel, dynamically linked; its licence text travels in `netgen_occt-*.dist-info/` |
| OpenBLAS (`ngsolve-openblas`) | BSD-3-Clause | NGSolve's dense linear algebra, dynamically linked. A Linux bundle also carries the `libgfortran` it links, under GPL-3 with the GCC Runtime Library Exception |
| SuiteSparse UMFPACK | **GPL-2+** | Default direct linear solver, built into the NGSolve wheel |
| PySide6, Qt 6 (including Qt WebEngine) | LGPL-3 | Desktop shell and the embedded field viewer, dynamically linked |
| NumPy, SciPy, pydantic, PyYAML, meshio, h5py, SymPy | BSD-3-Clause / MIT / Apache-2.0 | Numerics, configuration and file formats |

## Your rights under the LGPL components

NGSolve, Netgen, Open CASCADE, PySide6 and Qt are used under their LGPL options, which give you the right to
replace them with your own versions. The bundle is built **one-dir** rather than one-file precisely
so that you can: every shared library is an ordinary file in the bundle directory and may be
replaced in place. Nothing in the bundle is statically linked against an LGPL component.

## Source

nanopnp's source, including the build recipe for this bundle
(`packaging/nanopnp-probe.spec`), is at <https://github.com/willemsk/nanopnp>. The upstream sources
of every component above are available from their own projects; NGSolve at
<https://ngsolve.org>, SuiteSparse at <https://people.engr.tamu.edu/davis/suitesparse.html>, and
Qt for Python at <https://doc.qt.io/qtforpython>.

## What this bundle is

The current bundle is the **packaging probe** of `SPECIFICATION.md` §8.2 criterion 4 as amended by
§8.2.1 A4: a trivial application that imports PySide6, Qt WebEngine, NGSolve, Netgen and
`ngsolve.webgui` in one process, so that RSK-13 — desktop packaging defeated by a binary
dependency — is detected on every push rather than once. It is not the desktop shell, and it solves
nothing. The licence obligations above are stated with the first bundle rather than with the first
useful one, because a licence statement cannot be retrofitted to something already distributed.
