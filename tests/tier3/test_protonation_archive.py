"""VER-57 at Tier 3, recorded: the protonation driver against the author's archived PQRs."""

from __future__ import annotations

import logging
import math
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest

from nanopnp import Case, Session
from nanopnp.charge.pqr import PQRFrame, parent_residue, read_pqr
from nanopnp.charge.protonation import ProtonationTable
from nanopnp.core.paths import REFERENCE_DATA_VARIABLE, reference_file
from nanopnp.core.stages import create
from nanopnp.io.artefact import Artefact, StageInputs
from nanopnp.io.store import Store
from nanopnp.pipeline.case import load_case, resolve
from nanopnp.structure.ensemble import AlignedEnsemble

logger = logging.getLogger(__name__)

# The paper's 50 frames, in time order: DCD frames 48-97.
ARCHIVED_FRAMES = range(50, 100)

ARCHIVED = [
    reference_file(f"prod5_protein_aligned_100ps_{number:02d}.pdb.pqr")
    for number in ARCHIVED_FRAMES
]

# Archive Q_net:
# knowledge/04-clya-geometry-and-charge/03-fixed-charge-pipeline.md.
ARCHIVED_Q_NET_E = -72

needs_pqrs = pytest.mark.skipif(
    any(path is None for path in ARCHIVED),
    reason=(
        f"prod5_protein_aligned_100ps_50..99.pdb.pqr are not in ${REFERENCE_DATA_VARIABLE}; the "
        "author extracts them from prod5_trajectory_last_10ns.7z"
    ),
)


@pytest.fixture(scope="module")
def clya_structure(
    tmp_path_factory: pytest.TempPathFactory,
    ensemble_store: Store,
    ensemble_case: Callable[..., Path],
) -> tuple[Path, Artefact]:
    case = ensemble_case(tmp_path_factory.mktemp("clya-as-protonation"), name="clya-as-protonation")
    result = Session(ensemble_store, write=False).run(Case.load(case), upto="structure")
    return case, result.artefacts["structure"]


def _chain_map(archived: PQRFrame, table_chains: list[str]) -> dict[str, str]:
    ours = list(dict.fromkeys(table_chains))
    theirs = list(dict.fromkeys(archived.chain.tolist()))
    assert len(ours) == len(theirs), (ours, theirs)
    return dict(zip(theirs, ours, strict=True))


def _archived_residues(
    frame: PQRFrame, chains: dict[str, str]
) -> dict[tuple[str, int, str], tuple[float, str]]:
    found: dict[tuple[str, int, str], list[float]] = {}
    names: dict[tuple[str, int, str], str] = {}
    for chain, resid, icode, name, charge in zip(
        frame.chain.tolist(),
        frame.resid.tolist(),
        frame.icode.tolist(),
        frame.resname.tolist(),
        frame.charge_e.tolist(),
        strict=True,
    ):
        key = (chains[chain], resid, icode)
        found.setdefault(key, []).append(charge)
        names[key] = name
    return {key: (math.fsum(charges), names[key]) for key, charges in found.items()}


