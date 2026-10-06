"""Stage 5 of section 5.2: CAD assembly of any pore profile into the tagged region (FR-09).

The profile arrives from stage 4 or from ``inputs.profile``, in the structure's
frame. Stage 5 puts a reservoir and a bilayer around it and emits a
**declarative record** of the result (section 5.3.2 row 5): the model-frame
profile, the membrane with its derived inner edge, the reservoir radius, the axis
split, and the face areas and edge-name counts the assembly measured.
:func:`build_region` rebuilds the glued, named OCC shape from that record alone,
so the artefact hashes by content where a BRep's bytes need not be stable.

The steps, each from the section 5.2.1 NOTE on the membrane junction on any
profile (WP21 D2-D6):

1. **Model frame.** ``z <- z - geometry.membrane.centre_z_nm``, applied to every
   vertex before anything else, for a stage-4 and a supplied profile alike.
2. **The lumen-adjacent intervals.** On each bilayer plane ``z = +/-t/2`` the
   body interval ``[r1, r2]`` bounded by the profile's two smallest crossings.
3. **The inner edge.** The chord from the lower plane's interval to the upper
   plane's with the largest minimum distance to the profile, over the 63 x 63
   interior points ``r1 + (r2 - r1) k / 64``. Any chord with its ends in those
   intervals that stays inside the body yields the same region (the NOTE gives
   the argument), so the widest-margin one is taken as the choice furthest from
   every failure. The chord between the intervals' mid-points is **not** such a
   chord in general: on the reference fixture it crosses the cleft under the cap
   and splits the electrolyte in two.
4. **Assembly.** The membrane is the quadrilateral from the chord out past the
   reservoir, clipped to the half-disc and cut by the pore body; the
   electrolyte is what the half-disc has left. ``Glue`` makes every seam one
   node chain (VER-28).
5. **Naming, topologically.** An edge of the pore body is ``interface`` where it
   also bounds the membrane and ``wall`` where it bounds the electrolyte; an
   edge shared by membrane and electrolyte is ``membrane``; the reservoir arc
   is ``membrane_outer`` where it bounds the membrane and ``cis`` or ``trans``
   elsewhere; ``r = 0`` is ``axis``. Read from the glued shape's own adjacency,
   this is exact on any profile, where a test of position against the chord
   would be a heuristic that happens to agree.

The junction gate aborts naming the criterion, the value, the threshold and the
``(r, z)`` (QR-12). Every threshold is a constant that keys the artefact, and
none is a case key.
"""

from __future__ import annotations

import logging
import math
import tempfile
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from nanopnp.core.hashing import Canonicalisable
from nanopnp.core.paths import store_root
from nanopnp.core.stages import (
    CancelToken,
    MissingExtraError,
    Progress,
    StageDescription,
    check_cancelled,
    describe,
    report,
)
from nanopnp.geometry.profile import (
    PoreProfile,
    load_profile,
    min_vertex_spacing,
    plane_crossings,
    profile_digest,
    signed_area,
)
from nanopnp.geometry.tolerance import TOL_NM
from nanopnp.io.artefact import RegionArtefact
from nanopnp.io.case import (
    MembraneSpec,
    ReservoirSpec,
    UnsupportedCaseSection,
)

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

    from nanopnp.core.typing import Shape
    from nanopnp.io.artefact import StageInputs
    from nanopnp.io.resolved import ResolvedCase

logger = logging.getLogger(__name__)

REGION_SCHEMA = "nanopnp/region/v1"
"""Stage 5's record: the same string as :data:`nanopnp.io.artefact.REGION_SCHEMA`."""

CHORD_DIVISIONS = 64
"""The chord search divides each lumen-adjacent interval into this many parts.

Its 63 interior points include each interval's mid-point (``k = 32``), so a
symmetric body's optimum is on the grid exactly.
"""

JUNCTION_CLEARANCE_NM = 0.01
"""The least clearance the best chord may have to the profile, in nm (WP21 D4).

10^5 times OCC's confusion tolerance, and a fifth of the smallest half-thickness
a stage-4 body can have, h = 0.05 nm. Measured clearances are 0.2365 nm on the
reference fixture and about 0.30 nm on 2WCD's stage-4 profile.
"""

MEMBRANE_OVERSHOOT = "half_thickness"
"""How far past the reservoir radius the membrane quadrilateral is traced.

Ending it exactly on ``r = R`` makes its outer edge touch the reservoir arc at
the single point ``(R, 0)`` rather than crossing it, a boolean the mesher would
have to resolve exactly for no gain. One membrane half-thickness removes the
contact and scales with the geometry.
"""

KEY_CONSTANTS: Mapping[str, Canonicalisable] = {
    "chord_divisions": CHORD_DIVISIONS,
    "junction_clearance_nm": JUNCTION_CLEARANCE_NM,
    "junction_tolerance_nm": TOL_NM,
    "membrane_overshoot": MEMBRANE_OVERSHOOT,
}
"""Every code constant that moves a vertex of the region or a verdict of its gate (D5)."""

PAYLOAD_NAME = "region"
"""The artefact's payload key; the file is ``region.yaml``."""

WORKSPACE_DIRNAME = "tmp"
"""Directory under the store root the payload is written to when no workspace is given."""

DOMAINS: tuple[str, str, str] = ("electrolyte", "membrane", "protein")
"""The region's three domains, in assembly order (VER-28)."""

EXCLUSION = "exclusion"
"""The fourth domain, the ion-exclusion shell, present only with ``a > 0`` (FR-15, WP30)."""

EXCLUSION_QUAD_SEGS = 8
"""Segments per quarter circle of the offset's round joins (WP20 D5, WP30 D7)."""

EXCLUSION_CLOSING = 2.0
"""The offset's closing radius, in units of ``h_c``: step 3 of section 5.2.1's, for its reason."""

EXCLUSION_RESAMPLE = 1.05
"""The ring's resampling arc length is at least this many ``h_c`` (WP30 Outcomes).

Uniform, at ``L / floor(L / (1.05 h_c))``, before step 6. At 8 segments a
quarter circle's chords are ``a pi/16``, just under ``h_c`` at ``a`` = 0.25 nm,
and step 6 merges runs of them into chords near ``3 h_c``, deeper inside the
offset than the thickness bound allows: 0.0106 nm on a rectangle, against 0.01
[tested]. Resampled at 1.05 ``h_c`` every chord stays above ``h_c``, even round a
join of radius ``2 h_c``, so step 6 has nothing to merge. The factor is no
larger because an edge must stay near the default wall target, 0.05 nm: netgen
leaves an edge of 1.5 times its size target as one segment, and the wall-size
gate then refuses the mesh [tested]. Below that target stage 6 cuts each edge
into equal segments (:data:`nanopnp.mesh.sizing.EXCLUSION_WALL_DIVISION`).
"""

EXCLUSION_CONSTANTS: Mapping[str, Canonicalisable] = {
    "join": "round",
    "quad_segs": EXCLUSION_QUAD_SEGS,
    "closing": f"{EXCLUSION_CLOSING:g}h_c",
    "holes": "filled",
    "resample": f"L/floor(L/{EXCLUSION_RESAMPLE:g}h_c)",
    "spacing": "h_c",
    "axis_clearance": "h_c",
    "inner_bound": "max(h_c^2/a, a/100)",
}
"""Every code constant that moves a vertex of the shell or a verdict of its gate (WP30 D10).

In the stage-5 key only when the shell is built, beside the offset and ``h_c``,
so that :data:`KEY_CONSTANTS`, and with it every shell-free key, is unchanged.
"""

