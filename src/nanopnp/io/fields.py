"""IF-07 field export: XDMF with HDF5 heavy data at the P2 node set.

A solved state is written where NUM-01 puts it. For a P2 space on triangles
``ndof = nv + nedge``, and a P2 polynomial on a straight-sided triangle is
determined by its values at the three vertices and the three edge midpoints, so
writing ``Triangle_6`` cells over exactly that node set records the solution
without introducing an interpolation error. The same six nodes record ``p``
exactly too: a P1 function's midpoint value is the mean of its endpoints, so the
P2 container costs nothing but the space. Midside nodes are identified by the
*unordered pair of vertices* they lie between, never by a backend's local edge
numbering — a permutation of the three would give a picture that looks right and
is wrong.

Two files are written, not one. ``phi`` is posed over all of Omega and ``c_i``,
``u`` and ``p`` over the fluid alone, and padding the fluid fields with zeros
over the membrane would produce a file in which a zero concentration *inside a
wall* is indistinguishable from a converged depletion (IF-07). Coordinates are
in nm, matching the archival mesh of IF-06; values are SI with the unit in the
attribute name. The ``2 pi`` of the axisymmetric measure is **not** applied:
these values are pointwise, and section 6.7 restores that factor exactly once, in
the quantity-of-interest extraction.

Two things this module does are not what a first reading of IF-07 suggests, and
both were measured rather than reasoned.

**A fluid-restricted field is sampled through a whole-domain carrier.** Point
evaluation asks the mesh which element contains a point, and for a node on the
electrolyte/membrane interface the answer may be the membrane element, where a
space built with ``definedon=fluid`` has no degrees of freedom and returns zero.
On the coarse four-material pore that is 16 of the 208 fluid nodes and a maximum
error of 13.0 against a linear test function. Interpolating into a whole-domain
space of the same order first and evaluating *that* is exact to 5.5e-14, because
the value at a P2 node depends only on the entities carrying it — the vertex, or
the edge and its two endpoints — and each of those is a fluid entity whose
coefficient the restricted-region interpolation set correctly.

**The scale set is recorded as HDF5 root attributes, not as an XDMF
``Information`` element.** meshio 5.3.5 reads ``Information`` only in its own
``field_data`` encoding — children carrying ``key`` and ``dim`` attributes with
integer text — and raises ``ParseError`` on anything else, so an ``Information``
element carrying a float scale set makes the exported file unreadable by the
commonest Python XDMF reader. IF-07 requires the scale set "in the file"; the
heavy-data file is where a reader of the values already is.

Discontinuous quantities are written **cell-centred**. ``material_id`` and
``eps_r`` jump across a material interface, so a node value there is one side
chosen arbitrarily and a viewer would draw a fictitious ramp across every
boundary element. Cell-centring draws the jump where it is and makes a threshold
by material exact.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.core.scaling import Scales
from nanopnp.core.typing import Expression, Mesh
from nanopnp.mesh.primitives import ELECTROLYTE_DOMAINS
from nanopnp.physics.models import (
    POTENTIAL,
    PRESSURE,
    VELOCITY,
    ModelSolution,
)

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

__all__ = [
    "FIELDS_SCHEMA",
    "OMEGA_STEM",
    "OMEGA_W_STEM",
    "FieldExport",
    "P2Nodes",
    "attribute_name",
    "export_fields",
    "p2_nodes",
]

logger = logging.getLogger(__name__)

FIELDS_SCHEMA = "nanopnp/fields/v1"
"""Domain separator recorded in each file, so a reader can refuse a later one."""

OMEGA_STEM = "fields_omega"
"""Stem of the whole-domain file pair."""

OMEGA_W_STEM = "fields_omega_w"
"""Stem of the fluid-only file pair."""

MATERIAL_ID = "material_id"
"""Cell attribute naming each element's material by its index in ``GetMaterials()``."""

WALL_DISTANCE = "wall_distance_nm"
"""Node attribute carrying the PHY-02 distance field, already in nm."""

_MIDSIDES: tuple[tuple[int, int], ...] = ((0, 1), (1, 2), (2, 0))
"""Vertex pairs whose midpoints are Triangle_6 nodes 3, 4 and 5, in that order."""


