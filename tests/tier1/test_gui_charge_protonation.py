"""VER-60 — the protonation pane, through PDB2PQR and PROPKA on a fragment of 2WCD.

``GLU 18`` to ``LEU 26`` of chain A carries three acids and both termini, so its
``Q_net`` moves from 0 e at pH 2 to -3 e at pH 8 (`.knowledge/07` section 3). The
view is read from the artefact the stage stored, as the shell reads it, and
every number it shows is checked against the payload read independently: the
pKa column against ``group_pka``, the applied charges against ``Q_net``, and the
unapplied flags against the record's own list.

Needs the ``structure`` extra, and is skipped visibly without it.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest

from nanopnp.charge.protonation import ProtonationStage, ProtonationTable
from nanopnp.gui.charge import load_protonation
from nanopnp.gui.solver import Produced
from nanopnp.io.artefact import StageInputs, StructureArtefact
from nanopnp.io.case import loads_case
from nanopnp.io.store import Store

pytest.importorskip("pdb2pqr", reason="the structure extra carries PDB2PQR")

CASE = """\
schema: nanopnp/case/v2
name: fragment
structure:
  source: {{path: {path}}}
  symmetry: {{point_group: C1, axis: z}}
charge: {{ph: {ph}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.15
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: epnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
"""


def _produce(directory: Path, fragment_2wcd: Callable[..., object], ph: float) -> Produced:
    """Protonate ``GLU 18``-``LEU 26`` at ``ph``, store the artefact, and return its event."""
    ensemble = fragment_2wcd(18, 26)
    path = ensemble.write(directory / "ensemble.npz")  # type: ignore[attr-defined]
    structure = StructureArtefact(
        parameters={"ensemble": ensemble.digest()},  # type: ignore[attr-defined]
        payload={"ensemble": path},
    )
    case = loads_case(CASE.format(path=directory / "fragment.pdb", ph=ph))
    store = Store(directory / "store")
    artefact = ProtonationStage(workspace=directory / "work", store=store).run(
        StageInputs(case=case, upstream={"structure": structure})
    )
    stored = store.put(artefact)
    return Produced(
        name="protonation",
        schema=stored.schema,
        hash=stored.hash,
        cached=False,
        store=str(store.root),
    )


@pytest.mark.parametrize(("ph", "q_net_e"), [(2.0, 0.0), (8.0, -3.0)])
def test_ver60_the_pane_shows_the_fragment_s_states_at_the_ph(
    tmp_path: Path, fragment_2wcd, ph: float, q_net_e: float
) -> None:
    """``Q_net``, applied charges, pKa column and unapplied rows, each from the artefact."""
    event = _produce(tmp_path, fragment_2wcd, ph)
    view = load_protonation(event)
    stored = Store(Path(event.store)).get(event.schema, event.hash)
    assert stored is not None
    table = ProtonationTable.read(Path(stored.payload["protonation"]))

    assert view.frames == 1
    assert view.q_net_e[0] == pytest.approx(q_net_e, abs=1e-6)
    frame = view.frame(0)
    assert frame.q_net_e == pytest.approx(q_net_e, abs=1e-6)
    assert math.fsum(table.residue_charge_e[0].tolist()) == pytest.approx(q_net_e, abs=1e-6)
    assert view.titrated
    assert view.pka_status == "computed"

    # One row per PROPKA group, its pKa the table's, NaN shown as not computed.
    assert len(frame.rows) == len(table.group_type)
    shown = np.array([np.nan if row.pka is None else row.pka for row in frame.rows])
    np.testing.assert_array_equal(shown, table.group_pka[0])
    # Each row's applied charge is its residue's, and the residues' sum is Q_net.
    residues = {(row.chain, row.residue): row.applied_e for row in frame.rows}
    for column in range(len(table.residue_name)):
        key = (
            str(table.residue_chain[column]),
            f"{table.residue_name[column]} {int(table.residue_resid[column])}"
            f"{table.residue_icode[column]}",
        )
        if key in residues:
            assert residues[key] == float(table.residue_charge_e[0, column])

    flagged = {(row.chain, row.residue) for row in frame.rows if row.unapplied}
    recorded = {(entry["chain"], entry["residue"]) for entry in stored.summary["unapplied"]}  # type: ignore[union-attr, index]
    assert flagged == recorded
    assert f"ph: {ph}" in view.settings
    assert view.chain_differences == ()
