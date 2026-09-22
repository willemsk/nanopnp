"""VER-36 — the sweep plan: substitution, validation and the warm-start forest.

FR-24's four verbs contradict each other on their face: *dispatch the points as
independent jobs* and *warm-start each solve from a converged neighbour*.
Independent jobs have no predecessors; a warm start is a predecessor. The forest
of §5.3.4 is where they are reconciled, and every property that makes it correct
is a combinatorial fact this module asserts on plans that never solve anything.

Three of them carry the weight.

- **Every edge is one grid step**, so a warm start is a step the envelope walk has
  already demonstrated rather than an extrapolation nobody measured.
- **Wave equals depth, and one wave is pairwise independent**, so running a wave
  in parallel is correct and not merely convenient.
- **Identity is not the index.** Inserting one concentration renumbers every index
  after it; a dataset keyed on the index would relabel last week's results without
  a symptom.

Everything here runs without NGSolve. That is the point of validating the whole
plan before a solve: ``resolve`` is pure Python, and a 3,675-point plan whose
two-thousandth point is inadmissible must fail in seconds.
"""

from __future__ import annotations

import re
import subprocess
import sys
from itertools import product
from pathlib import Path

import pytest

from nanopnp.io.case import CaseValidationError, loads_case
from nanopnp.sweep.document import loads_sweep
from nanopnp.sweep.plan import (
    SweepPlan,
    SweepPlanError,
    build_plan,
    plan_from_document,
    read_plan,
    write_plan,
)

REFERENCE_SWEEP = Path("docs/sweeps/phase1-reference.sweep.yaml")
"""The §8.3 reference sweep, checked in so the deferred twelve-core run is one command."""

BASE = """
schema: nanopnp/case/v1
name: base
inputs:
  mesh: {{path: {mesh}, format: vol, groups: {{default: interface}}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.1
  parameters: willems2020_nacl
  corrections:
    diffusivity:  {{model: willems2020_nacl}}
    mobility:     {{model: willems2020_nacl}}
    viscosity:    {{model: willems2020_nacl}}
    permittivity: {{model: willems2020_nacl}}
    density:      {{model: willems2020_nacl}}
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: epnp-ns, solid_permittivities: {{membrane: 3.2}}}}
numerics: {{continuation: default_ladder}}
outputs: {outputs}
"""


@pytest.fixture
def base(tmp_path: Path) -> Path:
    """Write a base case naming a mesh path, and return it.

    The mesh is never read: nothing in this module builds a plan with
    ``check_meshes``, because what is under test is the combinatorics and the
    validation, both of which are pure Python by design.
    """
    path = tmp_path / "base.yaml"
    path.write_text(BASE.format(mesh=tmp_path / "pore.vol", outputs="[current]"), encoding="utf-8")
    return path


def _sweep(base: Path, body: str) -> Path:
    """Write a sweep document beside ``base`` and return its path."""
    path = base.parent / "sweep.yaml"
    path.write_text(
        f"schema: nanopnp/sweep/v1\nname: probe\nbase: {base.name}\naxes:\n{body}",
        encoding="utf-8",
    )
    return path


def _plan(base: Path, body: str) -> SweepPlan:
    """Build a plan from a sweep document written beside ``base``."""
    return plan_from_document(_sweep(base, body), check_meshes=False)


TWO_BY_THREE = """
  - name: bias
    path: boundary_conditions.bias_V
    values: [-0.05, 0.05]
  - name: salt
    path: electrolyte.concentration_M
    values: [0.1, 0.3, 1.0]
"""


# -- the product, and the order it comes out in -------------------------------


def test_ver36_a_product_of_axes_enumerates_every_point_once(base: Path) -> None:
    """A 2 x 3 grid is six points, each combination present exactly once."""
    plan = _plan(base, TWO_BY_THREE)
    assert len(plan.points) == 6
    found = {
        (
            point.assignments["boundary_conditions.bias_V"],
            point.assignments["electrolyte.concentration_M"],
        )
        for point in plan.points
    }
    assert found == set(product((-0.05, 0.05), (0.1, 0.3, 1.0)))
    assert [point.index for point in plan.points] == list(range(6))


