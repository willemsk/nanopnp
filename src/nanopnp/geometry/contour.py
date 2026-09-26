"""Stage 4 of section 5.2: contour extraction, conditioning and its gate (FR-07, FR-08).

The pipeline is section 5.2.1's, and its constants are the WP20 plan's D4-D10.
Each step is a pure function over arrays, so a test can drive one alone:

1. :func:`extract_loops`: sub-pixel marching squares on stage 3's mean at the
   isolevel, diagonal neighbours above the level joined (``"high"``). A point
   ``(row, col)`` is placed by the grid's own axes, so bin j sits at its centre
   ``r_j = j·h``: the author's script placed it at the bin's left edge on a bin of
   the wrong width, which is its erratum (``.knowledge/04`` §1.2). A contour left
   open at the grid's edge is refused.
2. :func:`assemble_region`: the closed loops become the region above the level.
   ``positive_orientation="high"`` makes a loop around high values clockwise in
   ``(r, z)`` and a loop around a void counter-clockwise, so winding tells an
   outer boundary from a hole [tested]. Loops are taken largest first, so a loop
   is always met after the loop enclosing it.
3. :func:`close_and_open`: a closing, then an opening, by a disc of radius
   δ = 2h. Every gap and fin narrower than 4h goes. The margin is the §5.2.1
   NOTE's: simplification moves each wall by up to its tolerance, so the gate's
   feature size 2h holds only if δ > h + ``simplify_tol_nm``. Remaining holes are
   filled and recorded; exactly one component is admitted.
4. :func:`resample` at uniform arc length h/2, then :func:`taubin`: N = 10
   passes of λ = 0.5, μ = -0.53 with the umbrella operator. On a closed loop the
   operator is circulant, and mode ``k = 1 - cos θ`` is scaled by
   ``(1 - λk)(1 - μk)`` per pass: the pass band is wavelengths above 13.08
   samples, 0.33 nm, and the grid-scale staircase (k = 1) keeps 0.069 of its
   amplitude (WP20 plan, Design §3).
5. :func:`simplify`: Douglas-Peucker at ``simplify_tol_nm``, topology preserved.
6. :func:`enforce_spacing`: while an edge is shorter than ``h_c``, drop the
   endpoint whose removal moves the area least, the lower index on a tie.
7. :func:`canonical`: clockwise from the lowest-z vertex, the smallest r on a tie.

:func:`gate` then measures the loop and never moves it. **Its size target
``h_c`` is the density grid spacing h**, not the stage-6 wall size, which would
make the geometry depend on the electrolyte (§5.2.1 NOTE on the contour's size
target). Every threshold here is a constant that keys the stage-4 artefact
(D13), and none is a case key (WP17 D3).
"""

from __future__ import annotations

import logging
import math
import re
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import shapely
from shapely.geometry import LinearRing, MultiPolygon, Polygon
from shapely.geometry.base import BaseGeometry
from shapely.validation import explain_validity
from skimage.measure import find_contours

from nanopnp.core.hashing import Canonicalisable
from nanopnp.core.paths import store_root
from nanopnp.core.stages import (
    CancelToken,
    Progress,
    StageDescription,
    check_cancelled,
    describe,
    report,
)
from nanopnp.density.radii import KERNEL_RADII, radius_set_digest, resolve_radii
from nanopnp.geometry.probe import probe_radius_profile
from nanopnp.io.artefact import ProfileArtefact
from nanopnp.io.case import ContourSpec, DensitySpec, UnsupportedCaseSection, resolve
from nanopnp.mesh.profile import (
    LOCAL_EDGES,
    PIPELINE_SOURCE,
    PROFILE_SCHEMA,
    PoreProfile,
    ProfileProvenance,
    feature_sizes,
    min_feature_size,
    min_vertex_spacing,
    signed_area,
    write_profile,
)
from nanopnp.structure.ensemble import PAYLOAD_NAME as ENSEMBLE_PAYLOAD
from nanopnp.structure.ensemble import AlignedEnsemble
from nanopnp.symmetry.reduce import PAYLOAD_NAME as REDUCED_PAYLOAD
from nanopnp.symmetry.reduce import ReducedMap

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

    from nanopnp.io.artefact import StageInputs

logger = logging.getLogger(__name__)

CONNECTIVITY = "high"
"""``find_contours``'s ``fully_connected``: diagonal neighbours above the level are joined.

The closing of step 3 would join them anyway; choosing it here keeps marching
squares and the morphology in agreement (D4).
"""

CLOSING_SPACINGS = 2.0
"""δ, the closing and opening disc's radius, in grid spacings (D5)."""

