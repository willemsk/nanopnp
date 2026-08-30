"""Nernst-Planck flux assembly: the PHY-05 sign discipline and the NUM-02 branches.

The steric flux is where this model is most likely to be wrong quietly. A
flipped sign drives ions *into* crowded regions rather than out of them, pushes
the packing fraction towards its singularity and diverges — after producing
several plausible iterates. A collapsed sum over species, or a dropped
``a_i^3/a_0^3`` prefactor, does not diverge at all: it just returns the wrong
current. Both are asserted here against arithmetic done in the test.
"""

import math

import ngsolve as ngs
import pytest

from nanopnp.materials.electrolyte import Electrolyte
from nanopnp.mesh.primitives import SlabGeometry
from nanopnp.physics.coefficients import (
    SATURATED_WALL_DISTANCE_NM,
    NondimensionalCoefficients,
    mesh_unit_scales,
)
from nanopnp.physics.nernst_planck import (
    ConcentrationVariables,
    packing_fraction,
    species_flux,
    steric_flux,
)
from nanopnp.solve.gates import PackingFractionGate

CONCENTRATION_M = 1.0
SAMPLE = (0.5, 0.25)


@pytest.fixture(scope="module")
def mesh() -> ngs.Mesh:
    """Return a small planar slab; these tests interpolate onto it, they do not solve."""
    return SlabGeometry(width_nm=1.0, height_nm=1.0).generate(maxh_nm=0.25)


def _build(
    mesh: ngs.Mesh, expressions: dict[str, ngs.CoefficientFunction]
) -> tuple[ConcentrationVariables, NondimensionalCoefficients]:
    """Return concentration variables and coefficients for a prescribed state."""
    space = ngs.H1(mesh, order=2)
    fields = {}
    for name, expression in expressions.items():
        field = ngs.GridFunction(space, name=name)
        field.Set(expression)
        fields[name] = field
    variables = ConcentrationVariables.primitive(fields)
    electrolyte = Electrolyte.from_parameter_file()
    coefficients = NondimensionalCoefficients(
        electrolyte=electrolyte,
        scales=mesh_unit_scales(electrolyte, CONCENTRATION_M),
        concentrations=variables.values,
        wall_distance_nm=SATURATED_WALL_DISTANCE_NM,
    )
    return variables, coefficients


def _linear_state(
    mesh: ngs.Mesh,
) -> tuple[ConcentrationVariables, NondimensionalCoefficients]:
    """Return a state whose two species vary along *different* axes.

    ``c_Na`` varies only in r and ``c_Cl`` only in z, so any coupling between
    them in the steric flux shows up as a component that would otherwise be
    identically zero.
    """
    return _build(
        mesh,
        {"Na+": 1.0 + 0.5 * ngs.x, "Cl-": 1.0 + 0.2 * ngs.y},
    )


def test_phy05_steric_volume_ratio_is_not_a_normalisation(mesh: ngs.Mesh) -> None:
    """``a_i^3/a_0^3`` is 4.16 for the reference NaCl parameters, not 1."""
    _, coefficients = _linear_state(mesh)
    for species in ("Na+", "Cl-"):
        ratio = coefficients.steric_volume_ratio(species)
        assert ratio == pytest.approx((0.5 / 0.311) ** 3, rel=1e-12)
        assert ratio == pytest.approx(4.16, abs=0.01), "PHY-05 states 4.16 for NaCl"


def test_phy05_steric_flux_retains_the_sum_over_all_species(mesh: ngs.Mesh) -> None:
    """``beta_Na`` responds to ``grad c_Cl``; the sum is not a self-interaction."""
    variables, coefficients = _linear_state(mesh)
    packing = coefficients.packing_coefficients
    nu = packing["Na+"]
    assert packing["Cl-"] == pytest.approx(nu, rel=1e-12), "both ions share a_i = 0.5 nm"

    beta = steric_flux(
        variables,
        packing_coefficients=packing,
        volume_ratio=coefficients.steric_volume_ratio("Na+"),
    )
    point = mesh(*SAMPLE)
    computed = beta(point)

    c_na, c_cl = 1.0 + 0.5 * SAMPLE[0], 1.0 + 0.2 * SAMPLE[1]
    occupied = nu * (c_na + c_cl)
    ratio = coefficients.steric_volume_ratio("Na+")
    expected = (
        ratio * nu * 0.5 / (1.0 - occupied),
        ratio * nu * 0.2 / (1.0 - occupied),
    )
    assert computed[0] == pytest.approx(expected[0], rel=1e-10)
    assert computed[1] == pytest.approx(expected[1], rel=1e-10)
    assert computed[1] != 0.0, "the axial component comes only from the other species"


def test_phy05_steric_flux_drives_ions_out_of_crowded_regions(mesh: ngs.Mesh) -> None:
    """The negated bracket makes the steric term *add* to the down-gradient flux.

    Both species rise with r here, so the steric drive is radially outward and
    the flux it produces is inward-negative, that is down the gradient. A
    flipped sign — the failure PHY-05 warns about — would subtract from the
    diffusive flux instead and, at a high enough packing fraction, reverse it.
    """
    variables, coefficients = _build(mesh, {"Na+": 1.0 + 0.5 * ngs.x, "Cl-": 1.0 + 0.4 * ngs.x})
    potential = ngs.GridFunction(ngs.H1(mesh, order=2))
    potential.Set(ngs.CF(0.0))

    with_steric = species_flux(
        "Na+",
        coefficients=coefficients,
        variables=variables,
        potential=potential,
        steric=True,
    )
    without = species_flux(
        "Na+",
        coefficients=coefficients,
        variables=variables,
        potential=potential,
        steric=False,
    )
    point = mesh(*SAMPLE)
    radial_with, radial_without = with_steric(point)[0], without(point)[0]

    assert radial_without < 0.0, "diffusion alone already runs down the gradient"
    assert radial_with < radial_without, (
        "the steric term must reinforce the outward drive; a larger (less negative) "
        "radial flux is the flipped sign of PHY-05"
    )


