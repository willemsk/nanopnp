"""The geometry tab's view-model: stages 1-6 as they land, their pictures, and the contour editor.

§8.1's second GUI increment, and Phase 2 criterion 4: load a structure, build
stages 1 to 6 from the shell, inspect each stage's artefact as it lands, and
override the contour by hand. Everything the tab decides lives here, and nothing
here imports PySide6, NGSolve, Netgen or NumPy at module scope — the discipline of
:mod:`nanopnp.gui.run_model` and :mod:`nanopnp.gui.convergence`, for the same
reason: ``PySide6.QtWidgets`` does not import on the Linux push gate
(`.knowledge/07-software-stack.md` §5), so a rule implemented in a widget would be
asserted on two of the seven matrix jobs.

**What landed is read from the store by its hash, never from a caption.** The
walk's :class:`~nanopnp.core.stages.ArtefactHook` crosses the process boundary as
:class:`~nanopnp.gui.solver.Produced`, and :class:`StageList` and
:func:`load_view` are pure functions of those events and of the store they name
(WP24 D1).

**Two frames, and every picture names its own** (WP24 D4, Design §1). Stages 1
to 4 are in the stage-1 frame, in which the profile document is written; stage 5
shifts ``z ← z - centre_z_nm``, so the region and the mesh are in the model frame.
The editor draws and writes the stage-1 frame, with the membrane slab drawn at
``centre_z_nm ± thickness_nm/2``. An editor that wrote the region record's
vertices back would shift them twice on the next run, invisibly at ClyA's
``centre_z_nm = 0``.

**A pixel sits on its node** (WP24 D11, Design §2). A reduced map's column j is
the bin centred on ``r = j·h``, and a density's node j sits at its own
coordinate, so an image of n columns spans ``[x₀ - h/2, x_{n-1} + h/2]``.
Drawing it on ``[0, n·h]`` would move every wall outward by h/2, which is the
``pqr2grid`` erratum of `.knowledge/04` §1.2 reintroduced by a display.

**A hand edit is a supplied profile, and enters a run only through
``inputs.profile``** (WP24 D5, D6; the §5.3.1 NOTE on ``geometry.contour``). The
editor enforces what the loader enforces, by calling the loader's own validator,
and measures the §5.2.1 criteria only on request, in a spawned child
(:mod:`nanopnp.gui.assess`), recording them without enforcing them (D8).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal, TypeAlias

from pydantic import ValidationError

from nanopnp.core.stages import describe, walk_order
from nanopnp.density.map import PAYLOAD_NAME as DENSITY_PAYLOAD
from nanopnp.density.map import DensityMap
from nanopnp.geometry.profile import (
    HAND_EDIT_SOURCE,
    PROFILE_SCHEMA,
    PoreProfile,
    ProfileProvenance,
    load_profile,
    min_feature_size,
    min_vertex_spacing,
    profile_digest,
    signed_area,
    write_profile,
)
from nanopnp.geometry.region import PAYLOAD_NAME as REGION_PAYLOAD
from nanopnp.geometry.region import read_region
from nanopnp.io.case import (
    CaseDocument,
    MembraneSpec,
    dump_case,
)
from nanopnp.io.case_paths import (
    UnknownCasePathError,
    value_at,
    with_profile,
)
from nanopnp.io.store import Store
from nanopnp.pipeline.case import resolve
from nanopnp.pipeline.run import (
    DENSITY_RECORD_KEYS,
    REDUCTION_RECORD_KEYS,
    STRUCTURE_RECORD_KEYS,
    selected_stages,
)
from nanopnp.symmetry.reduce import PAYLOAD_NAME as REDUCED_PAYLOAD
from nanopnp.symmetry.reduce import QUANTITIES, ReducedMap

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Mapping, Sequence

    import numpy as np

    from nanopnp.gui.case_model import CaseEditor
    from nanopnp.gui.run_model import RunModel
    from nanopnp.gui.solver import Produced
    from nanopnp.io.artefact import Artefact

__all__ = [
    "BUILD_UPTO",
    "GEOMETRY_STAGES",
    "MODEL_FRAME",
    "STAGE_1_FRAME",
    "ImageModel",
    "ImageView",
    "OutlineView",
    "Palette",
    "ProfileEditor",
    "StageList",
    "StageRow",
    "StageStatus",
    "StageView",
    "SummaryView",
    "ViewTransform",
    "can_build",
    "density_section",
    "load_structure",
    "load_view",
    "lookup_table",
    "membrane_slab",
    "nearest_edge",
    "nearest_vertex",
    "reduced_image",
    "stored_artefact",
]

GEOMETRY_STAGES: tuple[str, ...] = (
    *(name for name in walk_order() if describe(name).needs_section == "structure"),
    "region",
    "mesh",
)
"""Stages 1 to 6: the ones the geometry tab lists, in the order a walk runs them.