QUAD_SEGS = 8
"""Segments per quarter circle of the buffer's round joins (D5)."""

RESAMPLE_SPACINGS = 0.5
"""The resampling arc length, in grid spacings: h/2 (D6)."""

TAUBIN_LAMBDA = 0.5
"""Taubin's shrinking factor λ (Taubin, SIGGRAPH 1995; WP20 plan, Design §3)."""

TAUBIN_MU = -0.53
"""Taubin's inflating factor μ; ``1/λ + 1/μ = 0.1132`` is the pass-band edge in k."""

TAUBIN_PASSES = 10
"""N, the number of λ|μ pass pairs (D6)."""

BAND_HIGH_NM = 1.5
"""The radius band's upper bound, ``r_c - R_p ≤ 1.5 nm``: a gross-error check (D11)."""

FEATURE_FACTOR = 2.0
"""The feature-size criterion is ``> FEATURE_FACTOR · h_c`` (§5.2.1)."""

KEY_CONSTANTS: Mapping[str, Canonicalisable] = {
    "connectivity": CONNECTIVITY,
    "closing": {"radius": "2h", "quad_segs": QUAD_SEGS},
    "taubin": {
        "lambda": TAUBIN_LAMBDA,
        "mu": TAUBIN_MU,
        "passes": TAUBIN_PASSES,
        "resample": "h/2",
    },
    "spacing": "h",
    "feature": {"factor": FEATURE_FACTOR, "local_edges": LOCAL_EDGES},
    "band": {"low": "-h", "high_nm": BAND_HIGH_NM},
}
"""Every code constant that moves a vertex or a verdict, as the stage-4 key records it (D13)."""


class ContourGateError(ValueError):
    """Stage 4's contour failed a section 5.2.1 criterion (FR-08, QR-12).

    Names the criterion, what was measured, the threshold and where, and is
    classified with the gates: the case is well formed, and the structure it names
    does not yield a contour the mesher can be trusted with.

    Parameters
    ----------
    criterion
        The §5.2.1 gate row, e.g. ``"minimum vertex spacing"``.
    measured
        The measured value, with units.
    threshold
        What it was held to, with units.
    where
        The location: an ``(r, z)``, a z range, or a list of components.
    """

    def __init__(self, criterion: str, measured: str, threshold: str, where: str) -> None:
        self.criterion = criterion
        self.measured = measured
        self.threshold = threshold
        self.where = where
        super().__init__(
            f"stage 4 contour gate, {criterion}: {measured}, against {threshold}, {where} "
            "(section 5.2.1, FR-08)"
        )


def _at(r_nm: float, z_nm: float) -> str:
    """Format a location for a gate message."""
    return f"at (r, z) = ({r_nm:.4f}, {z_nm:.4f}) nm"


# -- 1. extraction ---------------------------------------------------------------


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """Return the ``[first, last]`` index pairs of each run of true entries."""
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for index, flag in enumerate(mask.tolist()):
        if flag and start is None:
            start = index
        elif not flag and start is not None:
            runs.append((start, index - 1))
            start = None
    if start is not None:
        runs.append((start, len(mask) - 1))
    return runs


def extract_loops(
    mean: np.ndarray, r_nm: np.ndarray, z_nm: np.ndarray, isolevel: float
) -> list[np.ndarray]:
    """Return the closed isolevel contours of a ``[z, r]`` map, in ``(r, z)`` nm (step 1).

    Parameters
    ----------
    mean
        Stage 3's mean, indexed ``[z, r]``.
    r_nm, z_nm
        Its uniform axes; a point ``(row, col)`` maps to
        ``(r_nm[0] + col·Δr, z_nm[0] + row·Δz)``.
    isolevel
        The level, in (0, 1).

    Returns
    -------
    list of numpy.ndarray
        Each loop ``(n, 2)``, the closing vertex not repeated, in the orientation
        ``positive_orientation="high"`` gives it.

    Raises
    ------
    ContourGateError
        If a contour is open. At the axis, naming the z ranges where the axis bin
        lies at or above the level, which is where the lumen is closed; at another
        edge, naming the edge.
    """
    import numpy as np

    values = np.asarray(mean, dtype=np.float64)
    contours = find_contours(  # type: ignore[no-untyped-call]
        values, isolevel, fully_connected=CONNECTIVITY, positive_orientation="high"
    )
    r0, dr = float(r_nm[0]), float(r_nm[1] - r_nm[0])
    z0, dz = float(z_nm[0]), float(z_nm[1] - z_nm[0])
    rows, columns = values.shape
    loops: list[np.ndarray] = []
    for contour in contours:
        if not np.array_equal(contour[0], contour[-1]):
            ends = np.vstack((contour[0], contour[-1]))
            if np.any(ends[:, 1] == 0.0):
                closed = _runs(values[:, 0] >= isolevel)
                spans = ", ".join(
                    f"z = {z0 + first * dz:.3f} to {z0 + last * dz:.3f} nm"
                    for first, last in closed
                )
                raise ContourGateError(
                    "loop topology",
                    f"the contour at isolevel {isolevel} is open at the axis",
                    "a closed loop clear of the axis",
                    f"because the lumen is closed on the axis over {spans or 'no node'}",
                )
            edges = {
                "the outer radial edge": np.any(ends[:, 1] == columns - 1),
                "the lowest z plane": np.any(ends[:, 0] == 0.0),
                "the highest z plane": np.any(ends[:, 0] == rows - 1),
            }
            named = ", ".join(name for name, hit in edges.items() if hit) or "the grid's edge"
            first = ends[0]
            raise ContourGateError(
                "loop topology",
                f"the contour at isolevel {isolevel} is open at {named}",
                "a closed loop inside the grid",
                _at(r0 + first[1] * dr, z0 + first[0] * dz),
            )
        loop = np.column_stack((r0 + contour[:-1, 1] * dr, z0 + contour[:-1, 0] * dz))
        loops.append(loop)
    return loops


