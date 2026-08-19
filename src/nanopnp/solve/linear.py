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
"""

from __future__ import annotations

from nanopnp.core.typing import Expression, GridFunction, Mesh

DEFAULT_SOLVER = "umfpack"
"""Direct solver used unless a case says otherwise."""

_REJECTED = {
    "sparsecholesky": (
        "sparsecholesky is SPD-only and cannot factorise the unsymmetric coupled system (NUM-21)"
    ),
    "pardiso": "PARDISO is absent from the NGSolve wheel; the reference model's solver is "
    "unavailable on the default path (NUM-21)",
    "mumps": "MUMPS is absent from the NGSolve wheel and needs a source build with MPI (NUM-21)",
}


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
    if name == "superlu":
        raise NotImplementedError(
            "the scipy SuperLU path is the BSD-licensed fallback of CON-08/CON-11 and is not "
            "wired up yet; use umfpack"
        )
    if name != "umfpack":
        raise ValueError(f"unknown linear solver {name!r}; this build offers umfpack")
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
    check_solver(solver)
    space = solution.space
    residual = linear.vec.CreateVector()
    residual.data = linear.vec - bilinear.mat * solution.vec
    inverse = bilinear.mat.Inverse(space.FreeDofs(), inverse=solver)
    solution.vec.data += inverse * residual


def mesh_size_report(mesh: Mesh) -> str:
    """Return a one-line description of a mesh, for logs and diagnostics."""
    return f"{mesh.ne} elements, {mesh.nv} vertices, materials {mesh.GetMaterials()}"
