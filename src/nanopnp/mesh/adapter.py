"""One in-memory mesh, and every way in and out of it (IF-06, section 5.1)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.core.hashing import content_hash
from nanopnp.core.typing import Mesh
from nanopnp.io.artefact import MESH_ARTEFACT_SCHEMA

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

_LOGGER = logging.getLogger(__name__)

MESH_SCHEMA: str = MESH_ARTEFACT_SCHEMA
"""Stage 6: a tagged mesh, addressed by the content of its arrays and tag maps."""

TOL_NM = 1e-9
"""Tolerance on the out-of-plane coordinate of an ``(r, z)`` mesh, in nm.

Also the width of the axis band :meth:`MeshData._snap_to_axis` collapses to
``r = 0``: a femtometre, eleven orders below the smallest feature any pore
geometry of section 2.2 carries, so nothing physical can fall inside it.
"""

FORMATS: dict[str, str] = {
    "msh": "gmsh",
    "msh22": "gmsh",
    "msh41": "gmsh",
    "gmsh": "gmsh",
    "netgen": "netgen",
    "vol": "netgen",
}
"""``inputs.mesh.format`` spellings, mapped onto the two readers.

The MSH version is not a reader choice — meshio dispatches on the file's own
``$MeshFormat`` line — so ``msh22`` and ``msh41`` are the same route in and
differ only on the way out, where :func:`write_msh41` names the version it
writes.
"""

# Filename suffixes recognised when ``inputs.mesh.format`` is absent.
_SUFFIXES: dict[str, str] = {".msh": "gmsh", ".vol": "netgen", ".vol.gz": "netgen"}


class MeshFormatError(ValueError):
    """A mesh file cannot be read: unknown format, or unreadable contents."""


class MeshDataError(ValueError):
    """A :class:`MeshData` is not a well-formed tagged mesh."""


def detect_format(path: Path, declared: str | None = None) -> str:
    """Return the reader route, ``"gmsh"`` or ``"netgen"``, for ``path``.

    Raises
    ------
    MeshFormatError
        If the declared format is unknown, or none is declared and the suffix is unrecognised.
    """
    if declared is not None:
        route = FORMATS.get(declared.strip().lower())
        if route is None:
            known = ", ".join(sorted(FORMATS))
            raise MeshFormatError(
                f"inputs.mesh.format is {declared!r}; the readable formats are {known}"
            )
        return route
    name = path.name.lower()
    for suffix, route in _SUFFIXES.items():
        if name.endswith(suffix):
            return route
    known = ", ".join(sorted(_SUFFIXES))
    raise MeshFormatError(
        f"cannot tell the format of {path.name!r} from its name; the recognised suffixes are "
        f"{known}, or name the format in inputs.mesh.format"
    )


@dataclass(frozen=True)
class MeshData:
    """A tagged two-dimensional mesh in the ``(r, z)`` half-plane, in nm.

    Parameters
    ----------
    triangles
        ``(m, 3)`` vertex indices, counter-clockwise for a positively oriented element.
    """

    vertices: np.ndarray
    triangles: np.ndarray
    triangle_material: np.ndarray
    materials: tuple[str, ...]
    edges: np.ndarray
    edge_group: np.ndarray
    boundaries: tuple[str, ...]

    def __post_init__(self) -> None:
        import numpy as np

        object.__setattr__(self, "vertices", np.ascontiguousarray(self.vertices, dtype=np.float64))
        object.__setattr__(self, "triangles", np.ascontiguousarray(self.triangles, dtype=np.int64))
        object.__setattr__(
            self, "triangle_material", np.ascontiguousarray(self.triangle_material, dtype=np.int64)
        )
        object.__setattr__(self, "edges", np.ascontiguousarray(self.edges, dtype=np.int64))
        object.__setattr__(
            self, "edge_group", np.ascontiguousarray(self.edge_group, dtype=np.int64)
        )
        object.__setattr__(self, "materials", tuple(self.materials))
        object.__setattr__(self, "boundaries", tuple(self.boundaries))
        self._snap_to_axis()
        self._validate()

    def _snap_to_axis(self) -> None:
        import numpy as np

        radii = self.vertices[:, 0]
        snapped = np.where(np.abs(radii) < TOL_NM, 0.0, radii)
        if not np.array_equal(snapped, radii):
            vertices = self.vertices.copy()
            vertices[:, 0] = snapped
            object.__setattr__(self, "vertices", vertices)

    def _validate(self) -> None:
        import numpy as np

        if self.vertices.ndim != 2 or self.vertices.shape[1] != 2:
            raise MeshDataError(
                f"vertices must be an (n, 2) array of (r, z) in nm, got shape {self.vertices.shape}"
            )
        if self.triangles.ndim != 2 or self.triangles.shape[1] != 3:
            raise MeshDataError(f"triangles must be an (m, 3) array, got {self.triangles.shape}")
        if self.edges.ndim != 2 or self.edges.shape[1] != 2:
            raise MeshDataError(f"edges must be a (k, 2) array, got {self.edges.shape}")
        if self.triangle_material.shape != (self.triangles.shape[0],):
            raise MeshDataError(
                f"triangle_material has {self.triangle_material.shape} entries for "
                f"{self.triangles.shape[0]} triangles"
            )
        if self.edge_group.shape != (self.edges.shape[0],):
            raise MeshDataError(
                f"edge_group has {self.edge_group.shape} entries for {self.edges.shape[0]} edges"
            )
        for table, label in ((self.materials, "material"), (self.boundaries, "boundary")):
            if len(set(table)) != len(table):
                raise MeshDataError(f"{label} names must be unique, got {list(table)}")
        n = self.vertices.shape[0]
        for index, label, limit in (
            (self.triangles, "triangle", n),
            (self.edges, "edge", n),
            (self.triangle_material, "triangle_material", len(self.materials)),
            (self.edge_group, "edge_group", len(self.boundaries)),
        ):
            if index.size and (int(index.min()) < 0 or int(index.max()) >= limit):
                raise MeshDataError(
                    f"{label} index out of range: [{int(index.min())}, {int(index.max())}] against "
                    f"{limit} entries"
                )
        if self.triangles.size == 0:
            raise MeshDataError("a mesh with no triangle carries no domain to solve on")
        unused = set(range(len(self.materials))) - set(np.unique(self.triangle_material).tolist())
        if unused:
            named = ", ".join(sorted(self.materials[i] for i in unused))
            raise MeshDataError(f"material name table carries names no element uses: {named}")
        unused_bc = set(range(len(self.boundaries))) - set(np.unique(self.edge_group).tolist())
        if unused_bc:
            named = ", ".join(sorted(self.boundaries[i] for i in unused_bc))
            raise MeshDataError(f"boundary name table carries names no edge uses: {named}")

    @property
    def element_count(self) -> int:
        """Number of triangles."""
        return int(self.triangles.shape[0])

    @property
    def vertex_count(self) -> int:
        """Number of vertices."""
        return int(self.vertices.shape[0])

    def material_of(self, name: str) -> np.ndarray:
        """Return the boolean mask of triangles carrying the material ``name``."""
        if name not in self.materials:
            raise KeyError(f"no material {name!r}; the mesh carries {list(self.materials)}")
        mask: np.ndarray = self.triangle_material == self.materials.index(name)
        return mask

    def edges_of(self, name: str) -> np.ndarray:
        """Return the ``(k, 2)`` edges of the boundary group ``name``."""
        if name not in self.boundaries:
            raise KeyError(f"no boundary group {name!r}; the mesh carries {list(self.boundaries)}")
        rows: np.ndarray = self.edges[self.edge_group == self.boundaries.index(name)]
        return rows

    def renamed(
        self, *, materials: dict[str, str] | None = None, boundaries: dict[str, str] | None = None
    ) -> MeshData:
        """Return this mesh with its name tables mapped; groups mapped onto one name merge."""
        import numpy as np

        def remap(
            table: tuple[str, ...], mapping: dict[str, str] | None, tags: np.ndarray
        ) -> tuple[tuple[str, ...], np.ndarray]:
            targets = [(mapping or {}).get(name, name) for name in table]
            merged: list[str] = []
            index = np.empty(len(targets), dtype=np.int64)
            for position, target in enumerate(targets):
                if target not in merged:
                    merged.append(target)
                index[position] = merged.index(target)
            return tuple(merged), index[tags] if tags.size else tags.copy()

        new_materials, triangle_material = remap(self.materials, materials, self.triangle_material)
        new_boundaries, edge_group = remap(self.boundaries, boundaries, self.edge_group)
        return replace(
            self,
            materials=new_materials,
            triangle_material=triangle_material,
            boundaries=new_boundaries,
            edge_group=edge_group,
        )

    def canonical(self) -> MeshData:
        """Return this mesh in the form its content hash is taken over.

        Raises
        ------
        MeshDataError
            If two vertices share a location.
        """
        import numpy as np

        order = np.lexsort((self.vertices[:, 1], self.vertices[:, 0]))
        vertices = self.vertices[order]
        if vertices.shape[0] > 1 and bool(np.any(np.all(np.diff(vertices, axis=0) == 0.0, axis=1))):
            raise MeshDataError(
                "two vertices of this mesh share a location, so it has no canonical vertex order; "
                "a mesh with coincident vertices is degenerate"
            )
        renumber = np.empty(order.size, dtype=np.int64)
        renumber[order] = np.arange(order.size, dtype=np.int64)

        triangles = renumber[self.triangles]
        roll = np.argmin(triangles, axis=1)
        rows = np.arange(triangles.shape[0])[:, None]
        triangles = triangles[rows, (np.arange(3)[None, :] + roll[:, None]) % 3]
        material_names = np.array(self.materials)[self.triangle_material]
        triangle_order = np.lexsort(
            (triangles[:, 2], triangles[:, 1], triangles[:, 0], material_names)
        )

        edges = np.sort(renumber[self.edges], axis=1)
        group_names = np.array(self.boundaries)[self.edge_group]
        edge_order = np.lexsort((edges[:, 1], edges[:, 0], group_names))

        materials = tuple(sorted(self.materials))
        boundaries = tuple(sorted(self.boundaries))
        return MeshData(
            vertices=vertices,
            triangles=triangles[triangle_order],
            triangle_material=np.array(
                [materials.index(name) for name in material_names[triangle_order]], dtype=np.int64
            ),
            materials=materials,
            edges=edges[edge_order],
            edge_group=np.array(
                [boundaries.index(name) for name in group_names[edge_order]], dtype=np.int64
            ),
            boundaries=boundaries,
        )

    @property
    def content_hash(self) -> str:
        """The sha256 of this mesh's canonical form, as 64 hex characters."""
        form = self.canonical()
        return content_hash(
            MESH_SCHEMA,
            {
                "vertices": form.vertices,
                "triangles": form.triangles,
                "triangle_material": form.triangle_material,
                "materials": list(form.materials),
                "edges": form.edges,
                "edge_group": form.edge_group,
                "boundaries": list(form.boundaries),
            },
        )

    def summary(self) -> dict[str, object]:
        """Return the counts and name tables a manifest records."""
        return {
            "vertices": self.vertex_count,
            "elements": self.element_count,
            "edges": int(self.edges.shape[0]),
            "materials": list(self.materials),
            "boundaries": list(self.boundaries),
            "content_hash": self.content_hash,
        }


