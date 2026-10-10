"""VER-01, VER-02 and VER-29 on a real structure: 2WCD's protonated charge deposited on its mesh.

The root conftest's ``protonated_2wcd`` carries the PROPKA protonation of the
prepared dodecamer; ``seeded_protonated_2wcd`` copies it into this module's store,
so the walk pays stages 4 to 6 and stage 7's deposit, not PDB2PQR. The case is
registered as VAL-05 registers 2WCD (WP22 D6), and walks to stage 7 at the default
sizes with ``epnp-ns``, whose declaration carries ``fixed_charge`` (WP28 D8).

Gated, as stage 7 gates them: both legs of the conservation report and every
plane of the per-plane check at 1e-3, the boundary ring at 1e-4, and the solid
share at 0.5 (D4). ``Q_net`` is WP27's golden -60 e. Recorded: the solid share,
each material's charge, the worst plane of each side and the stage's seconds;
peak memory in a fresh process under ``-m slow``. The export is read back
through ``inputs.charge`` to the same grid digest (D11).

VER-60 reads the same artefacts as the desktop shell's Charge tab reads them
(WP31): the map carries the record's lattice charge, the conservation pane is the
record, and the protonation pane shows -60 e, no chain difference and the
recorded unapplied states. No second deposit is made.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from nanopnp.gui.charge import load_charge, load_protonation
from nanopnp.gui.solver import Produced
from nanopnp.io.store import Store
from nanopnp.pipeline.run import (
    RunResult,
    run_case,
)

pytestmark = pytest.mark.extended

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import Prepared2WCD, Seed2WCD

logger = logging.getLogger(__name__)

GOLDEN_Q_NET_E = -60
"""WP27's golden net charge of the protonated dodecamer at pH 7.5 (``test_protonation_2wcd``)."""

CASE = """\
schema: nanopnp/case/v0.5
name: 2wcd-charge
structure:
  source: {{path: {pdb}}}
  symmetry: {{point_group: C12}}
{geometry}electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.15
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: epnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
"""


@dataclass(frozen=True)
class Deposited:
    """2WCD walked to stage 7 on its own store."""

    root: Path
    store: Store
    case: Path
    result: RunResult

    @property
    def record(self) -> dict[str, Any]:
        """Return stage 7's charge record."""
        charge: dict[str, Any] = self.result.artefacts["charge"].summary["charge"]  # type: ignore[assignment]
        return charge


@pytest.fixture(scope="module")
def deposited(
    prepared_2wcd: Prepared2WCD,
    seeded_2wcd: Seed2WCD,
    seeded_protonated_2wcd: Callable[[Path], Path],
    tmp_path_factory: pytest.TempPathFactory,
) -> Deposited:
    """Walk 2WCD, registered by its C-alpha centroid (WP22 D6), to stage 7 at default sizes.

    Stages 1 to 6 and the protonation are the session's seeds (WP33 D2), the
    registration included; stage 7 runs here.
    """
    root = tmp_path_factory.mktemp("2wcd-charge")
    store = Store(seeded_protonated_2wcd(root / "store"))
    centre = seeded_2wcd.centre_z_nm
    case = root / "charge.case.yaml"
    case.write_text(
        CASE.format(pdb=prepared_2wcd.path, geometry=seeded_2wcd.geometry), encoding="utf-8"
    )
    result = run_case(case, store=store, upto="charge", workspace=root / "work", write=False)
    cached = {record.name for record in result.stages if record.cached}
    assert {
        "structure",
        "density",
        "symmetry",
        "contour",
        "region",
        "mesh",
        "protonation",
    } <= cached
    logger.info(
        "2WCD to stage 7 at the default sizes, centre_z_nm = %.4f nm: %s s",
        centre,
        {record.name: round(record.seconds, 2) for record in result.stages},
    )
    return Deposited(root=root, store=store, case=case, result=result)


