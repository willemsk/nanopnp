"""VAL-06 at Tier 2 on a closed form: a Gaussian ring in a grounded dielectric sphere (WP29 D10).

*Design* section 4 of the WP29 plan. A ring of unit charge at ``(r_b, z_b)``, each
point smeared as PHY-16 step 4's 3D Gaussian of width ``w``, lies inside a sphere
of radius ``a`` and permittivity ``eps_1`` in water (``eps_2 = eps_r,f^0``),
grounded at ``R``. Outside ``rho = b`` the smeared ring is the point ring to
``erfc`` of the gap over ``w``, about 1e-35 here, so in the water

    phi = sum_l (B_l rho^l + C_l rho^-(l+1)) P_l(cos theta),

with ``B_l``, ``C_l`` and the inner ``A_l`` fixed per ``l`` by the continuity of
``phi`` and of ``D.n`` at ``a`` and by ``phi(R) = 0``. Inside, the ring's own
potential is its azimuthal mean of ``erf(d/w)/d``, which the continuity check
evaluates by the periodic trapezoid rule.

APBS at 0.1 nm, with the box faces from the series, and our ``P2`` are each held to
half of VAL-06's tolerance against the series, and to the whole tolerance against
each other. Then every broken construction of *Design* section 6 must exceed half
the tolerance in the norm it names. This is the test that localises a failure of
the 2WCD comparison to the driver or to a solver.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pytest
from scipy.special import erf, eval_legendre

from nanopnp.charge.deposit import deposit, gridfunction
from nanopnp.charge.kernel import SourceAtoms, sum_kernel
from nanopnp.core.constants import BOLTZMANN, ELEMENTARY_CHARGE, VACUUM_PERMITTIVITY
from nanopnp.density.grid import RadialGrid
from nanopnp.materials.electrolyte import Electrolyte
from nanopnp.mesh.adapter import from_ngsolve, to_ngsolve
from nanopnp.numerics.measures import AXISYMMETRIC
from nanopnp.physics import models
from nanopnp.validation.apbs import (
    TOLERANCE,
    ApbsProblem,
    ApbsSolution,
    CubicGrid,
    MaterialRaster,
    Norms,
    ProbeSet,
    charge_extent,
    charge_map,
    dielectric_maps,
    face_map,
    fit_grid,
    norms,
    potential_sampler,
    probe_set,
    raster_extent,
    raster_from_mesh,
    run_apbs,
)

logger = logging.getLogger(__name__)

RING_R_NM = 1.0
"""``r_b``."""

RING_Z_NM = 0.5
"""``z_b``."""

WIDTH_NM = 0.1
"""``w`` of each ring point's Gaussian."""

SPHERE_NM = 2.0
"""``a``: the dielectric sphere."""

SPHERE_PERMITTIVITY = 20.0
"""``eps_1``, the protein's value (PHY-20, ``physics.solid_permittivities``)."""

GROUND_NM = 20.0
"""``R``: the grounded sphere, the half-disc's arc."""

TEMPERATURE_K = 298.15
"""The case default (``electrolyte.temperature_K``)."""

TERMS = 80
"""``l`` from 0 to 80: inside, the series converges as ``(b/a)^l = 0.56^l``."""

LATTICE_NM = 0.005
"""The export lattice's spacing (PHY-16 step 6)."""

APBS_DIME = 65
"""6.4 nm at 0.1 nm, which holds the ring 1.8 nm inside every face."""

HALF = TOLERANCE.scaled(0.5)


def water_permittivity() -> float:
    """Return ``eps_r,f^0`` of the willems2020 NaCl parameters, the fluid ``poisson`` assembles."""
    return Electrolyte.from_parameter_file("willems2020_nacl").permittivity_0


def bjerrum_vacuum_nm(temperature_K: float = TEMPERATURE_K) -> float:
    """Return ``l_B^0 = e^2 / (4 pi eps_0 k T)`` in nm.

    APBS's ``kT/e`` and the solver's ``phi~`` are the same unit at the same temperature.
    """
    return (
        ELEMENTARY_CHARGE**2
        / (4.0 * math.pi * VACUUM_PERMITTIVITY * BOLTZMANN * temperature_K)
        * 1e9
    )


