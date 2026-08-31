"""Manufactured solutions for the coupled axisymmetric system (VER-18).

The method of manufactured solutions is the only route that verifies the
``u_r/r^2`` hoop term and the axis treatment: an analytic benchmark tests one
term at a time and a whole-model comparison localises nothing, but a
manufactured solution exercises **every** term of the assembled residual against
an exact answer at a rate that is either O(h^3) for P2 or is not.

The construction here mirrors the weak forms of :mod:`nanopnp.physics` term by
term. Each equation's source is the *strong* residual of the manufactured
fields, written in cylindrical coordinates:

    f_phi  = -div(eps~ grad phi~) - S sum_i z_i c~_i
    f_i    = -div(J~_i)
    f_u    = -div(sigma~) + Re rho~ (u~.grad)u~ + S (sum_i z_i c~_i) grad phi~
    f_p    = -rho~ div^(u~)

with ``div`` the cylindrical divergence ``(1/r) d_r(r .) + d_z(.)`` and the
momentum divergence carrying the ``-sigma_theta,theta / r`` term that is the
strong-form counterpart of the weak hoop strain. Dropping that term here would
make the manufactured source consistent with a *wrong* weak form and the test
would pass while the solver stayed broken, so it is written out explicitly.

**Scope: constant transport coefficients.** ``D~_i``, ``mu~_i``, ``eta~``,
``rho~`` and ``eps~_r`` must be constants, which means every correction of the
model's electrolyte resolves to ``none``; :func:`constant_coefficients` checks it
rather than assuming it. That is deliberate. VER-18 exists to verify the
differential operators, the ``1/r`` terms and the axis; the correction formulae
themselves are verified pointwise by VER-03 and VER-04 in Tier 1, and driving
them from the fitted wall-distance field — itself a discrete solve with no
closed form — would pollute the observed rate rather than sharpen it. The steric
flux ``beta_i`` *is* retained: it is a differential operator, not a coefficient.

``sympy`` is imported at module scope, unlike ``ngsolve`` and ``numpy``. It costs
about 150 ms, which is the same order as those, but nothing on the CLI, GUI or
sweep-dispatch path imports ``nanopnp.validation``: ``import nanopnp.cli`` stays
at 34 ms and ``import nanopnp.physics.models`` at 28 ms with this module present.
If a stage introspection ever reaches in here, that measurement is the reason to
revisit it.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import cached_property
from typing import Any, TypeAlias

import sympy as sp

from nanopnp.core.typing import Expression, Mesh, Option
from nanopnp.materials.forms import NUMPY_OPS
from nanopnp.physics.coefficients import (
    SATURATED_WALL_DISTANCE_NM,
    NondimensionalCoefficients,
)
from nanopnp.physics.measures import Measures
from nanopnp.physics.models import (
    POTENTIAL,
    PRESSURE,
    PRESSURE_MEAN,
    VELOCITY,
    CoupledModel,
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
"""A sympy expression, or a tuple of them for a vector-valued field."""

RADIAL = sp.Symbol("r", real=True)
"""The radial coordinate of the manufactured expressions; ``ngsolve.x``."""

AXIAL = sp.Symbol("z", real=True)
"""The axial coordinate of the manufactured expressions; ``ngsolve.y``."""

_PROBE_CONCENTRATIONS = (0.5, 2.0)
"""Two dimensionless concentrations the constancy check is made at."""


@dataclass(frozen=True)
class ConstantCoefficients:
    """The dimensionless material constants of a corrections-off model."""

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


def constant_coefficients(model: CoupledModel) -> ConstantCoefficients:
    """Return the model's material constants, having checked that they are constant.

    Raises
    ------
    ValueError
        If any coefficient varies with concentration, which means a correction
        is active. The manufactured sources below are built from numbers, so a
        varying coefficient would silently make them inconsistent with the
        assembled form and the convergence rate would collapse for a reason that
        looks like a discretisation bug.
    """
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


def _numeric_coefficients(model: CoupledModel, value: float) -> NondimensionalCoefficients:
    """Return the model's coefficients evaluated numerically at a uniform state."""
    return NondimensionalCoefficients(
        electrolyte=model.electrolyte,
        scales=model.scales,
        concentrations={name: value for name in model.species},
        wall_distance_nm=SATURATED_WALL_DISTANCE_NM,
        ops=NUMPY_OPS,
    )


