"""Tier 3: the four-rung ladder, against the archive and against ourselves.

VAL-01, VAL-02, VAL-04. **Recorded, not gated** (§7.1, §7.6): §7.4's 1 % and 0.5 %
targets apply only once the matching stabilised mode exists *and* the meshes have
been convergence-matched. WP12 delivered the first; the second is not this
package's to achieve. So nothing here asserts a discrepancy is small. What is
asserted is that the numbers are *attributable*: that four rungs were compared
against one golden on one probe grid with one set of masks, that the deltas
telescope, and that the report says which of them could be a defect.

Two tests, and they answer different questions.

The **archive** test is the real one and it **skips** where
``$NANOPNP_REFERENCE_DATA`` is unset or does not hold the golden. Section 7.1's
NOTE is explicit: an unavailable reference is missing evidence, not a defect, and
a test that failed on one would make the tier unrunnable off the machine that
holds the archive.

The **self-golden** test runs everywhere, and its report carries
``golden_source: self``. It tests the machinery and nothing else — no number it
produces says anything about the reference implementation — and the point of
running the *full* ladder against it is that ``Delta_resid`` is then known in
advance: rung 3 generated the golden, so its distance from it is exactly zero,
and every other rung's distance is a real measurement of what that rung's
configuration costs on this discretisation.
"""

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
    golden_grid,
    probe_domains,
    sample_on_probe,
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
"""Where ``ingest-golden`` is expected to have written under the archive root.

``$NANOPNP_REFERENCE_DATA/comsol/<case>/<refinement>/golden.npz``, which is the
layout ``docs/validation/comsol-export-contract.md`` asks the author for.
"""

GENERATING_RUNG = len(LADDER) - 1
"""The rung a self-golden is made from: the last one, so ``Delta_resid`` vanishes.

``Delta_resid = E_3`` by construction, so making the golden from any other rung
would leave the one delta §7.4's targets apply to as an unpredicted number in a
test whose whole value is that every number in it is predicted.
"""


def _order(element: str) -> int:
    """Return the polynomial degree a ``P<n>`` element name carries."""
    return int(element[1:])


@pytest.fixture(scope="module")
def solved_ladder():
    """Return one converged solution per rung, on one mesh, plus the probe grid.

    Four full ePNP-NS solves. The flow must be *on*: rungs 2 and 3 differ only in
    the velocity and pressure spaces, and a classical truncation that solved no
    flow would make ``Delta_pair`` identically zero for a reason that has nothing
    to do with the discretisation.
    """
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
    """The whole ladder against one of our own solutions: every number predicted.

    ``Delta_resid`` is exactly zero because rung 3 generated the golden. The
    identity telescopes. The report says ``golden_source: self``, which is what
    keeps a reader from mistaking any of it for a statement about COMSOL.

    The other three deltas are **measurements**, recorded and not gated: what the
    transport stabilisation, the flow GLS term and the element pair each cost on
    this benchmark's discretisation. They are logged rather than bounded, because
    bounding them here would be inventing a tolerance §7.4 does not give.
    """
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
    """The ladder on the five frozen cases against the archived COMSOL goldens.

    **Recorded, not gated.** The deltas, ``Delta_ref`` and the verdict are written
    to a report and logged; no threshold is asserted, because §7.4's targets are
    conditional on both of its preconditions and only one of them holds.

    **Skips** where ``$NANOPNP_REFERENCE_DATA`` is unset or holds no golden: an
    unavailable reference is missing evidence, not a defect (§7.1 NOTE).

    It also needs the ladder sweep to have been *run*, because the comparison is
    post-processing and never solves (:mod:`nanopnp.validation.runs`); the run
    directory is named by ``$NANOPNP_LADDER_RUNS``. Without it the archive is
    present and the solves are not, which is again missing evidence.
    """
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

    from nanopnp.io.case import resolve
    from nanopnp.sweep.collect import read_members
    from nanopnp.sweep.plan import PLAN_FILENAME, read_plan
    from nanopnp.validation.comsol import case_identity

    plan = read_plan(Path(runs) / PLAN_FILENAME)
    members = {member.index: member for member in read_members(Path(runs))}

    for name, directory in available:
        golden = load_golden(directory)
        golden.check_probe(document)
        refined = root / ARCHIVE_SUBDIR / name / "refined_1"
        errors = (
            reference_error(golden, load_golden(refined), golden_grid(document, golden))
            if (refined / ARCHIVE_NAME).is_file()
            else None
        )
        outcomes: dict[int, RungOutcome] = {}
        sampled_fields: list[str] = []
        for index, member in sorted(members.items()):
            if member.status != "ok" or member.directory is None:
                continue
            run = reopen(member.directory)
            if case_identity(resolve(run.case)) != golden.manifest.case_hash:
                continue
            rung = plan.point(index).coordinates[0]
            grid = ProbeGrid.on_mesh(document, run.solution.space.mesh, probe_domains(run.solution))
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
            )
        if len(outcomes) != len(LADDER):
            pytest.skip(
                f"{name}: the sweep holds {len(outcomes)} of {len(LADDER)} rungs, so the deltas "
                "would be differences between rungs that are not adjacent"
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
    """Return the recorded per-species stabilisation contribution, or ``None``."""
    value = recorded.get("stabilisation_currents_A")
    return dict(value) if isinstance(value, dict) else None
