"""The optional Gmsh backend of ADR-002: stage 5's region meshed with the ``gmsh`` API (WP23).

Reached only through stage 6's dispatch on ``numerics.mesh.backend: gmsh``
(:func:`nanopnp.mesh.generate.generate`), so ``gmsh`` is imported at the top:
the default path never imports this module (CON-10), and a missing extra is
refused there, naming it. The ``gmsh`` API is called directly, never through
pygmsh (CON-12, section 5.2.2).

**The region is stage 5's, not Gmsh's own** (WP23 D1, D2). The glued, named
netgen shape is read into a :class:`~nanopnp.geometry.region.RegionGraph` and
built in Gmsh's built-in ``geo`` kernel from the shape's own coordinates: a
point per vertex, a line or a circle arc per edge, one counter-clockwise curve
loop and plane surface per domain, and one physical group per name. Faces share
curves, so the mesh is conformal by construction, and every region vertex is a
mesh node.

**The size field states what netgen does implicitly** (the section 5.2.2 NOTE on
the Gmsh backend's size field; WP23 D3, D4). Every source is a ``Distance`` and
``Threshold`` pair giving ``h(d) = h_s + g d``, with ``g`` netgen's
:data:`~nanopnp.mesh.sizing.GRADING`, capped at the global size:

- each sized boundary of the table, at its size;
- the boundary of each sized domain at the domain's size, the domain held to it
  inside by a ``Constant`` field; the membrane is one of these, at its own
  thickness, unscaled, because that is a feature of the geometry and not an
  entry of the table;
- each vertex whose shortest incident curve is shorter than the smallest target
  of its incident curves, at that curve's length.

The background field is their ``Min``. Without the domain boundaries, the
reference fixture's minimum gamma is 0.3143 against VER-10's 0.3; without the
short curves and the graded membrane it fails at ``size_scale`` 2 and 4 (WP23
plan, Design section 2).

**Process hygiene** (WP23 D6). A session this module opens reads no
configuration file and installs no SIGINT handler, and it is finalised on the
way out. In a session already open, the mesh is built in a model of its own,
every option set here is restored, and the model is removed. Gmsh's messages go
to :mod:`logging` at DEBUG, and never to standard output, which IF-02 reserves.
"""

from __future__ import annotations

import itertools
import logging
import math
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import TYPE_CHECKING

import gmsh

from nanopnp.mesh.adapter import MeshData
from nanopnp.mesh.sizing import (
    GMSH_ALGORITHM,
    GMSH_SMOOTHING,
    GRADING,
    SizeTable,
    domain_size,
    edge_size,
)

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

    from nanopnp.geometry.region import RegionGraph

logger = logging.getLogger(__name__)

_TRIANGLE = 2
"""Gmsh's element type for a three-node triangle."""

_LINE = 1
"""Gmsh's element type for a two-node line."""

_SAMPLING_MARGIN = 2
"""Extra samples per curve above ``ceil(L / h)`` on each ``Distance`` field (WP23 D3)."""

_MODEL_IDS = itertools.count()
"""Numbers the models this module adds, so a session already open never sees a clash."""


class GmshMeshingError(RuntimeError):
    """Gmsh refused the region or failed to mesh it; its own log is quoted (QR-12)."""


class GmshInitializationError(RuntimeError):
    """Gmsh failed to initialise (REV-37)."""


def version() -> str:
    """Return the installed Gmsh's version, which the manifest records beside the key (D8)."""
    return str(gmsh.__version__)


