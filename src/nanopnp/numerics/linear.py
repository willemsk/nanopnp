"""Direct linear solves (NUM-10, NUM-21)."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol, TypeAlias

if TYPE_CHECKING:
    import numpy as np
    from scipy.sparse import csr_matrix

from nanopnp.core.typing import Expression, GridFunction, Mesh, Option

DEFAULT_SOLVER = "umfpack"

_REJECTED = {
    "sparsecholesky": (
        "sparsecholesky is SPD-only and cannot factorise the unsymmetric coupled system (NUM-21)"
    ),
    "pardiso": "PARDISO is absent from the NGSolve wheel; the reference model's solver is "
    "unavailable on the default path (NUM-21)",
    "mumps": "MUMPS is absent from the NGSolve wheel and needs a source build with MPI (NUM-21)",
}


class LinearSolver(Protocol):
    """Direct linear solver on the free degrees of freedom."""

    name: str

    def solve(
        self,
        matrix: Expression,
        rhs: Expression,
        correction: Expression,
        freedofs: Option,
    ) -> None:
        """Solve ``matrix @ correction = rhs`` on the free degrees of freedom, in place."""
        ...
        ...


class UmfpackSolver:
    """UMFPACK sparse direct solver."""

    name: str = "umfpack"

    def solve(
        self,
        matrix: Expression,
        rhs: Expression,
        correction: Expression,
        freedofs: Option,
    ) -> None:
        """Solve a linear system in place with NGSolve's UMFPACK wrapper."""
        correction.data = matrix.Inverse(freedofs, inverse=self.name) * rhs


class SuperluSolver:
    """Scipy SuperLU sparse direct solver."""

    name: str = "superlu"

    def solve(
        self,
        matrix: Expression,
        rhs: Expression,
        correction: Expression,
        freedofs: Option,
    ) -> None:
        """Solve a linear system in place with SciPy's SuperLU wrapper."""
        correction.FV().NumPy()[:] = solve_superlu(matrix, rhs, freedofs)


SolverBuilder: TypeAlias = Callable[[], LinearSolver]

_REGISTRY: dict[str, SolverBuilder] = {}


def register_solver(name: str, builder: SolverBuilder) -> None:
    """Register a linear solver under ``name``; ValueError if rejected or taken."""
    if name == "sparsecholesky":
        raise ValueError(
            f"linear solver 'sparsecholesky' cannot be registered: {_REJECTED['sparsecholesky']}"
        )
    if name in _REGISTRY:
        raise ValueError(f"linear solver {name!r} is already registered")
    _REGISTRY[name] = builder


def registered_solvers() -> tuple[str, ...]:
    """Return every selectable solver name, sorted."""
    return tuple(sorted(_REGISTRY))


def create_solver(name: str) -> LinearSolver:
    """Build the linear solver registered as ``name``; KeyError if none is."""
    try:
        builder = _REGISTRY[name]
    except KeyError:
        known = ", ".join(registered_solvers())
        raise KeyError(f"unknown linear solver {name!r}; registered solvers are {known}") from None
    return builder()


register_solver("umfpack", UmfpackSolver)
register_solver("superlu", SuperluSolver)


def rejection(name: str) -> str | None:
    """Return the reason for refusing an unregistered ``name``, or None."""
    return None if name in _REGISTRY else _REJECTED.get(name)


def check_solver(name: str) -> str:
    """Return ``name`` if usable on this build; otherwise ValueError saying why."""
    if name in _REGISTRY:
        return name
    reason = rejection(name)
    if reason is not None:
        raise ValueError(f"linear solver {name!r} is not usable: {reason}")
    known = list(registered_solvers())
    raise ValueError(f"unknown linear solver {name!r}; this build offers {known}")


def solve_linear(
    bilinear: Expression,
    linear: Expression,
    solution: GridFunction,
    *,
    solver: str = DEFAULT_SOLVER,
) -> None:
    """Solve one assembled linear variational problem in place, keeping its Dirichlet data."""
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
    """Solve ``matrix @ correction = rhs`` on the free degrees of freedom, in place."""
    check_solver(solver)
    create_solver(solver).solve(matrix, rhs, correction, freedofs)


def to_scipy(matrix: Expression) -> csr_matrix:
    """Return an assembled NGSolve sparse matrix as a scipy CSR matrix."""
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

    Parameters
    ----------
    equilibrate
        Divide each row by its largest magnitude before factorising.
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


def mesh_size_report(mesh: Mesh) -> str:
    """Return a one-line description of a mesh, for logs and diagnostics."""
    return f"{mesh.ne} elements, {mesh.nv} vertices, materials {mesh.GetMaterials()}"