_ARC_RTOL = 1e-9
"""Relative tolerance for deciding that a point lies on the reservoir arc."""


class RegionGateError(ValueError):
    """Stage 5's region failed a junction criterion (FR-09, QR-12).

    Names the criterion, what was measured, the threshold and where, and is
    classified with the gates: the case is well formed, and the profile and
    membrane it names do not assemble into the region section 5.2.1 describes.

    Parameters
    ----------
    criterion
        The §5.2.1 NOTE's criterion, e.g. ``"chord clearance"``.
    measured
        The measured value, with units.
    threshold
        What it was held to, with units.
    where
        The location: an ``(r, z)``, a plane, or a list of faces.
    """

    def __init__(self, criterion: str, measured: str, threshold: str, where: str) -> None:
        self.criterion = criterion
        self.measured = measured
        self.threshold = threshold
        self.where = where
        super().__init__(
            f"stage 5 junction gate, {criterion}: {measured}, against {threshold}, {where} "
            "(section 5.2.1 NOTE on the membrane junction on any profile, FR-09)"
        )


def _at(r_nm: float, z_nm: float) -> str:
    """Format a location for a gate message."""
    return f"at (r, z) = ({r_nm:.4f}, {z_nm:.4f}) nm"


# -- the record --------------------------------------------------------------------


class _Strict(BaseModel):
    """Base for the record's blocks: unknown keys are rejected, naming them."""

    model_config = ConfigDict(extra="forbid")


class MembraneRecord(_Strict):
    """The bilayer as assembled: its slab, its frame shift and its inner edge.

    Parameters
    ----------
    thickness_nm, centre_z_nm
        ``geometry.membrane``; ``centre_z_nm`` is the shift into the model frame.
    inner_trans_nm, inner_cis_nm
        The inner edge's radii on ``z = -t/2`` and ``z = +t/2``.
    clearance_nm
        The inner edge's least distance to the profile; ``None`` for a drawn
        edge, which was not searched for.
    """

    thickness_nm: float
    centre_z_nm: float
    inner_trans_nm: float
    inner_cis_nm: float
    clearance_nm: float | None = None

    @property
    def half_thickness_nm(self) -> float:
        """Half the bilayer thickness; the membrane spans ``+/- this``."""
        return 0.5 * self.thickness_nm


class FilledHoles(_Strict):
    """The pockets of fluid the offset enclosed, which no ion can reach, filled and recorded."""

    count: int
    area_nm2: float
    centroids_nm: list[tuple[float, float]] = Field(default_factory=list)


class ExclusionRecord(_Strict):
    """The ion-exclusion shell's outer loop and what its construction measured (WP30 D10).

    Parameters
    ----------
    offset_nm
        ``charge.exclusion_offset_nm``, ``a``.
    h_c_nm
        The contour's size target, the density grid spacing.
    constants
        :data:`EXCLUSION_CONSTANTS`.
    loop
        The offset's outer ring ``O`` in the model frame, after the closing, the
        hole filling and step 6, in nm. Stage 6 rebuilds the shell from it, so
        no Shapely is needed there.
    holes
        The pockets the offset enclosed and step 3 filled.
    removed_vertices
        How many vertices step 6 removed.
    distance_nm
        ``[min, max]`` distance to the profile: the least over the loop's edges,
        exactly, which is ``a`` less the sagitta of the longest merged chord, and
        the greatest over its vertices, which exceeds ``a`` where the closing
        filled a groove.
    """

    offset_nm: float
    h_c_nm: float
    constants: dict[str, Canonicalisable]
    loop: list[tuple[float, float]]
    holes: FilledHoles
    removed_vertices: int
    distance_nm: tuple[float, float]

    def points(self) -> np.ndarray:
        """Return the loop as an ``(n, 2)`` float64 array."""
        import numpy as np

        return np.asarray(self.loop, dtype=np.float64).reshape(-1, 2)

    def summary(self) -> dict[str, Canonicalisable]:
        """Return the shell's entry in the manifest's Geometry group."""
        return {
            "offset_nm": self.offset_nm,
            "h_c_nm": self.h_c_nm,
            "loop_vertices": len(self.loop),
            "removed_vertices": self.removed_vertices,
            "holes": self.holes.model_dump(mode="json"),
            "distance_nm": list(self.distance_nm),
        }


class RegionRecord(_Strict):
    """Stage 5's artefact: everything :func:`build_region` needs, and what it measured.

    Parameters
    ----------
    schema_id
        :data:`REGION_SCHEMA`.
    profile
        The pore polygon's vertices in the model frame, in nm, in the profile's
        own order and orientation.
    membrane
        The bilayer, with its inner edge.
    reservoir_radius_nm
        The half-disc's radius.
    axis_split_nm
        Where the axis is split: the profile's model-frame z extent, over which
        section 5.2.2's axis-in-pore size applies.
    junction_nm
        ``{"trans": r2, "cis": r2}``: the lumen-adjacent interval's outer end on
        each plane, which is where the membrane meets the body.
    face_areas_nm2
        Each domain's area, as assembled.
    edge_counts
        Each boundary name's count of unique edges, as assembled.
    exclusion
        The ion-exclusion shell, or ``None`` without one. Omitted from the
        written record when absent, so a shell-free record's bytes are those of
        a record written before the shell existed (WP30 D10).
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_id: str = Field(alias="schema", default=REGION_SCHEMA)
    profile: list[tuple[float, float]]
    membrane: MembraneRecord
    reservoir_radius_nm: float
    axis_split_nm: tuple[float, float]
    junction_nm: dict[str, float]
    face_areas_nm2: dict[str, float] = Field(default_factory=dict)
    edge_counts: dict[str, int] = Field(default_factory=dict)
    exclusion: ExclusionRecord | None = None

    def points(self) -> np.ndarray:
        """Return the model-frame profile as an ``(n, 2)`` float64 array."""
        import numpy as np

        return np.asarray(self.profile, dtype=np.float64).reshape(-1, 2)

    def summary(self) -> dict[str, Canonicalisable]:
        """Return what the manifest's Geometry group records as ``region`` (WP21 D16).

        The shell's entry is there only when the region has one.
        """
        summary: dict[str, Canonicalisable] = {
            "frame_shift_nm": self.membrane.centre_z_nm,
            "thickness_nm": self.membrane.thickness_nm,
            "reservoir_radius_nm": self.reservoir_radius_nm,
            "chord": {
                "trans_nm": self.membrane.inner_trans_nm,
                "cis_nm": self.membrane.inner_cis_nm,
                "clearance_nm": self.membrane.clearance_nm,
            },
            "junction_nm": dict(sorted(self.junction_nm.items())),
            "axis_split_nm": list(self.axis_split_nm),
            "face_areas_nm2": dict(sorted(self.face_areas_nm2.items())),
            "edge_counts": dict(sorted(self.edge_counts.items())),
            "profile_vertices": len(self.profile),
        }
        if self.exclusion is not None:
            summary["exclusion"] = self.exclusion.summary()
        return summary


def write_region(record: RegionRecord, path: Path) -> Path:
    """Write ``record`` as ``nanopnp/region/v1`` YAML that :func:`read_region` reads back.

    Floats are written as Python's shortest round-trip representation, so the
    vertices read back bit for bit and the rebuilt region is the one measured.
    """
    document = record.model_dump(by_alias=True, mode="json")
    document["profile"] = [[float(r), float(z)] for r, z in record.profile]
    if record.exclusion is None:
        del document["exclusion"]
    else:
        document["exclusion"]["loop"] = [[float(r), float(z)] for r, z in record.exclusion.loop]
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(document, sort_keys=False, default_flow_style=None, width=100)
    path.write_text(text, encoding="utf-8")
    return path


def read_region(path: Path) -> RegionRecord:
    """Read a ``nanopnp/region/v1`` record.

    Raises
    ------
    ValueError
        If the document declares another schema, naming the file and the schema.
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    schema = raw.get("schema") if isinstance(raw, dict) else None
    if schema != REGION_SCHEMA:
        raise ValueError(f"{path}: expected schema {REGION_SCHEMA!r}, found {schema!r}")
    return RegionRecord.model_validate(raw)