def test_ver01_2wcd_deposit_conserves_its_charge_on_its_generated_mesh(
    deposited: Deposited,
) -> None:
    """Both legs at 1e-3, ``Q_net`` -60 e, the ring at 1e-4 and half the charge in the solids."""
    record = deposited.record
    conservation = record["conservation"]
    mesh = deposited.result.artefacts["mesh"].summary
    assert record["source"] == "deposited"
    assert record["q_net_e"] == pytest.approx(GOLDEN_Q_NET_E, abs=1e-9)
    assert conservation["q_net_e"] == pytest.approx(GOLDEN_Q_NET_E, abs=1e-9)
    assert abs(conservation["producer"]["relative_error"]) <= 1e-3
    assert abs(conservation["consumer"]["relative_error"]) <= 1e-3
    assert abs(conservation["quadrature_agreement"]["relative_error"]) <= 1e-3
    assert conservation["boundary_ring"]["ratio"] <= 1e-4
    share = record["solid_share"]
    assert share["solid_share"] >= 0.5
    logger.info(
        "VER-01 2WCD on %d elements (P%d): Q_net %.9f e, lattice %.9f e, mesh %.9f e; producer "
        "%.3e, consumer %.3e, quadrature %.3e, ring %.3e, axis guard %.3e e",
        mesh["elements"],
        record["order"],
        conservation["q_net_e"],
        conservation["q_grid_e"],
        conservation["q_mesh_e"],
        conservation["producer"]["relative_error"],
        conservation["consumer"]["relative_error"],
        conservation["quadrature_agreement"]["relative_error"],
        conservation["boundary_ring"]["ratio"],
        conservation["axis_guard_deficit_e"],
    )
    (stage,) = [record for record in deposited.result.stages if record.name == "charge"]
    logger.info(
        "VER-01 2WCD solid share %s; material charge %s e; lattice %s; deposit %s; stage 7 %.2f s",
        share,
        record["material_charge_e"],
        {key: record["lattice"].get(key) for key in ("atoms", "grid", "cached")},
        record["deposit"],
        stage.seconds,
    )


def test_ver02_2wcd_every_plane_agrees_with_the_source_atoms(deposited: Deposited) -> None:
    """The per-plane check at its 12 planes: lattice and mesh against the atoms, at 1e-3."""
    plane = deposited.record["conservation"]["per_plane"]
    assert plane["count"] == 12
    assert plane["grid_worst_relative_error"] <= 1e-3
    assert plane["mesh_worst_relative_error"] <= 1e-3
    logger.info(
        "VER-02 2WCD per plane (s = %.2f nm, planes %s nm): worst lattice %.3e at z = %.3f nm, "
        "worst mesh %.3e at z = %.3f nm",
        plane["smoothing_nm"],
        [round(z, 3) for z in plane["planes_nm"]],
        plane["grid_worst_relative_error"],
        plane["grid_worst_plane_z_nm"],
        plane["mesh_worst_relative_error"],
        plane["mesh_worst_plane_z_nm"],
    )


def test_ver29_the_2wcd_export_reads_back_through_inputs_charge_to_the_same_digest(
    deposited: Deposited, tmp_path: Path
) -> None:
    """D11: ``stage charge --export X.yaml``, then the document read as ``inputs.charge``."""
    from nanopnp.charge.fields import load_field
    from nanopnp.charge.stage import export_charge
    from nanopnp.density.grid import read_grid

    stage7 = deposited.result.artefacts["charge"]
    export_charge(stage7, tmp_path / "2wcd-charge.yaml")
    field = load_field(tmp_path / "2wcd-charge.yaml")
    stored = read_grid(stage7.payload["charge"], format="npz")
    assert field.grid.digest() == stored.digest()
    assert field.document.q_net_e == pytest.approx(GOLDEN_Q_NET_E, abs=1e-9)
    assert field.planar_integral_C() / 1.602176634e-19 == pytest.approx(GOLDEN_Q_NET_E, rel=1e-9)


def _event(deposited: Deposited, name: str) -> Produced:
    """Return the walk's artefact for ``name`` as the build reports it to the shell."""
    artefact = deposited.result.artefacts[name]
    return Produced(
        name=name,
        schema=artefact.schema,
        hash=artefact.hash,
        cached=False,
        store=str(deposited.store.root),
    )


