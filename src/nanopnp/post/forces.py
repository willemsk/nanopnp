"""The axial force on an embedded analyte (NUM-28, NUM-29).

Three routes, and none of them is optional.

* **Route A, the domain form of NUM-28.** With ``w`` a smooth vector field equal
  to ``e_z`` on the body and zero on every other boundary, the divergence theorem
  turns the surface traction into a volume integral over the shell where ``w``
  varies::

      F_z = - int_Omega T : grad(w) dV - int_Omega (div T) . w dV

  It is the force analogue of the NUM-24 indicator current, and it is preferred
  for the same reason: a continuous-Galerkin traction evaluated on one facet ring
  is noisy, and a volume integral over a band averages that noise away.
* **Route B, the surface form.** ``F_z = surface_int (T . n_B) . e_z dS`` taken
  over the body's own boundary. The cross-check NUM-28 asks for.
* **Route C, the variational reaction force.** The analyte surface is a Dirichlet
  boundary for ``u``, so pairing the assembled momentum residual with a test
  function equal to ``e_z`` there returns the hydrodynamic force *discretely
  exactly* - and, because the residual vanishes on every free degree of freedom,
  **exactly independently of** ``w``. It is the NUM-25 reaction flux one rank up,
  and it is the oracle for the split.

The consistency term, and why the split needs it
------------------------------------------------
The printed NUM-28 form keeps only the first integral, which is exact **iff**
``div T = 0`` in the fluid. In this model it is not. With ``T = T_M + T_H``,

    div T_H = -f_total + Re rho (u.grad) u        (PHY-07, PHY-08)
    div T_M = rho_ion E - 1/2 |E|^2 grad(eps)

so each component carries its own body-force term:

    F^em = - int T_M : grad(w) - int f_ion . w - int f_KH . w
    F^hd = - int T_H : grad(w) + int f_total . w - Re int rho (u.grad)u . w

with ``f_ion = rho_ion E`` the PHY-08 electrical body force and
``f_KH = -1/2 |E|^2 grad(eps)`` the Korteweg-Helmholtz force. Omitting those
terms leaves each component a function of *where the band was put* - an O(10 pN)
function, since ``int f_ion . w`` is the electrical force on all the fluid inside
the shell. RSK-04 is precisely that the net force is a small difference of two
large opposite ones, so a split that depends on the band is the plausible wrong
answer this module exists to prevent.

They cancel in the sum when the momentum equation carries every force the Maxwell
tensor implies, that is when ``f_total = f_ion + f_KH``. The validated model
deliberately omits ``f_KH`` (PHY-23), so with the permittivity correction active
they do not cancel, and NUM-28 *as printed* - the stress-work integral alone -
falls short of the true total by exactly ``-int f_KH . w``. Routes A and B still
agree with each other, because each of route A's components carries the
divergence of the tensor that component was built from; what disagrees with them
is the printed form. That gap is reported as
:attr:`AnalyteForces.dielectric_gradient_N` rather than left as a mystery: it is
a *measurement* of the omission. Classically it is identically zero, which is why
VER-22 gates there.

No ``1/r``, and why
-------------------
``w`` is axial, so ``(grad w)_phi,phi = w_r / r = 0`` and the hoop components of
both tensors are contracted against zero: ``T : grad(w) = T_rz d_r w_z +
T_zz d_z w_z``. The integrals still go through
:class:`~nanopnp.physics.measures.Measures`, for the ``r`` weight, the
integration-order floor and the non-finite abort, but ``singular=True`` would be
cargo cult here and is not claimed. The same holds for every consistency term.

The ``2 pi`` (NUM-27's NOTE)
----------------------------
Every integral arrives short of the azimuthal Jacobian that ``Measures``
cancelled from the weak form, and this module restores it exactly once, through
:data:`~nanopnp.post.qoi.TWO_PI`, at the same boundary
:mod:`nanopnp.post.qoi` does. The force scale is
:attr:`~nanopnp.core.scaling.Scales.force_N`, ``eps V_T^2`` = 0.4568 pN, which
does not depend on the reference length.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from nanopnp.core.typing import (
    AssembledForm,
    Expression,
    GridFunction,
    Mesh,
    Numeric,
    Option,
)
from nanopnp.geometry.analyte import ANALYTE_BOUNDARY
from nanopnp.mesh.distance import wall_distance
from nanopnp.mesh.primitives import ELECTROLYTE_DOMAINS
from nanopnp.physics.coefficients import NondimensionalCoefficients
from nanopnp.physics.flow import permittivity_gradient
from nanopnp.physics.measures import Measures
from nanopnp.physics.models import POTENTIAL, PRESSURE, VELOCITY, CoupledModel, ModelSolution
from nanopnp.post.indicator import smoothstep
from nanopnp.post.qoi import TWO_PI
from nanopnp.post.reaction_flux import boundary_reaction_flux

__all__ = [
    "FORCE_ROUTE_TOLERANCE_N",
    "AnalyteForces",
    "ExtensionError",
    "ForceAgreement",
    "ForceComponents",
    "ForceDisagreementError",
    "axial_extension",
    "check_extension",
    "domain_force",
    "electrostatic_domain_force",
    "electrostatic_surface_force",
    "extract",
    "hydrodynamic_stress",
    "maxwell_stress",
    "reaction_force",
    "surface_force",
]

logger = logging.getLogger(__name__)

FORCE_ROUTE_TOLERANCE_N = 1.0e-13
"""The NUM-29 route-agreement tolerance: 0.1 pN, **absolute**.