The structure stages come from the registry, each declaring the case section it
needs; ``region`` and ``mesh`` are this tab's own choice of view.
"""

BUILD_UPTO = "mesh"
"""Where **Build geometry** stops: the command line's ``run --upto mesh`` (WP24 D3)."""

STAGE_1_FRAME = "stage-1 frame"
"""Caption of a view in the frame stage 1 aligns to and the profile document is in."""

MODEL_FRAME = "model frame"
"""Caption of a view after stage 5's ``z ← z - centre_z_nm``."""

StageStatus: TypeAlias = Literal["waiting", "running", "stored", "cached", "failed", "cancelled"]
"""Where one stage of a build is. ``stored`` did the work, ``cached`` found it in the
store; both have an artefact to show."""


# -- the stage list -------------------------------------------------------------


@dataclass(frozen=True)
class StageRow:
    """One stage of the list: what it is, where it got to, and what it left.

    Parameters
    ----------
    name, number, title
        The stage as the registry describes it, read without importing it (FR-27).
    status
        Where the build got to with it.
    produced
        The event naming its artefact, once it has one.
    """

    name: str
    number: int
    title: str
    status: StageStatus
    produced: Produced | None = None

    @property
    def hash(self) -> str:
        """The artefact's hash, or ``""`` before there is one."""
        return self.produced.hash if self.produced is not None else ""


def planned_stages(document: CaseDocument) -> tuple[str, ...]:
    """Return the geometry stages this case walks, in order.

    Stages 1 to 4 need ``structure:``; stage 5 needs a generated mesh. The
    rule :func:`nanopnp.pipeline.run.run_case` applies, taken from the driver's own
    :func:`~nanopnp.pipeline.run.selected_stages` so the list cannot drift from the walk.

    Raises
    ------
    nanopnp.io.case.CaseValidationError
        If the case does not resolve.
    """
    walked = selected_stages(resolve(document), None)
    return tuple(name for name in walked if name in GEOMETRY_STAGES)


def can_build(document: CaseDocument) -> bool:
    """Whether **Build geometry** is offered for this case (WP24 D3).

    Only a case whose stages 5 and 6 build its mesh has geometry to build; a case
    supplying ``inputs.mesh`` reads a file at stage 6 and runs nothing before it.
    A case that does not resolve is not offered either: the child would refuse it
    with the diagnostic the Case tab already shows.
    """
    try:
        return resolve(document).generates_mesh
    except (ValueError, NotImplementedError):
        return False


@dataclass(frozen=True)
class StageList:
    """The geometry stages of one case, and a projection of a run onto them.

    Parameters
    ----------
    planned
        :func:`planned_stages` of the case being built.
    """

    planned: tuple[str, ...]

    def rows(self, model: RunModel) -> tuple[StageRow, ...]:
        """Return one row per planned stage, as the run's own event stream places it.

        A pure function of the model, so a test writes the stream by hand. A
        stage with a :class:`~nanopnp.gui.solver.Produced` is ``stored`` or
        ``cached``; the stage the walk last entered without producing anything is
        ``running`` while the run is, and ``failed`` or ``cancelled`` once it has
        stopped; every other stage is ``waiting``.
        """
        produced = {event.name: event for event in model.produced}
        entered = model.walked[-1] if model.walked else None
        rows: list[StageRow] = []
        for name in self.planned:
            description = describe(name)
            status: StageStatus = "waiting"
            event = produced.get(name)
            if event is not None:
                status = "cached" if event.cached else "stored"
            elif name == entered:
                if model.state == "running":
                    status = "running"
                elif model.state in ("failed", "cancelled"):
                    status = model.state
            rows.append(
                StageRow(
                    name=name,
                    number=description.number,
                    title=description.title,
                    status=status,
                    produced=event,
                )
            )
        return tuple(rows)


