"""The stage-2 artefact's payload: the ensemble-mean density on its canonical grid (WP19 D10).

One compressed ``.npz`` holds the map, float32 and indexed ``[z, y, x]``, the grid
that places it, and a JSON header: the radius set and its digest, sigma, ε, the frames
and the atom counts by element, hydrogens included. The header is also the
artefact's summary.

**It is exported to OpenDX and CCP4 through GridDataFormats** (IF-05), transposed to
gridData's x-first order, and read back from either. Those formats carry the grid
and the values but no header, so a map read from one carries only its file name.
gridData writes an OpenDX origin to six decimals, its spacing to seven significant
figures and its values at the array's own precision, six decimals for float32; its
MRC writer is the CCP4-2000 format and stores everything as float32, so a CCP4
round trip of this float32 map's values is exact (``.knowledge/07-software-stack.md``
§2). The grid is canonical, so a read rebuilds it from integer node indices and a
spacing read at seven significant figures, and loses nothing.

Reading ``.npz`` needs NumPy alone; the interchange formats need the ``structure``
extra, and a missing extra is refused naming it.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from nanopnp.core.hashing import Canonicalisable, content_hash
from nanopnp.density.grid import GridFormatError, _grid_data_module
from nanopnp.density.union import DensityGrid
from nanopnp.io.artefact import DENSITY_SCHEMA

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

PAYLOAD_NAME = "density"
"""The artefact's payload key, and the ``.npz`` file's stem."""

_INTERCHANGE: Mapping[str, str] = {".dx": "DX", ".ccp4": "MRC", ".mrc": "MRC", ".map": "MRC"}
"""Suffixes gridData reads and writes, against its exporter key.

``.ccp4`` goes through ``MRC`` because gridData has no CCP4 writer, and its MRC
writer is the CCP4-2000 map format (``.knowledge/07-software-stack.md`` §2).
"""

SPACING_TOLERANCE_NM = 1e-6
"""How far a file's spacings may differ from one another before it is not a canonical grid.

gridData writes an OpenDX delta to seven significant figures.
"""

LATTICE_TOLERANCE_NM = 1e-5
"""How far a file's origin may lie from a node ``i·h`` before it is not a canonical grid.

