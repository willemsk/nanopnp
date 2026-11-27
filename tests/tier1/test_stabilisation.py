"""The stabilisation registry and its parameters (VER-41, NUM-11, NUM-12, NUM-14, NUM-15)."""

import ngsolve as ngs
import pytest

from nanopnp.io.vocabulary import POTENTIAL, VELOCITY
from nanopnp.materials.electrolyte import CorrectionSwitches, Electrolyte
from nanopnp.mesh.primitives import SlabGeometry
from nanopnp.numerics.measures import Measures
from nanopnp.physics import kernel
from nanopnp.physics import stabilisation as stab
from nanopnp.physics.backend import NGSOLVE_OPERATORS, geometry_of
from nanopnp.physics.coefficients import (
    SATURATED_WALL_DISTANCE_NM,
    NondimensionalCoefficients,
    mesh_unit_scales,
)
from nanopnp.physics.coupled import COUPLED_TERMS, coupled_slots
from nanopnp.physics.nernst_planck import ConcentrationVariables, species_flux
from nanopnp.physics.steric import steric_form

CONCENTRATION_M = 1.0
TRANSPORT_TERMS = ("Nernst\N{EN DASH}Planck", "Steric flux", "Advection")
REGISTERED = ("none", "reference", "supg")

SAMPLE = (0.4, 0.3)


@pytest.fixture(scope="module")
def mesh() -> ngs.Mesh:
    return SlabGeometry(width_nm=1.0, height_nm=1.0).generate(maxh_nm=0.3)


def _built(
    mesh: ngs.Mesh,
    *,
    potential_slope: float = 1.0,
    steric: bool = False,
    with_velocity: bool = False,
    classical: bool = True,
    aligned_gradient: bool = False,
) -> tuple[kernel.Context, kernel.Side]:
    scalar = ngs.H1(mesh, order=2)
    fields: dict[str, ngs.GridFunction] = {}
    # c_Na varies along both axes, so grad c is not parallel to the wind (bound strict).
    sodium = 1.0 + 0.5 * ngs.x if aligned_gradient else 1.0 + 0.5 * ngs.x + 0.3 * ngs.y
    for name, expression in (("Na+", sodium), ("Cl-", 1.0 + 0.2 * ngs.y)):
        function = ngs.GridFunction(scalar, name=name)
        function.Set(expression)
        fields[name] = function
    potential = ngs.GridFunction(scalar, name="phi")
    potential.Set(potential_slope * ngs.x)

    velocity = None
    if with_velocity:
        vector = ngs.VectorH1(mesh, order=2)
        velocity = ngs.GridFunction(vector, name="u")
        velocity.Set(ngs.CF((0.3 + 0.1 * ngs.y, -0.2 * ngs.x)))

    switches = CorrectionSwitches.classical() if classical else None
    electrolyte = (
        Electrolyte.from_parameter_file(switches=switches)
        if switches is not None
        else Electrolyte.from_parameter_file()
    )
    variables = ConcentrationVariables.primitive(fields, NGSOLVE_OPERATORS)
    coefficients = NondimensionalCoefficients(
        electrolyte=electrolyte,
        scales=mesh_unit_scales(electrolyte, CONCENTRATION_M),
        concentrations=variables.values,
        wall_distance_nm=SATURATED_WALL_DISTANCE_NM,
    )
    functions = {POTENTIAL: potential, **{f"c_{name}": f for name, f in fields.items()}}
    if velocity is not None:
        functions[VELOCITY] = velocity
    side = kernel.Side(functions=functions, variables=variables, coefficients=coefficients)
    context = kernel.Context(
        ops=NGSOLVE_OPERATORS,
        geometry=geometry_of(mesh, Measures(symmetry="planar")),
        measures=Measures(symmetry="planar"),
        fluid=mesh.Materials(".*"),
        trial=side,
        lagged=side,
        tests={},
        inputs=kernel.Inputs(),
        steric=steric_form("borukhov") if steric else None,
        stabilisation=stab.create("none"),
        terms=tuple(term for term in COUPLED_TERMS if term.name in TRANSPORT_TERMS),
    )
    return context, side