def load_structure(editor: CaseEditor, path: str | Path) -> Path:
    """Stage ``structure.source.path`` as the absolute path of a picked file (WP24 D7).

    Absolute, because case paths resolve against the process's working
    directory and a double-clicked shell has none that means anything. Inputs are
    hashed by content (§5.3.2), so the spelling moves no key.

    Returns
    -------
    Path
        The path staged.

    Raises
    ------
    UnknownCasePathError
        If the case declares no ``structure:`` section. There is then no point
        group to align the structure to, and the shell does not invent one: the
        section is written in the case file (``docs/guide/case-files.md``).
    nanopnp.io.case.CaseValidationError
        If the value is refused, with the editor's own diagnostic.
    """
    absolute = Path(path).expanduser().resolve()
    try:
        value_at(editor.document, "structure.source")
    except UnknownCasePathError:
        raise UnknownCasePathError(
            f"case {editor.document.name!r} carries no structure: section, so there is no point "
            "group to align a structure to; write the section, naming "
            "structure.symmetry.point_group, in the case file first"
        ) from None
    editor.stage("structure.source.path", str(absolute))
    return absolute


def membrane_slab(document: CaseDocument) -> tuple[float, float]:
    """Return the bilayer's z extent in the stage-1 frame: ``centre ± thickness/2`` (WP24 D4)."""
    membrane = document.geometry.membrane if document.geometry is not None else MembraneSpec()
    half = 0.5 * membrane.thickness_nm
    return membrane.centre_z_nm - half, membrane.centre_z_nm + half


# -- images -----------------------------------------------------------------------

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
"""Nine anchors of viridis (van der Walt and Smith, CC0), interpolated to 256 entries.

Perceptually uniform and monotone in lightness, so a density of 0.25 reads as a
quarter of the way up in greyscale too; the isolevel is not a colour boundary."""


_DIVERGING: tuple[tuple[int, int, int], ...] = (
    (59, 76, 192),
    (221, 221, 221),
    (180, 4, 38),
)
"""Moreland's cool-to-warm diverging map (Moreland 2009, *Diverging Color Maps for
Scientific Visualization*): blue, a neutral grey, red, interpolated to 255 entries.

An odd count, so that the middle entry *is* the neutral anchor and a value of zero
on a scale ``[-L, L]`` lands on it exactly; negative is blue and positive red
(WP31 D8)."""

Palette: TypeAlias = Literal["viridis", "diverging"]
"""Which lookup table an image is coloured with: sequential, or diverging about zero."""

_PALETTES: dict[str, tuple[tuple[tuple[int, int, int], ...], int]] = {
    "viridis": (_VIRIDIS, 256),
    "diverging": (_DIVERGING, 255),
}
"""Each palette's anchors and its entry count."""


def lookup_table(palette: Palette = "viridis") -> np.ndarray:
    """Return a palette's N x 4 RGBA lookup table, interpolated from its anchors."""
    import numpy as np

    colours, size = _PALETTES[palette]
    anchors = np.asarray(colours, dtype=np.float64)
    positions = np.linspace(0.0, 1.0, len(anchors))
    samples = np.linspace(0.0, 1.0, size)
    table = np.empty((size, 4), dtype=np.uint8)
    for channel in range(3):
        table[:, channel] = np.round(np.interp(samples, positions, anchors[:, channel]))
    table[:, 3] = 255
    return table


