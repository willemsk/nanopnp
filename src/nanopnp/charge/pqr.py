"""The PQR file: one reader and one writer for both of stage 7's protonation routes (WP27).

A PQR is a PDB whose occupancy and B-factor columns carry each atom's partial
charge in e and its radius in Å. Stage 7's ``protonation`` half reads one in two
places, and reads it here both times (WP27 D6): the file PDB2PQR writes for each
frame it protonates, and a file supplied through ``inputs.pqr`` (section 5.3.1
NOTE on ``inputs:``). The produced and the supplied artefact are then the same
object, read by the same code.

**The layout is PDB2PQR's, read two ways.** PDB2PQR writes PDB fixed columns
through the coordinates and then the charge and the radius, so a coordinate at or
below -100 Å runs into its neighbour (``-37.705-115.041``) and a whitespace
split cannot read the line (``.knowledge/07`` section 3). Other tools write
whitespace-separated fields that the columns do not hold. Each ATOM and HETATM
line is therefore read by the columns, and as whitespace-separated fields; a line
only one reading accepts is taken from that one, and a line both accept with
different values is refused naming its line number, because one of the two
readings is a plausible wrong number and nothing here can say which (QR-12).

**A residue is its chain, number and insertion code**, and its name is the one its
atoms carry other than the patch names ``TER`` and ``DISU``: ``--ffout=CHARMM``
writes the terminal-patch atoms under the residue name ``TER`` (``N TER A 8``) and
a disulfide-bonded cysteine's ``CB`` and ``SG`` as ``1CB`` and ``1SG`` under
``DISU`` (``1CBDISU A 285``), and a residue patched to a
protonation variant with its backbone under the parent and its side chain under
the variant (``ASP`` and ``ASPP``), whose name is then the variant. The protonation-variant
names of the PHY-16 step-3 NOTE are read as their parent wherever two residue
names are *compared*, and kept as written in the atom table.

**Frames are ``MODEL`` records.** A file without them is one frame. Every frame
SHALL hold the same residues (section 5.3.1 NOTE on ``inputs:``); the atoms may
differ, because the hydrogens a frame carries depend on its protonation states.

Nothing here imports NumPy at module scope (CLAUDE.md), and nothing imports
PDB2PQR at all: reading a supplied PQR needs no extra.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.structure.ensemble import CHAIN_CHARACTERS

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

__all__ = [
    "PARENT_RESIDUE",
    "PATCH_RESIDUES",
    "PQRError",
    "PQRFrame",
    "chain_characters",
    "check_same_residues",
    "format_pqr",
    "is_hydrogen",
    "parent_residue",
    "parse_pqr",
    "read_pqr",
    "write_pqr",
]

PATCH_RESIDUES: frozenset[str] = frozenset({"TER", "DISU"})
"""The residue names ``--ffout=CHARMM`` gives patch atoms, which name no residue.

