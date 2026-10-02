"""VER-60 — the charge tab's view-models, on a tube that deposits two atoms in a second or two.

The picture is the place a charge can look right and be wrong in sign, in frame
or in integral (RSK-15), so each of the three is asserted against an oracle the
view did not compute: the atoms' own model-frame (r, z) and signs, the record's
``q_grid_e``, and the record's tolerances. The tube is ``tests/conftest.py``'s
``charged_tube``: the parallelogram through ``inputs.profile``, an ``inputs.pqr``
of a +1 e and a -2 e atom inside the body, walked through stage 7 at
``size_scale`` 5.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from nanopnp.charge.fields import ConservationReport
from nanopnp.charge.stage import stored_lattice
from nanopnp.core.constants import ELEMENTARY_CHARGE
from nanopnp.density.grid import RingMaximum
from nanopnp.gui.charge import (
    MAX_PIXELS,
    ConservationView,
    block_size,
    build_offer,
    charge_image,
    charge_stages,
    load_charge,
    load_protonation,
)
from nanopnp.gui.geometry import MODEL_FRAME, lookup_table
from nanopnp.gui.solver import Produced
from nanopnp.io.case import load_case
from nanopnp.io.run import RunResult, run_case
from nanopnp.io.store import Store


def _produced(result: RunResult, store: Store, name: str) -> Produced:
    """Return the event the hook would have posted for one stage of a finished walk."""
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
    """Walk the one-frame tube through stage 7 once, into a store kept for the module."""
    work = tmp_path_factory.mktemp("tube")
    store = Store(work / "store")
    case = charged_tube.write(work / "case")
    return case, store, run_case(case, store=store, upto="charge", write=False)


@pytest.fixture(scope="module")
def two_frames(charged_tube, tmp_path_factory: pytest.TempPathFactory):
    """Walk the two-frame tube through stage 7 once."""
    work = tmp_path_factory.mktemp("frames")
    store = Store(work / "store")
    case = charged_tube.write(work / "case", frames=2)
    return case, store, run_case(case, store=store, upto="charge", write=False)


def _record(result: RunResult) -> dict[str, object]:
    """Return stage 7's charge record."""
    record = result.artefacts["charge"].summary["charge"]
    assert isinstance(record, dict)
    return record


def _model_frame(atom: tuple[str, float, float, float, float]) -> tuple[float, float]:
    """Return an atom's (r, z) in nm; the tube's ``centre_z_nm`` is 0, so stage 1's frame is it."""
    _, x, y, z, _ = atom
    return math.hypot(x, y) / 10.0, z / 10.0


# -- building --------------------------------------------------------------------


def test_ver60_build_charge_is_offered_with_the_stages_the_walk_runs(tube) -> None:
    """A depositing case walks both halves of stage 7; a case walking none is refused (D2)."""
    case, _, _ = tube
    document = load_case(case)
    assert build_offer(document).offered
    assert charge_stages(document).planned == ("protonation", "charge")
    uncharged = document.model_copy(
        update={"inputs": document.inputs.model_copy(update={"pqr": None})}
    )
    offer = build_offer(uncharged)
    assert not offer.offered
    assert "supplies neither inputs.charge nor inputs.eps_r" in offer.reason


# -- the charge map --------------------------------------------------------------


def test_ver60_each_atom_lands_in_its_own_pixel_with_its_sign(tube, charged_tube) -> None:
    """The positive atom's pixel holds the maximum and the negative atom's the minimum (D4, D5).

    The pixel is the one whose centre is nearest the atom's model-frame (r, z); the
    top row is the largest z and r increases to the right. A picture that dropped
    ``y``, swapped the axes, flipped z or negated the charge fails one of the four.
    """
    _, store, result = tube
    view = load_charge(_produced(result, store, "charge"), block=1)
    assert view.charge is not None
    image = view.charge.image
    assert view.frame == image.frame == MODEL_FRAME
    shown = image.display()
    for atom in charged_tube.atoms:
        r_nm, z_nm = _model_frame(atom)
        column, row = image.pixel_of(r_nm, z_nm)
        centre = image.pixel_centre(column, row)
        assert abs(centre[0] - r_nm) <= 0.5 * image.spacing_nm[0] + 1e-12
        assert abs(centre[1] - z_nm) <= 0.5 * image.spacing_nm[1] + 1e-12
        extremum = np.nanmax(shown) if atom[4] > 0 else np.nanmin(shown)
        assert shown[row, column] == extremum, atom
    assert image.pixel_centre(0, 0)[1] == float(image.z_nm[-1])
    assert image.pixel_centre(1, 0)[0] > image.pixel_centre(0, 0)[0]


