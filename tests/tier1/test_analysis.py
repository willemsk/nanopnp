"""FR-32: the comparison's difference of two runs' fields over their fluids' overlap."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import numpy as np
import pytest

from nanopnp.core.typing import Expression, Mesh, Numeric
from nanopnp.geometry.pore import CylinderPore
from nanopnp.mesh.primitives import ELECTROLYTE_DOMAINS, mesh_cylinder_pore
from nanopnp.physics import models
from nanopnp.physics.models import ModelSolution
from nanopnp.post.export import (
    SolutionFields,
    field_scale,
    fields_of,
    read_solution_fields,
    write_solution_fields,
)
from nanopnp.post.fields import (
    field_at,
    field_difference,
    field_grid,
    joint_range,
    subdivided,
)

# The two runs differ in lumen radius, membrane thickness, box and mesh size.
FIRST = CylinderPore(pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0)
SECOND = CylinderPore(pore_radius_nm=2.5, membrane_thickness_nm=8.0, reservoir_radius_nm=12.0)

# Round-off of a linear field read through a P2 Set and the four-triangle split.
EXACT = 1e-10

# A dyadic step: a window of this width has its one cell's centre 2^-10 nm, about 10^-3 nm,
# from its edge, with no rounding in the grid's arithmetic.
STEP_NM = 2.0**-9

Linear = Callable[[Numeric, Numeric], Numeric]


def _linear(a: float, b: float, c: float) -> Linear:
    def evaluate(r: Numeric, z: Numeric) -> Numeric:
        return a * r + b * z + c

    return evaluate


FIRST_FIELDS: dict[str, Linear] = {
    "potential": _linear(0.4, -0.3, 0.1),
    "c_Na+": _linear(-0.02, 0.05, 1.0),
    "c_Cl-": _linear(0.03, 0.01, 1.2),
    "velocity_r": _linear(0.2, 0.1, -0.3),
    "velocity_z": _linear(-0.1, 0.6, 0.2),
    "pressure": _linear(0.8, -1.3, 0.25),
}

SECOND_FIELDS: dict[str, Linear] = {
    "potential": _linear(-0.2, 0.5, -0.4),
    "c_Na+": _linear(0.04, -0.02, 0.9),
    "c_Cl-": _linear(-0.01, 0.07, 1.1),
    "velocity_r": _linear(0.5, -0.2, 0.1),
    "velocity_z": _linear(0.3, 0.2, -0.5),
    "pressure": _linear(-0.6, 0.9, 1.5),
}

# Quantity, the model field it reads, and the attribute it is written under.
QUANTITIES: tuple[tuple[str, str], ...] = (
    ("potential", "potential"),
    ("c_Na+_mol_m3", "c_Na+"),
    ("c_Cl-_mol_m3", "c_Cl-"),
    ("u_r", "velocity_r"),
    ("u_z", "velocity_z"),
    ("p_Pa", "pressure"),
)


def _populated(mesh: Mesh, values: dict[str, Linear]) -> ModelSolution:
    import ngsolve as ngs

    model = models.create("epnp-ns")
    space = model.space(mesh)
    state = model.cold_state(mesh)
    fluid = mesh.Materials(ELECTROLYTE_DOMAINS)
    for field, component in zip(model.fields, state.components, strict=True):
        if field.element == "number":
            continue
        target: Expression = (
            ngs.CF((values["velocity_r"](ngs.x, ngs.y), values["velocity_z"](ngs.x, ngs.y)))
            if field.element == "vector_h1"
            else values[field.name](ngs.x, ngs.y)
        )
        if field.domain is None:
            component.Set(target)
        else:
            component.Set(target, definedon=fluid)
    distance = ngs.GridFunction(ngs.H1(mesh, order=2))
    distance.Set(ngs.CF(1.0))
    return ModelSolution(model=model, space=space, state=state, wall_distance_nm=distance)


@pytest.fixture(scope="module")
def runs() -> tuple[SolutionFields, SolutionFields, ModelSolution]:
    first = _populated(mesh_cylinder_pore(FIRST, maxh_nm=4.0, wall_h_nm=1.0), FIRST_FIELDS)
    second = _populated(mesh_cylinder_pore(SECOND, maxh_nm=3.0, wall_h_nm=0.7), SECOND_FIELDS)
    return fields_of(first), fields_of(second), first


def _scale(field: str, solution: ModelSolution) -> float:
    model_field = "velocity" if field.startswith("velocity") else field
    return field_scale(model_field, solution.model.scales)


def _one_cell(r_nm: float, z_nm: float) -> tuple[float, float, float, float]:
    """Return a window whose one cell is centred on ``(r_nm, z_nm)``."""
    half = 0.5 * STEP_NM
    return (r_nm - half, r_nm + half, z_nm - half, z_nm + half)


def test_fr32_each_fields_difference_is_the_analytic_one_on_the_overlap(
    runs: tuple[SolutionFields, SolutionFields, ModelSolution],
) -> None:
    # A P2 field holds a linear one, and the split reads it exactly: a wrong weight, a swapped
    # run or a node read from the other mesh moves the difference by far more than round-off.
    first, second, solution = runs
    for quantity, field in QUANTITIES:
        found = field_difference(first, second, quantity, cells=20_000)
        r, z = np.meshgrid(found.r_nm, found.z_nm)
        scale = _scale(field, solution)
        expected = scale * (SECOND_FIELDS[field](r, z) - FIRST_FIELDS[field](r, z))
        kept = np.isfinite(found.difference)
        assert kept.sum() > 10_000, quantity
        span = np.ptp(expected[kept])
        np.testing.assert_allclose(
            found.difference[kept], expected[kept], rtol=0.0, atol=EXACT * span, err_msg=quantity
        )
        np.testing.assert_allclose(
            found.first[kept],
            scale * FIRST_FIELDS[field](r, z)[kept],
            rtol=0.0,
            atol=EXACT * np.ptp(found.first[kept]),
            err_msg=quantity,
        )


def test_fr32_one_run_against_itself_differs_by_exactly_zero(
    runs: tuple[SolutionFields, SolutionFields, ModelSolution],
) -> None:
    # Any asymmetry in reading the two runs (a different split, a different set) shows here; the
    # second copy is sampled again from the state, so no array is shared with the first.
    first, _, solution = runs
    again = fields_of(solution)
    for quantity, _ in QUANTITIES:
        found = field_difference(first, again, quantity, cells=20_000)
        kept = np.isfinite(found.difference)
        assert kept.any()
        assert (found.difference[kept] == 0.0).all(), quantity


def test_fr32_a_cell_is_kept_only_inside_both_fluids(
    runs: tuple[SolutionFields, SolutionFields, ModelSolution],
) -> None:
    # About 10^-3 nm either side of each run's wall: a mask from one run alone, or from the whole
    # domain, keeps a cell in a membrane.
    first, second, _ = runs
    inside = 1.0 - 2.0**-10
    for centre, kept in (
        ((FIRST.pore_radius_nm - 2.0**-10, 0.0), True),
        ((FIRST.pore_radius_nm + 2.0**-10, 0.0), False),
        ((SECOND.pore_radius_nm - 2.0**-10, 0.0), False),
        ((5.0, SECOND.half_thickness_nm - 2.0**-10), False),
        ((5.0, SECOND.half_thickness_nm + 2.0**-10), True),
        ((inside, FIRST.half_thickness_nm + 1.0), True),
    ):
        for quantity in ("potential", "c_Na+_mol_m3"):
            found = field_difference(first, second, quantity, window_nm=_one_cell(*centre), cells=1)
            assert found.difference.shape == (1, 1)
            assert np.isfinite(found.difference[0, 0]) == kept, (centre, quantity)


def test_fr32_the_potential_is_masked_to_the_fluids_overlap(
    runs: tuple[SolutionFields, SolutionFields, ModelSolution],
) -> None:
    # The potential is solved on the membrane too; its difference there would compare a solid's
    # field with a fluid's.
    first, second, _ = runs
    in_first_membrane = (FIRST.pore_radius_nm + 0.25, 0.0)
    assert np.isfinite(field_at(first, "potential", *in_first_membrane))
    assert np.isfinite(field_at(second, "potential", *in_first_membrane))
    assert np.isnan(field_at(first, "c_Na+_mol_m3", *in_first_membrane))
    found = field_difference(
        first, second, "potential", window_nm=_one_cell(*in_first_membrane), cells=1
    )
    assert np.isnan(found.difference[0, 0])


def test_fr32_the_grid_is_the_rule_over_both_boxes_overlap(
    runs: tuple[SolutionFields, SolutionFields, ModelSolution],
) -> None:
    # A grid over either run's box alone would read the other past its domain, and one off the
    # rule would place the map's cells where its axes do not say.
    first, second, _ = runs
    half = FIRST.half_thickness_nm + FIRST.reservoir_radius_nm
    box = (0.0, FIRST.reservoir_radius_nm, -half, half)
    for pair in ((first, second), (second, first)):
        found = field_difference(*pair, "potential", window_nm=(-5.0, 30.0, -40.0, 40.0), cells=400)
        width, height = box[1] - box[0], box[3] - box[2]
        spacing = np.sqrt(width * height / 400)
        n_r, n_z = int(np.ceil(width / spacing)), int(np.ceil(height / spacing))
        np.testing.assert_allclose(
            found.r_nm, box[0] + (np.arange(n_r) + 0.5) * width / n_r, rtol=0, atol=1e-9
        )
        np.testing.assert_allclose(
            found.z_nm, box[2] + (np.arange(n_z) + 0.5) * height / n_z, rtol=0, atol=1e-9
        )
        assert found.difference.shape == (n_z, n_r)


def test_fr32_a_point_off_the_mesh_is_nan_without_a_table_to_reach_it(
    runs: tuple[SolutionFields, SolutionFields, ModelSolution],
) -> None:
    # A probe typed 10 um away, or not a number, sized the bucket table to the gap: gigabytes.
    first, _, _ = runs
    found = field_at(
        first,
        "potential",
        np.array([1.0, 1.0e4, np.nan, FIRST.reservoir_radius_nm + 2.0**-10]),
        np.array([0.0, 1.0e4, 0.0, 0.0]),
    )
    assert np.isfinite(found[0]) and np.isnan(found[1:]).all()


def test_fr32_each_point_is_read_on_the_lowest_split_triangle_holding_it(
    runs: tuple[SolutionFields, SolutionFields, ModelSolution],
) -> None:
    # A linear field reads the same on any triangle; r^2 + z^2 does not, so a wrong owner or a
    # weight paired with another node shows. The oracle tests every triangle of the split.
    first, _, _ = runs
    points, cells, _ = first.fluid
    r_nm, z_nm = points[:, 0] * 1e9, points[:, 1] * 1e9
    quadratic = SolutionFields(
        model=first.model,
        whole=first.whole,
        fluid=(points, cells, {"c_Na+_mol_m3": r_nm**2 + z_nm**2}),
    )
    zero = SolutionFields(
        model=first.model,
        whole=first.whole,
        fluid=(points.copy(), cells.copy(), {"c_Na+_mol_m3": np.zeros(len(points))}),
    )
    found = field_difference(
        zero, quadratic, "c_Na+_mol_m3", window_nm=(0.0, 4.0, -5.0, 5.0), cells=300
    )
    grid_r, grid_z = np.meshgrid(found.r_nm, found.z_nm)
    at = np.column_stack([grid_r.ravel(), grid_z.ravel()])
    triangles = subdivided(cells)
    corners = np.column_stack([r_nm, z_nm])[triangles]
    v0, e1, e2 = corners[:, 0], corners[:, 1] - corners[:, 0], corners[:, 2] - corners[:, 0]
    inverse = np.linalg.inv(np.stack([e1, e2], axis=2))
    local = np.einsum("tij,ptj->pti", inverse, at[:, None, :] - v0[None])
    weights = np.concatenate([1.0 - local.sum(axis=2, keepdims=True), local], axis=2)
    inside = (weights >= -1e-12).all(axis=2)
    owner = np.where(inside.any(axis=1), inside.argmax(axis=1), -1)
    values = (r_nm**2 + z_nm**2)[triangles]
    expected = np.where(
        owner >= 0,
        np.einsum("pk,pk->p", weights[np.arange(len(at)), owner], values[owner]),
        np.nan,
    ).reshape(grid_r.shape)
    np.testing.assert_array_equal(np.isnan(found.difference), np.isnan(expected))
    kept = np.isfinite(expected)
    assert kept.sum() > 100
    np.testing.assert_allclose(found.difference[kept], expected[kept], rtol=1e-12, atol=1e-12)


def test_fr32_a_quantity_either_run_lacks_is_refused_naming_both(
    runs: tuple[SolutionFields, SolutionFields, ModelSolution],
) -> None:
    first, second, _ = runs
    with pytest.raises(KeyError, match=r"first holds .*phi_V.*second holds"):
        field_difference(first, second, "c_K+_mol_m3")


def test_fr32_one_runs_map_and_the_joint_range(
    runs: tuple[SolutionFields, SolutionFields, ModelSolution],
) -> None:
    # One run's map spans its own field's box; the pair's range spans both runs' nodal values.
    first, second, solution = runs
    r, z, values = field_grid(first, "c_Na+_mol_m3", cells=5_000)
    grid_r, grid_z = np.meshgrid(r, z)
    kept = np.isfinite(values)
    expected = _scale("c_Na+", solution) * FIRST_FIELDS["c_Na+"](grid_r, grid_z)
    np.testing.assert_allclose(
        values[kept], expected[kept], rtol=0.0, atol=EXACT * np.ptp(expected[kept])
    )
    low, high = joint_range(first, second, "potential")
    nodal = np.concatenate([first.whole[2]["phi_V"], second.whole[2]["phi_V"]])
    assert (low, high) == (nodal.min(), nodal.max())


def test_fr27_a_fields_file_reads_back_array_equal_with_its_solve(
    runs: tuple[SolutionFields, SolutionFields, ModelSolution], tmp_path: Path
) -> None:
    # The server samples maps from this file alone: a dropped set, a renamed attribute or a lost
    # bulk value would draw another run's field, or none, without NGSolve to notice.
    first, _, _ = runs
    path = write_solution_fields(first, tmp_path / "viewer" / "fields.npz", solve="a" * 64)
    read, solve = read_solution_fields(path)
    assert solve == "a" * 64
    assert read.model == first.model
    assert read.wall_extent_nm == first.wall_extent_nm
    assert read.bulk_mol_m3 == first.bulk_mol_m3
    for held, written in ((read.whole, first.whole), (read.fluid, first.fluid)):
        np.testing.assert_array_equal(held[0], written[0])
        np.testing.assert_array_equal(held[1], written[1])
        assert held[2].keys() == written[2].keys()
        for key, values in written[2].items():
            np.testing.assert_array_equal(held[2][key], values)
    assert not list(tmp_path.glob("viewer/*.partial.npz"))