@dataclass(frozen=True)
class Series:
    """The scaled coefficients ``A'_l = A_l a^l``, ``B'_l = B_l a^l``, ``C'_l = C_l a^-(l+1)``."""

    a: np.ndarray
    b: np.ndarray
    c: np.ndarray
    eps_1: float
    eps_2: float
    k: float

    @classmethod
    def build(
        cls,
        *,
        eps_1: float = SPHERE_PERMITTIVITY,
        eps_2: float | None = None,
        ground_nm: float = GROUND_NM,
    ) -> Series:
        """Solve the three conditions per ``l`` in the scaled unknowns, which keep them O(1).

        With ``beta'_l = k p_l (b/a)^l / (eps_1 a)`` and ``gamma = (a/R)^(2l+1)``,
        grounding gives ``B' = -gamma C'``, continuity ``A' = (1 - gamma) C' - beta'``,
        and the displacement
        ``C' = eps_1 (2l+1) beta' / (eps_1 l (1 - gamma) + eps_2 (l (1 + gamma) + 1))``.
        As ``R -> inf``, ``C_l = k p_l b^l (2l+1) / (eps_1 l + eps_2 (l+1))``: Kirkwood's.
        """
        eps_2 = water_permittivity() if eps_2 is None else eps_2
        k = bjerrum_vacuum_nm()
        ell = np.arange(TERMS + 1, dtype=np.float64)
        b = math.hypot(RING_R_NM, RING_Z_NM)
        p = eval_legendre(ell, RING_Z_NM / b)
        beta = k * p * (b / SPHERE_NM) ** ell / (eps_1 * SPHERE_NM)
        gamma = (SPHERE_NM / ground_nm) ** (2 * ell + 1)
        c = (
            eps_1
            * (2 * ell + 1)
            * beta
            / (eps_1 * ell * (1 - gamma) + eps_2 * (ell * (1 + gamma) + 1))
        )
        return cls(a=(1 - gamma) * c - beta, b=-gamma * c, c=c, eps_1=eps_1, eps_2=eps_2, k=k)

    def outside(self, r_nm: np.ndarray, z_nm: np.ndarray) -> np.ndarray:
        """Return ``phi~`` at ``a <= rho <= R``."""
        rho = np.hypot(r_nm, z_nm)
        if np.any(rho < SPHERE_NM * (1 - 1e-12)):
            raise ValueError("the outer series holds only outside the sphere")
        cosine = np.where(rho > 0, z_nm / np.where(rho > 0, rho, 1.0), 1.0)
        total = np.zeros_like(rho, dtype=np.float64)
        for ell in range(TERMS + 1):
            radial = self.b[ell] * (rho / SPHERE_NM) ** ell + self.c[ell] * (SPHERE_NM / rho) ** (
                ell + 1
            )
            total += radial * eval_legendre(ell, cosine)
        return total

    def inside(self, r_nm: np.ndarray, z_nm: np.ndarray, *, angles: int = 2048) -> np.ndarray:
        """Return ``phi~`` at ``rho <= a``: the ring's own potential plus the reaction field."""
        rho = np.hypot(r_nm, z_nm)
        cosine = np.where(rho > 0, z_nm / np.where(rho > 0, rho, 1.0), 1.0)
        theta = 2.0 * math.pi * np.arange(angles) / angles
        d = np.sqrt(
            r_nm[..., None] ** 2
            + RING_R_NM**2
            - 2.0 * r_nm[..., None] * RING_R_NM * np.cos(theta)
            + (z_nm[..., None] - RING_Z_NM) ** 2
        )
        own = np.mean(erf(d / WIDTH_NM) / d, axis=-1)
        total = (self.k / self.eps_1) * own
        for ell in range(TERMS + 1):
            total = total + self.a[ell] * (rho / SPHERE_NM) ** ell * eval_legendre(ell, cosine)
        return np.asarray(total)