@dataclass(frozen=True)
class P2Nodes:
    """The P2 node set of a mesh, or of a selection of its materials.

    Parameters
    ----------
    points_nm
        ``(n, 2)`` node coordinates in nm, vertices before edge midpoints.
    cells
        ``(m, 6)`` Triangle_6 connectivity: three vertices then the midpoints of
        edges ``(0, 1)``, ``(1, 2)`` and ``(2, 0)``, indexing ``points_nm``.
    elements
        NGSolve element numbers, in the order the rows of ``cells`` take, so a
        cell-centred attribute can be evaluated element by element.
    materials
        The distinct material names the retained elements carry, in the mesh's
        own material order. Recorded in the file so a reader knows which part of
        Omega it is holding without re-deriving it from ``material_id``.
    """

    points_nm: np.ndarray
    cells: np.ndarray
    elements: tuple[int, ...]
    materials: tuple[str, ...]


@dataclass(frozen=True)
class FieldExport:
    """What one call to :func:`export_fields` wrote.

    Parameters
    ----------
    omega
        The whole-domain ``.xdmf`` and ``.h5`` pair.
    omega_w
        The fluid-only pair, or ``None`` if the model solves no fluid field.
    attributes
        Attribute names written, per file stem, for the FR-25 manifest.
    """

    omega: tuple[Path, Path]
    omega_w: tuple[Path, Path] | None
    attributes: dict[str, tuple[str, ...]]

    def paths(self) -> tuple[Path, ...]:
        """Return every file written, in a stable order."""
        written = list(self.omega)
        if self.omega_w is not None:
            written.extend(self.omega_w)
        return tuple(written)


def attribute_name(field: str) -> str:
    """Return the SI attribute name of one model field.

    The unit goes in the name because a file is a boundary and the house rule
    puts units at boundaries. Concentrations keep the species in the field name
    they already carry, so ``c_Na+`` becomes ``c_Na+_mol_m3``.
    """
    if field == POTENTIAL:
        return "phi_V"
    if field == VELOCITY:
        return "u_m_s"
    if field == PRESSURE:
        return "p_Pa"
    return f"{field}_mol_m3"


def _field_scale(field: str, scales: Scales) -> float:
    """Return the NUM-09 scale that takes one field from nondimensional to SI."""
    if field == POTENTIAL:
        return scales.potential_V
    if field == VELOCITY:
        return scales.velocity_m_s
    if field == PRESSURE:
        return scales.pressure_Pa
    return scales.concentration_mol_m3


def p2_nodes(mesh: Mesh, *, materials: str | None = None) -> P2Nodes:
    """Return the P2 node set and Triangle_6 cells of ``mesh``.

    Parameters
    ----------
    mesh
        The deployed mesh.
    materials
        Material-name regular expression to restrict the cells to, or ``None``
        for every material. Nodes not carried by a retained element are dropped
        and the remainder renumbered compactly, so the fluid file holds no node
        that is only a membrane node.

    Notes
    -----
    Midside nodes are found through a map from the *unordered* pair of endpoint
    vertices to the edge number, so the result assumes nothing about how the
    backend orders an element's edges locally.
    """
    import ngsolve as ngs
    import numpy as np

    vertices = np.array([vertex.point for vertex in mesh.vertices], dtype=float)
    midpoints = np.empty((mesh.nedge, vertices.shape[1]), dtype=float)
    pair_to_edge: dict[frozenset[int], int] = {}
    for edge in mesh.edges:
        ends = [vertex.nr for vertex in edge.vertices]
        pair_to_edge[frozenset(ends)] = edge.nr
        midpoints[edge.nr] = 0.5 * (vertices[ends[0]] + vertices[ends[1]])

    keep = None if materials is None else mesh.Materials(materials).Mask()
    rows: list[list[int]] = []
    elements: list[int] = []
    for element in mesh.Elements(ngs.VOL):
        if keep is not None and not keep[element.index]:
            continue
        ends = [vertex.nr for vertex in element.vertices]
        rows.append(
            ends + [mesh.nv + pair_to_edge[frozenset((ends[a], ends[b]))] for a, b in _MIDSIDES]
        )
        elements.append(element.nr)
    if not rows:
        raise ValueError(
            f"no element of the mesh carries a material matching {materials!r}; "
            f"it has {', '.join(mesh.GetMaterials())}"
        )

    names = mesh.GetMaterials()
    connectivity = np.array(rows, dtype=np.int64)
    used = np.unique(connectivity)
    lookup = np.full(mesh.nv + mesh.nedge, -1, dtype=np.int64)
    lookup[used] = np.arange(used.size, dtype=np.int64)
    return P2Nodes(
        points_nm=np.vstack([vertices, midpoints])[used],
        cells=lookup[connectivity].astype(np.int32),
        elements=tuple(elements),
        materials=tuple(name for index, name in enumerate(names) if keep is None or keep[index]),
    )


