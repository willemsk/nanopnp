"""VAL-06 at Tier 2 on 2WCD: our ``poisson`` against APBS on the same maps (WP29 D1 to D9).

The Phase 3 gate's third leg. ``seeded_protonated_2wcd`` carries the PROPKA
protonation of the prepared dodecamer, and the case is registered as
``test_charge_2wcd`` registers it. It is walked to the solve with ``poisson``,
both electrodes grounded, the protein at 20 and the membrane at 3.2, once at
``P2`` and once at ``P3`` (D1).

The gated leg (D2 to D8) hands APBS stage 7's export lattice by hat weights, the
assembled permittivity by harmonic staggered maps, and our ``P2`` solution on the
box faces. The refinement budget and the charge's visibility are measured first,
in the same run, and :func:`~nanopnp.validation.apbs.check_report` reads them
before the agreement: ``e_max <= 3 %``, ``e_rms <= 1 %`` and ``e_axis <= 1.5 %``
(section 7.4 NOTE on VAL-06). The report is written as JSON and logged.

Under ``-m slow``: the recorded leg (D9), APBS's own ``spl4`` charge and ``smol``
surface with our membrane imposed, compared per probe ring; and a focused 0.05 nm
grid on the lumen, which checks the order that makes ``e^_A`` a bound.
"""

from __future__ import annotations

import json
import logging
import math
import sys
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pytest

from nanopnp.io.case import load_case, resolve
from nanopnp.io.run import RunResult, run_case
from nanopnp.io.store import Store
from nanopnp.validation.apbs import (
    TOLERANCE,
    ApbsProblem,
    CubicGrid,
    GatedInputs,
    GatedResult,
    MaterialRaster,
    RecordedInputs,
    charge_extent,
    charge_map,
    check_report,
    dielectric_maps,
    face_map_3d,
    fit_grid,
    gated_leg,
    potential_sampler,
    raster_extent,
    raster_from_mesh,
    recorded_leg,
    run_apbs,
    trilinear,
    write_pqr,
)

pytestmark = pytest.mark.extended

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import Prepared2WCD, Seed2WCD
    from nanopnp.density.grid import RadialGrid
    from nanopnp.physics.models import ModelSolution

logger = logging.getLogger(__name__)

CASE = """\
schema: nanopnp/case/v2
name: 2wcd-val06
structure:
  source: {{path: {pdb}}}
  symmetry: {{point_group: C12}}
{geometry}electrolyte:
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
"""D1: ``poisson`` at zero bias, the solids of PHY-20, and the fluid at ``eps_r,f^0``."""


@dataclass(frozen=True)
class Solved:
    """One ``poisson`` walk of 2WCD to the solve, and its restored solution."""

    result: RunResult
    solution: ModelSolution
    order: int
    seconds: float

    def sampler(self) -> Callable[[np.ndarray, np.ndarray], np.ndarray]:
        """Return the potential in ``kT/e`` at ``(r, z)`` arrays, through a whole-domain carrier."""
        return potential_sampler(self.solution, order=self.order)


@dataclass(frozen=True)
class Walked:
    """2WCD solved at ``P2`` and ``P3`` on one store, and the gated leg's inputs."""

    root: Path
    p2: Solved
    p3: Solved
    lattice: RadialGrid
    raster: MaterialRaster
    grid: CubicGrid
    temperature_K: float
    sdie: float
    raster_seconds: float


def _walk(case: Path, store: Store, root: Path, order: int) -> Solved:
    from nanopnp.solve.state import restore, warm_start_payload

    started = time.perf_counter()
    result = run_case(case, store=store, upto="solve", workspace=root / "work", write=False)
    seconds = time.perf_counter() - started
    artefacts = result.artefacts
    solution = restore(
        warm_start_payload(artefacts["solve"]),
        case=load_case(case),
        mesh_artefact=artefacts["mesh"],
        charge_artefact=artefacts["charge"],
    )
    return Solved(result=result, solution=solution, order=order, seconds=seconds)


