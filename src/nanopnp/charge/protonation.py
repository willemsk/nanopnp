"""Stage 7, first half: protonation, partial charges and radii per frame (FR-12)."""

from __future__ import annotations

import contextlib
import dataclasses
import hashlib
import json
import logging
import math
import tempfile
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from nanopnp.charge.pqr import (
    PARENT_RESIDUE,
    PQRError,
    PQRFrame,
    chain_characters,
    check_same_residues,
    is_hydrogen,
    parent_residue,
    parse_pqr,
    read_pqr,
    write_pqr,
)
from nanopnp.core.hashing import Canonicalisable, content_hash, file_hash
from nanopnp.core.paths import store_root
from nanopnp.core.stages import (
    CancelToken,
    MissingExtraError,
    Progress,
    StageDescription,
    check_cancelled,
    describe,
    report,
)
from nanopnp.density.radii import RadiusSet, radius_set_digest
from nanopnp.io.artefact import (
    PROTONATION_FRAME_SCHEMA,
    PROTONATION_SCHEMA,
    Artefact,
    ProtonationArtefact,
)
from nanopnp.io.case import UnsupportedCaseSection
from nanopnp.io.resolved import ResolvedProtonation
from nanopnp.structure.ensemble import PAYLOAD_NAME as ENSEMBLE_PAYLOAD
from nanopnp.structure.ensemble import AlignedEnsemble

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

    from nanopnp.io.artefact import StageInputs
    from nanopnp.io.resolved import ResolvedCase
    from nanopnp.io.store import Store

__all__ = [
    "PAYLOAD_NAME",
    "ProtonationError",
    "ProtonationStage",
    "ProtonationTable",
    "export_pqr",
    "frame_pdb",
    "pdb2pqr_arguments",
    "protonation_parameters",
    "run_pdb2pqr",
]

logger = logging.getLogger(__name__)

PAYLOAD_NAME = "protonation"
"""The artefact's payload key, and the ``.npz`` file's stem."""

WORKSPACE_DIRNAME = "tmp"
"""Directory under the store root the payload is written to when no workspace is given."""

FIXED_FLAGS: tuple[str, ...] = ("--drop-water", "--keep-chain")
"""PHY-16 step 3's flags that no case key sets."""

REGISTRATION_TOLERANCE_A = 0.01
"""How far a supplied heavy atom may lie from its stage-1 atom, in Å (section 5.3.1 NOTE).

About ten times the rounding of a PQR's coordinate columns plus stage 1's float32
spacing, and a hundredth of the shortest heavy-atom bond.
"""

COORDINATE_DECIMALS = 3
"""The payload's coordinates lie on the 0.001 Å lattice a PQR prints, so an export reads back."""

Q_NET_TOLERANCE_E = 1e-6
"""How far ``Q_net`` may lie from an integer, in e (PHY-16 step 3)."""

MINIMUM_CALPHA = 3
"""C-alpha pairs a registration needs: three points fix a rigid motion."""

RADIUS_SET = "pdb2pqr_charmm"
"""The stage-2 radius set the PQR's radii are compared with under CHARMM."""

ACID_GROUPS: frozenset[str] = frozenset({"COO", "C-", "CYS", "TYR"})
"""PROPKA group types that carry -1 at a pH at or above their pKa."""

BASE_GROUPS: frozenset[str] = frozenset({"HIS", "LYS", "ARG", "N+"})
"""PROPKA group types that carry +1 at a pH below their pKa."""

FLIPPABLE: Mapping[str, frozenset[str]] = {
    "ASN": frozenset({"OD1", "ND2"}),
    "GLN": frozenset({"OE1", "NE2"}),
    "HIS": frozenset({"ND1", "CD2", "CE1", "NE2"}),
}
"""The heavy atoms PDB2PQR's hydrogen-bond optimisation may flip, by parent residue.

A flip turns an amide or an imidazole ring through 180 degrees about the bond to
it, and the group is not symmetric about that bond, so a flipped atom lands
0.13-0.40 Å from every atom it was given: on 2WCD at pH 7.5, 140 heavy atoms, in
44 asparagines, 92 glutamines and one histidine, and no other atom moved
(``.knowledge/07`` section 3, measured). They are not held to
the registration tolerance; the rest of each residue fixes where it is.
"""

WATER_RESIDUES: frozenset[str] = frozenset(
    {"HOH", "WAT", "H2O", "DOD", "SOL", "TIP3", "TP3M", "SPC"}
)
"""Water residue names, on neither side of a registration and never given to PDB2PQR.

``--drop-water`` removes only ``HOH`` and ``WAT`` (``aa.WAT.water_residue_names``,
PDB2PQR 3.7.1), so the frame PDB leaves the rest out itself rather than hand
PDB2PQR a ``SOL`` it cannot parameterise or :func:`frame_pdb` a ``TIP3`` its
columns cannot hold. ``TP3M`` is the name ``--ffout=CHARMM`` gives a water it keeps.
"""

# The library loggers raised to WARNING during a call; the versioned one is added.
_LOGGERS: tuple[str, ...] = ("pdb2pqr", "propka")

# The extra that carries PDB2PQR and PROPKA (``pyproject.toml``).
_EXTRA = "structure"


class ProtonationError(RuntimeError):
    """A protonation gate failed, naming the frame and the residue or atom."""


def pdb2pqr_arguments(settings: ResolvedProtonation) -> tuple[str, ...]:
    """Return the flags PDB2PQR is run with, without the two paths."""
    flags = [f"--ff={settings.forcefield}", f"--ffout={settings.forcefield}"]
    if settings.titration != "none":
        flags += [f"--with-ph={settings.ph!r}", f"--titration-state-method={settings.titration}"]
    return (*flags, *FIXED_FLAGS)


def protonation_parameters(settings: ResolvedProtonation) -> dict[str, Canonicalisable]:
    """Return the produced artefact's key parameters, which also key each frame."""
    return {
        "source": "pdb2pqr",
        "ph": settings.ph,
        "forcefield": settings.forcefield,
        "titration": settings.titration,
        "arguments": list(pdb2pqr_arguments(settings)),
        "normalisation": dict(sorted(PARENT_RESIDUE.items())),
        "coordinate_decimals": COORDINATE_DECIMALS,
        "gates": _gate_parameters(),
    }


