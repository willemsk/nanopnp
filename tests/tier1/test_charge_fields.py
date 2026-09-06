"""VER-29: reading a supplied ``(r, z)`` field, and gating the charge it carries.

The unit half. What is checked here is everything that can be wrong before a
solve exists: the container's axis order, the formats, the header document, the
interpolant's support, and each gate of PHY-19 firing on a field built to fail
it. The whole-model half — the same machinery on the deployed ClyA reference
mesh — is ``tests/tier2/test_charge_conservation.py``.

Two of these tests exist because the obvious version of them passes on broken
code. A grid sampled where ``r = z`` agrees exactly with its own transpose, so
the interpolation test samples off the diagonal; and a quadrature-agreement check
written as ``extra_order=3`` evaluates a singular form at *exactly* the order it
already used, so the two sides agree to the last bit and the gate can only pass.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from nanopnp.charge.fields import (
    CONSERVATION_TOL,
    QUADRATURE_REFINEMENT,
    RING_TOL,
    ChargeField,
    ChargeFieldError,
    FieldDocument,
    FieldDocumentError,
    FormSpec,
    check_conservation,
    conservation,
    create_form,
    load_field,
    registered_forms,
)
from nanopnp.core.constants import ELEMENTARY_CHARGE
from nanopnp.density.grid import (
    GridFormatError,
    RadialGrid,
    coefficient,
    read_grid,
    write_grid,
)
from nanopnp.physics.measures import AXISYMMETRIC


def _has_griddata() -> bool:
    """Return whether GridDataFormats is installed (the ``structure`` extra)."""
    try:
        import gridData  # noqa: F401
    except ImportError:
        return False
    return True


needs_griddata = pytest.mark.skipif(
    not _has_griddata(), reason="OpenDX and CCP4 need GridDataFormats (the 'structure' extra)"
)


@pytest.fixture(scope="module")
def mesh():
    """Return a plain rectangle covering ``r in [0, 6]``, ``z in [0, 10]``, in nm."""
    import netgen.occ as occ
    import ngsolve as ngs

    face = occ.Rectangle(6.0, 10.0).Face()
    face.name = "electrolyte"
    return ngs.Mesh(occ.OCCGeometry(face, dim=2).GenerateMesh(maxh=0.15))


RING_WIDTH_NM = 0.3
"""Smearing width of the Tier-1 ring.