@needs_pqrs
def test_ver57_the_driver_against_the_archived_pqrs(
    clya_structure: tuple[Path, Artefact], ensemble_store: Store, tmp_path: Path
) -> None:
    case, structure = clya_structure
    inputs = StageInputs(resolved=resolve(load_case(case)), upstream={"structure": structure})
    stage = create("protonation", workspace=tmp_path / "workspace", store=ensemble_store)
    artefact = ensemble_store.get_or_compute(
        stage.key(inputs),  # type: ignore[attr-defined]
        lambda: stage.run(inputs),
    )
    table = ProtonationTable.read(artefact.payload["protonation"])
    assert table.frames == len(ARCHIVED)
    keys = list(
        zip(
            table.residue_chain.tolist(),
            table.residue_resid.tolist(),
            table.residue_icode.tolist(),
            strict=True,
        )
    )
    charge_agreement: list[float] = []
    tautomer_agreement: list[float] = []
    archived_q_net: list[int] = []
    differing: dict[str, int] = {}
    for frame, path in enumerate(ARCHIVED):
        assert path is not None
        (archived,) = read_pqr(path)
        theirs = _archived_residues(archived, _chain_map(archived, table.residue_chain.tolist()))
        q_net = math.fsum(archived.charge_e.tolist())
        archived_q_net.append(round(q_net))
        agree = histidines = histidines_agree = 0
        for column, key in enumerate(keys):
            charge, name = theirs[key]
            ours = round(float(table.residue_charge_e[frame, column]))
            if ours == round(charge):
                agree += 1
            else:
                label = f"{parent_residue(str(table.residue_name[column]))} {key[1]}"
                differing[label] = differing.get(label, 0) + 1
            if parent_residue(name) == "HIS":
                histidines += 1
                histidines_agree += int(str(table.tautomer[frame, column]) == name)
        charge_agreement.append(agree / len(keys))
        tautomer_agreement.append(histidines_agree / histidines if histidines else 1.0)
    ours_q_net = list(artefact.summary["q_net_e"])  # type: ignore[call-overload]
    logger.info(
        "VER-57 Tier 3: residue charge agreement %.4f-%.4f, histidine tautomer agreement "
        "%.4f-%.4f over %d frames; Q_net ours %s, archived %s; residues differing (frames): %s; "
        "unapplied %s; versions %s",
        min(charge_agreement),
        max(charge_agreement),
        min(tautomer_agreement),
        max(tautomer_agreement),
        table.frames,
        sorted(set(ours_q_net)),
        sorted(set(archived_q_net)),
        dict(sorted(differing.items(), key=lambda item: -item[1])[:20]),
        artefact.summary["unapplied"],
        artefact.summary["versions"],
    )
    assert archived_q_net == [ARCHIVED_Q_NET_E] * len(ARCHIVED)
    assert all(isinstance(value, int) for value in ours_q_net)


def _neighbour_margin_A(ensemble: AlignedEnsemble) -> float:
    heavy = np.char.upper(np.char.strip(ensemble.element.astype(str))) != "H"
    positions = np.asarray(ensemble.positions_nm[:, heavy], dtype=np.float64) * 10.0
    steps = np.sqrt(((positions[1:] - positions[:-1]) ** 2).sum(axis=2).mean(axis=1))
    return float(steps.min()) if steps.size else float("inf")


@needs_pqrs
def test_ver57_the_archived_pqrs_register_through_inputs_pqr(
    clya_structure: tuple[Path, Artefact], tmp_path: Path
) -> None:
    case, structure = clya_structure
    bundle = tmp_path / "archived.pqr"
    with bundle.open("w", encoding="utf-8") as handle:
        for model, path in enumerate(ARCHIVED, start=1):
            assert path is not None
            handle.write(f"MODEL     {model:>4}\n")
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith(("ATOM", "HETATM")):
                    handle.write(line + "\n")
            handle.write("ENDMDL\n")
    text = case.read_text(encoding="utf-8").replace(
        "structure:\n", f"inputs:\n  pqr: {{path: {bundle}, format: pqr}}\nstructure:\n", 1
    )
    supplied_case = tmp_path / "supplied.case.yaml"
    supplied_case.write_text(text, encoding="utf-8")
    stage = create("protonation", workspace=tmp_path / "workspace")
    artefact = stage.run(
        StageInputs(resolved=resolve(load_case(supplied_case)), upstream={"structure": structure})
    )
    registration = artefact.summary["registration"]
    ensemble = AlignedEnsemble.read(structure.payload["ensemble"])
    margin_A = _neighbour_margin_A(ensemble)
    logger.info(
        "VER-57 Tier 3: archived PQRs registered: %s; Q_net %s; smallest neighbouring-frame "
        "heavy-atom RMSD %.4f Å against the 0.01 Å tolerance",
        registration,
        sorted(set(artefact.summary["q_net_e"])),  # type: ignore[arg-type]
        margin_A,
    )
    assert registration["worst_residual_A"] <= 0.01  # type: ignore[index]
    assert set(artefact.summary["q_net_e"]) == {ARCHIVED_Q_NET_E}  # type: ignore[arg-type]
