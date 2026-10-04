"""Stage 7, first half: protonation, partial charges and radii per frame (FR-12, WP27).

The ``protonation`` stage takes stage 1's aligned ensemble and runs PDB2PQR, with
PROPKA, on every frame of it (section 8.2.4 D4), or reads a supplied
``inputs.pqr``; either way it emits a per-frame atom table in stage 1's frame,
with each atom's charge and radius, ``Q_net`` per frame and the protonation
state of every titratable residue. PHY-16 step 3 and its NOTE are the contract;
the decisions are the WP27 plan's.

**What PDB2PQR is given is ours** (D5). Each frame is written by
:func:`frame_pdb` in PDB fixed columns, to 0.001 Å, with its hydrogens dropped,
every protonation-variant residue name written as its titratable parent, and
each chain key as one character. PDB2PQR 3.7.1 treats ``HSD`` and ``HSE`` as
fixed residues and refuses ``HSE`` with its hydrogens present, so a CHARMM-named
frame passed through verbatim would pin every histidine (``.knowledge/07``
section 3). The bytes are ours, not MDAnalysis's, because their digest keys the
frame (D10).

**Each frame is cached on its own** under ``nanopnp/protonation-frame/v1``, keyed
on the digest of that PDB and the protonation parameters, so a changed frame
selection re-protonates only the frames it adds. The PQR PDB2PQR wrote is read
back through :mod:`nanopnp.charge.pqr`, the reader ``inputs.pqr`` goes through,
so the two routes produce the same object (D6).

**A state PDB2PQR could not apply is recorded, never parsed from its log** (D8,
the PHY-16 step-3 NOTE). Each residue's applied charge is compared with the sum
of PROPKA's group states at the pH; where the two differ the state is
*unapplied*. CHARMM cannot hold ``CYS⁻``, ``LYS⁰``, ``TYR⁻``, ``ARG⁰`` or a
neutral terminus, and PDB2PQR never applies a terminal pKa at all.

**Gates abort, naming the frame** (D9, QR-12): an atom PDB2PQR could not
parameterise, a charged atom without a positive radius (PHY-16 step 4's width
``w_i = 0.5 R_i`` would vanish), and a ``Q_net`` that is not an integer to 10⁻⁶ e.
A supplied PQR that does not match its ensemble is a case refusal instead
(:class:`~nanopnp.charge.pqr.PQRError`).

``pdb2pqr`` is imported only inside the functions that drive it (D4), so
``inputs.pqr`` runs without the ``structure`` extra and listing the registry
imports neither PDB2PQR nor PROPKA (VER-25).
"""

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
from nanopnp.io.case import ResolvedProtonation, UnsupportedCaseSection, resolve
from nanopnp.structure.ensemble import PAYLOAD_NAME as ENSEMBLE_PAYLOAD
from nanopnp.structure.ensemble import AlignedEnsemble

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

    from nanopnp.io.artefact import StageInputs
    from nanopnp.io.case import ResolvedCase
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
spacing, and a hundredth of the shortest heavy-atom bond (WP27 *Design* §3).
"""

COORDINATE_DECIMALS = 3
"""The payload's coordinates lie on the 0.001 Å lattice a PQR prints, so an export reads back."""

Q_NET_TOLERANCE_E = 1e-6
"""How far ``Q_net`` may lie from an integer, in e (PHY-16 step 3, D9)."""

MINIMUM_CALPHA = 3
"""C-alpha pairs a registration needs: three points fix a rigid motion."""

RADIUS_SET = "pdb2pqr_charmm"
"""The stage-2 radius set the PQR's radii are compared with under CHARMM (D14)."""

ACID_GROUPS: frozenset[str] = frozenset({"COO", "C-", "CYS", "TYR"})
"""PROPKA group types that carry -1 at a pH at or above their pKa (*Design* §2)."""

BASE_GROUPS: frozenset[str] = frozenset({"HIS", "LYS", "ARG", "N+"})
"""PROPKA group types that carry +1 at a pH below their pKa (*Design* §2)."""

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

