"""What the (r, z) view draws for each Continuum and Physics tool: its frame, extent and layers."""

from __future__ import annotations

import hashlib
import math
import re
import struct
import threading
import zlib
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, TypeVar

from nanopnp.core.stages import describe
from nanopnp.density.map import PAYLOAD_NAME as DENSITY_PAYLOAD
from nanopnp.density.map import DensityMap
from nanopnp.geometry.profile import load_profile
from nanopnp.gui.geometry import ImageModel, density_section, lookup_table, reduced_image
from nanopnp.gui.web.builds import REFUSED
from nanopnp.gui.web.continuum import ContinuumModel
from nanopnp.io.case import Membrane, Reservoir
from nanopnp.mesh.adapter import detect_format, read
from nanopnp.mesh.ingest import BOUNDARY_VOCABULARY, FLUID_MATERIALS, apply_groups, deployed_mesh
from nanopnp.mesh.primitives import PERMITTIVITY_EXEMPT
from nanopnp.physics.models import case_model, role_conditions
from nanopnp.pipeline.case import resolve
from nanopnp.pipeline.run import keyed_walk
from nanopnp.plot.data import (
    MeshElements,
    RegionDrawing,
    axis_label,
    boundary_edges,
    case_curves,
    colour_scale,
    contour_polygon_m,
    mesh_elements,
    mesh_of,
    reduced_map,
    region_drawing,
    region_edges,
)
from nanopnp.post.export import FIXED_CHARGE_ATTRIBUTE

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np
    from shapely.geometry.base import BaseGeometry

    from nanopnp.api.case import Case
    from nanopnp.geometry.outlines import Stage5Region
    from nanopnp.gui.charge import ChargeMap, ConservationView
    from nanopnp.io.artefact import Artefact
    from nanopnp.io.resolved import ResolvedCase
    from nanopnp.io.store import Store
    from nanopnp.materials.electrolyte import Electrolyte

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
    "charge_ends",
    "charge_plane",
    "deployed_layer",
    "electrolyte_plane",
    "image_png",
    "ion_text",
    "mesh_quality",
    "mesh_stored",
    "physics_plane",
    "plane",
    "png",
    "shown_solids",
    "unit_text",
]

Frame = Literal["structure", "model", "plot"]

_T = TypeVar("_T")

IMAGES: tuple[str, ...] = ("density", "mean", "cn_variance", "raw_variance")
"""The pictures Density draws, stage 2's section then stage 3's maps; Outline draws stage 3's."""

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

MESO_TOOLS: tuple[str, ...] = ("density", "outline")
"""The tools that draw in stage 1's frame: Meso's density and outline."""

STAGE_THREE: tuple[str, ...] = ("mean", "cn_variance", "raw_variance")
"""The pictures of stage 3's map, which the outline is drawn over."""

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