Absolute and not relative, and that is the whole point. At the reference
operating point the two components are about +10 pN and -10 pN, so their sum is a
small difference of two large numbers; a relative test on that sum measures the
cancellation rather than the discretisation, and passes trivially on a total that
happens to be near zero. In the nondimensional scaling 0.1 pN is 0.219 force
units, whatever the pore radius, because ``force_N = eps V_T^2`` carries no
length (RSK-04, NUM-29).
"""


class ExtensionError(ValueError):
    """``w`` is not the smooth extension of ``e_z`` that NUM-28 needs.

    An inverted band puts ``e_z`` on the outer boundary and zero on the body,
    which returns the force on the *reservoir* with no other symptom; a band
    that has run off the end of the domain makes ``grad(w)`` vanish and every
    force zero. Both are silent, so both abort here (QR-12).
    """


class ForceDisagreementError(RuntimeError):
    """Two of the NUM-28 routes disagree beyond the tolerance.

    One of them is wrong and the numbers cannot say which, so no force is
    reported (QR-12).
    """


# -- the test function -------------------------------------------------------


def axial_extension(
    mesh: Mesh,
    *,
    inner_nm: float,
    outer_nm: float,
    order: int = 2,
    fluid: str = ELECTROLYTE_DOMAINS,
    body: str = ANALYTE_BOUNDARY,
    axis: str = "axis",
    distance_nm: GridFunction | None = None,
    check: bool = True,
) -> GridFunction:
    """Return ``w``: ``e_z`` within ``inner_nm`` of the body, 0 beyond ``outer_nm``.

    Built as ``(1 - S(d)) e_z`` from the distance to the body's own surface
    through the C1 smoothstep of :func:`~nanopnp.post.indicator.smoothstep`, so
    that ``grad(w)`` is continuous at both ends of the shell and the force
    converges in the band width rather than oscillating with it.

    **Interpolated, and on the fluid alone.** Writing degrees of freedom instead
    would hit the hierarchical-basis trap that
    :func:`~nanopnp.post.reaction_flux.boundary_indicator` documents - a P2 edge
    whose nominal coefficients are 1 integrates to 11/12 of its length. And
    restricting to the fluid is what makes ``w`` *exactly* zero on the far
    boundary, for the same reason the NUM-24 indicator is restricted: an element
    of the solid straddling the band would share its corner vertex with a
    boundary the extension has to vanish on.

    ``inner_nm`` must exceed the element size next to the body. ``Set``
    interpolates elementwise, so an element on which ``d`` runs from 0 up past
    ``inner_nm`` returns a projection that is *not* exactly ``e_z`` on the
    surface, and the traction the force is taken over is then scaled by a number
    slightly below 1. :func:`check_extension` is what catches that.

    Parameters
    ----------
    mesh
        The meshed domain, carrying the body as a named boundary.
    inner_nm, outer_nm
        Ends of the transition shell, as distances from the body's surface in nm.
    order
        Element order. It must match the fields the force integrand is built
        from, or ``grad(w)`` is represented more coarsely than the stress.
    fluid
        Material-name regular expression the extension lives on.
    body
        Boundary-name regular expression of the analyte surface.
    axis
        Boundary name of the symmetry axis, excluded from the "``w`` vanishes
        here" check: the axis runs through the body's own poles and ``w`` is
        ``e_z`` there by construction.
    distance_nm
        The distance field to build the shell from. Defaults to a Varadhan solve
        against ``body``. Its *accuracy* barely matters - the total force is
        independent of ``w`` - but its exactness at ``d = 0`` does, and
        :func:`~nanopnp.mesh.distance.wall_distance` zeroes the source degrees of
        freedom outright for that reason.

        The default solve is run at a diffusion length of a quarter of the shell
        width rather than at
        :data:`~nanopnp.mesh.distance.DEFAULT_DIFFUSION_LENGTH_NM`, which is
        sized for the sub-nanometre wall corrections. An unresolved screened
        Poisson oscillates, and where it undershoots the exponential floor the
        recovered ``d`` jumps to the cap *inside an element touching the body* -
        so ``S(d)`` is no longer zero there, and ``w`` comes off the surface at
        1 - 1e-4 rather than at 1. The shell is what this field has to resolve.
    check
        Whether to verify the result with :func:`check_extension`.

    Raises
    ------
    ExtensionError
        If the shell has no width or starts inside the body, or - through
        :func:`check_extension` - if the interpolated ``w`` misses either of the
        two boundary values NUM-28's derivation assumes.
    """
    import ngsolve as ngs

    if outer_nm <= inner_nm:
        raise ExtensionError(
            f"the transition shell must have positive width, got inner={inner_nm} nm and "
            f"outer={outer_nm} nm"
        )
    if inner_nm < 0.0:
        raise ExtensionError(f"inner_nm must not be negative, got {inner_nm} nm")

    if distance_nm is None:
        distance_nm = wall_distance(
            mesh,
            body,
            order=order,
            diffusion_length_nm=(outer_nm - inner_nm) / 4.0,
            max_distance_nm=2.0 * outer_nm,
        )
    space = ngs.VectorH1(mesh, order=order, definedon=mesh.Materials(fluid))
    extension = ngs.GridFunction(space, name="w")
    profile = 1.0 - smoothstep(distance_nm, lower_nm=inner_nm, upper_nm=outer_nm)
    extension.Set(ngs.CF((0.0, profile)))
    if check:
        check_extension(extension, mesh, body=body, axis=axis, fluid=fluid)
    return extension


def _outer_boundaries(mesh: Mesh, body: str, axis: str, fluid: str) -> str:
    """Return the boundaries of the fluid that are neither the body nor the axis.

    Built from the mesh's own vocabulary rather than asked of the caller, so
    that a geometry with an unexpected boundary is checked rather than skipped.
    Both ``body`` and ``axis`` are matched as the boundary-name regular
    expressions they are declared to be, through the mesh's own matcher.

    Interfaces *interior to the fluid* are left out. NUM-28 integrates over the
    fluid, and the divergence theorem asks for ``w`` to vanish on the boundary
    of that domain only; an interface with electrolyte on both sides is not part
    of it. :class:`~nanopnp.geometry.analyte.PoreWithAnalyte` has two of them --
    the pore mouths, which carry netgen's automatic name ``default`` and
    separate the lumen from the reservoirs -- so demanding ``w = 0`` there would
    abort a body sitting within a shell width of a mouth, and blame an inverted
    shell for it. The membrane interface is *not* interior to the fluid and is
    kept.
    """
    on_body = mesh.Boundaries(body).Mask()
    on_axis = mesh.Boundaries(axis).Mask()
    fluid_mask = mesh.Materials(fluid).Mask()
    # ``domin``/``domout`` are 1-based material numbers, 0 meaning the outside;
    # the descriptors are in the order of ``GetBoundaries``.
    descriptors = list(mesh.ngmesh.EdgeDescriptors())

    def _interior_to_the_fluid(index: int) -> bool:
        descriptor = descriptors[index]
        return all(
            side > 0 and fluid_mask[side - 1] for side in (descriptor.domin, descriptor.domout)
        )

    names = sorted(
        {
            name
            for index, name in enumerate(mesh.GetBoundaries())
            if not on_body[index] and not on_axis[index] and not _interior_to_the_fluid(index)
        }
    )
    return "|".join(names)


def check_extension(
    extension: GridFunction,
    mesh: Mesh,
    *,
    body: str = ANALYTE_BOUNDARY,
    axis: str = "axis",
    fluid: str = ELECTROLYTE_DOMAINS,
    tolerance: float = 1e-12,
) -> None:
    """Assert that ``w`` is ``e_z`` on the body and zero on every other boundary.

    Parameters
    ----------
    extension
        The extension to check.
    mesh
        The meshed domain.
    body
        Boundary-name regular expression of the analyte surface.
    axis
        Boundary name of the symmetry axis, which the body's poles sit on and
        where ``w`` is therefore ``e_z``, not zero.
    fluid
        Material-name regular expression of the domain NUM-28 integrates over.
        Interfaces with fluid on both sides are interior to it and are not
        checked; see :func:`_outer_boundaries`.
    tolerance
        Mean-square departure permitted on each boundary. Tight, because the
        requirement is exactness and not approximate separation: NUM-28 is a
        surface traction rewritten as a volume integral, and the rewriting holds
        only if ``w`` takes those two values exactly.

    Raises
    ------
    ExtensionError
        If either condition fails, with the measured departures in the message.
    """
    import ngsolve as ngs

    def _mean_square(target: Expression, boundary: str) -> float:
        region = mesh.Boundaries(boundary)
        length = float(ngs.Integrate(ngs.CF(1.0), mesh, definedon=region))
        if length <= 0.0:
            known = ", ".join(sorted(set(mesh.GetBoundaries())))
            raise ExtensionError(f"no boundary matching {boundary!r} in this mesh; it has {known}")
        difference = extension - ngs.CF(target)
        deviation = float(
            ngs.Integrate(ngs.InnerProduct(difference, difference), mesh, definedon=region)
        )
        return deviation / length

    outer = _outer_boundaries(mesh, body, axis, fluid)
    on_body = _mean_square((0.0, 1.0), body)
    on_outer = _mean_square((0.0, 0.0), outer) if outer else 0.0
    if on_body > tolerance or on_outer > tolerance:
        raise ExtensionError(
            f"w must be e_z on {body!r} and zero on {outer!r}; the mean-square departures are "
            f"{on_body:.3e} and {on_outer:.3e} against a tolerance of {tolerance:.3e}. An "
            "inverted shell returns the force on the reservoir and a shell wider than the "
            "domain returns zero, neither with any other symptom. If only the body fails, "
            "inner_nm is smaller than the element size there"
        )
    logger.debug("w is e_z on %r and 0 on %r: %.2e, %.2e", body, outer, on_body, on_outer)


# -- the stress tensors ------------------------------------------------------


def maxwell_stress(potential_gradient: Expression, permittivity: Numeric) -> Expression:
    """Return the in-plane Maxwell stress ``eps (E .x. E - 1/2 |E|^2 I)``.

    Taken in the *nondimensional* variables, where ``E~ = -grad(phi~)`` and the
    permittivity is the ratio ``eps~_r``: the pressure scale ``p_0 = eps V_T^2 /
    a^2`` is exactly the scale of this tensor, so no prefactor survives. ``E``
    appears twice, so the sign of ``E`` does not matter and the gradient is used
    as it stands.

    Parameters
    ----------
    potential_gradient
        ``grad(phi~)``, in the fluid.
    permittivity
        ``eps~_r`` in the fluid. The **fluid** value: the force on the body is
        the traction of the surrounding medium on it, so the solid's own
        permittivity never enters this tensor.

    Returns
    -------
    Expression
        The two-by-two in-plane tensor. The hoop component is omitted because an
        axial ``w`` contracts it against zero; see the module docstring.
    """
    import ngsolve as ngs

    field = potential_gradient
    return permittivity * (
        ngs.OuterProduct(field, field) - 0.5 * ngs.InnerProduct(field, field) * ngs.Id(2)
    )


def hydrodynamic_stress(
    velocity_gradient: Expression, pressure: Expression, viscosity: Numeric
) -> Expression:
    """Return the in-plane hydrodynamic stress ``-p I + 2 eta sym grad(u)``.

    The sign convention is the one NUM-28 states and the one the momentum
    residual of :mod:`nanopnp.physics.flow` is written in: ``div T_H + f = Re rho
    (u.grad) u``, so a positive ``p`` pushes outward. ``.knowledge/05`` section 4
    writes the same tensor with the opposite overall sign; the traction and the
    force flip with it and the physics does not, but the two must never be mixed.

    Taken from the gradient rather than from the velocity, because the surface
    route needs the volume gradient lifted to the boundary and
    :func:`~nanopnp.physics.flow.strain_rate` takes the function itself.

    Parameters
    ----------
    velocity_gradient
        ``grad(u~)``, with ``grad(u)[i, j] = d u_i / d x_j``.
    pressure
        ``p~``.
    viscosity
        ``eta~``, which is position-dependent whenever the wall correction is
        active.
    """
    import ngsolve as ngs

    strain = 0.5 * (velocity_gradient + velocity_gradient.trans)
    return -pressure * ngs.Id(2) + 2.0 * viscosity * strain


# -- the results -------------------------------------------------------------


# -- the Maxwell half, for a model that solves only Poisson -------------------


def electrostatic_domain_force(
    mesh: Mesh,
    potential_gradient: Expression,
    permittivity: Numeric,
    extension: GridFunction,
    measures: Measures,
    *,
    force_N: float,
    fluid: str = ELECTROLYTE_DOMAINS,
) -> float:
    """Return ``-2 pi force_N int T_M : grad(w) r dr dz``, in newtons - route A's Maxwell half.

    Separated from :func:`domain_force` because the electromagnetic half is
    defined for any model that solves Poisson, and VER-20's dielectric sphere is
    exactly such a model: a body in a uniform applied field, with no ions to
    screen it and no flow. Composing the scale and the ``2 pi`` here rather than
    in each caller is what keeps NUM-27's "restored exactly once" checkable.

    It carries **no consistency term**: a caller whose fluid holds mobile charge
    or a permittivity gradient must add ``-int f_ion . w`` and ``-int f_KH . w``
    itself, as :func:`domain_force` does. Where the fluid is charge-free and
    uniform - the VER-20 configuration - both vanish and this is the whole force.

    Parameters
    ----------
    mesh
        The meshed domain.
    potential_gradient
        ``grad(phi~)``, in the fluid.
    permittivity
        ``eps~_r`` in the **fluid**; see :func:`maxwell_stress`.
    extension
        ``w``, from :func:`axial_extension`.
    measures
        The symmetry and quadrature policy.
    force_N
        :attr:`~nanopnp.core.scaling.Scales.force_N`, ``eps V_T^2``.
    fluid
        Material-name regular expression of the region to integrate over.
    """
    import ngsolve as ngs

    stress = maxwell_stress(potential_gradient, permittivity)
    work = measures.integrate(
        ngs.InnerProduct(stress, ngs.grad(extension)),
        mesh,
        definedon=mesh.Materials(fluid),
        what="the Maxwell stress work",
    )
    return -TWO_PI * force_N * work


def electrostatic_surface_force(
    mesh: Mesh,
    potential_gradient: Expression,
    permittivity: Numeric,
    measures: Measures,
    *,
    force_N: float,
    boundary: str = ANALYTE_BOUNDARY,
    piecewise_permittivity: Numeric | None = None,
) -> float:
    """Return ``2 pi force_N surface_int (T_M . n_B) . e_z r dl``, in newtons - route B's half.

    The cross-check of :func:`electrostatic_domain_force`, and the two guards
    :func:`surface_force` documents at length apply here in full: every
    coefficient is lifted with ``BoundaryFromVolumeCF`` because ``ngsolve.grad``
    on a boundary region returns only the tangential part, and the normal's
    orientation is measured rather than assumed.

    Parameters
    ----------
    mesh
        The meshed domain.
    potential_gradient
        ``grad(phi~)``, as a volume expression; it is lifted here.
    permittivity
        ``eps~_r`` in the fluid.
    measures
        The symmetry and quadrature policy.
    force_N
        :attr:`~nanopnp.core.scaling.Scales.force_N`.
    boundary
        The body's surface.
    piecewise_permittivity
        The permittivity over all of Omega, if it jumps across the surface.
        Supplying it enables the check that the lift landed on the fluid side,
        which is worth the argument: taking the body's side gives a traction
        wrong by the whole dielectric contrast, silently. ``None`` skips the
        check and is correct only where the permittivity is continuous.

    Raises
    ------
    ValueError
        If the boundary matches nothing, if the lift lands on the solid side, or
        if the normal's orientation cannot be determined.
    """
    import ngsolve as ngs

    region, arc = _boundary_region(mesh, boundary)
    lift = ngs.BoundaryFromVolumeCF
    fluid_permittivity = lift(permittivity)
    if piecewise_permittivity is not None:
        _check_fluid_side(mesh, lift(piecewise_permittivity), fluid_permittivity, region, arc)
    normal = _oriented_normal(mesh, region, arc)
    stress = maxwell_stress(lift(potential_gradient), fluid_permittivity)
    traction = measures.integrate(
        (stress * normal)[1], mesh, definedon=region, what="the Maxwell surface traction"
    )
    return TWO_PI * force_N * traction


@dataclass(frozen=True)
class ForceComponents:
    """The axial force on the body, split into its two origins, in newtons.

    The split is the quantity RSK-04 is about; the total is the easy part.
    """

    em_N: float
    hd_N: float

    @property
    def total_N(self) -> float:
        """The net axial force, ``F^em + F^hd``.

        Near-cancelling by construction at the reference operating point: two
        contributions of about 10 pN and opposite sign.
        """
        return self.em_N + self.hd_N

    def summary(self) -> dict[str, float]:
        """Return the three numbers, for logs and the manifest (FR-25)."""
        return {
            "electromagnetic_N": self.em_N,
            "hydrodynamic_N": self.hd_N,
            "total_N": self.total_N,
        }


@dataclass(frozen=True)
class ForceAgreement:
    """How far apart the NUM-28 routes are on one solution."""

    domain: ForceComponents
    surface: ForceComponents
    reaction_hd_N: float | None = None

    @property
    def total_difference_N(self) -> float:
        """``|F_tot(A) - F_tot(B)|``, the domain against the surface route."""
        return abs(self.domain.total_N - self.surface.total_N)

    @property
    def hydrodynamic_difference_N(self) -> float:
        """``|F^hd(A) - F^hd(C)|``, the split against its oracle; 0 without route C."""
        if self.reaction_hd_N is None:
            return 0.0
        return abs(self.domain.hd_N - self.reaction_hd_N)

    def check(self, tolerance_N: float = FORCE_ROUTE_TOLERANCE_N) -> None:
        """Assert the routes agree to within an absolute tolerance (NUM-29, VER-22).

        Raises
        ------
        ForceDisagreementError
            If they do not, naming every route's value in piconewtons and the
            two absolute differences.
        """
        total = self.total_difference_N
        hydrodynamic = self.hydrodynamic_difference_N
        if total <= tolerance_N and hydrodynamic <= tolerance_N:
            logger.debug(
                "force routes agree: total %.3e N, hydrodynamic %.3e N", total, hydrodynamic
            )
            return
        if self.reaction_hd_N is None:
            reaction = "not taken"
        else:
            reaction = f"{self.reaction_hd_N * 1e12:+.4f}"
        raise ForceDisagreementError(
            "the NUM-28 force routes disagree beyond the NUM-29 tolerance of "
            f"{tolerance_N * 1e12:.4f} pN. Domain (A): F^em = "
            f"{self.domain.em_N * 1e12:+.4f} pN, F^hd = {self.domain.hd_N * 1e12:+.4f} pN, "
            f"total {self.domain.total_N * 1e12:+.4f} pN. Surface (B): F^em = "
            f"{self.surface.em_N * 1e12:+.4f} pN, F^hd = {self.surface.hd_N * 1e12:+.4f} pN, "
            f"total {self.surface.total_N * 1e12:+.4f} pN. Reaction (C): F^hd = "
            f"{reaction} pN. The differences are {total * 1e12:.4f} pN on the total and "
            f"{hydrodynamic * 1e12:.4f} pN on the hydrodynamic split. A disagreement on the "
            "split alone points at a missing or mis-signed body-force consistency term; the "
            "net force is a small difference of two large ones and an error in either flips "
            "the trapping landscape (RSK-04)"
        )

    def summary(self) -> dict[str, Option]:
        """Return every route and both differences, for the manifest (FR-25)."""
        return {
            "domain": self.domain.summary(),
            "surface": self.surface.summary(),
            "reaction_hydrodynamic_N": self.reaction_hd_N,
            "total_difference_N": self.total_difference_N,
            "hydrodynamic_difference_N": self.hydrodynamic_difference_N,
        }


@dataclass(frozen=True)
class AnalyteForces:
    """The NUM-28 force on one body, in SI units, with its route record."""

    forces: ForceComponents
    dielectric_gradient_N: float
    agreement: ForceAgreement | None

    @property
    def total_N(self) -> float:
        """The net axial force, in newtons."""
        return self.forces.total_N

    def summary(self) -> dict[str, Option]:
        """Return every quantity, for logs and the provenance manifest (FR-25)."""
        record: dict[str, Option] = {
            **self.forces.summary(),
            # The PHY-23 term the validated model omits. It is already inside
            # ``electromagnetic_N``; reported on its own because it is exactly
            # the amount by which NUM-28 as printed falls short of that total.
            "dielectric_gradient_N": self.dielectric_gradient_N,
            "two_pi_included": True,
            "routes_checked": self.agreement is not None,
        }
        if self.agreement is not None:
            record["route_agreement"] = self.agreement.summary()
        return record


# -- the three routes --------------------------------------------------------


def _coupled(solution: ModelSolution) -> CoupledModel:
    """Return the solution's model, insisting it is one a force can be taken from.

    Raises
    ------
    TypeError
        If the model is not of the ePNP-NS family, or solves no flow block: the
        hydrodynamic half of NUM-28 does not exist without one, and reporting it
        as zero would claim the flow was computed and found to vanish.
    """
    model = solution.model
    if not isinstance(model, CoupledModel):
        raise TypeError(
            f"{model.name!r} is not a model of the epnp-ns family, so the NUM-28 force on an "
            "analyte is not defined for it"
        )
    if not model.flow:
        raise TypeError(
            f"{model.name!r} solves no flow block, so it has no hydrodynamic force to report; "
            "NUM-28 splits the force into an electromagnetic and a hydrodynamic half and "
            "reporting the second as zero would claim a computed result"
        )
    return model


@dataclass(frozen=True)
class _Integrands:
    """The nondimensional expressions both domain routes are built from."""

    model: CoupledModel
    mesh: Mesh
    coefficients: NondimensionalCoefficients
    potential_gradient: Expression
    velocity: Expression
    velocity_gradient: Expression
    pressure: Expression
    permittivity: Expression
    viscosity: Expression
    body_force: Expression
    korteweg_force: Expression | None
    mass_density: Expression
    reynolds: float

    def korteweg(self) -> Expression:
        """Return ``f_KH``, insisting the current branch can express it.

        Kept behind a call rather than built eagerly so that route B, which
        integrates a traction and needs no ``grad(eps)`` at all, stays available
        on the branch route A cannot be taken on.

        Raises
        ------
        NotImplementedError
            In the NUM-02 log branch with an active permittivity correction,
            where the Korteweg-Helmholtz term would need a derivative in ``w_i``.
        """
        if self.korteweg_force is None:
            raise NotImplementedError(
                "the NUM-28 electromagnetic force is not implemented for the NUM-02 log branch "
                "with an active permittivity correction: the Korteweg-Helmholtz consistency term "
                "needs d(eps~_r)/d(c~_i) and the symbolic derivative would come back in w_i"
            )
        return self.korteweg_force


def _integrands(solution: ModelSolution, wall_distance_nm: Expression | None) -> _Integrands:
    """Return the coefficients of the converged state, in the model's own variables.

    Rebuilt through the model's public seams against the distance field the
    solve recorded, exactly as
    :func:`~nanopnp.post.qoi.indicator_currents` does, so that the ``eta`` and
    ``eps`` in the stress are the ones the residual was assembled from.

    ``korteweg_force`` comes back ``None`` on the one branch that cannot express
    it; :meth:`_Integrands.korteweg` is what turns that into an error, and only
    for the routes that need the term.
    """
    import ngsolve as ngs

    model = _coupled(solution)
    mesh = solution.space.mesh
    distance = solution.wall_distance_nm if wall_distance_nm is None else wall_distance_nm
    functions = {field.name: solution.component(field.name) for field in model.fields}
    variables = model.concentration_variables(functions)
    coefficients = model.coefficients(variables, distance)

    field = ngs.grad(functions[POTENTIAL])
    permittivity = coefficients.relative_permittivity()
    # f_ion = rho_ion E = -S (sum_i z_i c~_i) grad(phi~); the same coefficient
    # the Poisson source carries, because it is the same charge (PHY-08).
    body_force = -coefficients.screening * coefficients.ionic_charge_density() * field

    if model.electrolyte.switches.permittivity.model == "none":
        # grad(eps) is identically zero, so the Korteweg-Helmholtz force is too,
        # and the symbolic chain rule need not be built at all - which is what
        # lets the log branch take a classical force.
        korteweg: Expression | None = ngs.CF((0.0, 0.0))
    elif variables.logarithmic:
        # d(eps~_r)/d(c~_i) would come back in w_i; see _Integrands.korteweg.
        korteweg = None
    else:
        korteweg = (
            -0.5 * ngs.InnerProduct(field, field) * permittivity_gradient(coefficients, variables)
        )

    velocity = functions[VELOCITY]
    return _Integrands(
        model=model,
        mesh=mesh,
        coefficients=coefficients,
        potential_gradient=field,
        velocity=velocity,
        velocity_gradient=ngs.grad(velocity),
        pressure=functions[PRESSURE],
        permittivity=permittivity,
        viscosity=coefficients.viscosity(),
        body_force=body_force,
        korteweg_force=korteweg,
        mass_density=coefficients.mass_density() if model.variable_density else 1.0,
        reynolds=coefficients.reynolds,
    )


def domain_force(
    solution: ModelSolution,
    measures: Measures,
    extension: GridFunction,
    *,
    wall_distance_nm: Expression | None = None,
) -> ForceComponents:
    """Return the NUM-28 domain force on the body, in newtons - **route A**.

    Each component carries its own body-force consistency term, for the reason
    the module docstring gives at length: without them the split is a function of
    where the shell was put, and the split is what RSK-04 is about.

    Parameters
    ----------
    solution
        A converged solution of a coupled model with a flow block.
    measures
        The symmetry and quadrature policy the model was solved with.
    extension
        ``w``, from :func:`axial_extension`.
    wall_distance_nm
        Overrides the distance field recorded on the solution; rebuilding the
        stress with a different one silently evaluates a different model.
    """
    return _domain_force(_integrands(solution, wall_distance_nm), measures, extension)[0]


def _korteweg_work(terms: _Integrands, measures: Measures, extension: GridFunction) -> float:
    """Return ``int f_KH . w``, nondimensional: the PHY-23 consistency term."""
    import ngsolve as ngs

    return measures.integrate(
        ngs.InnerProduct(terms.korteweg(), extension),
        terms.mesh,
        definedon=terms.mesh.Materials(terms.model.fluid),
        what="the dielectric-gradient consistency term",
    )


def _domain_force(
    terms: _Integrands, measures: Measures, extension: GridFunction
) -> tuple[ForceComponents, float]:
    """Return route A's force and the ``int f_KH . w`` it had to evaluate anyway.

    The second return value is what :func:`dielectric_gradient_residual`
    reports, handed back rather than re-integrated so that :func:`extract`
    quadratures it once instead of twice.
    """
    import ngsolve as ngs

    mesh, model = terms.mesh, terms.model
    fluid = mesh.Materials(model.fluid)
    gradient = ngs.grad(extension)
    scale = TWO_PI * model.scales.force_N

    def integrate(integrand: Expression, what: str) -> float:
        return measures.integrate(integrand, mesh, definedon=fluid, what=what)

    hydro = hydrodynamic_stress(terms.velocity_gradient, terms.pressure, terms.viscosity)
    ionic_work = integrate(
        ngs.InnerProduct(terms.body_force, extension), "the ionic body-force consistency term"
    )
    korteweg_work = _korteweg_work(terms, measures, extension)

    em_N = electrostatic_domain_force(
        mesh,
        terms.potential_gradient,
        terms.permittivity,
        extension,
        measures,
        force_N=model.scales.force_N,
        fluid=model.fluid,
    )
    em_N -= scale * (ionic_work + korteweg_work)

    hd = -integrate(ngs.InnerProduct(hydro, gradient), "the hydrodynamic stress work")
    hd += ionic_work
    if model.dielectric_gradient_forces:
        # The momentum equation carries f_KH too, so f_total = f_ion + f_KH and
        # the two components' consistency terms cancel exactly in the sum.
        hd += korteweg_work
    if model.inertia:
        convective = ngs.InnerProduct(terms.velocity_gradient * terms.velocity, extension)
        hd -= terms.reynolds * integrate(
            terms.mass_density * convective, "the inertial consistency term"
        )

    forces = ForceComponents(em_N=em_N, hd_N=scale * hd)
    logger.debug("domain force (pN): %s", {k: v * 1e12 for k, v in forces.summary().items()})
    return forces, korteweg_work


def dielectric_gradient_residual(
    solution: ModelSolution,
    measures: Measures,
    extension: GridFunction,
    *,
    wall_distance_nm: Expression | None = None,
) -> float:
    """Return ``-int f_KH . w`` in newtons, the PHY-23 term the model omits.

    Zero classically and zero with ``dielectric_gradient_forces`` enabled, where
    the momentum equation carries the force and the two consistency terms cancel.
    In between - the validated configuration, permittivity correction on and the
    Korteweg-Helmholtz force off - it is exactly the amount by which NUM-28 as
    printed, the stress-work integral alone, falls short of the force the three
    routes agree on, and reporting it turns that gap from a mystery into a
    measurement of the PHY-23 omission.
    """
    return _dielectric_gradient_residual(
        _integrands(solution, wall_distance_nm), measures, extension
    )


def _dielectric_gradient_residual(
    terms: _Integrands,
    measures: Measures,
    extension: GridFunction,
    *,
    work: float | None = None,
) -> float:
    """Return ``-int f_KH . w`` in newtons, reusing ``work`` if route A found it."""
    if terms.model.dielectric_gradient_forces:
        return 0.0
    if work is None:
        work = _korteweg_work(terms, measures, extension)
    return -TWO_PI * terms.model.scales.force_N * work


def surface_force(
    solution: ModelSolution,
    measures: Measures,
    *,
    boundary: str = ANALYTE_BOUNDARY,
    wall_distance_nm: Expression | None = None,
) -> ForceComponents:
    """Return the traction integral over the body's own surface - **route B**.

    ``F_z = surface_int (T . n_B) . e_z r dl``, with ``n_B`` pointing out of the
    body. The cross-check of NUM-28, and it needs two guards that are invisible
    when they fail.

    **``ngsolve.grad`` on a boundary region returns the surface gradient of the
    trace, not the volume gradient.** The normal derivative is silently dropped:
    on the smooth field ``-z``, integrating ``grad(.)_z`` over a semicircular arc
    returns -0.5 rather than -1, because the trace only sees the tangential part
    [tested]. Every gradient here is therefore lifted with
    ``BoundaryFromVolumeCF``, which does return the volume gradient - and, on the
    analyte interface, the one on the fluid side.

    **That side is checked, not assumed.** The lift's choice of adjacent element
    is a property of the mesh, and taking the body's side would give a traction
    wrong by the whole dielectric contrast. The check compares the lifted
    piecewise permittivity against the fluid's own, which differ precisely when
    the side matters.

    The normal's orientation is likewise measured rather than assumed, against
    the body's own centroid: a flipped normal negates the force and nothing else.

    Raises
    ------
    ValueError
        If the boundary matches nothing, if the lift lands on the solid side, or
        if the normal's orientation cannot be determined.
    """
    return _surface_force(_integrands(solution, wall_distance_nm), measures, boundary)


def _surface_force(terms: _Integrands, measures: Measures, boundary: str) -> ForceComponents:
    """Return route B's traction integral from already-rebuilt coefficients."""
    import ngsolve as ngs

    mesh, model = terms.mesh, terms.model
    region, arc = _boundary_region(mesh, boundary)

    lift = ngs.BoundaryFromVolumeCF
    normal = _oriented_normal(mesh, region, arc)
    hydro = hydrodynamic_stress(
        lift(terms.velocity_gradient), lift(terms.pressure), lift(terms.viscosity)
    )
    scale = TWO_PI * model.scales.force_N
    forces = ForceComponents(
        em_N=electrostatic_surface_force(
            mesh,
            terms.potential_gradient,
            terms.permittivity,
            measures,
            force_N=model.scales.force_N,
            boundary=boundary,
            piecewise_permittivity=model.permittivity(mesh, terms.coefficients),
        ),
        hd_N=scale
        * measures.integrate(
            (hydro * normal)[1],
            mesh,
            definedon=region,
            what="the hydrodynamic surface traction",
        ),
    )
    logger.debug("surface force (pN): %s", {k: v * 1e12 for k, v in forces.summary().items()})
    return forces


