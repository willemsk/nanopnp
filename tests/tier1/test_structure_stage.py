"""VER-48: stage 1 on real files: readers, refusals, frames, the artefact and the walk."""

from __future__ import annotations

import dataclasses
import json
import logging
import math
import subprocess
import sys
import warnings
from pathlib import Path
from typing import TYPE_CHECKING

import MDAnalysis as mda  # noqa: N813 - the alias the library documents
import numpy as np
import pytest
from MDAnalysis.coordinates.memory import MemoryReader

from nanopnp import Case, Session
from nanopnp.io.artefact import CASE_SCHEMA
from nanopnp.io.case import CaseValidationError
from nanopnp.io.store import Store
from nanopnp.pipeline.case import (
    load_case,
    resolve,
)
from nanopnp.pipeline.run import UnknownStageError, selected_stages
from nanopnp.structure.axis import SymmetryGateError, measure_axis, minimal_rotation
from nanopnp.structure.ensemble import AlignedEnsemble
from nanopnp.structure.read import (
    StructureInputError,
    check_chains_whole,
    frame_times,
    load_universe,
    positions_nm,
    select,
    select_frames,
)

if TYPE_CHECKING:
    from conftest import Prepared2WCD

logger = logging.getLogger(__name__)

STRUCTURES = Path(__file__).parents[1] / "data" / "structures"
PDB = STRUCTURES / "2wcd.pdb.gz"
CIF = STRUCTURES / "2wcd.cif.gz"
DODECAMER = "A,B,C,D,E,F,G,H,I,J,K,L"


def _case(tmp_path: Path, structure: str, *, name: str = "structure") -> Path:
    text = (
        f"schema: {CASE_SCHEMA}\n"
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
    variant: str | None = None,
) -> str:
    label = "" if variant is None else f", variant: '{variant}'"
    lines = [
        f"  source: {{path: {path}, chains: '{chains}', selection: '{selection}'{label}}}\n",
        f"  symmetry: {{point_group: {point_group}, axis: {axis}}}\n",
    ]
    if trajectory is not None or frames:
        ensemble = [f"trajectory: {trajectory}"] if trajectory is not None else []
        if frames:
            ensemble.append(f"frames: {{{frames}}}")
        lines.append(f"  ensemble: {{{', '.join(ensemble)}}}\n")
    return "".join(lines)


def _rotation(axis: np.ndarray, angle: float) -> np.ndarray:
    k = np.asarray(axis, dtype=np.float64) / np.linalg.norm(axis)
    skew = np.array([[0.0, -k[2], k[1]], [k[2], 0.0, -k[0]], [-k[1], k[0], 0.0]])
    return np.eye(3) + math.sin(angle) * skew + (1.0 - math.cos(angle)) * (skew @ skew)


def _write(group: mda.AtomGroup, frames_angstrom: np.ndarray, path: Path) -> Path:
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


@pytest.fixture(scope="module")
def prepared(prepared_2wcd: Prepared2WCD) -> Path:
    return prepared_2wcd.path


def _run(case: Path, store: Path) -> AlignedEnsemble:
    result = Session(Store(store), write=False).run(Case.load(case), upto="structure")
    artefact = result.artefacts["structure"]
    return AlignedEnsemble.read(artefact.payload["ensemble"])


def test_ver48_relabelling_the_variant_is_a_cache_hit_and_the_manifest_keeps_the_label(
    prepared: Path, tmp_path: Path
) -> None:
    store = Store(tmp_path / "store")
    first = Session(store, write=False).run(
        Case.load(_case(tmp_path, _block(prepared, variant="ClyA-AS"), name="first")),
        upto="structure",
    )
    second = Session(store, write=False).run(
        Case.load(_case(tmp_path, _block(prepared, variant="ClyA-AS-relabelled"), name="second")),
        upto="structure",
    )
    assert not first.stages[-1].cached
    assert second.stages[-1].cached
    assert first.artefacts["structure"].hash == second.artefacts["structure"].hash
    assert "variant" not in first.artefacts["structure"].summary
    assert "variant: 'ClyA-AS'" in first.manifest.case_text
    assert "variant: 'ClyA-AS-relabelled'" in second.manifest.case_text