_LOGGERS: tuple[str, ...] = ("pdb2pqr", "propka")
"""The library loggers raised to WARNING during a call (D7); the versioned one is added."""

_EXTRA = "structure"
"""The extra that carries PDB2PQR and PROPKA (``pyproject.toml``)."""


class ProtonationError(RuntimeError):
    """A protonation gate failed, naming the frame and the residue or atom (D9, QR-12).

    Classified with the gates (IF-02 class 4): the case is well formed and the
    structure it names, or the PQR it supplies, gives an atom table the charge
    kernel cannot use.
    """


# -- the settings -----------------------------------------------------------


def pdb2pqr_arguments(settings: ResolvedProtonation) -> tuple[str, ...]:
    """Return the flags PDB2PQR is run with, without the two paths (PHY-16 step 3, D6).

    ``titration: none`` passes neither ``--with-ph`` nor
    ``--titration-state-method``, so every residue keeps the force field's
    standard state and the pH reaches nothing.
    """
    flags = [f"--ff={settings.forcefield}", f"--ffout={settings.forcefield}"]
    if settings.titration != "none":
        flags += [f"--with-ph={settings.ph!r}", f"--titration-state-method={settings.titration}"]
    return (*flags, *FIXED_FLAGS)


def protonation_parameters(settings: ResolvedProtonation) -> dict[str, Canonicalisable]:
    """Return the produced artefact's key parameters, which also key each frame (D10)."""
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
    """Return a supplied artefact's key parameters: the constants that move a number or verdict."""
    return {
        "source": "inputs.pqr",
        "normalisation": dict(sorted(PARENT_RESIDUE.items())),
        "coordinate_decimals": COORDINATE_DECIMALS,
        "gates": _gate_parameters(),
    }


def _gate_parameters() -> dict[str, Canonicalisable]:
    """Return the tolerances the gates are evaluated at, which key the verdict."""
    return {
        "registration_tolerance_A": REGISTRATION_TOLERANCE_A,
        "q_net_tolerance_e": Q_NET_TOLERANCE_E,
        "minimum_calpha": MINIMUM_CALPHA,
    }


def _versions() -> dict[str, Canonicalisable]:
    """Return the PDB2PQR and PROPKA versions, recorded beside the key (section 5.3.2)."""
    found: dict[str, Canonicalisable] = {}
    for distribution in ("pdb2pqr", "propka"):
        try:
            found[distribution] = metadata.version(distribution)
        except metadata.PackageNotFoundError:
            found[distribution] = None
    return found


# -- the payload ------------------------------------------------------------


def _residue_label(name: str, resid: int, icode: str, chain: str) -> str:
    """Return a residue as diagnostics name it."""
    return f"{name} {resid}{icode} of chain {chain!r}"


