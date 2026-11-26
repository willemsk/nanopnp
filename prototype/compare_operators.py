"""Compare the composed coupled operator with today's, variant by variant, at one smooth state.

Run ``uv run python prototype/compare_operators.py [--slots]``. It exits 1 where a variant's
residual or Jacobian differs from today's by more than 1e-12 of its largest entry (WP6.09 D5 a).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping
from dataclasses import dataclass

import ngsolve as ngs
import numpy as np

from nanopnp.core.typing import Expression, FESpace, GridFunction, IntegralTerm, Mesh, Option
from nanopnp.io.vocabulary import POTENTIAL, PRESSURE, PRESSURE_MEAN, VELOCITY
from nanopnp.materials.electrolyte import CorrectionSwitches, Electrolyte
from nanopnp.mesh.primitives import CylinderGeometry
from nanopnp.numerics.measures import FixedCharge, Measures
from nanopnp.physics.kernel import compose_integrals
from nanopnp.physics.models import CoupledBoundaries, CoupledModel, create
from nanopnp.validation.mms import ManufacturedSolution

TOLERANCE = 1.0e-12
AXISYMMETRIC = Measures(symmetry="axisymmetric", element_order=2)
BOUNDARIES = CoupledBoundaries(
    potential="wall|end",
    concentration="wall|end",
    velocity="wall|end",
    velocity_axis="axis",
)
FLUID = "electrolyte"
MULTIPLIER = 0.5


@dataclass(frozen=True)
class Variant:
    label: str
    name: str
    options: Mapping[str, Option]


VARIANTS = (
    Variant("epnp-ns default", "epnp-ns", {}),
    Variant("dielectric_gradient_forces", "epnp-ns", {"dielectric_gradient_forces": True}),
    Variant("log_variables", "epnp-ns", {"log_variables": True}),
    Variant("stabilisation reference", "epnp-ns", {"stabilisation": "reference"}),
    Variant("stabilisation supg", "epnp-ns", {"stabilisation": "supg"}),
    Variant("variable_density off", "epnp-ns", {"variable_density": False}),
    Variant("inertia off", "epnp-ns", {"inertia": False}),
    Variant("pressure_constraint", "epnp-ns", {"pressure_constraint": True}),
    Variant("pnp-ns", "pnp-ns", {}),
    Variant("pnp", "pnp", {}),
)


def _manufactured_fields() -> Mapping[str, Expression]:
    electrolyte = Electrolyte.from_parameter_file(
        switches=CorrectionSwitches(steric="borukhov"),
    )
    model = CoupledModel(
        electrolyte=electrolyte,
        concentration_M=0.1,
        name="mms",
        fluid=FLUID,
        pressure_constraint=True,
    )
    return ManufacturedSolution.polynomial(model).coefficient_functions()


def _state(model: CoupledModel, space: FESpace, fields: Mapping[str, Expression]) -> GridFunction:
    state = ngs.GridFunction(space)
    for field, component in zip(model.fields, state.components, strict=True):
        if field.name == PRESSURE_MEAN:
            component.vec[:] = MULTIPLIER
            continue
        value = fields[field.name]
        if model.log_variables and field.name.startswith("c_"):
            value = ngs.log(value)
        component.Set(value)
    return state


def _keywords(model: CoupledModel, state: GridFunction) -> dict[str, Option]:
    r, z = ngs.x, ngs.y
    sources: dict[str, Expression] = {POTENTIAL: 0.3 * ngs.cos(0.5 * z) * (1 + 0.1 * r * r)}
    for index, species in enumerate(model.species):
        sources[f"c_{species}"] = (0.05 + 0.02 * index) * ngs.sin(0.4 * z) * (1 - 0.05 * r * r)
    if model.flow:
        sources[VELOCITY] = ngs.CF((0.02 * r * ngs.cos(0.3 * z), 0.04 * (1 - 0.1 * r * r)))
        sources[PRESSURE] = 0.01 * ngs.sin(0.6 * z) * (1 + 0.2 * r * r)
        if model.pressure_constraint:
            sources[PRESSURE_MEAN] = ngs.CF(0.03)
    return {
        "wall_distance_nm": 2.0 - r,
        "fixed_charge": FixedCharge(
            density=0.4 * ngs.cos(0.8 * z) * (1 - 0.2 * r * r), rule_order=8
        ),
        "surface_charge": 0.2 * ngs.sin(0.7 * z) + 0.1,
        "surface_charge_boundary": "wall",
        "sources": sources,
        "state": state,
    }


def _assembled(
    space: FESpace, integral: IntegralTerm, state: GridFunction
) -> tuple[np.ndarray, np.ndarray]:
    form = ngs.BilinearForm(space)
    form += integral.MakeBFI() if isinstance(integral, ngs.comp.Integral) else integral
    out = state.vec.CreateVector()
    form.Apply(state.vec, out)
    form.AssembleLinearization(state.vec)
    return np.array(out.FV().NumPy()), np.array(form.mat.AsVector().FV().NumPy())


def _relative(new: np.ndarray, old: np.ndarray) -> float:
    scale = float(np.max(np.abs(old)))
    if new.shape != old.shape:
        return float("inf")
    difference = float(np.max(np.abs(new - old)))
    return difference / scale if scale > 0.0 else difference


def _integrals(sum_of_integrals: IntegralTerm) -> list[IntegralTerm]:
    return [sum_of_integrals[index] for index in range(len(sum_of_integrals))]


def _compare(variant: Variant, mesh: Mesh, fields: Mapping[str, Expression], slots: bool) -> bool:
    model = create(variant.name, concentration_M=0.1, fluid=FLUID, **variant.options)
    assert isinstance(model, CoupledModel)
    space = model.space(mesh, BOUNDARIES)
    state = _state(model, space, fields)
    keywords = _keywords(model, state)
    old = model._reference_residual_form(space, AXISYMMETRIC, **keywords)
    new = model.residual_form(space, AXISYMMETRIC, **keywords)
    old_residual, old_jacobian = _assembled(space, old, state)
    new_residual, new_jacobian = _assembled(space, new, state)
    residual = _relative(new_residual, old_residual)
    jacobian = _relative(new_jacobian, old_jacobian)
    passed = residual <= TOLERANCE and jacobian <= TOLERANCE and np.isfinite(new_jacobian).all()
    print(
        f"{variant.label:28s} residual {residual:.3e}  jacobian {jacobian:.3e}  "
        f"{'pass' if passed else 'MISS'}"
    )
    if slots or not passed:
        terms, slot_list, context = model._composition(space, AXISYMMETRIC, **keywords)
        named = compose_integrals(terms, slot_list, context)
        reference = _integrals(old)
        if len(reference) != len(named):
            print(f"    {len(named)} slots against {len(reference)} integrals today")
            for name, _ in named:
                print(f"    slot {name}")
            return passed
        for (name, integral), today in zip(named, reference, strict=True):
            slot_residual, _ = _assembled(space, integral, state)
            today_residual, _ = _assembled(space, today, state)
            print(f"    {name:28s} {_relative(slot_residual, today_residual):.3e}")
    return passed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slots", action="store_true", help="compare each slot alone")
    arguments = parser.parse_args()
    mesh = CylinderGeometry(radius_nm=2.0, length_nm=4.0).generate(maxh_nm=0.4)
    fields = _manufactured_fields()
    print(f"mesh: {mesh.ne} elements; tolerance {TOLERANCE:.0e} of the largest entry")
    results = [_compare(variant, mesh, fields, arguments.slots) for variant in VARIANTS]
    print(f"{sum(results)} of {len(results)} variants within {TOLERANCE:.0e}")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
