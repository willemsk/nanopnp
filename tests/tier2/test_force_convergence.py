"""NUM-29 (with NUM-18, PHY-23, QR-12, VAL-11, VER-22): force convergence, RSK-04."""

import logging
from dataclasses import dataclass
from itertools import pairwise

import ngsolve as ngs
import pytest

from nanopnp.geometry.analyte import (
    ANALYTE_DOMAIN,
    AnalyteInBoxGeometry,
    PoreWithAnalyte,
    SphereBody,
    SpheroidBody,
)
from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.numerics.measures import AXISYMMETRIC, FixedCharge
from nanopnp.physics import models
from nanopnp.physics.distance import wall_distance
from nanopnp.physics.models import CoupledBoundaries, CoupledModel
from nanopnp.post.forces import FORCE_ROUTE_TOLERANCE_N, AnalyteForces, axial_extension, extract
from nanopnp.solve.continuation import default_ladder, mesh_report, run_ladder

logger = logging.getLogger(__name__)


RADIUS_NM, OUTER_NM = 2.0, 12.0
CONCENTRATION_M = 0.3
FIELD = 0.2
CHARGE_E = -20.0
# VER-22
SHELL_NM = (2.5, 6.0)

MESHES = ((1.2, 0.15), (0.8, 0.10), (0.53, 0.067))

# NUM-29
STEP_TOLERANCE_N = 1e-14


@dataclass(frozen=True)
class Refinement:
    maxh_nm: float
    wall_h_nm: float
    elements: int
    dofs: int
    forces: AnalyteForces

    @property
    def route_difference_N(self) -> float:
        assert self.forces.agreement is not None
        return self.forces.agreement.total_difference_N

    @property
    def oracle_difference_N(self) -> float:
        assert self.forces.agreement is not None
        return self.forces.agreement.hydrodynamic_difference_N


# VER-22
def _charged_sphere_model() -> CoupledModel:
    model = models.create(
        "pnp-ns",
        concentration_M=CONCENTRATION_M,
        inertia=False,
        variable_density=False,
        pressure_constraint=True,
        solid_permittivities={ANALYTE_DOMAIN: 20.0},
    )
    assert isinstance(model, CoupledModel)
    return model


# VER-22
@pytest.fixture(scope="module")
def study() -> tuple[Refinement, ...]:
    body = SphereBody(radius_nm=RADIUS_NM)
    model = _charged_sphere_model()
    density = body.charge_density_C_m3(CHARGE_E) / model.scales.charge_density_C_m3
    boundaries = CoupledBoundaries(
        potential="outer",
        concentration="outer",
        velocity="analyte|outer",
        velocity_axis="axis",
    )

    refinements: list[Refinement] = []
    for maxh_nm, wall_h_nm in MESHES:
        mesh = AnalyteInBoxGeometry(body, outer_radius_nm=OUTER_NM).generate(
            maxh_nm=maxh_nm, wall_h_nm=wall_h_nm
        )
        solution = model.solve(
            mesh,
            AXISYMMETRIC,
            boundaries=boundaries,
            potential_values=-FIELD * ngs.y,
            velocity_values=ngs.CF((0.0, 0.0)),
            fixed_charge=FixedCharge(mesh.MaterialCF({ANALYTE_DOMAIN: density}, default=0.0), None),
        )
        extension = axial_extension(mesh, inner_nm=SHELL_NM[0], outer_nm=SHELL_NM[1])
        refinements.append(
            Refinement(
                maxh_nm=maxh_nm,
                wall_h_nm=wall_h_nm,
                elements=int(str(mesh_report(mesh)["elements"])),
                dofs=int(solution.space.ndof),
                forces=extract(solution, AXISYMMETRIC, extension),
            )
        )
    return tuple(refinements)


