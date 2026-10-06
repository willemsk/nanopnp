"""The mesher registry and the Mesher protocol (FR-10, QR-14; §5.5, §8.2.8 H7).

A mesher backend is named by string in the case file (``numerics.mesh.backend``)
and resolved here. Two meshers are built in: ``netgen`` (default, LGPL-2.1) and
``gmsh`` (optional, GPLv2+).

A mesher provides its backend-specific recipe entries through :meth:`Mesher.settings`,
which :func:`~nanopnp.mesh.generate.sizing_parameters` merges into the stage-6
recipe, and meshes stage 5's region through :meth:`Mesher.mesh`.
"""

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
"""The ``pyproject.toml`` extra the Gmsh backend needs (CON-10, WP23 D9)."""


class Mesher(Protocol):
    """A mesher backend for stage 6 (FR-10, QR-14)."""

    name: str

    def settings(self, *, exclusion: bool = False) -> dict[str, Canonicalisable]:
        """Return the backend's own entries of the stage-6 recipe."""
        ...

    def mesh(
        self,
        record: RegionRecord,
        wall_h_nm: float | None,
        sizes: SizeTable,
    ) -> tuple[MeshData, str]:
        """Mesh stage 5's region; return the mesh and the mesher's version."""
        ...


def mesh_shape(shape: Shape, sizes: SizeTable) -> Mesh:
    """Mesh a named, sized region with netgen at the table's global size.

    The one call both the reference geometry and stage 6 make, so the two cannot
    mesh the same region with different mesher settings.
    """
    import netgen.occ as occ
    import ngsolve as ngs

    geometry = occ.OCCGeometry(shape, dim=2)
    return ngs.Mesh(
        geometry.GenerateMesh(maxh=sizes.global_nm, grading=GRADING, optsteps2d=OPTIMISATION_STEPS)
    )


class NetgenMesher:
    """The default in-process OpenCASCADE mesher (LGPL-2.1)."""

    name: str = "netgen"

    def settings(self, *, exclusion: bool = False) -> dict[str, Canonicalisable]:
        """Return the stage-6 sizing settings specific to Netgen.

        Parameters
        ----------
        exclusion : bool, default False
            Whether an ion-exclusion layer is configured.

        Returns
        -------
        dict[str, Canonicalisable]
            Dictionary of Netgen-specific sizing settings.
        """
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
        """Mesh a stage-5 region using Netgen.

        Parameters
        ----------
        record : RegionRecord
            The stage-5 CAD region record.
        wall_h_nm : float or None
            Target pore-wall element size in nm.
        sizes : SizeTable
            Dictionary of feature sizes.

        Returns
        -------
        tuple[MeshData, str]
            The generated mesh data and Netgen version string.
        """
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
    """Return the refusal of ``numerics.mesh.backend: gmsh`` on an install that lacks it.

    The remedy follows the error: a missing module wants the extra, an
    ``OSError`` means the wheel is installed and a system library it loads is
    not, and ``initialising`` means the library loaded and then failed to
    initialise (CON-10, REV-37). Installing the extra again would change neither
    of the last two.
    """
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
    """Import the Gmsh backend, or refuse naming the extra (CON-10, WP23 D9)."""
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
    """The optional Gmsh backend (ADR-002, GPLv2+)."""

    name: str = "gmsh"

    def settings(self, *, exclusion: bool = False) -> dict[str, Canonicalisable]:
        """Return the stage-6 sizing settings specific to Gmsh.

        Parameters
        ----------
        exclusion : bool, default False
            Whether an ion-exclusion layer is configured.

        Returns
        -------
        dict[str, Canonicalisable]
            Dictionary of Gmsh-specific sizing settings.
        """
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
        """Mesh a stage-5 region using Gmsh.

        Parameters
        ----------
        record : RegionRecord
            The stage-5 CAD region record.
        wall_h_nm : float or None
            Target pore-wall element size in nm.
        sizes : SizeTable
            Dictionary of feature sizes.

        Returns
        -------
        tuple[MeshData, str]
            The generated mesh data and Gmsh version string.
        """
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
    """Register a mesher backend under ``name``.

    Raises
    ------
    ValueError
        If ``name`` is already registered.
    """
    if name in _REGISTRY:
        raise ValueError(f"mesher {name!r} is already registered")
    _REGISTRY[name] = builder


def registered_meshers() -> tuple[str, ...]:
    """Return every selectable mesher name, sorted."""
    return tuple(sorted(_REGISTRY))


def create_mesher(name: str) -> Mesher:
    """Build the mesher registered as ``name``.

    Raises
    ------
    KeyError
        If no such mesher is registered; the message lists the known names.
    """
    try:
        builder = _REGISTRY[name]
    except KeyError:
        known = ", ".join(registered_meshers())
        raise KeyError(f"unknown mesher {name!r}; registered meshers are {known}") from None
    return builder()


register_mesher("netgen", NetgenMesher)
register_mesher("gmsh", GmshMesher)
