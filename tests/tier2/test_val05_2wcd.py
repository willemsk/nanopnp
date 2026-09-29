"""VAL-05, the 2WCD leg: the vendored structure against the reference polygon (WP22 D5).

The root conftest's ``prepared_2wcd`` runs through stages 1 to 5 at the defaults,
registered to the MD frame by its C-alpha centroid (D6), and its model-frame
polygon is compared with the delivered 185-vertex table on the 282 D2 planes.
The D5 tolerances are the assertion: ``|ε_G| <= 10 %``, ``|Δr_c| <= 0.1 nm``,
rms ``<= 0.2 nm`` (author ruling 14; ``SPECIFICATION.md`` §7.4 NOTE on VAL-05).
The isolevel sweep's ``ε_G`` must be strictly increasing over the levels that
pass (D8), a property of nested superlevel sets rather than a tolerance.

Everything else is recorded, not gated, and logged at INFO as YAML (D13): the
attribution to the reference's construction (D7), the rms-optimal offset (D6),
one frozen case's conductance on the generated mesh against the fixture's (D9),
the default-size mesh against the reference figures (D10), and the stage-3
variance (D11). The module runs on its own store, as ``test_contour_2wcd.py``
does, because ``--dist loadfile`` may place the two on different workers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pytest
import yaml

from nanopnp.core.paths import profile_file
from nanopnp.geometry.contour import PAYLOAD_NAME as CONTOUR_PAYLOAD
from nanopnp.geometry.region import PAYLOAD_NAME as REGION_PAYLOAD
from nanopnp.geometry.region import read_region, to_model_frame
from nanopnp.io.run import RunResult, run_case
from nanopnp.io.store import Store
from nanopnp.mesh.profile import load_profile
from nanopnp.structure.ensemble import PAYLOAD_NAME as ENSEMBLE_PAYLOAD
from nanopnp.structure.ensemble import AlignedEnsemble
from nanopnp.validation.geometry import (
    ISOLEVELS,
    ProfileComparison,
    attribute_to_construction,
    calpha_centroid_z_nm,
    compare_profiles,
    register_by_centroid,
    rms_optimal_offset,
    sweep_isolevels,
    zero_crossing,
)

if TYPE_CHECKING:
    from conftest import Prepared2WCD

logger = logging.getLogger(__name__)

REFERENCE_TRIANGLES = 120_917
"""The reference COMSOL mesh's element count (section 5.2.2)."""

REFERENCE_MIN_QUALITY = 0.6378
"""Its minimum element quality, by a measure the model report does not state (``.knowledge/09``)."""

REFERENCE_MEAN_QUALITY = 0.9765
"""Its mean element quality, by the same unstated measure."""

FROZEN_SIZE_SCALE = 2.0
"""D9's ``size_scale`` at Tier 2, on both meshes, so they are like for like."""

STRUCTURE = """\
structure:
  source: {{path: {pdb}}}
  symmetry: {{point_group: C12}}
"""

GEOMETRY_CASE = """\
schema: nanopnp/case/v2
name: 2wcd-val05
{structure}{geometry}electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.15
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: epnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
"""

FROZEN_CASE = """\
schema: nanopnp/case/v2
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
  solid_permittivities: {{protein: 20.0, membrane: 3.2}}
numerics:
  continuation: none
  stabilisation: none
  mesh: {{size_scale: {size_scale}}}
outputs: [current]
"""
"""D9: uncharged, so G is geometric; 1 M, +50 mV, ground *cis*, every correction ``none``."""


def as_yaml(record: object) -> str:
    """Return a pydantic record as YAML, the form D13 logs it in."""
    return yaml.safe_dump(record.model_dump(mode="json"), sort_keys=False)  # type: ignore[attr-defined]


@dataclass(frozen=True)
class Walked:
    """2WCD through stage 5 at the D6 registration, and the comparison of its polygon."""

    root: Path
    store: Store
    structure: str
    geometry: str
    centre_z_nm: float
    centroid_z_nm: float
    stage1: RunResult
    region: RunResult
    stage4: np.ndarray
    """Stage 4's polygon, in the stage-1 frame."""
    ours: np.ndarray
    """Stage 5's polygon, in the model frame."""
    comparison: ProfileComparison
    """The comparison on the planes both polygons cross; the gated test applies D2's rule itself,
    so a plane missed outside the tip band fails that test and leaves the records to run."""


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def reference() -> np.ndarray:
    """Return the delivered 185-vertex polygon, in the model frame."""
    return load_profile(profile_file("clya_reference_profile")).as_array()


