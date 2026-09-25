"""VER-48: stage 1 on real files — readers, refusals, frames, the artefact and the walk.

The axis itself is verified on synthetic assemblies in ``test_structure_axis.py``;
this file holds the parts that need a file: the PDB and mmCIF readers, every
trajectory format, the input refusals of the section 5.3.1 NOTE on
``structure:``, the frame window, the superposition, the artefact and the walk
rules (IF-02, IF-04, FR-01 to FR-03, FR-27).

The vendored wwPDB entry 2WCD holds two dodecamers (chains A-L and M-X) in the
crystal frame, where the pore axis is 22.9 degrees from z and +z points to
*trans*. That frame is refused by the orientation gate, as the specification
requires (a test below holds it). The stage-one run uses chains A-L rigidly
moved into a frame the stage admits: a test-time preparation, since preparing a
structure is outside the pipeline (WP18 Outcomes).
"""

from __future__ import annotations

import json
import logging
import math
import subprocess
import sys
import warnings
from pathlib import Path

import gemmi
import MDAnalysis as mda  # noqa: N813 - the alias the library documents
import numpy as np
import pytest
from MDAnalysis.coordinates.memory import MemoryReader

from nanopnp.core.stages import create
from nanopnp.io.case import (
    CaseValidationError,
    UnsupportedCaseSection,
    load_case,
    resolve,
)
from nanopnp.io.run import UnknownStageError, run_case
from nanopnp.io.store import Store
from nanopnp.structure.axis import SymmetryGateError, measure_axis, minimal_rotation
from nanopnp.structure.ensemble import AlignedEnsemble
from nanopnp.structure.read import (
    StructureInputError,
    frame_times,
    load_universe,
    positions_nm,
    select,
    select_frames,
)

logger = logging.getLogger(__name__)

STRUCTURES = Path(__file__).parents[1] / "data" / "structures"
PDB = STRUCTURES / "2wcd.pdb.gz"
CIF = STRUCTURES / "2wcd.cif.gz"
DODECAMER = "A,B,C,D,E,F,G,H,I,J,K,L"

PREPARED_TILT_DEG = 4.0
"""The tilt the prepared copy is left with, so the frame transform is not the identity."""

PREPARED_SHIFT_NM = np.array([0.6, -0.35, 1.2])


def _case(tmp_path: Path, structure: str, *, name: str = "structure") -> Path:
    """Write a case file carrying ``structure`` (YAML text) and return its path."""
    text = (
        "schema: nanopnp/case/v2\n"
        f"name: {name}\n"
        f"structure:\n{structure}"
        "electrolyte:\n"
        "  species: [{name: Na+, z: +1}, {name: Cl-, z: -1}]\n"
        "  concentration_M: 0.1\n"
        "  parameters: willems2020_nacl\n"
        "boundary_conditions: {bias_V: 0.1}\n"
        "physics: {model: epnp-ns, solid_permittivities: {membrane: 3.2}}\n"
    )
    path = tmp_path / f"{name}.case.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def _block(
    path: Path,
    *,
    chains: str = "all",
    point_group: str = "C12",
    axis: str = "auto",
    trajectory: Path | None = None,
    frames: str = "",
    selection: str = "protein",
) -> str:
    """Return a ``structure:`` block as YAML text."""
    lines = [
        f"  source: {{path: {path}, chains: '{chains}', selection: '{selection}'}}\n",
        f"  symmetry: {{point_group: {point_group}, axis: {axis}}}\n",
    ]
    if trajectory is not None or frames:
        ensemble = [f"trajectory: {trajectory}"] if trajectory is not None else []
        if frames:
            ensemble.append(f"frames: {{{frames}}}")
        lines.append(f"  ensemble: {{{', '.join(ensemble)}}}\n")
    return "".join(lines)