def read(path: Path, *, format: str | None = None) -> MeshData:
    """Read a tagged mesh from disk.

    Raises
    ------
    MeshFormatError
        If the format is unknown or the reader refuses the file.
    """
    route = detect_format(path, format)
    if not path.is_file():
        raise MeshFormatError(f"no mesh file at {path}")
    if route == "gmsh":
        return _read_meshio(path)
    return _read_netgen(path)


def _read_meshio(path: Path) -> MeshData:
    import meshio
    import numpy as np

    try:
        # meshio tries ANSYS first for ``.msh`` and prints an empty line to stdout (IF-02).
        mesh = meshio.read(str(path), file_format="gmsh")
    except Exception as error:  # meshio raises a dozen unrelated types
        raise MeshFormatError(f"meshio could not read {path}: {error}") from error

    points = np.asarray(mesh.points, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] < 2:
        raise MeshFormatError(f"{path}: expected point coordinates, got shape {points.shape}")
    if points.shape[1] > 2 and not bool(np.all(np.abs(points[:, 2]) <= TOL_NM)):
        raise MeshFormatError(
            f"{path}: this is a three-dimensional mesh; nanopnp solves the (r, z) half-plane "
            "and reads a mesh whose third coordinate is zero throughout (CON-04)"
        )
    vertices = np.ascontiguousarray(points[:, :2])

    names = read_physical_names(path)
    physical = mesh.cell_data.get("gmsh:physical")
    blocks: dict[str, dict[int, list[np.ndarray]]] = {"triangle": {}, "line": {}}
    for position, block in enumerate(mesh.cells):
        if block.type == "vertex":
            _LOGGER.debug("ignoring %d %s cells in %s", len(block.data), block.type, path.name)
            continue
        if block.type not in blocks:
            # A dropped row of quads would leave a hole whose edge takes the free condition.
            raise MeshFormatError(
                f"{path}: carries {len(block.data)} {block.type!r} cells; nanopnp solves on "
                "straight-sided triangles bounded by line segments (section 5.2.2), and dropping "
                "these cells would leave a hole whose edge carries no boundary condition"
            )
        connectivity = np.asarray(block.data, dtype=np.int64)
        tags = (
            np.asarray(physical[position], dtype=np.int64)
            if physical is not None and position < len(physical)
            else np.zeros(len(connectivity), dtype=np.int64)
        )
        for tag in np.unique(tags):
            blocks[block.type].setdefault(int(tag), []).append(connectivity[tags == tag])

    def table(kind: str, dim: int, width: int) -> tuple[tuple[str, ...], np.ndarray, np.ndarray]:
        table_names: list[str] = []
        rows: list[np.ndarray] = []
        group: list[np.ndarray] = []
        for tag, chunks in sorted(blocks[kind].items()):
            name = names.get((dim, tag), f"group-{tag}")
            if name in table_names:
                raise MeshFormatError(
                    f"{path}: two physical groups of dimension {dim} are both called {name!r}"
                )
            stacked = np.concatenate(chunks)
            table_names.append(name)
            rows.append(stacked)
            group.append(np.full(len(stacked), len(table_names) - 1, dtype=np.int64))
        if not rows:
            return (), np.zeros((0, width), dtype=np.int64), np.zeros(0, dtype=np.int64)
        return tuple(table_names), np.concatenate(rows), np.concatenate(group)

    materials, triangles, triangle_material = table("triangle", 2, 3)
    boundaries, edges, edge_group = table("line", 1, 2)
    if not materials:
        raise MeshFormatError(f"{path}: no triangles, so nothing to solve on")
    if not boundaries:
        raise MeshFormatError(
            f"{path}: no boundary segments, so no name for the weak forms to select on; every "
            "boundary condition of section 5.3.1 is imposed by name"
        )
    return MeshData(
        vertices=vertices,
        triangles=triangles,
        triangle_material=triangle_material,
        materials=materials,
        edges=edges,
        edge_group=edge_group,
        boundaries=boundaries,
    )