@pytest.fixture(scope="module")
def walked(
    prepared_2wcd: Prepared2WCD,
    seeded_2wcd: Seed2WCD,
    seeded_protonated_2wcd: Callable[[Path], Path],
    tmp_path_factory: pytest.TempPathFactory,
) -> Walked:
    """Register 2WCD by its C-alpha centroid (WP22 D6), solve at P2 and P3, raster the solve.

    Stages 1 to 6, the registration and the protonation are the session's seeds
    (WP33 D2): the default-size mesh both orders solve on is the seeded one.
    """
    from nanopnp.density.grid import read_grid
    from nanopnp.physics.models import PoissonModel

    root = tmp_path_factory.mktemp("2wcd-val06")
    store = Store(seeded_protonated_2wcd(root / "store"))
    centre = seeded_2wcd.centre_z_nm
    geometry = seeded_2wcd.geometry
    solved = {}
    for order in (2, 3):
        case = root / f"p{order}.case.yaml"
        case.write_text(
            CASE.format(pdb=prepared_2wcd.path, geometry=geometry, order=order), encoding="utf-8"
        )
        solved[order] = _walk(case, store, root, order)
        cached = {record.name for record in solved[order].result.stages if record.cached}
        assert {"structure", "density", "symmetry", "contour", "region", "mesh"} <= cached
    p2, p3 = solved[2], solved[3]
    assert p2.result.artefacts["mesh"].hash == p3.result.artefacts["mesh"].hash, (
        "P3 must solve on P2's mesh, so that e^_F is the order's alone"
    )

    resolved = resolve(load_case(root / "p2.case.yaml"))
    lattice = read_grid(p2.result.artefacts["charge"].payload["charge"], format="npz")
    lattice3 = read_grid(p3.result.artefacts["charge"].payload["charge"], format="npz")
    assert lattice.digest() == lattice3.digest(), "the export lattice is the deposit's source"
    grid = fit_grid(
        charge_extent(lattice),
        interface_z_nm=0.5 * resolved.document.geometry.membrane.thickness_nm,  # type: ignore[union-attr]
    )
    model = p2.solution.model
    assert isinstance(model, PoissonModel)
    mesh = p2.solution.space.mesh
    started = time.perf_counter()
    r_max, z_min, z_max = raster_extent(grid)
    raster = raster_from_mesh(
        mesh,
        model.relative_permittivity(p2.solution) * model.scales.relative_permittivity,
        fluid=model.fluid,
        solids=sorted(model.solid_permittivities),
        r_max_nm=r_max,
        z_min_nm=z_min,
        z_max_nm=z_max,
    )
    raster_seconds = time.perf_counter() - started
    assert model.scales.temperature_K == pytest.approx(resolved.temperature_K, rel=1e-12)
    logger.info(
        "VAL-06 2WCD: centre_z_nm %.4f; P2 walk %.1f s, P3 walk %.1f s; raster %s cells in %.1f s",
        centre,
        p2.seconds,
        p3.seconds,
        raster.permittivity.shape,
        raster_seconds,
    )
    return Walked(
        root=root,
        p2=p2,
        p3=p3,
        lattice=lattice,
        raster=raster,
        grid=grid,
        temperature_K=resolved.temperature_K,
        sdie=resolved.electrolyte.permittivity_0,
        raster_seconds=raster_seconds,
    )