CURVE_PROPERTIES = ("viscosity", "density", "permittivity", "diffusivity", "mobility")
"""The corrected properties in the order their curves take the series' colours."""
ION_DASHES: tuple[tuple[int, ...], ...] = ((), (7, 4), (2, 3))
"""Each ion's dash, in the order the parameter set lists the ions: the first drawn solid."""
SQRT_TICKS_M = (0.0, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
"""The ticks of a square-root concentration axis, in M, far enough apart near its origin."""
STAND_IN_M = 1.0
"""The salt the curves of a model with none are evaluated at; the drawing shows no value of it."""
PLOT_TICKS = 5
"""How many ticks each axis of a plot carries, its two ends among them."""

NICE_STEPS = (1.0, 2.0, 2.5, 5.0, 10.0, 20.0)
"""The multiples of a power of ten a plot's tick step is chosen from."""

UNBUILT_REGION = (
    "The region of the shown study is not built. Build it in Continuum \u203a Region to see the "
    "boundaries."
)
"""What the Conditions view says where the shown case's stage-5 region is not stored."""
UNMESHED = "The mesh of the shown study is not built. Build it in Continuum \u203a Mesh to see it."
"""What the Conditions view says where *Show mesh* is on and no mesh is stored."""
REFUSED_SHOWN = "The shown study cannot run. The pane tells why."
"""What a Physics view says where the shown case does not resolve."""


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
    panels
        A plot's graphs, one above the other, each with its ``axes``, ``extent_nm``, x
        ``scale`` (``linear`` or ``sqrt``) and, optionally, its x ``ticks``; a layer names its
        graph by ``panel``. Empty: one graph of ``axes`` and ``extent_nm``.
    point_pick
        Whether a click asks about the point itself, as the charge map's residues, in place of
        picking a vertex, an element or a domain.
    key_below
        Whether a plot's key stands below it at any width, its rows in columns, so that a plot
        in a narrow pane keeps the pane's width.
    """

    frame: Frame
    axes: tuple[str, str]
    extent_nm: tuple[float, float, float, float]
    layers: tuple[dict[str, Any], ...]
    notes: tuple[str, ...] = ()
    panels: tuple[dict[str, Any], ...] = ()
    point_pick: bool = False
    key_below: bool = False

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
            **({"panels": list(self.panels)} if self.panels else {}),
            **({"point_pick": True} if self.point_pick else {}),
            **({"key_below": True} if self.key_below else {}),
        }


def png(rgba: bytes, width: int, height: int) -> bytes:
    """Return a PNG of tightly packed RGBA8888 rows, top row first."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    rows = b"".join(b"\x00" + rgba[y * width * 4 : (y + 1) * width * 4] for y in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


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
        "url": f"/api/meso/{model.name}/image?layer={identifier}&v={digest[:12]}",
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
    document_membrane: Membrane,
    outline: Sequence[float] | None,
    *,
    r_high: float,
    r_drawn: float = 0.0,
) -> list[dict[str, Any]]:
    """Return the membrane's faces in stage 1's frame, each from the outline's outer edge out.

    With no outline each starts at ``r_drawn``, the edge of what is drawn, so it crosses no
    protein and no lumen.
    """
    from shapely import LineString, Polygon

    centre = document_membrane.centre_z_nm
    half = 0.5 * document_membrane.thickness_nm
    solid = None
    if outline is not None and len(outline) >= 6:
        solid = Polygon(list(zip(outline[0::2], outline[1::2], strict=True))).buffer(0)
    faces = []
    for side, z in (("trans", centre - half), ("cis", centre + half)):
        start = r_drawn
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
    model: ContinuumModel, held: dict[str, Artefact], *, image: str, outlined: bool = True
) -> tuple[list[dict[str, Any]], list[str], str, np.ndarray | None]:
    """Return stages 2 to 4's layers in stage 1's frame, the notes, the r axis's name and the loop.

    ``outlined`` draws the outline and the probe over the picture; the loop is returned either way.
    """
    layers: list[dict[str, Any]] = []
    notes: list[str] = []
    axis = "r (nm)"
    stage = "density" if image == "density" else "symmetry"
    if stage in held:
        layers.append(_image(model, image, _picture(held[stage], image), held[stage].hash))
        if image == "density":
            axis = "x (nm), section y = 0"
    built = contour_polygon_m(held["contour"]) if "contour" in held else None
    supplied = _supplied(model)
    loop = built * 1e9 if built is not None else supplied
    if built is not None and outlined:
        layers.append(_polygon("contour", "contour", built * 1e9, "Outline, stage 4"))
        layers += _probe(held["contour"])
    elif supplied is not None:
        if outlined:
            layers.append(_polygon("contour", "contour", supplied, "Outline, supplied"))
        notes.append("The model supplies its outline (inputs.profile): stages 2 to 4 do not run.")
    if not layers and supplied is None:
        built_by = "the outline" if outlined else "the density"
        notes.append(_unbuilt(model, f"Nothing is built yet: build {built_by} to draw it."))
    return layers, notes, axis, loop


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
# A region's named boundaries, by its stage-5 artefact's hash.
_REGION_EDGES: dict[str, dict[str, np.ndarray]] = {}
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


