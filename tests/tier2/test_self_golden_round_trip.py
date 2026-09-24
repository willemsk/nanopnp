"""VAL-01, VAL-02: one solution through the whole golden path, back to itself.

The Tier-3 harness has to be exercisable before the COMSOL exports land — and the
honest way to exercise it is to make the reference *be* the solution under test,
so that every field norm and every quantity-of-interest error is known in advance
to be zero. Anything that is not zero is a defect in the harness: a transposed
patch, a lost NaN, a scale applied twice, a sign flipped where none was declared.

The path exercised is the whole one, not the shortcut. The converged fields are
sampled on a probe grid, written as ``%Grid``/``%Data`` **text tables**, read back
through :func:`~nanopnp.density.grid.read_grid` — the reader VAL-15 verified
against the delivered 77 MB reference table to 4.7e-12 — archived as ``.npz`` with
a validated manifest, and only then compared. A round trip through the in-memory
arrays alone would test the container and skip the format.

The tolerance is **exactly zero**, not 1e-14. ``%.17g`` round-trips ``float64``
by definition, so a difference of one ulp here is a defect in the transport
format rather than a rounding budget being spent.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.physics.measures import AXISYMMETRIC
from nanopnp.post import qoi
from nanopnp.post.indicator import axial_indicator, lumen_band
from nanopnp.solve.continuation import default_ladder, run_ladder
from nanopnp.validation.compare import (
    compare_fields,
    compare_quantities,
    probe_domains,
    sample_on_probe,
)
from nanopnp.validation.comsol import (
    GOLDEN_SCHEMA,
    MANIFEST_NAME,
    GoldenManifest,
    export_golden,
    field_unit,
    ingest_golden,
    load_golden,
)
from nanopnp.validation.probe import PROBE_SCHEMA, ProbeGrid, loads_probe

logger = logging.getLogger(__name__)

PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=13.0, reservoir_radius_nm=25.0
)
"""The VER-11 benchmark pore. Nothing here reads a number out of the solution, so
the mesh is the cheapest one that converges: what is under test is the harness."""

CONCENTRATION_M = 0.5
BIAS_V = 0.05
SURFACE_CHARGE_C_M2 = -0.05
"""A charged pore, so the two species carry unequal currents and a transport
number exists for the round trip to preserve."""

PROBE_TEXT = f"""
schema: {PROBE_SCHEMA}
name: ver11-benchmark
patches:
  - {{name: lumen, r_nm: [0.0, 1.5], z_nm: [-6.0, 6.0], n_r: 7, n_z: 13}}
  - {{name: bulk, r_nm: [0.1, 10.1], z_nm: [10.0, 20.0], n_r: 11, n_z: 6}}
"""
"""Two non-square patches: the lumen, where the mask keeps everything, and a
block of cis reservoir. 91 + 66 = 157 points, which is a round trip and not a
benchmark."""


@pytest.fixture(scope="module")
def solved():
    """Return one converged solution, its probe grid and its quantities.

    Module-scoped: the solve is the expensive part and every assertion below is a
    reading of the same converged state.
    """
    mesh = PORE.generate(maxh_nm=5.0, wall_h_nm=0.4)
    ladder = default_ladder(
        mesh,
        concentration_M=CONCENTRATION_M,
        bias_V=BIAS_V,
        surface_charge_C_m2=SURFACE_CHARGE_C_M2,
        solid_permittivities={"membrane": 2.0},
        start_concentration_M=None,
        charge_steps=2,
    )
    classical = [rung for rung in ladder if rung.stage <= 5]
    result = run_ladder(classical)
    solution = result.solution
    logger.info(
        "solved in %d rungs, %d iterations, %.1f s",
        len(result.rungs),
        result.iterations,
        result.seconds,
    )

    document = loads_probe(PROBE_TEXT)
    grid = ProbeGrid.on_mesh(document, solution.space.mesh, probe_domains(solution))
    measures = replace(AXISYMMETRIC, element_order=max(3, AXISYMMETRIC.element_order))
    lower, upper = lumen_band(PORE, fraction=0.8)
    indicator = axial_indicator(
        solution.space.mesh,
        lower_nm=lower,
        upper_nm=upper,
        order=AXISYMMETRIC.element_order,
    )
    quantities = qoi.extract(solution, measures, indicator, bias_V=BIAS_V)
    return solution, document, grid, quantities


def _manifest(document, quantities, fields) -> dict[str, object]:
    """Return the self-golden manifest for this solution, as the author's YAML form."""
    return {
        "schema": GOLDEN_SCHEMA,
        "case": "ver11-benchmark",
        "case_hash": "b" * 64,
        "probe": document.name,
        "probe_hash": document.hash,
        "refinement": "published",
        "source": "self",
        "comsol_version": "nanopnp (self-golden, no COMSOL)",
        "model_file": "tests/tier2/test_self_golden_round_trip.py",
        "export_date": "2026-09-18",
        "fields": {name: {"expression": name, "unit": field_unit(name)} for name in sorted(fields)},
        "current_boundary": "the NUM-24 domain indicator, not a boundary",
        "current_sign_reference": "cis",
        "quantities": {
            "bias_V": quantities.bias_V,
            "current_A": quantities.current_A,
            "currents_A": dict(quantities.currents_A),
            "transport_number": quantities.transport_number,
            "conductance_S": quantities.conductance_S,
            "eof_m3_s": quantities.eof_m3_s,
        },
    }


