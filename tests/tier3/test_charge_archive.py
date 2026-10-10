"""VER-01, VER-02 and VAL-15 at Tier 3, recorded: the author's archived PQRs deposited (WP28).

PQRs 50-99 are the paper's 50 frames (``.knowledge/04`` §1.1). Supplied through
``inputs.pqr`` beside the ClyA-AS ``structure:``, each frame registers to its stage-1
frame (WP27), and with ``centre_z_nm = 0`` the model frame is VAL-05's, the MD
frame (G9). Recorded, not gated (section 7.1):

1. stage 7's report on the generated mesh: both legs, the quadrature agreement,
   the worst plane of each side, the solid share and ``Q_net``;
2. the export against the delivered ``rhoq_pore``: planar integrals, the rms and
   largest field difference, and the 12 planes, split through the reference's
   construction rebuilt from the same PQRs (G4, :mod:`nanopnp.validation.charge`)
   into the construction (ours against G4 on the registered atoms), the
   registration (G4 registered against G4 on the archive as printed) and the
   reproduction (G4 as printed against the table);
3. the export read back through ``inputs.charge`` on the WP8 reference mesh: the
   consumer path's report and the gates' verdict, beside VAL-15's 9.9e-3 for the
   table on the same mesh;
4. one frozen case, charged: ``G`` and ``t+`` on the pipeline's mesh and charge,
   on the reference mesh with the same deposit, and the table's verdict on the
   reference mesh, which VAL-15 says its quadrature gate refuses.

Skips without the PQRs, the trajectory or the table.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import yaml

from nanopnp.charge.fields import (
    ChargeFieldError,
    check_conservation,
    conservation,
    load_field,
)
from nanopnp.charge.kernel import SourceAtoms, source_atoms
from nanopnp.charge.pqr import read_pqr
from nanopnp.charge.protonation import ProtonationTable
from nanopnp.charge.stage import export_charge
from nanopnp.core.paths import REFERENCE_DATA_VARIABLE, profile_file, reference_file
from nanopnp.density.grid import read_grid
from nanopnp.io.store import Store
from nanopnp.mesh.reference import ReferenceGeometry
from nanopnp.numerics.measures import AXISYMMETRIC
from nanopnp.pipeline.run import (
    RunResult,
    run_case,
)
from nanopnp.post.qoi import transport_number
from nanopnp.validation.charge import AreaComparison, compare_areal, reference_construction

logger = logging.getLogger(__name__)

ARCHIVED = [
    reference_file(f"prod5_protein_aligned_100ps_{number:02d}.pdb.pqr") for number in range(50, 100)
]
"""The PQRs of the paper's 50 frames, in time order: DCD frames 48-97."""

TABLE = reference_file("prod5_clya_charge")
"""The delivered ``rhoq_pore`` table (VAL-15)."""

ARCHIVED_Q_NET_E = -72
"""The archive's ``Q_net`` (``.knowledge/04`` §3.1)."""

SHARPNESS = 0.5
"""The reference's sharpness, which is the validated default (``.knowledge/04`` §3)."""

PLANE_SMOOTHING_NM = 0.5
"""``s`` of the per-plane comparisons, the producer path's own (D6)."""

GEOMETRY = "geometry: {membrane: {centre_z_nm: 0.0}}\n"
"""G9: the MD frame's bilayer centre is z = 0, so the model frame is the stage-1 frame."""

FROZEN_CASE = """\
schema: nanopnp/case/v0.5
name: {name}
{source}electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 1.0
  parameters: willems2020_nacl
  corrections:
    diffusivity:  {{model: none}}
    mobility:     {{model: none}}
    viscosity:    {{model: none}}
    permittivity: {{model: none}}
    density:      {{model: none}}
    steric:       {{model: none}}
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics:
  model: pnp
  flow: false
  variable_density: false
  inertia: false
  solid_permittivities: {{protein: 20.0, membrane: 3.2}}
numerics:
  continuation: none
  stabilisation: none
outputs: [current]
"""
"""WP22 D9's frozen case, charged: 1 M, +50 mV, ground *cis*, every correction ``none``."""

needs_archive = pytest.mark.skipif(
    any(path is None for path in ARCHIVED) or TABLE is None,
    reason=(
        f"prod5_protein_aligned_100ps_50..99.pdb.pqr or prod5_clya_charge are not in "
        f"${REFERENCE_DATA_VARIABLE}"
    ),
)

pytestmark = needs_archive


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _bundle(target: Path) -> Path:
    """Write PQRs 50-99 as one multi-MODEL PQR, one MODEL per frame (WP27)."""
    with target.open("w", encoding="utf-8") as handle:
        for model, path in enumerate(ARCHIVED, start=1):
            assert path is not None
            handle.write(f"MODEL     {model:>4}\n")
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith(("ATOM", "HETATM")):
                    handle.write(line + "\n")
            handle.write("ENDMDL\n")
    return target