def _boundary_region(mesh: Mesh, boundary: str) -> tuple[Option, float]:
    """Return a boundary region and its meridian arc length, insisting it exists.

    Raises
    ------
    ValueError
        If the name matches nothing; the message lists what the mesh does carry.
    """
    import ngsolve as ngs

    region = mesh.Boundaries(boundary)
    arc = float(ngs.Integrate(ngs.CF(1.0), mesh, definedon=region))
    if arc <= 0.0:
        known = ", ".join(sorted(set(mesh.GetBoundaries())))
        raise ValueError(f"no boundary matching {boundary!r} in this mesh; it has {known}")
    return region, arc


def _check_fluid_side(
    mesh: Mesh, piecewise: Expression, fluid: Expression, region: Option, arc: float
) -> None:
    """Assert the boundary lift evaluates on the fluid side of the analyte surface.

    Both coefficients are already lifted. Where the permittivity is continuous
    across the surface the check is vacuous; where it jumps - which is exactly
    where the side matters - it fires.

    Raises
    ------
    ValueError
        If the piecewise permittivity lifted from the volume disagrees with the
        fluid's own by more than a per cent of it.
    """
    import ngsolve as ngs

    departure = float(ngs.Integrate((piecewise - fluid) ** 2, mesh, definedon=region)) / arc
    reference = float(ngs.Integrate(fluid**2, mesh, definedon=region)) / arc
    if departure > 1e-4 * max(reference, 1.0):
        raise ValueError(
            "the boundary lift is evaluating the analyte surface on the solid side: the "
            f"piecewise permittivity there departs from the fluid's by {departure:.3e} in mean "
            f"square against {reference:.3e}. The traction would then be the body's own stress "
            "rather than the medium's, wrong by the whole dielectric contrast"
        )