def _state(mesh: ngs.Mesh, **options: bool | float) -> stab.TransportState:
    context, side = _built(mesh, **options)  # type: ignore[arg-type]
    return stab.transport_state(context, side, "Na+")


def _flow_state(mesh: ngs.Mesh) -> stab.FlowState:
    vector = ngs.VectorH1(mesh, order=2)
    scalar = ngs.H1(mesh, order=1)
    velocity = ngs.GridFunction(vector, name="u")
    velocity.Set(ngs.CF((0.3 + 0.1 * ngs.y, -0.2 * ngs.x)))
    pressure = ngs.GridFunction(scalar, name="p")
    pressure.Set(0.5 - ngs.y)
    _, side = _built(mesh)
    return stab.FlowState(
        velocity=velocity,
        pressure=pressure,
        density=1.0,
        viscosity=side.coefficients.viscosity(),
        reynolds=side.coefficients.reynolds,
        force=None,
        source=None,
        ops=NGSOLVE_OPERATORS,
        geometry=geometry_of(mesh, Measures(symmetry="planar")),
    )


def _norm(vector: ngs.CoefficientFunction) -> ngs.CoefficientFunction:
    return ngs.sqrt(vector * vector)


def _frobenius_squared(matrix: ngs.CoefficientFunction) -> ngs.CoefficientFunction:
    total = matrix[0, 0] ** 2
    for index in ((0, 1), (1, 0), (1, 1)):
        total = total + matrix[index] ** 2
    return total


# -- h_K ------------------------------------------------------------------


def test_ver41_element_size_is_the_square_root_of_twice_the_element_area(
    mesh: ngs.Mesh,
) -> None:
    areas = ngs.Integrate(ngs.CF(1.0), mesh, element_wise=True)
    sizes = ngs.Integrate(NGSOLVE_OPERATORS.element_size(), mesh, element_wise=True)
    assert len(areas) > 10, "the measurement needs an unstructured mesh, not one triangle"
    worst = 0.0
    for area, integral in zip(areas, sizes, strict=True):
        measured = integral / area
        expected = (2.0 * area) ** 0.5
        worst = max(worst, abs(measured - expected) / expected)
    assert worst < 1e-12, f"mesh_size is not sqrt(2|K|); worst relative deviation {worst:g}"


def test_ver41_element_size_is_about_93_per_cent_of_an_equilateral_edge(
    mesh: ngs.Mesh,
) -> None:
    ratio = (3.0**0.5 / 2.0) ** 0.5
    assert ratio == pytest.approx(0.9306, abs=5e-5)


# -- the registry ---------------------------------------------------------


# NUM-13
def test_num11_registry_lists_exactly_the_three_specified_modes() -> None:
    assert stab.registered_stabilisations() == REGISTERED


def test_create_rejects_an_unknown_mode_and_lists_the_known_ones() -> None:
    with pytest.raises(KeyError) as raised:
        stab.create("streamline")
    message = str(raised.value)
    assert "streamline" in message
    for name in REGISTERED:
        assert name in message


def test_register_refuses_to_shadow_an_existing_mode() -> None:
    with pytest.raises(ValueError, match="already registered"):
        stab.register("reference", stab.NoStabilisation)


def test_phy22_off_is_a_named_model_that_assembles_nothing(mesh: ngs.Mesh) -> None:
    model = stab.create("none")
    assert isinstance(model, stab.NoStabilisation)
    state, flow = _state(mesh), _flow_state(mesh)
    assert model.transport_contributions(trial=state, lagged=state, test=ngs.CF(1.0)) == {}
    assert (
        model.flow_contributions(
            trial=flow, lagged=flow, velocity_test=flow.velocity, pressure_test=flow.pressure
        )
        == {}
    )
    assert model.parameters == {}
    assert model.provenance["mode"] == "none"
    assert model.provenance["terms"] == ""