def supplied_parameters() -> dict[str, Canonicalisable]:
    """Return a supplied artefact's key parameters."""
    return {
        "source": "inputs.pqr",
        "normalisation": dict(sorted(PARENT_RESIDUE.items())),
        "coordinate_decimals": COORDINATE_DECIMALS,
        "gates": _gate_parameters(),
    }


def _gate_parameters() -> dict[str, Canonicalisable]:
    return {
        "registration_tolerance_A": REGISTRATION_TOLERANCE_A,
        "q_net_tolerance_e": Q_NET_TOLERANCE_E,
        "minimum_calpha": MINIMUM_CALPHA,
    }


def _versions() -> dict[str, Canonicalisable]:
    found: dict[str, Canonicalisable] = {}
    for distribution in ("pdb2pqr", "propka"):
        try:
            found[distribution] = metadata.version(distribution)
        except metadata.PackageNotFoundError:
            found[distribution] = None
    return found


def _residue_label(name: str, resid: int, icode: str, chain: str) -> str:
    return f"{name} {resid}{icode} of chain {chain!r}"


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
                raise PQRError(
                    f"{path.name!r} is not a protonation table: it lacks {', '.join(missing)}"
                )
            arrays = {key: np.asarray(data[key]) for key in cls.ARRAYS}
            header = json.loads(str(data["header"]))
        return cls(header=header, **arrays)

    def pqr_frames(self) -> tuple[PQRFrame, ...]:
        """Return the frames in angstrom, each value the one that reads back to this table."""
        positions_A = _angstrom(self.positions_nm, COORDINATE_DECIMALS, lattice=True)
        radius_A = _angstrom(self.radius_nm, 4, lattice=False)
        frames = []
        for frame in range(self.frames):
            atoms = self.frame_slice(frame)
            frames.append(
                PQRFrame(
                    name=self.name[atoms],
                    resname=self.resname[atoms],
                    chain=self.chain[atoms],
                    resid=self.resid[atoms],
                    icode=self.icode[atoms],
                    positions_A=positions_A[atoms],
                    charge_e=self.charge_e[atoms],
                    radius_A=radius_A[atoms],
                )
            )
        return tuple(frames)


def _angstrom(values_nm: np.ndarray, decimals: int, *, lattice: bool) -> np.ndarray:
    import numpy as np

    values = np.asarray(values_nm, dtype=np.float64)
    found = np.round(values * 10.0, decimals)
    wrong = found * 0.1 != values
    if not wrong.any():
        return found
    if lattice:
        raise ValueError(
            f"{int(wrong.sum())} coordinates are not on the 0.001 Å lattice a PQR file prints"
        )
    target = values[wrong]
    start = target * 10.0
    result = np.full_like(start, np.nan)
    up, down = start.copy(), start.copy()
    for candidate in (start, *_neighbours(up, down)):
        hit = np.isnan(result) & (candidate * 0.1 == target)
        result[hit] = candidate[hit]
    if np.isnan(result).any():  # pragma: no cover - the original value is always a neighbour
        raise ValueError("a value has no ångström reading that converts back to it exactly")
    found[wrong] = result
    return found


def _neighbours(up: np.ndarray, down: np.ndarray, steps: int = 4) -> Iterator[np.ndarray]:
    import numpy as np

    for _ in range(steps):
        up = np.nextafter(up, np.inf)
        down = np.nextafter(down, -np.inf)
        yield up
        yield down


def frame_pdb(
    ensemble: AlignedEnsemble,
    frame: int,
    heavy: np.ndarray,
    chains: Mapping[str, str],
) -> bytes:
    """Return the PDB that PDB2PQR is given for one frame, heavy atoms only."""
    lines: list[str] = []
    positions = ensemble.positions_nm[frame] * 10.0
    for serial, index in enumerate(heavy.tolist(), start=1):
        name = str(ensemble.name[index])
        resname = parent_residue(str(ensemble.resname[index]))
        resid = int(ensemble.resid[index])
        chain = chains[str(ensemble.chain[index])]
        x, y, z = (float(value) for value in positions[index])
        if len(resname) > 3 or not -999 <= resid <= 9999:
            raise ProtonationError(
                f"frame {frame}: residue {resname} {resid} of chain {str(ensemble.chain[index])!r} "
                "does not fit the PDB columns PDB2PQR reads"
            )
        if not all(-999.999 <= value <= 9999.999 for value in (x, y, z)):
            raise ProtonationError(
                f"frame {frame}: atom {name} of {resname} {resid} lies at ({x:.3f}, {y:.3f}, "
                f"{z:.3f}) Å, outside the PDB coordinate columns"
            )
        field = name if len(name) >= 4 else f" {name:<3}"
        lines.append(
            f"ATOM  {serial % 100000:5d} {field:<4} {resname:<3} {chain:1}{resid:4d}"
            f"{str(ensemble.icode[index])[:1]:1}   {x:8.3f}{y:8.3f}{z:8.3f}{1.0:6.2f}{0.0:6.2f}"
            f"          {str(ensemble.element[index]).upper():>2}"
        )
    lines.append("END")
    return ("\n".join(lines) + "\n").encode("ascii")


