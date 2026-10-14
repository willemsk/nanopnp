"""Stage 5: CAD assembly of a pore profile into the tagged region (FR-09)."""

from __future__ import annotations

import logging
import math
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from nanopnp.core.hashing import Canonicalisable
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
from nanopnp.io.artefact import REGION_SCHEMA, RegionArtefact
from nanopnp.io.case import (
    MembraneSpec,
    ReservoirSpec,
    UnsupportedCaseSection,
)
from nanopnp.io.workspace import scratch_directory

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

    from nanopnp.core.typing import Shape
    from nanopnp.io.artefact import StageInputs
    from nanopnp.io.resolved import ResolvedCase

logger = logging.getLogger(__name__)

CHORD_DIVISIONS = 64

JUNCTION_CLEARANCE_NM = 0.01

MEMBRANE_OVERSHOOT = "half_thickness"

KEY_CONSTANTS: Mapping[str, Canonicalisable] = {
    "chord_divisions": CHORD_DIVISIONS,
    "junction_clearance_nm": JUNCTION_CLEARANCE_NM,
    "junction_tolerance_nm": TOL_NM,
    "membrane_overshoot": MEMBRANE_OVERSHOOT,
}

PAYLOAD_NAME = "region"


DOMAINS: tuple[str, str, str] = ("electrolyte", "membrane", "protein")

EXCLUSION = "exclusion"

EXCLUSION_QUAD_SEGS = 8

EXCLUSION_CLOSING = 2.0

EXCLUSION_RESAMPLE = 1.05

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

_ARC_RTOL = 1e-9


class RegionGateError(ValueError):
    """Stage 5's region failed a junction criterion.

    Parameters
    ----------
    criterion
        The criterion that failed, e.g. ``"chord clearance"``.
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
    return f"at (r, z) = ({r_nm:.4f}, {z_nm:.4f}) nm"


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MembraneRecord(_Strict):
    """The bilayer as assembled: its slab, its frame shift and its inner edge."""

    thickness_nm: float
    centre_z_nm: float
    inner_trans_nm: float
    inner_cis_nm: float
    clearance_nm: float | None = None

    @property
    def half_thickness_nm(self) -> float:
        """Half the bilayer thickness, in nm."""
        return 0.5 * self.thickness_nm


class FilledHoles(_Strict):
    """The pockets of fluid the offset enclosed, which no ion can reach, filled and recorded."""

    count: int
    area_nm2: float
    centroids_nm: list[tuple[float, float]] = Field(default_factory=list)


class ExclusionRecord(_Strict):
    """The ion-exclusion shell's outer loop and what its construction measured."""

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
    profile
        The pore polygon's vertices in the model frame, in nm.
    axis_split_nm
        The profile's model-frame z extent, in nm.
    exclusion
        The ion-exclusion shell, or ``None`` without one.
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
        """Return what the manifest's Geometry group records as ``region``."""
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
    """Write ``record`` as ``nanopnp/region/v0.5`` YAML that :func:`read_region` reads back."""
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
    """Read a ``nanopnp/region/v0.5`` record.

    Raises
    ------
    ValueError
        If the document declares another schema.
    """
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    schema = raw.get("schema") if isinstance(raw, dict) else None
    if schema != REGION_SCHEMA:
        raise ValueError(f"{path}: expected schema {REGION_SCHEMA!r}, found {schema!r}")
    return RegionRecord.model_validate(raw)


def to_model_frame(points: np.ndarray, centre_z_nm: float) -> np.ndarray:
    """Return ``points`` moved into the model frame, ``z <- z - centre_z_nm``."""
    shifted = points.copy()
    shifted[:, 1] = shifted[:, 1] - centre_z_nm
    return shifted


def lumen_interval(points: np.ndarray, z_nm: float, *, centre_z_nm: float) -> tuple[float, float]:
    """Return the lumen-adjacent body interval ``[r1, r2]`` on the plane ``z = z_nm``."""
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
    orientation: np.ndarray = (q[..., 0] - p[..., 0]) * (r[..., 1] - p[..., 1]) - (
        q[..., 1] - p[..., 1]
    ) * (r[..., 0] - p[..., 0])
    return orientation


def chord_clearances(starts: np.ndarray, ends: np.ndarray, points: np.ndarray) -> np.ndarray:
    """Return each chord's least distance to the closed polygon ``points``, in nm."""
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
    """Return the widest-margin inner edge as ``(r_trans, r_cis, clearance)``, in nm."""
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
    """Return the ion-exclusion shell's outer loop, built and gated.

    Raises
    ------
    RegionGateError
        If the shell is invalid, closes the constriction, or leaves the reservoir.
    MissingExtraError
        Without Shapely, naming the ``structure`` extra.
    """
    try:
        from shapely import box
        from shapely.geometry import LinearRing, MultiPolygon, Polygon

        from nanopnp.geometry.contour import enforce_spacing, resample
    except ImportError as error:
        raise _missing_shapely(error) from error
    import numpy as np

    if not np.isfinite(points).all():
        bad = np.argwhere(~np.isfinite(points))[0]
        raise RegionGateError(
            "exclusion shell input",
            f"a non-finite coordinate, {float(points[bad[0], bad[1]])}, at vertex {int(bad[0])}",
            "finite (r, z) for every vertex",
            f"at vertex {int(bad[0])} of the model-frame profile",
        )
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
    if not lowest >= h_c_nm:
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
    if not spacing >= h_c_nm:  # pragma: no cover - enforce_spacing stops only at 3 vertices
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