def _options(sizes: SizeTable) -> dict[str, float]:
    """Return every option the mesh depends on, set explicitly (WP23 D5, D6).

    Explicit even where the value is Gmsh's default, so that a session opened
    elsewhere with other values meshes the same region to the same mesh.
    """
    return {
        "General.Terminal": 0,
        "General.Verbosity": 5,
        "General.NumThreads": 1,
        "Mesh.MaxNumThreads2D": 1,
        "Mesh.Algorithm": GMSH_ALGORITHM,
        "Mesh.Smoothing": GMSH_SMOOTHING,
        "Mesh.ElementOrder": 1,
        "Mesh.RecombineAll": 0,
        "Mesh.MeshSizeFactor": 1.0,
        "Mesh.MeshSizeMin": 0.0,
        "Mesh.MeshSizeMax": sizes.global_nm,
        "Mesh.MeshSizeFromPoints": 0,
        "Mesh.MeshSizeFromCurvature": 0,
        "Mesh.MeshSizeExtendFromBoundary": 0,
        # Gmsh's defaults, pinned so a session opened elsewhere cannot move the
        # mesh under an unchanged key: points per curve and per circle, the
        # perturbation of the Delaunay kernel, and the geometry's tolerance.
        "Mesh.MeshSizeFromParametricPoints": 0,
        "Mesh.MinimumCurvePoints": 3,
        "Mesh.MinimumCirclePoints": 7,
        "Mesh.RandomFactor": 1e-9,
        "Mesh.LcIntegrationPrecision": 1e-9,
        "Geometry.Tolerance": 1e-8,
        "Geometry.AutoCoherence": 1,
    }


@contextmanager
def _session(options: Mapping[str, float]) -> Iterator[None]:
    """Open a session, or borrow the one open, in a model of this call's own.

    On exit Gmsh's log is forwarded to :mod:`logging`, the model is removed,
    every option is restored, the previous model is made current again, and a
    session this call opened is finalised.
    """
    from collections.abc import Callable

    opened = not gmsh.isInitialized()
    if opened:
        try:
            gmsh.initialize(readConfigFiles=False, interruptible=False)
        except Exception as error:
            raise GmshInitializationError(f"gmsh.initialize failed: {error}") from error
    # Silence the terminal before anything else can print.
    previous_terminal = gmsh.option.getNumber("General.Terminal")
    gmsh.option.setNumber("General.Terminal", 0)
    previous_model = None if opened else gmsh.model.getCurrent()
    saved = {name: gmsh.option.getNumber(name) for name in options}
    saved["General.Terminal"] = previous_terminal
    messages: list[str] = []
    if opened:
        gmsh.logger.start()

    cleanup_steps: list[Callable[[], None]] = []
    if opened:
        cleanup_steps.append(lambda: messages.extend(gmsh.logger.get()))
    cleanup_steps.append(lambda: gmsh.model.remove())
    if opened:
        cleanup_steps.append(lambda: gmsh.logger.stop())

        def _log_messages() -> None:
            for message in messages:
                logger.debug("gmsh: %s", message)

        cleanup_steps.append(_log_messages)
        cleanup_steps.append(lambda: gmsh.finalize())
    else:

        def _restore_options() -> None:
            for name, value in saved.items():
                gmsh.option.setNumber(name, value)

        cleanup_steps.append(_restore_options)
        if previous_model is not None:
            cleanup_steps.append(lambda: gmsh.model.setCurrent(previous_model))

    propagating: BaseException | None = None
    try:
        for name, value in options.items():
            gmsh.option.setNumber(name, value)
        gmsh.model.add(f"nanopnp-region-{next(_MODEL_IDS)}")
        try:
            yield
        except BaseException as error:
            propagating = error
            raise
    finally:
        first_failure: BaseException | None = None
        for step in cleanup_steps:
            try:
                step()
            except BaseException as cleanup_error:
                if propagating is not None:
                    logger.warning("Gmsh session cleanup failed: %s", cleanup_error)
                    propagating.add_note(f"Gmsh session cleanup failed: {cleanup_error}")
                else:
                    if first_failure is None:
                        first_failure = cleanup_error
                    else:
                        logger.warning("Gmsh session cleanup failed: %s", cleanup_error)
                        first_failure.add_note(f"Gmsh session cleanup failed: {cleanup_error}")
        if propagating is None and first_failure is not None:
            raise first_failure


