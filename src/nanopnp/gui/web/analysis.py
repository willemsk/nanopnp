"""The Analysis suite's view-model: a project's runs, their fields, maps, cuts and comparisons."""

from __future__ import annotations

import json
import math
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar, Literal

from nanopnp.api.project import Project, RunState
from nanopnp.core.hashing import decode_floats
from nanopnp.gui.geometry import ImageModel
from nanopnp.gui.render import FIELDS_FILENAME
from nanopnp.gui.web.chart import Axis, Chart, Panel, Series
from nanopnp.gui.web.plane import SERIES, Plane, palette_stops, png
from nanopnp.io.manifest import MANIFEST_FILENAME, RUN_RECORD_FILENAME
from nanopnp.io.project import ComparisonFile
from nanopnp.plot.data import fields_lumen_nm, qoi_rows
from nanopnp.post.export import read_solution_fields
from nanopnp.post.fields import (
    FIELD_ALIASES,
    Window,
    field_at,
    field_difference,
    field_grid,
    field_unit,
    quantity_name,
)
from nanopnp.sweep.collect import read_members

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

    from nanopnp.post.export import SolutionFields

__all__ = [
    "CUT_POINTS",
    "MAP_CELLS",
    "MAP_PERCENTILE",
    "AnalysisModel",
    "FieldMap",
    "Positive",
    "RunChoice",
    "cut_chart",
    "dark_palette",
    "difference_map",
    "field_map",
    "iv_chart",
    "map_drawing",
    "pair_maps",
    "pore_window",
    "quantities_of",
    "scene_field",
]

MAP_PERCENTILE = 99.0
"""The percentile of a quantity's size a map's scale across zero opens on, as the charge map's
does (WB-49): a few nodes beside a charged atom then do not wash out the rest."""

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
    conductance_S: float | None = None


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
    note: str = ""

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
                    conductance_S=_number(quantities.get("conductance_S")),
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
                        conductance_S=_number(quantities.get("conductance_S")),
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


def pore_window(*fields: SolutionFields) -> Window:
    """Return the close-up of the pore that holds each run's: ``(0, r, -z, z)`` in nm."""
    windows = [fields_lumen_nm(one) for one in fields]
    r_nm = max(r for r, _ in windows)
    z_nm = max(z for _, z in windows)
    return (0.0, r_nm, -z_nm, z_nm)


Positive = Literal["blue", "red"]


def _diverging(positive: Positive) -> str:
    # The workbench's diverging map runs blue to red; positive blue is it reversed (WB-39).
    return "diverging_r" if positive == "blue" else "diverging"


def _palette(scale: tuple[float, float], palette: str | None, positive: Positive) -> str:
    if palette:
        return palette
    return _diverging(positive) if scale[0] < 0.0 < scale[1] else "viridis"


def dark_palette(palette: str) -> str:
    """Return the colour map a dark canvas draws in place of one: the diverging map's dark pair."""
    return {"diverging": "diverging_dark", "diverging_r": "diverging_dark_r"}.get(palette, palette)


def _scale(
    values: np.ndarray, colour_range: tuple[float, float] | None
) -> tuple[tuple[float, float], bool]:
    """Return the scale and whether it clips the values: across zero, their size's percentile."""
    import numpy as np

    if colour_range is not None:
        return colour_range, False
    finite = values[np.isfinite(values)]
    if not finite.size:
        return (0.0, 1.0), False
    low, high = float(finite.min()), float(finite.max())
    if low < 0.0 < high:
        # A range across zero takes a diverging map, centred on zero.
        largest = max(-low, high)
        top = float(np.percentile(np.abs(finite), MAP_PERCENTILE))
        top = top if top > 0.0 else largest
        return (-top, top), top < largest
    return ((low, high) if high > low else (low - 0.5, high + 0.5)), False


def field_map(
    fields: SolutionFields,
    quantity: str,
    *,
    palette: str | None = None,
    colour_range: tuple[float, float] | None = None,
    window_nm: Window | None = None,
    positive: Positive = "blue",
    cells: int = MAP_CELLS,
) -> FieldMap:
    """Return one run's map of a quantity over its field's box, cut to ``window_nm``.

    Its scale is the typed range, else the values' own, centred on zero where they cross it,
    where the colour ``positive`` names takes the positive side.
    """
    r_nm, z_nm, values = field_grid(fields, quantity, window_nm=window_nm, cells=cells)
    scale, clipped = _scale(values, colour_range)
    unit = field_unit(quantity)
    note = (
        f"Colours to ±{scale[1]:.3g}{f' {unit}' if unit else ''}, the {MAP_PERCENTILE:g}th "
        "percentile of |values|; beyond, the end colours."
        if clipped
        else ""
    )
    return FieldMap(
        quantity_name(quantity),
        unit,
        r_nm,
        z_nm,
        values,
        scale,
        _palette(scale, palette, positive),
        note,
    )


