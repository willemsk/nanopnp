"""PHY-16 step 6: the lattice deposited on the deployed mesh by ``r``-weighted L2 projection (WP28).

On each triangle ``K`` the deposit is the polynomial ``rho_h|K`` of degree ``k`` --
the potential's element order -- solving

``int_K rho_h v r dr dz = sum_{n in K} m_n v(x_n)``  for every ``v`` in ``P_k(K)``,

where ``m_n = tau_n h^2 a_n / (2 pi)`` is the lattice's trapezoid mass at node
``n`` and ``a_n = 2 pi r rho`` its areal density. Since ``rho r = a/(2 pi)``,
nothing singular is sampled (*Design* §2). Every test function of the
potential's space restricts to ``P_k(K)``, so the assembled source equals the
lattice integral of the kernel against every test function: the projection adds
no error of its own wherever the assembly integrates degree ``2k + 1`` (D13).

**The basis** is the scaled monomials ``((r - r_K)/d_K)^a ((z - z_K)/d_K)^b``,
``a + b <= k``, about each centroid and scaled by the diameter, so every Gram
matrix is well conditioned. Each Gram is integrated by a collapsed Gauss rule
exact to degree ``2k + 1``. The generated meshes are affine (nothing calls
``Curve``), so the barycentric node location and the NGSolve geometry agree.

**Each lattice node is counted in exactly one element**: the lowest-indexed one
containing it, so a node on a shared edge is not counted twice. Charge on no
element at all is refused, naming its ``(r, z)`` (D4, QR-12).

**The payload** is the coefficients ``(elements, basis)`` in C m^-3, the order,
and a digest of the element geometry they belong to. :func:`gridfunction` sets
an NGSolve ``L2(order=k)`` field from them on a mesh whose element geometry
hashes to the same digest, and refuses any other, naming both digests (D5).

NumPy and NGSolve are imported inside the functions that use them (CLAUDE.md).
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.charge.fields import ChargeFieldError
from nanopnp.core.hashing import Canonicalisable, content_hash
from nanopnp.core.stages import CancelToken, Progress, check_cancelled, report

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

    from nanopnp.charge.kernel import SourceAtoms
    from nanopnp.core.scaling import Scales
    from nanopnp.core.typing import Expression, Mesh
    from nanopnp.density.grid import RadialGrid
    from nanopnp.mesh.adapter import MeshData

__all__ = [
    "DEPOSIT_PAYLOAD",
    "GEOMETRY_SCHEMA",
    "SOLID_SHARE_MIN",
    "UNCOVERED_TOL",
    "Deposit",
    "DepositedCharge",
    "SolidShare",
    "basis_exponents",
    "check_solid_share",
    "deposit",
    "element_geometry",
    "geometry_digest",
    "gridfunction",
    "lattice_masses",
    "locate",
    "mesh_geometry_digest",
    "triangle_rule",
]

logger = logging.getLogger(__name__)

GEOMETRY_SCHEMA = "nanopnp/deposit-geometry/v1"
"""Domain separator of the element-geometry digest a deposit belongs to (D5)."""

DEPOSIT_PAYLOAD = "deposit"
"""The stage-7 payload key of the deposit's ``.npz`` (D7)."""

UNCOVERED_TOL = 1e-12
"""Largest lattice mass on no element, relative to the largest mass, that is not refused (D4)."""

SOLID_SHARE_MIN = 0.5
"""Smallest share of ``sum |q_i|`` whose atom centres must lie in a solid material (D4).

A structure in another frame than its mesh shows as its atoms sitting in the
electrolyte; ClyA's charged atoms sit in the protein (*Design* §5, the
``centre_z_nm`` row).
"""

BARYCENTRIC_TOL = 1e-12
"""How far below zero a barycentric coordinate may fall and the point still count as inside.

Lattice nodes on an element edge -- the axis nodes on an axis edge above all --
land within round-off of zero; the lowest-index rule then picks one element.
"""

LOCATE_CHUNK = 2_000_000
"""Candidate (point, triangle) pairs tested per vectorised chunk."""

NM_TO_M = 1e-9
"""Metres per nanometre."""


# -- the reference element ------------------------------------------------------