def _sample_nodes(
    mesh: Mesh,
    expression: Expression,
    points_nm: np.ndarray,
    *,
    order: int,
    dimension: int = 1,
    materials: str | None = None,
) -> np.ndarray:
    """Return ``expression`` at ``points_nm``, through a whole-domain carrier.

    The carrier is the point of the function. Evaluating a space built with
    ``definedon`` directly returns zero wherever the mesh's point search lands in
    an element outside the region, which on an interface node it may; see the
    module docstring for the measurement. Interpolating into a whole-domain space
    of the same order restricted to the same region, and evaluating that, is
    exact at every node of the region.

    Parameters
    ----------
    mesh
        The deployed mesh.
    expression
        The field, in whatever units it is to be written.
    points_nm
        ``(n, 2)`` evaluation points.
    order
        Polynomial order of the carrier, matching the field's own.
    dimension
        1 for a scalar, 2 for the ``(r, z)`` velocity.
    materials
        Region the field is defined on, or ``None`` for all of Omega.
    """
    import ngsolve as ngs
    import numpy as np

    space = ngs.VectorH1(mesh, order=order) if dimension > 1 else ngs.H1(mesh, order=order)
    carrier = ngs.GridFunction(space)
    if materials is None:
        carrier.Set(expression)
    else:
        carrier.Set(expression, definedon=mesh.Materials(materials))
    sampled = np.asarray(carrier(mesh(points_nm[:, 0], points_nm[:, 1])))
    return sampled.reshape(points_nm.shape[0], dimension)


def _sample_cells(mesh: Mesh, expression: Expression, nodes: P2Nodes) -> np.ndarray:
    """Return ``expression`` at the barycentre of each retained element.

    A barycentre lies strictly inside its element, so the point search is
    unambiguous even for a coefficient that jumps across the element's faces —
    which is the reason a discontinuous quantity is written cell-centred at all.
    """
    import numpy as np

    corners = nodes.points_nm[nodes.cells[:, :3]]
    centres = corners.mean(axis=1)
    return np.asarray(expression(mesh(centres[:, 0], centres[:, 1]))).reshape(-1)


def _material_ids(mesh: Mesh, nodes: P2Nodes) -> np.ndarray:
    """Return each retained element's material index into ``mesh.GetMaterials()``."""
    import ngsolve as ngs
    import numpy as np

    index = {element.nr: element.index for element in mesh.Elements(ngs.VOL)}
    return np.array([index[number] for number in nodes.elements], dtype=np.int32)


def _as_vector(values: np.ndarray) -> np.ndarray:
    """Return an ``(n, 2)`` half-plane velocity as the ``(n, 3)`` XDMF expects.

    The third component is the azimuthal velocity ``u_theta``, identically zero
    under the axisymmetric ansatz of PHY-01, so writing it invents nothing. It is
    written because XDMF's ``Vector`` attribute means three components: a
    two-component one reads back as a vector no glyph filter will accept, which
    would make the flow field the one thing in the file nobody can look at.
    """
    import numpy as np

    return np.column_stack([values, np.zeros(values.shape[0], dtype=values.dtype)])


def _write_pair(
    path: Path,
    nodes: P2Nodes,
    *,
    point_data: dict[str, np.ndarray],
    cell_data: dict[str, np.ndarray],
    metadata: dict[str, object],
) -> tuple[Path, Path]:
    """Write one XDMF/HDF5 pair and return both paths.

    meshio compresses HDF5 heavy data with gzip by default, which is the setting
    IF-07 asks for; it is passed explicitly rather than inherited, so a change of
    that default cannot silently multiply a sweep's storage by five.
    """
    import h5py
    import meshio

    grid = meshio.Mesh(
        nodes.points_nm,
        [("triangle6", nodes.cells)],
        point_data=point_data,
        cell_data={name: [values] for name, values in cell_data.items()},
    )
    meshio.xdmf.write(path, grid, data_format="HDF", compression="gzip")
    heavy = path.with_suffix(".h5")
    with h5py.File(heavy, "a") as handle:
        for key, value in metadata.items():
            handle.attrs[key] = value
    return (path, heavy)


