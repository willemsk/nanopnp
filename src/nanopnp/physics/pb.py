"""Poisson-Boltzmann, linear and nonlinear (PHY-21, PHY-24, FR-19).

Poisson-Boltzmann is a **distinct physics model**, not the PNP solver evaluated
at zero bias. In ePNP-NS the diffusivity and the mobility carry different
concentration corrections, so the model violates the Einstein relation at finite
concentration and its zero-bias limit is not a Boltzmann distribution (PHY-14).
Treating PB as "PNP at V = 0" would therefore be wrong in exactly the regime
where PB is most useful.

Both variants are written in the **nondimensional potential** ``phi~ = phi/V_T``
with lengths in the mesh's unit (nm, per ``mesh.primitives``). In those variables
the equations carry no material constants at all:

    linear (Debye-Hueckel):   -laplacian(phi~) + phi~ / lambda^2      = 0
    nonlinear:                -laplacian(phi~) + sinh(phi~)/lambda^2  = 0

for a symmetric monovalent electrolyte, with ``lambda`` the Debye length in mesh
units. That is the NUM-09 scaling, and it is why these two rungs of the
continuation ladder are cheap and robust enough to initialise everything else.
"""

from __future__ import annotations

import logging

from nanopnp.core.constants import (
    REFERENCE_TEMPERATURE_K,
    VACUUM_PERMITTIVITY,
    thermal_voltage,
)
from nanopnp.core.scaling import REFERENCE_PERMITTIVITY, debye_length_nm
from nanopnp.core.typing import Expression, GridFunction, IntegralTerm, Mesh, Option
from nanopnp.physics.measures import Measures
from nanopnp.physics.poisson import poisson_operator
from nanopnp.physics.spaces import set_boundary_values
from nanopnp.solve.gates import FieldSampler, PotentialIncrementGate
from nanopnp.solve.linear import DEFAULT_SOLVER, solve_linear
from nanopnp.solve.newton import (
    DEFAULT_SETTINGS,
    NewtonResult,
    NewtonSettings,
    damped_newton,
)

__all__ = [
    "ELECTROLYTE_PERMITTIVITY",
    "debye_length_nm",
    "linear_pb_operator",
    "nonlinear_pb_residual",
    "solve_pb",
    "solve_pb_recorded",
]

logger = logging.getLogger(__name__)

ELECTROLYTE_PERMITTIVITY = REFERENCE_PERMITTIVITY
"""``eps_r,f0``, the infinite-dilution relative permittivity of the electrolyte.

Gavish 2016, via SPECIFICATION.md section 8.2 and
``.knowledge/01-physics-epnpns.md`` section 4; it is the ``P0`` of the
``permittivity`` correction in ``data/corrections/willems2020_nacl.yaml``. Held
once, in ``core.scaling``, so the scaling layer and the forms cannot disagree
about it.
"""


def dimensionless_surface_charge(
    surface_charge_C_m2: float,
    *,
    relative_permittivity: float,
    temperature_K: float = REFERENCE_TEMPERATURE_K,
    length_nm: float = 1.0,
) -> float:
    """Return the Neumann datum a surface charge imposes on ``phi~``.

    ``d phi~ / d n = sigma_s L / (eps_0 eps_r V_T)`` with ``n`` the outward
    normal of the electrolyte, which is Gauss's law at a charged plane written
    in the variables the Poisson-Boltzmann solver works in.

    The permittivity is an argument rather than :data:`ELECTROLYTE_PERMITTIVITY`
    because it must be the *same* one the caller built its Debye length from: the
    PB operator carries no ``eps`` at all — it enters only through ``lambda`` —
    so a permittivity assumed here and a different one assumed there would be
    silently inconsistent, and the profile would still converge.

    Parameters
    ----------
    surface_charge_C_m2
        The surface charge density, SI.
    relative_permittivity
        The electrolyte's ``eps_r``.
    temperature_K
        Sets ``V_T = RT/F``.
    length_nm
        The mesh's length unit in nm; 1 by default, as every mesh here is in nm.
    """
    return (
        surface_charge_C_m2
        * length_nm
        * 1e-9
        / (VACUUM_PERMITTIVITY * relative_permittivity * thermal_voltage(temperature_K))
    )


def linear_pb_operator(
    trial: Expression,
    test: Expression,
    measures: Measures,
    *,
    debye_length_nm: float,
    ions: Option | None = None,
) -> IntegralTerm:
    """Return the Debye-Hueckel operator ``int (grad phi~ . grad v + phi~ v / lambda^2) r``.

    ``ions`` restricts the screening term to a region, as in
    :func:`nonlinear_pb_residual`; Laplace's equation holds outside it.
    """
    screening = 1.0 / debye_length_nm**2
    return poisson_operator(trial, test, measures) + measures.volume(
        screening * trial * test, **_ion_region(ions)
    )