def test_num14_reference_is_supg_with_both_further_terms_switched_on() -> None:
    supg = stab.create("supg")
    reference = stab.create("reference")
    assert isinstance(reference, stab.StreamlineStabilisation)
    assert (supg.crosswind, supg.flow) == (False, False)
    assert (reference.crosswind, reference.flow) == (True, True)
    assert supg.terms == ("streamline",)
    assert reference.terms == ("streamline", "crosswind", "flow_gls", "grad_div")


def test_num03_only_the_mode_that_assembles_the_flow_term_permits_equal_order() -> None:
    assert stab.create("none").permits_equal_order is False
    assert stab.create("supg").permits_equal_order is False
    assert stab.create("reference").permits_equal_order is True
    assert stab.StreamlineStabilisation(crosswind=True, flow=False).permits_equal_order is False
    assert stab.StreamlineStabilisation(flow=True).permits_equal_order is True


def test_fr25_provenance_distinguishes_two_settings_of_the_same_mode() -> None:
    reference = stab.create("reference")
    assert reference.parameters["crosswind_coefficient"] == stab.CROSSWIND_COEFFICIENT
    assert reference.parameters["streamline_cutoff"] == stab.STREAMLINE_CUTOFF
    assert reference.parameters["grad_div_coefficient"] == stab.GRAD_DIV_COEFFICIENT
    retuned = stab.ReferenceStabilisation(crosswind_coefficient=0.35)
    assert retuned.parameters != reference.parameters
    # supg records no crosswind or flow constants: one recorded for an off term would make
    # an ablation run indistinguishable from the full one (FR-25).
    assert "crosswind_coefficient" not in stab.create("supg").parameters
    assert "grad_div_coefficient" not in stab.create("supg").parameters
    assert stab.create("supg").provenance["crosswind_source"] == "off"
    assert stab.create("supg").provenance["flow_source"] == "off"


# -- b~_i -----------------------------------------------------------------


# PHY-04, PHY-05
@pytest.mark.parametrize("steric", [False, True])
@pytest.mark.parametrize("with_velocity", [False, True])
def test_num14_advective_velocity_is_the_flux_bracket_of_species_flux(
    mesh: ngs.Mesh, steric: bool, with_velocity: bool
) -> None:
    context, side = _built(mesh, steric=steric, with_velocity=with_velocity)
    state = stab.transport_state(context, side, "Na+")
    flux = species_flux(
        state.species,
        coefficients=side.coefficients,
        variables=side.variables,
        potential=side.functions[POTENTIAL],
        velocity=side.functions.get(VELOCITY),
        steric=context.steric,
    )
    concentration = side.variables.values[state.species]
    expected = (-flux - state.diffusivity * state.gradient) / concentration
    difference = state.wind - expected
    scale = ngs.Integrate(_norm(expected) ** 2, mesh, order=6)
    assert scale > 1e-6, "the comparison must not be against a vanishing wind"
    assert ngs.Integrate(difference * difference, mesh, order=6) == pytest.approx(
        0.0, abs=1e-24 * scale
    )


# PHY-14, VER-05
def test_num12_cell_peclet_is_the_wind_times_h_over_twice_the_diffusivity(
    mesh: ngs.Mesh,
) -> None:
    slope = 3.0
    context, side = _built(mesh, potential_slope=slope)
    state = stab.transport_state(context, side, "Na+")
    size = NGSOLVE_OPERATORS.element_size()
    expected = _norm(state.wind) * size / (2.0 * state.diffusivity)
    difference = stab.cell_peclet(state) - expected
    assert ngs.Integrate(difference**2, mesh, order=6) == pytest.approx(0.0, abs=1e-24)

    # The printed form differs from it by exactly mu~/D~, which is not 1.
    mobility = float(side.coefficients.mobility(state.species))
    diffusivity = float(state.diffusivity)
    printed = 0.5 * slope * size
    ratio = ngs.Integrate(stab.cell_peclet(state) / printed, mesh, order=6) / ngs.Integrate(
        ngs.CF(1.0), mesh
    )
    assert ratio == pytest.approx(mobility / diffusivity, rel=1e-10)


