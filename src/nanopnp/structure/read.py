"""Reading a structure and its ensemble into one MDAnalysis universe (IF-04, FR-03)."""

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

from nanopnp.io.resolved import parse_chains

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

logger = logging.getLogger(__name__)

ANGSTROM_NM = 0.1

PS_NS = 1e-3

STRUCTURE_SUFFIXES: dict[str, Literal["pdb", "mmcif"]] = {
    ".pdb": "pdb",
    ".ent": "pdb",
    ".cif": "mmcif",
    ".mmcif": "mmcif",
}

TRAJECTORY_FORMATS: dict[str, str] = {
    ".dcd": "DCD",
    ".xtc": "XTC",
    ".trr": "TRR",
    ".nc": "NCDF",
    ".ncdf": "NCDF",
}

HISTIDINES: frozenset[str] = frozenset({"HSD", "HSE", "HSP", "HID", "HIE", "HIP"})

COVERAGE_FRACTION = 0.5


class StructureInputError(ValueError): ...


def structure_format(path: Path) -> Literal["pdb", "mmcif"]:
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
    found = TRAJECTORY_FORMATS.get(path.suffix.lower())
    if found is None:
        raise StructureInputError(
            f"structure.ensemble.trajectory {path.name!r} is not a trajectory this stage reads; "
            f"the accepted extensions are {', '.join(TRAJECTORY_FORMATS)} (IF-04)"
        )
    return found


def _require_file(path: Path, key: str) -> None:
    if not path.is_file():
        raise StructureInputError(f"{key} {str(path)!r} does not exist or is not a file")


def load_universe(source: Path, trajectory: Path | None = None) -> mda.Universe:
    _require_file(source, "structure.source.path")
    kind = structure_format(source)
    if trajectory is not None:
        _require_file(trajectory, "structure.ensemble.trajectory")
        chosen = trajectory_format(trajectory)
    with warnings.catch_warnings():
        # Defaulted-record warnings are noise; the ones that matter are re-checked in select.
        warnings.simplefilter("ignore")
        if kind == "mmcif":
            universe = _universe_from_mmcif(source)
        else:
            universe = mda.Universe(str(source), topology_format="PDB", format="PDB")
        if trajectory is not None:
            try:
                universe.load_new(str(trajectory), format=chosen)
            except ValueError as error:
                # MDAnalysis raises a bare ValueError on an atom-count mismatch; name both files.
                raise StructureInputError(
                    f"structure.ensemble.trajectory {trajectory.name!r} cannot be read against "
                    f"structure.source.path {source.name!r}, which holds {len(universe.atoms)} "
                    f"atoms: {error}"
                ) from error
    return universe


def _universe_from_mmcif(path: Path) -> mda.Universe:
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
        # Equal counts are not the same atoms: another chain order would mis-assign coordinates.
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
    element: np.ndarray
    name: np.ndarray
    resname: np.ndarray
    resid: np.ndarray
    icode: np.ndarray
    chain: np.ndarray

    def __len__(self) -> int:
        return len(self.name)


@dataclass(frozen=True)
class Selection:
    group: mda.AtomGroup
    atoms: AtomTable
    chain_key: str
    chains: tuple[str, ...]
    fit_index: np.ndarray
    common_index: np.ndarray


def _chain_keys(group: mda.AtomGroup) -> tuple[list[str], str]:
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
    # Element and altloc refusals apply only to the chains kept (§5.3.1 NOTE).
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
    chain = str(getattr(atom, "chainID", "")).strip() or str(getattr(atom, "segid", "")).strip()
    return (
        f"{int(atom.index) + 1} ({atom.name} {atom.resname} {int(atom.resid)}"
        f"{', chain ' + chain if chain else ''})"
    )


@dataclass(frozen=True)
class FrameWindow:
    indices: tuple[int, ...]
    times_ns: tuple[float, ...]
    interval_ns: float
    available: int

    def summary(self) -> dict[str, Any]:
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
    available = len(times_ns)
    window = list(range(available))
    if last_ns is not None:
        span = times_ns[-1] - times_ns[0]
        if not last_ns <= span + interval_ns:
            raise StructureInputError(
                f"structure.ensemble.frames.last_ns is {last_ns:g} ns, but the file records "
                f"{available} frames spanning {span:.6g} ns at an interval of {interval_ns:.6g} "
                "ns. A file written without a timestep reads as 1 ps or 0 ps per frame, so this "
                "window would be the whole trajectory in silence (section 5.3.1 NOTE)"
            )
        start = times_ns[-1] - last_ns
        # Slack for float32 dt accumulated as frame * dt (a DCD stores it so); a thousandth of
        # an interval never admits a neighbouring frame and covers ~1.6e4 frames of drift.
        slack = 1e-9 * max(1.0, abs(times_ns[-1])) + 1e-3 * interval_ns
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
    trajectory = universe.trajectory
    with warnings.catch_warnings():
        # The "no dt information" warning repeats what the recorded interval already says.
        warnings.simplefilter("ignore")
        times = tuple(float(step.time) * PS_NS for step in trajectory)
        interval = float(trajectory.dt) * PS_NS
    return times, (0.0 if math.isnan(interval) else interval)


def positions_nm(group: mda.AtomGroup, indices: Sequence[int]) -> np.ndarray:
    import numpy as np

    trajectory = group.universe.trajectory
    # Filled in place: a list of frames plus its stack held the ensemble twice.
    positions = np.empty((len(indices), len(group), 3), dtype=np.float64)
    with warnings.catch_warnings():
        # Re-reading a PDB frame repeats reader notices that do not bear on the coordinates.
        warnings.simplefilter("ignore")
        for frame, index in enumerate(indices):
            trajectory[index]
            # Widened to float64 before scaling.
            positions[frame] = group.positions
            positions[frame] *= ANGSTROM_NM
    return positions
