"""What the (r, z) view draws for each Continuum and Physics tool: its frame, extent and layers."""

from __future__ import annotations

import hashlib
import math
import threading
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, TypeVar

from nanopnp.core.stages import describe
from nanopnp.density.map import PAYLOAD_NAME as DENSITY_PAYLOAD
from nanopnp.density.map import DensityMap
from nanopnp.geometry.profile import load_profile
from nanopnp.gui.geometry import ImageModel, density_section, lookup_table, reduced_image
from nanopnp.gui.web.builds import REFUSED
from nanopnp.gui.web.continuum import ContinuumModel
from nanopnp.gui.web.link import png
from nanopnp.io.case import Membrane, Reservoir
from nanopnp.mesh.ingest import BOUNDARY_VOCABULARY, deployed_mesh
from nanopnp.physics.models import case_model, role_conditions
from nanopnp.pipeline.case import resolve
from nanopnp.pipeline.run import keyed_walk
from nanopnp.plot.data import (
    MeshElements,
    RegionDrawing,
    axis_label,
    boundary_edges,
    case_correction_curves,
    contour_polygon_m,
    mesh_elements,
    mesh_of,
    reduced_map,
    region_drawing,
)

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np
    from shapely.geometry.base import BaseGeometry

    from nanopnp.api.case import Case
    from nanopnp.io.artefact import Artefact
    from nanopnp.io.resolved import ResolvedCase
    from nanopnp.io.store import Store

__all__ = [
    "COLOURINGS",
    "DOMAINS",
    "IMAGES",
    "MATERIAL_COLOURS",
    "PARTS",
    "ROLE_COLOURS",
    "ROLE_TITLES",
    "SERIES",
    "Plane",
    "image_png",
    "mesh_quality",
    "physics_plane",
    "plane",
]

Frame = Literal["structure", "model", "plot"]

_T = TypeVar("_T")

IMAGES: tuple[str, ...] = ("density", "mean", "cn_variance", "raw_variance")
"""The pictures Pore geometry draws under its outline: stage 2's section, then stage 3's maps."""

IMAGE_BARS: dict[str, tuple[str, str]] = {
    "density": ("Density, stage 2", "fraction of space filled"),
    "mean": ("Mean density, stage 3", "fraction of space filled"),
    "cn_variance": ("Cn variance, stage 3", "fraction squared"),
    "raw_variance": ("Raw variance, stage 3", "fraction squared"),
}
"""Each picture's quantity and unit, which its colour bar names."""

DOMAINS: dict[str, str] = {
    "protein": "Protein",
    "exclusion": "Ion-exclusion shell",
    "membrane": "Membrane",
    "electrolyte": "Electrolyte",
}
"""Stage 5's domains as the view names them, the smallest first, so a pick finds it first."""

PARTS: dict[str, str] = {
    "protein": "Protein",
    "electrolyte": "Electrolyte",
    "membrane": "Membrane",
    "wall": "Wall, the protein's surface",
    "arc": "Outer boundary",
    "axis": "Axis in the pore",
    "global": "Global",
}
"""The parts of a generated mesh the Mesh tool sizes: its domains, its boundaries, the rest."""

COLOURINGS: tuple[str, ...] = ("material", "sicn", "gamma")
"""What the Mesh tool colours its elements by."""

MATERIAL_COLOURS: dict[str, str] = {
    "electrolyte": "#a8cfe6",
    "cis": "#a8cfe6",
    "trans": "#a8cfe6",
    "protein": "#d9925b",
    "membrane": "#b8b07e",
    "exclusion": "#8fb9a8",
    "analyte": "#b48ac2",
}
"""Each material's fill in the mesh drawn by material, on either theme's canvas."""

QUALITY_STOPS = 12
"""How many colours of the sequential palette a quality colouring sends."""

ROUND_NM = 5
"""Decimal places of nm a coordinate is sent with: 10 fm, far below any element."""

MARGIN = 0.08
"""The share of the drawing's span the first view leaves around it."""

FRAMED = frozenset({"contour", "pore", "exclusion", "probe", "lumen"})
"""The outlines the first view frames, with the pictures: the pore, not the membrane."""

SERIES: tuple[str, ...] = (
    "#2a78d6",
    "#d95926",
    "#199e70",
    "#c98500",
    "#d55181",
    "#008300",
    "#9085e9",
    "#e34948",
)
"""A plot's line colours in their fixed order, each at 3:1 or more on either theme's canvas."""

