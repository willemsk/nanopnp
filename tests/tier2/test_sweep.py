"""VER-37 and VER-38 (Tier 2) — a sweep that actually solves (FR-24, FR-23).

The Tier-1 modules assert the combinatorics of the forest and the shape of the
records. Neither can assert the one thing the whole design rests on: **that a
warm start does not move the answer**.

§5.3.2 lets the warm-start source stay out of the stage-10 key — two members
differing only in where Newton started key one artefact — and that is admissible
*only* because it is asserted rather than assumed. A converged state that
depended on its starting point is a defect, and this module is where it would
show: every point of a 2 x 2 grid is solved twice, once warm from its parent and
once cold into a store that has never seen a neighbour, and the two are required
to agree to the nonlinear relative tolerance of §5.3.1.

That tolerance, ``1e-6``, is the case schema's own ``numerics.nonlinear.rtol``
(NUM-16) — the same number QR-08's reproduction check uses and for the same
reason: two Newton solves converged to one fixed point from different starting
points differ by the residual each left behind, and that is what ``rtol`` bounds.
The measured difference is reported alongside the verdict, so the figure is on
the record rather than inferred from a pass.

The grid is deliberately small and deliberately spans **two axes**: a bias step,
where the warm start differs from its neighbour in ``solve_hash`` alone, and a
salt step, where ``model.scales`` moves too. One axis would leave the other
untested, and the salt axis is the one that would be refused outright by a gate
on the wrong descriptor key.
"""

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
WALL_H_NM = 0.35
"""The coarsest mesh NUM-34 admits with the wall corrections on (392 elements).

Set by the gate rather than by NUM-26: ``wall_h`` 0.4 nm puts the P2 distance
field a nanometre below zero and is refused, 0.35 nm gives ``min d = +9.5e-06``
nm. See ``tests/tier1/test_wall_distance.py``. Nothing here compares a current
against a closed form — what is under test is that two *routes to the same
current* agree — so the mesh is the cheapest admissible one. **[tested]**
"""

TOLERANCE = 1.0e-6
"""``numerics.nonlinear.rtol`` (§5.3.1, NUM-16): what two Newton solves of one
fixed point may differ by, which is the residual each left behind."""

BASE = """
schema: nanopnp/case/v1
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
schema: nanopnp/sweep/v1
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
"""Two axes, four points, three waves.

Rooted at (0.1 M, -50 mV). The parent rule moves the *last* differing axis
first, so the edge out of the root is a bias step — a warm start differing in
``solve_hash`` alone — and the next is a salt step, which moves ``model.scales``
as well. Both kinds of edge are exercised, which one axis could not do.
"""


class Swept:
    """One planned grid, solved twice: warm through the forest and cold member by member."""

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


@pytest.fixture(scope="module")
def swept(tmp_path_factory: pytest.TempPathFactory) -> Swept:
    """Plan the grid, run it warm, then run every member cold into a fresh store.

    The cold pass runs the members in **reverse index order** into a store that
    starts empty, which is what makes every one of them cold: a point's parent is
    always nearer the origin and so has a lower index, and running downwards
    means no parent has been solved when its child looks for it. That is exactly
    the state a job-array member finds on a machine that has seen nothing else —
    FR-24's "independent jobs" — reached without any special casing in the
    runner.
    """
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
    """Return a member's warm-start status, for a diagnostic."""
    return str(dict(member.warm_start or {}).get("status", "?"))


# -- the premise the whole design rests on ------------------------------------


def test_ver37_a_warm_start_does_not_move_the_answer(swept: Swept) -> None:
    """Every point, warm against cold, to the nonlinear relative tolerance.

    This is what licenses §5.3.2's decision to keep the warm-start source out of
    the stage-10 key. Two members differing only in where Newton started must key
    one artefact, or the store holds two entries for one converged state and
    QR-08's reproduction compares a warm result against a cold key — and that is
    admissible only because the premise is *measured*, which is what this does.

    Every scalar the members reported is compared, not only the current: a
    transport number or an electro-osmotic rate that moved with the starting
    point would be the same defect showing in a quantity nobody looked at.
    """
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


def test_ver37_the_warm_path_costs_strictly_fewer_newton_iterations(swept: Swept) -> None:
    """The point of the exercise: a neighbour's state is most of the answer.

    A warm-started member solves the target rung alone — NUM-18 stage 9
    generalised to the other axes of the envelope — where a cold one climbs the
    whole ladder. Asserted on the *total* rather than per member, because the
    root of the tree is cold in both passes by construction and would drag a
    per-member comparison to equality.

    On **Newton iterations** and not on wall time, which was the first version of
    this test and was a mistake: ``seconds`` is wall clock, and on a machine
    doing anything else the two passes swap places. Measured here, in a run
    alongside the rest of the suite: 34.3 s warm against 26.7 s cold, where the
    same code on an idle machine gave 10.0 s against 21.6 s. Iterations are a
    property of the solves. The seconds are still reported, because they are
    what a reader wants — they are just not what is asserted. **[tested]**
    """
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