def _ion_region(ions: Option | None) -> dict[str, Option]:
    """Return the ``definedon`` keyword for the mobile-charge term, if restricted.

    Omitted rather than passed as the whole mesh so that the unrestricted form
    assembles exactly the term it did before an ion-free layer was expressible.
    """
    return {} if ions is None else {"definedon": ions}


def nonlinear_pb_residual(
    potential: Expression,
    test: Expression,
    measures: Measures,
    *,
    debye_length_nm: float,
    ions: Option | None = None,
) -> IntegralTerm:
    """Return the nonlinear PB residual ``int (grad phi~ . grad v + sinh(phi~) v / lambda^2) r``.

    The ``sinh`` is the Boltzmann-distributed mobile charge of a symmetric
    monovalent electrolyte: ``rho_ion = -2 F c_0 sinh(phi~)``.

    ``ions`` is the region the mobile charge occupies — a material selection, not
    the whole mesh — and the Poisson operator is still assembled everywhere. That
    is the Gouy-Chapman-**Stern** model: an ion-free layer of thickness
    ``lambda_S`` against the wall carries no space charge, so ``phi`` is linear
    across it and the diffuse layer beyond it is unchanged (VER-31, FR-15). It is
    a deviation from the validated model, which has no explicit Stern layer, and
    is recorded as one wherever a mesh presents the region (§5.3.1 NOTE).

    ``potential`` MUST be the **trial function**, not the grid function holding
    the current iterate. NGSolve linearises a nonlinear form by differentiating
    with respect to the trial function and substituting the state vector in
    ``AssembleLinearization``; a form written directly in terms of a grid
    function assembles a Jacobian that is **identically zero**, with no error
    raised, and Newton then fails with "matrix is singular" from the linear
    solver rather than from the actual mistake.
    """
    import ngsolve as ngs

    screening = 1.0 / debye_length_nm**2
    return poisson_operator(potential, test, measures) + measures.volume(
        screening * ngs.sinh(potential) * test, **_ion_region(ions)
    )


def solve_pb(
    mesh: Mesh,
    measures: Measures,
    *,
    debye_length_nm: float,
    dirichlet: str,
    boundary_values: Expression,
    ions: str | None = None,
    surface_charge: float = 0.0,
    surface_charge_boundary: str = "wall",
    nonlinear: bool = True,
    order: int = 2,
    solver: str = DEFAULT_SOLVER,
    settings: NewtonSettings = DEFAULT_SETTINGS,
    initial: GridFunction | None = None,
) -> GridFunction:
    """Solve Poisson-Boltzmann and return the nondimensional potential.

    A thin wrapper over :func:`solve_pb_recorded`, which returns the convergence
    record as well. Use that one where the record is needed — a continuation rung
    whose Newton history goes into the FR-25 manifest — and this one where it is
    not.

    Parameters
    ----------
    mesh
        Meshed domain.
    measures
        Symmetry and quadrature policy; its ``element_order`` must match
        ``order``, which is checked.
    debye_length_nm
        Debye length in mesh units.
    dirichlet
        Boundary-name regular expression carrying the essential condition. The
        axis must not appear here: its condition is natural (NUM-06).
    boundary_values
        Values to set on those boundaries, in units of ``V_T``.
    ions
        Material-name regular expression naming where the mobile charge is, for
        a Gouy-Chapman-Stern layer; ``None`` puts it everywhere, which is plain
        Gouy-Chapman. Poisson is solved over the whole mesh either way.
    surface_charge, surface_charge_boundary
        A prescribed surface charge on a boundary, as the Neumann datum
        :func:`dimensionless_surface_charge` returns. The natural condition
        under these forms is the free one, so a boundary carrying neither an
        essential value nor a datum is uncharged — which is the right default and
        the reason this is stated positively rather than as an absence.
    nonlinear
        Solve the full ``sinh`` form, or the Debye-Hueckel linearisation.
    order
        Lagrange element order.
    solver
        Direct linear solver.
    settings
        Damping and tolerance policy for the nonlinear branch.
    initial
        A previous potential to warm-start from, on the same mesh and at the
        same order. NUM-18 stage 2 warm-starts the nonlinear branch from the
        linear one, which is the whole reason both are on the ladder.

    Returns
    -------
    GridFunction
        The converged ``phi~``.

    Raises
    ------
    ValueError
        If ``measures.element_order`` does not match ``order``.
    RuntimeError
        If the nonlinear branch does not converge.

    Notes
    -----
    The nonlinear branch runs the project's own damped Newton (NUM-16) with the
    potential-increment gate of NUM-17 active. That gate is a real constraint
    here rather than a formality: ``sinh`` grows exponentially, so an undamped
    step from ``phi~ = 0`` at a large zeta potential overshoots by orders of
    magnitude, and capping the increment at one thermal voltage is what keeps
    the first few steps inside the range where the linearisation means anything.

    The concentration and packing gates do not apply — Poisson-Boltzmann carries
    no independent concentration field, its ion densities being slaved to the
    potential by construction.
    """
    return solve_pb_recorded(
        mesh,
        measures,
        debye_length_nm=debye_length_nm,
        dirichlet=dirichlet,
        boundary_values=boundary_values,
        ions=ions,
        surface_charge=surface_charge,
        surface_charge_boundary=surface_charge_boundary,
        nonlinear=nonlinear,
        order=order,
        solver=solver,
        settings=settings,
        initial=initial,
    )[0]