@contextlib.contextmanager
def _quiet_libraries() -> Iterator[Counter[str]]:
    collected: Counter[str] = Counter()

    class _Collect(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            collected[record.getMessage()] += 1

    names = list(_LOGGERS)
    with contextlib.suppress(ImportError, AttributeError):
        from pdb2pqr.main import VERSION

        names.append(f"PDB2PQR{VERSION}")
    handler = _Collect(level=logging.WARNING)
    saved = []
    for name in names:
        library = logging.getLogger(name)
        saved.append((library, library.level, library.propagate))
        library.setLevel(logging.WARNING)
        library.propagate = False
        library.addHandler(handler)
    try:
        yield collected
    finally:
        for library, level, propagate in saved:
            library.removeHandler(handler)
            library.setLevel(level)
            library.propagate = propagate


def _require_pdb2pqr() -> None:
    try:
        import pdb2pqr.main  # noqa: F401 - imported to prove it is there
        import propka  # noqa: F401
    except ImportError as error:
        missing = getattr(error, "name", None) or "pdb2pqr"
        raise MissingExtraError(
            f"stage 'protonation' runs PDB2PQR and PROPKA on a structure: section, and needs the "
            f"{_EXTRA!r} extra: importing {missing!r} failed. Install the extras with "
            "`uv sync --all-extras`, or supply the charges through inputs.pqr, which needs none",
            name=missing,
        ) from error


def _instance_annotations(self: object, name: str) -> Any:  # noqa: ANN401 - mirrors __getattr__
    if name == "__annotations__":
        return type(self).__annotations__
    raise AttributeError(f"{type(self).__name__!r} object has no attribute {name!r}")


def restore_propka_annotations() -> bool:
    """Let PROPKA read its parameter file on Python 3.14; return whether it had to."""
    from propka.parameters import Parameters

    if hasattr(Parameters(), "__annotations__"):
        return False
    Parameters.__getattr__ = _instance_annotations  # type: ignore[attr-defined]
    return True


def run_pdb2pqr(pdb: Path, pqr: Path, settings: ResolvedProtonation) -> dict[str, Canonicalisable]:
    """Run PDB2PQR in-process on one PDB file and return what it reported.

    Parameters
    ----------
    pdb
        The input file; it must exist, or PDB2PQR would fetch it from the network.
    """
    from pdb2pqr.main import run_pdb2pqr as pdb2pqr_main

    restore_propka_annotations()
    source = pdb.resolve()
    if not source.is_file():
        raise FileNotFoundError(f"the frame PDB {source} is not a file")
    with _quiet_libraries() as warnings:
        missing, pka_rows, _ = pdb2pqr_main(
            [*pdb2pqr_arguments(settings), str(source), str(pqr.resolve())]
        )
    return {
        "pka": [_pka_row(row) for row in (pka_rows or [])],
        "missing": [_describe_atom(atom) for atom in (missing or [])],
        "warnings": dict(sorted(warnings.items())),
    }


def _pka_row(row: Mapping[str, Any]) -> dict[str, Canonicalisable]:
    pka = row.get("pKa")
    return {
        "chain": str(row.get("chain_id", "")).strip(),
        "resid": int(row["res_num"]),
        "icode": str(row.get("ins_code", "") or "").strip(),
        "resname": str(row.get("res_name", "")),
        "group_type": str(row.get("group_type", "")),
        "group_label": str(row.get("group_label", "")),
        "pka": float(pka) if pka is not None else None,
    }


def _describe_atom(atom: object) -> str:
    residue = getattr(atom, "residue", None)
    return (
        f"{getattr(atom, 'name', '?')} of {getattr(residue, 'name', '?')} "
        f"{getattr(atom, 'res_seq', '?')} of chain {getattr(atom, 'chain_id', '?')!r}"
    )


ResidueKey = tuple[str, int, str]
"""A residue's identity: chain key, number and insertion code."""


def _residue_keys(frame: PQRFrame) -> list[ResidueKey]:
    return list(zip(frame.chain.tolist(), frame.resid.tolist(), frame.icode.tolist(), strict=True))


def _rechain(frame: PQRFrame, keys: Mapping[str, str]) -> PQRFrame:
    import numpy as np

    chain = np.array([keys.get(value, value) for value in frame.chain.tolist()], dtype=str)
    return dataclasses.replace(frame, chain=chain)


def _tautomer(atoms: set[str]) -> str:
    delta, epsilon = "HD1" in atoms, "HE2" in atoms
    if delta and epsilon:
        return "HSP"
    if delta:
        return "HSD"
    if epsilon:
        return "HSE"
    return ""


def _group_state(group_type: str, pka: float, ph: float) -> float | None:
    if group_type in ACID_GROUPS:
        return -1.0 if ph >= pka else 0.0
    if group_type in BASE_GROUPS:
        return 1.0 if ph < pka else 0.0
    return None


@dataclass(frozen=True)
class _Reference:
    # Every residue but water, in order: its key and its parent name.
    residues: dict[ResidueKey, str]
    # Indices of those residues' heavy atoms in the ensemble's atom table.
    heavy: np.ndarray
    heavy_residue: list[ResidueKey]
    heavy_name: list[str]
    # Indices of the heavy atoms of :data:`FLIPPABLE`, which are not held to the tolerance.
    flippable: np.ndarray
    # Each residue's one C-alpha, as an ensemble atom index.
    calpha: dict[ResidueKey, int]
    # Heavy atoms by residue and element, in each residue holding :data:`FLIPPABLE` atoms.
    flippable_elements: Counter[tuple[ResidueKey, str]]

    @property
    def flippable_residues(self) -> set[ResidueKey]:
        return {key for key, _ in self.flippable_elements}


def _reference(ensemble: AlignedEnsemble) -> _Reference:
    import numpy as np

    residues: dict[ResidueKey, str] = {}
    heavy: list[int] = []
    heavy_residue: list[ResidueKey] = []
    heavy_name: list[str] = []
    flippable: list[int] = []
    flippable_elements: Counter[tuple[ResidueKey, str]] = Counter()
    calphas: dict[ResidueKey, list[int]] = {}
    for atom, (chain, resid, icode, resname, name, element) in enumerate(
        zip(
            ensemble.chain.tolist(),
            ensemble.resid.tolist(),
            ensemble.icode.tolist(),
            ensemble.resname.tolist(),
            ensemble.name.tolist(),
            ensemble.element.tolist(),
            strict=True,
        )
    ):
        if resname in WATER_RESIDUES:
            continue
        key = (str(chain), int(resid), str(icode).strip())
        parent = residues.setdefault(key, parent_residue(str(resname)))
        if str(element).strip().upper() == "H":
            continue
        if parent in FLIPPABLE:
            flippable_elements[(key, _element(str(name)))] += 1
        if name in FLIPPABLE.get(parent, ()):
            flippable.append(atom)
            continue
        heavy.append(atom)
        heavy_residue.append(key)
        heavy_name.append(str(name))
        if name == "CA":
            calphas.setdefault(key, []).append(atom)
    return _Reference(
        residues=residues,
        heavy=np.asarray(heavy, dtype=np.intp),
        heavy_residue=heavy_residue,
        heavy_name=heavy_name,
        flippable=np.asarray(flippable, dtype=np.intp),
        calpha={key: atoms[0] for key, atoms in calphas.items() if len(atoms) == 1},
        flippable_elements=flippable_elements,
    )


def _element(name: str) -> str:
    return name.lstrip("0123456789")[:1].upper()


def _residue_mismatch(frame: PQRFrame, reference: _Reference) -> str | None:
    found = {
        (chain, resid, icode): parent_residue(name)
        for chain, resid, icode, name in frame.residues()
        if name not in WATER_RESIDUES
    }
    for (chain, resid, icode), name in reference.residues.items():
        other = found.get((chain, resid, icode))
        if other is None:
            return f"it lacks the ensemble's {_residue_label(name, resid, icode, chain)}"
        if other != name:
            return (
                f"it names {_residue_label(other, resid, icode, chain)} what the ensemble names "
                f"{name}"
            )
    for (chain, resid, icode), name in found.items():
        if (chain, resid, icode) not in reference.residues:
            return (
                f"it holds {_residue_label(name, resid, icode, chain)}, which the ensemble does not"
            )
    return None


def _kabsch(moving: np.ndarray, fixed: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    import numpy as np

    centre_moving, centre_fixed = moving.mean(axis=0), fixed.mean(axis=0)
    covariance = (moving - centre_moving).T @ (fixed - centre_fixed)
    u, _, vt = np.linalg.svd(covariance)
    sign = 1.0 if np.linalg.det(vt.T @ u.T) >= 0.0 else -1.0
    rotation = vt.T @ np.diag([1.0, 1.0, sign]) @ u.T
    return rotation, centre_fixed - rotation @ centre_moving


@dataclass(frozen=True)
class _Registration:
    positions_A: np.ndarray
    moved: bool
    # The largest distance from a compared heavy atom to its match.
    worst_A: float
    # The largest distance from a :data:`FLIPPABLE` atom to the nearest heavy atom.
    flipped_A: float
    # How many :data:`FLIPPABLE` atoms lie farther than the tolerance from every heavy atom.
    flipped: int
    added_heavy: int
    failure: str | None


def _register(
    frame: PQRFrame, target_A: np.ndarray, reference: _Reference, *, may_move: bool
) -> _Registration:
    import numpy as np
    from scipy.spatial import cKDTree

    keys = _residue_keys(frame)
    heavy = np.array([not is_hydrogen(name) for name in frame.name.tolist()], dtype=bool)
    candidates = np.flatnonzero(heavy)
    fixed = target_A[reference.heavy]
    added = len(candidates) - len(fixed) - len(reference.flippable)

    def flipped(positions: np.ndarray) -> tuple[float, int]:
        if not len(reference.flippable) or not len(candidates):
            return 0.0, 0
        distance, _ = cKDTree(positions[candidates]).query(target_A[reference.flippable], k=1)
        return float(distance.max()), int((distance > REGISTRATION_TOLERANCE_A).sum())

    def check(positions: np.ndarray) -> tuple[float, str | None]:
        if not len(candidates):
            return float("inf"), "it holds no heavy atom"
        distance, nearest = cKDTree(positions[candidates]).query(fixed, k=1)
        nearest = np.minimum(nearest, len(candidates) - 1)
        matched = candidates[nearest]
        ok = (distance <= REGISTRATION_TOLERANCE_A) & np.array(
            [
                keys[int(atom)] == key
                for atom, key in zip(matched, reference.heavy_residue, strict=True)
            ],
            dtype=bool,
        )
        worst = float(distance[ok].max()) if ok.any() else float("inf")
        if not ok.all():
            first = int(np.flatnonzero(~ok)[0])
            key = reference.heavy_residue[first]
            own = [int(atom) for atom in candidates if keys[int(atom)] == key]
            gap = (
                float(np.linalg.norm(positions[own] - fixed[first], axis=1).min())
                if own
                else float("inf")
            )
            chain, resid, icode = key
            return worst, (
                f"{int((~ok).sum())} of the ensemble's {len(fixed)} heavy atoms lie farther than "
                f"{REGISTRATION_TOLERANCE_A} Å from every heavy atom of their residue in the PQR; "
                f"the first is {reference.heavy_name[first]} of "
                f"{_residue_label(reference.residues[key], resid, icode, chain)}, {gap:.4f} Å "
                "from the nearest"
            )
        if len(np.unique(matched)) != len(matched):
            return worst, "two heavy atoms of the ensemble match one heavy atom of the PQR"
        # The flippable atoms are not compared, but a flip moves them and never
        # removes them or changes their element. Counted by element, because a
        # terminal oxygen PDB2PQR adds would otherwise stand in for a lost N.
        residues = reference.flippable_residues
        held = Counter(
            (keys[int(atom)], _element(str(frame.name[atom])))
            for atom in candidates
            if keys[int(atom)] in residues
        )
        for (key, element), count in reference.flippable_elements.items():
            if held[(key, element)] < count:
                chain, resid, icode = key
                return worst, (
                    f"it holds {held[(key, element)]} {element} atoms of "
                    f"{_residue_label(reference.residues[key], resid, icode, chain)} and the "
                    f"ensemble {count}; a flip moves heavy atoms and never removes them"
                )
        return worst, None

    positions = frame.positions_A
    worst, failure = check(positions)
    if failure is None or not may_move:
        return _Registration(positions, False, worst, *flipped(positions), added, failure)
    calpha: dict[ResidueKey, list[int]] = {}
    for atom in candidates.tolist():
        if frame.name[atom] == "CA":
            calpha.setdefault(keys[atom], []).append(atom)
    pairs = [
        (reference.calpha[key], atoms[0])
        for key, atoms in calpha.items()
        if len(atoms) == 1 and key in reference.calpha
    ]
    if len(pairs) < MINIMUM_CALPHA:
        return _Registration(
            positions,
            False,
            worst,
            *flipped(positions),
            added,
            f"it shares {len(pairs)} C-alpha atoms with the ensemble, one per residue, and a "
            f"superposition needs {MINIMUM_CALPHA}",
        )
    ensemble_atoms = np.array([pair[0] for pair in pairs], dtype=np.intp)
    pqr_atoms = np.array([pair[1] for pair in pairs], dtype=np.intp)
    rotation, shift = _kabsch(positions[pqr_atoms], target_A[ensemble_atoms])
    positions = np.round(positions @ rotation.T + shift, COORDINATE_DECIMALS)
    worst, failure = check(positions)
    return _Registration(positions, True, worst, *flipped(positions), added, failure)


def _gate(frame: PQRFrame, index: int) -> float:
    import numpy as np

    bad = np.flatnonzero((frame.charge_e != 0.0) & ~(frame.radius_A > 0.0))
    if bad.size:
        atom = int(bad[0])
        residue = _residue_label(
            str(frame.resname[atom]),
            int(frame.resid[atom]),
            str(frame.icode[atom]),
            str(frame.chain[atom]),
        )
        raise ProtonationError(
            f"frame {index}: {bad.size} charged atoms have a radius that is not positive; the "
            f"first is {frame.name[atom]} of {residue}"
            f", charge {float(frame.charge_e[atom])} e and radius {float(frame.radius_A[atom])} Å, "
            "and PHY-16 step 4's kernel width w = 0.5 R would not be positive (section 5.3.1 NOTE "
            "on the protonation keys)"
        )
    q_net = math.fsum(frame.charge_e.tolist())
    if not abs(q_net - round(q_net)) <= Q_NET_TOLERANCE_E:
        raise ProtonationError(
            f"frame {index}: Q_net = {q_net!r} e is {abs(q_net - round(q_net)):.3g} e from an "
            f"integer, more than {Q_NET_TOLERANCE_E} e (PHY-16 step 3); an atom carries a charge "
            "its force field does not give it"
        )
    return q_net


def _chain_differences(
    residues: Sequence[tuple[str, int, str, str]], charges: np.ndarray
) -> list[dict[str, Canonicalisable]]:
    sequences: dict[str, list[tuple[int, str, str]]] = {}
    positions: dict[str, dict[tuple[int, str], int]] = {}
    for index, (chain, resid, icode, name) in enumerate(residues):
        sequences.setdefault(chain, []).append((resid, icode, parent_residue(name)))
        positions.setdefault(chain, {})[(resid, icode)] = index
    groups: dict[tuple[tuple[int, str, str], ...], list[str]] = {}
    for chain, sequence in sequences.items():
        groups.setdefault(tuple(sequence), []).append(chain)
    found: list[dict[str, Canonicalisable]] = []
    for shared, chains in groups.items():
        if len(chains) < 2:
            continue
        for resid, icode, name in shared:
            columns = [positions[chain][(resid, icode)] for chain in chains]
            frames = [
                frame
                for frame in range(charges.shape[0])
                if len({round(float(charges[frame, column])) for column in columns}) > 1
            ]
            if not frames:
                continue
            first = frames[0]
            found.append(
                {
                    "residue": f"{name} {resid}{icode}",
                    "frames": frames,
                    "charges_e": {
                        chain: round(float(charges[first, column]))
                        for chain, column in zip(chains, columns, strict=True)
                    },
                }
            )
    return found


def _unapplied(
    residues: Sequence[tuple[str, int, str, str]],
    charges: np.ndarray,
    expected: np.ndarray,
    unapplied: np.ndarray,
) -> list[dict[str, Canonicalisable]]:
    import numpy as np

    found: list[dict[str, Canonicalisable]] = []
    for column in np.flatnonzero(unapplied.any(axis=0)).tolist():
        chain, resid, icode, name = residues[column]
        frames = np.flatnonzero(unapplied[:, column]).tolist()
        first = frames[0]
        found.append(
            {
                "chain": chain,
                "residue": f"{name} {resid}{icode}",
                "frames": len(frames),
                "first_frame": first,
                "applied_e": round(float(charges[first, column])),
                "expected_e": round(float(expected[first, column])),
            }
        )
    return found


def _table_radius(radius_set: RadiusSet, resname: str, name: str) -> float:
    try:
        return radius_set.radius_A(resname, name)
    except KeyError:
        parent = parent_residue(resname)
        if parent == resname:
            raise
        return radius_set.radius_A(parent, name)


def _radii(
    frames: Sequence[PQRFrame],
    tautomers: Sequence[Sequence[str]],
    residues: Sequence[tuple[str, int, str, str]],
) -> dict[str, Canonicalisable]:
    radius_set = RadiusSet.load(RADIUS_SET)
    index_of = {key[:3]: i for i, key in enumerate(residues)}
    counts: Counter[tuple[str, str, float]] = Counter()
    for frame, tautomer in zip(frames, tautomers, strict=True):
        for name, resname, key, radius in zip(
            frame.name.tolist(),
            frame.resname.tolist(),
            _residue_keys(frame),
            frame.radius_A.tolist(),
            strict=True,
        ):
            lookup = tautomer[index_of[key]] or str(resname)
            counts[(lookup, str(name), float(radius))] += 1
    compared = differing = heavy_differing = unresolved = heavy_unresolved = 0
    worst: dict[str, Canonicalisable] | None = None
    worst_difference = 0.0
    unresolved_names: list[str] = []
    for (resname, name, radius), count in sorted(counts.items()):
        try:
            table = _table_radius(radius_set, resname, name)
        except KeyError:
            unresolved += count
            heavy_unresolved += 0 if is_hydrogen(name) else count
            if len(unresolved_names) < 10:
                unresolved_names.append(f"{resname} {name}")
            continue
        compared += count
        difference = abs(radius - table)
        if difference <= 0.5e-4:
            continue
        differing += count
        heavy_differing += 0 if is_hydrogen(name) else count
        if worst is None or difference > worst_difference:
            worst_difference = difference
            worst = {
                "residue": resname,
                "atom": name,
                "pqr_A": radius,
                "table_A": table,
                "difference_A": difference,
            }
    return {
        "set": RADIUS_SET,
        "sha256": radius_set_digest(RADIUS_SET),
        "compared": compared,
        "differing": differing,
        "heavy_differing": heavy_differing,
        "unresolved": unresolved,
        "heavy_unresolved": heavy_unresolved,
        "unresolved_examples": unresolved_names,
        "worst": worst,
    }


def _assemble(
    frames: Sequence[PQRFrame],
    pka: Sequence[Sequence[Mapping[str, Canonicalisable]]] | None,
    *,
    ph: float,
    header: Mapping[str, Canonicalisable],
    compare_radii: bool = True,
) -> tuple[ProtonationTable, dict[str, Canonicalisable]]:
    import numpy as np

    residues = frames[0].residues()
    index_of = {key[:3]: i for i, key in enumerate(residues)}
    count = len(residues)
    shape = (len(frames), count)
    residue_charge = np.zeros(shape)
    tautomer = np.full(shape, "", dtype="<U3")
    expected = np.full(shape, np.nan)
    # Keyed on the label as well as the type: a C-terminal ASP or GLU carries
    # two COO groups, its side chain's and the terminus's, which PROPKA types alike.
    groups: dict[tuple[int, str, str], int] = {}
    group_values: list[dict[int, float]] = []
    q_net: list[float] = []
    for number, frame in enumerate(frames):
        q_net.append(_gate(frame, number))
        owner = np.array([index_of[key] for key in _residue_keys(frame)], dtype=np.intp)
        residue_charge[number] = np.bincount(owner, weights=frame.charge_e, minlength=count)
        atoms: list[set[str]] = [set() for _ in residues]
        for residue, name in zip(owner.tolist(), frame.name.tolist(), strict=True):
            atoms[residue].add(name)
        for residue, (_, _, _, name) in enumerate(residues):
            if parent_residue(name) == "HIS":
                tautomer[number, residue] = _tautomer(atoms[residue])
        values: dict[int, float] = {}
        for row in pka[number] if pka is not None else ():
            residue = index_of.get((str(row["chain"]), int(str(row["resid"])), str(row["icode"])))
            value = row.get("pka")
            if residue is None or value is None:
                continue
            group_type = str(row["group_type"])
            label = str(row.get("group_label", ""))
            values[groups.setdefault((residue, group_type, label), len(groups))] = float(str(value))
            state = _group_state(group_type, float(str(value)), ph)
            if state is not None:
                previous = expected[number, residue]
                expected[number, residue] = (0.0 if np.isnan(previous) else previous) + state
        group_values.append(values)
    group_pka = np.full((len(frames), len(groups)), np.nan)
    for number, values in enumerate(group_values):
        for group, value in values.items():
            group_pka[number, group] = value
    unapplied = ~np.isnan(expected) & (np.abs(residue_charge - np.nan_to_num(expected)) > 0.5)
    offsets = np.cumsum([0, *(frame.atoms for frame in frames)]).astype(np.int64)
    positions_A = np.round(
        np.concatenate([frame.positions_A for frame in frames]), COORDINATE_DECIMALS
    )
    ordered = sorted(groups, key=groups.__getitem__)
    table = ProtonationTable(
        frame_offsets=offsets,
        positions_nm=positions_A * 0.1,
        charge_e=np.concatenate([frame.charge_e for frame in frames]),
        radius_nm=np.concatenate([frame.radius_A for frame in frames]) * 0.1,
        name=np.concatenate([frame.name for frame in frames]).astype(str),
        resname=np.concatenate([frame.resname for frame in frames]).astype(str),
        chain=np.concatenate([frame.chain for frame in frames]).astype(str),
        resid=np.concatenate([frame.resid for frame in frames]).astype(np.int64),
        icode=np.concatenate([frame.icode for frame in frames]).astype(str),
        residue_chain=np.array([key[0] for key in residues], dtype=str),
        residue_resid=np.array([key[1] for key in residues], dtype=np.int64),
        residue_icode=np.array([key[2] for key in residues], dtype=str),
        residue_name=np.array([key[3] for key in residues], dtype=str),
        residue_charge_e=residue_charge,
        tautomer=tautomer,
        expected_charge_e=expected,
        unapplied=unapplied,
        group_residue=np.array([group[0] for group in ordered], dtype=np.int64),
        group_type=np.array([group[1] for group in ordered], dtype=str),
        group_label=np.array([group[2] for group in ordered], dtype=str),
        group_pka=group_pka,
        header=dict(header),
    )
    record: dict[str, Canonicalisable] = {
        # Integers, as the gate has just shown each to be to 1e-6 e; the
        # residual a sum of four-decimal charges leaves in binary is recorded
        # beside them rather than in them.
        "q_net_e": [round(value) for value in q_net],
        "q_net_residual_e": max(abs(value - round(value)) for value in q_net),
        "atoms": [frame.atoms for frame in frames],
        "residues": count,
        "unapplied": _unapplied(residues, residue_charge, expected, unapplied),
        "chain_differences": _chain_differences(residues, residue_charge),
        "radii": (
            _radii(frames, tautomer.tolist(), residues)
            if compare_radii
            else {
                "set": RADIUS_SET,
                "status": (
                    f"not compared: the PQR's radii are {header.get('forcefield')}'s, and the "
                    "stage-2 table is CHARMM's (D14)"
                ),
            }
        ),
    }
    return table, record


def export_pqr(payload: Path, path: Path) -> Path:
    """Write a stored protonation table as a PQR file, one MODEL per frame, in angstrom."""
    table = ProtonationTable.read(payload)
    recorded = table.header.get("chains")
    chains = (
        {str(key): str(letter) for key, letter in recorded.items()}
        if isinstance(recorded, Mapping)
        else chain_characters(table.chain.tolist())
    )
    return write_pqr(path, table.pqr_frames(), chains=chains)


def _resolved(inputs: StageInputs) -> ResolvedCase:
    resolved = inputs.resolved
    if not resolved.protonates:
        raise UnsupportedCaseSection(
            f"case {inputs.resolved.name!r} has nothing for the protonation stage to read: it "
            + (
                "supplies inputs.charge, which replaces what stage 7 makes of the protonation"
                if resolved.charge is not None
                else "carries no structure: section and supplies no inputs.pqr"
            )
        )
    return resolved


class ProtonationStage:
    """Stage 7, first half: the aligned ensemble, or inputs.pqr, to an atom table."""

    name = "protonation"

    def __init__(self, *, workspace: Path | None = None, store: Store | None = None) -> None:
        self._workspace = Path(workspace) if workspace is not None else None
        self._store = store

    def describe(self) -> StageDescription:
        """Return the registry's description of this stage."""
        return describe(self.name)

    def key(self, inputs: StageInputs) -> ProtonationArtefact:
        """Return the artefact key of this stage."""
        return self._key(inputs, _resolved(inputs))

    @staticmethod
    def _key(inputs: StageInputs, resolved: ResolvedCase) -> ProtonationArtefact:
        if resolved.pqr is not None:
            assert resolved.pqr.path is not None
            keyed = {"pqr": file_hash(resolved.pqr.path)}
            if resolved.structure is not None:
                keyed["structure"] = inputs.require("structure").hash
            return ProtonationArtefact(parameters=supplied_parameters(), inputs=keyed)
        return ProtonationArtefact(
            parameters=protonation_parameters(resolved.protonation),
            inputs={"structure": inputs.require("structure").hash},
        )

    def run(
        self,
        inputs: StageInputs,
        *,
        progress: Progress | None = None,
        cancel: CancelToken | None = None,
    ) -> ProtonationArtefact:
        """Protonate every frame, or register inputs.pqr, and emit the artefact."""
        resolved = _resolved(inputs)
        key = self._key(inputs, resolved)
        ensemble = None
        if resolved.structure is not None:
            check_cancelled(cancel, "reading the aligned ensemble")
            ensemble = AlignedEnsemble.read(inputs.require("structure").payload[ENSEMBLE_PAYLOAD])
        directory = self._directory()
        settings = resolved.protonation
        if resolved.pqr is not None:
            assert resolved.pqr.path is not None
            frames, record = _supplied(
                resolved.pqr.path, ensemble, progress=progress, cancel=cancel
            )
            pka = None
            source: dict[str, Canonicalisable] = {
                "source": "inputs.pqr",
                "forcefield": None,
                "ph": None,
                "titration": None,
                "pqr_sha256": key.inputs["pqr"],
            }
        else:
            assert ensemble is not None
            frames, pka, record = self._produced(
                ensemble, settings, directory, progress=progress, cancel=cancel
            )
            source = {
                "source": "pdb2pqr",
                "forcefield": settings.forcefield,
                "ph": settings.ph,
                "titration": settings.titration,
                "arguments": list(pdb2pqr_arguments(settings)),
            }
        check_cancelled(cancel, "tabulating the protonation states")
        # A produced table names the versions that wrote its frames, which a
        # cached frame may not share with what is installed now (section 5.3.2).
        versions = record.pop("versions", None) or _versions()
        frames_header = ensemble.header.get("frames") if ensemble is not None else None
        header: dict[str, Canonicalisable] = {
            **source,
            "versions": versions,
            "frames": {
                "count": len(frames),
                "indices": frames_header.get("indices")
                if isinstance(frames_header, dict)
                else None,
            },
            # The map each frame was written and registered by, which the export
            # writes it back by; None where no structure: gave stage-1 keys.
            "chains": (
                dict(chain_characters(ensemble.chain.tolist())) if ensemble is not None else None
            ),
        }
        table, states = _assemble(
            frames,
            pka,
            ph=settings.ph if pka is not None else float("nan"),
            header=header,
            compare_radii=resolved.pqr is not None or settings.forcefield == "CHARMM",
        )
        path = table.write(directory / f"{PAYLOAD_NAME}.npz")
        variant = resolved.structure.spec.source.variant if resolved.structure else None
        summary: dict[str, Canonicalisable] = {
            **header,
            "variant": variant,
            **states,
            **record,
            "payload_digest": table.digest(),
        }
        for message, count in sorted(_mapping(record.get("warnings")).items()):
            logger.warning("protonation: PDB2PQR or PROPKA warned %d times: %s", count, message)
        q_net = [round(value) for value in table.q_net_e().tolist()]
        report(progress, 1.0, f"{table.frames} frames protonated, Q_net {q_net[0]} e in frame 0")
        return ProtonationArtefact(
            parameters=key.parameters,
            inputs=key.inputs,
            payload={PAYLOAD_NAME: path},
            summary=summary,
        )

    def _directory(self) -> Path:
        if self._workspace is not None:
            self._workspace.mkdir(parents=True, exist_ok=True)
            return Path(tempfile.mkdtemp(prefix="protonation-", dir=self._workspace))
        root = store_root() / WORKSPACE_DIRNAME
        root.mkdir(parents=True, exist_ok=True)
        return Path(tempfile.mkdtemp(prefix="protonation-", dir=root))

    def _produced(
        self,
        ensemble: AlignedEnsemble,
        settings: ResolvedProtonation,
        directory: Path,
        *,
        progress: Progress | None,
        cancel: CancelToken | None,
    ) -> tuple[list[PQRFrame], list[list[dict[str, Canonicalisable]]], dict[str, Canonicalisable]]:
        import numpy as np

        _require_pdb2pqr()
        reference = _reference(ensemble)
        heavy = np.flatnonzero(
            (np.char.upper(np.char.strip(ensemble.element.astype(str))) != "H")
            & ~np.isin(ensemble.resname.astype(str), sorted(WATER_RESIDUES))
        )
        chains = chain_characters(ensemble.chain.tolist())
        keys = {letter: chain for chain, letter in chains.items()}
        parameters = protonation_parameters(settings)
        produced_by: list[Canonicalisable] = []
        frames: list[PQRFrame] = []
        pka: list[list[dict[str, Canonicalisable]]] = []
        registrations: list[_Registration] = []
        warnings: Counter[str] = Counter()
        cached = 0
        for index in range(ensemble.frames):
            check_cancelled(cancel, f"protonating frame {index}")
            report(progress, index / ensemble.frames, f"frame {index + 1} of {ensemble.frames}")
            pdb = frame_pdb(ensemble, index, heavy, chains)
            frame_key = Artefact(
                schema=PROTONATION_FRAME_SCHEMA,
                parameters=parameters,
                inputs={"pdb": hashlib.sha256(pdb).hexdigest()},
            )
            stored = (
                self._store.get(frame_key.schema, frame_key.hash)
                if self._store is not None
                else None
            )
            if stored is None:
                try:
                    stored = self._protonate(frame_key, pdb, settings, directory / f"frame-{index}")
                except (RuntimeError, ValueError) as error:
                    # PDB2PQR raises a bare RuntimeError, with no message, for
                    # what it gives up on (main_driver, 3.7.1): name the frame
                    # and its cause.
                    cause = error.__cause__ or error
                    raise ProtonationError(
                        f"frame {index}: PDB2PQR gave up on the frame it was given: "
                        f"{type(cause).__name__}: {cause}"
                    ) from error
            else:
                cached += 1
            produced_by.append(stored.summary.get("versions"))
            text = Path(stored.payload["pqr"]).read_text(encoding="utf-8")
            reported = json.loads(Path(stored.payload["record"]).read_text(encoding="utf-8"))
            missing = list(reported.get("missing", []))
            if missing:
                raise ProtonationError(
                    f"frame {index}: PDB2PQR could not parameterise {len(missing)} atoms and "
                    f"left them out of the PQR; the first is {missing[0]} (PHY-16 step 3)"
                )
            try:
                (frame,) = parse_pqr(text, source=f"PDB2PQR's PQR of frame {index}")
            except (PQRError, ValueError) as error:
                raise ProtonationError(
                    f"frame {index}: the PQR PDB2PQR wrote does not read as one frame with a "
                    f"charge and a radius on every atom: {error}"
                ) from error
            frame = _rechain(frame, keys)
            mismatch = _residue_mismatch(frame, reference)
            target = np.asarray(ensemble.positions_nm[index], dtype=np.float64) * 10.0
            registration = _register(frame, target, reference, may_move=False)
            failure = mismatch or registration.failure
            if failure is not None:
                raise ProtonationError(
                    f"frame {index}: the PQR PDB2PQR wrote does not hold the frame it was given: "
                    f"{failure}"
                )
            registrations.append(registration)
            frames.append(frame)
            pka.append(
                [
                    {**row, "chain": keys.get(str(row["chain"]), str(row["chain"]))}
                    for row in reported.get("pka", [])
                ]
            )
            warnings.update({str(k): int(v) for k, v in reported.get("warnings", {}).items()})
        try:
            check_same_residues(frames, source="the protonated ensemble")
        except PQRError as error:
            raise ProtonationError(str(error)) from error
        return (
            frames,
            pka,
            {
                "cached_frames": cached,
                "versions": _frame_versions(produced_by),
                "registration": _registration_record(registrations, reference, moved=[]),
                "warnings": dict(sorted(warnings.items())),
            },
        )

    def _protonate(
        self, key: Artefact, pdb: bytes, settings: ResolvedProtonation, directory: Path
    ) -> Artefact:
        directory.mkdir(parents=True, exist_ok=True)
        source = directory / "frame.pdb"
        source.write_bytes(pdb)
        pqr = directory / "frame.pqr"
        reported = run_pdb2pqr(source, pqr, settings)
        record = directory / "record.json"
        record.write_text(json.dumps(reported, sort_keys=True), encoding="utf-8")
        produced = Artefact(
            schema=key.schema,
            parameters=key.parameters,
            inputs=key.inputs,
            payload={"pqr": pqr, "record": record},
            summary={"versions": _versions()},
        )
        return self._store.put(produced) if self._store is not None else produced


def _mapping(value: Canonicalisable) -> Mapping[str, int]:
    if isinstance(value, Mapping):
        return {str(key): int(str(count)) for key, count in value.items()}
    return {}


def _supplied(
    path: Path,
    ensemble: AlignedEnsemble | None,
    *,
    progress: Progress | None,
    cancel: CancelToken | None,
) -> tuple[list[PQRFrame], dict[str, Canonicalisable]]:
    import numpy as np

    report(progress, 0.0, f"reading {path.name}")
    read = list(read_pqr(path))
    if ensemble is None:
        return read, {
            "registration": {"status": "not run: no structure: section to register to"},
            "warnings": {},
        }
    if len(read) != ensemble.frames:
        raise PQRError(
            f"{path} holds {len(read)} frames and the ensemble {ensemble.frames}; beside "
            "structure: the PQR holds exactly the ensemble's frames, in order (section 5.3.1 "
            "NOTE on inputs:)"
        )
    reference = _reference(ensemble)
    keys = {letter: chain for chain, letter in chain_characters(ensemble.chain.tolist()).items()}
    frames: list[PQRFrame] = []
    moved: list[int] = []
    registrations: list[_Registration] = []
    for index, frame in enumerate(read):
        check_cancelled(cancel, f"registering frame {index}")
        report(progress, index / len(read), f"registering frame {index + 1} of {len(read)}")
        frame = _rechain(frame, keys)
        mismatch = _residue_mismatch(frame, reference)
        if mismatch is not None:
            raise PQRError(
                f"{path} frame {index} does not hold the residues of stage 1's frame {index}: "
                f"{mismatch} (section 5.3.1 NOTE on inputs:)"
            )
        target = np.asarray(ensemble.positions_nm[index], dtype=np.float64) * 10.0
        registration = _register(frame, target, reference, may_move=True)
        if registration.failure is not None:
            raise PQRError(
                f"{path} frame {index} does not register to stage 1's frame {index}: "
                f"{registration.failure} (section 5.3.1 NOTE on inputs:)"
            )
        if registration.moved:
            moved.append(index)
        registrations.append(registration)
        frames.append(dataclasses.replace(frame, positions_A=registration.positions_A))
    return frames, {
        "registration": _registration_record(registrations, reference, moved=moved),
        "warnings": {},
    }


def _frame_versions(produced_by: Sequence[Canonicalisable]) -> Canonicalisable:
    distinct = {json.dumps(found, sort_keys=True) for found in produced_by}
    return produced_by[0] if len(distinct) == 1 else list(produced_by)


def _registration_record(
    registrations: Sequence[_Registration], reference: _Reference, *, moved: list[int]
) -> dict[str, Canonicalisable]:
    return {
        "moved_frames": moved,
        "worst_residual_A": max([0.0, *(found.worst_A for found in registrations)]),
        "flippable_atoms": len(reference.flippable),
        "worst_flipped_A": max([0.0, *(found.flipped_A for found in registrations)]),
        "flipped_atoms": max([0, *(found.flipped for found in registrations)]),
        "added_heavy_atoms": max([0, *(found.added_heavy for found in registrations)]),
        "tolerance_A": REGISTRATION_TOLERANCE_A,
    }
