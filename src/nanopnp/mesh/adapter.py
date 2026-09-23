"""One in-memory mesh, and every way in and out of it (IF-06, section 5.1).

A mesh reaches the solver from three places — netgen's own ``.vol``, an MSH 4.1
file written by somebody else's mesher, and the in-process geometries of
:mod:`nanopnp.mesh.primitives` — and exactly one of those three is checked by
anything today. :class:`MeshData` is the seam that makes one route out of the
three: every reader lands here, every gate runs here, and nothing downstream of
this module knows which mesher produced the arrays.

**MSH 4.1 is the archival format** (IF-06), written and read through ``meshio``.
netgen's ``read_gmsh.ReadGmsh`` is an MSH **2.2** parser — handed a 4.1 file it
dies in ``int()`` on the entity-block header [tested] — so the reader that
writes the archival format cannot be the one netgen ships, and the ingestion
path never imports it (CON-10 keeps ``gmsh`` off the default path for the same
reason, by a different argument).

meshio's 4.1 writer needs entity bookkeeping that a tagged FE mesh does not
carry, and gets it wrong quietly in two distinguishable ways [both tested,
meshio 5.3.5]:

*One cell block is one entity.* ``_write_elements`` takes the **first**
``gmsh:geometrical`` tag of a block and writes the whole block under it, so four
boundary groups packed into a single ``line`` block come back with all four
physical tags equal to the first — three no-flux walls silently becoming one.
:func:`write_msh41` therefore emits one cell block per (group, element type).

*An entity that owns no node is never written.* ``_write_entities`` builds
``$Entities`` from ``np.unique(point_data["gmsh:dim_tags"])`` alone, so an entity
a cell block references but no node claims is omitted, and reading the file back
raises ``KeyError`` — after the write reported success. :func:`_node_entities`
therefore assigns each node its lowest-dimensional entity and then repairs any
group left with none.

**The content hash is taken over a canonical form, not over the arrays as
supplied.** meshio's 4.1 reader returns nodes grouped by entity and cell blocks
in entity order, so a write/read round trip permutes both [tested]; hashing the
arrays in file order would make a mesh differ from itself. :meth:`MeshData.canonical`
sorts the vertices by ``(r, z)``, renumbers the connectivity into that order,
and sorts the elements by group name, which is invariant under everything a
round trip does and changes the moment an edge moves group.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.core.hashing import content_hash
from nanopnp.core.typing import Mesh

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

_LOGGER = logging.getLogger(__name__)

MESH_SCHEMA = "nanopnp/mesh/v1"
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

_SUFFIXES: dict[str, str] = {".msh": "gmsh", ".vol": "netgen", ".vol.gz": "netgen"}
"""Filename suffixes recognised when ``inputs.mesh.format`` is absent."""


class MeshFormatError(ValueError):
    """A mesh file cannot be read: unknown format, or unreadable contents."""


class MeshDataError(ValueError):
    """A :class:`MeshData` is not a well-formed tagged mesh."""


def detect_format(path: Path, declared: str | None = None) -> str:
    """Return the reader route for ``path``, ``"gmsh"`` or ``"netgen"``.

    Parameters
    ----------
    path
        The mesh file. Only its name is inspected.
    declared
        ``inputs.mesh.format`` when the case gives one; it wins over the
        suffix, so a file named without one is still readable.

    Raises
    ------
    MeshFormatError
        If the declared format is not one of :data:`FORMATS`, or no format was
        declared and the suffix is not one of :data:`_SUFFIXES`. The message
        lists what is accepted, because the fix is one word in the case file.
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
    vertices
        ``(n, 2)`` float64 array of ``(r, z)`` coordinates in nm.
    triangles
        ``(m, 3)`` int64 array of vertex indices, counter-clockwise for a
        positively oriented element (:mod:`nanopnp.mesh.quality` gates the sign).
    triangle_material
        ``(m,)`` int64 array of indices into :attr:`materials`.
    materials
        Domain names, in file order. The index is positional.
    edges
        ``(k, 2)`` int64 array of vertex indices: the boundary segments.
    edge_group
        ``(k,)`` int64 array of indices into :attr:`boundaries`.
    boundaries
        Boundary group names, in file order.

    Notes
    -----
    Names are whatever the file said. Mapping them onto the vocabulary the weak
    forms select on is :mod:`nanopnp.mesh.ingest`'s job and happens exactly once,
    so that a name in a :class:`MeshData` is never half-translated.
    """

    vertices: np.ndarray
    triangles: np.ndarray
    triangle_material: np.ndarray
    materials: tuple[str, ...]
    edges: np.ndarray
    edge_group: np.ndarray
    boundaries: tuple[str, ...]

    def __post_init__(self) -> None:
        """Normalise the array dtypes and reject a malformed mesh.

        The dtypes are normalised rather than merely checked because they reach
        the content hash: :func:`nanopnp.core.hashing.canonical` digests an array
        as dtype, shape and bytes, so the same mesh read as ``int32`` and as
        ``int64`` would otherwise be two meshes.
        """
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
        """Set ``r`` to exactly zero wherever it is within :data:`TOL_NM` of it.

        Netgen's OCC kernel puts axis vertices at ``r = -1.5e-15`` nm and at
        ``+7e-16`` nm rather than at zero [tested], which is round-off in the
        rotation the revolve applies and not a mesh that crosses the axis. Two
        things need it snapped. The CON-04 gate in
        :func:`nanopnp.mesh.quality.check_radii` asks for ``r >= 0`` exactly, and
        must go on asking exactly, because the failure it is there to catch — a
        mesh mirrored about the axis — is a *sign* error, and a gate with a
        tolerance wide enough to pass round-off is a gate that has to justify its
        width. And the content hash digests the coordinate bytes, so two runs of
        the same mesher that differ only in that round-off would otherwise be two
        meshes and two cache entries (section 5.3.2).

        Snapped in the constructor rather than in the reader so that it holds for
        every route into a :class:`MeshData`, the meshers' own included.
        """
        import numpy as np

        radii = self.vertices[:, 0]
        snapped = np.where(np.abs(radii) < TOL_NM, 0.0, radii)
        if not np.array_equal(snapped, radii):
            vertices = self.vertices.copy()
            vertices[:, 0] = snapped
            object.__setattr__(self, "vertices", vertices)

    def _validate(self) -> None:
        """Raise :class:`MeshDataError` unless every array and table lines up."""
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
        """Return the boolean mask of triangles carrying the material ``name``.

        Raises
        ------
        KeyError
            If the mesh has no such material; the message lists the ones it has.
        """
        if name not in self.materials:
            raise KeyError(f"no material {name!r}; the mesh carries {list(self.materials)}")
        mask: np.ndarray = self.triangle_material == self.materials.index(name)
        return mask

    def edges_of(self, name: str) -> np.ndarray:
        """Return the ``(k, 2)`` edges of the boundary group ``name``.

        Raises
        ------
        KeyError
            If the mesh has no such boundary group.
        """
        if name not in self.boundaries:
            raise KeyError(f"no boundary group {name!r}; the mesh carries {list(self.boundaries)}")
        rows: np.ndarray = self.edges[self.edge_group == self.boundaries.index(name)]
        return rows

    def renamed(
        self, *, materials: dict[str, str] | None = None, boundaries: dict[str, str] | None = None
    ) -> MeshData:
        """Return this mesh with its name tables mapped through ``materials``/``boundaries``.

        Many-to-one is the expected case — a CAD export splits one physical wall
        into several curves — so groups that map onto the same name are merged
        into one index and the element tags follow.

        Parameters
        ----------
        materials, boundaries
            ``{name in this mesh: new name}``. A name absent from the mapping is
            kept as it is.
        """
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

        Vertices sorted by ``(r, z)`` and the connectivity renumbered into that
        order; each triangle rotated to start at its lowest vertex, which keeps
        its orientation and so keeps an inverted element inverted; each edge's
        endpoints sorted, a boundary segment having no direction; elements sorted
        by group name and then by connectivity; and both name tables sorted.

        Invariant under everything an MSH round trip does to a mesh — which
        permutes the nodes into entity order and the cell blocks with them — and
        not invariant under anything that changes the mesh, including one edge
        moving from one boundary group to another.

        Raises
        ------
        MeshDataError
            If two vertices share a location, which leaves the sorted order
            ambiguous and means the mesh is degenerate anyway.
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
        """The sha256 of this mesh's canonical form, as 64 hex characters.

        Over the geometry and the tagging, never over the file's bytes: a mesh
        meshio rewrote with a different header is the same mesh and hits the
        store, and a mesh whose ``wall`` group gained one edge is a different one
        and misses (section 5.3.2).
        """
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
        """Return the counts and name tables a manifest records (FR-25).

        The triangle count is called ``elements`` rather than ``triangles`` so
        that this group and :meth:`nanopnp.mesh.quality.QualityReport.summary`
        and :func:`nanopnp.solve.continuation.mesh_report` all name it the same
        thing; a manifest whose two mesh counts have different keys is one a
        reader has to be told about.
        """
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

    Parameters
    ----------
    path
        The mesh file.
    format
        ``inputs.mesh.format`` when the case gives one; otherwise the format is
        taken from the suffix. Shadows the builtin because the case field is
        called ``format`` and a second spelling here would be one more thing to
        remember.

    Returns
    -------
    MeshData
        The mesh with the names the file gave it, untranslated.

    Raises
    ------
    MeshFormatError
        If the format is unknown, the file is not a two-dimensional ``(r, z)``
        mesh, or the reader refuses it.
    """
    route = detect_format(path, format)
    if not path.is_file():
        raise MeshFormatError(f"no mesh file at {path}")
    if route == "gmsh":
        return _read_meshio(path)
    return _read_netgen(path)


