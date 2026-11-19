"""The Analysis suite's view-model: a project's runs, their fields, maps, cuts and comparisons."""

from __future__ import annotations

import json
import math
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from nanopnp.api.project import Project, RunState
from nanopnp.core.hashing import decode_floats
from nanopnp.gui.geometry import ImageModel
from nanopnp.gui.render import FIELDS_FILENAME
from nanopnp.gui.web.chart import Axis, Chart, Panel, Series
from nanopnp.gui.web.plane import SERIES, Plane, palette_stops, png
from nanopnp.io.manifest import MANIFEST_FILENAME, RUN_RECORD_FILENAME
from nanopnp.io.project import ComparisonFile
from nanopnp.plot.data import qoi_rows
from nanopnp.post.export import read_solution_fields
from nanopnp.post.fields import (
    FIELD_ALIASES,
    field_at,
    field_difference,
    field_grid,
    field_unit,
    joint_range,
)
from nanopnp.sweep.collect import read_members

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

    from nanopnp.post.export import SolutionFields

__all__ = [
    "CUT_POINTS",
    "MAP_CELLS",
    "AnalysisModel",
    "FieldMap",
    "RunChoice",
    "cut_chart",
    "dark_palette",
    "difference_map",
    "field_map",
    "iv_chart",
    "map_drawing",
    "pair_maps",
    "quantities_of",
    "scene_field",
    "slope_conductance_S",
]

MAP_CELLS = 250_000
"""The cells of a map the explorer draws: a quarter of the difference's grid, for a map that
answers a pick at once."""

CUT_POINTS = 400
"""The samples of an axial cut along z."""

_KEPT_FIELDS = 4

_MAP_AXES = ("r (nm)", "z (nm)")


@dataclass(frozen=True)
class RunChoice:
    """A run the explorer can show: a study's own run or a member of one of its sweeps.

    Parameters
    ----------
    sweep
        The sweep's folder name, or ``""`` for a run of the study itself.
    status
        ``ok``, or how a sweep's member ended.
    """

    directory: Path
    study: str
    label: str
    bias_V: float | None
    current_A: float | None
    sweep: str = ""
    status: str = "ok"


@dataclass(frozen=True)
class FieldMap:
    """One quantity on a uniform ``[z, r]`` grid, with the scale and colour map it is drawn in."""

    quantity: str
    unit: str
    r_nm: np.ndarray
    z_nm: np.ndarray
    values: np.ndarray
    scale: tuple[float, float]
    palette: str

    def image(self) -> ImageModel:
        """Return the map as the (r, z) view's picture model."""
        return ImageModel(
            values=self.values,
            x_nm=self.r_nm,
            z_nm=self.z_nm,
            scale=self.scale,
            title=self.quantity,
            x_label="r (nm)",
            frame="model",
            palette=self.palette,
        )

    def png(self) -> bytes:
        """Return the map as a PNG, NaN transparent."""
        picture = self.image()
        return png(picture.rgba(), picture.width, picture.height)


def _number(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) and math.isfinite(value) else None


