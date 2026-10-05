"""VER-46 — example 01, the quick start, executed verbatim (QR-08, FR-23, FR-25).

The README's four commands run from a copy of ``examples/01-quickstart``: mesh,
run, inspect, reproduce. ``nanopnp reproduce`` exits nonzero unless every
recorded scalar comes back within tolerance from a fresh store, so its exit
status *is* the QR-08 oracle. The other two are read from the run record: the
FR-23 routes agree to the NUM-26 tolerance, and a case at every validated default
records no deviation. Stabilisation is ``none`` (NUM-11).
"""

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
    """Return a record written through ``canonical``, its floats decoded."""
    decoded = decode_floats(json.loads(path.read_text(encoding="utf-8")))
    assert isinstance(decoded, dict)
    return decoded


@pytest.fixture(scope="module")
def ran(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, list[CommandResult]]:
    """Copy the example and run its ``run`` block; every command must exit 0."""
    example = copy_example(
        REPOSITORY / "examples" / "01-quickstart",
        tmp_path_factory.mktemp("examples"),
        repository=REPOSITORY,
    )
    return example, run_tagged(example, "run")


def test_ver46_quickstart_runs_and_reproduces(ran: tuple[Path, list[CommandResult]]) -> None:
    """Every command exits 0; the last is ``reproduce``, which exits 0 only if it agreed."""
    example, results = ran
    assert [result.argv[1] for result in results] == ["mesh", "run", "inspect", "reproduce"]
    assert "reproduced" in results[-1].stdout
    assert (example / "run" / "manifest.json").is_file()


def test_ver46_quickstart_current_routes_agree(ran: tuple[Path, list[CommandResult]]) -> None:
    """FR-23's two current routes agree to the tolerance QR-04 gates (NUM-26)."""
    example, _ = ran
    quantities = _read(example / "run" / "run.json")["quantities"]
    assert isinstance(quantities, dict)
    assert quantities["routes_checked"] is True
    agreement = quantities["route_agreement"]
    assert isinstance(agreement, dict)
    assert agreement["relative_difference"] < ROUTE_AGREEMENT_TOLERANCE


def test_ver46_quickstart_records_no_deviation(ran: tuple[Path, list[CommandResult]]) -> None:
    """Every switch at its validated default: the manifest lists no deviation (FR-25)."""
    example, _ = ran
    deviations = _read(example / "run" / "manifest.json")["deviations"]
    assert isinstance(deviations, dict)
    assert deviations["count"] == 0, deviations


def _mesh_hash(run: Path) -> str:
    """Return the deployed mesh's content hash, as the run's manifest records it."""
    group = _read(run / "manifest.json")["geometry_and_mesh"]
    assert isinstance(group, dict)
    return str(group["content_hash"])


def test_ver62_quickstart_holds_the_number_stability_golden(
    ran: tuple[Path, list[CommandResult]], number_stability: NumberStability
) -> None:
    """VER-62: the quick start's numbers hold the golden recorded on v0.4.0's tree (G10)."""
    example, _ = ran
    quantities = _read(example / "run" / "run.json")["quantities"]
    assert isinstance(quantities, dict)
    number_stability("example-01", _mesh_hash(example / "run"), quantities)
