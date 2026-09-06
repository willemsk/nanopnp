"""VER-29 on the deployed ClyA reference mesh: PHY-19's assertion, decomposed.

The Tier-1 half of VER-29 checks the container, the formats and each gate firing
on a field built to fail it. This is the half that cannot be done on a toy mesh:
whether the *reference* mesh — 0.05 nm at the pore wall, 0.1 nm in the lumen,
2.8 nm in the reservoir, 44 000 elements — carries a field smeared at the
reference's own ``sigma R_i ~ 0.085 nm`` to within QR-03's 10^-3.

The field is a sum of Gaussian rings centred on the delivered pore contour,
because the reference's smearing kernel integrates to *exactly* its charge over
the plane (`.knowledge/04` §3): ``Q_net = e Sum_i q_i`` is known in closed form
rather than measured by the code under test. Every ring sits on the wall, where
the elements are 0.05 nm — that is the mesh the reference actually deployed, and
placing the same charge 0.5 nm into the coarser lumen is enough to fail the
quadrature gate (measured: 1.3e-4 against the 1e-4 it allows).

Two things here are gates on the *gates*. The coarsened mesh must fail the
quadrature-agreement gate while its conservation legs still pass, or the
agreement gate is decoration; and the per-plane check must be materially better
with the 0.2 nm ramp than with a near-step indicator, or the ramp is.
"""

from __future__ import annotations

import numpy as np
import pytest

from nanopnp.charge.fields import (
    CONSERVATION_TOL,
    QUADRATURE_TOL,
    RING_TOL,
    ChargeField,
    ChargeFieldError,
    FieldDocument,
    FormSpec,
    check_conservation,
    conservation,
    create_form,
)
from nanopnp.core.constants import ELEMENTARY_CHARGE
from nanopnp.density.grid import RadialGrid
from nanopnp.mesh.reference import ReferenceGeometry
from nanopnp.physics.measures import AXISYMMETRIC

SMEARING_WIDTH_NM = 0.085
"""``sigma R_i`` at the reference's own smearing: ``0.5 x 0.17 nm`` (PHY-16 step 3)."""

GRID_ORIGIN_NM = (0.0, -2.5)
GRID_SPACING_NM = (0.01, 0.01)
GRID_SHAPE = (601, 1551)
"""``r`` in [0, 6], ``z`` in [-2.5, 13] nm, at twice the reference's 0.005 nm step.

Twice the step and not the step itself because the trapezium rule on a function
decaying to zero at both ends has no Euler-Maclaurin boundary terms at all: its
error is beyond every order in ``h``, so ``Q_grid`` is exact either way and the
grid costs a quarter of the memory. Confirmed below — ``Q_grid`` reproduces the
closed-form ``Q_net`` to the last bit.
"""

RINGS = (
    (1.85, -0.85, -12.0),
    (2.20, 0.70, -12.0),
    (2.95, 3.15, -12.0),
    (3.00, 4.80, -12.0),
    (3.02, 8.48, -12.0),
    (3.08, 10.28, -12.0),
)
"""``(r0, z0, q_e)`` per ring: six vertices of the delivered ClyA contour.

The total is -72 e, which is ClyA's own charge at pH 7.5 and the number the
reference's own table integrates to exactly (`.knowledge/04` §7 G5). It is a
coincidence of construction here, not a physical claim: what the test needs is
a ``Q_net`` known in closed form, and this makes the numbers legible beside the
reference's.
"""

Q_NET_E = sum(charge for _, _, charge in RINGS)

COARSE_MAXH_NM = 0.2
"""Uniform element size of the deliberately under-resolving mesh.

Chosen by measurement rather than by argument: at 0.2 nm the conservation legs
read 1.3e-4 — comfortably inside QR-03 — while the order/order+3 agreement reads
2.3e-4, over twice what it allows. The quadrature error is *not* monotone in
``h`` (0.3 nm reads 1.0e-4 and 0.5 nm reads 1.4e-3), which is what aliasing of a
0.085 nm Gaussian by a Gauss rule looks like and is exactly why the gate is a
measured agreement rather than an element-size rule.
"""


