"""VAL-01, VAL-02 and VAL-04 at Tier 3: the four-rung ladder, against the archive and itself."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from pathlib import Path

import pytest

from nanopnp.core.paths import REFERENCE_DATA_VARIABLE, reference_data_root
from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.solve.continuation import default_ladder, run_ladder
from nanopnp.validation.attribution import (
    IDENTITY_TOLERANCE,
    LADDER,
    RungOutcome,
    attribute,
    reference_error,
    write_report,
)
from nanopnp.validation.compare import (
    compare_fields,
    compare_quantities,
    probe_domains,
    sample_on_probe,
    zero_reference_quantities,
)
from nanopnp.validation.comsol import (
    ARCHIVE_NAME,
    GOLDEN_SCHEMA,
    GoldenManifest,
    export_golden,
    field_unit,
    load_golden,
)
from nanopnp.validation.probe import PROBE_SCHEMA, ProbeGrid, load_probe, loads_probe
from nanopnp.validation.runs import reopen

logger = logging.getLogger(__name__)

PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=13.0, reservoir_radius_nm=25.0
)
CONCENTRATION_M = 0.5
BIAS_V = 0.05
SURFACE_CHARGE_C_M2 = -0.05

PROBE_TEXT = f"""
schema: {PROBE_SCHEMA}
name: ver11-benchmark
patches:
  - {{name: lumen, r_nm: [0.0, 1.5], z_nm: [-6.0, 6.0], n_r: 7, n_z: 13}}
  - {{name: bulk, r_nm: [0.1, 10.1], z_nm: [10.0, 20.0], n_r: 11, n_z: 6}}