def test_val01_self_golden_reproduces_its_own_solution(solved, tmp_path: Path) -> None:
    """Every field norm and every QoI error is exactly zero through the whole path.

    Sampled, written as text tables, ingested through the reference reader,
    archived, loaded and compared. Three things are asserted beyond the zeros,
    because a comparison of a thing with itself passes trivially if it compared
    nothing:

    - the mask retains points, and the same points on both sides;
    - the located maximum is a real ``(r, z)`` on the grid;
    - the transport format is what was traversed — the tables exist on disk and
      the archive was built from them, not from the arrays in memory.
    """
    import numpy as np

    solution, document, grid, quantities = solved
    sampled = sample_on_probe(solution, grid, scales=solution.model.scales)
    assert set(sampled) == set(grid.masks)
    assert all(mask.sum() > 0 for mask in grid.masks.values())

    exported = tmp_path / "export"
    manifest = _manifest(document, quantities, sampled)
    export_golden(sampled, GoldenManifest.model_validate(manifest), exported, tables=document)
    (exported / MANIFEST_NAME).write_text(yaml.safe_dump(manifest, sort_keys=False), "utf-8")
    written = sorted(path.name for path in exported.glob("*.txt"))
    assert len(written) == len(sampled) * len(document.patches)

    archive = tmp_path / "archive"
    ingest_golden(exported, probe=document, destination=archive)
    golden = load_golden(archive)
    assert golden.source == "self"
    assert golden.current_sign_flipped is False

    comparisons = compare_fields(sampled, golden, grid)
    assert {entry.field for entry in comparisons} == set(sampled)
    for entry in comparisons:
        assert entry.points == int(grid.masks[entry.field].sum())
        assert entry.rel_L2_r == 0.0, f"{entry.field} moved through the round trip"
        assert entry.rel_l2 == 0.0
        assert entry.max_abs_rel == 0.0
        assert np.isfinite(entry.max_at_nm).all()

    recorded = quantities.summary()
    compared = compare_quantities(recorded, golden.quantities)
    assert {entry.name for entry in compared} >= {"current_A", "conductance_S", "transport_number"}
    for entry in compared:
        assert entry.relative == 0.0, f"{entry.name} moved through the round trip"
        assert entry.ours == entry.golden


def test_val01_the_round_trip_preserves_the_masked_points_as_nan(solved, tmp_path: Path) -> None:
    """A masked point survives the text format as ``NaN``, not as a zero.

    This is the failure the round trip is really guarding: NGSolve returns ``0``
    outside a ``definedon`` region, so a masked point that came back a number
    would enter the norm as fabricated agreement. It has to travel as ``NaN``
    through ``%.17g``, through ``np.fromstring`` and through the archive.
    """
    import numpy as np

    solution, document, grid, quantities = solved
    sampled = sample_on_probe(solution, grid, scales=solution.model.scales)
    concentrations = [name for name in sampled if name.startswith("c_")]
    assert concentrations, "the benchmark solves for ions"

    exported = tmp_path / "export"
    manifest = _manifest(document, quantities, sampled)
    export_golden(sampled, GoldenManifest.model_validate(manifest), exported, tables=document)
    (exported / MANIFEST_NAME).write_text(yaml.safe_dump(manifest, sort_keys=False), "utf-8")
    ingest_golden(exported, probe=document, destination=exported)
    golden = load_golden(exported)

    for name in sorted(sampled):
        ours = ~np.isnan(sampled[name])
        assert np.array_equal(golden.defined(name), ours), (
            f"{name}: the golden's NaN set is not the mask that was written"
        )
        assert np.array_equal(golden.defined(name), np.asarray(grid.masks[name]))


# -- the CLI path: a finished run, reopened and compared (IF-02, FR-27) --------

RUN_CASE = """
schema: nanopnp/case/v2
name: validate-probe
inputs:
  mesh:
    path: {mesh_path}
    format: vol
    groups: {{default: interface}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.1
  temperature_K: 298.15
  parameters: willems2020_nacl
boundary_conditions:
  bias_V: 0.02
  ground: cis
physics:
  model: epnp-ns
  solid_permittivities: {{membrane: 3.2}}
numerics:
  continuation: default_ladder
  stabilisation: none
outputs: [current, transport_numbers, eof_rate]
"""

