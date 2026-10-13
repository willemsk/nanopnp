"""The wall-distance field (PHY-02, NUM-31)."""

from __future__ import annotations

import math

from nanopnp.core.typing import GridFunction, Mesh
from nanopnp.numerics.linear import DEFAULT_SOLVER, solve_linear
from nanopnp.numerics.measures import Measures

DEFAULT_MAX_DISTANCE_NM = 3.0

# Measured against a cylinder in .knowledge/06-numerics-fem.md (screened-Poisson length).
DEFAULT_DIFFUSION_LENGTH_NM = 0.2


def wall_distance(
    mesh: Mesh,
    sources: str,
    *,
    order: int = 2,
    diffusion_length_nm: float | None = None,
    max_distance_nm: float = DEFAULT_MAX_DISTANCE_NM,
    smoothing_length_nm: float | None = None,
    solver: str = DEFAULT_SOLVER,
) -> GridFunction:
    import ngsolve as ngs

    if mesh.Boundaries(sources).Mask().NumSet() == 0:
        known = ", ".join(sorted(set(mesh.GetBoundaries())))
        raise ValueError(f"no boundary matching {sources!r} in this mesh; it has {known}")

    scale = diffusion_length_nm if diffusion_length_nm is not None else DEFAULT_DIFFUSION_LENGTH_NM
    # (r, z) distance without the r weight is the 3D distance to the revolved surface.
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

    floor = math.exp(-max_distance_nm / scale)
    if not floor > 0.0:
        raise ValueError(
            f"diffusion_length_nm = {scale} nm is too small for max_distance_nm = "
            f"{max_distance_nm} nm: exp(-{max_distance_nm / scale:.0f}) underflows to zero, the "
            "lower clamp becomes a no-op and log(0) would return an infinite distance"
        )
    clamped = ngs.IfPos(decayed - floor, ngs.IfPos(decayed - 1.0, 1.0, decayed), floor)
    distance = ngs.GridFunction(space, name="wall_distance")
    distance.Set(-scale * ngs.log(clamped))
    # Set projects element-wise, so the source boundary comes back at a few
    # times 1e-4 rather than at zero. PHY-02 wants d = 0 there exactly - a
    # slightly negative d would shift f^w at the wall by percent - so the
    # constrained degrees of freedom are zeroed outright.
    on_sources = space.GetDofs(mesh.Boundaries(sources))
    distance.vec.data = ngs.Projector(on_sources, False) * distance.vec

    if smoothing_length_nm is None:
        return distance
    return mollify(distance, smoothing_length_nm, sources=sources, solver=solver)


def mollify(
    field: GridFunction,
    smoothing_length_nm: float,
    *,
    sources: str | None = None,
    solver: str = DEFAULT_SOLVER,
) -> GridFunction:
    import ngsolve as ngs

    space = field.space
    mesh = space.mesh
    planar = Measures(symmetry="planar", element_order=space.globalorder)
    smoothed = ngs.GridFunction(space, name=f"{field.name}_mollified")
    if sources is not None:
        still_free = space.GetDofs(mesh.Boundaries(sources)) & space.FreeDofs()
        if still_free.NumSet() != 0:
            raise ValueError(
                f"{still_free.NumSet()} degrees of freedom on {sources!r} are free in this "
                "field's space; build it with dirichlet=sources, or the smoothing pass will "
                "not hold the boundary at zero"
            )
        smoothed.Set(ngs.CF(0.0), definedon=mesh.Boundaries(sources))

    trial, test = space.TnT()
    a = ngs.BilinearForm(
        planar.volume(trial * test + smoothing_length_nm**2 * ngs.grad(trial) * ngs.grad(test))
    ).Assemble()
    f = ngs.LinearForm(planar.volume(field * test)).Assemble()
    solve_linear(a, f, smoothed, solver=solver)
    return smoothed


def gradient_jump(field: GridFunction) -> float:
    import ngsolve as ngs

    mesh = field.space.mesh
    gradient = ngs.grad(field)
    jump = gradient - gradient.Other()
    facets = ngs.dx(element_boundary=True, bonus_intorder=2)
    jump_norm = ngs.Integrate(ngs.InnerProduct(jump, jump) * facets, mesh)
    scale = ngs.Integrate(ngs.InnerProduct(gradient, gradient) * facets, mesh)
    return math.sqrt(float(jump_norm) / float(scale)) if scale > 0.0 else 0.0