@dataclass(frozen=True)
class ImageModel:
    """A field on a uniform ``[z, x]`` grid, as an image and as the frame it sits in.

    Parameters
    ----------
    values
        ``[z, x]`` samples, ``float64``. ``NaN`` is drawn transparent.
    x_nm, z_nm
        The node (or bin-centre) coordinates of the columns and rows, uniform.
    scale
        ``(low, high)``: the values mapped to the ends of the lookup table.
    title
        What the image shows, as its caption says it.
    x_label
        The horizontal axis: ``r`` for a reduced map, ``x`` for a section.
    frame
        :data:`STAGE_1_FRAME` or :data:`MODEL_FRAME`.
    palette
        The lookup table: ``viridis`` for a density, ``diverging`` for a signed
        charge on a scale symmetric about zero (WP31 D8).
    """

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
        """``(x_low, x_high, z_low, z_high)`` of the image's outer edges.

        Half a spacing beyond the first and last nodes, because a pixel is
        centred on its node (Design §2).
        """
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
        """Return the image as tightly packed RGBA8888 rows, top row first.

        The widget wraps these bytes in a ``QImage`` and draws it into the
        rectangle :class:`ViewTransform` maps :attr:`extent_nm` to; it decides
        nothing about colour or orientation.
        """
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
    """Return one field of a stage-3 reduction as an image (WP24 D11).

    The mean shares the fixed [0, 1] scale of the density (VER-49's bounds); a
    variance is shown on its own scale, ``[0, max]``, and its title says so.
    """
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
    """Return the axial section ``y = 0`` of a stage-2 map, over ``x ∈ [-R, R]`` (WP24 D11).

    Over the whole diameter rather than ``r ≥ 0``, so that the Cₙ asymmetry the
    reduction averages away is visible before it is averaged.

    Parameters
    ----------
    values
        The map, ``[z, y, x]``.
    x_nm, z_nm
        Its node coordinates.
    y_index
        The node at ``y = 0``: the grid's half-width.
    """
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


# -- the transform ---------------------------------------------------------------


@dataclass(frozen=True)
class ViewTransform:
    """A data rectangle in nm mapped into a widget rectangle in pixels, at one scale.

    Equal nm per pixel on both axes: a pore drawn with a stretched aspect would
    make a constriction look wider or narrower than it is. z increases upwards,
    because screens count downwards.

    Parameters
    ----------
    x_range, z_range
        The data to fit, in nm.
    width, height
        The widget's drawable area, in pixels.
    margin
        Pixels left free on every side.
    """

    x_range: tuple[float, float]
    z_range: tuple[float, float]
    width: float
    height: float
    margin: float = 24.0

    @property
    def scale(self) -> float:
        """Pixels per nm."""
        span_x = max(self.x_range[1] - self.x_range[0], 1e-12)
        span_z = max(self.z_range[1] - self.z_range[0], 1e-12)
        room_x = max(self.width - 2.0 * self.margin, 1.0)
        room_z = max(self.height - 2.0 * self.margin, 1.0)
        return min(room_x / span_x, room_z / span_z)

    @property
    def _origin(self) -> tuple[float, float]:
        """The pixel of ``(x_low, z_low)``, centring the data in the widget."""
        s = self.scale
        used_x = (self.x_range[1] - self.x_range[0]) * s
        used_z = (self.z_range[1] - self.z_range[0]) * s
        left = 0.5 * (self.width - used_x)
        bottom = self.height - 0.5 * (self.height - used_z)
        return left, bottom

    def to_screen(self, x_nm: float, z_nm: float) -> tuple[float, float]:
        """Return the pixel of a point in nm."""
        left, bottom = self._origin
        s = self.scale
        return left + (x_nm - self.x_range[0]) * s, bottom - (z_nm - self.z_range[0]) * s

    def to_data(self, x_px: float, y_px: float) -> tuple[float, float]:
        """Return the point in nm under a pixel."""
        left, bottom = self._origin
        s = self.scale
        return self.x_range[0] + (x_px - left) / s, self.z_range[0] + (bottom - y_px) / s

    def rectangle(
        self, x_low: float, x_high: float, z_low: float, z_high: float
    ) -> tuple[float, float, float, float]:
        """Return ``(left, top, width, height)`` in pixels of a data rectangle."""
        left, top = self.to_screen(x_low, z_high)
        right, bottom = self.to_screen(x_high, z_low)
        return left, top, right - left, bottom - top


def nearest_vertex(
    vertices: Sequence[tuple[float, float]],
    transform: ViewTransform,
    x_px: float,
    y_px: float,
    *,
    tolerance_px: float = 8.0,
) -> int | None:
    """Return the vertex drawn nearest a pixel, if it is within ``tolerance_px`` of it."""
    best: int | None = None
    best_distance = tolerance_px
    for index, (r, z) in enumerate(vertices):
        px, py = transform.to_screen(r, z)
        distance = math.hypot(px - x_px, py - y_px)
        if distance <= best_distance:
            best, best_distance = index, distance
    return best


