"""The stabilisation registry and its parameters (VER-41, NUM-11, NUM-12, NUM-14, NUM-15).

Three claims are defended here, in order of how quietly they would break.

The first is that ``b~_i`` is the *same* advective velocity the Nernst-Planck
flux is built from. It is asserted against :func:`~nanopnp.physics.nernst_planck.species_flux`
itself, by algebra on the assembled expression rather than by reading both
functions: ``b~_i = (-J~_i - D~_i grad c~_i)/c~_i``. A stabilisation built on the
migration term alone would stabilise an operator the solver does not solve, and
nothing else in the suite would notice.

The second is that ``h_K`` is ``sqrt(2|K|)``. Every ``tau`` in the module is
defined against NGSolve's ``specialcf.mesh_size``, so its convention is measured
here rather than assumed: a change upstream would retune the whole mode with no
diagnostic.

The third is that the crosswind viscosity is identically zero on a mesh where
``C_cw Pe_K <= 1`` and bounded by ``D~_i (C_cw Pe_K - 1)`` above it. That is what
makes ``reference`` safe to switch on by default in Phase 1 without changing a
production answer, and it is asserted as an inequality on the coefficient
function, not on an integrated norm that could average a violation away.
"""

from dataclasses import dataclass, field

import ngsolve as ngs
import pytest

from nanopnp.materials.electrolyte import CorrectionSwitches, Electrolyte
from nanopnp.mesh.primitives import SlabGeometry
from nanopnp.physics import stabilisation as stab
from nanopnp.physics.coefficients import (
    SATURATED_WALL_DISTANCE_NM,
    NondimensionalCoefficients,
    mesh_unit_scales,
)
from nanopnp.physics.measures import Measures
from nanopnp.physics.nernst_planck import ConcentrationVariables, species_flux

CONCENTRATION_M = 1.0
REGISTERED = ("none", "reference", "supg")
"""Every selectable mode, sorted as :func:`registered_stabilisations` returns them."""

SAMPLE = (0.4, 0.3)
"""An interior point of the unit slab, away from any element boundary by luck."""


@pytest.fixture(scope="module")
def mesh() -> ngs.Mesh:
    """Return an unstructured planar slab; these tests interpolate, they do not solve."""
    return SlabGeometry(width_nm=1.0, height_nm=1.0).generate(maxh_nm=0.3)


def _state(
    mesh: ngs.Mesh,
    *,
    potential_slope: float = 1.0,
    steric: bool = False,
    with_velocity: bool = False,
    classical: bool = True,
    aligned_gradient: bool = False,
) -> stab.TransportState:
    """Return a ``Na+`` transport state with a prescribed, exactly linear potential.

    With ``classical`` switches every corrected property is its reference value,
    so ``D~`` and ``mu~`` are constants and the expected ``tau`` and ``nu_K`` are
    closed-form. The potential is interpolated into P2, where ``k r`` is exact, so
    ``grad(phi~) = (k, 0)`` to round-off rather than approximately.

    ``aligned_gradient`` makes ``grad c_Na`` parallel to the wind, which is the case
    where the Cauchy-Schwarz bound on ``nu_K`` is attained rather than strict.
    """
    scalar = ngs.H1(mesh, order=2)
    fields: dict[str, ngs.GridFunction] = {}
    # ``c_Na`` deliberately varies along *both* axes, so that its gradient is not
    # parallel to the wind: the Cauchy-Schwarz bound on ``nu_K`` is then strict
    # rather than attained, and a violation is a violation instead of round-off.
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
    variables = ConcentrationVariables.primitive(fields)
    coefficients = NondimensionalCoefficients(
        electrolyte=electrolyte,
        scales=mesh_unit_scales(electrolyte, CONCENTRATION_M),
        concentrations=variables.values,
        wall_distance_nm=SATURATED_WALL_DISTANCE_NM,
    )
    return stab.TransportState(
        species="Na+",
        coefficients=coefficients,
        variables=variables,
        potential=potential,
        velocity=velocity,
        steric=steric,
    )