# -- the junction: geometry on arrays -------------------------------------------------


def to_model_frame(points: np.ndarray, centre_z_nm: float) -> np.ndarray:
    """Return ``points`` moved into the model frame, ``z <- z - centre_z_nm`` (D2)."""
    shifted = points.copy()
    shifted[:, 1] = shifted[:, 1] - centre_z_nm
    return shifted


def lumen_interval(points: np.ndarray, z_nm: float, *, centre_z_nm: float) -> tuple[float, float]:
    """Return the lumen-adjacent body interval ``[r1, r2]`` on the plane ``z = z_nm``.

    Raises
    ------
    RegionGateError
        If the plane crosses the profile fewer than twice, naming the profile's
        model-frame z extent and ``centre_z_nm``: the membrane then does not
        meet the body on that plane at all.
    """
    crossings = plane_crossings(points, z_nm)
    if len(crossings) < 2:
        lower, upper = float(points[:, 1].min()), float(points[:, 1].max())
        raise RegionGateError(
            "bilayer plane crossings",
            f"{len(crossings)} crossings of z = {z_nm:+.4f} nm",
            "at least 2",
            f"with the profile spanning z = [{lower:.4f}, {upper:.4f}] nm in the model frame "
            f"after geometry.membrane.centre_z_nm = {centre_z_nm:g} nm",
        )
    import numpy as np

    # The half-open test counts one end of an edge lying on the plane; the body's
    # section runs on along it, and the membrane meets the body at the far end.
    following = np.roll(points, -1, axis=0)
    flat = [
        (min(a[0], b[0]), max(a[0], b[0]))
        for a, b in zip(points, following, strict=True)
        if a[1] == z_nm and b[1] == z_nm
    ]
    r2, grown = crossings[1], True
    while grown:
        grown = False
        for low, high in flat:
            if low <= r2 < high:
                r2, grown = float(high), True
    return crossings[0], r2


def _point_segment_distance(p: np.ndarray, s0: np.ndarray, s1: np.ndarray) -> np.ndarray:
    """Return the distance from each point to each segment, broadcasting."""
    import numpy as np

    span = s1 - s0
    length_squared = np.sum(span * span, axis=-1)
    safe = np.where(length_squared > 0.0, length_squared, 1.0)
    parameter = np.clip(np.sum((p - s0) * span, axis=-1) / safe, 0.0, 1.0)
    nearest = s0 + parameter[..., None] * span
    difference = p - nearest
    distance: np.ndarray = np.sqrt(np.sum(difference * difference, axis=-1))
    return distance


def _orientation(p: np.ndarray, q: np.ndarray, r: np.ndarray) -> np.ndarray:
    """Return the signed area of the triangle ``pqr``, broadcasting."""
    orientation: np.ndarray = (q[..., 0] - p[..., 0]) * (r[..., 1] - p[..., 1]) - (
        q[..., 1] - p[..., 1]
    ) * (r[..., 0] - p[..., 0])
    return orientation


def chord_clearances(starts: np.ndarray, ends: np.ndarray, points: np.ndarray) -> np.ndarray:
    """Return each chord's least distance to the closed polygon ``points``, in nm.

    Zero for a chord that crosses an edge of the polygon. Otherwise the segment
    distance is attained at an endpoint of one of the two segments, so it is the
    least of four point-to-segment distances.

    Parameters
    ----------
    starts, ends
        ``(k, 2)`` chord endpoints.
    points
        ``(n, 2)`` polygon vertices, the closing edge implied.
    """
    import numpy as np

    a0, a1 = starts[:, None, :], ends[:, None, :]
    b0 = points[None, :, :]
    b1 = np.roll(points, -1, axis=0)[None, :, :]
    distance = np.minimum.reduce(
        [
            _point_segment_distance(a0, b0, b1),
            _point_segment_distance(a1, b0, b1),
            _point_segment_distance(b0, a0, a1),
            _point_segment_distance(b1, a0, a1),
        ]
    )
    crossing = (_orientation(a0, a1, b0) * _orientation(a0, a1, b1) < 0.0) & (
        _orientation(b0, b1, a0) * _orientation(b0, b1, a1) < 0.0
    )
    clearance: np.ndarray = np.where(crossing, 0.0, distance).min(axis=1)
    return clearance


def best_chord(
    points: np.ndarray,
    trans: tuple[float, float],
    cis: tuple[float, float],
    half_thickness_nm: float,
) -> tuple[float, float, float]:
    """Return the widest-margin inner edge: ``(r_trans, r_cis, clearance)`` in nm (D3).

    Searched over the 63 x 63 interior grid points of the two lumen-adjacent
    intervals. The first maximum in grid order wins a tie, so the choice is a
    function of the profile alone.

    Parameters
    ----------
    points
        The model-frame profile.
    trans, cis
        ``[r1, r2]`` on ``z = -t/2`` and ``z = +t/2``.
    half_thickness_nm
        ``t/2``.
    """
    import numpy as np

    fractions = np.arange(1, CHORD_DIVISIONS) / CHORD_DIVISIONS
    lower = trans[0] + (trans[1] - trans[0]) * fractions
    upper = cis[0] + (cis[1] - cis[0]) * fractions
    grid_lower, grid_upper = np.meshgrid(lower, upper, indexing="ij")
    count = grid_lower.size
    starts = np.stack([grid_lower.ravel(), np.full(count, -half_thickness_nm)], axis=1)
    ends = np.stack([grid_upper.ravel(), np.full(count, half_thickness_nm)], axis=1)
    clearance = chord_clearances(starts, ends, points)
    best = int(np.argmax(clearance))
    return float(starts[best, 0]), float(ends[best, 0]), float(clearance[best])


def _check_inside_reservoir(points: np.ndarray, radius_nm: float) -> None:
    """Abort unless every model-frame vertex is strictly inside the reservoir disc."""
    import numpy as np

    distances = np.hypot(points[:, 0], points[:, 1])
    worst = int(np.argmax(distances))
    if not distances[worst] < radius_nm:
        raise RegionGateError(
            "profile inside the reservoir",
            f"a vertex at distance {float(distances[worst]):.4f} nm from the origin",
            f"strictly below the reservoir radius {radius_nm:g} nm",
            _at(float(points[worst, 0]), float(points[worst, 1])) + " in the model frame",
        )


# -- the ion-exclusion shell (WP30) ------------------------------------------------------


def distance_to_segments(points: np.ndarray, segments: np.ndarray) -> np.ndarray:
    """Return each point's least distance to the ``(k, 2, 2)`` segments, in nm."""
    distance: np.ndarray = _point_segment_distance(
        points[:, None, :], segments[None, :, 0, :], segments[None, :, 1, :]
    ).min(axis=1)
    return distance


def distance_to_loop(points: np.ndarray, loop: np.ndarray) -> np.ndarray:
    """Return each point's least distance to the closed polygon ``loop``, in nm."""
    import numpy as np

    return distance_to_segments(points, np.stack([loop, np.roll(loop, -1, axis=0)], axis=1))