def deployed_layer(
    path: Path, *, positive: Literal["blue", "red"] = "blue", span: float | None = None
) -> dict[str, Any]:
    """Return a run's deployed charge, one mean per element, as a mesh layer with its colour bar.

    ``path`` is the file :func:`nanopnp.gui.render.render_charge_elements` wrote. The charge's
    scale is symmetric about zero, a positive charge in the named colour, and runs to ``span``,
    or else opens on :func:`~nanopnp.plot.data.colour_scale`'s share of its size.
    """
    import numpy as np

    with np.load(path) as held:
        vertices = np.asarray(held["vertices_nm"], dtype=np.float64)
        triangles = np.asarray(held["triangles"], dtype=np.int64)
        values = np.asarray(held["values"], dtype=np.float64)
        material = np.asarray(held["material"], dtype=np.int64)
        name, units = str(held["name"]), str(held["units"])
    charge = name == FIXED_CHARGE_ATTRIBUTE
    scale_of = colour_scale(values)
    limit = scale_of.largest
    top = 1.0
    if charge:
        top = _span(limit, scale_of.clip, span)
        scale = [-top, top]
        palette = _charge_palette(positive)
    else:
        scale = [0.0, 1.0]
        palette = _stops(lookup_table("viridis"))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    return {
        "id": "deployed",
        "kind": "mesh",
        "mesh": f"deployed-{digest}",
        "vertices_nm": vertices.ravel().tolist(),
        "triangles": triangles.ravel().tolist(),
        "material": material.tolist(),
        "colour": name,
        "values": values.tolist(),
        "palette": palette,
        "scale": scale,
        "legend": [],
        "categorical": False,
        "outlined": [],
        "bar": (
            {"quantity": "Fixed charge density", "unit": unit_text(units), "clipped": top < limit}
            if charge
            else {"quantity": name, "unit": unit_text(units)}
        ),
        **({"dark": {"palette": _charge_palette(positive, dark=True)}} if charge else {}),
        "largest": limit,
    }


CHARGE_AXES = ("r (nm)", "z (nm)")
NO_LATTICE = "The charge stores no lattice to draw: it is supplied on the mesh."
NO_DEPLOYED = (
    "The deployed charge is read from the charge's run record. Build the charge map to write one."
)


def _charge_palette(positive: Literal["blue", "red"], *, dark: bool = False) -> list[str]:
    if positive == "blue":
        return _stops(lookup_table("diverging_dark_r" if dark else "diverging_r"))
    return _stops(lookup_table("diverging_dark" if dark else "diverging"))


def _span(limit: float, clip: float, span: float | None) -> float:
    """Return how far a charge's scale runs each side of zero: ``span``, else the clip."""
    # An all-zero charge still needs a range a colour map can divide by.
    for value in (span, clip, limit):
        if value is not None and value > 0.0:
            return value
    return 1.0


def charge_ends(positive: Literal["blue", "red"] = "blue") -> tuple[str, str]:
    """Return the colours of a positive and a negative charge at the ends of the charge's scale."""
    palette = _charge_palette(positive)
    return palette[-1], palette[0]