def test_val06_the_ring_series_is_grounded_continuous_and_kirkwood_at_infinity() -> None:
    """The oracle first: zero at ``R``, continuous at ``a``, Kirkwood's ``C_l`` as ``R -> inf``."""
    series = Series.build()
    angles = np.linspace(-0.5 * math.pi, 0.5 * math.pi, 61)
    r_ground, z_ground = GROUND_NM * np.cos(angles), GROUND_NM * np.sin(angles)
    on_sphere = SPHERE_NM * np.cos(angles), SPHERE_NM * np.sin(angles)
    peak = float(np.max(np.abs(series.outside(*on_sphere))))
    assert np.max(np.abs(series.outside(r_ground, z_ground))) <= 1e-12 * peak
    inner = series.inside(*on_sphere)
    outer = series.outside(*on_sphere)
    assert np.max(np.abs(inner - outer)) <= 1e-9 * peak
    unbounded = Series.build(ground_nm=1e12)
    ell = np.arange(TERMS + 1)
    b = math.hypot(RING_R_NM, RING_Z_NM)
    kirkwood = (
        unbounded.k
        * eval_legendre(ell, RING_Z_NM / b)
        * b**ell
        * (2 * ell + 1)
        / (unbounded.eps_1 * ell + unbounded.eps_2 * (ell + 1))
    )
    assert np.allclose(unbounded.c * SPHERE_NM ** (ell + 1), kirkwood, rtol=1e-12, atol=0.0)
    # l = 0 by hand: the total charge sees eps_2 outside, k/(eps_2 rho) less its value at R.
    assert series.c[0] * SPHERE_NM == pytest.approx(series.k / series.eps_2, rel=1e-12)
    assert series.b[0] == pytest.approx(-series.k / (series.eps_2 * GROUND_NM), rel=1e-12)


def _mesh(near_nm: float) -> object:
    """Return the grounded half-disc with the sphere as material ``protein``, water outside."""
    import netgen.occ as occ
    import ngsolve as ngs

    disc = occ.Circle(occ.Pnt(0.0, 0.0), GROUND_NM).Face()
    half = disc * occ.MoveTo(0.0, -GROUND_NM).Rectangle(GROUND_NM, 2.0 * GROUND_NM).Face()
    sphere = occ.Circle(occ.Pnt(0.0, 0.0), SPHERE_NM).Face() * half
    sphere.name = "protein"
    sphere.maxh = near_nm
    box = occ.Circle(occ.Pnt(0.0, 0.0), 6.0).Face() * half - sphere
    box.name = "electrolyte"
    box.maxh = near_nm
    outer = half - box - sphere
    outer.name = "electrolyte"
    shape = occ.Glue([sphere, box, outer])
    for edge in shape.edges:
        start, end = edge.start, edge.end
        if abs(start[0]) < 1e-9 and abs(end[0]) < 1e-9:
            edge.name = "axis"
        elif all(abs(math.hypot(p[0], p[1]) - GROUND_NM) < 1e-6 for p in (start, end)):
            edge.name = "cis" if start[1] + end[1] > 0 else "trans"
        elif all(abs(math.hypot(p[0], p[1]) - SPHERE_NM) < 1e-6 for p in (start, end)):
            edge.name = "interface"
            edge.maxh = 0.02
        else:
            edge.name = "interface"
    generated = occ.OCCGeometry(shape, dim=2).GenerateMesh(maxh=2.0)
    return to_ngsolve(from_ngsolve(ngs.Mesh(generated)))


@dataclass(frozen=True)
class Ring:
    """The ring solved by us, rastered, and set up for APBS."""

    series: Series
    lattice: RadialGrid
    ours: Callable[[np.ndarray, np.ndarray], np.ndarray]
    raster: MaterialRaster
    grid: CubicGrid
    probes: ProbeSet
    problem: ApbsProblem
    exact: np.ndarray
    """The series at the probes."""
    elements: int