@dataclass(frozen=True)
class ProtonationTable:
    """The protonation artefact's payload: the atoms of every frame and their residues' states.

    Frames differ in their hydrogens, so the atom arrays are the frames'
    concatenated, and frame ``f`` is ``frame_offsets[f]:frame_offsets[f + 1]``
    (D11). The residues are the same in every frame (section 5.3.1 NOTE on
    ``inputs:``) and are tabulated once.

    Parameters
    ----------
    frame_offsets
        ``(frames + 1,)`` int64.
    positions_nm
        ``(atoms, 3)`` float64, in nm in stage 1's frame, on the 0.001 Å lattice.
    charge_e, radius_nm
        float64, one entry per atom.
    name, resname, chain, icode, resid
        The atom table; ``chain`` holds stage 1's chain keys.
    residue_chain, residue_resid, residue_icode, residue_name
        One entry per residue, in order of first appearance.
    residue_charge_e
        ``(frames, residues)`` float64: each residue's applied charge.
    tautomer
        ``(frames, residues)`` strings: ``HSD``, ``HSE`` or ``HSP`` for a
        histidine, by its ``HD1`` and ``HE2``; empty otherwise.
    expected_charge_e
        ``(frames, residues)`` float64: the sum of PROPKA's group states at the pH,
        NaN where no group of *Design* §2 was computed.
    unapplied
        ``(frames, residues)`` bool: the applied and expected charges differ.
    group_residue, group_type, group_label, group_pka
        PROPKA's groups: the residue each belongs to, its type, its label, and
        its pKa per frame, ``(frames, groups)`` float64 with NaN where a frame
        lacks it. The label tells apart the two ``COO`` groups of a C-terminal
        ``ASP`` or ``GLU`` (``ASP  21 A`` and ``C-   21 A``).
    header
        Settings, source, versions and the chain map (``chains``: each stage-1
        chain key and the character a PQR writes it as), as plain data.
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
        """Number of frames."""
        return len(self.frame_offsets) - 1

    def frame_slice(self, frame: int) -> slice:
        """Return the atom range of one frame."""
        return slice(int(self.frame_offsets[frame]), int(self.frame_offsets[frame + 1]))

    def q_net_e(self) -> np.ndarray:
        """Return ``Q_net = Σ q_i`` per frame, in e."""
        import numpy as np

        return np.array(
            [
                math.fsum(self.charge_e[self.frame_slice(frame)].tolist())
                for frame in range(self.frames)
            ]
        )

    def digest(self) -> str:
        """Return a content hash over every array and the header (VER-23)."""
        return content_hash(
            f"{PROTONATION_SCHEMA}/payload",
            {**{key: getattr(self, key) for key in self.ARRAYS}, "header": dict(self.header)},
        )

    def write(self, path: Path) -> Path:
        """Write the table to ``path`` as ``.npz``, header included; return the path."""
        import numpy as np

        arrays: dict[str, Any] = {key: np.asarray(getattr(self, key)) for key in self.ARRAYS}
        arrays["header"] = np.asarray(json.dumps(dict(self.header), sort_keys=True))
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as handle:
            np.savez(handle, **arrays)
        return path

    @classmethod
    def read(cls, path: Path) -> ProtonationTable:
        """Read a table written by :meth:`write`.

        Raises
        ------
        PQRError
            If an array is missing.
        """
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
        """Return the frames in ångströms, each value the one that reads back to this table.

        Raises
        ------
        ValueError
            If a coordinate is not on the 0.001 Å lattice, which no table this
            module wrote can hold.
        """
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
    """Return values in Å that convert back to ``values_nm`` exactly under ``x 0.1``.

    The payload holds ``A x 0.1`` for each value ``A`` read from a PQR, and an
    export must print an ``A`` that reads back to the same bits (the section 3.1
    IF-02 export NOTE). Rounding ``values_nm x 10`` to the printed decimals
    recovers it whenever it was printed to those decimals; otherwise the
    neighbouring doubles are searched, which always holds the original.
    """
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
    """Yield the doubles within ``steps`` ulps of a start, nearest first."""
    import numpy as np

    for _ in range(steps):
        up = np.nextafter(up, np.inf)
        down = np.nextafter(down, -np.inf)
        yield up
        yield down


# -- PDB2PQR as a driver ----------------------------------------------------


def frame_pdb(
    ensemble: AlignedEnsemble,
    frame: int,
    heavy: np.ndarray,
    chains: Mapping[str, str],
) -> bytes:
    """Return the PDB PDB2PQR is given for one frame (D5, the PHY-16 step-3 NOTE).

    PDB fixed columns, coordinates in Å to 0.001, the heavy atoms alone, each
    protonation-variant residue name written as its parent, and each chain key
    as its single character.

    Raises
    ------
    ProtonationError
        For a residue name or number, or a coordinate, the PDB columns cannot hold.
    """
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
    """Raise PDB2PQR's and PROPKA's loggers to WARNING and collect what they warn (D7).

    PROPKA logs its full report at INFO, about 400 kB for the dodecamer. The
    warnings are collected rather than dropped, and the caller re-logs each
    distinct one once and records its count: surfaced, never swallowed.
    """
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
    """Refuse a produced run without PDB2PQR, naming the extra, before the first frame (D4)."""
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
    """Answer ``self.__annotations__`` from the class, and refuse every other missing name."""
    if name == "__annotations__":
        return type(self).__annotations__
    raise AttributeError(f"{type(self).__name__!r} object has no attribute {name!r}")


def restore_propka_annotations() -> bool:
    """Let PROPKA 3.5.1 read its parameter file on Python 3.14; return whether it had to.

    ``propka.parameters.Parameters.parse_line`` dispatches on
    ``self.__annotations__``. From Python 3.14 (PEP 649 and 749) annotations are
    evaluated lazily and are an attribute of the class only, so on an instance
    the lookup raises ``AttributeError`` and every PROPKA run fails before its
    first residue. QR-09 holds the package to 3.11-3.14, and no PROPKA release
    fixes it (3.5.1 is the latest), so the instance is given a
    fallback that answers that one name from its class and nothing else.

    Detected, not version-checked: where an instance already has
    ``__annotations__``, as on 3.11-3.13 and on any PROPKA that stops reading
    it, nothing is installed. The dispatch compares the annotation objects by
    identity, and the class's evaluated annotations are those objects, so the
    run is unchanged: on the fragment ``GLU 18``-``LEU 26`` at pH 2, 3.14 with
    this fallback and 3.12 without it give byte-identical PQRs and equal pKas
    (``.knowledge/07`` section 3).
    """
    from propka.parameters import Parameters

    if hasattr(Parameters(), "__annotations__"):
        return False
    Parameters.__getattr__ = _instance_annotations  # type: ignore[attr-defined]
    return True


def run_pdb2pqr(pdb: Path, pqr: Path, settings: ResolvedProtonation) -> dict[str, Canonicalisable]:
    """Run PDB2PQR in-process on one PDB file and return what it reported (D6, D7).

    Parameters
    ----------
    pdb
        The input file. It must exist: PDB2PQR fetches a path that is not a file
        from rcsb.org (``.knowledge/07`` section 3), so it is resolved and checked.
    pqr
        Where PDB2PQR writes the PQR.
    settings
        The case's protonation settings.

    Returns
    -------
    dict
        ``pka``: PROPKA's groups, as plain rows; ``missing``: the atoms PDB2PQR
        could not parameterise; ``warnings``: each distinct warning the libraries
        logged, with its count.
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
    """Return one PROPKA group as plain data, with the insertion code stripped."""
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
    """Return an atom PDB2PQR could not parameterise as a diagnostic names it."""
    residue = getattr(atom, "residue", None)
    return (
        f"{getattr(atom, 'name', '?')} of {getattr(residue, 'name', '?')} "
        f"{getattr(atom, 'res_seq', '?')} of chain {getattr(atom, 'chain_id', '?')!r}"
    )


