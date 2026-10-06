"""VER-57, FR-12, QR-12: the protonation stage on fragments of 2WCD chain A (WP27).

Each fragment is a few residues cut from the vendored 2WCD and handed to the
stage as a stage-1 ensemble, so PDB2PQR and PROPKA run in about 0.1 s a frame.
The oracles are independent of the code under test: the charges are checked
against ``CHARMM.DAT`` parsed here from the installed package, ``Q_net`` against a
hand count of the standard states, and the states PROPKA changes against
``.knowledge/07`` section 3's measurements on the same fragment.

The gates are driven with a stand-in for :func:`run_pdb2pqr` that writes a chosen
PQR, so each D9 gate is shown to fire, naming its frame, on exactly the defect
it guards.
"""

from __future__ import annotations

import dataclasses
import sys
from collections.abc import Callable
from importlib import resources
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from nanopnp.charge.pqr import (
    PQRError,
    PQRFrame,
    is_hydrogen,
    parent_residue,
    read_pqr,
    write_pqr,
)
from nanopnp.charge.protonation import (
    ProtonationError,
    ProtonationStage,
    ProtonationTable,
    export_pqr,
    frame_pdb,
    pdb2pqr_arguments,
)
from nanopnp.core.stages import CancelFlag, Cancelled, MissingExtraError
from nanopnp.io.artefact import StageInputs, StructureArtefact
from nanopnp.io.case import (
    CaseDocument,
    CaseValidationError,
    UnsupportedCaseSection,
)
from nanopnp.io.resolved import ResolvedProtonation
from nanopnp.io.store import Store
from nanopnp.pipeline.case import loads_case, resolve
from nanopnp.structure.ensemble import AlignedEnsemble

pytest.importorskip("pdb2pqr", reason="the structure extra carries PDB2PQR")

Fragment = Callable[..., AlignedEnsemble]

FRAGMENT = (18, 26)
"""``GLU 18`` to ``LEU 26`` of chain A: three acids and both termini (``.knowledge/07`` §3)."""

HISTIDINE = (285, 292)
"""``CYS 285`` to ``HIS 292``, the C-terminal histidine of chain A."""

CASE = """\
schema: nanopnp/case/v2
name: {name}
{inputs}{structure}{charge}electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.15
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: epnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
"""


def _case(
    tmp_path: Path,
    *,
    charge: str = "",
    pqr: Path | None = None,
    structure: bool = True,
    mesh: bool = False,
) -> CaseDocument:
    """Return a case naming a fragment's structure, and optionally a supplied PQR."""
    inputs = ""
    if pqr is not None or mesh:
        inputs = "inputs:\n"
        if pqr is not None:
            inputs += f"  pqr: {{path: {pqr}, format: pqr}}\n"
        if mesh:
            inputs += "  mesh: {path: pore.msh, format: msh41}\n"
    block = (
        f"structure:\n  source: {{path: {tmp_path / 'fragment.pdb'}}}\n"
        "  symmetry: {point_group: C1, axis: z}\n"
        if structure
        else ""
    )
    return loads_case(
        CASE.format(
            name="fragment",
            inputs=inputs,
            structure=block,
            charge=f"charge: {{{charge}}}\n" if charge else "",
        )
    )


def _inputs(tmp_path: Path, ensemble: AlignedEnsemble, case: CaseDocument) -> StageInputs:
    """Return stage inputs carrying ``ensemble`` as stage 1's artefact.

    The structure artefact is keyed on the ensemble's digest, so two ensembles
    are two inputs, as two stage-1 runs would be.
    """
    path = ensemble.write(tmp_path / f"ensemble-{ensemble.digest()[:12]}.npz")
    structure = StructureArtefact(
        parameters={"ensemble": ensemble.digest()}, payload={"ensemble": path}
    )
    return StageInputs(resolved=resolve(case), upstream={"structure": structure})


def _run(
    tmp_path: Path,
    ensemble: AlignedEnsemble,
    *,
    charge: str = "",
    store: Store | None = None,
) -> tuple[ProtonationTable, dict[str, Any]]:
    """Protonate ``ensemble`` through the stage API; return the table and the summary."""
    stage = ProtonationStage(workspace=tmp_path / "workspace", store=store)
    artefact = stage.run(_inputs(tmp_path, ensemble, _case(tmp_path, charge=charge)))
    return ProtonationTable.read(artefact.payload["protonation"]), dict(artefact.summary)