@pytest.fixture(scope="module")
def ring() -> Ring:
    """Deposit and solve the ring at ``P2``, raster the solve and build APBS's maps at 0.1 nm."""
    eps_2 = water_permittivity()
    series = Series.build(eps_2=eps_2)
    atoms = SourceAtoms(
        r_nm=np.array([RING_R_NM]),
        z_nm=np.array([RING_Z_NM]),
        width_nm=np.array([WIDTH_NM]),
        weight_e=np.array([1.0]),
        frame=np.zeros(1, dtype=np.int64),
        atom=np.zeros(1, dtype=np.int64),
        frames=1,
        shift_z_nm=0.0,
    )
    lattice = sum_kernel(atoms, LATTICE_NM).grid
    mesh = _mesh(0.05)
    data = from_ngsolve(mesh)
    found = deposit(lattice, data, 2)
    electrolyte = Electrolyte.from_parameter_file("willems2020_nacl")
    model = models.create(
        "poisson", electrolyte=electrolyte, solid_permittivities={"protein": SPHERE_PERMITTIVITY}
    )
    scales = model.scales
    assert scales.temperature_K == pytest.approx(TEMPERATURE_K)
    solution = model.solve(
        mesh,
        AXISYMMETRIC,
        potential_values=mesh.BoundaryCF({"cis": 0.0, "trans": 0.0}),  # type: ignore[attr-defined]
        fixed_charge=gridfunction(found, mesh) / scales.charge_density_C_m3,
    )
    grid = fit_grid(charge_extent(lattice), dime=APBS_DIME)
    r_max, z_min, z_max = raster_extent(grid)
    raster = raster_from_mesh(
        mesh,  # type: ignore[arg-type]
        model.permittivity(mesh) * scales.relative_permittivity,  # type: ignore[attr-defined]
        fluid=model.fluid,  # type: ignore[attr-defined]
        solids=["protein"],
        r_max_nm=r_max,
        z_min_nm=z_min,
        z_max_nm=z_max,
    )
    probes = probe_set(grid, raster)
    problem = ApbsProblem(
        grid=grid,
        temperature_K=TEMPERATURE_K,
        sdie=eps_2,
        charge=charge_map(lattice, grid),
        dielectric=dielectric_maps(raster, grid),
        faces=face_map(grid, series.outside),
    )
    exact = probes.sample(series.outside)
    return Ring(
        series=series,
        lattice=lattice,
        ours=potential_sampler(solution, order=2),
        raster=raster,
        grid=grid,
        probes=probes,
        problem=problem,
        exact=exact,
        elements=data.element_count,
    )


@pytest.fixture(scope="module")
def apbs_ring(ring: Ring, apbs: None, tmp_path_factory: pytest.TempPathFactory) -> ApbsSolution:
    """APBS on the ring's maps, with the series on the faces."""
    return run_apbs(ring.problem, tmp_path_factory.mktemp("val06-ring"), name="ring")


def _against_series(ring: Ring, values: np.ndarray) -> Norms:
    return norms(values - ring.exact, ring.exact, ring.probes.axis)


def test_val06_ring_p2_is_within_half_the_tolerance_of_the_series(ring: Ring) -> None:
    """Our side alone: the deposit and ``poisson`` at ``P2`` against the series at the probes."""
    found = _against_series(ring, ring.probes.sample(ring.ours))
    logger.info(
        "VAL-06 ring: P2 (%d elements) against the series over %d probes (%d on the axis): %s",
        ring.elements,
        ring.probes.count,
        int(np.count_nonzero(ring.probes.axis)),
        found,
    )
    assert not found.exceeding(HALF), found


def test_val06_ring_apbs_is_within_half_the_tolerance_of_the_series(
    ring: Ring, apbs_ring: ApbsSolution
) -> None:
    """The driver and APBS: hat-weighted charge, harmonic staggered diel, series faces."""
    found = _against_series(ring, ring.probes.at(apbs_ring.potential))
    logger.info(
        "VAL-06 ring: APBS %d^3 at %.2f nm against the series: %s (%.1f s)",
        ring.grid.dime,
        ring.grid.spacing_nm,
        found,
        apbs_ring.seconds,
    )
    assert not found.exceeding(HALF), found


def test_val06_ring_the_two_solvers_agree_within_the_tolerance(
    ring: Ring, apbs_ring: ApbsSolution
) -> None:
    """D6's metric between the solvers, as the 2WCD leg forms it, but with series faces."""
    ours = ring.probes.sample(ring.ours)
    found = norms(ring.probes.at(apbs_ring.potential) - ours, ours, ring.probes.axis)
    logger.info("VAL-06 ring: APBS against P2: %s", found)
    assert not found.exceeding(TOLERANCE), found


def _node_sampled_dielectric(ring: Ring) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Each map's values at the grid *nodes*, while APBS reads them at the staggered origin."""
    grid = ring.grid
    x, y, z = grid.axis(0), grid.axis(1), grid.axis(2)
    radius = np.hypot(x[:, None], y[None, :])
    i_r = ring.raster.r_index(radius)
    i_z = ring.raster.z_index(z)
    values = ring.raster.permittivity[i_z][:, i_r]
    nodes = np.ascontiguousarray(np.moveaxis(values, 0, -1))
    return nodes, nodes.copy(), nodes.copy()


