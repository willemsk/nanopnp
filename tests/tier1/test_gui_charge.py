"""VER-60: the charge tab's view-models, on a tube that deposits two atoms."""

from __future__ import annotations

import pytest

from nanopnp import Case, Session
from nanopnp.charge.stage import stored_lattice
from nanopnp.gui.charge import (
    charge_image,
    load_protonation,
)
from nanopnp.gui.solver import Produced
from nanopnp.io.store import Store
from nanopnp.pipeline.run import RunResult


def _produced(result: RunResult, store: Store, name: str) -> Produced:
    record = next(record for record in result.stages if record.name == name)
    return Produced(
        name=name,
        schema=record.schema,
        hash=record.hash,
        cached=record.cached,
        store=str(store.root),
    )


@pytest.fixture(scope="module")
def tube(charged_tube, tmp_path_factory: pytest.TempPathFactory):
    work = tmp_path_factory.mktemp("tube")
    store = Store(work / "store")
    case = charged_tube.write(work / "case")
    return case, store, Session(store, write=False).run(Case.load(case), upto="charge")


@pytest.fixture(scope="module")
def two_frames(charged_tube, tmp_path_factory: pytest.TempPathFactory):
    work = tmp_path_factory.mktemp("frames")
    store = Store(work / "store")
    case = charged_tube.write(work / "case", frames=2)
    return case, store, Session(store, write=False).run(Case.load(case), upto="charge")


def _record(result: RunResult) -> dict[str, object]:
    record = result.artefacts["charge"].summary["charge"]
    assert isinstance(record, dict)
    return record


@pytest.mark.parametrize("block", [1, 7])
def test_ver60_the_picture_carries_the_record_s_charge(tube, block: int) -> None:
    _, _, result = tube
    lattice = stored_lattice(result.artefacts["charge"])
    assert lattice is not None
    rows, columns = lattice.grid.values.shape
    if block == 7:
        assert rows % 7 and columns % 7
    picture = charge_image(lattice, block=block)
    recorded = _record(result)["conservation"]["q_grid_e"]  # type: ignore[index]
    assert picture.integral_e == pytest.approx(recorded, rel=1e-12)
    weights_z, weights_r = lattice.weights_m()
    assert picture.areas.sum() == pytest.approx(weights_z.sum() * weights_r.sum(), rel=1e-12)
    assert picture.quantity == "areal_charge_density"
    assert picture.units == "C/m^2"


def test_ver60_the_frame_selector_switches_the_charges_and_q_net(two_frames, charged_tube) -> None:
    _, store, result = two_frames
    view = load_protonation(_produced(result, store, "protonation"))
    assert view.frames == 2
    first = tuple(atom[4] for atom in charged_tube.atoms)
    second = charged_tube.second_frame_e
    assert view.q_net_e == (pytest.approx(sum(first)), pytest.approx(sum(second)))
    assert view.frame(0).q_net_e == pytest.approx(sum(first))
    assert view.frame(1).q_net_e == pytest.approx(sum(second))
    assert [row.applied_e for row in view.frame(0).rows] == [pytest.approx(sum(first))]
    assert [row.applied_e for row in view.frame(1).rows] == [pytest.approx(sum(second))]
    assert view.frame(0).rows[0].residue == "GLU 18"
    assert not view.titrated
    assert view.pka_status.startswith("not run")
    assert all(row.pka is None for row in view.frame(0).rows)
    with pytest.raises(IndexError, match="frame 2 is not in a table of 2 frames"):
        view.frame(2)
