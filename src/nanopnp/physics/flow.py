"""The flow equations, axisymmetric (PHY-07, PHY-08, NUM-04, NUM-05).

In the nondimensional variables of :mod:`nanopnp.physics.coefficients` the
momentum residual on the fluid domain is

    int [ 2 eta~ eps(u~):eps(v) + 2 eta~ u~_r v_r / r^2
          - p~ div^(v) - q div^(rho~ u~) ] r dr dz
      + Re int rho~ (u~.grad) u~ . v r dr dz
      + S int (sum_i z_i c~_i) grad(phi~) . v r dr dz  =  0

    div^(u~) = d_r u~_r + u~_r/r + d_z u~_z

with ``S`` the screening coefficient shared with the Poisson source: the body
force is the electrostatic force on the *mobile* charge and nothing else
(PHY-08).

Two terms in that list are easy to lose.

**The hoop-strain term ``2 eta u_r v_r / r^2``** is the weak-form counterpart of
the strong-form ``-u_r/r^2`` that COMSOL hides inside its axisymmetric
interface. Omitting it produces a plausible but wrong flow field with no solver
diagnostic (NUM-05). After the ``r`` weight it reads ``2 eta u_r v_r / r``,
integrable because ``u_r -> 0`` on the axis.

**The ``u_r/r`` inside the divergence** is a ``1/r`` factor in its own right, and
it is evaluated before the ``r`` weight multiplies it. An order-2 rule on an
axis-touching element samples ``r = 0`` exactly and returns ``inf * 0``, so the
continuity and pressure blocks need the NUM-07 guarantee as much as the hoop
term does. Every measure below that touches a divergence therefore passes
``singular=True``.
"""

from __future__ import annotations

from collections.abc import Mapping

from nanopnp.core.typing import Expression, IntegralTerm, Numeric, Option
from nanopnp.physics.coefficients import NondimensionalCoefficients
from nanopnp.physics.measures import Measures
from nanopnp.physics.nernst_planck import ConcentrationVariables

__all__ = [
    "axisymmetric_divergence",
    "continuity_term",
    "dielectric_gradient_force",
    "electrical_body_force",
    "inertia_term",
    "permittivity_gradient",
    "pressure_term",
    "strain_rate",
    "viscous_operator",
]


def _singular(kwargs: Mapping[str, Option]) -> dict[str, Option]:
    """Return ``kwargs`` with the NUM-07 ``1/r`` flag forced on.

    The flag is a property of the integrand, not of the call site, so a caller
    routing ``singular`` through ``**kwargs`` must not be able to clear it - and
    must not collide with it either, which passing it alongside ``**kwargs``
    would do.
    """
    return {**kwargs, "singular": True}


def strain_rate(velocity: Expression) -> Expression:
    """Return the in-plane rate-of-strain tensor ``eps(u) = sym grad(u)``.

    The hoop component ``eps_theta,theta = u_r/r`` is not part of this
    two-by-two tensor; it enters through :func:`viscous_operator` and
    :func:`axisymmetric_divergence` instead, which is why neither may be
    reconstructed from this function alone.
    """
    import ngsolve as ngs

    gradient = ngs.grad(velocity)
    return 0.5 * (gradient + gradient.trans)


def axisymmetric_divergence(velocity: Expression, measures: Measures) -> Expression:
    """Return ``div^(u) = d_r u_r + u_r/r + d_z u_z``, or the planar divergence.

    Carries a ``1/r`` factor in axisymmetric geometry, so every measure it is
    integrated under must declare ``singular=True`` (NUM-07).
    """
    import ngsolve as ngs

    planar = ngs.Trace(ngs.grad(velocity))
    if not measures.is_axisymmetric:
        return planar
    return planar + velocity[0] / ngs.x


def viscous_operator(
    velocity: Expression,
    test: Expression,
    measures: Measures,
    *,
    viscosity: Numeric = 1.0,
    **kwargs: Option,
) -> IntegralTerm:
    """Return ``int [2 eta eps(u):eps(v) + 2 eta u_r v_r / r^2] r``.

    The second term is the cylindrical hoop strain of NUM-05, assembled as its
    own integral so that the ``singular=True`` guarantee applies to it and only
    to it. In planar geometry it is absent.
    """
    import ngsolve as ngs

    deviatoric = measures.volume(
        2.0 * viscosity * ngs.InnerProduct(strain_rate(velocity), strain_rate(test)), **kwargs
    )
    if not measures.is_axisymmetric:
        return deviatoric
    hoop = measures.volume(
        2.0 * viscosity * velocity[0] * test[0] / (ngs.x * ngs.x), **_singular(kwargs)
    )
    return deviatoric + hoop


def pressure_term(
    pressure: Expression,
    test: Expression,
    measures: Measures,
    **kwargs: Option,
) -> IntegralTerm:
    """Return ``-int p div^(v) r``, the pressure contribution to momentum."""
    return measures.volume(-pressure * axisymmetric_divergence(test, measures), **_singular(kwargs))


