"""The wall-distance field (PHY-02, NUM-31).

``d`` is the distance to the nearest **pore** boundary. The membrane is
deliberately excluded from the source set: electrolyte properties near the
bilayer do not affect the pore's figures of merit, and the reference model's
general-extrusion operator ran over the pore boundaries only.

The distance is measured **in the (r, z) half-plane, without the r weight**. For
a surface of revolution the nearest point to any field point lies in that point's
own meridian plane, so the two-dimensional distance in (r, z) *is* the
three-dimensional distance to the revolved surface. Weighting this solve by r
would silently measure something else.

Method: Varadhan's screened-Poisson approximation. Solve

    w - t laplacian(w) = 0,   w = 1 on the source boundaries

whose solution decays as ``exp(-d/sqrt(t))``, and recover ``d = -sqrt(t) ln w``.
The result is smooth by construction, which is the point: ``D``, ``mu`` and
``eta`` all depend on ``d``, so a kinked distance field propagates into the
Jacobian and degrades Newton convergence (NUM-31). ``d = 0`` holds exactly on the
sources, the Dirichlet condition making ``ln w`` vanish there.

Far from the wall ``w`` underflows, and the correction functions have long since
saturated - ``f^w_D`` is within 1 % of 1 by 0.75 nm - so the field is capped at
``max_distance`` rather than chasing an exponent to zero.
"""

from __future__ import annotations

import math

from nanopnp.core.typing import GridFunction, Mesh
from nanopnp.physics.measures import Measures
from nanopnp.solve.linear import DEFAULT_SOLVER, solve_linear

DEFAULT_MAX_DISTANCE_NM = 3.0
"""Cap on the field, in nm; every wall correction has saturated well before it."""

DEFAULT_DIFFUSION_LENGTH_NM = 0.2
"""Screened-Poisson length ``sqrt(t)``, in nm.

Measured against the exact ``a - r`` of a cylinder on a mesh resolving the wall:
0.1 nm gives a worst error of 0.6 pm within 1.5 nm of the wall but a 1.1 %
gradient jump; 0.2 nm gives 1.4 pm and 0.17 %; 0.3 nm gives 10 pm and 0.08 %.
0.2 nm keeps both below the tolerances VER-06 states.

Accuracy holds where the mesh resolves this length. In a coarse far reservoir
the field is only qualitatively right - and every wall correction has saturated
there, ``f^w_D`` being within 1 % of 1 beyond 0.75 nm.
"""


def wall_distance(
    mesh: Mesh,
    sources: str,
    *,
    order: int = 2,
    diffusion_length: float | None = None,
    max_distance: float = DEFAULT_MAX_DISTANCE_NM,
    smoothing_length: float | None = None,
    solver: str = DEFAULT_SOLVER,
) -> GridFunction:
    """Return the mollified distance to ``sources`` as a finite-element field.

    Parameters
    ----------
    mesh
        The meshed domain.
    sources
        Boundary-name regular expression naming the distance sources. Pass the
        pore wall only; passing the membrane too would be a model change
        (PHY-02).
    order
        Element order of the returned field.
    diffusion_length
        ``sqrt(t)`` of the screened-Poisson solve, in mesh units. Smaller is
        more accurate and worse conditioned. Defaults to one tenth of
        ``max_distance``.
    max_distance
        Cap on the returned distance, in mesh units.
    smoothing_length
        If given, the field is additionally smoothed by one screened-Poisson
        pass of this length, trading a little accuracy for smaller gradient
        jumps.
    solver
        Direct linear solver.

    Returns
    -------
    GridFunction
        The distance field, zero on ``sources`` and capped at ``max_distance``.

    Raises
    ------
    ValueError
        If the source boundary does not exist in the mesh, which would silently
        return a distance to nothing.
    """
    import ngsolve as ngs

    if mesh.Boundaries(sources).Mask().NumSet() == 0:
        known = ", ".join(sorted(set(mesh.GetBoundaries())))
        raise ValueError(f"no boundary matching {sources!r} in this mesh; it has {known}")

    scale = diffusion_length if diffusion_length is not None else DEFAULT_DIFFUSION_LENGTH_NM
    # The distance is planar in (r, z) even in an axisymmetric problem; see the
    # module docstring.
    planar = Measures(symmetry="planar", element_order=order)

    space = ngs.H1(mesh, order=order, dirichlet=sources)
    decayed = ngs.GridFunction(space, name="varadhan_w")
    decayed.Set(ngs.CF(1.0), definedon=mesh.Boundaries(sources))

    trial, test = space.TnT()
    a = ngs.BilinearForm(
        planar.volume(trial * test + scale**2 * ngs.grad(trial) * ngs.grad(test))
    ).Assemble()
    f = ngs.LinearForm(space).Assemble()
    solve_linear(a, f, decayed, solver=solver)

    floor = math.exp(-max_distance / scale)
    clamped = ngs.IfPos(decayed - floor, ngs.IfPos(decayed - 1.0, 1.0, decayed), floor)
    distance = ngs.GridFunction(space, name="wall_distance")
    distance.Set(-scale * ngs.log(clamped))
    # Set projects element-wise, so the source boundary comes back at a few
    # times 1e-4 rather than at zero. PHY-02 wants d = 0 there exactly - a
    # slightly negative d would shift f^w at the wall by percent - so the
    # constrained degrees of freedom are zeroed outright.
    on_sources = space.GetDofs(mesh.Boundaries(sources))
    for dof in range(len(distance.vec)):
        if on_sources[dof]:
            distance.vec[dof] = 0.0

    if smoothing_length is None:
        return distance
    return mollify(distance, smoothing_length, sources=sources, solver=solver)


def mollify(
    field: GridFunction,
    smoothing_length: float,
    *,
    sources: str | None = None,
    solver: str = DEFAULT_SOLVER,
) -> GridFunction:
    """Return ``field`` smoothed by one screened-Poisson pass.

    Solves ``(1 - delta^2 laplacian) g = field``, which damps the facet-to-facet
    gradient jumps of an interpolated field while preserving its value scale.
    """
    import ngsolve as ngs

    space = field.space
    mesh = space.mesh
    planar = Measures(symmetry="planar", element_order=space.globalorder)
    smoothed = ngs.GridFunction(space, name=f"{field.name}_mollified")
    if sources is not None:
        smoothed.Set(ngs.CF(0.0), definedon=mesh.Boundaries(sources))

    trial, test = space.TnT()
    a = ngs.BilinearForm(
        planar.volume(trial * test + smoothing_length**2 * ngs.grad(trial) * ngs.grad(test))
    ).Assemble()
    f = ngs.LinearForm(planar.volume(field * test)).Assemble()
    solve_linear(a, f, smoothed, solver=solver)
    return smoothed


def gradient_jump(field: GridFunction) -> float:
    """Return the mean facet jump of ``grad(field)``, normalised by its own size.

    The C1 continuity measure of VER-06: zero for a genuinely smooth field, order
    one for a field that is merely continuous.
    """
    import ngsolve as ngs

    mesh = field.space.mesh
    gradient = ngs.grad(field)
    jump = gradient - gradient.Other()
    facets = ngs.dx(element_boundary=True, bonus_intorder=2)
    jump_norm = ngs.Integrate(ngs.InnerProduct(jump, jump) * facets, mesh)
    scale = ngs.Integrate(ngs.InnerProduct(gradient, gradient) * facets, mesh)
    return math.sqrt(float(jump_norm) / float(scale)) if scale > 0.0 else 0.0