def _dodecamer() -> mda.AtomGroup:
    """Return chains A-L of the deposited 2WCD, protein only."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        universe = load_universe(PDB)
    return universe.select_atoms("protein and chainID " + " ".join(DODECAMER.split(",")))


def _rotation(axis: np.ndarray, angle: float) -> np.ndarray:
    """Return the rotation by ``angle`` (radians) about ``axis``."""
    k = np.asarray(axis, dtype=np.float64) / np.linalg.norm(axis)
    skew = np.array([[0.0, -k[2], k[1]], [k[2], 0.0, -k[0]], [-k[1], k[0], 0.0]])
    return np.eye(3) + math.sin(angle) * skew + (1.0 - math.cos(angle)) * (skew @ skew)


def _write(group: mda.AtomGroup, frames_angstrom: np.ndarray, path: Path) -> Path:
    """Write ``group``'s topology with ``frames_angstrom`` as its coordinates.

    A ``.pdb`` gets the first frame; a trajectory extension gets every frame.
    """
    universe = mda.Merge(group)
    universe.load_new(np.asarray(frames_angstrom, dtype=np.float32), format=MemoryReader)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if path.suffix == ".pdb":
            universe.atoms.write(str(path))
        else:
            with mda.Writer(str(path), universe.atoms.n_atoms) as writer:
                for _ in universe.trajectory:
                    writer.write(universe.atoms)
    return path


def _prepared_rotation(group: mda.AtomGroup) -> np.ndarray:
    """Return a rotation taking the deposited dodecamer's axis to z, *cis* up, then tilting it 4°.

    Which end is *cis* is read from the structure, not assumed: the ClyA cap is the
    wide end (``.knowledge/04-clya-geometry-and-charge.md``). In the deposited
    frame the axis signed to +z has its narrow end up, so +z there points to
    *trans* — the same finding as a Kabsch superposition of chains A-L onto the
    author's aligned copy, which maps it to -z (WP18 Outcomes).
    """
    chains = []
    for chain in DODECAMER.split(","):
        ca = group.select_atoms(f"chainID {chain} and name CA and resid 8:292")
        chains.append(ca.positions / 10.0)
    record = measure_axis(np.asarray(chains), 12)
    flat = np.concatenate(chains)
    height = (flat - record.centroid_nm) @ record.axis
    radial = np.linalg.norm((flat - record.centroid_nm) - np.outer(height, record.axis), axis=1)
    top = radial[height > np.quantile(height, 0.8)].mean()
    bottom = radial[height < np.quantile(height, 0.2)].mean()
    cis = record.axis if top > bottom else -record.axis
    logger.info("deposited 2WCD: +axis end radius %.2f nm, -axis end %.2f nm", top, bottom)
    to_z = (
        _rotation(np.cross(cis, [0, 0, 1.0]), math.acos(float(cis[2]))) if cis[2] < 1 else np.eye(3)
    )
    tilt = _rotation(np.array([1.0, 1.0, 0.0]), math.radians(PREPARED_TILT_DEG))
    return tilt @ to_z


@pytest.fixture(scope="module")
def prepared(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Chains A-L of 2WCD, rigidly moved to *cis* up, tilted 4° and shifted: a prepared file."""
    group = _dodecamer()
    rotation = _prepared_rotation(group)
    moved = group.positions @ rotation.T + PREPARED_SHIFT_NM * 10.0
    return _write(group, moved[None], tmp_path_factory.mktemp("prepared") / "2wcd-prepared.pdb")


def _run(case: Path, store: Path) -> AlignedEnsemble:
    """Run stage 1 alone and return the ensemble it wrote."""
    result = run_case(case, store=Store(store), upto="structure", write=False)
    artefact = result.artefacts["structure"]
    return AlignedEnsemble.read(artefact.payload["ensemble"])


def test_ver48_the_deposited_2wcd_frame_is_refused_by_the_orientation_gate(
    tmp_path: Path,
) -> None:
    """The wwPDB entry as deposited: 22.9 degrees from z, refused naming the angle (§5.3.1 NOTE)."""
    case = _case(tmp_path, _block(PDB, chains=DODECAMER))
    with pytest.raises(SymmetryGateError, match=r"orientation gate: the detected axis is 22\.9"):
        run_case(case, store=Store(tmp_path / "store"), upto="structure", write=False)


