"""VER-50: stage 3, the reduction to (r, z): weights, mean, variances and the artefact."""

from __future__ import annotations

import logging
import math
from collections.abc import Callable
from pathlib import Path
from typing import TypeAlias

import numpy as np
import pytest
from scipy.special import ive

from nanopnp import Case, Session
from nanopnp.density.grid import read_grid, write_grid
from nanopnp.density.map import DensityMap
from nanopnp.density.radii import RadiusSet
from nanopnp.density.union import DensityGrid, canonical_grid, deposit
from nanopnp.io.store import Store
from nanopnp.symmetry.annular import annular_weights
from nanopnp.symmetry.reduce import (
    ReducedMap,
    harmonic_counts,
    reduce_map,
    unresolved_radius_nm,
)

logger = logging.getLogger(__name__)

H = 0.05

Assembly: TypeAlias = Callable[[float], tuple[np.ndarray, list[str], list[str]]]


def _map(grid: DensityGrid, function: object) -> DensityMap:
    z, y, x = np.meshgrid(grid.axis_nm("z"), grid.axis_nm("y"), grid.axis_nm("x"), indexing="ij")
    values = function(np.hypot(x, y), np.arctan2(y, x), z)  # type: ignore[operator]
    return DensityMap(values=values, grid=grid, header={})


