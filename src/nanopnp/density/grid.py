"""Gridded (r, z) fields: the container, its formats and its interpolant."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal, TypeAlias

from nanopnp.core.hashing import content_hash
from nanopnp.core.typing import Expression

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

GRID_SCHEMA = "nanopnp/grid/v0.5"

GridFormat: TypeAlias = Literal["npz", "dx", "mrc", "comsolgrid"]

NATIVE_FORMAT: GridFormat = "npz"

_SUFFIXES: dict[str, GridFormat] = {
    ".npz": "npz",
    ".dx": "dx",
    ".mrc": "mrc",
    ".ccp4": "mrc",
    ".map": "mrc",
    ".txt": "comsolgrid",
}

NM2_TO_M2 = 1e-18

# Round-off on a table written in metres to ten figures (.knowledge/07-software-stack.md, gridData).
UNIFORM_TOL_NM = 1e-9


class GridFormatError(ValueError):
    """A grid file cannot be read or written in the format it names."""


@dataclass(frozen=True)
class RingMaximum:
    """The largest absolute value on a grid's boundary ring, and where it is."""

    value: float
    r_nm: float
    z_nm: float

    def summary(self) -> dict[str, float]:
        """Return this maximum as plain data, for the manifest."""
        return {"value": self.value, "r_nm": self.r_nm, "z_nm": self.z_nm}


@dataclass(frozen=True)
class RadialGrid:
    """A uniform ``(r, z)`` grid of samples, in nm coordinates and SI values."""

    origin_nm: tuple[float, float]
    spacing_nm: tuple[float, float]
    values: np.ndarray

    def __post_init__(self) -> None:
        import numpy as np

        object.__setattr__(self, "values", np.ascontiguousarray(self.values, dtype=np.float64))

    @classmethod
    def from_axes(cls, r_nm: np.ndarray, z_nm: np.ndarray, values: np.ndarray) -> RadialGrid:
        """Return the grid two axes and a value array describe.

        Raises
        ------
        GridFormatError
            If an axis is too short or not uniform, or the value array does not match the axes.
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
            if not step > 0.0 or not float(np.max(np.abs(steps - step))) <= UNIFORM_TOL_NM:
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

    @property
    def shape(self) -> tuple[int, int]:
        """``(n_r, n_z)``: the sample counts, in coordinate order."""
        return (int(self.values.shape[1]), int(self.values.shape[0]))

    @property
    def r_nm(self) -> np.ndarray:
        """The radial axis, in nm."""
        import numpy as np

        start, step = self.origin_nm[0], self.spacing_nm[0]
        return start + step * np.arange(self.values.shape[1], dtype=np.float64)

    @property
    def z_nm(self) -> np.ndarray:
        """The axial axis, in nm."""
        import numpy as np

        start, step = self.origin_nm[1], self.spacing_nm[1]
        return start + step * np.arange(self.values.shape[0], dtype=np.float64)

    @property
    def extent_nm(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """``((r_min, r_max), (z_min, z_max))`` of the sampled box, in nm."""
        n_r, n_z = self.shape
        r0, z0 = self.origin_nm
        dr, dz = self.spacing_nm
        return ((r0, r0 + dr * (n_r - 1)), (z0, z0 + dz * (n_z - 1)))

    def descriptor(self) -> dict[str, object]:
        """Return the grid descriptor the manifest and the artefact record."""
        (r_min, r_max), (z_min, z_max) = self.extent_nm
        return {
            "origin_nm": list(self.origin_nm),
            "spacing_nm": list(self.spacing_nm),
            "shape": list(self.shape),
            "extent_nm": {"r": [r_min, r_max], "z": [z_min, z_max]},
        }

    def digest(self) -> str:
        """Return the content hash of this grid: its descriptor and its values."""
        return content_hash(GRID_SCHEMA, {**self.descriptor(), "values": self.values})

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
        """Return trapezium weights for the integral up to ``upper``, in nm."""
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
            Apply the axisymmetric volume element ``2*pi*r``.
        """
        import numpy as np

        supplied = dict(weights or {})
        weights_r = supplied.get("r")
        weights_r = self.trapezium_weights("r") if weights_r is None else weights_r
        if radial:
            # r is converted here and dr, dz once below; a second factor folded into
            # the final scale would leave a radial integral 1e9 too large.
            weights_r = weights_r * (2.0 * np.pi * self.r_nm * 1e-9)
        weights_z = supplied.get("z")
        weights_z = self.trapezium_weights("z") if weights_z is None else weights_z
        if z_weight is not None:
            weights_z = weights_z * np.asarray(z_weight, dtype=np.float64)
        return float(weights_z @ self.values @ weights_r) * NM2_TO_M2

    def planar_integral(self) -> float:
        """Return ``∫ v dr dz`` in SI, without the ``2*pi*r`` Jacobian."""
        return self.integral()

    def cumulative(
        self, planes_nm: Sequence[float], *, ramp_nm: float, radial: bool = False
    ) -> tuple[float, ...]:
        """Return the charge below each ``z`` plane, under a ramped indicator."""
        import numpy as np

        z = self.z_nm
        return tuple(
            self.integral(
                radial=radial,
                z_weight=np.clip((plane + 0.5 * ramp_nm - z) / ramp_nm, 0.0, 1.0),
            )
            for plane in planes_nm
        )

    def interior_maximum(self) -> float:
        """Return ``max|v|`` over the whole grid."""
        import numpy as np

        return float(np.max(np.abs(self.values)))

    def boundary_ring_maximum(self) -> RingMaximum:
        """Return the largest ``|v|`` on the grid's boundary ring, and where."""
        import numpy as np

        ring = np.zeros_like(self.values, dtype=bool)
        ring[0, :] = ring[-1, :] = True
        ring[:, -1] = True
        # A first column on or beyond the axis is not a cut edge: no mesh point lies at r < 0.
        if self.origin_nm[0] > 0.0:
            ring[:, 0] = True
        magnitude = np.where(ring, np.abs(self.values), -1.0)
        i_z, i_r = np.unravel_index(int(np.argmax(magnitude)), magnitude.shape)
        return RingMaximum(
            value=float(np.abs(self.values[i_z, i_r])),
            r_nm=float(self.r_nm[i_r]),
            z_nm=float(self.z_nm[i_z]),
        )

    def padded(self) -> RadialGrid:
        """Return this grid with a ring of zeros and the box one spacing larger."""
        import numpy as np

        dr, dz = self.spacing_nm
        r0, z0 = self.origin_nm
        return RadialGrid(
            origin_nm=(r0 - dr, z0 - dz),
            spacing_nm=(dr, dz),
            values=np.pad(self.values, 1, mode="constant", constant_values=0.0),
        )