def _rings_grid() -> RadialGrid:
    """Return the summed ring field, in C m^-2, on the shared grid."""
    values = np.zeros((GRID_SHAPE[1], GRID_SHAPE[0]), dtype=np.float64)
    for centre_r, centre_z, charge_e in RINGS:
        values += create_form(
            FormSpec(
                name="gaussian_ring",
                parameters={
                    "centre_r_nm": centre_r,
                    "centre_z_nm": centre_z,
                    "width_nm": SMEARING_WIDTH_NM,
                    "charge_e": charge_e,
                },
                origin_nm=GRID_ORIGIN_NM,
                spacing_nm=GRID_SPACING_NM,
                shape=GRID_SHAPE,
            )
        ).values
    return RadialGrid(origin_nm=GRID_ORIGIN_NM, spacing_nm=GRID_SPACING_NM, values=values)


def _document(**overrides: object) -> FieldDocument:
    """Return the header for the ring field, declaring the closed-form ``Q_net``."""
    payload: dict[str, object] = {
        "schema": "nanopnp/field/v1",
        "name": "clya-rings",
        "quantity": "areal_charge_density",
        "units": "C/m^2",
        "provenance": {
            "source": "analytic",
            "notes": "Gaussian rings on the delivered ClyA contour, PHY-16 step 3's kernel",
        },
        "form": FormSpec(
            name="gaussian_ring",
            parameters={},
            origin_nm=GRID_ORIGIN_NM,
            spacing_nm=GRID_SPACING_NM,
            shape=GRID_SHAPE,
        ).model_dump(),
        "q_net_e": Q_NET_E,
        **overrides,
    }
    return FieldDocument.model_validate(payload)


@pytest.fixture(scope="module")
def field() -> ChargeField:
    """Return the ring field: six Gaussians summing to a charge known exactly."""
    return ChargeField(
        document=_document(),
        grid=_rings_grid(),
        source=__file__,  # type: ignore[arg-type]
    )


@pytest.fixture(scope="module")
def mesh():
    """Return the WP8 ClyA reference mesh, at the §5.2.2 size fields."""
    return ReferenceGeometry.from_fixture().generate(check_quality=False)


@pytest.fixture(scope="module")
def report(field: ChargeField, mesh):
    """Return the conservation report on the reference mesh, ungated."""
    return conservation(field, mesh, AXISYMMETRIC)


@pytest.fixture(scope="module")
def coarse_mesh():
    """Return a uniform rectangle covering the whole grid box at 0.2 nm."""
    import netgen.occ as occ
    import ngsolve as ngs

    face = occ.MoveTo(0.0, GRID_ORIGIN_NM[1]).Rectangle(6.0, 15.5).Face()
    face.name = "electrolyte"
    return ngs.Mesh(occ.OCCGeometry(face, dim=2).GenerateMesh(maxh=COARSE_MAXH_NM))


# -- the two legs -------------------------------------------------------------


def test_ver29_the_producer_leg_reproduces_the_closed_form_charge(report) -> None:
    """``Q_grid`` against ``Q_net = e Sum_i q_i``, which no code here computed.

    The leg the reference's own 1.25 % discrepancy could not be attributed to.
    The trapezium rule has no boundary terms on a field decaying to zero at both
    ends, so this is not a tolerance so much as a check that the smearing kernel
    normalises the way `.knowledge/04` §3 says it does.
    """
    assert report.producer_error is not None
    assert abs(report.producer_error) < CONSERVATION_TOL
    assert report.q_grid_C / ELEMENTARY_CHARGE == pytest.approx(Q_NET_E, rel=1e-12)


def test_ver29_the_consumer_leg_conserves_on_the_reference_mesh(report) -> None:
    """``Q_mesh`` against ``Q_grid`` (QR-03): interpolation, quadrature, footprint.

    The whole point of the decomposition. A single number against ``Q_net``
    attributes nothing; this one says the deployed mesh carried what it was
    handed.
    """
    assert abs(report.consumer_error) < CONSERVATION_TOL
    # And the deployed mesh is not trivially reproducing the grid: the two are
    # different computations, so the agreement is evidence rather than identity.
    assert report.q_mesh_C != report.q_grid_C