# -- tau_i ----------------------------------------------------------------


def test_num14_streamline_parameter_takes_the_diffusive_branch_below_unit_peclet(
    mesh: ngs.Mesh,
) -> None:
    state = _state(mesh, potential_slope=0.05)
    peclet = stab.cell_peclet(state)
    assert ngs.Integrate(ngs.IfPos(peclet - 1.0, 1.0, 0.0), mesh, order=6) == pytest.approx(
        0.0, abs=1e-14
    ), "the slope must keep every element below unit Peclet for this branch"
    expected = NGSOLVE_OPERATORS.element_size() ** 2 / (4.0 * state.diffusivity)
    difference = stab.streamline_parameter(state) - expected
    assert ngs.Integrate(difference**2, mesh, order=6) == pytest.approx(0.0, abs=1e-30)

    # tau ||b||^2 / D = Pe^2: the added diffusion measured against the physical one.
    wind = _norm(state.wind)
    ratio = stab.streamline_parameter(state) * wind**2 / state.diffusivity
    assert ngs.Integrate((ratio - peclet**2) ** 2, mesh, order=6) == pytest.approx(0.0, abs=1e-30)


def test_num14_streamline_parameter_takes_the_convective_branch_above_unit_peclet(
    mesh: ngs.Mesh,
) -> None:
    state = _state(mesh, potential_slope=400.0)
    peclet = stab.cell_peclet(state)
    assert ngs.Integrate(ngs.IfPos(peclet - 1.0, 0.0, 1.0), mesh, order=6) == pytest.approx(
        0.0, abs=1e-14
    ), "the slope must carry every element above unit Peclet for this branch"
    wind = _norm(state.wind)
    expected = NGSOLVE_OPERATORS.element_size() / (2.0 * wind)
    difference = stab.streamline_parameter(state) - expected
    assert ngs.Integrate(difference**2, mesh, order=6) == pytest.approx(0.0, abs=1e-30)


# NUM-16
def test_num14_streamline_parameter_is_continuous_across_the_crossover(
    mesh: ngs.Mesh,
) -> None:
    point = mesh(*SAMPLE)
    unit = _state(mesh, potential_slope=1.0)
    wind_at_unit_slope = float(_norm(unit.wind)(point))
    diffusivity = float(unit.diffusivity)
    size = float(NGSOLVE_OPERATORS.element_size()(point))
    critical = 2.0 * diffusivity / (size * wind_at_unit_slope)

    below = stab.streamline_parameter(_state(mesh, potential_slope=critical * (1.0 - 1e-9)))
    above = stab.streamline_parameter(_state(mesh, potential_slope=critical * (1.0 + 1e-9)))
    assert float(below(point)) == pytest.approx(float(above(point)), rel=1e-7)
    assert float(below(point)) == pytest.approx(size**2 / (4.0 * diffusivity), rel=1e-7)


# VER-41
def test_num14_streamline_parameter_stays_continuous_when_the_cutoff_is_retuned(
    mesh: ngs.Mesh,
) -> None:
    cutoff = 2.5
    point = mesh(*SAMPLE)
    unit = _state(mesh, potential_slope=1.0)
    wind_at_unit_slope = float(_norm(unit.wind)(point))
    diffusivity = float(unit.diffusivity)
    size = float(NGSOLVE_OPERATORS.element_size()(point))
    critical = 2.0 * cutoff * diffusivity / (size * wind_at_unit_slope)

    below = stab.streamline_parameter(
        _state(mesh, potential_slope=critical * (1.0 - 1e-9)), cutoff=cutoff
    )
    above = stab.streamline_parameter(
        _state(mesh, potential_slope=critical * (1.0 + 1e-9)), cutoff=cutoff
    )
    assert float(below(point)) == pytest.approx(float(above(point)), rel=1e-7)
    assert float(below(point)) == pytest.approx(size**2 / (4.0 * cutoff * diffusivity), rel=1e-7)


