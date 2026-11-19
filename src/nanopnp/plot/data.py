"""Arrays for every figure, read from stored artefacts in SI and the model frame; no drawing."""

from __future__ import annotations

import dataclasses
import json
import math
import threading
import weakref
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from nanopnp.charge.kernel import check_charged, check_spacing, source_atoms, volume_density
from nanopnp.charge.protonation import PAYLOAD_NAME as PROTONATION_PAYLOAD
from nanopnp.charge.protonation import ProtonationTable
from nanopnp.charge.stage import CHARGE_PAYLOAD, EPS_R_PAYLOAD, frame_shift_nm, stored_lattice
from nanopnp.core.hashing import decode_floats
from nanopnp.density.grid import read_grid
from nanopnp.density.map import PAYLOAD_NAME as DENSITY_PAYLOAD
from nanopnp.density.map import DensityMap
from nanopnp.density.radii import KERNEL_RADII, resolve_protonated_radii, resolve_radii
from nanopnp.geometry.outlines import Stage5Region
from nanopnp.geometry.profile import PAYLOAD_NAME as PROFILE_PAYLOAD
from nanopnp.geometry.profile import load_profile
from nanopnp.geometry.region import PAYLOAD_NAME as REGION_PAYLOAD
from nanopnp.geometry.region import read_region
from nanopnp.io.artefact import SWEEP_SCHEMA, Artefact, StageInputs
from nanopnp.materials.electrolyte import MOLAR_PER_SI
from nanopnp.mesh.adapter import MeshData
from nanopnp.mesh.adapter import read as read_mesh
from nanopnp.mesh.ingest import MESH_PAYLOAD, deployed_mesh
from nanopnp.mesh.quality import QualityReport, element_quality
from nanopnp.post.export import lumen_extent_nm
from nanopnp.solve.state import NEWTON_HISTORY_KEY
from nanopnp.structure.ensemble import PAYLOAD_NAME as ENSEMBLE_PAYLOAD
from nanopnp.structure.ensemble import AlignedEnsemble, EnsembleFormatError, chain_characters
from nanopnp.symmetry.reduce import PAYLOAD_NAME as REDUCED_PAYLOAD
from nanopnp.symmetry.reduce import ReducedMap

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np
    from matplotlib.tri import Triangulation

    from nanopnp.io.resolved import ResolvedCase
    from nanopnp.materials.electrolyte import Electrolyte
    from nanopnp.materials.models import CorrectionModel
    from nanopnp.post.export import SolutionFields