def test_ver29_every_gate_passes_on_the_reference_mesh(report) -> None:
    """The reference configuration clears truncation, quadrature and both legs."""
    assert check_conservation(report) is report
    assert report.ring_ratio < RING_TOL
    assert report.quadrature_error < QUADRATURE_TOL


def test_ver29_every_ramped_plane_agrees_with_the_source_grid(report) -> None:
    """PHY-19's per-plane check, at every plane rather than only the worst.

    A globally satisfied check can hide compensating local errors, so the assert
    is on the whole ladder: the worst plane alone would be the same statement the
    gate makes, and would not notice a systematic drift down the pore.
    """
    reference = report.reference_C
    errors = [
        abs(mesh_value - grid_value) / reference
        for grid_value, mesh_value in zip(
            report.grid_cumulative_C, report.mesh_cumulative_C, strict=True
        )
    ]
    assert len(errors) == len(report.planes_nm) > 1
    assert max(errors) < CONSERVATION_TOL


def test_ver29_the_axis_guard_deletes_nothing_on_this_structure(report) -> None:
    """PHY-18's ``r < 0.01 nm`` guard, computed rather than assumed.

    The innermost ClyA atoms sit at ``r >~ 1.6 nm``, so the guard strip sees
    ``exp(-(1.6/0.085)^2)`` of peak and the deficit is numerically zero. Reported
    all the same, because a different structure — or an analyte on the axis —
    makes it real, and a deficit nobody measured is a deficit nobody notices.
    """
    assert abs(report.guard_deficit_C / ELEMENTARY_CHARGE) < 1e-9 * abs(Q_NET_E)


# -- the gates on the gates ---------------------------------------------------


def test_ver29_a_coarsened_mesh_fails_the_quadrature_gate_not_the_conservation_one(
    field: ChargeField, coarse_mesh
) -> None:
    """The under-resolving mesh is named as such, and not as a conservation failure.

    This is what the agreement gate is for. At 0.2 nm the conservation legs are
    still comfortably inside QR-03 — a run without the gate would report a
    conserved charge and a wrong field — while the order/order+3 agreement says
    plainly that the number cannot be defended. Getting these the wrong way round
    would name the field's producer for the mesh's failure.
    """
    coarse = conservation(field, coarse_mesh, AXISYMMETRIC)
    assert abs(coarse.consumer_error) < CONSERVATION_TOL
    assert coarse.producer_error is not None
    assert abs(coarse.producer_error) < CONSERVATION_TOL
    assert coarse.worst_plane[1] < CONSERVATION_TOL

    assert coarse.quadrature_error > QUADRATURE_TOL
    with pytest.raises(ChargeFieldError) as raised:
        check_conservation(coarse)
    assert raised.value.gate == "the deployed mesh under-resolves the supplied field"


def test_ver29_the_per_plane_ramp_is_not_cosmetic(field: ChargeField, mesh) -> None:
    """A near-step indicator on the same planes exceeds the budget the ramp meets.

    The planes are put through the ring centres, which is the worst case and the
    one a plane ladder will eventually land on. With a 0.002 nm ramp — a step for
    every practical purpose against a 0.05 nm element — the check reads 1.9e-3 of
    ``Q_net``, nearly twice QR-03's budget, purely from quadrature across the
    elements the plane straddles. The 0.2 nm ramp reads 7e-6. Both sides evaluate
    the same Lipschitz functional, so nothing is being smoothed away: what the
    ramp removes is the discontinuity, not the disagreement.
    """
    planes = tuple(centre_z for _, centre_z, _ in RINGS)
    ramped = conservation(field, mesh, AXISYMMETRIC, planes_nm=planes, ramp_nm=0.2)
    stepped = conservation(field, mesh, AXISYMMETRIC, planes_nm=planes, ramp_nm=0.002)

    assert ramped.worst_plane[1] < CONSERVATION_TOL
    assert stepped.worst_plane[1] > CONSERVATION_TOL
    assert stepped.worst_plane[1] > 100.0 * ramped.worst_plane[1]
