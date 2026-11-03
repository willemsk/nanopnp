"""The protonation artefact's payload: every frame's atoms, charges, radii and states."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from nanopnp.core.hashing import Canonicalisable, content_hash
from nanopnp.io.artefact import PROTONATION_SCHEMA

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

__all__ = [
    "PARENT_RESIDUE",
    "PAYLOAD_NAME",
    "ProtonationTable",
    "ProtonationTableError",
    "parent_residue",
]

PAYLOAD_NAME = "protonation"
"""The artefact's payload key, and the ``.npz`` file's stem."""

PARENT_RESIDUE: Mapping[str, str] = {
    # The PHY-16 step-3 NOTE's table, verbatim: every protonation-variant residue
    # name a CHARMM- or AMBER-named frame may carry, written as the titratable
    # parent PDB2PQR and PROPKA assign a state to.
    "HSD": "HIS",
    "HSE": "HIS",
    "HSP": "HIS",
    "HID": "HIS",
    "HIE": "HIS",
    "HIP": "HIS",
    "ASH": "ASP",
    "ASPP": "ASP",
    "GLH": "GLU",
    "GLUP": "GLU",
    "LYN": "LYS",
    "LSN": "LYS",
    "CYM": "CYS",
    "TYM": "TYR",
    "ARN": "ARG",
    # The disulfide-bonded cysteine of the AMBER-named force fields: PDB2PQR
    # writes it under SWANSON and PEOEPB, whose frames would otherwise name a
    # residue the ensemble calls CYS (PHY-16 step-3 NOTE).
    "CYX": "CYS",
}
"""Protonation-variant residue names and the parent each is written as (PHY-16 step-3 NOTE)."""


class ProtonationTableError(ValueError):
    """A protonation table that lacks an array its schema requires."""


def parent_residue(name: str) -> str:
    """Return the titratable parent of a protonation-variant residue name."""
    return PARENT_RESIDUE.get(name, name)


@dataclass(frozen=True)
class ProtonationTable:
    """The protonation artefact's payload: the atoms of every frame and their states.

    Parameters
    ----------
    frame_offsets
        Frame f spans frame_offsets[f]:frame_offsets[f + 1].
    positions_nm
        (atoms, 3) float64, in nm in stage 1's frame.
    expected_charge_e
        (frames, residues) float64; NaN where the expectation was not computed.
    """

    frame_offsets: np.ndarray
    positions_nm: np.ndarray
    charge_e: np.ndarray
    radius_nm: np.ndarray
    name: np.ndarray
    resname: np.ndarray
    chain: np.ndarray
    resid: np.ndarray
    icode: np.ndarray
    residue_chain: np.ndarray
    residue_resid: np.ndarray
    residue_icode: np.ndarray
    residue_name: np.ndarray
    residue_charge_e: np.ndarray
    tautomer: np.ndarray
    expected_charge_e: np.ndarray
    unapplied: np.ndarray
    group_residue: np.ndarray
    group_type: np.ndarray
    group_label: np.ndarray
    group_pka: np.ndarray
    header: Mapping[str, Canonicalisable]

    ARRAYS: ClassVar[tuple[str, ...]] = (
        "frame_offsets",
        "positions_nm",
        "charge_e",
        "radius_nm",
        "name",
        "resname",
        "chain",
        "resid",
        "icode",
        "residue_chain",
        "residue_resid",
        "residue_icode",
        "residue_name",
        "residue_charge_e",
        "tautomer",
        "expected_charge_e",
        "unapplied",
        "group_residue",
        "group_type",
        "group_label",
        "group_pka",
    )
    """Every array the ``.npz`` carries, beside ``header``."""

    @property
    def frames(self) -> int:
        """Return the number of frames."""
        return len(self.frame_offsets) - 1

    def frame_slice(self, frame: int) -> slice:
        """Return the atom range of one frame."""
        return slice(int(self.frame_offsets[frame]), int(self.frame_offsets[frame + 1]))

    def q_net_e(self) -> np.ndarray:
        """Return the net charge per frame, in e."""
        import numpy as np

        return np.array(
            [
                math.fsum(self.charge_e[self.frame_slice(frame)].tolist())
                for frame in range(self.frames)
            ]
        )

    def digest(self) -> str:
        """Return a content hash over every array and the header."""
        return content_hash(
            f"{PROTONATION_SCHEMA}/payload",
            {**{key: getattr(self, key) for key in self.ARRAYS}, "header": dict(self.header)},
        )

    def write(self, path: Path) -> Path:
        """Write the table to path as .npz, header included; return the path."""
        import numpy as np

        arrays: dict[str, Any] = {key: np.asarray(getattr(self, key)) for key in self.ARRAYS}
        arrays["header"] = np.asarray(json.dumps(dict(self.header), sort_keys=True))
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as handle:
            np.savez(handle, **arrays)
        return path

    @classmethod
    def read(cls, path: Path) -> ProtonationTable:
        """Read a table written by write, refusing one with a missing array."""
        import numpy as np

        with np.load(path, allow_pickle=False) as data:
            missing = [key for key in (*cls.ARRAYS, "header") if key not in data.files]
            if missing:
                raise ProtonationTableError(
                    f"{path.name!r} is not a protonation table: it lacks {', '.join(missing)}"
                )
            arrays = {key: np.asarray(data[key]) for key in cls.ARRAYS}
            header = json.loads(str(data["header"]))
        return cls(header=header, **arrays)