def continuity_term(
    velocity: Expression,
    test: Expression,
    measures: Measures,
    *,
    mass_density: Numeric | None = None,
    **kwargs: Option,
) -> IntegralTerm:
    """Return ``-int q rho~ div^(u~) r``, the continuity residual.

    With ``mass_density`` omitted this is the constant-density incompressible
    constraint ``-int q div^(u~) r``, which is what the ``variable_density_flow``
    switch of PHY-22 selects when off.

    With a density it is the velocity-continuity equation of the Axelsson
    variable-density system (PHY-07), ``div(rho u) - u.grad(rho) = 0``. The
    product rule collapses that to ``rho div(u)`` exactly, and it is assembled in
    that form: the density gradient appears twice with opposite signs and
    cancels identically, so forming it would add a symbolic derivative of the
    correction chain to the Jacobian for no change in the answer. The reference
    model reached the same equation from the other side, adding
    ``(u*d(rho,r) + w*d(rho,z))*test(p)`` by hand to COMSOL's compressible
    continuity.

    A consequence worth stating plainly: because ``rho~ > 0``, the variable-
    density system leaves the velocity field satisfying ``div^(u~) = 0`` just as
    the constant-density one does. The density reaches the answer through the
    inertia term of :func:`inertia_term`, not through continuity.
    """
    divergence = axisymmetric_divergence(velocity, measures)
    if mass_density is not None:
        divergence = mass_density * divergence
    return measures.volume(-test * divergence, **_singular(kwargs))


def inertia_term(
    velocity: Expression,
    test: Expression,
    measures: Measures,
    *,
    reynolds: float,
    mass_density: Numeric = 1.0,
    **kwargs: Option,
) -> IntegralTerm:
    """Return ``Re int rho~ (u~.grad) u~ . v r``, the convective momentum term.

    ``Re = rho_0 u_0 L_0 / eta_0`` is about 6e-4 here, so the term is a small
    perturbation; PHY-22 nevertheless leaves ``inertia`` on by default because
    the reference model retained it.

    ``(u.grad)(rho u)`` expands to ``rho (u.grad)u + u (u.grad rho)``, and the
    density-continuity equation of PHY-07 is exactly ``u.grad(rho) = 0``, so the
    second piece vanishes. That is what the three-equation Axelsson formulation
    buys: the variable-density inertia is the constant-density one weighted by
    ``rho~``.

    In axisymmetry the convective operator carries no extra hoop contribution,
    the ``u_theta^2/r`` term vanishing with ``u_theta``.
    """
    import ngsolve as ngs

    convective = ngs.grad(velocity) * velocity
    return measures.volume(reynolds * mass_density * ngs.InnerProduct(convective, test), **kwargs)


def electrical_body_force(
    charge_density: Expression,
    potential: Expression,
    test: Expression,
    measures: Measures,
    *,
    screening: float,
    **kwargs: Option,
) -> IntegralTerm:
    """Return ``+S int (sum_i z_i c~_i) grad(phi~) . v r``, the PHY-08 body force.

    The force itself is ``f = rho_ion E = -(F sum_i z_i c_i) grad(phi)``, which
    is ``-S (sum_i z_i c~_i) grad(phi~)`` after scaling; this function returns
    its contribution to the **residual**, that is ``-int f.v``, hence the plus.

    ``S`` is the same coefficient the Poisson source carries, because it is the
    same mobile charge. There is deliberately no dielectric-gradient term here:
    the published model contains none, and adding one is a deviation reachable
    only through ``dielectric_gradient_forces`` (PHY-08, PHY-23).
    """
    import ngsolve as ngs

    return measures.volume(
        screening * charge_density * ngs.InnerProduct(ngs.grad(potential), test), **kwargs
    )


def permittivity_gradient(
    coefficients: NondimensionalCoefficients,
    variables: ConcentrationVariables,
) -> Expression:
    """Return ``grad(eps~_r) = sum_i (d eps~_r / d c~_i) grad(c~_i)``.

    The permittivity is a function of the concentrations through the correction
    driver ``<c>``, not a finite-element field, so its gradient is taken by the
    chain rule with the sensitivities of
    :meth:`~nanopnp.physics.coefficients.NondimensionalCoefficients.permittivity_sensitivity`.

    Raises
    ------
    NotImplementedError
        In the NUM-02 log branch, for the reason given in
        :func:`nanopnp.physics.nernst_planck.excess_potential_gradient`.
    """
    if variables.logarithmic:
        raise NotImplementedError(
            "the dielectric-gradient body force is not implemented for the NUM-02 log branch: "
            "d(eps~_r)/d(c~_i) would come back as the derivative in w_i"
        )
    names = list(variables.values)
    total = coefficients.permittivity_sensitivity(names[0]) * variables.gradients[names[0]]
    for name in names[1:]:
        total = total + coefficients.permittivity_sensitivity(name) * variables.gradients[name]
    return total


def dielectric_gradient_force(
    potential: Expression,
    permittivity_gradient_expression: Expression,
    test: Expression,
    measures: Measures,
    **kwargs: Option,
) -> IntegralTerm:
    """Return ``+1/2 int |grad phi~|^2 grad(eps~_r) . v r``, the PHY-23 momentum term.

    The Korteweg-Helmholtz body force ``-1/2 |grad phi|^2 grad(eps)`` carries no
    prefactor once scaled — the permittivity scale cancels against the velocity
    and pressure scales exactly — so the nondimensional force is
    ``-1/2 |grad phi~|^2 grad(eps~_r)`` and its residual contribution is the
    positive form above.

    **This term is not in the validated model.** The published agreement with
    experiment was obtained without it, and it is thermodynamically inconsistent
    without its Nernst-Planck partner, so ``dielectric_gradient_forces`` enables
    the two together and never one alone (PHY-08, PHY-23). Enabling it is
    recorded in the run provenance (FR-25).
    """
    import ngsolve as ngs

    field = ngs.grad(potential)
    return measures.volume(
        0.5 * (field * field) * ngs.InnerProduct(permittivity_gradient_expression, test), **kwargs
    )
