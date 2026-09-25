"""Reading a structure and its ensemble into one MDAnalysis universe (IF-04, FR-01, FR-03).

Stage 1's inputs, read and checked before any geometry is computed. Three
readers meet in one object: MDAnalysis reads PDB and every trajectory format,
and gemmi reads mmCIF, which MDAnalysis 2.10 does not
(``.knowledge/07-software-stack.md`` §2). The gemmi result is poured into an
MDAnalysis ``Universe`` built from its topology attributes, with the coordinates
in a ``MemoryReader``, so nothing downstream knows which reader ran (WP18 D2).

**Every refusal names what it refused** (QR-12). The §5.3.1 NOTE on
``structure:`` is the contract:

- an element must be in the file, never guessed — a guessed element is how a
  C-alpha becomes calcium, and a plausible wrong radius in stage 2;
- an alternate location is refused, because choosing between them is structure
  preparation, which the pipeline does not do;
- the chains must number ``n``, a listed chain must be present, each must carry
  at least half the C-alpha of the most complete one, and they must agree in
  residue name wherever they share a residue number (FR-03);
- a ``last_ns`` beyond the recorded span, and a ``count`` beyond the window, are
  refused, because a file written without a timestep reads as 1 ps or 0 ps per
  frame and would otherwise yield the whole trajectory in silence.

Coordinates are converted from Å to nm exactly once, here.

MDAnalysis and gemmi are imported at the top: this module is reached only
through :func:`nanopnp.core.stages.create`, which names the ``structure`` extra
when they are missing, so ``nanopnp stage --list`` never imports either
(WP18 D13).
"""

from __future__ import annotations

import logging
import math
import warnings
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import gemmi
import MDAnalysis as mda  # noqa: N813 - the alias the library documents
from MDAnalysis.coordinates.memory import MemoryReader
from MDAnalysis.exceptions import SelectionError

from nanopnp.io.case import parse_chains

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

logger = logging.getLogger(__name__)

ANGSTROM_NM = 0.1
"""Nanometres per ångström: the one unit conversion stage 1 makes."""

PS_NS = 1e-3
"""Nanoseconds per picosecond; MDAnalysis reports times in ps."""

STRUCTURE_SUFFIXES: dict[str, Literal["pdb", "mmcif"]] = {
    ".pdb": "pdb",
    ".ent": "pdb",
    ".cif": "mmcif",
    ".mmcif": "mmcif",
}
"""Structure file extensions, each optionally followed by ``.gz`` (IF-04)."""

TRAJECTORY_FORMATS: dict[str, str] = {
    ".dcd": "DCD",
    ".xtc": "XTC",
    ".trr": "TRR",
    ".nc": "NCDF",
    ".ncdf": "NCDF",
}
"""Trajectory extensions against the MDAnalysis format that reads them (IF-04)."""

HISTIDINES: frozenset[str] = frozenset({"HSD", "HSE", "HSP", "HID", "HIE", "HIP"})
"""Histidine protonation variants, read as ``HIS`` when chains are compared (§5.3.1 NOTE)."""

COVERAGE_FRACTION = 0.5
"""Each chain carries at least this fraction of the most complete chain's C-alpha (§5.3.1 NOTE)."""


class StructureInputError(ValueError):
    """A structure, trajectory or frame selection was refused (FR-03, QR-12).

    Covers the files, the elements, alternate locations, the chains, their
    coverage and residue names, and the frame window. The message names the atom,
    chain, file or quantity refused.
    """