def _pore_face(points: np.ndarray) -> Shape:
    import netgen.occ as occ

    vertices = points[::-1] if signed_area(points) < 0.0 else points
    plane = occ.WorkPlane().MoveTo(float(vertices[0][0]), float(vertices[0][1]))
    for radius, height in vertices[1:]:
        plane = plane.LineTo(float(radius), float(height))
    return plane.Close().Face()


def _reservoir_face(radius_nm: float, axis_split_nm: tuple[float, float]) -> Shape:
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
    """Return the named faces (electrolyte, membrane, pore and any shell), unglued.

    Raises
    ------
    RegionGateError
        If any domain assembled as other than one face.
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
    start, end = edge.start, edge.end
    return (float(start[0]), float(start[1])), (float(end[0]), float(end[1]))


def _curve_midpoint(edge: Shape) -> tuple[float, float]:
    lower, upper = edge.parameter_interval
    point = edge.Value(0.5 * (lower + upper))
    return float(point[0]), float(point[1])


def name_region(shape: Shape, *, reservoir_radius_nm: float) -> None:
    """Name every edge of the glued region into the project vocabulary, in place.

    Raises
    ------
    RegionGateError
        If an edge bounds none of the combinations the vocabulary names.
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
    """Return the protein's edges against the electrolyte or a shell, as endpoint pairs."""
    edges_of: dict[str, set[Shape]] = {}
    for face in shape.faces:
        edges_of.setdefault(str(face.name), set()).update(face.edges)
    water = edges_of.get("electrolyte", set()) | edges_of.get(EXCLUSION, set())
    return [_endpoints(edge) for edge in edges_of.get("protein", set()) if edge in water]


def build_region(record: RegionRecord) -> Shape:
    """Rebuild the glued, named region from the record alone."""
    import netgen.occ as occ

    glued = occ.Glue(list(assemble_faces(record)))
    name_region(glued, reservoir_radius_nm=record.reservoir_radius_nm)
    return glued


def measure(shape: Shape) -> tuple[dict[str, float], dict[str, int]]:
    """Return each domain's area and each boundary name's count of unique edges."""
    areas = {str(face.name): float(face.mass) for face in shape.faces}
    counts = Counter(str(edge.name) for edge in set(shape.edges))
    return dict(sorted(areas.items())), dict(sorted(counts.items()))


GRAPH_AREA_RTOL = 1e-9


@dataclass(frozen=True)
class GraphEdge:
    """One edge of a :class:`RegionGraph`: its name, its end vertices and its kind."""

    name: str
    start: int
    end: int
    kind: Literal["segment", "arc"]


@dataclass(frozen=True)
class RegionGraph:
    """The glued, named region as vertices, edges and faces."""

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
        """Return a face's area in closed form, in nm^2; positive for a counter-clockwise loop."""
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
    return math.atan2(a[0] * b[1] - a[1] * b[0], a[0] * b[0] + a[1] * b[1])


def _classify_edge(
    edge: Shape, start: tuple[float, float], end: tuple[float, float], radius_nm: float
) -> Literal["segment", "arc"]:
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
    """Read the glued, named region into a :class:`RegionGraph`.

    Raises
    ------
    RegionGateError
        If the graph's edge counts or face areas are not the record's.
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
    """Return the innermost radius the membrane's fluid-side surface reaches on each plane."""
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
    """Abort unless the membrane meets the body at ``r2`` on both planes."""
    half = record.membrane.half_thickness_nm
    assembled = membrane_radii(shape, half)
    for (label, plane), radius in zip((("trans", -half), ("cis", half)), assembled, strict=True):
        expected = record.junction_nm[label]
        if not abs(radius - expected) <= TOL_NM:
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
    """Assemble ``profile`` into the tagged region and return its record.

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


def _profile_input(inputs: StageInputs, resolved: ResolvedCase) -> tuple[str, Path]:
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
    """Return the stage-5 key's parameters: the membrane, the reservoir and the constants."""
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
    """Stage 5: a pore profile to the tagged, gated region record."""

    name = "region"

    def __init__(self, *, workspace: Path | None = None) -> None:
        self._workspace = Path(workspace) if workspace is not None else None

    def describe(self) -> StageDescription:
        """Return the registry's description of this stage."""
        return describe(self.name)

    def key(self, inputs: StageInputs) -> RegionArtefact:
        """Return the key: the membrane, the reservoir, the constants and the profile."""
        resolved = inputs.resolved
        identity, _ = _profile_input(inputs, resolved)
        return self._key(resolved, identity)

    def _key(self, resolved: ResolvedCase, identity: str) -> RegionArtefact:
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
            At the first junction criterion the region fails.
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

        directory = scratch_directory(self._workspace, "region")
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
