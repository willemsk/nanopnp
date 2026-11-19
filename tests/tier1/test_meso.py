from __future__ import annotations

import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from nanopnp.charge.kernel import volume_density
from nanopnp.density.radii import resolve_protonated_radii, resolve_radii
from nanopnp.gui.geometry import ProfileEditor
from nanopnp.gui.web.molview import first_frame_pdb
from nanopnp.io.case import Density
from nanopnp.plot.data import (
    DensityAtoms,
    ResidueAtoms,
    ResidueCharges,
    ResidueCopies,
    inside_outline,
)
from nanopnp.structure.ensemble import PAYLOAD_NAME as ENSEMBLE_PAYLOAD
from nanopnp.structure.ensemble import AlignedEnsemble
from nanopnp.structure.protonated import ProtonationTable

SHARPNESS = 0.5

# One residue per chain: GLU 12 carries -1 e on OE1, LYS 30 +1 e on NZ; the CA atoms are neutral.
# Each chain's copy sits at its own azimuth and at a slightly different (r, z), so a sum over the
# copies is not a multiple of one copy's value.
_ATOMS = (
    ("GLU", 12, "CA", 0.0, 2.6, 0.8),
    ("GLU", 12, "OE1", -1.0, 3.0, 1.0),
    ("LYS", 30, "CA", 0.0, 4.4, -1.2),
    ("LYS", 30, "NZ", 1.0, 4.0, -1.0),
)
_NUDGE = {0: (0.0, 0.0), 1: (0.05, 0.02), 2: (-0.04, -0.03)}


def _table(
    chains: tuple[str, ...], *, frames: int = 2, header: dict | None = None
) -> ProtonationTable:
    rows = []
    for frame in range(frames):
        for unit, chain in enumerate(chains):
            phi = 2.0 * math.pi * unit / len(chains) + 0.1 * frame
            dr, dz = _NUDGE[unit % 3]
            for resname, resid, name, charge, r, z in _ATOMS:
                rr, zz = r + dr + 0.01 * frame, z + dz - 0.01 * frame
                rows.append(
                    (
                        chain,
                        resid,
                        resname,
                        name,
                        charge,
                        rr * math.cos(phi),
                        rr * math.sin(phi),
                        zz,
                    )
                )
    per_frame = len(rows) // frames
    residues = list(dict.fromkeys((c, resid, resname) for c, resid, resname, *_ in rows))
    return ProtonationTable(
        frame_offsets=np.arange(frames + 1) * per_frame,
        positions_nm=np.array([row[5:] for row in rows], dtype=np.float64),
        charge_e=np.array([row[4] for row in rows], dtype=np.float64),
        radius_nm=np.full(len(rows), 0.15),
        name=np.array([row[3] for row in rows]),
        resname=np.array([row[2] for row in rows]),
        chain=np.array([row[0] for row in rows]),
        resid=np.array([row[1] for row in rows]),
        icode=np.array([""] * len(rows)),
        residue_chain=np.array([c for c, _, _ in residues]),
        residue_resid=np.array([r for _, r, _ in residues]),
        residue_icode=np.array([""] * len(residues)),
        residue_name=np.array([n for _, _, n in residues]),
        residue_charge_e=np.zeros((frames, len(residues))),
        tautomer=np.full((frames, len(residues)), ""),
        expected_charge_e=np.zeros((frames, len(residues))),
        unapplied=np.zeros((frames, len(residues)), dtype=bool),
        group_residue=np.zeros(0, dtype=int),
        group_type=np.zeros(0),
        group_label=np.zeros(0),
        group_pka=np.zeros((frames, 0)),
        header=header or {},
    )


def _structure(units: list[str], n: int, *, payload: dict | None = None) -> SimpleNamespace:
    chains = [c for unit in units for c in unit.split("+")]
    return SimpleNamespace(
        summary={"n": n, "chains_cyclic_order": units, "chains_file_order": chains},
        payload=payload or {},
    )


def _resolved(shift_nm: float = 0.0, **density: object) -> SimpleNamespace:
    return SimpleNamespace(
        name="meso",
        smearing=SimpleNamespace(sharpness=SHARPNESS),
        generates_mesh=shift_nm != 0.0,
        membrane=SimpleNamespace(centre_z_nm=shift_nm),
        density=Density(**density),
    )