``TER`` for a terminal patch (``.knowledge/07`` section 3) and ``DISU`` for the
``CB`` and ``SG`` of a disulfide-bonded cysteine, written ``1CB`` and ``1SG``
(``CHARMM.names`` of PDB2PQR 3.7.1): without ``DISU``
here every cysteine in a disulfide carries two names and is refused.
"""

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

_RECORDS = ("ATOM", "HETATM")
"""The record types that carry an atom."""

MAX_COORDINATE_A = 9999.999
"""The largest coordinate the eight-character ``%8.3f`` column holds."""

MIN_COORDINATE_A = -999.999
"""The smallest: one character goes to the sign."""


class PQRError(ValueError):
    """A PQR file this release cannot read, or one that does not match its ensemble.

    Raised naming the line, the frame or the residue (QR-12). A case refusal, not
    a gate (IF-02 class 3, WP27 D9): the case names a file that is malformed or
    belongs to another structure, and a retry fails identically until the file
    is replaced.
    """


def parent_residue(name: str) -> str:
    """Return the titratable parent of a protonation-variant residue name, or the name itself."""
    return PARENT_RESIDUE.get(name, name)


def is_hydrogen(atom: str) -> bool:
    """Return whether an atom name names a hydrogen.

    A PQR has no element column, so the name decides: the first letter after any
    leading digits (``1HB``, ``HT1``, ``HD1``). Every atom PDB2PQR writes for a
    protein follows that convention, and so does every name in ``CHARMM.DAT``.
    """
    return atom.lstrip("0123456789").startswith("H")


def chain_characters(chains: Iterable[str]) -> dict[str, str]:
    """Return the single PDB chain character each chain key is written as.

    The keys themselves where every one is a single character; otherwise each
    chain, in order of appearance, gets the next of
    :data:`~nanopnp.structure.ensemble.CHAIN_CHARACTERS`, the rule the stage-1
    export follows. Both the PDB a frame is protonated from and an exported PQR
    use it, so a registration against the ensemble can map either back.

    Raises
    ------
    PQRError
        If the keys are longer than one character and there are more chains
        than single characters to give them.
    """
    ordered = list(dict.fromkeys(chains))
    if all(len(chain) == 1 for chain in ordered):
        return {chain: chain for chain in ordered}
    if len(ordered) > len(CHAIN_CHARACTERS):
        raise PQRError(
            f"{len(ordered)} chains do not fit the {len(CHAIN_CHARACTERS)} single-character chain "
            "identifiers of a PDB or PQR file, and their keys are longer than one character"
        )
    return {chain: CHAIN_CHARACTERS[index] for index, chain in enumerate(ordered)}


@dataclass(frozen=True)
class PQRFrame:
    """One frame of a PQR file: its atom table, coordinates, charges and radii.

    Parameters
    ----------
    name, resname, chain, icode
        String arrays, one entry per atom. ``resname`` is the residue's name as
        resolved by the module docstring's rule, never ``TER``; ``chain`` and
        ``icode`` are empty where the file leaves them blank.
    resid
        Integer array, one entry per atom.
    positions_A
        ``(atoms, 3)`` float64, in Å, as printed.
    charge_e, radius_A
        float64, one entry per atom, as printed.
    """

    name: np.ndarray
    resname: np.ndarray
    chain: np.ndarray
    resid: np.ndarray
    icode: np.ndarray
    positions_A: np.ndarray
    charge_e: np.ndarray
    radius_A: np.ndarray

    @property
    def atoms(self) -> int:
        """Number of atoms."""
        return len(self.name)

    def residues(self) -> list[tuple[str, int, str, str]]:
        """Return ``(chain, resid, icode, name)`` per residue, in order of first appearance."""
        seen: dict[tuple[str, int, str], str] = {}
        for chain, resid, icode, resname in zip(
            self.chain.tolist(),
            self.resid.tolist(),
            self.icode.tolist(),
            self.resname.tolist(),
            strict=True,
        ):
            seen.setdefault((chain, resid, icode), resname)
        return [(chain, resid, icode, name) for (chain, resid, icode), name in seen.items()]


@dataclass(frozen=True)
class _Atom:
    """One ATOM or HETATM line, read."""

    name: str
    resname: str
    chain: str
    resid: int
    icode: str
    xyz: tuple[float, float, float]
    charge: float
    radius: float


def _columns(line: str) -> _Atom | None:
    """Read a line by the PDB columns through the coordinates, then two numbers; ``None`` if not."""
    if len(line) < 54:
        return None
    try:
        rest = line[54:].split()
        if len(rest) < 2:
            return None
        sequence = line[22:26].strip()
        return _Atom(
            name=line[12:16].strip(),
            # PDB2PQR writes a four-character residue name (ASPP, GLUP) from
            # column 17, the PDB's alternate-location column, and a shorter one
            # from column 18 (``Atom.get_common_string_rep``, 3.7.1); a PQR
            # carries no alternate location to confuse with it.
            resname=(line[16:20] if line[16] != " " else line[17:21]).strip(),
            chain=line[21].strip(),
            resid=int(sequence),
            icode=line[26].strip() if len(line) > 26 else "",
            xyz=(float(line[30:38]), float(line[38:46]), float(line[46:54])),
            charge=float(rest[0]),
            radius=float(rest[1]),
        )
    except ValueError:
        return None


def _fields(line: str) -> _Atom | None:
    """Read a line as whitespace-separated fields; ``None`` if they do not read.

    ``record serial name resname [chain] resSeq[icode] x y z charge radius``, the
    layout ``pdb2pqr.io.read_pqr`` assumes.
    """
    tokens = line.split()
    if tokens and tokens[0].startswith("HETATM") and tokens[0] != "HETATM":
        # A six-character record runs into a five-digit serial (``HETATM12345``),
        # which is PDB2PQR's own layout; read as one token it shifts every field.
        tokens = ["HETATM", tokens[0][len("HETATM") :], *tokens[1:]]
    if len(tokens) not in (10, 11):
        return None
    middle = tokens[2:-6]
    try:
        numbers = [float(token) for token in tokens[-5:]]
        sequence = tokens[-6]
        icode = ""
        if sequence and sequence[-1].isalpha():
            sequence, icode = sequence[:-1], sequence[-1]
        resid = int(sequence)
    except ValueError:
        return None
    chain = middle[2] if len(middle) == 3 else ""
    if len(middle[0]) > 4 or len(middle[1]) > 4 or len(chain) > 1:
        # Not an atom name, a residue name and a chain: PDB2PQR fuses a
        # four-character atom name to a four-character residue (``OD2ASPP``),
        # which the columns read and a whitespace split cannot.
        return None
    return _Atom(
        name=middle[0],
        resname=middle[1],
        chain=chain,
        resid=resid,
        icode=icode,
        xyz=(numbers[0], numbers[1], numbers[2]),
        charge=numbers[3],
        radius=numbers[4],
    )


def _read_line(line: str, number: int, source: str) -> _Atom:
    """Read one atom line both ways and return the reading, refusing a disagreement."""
    by_columns, by_fields = _columns(line), _fields(line)
    if by_columns is None and by_fields is None:
        raise PQRError(
            f"{source} line {number}: an {line[:6].strip()} record that neither the PDB columns "
            "nor whitespace-separated fields read as an atom with coordinates, a charge and a "
            "radius (section 5.3.1 NOTE on inputs:)"
        )
    if by_columns is not None and by_fields is not None and by_columns != by_fields:
        raise PQRError(
            f"{source} line {number} reads differently by the PDB columns "
            f"({_describe(by_columns)}) "
            f"and as whitespace-separated fields ({_describe(by_fields)}); one of them is wrong "
            "and the file does not say which (section 5.3.1 NOTE on inputs:)"
        )
    atom = by_columns if by_columns is not None else by_fields
    assert atom is not None
    if not all(math.isfinite(value) for value in (*atom.xyz, atom.charge, atom.radius)):
        raise PQRError(
            f"{source} line {number}: atom {atom.name} of {atom.resname} {atom.resid} carries a "
            "coordinate, charge or radius that is not finite"
        )
    return atom


def _describe(atom: _Atom) -> str:
    """Return a reading as the diagnostic names it."""
    x, y, z = atom.xyz
    return (
        f"{atom.name} {atom.resname} {atom.chain or '-'} {atom.resid}{atom.icode} "
        f"{x} {y} {z} {atom.charge} {atom.radius}"
    )


def _residue_name(names: set[str]) -> str | None:
    """Return a residue's name from the non-``TER`` names its atoms carry, or ``None``.

    One name, or a parent and one of its variants: PDB2PQR writes a residue it
    patched to a protonation variant with its backbone under the parent and its
    side chain under the variant (``ASP`` and ``ASPP`` in one ``ASP 21`` at pH 2,
    PDB2PQR 3.7.1), and the variant is the state.
    """
    parents = {parent_residue(name) for name in names}
    if len(parents) != 1:
        return None
    variants = names - parents
    if len(variants) > 1:
        return None
    return variants.pop() if variants else parents.pop()


def _frame(atoms: Sequence[_Atom], index: int, source: str) -> PQRFrame:
    """Assemble one frame, resolving each residue's name from its non-patch atoms."""
    import numpy as np

    names: dict[tuple[str, int, str], set[str]] = {}
    for atom in atoms:
        key = (atom.chain, atom.resid, atom.icode)
        names.setdefault(key, set())
        if atom.resname not in PATCH_RESIDUES:
            names[key].add(atom.resname)
    resolved: dict[tuple[str, int, str], str] = {}
    for (chain, resid, icode), found in names.items():
        name = _residue_name(found)
        if name is None:
            what = (
                f"carries the names {', '.join(sorted(found))}"
                if found
                else f"carries only patch atoms ({', '.join(sorted(PATCH_RESIDUES))})"
            )
            raise PQRError(
                f"{source} frame {index}: residue {resid}{icode} of chain {chain or '-'!r} {what}; "
                "a residue is its chain, number and insertion code, and has one name"
            )
        resolved[(chain, resid, icode)] = name
    return PQRFrame(
        name=np.array([atom.name for atom in atoms], dtype=str),
        resname=np.array(
            [resolved[(atom.chain, atom.resid, atom.icode)] for atom in atoms], dtype=str
        ),
        chain=np.array([atom.chain for atom in atoms], dtype=str),
        resid=np.array([atom.resid for atom in atoms], dtype=np.int64),
        icode=np.array([atom.icode for atom in atoms], dtype=str),
        positions_A=np.array([atom.xyz for atom in atoms], dtype=np.float64).reshape(-1, 3),
        charge_e=np.array([atom.charge for atom in atoms], dtype=np.float64),
        radius_A=np.array([atom.radius for atom in atoms], dtype=np.float64),
    )