# -- 2. the region ---------------------------------------------------------------


def assemble_region(loops: Sequence[np.ndarray]) -> BaseGeometry:
    """Return the region above the isolevel that the loops bound (step 2).

    A clockwise loop in ``(r, z)`` bounds high values and is added; a
    counter-clockwise one bounds a void and is removed. Largest first, so every
    loop is met after the loop that encloses it: a body, then its void, then an
    island inside the void.
    """
    ordered = sorted(loops, key=lambda loop: abs(signed_area(loop)), reverse=True)
    region: BaseGeometry = Polygon()
    for loop in ordered:
        if len(loop) < 3:
            continue
        polygon = shapely.make_valid(Polygon(loop))
        region = region.union(polygon) if signed_area(loop) < 0.0 else region.difference(polygon)
    return region


# -- 3. the morphology -----------------------------------------------------------


def _components(region: BaseGeometry) -> list[Polygon]:
    """Return the region's polygons, largest first."""
    if isinstance(region, Polygon):
        parts = [] if region.is_empty else [region]
    elif isinstance(region, MultiPolygon):
        parts = list(region.geoms)
    else:
        parts = [part for part in getattr(region, "geoms", ()) if isinstance(part, Polygon)]
    return sorted(parts, key=lambda part: part.area, reverse=True)


def close_and_open(
    region: BaseGeometry, delta_nm: float
) -> tuple[Polygon, dict[str, Canonicalisable]]:
    """Close, then open, the region by a disc of radius ``delta_nm``, and fill its holes (step 3).

    Returns
    -------
    tuple
        The single component, holes filled, and the record: the area after the
        morphology, and the count, area and centroids of the holes filled.

    Raises
    ------
    ContourGateError
        If the region is empty, or more than one component remains, naming each
        other component's centroid and area.
    """
    options = {"quad_segs": QUAD_SEGS, "join_style": "round"}
    closed = region.buffer(delta_nm, **options).buffer(-delta_nm, **options)
    opened = closed.buffer(-delta_nm, **options).buffer(delta_nm, **options)
    parts = _components(opened)
    if not parts:
        raise ContourGateError(
            "loop topology",
            "no region lies above the isolevel",
            "one component",
            f"after a closing and opening of radius {delta_nm:.4f} nm",
        )
    if len(parts) > 1:
        others = "; ".join(
            f"centroid (r, z) = ({part.centroid.x:.4f}, {part.centroid.y:.4f}) nm, "
            f"area {part.area:.4g} nm^2"
            for part in parts[1:]
        )
        raise ContourGateError(
            "loop topology",
            f"{len(parts)} components remain",
            "one component, no detached island",
            f"beside the body of area {parts[0].area:.4g} nm^2: {others}",
        )
    body = parts[0]
    holes = [Polygon(ring) for ring in body.interiors]
    filled = Polygon(body.exterior)
    record: dict[str, Canonicalisable] = {
        "area_nm2": float(filled.area),
        "holes_filled": {
            "count": len(holes),
            "area_nm2": float(sum(hole.area for hole in holes)),
            "centroids_nm": [[float(h.centroid.x), float(h.centroid.y)] for h in holes],
        },
    }
    return filled, record


def exterior(polygon: Polygon) -> np.ndarray:
    """Return a polygon's exterior ring as ``(n, 2)``, the closing vertex not repeated."""
    import numpy as np

    return np.asarray(polygon.exterior.coords, dtype=np.float64)[:-1]


