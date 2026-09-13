"""The residual stabilisation registry and its terms (NUM-11, NUM-14, NUM-15).

A stabilisation mode is named by string in the case file and resolved here. The
registry follows :mod:`nanopnp.materials.models` and
:mod:`nanopnp.physics.models` deliberately, so the three levels of pluggability
of section 5.5 are the same shape: a correction is a data file, a physics model
is one class, a stabilisation mode is one class.

**"Off" is a named model, not a code branch.** Selecting ``none`` resolves to
:class:`NoStabilisation`, whose term builders return ``None``, so
:meth:`~nanopnp.physics.models.CoupledModel.residual_form` carries no ``if`` on
the mode and the ablation of section 7.4 is a sweep over configurations rather
than three code paths. That is PHY-22's rule applied one level up.

Three modes are registered. ``none`` assembles nothing. ``supg`` assembles the
transport streamline term alone, which is the half of NUM-11 that asks for SUPG
behind a flag for coarse continuation meshes. ``reference`` assembles the
streamline term, the crosswind term and the flow GLS and grad-div pair, which is
NUM-14's reference setting table, and is the only registered mode that permits an
equal-order velocity-pressure pair (NUM-03).

The approximate residual
------------------------
NUM-14's "Approximate residual" is read as *every second derivative of a trial
field is dropped*, which leaves the advective residual and its source,

    R~_i = b~_i . grad(c~_i) - s~_i

with ``b~_i = z_i mu~_i grad(phi~) + D~_i beta~_i - Pe u~`` the non-diffusive part
of the PHY-04 flux bracket. Two consequences follow and neither is hidden.

The streamline term is **inconsistent by construction**: ``R~_i`` does not vanish
on the exact solution, because the diffusive second derivative is exactly what
was dropped. The added error is ``O(h^2)`` in ``L^2``, so the VER-18 manufactured
solution converges at 2 rather than at 3 in this mode. That is a property of the
mode (NUM-14's NOTE), measured by ``tests/tier2/test_stabilised_mode.py`` rather
than assumed away; a rate near 3 means the term is not being assembled and a rate
below 2 means the source ``s~_i`` never reached ``R~_i``.

And none of the streamline, crosswind or GLS integrands carries a ``1/r`` factor,
because the approximate residual never forms the axisymmetric divergence. Only
the grad-div term does, through ``div^(u~) = d_r u_r + u_r/r + d_z u_z``, and it
declares ``singular=True`` (NUM-07). A later mode built on a *full* residual has
to revisit that.

Signs
-----
**This is the most dangerous part of the module.** The Nernst-Planck residual of
NUM-04 is written in the flux form ``int J~_i . grad(w) r``, and with
``J~_i = -[D~_i grad(c~_i) + b~_i c~_i]`` its diffusive part is
``-int D~_i grad(c~_i) . grad(w) r`` — *negative*. The residual assembled by this
package is therefore minus the coercive orientation the stabilisation literature
is written in, and the true advective velocity of the transport operator is
``-b~_i``, not ``b~_i``: a cation drifts *down* the potential gradient. Both signs
flip, and the consequence is that

- the streamline and crosswind terms enter the residual with a **minus**, the same
  sign as the Galerkin diffusion term they augment;
- the flow GLS term splits, because the two rows of the momentum-continuity
  residual do *not* share an orientation. The velocity row is the coercive one
  (``+int 2 eta~ eps(u):eps(v)``), so its GLS contribution enters with a plus; the
  continuity row is ``-int q rho~ div^(u~) r``, which is minus the orientation in
  which ``+tau_m int grad(q).grad(p~)`` is the stabilising pressure block, so the
  pressure-test part of the GLS term enters with a **minus**. Writing the GLS
  operator ``(Re rho~ (u~.grad)v + grad(q))`` as one signed term, as a reading of
  section 6.4.2 invites, would stabilise one row and destabilise the other.

The oracle for all of this is not arithmetic: it is
``tests/tier2/test_stabilised_mode.py``, where plain Galerkin on a coarse mesh
trips the NUM-17 positivity gate and ``reference`` does not. A flipped sign makes
that test worse, not silent.

Parameters are evaluated at the iterate
---------------------------------------
``tau_i``, ``nu_K``, ``tau_m``, ``tau_c`` and the crosswind projector ``P_b`` are
built from a ``GridFunction`` — the solve's own state — rather than from the trial
functions. NGSolve treats a grid function in an integrand as data, so the
parameters follow the current iterate on every ``Apply`` and are omitted from the
linearisation: COMSOL's ``nojac()`` in one line, and no new Newton hook. It keeps
``max(0, .)`` and ``1/||grad c~||`` out of the Jacobian, where they would wreck
the damping policy NUM-16 tunes, and the converged fixed point is unchanged
because at convergence the lagged parameter *is* the current one. NUM-16's
relative-update test on the undamped direction is the criterion that carries
this: relagging perturbs the residual by the size of the update, so a
residual-only test could stall at its floor.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol, TypeAlias

from nanopnp.core.typing import Expression, IntegralTerm, Mesh, Numeric, Option
from nanopnp.physics.coefficients import NondimensionalCoefficients
from nanopnp.physics.measures import Measures
from nanopnp.physics.nernst_planck import ConcentrationVariables, steric_flux

__all__ = [
    "CROSSWIND_BONUS_ORDER",
    "CROSSWIND_COEFFICIENT",
    "FLOW_BONUS_ORDER",
    "GRAD_DIV_COEFFICIENT",
    "STREAMLINE_BONUS_ORDER",
    "STREAMLINE_CUTOFF",
    "FlowState",
    "NoStabilisation",
    "ReferenceStabilisation",
    "StabilisationIntegrand",
    "StabilisationModel",
    "StreamlineStabilisation",
    "TransportState",
    "advective_velocity",
    "approximate_residual",
    "cell_peclet",
    "create",
    "crosswind_projector",
    "crosswind_viscosity",
    "element_size",
    "register",
    "registered_stabilisations",
    "streamline_parameter",
]

STREAMLINE_CUTOFF = 1.0
"""The cut-off of ``psi(q) = min(q, 1)`` in the streamline parameter (section 6.4.1).

