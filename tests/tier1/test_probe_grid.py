"""The Tier-3 comparison surface: its refusals, and its domain mask (VAL-01, QR-12)."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from nanopnp.mesh.primitives import ELECTROLYTE_DOMAINS
from nanopnp.validation.probe import (
    PROBE_SCHEMA,
    ProbeDocument,
    ProbeGrid,
    ProbePatch,
    load_probe,
)

REFERENCE_PROBE = Path("docs/validation/probes/clya-reference.probe.yaml")


def _document(**patch: object) -> str:
    fields = {"name": "block", "r_nm": [0.0, 1.0], "z_nm": [0.0, 2.0], "n_r": 5, "n_z": 9}
    fields.update(patch)
    lines = "\n".join(f"    {key}: {value}" for key, value in fields.items())
    return f"schema: {PROBE_SCHEMA}\nname: probe\npatches:\n  -{lines[3:]}\n"


@pytest.fixture(scope="module")
def reference_mesh(clya_reference_mesh):  # type: ignore[no-untyped-def]
    return clya_reference_mesh()


@pytest.fixture(scope="module")
def reference_document() -> ProbeDocument:
    return load_probe(REFERENCE_PROBE)


@pytest.fixture(scope="module")
def reference_grid(reference_document: ProbeDocument, reference_mesh) -> ProbeGrid:
    return ProbeGrid.on_mesh(
        reference_document, reference_mesh, {"potential": None, "c": ELECTROLYTE_DOMAINS}
    )


# -- the transpose refusal ----------------------------------------------------


# -- the document is the interface --------------------------------------------


def test_val01_probe_hash_is_stable_and_moves_with_any_extent(
    reference_document: ProbeDocument,
) -> None:
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
    patch = reference_document.patches[0]
    points = patch.points_nm()
    r_axis, z_axis = patch.axes_nm()
    assert points.shape == (patch.count, 2)
    assert points[: patch.n_r, 1] == pytest.approx(z_axis[0])
    assert points[: patch.n_r, 0] == pytest.approx(r_axis)
    assert points[patch.n_r, 1] == pytest.approx(z_axis[1])


def test_val01_probe_axes_are_written_in_metres(reference_document: ProbeDocument) -> None:
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
    import numpy as np

    names = np.asarray(reference_grid.document.patch_of_point())
    on_axis = names == "axis_line"
    assert on_axis.any()
    assert reference_grid.masks["c"][on_axis].all()
    assert (reference_grid.points_nm[on_axis, 0] == 0.0).any()


def test_val01_probe_weights_are_each_patch_own_spacing(
    reference_grid: ProbeGrid, reference_document: ProbeDocument
) -> None:
    import numpy as np

    names = np.asarray(reference_document.patch_of_point())
    weights = reference_grid.weights_nm2
    for patch in reference_document.patches:
        selected = weights[names == patch.name]
        dr, dz = patch.spacing_nm
        assert selected == pytest.approx(dr * dz)
        assert math.isclose(dr * dz, patch.weight_nm2)
