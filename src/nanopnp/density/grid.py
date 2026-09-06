"""Gridded ``(r, z)`` fields: the container, its formats, and its interpolant.

Section 5.1 assigns grid IO to ``density/``, and this module is the seam behind
every gridded field the solver consumes: the smeared fixed charge of PHY-16, the
solid fraction the dielectric blend of section 4.4 reads, and — when Phase 2
lands — the reduced density map itself. Nothing downstream knows which format a
grid arrived in, which is what :class:`~nanopnp.mesh.adapter.MeshData` already
does for the meshers.

Three facts about the container are load-bearing and none of them is guessable
from a bare array.

**The value array is indexed ``[i_z, i_r]``.** That is what
``ngsolve.VoxelCoefficient`` requires of a two-dimensional grid — its axes run
slowest-first — and passing the transpose raises nothing: a field built to be
``10r + z`` returns 1.0 at ``(r=1, z=0)`` where 10.0 was meant, and agrees
*exactly* on the diagonal, so a test that samples where ``r = z`` passes on a
transposed field [tested]. :meth:`RadialGrid.from_axes` is therefore the only
constructor, and it checks the shape against the two axes it was handed.

**Coordinates are in nanometres, values in SI.** The meshes are in nm
(:mod:`nanopnp.mesh.primitives`), so an interpolant evaluated on one must be too;
the values are whatever SI unit the quantity carries, which
:mod:`nanopnp.charge.fields` converts to at the file boundary. Every integral
here converts the lengths to metres on the way out, so a ``C m^-2`` grid
integrates to coulombs.

**The interpolant is zero outside the box, and that costs a ring of padding.**
``VoxelCoefficient`` continues by the *clamped edge value* outside its box, not
by zero [tested], and over a 250 nm reservoir against a 6 x 15 nm grid that
amplifies a residual edge value over an area a thousand times the grid's own
(section 5.3.1 NOTE, and the WP9 plan's Design section). :func:`coefficient`
therefore pads with a ring of zeros and extends the box by one spacing each way,
which makes the continuation exactly zero *and* keeps the coefficient function
continuous — an ``IfPos`` window would give the first and not the second.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal, TypeAlias

from nanopnp.core.hashing import content_hash
from nanopnp.core.typing import Expression

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

GRID_SCHEMA = "nanopnp/grid/v1"
"""Domain separator of :meth:`RadialGrid.digest`."""

GridFormat: TypeAlias = Literal["npz", "dx", "mrc", "comsolgrid"]
"""The data formats a grid is read from and written to (IF-05).

``npz`` is the native one and is on the default path. ``dx`` (OpenDX) and ``mrc``
(the CCP4-2000 map format) go through GridDataFormats, which is optional
(CON-10 applied to a second dependency): it needs Python 3.11 and this project's
floor is 3.10, so a field must be readable without it. ``comsolgrid`` is the
reference model's own text table, read only.
"""

NATIVE_FORMAT: GridFormat = "npz"
"""The format written when nothing else is asked for."""

_SUFFIXES: dict[str, GridFormat] = {
    ".npz": "npz",
    ".dx": "dx",
    ".mrc": "mrc",
    ".ccp4": "mrc",
    ".map": "mrc",
    ".txt": "comsolgrid",
}
"""Filename suffixes against the format each names.

``.ccp4`` and ``.map`` both resolve to ``mrc`` because gridData has no CCP4
writer at all — ``file_format="ccp4"`` raises ``ValueError: File format CCP4 not
available`` — and its ``MRC`` writer *is* the CCP4-2000 map format [tested].
"""

UNIFORM_TOL_NM = 1e-9
"""Tolerance on an axis's spacing, in nm, before it is refused as non-uniform.