def test_ver48_the_deposited_2wcd_frame_is_refused_by_the_orientation_gate(
    tmp_path: Path,
) -> None:
    case = _case(tmp_path, _block(PDB, chains=DODECAMER))
    with pytest.raises(SymmetryGateError, match=r"orientation gate: the detected axis is 22\.9"):
        Session(Store(tmp_path / "store"), write=False).run(Case.load(case), upto="structure")


def test_ver48_2wcd_runs_as_stage_one(
    prepared: Path, prepared_2wcd: Prepared2WCD, tmp_path: Path
) -> None:
    case = _case(tmp_path, _block(prepared))
    result = Session(Store(tmp_path / "store"), write=False).run(Case.load(case), upto="structure")
    artefact = result.artefacts["structure"]
    summary = artefact.summary
    ensemble = AlignedEnsemble.read(artefact.payload["ensemble"])

    assert summary["n"] == 12
    assert summary["chain_key"] == "chainID"
    assert summary["common_ca"] == 285
    assert summary["chains_cyclic_order"][0] == "A"
    record = summary["axis"]["file_frame"]
    assert abs(record["tilt_deg"] - prepared_2wcd.tilt_deg) <= 1e-6
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
    first = ensemble.positions_nm[0].astype(np.float64)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        source = mda.Universe(str(prepared)).select_atoms("protein").positions / 10.0
    axis = np.asarray(record["axis"])
    assert np.max(np.abs(first[:, 2] - source @ axis)) <= 2e-5


def test_ver48_2wcd_pdb_and_mmcif_agree() -> None:
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
def two_chains(
    dodecamer_2wcd: mda.AtomGroup, tmp_path_factory: pytest.TempPathFactory
) -> tuple[Path, np.ndarray]:
    group = dodecamer_2wcd.select_atoms("chainID A B")
    rng = np.random.default_rng(3)
    frames = np.stack(
        [group.positions + rng.normal(0.0, 0.5, group.positions.shape) for _ in range(3)]
    )
    directory = tmp_path_factory.mktemp("formats")
    return _write(group, frames, directory / "ab.pdb"), frames


@pytest.mark.parametrize(
    ("suffix", "tolerance_nm"),
    # DCD and NetCDF are exact; TRR and XTC round as recorded in
    # knowledge/07-software-stack/index.md (trajectory formats).
    [(".dcd", 0.0), (".xtc", 5e-4 + 3.1e-6), (".trr", 3.1e-6), (".nc", 0.0), (".ncdf", 0.0)],
)
def test_ver48_each_trajectory_format_reads(
    two_chains: tuple[Path, np.ndarray], suffix: str, tolerance_nm: float, tmp_path: Path
) -> None:
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
    assert 2.0 * math.ldexp(1.0, -23) * 13.0 == pytest.approx(3.1e-6, abs=1e-8)


def test_ver48_frame_selection_and_the_time_gate(
    two_chains: tuple[Path, np.ndarray], tmp_path: Path
) -> None:
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


@pytest.mark.parametrize("dt_ps", [0.5, 1.0, 2.0, 2.5, 10.0, 20.0])
def test_ver48_the_last_ns_window_does_not_depend_on_the_float32_timestep(
    dt_ps: float, tmp_path: Path
) -> None:
    frames = 1001
    universe = mda.Universe.empty(4, trajectory=True)
    universe.load_new(
        np.random.default_rng(0).random((frames, 4, 3)).astype(np.float32), format=MemoryReader
    )
    topology, trajectory = tmp_path / "t.pdb", tmp_path / "t.dcd"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        universe.atoms.write(str(topology))
        with mda.Writer(str(trajectory), 4, dt=dt_ps) as writer:
            for step in universe.trajectory:
                step.dt = dt_ps
                writer.write(universe.atoms)
        read = load_universe(topology, trajectory)
    times, interval = frame_times(read)
    span_ns = (frames - 1) * dt_ps / 1000.0
    for fraction in (0.1, 0.25, 0.5):
        window = select_frames(times, interval, last_ns=span_ns * fraction)
        assert len(window.indices) == round((frames - 1) * fraction) + 1