def _point_sampled_charge(ring: Ring, width_nm: float) -> np.ndarray:
    """Return the ring at ``width_nm`` point-sampled at the nodes, in e per cubic angstrom."""
    grid = ring.grid
    x, y, z = np.meshgrid(grid.axis(0), grid.axis(1), grid.axis(2), indexing="ij")
    theta = 2.0 * math.pi * np.arange(512) / 512
    total = np.zeros_like(x)
    for angle in theta:
        distance2 = (
            (x - RING_R_NM * math.cos(angle)) ** 2
            + (y - RING_R_NM * math.sin(angle)) ** 2
            + (z - RING_Z_NM) ** 2
        )
        total += np.exp(-distance2 / width_nm**2)
    density_nm3 = total / theta.size / (math.pi**1.5 * width_nm**3)
    return density_nm3 / 1000.0


def _circumference_dropped(ring: Ring) -> np.ndarray:
    """Return the map of the lattice divided by ``2 pi r`` in nm: areal read as volume density."""
    lattice = ring.lattice
    r = np.where(lattice.r_nm > 0, lattice.r_nm, np.inf)
    broken = RadialGrid(lattice.origin_nm, lattice.spacing_nm, lattice.values / (2 * math.pi * r))
    return charge_map(broken, ring.grid)


def _shifted(ring: Ring, dz_nm: float) -> np.ndarray:
    lattice = ring.lattice
    moved = RadialGrid(
        (lattice.origin_nm[0], lattice.origin_nm[1] + dz_nm), lattice.spacing_nm, lattice.values
    )
    return charge_map(moved, ring.grid)


def _coarse(ring: Ring, *, charge_scale: float = 1.0) -> ApbsProblem:
    """Return the ring's problem on the nested ``2h`` grid, its charge times ``charge_scale``."""
    coarse = ring.grid.coarsened()
    return ApbsProblem(
        grid=coarse,
        temperature_K=TEMPERATURE_K,
        sdie=ring.problem.sdie,
        charge=charge_map(ring.lattice, coarse) * charge_scale,
        dielectric=dielectric_maps(ring.raster, coarse),
        faces=face_map(coarse, ring.series.outside),
    )


BROKEN: dict[str, tuple[Callable[[Ring], ApbsProblem], tuple[str, ...]]] = {
    # At h = 0.1 nm = 1 angstrom, e per node and e per cubic angstrom are the same
    # number, so this row is invisible on the fine grid: it runs on the nested
    # 0.2 nm grid, where the factor is 8, as the 2WCD leg's 2h solve would see it.
    "charge in e per node, no 1/h^3": (
        lambda ring: _coarse(ring, charge_scale=(2.0 * ring.grid.spacing_nm * 10.0) ** 3),
        ("max", "rms", "axis"),
    ),
    "areal density read as a volume density": (
        lambda ring: replace(ring.problem, charge=_circumference_dropped(ring)),
        ("max", "rms", "axis"),
    ),
    "charge point-sampled, w = 0.0112 nm": (
        lambda ring: replace(ring.problem, charge=_point_sampled_charge(ring, 0.0112)),
        ("max", "rms", "axis"),
    ),
    "diel at the nodes, declared staggered": (
        lambda ring: replace(ring.problem, dielectric=_node_sampled_dielectric(ring)),
        ("max",),
    ),
    "temp 310 K against 298.15 K": (
        lambda ring: replace(ring.problem, temperature_K=310.0),
        ("max", "rms", "axis"),
    ),
    "charge 0.5 nm off in z": (
        lambda ring: replace(ring.problem, charge=_shifted(ring, 0.5)),
        ("max", "rms", "axis"),
    ),
    "bcfl zero in place of the faces": (
        lambda ring: replace(ring.problem, faces=None),
        ("max",),
    ),
    "charge map zeroed": (
        lambda ring: replace(ring.problem, charge=np.zeros_like(ring.problem.charge)),
        ("max", "rms", "axis"),
    ),
}
"""*Design* section 6: each construction and the norms it must exceed half the tolerance in."""


@pytest.mark.parametrize("name", list(BROKEN))
def test_val06_ring_every_broken_construction_exceeds_half_the_tolerance(
    ring: Ring, apbs: None, name: str, tmp_path: Path
) -> None:
    """A gate that cannot fail measures nothing: each row of *Design* section 6 must show."""
    build, expected = BROKEN[name]
    problem = build(ring)
    solved = run_apbs(problem, tmp_path, name="broken")
    coarse = problem.grid != ring.grid
    found = _against_series(ring, ring.probes.at(solved.potential, coarse=coarse))
    logger.info("VAL-06 ring, broken (%s): %s", name, found)
    over = found.exceeding(HALF)
    assert set(expected) <= set(over), (name, found)
