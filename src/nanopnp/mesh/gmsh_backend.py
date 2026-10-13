"""The optional Gmsh backend of ADR-002: stage 5's region meshed with the ``gmsh`` API (WP23)."""

from __future__ import annotations

import itertools
import logging
import math
from collections.abc import Callable, Iterable, Iterator, Mapping
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
    """Gmsh refused the region or failed to mesh it; its own log is quoted."""


class GmshInitialisationError(RuntimeError):
    """Gmsh failed to initialise."""


def version() -> str:
    """Return the installed Gmsh's version, which the manifest records beside the key."""
    return str(gmsh.__version__)


def _options(sizes: SizeTable) -> dict[str, float]:
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
        # Pinned so a session opened elsewhere cannot move the mesh under an unchanged key.
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
    opened = not gmsh.isInitialized()
    if opened:
        try:
            gmsh.initialize(readConfigFiles=False, interruptible=False)
        except Exception as error:
            raise GmshInitialisationError(f"gmsh.initialize failed: {error}") from error
    undo: list[Callable[[], None]] = []
    messages: list[str] = []
    propagating: BaseException | None = None
    try:
        if opened:
            undo.append(lambda: gmsh.finalize())
        saved = {"General.Terminal": gmsh.option.getNumber("General.Terminal")}
        if not opened:
            undo.append(lambda: _restore_options(saved))
        gmsh.option.setNumber("General.Terminal", 0)
        if opened:
            # A borrowed session's logger is the caller's.
            gmsh.logger.start()
            undo.append(lambda: _forward(messages))
            undo.append(lambda: gmsh.logger.stop())
        else:
            previous_model = gmsh.model.getCurrent()
            undo.append(lambda: gmsh.model.setCurrent(previous_model))
            saved.update({name: gmsh.option.getNumber(name) for name in options})
        for name, value in options.items():
            gmsh.option.setNumber(name, value)
        gmsh.model.add(f"nanopnp-region-{next(_MODEL_IDS)}")
        undo.append(lambda: gmsh.model.remove())
        if opened:
            undo.append(lambda: messages.extend(gmsh.logger.get()))
        yield
    except BaseException as error:
        propagating = error
        raise
    finally:
        _undo(reversed(undo), propagating)


def _restore_options(saved: Mapping[str, float]) -> None:
    for name, value in saved.items():
        gmsh.option.setNumber(name, value)


def _forward(messages: list[str]) -> None:
    for message in messages:
        logger.debug("gmsh: %s", message)


def _undo(steps: Iterable[Callable[[], None]], propagating: BaseException | None) -> None:
    first: BaseException | None = None
    for step in steps:
        try:
            step()
        except BaseException as error:
            if propagating is None and first is None:
                first = error
                continue
            logger.warning("Gmsh session cleanup failed: %s", error)
            target = propagating if propagating is not None else first
            if target is not None:
                target.add_note(f"Gmsh session cleanup failed: {error}")
    if first is not None:
        raise first


def _build(graph: RegionGraph) -> tuple[list[int], list[int], dict[str, int]]:
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
    field = gmsh.model.mesh.field
    distance = field.add("Distance")
    field.setNumbers(distance, "CurvesList", curves)
    field.setNumber(distance, "Sampling", math.ceil(max(lengths) / size) + _SAMPLING_MARGIN)
    return _threshold(distance, size, global_nm)


def _graded_points(points: list[int], size: float, global_nm: float) -> int:
    field = gmsh.model.mesh.field
    distance = field.add("Distance")
    field.setNumbers(distance, "PointsList", points)
    return _threshold(distance, size, global_nm)


def _threshold(distance: int, size: float, global_nm: float) -> int:
    field = gmsh.model.mesh.field
    threshold = int(field.add("Threshold"))
    field.setNumber(threshold, "InField", distance)
    field.setNumber(threshold, "SizeMin", size)
    field.setNumber(threshold, "SizeMax", global_nm)
    field.setNumber(threshold, "DistMin", 0.0)
    field.setNumber(threshold, "DistMax", (global_nm - size) / GRADING)
    return threshold


def _constant(surface: int, size: float, global_nm: float) -> int:
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
    """Return each edge's own size and each sized domain's size."""
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
    """Return the vertices the short-curve restriction applies to, by the length it is set to."""
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
    """Mesh stage 5's region with Gmsh under the section 5.2.2 table.

    Parameters
    ----------
    wall_h_nm
        The resolved wall size in nm; ``None`` leaves the wall to the other fields.

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