def _build(graph: RegionGraph) -> tuple[list[int], list[int], dict[str, int]]:
    """Build the graph in the ``geo`` kernel; return the point, curve and surface tags."""
    geo = gmsh.model.geo
    points = [geo.addPoint(r, z, 0.0) for r, z in graph.vertices]
    centre = geo.addPoint(0.0, 0.0, 0.0)
    curves = [
        geo.addLine(points[edge.start], points[edge.end])
        if edge.kind == "segment"
        else geo.addCircleArc(points[edge.start], centre, points[edge.end])
        for edge in graph.edges
    ]
    surfaces: dict[str, int] = {}
    for name in sorted(graph.faces):
        signed = [-curves[~index] if index < 0 else curves[index] for index in graph.faces[name]]
        surfaces[name] = geo.addPlaneSurface([geo.addCurveLoop(signed)])
    geo.synchronize()

    names = sorted({edge.name for edge in graph.edges})
    for name in names:
        tags = [curves[i] for i, edge in enumerate(graph.edges) if edge.name == name]
        gmsh.model.setPhysicalName(1, gmsh.model.addPhysicalGroup(1, tags), name)
    for name, surface in surfaces.items():
        gmsh.model.setPhysicalName(2, gmsh.model.addPhysicalGroup(2, [surface]), name)
    return points, curves, surfaces


def _graded_curves(curves: list[int], lengths: list[float], size: float, global_nm: float) -> int:
    """Add a source on ``curves`` at ``size``, graded at ``g`` to the global size."""
    field = gmsh.model.mesh.field
    distance = field.add("Distance")
    field.setNumbers(distance, "CurvesList", curves)
    field.setNumber(distance, "Sampling", math.ceil(max(lengths) / size) + _SAMPLING_MARGIN)
    return _threshold(distance, size, global_nm)


def _graded_points(points: list[int], size: float, global_nm: float) -> int:
    """Add a source on ``points`` at ``size``, graded at ``g`` to the global size."""
    field = gmsh.model.mesh.field
    distance = field.add("Distance")
    field.setNumbers(distance, "PointsList", points)
    return _threshold(distance, size, global_nm)


def _threshold(distance: int, size: float, global_nm: float) -> int:
    """Return ``h(d) = size + g d``, capped at the global size."""
    field = gmsh.model.mesh.field
    threshold = int(field.add("Threshold"))
    field.setNumber(threshold, "InField", distance)
    field.setNumber(threshold, "SizeMin", size)
    field.setNumber(threshold, "SizeMax", global_nm)
    field.setNumber(threshold, "DistMin", 0.0)
    field.setNumber(threshold, "DistMax", (global_nm - size) / GRADING)
    return threshold


def _constant(surface: int, size: float, global_nm: float) -> int:
    """Hold ``surface`` to ``size`` inside, its boundary included."""
    field = gmsh.model.mesh.field
    constant = int(field.add("Constant"))
    field.setNumbers(constant, "SurfacesList", [surface])
    field.setNumber(constant, "VIn", size)
    field.setNumber(constant, "VOut", global_nm)
    field.setNumber(constant, "IncludeBoundary", 1)
    return constant


def size_targets(
    graph: RegionGraph,
    wall_h_nm: float | None,
    sizes: SizeTable,
    *,
    membrane_thickness_nm: float,
    axis_extent_nm: tuple[float, float],
) -> tuple[list[float | None], dict[str, float]]:
    """Return each edge's own size and each sized domain's size (WP23 D3, D4 ii).

    The edges through :func:`~nanopnp.mesh.sizing.edge_size`, the classification
    netgen's sizes use. The domains through
    :func:`~nanopnp.mesh.sizing.domain_size`, and the membrane at its thickness,
    not multiplied by ``size_scale``.
    """
    own = []
    for edge in graph.edges:
        z_mid = 0.5 * (graph.vertices[edge.start][1] + graph.vertices[edge.end][1])
        own.append(
            edge_size(
                edge.name, z_mid, wall_h_nm=wall_h_nm, axis_extent_nm=axis_extent_nm, sizes=sizes
            )
        )
    domains = {
        name: size
        for name in graph.faces
        if (size := domain_size(name, sizes, wall_h_nm=wall_h_nm)) is not None
    }
    domains["membrane"] = membrane_thickness_nm
    return own, domains