def test_ver48_2wcd_runs_as_stage_one(prepared: Path, tmp_path: Path) -> None:
    """``run_case(upto="structure")``: 12 chains, 285 common C-alpha, gates pass, output on z.

    The prepared copy is tilted by 4 degrees, so the stage must measure that tilt
    (the algorithm is equivariant under a rigid move) and undo it. Re-detecting
    the axis on the output gives z through r = 0 to float32 round-off.
    """
    case = _case(tmp_path, _block(prepared))
    result = run_case(case, store=Store(tmp_path / "store"), upto="structure", write=False)
    artefact = result.artefacts["structure"]
    summary = artefact.summary
    ensemble = AlignedEnsemble.read(artefact.payload["ensemble"])

    assert summary["n"] == 12
    assert summary["chain_key"] == "chainID"
    assert summary["common_ca"] == 285
    assert summary["chains_cyclic_order"][0] == "A"
    record = summary["axis"]["file_frame"]
    assert abs(record["tilt_deg"] - PREPARED_TILT_DEG) <= 1e-6
    assert abs(record["angle_deg"] - 30.0) <= 0.01
    logger.info(
        "2WCD A-L: angle %.4f deg, worst spacing %.3f deg, permutation RMSD %.4f nm, tilt %.4f deg",
        record["angle_deg"],
        record["spacing_error_deg"],
        record["rmsd_nm"],
        record["tilt_deg"],
    )

    mean = ensemble.positions_nm.astype(np.float64).mean(axis=0)
    chains = []
    for chain in summary["chains_file_order"]:
        mask = (ensemble.chain == chain) & (ensemble.name == "CA")
        by_resid = dict(zip(ensemble.resid[mask].tolist(), mean[mask], strict=True))
        chains.append([by_resid[resid] for resid in range(8, 293)])
    again = measure_axis(np.asarray(chains), 12)
    assert np.linalg.norm(np.cross(again.axis, [0.0, 0.0, 1.0])) <= 1e-6
    assert np.hypot(*again.foot_nm[:2]) <= 1e-6
    # z' = a.x: the file's axial coordinate along the axis is kept.
    first = ensemble.positions_nm[0].astype(np.float64)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        source = mda.Universe(str(prepared)).select_atoms("protein").positions / 10.0
    axis = np.asarray(record["axis"])
    assert np.max(np.abs(first[:, 2] - source @ axis)) <= 2e-5


def test_ver48_2wcd_pdb_and_mmcif_agree() -> None:
    """PDB and mmCIF of one entry read to the same atom table and coordinates (IF-04)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from_pdb = select(load_universe(PDB), selection="protein", chains=DODECAMER, n=12)
        from_cif = select(load_universe(CIF), selection="protein", chains=DODECAMER, n=12)
    for field in ("element", "name", "resname", "resid", "icode", "chain"):
        assert np.array_equal(getattr(from_pdb.atoms, field), getattr(from_cif.atoms, field)), field
    assert np.array_equal(from_pdb.common_index, from_cif.common_index)
    difference = np.max(
        np.abs(positions_nm(from_pdb.group, [0]) - positions_nm(from_cif.group, [0]))
    )
    assert difference <= 5e-5


@pytest.fixture(scope="module")
def two_chains(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, np.ndarray]:
    """Chains A-B of 2WCD as a PDB, and three frames of coordinates in ångströms."""
    group = _dodecamer().select_atoms("chainID A B")
    rng = np.random.default_rng(3)
    frames = np.stack(
        [group.positions + rng.normal(0.0, 0.5, group.positions.shape) for _ in range(3)]
    )
    directory = tmp_path_factory.mktemp("formats")
    return _write(group, frames, directory / "ab.pdb"), frames


@pytest.mark.parametrize(
    ("suffix", "tolerance_nm"),
    # DCD and NetCDF store float32 angstroms, so the read is the written bytes
    # exactly. TRR stores float32 nanometres, so the conversion costs up to two
    # float32 ulps at 13 nm (2 x 2^-23 x 13 nm = 3.1e-6 nm). XTC is quantised to
    # 0.001 nm, so rounds by half of that, plus the same float32 round-off.
    [(".dcd", 0.0), (".xtc", 5e-4 + 3.1e-6), (".trr", 3.1e-6), (".nc", 0.0), (".ncdf", 0.0)],
)
def test_ver48_each_trajectory_format_reads(
    two_chains: tuple[Path, np.ndarray], suffix: str, tolerance_nm: float, tmp_path: Path
) -> None:
    """DCD, XTC, TRR and NetCDF written from a 2WCD subset read back (IF-04).

    Exact to the float32 bytes written for DCD and NetCDF, which store
    angstroms; within float32 round-off for TRR, which stores nanometres; within
    XTC's 0.001 nm quantisation.
    """
    topology, frames = two_chains
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        group = mda.Universe(str(topology)).atoms
    path = _write(group, frames, tmp_path / f"ab{suffix}")
    universe = load_universe(topology, path)
    read = positions_nm(universe.atoms, range(3))
    assert read.shape == (3, len(group), 3)
    written_nm = frames.astype(np.float32).astype(np.float64) * 0.1
    assert np.max(np.abs(read - written_nm)) <= tolerance_nm


def test_ver48_frame_selection_and_the_time_gate(
    two_chains: tuple[Path, np.ndarray], tmp_path: Path
) -> None:
    """The stride ends on the last frame; an untimed DCD's span refuses ``last_ns``; count > N."""
    times = [0.005 * k for k in range(1000)]
    window = select_frames(times, 0.005, last_ns=5.0, count=50)
    assert window.indices == tuple(range(19, 1000, 20))
    assert window.times_ns[1] - window.times_ns[0] == pytest.approx(0.1)
    # "Within 1 ns of the last" includes the frame exactly 1 ns before it.
    assert select_frames(times, 0.005, last_ns=1.0).indices == tuple(range(799, 1000))
    assert select_frames(times, 0.005, count=3).indices == (333, 666, 999)

    topology, frames = two_chains
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        group = mda.Universe(str(topology)).atoms
    dcd = _write(group, frames, tmp_path / "untimed.dcd")
    recorded, interval = frame_times(load_universe(topology, dcd))
    assert recorded == pytest.approx((0.0, 0.001, 0.002))
    assert interval == pytest.approx(0.001)
    with pytest.raises(StructureInputError, match=r"spanning 0\.002 ns at an interval of 0\.001"):
        select_frames(recorded, interval, last_ns=5.0)
    with pytest.raises(StructureInputError, match=r"count is 4, and the window holds 3"):
        select_frames(recorded, interval, count=4)