def charge_plane(
    shown: ChargeMap | None,
    conservation: ConservationView | None,
    *,
    image_url: str,
    positive: Literal["blue", "red"] = "blue",
    deployed: Path | None = None,
    layer: Literal["lattice", "deployed"] = "lattice",
    picked: tuple[str, Sequence[tuple[float, float, float]]] | None = None,
    span: float | None = None,
) -> Plane:
    """Return the charge on the mesh: the lattice or the deployed charge, with its bar.

    Each worst plane of the conservation record is a dashed line across the map, in the warning
    colour where its leg is over its tolerance, and a picked residue's charged atoms are rings in
    the charge's own colours. A click asks about its point.

    Parameters
    ----------
    image_url
        Where the canvas reads the lattice's picture, which the dark theme asks for with
        ``&middle=dark``.
    deployed
        The file of the deployed charge per element, where one is drawn.
    picked
        The picked residue's key and its charged atoms, each ``(r_nm, z_nm, q_e)``.
    span
        How far the scale runs each side of zero; by default the layer's clip.
    """
    palette = _charge_palette(positive)
    layers: list[dict[str, Any]] = []
    notes: list[str] = []
    extent: tuple[float, float, float, float] | None = None
    if shown is not None:
        r_low, r_high, z_low, z_high = shown.image.extent_nm
        extent = (r_low, r_high, z_low, z_high)
    if layer == "deployed":
        if deployed is None:
            notes.append(NO_DEPLOYED)
        else:
            drawn = deployed_layer(deployed, positive=positive, span=span)
            layers.append(drawn)
            if extent is None:
                rs, zs = drawn["vertices_nm"][0::2], drawn["vertices_nm"][1::2]
                extent = (min(rs), max(rs), min(zs), max(zs))
    elif shown is None:
        notes.append(NO_LATTICE)
    else:
        top = _span(shown.limit, shown.clip, span)
        layers.append(
            {
                "id": "lattice",
                "kind": "image",
                "url": image_url,
                "extent_nm": [round(v, ROUND_NM) for v in shown.image.extent_nm],
                "scale": [-top, top],
                "title": shown.image.title,
                "bar": {
                    "quantity": shown.quantity.replace("_", " ").capitalize(),
                    "unit": unit_text(shown.units),
                    "low": -top,
                    "high": top,
                    "palette": palette,
                    "clipped": top < shown.limit,
                },
                "dark": {
                    "url": f"{image_url}&middle=dark",
                    "bar": _charge_palette(positive, dark=True),
                },
                "largest": shown.limit,
            }
        )
    if extent is not None and layers and conservation is not None:
        over = {leg.name for leg in conservation.legs if leg.ratio is not None and leg.ratio > 1.0}
        for label, z_nm in conservation.planes:
            side = label.removeprefix("worst plane (").rstrip(")")
            layers.append(
                _line(
                    f"worst-{side}",
                    # A plane within its tolerance is a place, not a warning.
                    "worst" if label in over else "plane",
                    [(extent[0], z_nm), (extent[1], z_nm)],
                    f"{label.capitalize()}, z = {z_nm:.4g} nm",
                )
            )
    if picked is not None and picked[1] and layers:
        residue, markers = picked
        layers.append(
            {
                "id": "residue",
                "kind": "points",
                "points_nm": _flat((r, z) for r, z, _ in markers),
                "colours": [palette[-1] if q > 0 else palette[0] for _, _, q in markers],
                "title": f"Residue {residue}, its charged atoms",
                # Keyed as rings, one of each sign it holds.
                "ring": True,
            }
        )
    framed = _extent(layers, extent or (0.0, 1.0, -1.0, 1.0))
    return Plane("model", CHARGE_AXES, framed, tuple(layers), tuple(notes), point_pick=bool(layers))


def _atoms_layer(residue: str, atoms: Sequence[tuple[float, float, float]]) -> dict[str, Any]:
    """Return a residue's atoms as points at (r, z), on a density section at x = r."""
    return {
        "id": "residue",
        "kind": "points",
        "points_nm": _flat((r, z) for r, z, _ in atoms),
        "colours": [SERIES[4]] * len(atoms),
        "title": f"Residue {residue}, its atoms",
        "ring": True,
    }


