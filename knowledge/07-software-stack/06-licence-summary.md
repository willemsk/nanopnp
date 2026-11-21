---
type: Library Behaviour
title: 6. Licence summary
description: The licences of the dependencies.
tags:
- software
- library-behaviour
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
tested_with:
  ngsolve: 6.2.2606
  scipy: 1.18.0
  gmsh: 4.15.2
  mdanalysis: 2.10.0
  nicegui: 3.18.0
  gemmi: 0.7.5
verified:
- by: process:tests/tier1/test_gui_selftest.py::test_con11_the_licence_notice_states_the_installations_licence
  at: '2026-11-21T00:00:00Z'
---

## 6. Licence summary

Permissive core is achievable. The table gives each copyleft or weak-copyleft dependency, and the
permissive ones a reader is most likely to ask about, with the licence its installed metadata states
(read 10 November 2026) and the clause that governs it. `SPECIFICATION.md` §2.6 is the home for
each dependency's role and licence.

| Package | Licence (metadata) | Clause | Note |
|---|---|---|---|
| NGSolve, netgen-mesher | LGPL-2.1-only | CON-09 | Dynamically linked |
| netgen-occt | LGPLv2+ | CON-09 | The OpenCASCADE libraries netgen loads |
| MDAnalysis | LGPLv3+ | CON-09 | |
| GridDataFormats | LGPL-3.0-or-later | CON-09 | |
| PROPKA | LGPL v2.1 | CON-09 | Run by PDB2PQR |
| `webgui` (NGSolve's renderer) | LGPL-2.1-or-later | CON-09 | Loaded as a separate file (`05-gui-and-packaging.md`) |
| gemmi | MPL-2.0 | CON-09 | File-level copyleft, used unmodified as a separate package (CON-09, amended 25 September 2026) |
| NiceGUI, FastAPI, pydantic, PyYAML, meshio | MIT | CON-09 NOTE | The front end's dependencies are permissive |
| uvicorn, h5py, Shapely, SciPy, PDB2PQR | BSD | | |
| apbs-binary | Apache-2.0 | | The `apbs` group, for VAL-06 |
| **Gmsh** | GPLv2+ | CON-10 | Optional mesher backend only |
| **SuiteSparse UMFPACK** | GPL-2+ | CON-11 | See below |
| **Triangle / TetGen 1.5** | restricted / AGPLv3 | CON-12 | Avoided entirely |

**SuiteSparse UMFPACK.** It is the default linear solver, built into the NGSolve wheel, so an
*installation* that runs a case carries GPL-2+ obligations even though the library does not.
`src/nanopnp/THIRD-PARTY-LICENSES.md` states them, and `nanopnp --env` states the obligation and
the notice's path. **[tested: tests/tier1/test_gui_selftest.py::test_con11_the_licence_notice_states_the_installations_licence]** SciPy's SuperLU (BSD) is not an alternative at production size:
on the reference-sized factorisation (~1.2 × 10⁵ cells, five fields) it was OOM-killed, while
UMFPACK completed — the measurement behind SPECIFICATION.md §6.6 and the CON-11 amendment of
2 September 2026.