def parse_pqr(text: str, *, source: str = "<string>") -> tuple[PQRFrame, ...]:
    """Read the frames of a PQR document.

    Parameters
    ----------
    text
        The file's contents.
    source
        Named in every diagnostic.

    Raises
    ------
    PQRError
        For a line the two readings disagree on or neither reads, an atom outside
        a ``MODEL`` in a file that has them, an unterminated or empty ``MODEL``, a
        residue with two names, or frames that do not hold the same residues.
    """
    frames: list[list[_Atom]] = []
    current: list[_Atom] | None = None
    loose: list[_Atom] = []
    modelled = False
    for number, line in enumerate(text.splitlines(), start=1):
        record = line[:6].strip()
        if record not in (*_RECORDS, "MODEL", "ENDMDL"):
            # A whitespace-separated file need not pad its record name to six.
            record = (line.split() or [""])[0]
        if record == "MODEL":
            if current is not None:
                raise PQRError(f"{source} line {number}: MODEL inside a MODEL without ENDMDL")
            if loose:
                raise PQRError(
                    f"{source} line {number}: MODEL after atoms outside any MODEL; a file with "
                    "MODEL records holds every atom inside one"
                )
            modelled = True
            current = []
        elif record == "ENDMDL":
            if current is None:
                raise PQRError(f"{source} line {number}: ENDMDL without a MODEL")
            if not current:
                raise PQRError(f"{source} line {number}: MODEL {len(frames)} holds no atom")
            frames.append(current)
            current = None
        elif record in _RECORDS:
            atom = _read_line(line, number, source)
            if current is not None:
                current.append(atom)
            elif modelled:
                raise PQRError(
                    f"{source} line {number}: an atom outside any MODEL in a file with MODEL "
                    "records"
                )
            else:
                loose.append(atom)
    if current is not None:
        raise PQRError(f"{source}: MODEL {len(frames)} is not closed by ENDMDL")
    if not modelled:
        if not loose:
            raise PQRError(f"{source} holds no ATOM or HETATM record")
        frames = [loose]
    read = tuple(_frame(atoms, index, source) for index, atoms in enumerate(frames))
    check_same_residues(read, source=source)
    return read