@pytest.fixture(scope="module")
def walked(
    prepared_2wcd: Prepared2WCD, tmp_path_factory: pytest.TempPathFactory, reference: np.ndarray
) -> Walked:
    """Run stages 1-4, register by the C-alpha centroid (D6), then stage 5, and compare (D2, D3)."""
    root = tmp_path_factory.mktemp("2wcd-val05")
    store = Store(root / "store")
    structure = STRUCTURE.format(pdb=prepared_2wcd.path)
    case = _write(
        root / "contour.case.yaml", GEOMETRY_CASE.format(structure=structure, geometry="")
    )
    stage1 = run_case(case, store=store, upto="contour", write=False)
    ensemble = AlignedEnsemble.read(stage1.artefacts["structure"].payload[ENSEMBLE_PAYLOAD])
    atoms = {"name": ensemble.name, "resid": ensemble.resid, "chain": ensemble.chain}
    centroid = calpha_centroid_z_nm(ensemble.positions_nm, **atoms)
    centre = register_by_centroid(ensemble.positions_nm, **atoms)

    geometry = f"geometry: {{membrane: {{centre_z_nm: {centre!r}}}}}\n"
    case = _write(
        root / "region.case.yaml", GEOMETRY_CASE.format(structure=structure, geometry=geometry)
    )
    region = run_case(case, store=store, upto="region", write=False)
    assert {"structure", "density", "symmetry", "contour"} <= {
        record.name for record in region.stages if record.cached
    }
    record = read_region(region.artefacts["region"].payload[REGION_PAYLOAD])
    stage4 = load_profile(stage1.artefacts["contour"].payload[CONTOUR_PAYLOAD]).as_array()
    # D2: the compared polygon is stage 5's, and it is stage 4's moved by centre_z_nm.
    assert np.array_equal(record.points(), to_model_frame(stage4, centre))
    assert record.membrane.centre_z_nm == centre
    logger.info(
        "2WCD stages 1-5: %s s; C-alpha centroid z = %.4f nm in the stage-1 frame, "
        "centre_z_nm = %.4f nm",
        {entry.name: round(entry.seconds, 2) for entry in region.stages},
        centroid,
        centre,
    )
    return Walked(
        root=root,
        store=store,
        structure=structure,
        geometry=geometry,
        centre_z_nm=centre,
        centroid_z_nm=centroid,
        stage1=stage1,
        region=region,
        stage4=stage4,
        ours=record.points(),
        comparison=compare_profiles(record.points(), reference, strict=False),
    )


def test_val05_2wcd_against_the_reference_polygon(walked: Walked, reference: np.ndarray) -> None:
    """D5: |ε_G| <= 10 %, |Δr_c| <= 0.1 nm and rms <= 0.2 nm; every plane off the tips crossed.

    Predicted by the plan's prototype: ε_G = -8.08 %, Δr_c = -0.0205 nm, rms
    0.158 nm (Design §4). The attribution (D7), the conditioning's share and the
    rms-optimal offset (D6) are recorded beside the verdict.
    """
    comparison = compare_profiles(walked.ours, reference)
    logger.info("VAL-05, 2WCD leg:\n%s", as_yaml(comparison))
    assert comparison.planes == 282
    # compare_profiles is strict: an uncrossed plane outside the tip band has already failed.
    assert comparison.compared_planes >= 282 - 4

    attribution = attribute_to_construction(walked.ours, reference, comparison)
    logger.info(
        "VAL-05, 2WCD leg, attribution to the reference's construction (D7):\n%s",
        as_yaml(attribution),
    )
    conditioning = walked.stage1.artefacts["contour"].summary["conditioning"]
    logger.info("2WCD conditioning's lumen change (D7): %s", conditioning["lumen_change"])  # type: ignore[index]

    fitted = rms_optimal_offset(walked.stage4, reference, centre_nm=walked.centre_z_nm)
    logger.info(
        "2WCD registration (D6): centroid %.4f nm, centre_z_nm %.4f nm; rms-optimal offset "
        "%.4f nm (%+.4f nm from the centroid's, a diagnostic never used)",
        walked.centroid_z_nm,
        walked.centre_z_nm,
        fitted,
        fitted - walked.centre_z_nm,
    )
    comparison.check("2wcd")


