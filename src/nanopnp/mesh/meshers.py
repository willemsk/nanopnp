"""The mesher registry and the Mesher protocol (FR-10, QR-14; §5.5)."""

from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol, TypeAlias

from nanopnp.core.hashing import Canonicalisable
from nanopnp.core.stages import MissingExtraError
from nanopnp.geometry.region import RegionRecord, build_region, region_graph
from nanopnp.mesh.adapter import from_ngsolve
from nanopnp.mesh.sizing import (
    EXCLUSION_WALL_RULE,
    GMSH_ALGORITHM,
    GMSH_FIELD_RULES,
    GMSH_SMOOTHING,
    GRADING,
    OPTIMISATION_STEPS,
    SizeTable,
    apply_sizes,
)

if TYPE_CHECKING:
    from types import ModuleType

    from nanopnp.core.typing import Mesh, Shape
    from nanopnp.mesh.adapter import MeshData

GMSH_EXTRA = "gmsh"
"""The ``pyproject.toml`` extra the Gmsh backend needs (CON-10)."""


class Mesher(Protocol):
    """A mesher backend for stage 6."""

    name: str

    def settings(self, *, exclusion: bool = False) -> dict[str, Canonicalisable]:
        """Return the backend's own entries of the stage-6 recipe."""

    def mesh(
        self,
        record: RegionRecord,
        wall_h_nm: float | None,
        sizes: SizeTable,
    ) -> tuple[MeshData, str]:
        """Mesh stage 5's region; return the mesh and the mesher's version."""


def mesh_shape(shape: Shape, sizes: SizeTable) -> Mesh:
    """Mesh a named, sized region with netgen at the table's global size."""
    import netgen.occ as occ
    import ngsolve as ngs

    geometry = occ.OCCGeometry(shape, dim=2)
    return ngs.Mesh(
        geometry.GenerateMesh(maxh=sizes.global_nm, grading=GRADING, optsteps2d=OPTIMISATION_STEPS)
    )


class NetgenMesher:
    """The default in-process OpenCASCADE mesher."""

    name: str = "netgen"

    def settings(self, *, exclusion: bool = False) -> dict[str, Canonicalisable]:
        """Return the stage-6 sizing settings specific to Netgen."""
        settings: dict[str, Canonicalisable] = {"optsteps2d": OPTIMISATION_STEPS}
        if exclusion:
            settings["exclusion_wall"] = EXCLUSION_WALL_RULE
        return settings

    def mesh(
        self,
        record: RegionRecord,
        wall_h_nm: float | None,
        sizes: SizeTable,
    ) -> tuple[MeshData, str]:
        """Mesh a stage-5 region using Netgen; return the mesh and the Netgen version."""
        from netgen import config

        shape = build_region(record)
        apply_sizes(
            shape,
            wall_h_nm=wall_h_nm,
            axis_extent_nm=record.axis_split_nm,
            sizes=sizes,
            divide_wall=record.exclusion is not None,
        )
        return (
            from_ngsolve(mesh_shape(shape, sizes)),
            str(config.version).lstrip("v").split("-")[0],
        )


def _missing_gmsh(error: Exception, *, initialising: bool = False) -> MissingExtraError:
    step = "initialising" if initialising else "importing"
    remedy = (
        "The gmsh wheel is installed but failed to initialise; install the system library the "
        "error names"
        if initialising
        else "The gmsh wheel is installed but could not load a native library; install the "
        "system library the error names"
        if isinstance(error, OSError)
        else "Install the extras with `uv sync --all-extras`"
    )
    return MissingExtraError(
        f"numerics.mesh.backend is 'gmsh', which needs the {GMSH_EXTRA!r} extra: {step} gmsh "
        f"failed with {type(error).__name__}: {error}. {remedy}, or mesh with the default "
        "backend, netgen (CON-10, ADR-002)",
        name="gmsh",
    )


def _gmsh_backend() -> ModuleType:
    try:
        module = importlib.import_module("nanopnp.mesh.gmsh_backend")
    except ModuleNotFoundError as error:
        if error.name is None or error.name.split(".")[0] != "gmsh":
            raise
        raise _missing_gmsh(error) from error
    except OSError as error:
        raise _missing_gmsh(error) from error
    return module


class GmshMesher:
    """The optional Gmsh backend."""

    name: str = "gmsh"

    def settings(self, *, exclusion: bool = False) -> dict[str, Canonicalisable]:
        """Return the stage-6 sizing settings specific to Gmsh."""
        return {
            "gmsh": {
                "algorithm": GMSH_ALGORITHM,
                "smoothing": GMSH_SMOOTHING,
                "fields": list(GMSH_FIELD_RULES),
            }
        }

    def mesh(
        self,
        record: RegionRecord,
        wall_h_nm: float | None,
        sizes: SizeTable,
    ) -> tuple[MeshData, str]:
        """Mesh a stage-5 region using Gmsh; return the mesh and the Gmsh version."""
        module = _gmsh_backend()
        graph = region_graph(build_region(record), record)
        try:
            data = module.mesh_region(
                graph,
                wall_h_nm,
                sizes,
                membrane_thickness_nm=record.membrane.thickness_nm,
                axis_extent_nm=record.axis_split_nm,
            )
        except module.GmshInitialisationError as error:
            raise _missing_gmsh(error, initialising=True) from error
        return data, str(module.version())


MesherBuilder: TypeAlias = Callable[[], Mesher]
"""Builds one mesher."""

_REGISTRY: dict[str, MesherBuilder] = {}


def register_mesher(name: str, builder: MesherBuilder) -> None:
    """Register a mesher backend under ``name``; refuses a name already registered."""
    if name in _REGISTRY:
        raise ValueError(f"mesher {name!r} is already registered")
    _REGISTRY[name] = builder


def registered_meshers() -> tuple[str, ...]:
    """Return every selectable mesher name, sorted."""
    return tuple(sorted(_REGISTRY))


def create_mesher(name: str) -> Mesher:
    """Build the mesher registered as ``name``."""
    try:
        builder = _REGISTRY[name]
    except KeyError:
        known = ", ".join(registered_meshers())
        raise KeyError(f"unknown mesher {name!r}; registered meshers are {known}") from None
    return builder()


register_mesher("netgen", NetgenMesher)
register_mesher("gmsh", GmshMesher)