Wider than the reference's ``sigma R_i ~ 0.085 nm`` on purpose: these tests run
on a 0.15 nm mesh in seconds, and a 0.085 nm Gaussian on that mesh fails the
quadrature-agreement gate — correctly, and for a reason that has nothing to do
with what any of these tests is about. The reference width is exercised on the
reference mesh, in Tier 2.
"""


def _ring(charge_e: float = -12.0, **overrides: float) -> FormSpec:
    """Return one Gaussian ring of known total charge, on a 0.01 nm grid."""
    parameters = {
        "centre_r_nm": 2.0,
        "centre_z_nm": 4.0,
        "width_nm": RING_WIDTH_NM,
        "charge_e": charge_e,
        **overrides,
    }
    return FormSpec(
        name="gaussian_ring",
        parameters=parameters,
        origin_nm=(0.0, 0.0),
        spacing_nm=(0.01, 0.01),
        shape=(500, 900),
    )


def _document(spec: FormSpec, **overrides: object) -> FieldDocument:
    """Return a valid field document over an analytic form."""
    payload: dict[str, object] = {
        "schema": "nanopnp/field/v1",
        "name": "ring",
        "quantity": "areal_charge_density",
        "units": "C/m^2",
        "provenance": {"source": "analytic"},
        "form": spec.model_dump(),
        **overrides,
    }
    return FieldDocument.model_validate(payload)


def _field(spec: FormSpec, **overrides: object) -> ChargeField:
    """Return the charge field an analytic form describes."""
    document = _document(spec, **overrides)
    return ChargeField(document=document, grid=create_form(spec), source=__file__)  # type: ignore[arg-type]


# -- the container and its formats --------------------------------------------


def test_ver29_a_grid_round_trips_through_the_native_format(tmp_path):
    grid = RadialGrid.from_axes(
        np.array([0.0, 0.5, 1.0]),
        np.array([-1.0, 0.0]),
        np.array([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]),
    )
    written = write_grid(grid, tmp_path / "field.npz")
    back = read_grid(written)

    assert back.origin_nm == grid.origin_nm
    assert back.spacing_nm == pytest.approx(grid.spacing_nm)
    assert back.shape == (3, 2)
    np.testing.assert_array_equal(back.values, grid.values)
    assert back.digest() == grid.digest()


@needs_griddata
@pytest.mark.parametrize(("name", "tolerance"), [("field.dx", 0.0), ("field.ccp4", 1e-6)])
def test_ver29_a_grid_round_trips_through_opendx_and_ccp4(tmp_path, name, tolerance):
    """IF-05's interchange formats, with the singleton third axis.

    CCP4 is written through gridData's ``MRC`` writer — its registry has no
    ``CCP4`` entry at all — and that stores ``float32``, so the round trip is not
    bit-exact and the digest moves. Asserted rather than hidden: the native
    format is the working one.
    """
    grid = RadialGrid.from_axes(
        np.array([1.0, 1.5, 2.0, 2.5]),
        np.array([0.0, 0.25, 0.5]),
        np.arange(12.0).reshape(3, 4),
    )
    back = read_grid(write_grid(grid, tmp_path / name))

    assert back.shape == grid.shape
    assert back.origin_nm == pytest.approx(grid.origin_nm)
    assert back.spacing_nm == pytest.approx(grid.spacing_nm)
    np.testing.assert_allclose(back.values, grid.values, rtol=tolerance, atol=tolerance)


@needs_griddata
def test_ver29_a_genuinely_two_dimensional_array_is_refused_naming_its_shape(tmp_path):
    """GridData fails on a 2D array from inside its own writer; we say so first."""
    import gridData

    path = tmp_path / "flat.dx"
    gridData.Grid(
        grid=np.arange(24.0).reshape(4, 3, 2), origin=(0.0, 0.0, 0.0), delta=(1.0, 1.0, 1.0)
    ).export(str(path), file_format="DX")

    with pytest.raises(GridFormatError, match=r"\(4, 3, 2\)"):
        read_grid(path)


def test_ver29_the_value_array_is_checked_against_the_axes_it_belongs_to():
    """A transposed array is refused, naming both shapes.

    The check is the shape, and it is the only one available: a transposed grid
    raises nothing on its own and agrees with the intended one everywhere ``r``
    equals ``z``.
    """
    r_nm, z_nm = np.array([0.0, 1.0, 2.0]), np.array([0.0, 1.0])
    values = np.array([[0.0, 10.0, 20.0], [1.0, 11.0, 21.0]])

    RadialGrid.from_axes(r_nm, z_nm, values)
    with pytest.raises(GridFormatError, match=r"\(3, 2\).*\(2, 3\)"):
        RadialGrid.from_axes(r_nm, z_nm, values.T)


def test_ver29_the_interpolant_reproduces_a_field_that_is_not_symmetric(mesh):
    """``10 r + z`` off the diagonal, which is where a transposed grid differs."""
    r_nm, z_nm = np.linspace(0.0, 4.0, 5), np.linspace(0.0, 3.0, 4)
    values = 10.0 * r_nm[None, :] + z_nm[:, None]
    interpolant = coefficient(RadialGrid.from_axes(r_nm, z_nm, values))

    for r, z in ((1.0, 0.0), (0.0, 3.0), (3.5, 0.5), (0.5, 2.5)):
        assert interpolant(mesh(r, z)) == pytest.approx(10.0 * r + z, abs=1e-9)


def test_ver29_the_interpolant_is_zero_outside_the_grid_box(mesh):
    """The padding of :func:`coefficient`, against the clamped continuation.

    ``VoxelCoefficient`` continues by its box's edge value, which over a 250 nm
    reservoir would turn a residual edge value into a charge sheet a thousand
    times the grid's own footprint (section 5.3.1 NOTE).
    """
    r_nm, z_nm = np.linspace(0.0, 2.0, 5), np.linspace(0.0, 2.0, 5)
    grid = RadialGrid.from_axes(r_nm, z_nm, np.full((5, 5), 7.0))

    padded = coefficient(grid)
    clamped = coefficient(grid, pad=False)

    assert padded(mesh(1.0, 1.0)) == pytest.approx(7.0)
    assert padded(mesh(4.0, 6.0)) == pytest.approx(0.0)
    assert clamped(mesh(4.0, 6.0)) == pytest.approx(7.0), "the raw continuation is not zero"


def test_ver29_the_comsol_grid_table_reads_as_delivered(tmp_path):
    """The reference model's own ``%Grid``/``%Data`` table, in metres, row per z."""
    path = tmp_path / "table.txt"
    path.write_text(
        "%Grid\n0 5e-10 1e-9\n-1e-9 0 1e-9\n%Data\n1 2 3\n4 5 6\n7 8 9\n",
        encoding="utf-8",
    )
    grid = read_grid(path)

    assert grid.shape == (3, 3)
    assert grid.origin_nm == pytest.approx((0.0, -1.0))
    assert grid.spacing_nm == pytest.approx((0.5, 1.0))
    # Row per z, value per r: values[i_z, i_r], which is the container's order.
    assert grid.values[0, 2] == 3.0
    assert grid.values[2, 0] == 7.0


