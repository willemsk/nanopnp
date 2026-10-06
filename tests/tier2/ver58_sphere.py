"""VER-58's problem: one smeared atom deposited and solved, against its closed-form potential.

*Design* §4 of the WP28 plan. A unit charge smeared as PHY-16 step 4's 3D Gaussian
sits at ``(r_i, z_i)`` in a uniform dielectric inside a grounded sphere of radius
``R``: the half-disc of the ``(r, z)`` plane, its arc ``cis`` and ``trans`` at
zero bias. Outside the Gaussian's support the smeared ring is the point ring, so
the Kelvin image of each ring point is a charge ``-qR/a`` at ``R^2/a`` along the
same ray, ``a = (r_i^2 + z_i^2)^(1/2)``, and

    phi = (q/4 pi eps) <erf(d/w)/d>_theta  -  (q R/a)/(4 pi eps) <1/d'>_theta,

with ``d`` and ``d'`` the distances to the ring point and its image at azimuth
``theta``, averaged by the periodic trapezoid rule, which is spectrally accurate
for these smooth periodic integrands.

The deposit (D3) and the solve (``poisson``, which integrates the source at
degree ``2k + 1``, D13) are measured together: the ``r``-weighted L2 error over a
2 nm disc about the atom, as the near-atom mesh is halved twice. A Galerkin-exact
source leaves the potential's own ``O(h^3)``; a ``P0`` deposit moves charge by up
to half an element and shows as ``O(h^2)`` (*Design* §2). The error is computed by
a degree-8 rule of this file's own on the elements of the disc, sampling the
NGSolve field through its own point location, so the measurement does not share
the projection's quadrature.

The tests are in ``test_charge_potential_axis.py`` (``r_i = 0``) and
``test_charge_potential_off_axis.py`` (``r_i = 1.5`` nm), two files so that the
scheduler of ``--dist loadfile`` can run them at once (WP33 D4). Everything a
solve needs that does not depend on the deposit's order -- the mesh, the lattice,
and the closed form at the quadrature points -- is computed once per process and
read by both orders (:func:`_reference`). The closed form was nine tenths of a
solve's time, and it is the same numbers for ``P2`` and ``P0``.
"""

from __future__ import annotations

import functools
import logging
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np
from scipy.special import erf

from nanopnp.charge.deposit import deposit, gridfunction, triangle_rule
from nanopnp.charge.kernel import SourceAtoms, sum_kernel
from nanopnp.core.constants import ELEMENTARY_CHARGE, VACUUM_PERMITTIVITY
from nanopnp.materials.electrolyte import Electrolyte
from nanopnp.mesh.adapter import MeshData, from_ngsolve, to_ngsolve
from nanopnp.numerics.measures import AXISYMMETRIC
from nanopnp.physics import models

if TYPE_CHECKING:
    from nanopnp.charge.kernel import RadialGrid

SPHERE_NM = 10.0
"""``R``: the grounded sphere."""

DISC_NM = 2.0
"""Radius of the disc about the atom over which the error is measured."""

WIDTH_NM = 0.25
"""The resolved atom's ``w``."""

Z_ATOM_NM = 0.5
"""``z_i``: off the sphere's centre, so the image term varies."""

AZIMUTHS = 512
"""Periodic trapezoid points of the azimuthal mean."""

ARC_NM = 0.02
"""Element size on the sphere, the same at every level.

The mesh is affine, so the sphere is a polygon whose chords sag by ``h^2/(8R)``,
which moves the grounded surface and costs an ``O(h^2)`` potential error of the
oracle's geometry rather than of the deposit. With the arc tied to the coarse
far field (1.6, 0.8, 0.4 nm) that error sets the P2 rate at 2.0 between the finest
two levels, measured; at 0.02 nm everywhere it is a constant ``~ 1e-7`` of the
potential, under the finest level's error by fifty, and the rate is the deposit's.
"""

