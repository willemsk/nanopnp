"""The pore profile fixture: a closed ``(r, z)`` polygon, validated at the boundary."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from nanopnp.core.hashing import content_hash
from nanopnp.core.paths import profile_file
from nanopnp.io.artefact import PROFILE_ARTEFACT_SCHEMA

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

PROFILE_SCHEMA: str = PROFILE_ARTEFACT_SCHEMA

REFERENCE_SOURCES: frozenset[str] = frozenset({"model-report", "author-supplied"})

PIPELINE_SOURCE: str = "pipeline"

HAND_EDIT_SOURCE: str = "hand-edit"

MEASUREMENT_TOL: float = 1e-9


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProfileProvenance(_Strict):
    source: str
    citation: str
    sha256: str
    vertex_count: int
    min_vertex_spacing_nm: float
    min_feature_size_nm: float
    signed_area_nm2: float


class PoreProfile(_Strict):
    model_config = ConfigDict(extra="forbid")

    schema_id: str = Field(alias="schema")
    name: str
    description: str | None = None
    provenance: ProfileProvenance
    vertices: list[tuple[float, float]]

    @model_validator(mode="after")
    def _check_polygon(self) -> PoreProfile:
        import numpy as np

        points = self.as_array()
        if len(points) < 3:
            raise ValueError(f"a closed polygon needs at least three vertices, got {len(points)}")
        # First: a NaN coordinate fails no comparison, so every test below it,
        # the half-plane test included, would pass it by.
        finite = np.isfinite(points).all(axis=1)
        if not finite.all():
            index = int(np.flatnonzero(~finite)[0])
            raise ValueError(
                f"vertex {index} is ({points[index, 0]}, {points[index, 1]}); every coordinate "
                "must be a finite number of nanometres"
            )
        if float(points[:, 0].min()) < 0.0:
            index = int(np.argmin(points[:, 0]))
            raise ValueError(
                f"vertex radius must be non-negative in the (r, z) half-plane; the smallest is "
                f"{float(points[index, 0]):.6g} nm, at vertex {index}"
            )
        _check_no_repeats(points)
        _check_simple(points)
        if abs(signed_area(points)) <= 0.0:
            raise ValueError("this polygon encloses no area")
        return self

    @model_validator(mode="after")
    def _check_provenance_describes_these_vertices(self) -> PoreProfile:
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
            if not abs(claimed - measured) <= MEASUREMENT_TOL:  # NaN fails
                raise ValueError(
                    f"provenance.{key} is {claimed!r} but these vertices give {measured!r}; the "
                    "provenance block does not describe this polygon"
                )
        return self

    @property
    def is_reference(self) -> bool:
        return self.provenance.source in REFERENCE_SOURCES

    def require_reference(self, purpose: str) -> None:
        if not self.is_reference:
            allowed = ", ".join(sorted(REFERENCE_SOURCES))
            raise ValueError(
                f"{purpose} needs the reference geometry, but profile {self.name!r} has "
                f"provenance.source {self.provenance.source!r}; the reference sources are {allowed}"
            )

    def as_array(self) -> np.ndarray:
        import numpy as np

        return np.asarray(self.vertices, dtype=np.float64).reshape(-1, 2)

    @property
    def extent_r_nm(self) -> tuple[float, float]:
        radii = self.as_array()[:, 0]
        return float(radii.min()), float(radii.max())

    @property
    def extent_z_nm(self) -> tuple[float, float]:
        axial = self.as_array()[:, 1]
        return float(axial.min()), float(axial.max())

    @property
    def is_clockwise(self) -> bool:
        return signed_area(self.as_array()) < 0.0


def profile_digest(profile: PoreProfile) -> str:
    return content_hash(PROFILE_SCHEMA, profile.model_dump(by_alias=True, mode="json"))


def signed_area(points: np.ndarray) -> float:
    import numpy as np

    following = np.roll(points, -1, axis=0)
    return float(0.5 * np.sum(points[:, 0] * following[:, 1] - following[:, 0] * points[:, 1]))


def min_vertex_spacing(points: np.ndarray) -> float:
    import numpy as np

    return float(np.min(np.linalg.norm(np.roll(points, -1, axis=0) - points, axis=1)))


LOCAL_EDGES: int = 2


def min_feature_size(points: np.ndarray, *, local_edges: int = LOCAL_EDGES) -> float:
    return float(feature_sizes(points, local_edges=local_edges).min())


def feature_sizes(points: np.ndarray, *, local_edges: int = LOCAL_EDGES) -> np.ndarray:
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
        local = np.minimum((edge - vertex) % count, (vertex - edge - 1) % count) < neighbourhood
        offset = points[vertex] - starts
        parameter = np.clip(np.einsum("ij,ij->i", offset, span) / safe, 0.0, 1.0)
        distance = np.linalg.norm(offset - parameter[:, None] * span, axis=1)
        sizes[vertex] = np.min(distance[~local])
    return sizes


def plane_crossings(profile: PoreProfile | np.ndarray, z_nm: float) -> tuple[float, ...]:
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
        pair = sorted((int(order[first]), int(order[first + 1])))
        raise ValueError(
            f"two vertices coincide at (r, z) = ({r:.6g}, {z:.6g}) nm: vertices {pair[0]} and "
            f"{pair[1]}"
        )


def _check_simple(points: np.ndarray) -> None:
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
    return float((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))


def _segments_cross(a: np.ndarray, b: np.ndarray, c: np.ndarray, d: np.ndarray) -> bool:
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
    return bool(
        min(start[0], end[0]) <= point[0] <= max(start[0], end[0])
        and min(start[1], end[1]) <= point[1] <= max(start[1], end[1])
    )


def load_profile(name_or_path: str | Path) -> PoreProfile:
    path = (
        Path(name_or_path)
        if isinstance(name_or_path, Path) or Path(name_or_path).suffix in {".yaml", ".yml"}
        else profile_file(str(name_or_path))
    )
    with path.open(encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    schema = raw.get("schema") if isinstance(raw, dict) else None
    if schema != PROFILE_SCHEMA:
        raise ValueError(f"{path}: expected schema {PROFILE_SCHEMA!r}, found {schema!r}")
    return PoreProfile.model_validate(raw)


def write_profile(profile: PoreProfile, path: Path) -> Path:
    document = profile.model_dump(by_alias=True, mode="json", exclude_none=True)
    document["vertices"] = [[float(r), float(z)] for r, z in profile.vertices]
    path.parent.mkdir(parents=True, exist_ok=True)
    text = yaml.safe_dump(document, sort_keys=False, default_flow_style=None, width=100)
    path.write_text(text, encoding="utf-8")
    return path


def profile_from_csv(
    path: Path, *, name: str, source: str, citation: str, description: str | None = None
) -> PoreProfile:
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