def solve_pb_recorded(
    mesh: Mesh,
    measures: Measures,
    *,
    debye_length_nm: float,
    dirichlet: str,
    boundary_values: Expression,
    ions: str | None = None,
    surface_charge: float = 0.0,
    surface_charge_boundary: str = "wall",
    nonlinear: bool = True,
    order: int = 2,
    solver: str = DEFAULT_SOLVER,
    settings: NewtonSettings = DEFAULT_SETTINGS,
    initial: GridFunction | None = None,
) -> tuple[GridFunction, NewtonResult | None]:
    """Solve Poisson-Boltzmann, returning the potential and its convergence record.

    The record is ``None`` for the linear branch, which is a single linear solve
    and has no Newton history. Arguments are those of :func:`solve_pb`.

    It exists because a rung of the NUM-18 ladder must be able to say how it
    converged: a rung with no record has not been solved, whatever it returned,
    and FR-25 asks the manifest to carry the history rather than the log.
    """
    import ngsolve as ngs

    if measures.element_order != order:
        raise ValueError(
            f"measures.element_order is {measures.element_order} but the space is order {order}; "
            "the quadrature bonus of NUM-07 is computed from the element order, so a mismatch "
            "under-integrates the forms it is meant to protect"
        )

    space = ngs.H1(mesh, order=order, dirichlet=dirichlet)
    potential = ngs.GridFunction(space, name="phi_tilde")
    if initial is not None:
        potential.vec.data = initial.vec
    # ``Set(..., definedon=)`` zeroes everything outside the region, so the
    # essential data is written through the same projector split the coupled
    # model uses; on a cold start the interior is zero either way.
    set_boundary_values(potential, boundary_values, mesh.Boundaries(dirichlet))

    region = None if ions is None else mesh.Materials(ions)
    if region is not None and region.Mask().NumSet() == 0:
        raise ValueError(
            f"ions={ions!r} matches no material of the mesh; it carries "
            f"{', '.join(sorted(set(mesh.GetMaterials())))}. A screening term restricted to "
            "nothing would solve Laplace's equation and converge"
        )
    charged = None if surface_charge == 0.0 else mesh.Boundaries(surface_charge_boundary)
    if charged is not None and charged.Mask().NumSet() == 0:
        raise ValueError(
            f"surface_charge_boundary={surface_charge_boundary!r} matches no boundary of the "
            f"mesh; it carries {', '.join(sorted(set(mesh.GetBoundaries())))}. A charge applied "
            "to nothing leaves the wall uncharged and the solve converges (NUM-06, QR-12)"
        )

    def _charge_term(test: Expression, *, sign: float) -> IntegralTerm | None:
        """Return the surface-charge term, if there is one, with ``sign`` applied.

        The sign is folded into the integrand rather than negated afterwards:
        NGSolve's ``SumOfIntegrals`` has no unary minus, and a form built and then
        subtracted is a ``TypeError`` rather than a wrong answer only because of
        that.
        """
        if charged is None:
            return None
        return measures.surface(sign * surface_charge * test, definedon=charged)

    if not nonlinear:
        trial, test = space.TnT()
        a = ngs.BilinearForm(
            linear_pb_operator(trial, test, measures, debye_length_nm=debye_length_nm, ions=region)
        ).Assemble()
        f = ngs.LinearForm(space)
        term = _charge_term(test, sign=1.0)
        if term is not None:
            f += term
        f.Assemble()
        solve_linear(a, f, potential, solver=solver)
        return potential, None

    trial, test = space.TnT()
    residual = ngs.BilinearForm(space)
    residual += nonlinear_pb_residual(
        trial, test, measures, debye_length_nm=debye_length_nm, ions=region
    )
    # The Poisson boundary term is +int_Gamma (dphi~/dn) v ds on the right-hand
    # side, so it is subtracted from the residual exactly as
    # CoupledModel.residual_form subtracts its own.
    term = _charge_term(test, sign=-1.0)
    if term is not None:
        residual += term

    increment = ngs.GridFunction(space, name="delta_phi_tilde")
    sampler = FieldSampler(mesh, coordinates=measures.coordinate_names)
    result = damped_newton(
        residual,
        potential,
        settings=settings,
        solver=solver,
        increment=increment,
        increment_gates=[PotentialIncrementGate(sampler, increment)],
    )
    logger.debug("nonlinear Poisson-Boltzmann converged: %s", result.summary())
    return potential, result
