"""VER-46 — example 07, from a PDB entry to a charged run, executed verbatim (FR-12 to FR-15).

The README's two blocks run from a copy of ``examples/07-pdb-to-charged-run``, the
``run`` block first. It prepares the entry with example 06's own ``prepare.py``
(WP32 D5), walks every stage to an ePNP-NS solve under the validated model,
exports the PQR and the charge, feeds the PQR back through ``inputs.pqr``, and
turns both FR-15 switches on. The ``refused`` block re-supplies the exported
lattice through ``inputs.charge``, and stage 7's quadrature-agreement gate must
refuse it with exit 4 (WP32 D4, D8; VAL-15).

Each oracle is a property of the model, not a transcribed number (WP32 D7), and
fails loudly on a specific error:

- (a) the walk records every :data:`~nanopnp.io.run.PIPELINE` stage and no deviation,
  with a deposited charge from a PDB2PQR protonation;
- (b) ``Q_net`` is the integer the exported PQR's charge column sums to, parsed here
  independently of nanopnp: a lost frame or residue moves it;
- (c) the conservation report is in the manifest, each leg and each worst plane
  below its recorded tolerance. Stage 7 would have exited 4 otherwise, so this
  passes by construction; it is asserted because it is what the guide tells a user
  to read;
- (d) the negatively charged lumen is cation-selective, ``t+ > 1/2``, with the
  FR-23 routes in agreement. A flipped sign or a lost charge puts ``t+`` near or
  below the uncharged pore's infinite-dilution 0.396 (the WP32 plan, Design §1);
- (e) the PQR fed back gives the same atom table and byte-identical deposit and
  lattice files under a different charge key: the deposit depends on the atoms
  alone (VER-23's reproducible payloads, WP32 D15);
- (f) the switches are exactly the two deviations listed, the mesh carries an
  ``exclusion`` material, and the region and mesh keys move;
- (g) the exported charge is a ``nanopnp/field/v1`` areal charge density declaring
  the manifest's ``Q_net``;
- (h) the re-supplied lattice is refused at the quadrature-agreement check.

The mesh is ``size_scale`` 4, for runtime (WP32 D6); the stabilisation mode is the
case's default, ``none``, and is logged with the transport number. Block and stage
durations are logged.
"""

from __future__ import annotations

import json
import logging
import math
import re
import time
from pathlib import Path

import pytest
import yaml

from nanopnp.charge.deposit import DEPOSIT_PAYLOAD
from nanopnp.charge.protonation import PAYLOAD_NAME as PROTONATION_PAYLOAD
from nanopnp.charge.protonation import ProtonationTable
from nanopnp.charge.stage import CHARGE_PAYLOAD
from nanopnp.core.hashing import decode_floats
from nanopnp.io.artefact import FIELDS_SCHEMA, PROTONATION_SCHEMA
from nanopnp.io.run import PIPELINE
from nanopnp.io.store import Store
from nanopnp.post.qoi import ROUTE_AGREEMENT_TOLERANCE
from nanopnp.validation.examples import CommandResult, copy_example, run_tagged

logger = logging.getLogger(__name__)

REPOSITORY = Path(__file__).resolve().parents[2]

TIMEOUT_S = 1800.0
"""Per command: the solve is the longest, a few minutes on one core (WP32 D9)."""

Q_NET_TOL_E = 1e-6
"""How far the PQR's charge column, and the manifest's ``Q_net``, may lie from each other."""

SWITCHES = {"charge.exclusion_offset_nm", "charge.dielectric_transition_nm"}
"""The two FR-15 switches ``switches.case.yaml`` sets away from their validated ``0``."""

Ran = tuple[Path, list[CommandResult], list[CommandResult]]


def _read(path: Path) -> dict[str, object]:
    """Return a record written through ``canonical``, its floats decoded."""
    decoded = decode_floats(json.loads(path.read_text(encoding="utf-8")))
    assert isinstance(decoded, dict)
    return decoded


def _charge_record(example: Path, run: str) -> dict[str, object]:
    """Return a run's manifest charge group's deposited record."""
    group = _read(example / run / "manifest.json")["charge"]
    assert isinstance(group, dict)
    record = group["charge"]
    assert isinstance(record, dict)
    return record


def _artefacts(example: Path, run: str) -> dict[str, dict[str, object]]:
    """Return a run's manifest ``inputs.artefacts``: each stage's hash and its substitution."""
    inputs = _read(example / run / "manifest.json")["inputs"]
    assert isinstance(inputs, dict)
    artefacts = inputs["artefacts"]
    assert isinstance(artefacts, dict)
    return artefacts


def _pqr_charge_sums(path: Path) -> list[float]:
    """Return each ``MODEL``'s sum of a PQR's charge column, read without nanopnp.

    A PQR line carries, after the coordinates, the charge and the radius as the
    last two whitespace-separated fields; that is the layout PDB2PQR writes and
    the export copies.
    """
    sums: list[list[float]] = [[]]
    for line in path.read_text(encoding="ascii").splitlines():
        if line.startswith("ENDMDL"):
            sums.append([])
        elif line.startswith(("ATOM", "HETATM")):
            sums[-1].append(float(line.split()[-2]))
    return [math.fsum(column) for column in sums if column]


