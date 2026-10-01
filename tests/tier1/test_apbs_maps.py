"""VAL-06's driver without APBS: the maps it builds and the files it writes (WP29).

The construction of the WP29 plan's *Design* sections 2 and 3, checked on inputs
whose answer is known exactly. The hat-weighted charge map keeps the lattice's
charge and first moments. The staggered dielectric maps take each edge's harmonic
mean and sit ``h/2`` off the grid. The writer round-trips through GridDataFormats,
and the box refuses a charge it would cut, naming the face. None of this needs
APBS or NGSolve, and importing the module imports neither.
"""

from __future__ import annotations

import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from nanopnp.charge.kernel import SourceAtoms, sum_kernel
from nanopnp.density.grid import RadialGrid
from nanopnp.validation.apbs import (
    TOLERANCE,
    ApbsProblem,
    BoxError,
    ChargeExtent,
    CubicGrid,
    MaterialRaster,
    Norms,
    Val06Error,
    Val06Report,
    charge_extent,
    charge_map,
    check_box,
    check_report,
    dielectric_maps,
    face_map,
    fit_grid,
    lattice_charges,
    norms,
    probe_set,
    read_dx,
    write_dx,
    write_inputs,
)

H_NM = 0.1
DIME = 65
"""6.4 nm: the test lattice's kernel tails reach r = 2.1 nm, 1.1 nm inside each face."""


def _lattice() -> RadialGrid:
    """Return two smeared atoms off the axis and one on it, as stage 7 sums them."""
    atoms = SourceAtoms(
        r_nm=np.array([0.0, 0.73, 1.21]),
        z_nm=np.array([0.31, -0.42, 0.57]),
        width_nm=np.array([0.1, 0.0112, 0.15]),
        weight_e=np.array([1.0, -0.5, 0.25]),
        frame=np.zeros(3, dtype=np.int64),
        atom=np.arange(3, dtype=np.int64),
        frames=1,
        shift_z_nm=0.0,
    )
    return sum_kernel(atoms, 0.005).grid


@pytest.fixture(scope="module")
def lattice() -> RadialGrid:
    return _lattice()


@pytest.fixture(scope="module")
def grid(lattice: RadialGrid) -> CubicGrid:
    return fit_grid(charge_extent(lattice), spacing_nm=H_NM, dime=DIME)


def test_val06_the_charge_map_keeps_the_lattices_charge_and_first_moments(
    lattice: RadialGrid, grid: CubicGrid
) -> None:
    """The sum to 1e-12; the z-moment to 1e-12 e nm; the (x, y) dipole 0 to 1e-12 e nm."""
    charges = lattice_charges(lattice)
    q = float(charges.sum())
    z_moment = float(np.sum(charges * lattice.z_nm[:, None]))
    assert q == pytest.approx(0.75, rel=1e-12)

    found = charge_map(lattice, grid) * (grid.spacing_nm * 10.0) ** 3
    x, y, z = np.meshgrid(grid.axis(0), grid.axis(1), grid.axis(2), indexing="ij")
    assert float(found.sum()) == pytest.approx(q, rel=1e-12)
    assert abs(float(np.sum(found * z)) - z_moment) <= 1e-12
    assert abs(float(np.sum(found * x))) <= 1e-12
    assert abs(float(np.sum(found * y))) <= 1e-12


def test_val06_the_charge_map_is_in_e_per_cubic_angstrom(lattice: RadialGrid) -> None:
    """At 0.2 nm the node sums are divided by 8 cubic angstroms: the row the ring cannot see."""
    coarse = fit_grid(charge_extent(lattice), spacing_nm=0.2, dime=33)
    found = charge_map(lattice, coarse)
    assert float(found.sum()) * 8.0 == pytest.approx(0.75, rel=1e-12)


def _layered(spacing_nm: float, z0_nm: float, interface_nm: float) -> MaterialRaster:
    """Return a raster at ``eps`` 2 below ``interface_nm`` and 80 above, all fluid."""
    rows, columns = 800, 600
    z = z0_nm + (np.arange(rows) + 0.5) * spacing_nm
    eps = np.where(z < interface_nm, 2.0, 80.0)[:, None] * np.ones((1, columns))
    return MaterialRaster(
        spacing_nm=spacing_nm,
        z0_nm=z0_nm,
        permittivity=eps,
        material=np.zeros((rows, columns), dtype=np.int64),
        materials=("electrolyte",),
        fluid=frozenset({"electrolyte"}),
        solids=frozenset(),
    )


