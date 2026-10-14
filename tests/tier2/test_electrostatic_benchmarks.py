"""VER-12 and VER-13 (with NUM-06, NUM-25): Poisson-Boltzmann against closed forms."""

import math
from itertools import pairwise

import ngsolve as ngs
import numpy as np
import pytest
from scipy.special import i0

from nanopnp.core.constants import (
    GAS_CONSTANT,
    REFERENCE_TEMPERATURE_K,
    VACUUM_PERMITTIVITY,
    thermal_voltage,
)
from nanopnp.mesh.primitives import CylinderGeometry, SlabGeometry
from nanopnp.numerics.measures import AXISYMMETRIC, PLANAR
from nanopnp.physics.pb import (
    ELECTROLYTE_PERMITTIVITY,
    debye_length_nm,
    nonlinear_pb_residual,
    solve_pb,
)
from nanopnp.post.reaction_flux import boundary_reaction_flux


def _weighted_error(
    solution: ngs.GridFunction,
    exact: "np.ndarray",
    points: "np.ndarray",
    weights: "np.ndarray",
    mesh: ngs.Mesh,
    z: float,
) -> float:
    computed = np.array([solution(mesh(float(r), z)) for r in points])
    error = math.sqrt(float(np.sum(weights * (computed - exact) ** 2)))
    scale = math.sqrt(float(np.sum(weights * exact**2)))
    return error / scale


def test_ver13_debye_huckel_in_a_cylinder() -> None:
    radius, length, lam, zeta = 2.0, 4.0, 0.5, 1.0
    samples = np.linspace(0.0, radius, 201)
    exact = zeta * i0(samples / lam) / i0(radius / lam)
    weights = np.maximum(samples, 1e-12)  # the r weight of the axisymmetric L2 norm

    errors = []
    for maxh in (0.4, 0.2, 0.1):
        mesh = CylinderGeometry(radius_nm=radius, length_nm=length).generate(maxh_nm=maxh)
        solution = solve_pb(
            mesh,
            AXISYMMETRIC,
            debye_length_nm=lam,
            dirichlet="wall",
            boundary_values=ngs.CF(zeta),
            nonlinear=False,
        )
        errors.append(_weighted_error(solution, exact, samples, weights, mesh, 0.5 * length))

    assert errors[-1] < 5e-5, f"finest-mesh error {errors[-1]:.3g} is too large"
    rates = [math.log2(coarse / fine) for coarse, fine in pairwise(errors)]
    assert min(rates) > 2.5, f"observed convergence rates {rates} fall short of P2"


# NUM-06
def test_ver13_axis_condition_is_natural_not_dirichlet() -> None:
    radius, lam, zeta = 2.0, 0.5, 1.0
    mesh = CylinderGeometry(radius_nm=radius, length_nm=4.0).generate(maxh_nm=0.1)
    natural = solve_pb(
        mesh,
        AXISYMMETRIC,
        debye_length_nm=lam,
        dirichlet="wall",
        boundary_values=ngs.CF(zeta),
        nonlinear=False,
    )
    pinned = solve_pb(
        mesh,
        AXISYMMETRIC,
        debye_length_nm=lam,
        dirichlet="wall|axis",
        boundary_values=mesh.BoundaryCF({"wall": zeta, "axis": 0.0}),
        nonlinear=False,
    )
    exact_centre = zeta * i0(0.0) / i0(radius / lam)
    assert natural(mesh(0.0, 2.0)) == pytest.approx(exact_centre, rel=1e-3)
    assert pinned(mesh(0.0, 2.0)) == pytest.approx(0.0, abs=1e-12)


def test_ver12_gouy_chapman_profile() -> None:
    concentration_M = 0.1
    lam = debye_length_nm(concentration_M)
    width, zeta = 20.0 * lam, 2.0
    samples = np.linspace(0.0, width, 401)
    exact = 4.0 * np.arctanh(math.tanh(0.25 * zeta) * np.exp(-samples / lam))
    weights = np.ones_like(samples)

    errors = []
    for maxh in (lam / 2.0, lam / 4.0, lam / 8.0):
        mesh = SlabGeometry(width_nm=width, height_nm=lam).generate(maxh_nm=maxh)
        solution = solve_pb(
            mesh,
            PLANAR,
            debye_length_nm=lam,
            dirichlet="wall|bulk",
            boundary_values=mesh.BoundaryCF({"wall": zeta, "bulk": 0.0}),
            nonlinear=True,
        )
        errors.append(_weighted_error(solution, exact, samples, weights, mesh, 0.5 * lam))

    assert errors[-1] < 1e-5, f"finest-mesh error {errors[-1]:.3g} is too large"
    rates = [math.log2(coarse / fine) for coarse, fine in pairwise(errors)]
    assert min(rates) > 2.5, f"observed convergence rates {rates} fall short of P2"


# NUM-25
def test_ver12_grahame_surface_charge() -> None:
    concentration_M, zeta = 0.1, 2.0
    lam = debye_length_nm(concentration_M)
    height_nm = lam
    mesh = SlabGeometry(width_nm=20.0 * lam, height_nm=height_nm).generate(maxh_nm=lam / 8.0)
    solution = solve_pb(
        mesh,
        PLANAR,
        debye_length_nm=lam,
        dirichlet="wall|bulk",
        boundary_values=mesh.BoundaryCF({"wall": zeta, "bulk": 0.0}),
        nonlinear=True,
    )

    # The reaction flux needs the residual form on the space the solve used,
    # which solve_pb owns; it is rebuilt here from the same term rather than
    # duplicating the driver, so the damped Newton replaces it in one place.
    space = solution.space
    trial, test = space.TnT()
    residual = ngs.BilinearForm(space)
    residual += nonlinear_pb_residual(trial, test, PLANAR, debye_length_nm=lam)

    permittivity = VACUUM_PERMITTIVITY * ELECTROLYTE_PERMITTIVITY
    concentration_SI = concentration_M * 1e3
    grahame = math.sqrt(
        8.0 * permittivity * GAS_CONSTANT * REFERENCE_TEMPERATURE_K * concentration_SI
    ) * math.sinh(0.5 * zeta)

    # The reaction flux is int_wall (grad phi~ . n) ds with n pointing out of
    # the electrolyte; sigma_s = -eps dphi/dx at the wall, and the field is in
    # V_T and nm, so both scales come back in here. The PB residual has no
    # right-hand side, so no load form is passed.
    flux = boundary_reaction_flux(residual, solution, "wall")
    computed = permittivity * thermal_voltage() * (flux / height_nm) * 1e9

    assert computed == pytest.approx(grahame, rel=1e-4)
    assert computed > 0.0, "a positive wall potential implies a positive surface charge"