H = 0.0025
"""The lattice spacing, in nm: ``w/100``.

An atom on the axis keeps the trapezoid's end correction in its shape after
renormalisation, an ``O(H^2/w^2)`` redistribution near ``r = 0`` that does not fall
with the mesh. Measured at ``r_i = 0`` on the 0.05 nm level (P2): the disc error
4.1e-5, 1.9e-5, 1.7e-5 and the on-axis error 1.2e-3, 3.3e-4, 1.1e-4 at
``H`` = 0.01, 0.005, 0.0025 nm. At 0.005 nm the floor holds the rate to 2.80; at
0.0025 nm it is 2.99, the deposit's and the solve's.
"""

LEVELS_NM = (0.2, 0.1, 0.05)
"""The near-atom element sizes: halved twice, so VER-58 asserts a rate between the finest two."""


def _azimuths() -> tuple[np.ndarray, np.ndarray]:
    """Return the distinct azimuths of the :data:`AZIMUTHS`-point trapezoid rule and their weights.

    Both integrands depend on ``theta`` only through ``cos(theta)``, so the points
    ``theta`` and ``2 pi - theta`` carry the same value: the rule is evaluated on
    ``0 <= theta <= pi`` with every interior point counted twice (WP33 D4). It is
    the same rule; only the duplicated evaluations are gone.
    """
    half = AZIMUTHS // 2
    theta = 2.0 * math.pi * np.arange(half + 1) / AZIMUTHS
    weights = np.full(half + 1, 2.0 / AZIMUTHS)
    weights[0] = 1.0 / AZIMUTHS
    if AZIMUTHS % 2 == 0:
        # theta = pi is its own mirror only for an even count; for an odd one the
        # last point pairs with the next, and counts twice like the others.
        weights[-1] = 1.0 / AZIMUTHS
    return theta, weights


def exact_potential_V(
    r_nm: np.ndarray, z_nm: np.ndarray, r_i: float, z_i: float, width_nm: float, permittivity: float
) -> np.ndarray:
    """Return the closed form of *Design* §4 for a unit charge, in volts."""
    r = np.asarray(r_nm, dtype=np.float64)[..., None] * 1e-9
    z = np.asarray(z_nm, dtype=np.float64)[..., None] * 1e-9
    theta, weights = _azimuths()
    ri, zi, w, sphere = r_i * 1e-9, z_i * 1e-9, width_nm * 1e-9, SPHERE_NM * 1e-9
    distance = np.sqrt(r**2 + ri**2 - 2.0 * r * ri * np.cos(theta) + (z - zi) ** 2)
    # erf(d/w)/d -> 2/(w sqrt(pi)) as d -> 0, its finite limit at the ring itself.
    small = distance < 1e-6 * w
    direct = np.where(
        small, 2.0 / (w * math.sqrt(math.pi)), erf(distance / w) / np.where(small, 1.0, distance)
    )
    a = math.hypot(ri, zi)
    if a == 0.0:
        image = np.full(r.shape[:-1], 1.0 / sphere)
    else:
        scale = sphere**2 / a**2
        image_distance = np.sqrt(
            r**2 + (scale * ri) ** 2 - 2.0 * r * scale * ri * np.cos(theta) + (z - scale * zi) ** 2
        )
        image = (sphere / a) * ((1.0 / image_distance) @ weights)
    prefactor = ELEMENTARY_CHARGE / (4.0 * math.pi * permittivity)
    return np.asarray(prefactor * (direct @ weights - image))