def _flow_state(mesh: ngs.Mesh) -> stab.FlowState:
    """Return a flow state with interpolated velocity and pressure fields."""
    vector = ngs.VectorH1(mesh, order=2)
    scalar = ngs.H1(mesh, order=1)
    velocity = ngs.GridFunction(vector, name="u")
    velocity.Set(ngs.CF((0.3 + 0.1 * ngs.y, -0.2 * ngs.x)))
    pressure = ngs.GridFunction(scalar, name="p")
    pressure.Set(0.5 - ngs.y)
    transport = _state(mesh)
    return stab.FlowState(
        coefficients=transport.coefficients,
        velocity=velocity,
        pressure=pressure,
        body_force=ngs.CF((0.0, 0.0)),
    )


def _norm(vector: ngs.CoefficientFunction) -> ngs.CoefficientFunction:
    """Return ``||vector||``; the test's own arithmetic, not the module's helper."""
    return ngs.sqrt(vector * vector)


def _frobenius_squared(matrix: ngs.CoefficientFunction) -> ngs.CoefficientFunction:
    """Return ``sum_ij M_ij^2`` for a 2x2 matrix-valued expression."""
    total = matrix[0, 0] ** 2
    for index in ((0, 1), (1, 0), (1, 1)):
        total = total + matrix[index] ** 2
    return total


# -- h_K ------------------------------------------------------------------


def test_ver41_element_size_is_the_square_root_of_twice_the_element_area(
    mesh: ngs.Mesh,
) -> None:
    """``specialcf.mesh_size == sqrt(2|K|)`` elementwise (VER-41).

    Measured, not assumed: every stabilisation parameter in the module divides or
    multiplies by this length, so NGSolve's convention is a load-bearing fact and
    is pinned by a test that fails if it changes. The per-element value is
    recovered as the mean of the (piecewise constant) coefficient function over
    the element, which is exact for a constant.
    """
    areas = ngs.Integrate(ngs.CF(1.0), mesh, element_wise=True)
    sizes = ngs.Integrate(stab.element_size(), mesh, element_wise=True)
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
    """The 7 % gap to the edge length, recorded because the tuning constants absorb it.

    An equilateral triangle of side ``a`` has area ``sqrt(3) a^2 / 4``, so
    ``sqrt(2|K|) = a sqrt(sqrt(3)/2) = 0.9306 a``. Stated here so that a future
    switch to a direction-dependent ``h_b`` knows what it is replacing.
    """
    ratio = (3.0**0.5 / 2.0) ** 0.5
    assert ratio == pytest.approx(0.9306, abs=5e-5)


# -- the registry ---------------------------------------------------------


def test_num11_registry_lists_exactly_the_three_specified_modes() -> None:
    """``none``, ``supg`` and ``reference``; nothing else is selectable (NUM-11, NUM-13)."""
    assert stab.registered_stabilisations() == REGISTERED


def test_create_rejects_an_unknown_mode_and_lists_the_known_ones() -> None:
    """A case file naming ``streamline`` is told the three names it could have meant."""
    with pytest.raises(KeyError) as raised:
        stab.create("streamline")
    message = str(raised.value)
    assert "streamline" in message
    for name in REGISTERED:
        assert name in message


def test_register_refuses_to_shadow_an_existing_mode() -> None:
    """Re-registering a name would change what an existing case file means."""
    with pytest.raises(ValueError, match="already registered"):
        stab.register("reference", stab.NoStabilisation)


def test_phy22_off_is_a_named_model_that_assembles_nothing(mesh: ngs.Mesh) -> None:
    """``none`` returns ``None`` from both term builders and zero from the indicator.

    This is the structural half of the claim; the other half — that the residual a
    ``none`` run assembles is bit-for-bit the unstabilised one — is asserted on the
    assembled vector in ``test_physics_models.py``.
    """
    model = stab.create("none")
    assert isinstance(model, stab.NoStabilisation)
    state = _state(mesh)
    measures = Measures(symmetry="planar")
    assert model.transport_term(measures, trial=state, lagged=state, test=state.potential) is None
    assert model.indicator_term(measures, mesh, state=state, indicator=ngs.CF(1.0)) == 0.0
    assert model.parameters == {}
    assert model.provenance["mode"] == "none"
    assert model.provenance["terms"] == ""