# -- residues, states and registration ----------------------------------------


ResidueKey = tuple[str, int, str]
"""A residue's identity: chain key, number and insertion code."""


def _residue_keys(frame: PQRFrame) -> list[ResidueKey]:
    """Return each atom's residue key."""
    return list(zip(frame.chain.tolist(), frame.resid.tolist(), frame.icode.tolist(), strict=True))


def _rechain(frame: PQRFrame, keys: Mapping[str, str]) -> PQRFrame:
    """Return ``frame`` with each single-character chain replaced by its stage-1 key.

    A character the map does not hold is kept, so the residue check that follows
    names the residue it cannot place rather than this function guessing.
    """
    import numpy as np

    chain = np.array([keys.get(value, value) for value in frame.chain.tolist()], dtype=str)
    return dataclasses.replace(frame, chain=chain)


def _tautomer(atoms: set[str]) -> str:
    """Return a histidine's CHARMM name from the ring hydrogens it carries (D8)."""
    delta, epsilon = "HD1" in atoms, "HE2" in atoms
    if delta and epsilon:
        return "HSP"
    if delta:
        return "HSD"
    if epsilon:
        return "HSE"
    return ""


def _group_state(group_type: str, pka: float, ph: float) -> float | None:
    """Return the charge PROPKA's pKa prefers for one group at ``ph`` (*Design* §2).

    The comparisons ``Biomolecule.apply_pka_values`` makes; ``None`` for a group
    type outside the eight, which is recorded and not compared.
    """
    if group_type in ACID_GROUPS:
        return -1.0 if ph >= pka else 0.0
    if group_type in BASE_GROUPS:
        return 1.0 if ph < pka else 0.0
    return None


