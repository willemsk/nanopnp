"""VER-21 (with NUM-09, VER-19): the electrophoretic mobility of a charged sphere."""

import logging
import math
from dataclasses import dataclass
from itertools import pairwise

import ngsolve as ngs
import pytest

from nanopnp.geometry.analyte import ANALYTE_BOUNDARY, AnalyteInBoxGeometry, SphereBody
from nanopnp.numerics.measures import AXISYMMETRIC
from nanopnp.physics import models
from nanopnp.physics.models import CoupledBoundaries, CoupledModel, ModelSolution
from nanopnp.post.forces import axial_extension, extract

logger = logging.getLogger(__name__)

FIELD = 0.02

SPEED = 0.05

ZETA = 0.5

# VER-21
HENRY_TOLERANCE = 0.05

SMOLUCHOWSKI_TOLERANCE = 0.15


@dataclass(frozen=True)
class Case:
    radius_nm: float
    concentration_M: float
    outer_ratio: float
    wall_fraction: float = 0.2


CASES = (
    Case(radius_nm=1.0, concentration_M=0.0231, outer_ratio=16.0),
    Case(radius_nm=2.0, concentration_M=0.1, outer_ratio=12.0),
    Case(radius_nm=5.0, concentration_M=1.0, outer_ratio=10.0),
)


def henry_function(kappa_a: float) -> float:
    return 1.0 + 1.0 / (2.0 * (1.0 + 2.5 / (kappa_a * (1.0 + 2.0 * math.exp(-kappa_a)))) ** 3)


@dataclass(frozen=True)
class Mobility:
    kappa_a: float
    zeta: float
    mobility: float
    zeta_drift: float


def _surface_mean_potential(solution: ModelSolution, mesh: ngs.Mesh) -> float:
    region = mesh.Boundaries(ANALYTE_BOUNDARY)
    lifted = ngs.BoundaryFromVolumeCF(solution.potential)
    weighted = float(ngs.Integrate(lifted * ngs.x, mesh, definedon=region))
    area = float(ngs.Integrate(ngs.x, mesh, definedon=region))
    return weighted / area


def _measure(case: Case) -> Mobility:
    model = models.create(
        "pnp-ns",
        concentration_M=case.concentration_M,
        inertia=False,
        variable_density=False,
        pressure_constraint=True,
        solid_permittivities={"analyte": 20.0},
    )
    assert isinstance(model, CoupledModel)
    debye_nm = model.scales.debye_length_nm
    outer_nm = case.outer_ratio * case.radius_nm
    mesh = AnalyteInBoxGeometry(
        SphereBody(radius_nm=case.radius_nm), outer_radius_nm=outer_nm
    ).generate(maxh_nm=0.15 * outer_nm, wall_h_nm=case.wall_fraction * debye_nm)
    extension = axial_extension(mesh, inner_nm=1.2 * case.radius_nm, outer_nm=3.0 * case.radius_nm)

    # Debye-Hueckel around a sphere: sigma_s = eps zeta (1/a + 1/lambda_D).
    # It only has to land near the target; zeta is read back, not assumed.
    surface_charge = ZETA * (1.0 / case.radius_nm + 1.0 / debye_nm)
    still = ngs.CF((0.0, 0.0))
    common = {
        "boundaries": CoupledBoundaries(
            potential="outer",
            concentration="outer",
            velocity="analyte|outer",
            velocity_axis="axis",
        ),
        "surface_charge": ngs.CF(surface_charge),
        "surface_charge_boundary": ANALYTE_BOUNDARY,
    }
    field = model.solve(
        mesh, AXISYMMETRIC, potential_values=-FIELD * ngs.y, velocity_values=still, **common
    )
    drag = model.solve(
        mesh,
        AXISYMMETRIC,
        potential_values=0.0,
        velocity_values=mesh.BoundaryCF({"outer": ngs.CF((0.0, SPEED))}, default=still),
        **common,
    )
    field_N = extract(field, AXISYMMETRIC, extension).total_N
    drag_N = extract(drag, AXISYMMETRIC, extension).total_N
    zeta_field = _surface_mean_potential(field, mesh)
    zeta_drag = _surface_mean_potential(drag, mesh)

    point = Mobility(
        kappa_a=case.radius_nm / debye_nm,
        zeta=zeta_drag,
        mobility=field_N * SPEED / (drag_N * FIELD),
        zeta_drift=abs(zeta_field - zeta_drag),
    )
    logger.info(
        "kappa a = %.2f: zeta~ = %.4f, mu~_e = %.4f against Hueckel %.4f, Henry %.4f and "
        "Smoluchowski %.4f (f = %.4f)",
        point.kappa_a,
        point.zeta,
        point.mobility,
        2.0 * point.zeta / 3.0,
        2.0 * point.zeta / 3.0 * henry_function(point.kappa_a),
        point.zeta,
        henry_function(point.kappa_a),
    )
    return point