def _json(path: Path) -> dict[str, Any]:
    try:
        # A record writes a float that JSON cannot hold, as NaN, encoded.
        found = decode_floats(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return {}
    return found if isinstance(found, dict) else {}


def _bias_text(bias_V: float | None) -> str:
    return "no bias recorded" if bias_V is None else f"{bias_V * 1e3:+.4g} mV"


class AnalysisModel:
    """What the Analysis suite reads of a project: its runs, their records and their fields."""

    # Shared by every model of the server: a fields file read once serves each page.
    _fields: ClassVar[dict[tuple[Path, int], tuple[SolutionFields, str]]] = {}
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self, project: Project) -> None:
        self.project = project

    def studies(self) -> tuple[str, ...]:
        """Return the project's studies."""
        return tuple(self.project.items("study"))

    def choices(self, study: str) -> tuple[RunChoice, ...]:
        """Return a study's runs, newest first, then its sweeps' members in their order."""
        found: list[RunChoice] = []
        for directory in reversed(self.project.runs(study)):
            quantities = _json(directory / RUN_RECORD_FILENAME).get("quantities") or {}
            bias = _number(quantities.get("bias_V"))
            found.append(
                RunChoice(
                    directory,
                    study,
                    f"Run {directory.name[:8]}, {_bias_text(bias)}",
                    bias,
                    _number(quantities.get("current_A")),
                )
            )
        for sweep in self.project.sweeps(study):
            try:
                members = read_members(sweep)
            except ValueError:
                continue
            for member in members:
                if member.directory is None:
                    continue
                directory = Path(member.directory)
                quantities = member.quantities or {}
                bias = _number(quantities.get("bias_V"))
                found.append(
                    RunChoice(
                        directory if directory.is_absolute() else sweep / directory,
                        study,
                        f"Sweep {sweep.name}, point {member.index + 1}, {_bias_text(bias)}",
                        bias,
                        _number(quantities.get("current_A")),
                        sweep=sweep.name,
                        status=member.status,
                    )
                )
        return tuple(found)

    def record(self, run: Path) -> dict[str, Any]:
        """Return a run's record, or an empty one where it does not read."""
        return _json(run / RUN_RECORD_FILENAME)

    def state(self, run: Path) -> RunState:
        """Return whether a run's solve is in the store, cleaned from it, or never reached."""
        return self.project.run_state(run)

    def quantity_rows(self, run: Path) -> list[dict[str, str]]:
        """Return a run's quantities of interest as rows of quantity, value and unit (Q38)."""
        quantities = self.record(run).get("quantities")
        return qoi_rows(quantities) if isinstance(quantities, dict) else []

    def deviations(self, run: Path) -> list[str]:
        """Return each switch the run set away from its validated default (Q39; FR-25)."""
        found = _json(run / MANIFEST_FILENAME).get("deviations")
        switches = found.get("switches") if isinstance(found, dict) else None
        return [
            f"{switch.get('path')}: {switch.get('value')}, "
            f"validated {switch.get('validated_default')}"
            for switch in switches or ()
            if isinstance(switch, dict)
        ]

    def solve_hash(self, run: Path) -> str | None:
        """Return the hash of the solve a run's record names, or None."""
        artefacts = self.record(run).get("artefacts")
        solve = artefacts.get("solve") if isinstance(artefacts, dict) else None
        found = solve.get("hash") if isinstance(solve, dict) else None
        return found if isinstance(found, str) else None

    def fields(self, run: Path) -> SolutionFields | None:
        """Return a run's fields from its fields file, or None while it is not written.

        A file written from another solve than the record names is not this run's, and reads
        as not written. The last four read are kept.
        """
        path = run / "viewer" / FIELDS_FILENAME
        try:
            stamp = path.stat().st_mtime_ns
        except OSError:
            return None
        key = (path, stamp)
        with self._lock:
            held = self._fields.get(key)
        if held is None:
            try:
                held = read_solution_fields(path)
            except (OSError, ValueError, KeyError):
                return None
            with self._lock:
                self._fields[key] = held
                while len(self._fields) > _KEPT_FIELDS:
                    self._fields.pop(next(iter(self._fields)))
        fields, solve = held
        return fields if solve == self.solve_hash(run) else None

    def comparisons(self) -> tuple[str, ...]:
        """Return the project's comparisons."""
        return tuple(self.project.items("comparison"))

    def comparison(self, name: str) -> ComparisonFile:
        """Return a comparison's file."""
        return self.project.comparison(name)

    def run_path(self, run: str) -> Path:
        """Return a run folder named relative to the project, as a comparison records it."""
        return self.project.root / run


def quantities_of(fields: SolutionFields) -> tuple[str, ...]:
    """Return the scalar quantities a run's fields carry, and a vector's two components."""
    found: list[str] = []
    for _, _, values in (fields.whole, fields.fluid):
        for key, array in values.items():
            if key in found:
                continue
            if array.ndim == 1:
                found.append(key)
    vectors = {key for _, _, values in (fields.whole, fields.fluid) for key in values}
    found.extend(
        alias for alias, (key, part) in FIELD_ALIASES.items() if part is not None and key in vectors
    )
    return tuple(found)


def scene_field(quantity: str) -> str:
    """Return the attribute a 3D scene draws for a quantity: a component's vector whole."""
    return FIELD_ALIASES.get(quantity, (quantity, None))[0]


def _palette(scale: tuple[float, float], palette: str | None) -> str:
    if palette:
        return palette
    return "diverging" if scale[0] < 0.0 < scale[1] else "viridis"


def dark_palette(palette: str) -> str:
    """Return the colour map a dark canvas draws in place of one: the diverging map's dark pair."""
    return {"diverging": "diverging_dark", "diverging_r": "diverging_dark_r"}.get(palette, palette)