def _edited(model: ContinuumModel, layers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Put the hand edit held in place of the outline, over the outline it was edited from."""
    editor = model.editor()
    if editor is None:
        return layers
    kept = [layer for layer in layers if layer["id"] != "contour"]
    opened = [layer for layer in layers if layer["id"] == "contour"]
    edit = {**_polygon("contour", "contour", editor.vertices, "Edited outline"), "editable": True}
    if not editor.changed and opened:
        # Before its first change the edit is the outline it opened on, keyed as that outline.
        return [*kept, {**edit, "title": opened[0].get("title", "")}]
    original = [
        {**layer, "id": "original", "role": "original", "title": "Outline before the edit"}
        for layer in opened
    ]
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
    marked: tuple[str, Sequence[tuple[float, float, float]]] | None = None,
) -> Plane:
    """Return what the (r, z) view draws for one tool of a continuum model, Meso's or its own.

    Density draws its picture and the membrane, and a click asks about its point; Outline draws
    stage 3's picture under the outline, the probe and the edit held.

    Parameters
    ----------
    image
        The picture Density or Outline draws, one of :data:`IMAGES`; Outline's, of stage 3.
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
    marked
        A residue's key and its atoms, each ``(r_nm, z_nm, q_e)`` in stage 1's frame, marked on
        Density's and Outline's drawings.

    Raises
    ------
    ValueError
        If the tool, the picture, the colouring or the pick is not one this view draws.
    """
    if image not in (STAGE_THREE if tool == "outline" else IMAGES):
        raise ValueError(f"image {image!r} is not one of {tool}'s pictures")
    if colour not in COLOURINGS:
        raise ValueError(f"colour {colour!r} is not one of {', '.join(COLOURINGS)}")
    if tool not in (*MESO_TOOLS, "region", "mesh"):
        raise ValueError(f"tool {tool!r} is not a tool of a continuum model's (r, z) view")
    if pick and pick not in (DOMAINS if tool == "region" else PARTS):
        raise ValueError(f"pick {pick!r} is not a domain or a part of the {tool} tool")
    blank = (0.0, 10.0, -10.0, 10.0)
    frame: Frame = "structure" if tool in MESO_TOOLS else "model"
    if model is None:
        empty = ("No continuum model is open.",)
        return Plane(frame, ("r (nm)", "z (nm)"), _extent([], blank), (), empty)
    if model.problem() is not None:
        refused = ("The model's file forms no case, so nothing is drawn: see the pane.",)
        return Plane(frame, ("r (nm)", "z (nm)"), _extent([], blank), (), refused)
    held = model.artefacts()
    if tool in MESO_TOOLS:
        outlined = tool == "outline"
        layers, notes, axis, loop = _outline_layers(model, held, image=image, outlined=outlined)
        if outlined:
            layers = _edited(model, layers)
        membrane, _, _ = _values(model)
        extent = _extent(layers, blank)
        outline = None if loop is None else _flat(loop)
        drawn = _bounds(layers)
        layers += _membrane(
            membrane, outline, r_high=extent[1], r_drawn=0.0 if drawn is None else drawn[1]
        )
        if marked is not None and marked[1]:
            layers.append(_atoms_layer(*marked))
        return Plane(
            "structure",
            (axis, "z (nm)"),
            extent,
            tuple(layers),
            tuple(notes),
            point_pick=not outlined,
        )
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
    identifier: str, title: str, x: np.ndarray, y: np.ndarray, colour: str, panel: int
) -> dict[str, Any]:
    import numpy as np

    kept = np.isfinite(x) & np.isfinite(y)
    return {
        "id": identifier,
        "kind": "line",
        "title": title,
        "points_nm": _flat(np.column_stack((x[kept], y[kept]))),
        "colour": colour,
        "panel": panel,
    }


_SUPERSCRIPT = str.maketrans(
    "0123456789+-", "\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079\u207a\u207b"
)


def unit_text(units: str) -> str:
    """Return a unit as the panes write it, each power raised: ``C/m^3`` reads ``C m⁻³``."""
    raised = re.sub(r"\^([+-]?\d+)", lambda found: found.group(1).translate(_SUPERSCRIPT), units)
    over, slash, under = raised.partition("/")
    if not slash or "/" in under:
        return raised
    # One unit over another: the divisor's power negative, as C m⁻² in the panes.
    power = re.search(r"[\u2070\u00b9\u00b2\u00b3\u2074-\u2079]+$", under)
    base = under[: power.start()] if power else under
    return f"{over} {base}\u207b{power.group(0) if power else chr(0xB9)}"


def ion_text(name: str) -> str:
    """Return an ion's name with its charge raised, as Na⁺ for ``Na+``."""
    base = name.rstrip("+-0123456789")
    return base + name[len(base) :].translate(_SUPERSCRIPT) if base else name


def _curve_style(name: str, ions: list[str]) -> tuple[str, list[int]]:
    # The colour follows the property, the dash the ion.
    prop, _, ion = name.partition(":")
    colour = (
        SERIES[CURVE_PROPERTIES.index(prop) % len(SERIES)]
        if prop in CURVE_PROPERTIES
        else SERIES[-1]
    )
    rank = ions.index(ion) if ion in ions else 0
    return colour, list(ION_DASHES[rank % len(ION_DASHES)])


def _factor_range(curves: Iterable[np.ndarray]) -> tuple[float, float]:
    import numpy as np

    values = np.concatenate([curve[np.isfinite(curve)] for curve in curves])
    # A factor is read against 1, the uncorrected value, so the axis always holds it.
    return _nice(min(float(values.min()), 1.0), max(float(values.max()), 1.0))


def electrolyte_plane(electrolyte: Electrolyte, concentration_M: float | None) -> Plane:
    """Return Electrolyte's two graphs: each correction against the driver, then the wall distance.

    Without a concentration, as for a model that sets no salt, the curves against the driver are
    drawn alone, with no operating value: they read none.
    """
    import numpy as np

    operating = concentration_M is not None
    curves = case_curves(electrolyte, STAND_IN_M if concentration_M is None else concentration_M)
    named = (
        curves[0].driver_label
        if curves
        else "ionic strength I"
        if electrolyte.driver == "ionic_strength"
        else "average concentration"
    )
    # The canvas draws in the interface's face, which has no angle brackets: the axis names the
    # average in words, and the marks write it c.
    symbol = "I" if electrolyte.driver == "ionic_strength" else "c"
    bracketed = " \u27e8c\u27e9"
    driver_axis = f"{named.replace(bracketed, '')} (M)"
    if not curves:
        flat = ("Each correction is the none model, so each factor is 1.",)
        return Plane("plot", (driver_axis, "correction factor"), (0.0, 1.0, 0.0, 2.0), (), flat)
    at_M = curves[0].at_driver_M
    low, high = electrolyte.validity_M
    layers: list[dict[str, Any]] = [
        {
            "id": "validity",
            "kind": "band",
            "title": f"Fitted range, {low:g} to {high:g} M",
            "x": [low, high],
            "panel": 0,
        }
    ]
    if operating:
        layers.append(
            {
                "id": "driver",
                "kind": "rule",
                "title": f"Operating {symbol}, {at_M:g} M",
                "x": at_M,
                "panel": 0,
            }
        )
    ions = [species.name for species in electrolyte.species]
    for curve in curves:
        prop, _, ion = curve.name.partition(":")
        title = f"{prop.capitalize()}, {ion_text(ion)}" if ion else prop.capitalize()
        colour, dash = _curve_style(curve.name, ions)
        drawn = [(0, curve.driver_M, curve.factor_vs_driver)]
        if operating:
            drawn.append((1, curve.distance_m * 1e9, curve.factor_vs_distance))
        for panel, x, y in drawn:
            line = _curve(f"curve-{panel}-{curve.name}", title, x, y, colour, panel)
            layers.append({**line, "dash": dash})
    x_high = max(float(np.nanmax(curves[0].driver_M)), at_M)
    panels: list[dict[str, Any]] = [
        {
            "axes": [driver_axis, "correction factor"],
            "extent_nm": [0.0, x_high, *_factor_range(c.factor_vs_driver for c in curves)],
            "scale": "sqrt",
            "ticks": [tick for tick in SQRT_TICKS_M if tick <= x_high],
        }
    ]
    notes: tuple[str, ...] = ()
    if operating:
        distance = axis_label("distance d to the pore wall", "length")
        d_high = float(np.nanmax(curves[0].distance_m)) * 1e9
        panels.append(
            {
                "axes": [f"{distance}, at {symbol} = {at_M:g} M", "correction factor"],
                "extent_nm": [
                    0.0,
                    d_high,
                    *_factor_range(c.factor_vs_distance for c in curves),
                ],
                "scale": "linear",
                "ticks": [0.5 * k for k in range(int(2 * d_high) + 1)],
            }
        )
    else:
        notes = ("Type the concentration to see the factors against the distance to the wall.",)
    first = panels[0]
    return Plane(
        "plot",
        tuple(first["axes"]),
        tuple(first["extent_nm"]),
        tuple(layers),
        notes,
        panels=tuple(panels),
    )


def _stored_stages(
    resolved: ResolvedCase, store: Store, upto: str | None = None
) -> tuple[dict[str, Artefact], str | None]:
    identities = keyed_walk(resolved, store=store, planned=set(), upto=upto)
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


def _region_boundaries(artefact: Artefact, record: Stage5Region) -> dict[str, np.ndarray]:
    return _kept(_REGION_EDGES, artefact.hash, lambda: region_edges(record))


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
    # In the roles' own order, which the key keeps; the view draws the picked one over the rest.
    for name in (role for role in roles if role in edges):
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
    *,
    mesh: bool,
) -> Plane:
    axes = ("r (nm)", "z (nm)")
    roles = role_conditions(case_model(resolved), resolved.ground)
    if resolved.mesh is not None:
        # A supplied mesh has no region: its own boundaries are drawn.
        return _supplied_conditions(resolved, store, roles, pick, mesh_held, blank)
    try:
        # The region and the mesh are keyed alone, so a later stage's check does not hide them.
        held, key = _stored_stages(resolved, store, upto="mesh")
    except REFUSED:
        return Plane("model", axes, _extent([], blank), (), (REFUSED_SHOWN,))
    domains, drawing = _region_layers(held, filled=True)
    if drawing is None:
        return Plane("model", axes, _extent([], blank), (), (UNBUILT_REGION,))
    framing = [layer for layer in domains if layer["id"] == "pore"]
    extent = _extent(framing, blank)
    edges = _region_boundaries(held["region"], drawing.record)
    lines = _role_lines(roles, edges, ground=resolved.ground, pick=pick)
    if not mesh:
        return Plane("model", axes, extent, (*domains, *lines))
    if "mesh" not in held:
        return Plane("model", axes, extent, (*domains, *lines), (UNMESHED,))
    try:
        mesh_hash, elements, _ = _deployed(resolved, held["mesh"], key)
    except (KeyError, ValueError, OSError) as error:
        unread = (f"The mesh does not read: {error}",)
        return Plane("model", axes, extent, (*domains, *lines), unread)
    drawn = _mesh_layer(elements, mesh_hash, "material", None, mesh_held=mesh_held)
    # The mesh takes the domains' place; the region's outlines and the roles stay as they were.
    outlines = [layer for layer in domains if layer["kind"] != "domain"]
    return Plane("model", axes, extent, (drawn, *outlines, *lines))


