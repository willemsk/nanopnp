"""VER-17 (with NUM-09, NUM-27 and PHY-21): Maxwell-Hall access conductance of an uncharged pore."""

import logging
import math

import pytest

from nanopnp.core.constants import FARADAY
from nanopnp.materials.electrolyte import Electrolyte
from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.numerics.measures import AXISYMMETRIC
from nanopnp.physics import models
from nanopnp.post import qoi
from nanopnp.post.indicator import axial_indicator, lumen_band

logger = logging.getLogger(__name__)

PORE_RADIUS_NM = 2.0
MEMBRANE_THICKNESS_NM = 13.0
CONCENTRATION_M = 1.0
BIAS_V = 0.025

# QR-01, VER-17
TOLERANCE = 0.02

RESERVOIR_RADII_NM = (50.0, 100.0)

MEMBRANE_PERMITTIVITY = {"membrane": 2.0}


# PHY-14, VER-05
def bulk_conductivity_S_m(electrolyte: Electrolyte, concentration_M: float) -> float:
    concentration_mol_m3 = concentration_M * 1.0e3
    return FARADAY * math.fsum(
        ion.valence**2 * ion.mobility_0 * concentration_mol_m3 for ion in electrolyte.species
    )


def maxwell_hall_conductance_S(
    conductivity_S_m: float, *, radius_nm: float, length_nm: float
) -> float:
    radius_m = radius_nm * 1e-9
    length_m = length_nm * 1e-9
    resistance = length_m / (math.pi * radius_m**2) + 1.0 / (2.0 * radius_m)
    return conductivity_S_m / resistance


def _solve(reservoir_radius_nm: float) -> float:
    pore = CylindricalPoreGeometry(
        pore_radius_nm=PORE_RADIUS_NM,
        membrane_thickness_nm=MEMBRANE_THICKNESS_NM,
        reservoir_radius_nm=reservoir_radius_nm,
    )
    model = models.create(
        "pnp",
        classical=True,
        concentration_M=CONCENTRATION_M,
        solid_permittivities=MEMBRANE_PERMITTIVITY,
    )
    # Uncharged, so no double layer needs wall grading; the refinement goes to the
    # mouth, where the access resistance is set.
    mesh = pore.generate(maxh_nm=reservoir_radius_nm / 12.0, wall_h_nm=0.5)
    bias_tilde = BIAS_V / model.scales.potential_V
    solution = model.solve(
        mesh,
        AXISYMMETRIC,
        potential_values=mesh.BoundaryCF({"cis": 0.0, "trans": bias_tilde}),
    )
    lower, upper = lumen_band(pore)
    indicator = axial_indicator(mesh, lower_nm=lower, upper_nm=upper)
    quantities = qoi.extract(solution, AXISYMMETRIC, indicator, bias_V=BIAS_V)
    logger.info(
        "R = %.0f nm: %d elements, %d dof, I = %.6e A, G = %.6e S, t+ = %.4f, routes agree to %.2e",
        reservoir_radius_nm,
        mesh.ne,
        solution.space.ndof,
        quantities.current_A,
        quantities.conductance_S,
        quantities.transport_number,
        quantities.agreement.relative_difference if quantities.agreement else float("nan"),
    )
    return quantities.conductance_S


@pytest.fixture(scope="module")
def conductances() -> dict[float, float]:
    return {radius: _solve(radius) for radius in RESERVOIR_RADII_NM}


@pytest.fixture(scope="module")
def analytic_S() -> float:
    electrolyte = Electrolyte.from_parameter_file()
    conductivity = bulk_conductivity_S_m(electrolyte, CONCENTRATION_M)
    analytic = maxwell_hall_conductance_S(
        conductivity, radius_nm=PORE_RADIUS_NM, length_nm=MEMBRANE_THICKNESS_NM
    )
    logger.info("sigma = %.4f S/m, Maxwell-Hall G = %.6e S", conductivity, analytic)
    return analytic


# QR-01
@pytest.mark.parametrize("radius_nm", RESERVOIR_RADII_NM)
def test_ver17_access_conductance_matches_maxwell_hall(
    conductances: dict[float, float], analytic_S: float, radius_nm: float
) -> None:
    measured = conductances[radius_nm]
    error = abs(measured - analytic_S) / analytic_S
    logger.info(
        "R = %.0f nm: G = %.6e S against %.6e S, %.2f %%",
        radius_nm,
        measured,
        analytic_S,
        100.0 * error,
    )
    assert measured > 0.0, (
        "an ohmic pore has a positive conductance; a negative one means the current "
        "is referenced to the wrong electrode or psi runs the wrong way"
    )
    assert error < TOLERANCE, (
        f"G = {measured:.6e} S against the Maxwell-Hall {analytic_S:.6e} S, an error of "
        f"{100.0 * error:.2f} % against a tolerance of {100.0 * TOLERANCE:.0f} %"
    )


def test_ver17_the_model_s_own_bulk_conductivity_of_1_m_nacl_is_12_6_s_per_m() -> None:
    sigma0 = bulk_conductivity_S_m(Electrolyte.from_parameter_file(), CONCENTRATION_M)
    assert sigma0 == pytest.approx(12.6, abs=0.05)


def test_ver17_the_finite_reservoir_is_not_what_the_benchmark_measures(
    conductances: dict[float, float],
) -> None:
    small, large = (conductances[radius] for radius in RESERVOIR_RADII_NM)
    drift = abs(large - small) / large
    logger.info(
        "G moves by %.3f %% between R = %.0f nm and R = %.0f nm",
        100.0 * drift,
        *RESERVOIR_RADII_NM,
    )
    assert drift < 0.5 * TOLERANCE, (
        f"G moved {100.0 * drift:.2f} % when the reservoir doubled, which is not small "
        f"against the {100.0 * TOLERANCE:.0f} % this benchmark asserts"
    )


def test_ver17_the_access_term_is_a_fifth_of_the_resistance_and_carries_the_factor_two() -> None:
    radius_m = PORE_RADIUS_NM * 1e-9
    diameter_m = 2.0 * radius_m
    length_m = MEMBRANE_THICKNESS_NM * 1e-9

    by_radius = length_m / (math.pi * radius_m**2) + 1.0 / (2.0 * radius_m)
    by_diameter = 4.0 * length_m / (math.pi * diameter_m**2) + 1.0 / diameter_m
    assert by_radius == pytest.approx(by_diameter, rel=1e-12)

    access_share = (1.0 / (2.0 * radius_m)) / by_radius
    assert access_share == pytest.approx(0.195, abs=0.005)

    wrong = length_m / (math.pi * radius_m**2) + 1.0 / radius_m
    assert abs(by_radius / wrong - 1.0) > 0.15, (
        "the 1/a variant must be far enough out to be caught by a 2 % tolerance"
    )