def basis_exponents(order: int) -> tuple[tuple[int, int], ...]:
    """Return the scaled-monomial exponents ``(a, b)``, ``a + b <= order``, by total degree."""
    return tuple((degree - b, b) for degree in range(order + 1) for b in range(degree + 1))


def triangle_rule(degree: int) -> tuple[np.ndarray, np.ndarray]:
    """Return a triangle quadrature exact for every polynomial of total degree ``degree``.

    A collapsed (Duffy) product of Gauss-Legendre rules: ``n = ceil((degree + 2)/2)``
    points a side, the collapse adding one degree in the outer direction.

    Returns
    -------
    tuple of numpy.ndarray
        Barycentric coordinates ``(points, 3)`` and weights summing to 1, so a
        triangle's integral is its area times the weighted sum.
    """
    import numpy as np

    count = max(1, math.ceil((degree + 2) / 2))
    nodes, weights = np.polynomial.legendre.leggauss(count)
    u = 0.5 * (nodes + 1.0)
    w = 0.5 * weights
    outer, inner = np.meshgrid(u, u, indexing="ij")
    weight = np.outer(w, w) * (1.0 - outer)
    xi = outer.reshape(-1)
    eta = (inner * (1.0 - outer)).reshape(-1)
    barycentric = np.stack([1.0 - xi - eta, xi, eta], axis=1)
    return barycentric, 2.0 * weight.reshape(-1)


def element_geometry(data: MeshData) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return each triangle's centroid ``(m, 2)``, diameter ``(m,)`` and area ``(m,)``, in nm."""
    import numpy as np

    corners = data.vertices[data.triangles]
    centroid = corners.mean(axis=1)
    edges = corners[:, [1, 2, 0]] - corners
    diameter = np.max(np.hypot(edges[..., 0], edges[..., 1]), axis=1)
    area = 0.5 * np.abs(
        edges[:, 0, 0] * (corners[:, 2, 1] - corners[:, 0, 1])
        - edges[:, 0, 1] * (corners[:, 2, 0] - corners[:, 0, 0])
    )
    return centroid, diameter, area


def geometry_digest(data: MeshData) -> str:
    """Return the digest of the element geometry: every triangle's corners, in element order (D5).

    A mesh with the same triangles in another order, or one vertex moved, is
    another digest, and a deposit made on one is refused on the other.
    """
    import numpy as np

    return content_hash(
        GEOMETRY_SCHEMA, {"corners": np.ascontiguousarray(data.vertices[data.triangles])}
    )


def mesh_geometry_digest(mesh: Mesh) -> str:
    """Return :func:`geometry_digest` of an NGSolve mesh, read from its own arrays.

    Read from the mesh NGSolve will assemble on, not from the :class:`MeshData`
    it was built from, so the assertion that the two number their elements
    alike is made against NGSolve's own element order (D5).
    """
    import numpy as np

    ngmesh = mesh.ngmesh
    vertices = np.asarray(ngmesh.Coordinates(), dtype=np.float64)[:, :2]
    nodes = np.asarray(ngmesh.Elements2D().NumPy()["nodes"], dtype=np.int64)[:, :3] - 1
    return content_hash(GEOMETRY_SCHEMA, {"corners": np.ascontiguousarray(vertices[nodes])})


# -- point location ---------------------------------------------------------------