def test_ver36_an_assignment_valued_axis_moves_several_paths_together(base: Path) -> None:
    """One axis, several case-file fields — which is how the §8.3 physics cases move.

    An assignment is how several paths are varied as one, so there is no ``zip:``
    operator and no second concept: the five physics configurations of the
    reference sweep each move six correction switches at once, and they are one
    axis of length five rather than six axes that must be kept in step.
    """
    plan = _plan(
        base,
        """
  - name: physics
    assignments:
      - {electrolyte.corrections.diffusivity.model: none,
         electrolyte.corrections.mobility.model: none,
         electrolyte.corrections.steric.model: none}
      - {electrolyte.corrections.diffusivity.model: willems2020_nacl,
         electrolyte.corrections.mobility.model: willems2020_nacl,
         electrolyte.corrections.steric.model: borukhov}
""",
    )
    assert len(plan.points) == 2
    assert plan.points[0].assignments == {
        "electrolyte.corrections.diffusivity.model": "none",
        "electrolyte.corrections.mobility.model": "none",
        "electrolyte.corrections.steric.model": "none",
    }
    assert plan.points[1].assignments["electrolyte.corrections.steric.model"] == "borukhov"


def test_ver36_two_axes_writing_one_path_are_refused(base: Path) -> None:
    """One would silently overwrite the other, and the dataset would report a lie.

    A column of the collected table whose values never reached the case is worse
    than a missing column: it says the sweep varied a field it held fixed.
    """
    with pytest.raises(
        SweepPlanError, match=re.escape("both write 'physics.dielectric_gradient_forces'")
    ):
        _plan(
            base,
            """
  - name: one
    assignments: [{physics.dielectric_gradient_forces: true},
                  {physics.dielectric_gradient_forces: false}]
  - name: two
    assignments: [{physics.dielectric_gradient_forces: true}]
""",
        )


def test_ver36_an_axis_declaring_the_same_value_twice_is_refused(base: Path) -> None:
    """Two identical points would key one dataset row and be reported once."""
    with pytest.raises(SweepPlanError, match="identical assignments"):
        _plan(
            base,
            """
  - name: bias
    path: boundary_conditions.bias_V
    values: [0.05, 0.05]
""",
        )


# -- identity, and what it is not ---------------------------------------------


def test_ver36_a_point_identity_is_stable_across_processes(base: Path) -> None:
    """The identity is a content hash, so it does not move with PYTHONHASHSEED.

    Asserted in a *fresh interpreter* with the seed varied, because Python's
    ``hash`` is randomised per process and a dictionary iteration order that
    leaked into the digest would make a resumed sweep miss every cache entry it
    had — which is a slow sweep, not a wrong one, and so would never be noticed.
    """
    plan = _plan(base, TWO_BY_THREE)
    expected = [point.point_id for point in plan.points]
    script = (
        "from pathlib import Path;"
        "from nanopnp.sweep.plan import plan_from_document;"
        f"plan = plan_from_document(Path({str(base.parent / 'sweep.yaml')!r}), check_meshes=False);"
        "print(','.join(point.point_id for point in plan.points))"
    )
    found = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
        env={"PYTHONHASHSEED": "12345", "PATH": "/usr/bin:/bin"},
    )
    assert found.stdout.strip().split(",") == expected


def test_ver36_inserting_a_value_moves_the_index_and_not_the_identity(base: Path) -> None:
    """§5.3.4: the identity keys the dataset, the index keys the dispatch.

    Inserting one concentration renumbers every index after it, and a dataset
    keyed on the index would silently relabel last week's results. This is the
    test that says the identity does not move — and, in the same breath, that the
    index does, so the assertion is not vacuous.
    """
    before = {point.point_id: point.index for point in _plan(base, TWO_BY_THREE).points}
    after = _plan(
        base,
        """
  - name: bias
    path: boundary_conditions.bias_V
    values: [-0.05, 0.05]
  - name: salt
    path: electrolyte.concentration_M
    values: [0.1, 0.2, 0.3, 1.0]
""",
    )
    shared = {point.point_id: point.index for point in after.points if point.point_id in before}
    assert len(shared) == 6, "every point of the smaller grid is still in the larger one"
    assert any(before[identity] != index for identity, index in shared.items()), (
        "an inserted value must renumber something, or this test asserts nothing"
    )


