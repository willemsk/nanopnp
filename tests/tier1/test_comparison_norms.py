"""The three norms, the gauge-free pressure and the mask gate (VAL-01, NUM-06, QR-12)."""

from __future__ import annotations

from pathlib import Path

import pytest

from nanopnp.validation.compare import (
    PRESSURE_FIELD,
    check_mask_agreement,
    compare_fields,
    field_error,
)
from nanopnp.validation.comsol import GOLDEN_SCHEMA, Golden, GoldenManifest
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
    import numpy as np

    keep = np.ones(document.count, dtype=bool)
    return ProbeGrid(
        document=document,
        points_nm=document.points_nm(),
        weights_nm2=document.weights_nm2(),
        masks=dict.fromkeys(fields, keep),
        bare=dict.fromkeys(fields, keep),
        dropped=dict.fromkeys(fields, 0),
    )


@pytest.fixture(scope="module")
def reference_document() -> ProbeDocument:
    return load_probe(REFERENCE_PROBE)


def test_val01_relative_l2_on_a_known_field() -> None:
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


def test_val01_axis_defect_is_invisible_to_the_weighted_norm(
    reference_document: ProbeDocument,
) -> None:
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
    assert comparison.max_abs_rel == pytest.approx(1.0)
    assert comparison.max_at_nm[0] <= 0.045


def test_val01_the_same_defect_at_the_wall_is_visible_to_both(
    reference_document: ProbeDocument,
) -> None:
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


def test_val01_pressure_gauge_offset_does_not_register() -> None:
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


# QR-12
def test_val01_a_norm_over_no_retained_point_aborts() -> None:
    import numpy as np

    document = loads_probe(
        f"schema: {PROBE_SCHEMA}\nname: empty\npatches:\n"
        "  - {name: block, r_nm: [0.5, 5.5], z_nm: [-2.0, 2.0], n_r: 11, n_z: 17}\n"
    )
    grid = _grid(document, ("potential",))
    values = np.zeros(document.count, dtype=np.float64)
    nothing = np.zeros(document.count, dtype=bool)
    with pytest.raises(ProbeGridError, match="retains no probe point"):
        field_error("potential", values + 1.0, values, grid, nothing)


# QR-12
def test_val01_mask_disagreement_aborts_with_location() -> None:
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

    check_mask_agreement("c_Na+", ours, ours, grid)
    with pytest.raises(ProbeGridError) as raised:
        check_mask_agreement("c_Na+", ours, theirs, grid)
    message = str(raised.value)
    assert "c_Na+" in message
    assert f"{r_nm:.6g}" in message and f"{z_nm:.6g}" in message
    assert "1 of 35" in message
    assert "nm from the nearest point" in message


def _banded(document: ProbeDocument) -> ProbeGrid:
    import numpy as np

    points = document.points_nm()
    bare = points[:, 1] < 6.0
    keep = bare & (points[:, 0] < 4.0)
    return ProbeGrid(
        document=document,
        points_nm=points,
        weights_nm2=document.weights_nm2(),
        masks={"c_Na+": keep},
        bare={"c_Na+": bare},
        dropped={"c_Na+": int(np.count_nonzero(bare & ~keep))},
    )


def _golden_defined_at(defined: object) -> Golden:
    import numpy as np

    manifest = GoldenManifest.model_validate(
        {
            "schema": GOLDEN_SCHEMA,
            "case": "fixture",
            "case_hash": "f" * 64,
            "probe": "masks",
            "probe_hash": "e" * 64,
            "refinement": "published",
            "source": "comsol",
            "comsol_version": "COMSOL 5.4",
            "model_file": "npgrid_clya_v8_NaCl_report.mph",
            "export_date": "2026-09-18",
            "fields": {
                "potential": {"expression": "V", "unit": "V"},
                "c_Na+": {"expression": "c_Na", "unit": "mol/m^3"},
            },
            "current_boundary": "the cis reservoir cap",
            "current_sign_reference": "cis",
            "quantities": {"bias_V": 0.05, "current_A": 1.0e-9},
        }
    )
    values = np.where(np.asarray(defined, dtype=bool), 1.0, np.nan)
    return Golden(
        manifest=manifest,
        values={"c_Na+": values},
        quantities=manifest.quantities,
        current_sign_flipped=False,
        hash="d" * 64,
    )


def test_val01_the_margin_band_is_in_neither_the_mask_gate_nor_the_norms() -> None:
    import numpy as np

    document = loads_probe(
        f"schema: {PROBE_SCHEMA}\nname: masks\npatches:\n"
        "  - {name: block, r_nm: [0.0, 4.0], z_nm: [0.0, 6.0], n_r: 5, n_z: 7}\n"
    )
    grid = _banded(document)
    keep, bare = grid.masks["c_Na+"], grid.bare["c_Na+"]
    assert int(np.count_nonzero(grid.band("c_Na+"))) == 6
    ours = {"c_Na+": np.where(keep, 1.0, np.nan)}

    for defined in (bare, keep):
        (comparison,) = compare_fields(ours, _golden_defined_at(defined), grid)
        assert comparison.points == int(np.count_nonzero(keep))
        assert comparison.rel_L2_r == 0.0

    outside = bare.copy()
    outside[np.flatnonzero(~bare)[0]] = True
    with pytest.raises(ProbeGridError, match="1 only by the golden"):
        compare_fields(ours, _golden_defined_at(outside), grid)
    missing = bare.copy()
    missing[np.flatnonzero(keep)[0]] = False
    with pytest.raises(ProbeGridError, match="1 kept only by us"):
        compare_fields(ours, _golden_defined_at(missing), grid)


def test_val01_mask_disagreement_names_the_furthest_point_not_the_first() -> None:
    import numpy as np

    document = loads_probe(
        f"schema: {PROBE_SCHEMA}\nname: masks\npatches:\n"
        "  - {name: block, r_nm: [0.0, 9.0], z_nm: [0.0, 6.0], n_r: 10, n_z: 7}\n"
    )
    grid = _grid(document, ("c_Na+",))
    points = grid.points_nm
    ours = np.ones(document.count, dtype=bool)
    theirs = ours.copy()
    theirs[0] = False
    deep = np.flatnonzero((points[:, 0] >= 3.0) & (points[:, 0] <= 5.0))
    theirs[deep] = False

    with pytest.raises(ProbeGridError) as raised:
        check_mask_agreement("c_Na+", ours, theirs, grid)
    message = str(raised.value)
    assert "2 nm from the nearest point" in message
    assert "(r, z) = (4," in message
    assert f"{len(deep) + 1} of {document.count}" in message