def structure_format(path: Path) -> Literal["pdb", "mmcif"]:
    """Return which reader a structure file takes, from its extension.

    Raises
    ------
    StructureInputError
        If the extension is not one of :data:`STRUCTURE_SUFFIXES`, optionally
        gzipped.
    """
    suffixes = [suffix.lower() for suffix in path.suffixes]
    if suffixes and suffixes[-1] == ".gz":
        suffixes = suffixes[:-1]
    found = STRUCTURE_SUFFIXES.get(suffixes[-1]) if suffixes else None
    if found is None:
        accepted = ", ".join(f"{suffix}[.gz]" for suffix in STRUCTURE_SUFFIXES)
        raise StructureInputError(
            f"structure.source.path {path.name!r} is not a structure file this stage reads; the "
            f"accepted extensions are {accepted} (IF-04)"
        )
    return found


def trajectory_format(path: Path) -> str:
    """Return the MDAnalysis format a trajectory file is read as, from its extension.

    Raises
    ------
    StructureInputError
        If the extension is not one of :data:`TRAJECTORY_FORMATS`.
    """
    found = TRAJECTORY_FORMATS.get(path.suffix.lower())
    if found is None:
        raise StructureInputError(
            f"structure.ensemble.trajectory {path.name!r} is not a trajectory this stage reads; "
            f"the accepted extensions are {', '.join(TRAJECTORY_FORMATS)} (IF-04)"
        )
    return found


def _require_file(path: Path, key: str) -> None:
    """Refuse a path that is not a file, naming the case key."""
    if not path.is_file():
        raise StructureInputError(f"{key} {str(path)!r} does not exist or is not a file")


def load_universe(source: Path, trajectory: Path | None = None) -> mda.Universe:
    """Read a structure, and optionally a trajectory, into one universe (IF-04).

    Parameters
    ----------
    source
        PDB or mmCIF, optionally gzipped. Without a trajectory its models are the
        ensemble.
    trajectory
        DCD, XTC, TRR or NetCDF, whose frames replace the models.

    Raises
    ------
    StructureInputError
        If a file is missing, has an extension outside the accepted set, or an
        mmCIF file has no ``_atom_site.type_symbol`` column; or if the trajectory
        does not hold the structure's atoms.
    """
    _require_file(source, "structure.source.path")
    kind = structure_format(source)
    if trajectory is not None:
        _require_file(trajectory, "structure.ensemble.trajectory")
        chosen = trajectory_format(trajectory)
    with warnings.catch_warnings():
        # MDAnalysis warns for every record it fills with a default (a missing
        # occupancy, an unset segment). Each is re-checked below where it
        # matters; the rest is noise on a structure it read correctly.
        warnings.simplefilter("ignore")
        if kind == "mmcif":
            universe = _universe_from_mmcif(source)
        else:
            universe = mda.Universe(str(source), topology_format="PDB", format="PDB")
        if trajectory is not None:
            try:
                universe.load_new(str(trajectory), format=chosen)
            except ValueError as error:
                # MDAnalysis refuses a trajectory whose atom count is not the
                # topology's with a plain ValueError; name both files (QR-12).
                raise StructureInputError(
                    f"structure.ensemble.trajectory {trajectory.name!r} cannot be read against "
                    f"structure.source.path {source.name!r}, which holds {len(universe.atoms)} "
                    f"atoms: {error}"
                ) from error
    return universe


