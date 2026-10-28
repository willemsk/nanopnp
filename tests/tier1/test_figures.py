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
from nanopnp.post.export import SolutionFields


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


def _p2_square() -> tuple[np.ndarray, np.ndarray]:
    # The unit square in nm as two P2 triangles: four corners, then the five edge midpoints.
    corners = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    midsides = [(0.5, 0.0), (1.0, 0.5), (0.5, 0.5), (0.5, 1.0), (0.0, 0.5)]
    points_m = np.array(corners + midsides) * 1e-9
    cells = np.array([[0, 1, 2, 4, 5, 6], [0, 2, 3, 6, 7, 8]])
    return points_m, cells


def _fields(
    fluid: dict[str, np.ndarray],
    whole: dict[str, np.ndarray] | None = None,
    bulk_mol_m3: dict[str, float] | None = None,
) -> SolutionFields:
    points_m, cells = _p2_square()
    return SolutionFields(
        model="test",
        whole=(points_m, cells, whole or {}),
        fluid=(points_m, cells, fluid),
        bulk_mol_m3=bulk_mol_m3 or {},
    )


def test_radial_cutline_is_masked_outside_the_fluid() -> None:
    # A linear field is exact on the subdivided cells; past r = 1 nm the line leaves the fluid.
    pytest.importorskip("matplotlib")
    points_m, _ = _p2_square()
    r_nm, z_nm = points_m[:, 0] * 1e9, points_m[:, 1] * 1e9
    fields = _fields({"c_Na_mol_m3": 3.0 + 2.0 * r_nm - z_nm})
    r, values = data.radial_cutline(
        fields, "c_Na_mol_m3", z_nm=0.25, r_nm=np.linspace(0.0, 2.0, 41)
    )
    inside = r <= 1.0
    np.testing.assert_allclose(values[inside], 3.0 + 2.0 * r[inside] - 0.25, rtol=1e-12)
    assert np.isnan(values[~inside]).all()
    # r² is quadratic: only a split through the midsides returns it at the midside nodes.
    quadratic = _fields({"c_Na_mol_m3": r_nm**2})
    _, at_midsides = data.radial_cutline(quadratic, "c_Na_mol_m3", z_nm=0.0, r_nm=np.array([0.5]))
    np.testing.assert_allclose(at_midsides, [0.25], rtol=1e-12)
    # A swapped midside column keeps every node a vertex but overlaps the four sub-triangles.
    _, cells = _p2_square()

    def areas(triangles: np.ndarray) -> np.ndarray:
        a, b, c = (points_m[triangles[:, k]] for k in range(3))
        return np.asarray(
            0.5 * np.abs((b - a)[:, 0] * (c - a)[:, 1] - (c - a)[:, 0] * (b - a)[:, 1])
        )

    np.testing.assert_allclose(
        areas(data.subdivided(cells)).reshape(4, -1).sum(axis=0), areas(cells[:, :3]), rtol=1e-12
    )


def test_potential_panel_is_millivolts_centred_at_zero() -> None:
    # A one-signed potential: TwoSlopeNorm would raise, and a panel in V would read 0.02.
    # A set colour range is in mV too: one taken in V would saturate the whole panel.
    pytest.importorskip("matplotlib")
    from nanopnp.plot.panels import plot_field

    fields = _fields({}, {"phi_V": np.full(9, 0.02)})
    ax = plot_field(fields, "potential")
    image = ax.collections[0]
    np.testing.assert_allclose(np.asarray(image.get_array()), 20.0, rtol=1e-12)
    assert getattr(image.norm, "vcenter", None) == 0.0
    ranged = plot_field(fields, "potential", halfrange=100.0).collections[0]
    assert ranged.norm(20.0) == pytest.approx(0.6, rel=1e-12)


def test_concentration_panel_is_log_relative_to_each_species_bulk() -> None:
    # c = 2 c_bulk reads log10 2 against that species' own bulk, in mol/m3 as the solve imposed it:
    # one bulk for every species, or one in M, would read another number.
    pytest.importorskip("matplotlib")
    from nanopnp.plot.panels import plot_field

    fields = _fields(
        {"c_Na_mol_m3": np.full(9, 200.0), "c_Cl_mol_m3": np.full(9, 50.0)},
        bulk_mol_m3={"c_Na_mol_m3": 100.0, "c_Cl_mol_m3": 25.0},
    )
    for key in ("c_Na_mol_m3", "c_Cl_mol_m3"):
        image = plot_field(fields, key, relative=True).collections[0]
        np.testing.assert_allclose(np.asarray(image.get_array()), np.log10(2.0), rtol=1e-12)
        assert getattr(image.norm, "vcenter", None) == 0.0
    with pytest.raises(ValueError, match="record no bulk"):
        plot_field(_fields({"c_K_mol_m3": np.full(9, 1.0)}), "c_K_mol_m3", relative=True)


def test_sweep_panels_share_the_cis_referenced_bias_and_keep_failed_points() -> None:
    # Under ground: trans the recorded bias is the assigned one's negative; a failed point
    # records none, and must still be marked at its cis-referenced bias, on every panel alike.
    pytest.importorskip("matplotlib")
    from nanopnp.io.artefact import SWEEP_SCHEMA, Artefact
    from nanopnp.plot import figure

    def row(index: int, bias_V: float, ok: bool) -> dict[str, object]:
        quantities = {"current_A": -1e-9 * bias_V * 10, "eof_m3_s": 1e-21, "bias_V": -bias_V}
        return {
            "index": index,
            "assignments": {"boundary_conditions.bias_V": bias_V},
            "status": "ok" if ok else "failed",
            "quantities": quantities if ok else None,
        }

    rows = [row(0, -0.1, True), row(1, 0.05, False), row(2, 0.1, True)]
    drawn = figure(Artefact(schema=SWEEP_SCHEMA, parameters={}, summary={"rows": rows}))
    iv, flow = drawn.axes[:2]
    assert iv.lines[0].get_xdata().tolist() == pytest.approx([100.0, -50.0, -100.0])
    assert flow.lines[0].get_xdata().tolist() == pytest.approx([100.0, -50.0, -100.0])
    failed = [line for line in iv.lines if line.get_marker() == "x"]
    assert failed[0].get_xdata().tolist() == pytest.approx([-50.0])
    # With no point at a non-zero bias to say which side is ground, its sign is unknown.
    none_ok = data.cis_referenced_bias_V(
        data.SweepCurves(
            axis="boundary_conditions.bias_V",
            x=np.array([0.0, 0.05]),
            ok=np.array([True, False]),
            quantities={"bias_V": np.array([0.0, np.nan])},
        )
    )
    assert none_ok[0] == 0.0 and np.isnan(none_ok[1])


def test_qoi_rows_show_each_quantity_in_its_display_unit() -> None:
    # A species' current takes its mapping's unit; a nested key takes its own, not the parent's.
    from nanopnp.plot.data import qoi_rows

    rows = qoi_rows(
        {
            "current_A": 2e-9,
            "currents_A": {"Na+": 1.5e-9},
            "route_agreement": {"reaction_A": 2e-9, "relative_difference": 1e-5},
            "eof_m3_s": 3e-19,
            "forces": {"total_N": 2.5e-12},
        }
    )
    assert [(row["quantity"], row["value"], row["unit"]) for row in rows] == [
        ("current", "2", "nA"),
        ("currents (Na+)", "1.5", "nA"),
        ("route agreement (reaction)", "2", "nA"),
        ("route agreement (relative difference)", "1e-05", ""),
        ("eof", "0.3", "µm³/s"),
        ("forces (total)", "2.5", "pN"),
    ]
