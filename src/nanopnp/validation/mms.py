"""Manufactured solutions for the coupled axisymmetric system (VER-18)."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import cached_property
from typing import Any, TypeAlias

import sympy as sp

from nanopnp.core.typing import Expression, Mesh, Option
from nanopnp.io.vocabulary import (
    POTENTIAL,
    PRESSURE,
    PRESSURE_MEAN,
    VELOCITY,
)
from nanopnp.materials.forms import NUMPY_OPS
from nanopnp.numerics.measures import Measures
from nanopnp.physics.coefficients import (
    SATURATED_WALL_DISTANCE_NM,
    NondimensionalCoefficients,
)
from nanopnp.physics.models import (
    TransportModel,
    concentration_field_name,
)

__all__ = [
    "AXIAL",
    "RADIAL",
    "ConstantCoefficients",
    "ManufacturedSolution",
    "Symbolic",
    "constant_coefficients",
    "convergence_rates",
    "to_coefficient_function",
    "weighted_l2_error",
]

Symbolic: TypeAlias = Any

RADIAL = sp.Symbol("r", real=True)

AXIAL = sp.Symbol("z", real=True)

_PROBE_CONCENTRATIONS = (0.5, 2.0)


@dataclass(frozen=True)
class ConstantCoefficients:
    diffusivity: Mapping[str, float]
    mobility: Mapping[str, float]
    valence: Mapping[str, int]
    packing: Mapping[str, float]
    volume_ratio: Mapping[str, float]
    viscosity: float
    mass_density: float
    permittivity: float
    screening: float
    peclet: float
    reynolds: float


def constant_coefficients(model: TransportModel) -> ConstantCoefficients:
    probes = [_numeric_coefficients(model, value) for value in _PROBE_CONCENTRATIONS]
    reference, other = probes
    for name in model.species:
        _require_equal(reference.diffusivity(name), other.diffusivity(name), f"D~ of {name}", model)
        _require_equal(reference.mobility(name), other.mobility(name), f"mu~ of {name}", model)
    _require_equal(reference.viscosity(), other.viscosity(), "eta~", model)
    _require_equal(reference.mass_density(), other.mass_density(), "rho~", model)
    _require_equal(
        reference.relative_permittivity(), other.relative_permittivity(), "eps~_r", model
    )
    return ConstantCoefficients(
        diffusivity={name: float(reference.diffusivity(name)) for name in model.species},
        mobility={name: float(reference.mobility(name)) for name in model.species},
        valence={ion.name: ion.valence for ion in model.electrolyte.species},
        packing={name: float(value) for name, value in reference.packing_coefficients.items()},
        volume_ratio={name: reference.steric_volume_ratio(name) for name in model.species},
        viscosity=float(reference.viscosity()),
        mass_density=float(reference.mass_density()),
        permittivity=float(reference.relative_permittivity()),
        screening=reference.screening,
        peclet=reference.peclet,
        reynolds=reference.reynolds,
    )


def _numeric_coefficients(model: TransportModel, value: float) -> NondimensionalCoefficients:
    return NondimensionalCoefficients(
        electrolyte=model.electrolyte,
        scales=model.scales,
        concentrations={name: value for name in model.species},
        wall_distance_nm=SATURATED_WALL_DISTANCE_NM,
        ops=NUMPY_OPS,
    )


def _require_equal(first: float, second: float, what: str, model: TransportModel) -> None:
    if not math.isclose(float(first), float(second), rel_tol=1e-12, abs_tol=0.0):
        raise ValueError(
            f"{what} varies with concentration ({first:.6g} against {second:.6g}), so a "
            f"correction is active on {model.name!r}. The manufactured sources of VER-18 assume "
            "constant transport coefficients; build the model with every correction set to 'none'"
        )


@dataclass(frozen=True)
class ManufacturedSolution:
    model: TransportModel
    potential: sp.Expr
    concentrations: Mapping[str, sp.Expr]
    velocity: tuple[sp.Expr, sp.Expr] | None = None
    pressure: sp.Expr | None = None

    def __post_init__(self) -> None:
        missing = [name for name in self.model.species if name not in self.concentrations]
        if missing:
            raise ValueError(f"no manufactured concentration for {', '.join(missing)}")
        has_flow = self.velocity is not None and self.pressure is not None
        if has_flow != self.model.flow:
            raise ValueError(
                f"{self.model.name!r} solves flow: {self.model.flow}, but manufactured velocity "
                f"and pressure were {'given' if has_flow else 'omitted'}"
            )

    @classmethod
    def polynomial(cls, model: TransportModel) -> ManufacturedSolution:
        r, z = RADIAL, AXIAL
        potential = 0.30 * (1 + 0.50 * r**2 - 0.08 * r**4) * sp.cos(0.7 * z)
        concentrations: dict[str, sp.Expr] = {}
        for index, name in enumerate(model.species):
            amplitude = 0.18 - 0.05 * index
            radial = 1 + (-0.24 + 0.10 * index) * r**2 + (0.030 - 0.012 * index) * r**4
            axial = sp.sin(0.5 * z) if index % 2 == 0 else sp.cos(0.4 * z)
            concentrations[name] = 1 + amplitude * radial * axial
        if not model.flow:
            return cls(model=model, potential=potential, concentrations=concentrations)
        velocity = (
            0.10 * r * (1 - 0.15 * r**2) * sp.sin(0.6 * z),
            0.20 * (1 + 0.12 * r**2 - 0.020 * r**4) * sp.cos(0.3 * z),
        )
        pressure = 0.05 * (1 + 0.30 * r**2) * sp.sin(0.4 * z)
        return cls(
            model=model,
            potential=potential,
            concentrations=concentrations,
            velocity=velocity,
            pressure=pressure,
        )

    @cached_property
    def constants(self) -> ConstantCoefficients:
        return constant_coefficients(self.model)

    def expressions(self) -> Mapping[str, Symbolic]:
        exact: dict[str, Symbolic] = {POTENTIAL: self.potential}
        for name, value in self.concentrations.items():
            exact[concentration_field_name(name)] = value
        if self.velocity is not None and self.pressure is not None:
            exact[VELOCITY] = self.velocity
            exact[PRESSURE] = self.pressure
        return exact

    def coefficient_functions(self) -> Mapping[str, Expression]:
        return {name: to_coefficient_function(value) for name, value in self.expressions().items()}

    def ionic_charge_density(self) -> sp.Expr:
        constants = self.constants
        return sum(
            constants.valence[name] * self.concentrations[name] for name in self.model.species
        )

    def sources(self, measures: Measures) -> Mapping[str, Symbolic]:
        axisymmetric = measures.is_axisymmetric
        sources: dict[str, Symbolic] = {POTENTIAL: self._potential_source(axisymmetric)}
        for name in self.model.species:
            sources[concentration_field_name(name)] = self._species_source(name, axisymmetric)
        if self.model.flow:
            sources[VELOCITY] = self._momentum_source(axisymmetric)
            sources[PRESSURE] = self._continuity_source(axisymmetric)
            if self.model.pressure_constraint:
                sources[PRESSURE_MEAN] = self.pressure
        for name, expression in sources.items():
            _assert_regular_on_axis(expression, name)
        return sources

    def source_functions(self, measures: Measures) -> Mapping[str, Expression]:
        return {
            name: to_coefficient_function(value) for name, value in self.sources(measures).items()
        }

    def _potential_source(self, axisymmetric: bool) -> sp.Expr:
        constants = self.constants
        permittivity = constants.permittivity
        flux = (
            permittivity * sp.diff(self.potential, RADIAL),
            permittivity * sp.diff(self.potential, AXIAL),
        )
        divergence = _divergence(flux, axisymmetric)
        return _reduce(-divergence - constants.screening * self.ionic_charge_density())

    def _steric_flux(self, name: str, axisymmetric: bool) -> tuple[sp.Expr, sp.Expr]:
        del axisymmetric
        constants = self.constants
        occupied = sum(
            constants.packing[other] * self.concentrations[other] for other in self.model.species
        )
        ratio = constants.volume_ratio[name]
        gradient = [
            sum(
                constants.packing[other] * sp.diff(self.concentrations[other], coordinate)
                for other in self.model.species
            )
            for coordinate in (RADIAL, AXIAL)
        ]
        return (
            ratio * gradient[0] / (1 - occupied),
            ratio * gradient[1] / (1 - occupied),
        )

    def _species_source(self, name: str, axisymmetric: bool) -> sp.Expr:
        constants = self.constants
        concentration = self.concentrations[name]
        diffusivity = constants.diffusivity[name]
        mobility = constants.mobility[name]
        valence = constants.valence[name]
        bracket = [
            diffusivity * sp.diff(concentration, coordinate)
            + valence * mobility * concentration * sp.diff(self.potential, coordinate)
            for coordinate in (RADIAL, AXIAL)
        ]
        if self.model.steric:
            steric = self._steric_flux(name, axisymmetric)
            bracket = [
                term + diffusivity * concentration * s
                for term, s in zip(bracket, steric, strict=True)
            ]
        if self.velocity is not None:
            bracket = [
                term - constants.peclet * component * concentration
                for term, component in zip(bracket, self.velocity, strict=True)
            ]
        flux = (-bracket[0], -bracket[1])
        return _reduce(-_divergence(flux, axisymmetric))

    def _stress(self, axisymmetric: bool) -> tuple[sp.Expr, sp.Expr, sp.Expr, sp.Expr]:
        assert self.velocity is not None and self.pressure is not None
        viscosity = self.constants.viscosity
        radial, axial = self.velocity
        pressure = self.pressure
        hoop = -pressure + 2 * viscosity * radial / RADIAL if axisymmetric else sp.Integer(0)
        return (
            -pressure + 2 * viscosity * sp.diff(radial, RADIAL),
            viscosity * (sp.diff(radial, AXIAL) + sp.diff(axial, RADIAL)),
            -pressure + 2 * viscosity * sp.diff(axial, AXIAL),
            hoop,
        )

    def _momentum_source(self, axisymmetric: bool) -> tuple[sp.Expr, sp.Expr]:
        assert self.velocity is not None
        constants = self.constants
        s_rr, s_rz, s_zz, s_tt = self._stress(axisymmetric)
        radial, axial = self.velocity
        divergence_r = _divergence((s_rr, s_rz), axisymmetric)
        if axisymmetric:
            divergence_r = divergence_r - s_tt / RADIAL
        divergence_z = _divergence((s_rz, s_zz), axisymmetric)

        density = constants.mass_density if self.model.variable_density else 1.0
        charge = self.ionic_charge_density()
        components = []
        for divergence, component, coordinate in (
            (divergence_r, radial, RADIAL),
            (divergence_z, axial, AXIAL),
        ):
            source = -divergence + constants.screening * charge * sp.diff(
                self.potential, coordinate
            )
            if self.model.inertia:
                convective = radial * sp.diff(component, RADIAL) + axial * sp.diff(component, AXIAL)
                source = source + constants.reynolds * density * convective
            components.append(_reduce(source))
        return (components[0], components[1])

    def _continuity_source(self, axisymmetric: bool) -> sp.Expr:
        assert self.velocity is not None
        radial, axial = self.velocity
        divergence = sp.diff(radial, RADIAL) + sp.diff(axial, AXIAL)
        if axisymmetric:
            divergence = divergence + radial / RADIAL
        density = self.constants.mass_density if self.model.variable_density else 1.0
        return _reduce(-density * divergence)


def _divergence(vector: Sequence[sp.Expr], axisymmetric: bool) -> sp.Expr:
    radial, axial = vector
    if axisymmetric:
        return sp.diff(RADIAL * radial, RADIAL) / RADIAL + sp.diff(axial, AXIAL)
    return sp.diff(radial, RADIAL) + sp.diff(axial, AXIAL)


_AXIS_PROBE_HEIGHTS = (0.0, 0.37, 1.13, 2.71)


def _reduce(expression: sp.Expr) -> sp.Expr:
    return sp.cancel(sp.together(expression))


def _assert_regular_on_axis(expression: Symbolic, name: str) -> None:
    for item in expression if isinstance(expression, tuple) else (expression,):
        evaluate = sp.lambdify((RADIAL, AXIAL), item, "math")
        for height in _AXIS_PROBE_HEIGHTS:
            try:
                value = float(evaluate(0.0, height))
            except ZeroDivisionError:
                value = math.nan
            if not math.isfinite(value):
                raise ValueError(
                    f"the manufactured source for {name!r} is singular on the axis at z = "
                    f"{height}; a 1/r factor survived cancellation, which usually means a "
                    "manufactured field has the wrong parity in r (see ManufacturedSolution)"
                )


def to_coefficient_function(expression: Symbolic) -> Expression:
    import ngsolve as ngs

    if isinstance(expression, tuple):
        return ngs.CF(tuple(to_coefficient_function(item) for item in expression))
    namespace = {
        "sin": ngs.sin,
        "cos": ngs.cos,
        "tan": ngs.tan,
        "exp": ngs.exp,
        "log": ngs.log,
        "sqrt": ngs.sqrt,
        "sinh": ngs.sinh,
        "cosh": ngs.cosh,
        "atan": ngs.atan,
    }
    evaluate = sp.lambdify((RADIAL, AXIAL), expression, modules=[namespace, "math"], cse=True)
    return ngs.CF(evaluate(ngs.x, ngs.y)).Compile()


def weighted_l2_error(
    computed: Expression,
    exact: Expression,
    mesh: Mesh,
    measures: Measures,
    *,
    extra_order: int = 3,
    what: str = "field",
    **kwargs: Option,
) -> float:
    import ngsolve as ngs

    difference = computed - exact
    error = measures.integrate(
        ngs.InnerProduct(difference, difference),
        mesh,
        extra_order=extra_order,
        what=f"{what} error",
        **kwargs,
    )
    scale = measures.integrate(
        ngs.InnerProduct(exact, exact),
        mesh,
        extra_order=extra_order,
        what=f"{what} norm",
        **kwargs,
    )
    if scale <= 0.0:
        raise ValueError(f"the exact {what} has zero norm, so a relative error is undefined")
    return math.sqrt(error / scale)


def convergence_rates(errors: Sequence[float], sizes: Sequence[float]) -> list[float]:
    if len(errors) != len(sizes) or len(errors) < 2:
        raise ValueError(
            f"need at least two matched levels, got {len(errors)} errors and {len(sizes)} sizes"
        )
    if any(error <= 0.0 for error in errors):
        raise ValueError(f"a refinement level reported a non-positive error: {list(errors)}")
    return [
        math.log(errors[index] / errors[index + 1]) / math.log(sizes[index] / sizes[index + 1])
        for index in range(len(errors) - 1)
    ]
