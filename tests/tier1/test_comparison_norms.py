"""The three norms, the gauge-free pressure and the mask gate (VAL-01, NUM-06, QR-12).

Two norms are reported because one of them cannot see the axis, and the second
test here is the demonstration. The ``r`` weight of the axisymmetric norm is
0.005 nm on the near-axis line of the reference probe grid and 60 nm at the far
edge of the reservoir patch, so a perturbation confined to the axis contributes
of order 1e-7 of the norm's denominator while occupying a quarter of its points.
The axis is where the ``1/r`` forms of section 6.2 and the NUM-06 natural
condition are fragile, so a comparison reporting ``rel_L2_r`` alone would be
least sensitive exactly where this implementation is most likely to be wrong.

No mesh is built here. The masks are handed to :class:`ProbeGrid` directly, so
what is under test is the arithmetic and not the geometry — which is the point of
an analytic test.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from nanopnp.validation.compare import PRESSURE_FIELD, check_mask_agreement, field_error
from nanopnp.validation.probe import (
    PROBE_SCHEMA,
    ProbeDocument,
    ProbeGrid,
    ProbeGridError,
    load_probe,
    loads_probe,
)

REFERENCE_PROBE = Path("docs/validation/probes/clya-reference.probe.yaml")
"""The checked-in grid for the section 5.2.1 geometry, resolved from the repo root."""


def _grid(document: ProbeDocument, fields: tuple[str, ...]) -> ProbeGrid:
    """Return an all-retained grid for ``document``: the arithmetic, without a mesh."""
    import numpy as np

    keep = np.ones(document.count, dtype=bool)
    return ProbeGrid(
        document=document,
        points_nm=document.points_nm(),
        weights_nm2=document.weights_nm2(),
        masks=dict.fromkeys(fields, keep),
        dropped=dict.fromkeys(fields, 0),
    )


@pytest.fixture(scope="module")
def reference_document() -> ProbeDocument:
    """Return the checked-in probe grid for the reference geometry."""
    return load_probe(REFERENCE_PROBE)


# -- the closed form ----------------------------------------------------------


def test_val01_relative_l2_on_a_known_field() -> None:
    """Both norms match a closed form on a field whose sums are elementary.

    On one patch with ``r_i = i h`` and a reference field ``g = 1``, a difference
    ``s - g = r`` gives

        rel_L2_r^2 = sum r^3 / sum r   = h^2 n (n - 1) / 2
        rel_l2^2   = sum r^2 / n       = h^2 (n - 1)(2n - 1) / 6

    by Faulhaber's formulae, the constant patch weight and the ``z`` sum
    cancelling from both ratios. Independently derived rather than read off the
    implementation, and it is the ``r`` factor that separates the two — which is
    the only thing distinguishing the two norms at all.

    Exact to round-off: every sum is finite and the tolerance is the accumulation
    of a few thousand additions, not a quadrature budget.
    """
    import numpy as np

    count, spacing = 41, 0.25
    document = loads_probe(
        f"schema: {PROBE_SCHEMA}\nname: closed-form\npatches:\n"
        f"  - {{name: ramp, r_nm: [0.0, {(count - 1) * spacing}], z_nm: [0.0, 1.0], "
        f"n_r: {count}, n_z: 7}}\n"
    )
    grid = _grid(document, ("potential",))
    reference = np.ones(document.count, dtype=np.float64)
    ours = reference + grid.points_nm[:, 0]

    comparison = field_error("potential", ours, reference, grid, grid.masks["potential"])
    weighted = spacing * np.sqrt(count * (count - 1) / 2.0)
    plain = spacing * np.sqrt((count - 1) * (2 * count - 1) / 6.0)
    assert comparison.rel_L2_r == pytest.approx(weighted, rel=1e-12)
    assert comparison.rel_l2 == pytest.approx(plain, rel=1e-12)


def test_val01_a_difference_proportional_to_the_reference_is_that_ratio() -> None:
    """``s - g = alpha g`` gives ``alpha`` in every weighted norm, exactly.

    The one closed form that holds for any weights at all, so it isolates the
    ratio structure from the quadrature: a bug in either weight array would
    leave this passing and the test above failing, and vice versa.
    """
    import numpy as np

    document = loads_probe(
        f"schema: {PROBE_SCHEMA}\nname: scaled\npatches:\n"
        "  - {name: block, r_nm: [0.5, 3.5], z_nm: [-1.0, 1.0], n_r: 13, n_z: 9}\n"
    )
    grid = _grid(document, ("potential",))
    rng = np.random.default_rng(20260918)
    reference = rng.normal(size=document.count) + 3.0
    for alpha in (0.25, -0.125):
        comparison = field_error(
            "potential", (1.0 + alpha) * reference, reference, grid, grid.masks["potential"]
        )
        assert comparison.rel_L2_r == pytest.approx(abs(alpha), rel=1e-14)
        assert comparison.rel_l2 == pytest.approx(abs(alpha), rel=1e-14)


# -- the axis --------------------------------------------------------------


def test_val01_axis_defect_is_invisible_to_the_weighted_norm(
    reference_document: ProbeDocument,
) -> None:
    """A defect on the axis passes ``rel_L2_r`` and fails ``rel_l2``, on the real grid.

    ``g = 1`` everywhere and ``s = 2`` on the ``axis_line`` patch alone — 1 610 of
    6 205 points, every one of them within 0.045 nm of the symmetry axis. The
    unweighted norm sees ``sqrt(1610/6205) = 0.51``; the *r*-weighted norm sees
    about 4e-4, because those points carry a weight of ``0.001 nm^2 * r`` against
    a reservoir patch carrying ``6 nm^2 * r`` out to 60 nm.

    That three-order gap is the whole reason both numbers are reported. The
    thresholds are the WP13 plan's own: ``rel_L2_r < 1e-3`` and ``rel_l2 > 1e-1``.
    """
    import numpy as np

    grid = _grid(reference_document, ("potential",))
    names = np.asarray(reference_document.patch_of_point())
    on_axis = names == "axis_line"

    reference = np.ones(reference_document.count, dtype=np.float64)
    ours = reference + on_axis.astype(np.float64)
    comparison = field_error("potential", ours, reference, grid, grid.masks["potential"])

    assert comparison.rel_l2 == pytest.approx(np.sqrt(on_axis.sum() / on_axis.size), rel=1e-12)
    assert comparison.rel_l2 > 1e-1
    assert comparison.rel_L2_r < 1e-3
    # The maximum is located, and it is on the axis where the defect was put.
    assert comparison.max_abs_rel == pytest.approx(1.0)
    assert comparison.max_at_nm[0] <= 0.045


def test_val01_the_same_defect_at_the_wall_is_visible_to_both(
    reference_document: ProbeDocument,
) -> None:
    """The contrast is the axis, not the patch size: move the defect and both norms see it.

    Without this, the test above would be consistent with ``rel_L2_r`` simply
    being small whenever few points move.
    """
    import numpy as np

    grid = _grid(reference_document, ("potential",))
    names = np.asarray(reference_document.patch_of_point())
    far = names == "reservoir"

    reference = np.ones(reference_document.count, dtype=np.float64)
    comparison = field_error(
        "potential", reference + far.astype(np.float64), reference, grid, grid.masks["potential"]
    )
    assert comparison.rel_L2_r > 1e-1
    assert comparison.rel_l2 > 1e-1


# -- the pressure gauge -------------------------------------------------------


def test_val01_pressure_gauge_offset_does_not_register() -> None:
    """Adding a constant to ``p`` leaves the discrepancy unchanged, and is reported.

    ``p`` enters the momentum equation only through ``grad p``, and COMSOL's
    gauge is not ours and is not in the model report. Compared raw, a 1 000 Pa
    offset against a 10 Pa physical pressure is a 100-fold "discrepancy" that is
    not one — which this asserts by comparing the gauge-free number against the
    same fields with no offset at all.
    """
    import numpy as np

    document = loads_probe(
        f"schema: {PROBE_SCHEMA}\nname: gauge\npatches:\n"
        "  - {name: block, r_nm: [0.5, 5.5], z_nm: [-2.0, 2.0], n_r: 11, n_z: 17}\n"
    )
    grid = _grid(document, (PRESSURE_FIELD,))
    keep = grid.masks[PRESSURE_FIELD]
    rng = np.random.default_rng(13)
    reference = 10.0 * rng.normal(size=document.count)
    ours = reference + 0.5 * np.sin(grid.points_nm[:, 1])

    base = field_error(PRESSURE_FIELD, ours, reference, grid, keep)
    offset = 1.0e3
    shifted = field_error(PRESSURE_FIELD, ours + offset, reference, grid, keep)

    assert shifted.rel_L2_r == pytest.approx(base.rel_L2_r, rel=1e-14)
    assert shifted.rel_l2 == pytest.approx(base.rel_l2, rel=1e-14)
    assert shifted.gauge_removed is not None
    assert shifted.gauge_removed[0] - base.gauge_removed[0] == pytest.approx(offset, rel=1e-12)
    assert shifted.summary()["gauge_removed_Pa"]["difference"] == pytest.approx(
        shifted.gauge_removed[0] - shifted.gauge_removed[1], rel=1e-14
    )


def test_val01_no_other_field_is_gauge_shifted() -> None:
    """The potential's offset is physical — the cis electrode grounds it — so it counts.

    Removing a mean from ``phi`` would hide a wrong boundary condition, which is
    the opposite of what the pressure path is for.
    """
    import numpy as np

    document = loads_probe(
        f"schema: {PROBE_SCHEMA}\nname: gauge\npatches:\n"
        "  - {name: block, r_nm: [0.5, 5.5], z_nm: [-2.0, 2.0], n_r: 11, n_z: 17}\n"
    )
    grid = _grid(document, ("potential",))
    reference = np.full(document.count, 0.05, dtype=np.float64)
    comparison = field_error(
        "potential", reference + 0.01, reference, grid, grid.masks["potential"]
    )
    assert comparison.gauge_removed is None
    assert comparison.rel_L2_r == pytest.approx(0.2, rel=1e-12)


# -- the mask gate ------------------------------------------------------------


def test_val01_mask_disagreement_aborts_with_location() -> None:
    """Two statements about where a field exists must agree, or the run stops.

    Our mask is the set of points inside the field's ``definedon`` materials;
    the golden's is where COMSOL wrote a number rather than ``NaN``. Intersecting
    them would absorb a real geometry difference, so the disagreement aborts —
    naming the worst point's ``(r, z)`` and how far it is from the nearest point
    the other mask retains, which is what separates a one-element fringe from a
    block in the wrong place (QR-12).
    """
    import numpy as np

    document = loads_probe(
        f"schema: {PROBE_SCHEMA}\nname: masks\npatches:\n"
        "  - {name: block, r_nm: [0.0, 4.0], z_nm: [0.0, 6.0], n_r: 5, n_z: 7}\n"
    )
    grid = _grid(document, ("c_Na+",))
    ours = np.ones(document.count, dtype=bool)
    theirs = ours.copy()
    theirs[12] = False
    r_nm, z_nm = grid.points_nm[12]

    check_mask_agreement("c_Na+", ours, ours, grid)  # agreement is silent
    with pytest.raises(ProbeGridError) as raised:
        check_mask_agreement("c_Na+", ours, theirs, grid)
    message = str(raised.value)
    assert "c_Na+" in message
    assert f"{r_nm:.6g}" in message and f"{z_nm:.6g}" in message
    assert "1 of 35" in message
    assert "nm from the nearest point" in message


def test_val01_mask_disagreement_names_the_furthest_point_not_the_first() -> None:
    """The worst point is the diagnosis; the first is an accident of ordering.

    A fringe one spacing wide and a block three spacings deep are different
    problems, and the reported distance is what tells them apart.
    """
    import numpy as np

    document = loads_probe(
        f"schema: {PROBE_SCHEMA}\nname: masks\npatches:\n"
        "  - {name: block, r_nm: [0.0, 9.0], z_nm: [0.0, 6.0], n_r: 10, n_z: 7}\n"
    )
    grid = _grid(document, ("c_Na+",))
    points = grid.points_nm
    ours = np.ones(document.count, dtype=bool)
    theirs = ours.copy()
    # One point on the edge of the block, and a compact square well inside it.
    theirs[0] = False
    deep = np.flatnonzero((points[:, 0] >= 3.0) & (points[:, 0] <= 5.0))
    theirs[deep] = False

    with pytest.raises(ProbeGridError) as raised:
        check_mask_agreement("c_Na+", ours, theirs, grid)
    message = str(raised.value)
    # The missing block spans r in {3, 4, 5} nm at dr = 1 nm, so its middle
    # column is 2 nm from the nearest r the other mask still retains, while the
    # isolated point at the origin is 1 nm from its neighbour. The reported
    # point is the middle column's, and the reported distance is 2 nm.
    assert "2 nm from the nearest point" in message
    assert "(r, z) = (4," in message
    assert f"{len(deep) + 1} of {document.count}" in message