def nearest_edge(
    vertices: Sequence[tuple[float, float]],
    transform: ViewTransform,
    x_px: float,
    y_px: float,
    *,
    tolerance_px: float = 8.0,
) -> int | None:
    """Return the edge drawn nearest a pixel, edge i joining vertex i to i + 1, closing included."""
    best: int | None = None
    best_distance = tolerance_px
    count = len(vertices)
    for index in range(count):
        ax, ay = transform.to_screen(*vertices[index])
        bx, by = transform.to_screen(*vertices[(index + 1) % count])
        dx, dy = bx - ax, by - ay
        length = dx * dx + dy * dy
        t = (
            0.0
            if length == 0.0
            else max(0.0, min(1.0, ((x_px - ax) * dx + (y_px - ay) * dy) / length))
        )
        distance = math.hypot(ax + t * dx - x_px, ay + t * dy - y_px)
        if distance <= best_distance:
            best, best_distance = index, distance
    return best


# -- the views ---------------------------------------------------------------------


@dataclass(frozen=True)
class SummaryView:
    """A stage shown as the entries of its artefact's summary."""

    name: str
    lines: tuple[str, ...]
    frame: str = STAGE_1_FRAME


@dataclass(frozen=True)
class ImageView:
    """A stage shown as one or more images, and the contour over them if there is one.

    Parameters
    ----------
    images
        By quantity, in the order the selector offers them.
    loop
        The stage-4 profile's vertices, in the stage-1 frame, or ``()``.
    slab
        The membrane's z extent in the stage-1 frame, or ``None``.
    profile
        The stage-4 profile document, for the editor to start from.
    """

    name: str
    images: Mapping[str, ImageModel]
    lines: tuple[str, ...] = ()
    loop: tuple[tuple[float, float], ...] = ()
    slab: tuple[float, float] | None = None
    profile: PoreProfile | None = None

    @property
    def frame(self) -> str:
        """Every image of one view is in one frame."""
        return next(iter(self.images.values())).frame


@dataclass(frozen=True)
class OutlineView:
    """Stage 5's region, drawn as outlines in the model frame.

    Parameters
    ----------
    loop
        The model-frame profile.
    chord
        The membrane's inner edge, ``((r, -t/2), (r, +t/2))``.
    slab
        ``(-t/2, +t/2)``.
    reservoir_nm
        The reservoir radius, for the caption.
    """

    name: str
    loop: tuple[tuple[float, float], ...]
    chord: tuple[tuple[float, float], tuple[float, float]]
    slab: tuple[float, float]
    reservoir_nm: float
    lines: tuple[str, ...] = ()
    frame: str = MODEL_FRAME


StageView: TypeAlias = SummaryView | ImageView | OutlineView
"""What one stage's pane shows."""


def _format(value: object) -> str:
    """Render one summary entry for a pane: numbers to four significant figures."""
    if isinstance(value, float):
        return f"{value:.4g}"
    if isinstance(value, dict):
        return "{" + ", ".join(f"{key}: {_format(item)}" for key, item in value.items()) + "}"
    if isinstance(value, (list, tuple)):
        shown = ", ".join(_format(item) for item in list(value)[:8])
        return f"[{shown}{', …' if len(value) > 8 else ''}]"
    return str(value)


def _lines(summary: Mapping[str, object], keys: Sequence[str]) -> tuple[str, ...]:
    """Return ``key: value`` lines for the entries of a summary that it carries."""
    return tuple(f"{key}: {_format(summary[key])}" for key in keys if key in summary)


def stored_artefact(event: Produced) -> Artefact:
    """Return the stored artefact an event names, or say it is gone."""
    found = Store(event.store).get(event.schema, event.hash)
    if found is None:
        raise FileNotFoundError(
            f"{event.name}'s artefact {event.schema} {event.hash[:12]} is not in the store at "
            f"{event.store}; it was removed after the build reported it"
        )
    return found


