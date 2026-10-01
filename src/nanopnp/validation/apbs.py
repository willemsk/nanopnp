"""VAL-06: our Poisson solve against APBS's, on maps of the same problem (WP29).

``SPECIFICATION.md`` section 7.4's NOTE on VAL-06 states the construction, and the
WP29 plan's *Design* section 1 to 6 argues it. APBS is handed the problem as maps on
one cubic grid, so that the two solves differ only in how they discretise it:

- **The charge** (:func:`charge_map`) is stage 7's export lattice moved onto the
  grid nodes by hat weights. They are linear in ``z``, and around each ring they
  spread ``M >= 16 * 2 pi r / h`` equal-angle samples bilinearly in ``(x, y)``. Each
  step is a partition of unity, so the map carries the lattice's charge to
  round-off and keeps its first moments. The weights are the 7-point operator's
  own test functions, so APBS receives the charge through its test space as the
  deposit gives it to ours (*Design* section 2). Point sampling would alias, as the
  consumer path does (VAL-15).
- **The dielectric** (:func:`dielectric_maps`) is the permittivity the solve
  assembled, rastered on the deployed mesh (:func:`raster_from_mesh`). Each of
  APBS's three maps is staggered by ``h/2`` along its own axis, and each edge
  takes the harmonic mean of eight samples along it, which makes the flux across
  an interface normal to the edge exact (*Design* section 3).
- **The box faces** (:func:`face_map`) take our own solution through ``bcfl map``.
  Our grounded arc and the membrane's natural edge cannot be posed in APBS, so the
  two interiors are compared (*Design* section 1).

:func:`run_apbs` writes the deck and the maps, runs the ``apbs`` binary of the
test-only ``apbs`` dependency group and reads the potential back. :func:`probe_set`
and :func:`norms` give the probes and metric, and :func:`gated_leg` puts the steps
together with the refinement budget that has to hold first.

Lengths are in nm here and in angstroms only in the files APBS reads. The
potential is in ``kT/e`` at the deck's temperature, which is the solver's
``phi~ = phi / V_T``, so the two are compared without conversion.
"""

from __future__ import annotations

import logging
import math
import platform
import re
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, ConfigDict

from nanopnp.core.constants import ELEMENTARY_CHARGE
from nanopnp.io.fields import sample_at
from nanopnp.physics.models import POTENTIAL

if TYPE_CHECKING:
    import numpy as np
    from scipy.sparse import csc_matrix, csr_matrix

    from nanopnp.core.typing import Expression, FESpace, Mesh
    from nanopnp.density.grid import RadialGrid
    from nanopnp.physics.models import ModelSolution

__all__ = [
    "APBS_GROUP",
    "REQUIRE_APBS",
    "TOLERANCE",
    "ApbsError",
    "ApbsProblem",
    "ApbsSolution",
    "BoxError",
    "CubicGrid",
    "GatedInputs",
    "GatedResult",
    "MaterialRaster",
    "Norms",
    "ProbeSet",
    "RecordedInputs",
    "RecordedReport",
    "SmolSurface",
    "Val06Error",
    "Val06Report",
    "apbs_available",
    "charge_map",
    "check_box",
    "check_report",
    "dielectric_maps",
    "face_map",
    "face_map_3d",
    "fit_grid",
    "gated_leg",
    "impose_materials",
    "lattice_charges",
    "norms",
    "potential_sampler",
    "probe_set",
    "raster_from_mesh",
    "read_dx",
    "recorded_leg",
    "ring_statistics",
    "run_apbs",
    "trilinear",
    "write_dx",
    "write_inputs",
    "write_pqr",
]

logger = logging.getLogger(__name__)

APBS_GROUP = "apbs"
"""The ``pyproject.toml`` dependency group carrying ``apbs-binary`` (WP29 D11)."""

REQUIRE_APBS = "NANOPNP_REQUIRE_APBS"
"""Set to ``1`` where APBS must run, so its tests fail rather than skip (WP29 D12)."""

NM_TO_ANGSTROM = 10.0
"""Angstroms per nanometre: APBS's decks and maps are in angstroms."""

SPACING_NM = 0.1
"""The gated leg's fine grid spacing (WP29 D3)."""

DIME = 193
"""Nodes per side of the fine grid: ``6 * 2^5 + 1``, so ``nlev`` 4 (WP29 D3)."""

NLEV = 4
"""APBS's multigrid levels; ``dime`` must be ``c * 2^(nlev + 1) + 1``."""

CHARGE_MARGIN_NM = 1.0
"""How far inside every face all of the lattice's charge must lie (WP29 D3)."""

RASTER_NM = 0.01
"""The ``(r, z)`` raster's cell size (WP29 D5; *Design* section 3)."""

EDGE_SAMPLES = 8
"""Sub-samples along each grid edge whose harmonic mean is the edge's permittivity."""

RING_OVERSAMPLING = 16
"""Azimuthal samples per grid spacing of circumference (WP29 D4)."""

MINIMUM_ANGLES = 64
"""The fewest azimuthal samples of a ring, so a ring on or near the axis is still spread."""

PROBE_STRIDE = 2
"""Probes are the nodes of the nested ``2h`` grid, which are also fine-grid nodes (D6)."""

SOLID_DISTANCE_NM = 0.3
"""How far a probe must lie from every solid (WP29 D6)."""

FACE_MARGIN_NM = 0.4
"""How far a probe must lie inside every face (WP29 D6)."""

TIMEOUT_S = 1800.0
"""The wall-clock limit of one APBS run, after which it is killed and named (WP29 D13).

About forty times the 44 s that the 193^3 run took on four cores (``.knowledge/07``
section 3), so only a hung run reaches it.
"""

VISIBILITY = 10.0
"""The charge must move the probes by at least this many ``tau_rms`` (WP29 D8)."""


class ApbsError(RuntimeError):
    """APBS is absent, refused the deck, failed, or ran past its time limit.

    The message names the run and quotes the end of APBS's log, which is where it
    says why.
    """


class BoxError(ValueError):
    """The APBS box does not hold the charge with the margin the construction needs.

    Names the face and the coordinate, so the remedy (a larger ``dime``, or a
    different centre) is evident rather than the run being silently cut (D3).
    """


class Val06Error(AssertionError):
    """VAL-06 failed: its refinement budget, its charge visibility or its agreement.

    The message names which of the three, the norm and both numbers (QR-12). The
    budget is checked before the agreement: an agreement inside an unmeasured
    error is luck (WP29 D8).
    """


def apbs_available() -> str | None:
    """Return why APBS cannot run here, or ``None`` if it can.

    The ``apbs-binary`` wheel exists for Linux x86_64 and macOS only (WP29 D11), so
    any other platform (Windows, or Linux on ARM) reports the absent wheel, and a
    covered platform without the group reports the missing group.
    """
    try:
        import apbs_binary
    except ImportError:
        covered = sys.platform == "darwin" or (
            sys.platform == "linux" and platform.machine() == "x86_64"
        )
        if not covered:
            return (
                f"apbs-binary publishes no wheel for {sys.platform} {platform.machine()}, so APBS "
                "cannot run here (WP29 D11); VAL-06 runs on Linux x86_64 and macOS"
            )
        return (
            f"apbs-binary does not import; install the {APBS_GROUP!r} dependency group "
            f"('uv sync --group {APBS_GROUP}')"
        )
    if not Path(apbs_binary.APBS_BIN_PATH).is_file():
        return f"apbs-binary is installed but {apbs_binary.APBS_BIN_PATH} is not there"
    return None


# -- the grid ------------------------------------------------------------------


