"""VER-30: the supplied dielectric field and the blend it drives (section 4.4, PHY-20)."""

from __future__ import annotations

import numpy as np
import pytest

from nanopnp.charge.dielectric import (
    FLUID_MEAN_CEILING,
    SOLID_MEAN_FLOOR,
    SolidFractionField,
    load_solid_fraction,
    summary,
)
from nanopnp.charge.fields import (
    ChargeFieldError,
    FieldDocument,
    FieldDocumentError,
    FormSpec,
    create_form,
    load_document,
)
from nanopnp.materials.electrolyte import Electrolyte
from nanopnp.materials.fields import blend
from nanopnp.mesh.primitives import CylindricalPoreGeometry, SlabGeometry
from nanopnp.numerics.measures import AXISYMMETRIC
from nanopnp.physics import models
from nanopnp.physics.coefficients import (
    SATURATED_WALL_DISTANCE_NM,
    NondimensionalCoefficients,
    mesh_unit_scales,
)
from nanopnp.physics.nernst_planck import ConcentrationVariables

PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=8.0
)

MEMBRANE_PERMITTIVITY = {"membrane": 2.0}

CONCENTRATION_M = 1.0


@pytest.fixture(scope="module")
def mesh():
    return PORE.generate(maxh_nm=1.0)


def _slab_spec(**overrides: float) -> FormSpec:
    parameters = {
        "r_min_nm": PORE.pore_radius_nm,
        "r_max_nm": PORE.reservoir_radius_nm + 1.0,
        "z_min_nm": -PORE.half_thickness_nm,
        "z_max_nm": PORE.half_thickness_nm,
        "value": 1.0,
        **overrides,
    }
    return FormSpec(
        name="slab",
        parameters=parameters,
        origin_nm=(0.0, -12.0),
        spacing_nm=(0.05, 0.05),
        shape=(201, 481),
    )


def _document(**overrides: object) -> FieldDocument:
    payload: dict[str, object] = {
        "schema": "nanopnp/field/v0.5",
        "name": "chi",
        "quantity": "solid_fraction",
        "units": "1",
        "provenance": {"source": "analytic"},
        "form": _slab_spec().model_dump(),
        **overrides,
    }
    return FieldDocument.model_validate(payload)


def _field(values: np.ndarray | None = None, **overrides: object) -> SolidFractionField:
    from nanopnp.density.grid import RadialGrid

    document = _document(**overrides)
    grid = create_form(_slab_spec())
    if values is not None:
        grid = RadialGrid(
            origin_nm=grid.origin_nm, spacing_nm=grid.spacing_nm, values=values.copy()
        )
    return SolidFractionField(document=document, grid=grid, source=__file__)  # type: ignore[arg-type]


def test_ver30_an_absolute_permittivity_field_is_refused_naming_the_reason(tmp_path) -> None:
    header = tmp_path / "eps.yaml"
    header.write_text(
        "schema: nanopnp/field/v0.5\n"
        "name: eps\n"
        "quantity: relative_permittivity\n"
        "units: '1'\n"
        "provenance: {source: a COMSOL export}\n"
        "form: {name: uniform, parameters: {value: 20.0}, origin_nm: [0, 0], "
        "spacing_nm: [1, 1], shape: [2, 2]}\n",
        encoding="utf-8",
    )
    with pytest.raises(FieldDocumentError) as raised:
        load_solid_fraction(header)
    message = str(raised.value)
    assert "PHY-11" in message
    assert "solid fraction" in message
    assert "chi * eps_p + (1 - chi) * eps_r,f" in message


@pytest.mark.parametrize("quantity", ["permittivity", "eps_r", "epsilon_r", "dielectric"])
def test_ver30_every_spelling_of_an_absolute_permittivity_is_refused(quantity: str) -> None:
    with pytest.raises(ValueError, match="PHY-11"):
        _document(quantity=quantity)


