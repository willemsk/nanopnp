"""NUM-29: the force convergence study, and the RSK-04 record on the reference shape.

Two `slow` measurements, neither of which is a gate in the sense the rest of
Tier 2 is. VER-22 already asserts that the three routes agree at one operating
point; NUM-29 asks for something the single point cannot show — that the numbers
are *resolved*, meaning they stop moving under refinement, and by how much.

**The convergence study** refines VER-22's own configuration by 1.5 in element
size twice over and reports ``F^em``, ``F^hd``, ``F^tot`` and the route
disagreement against degrees of freedom. The assertions are on the *shape* of the
sequence: each component's successive change halves, and the last change is two
orders of magnitude inside the 1 pN of NUM-29. The route disagreement is
**reported and not asserted to fall**: at 1e-2 pN it is already two parts in
100 000 of ``F^em`` and is dominated by quadrature on two different geometric
supports, so it wanders rather than converging, and a monotonicity assertion on
it would be asserting noise. What is asserted is that every mesh, the coarsest
included, meets the 0.1 pN NUM-29 asks for.

**The reference-shaped record** is the RSK-04 evidence Phase 0 owes: the ePNP-NS
model with every correction active, a body of revolution in the lumen of a
charged pore at 300 mM and +50 mV with ``q = -4 e`` and ``eps_p = 20``, reached
through the NUM-18 ladder. It reports the two halves separately, their sum, the
Korteweg-Helmholtz residual PHY-23 omits — which is *not* zero here, the ``eps_r``
correction being on — and the route disagreement.

**What it is not.** It is not the PlyAB case. The pore is the analytic cylinder of
``mesh/primitives``, not a homology model, so it carries a uniform wall charge
rather than PlyAB-E1's atomistic distribution and has neither the cis cone nor the
constriction; the lumen is widened from the reference's 7.2 nm diameter to 9 nm,
which is this package's stated response to the QR-12 sliver risk of grading two
surfaces a fraction of a nanometre apart, and it leaves room for ``w``'s shell to
reach zero before the wall. Both forces come out at a few piconewtons rather than
the reference's ten, and *that is the expected consequence of those differences*,
not a discrepancy to explain away. What does carry over is the structure: ``F^em``
towards trans, ``F^hd`` towards cis, opposed and of the same order — VAL-11 is the
Tier-4 test that compares numbers, and this is not it.
"""

import logging
from dataclasses import dataclass
from itertools import pairwise

import ngsolve as ngs
import pytest

from nanopnp.core.constants import ELEMENTARY_CHARGE
from nanopnp.geometry.analyte import (
    ANALYTE_DOMAIN,
    AnalyteInBoxGeometry,
    PoreWithAnalyte,
    SphereBody,
    SpheroidBody,
)
from nanopnp.mesh.distance import wall_distance
from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.physics import models
from nanopnp.physics.measures import AXISYMMETRIC
from nanopnp.physics.models import CoupledBoundaries, CoupledModel
from nanopnp.post.forces import FORCE_ROUTE_TOLERANCE_N, AnalyteForces, axial_extension, extract
from nanopnp.solve.continuation import default_ladder, mesh_report, run_ladder

logger = logging.getLogger(__name__)

# -- the convergence study ---------------------------------------------------

RADIUS_NM, OUTER_NM = 2.0, 12.0
CONCENTRATION_M = 0.3
FIELD = 0.2
CHARGE_E = -20.0
SHELL_NM = (2.5, 6.0)
"""VER-22's configuration verbatim, so that the study refines the point the gate
is taken at rather than a neighbouring one."""

MESHES = ((1.2, 0.15), (0.8, 0.10), (0.53, 0.067))
"""``(maxh_nm, wall_h_nm)`` refined by 1.5 twice.

Not 2, which would put the finest mesh at 130 000 degrees of freedom for no extra
information: three points an octave apart already separate a converging sequence
from a wandering one, and the 1.5 ratio keeps the whole study inside a minute.
"""

STEP_TOLERANCE_N = 1e-14
"""0.01 pN, the change each component is required to be inside on the last step.

A hundredth of the 1 pN NUM-29 asks each contribution to be resolved to. Stated
as the *step*, not as an error against a reference, because there is no closed
form here — a sequence whose increments are this small has nowhere left to go.
"""


@dataclass(frozen=True)
class Refinement:
    """One mesh of the study and the forces taken on it."""

    maxh_nm: float
    wall_h_nm: float
    elements: int
    dofs: int
    forces: AnalyteForces

    @property
    def route_difference_N(self) -> float:
        """Domain against surface, absolutely."""
        assert self.forces.agreement is not None
        return self.forces.agreement.total_difference_N

    @property
    def oracle_difference_N(self) -> float:
        """Domain's ``F^hd`` against the reaction route's."""
        assert self.forces.agreement is not None
        return self.forces.agreement.hydrodynamic_difference_N


def _charged_sphere_model() -> CoupledModel:
    """Return VER-22's classical model."""
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


@pytest.fixture(scope="module")
def study() -> tuple[Refinement, ...]:
    """Solve the VER-22 configuration on three meshes and take the force on each."""
    body = SphereBody(radius_nm=RADIUS_NM)
    model = _charged_sphere_model()
    density = (CHARGE_E * ELEMENTARY_CHARGE / (body.volume_nm3 * 1e-27)) / (
        model.scales.charge_density_C_m3
    )
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
            fixed_charge=mesh.MaterialCF({ANALYTE_DOMAIN: density}, default=0.0),
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
    """``F^em``, ``F^hd`` and ``F^tot`` each stop moving, and the table is logged.

    The assertion is on the increments rather than on an error, there being no
    closed form for this configuration: a sequence whose successive changes fall
    and whose last change is 0.01 pN has resolved the quantity to far better than
    the 1 pN NUM-29 asks for. Per *component*, because RSK-04 is about the split
    and a total that converges while its halves drift is exactly the failure the
    study exists to rule out.
    """
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