def _edited(path: Path, tmp_path: Path, name: str, edit: object) -> Path:
    """Write a copy of ``path`` with ``edit`` applied to its ATOM lines."""
    lines = path.read_text().splitlines()
    atoms = [index for index, line in enumerate(lines) if line.startswith("ATOM")]
    edit(lines, atoms)  # type: ignore[operator]
    target = tmp_path / name
    target.write_text("\n".join(lines) + "\n")
    return target


@pytest.fixture(scope="module")
def dodecamer_pdb(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Chains A-L of 2WCD, as deposited, as a plain PDB the refusal cases edit."""
    group = _dodecamer()
    return _write(group, group.positions[None], tmp_path_factory.mktemp("refusals") / "al.pdb")


def _blank_element(lines: list[str], atoms: list[int]) -> None:
    lines[atoms[3]] = lines[atoms[3]][:76] + "  " + lines[atoms[3]][78:]


def _alternate(lines: list[str], atoms: list[int]) -> None:
    lines[atoms[5]] = lines[atoms[5]][:16] + "A" + lines[atoms[5]][17:]


def _drop_chain_k(lines: list[str], atoms: list[int]) -> None:
    for index in reversed(atoms):
        if lines[index][21] == "K":
            del lines[index]


def _truncate_chain_c(lines: list[str], atoms: list[int]) -> None:
    for index in reversed(atoms):
        if lines[index][21] == "C" and int(lines[index][22:26]) > 120:
            del lines[index]


def _rename_residue(lines: list[str], atoms: list[int]) -> None:
    for index in atoms:
        line = lines[index]
        if line[21] == "D" and int(line[22:26]) == 50:
            lines[index] = line[:17] + "TRP" + line[20:]


@pytest.mark.parametrize(
    ("edit", "chains", "point_group", "message"),
    [
        (_blank_element, "all", "C12", r"atom 4 \(O LYS 8, chain A\) carries no element"),
        (_alternate, "all", "C12", r"atom 6 .* has alternate location 'A'"),
        (_drop_chain_k, "all", "C12", r"C12 expects 12 chains, and the selection holds 11"),
        (None, "A,B,C,D,E,F,G,H,I,J,K,M", "C12", r"lists M, which the selection does not"),
        (_truncate_chain_c, "all", "C12", r"chain C carries \d+ C-alpha, under half"),
        (_rename_residue, "all", "C12", r"chain D has TRP at residue 50 where chain A has"),
    ],
)
def test_ver48_input_refusals(
    dodecamer_pdb: Path,
    tmp_path: Path,
    edit: object,
    chains: str,
    point_group: str,
    message: str,
) -> None:
    """Each input the §5.3.1 NOTE refuses is refused naming the atom or the chain (FR-03, QR-12)."""
    path = dodecamer_pdb if edit is None else _edited(dodecamer_pdb, tmp_path, "edited.pdb", edit)
    case = _case(tmp_path, _block(path, chains=chains, point_group=point_group))
    with pytest.raises(StructureInputError, match=message):
        run_case(case, store=Store(tmp_path / "store"), upto="structure", write=False)


def _alternate_in_chain_l(lines: list[str], atoms: list[int]) -> None:
    index = next(index for index in atoms if lines[index][21] == "L")
    lines[index] = lines[index][:16] + "A" + lines[index][17:]


def test_ver48_element_and_location_refusals_apply_to_the_listed_chains(
    dodecamer_pdb: Path, tmp_path: Path
) -> None:
    """An alternate location in a chain ``source.chains`` leaves out is not refused (§5.3.1 NOTE).

    The chains a case lists are the selected ones; the same file with every
    chain selected is refused naming the atom.
    """
    path = _edited(dodecamer_pdb, tmp_path, "alternate_l.pdb", _alternate_in_chain_l)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        universe = load_universe(path)
    chosen = select(universe, selection="protein", chains="A,B,C,D,E,F,G,H,I,J,K", n=11)
    assert chosen.chains == tuple("ABCDEFGHIJK")
    with pytest.raises(StructureInputError, match=r"chain L\) has alternate location 'A'"):
        select(universe, selection="protein", chains="all", n=12)


def test_ver48_a_malformed_selection_is_refused_naming_the_key(tmp_path: Path) -> None:
    """A selection MDAnalysis cannot parse is a named refusal, not an unexpected error (QR-12)."""
    case = _case(tmp_path, _block(PDB, selection="protien"))
    with pytest.raises(StructureInputError, match=r"selection 'protien' is not an MDAnalysis"):
        run_case(case, store=Store(tmp_path / "store"), upto="structure", write=False)


def test_ver48_a_trajectory_of_other_atoms_is_refused_naming_both_files(
    two_chains: tuple[Path, np.ndarray], tmp_path: Path
) -> None:
    """A trajectory whose atom count is not the structure's is refused naming both (QR-12)."""
    topology, frames = two_chains
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        group = mda.Universe(str(topology)).select_atoms("chainID A")
    count = len(group)
    dcd = _write(group, frames[:, :count], tmp_path / "a.dcd")
    with pytest.raises(StructureInputError, match=r"'a\.dcd' cannot be read against .*'ab\.pdb'"):
        load_universe(topology, dcd)


def test_ver48_mmcif_models_must_hold_the_same_atoms_in_order(tmp_path: Path) -> None:
    """An mmCIF model listing the same atoms in another order is refused (IF-04).

    Equal atom counts are not enough: with chain A moved after chain B in model
    2, chain B's coordinates would otherwise be read onto chain A's topology.
    """

    def two_models(swap: bool) -> Path:
        structure = gemmi.read_structure(str(CIF))
        structure.remove_ligands_and_waters()
        model = structure[0]
        for name in [chain.name for chain in model]:
            if name not in ("A", "B"):
                model.remove_chain(name)
        second = model.clone()
        second.num = 2
        if swap:
            chain = second["A"].clone()
            second.remove_chain("A")
            second.add_chain(chain)
        structure.add_model(second)
        path = tmp_path / f"models_{swap}.cif"
        structure.make_mmcif_document().write_file(str(path))
        return path

    assert len(load_universe(two_models(swap=False)).trajectory) == 2
    with pytest.raises(StructureInputError, match=r"atom 1 of model 2 is not atom 1 of model 1"):
        load_universe(two_models(swap=True))


@pytest.mark.parametrize(
    ("block", "message"),
    [
        ("point_group: D6", r"point_group 'D6' is not a cyclic point group"),
        ("point_group: C0", r"point_group 'C0' is not a cyclic point group"),
        ("point_group: C1", r"axis is auto and the point group is C1"),
        (
            "chains: 'A,B'",
            r"lists 2 chains \(A, B\), and structure.symmetry.point_group C12 has 12",
        ),
        ("chains: 'A,,B'", r"has an empty entry"),
        ("last_ns: 0", r"last_ns is 0.0; it is a positive time"),
        ("count: 0", r"count is 0; it is at least 1"),
    ],
)
def test_ver48_resolution_refusals(tmp_path: Path, block: str, message: str) -> None:
    """The refusals that need no file are made by ``resolve()``, naming the key (§5.3.1 NOTE)."""
    key, _, value = block.partition(": ")
    options = {
        "point_group": {"point_group": value},
        "chains": {"chains": value.strip("'")},
        "last_ns": {"frames": f"last_ns: {value}"},
        "count": {"frames": f"count: {value}"},
    }[key]
    case = _case(tmp_path, _block(PDB, **options))
    with pytest.raises(CaseValidationError, match=message):
        resolve(load_case(case))


def test_ver48_artefact_round_trip_and_export(prepared: Path, tmp_path: Path) -> None:
    """The ``.npz`` round-trips; the key is stable across processes; a hand edit reads as one.

    The exported PDB and DCD reload through MDAnalysis to the same coordinates.
    """
    case = _case(tmp_path, _block(prepared))
    store = Store(tmp_path / "store")
    result = run_case(case, store=store, upto="structure", write=False)
    artefact = result.artefacts["structure"]
    path = artefact.payload["ensemble"]
    ensemble = AlignedEnsemble.read(path)
    assert ensemble.digest() == artefact.summary["payload_digest"]
    copy = ensemble.write(tmp_path / "copy.npz")
    again = AlignedEnsemble.read(copy)
    assert again.digest() == ensemble.digest()
    assert not artefact.hand_substituted

    script = (
        "from nanopnp.core.stages import create\n"
        "from nanopnp.io.artefact import StageInputs\n"
        "from nanopnp.io.case import load_case\n"
        f"print(create('structure').key(StageInputs(case=load_case({str(case)!r}))).hash)\n"
    )
    other = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=True
    )
    assert other.stdout.strip() == artefact.hash

    # A second run is a cache hit, and a hand edit of the payload is recorded as one.
    assert run_case(case, store=store, upto="structure", write=False).stages[-1].cached
    stored = store.get(artefact.schema, artefact.hash)
    assert stored is not None
    edited = AlignedEnsemble(
        positions_nm=ensemble.positions_nm + np.float32(0.001),
        element=ensemble.element,
        name=ensemble.name,
        resname=ensemble.resname,
        resid=ensemble.resid,
        icode=ensemble.icode,
        chain=ensemble.chain,
        header=ensemble.header,
    )
    edited.write(stored.payload["ensemble"])
    assert store.get(artefact.schema, artefact.hash).hand_substituted  # type: ignore[union-attr]

    pdb, dcd = ensemble.export(tmp_path / "export")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        reloaded = mda.Universe(str(pdb), str(dcd))
    assert len(reloaded.trajectory) == ensemble.frames
    assert np.array_equal(reloaded.atoms.names, ensemble.name)
    assert np.max(np.abs(reloaded.atoms.positions / 10.0 - ensemble.positions_nm[0])) <= 1e-5
    assert json.loads(json.dumps(dict(ensemble.header)))["n"] == 12