def _universe_from_mmcif(path: Path) -> mda.Universe:
    """Build an MDAnalysis universe from an mmCIF file read by gemmi (WP18 D2).

    Chains are gemmi's ``auth_asym_id``, residue numbers its ``auth_seq_id`` and
    insertion code, elements the ``type_symbol`` column, alternate locations the
    ``label_alt_id``. Every model becomes a frame, and every model must hold the
    same atoms in the same order.
    """
    import numpy as np

    block = gemmi.cif.read(str(path)).sole_block()
    if not block.find_values("_atom_site.type_symbol"):
        raise StructureInputError(
            f"{path.name!r} has no _atom_site.type_symbol column; every selected atom must carry "
            "its element in the file (SPECIFICATION.md section 5.3.1 NOTE on structure:)"
        )
    structure = gemmi.make_structure_from_block(block)
    if len(structure) == 0:
        raise StructureInputError(f"{path.name!r} holds no model")

    def atoms_of(model: Any) -> list[tuple[Any, Any, Any]]:  # noqa: ANN401 - gemmi is untyped
        return [(chain, residue, atom) for chain in model for residue in chain for atom in residue]

    def identity(atoms: list[tuple[Any, Any, Any]]) -> list[tuple[str, str, str, str]]:
        return [
            (chain.name, str(residue.seqid), residue.name, atom.name)
            for chain, residue, atom in atoms
        ]

    first = atoms_of(structure[0])
    first_identity = identity(first)
    names, elements, altlocs, chains = [], [], [], []
    residues: list[tuple[str, int, str, str]] = []
    resindex: list[int] = []
    for chain, residue, atom in first:
        key = (chain.name, residue.seqid.num, residue.seqid.icode.strip(), residue.name)
        if not residues or residues[-1] != key:
            residues.append(key)
        resindex.append(len(residues) - 1)
        names.append(atom.name)
        elements.append("" if atom.element.name == "X" else atom.element.name)
        altlocs.append("" if atom.altloc == "\0" else atom.altloc)
        chains.append(chain.name)
    frames = []
    for index, model in enumerate(structure):
        atoms = first if index == 0 else atoms_of(model)
        if len(atoms) != len(first):
            raise StructureInputError(
                f"{path.name!r}: model {index + 1} holds {len(atoms)} atoms and model 1 holds "
                f"{len(first)}; the models of an ensemble must hold the same atoms"
            )
        # Equal counts are not the same atoms: a model listing its chains in
        # another order would put one chain's coordinates on another's topology.
        found = first_identity if index == 0 else identity(atoms)
        if found != first_identity:
            mismatch = next(
                position
                for position, pair in enumerate(zip(found, first_identity, strict=True))
                if pair[0] != pair[1]
            )
            raise StructureInputError(
                f"{path.name!r}: atom {mismatch + 1} of model {index + 1} is not atom "
                f"{mismatch + 1} of model 1; the models of an ensemble must hold the same atoms "
                "in the same order"
            )
        frames.append([[atom.pos.x, atom.pos.y, atom.pos.z] for _, _, atom in atoms])

    universe = mda.Universe.empty(
        len(first),
        n_residues=len(residues),
        n_segments=1,
        atom_resindex=np.asarray(resindex),
        residue_segindex=np.zeros(len(residues), dtype=int),
        trajectory=True,
    )
    universe.add_TopologyAttr("names", names)
    universe.add_TopologyAttr("elements", elements)
    universe.add_TopologyAttr("altLocs", altlocs)
    universe.add_TopologyAttr("chainIDs", chains)
    universe.add_TopologyAttr("resnames", [residue[3] for residue in residues])
    universe.add_TopologyAttr("resids", [residue[1] for residue in residues])
    universe.add_TopologyAttr("icodes", [residue[2] for residue in residues])
    universe.add_TopologyAttr("segids", [""])
    universe.load_new(np.asarray(frames, dtype=np.float32), format=MemoryReader)
    return universe


@dataclass(frozen=True)
class AtomTable:
    """The selected atoms, in file order (WP18 D10).

    Parameters
    ----------
    element, name, resname, chain
        String arrays; ``chain`` is the chain key of :attr:`Selection.chain_key`.
    resid
        Integer residue numbers.
    icode
        Insertion codes, blank where the file has none. Residues 27 and 27A
        share a number and are told apart only by this.
    """

    element: np.ndarray
    name: np.ndarray
    resname: np.ndarray
    resid: np.ndarray
    icode: np.ndarray
    chain: np.ndarray

    def __len__(self) -> int:
        """Return the number of atoms."""
        return len(self.name)