def _charmm() -> dict[str, dict[str, float]]:
    """Return ``CHARMM.DAT``'s charges by residue and atom, parsed here from the installed file.

    Independent of PDB2PQR's own parser: whitespace columns, residue, atom,
    charge, radius, type; ``#`` starts a comment.
    """
    text = (resources.files("pdb2pqr") / "dat" / "CHARMM.DAT").read_text(encoding="utf-8")
    table: dict[str, dict[str, float]] = {}
    for line in text.splitlines():
        fields = line.split("#", 1)[0].split()
        if len(fields) >= 4:
            table.setdefault(fields[0], {})[fields[1]] = float(fields[2])
    return table


def _residues(table: ProtonationTable) -> dict[str, float]:
    """Return frame 0's charge by residue label, ``GLU 18``, variants as their parent."""
    return {
        f"{parent_residue(name)} {resid}": float(charge)
        for name, resid, charge in zip(
            table.residue_name.tolist(),
            table.residue_resid.tolist(),
            table.residue_charge_e[0],
            strict=True,
        )
    }


# -- the force field's own charges -------------------------------------------


@pytest.mark.parametrize("charge", ["titration: none", "ph: 8.0"])
def test_ver57_charges_are_charmm_dat_and_q_net_the_hand_count(
    tmp_path: Path, fragment_2wcd: Fragment, charge: str
) -> None:
    """Every atom's charge is ``CHARMM.DAT``'s to 10⁻⁶ e; ``Q_net`` is -3 e by hand.

    Standard states, which PROPKA at pH 8 also gives: ``GLU 18`` with the
    N-terminal patch is 0, ``ASP 21`` and ``ASP 25`` are -1 each, and ``LEU 26``
    with the C-terminal patch is -1. A ``TER`` atom is looked up in the patches.
    """
    table, summary = _run(tmp_path, fragment_2wcd(*FRAGMENT), charge=charge)
    charmm = _charmm()
    (frame,) = table.pqr_frames()
    pqr = read_pqr(tmp_path / "workspace" / next(iter(_frame_pqrs(tmp_path))))[0]
    for name, resname, written, value in zip(
        pqr.name.tolist(), pqr.resname.tolist(), _written_names(tmp_path), pqr.charge_e, strict=True
    ):
        sources = ("NTER", "CTER") if written == "TER" else (resname,)
        expected = [charmm[source][name] for source in sources if name in charmm[source]]
        assert expected, f"{resname} {name} is in no CHARMM.DAT entry"
        assert abs(value - expected[0]) <= 1e-6, f"{resname} {name}"
    np.testing.assert_array_equal(frame.charge_e, pqr.charge_e)
    assert table.q_net_e() == pytest.approx([-3.0], abs=1e-9)
    assert summary["q_net_e"] == [-3.0]
    assert _residues(table) == pytest.approx(
        {
            "GLU 18": 0.0,
            "THR 19": 0.0,
            "ALA 20": 0.0,
            "ASP 21": -1.0,
            "GLY 22": 0.0,
            "ALA 23": 0.0,
            "LEU 24": 0.0,
            "ASP 25": -1.0,
            "LEU 26": -1.0,
        },
        abs=1e-6,
    )


def _frame_pqrs(tmp_path: Path) -> list[str]:
    """Return the frame PQRs PDB2PQR wrote under the workspace, relative to it."""
    root = tmp_path / "workspace"
    return sorted(str(path.relative_to(root)) for path in root.rglob("frame.pqr"))


def _written_names(tmp_path: Path) -> list[str]:
    """Return the residue names PDB2PQR wrote in the first frame PQR, ``TER`` included."""
    path = tmp_path / "workspace" / _frame_pqrs(tmp_path)[0]
    return [
        line[17:21].strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("ATOM")
    ]


def test_ver57_without_titration_the_ph_reaches_nothing(
    tmp_path: Path, fragment_2wcd: Fragment
) -> None:
    """``titration: none`` at pH 3 and pH 9 passes the same flags and gives the same charges.

    The case refuses a pH beside ``none`` (the section 5.3.1 NOTE), so the two
    are driven through the driver directly: neither ``--with-ph`` nor
    ``--titration-state-method`` reaches PDB2PQR.
    """
    from nanopnp.charge.pqr import chain_characters
    from nanopnp.charge.protonation import run_pdb2pqr

    low = ResolvedProtonation(ph=3.0, titration="none")
    high = ResolvedProtonation(ph=9.0, titration="none")
    assert pdb2pqr_arguments(low) == pdb2pqr_arguments(high)
    assert not any("ph" in flag or "titration" in flag for flag in pdb2pqr_arguments(low))
    ensemble = fragment_2wcd(*FRAGMENT)
    heavy = np.flatnonzero(ensemble.element != "H")
    pdb = tmp_path / "fragment.pdb"
    pdb.write_bytes(frame_pdb(ensemble, 0, heavy, chain_characters(ensemble.chain.tolist())))
    charges = []
    for settings, name in ((low, "low.pqr"), (high, "high.pqr")):
        run_pdb2pqr(pdb, tmp_path / name, settings)
        charges.append(read_pqr(tmp_path / name)[0].charge_e)
    np.testing.assert_array_equal(charges[0], charges[1])