SMALL_PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
)
"""The cheapest pore a full ``run_case`` converges on; see tests/tier2/test_reproducibility.py."""

RUN_PROBE_TEXT = f"""
schema: {PROBE_SCHEMA}
name: validate-probe-grid
patches:
  - {{name: lumen, r_nm: [0.0, 1.5], z_nm: [-2.5, 2.5], n_r: 4, n_z: 6}}
  - {{name: bulk, r_nm: [0.1, 4.1], z_nm: [5.0, 7.0], n_r: 5, n_z: 3}}
"""


@pytest.fixture(scope="module")
def archived_run(tmp_path_factory: pytest.TempPathFactory):
    """Run one case end to end and keep its directory, store and probe document."""
    from nanopnp.io.run import run_case
    from nanopnp.io.store import Store

    work = tmp_path_factory.mktemp("validate")
    mesh_path = work / "pore.vol"
    SMALL_PORE.generate(maxh_nm=4.0, wall_h_nm=1.0).ngmesh.Save(str(mesh_path))
    case_path = work / "case.yaml"
    case_path.write_text(RUN_CASE.format(mesh_path=mesh_path), encoding="utf-8")

    store = Store(work / "store")
    result = run_case(case_path, store=store, workspace=work / "fields")
    probe_path = work / "probe.yaml"
    probe_path.write_text(RUN_PROBE_TEXT, encoding="utf-8")
    return result.directory, store, probe_path, work


def test_val01_a_finished_run_reopens_without_re_solving_it(archived_run) -> None:
    """``reopen`` returns the run's own converged state and its *recorded* quantities.

    Both halves matter. The state comes back through
    :func:`~nanopnp.solve.state.restore`, which rebuilds the operator from the
    same ladder the solve used, so it cannot differ from the solved one in a
    switch. The quantities come from ``run.json`` rather than being re-extracted,
    because FR-25 archived what the run *reported* and a comparison against
    freshly recomputed numbers would be comparing the golden to something the
    manifest does not describe.
    """
    import numpy as np

    from nanopnp.validation.runs import reopen

    directory, store, probe_path, _ = archived_run
    run = reopen(directory, store=store)
    assert run.case.name == "validate-probe"
    assert run.quantities["current_A"] != 0.0
    assert run.quantities["bias_V"] == pytest.approx(0.02)

    document = loads_probe(probe_path.read_text(encoding="utf-8"))
    grid = ProbeGrid.on_mesh(document, run.solution.space.mesh, probe_domains(run.solution))
    sampled = sample_on_probe(run.solution, grid, scales=run.scales)
    for name, values in sorted(sampled.items()):
        kept = values[grid.masks[name]]
        assert kept.size > 0
        assert np.isfinite(kept).all(), f"{name} is not finite where its mask retains it"


def test_val01_export_golden_then_compare_is_zero_through_the_cli(
    archived_run, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``validate export-golden`` then ``validate compare`` on one run: every number zero.

    The end-to-end IF-02 path — reopen, sample, archive, reload, compare — with
    the one solution playing both sides, so every field norm and every QoI error
    is known in advance. It also pins the ``case_hash`` gate: the golden's
    identity comes from the same route ``compare`` checks it against, so a
    mismatch here would mean the two disagree about what a case *is*.
    """
    import json

    from nanopnp.cli import main

    directory, store, probe_path, _ = archived_run
    destination = tmp_path / "self-golden"
    assert (
        main(
            [
                "validate",
                "export-golden",
                str(directory),
                "--probe",
                str(probe_path),
                "--destination",
                str(destination),
                "--store",
                str(store.root),
                "--export-date",
                "2026-09-18",
                "--json",
            ]
        )
        == 0
    )
    written = json.loads(capsys.readouterr().out)
    assert written["golden_source"] == "self"

    assert (
        main(
            [
                "validate",
                "compare",
                str(directory),
                "--probe",
                str(probe_path),
                "--golden",
                str(destination),
                "--store",
                str(store.root),
                "--json",
            ]
        )
        == 0
    )
    report = json.loads(capsys.readouterr().out)
    assert report["golden_source"] == "self"
    assert report["current_sign_flipped"] is False
    assert report["fields"], "the comparison covered no field"
    for entry in report["fields"]:
        assert entry["rel_L2_r"] == 0.0
        assert entry["rel_l2"] == 0.0
    assert report["quantities"], "the comparison covered no quantity"
    for entry in report["quantities"]:
        assert entry["relative"] == 0.0
