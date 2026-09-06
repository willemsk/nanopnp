"""VAL-15: the delivered ClyA ``rho_q`` table, read as the reference model wrote it.

The Tier-1 and Tier-2 conservation tests are built on synthetic fields whose
``Q_net`` is known exactly by construction. That verifies the machinery and
verifies nothing about the *reference's own* input, which is what this file
reads: ``prod5_clya_charge``, the 77 MB ``%Grid``/``%Data`` table the published
COMSOL model interpolates its fixed charge from.

Three things come out of it, and only the first two are gates:

1. the table integrates to ``-72.000000000 e``, to 5e-12 relative. The published
   pore charge is ``-72.9 e``; the exact integer settles what the delivered file
   is, and settles the units question with it -- the values are in ``e/m^2``,
   with the ``e_const`` of the COMSOL assembly expression supplying the coulombs,
   so the ``e`` that ``.knowledge/04`` section 3 transcribes inside the sum is
   not also in the file (no double count);
2. it is not truncated: its boundary ring is 24 orders below its interior
   maximum, so nothing is lost to the interpolant's zero padding;
3. its *consumer* leg on the WP8 reference mesh is one per cent, not the 1e-3
   QR-03 asks for -- and that is a property of the field, not of the mesh. The
   table's radial structure alternates sign on a ~0.035 nm scale, an order below
   the finest element WP8 places, so pointwise quadrature of the bilinear
   interpolant is aliased. Neither refining ``h`` (44,316 -> 3,463,372 elements)
   nor raising the quadrature order (8 -> 37) converges it; both wander at the
   1e-3 to 1e-2 level about the exact answer [tested]. Recorded here, with the
   numbers, because the fix belongs to the producer (deposit onto the finite
   element space and rescale, rather than sample an interpolant) and that is
   v0.9's stage 7, not this one.

That third measurement also answers what the plan raised as OPN-06. The
published ``-72.9 e`` sits +1.25 % from the table's exact ``-72 e``; our own
consumer leg on a comparable mesh sits -0.99 % from it by the same route. Same
size, same character, opposite sign -- which is what an aliasing error does. The
gap is the reference's own quadrature of its own table, not evidence that the
two numbers describe different constructs.

The archive is named by ``$NANOPNP_REFERENCE_DATA`` rather than vendored: the
table is far too large for the repository or the wheel, and a Tier-3 test that
could not run off the machine holding it would make the tier unrunnable rather
than skipped (section 7.1).
"""

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
from nanopnp.physics.measures import AXISYMMETRIC

TABLE = "prod5_clya_charge"
"""The delivered table's name within the reference archive."""

Q_NET_E = -72.0
"""What the delivered table integrates to, exactly (measured 4.68e-12 relative)."""

GRID_SHAPE = (1401, 3401)
"""``(n_r, n_z)``: 0 to 7 nm and -3.5 to 13.5 nm at 0.005 nm."""

GRID_SPACING_NM = (0.005, 0.005)
GRID_ORIGIN_NM = (0.0, -3.5)

CONSUMER_LEG = 9.868e-3
"""``Q_mesh`` against ``Q_grid`` on the WP8 reference mesh, at 44,316 elements.

Not a tolerance: a recorded measurement of a field this route cannot assemble to
QR-03's budget, with the docstring above for why. A change in it either way is a
change in the interpolation, the quadrature policy or the reference mesh, and
this is where it shows.
"""

table = reference_file(TABLE)
needs_archive = pytest.mark.skipif(
    table is None,
    reason=f"{TABLE} is not in ${REFERENCE_DATA_VARIABLE}; see the module docstring",
)


def _document(path: Path, target: Path) -> Path:
    """Write the header the delivered table is read through, and return it."""
    target.write_text(
        "schema: nanopnp/field/v1\n"
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
    """Return the delivered table, read through a header that declares its grid.

    The declared ``grid:`` block is checked against the file rather than used, so
    reading it at all asserts that the descriptor above is the delivered one.
    """
    assert table is not None  # guarded by ``needs_archive`` on every test
    header = _document(table, tmp_path_factory.mktemp("field") / "rhoq_pore.yaml")
    return load_field(header)


@pytest.fixture(scope="module")
def mesh():
    """Return the WP8 reference mesh, at the section 5.2.2 size fields."""
    return ReferenceGeometry.from_fixture().generate(check_quality=False)


@needs_archive
def test_val15_the_delivered_table_reads_with_the_grid_its_header_declares(field) -> None:
    """0.005 nm over ``r in [0, 7]``, ``z in [-3.5, 13.5]``, in ``e/m^2``."""
    assert field.grid.shape == GRID_SHAPE
    assert field.document.units == "e/m^2"
    (r_min, r_max), (z_min, z_max) = field.grid.extent_nm
    assert (r_min, r_max) == pytest.approx((0.0, 7.0), abs=1e-9)
    assert (z_min, z_max) == pytest.approx((-3.5, 13.5), abs=1e-9)


@needs_archive
def test_val15_the_delivered_table_carries_exactly_minus_seventy_two_e(field, mesh) -> None:
    """The producer leg on the reference's own file, and the units it settles.

    An exact integer to 5e-12 is not what a rounded transcription produces, and
    it is not what a table in coulombs would give either: read as ``C/m^2`` the
    same integral would be ``-72 C``. The delivered values are elementary
    charges per square metre, and the assembly expression's ``e_const`` is what
    turns them into coulombs.
    """
    q_grid_e = field.planar_integral_C() / ELEMENTARY_CHARGE
    assert q_grid_e == pytest.approx(Q_NET_E, rel=1e-9)
    # And through the gate's own decomposition rather than only by hand.
    report = conservation(field, mesh, AXISYMMETRIC)
    assert report.producer_error is not None
    assert abs(report.producer_error) < CONSERVATION_TOL


@needs_archive
def test_val15_the_delivered_table_is_not_truncated(field) -> None:
    """Its boundary ring is 24 orders below its interior maximum.

    PHY-16 step 4 asks the grid to extend at least 4 sigma beyond the structure.
    The delivered table does far better than that, which is worth knowing: the
    per-cent consumer leg below cannot be blamed on charge falling outside the
    box and being discarded by the interpolant's zero padding.
    """
    ring = field.grid.boundary_ring_maximum()
    interior = field.grid.interior_maximum()
    assert interior > 0.0
    assert ring.value / interior < 1e-20
    assert ring.value / interior < RING_TOL


@needs_archive
def test_val15_the_consumer_leg_on_the_reference_mesh_is_a_per_cent(field, mesh) -> None:
    """Recorded, not gated: this field is not assemblable to 1e-3 by this route.

    The gate is still *run*, and still fails, because a Tier-3 test that quietly
    lowered QR-03's budget for the one field that matters would be the exact
    failure section 7.3 forbids. What is asserted is the measurement and which
    gate catches it -- the quadrature-agreement gate, ahead of conservation,
    which is the gate that names the real cause.
    """
    report = conservation(field, mesh, AXISYMMETRIC)
    assert report.q_net_C is not None
    assert report.consumer_error == pytest.approx(CONSUMER_LEG, rel=0.05)
    assert abs(report.consumer_error) > CONSERVATION_TOL

    with pytest.raises(ChargeFieldError) as raised:
        check_conservation(report)
    assert "under-resolves the supplied field" in str(raised.value)