@pytest.mark.parametrize("block", [1, 7])
def test_ver60_the_picture_carries_the_record_s_charge(tube, block: int) -> None:
    """``sum_p mean_p A_p`` is the record's ``q_grid_e`` to 1e-12 relative (D6, Design section 1).

    At ``k`` = 7 the 781 x 1041 lattice leaves a partial last block on both axes,
    so a reduction that dropped or double-counted the remainder fails here.
    """
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


def test_ver60_the_default_block_leaves_at_most_the_pixel_limit(tube) -> None:
    """``k`` is the smallest that leaves at most :data:`MAX_PIXELS` pixels along either axis."""
    _, _, result = tube
    lattice = stored_lattice(result.artefacts["charge"])
    assert lattice is not None
    shape = lattice.grid.values.shape
    picture = charge_image(lattice)
    k = picture.block
    assert k == block_size(shape)
    assert max(picture.image.values.shape) <= MAX_PIXELS
    assert k == 1 or max(math.ceil(n / (k - 1)) for n in shape) > MAX_PIXELS
    assert block_size((2048, 10)) == 2
    assert block_size((2049, 10)) == 3


def test_ver60_zero_is_the_centre_of_the_diverging_table(tube) -> None:
    """Zero maps to the neutral middle entry, and the limit is the largest magnitude drawn (D8)."""
    _, _, result = tube
    lattice = stored_lattice(result.artefacts["charge"])
    assert lattice is not None
    picture = charge_image(lattice, block=3)
    image = picture.image
    table = lookup_table("diverging")
    centre = len(table) // 2
    assert len(table) % 2 == 1
    assert int(image.colour_index(0.0)) == centre
    assert tuple(table[centre][:3]) == (221, 221, 221)
    assert picture.limit == float(np.nanmax(np.abs(image.values)))
    assert image.scale == (-picture.limit, picture.limit)
    assert int(image.colour_index(picture.limit)) == len(table) - 1
    assert int(image.colour_index(-picture.limit)) == 0
    assert f"±{picture.limit:.3g}" in image.title


def test_ver60_the_recorded_worst_planes_are_marked_at_their_z(tube) -> None:
    """Each marker row contains the z its record names, never a recomputed one (D9)."""
    _, store, result = tube
    plane = _record(result)["conservation"]["per_plane"]  # type: ignore[index]
    view = load_charge(_produced(result, store, "charge"))
    assert view.charge is not None
    # A deposit and a sharp dielectric: the deployed pane offers the charge alone.
    assert view.quantities == ("charge",)
    picture = view.charge
    assert dict(picture.planes) == {
        "worst plane (lattice)": plane["grid_worst_plane_z_nm"],
        "worst plane (mesh)": plane["mesh_worst_plane_z_nm"],
    }
    for _, z_nm in picture.planes:
        row = picture.plane_row(z_nm)
        _, centre = picture.image.pixel_centre(0, row)
        assert abs(centre - z_nm) <= 0.5 * picture.image.spacing_nm[1] + 1e-12


# -- the conservation report -----------------------------------------------------


def test_ver60_every_number_of_the_conservation_view_is_the_record_s(tube) -> None:
    """Each leg's value and tolerance, and each figure, equal the record's (D10)."""
    _, store, result = tube
    record = _record(result)
    report = record["conservation"]
    view = load_charge(_produced(result, store, "charge")).conservation
    assert view is not None
    assert view.source == "deposited"
    legs = {leg.name: leg for leg in view.legs}
    for name, key in (
        ("producer", "producer"),
        ("consumer", "consumer"),
        ("quadrature agreement", "quadrature_agreement"),
    ):
        assert legs[name].value == report[key]["relative_error"]  # type: ignore[index]
        assert legs[name].tolerance == report[key]["tolerance"]  # type: ignore[index]
        assert legs[name].ratio == pytest.approx(
            abs(report[key]["relative_error"]) / report[key]["tolerance"]  # type: ignore[index]
        )
    plane = report["per_plane"]  # type: ignore[index]
    assert legs["worst plane (lattice)"].value == plane["grid_worst_relative_error"]
    assert legs["worst plane (mesh)"].value == plane["mesh_worst_relative_error"]
    assert legs["worst plane (mesh)"].tolerance == plane["tolerance"]
    for key in ("q_net_e", "q_grid_e", "q_mesh_e", "axis_guard_deficit_e", "boundary_ring"):
        assert view.figures[key] == report[key]  # type: ignore[index]
    assert view.figures["material_charge_e"] == record["material_charge_e"]
    assert view.figures["solid_share"] == record["solid_share"]