def _sphere(r_i: float, z_i: float, near_nm: float) -> MeshData:
    """Return the grounded half-disc, refined to ``near_nm`` within :data:`DISC_NM` of the atom."""
    import netgen.occ as occ
    import ngsolve as ngs

    circle = occ.Circle(occ.Pnt(0.0, 0.0), SPHERE_NM).Face()
    upper = circle * occ.MoveTo(0.0, 0.0).Rectangle(SPHERE_NM, SPHERE_NM).Face()
    lower = circle * occ.MoveTo(0.0, -SPHERE_NM).Rectangle(SPHERE_NM, SPHERE_NM).Face()
    near = (
        occ.Circle(occ.Pnt(r_i, z_i), DISC_NM).Face()
        * occ.MoveTo(0.0, -SPHERE_NM).Rectangle(SPHERE_NM, 2.0 * SPHERE_NM).Face()
    )
    near.name = "near"
    near.maxh = near_nm
    faces = [upper - near, lower - near, near]
    for face in faces[:2]:
        face.name = "far"
    shape = occ.Glue(faces)
    # By the endpoints: an arc's ``center`` is its centre of mass, inside the circle.
    for edge in shape.edges:
        start, end = edge.start, edge.end
        if abs(start[0]) < 1e-9 and abs(end[0]) < 1e-9:
            edge.name = "axis"
        elif all(abs(math.hypot(p[0], p[1]) - SPHERE_NM) < 1e-6 for p in (start, end)):
            edge.name = "cis" if start[1] + end[1] > 0 else "trans"
            edge.maxh = ARC_NM
        else:
            edge.name = "interface"
    generated = occ.OCCGeometry(shape, dim=2).GenerateMesh(maxh=min(8.0 * near_nm, 1.6))
    return from_ngsolve(ngs.Mesh(generated))


@functools.cache
def _mesh(r_i: float, near_nm: float) -> tuple[MeshData, Any]:
    """Return :func:`_sphere`'s mesh and its NGSolve form, built once per ``(r_i, near_nm)``."""
    data = _sphere(r_i, Z_ATOM_NM, near_nm)
    assert {"cis", "trans", "axis"} <= set(data.boundaries), data.boundaries
    return data, to_ngsolve(data)


@functools.cache
def _lattice(r_i: float, width_nm: float) -> RadialGrid:
    """Return the atom's lattice at :data:`H`: it depends on neither the mesh nor the order."""
    atoms = SourceAtoms(
        r_nm=np.array([r_i]),
        z_nm=np.array([Z_ATOM_NM]),
        width_nm=np.array([width_nm]),
        weight_e=np.array([1.0]),
        frame=np.zeros(1, dtype=np.int64),
        atom=np.zeros(1, dtype=np.int64),
        frames=1,
        shift_z_nm=0.0,
    )
    return sum_kernel(atoms, H).grid


@functools.cache
def _electrolyte() -> Electrolyte:
    return Electrolyte.from_parameter_file("willems2020_nacl")


@dataclass(frozen=True)
class Reference:
    """What one mesh's error measurement needs that no deposit order changes."""

    located: Any
    """The quadrature points, located in the NGSolve mesh."""
    weight: np.ndarray
    """The quadrature weight times ``r`` at each point."""
    exact: np.ndarray
    """The closed form at each point, in volts."""
    norm: float
    """``(int phi^2 r)^(1/2)`` over the measured elements."""
    axis_located: Any
    """The axis samples within the disc, located; ``None`` where the disc misses the axis."""
    axis_exact: np.ndarray | None
    """The closed form at them."""


@functools.cache
def _reference(r_i: float, width_nm: float, near_nm: float, beyond_nm: float) -> Reference:
    """Return the closed form on the disc's elements at least ``beyond_nm`` from the atom."""
    data, mesh = _mesh(r_i, near_nm)
    permittivity = VACUUM_PERMITTIVITY * _electrolyte().permittivity_0
    near = data.materials.index("near")
    elements = np.flatnonzero(data.triangle_material == near)
    corners = data.vertices[data.triangles[elements]]
    centroid = corners.mean(axis=1)
    keep = np.hypot(centroid[:, 0] - r_i, centroid[:, 1] - Z_ATOM_NM) >= beyond_nm
    corners = corners[keep]
    barycentric, weights = triangle_rule(8)
    points = np.einsum("qv,mvd->mqd", barycentric, corners).reshape(-1, 2)
    edges = corners[:, 1:] - corners[:, :1]
    area = 0.5 * np.abs(edges[:, 0, 0] * edges[:, 1, 1] - edges[:, 0, 1] * edges[:, 1, 0])
    exact = exact_potential_V(points[:, 0], points[:, 1], r_i, Z_ATOM_NM, width_nm, permittivity)
    weight = (np.outer(area, weights).reshape(-1)) * points[:, 0]
    norm = math.sqrt(float(np.sum(weight * exact**2)))
    axis_located: Any = None
    axis_exact: np.ndarray | None = None
    if r_i < DISC_NM:
        axis_z = np.linspace(Z_ATOM_NM - 0.95 * DISC_NM, Z_ATOM_NM + 0.95 * DISC_NM, 201)
        axis_located = mesh(np.zeros_like(axis_z), axis_z)
        axis_exact = exact_potential_V(
            np.zeros_like(axis_z), axis_z, r_i, Z_ATOM_NM, width_nm, permittivity
        )
    return Reference(
        located=mesh(points[:, 0], points[:, 1]),
        weight=weight,
        exact=exact,
        norm=norm,
        axis_located=axis_located,
        axis_exact=axis_exact,
    )


