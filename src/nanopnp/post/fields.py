"""A run's fields at points and on a grid, and two runs' difference over their fluids' overlap."""

from __future__ import annotations

import math
import threading
import weakref
from dataclasses import dataclass
from typing import TYPE_CHECKING

from nanopnp.charge.deposit import locate_points

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

    from nanopnp.post.export import SolutionFields

__all__ = [
    "FIELD_ALIASES",
    "GRID_CELLS",
    "LOCATE_BUCKETS",
    "FieldDifference",
    "FieldSplit",
    "field_at",
    "field_difference",
    "field_grid",
    "field_split",
    "field_unit",
    "field_values",
    "joint_range",
    "quantity_name",
    "subdivided",
]

GRID_CELLS = 1_000_000
"""The number of cells a grid over a field's box aims at."""

FIELD_ALIASES: dict[str, tuple[str, int | None]] = {
    "potential": ("phi_V", None),
    "u_r": ("u_m_s", 0),
    "u_z": ("u_m_s", 1),
}
"""Quantity names a field panel takes beside the attribute keys, as ``(key, component)``."""

_UNITS: tuple[tuple[str, str], ...] = (
    ("_mol_m3", "mol/m³"),
    ("_C_m3", "C/m³"),
    ("_m_s", "m/s"),
    ("_Pa", "Pa"),
    ("_nm", "nm"),
    ("_V", "V"),
)

_NM = 1e-9

Window = tuple[float, float, float, float]
"""``(r_min, r_max, z_min, z_max)`` in nm."""


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
    raise KeyError(f"no field {quantity!r}; the run holds {', '.join(_quantities(fields))}")


def _quantities(fields: SolutionFields) -> list[str]:
    return sorted({*fields.whole[2], *fields.fluid[2], *FIELD_ALIASES})


def field_unit(quantity: str) -> str:
    """Return the SI unit of a quantity from its attribute key's suffix; ``""`` for none."""
    key = FIELD_ALIASES.get(quantity, (quantity, None))[0]
    return next((unit for suffix, unit in _UNITS if key.endswith(suffix)), "")


_NAMES: dict[tuple[str, int | None], str] = {
    ("phi_V", None): "potential φ",
    ("u_m_s", 0): "radial velocity u_r",
    ("u_m_s", 1): "axial velocity u_z",
    ("p_Pa", None): "pressure p",
}


def quantity_name(quantity: str) -> str:
    """Return a quantity as a reader names it, ``potential φ`` for ``phi_V``; else the key."""
    key, component = FIELD_ALIASES.get(quantity, (quantity, None))
    if (key, component) in _NAMES:
        return _NAMES[(key, component)]
    if key.startswith("c_") and key.endswith("_mol_m3"):
        return f"{key.removeprefix('c_').removesuffix('_mol_m3')} concentration"
    return quantity


@dataclass(frozen=True)
class FieldSplit:
    """The four linear triangles of each P2 cell, in nm, with the bucket size to locate in.

    Parameters
    ----------
    cell_nm
        The bucket size: the median edge of the triangles, or larger where that would give the
        box more than :data:`LOCATE_BUCKETS` buckets.
    box_nm
        ``(r_min, r_max, z_min, z_max)`` of the vertices.
    """

    vertices_nm: np.ndarray
    triangles: np.ndarray
    cell_nm: float
    box_nm: tuple[float, float, float, float]


LOCATE_BUCKETS = 4_000_000
"""The most buckets a split's box is cut into to locate points; it bounds the bucket table."""

_SPLITS: list[
    tuple[weakref.ReferenceType[np.ndarray], weakref.ReferenceType[np.ndarray], FieldSplit]
] = []
_SPLIT_LOCK = threading.Lock()
_KEPT_SPLITS = 4


def field_split(points_m: np.ndarray, cells: np.ndarray) -> FieldSplit:
    """Return the split of a P2 mesh in nm; the last few are kept.

    A value is exact at the P2 nodes only on this split. The arrays are matched by identity, so
    a map and a cut that read the same fields build it once. An entry never keeps its arrays
    alive: it is dropped when either is collected.
    """
    import numpy as np

    with _SPLIT_LOCK:
        _SPLITS[:] = [
            entry for entry in _SPLITS if entry[0]() is not None and entry[1]() is not None
        ]
        for held_points, held_cells, held in _SPLITS:
            if held_points() is points_m and held_cells() is cells:
                return held
    vertices = np.ascontiguousarray(points_m[:, :2], dtype=np.float64) / _NM
    triangles = subdivided(np.asarray(cells, dtype=np.int64))
    corners = vertices[triangles]
    edges = np.linalg.norm(corners - np.roll(corners, 1, axis=1), axis=2)
    low, high = vertices.min(axis=0), vertices.max(axis=0)
    area = float(np.prod(np.maximum(high - low, np.finfo(np.float64).tiny)))
    built = FieldSplit(
        vertices,
        triangles,
        max(float(np.median(edges)), math.sqrt(area / LOCATE_BUCKETS)),
        (float(low[0]), float(high[0]), float(low[1]), float(high[1])),
    )
    with _SPLIT_LOCK:
        _SPLITS.append((weakref.ref(points_m), weakref.ref(cells), built))
        del _SPLITS[:-_KEPT_SPLITS]
    return built


