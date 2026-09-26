"""The pore profile fixture: a closed ``(r, z)`` polygon, validated at the boundary.

The reference pore boundary is data, not code — the same rule the correction
parameters are held to (FR-16, ADR-005), applied to geometry. The delivered
table stays in the repository verbatim as
``data/geometry/clya_as_radial_geometry.csv``, CRLF line endings and all, so
that its sha256 identifies the artefact the author supplied and not our
reformatting of it; :func:`profile_from_csv` converts it once into the YAML
fixture the code loads, and a Tier-1 test re-derives the fixture from the table
so the two cannot drift.

The fixture is **not** gated on the section 5.2.1 conditioning criteria. Those
apply to contours the FR-08 pipeline produces: the delivered polygon fails two
of them at the reference wall size of 0.05 nm — minimum vertex spacing 0.0361 nm
and minimum local feature size 0.0806 nm — and is nevertheless the polygon the
reference mesh was built from, at that wall size, reaching minimum element
quality 0.6378. A supplied fixture is gated on validity, simplicity and loop
topology instead, and its spacing and feature size are *recorded* in provenance,
so a mesh size chosen against it can be checked rather than assumed (section
5.2.1 NOTE).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from nanopnp.core.paths import profile_file

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

PROFILE_SCHEMA: str = "nanopnp/profile/v1"
"""Schema identifier every profile fixture must declare."""

REFERENCE_SOURCES: frozenset[str] = frozenset({"model-report", "author-supplied"})
"""Provenance sources that make a profile the reference geometry.

A Tier-3 or Tier-4 comparison is against the reference model and means nothing
against a stand-in, so :meth:`PoreProfile.require_reference` gates on this set
rather than on the fixture's name. ``author-supplied`` is here beside
``model-report`` because the delivered table came from the reference model's
author and is the geometry of record section 5.2.1 amends to; nothing nominal
ships (OPN-05, closed on the delivered table).
"""

PIPELINE_SOURCE: str = "pipeline"
"""``provenance.source`` of a profile stage 4 extracted (§5.3.1 NOTE on ``geometry.contour``).

Outside :data:`REFERENCE_SOURCES`: a contour drawn from a structure is a
geometry, not the reference model's, and a Tier-3 comparison refuses it.
"""

MEASUREMENT_TOL: float = 1e-9
"""Tolerance, in nm and nm², on a recorded measurement against the vertices.