# -- the crosswind --------------------------------------------------------


# NUM-30
def test_num14_crosswind_viscosity_is_identically_zero_below_unit_cell_peclet(
    mesh: ngs.Mesh,
) -> None:
    state = _state(mesh, potential_slope=0.05)
    viscosity = stab.crosswind_viscosity(state)
    assert ngs.Integrate(viscosity**2, mesh, order=8) == 0.0


def test_num14_crosswind_viscosity_is_positive_and_bounded_above_unit_cell_peclet(
    mesh: ngs.Mesh,
) -> None:
    state = _state(mesh, potential_slope=400.0)
    viscosity = stab.crosswind_viscosity(state)
    assert ngs.Integrate(viscosity, mesh, order=8) > 0.0, "the term must actually switch on"

    bound = state.diffusivity * (stab.CROSSWIND_COEFFICIENT * stab.cell_peclet(state) - 1.0)
    violation = ngs.IfPos(viscosity - bound, viscosity - bound, 0.0)
    assert ngs.Integrate(violation, mesh, order=8) == 0.0

    # The bound is attained when grad c is parallel to the wind; checked to round-off.
    aligned = _state(mesh, potential_slope=400.0, aligned_gradient=True)
    tight = stab.crosswind_viscosity(aligned)
    limit = aligned.diffusivity * (stab.CROSSWIND_COEFFICIENT * stab.cell_peclet(aligned) - 1.0)
    scale = ngs.Integrate(limit, mesh, order=8)
    assert scale > 0.0
    assert ngs.Integrate(tight - limit, mesh, order=8) == pytest.approx(0.0, abs=1e-12 * scale)
    assert ngs.Integrate(ngs.IfPos(-viscosity, 1.0, 0.0), mesh, order=8) == pytest.approx(
        0.0, abs=1e-14
    ), "nu_K is a viscosity and must never be negative"


def test_num14_crosswind_viscosity_is_switched_off_without_a_wind(mesh: ngs.Mesh) -> None:
    state = _state(mesh, potential_slope=0.0)
    assert ngs.Integrate(_norm(state.wind) ** 2, mesh, order=6) == 0.0
    source = ngs.CF(1.0e6)
    assert ngs.Integrate(stab.crosswind_viscosity(state, source=source) ** 2, mesh, order=8) == 0.0


def test_ver41_crosswind_projector_annihilates_the_wind_and_is_idempotent(
    mesh: ngs.Mesh,
) -> None:
    state = _state(mesh, potential_slope=7.0, with_velocity=True)
    projector = stab.crosswind_projector(state)
    wind = state.wind
    projected = projector * wind
    scale = ngs.Integrate(wind * wind, mesh, order=6)
    assert scale > 1e-6
    assert ngs.Integrate(projected * projected, mesh, order=6) == pytest.approx(
        0.0, abs=1e-24 * scale
    )
    idempotency = projector * projector - projector
    assert ngs.Integrate(_frobenius_squared(idempotency), mesh, order=6) == pytest.approx(
        0.0, abs=1e-24
    )


# VER-42
def test_num14_approximate_residual_carries_the_source(mesh: ngs.Mesh) -> None:
    state = _state(mesh, potential_slope=2.0)
    source = ngs.CF(0.75 + ngs.x)
    without = stab.approximate_residual(state)
    with_source = stab.approximate_residual(state, source=source)
    difference = with_source - (without - source)
    assert ngs.Integrate(difference**2, mesh, order=6) == pytest.approx(0.0, abs=1e-24)
    expected = state.wind * state.gradient
    assert ngs.Integrate((without - expected) ** 2, mesh, order=6) == pytest.approx(0.0, abs=1e-24)


# -- quadrature -----------------------------------------------------------


def _bonuses(families: tuple[str, ...]) -> list[tuple[bool, int]]:
    slots = coupled_slots(("Na+",), {"c_Na+", "velocity", "pressure"}, None, ())
    return [(slot.singular, slot.extra_order) for slot in slots if slot.family in families]