def test_ver48_artefact_round_trip_and_export(prepared: Path, tmp_path: Path) -> None:
    case = _case(tmp_path, _block(prepared))
    store = Store(tmp_path / "store")
    result = Session(store, write=False).run(Case.load(case), upto="structure")
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
        "from nanopnp.pipeline.case import load_case, resolve\n"
        f"print(create('structure').key(StageInputs(resolved=resolve(load_case({str(case)!r})))).hash)\n"
    )
    other = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=True
    )
    assert other.stdout.strip() == artefact.hash

    assert Session(store, write=False).run(Case.load(case), upto="structure").stages[-1].cached
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


@pytest.mark.parametrize(
    "chains",
    [["PROA", "PROA", "PROB", "PROB"], ["AA", "AA", "BB", "BB", "C", "C"]],
    ids=["segids", "mixed-length"],
)
def test_ver48_an_export_keeps_chains_distinct_whatever_their_keys(
    chains: list[str], tmp_path: Path
) -> None:
    atoms = len(chains)
    ensemble = AlignedEnsemble(
        positions_nm=np.random.default_rng(1).random((2, atoms, 3)).astype(np.float32),
        element=np.array(["C"] * atoms),
        name=np.array(["CA"] * atoms),
        resname=np.array(["ALA"] * atoms),
        resid=np.array([1, 2] * (atoms // 2)),
        icode=np.array([""] * atoms),
        chain=np.array(chains),
        header={},
    )
    pdb, _ = ensemble.export(tmp_path, stem="x")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        written = mda.Universe(str(pdb)).atoms
    ids = [str(value) for value in written.chainIDs]
    assert len(set(ids)) == len(set(chains)), ids
    assert [ids[i] == ids[0] for i in range(atoms)] == [chain == chains[0] for chain in chains]
    if chains[0] == "PROA":
        assert [str(value) for value in written.segids] == chains
    letters = ["A", "A", "B", "B", "C", "C"][:atoms]
    plain = dataclasses.replace(ensemble, chain=np.array(letters))
    pdb_plain, _ = plain.export(tmp_path, stem="plain")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        assert [str(v) for v in mda.Universe(str(pdb_plain)).atoms.chainIDs] == letters


def test_ver48_insertion_codes_survive_the_artefact_and_its_export(tmp_path: Path) -> None:
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


# FR-01
def test_ver48_rigid_move_superposes_to_zero(prepared: Path, tmp_path: Path) -> None:
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
    result = Session(Store(tmp_path / "store"), write=False).run(Case.load(case), upto="structure")
    summary = result.artefacts["structure"].summary
    rmsd = summary["superposition"]["rmsd_nm"]
    logger.info("superposition RMSD per frame: %s nm", rmsd)
    assert len(rmsd) == 4
    assert max(rmsd) <= 1e-5
    assert max(summary["drift_deg"]) <= 1e-3


def test_ver48_walk_rules(prepared: Path, tmp_path: Path) -> None:
    case = _case(tmp_path, _block(prepared))
    store = Store(tmp_path / "store")
    assert "region" in selected_stages(resolve(load_case(case)), None)
    assert selected_stages(resolve(load_case(case)), "solve")[-6:] == (
        "region",
        "mesh",
        "protonation",
        "charge",
        "materials",
        "solve",
    )
    assert Session(store, write=False).run(Case.load(case), upto="case").stages[-1].name == "case"
    ran = Session(store, write=False).run(Case.load(case), upto="structure")
    assert [record.name for record in ran.stages] == ["case", "structure"]
    assert "structure" in ran.manifest.geometry_and_mesh
    assert set(ran.manifest.inputs["files"]) >= {"structure"}  # type: ignore[arg-type]

    plain = Path(__file__).parents[2] / "examples" / "01-quickstart" / "quickstart.case.yaml"
    with pytest.raises(UnknownStageError, match=r"carries no structure: section"):
        Session(store, write=False).run(Case.load(plain), upto="structure")


def test_ver48_a_sweep_over_a_structure_case_plans(prepared: Path, tmp_path: Path) -> None:
    from nanopnp.sweep.plan import plan_from_document

    case = _case(tmp_path, _block(prepared))
    sweep = tmp_path / "sweep.yaml"
    sweep.write_text(
        "schema: nanopnp/sweep/v0.5\n"
        "name: structure-sweep\n"
        f"base: {case}\n"
        "axes:\n"
        "  - {name: bias, path: boundary_conditions.bias_V, values: [0.05, 0.1]}\n",
        encoding="utf-8",
    )
    plan = plan_from_document(sweep)
    assert len(plan.points) == 2
    assert plan.warnings == ()


def test_ver48_axis_z_on_the_prepared_copy_is_refused_by_the_budget(
    prepared: Path, tmp_path: Path
) -> None:
    case = _case(tmp_path, _block(prepared, axis="z"))
    with pytest.raises(SymmetryGateError, match=r"axis: z displacement gate: .* \(tilt 4\.000"):
        Session(Store(tmp_path / "store"), write=False).run(Case.load(case), upto="structure")


def test_ver48_minimal_rotation_is_the_identity_on_z() -> None:
    assert np.array_equal(minimal_rotation(np.array([0.0, 0.0, 1.0])), np.eye(3))


# QR-12
def test_ver48_a_chain_wrapped_across_the_box_in_one_frame_is_refused(
    two_chains: tuple[Path, np.ndarray], tmp_path: Path
) -> None:
    topology, frames = two_chains
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        group = mda.Universe(str(topology)).atoms
    universe = load_universe(topology, _write(group, frames, tmp_path / "whole.dcd"))
    chosen = select(universe, selection="protein", chains="all", n=2)
    whole = positions_nm(chosen.group, range(3))
    check_chains_whole(chosen, whole, range(3))

    moved = frames.copy()
    pair_start = int(chosen.fit_index[10])
    moved[2, pair_start:] += np.array([0.0, 0.0, 100.0])
    dcd = _write(group, moved, tmp_path / "wrapped.dcd")
    wrapped = load_universe(topology, dcd)
    chosen = select(wrapped, selection="protein", chains="all", n=2)
    with pytest.raises(
        StructureInputError,
        match=r"chain A is split .* in frame 2: .* residues 17 and 18 lie 9\.\d{3} nm",
    ):
        check_chains_whole(chosen, positions_nm(chosen.group, range(3)), range(3))


# QR-12
def test_ver48_a_pair_across_an_inserted_residue_is_not_a_bonded_pair(
    two_chains: tuple[Path, np.ndarray],
) -> None:
    topology, _ = two_chains
    chosen = select(load_universe(topology), selection="protein", chains="all", n=2)
    positions = positions_nm(chosen.group, [0])
    positions[0, int(chosen.fit_index[10]) :] += np.array([0.0, 0.0, 10.0])
    with pytest.raises(StructureInputError, match="residues 17 and 18 lie"):
        check_chains_whole(chosen, positions, [0])

    resid, icode = chosen.atoms.resid.copy(), chosen.atoms.icode.copy()
    resid[chosen.fit_index[20]], icode[chosen.fit_index[20]] = 17, "A"
    inserted = dataclasses.replace(
        chosen, atoms=dataclasses.replace(chosen.atoms, resid=resid, icode=icode)
    )
    check_chains_whole(inserted, positions, [0])


# QR-12
def test_ver48_a_selection_without_consecutive_residues_has_nothing_to_check(
    two_chains: tuple[Path, np.ndarray],
) -> None:
    topology, _ = two_chains
    chosen = select(load_universe(topology), selection="protein", chains="all", n=2)
    lone = dataclasses.replace(chosen, fit_index=chosen.fit_index[:1])
    check_chains_whole(lone, positions_nm(chosen.group, [0]), [0])


# QR-12
def test_ver48_the_deposited_2wcd_has_no_pair_near_the_wrap_bound() -> None:
    universe = load_universe(PDB)
    chosen = select(universe, selection="protein", chains=DODECAMER, n=12)
    positions = positions_nm(chosen.group, [0])
    check_chains_whole(chosen, positions, [0])
    carbons = {
        (str(chosen.atoms.chain[i]), int(chosen.atoms.resid[i])): int(i)
        for i in chosen.fit_index
        if not str(chosen.atoms.icode[i])
    }
    gaps = [
        float(
            np.linalg.norm(positions[0, carbons[key]] - positions[0, carbons[key[0], key[1] + 1]])
        )
        for key in carbons
        if (key[0], key[1] + 1) in carbons
    ]
    assert len(gaps) == 3408
    assert max(gaps) == pytest.approx(0.3856, abs=1e-4)


def test_ver48_a_dcd_reports_its_frame_times_without_decoding_a_frame(
    two_chains: tuple[Path, np.ndarray], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    topology, frames = two_chains
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        group = mda.Universe(str(topology)).atoms
        path = tmp_path / "timed.dcd"
        merged = mda.Merge(group)
        merged.load_new(np.asarray(frames, dtype=np.float32), format=MemoryReader)
        with mda.Writer(str(path), merged.atoms.n_atoms, dt=2.5, istart=2, nsavc=2) as writer:
            for step in merged.trajectory:
                step.dt = 2.5
                writer.write(merged.atoms)
        universe = load_universe(topology, path)
        decoded = tuple(float(step.time) * 1e-3 for step in universe.trajectory)

    def refuse(*args: object, **kwargs: object) -> None:
        raise AssertionError("a frame was decoded")

    reader = type(universe.trajectory)
    for name in ("_read_next_timestep", "_read_frame", "_read_frame_with_aux"):
        monkeypatch.setattr(reader, name, refuse)
    times, interval = frame_times(universe)

    assert times == decoded
    assert interval == pytest.approx(2.5e-3)


def test_ver48_a_dcd_reader_without_its_header_is_decoded_for_its_frame_times(
    two_chains: tuple[Path, np.ndarray], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    topology, frames = two_chains
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        group = mda.Universe(str(topology)).atoms
        dcd = _write(group, frames, tmp_path / "plain.dcd")
        universe = load_universe(topology, dcd)
        decoded = tuple(float(step.time) * 1e-3 for step in universe.trajectory)
        real = universe.trajectory._file

        class Headerless:
            asked = False

            def __getattr__(self, name: str) -> object:
                # Only the first read fails: the reader decodes frames through the same header.
                if name == "header" and not self.asked:
                    self.asked = True
                    raise AttributeError(name)
                return getattr(real, name)

            def __len__(self) -> int:
                return len(real)

        monkeypatch.setattr(universe.trajectory, "_file", Headerless())
        times, _ = frame_times(universe)

    assert times == decoded


def test_ver48_structure_beside_a_supplied_mesh_is_refused(tmp_path: Path) -> None:
    case = _case(tmp_path, _block(PDB, chains=DODECAMER))
    text = case.read_text().replace(
        "structure:\n", "inputs:\n  mesh: {path: pore.msh, format: msh41}\nstructure:\n", 1
    )
    case.write_text(text)
    with pytest.raises(CaseValidationError, match=r"structure: section and supplies inputs.mesh"):
        resolve(load_case(case))
