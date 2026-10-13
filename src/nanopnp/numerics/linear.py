"""Direct linear solves and block-scaling diagnostics (NUM-10, NUM-21)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol, TypeAlias

if TYPE_CHECKING:
    import numpy as np
    from scipy.sparse import csr_matrix

from nanopnp.core.typing import Expression, FESpace, GridFunction, Mesh, Option

logger = logging.getLogger(__name__)

DEFAULT_SOLVER = "umfpack"

BLOCK_SCALING_WARNING = 1.0e3

_REJECTED = {
    "sparsecholesky": (
        "sparsecholesky is SPD-only and cannot factorise the unsymmetric coupled system (NUM-21)"
    ),
    "pardiso": "PARDISO is absent from the NGSolve wheel; the reference model's solver is "
    "unavailable on the default path (NUM-21)",
    "mumps": "MUMPS is absent from the NGSolve wheel and needs a source build with MPI (NUM-21)",
}


class LinearSolver(Protocol):
    name: str

    def solve(
        self,
        matrix: Expression,
        rhs: Expression,
        correction: Expression,
        freedofs: Option,
    ) -> None:
        ...
        ...


class UmfpackSolver:
    name: str = "umfpack"

    def solve(
        self,
        matrix: Expression,
        rhs: Expression,
        correction: Expression,
        freedofs: Option,
    ) -> None:
        correction.data = matrix.Inverse(freedofs, inverse=self.name) * rhs


class SuperluSolver:
    name: str = "superlu"

    def solve(
        self,
        matrix: Expression,
        rhs: Expression,
        correction: Expression,
        freedofs: Option,
    ) -> None:
        correction.FV().NumPy()[:] = solve_superlu(matrix, rhs, freedofs)


SolverBuilder: TypeAlias = Callable[[], LinearSolver]

_REGISTRY: dict[str, SolverBuilder] = {}


def register_solver(name: str, builder: SolverBuilder) -> None:
    if name == "sparsecholesky":
        raise ValueError(
            f"linear solver 'sparsecholesky' cannot be registered: {_REJECTED['sparsecholesky']}"
        )
    if name in _REGISTRY:
        raise ValueError(f"linear solver {name!r} is already registered")
    _REGISTRY[name] = builder


def registered_solvers() -> tuple[str, ...]:
    return tuple(sorted(_REGISTRY))


def create_solver(name: str) -> LinearSolver:
    try:
        builder = _REGISTRY[name]
    except KeyError:
        known = ", ".join(registered_solvers())
        raise KeyError(f"unknown linear solver {name!r}; registered solvers are {known}") from None
    return builder()


register_solver("umfpack", UmfpackSolver)
register_solver("superlu", SuperluSolver)


def rejection(name: str) -> str | None:
    return None if name in _REGISTRY else _REJECTED.get(name)


def check_solver(name: str) -> str:
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
    check_solver(solver)
    create_solver(solver).solve(matrix, rhs, correction, freedofs)


def to_scipy(matrix: Expression) -> csr_matrix:
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
    system = to_scipy(matrix)
    ranges = _component_ranges(space)
    norms: dict[str, float] = {}
    for name, (start, stop) in ranges.items():
        # abs() the block, not the matrix: blocks are a small part of a 6e7-nonzero Jacobian.
        block = abs(system[start:stop, start:stop])
        norms[name] = float(block.sum(axis=1).max()) if block.nnz else 0.0
    return norms


def field_row_scaling(matrix: Expression, space: FESpace) -> dict[str, float]:
    return {
        name: (1.0 / norm if norm > 0.0 else 1.0)
        for name, norm in diagonal_block_norms(matrix, space).items()
    }


def report_block_scaling(
    matrix: Expression, space: FESpace, *, threshold: float = BLOCK_SCALING_WARNING
) -> dict[str, float]:
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
    return f"{mesh.ne} elements, {mesh.nv} vertices, materials {mesh.GetMaterials()}"
