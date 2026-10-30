"""VER-29: reading a supplied ``(r, z)`` field, and gating the charge it carries."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest
import yaml

from nanopnp.charge.fields import (
    CONSERVATION_TOL,
    QUADRATURE_REFINEMENT,
    RING_TOL,
    ChargeField,
    ChargeFieldError,
    ConservationReport,
    FieldDocument,
    FieldDocumentError,
    FormSpec,
    check_conservation,
    conservation,
    create_form,
    load_document,
    load_field,
)
from nanopnp.core.constants import ELEMENTARY_CHARGE
from nanopnp.density.grid import (
    GridFormatError,
    RadialGrid,
    RingMaximum,
    coefficient,
    read_grid,
    writable_formats,
    write_grid,
)
from nanopnp.numerics.measures import AXISYMMETRIC


def _has_griddata() -> bool:
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
    payload: dict[str, object] = {
        "schema": "nanopnp/field/v0.5",
        "name": "ring",
        "quantity": "areal_charge_density",
        "units": "C/m^2",
        "provenance": {"source": "analytic"},
        "form": spec.model_dump(),
        **overrides,
    }
    return FieldDocument.model_validate(payload)


def _field(spec: FormSpec, **overrides: object) -> ChargeField:
    document = _document(spec, **overrides)
    return ChargeField(document=document, grid=create_form(spec), source=__file__)  # type: ignore[arg-type]


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


def test_ver29_npz_round_trips_origin_and_spacing_bitwise(tmp_path):
    spacing = (0.1 + 0.2, 1.0 / 3.0)
    grid = RadialGrid(
        origin_nm=(0.0, -7.0 / 3.0),
        spacing_nm=spacing,
        values=np.arange(4 * 5, dtype=float).reshape(5, 4),
    )
    back = read_grid(write_grid(grid, tmp_path / "field.npz"))

    assert back.origin_nm == grid.origin_nm
    assert back.spacing_nm == grid.spacing_nm
    assert back.digest() == grid.digest()


def test_ver29_axes_only_npz_still_reads(tmp_path):
    path = tmp_path / "axes.npz"
    np.savez(
        path,
        r_nm=np.array([0.0, 0.5, 1.0]),
        z_nm=np.array([-1.0, 0.0]),
        values=np.ones((2, 3)),
    )
    back = read_grid(path)

    assert back.origin_nm == (0.0, -1.0)
    assert back.spacing_nm == (0.5, 1.0)


# IF-05
@needs_griddata
@pytest.mark.parametrize(
    ("name", "writer", "tolerance"), [("field.dx", "dx", 0.0), ("field.ccp4", "mrc", 1e-6)]
)
def test_ver29_a_grid_round_trips_through_opendx_and_ccp4(tmp_path, name, writer, tolerance):
    grid = RadialGrid.from_axes(
        np.array([1.0, 1.5, 2.0, 2.5]),
        np.array([0.0, 0.25, 0.5]),
        np.arange(12.0).reshape(3, 4),
    )

    assert writer in writable_formats()
    back = read_grid(write_grid(grid, tmp_path / name))

    assert back.shape == grid.shape
    assert back.origin_nm == pytest.approx(grid.origin_nm)
    assert back.spacing_nm == pytest.approx(grid.spacing_nm)
    np.testing.assert_allclose(back.values, grid.values, rtol=tolerance, atol=tolerance)


def test_ver29_the_value_array_is_checked_against_the_axes_it_belongs_to():
    r_nm, z_nm = np.array([0.0, 1.0, 2.0]), np.array([0.0, 1.0])
    values = np.array([[0.0, 10.0, 20.0], [1.0, 11.0, 21.0]])

    RadialGrid.from_axes(r_nm, z_nm, values)
    with pytest.raises(GridFormatError, match=r"\(3, 2\).*\(2, 3\)"):
        RadialGrid.from_axes(r_nm, z_nm, values.T)


def test_ver29_the_interpolant_reproduces_a_field_that_is_not_symmetric(mesh):
    r_nm, z_nm = np.linspace(0.0, 4.0, 5), np.linspace(0.0, 3.0, 4)
    values = 10.0 * r_nm[None, :] + z_nm[:, None]
    interpolant = coefficient(RadialGrid.from_axes(r_nm, z_nm, values))

    for r, z in ((1.0, 0.0), (0.0, 3.0), (3.5, 0.5), (0.5, 2.5)):
        assert interpolant(mesh(r, z)) == pytest.approx(10.0 * r + z, abs=1e-9)


def test_ver29_the_interpolant_is_zero_outside_the_grid_box(mesh):
    r_nm, z_nm = np.linspace(0.0, 2.0, 5), np.linspace(0.0, 2.0, 5)
    grid = RadialGrid.from_axes(r_nm, z_nm, np.full((5, 5), 7.0))

    padded = coefficient(grid)
    clamped = coefficient(grid, pad=False)

    assert padded(mesh(1.0, 1.0)) == pytest.approx(7.0)
    assert padded(mesh(4.0, 6.0)) == pytest.approx(0.0)
    assert clamped(mesh(4.0, 6.0)) == pytest.approx(7.0), "the raw continuation is not zero"


def test_ver29_the_comsol_grid_table_reads_as_delivered(tmp_path):
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


def test_ver29_declared_units_convert_onto_the_canonical_si_unit(tmp_path):
    grid = RadialGrid.from_axes(np.array([0.0, 1.0]), np.array([0.0, 1.0]), np.full((2, 2), 2.0))
    write_grid(grid, tmp_path / "ring.npz")
    (tmp_path / "field.yaml").write_text(
        "schema: nanopnp/field/v0.5\n"
        "name: ring\n"
        "quantity: areal_charge_density\n"
        "units: e/m^2\n"
        "provenance: {source: analytic}\n"
        "data: {path: ring.npz}\n",
        encoding="utf-8",
    )
    field = load_field(tmp_path / "field.yaml")

    assert field.grid.values[0, 0] == pytest.approx(2.0 * ELEMENTARY_CHARGE)


# QR-03
def test_ver29_conservation_against_an_analytic_net_charge(mesh):
    field = _field(_ring(), q_net_e=-12.0)
    report = check_conservation(conservation(field, mesh, AXISYMMETRIC, planes_nm=[2.0, 4.0, 6.0]))

    assert report.q_grid_C / ELEMENTARY_CHARGE == pytest.approx(-12.0, rel=1e-9)
    assert abs(report.producer_error) < 1e-9
    assert abs(report.consumer_error) < CONSERVATION_TOL
    assert report.worst_plane[1] < CONSERVATION_TOL
    assert report.summary()["interpolation"] == "bilinear"


# PHY-18
def test_ver29_the_axis_guard_deficit_is_reported_rather_than_assumed(mesh):
    field = _field(
        _ring(charge_e=-1.0, centre_r_nm=0.0, centre_z_nm=4.0),
        q_net_e=-0.5,
        axis_cutoff_nm=RING_WIDTH_NM,
    )

    deficit = field.guard_deficit_C() / ELEMENTARY_CHARGE
    assert field.planar_integral_C() / ELEMENTARY_CHARGE == pytest.approx(-0.5, rel=1e-6)
    assert deficit == pytest.approx(-0.5 * math.erf(1.0), rel=2e-4)

    report = conservation(field, mesh, AXISYMMETRIC, planes_nm=[4.0])
    residual = report.q_grid_C - report.guard_deficit_C
    assert abs(report.q_mesh_C - residual) < 5e-3 * abs(report.q_grid_C)


def test_ver29_the_projection_and_the_guard_apply_to_an_areal_density_only(mesh):
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


def test_ver29_charge_on_the_axis_column_is_not_a_truncation():
    r_nm, z_nm = np.linspace(0.0, 1.0, 11), np.linspace(0.0, 2.0, 21)
    values = np.zeros((z_nm.size, r_nm.size))
    values[10, 0] = 1.0
    values[10, 5] = 1.0e-9
    on_axis = RadialGrid.from_axes(r_nm, z_nm, values)
    assert on_axis.boundary_ring_maximum().value == 0.0

    off_axis = RadialGrid.from_axes(r_nm + 0.5, z_nm, values)
    ring = off_axis.boundary_ring_maximum()
    assert (ring.value, ring.r_nm, ring.z_nm) == (1.0, 0.5, 1.0)


def test_ver29_a_field_with_no_declared_charge_still_gates_the_consumer_leg(mesh):
    field = _field(_ring())
    report = check_conservation(conservation(field, mesh, AXISYMMETRIC, planes_nm=[4.0]))

    assert report.producer_error is None
    assert report.summary()["producer"] == {
        "status": "not run",
        "reason": "the field document declares no q_net_e",
    }
    assert report.reference_C == pytest.approx(abs(report.q_grid_C))
    assert abs(report.consumer_error) < CONSERVATION_TOL


def test_qr03_a_charge_stated_twice_with_opposite_signs_is_refused_when_read(tmp_path, mesh):
    def written(charge_e: float, **overrides: float) -> Path:
        path = tmp_path / "ring.field.yaml"
        payload = _document(_ring(charge_e=charge_e)).model_dump(by_alias=True, mode="json")
        payload.pop("q_net_e")
        path.write_text(yaml.safe_dump({**payload, **overrides}), encoding="utf-8")
        return path

    for charge_e, q_net_e in ((6.0, -6.0), (0.0, -6.0), (-6.0, 0.0)):
        with pytest.raises(FieldDocumentError) as raised:
            load_document(written(charge_e, q_net_e=q_net_e))
        assert "form.parameters.charge_e" in str(raised.value)
        assert "q_net_e" in str(raised.value)
    assert load_document(written(-6.0, q_net_e=-3.0)).q_net_e == -3.0
    assert load_document(written(6.0)).q_net_e is None

    field = _field(_ring(charge_e=-12.0), q_net_e=-6.0)
    report = conservation(field, mesh, AXISYMMETRIC, planes_nm=[2.0, 4.0, 6.0])
    with pytest.raises(ChargeFieldError) as raised:
        check_conservation(report)
    assert raised.value.gate.startswith("the supplied field does not carry the charge it declares")
    assert "form.parameters.charge_e" in str(raised.value)
    assert "q_net_e" in str(raised.value)


def _report(**overrides: object) -> ConservationReport:
    q_C = -12.0 * ELEMENTARY_CHARGE
    fields: dict[str, object] = {
        "q_net_C": q_C,
        "q_grid_C": q_C,
        "q_mesh_C": q_C,
        "q_mesh_refined_C": q_C,
        "guard_deficit_C": 0.0,
        "ring": RingMaximum(value=0.0, r_nm=10.0, z_nm=0.0),
        "interior_maximum": 1.0,
        "planes_nm": (2.0, 4.0, 6.0),
        "grid_cumulative_C": (0.0, q_C / 2, q_C),
        "mesh_cumulative_C": (0.0, q_C / 2, q_C),
        "ramp_nm": 0.1,
    }
    fields.update(overrides)
    return ConservationReport(**fields)  # type: ignore[arg-type]


# PHY-19
@pytest.mark.parametrize(
    ("overrides", "gate"),
    [
        (
            {"ring": RingMaximum(value=math.nan, r_nm=10.0, z_nm=3.0)},
            "the supplied grid is truncated",
        ),
        ({"q_mesh_refined_C": math.nan}, "the deployed mesh under-resolves the supplied field"),
        ({"q_grid_C": math.nan}, "the supplied field does not carry the charge it declares"),
        ({"q_mesh_C": math.nan}, "the deployed mesh under-resolves the supplied field"),
        (
            {"mesh_cumulative_C": (0.0, math.nan, -12.0 * ELEMENTARY_CHARGE)},
            "the cumulative charge disagrees with the source grid at a z plane",
        ),
    ],
)
def test_qr12_a_nan_leg_fails_the_conservation_gate(overrides, gate):
    check_conservation(_report())
    with pytest.raises(ChargeFieldError) as raised:
        check_conservation(_report(**overrides))
    assert raised.value.gate.startswith(gate)
    assert "nan" in raised.value.quantity


def test_qr12_a_nan_plane_is_the_worst_plane_wherever_it_sits():
    q_C = -12.0 * ELEMENTARY_CHARGE
    report = _report(mesh_cumulative_C=(1e-3 * q_C, math.nan, q_C))
    plane, error = report.worst_plane
    assert plane == 4.0
    assert math.isnan(error)


# PHY-16
def test_ver29_the_quadrature_check_compares_two_genuinely_different_orders():
    base = AXISYMMETRIC.integration_order(singular=True)
    naive = AXISYMMETRIC.integration_order(singular=True, extra=QUADRATURE_REFINEMENT)
    refined = AXISYMMETRIC.integration_order(
        singular=True,
        extra=AXISYMMETRIC.bonus_order(singular=True) + QUADRATURE_REFINEMENT,
    )

    assert naive == base, "the trap this constant exists to avoid"
    assert refined == base + QUADRATURE_REFINEMENT


def test_ver29_the_charge_grid_key_names_the_lattice_record_so_an_axes_only_entry_misses() -> None:
    from nanopnp.charge.kernel import LATTICE_RECORD, kernel_parameters
    from nanopnp.io.artefact import ChargeGridArtefact

    parameters = kernel_parameters(sharpness=1.0, spacing_nm=0.05, shift_z_nm=0.0)
    legacy = {name: value for name, value in parameters.items() if name != "lattice_record"}
    assert parameters["lattice_record"] == LATTICE_RECORD
    moved = ChargeGridArtefact(parameters=parameters, protonation_hash="p")
    assert moved.hash != ChargeGridArtefact(parameters=legacy, protonation_hash="p").hash


def test_ver29_a_non_uniform_axis_is_refused_rather_than_resampled():
    with pytest.raises(GridFormatError, match="not uniformly ascending"):
        RadialGrid.from_axes(np.array([0.0, 1.0, 3.0]), np.array([0.0, 1.0]), np.zeros((2, 3)))


def test_ver30_an_absolute_permittivity_field_is_refused_naming_the_blend():
    with pytest.raises(ValueError, match=r"eps_r,f\^c|concentration dependence"):
        _document(_ring(), quantity="relative_permittivity", units="1")


def test_ver29_units_are_checked_against_the_quantity_they_belong_to():
    with pytest.raises(ValueError, match="do not belong to quantity"):
        _document(_ring(), units="C/m^3")


@pytest.mark.parametrize("key", ["q_net_e", "axis_cutoff_nm"])
@pytest.mark.parametrize("value", [math.nan, math.inf])
def test_ver29_a_header_value_that_is_not_finite_is_refused(key, value):
    with pytest.raises(ValueError, match=key):
        _document(_ring(), **{key: value})


def test_ver29_a_declared_grid_descriptor_is_checked_against_the_data(tmp_path):
    grid = RadialGrid.from_axes(np.array([0.0, 1.0]), np.array([0.0, 1.0]), np.zeros((2, 2)))
    write_grid(grid, tmp_path / "ring.npz")
    (tmp_path / "field.yaml").write_text(
        "schema: nanopnp/field/v0.5\n"
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