def test_ver30_a_charge_field_supplied_as_the_dielectric_is_refused() -> None:
    with pytest.raises(FieldDocumentError) as raised:
        SolidFractionField(
            document=FieldDocument.model_validate(
                {
                    "schema": "nanopnp/field/v0.5",
                    "name": "rho",
                    "quantity": "areal_charge_density",
                    "units": "C/m^2",
                    "provenance": {"source": "analytic"},
                    "form": _slab_spec().model_dump(),
                }
            ),
            grid=create_form(_slab_spec()),
            source=__file__,  # type: ignore[arg-type]
        )
    assert "areal_charge_density" in str(raised.value)
    assert "solid_fraction" in str(raised.value)


def test_ver30_a_solid_fraction_outside_the_unit_interval_aborts_naming_where() -> None:
    field = _field()
    values = field.grid.values.copy()
    i_z, i_r = 300, 120
    values[i_z, i_r] = 1.4
    spoiled = _field(values)

    spoiled_r = float(spoiled.grid.r_nm[i_r])
    spoiled_z = float(spoiled.grid.z_nm[i_z])
    with pytest.raises(ChargeFieldError) as raised:
        spoiled.check_range()
    assert raised.value.gate == "the supplied solid fraction leaves [0, 1]"
    assert "1.4" in raised.value.quantity
    assert raised.value.location is not None
    assert f"{spoiled_r:.4g}" in raised.value.location
    assert f"{spoiled_z:.4g}" in raised.value.location
    field.check_range()


def test_ver30_the_worst_offender_is_the_one_reported() -> None:
    field = _field()
    values = field.grid.values.copy()
    values[100, 10] = 1.05
    values[300, 120] = -3.0
    with pytest.raises(ChargeFieldError) as raised:
        _field(values).check_range()
    assert "-3" in raised.value.quantity
    assert "2 samples" in raised.value.quantity


def test_ver30_a_nan_sample_leaves_the_unit_interval() -> None:
    field = _field()
    values = field.grid.values.copy()
    values[300, 120] = -3.0
    values[100, 10] = float("nan")
    with pytest.raises(ChargeFieldError) as raised:
        _field(values).check_range()
    assert "chi = nan" in raised.value.quantity
    assert "2 samples" in raised.value.quantity
    assert raised.value.location is not None
    assert f"{float(field.grid.r_nm[10]):.4g}" in raised.value.location


def test_ver30_the_sharp_field_registers_with_the_materials(mesh) -> None:
    means = _field().check_materials(mesh, AXISYMMETRIC, solids=MEMBRANE_PERMITTIVITY)
    by_material = {mean.material: mean for mean in means}
    assert set(by_material) == {"cis", "electrolyte", "membrane", "trans"}
    assert by_material["membrane"].branch == "solid"
    assert by_material["membrane"].mean == pytest.approx(1.0, abs=1e-3)
    for name in ("cis", "electrolyte", "trans"):
        assert by_material[name].branch == "fluid"
        assert by_material[name].mean == pytest.approx(0.0, abs=1e-3)


def test_ver30_an_inverted_solid_fraction_aborts_reporting_both_numbers(mesh) -> None:
    inverted = _field(1.0 - _field().grid.values)
    with pytest.raises(ChargeFieldError) as raised:
        inverted.check_materials(mesh, AXISYMMETRIC, solids=MEMBRANE_PERMITTIVITY)
    message = raised.value.quantity
    for name in ("cis", "electrolyte", "membrane", "trans"):
        assert f"{name!r} averages chi" in message
    assert f">= {SOLID_MEAN_FLOOR:g}" in message
    assert f"<= {FLUID_MEAN_CEILING:g}" in message


def test_ver30_a_transposed_field_aborts_on_the_material_means(mesh) -> None:
    grid = _field().grid
    transposed = np.zeros_like(grid.values)
    n = min(grid.values.shape)
    transposed[:n, :n] = grid.values[:n, :n].T
    with pytest.raises(ChargeFieldError, match="does not register"):
        _field(transposed).check_materials(mesh, AXISYMMETRIC, solids=MEMBRANE_PERMITTIVITY)