ROLE_COLOURS: dict[str, str] = {
    "cis": SERIES[0],
    "trans": SERIES[1],
    "wall": SERIES[2],
    "membrane": SERIES[3],
    "axis": SERIES[4],
}
"""Each boundary role's line in the Conditions view, unless it is picked: that takes the accent."""

ROLE_TITLES: dict[str, str] = {
    "cis": "Cis boundary",
    "trans": "Trans boundary",
    "wall": "Pore wall",
    "membrane": "Membrane faces",
    "axis": "Axis",
}
"""Each boundary role as the Conditions view's key names it."""

PLOT_TICKS = 5
"""How many ticks each axis of a plot carries, its two ends among them."""

NICE_STEPS = (1.0, 2.0, 2.5, 5.0, 10.0, 20.0)
"""The multiples of a power of ten a plot's tick step is chosen from."""

UNMESHED = "The boundaries are drawn on the pore's mesh: build it in Continuum \u203a Mesh."
"""What the Conditions view says where the shown case's mesh is not built."""


@dataclass(frozen=True)
class Plane:
    """One drawing of the (r, z) view.

    Parameters
    ----------
    frame
        ``structure``, stage 1's frame, where stages 2 to 4 draw; ``model``, the membrane at
        z = 0, where the region and the mesh draw; ``plot``, a graph with each axis scaled
        alone. The view keeps its pan and zoom while the frame stays the same.
    extent_nm
        ``(r_low, r_high, z_low, z_high)`` the view opens on: the pore, not the reservoir. A
        plot's ``(x_low, x_high, y_low, y_high)``, in its axes' units, as its layers' points.
    notes
        What is not drawn, and why, said beside the drawing.
    """

    frame: Frame
    axes: tuple[str, str]
    extent_nm: tuple[float, float, float, float]
    layers: tuple[dict[str, Any], ...]
    notes: tuple[str, ...] = ()

    def json(self) -> dict[str, Any]:
        """Return the drawing as the canvas reads it."""
        return {
            "frame": self.frame,
            "axes": list(self.axes),
            "extent_nm": list(self.extent_nm),
            # Whether the extent frames something drawn, not the empty view's stand-in; a plot
            # is fitted to its extent at every drawing.
            "framed": self.frame != "plot" and _bounds(self.layers) is not None,
            "layers": list(self.layers),
            "notes": list(self.notes),
        }


def _flat(points_nm: Iterable[Sequence[float]]) -> list[float]:
    return [round(float(value), ROUND_NM) for point in points_nm for value in point[:2]]


def _line(
    identifier: str, role: str, points_nm: Iterable[Sequence[float]], title: str = ""
) -> dict[str, Any]:
    drawn = {"id": identifier, "kind": "line", "role": role, "points_nm": _flat(points_nm)}
    return {**drawn, "title": title} if title else drawn


def _polygon(
    identifier: str, role: str, points_nm: Iterable[Sequence[float]], title: str = ""
) -> dict[str, Any]:
    drawn = {"id": identifier, "kind": "polygon", "role": role, "points_nm": _flat(points_nm)}
    return {**drawn, "title": title} if title else drawn


def _rings(shape: BaseGeometry) -> list[list[float]]:
    """Return a shape's rings as the canvas fills them, even-odd: each outline, then its holes."""
    from shapely import Polygon

    polygons = getattr(shape, "geoms", [shape])
    rings: list[list[float]] = []
    for polygon in polygons:
        if polygon.is_empty or not isinstance(polygon, Polygon):
            continue
        rings.append(_flat(polygon.exterior.coords))
        rings += [_flat(hole.coords) for hole in polygon.interiors]
    return rings


def _label(
    path: str, name: str, value: float, unit: str, anchor_nm: tuple[float, float]
) -> dict[str, Any]:
    return {
        "id": f"label-{path}",
        "kind": "label",
        "path": path,
        "name": name,
        "value": value,
        "unit": unit,
        "anchor_nm": [round(anchor_nm[0], ROUND_NM), round(anchor_nm[1], ROUND_NM)],
    }


def _bounds(layers: Iterable[dict[str, Any]]) -> tuple[float, float, float, float] | None:
    rs: list[float] = []
    zs: list[float] = []
    for layer in layers:
        if layer["kind"] == "image":
            r0, r1, z0, z1 = layer["extent_nm"]
            rs += [r0, r1]
            zs += [z0, z1]
        elif layer.get("role") in FRAMED and "points_nm" in layer:
            points = layer["points_nm"]
            rs += points[0::2]
            zs += points[1::2]
    if not rs:
        return None
    return min(rs), max(rs), min(zs), max(zs)