def _read_netgen(path: Path) -> MeshData:
    import ngsolve as ngs

    try:
        mesh = ngs.Mesh(str(path))
    except Exception as error:
        raise MeshFormatError(f"netgen could not read {path}: {error}") from error
    return from_ngsolve(mesh)


def from_ngsolve(mesh: Mesh) -> MeshData:
    """Return the arrays and tag maps of an ``ngsolve.Mesh``."""
    import numpy as np

    ngmesh = mesh.ngmesh
    points = np.array([point.p for point in ngmesh.Points()], dtype=np.float64)
    if points.shape[1] > 2 and not bool(
        np.all(np.abs(points[:, 2]) <= TOL_NM)
    ):  # pragma: no cover - 3D mesh in ngsolve adapter
        raise MeshFormatError(
            "this is a three-dimensional mesh; nanopnp solves the (r, z) half-plane (CON-04)"
        )
    vertices = np.ascontiguousarray(points[:, :2])

    elements = list(ngmesh.Elements2D())
    triangles = np.array(
        [[vertex.nr - 1 for vertex in element.vertices] for element in elements], dtype=np.int64
    )
    if triangles.size and triangles.shape[1] != 3:
        raise MeshFormatError("only straight-sided triangles are supported (section 5.2.2)")
    material_names = [ngmesh.GetMaterial(element.index) for element in elements]
    segments = list(ngmesh.Elements1D())
    edges = np.array(
        [[vertex.nr - 1 for vertex in segment.vertices] for segment in segments], dtype=np.int64
    )
    boundary_names = [ngmesh.GetBCName(segment.index - 1) for segment in segments]

    def index(names: list[str]) -> tuple[tuple[str, ...], np.ndarray]:
        table: list[str] = []
        for name in names:
            if name not in table:
                table.append(name)
        return tuple(table), np.array([table.index(name) for name in names], dtype=np.int64)

    materials, triangle_material = index(material_names)
    boundaries, edge_group = index(boundary_names)
    return MeshData(
        vertices=vertices,
        triangles=triangles,
        triangle_material=triangle_material,
        materials=materials,
        edges=edges.reshape(-1, 2),
        edge_group=edge_group,
        boundaries=boundaries,
    )