The provenance block is checked against the polygon it describes at load, so a
fixture cannot ship a spacing or an area belonging to a different table. The
values are written with full precision, so this is round-off.
"""


class _Strict(BaseModel):
    """Base for the fixture blocks: unknown keys are rejected, naming them."""

    model_config = ConfigDict(extra="forbid")


class ProfileProvenance(_Strict):
    """Where a profile came from, and what was measured on it.

    Parameters
    ----------
    source
        ``model-report``, ``author-supplied`` or a name of the run that produced
        it. :data:`REFERENCE_SOURCES` decides which ones count as the reference.
    citation
        The publication or model file the table belongs to.
    sha256
        Digest of the delivered table this fixture was derived from, over its
        bytes as delivered.
    vertex_count, min_vertex_spacing_nm, min_feature_size_nm, signed_area_nm2
        Measured on the vertices below and re-checked against them at load. The
        signed area is negative for a clockwise loop, and its sign is the
        orientation.
    """

    source: str
    citation: str
    sha256: str
    vertex_count: int
    min_vertex_spacing_nm: float
    min_feature_size_nm: float
    signed_area_nm2: float


class PoreProfile(_Strict):
    """A closed pore-boundary polygon in the ``(r, z)`` half-plane, in nm.

    The closing edge from the last vertex back to the first is implied and is
    never repeated, so ``len(vertices)`` is the vertex count and also the edge
    count.

    Raises
    ------
    ValueError
        At construction, if the loop is not a valid simple closed polygon in the
        half-plane, or if the provenance block does not describe these vertices.
    """

    model_config = ConfigDict(extra="forbid")

    schema_id: str = Field(alias="schema")
    name: str
    description: str | None = None
    provenance: ProfileProvenance
    vertices: list[tuple[float, float]]

    @model_validator(mode="after")
    def _check_polygon(self) -> PoreProfile:
        """Gate the loop on validity, simplicity and topology (section 5.2.1 NOTE)."""
        points = self.as_array()
        if len(points) < 3:
            raise ValueError(f"a closed polygon needs at least three vertices, got {len(points)}")
        if float(points[:, 0].min()) < 0.0:
            raise ValueError(
                f"vertex radius must be non-negative in the (r, z) half-plane; the smallest is "
                f"{float(points[:, 0].min()):.6g} nm"
            )
        _check_no_repeats(points)
        _check_simple(points)
        if abs(signed_area(points)) <= 0.0:
            raise ValueError("this polygon encloses no area")
        return self

    @model_validator(mode="after")
    def _check_provenance_describes_these_vertices(self) -> PoreProfile:
        """Reject a provenance block measured on a different table.

        The recorded spacing and feature size are what a mesh size is chosen
        against, so a fixture whose vertices were edited without its provenance
        being re-derived would silently justify the wrong element size.
        """
        points = self.as_array()
        if self.provenance.vertex_count != len(points):
            raise ValueError(
                f"provenance.vertex_count is {self.provenance.vertex_count} but the table carries "
                f"{len(points)} vertices"
            )
        recorded = {
            "min_vertex_spacing_nm": (
                self.provenance.min_vertex_spacing_nm,
                min_vertex_spacing(points),
            ),
            "min_feature_size_nm": (self.provenance.min_feature_size_nm, min_feature_size(points)),
            "signed_area_nm2": (self.provenance.signed_area_nm2, signed_area(points)),
        }
        for key, (claimed, measured) in recorded.items():
            if abs(claimed - measured) > MEASUREMENT_TOL:
                raise ValueError(
                    f"provenance.{key} is {claimed!r} but these vertices give {measured!r}; the "
                    "provenance block does not describe this polygon"
                )
        return self

    @property
    def is_reference(self) -> bool:
        """Whether this profile is the reference geometry (:data:`REFERENCE_SOURCES`)."""
        return self.provenance.source in REFERENCE_SOURCES

    def require_reference(self, purpose: str) -> None:
        """Raise unless this profile is the reference geometry.

        Parameters
        ----------
        purpose
            What the caller is doing, quoted in the message: a Tier-3 comparison
            or a Tier-4 reproduction is against the reference model, and run on
            a stand-in it would report an agreement that means nothing.

        Raises
        ------
        ValueError
            If :attr:`is_reference` is false; the message names the source found
            and the ones that count.
        """
        if not self.is_reference:
            allowed = ", ".join(sorted(REFERENCE_SOURCES))
            raise ValueError(
                f"{purpose} needs the reference geometry, but profile {self.name!r} has "
                f"provenance.source {self.provenance.source!r}; the reference sources are {allowed}"
            )

    def as_array(self) -> np.ndarray:
        """Return the vertices as an ``(n, 2)`` float64 array of ``(r, z)`` in nm."""
        import numpy as np

        return np.asarray(self.vertices, dtype=np.float64).reshape(-1, 2)

    @property
    def extent_r_nm(self) -> tuple[float, float]:
        """``(min, max)`` radius over the loop, in nm."""
        radii = self.as_array()[:, 0]
        return float(radii.min()), float(radii.max())

    @property
    def extent_z_nm(self) -> tuple[float, float]:
        """``(min, max)`` axial coordinate over the loop, in nm."""
        axial = self.as_array()[:, 1]
        return float(axial.min()), float(axial.max())

    @property
    def is_clockwise(self) -> bool:
        """Whether the loop runs clockwise in ``(r, z)``; the delivered table does."""
        return signed_area(self.as_array()) < 0.0


def signed_area(points: np.ndarray) -> float:
    """Return the shoelace signed area of a closed loop, in nm^2.

    Negative for a clockwise loop in ``(r, z)``. The closing edge is implied, so
    the last vertex is joined back to the first here rather than in the table.
    """
    import numpy as np

    following = np.roll(points, -1, axis=0)
    return float(0.5 * np.sum(points[:, 0] * following[:, 1] - following[:, 0] * points[:, 1]))


def min_vertex_spacing(points: np.ndarray) -> float:
    """Return the shortest edge of the closed loop, in nm."""
    import numpy as np

    return float(np.min(np.linalg.norm(np.roll(points, -1, axis=0) - points, axis=1)))


LOCAL_EDGES: int = 2
"""How many edges either side of a vertex count as its own neighbourhood.