def test_ver57_propka_across_a_pka_changes_exactly_the_acids(
    tmp_path: Path, fragment_2wcd: Fragment
) -> None:
    """At pH 2 ``GLU 18``, ``ASP 21`` and ``ASP 25`` are neutral; at pH 8 they are charged.

    ``.knowledge/07`` section 3: the fragment is +0 e at pH 2 and -3 e at pH 8.
    No other residue's charge moves, and the C terminus, which CHARMM cannot
    hold neutral, stays -1 and is recorded as unapplied at pH 2.
    """
    acid, _ = _run(tmp_path / "acid", fragment_2wcd(*FRAGMENT), charge="ph: 2.0")
    basic, _ = _run(tmp_path / "basic", fragment_2wcd(*FRAGMENT), charge="ph: 8.0")
    low, high = _residues(acid), _residues(basic)
    changed = sorted(label for label in low if abs(low[label] - high[label]) > 1e-6)
    assert changed == ["ASP 21", "ASP 25", "GLU 18"]
    assert acid.q_net_e() == pytest.approx([0.0], abs=1e-9)
    assert basic.q_net_e() == pytest.approx([-3.0], abs=1e-9)
    column = acid.residue_resid.tolist().index(26)
    assert bool(acid.unapplied[0, column]) == (acid.expected_charge_e[0, column] == 0.0)


def test_ver57_the_n_terminus_at_ph_9_is_unapplied(tmp_path: Path, fragment_2wcd: Fragment) -> None:
    """PROPKA puts ``GLU 18``'s N+ near 7.8; at pH 9 it prefers neutral, and PDB2PQR keeps +1.

    Terminal pKas are never applied (the PHY-16 step-3 NOTE), so the residue's
    applied charge 0 differs from the expected -1, which is derived from the
    groups and not from any log line.
    """
    table, summary = _run(tmp_path, fragment_2wcd(*FRAGMENT), charge="ph: 9.0")
    column = table.residue_resid.tolist().index(18)
    assert bool(table.unapplied[0, column])
    assert table.expected_charge_e[0, column] == -1.0
    assert round(float(table.residue_charge_e[0, column])) == 0
    groups = {
        str(kind): float(table.group_pka[0, index])
        for index, (owner, kind) in enumerate(
            zip(table.group_residue.tolist(), table.group_type.tolist(), strict=True)
        )
        if owner == column
    }
    assert set(groups) == {"N+", "COO"}
    assert groups["N+"] < 9.0
    assert {key: summary["unapplied"][0][key] for key in ("chain", "residue", "frames")} == {
        "chain": "A",
        "residue": "GLU 18",
        "frames": 1,
    }


def test_ver57_a_c_terminal_acid_keeps_both_carboxyl_groups(
    tmp_path: Path, fragment_2wcd: Fragment
) -> None:
    """``ASP 21`` ending the fragment carries two ``COO`` groups, its own and the terminus's.

    PROPKA types both ``COO`` and labels them ``ASP  21 A`` and ``C-   21 A``; the
    group table keeps each pKa, and the residue's expected charge sums both.
    """
    table, _ = _run(tmp_path, fragment_2wcd(18, 21), charge="ph: 8.0")
    column = table.residue_resid.tolist().index(21)
    owned = [
        (str(kind), str(label).split()[0])
        for owner, kind, label in zip(
            table.group_residue.tolist(),
            table.group_type.tolist(),
            table.group_label.tolist(),
            strict=True,
        )
        if owner == column
    ]
    assert sorted(owned) == [("COO", "ASP"), ("COO", "C-")]
    assert table.expected_charge_e[0, column] == -2.0


def test_ver57_pdb2pqr_giving_up_names_the_frame(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fragment_2wcd: Fragment
) -> None:
    """PDB2PQR's own failure is a bare ``RuntimeError``; the stage names the frame and cause."""

    def gives_up(pdb: Path, pqr: Path, settings: ResolvedProtonation) -> dict[str, Any]:
        del pdb, pqr, settings
        try:
            raise ValueError("Unable to debump biomolecule.")
        except ValueError as error:
            raise RuntimeError from error

    monkeypatch.setattr("nanopnp.charge.protonation.run_pdb2pqr", gives_up)
    with pytest.raises(ProtonationError, match=r"frame 0: .*Unable to debump"):
        _run(tmp_path, fragment_2wcd(*FRAGMENT))