def _missing_shapely(error: ImportError) -> MissingExtraError:
    """Return the refusal of an exclusion shell without the ``structure`` extra (WP30 D7)."""
    missing = getattr(error, "name", None) or "shapely"
    return MissingExtraError(
        f"charge.exclusion_offset_nm builds the ion-exclusion shell by offsetting the profile "
        f"with Shapely, which is in the 'structure' extra: importing {missing!r} failed. Install "
        "the extras with `uv sync --all-extras`, or set charge.exclusion_offset_nm: 0 (section "
        "5.2.1 NOTE on the ion-exclusion shell)",
        name=missing,
    )


def exclusion_shell(
    points: np.ndarray, offset_nm: float, h_c_nm: float, *, reservoir_radius_nm: float
) -> ExclusionRecord:
    """Return the ion-exclusion shell's outer loop, built and gated (section 5.2.1 NOTE, WP30 D7).

    1. ``O``, the dilation of the profile by ``a``, with round joins at
       :data:`EXCLUSION_QUAD_SEGS` segments per quarter circle;
    2. closed by a disc of radius ``2 h_c``, as step 3 of section 5.2.1;
    3. every hole filled and recorded: fluid enclosed by the shell, which no ion
       can reach;
    4. its ring resampled at uniform arc length no shorter than
       :data:`EXCLUSION_RESAMPLE` ``h_c``, then step 6 of section 5.2.1;
    5. the ring's validity, simplicity and spacing, its clearance of ``h_c`` from
       the axis, every vertex strictly inside the reservoir disc, and every edge
       at least ``a - max(h_c^2/a, a/100)`` from the body.

    The last is a gate as well as an argument. A ring at least ``2 pi a > 4 pi h_c``
    long is cut into at least 11 arcs, so its chords are ``s < 1.15 h_c``, and
    they sit at most ``a (1 - cos(pi/32)) + s^2/(8a)`` inside the offset. That
    is within the bound for every ``a`` (WP30 Outcomes) [verified].

    Parameters
    ----------
    points
        The model-frame profile ``P``.
    offset_nm
        ``a``, positive; the case resolver has refused ``a <= 2 h_c``.
    h_c_nm
        The contour's size target.
    reservoir_radius_nm
        The disc every vertex must lie strictly inside.

    Raises
    ------
    RegionGateError
        Naming the criterion, the value, the threshold and where: an offset
        within ``h_c`` of the axis, which closes the constriction, with the z
        interval and the body's least radius over it; a vertex outside the
        reservoir; a ring that is invalid, not simple or more than one face; an
        edge closer to the body than the inner bound.
    MissingExtraError
        Without Shapely, naming the ``structure`` extra and the key.
    """
    try:
        from shapely import box
        from shapely.geometry import LinearRing, MultiPolygon, Polygon

        from nanopnp.geometry.contour import enforce_spacing, resample
    except ImportError as error:
        raise _missing_shapely(error) from error
    import numpy as np

    body = Polygon(points)
    radius = EXCLUSION_CLOSING * h_c_nm
    dilated = body.buffer(offset_nm, quad_segs=EXCLUSION_QUAD_SEGS)
    closed = dilated.buffer(radius, quad_segs=EXCLUSION_QUAD_SEGS).buffer(
        -radius, quad_segs=EXCLUSION_QUAD_SEGS
    )
    if isinstance(closed, MultiPolygon) or not isinstance(closed, Polygon):
        parts = list(getattr(closed, "geoms", [closed]))
        raise RegionGateError(
            "exclusion offset topology",
            f"{len(parts)} components after the offset by {offset_nm:g} nm and its closing",
            "one face",
            "with centroids "
            + "; ".join(f"({part.centroid.x:.4f}, {part.centroid.y:.4f}) nm" for part in parts),
        )
    holes = [Polygon(ring) for ring in closed.interiors]
    outer = Polygon(closed.exterior)

    lowest = float(outer.bounds[0])
    if lowest < h_c_nm:
        coordinates = np.asarray(outer.exterior.coords, dtype=np.float64)
        near = coordinates[coordinates[:, 0] < h_c_nm]
        z_low, z_high = float(near[:, 1].min()), float(near[:, 1].max())
        band = body.intersection(box(-1.0, z_low, 2.0 * reservoir_radius_nm, z_high))
        least = float(band.bounds[0]) if not band.is_empty else float(body.bounds[0])
        raise RegionGateError(
            "exclusion offset clears the axis",
            f"the offset by a = {offset_nm:g} nm reaches r = {lowest:.4f} nm, closing the "
            f"constriction over z = [{z_low:.4f}, {z_high:.4f}] nm, where the body's least radius "
            f"is {least:.4f} nm",
            f"r >= h_c = {h_c_nm:g} nm, so a body radius of at least a + h_c = "
            f"{offset_nm + h_c_nm:.4f} nm",
            f"over z = [{z_low:.4f}, {z_high:.4f}] nm in the model frame",
        )

    ring = np.asarray(outer.exterior.coords, dtype=np.float64)[:-1]
    length = float(np.linalg.norm(np.roll(ring, -1, axis=0) - ring, axis=1).sum())
    count = max(3, math.floor(length / (EXCLUSION_RESAMPLE * h_c_nm)))
    ring, removed = enforce_spacing(resample(ring, length / count), h_c_nm)
    linear = LinearRing(ring)
    if not (linear.is_valid and linear.is_simple):
        raise RegionGateError(
            "exclusion ring validity",
            "an invalid or self-intersecting ring after step 6",
            "LinearRing.is_valid and is_simple",
            "over the whole offset loop",
        )
    spacing = min_vertex_spacing(ring)
    if spacing < h_c_nm:  # pragma: no cover - enforce_spacing stops only at 3 vertices
        raise RegionGateError(
            "exclusion ring spacing", f"{spacing:.4g} nm", f">= h_c = {h_c_nm:g} nm", "on the ring"
        )
    _check_inside_reservoir(ring, reservoir_radius_nm)
    following = np.roll(ring, -1, axis=0)
    # Exact for a segment against a polygon: the least of four endpoint distances,
    # or zero where they cross (chord_clearances).
    clearance = chord_clearances(ring, following, points)
    nearest = int(np.argmin(clearance))
    bound = offset_nm - max(h_c_nm**2 / offset_nm, offset_nm / 100.0)
    if not clearance[nearest] >= bound:
        r_mid, z_mid = 0.5 * (ring[nearest] + following[nearest])
        raise RegionGateError(
            "exclusion shell thickness",
            f"an outer-surface edge {float(clearance[nearest]):.5f} nm from the body",
            f"at least a - max(h_c^2/a, a/100) = {bound:.5f} nm",
            _at(float(r_mid), float(z_mid)),
        )
    distance = distance_to_loop(ring, points)
    return ExclusionRecord(
        offset_nm=offset_nm,
        h_c_nm=h_c_nm,
        constants=dict(EXCLUSION_CONSTANTS),
        loop=[(float(r), float(z)) for r, z in ring],
        holes=FilledHoles(
            count=len(holes),
            area_nm2=float(sum(hole.area for hole in holes)),
            centroids_nm=[(float(hole.centroid.x), float(hole.centroid.y)) for hole in holes],
        ),
        removed_vertices=removed,
        distance_nm=(float(clearance.min()), float(distance.max())),
    )


# -- the junction: assembly in OCC --------------------------------------------------------