# -- 4. resampling and smoothing -------------------------------------------------


def resample(loop: np.ndarray, spacing_nm: float) -> np.ndarray:
    """Return the closed loop resampled at a uniform arc length near ``spacing_nm`` (step 4).

    ``n = round(L / spacing_nm)`` points at arc length ``L/n`` apart, from the
    loop's first vertex, so the operator of :func:`taubin` acts on a scale in
    nanometres rather than in marching-squares vertices, which lie 1e-4 to 0.07 nm
    apart (Design §3).
    """
    import numpy as np

    closed = np.vstack((loop, loop[:1]))
    lengths = np.linalg.norm(np.diff(closed, axis=0), axis=1)
    arc = np.concatenate(([0.0], np.cumsum(lengths)))
    total = float(arc[-1])
    count = max(3, round(total / spacing_nm))
    targets = np.arange(count) * (total / count)
    return np.column_stack(
        (np.interp(targets, arc, closed[:, 0]), np.interp(targets, arc, closed[:, 1]))
    )


def taubin(
    loop: np.ndarray,
    *,
    lam: float = TAUBIN_LAMBDA,
    mu: float = TAUBIN_MU,
    passes: int = TAUBIN_PASSES,
) -> np.ndarray:
    """Return the closed loop after ``passes`` Taubin λ|μ passes of the umbrella operator.

    ``Δx_i = ½(x_{i-1} + x_{i+1}) - x_i``, applied with λ and then with μ. With
    ``mu = 0`` this is a Laplacian smoothing of the same number of passes, which
    shrinks a convex loop; λ|μ does not (step 4).
    """
    import numpy as np

    points = np.asarray(loop, dtype=np.float64).copy()
    for _ in range(passes):
        for factor in (lam, mu):
            if factor == 0.0:
                continue
            umbrella = 0.5 * (np.roll(points, 1, axis=0) + np.roll(points, -1, axis=0)) - points
            points = points + factor * umbrella
    return points


# -- 5-7. simplification, spacing, canonical form -------------------------------


def simplify(loop: np.ndarray, tolerance_nm: float) -> np.ndarray:
    """Return the loop after Douglas-Peucker at ``tolerance_nm``, topology preserved (step 5)."""
    simplified = Polygon(loop).simplify(tolerance_nm, preserve_topology=True)
    if not isinstance(simplified, Polygon) or simplified.is_empty:
        raise ContourGateError(
            "validity",
            f"simplification at {tolerance_nm} nm left {simplified.geom_type}",
            "one polygon",
            "over the whole loop",
        )
    return exterior(simplified)


def _removal_cost(points: np.ndarray, vertex: int) -> float:
    """Return the area a vertex's removal changes: its triangle with its two neighbours."""
    count = len(points)
    previous, following = points[(vertex - 1) % count], points[(vertex + 1) % count]
    a, b = previous - points[vertex], following - points[vertex]
    return 0.5 * abs(float(a[0] * b[1] - a[1] * b[0]))


def enforce_spacing(loop: np.ndarray, minimum_nm: float) -> tuple[np.ndarray, int]:
    """Drop vertices until no edge is shorter than ``minimum_nm`` (step 6, D8).

    The shortest edge first, its first occurrence on a tie; of its two endpoints,
    the one whose removal changes the area least, the lower index on a tie.

    Returns
    -------
    tuple
        The loop, and how many vertices were removed.
    """
    import numpy as np

    points = np.asarray(loop, dtype=np.float64)
    removed = 0
    while len(points) > 3:
        lengths = np.linalg.norm(np.roll(points, -1, axis=0) - points, axis=1)
        edge = int(np.argmin(lengths))
        if lengths[edge] >= minimum_nm:
            break
        ends = sorted((edge, (edge + 1) % len(points)))
        costs = [_removal_cost(points, vertex) for vertex in ends]
        drop = ends[0] if costs[0] <= costs[1] else ends[1]
        points = np.delete(points, drop, axis=0)
        removed += 1
    return points, removed


def canonical(loop: np.ndarray) -> np.ndarray:
    """Return the loop clockwise, starting at its lowest-z vertex, the smallest r on a tie (D9)."""
    import numpy as np

    points = np.asarray(loop, dtype=np.float64)
    if signed_area(points) > 0.0:
        points = points[::-1]
    start = int(np.lexsort((points[:, 0], points[:, 1]))[0])
    return np.roll(points, -start, axis=0)


# -- the radius profile ------------------------------------------------------------