def test_num14_reference_is_supg_with_both_further_terms_switched_on() -> None:
    """``reference`` is a *configuration* of the same class, not a second operator."""
    supg = stab.create("supg")
    reference = stab.create("reference")
    assert isinstance(reference, stab.StreamlineStabilisation)
    assert (supg.crosswind, supg.flow) == (False, False)
    assert (reference.crosswind, reference.flow) == (True, True)
    assert supg.terms == ("streamline",)
    assert reference.terms == ("streamline", "crosswind", "flow_gls", "grad_div")


def test_num03_only_the_mode_that_assembles_the_flow_term_permits_equal_order() -> None:
    """``permits_equal_order`` is read off the term built, not declared per class."""
    assert stab.create("none").permits_equal_order is False
    assert stab.create("supg").permits_equal_order is False
    assert stab.create("reference").permits_equal_order is True
    # And it follows the switch rather than the name, so a hand-built variant
    # cannot claim a legality it does not supply.
    assert stab.StreamlineStabilisation(crosswind=True, flow=False).permits_equal_order is False
    assert stab.StreamlineStabilisation(flow=True).permits_equal_order is True


def test_fr25_provenance_distinguishes_two_settings_of_the_same_mode() -> None:
    """``reference`` alone does not identify the operator; ``C_cw`` is reported too."""
    reference = stab.create("reference")
    assert reference.parameters["crosswind_coefficient"] == stab.CROSSWIND_COEFFICIENT
    assert reference.parameters["streamline_cutoff"] == stab.STREAMLINE_CUTOFF
    assert reference.parameters["grad_div_coefficient"] == stab.GRAD_DIV_COEFFICIENT
    retuned = stab.ReferenceStabilisation(crosswind_coefficient=0.35)
    assert retuned.parameters != reference.parameters
    # ``supg`` reports neither the crosswind nor the flow constants, because it
    # assembles neither: a parameter recorded for a term that is off would make an
    # ablation run indistinguishable from the full one (FR-25).
    assert "crosswind_coefficient" not in stab.create("supg").parameters
    assert "grad_div_coefficient" not in stab.create("supg").parameters
    assert stab.create("supg").provenance["crosswind_source"] == "off"
    assert stab.create("supg").provenance["flow_source"] == "off"


# -- b~_i -----------------------------------------------------------------


@pytest.mark.parametrize("steric", [False, True])
@pytest.mark.parametrize("with_velocity", [False, True])
def test_num14_advective_velocity_is_the_flux_bracket_of_species_flux(
    mesh: ngs.Mesh, steric: bool, with_velocity: bool
) -> None:
    """``b~_i = (-J~_i - D~_i grad c~_i)/c~_i``, term for term (PHY-04, PHY-05).

    The oracle is the flux the solver assembles, not a second reading of the
    equation: ``advective_velocity`` and
    :func:`~nanopnp.physics.nernst_planck.species_flux` are required to agree for
    every combination of the steric and convective switches. A stabilisation term
    built on a different wind is stabilising a different problem, and would show
    up nowhere else — least of all as a divergence.
    """
    state = _state(mesh, steric=steric, with_velocity=with_velocity)
    flux = species_flux(
        state.species,
        coefficients=state.coefficients,
        variables=state.variables,
        potential=state.potential,
        velocity=state.velocity,
        steric=state.steric,
    )
    concentration = state.variables.values[state.species]
    expected = (-flux - state.diffusivity * state.concentration_gradient) / concentration
    difference = stab.advective_velocity(state) - expected
    scale = ngs.Integrate(_norm(expected) ** 2, mesh, order=6)
    assert scale > 1e-6, "the comparison must not be against a vanishing wind"
    assert ngs.Integrate(difference * difference, mesh, order=6) == pytest.approx(
        0.0, abs=1e-24 * scale
    )


