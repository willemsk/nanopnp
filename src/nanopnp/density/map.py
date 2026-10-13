"""The stage-2 payload: the ensemble-mean density map and its npz, OpenDX and CCP4 IO."""

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

_INTERCHANGE: Mapping[str, str] = {".dx": "DX", ".ccp4": "MRC", ".mrc": "MRC", ".map": "MRC"}

# The interchange files' length unit (SPECIFICATION.md §8.2.2 B10).
ANGSTROM_PER_NM = 10.0

# gridData writes an OpenDX delta to seven significant figures.
SPACING_TOLERANCE_NM = 1e-6

# Above gridData's OpenDX origin rounding (5e-8 nm) and MRC float32 (1.5e-6 nm).
LATTICE_TOLERANCE_NM = 1e-5


@dataclass(frozen=True)
class DensityMap:
    values: np.ndarray
    grid: DensityGrid
    header: Mapping[str, Canonicalisable]

    def __post_init__(self) -> None:
        import numpy as np

        object.__setattr__(self, "values", np.ascontiguousarray(self.values, dtype=np.float32))
        if tuple(self.values.shape) != self.grid.shape:
            raise GridFormatError(
                f"a density map of shape {tuple(self.values.shape)} does not fit its grid of "
                f"shape {self.grid.shape} (z, y, x)"
            )

    def digest(self) -> str:
        return content_hash(
            f"{DENSITY_SCHEMA}/payload",
            {"values": self.values, "grid": self.grid.summary(), "header": dict(self.header)},
        )

    def write(self, path: Path) -> Path:
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
        # gridData guesses the reader from the extension and has none for .map.
        data = module.Grid(  # type: ignore[attr-defined]
            str(path), file_format=_INTERCHANGE[path.suffix.lower()]
        )
        array = np.asarray(data.grid)
        if array.ndim != 3:
            raise GridFormatError(
                f"{path.name!r} holds an array of shape {tuple(array.shape)}; a density map is "
                "three-dimensional"
            )
        origin = np.asarray(data.origin, dtype=np.float64) / ANGSTROM_PER_NM
        delta = np.asarray(data.delta, dtype=np.float64).reshape(-1)[:3] / ANGSTROM_PER_NM
        # MRC's float32 returns 0.5 Å as 0.500000007; seven figures reads it as the double 0.05 nm.
        h = float(f"{float(delta[0]):.7g}")
        nx, ny, nz = (int(size) for size in array.shape)
        # An origin off the lattice would shift every value by up to h/2 if rounded.
        nodes = np.rint(origin / h)
        half_width = int(-nodes[0])
        if (
            not float(np.max(np.abs(delta - h))) <= SPACING_TOLERANCE_NM
            or not float(np.max(np.abs(origin - nodes * h))) <= LATTICE_TOLERANCE_NM
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
            origin=tuple(value * ANGSTROM_PER_NM for value in self.grid.origin_nm),
            delta=(self.grid.spacing_nm * ANGSTROM_PER_NM,) * 3,
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        data.export(str(path), file_format=exporter)
        return path