def test_ver37_the_warm_start_record_names_the_neighbour_and_what_differed(
    swept: Swept,
) -> None:
    """FR-25: a member's manifest says how it was reached, key by key.

    A bias step differs in ``solve_hash`` alone; a salt step moves
    ``model.scales`` too, because that is the NUM-09 scale set and it is a
    function of the concentration. Both are in the record, and both are operator
    keys the §5.3.2 partition permits to differ.
    """
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


def test_ver38_a_member_whose_parent_is_absent_falls_back_to_the_full_ladder(
    swept: Swept,
) -> None:
    """FR-24's "independent jobs", asserted on the pass that had no neighbours.

    The cold pass ran every member into a store that had never seen its parent,
    and every one of them converged and recorded ``cold`` with the reason. That
    is what makes a member runnable alone, in any order, on a machine that has
    seen nothing else — the warm start is an optimisation the store may or may
    not be able to supply, never a precondition.
    """
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
    """The other reading of the same pair, and the one a user would make.

    ``nanopnp sweep run --index 3`` on a fresh machine is the cold pass; the same
    point inside the sweep is the warm one. A member whose answer depended on
    which of those it was would make a job array and a local sweep two different
    experiments wearing one dataset.
    """
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

    # And it keys the *same* artefact, which is the §5.3.2 decision this checks.
    assert warm.solution == cold.solution


# -- the collected dataset ----------------------------------------------------


def test_ver38_the_dataset_carries_a_row_per_point_with_its_route_agreement(
    swept: Swept,
) -> None:
    """NUM-26's figure reaches the collected table, not only the log.

    With the wall corrections on, route disagreement is a statement about the
    resolution of the mesh at the wall as much as about the extraction
    (``.knowledge/06`` §7.1.1). A sweep is the first thing here that runs
    unattended, so an under-resolved corner of the envelope has to be visible in
    the table rather than in the log of the one member that noticed.
    """
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


def test_ver23_the_rectification_is_the_two_point_ratio_of_the_pair(swept: Swept) -> None:
    """FR-23: the ratio the collector produces is the one §6.7 defines, exactly.

    ``rectification`` is stripped from every member — a case asking for it at one
    operating point is refused by the §5.3.1 NOTE — and produced here from the
    matched opposite-bias pairs. Equality is exact and not to a tolerance: the
    collector must be applying :func:`~nanopnp.post.qoi.rectification_ratio` to
    the two currents the members reported, and any other arithmetic is a
    different quantity wearing the name.
    """
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

    # A straight lumen with no fixed charge is symmetric in z, so the physical
    # answer is 1 and any departure is the extraction's own (VER-11's argument,
    # reached here through the sweep rather than through two hand-built solves).
    for entry in ratios:
        assert abs(float(entry["rectification"]) - 1.0) < 1.0e-3


def test_ver38_the_dataset_on_disk_is_the_one_the_artefact_carries(swept: Swept) -> None:
    """``dataset.json`` round-trips to the summary, through the canonical encoding."""
    artefact = collect(swept.plan, swept.directory, members=tuple(swept.warm.values()))
    written = decode_floats(
        json.loads((swept.directory / DATASET_FILENAME).read_text(encoding="utf-8"))
    )
    assert written["rows"] == list(artefact.summary["rows"])
    assert written["plan"] == swept.plan.hash
    assert written["counts"] == {"ok": len(swept.plan.points)}


def test_fr25_the_manifest_of_a_warm_member_records_how_it_was_reached(swept: Swept) -> None:
    """The warm-start record reaches the FR-25 manifest, not only the dataset row.

    §5.3.2 requires the warm-start source recorded in provenance and kept out of
    the stage-10 key, and the §6.5 NOTE requires the rungs actually run. Both are
    in the solver group of the member's own ``manifest.json``, which is the file
    a reader of an archived member opens — the dataset is one level up and a
    member has to stand on its own.
    """
    from nanopnp.io.manifest import MANIFEST_FILENAME
    from nanopnp.io.manifest import read as read_manifest

    def _read(directory: str) -> dict[str, object]:
        """Return a written manifest with its float encoding undone.

        ``manifest.json`` is written through ``canonical``, which encodes every
        float as ``{"__f__": <hex>}`` so the digest is exact. That is the right
        thing to hash and the wrong thing to read, which is why §5.3.2 requires a
        decoder to exist beside it — and why a consumer comparing a recorded
        number against a live one has to use it.
        """
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

    # And NUM-34's measurement is in the mesh group, as the requirement asks.
    measured = dict(dict(manifest["geometry_and_mesh"])["wall_distance"])
    assert float(measured["minimum_nm"]) > 0.0