def test_ver29_a_comsol_table_with_ragged_rows_is_refused(tmp_path):
    path = tmp_path / "ragged.txt"
    path.write_text("%Grid\n0 1e-9\n0 1e-9\n%Data\n1 2\n3\n", encoding="utf-8")
    with pytest.raises(GridFormatError, match="different lengths"):
        read_grid(path)


def test_ver29_the_comsol_table_is_read_only(tmp_path):
    grid = RadialGrid.from_axes(np.array([0.0, 1.0]), np.array([0.0, 1.0]), np.zeros((2, 2)))
    with pytest.raises(GridFormatError, match="read-only"):
        write_grid(grid, tmp_path / "out.txt")


def test_ver29_a_non_uniform_axis_is_refused_rather_than_resampled():
    with pytest.raises(GridFormatError, match="not uniformly ascending"):
        RadialGrid.from_axes(np.array([0.0, 1.0, 3.0]), np.array([0.0, 1.0]), np.zeros((2, 3)))


# -- the header document ------------------------------------------------------


def test_if03_an_unknown_key_in_a_field_document_is_rejected_naming_it(tmp_path):
    path = tmp_path / "field.yaml"
    path.write_text(
        "schema: nanopnp/field/v1\n"
        "name: ring\n"
        "quantity: areal_charge_density\n"
        "units: C/m^2\n"
        "q_net: -72\n"
        "provenance: {source: analytic}\n"
        "data: {path: ring.npz}\n",
        encoding="utf-8",
    )
    with pytest.raises(FieldDocumentError, match="q_net"):
        load_field(path)


def test_ver30_an_absolute_permittivity_field_is_refused_naming_the_blend():
    """§4.4's NOTE by name, not "not one of the three quantities"."""
    with pytest.raises(ValueError, match=r"eps_r,f\^c|concentration dependence"):
        _document(_ring(), quantity="relative_permittivity", units="1")


def test_ver29_units_are_checked_against_the_quantity_they_belong_to():
    with pytest.raises(ValueError, match="do not belong to quantity"):
        _document(_ring(), units="C/m^3")


def test_ver29_declared_units_convert_onto_the_canonical_si_unit(tmp_path):
    """``e/m^2`` against ``C/m^2``: the erratum G5 made a validation matter.

    The reference table stores the charge sum *without* ``e`` and its COMSOL
    assembly multiplies by ``e_const``; a table read as C m^-2 would be wrong by
    1.6e-19 with nothing to say so.
    """
    grid = RadialGrid.from_axes(np.array([0.0, 1.0]), np.array([0.0, 1.0]), np.full((2, 2), 2.0))
    write_grid(grid, tmp_path / "ring.npz")
    (tmp_path / "field.yaml").write_text(
        "schema: nanopnp/field/v1\n"
        "name: ring\n"
        "quantity: areal_charge_density\n"
        "units: e/m^2\n"
        "provenance: {source: analytic}\n"
        "data: {path: ring.npz}\n",
        encoding="utf-8",
    )
    field = load_field(tmp_path / "field.yaml")

    assert field.grid.values[0, 0] == pytest.approx(2.0 * ELEMENTARY_CHARGE)