def to_ngsolve(data: MeshData) -> Mesh:
    """Build an ``ngsolve.Mesh`` from ``data``, names and all."""
    import ngsolve as ngs
    from netgen.meshing import Element1D, Element2D, FaceDescriptor, MeshPoint, Pnt
    from netgen.meshing import Mesh as NetgenMesh

    ngmesh = NetgenMesh(dim=2)
    descriptors = []
    for position, name in enumerate(data.materials, start=1):
        descriptors.append(ngmesh.Add(FaceDescriptor(surfnr=position, domin=position, bc=position)))
        ngmesh.SetMaterial(position, name)
    points = [ngmesh.Add(MeshPoint(Pnt(float(r), float(z), 0.0))) for r, z in data.vertices]
    for triangle, material in zip(data.triangles, data.triangle_material, strict=True):
        ngmesh.Add(
            Element2D(descriptors[int(material)], [points[int(vertex)] for vertex in triangle])
        )
    for position, name in enumerate(data.boundaries, start=1):
        ngmesh.Add(FaceDescriptor(surfnr=position, domin=1, bc=position))
        ngmesh.SetBCName(position - 1, name)
    for edge, group in zip(data.edges, data.edge_group, strict=True):
        ngmesh.Add(Element1D([points[int(edge[0])], points[int(edge[1])]], index=int(group) + 1))
    return ngs.Mesh(ngmesh)