# NUM-07
def test_num15_transport_terms_request_the_specified_integration_bonus(
    mesh: ngs.Mesh,
) -> None:
    state = _state(mesh, potential_slope=2.0)
    test = ngs.GridFunction(ngs.H1(mesh, order=2))
    reference = stab.create("reference").transport_contributions(
        trial=state, lagged=state, test=test
    )
    assert tuple(reference) == stab.TRANSPORT_SLOTS
    assert _bonuses(stab.TRANSPORT_SLOTS) == [
        (False, stab.STREAMLINE_BONUS_ORDER),
        (False, stab.CROSSWIND_BONUS_ORDER),
    ]
    assert (stab.STREAMLINE_BONUS_ORDER, stab.CROSSWIND_BONUS_ORDER) == (4, 6)

    supg = stab.create("supg").transport_contributions(trial=state, lagged=state, test=test)
    assert tuple(supg) == ("streamline",)


# VER-07
def test_num07_only_the_grad_div_term_declares_the_singular_rule(mesh: ngs.Mesh) -> None:
    flow = _flow_state(mesh)
    scalar = ngs.H1(mesh, order=1)
    vector = ngs.VectorH1(mesh, order=2)
    contributions = stab.create("reference").flow_contributions(
        trial=flow,
        lagged=flow,
        velocity_test=ngs.GridFunction(vector),
        pressure_test=ngs.GridFunction(scalar),
    )
    assert tuple(contributions) == stab.FLOW_SLOTS
    assert _bonuses(stab.FLOW_SLOTS) == [
        (False, stab.FLOW_BONUS_ORDER),
        (False, stab.FLOW_BONUS_ORDER),
        (True, stab.FLOW_BONUS_ORDER),
    ]


def test_num11_supg_assembles_no_flow_term(mesh: ngs.Mesh) -> None:
    flow = _flow_state(mesh)
    scalar = ngs.H1(mesh, order=1)
    vector = ngs.VectorH1(mesh, order=2)
    assert (
        stab.create("supg").flow_contributions(
            trial=flow,
            lagged=flow,
            velocity_test=ngs.GridFunction(vector),
            pressure_test=ngs.GridFunction(scalar),
        )
        == {}
    )


# -- what the terms do to the assembled residual --------------------------


def _coupled(mode: str) -> tuple[object, ngs.Mesh, object, ngs.GridFunction]:
    from nanopnp.io.vocabulary import POTENTIAL, PRESSURE, VELOCITY
    from nanopnp.mesh.primitives import CylinderGeometry
    from nanopnp.physics import models

    mesh = CylinderGeometry(radius_nm=2.0, length_nm=4.0).generate(maxh_nm=1.0)
    model = models.create("pnp-ns", fluid="electrolyte", stabilisation=mode)
    boundaries = models.CoupledBoundaries(
        potential="end", concentration="end", velocity="wall", velocity_axis="axis"
    )
    space = model.space(mesh, boundaries)
    state = ngs.GridFunction(space, name="state")
    fields = {f.name: c for f, c in zip(model.fields, state.components, strict=True)}
    fields[POTENTIAL].Set(0.4 * ngs.y + 0.2 * ngs.x)
    fields["c_Na+"].Set(1.0 + 0.15 * ngs.x)
    fields["c_Cl-"].Set(1.0 - 0.1 * ngs.y)
    fields[VELOCITY].Set(ngs.CF((0.05 * ngs.x, 0.2)))
    fields[PRESSURE].Set(0.3 * ngs.y)
    return model, mesh, space, state


def _applied(
    model: object, space: object, at: ngs.GridFunction, *, lagged: bool = False
) -> ngs.BaseVector:
    from nanopnp.numerics.measures import AXISYMMETRIC

    extra = {"state": at} if lagged else {}
    form = ngs.BilinearForm(space)
    form += model.residual_form(space, AXISYMMETRIC, **extra)  # type: ignore[attr-defined]
    out = at.vec.CreateVector()
    form.Apply(at.vec, out)
    return out


