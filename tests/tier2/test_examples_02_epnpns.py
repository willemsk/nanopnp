"""VER-46, VER-62: example 02's ePNP-NS leg, the charged walk of every push."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from nanopnp.core.hashing import decode_floats
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
        REPOSITORY / "examples" / "02-charged-pore",
        tmp_path_factory.mktemp("examples"),
        repository=REPOSITORY,
    )
    return example, run_tagged(example, "run", only=("mesh", "run-epnpns"))


# FR-23
def test_ver46_a_negatively_charged_pore_is_cation_selective(
    ran: tuple[Path, list[CommandResult]],
) -> None:
    example, _ = ran
    quantities = _read(example / "run-epnpns" / "run.json")["quantities"]
    assert isinstance(quantities, dict)
    assert quantities["transport_number"] > 0.5, quantities
    agreement = quantities["route_agreement"]
    assert isinstance(agreement, dict)
    assert agreement["relative_difference"] < ROUTE_AGREEMENT_TOLERANCE


def test_ver46_the_validated_model_lists_no_deviation(
    ran: tuple[Path, list[CommandResult]],
) -> None:
    example, _ = ran
    validated = _read(example / "run-epnpns" / "manifest.json")["deviations"]
    assert isinstance(validated, dict)
    assert validated["count"] == 0, validated


def _mesh_hash(run: Path) -> str:
    group = _read(run / "manifest.json")["geometry_and_mesh"]
    assert isinstance(group, dict)
    return str(group["content_hash"])


def _quantities(run: Path) -> dict[str, object]:
    quantities = _read(run / "run.json")["quantities"]
    assert isinstance(quantities, dict)
    return quantities


def test_ver62_example_02_epnpns_holds_the_number_stability_golden(
    ran: tuple[Path, list[CommandResult]], number_stability: NumberStability
) -> None:
    run = ran[0] / "run-epnpns"
    number_stability("example-02-epnpns", _mesh_hash(run), _quantities(run))


def test_every_figure_draws_and_displays(
    ran: tuple[Path, list[CommandResult]],
    cached_run: Callable[..., RunResult],
    check_figures: Callable[[RunResult], None],
) -> None:
    check_figures(cached_run(ran[0], "epnpns.case.yaml"))