gridData writes an OpenDX origin to six decimals (5e-7 nm), and MRC holds it as
float32, whose half-spacing at 50 nm is 1.9e-6 nm; half a spacing is 0.0125 nm at
the finest grid FR-04 admits.
"""


@dataclass(frozen=True)
class DensityMap:
    """A 3D density map on the canonical stage-2 grid.

    Parameters
    ----------
    values
        float32, indexed ``[z, y, x]``, of shape ``grid.shape``.
    grid
        The canonical grid.
    header
        Everything else, as plain data: see the module docstring.
    """

    values: np.ndarray
    grid: DensityGrid
    header: Mapping[str, Canonicalisable]

    def __post_init__(self) -> None:
        """Hold the map as contiguous float32 and check it fits its grid."""
        import numpy as np

        object.__setattr__(self, "values", np.ascontiguousarray(self.values, dtype=np.float32))
        if tuple(self.values.shape) != self.grid.shape:
            raise GridFormatError(
                f"a density map of shape {tuple(self.values.shape)} does not fit its grid of "
                f"shape {self.grid.shape} (z, y, x)"
            )

    def digest(self) -> str:
        """Return a content hash over the values, the grid and the header.

        Recorded in the artefact's summary and never in its key (section 5.3.2).
        """
        return content_hash(
            f"{DENSITY_SCHEMA}/payload",
            {"values": self.values, "grid": self.grid.summary(), "header": dict(self.header)},
        )

    def write(self, path: Path) -> Path:
        """Write the map to ``path`` as compressed ``.npz``; return the path."""
        import numpy as np

        arrays: dict[str, Any] = {
            "values": self.values,
            "grid": np.asarray(json.dumps(self.grid.summary(), sort_keys=True)),
            "header": np.asarray(json.dumps(dict(self.header), sort_keys=True)),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as handle:
            np.savez_compressed(handle, **arrays)
        return path

    @classmethod
    def read(cls, path: Path) -> DensityMap:
        """Read a map from ``.npz``, OpenDX or CCP4/MRC, by suffix.

        Raises
        ------
        GridFormatError
            If the file is not a density map on a canonical grid, the suffix
            names no format this reads, or an interchange format is asked for
            without the ``structure`` extra.
        """
        suffix = path.suffix.lower()
        if suffix == ".npz":
            return cls._read_npz(path)
        if suffix in _INTERCHANGE:
            return cls._read_interchange(path)
        raise GridFormatError(
            f"cannot tell the format of {path.name!r}: a density map is .npz, .dx, .ccp4, .mrc "
            "or .map"
        )

    @classmethod
    def _read_npz(cls, path: Path) -> DensityMap:
        import numpy as np

        with np.load(path, allow_pickle=False) as data:
            missing = [key for key in ("values", "grid", "header") if key not in data.files]
            if missing:
                raise GridFormatError(
                    f"{path.name!r} is not a density map: it lacks {', '.join(missing)}"
                )
            values = np.asarray(data["values"], dtype=np.float32)
            grid = DensityGrid.from_summary(json.loads(str(data["grid"])))
            header = json.loads(str(data["header"]))
        return cls(values=values, grid=grid, header=header)

    @classmethod
    def _read_interchange(cls, path: Path) -> DensityMap:
        import numpy as np

        module = _grid_data_module()
        data = module.Grid(str(path))  # type: ignore[attr-defined]
        array = np.asarray(data.grid)
        if array.ndim != 3:
            raise GridFormatError(
                f"{path.name!r} holds an array of shape {tuple(array.shape)}; a density map is "
                "three-dimensional"
            )
        origin = np.asarray(data.origin, dtype=np.float64)
        delta = np.asarray(data.delta, dtype=np.float64).reshape(-1)[:3]
        # Both formats hold the spacing to about seven significant figures: OpenDX
        # writes it so, and MRC stores float32, which returns 0.05 as 0.0500000007.
        h = float(f"{float(delta[0]):.7g}")
        nx, ny, nz = (int(size) for size in array.shape)
        # The origin must sit on a node of the canonical lattice, or rounding it
        # would move every value by up to h/2 without a word.
        nodes = np.rint(origin / h)
        half_width = int(-nodes[0])
        if (
            float(np.max(np.abs(delta - h))) > SPACING_TOLERANCE_NM
            or float(np.max(np.abs(origin - nodes * h))) > LATTICE_TOLERANCE_NM
            or nx != ny
            or nx != 2 * half_width + 1
            or int(-nodes[1]) != half_width
        ):
            raise GridFormatError(
                f"{path.name!r} is not a canonical stage-2 grid: spacing {delta.tolist()} nm, "
                f"origin {origin.tolist()} nm, shape {tuple(array.shape)}. Stage 2 grids are "
                "square in (x, y), symmetric about the axis, with one spacing, and their nodes "
                "are integer multiples of it"
            )
        grid = DensityGrid(spacing_nm=h, half_width=half_width, z_first=int(nodes[2]), nz=nz)
        # gridData indexes [x, y, z]; this container indexes [z, y, x].
        values = np.transpose(array, (2, 1, 0)).astype(np.float32)
        return cls(values=values, grid=grid, header={"file": path.name})

    def export(self, path: Path) -> Path:
        """Write the map as OpenDX (``.dx``) or CCP4 (``.ccp4``, ``.mrc``, ``.map``).

        ``.npz`` writes the native format with its header. Returns the path.

        Raises
        ------
        GridFormatError
            If the suffix names no format, or GridDataFormats is not installed.
        """
        suffix = path.suffix.lower()
        if suffix == ".npz":
            return self.write(path)
        exporter = _INTERCHANGE.get(suffix)
        if exporter is None:
            raise GridFormatError(
                f"cannot export a density map as {path.name!r}: the formats are .npz, .dx, "
                ".ccp4, .mrc and .map"
            )
        import numpy as np

        module = _grid_data_module()
        data = module.Grid(  # type: ignore[attr-defined]
            grid=np.transpose(self.values, (2, 1, 0)),
            origin=self.grid.origin_nm,
            delta=(self.grid.spacing_nm,) * 3,
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        data.export(str(path), file_format=exporter)
        return path