"""

REFERENCE_PROBE = Path("docs/validation/probes/clya-reference.probe.yaml")
FROZEN_CASES = Path("docs/validation/cases")
ARCHIVE_SUBDIR = "comsol"

GENERATING_RUNG = len(LADDER) - 1


def _order(element: str) -> int:
    return int(element[1:])


@pytest.fixture(scope="module")
def solved_ladder():
    # The flow stays on: rungs 2 and 3 differ only in the velocity and pressure spaces.
    mesh = PORE.generate(maxh_nm=5.0, wall_h_nm=0.4)
    solutions = []
    for rung in LADDER:
        stages = default_ladder(
            mesh,
            concentration_M=CONCENTRATION_M,
            bias_V=BIAS_V,
            surface_charge_C_m2=SURFACE_CHARGE_C_M2,
            solid_permittivities={"membrane": 2.0},
            start_concentration_M=None,
            charge_steps=2,
            stabilisation=rung.stabilisation,
            velocity_order=_order(rung.velocity_element),
            pressure_order=_order(rung.pressure_element),
        )
        result = run_ladder(stages)
        logger.info(
            "rung %d %s: %d rungs, %d iterations, %.1f s",
            rung.index,
            rung.name,
            len(result.rungs),
            result.iterations,
            result.seconds,
        )
        solutions.append(result.solution)

    document = loads_probe(PROBE_TEXT)
    grid = ProbeGrid.on_mesh(document, mesh, probe_domains(solutions[0]))
    sampled = [
        sample_on_probe(solution, grid, scales=solution.model.scales) for solution in solutions
    ]
    return document, grid, solutions, sampled


def test_val01_full_ladder_against_a_self_golden(solved_ladder, tmp_path: Path) -> None:
    document, grid, _, sampled = solved_ladder

    manifest = GoldenManifest.model_validate(
        {
            "schema": GOLDEN_SCHEMA,
            "case": "ver11-benchmark",
            "case_hash": "b" * 64,
            "probe": document.name,
            "probe_hash": document.hash,
            "refinement": "published",
            "source": "self",
            "comsol_version": "nanopnp (self-golden, no COMSOL)",
            "model_file": f"{LADDER[GENERATING_RUNG].name} on the VER-11 benchmark pore",
            "export_date": "2026-09-18",
            "fields": {
                name: {"expression": name, "unit": field_unit(name)}
                for name in sorted(sampled[GENERATING_RUNG])
            },
            "current_boundary": "the NUM-24 domain indicator, not a boundary",
            "current_sign_reference": "cis",
            "quantities": {"bias_V": BIAS_V, "current_A": 1.0},
        }
    )
    export_golden(sampled[GENERATING_RUNG], manifest, tmp_path)
    golden = load_golden(tmp_path)
    assert golden.source == "self"

    outcomes = [
        RungOutcome(
            rung=rung,
            golden_hash=golden.hash,
            probe_hash=golden.manifest.probe_hash,
            case_hash=golden.manifest.case_hash,
            fields=compare_fields(sampled[rung.index], golden, grid),
            quantities=compare_quantities({}, golden.quantities),
        )
        for rung in LADDER
    ]
    report = attribute(
        outcomes,
        case="ver11-benchmark",
        golden=golden,
        sampled_fields=sorted(sampled[GENERATING_RUNG]),
    )
    report.check_identity()
    assert report.golden_source == "self"
    assert "tests the harness and nothing else" in report.markdown()

    for entry in report.attributions:
        assert entry.residual == 0.0, (
            f"{entry.key}: the generating rung is not at zero distance from its own golden"
        )
        assert abs(entry.identity_residual()) <= IDENTITY_TOLERANCE
        assert entry.verdict() == "reference-unbounded"
        logger.info(
            "%s: total %.4e transport %+.4e flow %+.4e pair %+.4e resid %.4e",
            entry.key,
            entry.total,
            entry.transport,
            entry.flow,
            entry.pair,
            entry.residual,
        )

    json_path, markdown = write_report(report, tmp_path)
    assert json_path.is_file() and markdown.is_file()
    assert "golden_source" in json_path.read_text(encoding="utf-8")


def test_val01_val02_val04_attribution_against_the_archive() -> None:
    import os

    root = reference_data_root()
    if root is None:
        pytest.skip(
            f"{REFERENCE_DATA_VARIABLE} is unset, so there is no archive to compare against"
        )

    document = load_probe(REFERENCE_PROBE)
    cases = sorted(path.name.split(".case")[0] for path in FROZEN_CASES.glob("*.case.yaml"))
    available = [
        (name, root / ARCHIVE_SUBDIR / name / "published")
        for name in cases
        if (root / ARCHIVE_SUBDIR / name / "published" / ARCHIVE_NAME).is_file()
    ]
    if not available:
        pytest.skip(
            f"{root / ARCHIVE_SUBDIR} holds no ingested golden for any of {', '.join(cases)}; "
            "run 'nanopnp validate ingest-golden' against the delivered exports first"
        )

    runs = os.environ.get("NANOPNP_LADDER_RUNS")
    if not runs:
        pytest.skip(
            "NANOPNP_LADDER_RUNS is unset, so the ladder's twenty members have not been "
            "dispatched here. Run 'nanopnp sweep run' on docs/validation/comsol-ladder.sweep.yaml "
            "and point it at that sweep directory"
        )

    from nanopnp.pipeline.case import resolve
    from nanopnp.sweep.collect import read_members
    from nanopnp.sweep.plan import PLAN_FILENAME, read_plan
    from nanopnp.validation.comsol import case_identity

    plan = read_plan(Path(runs) / PLAN_FILENAME)
    members = {member.index: member for member in read_members(Path(runs))}

    for name, directory in available:
        golden = load_golden(directory)
        golden.check_probe(document)
        refined = root / ARCHIVE_SUBDIR / name / "refined_1"
        outcomes: dict[int, RungOutcome] = {}
        sampled_fields: list[str] = []
        rung_grid: ProbeGrid | None = None
        for index, member in sorted(members.items()):
            if member.status != "ok" or member.directory is None:
                continue
            run = reopen(member.directory)
            if case_identity(resolve(run.case), recorded=run.upstream) != golden.manifest.case_hash:
                continue
            rung = plan.point(index).coordinates[0]
            grid = rung_grid = ProbeGrid.on_mesh(
                document, run.solution.space.mesh, probe_domains(run.solution)
            )
            sampled = sample_on_probe(run.solution, grid, scales=run.scales)
            sampled_fields = sorted(sampled)
            outcomes[rung] = RungOutcome(
                rung=LADDER[rung],
                golden_hash=golden.hash,
                probe_hash=golden.manifest.probe_hash,
                case_hash=golden.manifest.case_hash,
                fields=compare_fields(sampled, golden, grid),
                quantities=compare_quantities(run.quantities, golden.quantities),
                stabilisation_currents_A=_currents(run.quantities),
                zero_reference=zero_reference_quantities(run.quantities, golden.quantities),
            )
        if len(outcomes) != len(LADDER):
            pytest.skip(
                f"{name}: the sweep holds {len(outcomes)} of {len(LADDER)} rungs, so the deltas "
                "would be differences between rungs that are not adjacent"
            )
        assert rung_grid is not None
        # Over a rung's own masks, which drop the margin band E_k is taken without.
        errors = (
            reference_error(golden, load_golden(refined), rung_grid)
            if (refined / ARCHIVE_NAME).is_file()
            else None
        )
        report = attribute(
            [outcomes[index] for index in range(len(LADDER))],
            case=name,
            golden=golden,
            reference_errors=errors,
            sampled_fields=sampled_fields,
        )
        write_report(report, Path(runs))
        logger.info("%s", report.markdown())


def _currents(recorded: Mapping[str, object]) -> Mapping[str, float] | None:
    value = recorded.get("stabilisation_currents_A")
    return dict(value) if isinstance(value, dict) else None