def _table_document(target: Path) -> Path:
    """Write the header the delivered table is read through (``test_reference_charge_map``)."""
    return _write(
        target,
        "schema: nanopnp/field/v1\n"
        "name: rhoq_pore\n"
        "quantity: areal_charge_density\n"
        "units: e/m^2\n"
        f"q_net_e: {float(ARCHIVED_Q_NET_E)}\n"
        "provenance:\n"
        "  source: prod5_clya_charge, the COMSOL model's own interpolation table\n"
        "  citation: Willems et al., Nanoscale 12, 16775-16795 (2020), ESI\n"
        f"data: {{path: {TABLE}, format: comsolgrid}}\n"
        "grid:\n"
        "  origin_nm: [0.0, -3.5]\n"
        "  spacing_nm: [0.005, 0.005]\n"
        "  shape: [1401, 3401]\n",
    )


def _printed_atoms() -> SourceAtoms:
    """Return the archive's charged atoms as printed, unregistered, in the MD frame."""
    frames = [read_pqr(path)[0] for path in ARCHIVED if path is not None]
    rows: dict[str, list[np.ndarray]] = {"r": [], "z": [], "w": [], "q": [], "frame": []}
    for index, frame in enumerate(frames):
        charged = frame.charge_e != 0.0
        positions = frame.positions_A[charged] / 10.0
        rows["r"].append(np.hypot(positions[:, 0], positions[:, 1]))
        rows["z"].append(positions[:, 2])
        rows["w"].append(SHARPNESS * frame.radius_A[charged] / 10.0)
        rows["q"].append(frame.charge_e[charged] / len(frames))
        rows["frame"].append(np.full(int(charged.sum()), index, dtype=np.int64))
    joined = {key: np.concatenate(value) for key, value in rows.items()}
    return SourceAtoms(
        r_nm=joined["r"],
        z_nm=joined["z"],
        width_nm=joined["w"],
        weight_e=joined["q"],
        frame=joined["frame"],
        atom=np.arange(joined["r"].size, dtype=np.int64),
        frames=len(frames),
        shift_z_nm=0.0,
    )


def _record(comparison: AreaComparison) -> str:
    return yaml.safe_dump(comparison.model_dump(mode="json"), sort_keys=False)


@pytest.fixture(scope="module")
def charged(
    tmp_path_factory: pytest.TempPathFactory,
    ensemble_store: Store,
    ensemble_case: Callable[..., Path],
) -> tuple[Path, Path, RunResult]:
    """Return the bundle, the frozen case on the generated mesh, and its walk to the report."""
    root = tmp_path_factory.mktemp("clya-as-charge")
    bundle = _bundle(root / "archived.pqr")
    structured = ensemble_case(root, name="clya-as-charged", geometry=GEOMETRY)
    source = yaml.safe_load(structured.read_text(encoding="utf-8"))
    block = yaml.safe_dump(
        {"structure": source["structure"], "geometry": source["geometry"]}, sort_keys=False
    )
    case = _write(
        root / "frozen-pipeline.case.yaml",
        FROZEN_CASE.format(
            name="clya-as-frozen-pipeline",
            source=f"inputs:\n  pqr: {{path: {bundle}, format: pqr}}\n{block}",
        ),
    )
    result = run_case(case, store=ensemble_store, workspace=root / "pipeline")
    return bundle, case, result


def _frozen(result: RunResult) -> dict[str, Any]:
    currents = result.quantities["currents_A"]
    assert isinstance(currents, dict)
    return {
        "conductance_S": float(result.quantities["conductance_S"]),  # type: ignore[arg-type]
        "t_plus": transport_number(currents, ["Na+"]),
        "elements": result.artefacts["mesh"].summary["elements"],
    }


def test_ver01_the_archived_pqrs_deposit_on_the_generated_mesh(charged) -> None:
    """Both legs, the quadrature agreement and the worst plane of each side; recorded."""
    _, _, result = charged
    record = result.artefacts["charge"].summary["charge"]
    conservation_record = record["conservation"]  # type: ignore[index]
    logger.info(
        "VER-01/VER-02 Tier 3, archived PQRs 50-99 on the generated mesh (%d elements):\n%s",
        result.artefacts["mesh"].summary["elements"],
        yaml.safe_dump(
            {
                "q_net_e": record["q_net_e"],  # type: ignore[index]
                "conservation": conservation_record,
                "solid_share": record["solid_share"],  # type: ignore[index]
                "material_charge_e": record["material_charge_e"],  # type: ignore[index]
                "seconds": next(stage.seconds for stage in result.stages if stage.name == "charge"),
            },
            sort_keys=False,
        ),
    )
    assert round(record["q_net_e"]) == ARCHIVED_Q_NET_E  # type: ignore[index]


