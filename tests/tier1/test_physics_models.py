"""The physics-model registry (PHY-21, PHY-22, PHY-23, FR-20, NUM-01, NUM-03)."""

from collections.abc import Iterator
from dataclasses import fields as dataclass_fields
from dataclasses import replace

import pytest

from nanopnp.io.vocabulary import (
    POTENTIAL,
    PRESSURE,
    VELOCITY,
)
from nanopnp.materials.electrolyte import CorrectionSwitches, Electrolyte
from nanopnp.mesh.primitives import ELECTROLYTE_DOMAINS
from nanopnp.physics import models
from nanopnp.physics.models import CoupledModel

SPECIFIED_MODELS = ("epnp-ns", "pnp-ns", "pnp", "pb", "pb-linear", "poisson")


def test_phy21_every_specified_model_is_registered() -> None:
    assert set(SPECIFIED_MODELS) <= set(models.registered_models())


def test_create_rejects_an_unknown_model_and_lists_the_known_ones() -> None:
    with pytest.raises(KeyError) as raised:
        models.create("epnpns")
    message = str(raised.value)
    assert "epnpns" in message
    for name in SPECIFIED_MODELS:
        assert name in message


def test_phy21_pnp_ns_is_epnp_ns_with_every_correction_off() -> None:
    extended = models.create("epnp-ns")
    classical = models.create("pnp-ns")
    assert type(classical) is type(extended) is CoupledModel

    assert classical.steric is False
    assert all(model.name == "none" for model in classical.electrolyte.corrections.values()), (
        "PNP-NS must select the 'none' correction model, not branch around the correction"
    )

    assert extended.steric is True
    assert any(model.name != "none" for model in extended.electrolyte.corrections.values())
    assert [field.name for field in classical.fields] == [field.name for field in extended.fields]


def test_phy21_pnp_is_the_coupled_model_without_the_flow_block() -> None:
    with_flow = models.create("epnp-ns")
    without = models.create("pnp")
    assert type(without) is CoupledModel
    assert without.flow is False
    names = [field.name for field in without.fields]
    assert VELOCITY not in names and PRESSURE not in names
    assert names == [field.name for field in with_flow.fields][: len(names)]


def test_num01_field_set_matches_the_specified_discretisation() -> None:
    model = models.create("epnp-ns")
    declared = {field.name: field for field in model.fields}
    assert declared[POTENTIAL].element == "h1"
    assert declared[POTENTIAL].order == 2
    assert declared[POTENTIAL].domain is None, "Poisson is solved over all of Omega (PHY-03)"
    for species in model.species:
        concentration = declared[f"c_{species}"]
        assert concentration.order == 2
        assert concentration.domain == ELECTROLYTE_DOMAINS
    assert declared[VELOCITY].element == "vector_h1"
    assert declared[VELOCITY].order == 2
    assert declared[PRESSURE].order == 1
    assert declared[VELOCITY].domain == declared[PRESSURE].domain == ELECTROLYTE_DOMAINS


def test_num03_equal_order_velocity_pressure_is_rejected_without_a_flow_stabilisation() -> None:
    electrolyte = Electrolyte.from_parameter_file()
    for mode in ("none", "supg"):
        with pytest.raises(ValueError, match="inf-sup") as raised:
            CoupledModel(electrolyte=electrolyte, order=2, pressure_order=2, stabilisation=mode)
        assert "reference" in str(raised.value), "the refusal must name the permitting mode"
        assert repr(mode) in str(raised.value)


# NUM-14
def test_num03_equal_order_velocity_pressure_is_accepted_in_the_reference_mode() -> None:
    electrolyte = Electrolyte.from_parameter_file()
    model = CoupledModel(
        electrolyte=electrolyte,
        order=2,
        velocity_order=1,
        pressure_order=1,
        stabilisation="reference",
    )
    declared = {field.name: field for field in model.fields}
    assert declared[POTENTIAL].order == 2
    assert declared[VELOCITY].order == 1
    assert declared[PRESSURE].order == 1
    # And the gate is on the *pair*, not on the mode: an equal-order pair is still
    # refused in ``none`` even when the velocity order is set explicitly.
    with pytest.raises(ValueError, match="inf-sup"):
        CoupledModel(electrolyte=electrolyte, order=2, velocity_order=1, pressure_order=1)


def test_num03_velocity_order_defaults_to_the_shared_element_order() -> None:
    electrolyte = Electrolyte.from_parameter_file()
    implicit = CoupledModel(electrolyte=electrolyte, order=3, pressure_order=2)
    explicit = CoupledModel(electrolyte=electrolyte, order=3, velocity_order=3, pressure_order=2)
    assert implicit.resolved_velocity_order == 3
    assert implicit.provenance["fields"] == explicit.provenance["fields"]
    assert implicit.provenance["elements"] == explicit.provenance["elements"]


