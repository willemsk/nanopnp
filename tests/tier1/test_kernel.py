"""The kernel: one integral a slot, a term's own slots, one statement every reader (VER-81)."""

from __future__ import annotations

import ngsolve as ngs
import numpy as np
import pytest

from nanopnp.core.typing import Expression
from nanopnp.materials.electrolyte import Electrolyte
from nanopnp.mesh.primitives import CylinderGeometry
from nanopnp.numerics.measures import AXISYMMETRIC
from nanopnp.physics import kernel
from nanopnp.physics.backend import NGSOLVE_OPERATORS, geometry_of
from nanopnp.physics.coefficients import (
    SATURATED_WALL_DISTANCE_NM,
    NondimensionalCoefficients,
    mesh_unit_scales,
)
from nanopnp.physics.nernst_planck import ConcentrationVariables
from nanopnp.physics.stabilisation import create as create_stabilisation

FLUID = "electrolyte"
ROUND_OFF = 1.0e-12
OPS = NGSOLVE_OPERATORS


@pytest.fixture(scope="module")
def mesh() -> ngs.Mesh:
    return CylinderGeometry(radius_nm=2.0, length_nm=4.0).generate(maxh_nm=0.4)


def _applied(space: ngs.FESpace, integral: object, state: ngs.GridFunction) -> np.ndarray:
    form = ngs.BilinearForm(space)
    form += integral
    out = state.vec.CreateVector()
    form.Apply(state.vec, out)
    return np.array(out.FV().NumPy())


def _relative(new: np.ndarray, old: np.ndarray) -> float:
    return float(np.max(np.abs(new - old)) / np.max(np.abs(old)))


def _hand_context(mesh: ngs.Mesh, space: ngs.FESpace) -> kernel.Context:
    potential, concentration = space.TrialFunction()
    potential_test, concentration_test = space.TestFunction()
    variables = ConcentrationVariables(
        values={"s": concentration},
        gradients={"s": ngs.grad(concentration)},
        variables={"s": concentration},
    )
    electrolyte = Electrolyte.from_parameter_file()
    coefficients = NondimensionalCoefficients(
        electrolyte=electrolyte,
        scales=mesh_unit_scales(electrolyte, 0.1),
        concentrations={ion.name: concentration for ion in electrolyte.species},
        wall_distance_nm=SATURATED_WALL_DISTANCE_NM,
    )
    side = kernel.Side(
        functions={"phi": potential, "c": concentration},
        variables=variables,
        coefficients=coefficients,
    )
    return kernel.Context(
        ops=OPS,
        geometry=geometry_of(mesh, AXISYMMETRIC),
        measures=AXISYMMETRIC,
        fluid=mesh.Materials(FLUID),
        trial=side,
        lagged=side,
        tests={"phi": potential_test, "c": concentration_test},
        inputs=kernel.Inputs(),
        steric=None,
        stabilisation=create_stabilisation("none"),
    )


def _diffusion(context: kernel.Context) -> Expression:
    return OPS.grad(context.trial.functions["c"])


def _drift(context: kernel.Context, side: kernel.Side, species: str) -> Expression:
    del context, species
    return OPS.grad(side.functions["phi"])


def _negated_flux(total: Expression, context: kernel.Context) -> Expression:
    return -OPS.dot(total, OPS.grad(context.tests["c"]))


def test_ver81_one_slot_is_one_integral_where_term_by_term_moves_the_rule(
    mesh: ngs.Mesh,
) -> None:
    space = ngs.H1(mesh, order=2) * ngs.H1(mesh, order=2, definedon=mesh.Materials(FLUID))
    state = ngs.GridFunction(space)
    state.components[0].Set(0.3 * ngs.sin(0.7 * ngs.y) * (1.0 + 0.1 * ngs.x * ngs.x))
    state.components[1].Set(1.0 + 0.2 * ngs.cos(0.5 * ngs.y) * (1.0 - 0.05 * ngs.x * ngs.x))
    context = _hand_context(mesh, space)
    diffusion = kernel.KernelTerm(
        "diffusion", "PHY-04", contributions=(kernel.Contribution(kernel.FLUX, _diffusion),)
    )
    drift = kernel.KernelTerm("drift", "PHY-04", drift=_drift)
    slot = kernel.Slot(kernel.FLUX, "c", "fluid", _negated_flux, species="s")

    potential, concentration = space.TrialFunction()
    _, test = space.TestFunction()
    written = (
        -ngs.InnerProduct(
            ngs.grad(concentration) + concentration * ngs.grad(potential), ngs.grad(test)
        )
        * ngs.x
        * ngs.dx(definedon=mesh.Materials(FLUID))
    )
    reference = _applied(space, written, state)

    composed = _applied(space, kernel.compose((diffusion, drift), (slot,), context), state)
    apart = _applied(space, kernel.compose((diffusion,), (slot,), context), state) + _applied(
        space, kernel.compose((drift,), (slot,), context), state
    )
    assert _relative(composed, reference) <= ROUND_OFF
    assert _relative(apart, reference) > 1.0e-6