def short_curve_sources(
    graph: RegionGraph, own: list[float | None], domains: Mapping[str, float], global_nm: float
) -> dict[float, list[int]]:
    """Return the vertices D4 (i) restricts, grouped by the length they are restricted to.

    A curve's target is the smallest of its own size, the sizes of the domains
    it bounds and the global size. A vertex whose shortest incident curve is
    shorter than the smallest target of its incident curves is a source at that
    curve's length, which is what netgen's restriction by edge length does
    without being asked (the section 5.2.2 NOTE on the Gmsh backend's size
    field).
    """
    target = [global_nm if size is None else min(size, global_nm) for size in own]
    for name, loop in graph.faces.items():
        size = domains.get(name)
        if size is None:
            continue
        for signed in loop:
            index = ~signed if signed < 0 else signed
            target[index] = min(target[index], size)
    shortest: dict[int, float] = {}
    smallest: dict[int, float] = {}
    for index, edge in enumerate(graph.edges):
        length = graph.length(index)
        for vertex in (edge.start, edge.end):
            shortest[vertex] = min(shortest.get(vertex, math.inf), length)
            smallest[vertex] = min(smallest.get(vertex, math.inf), target[index])
    grouped: dict[float, list[int]] = {}
    for vertex in sorted(shortest):
        if shortest[vertex] < smallest[vertex]:
            grouped.setdefault(shortest[vertex], []).append(vertex)
    return grouped


def _size_field(
    graph: RegionGraph,
    points: list[int],
    curves: list[int],
    surfaces: Mapping[str, int],
    own: list[float | None],
    domains: Mapping[str, float],
    global_nm: float,
) -> int:
    """Add every D3-D4 source and return the ``Min`` field over them."""
    components: list[int] = []
    by_size: dict[float, list[int]] = {}
    for index, size in enumerate(own):
        if size is not None and size < global_nm:
            by_size.setdefault(size, []).append(index)
    for name in sorted(domains):
        size = domains[name]
        if name not in graph.faces or not size < global_nm:
            continue
        loop = sorted({~signed if signed < 0 else signed for signed in graph.faces[name]})
        components.append(
            _graded_curves(
                [curves[i] for i in loop], [graph.length(i) for i in loop], size, global_nm
            )
        )
        components.append(_constant(surfaces[name], size, global_nm))
    for size, indices in sorted(by_size.items()):
        components.append(
            _graded_curves(
                [curves[i] for i in indices], [graph.length(i) for i in indices], size, global_nm
            )
        )
    for length, vertices in sorted(short_curve_sources(graph, own, domains, global_nm).items()):
        components.append(_graded_points([points[v] for v in vertices], length, global_nm))
    field = gmsh.model.mesh.field
    background = int(field.add("Min"))
    field.setNumbers(background, "FieldsList", components)
    return background