def _with_hydrogens(tmp_path: Path, ensemble: AlignedEnsemble) -> AlignedEnsemble:
    """Return ``ensemble`` protonated, hydrogens and patch names as PDB2PQR wrote them.

    A stand-in for a CHARMM-named MD frame: every hydrogen present, the
    C-terminal oxygens ``OT1`` and ``OT2``, and the histidine renamed ``HSE``.
    """
    table, _ = _run(tmp_path / "hydrogens", ensemble)
    (frame,) = table.pqr_frames()
    resname = np.where(frame.resname == "HIS", "HSE", frame.resname)
    return AlignedEnsemble(
        positions_nm=(frame.positions_A[None] / 10.0).astype(np.float32),
        element=np.array(["H" if is_hydrogen(name) else name[0] for name in frame.name.tolist()]),
        name=frame.name,
        resname=resname,
        resid=frame.resid,
        icode=frame.icode,
        chain=frame.chain,
        header={"frames": {"indices": [0]}},
    )


def test_ver57_a_hse_named_histidine_is_titrated_as_his(
    tmp_path: Path, fragment_2wcd: Fragment
) -> None:
    """``HSE 292``, with or without its hydrogens, protonates as ``HIS 292`` does (D5).

    PDB2PQR pins ``HSE`` and refuses it with hydrogens present; the stage drops
    the hydrogens and writes the parent, so PROPKA decides. Without hydrogens the
    PDB PDB2PQR is given is byte for byte the ``HIS``-named one.
    """
    from nanopnp.charge.pqr import chain_characters

    plain = fragment_2wcd(*HISTIDINE)
    renamed = dataclasses.replace(
        plain, resname=np.where(plain.resname == "HIS", "HSE", plain.resname)
    )
    heavy = np.flatnonzero(plain.element != "H")
    chains = chain_characters(plain.chain.tolist())
    assert frame_pdb(plain, 0, heavy, chains) == frame_pdb(renamed, 0, heavy, chains)
    reference, _ = _run(tmp_path / "his", plain)
    hydrogenated = _with_hydrogens(tmp_path, plain)
    assert "HSE" in hydrogenated.resname.tolist()
    assert int((hydrogenated.element == "H").sum()) > 0
    found, _ = _run(tmp_path / "hse", hydrogenated)
    assert _residues(found) == pytest.approx(_residues(reference), abs=1e-6)
    np.testing.assert_array_equal(found.tautomer, reference.tautomer)
    assert found.q_net_e() == pytest.approx(reference.q_net_e(), abs=1e-9)


# -- the D9 gates, each naming its frame ---------------------------------------


def _stand_in(
    monkeypatch: pytest.MonkeyPatch,
    edit: Callable[[list[str]], list[str]],
    **record: list[str],
) -> None:
    """Replace PDB2PQR by a writer of the frame's own heavy atoms, edited by ``edit``.

    Every atom gets charge 0 and radius 1.5 Å, so an unedited frame passes every
    gate with ``Q_net`` 0, and ``edit`` introduces exactly one defect.
    """

    def fake(pdb: Path, pqr: Path, settings: ResolvedProtonation) -> dict[str, Any]:
        del settings
        lines = [
            f"{line[:54]} 0.0000 1.5000"
            for line in pdb.read_text(encoding="ascii").splitlines()
            if line.startswith("ATOM")
        ]
        pqr.write_text("\n".join(edit(lines)) + "\n", encoding="ascii")
        return {"pka": [], "missing": [], "warnings": {}, **record}

    monkeypatch.setattr("nanopnp.charge.protonation.run_pdb2pqr", fake)


def _two_frames(fragment_2wcd: Fragment) -> AlignedEnsemble:
    """Return the fragment over two frames, the second moved non-rigidly by 0.05 nm in one atom."""
    ensemble = fragment_2wcd(*FRAGMENT, frames=2)
    positions = ensemble.positions_nm.copy()
    positions[1, 5] += np.float32(0.05)
    return dataclasses.replace(ensemble, positions_nm=positions)