def test_val15_the_export_against_the_delivered_table_split_through_g4(
    charged, tmp_path: Path
) -> None:
    """Ours against ``rhoq_pore``, and the three parts of the difference; recorded."""
    _, _, result = charged
    stage7 = result.artefacts["charge"]
    ours = read_grid(stage7.payload["charge"], format="npz")
    table = load_field(_table_document(tmp_path / "rhoq_pore.yaml")).grid
    registered_table = ProtonationTable.read(result.artefacts["protonation"].payload["protonation"])
    registered = source_atoms(registered_table, sharpness=SHARPNESS)
    g4_registered = reference_construction(registered, table)
    g4_printed = reference_construction(_printed_atoms(), table)
    planes = registered.planes_nm()
    legs = {
        "total (ours - table)": compare_areal(ours, table, planes, smoothing_nm=PLANE_SMOOTHING_NM),
        "construction (ours - G4 registered)": compare_areal(
            ours, g4_registered, planes, smoothing_nm=PLANE_SMOOTHING_NM
        ),
        "registration (G4 registered - G4 printed)": compare_areal(
            g4_registered, g4_printed, planes, smoothing_nm=PLANE_SMOOTHING_NM
        ),
        "reproduction (G4 printed - table)": compare_areal(
            g4_printed, table, planes, smoothing_nm=PLANE_SMOOTHING_NM
        ),
    }
    for name, comparison in legs.items():
        logger.info("VAL-15 Tier 3, %s:\n%s", name, _record(comparison))
    assert all(np.isfinite(comparison.rms_difference_C_m2) for comparison in legs.values())


def test_val15_the_export_read_back_on_the_reference_mesh(charged, tmp_path: Path) -> None:
    """``inputs.charge`` on the WP8 reference mesh: the consumer report and its verdict."""
    _, _, result = charged
    export_charge(result.artefacts["charge"], tmp_path / "clya-as.yaml")
    field = load_field(tmp_path / "clya-as.yaml")
    mesh = ReferenceGeometry.from_fixture().generate(check_quality=False)
    report = conservation(field, mesh, AXISYMMETRIC)
    try:
        check_conservation(report)
        verdict = "passed"
    except ChargeFieldError as error:
        verdict = f"refused: {error}"
    logger.info(
        "VAL-15 Tier 3: our export on the reference mesh: producer %.3e, consumer %.3e, "
        "quadrature %s, against the table's consumer 9.868e-3 on the same mesh; %s",
        report.producer_error,
        report.consumer_error,
        report.summary().get("quadrature_agreement"),
        verdict,
    )


def test_val15_the_charged_frozen_case_against_the_reference_mesh(
    charged, ensemble_store: Store, tmp_path: Path
) -> None:
    """``G`` and ``t+`` on the pipeline's mesh, on the reference mesh, and the table's verdict."""
    bundle, _, pipeline = charged
    profile = f"  profile: {{path: {profile_file('clya_reference_profile')}}}\n"
    reference = run_case(
        _write(
            tmp_path / "frozen-reference.case.yaml",
            FROZEN_CASE.format(
                name="clya-as-frozen-reference",
                source=f"inputs:\n  pqr: {{path: {bundle}, format: pqr}}\n{profile}",
            ),
        ),
        store=ensemble_store,
        workspace=tmp_path / "reference",
    )
    document = _table_document(tmp_path / "rhoq_pore.yaml")
    try:
        table = run_case(
            _write(
                tmp_path / "frozen-table.case.yaml",
                FROZEN_CASE.format(
                    name="clya-as-frozen-table",
                    source=f"inputs:\n  charge: {{path: {document}}}\n{profile}",
                ),
            ),
            store=ensemble_store,
            workspace=tmp_path / "table",
        )
        table_record: dict[str, Any] | str = _frozen(table)
    except ChargeFieldError as error:
        table_record = f"refused: {error}"
    ours, theirs = _frozen(pipeline), _frozen(reference)
    logger.info(
        "VAL-16 recorded leg, the charged frozen case (1 M, +50 mV, pnp, flow off):\n%s",
        yaml.safe_dump(
            {
                "pipeline mesh, deposited archive": ours,
                "reference mesh, deposited archive": theirs,
                "reference mesh, delivered table": table_record,
                "G pipeline / G reference - 1": ours["conductance_S"] / theirs["conductance_S"]
                - 1.0,
                "t+ pipeline - t+ reference": ours["t_plus"] - theirs["t_plus"],
            },
            sort_keys=False,
        ),
    )
    assert ours["conductance_S"] > 0.0 and theirs["conductance_S"] > 0.0