@dataclass(frozen=True)
class Selection:
    """The atoms stage 1 carries, and the C-alpha sets it fits on.

    Parameters
    ----------
    group
        The selected MDAnalysis atom group; its positions follow the trajectory.
    atoms
        The atom table of ``group``.
    chain_key
        Which identifier named the chains: ``chainID``, ``segid``, or
        ``chainID, segid where blank``.
    chains
        The chain keys in file order.
    fit_index
        Indices into ``group`` of every C-alpha of the selection: the FR-01
        superposition set.
    common_index
        ``(n, m)`` indices into ``group`` of the C-alpha each chain carries at
        the ``m`` residues every chain shares, in residue order: the FR-02 set.
    """

    group: mda.AtomGroup
    atoms: AtomTable
    chain_key: str
    chains: tuple[str, ...]
    fit_index: np.ndarray
    common_index: np.ndarray


def _chain_keys(group: mda.AtomGroup) -> tuple[list[str], str]:
    """Return each atom's chain key, and which identifier supplied it."""
    chain_ids = [str(value).strip() for value in group.chainIDs]
    segids = [str(value).strip() for value in group.segids]
    blank = [not value for value in chain_ids]
    if not any(blank):
        return chain_ids, "chainID"
    if all(blank):
        return segids, "segid"
    keys = [
        segid if missing else chain
        for chain, segid, missing in zip(chain_ids, segids, blank, strict=True)
    ]
    return keys, "chainID, segid where blank"


