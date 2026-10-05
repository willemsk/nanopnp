"""VER-46 — example 03, a bias sweep over a charged pore and its uncharged control.

The oracle is a symmetry, not a number. Reversing the bias maps a z-symmetric,
uncharged pore onto its own mirror image — the governing equations see only
potential differences, so the reversed problem is the mirrored one shifted by a
constant — and its current therefore reverses exactly: ``RR = 1``. The discrete
departure is bounded by the mesh's own asymmetry and the Newton residual, and it
is held to the NUM-26 route tolerance, as ``test_current_routes`` holds the same
property of the same pore family. The charged pore's rows must all be present and
every member must exit 0 (FR-24, IF-02). The collector's rectification is read
from ``dataset.json``, the dataset artefact, rather than recomputed here.
Stabilisation is ``none`` (NUM-11).
"""

from __future__ import annotations

import csv
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


def _dataset(directory: Path) -> dict[str, object]:
    """Return a sweep's ``dataset.json``, its floats decoded."""
    decoded = decode_floats(json.loads((directory / "dataset.json").read_text(encoding="utf-8")))
    assert isinstance(decoded, dict)
    return decoded


@pytest.fixture(scope="module")
def ran(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, list[CommandResult]]:
    """Copy the example and run its ``run`` block; every command must exit 0."""
    example = copy_example(
        REPOSITORY / "examples" / "03-iv-sweep",
        tmp_path_factory.mktemp("examples"),
        repository=REPOSITORY,
    )
    return example, run_tagged(example, "run")


def test_ver46_an_uncharged_symmetric_pore_rectifies_to_unity(
    ran: tuple[Path, list[CommandResult]],
) -> None:
    """``|RR - 1|`` of the control is below the route tolerance (FR-23, RSK-03)."""
    example, _ = ran
    pairs = _dataset(example / "iv-uncharged")["rectification"]
    assert isinstance(pairs, list) and len(pairs) == 1
    ratio = pairs[0]["rectification"]
    assert abs(ratio - 1.0) < ROUTE_AGREEMENT_TOLERANCE, pairs


@pytest.mark.parametrize(("sweep", "points"), [("iv-charged", 4), ("iv-uncharged", 2)])
def test_ver46_every_member_exits_zero_and_every_row_has_a_current(
    ran: tuple[Path, list[CommandResult]], sweep: str, points: int
) -> None:
    """The CSV export is complete: every point a row, every row ``ok`` with a current."""
    example, _ = ran
    with (example / sweep / "dataset.csv").open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(line for line in stream if not line.startswith("#")))
    assert len(rows) == points
    assert all(row["status"] == "ok" and row["exit_class"] == "0" for row in rows), rows
    assert all(row["current_A"] for row in rows)


def test_ver46_the_charged_pore_has_a_ratio_at_each_bias_magnitude(
    ran: tuple[Path, list[CommandResult]],
) -> None:
    """Both exactly-opposite pairs produced a ratio, and ``plot_iv.py`` tabulated all rows."""
    example, _ = ran
    pairs = _dataset(example / "iv-charged")["rectification"]
    assert isinstance(pairs, list)
    assert sorted(pair["bias_V"] for pair in pairs) == [0.05, 0.1]
    with (example / "iv.csv").open(encoding="utf-8") as stream:
        assert len(list(csv.DictReader(stream))) == 6


def test_ver62_charged_sweep_holds_the_number_stability_golden(
    ran: tuple[Path, list[CommandResult]], number_stability: NumberStability
) -> None:
    """VER-62: every member of the charged sweep holds the golden of v0.4.0's tree (G10).

    One entry for the sweep, each value named by its member's index, so the sweep
    runner's warm starts are part of what the golden pins.
    """
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