def _pore_face(points: np.ndarray) -> Shape:
    """Return the profile as a face, counter-clockwise.

    A clockwise wire gives OCC a face of negative area, and a negative face is
    not merely upside down: it subtracts as an addition, so ``disc - quad``
    returns the disc split in two rather than the disc with a hole [tested]. The
    delivered ClyA table and every stage-4 loop run clockwise, so orientation is
    fixed here, once.
    """
    import netgen.occ as occ

    vertices = points[::-1] if signed_area(points) < 0.0 else points
    plane = occ.WorkPlane().MoveTo(float(vertices[0][0]), float(vertices[0][1]))
    for radius, height in vertices[1:]:
        plane = plane.LineTo(float(radius), float(height))
    return plane.Close().Face()


def _reservoir_face(radius_nm: float, axis_split_nm: tuple[float, float]) -> Shape:
    """Return the reservoir half-disc, its side on ``r = 0`` split at the pore's extent.

    The clipping box is traced by hand rather than taken from ``Rectangle`` so
    that its side on ``r = 0`` is broken into three collinear segments at the
    pore's axial extent. OCC keeps collinear segments as separate edges, and that
    is the only way section 5.2.2's axis-in-pore size can be a size field at all:
    the pore polygon never touches the axis, so nothing else splits it.

    The half-disc's arc carries one vertex the construction did not ask for.
    ``Circle(...).Face()`` is a single closed edge whose seam OCC places at
    ``(R, 0)``, and clipping keeps it, so the arc between the membrane's outer
    corners is two arcs, both ``membrane_outer`` [tested].
    """
    import netgen.occ as occ

    lower, upper = axis_split_nm
    disc = occ.WorkPlane().Circle(0.0, 0.0, radius_nm).Face()
    box = (
        occ.WorkPlane()
        .MoveTo(0.0, -radius_nm)
        .LineTo(radius_nm, -radius_nm)
        .LineTo(radius_nm, radius_nm)
        .LineTo(0.0, radius_nm)
        .LineTo(0.0, upper)
        .LineTo(0.0, lower)
        .Close()
        .Face()
    )
    return disc * box


def _membrane_face(membrane: MembraneRecord, radius_nm: float) -> Shape:
    """Return the membrane quadrilateral, counter-clockwise, traced past the reservoir.

    Its inner edge runs from ``(inner_trans, -t/2)`` to ``(inner_cis, +t/2)``,
    and its outer edge sits :data:`MEMBRANE_OVERSHOOT` beyond the reservoir
    radius; the intersection with the half-disc clips it back.
    """
    import netgen.occ as occ

    half = membrane.half_thickness_nm
    outer = radius_nm + half
    return (
        occ.WorkPlane()
        .MoveTo(membrane.inner_trans_nm, -half)
        .LineTo(outer, -half)
        .LineTo(outer, half)
        .LineTo(membrane.inner_cis_nm, half)
        .Close()
        .Face()
    )


def assemble_faces(record: RegionRecord) -> tuple[Shape, ...]:
    """Return the named faces, electrolyte, membrane, pore and any shell, unglued.

    The booleans are the assembly: the membrane is the quadrilateral clipped to
    the reservoir and cut by the pore body, and the electrolyte is what the
    half-disc has left once both are removed. With an exclusion shell, whose
    outer loop is ``O``, the shell is ``O - P - M`` and the electrolyte
    ``D - M - O``; the membrane is unchanged (section 5.2.1 NOTE on the
    ion-exclusion shell). Names are set after the booleans, because a face's name
    does not survive being cut.

    Raises
    ------
    RegionGateError
        If any domain assembled as other than one face, naming each face's
        centroid and area.
    """
    pore = _pore_face(record.points())
    disc = _reservoir_face(record.reservoir_radius_nm, record.axis_split_nm)
    quad = _membrane_face(record.membrane, record.reservoir_radius_nm)

    membrane = (quad * disc) - pore
    named: tuple[tuple[Shape, str], ...]
    if record.exclusion is None:
        electrolyte = (disc - quad) - pore
        named = ((electrolyte, "electrolyte"), (membrane, "membrane"), (pore, "protein"))
    else:
        offset = _pore_face(record.exclusion.points())
        shell = (offset - pore) - quad
        # ``O`` contains ``P`` by construction; the pore is cut as well so that a
        # loop that does not (a record edited by hand, FR-27) leaves no
        # electrolyte overlapping the protein, and the naming gate sees the edge.
        electrolyte = ((disc - quad) - offset) - pore
        named = (
            (electrolyte, "electrolyte"),
            (membrane, "membrane"),
            (pore, "protein"),
            (shell, EXCLUSION),
        )
    for face, name in named:
        face.name = name
    for shape, name in named:
        faces = list(shape.faces)
        if len(faces) != 1:
            listed = "; ".join(
                f"centroid ({float(face.center[0]):.4f}, {float(face.center[1]):.4f}) nm, "
                f"area {float(face.mass):.6g} nm^2"
                for face in faces
            )
            raise RegionGateError(
                f"{name} domain topology",
                f"{len(faces)} faces",
                "exactly one",
                f"the faces being {listed or 'none'}",
            )
    return tuple(face for face, _ in named)


def _endpoints(edge: Shape) -> tuple[tuple[float, float], tuple[float, float]]:
    """Return an edge's two endpoints as ``(r, z)`` pairs, in nm."""
    start, end = edge.start, edge.end
    return (float(start[0]), float(start[1])), (float(end[0]), float(end[1]))


def _curve_midpoint(edge: Shape) -> tuple[float, float]:
    """Return the point halfway along ``edge`` in its own parameter, as ``(r, z)``.

    ``edge.center`` is the centre of mass and lies off the curve for an arc, so
    it cannot classify a boundary that has any [tested]; ``Value`` on the
    midpoint of ``parameter_interval`` is on the curve for both an arc and a
    segment.
    """
    lower, upper = edge.parameter_interval
    point = edge.Value(0.5 * (lower + upper))
    return float(point[0]), float(point[1])


def name_region(shape: Shape, *, reservoir_radius_nm: float) -> None:
    """Name every edge of the glued region into the section 5.3.1 vocabulary, in place.

    By adjacency in the glued shape (see the module docstring), after two
    positional tests that adjacency cannot make: ``r = 0`` is ``axis``, and the
    reservoir arc is split into ``membrane_outer`` and ``cis``/``trans`` by the
    face it bounds and the side of ``z = 0`` it lies on. With an exclusion shell
    its outer surface, against the electrolyte, is ``wall``, and its seams with
    the protein and the membrane are ``interface``, as the protein's with the
    membrane is (WP30 D8).

    Raises
    ------
    RegionGateError
        If an edge bounds none of the combinations the vocabulary names, which
        means the assembly produced a seam no boundary condition would select,
        and, beside a shell, if a protein edge faces the electrolyte: the shell
        did not cover the body there.
    """
    edges_of = {
        str(face.name): set(face.edges)
        for face in shape.faces
        if face.name in {*DOMAINS, EXCLUSION}
    }
    electrolyte = edges_of.get("electrolyte", set())
    membrane = edges_of.get("membrane", set())
    protein = edges_of.get("protein", set())
    shell = edges_of.get(EXCLUSION)
    for edge in set(shape.edges):
        r_mid, z_mid = _curve_midpoint(edge)
        on_arc = (
            abs(math.hypot(r_mid, z_mid) - reservoir_radius_nm) < _ARC_RTOL * reservoir_radius_nm
        )
        if abs(r_mid) < TOL_NM:
            edge.name = "axis"
        elif edge in protein:
            if edge in membrane or (shell is not None and edge in shell):
                edge.name = "interface"
            elif edge in electrolyte and shell is not None:
                raise RegionGateError(
                    "edge naming",
                    "a pore-boundary edge facing the electrolyte beside an exclusion shell",
                    "every pore edge covered by the shell or the membrane",
                    _at(r_mid, z_mid),
                )
            elif edge in electrolyte:
                edge.name = "wall"
            else:
                raise RegionGateError(
                    "edge naming",
                    "a pore-boundary edge bounding neither membrane nor electrolyte",
                    "every pore edge faces one of them",
                    _at(r_mid, z_mid),
                )
        elif shell is not None and edge in shell:
            if edge in electrolyte:
                edge.name = "wall"
            elif edge in membrane:
                edge.name = "interface"
            else:
                raise RegionGateError(
                    "edge naming",
                    "a shell edge bounding neither the electrolyte, the membrane nor the protein",
                    "every shell edge faces one of them",
                    _at(r_mid, z_mid),
                )
        elif on_arc:
            if edge in membrane:
                edge.name = "membrane_outer"
            else:
                edge.name = "cis" if z_mid > 0.0 else "trans"
        elif edge in membrane and edge in electrolyte:
            edge.name = "membrane"
        else:
            raise RegionGateError(
                "edge naming",
                "an edge the section 5.3.1 vocabulary does not name",
                "every edge on the axis, the arc, the pore boundary or the bilayer surfaces",
                _at(r_mid, z_mid),
            )