def _charges(table: ProtonationTable, structure: SimpleNamespace | None) -> ResidueCharges:
    copies = ResidueCopies.of(structure)  # type: ignore[arg-type]
    return ResidueCharges(table, _resolved(), copies)  # type: ignore[arg-type]


def test_ver60_a_point_names_a_cn_residue_once_its_value_the_copies_sum() -> None:
    table = _table(("A", "B", "C"))
    shift = 0.7
    copies = ResidueCopies.of(_structure(["A", "B", "C"], 3))  # type: ignore[arg-type]
    charges = ResidueCharges(table, _resolved(shift), copies)  # type: ignore[arg-type]
    rows = np.flatnonzero(table.charge_e != 0.0)
    positions = table.positions_nm[rows]
    # The map is in the model frame, stage 1's shifted down by the membrane's centre.
    r_i, z_i = np.hypot(positions[:, 0], positions[:, 1]), positions[:, 2] - shift
    glu = rows[table.resname[rows] == "GLU"]
    for r, z in ((3.0, 1.0 - shift), (3.1, 0.9 - shift)):
        found = dict(charges.at(r, z))
        assert next(key for key, _ in charges.at(r, z)) == "A:12"
        assert set(found) <= {"A:12", "A:30"}
        # The third route: every copy's q / frames times the closed-form kernel, summed by hand.
        expected = sum(
            float(table.charge_e[i])
            / table.frames
            * float(
                volume_density(
                    np.array(r), np.array(z), r_i[rows == i][0], z_i[rows == i][0], SHARPNESS * 0.15
                )
            )
            for i in glu
        )
        assert found["A:12"] == pytest.approx(expected, rel=1e-12)
    assert charges.residues() == [
        ("A:12", "GLU", pytest.approx(-1.0, rel=1e-12), 3),
        ("A:30", "LYS", pytest.approx(1.0, rel=1e-12), 3),
    ]
    assert len(charges.markers("B:12")) == 3 * table.frames
    assert charges.markers("B:12") == charges.markers("A:12")
    assert sorted(z for _, z, _ in charges.markers("A:12")) == pytest.approx(
        sorted(z_i[np.isin(rows, glu)]), abs=1e-12
    )
    # The outlines are in stage 1's frame, and so are the atoms an edit is read against.
    assert np.array_equal(ResidueAtoms(table).z_nm, table.positions_nm[:, 2])
    assert charges.copies("C:12") == ("A:12", "B:12", "C:12")
    assert "C:30" in charges


def test_ver60_under_c1_each_chains_residue_stands_alone() -> None:
    table = _table(("A", "B", "C"))
    for structure in (None, _structure(["A", "B", "C"], 1)):
        charges = _charges(table, structure)
        assert {key for key, *_ in charges.residues()} == {
            f"{c}:{n}" for c in "ABC" for n in (12, 30)
        }
        assert {copies for *_, copies in charges.residues()} == {1}
        assert len(charges.markers("B:12")) == table.frames


def test_ver60_segment_chains_are_named_as_the_pqr_writes_them() -> None:
    chains = ("PROA", "PROB", "PROC")
    letters = {"PROA": "A", "PROB": "B", "PROC": "C"}
    table = _table(chains, header={"chains": letters})
    alone = _charges(table, _structure(list(chains), 1))
    assert {key for key, *_ in alone.residues()} == {f"{c}:{n}" for c in "ABC" for n in (12, 30)}
    together = ResidueCharges(
        table,
        _resolved(),  # type: ignore[arg-type]
        ResidueCopies.of(_structure(list(chains), 3), letters),  # type: ignore[arg-type]
    )
    assert [(key, copies) for key, _, _, copies in together.residues()] == [
        ("A:12", 3),
        ("A:30", 3),
    ]
    # The molecule Mol* reads names the chains by the same characters.
    written = {line[21] for line in first_frame_pdb(table).splitlines() if line.startswith("ATOM")}
    assert written == {"A", "B", "C"}


