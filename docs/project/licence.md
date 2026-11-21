# Licence

**The nanopnp library is BSD-3-Clause.** See
[`LICENSE`](https://github.com/willemsk/nanopnp/blob/main/LICENSE).

**An installation that runs a case is used under GPL-2+.** Its default direct linear solver,
SuiteSparse UMFPACK, is GPL-2+ and is built into the NGSolve wheel that `uv sync` installs. The
library itself stays BSD-3 and reaches UMFPACK only through that wheel (CON-11). UMFPACK is the
default because the BSD-licensed SuperLU alternative ran out of memory on the reference-sized
factorisation (§6.6). SuperLU stays selectable (`numerics.linear.solver: superlu`), but an
installation configured that way still carries UMFPACK, so its obligations do not change.
`nanopnp --env` states the obligation and names the notice below.

The notice installed with the package lists every component, its licence, and your right to
replace the LGPL components in place:
[`src/nanopnp/THIRD-PARTY-LICENSES.md`](https://github.com/willemsk/nanopnp/blob/main/src/nanopnp/THIRD-PARTY-LICENSES.md).

gmsh (GPL-2+) is an optional mesher backend only. It is never imported on the default path, and the
library works without it (CON-10).