def _to_mesh_data() -> MeshData:
    """Return the current model's mesh as a :class:`MeshData`, named by physical group (D7).

    Only the nodes an element uses are kept, in Gmsh's node order; the arc
    centre is a model point and no element's node.
    """
    import numpy as np

    tags, coordinates, _ = gmsh.model.mesh.getNodes()
    tags = np.asarray(tags, dtype=np.int64)
    xy = np.asarray(coordinates, dtype=np.float64).reshape(-1, 3)[:, :2]
    position = np.full(int(tags.max()) + 1, -1, dtype=np.int64)
    position[tags] = np.arange(len(tags))

    def blocks(dimension: int, expected: int) -> tuple[tuple[str, ...], list[np.ndarray]]:
        names: list[str] = []
        connectivity: list[np.ndarray] = []
        width = 3 if dimension == 2 else 2
        for _, group in gmsh.model.getPhysicalGroups(dimension):
            names.append(gmsh.model.getPhysicalName(dimension, group))
            found = []
            for entity in gmsh.model.getEntitiesForPhysicalGroup(dimension, group):
                types, _, nodes = gmsh.model.mesh.getElements(dimension, entity)
                for kind, block in zip(types, nodes, strict=True):
                    if kind != expected:
                        raise GmshMeshingError(
                            f"gmsh wrote element type {kind} in {names[-1]!r}, where only type "
                            f"{expected} is meshed (section 5.2.2: first-order triangles)"
                        )
                    found.append(position[np.asarray(block, dtype=np.int64)].reshape(-1, width))
            connectivity.append(np.concatenate(found) if found else np.empty((0, width), int))
        return tuple(names), connectivity

    materials, triangle_blocks = blocks(2, _TRIANGLE)
    boundaries, edge_blocks = blocks(1, _LINE)
    triangles = np.concatenate(triangle_blocks)
    edges = np.concatenate(edge_blocks)
    used = np.unique(np.concatenate([triangles.ravel(), edges.ravel()]))
    renumber = np.full(len(tags), -1, dtype=np.int64)
    renumber[used] = np.arange(len(used))
    return MeshData(
        vertices=xy[used],
        triangles=renumber[triangles],
        triangle_material=np.repeat(
            np.arange(len(materials)), [len(block) for block in triangle_blocks]
        ),
        materials=materials,
        edges=renumber[edges],
        edge_group=np.repeat(np.arange(len(boundaries)), [len(block) for block in edge_blocks]),
        boundaries=boundaries,
    )


def mesh_region(
    graph: RegionGraph,
    wall_h_nm: float | None,
    sizes: SizeTable,
    *,
    membrane_thickness_nm: float,
    axis_extent_nm: tuple[float, float],
) -> MeshData:
    """Mesh stage 5's region with Gmsh under the section 5.2.2 table (WP23 D2-D7).

    Parameters
    ----------
    graph
        The region, as :func:`~nanopnp.geometry.region.region_graph` read it.
    wall_h_nm
        The resolved wall size; ``None`` leaves the wall to the other fields.
    sizes
        The table, ``size_scale`` applied.
    membrane_thickness_nm
        The membrane's size (D4 ii), unscaled.
    axis_extent_nm
        The pore's axial extent, over which the axis-in-pore size applies.

    Returns
    -------
    MeshData
        Named by the region's physical groups: the materials are its domains and
        the boundaries its edge names, each sorted. Not yet gated: stage 6 writes
        it and reads it back through the gates as netgen's mesh is (D7).

    Raises
    ------
    GmshMeshingError
        If Gmsh raised, quoting the error and the last of its log.
    """
    own, domains = size_targets(
        graph,
        wall_h_nm,
        sizes,
        membrane_thickness_nm=membrane_thickness_nm,
        axis_extent_nm=axis_extent_nm,
    )
    with _session(_options(sizes)):
        try:
            points, curves, surfaces = _build(graph)
            background = _size_field(graph, points, curves, surfaces, own, domains, sizes.global_nm)
            gmsh.model.mesh.field.setAsBackgroundMesh(background)
            gmsh.model.mesh.generate(2)
            data = _to_mesh_data()
        except Exception as error:
            tail = "; ".join(gmsh.logger.get()[-5:]) or "no log"
            raise GmshMeshingError(
                f"gmsh {version()} failed to mesh the region: {error}. Its log ends: {tail}"
            ) from error
    logger.info(
        "gmsh %s: %d triangles over %d vertices", version(), data.element_count, len(data.vertices)
    )
    return data