def _extent(
    layers: Sequence[dict[str, Any]], fallback: tuple[float, float, float, float]
) -> tuple[float, float, float, float]:
    found = _bounds(layers) or fallback
    r0, r1, z0, z1 = found
    pad = MARGIN * max(r1 - r0, z1 - z0, 1.0)
    # The axis is the drawing's edge, unless a section across it reaches below r = 0.
    low = r0 - pad if r0 < 0.0 else 0.0
    return low, r1 + pad, z0 - pad, z1 + pad


def _stops(table: np.ndarray) -> list[str]:
    import numpy as np

    picks = np.linspace(0, len(table) - 1, QUALITY_STOPS).round().astype(int)
    return [f"#{r:02x}{g:02x}{b:02x}" for r, g, b, _ in table[picks]]


def _image(
    model: ContinuumModel, identifier: str, picture: ImageModel, digest: str
) -> dict[str, Any]:
    quantity, unit = IMAGE_BARS[identifier]
    return {
        "id": identifier,
        "kind": "image",
        "url": f"/api/continuum/{model.name}/image?layer={identifier}&v={digest[:12]}",
        "extent_nm": [round(v, ROUND_NM) for v in picture.extent_nm],
        "scale": list(picture.scale),
        "title": picture.title,
        "bar": {
            "quantity": quantity,
            "unit": unit,
            "low": picture.scale[0],
            "high": picture.scale[1],
            "palette": _stops(lookup_table(picture.palette)),
        },
    }


def _picture(artefact: Artefact, layer: str) -> ImageModel:
    if layer == "density":
        density = DensityMap.read(artefact.payload[DENSITY_PAYLOAD])
        grid = density.grid
        return density_section(
            density.values, grid.axis_nm("x"), grid.axis_nm("z"), y_index=grid.half_width
        )
    reduced = reduced_map(artefact)
    if reduced is None:
        raise ValueError(f"stage 3's artefact {artefact.hash[:12]} holds no reduced map")
    return reduced_image(reduced.r_nm, reduced.z_nm, getattr(reduced, layer), quantity=layer)


def image_png(model: ContinuumModel, layer: str) -> bytes | None:
    """Return one picture of the model's built stages as a PNG, or None where it is not built."""
    if layer not in IMAGES:
        raise ValueError(f"layer {layer!r} is not one of {', '.join(IMAGES)}")
    held = model.artefacts()
    stage = "density" if layer == "density" else "symmetry"
    if stage not in held:
        return None
    picture = _picture(held[stage], layer)
    return png(picture.rgba(), picture.width, picture.height)


def _membrane(
    document_membrane: Membrane, outline: Sequence[float] | None, *, r_high: float
) -> list[dict[str, Any]]:
    """Return the membrane's faces in stage 1's frame, each from the outline's outer edge out."""
    from shapely import LineString, Polygon

    centre = document_membrane.centre_z_nm
    half = 0.5 * document_membrane.thickness_nm
    solid = None
    if outline is not None and len(outline) >= 6:
        solid = Polygon(list(zip(outline[0::2], outline[1::2], strict=True))).buffer(0)
    faces = []
    for side, z in (("trans", centre - half), ("cis", centre + half)):
        start = 0.0
        if solid is not None:
            crossed = LineString([(0.0, z), (r_high, z)]).intersection(solid)
            start = 0.0 if crossed.is_empty else float(crossed.bounds[2])
        faces.append(
            _line(f"membrane-{side}", "membrane", [(start, z), (r_high, z)], "Membrane faces")
        )
    return faces


def _probe(artefact: Artefact) -> list[dict[str, Any]]:
    gate = artefact.summary.get("gate")
    profile = gate.get("radius_profile") if isinstance(gate, dict) else None
    if not isinstance(profile, dict):
        return []
    z = profile.get("z_nm")
    layers = []
    for key, role in (("probe_nm", "probe"), ("lumen_nm", "lumen")):
        r = profile.get(key)
        if not isinstance(z, list) or not isinstance(r, list):
            continue
        points = [(float(a), float(b)) for a, b in zip(r, z, strict=True) if math.isfinite(a)]
        if points:
            title = "Probe radius" if role == "probe" else "Lumen radius"
            layers.append(_line(role, role, points, title))
    return layers


def _values(model: ContinuumModel) -> tuple[Membrane, Reservoir, float | None]:
    case = model.case()
    geometry = None if case is None else case.geometry
    membrane = geometry.membrane if geometry is not None else Membrane()
    reservoir = geometry.reservoir if geometry is not None else Reservoir()
    offset = None if case is None or case.charge is None else case.charge.exclusion_offset_nm
    return membrane, reservoir, offset


