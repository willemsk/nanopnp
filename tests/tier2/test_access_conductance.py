"""VER-17: the Maxwell-Hall access conductance of an uncharged pore, to 2 %.

    G = sigma [ L/(pi a^2) + 1/(2a) ]^-1    ==    sigma [ 4L/(pi d^2) + 1/d ]^-1

The bracket is a resistance per unit conductivity: a cylinder of length ``L`` and
radius ``a``, plus the access resistance of the two mouths, ``1/(4 sigma a)``
apiece. The two forms above are the same expression in the radius and in the
diameter, and they are written out together because the widely-copied variant
with ``1/a`` in place of ``1/(2a)`` is wrong by a factor of two in the access
term — which for this pore is 19.5 % of the total resistance and would show up as
a 16 % error in ``G``, well outside the tolerance but comfortably inside the range
where a result still looks plausible.

This is the one Tier-2 benchmark that pins an *absolute* current. VER-11 checks
that the two extraction routes agree, which they would even if both were scaled
by the same wrong constant; only a closed form catches that. So the ``2 pi`` of
the NUM-27 convention, the NUM-09 current scale ``F D_0 c_0 a``, and the sign
that makes ``G`` positive are all under test here and nowhere else.

Why this runs classical and uncharged
-------------------------------------
The closed form needs one bulk conductivity ``sigma``. With the corrections
active ``mu_i`` varies with ``<c>`` and with the distance to the wall, so there
is no single ``sigma`` for the formula to be compared against; the run is
therefore ``pnp`` with ``classical=True``, which is the registered ``none``
correction rather than a code branch (PHY-21). The pore is uncharged because a
double layer would add surface conduction that the formula does not contain — and
that economy is what makes the benchmark affordable: with no double layer there
is no ``lambda_D/5`` wall grading to pay for, and the elements can be spent on the
reservoir instead, where the access resistance actually lives.

``sigma`` is derived from the model's own mobilities rather than quoted:
``sigma = F sum_i z_i^2 mu_i^0 c_i``, the infinite-dilution conductivity, which is
what a classical run with no mobility correction actually transports. It is
12.6 S/m for 1 M NaCl here, against about 8.5 S/m measured for real 1 M brine;
the difference is the concentration correction this configuration has switched
off, and comparing against the measured value instead would be comparing two
different models.
"""

import logging
import math

import pytest

from nanopnp.core.constants import FARADAY
from nanopnp.materials.electrolyte import Electrolyte
from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.physics import models
from nanopnp.physics.measures import AXISYMMETRIC
from nanopnp.post import qoi
from nanopnp.post.indicator import axial_indicator, lumen_band

logger = logging.getLogger(__name__)

PORE_RADIUS_NM = 2.0
MEMBRANE_THICKNESS_NM = 13.0
CONCENTRATION_M = 1.0
BIAS_V = 0.025
"""Small enough that the response is ohmic, large enough to be well above the
convergence floor. The formula is a linear-response result."""

TOLERANCE = 0.02
"""QR-01 and VER-17: "better than 2 %"."""

RESERVOIR_RADII_NM = (50.0, 100.0)
"""Two reservoirs, because the closed form assumes access to infinity.

With ``a = 2 nm`` and ``L = 13 nm`` the pore term is ``L/(pi a^2) = 1.035e9 /m``
and the access term ``1/(2a) = 2.5e8 /m``, so access is 19.5 % of the total. A
finite reservoir truncates that term by of order ``a/R``, which at 50 nm is a few
per cent of 19.5 %, so about 1 % on ``G`` — inside the tolerance, but not by
enough to leave unmeasured. Running two radii turns that into a measurement: if
``G`` barely moves between them, the benchmark is testing the discretisation
rather than the truncation."""

MEMBRANE_PERMITTIVITY = {"membrane": 2.0}
"""An insulating membrane, as the closed form assumes. Not a fitted parameter:
Maxwell-Hall is derived for a perfectly insulating septum, and any value far
below the electrolyte's 78 approximates that. Leaving it unset would put the
electrolyte's permittivity in the membrane, letting the field leak through the
septum and changing the very geometry the benchmark is about."""


def bulk_conductivity_S_m(electrolyte: Electrolyte, concentration_M: float) -> float:
    """Return ``sigma = F sum_i z_i^2 mu_i^0 c_i``, in S/m.

    The infinite-dilution conductivity, which is what a run with the ``none``
    mobility correction transports. ``mu_i^0 = D_i^0 / V_T`` is the Nernst-
    Einstein relation, which holds at infinite dilution and only there (PHY-14,
    VER-05) — that is precisely why this benchmark runs classical.
    """
    concentration_mol_m3 = concentration_M * 1.0e3
    return FARADAY * math.fsum(
        ion.valence**2 * ion.mobility_0 * concentration_mol_m3 for ion in electrolyte.species
    )


def maxwell_hall_conductance_S(
    conductivity_S_m: float, *, radius_nm: float, length_nm: float
) -> float:
    """Return ``G = sigma [L/(pi a^2) + 1/(2a)]^-1``, in siemens."""
    radius_m = radius_nm * 1e-9
    length_m = length_nm * 1e-9
    resistance = length_m / (math.pi * radius_m**2) + 1.0 / (2.0 * radius_m)
    return conductivity_S_m / resistance


def _solve(reservoir_radius_nm: float) -> float:
    """Return the conductance of the uncharged pore in one reservoir, in siemens."""
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
    # No wall grading: the pore is uncharged, so there is no double layer to
    # resolve. The refinement goes to the mouth, where the current density is
    # singular and the access resistance is set.
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
    """Return the measured conductance at each reservoir radius, in siemens."""
    return {radius: _solve(radius) for radius in RESERVOIR_RADII_NM}


@pytest.fixture(scope="module")
def analytic_S() -> float:
    """Return the Maxwell-Hall conductance for this pore and electrolyte."""
    electrolyte = Electrolyte.from_parameter_file()
    conductivity = bulk_conductivity_S_m(electrolyte, CONCENTRATION_M)
    analytic = maxwell_hall_conductance_S(
        conductivity, radius_nm=PORE_RADIUS_NM, length_nm=MEMBRANE_THICKNESS_NM
    )
    logger.info("sigma = %.4f S/m, Maxwell-Hall G = %.6e S", conductivity, analytic)
    return analytic


@pytest.mark.parametrize("radius_nm", RESERVOIR_RADII_NM)
def test_ver17_access_conductance_matches_maxwell_hall(
    conductances: dict[float, float], analytic_S: float, radius_nm: float
) -> None:
    """``G`` from the solve is the closed form to better than 2 % (VER-17, QR-01)."""
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


def test_ver17_the_finite_reservoir_is_not_what_the_benchmark_measures(
    conductances: dict[float, float],
) -> None:
    """Doubling the reservoir must move ``G`` by well under the tolerance.

    The closed form assumes access to infinity. If ``G`` moved appreciably
    between a 50 nm and a 100 nm reservoir, the 2 % above would be measuring the
    truncation of the domain rather than the accuracy of the axisymmetric
    discretisation, and passing it would mean nothing.
    """
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
    """The variant with ``1/a`` would be 16 % out, so the two forms are checked against each other.

    Two claims, both arithmetic and both cheap. First, that the radius form and
    the diameter form of VER-17 are the same expression — a transcription error
    between them is the easiest way to get this wrong. Second, that the access
    term is a large enough share of the total for the factor of two in it to
    matter: 19.5 % here, so halving the access resistance shifts ``G`` by about
    10 % and doubling it by about 16 %, either of which is a plausible-looking
    wrong answer.
    """
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