The local feature size excludes them. Excluding only the two edges incident on
the vertex is not enough: a vertex is always within an edge length of the edge
beyond its neighbour, so the measure would collapse onto the shortest edge and
report 0.0361 nm for the reference polygon rather than 0.0806 nm [tested] —
sampling density, not a feature.
"""


def min_feature_size(points: np.ndarray, *, local_edges: int = LOCAL_EDGES) -> float:
    """Return the smallest distance from a vertex to a non-local edge, in nm.

    The feature a mesher has to resolve: a near-tangential self-approach at the
    constriction generates slivers no amount of smoothing repairs (section
    5.2.1). Edges within ``local_edges`` of the vertex along the loop are its own
    neighbourhood and are excluded; see :data:`LOCAL_EDGES`.

    Parameters
    ----------
    points
        ``(n, 2)`` vertices of the closed loop, the closing edge implied.
    local_edges
        Cyclic edge distance below which an edge counts as local to the vertex.
    """
    return float(feature_sizes(points, local_edges=local_edges).min())


def feature_sizes(points: np.ndarray, *, local_edges: int = LOCAL_EDGES) -> np.ndarray:
    """Return each vertex's distance to its nearest non-local edge, in nm.

    :func:`min_feature_size` is the minimum of this. The array is what locates
    it, which stage 4's gate names when the criterion fails (QR-12).

    Parameters
    ----------
    points, local_edges
        As :func:`min_feature_size` takes them.
    """
    import numpy as np

    count = len(points)
    starts = points
    span = np.roll(points, -1, axis=0) - starts
    length_squared = np.einsum("ij,ij->i", span, span)
    safe = np.where(length_squared > 0.0, length_squared, 1.0)
    edge = np.arange(count)
    sizes = np.empty(count)
    # On a loop so short that the neighbourhood would swallow every edge — a
    # triangle, a quadrilateral — it shrinks to the two incident edges, which
    # leaves the measure defined rather than empty. It cannot bite on a profile
    # of any realistic size.
    neighbourhood = min(local_edges, max(1, (count - 1) // 2))
    for vertex in range(count):
        # Cyclic distance from the vertex to edge i, which spans vertices i and i+1.
        local = np.minimum((edge - vertex) % count, (vertex - edge - 1) % count) < neighbourhood
        offset = points[vertex] - starts
        parameter = np.clip(np.einsum("ij,ij->i", offset, span) / safe, 0.0, 1.0)
        distance = np.linalg.norm(offset - parameter[:, None] * span, axis=1)
        sizes[vertex] = np.min(distance[~local])
    return sizes


def plane_crossings(profile: PoreProfile | np.ndarray, z_nm: float) -> tuple[float, ...]:
    """Return the radii at which a closed polygon crosses the plane ``z = z_nm``.

    Here rather than in :mod:`nanopnp.mesh.reference` because stage 5 derives the
    membrane junction of *any* profile from it (section 5.2.1 NOTE on the
    membrane junction on any profile); the reference module re-exports it.

    Parameters
    ----------
    profile
        The pore profile, or its ``(n, 2)`` vertices. The closing edge is
        implied, and is included here.
    z_nm
        The plane, in nm.

    Returns
    -------
    tuple of float
        The crossing radii, sorted ascending. A closed simple polygon crosses a
        plane an even number of times, so consecutive pairs bracket the body's
        intervals on the plane; the first pair is the lumen-adjacent one.

    Notes
    -----
    A vertex lying exactly on the plane is counted once, not twice: the interval
    test is half-open in ``z``, which is the standard fix for the double-count
    and is why the delivered table's vertex at ``(4.88, +1.4)`` gives ``4.88``
    rather than a duplicate.
    """
    import numpy as np

    points = profile.as_array() if isinstance(profile, PoreProfile) else profile
    starts = points
    ends = np.roll(points, -1, axis=0)
    z0, z1 = starts[:, 1], ends[:, 1]
    lower = np.minimum(z0, z1)
    upper = np.maximum(z0, z1)
    crossing = (lower <= z_nm) & (z_nm < upper)
    if not bool(np.any(crossing)):
        return ()
    fraction = (z_nm - z0[crossing]) / (z1[crossing] - z0[crossing])
    radii = starts[crossing, 0] + fraction * (ends[crossing, 0] - starts[crossing, 0])
    return tuple(sorted(float(value) for value in radii))


def _check_no_repeats(points: np.ndarray) -> None:
    """Raise if any two vertices coincide, naming the first pair.

    A repeated closing vertex is the common mistake and gets its own message:
    the closing edge is implied by the format, and repeating it would give the
    loop a zero-length edge that no mesher survives.
    """
    import numpy as np

    if bool(np.all(points[0] == points[-1])):
        raise ValueError(
            "the first and last vertices coincide; the closing edge is implied and the last "
            "vertex must not repeat the first"
        )
    order = np.lexsort((points[:, 1], points[:, 0]))
    sorted_points = points[order]
    same = np.all(np.diff(sorted_points, axis=0) == 0.0, axis=1)
    if bool(np.any(same)):
        first = int(np.argmax(same))
        r, z = sorted_points[first]
        raise ValueError(f"two vertices coincide at (r, z) = ({r:.6g}, {z:.6g}) nm")


def _check_simple(points: np.ndarray) -> None:
    """Raise if any two non-adjacent edges of the closed loop meet.

    Adjacent edges are excluded, sharing an endpoint by construction; a
    collinear back-track along a neighbour is caught by the zero-area and
    repeated-vertex checks instead. Quadratic in the vertex count, which is 185
    for the reference polygon and a few hundred for anything the FR-08 pipeline
    produces.
    """
    count = len(points)
    starts = points
    ends = [points[(i + 1) % count] for i in range(count)]
    for i in range(count):
        for j in range(i + 1, count):
            if j == i + 1 or (i == 0 and j == count - 1):
                continue
            if _segments_cross(starts[i], ends[i], starts[j], ends[j]):
                raise ValueError(
                    f"the loop is not simple: edge {i} from (r, z) = "
                    f"({starts[i][0]:.6g}, {starts[i][1]:.6g}) crosses edge {j} from "
                    f"({starts[j][0]:.6g}, {starts[j][1]:.6g}) nm"
                )


def _orientation(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Return twice the signed area of the triangle ``a, b, c``."""
    return float((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))