def test_ver48_insertion_codes_survive_the_artefact_and_its_export(tmp_path: Path) -> None:
    """Residues 27 and 27A stay two residues through the ``.npz`` and the PDB export (IF-04).

    They share a residue number and differ only in insertion code, so an atom
    table without one would merge them.
    """
    ensemble = AlignedEnsemble(
        positions_nm=np.arange(12, dtype=np.float32).reshape(1, 4, 3),
        element=np.array(["N", "C", "N", "C"]),
        name=np.array(["N", "CA", "N", "CA"]),
        resname=np.array(["GLY", "GLY", "ALA", "ALA"]),
        resid=np.array([27, 27, 27, 27]),
        icode=np.array(["", "", "A", "A"]),
        chain=np.array(["A", "A", "A", "A"]),
        header={"n": 1},
    )
    again = AlignedEnsemble.read(ensemble.write(tmp_path / "icodes.npz"))
    assert again.icode.tolist() == ["", "", "A", "A"]
    assert again.digest() == ensemble.digest()

    pdb, _ = again.export(tmp_path / "export")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        residues = mda.Universe(str(pdb)).residues
    assert [(int(r.resid), str(r.icode).strip(), str(r.resname)) for r in residues] == [
        (27, "", "GLY"),
        (27, "A", "ALA"),
    ]