def _supplied_conditions(
    resolved: ResolvedCase,
    store: Store,
    roles: dict[str, dict[str, str]],
    pick: str,
    mesh_held: str,
    blank: tuple[float, float, float, float],
) -> Plane:
    axes = ("r (nm)", "z (nm)")
    try:
        mesh_hash, elements, edges = _deployed(resolved, None, None)
    except (KeyError, ValueError, OSError) as error:
        return Plane("model", axes, _extent([], blank), (), (f"The mesh does not read: {error}",))
    r_window, z_window = elements.lumen_nm
    extent = _extent([], (0.0, r_window, -z_window, z_window))
    drawn = _mesh_layer(elements, mesh_hash, "material", None, mesh_held=mesh_held)
    lines = _role_lines(roles, edges, ground=resolved.ground, pick=pick)
    return Plane("model", axes, extent, (drawn, *lines))


def mesh_stored(case: Case | None, store: Store) -> bool:
    """Return whether a shown case's mesh is supplied or stored, which *Show mesh* draws."""
    if case is None:
        return False
    try:
        resolved = resolve(case, base=case.source.base)
        if resolved.mesh is not None:
            return True
        held, _ = _stored_stages(resolved, store, upto="mesh")
    except REFUSED:
        return False
    return "mesh" in held