def _oriented_normal(mesh: Mesh, region: Option, arc: float) -> Expression:
    """Return the boundary normal, oriented out of the body.

    Measured against the surface's own centroid: for a body star-shaped about it
    - every body of revolution CON-02 admits is - ``n . (x - c)`` is positive
    everywhere on an outward normal and negative everywhere on an inward one.

    Raises
    ------
    ValueError
        If the mean is too near zero to decide, which would leave the sign of
        the force resting on a coin toss.
    """
    import ngsolve as ngs

    normal = ngs.specialcf.normal(2)
    position = ngs.CF((ngs.x, ngs.y))
    centroid = ngs.CF(
        tuple(
            float(ngs.Integrate(component, mesh, definedon=region)) / arc
            for component in (ngs.x, ngs.y)
        )
    )
    radial = position - centroid
    sense = float(ngs.Integrate(ngs.InnerProduct(normal, radial), mesh, definedon=region)) / arc
    span = float(ngs.Integrate(ngs.sqrt(ngs.InnerProduct(radial, radial)), mesh, definedon=region))
    if abs(sense) < 0.1 * span / arc:
        raise ValueError(
            f"cannot orient the normal on this surface: the mean of n.(x - c) is {sense:.3e} "
            f"against a mean radius of {span / arc:.3e}. The surface is not star-shaped about "
            "its own centroid, and an unoriented normal negates the force with no other symptom"
        )
    return normal if sense > 0.0 else -normal