``VoxelCoefficient`` takes a box and a shape, so a non-uniform axis would be
resampled onto a uniform one silently. The tolerance is round-off on a table
written in metres to ten significant figures: the reference grid's own axes vary
by 1e-15 nm about 0.005 nm [tested].
"""


class GridFormatError(ValueError):
    """A grid file cannot be read or written in the format it names.

    Its own type rather than a bare :class:`ValueError` so that a caller can tell
    "this file is not a grid" from "this grid is not usable here", exactly as
    :class:`~nanopnp.mesh.ingest.MeshVocabularyError` does for meshes.
    """


@dataclass(frozen=True)
class RingMaximum:
    """The largest absolute value on a grid's boundary ring, and where it is.

    Parameters
    ----------
    value
        ``max|v|`` over the four edges of the grid, in the value's own units.
    r_nm, z_nm
        Where it sits, so that a truncation diagnostic names a location rather
        than only a number (QR-12).
    """

    value: float
    r_nm: float
    z_nm: float

    def summary(self) -> dict[str, float]:
        """Return this maximum as plain data, for the FR-25 manifest."""
        return {"value": self.value, "r_nm": self.r_nm, "z_nm": self.z_nm}


@dataclass(frozen=True)
class RadialGrid:
    """A uniform ``(r, z)`` grid of samples, in nm coordinates and SI values.

    Parameters
    ----------
    origin_nm
        ``(r, z)`` of the sample at index ``[0, 0]``.
    spacing_nm
        ``(dr, dz)``, both positive.
    values
        ``float64``, indexed ``[i_z, i_r]``. See the module docstring: this is
        the axis order ``VoxelCoefficient`` requires and the one a transposed
        array agrees with on the diagonal.

    Notes
    -----
    Built through :meth:`from_axes`, which is the only constructor that can check
    the value array against the axes it belongs to.
    """

    origin_nm: tuple[float, float]
    spacing_nm: tuple[float, float]
    values: np.ndarray

    def __post_init__(self) -> None:
        """Normalise the array to contiguous ``float64``, as ``MeshData`` does.

        Two grids that differ only in memory layout or in ``float32`` against
        ``float64`` would otherwise digest differently and key two artefacts.
        """
        import numpy as np

        object.__setattr__(self, "values", np.ascontiguousarray(self.values, dtype=np.float64))

    # -- construction ------------------------------------------------------

    @classmethod
    def from_axes(cls, r_nm: np.ndarray, z_nm: np.ndarray, values: np.ndarray) -> RadialGrid:
        """Return the grid two axes and a value array describe.

        Parameters
        ----------
        r_nm, z_nm
            Sample coordinates, ascending and uniformly spaced, in nm.
        values
            ``[i_z, i_r]``, so ``values.shape == (z_nm.size, r_nm.size)``.

        Raises
        ------
        GridFormatError
            If either axis has fewer than two samples or is not uniform, or if
            the value array's shape does not match the two axes. The last one is
            the axis-order check: a transposed array fails it unless the grid is
            square, and the message names both shapes.
        """
        import numpy as np

        axes = {"r": np.asarray(r_nm, dtype=np.float64), "z": np.asarray(z_nm, dtype=np.float64)}
        spacing: dict[str, float] = {}
        for name, axis in axes.items():
            if axis.ndim != 1 or axis.size < 2:
                raise GridFormatError(
                    f"the {name} axis has shape {tuple(axis.shape)}; a grid needs at least two "
                    "samples on each axis, since one sample fixes no spacing"
                )
            steps = np.diff(axis)
            step = float(steps[0])
            if step <= 0.0 or float(np.max(np.abs(steps - step))) > UNIFORM_TOL_NM:
                raise GridFormatError(
                    f"the {name} axis is not uniformly ascending: spacing runs from "
                    f"{float(np.min(steps)):.6g} to {float(np.max(steps)):.6g} nm. A voxel "
                    "interpolant takes a box and a shape, so a non-uniform axis would be "
                    "resampled onto a uniform one with nothing to say so"
                )
            spacing[name] = step
        array = np.asarray(values, dtype=np.float64)
        expected = (axes["z"].size, axes["r"].size)
        if array.shape != expected:
            raise GridFormatError(
                f"the value array has shape {tuple(array.shape)} and the axes need "
                f"{expected}: the array is indexed [i_z, i_r], slowest axis first, which is what "
                "ngsolve.VoxelCoefficient requires. A transposed array agrees with the intended "
                "one wherever r = z, so this shape check is what catches it"
            )
        return cls(
            origin_nm=(float(axes["r"][0]), float(axes["z"][0])),
            spacing_nm=(spacing["r"], spacing["z"]),
            values=array,
        )

    # -- geometry ----------------------------------------------------------

    @property
    def shape(self) -> tuple[int, int]:
        """``(n_r, n_z)``: the sample counts, in coordinate order."""
        return (int(self.values.shape[1]), int(self.values.shape[0]))

    @property
    def r_nm(self) -> np.ndarray:
        """The radial axis."""
        import numpy as np

        start, step = self.origin_nm[0], self.spacing_nm[0]
        return start + step * np.arange(self.values.shape[1], dtype=np.float64)

    @property
    def z_nm(self) -> np.ndarray:
        """The axial axis."""
        import numpy as np

        start, step = self.origin_nm[1], self.spacing_nm[1]
        return start + step * np.arange(self.values.shape[0], dtype=np.float64)

    @property
    def extent_nm(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """``((r_min, r_max), (z_min, z_max))`` of the sampled box."""
        n_r, n_z = self.shape
        r0, z0 = self.origin_nm
        dr, dz = self.spacing_nm
        return ((r0, r0 + dr * (n_r - 1)), (z0, z0 + dz * (n_z - 1)))

    def descriptor(self) -> dict[str, object]:
        """Return the grid descriptor the manifest and the artefact record.

        Origin, spacing, shape and extent — enough for a reader to place the
        grid without opening the data file (FR-25, section 5.3.1).
        """
        (r_min, r_max), (z_min, z_max) = self.extent_nm
        return {
            "origin_nm": list(self.origin_nm),
            "spacing_nm": list(self.spacing_nm),
            "shape": list(self.shape),
            "extent_nm": {"r": [r_min, r_max], "z": [z_min, z_max]},
        }

    def digest(self) -> str:
        """Return the content hash of this grid: its descriptor and its values.

        Over the array's bytes rather than its elements, which
        :func:`nanopnp.core.hashing.content_hash` already does, so digesting the
        reference grid's 4.8 million samples costs one pass over the buffer.
        """
        return content_hash(GRID_SCHEMA, {**self.descriptor(), "values": self.values})

    # -- integrals ---------------------------------------------------------

    def trapezium_weights(self, axis: Literal["r", "z"]) -> np.ndarray:
        """Return the trapezium weights along one axis, in nm."""
        import numpy as np

        count, step = (
            (self.values.shape[1], self.spacing_nm[0])
            if axis == "r"
            else (self.values.shape[0], self.spacing_nm[1])
        )
        weights = np.full(count, step, dtype=np.float64)
        weights[0] *= 0.5
        weights[-1] *= 0.5
        return weights

    def truncated_weights(self, axis: Literal["r", "z"], upper: float) -> np.ndarray:
        """Return trapezium weights for the integral up to ``upper``, in nm.

        Exact for the piecewise-linear interpolant a voxel coefficient carries,
        the partial interval the cutoff falls in included — which PHY-18's
        0.01 nm axis guard does on the reference model's 0.005 nm grid, and which
        a mask over the samples alone gets wrong by a factor of two right where
        the guard bites.

        Parameters
        ----------
        axis
            ``"r"`` or ``"z"``.
        upper
            Upper limit, in nm. Below the first sample this returns zeros.
        """
        import numpy as np

        coordinates = self.r_nm if axis == "r" else self.z_nm
        step = self.spacing_nm[0] if axis == "r" else self.spacing_nm[1]
        weights = np.zeros(coordinates.size, dtype=np.float64)
        inside = int(np.searchsorted(coordinates, upper, side="right")) - 1
        if inside < 0:
            return weights
        if inside >= 1:
            weights[: inside + 1] = step
            weights[0] = weights[inside] = 0.5 * step
        # The part of the interval [r_k, r_k+1] below the cutoff, integrated
        # against the linear interpolant between the two samples.
        fraction = min((upper - float(coordinates[inside])) / step, 1.0)
        if fraction > 0.0 and inside + 1 < coordinates.size:
            weights[inside] += step * fraction * (1.0 - 0.5 * fraction)
            weights[inside + 1] += step * 0.5 * fraction**2
        return weights

    def integral(
        self,
        *,
        radial: bool = False,
        z_weight: np.ndarray | None = None,
        weights: Mapping[str, np.ndarray] | None = None,
    ) -> float:
        """Return the trapezium integral of the values over the grid, in SI.

        Parameters
        ----------
        radial
            Apply the axisymmetric volume element ``2*pi*r``, for a value that is
            a volume density. Left off for the reference's ``rhoq_pore``, whose
            own ``1/(2*pi*r)`` cancels the Jacobian identically (section 4.4
            NOTE): its mesh integral *is* the planar integral of the table.
        z_weight
            A per-sample weight along ``z``, multiplied onto the trapezium
            weights, for the ramped cumulative of :meth:`cumulative`.
        weights
            Trapezium weights to use *instead* of this grid's own, by axis name —
            :meth:`truncated_weights` for a partial integral. Replacing them
            rather than multiplying is the point: a mask multiplied onto the
            trapezium weights halves the sample at each end of the mask, which is
            the whole integral when the region is a spacing wide.

        Returns
        -------
        float
            ``∫ v dr dz`` with the lengths in **metres**, so a grid in C m^-2
            integrates to coulombs and one in C m^-3 integrates to coulombs once
            ``radial`` supplies the missing length.

        Notes
        -----
        The trapezium rule is not a compromise here. Applied to a smooth function
        that decays to zero at both ends of the range it has no Euler-Maclaurin
        boundary terms, so its error is beyond all orders in the spacing: on the
        reference grid it reproduces the exact ``-72 e`` to 5e-12 [tested].
        """
        import numpy as np

        supplied = dict(weights or {})
        weights_r = supplied.get("r")
        weights_r = self.trapezium_weights("r") if weights_r is None else weights_r
        if radial:
            weights_r = weights_r * (2.0 * np.pi * self.r_nm * 1e-9)
        weights_z = supplied.get("z")
        weights_z = self.trapezium_weights("z") if weights_z is None else weights_z
        if z_weight is not None:
            weights_z = weights_z * np.asarray(z_weight, dtype=np.float64)
        metres = 1e-18 if not radial else 1e-9
        return float(weights_z @ self.values @ weights_r) * metres

    def planar_integral(self) -> float:
        """Return ``∫ v dr dz`` in SI, without the ``2*pi*r`` Jacobian."""
        return self.integral()

    def cumulative(
        self, planes_nm: Sequence[float], *, ramp_nm: float, radial: bool = False
    ) -> tuple[float, ...]:
        """Return the charge below each ``z`` plane, under a ramped indicator.

        PHY-19 asks for a per-``z``-slice cumulative because a globally satisfied
        conservation check can hide compensating local errors. A step indicator
        cannot deliver it: NGSolve integrates the discontinuity inside every
        element the plane crosses, which on the reference mesh is a noise floor
        several times the tolerance the check enforces. Section 4.4's NOTE
        therefore makes the weight Lipschitz and of stated width, applied
        identically to the grid side and the mesh side, so that both evaluate one
        functional and the smoothing cancels out of the comparison.

        Parameters
        ----------
        planes_nm
            The ``z`` planes, in nm.
        ramp_nm
            Width of the linear ramp centred on each plane. Two to four times the
            local element size is the condition for the mesh side's quadrature
            error to be negligible.
        radial
            As :meth:`integral`.

        Returns
        -------
        tuple of float
            One cumulative per plane, in the order given.
        """
        import numpy as np

        z = self.z_nm
        return tuple(
            self.integral(
                radial=radial,
                z_weight=np.clip((plane + 0.5 * ramp_nm - z) / ramp_nm, 0.0, 1.0),
            )
            for plane in planes_nm
        )

    # -- gates and padding -------------------------------------------------

    def interior_maximum(self) -> float:
        """Return ``max|v|`` over the whole grid."""
        import numpy as np

        return float(np.max(np.abs(self.values)))

    def boundary_ring_maximum(self) -> RingMaximum:
        """Return the largest ``|v|`` on the grid's boundary ring, and where.

        What the padding of :func:`coefficient` throws away. A grid extended
        ``>= 4 sigma`` beyond the structure as PHY-16 step 4 requires carries
        ``exp(-16) = 1.1e-7`` of its peak there, so a compliant grid clears the
        truncation gate by decades and a truncated one does not.
        """
        import numpy as np

        ring = np.zeros_like(self.values, dtype=bool)
        ring[0, :] = ring[-1, :] = True
        ring[:, 0] = ring[:, -1] = True
        magnitude = np.where(ring, np.abs(self.values), -1.0)
        i_z, i_r = np.unravel_index(int(np.argmax(magnitude)), magnitude.shape)
        return RingMaximum(
            value=float(np.abs(self.values[i_z, i_r])),
            r_nm=float(self.r_nm[i_r]),
            z_nm=float(self.z_nm[i_z]),
        )

    def padded(self) -> RadialGrid:
        """Return this grid with a ring of zeros and the box one spacing larger.

        Why, rather than clamping or windowing: see the module docstring.
        """
        import numpy as np

        dr, dz = self.spacing_nm
        r0, z0 = self.origin_nm
        return RadialGrid(
            origin_nm=(r0 - dr, z0 - dz),
            spacing_nm=(dr, dz),
            values=np.pad(self.values, 1, mode="constant", constant_values=0.0),
        )


def coefficient(grid: RadialGrid, *, pad: bool = True) -> Expression:
    """Return the bilinear interpolant of ``grid`` as an NGSolve coefficient.

    Bilinear rather than nearest-neighbour, matching the reference model's own
    "2D linear interpolation function": nearest-neighbour would make the
    conservation budget a function of the mesh rather than of the field.

    Parameters
    ----------
    grid
        The grid, in nm coordinates.
    pad
        Pad with a ring of zeros so the interpolant is zero outside the box
        (section 5.3.1 NOTE). Off only for a test that wants to see the raw
        continuation behaviour; every consumer leaves it on.

    Returns
    -------
    Expression
        A coefficient function of the mesh coordinates, in the grid's own value
        units.
    """
    import ngsolve as ngs

    source = grid.padded() if pad else grid
    (r_min, r_max), (z_min, z_max) = source.extent_nm
    return ngs.VoxelCoefficient(
        start=(r_min, z_min),
        end=(r_max, z_max),
        values=source.values,
        linear=True,
    )


# -- formats ------------------------------------------------------------------


def detect_format(path: Path, declared: str | None = None) -> GridFormat:
    """Return the format a grid file is in, declared or read from its suffix.

    Parameters
    ----------
    path
        The file.
    declared
        The format the field document names, if any. Honoured over the suffix,
        because a supplied file need not be named helpfully.

    Raises
    ------
    GridFormatError
        If the declared format is not one this release reads, or if no format was
        declared and the suffix names none. The message lists the formats.
    """
    known = ", ".join(sorted({*_SUFFIXES.values()}))
    if declared is not None:
        if declared not in set(_SUFFIXES.values()):
            raise GridFormatError(
                f"grid format {declared!r} is not one this release reads; the formats are {known}"
            )
        return declared
    found = _SUFFIXES.get(path.suffix.lower())
    if found is None:
        raise GridFormatError(
            f"cannot tell the format of {path.name!r} from its suffix and none was declared; "
            f"the formats are {known}, named by the data.format key of the field document"
        )
    return found


def read_grid(path: str | Path, *, format: str | None = None) -> RadialGrid:
    """Read a grid from disk.

    Parameters
    ----------
    path
        The data file.
    format
        One of :data:`GridFormat`, or ``None`` to read it from the suffix.

    Raises
    ------
    FileNotFoundError
        If the file is not there.
    GridFormatError
        If the format is unknown, if the file is not a grid this release can
        read, or if it carries a genuinely two-dimensional array in a format
        whose readers require the singleton third axis.
    """
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"no grid file at {str(source)!r}")
    chosen = detect_format(source, format)
    if chosen == "npz":
        return _read_npz(source)
    if chosen == "comsolgrid":
        return _read_comsol(source)
    return _read_griddata(source, chosen)


def write_grid(grid: RadialGrid, path: str | Path, *, format: str | None = None) -> Path:
    """Write a grid to disk and return the path written.

    Raises
    ------
    GridFormatError
        If the format is unknown, or is ``comsolgrid``, which is read-only: it is
        the reference model's own table and writing one would invite a
        round-tripped copy to be mistaken for it.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    chosen = detect_format(target, format)
    if chosen == "comsolgrid":
        raise GridFormatError(
            "the COMSOL grid table is read-only: it is the reference model's own input, and a "
            f"round-tripped copy under the same format would be indistinguishable from it. Write "
            f"{NATIVE_FORMAT!r}, 'dx' or 'mrc' instead"
        )
    if chosen == "npz":
        return _write_npz(grid, target)
    return _write_griddata(grid, target, chosen)


