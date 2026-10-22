"""Figures: the registry's classification and the data layer's unit conversions (FR-30)."""

from __future__ import annotations

import importlib

import numpy as np
import pytest

from nanopnp.core.stages import FIGURE_FREE, _catalogue, figure_target, walk_order
from nanopnp.materials.electrolyte import Electrolyte
from nanopnp.mesh.adapter import MeshData
from nanopnp.mesh.quality import element_quality
from nanopnp.plot import data


def test_figure_classification_both_ways() -> None:
    entries = _catalogue()
    for name in walk_order():
        declared = entries[name].figure is not None
        assert declared != (name in FIGURE_FREE), name
    targets = [entry.figure for entry in entries.values() if entry.figure is not None]
    targets.append(figure_target("nanopnp/sweep/v0.5"))
    assert all(target is not None for target in targets)
    for target in targets:
        module_name, _, attribute = str(target).partition(":")
        assert callable(getattr(importlib.import_module(module_name), attribute)), target


def test_structure_atoms_land_at_r_hypot_in_metres() -> None:
    # An atom at x = 3, y = 4 nm sits 5 nm from the axis; swapping r with x would give 3.
    r, z = data.atoms_r_z_m(np.array([[[3.0, 4.0, -2.0]]]))
    assert r[0] == pytest.approx(5.0e-9, rel=1e-12)
    assert z[0] == pytest.approx(-2.0e-9, rel=1e-12)


def test_mesh_size_and_sicn_are_si_per_element() -> None:
    # Two triangles of different size: a per-mesh scalar or a nm value would fail one of them.
    vertices = np.array([[0.0, 0.0], [2.0, 0.0], [0.0, 2.0], [4.0, 4.0]])
    triangles = np.array([[0, 1, 2], [1, 3, 2]])
    mesh = MeshData(
        vertices=vertices,
        triangles=triangles,
        triangle_material=np.zeros(2, dtype=np.int64),
        materials=("electrolyte",),
        edges=np.zeros((0, 2), dtype=np.int64),
        edge_group=np.zeros(0, dtype=np.int64),
        boundaries=(),
    )
    elements = data.mesh_elements(mesh)
    longest = [2.0 * np.sqrt(2.0), np.hypot(2.0, 4.0)]
    np.testing.assert_allclose(elements.size_m, np.array(longest) * 1e-9, rtol=1e-12)
    np.testing.assert_allclose(elements.sicn, element_quality(mesh).sicn, rtol=1e-12)
    np.testing.assert_allclose(elements.vertices_m, vertices * 1e-9, rtol=1e-12)


@pytest.mark.parametrize("driver", ["average", "ionic_strength"])
def test_correction_curve_follows_the_declared_driver(driver: str) -> None:
    electrolyte = Electrolyte.from_parameter_file("willems2020_nacl", driver=driver)
    curves = data.correction_curves(
        electrolyte.corrections,
        driver=electrolyte.driver,
        concentration_M=0.15,
        validity_M=electrolyte.validity_M,
    )
    assert curves
    for curve in curves:
        model = electrolyte.corrections[curve.name]
        far = np.full_like(curve.driver_M, data.FAR_FROM_WALL_NM)
        np.testing.assert_allclose(curve.factor_vs_driver, model.evaluate(curve.driver_M, far))
        at = np.full_like(curve.distance_m, 0.15)
        np.testing.assert_allclose(
            curve.factor_vs_distance, model.evaluate(at, curve.distance_m * 1e9), rtol=1e-12
        )
        assert curve.distance_m[0] == 0.0
        assert curve.validity_M == model.validity_M
        assert ("ionic strength" in curve.driver_label) == (driver == "ionic_strength")


def test_sweep_curves_keep_failed_points() -> None:
    # Rows arrive unordered with one failed point; it must stay, flagged, at its axis value.
    rows = [
        {"index": 0, "assignments": {"bias_V": 0.2}, "status": "ok", "quantities": {"I": 4.0}},
        {"index": 1, "assignments": {"bias_V": -0.2}, "status": "ok", "quantities": {"I": -4.0}},
        {"index": 2, "assignments": {"bias_V": 0.0}, "status": "failed", "quantities": None},
    ]
    curves = data.sweep_curves(rows)
    assert curves is not None
    assert curves.axis == "bias_V"
    assert curves.x.tolist() == [-0.2, 0.0, 0.2]
    assert curves.ok.tolist() == [True, False, True]
    assert curves.quantities["I"][[0, 2]].tolist() == [-4.0, 4.0]
    assert np.isnan(curves.quantities["I"][1])


def test_sweep_figure_draws_current_in_nanoamperes_and_scales() -> None:
    # A sweep whose current is in A must reach the I-V panel in nA, and scale must grow the canvas.
    pytest.importorskip("matplotlib")
    from nanopnp.io.artefact import SWEEP_SCHEMA, Artefact
    from nanopnp.plot import figure

    rows = [
        {
            "index": i,
            "assignments": {"boundary_conditions.bias_V": v},
            "status": "ok",
            "quantities": {"current_A": 2e-9 * v, "eof_m3_s": 1e-21 * v},
        }
        for i, v in enumerate([-0.1, 0.1])
    ]
    artefact = Artefact(schema=SWEEP_SCHEMA, parameters={}, summary={"rows": rows})
    drawn = figure(artefact)
    iv, flow = drawn.axes[:2]
    assert iv.get_ylabel() == "I (nA)"
    assert iv.lines[0].get_ydata().tolist() == pytest.approx([-0.2, 0.2])
    assert flow.get_ylabel() == "Q_EOF (µm³/s)"
    assert flow.lines[0].get_ydata().tolist() == pytest.approx([-1e-4, 1e-4])
    assert figure(artefact, scale=2.0).get_size_inches().tolist() == pytest.approx(
        (2 * drawn.get_size_inches()).tolist()
    )