# NUM-11
def test_phy22_the_none_mode_assembles_the_unstabilised_residual_exactly() -> None:
    model, _, space, state = _coupled("none")
    with_state = _applied(model, space, state, lagged=True)
    without = _applied(model, space, state)
    assert with_state.Norm() > 0.0
    assert (with_state - without).Norm() == 0.0


def test_num14_the_reference_mode_changes_the_assembled_residual() -> None:
    plain, _, space, state = _coupled("none")
    stabilised, _, _, _ = _coupled("reference")
    difference = _applied(stabilised, space, state, lagged=True) - _applied(plain, space, state)
    reference_norm = _applied(plain, space, state).Norm()
    assert difference.Norm() > 1e-6 * reference_norm


# NUM-11
def test_num14_the_stabilisation_leaves_the_poisson_row_untouched() -> None:
    from nanopnp.io.vocabulary import POTENTIAL

    plain, _, space, state = _coupled("none")
    stabilised, _, _, _ = _coupled("reference")
    unstabilised = _applied(plain, space, state)
    difference = unstabilised.CreateVector()
    difference.data = _applied(stabilised, space, state, lagged=True) - unstabilised
    blocks = {
        field.name: difference[space.Range(index)].Norm()
        for index, field in enumerate(plain.fields)  # type: ignore[attr-defined]
    }
    assert blocks[POTENTIAL] == 0.0
    for name, norm in blocks.items():
        if name != POTENTIAL:
            assert norm > 0.0, f"the {name!r} row gained no stabilisation term"


# NUM-18
def test_num14_every_term_vanishes_at_a_state_with_no_wind() -> None:
    from nanopnp.mesh.primitives import CylinderGeometry
    from nanopnp.physics import models

    mesh = CylinderGeometry(radius_nm=2.0, length_nm=4.0).generate(maxh_nm=1.0)
    boundaries = models.CoupledBoundaries(
        potential="end", concentration="end", velocity="wall", velocity_axis="axis"
    )
    plain = models.create("pnp-ns", fluid="electrolyte")
    stabilised = models.create("pnp-ns", fluid="electrolyte", stabilisation="reference")
    space = plain.space(mesh, boundaries)
    cold = plain.cold_state(mesh, boundaries)
    difference = _applied(stabilised, space, cold, lagged=True) - _applied(plain, space, cold)
    assert difference.Norm() == pytest.approx(0.0, abs=1e-20)


# NUM-18, QR-12, NUM-14
@pytest.mark.parametrize("mode", ["none", "supg", "reference"])
def test_ver41_the_linearisation_is_finite_at_the_zero_wind_cold_state(mode: str) -> None:
    import numpy as np

    from nanopnp.mesh.primitives import CylinderGeometry
    from nanopnp.numerics.measures import AXISYMMETRIC
    from nanopnp.physics import models

    mesh = CylinderGeometry(radius_nm=2.0, length_nm=4.0).generate(maxh_nm=1.0)
    boundaries = models.CoupledBoundaries(
        potential="end", concentration="end", velocity="wall", velocity_axis="axis"
    )
    model = models.create("pnp-ns", fluid="electrolyte", stabilisation=mode)
    space = model.space(mesh, boundaries)
    cold = model.cold_state(mesh, boundaries)

    form = ngs.BilinearForm(space)
    form += model.residual_form(space, AXISYMMETRIC, state=cold)
    form.AssembleLinearization(cold.vec)
    entries = np.asarray(form.mat.COO()[2])

    assert entries.size > 0
    assert np.isfinite(entries).all(), (
        f"the {mode!r} linearisation carries {int(np.isnan(entries).sum())} NaN and "
        f"{int(np.isinf(entries).sum())} infinite entries at the zero-wind cold state; "
        "a stabilisation parameter is taking the square root of an exactly-zero vector"
    )


