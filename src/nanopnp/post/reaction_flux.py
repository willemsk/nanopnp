"""The variational reaction flux (NUM-25)."""

from __future__ import annotations

from nanopnp.core.typing import AssembledForm, Expression, FESpace, GridFunction


def boundary_indicator(
    space: FESpace,
    boundary: str,
    *,
    component: int | None = None,
    value: Expression = 1.0,
) -> GridFunction:
    """Return the function equal to ``value`` on ``boundary`` and 0 elsewhere.

    Parameters
    ----------
    component
        On a product space, the field whose flux is wanted; other blocks are zero.
    value
        1 for a scalar field; a vector such as ``(0, 1)`` for the axial component.
    """
    import ngsolve as ngs

    indicator = ngs.GridFunction(space, name=f"psi_{boundary}")
    region = space.mesh.Boundaries(boundary)
    target = ngs.CF(value)
    if component is None:
        indicator.Set(target, definedon=region)
    else:
        indicator.components[component].Set(target, definedon=region)
    return indicator


def boundary_reaction_flux(
    residual_form: AssembledForm,
    solution: GridFunction,
    boundary: str,
    *,
    component: int | None = None,
    value: Expression = 1.0,
    load_form: AssembledForm | None = None,
) -> float:
    """Return the reaction flux through ``boundary``.

    Parameters
    ----------
    boundary
        Boundary-name regular expression; its degrees of freedom must be constrained.

    Raises
    ------
    ValueError
        If ``boundary`` matches nothing, or any of its degrees of freedom are free.
    """
    import ngsolve as ngs

    space = solution.space
    mesh = space.mesh
    field_space = space if component is None else space.components[component]
    on_boundary = field_space.GetDofs(mesh.Boundaries(boundary))
    if on_boundary.NumSet() == 0:
        known = ", ".join(sorted(set(mesh.GetBoundaries())))
        raise ValueError(f"no boundary matching {boundary!r} in this mesh; it has {known}")
    still_free = on_boundary & field_space.FreeDofs()
    if still_free.NumSet() != 0:
        raise ValueError(
            f"{still_free.NumSet()} of the {on_boundary.NumSet()} degrees of freedom on "
            f"{boundary!r} are free, so the residual there is not the boundary flux; the "
            "reaction flux of NUM-25 needs a boundary the solve constrained"
        )

    residual = solution.vec.CreateVector()
    residual_form.Apply(solution.vec, residual)
    if load_form is not None:
        residual.data = residual - load_form.vec
    indicator = boundary_indicator(space, boundary, component=component, value=value)
    return float(ngs.InnerProduct(residual, indicator.vec))