@dataclass(frozen=True)
class _Reference:
    """Stage 1's residues and heavy atoms, which a PQR frame is checked and registered against."""

    residues: dict[ResidueKey, str]
    """Every residue but water, in order: its key and its parent name."""
    heavy: np.ndarray
    """Indices of those residues' heavy atoms in the ensemble's atom table."""
    heavy_residue: list[ResidueKey]
    """Each heavy atom's residue."""
    heavy_name: list[str]
    """Each heavy atom's name."""
    flippable: np.ndarray
    """Indices of the heavy atoms of :data:`FLIPPABLE`, which are not held to the tolerance."""
    calpha: dict[ResidueKey, int]
    """Each residue's one C-alpha, as an ensemble atom index."""
    flippable_elements: Counter[tuple[ResidueKey, str]]
    """Heavy atoms by residue and element, in each residue holding :data:`FLIPPABLE` atoms."""

    @property
    def flippable_residues(self) -> set[ResidueKey]:
        """The residues holding :data:`FLIPPABLE` atoms."""
        return {key for key, _ in self.flippable_elements}


def _reference(ensemble: AlignedEnsemble) -> _Reference:
    """Tabulate the ensemble's residues and heavy atoms, leaving out ``--drop-water``'s waters."""
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
    """Return a heavy atom's element as its name's first letter (``1SG`` is S).

    Used only on the residues of :data:`FLIPPABLE`, whose atoms are C, N and O
    and whose names begin with their element.
    """
    return name.lstrip("0123456789")[:1].upper()


def _residue_mismatch(frame: PQRFrame, reference: _Reference) -> str | None:
    """Return why a frame does not hold the ensemble's residues, or ``None`` if it does.

    Compared by key and parent name, both ways; waters are on neither side.
    """
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
    """Return ``(R, t)`` minimising ``Σ |R p + t - q|²`` over the paired rows."""
    import numpy as np

    centre_moving, centre_fixed = moving.mean(axis=0), fixed.mean(axis=0)
    covariance = (moving - centre_moving).T @ (fixed - centre_fixed)
    u, _, vt = np.linalg.svd(covariance)
    sign = 1.0 if np.linalg.det(vt.T @ u.T) >= 0.0 else -1.0
    rotation = vt.T @ np.diag([1.0, 1.0, sign]) @ u.T
    return rotation, centre_fixed - rotation @ centre_moving


@dataclass(frozen=True)
class _Registration:
    """What registering one frame found."""

    positions_A: np.ndarray
    moved: bool
    worst_A: float
    """The largest distance from a compared heavy atom to its match."""
    flipped_A: float
    """The largest distance from a :data:`FLIPPABLE` atom to the nearest heavy atom."""
    flipped: int
    """How many :data:`FLIPPABLE` atoms lie farther than the tolerance from every heavy atom."""
    added_heavy: int
    failure: str | None


def _register(
    frame: PQRFrame, target_A: np.ndarray, reference: _Reference, *, may_move: bool
) -> _Registration:
    """Register one PQR frame to its stage-1 frame (section 5.3.1 NOTE on ``inputs:``).

    Every heavy atom of the ensemble but the :data:`FLIPPABLE` ones must lie
    within 0.01 Å of a distinct heavy atom of the same residue of the PQR: where
    the PQR stands, or, if it does not and ``may_move``, after superposing the
    PQR's C-alpha atoms on the ensemble's, residue for residue. A frame that
    already meets the criterion is not moved. Matching is by position, never by
    name: PDB2PQR renames atoms (``ILE CD1`` to ``CD``, the C-terminal ``O`` to
    ``OT1``), and the atoms its hydrogen-bond optimisation flips land 0.13-0.40 Å
    from any they were given, which is why they are left out and their worst
    distance recorded. The shortest heavy-atom bond is 1.23 Å, so at most one
    heavy atom lies within the tolerance of any point, and the nearest neighbour
    over the whole frame is the only candidate (*Design* §3).
    """
    import numpy as np
    from scipy.spatial import cKDTree

    keys = _residue_keys(frame)
    heavy = np.array([not is_hydrogen(name) for name in frame.name.tolist()], dtype=bool)
    candidates = np.flatnonzero(heavy)
    fixed = target_A[reference.heavy]
    added = len(candidates) - len(fixed) - len(reference.flippable)

    def flipped(positions: np.ndarray) -> tuple[float, int]:
        """Return the worst flippable atom's distance to a PQR heavy atom, and how many moved."""
        if not len(reference.flippable) or not len(candidates):
            return 0.0, 0
        distance, _ = cKDTree(positions[candidates]).query(target_A[reference.flippable], k=1)
        return float(distance.max()), int((distance > REGISTRATION_TOLERANCE_A).sum())

    def check(positions: np.ndarray) -> tuple[float, str | None]:
        """Return the worst residual over the matched atoms, and the first failure."""
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