def load_view(
    event: Produced, produced: Mapping[str, Produced], document: CaseDocument
) -> StageView:
    """Read one stage's artefact from the store into what its pane shows.

    Called off the Qt thread (WP24 D11): a stage-2 map is a hundred megabytes of
    compressed ``float32``. Each payload is read through the module that wrote
    it, so the pane shows what the next stage read.

    Parameters
    ----------
    event
        The stage's :class:`~nanopnp.gui.solver.Produced`.
    produced
        Every artefact the build has reported, by stage: the contour is drawn
        over stage 3's mean.
    document
        The case being built, for the membrane slab.

    Raises
    ------
    FileNotFoundError
        If the artefact has been removed from the store since it was reported.
    ValueError
        If the stage is not one of stages 1 to 6.
    """
    artefact = stored_artefact(event)
    summary = dict(artefact.summary)
    if event.name == "structure":
        return SummaryView(name=event.name, lines=_lines(summary, STRUCTURE_RECORD_KEYS))
    if event.name == "density":
        density = DensityMap.read(artefact.payload[DENSITY_PAYLOAD])
        grid = density.grid
        section = density_section(
            density.values, grid.axis_nm("x"), grid.axis_nm("z"), y_index=grid.half_width
        )
        return ImageView(
            name=event.name,
            images={"density": section},
            lines=_lines(summary, DENSITY_RECORD_KEYS),
            slab=membrane_slab(document),
        )
    if event.name in ("symmetry", "contour"):
        symmetry = artefact if event.name == "symmetry" else stored_artefact(produced["symmetry"])
        reduced = ReducedMap.read(symmetry.payload[REDUCED_PAYLOAD])
        # The contour is drawn over the mean alone, so its view builds no variance.
        quantities = QUANTITIES if event.name == "symmetry" else ("mean",)
        images = {
            quantity: reduced_image(
                reduced.r_nm, reduced.z_nm, getattr(reduced, quantity), quantity=quantity
            )
            for quantity in quantities
        }
        if event.name == "symmetry":
            return ImageView(
                name=event.name,
                images=images,
                lines=_lines(summary, REDUCTION_RECORD_KEYS),
                slab=membrane_slab(document),
            )
        # Deferred: stage 4's module imports scikit-image and Shapely, the
        # ``structure`` extra, which a case supplying its profile does not need.
        from nanopnp.geometry.contour import PAYLOAD_NAME as PROFILE_PAYLOAD

        profile = load_profile(artefact.payload[PROFILE_PAYLOAD])
        return ImageView(
            name=event.name,
            images=images,
            lines=_lines(
                summary,
                (
                    "vertex_count",
                    "min_vertex_spacing_nm",
                    "min_feature_size_nm",
                    "band",
                    "constriction",
                ),
            ),
            loop=tuple((float(r), float(z)) for r, z in profile.vertices),
            slab=membrane_slab(document),
            profile=profile,
        )
    if event.name == "region":
        record = read_region(artefact.payload[REGION_PAYLOAD])
        points = record.points()
        half = record.membrane.half_thickness_nm
        return OutlineView(
            name=event.name,
            loop=tuple((float(r), float(z)) for r, z in points),
            chord=(
                (record.membrane.inner_trans_nm, -half),
                (record.membrane.inner_cis_nm, half),
            ),
            slab=(-half, half),
            reservoir_nm=record.reservoir_radius_nm,
            lines=_lines(summary, tuple(summary)),
        )
    if event.name == "mesh":
        return SummaryView(
            name=event.name,
            lines=_lines(summary, ("elements", "quality", "sizing", "content_hash")),
            frame=MODEL_FRAME,
        )
    raise ValueError(f"stage {event.name!r} is not one of the geometry stages {GEOMETRY_STAGES}")


# -- the contour editor ------------------------------------------------------------

Vertex: TypeAlias = tuple[float, float]
"""``(r, z)`` in nm, in the stage-1 frame."""


def _loader_text(error: ValidationError) -> str:
    """Return the validator's own sentence from a pydantic error.

    The loader raises the same :class:`~pydantic.ValidationError` for the same
    document, so the editor reports the loader's words and a user reading one
    has read the other (WP24 D8).
    """
    first = error.errors()[0]
    message = str(first.get("msg", error))
    prefix = "Value error, "
    return message[len(prefix) :] if message.startswith(prefix) else message