def _read_npz(path: Path) -> RadialGrid:
    """Read the native format: the two axes and the value array, float64."""
    import numpy as np

    with np.load(path) as archive:
        missing = sorted({"r_nm", "z_nm", "values"} - set(archive.files))
        if missing:
            raise GridFormatError(
                f"{path.name!r} is an npz archive without {', '.join(missing)}; a nanopnp grid "
                "carries r_nm, z_nm and values"
            )
        return RadialGrid.from_axes(archive["r_nm"], archive["z_nm"], archive["values"])


def _write_npz(grid: RadialGrid, path: Path) -> Path:
    """Write the native format, uncompressed: the axes reconstruct exactly."""
    import numpy as np

    np.savez(path, r_nm=grid.r_nm, z_nm=grid.z_nm, values=grid.values)
    return path


def _grid_data_module() -> object:
    """Return the ``gridData`` module, or refuse with the extra that carries it.

    Raises
    ------
    GridFormatError
        If GridDataFormats is not installed. It is behind the ``structure``
        extra: it requires Python 3.11 and this project supports 3.10 (QR-09), so
        the interchange formats of IF-05 cannot be on the default path.
    """
    try:
        import gridData
    except ImportError as error:  # pragma: no cover - exercised by the skip in Tier 1
        raise GridFormatError(
            "reading or writing OpenDX and CCP4 grids needs GridDataFormats, which is behind the "
            "'structure' extra (IF-05, CON-10): install with `uv sync --all-extras`, or use the "
            f"{NATIVE_FORMAT!r} format, which is on the default path"
        ) from error
    return gridData


