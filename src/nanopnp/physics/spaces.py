"""Writing essential data into a finite-element function.

One idiom, shared by every solver in the package. It is here rather than in
:mod:`nanopnp.physics.models` because :mod:`nanopnp.physics.pb` needs it too and
imports the other way round; a second copy of it in ``pb`` would be a second
place to correct.
"""

from __future__ import annotations

from nanopnp.core.typing import Expression, GridFunction, Option

__all__ = ["set_boundary_values"]


def set_boundary_values(component: GridFunction, values: Expression, region: Option) -> None:
    """Write ``values`` onto ``region`` without disturbing the rest of the field.

    ``GridFunction.Set(cf, definedon=region)`` zeroes every degree of freedom
    outside the region, so calling it after an initial guess has been written
    destroys that guess — and calling it on a warm start destroys the state the
    continuation ladder is warm-starting from. The interpolation is therefore
    done on a scratch function and only the region's degrees of freedom are
    copied across.

    Parameters
    ----------
    component
        The field to write into, in place. On a product space this is one
        component, not the compound function: a compound space has no evaluator
        of its own and ``Set`` on it raises.
    values
        The essential data, as a coefficient function.
    region
        The ``Region`` to write on, from ``mesh.Boundaries(...)``.
    """
    import ngsolve as ngs

    space = component.space
    scratch = ngs.GridFunction(space)
    scratch.Set(values, definedon=region)
    on_region = space.GetDofs(region)
    component.vec.data = (
        ngs.Projector(on_region, False) * component.vec
        + ngs.Projector(on_region, True) * scratch.vec
    )