def _segments_cross(a: np.ndarray, b: np.ndarray, c: np.ndarray, d: np.ndarray) -> bool:
    """Whether segments ``ab`` and ``cd`` intersect, a touch included.

    The two cases are kept apart deliberately. A *proper* crossing has all four
    orientations non-zero and the endpoints of each segment on opposite sides of
    the other; anything with a zero orientation is collinear or touching, and is
    decided by whether the coincident point lies within the other segment. A
    touch counts as an intersection here: two non-adjacent edges of a pore
    boundary meeting at a point is a pinch, which the mesher cannot resolve.
    """
    d1, d2 = _orientation(c, d, a), _orientation(c, d, b)
    d3, d4 = _orientation(a, b, c), _orientation(a, b, d)
    proper = (d1 > 0.0) != (d2 > 0.0) and (d3 > 0.0) != (d4 > 0.0)
    if proper and 0.0 not in (d1, d2, d3, d4):
        return True
    for point, (start, end), cross in (
        (a, (c, d), d1),
        (b, (c, d), d2),
        (c, (a, b), d3),
        (d, (a, b), d4),
    ):
        if cross == 0.0 and _on_segment(start, end, point):
            return True
    return False


def _on_segment(start: np.ndarray, end: np.ndarray, point: np.ndarray) -> bool:
    """Whether ``point``, known collinear with ``start``-``end``, lies within it."""
    return bool(
        min(start[0], end[0]) <= point[0] <= max(start[0], end[0])
        and min(start[1], end[1]) <= point[1] <= max(start[1], end[1])
    )