def test_ver29_a_document_naming_both_a_file_and_a_form_is_refused():
    with pytest.raises(ValueError, match="exactly one"):
        _document(_ring(), data={"path": "ring.npz"})


def test_ver29_a_declared_grid_descriptor_is_checked_against_the_data(tmp_path):
    grid = RadialGrid.from_axes(np.array([0.0, 1.0]), np.array([0.0, 1.0]), np.zeros((2, 2)))
    write_grid(grid, tmp_path / "ring.npz")
    (tmp_path / "field.yaml").write_text(
        "schema: nanopnp/field/v1\n"
        "name: ring\n"
        "quantity: solid_fraction\n"
        "units: '1'\n"
        "provenance: {source: analytic}\n"
        "data: {path: ring.npz}\n"
        "grid: {origin_nm: [0.0, 0.0], spacing_nm: [1.0, 1.0], shape: [3, 3]}\n",
        encoding="utf-8",
    )
    with pytest.raises(FieldDocumentError, match=r"shape \[3, 3\]"):
        load_field(tmp_path / "field.yaml")


def test_ver29_a_solid_fraction_is_refused_as_a_fixed_charge():
    with pytest.raises(FieldDocumentError, match=r"inputs\.eps_r"):
        _field(_ring(), quantity="solid_fraction", units="1")


def test_fr16_the_analytic_forms_are_a_named_registry():
    assert registered_forms() == ("gaussian_ring", "slab", "uniform")
    with pytest.raises(FieldDocumentError, match="gaussian_ring"):
        create_form(_ring().model_copy(update={"name": "not_a_form"}))
    with pytest.raises(FieldDocumentError, match="centre_z_nm"):
        create_form(_ring().model_copy(update={"parameters": {"centre_r_nm": 1.0}}))


# -- conservation and its gates ----------------------------------------------


def test_ver29_conservation_against_an_analytic_net_charge(mesh):
    """QR-03 on both legs, with ``Q_net`` known in closed form.

    A Gaussian ring integrates to its own charge over the whole plane, so the
    producer leg here measures the trapezium rule against exact arithmetic and
    nothing else — which is what makes the consumer leg attributable.
    """
    field = _field(_ring(), q_net_e=-12.0)
    report = check_conservation(conservation(field, mesh, AXISYMMETRIC, planes_nm=[2.0, 4.0, 6.0]))

    assert report.q_grid_C / ELEMENTARY_CHARGE == pytest.approx(-12.0, rel=1e-9)
    assert abs(report.producer_error) < 1e-9
    assert abs(report.consumer_error) < CONSERVATION_TOL
    assert report.worst_plane[1] < CONSERVATION_TOL
    assert report.summary()["interpolation"] == "bilinear"


def test_ver29_the_axis_guard_deficit_is_reported_rather_than_assumed(mesh):
    """PHY-18 deletes charge inside ``r < 0.01 nm``; the report says how much.

    Put on the axis on purpose. The reference structure's innermost atoms sit at
    ``r >~ 1.6 nm`` and the strip sees ``exp(-354)`` of peak, so a field that
    never touches the axis cannot tell a computed deficit from a hard-coded zero.
    """
    # A guard radius the mesh can resolve, so that the third route below means
    # something: at the reference's own 0.01 nm the guard is a fifteenth of an
    # element and no mesh integral can see its edge.
    field = _field(
        _ring(charge_e=-1.0, centre_r_nm=0.0, centre_z_nm=4.0),
        q_net_e=-0.5,
        axis_cutoff_nm=RING_WIDTH_NM,
    )

    # Both numbers are closed forms. The half-plane holds half a ring centred on
    # the axis, and the strip inside the guard holds ``q erf(a/w) / 2``.
    # The two tolerances differ by two decades, and that is the design's own
    # argument made visible: the whole-grid integral is a trapezium rule over a
    # range the field decays to zero at, so it has no Euler-Maclaurin boundary
    # terms and is exact beyond all orders; the guard's is a *partial* integral,
    # cut where the field is still steep, so it carries the usual O(h^2) term.
    deficit = field.guard_deficit_C() / ELEMENTARY_CHARGE
    assert field.planar_integral_C() / ELEMENTARY_CHARGE == pytest.approx(-0.5, rel=1e-6)
    assert deficit == pytest.approx(-0.5 * math.erf(1.0), rel=2e-4)

    # And the third route: the mesh integral is the grid's less exactly what the
    # guard deleted, which is what says the reported deficit is the charge the
    # solver actually discarded rather than a number computed beside it.
    # Against the reference charge, as QR-03 poses every tolerance here, and not
    # against the residual: what is left after the guard is a seventh of the
    # grid's charge, and a discontinuity the mesh cannot resolve — the guard's own
    # step, an element-scale jump — costs a fixed fraction of the *total*.
    report = conservation(field, mesh, AXISYMMETRIC, planes_nm=[4.0])
    residual = report.q_grid_C - report.guard_deficit_C
    assert abs(report.q_mesh_C - residual) < 5e-3 * abs(report.q_grid_C)