def locate(data: MeshData, points_nm: np.ndarray, *, cell_nm: float) -> np.ndarray:
    """Return the lowest-indexed triangle containing each point, or -1 (*Design* §2).

    The points are bucketed onto a uniform grid of ``cell_nm``; each triangle is
    rasterised over the buckets its bounding box touches, and its candidates are
    tested barycentrically, with :data:`BARYCENTRIC_TOL` of slack so that a point
    on an edge is inside both elements and the lower index takes it.

    Parameters
    ----------
    data
        The mesh, in nm.
    points_nm
        ``(n, 2)`` ``(r, z)``.
    cell_nm
        The bucket size: the lattice spacing for lattice nodes, for which every
        bucket holds exactly one node.
    """
    import numpy as np

    points = np.asarray(points_nm, dtype=np.float64).reshape(-1, 2)
    owner = np.full(points.shape[0], np.iinfo(np.int64).max, dtype=np.int64)
    if points.shape[0] == 0:
        return np.full(0, -1, dtype=np.int64)
    bucket = np.rint(points / cell_nm).astype(np.int64)
    low = bucket.min(axis=0)
    high = bucket.max(axis=0)
    shape = high - low + 1
    flat = (bucket[:, 1] - low[1]) * shape[0] + (bucket[:, 0] - low[0])
    order = np.argsort(flat, kind="stable")
    starts = np.searchsorted(flat[order], np.arange(shape[0] * shape[1] + 1))

    corners = data.vertices[data.triangles]
    box_low = np.ceil(corners.min(axis=1) / cell_nm - 0.5 - 1e-9).astype(np.int64)
    box_high = np.floor(corners.max(axis=1) / cell_nm + 0.5 + 1e-9).astype(np.int64)
    box_low = np.maximum(box_low, low)
    box_high = np.minimum(box_high, high)
    span = np.maximum(box_high - box_low + 1, 0)
    buckets = span[:, 0] * span[:, 1]
    candidates = np.flatnonzero(buckets > 0)
    # Barycentric maps, once per triangle: lambda_1,2 = T^-1 (p - v0).
    v0 = corners[:, 0]
    jacobian = np.stack([corners[:, 1] - v0, corners[:, 2] - v0], axis=2)
    determinant = jacobian[:, 0, 0] * jacobian[:, 1, 1] - jacobian[:, 0, 1] * jacobian[:, 1, 0]
    inverse = np.empty_like(jacobian)
    inverse[:, 0, 0] = jacobian[:, 1, 1] / determinant
    inverse[:, 0, 1] = -jacobian[:, 0, 1] / determinant
    inverse[:, 1, 0] = -jacobian[:, 1, 0] / determinant
    inverse[:, 1, 1] = jacobian[:, 0, 0] / determinant

    cumulative = np.cumsum(buckets[candidates])
    begin = 0
    while begin < candidates.size:
        end = int(
            np.searchsorted(
                cumulative,
                cumulative[begin] - buckets[candidates[begin]] + LOCATE_CHUNK,
                side="right",
            )
        )
        end = max(end, begin + 1)
        chunk = candidates[begin:end]
        begin = end
        counts = buckets[chunk]
        triangle = np.repeat(chunk, counts)
        offset = np.arange(int(counts.sum())) - np.repeat(np.cumsum(counts) - counts, counts)
        width = span[triangle, 0]
        b_r = box_low[triangle, 0] + offset % width
        b_z = box_low[triangle, 1] + offset // width
        cell = (b_z - low[1]) * shape[0] + (b_r - low[0])
        first, last = starts[cell], starts[cell + 1]
        occupied = last > first
        triangle, first, last = triangle[occupied], first[occupied], last[occupied]
        per = last - first
        triangle = np.repeat(triangle, per)
        slot = np.repeat(first, per) + (
            np.arange(int(per.sum())) - np.repeat(np.cumsum(per) - per, per)
        )
        point = order[slot]
        relative = points[point] - v0[triangle]
        l1 = inverse[triangle, 0, 0] * relative[:, 0] + inverse[triangle, 0, 1] * relative[:, 1]
        l2 = inverse[triangle, 1, 0] * relative[:, 0] + inverse[triangle, 1, 1] * relative[:, 1]
        inside = (
            (l1 >= -BARYCENTRIC_TOL)
            & (l2 >= -BARYCENTRIC_TOL)
            & (1.0 - l1 - l2 >= -BARYCENTRIC_TOL)
        )
        np.minimum.at(owner, point[inside], triangle[inside])
    return np.where(owner == np.iinfo(np.int64).max, -1, owner)


# -- the projection ------------------------------------------------------------------


