"""The dielectric blend: the permittivity a solid fraction drives (section 4.4).

``eps_r = chi * eps_p + (1 - chi) * eps_r,f(<c>)``, with the 1-2 Angstrom
transition carried by ``chi`` alone. The solid fraction itself, supplied or
derived, is :mod:`nanopnp.charge.dielectric`'s: stage 7 produces it, and the
weak forms of :mod:`nanopnp.physics.models` evaluate the permittivity here from
it, so neither the corrections nor the forms reach back into the charge stage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from nanopnp.core.typing import Expression, Mesh

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Mapping


def blend(
    chi: Expression, solid_permittivity: Expression, fluid_permittivity: Expression
) -> Expression:
    """Return §4.4's dielectric blend, ``chi * eps_p + (1 - chi) * eps_r,f(<c>)``.

    Parameters
    ----------
    chi
        The solid fraction, in ``[0, 1]``.
    solid_permittivity
        The piecewise solid branch — the whole ``MaterialCF`` of
        :meth:`nanopnp.physics.models.CoupledModel.permittivity`, not one
        material's constant, so that a mesh with a protein *and* a membrane
        blends each towards its own ``eps_p``. Where ``chi`` is zero its value
        is irrelevant, which is why its fluid default costs nothing.
    fluid_permittivity
        The corrected ``eps_r,f(<c>)/eps_r,f0`` of PHY-11 and PHY-12.

    Returns
    -------
    Expression
        The blended relative permittivity, nondimensionalised exactly as its two
        arguments are. With the sharp material indicator for ``chi`` this is
        identically the piecewise assignment of PHY-20.
    """
    return chi * solid_permittivity + (1.0 - chi) * fluid_permittivity


_NEAREST_SOLID_CACHE = "_nanopnp_nearest_solid_permittivity"
"""Attribute on an NGSolve mesh holding :func:`nearest_solid_permittivity`'s cache."""


def nearest_solid_permittivity(mesh: Mesh, permittivities: Mapping[str, float]) -> Expression:
    """Return the ``eps_p`` the blend goes towards: each solid's own, elsewhere the nearest's.

    §4.4's blend needs an ``eps_p`` wherever ``chi > 0``, and the 1-2 Angstrom
    transition reaches past the mesh boundary into fluid and exclusion elements,
    which carry none of their own. The ``chi`` there is the nearest solid's, so
    its ``eps_p`` is the one the blend goes to; taking any single value instead
    would blend the fluid beside the membrane towards the protein. Nearest by
    element centroid in the meridional plane, which is where the nearest point of
    an axisymmetric body lies. Two solids can tie only where both are within an
    element of the point, and ``chi`` is then the sum of both, so either value is
    within the transition's own resolution.

    Piecewise constant, an ``L2`` order-0 field, because it is a statement about
    which element a point is in. Kept on the mesh, as
    :meth:`nanopnp.numerics.gates.FieldSampler.shared` keeps its samplers, so every
    rung's residual reads one field and the cache dies with the mesh.

    Parameters
    ----------
    mesh
        The deployed mesh, in nm.
    permittivities
        Each solid material's nondimensional ``eps_p``, by material name.

    Raises
    ------
    ValueError
        If no material of the mesh is named in ``permittivities``, so that there
        is no solid for a solid fraction to be a fraction of, or if the mesh
        holds a cell that is not a triangle.
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
    # Netgen numbers vertices and face descriptors from one; NGSolve's element
    # order is the Elements2D order, so row i is element i and dof i of L2(0).
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
