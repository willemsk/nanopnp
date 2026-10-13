"""The dielectric blend and the nearest-solid permittivity field (section 4.4)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nanopnp.core.typing import Expression, Mesh

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Mapping


def blend(
    chi: Expression, solid_permittivity: Expression, fluid_permittivity: Expression
) -> Expression:
    return chi * solid_permittivity + (1.0 - chi) * fluid_permittivity


_NEAREST_SOLID_CACHE = "_nanopnp_nearest_solid_permittivity"


def nearest_solid_permittivity(mesh: Mesh, permittivities: Mapping[str, float]) -> Expression:
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