def test_ver60_hetero_units_group_by_their_position_in_the_unit() -> None:
    copies = ResidueCopies.of(_structure(["A+B", "C+D", "E+F"], 3))  # type: ignore[arg-type]
    assert copies.group("D:7") == "B:7"
    assert copies.copies("E:7") == ("A:7", "C:7", "E:7")
    # Units that number other than n are not read as copies.
    assert ResidueCopies.of(_structure(["A", "B"], 3)).group("B:7") == "B:7"  # type: ignore[arg-type]


_SQUARE = np.array([(1.0, -2.0), (5.0, -2.0), (5.0, 2.0), (1.0, 2.0)])


def _in_triangle(points: np.ndarray, a: tuple, b: tuple, c: tuple) -> np.ndarray:
    def side(p: np.ndarray, q: tuple, r: tuple) -> np.ndarray:
        return (p[:, 0] - r[0]) * (q[1] - r[1]) - (q[0] - r[0]) * (p[:, 1] - r[1])

    d1, d2, d3 = side(points, a, b), side(points, b, c), side(points, c, a)
    return ~(((d1 < 0) | (d2 < 0) | (d3 < 0)) & ((d1 > 0) | (d2 > 0) | (d3 > 0)))


def _scattered(count: int) -> ProtonationTable:
    rng = np.random.default_rng(7)
    r = rng.uniform(0.0, 8.0, count)
    z = rng.uniform(-3.0, 3.0, count)
    phi = rng.uniform(0.0, 2.0 * math.pi, count)
    table = _table(("A",), frames=1)
    names = np.array([f"C{i % 9}" for i in range(count)])
    return ProtonationTable(
        **{
            **{key: getattr(table, key) for key in ProtonationTable.ARRAYS},
            "frame_offsets": np.array([0, count]),
            "positions_nm": np.column_stack([r * np.cos(phi), r * np.sin(phi), z]),
            "charge_e": rng.choice([-0.5, 0.25], count),
            "radius_nm": np.full(count, 0.15),
            "name": names,
            "resname": np.array(["ALA"] * count),
            "chain": np.array(["A"] * count),
            "resid": np.arange(count) // 4,
            "icode": np.array([""] * count),
        },
        header={},
    )


def test_ver60_an_edit_moves_exactly_the_atoms_its_cut_holds_each_way() -> None:
    table = _scattered(4000)
    atoms = ResidueAtoms(table)
    points = np.column_stack([atoms.r_nm, atoms.z_nm])
    key = np.array([f"A:{n}" for n in table.resid.tolist()])

    def tally(moved: dict) -> tuple[dict, dict]:
        return (
            {k: c.atoms for k, c in moved.items()},
            {k: c.charge_e for k, c in moved.items()},
        )

    def expected(mask: np.ndarray) -> tuple:
        atoms_k: dict[str, float] = {}
        charge_k: dict[str, float] = {}
        for k, q in zip(key[mask].tolist(), table.charge_e[mask].tolist(), strict=True):
            atoms_k[k] = atoms_k.get(k, 0.0) + 1.0
            charge_k[k] = charge_k.get(k, 0.0) + q
        return pytest.approx(atoms_k, rel=1e-12), pytest.approx(charge_k, rel=1e-12)

    inward = _SQUARE.copy()
    inward[2] = (3.0, 2.0)
    cut = _in_triangle(points, (5.0, -2.0), (5.0, 2.0), (3.0, 2.0))
    assert cut.any()
    moved = atoms.moved(_SQUARE, inward)
    assert tally(moved.out) == expected(cut)
    assert moved.in_ == {}

    outward = _SQUARE.copy()
    outward[2] = (7.0, 2.0)
    added = _in_triangle(points, (5.0, -2.0), (7.0, 2.0), (5.0, 2.0))
    assert added.any()
    moved = atoms.moved(_SQUARE, outward)
    assert moved.out == {}
    assert tally(moved.in_) == expected(added)

    assert atoms.moved(_SQUARE, _SQUARE.copy()) == type(moved)({}, {})

    editor = ProfileEditor.from_seed([tuple(v) for v in _SQUARE], digest="0" * 64, name="seed")
    editor.move(2, 3.0, 2.0)
    assert np.array_equal(np.array(editor.start), _SQUARE)
    assert tally(atoms.moved(np.array(editor.start), np.array(editor.vertices)).out) == (
        expected(cut)
    )