def difference_map(
    first: SolutionFields,
    second: SolutionFields,
    quantity: str,
    *,
    palette: str | None = None,
    colour_range: tuple[float, float] | None = None,
    window_nm: Window | None = None,
    positive: Positive = "blue",
    cells: int = MAP_CELLS,
) -> FieldMap:
    """Return the second run less the first on their fluids' overlap, its scale symmetric."""
    import numpy as np

    found = field_difference(first, second, quantity, window_nm=window_nm, cells=cells)
    if colour_range is None:
        finite = found.difference[np.isfinite(found.difference)]
        top = float(np.abs(finite).max()) if finite.size else 0.0
        colour_range = (-top, top) if top > 0.0 else (-1.0, 1.0)
    return FieldMap(
        f"{quantity_name(quantity)}, second less first",
        found.unit,
        found.r_nm,
        found.z_nm,
        found.difference,
        colour_range,
        palette or _diverging(positive),
    )


def pair_maps(
    first: SolutionFields,
    second: SolutionFields,
    quantity: str,
    *,
    palette: str | None = None,
    colour_range: tuple[float, float] | None = None,
    window_nm: Window | None = None,
    positive: Positive = "blue",
    cells: int = MAP_CELLS,
) -> tuple[FieldMap, FieldMap]:
    """Return the two runs' maps on the difference's grid, on one scale over what both draw."""
    import numpy as np

    found = field_difference(first, second, quantity, window_nm=window_nm, cells=cells)
    # The scale is the fluid's both maps draw, centred on zero where it spans it.
    scale = colour_range or _scale(np.concatenate([found.first, found.second]), None)[0]
    shown, name = _palette(scale, palette, positive), quantity_name(quantity)
    return (
        FieldMap(name, found.unit, found.r_nm, found.z_nm, found.first, scale, shown),
        FieldMap(name, found.unit, found.r_nm, found.z_nm, found.second, scale, shown),
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
    notes = tuple(
        text
        for text in (note, shown.note, "" if finite else "The quantity is nowhere defined here.")
        if text
    )
    return Plane("model", _MAP_AXES, extent, tuple(layers), notes, point_pick=True)


def _z_samples(fields: tuple[SolutionFields, ...], window_nm: Window | None = None) -> np.ndarray:
    import numpy as np

    lows, highs = [], []
    for one in fields:
        z_nm = np.asarray(one.whole[0], dtype=np.float64)[:, 1] * 1e9
        lows.append(float(z_nm.min()))
        highs.append(float(z_nm.max()))
    if window_nm is not None:
        lows.append(window_nm[2])
        highs.append(window_nm[3])
    return np.linspace(max(lows), min(highs), CUT_POINTS)


def cut_chart(
    runs: tuple[tuple[str, SolutionFields], ...],
    quantity: str,
    r_nm: float,
    window_nm: Window | None = None,
) -> Chart:
    """Return the axial cut at ``r_nm``: the quantity along z, a series per run.

    The cut spans the z every run's domain and ``window_nm`` cover; a point outside a run's
    domain is a gap.
    """
    import numpy as np

    unit = field_unit(quantity)
    z_nm = _z_samples(tuple(fields for _, fields in runs), window_nm)
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
    name = quantity_name(quantity)
    panel = Panel(Axis("z (nm)"), Axis(f"{name} ({unit})" if unit else name))
    return Chart(
        (panel,),
        tuple(series),
        label=f"{name} along z at r = {r_nm:.3g} nm",
    )


def iv_chart(choices: tuple[RunChoice, ...], picked: Path | None = None) -> Chart:
    """Return the current against the bias of a study's runs and its sweeps' members.

    Each point is a run with both numbers recorded; the note gives the shown run's recorded
    conductance, a number of its record and none the chart makes.
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
    notes: list[str] = []
    if len({bias for bias, _, _ in points}) < 2:
        notes.append("One bias is recorded: sweep the bias to draw the current against it.")
    picked_choice = next((choice for choice in choices if choice.directory == picked), None)
    if picked_choice is not None and picked_choice.conductance_S is not None:
        notes.append(
            f"The shown run's recorded conductance, its current over its bias: "
            f"{picked_choice.conductance_S * 1e9:.4g} nS."
        )
    panel = Panel(Axis("bias (mV)"), Axis("current (nA)"))
    return Chart((panel,), tuple(series), notes=tuple(notes), label="Current against bias")
