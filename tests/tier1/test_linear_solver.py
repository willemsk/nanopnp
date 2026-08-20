"""Direct linear solvers and the NUM-10 scaling diagnostic.

Three things matter here and none of them is speed. That the solvers this build
cannot use are rejected with a reason rather than failing obscurely inside
NGSolve; that the BSD-licensed SuperLU fallback of CON-08/CON-11 gives the same
answer as UMFPACK, so the licensing choice is not also a numerical one; and that
a badly scaled block system is *noticed*, because a direct solver will factorise
one without complaint and quietly return fewer digits than the tolerance assumes.
"""

from __future__ import annotations

import logging

import ngsolve as ngs
import numpy as np
import pytest

from nanopnp.mesh.primitives import SlabGeometry
from nanopnp.physics.measures import PLANAR
from nanopnp.physics.pb import debye_length_nm, solve_pb
from nanopnp.solve.linear import (
    AVAILABLE_SOLVERS,
    check_solver,
    diagonal_block_norms,
    field_row_scaling,
    report_block_scaling,
    solve_superlu,
    to_scipy,
)

CONCENTRATION_M = 0.1
"""Bulk concentration of the test problem, in mol/L."""


@pytest.fixture
def slab() -> ngs.Mesh:
    """Return a planar slab meshed to resolve the double layer."""
    screening_nm = debye_length_nm(CONCENTRATION_M)
    return SlabGeometry(width_nm=8.0 * screening_nm).generate(maxh_nm=screening_nm / 3.0)


def _mixed_space(mesh: ngs.Mesh) -> ngs.FESpace:
    """Return a two-field compound space, standing in for the coupled system."""
    return ngs.FESpace([ngs.H1(mesh, order=2, dirichlet="wall"), ngs.H1(mesh, order=1)])


@pytest.mark.parametrize(
    ("name", "reason"),
    [
        ("sparsecholesky", "SPD-only"),
        ("pardiso", "absent from the NGSolve wheel"),
        ("mumps", "absent from the NGSolve wheel"),
    ],
)
def test_num21_unusable_solvers_are_rejected_with_a_reason(name: str, reason: str) -> None:
    """A solver this build cannot use fails at the call site, saying why (NUM-21)."""
    with pytest.raises(ValueError) as caught:
        check_solver(name)
    assert reason in str(caught.value)


def test_num21_unknown_solver_lists_the_alternatives() -> None:
    """A typo names what was available instead of failing inside NGSolve."""
    with pytest.raises(ValueError, match="umfpack"):
        check_solver("superlu_dist")


def test_num21_both_licensed_paths_are_available() -> None:
    """UMFPACK (GPL-2+) and SuperLU (BSD) are both usable; CON-11 needs the second."""
    assert {"umfpack", "superlu"} == AVAILABLE_SOLVERS
    assert check_solver("umfpack") == "umfpack"
    assert check_solver("superlu") == "superlu"


def test_con11_superlu_agrees_with_umfpack(slab: ngs.Mesh) -> None:
    """The BSD fallback is a licensing choice, not a numerical one.

    Both factorise the same Debye-Hueckel system; agreement at round-off is what
    lets a redistributable bundle drop the copyleft dependency without any
    caveat about results.
    """
    screening_nm = debye_length_nm(CONCENTRATION_M)
    arguments = {
        "debye_length_nm": screening_nm,
        "dirichlet": "wall",
        "boundary_values": ngs.CF(1.0),
        "nonlinear": False,
    }
    umfpack = solve_pb(slab, PLANAR, solver="umfpack", **arguments)
    superlu = solve_pb(slab, PLANAR, solver="superlu", **arguments)

    difference = np.abs(
        np.asarray(umfpack.vec.FV().NumPy()) - np.asarray(superlu.vec.FV().NumPy())
    ).max()
    assert difference < 1e-12


def test_superlu_returns_zero_on_the_constrained_degrees_of_freedom(slab: ngs.Mesh) -> None:
    """Constrained rows are dropped, not zeroed, so the correction leaves them alone."""
    space = ngs.H1(slab, order=1, dirichlet="wall")
    trial, test = space.TnT()
    matrix = ngs.BilinearForm(ngs.grad(trial) * ngs.grad(test) * ngs.dx).Assemble()
    rhs = ngs.LinearForm(test * ngs.dx).Assemble()

    correction = solve_superlu(matrix.mat, rhs.vec, space.FreeDofs())

    constrained = ~np.asarray(list(space.FreeDofs()), dtype=bool)
    assert np.all(correction[constrained] == 0.0)
    assert np.any(correction != 0.0)