def test_ver60_the_2wcd_charge_tab_shows_its_record(deposited: Deposited) -> None:
    """The map integrates to the record's lattice charge, and the report is the record (D6, D10).

    The map's block means, weighted by their areas, sum to ``q_grid`` to
    round-off: the picture is the deposit, reduced, never a field rebuilt for
    display. The deposit conserves ``Q_net`` to round-off too (its producer leg
    is about 1e-14, gated at 1e-3), so the picture carries -60 e to 1e-12.
    """
    view = load_charge(_event(deposited, "charge"))
    record = deposited.record
    conservation = record["conservation"]
    assert view.charge is not None
    assert view.charge.integral_e == pytest.approx(conservation["q_grid_e"], rel=1e-12)
    assert view.charge.integral_e == pytest.approx(GOLDEN_Q_NET_E, rel=1e-12)
    assert view.quantities[0] == "charge"

    shown = view.conservation
    assert shown is not None
    assert shown.source == "deposited"
    for key in ("q_net_e", "q_grid_e", "q_mesh_e", "axis_guard_deficit_e", "boundary_ring"):
        assert shown.figures[key] == conservation[key]
    assert shown.figures["material_charge_e"] == record["material_charge_e"]
    assert shown.figures["solid_share"] == record["solid_share"]
    legs = {leg.name: leg for leg in shown.legs}
    for name, key in (
        ("producer", "producer"),
        ("consumer", "consumer"),
        ("quadrature agreement", "quadrature_agreement"),
    ):
        assert legs[name].value == conservation[key]["relative_error"]
        assert legs[name].tolerance == conservation[key].get("tolerance")
    plane = conservation["per_plane"]
    assert legs["worst plane (lattice)"].value == plane["grid_worst_relative_error"]
    assert legs["worst plane (mesh)"].value == plane["mesh_worst_relative_error"]
    assert dict(shown.planes) == {
        "worst plane (lattice)": plane["grid_worst_plane_z_nm"],
        "worst plane (mesh)": plane["mesh_worst_plane_z_nm"],
    }
    logger.info(
        "VER-60 2WCD map: %s pixels of up to %d x %d lattice nodes each, %.12f e against "
        "q_grid %.12f e",
        view.charge.areas.shape,
        view.charge.block,
        view.charge.block,
        view.charge.integral_e,
        conservation["q_grid_e"],
    )


def test_ver60_the_2wcd_protonation_pane_shows_the_recorded_states(deposited: Deposited) -> None:
    """-60 e, no chain difference, and the unapplied rows: ``CYS 285`` everywhere, ``LYS 8``'s N+.

    Under CHARMM a ``CYS⁻`` cannot be held, so ``CYS 285`` (pKa 6.25) is
    unapplied in every chain. PDB2PQR never applies a terminal pKa, so a chain
    whose ``LYS 8`` N-terminus PROPKA places below pH 7.5 is unapplied there
    (`.knowledge/07` section 3). The pane reads both from the table and checks
    them against the record (D11).
    """
    event = _event(deposited, "protonation")
    view = load_protonation(event)
    summary = deposited.result.artefacts["protonation"].summary

    assert view.titrated
    assert all(q == pytest.approx(GOLDEN_Q_NET_E, abs=1e-6) for q in view.q_net_e)
    assert view.chain_differences == ()
    recorded = {(entry["chain"], entry["residue"]) for entry in summary["unapplied"]}  # type: ignore[union-attr, index]
    chains = {chain for chain, _ in recorded}
    assert chains == set("ABCDEFGHIJKL")
    assert {(chain, "CYS 285") for chain in chains} <= recorded
    assert {residue for _, residue in recorded} <= {"CYS 285", "LYS 8"}

    shown: set[tuple[str, str]] = set()
    for index in range(view.frames):
        frame = view.frame(index)
        assert frame.q_net_e == pytest.approx(GOLDEN_Q_NET_E, abs=1e-6)
        shown |= {(row.chain, row.residue) for row in frame.rows if row.unapplied}
    assert shown == recorded
    logger.info(
        "VER-60 2WCD protonation pane: %d frame(s), unapplied %s",
        view.frames,
        sorted(recorded),
    )


