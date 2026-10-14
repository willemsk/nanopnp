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
---

## 6. Licence summary

Permissive core is achievable. Everything is LGPL/BSD/MIT/Apache **except**:

- **Gmsh** GPLv2+ → optional mesher backend only.
- **SuiteSparse UMFPACK** GPL-2+ → if it is the bundled default linear solver, the *bundle*
  carries GPL even though the library does not, so the distribution licence follows the solver
  chosen as default. **[tested: pending]** SciPy's SuperLU (BSD) is not an alternative at production size:
  on the reference-sized factorisation (~1.2 × 10⁵ cells, five fields) it was OOM-killed, while
  UMFPACK completed — the measurement behind SPECIFICATION.md §6.6 and the CON-11 amendment of
  2 September 2026.
- **Triangle / TetGen** → avoid entirely.

LGPL dependencies (NGSolve, MDAnalysis, PySide6) are fine for a permissively-licensed project when
dynamically linked. gemmi is MPL-2.0. That copyleft is file-level, so it is fine used unmodified as
a separate package (CON-09, amended 25 September 2026).

---