def mid_planes(loops: Sequence[np.ndarray], z_nm: np.ndarray) -> np.ndarray:
    """Return the mid-planes between consecutive z nodes that cross any of the loops.

    Marching-squares vertices lie on the z lattice, so the band is sampled
    between them rather than on them (Design §5).
    """
    import numpy as np

    z = np.asarray(z_nm, dtype=np.float64)
    mids = 0.5 * (z[:-1] + z[1:])
    low = min(float(loop[:, 1].min()) for loop in loops)
    high = max(float(loop[:, 1].max()) for loop in loops)
    planes: np.ndarray = mids[(mids > low) & (mids < high)]
    return planes


def innermost_crossings(loops: Sequence[np.ndarray], planes: np.ndarray) -> np.ndarray:
    """Return the smallest radius at which any loop crosses each plane; ``nan`` where none does.

    The interval test is half-open in z, as :func:`nanopnp.mesh.reference.plane_crossings`
    takes it, so a vertex on the plane is counted once.
    """
    import numpy as np

    heights = np.asarray(planes, dtype=np.float64)
    innermost = np.full(heights.size, np.inf)
    for loop in loops:
        starts, ends = loop, np.roll(loop, -1, axis=0)
        z0, z1 = starts[:, 1], ends[:, 1]
        lower, upper = np.minimum(z0, z1), np.maximum(z0, z1)
        crossing = (lower[None, :] <= heights[:, None]) & (heights[:, None] < upper[None, :])
        span = np.where(z1 != z0, z1 - z0, 1.0)
        fraction = (heights[:, None] - z0[None, :]) / span[None, :]
        radii = starts[None, :, 0] + fraction * (ends[None, :, 0] - starts[None, :, 0])
        innermost = np.minimum(innermost, np.where(crossing, radii, np.inf).min(axis=1))
    result: np.ndarray = np.where(np.isfinite(innermost), innermost, np.nan)
    return result


# -- the pipeline ----------------------------------------------------------------


@dataclass(frozen=True)
class ConditionedContour:
    """The conditioned loop, and what conditioning did to it.

    Parameters
    ----------
    loop
        ``(n, 2)`` in ``(r, z)`` nm, canonical (D9).
    raw_loops
        The closed loops of step 1, before anything moved them.
    record
        Area and vertex count after each step, the holes filled, and the vertices
        the spacing step removed.
    """

    loop: np.ndarray
    raw_loops: tuple[np.ndarray, ...]
    record: dict[str, Canonicalisable]


def condition(
    mean: np.ndarray,
    r_nm: np.ndarray,
    z_nm: np.ndarray,
    *,
    spacing_nm: float,
    isolevel: float,
    smoothing: str,
    simplify_tol_nm: float,
) -> ConditionedContour:
    """Run steps 1 to 7 on a stage-3 mean.

    Parameters
    ----------
    mean, r_nm, z_nm
        As :func:`extract_loops` takes them.
    spacing_nm
        h, the density grid spacing: δ = 2h, the resampling h/2, and ``h_c = h``.
    isolevel, smoothing, simplify_tol_nm
        ``geometry.contour``. ``smoothing: none`` skips the resampling and Taubin.

    Raises
    ------
    ContourGateError
        From extraction, the morphology or simplification, naming the criterion.
    """
    import numpy as np

    loops = extract_loops(mean, r_nm, z_nm, isolevel)
    if not loops:
        raise ContourGateError(
            "loop topology",
            f"the map has no closed contour at isolevel {isolevel}",
            "one closed loop",
            f"over the whole grid, whose largest value is {float(np.max(mean)):.4g}",
        )
    steps: dict[str, Canonicalisable] = {}

    def record(step: str, points: np.ndarray) -> None:

        steps[step] = {"vertices": len(points), "area_nm2": abs(signed_area(points))}

    region = assemble_region(loops)
    steps["contour"] = {
        "loops": len(loops),
        "vertices": sum(len(loop) for loop in loops),
        "area_nm2": float(region.area),
    }
    body, morphology = close_and_open(region, CLOSING_SPACINGS * spacing_nm)
    points = exterior(body)
    record("morphology", points)
    if smoothing == "taubin":
        points = resample(points, RESAMPLE_SPACINGS * spacing_nm)
        record("resampled", points)
        points = taubin(points)
        record("taubin", points)
    points = simplify(points, simplify_tol_nm)
    record("simplified", points)
    points, removed = enforce_spacing(points, spacing_nm)
    record("spacing", points)
    loop = canonical(points)
    return ConditionedContour(
        loop=loop,
        raw_loops=tuple(loops),
        record={
            "steps": steps,
            "holes_filled": morphology["holes_filled"],
            "spacing_removed": removed,
        },
    )