def lattice_masses(grid: RadialGrid) -> tuple[np.ndarray, np.ndarray]:
    """Return the lattice's nonzero nodes ``(n, 2)`` in nm and their masses ``m_n``.

    ``m_n = tau_n h_r h_z a_n / (2 pi)`` with the lengths in nm and ``a_n`` in
    C m^-2, scaled by 1e9 so that ``sum_n m_n v(x_n)`` is ``int rho v r dr dz`` with
    ``rho`` in C m^-3 and ``r dr dz`` in nm^3 -- the units the mesh integral takes.
    """
    import numpy as np

    weights = np.outer(grid.trapezium_weights("z"), grid.trapezium_weights("r"))
    masses = weights * grid.values / (2.0 * math.pi) * 1e9
    i_z, i_r = np.nonzero(masses)
    nodes = np.stack([grid.r_nm[i_r], grid.z_nm[i_z]], axis=1)
    return nodes, masses[i_z, i_r]


def _scaled(
    points: np.ndarray, centroid: np.ndarray, diameter: np.ndarray, order: int
) -> np.ndarray:
    """Return the scaled monomials at ``points`` (``(..., 2)``) about each element's centroid."""
    import numpy as np

    xi = (points[..., 0] - centroid[..., 0]) / diameter
    eta = (points[..., 1] - centroid[..., 1]) / diameter
    return np.stack([xi**a * eta**b for a, b in basis_exponents(order)], axis=-1)


def _gram(
    data: MeshData,
    centroid: np.ndarray,
    diameter: np.ndarray,
    area: np.ndarray,
    order: int,
    *,
    weighted: bool,
) -> np.ndarray:
    """Return every element's Gram matrix ``int_K phi_a phi_b r``, exact to degree ``2k + 1``."""
    import numpy as np

    barycentric, weights = triangle_rule(2 * order + 1)
    corners = data.vertices[data.triangles]
    count = len(basis_exponents(order))
    gram = np.empty((corners.shape[0], count, count), dtype=np.float64)
    step = 20_000
    for start in range(0, corners.shape[0], step):
        part = slice(start, start + step)
        points = np.einsum("qv,mvd->mqd", barycentric, corners[part])
        phi = _scaled(points, centroid[part, None, :], diameter[part, None], order)
        radial = points[..., 0] if weighted else np.ones(points.shape[:2])
        scale = radial * weights[None, :] * area[part, None]
        gram[part] = np.einsum("mqa,mqb,mq->mab", phi, phi, scale)
    return gram