# -- the forest ---------------------------------------------------------------


def test_ver36_every_point_has_one_parent_one_grid_step_nearer_the_origin(base: Path) -> None:
    """The property that makes a warm start a step the envelope walk demonstrated.

    Exactly one parent, exactly one axis moved, exactly one index — and towards
    the origin. An edge of two steps would be an extrapolation nobody measured,
    and an edge *away* from the origin would climb the ladder at the hard corner.
    """
    plan = _plan(base, TWO_BY_THREE)
    origins = (0, 0)
    roots = [point for point in plan.points if point.parent is None]
    assert len(roots) == 1
    assert roots[0].coordinates == origins

    for point in plan.points:
        if point.parent is None:
            continue
        parent = plan.point(point.parent)
        moved = [
            axis
            for axis, (here, there) in enumerate(
                zip(point.coordinates, parent.coordinates, strict=True)
            )
            if here != there
        ]
        assert len(moved) == 1, f"point {point.index} moves {len(moved)} axes from its parent"
        axis = moved[0]
        assert abs(point.coordinates[axis] - parent.coordinates[axis]) == 1
        assert abs(parent.coordinates[axis] - origins[axis]) < abs(
            point.coordinates[axis] - origins[axis]
        ), "the parent must be nearer the origin, not further"


def test_ver36_the_wave_is_the_depth_and_a_wave_is_pairwise_independent(base: Path) -> None:
    """``wave == sum |i_j - o_j|``, and no point of a wave is another's ancestor.

    Independence is what licenses running a wave in parallel. Asserted by walking
    each point's whole ancestry rather than only its parent: a wave containing a
    grandparent would still have no parent-child pair in it and would still be
    wrong.
    """
    plan = _plan(base, TWO_BY_THREE)
    for point in plan.points:
        assert point.wave == sum(abs(index) for index in point.coordinates)

    by_wave: dict[int, list[int]] = {}
    for point in plan.points:
        by_wave.setdefault(point.wave, []).append(point.index)

    def ancestry(index: int) -> set[int]:
        found: set[int] = set()
        parent = plan.point(index).parent
        while parent is not None:
            found.add(parent)
            parent = plan.point(parent).parent
        return found

    for indices in by_wave.values():
        for index in indices:
            assert not ancestry(index) & set(indices)


def test_ver36_the_waves_are_contiguous_index_ranges(base: Path) -> None:
    """A wave is a range a job array can be submitted over, and nothing else.

    §5.3.4 requires the ordering for exactly this: the scheduler integration this
    project does is printing these ranges, and a wave that were not contiguous
    would need a list of indices instead — which is the point at which somebody
    writes a SLURM script generator, which CON-07 forbids.
    """
    plan = _plan(base, TWO_BY_THREE)
    spans = plan.waves()
    assert spans[0][0] == 0
    assert spans[-1][1] == len(plan.points)
    for wave, (first, last) in enumerate(spans):
        assert last > first
        assert all(plan.point(index).wave == wave for index in range(first, last))
    assert all(spans[wave][1] == spans[wave + 1][0] for wave in range(len(spans) - 1))


def test_ver36_a_symmetric_axis_roots_at_its_declared_origin_and_walks_both_ways(
    base: Path,
) -> None:
    """An axis running -0.2 to +0.2 has its *hardest* corner at index 0.

    Rooting at the first declared value would climb the ladder cold at -200 mV
    and then walk 400 mV in one direction. ``origin`` is the envelope test's own
    behaviour made declarative: from 0 V the forest walks outward each way, and
    the deepest point is 2 rather than 4.
    """
    plan = _plan(
        base,
        """
  - name: bias
    path: boundary_conditions.bias_V
    origin: 2
    values: [-0.2, -0.1, 0.0, 0.1, 0.2]
""",
    )
    root = next(point for point in plan.points if point.parent is None)
    assert root.assignments["boundary_conditions.bias_V"] == 0.0
    assert max(point.wave for point in plan.points) == 2
    assert len(plan.waves()) == 3
    assert len(plan.waves()[1]) and plan.waves()[1] == (1, 3), "one step each way"


