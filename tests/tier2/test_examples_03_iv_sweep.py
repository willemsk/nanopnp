"""VER-46 (with FR-23, FR-24, NUM-11, NUM-26, VER-62): example 03, a bias sweep."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from nanopnp import plot
from nanopnp.core.hashing import decode_floats
from nanopnp.post.qoi import ROUTE_AGREEMENT_TOLERANCE
from nanopnp.sweep.collect import collect
from nanopnp.sweep.plan import read_plan
from nanopnp.validation.examples import CommandResult, copy_example, run_tagged

if TYPE_CHECKING:
    from conftest import NumberStability

pytestmark = pytest.mark.nightly

REPOSITORY = Path(__file__).resolve().parents[2]


def _dataset(directory: Path) -> dict[str, object]:
    decoded = decode_floats(json.loads((directory / "dataset.json").read_text(encoding="utf-8")))
    assert isinstance(decoded, dict)
    return decoded


@pytest.fixture(scope="module")
def ran(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, list[CommandResult]]:
    example = copy_example(
        REPOSITORY / "examples" / "03-iv-sweep",
        tmp_path_factory.mktemp("examples"),
        repository=REPOSITORY,
    )
    return example, run_tagged(example, "run")


# FR-23
def test_ver46_an_uncharged_symmetric_pore_rectifies_to_unity(
    ran: tuple[Path, list[CommandResult]],
) -> None:
    example, _ = ran
    pairs = _dataset(example / "iv-uncharged")["rectification"]
    assert isinstance(pairs, list) and len(pairs) == 1
    ratio = pairs[0]["rectification"]
    assert abs(ratio - 1.0) < ROUTE_AGREEMENT_TOLERANCE, pairs


@pytest.mark.parametrize(("sweep", "points"), [("iv-charged", 4), ("iv-uncharged", 2)])
def test_ver46_every_member_exits_zero_and_every_row_has_a_current(
    ran: tuple[Path, list[CommandResult]], sweep: str, points: int
) -> None:
    example, _ = ran
    with (example / sweep / "dataset.csv").open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(line for line in stream if not line.startswith("#")))
    assert len(rows) == points
    assert all(row["status"] == "ok" and row["exit_class"] == "0" for row in rows), rows
    assert all(row["current_A"] for row in rows)


def test_ver46_the_charged_pore_has_a_ratio_at_each_bias_magnitude(
    ran: tuple[Path, list[CommandResult]],
) -> None:
    example, _ = ran
    pairs = _dataset(example / "iv-charged")["rectification"]
    assert isinstance(pairs, list)
    assert sorted(pair["bias_V"] for pair in pairs) == [0.05, 0.1]
    with (example / "iv.csv").open(encoding="utf-8") as stream:
        assert len(list(csv.DictReader(stream))) == 6


def test_ver62_charged_sweep_holds_the_number_stability_golden(
    ran: tuple[Path, list[CommandResult]], number_stability: NumberStability
) -> None:
    example, _ = ran
    rows = _dataset(example / "iv-charged")["rows"]
    assert isinstance(rows, list) and len(rows) == 4
    values: dict[str, float] = {}
    meshes = set()
    for row in rows:
        member = number_stability.values(row["quantities"])
        values.update({f"point-{row['index']}.{name}": value for name, value in member.items()})
        manifest = decode_floats(
            json.loads((Path(row["directory"]) / "manifest.json").read_text(encoding="utf-8"))
        )
        meshes.add(manifest["geometry_and_mesh"]["content_hash"])
    assert len(meshes) == 1, meshes
    number_stability("example-03-charged", meshes.pop(), {}, values)


def test_every_figure_draws_and_displays(ran: tuple[Path, list[CommandResult]]) -> None:
    directory = ran[0] / "iv-charged"
    artefact = collect(read_plan(directory / "plan.json"), directory)
    figure = plot.figure(artefact)
    assert figure.axes
    assert "data:image/png;base64," in artefact._repr_mimebundle_()["text/html"]
