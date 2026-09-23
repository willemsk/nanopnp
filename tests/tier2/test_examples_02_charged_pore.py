"""VER-46 — example 02, a charged pore under ePNP-NS and classical PNP-NS.

Two oracles that are properties of the model, not transcriptions of a number. A
negative fixed charge enriches cations in the pore, so the cation transport
number exceeds one half under both models; the uncharged pore of example 01 sits
below it, at the bulk ratio of the diffusivities, so this fails on a sign error
anywhere from the field header to the Poisson source. And classical PNP-NS is
every correction set to ``none``, which the manifest must list, each one, as a
deviation from the validated model (PHY-21, PHY-22, FR-25). Stabilisation is
``none`` (NUM-11).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nanopnp.core.hashing import decode_floats
from nanopnp.io.case import CORRECTION_PROPERTIES
from nanopnp.post.qoi import ROUTE_AGREEMENT_TOLERANCE
from nanopnp.validation.examples import CommandResult, copy_example, run_tagged

REPOSITORY = Path(__file__).resolve().parents[2]
RUNS = ("run-epnpns", "run-classical")


def _read(path: Path) -> dict[str, object]:
    """Return a record written through ``canonical``, its floats decoded."""
    decoded = decode_floats(json.loads(path.read_text(encoding="utf-8")))
    assert isinstance(decoded, dict)
    return decoded


@pytest.fixture(scope="module")
def ran(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, list[CommandResult]]:
    """Copy the example and run its ``run`` block; every command must exit 0."""
    example = copy_example(
        REPOSITORY / "examples" / "02-charged-pore",
        tmp_path_factory.mktemp("examples"),
        repository=REPOSITORY,
    )
    return example, run_tagged(example, "run")


@pytest.mark.parametrize("run", RUNS)
def test_ver46_a_negatively_charged_pore_is_cation_selective(
    ran: tuple[Path, list[CommandResult]], run: str
) -> None:
    """``t+ > 1/2`` under both models, with the FR-23 routes in agreement."""
    example, _ = ran
    quantities = _read(example / run / "run.json")["quantities"]
    assert isinstance(quantities, dict)
    assert quantities["transport_number"] > 0.5, quantities
    agreement = quantities["route_agreement"]
    assert isinstance(agreement, dict)
    assert agreement["relative_difference"] < ROUTE_AGREEMENT_TOLERANCE


def test_ver46_classical_pnp_ns_lists_every_none_as_a_deviation(
    ran: tuple[Path, list[CommandResult]],
) -> None:
    """Each correction's ``none`` is named under deviations; the ePNP-NS run names none."""
    example, _ = ran
    classical = _read(example / "run-classical" / "manifest.json")["deviations"]
    assert isinstance(classical, dict)
    listed = {entry["path"]: entry for entry in classical["switches"]}
    expected = {f"electrolyte.corrections.{name}.model" for name in CORRECTION_PROPERTIES}
    expected.add("electrolyte.corrections.steric.model")
    assert set(listed) == expected
    assert all(entry["value"] == "none" for entry in listed.values())
    validated = _read(example / "run-epnpns" / "manifest.json")["deviations"]
    assert isinstance(validated, dict)
    assert validated["count"] == 0, validated