def test_num12_cell_peclet_is_the_wind_times_h_over_twice_the_diffusivity(
    mesh: ngs.Mesh,
) -> None:
    """``Pe_K = ||b~|| h_K / (2 D~)``, on the assembled wind rather than on ``|z grad phi|``.

    Section 6.4.1 prints ``Pe_h = 1/2 |z_i| |grad phi~| h~``, which assumes the
    Einstein relation ``mu~_i = D~_i``. PHY-14 forbids that at finite
    concentration, so the printed form is checked here to be the *classical*
    limit of this one and not its definition: with ``mu~/D~ = 1`` the two agree,
    and where they do not, this one is what the solver's own element Peclet number
    is (VER-05, NUM-12's NOTE).
    """
    slope = 3.0
    state = _state(mesh, potential_slope=slope)
    size = stab.element_size()
    expected = _norm(stab.advective_velocity(state)) * size / (2.0 * state.diffusivity)
    difference = stab.cell_peclet(state) - expected
    assert ngs.Integrate(difference**2, mesh, order=6) == pytest.approx(0.0, abs=1e-24)

    # The printed form differs from it by exactly mu~/D~, which is not 1.
    mobility = float(state.coefficients.mobility(state.species))
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
    """``tau_i = h_K^2/(4 D~_i)`` exactly where ``Pe_K <= 1``.

    Exactly, not approximately: the ``||b~_i||`` cancels, which is why the branch
    is written out rather than left as a ``min`` over a quotient that is ``0/0`` at
    zero wind. The artificial streamline diffusivity is then ``Pe_K^2 D~_i``, and
    that ratio is what section 6.4.1's ``zeta~^2/100`` estimate rests on.
    """
    state = _state(mesh, potential_slope=0.05)
    peclet = stab.cell_peclet(state)
    assert ngs.Integrate(ngs.IfPos(peclet - 1.0, 1.0, 0.0), mesh, order=6) == pytest.approx(
        0.0, abs=1e-14
    ), "the slope must keep every element below unit Peclet for this branch"
    expected = stab.element_size() ** 2 / (4.0 * state.diffusivity)
    difference = stab.streamline_parameter(state) - expected
    assert ngs.Integrate(difference**2, mesh, order=6) == pytest.approx(0.0, abs=1e-30)

    # tau ||b||^2 / D = Pe^2: the added diffusion measured against the physical one.
    wind = _norm(stab.advective_velocity(state))
    ratio = stab.streamline_parameter(state) * wind**2 / state.diffusivity
    assert ngs.Integrate((ratio - peclet**2) ** 2, mesh, order=6) == pytest.approx(0.0, abs=1e-30)


def test_num14_streamline_parameter_takes_the_convective_branch_above_unit_peclet(
    mesh: ngs.Mesh,
) -> None:
    """``tau_i = h_K/(2||b~_i||)`` where ``Pe_K > 1``."""
    state = _state(mesh, potential_slope=400.0)
    peclet = stab.cell_peclet(state)
    assert ngs.Integrate(ngs.IfPos(peclet - 1.0, 0.0, 1.0), mesh, order=6) == pytest.approx(
        0.0, abs=1e-14
    ), "the slope must carry every element above unit Peclet for this branch"
    wind = _norm(stab.advective_velocity(state))
    expected = stab.element_size() / (2.0 * wind)
    difference = stab.streamline_parameter(state) - expected
    assert ngs.Integrate(difference**2, mesh, order=6) == pytest.approx(0.0, abs=1e-30)


def test_num14_streamline_parameter_is_continuous_across_the_crossover(
    mesh: ngs.Mesh,
) -> None:
    """The two branches agree at ``Pe_K = 1`` to round-off.

    Approached from both sides at one point, with the slope solved for from the
    measured ``h_K`` and ``D~`` there rather than guessed: a discontinuous ``tau``
    would make the Newton residual jump as an element crosses the threshold, which
    the NUM-16 damping policy would read as a bad step.
    """
    point = mesh(*SAMPLE)
    unit = _state(mesh, potential_slope=1.0)
    wind_at_unit_slope = float(_norm(stab.advective_velocity(unit))(point))
    diffusivity = float(unit.diffusivity)
    size = float(stab.element_size()(point))
    critical = 2.0 * diffusivity / (size * wind_at_unit_slope)

    below = stab.streamline_parameter(_state(mesh, potential_slope=critical * (1.0 - 1e-9)))
    above = stab.streamline_parameter(_state(mesh, potential_slope=critical * (1.0 + 1e-9)))
    assert float(below(point)) == pytest.approx(float(above(point)), rel=1e-7)
    assert float(below(point)) == pytest.approx(size**2 / (4.0 * diffusivity), rel=1e-7)