@pytest.fixture(scope="module")
def mobilities() -> tuple[Mobility, ...]:
    return tuple(_measure(case) for case in CASES)


def test_ver21_the_mobility_follows_henrys_function_at_every_screening_ratio(
    mobilities: tuple[Mobility, ...],
) -> None:
    assert henry_function(1e-9) == pytest.approx(1.0, abs=1e-6)
    assert henry_function(1e9) == pytest.approx(1.5, abs=1e-6)
    for point in mobilities:
        expected = 2.0 * point.zeta / 3.0 * henry_function(point.kappa_a)
        error = abs(point.mobility / expected - 1.0)
        assert error < HENRY_TOLERANCE, (
            f"at kappa a = {point.kappa_a:.2f} the measured mu~_e = {point.mobility:.4f} against "
            f"Henry's {expected:.4f} (zeta~ = {point.zeta:.4f}, f = "
            f"{henry_function(point.kappa_a):.4f}): a relative error of {error:.3g} beyond the "
            f"stated {HENRY_TOLERANCE:.0%}"
        )


def test_ver21_the_huckel_limit_is_recovered_at_small_kappa_a(
    mobilities: tuple[Mobility, ...],
) -> None:
    point = mobilities[0]
    assert point.kappa_a < 1.0, (
        f"the small-kappa_a case sits at kappa a = {point.kappa_a:.2f}, which is not the thick "
        "double layer Hueckel describes"
    )
    huckel = 2.0 * point.zeta / 3.0
    error = abs(point.mobility / huckel - 1.0)
    assert error < HENRY_TOLERANCE, (
        f"at kappa a = {point.kappa_a:.2f} the measured mu~_e = {point.mobility:.4f} against "
        f"Hueckel's 2 zeta~/3 = {huckel:.4f}, a relative error of {error:.3g} beyond the stated "
        f"{HENRY_TOLERANCE:.0%}. Henry's correction at this kappa a is only "
        f"{henry_function(point.kappa_a) - 1.0:.1%}, so this is not the asymptotics"
    )


def test_ver21_the_mobility_climbs_towards_the_smoluchowski_limit(
    mobilities: tuple[Mobility, ...],
) -> None:
    ratios = [point.mobility / point.zeta for point in mobilities]
    assert all(coarse < fine for coarse, fine in pairwise(ratios)), (
        f"mu~_e/zeta~ = {[round(r, 4) for r in ratios]} does not rise with kappa a "
        f"{[round(p.kappa_a, 2) for p in mobilities]}; the mobility must run from 2/3 at the "
        "Hueckel end to 1 at the Smoluchowski end"
    )
    thinnest = mobilities[-1]
    gap = 1.0 - ratios[-1]
    henry_gap = 1.0 - 2.0 * henry_function(thinnest.kappa_a) / 3.0
    assert gap < SMOLUCHOWSKI_TOLERANCE, (
        f"at kappa a = {thinnest.kappa_a:.2f} the measured mu~_e is {gap:.1%} below "
        f"Smoluchowski's eps zeta/eta, beyond the {SMOLUCHOWSKI_TOLERANCE:.0%} this test allows. "
        f"Henry's own shortfall at this kappa a is {henry_gap:.1%}"
    )
    assert gap < henry_gap + HENRY_TOLERANCE, (
        f"the measured shortfall from Smoluchowski is {gap:.1%} against Henry's {henry_gap:.1%}; "
        "the measurement is further from the limit than the closed form allows, which is a "
        "defect rather than the asymptotics"
    )


def test_ver21_the_zeta_potential_is_the_same_in_both_solves(
    mobilities: tuple[Mobility, ...],
) -> None:
    for point in mobilities:
        assert point.zeta_drift < 1e-3, (
            f"at kappa a = {point.kappa_a:.2f} the mean surface potential differs by "
            f"{point.zeta_drift:.2e} V_T between the field and drag solves, against a zeta~ of "
            f"{point.zeta:.4f}. The applied field is polarising the double layer, so Henry's "
            "linear-response result is not the right target"
        )