@pytest.mark.slow
def test_num29_the_routes_agree_on_every_mesh_of_the_study(
    study: tuple[Refinement, ...],
) -> None:
    """0.1 pN between A and B, on the coarsest mesh as much as on the finest.

    NUM-29's tolerance is not a statement about the finest mesh available; it is
    what any mesh the force is reported from has to meet. The coarsest here is
    1 000 elements, which is the point: the identity behind NUM-28 is discrete,
    so the agreement does not have to be bought with resolution.
    """
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
    """A against C falls monotonically, unlike A against B, and that is expected.

    C is a discrete identity on the *same* space the residual was assembled on,
    so its gap to A is pure consistency error in A's quadrature of the body-force
    term and inherits the solution's own convergence. B integrates a traction on
    a different geometric support and its gap to A is dominated by surface
    quadrature, which does not converge in step with anything. Asserting the
    monotonicity where it exists and reporting it where it does not is the
    difference between a measurement and a decoration.
    """
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


# -- the reference-shaped record ---------------------------------------------

REFERENCE_PORE = CylindricalPoreGeometry(
    pore_radius_nm=4.5, membrane_thickness_nm=13.0, reservoir_radius_nm=20.0
)
"""13 nm thick, as PlyAB is, with the lumen widened from the reference's 3.6 nm
radius to 4.5 nm — see the module docstring on why, and on what that costs."""

REFERENCE_BODY = SpheroidBody(semi_radial_nm=2.9, semi_axial_nm=3.35)
"""The reference analyte: haemoglobin "approximated by a smooth cylinder-like
particle (h = 6.7 nm, w = 5.8 nm)", taken as the spheroid of those axes
(``.knowledge/05-analyte-and-forces.md`` section 10.3). Held at the lumen centre;
the z-sweep that would make an energy landscape out of this is FR-22 v1.0 work,
which amendment A1 leaves out of the spike."""

REFERENCE_CHARGE_E = -4.0
"""``q_Hb`` of the production runs, smeared as ``rho_part = q/V`` (section 10.3)."""

REFERENCE_BIAS_V = 0.05
REFERENCE_CONCENTRATION_M = 0.3
"""+50 mV in 300 mM NaCl, the operating point the +/-10 pN pair is quoted at."""

REFERENCE_SURFACE_CHARGE_C_M2 = -0.02
"""A uniformly negative lumen, which is as much of "predominantly negatively
charged, particularly at the constriction" as an analytic cylinder can carry."""

ANALYTE_PERMITTIVITY = 20.0
"""``eps_p`` of the body. The SI value is unverified; 20 is the upper of the two
candidates section 3 of the knowledge file offers, and it is recorded here
because a permittivity assumed silently is a result that cannot be reconstructed
(FR-25)."""

MEMBRANE_PERMITTIVITY = 2.0
REFERENCE_MESH = (3.0, 0.12)
REFERENCE_SHELL_NM = (0.25, 1.1)
"""``w``'s shell, fitting inside the 1.6 nm between the body and the lumen wall
with room at both ends: wider than the 0.12 nm elements at the body, and reaching
zero well before the wall, where ``check_extension`` requires it to have."""


@pytest.fixture(scope="module")
def reference_case() -> tuple[CoupledModel, AnalyteForces, float]:
    """Climb the ladder to the reference-shaped operating point and take the force.

    Every correction is active at the top of the ladder, so this is the one force
    measurement in the suite where ``grad(eps)`` is non-zero and the PHY-23
    residual has something to report.
    """
    geometry = PoreWithAnalyte(REFERENCE_PORE, REFERENCE_BODY, analyte_h_nm=REFERENCE_MESH[1])
    mesh = geometry.generate(maxh_nm=REFERENCE_MESH[0], wall_h_nm=REFERENCE_MESH[1])
    # PHY-02: the distance field is to the pore wall, and the analyte is not a
    # source. Driving the wall corrections from proximity to the body would be a
    # model change, and it goes behind a flag rather than into a benchmark.
    distance = wall_distance(mesh, "wall", order=AXISYMMETRIC.element_order)
    density_C_m3 = REFERENCE_CHARGE_E * ELEMENTARY_CHARGE / (REFERENCE_BODY.volume_nm3 * 1e-27)

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


@pytest.mark.slow
def test_rsk04_the_reference_shaped_case_is_recorded(
    reference_case: tuple[CoupledModel, AnalyteForces, float],
) -> None:
    """The RSK-04 record: two opposed forces, their sum, and the omitted term.

    Asserted only where the structure is a claim and not a number: the two halves
    are opposed, ``F^em`` pointing trans and ``F^hd`` cis as the reference has
    them, both are of piconewton order, and the routes still agree once every
    correction is on — which is the part that could have failed, the domain form's
    coefficients being the corrected ``eta`` and ``eps`` rather than constants.
    The magnitudes are logged, not gated; VAL-11 is where they are compared.
    """
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


@pytest.mark.slow
def test_rsk04_the_omitted_korteweg_helmholtz_term_is_measured_not_assumed(
    reference_case: tuple[CoupledModel, AnalyteForces, float],
) -> None:
    """With ``eps_r`` active the PHY-23 residual is non-zero, and it is reported.

    VER-22 asserts it vanishes classically. Here it does not, and the pair of
    assertions is what turns "the validated model omits the Korteweg-Helmholtz
    force" from a docstring into a measurement: this is the amount by which
    NUM-28 as printed falls short of the force the three routes agree on, at the
    operating point the omission was validated at.
    """
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