@dataclass(frozen=True)
class Deposit:
    """The deposited fixed charge: per-element polynomial coefficients on one mesh (D3, D5).

    Parameters
    ----------
    coefficients
        ``(elements, basis)`` in C m^-3, against :func:`basis_exponents` of
        ``order`` about each element's centroid and scaled by its diameter.
    order
        ``k``, the potential's element order.
    geometry_digest
        :func:`geometry_digest` of the mesh the coefficients belong to.
    centroids_nm, diameters_nm
        The basis's centre and scale per element, in nm.
    element_charge_C
        Each element's charge, ``2 pi int_K rho_h r``: its lattice charge exactly.
    uncovered
        The largest lattice mass on no element, relative to the largest mass, and
        its ``(r, z)`` in nm; zero and ``None`` when every node is covered.
    nodes
        Lattice nodes carrying mass, and how many of them no element holds.
    weighted
        Whether the Gram carried the ``r`` weight; ``False`` only for the broken
        construction VER-01's consumer leg must fail (*Design* §5).
    seconds
        Wall time of the projection.
    """

    coefficients: np.ndarray
    order: int
    geometry_digest: str
    centroids_nm: np.ndarray
    diameters_nm: np.ndarray
    element_charge_C: np.ndarray
    uncovered: tuple[float, tuple[float, float] | None]
    nodes: tuple[int, int]
    weighted: bool = True
    seconds: float = 0.0

    def write(self, path: Path) -> Path:
        """Write the deposit as ``.npz``; return the path."""
        import numpy as np

        path.parent.mkdir(parents=True, exist_ok=True)
        ratio, where = self.uncovered
        with path.open("wb") as handle:
            np.savez(
                handle,
                coefficients=self.coefficients,
                order=np.asarray(self.order),
                geometry_digest=np.asarray(self.geometry_digest),
                centroids_nm=self.centroids_nm,
                diameters_nm=self.diameters_nm,
                element_charge_C=self.element_charge_C,
                uncovered_ratio=np.asarray(ratio),
                uncovered_at_nm=np.asarray(where if where is not None else (np.nan, np.nan)),
                nodes=np.asarray(self.nodes),
                weighted=np.asarray(self.weighted),
                seconds=np.asarray(self.seconds),
            )
        return path

    @classmethod
    def read(cls, path: Path) -> Deposit:
        """Read a deposit written by :meth:`write`."""
        import numpy as np

        with np.load(path, allow_pickle=False) as data:
            where = tuple(float(value) for value in data["uncovered_at_nm"])
            nodes = tuple(int(value) for value in data["nodes"])
            return cls(
                coefficients=np.asarray(data["coefficients"]),
                order=int(data["order"]),
                geometry_digest=str(data["geometry_digest"]),
                centroids_nm=np.asarray(data["centroids_nm"]),
                diameters_nm=np.asarray(data["diameters_nm"]),
                element_charge_C=np.asarray(data["element_charge_C"]),
                uncovered=(
                    float(data["uncovered_ratio"]),
                    None if math.isnan(where[0]) else (where[0], where[1]),
                ),
                nodes=(nodes[0], nodes[1]),
                weighted=bool(data["weighted"]),
                # Read back rather than reset: every reader records this deposit's
                # summary (the solve's ``fields`` record among them), and a deposit
                # that took seconds must not read as one that took none.
                seconds=float(data["seconds"]) if "seconds" in data.files else 0.0,
            )

    def charge_C(self) -> float:
        """Return the deposit's total charge, ``sum_K Q_K``, in coulombs."""
        return math.fsum(self.element_charge_C.tolist())

    def evaluate(self, points_nm: np.ndarray, elements: np.ndarray) -> np.ndarray:
        """Return ``rho_h`` in C m^-3 at ``points_nm`` ``(n, 2)``, each in its given element."""
        import numpy as np

        phi = _scaled(
            np.asarray(points_nm, dtype=np.float64),
            self.centroids_nm[elements],
            self.diameters_nm[elements],
            self.order,
        )
        return np.asarray(np.sum(phi * self.coefficients[elements], axis=-1))

    def material_charges_e(self, data: MeshData) -> dict[str, float]:
        """Return the deposited charge per material, in e: where the charge was put (D4)."""
        import numpy as np

        from nanopnp.core.constants import ELEMENTARY_CHARGE

        found = np.bincount(
            data.triangle_material,
            weights=self.element_charge_C,
            minlength=len(data.materials),
        )
        return {
            name: float(found[index]) / ELEMENTARY_CHARGE
            for index, name in enumerate(data.materials)
        }

    def summary(self) -> dict[str, Canonicalisable]:
        """Return what the stage-7 artefact records about the deposit (FR-25)."""
        ratio, where = self.uncovered
        return {
            "order": self.order,
            "elements": int(self.coefficients.shape[0]),
            "basis": int(self.coefficients.shape[1]),
            "geometry_digest": self.geometry_digest,
            "lattice_nodes": self.nodes[0],
            "uncovered_nodes": self.nodes[1],
            "uncovered_largest_ratio": ratio,
            "uncovered_largest_at_nm": list(where) if where is not None else None,
            "seconds": self.seconds,
        }