def select(universe: mda.Universe, *, selection: str, chains: str, n: int) -> Selection:
    """Select the pore's atoms and check the oligomeric state (FR-03, QR-12).

    Parameters
    ----------
    universe
        As :func:`load_universe` returned it.
    selection
        ``structure.source.selection``, an MDAnalysis selection string.
    chains
        ``structure.source.chains``: ``all`` or a comma-separated list.
    n
        The order of the expected point group.

    Raises
    ------
    StructureInputError
        Naming the first atom with no element or with an alternate location; the
        chain count against ``n``; a listed chain that is absent; a chain whose
        C-alpha coverage is under half the most complete chain's; a residue-name
        disagreement between chains; or too few shared C-alpha to fit.
    """
    import numpy as np

    try:
        group = universe.select_atoms(selection)
    except SelectionError as error:
        raise StructureInputError(
            f"structure.source.selection {selection!r} is not an MDAnalysis selection: {error}"
        ) from error
    if len(group) == 0:
        raise StructureInputError(f"structure.source.selection {selection!r} selects no atom")
    keys, chain_key = _chain_keys(group)
    listed = parse_chains(chains)
    present = tuple(dict.fromkeys(keys))
    if listed is not None:
        missing = [chain for chain in listed if chain not in present]
        if missing:
            raise StructureInputError(
                f"structure.source.chains lists {', '.join(missing)}, which the selection does not "
                f"contain; it holds chains {', '.join(present)} by {chain_key} (FR-03)"
            )
        mask = np.isin(np.asarray(keys), np.asarray(listed))
        group = group[mask]
        keys = [key for key, kept in zip(keys, mask, strict=True) if kept]
        present = tuple(chain for chain in present if chain in listed)
    # The element and alternate-location refusals apply to the atoms stage 1
    # keeps: a chain source.chains leaves out is not selected (section 5.3.1 NOTE).
    if not hasattr(group, "elements"):
        raise StructureInputError(
            f"no atom of structure.source.selection {selection!r} carries an element in the file; "
            "every selected atom must, in the PDB element columns or the mmCIF type_symbol, "
            "because a guessed element is how a C-alpha becomes calcium (section 5.3.1 NOTE)"
        )
    elements = [str(value).strip() for value in group.elements]
    for index, element in enumerate(elements):
        if not element:
            raise StructureInputError(
                f"atom {_describe(group[index])} carries no element in the file; every selected "
                "atom must, in the PDB element columns or the mmCIF type_symbol, because a "
                "guessed element is how a C-alpha becomes calcium (section 5.3.1 NOTE)"
            )
    if hasattr(group, "altLocs"):
        for index, altloc in enumerate(group.altLocs):
            if str(altloc).strip():
                raise StructureInputError(
                    f"atom {_describe(group[index])} has alternate location {str(altloc)!r}; "
                    "choosing between alternate locations is structure preparation, which the "
                    "pipeline does not do (section 5.3.1 NOTE). Select one location, or prepare "
                    "the file"
                )

    if len(present) != n:
        raise StructureInputError(
            f"C{n} expects {n} chains, and the selection holds {len(present)} "
            f"({', '.join(present)}) by {chain_key}; list the chains of one assembly in "
            "structure.source.chains, or correct symmetry.point_group (FR-03)"
        )

    key_array = np.asarray(keys)
    names = np.asarray([str(value) for value in group.names])
    element_array = np.asarray(elements)
    resnames = np.asarray([str(value) for value in group.resnames])
    resids = np.asarray(group.resids, dtype=np.int64)
    icodes = (
        np.asarray([str(value).strip() for value in group.icodes])
        if hasattr(group, "icodes")
        else np.full(len(group), "")
    )
    is_ca = (names == "CA") & (element_array == "C")

    per_chain: dict[str, dict[tuple[int, str], int]] = {}
    residue_names: dict[str, dict[tuple[int, str], str]] = {}
    for index in range(len(group)):
        chain = str(key_array[index])
        residue = (int(resids[index]), str(icodes[index]))
        name = str(resnames[index])
        residue_names.setdefault(chain, {})[residue] = "HIS" if name in HISTIDINES else name
        if is_ca[index]:
            per_chain.setdefault(chain, {})[residue] = index

    counts = {chain: len(per_chain.get(chain, {})) for chain in present}
    most = max(counts.values())
    for chain in present:
        if counts[chain] < COVERAGE_FRACTION * most:
            raise StructureInputError(
                f"chain {chain} carries {counts[chain]} C-alpha, under half the {most} of the "
                f"most complete chain; a truncated chain would bias the axis and the density "
                "(FR-03, section 5.3.1 NOTE)"
            )

    reference = present[0]
    for chain in present[1:]:
        for residue, name in residue_names[chain].items():
            expected = residue_names[reference].get(residue)
            if expected is not None and expected != name:
                raise StructureInputError(
                    f"chain {chain} has {name} at residue {residue[0]}{residue[1]} where chain "
                    f"{reference} has {expected}; the chains of a C{n} assembly must agree in "
                    "residue name wherever they share a residue number (FR-03)"
                )

    common = sorted(set.intersection(*(set(per_chain.get(chain, {})) for chain in present)))
    if len(common) < 3:
        raise StructureInputError(
            f"the {n} chains share {len(common)} C-alpha, and a superposition needs at least 3"
        )
    common_index = np.asarray(
        [[per_chain[chain][residue] for residue in common] for chain in present], dtype=np.int64
    )
    table = AtomTable(
        element=element_array,
        name=names,
        resname=resnames,
        resid=resids,
        icode=icodes,
        chain=key_array,
    )
    return Selection(
        group=group,
        atoms=table,
        chain_key=chain_key,
        chains=present,
        fit_index=np.flatnonzero(is_ca),
        common_index=common_index,
    )


def _describe(atom: Any) -> str:  # noqa: ANN401 - an MDAnalysis Atom, which is untyped
    """Name one atom as a diagnostic should: index, name, residue and chain."""
    chain = str(getattr(atom, "chainID", "")).strip() or str(getattr(atom, "segid", "")).strip()
    return (
        f"{int(atom.index) + 1} ({atom.name} {atom.resname} {int(atom.resid)}"
        f"{', chain ' + chain if chain else ''})"
    )