def _require_equal(first: float, second: float, what: str, model: CoupledModel) -> None:
    """Raise if a coefficient differs between the two probe concentrations."""
    if not math.isclose(float(first), float(second), rel_tol=1e-12, abs_tol=0.0):
        raise ValueError(
            f"{what} varies with concentration ({first:.6g} against {second:.6g}), so a "
            f"correction is active on {model.name!r}. The manufactured sources of VER-18 assume "
            "constant transport coefficients; build the model with every correction set to 'none'"
        )


@dataclass(frozen=True)
class ManufacturedSolution:
    """Exact fields and the source terms that make them a solution (VER-18).

    Parameters
    ----------
    model
        The model whose residual the sources are built against. Its constants
        are read through :func:`constant_coefficients`, so a source and the form
        it drives cannot quote different numbers.
    potential
        ``phi~(r, z)`` as a sympy expression in :data:`RADIAL` and :data:`AXIAL`.
    concentrations
        ``c~_i(r, z)`` by species name.
    velocity
        ``(u~_r, u~_z)``, or ``None`` for a model with no flow.
    pressure
        ``p~(r, z)``, or ``None`` for a model with no flow.

    Notes
    -----
    Axis parity is the caller's responsibility and is what the test is *for*:
    ``phi~``, ``c~_i``, ``u~_z`` and ``p~`` must be even in ``r`` and ``u~_r``
    odd, so that ``u~_r = 0`` on the axis is consistent and ``u~_r/r`` is
    regular there. :meth:`polynomial` builds such a set.
    """

    model: CoupledModel
    potential: sp.Expr
    concentrations: Mapping[str, sp.Expr]
    velocity: tuple[sp.Expr, sp.Expr] | None = None
    pressure: sp.Expr | None = None

    def __post_init__(self) -> None:
        """Reject a manufactured set that does not match the model's field set.

        Raises
        ------
        ValueError
            If a species is missing, or if the flow fields disagree with whether
            the model solves for flow.
        """
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
    def polynomial(cls, model: CoupledModel) -> ManufacturedSolution:
        """Return a default manufactured set: even powers of ``r``, trigonometric in ``z``.

        The radial dependence is polynomial and includes an ``r^4`` term, which
        no P2 element reproduces exactly, so the measured rate is a rate and not
        an artefact of the exact solution lying in the space. The axial
        dependence is trigonometric for the same reason. Concentrations stay
        near 1 and comfortably positive so that the NUM-17 positivity gate does
        not fire on the exact solution.
        """
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

    # -- the exact fields --------------------------------------------------

    @cached_property
    def constants(self) -> ConstantCoefficients:
        """The model's dimensionless material constants.

        Cached: one source build reads it seven times, and each read would
        otherwise rebuild two :class:`NondimensionalCoefficients` and re-run the
        whole constant-coefficient scope check to return the same numbers.
        """
        return constant_coefficients(self.model)

    def expressions(self) -> Mapping[str, Symbolic]:
        """Return the exact fields by model field name, as sympy expressions."""
        exact: dict[str, Symbolic] = {POTENTIAL: self.potential}
        for name, value in self.concentrations.items():
            exact[concentration_field_name(name)] = value
        if self.velocity is not None and self.pressure is not None:
            exact[VELOCITY] = self.velocity
            exact[PRESSURE] = self.pressure
        return exact

    def coefficient_functions(self) -> Mapping[str, Expression]:
        """Return the exact fields as NGSolve coefficient functions."""
        return {name: to_coefficient_function(value) for name, value in self.expressions().items()}

    def ionic_charge_density(self) -> sp.Expr:
        """Return ``sum_i z_i c~_i``, the dimensionless mobile charge."""
        constants = self.constants
        return sum(
            constants.valence[name] * self.concentrations[name] for name in self.model.species
        )

    # -- the source terms --------------------------------------------------

    def sources(self, measures: Measures) -> Mapping[str, Symbolic]:
        """Return the source term of each equation, as sympy expressions.

        The keys are model field names, so the result is passed straight to
        :meth:`nanopnp.physics.models.CoupledModel.residual_form` after
        conversion by :meth:`source_functions`.
        """
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
        """Return the source terms as NGSolve coefficient functions."""
        return {
            name: to_coefficient_function(value) for name, value in self.sources(measures).items()
        }

    def _potential_source(self, axisymmetric: bool) -> sp.Expr:
        """Return ``-div(eps~ grad phi~) - S sum_i z_i c~_i``."""
        constants = self.constants
        permittivity = constants.permittivity
        flux = (
            permittivity * sp.diff(self.potential, RADIAL),
            permittivity * sp.diff(self.potential, AXIAL),
        )
        divergence = _divergence(flux, axisymmetric)
        return _reduce(-divergence - constants.screening * self.ionic_charge_density())

    def _steric_flux(self, name: str, axisymmetric: bool) -> tuple[sp.Expr, sp.Expr]:
        """Return ``beta~_i`` of PHY-05, with the sign discipline of the weak form."""
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
        """Return ``-div(J~_i)``, mirroring ``nernst_planck.species_flux`` term by term."""
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
        """Return ``(sigma_rr, sigma_rz, sigma_zz, sigma_theta,theta)``."""
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
        """Return ``-div(sigma~) + Re rho~ (u~.grad)u~ + S rho~_ion grad(phi~)``.

        The ``-sigma_theta,theta / r`` term in the radial component is the strong
        counterpart of the weak hoop strain ``2 eta u_r v_r / r^2`` (NUM-05).
        Omitting it here would make the manufactured source consistent with the
        weak form that omits the hoop term, and VER-18 would then certify a
        solver that is wrong in exactly the way this benchmark exists to catch.
        """
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
        """Return ``-rho~ div^(u~)``, the residual of the continuity equation."""
        assert self.velocity is not None
        radial, axial = self.velocity
        divergence = sp.diff(radial, RADIAL) + sp.diff(axial, AXIAL)
        if axisymmetric:
            divergence = divergence + radial / RADIAL
        density = self.constants.mass_density if self.model.variable_density else 1.0
        return _reduce(-density * divergence)