_MEASURE = """\
import json, logging, resource, sys, time
from pathlib import Path
from nanopnp.core.stages import create
from nanopnp.io.artefact import StageInputs
from nanopnp.pipeline.case import load_case, resolve
from nanopnp.io.store import Store
store, case, mesh, protonation, workspace = sys.argv[1:6]
document = load_case(Path(case))
upstream = {
    "mesh": Store(store).get("nanopnp/mesh/v1", mesh),
    "protonation": Store(store).get("nanopnp/protonation/v1", protonation),
}
parts = {}
class Parts(logging.Handler):
    def emit(self, record):
        parts.update(getattr(record, "timings", {}))
source = logging.getLogger("nanopnp.charge.stage")
source.setLevel(logging.INFO)
source.addHandler(Parts())
stage = create("charge", workspace=Path(workspace))
started = time.perf_counter()
done = stage.run(StageInputs(resolved=resolve(document), upstream=upstream))
seconds = time.perf_counter() - started
scale = 1e9 if sys.platform == "darwin" else 1e6
peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / scale
print(json.dumps({"seconds": seconds, "peak_GB": peak, "parts": parts}))
"""
"""Stage 7 cold in a fresh process, with no store: the lattice summed, and a peak RSS its own."""


@pytest.mark.slow
@pytest.mark.skipif(sys.platform == "win32", reason="resource is POSIX only")
def test_ver01_cost_of_the_2wcd_deposit(deposited: Deposited, tmp_path: Path) -> None:
    """Wall clock and peak memory of stage 7 on 2WCD at the default sizes, cold; recorded."""
    artefacts = deposited.result.artefacts
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            _MEASURE,
            str(deposited.store.root),
            str(deposited.case),
            artefacts["mesh"].hash,
            artefacts["protonation"].hash,
            str(tmp_path / "workspace"),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    measured = json.loads(result.stdout.strip().splitlines()[-1])
    logger.info(
        "WP28: stage 7 on 2WCD (%d elements), cold, %.1f s (%s) and %.2f GB peak RSS",
        artefacts["mesh"].summary["elements"],
        measured["seconds"],
        {key: round(value, 2) for key, value in measured["parts"].items()},
        measured["peak_GB"],
    )
    assert measured["seconds"] > 0.0
    # The parts come from stage 7's log record, never its artefact (WP32 D15).
    assert set(measured["parts"]) == {"sum", "deposit", "gates"}, measured["parts"]


_MEASURE_FRAMES = """\
import json, resource, sys, time
from dataclasses import replace
from pathlib import Path
import numpy as np
from nanopnp.charge.kernel import source_atoms, sum_kernel
from nanopnp.charge.protonation import ProtonationTable
from nanopnp.io.store import Store
store, protonation, frames = sys.argv[1], sys.argv[2], int(sys.argv[3])
artefact = Store(store).get("nanopnp/protonation/v1", protonation)
one = source_atoms(ProtonationTable.read(Path(artefact.payload["protonation"])), sharpness=0.5)
atoms = replace(
    one,
    r_nm=np.tile(one.r_nm, frames),
    z_nm=np.tile(one.z_nm, frames),
    width_nm=np.tile(one.width_nm, frames),
    weight_e=np.tile(one.weight_e / frames, frames),
    frame=np.repeat(np.arange(frames, dtype=np.int64), one.count),
    atom=np.tile(one.atom, frames),
    frames=frames,
    table=None,
)
started = time.perf_counter()
lattice = sum_kernel(atoms, 0.005)
seconds = time.perf_counter() - started
scale = 1e9 if sys.platform == "darwin" else 1e6
peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / scale
q = lattice.grid.planar_integral() / 1.602176634e-19
print(json.dumps({"seconds": seconds, "peak_GB": peak, "q_e": q}))
"""
"""The sum over ``frames`` copies of the 2WCD frame, each carrying ``q_i/frames``: its cost."""


@pytest.mark.slow
@pytest.mark.skipif(sys.platform == "win32", reason="resource is POSIX only")
def test_ver01_cost_of_summing_fifty_2wcd_frames(deposited: Deposited) -> None:
    """The sum is linear in frames (*Design* §6): 50 frames' wall clock and peak RSS, recorded."""
    frames = 50
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            _MEASURE_FRAMES,
            str(deposited.store.root),
            deposited.result.artefacts["protonation"].hash,
            str(frames),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    measured = json.loads(result.stdout.strip().splitlines()[-1])
    logger.info(
        "WP28: the kernel summed over %d copies of the 2WCD frame, %.1f s (%.2f s per frame) and "
        "%.2f GB peak RSS; Q %.9f e",
        frames,
        measured["seconds"],
        measured["seconds"] / frames,
        measured["peak_GB"],
        measured["q_e"],
    )
    assert measured["q_e"] == pytest.approx(GOLDEN_Q_NET_E, rel=1e-9)