# -- the gate --------------------------------------------------------------------


_LOCATION = re.compile(r"\[(-?[0-9.eE+-]+) (-?[0-9.eE+-]+)\]")


def gate(
    loop: np.ndarray,
    *,
    spacing_nm: float,
    planes_nm: np.ndarray,
    probe_nm: np.ndarray,
) -> dict[str, Canonicalisable]:
    """Measure the loop against every section 5.2.1 criterion; never move it (D10).

    Parameters
    ----------
    loop
        The conditioned loop, ``(n, 2)`` in ``(r, z)`` nm.
    spacing_nm
        ``h_c``, the density grid spacing.
    planes_nm, probe_nm
        The mid-planes and the probe radius ``R_p`` on each (D11).

    Returns
    -------
    dict
        Each criterion's measured value, threshold and location, and the radius
        profile: ``z_nm``, ``probe_nm`` and ``lumen_nm`` on every plane.

    Raises
    ------
    ContourGateError
        At the first criterion that fails, naming it, the value, the threshold and
        the (r, z).
    """
    import numpy as np

    points = np.asarray(loop, dtype=np.float64)
    h_c = spacing_nm
    polygon = Polygon(points)
    if len(points) < 3 or not LinearRing(points).is_simple or not polygon.is_valid:
        reason = explain_validity(polygon) if len(points) >= 3 else "fewer than three vertices"
        found = _LOCATION.search(reason)
        where = _at(float(found.group(1)), float(found.group(2))) if found else "over the loop"
        raise ContourGateError(
            "validity and simplicity", f"the loop is not simple ({reason})", "a simple ring", where
        )

    record: dict[str, Canonicalisable] = {"h_c_nm": h_c}

    nearest = int(np.argmin(points[:, 0]))
    axis_r = float(points[nearest, 0])
    record["axis_clearance"] = {
        "value_nm": axis_r,
        "threshold_nm": h_c,
        "r_nm": axis_r,
        "z_nm": float(points[nearest, 1]),
    }
    if axis_r < h_c:
        raise ContourGateError(
            "loop topology",
            f"the loop comes within {axis_r:.4g} nm of the axis",
            f"a clearance of h_c = {h_c} nm",
            _at(axis_r, float(points[nearest, 1])),
        )

    lengths = np.linalg.norm(np.roll(points, -1, axis=0) - points, axis=1)
    edge = int(np.argmin(lengths))
    middle = 0.5 * (points[edge] + points[(edge + 1) % len(points)])
    record["vertex_spacing"] = {
        "value_nm": float(lengths[edge]),
        "threshold_nm": h_c,
        "r_nm": float(middle[0]),
        "z_nm": float(middle[1]),
    }
    if lengths[edge] < h_c:
        raise ContourGateError(
            "minimum vertex spacing",
            f"an edge is {float(lengths[edge]):.4g} nm long",
            f">= h_c = {h_c} nm",
            _at(float(middle[0]), float(middle[1])),
        )

    sizes = feature_sizes(points)
    pinch = int(np.argmin(sizes))
    record["feature_size"] = {
        "value_nm": float(sizes[pinch]),
        "threshold_nm": FEATURE_FACTOR * h_c,
        "r_nm": float(points[pinch, 0]),
        "z_nm": float(points[pinch, 1]),
    }
    if not sizes[pinch] > FEATURE_FACTOR * h_c:
        raise ContourGateError(
            "minimum local feature size",
            f"{float(sizes[pinch]):.4g} nm",
            f"> {FEATURE_FACTOR:g} h_c = {FEATURE_FACTOR * h_c:.4g} nm",
            _at(float(points[pinch, 0]), float(points[pinch, 1])),
        )

    planes = np.asarray(planes_nm, dtype=np.float64)
    probe = np.asarray(probe_nm, dtype=np.float64)
    lumen = innermost_crossings([points], planes)
    margin = lumen - probe
    record["radius_profile"] = {
        "z_nm": planes.tolist(),
        "probe_nm": probe.tolist(),
        "lumen_nm": lumen.tolist(),
    }
    measured = np.isfinite(margin)
    if not np.any(measured):
        raise ContourGateError(
            "radius profile",
            "no mid-plane between z nodes crosses the loop",
            "at least one plane",
            "over the loop's z extent",
        )
    low = int(np.nanargmin(np.where(measured, margin, np.nan)))
    high = int(np.nanargmax(np.where(measured, margin, np.nan)))
    constriction = int(np.nanargmin(np.where(measured, lumen, np.nan)))
    record["band"] = {
        "low": {"value_nm": float(margin[low]), "threshold_nm": -h_c, "z_nm": float(planes[low])},
        "high": {
            "value_nm": float(margin[high]),
            "threshold_nm": BAND_HIGH_NM,
            "z_nm": float(planes[high]),
        },
    }
    record["constriction"] = {
        "r_nm": float(lumen[constriction]),
        "z_nm": float(planes[constriction]),
    }
    if margin[low] < -h_c:
        raise ContourGateError(
            "radius profile",
            f"the lumen radius {float(lumen[low]):.4f} nm lies {float(-margin[low]):.4g} nm inside "
            f"the probe radius {float(probe[low]):.4f} nm",
            f"r_c - R_p >= -h_c = {-h_c} nm",
            _at(float(lumen[low]), float(planes[low])),
        )
    if margin[high] > BAND_HIGH_NM:
        raise ContourGateError(
            "radius profile",
            f"the lumen radius {float(lumen[high]):.4f} nm lies {float(margin[high]):.4g} nm "
            f"outside the probe radius {float(probe[high]):.4f} nm",
            f"r_c - R_p <= {BAND_HIGH_NM} nm",
            _at(float(lumen[high]), float(planes[high])),
        )
    return record


