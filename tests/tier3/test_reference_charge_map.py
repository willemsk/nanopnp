"""VAL-15: the delivered ClyA rho_q table, read as the reference model wrote it."""

from __future__ import annotations

from pathlib import Path

import pytest

from nanopnp.charge.fields import (
    CONSERVATION_TOL,
    RING_TOL,
    ChargeFieldError,
    check_conservation,
    conservation,
    load_field,
)
from nanopnp.core.constants import ELEMENTARY_CHARGE
from nanopnp.core.paths import REFERENCE_DATA_VARIABLE, reference_file
from nanopnp.mesh.reference import ReferenceGeometry
from nanopnp.numerics.measures import AXISYMMETRIC

TABLE = "prod5_clya_charge"

Q_NET_E = -72.0

GRID_SHAPE = (1401, 3401)

GRID_SPACING_NM = (0.005, 0.005)
GRID_ORIGIN_NM = (0.0, -3.5)

CONSUMER_LEG = 9.868e-3

table = reference_file(TABLE)
needs_archive = pytest.mark.skipif(
    table is None,
    reason=f"{TABLE} is not in ${REFERENCE_DATA_VARIABLE}; see the module docstring",
)


def _document(path: Path, target: Path) -> Path:
    target.write_text(
        "schema: nanopnp/field/v0.5\n"
        "name: rhoq_pore\n"
        "quantity: areal_charge_density\n"
        "units: e/m^2\n"
        f"q_net_e: {Q_NET_E}\n"
        "provenance:\n"
        "  source: prod5_clya_charge, the COMSOL model's own interpolation table\n"
        "  citation: Willems et al., Nanoscale 12, 16775-16795 (2020), ESI\n"
        f"data: {{path: {path}, format: comsolgrid}}\n"
        "grid:\n"
        f"  origin_nm: [{GRID_ORIGIN_NM[0]}, {GRID_ORIGIN_NM[1]}]\n"
        f"  spacing_nm: [{GRID_SPACING_NM[0]}, {GRID_SPACING_NM[1]}]\n"
        f"  shape: [{GRID_SHAPE[0]}, {GRID_SHAPE[1]}]\n",
        encoding="utf-8",
    )
    return target


@pytest.fixture(scope="module")
def field(tmp_path_factory: pytest.TempPathFactory):
    assert table is not None
    header = _document(table, tmp_path_factory.mktemp("field") / "rhoq_pore.yaml")
    return load_field(header)


@pytest.fixture(scope="module")
def mesh():
    return ReferenceGeometry.from_fixture().generate(check_quality=False)


@needs_archive
def test_val15_the_delivered_table_reads_with_the_grid_its_header_declares(field) -> None:
    assert field.grid.shape == GRID_SHAPE
    assert field.document.units == "e/m^2"
    (r_min, r_max), (z_min, z_max) = field.grid.extent_nm
    assert (r_min, r_max) == pytest.approx((0.0, 7.0), abs=1e-9)
    assert (z_min, z_max) == pytest.approx((-3.5, 13.5), abs=1e-9)


@needs_archive
def test_val15_the_delivered_table_carries_exactly_minus_seventy_two_e(field, mesh) -> None:
    q_grid_e = field.planar_integral_C() / ELEMENTARY_CHARGE
    assert q_grid_e == pytest.approx(Q_NET_E, rel=1e-9)
    report = conservation(field, mesh, AXISYMMETRIC)
    assert report.producer_error is not None
    assert abs(report.producer_error) < CONSERVATION_TOL


# PHY-16
@needs_archive
def test_val15_the_delivered_table_is_not_truncated(field) -> None:
    ring = field.grid.boundary_ring_maximum()
    interior = field.grid.interior_maximum()
    assert interior > 0.0
    assert ring.value / interior < 1e-20
    assert ring.value / interior < RING_TOL


# QR-03
@needs_archive
def test_val15_the_consumer_leg_on_the_reference_mesh_is_a_per_cent(field, mesh) -> None:
    report = conservation(field, mesh, AXISYMMETRIC)
    assert report.q_net_C is not None
    assert report.consumer_error == pytest.approx(CONSUMER_LEG, rel=0.05)
    assert abs(report.consumer_error) > CONSERVATION_TOL

    with pytest.raises(ChargeFieldError) as raised:
        check_conservation(report)
    assert "under-resolves the supplied field" in str(raised.value)