def test_num16_a_stabilised_assembly_without_a_state_is_refused() -> None:
    from nanopnp.numerics.measures import AXISYMMETRIC

    model, _, space, _ = _coupled("reference")
    with pytest.raises(ValueError, match="needs the solve state") as raised:
        model.residual_form(space, AXISYMMETRIC)  # type: ignore[attr-defined]
    for term in ("streamline", "crosswind", "flow_gls", "grad_div"):
        assert term in str(raised.value)


def _diagnostic(mode: str, potential: ngs.CoefficientFunction) -> object:
    from nanopnp.io.vocabulary import POTENTIAL
    from nanopnp.numerics.gates import FieldSampler, PecletDiagnostic

    model, mesh, _, state = _coupled(mode)
    fields = {f.name: c for f, c in zip(model.fields, state.components, strict=True)}  # type: ignore[attr-defined]
    fields[POTENTIAL].Set(potential)
    return PecletDiagnostic(
        FieldSampler(mesh, materials="electrolyte"),
        model.cell_peclet(state, ngs.CF(1.0)),  # type: ignore[attr-defined]
    )


# NUM-11
@pytest.mark.parametrize("mode", ["none", "supg", "reference"])
def test_num12_the_peclet_diagnostic_warns_naming_the_species_value_and_place(
    mode: str, caplog: pytest.LogCaptureFixture
) -> None:
    diagnostic = _diagnostic(mode, 2.0 * ngs.y * ngs.y)
    with caplog.at_level("INFO", logger="nanopnp.numerics.gates"):
        found = diagnostic.report()  # type: ignore[attr-defined]

    assert found.maximum > 1.0
    assert found.species in ("Na+", "Cl-")
    assert 0.0 < found.exceeding_fraction < 1.0
    records = [r for r in caplog.records if r.levelname == "WARNING"]
    assert len(records) == 1
    message = records[0].getMessage()
    assert found.species in message
    assert f"{found.maximum:.4g}" in message
    assert f"{found.location[0]:.4g}" in message
    assert f"{found.location[1]:.4g}" in message
    assert "NUM-12" in message
    # Section 6.4.1's printed Pe_h assumes mu = D (Einstein); this one does not (PHY-14).
    assert "mu_i grad(phi~)" in message


def test_num12_the_peclet_diagnostic_is_silent_below_the_threshold(
    caplog: pytest.LogCaptureFixture,
) -> None:
    diagnostic = _diagnostic("reference", 0.4 * ngs.y + 0.2 * ngs.x)
    with caplog.at_level("INFO", logger="nanopnp.numerics.gates"):
        found = diagnostic.report()  # type: ignore[attr-defined]

    assert found.maximum < 1.0
    assert found.exceeding == 0
    assert found.exceeding_fraction == 0.0
    assert [r for r in caplog.records if r.levelname == "WARNING"] == []
    assert len(caplog.records) == 1


def test_num12_the_peclet_diagnostic_never_aborts_a_run() -> None:
    from nanopnp.numerics.gates import PecletDiagnostic

    assert not hasattr(PecletDiagnostic, "check")


# QR-12
def test_num12_the_peclet_diagnostic_refuses_an_empty_species_mapping() -> None:
    from nanopnp.numerics.gates import FieldSampler, PecletDiagnostic

    _, mesh, _, _ = _coupled("reference")
    diagnostic = PecletDiagnostic(FieldSampler(mesh, materials="electrolyte"), {})
    with pytest.raises(ValueError, match="given no species"):
        diagnostic.measure()


# PHY-14
def test_num12_the_peclet_measurement_reports_every_species_separately() -> None:
    diagnostic = _diagnostic("reference", 2.0 * ngs.y * ngs.y)
    found = diagnostic.measure()  # type: ignore[attr-defined]

    assert set(found.per_species) == {"Na+", "Cl-"}
    assert found.maximum == max(found.per_species.values())
    assert found.per_species[found.species] == found.maximum
    assert found.per_species["Na+"] != found.per_species["Cl-"]
    assert found.summary()["per_species"] == dict(found.per_species)