def reaction_force(
    solution: ModelSolution,
    *,
    boundary: str = ANALYTE_BOUNDARY,
    load_form: AssembledForm | None = None,
) -> float:
    """Return the hydrodynamic force from the assembled residual - **route C**.

    The analyte surface is a Dirichlet boundary for ``u``, so the momentum
    residual paired with a velocity-block test function equal to ``e_z`` there is
    the traction integral itself, ``surface_int (T_H . n_fluid) . e_z``, with
    ``n_fluid`` pointing into the body - hence the negation, the force on the
    body being taken with the opposite normal.

    This is the oracle of the package. It is discretely exact, it needs no
    quadrature of a post-processed stress, and because the residual vanishes on
    every free degree of freedom it is **exactly independent of** ``w``. Route A
    therefore disagrees with it precisely when a body-force consistency term is
    missing or mis-signed, which is the failure mode RSK-04 names (NUM-25,
    NUM-28).

    Parameters
    ----------
    solution
        A converged solution carrying its residual form.
    boundary
        The body's surface. Its velocity degrees of freedom must be the
        constrained ones of the solve, which
        :func:`~nanopnp.post.reaction_flux.boundary_reaction_flux` checks.
    load_form
        The assembled load vector, if the problem has one.

    Returns
    -------
    float
        ``F^hd_z`` in newtons.

    Raises
    ------
    ValueError
        If the solution carries no residual form.
    """
    model = _coupled(solution)
    if solution.residual is None:
        raise ValueError(
            "this solution carries no residual form, so the NUM-28 reaction force cannot be "
            "taken from it; solve through CoupledModel.solve, which records it"
        )
    block = [field.name for field in model.fields].index(VELOCITY)
    traction = boundary_reaction_flux(
        solution.residual,
        solution.state,
        boundary,
        component=block,
        value=(0.0, 1.0),
        load_form=load_form,
    )
    force = -TWO_PI * model.scales.force_N * traction
    logger.debug("reaction force (pN): %+.6f", force * 1e12)
    return force