def test_val06_each_z_edge_takes_the_exact_harmonic_mean_of_a_layered_dielectric() -> None:
    """An interface a quarter of the way along a z edge: ``h / (h/4 / 2 + 3h/4 / 80)`` exactly.

    The x and y maps lie in a plane of one layer and take its value; the z map's
    edge from node ``k`` to ``k + 1`` straddles the interface. It lies on a raster
    cell face and between two of the eight sub-samples, so the eight-sample mean
    is the exact one.
    """
    grid = CubicGrid((-1.6, -1.6, -1.6), H_NM, 33)
    k = 16
    interface = grid.axis(2)[k] + 0.25 * H_NM
    raster = _layered(0.01, interface - 4.0, interface)
    x_map, y_map, z_map = dielectric_maps(raster, grid)
    exact = H_NM / (0.25 * H_NM / 2.0 + 0.75 * H_NM / 80.0)
    assert np.allclose(z_map[:, :, k], exact, rtol=1e-14, atol=0.0)
    assert np.all(z_map[:, :, :k] == 2.0)
    assert np.all(z_map[:, :, k + 1 :] == 80.0)
    for plane in (x_map, y_map):
        assert np.all(plane[:, :, : k + 1] == 2.0)
        assert np.all(plane[:, :, k + 1 :] == 80.0)


def test_val06_each_dielectric_map_is_staggered_half_a_spacing_along_its_axis(
    lattice: RadialGrid, grid: CubicGrid, tmp_path: Path
) -> None:
    """The written x, y and z maps start at the grid origin plus ``h/2`` along their own axis."""
    raster = _layered(0.01, grid.origin_nm[2] - 1.0, 0.0)
    problem = ApbsProblem(
        grid=grid,
        temperature_K=298.15,
        sdie=78.15,
        charge=charge_map(lattice, grid),
        dielectric=dielectric_maps(raster, grid),
        faces=face_map(grid, lambda r, z: r + z),
    )
    deck = write_inputs(problem, tmp_path)
    text = deck.read_text(encoding="ascii")
    assert "diel dx dielx.dx diely.dx dielz.dx" in text
    assert "bcfl map" in text and "usemap pot 1" in text and "usemap charge 1" in text
    assert f"dime {DIME} {DIME} {DIME}" in text and "grid 1.0000000000" in text
    for index, axis in enumerate("xyz"):
        _, origin, spacing = read_dx(tmp_path / f"diel{axis}.dx")
        expected = list(grid.origin_nm)
        expected[index] += 0.5 * H_NM
        assert np.allclose(origin, expected, atol=1e-12)
        assert spacing == pytest.approx(H_NM, rel=1e-12)
    for name in ("charge", "faces"):
        _, origin, _ = read_dx(tmp_path / f"{name}.dx")
        assert np.allclose(origin, grid.origin_nm, atol=1e-12)


def test_val06_the_dx_writer_round_trips_through_griddata(tmp_path: Path) -> None:
    """Values to 1e-10 relative, the origin and spacing in nm, an item count not a multiple of 3."""
    values = np.random.default_rng(6).standard_normal((5, 7, 11)) * 10.0 ** np.arange(11)
    path = write_dx(tmp_path / "map.dx", values, (-1.25, 0.5, 3.0), 0.2)
    read, origin, spacing = read_dx(path)
    assert values.size % 3 != 0
    assert np.allclose(read, values, rtol=1e-10, atol=0.0)
    assert np.allclose(origin, (-1.25, 0.5, 3.0), atol=1e-12)
    assert spacing == pytest.approx(0.2, rel=1e-12)


def test_val06_the_face_map_carries_the_potential_on_the_faces_only() -> None:
    """``bcfl map`` reads the faces; the interior is zero, and each face node has its ``(r, z)``."""
    grid = CubicGrid((-0.4, -0.4, 1.0), 0.2, 5)
    found = face_map(grid, lambda r, z: 1.0 + r + 10.0 * z)
    assert np.all(found[1:-1, 1:-1, 1:-1] == 0.0)
    x, y, z = np.meshgrid(grid.axis(0), grid.axis(1), grid.axis(2), indexing="ij")
    expected = 1.0 + np.hypot(x, y) + 10.0 * z
    face = np.ones(found.shape, dtype=bool)
    face[1:-1, 1:-1, 1:-1] = False
    assert np.allclose(found[face], expected[face], rtol=1e-12)


@pytest.mark.parametrize(
    ("extent", "face"),
    [
        (ChargeExtent(r_max_nm=2.5, z_min_nm=0.0, z_max_nm=1.0), "x-"),
        (ChargeExtent(r_max_nm=1.0, z_min_nm=-2.5, z_max_nm=1.0), "z-"),
        (ChargeExtent(r_max_nm=1.0, z_min_nm=0.0, z_max_nm=2.5), "z+"),
    ],
)
def test_val06_a_box_too_small_for_the_charge_is_refused_naming_the_face(
    extent: ChargeExtent, face: str
) -> None:
    """D3: the charge must lie 1 nm inside every face, or the run is refused, not cut."""
    grid = CubicGrid((-3.2, -3.2, -3.2), H_NM, 65)
    with pytest.raises(BoxError, match=re.escape(f"{face} face")):
        check_box(grid, extent)


