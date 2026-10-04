"""VER-57, FR-12: the prepared 2WCD dodecamer protonated at pH 7.5 with PROPKA (WP27).

The dodecamer is protonated once per session by the ``protonated_2wcd`` fixture,
through the stage API, in about a minute (WP27 D17). The golden is ``Q_net`` in
stage 1's frame, measured once and pinned: a move of it is a change in PDB2PQR
or PROPKA, or in what the stage gives them, and the failure names the versions.
The CHARMM radii, the repaired termini and the unapplied states are checked
against what ``.knowledge/07`` section 3 and the PHY-16 step-3 NOTE record.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import pytest

from nanopnp.charge.protonation import (
    ProtonationStage,
    ProtonationTable,
    export_pqr,
)
from nanopnp.io.artefact import StageInputs
from nanopnp.io.case import load_case, loads_case
from nanopnp.io.store import Store

pytestmark = pytest.mark.extended

if TYPE_CHECKING:
    from conftest import Protonated2WCD

pytest.importorskip("pdb2pqr", reason="the structure extra carries PDB2PQR")

logger = logging.getLogger(__name__)

GOLDEN_Q_NET_E = -60
"""``Q_net`` of the prepared dodecamer at pH 7.5, CHARMM and PROPKA, in stage 1's frame.

-5 e per chain, as measured in the crystal frame while planning (``.knowledge/07``
section 3), re-measured through the stage and pinned.
"""

CHAINS = 12
"""ClyA is a dodecamer (C12)."""


@pytest.fixture(scope="module")
def protonated(protonated_2wcd: Protonated2WCD) -> tuple[ProtonationTable, dict[str, Any]]:
    """Return the protonated dodecamer's table and summary."""
    artefact = Store(protonated_2wcd.store).get(
        "nanopnp/protonation/v1", protonated_2wcd.protonation
    )
    assert artefact is not None
    logger.info("protonated 2WCD in %.1f s", protonated_2wcd.seconds)
    return ProtonationTable.read(artefact.payload["protonation"]), dict(artefact.summary)


def test_ver57_q_net_of_the_prepared_dodecamer_is_its_golden(
    protonated: tuple[ProtonationTable, dict[str, Any]],
) -> None:
    """``Q_net`` is an integer to 10⁻⁶ e and equals its golden, -5 e on every chain."""
    table, summary = protonated
    versions = summary["versions"]
    (q_net,) = table.q_net_e().tolist()
    assert abs(q_net - round(q_net)) <= 1e-6
    assert summary["q_net_e"] == [GOLDEN_Q_NET_E], (
        f"Q_net moved from its golden {GOLDEN_Q_NET_E} e to {summary['q_net_e']} e under "
        f"PDB2PQR {versions['pdb2pqr']} and PROPKA {versions['propka']}"
    )
    by_chain: dict[str, float] = {}
    for chain, charge in zip(table.residue_chain.tolist(), table.residue_charge_e[0], strict=True):
        by_chain[chain] = by_chain.get(chain, 0.0) + float(charge)
    assert len(by_chain) == CHAINS
    assert {chain: round(value) for chain, value in by_chain.items()} == dict.fromkeys(by_chain, -5)
    assert summary["chain_differences"] == []


def test_ver57_every_heavy_radius_is_the_charmm_tables(
    protonated: tuple[ProtonationTable, dict[str, Any]],
) -> None:
    """The PQR's radii and the stage-2 table agree on every heavy atom (D14).

    Both are transcribed from one ``CHARMM.DAT``, so a disagreement would be a
    defect in one of them, not a modelling choice.
    """
    _, summary = protonated
    radii = summary["radii"]
    logger.info("radii: %s", radii)
    assert radii["heavy_differing"] == 0, radii["worst"]
    assert radii["heavy_unresolved"] == 0, radii["unresolved_examples"]
    assert radii["compared"] > 0


def test_ver57_pdb2pqr_repairs_twelve_terminal_oxygens(
    protonated: tuple[ProtonationTable, dict[str, Any]],
) -> None:
    """One ``OXT`` per chain, added as ``OT2``; every other heavy atom registers or is a flip.

    The flipped amide and ring atoms are recorded, not held to 0.01 Å; they land
    0.13-0.40 Å from any atom given (``.knowledge/07`` section 3).
    """
    table, summary = protonated
    registration = summary["registration"]
    logger.info("registration: %s", registration)
    assert registration["added_heavy_atoms"] == CHAINS
    assert registration["worst_residual_A"] <= 0.01
    assert registration["worst_flipped_A"] < 0.5
    names = table.name[table.frame_slice(0)]
    assert int((names == "OT2").sum()) == CHAINS