# -- the crosswind --------------------------------------------------------


def test_num14_crosswind_viscosity_is_identically_zero_below_unit_cell_peclet(
    mesh: ngs.Mesh,
) -> None:
    """``nu_K = 0`` wherever ``C_cw Pe_K <= 1`` — everywhere on a NUM-30 mesh.

    Identically zero, as an integral of the square: this is what makes
    ``reference`` safe to enable without changing a production answer, and the
    claim is about the coefficient function rather than about a norm that could
    average a small violation away.
    """
    state = _state(mesh, potential_slope=0.05)
    viscosity = stab.crosswind_viscosity(state)
    assert ngs.Integrate(viscosity**2, mesh, order=8) == 0.0


def test_num14_crosswind_viscosity_is_positive_and_bounded_above_unit_cell_peclet(
    mesh: ngs.Mesh,
) -> None:
    """``0 < nu_K <= D~_i (C_cw Pe_K - 1)`` where the cell Peclet number exceeds one.

    The upper bound is Cauchy-Schwarz on ``R~_i = b~_i . grad c~_i`` and is the
    reason the term cannot run away: it adds at most the diffusivity that brings
    the effective cell Peclet number back to ``1/C_cw``. Asserted pointwise, as the
    integral of the positive part of the violation.
    """
    state = _state(mesh, potential_slope=400.0)
    viscosity = stab.crosswind_viscosity(state)
    assert ngs.Integrate(viscosity, mesh, order=8) > 0.0, "the term must actually switch on"

    bound = state.diffusivity * (stab.CROSSWIND_COEFFICIENT * stab.cell_peclet(state) - 1.0)
    violation = ngs.IfPos(viscosity - bound, viscosity - bound, 0.0)
    assert ngs.Integrate(violation, mesh, order=8) == 0.0

    # The bound is *attained* when the concentration gradient is parallel to the
    # wind, which is the worst case and the one the guarantee has to survive. Here
    # it is checked to round-off rather than as an inequality, because an inequality
    # that holds by a factor of two would not notice a mis-scaled parameter.
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
    """With ``b~_i = 0`` the term is off, not isotropic artificial diffusion.

    The projector degenerates to the identity at zero wind, so a residual-driven
    ``nu_K`` there would add diffusion in *every* direction — the one setting the
    reference model had explicitly off (NUM-14). The gate is on the wind, so a
    manufactured source cannot resurrect it either.
    """
    state = _state(mesh, potential_slope=0.0)
    assert ngs.Integrate(_norm(stab.advective_velocity(state)) ** 2, mesh, order=6) == 0.0
    source = ngs.CF(1.0e6)
    assert ngs.Integrate(stab.crosswind_viscosity(state, source=source) ** 2, mesh, order=8) == 0.0


def test_ver41_crosswind_projector_annihilates_the_wind_and_is_idempotent(
    mesh: ngs.Mesh,
) -> None:
    """``P_b b~_i = 0`` and ``P_b P_b = P_b``, both to round-off."""
    state = _state(mesh, potential_slope=7.0, with_velocity=True)
    projector = stab.crosswind_projector(state)
    wind = stab.advective_velocity(state)
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


def test_num14_approximate_residual_carries_the_source(mesh: ngs.Mesh) -> None:
    """``R~_i = b~_i . grad c~_i - s~_i``; dropping ``s~_i`` is the easy mistake.

    It is invisible in production, where ``s~_i = 0``, and shows up only as a
    manufactured-solution rate below 2 (VER-42) — so it is pinned here, where the
    failure is a one-line diagnostic instead of a convergence study.
    """
    state = _state(mesh, potential_slope=2.0)
    source = ngs.CF(0.75 + ngs.x)
    without = stab.approximate_residual(state)
    with_source = stab.approximate_residual(state, source=source)
    difference = with_source - (without - source)
    assert ngs.Integrate(difference**2, mesh, order=6) == pytest.approx(0.0, abs=1e-24)
    expected = stab.advective_velocity(state) * state.concentration_gradient
    assert ngs.Integrate((without - expected) ** 2, mesh, order=6) == pytest.approx(0.0, abs=1e-24)