def _read_meshio(path: Path) -> MeshData:
    """Read an MSH file through meshio, one group per distinct physical tag."""
    import meshio
    import numpy as np

    try:
        # The format is named, not left to the suffix: meshio maps ``.msh`` to
        # ANSYS *and* gmsh, tries ANSYS first, and prints that reader's refusal
        # -- an empty line -- to standard output, which the CLI reserves for its
        # result (IF-02 NOTE) [tested].
        mesh = meshio.read(str(path), file_format="gmsh")
    except Exception as error:  # meshio raises a dozen unrelated types
        raise MeshFormatError(f"meshio could not read {path}: {error}") from error

    points = np.asarray(mesh.points, dtype=np.float64)
    if points.ndim != 2 or points.shape[1] < 2:
        raise MeshFormatError(f"{path}: expected point coordinates, got shape {points.shape}")
    if points.shape[1] > 2 and bool(np.any(np.abs(points[:, 2]) > TOL_NM)):
        raise MeshFormatError(
            f"{path}: this is a three-dimensional mesh; nanopnp solves the (r, z) half-plane "
            "and reads a mesh whose third coordinate is zero throughout (CON-04)"
        )
    vertices = np.ascontiguousarray(points[:, :2])

    names = read_physical_names(path)
    physical = mesh.cell_data.get("gmsh:physical")
    blocks: dict[str, dict[int, list[np.ndarray]]] = {"triangle": {}, "line": {}}
    for position, block in enumerate(mesh.cells):
        if block.type not in blocks:
            _LOGGER.debug("ignoring %d %s cells in %s", len(block.data), block.type, path.name)
            continue
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
    """Read a netgen ``.vol`` (or ``.vol.gz``) through NGSolve."""
    import ngsolve as ngs

    try:
        mesh = ngs.Mesh(str(path))
    except Exception as error:
        raise MeshFormatError(f"netgen could not read {path}: {error}") from error
    return from_ngsolve(mesh)