def write_msh41(data: MeshData, path: Path, *, binary: bool = False) -> Path:
    """Write ``data`` as MSH 4.1 at ``path`` and return the path.

    Parameters
    ----------
    binary
        Whether to write the binary encoding; ASCII round-trips float64 exactly.
    """
    import meshio
    import numpy as np

    cells: list[tuple[str, np.ndarray]] = []
    tags: list[np.ndarray] = []
    entities: list[tuple[int, int, np.ndarray]] = []
    tag = 0
    for name in data.materials:
        tag += 1
        rows = data.triangles[data.material_of(name)]
        cells.append(("triangle", rows))
        tags.append(np.full(len(rows), tag, dtype=np.int64))
        entities.append((2, tag, rows))
    for name in data.boundaries:
        tag += 1
        rows = data.edges_of(name)
        cells.append(("line", rows))
        tags.append(np.full(len(rows), tag, dtype=np.int64))
        entities.append((1, tag, rows))

    mesh = meshio.Mesh(
        points=data.vertices,
        cells=cells,
        cell_data={"gmsh:physical": tags, "gmsh:geometrical": [block.copy() for block in tags]},
        point_data={"gmsh:dim_tags": _node_entities(data.vertex_count, entities)},
    )
    meshio.write(str(path), mesh, file_format="gmsh", binary=binary)
    named = [
        (dim, tag, name)
        for (dim, tag, _rows), name in zip(entities, data.materials + data.boundaries, strict=True)
    ]
    _insert_physical_names(path, named)
    return path