def lumen_change(
    raw_loops: Sequence[np.ndarray], loop: np.ndarray, planes_nm: np.ndarray
) -> dict[str, Canonicalisable]:
    """Return how far conditioning moved the lumen radius from the raw contour's (D5).

    The maximum and rms of ``|Δr_c|`` over the planes where both cross, and the
    change at the conditioned loop's constriction.
    """
    import numpy as np

    raw = innermost_crossings(raw_loops, planes_nm)
    final = innermost_crossings([loop], planes_nm)
    both = np.isfinite(raw) & np.isfinite(final)
    if not np.any(both):
        return {"max_nm": None, "rms_nm": None, "at_constriction_nm": None}
    change = final[both] - raw[both]
    worst = int(np.argmax(np.abs(change)))
    constriction = int(np.argmin(final[both]))
    return {
        "max_nm": float(abs(change[worst])),
        "max_z_nm": float(np.asarray(planes_nm)[both][worst]),
        "rms_nm": float(math.sqrt(float(np.mean(change * change)))),
        "at_constriction_nm": float(change[constriction]),
    }


# -- the stage -------------------------------------------------------------------


PAYLOAD_NAME = "profile"
"""The artefact's payload key; the file is ``profile.yaml``."""

CITATION = "nanopnp stage 4, SPECIFICATION.md section 5.2.1"
"""``provenance.citation`` of every profile stage 4 writes (D12)."""

WORKSPACE_DIRNAME = "tmp"
"""Directory under the store root the payload is written to when no workspace is given."""


def _specs(inputs: StageInputs) -> tuple[ContourSpec, DensitySpec]:
    """Return ``geometry.contour`` and ``geometry.density``, or refuse a case without them."""
    resolved = resolve(inputs.case)
    if resolved.contour is None or resolved.density is None:
        raise UnsupportedCaseSection(
            f"case {inputs.case.name!r} carries no structure: section, so stage 4 has no map "
            "to contour"
        )
    return resolved.contour, resolved.density


def contour_parameters(inputs: StageInputs) -> dict[str, Canonicalisable]:
    """Return the stage-4 key's parameters (D13): the block, h, the constants and the radius set."""
    contour, density = _specs(inputs)
    name = KERNEL_RADII[density.kernel]
    return {
        "contour": contour.model_dump(mode="json"),
        "h_nm": density.grid_spacing_nm,
        **KEY_CONSTANTS,
        "radius_set": {"name": name, "sha256": radius_set_digest(name)},
    }