# -- quadrature -----------------------------------------------------------


@dataclass(frozen=True)
class RecordingMeasures(Measures):
    """A ``Measures`` that records what each term asked for instead of integrating.

    The NUM-15 claim is about the *request*, not about the value: an integrand
    evaluated at order 4 and one evaluated at order 10 usually differ by less than
    any tolerance a test would set, so asserting on a number would pass whatever
    the mode asked for. Recording the call is the only way to see the deficit.
    """

    calls: list[tuple[bool, int]] = field(default_factory=list, compare=False)

    def volume(  # noqa: D102 - documented on the base class
        self,
        integrand: object,
        *,
        singular: bool = False,
        extra_order: int = 0,
        **kwargs: object,
    ) -> int:
        del integrand, kwargs
        self.calls.append((singular, extra_order))
        return 0


def test_num15_transport_terms_request_the_specified_integration_bonus(
    mesh: ngs.Mesh,
) -> None:
    """Streamline at bonus 4, crosswind at 6, neither declared singular (NUM-07, NUM-15)."""
    state = _state(mesh, potential_slope=2.0)
    measures = RecordingMeasures(symmetry="axisymmetric")
    stab.create("reference").transport_term(
        measures, trial=state, lagged=state, test=state.potential
    )
    assert measures.calls == [
        (False, stab.STREAMLINE_BONUS_ORDER),
        (False, stab.CROSSWIND_BONUS_ORDER),
    ]
    assert (stab.STREAMLINE_BONUS_ORDER, stab.CROSSWIND_BONUS_ORDER) == (4, 6)

    supg = RecordingMeasures(symmetry="axisymmetric")
    stab.create("supg").transport_term(supg, trial=state, lagged=state, test=state.potential)
    assert supg.calls == [(False, stab.STREAMLINE_BONUS_ORDER)]


def test_num07_only_the_grad_div_term_declares_the_singular_rule(mesh: ngs.Mesh) -> None:
    """Grad-div carries ``u_r/r`` and asks for the singular rule; the GLS pair does not.

    The approximate residual never forms the axisymmetric divergence, so three of
    the four new integrands carry no ``1/r`` factor at all. The fourth does, and
    declaring it is what raises the order past NGSolve's axis-sampling rule
    (VER-07). A later mode built on a full residual has to revisit this.
    """
    flow = _flow_state(mesh)
    measures = RecordingMeasures(symmetry="axisymmetric")
    scalar = ngs.H1(mesh, order=1)
    vector = ngs.VectorH1(mesh, order=2)
    stab.create("reference").flow_term(
        measures,
        trial=flow,
        lagged=flow,
        velocity_test=ngs.GridFunction(vector),
        pressure_test=ngs.GridFunction(scalar),
    )
    assert measures.calls == [
        (False, stab.FLOW_BONUS_ORDER),
        (False, stab.FLOW_BONUS_ORDER),
        (True, stab.FLOW_BONUS_ORDER),
    ]


def test_num11_supg_assembles_no_flow_term(mesh: ngs.Mesh) -> None:
    """``supg`` is the transport streamline term alone, which is why it is not equal-order."""
    flow = _flow_state(mesh)
    measures = RecordingMeasures(symmetry="axisymmetric")
    scalar = ngs.H1(mesh, order=1)
    vector = ngs.VectorH1(mesh, order=2)
    assert (
        stab.create("supg").flow_term(
            measures,
            trial=flow,
            lagged=flow,
            velocity_test=ngs.GridFunction(vector),
            pressure_test=ngs.GridFunction(scalar),
        )
        is None
    )
    assert measures.calls == []


# -- what the terms do to the assembled residual --------------------------