def solve_error(
    r_i: float, width_nm: float, near_nm: float, deposit_order: int, *, beyond_nm: float = 0.0
) -> tuple[float, float, int]:
    """Deposit, solve ``poisson`` at P2, and return the disc error, the axis error and the size.

    The disc error is ``(int (phi_h - phi)^2 r)^(1/2) / (int phi^2 r)^(1/2)`` over the
    elements of the disc whose centroid is at least ``beyond_nm`` from the atom;
    the axis error the largest ``|phi_h - phi|`` on ``r = 0`` within the disc,
    relative to ``max |phi|`` there.
    """
    data, mesh = _mesh(r_i, near_nm)
    reference = _reference(r_i, width_nm, near_nm, beyond_nm)
    found = deposit(_lattice(r_i, width_nm), data, deposit_order)
    model = models.create("poisson", electrolyte=_electrolyte())
    scales = model.scales
    solution = model.solve(
        mesh,
        AXISYMMETRIC,
        potential_values=mesh.BoundaryCF({"cis": 0.0, "trans": 0.0}),
        fixed_charge=gridfunction(found, mesh) / scales.charge_density_C_m3,
    )
    computed = solution.state(reference.located).reshape(-1) * scales.potential_V
    error = math.sqrt(float(np.sum(reference.weight * (computed - reference.exact) ** 2)))
    if reference.axis_exact is None:
        axis_error = float("nan")
    else:
        axis_h = solution.state(reference.axis_located).reshape(-1) * scales.potential_V
        axis_error = float(
            np.max(np.abs(axis_h - reference.axis_exact)) / np.max(np.abs(reference.axis_exact))
        )
    return error / reference.norm, axis_error, data.element_count


def errors_and_rates(
    r_i: float, logger: logging.Logger
) -> tuple[dict[int, list[float]], dict[int, list[float]]]:
    """Return the disc errors at each of :data:`LEVELS_NM` and the rates between them, by order."""
    errors: dict[int, list[float]] = {2: [], 0: []}
    for order in (2, 0):
        for near in LEVELS_NM:
            error, axis, elements = solve_error(r_i, WIDTH_NM, near, order)
            errors[order].append(error)
            logger.info(
                "VER-58 r_i = %.1f nm, w = %.2f nm, near h = %.3f nm (%d elements), P%d deposit: "
                "disc L2(r) error %.3e, on-axis error %.3e",
                r_i,
                WIDTH_NM,
                near,
                elements,
                order,
                error,
                axis,
            )
    rates = {
        order: [math.log2(found[i] / found[i + 1]) for i in range(len(found) - 1)]
        for order, found in errors.items()
    }
    logger.info("VER-58 r_i = %.1f nm: rates P2 %s, P0 %s", r_i, rates[2], rates[0])
    return errors, rates


def release() -> None:
    """Drop every mesh, lattice and closed form computed here.

    The caches live as long as the process, and a ``pytest-xdist`` worker goes
    on to other files: each VER-58 file releases them when it is done, so the
    0.05 nm level's mesh and its located quadrature points are not held through
    the rest of the session. Nothing is shared between the two files' atoms.
    """
    for cached in (_mesh, _lattice, _reference, _electrolyte):
        cached.cache_clear()