def _physical_names_block(named: list[tuple[int, int, str]]) -> bytes:
    lines = [b"$PhysicalNames", str(len(named)).encode("ascii")]
    lines += [f'{dim} {tag} "{name}"'.encode() for dim, tag, name in named]
    lines.append(b"$EndPhysicalNames")
    return b"\n".join(lines) + b"\n"


def _insert_physical_names(path: Path, named: list[tuple[int, int, str]]) -> None:
    raw = path.read_bytes()
    marker = b"$EndMeshFormat\n"
    start = raw.find(marker)
    if start < 0:
        raise MeshFormatError(f"{path}: meshio wrote no $EndMeshFormat, so this is not an MSH file")
    cut = start + len(marker)
    path.write_bytes(raw[:cut] + _physical_names_block(named) + raw[cut:])


def read_physical_names(path: Path) -> dict[tuple[int, int], str]:
    """Return ``{(dimension, tag): name}`` from a file's ``$PhysicalNames`` section."""
    names: dict[tuple[int, int], str] = {}
    with path.open("rb") as handle:
        for raw in handle:
            line = raw.decode("utf-8", errors="replace").strip()
            if line == "$PhysicalNames":
                break
            if line in {"$Nodes", "$Elements"}:
                return names
        else:
            return names
        handle.readline()  # the count; the block ends at its own marker
        for raw in handle:
            line = raw.decode("utf-8", errors="replace").strip()
            if line == "$EndPhysicalNames":
                break
            dimension, tag, quoted = line.split(maxsplit=2)
            names[(int(dimension), int(tag))] = quoted.strip().strip('"')
    return names


def _node_entities(count: int, entities: list[tuple[int, int, np.ndarray]]) -> np.ndarray:
    import numpy as np

    candidates: dict[int, list[tuple[int, int]]] = {}
    members: dict[tuple[int, int], list[int]] = {}
    for dim, tag, rows in entities:
        nodes = [int(node) for node in np.unique(rows)]
        members[(dim, tag)] = nodes
        for node in nodes:
            candidates.setdefault(node, []).append((dim, tag))

    representative: dict[int, tuple[int, int]] = {}

    def augment(entity: tuple[int, int], seen: set[int]) -> bool:
        for node in members[entity]:
            if node in seen:
                continue
            seen.add(node)
            held = representative.get(node)
            if held is None or augment(held, seen):
                representative[node] = entity
                return True
        return False

    for dim, tag, _rows in entities:
        if not augment((dim, tag), set()):
            raise MeshDataError(
                f"no node can be given to the group with tag {tag} in dimension {dim} without "
                "leaving another group with none; this mesh has fewer nodes than groups"
            )

    assigned: dict[int, tuple[int, int]] = {
        node: min(options) for node, options in candidates.items()
    }
    assigned.update(representative)
    orphans = sorted(set(range(count)) - set(assigned))
    if orphans:
        raise MeshDataError(
            f"{len(orphans)} vertices belong to no element (first: {orphans[0]}); a mesh with "
            "unused vertices cannot be written as MSH, every node needing an entity"
        )
    return np.array([assigned[node] for node in range(count)], dtype=np.int64)