def _grid(reach_nm: float, planes: int = 7) -> DensityGrid:
    return DensityGrid(
        spacing_nm=H,
        half_width=math.ceil(reach_nm / H) + 2,
        z_first=-(planes // 2),
        nz=planes,
    )


# -- the weights ----------------------------------------------------------------


# FR-05
def test_ver50_annular_weights_are_exact() -> None:
    weights = annular_weights(120, H)
    j = np.arange(weights.bins)
    exact = 2.0 * np.pi * j * H**2
    exact[0] = np.pi * H**2 / 4.0
    relative = np.max(np.abs(weights.areas_nm2 - exact) / exact)
    logger.info("annulus areas: worst relative error %.3g", relative)
    assert relative <= 1e-11

    radius, _ = weights.cell_coordinates()
    columns = np.asarray(weights.matrix.sum(axis=0)).reshape(-1)
    interior = radius + H / math.sqrt(2.0) <= (weights.half_width + 0.5) * H
    assert np.max(np.abs(columns[interior] - H**2)) <= 1e-12 * H**2

    rng = np.random.default_rng(50)
    grid = DensityGrid(spacing_nm=H, half_width=120, z_first=0, nz=3)
    _, y, x = np.meshgrid(grid.axis_nm("z"), grid.axis_nm("y"), grid.axis_nm("x"), indexing="ij")
    values = rng.uniform(0.0, 1.0, grid.shape) * (np.hypot(x, y) <= 119 * H)
    reduced = reduce_map(DensityMap(values=values, grid=grid, header={}), 12)
    binned = reduced.mean @ weights.areas_nm2
    direct = values.astype(np.float32).astype(np.float64).sum(axis=(1, 2)) * H**2
    assert np.max(np.abs(binned - direct) / direct) <= 1e-12


# -- the closed forms -------------------------------------------------------------


# FR-05, FR-06
@pytest.mark.parametrize("width", [0.15, 0.2])
@pytest.mark.parametrize("offset", [1.0, 1.7, 2.0, 5.0])
@pytest.mark.parametrize("n", [7, 12])
def test_ver50_off_axis_gaussian_closed_forms(width: float, offset: float, n: int) -> None:
    grid = _grid(offset + 5 * width)
    density = _map(
        grid,
        lambda r, theta, z: np.exp(
            -((r * np.cos(theta) - offset) ** 2 + (r * np.sin(theta)) ** 2 + z**2) / width**2
        ),
    )
    reduced = reduce_map(density, n)
    r = reduced.r_nm[None, :]
    z = reduced.z_nm[:, None]
    beta = 2.0 * r * offset / width**2
    envelope = np.exp(-((r - offset) ** 2 + z**2) / width**2)
    mean = envelope * ive(0, beta)
    cn = 2.0 * envelope**2 * sum(ive(k * n, beta) ** 2 for k in range(1, 400))
    raw = np.exp(-2.0 * ((r - offset) ** 2 + z**2) / width**2) * ive(0, 2.0 * beta) - mean**2
    resolved = reduced.harmonics[None, :] > 0
    peak = float(cn.max())
    errors = {
        "mean": float(np.max(np.abs(reduced.mean - mean))),
        "cn": float(np.max(np.abs(reduced.cn_variance - np.where(resolved, cn, 0.0)))),
        "peak": (float(reduced.cn_variance.max()) - peak) / peak,
        "raw": float(np.max(np.abs(reduced.raw_variance - raw))),
    }
    logger.info("w %.2f, r_i %.1f, C%d: %s", width, offset, n, errors)
    assert errors["mean"] <= 1e-3
    assert errors["cn"] <= 3e-5
    assert abs(errors["peak"]) <= 0.02
    assert errors["raw"] <= 1e-3


# CON-04, FR-06
@pytest.mark.parametrize("width", [0.15, 0.2])
@pytest.mark.parametrize("n", [7, 12])
def test_ver50_axisymmetric_input_has_no_variance(width: float, n: int) -> None:
    shapes = {
        "on-axis": lambda r, theta, z: np.exp(-(r**2 + z**2) / width**2),
        "ring 0.4": lambda r, theta, z: np.exp(-((r - 0.4) ** 2 + z**2) / width**2),
        "ring 2": lambda r, theta, z: np.exp(-((r - 2.0) ** 2 + z**2) / width**2),
    }
    for name, function in shapes.items():
        density = _map(_grid(2.0 + 5 * width), function)
        reduced = reduce_map(density, n)
        cn = float(np.max(np.abs(reduced.cn_variance)))
        raw = float(np.max(np.abs(reduced.raw_variance)))
        logger.info("%s, w %.2f, C%d: Cn %.3g, raw %.3g", name, width, n, cn, raw)
        assert cn <= 1e-6, name
        assert raw <= 5e-5, name
        if name == "ring 2":
            undetrended = reduce_map(density, n, detrend=False)
            logger.info("undetrended: Cn %.3g", float(undetrended.cn_variance.max()))
            assert undetrended.cn_variance.max() > 1e-4


@pytest.mark.parametrize("n", [7, 12])
@pytest.mark.parametrize("multiple", ["n", "2n", 5, 6, 3])
def test_ver50_cos_modulation(n: int, multiple: str | int) -> None:
    m = {"n": n, "2n": 2 * n}.get(str(multiple), multiple)
    assert isinstance(m, int)

    def envelope(r: np.ndarray) -> np.ndarray:
        return np.exp(-((r - 3.0) ** 2) / 0.64)

    density = _map(
        _grid(6.4, planes=3),
        lambda r, theta, z: (0.4 + 0.2 * np.cos(m * theta)) * envelope(r) + 0.0 * z,
    )
    reduced = reduce_map(density, n)
    outer = reduced.r_nm >= 1.0
    e = envelope(reduced.r_nm[outer])
    target = (0.2 * e) ** 2 / 2.0
    scale = float(target.max())
    cn = reduced.cn_variance[:, outer]
    raw = reduced.raw_variance[:, outer]
    mean = reduced.mean[:, outer]
    divides = m % n == 0
    measured = {
        "cn": float(np.max(np.abs(cn - (target if divides else 0.0)))) / scale,
        "raw": float(np.max(np.abs(raw - target))) / scale,
        "mean": float(np.max(np.abs(mean - 0.4 * e))) / 0.4,
    }
    logger.info("C%d, m %d: %s", n, m, measured)
    assert measured["cn"] <= (5e-3 if divides else 1e-3)
    assert measured["raw"] <= 5e-3
    assert measured["mean"] <= 1e-3


# -- symmetry of a deposited assembly ---------------------------------------------


def _synthetic_reduction(assembly: Assembly, turn_rad: float) -> ReducedMap:
    positions, names, _ = assembly(turn_rad)
    radii = RadiusSet.load("pdb2pqr_charmm")
    widths = 0.93 * 0.1 * np.array([radii.radius_A("ALA", name) for name in names])
    frames = positions[None]
    grid = canonical_grid(assembly(0.0)[0][None], widths, H)
    return reduce_map(DensityMap(values=deposit(frames, widths, grid), grid=grid, header={}), 12)


# FR-05
def test_ver50_cn_invariance(c12_assembly: Assembly) -> None:
    base = _synthetic_reduction(c12_assembly, 0.0)
    assert base.cn_variance.max() > 1e-2  # the assembly is far from axisymmetric
    for degrees, mean_tolerance, variance_fraction in (
        (90.0, 1e-12, 1e-12),
        (30.0, 1e-6, 1e-6),
        (15.0, 1e-3, 1e-2),
    ):
        turned = _synthetic_reduction(c12_assembly, math.radians(degrees))
        mean = float(np.max(np.abs(turned.mean - base.mean)))
        assert mean <= mean_tolerance, degrees
        for name in ("cn_variance", "raw_variance"):
            peak = float(getattr(base, name).max())
            moved = float(np.max(np.abs(getattr(turned, name) - getattr(base, name))))
            logger.info("turned %.0f deg: %s moved %.3g of %.3g", degrees, name, moved, peak)
            assert moved <= variance_fraction * peak, (degrees, name)


# -- the artefact ----------------------------------------------------------------


# FR-27, VER-23
def test_ver50_unresolved_region_and_artefact(synthetic_c12: Path, tmp_path: Path) -> None:
    counts = harmonic_counts(40, 12)
    radius = unresolved_radius_nm(12, H)
    assert radius == pytest.approx(12 * H / math.pi)
    r = np.arange(40) * H
    assert np.all(counts[r < radius] == 0)
    assert np.all(counts[r > radius] >= 1)
    assert counts[20] == math.floor(math.pi * 20 / 12)

    case = tmp_path / "reduction.case.yaml"
    case.write_text(
        "schema: nanopnp/case/v0.5\n"
        "name: reduction\n"
        "structure:\n"
        f"  source: {{path: {synthetic_c12}}}\n"
        "  symmetry: {point_group: C12}\n"
        "electrolyte:\n"
        "  species: [{name: Na+, z: +1}, {name: Cl-, z: -1}]\n"
        "  concentration_M: 0.1\n"
        "  parameters: willems2020_nacl\n"
        "boundary_conditions: {bias_V: 0.1}\n"
        "physics: {model: epnp-ns, solid_permittivities: {membrane: 3.2}}\n",
        encoding="utf-8",
    )
    store = Store(tmp_path / "store")
    result = Session(store, write=False).run(Case.load(case), upto="symmetry")
    artefact = result.artefacts["symmetry"]
    reduced = ReducedMap.read(artefact.payload["reduced"])
    assert reduced.digest() == artefact.summary["payload_digest"]
    assert artefact.summary["unresolved_radius_nm"] == pytest.approx(radius)
    assert np.array_equal(reduced.harmonics, harmonic_counts(reduced.r_nm.size, 12))
    assert np.all(reduced.cn_variance[:, reduced.harmonics == 0] == 0.0)
    assert artefact.inputs == {"density": result.artefacts["density"].hash}
    again = ReducedMap.read(reduced.write(tmp_path / "copy.npz"))
    assert again.digest() == reduced.digest()

    for name, grid in reduced.grids().items():
        assert grid.shape == (reduced.r_nm.size, reduced.z_nm.size)
        for suffix in (".npz", ".dx"):
            back = read_grid(write_grid(grid, tmp_path / f"{name}{suffix}"))
            assert back.origin_nm == pytest.approx(grid.origin_nm, abs=1e-6)
            assert np.max(np.abs(back.values - grid.values)) <= 1e-6

    assert Session(store, write=False).run(Case.load(case), upto="symmetry").stages[-1].cached
    stored = store.get(artefact.schema, artefact.hash)
    assert stored is not None
    assert not stored.hand_substituted
    ReducedMap(
        r_nm=reduced.r_nm,
        z_nm=reduced.z_nm,
        mean=reduced.mean * 0.5,
        cn_variance=reduced.cn_variance,
        raw_variance=reduced.raw_variance,
        harmonics=reduced.harmonics,
        header=reduced.header,
    ).write(stored.payload["reduced"])
    assert store.get(artefact.schema, artefact.hash).hand_substituted  # type: ignore[union-attr]