def extract(
    solution: ModelSolution,
    measures: Measures,
    extension: GridFunction,
    *,
    boundary: str = ANALYTE_BOUNDARY,
    wall_distance_nm: Expression | None = None,
    load_form: AssembledForm | None = None,
    tolerance_N: float = FORCE_ROUTE_TOLERANCE_N,
    check_routes: bool = True,
) -> AnalyteForces:
    """Return the NUM-28 force on the body, with every route checked (NUM-29).

    The reported force is route A's, the domain form. Routes B and C are computed
    alongside it and all three are checked against each other before any number
    is returned. That check is not a diagnostic: it is the mechanism by which
    RSK-04 - a plausible, stable, wrong *split* of a near-cancelling total - is
    retired.

    Parameters
    ----------
    solution
        A converged solution of a coupled model with a flow block.
    measures
        The symmetry and quadrature policy the model was solved with.
    extension
        ``w``, from :func:`axial_extension`.
    boundary
        The body's surface.
    wall_distance_nm
        Overrides the distance field recorded on the solution.
    load_form
        The assembled load vector, if the problem has one.
    tolerance_N
        Absolute route-agreement tolerance; :data:`FORCE_ROUTE_TOLERANCE_N` by
        default.
    check_routes
        Whether to compute and check routes B and C. ``False`` skips them, for a
        sweep that has established agreement at a representative point and is
        paying for the extra assembly at a thousand others. It is a deviation
        from NUM-29 and the summary records it.

    Raises
    ------
    ForceDisagreementError
        If the routes disagree beyond ``tolerance_N``.
    """
    # One rebuild of the coefficients for all three routes: ``_integrands``
    # re-evaluates the correction chain against the distance field, and doing it
    # per route made a force extraction pay for it three times over.
    terms = _integrands(solution, wall_distance_nm)
    forces, korteweg_work = _domain_force(terms, measures, extension)
    residual = _dielectric_gradient_residual(terms, measures, extension, work=korteweg_work)

    agreement: ForceAgreement | None = None
    if check_routes:
        # Compared uncorrected, and that is not an oversight: route A's ``F^em``
        # carries ``div T_M`` and its ``F^hd`` carries ``div T_H``, each the
        # divergence of the tensor route B integrates the traction of, so the
        # two routes agree component by component whatever the model omits. The
        # PHY-23 residual is a gap between NUM-28 as printed and both of them,
        # not a gap between them.
        surface = _surface_force(terms, measures, boundary)
        agreement = ForceAgreement(
            domain=forces,
            surface=surface,
            reaction_hd_N=reaction_force(solution, boundary=boundary, load_form=load_form),
        )
        agreement.check(tolerance_N)
    return AnalyteForces(forces=forces, dielectric_gradient_N=residual, agreement=agreement)