def read_pqr(path: Path) -> tuple[PQRFrame, ...]:
    """Read the frames of a PQR file; see :func:`parse_pqr`."""
    return parse_pqr(path.read_text(encoding="utf-8"), source=str(path))


def check_same_residues(frames: Sequence[PQRFrame], *, source: str) -> None:
    """Refuse frames that do not hold the same residues, naming the first frame that differs.

    Residues are compared by chain, number, insertion code and parent name, in
    order, so a histidine PDB2PQR 2.1.1 wrote as ``HSE`` in one frame and ``HSD``
    in the next is one residue.
    """
    if not frames:
        return
    reference = [
        (chain, resid, icode, parent_residue(name))
        for chain, resid, icode, name in frames[0].residues()
    ]
    for index, frame in enumerate(frames[1:], start=1):
        found = [
            (chain, resid, icode, parent_residue(name))
            for chain, resid, icode, name in frame.residues()
        ]
        if found == reference:
            continue
        missing = [residue for residue in reference if residue not in found]
        extra = [residue for residue in found if residue not in reference]
        detail = (
            f"it lacks {_residue(missing[0])}"
            if missing
            else f"it adds {_residue(extra[0])}"
            if extra
            else "it holds them in another order"
        )
        raise PQRError(
            f"{source} frame {index} does not hold the residues of frame 0: {detail} (section "
            "5.3.1 NOTE on inputs:)"
        )