def test_num06_axis_carries_only_the_radial_velocity_condition() -> None:
    model = models.create("epnp-ns")
    vocabulary = model.boundary_conditions
    assert vocabulary[POTENTIAL]["axis"] == "natural"
    for species in model.species:
        assert vocabulary[f"c_{species}"]["axis"] == "natural"
    assert "u_r = 0" in vocabulary[VELOCITY]["axis"]
    assert "natural" in vocabulary[VELOCITY]["axis"]


# PHY-08
def test_phy23_dielectric_gradient_forces_is_one_switch_and_defaults_off() -> None:
    model = models.create("epnp-ns")
    assert model.dielectric_gradient_forces is False, "PHY-22 default is off"
    switches = [
        field.name for field in dataclass_fields(CoupledModel) if "dielectric" in field.name
    ]
    assert switches == ["dielectric_gradient_forces"]


def test_phy23_dielectric_gradient_forces_cannot_use_the_log_branch() -> None:
    electrolyte = Electrolyte.from_parameter_file()
    with pytest.raises(ValueError, match="log branch"):
        CoupledModel(electrolyte=electrolyte, dielectric_gradient_forces=True, log_variables=True)


def test_fr25_provenance_records_every_deviation_from_the_validated_default() -> None:
    electrolyte = Electrolyte.from_parameter_file()
    default = CoupledModel(electrolyte=electrolyte)
    assert default.provenance["deviations_from_validated_default"] == []

    deviant = CoupledModel(electrolyte=electrolyte, dielectric_gradient_forces=True, inertia=False)
    recorded = deviant.provenance["deviations_from_validated_default"]
    # Named by case-file path, so the manifest's own diff (io/defaults.deviations)
    # and this one are comparable rather than merely both plausible.
    assert "physics.dielectric_gradient_forces" in recorded
    assert "physics.inertia" in recorded
    assert deviant.provenance["switches"]["steric"] is True


def test_fr25_provenance_records_the_stabilisation_mode() -> None:
    electrolyte = Electrolyte.from_parameter_file()
    assert CoupledModel(electrolyte=electrolyte).provenance["stabilisation"] == "none"
    assert (
        CoupledModel(electrolyte=electrolyte, stabilisation="supg").provenance["stabilisation"]
        == "supg"
    )
    with pytest.raises(ValueError, match="'streamline' is not a registered mode") as raised:
        CoupledModel(electrolyte=electrolyte, stabilisation="streamline")
    for mode in ("none", "supg", "reference"):
        assert mode in str(raised.value)


@pytest.fixture
def retuned_mode() -> Iterator[str]:
    from nanopnp.physics import stabilisation as stab

    name = "reference-cw035"
    stab.register(name, lambda: stab.ReferenceStabilisation(crosswind_coefficient=0.35))
    try:
        yield name
    finally:
        # No public counterpart to ``register``; the registry is process-global.
        del stab._REGISTRY[name]


def test_fr25_provenance_distinguishes_two_tunings_of_the_same_mode(retuned_mode: str) -> None:
    from nanopnp.core.hashing import content_hash

    electrolyte = Electrolyte.from_parameter_file()
    baseline = CoupledModel(electrolyte=electrolyte, stabilisation="reference")
    retuned = CoupledModel(electrolyte=electrolyte, stabilisation=retuned_mode)
    assert baseline.provenance["stabilisation_parameters"]["crosswind_coefficient"] == 1.0
    assert retuned.provenance["stabilisation_parameters"]["crosswind_coefficient"] == 0.35
    schema = "test/model-provenance/v1"
    assert content_hash(schema, baseline.provenance) != content_hash(schema, retuned.provenance)


def test_fr25_provenance_records_the_three_element_orders() -> None:
    electrolyte = Electrolyte.from_parameter_file()
    model = CoupledModel(
        electrolyte=electrolyte,
        order=2,
        velocity_order=1,
        pressure_order=1,
        stabilisation="reference",
    )
    assert model.provenance["elements"] == {
        "potential": 2,
        "concentration": 2,
        "velocity": 1,
        "pressure": 1,
    }
    assert model.provenance["stabilisation_provenance"]["terms"] == (
        "streamline,crosswind,flow_gls,grad_div"
    )


def test_fr20_a_model_declares_fields_boundaries_and_a_solve_strategy() -> None:
    for name in SPECIFIED_MODELS:
        model = models.create(name)
        assert model.name == name
        assert model.fields
        assert set(model.boundary_conditions) <= {field.name for field in model.fields}
        assert model.provenance["model"] == name
        assert callable(model.space)
        assert callable(model.cold_state)
        assert callable(model.residual_form)
        assert callable(model.solve)


