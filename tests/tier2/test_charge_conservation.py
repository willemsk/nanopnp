"""VER-29 (with PHY-16, PHY-18, PHY-19, QR-03): the reference-mesh charge, decomposed."""

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
from nanopnp.numerics.measures import AXISYMMETRIC

# PHY-16
SMEARING_WIDTH_NM = 0.085

GRID_ORIGIN_NM = (0.0, -2.5)
GRID_SPACING_NM = (0.01, 0.01)
GRID_SHAPE = (601, 1551)

RINGS = (
    (1.85, -0.85, -12.0),
    (2.20, 0.70, -12.0),
    (2.95, 3.15, -12.0),
    (3.00, 4.80, -12.0),
    (3.02, 8.48, -12.0),
    (3.08, 10.28, -12.0),
)

Q_NET_E = sum(charge for _, _, charge in RINGS)

# QR-03
COARSE_DIVISIONS = (27, 70)


def _grid_extent_nm() -> tuple[tuple[float, float], tuple[float, float]]:
    return tuple(  # type: ignore[return-value]
        (origin, origin + spacing * (count - 1))
        for origin, spacing, count in zip(GRID_ORIGIN_NM, GRID_SPACING_NM, GRID_SHAPE, strict=True)
    )


def _rings_grid() -> RadialGrid:
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
    payload: dict[str, object] = {
        "schema": "nanopnp/field/v0.5",
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
    return ChargeField(
        document=_document(),
        grid=_rings_grid(),
        source=__file__,  # type: ignore[arg-type]
    )


@pytest.fixture(scope="module")
def mesh(clya_reference_mesh):  # type: ignore[no-untyped-def]
    return clya_reference_mesh()


@pytest.fixture(scope="module")
def report(field: ChargeField, mesh):
    return conservation(field, mesh, AXISYMMETRIC)


@pytest.fixture(scope="module")
def coarse_mesh():
    from ngsolve.meshes import MakeStructured2DMesh

    (r_min, r_max), (z_min, z_max) = _grid_extent_nm()
    divisions_r, divisions_z = COARSE_DIVISIONS
    return MakeStructured2DMesh(
        quads=False,
        nx=divisions_r,
        ny=divisions_z,
        mapping=lambda x, y: (r_min + (r_max - r_min) * x, z_min + (z_max - z_min) * y),
    )


def test_ver29_the_producer_leg_reproduces_the_closed_form_charge(report) -> None:
    assert report.producer_error is not None
    assert abs(report.producer_error) < CONSERVATION_TOL
    assert report.q_grid_C / ELEMENTARY_CHARGE == pytest.approx(Q_NET_E, rel=1e-12)


# QR-03
def test_ver29_the_consumer_leg_conserves_on_the_reference_mesh(report) -> None:
    assert abs(report.consumer_error) < CONSERVATION_TOL
    assert report.q_mesh_C != report.q_grid_C


def test_ver29_every_gate_passes_on_the_reference_mesh(report) -> None:
    assert check_conservation(report) is report
    assert report.ring_ratio < RING_TOL
    assert report.quadrature_error < QUADRATURE_TOL


# PHY-19
def test_ver29_every_ramped_plane_agrees_with_the_source_grid(report) -> None:
    reference = report.reference_C
    errors = [
        abs(mesh_value - grid_value) / reference
        for grid_value, mesh_value in zip(
            report.grid_cumulative_C, report.mesh_cumulative_C, strict=True
        )
    ]
    assert len(errors) == len(report.planes_nm) > 1
    assert max(errors) < CONSERVATION_TOL


# PHY-18
def test_ver29_the_axis_guard_deletes_nothing_on_this_structure(report) -> None:
    assert abs(report.guard_deficit_C / ELEMENTARY_CHARGE) < 1e-9 * abs(Q_NET_E)


# QR-03
def test_ver29_a_coarsened_mesh_fails_the_quadrature_gate_not_the_conservation_one(
    field: ChargeField, coarse_mesh
) -> None:
    coarse = conservation(field, coarse_mesh, AXISYMMETRIC)
    assert abs(coarse.consumer_error) < CONSERVATION_TOL
    assert coarse.producer_error is not None
    assert abs(coarse.producer_error) < CONSERVATION_TOL
    assert coarse.worst_plane[1] < CONSERVATION_TOL

    assert coarse.quadrature_error > QUADRATURE_TOL
    with pytest.raises(ChargeFieldError) as raised:
        check_conservation(coarse)
    assert raised.value.gate == "the deployed mesh under-resolves the supplied field"


# QR-03
def test_ver29_the_per_plane_ramp_is_not_cosmetic(field: ChargeField, mesh) -> None:
    planes = tuple(centre_z for _, centre_z, _ in RINGS)
    ramped = conservation(field, mesh, AXISYMMETRIC, planes_nm=planes, ramp_nm=0.2)
    stepped = conservation(field, mesh, AXISYMMETRIC, planes_nm=planes, ramp_nm=0.002)

    assert ramped.worst_plane[1] < CONSERVATION_TOL
    assert stepped.worst_plane[1] > CONSERVATION_TOL
    assert stepped.worst_plane[1] > 100.0 * ramped.worst_plane[1]