def _residue(residue: tuple[str, int, str, str]) -> str:
    """Return a residue key as a diagnostic names it."""
    chain, resid, icode, name = residue
    return f"{name} {resid}{icode} of chain {chain or '-'!r}"


def _number(value: float) -> str:
    """Return a charge or radius as PDB2PQR prints it, or exactly where four decimals would not be.

    The export reads back to the payload exactly (the section 3.1 IF-02 export
    NOTE), so a value that four decimals would round is written in full.
    """
    printed = f"{value:.4f}"
    return printed if float(printed) == value else repr(float(value))


def format_pqr(frames: Sequence[PQRFrame], *, chains: Mapping[str, str] | None = None) -> str:
    """Return frames as a PQR document, one ``MODEL`` per frame where there is more than one.

    Coordinates are written to 0.001 Å in the PDB columns and the charge and the
    radius after them, as PDB2PQR writes them. A coordinate already on that
    lattice therefore reads back exactly, and so does every charge and radius.

    Parameters
    ----------
    frames
        The frames to write.
    chains
        The single character each chain key is written as; :func:`chain_characters`
        of the first frame's chains when omitted.

    Raises
    ------
    PQRError
        For a coordinate the columns cannot hold, a residue name longer than
        four characters or a residue number longer than four digits.
    """
    if not frames:
        raise PQRError("a PQR file holds at least one frame")
    letters = chains if chains is not None else chain_characters(frames[0].chain.tolist())
    lines: list[str] = []
    several = len(frames) > 1
    for index, frame in enumerate(frames):
        if several:
            lines.append(f"MODEL     {index + 1:>4}")
        for serial in range(frame.atoms):
            name = str(frame.name[serial])
            resname = str(frame.resname[serial])
            resid = int(frame.resid[serial])
            x, y, z = (float(value) for value in frame.positions_A[serial])
            if len(resname) > 4 or not -999 <= resid <= 9999:
                raise PQRError(
                    f"residue {resname} {resid} does not fit the PDB residue columns of a PQR file"
                )
            if not all(MIN_COORDINATE_A <= value <= MAX_COORDINATE_A for value in (x, y, z)):
                raise PQRError(
                    f"atom {name} of {resname} {resid} lies at ({x}, {y}, {z}) Å, outside what "
                    "the PDB coordinate columns hold"
                )
            field = name if len(name) >= 4 else f" {name:<3}"
            lines.append(
                f"ATOM  {(serial + 1) % 100000:5d} {field:<4} {resname:<4}"
                f"{letters[str(frame.chain[serial])]:1}{resid:4d}{frame.icode[serial]!s:1}   "
                f"{x:8.3f}{y:8.3f}{z:8.3f} {_number(float(frame.charge_e[serial]))} "
                f"{_number(float(frame.radius_A[serial]))}"
            )
        if several:
            lines.append("ENDMDL")
    lines.append("END")
    return "\n".join(lines) + "\n"


def write_pqr(
    path: Path, frames: Sequence[PQRFrame], *, chains: Mapping[str, str] | None = None
) -> Path:
    """Write frames to ``path`` as :func:`format_pqr` formats them; return the path."""
    path.write_text(format_pqr(frames, chains=chains), encoding="utf-8")
    return path