def coefficient(grid: RadialGrid, *, pad: bool = True) -> Expression:
    """Return the bilinear interpolant of ``grid`` as an NGSolve coefficient."""
    import ngsolve as ngs

    source = grid.padded() if pad else grid
    (r_min, r_max), (z_min, z_max) = source.extent_nm
    return ngs.VoxelCoefficient(
        start=(r_min, z_min),
        end=(r_max, z_max),
        values=source.values,
        linear=True,
    )


def detect_format(path: Path, declared: str | None = None) -> GridFormat:
    """Return the format a grid file is in, declared or read from its suffix.

    Raises
    ------
    GridFormatError
        If the format is unknown, or none is declared and the suffix names none.
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

    Raises
    ------
    GridFormatError
        If the format is unknown, or the file is not a grid this release can read.
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
        If the format is unknown, is read-only, or needs a dependency that is not installed.
    """
    target = Path(path)
    # Before the directory is made, so a refused format writes nothing.
    chosen = detect_format(target, format)
    if chosen == "comsolgrid":
        raise GridFormatError(
            "the COMSOL grid table is read-only: it is the reference model's own input, and a "
            f"round-tripped copy under the same format would be indistinguishable from it. Write "
            f"{NATIVE_FORMAT!r}, 'dx' or 'mrc' instead"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    if chosen == "npz":
        return _write_npz(grid, target)
    return _write_griddata(grid, target, chosen)


def _read_npz(path: Path) -> RadialGrid:
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
    import numpy as np

    written = path if path.suffix.lower() == ".npz" else path.with_name(f"{path.name}.npz")
    np.savez(written, r_nm=grid.r_nm, z_nm=grid.z_nm, values=grid.values)
    return written


def _grid_data_module() -> object:
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


_GRIDDATA_EXPORTERS: dict[GridFormat, str] = {"dx": "DX", "mrc": "MRC"}


def writable_formats() -> frozenset[GridFormat]:
    """Return the formats :func:`write_grid` can write in this environment."""
    formats: set[GridFormat] = {NATIVE_FORMAT}
    try:
        _grid_data_module()
    except GridFormatError:
        return frozenset(formats)
    formats.update(_GRIDDATA_EXPORTERS)
    return frozenset(formats)


def _write_griddata(grid: RadialGrid, path: Path, chosen: GridFormat) -> Path:
    module = _grid_data_module()
    data = module.Grid(  # type: ignore[attr-defined]
        grid=grid.values.T[:, :, None],
        origin=(grid.origin_nm[0], grid.origin_nm[1], 0.0),
        delta=(grid.spacing_nm[0], grid.spacing_nm[1], 1.0),
    )
    data.export(str(path), file_format=_GRIDDATA_EXPORTERS[chosen])
    return path


COMSOL_GRID_HEADER = "%Grid"

COMSOL_DATA_HEADER = "%Data"
COMSOL_LENGTH_SCALE_NM = 1e9


def _read_comsol(path: Path) -> RadialGrid:
    import numpy as np

    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines or lines[0].strip() != COMSOL_GRID_HEADER:
        raise GridFormatError(
            f"{path.name!r} does not begin with {COMSOL_GRID_HEADER!r}; a COMSOL grid table "
            "carries that header, one line per axis, then a %Data header"
        )
    try:
        split = next(i for i, line in enumerate(lines) if line.strip() == COMSOL_DATA_HEADER)
    except StopIteration:
        raise GridFormatError(
            f"{path.name!r} carries no {COMSOL_DATA_HEADER!r} header, so its axes and its values "
            "cannot be told apart"
        ) from None
    axes = lines[1:split]
    if len(axes) != 2:
        raise GridFormatError(
            f"{path.name!r} declares {len(axes)} coordinate axes between {COMSOL_GRID_HEADER!r} "
            f"and {COMSOL_DATA_HEADER!r}; this release reads two-dimensional (r, z) tables only"
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
