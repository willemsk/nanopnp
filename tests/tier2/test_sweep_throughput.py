"""VER-39 (slow): sweep throughput and parallel scaling (QR-06, section 8.3)."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

import pytest

from nanopnp.api.session import Session
from nanopnp.api.sweep import run_plan
from nanopnp.io.store import Store
from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.sweep.plan import plan_from_document, write_plan
from nanopnp.sweep.run import THREAD_VARIABLES

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.slow

PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
)
MAXH_NM = 4.0
# NUM-34
WALL_H_NM = 0.35

WORKER_COUNTS: tuple[int, ...] = (1, 2, 4)

BASE = """
schema: nanopnp/case/v0.5
name: throughput
inputs:
  mesh: {{path: {mesh}, format: vol, groups: {{default: interface}}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.1
  temperature_K: 298.15
  parameters: willems2020_nacl
  corrections:
    diffusivity:  {{model: willems2020_nacl, wall: true, concentration: true}}
    mobility:     {{model: willems2020_nacl, wall: true, concentration: true}}
    viscosity:    {{model: willems2020_nacl, wall: true, concentration: true}}
    permittivity: {{model: willems2020_nacl}}
    density:      {{model: willems2020_nacl}}
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: epnp-ns, solid_permittivities: {{membrane: 3.2}}}}
numerics: {{continuation: default_ladder, stabilisation: none}}
outputs: [current]
"""

# NUM-26
SWEEP = """
schema: nanopnp/sweep/v0.5
name: throughput
base: base.yaml
axes:
  - name: bias
    path: boundary_conditions.bias_V
    origin: 2
    values: [0.03, 0.04, 0.05, 0.06, 0.07]
  - name: salt
    path: electrolyte.concentration_M
    origin: 0
    values: [0.1, 0.15, 0.22, 0.33, 0.5]
"""


@pytest.fixture(scope="module")
def planned(tmp_path_factory: pytest.TempPathFactory) -> Path:
    work = tmp_path_factory.mktemp("throughput")
    mesh_path = work / "pore.vol"
    PORE.generate(maxh_nm=MAXH_NM, wall_h_nm=WALL_H_NM).ngmesh.Save(str(mesh_path))
    (work / "base.yaml").write_text(BASE.format(mesh=mesh_path), encoding="utf-8")
    (work / "sweep.yaml").write_text(SWEEP, encoding="utf-8")
    plan = plan_from_document(work / "sweep.yaml")
    return write_plan(plan, work / "sweep")


def test_ver39_the_scaling_curve_is_measured_and_recorded(
    planned: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    from nanopnp.sweep.plan import read_plan

    plan = read_plan(planned)
    widths = [last - first for first, last in plan.waves()]
    logger.info(
        "grid: %d points in %d waves, widths %s; %d visible cores; pinning %s",
        len(plan.points),
        len(widths),
        widths,
        os.cpu_count(),
        ", ".join(f"{variable}=1" for variable in THREAD_VARIABLES),
    )

    seconds: dict[int, float] = {}
    for workers in WORKER_COUNTS:
        # A fresh store and sweep directory each time: no run may be faster because an earlier
        # one already solved its members.
        work = tmp_path_factory.mktemp(f"workers-{workers}")
        directory = work / "sweep"
        write_plan(plan, directory)
        started = time.perf_counter()
        members = run_plan(plan, directory, session=Session(Store(work / "store")), workers=workers)
        elapsed = time.perf_counter() - started
        seconds[workers] = elapsed

        assert len(members) == len(plan.points)
        assert all(member.status == "ok" for member in members), [
            (member.index, member.error) for member in members if member.status != "ok"
        ]
        uncached = [member for member in members if not member.cached]
        assert len(uncached) == len(members), (
            "a fresh store must make every member a miss, or the throughput figure is a "
            "statement about the cache rather than about the dispatch (QR-06)"
        )
        logger.info(
            "N = %d: %6.1f s wall, %6.1f s summed over members, %5.1f points/worker-hour, "
            "efficiency %.2f",
            workers,
            elapsed,
            sum(member.seconds for member in members),
            3600.0 * len(uncached) / (workers * elapsed),
            seconds[1] / (workers * elapsed),
        )

    logger.info(
        "scaling curve (recorded, not gated): %s",
        ", ".join(
            f"efficiency({workers}) = {seconds[1] / (workers * seconds[workers]):.2f}"
            for workers in WORKER_COUNTS
        ),
    )
    # Completion is the only assertion: a threshold on shared hardware would test the hardware.
    assert set(seconds) == set(WORKER_COUNTS)