@pytest.mark.slow
def test_num29_each_component_of_the_force_is_resolved_under_refinement(
    study: tuple[Refinement, ...],
) -> None:
    logger.info(
        "%9s %9s %8s %8s %12s %12s %12s %10s %10s",
        "maxh/nm",
        "wall/nm",
        "elements",
        "dofs",
        "F^em/pN",
        "F^hd/pN",
        "F^tot/pN",
        "|A-B|/pN",
        "|A-C|/pN",
    )
    for step in study:
        logger.info(
            "%9.3f %9.3f %8d %8d %+12.5f %+12.5f %+12.5f %10.2e %10.2e",
            step.maxh_nm,
            step.wall_h_nm,
            step.elements,
            step.dofs,
            step.forces.forces.em_N * 1e12,
            step.forces.forces.hd_N * 1e12,
            step.forces.total_N * 1e12,
            step.route_difference_N * 1e12,
            step.oracle_difference_N * 1e12,
        )

    components = {
        "F^em": [step.forces.forces.em_N for step in study],
        "F^hd": [step.forces.forces.hd_N for step in study],
        "F^tot": [step.forces.total_N for step in study],
    }
    for name, values in components.items():
        steps = [abs(fine - coarse) for coarse, fine in pairwise(values)]
        assert steps[-1] < steps[0], (
            f"{name} moves by {steps[0] * 1e12:.5f} pN on the first refinement and "
            f"{steps[-1] * 1e12:.5f} pN on the second; a sequence that is not settling is not a "
            "converged force, whatever the routes agree on"
        )
        assert steps[-1] < STEP_TOLERANCE_N, (
            f"{name} still moves by {steps[-1] * 1e12:.5f} pN between the two finest meshes, "
            f"beyond the {STEP_TOLERANCE_N * 1e12:.2f} pN this study calls resolved; NUM-29 asks "
            "for each contribution well inside 1 pN"
        )


# NUM-28
@pytest.mark.slow
def test_num29_the_routes_agree_on_every_mesh_of_the_study(
    study: tuple[Refinement, ...],
) -> None:
    for step in study:
        assert step.route_difference_N < FORCE_ROUTE_TOLERANCE_N, (
            f"on the {step.elements}-element mesh the domain and surface routes are "
            f"{step.route_difference_N * 1e12:.4f} pN apart, beyond the NUM-29 tolerance of "
            f"{FORCE_ROUTE_TOLERANCE_N * 1e12:.1f} pN"
        )


@pytest.mark.slow
def test_num29_the_reaction_route_converges_to_the_domain_route(
    study: tuple[Refinement, ...],
) -> None:
    gaps = [step.oracle_difference_N for step in study]
    assert all(fine < coarse for coarse, fine in pairwise(gaps)), (
        "the gap between the domain route's F^hd and the reaction route's does not fall "
        f"monotonically under refinement: {[f'{gap * 1e12:.2e}' for gap in gaps]} pN. C is exact "
        "on the discrete problem, so a gap that does not shrink with the solution points at the "
        "domain form's consistency term rather than at resolution"
    )
    assert gaps[-1] < 1e-16, (
        f"the finest mesh still leaves {gaps[-1] * 1e12:.3e} pN between the two, which is more "
        "than a discrete identity should cost"
    )


REFERENCE_PORE = CylindricalPoreGeometry(
    pore_radius_nm=4.5, membrane_thickness_nm=13.0, reservoir_radius_nm=20.0
)

# FR-22
REFERENCE_BODY = SpheroidBody(semi_radial_nm=2.9, semi_axial_nm=3.35)

# q_Hb of the production runs: .knowledge/05-analyte-and-forces.md section 10.3.
REFERENCE_CHARGE_E = -4.0

REFERENCE_BIAS_V = 0.05
REFERENCE_CONCENTRATION_M = 0.3

REFERENCE_SURFACE_CHARGE_C_M2 = -0.02

# FR-25
# Candidates: .knowledge/05-analyte-and-forces.md section 3; 20 is the upper one.
ANALYTE_PERMITTIVITY = 20.0

MEMBRANE_PERMITTIVITY = 2.0
REFERENCE_MESH = (3.0, 0.12)
REFERENCE_SHELL_NM = (0.25, 1.1)


# PHY-23
@pytest.fixture(scope="module")
def reference_case() -> tuple[CoupledModel, AnalyteForces, float]:
    geometry = PoreWithAnalyte(REFERENCE_PORE, REFERENCE_BODY, analyte_h_nm=REFERENCE_MESH[1])
    mesh = geometry.generate(maxh_nm=REFERENCE_MESH[0], wall_h_nm=REFERENCE_MESH[1])
    # PHY-02: the distance field is to the pore wall, and the analyte is not a
    # source. Driving the wall corrections from proximity to the body would be a
    # model change, and it goes behind a flag rather than into a benchmark.
    distance = wall_distance(mesh, "wall", order=AXISYMMETRIC.element_order)
    density_C_m3 = REFERENCE_BODY.charge_density_C_m3(REFERENCE_CHARGE_E)

    ladder = run_ladder(
        default_ladder(
            mesh,
            concentration_M=REFERENCE_CONCENTRATION_M,
            bias_V=REFERENCE_BIAS_V,
            surface_charge_C_m2=REFERENCE_SURFACE_CHARGE_C_M2,
            fixed_charge_C_m3=density_C_m3,
            fixed_charge_domain=ANALYTE_DOMAIN,
            wall_distance_nm=distance,
            solid_permittivities={
                "membrane": MEMBRANE_PERMITTIVITY,
                ANALYTE_DOMAIN: ANALYTE_PERMITTIVITY,
            },
            boundaries=CoupledBoundaries(velocity="wall|membrane|analyte"),
        )
    )
    extension = axial_extension(
        mesh, inner_nm=REFERENCE_SHELL_NM[0], outer_nm=REFERENCE_SHELL_NM[1]
    )
    forces = extract(ladder.solution, AXISYMMETRIC, extension, wall_distance_nm=distance)
    model = ladder.solution.model
    assert isinstance(model, CoupledModel)
    return model, forces, density_C_m3


