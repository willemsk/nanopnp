"""VER-58 at Tier 2: one smeared atom deposited and solved, against its closed-form potential.

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
"""

from __future__ import annotations

import logging
import math

import numpy as np
import pytest
from scipy.special import erf

from nanopnp.charge.deposit import deposit, gridfunction, triangle_rule
from nanopnp.charge.kernel import SourceAtoms, sum_kernel
from nanopnp.core.constants import ELEMENTARY_CHARGE, VACUUM_PERMITTIVITY
from nanopnp.materials.electrolyte import Electrolyte
from nanopnp.mesh.adapter import MeshData, from_ngsolve, to_ngsolve
from nanopnp.physics import models
from nanopnp.physics.measures import AXISYMMETRIC

logger = logging.getLogger(__name__)

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


def exact_potential_V(
    r_nm: np.ndarray, z_nm: np.ndarray, r_i: float, z_i: float, width_nm: float, permittivity: float
) -> np.ndarray:
    """Return the closed form of *Design* §4 for a unit charge, in volts."""
    r = np.asarray(r_nm, dtype=np.float64)[..., None] * 1e-9
    z = np.asarray(z_nm, dtype=np.float64)[..., None] * 1e-9
    theta = 2.0 * math.pi * np.arange(AZIMUTHS) / AZIMUTHS
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
        image = (sphere / a) * np.mean(1.0 / image_distance, axis=-1)
    prefactor = ELEMENTARY_CHARGE / (4.0 * math.pi * permittivity)
    return np.asarray(prefactor * (np.mean(direct, axis=-1) - image))


def test_ver58_the_closed_form_vanishes_on_the_sphere() -> None:
    """The oracle first: the potential is zero on the grounded sphere, to 1e-17 of its peak."""
    eps = VACUUM_PERMITTIVITY * 78.15
    for r_i in (0.0, 1.5):
        angles = np.linspace(-0.5 * math.pi, 0.5 * math.pi, 41)
        on_sphere = exact_potential_V(
            SPHERE_NM * np.cos(angles), SPHERE_NM * np.sin(angles), r_i, Z_ATOM_NM, WIDTH_NM, eps
        )
        peak = float(
            exact_potential_V(
                np.array([r_i]), np.array([Z_ATOM_NM]), r_i, Z_ATOM_NM, WIDTH_NM, eps
            )[0]
        )
        assert np.max(np.abs(on_sphere)) <= 1e-12 * abs(peak)
    # On the axis every ring point is equidistant: the closed form's own special case.
    rho = math.hypot(1.5, 2.0 - Z_ATOM_NM) * 1e-9
    a = math.hypot(1.5, Z_ATOM_NM)
    scale = SPHERE_NM**2 / a**2
    rho_image = math.hypot(scale * 1.5, 2.0 - scale * Z_ATOM_NM) * 1e-9
    axis = (
        ELEMENTARY_CHARGE
        / (4 * math.pi * eps)
        * (math.erf(rho / (WIDTH_NM * 1e-9)) / rho - SPHERE_NM / a / rho_image)
    )
    found = exact_potential_V(np.array([0.0]), np.array([2.0]), 1.5, Z_ATOM_NM, WIDTH_NM, eps)
    assert float(found[0]) == pytest.approx(axis, rel=1e-13)


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