def test_val06_fit_grid_puts_the_axis_on_a_node_line_and_the_membrane_between_planes() -> None:
    """D3: x and y centred on the axis; each membrane face midway between two fine planes."""
    extent = ChargeExtent(r_max_nm=6.45, z_min_nm=-2.24, z_max_nm=12.84)
    grid = fit_grid(extent, interface_z_nm=1.4)
    assert (grid.dime, grid.spacing_nm, grid.nlev()) == (193, 0.1, 4)
    x = grid.axis(0)
    assert np.min(np.abs(x)) <= 1e-12 and np.min(np.abs(grid.axis(1))) <= 1e-12
    for face in (1.4, -1.4):
        offset = (face - grid.origin_nm[2]) / grid.spacing_nm
        assert offset - math.floor(offset) == pytest.approx(0.5, abs=1e-9)
    assert grid.coarsened().dime == 97 and grid.coarsened().nlev() == 4
    with pytest.raises(ValueError, match="nlev"):
        CubicGrid((0.0, 0.0, 0.0), 0.1, 51).nlev()


def test_val06_probes_lie_in_the_fluid_clear_of_solids_and_faces() -> None:
    """D6: nested-grid nodes in the fluid, at least 0.3 nm from a solid and 0.4 nm inside."""
    grid = CubicGrid((-1.6, -1.6, -1.6), H_NM, 33)
    rows, columns = 400, 300
    spacing = 0.01
    z0 = -2.0
    z = z0 + (np.arange(rows) + 0.5) * spacing
    r = (np.arange(columns) + 0.5) * spacing
    solid = (np.hypot(r[None, :], z[:, None]) < 0.8).astype(np.int64)
    raster = MaterialRaster(
        spacing_nm=spacing,
        z0_nm=z0,
        permittivity=np.where(solid == 1, 20.0, 78.15),
        material=solid,
        materials=("electrolyte", "protein"),
        fluid=frozenset({"electrolyte"}),
        solids=frozenset({"protein"}),
    )
    probes = probe_set(grid, raster)
    rho = np.linalg.norm(probes.points_nm, axis=1)
    assert np.all(rho >= 0.8 + 0.3 - spacing)
    assert np.all(np.abs(probes.points_nm) <= 1.6 - 0.4 + 1e-9)
    assert np.all(probes.fine % 2 == 0) and np.array_equal(probes.coarse * 2, probes.fine)
    on_axis = np.hypot(probes.points_nm[:, 0], probes.points_nm[:, 1]) == 0.0
    assert np.array_equal(on_axis, probes.axis) and probes.axis.any()


def test_val06_norms_and_the_check_read_the_budget_before_the_agreement() -> None:
    """D6 and D8: the three norms, and a failing budget named before an agreement is read."""
    reference = np.array([1.0, -2.0, 4.0, 0.5])
    difference = np.array([0.01, 0.0, -0.02, 0.0])
    axis = np.array([True, False, False, True])
    found = norms(difference, reference, axis)
    assert found.max == pytest.approx(0.02 / 4.0)
    assert found.rms == pytest.approx(math.sqrt(0.0005 / 4) / math.sqrt(21.25 / 4))
    assert found.axis == pytest.approx(0.01 / 1.0)

    small = Norms(max=0.001, rms=0.001, axis=0.001)

    def report(budget: Norms, agreement: Norms, visibility: float = 1.0) -> Val06Report:
        return Val06Report(
            leg="gated",
            structure="test",
            temperature_K=298.15,
            grid={},
            coarse_grid={},
            probes=4,
            axis_probes=2,
            potential_scale={},
            apbs_refinement=budget,
            ours_refinement=Norms(max=0.0, rms=0.0, axis=0.0),
            budget=budget,
            charge_visibility=visibility,
            agreement=agreement,
            tolerance=TOLERANCE,
            seconds={},
            memory_GB={},
        )

    check_report(report(small, small))
    nan = float("nan")
    assert Norms(max=nan, rms=0.0, axis=0.0).exceeding(TOLERANCE) == ["max"]
    with pytest.raises(Val06Error, match="charge moves the probes"):
        check_report(report(small, small, visibility=nan))
    with pytest.raises(ValueError, match="reference potential is zero"):
        norms(difference, np.zeros(4), axis)
    wide = Norms(max=0.02, rms=0.001, axis=0.001)
    with pytest.raises(Val06Error, match="refinement budget fails in the max norm"):
        check_report(report(wide, Norms(max=0.5, rms=0.5, axis=0.5)))
    with pytest.raises(Val06Error, match="charge moves the probes"):
        check_report(report(small, small, visibility=0.05))
    with pytest.raises(Val06Error, match="agreement fails in the rms norm"):
        check_report(report(small, Norms(max=0.001, rms=0.02, axis=0.001)))


def test_val06_importing_the_driver_imports_neither_apbs_nor_ngsolve() -> None:
    """The driver is introspectable cold: APBS is imported where it runs, NGSolve by the caller."""
    found = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys, nanopnp.validation.apbs; "
            "print(sorted(m for m in ('apbs_binary', 'ngsolve', 'scipy') if m in sys.modules))",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert found.stdout.strip() == "[]"
