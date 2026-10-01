"""VAL-06 at Tier 3, recorded: the ClyA-AS ensemble against APBS (WP29 D14).

The author's PQRs 50-99 are the paper's 50 frames (``.knowledge/04`` §1.1),
supplied through ``inputs.pqr`` beside the ClyA-AS ``structure:``; with
``centre_z_nm = 0`` the model frame is the MD frame (G9), as in
``test_charge_archive``. The case is ``poisson`` at zero bias, at ``P2`` and ``P3``.

Recorded, not gated (section 7.1):

1. the gated construction once, on the frame-averaged deposit: the budget, the
   charge's visibility and the agreement, with :func:`check_report`'s verdict;
2. the recorded leg on every frame, APBS's ``spl4`` and ``smol`` from that frame's
   PQR with the membrane imposed: each frame's ring-mean agreement with ours,
   and the frames' mean of APBS's ring means against ours.

About 75 minutes, most of it 100 APBS runs at 193^3. Skips without the archive;
the box is refused, naming its face, if the ensemble's charge does not fit it.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest
import yaml

from nanopnp.charge.protonation import ProtonationTable
from nanopnp.charge.stage import frame_shift_nm
from nanopnp.core.paths import REFERENCE_DATA_VARIABLE, reference_file
from nanopnp.density.grid import read_grid
from nanopnp.io.case import load_case, resolve
from nanopnp.io.run import run_case
from nanopnp.io.store import Store
from nanopnp.physics.models import PoissonModel
from nanopnp.solve.state import restore, warm_start_payload
from nanopnp.validation.apbs import (
    GatedInputs,
    RecordedInputs,
    Val06Error,
    charge_extent,
    check_report,
    fit_grid,
    gated_leg,
    norms,
    potential_sampler,
    raster_extent,
    raster_from_mesh,
    recorded_leg,
    write_pqr,
)

logger = logging.getLogger(__name__)

ARCHIVED = [
    reference_file(f"prod5_protein_aligned_100ps_{number:02d}.pdb.pqr") for number in range(50, 100)
]
"""The PQRs of the paper's 50 frames, in time order: DCD frames 48-97."""

GEOMETRY = "geometry: {membrane: {centre_z_nm: 0.0}}\n"
"""G9: the MD frame's bilayer centre is z = 0, so the model frame is the stage-1 frame."""

CASE = """\
schema: nanopnp/case/v2
name: {name}
inputs:
  pqr: {{path: {bundle}, format: pqr}}
{block}electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.15
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.0, ground: cis}}
physics:
  model: poisson
  flow: false
  variable_density: false
  inertia: false
  solid_permittivities: {{protein: 20.0, membrane: 3.2}}
numerics: {{continuation: none, elements: {{phi: P{order}, c: P{order}}}}}
outputs: []
"""
"""D1 on the ensemble: ``poisson`` at zero bias on the archived charge."""

pytestmark = pytest.mark.skipif(
    any(path is None for path in ARCHIVED),
    reason=f"prod5_protein_aligned_100ps_50..99.pdb.pqr are not in ${REFERENCE_DATA_VARIABLE}",
)


def _bundle(target: Path) -> Path:
    """Write PQRs 50-99 as one multi-MODEL PQR, one MODEL per frame, as ``test_charge_archive``."""
    with target.open("w", encoding="utf-8") as handle:
        for model, path in enumerate(ARCHIVED, start=1):
            assert path is not None
            handle.write(f"MODEL     {model:>4}\n")
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith(("ATOM", "HETATM")):
                    handle.write(line + "\n")
            handle.write("ENDMDL\n")
    return target


