"""Arrays for every figure, read from stored artefacts in SI and the model frame; no drawing."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from nanopnp.charge.protonation import PAYLOAD_NAME as PROTONATION_PAYLOAD
from nanopnp.charge.protonation import ProtonationTable
from nanopnp.charge.stage import EPS_R_PAYLOAD, stored_lattice
from nanopnp.core.hashing import decode_floats
from nanopnp.density.grid import read_grid
from nanopnp.density.map import PAYLOAD_NAME as DENSITY_PAYLOAD
from nanopnp.density.map import DensityMap
from nanopnp.geometry.pore import IdealisedRegionRecord
from nanopnp.geometry.profile import PAYLOAD_NAME as PROFILE_PAYLOAD
from nanopnp.geometry.profile import load_profile
from nanopnp.geometry.region import PAYLOAD_NAME as REGION_PAYLOAD
from nanopnp.geometry.region import RegionRecord, read_region
from nanopnp.io.artefact import SWEEP_SCHEMA, Artefact, StageInputs
from nanopnp.mesh.adapter import MeshData
from nanopnp.mesh.adapter import read as read_mesh
from nanopnp.mesh.ingest import MESH_PAYLOAD, deployed_mesh
from nanopnp.mesh.quality import QualityReport, element_quality
from nanopnp.post.export import lumen_extent_nm
from nanopnp.solve.state import NEWTON_HISTORY_KEY
from nanopnp.structure.ensemble import PAYLOAD_NAME as ENSEMBLE_PAYLOAD
from nanopnp.structure.ensemble import AlignedEnsemble
from nanopnp.symmetry.reduce import PAYLOAD_NAME as REDUCED_PAYLOAD
from nanopnp.symmetry.reduce import ReducedMap

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np
    from matplotlib.tri import Triangulation

    from nanopnp.materials.models import CorrectionModel
    from nanopnp.post.export import SolutionFields

__all__ = [
    "CUTLINE_POINTS",
    "DISPLAY",
    "FIELD_ALIASES",
    "LUMEN_NM",
    "QOI_UNITS",
    "SICN_FLOOR",
    "CorrectionCurves",
    "Display",
    "MeshElements",
    "NewtonRung",
    "ProtonationCharges",
    "RegionDrawing",
    "StoredGrid",
    "SweepCurves",
    "atoms_r_z_m",
    "axial_cutline",
    "axial_section",
    "axis_label",
    "charge_grids",
    "cis_referenced_bias_V",
    "contour_polygon_m",
    "correction_curves",
    "default_potential_range_mV",
    "density_section",
    "element_sizes_m",
    "field_menu",
    "field_values",
    "fields_lumen_nm",
    "lumen_window_nm",
    "mesh_elements",
    "newton_history",
    "protonation_charges",
    "qoi_rows",
    "radial_cutline",
    "reduced_map",
    "region_drawing",
    "sampled",
    "structure_atoms",
    "subdivided",
    "sweep_curves",
]

SICN_FLOOR = 0.3
"""The mesh gate's quality floor, marked on the SICN panel (SPECIFICATION.md NUM-14)."""

MAX_ATOMS_DRAWN = 40000

_NM = 1e-9


@dataclass(frozen=True)
class Display:
    """A quantity's display unit; ``value_display = value_SI * per_SI``."""

    unit: str
    per_SI: float


DISPLAY: dict[str, Display] = {
    "length": Display("nm", 1e9),
    "concentration": Display("M", 1e-3),
    "potential": Display("mV", 1e3),
    "velocity": Display("µm/s", 1e6),
    "pressure": Display("Pa", 1.0),
    "charge_density": Display("C/m³", 1.0),
    "density": Display("1", 1.0),
    "current": Display("nA", 1e9),
    "conductance": Display("nS", 1e9),
    "flow": Display("µm³/s", 1e18),
    "force": Display("pN", 1e12),
}
"""Every display unit of a figure, in one place; an axis names its unit from here."""


def axis_label(name: str, quantity: str) -> str:
    """Return ``name (unit)`` for a quantity of :data:`DISPLAY`."""
    return f"{name} ({DISPLAY[quantity].unit})"