def test_superlu_equilibration_does_not_change_the_answer(slab: ngs.Mesh) -> None:
    """Row equilibration (NUM-10) rescales the system, not its solution."""
    space = ngs.H1(slab, order=1, dirichlet="wall")
    trial, test = space.TnT()
    matrix = ngs.BilinearForm(1e6 * ngs.grad(trial) * ngs.grad(test) * ngs.dx).Assemble()
    rhs = ngs.LinearForm(1e6 * test * ngs.dx).Assemble()

    scaled = solve_superlu(matrix.mat, rhs.vec, space.FreeDofs(), equilibrate=True)
    plain = solve_superlu(matrix.mat, rhs.vec, space.FreeDofs(), equilibrate=False)

    assert np.abs(scaled - plain).max() < 1e-12 * max(np.abs(plain).max(), 1.0)


def test_to_scipy_sums_duplicate_entries(slab: ngs.Mesh) -> None:
    """NGSolve's COO export lists duplicates; summing them is the assembly semantics.

    Getting this wrong gives a matrix that is wrong only on the shared entries —
    which is every interior degree of freedom — so it is worth pinning against
    an independent evaluation of the same bilinear form.
    """
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


def test_num10_diagonal_block_norms_separate_the_fields(slab: ngs.Mesh) -> None:
    """Each field's block norm is measured on its own rows and columns."""
    space = _mixed_space(slab)
    (first, second), (test_first, test_second) = space.TnT()
    form = ngs.BilinearForm(space)
    form += (1e3 * ngs.grad(first) * ngs.grad(test_first) + 1e-3 * second * test_second) * ngs.dx
    form.Assemble()

    norms = diagonal_block_norms(form.mat, space)

    assert set(norms) == {"field_0", "field_1"}
    assert norms["field_0"] > norms["field_1"] * 1e6


def test_num10_row_scaling_is_the_reciprocal_of_the_block_norm(slab: ngs.Mesh) -> None:
    """The scaling factors are what would bring every diagonal block to O(1)."""
    space = _mixed_space(slab)
    (first, second), (test_first, test_second) = space.TnT()
    form = ngs.BilinearForm(space)
    form += (ngs.grad(first) * ngs.grad(test_first) + 4.0 * second * test_second) * ngs.dx
    form.Assemble()

    norms = diagonal_block_norms(form.mat, space)
    scaling = field_row_scaling(form.mat, space)

    for name, norm in norms.items():
        assert scaling[name] * norm == pytest.approx(1.0, rel=1e-12)


def test_num10_an_empty_block_is_left_unscaled(slab: ngs.Mesh) -> None:
    """A pure constraint block — the Taylor-Hood pressure diagonal — has no scale.

    Its diagonal block is empty, and the reciprocal of zero is not a scaling
    factor. Leaving it at 1 is the only defensible choice, and it must not be an
    infinity that propagates into the matrix.
    """
    space = _mixed_space(slab)
    (first, _), (test_first, _) = space.TnT()
    form = ngs.BilinearForm(space)
    form += ngs.grad(first) * ngs.grad(test_first) * ngs.dx
    form.Assemble()

    scaling = field_row_scaling(form.mat, space)

    assert scaling["field_1"] == 1.0
    assert np.isfinite(list(scaling.values())).all()


def test_num10_a_badly_scaled_system_is_reported(
    slab: ngs.Mesh, caplog: pytest.LogCaptureFixture
) -> None:
    """A large block-norm spread warns; a direct solver would not have complained."""
    space = _mixed_space(slab)
    (first, second), (test_first, test_second) = space.TnT()
    form = ngs.BilinearForm(space)
    form += (1e6 * ngs.grad(first) * ngs.grad(test_first) + 1e-6 * second * test_second) * ngs.dx
    form.Assemble()

    with caplog.at_level(logging.WARNING, logger="nanopnp.solve.linear"):
        norms = report_block_scaling(form.mat, space)

    assert "NUM-10" in caplog.text
    assert set(norms) == {"field_0", "field_1"}


def test_num10_a_well_scaled_system_is_quiet(
    slab: ngs.Mesh, caplog: pytest.LogCaptureFixture
) -> None:
    """Comparable blocks produce no warning, so the warning stays meaningful."""
    space = _mixed_space(slab)
    (first, second), (test_first, test_second) = space.TnT()
    form = ngs.BilinearForm(space)
    form += (ngs.grad(first) * ngs.grad(test_first) + second * test_second) * ngs.dx
    form.Assemble()

    with caplog.at_level(logging.WARNING, logger="nanopnp.solve.linear"):
        report_block_scaling(form.mat, space)

    assert caplog.text == ""


def test_num10_a_single_field_space_reports_one_block(slab: ngs.Mesh) -> None:
    """A non-compound space is one block, so the diagnostic works before WP4."""
    space = ngs.H1(slab, order=1)
    trial, test = space.TnT()
    form = ngs.BilinearForm(trial * test * ngs.dx).Assemble()

    assert set(diagonal_block_norms(form.mat, space)) == {"field"}
