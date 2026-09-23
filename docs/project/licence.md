# Licence

**The nanopnp library is BSD-3-Clause.** See
[`LICENSE`](https://github.com/willemsk/nanopnp/blob/main/LICENSE).

**The desktop bundle is GPL-2+.** Its default direct linear solver, SuiteSparse UMFPACK, is GPL-2+
and is built into the NGSolve wheel, so a bundle that carries NGSolve is distributed as a whole under
GPL-2+. The library itself stays BSD-3 (CON-11). UMFPACK is the default because the BSD-licensed
SuperLU alternative ran out of memory on the reference-sized factorisation (§6.6). SuperLU remains
selectable (`numerics.linear.solver: superlu`), but a bundle configured that way still carries
UMFPACK and is still GPL-2+.

The notice that travels with every bundle lists every component, its licence, and your right to
replace the LGPL components in place, which is why the bundle is built one-dir:
[`packaging/LICENSES-BUNDLE.md`](https://github.com/willemsk/nanopnp/blob/main/packaging/LICENSES-BUNDLE.md).

gmsh (GPL-2+) is an optional mesher backend only. It is never imported on the default path, and the
library works without it (CON-10).
