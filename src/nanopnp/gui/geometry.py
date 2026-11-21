"""The geometry view-models: stage pictures, colour maps and the contour editor."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeAlias

from pydantic import ValidationError

from nanopnp.geometry.profile import (
    HAND_EDIT_SOURCE,
    PROFILE_SCHEMA,
    PoreProfile,
    ProfileProvenance,
    min_feature_size,
    min_vertex_spacing,
    profile_digest,
    signed_area,
    write_profile,
)
from nanopnp.io.case import (
    CaseDocument,
    dump_case,
)
from nanopnp.io.case_paths import (
    with_profile,
)
from nanopnp.io.store import Store

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Sequence

    import numpy as np

    from nanopnp.gui.solver import Produced
    from nanopnp.io.artefact import Artefact

__all__ = [
    "COLOUR_MAP_SIZE",
    "MODEL_FRAME",
    "STAGE_1_FRAME",
    "ImageModel",
    "Palette",
    "ProfileEditor",
    "colour_maps",
    "density_section",
    "lookup_table",
    "reduced_image",
    "stored_artefact",
]

STAGE_1_FRAME = "stage-1 frame"

MODEL_FRAME = "model frame"

# Nine anchors of viridis (van der Walt and Smith, CC0), interpolated to 256 entries.
_VIRIDIS: tuple[tuple[int, int, int], ...] = (
    (68, 1, 84),
    (71, 44, 122),
    (59, 81, 139),
    (44, 113, 142),
    (33, 144, 141),
    (39, 173, 129),
    (92, 200, 99),
    (170, 220, 50),
    (253, 231, 37),
)


# Moreland 2009 cool-to-warm, 255 entries: an odd count, so zero on a scale [-L, L] lands on the
# neutral anchor.
_DIVERGING: tuple[tuple[int, int, int], ...] = (
    (59, 76, 192),
    (221, 221, 221),
    (180, 4, 38),
)

# A dark middle, for the dark theme, where a light middle reads as a bright slab: the four outer
# anchors each side of Crameri's berlin (Scientific colour maps 8, MIT; as Matplotlib 3.10 ships
# it) about a neutral grey a step above the dark canvas, so zero reads as neither sign. Nine
# anchors over 255 entries put zero on the grey.
_DIVERGING_DARK: tuple[tuple[int, int, int], ...] = (
    (158, 176, 255),
    (98, 166, 224),
    (50, 128, 166),
    (32, 82, 106),
    (44, 46, 50),
    (97, 32, 11),
    (150, 74, 54),
    (202, 123, 113),
    (255, 173, 173),
)

Palette: TypeAlias = str
"""A colour map's name: one of the workbench's own five, else any Matplotlib registers, its
reverse ending ``_r``. ``diverging`` runs from blue to red; ``diverging_r`` from red to blue,
positive blue; the ``_dark`` pair the same ways through a dark middle."""

_PALETTES: dict[str, tuple[tuple[tuple[int, int, int], ...], int]] = {
    "viridis": (_VIRIDIS, 256),
    "diverging": (_DIVERGING, 255),
    "diverging_r": (_DIVERGING[::-1], 255),
    "diverging_dark": (_DIVERGING_DARK, 255),
    "diverging_dark_r": (_DIVERGING_DARK[::-1], 255),
}

COLOUR_MAP_SIZE = 256
"""The entries of a lookup table sampled from a Matplotlib colour map."""


def colour_maps() -> tuple[str, ...]:
    """Return every colour map's name: the workbench's own, then Matplotlib's, each reversed too.

    Raises
    ------
    ValueError
        If Matplotlib, of the ``gui`` extra, is not installed.
    """
    borrowed = sorted(name for name in _matplotlib_maps() if name not in _PALETTES)
    return (*_PALETTES, *borrowed)


def lookup_table(palette: Palette = "viridis") -> np.ndarray:
    """Return a colour map's N x 4 RGBA lookup table: the workbench's own, else Matplotlib's.

    Raises
    ------
    ValueError
        If no colour map has that name, or Matplotlib, of the ``gui`` extra, is not installed.
    """
    import numpy as np

    if palette not in _PALETTES:
        maps = _matplotlib_maps()
        if palette not in maps:
            raise ValueError(
                f"no colour map is named {palette!r}: the workbench's own are "
                f"{', '.join(_PALETTES)}, and Matplotlib's are listed by colour_maps()"
            )
        sampled = maps[palette](np.linspace(0.0, 1.0, COLOUR_MAP_SIZE), bytes=True)
        return np.ascontiguousarray(sampled, dtype=np.uint8)
    colours, size = _PALETTES[palette]
    anchors = np.asarray(colours, dtype=np.float64)
    positions = np.linspace(0.0, 1.0, len(anchors))
    samples = np.linspace(0.0, 1.0, size)
    table = np.empty((size, 4), dtype=np.uint8)
    for channel in range(3):
        table[:, channel] = np.round(np.interp(samples, positions, anchors[:, channel]))
    table[:, 3] = 255
    return table


def _matplotlib_maps() -> Any:  # noqa: ANN401 - Matplotlib's colour-map registry
    try:
        from matplotlib import colormaps
    except ImportError as error:
        raise ValueError(
            "a colour map other than the workbench's own needs Matplotlib: install nanopnp's "
            f"gui extra ({error})"
        ) from None
    return colormaps


@dataclass(frozen=True)
class ImageModel:
    """A field on a uniform ``[z, x]`` grid; ``NaN`` is drawn transparent."""

    values: np.ndarray
    x_nm: np.ndarray
    z_nm: np.ndarray
    scale: tuple[float, float]
    title: str
    x_label: str
    frame: str
    palette: Palette = "viridis"

    @property
    def width(self) -> int:
        """Columns."""
        return int(self.values.shape[1])

    @property
    def height(self) -> int:
        """Rows."""
        return int(self.values.shape[0])

    @property
    def spacing_nm(self) -> tuple[float, float]:
        """``(Δx, Δz)`` between node centres."""
        return (
            float(self.x_nm[1] - self.x_nm[0]) if self.width > 1 else 1.0,
            float(self.z_nm[1] - self.z_nm[0]) if self.height > 1 else 1.0,
        )

    @property
    def extent_nm(self) -> tuple[float, float, float, float]:
        """``(x_low, x_high, z_low, z_high)`` of the outer pixel edges."""
        dx, dz = self.spacing_nm
        return (
            float(self.x_nm[0]) - 0.5 * dx,
            float(self.x_nm[-1]) + 0.5 * dx,
            float(self.z_nm[0]) - 0.5 * dz,
            float(self.z_nm[-1]) + 0.5 * dz,
        )

    def pixel_centre(self, column: int, row: int) -> tuple[float, float]:
        """Return the ``(x, z)`` a display pixel is centred on; row 0 is the top, at maximum z."""
        return float(self.x_nm[column]), float(self.z_nm[self.height - 1 - row])

    def pixel_of(self, x_nm: float, z_nm: float) -> tuple[int, int]:
        """Return the display ``(column, row)`` whose pixel contains ``(x, z)``."""
        dx, dz = self.spacing_nm
        column = math.floor((x_nm - float(self.x_nm[0])) / dx + 0.5)
        index = math.floor((z_nm - float(self.z_nm[0])) / dz + 0.5)
        return column, self.height - 1 - index

    def display(self) -> np.ndarray:
        """Return the values in display order: row 0 at maximum z, x increasing to the right."""
        flipped: np.ndarray = self.values[::-1, :]
        return flipped

    def rgba(self) -> bytes:
        """Return the image as tightly packed RGBA8888 rows, top row first."""
        import numpy as np

        shown = self.display()
        finite = np.isfinite(shown)
        index = self.colour_index(np.where(finite, shown, self.scale[0]))
        pixels = lookup_table(self.palette)[index]
        pixels[~finite] = 0
        return bytes(np.ascontiguousarray(pixels, dtype=np.uint8).tobytes())

    def colour_index(self, values: np.ndarray | float) -> np.ndarray:
        """Return the lookup-table entry each value is coloured with, clipped to the scale."""
        import numpy as np

        low, high = self.scale
        span = high - low if high > low else 1.0
        # The table's size, not the table: building it is :meth:`rgba`'s job.
        last = _PALETTES[self.palette][1] - 1
        fraction = np.clip((np.asarray(values, dtype=np.float64) - low) / span, 0.0, 1.0)
        index: np.ndarray = np.round(fraction * last).astype(np.intp)
        return index


def reduced_image(
    r_nm: np.ndarray, z_nm: np.ndarray, values: np.ndarray, *, quantity: str
) -> ImageModel:
    """Return a stage-3 reduced field as an image; means use [0, 1], variances ``[0, max]``."""
    import numpy as np

    data = np.asarray(values, dtype=np.float64)
    if quantity == "mean":
        scale = (0.0, 1.0)
        title = "stage 3: (r, z) mean, scale [0, 1]"
    else:
        peak = float(np.nanmax(data)) if np.any(np.isfinite(data)) else 0.0
        scale = (0.0, peak if peak > 0.0 else 1.0)
        title = f"stage 3: {quantity.replace('_', ' ')}, scale [0, {scale[1]:.3g}]"
    return ImageModel(
        values=data,
        x_nm=np.asarray(r_nm, dtype=np.float64),
        z_nm=np.asarray(z_nm, dtype=np.float64),
        scale=scale,
        title=title,
        x_label="r (nm)",
        frame=STAGE_1_FRAME,
    )


def density_section(
    values: np.ndarray, x_nm: np.ndarray, z_nm: np.ndarray, *, y_index: int
) -> ImageModel:
    """Return the axial section ``y = 0`` of a stage-2 map, over ``x ∈ [-R, R]``."""
    import numpy as np

    return ImageModel(
        values=np.asarray(values[:, y_index, :], dtype=np.float64),
        x_nm=np.asarray(x_nm, dtype=np.float64),
        z_nm=np.asarray(z_nm, dtype=np.float64),
        scale=(0.0, 1.0),
        title="stage 2: density, section y = 0, scale [0, 1]",
        x_label="x (nm)",
        frame=STAGE_1_FRAME,
    )


def stored_artefact(event: Produced) -> Artefact:
    """Return the stored artefact an event names; say so if it is gone."""
    found = Store(event.store).get(event.schema, event.hash)
    if found is None:
        raise FileNotFoundError(
            f"{event.name}'s artefact {event.schema} {event.hash[:12]} is not in the store at "
            f"{event.store}; it was removed after the build reported it"
        )
    return found


Vertex: TypeAlias = tuple[float, float]


def _loader_text(error: ValidationError) -> str:
    first = error.errors()[0]
    message = str(first.get("msg", error))
    prefix = "Value error, "
    return message[len(prefix) :] if message.startswith(prefix) else message


@dataclass
class ProfileEditor:
    """A hand edit of a pore profile: the operations, their undo, and the document they make.

    Parameters
    ----------
    parent_digest
        ``provenance.sha256`` the edit records: the digest of the profile it was edited from.
    start
        The loop the edit started from, which the atoms it moves are read against.
    seeded
        Whether the loop was traced from the map, not opened on a stored outline.
    """

    vertices: list[Vertex]
    parent_digest: str
    parent_name: str
    start: list[Vertex] = field(default_factory=list)
    seeded: bool = False
    _undo: list[list[Vertex]] = field(default_factory=list, repr=False)
    _redo: list[list[Vertex]] = field(default_factory=list, repr=False)

    @classmethod
    def from_profile(cls, profile: PoreProfile) -> ProfileEditor:
        """Start from a profile document: stage 4's, or a supplied one."""
        vertices = [(float(r), float(z)) for r, z in profile.vertices]
        return cls(
            vertices=vertices,
            parent_digest=profile_digest(profile),
            parent_name=profile.name,
            start=list(vertices),
        )

    @classmethod
    def from_seed(cls, vertices: Sequence[Vertex], *, digest: str, name: str) -> ProfileEditor:
        """Start from a loop stage 4's gate refused."""
        loop = [(float(r), float(z)) for r, z in vertices]
        return cls(
            vertices=loop, parent_digest=digest, parent_name=name, start=list(loop), seeded=True
        )

    def _push(self) -> None:
        self._undo.append(list(self.vertices))
        self._redo.clear()

    def move(self, index: int, r_nm: float, z_nm: float) -> None:
        """Move vertex ``index`` to ``(r, z)``: one undoable step, however it was dragged."""
        self._check_index(index)
        self._push()
        self.vertices[index] = (float(r_nm), float(z_nm))

    def insert(self, edge: int) -> int:
        """Insert a vertex at the midpoint of edge ``edge``; return its index."""
        self._check_index(edge)
        a = self.vertices[edge]
        b = self.vertices[(edge + 1) % len(self.vertices)]
        self._push()
        self.vertices.insert(edge + 1, (0.5 * (a[0] + b[0]), 0.5 * (a[1] + b[1])))
        return edge + 1

    def delete(self, index: int) -> None:
        """Delete vertex ``index``. A loop keeps at least three.

        Raises
        ------
        ValueError
            If the loop would be left with fewer than three vertices.
        """
        self._check_index(index)
        if len(self.vertices) <= 3:
            raise ValueError(
                f"a closed polygon needs at least three vertices, and this one has "
                f"{len(self.vertices)}; vertex {index} cannot be deleted"
            )
        self._push()
        del self.vertices[index]

    def undo(self) -> bool:
        """Return to the loop before the last edit; ``False`` if there is none."""
        if not self._undo:
            return False
        self._redo.append(list(self.vertices))
        self.vertices = self._undo.pop()
        return True

    def redo(self) -> bool:
        """Re-apply the last edit undone; ``False`` if there is none."""
        if not self._redo:
            return False
        self._undo.append(list(self.vertices))
        self.vertices = self._redo.pop()
        return True

    def _check_index(self, index: int) -> None:
        if not 0 <= index < len(self.vertices):
            raise IndexError(f"vertex {index} is not in a loop of {len(self.vertices)}")

    @property
    def can_undo(self) -> bool:
        """Whether there is an edit to undo."""
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        """Whether there is an undone edit to re-apply."""
        return bool(self._redo)

    @property
    def changed(self) -> bool:
        """Whether the loop is other than the outline it opened on: a seed, or an edit applied."""
        return self.seeded or self.can_undo

    @property
    def name(self) -> str:
        """The edited profile's name: its parent's, marked as a hand edit."""
        return f"{self.parent_name}-{HAND_EDIT_SOURCE}"

    def document(self) -> PoreProfile:
        """Return the edit as a validated ``nanopnp/profile/v0.5`` document.

        Raises
        ------
        ValueError
            The loader's sentence, naming the vertex, if the loop is not a simple closed polygon.
        """
        import numpy as np

        points = np.asarray(self.vertices, dtype=np.float64).reshape(-1, 2)
        try:
            provenance = ProfileProvenance(
                source=HAND_EDIT_SOURCE,
                citation=self.parent_name,
                sha256=self.parent_digest,
                vertex_count=len(points),
                min_vertex_spacing_nm=min_vertex_spacing(points) if len(points) else 0.0,
                min_feature_size_nm=min_feature_size(points) if len(points) >= 3 else 0.0,
                signed_area_nm2=signed_area(points) if len(points) else 0.0,
            )
            return PoreProfile(
                schema=PROFILE_SCHEMA,
                name=self.name,
                description=(
                    f"Edited by hand in the nanopnp desktop shell from {self.parent_name}, in "
                    "the stage-1 frame"
                ),
                provenance=provenance,
                vertices=list(self.vertices),
            )
        except ValidationError as error:
            raise ValueError(_loader_text(error)) from None

    @property
    def problem(self) -> str | None:
        """The loader's refusal of the loop as it stands, or ``None`` if it would load."""
        try:
            self.document()
        except ValueError as error:
            return str(error)
        return None

    def _target(self, directory: str | Path) -> tuple[PoreProfile, Path]:
        profile = self.document()
        root = Path(directory).expanduser().resolve()
        return profile, root / f"{HAND_EDIT_SOURCE}-{profile_digest(profile)[:16]}.yaml"

    def save(self, directory: str | Path) -> Path:
        """Write the edit as a profile document named by its digest, and return its absolute path.

        Raises
        ------
        ValueError
            If the loop would not load; nothing is written.
        """
        profile, path = self._target(directory)
        return write_profile(profile, path)

    def save_case(self, case: CaseDocument, case_path: str | Path) -> tuple[Path, Path]:
        """Write the edit and a derived case beside the original, and return both paths.

        The original is never modified.

        Raises
        ------
        ValueError
            If the loop or the derived case would not load; nothing is written.
        """
        source = Path(case_path).expanduser().resolve()
        profile, path = self._target(source.parent)
        derived = with_profile(case, path)
        write_profile(profile, path)
        return path, dump_case(derived, source.with_name(f"{source.stem}.{path.stem}.yaml"))
