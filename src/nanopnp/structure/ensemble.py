"""The stage-1 artefact's payload: an aligned ensemble with its axis record (WP18 D10).

One ``.npz`` holds the aligned coordinates, float32 ``(frames, atoms, 3)`` in nm
in the model frame, and the atom table — element, name, residue name, residue
number and chain. The header travels in the same file, as a JSON string, and is
also the artefact's summary: the source and trajectory digests, the selection,
the chains in cyclic order, the frames as read, the superposition RMSD, the axis
in the file frame and the rotation ``Q`` that took it to z, every gate
measurement beside its threshold, and the per-frame axis drift.

**There is no van der Waals radius here.** It is a density-kernel parameter, so
it belongs in stage 2's key and not stage 1's (WP18 D10; the phase plan's
stage-artefact row).

Reading the payload needs NumPy alone, so a later stage, the GUI or a test can
open an ensemble without the ``structure`` extra. Only :meth:`AlignedEnsemble.export`
needs MDAnalysis, and imports it where it is used for that reason.
"""

from __future__ import annotations

import json
import warnings
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from nanopnp.core.hashing import Canonicalisable, content_hash
from nanopnp.io.artefact import STRUCTURE_SCHEMA

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

PAYLOAD_NAME = "ensemble"
"""The artefact's payload key, and the ``.npz`` file's stem."""

ATOM_FIELDS: tuple[str, ...] = ("element", "name", "resname", "resid", "chain")
"""The atom-table arrays the payload carries, in order."""

ORIENTATION_RULE = (
    "x' = Q (x - p): the Cn axis on z through r = 0, signed to the file's +z (trans to cis), "
    "with z' = a.x so the file's axial coordinate is kept; the first chain in file order on +x "
    "and the others counter-clockwise in the recorded order. geometry.membrane.centre_z_nm is "
    "not applied here; stage 5 applies it"
)
"""The frame convention of WP18 D8, recorded with every ensemble."""


class EnsembleFormatError(ValueError):
    """A stage-1 payload file is not an aligned ensemble this release reads."""


@dataclass(frozen=True)
class AlignedEnsemble:
    """The aligned ensemble: coordinates in the model frame, the atoms, and the header.

    Parameters
    ----------
    positions_nm
        ``(frames, atoms, 3)`` float32, in the model frame of WP18 D8.
    element, name, resname, chain
        String arrays, one entry per atom.
    resid
        Integer array, one entry per atom.
    header
        Everything else, as plain data: see the module docstring.
    """

    positions_nm: np.ndarray
    element: np.ndarray
    name: np.ndarray
    resname: np.ndarray
    resid: np.ndarray
    chain: np.ndarray
    header: Mapping[str, Canonicalisable]

    @property
    def frames(self) -> int:
        """Number of frames."""
        return int(self.positions_nm.shape[0])

    @property
    def atoms(self) -> int:
        """Number of atoms."""
        return int(self.positions_nm.shape[1])

    def digest(self) -> str:
        """Return a content hash over the payload's arrays and header.

        Recorded in the artefact's summary, never in its key: the coordinates come
        out of an SVD, and a key over their last bits would differ by platform
        (section 5.3.2).
        """
        return content_hash(
            f"{STRUCTURE_SCHEMA}/payload",
            {
                "positions_nm": self.positions_nm,
                **{field: getattr(self, field) for field in ATOM_FIELDS},
                "header": dict(self.header),
            },
        )

    def write(self, path: Path) -> Path:
        """Write the ensemble to ``path`` as ``.npz``, header included; return the path."""
        import numpy as np

        arrays: dict[str, Any] = {
            "positions_nm": np.asarray(self.positions_nm, dtype=np.float32),
            "header": np.asarray(json.dumps(dict(self.header), sort_keys=True)),
            **{field: np.asarray(getattr(self, field)) for field in ATOM_FIELDS},
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as handle:
            np.savez(handle, **arrays)
        return path

    @classmethod
    def read(cls, path: Path) -> AlignedEnsemble:
        """Read an ensemble written by :meth:`write`.

        Raises
        ------
        EnsembleFormatError
            If an array is missing, or the atom table and the coordinates
            disagree in length.
        """
        import numpy as np

        with np.load(path, allow_pickle=False) as data:
            missing = [
                key for key in ("positions_nm", "header", *ATOM_FIELDS) if key not in data.files
            ]
            if missing:
                raise EnsembleFormatError(
                    f"{path.name!r} is not an aligned ensemble: it lacks {', '.join(missing)}"
                )
            positions = np.asarray(data["positions_nm"], dtype=np.float32)
            fields = {field: np.asarray(data[field]) for field in ATOM_FIELDS}
            header = json.loads(str(data["header"]))
        if positions.ndim != 3 or positions.shape[2] != 3:
            raise EnsembleFormatError(
                f"{path.name!r}: positions_nm has shape {positions.shape}, not (frames, atoms, 3)"
            )
        for field, values in fields.items():
            if len(values) != positions.shape[1]:
                raise EnsembleFormatError(
                    f"{path.name!r}: {field} has {len(values)} entries for {positions.shape[1]} "
                    "atoms"
                )
        return cls(positions_nm=positions, header=header, **fields)

    def export(self, directory: Path, *, stem: str = "ensemble") -> tuple[Path, Path]:
        """Write the ensemble as a PDB topology and a DCD trajectory, in ångströms.

        For a molecular viewer or another tool; the ``.npz`` stays the native
        format. Written through MDAnalysis, so a reader of either file is reading
        what MDAnalysis wrote rather than a hand-rolled format.

        Returns
        -------
        tuple[Path, Path]
            The PDB (first frame) and the DCD (every frame).
        """
        import MDAnalysis as mda  # noqa: N813 - the alias the library documents
        import numpy as np
        from MDAnalysis.coordinates.memory import MemoryReader

        keys = list(zip(self.chain.tolist(), self.resid.tolist(), strict=True))
        starts = [0] + [index for index in range(1, len(keys)) if keys[index] != keys[index - 1]]
        boundary = np.zeros(len(keys), dtype=int)
        boundary[starts] = 1
        resindex = np.cumsum(boundary) - 1
        universe = mda.Universe.empty(
            self.atoms,
            n_residues=len(starts),
            n_segments=1,
            atom_resindex=resindex,
            residue_segindex=np.zeros(len(starts), dtype=int),
            trajectory=True,
        )
        universe.add_TopologyAttr("names", self.name.tolist())
        universe.add_TopologyAttr("elements", self.element.tolist())
        universe.add_TopologyAttr("chainIDs", self.chain.tolist())
        universe.add_TopologyAttr("resnames", [str(self.resname[i]) for i in starts])
        universe.add_TopologyAttr("resids", [int(self.resid[i]) for i in starts])
        universe.add_TopologyAttr("segids", [""])
        universe.load_new(
            np.asarray(self.positions_nm, dtype=np.float32) * np.float32(10.0), format=MemoryReader
        )
        directory.mkdir(parents=True, exist_ok=True)
        pdb, dcd = directory / f"{stem}.pdb", directory / f"{stem}.dcd"
        with warnings.catch_warnings():
            # The PDB writer warns for every record it fills with a default
            # (occupancy, B-factor, record type); none carries information here.
            warnings.simplefilter("ignore")
            universe.trajectory[0]
            universe.atoms.write(str(pdb))
            with mda.Writer(str(dcd), self.atoms) as writer:
                for _ in universe.trajectory:
                    writer.write(universe.atoms)
        return pdb, dcd
