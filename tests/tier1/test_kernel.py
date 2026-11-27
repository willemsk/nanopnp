"""The kernel: one integral a slot, a term's own slots, one statement every reader (VER-81)."""

from __future__ import annotations

from dataclasses import replace

import ngsolve as ngs
import numpy as np
import pytest

from nanopnp.core.typing import Expression
from nanopnp.io.vocabulary import POTENTIAL, PRESSURE, VELOCITY
from nanopnp.materials.electrolyte import Electrolyte
from nanopnp.mesh.primitives import CoupledBoundaries, CylinderGeometry
from nanopnp.numerics.gates import PECLET_EXPRESSION
from nanopnp.numerics.measures import AXISYMMETRIC
from nanopnp.physics import kernel, stabilisation
from nanopnp.physics.backend import NGSOLVE_OPERATORS, geometry_of
from nanopnp.physics.coefficients import (
    SATURATED_WALL_DISTANCE_NM,
    NondimensionalCoefficients,
    mesh_unit_scales,
)
from nanopnp.physics.coupled import coupled_slots
from nanopnp.physics.models import CoupledModel, create
from nanopnp.physics.nernst_planck import ConcentrationVariables
from nanopnp.physics.stabilisation import create as create_stabilisation

FLUID = "electrolyte"
BOUNDARIES = CoupledBoundaries(
    potential="wall|end", concentration="wall|end", velocity="wall|end", velocity_axis="axis"
)
ROUND_OFF = 1.0e-12
OPS = NGSOLVE_OPERATORS


@pytest.fixture(scope="module")
def mesh() -> ngs.Mesh:
    return CylinderGeometry(radius_nm=2.0, length_nm=4.0).generate(maxh_nm=0.4)


def _applied(space: ngs.FESpace, integral: object, state: ngs.GridFunction) -> np.ndarray:
    form = ngs.BilinearForm(space)
    form += integral
    out = state.vec.CreateVector()
    form.Apply(state.vec, out)
    return np.array(out.FV().NumPy())


def _relative(new: np.ndarray, old: np.ndarray) -> float:
    return float(np.max(np.abs(new - old)) / np.max(np.abs(old)))


def _hand_context(mesh: ngs.Mesh, space: ngs.FESpace) -> kernel.Context:
    potential, concentration = space.TrialFunction()
    potential_test, concentration_test = space.TestFunction()
    variables = ConcentrationVariables(
        values={"s": concentration},
        gradients={"s": ngs.grad(concentration)},
        variables={"s": concentration},
    )
    electrolyte = Electrolyte.from_parameter_file()
    coefficients = NondimensionalCoefficients(
        electrolyte=electrolyte,
        scales=mesh_unit_scales(electrolyte, 0.1),
        concentrations={ion.name: concentration for ion in electrolyte.species},
        wall_distance_nm=SATURATED_WALL_DISTANCE_NM,
    )
    side = kernel.Side(
        functions={"phi": potential, "c": concentration},
        variables=variables,
        coefficients=coefficients,
    )
    return kernel.Context(
        ops=OPS,
        geometry=geometry_of(mesh, AXISYMMETRIC),
        measures=AXISYMMETRIC,
        fluid=mesh.Materials(FLUID),
        trial=side,
        lagged=side,
        tests={"phi": potential_test, "c": concentration_test},
        inputs=kernel.Inputs(),
        steric=None,
        stabilisation=create_stabilisation("none"),
    )


def _diffusion(context: kernel.Context) -> Expression:
    return OPS.grad(context.trial.functions["c"])


def _drift(context: kernel.Context, side: kernel.Side, species: str) -> Expression:
    del context, species
    return OPS.grad(side.functions["phi"])


def _negated_flux(total: Expression, context: kernel.Context) -> Expression:
    return -OPS.dot(total, OPS.grad(context.tests["c"]))