@pytest.mark.parametrize(
    ("edit", "record", "match"),
    [
        (
            lambda lines: lines,
            {"missing": ["OXT of LEU 26 of chain 'A'"]},
            "could not parameterise",
        ),
        (
            lambda lines: [*lines[:3], lines[3][:-7], *lines[4:]],
            {},
            "does not read as one frame",
        ),
        (
            lambda lines: [lines[0].replace(" 0.0000 1.5000", " 0.5000 0.0000"), *lines[1:]],
            {},
            "radius that is not positive",
        ),
        (
            lambda lines: [lines[0].replace(" 0.0000 1.5000", " 0.5000 1.5000"), *lines[1:]],
            {},
            "Q_net = 0.5 e",
        ),
        (lambda lines: lines[:-3], {}, "does not hold the frame it was given"),
    ],
    ids=["missed-atom", "no-radius", "zero-radius", "fractional-q-net", "dropped-atoms"],
)
def test_ver57_each_gate_names_its_frame(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fragment_2wcd: Fragment,
    edit: Callable[[list[str]], list[str]],
    record: dict[str, Any],
    match: str,
) -> None:
    """Each D9 gate refuses, naming the frame, on the defect it guards (QR-12)."""
    _stand_in(monkeypatch, edit, **record)
    with pytest.raises(ProtonationError, match=match) as raised:
        _run(tmp_path, _two_frames(fragment_2wcd))
    assert "frame 0" in str(raised.value)


def test_ver57_an_unedited_stand_in_passes_every_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fragment_2wcd: Fragment
) -> None:
    """The control for the gate tests: the stand-in's own frames pass, with ``Q_net`` 0."""
    _stand_in(monkeypatch, lambda lines: lines)
    table, summary = _run(tmp_path, _two_frames(fragment_2wcd))
    assert table.q_net_e() == pytest.approx([0.0, 0.0], abs=1e-9)
    assert summary["registration"]["worst_residual_A"] < 1e-3


# -- inputs.pqr: registration, mismatch and the export round trip ---------------


def _produced(tmp_path: Path, ensemble: AlignedEnsemble) -> tuple[Path, ProtonationTable]:
    """Protonate ``ensemble`` and export it; return the export and the table."""
    stage = ProtonationStage(workspace=tmp_path / "produced")
    artefact = stage.run(_inputs(tmp_path, ensemble, _case(tmp_path)))
    payload = artefact.payload["protonation"]
    return export_pqr(payload, tmp_path / "export.pqr"), ProtonationTable.read(payload)


def _supply(
    tmp_path: Path, ensemble: AlignedEnsemble, pqr: Path
) -> tuple[ProtonationTable, dict[str, Any]]:
    """Read ``pqr`` through ``inputs.pqr`` beside ``structure:``."""
    stage = ProtonationStage(workspace=tmp_path / "supplied")
    artefact = stage.run(_inputs(tmp_path, ensemble, _case(tmp_path, pqr=pqr)))
    return ProtonationTable.read(artefact.payload["protonation"]), dict(artefact.summary)


ATOM_TABLE = (
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
)
"""The arrays a PQR carries; the PROPKA expectations it does not."""


def test_ver57_the_export_resupplied_is_bitwise_the_payload(
    tmp_path: Path, fragment_2wcd: Fragment
) -> None:
    """Export, then ``inputs.pqr`` beside the same structure: the atom table, bit for bit.

    The section 3.1 IF-02 export NOTE. The frames already register where they
    stand, so none is moved.
    """
    ensemble = _two_frames(fragment_2wcd)
    exported, produced = _produced(tmp_path, ensemble)
    assert exported.read_text(encoding="utf-8").count("MODEL") == 2
    supplied, summary = _supply(tmp_path, ensemble, exported)
    for key in ATOM_TABLE:
        left, right = getattr(produced, key), getattr(supplied, key)
        assert left.dtype == right.dtype, key
        assert left.tobytes() == right.tobytes(), key
    assert summary["registration"]["moved_frames"] == []
    assert summary["source"] == "inputs.pqr"


def test_ver57_a_moved_pqr_registers_to_its_ensemble(
    tmp_path: Path, fragment_2wcd: Fragment
) -> None:
    """A PQR written in another frame lands in stage 1's, to 0.01 Å.

    The reference's PQRs are in the MD frame; a rigid motion of 20 degrees and
    3 nm stands in for it. Every frame is moved, every heavy atom lands within the
    tolerance, and the charges are untouched.
    """
    ensemble = _two_frames(fragment_2wcd)
    exported, produced = _produced(tmp_path, ensemble)
    angle = np.radians(20.0)
    rotation = np.array(
        [[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0, 0, 1.0]]
    )
    frames = [
        dataclasses.replace(frame, positions_A=frame.positions_A @ rotation.T + [30.0, -5.0, 2.0])
        for frame in read_pqr(exported)
    ]
    moved = write_pqr(tmp_path / "moved.pqr", frames)
    supplied, summary = _supply(tmp_path, ensemble, moved)
    assert summary["registration"]["moved_frames"] == [0, 1]
    assert summary["registration"]["worst_residual_A"] <= 0.01
    difference_A = np.abs(supplied.positions_nm - produced.positions_nm).max() * 10.0
    assert difference_A <= 0.01
    np.testing.assert_array_equal(supplied.charge_e, produced.charge_e)