def _scale(values: np.ndarray, colour_range: tuple[float, float] | None) -> tuple[float, float]:
    import numpy as np

    if colour_range is not None:
        return colour_range
    finite = values[np.isfinite(values)]
    if not finite.size:
        return (0.0, 1.0)
    low, high = float(finite.min()), float(finite.max())
    if low < 0.0 < high:
        # A range across zero takes a diverging map, centred on zero.
        top = max(-low, high)
        return (-top, top)
    return (low, high) if high > low else (low - 0.5, high + 0.5)


def field_map(
    fields: SolutionFields,
    quantity: str,
    *,
    palette: str | None = None,
    colour_range: tuple[float, float] | None = None,
    cells: int = MAP_CELLS,
) -> FieldMap:
    """Return one run's map of a quantity over its field's box.

    Its scale is the typed range, else the values' own, centred on zero where they cross it.
    """
    r_nm, z_nm, values = field_grid(fields, quantity, cells=cells)
    scale = _scale(values, colour_range)
    return FieldMap(
        quantity, field_unit(quantity), r_nm, z_nm, values, scale, _palette(scale, palette)
    )


def difference_map(
    first: SolutionFields,
    second: SolutionFields,
    quantity: str,
    *,
    palette: str | None = None,
    colour_range: tuple[float, float] | None = None,
    cells: int = MAP_CELLS,
) -> FieldMap:
    """Return the second run less the first on their fluids' overlap, its scale symmetric."""
    import numpy as np

    found = field_difference(first, second, quantity, cells=cells)
    if colour_range is None:
        finite = found.difference[np.isfinite(found.difference)]
        top = float(np.abs(finite).max()) if finite.size else 0.0
        colour_range = (-top, top) if top > 0.0 else (-1.0, 1.0)
    return FieldMap(
        f"{quantity}, second less first",
        found.unit,
        found.r_nm,
        found.z_nm,
        found.difference,
        colour_range,
        palette or "diverging",
    )


def pair_maps(
    first: SolutionFields,
    second: SolutionFields,
    quantity: str,
    *,
    palette: str | None = None,
    colour_range: tuple[float, float] | None = None,
    cells: int = MAP_CELLS,
) -> tuple[FieldMap, FieldMap]:
    """Return the two runs' maps on the difference's grid, on one scale: their joint range."""
    found = field_difference(first, second, quantity, cells=cells)
    scale = colour_range or joint_range(first, second, quantity)
    shown = _palette(scale, palette)
    return (
        FieldMap(quantity, found.unit, found.r_nm, found.z_nm, found.first, scale, shown),
        FieldMap(quantity, found.unit, found.r_nm, found.z_nm, found.second, scale, shown),
    )


def map_drawing(
    shown: FieldMap,
    image_url: str,
    *,
    cut_r_nm: float | None = None,
    probes: tuple[tuple[float, float], ...] = (),
    note: str = "",
) -> Plane:
    """Return a map as the (r, z) view draws it: the picture, the cut's line and the probes.

    A click on it asks about the point, which places the cut or a probe.
    """
    import numpy as np

    r_low, r_high = float(shown.r_nm[0]), float(shown.r_nm[-1])
    z_low, z_high = float(shown.z_nm[0]), float(shown.z_nm[-1])
    half_r = 0.5 * (r_high - r_low) / max(len(shown.r_nm) - 1, 1)
    half_z = 0.5 * (z_high - z_low) / max(len(shown.z_nm) - 1, 1)
    extent = (r_low - half_r, r_high + half_r, z_low - half_z, z_high + half_z)
    stops = palette_stops(shown.palette)
    layers: list[dict[str, Any]] = [
        {
            "id": "field",
            "kind": "image",
            "url": image_url,
            "extent_nm": [round(value, 6) for value in extent],
            "scale": list(shown.scale),
            "title": shown.quantity,
            "bar": {
                "quantity": shown.quantity,
                "unit": shown.unit or "no unit",
                "low": shown.scale[0],
                "high": shown.scale[1],
                "palette": stops,
            },
        }
    ]
    dark = dark_palette(shown.palette)
    if dark != shown.palette:
        # A dark canvas takes the diverging map through a dark middle, the picture and its bar.
        layers[0]["dark"] = {"url": f"{image_url}&dark=1", "bar": palette_stops(dark)}
    if cut_r_nm is not None:
        layers.append(
            {
                "id": "cut",
                "kind": "line",
                "role": "probe",
                "points_nm": [cut_r_nm, extent[2], cut_r_nm, extent[3]],
                "title": f"Axial cut, r = {cut_r_nm:.3g} nm",
            }
        )
    if probes:
        layers.append(
            {
                "id": "probes",
                "kind": "points",
                "points_nm": [value for point in probes for value in point],
                "colours": [SERIES[(k + 2) % len(SERIES)] for k in range(len(probes))],
                "title": "Probes",
            }
        )
    finite = bool(np.isfinite(shown.values).any())
    notes = (note,) if note else () if finite else ("The quantity is nowhere defined here.",)
    return Plane("model", _MAP_AXES, extent, tuple(layers), notes, point_pick=True)