def test_phy06_packing_fraction_agrees_with_the_num17_gate(mesh: ngs.Mesh) -> None:
    """The ``Phi`` of the flux and the ``Phi`` of the gate are the same quantity."""
    variables, coefficients = _linear_state(mesh)
    from_flux = packing_fraction(variables.values, coefficients.packing_coefficients)

    scale = coefficients.scales.concentration_mol_m3
    gate = PackingFractionGate(
        sampler=None,  # type: ignore[arg-type]
        concentrations={name: value * scale for name, value in variables.values.items()},
    )
    point = mesh(*SAMPLE)
    assert from_flux(point) == pytest.approx(gate.packing_fraction(point), rel=1e-12)


def test_phy04_flux_vanishes_on_a_uniform_state(mesh: ngs.Mesh) -> None:
    """No gradients, no field, no flow: every term of ``J_i`` is zero."""
    variables, coefficients = _build(mesh, {"Na+": ngs.CF(1.0), "Cl-": ngs.CF(1.0)})
    potential = ngs.GridFunction(ngs.H1(mesh, order=2))
    potential.Set(ngs.CF(0.7))
    flux = species_flux("Na+", coefficients=coefficients, variables=variables, potential=potential)
    point = mesh(*SAMPLE)
    assert flux(point)[0] == pytest.approx(0.0, abs=1e-12)
    assert flux(point)[1] == pytest.approx(0.0, abs=1e-12)


def test_num02_log_branch_uses_the_chain_rule() -> None:
    """``grad(c~_i)`` in the log branch is ``exp(w_i) grad(w_i)``.

    ``exp(w)`` is not a finite-element function, so its gradient cannot be asked
    of NGSolve and has to be supplied; getting the chain rule wrong there would
    scale every diffusive and steric term by ``c~_i`` with nothing to catch it.
    The comparison is against a central difference of ``exp(w)`` on the mesh,
    which knows nothing about the implementation.
    """
    mesh = SlabGeometry(width_nm=1.0, height_nm=1.0).generate(maxh_nm=0.25)
    space = ngs.H1(mesh, order=2)
    field = ngs.GridFunction(space, name="w")
    field.Set(0.3 * ngs.x - 0.7 * ngs.y)
    variables = ConcentrationVariables.logarithmic_branch({"Na+": field})

    step = 1e-5
    radial, axial = SAMPLE
    value = variables.values["Na+"]
    difference = (
        (value(mesh(radial + step, axial)) - value(mesh(radial - step, axial))) / (2 * step),
        (value(mesh(radial, axial + step)) - value(mesh(radial, axial - step))) / (2 * step),
    )
    computed = variables.gradients["Na+"](mesh(*SAMPLE))
    assert computed[0] == pytest.approx(difference[0], rel=1e-6)
    assert computed[1] == pytest.approx(difference[1], rel=1e-6)


def test_num02_branches_agree_where_both_are_exact() -> None:
    """On a uniform state the two formulations give the identical flux.

    A varying state cannot compare them to round-off — one branch represents
    ``c~_i`` exactly and the other represents ``log c~_i`` exactly, and the
    difference between the two interpolants is the mesh's, not the model's. A
    uniform concentration is exact in both, so what is left is the plumbing:
    the valence, the mobility and the migration term, which must match exactly.
    """
    mesh = SlabGeometry(width_nm=1.0, height_nm=1.0).generate(maxh_nm=0.25)
    space = ngs.H1(mesh, order=2)
    potential = ngs.GridFunction(space)
    potential.Set(0.3 * ngs.x - 0.1 * ngs.y)

    primitive, coefficients = _build(mesh, {"Na+": ngs.CF(1.3), "Cl-": ngs.CF(1.3)})
    logs = {}
    for name in ("Na+", "Cl-"):
        field = ngs.GridFunction(space, name=f"w_{name}")
        field.Set(ngs.CF(math.log(1.3)))
        logs[name] = field
    logarithmic = ConcentrationVariables.logarithmic_branch(logs)
    log_coefficients = NondimensionalCoefficients(
        electrolyte=coefficients.electrolyte,
        scales=coefficients.scales,
        concentrations=logarithmic.values,
        wall_distance_nm=SATURATED_WALL_DISTANCE_NM,
    )

    point = mesh(*SAMPLE)
    for species in ("Na+", "Cl-"):
        expected = species_flux(
            species, coefficients=coefficients, variables=primitive, potential=potential
        )(point)
        computed = species_flux(
            species,
            coefficients=log_coefficients,
            variables=logarithmic,
            potential=potential,
        )(point)
        assert computed[0] == pytest.approx(expected[0], rel=1e-10)
        assert computed[1] == pytest.approx(expected[1], rel=1e-10)


def test_num02_log_branch_is_positive_by_construction(mesh: ngs.Mesh) -> None:
    """``exp(w)`` cannot be negative, which is the whole point of the branch."""
    space = ngs.H1(mesh, order=2)
    field = ngs.GridFunction(space)
    field.Set(-8.0 + 4.0 * ngs.x)
    variables = ConcentrationVariables.logarithmic_branch({"Na+": field})
    value = variables.values["Na+"](mesh(*SAMPLE))
    assert value > 0.0
    assert value == pytest.approx(math.exp(-8.0 + 4.0 * SAMPLE[0]), rel=1e-6)