def shown_solids(case: Case | None, store: Store) -> tuple[str, ...] | None:
    """Return the solids of the mesh the store holds for a shown case, or None where it holds none.

    The fluids are left out, and so is the ion-exclusion shell, which takes the fluid's
    permittivity.
    """
    if case is None:
        return None
    try:
        resolved = resolve(case, base=case.source.base)
        supplied = resolved.mesh
        if supplied is not None and supplied.path is not None:
            # A supplied mesh is read for its names alone, mapped as a run maps them.
            path = Path(supplied.path)
            read_in = read(path, format=detect_format(path, supplied.format))
            materials: object = list(apply_groups(read_in, dict(supplied.groups))[0].materials)
        else:
            # Keyed to the mesh alone, so a later stage's check, such as a solid with no
            # permittivity, does not hide the solids it names.
            held, _ = _stored_stages(resolved, store, upto="mesh")
            materials = held["mesh"].summary.get("materials") if "mesh" in held else None
    except REFUSED:
        return None
    if not isinstance(materials, list):
        return None
    return tuple(
        name
        for name in map(str, materials)
        if name not in FLUID_MATERIALS and name not in PERMITTIVITY_EXEMPT
    )


def physics_plane(
    case: Case | None,
    store: Store,
    tool: str,
    *,
    pick: str | None = None,
    mesh_held: str = "",
    mesh: bool = False,
) -> Plane:
    """Return what the view draws for one Physics tool of the shown case.

    Parameters
    ----------
    case
        The shown case: a study's file with the model's physics, or None where it forms none.
    store
        The project's store, read for the stages the case's keys name.
    tool
        ``electrolyte``, each correction's factor against the concentration driver, then
        against the distance to the wall; ``conditions``, the boundaries.
    pick
        The boundary role the Conditions tool draws picked.
    mesh_held
        The content hash of the mesh whose vertices, triangles and materials the view holds,
        which the drawing then leaves out.
    mesh
        Whether the Conditions view draws the stored mesh in place of the region's domains.

    Raises
    ------
    ValueError
        If the tool or the pick is not one this view draws.
    """
    if tool not in ("electrolyte", "conditions"):
        raise ValueError(f"tool {tool!r} is not a Physics tool the view draws")
    if pick and pick not in BOUNDARY_VOCABULARY:
        raise ValueError(f"pick {pick!r} is not one of {', '.join(BOUNDARY_VOCABULARY)}")
    blank = (0.0, 10.0, -10.0, 10.0)
    frame: Frame = "plot" if tool == "electrolyte" else "model"
    if tool == "electrolyte":
        axes, empty = ("concentration driver (M)", "correction factor"), (0.0, 1.0, 0.0, 2.0)
    else:
        axes, empty = ("r (nm)", "z (nm)"), _extent([], blank)
    if case is None:
        return Plane(frame, axes, empty, (), (REFUSED_SHOWN,))
    try:
        resolved = resolve(case, base=case.source.base)
    except REFUSED:
        return Plane(frame, axes, empty, (), (REFUSED_SHOWN,))
    if tool == "electrolyte":
        return electrolyte_plane(resolved.electrolyte, resolved.concentration_M)
    return _conditions_plane(resolved, store, pick or "", mesh_held, blank, mesh=mesh)
