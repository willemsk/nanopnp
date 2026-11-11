"""The channel's axis from a pore's empty space, and its gates (FR-02)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from nanopnp.core.hashing import Canonicalisable
from nanopnp.structure.axis import (
    ORIENTATION_LIMIT_DEG,
    Displacement,
    SymmetryGateError,
    tilt_deg,
    z_displacement,
)

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

# Every constant here: SPECIFICATION.md §5.2 NOTE on stage 1, the channel's axis; the two
# measured ones: knowledge/04-clya-geometry-and-charge/15-the-channel-axis-of-2wcd.md.
SLAB_NM = 0.5

REACH_NM = 1.0

GAP_DEG = 90.0

MIN_CLEARANCE_NM = 0.2

TIE_NM = 1e-3

COVERAGE_FRACTION = 0.5

TURN_TOL_RAD = 1e-6

MOVE_TOL_NM = 1e-6

MAX_ITERATIONS = 50

STRAIGHTNESS_NM = 0.03

CAVITY_BUDGET_NM = 0.015

HYDROGENS: frozenset[str] = frozenset({"H", "D"})


@dataclass(frozen=True)
class ChannelRecord:
    """The channel's axis in the file's frame, with every gate measurement."""

    axis: np.ndarray
    foot_nm: np.ndarray
    centroid_nm: np.ndarray
    centres_nm: np.ndarray
    planes: int
    straightness_nm: float
    iterations: int
    turn_rad: float
    move_nm: float
    carried: tuple[np.ndarray, ...]

    @property
    def coverage(self) -> float:
        """The fraction of the planes that hold an enclosed space."""
        return len(self.centres_nm) / self.planes

    @property
    def tilt_deg(self) -> float:
        """The angle between the axis and the file's z, in degrees."""
        return tilt_deg(self.axis)

    @property
    def converged(self) -> bool:
        """Whether the last iteration left the line where it found it."""
        return self.turn_rad <= TURN_TOL_RAD and self.move_nm <= MOVE_TOL_NM

    def summary(self) -> dict[str, Canonicalisable]:
        """Return the record as plain data, for the artefact header."""
        return {
            "axis": [float(value) for value in self.axis],
            "centroid_nm": [float(value) for value in self.centroid_nm],
            "foot_nm": [float(value) for value in self.foot_nm],
            "planes": self.planes,
            "centres": len(self.centres_nm),
            "coverage": self.coverage,
            "straightness_nm": self.straightness_nm,
            "iterations": self.iterations,
            "tilt_deg": self.tilt_deg,
        }


@dataclass(frozen=True)
class _Voids:
    atoms: np.ndarray
    tree: Any
    simplices: np.ndarray
    centres: np.ndarray
    edges: np.ndarray
    edge_atom: np.ndarray
    reach_nm: float