def test_ver36_an_origin_off_the_end_of_its_axis_is_refused(base: Path) -> None:
    """A plan rooted at a point that does not exist is refused where it is written."""
    with pytest.raises(CaseValidationError, match="origin 9"):
        _plan(
            base,
            """
  - name: bias
    path: boundary_conditions.bias_V
    origin: 9
    values: [-0.1, 0.1]
""",
        )


# -- what the plan refuses ----------------------------------------------------


def test_ver36_a_misspelt_path_is_refused_naming_the_component_and_the_prefix(base: Path) -> None:
    """IF-03's diagnostic, applied to a sweep axis before any point is built."""
    with pytest.raises(SweepPlanError) as raised:
        _plan(
            base,
            """
  - name: bias
    path: boundary_conditions.bais_V
    values: [-0.05, 0.05]
""",
        )
    message = str(raised.value)
    assert "axis 'bias'" in message
    assert "boundary_conditions has no 'bais_V'" in message
    assert "did you mean 'bias_V'" in message


def test_ver36_a_value_of_the_wrong_declared_type_is_refused_at_plan_time(base: Path) -> None:
    """A string where a float belongs, named before the plan commits to any point.

    Re-validating each substituted document would catch it too, but only per
    point and only after the plan had enumerated thousands of them; the walk
    over the schema knows the declared type and says so.
    """
    with pytest.raises(SweepPlanError, match="not a value this field accepts"):
        _plan(
            base,
            """
  - name: bias
    path: boundary_conditions.bias_V
    values: [0.05, hot]
""",
        )


def test_ver36_a_point_the_case_schema_refuses_fails_when_the_plan_is_built(base: Path) -> None:
    """The NUM-18 ladder refusal, reached through substitution rather than by hand.

    ``physics.flow: false`` with ``continuation: default_ladder`` is refused by
    :func:`~nanopnp.io.case.resolve` — flow is enabled at rung 6, so a run
    without it is not a rung of this ladder but a different run. The plan runs
    that refusal over every point *before a single solve*, which is the whole
    argument for resolving at plan time, and the message names the point.
    """
    with pytest.raises(SweepPlanError) as raised:
        _plan(
            base,
            """
  - name: flow
    path: physics.flow
    values: [true, false]
""",
        )
    message = str(raised.value)
    assert "point 1" in message
    assert "physics.flow" in message
    assert "default_ladder" in message or "ladder" in message


def test_ver36_rectification_with_no_opposite_bias_pair_is_refused(tmp_path: Path) -> None:
    """QR-12's shape: name the gate and what it wanted, rather than a column of nulls.

    ``rectification`` is ``|I(+V)|/|I(-V)|`` and §5.3.1 already says the second
    bias can only come from a sweep. A sweep whose bias axis is not symmetric
    cannot supply it, and reporting an empty column would leave a reader to work
    out why.
    """
    base = tmp_path / "base.yaml"
    base.write_text(
        BASE.format(mesh=tmp_path / "pore.vol", outputs="[current, rectification]"),
        encoding="utf-8",
    )
    with pytest.raises(SweepPlanError) as raised:
        _plan(
            base,
            """
  - name: bias
    path: boundary_conditions.bias_V
    values: [0.05, 0.1]
""",
        )
    assert "boundary_conditions.bias_V" in str(raised.value)
    assert "exactly opposite" in str(raised.value)