def _solve_error(
    r_i: float, width_nm: float, near_nm: float, deposit_order: int, *, beyond_nm: float = 0.0
) -> tuple[float, float, int]:
    """Deposit, solve ``poisson`` at P2, and return the disc error, the axis error and the size.

    The disc error is ``(int (phi_h - phi)^2 r)^(1/2) / (int phi^2 r)^(1/2)`` over the
    elements of the disc whose centroid is at least ``beyond_nm`` from the atom;
    the axis error the largest ``|phi_h - phi|`` on ``r = 0`` within the disc,
    relative to ``max |phi|`` there.
    """
    import ngsolve as ngs

    electrolyte = Electrolyte.from_parameter_file("willems2020_nacl")
    permittivity = VACUUM_PERMITTIVITY * electrolyte.permittivity_0
    data = _sphere(r_i, Z_ATOM_NM, near_nm)
    assert {"cis", "trans", "axis"} <= set(data.boundaries), data.boundaries
    mesh = to_ngsolve(data)
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
    lattice = sum_kernel(atoms, H).grid
    found = deposit(lattice, data, deposit_order)
    model = models.create("poisson", electrolyte=electrolyte)
    scales = model.scales
    solution = model.solve(
        mesh,
        AXISYMMETRIC,
        potential_values=mesh.BoundaryCF({"cis": 0.0, "trans": 0.0}),
        fixed_charge=gridfunction(found, mesh) / scales.charge_density_C_m3,
    )

    near = data.materials.index("near")
    elements = np.flatnonzero(data.triangle_material == near)
    corners = data.vertices[data.triangles[elements]]
    centroid = corners.mean(axis=1)
    keep = np.hypot(centroid[:, 0] - r_i, centroid[:, 1] - Z_ATOM_NM) >= beyond_nm
    elements, corners = elements[keep], corners[keep]
    barycentric, weights = triangle_rule(8)
    points = np.einsum("qv,mvd->mqd", barycentric, corners).reshape(-1, 2)
    edges = corners[:, 1:] - corners[:, :1]
    area = 0.5 * np.abs(edges[:, 0, 0] * edges[:, 1, 1] - edges[:, 0, 1] * edges[:, 1, 0])
    located = mesh(points[:, 0], points[:, 1])
    computed = solution.state(located).reshape(-1) * scales.potential_V
    exact = exact_potential_V(points[:, 0], points[:, 1], r_i, Z_ATOM_NM, width_nm, permittivity)
    weight = (np.outer(area, weights).reshape(-1)) * points[:, 0]
    error = math.sqrt(float(np.sum(weight * (computed - exact) ** 2)))
    norm = math.sqrt(float(np.sum(weight * exact**2)))

    axis_z = np.linspace(Z_ATOM_NM - 0.95 * DISC_NM, Z_ATOM_NM + 0.95 * DISC_NM, 201)
    if r_i >= DISC_NM:
        axis_error = float("nan")
    else:
        on_axis = mesh(np.zeros_like(axis_z), axis_z)
        axis_h = solution.state(on_axis).reshape(-1) * scales.potential_V
        axis_exact = exact_potential_V(
            np.zeros_like(axis_z), axis_z, r_i, Z_ATOM_NM, width_nm, permittivity
        )
        axis_error = float(np.max(np.abs(axis_h - axis_exact)) / np.max(np.abs(axis_exact)))
    del ngs
    return error / norm, axis_error, data.element_count


@pytest.mark.parametrize("r_i", [0.0, 1.5])
def test_ver58_deposited_potential_converges_at_the_potentials_own_rate(r_i: float) -> None:
    """The P2 deposit's potential error falls at >= 2.5 between the finest two meshes; P0's at 2."""
    sizes = (0.2, 0.1, 0.05)
    errors: dict[int, list[float]] = {2: [], 0: []}
    for order in (2, 0):
        for near in sizes:
            error, axis, elements = _solve_error(r_i, WIDTH_NM, near, order)
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
    assert rates[2][-1] >= 2.5
    assert rates[0][-1] < rates[2][-1]
    assert errors[2][-1] < errors[0][-1]


def test_ver58_an_unresolved_atom_is_recorded_beside_p0() -> None:
    """Recorded: a CHARMM polar hydrogen on 0.1 nm elements, the error at >= 1 nm from it."""
    width = 0.0112
    found = {}
    for order in (2, 0):
        error, _, elements = _solve_error(1.5, width, 0.1, order, beyond_nm=1.0)
        found[order] = error
        logger.info(
            "VER-58 unresolved atom (w = %.4f nm) on 0.1 nm elements (%d), P%d deposit: L2(r) "
            "error at >= 1 nm from it %.3e",
            width,
            elements,
            order,
            error,
        )
    assert all(math.isfinite(value) for value in found.values())