def test_ver81_one_slot_is_one_integral_where_term_by_term_moves_the_rule(
    mesh: ngs.Mesh,
) -> None:
    space = ngs.H1(mesh, order=2) * ngs.H1(mesh, order=2, definedon=mesh.Materials(FLUID))
    state = ngs.GridFunction(space)
    state.components[0].Set(0.3 * ngs.sin(0.7 * ngs.y) * (1.0 + 0.1 * ngs.x * ngs.x))
    state.components[1].Set(1.0 + 0.2 * ngs.cos(0.5 * ngs.y) * (1.0 - 0.05 * ngs.x * ngs.x))
    context = _hand_context(mesh, space)
    diffusion = kernel.KernelTerm(
        "diffusion", "PHY-04", contributions=(kernel.Contribution(kernel.FLUX, _diffusion),)
    )
    drift = kernel.KernelTerm("drift", "PHY-04", drift=_drift)
    slot = kernel.Slot(kernel.FLUX, "c", "fluid", _negated_flux, species="s")

    potential, concentration = space.TrialFunction()
    _, test = space.TestFunction()
    written = (
        -ngs.InnerProduct(
            ngs.grad(concentration) + concentration * ngs.grad(potential), ngs.grad(test)
        )
        * ngs.x
        * ngs.dx(definedon=mesh.Materials(FLUID))
    )
    reference = _applied(space, written, state)

    composed = _applied(space, kernel.compose((diffusion, drift), (slot,), context), state)
    apart = _applied(space, kernel.compose((diffusion,), (slot,), context), state) + _applied(
        space, kernel.compose((drift,), (slot,), context), state
    )
    assert _relative(composed, reference) <= ROUND_OFF
    assert _relative(apart, reference) > 1.0e-6


def _coupled_state(
    mesh: ngs.Mesh, **options: str | bool
) -> tuple[CoupledModel, ngs.FESpace, ngs.GridFunction]:
    model = create("epnp-ns", concentration_M=0.1, fluid=FLUID, **options)
    assert isinstance(model, CoupledModel)
    space = model.space(mesh, BOUNDARIES)
    state = ngs.GridFunction(space)
    r, z = ngs.x, ngs.y
    values = {
        POTENTIAL: 0.3 * ngs.sin(0.7 * z) * (1.0 + 0.1 * r * r),
        "c_Na+": 1.0 + 0.2 * ngs.cos(0.5 * z) * (1.0 - 0.05 * r * r),
        "c_Cl-": 1.0 - 0.15 * ngs.sin(0.4 * z) * (1.0 + 0.05 * r * r),
        VELOCITY: ngs.CF((0.02 * r * ngs.cos(0.3 * z), 0.04 * (1.0 - 0.1 * r * r))),
        PRESSURE: 0.01 * ngs.sin(0.6 * z) * (1.0 + 0.2 * r * r),
    }
    for field, component in zip(model.fields, state.components, strict=True):
        component.Set(values[field.name])
    return model, space, state


def _slot_vectors(
    model: CoupledModel,
    space: ngs.FESpace,
    state: ngs.GridFunction,
    terms: tuple[kernel.KernelTerm, ...],
) -> dict[str, np.ndarray]:
    mesh = space.mesh
    context = model.context(
        mesh,
        AXISYMMETRIC,
        trial=dict(zip((f.name for f in model.fields), space.TrialFunction(), strict=True)),
        tests=dict(zip((f.name for f in model.fields), space.TestFunction(), strict=True)),
    )
    slots = coupled_slots(model.species, [f.name for f in model.fields], None, ())
    return {
        name: _applied(space, integral, state)
        for name, integral in kernel.integrals(terms, slots, context)
    }


@pytest.mark.parametrize("left_out", ["Steric flux", "Advection", "Inertia", "Body force"])
def test_ver81_a_term_left_out_changes_its_own_slots_alone(mesh: ngs.Mesh, left_out: str) -> None:
    model, space, state = _coupled_state(mesh)
    terms = model.terms_in_force()
    (term,) = (term for term in terms if term.name == left_out)
    whole = _slot_vectors(model, space, state, terms)
    without = _slot_vectors(model, space, state, tuple(t for t in terms if t is not term))
    families = set(term.slots)
    for name, vector in whole.items():
        other = without.get(name, np.zeros_like(vector))
        if name.split(":")[0] in families:
            assert np.max(np.abs(vector - other)) > 1.0e-8 * np.max(np.abs(vector)), name
        else:
            assert np.array_equal(vector, other), name