@dataclass
class ProfileEditor:
    """A hand edit of a pore profile: the operations, their undo, and the document they make.

    Parameters
    ----------
    vertices
        The loop being edited, in the stage-1 frame.
    parent_digest
        ``provenance.sha256`` the edit records: the canonical
        :func:`~nanopnp.geometry.profile.profile_digest` of the profile it was
        edited from, or under §8.2.2 B9 the stage-3 payload digest stage 4
        would have recorded (WP24 D5).
    parent_name
        The parent's name, recorded as ``provenance.citation``.
    """

    vertices: list[Vertex]
    parent_digest: str
    parent_name: str
    _undo: list[list[Vertex]] = field(default_factory=list, repr=False)
    _redo: list[list[Vertex]] = field(default_factory=list, repr=False)

    @classmethod
    def from_profile(cls, profile: PoreProfile) -> ProfileEditor:
        """Start from a profile document: stage 4's, or a supplied one."""
        return cls(
            vertices=[(float(r), float(z)) for r, z in profile.vertices],
            parent_digest=profile_digest(profile),
            parent_name=profile.name,
        )

    @classmethod
    def from_seed(cls, vertices: Sequence[Vertex], *, digest: str, name: str) -> ProfileEditor:
        """Start from a loop stage 4's gate refused (§8.2.2 B9, WP24 D10).

        Parameters
        ----------
        vertices
            :func:`~nanopnp.geometry.contour.condition`'s loop on the stored map.
        digest
            That map's payload digest, which stage 4 would have recorded.
        name
            The name stage 4 would have given its profile.
        """
        return cls(
            vertices=[(float(r), float(z)) for r, z in vertices],
            parent_digest=digest,
            parent_name=name,
        )

    # -- operations -------------------------------------------------------------

    def _push(self) -> None:
        """Remember the loop before an edit, and forget what was undone."""
        self._undo.append(list(self.vertices))
        self._redo.clear()

    def move(self, index: int, r_nm: float, z_nm: float) -> None:
        """Move vertex ``index`` to ``(r, z)``: one undoable step, however it was dragged."""
        self._check_index(index)
        self._push()
        self.vertices[index] = (float(r_nm), float(z_nm))

    def insert(self, edge: int) -> int:
        """Insert a vertex at the midpoint of edge ``edge`` (vertex ``edge`` to ``edge + 1``).

        Returns
        -------
        int
            The new vertex's index.
        """
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
        """Refuse an index outside the loop, naming it."""
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

    # -- the document ------------------------------------------------------------

    @property
    def name(self) -> str:
        """The edited profile's name: its parent's, marked as a hand edit."""
        return f"{self.parent_name}-{HAND_EDIT_SOURCE}"

    def document(self) -> PoreProfile:
        """Return the edit as a validated ``nanopnp/profile/v1`` document (WP24 D5).

        ``provenance.source`` is :data:`~nanopnp.geometry.profile.HAND_EDIT_SOURCE`,
        never a reference source; ``sha256`` is the parent's digest; every
        measurement is re-derived from the edited vertices, which the loader
        re-checks, so a stale block cannot be written.

        Raises
        ------
        ValueError
            With the loader's own sentence, naming the vertex, if the loop is not
            a valid simple closed polygon in the half-plane.
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
        """Return the document and the path it is written to, named by its own digest."""
        profile = self.document()
        root = Path(directory).expanduser().resolve()
        return profile, root / f"{HAND_EDIT_SOURCE}-{profile_digest(profile)[:16]}.yaml"

    def save(self, directory: str | Path) -> Path:
        """Write the edit as a profile document named by its own digest, and return its path.

        Absolute (WP24 D7), so a derived case naming it runs from any working
        directory.

        Raises
        ------
        ValueError
            If the loop would not load; nothing is written.
        """
        profile, path = self._target(directory)
        return write_profile(profile, path)

    def save_case(self, case: CaseDocument, case_path: str | Path) -> tuple[Path, Path]:
        """Write the edit and a derived case beside the original, which is never modified (WP24 D6).

        Parameters
        ----------
        case
            The case the edit was made in.
        case_path
            Where it was read from. The profile and the derived case are written
            beside it; the derived case is ``<stem>.<profile file stem>.yaml``.

        Returns
        -------
        tuple of Path
            The profile, and the derived case.

        Raises
        ------
        ValueError
            If the loop would not load, or the derived case is refused. Both are
            decided before either file is written.
        """
        source = Path(case_path).expanduser().resolve()
        profile, path = self._target(source.parent)
        derived = with_profile(case, path)
        write_profile(profile, path)
        return path, dump_case(derived, source.with_name(f"{source.stem}.{path.stem}.yaml"))
