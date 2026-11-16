"""The dielectric blend and the nearest-solid permittivity field (section 4.4)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from nanopnp.core.typing import Expression, Mesh

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Mapping


def blend(
    chi: Expression, solid_permittivity: Expression, fluid_permittivity: Expression
) -> Expression:
    """Return the dielectric blend ``chi * eps_p + (1 - chi) * eps_r,f(<c>)``.

    Parameters
    ----------
    chi
        The solid fraction, in [0, 1].
    solid_permittivity
        The piecewise solid branch; each solid blends towards its own ``eps_p``.
    """
    return chi * solid_permittivity + (1.0 - chi) * fluid_permittivity


@dataclass(frozen=True)
class SolidBlend:
    """The solid side of the blend in the electrolyte: ``chi``, ``grad(chi)`` and ``eps_p``.

    Parameters
    ----------
    gradient
        ``grad(chi)`` per mesh length unit.
    solid_permittivity
        The ``eps_p`` of :func:`nearest_solid_permittivity`, in the units of the fluid's.
    """

    chi: Expression
    gradient: Expression
    solid_permittivity: Expression


def blend_gradient(
    solid: SolidBlend, fluid_permittivity: Expression, fluid_gradient: Expression
) -> Expression:
    """Return the blend's gradient, ``(1 - chi) grad eps_r,f + (eps_p - eps_r,f) grad chi``.

    ``eps_p`` is piecewise constant, so its own gradient is zero almost everywhere.
    """
    return (1.0 - solid.chi) * fluid_gradient + (
        solid.solid_permittivity - fluid_permittivity
    ) * solid.gradient


def blend_sensitivity(
    solid: SolidBlend, sensitivity: Expression, sensitivity_gradient: Expression
) -> tuple[Expression, Expression]:
    """Return ``d eps_r / d c_i`` of the blend and its gradient, from the fluid's own pair.

    The solid branch does not depend on ``c_i``, so the blend's sensitivity is
    ``(1 - chi) d eps_r,f / d c_i``.
    """
    return (
        (1.0 - solid.chi) * sensitivity,
        (1.0 - solid.chi) * sensitivity_gradient - sensitivity * solid.gradient,
    )


_NEAREST_SOLID_CACHE = "_nanopnp_nearest_solid_permittivity"


def nearest_solid_permittivity(mesh: Mesh, permittivities: Mapping[str, float]) -> Expression:
    """Return the ``eps_p`` the blend goes towards: each solid's own, elsewhere the nearest solid's.

    Raises
    ------
    ValueError
        If no mesh material is in ``permittivities``, or the mesh holds a non-triangle cell.
    """
    key = tuple(sorted(permittivities.items()))
    cache: dict[tuple[tuple[str, float], ...], Expression] | None = getattr(
        mesh, _NEAREST_SOLID_CACHE, None
    )
    if cache is None:
        cache = {}
        setattr(mesh, _NEAREST_SOLID_CACHE, cache)
    found = cache.get(key)
    if found is not None:
        return found

    import ngsolve as ngs
    import numpy as np
    from scipy.spatial import cKDTree

    names = mesh.GetMaterials()
    elements = mesh.ngmesh.Elements2D().NumPy()
    if not bool(np.all(np.asarray(elements["np"]) == 3)):
        raise ValueError("the nearest-solid permittivity is taken over triangles only")
    # Netgen numbers from one; NGSolve's element order is Elements2D order
    vertices = np.asarray(elements["nodes"])[:, :3] - 1
    coordinates = np.asarray(mesh.ngmesh.Coordinates(), dtype=np.float64)[:, :2]
    centroids = coordinates[vertices].mean(axis=1)
    by_material = np.array([permittivities.get(name, np.nan) for name in names])
    own = by_material[np.asarray(elements["index"]) - 1]
    solid = np.isfinite(own)
    if not bool(solid.any()):
        raise ValueError(
            f"no material of this mesh ({', '.join(sorted(set(names)))}) has a solid "
            "permittivity, so a solid fraction has no eps_p to blend towards (§4.4)"
        )
    values = own.copy()
    if not bool(solid.all()):
        _, nearest = cKDTree(centroids[solid]).query(centroids[~solid])
        values[~solid] = own[solid][nearest]
    field = ngs.GridFunction(ngs.L2(mesh, order=0), name="nearest_solid_permittivity")
    field.vec.FV().NumPy()[:] = values
    cache[key] = field
    return field