def _coupled(mode: str) -> tuple[object, ngs.Mesh, object, ngs.GridFunction]:
    """Return a flow-coupled model, a small mesh, its space and a non-trivial state.

    The state matters: at the cold start ``phi~ = 0``, ``c~_i = 1`` and ``u~ = 0``,
    so ``b~_i``, ``R~_i`` and ``R~_m`` all vanish and every stabilisation term is
    identically zero. A test that asserted on that state would pass with the terms
    unwired, which is why the fields below are set to something with a gradient.
    """
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
    fields[models.POTENTIAL].Set(0.4 * ngs.y + 0.2 * ngs.x)
    fields["c_Na+"].Set(1.0 + 0.15 * ngs.x)
    fields["c_Cl-"].Set(1.0 - 0.1 * ngs.y)
    fields[models.VELOCITY].Set(ngs.CF((0.05 * ngs.x, 0.2)))
    fields[models.PRESSURE].Set(0.3 * ngs.y)
    return model, mesh, space, state


def _applied(
    model: object, space: object, at: ngs.GridFunction, *, lagged: bool = False
) -> ngs.BaseVector:
    """Return the residual of ``model`` applied at ``at``.

    ``lagged`` decides whether the state is handed to ``residual_form`` as the side
    the stabilisation parameters are read from. Both calls apply the form at the
    same vector either way, so the difference between them is the stabilisation and
    nothing else.
    """
    from nanopnp.physics.measures import AXISYMMETRIC

    extra = {"state": at} if lagged else {}
    form = ngs.BilinearForm(space)
    form += model.residual_form(space, AXISYMMETRIC, **extra)  # type: ignore[attr-defined]
    out = at.vec.CreateVector()
    form.Apply(at.vec, out)
    return out


def test_phy22_the_none_mode_assembles_the_unstabilised_residual_exactly() -> None:
    """``none`` is the unstabilised residual on the vector, not merely by its name.

    Asserted bit-for-bit: passing a state to a ``none`` model must change nothing at
    all, which is the guarantee that makes the mode a *configuration* rather than a
    code path and that keeps every pre-WP12 result reproducible (PHY-22, NUM-11).
    """
    model, _, space, state = _coupled("none")
    with_state = _applied(model, space, state, lagged=True)
    without = _applied(model, space, state)
    assert with_state.Norm() > 0.0
    assert (with_state - without).Norm() == 0.0


def test_num14_the_reference_mode_changes_the_assembled_residual() -> None:
    """The terms are actually assembled; a wiring that dropped them fails here."""
    plain, _, space, state = _coupled("none")
    stabilised, _, _, _ = _coupled("reference")
    difference = _applied(stabilised, space, state, lagged=True) - _applied(plain, space, state)
    reference_norm = _applied(plain, space, state).Norm()
    assert difference.Norm() > 1e-6 * reference_norm


def test_num14_the_stabilisation_leaves_the_poisson_row_untouched() -> None:
    """Only the transport and flow rows gain a term (NUM-11, NUM-14).

    Poisson is elliptic and unstabilised by construction — §6.4 stabilises the
    transport and flow equations and nothing else — so the potential block of the
    difference must be exactly zero while the others are not. A term added against
    the wrong test function would pass a norm test on the whole vector.
    """
    from nanopnp.physics.models import POTENTIAL

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


def test_num14_every_term_vanishes_at_a_state_with_no_wind() -> None:
    """At ``phi~ = 0``, ``c~_i = 1``, ``u~ = 0`` and ``p~ = 0`` the mode adds nothing.

    ``b~_i = 0`` there, and with a symmetric salt at bulk the body force and the
    momentum residual vanish too, so every parameter multiplies a zero residual.
    Worth pinning: it is what makes the entry rung of the NUM-18 ladder identical in
    every mode, and a term with a stray additive constant would break it.
    """
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


def test_num16_a_stabilised_assembly_without_a_state_is_refused() -> None:
    """The parameters must be lagged, so the state is not optional for a real mode.

    Building them from the trial functions would put ``max(0, .)`` and
    ``1/||grad c~_i||`` into the Jacobian, which the NUM-16 damping policy is not
    tuned for — a silent change of solver behaviour rather than a wrong answer, and
    therefore worth a refusal rather than a fallback.
    """
    from nanopnp.physics.measures import AXISYMMETRIC

    model, _, space, _ = _coupled("reference")
    with pytest.raises(ValueError, match="needs the solve state") as raised:
        model.residual_form(space, AXISYMMETRIC)  # type: ignore[attr-defined]
    for term in ("streamline", "crosswind", "flow_gls", "grad_div"):
        assert term in str(raised.value)