@dataclass(frozen=True)
class FrameWindow:
    """The frames of the ensemble, as selected and as their file records them (§5.3.1 NOTE).

    Parameters
    ----------
    indices
        Frame indices into the trajectory (or the source file's models).
    times_ns
        Their times as read, in nanoseconds; not corrected, because a wrong
        timestep cannot be detected inside its span.
    interval_ns
        The reader's frame interval.
    available
        How many frames the file holds.
    """

    indices: tuple[int, ...]
    times_ns: tuple[float, ...]
    interval_ns: float
    available: int

    def summary(self) -> dict[str, Any]:
        """Return the window as plain data."""
        return {
            "indices": list(self.indices),
            "times_ns": list(self.times_ns),
            "interval_ns": self.interval_ns,
            "available": self.available,
        }


def select_frames(
    times_ns: Sequence[float],
    interval_ns: float,
    *,
    last_ns: float | None = None,
    count: int | None = None,
) -> FrameWindow:
    """Choose the ensemble's frames by ``last_ns`` and ``count`` (§5.3.1 NOTE, WP18 D5).

    ``last_ns`` keeps the frames within that many nanoseconds of the last one, by
    the recorded times. ``count`` then keeps ``count`` frames at the uniform
    stride ``⌊N/count⌋``, ending on the last frame of the window of ``N``.

    Raises
    ------
    StructureInputError
        If ``last_ns`` exceeds the recorded span by more than one frame interval,
        naming the span and the interval; or if ``count`` exceeds the window,
        naming both.
    """
    available = len(times_ns)
    window = list(range(available))
    if last_ns is not None:
        span = times_ns[-1] - times_ns[0]
        if last_ns > span + interval_ns:
            raise StructureInputError(
                f"structure.ensemble.frames.last_ns is {last_ns:g} ns, but the file records "
                f"{available} frames spanning {span:.6g} ns at an interval of {interval_ns:.6g} "
                "ns. A file written without a timestep reads as 1 ps or 0 ps per frame, so this "
                "window would be the whole trajectory in silence (section 5.3.1 NOTE)"
            )
        start = times_ns[-1] - last_ns
        # A relative slack for the round-off of times accumulated as frame * dt.
        slack = 1e-9 * max(1.0, abs(times_ns[-1]))
        window = [index for index in window if times_ns[index] >= start - slack]
    if count is not None:
        if count > len(window):
            raise StructureInputError(
                f"structure.ensemble.frames.count is {count}, and the window holds "
                f"{len(window)} frames (section 5.3.1 NOTE)"
            )
        stride = len(window) // count
        last = len(window) - 1
        window = [window[last - stride * (count - 1 - k)] for k in range(count)]
    return FrameWindow(
        indices=tuple(window),
        times_ns=tuple(float(times_ns[index]) for index in window),
        interval_ns=interval_ns,
        available=available,
    )


def frame_times(universe: mda.Universe) -> tuple[tuple[float, ...], float]:
    """Return every frame's recorded time and the reader's interval, in nanoseconds."""
    trajectory = universe.trajectory
    with warnings.catch_warnings():
        # "Reader has no dt information, set to 1.0 ps": the 1 ps is what the
        # file records, and the last_ns gate below exists because of it. The
        # warning says nothing the recorded interval does not.
        warnings.simplefilter("ignore")
        times = tuple(float(step.time) * PS_NS for step in trajectory)
        interval = float(trajectory.dt) * PS_NS
    return times, (0.0 if math.isnan(interval) else interval)


def positions_nm(group: mda.AtomGroup, indices: Sequence[int]) -> np.ndarray:
    """Return ``(frames, atoms, 3)`` positions of ``group`` at ``indices``, in nm, float64."""
    import numpy as np

    trajectory = group.universe.trajectory
    frames = []
    with warnings.catch_warnings():
        # Re-reading a PDB frame repeats the reader's notices (a placeholder
        # CRYST1 cell, a filled-in occupancy); none bears on the coordinates.
        warnings.simplefilter("ignore")
        for index in indices:
            trajectory[index]
            frames.append(np.asarray(group.positions, dtype=np.float64) * ANGSTROM_NM)
    return np.stack(frames)