def deposit(
    grid: RadialGrid,
    data: MeshData,
    order: int,
    *,
    weighted: bool = True,
    cancel: CancelToken | None = None,
    progress: Progress | None = None,
) -> Deposit:
    """Project the lattice onto discontinuous ``P_order`` on ``data`` (PHY-16 step 6, D3).

    Parameters
    ----------
    grid
        The export lattice: areal density in C m^-2.
    data
        The deployed mesh.
    order
        ``k``: the potential's element order.
    weighted
        Carry the ``r`` weight in the Gram; ``False`` only for a broken
        construction under test.
    cancel, progress
        Checked and reported before the projection (D12).

    Raises
    ------
    ChargeFieldError
        Where lattice mass falls on no element, more than :data:`UNCOVERED_TOL`
        of the largest mass, naming its ``(r, z)`` (D4).
    """
    import numpy as np

    started = time.perf_counter()
    check_cancelled(cancel, "locating the lattice in the mesh")
    report(progress, 0.0, "locating the lattice nodes in the mesh")
    nodes, masses = lattice_masses(grid)
    owner = locate(data, nodes, cell_nm=min(grid.spacing_nm))
    missing = owner < 0
    largest = float(np.max(np.abs(masses))) if masses.size else 0.0
    uncovered: tuple[float, tuple[float, float] | None] = (0.0, None)
    if np.any(missing):
        worst = int(np.flatnonzero(missing)[np.argmax(np.abs(masses[missing]))])
        ratio = float(abs(masses[worst]) / largest)
        uncovered = (ratio, (float(nodes[worst, 0]), float(nodes[worst, 1])))
        if ratio > UNCOVERED_TOL:
            raise ChargeFieldError(
                "lattice charge falls on no element of the mesh (PHY-16 NOTE on the deposition)",
                f"{int(missing.sum())} lattice nodes carry charge outside every element, the "
                f"largest {ratio:.3g} of the largest node's against {UNCOVERED_TOL:g}; a mesh "
                "that does not cover the structure, or a structure in another frame, moves "
                "charge silently",
                f"(r, z) = ({nodes[worst, 0]:.4g}, {nodes[worst, 1]:.4g}) nm",
            )
    check_cancelled(cancel, "the projection onto the mesh")
    report(progress, 0.4, f"projecting onto P{order} on {data.element_count} elements")
    centroid, diameter, area = element_geometry(data)
    held = ~missing
    phi = _scaled(nodes[held], centroid[owner[held]], diameter[owner[held]], order)
    count = len(basis_exponents(order))
    moments = np.zeros((data.element_count, count), dtype=np.float64)
    for column in range(count):
        moments[:, column] = np.bincount(
            owner[held], weights=masses[held] * phi[:, column], minlength=data.element_count
        )
    gram = _gram(data, centroid, diameter, area, order, weighted=weighted)
    coefficients = np.linalg.solve(gram, moments[..., None])[..., 0]
    # 2 pi, and nm^3 -> m^3 for the r dr dz the masses were taken in.
    charges = 2.0 * math.pi * 1e-27 * moments[:, 0]
    seconds = time.perf_counter() - started
    report(progress, 1.0, f"deposited on {data.element_count} elements in {seconds:.1f} s")
    return Deposit(
        coefficients=coefficients,
        order=order,
        geometry_digest=geometry_digest(data),
        centroids_nm=centroid,
        diameters_nm=diameter,
        element_charge_C=charges,
        uncovered=uncovered,
        nodes=(int(masses.size), int(missing.sum())),
        weighted=weighted,
        seconds=seconds,
    )


# -- the frame check ---------------------------------------------------------------


@dataclass(frozen=True)
class SolidShare:
    """Where the atom centres sit: ``sum |q_i|`` per material, and the solids' share (D4).

    Parameters
    ----------
    share
        The share of ``sum |q_i|`` centred in a solid material.
    by_material
        ``sum |q_i|`` per material, in e, with ``outside`` for atoms on no element.
    """

    share: float
    by_material: dict[str, float]

    def summary(self) -> dict[str, Canonicalisable]:
        """Return the record of the check."""
        return {
            "solid_share": self.share,
            "minimum": SOLID_SHARE_MIN,
            "absolute_charge_by_material_e": dict(sorted(self.by_material.items())),
        }