def test_ver30_the_exclusion_shell_takes_the_fluid_branch() -> None:
    from nanopnp.density.grid import RadialGrid

    mesh = SlabGeometry(width_nm=2.0, height_nm=1.0, exclusion_nm=0.25).generate(maxh_nm=0.2)
    grid = RadialGrid.from_axes(
        np.array([0.0, 2.0]), np.array([0.0, 1.0]), np.zeros((2, 2), dtype=np.float64)
    )
    field = SolidFractionField(document=_document(), grid=grid, source=__file__)  # type: ignore[arg-type]
    means = {
        mean.material: mean
        for mean in field.check_materials(mesh, AXISYMMETRIC, solids=MEMBRANE_PERMITTIVITY)
    }
    assert means["exclusion"].branch == "fluid"
    assert means["exclusion"].mean == pytest.approx(0.0, abs=1e-12)


def _coefficients(mesh) -> NondimensionalCoefficients:
    import ngsolve as ngs

    electrolyte = Electrolyte.from_parameter_file()
    space = ngs.H1(mesh, order=2)
    fields = {}
    for ion in electrolyte.species:
        bulk = ngs.GridFunction(space, name=ion.name)
        bulk.Set(1.0)
        fields[ion.name] = bulk
    variables = ConcentrationVariables.primitive(fields)
    return NondimensionalCoefficients(
        electrolyte=electrolyte,
        scales=mesh_unit_scales(electrolyte, CONCENTRATION_M),
        concentrations=variables.values,
        wall_distance_nm=SATURATED_WALL_DISTANCE_NM,
    )


def test_ver30_the_sharp_solid_fraction_reproduces_the_piecewise_assignment(mesh) -> None:
    import ngsolve as ngs

    model = models.create("epnp-ns", solid_permittivities=MEMBRANE_PERMITTIVITY)
    coefficients = _coefficients(mesh)
    piecewise = model.permittivity(mesh, coefficients)
    indicator = mesh.MaterialCF({"membrane": 1.0}, default=0.0)
    blended = model.permittivity(mesh, coefficients, solid_fraction=indicator)

    order = AXISYMMETRIC.integration_order(extra=6)
    difference = float(ngs.Integrate(ngs.sqrt((blended - piecewise) ** 2), mesh, order=order))
    scale = float(ngs.Integrate(ngs.sqrt(piecewise**2), mesh, order=order))
    assert scale > 0.0
    assert difference == pytest.approx(0.0, abs=1e-14 * scale)


def test_ver30_the_blend_is_a_convex_combination_of_the_two_branches(mesh) -> None:
    import ngsolve as ngs

    model = models.create("epnp-ns", solid_permittivities=MEMBRANE_PERMITTIVITY)
    coefficients = _coefficients(mesh)
    fluid = model.permittivity(mesh, coefficients, solid_fraction=ngs.CF(0.0))
    solid = model.permittivity(mesh, coefficients, solid_fraction=ngs.CF(1.0))
    half = model.permittivity(mesh, coefficients, solid_fraction=ngs.CF(0.5))

    order = AXISYMMETRIC.integration_order(extra=6)
    midpoint = float(
        ngs.Integrate(ngs.sqrt((half - 0.5 * (fluid + solid)) ** 2), mesh, order=order)
    )
    assert midpoint == pytest.approx(0.0, abs=1e-14)
    assert float(ngs.Integrate(ngs.sqrt((solid - fluid) ** 2), mesh, order=order)) > 0.0


def test_ver30_water_off_the_fluid_is_ion_free_water() -> None:
    mesh = SlabGeometry(width_nm=5.0, exclusion_nm=0.3).generate(maxh_nm=0.2)
    model = models.create("pnp", concentration_M=3.0, fluid="electrolyte")
    boundaries = models.CoupledBoundaries(
        potential="bulk", concentration="bulk", velocity="wall", velocity_axis="lateral"
    )
    state = model.cold_state(mesh, boundaries)
    fields = {
        field.name: component
        for field, component in zip(model.fields, state.components, strict=True)
    }
    coefficients = model.coefficients(model.concentration_variables(fields), 3.0)
    permittivity = model.permittivity(mesh, coefficients)
    reference = model.electrolyte.permittivity_0
    assert float(permittivity(mesh(0.15, 0.5))) * reference == 78.15
    assert float(permittivity(mesh(0.45, 0.5))) * reference < 60.0