def _supplied(model: ContinuumModel) -> np.ndarray | None:
    path = model.profile()
    if path is None or not path.is_file():
        return None
    try:
        return load_profile(path).as_array()
    except (OSError, ValueError):
        return None


def _outline_layers(
    model: ContinuumModel, held: dict[str, Artefact], *, image: str
) -> tuple[list[dict[str, Any]], list[str], str]:
    """Return stages 2 to 4's layers in stage 1's frame, the notes and the r axis's name."""
    layers: list[dict[str, Any]] = []
    notes: list[str] = []
    axis = "r (nm)"
    stage = "density" if image == "density" else "symmetry"
    if stage in held:
        layers.append(_image(model, image, _picture(held[stage], image), held[stage].hash))
        if image == "density":
            axis = "x (nm), section y = 0"
    loop = contour_polygon_m(held["contour"]) if "contour" in held else None
    supplied = _supplied(model)
    if loop is not None:
        layers.append(_polygon("contour", "contour", loop * 1e9, "Outline, stage 4"))
        layers += _probe(held["contour"])
    elif supplied is not None:
        layers.append(_polygon("contour", "contour", supplied, "Outline, supplied"))
        notes.append("The model supplies its outline (inputs.profile): stages 2 to 4 do not run.")
    if not layers:
        notes.append(_unbuilt(model, "Nothing is built yet: build the geometry to draw it."))
    return layers, notes, axis


def _unbuilt(model: ContinuumModel, note: str) -> str:
    # The view is drawn once a build starts, so it names no stage: the pane's button does.
    if model.running_stage() is None:
        return note
    return "A build is running: the view draws the model when it ends."


def _arc(radius_nm: float) -> list[tuple[float, float]]:
    return [
        (radius_nm * math.cos(angle), radius_nm * math.sin(angle))
        for angle in (math.pi * (k / 64 - 0.5) for k in range(65))
    ]


def domain_shapes(drawing: RegionDrawing) -> dict[str, BaseGeometry]:
    """Return stage 5's domains in nm, each as the meshed region holds it, by :data:`DOMAINS`.

    The membrane stops at the protein, and the electrolyte is the reservoir's half disc less
    every solid. An idealised pore's ``pore`` outline is its lumen, so it has no protein.
    """
    from shapely import Polygon, unary_union

    pore = Polygon(drawing.pore_m * 1e9).buffer(0)
    slab = Polygon(drawing.membrane_m * 1e9).buffer(0)
    radius = drawing.reservoir_radius_m * 1e9
    disc = Polygon([(0.0, -radius), *_arc(radius), (0.0, radius)])
    found: dict[str, BaseGeometry] = {}
    if drawing.record.is_idealised:
        found["membrane"] = slab
    else:
        found["protein"] = pore
        if drawing.exclusion_m is not None:
            found["exclusion"] = Polygon(drawing.exclusion_m * 1e9).buffer(0).difference(pore)
        found["membrane"] = slab.difference(pore)
    found["electrolyte"] = disc.difference(unary_union(list(found.values())))
    return {name: found[name] for name in DOMAINS if name in found}


def _region_layers(
    held: dict[str, Artefact], *, filled: bool, picked: str = ""
) -> tuple[list[dict[str, Any]], RegionDrawing | None]:
    drawing = region_drawing(held["region"]) if "region" in held else None
    if drawing is None:
        return [], None
    layers: list[dict[str, Any]] = []
    for name, shape in domain_shapes(drawing).items():
        layers.append(
            {
                "id": f"domain-{name}",
                "kind": "domain",
                "role": "domain",
                "domain": name,
                "title": DOMAINS[name],
                "fill": MATERIAL_COLOURS[name],
                "filled": filled,
                "picked": name == picked,
                "rings": _rings(shape),
            }
        )
    # The pore's outline frames the first view, drawn by its domains.
    layers.append({**_polygon("pore", "pore", drawing.pore_m * 1e9), "hidden": True})
    radius = drawing.reservoir_radius_m * 1e9
    layers.append(_line("reservoir", "reservoir", _arc(radius), "Reservoir boundary"))
    return layers, drawing


def _part_line(drawing: RegionDrawing, part: str) -> dict[str, Any] | None:
    """Return a boundary part of the mesh as a line the view draws over it, or None."""
    outlines = drawing.record.outlines_nm()
    if part == "arc":
        points: Sequence[Sequence[float]] = _arc(outlines.reservoir_radius_nm)
    elif part == "axis":
        low, high = outlines.z_extent_nm
        points = [(0.0, low), (0.0, high)]
    elif part == "wall":
        if drawing.record.is_idealised:
            radius = float(outlines.pore_nm[1][0])
            half = outlines.membrane_half_thickness_nm
            points = [(radius, -half), (radius, half)]
        else:
            points = [*outlines.pore_nm, outlines.pore_nm[0]]
    else:
        return None
    return _line("part", "picked", points, PARTS[part])