def test_ver36_a_symmetric_bias_axis_supplies_the_pairs(tmp_path: Path) -> None:
    """And the pairing is exact, not approximate.

    A tolerance would let 100 mV and -95 mV be reported as a rectification, which
    is a ratio between two unrelated operating points wearing the name of one.
    """
    base = tmp_path / "base.yaml"
    base.write_text(
        BASE.format(mesh=tmp_path / "pore.vol", outputs="[current, rectification]"),
        encoding="utf-8",
    )
    plan = _plan(
        base,
        """
  - name: bias
    path: boundary_conditions.bias_V
    origin: 1
    values: [-0.05, 0.0, 0.05, 0.1]
""",
    )
    assert plan.rectification
    assert len(plan.pairs) == 1
    forward, reverse = plan.pairs[0]
    assert plan.point(forward).assignments["boundary_conditions.bias_V"] == 0.05
    assert plan.point(reverse).assignments["boundary_conditions.bias_V"] == -0.05


def test_ver36_the_member_case_carries_the_identity_and_drops_rectification(
    tmp_path: Path,
) -> None:
    """A member is named for its point and does not ask for the two-point quantity.

    ``name`` reaches the manifest and the run directory and nothing that keys a
    solve, so rewriting it moves no field and costs no cache entry — and a member
    whose own manifest cannot say which point it is is not evidence (QR-06).
    """
    base = tmp_path / "base.yaml"
    base.write_text(
        BASE.format(mesh=tmp_path / "pore.vol", outputs="[current, rectification]"),
        encoding="utf-8",
    )
    plan = _plan(
        base,
        """
  - name: bias
    path: boundary_conditions.bias_V
    origin: 0
    values: [0.05, -0.05]
""",
    )
    member = plan.case(0)
    assert member.name == f"base-{plan.point(0).point_id}"
    assert "rectification" not in member.outputs
    assert "current" in member.outputs
    assert member.boundary_conditions.bias_V == 0.05
    # And the base case is untouched by any of it.
    assert "rectification" in loads_case(base.read_text(encoding="utf-8")).outputs


def test_ver36_an_axis_over_the_mesh_warns_and_does_not_refuse(base: Path) -> None:
    """The author's ruling of 8 September 2026: warn, do not refuse.

    ``transfer`` refuses a cross-mesh interpolation deliberately, so the forest
    degenerates to one-point trees and every member is cold — correct, only
    slower. VAL-04's mesh-convergence study is a sweep of exactly that shape, so
    refusing it would refuse a study the specification asks for.
    """
    plan = _plan(
        base,
        """
  - name: mesh
    assignments:
      - {inputs.mesh.path: coarse.vol}
      - {inputs.mesh.path: fine.vol}
""",
    )
    assert len(plan.points) == 2
    assert len(plan.warnings) == 1
    assert "inputs.mesh.path" in plan.warnings[0]
    assert "cold" in plan.warnings[0] or "full NUM-18 ladder" in plan.warnings[0]


# -- the plan file ------------------------------------------------------------


def test_ver36_a_plan_round_trips_through_its_file(base: Path, tmp_path: Path) -> None:
    """Written through ``canonical`` and read back to the same points and hash.

    The floats matter: the bias axis is the thing every member is keyed on, and
    a plan whose values came back as ``0.049999999999999996`` would dispatch a
    different sweep from the one that was planned. Canonical JSON encodes each
    float by ``float.hex()``, which is why this is equality and not a tolerance.
    """
    plan = _plan(base, TWO_BY_THREE)
    path = write_plan(plan, tmp_path / "sweep")
    reloaded = read_plan(path)
    assert reloaded.hash == plan.hash
    assert [point.summary() for point in reloaded.points] == [
        point.summary() for point in plan.points
    ]
    assert reloaded.waves() == plan.waves()
    assert reloaded.pairs == plan.pairs


def test_ver36_a_file_of_another_schema_is_refused(tmp_path: Path) -> None:
    """Read rather than rebuilt, so the schema is what says the file is a plan."""
    path = tmp_path / "plan.json"
    path.write_text('{"schema": "nanopnp/run/v1"}', encoding="utf-8")
    with pytest.raises(SweepPlanError, match="nanopnp/run/v1"):
        read_plan(path)


