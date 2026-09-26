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
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from pydantic import BaseModel, ConfigDict, Field

from nanopnp.core.hashing import Canonicalisable, content_hash
from nanopnp.core.paths import store_root
from nanopnp.core.stages import (
    CancelToken,
    Progress,
    StageDescription,
    check_cancelled,
    describe,
    report,
)
from nanopnp.io.artefact import RegionArtefact
from nanopnp.io.case import MembraneSpec, ReservoirSpec, UnsupportedCaseSection, resolve
from nanopnp.mesh.primitives import TOL_NM
from nanopnp.mesh.profile import PROFILE_SCHEMA, PoreProfile, load_profile, plane_crossings

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

    from nanopnp.core.typing import Shape
    from nanopnp.io.artefact import StageInputs

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

    def points(self) -> np.ndarray:
        """Return the model-frame profile as an ``(n, 2)`` float64 array."""
        import numpy as np

        return np.asarray(self.profile, dtype=np.float64).reshape(-1, 2)

    def summary(self) -> dict[str, Canonicalisable]:
        """Return what the manifest's Geometry group records as ``region`` (WP21 D16)."""
        return {
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


def write_region(record: RegionRecord, path: Path) -> Path:
    """Write ``record`` as ``nanopnp/region/v1`` YAML that :func:`read_region` reads back.

    Floats are written as Python's shortest round-trip representation, so the
    vertices read back bit for bit and the rebuilt region is the one measured.
    """
    document = record.model_dump(by_alias=True, mode="json")
    document["profile"] = [[float(r), float(z)] for r, z in record.profile]
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


def profile_digest(profile: PoreProfile) -> str:
    """Return the canonical digest of a validated profile's payload (WP21 D5).

    Over the validated document rather than the file's bytes, so reformatting a
    supplied profile is the same input and editing a vertex is a different one
    (FR-27).
    """
    return content_hash(PROFILE_SCHEMA, profile.model_dump(by_alias=True, mode="json"))


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
    return crossings[0], crossings[1]


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

    from nanopnp.mesh.profile import signed_area

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


def assemble_faces(record: RegionRecord) -> tuple[Shape, Shape, Shape]:
    """Return the three named faces, electrolyte, membrane and pore, unglued.

    The booleans are the assembly: the membrane is the quadrilateral clipped to
    the reservoir and cut by the pore body, and the electrolyte is what the
    half-disc has left once both are removed. Names are set after the booleans,
    because a face's name does not survive being cut.

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
    electrolyte = (disc - quad) - pore
    named = ((electrolyte, "electrolyte"), (membrane, "membrane"), (pore, "protein"))
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
    return electrolyte, membrane, pore


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
    face it bounds and the side of ``z = 0`` it lies on.

    Raises
    ------
    RegionGateError
        If an edge bounds none of the combinations the vocabulary names, which
        means the assembly produced a seam no boundary condition would select.
    """
    edges_of = {
        str(face.name): set(face.edges) for face in shape.faces if face.name in set(DOMAINS)
    }
    electrolyte = edges_of.get("electrolyte", set())
    membrane = edges_of.get("membrane", set())
    protein = edges_of.get("protein", set())
    for edge in set(shape.edges):
        r_mid, z_mid = _curve_midpoint(edge)
        on_arc = (
            abs(math.hypot(r_mid, z_mid) - reservoir_radius_nm) < _ARC_RTOL * reservoir_radius_nm
        )
        if abs(r_mid) < TOL_NM:
            edge.name = "axis"
        elif edge in protein:
            if edge in membrane:
                edge.name = "interface"
            elif edge in electrolyte:
                edge.name = "wall"
            else:
                raise RegionGateError(
                    "edge naming",
                    "a pore-boundary edge bounding neither membrane nor electrolyte",
                    "every pore edge faces one of them",
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


def build_region(record: RegionRecord) -> Shape:
    """Rebuild the glued, named region from the record alone (D5).

    Deterministic: the same record assembles the same faces through the same
    booleans in one process and platform. Sizes are stage 6's and are not set
    here (:func:`nanopnp.mesh.sizing.apply_sizes`).
    """
    import netgen.occ as occ

    electrolyte, membrane, pore = assemble_faces(record)
    glued = occ.Glue([electrolyte, membrane, pore])
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


def membrane_radii(shape: Shape, half_thickness_nm: float) -> tuple[float, float]:
    """Return the innermost radius the ``membrane`` boundary reaches on each plane.

    Raises
    ------
    RegionGateError
        If either plane carries no ``membrane`` edge: the quadrilateral did not
        meet the pore body there.
    """
    found: list[float] = []
    for plane, label in ((-half_thickness_nm, "trans"), (half_thickness_nm, "cis")):
        radii = [
            point[0]
            for edge in shape.edges
            if edge.name == "membrane"
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
    profile: PoreProfile, membrane: MembraneSpec, reservoir: ReservoirSpec
) -> RegionRecord:
    """Assemble ``profile`` into the tagged region and return its record (D2-D6).

    Parameters
    ----------
    profile
        The pore profile, in the structure's frame.
    membrane, reservoir
        ``geometry.membrane`` and ``geometry.reservoir``, validated by the case
        resolver as finite and positive.

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
    shape = build_region(record)
    check_junction(record, shape)
    areas, counts = measure(shape)
    return record.model_copy(update={"face_areas_nm2": areas, "edge_counts": counts})


# -- the stage -------------------------------------------------------------------------


def _profile_input(inputs: StageInputs) -> tuple[str, Path]:
    """Return the profile's identity and its file: stage 4's artefact, or ``inputs.profile``.

    Raises
    ------
    UnsupportedCaseSection
        If the case has neither a ``structure:`` section nor ``inputs.profile``,
        so there is no profile to assemble.
    """
    resolved = resolve(inputs.case)
    if resolved.profile is not None:
        path = resolved.profile.path
        assert path is not None  # the resolver refuses artefact: on inputs.profile
        return profile_digest(load_profile(path)), path
    if resolved.structure is None:
        raise UnsupportedCaseSection(
            f"case {inputs.case.name!r} supplies inputs.mesh, so there is no region for stage 5 "
            "to assemble"
        )
    contour = inputs.require("contour")
    return contour.hash, contour.payload["profile"]


def region_parameters(
    membrane: MembraneSpec, reservoir: ReservoirSpec
) -> dict[str, Canonicalisable]:
    """Return the stage-5 key's parameters (D5): the membrane, the reservoir and the constants."""
    return {
        "membrane": membrane.model_dump(mode="json"),
        "reservoir": reservoir.model_dump(mode="json"),
        "constants": dict(KEY_CONSTANTS),
    }


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
        identity, _ = _profile_input(inputs)
        return self._key(inputs, identity)

    def _key(self, inputs: StageInputs, identity: str) -> RegionArtefact:
        """Return the key from a profile identity already in hand."""
        resolved = resolve(inputs.case)
        assert resolved.membrane is not None and resolved.reservoir is not None
        return RegionArtefact(
            parameters=region_parameters(resolved.membrane, resolved.reservoir),
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
        identity, path = _profile_input(inputs)
        key = self._key(inputs, identity)
        resolved = resolve(inputs.case)
        assert resolved.membrane is not None and resolved.reservoir is not None
        profile = load_profile(path)

        check_cancelled(cancel, "assembling the region")
        report(progress, 0.2, f"assembling the region around {len(profile.vertices)} vertices")
        record = derive_region(profile, resolved.membrane, resolved.reservoir)

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