def test_ver57_a_pqr_missing_a_flippable_atom_is_refused(
    tmp_path: Path, fragment_2wcd: Fragment
) -> None:
    """``NE2`` of ``HIS 292`` deleted: the flippable atoms are not compared, but are counted.

    A flip moves an atom and never removes it, so a residue holding fewer heavy
    atoms than the ensemble's is refused naming it (section 5.3.1 NOTE on ``inputs:``).
    """
    ensemble = fragment_2wcd(*HISTIDINE)
    exported, _ = _produced(tmp_path, ensemble)
    (frame,) = read_pqr(exported)
    keep = ~((frame.resid == 292) & (frame.name == "NE2"))
    assert int((~keep).sum()) == 1
    edited = write_pqr(
        tmp_path / "edited.pqr",
        [
            PQRFrame(
                **{
                    field.name: getattr(frame, field.name)[keep]
                    for field in dataclasses.fields(PQRFrame)
                }
            )
        ],
    )
    with pytest.raises(PQRError, match=r"frame 0 does not register.*holds 2 N atoms of HIS 292"):
        _supply(tmp_path, ensemble, edited)


def test_ver57_a_pqr_with_another_frame_count_is_refused(
    tmp_path: Path, fragment_2wcd: Fragment
) -> None:
    """One frame supplied beside an ensemble of two."""
    exported, _ = _produced(tmp_path, fragment_2wcd(*FRAGMENT))
    with pytest.raises(PQRError, match="holds 1 frames and the ensemble 2"):
        _supply(tmp_path, _two_frames(fragment_2wcd), exported)


def test_ver57_a_pqr_missing_a_residue_is_refused_naming_the_frame(
    tmp_path: Path, fragment_2wcd: Fragment
) -> None:
    """``GLY 22`` deleted from the second frame: frame 1 lacks a residue of the ensemble."""
    ensemble = _two_frames(fragment_2wcd)
    exported, _ = _produced(tmp_path, ensemble)
    first, second = read_pqr(exported)
    keep = second.resid != 22
    second = PQRFrame(
        **{field.name: getattr(second, field.name)[keep] for field in dataclasses.fields(PQRFrame)}
    )
    edited = write_pqr(tmp_path / "edited.pqr", [first, second])
    with pytest.raises(PQRError, match=r"frame 1 does not hold the residues"):
        _supply(tmp_path, ensemble, edited)


def test_ver57_a_pqr_of_another_frame_is_refused_naming_it(
    tmp_path: Path, fragment_2wcd: Fragment
) -> None:
    """The frames supplied in the wrong order: frame 0's atoms are frame 1's, which moved.

    A non-rigid move of one atom by 0.5 Å survives the C-alpha superposition, so
    the frame is refused rather than registered.
    """
    ensemble = fragment_2wcd(*FRAGMENT, frames=2)
    positions = ensemble.positions_nm.copy()
    positions[1, 5] += np.float32(0.05)
    ensemble = dataclasses.replace(ensemble, positions_nm=positions)
    exported, _ = _produced(tmp_path, ensemble)
    first, second = read_pqr(exported)
    swapped = write_pqr(tmp_path / "swapped.pqr", [second, first])
    with pytest.raises(PQRError, match=r"frame 0 does not register to stage 1's frame 0"):
        _supply(tmp_path, ensemble, swapped)


def test_ver57_a_pqr_without_structure_is_read_as_it_stands(
    tmp_path: Path, fragment_2wcd: Fragment
) -> None:
    """Without ``structure:`` the coordinates are taken to be in stage 1's frame already."""
    exported, produced = _produced(tmp_path, fragment_2wcd(*FRAGMENT))
    case = _case(tmp_path, pqr=exported, structure=False, mesh=True)
    stage = ProtonationStage(workspace=tmp_path / "alone")
    artefact = stage.run(StageInputs(resolved=resolve(case)))
    table = ProtonationTable.read(artefact.payload["protonation"])
    assert table.positions_nm.tobytes() == produced.positions_nm.tobytes()
    assert artefact.inputs.keys() == {"pqr"}


