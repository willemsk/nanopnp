"""VER-18: the method of manufactured solutions on the full coupled system.

This is the only route that verifies the ``u_r/r^2`` hoop term and the axis
treatment. An analytic benchmark exercises one term at a time and a whole-model
comparison localises nothing; a manufactured solution drives *every* term of the
assembled residual and asks whether the error falls at the rate the element
order promises.

Rates expected (NUM-01, VER-18): ``O(h^3)`` in L2 for the P2 fields ``phi``,
``c_i`` and ``u``. The Taylor-Hood pressure is P1 and converges at ``O(h^2)``,
which is not a shortfall but the pair's own rate; asserting 3 there would be
asserting something untrue of a correct solver.

Refinement levels and budget
----------------------------
Three levels on a 2 x 4 nm cylinder at ``maxh`` 0.4, 0.2 and 0.1 nm, the finest
carrying about 2 x 10^4 degrees of freedom. That is three orders of magnitude
below the 1.04 x 10^6 at which WP3 measured 41 s and 6.2 GB for one
factorisation, so the sequence stays comfortably inside the development
laptop's budget. The observed rate is the deliverable, not the number of levels.
"""

from dataclasses import replace

import pytest

from nanopnp.materials.electrolyte import CorrectionSwitches, Electrolyte
from nanopnp.mesh.primitives import CylinderGeometry
from nanopnp.physics.measures import Measures
from nanopnp.physics.models import (
    POTENTIAL,
    PRESSURE,
    VELOCITY,
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
"""The refinement sequence; 0.1 nm is the finest level this benchmark runs at."""

BOUNDARIES = CoupledBoundaries(
    potential="wall|end",
    concentration="wall|end",
    velocity="wall|end",
    velocity_axis="axis",
)
"""Every non-axis boundary is essential, so the pressure needs the mean
constraint; on the axis only ``u_r`` is fixed, which is the condition VER-18
exists to test (NUM-06)."""


def _model() -> CoupledModel:
    """Return the coupled model the manufactured solution is built against.

    Every correction resolves to ``none`` — the constant-coefficient scope the
    manufactured sources assume — while the steric flux stays **on**, because
    ``beta_i`` is a differential operator rather than a coefficient and is
    exactly the kind of term MMS exists to verify.
    """
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
    """Solve the manufactured problem at each level and return the L2 errors."""
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
    """``phi``, ``c_i`` and ``u`` fall as ``O(h^3)`` in the r-weighted L2 norm."""
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
    """The P1 pressure of the inf-sup stable pair converges at ``O(h^2)``, not 3."""
    errors, sizes = refinement
    rates = convergence_rates(errors[PRESSURE], sizes)
    assert min(rates) > 1.8, f"pressure: observed rates {rates} fall short of P1"


def test_ver18_manufactured_coefficients_are_constant_by_construction() -> None:
    """The scope guard fires when a correction is left on.

    The manufactured sources are built from numbers, so a concentration-dependent
    coefficient would make them inconsistent with the assembled form — and the
    convergence rate would collapse for a reason that reads like a
    discretisation bug rather than a misconfiguration.
    """
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
