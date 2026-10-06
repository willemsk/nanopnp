"""Direct linear solves (NUM-21).

At 2D-axisymmetric sizes a sparse direct method is the right answer: nested
dissection fills in ``O(N log N)`` and factorises in ``O(N^1.5)``. It is 3D where
this collapses.

The pip wheel constrains the choice. ``ngsolve.config`` reports ``USE_MUMPS``,
``USE_PARDISO`` and ``USE_MKL`` all false, so neither the reference model's
PARDISO nor MUMPS is reachable without a source build and the compiler
dependency ADR-001 exists to avoid. UMFPACK *is* built into the wheel and is the
default here; it is GPL-2+, which bears on what a redistributable bundle may
contain (CON-11) but not on the library itself.

``sparsecholesky`` is rejected rather than merely discouraged: it is SPD-only,
and the coupled five-field system is unsymmetric, so it would either fail or
return a wrong answer.

The scipy SuperLU path exists for licensing rather than for performance
(CON-08, CON-11). UMFPACK is SuiteSparse and GPL-2+; a redistributable bundle
that must not carry a copyleft dependency needs a BSD-licensed factorisation,
and SuperLU is it. It is slower, so it is a fallback and not the default.

Scaling (NUM-10) is the third concern here. Even after nondimensionalisation the
five diagonal blocks of the Jacobian do not have comparable norms — the Poisson
block scales as ``1/lambda~^2``, which is 130 at 3 M and a pore radius of 2 nm,
while the continuity block has no scale of its own at all. A direct solver's
pivoting is not scale-invariant, so the spread shows up as a loss of digits.
``field_row_scaling`` measures the spread and ``report_block_scaling`` warns
when it is large enough to matter.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    from scipy.sparse import csr_matrix

from nanopnp.core.typing import Expression, FESpace, GridFunction, Mesh, Option

logger = logging.getLogger(__name__)

DEFAULT_SOLVER = "umfpack"
"""Direct solver used unless a case says otherwise."""

BLOCK_SCALING_WARNING = 1.0e3
"""Ratio of largest to smallest diagonal-block norm above which to warn (NUM-10)."""

_REJECTED = {
    "sparsecholesky": (
        "sparsecholesky is SPD-only and cannot factorise the unsymmetric coupled system (NUM-21)"
    ),
    "pardiso": "PARDISO is absent from the NGSolve wheel; the reference model's solver is "
    "unavailable on the default path (NUM-21)",
    "mumps": "MUMPS is absent from the NGSolve wheel and needs a source build with MPI (NUM-21)",
}


AVAILABLE_SOLVERS = frozenset({"umfpack", "superlu"})
"""Solvers this build can actually use."""


def check_solver(name: str) -> str:
    """Return ``name`` if it is usable on this build, else explain why it is not.

    Raises
    ------
    ValueError
        If the solver is one this project rejects, or is unavailable in the
        installed NGSolve. The message says which and why.
    """
    if name in _REJECTED:
        raise ValueError(f"linear solver {name!r} is not usable: {_REJECTED[name]}")
    if name not in AVAILABLE_SOLVERS:
        raise ValueError(
            f"unknown linear solver {name!r}; this build offers {sorted(AVAILABLE_SOLVERS)}"
        )
    return name


def solve_linear(
    bilinear: Expression,
    linear: Expression,
    solution: GridFunction,
    *,
    solver: str = DEFAULT_SOLVER,
) -> None:
    """Solve one assembled linear variational problem in place.

    The inhomogeneous Dirichlet data already set on ``solution`` is respected:
    the correction is solved for and added, rather than the free part alone.

    Parameters
    ----------
    bilinear, linear
        Assembled forms.
    solution
        Grid function carrying the boundary values on entry and the solution on
        exit.
    solver
        Direct solver name; see ``check_solver``.
    """
    space = solution.space
    residual = linear.vec.CreateVector()
    residual.data = linear.vec - bilinear.mat * solution.vec
    correction = linear.vec.CreateVector()
    solve_correction(bilinear.mat, residual, correction, space.FreeDofs(), solver=solver)
    solution.vec.data += correction


def solve_correction(
    matrix: Expression,
    rhs: Expression,
    correction: Expression,
    freedofs: Option,
    *,
    solver: str = DEFAULT_SOLVER,
) -> None:
    """Solve ``matrix @ correction = rhs`` on the free degrees of freedom, in place.

    The single point at which a solver name becomes a factorisation, so that
    every caller — the linear driver and every Newton step alike — gets the same
    implementation of the same name. Routing ``superlu`` through here rather than
    through ``mat.Inverse(inverse="superlu")`` is what keeps the row
    equilibration of NUM-10 on the coupled Jacobian, where the block-norm spread
    that motivates it actually lives; NGSolve's own registered SuperLU does not
    equilibrate.

    The factorisation is a local: it is released on return rather than being held
    while the next one is built. At the reference mesh size a single UMFPACK
    factorisation of the five-field system is 6.2 GB (SPECIFICATION.md section
    6.6), so holding two at once does not fit on the laptop the criterion is
    measured against.

    Parameters
    ----------
    matrix
        Assembled system matrix.
    rhs
        Right-hand-side vector.
    correction
        Vector the solution is written into. Zero on the constrained degrees of
        freedom.
    freedofs
        ``BitArray`` of degrees of freedom to solve for.
    solver
        Direct solver name; see :func:`check_solver`.
    """
    check_solver(solver)
    if solver == "superlu":
        correction.FV().NumPy()[:] = solve_superlu(matrix, rhs, freedofs)
        return
    correction.data = matrix.Inverse(freedofs, inverse=solver) * rhs


def to_scipy(matrix: Expression) -> csr_matrix:
    """Return an assembled NGSolve sparse matrix as a scipy CSR matrix.

    NGSolve's ``COO`` export lists duplicate entries for the same position;
    scipy's COO constructor sums them, which is the correct assembly semantics.
    """
    import numpy as np
    from scipy import sparse

    rows, cols, values = matrix.COO()
    shape = (matrix.height, matrix.width)
    return sparse.coo_matrix(
        (np.asarray(values), (np.asarray(rows), np.asarray(cols))), shape=shape
    ).tocsr()


def solve_superlu(
    matrix: Expression, rhs: Expression, freedofs: Option, *, equilibrate: bool = True
) -> np.ndarray:
    """Solve one linear system on the free degrees of freedom with scipy's SuperLU.

    The BSD-licensed fallback of CON-08/CON-11. The constrained rows and columns
    are dropped rather than zeroed, so the submatrix that reaches SuperLU is the
    one that is actually non-singular; the returned correction is zero on the
    constrained degrees of freedom.

    Parameters
    ----------
    matrix
        Assembled system matrix.
    rhs
        Right-hand-side vector.
    freedofs
        ``BitArray`` of degrees of freedom to solve for.
    equilibrate
        Apply row equilibration before factorising (NUM-10). Each row is divided
        by its largest magnitude, which costs one pass over the matrix and
        removes the block-scale spread that pivoting would otherwise pay for.

    Returns
    -------
    numpy.ndarray
        The correction over all degrees of freedom.

    Raises
    ------
    RuntimeError
        If the factorisation fails, with the matrix size in the message so the
        failure is attributable.
    """
    import numpy as np
    from scipy import sparse
    from scipy.sparse.linalg import splu

    free = np.asarray(list(freedofs), dtype=bool)
    system = to_scipy(matrix)[free][:, free]
    right = np.asarray(rhs.FV().NumPy())[free].astype(float)

    if equilibrate:
        scale = np.asarray(abs(system).max(axis=1).todense()).ravel()
        scale[scale == 0.0] = 1.0
        system = sparse.diags(1.0 / scale) @ system
        right = right / scale

    try:
        factorisation = splu(system.tocsc())
    except RuntimeError as error:  # pragma: no cover - depends on the input matrix
        raise RuntimeError(
            f"SuperLU factorisation failed on a {system.shape[0]}x{system.shape[1]} system "
            f"with {system.nnz} nonzeros: {error}"
        ) from error

    correction = np.zeros(matrix.height)
    correction[free] = factorisation.solve(right)
    return correction


def diagonal_block_norms(matrix: Expression, space: FESpace) -> dict[str, float]:
    """Return the norm of each diagonal Jacobian block of a compound space (NUM-10).

    The norm is the largest absolute row sum of the block restricted to its own
    rows and columns, which is the quantity NUM-10 wants to be O(1) for every
    field.

    Parameters
    ----------
    matrix
        Assembled system matrix.
    space
        Compound finite-element space whose components name the fields. A
        non-compound space is reported as one block named ``field``.

    Returns
    -------
    dict
        Component index (as ``field_0``, ``field_1``, ...) to block norm.
    """
    system = to_scipy(matrix)
    ranges = _component_ranges(space)
    norms: dict[str, float] = {}
    for name, (start, stop) in ranges.items():
        # abs() the block, not the whole matrix: the diagonal blocks are a small
        # fraction of a coupled Jacobian that runs to 6e7 nonzeros at production
        # size, and the full copy would dominate the cost of the diagnostic.
        block = abs(system[start:stop, start:stop])
        norms[name] = float(block.sum(axis=1).max()) if block.nnz else 0.0
    return norms


def field_row_scaling(matrix: Expression, space: FESpace) -> dict[str, float]:
    """Return the reciprocal diagonal-block norms, the NUM-10 row scaling factors.

    A block with a zero norm — a pure constraint block, such as the pressure
    diagonal of a Taylor-Hood system — is left unscaled at 1.0 rather than
    producing an infinity.
    """
    return {
        name: (1.0 / norm if norm > 0.0 else 1.0)
        for name, norm in diagonal_block_norms(matrix, space).items()
    }


def report_block_scaling(
    matrix: Expression, space: FESpace, *, threshold: float = BLOCK_SCALING_WARNING
) -> dict[str, float]:
    """Log the diagonal-block norms and warn if their spread exceeds ``threshold``.

    Returns the norms, so a caller can put them in the provenance manifest.
    """
    norms = diagonal_block_norms(matrix, space)
    nonzero = [value for value in norms.values() if value > 0.0]
    if not nonzero:
        return norms
    spread = max(nonzero) / min(nonzero)
    logger.debug("diagonal block norms: %s (spread %.3g)", norms, spread)
    if spread > threshold:
        logger.warning(
            "diagonal Jacobian block norms span a factor of %.3g (%s); NUM-10 asks for O(1) "
            "blocks, so check the nondimensionalisation before trusting the factorisation",
            spread,
            norms,
        )
    return norms


def _component_ranges(space: FESpace) -> dict[str, tuple[int, int]]:
    """Return the degree-of-freedom range of each component of a compound space.

    ``FESpace.components`` *raises* on a non-compound space rather than being
    absent, so ``getattr(space, "components", None)`` does not protect against
    it: the default only applies when the attribute is missing, not when the
    property itself throws.
    """
    try:
        components = space.components
    except Exception:
        return {"field": (0, space.ndof)}
    if not components:
        return {"field": (0, space.ndof)}
    ranges = {}
    for index in range(len(components)):
        dof_range = space.Range(index)
        ranges[f"field_{index}"] = (int(dof_range.start), int(dof_range.stop))
    return ranges


def mesh_size_report(mesh: Mesh) -> str:
    """Return a one-line description of a mesh, for logs and diagnostics."""
    return f"{mesh.ne} elements, {mesh.nv} vertices, materials {mesh.GetMaterials()}"