def _z_samples(fields: tuple[SolutionFields, ...]) -> np.ndarray:
    import numpy as np

    lows, highs = [], []
    for one in fields:
        z_nm = np.asarray(one.whole[0], dtype=np.float64)[:, 1] * 1e9
        lows.append(float(z_nm.min()))
        highs.append(float(z_nm.max()))
    return np.linspace(max(lows), min(highs), CUT_POINTS)


def cut_chart(runs: tuple[tuple[str, SolutionFields], ...], quantity: str, r_nm: float) -> Chart:
    """Return the axial cut at ``r_nm``: the quantity along z, a series per run.

    The cut spans the z every run's domain covers; a point outside a run's domain is a gap.
    """
    import numpy as np

    unit = field_unit(quantity)
    z_nm = _z_samples(tuple(fields for _, fields in runs))
    series = []
    for index, (label, fields) in enumerate(runs):
        values = field_at(fields, quantity, np.full_like(z_nm, r_nm), z_nm)
        series.append(
            Series(
                f"cut-{index}",
                label,
                tuple(float(z) for z in z_nm),
                tuple(float(v) if math.isfinite(v) else None for v in values),
                SERIES[index % len(SERIES)],
                () if index == 0 else (5.0, 3.0),
            )
        )
    panel = Panel(Axis("z (nm)"), Axis(f"{quantity} ({unit})" if unit else quantity))
    return Chart(
        (panel,),
        tuple(series),
        label=f"{quantity} along z at r = {r_nm:.3g} nm",
    )


def slope_conductance_S(points: list[tuple[float, float]]) -> float | None:
    """Return the slope of the least-squares line through ``(bias_V, current_A)`` points.

    None for fewer than two points at distinct biases.
    """
    if len({bias for bias, _ in points}) < 2:
        return None
    n = len(points)
    mean_v = sum(bias for bias, _ in points) / n
    mean_i = sum(current for _, current in points) / n
    across = sum((bias - mean_v) * (current - mean_i) for bias, current in points)
    spread = sum((bias - mean_v) ** 2 for bias, _ in points)
    return across / spread


def iv_chart(choices: tuple[RunChoice, ...], picked: Path | None = None) -> Chart:
    """Return the current against the bias of a study's runs and its sweeps' members.

    Each point is a run with both numbers recorded; the note gives the slope of the line through
    them, a conductance only where the current is linear in the bias.
    """
    points = sorted(
        (choice.bias_V, choice.current_A, choice.directory)
        for choice in choices
        if choice.bias_V is not None and choice.current_A is not None and choice.status == "ok"
    )
    x = tuple(bias * 1e3 for bias, _, _ in points)
    series = [
        Series(
            "iv",
            "Current",
            x,
            tuple(current * 1e9 for _, current, _ in points),
            SERIES[0],
            marks=True,
        )
    ]
    shown = [index for index, (_, _, run) in enumerate(points) if run == picked]
    if shown:
        k = shown[0]
        series.append(
            Series("picked", "Shown run", (x[k],), (points[k][1] * 1e9,), SERIES[3], marks=True)
        )
    slope = slope_conductance_S([(bias, current) for bias, current, _ in points])
    notes = (
        ("Fewer than two biases are recorded: no slope is drawn.",)
        if slope is None
        else (
            f"Slope of the line through the {len(points)} points: {slope * 1e9:.4g} nS, "
            "the conductance where the current is linear in the bias.",
        )
    )
    panel = Panel(Axis("bias (mV)"), Axis("current (nA)"))
    return Chart((panel,), tuple(series), notes=notes, label="Current against bias")