DEFAULT_WIND = "z_i mu_i grad(phi~) + D_i beta_i - Pe u~"
FLUX_TERMS = ("Nernst\N{EN DASH}Planck", "Steric flux", "Advection", "Dielectric decrement")
FORCE_TERMS = ("Inertia", "Body force", "Dielectric-gradient force")
READERS: dict[str, str | bool] = {"dielectric_gradient_forces": True, "stabilisation": "reference"}


@pytest.fixture(scope="module")
def readers(
    mesh: ngs.Mesh,
) -> tuple[CoupledModel, ngs.GridFunction, kernel.Context, ngs.GridFunction]:
    model, _, state = _coupled_state(mesh, **READERS)
    indicator = ngs.GridFunction(ngs.H1(mesh, order=model.order))
    indicator.Set(0.25 * ngs.y + 0.03 * ngs.x * ngs.x)
    functions = dict(zip((f.name for f in model.fields), state.components, strict=True))
    tests = {f"c_{name}": indicator for name in model.species}
    context = model.context(mesh, AXISYMMETRIC, trial=functions, tests=tests)
    return model, state, context, indicator


def _l2_relative(mesh: ngs.Mesh, computed: Expression, expected: Expression) -> float:
    difference = computed - expected
    fluid = mesh.Materials(FLUID)
    error = ngs.Integrate(ngs.InnerProduct(difference, difference), mesh, order=8, definedon=fluid)
    scale = ngs.Integrate(ngs.InnerProduct(expected, expected), mesh, order=8, definedon=fluid)
    assert scale > 0.0, "the comparison must not be against a vanishing expression"
    return float(np.sqrt(abs(error) / scale))


def _drifts(context: kernel.Context, species: str) -> dict[str, Expression]:
    # PHY-04, PHY-05 and PHY-23's drifts written in NGSolve, from the coefficients alone.
    side = context.trial
    coefficients, variables = side.coefficients, side.variables
    potential = side.functions[POTENTIAL]
    field = ngs.grad(potential)
    permittivity = coefficients.relative_permittivity()
    names = list(variables.values)
    sensitivity = permittivity.Diff(variables.variables[species])
    sensitivity_gradient = sum(
        (
            sensitivity.Diff(variables.variables[name]) * variables.gradients[name]
            for name in names[1:]
        ),
        sensitivity.Diff(variables.variables[names[0]]) * variables.gradients[names[0]],
    )
    excess_gradient = -(
        2.0 * sensitivity * (potential.Operator("hesse") * field)
        + ngs.InnerProduct(field, field) * sensitivity_gradient
    ) / (2.0 * coefficients.screening)
    diffusivity = coefficients.diffusivity(species)
    valence = float(coefficients.electrolyte.ion(species).valence)
    assert context.steric is not None
    return {
        FLUX_TERMS[0]: valence * coefficients.mobility(species) * field,
        FLUX_TERMS[1]: diffusivity * context.steric(variables, coefficients, species),
        FLUX_TERMS[2]: -coefficients.peclet * side.functions[VELOCITY],
        FLUX_TERMS[3]: diffusivity * excess_gradient,
    }


def _sum(parts: list[Expression]) -> Expression:
    total = parts[0]
    for part in parts[1:]:
        total = total + part
    return total


@pytest.mark.parametrize("species", ["Na+", "Cl-"])
def test_ver81_the_wind_is_the_sum_of_the_drifts_written_once(
    mesh: ngs.Mesh,
    readers: tuple[CoupledModel, ngs.GridFunction, kernel.Context, ngs.GridFunction],
    species: str,
) -> None:
    _, _, context, _ = readers
    drifts = _drifts(context, species)
    expected = _sum(list(drifts.values()))
    wind = kernel.wind(context, context.trial, species)
    assert wind is not None
    assert _l2_relative(mesh, wind, expected) <= ROUND_OFF
    for name in FLUX_TERMS:
        without = replace(context, terms=tuple(t for t in context.terms if t.name != name))
        reduced = kernel.wind(without, context.trial, species)
        assert reduced is not None
        assert _l2_relative(mesh, reduced, expected - drifts[name]) <= ROUND_OFF, name
        assert _l2_relative(mesh, reduced, expected) > 1.0e-6, f"{name} adds no drift here"