def test_val05_2wcd_isolevel_sweep_is_strictly_increasing(
    walked: Walked, reference: np.ndarray
) -> None:
    """D8: ε_G strictly increasing over the passing isolevels; the zero crossing recorded.

    The union density's superlevel sets are nested, so the raw lumen cannot
    narrow as the level rises; the measured steps (2.0-5.3 pp) dwarf the
    conditioning's 0.01 nm rms, so a violation is a sign or ordering error.
    """
    case = _write(
        walked.root / "sweep.case.yaml",
        GEOMETRY_CASE.format(structure=walked.structure, geometry=walked.geometry),
    )
    points = sweep_isolevels(
        case,
        store=walked.store,
        reference=reference,
        workspace=walked.root / "sweep",
    )
    assert [point.isolevel for point in points] == list(ISOLEVELS)
    for point in points:
        if point.comparison is None:
            logger.info("isolevel %g: refused: %s", point.isolevel, point.refusal)
            continue
        c = point.comparison
        logger.info(
            "isolevel %.2f: ε_G %+.2f %%, exact %+.2f %%, mean Δ %+.4f nm, rms %.4f nm, "
            "r_c %.4f nm at z = %.3f nm, %d vertices, %d planes compared, uncrossed %s",
            point.isolevel,
            100 * c.conductance_deviation,
            100 * c.conductance_ratio_exact,
            c.mean_nm,
            c.rms_nm,
            c.constriction_ours.value_nm,
            c.constriction_ours.z_nm,
            point.vertices,
            c.compared_planes,
            [round(z, 3) for z in c.uncrossed_planes_nm],
        )
    default = next(point for point in points if point.isolevel == 0.25)
    assert default.comparison == walked.comparison
    passing = [p.comparison.conductance_deviation for p in points if p.comparison is not None]
    assert all(b > a for a, b in pairwise(passing)), passing
    logger.info("2WCD ε_G crosses zero at isolevel %s (a diagnostic, D8)", zero_crossing(points))


def test_val05_2wcd_mesh_against_the_reference_figures(walked: Walked) -> None:
    """D10, recorded: the default-size mesh beside the reference's 120,917, 0.6378 and 0.9765."""
    case = _write(
        walked.root / "mesh.case.yaml",
        GEOMETRY_CASE.format(structure=walked.structure, geometry=walked.geometry),
    )
    result = run_case(case, store=walked.store, upto="mesh", write=False)
    mesh = result.artefacts["mesh"].summary
    quality = mesh["quality"]
    logger.info(
        "2WCD mesh at the default sizes (D10): %d triangles (reference %d), min SICN %.4f, "
        "mean SICN %.4f, min gamma %.4f, mean gamma %.4f (reference min %.4f, mean %.4f, by a "
        "measure the model report does not state); %.2f s",
        mesh["elements"],
        REFERENCE_TRIANGLES,
        quality["min_sicn"],  # type: ignore[index]
        quality["mean_sicn"],  # type: ignore[index]
        quality["min_gamma"],  # type: ignore[index]
        quality["mean_gamma"],  # type: ignore[index]
        REFERENCE_MIN_QUALITY,
        REFERENCE_MEAN_QUALITY,
        next(entry.seconds for entry in result.stages if entry.name == "mesh"),
    )
    reduction = result.artefacts["symmetry"].summary
    for quantity, where in reduction["maximum"].items():  # type: ignore[union-attr]
        logger.info(
            "2WCD stage 3 (D11): largest %s %.4g at r = %.2f nm, z = %.2f nm",
            quantity,
            where["value"],
            where["r_nm"],
            where["z_nm"],
        )


def test_val05_2wcd_frozen_case_conductance(walked: Walked) -> None:
    """D9, recorded: G on the generated mesh against the fixture's, beside ε_G.

    Uncharged at 1 M, so G is geometric and ``ε_G`` is its bulk-resistor proxy;
    access resistance dilutes the difference, and by how much is the record.
    """
    generated = run_case(
        _write(
            walked.root / "frozen-generated.case.yaml",
            FROZEN_CASE.format(
                name="2wcd-frozen",
                source=walked.structure + walked.geometry,
                size_scale=FROZEN_SIZE_SCALE,
            ),
        ),
        store=walked.store,
        workspace=walked.root / "frozen-generated",
    )
    fixture = run_case(
        _write(
            walked.root / "frozen-fixture.case.yaml",
            FROZEN_CASE.format(
                name="fixture-frozen",
                source=f"inputs:\n  profile: {{path: {profile_file('clya_reference_profile')}}}\n",
                size_scale=FROZEN_SIZE_SCALE,
            ),
        ),
        store=walked.store,
        workspace=walked.root / "frozen-fixture",
    )
    g_generated = float(generated.quantities["conductance_S"])  # type: ignore[arg-type]
    g_fixture = float(fixture.quantities["conductance_S"])  # type: ignore[arg-type]
    assert g_generated > 0.0 and g_fixture > 0.0
    logger.info(
        "2WCD frozen case (D9) at size_scale %g: G generated %.6e S (%d triangles), fixture "
        "%.6e S (%d triangles); G_gen/G_ref - 1 = %+.2f %% against ε_G %+.2f %% (exact series "
        "%+.2f %%); solve %.1f s and %.1f s",
        FROZEN_SIZE_SCALE,
        g_generated,
        generated.artefacts["mesh"].summary["elements"],
        g_fixture,
        fixture.artefacts["mesh"].summary["elements"],
        100 * (g_generated / g_fixture - 1.0),
        100 * walked.comparison.conductance_deviation,
        100 * walked.comparison.conductance_ratio_exact,
        sum(entry.seconds for entry in generated.stages),
        sum(entry.seconds for entry in fixture.stages),
    )