From Chaudhry, Comer, Aksimentiev & Olson, *Commun. Comput. Phys.* **15**, 93
(2014), which section 6.4.1 names: ``sigma_i = (h_tau / 2||b_i||) psi(Pe_tau)``.
The same paper reports the spurious negative concentrations near charged nanopore
walls that this mode exists to remove.
"""

CROSSWIND_COEFFICIENT = 1.0
"""``C_cw`` of the Do Carmo-Galeao-type crosswind term (NUM-14).

COMSOL exports neither ``tds.crosswind`` nor its tuning, so this reproduces the
*family* — residual-scaled, acting across the streamline, vanishing where the
element Peclet number is at or below ``1/C_cw`` — and not the operator
(``.knowledge/09-comsol-reference-settings.md`` section F). At 1 the term is
identically zero on every mesh meeting NUM-30, and active on exactly the elements
where NUM-12's warning fires.

A numerics constant of a named mode, not a fitted parameter: it is deliberately
**not** a case-file field, because a case that could retune it would make
``reference`` mean a different operator per run while the manifest recorded one
word. A variant is a second registered entry.
"""

GRAD_DIV_COEFFICIENT = 0.5
"""The coefficient of ``tau_c = C Re rho~ ||u~|| h_K`` in the grad-div term.

One half, so that ``tau_c = Re rho~ ||u~|| h_K / 2``, the standard scaling. At
``Re = 6e-4`` this is about ``9e-6`` and the term is numerically inert here; it is
assembled regardless, so the mode is not silently specific to this Reynolds
number.
"""

SHAKIB_CONVECTIVE = 2.0
SHAKIB_VISCOUS = 4.0
"""The two branches of the Shakib momentum parameter.

``tau_m = [(2 Re rho~ ||u~|| / h_K)^2 + (4 eta~ / h_K^2)^2]^(-1/2)``. At
``Re = 6e-4``, ``h~ = 0.03`` and ``||u~|| ~ 1`` the convective branch is ``4.0e-2``
against the viscous ``4.4e+3``: five orders below it, so the flow stabilisation
here is pure PSPG and the ``tau_m int grad(q).grad(p~)`` piece inside the GLS
operator is the whole of what makes the equal-order pair legal (NUM-03).
"""

STREAMLINE_BONUS_ORDER = 4
"""Quadrature bonus for the streamline term (NUM-15).

NUM-15 asks for integration order 4, and its NOTE reads that as a lower bound:
:class:`~nanopnp.physics.measures.Measures` takes a *bonus* over an
integrand-dependent estimate rather than an absolute order, so a bonus of 4
guarantees at least 4. Overshoot costs quadrature points, not correctness.
"""

CROSSWIND_BONUS_ORDER = 6
"""Quadrature bonus for the crosswind term (NUM-15), read as a lower bound.

The reference exported ``tds.crosswind`` at order 6, and because the term is
identically zero wherever ``C_cw Pe_K <= 1`` that cost is paid only on the
elements where it buys something.
"""

FLOW_BONUS_ORDER = 4
"""Quadrature bonus for the flow GLS and grad-div terms.

The reference assembled ``spf.streamlinens`` and ``spf.crosswindns`` at order 2.
That is superseded here: the grad-div integrand carries ``u_r/r``, so NUM-07's
minimum governs irrespective of the reference's setting (section 6.2's NOTE), and
the GLS integrand carries a product of three fields.
"""

WIND_FLOOR = 1.0e-30
"""Denominator guard on ``||b~_i||`` and ``||u~||``, in nondimensional units.

Not a tuning constant: ``tau_i`` and the crosswind projector both divide by a
speed, and the diffusive branch of ``tau_i`` is the finite limit of a ``0/0``.
Small enough to be invisible against any speed a solve produces — the relative
perturbation at ``||b~|| ~ 1`` is ``1e-30`` — and large enough that the unselected
branch of the ``IfPos`` cannot overflow.
"""

WIND_THRESHOLD = 1.0e-12
"""Below this ``||b~_i||`` the crosswind term is switched off entirely.