@pytest.fixture(scope="module")
def ran(tmp_path_factory: pytest.TempPathFactory) -> Ran:
    """Copy the example; run the ``run`` block, then the ``refused`` one, which reads its export."""
    example = copy_example(
        REPOSITORY / "examples" / "07-pdb-to-charged-run",
        tmp_path_factory.mktemp("examples"),
        repository=REPOSITORY,
    )
    started = time.perf_counter()
    walked = run_tagged(example, "run", timeout_s=TIMEOUT_S)
    middle = time.perf_counter()
    refused = run_tagged(example, "refused", timeout_s=TIMEOUT_S)
    logger.info(
        "example 07: run block %.1f s, refused block %.1f s",
        middle - started,
        time.perf_counter() - middle,
    )
    record = _read(example / "run" / "run.json")
    stages = record["stages"]
    assert isinstance(stages, list)
    logger.info(
        "example 07 run: stage seconds %s",
        {stage["stage"]: round(stage["seconds"], 2) for stage in stages},
    )
    return example, walked, refused


def test_ver46_07_the_prepared_entry_walks_every_stage_to_a_charged_solve(ran: Ran) -> None:
    """(a) Every stage keyed, no deviation, a deposited charge from PDB2PQR (FR-12-FR-14, FR-25)."""
    example, walked, _ = ran
    assert [result.argv[:2] for result in walked] == [
        ("python", "../06-pdb-to-mesh/prepare.py"),
        ("nanopnp", "run"),
        ("nanopnp", "inspect"),
        ("nanopnp", "stage"),
        ("nanopnp", "stage"),
        ("nanopnp", "run"),
        ("nanopnp", "run"),
        ("nanopnp", "inspect"),
    ]
    artefacts = _artefacts(example, "run")
    assert set(PIPELINE) <= set(artefacts), sorted(artefacts)
    assert not any(entry["hand_substituted"] for entry in artefacts.values())
    manifest = _read(example / "run" / "manifest.json")
    deviations = manifest["deviations"]
    assert isinstance(deviations, dict)
    assert deviations["count"] == 0, deviations
    group = manifest["charge"]
    assert isinstance(group, dict)
    assert group["charge"]["source"] == "deposited"  # type: ignore[index]
    assert group["protonation"]["source"] == "pdb2pqr"  # type: ignore[index]
    # ``inspect run`` shows the report where the guide says to read it.
    # The path as the platform writes it: ``run\\manifest.json`` on Windows.
    assert str(Path("run") / "manifest.json") in walked[2].stdout
    assert '"conservation"' in walked[2].stdout


def test_ver46_07_q_net_is_the_integer_the_exported_pqr_sums_to(ran: Ran) -> None:
    """(b) The PQR's charge column, parsed here, sums to an integer: the manifest's ``Q_net``."""
    example, _, _ = ran
    (column,) = _pqr_charge_sums(example / "2wcd.pqr")
    assert abs(column - round(column)) < Q_NET_TOL_E, column
    assert round(column) < 0, "the ClyA lumen carries a net negative charge at pH 7.5"
    q_net = _charge_record(example, "run")["q_net_e"]
    assert isinstance(q_net, float)
    assert abs(q_net - column) < Q_NET_TOL_E, (q_net, column)
    logger.info("example 07: Q_net %.9f e, PQR column %.9f e", q_net, column)


def test_ver46_07_the_conservation_report_is_in_the_manifest_and_passes(ran: Ran) -> None:
    """(c) Each leg and each worst plane below the tolerance the record carries (PHY-19, QR-03)."""
    example, _, _ = ran
    report = _charge_record(example, "run")["conservation"]
    assert isinstance(report, dict)
    for leg in ("producer", "consumer", "quadrature_agreement"):
        entry = report[leg]
        assert abs(entry["relative_error"]) < entry["tolerance"], (leg, entry)
    plane = report["per_plane"]
    assert plane["reference"] == "source atoms, in closed form"
    for side in ("grid", "mesh"):
        assert abs(plane[f"{side}_worst_relative_error"]) < plane["tolerance"], (side, plane)
    logger.info(
        "example 07 conservation: producer %.3e, consumer %.3e, quadrature %.3e, worst plane "
        "%.3e (lattice) and %.3e (mesh), against %.0e",
        report["producer"]["relative_error"],
        report["consumer"]["relative_error"],
        report["quadrature_agreement"]["relative_error"],
        plane["grid_worst_relative_error"],
        plane["mesh_worst_relative_error"],
        plane["tolerance"],
    )