def test_ver48_rigid_move_superposes_to_zero(prepared: Path, tmp_path: Path) -> None:
    """Frames ``R_k x + t_k`` of the prepared 2WCD superpose on the first to zero RMSD (FR-01)."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        group = mda.Universe(str(prepared)).atoms
    rng = np.random.default_rng(7)
    frames = [group.positions]
    for _ in range(3):
        rotation = _rotation(rng.normal(size=3), rng.uniform(0.2, 2.5))
        frames.append(group.positions @ rotation.T + rng.uniform(-40.0, 40.0, 3))
    dcd = _write(group, np.stack(frames), tmp_path / "moved.dcd")
    case = _case(tmp_path, _block(prepared, trajectory=dcd))
    result = run_case(case, store=Store(tmp_path / "store"), upto="structure", write=False)
    summary = result.artefacts["structure"].summary
    rmsd = summary["superposition"]["rmsd_nm"]
    logger.info("superposition RMSD per frame: %s nm", rmsd)
    assert len(rmsd) == 4
    assert max(rmsd) <= 1e-5
    assert max(summary["drift_deg"]) <= 1e-3


def test_ver48_walk_rules(prepared: Path, tmp_path: Path) -> None:
    """A full walk is refused naming stage 2; ``upto`` must name a stage the case has (IF-02)."""
    case = _case(tmp_path, _block(prepared))
    store = Store(tmp_path / "store")
    with pytest.raises(UnsupportedCaseSection, match=r"Stage 2, the density map \(FR-04\)"):
        run_case(case, store=store, write=False)
    with pytest.raises(UnsupportedCaseSection, match=r"stage 'materials'"):
        run_case(case, store=store, upto="materials", write=False)
    assert run_case(case, store=store, upto="case", write=False).stages[-1].name == "case"
    ran = run_case(case, store=store, upto="structure", write=False)
    assert [record.name for record in ran.stages] == ["case", "structure"]
    assert "structure" in ran.manifest.geometry_and_mesh
    assert set(ran.manifest.inputs["files"]) >= {"structure"}  # type: ignore[arg-type]

    plain = Path(__file__).parents[2] / "examples" / "01-quickstart" / "quickstart.case.yaml"
    with pytest.raises(UnknownStageError, match=r"carries no structure: section"):
        run_case(plain, store=store, upto="structure", write=False)


def test_ver48_a_sweep_over_a_structure_case_is_refused_at_plan_build(
    prepared: Path, tmp_path: Path
) -> None:
    """The walk refusal is the sweep plan builder's too, so no member is dispatched."""
    from nanopnp.sweep.plan import SweepPlanError, plan_from_document

    case = _case(tmp_path, _block(prepared))
    sweep = tmp_path / "sweep.yaml"
    sweep.write_text(
        "schema: nanopnp/sweep/v1\n"
        "name: structure-sweep\n"
        f"base: {case}\n"
        "axes:\n"
        "  - {name: bias, path: boundary_conditions.bias_V, values: [0.05, 0.1]}\n",
        encoding="utf-8",
    )
    with pytest.raises(SweepPlanError, match=r"Stage 2, the density map"):
        plan_from_document(sweep)


