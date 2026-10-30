"""VER-46, VER-62: example 02's classical leg, nightly."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from nanopnp.cli import main
from nanopnp.core.hashing import decode_floats
from nanopnp.io.case import CORRECTION_PROPERTIES
from nanopnp.post.qoi import ROUTE_AGREEMENT_TOLERANCE
from nanopnp.validation.examples import CommandResult, copy_example, run_tagged

if TYPE_CHECKING:
    from conftest import NumberStability

pytestmark = pytest.mark.nightly

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
    return example, run_tagged(example, "run")


# FR-23
def test_ver46_classical_pnp_ns_is_cation_selective(
    ran: tuple[Path, list[CommandResult]],
) -> None:
    example, _ = ran
    quantities = _read(example / "run-classical" / "run.json")["quantities"]
    assert isinstance(quantities, dict)
    assert quantities["transport_number"] > 0.5, quantities
    agreement = quantities["route_agreement"]
    assert isinstance(agreement, dict)
    assert agreement["relative_difference"] < ROUTE_AGREEMENT_TOLERANCE


def test_ver46_classical_pnp_ns_lists_every_none_as_a_deviation(
    ran: tuple[Path, list[CommandResult]],
) -> None:
    example, _ = ran
    classical = _read(example / "run-classical" / "manifest.json")["deviations"]
    assert isinstance(classical, dict)
    listed = {entry["path"]: entry for entry in classical["switches"]}
    expected = {f"electrolyte.corrections.{name}.model" for name in CORRECTION_PROPERTIES}
    expected.add("electrolyte.corrections.steric.model")
    assert set(listed) == expected
    assert all(entry["value"] == "none" for entry in listed.values())


def test_fr25_inspect_reads_back_every_deviation_and_compares_the_runs(
    ran: tuple[Path, list[CommandResult]], capsys: pytest.CaptureFixture[str]
) -> None:
    example, results = ran
    run = example / "run-classical"
    manifest = _read(run / "manifest.json")
    block = manifest["deviations"]
    assert isinstance(block, dict)
    paths = sorted(str(entry["path"]) for entry in block["switches"])
    assert paths, "the classical run must deviate, or this reads back nothing"

    reading = next(result for result in results if result.argv[1] == "inspect").stdout
    lines = [line.split() for line in reading.splitlines() if line.startswith("deviation ")]
    assert sorted(words[1].rstrip(":") for words in lines) == paths

    assert main(["inspect", str(run), "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == manifest

    assert main(["inspect", str(example / "run-epnpns"), str(run), "--json"]) == 0
    compared = json.loads(capsys.readouterr().out)
    corrections = {f"electrolyte.corrections.{name}.model" for name in CORRECTION_PROPERTIES}
    corrections.add("electrolyte.corrections.steric.model")
    assert {entry["path"] for entry in compared["case"]} - {"name"} == corrections
    assert compared["deviations"]["left"] == []
    assert sorted(entry["path"] for entry in compared["deviations"]["right"]) == sorted(corrections)
    assert {entry["name"] for entry in compared["quantities"]} >= {"current_A", "transport_number"}


def _mesh_hash(run: Path) -> str:
    group = _read(run / "manifest.json")["geometry_and_mesh"]
    assert isinstance(group, dict)
    return str(group["content_hash"])


def _quantities(run: Path) -> dict[str, object]:
    quantities = _read(run / "run.json")["quantities"]
    assert isinstance(quantities, dict)
    return quantities


# One test per case, not one for both: on a key with no entry the first assertion
# fails, and the second case's entry would not be printed until another CI run.
def test_ver62_example_02_classical_holds_the_number_stability_golden(
    ran: tuple[Path, list[CommandResult]], number_stability: NumberStability
) -> None:
    run = ran[0] / "run-classical"
    number_stability("example-02-classical", _mesh_hash(run), _quantities(run))
