"""VER-18: the method of manufactured solutions on the full coupled system."""

from dataclasses import replace

import pytest

from nanopnp.io.vocabulary import (
    POTENTIAL,
    PRESSURE,
    VELOCITY,
)
from nanopnp.materials.electrolyte import CorrectionSwitches, Electrolyte
from nanopnp.mesh.primitives import CylinderGeometry
from nanopnp.numerics.measures import Measures
from nanopnp.physics.models import (
    CoupledBoundaries,
    CoupledModel,
)
from nanopnp.validation.mms import (
    ManufacturedSolution,
    constant_coefficients,
    convergence_rates,
    weighted_l2_error,
)

AXISYMMETRIC = Measures(symmetry="axisymmetric", element_order=2)
RADIUS_NM, LENGTH_NM = 2.0, 4.0
MESH_SIZES_NM = (0.4, 0.2, 0.1)

# NUM-06
BOUNDARIES = CoupledBoundaries(
    potential="wall|end",
    concentration="wall|end",
    velocity="wall|end",
    velocity_axis="axis",
)


def _model() -> CoupledModel:
    electrolyte = Electrolyte.from_parameter_file(
        switches=replace(CorrectionSwitches.classical(), steric=True)
    )
    return CoupledModel(
        electrolyte=electrolyte,
        concentration_M=0.1,
        name="mms",
        fluid="electrolyte",
        pressure_constraint=True,
    )


@pytest.fixture(scope="module")
def refinement() -> tuple[dict[str, list[float]], tuple[float, ...]]:
    model = _model()
    manufactured = ManufacturedSolution.polynomial(model)
    exact = manufactured.coefficient_functions()
    sources = manufactured.source_functions(AXISYMMETRIC)

    errors: dict[str, list[float]] = {name: [] for name in exact}
    for maxh_nm in MESH_SIZES_NM:
        mesh = CylinderGeometry(radius_nm=RADIUS_NM, length_nm=LENGTH_NM).generate(maxh_nm=maxh_nm)
        solution = model.solve(
            mesh,
            AXISYMMETRIC,
            boundaries=BOUNDARIES,
            potential_values=exact[POTENTIAL],
            concentration_values={species: exact[f"c_{species}"] for species in model.species},
            velocity_values=exact[VELOCITY],
            sources=sources,
        )
        for name, reference in exact.items():
            errors[name].append(
                weighted_l2_error(
                    solution.component(name), reference, mesh, AXISYMMETRIC, what=name
                )
            )
    return errors, MESH_SIZES_NM


def test_ver18_second_order_fields_converge_at_third_order(
    refinement: tuple[dict[str, list[float]], tuple[float, ...]],
) -> None:
    errors, sizes = refinement
    model = _model()
    quadratic = [POTENTIAL, VELOCITY] + [f"c_{species}" for species in model.species]
    for name in quadratic:
        rates = convergence_rates(errors[name], sizes)
        assert min(rates) > 2.8, f"{name}: observed rates {rates} fall short of P2"
        assert errors[name][-1] < 1e-4, f"{name}: finest-level error {errors[name][-1]:.3g}"


def test_ver18_taylor_hood_pressure_converges_at_its_own_order(
    refinement: tuple[dict[str, list[float]], tuple[float, ...]],
) -> None:
    errors, sizes = refinement
    rates = convergence_rates(errors[PRESSURE], sizes)
    assert min(rates) > 1.8, f"pressure: observed rates {rates} fall short of P1"


def test_ver18_manufactured_coefficients_are_constant_by_construction() -> None:
    constants = constant_coefficients(_model())
    assert constants.viscosity == pytest.approx(1.0, rel=1e-12)
    assert constants.permittivity == pytest.approx(1.0, rel=1e-12)

    extended = CoupledModel(
        electrolyte=Electrolyte.from_parameter_file(),
        concentration_M=0.1,
        name="mms-extended",
        fluid="electrolyte",
    )
    with pytest.raises(ValueError, match="varies with concentration"):
        constant_coefficients(extended)