def test_ver29_the_projection_and_the_guard_apply_to_an_areal_density_only(mesh):
    """The declared quantity, not an inference: the two differ by ``2 pi r``."""
    spec = _ring()
    areal = _field(spec)
    volume = _field(spec, quantity="volume_charge_density", units="C/m^3")

    r, z = 2.0, 4.0
    raw = coefficient(create_form(spec))(mesh(r, z))
    assert areal.volume_density_C_m3()(mesh(r, z)) == pytest.approx(
        raw / (2.0 * math.pi * r * 1e-9)
    )
    assert volume.volume_density_C_m3()(mesh(r, z)) == pytest.approx(raw)
    assert areal.volume_density_C_m3()(mesh(0.005, z)) == 0.0
    assert volume.guard_deficit_C() == 0.0


def test_ver29_the_truncation_gate_names_the_ring_value_and_its_location(mesh):
    """A grid cut short before its field decayed, which the padding would hide."""
    spec = (
        _ring()
        .model_copy(
            update={"shape": (200, 200)},
        )
        .model_copy(
            update={
                "parameters": {
                    "centre_r_nm": 2.0,
                    "centre_z_nm": 1.0,
                    "width_nm": 0.5,
                    "charge_e": -12.0,
                }
            }
        )
    )
    field = _field(spec)
    report = conservation(field, mesh, AXISYMMETRIC, planes_nm=[1.0])

    assert report.ring_ratio > RING_TOL
    with pytest.raises(ChargeFieldError) as raised:
        check_conservation(report)
    assert raised.value.gate == "the supplied grid is truncated"
    assert "(r, z) = " in str(raised.value)


def test_ver29_a_field_with_no_declared_charge_still_gates_the_consumer_leg(mesh):
    """The producer leg records that it could not run; the consumer leg gates."""
    field = _field(_ring())
    report = check_conservation(conservation(field, mesh, AXISYMMETRIC, planes_nm=[4.0]))

    assert report.producer_error is None
    assert report.summary()["producer"] == {
        "status": "not run",
        "reason": "the field document declares no q_net_e",
    }
    assert report.reference_C == pytest.approx(abs(report.q_grid_C))
    assert abs(report.consumer_error) < CONSERVATION_TOL


def test_ver29_the_quadrature_check_compares_two_genuinely_different_orders():
    """The gate would otherwise pass by evaluating one computation twice.

    ``Measures.bonus_order`` takes ``max(extra, SINGULAR_MIN_ORDER)`` on a
    singular form, so ``extra_order=3`` on the ``1/r`` field of PHY-16 step 6 is
    the order it already used. The refinement is therefore measured from the
    bonus, and this is what says so.
    """
    base = AXISYMMETRIC.integration_order(singular=True)
    naive = AXISYMMETRIC.integration_order(singular=True, extra=QUADRATURE_REFINEMENT)
    refined = AXISYMMETRIC.integration_order(
        singular=True,
        extra=AXISYMMETRIC.bonus_order(singular=True) + QUADRATURE_REFINEMENT,
    )

    assert naive == base, "the trap this constant exists to avoid"
    assert refined == base + QUADRATURE_REFINEMENT