def test_ver81_the_flow_force_is_the_sum_of_the_three_densities(
    mesh: ngs.Mesh,
    readers: tuple[CoupledModel, ngs.GridFunction, kernel.Context, ngs.GridFunction],
) -> None:
    model, _, context, _ = readers
    assert {t.name for t in context.terms} >= set(FORCE_TERMS)
    side = context.trial
    coefficients, variables = side.coefficients, side.variables
    velocity, field = side.functions[VELOCITY], ngs.grad(side.functions[POTENTIAL])
    density = 1.0 if side.density is None else side.density
    charge = _sum(
        [
            float(coefficients.electrolyte.ion(name).valence) * variables.values[name]
            for name in model.species
        ]
    )
    permittivity = coefficients.relative_permittivity()
    permittivity_gradient = _sum(
        [
            permittivity.Diff(variables.variables[name]) * variables.gradients[name]
            for name in variables.values
        ]
    )
    expected = (
        -coefficients.reynolds * density * (ngs.grad(velocity) * velocity)
        - coefficients.screening * charge * field
        - 0.5 * ngs.InnerProduct(field, field) * permittivity_gradient
    )
    force = stabilisation.flow_state(context, side).force
    assert force is not None
    assert _l2_relative(mesh, force, expected) <= ROUND_OFF
    for name in FORCE_TERMS:
        without = replace(context, terms=tuple(t for t in context.terms if t.name != name))
        reduced = stabilisation.flow_state(without, side).force
        assert reduced is not None
        assert _l2_relative(mesh, reduced, expected) > 1.0e-6, f"{name} adds no density here"


@pytest.mark.parametrize("species", ["Na+", "Cl-"])
def test_ver81_the_cell_peclet_and_the_indicator_read_the_whole_wind(
    mesh: ngs.Mesh,
    readers: tuple[CoupledModel, ngs.GridFunction, kernel.Context, ngs.GridFunction],
    species: str,
) -> None:
    model, state, context, indicator = readers
    wind = _sum(list(_drifts(context, species).values()))
    diffusivity = context.trial.coefficients.diffusivity(species)
    printed = ngs.sqrt(ngs.InnerProduct(wind, wind)) * ngs.specialcf.mesh_size / (2.0 * diffusivity)
    peclet = model.cell_peclet(state, AXISYMMETRIC, SATURATED_WALL_DISTANCE_NM)[species]
    assert _l2_relative(mesh, peclet, printed) <= ROUND_OFF

    (slot,) = (
        slot
        for slot in coupled_slots(model.species, [f.name for f in model.fields], None, ())
        if slot.family == kernel.FLUX and slot.species == species
    )
    concentration = context.trial.variables.values[species]
    bracket = diffusivity * ngs.grad(concentration) + concentration * wind
    expected = -ngs.InnerProduct(bracket, ngs.grad(indicator))
    integrand = kernel.integrand(context.terms, slot, context)
    assert integrand is not None
    assert _l2_relative(mesh, integrand, expected) <= ROUND_OFF


def test_ver81_the_peclet_expression_lists_the_drifts_in_force() -> None:
    default = create("epnp-ns", fluid=FLUID)
    assert isinstance(default, CoupledModel)
    assert kernel.wind_text(default.terms_in_force()) == DEFAULT_WIND
    assert f"||b_i|| h_K / (2 D_i), b_i = {DEFAULT_WIND}" == PECLET_EXPRESSION
    dielectric = create("epnp-ns", fluid=FLUID, dielectric_gradient_forces=True)
    assert isinstance(dielectric, CoupledModel)
    assert kernel.wind_text(dielectric.terms_in_force()) == (f"{DEFAULT_WIND} + D_i grad(mu~_ex,i)")


def test_ver81_the_decrement_in_the_wind_assembles_finite() -> None:
    coarse = CylinderGeometry(radius_nm=2.0, length_nm=4.0).generate(maxh_nm=1.5)
    model, space, state = _coupled_state(coarse, **READERS)
    form = ngs.BilinearForm(space)
    form += model.residual_form(space, AXISYMMETRIC, state=state)
    residual = state.vec.CreateVector()
    form.Apply(state.vec, residual)
    form.AssembleLinearization(state.vec)
    entries = form.mat.AsVector().FV().NumPy()
    assert np.isfinite(residual.FV().NumPy()).all()
    assert np.isfinite(entries).all()