def test_ver30_the_blend_goes_to_ion_free_water_in_a_solid_and_eps_p_in_the_fluid(
    mesh,
) -> None:
    import ngsolve as ngs

    model = models.create("epnp-ns", solid_permittivities=MEMBRANE_PERMITTIVITY)
    coefficients = _coefficients(mesh)
    reference = model.electrolyte.permittivity_0
    chi = 0.3
    blended = model.permittivity(mesh, coefficients, solid_fraction=ngs.CF(chi))
    eps_p = MEMBRANE_PERMITTIVITY["membrane"]
    fluid = float(coefficients.relative_permittivity()(mesh(1.8, 0.0))) * reference
    assert fluid < 78.0
    inside = float(blended(mesh(5.0, 0.0))) * reference
    beside = float(blended(mesh(1.8, 0.0))) * reference
    assert inside == pytest.approx(chi * eps_p + (1.0 - chi) * 78.15, rel=1e-12)
    assert beside == pytest.approx(chi * eps_p + (1.0 - chi) * fluid, rel=1e-12)


def test_ver30_the_solid_branch_off_the_solids_is_the_nearest_solids_eps_p(mesh) -> None:
    from nanopnp.materials.fields import nearest_solid_permittivity

    field = nearest_solid_permittivity(mesh, {"membrane": 2.0, "trans": 5.0})
    assert float(field(mesh(5.0, 0.0))) == 2.0
    assert float(field(mesh(4.0, -6.0))) == 5.0
    assert float(field(mesh(1.8, 0.0))) == 2.0
    assert float(field(mesh(0.2, -2.8))) == 5.0
    assert float(field(mesh(5.0, 3.5))) == 2.0
    assert nearest_solid_permittivity(mesh, {"trans": 5.0, "membrane": 2.0}) is field
    with pytest.raises(ValueError, match="no material of this mesh"):
        nearest_solid_permittivity(mesh, {"protein": 20.0})


def test_ver30_blend_takes_the_whole_solid_branch_not_one_constant() -> None:
    chi, solids, fluid = 0.25, 3.2, 78.0
    assert blend(chi, solids, fluid) == pytest.approx(0.25 * 3.2 + 0.75 * 78.0)
    assert blend(0.0, solids, fluid) == pytest.approx(fluid)
    assert blend(1.0, solids, fluid) == pytest.approx(solids)


# FR-25
def test_ver30_the_summary_records_the_grid_its_digest_and_the_means(mesh) -> None:
    field = _field()
    means = field.material_means(mesh, AXISYMMETRIC, solids=MEMBRANE_PERMITTIVITY)
    recorded = summary(field, means)

    assert recorded["quantity"] == "solid_fraction"
    assert recorded["interpolation"] == "bilinear"
    assert recorded["grid_digest"] == field.grid.digest()
    assert recorded["grid"] == field.grid.descriptor()
    materials = [entry["material"] for entry in recorded["material_means"]]  # type: ignore[index,union-attr]
    assert materials == ["cis", "electrolyte", "membrane", "trans"]


def test_ver30_a_dielectric_document_round_trips_through_a_file(tmp_path) -> None:
    header = tmp_path / "chi.yaml"
    spec = _slab_spec()
    header.write_text(
        "schema: nanopnp/field/v0.5\n"
        "name: chi\n"
        "quantity: solid_fraction\n"
        "units: '1'\n"
        "provenance: {source: analytic, notes: the sharp membrane indicator}\n"
        f"form: {{name: slab, parameters: {dict(spec.parameters)}, "
        f"origin_nm: {list(spec.origin_nm)}, spacing_nm: {list(spec.spacing_nm)}, "
        f"shape: {list(spec.shape)}}}\n",
        encoding="utf-8",
    )
    field = load_solid_fraction(header)
    assert load_document(header).quantity == "solid_fraction"
    assert field.grid.digest() == create_form(spec).digest()
    field.check_range()