def _divergence(vector: Sequence[sp.Expr], axisymmetric: bool) -> sp.Expr:
    """Return the cylindrical divergence ``(1/r) d_r(r a_r) + d_z a_z``."""
    radial, axial = vector
    if axisymmetric:
        return sp.diff(RADIAL * radial, RADIAL) / RADIAL + sp.diff(axial, AXIAL)
    return sp.diff(radial, RADIAL) + sp.diff(axial, AXIAL)


_AXIS_PROBE_HEIGHTS = (0.0, 0.37, 1.13, 2.71)
"""Axial coordinates the axis-regularity check evaluates a source at."""


def _reduce(expression: sp.Expr) -> sp.Expr:
    """Cancel the removable ``1/r`` factors a cylindrical operator leaves behind.

    Every ``1/r`` in these sources is removable for a solution with the right
    axis parity, but sympy leaves the quotient standing. NGSolve would then
    evaluate ``0/0`` at a quadrature point on the axis and return NaN with no
    diagnostic, so the cancellation is done here rather than hoped for at
    assembly — and :func:`_assert_regular_on_axis` then checks that it worked.

    ``together`` followed by ``cancel`` is enough and is what is used;
    ``expand``-ing first also works but doubles the size of the steric source
    and triples the time to build it, for no change in the result.
    """
    return sp.cancel(sp.together(expression))


def _assert_regular_on_axis(expression: Symbolic, name: str) -> None:
    """Raise if a source term is singular at ``r = 0``.

    A ``1/r`` that survived :func:`_reduce` does not fail loudly downstream: the
    quadrature rule of NUM-07 keeps its points off the axis for the *forms*, but
    a source coefficient function is evaluated wherever the rule asks, and a
    ``0/0`` there propagates through the assembled vector as a NaN with no
    diagnostic at all. Checking here costs four evaluations per field.

    Raises
    ------
    ValueError
        If the expression is not finite on the axis, naming the field. The usual
        cause is a manufactured field with the wrong parity in ``r`` — ``u~_r``
        even, or ``phi~`` odd — for which no cancellation exists because the
        solution is genuinely singular.
    """
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
    """Return a sympy expression as an NGSolve coefficient function in ``(x, y)``.

    ``ngsolve.x`` is the radial coordinate and ``ngsolve.y`` the axial one, per
    the (r, z) half-plane convention of ``mesh/primitives``. A tuple is returned
    as a vector coefficient function.
    """
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
    evaluate = sp.lambdify((RADIAL, AXIAL), expression, modules=[namespace, "math"])
    return ngs.CF(evaluate(ngs.x, ngs.y))


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
    """Return the relative ``r``-weighted L2 error of one field.

    The norm carries the same ``r`` weight as the weak forms, which is the norm
    the axisymmetric convergence theory is stated in; an unweighted norm would
    over-count the axis, where the true measure vanishes.
    """
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
    """Return the observed convergence rate between successive refinements.

    ``rate = log(e_coarse / e_fine) / log(h_coarse / h_fine)``. P2 elements
    should give 3 in the L2 norm (VER-18); the *observed* rate is the
    deliverable, not the number of levels it was measured over.

    Raises
    ------
    ValueError
        If fewer than two levels are given, or if an error has reached zero, in
        which case the ratio says nothing about the rate.
    """
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
