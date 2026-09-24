"""VER-35 — QR-08 end to end: a run directory back to the same numbers.

Section 3.3 promises that a result's manifest is sufficient to reconstruct the
run that produced it. That promise is only worth as much as the check behind it,
and there is one way to write the check so that it asserts nothing at all:

**The cache must be defeated.** :meth:`~nanopnp.io.store.Store.get_or_compute`
would serve the stored solution artefact, every scalar would agree to the last
bit, and what had been demonstrated is that a dictionary lookup is
deterministic. So the reproduction runs into a store that does not hold the run,
and this file asserts from both sides: that the fresh store *missed*, and that
the solve stage record came back not cached — the same construction VER-26 used
from the other side to prove that a hit does *not* re-enter Newton.

The second failure mode is quieter. A reproduction against an input file whose
contents moved is a different calculation, and nothing about the numbers coming
out of it would say so — so an input that no longer hashes to what the manifest
recorded is fatal, by name. A library version that moved is not that: it is
recorded, and if it moved a number the quantity comparison is what catches it.

One converged solve is shared by the module. Corrections are the validated
ePNP-NS set, and stabilisation is ``none`` (NUM-11) — recorded here because a
number whose mode is unrecorded is not comparable to the reference COMSOL run
(section 6.4).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import pytest

from nanopnp.io.reproduce import (
    DEFAULT_TOLERANCE,
    InputMovedError,
    ReproductionError,
    compare,
    reproduce,
)
from nanopnp.io.run import RUN_RECORD_FILENAME, run_case
from nanopnp.io.store import Store
from nanopnp.mesh.primitives import CylindricalPoreGeometry

logger = logging.getLogger(__name__)

PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
)
MAXH_NM = 4.0
WALL_H_NM = 1.0
CASE = """
schema: nanopnp/case/v2
name: reproduction-probe
inputs:
  mesh:
    path: {mesh_path}
    format: vol
    groups: {{default: interface}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.1
  temperature_K: 298.15
  parameters: willems2020_nacl
boundary_conditions:
  bias_V: 0.02
  ground: cis
physics:
  model: epnp-ns
  solid_permittivities: {{membrane: 3.2}}
numerics:
  continuation: default_ladder
  stabilisation: none
outputs: [current, transport_numbers, eof_rate]
"""


@dataclass
class Archived:
    """One completed run, and the paths a reproduction of it will read."""

    directory: Path
    store: Store
    mesh_path: Path
    case_path: Path


@pytest.fixture(scope="module")
def archived(tmp_path_factory: pytest.TempPathFactory) -> Archived:
    """Run one case end to end and keep its run directory."""
    work = tmp_path_factory.mktemp("reproduce")
    mesh_path = work / "pore.vol"
    PORE.generate(maxh_nm=MAXH_NM, wall_h_nm=WALL_H_NM).ngmesh.Save(str(mesh_path))
    case_path = work / "case.yaml"
    case_path.write_text(CASE.format(mesh_path=mesh_path), encoding="utf-8")

    store = Store(work / "store")
    result = run_case(case_path, store=store, workspace=work / "fields")
    logger.info(
        "archived %s: %d stages, quantities %s, stabilisation %s",
        result.directory,
        len(result.stages),
        sorted(result.quantities),
        result.manifest.groups()["stabilisation"],
    )
    return Archived(
        directory=result.directory, store=store, mesh_path=mesh_path, case_path=case_path
    )


def test_ver35_the_run_directory_carries_what_a_reproduction_needs(archived: Archived) -> None:
    """QR-08's premise: manifest, case and quantities, all written by the run."""
    record = json.loads((archived.directory / RUN_RECORD_FILENAME).read_text(encoding="utf-8"))
    assert [entry["stage"] for entry in record["stages"]][-1] == "report"
    assert set(record["quantities"]) >= {"current_A", "transport_number", "eof_m3_s"}


def test_ver35_a_run_reproduces_into_a_fresh_store(archived: Archived) -> None:
    """Every scalar comes back within the Newton ``rtol``, and Newton was re-entered.

    The measured worst relative difference is logged rather than merely asserted
    against: on a deterministic direct solve in one process it is expected to be
    exactly 0, and a figure that starts drifting is the interesting result even
    while it is inside tolerance.
    """
    found = reproduce(archived.directory)
    solve = next(record for record in found.run.stages if record.name == "solve")
    store = found.run.store

    assert found.reproduced, [drift.summary() for drift in found.drifts]
    assert found.worst is not None
    assert found.worst <= DEFAULT_TOLERANCE
    assert not solve.cached, "the reproduction was served from a store, so it asserted nothing"
    assert store is not None and store.misses > 0
    logger.info(
        "reproduced %d quantities, worst relative difference %.3e, store %d hits / %d misses",
        len(found.quantities),
        found.worst,
        store.hits,
        store.misses,
    )


def test_ver35_reproducing_into_the_store_that_holds_the_run_is_refused(
    archived: Archived,
) -> None:
    """The one way to write this check so that it asserts nothing is refused, by name.

    Not a matter of taste: the solve would be a dictionary lookup, every scalar
    would agree exactly, and the report would say the run reproduced.
    """
    with pytest.raises(ReproductionError) as refused:
        reproduce(archived.directory, store=archived.store)
    assert str(archived.store.root) in str(refused.value)
    assert "re-entered" in str(refused.value)


def test_ver35_an_input_whose_contents_moved_aborts_naming_it(
    archived: Archived, tmp_path: Path
) -> None:
    """A mesh edited under an archived run makes the reproduction a different sum.

    Restored afterwards, because the module shares one run directory and a mesh
    left moved would fail every test after this one for the wrong reason.
    """
    original = archived.mesh_path.read_bytes()
    try:
        archived.mesh_path.write_bytes(original + b"\n# edited\n")
        with pytest.raises(InputMovedError) as moved:
            reproduce(archived.directory)
        assert str(archived.mesh_path) in str(moved.value)
        assert "sha256" in str(moved.value)
    finally:
        archived.mesh_path.write_bytes(original)

    absent = tmp_path / "not-a-run"
    absent.mkdir()
    with pytest.raises(ReproductionError, match="not a run directory"):
        reproduce(absent)


def test_ver35_a_library_difference_is_reported_and_only_fatal_when_asked(
    archived: Archived, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A patch release is recorded, not refused; ``strict_environment`` inverts that.

    A version that moved a number is caught by the quantity comparison, which is
    the assertion that matters. Refusing on the version instead would make the
    check fail for a reason it cannot connect to any number.
    """
    from nanopnp.io import reproduce as module

    # Captured before the patch: ``drifted`` reads through the same name it is
    # about to replace, so reaching for it through the module would recur.
    unpatched = module.environment

    def drifted() -> dict[str, object]:
        found = dict(unpatched())
        packages = dict(found["packages"])  # type: ignore[arg-type]
        packages["numpy"] = "0.0.0-not-a-release"
        found["packages"] = packages
        return found

    monkeypatch.setattr(module, "environment", drifted)

    reported = reproduce(archived.directory)
    assert reported.reproduced
    assert any(item.key == "packages.numpy" for item in reported.environment)

    with pytest.raises(ReproductionError, match="strict_environment"):
        reproduce(archived.directory, strict_environment=True)


def test_ver35_compare_localises_a_drift_to_the_scalar_that_moved() -> None:
    """A nested block reports the ion, not "the block differs" (QR-12).

    A convention is required to be *equal* rather than close: a run whose ``2 pi``
    factor changed does not have numbers that are merely a little different from
    the archived ones, it has numbers that are not the same quantity.
    """
    recorded = {"currents_A": {"Na+": 1.0, "Cl-": 2.0}, "two_pi_included": True}
    reproduced = {"currents_A": {"Na+": 1.0, "Cl-": 2.0 * (1 + 1e-3)}, "two_pi_included": False}

    drifts, worst = compare(recorded, reproduced, tolerance=DEFAULT_TOLERANCE)
    paths = {drift.path for drift in drifts}
    assert paths == {"currents_A.Cl-", "two_pi_included"}
    assert worst == pytest.approx(1e-3, rel=1e-9)
    assert next(d for d in drifts if d.path == "two_pi_included").relative is None

    with pytest.raises(ReproductionError, match="produced no value for"):
        compare(recorded, {"currents_A": {"Na+": 1.0}}, tolerance=DEFAULT_TOLERANCE)