def _labels(
    model: ContinuumModel, extent: tuple[float, float, float, float]
) -> list[dict[str, Any]]:
    membrane, reservoir, offset = _values(model)
    r_high, z_low, z_high = extent[1], extent[2], extent[3]
    gap = 0.08 * (z_high - z_low)
    half = 0.5 * membrane.thickness_nm
    labels = [
        _label(
            "geometry.membrane.thickness_nm",
            "Membrane thickness",
            membrane.thickness_nm,
            "nm",
            (r_high, 0.0),
        ),
        _label(
            "geometry.membrane.centre_z_nm",
            "Membrane centre, z",
            membrane.centre_z_nm,
            "nm",
            (r_high, -half - gap),
        ),
        _label(
            "geometry.reservoir.radius_nm",
            "Reservoir radius",
            reservoir.radius_nm,
            "nm",
            (r_high, z_high - gap),
        ),
    ]
    if offset is not None:
        labels.append(
            _label(
                "charge.exclusion_offset_nm",
                "Ion-exclusion offset",
                offset,
                "nm",
                (r_high, z_low + gap),
            )
        )
    return labels


MESHES_HELD = 4
"""How many meshes' elements the server keeps read: each size or scale tried makes another."""

_MESHES: dict[str, MeshElements] = {}
# The mesh a run deploys, by its stage-6 key and its case: its hash, elements and boundaries.
_DEPLOYED: dict[str, tuple[str, MeshElements, dict[str, np.ndarray]]] = {}
# A drawing request runs in the server's thread pool, beside the window's own reads.
_MESHES_LOCK = threading.Lock()


def _kept(cache: dict[str, _T], key: str, read: Callable[[], _T]) -> _T:
    with _MESHES_LOCK:
        found = cache.pop(key, None)
    if found is None:
        found = read()
    with _MESHES_LOCK:
        # The latest read last; the least recently read goes first once the cache is full.
        cache[key] = found
        while len(cache) > MESHES_HELD:
            del cache[next(iter(cache))]
    return found


def _elements(artefact: Artefact) -> MeshElements:
    def read() -> MeshElements:
        found = mesh_of(artefact, None)
        if found is None:
            raise ValueError(f"stage 6's artefact {artefact.hash[:12]} holds no mesh")
        return found

    return _kept(_MESHES, artefact.hash, read)


def mesh_quality(model: ContinuumModel, colour: str) -> np.ndarray | None:
    """Return each element's SICN or gamma in the model's built mesh, or None unbuilt."""
    if colour not in ("sicn", "gamma"):
        raise ValueError(f"colour {colour!r} is not a quality: sicn or gamma")
    held = model.artefacts()
    if "mesh" not in held:
        return None
    elements = _elements(held["mesh"])
    return elements.sicn if colour == "sicn" else elements.gamma


def _mesh_layer(
    elements: MeshElements,
    key: str,
    colour: str,
    band: tuple[float, float] | None,
    part: str = "",
    mesh_held: str = "",
) -> dict[str, Any]:
    import numpy as np

    # The vertices, triangles and materials go once per mesh: a canvas holding them names the
    # mesh, and a restyle, a pick or a bar sends one value per element.
    geometry = (
        {}
        if mesh_held == key
        else {
            "vertices_nm": np.round(elements.vertices_m * 1e9, ROUND_NM).ravel().tolist(),
            "triangles": elements.triangles.ravel().tolist(),
            "material": elements.material.tolist(),
        }
    )
    # A domain picked keeps its colour and greys the rest; a boundary is drawn over the mesh.
    focus = elements.materials.index(part) if part in elements.materials else None
    outlined: list[int] = []
    if band is not None and colour != "material":
        quality = elements.sicn if colour == "sicn" else elements.gamma
        low, high = band
        inside = (quality >= low) & ((quality < high) | (high >= 1.0) & (quality <= high))
        outlined = np.flatnonzero(inside).tolist()
    if colour == "material":
        values = elements.material.tolist()
        palette = [MATERIAL_COLOURS.get(name, "#cccccc") for name in elements.materials]
        scale: list[float] = [0.0, float(max(len(palette) - 1, 1))]
        legend = list(elements.materials)
    else:
        quality = elements.sicn if colour == "sicn" else elements.gamma
        values = np.round(quality, 4).tolist()
        palette = _stops(lookup_table("viridis"))
        scale = [0.0, 1.0]
        legend = []
    return {
        "id": "mesh",
        "kind": "mesh",
        "mesh": key,
        **geometry,
        "colour": colour,
        "values": values,
        "palette": palette,
        "scale": scale,
        "legend": legend,
        "categorical": colour == "material",
        "outlined": outlined,
        **({} if focus is None else {"focus": focus}),
    }