def _weights(split: FieldSplit, points_nm: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return each point's triangle (-1 outside) and its three barycentric weights."""
    import numpy as np

    # A point off the mesh's box, or not finite, is outside; the bucket table spans the points
    # located, so one far point would size it to the gap.
    r_low, r_high, z_low, z_high = split.box_nm
    near = (
        np.isfinite(points_nm).all(axis=1)
        & (points_nm[:, 0] >= r_low - split.cell_nm)
        & (points_nm[:, 0] <= r_high + split.cell_nm)
        & (points_nm[:, 1] >= z_low - split.cell_nm)
        & (points_nm[:, 1] <= z_high + split.cell_nm)
    )
    owner = np.full(points_nm.shape[0], -1, dtype=np.int64)
    owner[near] = locate_points(
        split.vertices_nm, split.triangles, points_nm[near], cell_nm=split.cell_nm
    )
    weights = np.full((points_nm.shape[0], 3), np.nan)
    found = owner >= 0
    corners = split.vertices_nm[split.triangles[owner[found]]]
    v0 = corners[:, 0]
    e1, e2 = corners[:, 1] - v0, corners[:, 2] - v0
    relative = points_nm[found] - v0
    determinant = e1[:, 0] * e2[:, 1] - e2[:, 0] * e1[:, 1]
    l1 = (relative[:, 0] * e2[:, 1] - relative[:, 1] * e2[:, 0]) / determinant
    l2 = (e1[:, 0] * relative[:, 1] - e1[:, 1] * relative[:, 0]) / determinant
    weights[found] = np.column_stack([1.0 - l1 - l2, l1, l2])
    return owner, weights


def _interpolated(
    split: FieldSplit, values: np.ndarray, located: tuple[np.ndarray, np.ndarray]
) -> np.ndarray:
    import numpy as np

    owner, weights = located
    out = np.full(owner.shape[0], np.nan)
    found = owner >= 0
    nodes = split.triangles[owner[found]]
    out[found] = np.einsum("nk,nk->n", weights[found], values[nodes])
    return out


def _points(r_nm: np.ndarray, z_nm: np.ndarray) -> np.ndarray:
    import numpy as np

    r, z = np.broadcast_arrays(
        np.asarray(r_nm, dtype=np.float64), np.asarray(z_nm, dtype=np.float64)
    )
    return np.column_stack([r.ravel(), z.ravel()])


def field_at(
    fields: SolutionFields, quantity: str, r_nm: np.ndarray, z_nm: np.ndarray
) -> np.ndarray:
    """Return one field at the points ``(r_nm, z_nm)``, NaN outside the field's domain.

    The value is linear on each of the four triangles of a P2 cell, so it is the field's at
    every P2 node.
    """
    import numpy as np

    shape = np.broadcast_shapes(np.shape(r_nm), np.shape(z_nm))
    points, cells, values = field_values(fields, quantity)
    split = field_split(points, cells)
    at = _points(r_nm, z_nm)
    return _interpolated(split, values, _weights(split, at)).reshape(shape)


def _box_nm(points_m: np.ndarray) -> Window:
    r = points_m[:, 0] / _NM
    z = points_m[:, 1] / _NM
    return max(0.0, float(r.min())), float(r.max()), float(z.min()), float(z.max())


def _intersected(*boxes: Window | None) -> Window:
    held = [box for box in boxes if box is not None]
    return (
        max(box[0] for box in held),
        min(box[1] for box in held),
        max(box[2] for box in held),
        min(box[3] for box in held),
    )


def _grid(box: Window, cells: int) -> tuple[np.ndarray, np.ndarray]:
    """Return the cell centres of a grid over ``box`` of at least ``cells`` near-square cells."""
    import numpy as np

    r_low, r_high, z_low, z_high = box
    width, height = r_high - r_low, z_high - z_low
    if not (width > 0.0 and height > 0.0):
        raise ValueError(
            f"the window r {r_low:g} to {r_high:g} nm, z {z_low:g} to {z_high:g} nm holds no "
            "part of the fields' domain"
        )
    if cells < 1:
        raise ValueError(f"a grid needs at least one cell; got {cells}")
    spacing = math.sqrt(width * height / cells)
    n_r = max(1, math.ceil(width / spacing))
    n_z = max(1, math.ceil(height / spacing))
    r = r_low + (np.arange(n_r) + 0.5) * width / n_r
    z = z_low + (np.arange(n_z) + 0.5) * height / n_z
    return r, z


def field_grid(
    fields: SolutionFields,
    quantity: str,
    *,
    window_nm: Window | None = None,
    cells: int = GRID_CELLS,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return ``(r_nm, z_nm, values)`` of one run's field over its box, ``values[iz, ir]``.

    The box is the field's domain's, at ``r >= 0``, cut to ``window_nm``; a cell whose centre
    lies outside the field's domain is NaN.
    """
    import numpy as np

    points, _, _ = field_values(fields, quantity)
    r, z = _grid(_intersected(_box_nm(points), window_nm), cells)
    grid_r, grid_z = np.meshgrid(r, z)
    return r, z, field_at(fields, quantity, grid_r, grid_z)


@dataclass(frozen=True)
class FieldDifference:
    """Two runs' field on one grid over their fluids' overlap, and ``second - first``.

    Parameters
    ----------
    unit
        The SI unit of every array.
    first, second, difference
        ``[iz, ir]`` arrays, NaN where either run's fluid lacks the cell's centre.
    """

    quantity: str
    unit: str
    r_nm: np.ndarray
    z_nm: np.ndarray
    first: np.ndarray
    second: np.ndarray
    difference: np.ndarray


def _carried(first: SolutionFields, second: SolutionFields, quantity: str) -> None:
    missing = []
    for which, fields in (("first", first), ("second", second)):
        try:
            field_values(fields, quantity)
        except KeyError as error:
            if "is a vector" in str(error):
                raise
            missing.append(which)
    if missing:
        lacking = (
            "the first and the second run hold"
            if len(missing) == 2
            else f"the {missing[0]} run holds"
        )
        raise KeyError(
            f"{lacking} no field {quantity!r}; the first holds "
            f"{', '.join(_quantities(first))}; the second holds {', '.join(_quantities(second))}"
        )


def field_difference(
    first: SolutionFields,
    second: SolutionFields,
    quantity: str,
    *,
    window_nm: Window | None = None,
    cells: int = GRID_CELLS,
) -> FieldDifference:
    """Sample two runs onto one grid over their fluids' overlap; return each and their difference.

    The grid spans the overlap of the two fluids' boxes, at ``r >= 0``, cut to ``window_nm``. Each
    run is read on the domain its field is solved on; a cell is kept where its centre lies in both
    fluids.

    Raises
    ------
    KeyError
        Either run lacks the quantity; both runs' quantities are named.
    """
    import numpy as np

    _carried(first, second, quantity)
    r, z = _grid(_intersected(_box_nm(first.fluid[0]), _box_nm(second.fluid[0]), window_nm), cells)
    grid_r, grid_z = np.meshgrid(r, z)
    at = _points(grid_r, grid_z)
    kept = np.ones(at.shape[0], dtype=bool)
    sampled = []
    for fields in (first, second):
        fluid = field_split(fields.fluid[0], fields.fluid[1])
        located = _weights(fluid, at)
        kept &= located[0] >= 0
        points, cells_, values = field_values(fields, quantity)
        split = field_split(points, cells_)
        if split is not fluid:
            located = _weights(split, at)
        sampled.append(_interpolated(split, values, located))
    shape = grid_r.shape
    first_values, second_values = (
        np.where(kept, values, np.nan).reshape(shape) for values in sampled
    )
    return FieldDifference(
        quantity=quantity,
        unit=field_unit(quantity),
        r_nm=r,
        z_nm=z,
        first=first_values,
        second=second_values,
        difference=second_values - first_values,
    )


def joint_range(
    first: SolutionFields, second: SolutionFields, quantity: str
) -> tuple[float, float]:
    """Return the lowest and highest nodal value of one quantity over both runs."""
    import numpy as np

    _carried(first, second, quantity)
    values = np.concatenate([field_values(fields, quantity)[2] for fields in (first, second)])
    return float(np.nanmin(values)), float(np.nanmax(values))
