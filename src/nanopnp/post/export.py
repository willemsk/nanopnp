"""IF-07 field export: XDMF with HDF5 heavy data at the P2 node set."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.charge.stage import ResolvedFields, read_fields
from nanopnp.core.scaling import Scales
from nanopnp.core.typing import Expression, FESpace, Mesh
from nanopnp.io.vocabulary import (
    POTENTIAL,
    PRESSURE,
    VELOCITY,
)
from nanopnp.mesh.primitives import ELECTROLYTE_DOMAINS
from nanopnp.physics.models import (
    ModelSolution,
    PhysicsModel,
    concentration_field_name,
    transport_model,
)
from nanopnp.solve.state import STATE_FILENAME, STATE_KEY, restore

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

    from nanopnp.io.artefact import Artefact, StageInputs

__all__ = [
    "EXPORT_SCHEMA",
    "FIXED_CHARGE_ATTRIBUTE",
    "OMEGA_STEM",
    "OMEGA_W_STEM",
    "FieldExport",
    "P2Nodes",
    "SampledFields",
    "attribute_name",
    "export_fields",
    "field_scale",
    "logarithmic_fields",
    "p2_nodes",
    "restored",
    "sample_at",
    "sampled_fields",
]

logger = logging.getLogger(__name__)

EXPORT_SCHEMA = "nanopnp/export/v0.5"

OMEGA_STEM = "fields_omega"

OMEGA_W_STEM = "fields_omega_w"

FIXED_CHARGE_ATTRIBUTE = "rho_fixed_C_m3"

MATERIAL_ID = "material_id"

WALL_DISTANCE = "wall_distance_nm"

_MIDSIDES: tuple[tuple[int, int], ...] = ((0, 1), (1, 2), (2, 0))


@dataclass(frozen=True)
class P2Nodes:
    """The P2 node set of a mesh, or of a selection of its materials.

    Parameters
    ----------
    points_nm
        ``(n, 2)`` node coordinates in nm, vertices before edge midpoints.
    """

    points_nm: np.ndarray
    cells: np.ndarray
    elements: tuple[int, ...]
    materials: tuple[str, ...]


@dataclass(frozen=True)
class FieldExport:
    """What one ``export_fields`` call wrote: the whole-domain and fluid-only pairs."""

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
    """Return the SI attribute name of a model field, unit included."""
    if field == POTENTIAL:
        return "phi_V"
    if field == VELOCITY:
        return "u_m_s"
    if field == PRESSURE:
        return "p_Pa"
    return f"{field}_mol_m3"


def field_scale(field: str, scales: Scales) -> float:
    """Return the scale that takes one field from nondimensional to SI."""
    if field == POTENTIAL:
        return scales.potential_V
    if field == VELOCITY:
        return scales.velocity_m_s
    if field == PRESSURE:
        return scales.pressure_Pa
    return scales.concentration_mol_m3


def logarithmic_fields(model: PhysicsModel) -> frozenset[str]:
    """Return the fields that hold ln c, the unknowns of the logarithmic branch; else none."""
    if not model.species or not transport_model(model).log_variables:
        return frozenset()
    return frozenset(concentration_field_name(species) for species in model.species)


def p2_nodes(mesh: Mesh, *, materials: str | None = None) -> P2Nodes:
    """Return the P2 node set and Triangle_6 cells of ``mesh``."""
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


def sample_at(
    mesh: Mesh,
    expression: Expression,
    points_nm: np.ndarray,
    *,
    order: int,
    dimension: int = 1,
    materials: str | None = None,
    carriers: dict[tuple[int, int], FESpace] | None = None,
) -> np.ndarray:
    """Return ``expression`` at ``points_nm``, through a whole-domain carrier.

    Parameters
    ----------
    dimension
        1 for a scalar, 2 for the ``(r, z)`` velocity.
    materials
        Region the field is defined on; None for all of Omega.
    """
    import ngsolve as ngs
    import numpy as np

    # A space with ``definedon`` returns zero at an interface node whose point search lands outside
    # the region; a whole-domain carrier is exact
    # (knowledge/07-software-stack/04-geometry-meshing-and-io.md).
    if carriers is None:
        carriers = {}
    space = carriers.get((order, dimension))
    if space is None:
        space = ngs.VectorH1(mesh, order=order) if dimension > 1 else ngs.H1(mesh, order=order)
        carriers[(order, dimension)] = space
    carrier = ngs.GridFunction(space)
    if materials is None:
        carrier.Set(expression)
    else:
        carrier.Set(expression, definedon=mesh.Materials(materials))
    sampled = np.asarray(carrier(mesh(points_nm[:, 0], points_nm[:, 1])))
    return sampled.reshape(points_nm.shape[0], dimension)


def _sample_cells(mesh: Mesh, expression: Expression, nodes: P2Nodes) -> np.ndarray:
    import numpy as np

    corners = nodes.points_nm[nodes.cells[:, :3]]
    centres = corners.mean(axis=1)
    return np.asarray(expression(mesh(centres[:, 0], centres[:, 1]))).reshape(-1)


def _material_ids(mesh: Mesh, nodes: P2Nodes) -> np.ndarray:
    import ngsolve as ngs
    import numpy as np

    index = {element.nr: element.index for element in mesh.Elements(ngs.VOL)}
    return np.array([index[number] for number in nodes.elements], dtype=np.int32)


def _as_vector(values: np.ndarray) -> np.ndarray:
    import numpy as np

    # u_theta is zero by the axisymmetric ansatz; an XDMF Vector needs three components.
    return np.column_stack([values, np.zeros(values.shape[0], dtype=values.dtype)])


def _write_pair(
    path: Path,
    nodes: P2Nodes,
    *,
    point_data: dict[str, np.ndarray],
    cell_data: dict[str, np.ndarray],
    metadata: dict[str, object],
) -> tuple[Path, Path]:
    import h5py
    import meshio

    grid = meshio.Mesh(
        nodes.points_nm,
        [("triangle6", nodes.cells)],
        point_data=point_data,
        cell_data={name: [values] for name, values in cell_data.items()},
    )
    # Compression is explicit so a change of meshio's default cannot multiply a sweep's storage.
    meshio.xdmf.write(path, grid, data_format="HDF", compression="gzip")
    heavy = path.with_suffix(".h5")
    # HDF5 root attributes: meshio cannot read a float set from an XDMF Information element.
    with h5py.File(heavy, "a") as handle:
        for key, value in metadata.items():
            handle.attrs[key] = value
    return (path, heavy)


def restored(
    inputs: StageInputs, solution: Artefact
) -> tuple[ModelSolution, ResolvedFields | None]:
    """Restore the converged state of ``solution``; also return the supplied fields, if any.

    Raises
    ------
    KeyError
        The solve artefact carries no state record.
    """
    state_path = solution.payload.get(STATE_KEY)
    if state_path is None:
        carried = ", ".join(sorted(solution.payload)) or "nothing"
        raise KeyError(
            f"the solve artefact carries no {STATE_KEY!r} payload (the {STATE_FILENAME} "
            f"record); it carries {carried}. "
            "The IF-07 export is of the converged fields and there is nothing to export from"
        )
    resolved = inputs.resolved
    supplied = (
        read_fields(resolved) if resolved.charge is not None or resolved.eps_r is not None else None
    )
    state = restore(
        Path(state_path),
        resolved=resolved,
        mesh_artefact=inputs.upstream.get("mesh"),
        fields=supplied,
        charge_artefact=inputs.upstream.get("charge"),
    )
    return state, supplied


@dataclass(frozen=True)
class SampledFields:
    """Every solved field in SI at the P2 nodes of the whole domain or of the fluid.

    Parameters
    ----------
    whole, restricted
        Field arrays by attribute name; ``(n,)`` for a scalar and ``(n, 2)`` for the
        ``(r, z)`` velocity.
    carriers
        The carrier spaces built on the way, for the caller to reuse.
    """

    omega: P2Nodes
    omega_w: P2Nodes
    whole: dict[str, np.ndarray]
    restricted: dict[str, np.ndarray]
    carriers: dict[tuple[int, int], FESpace]


def sampled_fields(
    solution: ModelSolution, scales: Scales, *, fluid: str = ELECTROLYTE_DOMAINS
) -> SampledFields:
    """Sample every field of ``solution`` at the P2 nodes, exponentiated and scaled to SI."""
    import numpy as np

    mesh = solution.space.mesh
    model = solution.model
    omega = p2_nodes(mesh)
    omega_w = p2_nodes(mesh, materials=fluid)

    # One set of carrier spaces for the whole export.
    carriers: dict[tuple[int, int], FESpace] = {}
    whole: dict[str, np.ndarray] = {}
    restricted: dict[str, np.ndarray] = {}
    # The logarithmic branch solves ln c. Its nodal values are exponentiated after sampling:
    # sampling exp(ln c) through a carrier projects it and does not reproduce c at the nodes.
    logarithmic = logarithmic_fields(model)
    for field in model.fields:
        if field.element == "number":
            continue
        name = attribute_name(field.name)
        values = sample_at(
            mesh,
            solution.component(field.name),
            omega.points_nm if field.domain is None else omega_w.points_nm,
            order=field.order,
            dimension=2 if field.element == "vector_h1" else 1,
            materials=field.domain,
            carriers=carriers,
        )
        if field.name in logarithmic:
            values = np.exp(values)
        values = values * field_scale(field.name, scales)
        target = whole if field.domain is None else restricted
        target[name] = values if field.element == "vector_h1" else values[:, 0]
    return SampledFields(omega, omega_w, whole, restricted, carriers)


def export_fields(
    solution: ModelSolution,
    directory: Path,
    *,
    scales: Scales,
    fluid: str = ELECTROLYTE_DOMAINS,
    fixed_charge_C_m3: Expression | None = None,
    relative_permittivity: Expression | None = None,
) -> FieldExport:
    """Write the solved fields as XDMF with HDF5 data in SI; return what was written.

    Parameters
    ----------
    fixed_charge_C_m3
        The supplied fixed charge in C/m^3, if any; written node-centred.
    relative_permittivity
        ``eps_r`` as the form used it, if buildable; written cell-centred.
    """
    directory.mkdir(parents=True, exist_ok=True)
    mesh = solution.space.mesh
    model = solution.model

    sampled = sampled_fields(solution, scales, fluid=fluid)
    omega, omega_w = sampled.omega, sampled.omega_w
    carriers = sampled.carriers
    whole = {
        name: _as_vector(values) if values.ndim == 2 else values
        for name, values in sampled.whole.items()
    }
    restricted = {
        name: _as_vector(values) if values.ndim == 2 else values
        for name, values in sampled.restricted.items()
    }

    if fixed_charge_C_m3 is not None:
        whole[FIXED_CHARGE_ATTRIBUTE] = sample_at(
            mesh,
            fixed_charge_C_m3,
            omega.points_nm,
            order=model.fields[0].order,
            carriers=carriers,
        )[:, 0]
    restricted[WALL_DISTANCE] = sample_at(
        mesh,
        solution.wall_distance_nm,
        omega_w.points_nm,
        order=model.fields[0].order,
        carriers=carriers,
    )[:, 0]

    cells: dict[str, np.ndarray] = {MATERIAL_ID: _material_ids(mesh, omega)}
    if relative_permittivity is not None:
        cells["eps_r"] = _sample_cells(mesh, relative_permittivity, omega)

    common: dict[str, object] = {
        "schema": EXPORT_SCHEMA,
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
