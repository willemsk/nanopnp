"""The aligned-ensemble payload of stage 1: coordinates, atom table and axis header."""

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

ATOM_FIELDS: tuple[str, ...] = ("element", "name", "resname", "resid", "icode", "chain")

CHAIN_CHARACTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"

ORIENTATION_RULE = (
    "x' = Q (x - p): the Cn axis on z through r = 0, signed to the file's +z (trans to cis), "
    "with z' = a.x so the file's axial coordinate is kept; the first chain in file order on +x "
    "and the others counter-clockwise in the recorded order. geometry.membrane.centre_z_nm is "
    "not applied here; stage 5 applies it"
)


class EnsembleFormatError(ValueError):
    """A stage-1 payload file is not an aligned ensemble this release reads."""


@dataclass(frozen=True)
class AlignedEnsemble:
    """The aligned ensemble: model-frame coordinates, the atoms, and the header."""

    positions_nm: np.ndarray
    element: np.ndarray
    name: np.ndarray
    resname: np.ndarray
    resid: np.ndarray
    icode: np.ndarray
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
        """Return a content hash over the payload's arrays and header."""
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
            If an array is missing, or the atom table and the coordinates disagree in length.
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

        Raises
        ------
        ValueError
            If the chain keys are longer than one character and there are too many chains for them.
        """
        import MDAnalysis as mda  # noqa: N813 - the alias the library documents
        import numpy as np
        from MDAnalysis.coordinates.memory import MemoryReader

        keys = list(zip(self.chain.tolist(), self.resid.tolist(), self.icode.tolist(), strict=True))
        starts = [0] + [index for index in range(1, len(keys)) if keys[index] != keys[index - 1]]
        boundary = np.zeros(len(keys), dtype=int)
        boundary[starts] = 1
        resindex = np.cumsum(boundary) - 1
        # One segment per chain key: a key too long for the PDB chain column survives as segid.
        chains = list(dict.fromkeys(self.chain.tolist()))
        segment_of = {chain: index for index, chain in enumerate(chains)}
        universe = mda.Universe.empty(
            self.atoms,
            n_residues=len(starts),
            n_segments=len(chains),
            atom_resindex=resindex,
            residue_segindex=np.array(
                [segment_of[str(self.chain[index])] for index in starts], dtype=int
            ),
            trajectory=True,
        )
        universe.add_TopologyAttr("names", self.name.tolist())
        universe.add_TopologyAttr("elements", self.element.tolist())
        # The PDB writer turns a multi-character chain into ``X``, merging chains; so give each
        # chain one character and carry the key in segid (first four characters kept).
        single = all(len(chain) == 1 for chain in chains)
        if single:
            chain_ids = self.chain.tolist()
        else:
            if len(chains) > len(CHAIN_CHARACTERS):
                raise ValueError(
                    f"{len(chains)} chains do not fit the {len(CHAIN_CHARACTERS)} "
                    "single-character chain identifiers of a PDB file, and their keys are "
                    "longer than one character"
                )
            chain_ids = [CHAIN_CHARACTERS[segment_of[str(chain)]] for chain in self.chain]
        universe.add_TopologyAttr("chainIDs", chain_ids)
        universe.add_TopologyAttr("resnames", [str(self.resname[i]) for i in starts])
        universe.add_TopologyAttr("resids", [int(self.resid[i]) for i in starts])
        universe.add_TopologyAttr("icodes", [str(self.icode[i]) for i in starts])
        universe.add_TopologyAttr("segids", [""] * len(chains) if single else chains)
        universe.load_new(
            np.asarray(self.positions_nm, dtype=np.float32) * np.float32(10.0), format=MemoryReader
        )
        directory.mkdir(parents=True, exist_ok=True)
        pdb, dcd = directory / f"{stem}.pdb", directory / f"{stem}.dcd"
        with warnings.catch_warnings():
            # The PDB writer warns for every defaulted record (occupancy, B-factor); no information.
            warnings.simplefilter("ignore")
            universe.trajectory[0]
            universe.atoms.write(str(pdb))
            with mda.Writer(str(dcd), self.atoms) as writer:
                for _ in universe.trajectory:
                    writer.write(universe.atoms)
        return pdb, dcd