def _edited(model: ContinuumModel, layers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Put the hand edit held in place of the outline, over the outline it was edited from."""
    editor = model.editor()
    if editor is None:
        return layers
    kept = [layer for layer in layers if layer["id"] != "contour"]
    original = [
        {**layer, "id": "original", "role": "original", "title": "Outline before the edit"}
        for layer in layers
        if layer["id"] == "contour"
    ]
    edit = {**_polygon("contour", "contour", editor.vertices, "Edited outline"), "editable": True}
    return [*kept, *original, edit]


def plane(
    model: ContinuumModel | None,
    tool: str,
    *,
    image: str = "mean",
    colour: str = "material",
    band: tuple[float, float] | None = None,
    pick: str = "",
    mesh_held: str = "",
) -> Plane:
    """Return what the (r, z) view draws for one Continuum tool of a model.

    Parameters
    ----------
    image
        The picture Pore geometry draws, one of :data:`IMAGES`.
    colour
        What the Mesh tool colours its elements by, one of :data:`COLOURINGS`.
    band
        The quality range whose elements the Mesh tool fills, ``[low, high)``.
    pick
        Region's domain picked, one of :data:`DOMAINS`, or the Mesh tool's part, one of
        :data:`PARTS`, drawn over the rest.
    mesh_held
        The content hash of the mesh whose vertices, triangles and materials the view holds,
        which the drawing then leaves out.

    Raises
    ------
    ValueError
        If the tool, the picture, the colouring or the pick is not one this view draws.
    """
    if image not in IMAGES:
        raise ValueError(f"image {image!r} is not one of {', '.join(IMAGES)}")
    if colour not in COLOURINGS:
        raise ValueError(f"colour {colour!r} is not one of {', '.join(COLOURINGS)}")
    if tool not in ("geometry", "region", "mesh"):
        raise ValueError(f"tool {tool!r} is not a Continuum tool")
    if pick and pick not in (DOMAINS if tool == "region" else PARTS):
        raise ValueError(f"pick {pick!r} is not a domain or a part of the {tool} tool")
    blank = (0.0, 10.0, -10.0, 10.0)
    frame: Frame = "structure" if tool == "geometry" else "model"
    if model is None:
        empty = ("No continuum model is open.",)
        return Plane(frame, ("r (nm)", "z (nm)"), _extent([], blank), (), empty)
    if model.problem() is not None:
        refused = ("The model's file forms no case, so nothing is drawn: see the pane.",)
        return Plane(frame, ("r (nm)", "z (nm)"), _extent([], blank), (), refused)
    held = model.artefacts()
    if tool == "geometry":
        layers, notes, axis = _outline_layers(model, held, image=image)
        outline = next((layer["points_nm"] for layer in layers if layer["id"] == "contour"), None)
        layers = _edited(model, layers)
        membrane, _, _ = _values(model)
        extent = _extent(layers, blank)
        layers += _membrane(membrane, outline, r_high=extent[1])
        return Plane("structure", (axis, "z (nm)"), extent, tuple(layers), tuple(notes))
    outlines, drawing = _region_layers(
        held, filled=tool == "region", picked=pick if tool == "region" else ""
    )
    notes = (
        [] if outlines else [_unbuilt(model, "The region is not built yet: build it to draw it.")]
    )
    extent = _extent(outlines, blank)
    if tool == "region":
        layers = [*outlines, *_labels(model, extent)]
        return Plane("model", ("r (nm)", "z (nm)"), extent, tuple(layers), tuple(notes))
    if "mesh" not in held:
        notes.append(_unbuilt(model, "The mesh is not built yet: build it to draw it."))
        return Plane("model", ("r (nm)", "z (nm)"), extent, tuple(outlines), tuple(notes))
    over = None if drawing is None or not pick else _part_line(drawing, pick)
    mesh = _mesh_layer(_elements(held["mesh"]), held["mesh"].hash, colour, band, pick, mesh_held)
    return Plane(
        "model",
        ("r (nm)", "z (nm)"),
        extent,
        (mesh, *outlines, *([over] if over else [])),
        tuple(notes),
    )


def _nice(low: float, high: float) -> tuple[float, float]:
    if high - low <= 1e-12 * max(abs(low), abs(high), 1.0):
        low, high = low - 0.5, high + 0.5
    power = 10.0 ** math.floor(math.log10((high - low) / (PLOT_TICKS - 1)))
    for multiple in NICE_STEPS:
        step = multiple * power
        start = math.floor(low / step + 1e-9) * step
        end = start + (PLOT_TICKS - 1) * step
        if end >= high - 1e-9 * step:
            return round(start, 12), round(end, 12)
    return low, high


def _curve(
    identifier: str, title: str, x: np.ndarray, y: np.ndarray, colour: str
) -> dict[str, Any]:
    import numpy as np

    kept = np.isfinite(x) & np.isfinite(y)
    return {
        "id": identifier,
        "kind": "line",
        "title": title,
        "points_nm": _flat(np.column_stack((x[kept], y[kept]))),
        "colour": colour,
    }


def _electrolyte_plane(resolved: ResolvedCase, against: str) -> Plane:
    import numpy as np

    curves = case_correction_curves(resolved)
    electrolyte = resolved.electrolyte
    symbol = "I" if electrolyte.driver == "ionic_strength" else "⟨c⟩"
    driver_axis = f"{curves[0].driver_label if curves else symbol} (M)"
    if not curves:
        notes = ("Every correction is the none model: each factor is 1.",)
        return Plane("plot", (driver_axis, "correction factor"), (0.0, 1.0, 0.0, 2.0), (), notes)
    at_M = curves[0].at_driver_M
    layers: list[dict[str, Any]] = []
    if against == "driver":
        low, high = electrolyte.validity_M
        layers += [
            {
                "id": "validity",
                "kind": "band",
                "title": f"Fitted range, {low:g} to {high:g} M",
                "x": [low, high],
            },
            {"id": "driver", "kind": "rule", "title": f"Operating {symbol}, {at_M:g} M", "x": at_M},
        ]
        axes = (driver_axis, "correction factor")
        drawn = [(curve.driver_M, curve.factor_vs_driver) for curve in curves]
    else:
        distance = axis_label("distance d to the pore wall", "length")
        axes = (f"{distance}, at {symbol} = {at_M:g} M", "correction factor")
        drawn = [(curve.distance_m * 1e9, curve.factor_vs_distance) for curve in curves]
    # A curve keeps its colour while another correction is switched off.
    order = list(electrolyte.corrections)
    for curve, (x, y) in zip(curves, drawn, strict=True):
        title = curve.name.replace(":", ", ")
        colour = SERIES[order.index(curve.name) % len(SERIES)]
        layers.append(_curve(f"curve-{curve.name}", title[:1].upper() + title[1:], x, y, colour))
    xs = np.concatenate([x[np.isfinite(x)] for x, _ in drawn])
    ys = np.concatenate([y[np.isfinite(y)] for _, y in drawn])
    x_high = max(float(xs.max()), at_M) if against == "driver" else float(xs.max())
    # A factor is read against 1, the uncorrected value, so the axis always holds it.
    y_low, y_high = _nice(min(float(ys.min()), 1.0), max(float(ys.max()), 1.0))
    return Plane("plot", axes, (*_nice(0.0, x_high), y_low, y_high), tuple(layers))


def _stored_stages(resolved: ResolvedCase, store: Store) -> tuple[dict[str, Artefact], str | None]:
    try:
        identities = keyed_walk(resolved, store=store, planned=set())
    except REFUSED:
        return {}, None
    found: dict[str, Artefact] = {}
    for stage in ("region", "mesh"):
        identity = identities.get(stage)
        if identity is None or identity.built:
            continue
        stored = store.get(describe(stage).artefact_schema, identity.hash)
        if stored is not None:
            found[stage] = stored
    mesh = identities.get("mesh")
    return found, None if mesh is None else mesh.hash


def _deployed(
    resolved: ResolvedCase, artefact: Artefact | None, key: str | None
) -> tuple[str, MeshElements, dict[str, np.ndarray]]:
    def read() -> tuple[str, MeshElements, dict[str, np.ndarray]]:
        ingested = deployed_mesh(resolved, artefact)
        elements = mesh_elements(ingested.data, ingested.quality)
        return ingested.content_hash, elements, boundary_edges(ingested.data)

    if key is None:
        return read()
    # The deployment checks the mesh against the case's model and permittivities too, so a
    # case changed deploys its mesh anew; a pick, which changes no case, reads it once.
    case = hashlib.sha256(resolved.document.model_dump_json().encode("utf-8")).hexdigest()
    return _kept(_DEPLOYED, f"{key}-{case}", read)


def _role_lines(
    roles: Iterable[str], edges: dict[str, np.ndarray], *, ground: str, pick: str
) -> list[dict[str, Any]]:
    import numpy as np

    lines = []
    # The picked role last, so it is drawn over the others.
    for name in sorted((role for role in roles if role in edges), key=lambda role: role == pick):
        title = ROLE_TITLES.get(name, name.capitalize())
        line: dict[str, Any] = {
            "id": f"role-{name}",
            "kind": "line",
            "role": "picked" if name == pick else "boundary",
            # A boundary group's edges are drawn each alone: a group need not be one chain.
            "segments": True,
            "points_nm": np.round(edges[name], ROUND_NM).ravel().tolist(),
            "title": f"{title}, grounded" if name == ground else title,
        }
        if name != pick:
            line["colour"] = ROLE_COLOURS.get(name, SERIES[-1])
        lines.append(line)
    return lines


def _conditions_plane(
    resolved: ResolvedCase,
    store: Store,
    pick: str,
    mesh_held: str,
    blank: tuple[float, float, float, float],
) -> Plane:
    axes = ("r (nm)", "z (nm)")
    roles = role_conditions(case_model(resolved), resolved.ground)
    held, key = _stored_stages(resolved, store)
    outlines, _ = _region_layers(held, filled=True)
    try:
        mesh_hash, elements, edges = _deployed(resolved, held.get("mesh"), key)
    except KeyError:
        return Plane("model", axes, _extent(outlines, blank), tuple(outlines), (UNMESHED,))
    except (ValueError, OSError) as error:
        unread = (f"The mesh does not read, so nothing is drawn: {error}",)
        return Plane("model", axes, _extent(outlines, blank), tuple(outlines), unread)
    # The pore's outline frames the view, as in the Mesh tool; a supplied mesh, which has no
    # region, opens on its lumen.
    framing = [layer for layer in outlines if layer["id"] == "pore"]
    r_window, z_window = elements.lumen_nm
    extent = _extent(framing, (0.0, r_window, -z_window, z_window))
    mesh = _mesh_layer(elements, mesh_hash, "material", None, mesh_held=mesh_held)
    lines = _role_lines(roles, edges, ground=resolved.ground, pick=pick)
    return Plane("model", axes, extent, (mesh, *framing, *lines))


def physics_plane(
    case: Case | None,
    store: Store,
    tool: str,
    *,
    against: str = "driver",
    pick: str | None = None,
    mesh_held: str = "",
) -> Plane:
    """Return what the view draws for one Physics tool of the shown case.

    Parameters
    ----------
    case
        The shown case: a study's file with the model's physics, or None where it forms none.
    store
        The project's store, read for the stages the case's keys name.
    tool
        ``electrolyte``, a plot of each correction's factor; ``conditions``, the boundaries.
    against
        ``driver``: the factors against the concentration driver in M, with the fitted range
        and the operating driver; ``distance``: against the distance to the wall in nm.
    pick
        The boundary role the Conditions tool draws picked.
    mesh_held
        The content hash of the mesh whose vertices, triangles and materials the view holds,
        which the drawing then leaves out.

    Raises
    ------
    ValueError
        If the tool, ``against`` or the pick is not one this view draws.
    """
    if tool not in ("electrolyte", "conditions"):
        raise ValueError(f"tool {tool!r} is not a Physics tool the view draws")
    if against not in ("driver", "distance"):
        raise ValueError(f"against {against!r} is not 'driver' or 'distance'")
    if pick and pick not in BOUNDARY_VOCABULARY:
        raise ValueError(f"pick {pick!r} is not one of {', '.join(BOUNDARY_VOCABULARY)}")
    blank = (0.0, 10.0, -10.0, 10.0)
    frame: Frame = "plot" if tool == "electrolyte" else "model"
    if tool == "electrolyte":
        axis = (
            "concentration driver (M)"
            if against == "driver"
            else axis_label("distance d to the pore wall", "length")
        )
        axes, empty = (axis, "correction factor"), (0.0, 1.0, 0.0, 2.0)
    else:
        axes, empty = ("r (nm)", "z (nm)"), _extent([], blank)
    if case is None:
        return Plane(frame, axes, empty, (), ("No case is shown, so nothing is drawn.",))
    try:
        resolved = resolve(case, base=case.source.base)
    except REFUSED:
        refused = ("The shown case does not resolve, so nothing is drawn: see the pane.",)
        return Plane(frame, axes, empty, (), refused)
    if tool == "electrolyte":
        return _electrolyte_plane(resolved, against)
    return _conditions_plane(resolved, store, pick or "", mesh_held, blank)
