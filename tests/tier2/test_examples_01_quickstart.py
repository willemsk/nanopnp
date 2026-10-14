"""VER-46 (with FR-23, FR-25, NUM-11, NUM-26, QR-08, VER-62): example 01, verbatim."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from nanopnp.core.hashing import decode_floats
from nanopnp.post.qoi import ROUTE_AGREEMENT_TOLERANCE
from nanopnp.validation.examples import CommandResult, copy_example, run_tagged

if TYPE_CHECKING:
    from conftest import NumberStability

pytestmark = pytest.mark.extended

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
