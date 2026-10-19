"""Direct linear solvers and the CON-11 fallback."""

from __future__ import annotations

import ngsolve as ngs
import numpy as np
import pytest

from nanopnp.mesh.primitives import SlabGeometry
from nanopnp.numerics.linear import (
    check_solver,
    create_solver,
    register_solver,
    registered_solvers,
    solve_superlu,
    to_scipy,
)
from nanopnp.numerics.measures import PLANAR
from nanopnp.physics.pb import debye_length_nm, solve_pb_recorded

CONCENTRATION_M = 0.1
"""Bulk concentration of the test problem, in mol/L."""


@pytest.fixture
def slab() -> ngs.Mesh:
    screening_nm = debye_length_nm(CONCENTRATION_M)
    return SlabGeometry(width_nm=8.0 * screening_nm).generate(maxh_nm=screening_nm / 3.0)


@pytest.mark.parametrize(
    ("name", "reason"),
    [
        ("sparsecholesky", "SPD-only"),
        ("pardiso", "absent from the NGSolve wheel"),
        ("mumps", "absent from the NGSolve wheel"),
    ],
)
def test_num21_unusable_solvers_are_rejected_with_a_reason(name: str, reason: str) -> None:
    with pytest.raises(ValueError) as caught:
        check_solver(name)
    assert reason in str(caught.value)


def test_num21_unknown_solver_lists_the_alternatives() -> None:
    with pytest.raises(ValueError, match="umfpack"):
        check_solver("superlu_dist")


# CON-11
def test_num21_both_licensed_paths_are_available() -> None:
    assert registered_solvers() == ("superlu", "umfpack")
    assert check_solver("umfpack") == "umfpack"
    assert check_solver("superlu") == "superlu"


def test_num21_register_solver_rejects_sparsecholesky() -> None:
    class Dummy:
        name = "sparsecholesky"

        def solve(self, matrix: object, rhs: object, correction: object, freedofs: object) -> None:
            pass

    with pytest.raises(ValueError, match="NUM-21") as caught:
        register_solver("sparsecholesky", Dummy)
    assert "cannot be registered" in str(caught.value)
    assert "sparsecholesky" in str(caught.value)


def test_num21_register_solver_rejects_duplicate() -> None:
    class Dummy:
        name = "umfpack"

        def solve(self, matrix: object, rhs: object, correction: object, freedofs: object) -> None:
            pass

    with pytest.raises(ValueError, match="already registered"):
        register_solver("umfpack", Dummy)


def test_num21_create_solver_unknown_raises_key_error() -> None:
    with pytest.raises(KeyError, match="registered solvers are superlu, umfpack"):
        create_solver("nonexistent")


def test_num21_pardiso_and_mumps_may_be_registered() -> None:
    class Dummy:
        name = "mumps"

        def solve(self, matrix: object, rhs: object, correction: object, freedofs: object) -> None:
            pass

    try:
        register_solver("mumps", Dummy)
        assert "mumps" in registered_solvers()
        assert check_solver("mumps") == "mumps"
    finally:
        from nanopnp.numerics.linear import _REGISTRY

        _REGISTRY.pop("mumps", None)


def test_con11_superlu_agrees_with_umfpack(slab: ngs.Mesh) -> None:
    screening_nm = debye_length_nm(CONCENTRATION_M)
    arguments = {
        "debye_length_nm": screening_nm,
        "dirichlet": "wall",
        "boundary_values": ngs.CF(1.0),
        "nonlinear": False,
    }
    umfpack = solve_pb_recorded(slab, PLANAR, solver="umfpack", **arguments)[0]
    superlu = solve_pb_recorded(slab, PLANAR, solver="superlu", **arguments)[0]

    difference = np.abs(
        np.asarray(umfpack.vec.FV().NumPy()) - np.asarray(superlu.vec.FV().NumPy())
    ).max()
    assert difference < 1e-12


# NUM-10
def test_con11_superlu_agrees_with_umfpack_through_newton_too(slab: ngs.Mesh) -> None:
    screening_nm = debye_length_nm(CONCENTRATION_M)
    arguments = {
        "debye_length_nm": screening_nm,
        "dirichlet": "wall|bulk",
        "boundary_values": slab.BoundaryCF({"wall": 2.0, "bulk": 0.0}),
        "nonlinear": True,
    }
    umfpack = solve_pb_recorded(slab, PLANAR, solver="umfpack", **arguments)[0]
    superlu = solve_pb_recorded(slab, PLANAR, solver="superlu", **arguments)[0]

    difference = np.abs(
        np.asarray(umfpack.vec.FV().NumPy()) - np.asarray(superlu.vec.FV().NumPy())
    ).max()
    assert difference < 1e-10


def test_superlu_returns_zero_on_the_constrained_degrees_of_freedom(slab: ngs.Mesh) -> None:
    space = ngs.H1(slab, order=1, dirichlet="wall")
    trial, test = space.TnT()
    matrix = ngs.BilinearForm(ngs.grad(trial) * ngs.grad(test) * ngs.dx).Assemble()
    rhs = ngs.LinearForm(test * ngs.dx).Assemble()

    correction = solve_superlu(matrix.mat, rhs.vec, space.FreeDofs())

    constrained = ~np.asarray(list(space.FreeDofs()), dtype=bool)
    assert np.all(correction[constrained] == 0.0)
    assert np.any(correction != 0.0)


# NUM-10
def test_superlu_equilibration_does_not_change_the_answer(slab: ngs.Mesh) -> None:
    space = ngs.H1(slab, order=1, dirichlet="wall")
    trial, test = space.TnT()
    matrix = ngs.BilinearForm(1e6 * ngs.grad(trial) * ngs.grad(test) * ngs.dx).Assemble()
    rhs = ngs.LinearForm(1e6 * test * ngs.dx).Assemble()

    scaled = solve_superlu(matrix.mat, rhs.vec, space.FreeDofs(), equilibrate=True)
    plain = solve_superlu(matrix.mat, rhs.vec, space.FreeDofs(), equilibrate=False)

    assert np.abs(scaled - plain).max() < 1e-12 * max(np.abs(plain).max(), 1.0)


def test_to_scipy_sums_duplicate_entries(slab: ngs.Mesh) -> None:
    space = ngs.H1(slab, order=1)
    trial, test = space.TnT()
    form = ngs.BilinearForm(trial * test * ngs.dx).Assemble()
    system = to_scipy(form.mat)

    vector = ngs.GridFunction(space)
    vector.Set(ngs.x)
    product = vector.vec.CreateVector()
    product.data = form.mat * vector.vec

    expected = np.asarray(product.FV().NumPy())
    assert np.abs(system @ np.asarray(vector.vec.FV().NumPy()) - expected).max() < 1e-12