def test_ver48_structure_beside_a_supplied_mesh_is_refused(tmp_path: Path) -> None:
    """A supplied mesh means stage 1 never runs, so ``structure:`` beside it is refused."""
    case = _case(tmp_path, _block(PDB, chains=DODECAMER))
    text = case.read_text().replace(
        "structure:\n", "inputs:\n  mesh: {path: pore.msh, format: msh41}\nstructure:\n", 1
    )
    case.write_text(text)
    with pytest.raises(CaseValidationError, match=r"structure: section and supplies inputs.mesh"):
        resolve(load_case(case))


def test_ver48_axis_z_on_the_prepared_copy_is_refused_by_the_budget(
    prepared: Path, tmp_path: Path
) -> None:
    """``axis: z`` on a copy 4 degrees off z is refused, naming the tilt and displacement."""
    case = _case(tmp_path, _block(prepared, axis="z"))
    with pytest.raises(SymmetryGateError, match=r"axis: z displacement gate: .* \(tilt 4\.000"):
        run_case(case, store=Store(tmp_path / "store"), upto="structure", write=False)


def test_ver48_the_stage_is_created_through_the_registry() -> None:
    """``create("structure")`` returns the stage its registry entry describes (VER-25)."""
    stage = create("structure")
    assert stage.describe().name == "structure"
    assert stage.describe().number == 1


def test_ver48_minimal_rotation_is_the_identity_on_z() -> None:
    """The frame rotation of an axis already on z is the identity (D8)."""
    assert np.array_equal(minimal_rotation(np.array([0.0, 0.0, 1.0])), np.eye(3))