def check_solid_share(
    atoms: SourceAtoms, data: MeshData, solids: tuple[str, ...], *, cell_nm: float
) -> SolidShare:
    """Refuse a structure whose charge is not centred in the mesh's solids (D4, QR-12).

    Raises
    ------
    ChargeFieldError
        If less than :data:`SOLID_SHARE_MIN` of ``sum |q_i|`` has its atom centres
        in a solid material, naming the share and the frame shift the atoms were
        placed with.
    """
    import numpy as np

    points = np.stack([atoms.r_nm, atoms.z_nm], axis=1)
    owner = locate(data, points, cell_nm=cell_nm)
    magnitude = np.abs(atoms.weight_e)
    material = np.where(owner >= 0, data.triangle_material[np.maximum(owner, 0)], -1)
    by_material = {
        name: float(np.sum(magnitude[material == index]))
        for index, name in enumerate(data.materials)
    }
    by_material["outside"] = float(np.sum(magnitude[material < 0]))
    total = float(np.sum(magnitude))
    solid = sum(by_material.get(name, 0.0) for name in solids)
    share = solid / total if total > 0.0 else 0.0
    if not share >= SOLID_SHARE_MIN:
        raise ChargeFieldError(
            "the structure's charge is not centred in the mesh's solid materials "
            "(PHY-16 NOTE on the deposition)",
            f"{share:.3g} of sum |q_i| has its atom centres in {', '.join(solids) or 'no solid'} "
            f"against the {SOLID_SHARE_MIN:g} this gate requires; the atoms were shifted by "
            f"z <- z - {atoms.shift_z_nm:g} nm into the model frame. A structure in another frame "
            "than its mesh shows exactly so",
        )
    return SolidShare(share=share, by_material=by_material)


# -- the transfer -----------------------------------------------------------------


def gridfunction(deposit: Deposit, mesh: Mesh) -> Expression:
    """Return the deposit as an NGSolve ``L2(order=k)`` field on ``mesh``, in C m^-3 (D5).

    Raises
    ------
    ChargeFieldError
        If the mesh's element geometry, read from NGSolve, does not hash to the
        deposit's digest: another mesh, or this one with its elements permuted.
    """
    import ngsolve as ngs

    found = mesh_geometry_digest(mesh)
    if found != deposit.geometry_digest:
        raise ChargeFieldError(
            "the deposited charge belongs to another mesh (D5)",
            f"its element geometry digest is {deposit.geometry_digest} and this mesh's is {found}; "
            "a deposit is read only on the mesh it was made on, in its element order",
        )
    constant = ngs.L2(mesh, order=0)
    if constant.ndof != deposit.coefficients.shape[0]:
        raise ChargeFieldError(
            "the deposited charge belongs to another mesh (D5)",
            f"it has {deposit.coefficients.shape[0]} elements and this mesh {constant.ndof}",
        )

    def per_element(values: np.ndarray) -> Expression:
        field = ngs.GridFunction(constant)
        field.vec.FV().NumPy()[:] = values
        return field

    r_centre = per_element(deposit.centroids_nm[:, 0])
    z_centre = per_element(deposit.centroids_nm[:, 1])
    scale = per_element(deposit.diameters_nm)
    xi = (ngs.x - r_centre) / scale
    eta = (ngs.y - z_centre) / scale
    polynomial: Expression = 0.0
    for column, (a, b) in enumerate(basis_exponents(deposit.order)):
        term = per_element(deposit.coefficients[:, column])
        for _ in range(a):
            term = term * xi
        for _ in range(b):
            term = term * eta
        polynomial = polynomial + term
    field = ngs.GridFunction(ngs.L2(mesh, order=deposit.order))
    # The polynomial lies in the space, so the element-wise projection Set makes
    # reproduces it; the bonus covers NGSolve not counting x and y as degree 1.
    field.Set(polynomial, bonus_intorder=2 * deposit.order)
    return field


@dataclass(frozen=True)
class DepositedCharge:
    """A deposited fixed charge bound to the mesh it will be assembled on (D5).

    Behind the interface the solve, the restore and the export read of a
    supplied :class:`~nanopnp.charge.fields.ChargeField`: a volume density and
    its nondimensional form. It is never an areal density, so no axis guard or
    ``1/(2 pi r)`` applies (PHY-18).
    """

    deposit: Deposit
    field: Expression

    is_areal = False

    @classmethod
    def bind(cls, deposit: Deposit, mesh: Mesh) -> DepositedCharge:
        """Return the deposit set on ``mesh``; :func:`gridfunction` says what is refused."""
        return cls(deposit=deposit, field=gridfunction(deposit, mesh))

    def volume_density_C_m3(self) -> Expression:
        """Return the volume charge density, C m^-3: the ``L2(order=k)`` field itself."""
        return self.field

    def assemble(self, scales: Scales) -> Expression:
        """Return the dimensionless ``rho~_pore`` the weak form takes (NUM-09)."""
        return self.field / scales.charge_density_C_m3