# -- gates and assembly -------------------------------------------------------


def _gate(frame: PQRFrame, index: int) -> float:
    """Apply D9's atom and ``Q_net`` gates to one frame; return its ``Q_net`` in e.

    Raises
    ------
    ProtonationError
        For a charged atom whose radius is not positive, which PHY-16 step 4's
        width ``w_i = 0.5 R_i`` cannot smear, or a ``Q_net`` further than 10⁻⁶ e
        from an integer, naming the frame and the atom.
    """
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
    if abs(q_net - round(q_net)) > Q_NET_TOLERANCE_E:
        raise ProtonationError(
            f"frame {index}: Q_net = {q_net!r} e is {abs(q_net - round(q_net)):.3g} e from an "
            f"integer, more than {Q_NET_TOLERANCE_E} e (PHY-16 step 3); an atom carries a charge "
            "its force field does not give it"
        )
    return q_net


def _chain_differences(
    residues: Sequence[tuple[str, int, str, str]], charges: np.ndarray
) -> list[dict[str, Canonicalisable]]:
    """Return each residue whose charge differs between chains of identical sequence (D8).

    The states of a homo-oligomer's chains are not symmetrised (the PHY-16
    step-3 NOTE), so a difference is recorded per residue with the frames it
    occurs in and the chains' charges in the first of them.
    """
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
    """Return each residue with an unapplied state, with the frames and the charges (D8)."""
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
    """Return the table's radius for an atom, by its residue's name and then its parent's.

    A patched residue's backbone is the parent's: ``ASPP`` lists only the atoms
    the patch changes.
    """
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
    """Compare every atom's radius with the stage-2 CHARMM table (D14).

    The table is transcribed from the same ``CHARMM.DAT`` PDB2PQR reads, so a
    disagreement is a defect to find, not to average: it is recorded, counted
    and its worst instance named. A histidine is looked up by its tautomer and a
    terminal atom through the table's patches. Atoms the table does not resolve
    are counted separately.
    """
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
    """Tabulate gated frames and their residue states; return the table and its record.

    ``frames`` carry stage 1's chain keys and Å coordinates already registered;
    they are put on the 0.001 Å lattice here, so every table this stage writes
    exports and reads back exactly. ``compare_radii`` is false for a frame
    another force field than CHARMM produced, whose radii the stage-2 CHARMM
    table does not describe (D14).
    """
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
    """Write a stored protonation table as a PQR file, one ``MODEL`` per frame (IF-02 export NOTE).

    In ångströms and stage 1's frame. Read back through ``inputs.pqr`` beside the
    same ``structure:``, it gives this table exactly: the coordinates lie on the
    printed lattice, every charge and radius is printed so that it reads back to
    the same double, and each chain key goes to the character the header's chain
    map gives it, which is the map the registration reads it back by. A table
    with no map, read from a PQR without ``structure:``, takes
    :func:`~nanopnp.charge.pqr.chain_characters` of its own chains.
    """
    table = ProtonationTable.read(payload)
    recorded = table.header.get("chains")
    chains = (
        {str(key): str(letter) for key, letter in recorded.items()}
        if isinstance(recorded, Mapping)
        else chain_characters(table.chain.tolist())
    )
    return write_pqr(path, table.pqr_frames(), chains=chains)