class ContourStage:
    """Stage 4: stage 3's (r, z) mean to a conditioned, gated ``nanopnp/profile/v1`` loop."""

    name = "contour"

    def __init__(self, *, workspace: Path | None = None) -> None:
        """Build the stage.

        Parameters
        ----------
        workspace
            Directory ``profile.yaml`` is written to before the store copies it
            in. Defaults to a fresh directory under the store root.
        """
        self._workspace = Path(workspace) if workspace is not None else None

    def describe(self) -> StageDescription:
        """Return the registry's description of this stage (FR-27)."""
        return describe(self.name)

    def key(self, inputs: StageInputs) -> ProfileArtefact:
        """Return the artefact key from the block, h, the constants and stages 1 and 3."""
        return ProfileArtefact(
            parameters=contour_parameters(inputs),
            inputs={
                "structure": inputs.require("structure").hash,
                "symmetry": inputs.require("symmetry").hash,
            },
        )

    def run(
        self,
        inputs: StageInputs,
        *,
        progress: Progress | None = None,
        cancel: CancelToken | None = None,
    ) -> ProfileArtefact:
        """Extract, condition and gate the contour, and emit the stage-4 artefact.

        Raises
        ------
        ContourGateError
            At the first §5.2.1 criterion the contour fails. No artefact is
            written.
        Cancelled
            If ``cancel`` turns true. No artefact is written.
        """
        contour, density = _specs(inputs)
        key = self.key(inputs)
        structure = inputs.require("structure")
        symmetry = inputs.require("symmetry")
        h = density.grid_spacing_nm

        check_cancelled(cancel, "reading the reduced map")
        report(progress, 0.0, "reading the reduced map")
        reduced = ReducedMap.read(symmetry.payload[REDUCED_PAYLOAD])
        conditioned = condition(
            reduced.mean,
            reduced.r_nm,
            reduced.z_nm,
            spacing_nm=h,
            isolevel=contour.isolevel,
            smoothing=contour.smoothing,
            simplify_tol_nm=contour.simplify_tol_nm,
        )
        loop = conditioned.loop
        report(progress, 0.1, f"contour conditioned to {len(loop)} vertices")

        check_cancelled(cancel, "reading the aligned ensemble")
        ensemble = AlignedEnsemble.read(structure.payload[ENSEMBLE_PAYLOAD])
        radii = resolve_radii(
            KERNEL_RADII[density.kernel],
            resname=ensemble.resname,
            atom=ensemble.name,
            chain=ensemble.chain,
            resid=ensemble.resid,
            icode=ensemble.icode,
        )
        planes = mid_planes([loop], reduced.z_nm)

        def scaled(fraction: float, message: str) -> None:
            report(progress, 0.15 + 0.8 * fraction, message)

        probe = probe_radius_profile(
            ensemble.positions_nm, radii.radii_nm, planes, progress=scaled, cancel=cancel
        )
        checked = gate(loop, spacing_nm=h, planes_nm=planes, probe_nm=probe)
        change = lumen_change(conditioned.raw_loops, loop, planes)

        digest = reduced.digest()
        profile = PoreProfile(
            schema=PROFILE_SCHEMA,
            name=f"contour-{key.hash[:12]}",
            description=(
                f"The isolevel-{contour.isolevel:g} contour of stage 3's mean, conditioned and "
                "gated by stage 4, in the stage-1 frame"
            ),
            provenance=ProfileProvenance(
                source=PIPELINE_SOURCE,
                citation=CITATION,
                sha256=digest,
                vertex_count=len(loop),
                min_vertex_spacing_nm=min_vertex_spacing(loop),
                min_feature_size_nm=min_feature_size(loop),
                signed_area_nm2=signed_area(loop),
            ),
            vertices=[(float(r), float(z)) for r, z in loop],
        )
        directory = self._workspace
        if directory is None:
            root = store_root() / WORKSPACE_DIRNAME
            root.mkdir(parents=True, exist_ok=True)
            directory = Path(tempfile.mkdtemp(prefix="contour-", dir=root))
        path = write_profile(profile, directory / f"{PAYLOAD_NAME}.yaml")
        logger.info(
            "contour: %d vertices, spacing %.4f nm, feature size %.4f nm, band [%+.3f, %+.3f] nm, "
            "constriction %.3f nm at z = %.2f nm",
            len(loop),
            profile.provenance.min_vertex_spacing_nm,
            profile.provenance.min_feature_size_nm,
            checked["band"]["low"]["value_nm"],
            checked["band"]["high"]["value_nm"],
            checked["constriction"]["r_nm"],
            checked["constriction"]["z_nm"],
        )
        report(progress, 1.0, "contour written")
        summary: dict[str, Canonicalisable] = {
            "isolevel": contour.isolevel,
            "smoothing": contour.smoothing,
            "simplify_tol_nm": contour.simplify_tol_nm,
            "h_c_nm": h,
            "vertex_count": len(loop),
            "min_vertex_spacing_nm": profile.provenance.min_vertex_spacing_nm,
            "min_feature_size_nm": profile.provenance.min_feature_size_nm,
            "signed_area_nm2": profile.provenance.signed_area_nm2,
            "holes_filled": conditioned.record["holes_filled"],
            "band": checked["band"],
            "constriction": checked["constriction"],
            "conditioning": {**conditioned.record, "lumen_change": change},
            "gate": checked,
            "radius_set": {"name": radii.name, "sha256": radii.sha256},
            "reduced_payload_digest": digest,
        }
        return ProfileArtefact(
            parameters=key.parameters,
            inputs=key.inputs,
            payload={PAYLOAD_NAME: path},
            summary=summary,
        )