def _read_griddata(path: Path, chosen: GridFormat) -> RadialGrid:
    """Read an OpenDX or CCP4/MRC grid, requiring the singleton third axis.

    A ``(r, z)`` grid is written as a three-dimensional grid whose third axis is
    a singleton, because gridData fails on a genuinely two-dimensional array from
    inside its own DX writer, with a ``TypeError`` about a format string
    [tested]. Refusing the shape here is the difference between a diagnostic and
    a stack trace.
    """
    import numpy as np

    module = _grid_data_module()
    data = module.Grid(str(path))  # type: ignore[attr-defined]
    array = np.asarray(data.grid, dtype=np.float64)
    if array.ndim != 3 or array.shape[2] != 1:
        raise GridFormatError(
            f"{path.name!r} holds an array of shape {tuple(array.shape)}; an (r, z) grid is "
            "written as a three-dimensional grid whose third axis is a singleton, so the shape "
            "must be (n_r, n_z, 1). A two-dimensional array is not a grid these formats can carry"
        )
    origin = np.asarray(data.origin, dtype=np.float64)
    delta = np.asarray(data.delta, dtype=np.float64).reshape(-1)[:3]
    n_r, n_z = int(array.shape[0]), int(array.shape[1])
    r_nm = origin[0] + delta[0] * np.arange(n_r, dtype=np.float64)
    z_nm = origin[1] + delta[1] * np.arange(n_z, dtype=np.float64)
    # gridData indexes [i_r, i_z, 0]; this container indexes [i_z, i_r].
    return RadialGrid.from_axes(r_nm, z_nm, array[:, :, 0].T)