def circumcentres(points: np.ndarray, simplices: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return each tetrahedron's circumcentre and whether its four points fix one."""
    import numpy as np

    first = points[simplices[:, 0]]
    edges = points[simplices[:, 1:]] - first[:, None, :]
    lengths = np.linalg.norm(edges, axis=2).max(axis=1)
    sound = np.abs(np.linalg.det(edges)) > 1e-10 * lengths**3
    centres = np.full((len(simplices), 3), np.nan)
    if sound.any():
        half = 0.5 * np.sum(edges[sound] ** 2, axis=2)
        centres[sound] = first[sound] + np.linalg.solve(edges[sound], half[..., None])[..., 0]
    return centres, sound


def _voids(atoms: np.ndarray) -> _Voids:
    import numpy as np
    from scipy.spatial import Delaunay, cKDTree

    centre = atoms.mean(axis=0)
    local = atoms - centre
    mesh = Delaunay(local)
    simplices = np.asarray(mesh.simplices, dtype=np.int64)
    centres, sound = circumcentres(local, simplices)
    neighbours = np.asarray(mesh.neighbors, dtype=np.int64)
    # Atoms on one sphere, as the images of an atom under an exact symmetry are, triangulate
    # into tetrahedra some of which are flat. A flat one takes the centre of a neighbour whose
    # sphere holds its four atoms, so the Voronoi edges through it stay joined.
    flat = np.flatnonzero(~sound)
    while len(flat):
        taken = np.zeros(len(flat), dtype=bool)
        for side in range(4):
            beside = neighbours[flat, side]
            usable = ~taken & (beside >= 0) & sound[np.maximum(beside, 0)]
            centre_beside = centres[np.maximum(beside, 0)]
            span = np.linalg.norm(local[simplices[flat]] - centre_beside[:, None, :], axis=2)
            on_sphere = np.ptp(span, axis=1) <= 1e-9 * np.maximum(1.0, span.max(axis=1))
            adopt = usable & on_sphere
            centres[flat[adopt]] = centre_beside[adopt]
            taken |= adopt
        if not taken.any():
            break
        sound[flat[taken]] = True
        flat = flat[~taken]
    radius = np.linalg.norm(centres - local[simplices[:, 0]], axis=1)
    # A sphere wider than the molecule twice over has the molecule on one side of it.
    reach = 2.0 * float(np.linalg.norm(local, axis=1).max())
    valid = sound & (radius <= reach)
    centres = centres + centre
    tree = cKDTree(atoms)
    # A sliver of nearly cospherical atoms solves to a sphere that is not empty.
    nearest, _ = tree.query(centres[valid])
    valid[np.flatnonzero(valid)] = np.abs(nearest - radius[valid]) <= 1e-6 * np.maximum(
        1.0, radius[valid]
    )
    # A Voronoi edge joins the circumcentres of two tetrahedra that share a face, and every
    # point of it is as far from that face's three atoms as from no other atom nearer. Past a
    # face of the hull the edge runs on from its tetrahedron's centre along the face's normal.
    owner = np.repeat(np.arange(len(simplices)), 4)
    other = neighbours.reshape(-1)
    opposite = np.tile(np.arange(4), len(simplices))
    keep = (other > owner) & valid[owner] & valid[np.maximum(other, 0)]
    open_face = (other < 0) & valid[owner]
    corners = np.stack(
        [simplices[owner[open_face], (opposite[open_face] + k) % 4] for k in (1, 2, 3)], axis=1
    )
    apex = atoms[simplices[owner[open_face], opposite[open_face]]]
    base = atoms[corners[:, 0]]
    normal = np.cross(atoms[corners[:, 1]] - base, atoms[corners[:, 2]] - base)
    length = np.linalg.norm(normal, axis=1)
    whole = length > 0.0
    normal[whole] /= length[whole, None]
    normal *= -np.sign(np.sum((apex - base) * normal, axis=1))[:, None]
    ends = centres[owner[open_face]] + reach * normal
    return _Voids(
        atoms=atoms,
        tree=tree,
        simplices=simplices,
        centres=np.concatenate([centres, ends[whole]]),
        edges=np.concatenate(
            [
                np.column_stack([owner[keep], other[keep]]),
                np.column_stack(
                    [owner[open_face][whole], len(simplices) + np.arange(int(whole.sum()))]
                ),
            ]
        ),
        edge_atom=np.concatenate(
            [simplices[owner[keep], (opposite[keep] + 1) % 4], corners[whole, 0]]
        ),
        reach_nm=reach,
    )


def _basis(axis: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    import numpy as np

    seed = np.array([1.0, 0.0, 0.0]) if abs(axis[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    first = seed - (seed @ axis) * axis
    first /= np.linalg.norm(first)
    return first, np.cross(axis, first)


def _enclosed(voids: _Voids, centre: np.ndarray, clearance: float, axis: np.ndarray) -> bool:
    import numpy as np

    near = voids.tree.query_ball_point(centre, clearance + REACH_NM)
    offset = voids.atoms[near] - centre
    axial = offset @ axis
    first, second = _basis(axis)
    along, across = offset @ first, offset @ second
    beside = np.abs(axial) <= 0.5 * SLAB_NM
    if np.count_nonzero(beside) < 3:
        return False
    phi = np.sort(np.arctan2(across[beside], along[beside]))
    gaps = np.diff(np.concatenate([phi, phi[:1] + 2.0 * np.pi]))
    return bool(gaps.max() < math.radians(GAP_DEG))


@dataclass(frozen=True)
class _Section:
    points: np.ndarray
    clearance: np.ndarray
    edges: np.ndarray


def _sections(voids: _Voids, axis: np.ndarray, point: np.ndarray) -> list[_Section]:
    import numpy as np

    # The planes are counted from the atoms' centroid, which no iteration moves.
    anchor = float((voids.atoms.mean(axis=0) - point) @ axis)
    heights = (voids.atoms - point) @ axis
    first = math.ceil((float(heights.min()) - anchor) / SLAB_NM - 0.5)
    last = math.floor((float(heights.max()) - anchor) / SLAB_NM - 0.5)
    height = (voids.centres - point) @ axis
    below, above = height[voids.edges[:, 0]], height[voids.edges[:, 1]]
    sections = []
    for plane in range(first, last + 1):
        level = anchor + (plane + 0.5) * SLAB_NM
        crossing = np.flatnonzero(((below - level) * (above - level) <= 0.0) & (below != above))
        fraction = (level - below[crossing]) / (above[crossing] - below[crossing])
        start = voids.centres[voids.edges[crossing, 0]]
        points = start + fraction[:, None] * (voids.centres[voids.edges[crossing, 1]] - start)
        clearance = np.linalg.norm(points - voids.atoms[voids.edge_atom[crossing]], axis=1)
        wide = (clearance >= MIN_CLEARANCE_NM) & (clearance <= voids.reach_nm)
        order = np.flatnonzero(wide)[np.argsort(-clearance[wide], kind="stable")]
        sections.append(
            _Section(
                points=points[order],
                clearance=clearance[order],
                edges=voids.edges[crossing[order]],
            )
        )
    return sections


def _section_centres(
    voids: _Voids, axis: np.ndarray, point: np.ndarray
) -> tuple[np.ndarray, tuple[np.ndarray, ...], int]:
    import numpy as np

    sections = _sections(voids, axis, point)

    def pick(section: _Section, near: np.ndarray | None, allowed_nm: float) -> list[int]:
        # In descending clearance, as a section is held.
        members = np.arange(len(section.clearance))
        if near is not None:
            aside = section.points - near
            aside = aside - np.outer(aside @ axis, axis)
            members = members[np.linalg.norm(aside, axis=1) <= allowed_nm]
        tied: list[int] = []
        for index in members:
            if tied and section.clearance[index] < section.clearance[tied[0]] - TIE_NM:
                break
            if _enclosed(voids, section.points[index], float(section.clearance[index]), axis):
                tied.append(int(index))
        return tied

    # The channel starts at the widest enclosed space and is followed plane by plane: a centre
    # further aside than along from the last one is a void of the wall, not the channel.
    found: dict[int, list[int]] = {}
    widest = 0.0
    seed: int | None = None
    for plane, section in enumerate(sections):
        for index in range(len(section.clearance)):
            if section.clearance[index] <= widest:
                break
            if _enclosed(voids, section.points[index], float(section.clearance[index]), axis):
                widest, seed = float(section.clearance[index]), plane
                break
    if seed is not None:
        found[seed] = pick(sections[seed], None, 0.0)
        for step in (1, -1):
            last = seed
            plane = seed + step
            while 0 <= plane < len(sections):
                near = sections[last].points[found[last]].mean(axis=0)
                tied = pick(sections[plane], near, SLAB_NM * abs(plane - last))
                if tied:
                    found[plane] = tied
                    last = plane
                plane += step
    kept = sorted(found)
    centres = np.asarray(
        [sections[plane].points[found[plane]].mean(axis=0) for plane in kept]
    ).reshape(-1, 3)
    # A centre is carried with the atoms of the tetrahedron its edge starts from.
    carried = tuple(voids.simplices[sections[plane].edges[found[plane], 0]] for plane in kept)
    return centres, carried, len(sections)


def fit_line(centres: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return the least-squares line through ``centres``: its axis, signed to +z, and a point."""
    import numpy as np

    point = centres.mean(axis=0)
    _, _, vt = np.linalg.svd(centres - point)
    axis = vt[0] / np.linalg.norm(vt[0])
    return (axis if axis[2] >= 0.0 else -axis), point


def _off_line(points: np.ndarray, axis: np.ndarray, point: np.ndarray) -> np.ndarray:
    import numpy as np

    offset = np.atleast_2d(points) - point
    return np.asarray(
        np.linalg.norm(offset - np.outer(offset @ axis, axis), axis=1), dtype=np.float64
    )


def channel_axis(
    atoms_nm: np.ndarray,
    *,
    start_axis: np.ndarray | None = None,
    start_point_nm: np.ndarray | None = None,
) -> ChannelRecord:
    """Find the channel's axis among heavy atoms, without gating it.

    Parameters
    ----------
    start_axis, start_point_nm
        The line the iteration starts from; the file's z through the atoms' centroid when None.

    Raises
    ------
    SymmetryGateError
        When fewer than two planes hold an enclosed space, so no line can be fitted.
    """
    import numpy as np

    atoms = np.asarray(atoms_nm, dtype=np.float64)
    voids = _voids(atoms)
    axis = np.array([0.0, 0.0, 1.0]) if start_axis is None else np.asarray(start_axis, float)
    axis = axis / np.linalg.norm(axis)
    point = atoms.mean(axis=0) if start_point_nm is None else np.asarray(start_point_nm, float)
    iterations = 0
    while iterations < MAX_ITERATIONS:
        iterations += 1
        centres, carried, planes = _section_centres(voids, axis, point)
        if len(centres) < 2:
            raise SymmetryGateError(
                f"channel coverage gate: {len(centres)} of the {planes} planes {SLAB_NM:g} nm "
                f"apart along the axis hold an enclosed space of at least {MIN_CLEARANCE_NM:g} nm "
                "clearance, and a line needs two; the structure has no channel this method "
                "finds (SPECIFICATION.md section 5.2 NOTE on stage 1)"
            )
        found, centroid = fit_line(centres)
        turn = math.atan2(float(np.linalg.norm(np.cross(axis, found))), abs(float(axis @ found)))
        move = float(_off_line(centroid, axis, point)[0])
        axis, point = found, centroid
        if turn <= TURN_TOL_RAD and move <= MOVE_TOL_NM:
            break
    return ChannelRecord(
        axis=axis,
        foot_nm=point - (point @ axis) * axis,
        centroid_nm=point,
        centres_nm=centres,
        planes=planes,
        straightness_nm=float(_off_line(centres, axis, point).max()),
        iterations=iterations,
        turn_rad=turn,
        move_nm=move,
        carried=carried,
    )


def gate_channel(record: ChannelRecord) -> ChannelRecord:
    """Apply the convergence, coverage, straightness and orientation gates to a channel's axis.

    Raises
    ------
    SymmetryGateError
        Naming the gate and the measured value.
    """
    if not record.converged:
        raise SymmetryGateError(
            f"channel convergence gate: after {record.iterations} iterations the line through "
            f"the planes' centres still turned {record.turn_rad:.3e} rad and moved "
            f"{record.move_nm:.3e} nm, against limits of {TURN_TOL_RAD:g} rad and "
            f"{MOVE_TOL_NM:g} nm; the channel fixes no one axis"
        )
    if not record.coverage >= COVERAGE_FRACTION:
        raise SymmetryGateError(
            f"channel coverage gate: {len(record.centres_nm)} of the {record.planes} planes "
            f"{SLAB_NM:g} nm apart along the axis hold an enclosed space, a fraction of "
            f"{record.coverage:.2f} against a limit of {COVERAGE_FRACTION:g}; the channel does "
            "not run the length of the structure"
        )
    if not record.straightness_nm <= STRAIGHTNESS_NM:
        raise SymmetryGateError(
            f"channel straightness gate: a plane's centre lies {record.straightness_nm:.3f} nm "
            f"from the line fitted through them, against a limit of {STRAIGHTNESS_NM:g} nm; the "
            "channel is not straight enough to name an axis"
        )
    if not record.tilt_deg <= ORIENTATION_LIMIT_DEG:
        raise SymmetryGateError(
            f"orientation gate: the channel's axis is {record.tilt_deg:.2f} degrees from the "
            f"file's z against a limit of {ORIENTATION_LIMIT_DEG:g}; the axis is signed by the "
            "file's +z, which must point from trans to cis, and a frame this far from it does "
            "not name an end (SPECIFICATION.md section 5.2 NOTE on stage 1)"
        )
    return record


def detect_channel(atoms_nm: np.ndarray) -> ChannelRecord:
    """Find the channel's axis among heavy atoms and gate it.

    Raises
    ------
    SymmetryGateError
        On any gate failure.
    """
    return gate_channel(channel_axis(atoms_nm))


def check_z_channel(record: ChannelRecord, z_extent_nm: tuple[float, float]) -> Displacement:
    """Admit ``symmetry.axis: z`` only inside the channel's displacement budget.

    Raises
    ------
    SymmetryGateError
        When the displacement exceeds the budget.
    """
    found = z_displacement(record.axis, record.centroid_nm, z_extent_nm, budget_nm=CAVITY_BUDGET_NM)
    if not found.displacement_nm <= CAVITY_BUDGET_NM:
        raise SymmetryGateError(
            f"axis: z displacement gate: the file's z axis is {found.displacement_nm:.4f} nm from "
            f"the channel's axis over the C-alpha axial extent [{z_extent_nm[0]:.2f}, "
            f"{z_extent_nm[1]:.2f}] nm (tilt {found.tilt_deg:.3f} degrees, offset "
            f"{found.offset_nm:.4f} nm), against a budget of {CAVITY_BUDGET_NM:g} nm; use "
            "symmetry.axis: auto"
        )
    return found


def refit(record: ChannelRecord, mean_nm: np.ndarray, atoms_nm: np.ndarray) -> np.ndarray:
    """Return the axis through the record's centres, each moved with its tetrahedron's atoms.

    Parameters
    ----------
    mean_nm
        The heavy atoms the record was found among.
    atoms_nm
        The same atoms at other positions, a frame's.
    """
    import numpy as np

    mean = np.asarray(mean_nm, dtype=np.float64)
    atoms = np.asarray(atoms_nm, dtype=np.float64)
    centres = []
    for centre, simplices in zip(record.centres_nm, record.carried, strict=True):
        for corners in simplices:
            first = mean[corners[0]]
            edges = (mean[corners[1:]] - first).T
            if abs(np.linalg.det(edges)) <= 1e-10 * np.linalg.norm(edges, axis=0).max() ** 3:
                continue
            weights = np.linalg.solve(edges, centre - first)
            moved = atoms[corners[0]] + (atoms[corners[1:]] - atoms[corners[0]]).T @ weights
            centres.append(moved)
            break
    axis, _ = fit_line(np.asarray(centres))
    return axis