# -- the frame cache, cancellation and the missing extra ---------------------------


def test_ver57_one_changed_frame_of_two_reprotonates_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fragment_2wcd: Fragment
) -> None:
    """Each frame is keyed on its own PDB: frame 1 moved, a second run calls PDB2PQR once (D10)."""
    from nanopnp.charge import protonation

    calls: list[Path] = []
    real = protonation.run_pdb2pqr

    def counted(pdb: Path, pqr: Path, settings: ResolvedProtonation) -> dict[str, Any]:
        calls.append(pdb)
        return real(pdb, pqr, settings)

    monkeypatch.setattr("nanopnp.charge.protonation.run_pdb2pqr", counted)
    store = Store(tmp_path / "store")
    ensemble = _two_frames(fragment_2wcd)
    _, first = _run(tmp_path / "first", ensemble, store=store)
    assert len(calls) == 2 and first["cached_frames"] == 0
    positions = ensemble.positions_nm.copy()
    positions[1, 7] += np.float32(0.03)
    _, second = _run(
        tmp_path / "second", dataclasses.replace(ensemble, positions_nm=positions), store=store
    )
    assert len(calls) == 3
    assert second["cached_frames"] == 1


def test_ver57_a_cached_frame_records_the_versions_that_wrote_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fragment_2wcd: Fragment
) -> None:
    """The versions are beside the frame's key, not in it (section 5.3.2).

    A frame an earlier PDB2PQR or PROPKA wrote is reused, and the artefact names
    the versions that wrote it rather than the ones installed now (FR-25).
    """
    from nanopnp.charge import protonation

    calls: list[Path] = []
    real = protonation.run_pdb2pqr

    def counted(pdb: Path, pqr: Path, settings: ResolvedProtonation) -> dict[str, Any]:
        calls.append(pdb)
        return real(pdb, pqr, settings)

    monkeypatch.setattr("nanopnp.charge.protonation.run_pdb2pqr", counted)
    store = Store(tmp_path / "store")
    ensemble = fragment_2wcd(*FRAGMENT)
    _, first = _run(tmp_path / "first", ensemble, store=store)
    assert len(calls) == 1
    monkeypatch.setattr(
        "nanopnp.charge.protonation._versions", lambda: {"pdb2pqr": "9.9.9", "propka": "9.9.9"}
    )
    _, summary = _run(tmp_path / "second", ensemble, store=store)
    assert len(calls) == 1
    assert summary["cached_frames"] == 1
    assert summary["versions"] == first["versions"] != {"pdb2pqr": "9.9.9", "propka": "9.9.9"}


def test_ver57_cancellation_is_checked_between_frames(
    tmp_path: Path, fragment_2wcd: Fragment
) -> None:
    """A set token stops the stage before its first frame, and no artefact is written (D15)."""
    flag = CancelFlag()
    flag.cancel()
    stage = ProtonationStage(workspace=tmp_path / "workspace")
    inputs = _inputs(tmp_path, fragment_2wcd(*FRAGMENT), _case(tmp_path))
    with pytest.raises(Cancelled):
        stage.run(inputs, cancel=flag)
    assert not list((tmp_path / "workspace").rglob("protonation.npz"))


def test_ver57_without_pdb2pqr_a_structure_is_refused_and_a_pqr_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fragment_2wcd: Fragment
) -> None:
    """D4: the extra is named before the first frame; ``inputs.pqr`` needs none."""
    exported, _ = _produced(tmp_path, fragment_2wcd(*FRAGMENT))
    for module in [name for name in sys.modules if name.split(".")[0] in ("pdb2pqr", "propka")]:
        monkeypatch.delitem(sys.modules, module)
    monkeypatch.setitem(sys.modules, "pdb2pqr", None)
    monkeypatch.setitem(sys.modules, "pdb2pqr.main", None)
    with pytest.raises(MissingExtraError, match="'structure' extra"):
        _run(tmp_path / "refused", fragment_2wcd(*FRAGMENT))
    case = _case(tmp_path, pqr=exported, structure=False, mesh=True)
    artefact = ProtonationStage(workspace=tmp_path / "pqr").run(StageInputs(resolved=resolve(case)))
    assert artefact.summary["q_net_e"] == [-3.0]


# -- the case's refusals (D13) ---------------------------------------------------