def load_profile(name_or_path: str | Path) -> PoreProfile:
    """Load and validate a pore-profile fixture by name or by path.

    Parameters
    ----------
    name_or_path
        Fixture name (e.g. ``"clya_reference_profile"``) or a path to a YAML
        fixture.

    Returns
    -------
    PoreProfile
        The validated profile.

    Raises
    ------
    ValueError
        If the fixture declares a schema this version does not understand — the
        message names the file and the schema found, before any field error —
        or if it fails the polygon gate.
    """
    path = (
        Path(name_or_path)
        if Path(name_or_path).suffix in {".yaml", ".yml"}
        else profile_file(str(name_or_path))
    )
    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    schema = raw.get("schema") if isinstance(raw, dict) else None
    if schema != PROFILE_SCHEMA:
        raise ValueError(f"{path}: expected schema {PROFILE_SCHEMA!r}, found {schema!r}")
    return PoreProfile.model_validate(raw)


def write_profile(profile: PoreProfile, path: Path) -> Path:
    """Write ``profile`` as a ``nanopnp/profile/v1`` YAML document that :func:`load_profile` reads.

    Every float is written as Python's shortest round-trip representation, so
    the vertices read back bit for bit and the provenance block's measurements
    still describe them to round-off. The vertices are one ``[r, z]`` pair per
    line.

    Returns
    -------
    Path
        ``path``.
    """
    document = profile.model_dump(by_alias=True, mode="json", exclude_none=True)
    document["vertices"] = [[float(r), float(z)] for r, z in profile.vertices]
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(document, sort_keys=False, default_flow_style=None, width=100)
    path.write_text(text, encoding="utf-8")
    return path


def profile_from_csv(
    path: Path, *, name: str, source: str, citation: str, description: str | None = None
) -> PoreProfile:
    """Derive a profile fixture from a delivered ``r,z`` table.

    The one-way conversion: the CSV is the artefact as delivered and is never
    read at run time, and this is how the fixture beside it was built and how a
    test re-derives it. The digest is taken over the file's bytes exactly as
    they are on disk — line endings included — so it identifies the delivered
    table and not a normalisation of it.

    Parameters
    ----------
    path
        The ``r,z`` table: one vertex per line, in nm, in loop order, with the
        closing edge implied. Blank lines and ``#`` comments are ignored.
    name
        Fixture name.
    source, citation, description
        Provenance that is not in the table and cannot be derived from it.

    Returns
    -------
    PoreProfile
        The validated profile, its measurements taken from the table.

    Raises
    ------
    ValueError
        If a line is not a pair of numbers, or the loop fails the polygon gate.
    """
    import numpy as np

    raw = path.read_bytes()
    rows: list[tuple[float, float]] = []
    for number, line in enumerate(raw.decode("utf-8").splitlines(), start=1):
        text = line.split("#", 1)[0].strip()
        if not text:
            continue
        fields = text.split(",")
        if len(fields) != 2:
            raise ValueError(f"{path}:{number}: expected 'r,z' in nm, got {line.strip()!r}")
        try:
            rows.append((float(fields[0]), float(fields[1])))
        except ValueError as error:
            raise ValueError(
                f"{path}:{number}: {line.strip()!r} is not a pair of numbers"
            ) from error

    points = np.asarray(rows, dtype=np.float64)
    return PoreProfile(
        schema=PROFILE_SCHEMA,
        name=name,
        description=description,
        provenance=ProfileProvenance(
            source=source,
            citation=citation,
            sha256=hashlib.sha256(raw).hexdigest(),
            vertex_count=len(rows),
            min_vertex_spacing_nm=min_vertex_spacing(points),
            min_feature_size_nm=min_feature_size(points),
            signed_area_nm2=signed_area(points),
        ),
        vertices=rows,
    )