def test_ver57_cys_285_and_the_lys_8_n_terminus_are_unapplied_as_their_pka_says(
    protonated: tuple[ProtonationTable, dict[str, Any]],
) -> None:
    """``CYS 285`` is unapplied in every chain; ``LYS 8`` exactly where its N+ pKa is below 7.5.

    The PHY-16 step-3 NOTE: CHARMM cannot hold ``CYS⁻``, and PDB2PQR never applies
    a terminal pKa. The N+ pKa of ``LYS 8`` is 7.48-7.50 across the chains, so
    which chains are unapplied is decided by the unrounded value.
    """
    table, _ = protonated
    resid = table.residue_resid.tolist()
    for column in [index for index, number in enumerate(resid) if number == 285]:
        assert bool(table.unapplied[0, column]), table.residue_chain[column]
        assert table.residue_name[column] == "CYS"
    terminal = {}
    for group, (owner, kind) in enumerate(
        zip(table.group_residue.tolist(), table.group_type.tolist(), strict=True)
    ):
        if kind == "N+" and resid[owner] == 8:
            terminal[owner] = float(table.group_pka[0, group])
    assert len(terminal) == CHAINS
    logger.info(
        "LYS 8 N+ pKa by chain: %s", {table.residue_chain[k]: v for k, v in terminal.items()}
    )
    for column, pka in terminal.items():
        assert bool(table.unapplied[0, column]) == (pka < 7.5), (table.residue_chain[column], pka)
        assert 7.4 < pka < 7.6


def test_ver57_the_export_resupplied_beside_the_structure_is_the_payload(
    protonated: tuple[ProtonationTable, dict[str, Any]],
    protonated_2wcd: Protonated2WCD,
    tmp_path: Path,
) -> None:
    """Export, then ``inputs.pqr`` beside ``structure:``: the atom table, bit for bit.

    The section 3.1 IF-02 export NOTE on the reference structure: every frame
    registers where it stands, so none is moved, and the flipped atoms keep the
    positions PDB2PQR gave them.
    """
    table, _ = protonated
    store = Store(protonated_2wcd.store)
    produced = store.get("nanopnp/protonation/v1", protonated_2wcd.protonation)
    assert produced is not None
    exported = export_pqr(produced.payload["protonation"], tmp_path / "2wcd.pqr")
    text = protonated_2wcd.case.read_text(encoding="utf-8").replace(
        "name: 2wcd-protonated",
        f"name: 2wcd-supplied\ninputs:\n  pqr: {{path: {exported}, format: pqr}}",
    )
    case = loads_case(text)
    structure = store.get("nanopnp/structure/v1", protonated_2wcd.structure)
    assert structure is not None
    stage = ProtonationStage(workspace=tmp_path / "supplied")
    artefact = stage.run(StageInputs(case=case, upstream={"structure": structure}))
    supplied = ProtonationTable.read(artefact.payload["protonation"])
    for key in (
        "frame_offsets",
        "positions_nm",
        "charge_e",
        "radius_nm",
        "name",
        "resname",
        "chain",
        "resid",
        "icode",
        "residue_charge_e",
        "tautomer",
    ):
        left, right = getattr(table, key), getattr(supplied, key)
        assert left.tobytes() == right.tobytes(), key
    assert artefact.summary["registration"]["moved_frames"] == []
    np.testing.assert_array_equal(supplied.q_net_e(), table.q_net_e())
    assert load_case(protonated_2wcd.case).name == "2wcd-protonated"


_MEASURE = """\
import json, resource, sys, time
from pathlib import Path
from nanopnp.core.stages import create
from nanopnp.io.artefact import StageInputs
from nanopnp.io.case import load_case
from nanopnp.io.store import Store
store, case, structure, workspace = sys.argv[1:5]
document = load_case(Path(case))
artefact = Store(store).get("nanopnp/structure/v1", structure)
stage = create("protonation", workspace=Path(workspace))
started = time.perf_counter()
done = stage.run(StageInputs(case=document, upstream={"structure": artefact}))
seconds = time.perf_counter() - started
scale = 1e9 if sys.platform == "darwin" else 1e6
peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / scale
print(json.dumps({"seconds": seconds, "peak_GB": peak, "q_net_e": done.summary["q_net_e"]}))
"""
"""One cold frame in a fresh process: no frame cache, and a peak RSS that is this run's."""


@pytest.mark.slow
@pytest.mark.skipif(sys.platform == "win32", reason="resource is POSIX only")
def test_ver57_cost_of_one_dodecamer_frame(protonated_2wcd: Protonated2WCD, tmp_path: Path) -> None:
    """Wall clock and peak memory of protonating one frame of the dodecamer, cold; recorded.

    WP27's Verification asks for both per frame: the reference ensemble is 50
    frames, and frames run serially (D15).
    """
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            _MEASURE,
            str(protonated_2wcd.store),
            str(protonated_2wcd.case),
            protonated_2wcd.structure,
            str(tmp_path / "workspace"),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    measured = json.loads(result.stdout.strip().splitlines()[-1])
    logger.info(
        "VER-57: one 2WCD dodecamer frame, cold, %.1f s and %.2f GB peak RSS, Q_net %s",
        measured["seconds"],
        measured["peak_GB"],
        measured["q_net_e"],
    )
    assert measured["q_net_e"] == [GOLDEN_Q_NET_E]