def test_val06_the_ensemble_against_apbs_gated_construction_and_per_frame(
    tmp_path_factory: pytest.TempPathFactory,
    ensemble_store: Store,
    ensemble_case: Callable[..., Path],
    apbs: None,
) -> None:
    """Both legs on the archive; recorded, with the gated construction's verdict logged."""
    root = tmp_path_factory.mktemp("clya-as-val06")
    bundle = _bundle(root / "archived.pqr")
    structured = ensemble_case(root, name="clya-as-val06", geometry=GEOMETRY)
    source = yaml.safe_load(structured.read_text(encoding="utf-8"))
    block = yaml.safe_dump(
        {"structure": source["structure"], "geometry": source["geometry"]}, sort_keys=False
    )
    solved = {}
    for order in (2, 3):
        case = root / f"p{order}.case.yaml"
        case.write_text(
            CASE.format(name=f"clya-as-val06-p{order}", bundle=bundle, block=block, order=order),
            encoding="utf-8",
        )
        result = run_case(case, store=ensemble_store, upto="solve", workspace=root / "work")
        solution = restore(
            warm_start_payload(result.artefacts["solve"]),
            case=load_case(case),
            mesh_artefact=result.artefacts["mesh"],
            charge_artefact=result.artefacts["charge"],
        )
        solved[order] = (case, result, solution)
    case, result, solution = solved[2]
    resolved = resolve(load_case(case))
    model = solution.model
    assert isinstance(model, PoissonModel)
    lattice = read_grid(result.artefacts["charge"].payload["charge"], format="npz")
    grid = fit_grid(
        charge_extent(lattice),
        interface_z_nm=0.5 * resolved.document.geometry.membrane.thickness_nm,  # type: ignore[union-attr]
    )
    r_max, z_min, z_max = raster_extent(grid)
    raster = raster_from_mesh(
        solution.space.mesh,
        model.relative_permittivity(solution) * model.scales.relative_permittivity,
        fluid=model.fluid,
        solids=sorted(model.solid_permittivities),
        r_max_nm=r_max,
        z_min_nm=z_min,
        z_max_nm=z_max,
    )
    ours = potential_sampler(solution, order=2)
    gated = gated_leg(
        GatedInputs(
            lattice=lattice,
            raster=raster,
            ours=ours,
            refined=potential_sampler(solved[3][2], order=3),
            temperature_K=resolved.temperature_K,
            sdie=resolved.electrolyte.permittivity_0,
            structure="ClyA-AS, the archived PQRs 50-99, frame-averaged",
            mesh={"elements": result.artefacts["mesh"].summary["elements"], "orders": [2, 3]},
        ),
        grid,
        root / "apbs",
    )
    try:
        check_report(gated.report)
        verdict = "passes"
    except Val06Error as error:
        verdict = f"fails: {error}"
    logger.info(
        "VAL-06 Tier 3, the gated construction on the ensemble %s:\n%s",
        verdict,
        json.dumps(gated.report.model_dump(), indent=2),
    )

    table = ProtonationTable.read(result.artefacts["protonation"].payload["protonation"])
    shift = frame_shift_nm(resolved)
    means = []
    per_frame = []
    for frame in range(table.frames):
        rows = slice(int(table.frame_offsets[frame]), int(table.frame_offsets[frame + 1]))
        positions = np.array(table.positions_nm[rows], dtype=np.float64, copy=True)
        positions[:, 2] -= shift
        pqr = write_pqr(
            root / f"frame-{frame:02d}.pqr", positions, table.charge_e[rows], table.radius_nm[rows]
        )
        report, sampled = recorded_leg(
            RecordedInputs(
                pqr=pqr,
                raster=raster,
                ours=ours,
                temperature_K=resolved.temperature_K,
                sdie=resolved.electrolyte.permittivity_0,
                pdie=20.0,
                imposed={"membrane": 3.2},
                structure=f"ClyA-AS, archived PQR {50 + frame}",
            ),
            grid,
            root / "apbs" / f"frame-{frame:02d}",
            gated.probes,
        )
        per_frame.append(report.agreement.model_dump())
        means.append(sampled["mean"])
        reference, axis = sampled["ours"], sampled["axis"]
    averaged = np.mean(means, axis=0)
    found = norms(averaged - reference, reference, axis)
    logger.info(
        "VAL-06 Tier 3, the recorded leg: per frame %s; the frames' mean of APBS's ring means "
        "against ours %s",
        json.dumps(per_frame),
        found,
    )
    assert len(per_frame) == len(ARCHIVED)
