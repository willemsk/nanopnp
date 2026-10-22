"""Arrays for every figure, read from stored artefacts in SI and the model frame; no Matplotlib."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from nanopnp.charge.protonation import PAYLOAD_NAME as PROTONATION_PAYLOAD
from nanopnp.charge.protonation import ProtonationTable
from nanopnp.charge.stage import CHARGE_PAYLOAD, EPS_R_PAYLOAD
from nanopnp.core.hashing import decode_floats
from nanopnp.density.grid import read_grid
from nanopnp.density.map import PAYLOAD_NAME as DENSITY_PAYLOAD
from nanopnp.density.map import DensityMap
from nanopnp.geometry.profile import load_profile
from nanopnp.geometry.region import PAYLOAD_NAME as REGION_PAYLOAD
from nanopnp.geometry.region import RegionRecord, read_region
from nanopnp.io.artefact import SWEEP_SCHEMA, Artefact, StageInputs
from nanopnp.mesh.adapter import MeshData
from nanopnp.mesh.adapter import read as read_mesh
from nanopnp.mesh.ingest import MESH_PAYLOAD, deployed_mesh
from nanopnp.mesh.quality import QualityReport, element_quality
from nanopnp.post.export import restored, sampled_fields
from nanopnp.solve.state import NEWTON_HISTORY_KEY
from nanopnp.structure.ensemble import PAYLOAD_NAME as ENSEMBLE_PAYLOAD
from nanopnp.structure.ensemble import AlignedEnsemble
from nanopnp.symmetry.reduce import PAYLOAD_NAME as REDUCED_PAYLOAD
from nanopnp.symmetry.reduce import ReducedMap

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

    from nanopnp.materials.models import CorrectionModel

__all__ = [
    "DISPLAY",
    "SICN_FLOOR",
    "CorrectionCurves",
    "Display",
    "MeshElements",
    "NewtonRung",
    "ProtonationCharges",
    "RegionDrawing",
    "SolutionFields",
    "SweepCurves",
    "atoms_r_z_m",
    "axial_section",
    "axis_label",
    "charge_grids",
    "contour_polygon_m",
    "correction_curves",
    "density_section",
    "element_sizes_m",
    "mesh_elements",
    "newton_history",
    "protonation_charges",
    "reduced_map",
    "region_drawing",
    "solution_fields",
    "structure_atoms",
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
    "potential": Display("V", 1.0),
    "velocity": Display("µm/s", 1e6),
    "pressure": Display("Pa", 1.0),
    "charge_density": Display("C/m³", 1.0),
    "density": Display("1", 1.0),
    "current": Display("nA", 1e9),
    "flow": Display("µm³/s", 1e18),
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
    # Imported here: the contour module needs the structure extra, and a figure of the other
    # stages must not.
    from nanopnp.geometry.contour import PAYLOAD_NAME as PROFILE_PAYLOAD

    path = _payload(artefact, PROFILE_PAYLOAD)
    if path is None:
        return None
    return load_profile(path).as_array() * _NM


@dataclass(frozen=True)
class RegionDrawing:
    """Stage 5's named regions as outlines in m, in the model frame."""

    pore_m: np.ndarray
    exclusion_m: np.ndarray | None
    membrane_half_thickness_m: float
    reservoir_radius_m: float
    z_extent_m: tuple[float, float]
    record: RegionRecord


def region_drawing(artefact: Artefact) -> RegionDrawing | None:
    """Return the region record's outlines, or None without its payload."""
    path = _payload(artefact, REGION_PAYLOAD)
    if path is None:
        return None
    record = read_region(path)
    exclusion = None if record.exclusion is None else record.exclusion.points() * _NM
    return RegionDrawing(
        pore_m=record.points() * _NM,
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
    return MeshElements(
        vertices_m=data.vertices * _NM,
        triangles=data.triangles,
        size_m=element_sizes_m(data.vertices, data.triangles),
        sicn=report.sicn,
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


def charge_grids(artefact: Artefact) -> dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Return the stored charge and ε_r grids as ``{name: (r, z, values[z, r])}``, axes in m."""
    found = {}
    for key in (CHARGE_PAYLOAD, EPS_R_PAYLOAD):
        path = _payload(artefact, key)
        if path is not None:
            grid = read_grid(path, format="npz")
            found[key] = (grid.r_nm * _NM, grid.z_nm * _NM, grid.values)
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


@dataclass(frozen=True)
class SolutionFields:
    """The solved fields in SI on the P2 nodes of the whole domain and of the fluid.

    Parameters
    ----------
    whole, fluid
        ``(points_m, corner triangles, fields)``; a vector field is ``(n, 2)`` in ``(r, z)``.
    """

    model: str
    whole: tuple[np.ndarray, np.ndarray, dict[str, np.ndarray]]
    fluid: tuple[np.ndarray, np.ndarray, dict[str, np.ndarray]]


def solution_fields(inputs: StageInputs, artefact: Artefact) -> SolutionFields:
    """Restore the converged state and sample its fields through the export's own path."""
    state, _ = restored(inputs, artefact)
    sampled = sampled_fields(state, state.model.scales)
    return SolutionFields(
        model=state.model.name,
        whole=(sampled.omega.points_nm * _NM, sampled.omega.cells[:, :3], sampled.whole),
        fluid=(sampled.omega_w.points_nm * _NM, sampled.omega_w.cells[:, :3], sampled.restricted),
    )


# --- sweep -----------------------------------------------------------------------------------


@dataclass(frozen=True)
class SweepCurves:
    """A sweep's scalar quantities against its swept axis, ordered by the axis value."""

    axis: str
    x: np.ndarray
    ok: np.ndarray
    quantities: dict[str, np.ndarray]


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
    ordered = sorted(rows, key=lambda row: _axis_value(row, axis))
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
    )


def sweep_rows(artefact: Artefact) -> list[Mapping[str, Any]] | None:
    """Return the dataset rows of a sweep artefact, or None for another schema."""
    if artefact.schema != SWEEP_SCHEMA:
        return None
    rows = artefact.summary.get("rows")
    return list(rows) if isinstance(rows, list) else None