def _payload(artefact: Artefact, key: str) -> Path | None:
    return artefact.payload.get(key)


# --- stage 1 ---------------------------------------------------------------------------------


def atoms_r_z_m(positions_nm: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(r, z)`` in m of ``(..., 3)`` positions in nm, with ``r = hypot(x, y)``."""
    import numpy as np

    points = np.asarray(positions_nm, dtype=np.float64).reshape(-1, 3)
    return np.hypot(points[:, 0], points[:, 1]) * _NM, points[:, 2] * _NM


def structure_atoms(artefact: Artefact) -> tuple[np.ndarray, np.ndarray] | None:
    """Return the ensemble's atoms as ``(r, z)`` in m, thinned to a drawable count."""
    path = _payload(artefact, ENSEMBLE_PAYLOAD)
    if path is None:
        return None
    r, z = atoms_r_z_m(AlignedEnsemble.read(path).positions_nm)
    stride = max(1, r.size // MAX_ATOMS_DRAWN)
    return r[::stride], z[::stride]


# --- stages 2 and 3 --------------------------------------------------------------------------


def axial_section(
    values: np.ndarray, x_nm: np.ndarray, z_nm: np.ndarray, half_width: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return the ``y = 0`` section of a ``[z, y, x]`` map as ``(x, z, values[z, x])``, in m."""
    import numpy as np

    return x_nm * _NM, z_nm * _NM, np.asarray(values[:, half_width, :], dtype=np.float64)


def density_section(artefact: Artefact) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    """Return the density map's axial section, or None without its payload."""
    path = _payload(artefact, DENSITY_PAYLOAD)
    if path is None:
        return None
    density = DensityMap.read(path)
    grid = density.grid
    return axial_section(density.values, grid.axis_nm("x"), grid.axis_nm("z"), grid.half_width)


def reduced_map(artefact: Artefact) -> ReducedMap | None:
    """Return the stage-3 map (axes in nm, as stored), or None without its payload."""
    path = _payload(artefact, REDUCED_PAYLOAD)
    return None if path is None else ReducedMap.read(path)


# --- stages 4 and 5 --------------------------------------------------------------------------


def contour_polygon_m(artefact: Artefact) -> np.ndarray | None:
    """Return the conditioned contour as an ``(n, 2)`` array of ``(r, z)`` in m."""
    path = _payload(artefact, PROFILE_PAYLOAD)
    if path is None:
        return None
    return load_profile(path).as_array() * _NM


@dataclass(frozen=True)
class RegionDrawing:
    """Stage 5's named regions as outlines in m, in the model frame."""

    pore_m: np.ndarray
    membrane_m: np.ndarray
    exclusion_m: np.ndarray | None
    membrane_half_thickness_m: float
    reservoir_radius_m: float
    z_extent_m: tuple[float, float]
    record: RegionRecord | IdealisedRegionRecord


def region_drawing(artefact: Artefact) -> RegionDrawing | None:
    """Return the region record's outlines, or None without its payload."""
    path = _payload(artefact, REGION_PAYLOAD)
    if path is None:
        return None
    record = read_region(path)
    import numpy as np

    if isinstance(record, IdealisedRegionRecord):
        radius = record.pore.radius_nm
        half = 0.5 * record.membrane_thickness_nm
        outer = record.reservoir_radius_nm
        return RegionDrawing(
            pore_m=np.array([(0.0, -half), (radius, -half), (radius, half), (0.0, half)]) * _NM,
            membrane_m=np.array([(radius, -half), (outer, -half), (outer, half), (radius, half)])
            * _NM,
            exclusion_m=None,
            membrane_half_thickness_m=half * _NM,
            reservoir_radius_m=outer * _NM,
            z_extent_m=(-half * _NM, half * _NM),
            record=record,
        )
    exclusion = None if record.exclusion is None else record.exclusion.points() * _NM
    membrane = record.membrane
    half = membrane.half_thickness_nm
    # The face stage 5 meshes (geometry/region.py _membrane_face): from the inner chord out.
    outer = record.reservoir_radius_nm + half
    membrane_nm = np.array(
        [
            (membrane.inner_trans_nm, -half),
            (outer, -half),
            (outer, half),
            (membrane.inner_cis_nm, half),
        ]
    )
    return RegionDrawing(
        pore_m=record.points() * _NM,
        membrane_m=membrane_nm * _NM,
        exclusion_m=exclusion,
        membrane_half_thickness_m=record.membrane.half_thickness_nm * _NM,
        reservoir_radius_m=record.reservoir_radius_nm * _NM,
        z_extent_m=(record.axis_split_nm[0] * _NM, record.axis_split_nm[1] * _NM),
        record=record,
    )


# --- stage 6 ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class MeshElements:
    """A mesh's vertices in m, its triangles, and a size and a quality per element."""

    vertices_m: np.ndarray
    triangles: np.ndarray
    size_m: np.ndarray
    sicn: np.ndarray
    lumen_nm: tuple[float, float] = (5.0, 10.0)


def element_sizes_m(vertices_nm: np.ndarray, triangles: np.ndarray) -> np.ndarray:
    """Return each triangle's longest edge in m."""
    import numpy as np

    corners = vertices_nm[triangles]
    edges = np.stack(
        [
            np.linalg.norm(corners[:, 1] - corners[:, 0], axis=1),
            np.linalg.norm(corners[:, 2] - corners[:, 1], axis=1),
            np.linalg.norm(corners[:, 0] - corners[:, 2], axis=1),
        ]
    )
    return np.asarray(edges.max(axis=0) * _NM)


def mesh_elements(data: MeshData, quality: QualityReport | None = None) -> MeshElements:
    """Return the per-element size and SICN of ``data``; SICN from ``quality`` if given."""
    report = element_quality(data) if quality is None else quality
    extent = None
    if "wall" in data.boundaries:
        extent = lumen_extent_nm(data.vertices[data.edges_of("wall").ravel()])
    return MeshElements(
        vertices_m=data.vertices * _NM,
        triangles=data.triangles,
        size_m=element_sizes_m(data.vertices, data.triangles),
        sicn=report.sicn,
        lumen_nm=lumen_window_nm(extent),
    )


def mesh_of(artefact: Artefact, inputs: StageInputs | None) -> MeshElements | None:
    """Return the mesh a run solves on: deployed with inputs, else the stage-6 payload."""
    if inputs is not None:
        ingested = deployed_mesh(inputs.resolved, artefact)
        return mesh_elements(ingested.data, ingested.quality)
    path = _payload(artefact, MESH_PAYLOAD)
    return None if path is None else mesh_elements(read_mesh(path, format="msh41"))


# --- stage 7 ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class ProtonationCharges:
    """Each titratable residue's charge, mean over the frames, in e."""

    label: tuple[str, ...]
    charge_e: np.ndarray


def protonation_charges(artefact: Artefact) -> ProtonationCharges | None:
    """Return the residues' charges, or None without the table."""
    import numpy as np

    path = _payload(artefact, PROTONATION_PAYLOAD)
    if path is None:
        return None
    table = ProtonationTable.read(path)
    charge = np.asarray(table.residue_charge_e, dtype=np.float64)
    if charge.ndim == 2:
        charge = charge.mean(axis=0)
    labels = tuple(
        f"{name}{resid}{chain}"
        for name, resid, chain in zip(
            table.residue_name, table.residue_resid, table.residue_chain, strict=True
        )
    )
    return ProtonationCharges(labels, charge)


@dataclass(frozen=True)
class StoredGrid:
    """One stored stage-7 lattice: axes in m, ``values[z, r]`` as stored, and what they are."""

    r_m: np.ndarray
    z_m: np.ndarray
    values: np.ndarray
    quantity: str
    unit: str


def charge_grids(artefact: Artefact) -> dict[str, StoredGrid]:
    """Return the stored charge lattice and solid-fraction grid, each with its quantity."""
    found = {}
    lattice = stored_lattice(artefact)
    if lattice is not None:
        grid = lattice.grid
        found["charge"] = StoredGrid(
            grid.r_nm * _NM, grid.z_nm * _NM, grid.values, lattice.quantity, lattice.units
        )
    path = _payload(artefact, EPS_R_PAYLOAD)
    if path is not None:
        # The ``eps_r`` payload holds the solid fraction chi, not a permittivity
        # (charge/dielectric.py SOLID_FRACTION).
        grid = read_grid(path, format="npz")
        found["solid_fraction"] = StoredGrid(
            grid.r_nm * _NM, grid.z_nm * _NM, grid.values, "solid fraction χ", "1"
        )
    return found


# --- stage 8 ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class CorrectionCurves:
    """One correction against the declared driver and against the wall distance.

    Parameters
    ----------
    driver
        ``"average"`` or ``"ionic_strength"``: which quantity ``driver_M`` is.
    driver_M
        Driver values in mol/L; the factor is evaluated far from the wall.
    validity_M
        The fit's range in mol/L, which the figure shades.
    distance_m
        Distances to the nearest pore boundary, from 0.
    at_driver_M
        The driver value the distance curve is drawn at.
    """

    name: str
    model: str
    driver: str
    driver_M: np.ndarray
    factor_vs_driver: np.ndarray
    validity_M: tuple[float, float]
    distance_m: np.ndarray
    factor_vs_distance: np.ndarray
    at_driver_M: float

    @property
    def driver_label(self) -> str:
        """The x-axis name: ⟨c⟩ or I, from the declared driver."""
        return (
            "ionic strength I" if self.driver == "ionic_strength" else "average concentration ⟨c⟩"
        )


FAR_FROM_WALL_NM = 50.0
CURVE_POINTS = 120
DISTANCE_RANGE_NM = 3.0


def correction_curves(
    corrections: Mapping[str, CorrectionModel],
    *,
    driver: str,
    concentration_M: float,
    validity_M: tuple[float, float],
) -> list[CorrectionCurves]:
    """Return every non-trivial correction's curves, evaluated by the model itself."""
    import numpy as np

    curves = []
    for name, model in corrections.items():
        if model.name == "none":
            continue
        low, high = getattr(model, "validity_M", validity_M)
        # Past the fitted range the model clamps its driver, and the curve shows it going flat.
        x = np.linspace(0.0, 1.25 * high, CURVE_POINTS)
        d_nm = np.linspace(0.0, DISTANCE_RANGE_NM, CURVE_POINTS)
        curves.append(
            CorrectionCurves(
                name=name,
                model=model.name,
                driver=driver,
                driver_M=x,
                factor_vs_driver=np.asarray(model.evaluate(x, np.full_like(x, FAR_FROM_WALL_NM))),
                validity_M=(low, high),
                distance_m=d_nm * _NM,
                factor_vs_distance=np.asarray(
                    model.evaluate(np.full_like(d_nm, concentration_M), d_nm)
                ),
                at_driver_M=concentration_M,
            )
        )
    return curves


# --- stage 10 --------------------------------------------------------------------------------


@dataclass(frozen=True)
class NewtonRung:
    """One continuation rung's Newton steps."""

    name: str
    iteration: np.ndarray
    residual: np.ndarray
    update: np.ndarray
    damping: np.ndarray


def newton_history(artefact: Artefact) -> list[NewtonRung] | None:
    """Return the recorded rungs; None for a solve cached before the history was written."""
    import numpy as np

    path = _payload(artefact, NEWTON_HISTORY_KEY)
    if path is None:
        return None
    record = cast("dict[str, Any]", decode_floats(json.loads(path.read_text(encoding="utf-8"))))
    rungs = []
    for rung in record["rungs"]:
        steps = rung["steps"]
        rungs.append(
            NewtonRung(
                name=rung["name"],
                iteration=np.array([s["iteration"] for s in steps], dtype=np.int64),
                residual=np.array([s["residual"] for s in steps], dtype=np.float64),
                update=np.array([s["update"] for s in steps], dtype=np.float64),
                damping=np.array([s["damping"] for s in steps], dtype=np.float64),
            )
        )
    return rungs


QOI_UNITS: dict[str, str | None] = {
    "_m3_s": "flow",
    "_A": "current",
    "_S": "conductance",
    "_V": "potential",
    "_N": "force",
    "_nm": "length",
}
"""A quantity of interest's SI suffix and its :data:`DISPLAY` quantity; ``_nm`` stays as is."""


def _qoi_value(value: object, per: float) -> str | None:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, int | float):
        return f"{value * per:.4g}"
    if isinstance(value, list) and value and all(isinstance(item, int | float) for item in value):
        return " to ".join(f"{item * per:.4g}" for item in value)
    return None


def _split_unit(key: str) -> tuple[str, str]:
    suffix = next((end for end in QOI_UNITS if key.endswith(end)), "")
    return (key.removesuffix(suffix) if suffix else key).replace("_", " "), suffix


def qoi_rows(summary: Mapping[str, Any]) -> list[dict[str, str]]:
    """Return the quantities of interest as rows of ``quantity``, ``value`` and ``unit``.

    A key's SI suffix (:data:`QOI_UNITS`) sets the display unit; a mapping gives one row per
    entry, each entry taking its own suffix or, without one, its mapping's.
    """
    rows: list[dict[str, str]] = []

    def visit(label: str, suffix: str, value: object) -> None:
        if isinstance(value, Mapping):
            for key, inner in value.items():
                name, own = _split_unit(str(key))
                visit(f"{label} ({name})" if label else name, own or suffix, inner)
            return
        quantity = QOI_UNITS.get(suffix)
        display = DISPLAY[quantity] if quantity not in (None, "length") else None
        shown = _qoi_value(value, display.per_SI if display else 1.0)
        if shown is not None:
            unit = display.unit if display else ("nm" if suffix == "_nm" else "")
            rows.append({"quantity": label, "value": shown, "unit": unit})

    visit("", "", summary)
    return rows


def subdivided(cells: np.ndarray) -> np.ndarray:
    """Split each Triangle_6 cell into its four linear triangles, ``(n, 6)`` to ``(4n, 3)``."""
    import numpy as np

    a, b, c, ab, bc, ca = (cells[:, k] for k in range(6))
    return np.concatenate(
        [
            np.stack([a, ab, ca], axis=1),
            np.stack([ab, b, bc], axis=1),
            np.stack([ca, bc, c], axis=1),
            np.stack([ab, bc, ca], axis=1),
        ]
    )


FIELD_ALIASES: dict[str, tuple[str, int | None]] = {
    "potential": ("phi_V", None),
    "u_r": ("u_m_s", 0),
    "u_z": ("u_m_s", 1),
}
"""Quantity names a field panel takes beside the attribute keys, as ``(key, component)``."""

LUMEN_NM = (5.0, 10.0)
"""The ``(r, |z|)`` window of a close-up of the pore, in nm, where the mesh names no pore wall."""

_MOLAR_SUFFIX = "_mol_m3"

LUMEN_RADII = 2.5
LUMEN_VESTIBULE_RADII = 2.0


def lumen_window_nm(wall_extent_nm: tuple[float, float] | None) -> tuple[float, float]:
    """Return the ``(r, |z|)`` close-up of a pore from its lumen's largest ``r`` and wall's ``|z|``.

    The window reaches 2.5 lumen radii out and two lumen radii past the wall's ends, in nm;
    :data:`LUMEN_NM` where there is no wall.
    """
    if wall_extent_nm is None:
        return LUMEN_NM
    radius, half_length = wall_extent_nm
    return LUMEN_RADII * radius, half_length + LUMEN_VESTIBULE_RADII * radius


CUTLINE_POINTS = 400


def field_values(
    fields: SolutionFields, quantity: str
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return ``(points_m, cells, values)`` of one quantity, on the domain it is solved on.

    Parameters
    ----------
    quantity
        An attribute key of the fields (``phi_V``, ``c_Na_mol_m3``, ``p_Pa``), or
        ``"potential"``, ``"u_r"`` or ``"u_z"``.

    Raises
    ------
    KeyError
        No field of that name, or a vector named without its component.
    """
    import numpy as np

    key, component = FIELD_ALIASES.get(quantity, (quantity, None))
    for points, cells, values in (fields.whole, fields.fluid):
        if key not in values:
            continue
        found = np.asarray(values[key], dtype=np.float64)
        if component is not None:
            return points, cells, found[:, component]
        if found.ndim != 1:
            raise KeyError(f"{quantity!r} is a vector; name a component, 'u_r' or 'u_z'")
        return points, cells, found
    known = sorted({*fields.whole[2], *fields.fluid[2], *FIELD_ALIASES})
    raise KeyError(f"no field {quantity!r}; the run holds {', '.join(known)}")


_TRIANGULATIONS: list[tuple[np.ndarray, np.ndarray, Triangulation]] = []
_KEPT_TRIANGULATIONS = 4


def field_menu(fields: SolutionFields, *, radial: bool = True) -> dict[str, str]:
    """Return the fields the solve holds, by label, in the panels' quantity names.

    A model without flow offers neither velocity nor pressure.
    """
    held = {*fields.whole[2], *fields.fluid[2]}
    menu = {"potential φ": "potential"} if "phi_V" in held else {}
    concentrations = sorted(key for key in held if key.endswith(_MOLAR_SUFFIX))
    menu.update(
        {f"{key.removesuffix(_MOLAR_SUFFIX)} against the bulk": key for key in concentrations}
    )
    if "u_m_s" in held:
        menu["axial velocity u_z"] = "u_z"
        if radial:
            menu["radial velocity u_r"] = "u_r"
    if "p_Pa" in held:
        menu["pressure p"] = "p_Pa"
    return menu


def default_potential_range_mV(bias_mV: float) -> float:
    """Return the potential colour range to start from: twice the bias, at least 10 mV."""
    return max(10.0, 2.0 * abs(bias_mV))


def fields_lumen_nm(fields: SolutionFields) -> tuple[float, float]:
    """Return the ``(r, |z|)`` close-up of the pore that solved ``fields``, in nm."""
    return lumen_window_nm(fields.wall_extent_nm)


def field_triangulation(points_m: np.ndarray, cells: np.ndarray) -> Triangulation:
    """Return the mesh in nm as the four linear triangles of each P2 cell; the last few are kept.

    A cutline is exact at the P2 nodes only on this split. The arrays are matched by identity, so
    a figure and a slider that read the same fields build it once.
    """
    from matplotlib.tri import Triangulation

    for held_points, held_cells, held in _TRIANGULATIONS:
        if held_points is points_m and held_cells is cells:
            return held
    built = Triangulation(points_m[:, 0] / _NM, points_m[:, 1] / _NM, subdivided(cells))
    _TRIANGULATIONS.append((points_m, cells, built))
    del _TRIANGULATIONS[:-_KEPT_TRIANGULATIONS]
    return built


def sampled(
    fields: SolutionFields, quantity: str, r_nm: np.ndarray, z_nm: np.ndarray
) -> np.ndarray:
    """Return one field at the points ``(r_nm, z_nm)``, NaN outside the field's domain."""
    import numpy as np
    from matplotlib.tri import LinearTriInterpolator

    points, cells, values = field_values(fields, quantity)
    triangulation = field_triangulation(points, cells)
    found = LinearTriInterpolator(triangulation, values)(r_nm, z_nm)
    return np.ma.filled(np.ma.asarray(found, dtype=np.float64), np.nan)


def axial_cutline(
    fields: SolutionFields, quantity: str, *, r_nm: float = 0.0, z_nm: np.ndarray | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(z_nm, values)`` along the line ``r = r_nm``, NaN outside the field's domain.

    ``z_nm`` defaults to :data:`CUTLINE_POINTS` points over the field's axial extent.
    """
    import numpy as np

    if z_nm is None:
        points = field_values(fields, quantity)[0]
        z_nm = np.linspace(points[:, 1].min() / _NM, points[:, 1].max() / _NM, CUTLINE_POINTS)
    z = np.asarray(z_nm, dtype=np.float64)
    return z, sampled(fields, quantity, np.full_like(z, r_nm), z)


def radial_cutline(
    fields: SolutionFields, quantity: str, *, z_nm: float = 0.0, r_nm: np.ndarray | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """Return ``(r_nm, values)`` along the line ``z = z_nm``, NaN outside the field's domain.

    ``r_nm`` defaults to :data:`CUTLINE_POINTS` points from the axis to the field's outer edge.
    """
    import numpy as np

    if r_nm is None:
        points = field_values(fields, quantity)[0]
        r_nm = np.linspace(0.0, points[:, 0].max() / _NM, CUTLINE_POINTS)
    r = np.asarray(r_nm, dtype=np.float64)
    return r, sampled(fields, quantity, r, np.full_like(r, z_nm))


# --- sweep -----------------------------------------------------------------------------------


@dataclass(frozen=True)
class SweepCurves:
    """A sweep's scalar quantities against its swept axis, ordered by the axis value.

    Parameters
    ----------
    group
        Per point, the values of the sweep's other axes; one curve is drawn per group.
    index
        Per point, its index in the sweep's plan.
    """

    axis: str
    x: np.ndarray
    ok: np.ndarray
    quantities: dict[str, np.ndarray]
    group: tuple[str, ...] = ()
    index: tuple[int, ...] = ()


def _scalars(quantities: Mapping[str, Any]) -> dict[str, float]:
    return {
        key: float(value)
        for key, value in quantities.items()
        if isinstance(value, int | float) and not isinstance(value, bool)
    }


def _axis_value(row: Mapping[str, Any], axis: str) -> float:
    value = row["assignments"].get(axis, row["index"])
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(row["index"])


def sweep_curves(rows: Sequence[Mapping[str, Any]]) -> SweepCurves | None:
    """Return the curves of a sweep's rows, a point that is not ``ok`` kept and flagged."""
    import numpy as np

    if not rows:
        return None
    paths = sorted({path for row in rows for path in row["assignments"]})
    varying = [p for p in paths if len({str(row["assignments"].get(p)) for row in rows}) > 1]
    axis = varying[0] if varying else (paths[0] if paths else "index")
    # Another axis takes several values at one x; a path moved with the axis takes one.
    at_x: dict[str, dict[str, set[str]]] = {p: {} for p in varying[1:]}
    for row in rows:
        x_value = str(row["assignments"].get(axis))
        for p, seen in at_x.items():
            seen.setdefault(x_value, set()).add(str(row["assignments"].get(p)))
    others = [p for p, seen in at_x.items() if any(len(v) > 1 for v in seen.values())]

    def group_of(row: Mapping[str, Any]) -> str:
        return ", ".join(f"{p.rsplit('.', 1)[-1]}={row['assignments'].get(p)}" for p in others)

    ordered = sorted(rows, key=lambda row: (group_of(row), _axis_value(row, axis)))
    names = sorted({k for row in ordered for k in _scalars(row.get("quantities") or {})})
    series = {
        name: np.array(
            [_scalars(row.get("quantities") or {}).get(name, np.nan) for row in ordered],
            dtype=np.float64,
        )
        for name in names
    }
    return SweepCurves(
        axis=axis,
        x=np.array([_axis_value(row, axis) for row in ordered], dtype=np.float64),
        ok=np.array([row["status"] == "ok" for row in ordered], dtype=bool),
        quantities=series,
        group=tuple(group_of(row) for row in ordered),
        index=tuple(int(row["index"]) for row in ordered),
    )


def cis_referenced_bias_V(curves: SweepCurves) -> np.ndarray:
    """Return each point's bias as the current is reported against it, ``φ_trans - φ_cis``.

    A point that recorded no bias, as a failed one, takes its assigned bias, flipped where the
    recorded ones are the assigned ones' negatives (``ground: trans``). Where no point at a
    non-zero bias recorded one, the side of the ground is unknown and such a point is NaN.
    """
    import numpy as np

    recorded = curves.quantities.get("bias_V")
    if recorded is None:
        return curves.x
    both = np.isfinite(recorded) & (curves.x != 0.0)
    if not both.any():
        return np.where(np.isfinite(recorded), recorded, np.where(curves.x == 0.0, 0.0, np.nan))
    flipped = bool(np.median(recorded[both] / curves.x[both]) < 0.0)
    assigned = -curves.x if flipped else curves.x
    return np.where(np.isfinite(recorded), recorded, assigned)


def sweep_rows(artefact: Artefact) -> list[Mapping[str, Any]] | None:
    """Return the dataset rows of a sweep artefact, or None for another schema."""
    if artefact.schema != SWEEP_SCHEMA:
        return None
    rows = artefact.summary.get("rows")
    return list(rows) if isinstance(rows, list) else None
