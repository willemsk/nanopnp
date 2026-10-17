"""VER-36: the sweep plan, its substitution, validation and warm-start forest."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from itertools import product
from pathlib import Path

import pytest

from nanopnp.core.hashing import file_hash
from nanopnp.io.case import CaseValidationError
from nanopnp.pipeline.case import loads_case
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

BASE = """
schema: nanopnp/case/v0.5
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
    path = tmp_path / "base.yaml"
    path.write_text(BASE.format(mesh=tmp_path / "pore.vol", outputs="[current]"), encoding="utf-8")
    return path


def _sweep(base: Path, body: str) -> Path:
    path = base.parent / "sweep.yaml"
    path.write_text(
        f"schema: nanopnp/sweep/v0.5\nname: probe\nbase: {base.name}\naxes:\n{body}",
        encoding="utf-8",
    )
    return path


def _plan(base: Path, body: str) -> SweepPlan:
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


# CON-07
def test_ver36_the_waves_are_contiguous_index_ranges(base: Path) -> None:
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
    with pytest.raises(SweepPlanError, match="not a value this field accepts"):
        _plan(
            base,
            """
  - name: bias
    path: boundary_conditions.bias_V
    values: [0.05, hot]
""",
        )


# NUM-18
def test_ver36_a_point_the_case_schema_refuses_fails_when_the_plan_is_built(base: Path) -> None:
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


# QR-12
def test_ver36_rectification_with_no_opposite_bias_pair_is_refused(tmp_path: Path) -> None:
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
    with pytest.raises(SweepPlanError):
        _plan(
            base,
            """
  - name: bias
    path: boundary_conditions.bias_V
    values: [-0.095, 0.1]
""",
        )


def test_ver36_a_symmetric_bias_axis_supplies_the_pairs(tmp_path: Path) -> None:
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


# QR-06
def test_ver36_the_member_case_carries_the_identity_and_drops_rectification(
    tmp_path: Path,
) -> None:
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
    assert "rectification" in loads_case(base.read_text(encoding="utf-8")).outputs


# VAL-04
def test_ver36_an_axis_over_the_mesh_warns_and_does_not_refuse(base: Path) -> None:
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
    plan = _plan(base, TWO_BY_THREE)
    path = write_plan(plan, tmp_path / "sweep")
    reloaded = read_plan(path)
    assert reloaded.hash == plan.hash
    assert [point.summary() for point in reloaded.points] == [
        point.summary() for point in plan.points
    ]
    assert reloaded.waves() == plan.waves()
    assert reloaded.pairs == plan.pairs


def test_ver36_a_plan_whose_recorded_identities_no_longer_match_is_refused(
    base: Path, tmp_path: Path
) -> None:
    path = write_plan(_plan(base, TWO_BY_THREE), tmp_path / "sweep")
    text = path.read_text(encoding="utf-8")
    document = json.loads(text)
    assert read_plan(path).hash == document["hash"]

    document["points"][1]["assignments"]["bias"] = {"__f__": (0.3).hex()}
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(SweepPlanError, match=r"point 1 .* the plan was edited"):
        read_plan(path)

    document = json.loads(text)
    document["hash"] = "0" * 64
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(SweepPlanError, match="the plan was edited"):
        read_plan(path)


# QR-12
def test_ver36_the_plan_binds_itself_to_the_files_it_hashed(base: Path, tmp_path: Path) -> None:
    mesh = tmp_path / "pore.vol"
    mesh.write_bytes(b"one")
    plan = _plan(base, TWO_BY_THREE)
    assert plan.files == {str(mesh): file_hash(mesh)}
    assert plan.case(0).name.startswith("base-"), "an unchanged file builds members as before"

    other = tmp_path / "other"
    other.mkdir()
    (other / "pore.vol").write_bytes(b"a different mesh")
    (other / "base.yaml").write_text(
        base.read_text(encoding="utf-8").replace(str(mesh), str(other / "pore.vol")),
        encoding="utf-8",
    )
    assert _plan(other / "base.yaml", TWO_BY_THREE).hash != plan.hash

    mesh.write_bytes(b"three, and longer")
    with pytest.raises(SweepPlanError, match=r"different .*pore\.vol") as caught:
        plan.case(0)
    assert file_hash(mesh) in str(caught.value)
    assert plan.files[str(mesh)] in str(caught.value)

    mesh.unlink()
    with pytest.raises(SweepPlanError, match=r"pore\.vol, which is not there now"):
        plan.case(0)


def test_ver36_the_recorded_file_digests_round_trip_and_an_older_plan_is_refused(
    base: Path, tmp_path: Path
) -> None:
    (tmp_path / "pore.vol").write_bytes(b"one")
    plan = _plan(base, TWO_BY_THREE)
    path = write_plan(plan, tmp_path / "sweep")
    reloaded = read_plan(path)
    assert reloaded.files == plan.files and reloaded.hash == plan.hash

    document = json.loads(path.read_text(encoding="utf-8"))
    del document["files"]
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(SweepPlanError, match=r"records no input file digests.*re-plan"):
        read_plan(path)


def test_ver36_a_file_of_another_schema_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "plan.json"
    path.write_text('{"schema": "nanopnp/run/v0.5"}', encoding="utf-8")
    with pytest.raises(SweepPlanError, match=r"nanopnp/run/v0\.5"):
        read_plan(path)


def test_ver36_an_index_the_plan_does_not_enumerate_is_named(base: Path) -> None:
    plan = _plan(base, TWO_BY_THREE)
    with pytest.raises(SweepPlanError, match="there is no point 6"):
        plan.point(6)


# -- the checked-in reference sweep -------------------------------------------


@pytest.fixture(scope="module")
def reference_plan() -> SweepPlan:
    return build_plan(
        loads_sweep(REFERENCE_SWEEP.read_text(encoding="utf-8")),
        source=REFERENCE_SWEEP,
        check_meshes=False,
    )


@pytest.mark.skipif(not REFERENCE_SWEEP.is_file(), reason="run from the repository root")
def test_ver36_the_reference_sweep_parses_and_enumerates_the_section_8_3_grid(
    reference_plan: SweepPlan,
) -> None:
    document = loads_sweep(REFERENCE_SWEEP.read_text(encoding="utf-8"))
    assert document.shape() == (5, 35, 21)
    # The bias origin is 0 V and the salt origin the low end: the deepest point is 4 + 17 + 20 = 41.
    assert document.origins() == (0, 17, 0)

    plan = reference_plan
    assert len(plan.points) == 3675
    assert len(plan.waves()) == 42
    assert max(point.wave for point in plan.points) == 41
    assert sum(1 for point in plan.points if point.parent is None) == 1
    assert not plan.warnings

    root = plan.point(0)
    assert root.wave == 0
    # +5 mV, not 0 V: at zero bias NUM-26's relative check divides by a vanishing scale
    # (knowledge/06-numerics-fem/09-ngsolve-traps-found-by-implementing.md).
    # 17 opposite pairs and one unpaired value keep 3,675 points.
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