@dataclass(frozen=True)
class CubicGrid:
    """APBS's grid: ``dime`` nodes per side at ``spacing_nm``, from ``origin_nm``.

    Parameters
    ----------
    origin_nm
        ``(x, y, z)`` of node ``[0, 0, 0]``, in the model frame.
    spacing_nm
        ``h``, the same along every axis.
    dime
        Nodes per side.
    """

    origin_nm: tuple[float, float, float]
    spacing_nm: float
    dime: int

    def axis(self, index: int) -> np.ndarray:
        """Return the node coordinates along axis ``index`` (0, 1, 2 for x, y, z), in nm."""
        import numpy as np

        return self.origin_nm[index] + self.spacing_nm * np.arange(self.dime, dtype=np.float64)

    @property
    def upper_nm(self) -> tuple[float, float, float]:
        """Return the coordinates of the last node, in nm."""
        span = self.spacing_nm * (self.dime - 1)
        return (self.origin_nm[0] + span, self.origin_nm[1] + span, self.origin_nm[2] + span)

    @property
    def centre_nm(self) -> tuple[float, float, float]:
        """Return the box centre, APBS's ``gcent``, in nm."""
        half = 0.5 * self.spacing_nm * (self.dime - 1)
        return (self.origin_nm[0] + half, self.origin_nm[1] + half, self.origin_nm[2] + half)

    def coarsened(self) -> CubicGrid:
        """Return the nested grid of every second node, at ``2h`` from the same origin.

        Raises
        ------
        ValueError
            If ``dime`` is even, so that the last node would not be shared.
        """
        if self.dime % 2 == 0:
            raise ValueError(f"a grid of dime {self.dime} has no nested 2h grid; dime must be odd")
        return CubicGrid(self.origin_nm, 2.0 * self.spacing_nm, (self.dime + 1) // 2)

    def nlev(self) -> int:
        """Return the largest ``nlev <= 4`` that APBS accepts for this ``dime``.

        Raises
        ------
        ValueError
            If no ``nlev`` from 1 to 4 fits ``dime = c * 2^(nlev + 1) + 1``.
        """
        for level in range(NLEV, 0, -1):
            if (self.dime - 1) % 2 ** (level + 1) == 0:
                return level
        raise ValueError(
            f"dime {self.dime} is not c * 2^(nlev + 1) + 1 for any nlev from 1 to {NLEV}; "
            "APBS's multigrid needs it (e.g. 33, 65, 97, 129, 193)"
        )

    def summary(self) -> dict[str, object]:
        """Return the grid as plain data, for a report."""
        return {
            "origin_nm": list(self.origin_nm),
            "spacing_nm": self.spacing_nm,
            "dime": self.dime,
        }


@dataclass(frozen=True)
class ChargeExtent:
    """Where a lattice's charge lies: ``r <= r_max_nm`` and ``z_min_nm <= z <= z_max_nm``."""

    r_max_nm: float
    z_min_nm: float
    z_max_nm: float


def charge_extent(lattice: RadialGrid) -> ChargeExtent:
    """Return the extent of the lattice's nonzero nodes."""
    import numpy as np

    i_z, i_r = np.nonzero(lattice.values)
    if i_z.size == 0:
        raise BoxError("the lattice carries no charge, so there is nothing to place in a box")
    return ChargeExtent(
        r_max_nm=float(lattice.r_nm[i_r].max()),
        z_min_nm=float(lattice.z_nm[i_z].min()),
        z_max_nm=float(lattice.z_nm[i_z].max()),
    )


def check_box(
    grid: CubicGrid, extent: ChargeExtent, *, margin_nm: float = CHARGE_MARGIN_NM
) -> None:
    """Refuse a box that does not hold the charge ``margin_nm`` inside every face (D3).

    The charge is a body of revolution about ``z``, so in ``x`` and ``y`` it spans
    ``+-r_max``.

    Raises
    ------
    BoxError
        Naming the first face too close to the charge, the charge's coordinate and
        the face's.
    """
    lower, upper = grid.origin_nm, grid.upper_nm
    reaches = {
        "x-": (-extent.r_max_nm, lower[0], -1.0),
        "x+": (extent.r_max_nm, upper[0], 1.0),
        "y-": (-extent.r_max_nm, lower[1], -1.0),
        "y+": (extent.r_max_nm, upper[1], 1.0),
        "z-": (extent.z_min_nm, lower[2], -1.0),
        "z+": (extent.z_max_nm, upper[2], 1.0),
    }
    for face, (charge, wall, sign) in reaches.items():
        inside = sign * (wall - charge)
        if inside < margin_nm - 1e-9:
            raise BoxError(
                f"the APBS box's {face} face at {wall:.4f} nm lies {inside:.4f} nm from the "
                f"charge at {charge:.4f} nm, under the {margin_nm} nm margin VAL-06 needs "
                "(WP29 D3); enlarge dime or move the centre rather than cut the charge"
            )


def fit_grid(
    extent: ChargeExtent,
    *,
    spacing_nm: float = SPACING_NM,
    dime: int = DIME,
    interface_z_nm: float | None = None,
    margin_nm: float = CHARGE_MARGIN_NM,
) -> CubicGrid:
    """Return the cubic grid of D3 for a charge of this extent, checked by :func:`check_box`.

    ``x`` and ``y`` are centred on the axis, which is then a node line. ``z`` is
    centred on the charge, to the nearest node position that puts
    ``interface_z_nm`` (a membrane face) midway between two fine planes, so that no
    edge parallel to the slab lies on it (*Design* section 2).

    Parameters
    ----------
    extent
        The lattice's charge extent, from :func:`charge_extent`.
    spacing_nm, dime
        The fine grid; ``dime`` odd, so the axis is a node line.
    interface_z_nm
        A plane to stagger the ``z`` nodes off, or ``None`` to centre the charge
        exactly.
    margin_nm
        Passed to :func:`check_box`.
    """
    if dime % 2 == 0:
        raise ValueError(f"dime {dime} is even, so the axis would not be a node line")
    half = 0.5 * spacing_nm * (dime - 1)
    ideal = 0.5 * (extent.z_min_nm + extent.z_max_nm) - half
    if interface_z_nm is None:
        z0 = ideal
    else:
        anchor = interface_z_nm + 0.5 * spacing_nm
        z0 = anchor + round((ideal - anchor) / spacing_nm) * spacing_nm
    grid = CubicGrid((-half, -half, z0), spacing_nm, dime)
    grid.nlev()
    check_box(grid, extent, margin_nm=margin_nm)
    return grid


# -- the charge map --------------------------------------------------------------


def lattice_charges(lattice: RadialGrid) -> np.ndarray:
    """Return each lattice node's charge ``Q_n = tau_n a_n / e``, ``[i_z, i_r]``, in e.

    ``a_n`` is the areal density ``2 pi r rho`` in C m^-2 and ``tau_n`` the
    trapezium weights in nm^2, which carry the spacings: the mass the deposit
    projects (WP28 *Design* section 2), whose sum is the lattice's planar integral.
    """
    import numpy as np

    weights = np.outer(lattice.trapezium_weights("z"), lattice.trapezium_weights("r"))
    return np.asarray(weights * 1e-18 * lattice.values / ELEMENTARY_CHARGE)


def _hat_matrix(coordinates: np.ndarray, nodes: np.ndarray) -> csr_matrix:
    """Return the sparse matrix moving each coordinate onto two neighbouring nodes, linearly.

    A weight that would land on a node outside ``nodes`` is dropped: none does for a
    coordinate inside the grid, and for a focused grid that is the clipping wanted.
    """
    import numpy as np
    from scipy.sparse import csr_matrix

    spacing = float(nodes[1] - nodes[0])
    position = (coordinates - nodes[0]) / spacing
    lower = np.floor(position).astype(np.int64)
    fraction = position - lower
    rows = np.repeat(np.arange(coordinates.size), 2)
    columns = np.stack([lower, lower + 1], axis=1).reshape(-1)
    weights = np.stack([1.0 - fraction, fraction], axis=1).reshape(-1)
    inside = (columns >= 0) & (columns < nodes.size)
    return csr_matrix(
        (weights[inside], (rows[inside], columns[inside])), shape=(coordinates.size, nodes.size)
    )


def _ring_matrix(
    radii_nm: np.ndarray,
    grid: CubicGrid,
    *,
    oversampling: int = RING_OVERSAMPLING,
    minimum_angles: int = MINIMUM_ANGLES,
) -> csc_matrix:
    """Return the sparse ``(dime^2, rings)`` matrix spreading a unit ring onto the ``(x, y)`` nodes.

    Ring ``j`` is sampled at ``M_j = max(minimum, ceil(oversampling 2 pi r_j / h))``
    angles ``(m + 1/2) 2 pi / M_j``, each carrying ``1/M_j``, spread bilinearly to
    its four ``(x, y)`` neighbours. The angles are symmetric under ``theta -> -theta``
    and ``theta -> theta + pi`` when ``M_j`` is even, which it is made, so the
    ring's ``(x, y)`` dipole vanishes (D4).
    """
    import numpy as np
    from scipy.sparse import csc_matrix

    h = grid.spacing_nm
    counts = np.maximum(minimum_angles, np.ceil(oversampling * 2.0 * math.pi * radii_nm / h))
    counts = (2 * np.ceil(counts / 2)).astype(np.int64)
    ring = np.repeat(np.arange(radii_nm.size), counts)
    starts = np.repeat(np.cumsum(counts) - counts, counts)
    sample = np.arange(ring.size) - starts
    angle = (sample + 0.5) * (2.0 * math.pi / counts[ring])
    radius = radii_nm[ring]
    weight = 1.0 / counts[ring]
    columns: list[np.ndarray] = []
    rows: list[np.ndarray] = []
    values: list[np.ndarray] = []
    position = []
    for index, trig in ((0, np.cos), (1, np.sin)):
        coordinate = (radius * trig(angle) - grid.origin_nm[index]) / h
        lower = np.floor(coordinate).astype(np.int64)
        position.append((lower, coordinate - lower))
    (ix, fx), (iy, fy) = position
    for dx, wx in ((0, 1.0 - fx), (1, fx)):
        for dy, wy in ((0, 1.0 - fy), (1, fy)):
            # A sample outside the (x, y) box is dropped, as on a focused grid.
            inside = (ix + dx >= 0) & (ix + dx < grid.dime) & (iy + dy >= 0) & (iy + dy < grid.dime)
            rows.append(((ix + dx) * grid.dime + (iy + dy))[inside])
            columns.append(ring[inside])
            values.append((weight * wx * wy)[inside])
    return csc_matrix(
        (np.concatenate(values), (np.concatenate(rows), np.concatenate(columns))),
        shape=(grid.dime * grid.dime, radii_nm.size),
    )


def charge_map(
    lattice: RadialGrid,
    grid: CubicGrid,
    *,
    oversampling: int = RING_OVERSAMPLING,
    minimum_angles: int = MINIMUM_ANGLES,
    chunk: int = 128,
    clip: bool = False,
) -> np.ndarray:
    """Return APBS's charge map of the lattice, ``[ix, iy, iz]`` in e per cubic angstrom (D4).

    Each lattice node's charge (:func:`lattice_charges`) is split between its two
    neighbouring ``z`` planes linearly, then spread around its ring by
    :func:`_ring_matrix`; the node sums are divided by ``h^3`` in cubic angstroms,
    the unit ``READ charge`` takes (``.knowledge/07`` section 3). Rings are taken
    ``chunk`` at a time, so memory stays at the map and one chunk's samples.

    ``clip`` is for a focused grid that does not hold the whole charge: the weights
    landing outside it are dropped. Each interior node still receives
    ``int rho phi_j`` over its own support, which lies inside, and the charge
    outside reaches the interior only through the face data.

    Raises
    ------
    BoxError
        Without ``clip``, if the lattice's charge does not fit the box
        (:func:`check_box` with no margin): a node outside the grid would be cut.
    """
    import numpy as np

    if not clip:
        check_box(grid, charge_extent(lattice), margin_nm=0.0)
    charges = lattice_charges(lattice)
    columns = np.flatnonzero(np.any(charges != 0.0, axis=0))
    rows = np.flatnonzero(np.any(charges != 0.0, axis=1))
    z_hats = _hat_matrix(lattice.z_nm[rows], grid.axis(2))
    # (rings, planes): each ring's charge per z plane of the APBS grid.
    per_plane = np.asarray((z_hats.T @ charges[np.ix_(rows, columns)]).T)
    radii = lattice.r_nm[columns]
    nodes = np.zeros((grid.dime * grid.dime, grid.dime), dtype=np.float64)
    for start in range(0, radii.size, chunk):
        stop = min(start + chunk, radii.size)
        spread = _ring_matrix(
            radii[start:stop], grid, oversampling=oversampling, minimum_angles=minimum_angles
        )
        nodes += spread @ per_plane[start:stop]
    volume = (grid.spacing_nm * NM_TO_ANGSTROM) ** 3
    return nodes.reshape(grid.dime, grid.dime, grid.dime) / volume


# -- the dielectric -------------------------------------------------------------


@dataclass(frozen=True)
class MaterialRaster:
    """The deployed mesh's permittivity and materials on a cell-centred ``(r, z)`` raster.

    Parameters
    ----------
    spacing_nm
        The cell size; cell ``[i_z, i_r]`` covers ``r`` from ``i_r h`` and ``z`` from
        ``z0 + i_z h``.
    z0_nm
        The lower ``z`` edge of the first row.
    permittivity
        ``[i_z, i_r]``, the relative permittivity at each cell centre.
    material
        ``[i_z, i_r]``, the index into ``materials`` at each cell centre.
    materials
        The mesh's material names.
    fluid, solids
        Which materials are the fluid and which are solid.
    """

    spacing_nm: float
    z0_nm: float
    permittivity: np.ndarray
    material: np.ndarray
    materials: tuple[str, ...]
    fluid: frozenset[str]
    solids: frozenset[str]
    # Not an init field, so ``dataclasses.replace`` starts a copy with an empty cache
    # rather than handing it the distance transform of the materials it replaced.
    _distance: list[np.ndarray] = field(default_factory=list, init=False, repr=False, compare=False)

    def r_index(self, r_nm: np.ndarray) -> np.ndarray:
        """Return the column of the cells holding radii ``r_nm``.

        Raises
        ------
        ValueError
            If a radius lies outside the raster.
        """
        import numpy as np

        index = np.floor(np.asarray(r_nm) / self.spacing_nm).astype(np.int64)
        columns = self.permittivity.shape[1]
        if index.size and (index.min() < 0 or index.max() >= columns):
            raise ValueError(
                f"a radius lies outside the raster, which covers 0 <= r < "
                f"{columns * self.spacing_nm:.3f} nm"
            )
        return index

    def z_index(self, z_nm: np.ndarray) -> np.ndarray:
        """Return the row of the cells holding heights ``z_nm``.

        Raises
        ------
        ValueError
            If a height lies outside the raster.
        """
        import numpy as np

        index = np.floor((np.asarray(z_nm) - self.z0_nm) / self.spacing_nm).astype(np.int64)
        rows = self.permittivity.shape[0]
        if index.size and (index.min() < 0 or index.max() >= rows):
            raise ValueError(
                f"a height lies outside the raster, which covers {self.z0_nm:.3f} <= z < "
                f"{self.z0_nm + rows * self.spacing_nm:.3f} nm"
            )
        return index

    def mask(self, names: frozenset[str]) -> np.ndarray:
        """Return ``[i_z, i_r]``, true where the cell's material is in ``names``."""
        import numpy as np

        selected = np.array([name in names for name in self.materials], dtype=bool)
        return np.asarray(selected[self.material])

    def solid_distance_nm(self) -> np.ndarray:
        """Return ``[i_z, i_r]``, each cell centre's distance to the nearest solid cell centre.

        The ``(r, z)`` distance is the 3D distance to a body of revolution, whose
        nearest point lies in the same meridional half-plane. Computed once.
        """
        if not self._distance:
            from scipy.ndimage import distance_transform_edt

            solid = self.mask(self.solids)
            if not solid.any():
                import numpy as np

                self._distance.append(np.full(solid.shape, np.inf))
            else:
                self._distance.append(
                    distance_transform_edt(~solid, sampling=(self.spacing_nm, self.spacing_nm))
                )
        return self._distance[0]


def raster_extent(grid: CubicGrid) -> tuple[float, float, float]:
    """Return the ``r_max``, ``z_min`` and ``z_max`` a raster must cover for ``grid``'s maps.

    Every edge sample of a staggered map lies within one spacing of the box; the
    margin is two fine spacings, so the same raster serves the nested ``2h`` grid.
    """
    reach = 2.0 * grid.spacing_nm
    x = max(abs(grid.origin_nm[0]), abs(grid.upper_nm[0])) + reach
    y = max(abs(grid.origin_nm[1]), abs(grid.upper_nm[1])) + reach
    return math.hypot(x, y), grid.origin_nm[2] - reach, grid.upper_nm[2] + reach


def raster_from_mesh(
    mesh: Mesh,
    permittivity: Expression,
    *,
    fluid: str,
    solids: Sequence[str],
    r_max_nm: float,
    z_min_nm: float,
    z_max_nm: float,
    spacing_nm: float = RASTER_NM,
) -> MaterialRaster:
    """Sample the assembled permittivity and the materials on a cell-centred raster (D5).

    Parameters
    ----------
    mesh
        The deployed mesh the solve used: its materials, not stage 5's contour,
        are the FE solve's geometry, so both solvers see the same polygonal
        interface (*Design* section 3).
    permittivity
        The *relative* permittivity ``eps_r`` the solve assembled, as
        :meth:`~nanopnp.physics.models.PoissonModel.permittivity` returns it times
        its scale.
    fluid
        The model's fluid material pattern, a regular expression.
    solids
        The solid materials, those in ``physics.solid_permittivities``.
    r_max_nm, z_min_nm, z_max_nm
        What the raster must cover, from :func:`raster_extent`.
    spacing_nm
        The cell size.

    Raises
    ------
    ValueError
        If a cell centre lies outside the mesh, where NGSolve evaluates zero.
    """
    import numpy as np

    columns = math.ceil(r_max_nm / spacing_nm)
    rows = math.ceil((z_max_nm - z_min_nm) / spacing_nm)
    r = (np.arange(columns) + 0.5) * spacing_nm
    z = z_min_nm + (np.arange(rows) + 0.5) * spacing_nm
    rr, zz = np.meshgrid(r, z)
    points = mesh(rr.reshape(-1), zz.reshape(-1))
    names = tuple(mesh.GetMaterials())
    index_cf = mesh.MaterialCF({name: float(number + 1) for number, name in enumerate(names)})
    material = np.asarray(index_cf(points)).reshape(rows, columns)
    if np.any(material < 0.5):
        where = np.argwhere(material < 0.5)[0]
        raise ValueError(
            f"the raster point (r, z) = ({r[where[1]]:.4f}, {z[where[0]]:.4f}) nm lies outside "
            "the deployed mesh, so it has no material; the APBS box must lie inside the domain"
        )
    eps = np.asarray(permittivity(points)).reshape(rows, columns)
    pattern = re.compile(fluid)
    return MaterialRaster(
        spacing_nm=spacing_nm,
        z0_nm=z_min_nm,
        permittivity=np.ascontiguousarray(eps, dtype=np.float64),
        material=np.rint(material).astype(np.int64) - 1,
        materials=names,
        fluid=frozenset(name for name in names if pattern.fullmatch(name)),
        solids=frozenset(solids) & frozenset(names),
    )


def dielectric_maps(
    raster: MaterialRaster, grid: CubicGrid, *, samples: int = EDGE_SAMPLES
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return APBS's staggered ``x``, ``y`` and ``z`` permittivity maps, ``[ix, iy, iz]`` (D5).

    Node ``(i, j, k)`` of the ``a``-map lies at the grid node plus ``h/2`` along
    ``a``, as APBS reads it (``.knowledge/07`` section 3). Its value is the
    harmonic mean ``samples / sum_s 1/eps(x + u_s e_a)`` over the edge from node
    ``(i, j, k)`` to its neighbour along ``a``, ``u_s = (s + 1/2) h / samples``,
    read from the raster's nearest cell. The harmonic mean makes the flux across an
    interface normal to the edge exact; on the dielectric sphere it halves point
    sampling's error (*Design* section 3).
    """
    import numpy as np

    h = grid.spacing_nm
    x, y, z = grid.axis(0), grid.axis(1), grid.axis(2)
    offsets = (np.arange(samples) + 0.5) * h / samples
    inverse = 1.0 / raster.permittivity
    maps: list[np.ndarray] = []
    for along in (0, 1):
        moved = (x[:, None, None] + offsets[None, None, :]) if along == 0 else x[:, None, None]
        across = y[None, :, None] if along == 0 else (y[None, :, None] + offsets[None, None, :])
        radius = np.sqrt(moved**2 + across**2)
        radius = np.broadcast_to(radius, (grid.dime, grid.dime, samples))
        i_r = raster.r_index(radius)
        i_z = raster.z_index(z)
        values = np.empty((grid.dime, grid.dime, grid.dime), dtype=np.float64)
        for k, row in enumerate(i_z):
            values[:, :, k] = samples / inverse[row][i_r].sum(axis=-1)
        maps.append(values)
    radius = np.hypot(x[:, None], y[None, :])
    i_r = raster.r_index(radius)
    i_z = raster.z_index((z[:, None] + offsets[None, :]).reshape(-1))
    i_z = i_z.reshape(grid.dime, samples)
    values = np.empty((grid.dime, grid.dime, grid.dime), dtype=np.float64)
    for k in range(grid.dime):
        values[:, :, k] = samples / inverse[i_z[k]][:, i_r].sum(axis=0)
    maps.append(values)
    return maps[0], maps[1], maps[2]


# -- the face data ---------------------------------------------------------------


def _face_nodes(grid: CubicGrid) -> np.ndarray:
    """Return the ``(n, 3)`` indices of the nodes on the box's six faces."""
    import numpy as np

    last = grid.dime - 1
    index = np.indices((grid.dime,) * 3).reshape(3, -1).T
    on_face = np.any((index == 0) | (index == last), axis=1)
    return np.asarray(index[on_face])


def unique_meridional(points_nm: np.ndarray, *, decimals: int = 9) -> tuple[np.ndarray, np.ndarray]:
    """Return the distinct ``(r, z)`` of ``(n, 3)`` points, and the map back to each point.

    A box's nodes repeat each ``(r, z)`` many times by symmetry; sampling an
    axisymmetric field once per distinct pair is what keeps the probe and face
    evaluations cheap.
    """
    import numpy as np

    meridional = np.stack(
        [np.hypot(points_nm[:, 0], points_nm[:, 1]), points_nm[:, 2]], axis=1
    ).round(decimals)
    unique, inverse = np.unique(meridional, axis=0, return_inverse=True)
    return unique, inverse.reshape(-1)


Sampler = Callable[["np.ndarray", "np.ndarray"], "np.ndarray"]
"""A potential in ``kT/e`` at arrays of ``r`` and ``z`` in nm: ours, or a closed form."""


def potential_sampler(solution: ModelSolution, *, order: int) -> Sampler:
    """Return our solution's potential as a :data:`Sampler`, read through ``sample_at`` (D6).

    The one way a VAL-06 test reads our side: through a whole-domain carrier of
    ``order`` (:func:`~nanopnp.io.fields.sample_at`), which is right on an interface
    node where evaluating a restricted space directly is not. The carriers are
    built once and reused by every call.
    """
    import numpy as np

    mesh = solution.space.mesh
    field = solution.component(POTENTIAL)
    carriers: dict[tuple[int, int], FESpace] = {}

    def sample(r_nm: np.ndarray, z_nm: np.ndarray) -> np.ndarray:
        points = np.stack([np.asarray(r_nm), np.asarray(z_nm)], axis=1)
        return np.asarray(sample_at(mesh, field, points, order=order, carriers=carriers)[:, 0])

    return sample


def face_map(grid: CubicGrid, potential: Sampler) -> np.ndarray:
    """Return a potential map, ``[ix, iy, iz]`` in ``kT/e``, carrying ``potential`` on the faces.

    ``bcfl map`` reads only the face values (``.knowledge/07`` section 3), so the
    interior is left at zero rather than sampled (D2). An axisymmetric potential is
    evaluated once per distinct ``(r, z)``.
    """
    import numpy as np

    def at_points(points: np.ndarray) -> np.ndarray:
        meridional, inverse = unique_meridional(points)
        values = np.asarray(potential(meridional[:, 0], meridional[:, 1]), dtype=np.float64)
        return np.asarray(values.reshape(-1)[inverse])

    return face_map_3d(grid, at_points)


def face_map_3d(grid: CubicGrid, potential: Callable[[np.ndarray], np.ndarray]) -> np.ndarray:
    """Return a potential map carrying ``potential``, a function of ``(n, 3)`` points, on the faces.

    For focusing from a coarser APBS solution, which is not axisymmetric.
    """
    import numpy as np

    index = _face_nodes(grid)
    points = np.asarray(grid.origin_nm) + grid.spacing_nm * index
    result = np.zeros((grid.dime,) * 3, dtype=np.float64)
    result[index[:, 0], index[:, 1], index[:, 2]] = np.asarray(potential(points)).reshape(-1)
    return result


def trilinear(values: np.ndarray, grid: CubicGrid) -> Callable[[np.ndarray], np.ndarray]:
    """Return ``values[ix, iy, iz]`` on ``grid`` as a trilinear function of ``(n, 3)`` points in nm.

    APBS's own interpolation of a map between nodes. A point outside the grid is
    refused rather than extrapolated.
    """
    import numpy as np
    from scipy.ndimage import map_coordinates

    def sample(points_nm: np.ndarray) -> np.ndarray:
        index = (np.asarray(points_nm) - np.asarray(grid.origin_nm)) / grid.spacing_nm
        if np.any(index < -1e-9) or np.any(index > grid.dime - 1 + 1e-9):
            raise ValueError("a point lies outside the grid it is to be interpolated on")
        return np.asarray(map_coordinates(values, index.T, order=1, mode="nearest"))

    return sample


# -- files -------------------------------------------------------------------------


def write_dx(path: Path, values: np.ndarray, origin_nm: Sequence[float], spacing_nm: float) -> Path:
    """Write ``values[ix, iy, iz]`` as an OpenDX scalar map in angstroms, as APBS reads it.

    Three values per line at ``%.10e``, ``z`` fastest. Formatted in one ``%`` over
    the whole array: GridDataFormats' writer formats each of the ~7 M values of a
    193^3 map in a Python loop (D13).
    """
    import numpy as np

    counts = " ".join(str(n) for n in values.shape)
    origin = " ".join(f"{value * NM_TO_ANGSTROM:.10e}" for value in origin_nm)
    step = spacing_nm * NM_TO_ANGSTROM
    flat = np.ascontiguousarray(values, dtype=np.float64).reshape(-1)
    whole = flat.size - flat.size % 3
    lines = [
        f"object 1 class gridpositions counts {counts}",
        f"origin {origin}",
        f"delta {step:.10e} 0.0 0.0",
        f"delta 0.0 {step:.10e} 0.0",
        f"delta 0.0 0.0 {step:.10e}",
        f"object 2 class gridconnections counts {counts}",
        f"object 3 class array type double rank 0 items {flat.size} data follows",
    ]
    body = ("%.10e %.10e %.10e\n" * (whole // 3)) % tuple(flat[:whole].tolist())
    rest = " ".join(f"{value:.10e}" for value in flat[whole:].tolist())
    tail = [
        'attribute "dep" string "positions"',
        'object "regular positions regular connections" class field',
        'component "positions" value 1',
        'component "connections" value 2',
        'component "data" value 3',
    ]
    text = "\n".join(lines) + "\n" + body + (rest + "\n" if rest else "") + "\n".join(tail) + "\n"
    path.write_text(text, encoding="ascii")
    return path


def read_dx(path: Path) -> tuple[np.ndarray, tuple[float, float, float], float]:
    """Return an OpenDX map's values ``[ix, iy, iz]``, origin in nm and spacing in nm.

    Read through GridDataFormats (D13), whose reader takes APBS's output as is.

    Raises
    ------
    ApbsError
        If GridDataFormats, which is behind the ``structure`` extra, is not installed.
    ValueError
        If the map's spacing is not the same along the three axes.
    """
    import numpy as np

    try:
        from gridData import Grid
    except ImportError as error:
        raise ApbsError(
            f"reading the OpenDX map {path} needs GridDataFormats, which is behind the "
            "'structure' extra: install it with `uv sync --all-extras`"
        ) from error

    grid = Grid(str(path))
    delta = np.asarray(grid.delta, dtype=np.float64)
    if not np.allclose(delta, delta[0], rtol=1e-9):
        raise ValueError(f"{path} has spacings {delta} Å; a VAL-06 map is cubic")
    origin = tuple(float(value) / NM_TO_ANGSTROM for value in grid.origin)
    return (
        np.asarray(grid.grid, dtype=np.float64),
        (origin[0], origin[1], origin[2]),
        float(delta[0]) / NM_TO_ANGSTROM,
    )


def write_pqr(
    path: Path, positions_nm: np.ndarray, charges_e: np.ndarray, radii_nm: np.ndarray
) -> Path:
    """Write atoms as a whitespace-delimited PQR in angstroms, as APBS reads it.

    APBS splits a PQR line on whitespace, so no column alignment is needed.
    """
    import numpy as np

    xyz = np.asarray(positions_nm, dtype=np.float64).reshape(-1, 3) * NM_TO_ANGSTROM
    radii = np.asarray(radii_nm, dtype=np.float64).reshape(-1) * NM_TO_ANGSTROM
    charges = np.asarray(charges_e, dtype=np.float64).reshape(-1)
    lines = [
        f"ATOM {n + 1:7d} X    DUM {n + 1:5d} {x:.4f} {y:.4f} {z:.4f} {q:.6f} {r:.4f}"
        for n, ((x, y, z), q, r) in enumerate(zip(xyz, charges, radii, strict=True))
    ]
    path.write_text("\n".join([*lines, "END"]) + "\n", encoding="ascii")
    return path


# -- running APBS --------------------------------------------------------------------


@dataclass(frozen=True)
class SmolSurface:
    """APBS's own charge and surface from a PQR: the recorded leg's inputs (D9)."""

    pqr: Path
    pdie: float
    srad_nm: float = 0.14
    swin_nm: float = 0.03
    sdens: float = 10.0


@dataclass(frozen=True)
class ApbsProblem:
    """One APBS solve: the grid, the maps and the deck settings.

    Parameters
    ----------
    grid
        The grid the maps are on and the solve uses.
    temperature_K
        The deck's ``temp``, the case's temperature.
    sdie
        The solvent permittivity named in the deck. With dielectric maps it is
        read only for bookkeeping; with a surface it is the solvent's value.
    charge
        The charge map in e per cubic angstrom, or ``None`` to take the charge
        from ``surface``'s PQR with ``chgm spl4``.
    dielectric
        The three staggered maps, or ``None`` to build them from ``surface``.
    faces
        The potential map whose faces ``bcfl map`` reads, or ``None`` for ``bcfl
        zero``.
    surface
        The PQR and surface settings of the recorded leg, or ``None``.
    write_dielectric
        Also write APBS's own dielectric maps (pass 1 of the recorded leg).
    """

    grid: CubicGrid
    temperature_K: float
    sdie: float
    charge: np.ndarray | None = None
    dielectric: tuple[np.ndarray, np.ndarray, np.ndarray] | None = None
    faces: np.ndarray | None = None
    surface: SmolSurface | None = None
    write_dielectric: bool = False


@dataclass(frozen=True)
class ApbsSolution:
    """APBS's potential and what the run cost."""

    potential: np.ndarray
    """``[ix, iy, iz]`` in ``kT/e``, on the problem's grid."""
    seconds: float
    memory_GB: float | None
    """APBS's own high-water allocation, from its log."""
    log: Path
    dielectric: tuple[np.ndarray, np.ndarray, np.ndarray] | None = None
    """APBS's own staggered maps, when the problem asked for them."""


DUMMY_POSITION_NM = 1000.0
"""Where the deck's placeholder atom sits: far outside any box (APBS refuses no ``mol``)."""


def _deck(problem: ApbsProblem, molecule: str) -> str:
    """Return ``problem``'s input deck, naming its maps as :func:`run_apbs` writes them."""
    grid = problem.grid
    read = [f"    mol pqr {molecule}"]
    keywords = []
    if problem.charge is not None:
        read.append("    charge dx charge.dx")
        keywords += ["chgm spl2", "usemap charge 1"]
    else:
        keywords.append("chgm spl4")
    if problem.dielectric is not None:
        read.append("    diel dx dielx.dx diely.dx dielz.dx")
        keywords.append("usemap diel 1")
    if problem.faces is not None:
        read.append("    pot dx faces.dx")
        keywords += ["bcfl map", "usemap pot 1"]
    else:
        keywords.append("bcfl zero")
    # Without a surface every input is a map, and the surface keywords take
    # SmolSurface's own defaults, with the solvent's value as pdie.
    surface = problem.surface or SmolSurface(pqr=Path(molecule), pdie=problem.sdie)
    pdie, srad, swin, sdens = surface.pdie, surface.srad_nm, surface.swin_nm, surface.sdens
    h = grid.spacing_nm * NM_TO_ANGSTROM
    centre = " ".join(f"{value * NM_TO_ANGSTROM:.10f}" for value in grid.centre_nm)
    writes = ["write pot dx potential"]
    if problem.write_dielectric:
        writes += [
            "write dielx dx apbs_dielx",
            "write diely dx apbs_diely",
            "write dielz dx apbs_dielz",
        ]
    body = [
        "mg-manual",
        f"dime {grid.dime} {grid.dime} {grid.dime}",
        f"nlev {grid.nlev()}",
        f"grid {h:.10f} {h:.10f} {h:.10f}",
        f"gcent {centre}",
        "mol 1",
        "lpbe",
        *keywords,
        f"pdie {pdie:.6f}",
        f"sdie {problem.sdie:.6f}",
        "srfm smol",
        f"srad {srad * NM_TO_ANGSTROM:.6f}",
        f"swin {swin * NM_TO_ANGSTROM:.6f}",
        f"sdens {sdens:.6f}",
        f"temp {problem.temperature_K:.6f}",
        "calcenergy no",
        "calcforce no",
        *writes,
    ]
    return "\n".join(
        [
            "read",
            *read,
            "end",
            "elec name val06",
            *(f"    {line}" for line in body),
            "end",
            "quit",
            "",
        ]
    )


HIGH_WATER = re.compile(r"Final memory usage:.*?([0-9.]+) MB high water")
"""APBS's own report of its peak allocation, the last line of a finished run's log.

Read from the log rather than from the child's ``ru_maxrss``: on Linux that is a
high-water mark kept across ``execve``, so it includes the pages of the Python
process that forked it, 1.4 GB under pytest against APBS's own 0.24 GB at 97^3.
"""


def _high_water_GB(log: Path) -> float | None:
    """Return APBS's high-water memory from its log, in GB, or ``None`` if it reports none."""
    found = HIGH_WATER.findall(log.read_text(encoding="utf-8", errors="replace"))
    return float(found[-1]) / 1000.0 if found else None


def _wait(process: subprocess.Popen[str], *, timeout_s: float, name: str, log: Path) -> int:
    """Wait for ``process`` and return its exit code, killing it at the time limit."""
    try:
        return process.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
    raise ApbsError(
        f"APBS run {name!r} ran past its {timeout_s:.0f} s limit and was killed; its log is {log}"
    )


def write_inputs(problem: ApbsProblem, directory: Path) -> Path:
    """Write ``problem``'s maps, molecule and deck into ``directory``; return the deck.

    The charge and potential maps take the grid's origin, and each dielectric map
    the origin plus ``h/2`` along its own axis, where APBS samples it
    (``.knowledge/07`` section 3). Without a surface the molecule is a one-atom,
    zero-charge placeholder far outside the box, because APBS refuses a deck with
    no ``mol`` even when every input is a map.
    """
    import numpy as np

    directory.mkdir(parents=True, exist_ok=True)
    grid = problem.grid
    origin = grid.origin_nm
    if problem.charge is not None:
        write_dx(directory / "charge.dx", problem.charge, origin, grid.spacing_nm)
    if problem.dielectric is not None:
        for along, values in zip("xyz", problem.dielectric, strict=True):
            staggered = list(origin)
            staggered["xyz".index(along)] += 0.5 * grid.spacing_nm
            write_dx(directory / f"diel{along}.dx", values, staggered, grid.spacing_nm)
    if problem.faces is not None:
        write_dx(directory / "faces.dx", problem.faces, origin, grid.spacing_nm)
    if problem.surface is not None:
        molecule = str(problem.surface.pqr.resolve())
    else:
        placeholder = np.full((1, 3), DUMMY_POSITION_NM)
        molecule = write_pqr(
            directory / "placeholder.pqr", placeholder, np.zeros(1), np.full(1, 0.1)
        ).name
    deck = directory / "apbs.in"
    deck.write_text(_deck(problem, molecule), encoding="ascii")
    return deck


def run_apbs(
    problem: ApbsProblem,
    workspace: Path,
    *,
    name: str = "apbs",
    timeout_s: float = TIMEOUT_S,
    keep_maps: bool = False,
) -> ApbsSolution:
    """Write ``problem``'s maps and deck into ``workspace/name``, run APBS and read the potential.

    The maps are deleted once read, about 0.6 GB of text at 193^3, unless
    ``keep_maps``; the deck and APBS's log stay beside where they were.

    Raises
    ------
    ApbsError
        If APBS is not available, exits nonzero, writes no potential, or runs past
        ``timeout_s``. The message names the run and quotes the end of its log.
    ValueError
        If the potential APBS wrote is not on the problem's grid.
    """
    import numpy as np

    missing = apbs_available()
    if missing is not None:
        raise ApbsError(f"APBS run {name!r} cannot start: {missing}")
    import apbs_binary

    grid = problem.grid
    origin = grid.origin_nm
    deck = write_inputs(problem, workspace / name)
    directory = deck.parent
    log = directory / "apbs.log"
    output = directory / "potential.dx"
    # A map an earlier run left here (kept, or abandoned by a failure) must not be
    # read back as this run's: the check below is for the file APBS writes now.
    for stale in (output, *(directory / f"apbs_diel{axis}.dx" for axis in "xyz")):
        stale.unlink(missing_ok=True)
    started = time.perf_counter()
    with log.open("w", encoding="utf-8") as stream:
        process = apbs_binary.popen_apbs(
            [deck.name], cwd=directory, stdout=stream, stderr=stream, text=True
        )
        code = _wait(process, timeout_s=timeout_s, name=name, log=log)
    seconds = time.perf_counter() - started
    if code != 0 or not output.is_file():
        tail = "\n".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-20:])
        raise ApbsError(
            f"APBS run {name!r} exited with {code} and "
            f"{'wrote' if output.is_file() else 'wrote no'} potential; the end of {log}:\n{tail}"
        )
    potential, found_origin, spacing = read_dx(output)
    # APBS writes the header's origin and delta at %12.6e, seven significant
    # figures, so a grid whose numbers carry more is read back rounded to 5e-7
    # relative (`.knowledge/07` section 3); a shift that matters is a fraction of h.
    if (
        potential.shape != (grid.dime,) * 3
        or not np.allclose(found_origin, origin, rtol=1e-6, atol=1e-4 * grid.spacing_nm)
        or not math.isclose(spacing, grid.spacing_nm, rel_tol=1e-6)
    ):
        raise ValueError(
            f"APBS run {name!r} wrote a {potential.shape} map from {found_origin} nm at "
            f"{spacing} nm, not the problem's {grid.dime}^3 from {origin} at {grid.spacing_nm}"
        )
    dielectric: tuple[np.ndarray, np.ndarray, np.ndarray] | None = None
    if problem.write_dielectric:
        x, y, z = (read_dx(directory / f"apbs_diel{axis}.dx")[0] for axis in "xyz")
        dielectric = (x, y, z)
    memory = _high_water_GB(log)
    if not keep_maps:
        for map_file in directory.glob("*.dx"):
            map_file.unlink()
    logger.info(
        "APBS run %r on %d^3 at %.3f nm: %.1f s, high water %s GB",
        name,
        grid.dime,
        grid.spacing_nm,
        seconds,
        f"{memory:.2f}" if memory is not None else "n/a",
    )
    return ApbsSolution(
        potential=potential, seconds=seconds, memory_GB=memory, log=log, dielectric=dielectric
    )


# -- probes and the metric -------------------------------------------------------------


@dataclass(frozen=True)
class ProbeSet:
    """The probes of D6: nodes of the nested ``2h`` grid in the fluid, away from solids and faces.

    Parameters
    ----------
    fine
        ``(n, 3)`` indices into the fine grid.
    coarse
        ``(n, 3)`` indices into the nested ``2h`` grid: ``fine / 2``.
    points_nm
        ``(n, 3)`` coordinates.
    axis
        ``(n,)``, true for the probes on ``r = 0``.
    """

    fine: np.ndarray
    coarse: np.ndarray
    points_nm: np.ndarray
    axis: np.ndarray

    @property
    def count(self) -> int:
        """Return the number of probes."""
        return int(self.fine.shape[0])

    def sample(self, potential: Sampler) -> np.ndarray:
        """Return ``potential`` at every probe, evaluated once per distinct ``(r, z)``."""
        import numpy as np

        meridional, inverse = unique_meridional(self.points_nm)
        values = np.asarray(potential(meridional[:, 0], meridional[:, 1]), dtype=np.float64)
        return np.asarray(values.reshape(-1)[inverse])

    def subset(self, keep: np.ndarray) -> ProbeSet:
        """Return the probes where ``keep`` is true."""
        return ProbeSet(
            fine=self.fine[keep],
            coarse=self.coarse[keep],
            points_nm=self.points_nm[keep],
            axis=self.axis[keep],
        )

    def at(self, values: np.ndarray, *, coarse: bool = False) -> np.ndarray:
        """Return a map ``[ix, iy, iz]`` at the probes, on the fine grid or the nested one."""
        import numpy as np

        index = self.coarse if coarse else self.fine
        return np.asarray(values[index[:, 0], index[:, 1], index[:, 2]])


def probe_set(
    grid: CubicGrid,
    raster: MaterialRaster,
    *,
    stride: int = PROBE_STRIDE,
    solid_distance_nm: float = SOLID_DISTANCE_NM,
    face_margin_nm: float = FACE_MARGIN_NM,
) -> ProbeSet:
    """Return D6's probes on ``grid``: every ``stride``-th node in a fluid material.

    A probe lies at least ``solid_distance_nm`` from every solid, by an ``(r, z)``
    distance transform of the raster, and at least ``face_margin_nm`` inside every
    face. The probes on ``r = 0`` are a named subset.

    ``stride`` is even, so that every probe is also a node of the nested ``2h``
    grid (:meth:`CubicGrid.coarsened`) that ``ProbeSet.coarse`` indexes.

    Raises
    ------
    ValueError
        If ``stride`` is not a positive even number, or if no node qualifies.
    """
    import numpy as np

    if stride <= 0 or stride % 2:
        raise ValueError(
            f"a probe stride of {stride} does not land every probe on the nested 2h grid; "
            "it must be a positive even number"
        )
    index = np.indices(((grid.dime - 1) // stride + 1,) * 3).reshape(3, -1).T * stride
    points = np.asarray(grid.origin_nm) + grid.spacing_nm * index
    lower = np.asarray(grid.origin_nm) + face_margin_nm
    upper = np.asarray(grid.upper_nm) - face_margin_nm
    inside = np.all((points >= lower - 1e-9) & (points <= upper + 1e-9), axis=1)
    index, points = index[inside], points[inside]
    r = np.hypot(points[:, 0], points[:, 1])
    i_z, i_r = raster.z_index(points[:, 2]), raster.r_index(r)
    fluid = raster.mask(raster.fluid)[i_z, i_r]
    clear = raster.solid_distance_nm()[i_z, i_r] >= solid_distance_nm
    keep = fluid & clear
    if not keep.any():
        raise ValueError("no node of the nested grid lies in the fluid clear of every solid")
    index, points, r = index[keep], points[keep], r[keep]
    return ProbeSet(
        fine=index,
        coarse=index // 2,
        points_nm=points,
        axis=r <= 1e-9,
    )


class Norms(BaseModel):
    """D6's three relative norms of a difference against a reference potential."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    max: float
    """``max |difference| / max |reference|`` over the probes."""
    rms: float
    """``rms difference / rms reference`` over the probes."""
    axis: float
    """``max`` over the probes on ``r = 0``."""

    def __add__(self, other: Norms) -> Norms:
        """Return the sum, norm by norm: the budget adds the two solvers' estimates."""
        return Norms(
            max=self.max + other.max, rms=self.rms + other.rms, axis=self.axis + other.axis
        )

    def scaled(self, factor: float) -> Norms:
        """Return every norm times ``factor``."""
        return Norms(max=self.max * factor, rms=self.rms * factor, axis=self.axis * factor)

    def exceeding(self, limit: Norms) -> list[str]:
        """Return the names of the norms above ``limit``'s, in the order max, rms, axis.

        A norm that is not a number exceeds every limit: NaN compares false, and a
        gate that read ``NaN > limit`` as a pass would report one it cannot defend.
        """
        return [
            name
            for name in ("max", "rms", "axis")
            if not getattr(self, name) <= getattr(limit, name)
        ]


TOLERANCE = Norms(max=0.03, rms=0.01, axis=0.015)
"""VAL-06's tolerance: 3 % max, 1 % rms and 1.5 % on the axis.

``SPECIFICATION.md`` section 7.4, the VAL-06 row and its NOTE; ruled by the author on
1 October 2026 on the WP29 plan's *Design* section 4.
"""


def norms(difference: np.ndarray, reference: np.ndarray, axis: np.ndarray) -> Norms:
    """Return D6's norms of ``difference`` relative to ``reference`` at the same probes.

    Raises
    ------
    ValueError
        If no probe lies on the axis, if either array is not finite, or if the
        reference is zero over the probes or the axis, so no norm relative to it exists.
    """
    import numpy as np

    if not (np.all(np.isfinite(difference)) and np.all(np.isfinite(reference))):
        raise ValueError("a potential at a probe is not finite")
    if not np.any(axis):
        raise ValueError("no probe lies on the axis, so e_axis has nothing to measure")
    if not (np.any(reference != 0.0) and np.any(reference[axis] != 0.0)):
        raise ValueError(
            "the reference potential is zero over every probe or every axis probe, so a norm "
            "relative to it is undefined"
        )
    return Norms(
        max=float(np.max(np.abs(difference)) / np.max(np.abs(reference))),
        rms=float(np.sqrt(np.mean(difference**2)) / np.sqrt(np.mean(reference**2))),
        axis=float(np.max(np.abs(difference[axis])) / np.max(np.abs(reference[axis]))),
    )


# -- the gated leg ------------------------------------------------------------------------


class Val06Report(BaseModel):
    """One VAL-06 comparison, written as JSON beside the run (D13).

    The budget and the visibility are measured before the agreement, and
    :func:`check_report` reads them in that order.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    leg: Literal["gated", "recorded"]
    structure: str
    temperature_K: float
    grid: dict[str, object]
    coarse_grid: dict[str, object]
    probes: int
    axis_probes: int
    potential_scale: dict[str, float]
    """``max |phi|`` and ``rms phi`` of ours over the probes, in ``kT/e``."""
    apbs_refinement: Norms
    """``e^_A``: APBS at ``h`` against ``2h``, relative to ours (D8)."""
    ours_refinement: Norms | None
    """``e^_F``: ours at the higher order against the lower, relative to ours (D8)."""
    budget: Norms | None
    """``e^_A + e^_F``, which must lie within half of :data:`TOLERANCE`."""
    charge_visibility: float
    """``rms(phi_A(2h) - phi_A(2h, no charge)) / rms phi``, which must reach 10 ``tau_rms``."""
    agreement: Norms
    """APBS at ``h`` against ours."""
    tolerance: Norms
    seconds: dict[str, float]
    memory_GB: dict[str, float | None]
    """APBS's own high-water allocation per run, from its log, in GB; a caller may add its own."""
    mesh: dict[str, object] = {}
    """The deployed mesh's element count, hash and the solve's orders, when known."""
    stabilisation: str = "none"
    """The solve's stabilisation mode: ``poisson`` assembles none."""


def check_report(report: Val06Report, *, tolerance: Norms = TOLERANCE) -> None:
    """Raise if VAL-06 fails: the budget first, then the visibility, then the agreement.

    Raises
    ------
    Val06Error
        Naming the failing check, the norm and both numbers.
    """
    half = tolerance.scaled(0.5)
    if report.budget is None:
        raise Val06Error("VAL-06 needs the refinement budget, and this report carries none")
    over = report.budget.exceeding(half)
    if over:
        name = over[0]
        raise Val06Error(
            f"VAL-06's refinement budget fails in the {name} norm: e^_A + e^_F = "
            f"{getattr(report.budget, name):.4%} (APBS {getattr(report.apbs_refinement, name):.4%}"
            f", ours {getattr(report.ours_refinement, name, float('nan')):.4%}) against half the "
            f"tolerance, {getattr(half, name):.4%}. The remedy is a finer APBS grid, never a "
            "wider tolerance (section 7.4 NOTE on VAL-06)"
        )
    floor = VISIBILITY * tolerance.rms
    # Written so that a visibility that is not a number fails, as Norms.exceeding does.
    if not report.charge_visibility >= floor:
        raise Val06Error(
            f"VAL-06's charge moves the probes by {report.charge_visibility:.4%} rms, under "
            f"{VISIBILITY:g} tau_rms = {floor:.2%}: the box faces, not the charge, carry the "
            "comparison (WP29 D8)"
        )
    over = report.agreement.exceeding(tolerance)
    if over:
        name = over[0]
        raise Val06Error(
            f"VAL-06's agreement fails in the {name} norm: APBS against ours "
            f"{getattr(report.agreement, name):.4%} against the tolerance "
            f"{getattr(tolerance, name):.4%}, with the refinement budget at "
            f"{getattr(report.budget, name):.4%}"
        )


@dataclass(frozen=True)
class GatedInputs:
    """What the gated leg needs from our side.

    Parameters
    ----------
    lattice
        Stage 7's export lattice, the areal density in the model frame.
    raster
        The permittivity and materials of the solve, from :func:`raster_from_mesh`
        over :func:`raster_extent` of the fine grid.
    ours
        Our solution in ``kT/e``, which also supplies the face data.
    refined
        Our solution at the higher order, for ``e^_F``; ``None`` to leave the
        budget unmeasured, which :func:`check_report` refuses.
    temperature_K
        The case's temperature.
    sdie
        The fluid's relative permittivity, ``eps_r,f^0``.
    structure
        A name for the report.
    """

    lattice: RadialGrid
    raster: MaterialRaster
    ours: Sampler
    refined: Sampler | None
    temperature_K: float
    sdie: float
    structure: str
    mesh: Mapping[str, object] = field(default_factory=dict)


def gated_problem(inputs: GatedInputs, grid: CubicGrid) -> ApbsProblem:
    """Return the gated leg's APBS problem on ``grid``: the charge, dielectric and face maps."""
    return ApbsProblem(
        grid=grid,
        temperature_K=inputs.temperature_K,
        sdie=inputs.sdie,
        charge=charge_map(inputs.lattice, grid),
        dielectric=dielectric_maps(inputs.raster, grid),
        faces=face_map(grid, inputs.ours),
    )


@dataclass(frozen=True)
class GatedResult:
    """What :func:`gated_leg` measured.

    Parameters
    ----------
    report
        The record; :func:`check_report` is the gate.
    probes
        The probes.
    sampled
        The potentials at the probes, in ``kT/e``: ``ours``, ``refined``, ``apbs``,
        ``apbs_coarse`` and ``apbs_uncharged``.
    potential
        APBS's potential on the fine grid, ``[ix, iy, iz]``, for a focused check.
    """

    report: Val06Report
    probes: ProbeSet
    sampled: dict[str, np.ndarray]
    potential: np.ndarray


def gated_leg(
    inputs: GatedInputs,
    grid: CubicGrid,
    workspace: Path,
    *,
    timeout_s: float = TIMEOUT_S,
) -> GatedResult:
    """Run VAL-06's gated leg on ``grid`` and its nested ``2h`` grid (D2 to D8).

    Three APBS solves: ``h``, ``2h``, and ``2h`` with the charge zeroed. Then the
    probes, the budget ``e^_A + e^_F``, the charge visibility and the agreement,
    each relative to our solution at the probes.

    The box and the probes are checked before any APBS run, so a grid that holds the
    charge less than D3's margin inside a face, or a raster with no probe in it, is
    refused before the solves rather than after them.

    Raises
    ------
    BoxError
        If ``grid`` does not hold the lattice's charge ``CHARGE_MARGIN_NM`` inside
        every face (D3), whether or not :func:`fit_grid` made it.
    """
    import numpy as np

    check_box(grid, charge_extent(inputs.lattice))
    seconds: dict[str, float] = {}
    memory: dict[str, float | None] = {}
    coarse = grid.coarsened()

    started = time.perf_counter()
    probes = probe_set(grid, inputs.raster)
    probe_seconds = time.perf_counter() - started

    started = time.perf_counter()
    fine_problem = gated_problem(inputs, grid)
    coarse_problem = gated_problem(inputs, coarse)
    seconds["maps"] = time.perf_counter() - started

    solutions = {}
    for name, problem in (
        ("apbs", fine_problem),
        ("apbs_coarse", coarse_problem),
        ("apbs_uncharged", replace(coarse_problem, charge=np.zeros_like(coarse_problem.charge))),
    ):
        solved = run_apbs(problem, workspace, name=name, timeout_s=timeout_s)
        solutions[name] = solved
        seconds[name] = solved.seconds
        memory[name] = solved.memory_GB

    started = time.perf_counter()
    sampled = {
        "ours": probes.sample(inputs.ours),
        "apbs": probes.at(solutions["apbs"].potential),
        "apbs_coarse": probes.at(solutions["apbs_coarse"].potential, coarse=True),
        "apbs_uncharged": probes.at(solutions["apbs_uncharged"].potential, coarse=True),
    }
    if inputs.refined is not None:
        sampled["refined"] = probes.sample(inputs.refined)
    seconds["probes"] = probe_seconds + time.perf_counter() - started

    ours = sampled["ours"]
    apbs_refinement = norms(sampled["apbs"] - sampled["apbs_coarse"], ours, probes.axis)
    ours_refinement = (
        norms(sampled["refined"] - ours, ours, probes.axis) if "refined" in sampled else None
    )
    visibility = float(
        np.sqrt(np.mean((sampled["apbs_coarse"] - sampled["apbs_uncharged"]) ** 2))
        / np.sqrt(np.mean(ours**2))
    )
    report = Val06Report(
        leg="gated",
        structure=inputs.structure,
        temperature_K=inputs.temperature_K,
        grid=grid.summary(),
        coarse_grid=coarse.summary(),
        probes=probes.count,
        axis_probes=int(np.count_nonzero(probes.axis)),
        potential_scale={
            "max_kT_e": float(np.max(np.abs(ours))),
            "rms_kT_e": float(np.sqrt(np.mean(ours**2))),
        },
        apbs_refinement=apbs_refinement,
        ours_refinement=ours_refinement,
        budget=apbs_refinement + ours_refinement if ours_refinement is not None else None,
        charge_visibility=visibility,
        agreement=norms(sampled["apbs"] - ours, ours, probes.axis),
        tolerance=TOLERANCE,
        seconds=seconds,
        memory_GB=memory,
        mesh=dict(inputs.mesh),
    )
    return GatedResult(
        report=report, probes=probes, sampled=sampled, potential=solutions["apbs"].potential
    )


# -- the recorded leg ---------------------------------------------------------------------

RING_ANGLES = 24
"""Azimuthal samples per probe ring on the recorded leg (WP29 D9)."""


def impose_materials(
    maps: tuple[np.ndarray, np.ndarray, np.ndarray],
    raster: MaterialRaster,
    grid: CubicGrid,
    *,
    permittivities: Mapping[str, float],
    threshold: float,
) -> tuple[tuple[np.ndarray, np.ndarray, np.ndarray], int]:
    """Return APBS's own dielectric maps with our solids imposed where APBS sees solvent (D9).

    An edge takes ``permittivities[m]`` where our mesh's material at its midpoint is
    ``m`` and APBS's value exceeds ``threshold``, ``(pdie + sdie)/2``: APBS's surface
    knows the protein but not the membrane, and without it the recorded leg would
    measure the slab rather than the azimuthal averaging.

    Returns
    -------
    tuple
        The three maps, and how many edges were changed.
    """
    import numpy as np

    names = list(raster.materials)
    targets = {names.index(name): value for name, value in permittivities.items() if name in names}
    x, y, z = grid.axis(0), grid.axis(1), grid.axis(2)
    half = 0.5 * grid.spacing_nm
    changed = 0
    imposed: list[np.ndarray] = []
    for along, values in enumerate(maps):
        shifted = [x + half if along == 0 else x, y + half if along == 1 else y]
        radius = np.hypot(shifted[0][:, None], shifted[1][None, :])
        i_r = raster.r_index(radius)
        i_z = raster.z_index(z + half if along == 2 else z)
        result = np.array(values, dtype=np.float64, copy=True)
        for k, row in enumerate(i_z):
            material = raster.material[row][i_r]
            for number, value in targets.items():
                mask = (material == number) & (result[:, :, k] > threshold)
                changed += int(np.count_nonzero(mask))
                result[:, :, k][mask] = value
        imposed.append(result)
    return (imposed[0], imposed[1], imposed[2]), changed


def ring_statistics(
    potential: np.ndarray, grid: CubicGrid, points_nm: np.ndarray, *, angles: int = RING_ANGLES
) -> tuple[np.ndarray, np.ndarray]:
    """Return APBS's azimuthal mean and spread (max - min) on each point's ring, trilinearly.

    Each distinct ``(r, z)`` is sampled at ``angles`` equal angles; the result is
    mapped back to every point.
    """
    import numpy as np

    meridional, inverse = unique_meridional(points_nm)
    theta = 2.0 * math.pi * np.arange(angles) / angles
    r = meridional[:, 0][:, None]
    ring = np.stack(
        [
            (r * np.cos(theta)).reshape(-1),
            (r * np.sin(theta)).reshape(-1),
            np.repeat(meridional[:, 1], angles),
        ],
        axis=1,
    )
    values = trilinear(potential, grid)(ring).reshape(-1, angles)
    mean = values.mean(axis=1)
    spread = values.max(axis=1) - values.min(axis=1)
    return np.asarray(mean[inverse]), np.asarray(spread[inverse])


class RecordedReport(BaseModel):
    """VAL-06's recorded leg: APBS's own model of the PQR against ours (D9). Not gated."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    leg: Literal["recorded"] = "recorded"
    structure: str
    temperature_K: float
    grid: dict[str, object]
    probes: int
    axis_probes: int
    angles: int
    imposed_edges: int
    """Edges of APBS's maps set to a solid of ours that its surface called solvent."""
    agreement: Norms
    """APBS's azimuthal mean on each probe's ring against ours."""
    nodes: Norms
    """APBS at the probe nodes themselves against ours, before the azimuthal mean."""
    spread: dict[str, float]
    """``max`` and ``rms`` of the ring spread, relative to ours' max and rms: the 3D structure."""
    seconds: dict[str, float]
    memory_GB: dict[str, float | None]


@dataclass(frozen=True)
class RecordedInputs:
    """What the recorded leg needs.

    Parameters
    ----------
    pqr
        One frame's atoms in the model frame, as :func:`write_pqr` writes them.
    raster, ours, temperature_K, sdie, structure
        As for :class:`GatedInputs`.
    pdie
        The protein's permittivity, APBS's ``pdie``.
    imposed
        Solids APBS's surface does not know, and their permittivity: the membrane.
    """

    pqr: Path
    raster: MaterialRaster
    ours: Sampler
    temperature_K: float
    sdie: float
    pdie: float
    imposed: Mapping[str, float]
    structure: str


def recorded_leg(
    inputs: RecordedInputs,
    grid: CubicGrid,
    workspace: Path,
    probes: ProbeSet,
    *,
    timeout_s: float = TIMEOUT_S,
) -> tuple[RecordedReport, dict[str, np.ndarray]]:
    """Run VAL-06's recorded leg on ``grid``: two APBS passes, compared per ring (D9).

    Pass 1 takes APBS's ``chgm spl4`` charge and ``srfm smol`` surface from the
    PQR and writes its dielectric maps; our membrane is imposed on them
    (:func:`impose_materials`); pass 2 solves on the result with our solution on
    the faces. Each probe's ring is sampled at :data:`RING_ANGLES` angles: the mean
    is compared with ours, and the spread is what the azimuthal averaging of CON-04
    removes. Only the probes whose whole ring lies in the box are compared; a
    probe towards a corner of the box has a ring that leaves it.

    Returns
    -------
    tuple
        The report, and the arrays over the compared probes: ``ours``, ``mean``,
        ``spread``, ``nodes`` and ``axis``, the mask of those on ``r = 0``, so that a
        caller combining frames needs no second copy of the subset's rule.
    """
    import numpy as np

    reach = min(-grid.origin_nm[0], grid.upper_nm[0], -grid.origin_nm[1], grid.upper_nm[1])
    probes = probes.subset(np.hypot(probes.points_nm[:, 0], probes.points_nm[:, 1]) <= reach)

    surface = SmolSurface(pqr=inputs.pqr, pdie=inputs.pdie)
    faces = face_map(grid, inputs.ours)
    first = ApbsProblem(
        grid=grid,
        temperature_K=inputs.temperature_K,
        sdie=inputs.sdie,
        faces=faces,
        surface=surface,
        write_dielectric=True,
    )
    seconds: dict[str, float] = {}
    memory: dict[str, float | None] = {}
    surface_pass = run_apbs(first, workspace, name="recorded_surface", timeout_s=timeout_s)
    assert surface_pass.dielectric is not None
    seconds["recorded_surface"] = surface_pass.seconds
    memory["recorded_surface"] = surface_pass.memory_GB
    maps, changed = impose_materials(
        surface_pass.dielectric,
        inputs.raster,
        grid,
        permittivities=inputs.imposed,
        threshold=0.5 * (inputs.pdie + inputs.sdie),
    )
    solved = run_apbs(
        replace(first, dielectric=maps, write_dielectric=False),
        workspace,
        name="recorded",
        timeout_s=timeout_s,
    )
    seconds["recorded"] = solved.seconds
    memory["recorded"] = solved.memory_GB
    ours = probes.sample(inputs.ours)
    mean, spread = ring_statistics(solved.potential, grid, probes.points_nm)
    nodes = probes.at(solved.potential)
    report = RecordedReport(
        structure=inputs.structure,
        temperature_K=inputs.temperature_K,
        grid=grid.summary(),
        probes=probes.count,
        axis_probes=int(np.count_nonzero(probes.axis)),
        angles=RING_ANGLES,
        imposed_edges=changed,
        agreement=norms(mean - ours, ours, probes.axis),
        nodes=norms(nodes - ours, ours, probes.axis),
        spread={
            "max": float(np.max(spread) / np.max(np.abs(ours))),
            "rms": float(np.sqrt(np.mean(spread**2)) / np.sqrt(np.mean(ours**2))),
        },
        seconds=seconds,
        memory_GB=memory,
    )
    return report, {
        "ours": ours,
        "mean": mean,
        "spread": spread,
        "nodes": nodes,
        "axis": probes.axis,
    }