There is no crosswind without a wind. With ``b~_i = 0`` the projector degenerates
to the identity and ``nu_K`` would be driven by the source alone, which is
*isotropic* artificial diffusion — the one setting the reference had explicitly
off (NUM-14). Gating it here keeps ``reference`` from quietly becoming a mode the
reference did not run.
"""


def element_size() -> Expression:
    """Return ``h_K``, the element size the stabilisation parameters are built on.

    ``ngsolve.specialcf.mesh_size``, which on a triangle is **measured** to be
    exactly ``sqrt(2|K|)`` — the leg of the right isoceles triangle of the same
    area, and ``0.9306`` times the side of the equilateral one. Verified
    elementwise to a maximum relative deviation of ``2.4e-15`` over a 14-element
    unstructured mesh (`.knowledge/06-numerics-fem.md` section 2, VER-41).

    Pinned by measurement rather than by assumption because every ``tau`` in this
    module is defined against it: a silent change to NGSolve's convention would
    retune the whole mode with no diagnostic. A direction-dependent streamline
    length ``h_b = 2 / sum_a |b^.grad N_a|`` would be sharper but needs per-element
    basis gradients NGSolve does not expose as a coefficient function; the
    isotropic measure is standard and the 7 % gap to the edge length sits inside
    the tuning constant.
    """
    import ngsolve as ngs

    return ngs.specialcf.mesh_size


@dataclass(frozen=True)
class StabilisationIntegrand:
    """One stabilisation contribution, with the quadrature it must be taken at.

    The contributions are produced once and consumed twice: assembled into the
    residual through :meth:`~nanopnp.physics.measures.Measures.volume`, and
    evaluated against the NUM-24 indicator through
    :meth:`~nanopnp.physics.measures.Measures.integrate`. One expression, two
    routes — which is what makes the NUM-26 agreement an identity rather than a
    coincidence (section 6.7's NOTE).

    Parameters
    ----------
    integrand
        The unweighted integrand; the ``r`` weight is applied by ``Measures``.
    extra_order
        Quadrature bonus (NUM-15).
    singular
        Whether the integrand carries a ``1/r`` factor (NUM-07).
    """

    integrand: Expression
    extra_order: int = 0
    singular: bool = False


@dataclass(frozen=True)
class TransportState:
    """Everything a transport stabilisation term needs about one species.

    Built twice per species: once from the trial functions, which the term is
    linear in and Newton differentiates, and once from the solve's state grid
    function, which supplies the lagged parameters. The two are the same class so
    that no caller can accidentally read a parameter from the trial side.

    Parameters
    ----------
    species
        Ion name.
    coefficients
        The nondimensional coefficients evaluated on this side's concentrations.
    variables
        The concentrations and their gradients (NUM-02, either branch).
    potential
        The dimensionless potential ``phi~``.
    velocity
        The dimensionless velocity ``u~``, or ``None`` for a model with no flow.
    steric
        Whether ``beta~_i`` is part of the advective velocity, which follows the
        model's own switch (PHY-05, PHY-22).
    """

    species: str
    coefficients: NondimensionalCoefficients
    variables: ConcentrationVariables
    potential: Expression
    velocity: Expression | None
    steric: bool = True

    @property
    def diffusivity(self) -> Expression:
        """Return ``D~_i``."""
        return self.coefficients.diffusivity(self.species)

    @property
    def concentration_gradient(self) -> Expression:
        """Return ``grad(c~_i)``, in whichever NUM-02 branch is in force."""
        return self.variables.gradients[self.species]


@dataclass(frozen=True)
class FlowState:
    """Everything the flow stabilisation needs about the momentum block.

    Parameters
    ----------
    coefficients
        The nondimensional coefficients evaluated on this side's concentrations.
    velocity, pressure
        ``u~`` and ``p~``.
    density
        ``rho~``, or 1 when ``variable_density`` is off (PHY-07).
    body_force
        ``f~``, the body force the momentum equation carries — the PHY-08
        electrical force, plus the PHY-23 dielectric one where that deviation is
        enabled. Passed in rather than rebuilt, so the residual the stabilisation
        is built on cannot drift from the one the Galerkin form assembles.
    inertia
        Whether the convective momentum term is part of the residual (PHY-22).
    source
        ``s~_u``, the manufactured momentum source when one is present.
    """

    coefficients: NondimensionalCoefficients
    velocity: Expression
    pressure: Expression
    density: Numeric = 1.0
    body_force: Expression | None = None
    inertia: bool = True
    source: Expression | None = None


def _magnitude(vector: Expression) -> Expression:
    """Return ``||vector||``, exactly; see :data:`WIND_FLOOR` for the reciprocal."""
    import ngsolve as ngs

    return ngs.sqrt(vector * vector)


def _absolute(scalar: Expression) -> Expression:
    """Return ``|scalar|`` without a square root, which ``Diff`` would not like."""
    import ngsolve as ngs

    return ngs.IfPos(scalar, scalar, -scalar)


def _positive_part(scalar: Expression) -> Expression:
    """Return ``max(0, scalar)``."""
    import ngsolve as ngs

    return ngs.IfPos(scalar, scalar, 0.0)


def advective_velocity(state: TransportState) -> Expression:
    """Return ``b~_i``, the non-diffusive part of the PHY-04 flux bracket.

    ``b~_i = z_i mu~_i grad(phi~) + D~_i beta~_i - Pe u~``, assembled in the same
    order and with the same signs as
    :func:`~nanopnp.physics.nernst_planck.species_flux` builds the bracket, so
    that ``J~_i = -[D~_i grad(c~_i) + b~_i c~_i]`` holds term for term. Taking
    ``b~_i`` as the migration term alone would stabilise an operator the solver
    does not solve, and the steric drift is the term that diverges when its sign
    is wrong.

    Note that the **true** advective velocity of the transport operator is
    ``-b~_i``: a cation drifts down the potential gradient and the convective term
    carries ions with the flow. ``b~_i`` is used throughout because both signs of
    the pair (residual orientation and advective direction) flip together; see the
    module docstring.

    The PHY-23 dielectric-decrement drift is deliberately absent. Its leading part
    is a Hessian of ``phi~``, which "Approximate residual" drops, and the
    remainder is dropped with it: the stabilisation parameter is a numerical
    device on a term that is already inconsistent by construction, and a
    deviation-only contribution to it would buy nothing.
    """
    import ngsolve as ngs

    coefficients = state.coefficients
    ion = coefficients.electrolyte.ion(state.species)
    velocity = float(ion.valence) * coefficients.mobility(state.species) * ngs.grad(state.potential)
    if state.steric:
        velocity = velocity + state.diffusivity * steric_flux(
            state.variables,
            packing_coefficients=coefficients.packing_coefficients,
            volume_ratio=coefficients.steric_volume_ratio(state.species),
        )
    if state.velocity is not None:
        velocity = velocity - coefficients.peclet * state.velocity
    return velocity


def cell_peclet(state: TransportState, *, size: Expression | None = None) -> Expression:
    """Return ``Pe_K = ||b~_i|| h_K / (2 D~_i)`` (NUM-12).

    Evaluated on the advective velocity the solver actually assembles rather than
    on section 6.4.1's printed ``Pe_h = 1/2 |z_i| |grad phi~| h~``, which assumes
    the Einstein relation. PHY-14 and VER-05 forbid that at finite concentration:
    ``D_i/mu_i`` drifts to 1.2-1.7 x kT/e between 0.15 M and 3 M, so the printed
    form overestimates this one by that factor and errs towards warning early
    (NUM-12's NOTE).

    Parameters
    ----------
    state
        The state to evaluate at; the converged one, for a diagnostic.
    size
        ``h_K``; :func:`element_size` by default.
    """
    return (
        _magnitude(advective_velocity(state))
        * (element_size() if size is None else size)
        / (2.0 * state.diffusivity)
    )


def approximate_residual(state: TransportState, *, source: Expression | None = None) -> Expression:
    """Return ``R~_i = b~_i . grad(c~_i) - s~_i``, the residual of NUM-14's NOTE.

    Every second derivative of a trial field is dropped, which is what
    "Approximate residual" is taken to mean, and the source is **not**: leaving
    the manufactured ``s~_i`` out of ``R~_i`` is the single easiest mistake in this
    module, and it shows up as a stabilised MMS rate below 2 rather than as an
    error (VER-42).
    """
    residual = advective_velocity(state) * state.concentration_gradient
    if source is not None:
        residual = residual - source
    return residual


def streamline_parameter(
    state: TransportState,
    *,
    size: Expression | None = None,
    cutoff: float = STREAMLINE_CUTOFF,
) -> Expression:
    """Return ``tau_i = (h_K / 2||b~_i||) psi(Pe_K)`` with ``psi(q) = min(q, 1)``.

    Written as the two branches rather than as a ``min``, because the diffusive
    branch is the finite limit of a ``0/0``:

    - ``Pe_K <= 1``: ``tau_i = h_K^2 / (4 D~_i)``, exactly, since the ``||b~_i||``
      cancels. The artificial streamline diffusivity ``tau_i ||b~_i||^2`` is then
      ``Pe_K^2 D~_i`` — a ratio to the physical diffusivity independent of every
      material parameter, which is where section 6.4.1's ``zeta~^2/100`` on a mesh
      built to NUM-30 comes from.
    - ``Pe_K > 1``: ``tau_i = h_K / (2 ||b~_i||)``.

    The two agree at ``Pe_K = 1``, so ``tau_i`` is continuous at the crossover.
    """
    import ngsolve as ngs

    h = element_size() if size is None else size
    speed = _magnitude(advective_velocity(state))
    diffusivity = state.diffusivity
    peclet = speed * h / (2.0 * diffusivity)
    return ngs.IfPos(
        peclet - cutoff,
        h / (2.0 * (speed + WIND_FLOOR)),
        h * h / (4.0 * diffusivity),
    )


def crosswind_projector(state: TransportState) -> Expression:
    """Return ``P_b = I - b^ (x) b^``, the projector across the streamline.

    ``P_b b~_i = 0`` and ``P_b P_b = P_b``, both to round-off (VER-41). Built from
    the lagged state, so the ``1/||b~_i||`` inside ``b^`` never reaches the
    Jacobian.
    """
    import ngsolve as ngs

    direction = advective_velocity(state)
    unit = direction / (_magnitude(direction) + WIND_FLOOR)
    return ngs.Id(2) - ngs.OuterProduct(unit, unit)


def crosswind_viscosity(
    state: TransportState,
    *,
    source: Expression | None = None,
    size: Expression | None = None,
    coefficient: float = CROSSWIND_COEFFICIENT,
) -> Expression:
    """Return ``nu_K = max(0, C_cw h_K ||R~_i|| / (2||grad c~_i||) - D~_i)`` (NUM-14).

    The Do Carmo-Galeao-*type* parameter: residual-scaled, and switching itself
    off where the solution is smooth. In production ``s~_i = 0``, so
    ``R~_i = b~_i . grad(c~_i)`` exactly and Cauchy-Schwarz gives
    ``||R~_i|| <= ||b~_i|| ||grad c~_i||``, whence

        nu_K  <=  D~_i max(0, C_cw Pe_K - 1)

    so ``nu_K`` is **identically zero wherever ``C_cw Pe_K <= 1``** — everywhere on
    a mesh meeting NUM-30 — and is bounded above by the diffusivity that brings the
    effective cell Peclet number to ``1/C_cw``, so it cannot run away. It vanishes
    continuously at ``Pe_K = 1`` and is not differentiable there, which is the
    second reason the parameter is lagged rather than differentiated.

    Below :data:`WIND_THRESHOLD` the term is switched off outright: with no wind
    the projector degenerates to the identity and this would become isotropic
    artificial diffusion, which the reference had off.
    """
    import ngsolve as ngs

    h = element_size() if size is None else size
    residual = _absolute(approximate_residual(state, source=source))
    gradient = _magnitude(state.concentration_gradient)
    raw = coefficient * h * residual / (2.0 * (gradient + WIND_FLOOR)) - state.diffusivity
    return ngs.IfPos(
        _magnitude(advective_velocity(state)) - WIND_THRESHOLD, _positive_part(raw), 0.0
    )


def momentum_residual(state: FlowState) -> Expression:
    """Return ``R~_m = grad(p~) + Re rho~ (u~.grad)u~ - f~ - s~_u`` (section 6.4.2).

    The viscous second derivative is dropped on the same rule as the transport
    residual, which is also why this integrand carries no ``1/r``: the momentum
    equation's ``1/r`` lives in ``div^`` and in the hoop strain, and neither
    survives the approximation.
    """
    import ngsolve as ngs

    residual = ngs.grad(state.pressure)
    if state.inertia:
        residual = residual + state.coefficients.reynolds * state.density * (
            ngs.grad(state.velocity) * state.velocity
        )
    if state.body_force is not None:
        residual = residual - state.body_force
    if state.source is not None:
        residual = residual - state.source
    return residual


def momentum_parameter(state: FlowState, *, size: Expression | None = None) -> Expression:
    """Return the Shakib parameter ``tau_m`` of section 6.4.2.

    ``tau_m = [(2 Re rho~ ||u~|| / h_K)^2 + (4 eta~ / h_K^2)^2]^(-1/2)``. The
    viscous branch bounds it away from infinity at zero velocity, so this needs no
    floor of its own.
    """
    import ngsolve as ngs

    h = element_size() if size is None else size
    convective = (
        SHAKIB_CONVECTIVE
        * state.coefficients.reynolds
        * state.density
        * _magnitude(state.velocity)
        / h
    )
    viscous = SHAKIB_VISCOUS * state.coefficients.viscosity() / (h * h)
    return 1.0 / ngs.sqrt(convective * convective + viscous * viscous)


def grad_div_parameter(state: FlowState, *, size: Expression | None = None) -> Expression:
    """Return ``tau_c = Re rho~ ||u~|| h_K / 2`` (section 6.4.2)."""
    h = element_size() if size is None else size
    return (
        GRAD_DIV_COEFFICIENT
        * state.coefficients.reynolds
        * state.density
        * _magnitude(state.velocity)
        * h
    )


class StabilisationModel(Protocol):
    """One residual stabilisation mode, as section 6.4 requires it (NUM-13, NUM-14).

    Implementations are immutable and carry their own provenance, so a result can
    record the mode, its tuning parameters and where they came from (FR-25,
    section 5.3.3). "reference" alone does not distinguish ``C_cw = 1`` from
    ``C_cw = 0.35``.
    """

    @property
    def name(self) -> str:
        """Registered name of the mode."""
        ...

    @property
    def parameters(self) -> Mapping[str, float]:
        """The tuning constants in force, flattened for reporting."""
        ...

    @property
    def provenance(self) -> Mapping[str, str]:
        """Where the mode and its constants came from."""
        ...

    @property
    def terms(self) -> tuple[str, ...]:
        """The terms this mode assembles, in assembly order; empty for ``none``.

        Read by :meth:`~nanopnp.physics.models.CoupledModel.residual_form` to decide
        whether a solve state is required, which is the one thing a caller must know
        about a mode before building it. Deliberately not "is this mode ``none``":
        a future mode that assembles nothing under some configuration gets the same
        treatment without being special-cased by name.
        """
        ...

    @property
    def permits_equal_order(self) -> bool:
        """Whether this mode supplies the flow stabilisation NUM-03 requires.

        An equal-order velocity-pressure pair is LBB-unstable without the PSPG
        content of the flow GLS term, so only a mode that assembles it may be
        paired with one.
        """
        ...

    def transport_term(
        self,
        measures: Measures,
        *,
        trial: TransportState,
        lagged: TransportState,
        test: Expression,
        source: Expression | None = None,
        **kwargs: Option,
    ) -> IntegralTerm | None:
        """Return this mode's contribution to one species' residual, or ``None``."""
        ...

    def flow_term(
        self,
        measures: Measures,
        *,
        trial: FlowState,
        lagged: FlowState,
        velocity_test: Expression,
        pressure_test: Expression,
        **kwargs: Option,
    ) -> IntegralTerm | None:
        """Return this mode's contribution to the flow residual, or ``None``."""
        ...

    def indicator_term(
        self,
        measures: Measures,
        mesh: Mesh,
        *,
        state: TransportState,
        indicator: Expression,
        source: Expression | None = None,
        **kwargs: Option,
    ) -> float:
        """Return ``S_i(c~; psi)``, this mode's contribution to the NUM-24 current."""
        ...


@dataclass(frozen=True)
class NoStabilisation:
    """The ``none`` mode: unstabilised Galerkin (NUM-11).

    Assembles nothing. Selecting it is how the production policy of NUM-11 is
    expressed — as a named model rather than as a code branch (PHY-22) — so the
    residual a ``none`` run assembles is bit-for-bit the residual of a solver
    that had never heard of stabilisation. ``tests/tier1/test_stabilisation.py``
    asserts that on the assembled vector rather than on the mode string.
    """

    @property
    def name(self) -> str:  # noqa: D102 - documented on the protocol
        return "none"

    @property
    def parameters(self) -> Mapping[str, float]:  # noqa: D102
        return {}

    @property
    def provenance(self) -> Mapping[str, str]:  # noqa: D102
        return {
            "mode": "none",
            "terms": "",
            "note": "unstabilised Galerkin; no term is assembled (NUM-11)",
        }

    @property
    def terms(self) -> tuple[str, ...]:  # noqa: D102
        return ()

    @property
    def permits_equal_order(self) -> bool:  # noqa: D102
        return False

    def transport_term(  # noqa: D102
        self,
        measures: Measures,
        *,
        trial: TransportState,
        lagged: TransportState,
        test: Expression,
        source: Expression | None = None,
        **kwargs: Option,
    ) -> IntegralTerm | None:
        del measures, trial, lagged, test, source, kwargs
        return None

    def flow_term(  # noqa: D102
        self,
        measures: Measures,
        *,
        trial: FlowState,
        lagged: FlowState,
        velocity_test: Expression,
        pressure_test: Expression,
        **kwargs: Option,
    ) -> IntegralTerm | None:
        del measures, trial, lagged, velocity_test, pressure_test, kwargs
        return None

    def indicator_term(  # noqa: D102
        self,
        measures: Measures,
        mesh: Mesh,
        *,
        state: TransportState,
        indicator: Expression,
        source: Expression | None = None,
        **kwargs: Option,
    ) -> float:
        del measures, mesh, state, indicator, source, kwargs
        return 0.0


@dataclass(frozen=True)
class StreamlineStabilisation:
    """``supg``: the transport streamline term alone (NUM-11).

    The half of NUM-11 that asks for SUPG behind a flag for coarse continuation
    meshes, and the rung of WP13's attribution ladder that separates the transport
    streamline term from the crosswind and the flow pair. It does **not** permit an
    equal-order velocity-pressure pair: it assembles no flow term, so there is no
    PSPG content to make one legal (NUM-03).

    Parameters
    ----------
    crosswind, flow
        Which further terms are assembled. Both off here; :class:`ReferenceStabilisation`
        is this class with both on, which is what makes ``reference`` a
        configuration rather than a second implementation.
    crosswind_coefficient
        ``C_cw``; see :data:`CROSSWIND_COEFFICIENT`.
    streamline_cutoff
        The ``psi`` cut-off; see :data:`STREAMLINE_CUTOFF`.
    """

    crosswind: bool = False
    flow: bool = False
    crosswind_coefficient: float = CROSSWIND_COEFFICIENT
    streamline_cutoff: float = STREAMLINE_CUTOFF

    @property
    def name(self) -> str:  # noqa: D102
        return "supg"

    @property
    def permits_equal_order(self) -> bool:  # noqa: D102
        # Read off the flow term rather than declared per class: the pair is legal
        # exactly when the PSPG content of the GLS term is assembled, so a mode
        # that claimed otherwise would be claiming something about an operator it
        # does not build.
        return self.flow

    @property
    def parameters(self) -> Mapping[str, float]:  # noqa: D102
        values = {"streamline_cutoff": float(self.streamline_cutoff)}
        if self.crosswind:
            values["crosswind_coefficient"] = float(self.crosswind_coefficient)
        if self.flow:
            values["grad_div_coefficient"] = GRAD_DIV_COEFFICIENT
            values["shakib_convective"] = SHAKIB_CONVECTIVE
            values["shakib_viscous"] = SHAKIB_VISCOUS
        return values

    @property
    def terms(self) -> tuple[str, ...]:
        """Return the names of the terms this mode assembles, in assembly order."""
        assembled = ["streamline"]
        if self.crosswind:
            assembled.append("crosswind")
        if self.flow:
            assembled += ["flow_gls", "grad_div"]
        return tuple(assembled)

    @property
    def provenance(self) -> Mapping[str, str]:  # noqa: D102
        return {
            "mode": self.name,
            "terms": ",".join(self.terms),
            "residual": "approximate: every second derivative of a trial field dropped (NUM-14)",
            "element_size": "ngsolve.specialcf.mesh_size = sqrt(2|K|), measured (VER-41)",
            "parameters_evaluated_at": "iterate",
            "streamline_source": (
                "Chaudhry, Comer, Aksimentiev & Olson, Commun. Comput. Phys. 15, 93 (2014); "
                "SPECIFICATION.md section 6.4.1"
            ),
            "crosswind_source": (
                "Do Carmo-Galeao type, SPECIFICATION.md NUM-14; COMSOL's own tds.crosswind is "
                "not exported"
                if self.crosswind
                else "off"
            ),
            "flow_source": (
                "GLS with the Shakib parameter plus grad-div, SPECIFICATION.md section 6.4.2"
                if self.flow
                else "off"
            ),
            "integration_bonus": (
                f"streamline {STREAMLINE_BONUS_ORDER}, crosswind {CROSSWIND_BONUS_ORDER}, "
                f"flow {FLOW_BONUS_ORDER} (NUM-15, lower bounds)"
            ),
        }

    # -- the terms ---------------------------------------------------------

    def transport_contributions(
        self,
        *,
        trial: TransportState,
        lagged: TransportState,
        test: Expression,
        source: Expression | None = None,
    ) -> tuple[StabilisationIntegrand, ...]:
        """Return the transport contributions as unweighted integrands.

        Produced once and consumed by both :meth:`transport_term` and
        :meth:`indicator_term`, so the residual and the NUM-24 indicator
        functional cannot carry different expressions of the same term.

        Both contributions enter with a **minus**, the sign of the Galerkin
        diffusion term they augment in this flux-form residual; see the module
        docstring.
        """
        import ngsolve as ngs

        size = element_size()
        drift = advective_velocity(trial)
        residual = approximate_residual(trial, source=source)
        tau = streamline_parameter(lagged, size=size, cutoff=self.streamline_cutoff)
        contributions = [
            StabilisationIntegrand(
                -tau * residual * (drift * ngs.grad(test)),
                extra_order=STREAMLINE_BONUS_ORDER,
            )
        ]
        if self.crosswind:
            viscosity = crosswind_viscosity(
                lagged,
                source=source,
                size=size,
                coefficient=self.crosswind_coefficient,
            )
            projected = crosswind_projector(lagged) * trial.concentration_gradient
            contributions.append(
                StabilisationIntegrand(
                    -viscosity * (projected * ngs.grad(test)),
                    extra_order=CROSSWIND_BONUS_ORDER,
                )
            )
        return tuple(contributions)

    def transport_term(  # noqa: D102
        self,
        measures: Measures,
        *,
        trial: TransportState,
        lagged: TransportState,
        test: Expression,
        source: Expression | None = None,
        **kwargs: Option,
    ) -> IntegralTerm | None:
        contributions = self.transport_contributions(
            trial=trial, lagged=lagged, test=test, source=source
        )
        return _assemble(measures, contributions, **kwargs)

    def flow_term(  # noqa: D102
        self,
        measures: Measures,
        *,
        trial: FlowState,
        lagged: FlowState,
        velocity_test: Expression,
        pressure_test: Expression,
        **kwargs: Option,
    ) -> IntegralTerm | None:
        if not self.flow:
            return None
        import ngsolve as ngs

        from nanopnp.physics.flow import axisymmetric_divergence

        size = element_size()
        tau_m = momentum_parameter(lagged, size=size)
        tau_c = grad_div_parameter(lagged, size=size)
        residual = momentum_residual(trial)
        reynolds = trial.coefficients.reynolds

        # The velocity row is the coercive orientation, so its GLS contribution
        # enters with a plus; the continuity row is written as -int q rho~ div^(u~),
        # which is minus the orientation in which +tau_m int grad(q).grad(p~) is the
        # stabilising pressure block, so the pressure-test part enters with a
        # minus. One signed term for both would stabilise one row and destabilise
        # the other; see the module docstring.
        convective_test = reynolds * lagged.density * (ngs.grad(velocity_test) * lagged.velocity)
        # The third contribution is grad-div, on the velocity row and therefore
        # also with a plus. It is the one new term carrying a 1/r factor, through
        # div^(u~) = d_r u_r + u_r/r + d_z u_z, so it is the one integrated with
        # the singular rule (VER-07).
        return _assemble(
            measures,
            (
                StabilisationIntegrand(
                    tau_m * (residual * convective_test), extra_order=FLOW_BONUS_ORDER
                ),
                StabilisationIntegrand(
                    -tau_m * (residual * ngs.grad(pressure_test)), extra_order=FLOW_BONUS_ORDER
                ),
                StabilisationIntegrand(
                    tau_c
                    * axisymmetric_divergence(velocity_test, measures)
                    * axisymmetric_divergence(trial.velocity, measures),
                    extra_order=FLOW_BONUS_ORDER,
                    singular=True,
                ),
            ),
            **kwargs,
        )

    def indicator_term(  # noqa: D102
        self,
        measures: Measures,
        mesh: Mesh,
        *,
        state: TransportState,
        indicator: Expression,
        source: Expression | None = None,
        **kwargs: Option,
    ) -> float:
        total = 0.0
        for index, contribution in enumerate(
            self.transport_contributions(trial=state, lagged=state, test=indicator, source=source)
        ):
            total += measures.integrate(
                contribution.integrand,
                mesh,
                singular=contribution.singular,
                extra_order=contribution.extra_order,
                what=f"the {self.name!r} stabilisation term {index} of {state.species!r}",
                **kwargs,
            )
        return total


@dataclass(frozen=True)
class ReferenceStabilisation(StreamlineStabilisation):
    """``reference``: NUM-14's whole setting table.

    Streamline **and** crosswind in the transport equations, and the GLS and
    grad-div pair in the flow, which is the mode section 7.4's like-for-like
    comparison against the published currents needs. It is the only registered
    mode that permits an equal-order velocity-pressure pair, because it is the
    only one assembling the PSPG content that makes one legal (NUM-03).

    The flow terms are assembled on a Taylor-Hood pair as well. The attribution
    ladder of the phase plan is ``none`` + P2/P1, ``reference`` + P2/P1,
    ``reference`` + P1/P1, so the middle configuration has to be "the whole
    stabilisation, the stable pair"; the flow terms are consistent, so on a stable
    pair they are asymptotically inert rather than wrong.
    """

    crosswind: bool = True
    flow: bool = True

    @property
    def name(self) -> str:  # noqa: D102
        return "reference"


def _assemble(
    measures: Measures,
    contributions: tuple[StabilisationIntegrand, ...],
    **kwargs: Option,
) -> IntegralTerm | None:
    """Return the sum of ``contributions`` as one integral term, or ``None`` if empty."""
    if not contributions:
        return None
    terms = [
        measures.volume(
            contribution.integrand,
            singular=contribution.singular,
            extra_order=contribution.extra_order,
            **kwargs,
        )
        for contribution in contributions
    ]
    total = terms[0]
    for term in terms[1:]:
        total = total + term
    return total


ModelBuilder: TypeAlias = Callable[[], StabilisationModel]
"""Builds one stabilisation mode. The tuning constants are not case-file fields."""

_REGISTRY: dict[str, ModelBuilder] = {}


def register(name: str, builder: ModelBuilder) -> None:
    """Register a stabilisation mode under ``name``.

    Raises
    ------
    ValueError
        If the name is already registered, which would silently change the
        meaning of existing case files.
    """
    if name in _REGISTRY:
        raise ValueError(f"stabilisation mode {name!r} is already registered")
    _REGISTRY[name] = builder


def registered_stabilisations() -> tuple[str, ...]:
    """Return every selectable mode name, sorted."""
    return tuple(sorted(_REGISTRY))


def create(name: str) -> StabilisationModel:
    """Build the stabilisation mode registered as ``name``.

    Raises
    ------
    KeyError
        If no such mode is registered; the message lists the known names.
    """
    try:
        builder = _REGISTRY[name]
    except KeyError:
        known = ", ".join(registered_stabilisations())
        raise KeyError(
            f"unknown stabilisation mode {name!r}; registered modes are {known}"
        ) from None
    return builder()


register("none", NoStabilisation)
register("supg", StreamlineStabilisation)
register("reference", ReferenceStabilisation)