def _write_griddata(grid: RadialGrid, path: Path, chosen: GridFormat) -> Path:
    """Write an OpenDX or CCP4/MRC grid, with the singleton third axis.

    ``mrc`` stores ``float32``, so a CCP4 round trip is not bit-exact and changes
    the grid's digest. Recorded here rather than hidden: the native format is the
    working one and the interchange formats are for other tools (IF-05).
    """
    module = _grid_data_module()
    data = module.Grid(  # type: ignore[attr-defined]
        grid=grid.values.T[:, :, None],
        origin=(grid.origin_nm[0], grid.origin_nm[1], 0.0),
        delta=(grid.spacing_nm[0], grid.spacing_nm[1], 1.0),
    )
    data.export(str(path), file_format={"dx": "DX", "mrc": "MRC"}[chosen])
    return path


_COMSOL_GRID_HEADER = "%Grid"
_COMSOL_DATA_HEADER = "%Data"
COMSOL_LENGTH_SCALE_NM = 1e9
"""Nanometres per metre: the reference table's coordinates are in SI."""


def _read_comsol(path: Path) -> RadialGrid:
    """Read COMSOL's ``%Grid``/``%Data`` interpolation table.

    The format the reference model loaded ``rhoq_pore`` from: a ``%Grid`` header,
    one line per coordinate axis in **metres**, a ``%Data`` header, and then one
    line of ``n_r`` values per ``z`` sample — which is already this container's
    ``[i_z, i_r]`` order. Read only, and without a dependency, so the reference
    table is ingestible as delivered rather than through a conversion step
    somebody has to remember to describe in the provenance.
    """
    import numpy as np

    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines or lines[0].strip() != _COMSOL_GRID_HEADER:
        raise GridFormatError(
            f"{path.name!r} does not begin with {_COMSOL_GRID_HEADER!r}; a COMSOL grid table "
            "carries that header, one line per axis, then a %Data header"
        )
    try:
        split = next(i for i, line in enumerate(lines) if line.strip() == _COMSOL_DATA_HEADER)
    except StopIteration:
        raise GridFormatError(
            f"{path.name!r} carries no {_COMSOL_DATA_HEADER!r} header, so its axes and its values "
            "cannot be told apart"
        ) from None
    axes = lines[1:split]
    if len(axes) != 2:
        raise GridFormatError(
            f"{path.name!r} declares {len(axes)} coordinate axes between {_COMSOL_GRID_HEADER!r} "
            f"and {_COMSOL_DATA_HEADER!r}; this release reads two-dimensional (r, z) tables only"
        )
    r_nm = np.fromstring(axes[0], sep=" ") * COMSOL_LENGTH_SCALE_NM
    z_nm = np.fromstring(axes[1], sep=" ") * COMSOL_LENGTH_SCALE_NM
    rows = [np.fromstring(line, sep=" ") for line in lines[split + 1 :]]
    widths = {row.size for row in rows}
    if len(widths) != 1:
        raise GridFormatError(
            f"{path.name!r} has rows of {len(widths)} different lengths "
            f"({', '.join(str(width) for width in sorted(widths))}); every data row of a grid "
            "table carries one value per r sample"
        )
    return RadialGrid.from_axes(r_nm, z_nm, np.vstack(rows))