def test_unknown_keywords_are_rejected_rather_than_dropped() -> None:
    model = models.create("pb")
    with pytest.raises(TypeError, match="unexpected keyword"):
        model.residual_form(None, None, debye_length_nm=1.0, tractions={})


def test_electrolyte_owns_the_steric_switch() -> None:
    electrolyte = Electrolyte.from_parameter_file(
        switches=replace(CorrectionSwitches.classical(), steric=True)
    )
    model = CoupledModel(electrolyte=electrolyte)
    assert model.steric is True
    assert model.provenance["switches"]["steric"] is True


# NUM-17
def test_num18_cold_state_starts_the_ions_at_bulk_not_at_zero() -> None:
    import ngsolve as ngs

    from nanopnp.mesh.primitives import CylinderGeometry

    model = models.create("pnp", classical=True, fluid="electrolyte")
    mesh = CylinderGeometry(radius_nm=2.0, length_nm=4.0).generate(maxh_nm=2.0)
    boundaries = models.CoupledBoundaries(potential="end", concentration="end")
    state = model.cold_state(mesh, boundaries)
    fields = {f.name: c for f, c in zip(model.fields, state.components, strict=True)}
    # Compared as *functions*, never coefficient by coefficient: the P2 basis is
    # hierarchical, so the constant 1 has vertex coefficients 1 and edge
    # coefficients 0 (see ``post/reaction_flux.py``).
    for species in model.species:
        concentration = fields[f"c_{species}"]
        assert ngs.Integrate((concentration - 1.0) ** 2, mesh) == pytest.approx(0.0, abs=1e-20)
    assert ngs.Integrate(fields[POTENTIAL] ** 2, mesh) == pytest.approx(0.0, abs=1e-20)


# PHY-24
def test_cold_state_rejects_concentrations_on_a_model_that_solves_none() -> None:
    from nanopnp.mesh.primitives import CylinderGeometry

    model = models.create("pb")
    mesh = CylinderGeometry(radius_nm=2.0, length_nm=4.0).generate(maxh_nm=2.0)
    boundaries = models.CoupledBoundaries(potential="end")
    with pytest.raises(TypeError, match="initial_concentrations"):
        model.cold_state(mesh, boundaries, initial_concentrations={"Na": 1.0})


def test_num18_surface_charge_enters_poisson_as_its_boundary_term() -> None:
    import ngsolve as ngs

    from nanopnp.mesh.primitives import CylinderGeometry
    from nanopnp.numerics.measures import AXISYMMETRIC

    surface_density = 0.37
    model = models.create("pnp", classical=True, fluid="electrolyte")
    mesh = CylinderGeometry(radius_nm=2.0, length_nm=4.0).generate(maxh_nm=1.0)
    boundaries = models.CoupledBoundaries(potential="end", concentration="end")
    state = model.cold_state(mesh, boundaries)
    space = state.space

    def applied(**extra: object) -> ngs.BaseVector:
        form = ngs.BilinearForm(space)
        form += model.residual_form(space, AXISYMMETRIC, **extra)
        out = state.vec.CreateVector()
        form.Apply(state.vec, out)
        return out

    difference = applied(surface_charge=surface_density) - applied()

    potential_test = space.TestFunction()[0]
    load = ngs.LinearForm(space)
    load += AXISYMMETRIC.surface(
        surface_density * potential_test, definedon=mesh.Boundaries("wall")
    )
    load.Assemble()
    residual_of_difference = (difference + load.vec).Norm()
    assert residual_of_difference == pytest.approx(0.0, abs=1e-12 * max(load.vec.Norm(), 1.0))
    assert load.vec.Norm() > 0.0, "the wall boundary must actually carry the term"


# NUM-25
def test_fr23_a_solve_carries_its_residual_and_distance_field_on_the_solution() -> None:
    import ngsolve as ngs

    from nanopnp.mesh.primitives import CylinderGeometry
    from nanopnp.numerics.measures import AXISYMMETRIC

    distance = ngs.x + 0.25
    model = models.create("pnp", classical=True, fluid="electrolyte")
    mesh = CylinderGeometry(radius_nm=2.0, length_nm=4.0).generate(maxh_nm=1.0)
    boundaries = models.CoupledBoundaries(potential="end", concentration="end")
    steps: list[object] = []
    solution = model.solve(
        mesh,
        AXISYMMETRIC,
        boundaries=boundaries,
        wall_distance_nm=distance,
        callback=steps.append,
        potential_values=mesh.BoundaryCF({"end": 0.0}),
    )
    assert solution.residual is not None
    assert solution.wall_distance_nm is distance
    assert len(steps) == solution.newton.iterations
