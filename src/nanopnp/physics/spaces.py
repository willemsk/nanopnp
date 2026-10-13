"""Writing essential data into a finite-element function."""

from __future__ import annotations

from nanopnp.core.typing import Expression, GridFunction, Option

__all__ = ["set_boundary_values"]


def set_boundary_values(component: GridFunction, values: Expression, region: Option) -> None:
    import ngsolve as ngs

    space = component.space
    scratch = ngs.GridFunction(space)
    scratch.Set(values, definedon=region)
    on_region = space.GetDofs(region)
    component.vec.data = (
        ngs.Projector(on_region, False) * component.vec
        + ngs.Projector(on_region, True) * scratch.vec
    )