def protein_water_edges(
    shape: Shape,
) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Return the protein's edges against the electrolyte or a shell, as endpoint pairs.

    Read from the glued region's adjacency, as :func:`name_region` reads it: what
    a derived ``chi`` takes as the body's water-facing part (WP30 D2).
    """
    edges_of: dict[str, set[Shape]] = {}
    for face in shape.faces:
        edges_of.setdefault(str(face.name), set()).update(face.edges)
    water = edges_of.get("electrolyte", set()) | edges_of.get(EXCLUSION, set())
    return [_endpoints(edge) for edge in edges_of.get("protein", set()) if edge in water]


def build_region(record: RegionRecord) -> Shape:
    """Rebuild the glued, named region from the record alone (D5).

    Deterministic: the same record assembles the same faces through the same
    booleans in one process and platform. Sizes are stage 6's and are not set
    here (:func:`nanopnp.mesh.sizing.apply_sizes`).
    """
    import netgen.occ as occ

    glued = occ.Glue(list(assemble_faces(record)))
    name_region(glued, reservoir_radius_nm=record.reservoir_radius_nm)
    return glued


def measure(shape: Shape) -> tuple[dict[str, float], dict[str, int]]:
    """Return each domain's area and each boundary name's count of unique edges.

    Counted on unique geometry: OCC lists an edge once per face it bounds, so a
    glued three-face region lists every seam twice.
    """
    areas = {str(face.name): float(face.mass) for face in shape.faces}
    counts = Counter(str(edge.name) for edge in set(shape.edges))
    return dict(sorted(areas.items())), dict(sorted(counts.items()))


# -- the graph: the region as another mesher reads it ----------------------------------


GRAPH_AREA_RTOL = 1e-9
"""Relative tolerance on a graph face's exact area against the record's (WP23 D2).

The graph's area is closed form over the shape's own coordinates, and OCC's
``face.mass`` integrates the same boundary; on the reference fixture they agree to
1e-15 on the electrolyte and 1e-12 on the membrane [tested].
"""


@dataclass(frozen=True)
class GraphEdge:
    """One edge of a :class:`RegionGraph`: its name, its end vertices and its kind.

    Parameters
    ----------
    name
        The section 5.3.1 boundary name :func:`name_region` gave it.
    start, end
        Indices into :attr:`RegionGraph.vertices`, in the edge's own direction.
    kind
        ``"segment"``, or ``"arc"``: the shorter arc of the reservoir circle about
        the origin between its two ends.
    """

    name: str
    start: int
    end: int
    kind: Literal["segment", "arc"]


@dataclass(frozen=True)
class RegionGraph:
    """The glued, named region as vertices, edges and faces (WP23 D2).

    What a mesher other than netgen meshes: every coordinate is the netgen
    shape's own, bit for bit, and faces share edges by index, so a mesher that
    builds its curves once from :attr:`edges` meshes a conformal region by
    construction.

    Parameters
    ----------
    vertices
        ``(r, z)`` in nm, one per topological vertex.
    edges
        Each unique edge once.
    faces
        Each domain's boundary as one closed loop of signed edge indices,
        counter-clockwise: ``k`` walks edge ``k`` from its start to its end and
        ``~k`` walks it backwards. A clockwise loop would mesh inverted
        elements, so the orientation is fixed here, once, as :func:`_pore_face`
        fixes it for OCC.
    reservoir_radius_nm
        The circle every ``arc`` lies on.
    """

    vertices: tuple[tuple[float, float], ...]
    edges: tuple[GraphEdge, ...]
    faces: Mapping[str, tuple[int, ...]]
    reservoir_radius_nm: float

    def walk(self, signed: int) -> tuple[int, int]:
        """Return the start and end vertex of a signed edge index as a loop walks it."""
        edge = self.edges[~signed if signed < 0 else signed]
        return (edge.end, edge.start) if signed < 0 else (edge.start, edge.end)

    def length(self, index: int) -> float:
        """Return edge ``index``'s length along its curve, in nm."""
        edge = self.edges[index]
        (r0, z0), (r1, z1) = self.vertices[edge.start], self.vertices[edge.end]
        if edge.kind == "segment":
            return math.hypot(r1 - r0, z1 - z0)
        return self.reservoir_radius_nm * abs(_arc_angle((r0, z0), (r1, z1)))

    def area(self, face: str) -> float:
        """Return a face's area in closed form, in nm^2: positive for a counter-clockwise loop.

        Green's theorem, ``1/2 oint (r dz - z dr)``: a segment contributes
        ``1/2 (a x b)`` and an arc about the origin ``1/2 R^2 dtheta``, with
        ``dtheta`` its signed angle.
        """
        total = 0.0
        for signed in self.faces[face]:
            start, end = self.walk(signed)
            a, b = self.vertices[start], self.vertices[end]
            if self.edges[~signed if signed < 0 else signed].kind == "segment":
                total += 0.5 * (a[0] * b[1] - a[1] * b[0])
            else:
                total += 0.5 * self.reservoir_radius_nm**2 * _arc_angle(a, b)
        return total

    def edge_counts(self) -> dict[str, int]:
        """Return each boundary name's count of edges, as :func:`measure` counts them."""
        return dict(sorted(Counter(edge.name for edge in self.edges).items()))