def test_ver46_07_the_negatively_charged_lumen_is_cation_selective(ran: Ran) -> None:
    """(d) ``t+ > 1/2`` at 0.15 M and +50 mV, with the FR-23 routes in agreement (VER-46)."""
    example, _, _ = ran
    quantities = _read(example / "run" / "run.json")["quantities"]
    assert isinstance(quantities, dict)
    agreement = quantities["route_agreement"]
    assert isinstance(agreement, dict)
    stabilisation = _read(example / "run" / "manifest.json")["stabilisation"]
    logger.info(
        "example 07: t+ %.4f, route agreement %.3e, stabilisation %s",
        quantities["transport_number"],
        agreement["relative_difference"],
        stabilisation["mode"],  # type: ignore[index]
    )
    assert quantities["transport_number"] > 0.5, quantities
    assert agreement["relative_difference"] < ROUTE_AGREEMENT_TOLERANCE


def test_ver46_07_the_exported_pqr_deposits_the_same_charge(ran: Ran) -> None:
    """(e) Same atom table, byte-identical deposit and lattice, under another key (FR-12, FR-13).

    The protonation payloads are not compared: the PDB2PQR run's carries PROPKA's
    group table, which a PQR does not hold (WP32 D7).
    """
    example, _, _ = ran
    store = Store(example / "store")
    left, right = _artefacts(example, "run"), _artefacts(example, "run-pqr")
    files = _read(example / "run-pqr" / "manifest.json")["inputs"]["files"]  # type: ignore[index]
    assert Path(files["pqr"]["path"]) == Path("2wcd.pqr")  # type: ignore[index]
    protonation = _read(example / "run-pqr" / "manifest.json")["charge"]["protonation"]  # type: ignore[index]
    assert protonation["source"] == "inputs.pqr"  # type: ignore[index]

    tables = []
    for artefacts in (left, right):
        stored = store.get(PROTONATION_SCHEMA, str(artefacts["protonation"]["hash"]))
        assert stored is not None
        tables.append(ProtonationTable.read(Path(stored.payload[PROTONATION_PAYLOAD])))
    for name in ("frame_offsets", "positions_nm", "charge_e", "radius_nm", "name", "resname"):
        assert (getattr(tables[0], name) == getattr(tables[1], name)).all(), name

    assert left["charge"]["hash"] != right["charge"]["hash"]
    assert left["mesh"]["hash"] == right["mesh"]["hash"]
    fields = [
        store.get(FIELDS_SCHEMA, str(artefacts["charge"]["hash"])) for artefacts in (left, right)
    ]
    assert fields[0] is not None and fields[1] is not None
    for payload in (DEPOSIT_PAYLOAD, CHARGE_PAYLOAD):
        first = Path(fields[0].payload[payload]).read_bytes()
        assert first == Path(fields[1].payload[payload]).read_bytes(), payload


def test_ver46_07_both_switches_are_deviations_and_mesh_an_exclusion_material(ran: Ran) -> None:
    """(f) Exactly the two ``charge.*`` switches listed; ``exclusion`` meshed; new region, mesh."""
    example, walked, _ = ran
    manifest = _read(example / "run-switches" / "manifest.json")
    deviations = manifest["deviations"]
    assert isinstance(deviations, dict)
    assert {entry["path"] for entry in deviations["switches"]} == SWITCHES, deviations
    mesh = manifest["geometry_and_mesh"]
    assert isinstance(mesh, dict)
    assert "exclusion" in mesh["materials"], mesh["materials"]
    left, right = _artefacts(example, "run"), _artefacts(example, "run-switches")
    for name in ("region", "mesh"):
        assert left[name]["hash"] != right[name]["hash"], name
    report = _charge_record(example, "run-switches")["conservation"]
    assert isinstance(report, dict)
    for leg in ("producer", "consumer", "quadrature_agreement"):
        assert abs(report[leg]["relative_error"]) < report[leg]["tolerance"], leg
    assert "run-switches" in walked[-1].stdout


def test_ver46_07_the_exported_charge_is_an_areal_density_declaring_q_net(ran: Ran) -> None:
    """(g) A ``nanopnp/field/v1`` areal charge density declaring the run's ``Q_net`` (IF-05)."""
    example, _, _ = ran
    header = yaml.safe_load((example / "charge.field.yaml").read_text(encoding="utf-8"))
    assert header["schema"] == "nanopnp/field/v1"
    assert header["quantity"] == "areal_charge_density"
    assert (example / header["data"]["path"]).is_file()
    q_net = _charge_record(example, "run")["q_net_e"]
    assert header["q_net_e"] == pytest.approx(q_net, abs=1e-9)


def test_ver46_07_the_resupplied_lattice_is_refused_by_the_quadrature_gate(ran: Ran) -> None:
    """(h) Exit 4, naming the quadrature-agreement check and the supplied field (VAL-15, QR-12)."""
    _, _, refused = ran
    (result,) = refused
    assert result.returncode == 4
    assert "Traceback" not in result.stderr
    assert "under-resolves the supplied field" in result.stderr, result.stderr
    assert re.search(r"between the assembly order and three orders above it", result.stderr)