__all__ = [
    "CLIP_PERCENTILE",
    "CUTLINE_POINTS",
    "DISPLAY",
    "FIELD_ALIASES",
    "LUMEN_NM",
    "OVERLAY_LEVEL",
    "OVERLAY_SMOOTHING_NM",
    "OVERLAY_SPACING_NM",
    "QOI_UNITS",
    "SICN_FLOOR",
    "ChargeVolumes",
    "ColourScale",
    "CorrectionCurves",
    "Count",
    "DensityAtoms",
    "Display",
    "MeshElements",
    "Moved",
    "NewtonRung",
    "ProtonationCharges",
    "RegionDrawing",
    "ResidueAtoms",
    "ResidueCharges",
    "ResidueCopies",
    "StoredGrid",
    "SweepCurves",
    "atoms_r_z_m",
    "axial_cutline",
    "axial_section",
    "axis_label",
    "boundary_edges",
    "case_correction_curves",
    "case_curves",
    "chain_letters",
    "charge_grids",
    "charge_volumes",
    "cis_referenced_bias_V",
    "colour_scale",
    "contour_polygon_m",
    "correction_curves",
    "default_potential_range_mV",
    "density_section",
    "element_sizes_m",
    "field_menu",
    "field_values",
    "fields_lumen_nm",
    "inside_outline",
    "lumen_window_nm",
    "mesh_elements",
    "newton_history",
    "protonation_charges",
    "qoi_rows",
    "radial_cutline",
    "reduced_map",
    "region_drawing",
    "region_edges",
    "residue_key",
    "sampled",
    "structure_atoms",
    "subdivided",
    "sweep_curves",
    "table_letters",
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
    record: Stage5Region


def region_drawing(artefact: Artefact) -> RegionDrawing | None:
    """Return the region record's outlines, or None without its payload."""
    path = _payload(artefact, REGION_PAYLOAD)
    if path is None:
        return None
    record = read_region(path)
    outlines = record.outlines_nm()
    z_low, z_high = outlines.z_extent_nm
    return RegionDrawing(
        pore_m=outlines.pore_nm * _NM,
        membrane_m=outlines.membrane_nm * _NM,
        exclusion_m=None if outlines.exclusion_nm is None else outlines.exclusion_nm * _NM,
        membrane_half_thickness_m=outlines.membrane_half_thickness_nm * _NM,
        reservoir_radius_m=outlines.reservoir_radius_nm * _NM,
        z_extent_m=(z_low * _NM, z_high * _NM),
        record=record,
    )


REGION_EDGE_SAMPLES = 33
"""How many points a curved boundary of a region is drawn through."""


def region_edges(record: Stage5Region) -> dict[str, np.ndarray]:
    """Return each named boundary of a stage-5 region as ``(k, 2, 2)`` segments in nm.

    The boundaries are the region's own shape's, named as the mesher reads them, so they show
    before a mesh is built.
    """
    import numpy as np

    from nanopnp.geometry.pore import IdealisedRegionRecord
    from nanopnp.geometry.region import RegionRecord, build_region

    if isinstance(record, IdealisedRegionRecord):
        shape = record.geometry().shape(name_mouths=True)
    elif isinstance(record, RegionRecord):
        shape = build_region(record)
    else:
        raise TypeError(f"a region record of type {type(record).__name__} has no shape")
    found: dict[str, list[np.ndarray]] = {}
    for edge in shape.edges:
        if edge.name is None:
            continue
        low, high = edge.parameter_interval
        ends = np.array([[edge.start[0], edge.start[1]], [edge.end[0], edge.end[1]]])
        # A straight edge is its two ends; a curve, as the reservoir's arc, is sampled.
        straight = abs(float(edge.mass) - float(np.linalg.norm(ends[1] - ends[0]))) <= 1e-9 * max(
            float(edge.mass), 1.0
        )
        if straight:
            points = ends
        else:
            values = [edge.Value(t) for t in np.linspace(low, high, REGION_EDGE_SAMPLES)]
            points = np.array([[value[0], value[1]] for value in values])
        found.setdefault(str(edge.name), []).append(np.stack((points[:-1], points[1:]), axis=1))
    return {name: np.concatenate(parts) for name, parts in found.items()}


# --- stage 6 ---------------------------------------------------------------------------------


@dataclass(frozen=True)
class MeshElements:
    """A mesh's vertices in m, its triangles, and per element a size, two qualities and a material.

    Parameters
    ----------
    material
        Each triangle's index into ``materials``.
    """

    vertices_m: np.ndarray
    triangles: np.ndarray
    size_m: np.ndarray
    sicn: np.ndarray
    gamma: np.ndarray
    material: np.ndarray
    materials: tuple[str, ...]
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
    """Return the per-element size, quality and material of ``data``; quality from ``quality``."""
    report = element_quality(data) if quality is None else quality
    extent = None
    if "wall" in data.boundaries:
        extent = lumen_extent_nm(data.vertices[data.edges_of("wall").ravel()])
    return MeshElements(
        vertices_m=data.vertices * _NM,
        triangles=data.triangles,
        size_m=element_sizes_m(data.vertices, data.triangles),
        sicn=report.sicn,
        gamma=report.gamma,
        material=data.triangle_material,
        materials=data.materials,
        lumen_nm=lumen_window_nm(extent),
    )


def boundary_edges(data: MeshData) -> dict[str, np.ndarray]:
    """Return each boundary group's ``(k, 2, 2)`` segments in nm, by name."""
    return {name: data.vertices[data.edges_of(name)] for name in data.boundaries}


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


STRIP_MIN_CHARGE_E = 0.5
"""A residue is listed among the charged ones when its charge is at least this, in e."""

REACH_WIDTHS = 4.0
"""The distance, in smearing widths, beyond which an atom's density is not summed at a point."""


def chain_letters(chains: Iterable[str]) -> dict[str, str]:
    """Return the one PDB character each chain is written as, which Mol* reads back.

    Chains of one character keep it; where any key is longer (a segment id, ``PROA``), every chain
    takes ``A``, ``B``, … in order of first appearance, as the protonation stage writes its PQR.
    """
    ordered = list(dict.fromkeys(str(chain) for chain in chains))
    try:
        return chain_characters(ordered)
    except EnsembleFormatError:
        return {chain: chain.strip()[:1] or "A" for chain in ordered}


def table_letters(table: ProtonationTable) -> dict[str, str]:
    """Return the chain characters a protonation table's PQR was written with."""
    recorded = table.header.get("chains")
    if isinstance(recorded, Mapping):
        return {str(chain): str(letter) for chain, letter in recorded.items()}
    return chain_letters(table.chain.tolist())


def residue_key(chain: str, resid: int, icode: str) -> str:
    """Return the name a residue goes by on the molecule and on the map, ``<chain>:<resid><icode>``.

    The chain is its one PDB column (:func:`chain_letters`), which is all Mol* reads back; a blank
    chain is ``A``.
    """
    return f"{chain.strip()[:1] or 'A'}:{resid}{icode.strip()[:1]}"


class ResidueCopies:
    """Which residues are copies of one another: the chains at one position of the ring's units.

    Under Cn, n ≥ 2, stage 1 checked that the chains at one position of their units hold
    the same residue at a shared number, so a residue is named once, under its first unit's
    chain. Under C1, without stage 1, or where the header's units cannot be read so, each chain's
    residue stands alone.
    """

    def __init__(self, groups: Mapping[str, tuple[str, ...]] | None = None) -> None:
        self._members: dict[str, tuple[str, ...]] = dict(groups or {})
        self._group: dict[str, str] = {
            member: first for first, members in self._members.items() for member in members
        }

    @classmethod
    def of(
        cls, structure: Artefact | None, letters: Mapping[str, str] | None = None
    ) -> ResidueCopies:
        """Return the copies stage 1's header names, the chains named by ``letters``.

        Parameters
        ----------
        letters
            Each chain's PDB character; by default :func:`chain_letters` of the header's chains.
        """
        header = structure.summary if structure is not None else {}
        n, units = header.get("n"), header.get("chains_cyclic_order")
        if not (isinstance(n, int) and n >= 2 and isinstance(units, list) and len(units) == n):
            return cls()
        chains = [str(unit).split("+") for unit in units]
        if len({len(unit) for unit in chains}) != 1:
            return cls()
        if letters is None:
            listed = header.get("chains_file_order")
            letters = chain_letters(
                listed if isinstance(listed, list) else [c for unit in chains for c in unit]
            )
        named = [
            [letters.get(chain, chain.strip()[:1] or "A") for chain in unit] for unit in chains
        ]
        flat = [letter for unit in named for letter in unit]
        if len(set(flat)) != len(flat):
            return cls()
        return cls(
            {
                named[0][position]: tuple(unit[position] for unit in named)
                for position in range(len(named[0]))
            }
        )

    def group(self, key: str) -> str:
        """Return the key a residue is named by: its first unit's copy's."""
        chain, _, rest = key.partition(":")
        return f"{self._group.get(chain, chain)}:{rest}"

    def copies(self, key: str) -> tuple[str, ...]:
        """Return the keys of every copy of a residue, its first unit's first."""
        chain, _, rest = self.group(key).partition(":")
        return tuple(f"{member}:{rest}" for member in self._members.get(chain, (chain,)))


class ResidueCharges:
    """Each charged atom of a deposit, by residue: where it sits in (r, z) and what it carries.

    The atoms are the deposit's own, in the model frame, so a residue's markers fall where its
    charge is on the map, and a point on the map names the residues whose charge is there. A
    residue is named once with its copies (:class:`ResidueCopies`).
    """

    @classmethod
    def of(
        cls,
        protonation: Artefact,
        charge: Artefact,
        resolved: ResolvedCase,
        structure: Artefact | None = None,
    ) -> ResidueCharges | None:
        """Return the charges of a walk's stage-7 deposit, or None where it deposits none."""
        if CHARGE_PAYLOAD not in charge.payload or stored_lattice(charge) is None:
            return None
        table = ProtonationTable.read(Path(protonation.payload[PROTONATION_PAYLOAD]))
        return cls(table, resolved, ResidueCopies.of(structure, table_letters(table)))

    def __init__(
        self,
        table: ProtonationTable,
        resolved: ResolvedCase,
        copies: ResidueCopies | None = None,
    ) -> None:
        import numpy as np

        atoms = source_atoms(
            table,
            sharpness=resolved.smearing.sharpness,
            shift_z_nm=frame_shift_nm(resolved),
        )
        self._r, self._z = atoms.r_nm, atoms.z_nm
        self._width, self._weight = atoms.width_nm, atoms.weight_e
        self._copies = copies if copies is not None else ResidueCopies()
        # Every charged atom of every frame (an ensemble is tens of frames of tens of thousands of
        # atoms), keyed through plain lists and grouped in one pass in order of first appearance,
        # which the list's order follows.
        letters = table_letters(table)
        chain, resid, icode = table.chain.tolist(), table.resid.tolist(), table.icode.tolist()
        resname = table.resname.tolist()
        rows = atoms.atom.tolist()
        own = [residue_key(letters[str(chain[i])], int(resid[i]), str(icode[i])) for i in rows]
        self._keys: list[str] = [self._copies.group(key) for key in own]
        self._names = [str(resname[i]).strip() for i in rows]
        grouped: dict[str, list[int]] = {}
        present: dict[str, dict[str, None]] = {}
        for position, key in enumerate(self._keys):
            grouped.setdefault(key, []).append(position)
            present.setdefault(key, {})[own[position]] = None
        self._rows: dict[str, np.ndarray] = {
            key: np.array(found, dtype=np.intp) for key, found in grouped.items()
        }
        self._present: dict[str, tuple[str, ...]] = {
            key: tuple(member for member in self._copies.copies(key) if member in present[key])
            or tuple(present[key])
            for key in grouped
        }

    def __contains__(self, key: object) -> bool:
        """Say whether a residue key names a residue, or a copy of one, that carries charge."""
        return isinstance(key, str) and self._copies.group(key) in self._rows

    def group(self, key: str) -> str:
        """Return the key a residue is listed by, its copies together."""
        return self._copies.group(key)

    def copies(self, key: str) -> tuple[str, ...]:
        """Return the keys of a residue's copies that carry charge, its first unit's first."""
        return self._present.get(self._copies.group(key), ())

    def residues(self) -> list[tuple[str, str, float, int]]:
        """Return ``(key, name, charge_e, copies)`` of each strongly charged residue, named once.

        ``charge_e`` is one copy's: the residue's atoms of every frame and every copy, summed and
        divided by its copies.
        """
        found = []
        for key, rows in self._rows.items():
            count = len(self._present[key])
            charge = float(self._weight[rows].sum()) / count
            if abs(charge) >= STRIP_MIN_CHARGE_E:
                found.append((key, self._names[int(rows[0])], charge, count))
        return found

    def markers(self, key: str) -> list[tuple[float, float, float]]:
        """Return the ``(r_nm, z_nm, q_e)`` of each charged atom of a residue, every copy's."""
        return [
            (float(self._r[i]), float(self._z[i]), float(self._weight[i]))
            for i in self._rows[self._copies.group(key)]
        ]

    def at(self, r_nm: float, z_nm: float, n: int = 5) -> list[tuple[str, float]]:
        """Return the ``n`` residues adding most charge density at a point, as ``(key, e/nm^3)``.

        A residue's density is its copies' sum.
        """
        import numpy as np

        reach = REACH_WIDTHS * self._width
        near = np.flatnonzero((np.abs(self._z - z_nm) < reach) & (np.abs(self._r - r_nm) < reach))
        totals: dict[str, float] = {}
        for i in near:
            density = float(
                volume_density(
                    np.array(r_nm), np.array(z_nm), self._r[i], self._z[i], self._width[i]
                )
            )
            key = self._keys[i]
            totals[key] = totals.get(key, 0.0) + float(self._weight[i]) * density
        return sorted(totals.items(), key=lambda item: -abs(item[1]))[:n]


def inside_outline(loop: np.ndarray, r_nm: np.ndarray, z_nm: np.ndarray) -> np.ndarray:
    """Return whether each point ``(r_nm[i], z_nm[i])`` lies inside a closed ``(n, 2)`` loop.

    The even-odd rule, an edge counted where ``z0 <= z < z1`` and it crosses below ``r``, as the
    solid fraction's own test: a point on an edge facing larger ``r``, or on a lower edge, is
    inside.
    """
    import numpy as np

    points = np.asarray(loop, dtype=np.float64)
    r = np.asarray(r_nm, dtype=np.float64)
    z = np.asarray(z_nm, dtype=np.float64)
    inside = np.zeros(r.shape, dtype=bool)
    for start, end in zip(points, np.roll(points, -1, axis=0), strict=True):
        low, high = min(start[1], end[1]), max(start[1], end[1])
        crossing = (low <= z) & (z < high)
        if not bool(crossing.any()):
            continue
        at = start[0] + (z[crossing] - start[1]) * (end[0] - start[0]) / (end[1] - start[1])
        inside[crossing] ^= at < r[crossing]
    return inside


@dataclass(frozen=True)
class Count:
    """A residue's atoms an edit moves and their charge, each per copy and per frame."""

    atoms: float
    charge_e: float


@dataclass(frozen=True)
class Moved:
    """The residues whose atoms an edit moves, each way, keyed as :class:`ResidueCopies` names them.

    Parameters
    ----------
    out
        Atoms inside the outline the edit started from and outside the edit: into the water.
    in_
        Atoms outside the outline the edit started from and inside the edit: into the protein.
    """

    out: dict[str, Count]
    in_: dict[str, Count]


class ResidueAtoms:
    """Every atom of the protonation table, every frame, in stage 1's frame reduced to (r, z).

    The outlines, built or supplied, are in stage 1's frame, so an atom's side of an outline is
    read without the model frame's shift.
    """

    @classmethod
    def of(cls, protonation: Artefact, structure: Artefact | None = None) -> ResidueAtoms:
        """Return the atoms of a protonation artefact, named with stage 1's copies."""
        table = ProtonationTable.read(Path(protonation.payload[PROTONATION_PAYLOAD]))
        return cls(table, ResidueCopies.of(structure, table_letters(table)))

    def __init__(self, table: ProtonationTable, copies: ResidueCopies | None = None) -> None:
        import numpy as np

        positions = np.asarray(table.positions_nm, dtype=np.float64)
        self._r = np.hypot(positions[:, 0], positions[:, 1])
        self._z = positions[:, 2].copy()
        self._charge = np.asarray(table.charge_e, dtype=np.float64)
        self._frames = table.frames
        self._copies = copies if copies is not None else ResidueCopies()
        letters = table_letters(table)
        chain, resid, icode = table.chain.tolist(), table.resid.tolist(), table.icode.tolist()
        own = [
            residue_key(letters[str(c)], int(r), str(i))
            for c, r, i in zip(chain, resid, icode, strict=True)
        ]
        keys = [self._copies.group(key) for key in own]
        index = {key: number for number, key in enumerate(dict.fromkeys(keys))}
        self._keys = list(index)
        self._key_of = np.array([index[key] for key in keys], dtype=np.intp)
        present: dict[str, dict[str, None]] = {}
        self._names: dict[str, str] = {}
        for key, member, name in zip(keys, own, table.resname.tolist(), strict=True):
            present.setdefault(key, {})[member] = None
            self._names.setdefault(key, str(name).strip())
        self._present = {key: tuple(members) for key, members in present.items()}
        self._count = np.array([len(present[key]) for key in self._keys], dtype=np.float64)

    @property
    def r_nm(self) -> np.ndarray:
        """Return every atom's distance from the axis, in nm."""
        return self._r

    def group(self, key: str) -> str:
        """Return the key a residue is named by, its copies together."""
        return self._copies.group(key)

    def copies(self, key: str) -> tuple[str, ...]:
        """Return the keys of a residue's copies the table holds, its first unit's first."""
        return self._present.get(self._copies.group(key), ())

    def name(self, key: str) -> str:
        """Return a residue's name as the table writes it, or empty where it holds none."""
        return self._names.get(self._copies.group(key), "")

    @property
    def z_nm(self) -> np.ndarray:
        """Return every atom's height in stage 1's frame, in nm."""
        return self._z

    def moved(self, before: np.ndarray, after: np.ndarray) -> Moved:
        """Return the residues whose atoms ``after`` puts across ``before``, each way."""
        import numpy as np

        was = inside_outline(before, self._r, self._z)
        now = inside_outline(after, self._r, self._z)
        found = []
        for mask in (was & ~now, ~was & now):
            atoms = np.bincount(self._key_of[mask], minlength=len(self._keys)).astype(np.float64)
            charge = np.bincount(
                self._key_of[mask], weights=self._charge[mask], minlength=len(self._keys)
            )
            scale = self._frames * self._count
            found.append(
                {
                    self._keys[k]: Count(float(atoms[k] / scale[k]), float(charge[k] / scale[k]))
                    for k in np.flatnonzero(atoms)
                }
            )
        return Moved(found[0], found[1])

    def markers(self, key: str) -> list[tuple[float, float, float]]:
        """Return the ``(r_nm, z_nm, q_e)`` of a residue's atoms, every copy's and frame's."""
        import numpy as np

        group = self._copies.group(key)
        if group not in self._keys:
            return []
        rows = np.flatnonzero(self._key_of == self._keys.index(group))
        return [(float(self._r[i]), float(self._z[i]), float(self._charge[i])) for i in rows]


class DensityAtoms:
    """Stage 2's atoms and kernel widths, as the density stage smears them, by residue."""

    @classmethod
    def of(
        cls,
        resolved: ResolvedCase,
        structure: Artefact,
        protonation: Artefact | None = None,
    ) -> DensityAtoms:
        """Return the atoms ``geometry.density.atoms`` names: the protonation table's, or stage 1's.

        Raises
        ------
        ValueError
            If the case carries no density block, or names the protonated atoms without a table.
        """
        import numpy as np

        spec = resolved.density
        if spec is None:
            raise ValueError(f"case {resolved.name!r} carries no density block")
        if spec.atoms == "protonated":
            if protonation is None:
                raise ValueError("the density smears the protonated atoms, and none are built")
            table = ProtonationTable.read(Path(protonation.payload[PROTONATION_PAYLOAD]))
            letters = table_letters(table)
            radii = resolve_protonated_radii(KERNEL_RADII[spec.kernel], table).radii_nm
            positions = np.asarray(table.positions_nm, dtype=np.float64)
            chain, resid, icode = table.chain, table.resid, table.icode
        else:
            ensemble = AlignedEnsemble.read(structure.payload[ENSEMBLE_PAYLOAD])
            letters = chain_letters(ensemble.chain.tolist())
            radii = resolve_radii(
                KERNEL_RADII[spec.kernel],
                resname=ensemble.resname,
                atom=ensemble.name,
                chain=ensemble.chain,
                resid=ensemble.resid,
                icode=ensemble.icode,
            ).radii_nm
            frames = ensemble.frames
            positions = np.asarray(ensemble.positions_nm, dtype=np.float64).reshape(-1, 3)
            radii = np.tile(np.asarray(radii, dtype=np.float64), frames)
            chain, resid, icode = (
                np.tile(column, frames)
                for column in (ensemble.chain, ensemble.resid, ensemble.icode)
            )
        copies = ResidueCopies.of(structure, letters)
        keys = [
            copies.group(residue_key(letters[str(c)], int(r), str(i)))
            for c, r, i in zip(chain.tolist(), resid.tolist(), icode.tolist(), strict=True)
        ]
        return cls(
            np.hypot(positions[:, 0], positions[:, 1]),
            positions[:, 2],
            spec.sharpness * np.asarray(radii, dtype=np.float64),
            keys,
        )

    def __init__(
        self, r_nm: np.ndarray, z_nm: np.ndarray, width_nm: np.ndarray, keys: Sequence[str]
    ) -> None:
        import numpy as np

        self._r, self._z, self._width = r_nm, z_nm, width_nm
        index = {key: number for number, key in enumerate(dict.fromkeys(keys))}
        self._keys = list(index)
        self._key_of = np.array([index[key] for key in keys], dtype=np.intp)

    @property
    def width_nm(self) -> np.ndarray:
        """Return every atom's kernel width, in nm, in the order stage 2 deposits them."""
        return self._width

    def nearest(self, r_nm: float, z_nm: float, n: int = 5) -> list[tuple[str, float]]:
        """Return the ``n`` residues nearest a point, as ``(key, distance in kernel widths)``.

        Stage 2's density is a union of its atoms, not a sum, so a point is named by the atoms
        whose kernel reaches it first: each residue's least ``|(r, z) - (r_i, z_i)| / w_i``.
        """
        import numpy as np

        scaled = np.hypot(self._r - r_nm, self._z - z_nm) / self._width
        least = np.full(len(self._keys), np.inf)
        np.minimum.at(least, self._key_of, scaled)
        order = np.argsort(least, kind="stable")[:n]
        return [(self._keys[k], float(least[k])) for k in order if np.isfinite(least[k])]


CLIP_PERCENTILE = 99.0
"""The share of a charge's size, in percent, its colour scale opens on (WB-49): a few atoms near
the axis set the largest value, so a scale to it leaves the bulk of a map at its middle colour."""


@dataclass(frozen=True)
class ColourScale:
    """A charge's colour scale each side of zero: its largest size, and the size it opens on."""

    largest: float
    clip: float


def colour_scale(values: np.ndarray) -> ColourScale:
    """Return the colour scale of a charge's values: the :data:`CLIP_PERCENTILE` of its size.

    The percentile is of the values that are not zero, so the space no charge reaches does not
    pull it down; a charge with none opens on 0.
    """
    import numpy as np

    sizes = np.abs(np.asarray(values, dtype=np.float64))
    sizes = sizes[np.isfinite(sizes)]
    carried = sizes[sizes > 0.0]
    if not carried.size:
        return ColourScale(0.0, 0.0)
    return ColourScale(float(carried.max()), float(np.percentile(carried, CLIP_PERCENTILE)))


OVERLAY_SPACING_NM = 0.2
"""The overlay's grid spacing, in nm (§8.2.44 AT4)."""

OVERLAY_SMOOTHING_NM = 0.4
"""The least kernel width the overlay spreads an atom's charge over, in nm (§8.2.44 AT4)."""

OVERLAY_LEVEL = 0.1
"""The fraction of a volume's largest magnitude its isosurfaces are first drawn at."""


class ChargeVolumes:
    """The deposit's charge density on one 3D grid, and its mean about the axis, in e/nm^3.

    Both are indexed ``[ix, iy, iz]`` in stage 1's frame from ``origin_nm`` at ``spacing_nm``.
    Each atom's charge is spread over a Gaussian of width at least ``smoothing_nm``, so the grid
    resolves it; ``revolved`` is the closed-form mean about the axis of the same Gaussians, so it
    is the mean of ``full`` over the azimuth but for each Gaussian's cut-off at
    :data:`REACH_WIDTHS` widths, where it is 1.1 x 10^-7 of its peak.
    """

    def __init__(
        self,
        origin_nm: tuple[float, float, float],
        spacing_nm: float,
        smoothing_nm: float,
        full: np.ndarray,
        revolved: np.ndarray,
        atoms: tuple[np.ndarray, np.ndarray, np.ndarray],
    ) -> None:
        self.origin_nm = origin_nm
        self.spacing_nm = spacing_nm
        self.smoothing_nm = smoothing_nm
        self.full = full
        self.revolved = revolved
        self._positions, self._width, self._weight = atoms

    def peak(self, which: str) -> float:
        """Return the largest magnitude of ``full`` or ``revolved``, in e/nm^3."""
        return float(abs(self.full if which == "full" else self.revolved).max())

    def level(self, which: str) -> float:
        """Return the level a volume's isosurfaces are first drawn at, in e/nm^3."""
        return OVERLAY_LEVEL * self.peak(which)

    def axes_nm(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return the grid's x, y and z, in nm."""
        import numpy as np

        return cast(
            "tuple[np.ndarray, np.ndarray, np.ndarray]",
            tuple(
                self.origin_nm[axis] + self.spacing_nm * np.arange(self.full.shape[axis])
                for axis in range(3)
            ),
        )

    def full_at(self, points_nm: np.ndarray) -> np.ndarray:
        """Return the 3D charge density at ``(k, 3)`` points in stage 1's frame, in e/nm^3."""
        import numpy as np

        points = np.asarray(points_nm, dtype=np.float64).reshape(-1, 3)
        found = np.zeros(len(points))
        for i in range(len(self._weight)):
            width = float(self._width[i])
            squared = np.sum((points - self._positions[i]) ** 2, axis=1) / width**2
            near = squared <= REACH_WIDTHS**2
            found[near] += (
                float(self._weight[i]) * math.pi**-1.5 * width**-3 * np.exp(-squared[near])
            )
        return found


def charge_volumes(
    table: ProtonationTable,
    resolved: ResolvedCase,
    spacing_nm: float = OVERLAY_SPACING_NM,
    smoothing_nm: float = OVERLAY_SMOOTHING_NM,
) -> ChargeVolumes:
    """Return the deposit's charge in 3D and its mean about the axis, smoothed for the picture.

    Each charged atom of every frame carries ``q / frames``, as stage 7 deposits it, spread over a
    Gaussian of width ``max(w_i, smoothing_nm)``, ``w_i`` stage 7's own, and summed within
    :data:`REACH_WIDTHS` widths; the box spans every charged atom by as many widths.

    Raises
    ------
    ChargeFieldError
        If the table holds no charged atom, or the spacing exceeds half the narrowest width.
    """
    import numpy as np
    from scipy.special import i0e

    source = source_atoms(table, sharpness=resolved.smearing.sharpness)
    check_charged(source)
    width = np.maximum(source.width_nm, smoothing_nm)
    check_spacing(dataclasses.replace(source, width_nm=width), spacing_nm)
    positions = np.asarray(table.positions_nm, dtype=np.float64)[source.atom]
    weight = source.weight_e
    reach = REACH_WIDTHS * width
    # The grid is symmetric about the axis, so its columns share their distances from it.
    half = float(np.max(np.hypot(positions[:, 0], positions[:, 1]) + reach))
    across = math.ceil(half / spacing_nm)
    low_z = float(np.min(positions[:, 2] - reach))
    high_z = float(np.max(positions[:, 2] + reach))
    along = math.ceil((high_z - low_z) / spacing_nm) + 1
    origin = (-across * spacing_nm, -across * spacing_nm, low_z)
    shape = (2 * across + 1, 2 * across + 1, along)
    x = origin[0] + spacing_nm * np.arange(shape[0])
    z = origin[2] + spacing_nm * np.arange(shape[2])

    full = np.zeros(shape)
    y = x
    for i in range(len(weight)):
        # Each atom's Gaussian is the product of one per axis, added over the cube of its reach
        # with the points beyond the reach left out.
        w, limit = float(width[i]), float(reach[i])
        window = []
        for axis, values in enumerate((x, y, z)):
            first = max(0, math.floor((positions[i, axis] - limit - origin[axis]) / spacing_nm))
            last = min(
                shape[axis], math.ceil((positions[i, axis] + limit - origin[axis]) / spacing_nm) + 1
            )
            window.append((first, last, (values[first:last] - positions[i, axis]) ** 2))
        (x0, x1, dx), (y0, y1, dy), (z0, z1, dz) = window
        squared = dx[:, None, None] + dy[None, :, None] + dz[None, None, :]
        factor = float(weight[i]) * math.pi**-1.5 * w**-3
        gaussian = np.multiply.outer(
            np.multiply.outer(factor * np.exp(-dx / w**2), np.exp(-dy / w**2)), np.exp(-dz / w**2)
        )
        full[x0:x1, y0:y1, z0:z1] += np.where(squared <= limit**2, gaussian, 0.0)

    # The mean about the axis depends on (r, z) alone: summed once per distinct column radius.
    columns = np.hypot(x[:, None], x[None, :]).ravel()
    radii, column_radius = np.unique(columns, return_inverse=True)
    source_r = np.hypot(positions[:, 0], positions[:, 1])
    plane = np.zeros((len(radii), shape[2]))
    for i in range(len(weight)):
        w, r_i, z_i, limit = (
            float(width[i]),
            float(source_r[i]),
            float(positions[i, 2]),
            float(reach[i]),
        )
        r0, r1 = np.searchsorted(radii, [r_i - limit, r_i + limit], side="left")
        z0 = max(0, math.floor((z_i - limit - origin[2]) / spacing_nm))
        z1 = min(shape[2], math.ceil((z_i + limit - origin[2]) / spacing_nm) + 1)
        r_near, z_near = radii[r0:r1], z[z0:z1]
        if r_near.size == 0 or z_near.size == 0:
            continue
        dr, dz = (r_near - r_i) ** 2, (z_near - z_i) ** 2
        # volume_density, its radial and axial factors apart.
        radial = (
            float(weight[i])
            * math.pi**-1.5
            * w**-3
            * np.exp(-dr / w**2)
            * i0e(2.0 * r_near * r_i / w**2)
        )
        values = np.multiply.outer(radial, np.exp(-dz / w**2))
        plane[r0:r1, z0:z1] += np.where(dr[:, None] + dz[None, :] <= limit**2, values, 0.0)
    revolved = plane[column_radius].reshape(shape)
    return ChargeVolumes(
        origin_nm=origin,
        spacing_nm=spacing_nm,
        smoothing_nm=smoothing_nm,
        full=full.reshape(shape),
        revolved=revolved,
        atoms=(positions, width, weight),
    )


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
        # Even steps in the square root of the driver, as the corrections go with it.
        x = 1.25 * high * np.linspace(0.0, 1.0, CURVE_POINTS) ** 2
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


def case_correction_curves(resolved: ResolvedCase) -> list[CorrectionCurves]:
    """Return a resolved case's correction curves, drawn at the driver its bulk forms."""
    return case_curves(resolved.electrolyte, resolved.concentration_M)


def case_curves(electrolyte: Electrolyte, concentration_M: float) -> list[CorrectionCurves]:
    """Return an electrolyte's correction curves, drawn at the driver a bulk salt forms."""
    # Every species sits at the concentration in the bulk; the driver is formed from them as
    # the solve forms it: <c> = (1/n) sum c_i, or I, clamped to the fitted range.
    bulk_SI = concentration_M / MOLAR_PER_SI
    driver_M = float(electrolyte.average_concentration([bulk_SI] * len(electrolyte.species)))
    return correction_curves(
        electrolyte.corrections,
        driver=electrolyte.driver,
        concentration_M=driver_M,
        validity_M=electrolyte.validity_M,
    )


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


_TRIANGULATIONS: list[
    tuple[weakref.ReferenceType[np.ndarray], weakref.ReferenceType[np.ndarray], Triangulation]
] = []
_TRIANGULATION_LOCK = threading.Lock()
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
    a figure and a slider that read the same fields build it once. An entry never keeps its arrays
    alive: it is dropped when either is collected.
    """
    from matplotlib.tri import Triangulation

    with _TRIANGULATION_LOCK:
        _TRIANGULATIONS[:] = [
            entry for entry in _TRIANGULATIONS if entry[0]() is not None and entry[1]() is not None
        ]
        for held_points, held_cells, held in _TRIANGULATIONS:
            if held_points() is points_m and held_cells() is cells:
                return held
    built = Triangulation(points_m[:, 0] / _NM, points_m[:, 1] / _NM, subdivided(cells))
    with _TRIANGULATION_LOCK:
        _TRIANGULATIONS.append((weakref.ref(points_m), weakref.ref(cells), built))
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