def export_fields(
    solution: ModelSolution,
    directory: Path,
    *,
    scales: Scales,
    fluid: str = ELECTROLYTE_DOMAINS,
    fixed_charge_C_m3: Expression | None = None,
    relative_permittivity: Expression | None = None,
) -> FieldExport:
    """Write the solved fields as XDMF with HDF5 heavy data (IF-07).

    Parameters
    ----------
    solution
        The converged state. Its fields are read from the model's own field
        declarations, so a model that solves no flow simply writes no ``u_m_s``.
    directory
        Where the two file pairs go. Created if it does not exist.
    scales
        The NUM-09 scale set the state was solved in. Every value is written in
        SI, and the set itself is recorded in each file so the nondimensional
        reading stays recoverable without a second solve.
    fluid
        Material-name regular expression of Omega_w.
    fixed_charge_C_m3
        The supplied ``rho_fixed`` in C/m^3, if the case supplies one. Continuous
        by construction — it is a smeared field — so it is written node-centred.
    relative_permittivity
        ``eps_r`` as the form used it, if the caller can build it. Written
        cell-centred: it jumps by a factor of about 24 across the membrane.

    Returns
    -------
    FieldExport
        The paths written and the attribute names in each, for the manifest.

    Notes
    -----
    The ``2 pi`` of the axisymmetric measure is not applied here; see the module
    docstring.
    """
    directory.mkdir(parents=True, exist_ok=True)
    mesh = solution.space.mesh
    model = solution.model

    omega = p2_nodes(mesh)
    omega_w = p2_nodes(mesh, materials=fluid)

    whole: dict[str, np.ndarray] = {}
    restricted: dict[str, np.ndarray] = {}
    for field in model.fields:
        if field.element == "number":
            continue
        name = attribute_name(field.name)
        values = _sample_nodes(
            mesh,
            solution.component(field.name),
            omega.points_nm if field.domain is None else omega_w.points_nm,
            order=field.order,
            dimension=2 if field.element == "vector_h1" else 1,
            materials=field.domain,
        ) * _field_scale(field.name, scales)
        target = whole if field.domain is None else restricted
        target[name] = _as_vector(values) if field.element == "vector_h1" else values[:, 0]

    if fixed_charge_C_m3 is not None:
        whole["rho_fixed_C_m3"] = _sample_nodes(
            mesh, fixed_charge_C_m3, omega.points_nm, order=model.fields[0].order
        )[:, 0]
    restricted[WALL_DISTANCE] = _sample_nodes(
        mesh, solution.wall_distance_nm, omega_w.points_nm, order=model.fields[0].order
    )[:, 0]

    cells: dict[str, np.ndarray] = {MATERIAL_ID: _material_ids(mesh, omega)}
    if relative_permittivity is not None:
        cells["eps_r"] = _sample_cells(mesh, relative_permittivity, omega)

    common: dict[str, object] = {
        "schema": FIELDS_SCHEMA,
        "coordinate_units": "nm",
        "two_pi_applied": 0,
        "scales": json.dumps(scales.summary(), sort_keys=True),
        "materials": json.dumps(list(mesh.GetMaterials())),
        "model": model.name,
    }
    written_omega = _write_pair(
        directory / f"{OMEGA_STEM}.xdmf",
        omega,
        point_data=whole,
        cell_data=cells,
        metadata={
            **common,
            "domain": "omega",
            "domain_materials": json.dumps(list(omega.materials)),
        },
    )
    attributes = {OMEGA_STEM: tuple(sorted(whole)) + tuple(sorted(cells))}

    written_omega_w: tuple[Path, Path] | None = None
    if len(restricted) > 1:
        written_omega_w = _write_pair(
            directory / f"{OMEGA_W_STEM}.xdmf",
            omega_w,
            point_data=restricted,
            cell_data={},
            metadata={
                **common,
                "domain": "omega_w",
                "domain_materials": json.dumps(list(omega_w.materials)),
            },
        )
        attributes[OMEGA_W_STEM] = tuple(sorted(restricted))
    logger.info(
        "wrote %d nodes on Omega and %d on Omega_w to %s",
        omega.points_nm.shape[0],
        omega_w.points_nm.shape[0],
        directory,
    )
    return FieldExport(omega=written_omega, omega_w=written_omega_w, attributes=attributes)