# -- the stage ----------------------------------------------------------------


def _resolved(inputs: StageInputs) -> ResolvedCase:
    """Return the resolved case, refusing one the stage has nothing to read from (D3)."""
    resolved = resolve(inputs.case)
    if not resolved.protonates:
        raise UnsupportedCaseSection(
            f"case {inputs.case.name!r} has nothing for the protonation stage to read: it "
            + (
                "supplies inputs.charge, which replaces what stage 7 makes of the protonation"
                if resolved.charge is not None
                else "carries no structure: section and supplies no inputs.pqr"
            )
        )
    return resolved


class ProtonationStage:
    """Stage 7, first half: the aligned ensemble, or ``inputs.pqr``, to a per-frame atom table."""

    name = "protonation"

    def __init__(self, *, workspace: Path | None = None, store: Store | None = None) -> None:
        """Build the stage.

        Parameters
        ----------
        workspace
            Directory the frames' files and the payload are written to before the
            store copies them in. Defaults to a fresh directory under the store
            root.
        store
            Where each produced frame is cached under its own key (D10). Without
            one, every frame is protonated.
        """
        self._workspace = Path(workspace) if workspace is not None else None
        self._store = store

    def describe(self) -> StageDescription:
        """Return the registry's description of this stage (FR-27)."""
        return describe(self.name)

    def key(self, inputs: StageInputs) -> ProtonationArtefact:
        """Return the artefact key (D10, the section 5.3.2 stage-7 row)."""
        return self._key(inputs, _resolved(inputs))

    @staticmethod
    def _key(inputs: StageInputs, resolved: ResolvedCase) -> ProtonationArtefact:
        """Return the artefact key of an already resolved case."""
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
        """Protonate every frame, or read and register ``inputs.pqr``, and emit the artefact.

        Raises
        ------
        nanopnp.core.stages.MissingExtraError
            Before the first frame, for a ``structure:`` case without PDB2PQR.
        nanopnp.charge.pqr.PQRError
            For a supplied PQR that is malformed or does not match its ensemble.
        ProtonationError
            For a D9 gate, naming the frame.
        Cancelled
            If ``cancel`` turns true between frames. No artefact is written.
        """
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
        """Return the directory this run writes into, made fresh under the store root if unnamed."""
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
        """Protonate each frame through PDB2PQR, or read it from the frame cache (D5-D7, D10)."""
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
                    # and its cause (QR-12).
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
        """Run PDB2PQR on one frame's PDB and store the frame under its own key (D10)."""
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
    """Return a summary entry as a mapping of counts, or an empty one."""
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
    """Read ``inputs.pqr`` and register each frame to its stage-1 frame (D12, *Design* §3).

    Raises
    ------
    PQRError
        For a frame count that differs from the ensemble's, a residue the two do
        not share, or a frame whose heavy atoms do not register, naming the frame.
    """
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
    """Return the versions that produced the frames, recorded beside the key (section 5.3.2).

    The frame cache is keyed without them, so a frame an earlier PDB2PQR or
    PROPKA wrote is reused: one mapping where every frame shares it, otherwise
    each frame's, in frame order.
    """
    distinct = {json.dumps(found, sort_keys=True) for found in produced_by}
    return produced_by[0] if len(distinct) == 1 else list(produced_by)


def _registration_record(
    registrations: Sequence[_Registration], reference: _Reference, *, moved: list[int]
) -> dict[str, Canonicalisable]:
    """Return the registration record both routes write: each figure's worst over the frames."""
    return {
        "moved_frames": moved,
        "worst_residual_A": max([0.0, *(found.worst_A for found in registrations)]),
        "flippable_atoms": len(reference.flippable),
        "worst_flipped_A": max([0.0, *(found.flipped_A for found in registrations)]),
        "flipped_atoms": max([0, *(found.flipped for found in registrations)]),
        "added_heavy_atoms": max([0, *(found.added_heavy for found in registrations)]),
        "tolerance_A": REGISTRATION_TOLERANCE_A,
    }