def from_ngsolve(mesh: Mesh) -> MeshData:
    """Return the arrays and tag maps of an ``ngsolve.Mesh``.

    Reads the underlying ``netgen`` mesh rather than the NGSolve wrapper, because
    that is where the name tables live. ``el.vertices[i].nr`` is **1-based**
    there, as are ``Element2D.index`` into ``GetMaterial`` and ``Element1D.index``
    into ``GetBCName(index - 1)`` [tested]; :func:`to_ngsolve` runs the same two
    conventions in the opposite direction.

    Several geometric edges commonly carry the same boundary name — an OCC face
    with four ``cis`` edges gives four descriptors — and they merge here into one
    group, which is what the forms already see: NGSolve selects on the name.
    """
    import numpy as np

    ngmesh = mesh.ngmesh
    points = np.array([point.p for point in ngmesh.Points()], dtype=np.float64)
    if points.shape[1] > 2 and bool(np.any(np.abs(points[:, 2]) > TOL_NM)):
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
    """Build an ``ngsolve.Mesh`` from ``data``, names and all.

    One ``FaceDescriptor`` per material carries the domain names; one per
    boundary group carries the boundary names, through ``SetBCName``, which is
    **0-based** where ``Element1D(index=...)`` is **1-based**. Getting that pair
    wrong shifts every boundary name by one — a mesh where ``wall`` is the axis,
    and nothing raises.

    The route exists because an ingested mesh has no OCC geometry to regenerate
    itself from: the arrays are all there is.
    """
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
    """Write ``data`` as MSH 4.1, the archival mesh format (IF-06), and return the path.

    Parameters
    ----------
    data
        The tagged mesh.
    path
        Destination; its parent must exist.
    binary
        Whether to write the binary encoding. ASCII round-trips float64 exactly
        [tested], so this buys size and nothing else.

    Notes
    -----
    One cell block per group and one entity per block, because meshio writes a
    whole block under the *first* geometrical tag it carries; every entity owns
    at least one node, because meshio builds ``$Entities`` from the node tags
    alone and omits an entity no node claims — which makes the file unreadable
    by the reader that wrote it, after a write that reported success.

    ``$PhysicalNames`` is written here rather than by meshio. meshio keys
    ``field_data`` by name, and gmsh keys physical names by ``(dimension, tag)``:
    a mesh whose ``cis`` reservoir is a domain *and* whose ``cis`` electrode is a
    boundary — which is what :mod:`nanopnp.mesh.primitives` builds and what the
    section 5.3.1 vocabulary asks for — loses one of the two in that dict, and
    the name comes back as ``group-3`` [tested]. Only MSH 4.1 is written: netgen's
    own reader is a 2.2 parser and its 2-D path is unsound besides (see
    :func:`_read_meshio`), so a 2.2 file would exist for no reader that wants it.
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
    """Return the ``$PhysicalNames`` section naming every ``(dimension, tag)``."""
    lines = [b"$PhysicalNames", str(len(named)).encode("ascii")]
    lines += [f'{dim} {tag} "{name}"'.encode() for dim, tag, name in named]
    lines.append(b"$EndPhysicalNames")
    return b"\n".join(lines) + b"\n"


def _insert_physical_names(path: Path, named: list[tuple[int, int, str]]) -> None:
    """Put our own ``$PhysicalNames`` section into a file meshio has just written.

    The section is ASCII in both the ASCII and the binary encodings and sits
    between ``$EndMeshFormat`` and ``$Entities``, so this is a byte splice and
    not a re-serialisation.

    Raises
    ------
    MeshFormatError
        If the file has no ``$EndMeshFormat``, which would mean meshio wrote
        something that is not an MSH file.
    """
    raw = path.read_bytes()
    marker = b"$EndMeshFormat\n"
    start = raw.find(marker)
    if start < 0:
        raise MeshFormatError(f"{path}: meshio wrote no $EndMeshFormat, so this is not an MSH file")
    cut = start + len(marker)
    path.write_bytes(raw[:cut] + _physical_names_block(named) + raw[cut:])


def read_physical_names(path: Path) -> dict[tuple[int, int], str]:
    """Return ``{(dimension, tag): name}`` from a file's ``$PhysicalNames`` section.

    Read here rather than taken from ``meshio.Mesh.field_data``, which is keyed by
    name and so cannot carry the same name in two dimensions — and the section
    5.3.1 vocabulary uses ``cis``, ``trans``, ``membrane`` and ``analyte`` as both
    a domain name and a boundary name.

    An empty mapping is a valid answer: a mesh may carry physical tags and no
    names at all, and :func:`_read_meshio` then calls its groups ``group-<tag>``,
    which the ingestion gate quotes back as unclaimed.
    """
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
    """Return the ``(dim, tag)`` entity of every node, covering every entity.

    meshio builds ``$Entities`` from these tags alone, so an entity no node
    claims is dropped from the file and reading it back raises ``KeyError`` —
    after a write that reported success [tested]. Every entity must therefore be
    given a node of its own, and on a mesh whose every boundary node is shared
    between two groups (a closed loop of named edges: the common case, not a
    contrived one) a greedy assignment cannot always find one. Choosing the
    representatives is a bipartite matching, so it is done as one, by augmenting
    paths; the nodes left over then take their lowest-dimensional entity, which
    is gmsh's own convention.

    Raises
    ------
    MeshDataError
        If no system of distinct representatives exists, which means some set of
        groups touches fewer nodes than it has groups, or if a vertex belongs to
        no element at all.
    """
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
        """Claim a node for ``entity``, displacing a claim that can move."""
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
