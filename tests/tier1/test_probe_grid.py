"""The Tier-3 comparison surface: its refusals, and its domain mask (VAL-01, QR-12).

The two properties this file exists for are the two that fail silently.

A **square patch** makes a transposed ``%Data`` read plausible: the shape check
in :meth:`~nanopnp.density.grid.RadialGrid.from_axes` passes, and the field is
wrong everywhere except on the diagonal ``r = z``, where it is exactly right.
Requiring ``n_r != n_z`` turns that case into a shape error at ingest.

The **margin** is what makes the mask a statement about the geometry rather than
about which element the mesh's point search happened to land in. Without it a
residual disagreement against the golden's ``NaN`` set is a coin flip; with it,
it is a real difference between our reference geometry and the one the export was
made from.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from nanopnp.io.case import CaseValidationError
from nanopnp.mesh.primitives import ELECTROLYTE_DOMAINS
from nanopnp.validation.probe import (
    PROBE_SCHEMA,
    ProbeDocument,
    ProbeGrid,
    ProbeGridError,
    ProbePatch,
    load_probe,
    loads_probe,
)

REFERENCE_PROBE = Path("docs/validation/probes/clya-reference.probe.yaml")
"""The checked-in grid for the section 5.2.1 geometry, resolved from the repo root."""


def _document(**patch: object) -> str:
    """Return a one-patch probe document with the given patch fields."""
    fields = {"name": "block", "r_nm": [0.0, 1.0], "z_nm": [0.0, 2.0], "n_r": 5, "n_z": 9}
    fields.update(patch)
    lines = "\n".join(f"    {key}: {value}" for key, value in fields.items())
    return f"schema: {PROBE_SCHEMA}\nname: probe\npatches:\n  -{lines[3:]}\n"


@pytest.fixture(scope="module")
def reference_mesh():
    """Return the WP8 reference mesh, once for this module.

    Module-scoped because generating it costs about seven seconds and every mask
    assertion below is about the same geometry.
    """
    from nanopnp.mesh.reference import ReferenceGeometry

    return ReferenceGeometry.from_fixture().generate(check_quality=False)


@pytest.fixture(scope="module")
def reference_document() -> ProbeDocument:
    """Return the checked-in probe document for the reference geometry."""
    return load_probe(REFERENCE_PROBE)


@pytest.fixture(scope="module")
def reference_grid(reference_document: ProbeDocument, reference_mesh) -> ProbeGrid:
    """Return the reference probe grid bound to the reference mesh, with two masks.

    ``potential`` is solved over the whole of Omega and ``c`` over the
    electrolyte alone, which is the pair PHY-03 declares and the pair whose
    difference the margin rule is about.
    """
    return ProbeGrid.on_mesh(
        reference_document, reference_mesh, {"potential": None, "c": ELECTROLYTE_DOMAINS}
    )


# -- the transpose refusal ----------------------------------------------------


def test_val01_probe_patch_refuses_square_grid() -> None:
    """A square patch is refused, naming the ``%Data`` row order.

    Structural, so exact. The message has to say *why*, because the next author
    adding a patch will otherwise pick equal sample counts for tidiness and
    reopen the hole.
    """
    with pytest.raises(CaseValidationError) as raised:
        loads_probe(_document(n_r=9, n_z=9))
    message = str(raised.value)
    assert "square" in message
    assert "%Data" in message
    assert "one row per z sample" in message
    assert "r = z" in message


def test_val01_probe_patch_accepts_a_rectangular_grid() -> None:
    """The refusal is about squareness alone: one sample fewer and it passes."""
    document = loads_probe(_document(n_r=9, n_z=10))
    assert document.patches[0].count == 90


@pytest.mark.parametrize(
    ("patch", "expected"),
    [
        ({"n_r": 1}, "at least two samples"),
        ({"r_nm": [1.0, 1.0]}, "must be distinct"),
        ({"r_nm": [1.0, 0.0]}, "must be distinct"),
    ],
)
def test_val01_probe_patch_refuses_a_degenerate_axis(patch: dict, expected: str) -> None:
    """An axis with no extent or no spacing is refused before anything samples it."""
    with pytest.raises(CaseValidationError, match=expected):
        loads_probe(_document(**patch))


def test_val01_probe_document_refuses_two_patches_sharing_a_point() -> None:
    """A shared point would enter the weighted norm twice at a weight no patch declares."""
    text = (
        f"schema: {PROBE_SCHEMA}\nname: probe\npatches:\n"
        "  - {name: a, r_nm: [0.0, 1.0], z_nm: [0.0, 2.0], n_r: 3, n_z: 5}\n"
        "  - {name: b, r_nm: [0.0, 1.0], z_nm: [0.0, 4.0], n_r: 3, n_z: 9}\n"
    )
    with pytest.raises(CaseValidationError, match="twice"):
        loads_probe(text)


# -- the document is the interface --------------------------------------------


def test_val01_probe_hash_is_stable_and_moves_with_any_extent(
    reference_document: ProbeDocument,
) -> None:
    """The hash is what a golden manifest declares, so it must move with the points.

    Re-reading the same file gives the same digest, and widening one patch by
    0.001 nm gives a different one: an edited probe grid silently moves the
    sample points, and the hash is the only thing that notices.
    """
    again = load_probe(REFERENCE_PROBE)
    assert again.hash == reference_document.hash

    moved = reference_document.model_copy(deep=True)
    patch = moved.patches[0]
    moved.patches[0] = ProbePatch(
        name=patch.name,
        r_nm=(patch.r_nm[0], patch.r_nm[1] + 0.001),
        z_nm=patch.z_nm,
        n_r=patch.n_r,
        n_z=patch.n_z,
    )
    assert moved.hash != reference_document.hash


def test_val01_probe_points_flatten_in_data_row_order(
    reference_document: ProbeDocument,
) -> None:
    """The flattening is ``[i_z, i_r]``, which is what makes a ``%Data`` read a ravel.

    Checked against the axes rather than against the implementation: the first
    ``n_r`` points share a ``z`` and walk ``r``, which is one row of a COMSOL
    table.
    """
    patch = reference_document.patches[0]
    points = patch.points_nm()
    r_axis, z_axis = patch.axes_nm()
    assert points.shape == (patch.count, 2)
    assert points[: patch.n_r, 1] == pytest.approx(z_axis[0])
    assert points[: patch.n_r, 0] == pytest.approx(r_axis)
    assert points[patch.n_r, 1] == pytest.approx(z_axis[1])


def test_val01_probe_axes_are_written_in_metres(reference_document: ProbeDocument) -> None:
    """``write_comsol_axes`` emits what the author pastes, in a ``%Grid``'s own unit.

    A hand-entered axis is a silently moved sample point that the ``probe_hash``
    cannot catch — the document did not change — so the axes are emitted rather
    than described.
    """
    text = reference_document.write_comsol_axes()
    assert reference_document.hash in text
    patch = reference_document.patches[0]
    assert f"patch {patch.name!r}" in text
    r_axis, _ = patch.axes_nm()
    block = text.split(f"n_r = {patch.n_r}")[1].splitlines()
    written = [float(value) for value in block[1].split()]
    assert len(written) == patch.n_r
    assert written[0] == pytest.approx(r_axis[0] * 1e-9, abs=1e-24)
    assert written[-1] == pytest.approx(r_axis[-1] * 1e-9, abs=1e-24)


# -- the domain mask ----------------------------------------------------------


def test_val01_probe_mask_excludes_points_within_margin(
    reference_grid: ProbeGrid, reference_document: ProbeDocument, reference_mesh
) -> None:
    """No retained ``c_i`` point is within ``margin_nm`` of a non-electrolyte material.

    Three assertions, and the third is the one that is not a restatement of the
    implementation.

    The mask does something: fewer ``c`` points are kept than ``potential``
    points, and the margin rule itself drops a positive number beyond the bare
    point test — the count the document records.

    Two points with unambiguous answers land the right way: ``(4.05, 6.0)`` nm is
    inside the pore protein (the wall crossings at ``z = 6.2`` are 3.13 and 4.88
    nm) and ``(0.05, 30.0)`` nm is 30 nm up the axis in open reservoir.

    And every retained point survives a probe the implementation did not make:
    four **diagonal** offsets at ``margin/2``, whose normal component against any
    boundary is at most ``margin/2`` and so is implied by the axis-aligned test
    the mask actually applies. A mask built on the wrong materials, or not
    applied at all, fails it.
    """
    import numpy as np

    margin = reference_document.margin_nm
    kept = reference_grid.masks["c"]
    assert kept.sum() < reference_grid.masks["potential"].sum()
    assert reference_grid.dropped["c"] > 0

    points = reference_grid.points_nm
    for target, expected in (((4.05, 6.0), False), ((0.05, 30.0), True)):
        index = int(np.argmin(np.linalg.norm(points - np.asarray(target), axis=1)))
        assert points[index] == pytest.approx(np.asarray(target))
        assert bool(kept[index]) is expected

    indicator = reference_mesh.MaterialCF({"electrolyte": 1.0}, default=0.0)
    retained = points[kept]
    step = margin / 2.0
    for offset in ((step, step), (step, -step), (-step, step), (-step, -step)):
        probed = retained + np.asarray(offset)
        probed[:, 0] = np.abs(probed[:, 0])
        sampled = np.asarray(indicator(reference_mesh(probed[:, 0], probed[:, 1])))
        outside = np.flatnonzero(sampled.reshape(-1) <= 0.5)
        assert outside.size == 0, (
            f"offset {offset} nm leaves {outside.size} retained point(s) outside the "
            f"electrolyte, the first at {retained[outside[0]]} nm"
        )


def test_val01_probe_mask_keeps_the_near_axis_line(reference_grid: ProbeGrid) -> None:
    """The axis is mirrored, not clipped, so ``r = 0`` survives the margin rule.

    Clipping would drop the near-axis line entirely — every point on it has an
    ``r - margin`` neighbour outside the half-plane — and the near-axis line is
    the one patch ``rel_l2`` exists to see (WP13 Design section 2).
    """
    import numpy as np

    names = np.asarray(reference_grid.document.patch_of_point())
    on_axis = names == "axis_line"
    assert on_axis.any()
    assert reference_grid.masks["c"][on_axis].all()
    assert (reference_grid.points_nm[on_axis, 0] == 0.0).any()


def test_val01_probe_mask_refuses_a_patch_outside_the_mesh(reference_mesh) -> None:
    """A patch grown by the margin must lie in the mesh; outside has no material.

    Refused rather than masked out: every point of such a patch would come back
    "not in this field's materials", which reads as "the field is nowhere" rather
    than as "this grid is in the wrong place" (QR-12).
    """
    document = loads_probe(_document(r_nm=[0.0, 1.0], z_nm=[400.0, 402.0]))
    with pytest.raises(ProbeGridError, match="mask margin"):
        ProbeGrid.on_mesh(document, reference_mesh, {"potential": None})


def test_val01_probe_mask_refuses_materials_no_mesh_carries(reference_mesh) -> None:
    """A regular expression matching nothing is a misconfiguration, not an empty field."""
    document = loads_probe(_document())
    with pytest.raises(ProbeGridError, match="matches none"):
        ProbeGrid.on_mesh(document, reference_mesh, {"c": "cytoplasm"})


def test_val01_probe_weights_are_each_patch_own_spacing(
    reference_grid: ProbeGrid, reference_document: ProbeDocument
) -> None:
    """Each point's norm weight is ``dr dz`` of its own patch, not a global one.

    That is what lets a 0.005 nm near-axis line and a 2 nm reservoir block enter
    one norm without the fine patch dominating it by sample count alone.
    """
    import numpy as np

    names = np.asarray(reference_document.patch_of_point())
    weights = reference_grid.weights_nm2
    for patch in reference_document.patches:
        selected = weights[names == patch.name]
        dr, dz = patch.spacing_nm
        assert selected == pytest.approx(dr * dz)
        assert math.isclose(dr * dz, patch.weight_nm2)
