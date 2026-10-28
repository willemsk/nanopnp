"""VER-46 (with FR-23, FR-25, NUM-11, NUM-26, QR-08, VER-62): example 01, verbatim."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pytest

from nanopnp.core.hashing import decode_floats
from nanopnp.io.artefact import StageInputs
from nanopnp.pipeline.run import offered
from nanopnp.post.export import (
    attribute_name,
    field_scale,
    logarithmic_fields,
    restored,
    solution_fields,
)
from nanopnp.post.qoi import ROUTE_AGREEMENT_TOLERANCE
from nanopnp.validation.examples import CommandResult, copy_example, run_tagged

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import NumberStability
    from nanopnp.pipeline.run import RunResult

REPOSITORY = Path(__file__).resolve().parents[2]


def _read(path: Path) -> dict[str, object]:
    decoded = decode_floats(json.loads(path.read_text(encoding="utf-8")))
    assert isinstance(decoded, dict)
    return decoded


@pytest.fixture(scope="module")
def ran(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, list[CommandResult]]:
    example = copy_example(
        REPOSITORY / "examples" / "01-quickstart",
        tmp_path_factory.mktemp("examples"),
        repository=REPOSITORY,
    )
    return example, run_tagged(example, "run")


def test_ver46_quickstart_runs_and_reproduces(ran: tuple[Path, list[CommandResult]]) -> None:
    example, results = ran
    assert [result.argv[1] for result in results] == ["mesh", "run", "inspect", "reproduce"]
    assert "reproduced" in results[-1].stdout
    assert (example / "run" / "manifest.json").is_file()


# FR-23, NUM-26, QR-04
def test_ver46_quickstart_current_routes_agree(ran: tuple[Path, list[CommandResult]]) -> None:
    example, _ = ran
    quantities = _read(example / "run" / "run.json")["quantities"]
    assert isinstance(quantities, dict)
    assert quantities["routes_checked"] is True
    agreement = quantities["route_agreement"]
    assert isinstance(agreement, dict)
    assert agreement["relative_difference"] < ROUTE_AGREEMENT_TOLERANCE


# FR-25
def test_ver46_quickstart_records_no_deviation(ran: tuple[Path, list[CommandResult]]) -> None:
    example, _ = ran
    deviations = _read(example / "run" / "manifest.json")["deviations"]
    assert isinstance(deviations, dict)
    assert deviations["count"] == 0, deviations


def _mesh_hash(run: Path) -> str:
    group = _read(run / "manifest.json")["geometry_and_mesh"]
    assert isinstance(group, dict)
    return str(group["content_hash"])


def test_ver62_quickstart_holds_the_number_stability_golden(
    ran: tuple[Path, list[CommandResult]], number_stability: NumberStability
) -> None:
    example, _ = ran
    quantities = _read(example / "run" / "run.json")["quantities"]
    assert isinstance(quantities, dict)
    number_stability("example-01", _mesh_hash(example / "run"), quantities)


def test_every_figure_draws_and_displays(
    ran: tuple[Path, list[CommandResult]],
    cached_run: Callable[..., RunResult],
    check_figures: Callable[[RunResult], None],
) -> None:
    check_figures(cached_run(ran[0], "quickstart.case.yaml"))


def test_field_on_a_grid_matches_sample_at(
    ran: tuple[Path, list[CommandResult]], cached_run: Callable[..., RunResult]
) -> None:
    # The figure samples through the export's path; a third route evaluates the restored state
    # at the same nm points, so a swapped (r, z), a missed exp of ln c or a scale of 1 fails.
    result = cached_run(ran[0], "quickstart.case.yaml")
    inputs = StageInputs(
        resolved=result.resolved,
        upstream=offered("solve", result.artefacts),
    )
    solution = result.artefacts["solve"]
    fields = solution_fields(inputs, solution)
    state, _ = restored(inputs, solution)
    mesh = state.space.mesh
    logarithmic = logarithmic_fields(state.model)
    targets = np.array(
        [(r, z) for r in (0.5, 1.5, 3.0, 4.5, 6.0) for z in (4.0, 5.5, 7.0, 8.5, 10.0)]
    )
    checked = 0
    for field in state.model.fields:
        if field.element != "h1" or field.name == "pressure":
            continue
        points, _, values = fields.whole if field.domain is None else fields.fluid
        name = attribute_name(field.name)
        nodes_nm = points * 1e9
        picked = [int(np.argmin(np.linalg.norm(nodes_nm - target, axis=1))) for target in targets]
        for index in picked:
            r_nm, z_nm = nodes_nm[index]
            direct = float(state.component(field.name)(mesh(r_nm, z_nm)))
            if field.name in logarithmic:
                direct = float(np.exp(direct))
            expected = direct * field_scale(field.name, state.model.scales)
            assert values[name][index] == pytest.approx(expected, rel=1e-12, abs=1e-30)
            checked += 1
    assert checked >= 25 * 3


def test_cutline_matches_the_p2_nodes_on_the_axis(
    ran: tuple[Path, list[CommandResult]], cached_run: Callable[..., RunResult]
) -> None:
    # On the four linear triangles of each P2 cell a cutline passes through every node; a
    # corner-only triangulation interpolates across the midsides and misses them.
    pytest.importorskip("matplotlib")
    from matplotlib.tri import LinearTriInterpolator, Triangulation

    from nanopnp.plot import data

    fields = cached_run(ran[0], "quickstart.case.yaml").fields
    for quantity in ("potential", next(k for k in fields.fluid[2] if k.endswith("_mol_m3"))):
        points, cells, values = data.field_values(fields, quantity)
        on_axis = np.flatnonzero(points[:, 0] == 0.0)
        z_nm = points[on_axis, 1] * 1e9
        _, line = data.axial_cutline(fields, quantity, r_nm=0.0, z_nm=z_nm)
        # A grounded node holds round-off about zero, so the floor is relative to the field's size.
        floor = 1e-12 * float(np.abs(values).max())
        np.testing.assert_allclose(line, values[on_axis], rtol=1e-12, atol=floor, err_msg=quantity)
        corners = Triangulation(points[:, 0] * 1e9, points[:, 1] * 1e9, cells[:, :3])
        midsides = np.setdiff1d(on_axis, cells[:, :3])
        coarse = LinearTriInterpolator(corners, values)(
            np.zeros(midsides.size), z_nm[np.searchsorted(on_axis, midsides)]
        )
        assert not np.allclose(coarse, values[midsides], rtol=1e-12, atol=floor), quantity


def test_fields_record_the_solvers_bulk_per_species_and_the_pore_wall(
    ran: tuple[Path, list[CommandResult]], cached_run: Callable[..., RunResult]
) -> None:
    # The bulk a concentration panel is drawn against must be the value the solve imposed on cis
    # and trans, per species: the fluid's end faces hold exactly it. The wall extent sets the
    # lumen window, so it must sit inside the domain it frames.
    fields = cached_run(ran[0], "quickstart.case.yaml").fields
    points, _, values = fields.fluid
    z = points[:, 1]
    assert fields.bulk_mol_m3
    for key, bulk in fields.bulk_mol_m3.items():
        for end in (z.min(), z.max()):
            np.testing.assert_allclose(values[key][z == end], bulk, rtol=1e-9, err_msg=key)
    assert fields.wall_extent_nm is not None
    radius_nm, half_length_nm = fields.wall_extent_nm
    assert 0.0 < radius_nm * 1e-9 < points[:, 0].max()
    assert 0.0 < half_length_nm * 1e-9 < z.max()


def test_default_import_and_walk_load_no_plotting(
    ran: tuple[Path, list[CommandResult]],
) -> None:
    code = (
        "import json, sys\n"
        "import nanopnp, nanopnp.plot\n"
        "from nanopnp.io.store import Store\n"
        "from nanopnp.pipeline.run import run_case\n"
        "run_case('quickstart.case.yaml', store=Store('store'), write=False)\n"
        "print(json.dumps([m for m in ('matplotlib', 'marimo') if m in sys.modules]))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=ran[0], capture_output=True, text=True, check=True
    )
    assert json.loads(result.stdout.strip().splitlines()[-1]) == []