def test_ver60_moved_atoms_count_per_copy_and_per_frame() -> None:
    table = _table(("A", "B", "C"))
    atoms = ResidueAtoms(table, ResidueCopies.of(_structure(["A", "B", "C"], 3)))  # type: ignore[arg-type]
    # A cut holding every GLU atom and no LYS atom: two atoms of -1 e per copy and per frame.
    before = np.array([(0.0, -5.0), (10.0, -5.0), (10.0, 5.0), (0.0, 5.0)])
    after = np.array([(0.0, -5.0), (10.0, -5.0), (10.0, 0.0), (0.0, 0.0)])
    moved = atoms.moved(before, after)
    assert set(moved.out) == {"A:12"}
    assert moved.out["A:12"].atoms == pytest.approx(2.0, rel=1e-12)
    assert moved.out["A:12"].charge_e == pytest.approx(-1.0, rel=1e-12)
    assert len(atoms.markers("C:12")) == 2 * 3 * table.frames


def test_ver60_inside_outline_is_the_solid_fractions_even_odd_test() -> None:
    from nanopnp.charge.dielectric import _inside

    loop = np.array([(1.0, -2.0), (5.0, -2.0), (3.0, 0.5), (5.0, 2.0), (1.0, 2.0)])
    r = np.linspace(0.0, 6.0, 61)
    z = np.linspace(-3.0, 3.0, 61)
    rr, zz = np.meshgrid(r, z)
    assert np.array_equal(
        inside_outline(loop, rr.ravel(), zz.ravel()).reshape(rr.shape), _inside(loop, r, z)
    )


DENSITY_SHARPNESS = 0.8


def _density_atoms(tmp_path: Path, mode: str) -> tuple[DensityAtoms, ProtonationTable]:
    table = _table(("A", "B", "C"), frames=2)
    first = table.frame_slice(0)
    ensemble = AlignedEnsemble(
        positions_nm=table.positions_nm.reshape(table.frames, -1, 3).astype(np.float32),
        element=np.array([str(n)[0] for n in table.name[first]]),
        name=table.name[first],
        resname=table.resname[first],
        resid=table.resid[first],
        icode=table.icode[first],
        chain=table.chain[first],
        header={},
    )
    path = ensemble.write(tmp_path / "ensemble.npz")
    protonation = tmp_path / "table.npz"
    table.write(protonation)
    structure = _structure(["A", "B", "C"], 1, payload={ENSEMBLE_PAYLOAD: path})
    return (
        DensityAtoms.of(
            _resolved(atoms=mode, sharpness=DENSITY_SHARPNESS),  # type: ignore[arg-type]
            structure,  # type: ignore[arg-type]
            SimpleNamespace(payload={"protonation": protonation}),  # type: ignore[arg-type]
        ),
        table,
    )


@pytest.mark.parametrize("mode", ["protonated", "as_loaded"])
def test_ver60_a_point_on_an_atom_ranks_its_residue_first(tmp_path: Path, mode: str) -> None:
    atoms, table = _density_atoms(tmp_path, mode)
    # Stage 2's widths: geometry.density.sharpness times the CHARMM radii, as density/stage.py
    # takes them, and not the charge's sharpness times the PQR radii.
    if mode == "protonated":
        radii = resolve_protonated_radii("pdb2pqr_charmm", table).radii_nm
    else:
        first = table.frame_slice(0)
        radii = np.tile(
            resolve_radii(
                "pdb2pqr_charmm",
                resname=table.resname[first],
                atom=table.name[first],
                chain=table.chain[first],
                resid=table.resid[first],
                icode=table.icode[first],
            ).radii_nm,
            table.frames,
        )
    assert np.array_equal(atoms.width_nm, DENSITY_SHARPNESS * radii)
    assert not np.allclose(atoms.width_nm, SHARPNESS * table.radius_nm)
    positions = table.positions_nm
    for i in range(len(positions)):
        r, z = float(np.hypot(*positions[i, :2])), float(positions[i, 2])
        key, distance = atoms.nearest(r, z)[0]
        assert key == f"{table.chain[i]}:{table.resid[i]}"
        # Stage 1 stores its positions in float32.
        assert distance < 1e-5
