"""What the Continuum suite's (r, z) view draws for each tool: its frame, extent and layers."""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from nanopnp.density.map import PAYLOAD_NAME as DENSITY_PAYLOAD
from nanopnp.density.map import DensityMap
from nanopnp.geometry.profile import load_profile
from nanopnp.gui.geometry import ImageModel, density_section, lookup_table, reduced_image
from nanopnp.gui.web.continuum import ContinuumModel
from nanopnp.gui.web.link import png
from nanopnp.io.case import Membrane, Reservoir
from nanopnp.plot.data import MeshElements, contour_polygon_m, mesh_of, reduced_map, region_drawing

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

    from nanopnp.io.artefact import Artefact

__all__ = [
    "COLOURINGS",
    "IMAGES",
    "MATERIAL_COLOURS",
    "Plane",
    "image_png",
    "plane",
]

Frame = Literal["structure", "model"]

IMAGES: tuple[str, ...] = ("density", "mean", "cn_variance", "raw_variance")
"""The pictures Protein geometry draws under its outline: stage 2's section, then stage 3's maps."""

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


@dataclass(frozen=True)
class Plane:
    """One drawing of the (r, z) view.

    Parameters
    ----------
    frame
        ``structure``, stage 1's frame, where stages 2 to 4 draw; ``model``, the membrane at
        z = 0, where the region and the mesh draw. The view keeps its pan and zoom while the
        frame stays the same.
    extent_nm
        ``(r_low, r_high, z_low, z_high)`` the view opens on: the pore, not the reservoir.
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
            "layers": list(self.layers),
            "notes": list(self.notes),
        }


def _flat(points_nm: Iterable[Sequence[float]]) -> list[float]:
    return [round(float(value), ROUND_NM) for point in points_nm for value in point[:2]]


def _line(identifier: str, role: str, points_nm: Iterable[Sequence[float]]) -> dict[str, Any]:
    return {"id": identifier, "kind": "line", "role": role, "points_nm": _flat(points_nm)}


def _polygon(identifier: str, role: str, points_nm: Iterable[Sequence[float]]) -> dict[str, Any]:
    return {"id": identifier, "kind": "polygon", "role": role, "points_nm": _flat(points_nm)}


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
        elif layer.get("role") in FRAMED:
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
    return min(r0, 0.0) - pad, r1 + pad, z0 - pad, z1 + pad


def _image(
    model: ContinuumModel, identifier: str, picture: ImageModel, digest: str
) -> dict[str, Any]:
    return {
        "id": identifier,
        "kind": "image",
        "url": f"/api/continuum/{model.name}/image?layer={identifier}&v={digest[:12]}",
        "extent_nm": [round(v, ROUND_NM) for v in picture.extent_nm],
        "scale": list(picture.scale),
        "title": picture.title,
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


def _membrane(document_membrane: Membrane, *, frame: Frame, r_high: float) -> list[dict[str, Any]]:
    centre = document_membrane.centre_z_nm if frame == "structure" else 0.0
    half = 0.5 * document_membrane.thickness_nm
    return [
        _line(f"membrane-{side}", "membrane", [(0.0, z), (r_high, z)])
        for side, z in (("trans", centre - half), ("cis", centre + half))
    ]


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
            layers.append(_line(role, role, points))
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
        layers.append(_polygon("contour", "contour", loop * 1e9))
        layers += _probe(held["contour"])
    elif supplied is not None:
        layers.append(_polygon("contour", "contour", supplied))
        notes.append("The model supplies its outline (inputs.profile): stages 2 to 4 do not run.")
    if not layers:
        notes.append("Nothing is built yet: build the geometry to draw it.")
    return layers, notes, axis


def _region_layers(model: ContinuumModel, held: dict[str, Artefact]) -> list[dict[str, Any]]:
    drawing = region_drawing(held["region"]) if "region" in held else None
    if drawing is None:
        return []
    layers = [
        _polygon("pore", "pore", drawing.pore_m * 1e9),
        _polygon("membrane", "membrane", drawing.membrane_m * 1e9),
    ]
    if drawing.exclusion_m is not None:
        layers.append(_polygon("exclusion", "exclusion", drawing.exclusion_m * 1e9))
    radius = drawing.reservoir_radius_m * 1e9
    arc = [
        (radius * math.cos(angle), radius * math.sin(angle))
        for angle in (math.pi * (k / 64 - 0.5) for k in range(65))
    ]
    layers.append(_line("reservoir", "reservoir", arc))
    return layers


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


_MESHES: dict[str, MeshElements] = {}


def _mesh_layer(artefact: Artefact, colour: str) -> dict[str, Any]:
    import numpy as np

    elements = _MESHES.get(artefact.hash)
    if elements is None:
        found = mesh_of(artefact, None)
        if found is None:
            raise ValueError(f"stage 6's artefact {artefact.hash[:12]} holds no mesh")
        elements = _MESHES.setdefault(artefact.hash, found)
    if colour == "material":
        values = elements.material.tolist()
        palette = [MATERIAL_COLOURS.get(name, "#cccccc") for name in elements.materials]
        scale: list[float] = [0.0, float(max(len(palette) - 1, 1))]
        legend = list(elements.materials)
    else:
        quality = elements.sicn if colour == "sicn" else elements.gamma
        values = np.round(quality, 4).tolist()
        table = lookup_table("viridis")
        picks = np.linspace(0, len(table) - 1, QUALITY_STOPS).round().astype(int)
        palette = [f"#{r:02x}{g:02x}{b:02x}" for r, g, b, _ in table[picks]]
        scale = [0.0, 1.0]
        legend = []
    return {
        "id": "mesh",
        "kind": "mesh",
        "colour": colour,
        "vertices_nm": np.round(elements.vertices_m * 1e9, ROUND_NM).ravel().tolist(),
        "triangles": elements.triangles.ravel().tolist(),
        "values": values,
        "palette": palette,
        "scale": scale,
        "legend": legend,
        "categorical": colour == "material",
    }


def plane(
    model: ContinuumModel | None, tool: str, *, image: str = "mean", colour: str = "material"
) -> Plane:
    """Return what the (r, z) view draws for one Continuum tool of a model.

    Parameters
    ----------
    image
        The picture Protein geometry draws, one of :data:`IMAGES`; Contour draws the mean.
    colour
        What the Mesh tool colours its elements by, one of :data:`COLOURINGS`.

    Raises
    ------
    ValueError
        If the tool, the picture or the colouring is not one this view draws.
    """
    if image not in IMAGES:
        raise ValueError(f"image {image!r} is not one of {', '.join(IMAGES)}")
    if colour not in COLOURINGS:
        raise ValueError(f"colour {colour!r} is not one of {', '.join(COLOURINGS)}")
    blank = (0.0, 10.0, -10.0, 10.0)
    if model is None:
        frame: Frame = "structure" if tool in ("geometry", "contour") else "model"
        empty = ("No continuum model is open.",)
        return Plane(frame, ("r (nm)", "z (nm)"), _extent([], blank), (), empty)
    if model.problem() is not None:
        frame = "structure" if tool in ("geometry", "contour") else "model"
        refused = ("The model's file forms no case, so nothing is drawn: see the pane.",)
        return Plane(frame, ("r (nm)", "z (nm)"), _extent([], blank), (), refused)
    held = model.artefacts()
    if tool in ("geometry", "contour"):
        layers, notes, axis = _outline_layers(
            model, held, image=image if tool == "geometry" else "mean"
        )
        membrane, _, _ = _values(model)
        extent = _extent(layers, blank)
        layers += _membrane(membrane, frame="structure", r_high=extent[1])
        return Plane("structure", (axis, "z (nm)"), extent, tuple(layers), tuple(notes))
    if tool not in ("region", "mesh"):
        raise ValueError(f"tool {tool!r} is not a Continuum tool")
    outlines = _region_layers(model, held)
    notes = [] if outlines else ["The region is not built yet: build it to draw it."]
    extent = _extent(outlines, blank)
    if tool == "region":
        layers = [*outlines, *_labels(model, extent)]
        return Plane("model", ("r (nm)", "z (nm)"), extent, tuple(layers), tuple(notes))
    if "mesh" not in held:
        notes.append("The mesh is not built yet: build it to draw it.")
        return Plane("model", ("r (nm)", "z (nm)"), extent, tuple(outlines), tuple(notes))
    return Plane(
        "model",
        ("r (nm)", "z (nm)"),
        extent,
        (_mesh_layer(held["mesh"], colour), *outlines),
        tuple(notes),
    )