def test_ver57_the_force_fields_are_a_subset_of_pdb2pqrs() -> None:
    """``charge.forcefield``'s option set is one PDB2PQR's ``--ff`` accepts (D13)."""
    from typing import get_args

    from pdb2pqr.main import build_main_parser

    from nanopnp.io.case import Charge

    accepted = next(
        action.choices for action in build_main_parser()._actions if action.dest == "ff"
    )
    offered = set(get_args(Charge.model_fields["forcefield"].annotation))
    assert offered == {"CHARMM", "PEOEPB", "SWANSON"}
    assert offered <= set(accepted)


@pytest.mark.parametrize(
    ("charge", "kwargs", "error", "fragments"),
    [
        ("forcefield: AMBER", {}, CaseValidationError, ("forcefield",)),
        ("ph: 15.0", {}, CaseValidationError, ("ph",)),
        ("ph: .nan", {}, CaseValidationError, ("ph",)),
        ("ph: 6.0, titration: none", {}, CaseValidationError, ("charge.ph", "titration: none")),
        ("ph: 6.0", {"pqr": True}, CaseValidationError, ("charge.ph", "inputs.pqr")),
        (
            "forcefield: SWANSON",
            {"pqr": True},
            CaseValidationError,
            ("charge.forcefield", "inputs.pqr"),
        ),
        (
            "ph: 6.0",
            {"structure": False, "mesh": True},
            CaseValidationError,
            ("charge.ph", "nothing to protonate"),
        ),
        # charge.smearing is read by WP28's deposition: set beside a structure: it
        # resolves, and beside a supplied mesh with nothing to protonate it is
        # refused naming both keys (section 5.3.1 NOTE on charge.smearing).
        (
            "smearing: {sharpness: 0.4}",
            {"structure": False, "mesh": True},
            CaseValidationError,
            ("charge.smearing.sharpness", "structure:"),
        ),
    ],
)
def test_ver57_each_protonation_refusal_names_its_keys(
    tmp_path: Path,
    charge: str,
    kwargs: dict[str, bool],
    error: type[Exception],
    fragments: tuple[str, ...],
) -> None:
    """The section 5.3.1 NOTE on the protonation keys, refusal by refusal."""
    pqr = tmp_path / "supplied.pqr" if kwargs.pop("pqr", False) else None
    with pytest.raises(error) as raised:
        resolve(_case(tmp_path, charge=charge, pqr=pqr, **kwargs))
    message = str(raised.value)
    assert all(fragment in message for fragment in fragments), message


@pytest.mark.parametrize(
    ("supplied", "match"),
    [
        ("{artefact: abc123, format: pqr}", "inputs.pqr: artefact:"),
        ("{path: x.pqr, format: pqr, groups: {a: b}}", "inputs.pqr.groups"),
        ("{path: x.pqr, format: pdb}", "inputs.pqr.format"),
    ],
)
def test_ver57_a_supplied_pqr_is_named_by_path_and_format(supplied: str, match: str) -> None:
    """``inputs.pqr`` is a file, ``format: pqr``, with no vocabulary mapping."""
    text = CASE.format(
        name="pqr",
        inputs=f"inputs:\n  pqr: {supplied}\n  mesh: {{path: pore.msh, format: msh41}}\n",
        structure="",
        charge="",
    )
    with pytest.raises(CaseValidationError, match=match):
        resolve(loads_case(text))


def test_ver57_a_case_with_nothing_to_protonate_is_refused_by_the_stage(tmp_path: Path) -> None:
    """Neither ``structure:`` nor ``inputs.pqr``: the stage names what is missing."""
    case = _case(tmp_path, structure=False, mesh=True)
    with pytest.raises(UnsupportedCaseSection, match="no structure: section and supplies no"):
        ProtonationStage().key(StageInputs(resolved=resolve(case)))


def test_ver57_propka_reads_its_parameters_on_every_supported_python() -> None:
    """QR-09: PROPKA 3.5.1's parameter dispatch works on 3.11-3.14 once the driver has run.

    On 3.14 an instance has no ``__annotations__`` and PROPKA's ``parse_line``
    fails on its first line; the driver installs a fallback for that one name.
    Elsewhere it installs nothing, and on every interpreter the fallback answers
    no other missing attribute.
    """
    from propka.parameters import Parameters

    from nanopnp.charge.protonation import restore_propka_annotations

    needed = not hasattr(Parameters(), "__annotations__")
    assert restore_propka_annotations() is needed
    assert restore_propka_annotations() is False
    parameters = Parameters()
    parameters.parse_line("version VersionA\n")
    assert parameters.version == "VersionA"
    with pytest.raises(AttributeError):
        parameters.no_such_parameter  # noqa: B018 - the access is the assertion
    if sys.version_info < (3, 14):
        assert "__getattr__" not in vars(Parameters)
