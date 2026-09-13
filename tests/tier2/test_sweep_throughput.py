"""VER-39 (slow) — sweep throughput and parallel scaling (QR-06, §8.3).

QR-06 is a SHOULD with two halves: *3,675 solves within a day-scale wall clock on
12 cores*, and *throughput scaling linearly with the number of independent
workers*.

The first half is the author's machine and a Phase-1 end-of-phase number. It is
**not** measured here, by the author's ruling of 8 September 2026: a day-scale run
inside a package's own gate is not a gate. What WP11 owes it instead is that the
run be one command against a document under version control, which is
``docs/sweeps/phase1-reference.sweep.yaml`` and is checked at Tier 1.

The second half is measurable anywhere, and it is what this module measures:

    efficiency(N) = T(1) / (N . T(N))

over a grid small enough to run in a ``slow`` test, at N = 1, 2 and 4, **into a
fresh store each time**. Two things it must carry with it or it means nothing.

- **Thread pinning.** N processes sharing one BLAS pool are not N independent
  workers, and a curve measured without it reports the pool. The runner's
  ``spawn`` initialiser sets it; the setting is logged here beside the numbers.
- **Uncached members only.** A resumed sweep is a dictionary lookup and would
  report unbounded throughput, so ``points_per_worker_hour`` is computed over the
  members actually solved. The fresh store per run is what makes that the same as
  every member, and it is asserted rather than assumed.

**Recorded, never gated.** Completing the sweep is the assertion, exactly as the
envelope test frames its own numbers: a scaling figure measured on shared CI
hardware is a statement about that hardware. This development environment reports
four cores, so N = 4 is already the whole machine and the last point of the curve
is expected to sag.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

import pytest

from nanopnp.io.store import Store
from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.sweep.plan import plan_from_document, write_plan
from nanopnp.sweep.run import THREAD_VARIABLES, run_plan

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.slow

PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
)
MAXH_NM = 4.0
WALL_H_NM = 0.35
"""The coarsest mesh NUM-34 admits with the wall corrections on (392 elements)."""

WORKER_COUNTS: tuple[int, ...] = (1, 2, 4)
"""The curve's points. ``1`` runs in this process rather than in a pool of one:
a single-worker measurement must not pay the ``spawn`` cost, or ``efficiency(1)``
would be a statement about process startup."""

BASE = """
schema: nanopnp/case/v1
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

SWEEP = """
schema: nanopnp/sweep/v1
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
"""Twenty-five points in seven waves of widths 1, 3, 5, 5, 5, 4, 2.

Two axes rather than one, because a single axis rooted in its middle has waves
two points wide and would cap the curve at N = 2 whatever the runner did: the
measurement would report the *grid*. Five wide is enough for four workers, which
is what this machine has, and the shape — a narrow root, a broad middle, a short
serial tail — is the §8.3 grid's own.

No member sits at exactly 0 V, and that is not an accident: at zero bias the
current is zero and both extraction routes return round-off, so NUM-26's
*relative* agreement divides by a vanishing scale and reports a difference of
order 1. Measured on this pore: ``I_psi = 2.3e-27`` A against
``I_reaction = 4.6e-25`` A, a relative difference of 0.995, which aborts the
member. The route check is inapplicable at equilibrium rather than failing
there, and a throughput measurement is not the place to argue about it.
**[tested]**
"""


@pytest.fixture(scope="module")
def planned(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Write the mesh, the base case and the sweep, and return the plan path."""
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
    """Run one grid at 1, 2 and 4 workers and log what it cost. Never gated.

    The assertion is that every member of every run reached ``ok`` and that none
    of them was served from a cache: a run whose members were dictionary lookups
    would report a speedup that is a statement about the store. Everything else
    — the efficiency, the throughput, the wave widths — is *reported*, because a
    threshold on a number measured on shared hardware would be a threshold on
    the hardware.
    """
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
        # A fresh store each time, so that no run can be faster because an
        # earlier one already solved its members. The sweep directory is fresh
        # too: the member records are what the collector reads, and leaving the
        # previous run's behind would make the next one look complete.
        work = tmp_path_factory.mktemp(f"workers-{workers}")
        directory = work / "sweep"
        write_plan(plan, directory)
        started = time.perf_counter()
        members = run_plan(plan, directory, store=Store(work / "store"), workers=workers)
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
    # The one thing that is asserted, and it is not a threshold: the sweep
    # completed at every worker count, which is what makes the numbers above
    # measurements of the same work rather than of three different sweeps.
    assert set(seconds) == set(WORKER_COUNTS)