def test_ver36_an_index_the_plan_does_not_enumerate_is_named(base: Path) -> None:
    """A job array submitted over the wrong range says how many points there are."""
    plan = _plan(base, TWO_BY_THREE)
    with pytest.raises(SweepPlanError, match="there is no point 6"):
        plan.point(6)


# -- the checked-in reference sweep -------------------------------------------


@pytest.fixture(scope="module")
def reference_plan() -> SweepPlan:
    """Build the §8.3 reference plan once for the two tests that read it.

    ``build_plan`` resolves all 3,675 members; building it once per test doubled
    the cost of the slowest checks in Tier 1 for no additional assertion.
    """
    return build_plan(
        loads_sweep(REFERENCE_SWEEP.read_text(encoding="utf-8")),
        source=REFERENCE_SWEEP,
        check_meshes=False,
    )


@pytest.mark.skipif(not REFERENCE_SWEEP.is_file(), reason="run from the repository root")
def test_ver36_the_reference_sweep_parses_and_enumerates_the_section_8_3_grid(
    reference_plan: SweepPlan,
) -> None:
    """Everything about the deferred twelve-core run that can be verified in seconds.

    The §8.3 datum is 3,675 solves — 5 physics cases x 35 bias values x 21 salt
    concentrations — and the author runs it at the end of Phase 1. What WP11 owes
    that run is that it be one command against a document under version control,
    so this asserts the document *is* that: it parses, its base case resolves,
    and its plan is the grid the specification names, in the 42 waves the forest
    predicts. The mesh is not checked (``check_meshes=False``): it is 44,316
    triangles and is not a repository file.
    """
    document = loads_sweep(REFERENCE_SWEEP.read_text(encoding="utf-8"))
    assert document.shape() == (5, 35, 21)
    # The bias origin is 0 V and the salt origin is the low end, so the deepest
    # point is 4 + 17 + 20 = 41 and there are 42 waves.
    assert document.origins() == (0, 17, 0)

    plan = reference_plan
    assert len(plan.points) == 3675
    assert len(plan.waves()) == 42
    assert max(point.wave for point in plan.points) == 41
    assert sum(1 for point in plan.points if point.parent is None) == 1
    assert not plan.warnings

    root = plan.point(0)
    assert root.wave == 0
    # +5 mV, not 0 V: at exactly zero bias the current is zero and NUM-26's
    # *relative* route check divides by a vanishing scale and aborts the member
    # (`.knowledge/06` section 8.5). The axis therefore carries 17
    # exactly-opposite pairs plus one unpaired value at the easy corner, which
    # keeps the section 8.3 grid at 3,675 points and 1,785 pairs.
    assert root.assignments["boundary_conditions.bias_V"] == 0.005
    assert root.assignments["electrolyte.concentration_M"] == 0.05
    assert 0.0 not in set(
        loads_sweep(REFERENCE_SWEEP.read_text(encoding="utf-8")).axes[1].values or []
    )

    # 5 physics cases x 17 positive biases x 21 concentrations.
    assert plan.rectification
    assert len(plan.pairs) == 5 * 17 * 21


@pytest.mark.skipif(not REFERENCE_SWEEP.is_file(), reason="run from the repository root")
def test_ver36_the_reference_sweep_resolves_a_sample_of_its_members(
    reference_plan: SweepPlan,
) -> None:
    """``build_plan`` resolved all 3,675; this says what that means for a reader.

    Named separately because the assertion above would pass on a plan that
    enumerated the right *number* of inadmissible points: ``build_plan`` resolves
    every one of them and would have raised, and this makes the consequence
    visible — each member is a runnable case with the physics its axis selected.
    """
    plan = reference_plan
    classical = plan.case(0)
    assert classical.electrolyte.corrections.diffusivity.model == "none"
    assert classical.numerics.continuation == "default_ladder"

    corrected = next(
        plan.case(point.index)
        for point in plan.points
        if point.assignments.get("electrolyte.corrections.steric.model") == "borukhov"
    )
    assert corrected.electrolyte.corrections.diffusivity.wall is True
    assert corrected.physics.model == "epnp-ns"