def test_ver60_a_doubled_tolerance_is_shown_doubled(tube) -> None:
    """The tolerance comes from the record, never from ``CONSERVATION_TOL`` in ``gui/`` (D10)."""
    _, _, result = tube
    record = _record(result)
    report = dict(record["conservation"])  # type: ignore[call-overload]
    report["consumer"] = {
        **report["consumer"],
        "tolerance": 2.0 * report["consumer"]["tolerance"],
    }
    view = ConservationView.from_record({**record, "conservation": report})
    consumer = next(leg for leg in view.legs if leg.name == "consumer")
    assert consumer.tolerance == report["consumer"]["tolerance"]
    assert consumer.ratio == pytest.approx(
        abs(report["consumer"]["relative_error"]) / report["consumer"]["tolerance"]
    )


def test_ver60_a_leg_not_run_is_shown_as_not_run_with_its_reason() -> None:
    """A supplied field declaring no ``q_net_e`` has no producer leg, and is never shown as 0."""
    e = ELEMENTARY_CHARGE
    report = ConservationReport(
        q_net_C=None,
        q_grid_C=-12.0 * e,
        q_mesh_C=-12.000001 * e,
        q_mesh_refined_C=-12.000001 * e,
        guard_deficit_C=0.0,
        ring=RingMaximum(value=1e-9, r_nm=5.0, z_nm=9.0),
        interior_maximum=1.0,
        planes_nm=(1.0, 2.0),
        grid_cumulative_C=(-1.0 * e, -6.0 * e),
        mesh_cumulative_C=(-1.0 * e, -6.000001 * e),
        ramp_nm=0.2,
    )
    record = {"quantity": "areal_charge_density", "conservation": report.summary()}
    view = ConservationView.from_record(record)
    assert view.source == "supplied"
    producer = next(leg for leg in view.legs if leg.name == "producer")
    assert not producer.run
    assert producer.value is None
    assert producer.ratio is None
    assert producer.reason == "the field document declares no q_net_e"
    assert view.figures["q_net_e"] is None
    mesh = next(leg for leg in view.legs if leg.name == "worst plane (mesh)")
    assert mesh.value == report.worst_plane[1]
    assert view.planes == (("worst plane (mesh)", report.worst_plane[0]),)


# -- the protonation table -------------------------------------------------------


def test_ver60_the_frame_selector_switches_the_charges_and_q_net(two_frames, charged_tube) -> None:
    """Two ``MODEL`` frames that differ give two tables of rows and two ``Q_net`` (D11)."""
    _, store, result = two_frames
    view = load_protonation(_produced(result, store, "protonation"))
    assert view.frames == 2
    first = tuple(atom[4] for atom in charged_tube.atoms)
    second = charged_tube.second_frame_e
    assert view.q_net_e == (pytest.approx(sum(first)), pytest.approx(sum(second)))
    assert view.frame(0).q_net_e == pytest.approx(sum(first))
    assert view.frame(1).q_net_e == pytest.approx(sum(second))
    # One residue carrying both atoms: its applied charge is each frame's sum.
    assert [row.applied_e for row in view.frame(0).rows] == [pytest.approx(sum(first))]
    assert [row.applied_e for row in view.frame(1).rows] == [pytest.approx(sum(second))]
    assert view.frame(0).rows[0].residue == "GLU 18"
    assert not view.titrated
    assert view.pka_status.startswith("not run")
    assert all(row.pka is None for row in view.frame(0).rows)
    with pytest.raises(IndexError, match="frame 2 is not in a table of 2 frames"):
        view.frame(2)


def test_ver60_a_table_and_record_that_disagree_are_refused(two_frames) -> None:
    """The unapplied states are read from the table and checked against the record (D11)."""
    _, store, result = two_frames
    view = load_protonation(_produced(result, store, "protonation"))
    forged = {**view.summary, "unapplied": [{"chain": "A", "residue": "GLU 18"}]}
    with pytest.raises(ValueError, match="unapplied states are not the ones its record lists"):
        type(view).build(view.table, forged)


# -- the shell ---------------------------------------------------------------------


def test_ver60_a_generated_shell_s_mesh_lists_exclusion(charged_tube, tmp_path: Path) -> None:
    """The Mesh view colours by material, so the ``exclusion`` shell is listed as one (D17)."""
    from nanopnp.gui.render import MeshRequest, render_mesh

    case = charged_tube.write(tmp_path / "case")
    text = case.read_text(encoding="utf-8")
    case.write_text(text + "charge: {exclusion_offset_nm: 0.25}\n", encoding="utf-8")
    run = run_case(case, store=Store(tmp_path / "store"), upto="mesh").directory
    drawn = render_mesh(MeshRequest(run=str(run)))
    assert "exclusion" in drawn.materials