# VAL-11
@pytest.mark.slow
def test_rsk04_the_reference_shaped_case_is_recorded(
    reference_case: tuple[CoupledModel, AnalyteForces, float],
) -> None:
    model, result, density_C_m3 = reference_case
    split = result.forces
    logger.info(
        "reference-shaped case: %.0f mM, %+.0f mV, q = %+.1f e over %.1f nm^3 "
        "(rho = %.3e C/m^3), eps_p = %.0f",
        REFERENCE_CONCENTRATION_M * 1e3,
        REFERENCE_BIAS_V * 1e3,
        REFERENCE_CHARGE_E,
        REFERENCE_BODY.volume_nm3,
        density_C_m3,
        ANALYTE_PERMITTIVITY,
    )
    logger.info(
        "F^em = %+.4f pN (trans is negative), F^hd = %+.4f pN, F^tot = %+.4f pN",
        split.em_N * 1e12,
        split.hd_N * 1e12,
        split.total_N * 1e12,
    )
    logger.info(
        "Korteweg-Helmholtz residual %+.4e pN, domain against surface %.4e pN, "
        "domain against reaction %.4e pN",
        result.dielectric_gradient_N * 1e12,
        result.agreement.total_difference_N * 1e12 if result.agreement else float("nan"),
        result.agreement.hydrodynamic_difference_N * 1e12 if result.agreement else float("nan"),
    )
    logger.info(
        "force unit eps V_T^2 = %.4e N; NUM-29's 0.1 pN is %.3f of it",
        model.scales.force_N,
        FORCE_ROUTE_TOLERANCE_N / model.scales.force_N,
    )

    assert split.em_N < 0.0 < split.hd_N, (
        f"F^em = {split.em_N * 1e12:+.4f} pN and F^hd = {split.hd_N * 1e12:+.4f} pN are not "
        "opposed; the reference has the electromechanical force driving Hb to trans against a "
        "hydrodynamic force driving it to cis, and a record with both of one sign is not shaped "
        "like the case it is named for"
    )
    assert 1e-13 < min(abs(split.em_N), abs(split.hd_N)) < 1e-10, (
        f"the smaller half is {min(abs(split.em_N), abs(split.hd_N)) * 1e12:.4f} pN, outside the "
        "piconewton order this configuration is posed at; RSK-04 is a statement about forces of "
        "that size and a record three orders away from it evidences nothing"
    )


# NUM-28, PHY-23, VER-22
@pytest.mark.slow
def test_rsk04_the_omitted_korteweg_helmholtz_term_is_measured_not_assumed(
    reference_case: tuple[CoupledModel, AnalyteForces, float],
) -> None:
    _, result, _ = reference_case
    residual_N = result.dielectric_gradient_N
    assert residual_N != 0.0, (
        "the Korteweg-Helmholtz residual came out at exactly zero with the permittivity "
        "correction active; grad(eps) is not zero here, so either the correction is not on or "
        "the term is not being evaluated"
    )
    assert abs(residual_N) < 0.01 * abs(result.forces.em_N), (
        f"the omitted term is {residual_N * 1e12:+.4e} pN against an electromechanical force of "
        f"{result.forces.em_N * 1e12:+.4f} pN. It is a correction to the validated model, not a "
        "leading term, and a value this large means the dielectric-gradient body force can no "
        "longer be left off by default without saying so"
    )
    assert result.agreement is not None, "the routes were not checked on the reference case"
    assert result.agreement.total_difference_N < FORCE_ROUTE_TOLERANCE_N, (
        f"with every correction active the routes are "
        f"{result.agreement.total_difference_N * 1e12:.4f} pN apart, beyond NUM-29's "
        f"{FORCE_ROUTE_TOLERANCE_N * 1e12:.1f} pN. The domain form takes its eta and eps from the "
        "model's own coefficient seams, so a gap here is those coefficients disagreeing with the "
        "ones the residual was assembled from"
    )
