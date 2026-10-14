"""VER-37 and VER-38 (Tier 2): a sweep that actually solves (FR-24, FR-23)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from nanopnp.core.hashing import decode_floats
from nanopnp.io.store import Store
from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.post.qoi import rectification_ratio
from nanopnp.sweep.collect import DATASET_FILENAME, collect
from nanopnp.sweep.plan import SweepPlan, plan_from_document, write_plan
from nanopnp.sweep.run import MemberResult, run_plan, run_point

logger = logging.getLogger(__name__)

PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
)
MAXH_NM = 4.0
# NUM-34
WALL_H_NM = 0.35

# NUM-16
TOLERANCE = 1.0e-6

BASE = """
schema: nanopnp/case/v0.5
name: sweep-probe
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
outputs: [current, rectification]
"""

SWEEP = """
schema: nanopnp/sweep/v0.5
name: warm-vs-cold
base: base.yaml
axes:
  - name: salt
    path: electrolyte.concentration_M
    origin: 0
    values: [0.1, 0.3]
  - name: bias
    path: boundary_conditions.bias_V
    origin: 0
    values: [-0.05, 0.05]
"""


class Swept:
    def __init__(
        self,
        plan: SweepPlan,
        warm: tuple[MemberResult, ...],
        cold: tuple[MemberResult, ...],
        directory: Path,
    ) -> None:
        self.plan = plan
        self.warm = {member.index: member for member in warm}
        self.cold = {member.index: member for member in cold}
        self.directory = directory


# FR-24
@pytest.fixture(scope="module")
def swept(tmp_path_factory: pytest.TempPathFactory) -> Swept:
    work = tmp_path_factory.mktemp("sweep")
    mesh_path = work / "pore.vol"
    PORE.generate(maxh_nm=MAXH_NM, wall_h_nm=WALL_H_NM).ngmesh.Save(str(mesh_path))
    (work / "base.yaml").write_text(BASE.format(mesh=mesh_path), encoding="utf-8")
    (work / "sweep.yaml").write_text(SWEEP, encoding="utf-8")

    plan = plan_from_document(work / "sweep.yaml")
    directory = work / "warm"
    write_plan(plan, directory)
    warm = run_plan(plan, directory, store=Store(work / "warm-store"))

    cold_directory = work / "cold"
    cold_store = Store(work / "cold-store")
    cold = tuple(
        run_point(plan, index, store=cold_store, directory=cold_directory)
        for index in reversed(range(len(plan.points)))
    )
    return Swept(plan, warm, cold, directory)


def _status(member: MemberResult) -> str:
    return str(dict(member.warm_start or {}).get("status", "?"))


# -- the premise the whole design rests on ------------------------------------


# QR-08
def test_ver37_a_warm_start_does_not_move_the_answer(swept: Swept) -> None:
    worst = 0.0
    where = ""
    for index in sorted(swept.warm):
        warm, cold = swept.warm[index], swept.cold[index]
        assert warm.status == "ok" and cold.status == "ok", (warm.error, cold.error)
        assert warm.quantities is not None and cold.quantities is not None
        for name, value in warm.quantities.items():
            reference = cold.quantities.get(name)
            if not isinstance(value, int | float) or not isinstance(reference, int | float):
                continue
            scale = max(abs(float(value)), abs(float(reference)))
            if scale == 0.0:
                continue
            difference = abs(float(value) - float(reference)) / scale
            if difference > worst:
                worst, where = difference, f"point {index} {name}"

    logger.info(
        "warm against cold over %d points: worst relative difference %.3e (%s), tolerance %.0e",
        len(swept.warm),
        worst,
        where or "nothing compared",
        TOLERANCE,
    )
    assert where, "something must have been compared, or this asserts nothing"
    assert worst < TOLERANCE, f"{where} moved by {worst:.3e} between the warm and cold paths"


# NUM-18
def test_ver37_the_warm_path_costs_strictly_fewer_newton_iterations(swept: Swept) -> None:
    warm_iterations = sum(member.iterations or 0 for member in swept.warm.values())
    cold_iterations = sum(member.iterations or 0 for member in swept.cold.values())
    warm_seconds = sum(member.seconds for member in swept.warm.values())
    cold_seconds = sum(member.seconds for member in swept.cold.values())
    warm_start_count = sum(1 for member in swept.warm.values() if _status(member) == "warm")

    logger.info(
        "warm pass %d Newton iterations in %.1f s (%d of %d members warm-started), "
        "cold pass %d in %.1f s: %.2fx the iterations, %.2fx the wall clock",
        warm_iterations,
        warm_seconds,
        warm_start_count,
        len(swept.warm),
        cold_iterations,
        cold_seconds,
        cold_iterations / warm_iterations,
        cold_seconds / warm_seconds,
    )
    assert warm_start_count == len(swept.plan.points) - 1, "only the root has no parent"
    assert warm_iterations > 0, "the members must have reported their iteration counts"
    assert warm_iterations < cold_iterations


# FR-25, NUM-09
def test_ver37_the_warm_start_record_names_the_neighbour_and_what_differed(
    swept: Swept,
) -> None:
    salt_steps = 0
    for index, member in sorted(swept.warm.items()):
        record = dict(member.warm_start or {})
        point = swept.plan.point(index)
        if point.parent is None:
            assert record["status"] == "cold"
            assert "no neighbour" in str(record["reason"])
            continue
        assert record["status"] == "warm"
        assert record["source"] == swept.warm[point.parent].solution
        differing = list(record["differing_operator_keys"])
        assert "solve_hash" in differing, "every axis moves the solve provenance"
        parent = swept.plan.point(point.parent)
        moved_salt = (
            point.assignments["electrolyte.concentration_M"]
            != parent.assignments["electrolyte.concentration_M"]
        )
        if moved_salt:
            salt_steps += 1
            assert "model.scales" in differing
        else:
            assert "model.scales" not in differing
        logger.info("point %d warm from %s, differing %s", index, record["source"][:12], differing)
    assert salt_steps, "the grid must contain a salt step, or half the partition is untested"


# FR-24
def test_ver38_a_member_whose_parent_is_absent_falls_back_to_the_full_ladder(
    swept: Swept,
) -> None:
    for index, member in sorted(swept.cold.items()):
        assert member.status == "ok"
        record = dict(member.warm_start or {})
        assert record["status"] == "cold", index
        reason = str(record["reason"])
        assert "no neighbour" in reason or "store holds no converged state" in reason
        if swept.plan.point(index).parent is not None:
            assert "store holds no converged state" in reason
            logger.info("point %d ran cold: %s", index, reason)


def test_ver38_a_member_run_alone_gives_the_same_scalars_as_inside_the_sweep(
    swept: Swept,
) -> None:
    deepest = max(swept.plan.points, key=lambda point: point.wave).index
    warm, cold = swept.warm[deepest], swept.cold[deepest]
    assert _status(warm) == "warm" and _status(cold) == "cold"
    assert warm.quantities is not None and cold.quantities is not None
    warm_current = float(warm.quantities["current_A"])
    cold_current = float(cold.quantities["current_A"])
    difference = abs(warm_current - cold_current) / abs(cold_current)
    logger.info(
        "deepest point %d: warm %.9e A, alone %.9e A, relative difference %.3e",
        deepest,
        warm_current,
        cold_current,
        difference,
    )
    assert difference < TOLERANCE

    assert warm.solution == cold.solution


# -- the collected dataset ----------------------------------------------------


# NUM-26
def test_ver38_the_dataset_carries_a_row_per_point_with_its_route_agreement(
    swept: Swept,
) -> None:
    artefact = collect(swept.plan, swept.directory, members=tuple(swept.warm.values()))
    rows = list(artefact.summary["rows"])
    assert len(rows) == len(swept.plan.points)
    assert [row["index"] for row in rows] == list(range(len(rows)))
    for row in rows:
        assert row["status"] == "ok"
        assert row["route_agreement"] is not None
        assert float(row["route_agreement"]) < 1.0e-3, row["index"]
        assert row["wall_distance"] is not None
        assert float(dict(row["wall_distance"])["minimum_nm"]) > 0.0
    logger.info(
        "route agreement over %d members: worst %.3e",
        len(rows),
        max(float(row["route_agreement"]) for row in rows),
    )


# FR-23
def test_ver23_the_rectification_is_the_two_point_ratio_of_the_pair(swept: Swept) -> None:
    artefact = collect(swept.plan, swept.directory, members=tuple(swept.warm.values()))
    ratios = list(artefact.summary["rectification"])
    assert len(ratios) == 2, "two concentrations, one +/-50 mV pair each"

    rows = {int(row["index"]): row for row in artefact.summary["rows"]}
    for entry in ratios:
        forward = rows[int(entry["forward"])]
        reverse = rows[int(entry["reverse"])]
        assert float(dict(forward["quantities"])["bias_V"]) == 0.05
        assert float(dict(reverse["quantities"])["bias_V"]) == -0.05
        expected = rectification_ratio(
            float(dict(forward["quantities"])["current_A"]),
            float(dict(reverse["quantities"])["current_A"]),
        )
        assert entry["rectification"] == expected
        logger.info(
            "points %s/%s at %+.0f mV: RR = %.6f",
            entry["forward"],
            entry["reverse"],
            float(entry["bias_V"]) * 1e3,
            float(entry["rectification"]),
        )

    # A straight lumen with no fixed charge is symmetric in z, so the rectification is 1 and
    # any departure is the extraction's own.
    for entry in ratios:
        assert abs(float(entry["rectification"]) - 1.0) < 1.0e-3


def test_ver38_the_dataset_on_disk_is_the_one_the_artefact_carries(swept: Swept) -> None:
    artefact = collect(swept.plan, swept.directory, members=tuple(swept.warm.values()))
    written = decode_floats(
        json.loads((swept.directory / DATASET_FILENAME).read_text(encoding="utf-8"))
    )
    assert written["rows"] == list(artefact.summary["rows"])
    assert written["plan"] == swept.plan.hash
    assert written["counts"] == {"ok": len(swept.plan.points)}


def test_fr25_the_manifest_of_a_warm_member_records_how_it_was_reached(swept: Swept) -> None:
    from nanopnp.io.manifest import MANIFEST_FILENAME
    from nanopnp.io.manifest import read as read_manifest

    def _read(directory: str) -> dict[str, object]:
        found = decode_floats(dict(read_manifest(Path(directory) / MANIFEST_FILENAME)))
        assert isinstance(found, dict)
        return found

    warm = next(member for member in swept.warm.values() if _status(member) == "warm")
    assert warm.directory is not None
    manifest = _read(warm.directory)

    record = dict(dict(manifest["solver"])["warm_start"])
    assert record["status"] == "warm"
    # The *parent's* stage-10 artefact, not this member's own: the record says
    # where Newton started, and the member's own hash is what it produced.
    parent = swept.plan.point(warm.index).parent
    assert parent is not None
    assert record["source"] == swept.warm[parent].solution
    assert record["source"] != warm.solution, (
        "warm and cold key one artefact, but a member and its parent are two different "
        "operating points and must not"
    )
    assert "solve_hash" in list(record["differing_operator_keys"])

    # The rungs actually run: one, not twelve. NUM-18 stage 9 generalised to the
    # other axes of the envelope, rather than a departure from the fixed path.
    rungs = list(dict(dict(manifest["solver"])["run"])["rungs"])
    assert len(rungs) == 1, [rung["rung"] for rung in rungs]
    assert dict(rungs[0])["stage"] == 9

    cold = swept.warm[0]
    cold_manifest = _read(str(cold.directory))
    assert dict(dict(cold_manifest["solver"])["warm_start"])["status"] == "cold"
    assert len(list(dict(dict(cold_manifest["solver"])["run"])["rungs"])) > 1

    measured = dict(dict(manifest["geometry_and_mesh"])["wall_distance"])
    assert float(measured["minimum_nm"]) > 0.0