@pytest.fixture(scope="module")
def gated(walked: Walked, apbs: None) -> GatedResult:
    """Run the gated leg at 0.1 and 0.2 nm, write its report, and log it."""
    mesh = walked.p2.result.artefacts["mesh"]
    inputs = GatedInputs(
        lattice=walked.lattice,
        raster=walked.raster,
        ours=walked.p2.sampler(),
        refined=walked.p3.sampler(),
        temperature_K=walked.temperature_K,
        sdie=walked.sdie,
        structure="2WCD, prepared, PROPKA at pH 7.5",
        mesh={
            "elements": mesh.summary["elements"],
            "hash": mesh.hash,
            "orders": [2, 3],
        },
    )
    result = gated_leg(inputs, walked.grid, walked.root / "apbs")
    report = result.report
    seconds = dict(report.seconds)
    seconds.update(
        walk_p2=walked.p2.seconds, walk_p3=walked.p3.seconds, raster=walked.raster_seconds
    )
    memory = dict(report.memory_GB)
    if sys.platform != "win32":
        # Deferred: ``resource`` is Unix-only, and at module scope it fails
        # collection on Windows before the APBS skip is read.
        import resource

        scale = 1e9 if sys.platform == "darwin" else 1e6
        memory["pytest_peak_rss"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / scale
    report = report.model_copy(update={"seconds": seconds, "memory_GB": memory})
    path = walked.root / "val06-gated.json"
    path.write_text(json.dumps(report.model_dump(), indent=2), encoding="utf-8")
    logger.info(
        "VAL-06 2WCD gated report (%s):\n%s", path, json.dumps(report.model_dump(), indent=2)
    )
    return replace(result, report=report)


def test_val06_2wcd_the_refinement_budget_holds_within_half_the_tolerance(
    gated: GatedResult,
) -> None:
    """D8: ``e^_A + e^_F <= tau / 2`` in each norm, before any agreement is read."""
    report = gated.report
    assert report.budget is not None
    assert not report.budget.exceeding(TOLERANCE.scaled(0.5)), report.budget
    assert report.probes > 100_000 and report.axis_probes >= 50


def test_val06_2wcd_the_charge_not_the_faces_carries_the_comparison(gated: GatedResult) -> None:
    """D8: zeroing the charge moves the probes by at least 10 ``tau_rms``."""
    assert gated.report.charge_visibility >= 10.0 * TOLERANCE.rms


def test_val06_2wcd_apbs_agrees_with_poisson_within_the_tolerance(gated: GatedResult) -> None:
    """VAL-06's gate: the budget, the visibility, then ``3 %``, ``1 %`` and ``1.5 %``."""
    check_report(gated.report)
    logger.info(
        "VAL-06 2WCD: agreement %s within %s; budget %s (APBS %s, ours %s); visibility %.3f",
        gated.report.agreement,
        TOLERANCE,
        gated.report.budget,
        gated.report.apbs_refinement,
        gated.report.ours_refinement,
        gated.report.charge_visibility,
    )


def test_val06_2wcd_the_difference_is_located_and_recorded(gated: GatedResult) -> None:
    """Recorded: where the largest difference between the two solvers lies."""
    probes, sampled = gated.probes, gated.sampled
    difference = sampled["apbs"] - sampled["ours"]
    worst = int(np.argmax(np.abs(difference)))
    point = probes.points_nm[worst]
    logger.info(
        "VAL-06 2WCD: the largest |APBS - ours| is %.4f kT/e at (r, z) = (%.3f, %.3f) nm, "
        "where ours is %.4f kT/e",
        difference[worst],
        math.hypot(point[0], point[1]),
        point[2],
        sampled["ours"][worst],
    )
    assert np.all(np.isfinite(difference))


def test_val06_2wcd_apbs_is_unchanged_by_a_cubic_angstrom_slip_at_its_coarse_grid(
    gated: GatedResult,
) -> None:
    """The 0.2 nm run's unit: its potential tracks the 0.1 nm run's within the budget, not by 8."""
    ratio = float(
        np.sqrt(np.mean(gated.sampled["apbs_coarse"] ** 2))
        / np.sqrt(np.mean(gated.sampled["apbs"] ** 2))
    )
    assert ratio == pytest.approx(1.0, abs=TOLERANCE.rms)


def _pqr(walked: Walked, path: Path) -> Path:
    """Write the protonated 2WCD frame in the model frame: stage 5's shift applied to every atom."""
    from nanopnp.charge.protonation import ProtonationTable
    from nanopnp.charge.stage import frame_shift_nm

    payload = walked.p2.result.artefacts["protonation"].payload["protonation"]
    table = ProtonationTable.read(Path(payload))
    assert table.frames == 1
    positions = np.array(table.positions_nm, dtype=np.float64, copy=True)
    positions[:, 2] -= frame_shift_nm(resolve(load_case(walked.root / "p2.case.yaml")))
    return write_pqr(path, positions, table.charge_e, table.radius_nm)


@pytest.mark.slow
def test_val06_2wcd_the_recorded_leg_measures_the_azimuthal_averaging(
    walked: Walked, gated: GatedResult
) -> None:
    """D9, recorded: APBS's ``spl4`` and ``smol`` from the PQR, our membrane imposed, per ring."""
    inputs = RecordedInputs(
        pqr=_pqr(walked, walked.root / "2wcd-model-frame.pqr"),
        raster=walked.raster,
        ours=walked.p2.sampler(),
        temperature_K=walked.temperature_K,
        sdie=walked.sdie,
        pdie=20.0,
        imposed={"membrane": 3.2},
        structure="2WCD, prepared, PROPKA at pH 7.5",
    )
    report, _ = recorded_leg(inputs, walked.grid, walked.root / "apbs", gated.probes)
    path = walked.root / "val06-recorded.json"
    path.write_text(json.dumps(report.model_dump(), indent=2), encoding="utf-8")
    logger.info(
        "VAL-06 2WCD recorded leg (%s): ring mean against ours %s; ring spread %s; APBS at the "
        "nodes against ours %s; %d edges imposed; %s s; %s GB",
        path,
        report.agreement,
        report.spread,
        report.nodes,
        report.imposed_edges,
        report.seconds,
        report.memory_GB,
    )
    assert report.imposed_edges > 0
    assert all(math.isfinite(value) for value in report.spread.values())


FOCUS_NM = 0.05
"""The focused grid's spacing: half the gated leg's."""


@pytest.mark.slow
def test_val06_2wcd_a_focused_grid_confirms_apbs_converges_at_first_order_or_better(
    walked: Walked, gated: GatedResult, tmp_path: Path
) -> None:
    """D8's premise: ``|phi(h) - phi(2h)|`` bounds APBS's error only at first order or better.

    A 193^3 grid at 0.05 nm, centred on the axis at the probe of the largest
    ``e^_A``, takes its faces from APBS's own 0.1 nm solution (focusing) and the
    charge inside it (clipped). Over the probes it holds, the ratio of
    ``phi(0.1) - phi(0.2)`` to ``phi(0.05) - phi(0.1)`` is ``2^p``.
    """
    grid, probes, sampled = walked.grid, gated.probes, gated.sampled
    estimate = np.abs(sampled["apbs"] - sampled["apbs_coarse"])
    worst = probes.points_nm[int(np.argmax(estimate))]
    span = FOCUS_NM * (grid.dime - 1)
    lowest = grid.origin_nm[2] + 2 * grid.spacing_nm
    highest = grid.upper_nm[2] - 2 * grid.spacing_nm - span
    ideal = min(max(worst[2] - 0.5 * span, lowest), highest)
    z0 = grid.origin_nm[2] + grid.spacing_nm * round((ideal - grid.origin_nm[2]) / grid.spacing_nm)
    focus = CubicGrid((-0.5 * span, -0.5 * span, z0), FOCUS_NM, grid.dime)
    problem = ApbsProblem(
        grid=focus,
        temperature_K=walked.temperature_K,
        sdie=walked.sdie,
        charge=charge_map(walked.lattice, focus, clip=True),
        dielectric=dielectric_maps(walked.raster, focus),
        faces=face_map_3d(focus, trilinear(gated.potential, grid)),
    )
    solved = run_apbs(problem, tmp_path, name="focused")
    lower = np.asarray(focus.origin_nm) + 0.4
    upper = np.asarray(focus.upper_nm) - 0.4
    inside = np.all((probes.points_nm >= lower) & (probes.points_nm <= upper), axis=1)
    fine = trilinear(solved.potential, focus)(probes.points_nm[inside])
    first = sampled["apbs"][inside] - sampled["apbs_coarse"][inside]
    second = fine - sampled["apbs"][inside]
    order_max = math.log2(float(np.max(np.abs(first)) / np.max(np.abs(second))))
    order_rms = math.log2(float(np.sqrt(np.mean(first**2)) / np.sqrt(np.mean(second**2))))
    logger.info(
        "VAL-06 2WCD focused at %.2f nm from z = %.2f nm (largest e^_A at r = %.2f, z = %.2f nm) "
        "over %d probes: max |phi(0.1) - phi(0.2)| %.4f, |phi(0.05) - phi(0.1)| %.4f kT/e, "
        "order %.2f in max and %.2f in rms; %.1f s, %s GB",
        FOCUS_NM,
        z0,
        math.hypot(worst[0], worst[1]),
        worst[2],
        int(np.count_nonzero(inside)),
        float(np.max(np.abs(first))),
        float(np.max(np.abs(second))),
        order_max,
        order_rms,
        solved.seconds,
        solved.memory_GB,
    )
    assert order_rms >= 1.0
    assert order_max >= 1.0