def _arc_angle(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Return the signed angle about the origin from ``a`` to ``b``, in (-pi, pi]."""
    return math.atan2(a[0] * b[1] - a[1] * b[0], a[0] * b[0] + a[1] * b[1])


def _classify_edge(
    edge: Shape, start: tuple[float, float], end: tuple[float, float], radius_nm: float
) -> Literal["segment", "arc"]:
    """Return an edge's kind, or refuse it naming its midpoint (QR-12).

    Straight when its parameter midpoint lies on its chord. Otherwise it must lie
    on the reservoir circle, as must both its ends, and on the shorter arc
    between them: that is the arc a mesher's circle-arc primitive draws.
    """
    r_mid, z_mid = _curve_midpoint(edge)
    dr, dz = end[0] - start[0], end[1] - start[1]
    chord = math.hypot(dr, dz)
    off_chord = abs(dr * (z_mid - start[1]) - dz * (r_mid - start[0])) / max(chord, TOL_NM)
    if off_chord < _ARC_RTOL * max(1.0, chord):
        return "segment"
    tolerance = _ARC_RTOL * radius_nm
    on_circle = all(
        abs(math.hypot(*point) - radius_nm) < tolerance for point in (start, end, (r_mid, z_mid))
    )
    shorter = r_mid * (start[0] + end[0]) + z_mid * (start[1] + end[1]) > 0.0
    if on_circle and shorter:
        return "arc"
    raise RegionGateError(
        "edge geometry",
        f"an edge named {str(edge.name)!r} that is neither straight nor the shorter arc of the "
        f"reservoir circle, its midpoint {off_chord:.3e} nm off its chord",
        f"a segment, or an arc of r^2 + z^2 = {radius_nm:g}^2 spanning less than pi",
        _at(r_mid, z_mid),
    )


def _chain(graph_edges: list[GraphEdge], ids: list[int], name: str) -> list[int]:
    """Chain a face's edges into one closed loop of signed indices, by shared vertex."""
    remaining = list(ids[1:])
    loop = [ids[0]]
    first, current = graph_edges[ids[0]].start, graph_edges[ids[0]].end
    while remaining:
        following = next(
            (i for i in remaining if current in (graph_edges[i].start, graph_edges[i].end)), None
        )
        if following is None:
            raise RegionGateError(
                f"{name} boundary",
                f"{len(remaining)} of its edges not reachable along one loop",
                "one closed loop",
                f"from the vertex the chain stopped at, index {current}",
            )
        remaining.remove(following)
        edge = graph_edges[following]
        if edge.start == current:
            loop.append(following)
            current = edge.end
        else:
            loop.append(~following)
            current = edge.start
    if current != first:
        raise RegionGateError(
            f"{name} boundary", "an open loop", "one closed loop", f"ending at vertex {current}"
        )
    return loop


def region_graph(shape: Shape, record: RegionRecord) -> RegionGraph:
    """Read the glued, named region into a :class:`RegionGraph` (WP23 D2).

    Parameters
    ----------
    shape
        :func:`build_region`'s shape for ``record``.
    record
        The region's record: its reservoir radius classifies the arcs, and its
        measured edge counts and face areas check the graph.

    Raises
    ------
    RegionGateError
        On an edge that is neither a segment nor a reservoir arc, naming its
        midpoint; on a face that is not one closed loop; and on a graph whose
        edge-name counts or face areas are not the record's (QR-12).
    """
    radius = record.reservoir_radius_nm
    vertex_index: dict[Shape, int] = {}
    vertices: list[tuple[float, float]] = []
    for vertex in shape.vertices:
        if vertex not in vertex_index:
            point = vertex.p
            vertex_index[vertex] = len(vertices)
            vertices.append((float(point[0]), float(point[1])))

    edge_index: dict[Shape, int] = {}
    edges: list[GraphEdge] = []
    for edge in shape.edges:
        if edge in edge_index:
            continue
        ends = list(edge.vertices)
        start, end = vertex_index[ends[0]], vertex_index[ends[-1]]
        kind = _classify_edge(edge, vertices[start], vertices[end], radius)
        edge_index[edge] = len(edges)
        edges.append(GraphEdge(name=str(edge.name), start=start, end=end, kind=kind))

    faces: dict[str, tuple[int, ...]] = {}
    for face in shape.faces:
        name = str(face.name)
        ids = sorted({edge_index[edge] for edge in face.edges})
        faces[name] = tuple(_chain(edges, ids, name))
    unoriented = RegionGraph(
        vertices=tuple(vertices), edges=tuple(edges), faces=faces, reservoir_radius_nm=radius
    )
    graph = replace(
        unoriented,
        faces={
            name: tuple(~signed for signed in reversed(loop))
            if unoriented.area(name) < 0.0
            else loop
            for name, loop in faces.items()
        },
    )

    if graph.edge_counts() != dict(sorted(record.edge_counts.items())):
        raise RegionGateError(
            "graph edge counts",
            f"{graph.edge_counts()}",
            f"the record's {dict(sorted(record.edge_counts.items()))}",
            "over the whole region",
        )
    for name, expected in sorted(record.face_areas_nm2.items()):
        found = graph.area(name) if name in faces else 0.0
        if not abs(found - expected) <= GRAPH_AREA_RTOL * abs(expected):
            raise RegionGateError(
                "graph face area",
                f"{name} {found:.12g} nm^2, {found / expected - 1.0:+.3e} relative",
                f"the record's {expected:.12g} nm^2 to {GRAPH_AREA_RTOL:g}",
                f"on the {name} face",
            )
    return graph


def _membrane_surface(shape: Shape) -> list[Shape]:
    """Return the membrane's edges on its faces against the fluid side: the electrolyte or a shell.

    Without a shell these are the ``membrane`` edges. With one, the seam between
    the membrane and the shell, an ``interface``, runs from the junction to the
    shell's outer foot, so it is taken by adjacency and not by name; an edge the
    membrane shares with the protein is not on its surface.
    """
    if not any(face.name == EXCLUSION for face in shape.faces):
        return [edge for edge in shape.edges if edge.name == "membrane"]
    edges_of: dict[str, set[Shape]] = {}
    for face in shape.faces:
        edges_of.setdefault(str(face.name), set()).update(face.edges)
    fluid_side = edges_of.get("electrolyte", set()) | edges_of.get(EXCLUSION, set())
    return [
        edge
        for edge in edges_of.get("membrane", set())
        if edge in fluid_side and edge not in edges_of.get("protein", set())
    ]


def membrane_radii(shape: Shape, half_thickness_nm: float) -> tuple[float, float]:
    """Return the innermost radius the membrane's fluid-side surface reaches on each plane.

    Raises
    ------
    RegionGateError
        If either plane carries no ``membrane`` edge: the quadrilateral did not
        meet the pore body there.
    """
    surface = _membrane_surface(shape)
    found: list[float] = []
    for plane, label in ((-half_thickness_nm, "trans"), (half_thickness_nm, "cis")):
        radii = [
            point[0]
            for edge in surface
            for point in _endpoints(edge)
            if abs(point[1] - plane) < TOL_NM
        ]
        if not radii:
            raise RegionGateError(
                "membrane junction",
                f"no membrane boundary on the {label} plane",
                "one",
                f"on z = {plane:+.4f} nm",
            )
        found.append(min(radii))
    return found[0], found[1]


def check_junction(record: RegionRecord, shape: Shape) -> None:
    """Abort unless the membrane meets the body at ``r2`` on both planes (VER-28, made generic).

    Raises
    ------
    RegionGateError
        Naming the plane, the assembled radius, ``r2`` and the tolerance.
    """
    half = record.membrane.half_thickness_nm
    assembled = membrane_radii(shape, half)
    for (label, plane), radius in zip((("trans", -half), ("cis", half)), assembled, strict=True):
        expected = record.junction_nm[label]
        if abs(radius - expected) > TOL_NM:
            raise RegionGateError(
                "membrane junction",
                f"the membrane's innermost radius {radius:.9f} nm on the {label} plane, "
                f"{radius - expected:+.3e} nm from r2 = {expected:.9f} nm",
                f"|offset| <= {TOL_NM:g} nm",
                _at(radius, plane),
            )


def derive_region(
    profile: PoreProfile,
    membrane: MembraneSpec,
    reservoir: ReservoirSpec,
    *,
    exclusion_offset_nm: float = 0.0,
    h_c_nm: float | None = None,
) -> RegionRecord:
    """Assemble ``profile`` into the tagged region and return its record (D2-D6).

    Parameters
    ----------
    profile
        The pore profile, in the structure's frame.
    membrane, reservoir
        ``geometry.membrane`` and ``geometry.reservoir``, validated by the case
        resolver as finite and positive.
    exclusion_offset_nm
        ``charge.exclusion_offset_nm``, ``a``. With ``a > 0`` the region gains
        the ion-exclusion shell of :func:`exclusion_shell` (WP30); at ``0`` none
        of it runs.
    h_c_nm
        The contour's size target, required with ``a > 0``.

    Returns
    -------
    RegionRecord
        The model-frame region, with its derived inner edge and what the
        assembly measured.

    Raises
    ------
    RegionGateError
        At the first junction criterion the region fails.
    """
    half = 0.5 * membrane.thickness_nm
    radius = reservoir.radius_nm
    points = to_model_frame(profile.as_array(), membrane.centre_z_nm)
    _check_inside_reservoir(points, radius)
    trans = lumen_interval(points, -half, centre_z_nm=membrane.centre_z_nm)
    cis = lumen_interval(points, half, centre_z_nm=membrane.centre_z_nm)
    r_trans, r_cis, clearance = best_chord(points, trans, cis, half)
    if not clearance >= JUNCTION_CLEARANCE_NM:
        raise RegionGateError(
            "chord clearance",
            f"the widest-margin inner edge is {clearance:.4f} nm from the profile",
            f"at least {JUNCTION_CLEARANCE_NM:g} nm",
            f"on the chord from {_at(r_trans, -half)} to ({r_cis:.4f}, {half:.4f}) nm; the "
            "membrane is not representable as a quadrilateral with a slanted inner edge",
        )
    record = RegionRecord(
        profile=[(float(r), float(z)) for r, z in points],
        membrane=MembraneRecord(
            thickness_nm=membrane.thickness_nm,
            centre_z_nm=membrane.centre_z_nm,
            inner_trans_nm=r_trans,
            inner_cis_nm=r_cis,
            clearance_nm=clearance,
        ),
        reservoir_radius_nm=radius,
        axis_split_nm=(float(points[:, 1].min()), float(points[:, 1].max())),
        junction_nm={"trans": trans[1], "cis": cis[1]},
    )
    if exclusion_offset_nm > 0.0:
        if h_c_nm is None:
            raise ValueError("an exclusion shell needs h_c_nm, the contour's size target")
        shell = exclusion_shell(points, exclusion_offset_nm, h_c_nm, reservoir_radius_nm=radius)
        record = record.model_copy(update={"exclusion": shell})
    shape = build_region(record)
    check_junction(record, shape)
    areas, counts = measure(shape)
    return record.model_copy(update={"face_areas_nm2": areas, "edge_counts": counts})


# -- the stage -------------------------------------------------------------------------


def _profile_input(inputs: StageInputs, resolved: ResolvedCase) -> tuple[str, Path]:
    """Return the profile's identity and its file: stage 4's artefact, or ``inputs.profile``.

    Raises
    ------
    UnsupportedCaseSection
        If the case has neither a ``structure:`` section nor ``inputs.profile``,
        so there is no profile to assemble.
    """
    if resolved.profile is not None:
        path = resolved.profile.path
        assert path is not None  # the resolver refuses artefact: on inputs.profile
        return profile_digest(load_profile(path)), path
    if resolved.structure is None:
        raise UnsupportedCaseSection(
            f"case {inputs.resolved.name!r} supplies inputs.mesh, so there is no region for "
            "stage 5 to assemble"
        )
    contour = inputs.require("contour")
    return contour.hash, contour.payload["profile"]


def region_parameters(
    membrane: MembraneSpec,
    reservoir: ReservoirSpec,
    *,
    exclusion_offset_nm: float = 0.0,
    h_c_nm: float | None = None,
) -> dict[str, Canonicalisable]:
    """Return the stage-5 key's parameters (D5): the membrane, the reservoir and the constants.

    With an exclusion shell, the offset, ``h_c`` and the shell's constants join
    them under ``exclusion``; without one nothing is added, so every shell-free
    key is the key it was before the shell existed (WP30 D10).
    """
    parameters: dict[str, Canonicalisable] = {
        "membrane": membrane.model_dump(mode="json"),
        "reservoir": reservoir.model_dump(mode="json"),
        "constants": dict(KEY_CONSTANTS),
    }
    if exclusion_offset_nm > 0.0:
        parameters["exclusion"] = {
            "offset_nm": exclusion_offset_nm,
            "h_c_nm": h_c_nm,
            "constants": dict(EXCLUSION_CONSTANTS),
        }
    return parameters


class RegionStage:
    """Stage 5: a pore profile to the tagged, gated ``nanopnp/region/v1`` record."""

    name = "region"

    def __init__(self, *, workspace: Path | None = None) -> None:
        """Build the stage.

        Parameters
        ----------
        workspace
            Directory ``region.yaml`` is written to before the store copies it
            in. Defaults to a fresh directory under the store root.
        """
        self._workspace = Path(workspace) if workspace is not None else None

    def describe(self) -> StageDescription:
        """Return the registry's description of this stage (FR-27)."""
        return describe(self.name)

    def key(self, inputs: StageInputs) -> RegionArtefact:
        """Return the key: the membrane, the reservoir, the constants and the profile."""
        resolved = inputs.resolved
        identity, _ = _profile_input(inputs, resolved)
        return self._key(resolved, identity)

    def _key(self, resolved: ResolvedCase, identity: str) -> RegionArtefact:
        """Return the key from the resolved case and a profile identity already in hand."""
        assert resolved.membrane is not None and resolved.reservoir is not None
        return RegionArtefact(
            parameters=region_parameters(
                resolved.membrane,
                resolved.reservoir,
                exclusion_offset_nm=resolved.exclusion_offset_nm,
                h_c_nm=resolved.contour_spacing_nm,
            ),
            inputs={"profile": identity},
        )

    def run(
        self,
        inputs: StageInputs,
        *,
        progress: Progress | None = None,
        cancel: CancelToken | None = None,
    ) -> RegionArtefact:
        """Assemble and gate the region, and emit the stage-5 artefact.

        Raises
        ------
        RegionGateError
            At the first junction criterion the region fails. No artefact is
            written.
        Cancelled
            If ``cancel`` turns true. No artefact is written.
        """
        check_cancelled(cancel, "reading the profile")
        report(progress, 0.0, "reading the profile")
        resolved = inputs.resolved
        identity, path = _profile_input(inputs, resolved)
        key = self._key(resolved, identity)
        assert resolved.membrane is not None and resolved.reservoir is not None
        profile = load_profile(path)

        check_cancelled(cancel, "assembling the region")
        report(progress, 0.2, f"assembling the region around {len(profile.vertices)} vertices")
        record = derive_region(
            profile,
            resolved.membrane,
            resolved.reservoir,
            exclusion_offset_nm=resolved.exclusion_offset_nm,
            h_c_nm=resolved.contour_spacing_nm,
        )

        directory = self._workspace
        if directory is None:
            root = store_root() / WORKSPACE_DIRNAME
            root.mkdir(parents=True, exist_ok=True)
            directory = Path(tempfile.mkdtemp(prefix="region-", dir=root))
        written = write_region(record, directory / f"{PAYLOAD_NAME}.yaml")
        logger.info(
            "region: inner edge (%.4f, %.4f) nm, clearance %.4f nm, junction %.4f and %.4f nm, "
            "shift %g nm",
            record.membrane.inner_trans_nm,
            record.membrane.inner_cis_nm,
            record.membrane.clearance_nm,
            record.junction_nm["trans"],
            record.junction_nm["cis"],
            record.membrane.centre_z_nm,
        )
        report(progress, 1.0, "region written")
        return RegionArtefact(
            parameters=key.parameters,
            inputs=key.inputs,
            payload={PAYLOAD_NAME: written},
            summary=record.summary(),
        )
